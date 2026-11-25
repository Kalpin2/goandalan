"""Token-Efficient Self-Learning & Scrape Compaction Engine for @goandalan.

Implements 0-LLM-token deterministic pipelines:
1. `compact_scrape_text`: cleans raw Agent-Reach/web text (strips nav/HTML/link boilerplate),
   prioritizes Indonesian local-business UX & pain signals, caps at <= 700 chars/source & <= 4 sources.
2. `compute_edit_delta`: deterministic diff between agent draft and human-edited final text
   (word_delta, sapaan_changed, emoji_removed, shortened) using 0 LLM tokens.
3. `build_learning_digest`: aggregates `copy_learning_log.md`, `reels_learning_log.md`, and posted
   IG metrics into a compact `learning_digest.json` (strictly capped <= ~1,200 tokens).
4. `evaluate_learning_signals`: updates `learning_digest.json` and appends at most 3 new unapproved
   candidate patterns (`status: candidate`, `approved_by_user: false`) to `copy_candidates.md` /
   `reels_candidates.md` solely from the compact digest (never reading full raw logs into prompts).
5. `get_relevant_pattern_slice`: slice-only reader returning `learning_digest.json` + relevant
   pattern IDs for the requested channel/category/voice.
"""

from __future__ import annotations

import json
import re
import threading
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config import settings

REFERENCES_DIR = settings.BASE_DIR / "skills" / "instagram-creative-agent" / "references"
COPY_LEARNING_LOG_PATH = REFERENCES_DIR / "copy_learning_log.md"
COPY_CANDIDATES_PATH = REFERENCES_DIR / "copy_candidates.md"
REELS_LEARNING_LOG_PATH = REFERENCES_DIR / "reels_learning_log.md"
REELS_CANDIDATES_PATH = REFERENCES_DIR / "reels_candidates.md"
LEARNING_DIGEST_PATH = REFERENCES_DIR / "learning_digest.json"

MAX_DIGEST_CHARS = 4600  # ~1,150 tokens (strictly <= ~1,200 tokens)
_FILE_LOCK = threading.Lock()

EMOJI_PATTERN = re.compile(r"[\U0001F300-\U0001FAFF\u2600-\u27BF]")

_BOILERPLATE_LINE_RE = re.compile(
    r"(?:^|\b)(?:accept\s+all|cookie\s+policy|privacy\s+policy|terms\s+of\s+(?:service|use)|"
    r"all\s+rights\s+reserved|copyright\s+©?|skip\s+to\s+(?:main\s+)?content|sign\s+in|log\s+in|"
    r"register\s+now|subscribe\s+to|menu\s+navigation|toggle\s+navigation|powered\s+by|"
    r"baca\s+juga|ikuti\s+kami|bagikan\s+artikel|kebijakan\s+privasi|syarat\s+dan\s+ketentuan|"
    r"daftar\s+sekarang|masuk\s+akun|beranda\s*\|\s*tentang)(?:\b|$)",
    flags=re.IGNORECASE,
)

# Signals of real Indonesian local-business / UMKM UX, trust, booking, and ads pain points
PAIN_SIGNAL_KEYWORDS: tuple[str, ...] = (
    "whatsapp",
    "wa",
    "chat",
    "admin",
    "balas",
    "slow respon",
    "slow response",
    "booking",
    "reservasi",
    "jadwal",
    "antre",
    "antri",
    "website",
    "web",
    "link bio",
    "linktree",
    "linktr",
    "google maps",
    "maps",
    "instagram",
    "ig",
    "dm",
    "iklan",
    "ads",
    "boncos",
    "closing",
    "pelanggan",
    "customer",
    "klien",
    "pasien",
    "order",
    "pesan",
    "menu",
    "pdf",
    "harga",
    "katalog",
    "trust",
    "percaya",
    "kredibel",
    "profesional",
    "sepi",
    "hp",
    "mobile",
    "lemot",
    "ribet",
    "bingung",
    "umkm",
    "bisnis lokal",
    "klinik",
    "kafe",
    "kopi",
    "bakery",
    "barber",
    "bengkel",
    "pilates",
    "salon",
)

