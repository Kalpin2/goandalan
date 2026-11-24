"""Read-only prospect research & enrichment helper powered by Agent-Reach CLI.

Strictly read-only:
- Reads public prospect websites via `agent-reach read <url>` to derive concrete,
  evidence-backed `ux_flaw` observations (never invents issues if fetch fails).
- Optionally reads Instagram profile/recent posts via `agent-reach instagram`
  to populate 1 specific `ig_observation` for `NEW` leads that do not yet have one.
- NEVER logs in, NEVER copies or touches the main `@goandalan` Instagram session,
  and immediately stops querying Instagram on `NEED_LOGIN`, `RATE_LIMITED`,
  `PLATFORM_BLOCKED`, `BUSY`, `NEED_SETUP`, or `TIMEOUT`.
"""

from __future__ import annotations

import ipaddress
import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse

import database as db
from config import settings

RunnerFn = Callable[[list[str], int], dict[str, Any]]

STOP_ERROR_CODES = frozenset(
    {
        "NEED_LOGIN",
        "RATE_LIMITED",
        "PLATFORM_BLOCKED",
        "NEED_SETUP",
        "TIMEOUT",
        "BUSY",
        "UPSTREAM_BROKEN",
        "CLI_NOT_FOUND",
    }
)

AGGREGATOR_HOSTS = (
    "linktr.ee",
    "linktree.com",
    "lynk.id",
    "desty.page",
    "beacons.ai",
    "carrd.co",
    "taplink.cc",
    "taplink.at",
    "bio.site",
    "bit.ly",
    "s.id",
    "msha.ke",
)

INSTAGRAM_HOSTS = ("instagram.com", "www.instagram.com", "m.instagram.com", "instagr.am")

RESERVED_IG_SEGMENTS = frozenset(
    {
        "p",
        "reel",
        "reels",
        "stories",
        "explore",
        "accounts",
        "about",
        "legal",
        "developer",
        "developers",
        "direct",
        "tv",
        "share",
        "api",
        "oauth",
    }
)

_IG_HANDLE_RE = re.compile(r"^[A-Za-z0-9._]{1,30}$")


def resolve_agent_reach_bin() -> str | None:
    """Return path to the `agent-reach` CLI executable if available."""
    configured = (settings.AGENT_REACH_BIN or "").strip()
    if configured:
        cand = Path(configured)
        if cand.is_file():
            return str(cand)
        found_cfg = shutil.which(configured)
        if found_cfg:
            return found_cfg
    return shutil.which("agent-reach")


def validate_public_http_url(url: str | None) -> str:
    """Validate that `url` is a public http/https URL (blocks private/loopback/local hosts)."""
    raw = (url or "").strip()
    if not raw or raw.startswith("-"):
        return ""
    if "://" not in raw and "." in raw and " " not in raw:
        raw = f"https://{raw}"
    try:
        parsed = urlparse(raw)
    except Exception:
        return ""

    if parsed.scheme.lower() not in {"http", "https"}:
        return ""
    host = (parsed.hostname or "").strip().lower()
    if not host or "." not in host:
        return ""
    if host in {"localhost", "localhost.localdomain"} or host.endswith((".local", ".internal", ".localhost")):
        return ""

    try:
        ip = ipaddress.ip_address(host)
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_reserved
            or ip.is_unspecified
        ):
            return ""
    except ValueError:
        pass

    return parsed.geturl()


def _is_instagram_url(url: str) -> bool:
    try:
        host = (urlparse(url).hostname or "").lower()
    except Exception:
        return False
    return host in INSTAGRAM_HOSTS or host.endswith(".instagram.com")


def extract_instagram_handle(raw_handle: str | None = "", website_url: str | None = "") -> str:
    """Extract and validate a clean Instagram username (without @) from handle or URL."""
    candidates = [(raw_handle or "").strip(), (website_url or "").strip()]
    for cand in candidates:
        if not cand:
            continue
        cleaned = cand
        if "instagram.com" in cleaned.lower() or "instagr.am" in cleaned.lower():
            if "://" not in cleaned:
                cleaned = "https://" + cleaned
            try:
                parsed = urlparse(cleaned)
                parts = [p for p in (parsed.path or "").split("/") if p]
                if not parts:
                    continue
                cleaned = parts[0]
            except Exception:
                continue
        elif "://" in cleaned or "/" in cleaned:
            # Non-Instagram URL; skip this candidate
            continue

        cleaned = cleaned.lstrip("@").strip().strip("/")
        if cleaned.lower() in RESERVED_IG_SEGMENTS:
            continue
        if _IG_HANDLE_RE.match(cleaned):
            return cleaned.lower()
    return ""