_SAPAAN_PAIRS: tuple[tuple[str, str], ...] = (
    ("Kak", "Bapak/Ibu"),
    ("Bapak/Ibu", "Kak"),
    ("Anda", "Kak"),
    ("Kak", "Anda"),
    ("Anda", "Bapak/Ibu"),
    ("Bapak/Ibu", "Anda"),
    ("gw", "saya"),
    ("gue", "saya"),
    ("lo", "Anda"),
)


def _count_words(text: str) -> int:
    norm = re.sub(r"\[[^\]]+\]", "detail spesifik ig mereka", text or "")
    return len([w for w in re.split(r"\s+", norm.strip()) if w])


def _strip_boilerplate_and_html(raw: str) -> str:
    txt = str(raw or "")
    # Remove script/style/nav/footer blocks if raw HTML leaked in
    txt = re.sub(r"<(script|style|nav|footer|noscript|svg)[^>]*>[\s\S]*?</\1>", " ", txt, flags=re.IGNORECASE)
    txt = re.sub(r"<[^>]+>", " ", txt)
    # Remove markdown images and simplify links
    txt = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", txt)
    txt = re.sub(r"\[([^\]]+)\]\((?:https?://[^)]+)\)", r"\1", txt)
    # Deduplicate repeated URLs (drop bare URLs after stripping)
    txt = re.sub(r"https?://\S+", " ", txt)
    txt = re.sub(r"[#*_`>|~]+", " ", txt)

    kept_lines: list[str] = []
    seen_lines: set[str] = set()
    for line in re.split(r"[\r\n]+", txt):
        cleaned = re.sub(r"\s+", " ", line).strip(" -•·|")
        if len(cleaned) < 12:
            continue
        if _BOILERPLATE_LINE_RE.search(cleaned):
            continue
        norm_key = cleaned.lower()
        if norm_key in seen_lines:
            continue
        seen_lines.add(norm_key)
        kept_lines.append(cleaned)
    return "\n".join(kept_lines)


def _pain_signal_score(sentence: str) -> int:
    low = sentence.lower()
    score = 0
    for kw in PAIN_SIGNAL_KEYWORDS:
        if " " in kw:
            if kw in low:
                score += 2
        else:
            if re.search(rf"\b{re.escape(kw)}\b", low):
                score += 1
    return score


def compact_single_text(raw_text: str, *, max_chars: int = 700) -> str:
    """Clean a single raw scrape block, filter for Indonesian UMKM/UX pain sentences, and cap <= max_chars."""
    limit = max(80, min(700, int(max_chars)))
    cleaned = _strip_boilerplate_and_html(raw_text)
    if not cleaned:
        return ""

    # Split into candidate sentences preserving order
    raw_sentences: list[str] = []
    for line in cleaned.splitlines():
        for part in re.split(r"(?<=[.!?])\s+", line):
            s = re.sub(r"\s+", " ", part).strip(" -•·|")
            if len(s) >= 14:
                raw_sentences.append(s)

    if not raw_sentences:
        flat = re.sub(r"\s+", " ", cleaned).strip()
        return flat[:limit].rsplit(" ", 1)[0].strip() if len(flat) > limit else flat

    scored = [(idx, _pain_signal_score(s), s) for idx, s in enumerate(raw_sentences)]
    signal_only = [item for item in scored if item[1] > 0]
    if signal_only:
        # Rank highest-signal sentences first, then restore reading order of selected top sentences
        ranked = sorted(signal_only, key=lambda x: (-x[1], x[0]))
    else:
        ranked = scored

    chosen: list[tuple[int, str]] = []
    cur_len = 0
    seen_s: set[str] = set()
    for idx, _sc, sent in ranked:
        key = sent.lower()
        if key in seen_s:
            continue
        seen_s.add(key)
        add_len = len(sent) + (1 if chosen else 0)
        if cur_len + add_len <= limit:
            chosen.append((idx, sent))
            cur_len += add_len
        elif not chosen:
            trimmed = sent[: max(40, limit - 1)].rsplit(" ", 1)[0].strip() or sent[:limit]
            chosen.append((idx, trimmed))
            break

    chosen.sort(key=lambda x: x[0])
    out = " ".join(s for _, s in chosen).strip()
    if len(out) > limit:
        out = out[:limit].rsplit(" ", 1)[0].strip() or out[:limit]
    return out


def compact_scrape_text(
    raw_sources: str | list[Any],
    *,
    max_chars: int = 700,
    max_sources: int = 4,
) -> dict[str, Any]:
    """Pre-clean Agent-Reach raw output in Python: max 700 chars/source, max 4 sources/batch."""
    cap_chars = max(80, min(700, int(max_chars)))
    cap_sources = max(1, min(4, int(max_sources)))

    items_in: list[dict[str, str]] = []
    if isinstance(raw_sources, str):
        items_in = [{"title": "", "source": "text", "url": "", "text": raw_sources}]
    elif isinstance(raw_sources, list):
        for idx, entry in enumerate(raw_sources):
            if isinstance(entry, dict):
                title = str(entry.get("title") or "").strip()
                body = str(entry.get("text") or entry.get("snippet") or entry.get("content") or "").strip()
                combined = f"{title}. {body}".strip(". ") if title and body and title.lower() not in body.lower() else (body or title)
                items_in.append(
                    {
                        "title": title[:120],
                        "source": str(entry.get("source") or entry.get("channel") or f"source_{idx + 1}"),
                        "url": str(entry.get("url") or "").strip(),
                        "text": combined,
                    }
                )
            elif isinstance(entry, str) and entry.strip():
                items_in.append({"title": "", "source": f"source_{idx + 1}", "url": "", "text": entry})

    orig_chars = sum(len(x["text"]) for x in items_in)
    compacted_list: list[dict[str, Any]] = []
    for item in items_in:
        compact_txt = compact_single_text(item["text"], max_chars=cap_chars)
        if not compact_txt:
            continue
        sig_score = _pain_signal_score(compact_txt)
        compacted_list.append(
            {
                "source": item["source"],
                "title": item["title"],
                "url": item["url"],
                "text": compact_txt,
                "chars": len(compact_txt),
                "signal_score": sig_score,
            }
        )

    # Keep top `cap_sources` sources ranked by pain-signal density
    compacted_list.sort(key=lambda x: (-x["signal_score"], -x["chars"]))
    selected = compacted_list[:cap_sources]
    combined = "\n---\n".join(s["text"] for s in selected)
    total_chars = sum(s["chars"] for s in selected)
    saved_pct = round(100.0 * max(0, orig_chars - total_chars) / orig_chars, 1) if orig_chars > 0 else 0.0

    return {
        "sources": selected,
        "combined_text": combined,
        "source_count": len(selected),
        "total_chars": total_chars,
        "original_chars": orig_chars,
        "saved_pct": saved_pct,
        "max_chars_per_source": cap_chars,
        "max_sources": cap_sources,
    }


def compute_edit_delta(original_draft: str, final_text: str) -> dict[str, Any]:
    """Zero-token deterministic diff between agent draft and human-edited text."""
    orig = (original_draft or "").strip()
    final = (final_text or "").strip()
    ow = _count_words(orig)
    fw = _count_words(final)
    word_delta = fw - ow

    if orig == final:
        return {
            "changed": False,
            "orig_words": ow,
            "final_words": fw,
            "word_delta": 0,
            "shortened": False,
            "expanded": False,
            "sapaan_changed": "",
            "emoji_removed": 0,
            "emoji_added": 0,
            "edit_tags": ["unchanged"],
            "summary": "unchanged",
        }

    shortened = word_delta < -3
    expanded = word_delta > 3

    orig_emoji = len(EMOJI_PATTERN.findall(orig))
    final_emoji = len(EMOJI_PATTERN.findall(final))
    emoji_removed = max(0, orig_emoji - final_emoji)
    emoji_added = max(0, final_emoji - orig_emoji)

    sapaan_changed = ""
    for old_s, new_s in _SAPAAN_PAIRS:
        if re.search(rf"\b{re.escape(old_s)}\b", orig) and not re.search(rf"\b{re.escape(old_s)}\b", final) and re.search(rf"\b{re.escape(new_s)}\b", final):
            sapaan_changed = f"{old_s}->{new_s}"
            break

    notes: list[str] = []
    tags: list[str] = []
    if shortened:
        notes.append(f"shortened ({ow}->{fw}w)")
        tags.append("shortened")
    elif expanded:
        notes.append(f"expanded ({ow}->{fw}w)")
        tags.append("expanded")

    if emoji_removed > 0:
        notes.append("removed emoji")
        tags.append("emoji_removed")
    elif emoji_added > 0:
        notes.append("added emoji")
        tags.append("emoji_added")

    if sapaan_changed:
        notes.append(f"changed sapaan {sapaan_changed}")
        tags.append("sapaan_changed")

    if not notes:
        notes.append("edited wording")
        tags.append("edited_wording")

    return {
        "changed": True,
        "orig_words": ow,
        "final_words": fw,
        "word_delta": word_delta,
        "shortened": shortened,
        "expanded": expanded,
        "sapaan_changed": sapaan_changed,
        "emoji_removed": emoji_removed,
        "emoji_added": emoji_added,
        "edit_tags": tags,
        "summary": ", ".join(notes),
    }