def _parse_json_line(stdout: str) -> dict[str, Any] | None:
    lines = [line.strip() for line in (stdout or "").splitlines() if line.strip()]
    for line in reversed(lines):
        if line.startswith("{") and line.endswith("}"):
            try:
                data = json.loads(line)
                if isinstance(data, dict):
                    return data
            except json.JSONDecodeError:
                continue
    return None


def run_agent_reach(args: list[str], timeout: int = 22) -> dict[str, Any]:
    """Execute read-only `agent-reach` CLI safely (`shell=False`) and normalize JSON response."""
    cli = resolve_agent_reach_bin()
    if not cli:
        return {
            "ok": False,
            "items": [],
            "error_code": "CLI_NOT_FOUND",
            "error_message": "agent-reach CLI belum terpasang di environment ini.",
            "raw": {},
        }

    # Defense-in-depth: never allow login/logout/write/config mutations from the enricher
    if not args or args[0] not in {"read", "instagram", "web", "doctor", "channels"}:
        return {
            "ok": False,
            "items": [],
            "error_code": "BAD_INPUT",
            "error_message": "Aksi agent-reach tidak diizinkan untuk modul enrichment read-only.",
            "raw": {},
        }
    if args[0] == "instagram" and (len(args) < 2 or args[1] not in {"profile", "posts", "search"}):
        return {
            "ok": False,
            "items": [],
            "error_code": "BAD_INPUT",
            "error_message": "Hanya aksi baca Instagram (profile/posts/search) yang diizinkan.",
            "raw": {},
        }

    try:
        proc = subprocess.run(
            [cli, *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=max(5, int(timeout)),
            shell=False,
        )
    except subprocess.TimeoutExpired:
        return {
            "ok": False,
            "items": [],
            "error_code": "TIMEOUT",
            "error_message": "Permintaan agent-reach melewati batas waktu.",
            "raw": {},
        }
    except OSError as exc:
        return {
            "ok": False,
            "items": [],
            "error_code": "CLI_EXEC_ERROR",
            "error_message": str(exc),
            "raw": {},
        }

    payload = _parse_json_line(proc.stdout)
    if not payload:
        return {
            "ok": False,
            "items": [],
            "error_code": "INVALID_JSON",
            "error_message": (proc.stderr or proc.stdout or "Output agent-reach bukan JSON valid.")[:240],
            "raw": {},
        }

    err = payload.get("error") or {}
    return {
        "ok": bool(payload.get("ok")),
        "items": payload.get("items") or [],
        "error_code": str(err.get("code") or "") if isinstance(err, dict) else "",
        "error_message": str(err.get("message") or "") if isinstance(err, dict) else "",
        "raw": payload,
    }


def _clean_readable_text(text: str) -> str:
    txt = re.sub(r"https?://\S+", " ", text or "")
    txt = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", txt)
    txt = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", txt)
    txt = re.sub(r"[#*_`>|]+", " ", txt)
    txt = re.sub(r"\s+", " ", txt).strip()
    return txt


def analyze_website_ux_flaw(
    website_url: str | None,
    lead: dict[str, Any] | None = None,
    runner: RunnerFn | None = None,
    timeout: int = 22,
) -> dict[str, Any]:
    """Read a prospect's public homepage via `agent-reach read <url>` and summarize concrete UX flaws.

    Returns `{"ok": bool, "ux_flaw": str, "signals": list[str], "reason": str}`.
    Never fabricates observations when fetching fails or returns empty content.
    """
    clean_url = validate_public_http_url(website_url)
    if not clean_url:
        return {"ok": False, "ux_flaw": "", "signals": [], "reason": "invalid_or_empty_url"}

    if _is_instagram_url(clean_url):
        return {"ok": False, "ux_flaw": "", "signals": [], "reason": "instagram_url_skipped"}

    host = (urlparse(clean_url).hostname or "").lower()
    is_aggregator = any(host == dom or host.endswith("." + dom) for dom in AGGREGATOR_HOSTS)

    exec_fn = runner or run_agent_reach
    res = exec_fn(["read", clean_url], timeout)
    if not res.get("ok"):
        return {
            "ok": False,
            "ux_flaw": "",
            "signals": [],
            "reason": res.get("error_code") or "read_failed",
        }

    items = res.get("items") or []
    if not items or not isinstance(items[0], dict):
        return {"ok": False, "ux_flaw": "", "signals": [], "reason": "empty_items"}

    first = items[0]
    raw_text = "\n".join(
        part for part in (str(first.get("title") or ""), str(first.get("text") or "")) if part.strip()
    )
    if not raw_text.strip():
        return {"ok": False, "ux_flaw": "", "signals": [], "reason": "empty_text"}

    text_lower = raw_text.lower()
    readable = _clean_readable_text(raw_text)
    word_count = len(readable.split())

    signals: list[str] = []
    findings: list[str] = []

    if is_aggregator:
        signals.append("link_aggregator")
        findings.append(
            "halaman masih berupa daftar tautan aggregator sehingga ringkasan layanan dan info utama belum menyatu di satu tampilan web"
        )

    has_pdf_menu = bool(
        re.search(r"\.pdf\b|drive\.google\.com|download\s+menu|unduh\s+menu|menu\s+pdf|katalog\s+pdf", text_lower)
    )
    if has_pdf_menu:
        signals.append("pdf_menu")
        findings.append(
            "menu/katalog masih diarahkan ke file PDF atau dokumen terpisah sehingga kurang praktis dibuka cepat di layar HP"
        )

    image_markdown_count = len(re.findall(r"!\[[^\]]*\]\([^)]*\)", raw_text))
    if not has_pdf_menu and image_markdown_count >= 3 and word_count < 60:
        signals.append("image_heavy_low_text")
        findings.append(
            "informasi halaman masih banyak berbentuk gambar dengan teks ringkas yang minim sehingga agak sulit dipindai cepat di HP"
        )

    has_direct_contact = bool(
        re.search(
            r"wa\.me/|api\.whatsapp\.com|whatsapp\.com/send|\bwhatsapp\b|tel:\+?\d|\+62\s?\d|08\d{7,}",
            text_lower,
        )
    )
    if not has_direct_contact:
        signals.append("no_direct_whatsapp")
        findings.append(
            "belum terlihat tombol atau tautan kontak WhatsApp langsung di halaman utama untuk pengunjung HP"
        )

    if word_count < 30 and "image_heavy_low_text" not in signals:
        signals.append("sparse_content")
        findings.append(
            "teks informasi di halaman utama masih sangat minim sehingga pengunjung HP belum langsung menangkap layanan dan jam buka"
        )
    elif word_count > 750 and not has_direct_contact:
        signals.append("dense_mobile_text")
        findings.append(
            "teks halaman utama cukup panjang sehingga informasi inti butuh scroll cukup jauh di layar HP"
        )

    if not findings:
        return {"ok": True, "ux_flaw": "", "signals": [], "reason": "no_obvious_flaw_detected"}

    selected = findings[:2]
    if len(selected) == 1:
        summary = selected[0][0].upper() + selected[0][1:] + "."
    else:
        first_part = selected[0][0].upper() + selected[0][1:]
        summary = f"{first_part}, dan {selected[1]}."

    return {
        "ok": True,
        "ux_flaw": summary,
        "signals": signals,
        "reason": "ok",
    }


def _clean_ig_snippet(raw_text: str, max_chars: int = 95) -> str:
    """Distill 1 crisp, human-readable phrase from real Instagram bio/caption text."""
    if not raw_text:
        return ""
    txt = re.sub(r"https?://\S+", " ", raw_text)
    txt = re.sub(r"#[\w\u00C0-\u024F]+", " ", txt)
    txt = re.sub(r"@[\w.]+", " ", txt)
    txt = re.sub(r"[\r\n|•·]+", ". ", txt)
    # Strip excessive non-text symbols/emojis while keeping Indonesian letters, digits, basic punctuation
    txt = re.sub(r"[^\w\s.,&'/-]", " ", txt)
    txt = re.sub(r"\s+", " ", txt).strip(" .,-/")
    if len(txt) < 12:
        return ""

    # Pick the first meaningful clause/sentence
    clauses = [c.strip(" .,-/") for c in re.split(r"[.!?]+", txt) if len(c.strip(" .,-/")) >= 12]
    chosen = clauses[0] if clauses else txt
    if len(chosen) > max_chars:
        cut = chosen[:max_chars].rsplit(" ", 1)[0].strip(" ,.-/")
        chosen = cut or chosen[:max_chars].strip()
    return chosen


def fetch_ig_observation(
    instagram_handle: str | None = "",
    website_url: str | None = "",
    lead: dict[str, Any] | None = None,
    runner: RunnerFn | None = None,
    timeout: int = 22,
) -> dict[str, Any]:
    """Fetch 1 specific, real Instagram observation via read-only `agent-reach instagram`.

    Returns:
        {
            "ok": bool,
            "handle": str,
            "ig_observation": str,
            "reason": str,
            "stop_channel": bool,
        }
    NEVER invents an observation when Instagram is not logged in, rate-limited, blocked, or empty.
    """
    handle = extract_instagram_handle(instagram_handle, website_url)
    if not handle:
        return {
            "ok": False,
            "handle": "",
            "ig_observation": "",
            "reason": "no_instagram_handle",
            "stop_channel": False,
        }

    exec_fn = runner or run_agent_reach

    # Step 1: Try recent posts first (highest-signal detail for Cold DM #1)
    posts_res = exec_fn(["instagram", "posts", handle, "--limit", "3"], timeout)
    if not posts_res.get("ok"):
        code = str(posts_res.get("error_code") or "ig_posts_failed")
        if code in STOP_ERROR_CODES:
            return {
                "ok": False,
                "handle": handle,
                "ig_observation": "",
                "reason": code,
                "stop_channel": True,
            }
    else:
        for item in posts_res.get("items") or []:
            if not isinstance(item, dict):
                continue
            candidate_text = str(item.get("text") or item.get("title") or "").strip()
            snippet = _clean_ig_snippet(candidate_text)
            if snippet:
                return {
                    "ok": True,
                    "handle": handle,
                    "ig_observation": f"postingan terbaru soal {snippet}",
                    "reason": "ok_posts",
                    "stop_channel": False,
                }

    # Step 2: Fallback to profile bio (only if Step 1 did not trigger a stop code)
    prof_res = exec_fn(["instagram", "profile", handle], min(timeout, 18))
    if not prof_res.get("ok"):
        code = str(prof_res.get("error_code") or "ig_profile_failed")
        return {
            "ok": False,
            "handle": handle,
            "ig_observation": "",
            "reason": code,
            "stop_channel": code in STOP_ERROR_CODES,
        }

    for item in prof_res.get("items") or []:
        if not isinstance(item, dict):
            continue
        raw_obj = item.get("raw") if isinstance(item.get("raw"), dict) else {}
        bio_text = str(raw_obj.get("bio") or raw_obj.get("biography") or item.get("text") or "").strip()
        snippet = _clean_ig_snippet(bio_text)
        if snippet:
            return {
                "ok": True,
                "handle": handle,
                "ig_observation": f"bio IG yang menonjolkan {snippet}",
                "reason": "ok_profile",
                "stop_channel": False,
            }

    return {
        "ok": False,
        "handle": handle,
        "ig_observation": "",
        "reason": "no_public_ig_detail",
        "stop_channel": False,
    }


def enrich_new_lead(
    lead_id: int,
    *,
    ig_channel_blocked: bool = False,
    runner: RunnerFn | None = None,
    timeout: int = 22,
) -> dict[str, Any]:
    """Enrich a single `NEW` lead that has no `ig_observation` yet."""
    lead = db.get_lead(lead_id)
    if not lead:
        return {"lead_id": lead_id, "enriched": False, "skipped": True, "reason": "lead_not_found", "stop_ig_channel": False}

    if lead.get("status") != "NEW":
        return {"lead_id": lead_id, "enriched": False, "skipped": True, "reason": "status_not_new", "stop_ig_channel": False}

    if (lead.get("ig_observation") or "").strip():
        return {"lead_id": lead_id, "enriched": False, "skipped": True, "reason": "already_has_ig_observation", "stop_ig_channel": False}

    updates: dict[str, Any] = {}
    web_reason = "skipped"
    ig_reason = "skipped"
    stop_ig_channel = ig_channel_blocked

    website_url = (lead.get("website_url") or "").strip()
    if website_url and not _is_instagram_url(website_url):
        web_res = analyze_website_ux_flaw(website_url, lead=lead, runner=runner, timeout=timeout)
        web_reason = web_res.get("reason") or "unknown"
        if web_res.get("ok") and web_res.get("ux_flaw"):
            updates["ux_flaw"] = web_res["ux_flaw"]

    handle = extract_instagram_handle(lead.get("instagram_handle"), website_url)
    if handle and not (lead.get("instagram_handle") or "").strip():
        updates["instagram_handle"] = f"@{handle}"

    if handle and not ig_channel_blocked:
        ig_res = fetch_ig_observation(handle, website_url, lead=lead, runner=runner, timeout=timeout)
        ig_reason = ig_res.get("reason") or "unknown"
        if ig_res.get("stop_channel"):
            stop_ig_channel = True
        if ig_res.get("ok") and ig_res.get("ig_observation"):
            updates["ig_observation"] = ig_res["ig_observation"]
    elif handle and ig_channel_blocked:
        ig_reason = "ig_channel_paused"

    if updates:
        db.update_lead(lead_id, updates)

    return {
        "lead_id": lead_id,
        "business_name": lead.get("business_name") or "",
        "enriched": bool(updates),
        "skipped": False,
        "updated_fields": sorted(updates.keys()),
        "web_reason": web_reason,
        "ig_reason": ig_reason,
        "stop_ig_channel": stop_ig_channel,
    }


def enrich_new_leads(
    lead_ids: list[int] | None = None,
    *,
    limit: int = 15,
    progress_cb: Callable[[int, int, dict[str, Any]], None] | None = None,
    runner: RunnerFn | None = None,
    timeout: int = 22,
) -> dict[str, Any]:
    """Enrich eligible `NEW` leads without `ig_observation` after a scrape job.

    Safe fallback: if `agent-reach` CLI is missing or Instagram returns `NEED_LOGIN` /
    `RATE_LIMITED`, it never raises and cleanly skips blocked channels.
    """
    if runner is None and not resolve_agent_reach_bin():
        return {
            "available": False,
            "processed": 0,
            "updated": 0,
            "ux_flaw_updated": 0,
            "ig_observation_updated": 0,
            "ig_channel_paused": False,
            "items": [],
        }

    candidates: list[dict[str, Any]] = []
    if lead_ids is not None:
        for lid in lead_ids:
            row = db.get_lead(int(lid))
            if row and row.get("status") == "NEW" and not (row.get("ig_observation") or "").strip():
                candidates.append(row)
    else:
        for row in db.list_leads(statuses=["NEW"], limit=limit):
            if not (row.get("ig_observation") or "").strip():
                candidates.append(row)

    total = len(candidates)
    ig_paused = False
    updated_count = 0
    ux_updated = 0
    ig_updated = 0
    results: list[dict[str, Any]] = []

    for idx, lead in enumerate(candidates, start=1):
        if progress_cb:
            try:
                progress_cb(idx, total, lead)
            except Exception:
                pass
        res = enrich_new_lead(
            lead["id"],
            ig_channel_blocked=ig_paused,
            runner=runner,
            timeout=timeout,
        )
        if res.get("stop_ig_channel"):
            ig_paused = True
        if res.get("enriched"):
            updated_count += 1
            fields = res.get("updated_fields") or []
            if "ux_flaw" in fields:
                ux_updated += 1
            if "ig_observation" in fields:
                ig_updated += 1
        results.append(res)

    return {
        "available": True,
        "processed": total,
        "updated": updated_count,
        "ux_flaw_updated": ux_updated,
        "ig_observation_updated": ig_updated,
        "ig_channel_paused": ig_paused,
        "items": results,
    }