def _parse_yaml_blocks(path: Path, root_key: str) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8", errors="replace")
    blocks = re.findall(r"```yaml\s*([\s\S]*?)```", text)
    parsed: list[dict[str, Any]] = []
    for blk in blocks:
        if f"{root_key}:" not in blk:
            continue
        item: dict[str, Any] = {}
        for line in blk.splitlines():
            s = line.strip()
            if not s or s.startswith("#") or s == f"{root_key}:":
                continue
            if ":" not in s:
                continue
            k, _, raw_v = s.partition(":")
            k = k.strip()
            v = raw_v.strip()
            if not v:
                item[k] = ""
                continue
            try:
                item[k] = json.loads(v)
            except Exception:
                if v.lower() == "true":
                    item[k] = True
                elif v.lower() == "false":
                    item[k] = False
                elif re.fullmatch(r"-?\d+", v):
                    item[k] = int(v)
                elif re.fullmatch(r"-?\d+\.\d+", v):
                    item[k] = float(v)
                else:
                    item[k] = v.strip("\"'")
        # Ignore template schema block (empty lead_id and placeholder channel/date)
        if not item.get("date") and not item.get("lead_id") and not item.get("display_name"):
            continue
        if "|" in str(item.get("channel") or "") or "|" in str(item.get("outcome") or ""):
            continue
        parsed.append(item)
    return parsed


def _load_db_posted_metrics(db_path: Path | None = None) -> list[dict[str, Any]]:
    try:
        import database as db
        with db.get_conn(db_path) as conn:
            cols = {r["name"] for r in conn.execute("PRAGMA table_info(content_reviews)").fetchall()}
            if "metrics_json" not in cols:
                return []
            rows = conn.execute(
                """
                SELECT r.lead_id, r.content_format, r.voice_id, r.hook_pattern_id, r.metrics_json,
                       r.pain_code, r.reel_hook_id, l.category
                FROM content_reviews r
                JOIN leads l ON l.id = r.lead_id
                WHERE r.review_status = 'posted'
                """
            ).fetchall()
            out: list[dict[str, Any]] = []
            for r in rows:
                try:
                    m = json.loads(r["metrics_json"] or "{}")
                except Exception:
                    m = {}
                if any(int(m.get(k) or 0) > 0 for k in ("views", "saves", "shares", "dm_in")):
                    out.append(
                        {
                            "lead_id": r["lead_id"],
                            "content_format": r["content_format"] or "carousel",
                            "voice_id": r["voice_id"] or "",
                            "hook_pattern_id": r["hook_pattern_id"] or "",
                            "pain_code": r["pain_code"] or "",
                            "reel_hook_id": r["reel_hook_id"] or "",
                            "category": r["category"] or "Bisnis Lokal",
                            "views": int(m.get("views") or 0),
                            "saves": int(m.get("saves") or 0),
                            "shares": int(m.get("shares") or 0),
                            "dm_in": int(m.get("dm_in") or 0),
                        }
                    )
            return out
    except Exception:
        return []


def build_learning_digest(
    *,
    copy_log_path: Path | None = None,
    reels_log_path: Path | None = None,
    digest_path: Path | None = None,
    db_path: Path | None = None,
    write_file: bool = True,
) -> dict[str, Any]:
    """Deterministically aggregate copy/reels logs & IG metrics into compact `learning_digest.json` (<= ~1,200 tokens)."""
    c_path = copy_log_path or COPY_LEARNING_LOG_PATH
    r_path = reels_log_path or REELS_LEARNING_LOG_PATH
    out_path = digest_path or LEARNING_DIGEST_PATH

    copy_entries = _parse_yaml_blocks(c_path, "copy_log")
    reels_entries = _parse_yaml_blocks(r_path, "reels_log")
    posted_metrics = _load_db_posted_metrics(db_path=db_path)

    pattern_stats: dict[str, dict[str, Any]] = {}
    voice_stats: dict[str, dict[str, Any]] = {}
    category_stats: dict[str, dict[str, Any]] = {}
    edit_counter: Counter[str] = Counter()

    def _bucket(store: dict[str, dict[str, Any]], key: str) -> dict[str, Any]:
        if key not in store:
            store[key] = {
                "uses": 0,
                "interested": 0,
                "ignored_48h": 0,
                "edited": 0,
                "views": 0,
                "saves": 0,
                "shares": 0,
                "dm_in": 0,
                "metric_samples": 0,
            }
        return store[key]

    def _record_edit(edit_summary: str) -> bool:
        es = (edit_summary or "").strip().lower()
        if not es or es == "unchanged":
            return False
        if "shortened" in es:
            edit_counter["shortened"] += 1
        if "expanded" in es:
            edit_counter["expanded"] += 1
        if "sapaan" in es:
            edit_counter["sapaan_changed"] += 1
        if "removed emoji" in es or "emoji_removed" in es:
            edit_counter["emoji_removed"] += 1
        if "edited wording" in es:
            edit_counter["edited_wording"] += 1
        if not any(k in es for k in ("shortened", "expanded", "sapaan", "emoji", "edited wording")):
            edit_counter["other_edit"] += 1
        return True

    for e in copy_entries:
        edited = _record_edit(str(e.get("edit_summary") or ""))
        outcome = str(e.get("outcome") or "").strip().lower()
        voice = str(e.get("voice") or "").strip().upper()
        cat = str(e.get("category") or "Bisnis Lokal").strip() or "Bisnis Lokal"
        pats = e.get("patterns_used") if isinstance(e.get("patterns_used"), list) else []

        if voice and re.fullmatch(r"V[1-6]", voice):
            vb = _bucket(voice_stats, voice)
            vb["uses"] += 1
            if edited:
                vb["edited"] += 1
            if outcome == "interested":
                vb["interested"] += 1
            elif outcome == "ignored_48h":
                vb["ignored_48h"] += 1

        cb = _bucket(category_stats, cat)
        cb["uses"] += 1
        if edited:
            cb["edited"] += 1
        if outcome == "interested":
            cb["interested"] += 1
        elif outcome == "ignored_48h":
            cb["ignored_48h"] += 1

        for pid in pats:
            p = str(pid or "").strip().upper()
            if not p:
                continue
            pb = _bucket(pattern_stats, p)
            pb["uses"] += 1
            if edited:
                pb["edited"] += 1
            if outcome == "interested":
                pb["interested"] += 1
            elif outcome == "ignored_48h":
                pb["ignored_48h"] += 1

    for e in reels_entries:
        edited = _record_edit(str(e.get("edit_summary") or ""))
        cat = str(e.get("category") or "Bisnis Lokal").strip() or "Bisnis Lokal"
        voice = str(e.get("voice") or "").strip().upper()
        views = int(e.get("views") or 0)
        saves = int(e.get("saves") or 0)
        shares = int(e.get("shares") or 0)
        dm_in = int(e.get("dm_in") or 0)
        has_metrics = (views + saves + shares + dm_in) > 0

        cb = _bucket(category_stats, cat)
        cb["uses"] += 1
        if edited:
            cb["edited"] += 1
        if has_metrics:
            cb["views"] += views
            cb["saves"] += saves
            cb["shares"] += shares
            cb["dm_in"] += dm_in
            cb["metric_samples"] += 1

        if voice and re.fullmatch(r"V[1-6]", voice):
            vb = _bucket(voice_stats, voice)
            vb["uses"] += 1
            if edited:
                vb["edited"] += 1

        for p_raw in (e.get("pain_code"), e.get("reel_hook_id"), e.get("hook_pattern_id")):
            p = str(p_raw or "").strip().upper()
            if not p or p == "AUTO":
                continue
            pb = _bucket(pattern_stats, p)
            pb["uses"] += 1
            if edited:
                pb["edited"] += 1
            if has_metrics:
                pb["views"] += views
                pb["saves"] += saves
                pb["shares"] += shares
                pb["dm_in"] += dm_in
                pb["metric_samples"] += 1

    for pm in posted_metrics:
        cat = str(pm.get("category") or "Bisnis Lokal").strip()
        cb = _bucket(category_stats, cat)
        cb["views"] += pm["views"]
        cb["saves"] += pm["saves"]
        cb["shares"] += pm["shares"]
        cb["dm_in"] += pm["dm_in"]
        cb["metric_samples"] += 1
        for p_raw in (pm.get("pain_code"), pm.get("reel_hook_id"), pm.get("hook_pattern_id")):
            p = str(p_raw or "").strip().upper()
            if not p or p == "AUTO":
                continue
            pb = _bucket(pattern_stats, p)
            pb["views"] += pm["views"]
            pb["saves"] += pm["saves"]
            pb["shares"] += pm["shares"]
            pb["dm_in"] += pm["dm_in"]
            pb["metric_samples"] += 1

    def _compact_row(b: dict[str, Any]) -> dict[str, Any]:
        decided = b["interested"] + b["ignored_48h"]
        row: dict[str, Any] = {
            "u": b["uses"],
            "ed": b["edited"],
        }
        if decided > 0:
            row["win"] = round(b["interested"] / decided, 2)
            row["ok"] = b["interested"]
            row["ign"] = b["ignored_48h"]
        if b["metric_samples"] > 0:
            ms = b["metric_samples"]
            row["avg_v"] = int(round(b["views"] / ms))
            row["avg_sv"] = round(b["saves"] / ms, 1)
            row["avg_sh"] = round(b["shares"] / ms, 1)
            row["dms"] = b["dm_in"]
        return row

    compact_patterns = {
        k: _compact_row(v)
        for k, v in sorted(pattern_stats.items(), key=lambda kv: (-kv[1]["uses"], kv[0]))[:24]
    }
    compact_voices = {
        k: _compact_row(v)
        for k, v in sorted(voice_stats.items(), key=lambda kv: kv[0])
    }

    weak_categories: list[dict[str, Any]] = []
    for cat, b in sorted(category_stats.items(), key=lambda kv: (kv[1]["uses"], kv[0])):
        decided = b["interested"] + b["ignored_48h"]
        win = (b["interested"] / decided) if decided > 0 else None
        edit_rate = (b["edited"] / b["uses"]) if b["uses"] > 0 else 0.0
        reasons: list[str] = []
        if b["uses"] < 3:
            reasons.append("low_sample")
        if edit_rate >= 0.5 and b["uses"] >= 2:
            reasons.append("high_edit_rate")
        if win is not None and win < 0.2 and decided >= 2:
            reasons.append("low_win_rate")
        if reasons:
            weak_categories.append(
                {
                    "category": cat,
                    "uses": b["uses"],
                    "edit_rate": round(edit_rate, 2),
                    "win_rate": round(win, 2) if win is not None else None,
                    "reasons": reasons,
                }
            )
    weak_categories = weak_categories[:8]

    top_edits = [{"edit": k, "count": int(v)} for k, v in edit_counter.most_common(6)]

    digest: dict[str, Any] = {
        "version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "totals": {
            "copy_logs": len(copy_entries),
            "reels_logs": len(reels_entries),
            "posted_metric_items": len(posted_metrics),
        },
        "patterns": compact_patterns,
        "voices": compact_voices,
        "top_human_edits": top_edits,
        "weak_categories": weak_categories,
        "token_budget_rule": "Read learning_digest.json + pre-router pattern slice only; never load full raw logs.",
    }

    # Strictly enforce <= MAX_DIGEST_CHARS (~1,150 tokens)
    serialized = json.dumps(digest, ensure_ascii=False, separators=(",", ":"))
    if len(serialized) > MAX_DIGEST_CHARS:
        # Trim patterns & weak_categories progressively until well inside token budget
        for cap_p in (16, 12, 8):
            digest["patterns"] = dict(list(compact_patterns.items())[:cap_p])
            digest["weak_categories"] = weak_categories[:5]
            serialized = json.dumps(digest, ensure_ascii=False, separators=(",", ":"))
            if len(serialized) <= MAX_DIGEST_CHARS:
                break

    if write_file:
        with _FILE_LOCK:
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(json.dumps(digest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    return digest


def _existing_candidate_ids(path: Path) -> set[str]:
    if not path.exists():
        return set()
    txt = path.read_text(encoding="utf-8", errors="replace")
    return set(re.findall(r"^\s*id:\s*([A-Za-z0-9_-]+)", txt, flags=re.MULTILINE))


def _append_candidate_yaml(path: Path, header_title: str, yaml_body: str) -> None:
    with _FILE_LOCK:
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.write_text(f"# {header_title}\n\n## Candidates\n", encoding="utf-8")
        with path.open("a", encoding="utf-8") as fh:
            fh.write("\n" + yaml_body.strip() + "\n")


def evaluate_learning_signals(
    *,
    copy_log_path: Path | None = None,
    reels_log_path: Path | None = None,
    digest_path: Path | None = None,
    copy_candidates_path: Path | None = None,
    reels_candidates_path: Path | None = None,
    db_path: Path | None = None,
    max_candidates: int = 3,
) -> dict[str, Any]:
    """Rebuild `learning_digest.json` and propose up to 3 unapproved candidates ONLY from the compact digest."""
    out_digest_path = digest_path or LEARNING_DIGEST_PATH
    c_cand_path = copy_candidates_path or COPY_CANDIDATES_PATH
    r_cand_path = reels_candidates_path or REELS_CANDIDATES_PATH

    build_learning_digest(
        copy_log_path=copy_log_path,
        reels_log_path=reels_log_path,
        digest_path=out_digest_path,
        db_path=db_path,
        write_file=True,
    )

    # Slice-only reading: load ONLY the compact digest JSON from disk
    digest_raw = out_digest_path.read_text(encoding="utf-8")
    digest = json.loads(digest_raw)
    est_tokens = max(1, int(round(len(digest_raw) / 4.0)))

    existing_copy = _existing_candidate_ids(c_cand_path)
    existing_reels = _existing_candidate_ids(r_cand_path)

    cap = max(1, min(3, int(max_candidates)))
    proposed: list[dict[str, Any]] = []
    copy_added: list[str] = []
    reels_added: list[str] = []

    top_edits = {e["edit"]: e["count"] for e in (digest.get("top_human_edits") or [])}
    weak_cats = digest.get("weak_categories") or []
    patterns = digest.get("patterns") or {}

    # Proposal 1: If human frequently shortens copy, propose a tighter Cold DM opener candidate
    if len(proposed) < cap and top_edits.get("shortened", 0) >= 1 and "OPEN-C10" not in existing_copy:
        yaml_blk = """```yaml
pattern:
  id: OPEN-C10
  channel: dm
  slot: opener
  template: "{sapaan}, {detail_ig} di IG {nama_usaha} sudah rapi—tinggal halaman web ringkas biar calon tamu cepat cek info."
  levers: [L1, L4]
  voice_fit: [V1, V3, V5]
  works_for: ["coffee", "cafe", "bakery", "barbershop", "retail"]
  caution: ["Keep total DM <= 60 words; skip on formal clinics/legal"]
  distinct_from: "OPEN-C9 — tighter 1-clause phrasing triggered by human shortening edits in learning_digest."
  evidence: { uses: 0, replies: 0, interested: 0, declined: 0, ignored: 0, human_edited: 0 }
  source: digest_eval
  confidence: low
  status: candidate
  approved_by_user: false
```"""
        _append_candidate_yaml(c_cand_path, "Copy Candidates", yaml_blk)
        copy_added.append("OPEN-C10")
        proposed.append({"id": "OPEN-C10", "target": "copy_candidates.md", "reason": "frequent_shortened_edits"})

    # Proposal 2: If sapaan_changed or formal/weak category detected, propose a calm formal opener
    if len(proposed) < cap and (top_edits.get("sapaan_changed", 0) >= 1 or weak_cats) and "OPEN-C11" not in existing_copy:
        weak_cat_name = weak_cats[0]["category"] if weak_cats else "Klinik & Profesional"
        yaml_blk = f"""```yaml
pattern:
  id: OPEN-C11
  channel: dm
  slot: opener
  template: "{{sapaan}}, profil {{nama_usaha}} sudah jelas di Google Maps dan IG. Saya menyiapkan satu foto preview konsep halaman ringkas agar jadwal & layanan utama lebih mudah dibaca pasien/klien."
  levers: [L2, L4]
  voice_fit: [V2, V4]
  works_for: ["{weak_cat_name.lower()}", "klinik", "pilates", "legal", "b2b"]
  caution: ["Strict formal_editorial: zero casual slang, zero emoji, zero URL"]
  distinct_from: "OPEN-D1 — explicitly addresses weak/formal category signal from learning_digest."
  evidence: {{ uses: 0, replies: 0, interested: 0, declined: 0, ignored: 0, human_edited: 0 }}
  source: digest_eval
  confidence: low
  status: candidate
  approved_by_user: false
```"""
        _append_candidate_yaml(c_cand_path, "Copy Candidates", yaml_blk)
        copy_added.append("OPEN-C11")
        proposed.append({"id": "OPEN-C11", "target": "copy_candidates.md", "reason": f"weak_category_or_sapaan:{weak_cat_name}"})

    # Proposal 3: Propose a Reels pain-hook candidate if Reels pain hooks have low/missing coverage
    reel_pain_used = [k for k in patterns if k.startswith(("PAIN-", "REEL-HOOK-"))]
    if len(proposed) < cap and len(reel_pain_used) < 3 and "REEL-HOOK-C1" not in existing_reels:
        yaml_blk = """```yaml
reels_candidate:
  id: REEL-HOOK-C1
  pain_code: PAIN-WA
  voice_fit: [V1, V2, V5]
  hook_template: "Admin capek balas pertanyaan harga & alamat yang sama tiap hari?"
  vo_target_words: "35-55"
  cta_screen: "DM kata KONSEP"
  distinct_from: "REEL-HOOK-1 — opens directly with repetitive admin chat fatigue from UMKM pain signals."
  evidence: { uses: 0, avg_views: 0, avg_saves: 0, avg_shares: 0, dm_in: 0 }
  source: digest_eval
  confidence: low
  status: candidate
  approved_by_user: false
```"""
        _append_candidate_yaml(r_cand_path, "Reels Candidates", yaml_blk)
        reels_added.append("REEL-HOOK-C1")
        proposed.append({"id": "REEL-HOOK-C1", "target": "reels_candidates.md", "reason": "low_reels_hook_coverage"})

    return {
        "ok": True,
        "digest": digest,
        "digest_path": str(out_digest_path.relative_to(settings.BASE_DIR)).replace("\\", "/")
        if out_digest_path.is_relative_to(settings.BASE_DIR)
        else str(out_digest_path),
        "estimated_tokens": est_tokens,
        "proposed_candidates": proposed,
        "copy_candidates_added": copy_added,
        "reels_candidates_added": reels_added,
    }


def get_relevant_pattern_slice(
    channel: str,
    *,
    category: str = "",
    voice: str = "",
    digest_path: Path | None = None,
) -> dict[str, Any]:
    """Slice-only reader: returns compact digest + matching pattern metrics only (never full raw logs)."""
    path = digest_path or LEARNING_DIGEST_PATH
    if not path.exists():
        digest = build_learning_digest(digest_path=path, write_file=True)
    else:
        try:
            digest = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            digest = build_learning_digest(digest_path=path, write_file=True)

    ch = (channel or "").strip().lower()
    prefixes: tuple[str, ...]
    if ch in {"cold_dm_1", "dm", "outreach"}:
        prefixes = ("OPEN-", "ASK-")
    elif ch in {"reels", "reel"}:
        prefixes = ("PAIN-", "REEL-HOOK-", "HOOK-")
    else:
        prefixes = ("HOOK-", "CTA-")

    patterns = digest.get("patterns") or {}
    matched_patterns = {k: v for k, v in patterns.items() if k.startswith(prefixes)}
    v_key = (voice or "").strip().upper()
    matched_voice = {v_key: digest.get("voices", {}).get(v_key)} if v_key and v_key in (digest.get("voices") or {}) else (digest.get("voices") or {})

    cat_low = (category or "").strip().lower()
    weak = [
        w for w in (digest.get("weak_categories") or [])
        if not cat_low or cat_low in str(w.get("category") or "").lower()
    ]

    return {
        "channel": ch or "caption",
        "generated_at": digest.get("generated_at", ""),
        "totals": digest.get("totals", {}),
        "patterns": matched_patterns,
        "voices": matched_voice,
        "top_human_edits": digest.get("top_human_edits", []),
        "weak_categories": weak[:3],
    }
