"""Review & Publish Workflow Engine for RECYCLED_CONTENT Instagram Assets (@goandalan).

Provides:
- Strict anonymization leak checker (`check_anonymization_leak`)
- Byte-identical versioned asset snapshots (`site/demos/{anon_slug}/reviews/{lead_id}/v{n}/`)
- Transactional review state machine (`pending_review`, `changes_requested`, `revised`, `approved`, `posted`)
- Selective & single-asset downloads strictly from `approved_version`
- Overwrite guard preventing `/recycle` from clobbering `approved`/`posted` content
"""

from __future__ import annotations

import io
import json
import re
import shutil
import sqlite3
import zipfile
from pathlib import Path
from typing import Any

from PIL import Image

import database as db
from config import settings


ASSET_KEY_TO_FILENAME: dict[str, str] = {
    "slide-1": "slide-1.png",
    "slide-2": "slide-2.png",
    "slide-3": "slide-3.png",
    "slide-4": "slide-4.png",
    "contact_sheet": "contact_sheet.png",
    "concept_preview": "concept_preview.png",
    "reels_video": "reels.mp4",
    "cover_reels": "cover_reels.png",
}

ASSET_LABELS: dict[str, str] = {
    "slide-1": "Slide 1",
    "slide-2": "Slide 2",
    "slide-3": "Slide 3",
    "slide-4": "Slide 4",
    "contact_sheet": "Contact Sheet 2×2",
    "concept_preview": "Concept Preview",
    "reels_video": "Video Reels 9:16 (MP4)",
    "cover_reels": "Cover Reels 9:16 (PNG)",
}

ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "draft_brief": {"pending_review"},
    "pending_review": {"approved", "changes_requested", "revised", "pending_review"},
    "changes_requested": {"revised", "pending_review"},
    "revised": {"approved", "changes_requested", "revised", "pending_review"},
    "approved": {"posted", "changes_requested", "revised"},
    "posted": set(),
}

VALID_CONTENT_FORMATS = {"carousel", "reels"}
VALID_CAROUSEL_SEQUENCES = {"auto", "campaign_to_website", "reveal_first", "story_led"}
VALID_REELS_SEQUENCES = {"auto", "scroll_reveal_showcase", "before_after_ux", "kinetic_editorial"}
VALID_VOICE_IDS = {"auto", "V1", "V2", "V3", "V4", "V5", "V6"}
VALID_HOOK_PATTERNS = {"auto", "HOOK-Q1", "HOOK-K1", "HOOK-D1", "HOOK-B1", "HOOK-N1", "HOOK-L1"}
VALID_AUDIO_MODES = {"voiceover_and_music", "voiceover_only", "music_only", "silent"}


class ReviewError(Exception):
    status_code: int = 400


class ReviewNotFoundError(ReviewError):
    status_code: int = 404


class ReviewValidationError(ReviewError):
    status_code: int = 400


class ReviewConflictError(ReviewError):
    status_code: int = 409


class AnonymizationLeakError(ReviewError):
    status_code: int = 422

    def __init__(self, message: str, leak_report: dict[str, Any]) -> None:
        super().__init__(message)
        self.leak_report = leak_report


def _anon_name(lead: dict[str, Any]) -> str:
    name = (lead.get("anonymized_name") or "").strip()
    if name:
        return name
    return f"Konsep Lokal #{lead['id']}"


def _anon_slug(lead: dict[str, Any]) -> str:
    return db.slugify(_anon_name(lead))


def _split_caption_hashtags(raw_caption: str) -> tuple[str, str]:
    text = (raw_caption or "").strip()
    if not text:
        return "", ""
    lines = text.splitlines()
    last_non_empty = len(lines) - 1
    while last_non_empty >= 0 and not lines[last_non_empty].strip():
        last_non_empty -= 1
    if last_non_empty >= 0:
        tail = lines[last_non_empty].strip()
        tokens = tail.split()
        if tokens and all(tok.startswith("#") for tok in tokens):
            body = "\n".join(lines[:last_non_empty]).strip()
            return body, tail
    return text, ""


def _phone_variants(phone_raw: str, phone_wa: str) -> list[str]:
    variants: set[str] = set()
    for raw in (phone_raw or "", phone_wa or ""):
        digits = re.sub(r"\D+", "", raw)
        if len(digits) < 8:
            continue
        variants.add(digits)
        if digits.startswith("62") and len(digits) >= 10:
            variants.add("0" + digits[2:])
            variants.add(digits[2:])
        elif digits.startswith("0") and len(digits) >= 9:
            variants.add("62" + digits[1:])
            variants.add(digits[1:])
    return sorted(v for v in variants if len(v) >= 8)


def _extract_slide_texts_from_spec(ig_dir: Path) -> list[str]:
    texts: list[str] = []
    spec_path = ig_dir / "carousel_spec.json"
    if spec_path.exists():
        try:
            spec = json.loads(spec_path.read_text(encoding="utf-8"))
            for slide in spec.get("slides") or []:
                for k in ("kicker", "headline_html", "subhead", "poster_statement", "poster_display_top", "poster_display_bottom"):
                    v = slide.get(k)
                    if isinstance(v, str) and v.strip():
                        texts.append(re.sub(r"<[^>]+>", "", v))
                for pt in slide.get("walkthrough_points") or []:
                    texts.append(f"{pt.get('title', '')} {pt.get('desc', '')}")
                for hl in slide.get("story_highlights") or []:
                    if isinstance(hl, (list, tuple)):
                        texts.append(" ".join(str(x) for x in hl))
        except Exception:
            pass
    return texts


def check_anonymization_leak(
    lead: dict[str, Any],
    caption: str,
    hashtags: str = "",
    slide_texts: list[str] | None = None,
) -> dict[str, Any]:
    """Detect real business_name, phone/WA variants (08.../628...), or real address in anonymized content."""
    leaks: list[dict[str, str]] = []
    anon = (lead.get("anonymized_name") or "").strip().lower()
    real_name = (lead.get("business_name") or "").strip()
    real_addr = (lead.get("address") or "").strip()
    phone_vars = _phone_variants(lead.get("phone_raw") or "", lead.get("phone_wa") or "")

    surfaces: list[tuple[str, str]] = [
        ("caption", caption or ""),
        ("hashtags", hashtags or ""),
    ]
    for idx, st in enumerate(slide_texts or [], start=1):
        surfaces.append((f"slide_text_{idx}", str(st or "")))

    addr_candidates: list[str] = []
    if real_addr and "disamarkan" not in real_addr.lower():
        if len(real_addr) >= 8:
            addr_candidates.append(real_addr)
        first_seg = real_addr.split(",")[0].strip()
        if len(first_seg) >= 8 and first_seg != real_addr:
            addr_candidates.append(first_seg)

    for loc, text in surfaces:
        if not text:
            continue
        low = text.lower()
        digits_only = re.sub(r"\D+", "", text)

        if real_name and real_name.lower() != anon and real_name.lower() in low:
            leaks.append({"field": "business_name", "match": real_name, "location": loc})

        for pv in phone_vars:
            if pv in digits_only:
                leaks.append({"field": "phone_wa", "match": pv, "location": loc})
                break

        for ac in addr_candidates:
            if ac.lower() in low:
                leaks.append({"field": "address", "match": ac, "location": loc})
                break

    return {
        "passed": len(leaks) == 0,
        "leaks": leaks,
        "checked_at": db.iso_now(),
    }


def _raise_if_leak(leak_report: dict[str, Any]) -> None:
    if leak_report.get("passed"):
        return
    details = ", ".join(
        f"{item['field']} pada {item['location']}" for item in leak_report.get("leaks") or []
    )
    raise AnonymizationLeakError(
        f"Terdeteksi kebocoran data asli bisnis ({details}). Hapus seluruh nama bisnis asli, nomor WA/telepon, dan alamat asli sebelum melanjutkan.",
        leak_report=leak_report,
    )


def _discover_live_slide_files(ig_dir: Path) -> list[Path]:
    """Read actual ordered 4 slide PNG paths respecting P4 dynamic naming (`carousel_spec.json`)."""
    spec_path = ig_dir / "carousel_spec.json"
    ordered: list[Path] = []
    if spec_path.exists():
        try:
            spec = json.loads(spec_path.read_text(encoding="utf-8"))
            for s in spec.get("slides") or []:
                sname = s.get("name")
                if sname:
                    cand = ig_dir / f"{sname}.png"
                    if cand.exists():
                        ordered.append(cand)
        except Exception:
            ordered = []
    if len(ordered) == 4:
        return ordered

    fallback = sorted(ig_dir.glob("0[1-4]_*.png"))
    if len(fallback) >= 4:
        return fallback[:4]
    return ordered or fallback


def _snapshot_dir(lead: dict[str, Any], version_number: int) -> Path:
    return settings.DEMOS_DIR / _anon_slug(lead) / "reviews" / str(lead["id"]) / f"v{version_number}"


def _copy_live_assets_to_snapshot(lead: dict[str, Any], target_dir: Path) -> dict[str, Any]:
    """Copy actual rendered PNGs byte-for-byte (zero recompression) into versioned snapshot folder."""
    live_demo_dir = settings.DEMOS_DIR / lead["slug"]
    live_ig_dir = live_demo_dir / "ig"
    slide_files = _discover_live_slide_files(live_ig_dir)
    if len(slide_files) < 4:
        raise ReviewValidationError(
            f"Aset carousel tidak lengkap ({len(slide_files)}/4 slide ditemukan di {live_ig_dir}). Render ulang konten terlebih dahulu."
        )

    target_dir.mkdir(parents=True, exist_ok=True)
    for idx, src in enumerate(slide_files[:4], start=1):
        shutil.copy2(src, target_dir / f"slide-{idx}.png")

    cs_src = live_ig_dir / "contact_sheet.png"
    if cs_src.exists():
        shutil.copy2(cs_src, target_dir / "contact_sheet.png")

    cp_src = live_demo_dir / "concept_preview.png"
    if cp_src.exists():
        shutil.copy2(cp_src, target_dir / "concept_preview.png")

    raw_caption = ""
    cap_path = live_ig_dir / "caption.txt"
    if cap_path.exists():
        raw_caption = cap_path.read_text(encoding="utf-8")
    caption_body, hashtags = _split_caption_hashtags(raw_caption)

    qa_report: dict[str, Any] = {}
    qa_path = live_ig_dir / "qa_report.json"
    if qa_path.exists():
        try:
            qa_report = json.loads(qa_path.read_text(encoding="utf-8"))
        except Exception:
            qa_report = {}

    slide_texts = _extract_slide_texts_from_spec(live_ig_dir)
    return {
        "caption": caption_body,
        "hashtags": hashtags,
        "qa_report": qa_report,
        "slide_texts": slide_texts,
    }


def _safe_resolve_under_demos(candidate: Path) -> Path:
    """Prevent path traversal or symlink escape outside `settings.DEMOS_DIR`."""
    demos_root = settings.DEMOS_DIR.resolve()
    resolved = candidate.resolve()
    if not resolved.is_relative_to(demos_root):
        raise ReviewValidationError("Akses path aset di luar direktori yang diizinkan ditolak.")
    return resolved


def _has_valid_image_magic(raw_bytes: bytes) -> bool:
    if len(raw_bytes) < 12:
        return False
    if raw_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        return True
    if raw_bytes.startswith(b"\xff\xd8\xff"):
        return True
    if raw_bytes[:4] == b"RIFF" and raw_bytes[8:12] == b"WEBP":
        return True
    return False


def _save_uploaded_asset_bytes(raw_bytes: bytes, filename: str, target_png: Path) -> None:
    if len(raw_bytes) > settings.MAX_UPLOAD_BYTES:
        mb = settings.MAX_UPLOAD_BYTES // (1024 * 1024)
        raise ReviewValidationError(f"Ukuran file '{filename}' melebihi batas maksimal {mb} MB.")
    ext = Path(filename or "").suffix.lower()
    if ext not in {".png", ".jpg", ".jpeg", ".webp"}:
        raise ReviewValidationError(f"Format file '{filename}' tidak didukung. Gunakan PNG, JPG, atau WebP.")
    if not _has_valid_image_magic(raw_bytes):
        raise ReviewValidationError(f"Magic bytes file '{filename}' tidak cocok dengan gambar PNG/JPG/WebP yang valid.")
    _safe_resolve_under_demos(target_png.parent)
    try:
        with Image.open(io.BytesIO(raw_bytes)) as im:
            im.verify()
        with Image.open(io.BytesIO(raw_bytes)) as im:
            fmt = (im.format or "").upper()
            if fmt not in {"PNG", "JPEG", "WEBP"}:
                raise ReviewValidationError(f"File '{filename}' bukan gambar PNG/JPG/WebP yang valid.")
            if fmt == "PNG":
                target_png.write_bytes(raw_bytes)  # zero recompression
            else:
                im.convert("RGB").save(target_png, format="PNG")
    except ReviewValidationError:
        raise
    except Exception as exc:
        raise ReviewValidationError(f"File gambar '{filename}' rusak atau tidak dapat dibaca: {exc}") from exc


def _log_activity(
    conn: sqlite3.Connection,
    review_id: int,
    actor: str,
    action: str,
    metadata: dict[str, Any] | None = None,
) -> None:
    conn.execute(
        """
        INSERT INTO content_activity (review_id, actor, action, metadata_json, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (review_id, actor, action, json.dumps(metadata or {}, ensure_ascii=False), db.iso_now()),
    )


def _list_version_assets(lead_id: int, version_row: dict[str, Any]) -> list[dict[str, Any]]:
    sdir = settings.BASE_DIR / version_row["slides_dir"]
    vnum = int(version_row["version_number"])
    assets: list[dict[str, Any]] = []
    for key, fname in ASSET_KEY_TO_FILENAME.items():
        fpath = sdir / fname
        if fpath.exists():
            media_type = "video/mp4" if fpath.suffix.lower() == ".mp4" else "image/png"
            assets.append(
                {
                    "key": key,
                    "label": ASSET_LABELS[key],
                    "filename": fname,
                    "media_type": media_type,
                    "size_bytes": fpath.stat().st_size,
                    "preview_url": f"/api/content/{lead_id}/preview/{vnum}/{key}?v={int(fpath.stat().st_mtime)}",
                    "download_url": f"/api/content/{lead_id}/download/{key}",
                }
            )
    return assets


def _sanitize_ux_flaw_for_brief(lead: dict[str, Any], anon_name: str) -> str:
    txt = (lead.get("ux_flaw") or "").strip()
    if not txt:
        return "Tampilan informasi utama, jam operasional, dan kontak di layar HP dapat ditata lebih ringkas."
    real_name = (lead.get("business_name") or "").strip()
    if real_name and real_name.lower() != anon_name.lower():
        txt = re.sub(re.escape(real_name), anon_name, txt, flags=re.IGNORECASE)
    for pv in _phone_variants(lead.get("phone_raw") or "", lead.get("phone_wa") or ""):
        txt = txt.replace(pv, "[disamarkan]")
    return txt


def get_library_options() -> dict[str, Any]:
    """Return synchronized dropdown options + preview descriptions/swatches from typography & copy libraries."""
    from creative_agent.style_registry import STYLE_LIBRARY_12
    from creative_agent.copy_engine import VOICE_ARCHETYPES, CAPTION_HOOKS
    from reels_generator import REELS_SEQUENCE_PRESETS, AUDIO_MODE_OPTIONS

    art_directions = [
        {
            "id": "auto",
            "label": "Otomatis (Sesuai Niche)",
            "desc": "Sistem memilih arah visual, palet warna, dan pasangan font paling cocok dengan karakter industri bisnisnya.",
            "palette": ["#F6F3EC", "#EDE8DD", "#3E4E3C", "#C8552E"],
            "fonts": "Adaptif per niche",
        }
    ] + [
        {
            "id": k,
            "label": v["label"],
            "desc": v.get("direction_summary", ""),
            "palette": [
                v["palette"].get("bg", "#F6F3EC"),
                v["palette"].get("surface", "#EDE8DD"),
                v["palette"].get("accent", "#3E4E3C"),
                v["palette"].get("accent_2", "#C8552E"),
            ],
            "fonts": f"{v['font_display'].split(',')[0].strip(' \'\"')} + {v['font_body'].split(',')[0].strip(' \'\"')}",
        }
        for k, v in STYLE_LIBRARY_12.items()
    ]

    carousel_sequences = [
        {
            "id": "auto",
            "label": "Otomatis (Sesuai Niche)",
            "desc": "Menyesuaikan urutan slide paling efektif (Reveal First untuk industri formal/klinis, Campaign Poster untuk brand gaya hidup).",
            "steps": ["Slide 1: Pembuka adaptif", "Slide 2: Konteks / detail", "Slide 3: Preview Website", "Slide 4: Penutup netral"],
        },
        {
            "id": "campaign_to_website",
            "label": "Campaign Poster → Website Reveal",
            "desc": "Buka dengan poster grafis kuat untuk stop-scroll, lanjut cerita UX, lalu pamerkan website desktop & HP.",
            "steps": ["01: Poster Grafis", "02: Cerita UX", "03: Website Desktop+HP", "04: Detail Section"],
        },
        {
            "id": "reveal_first",
            "label": "Reveal First (Website di Slide 1)",
            "desc": "Langsung tampilkan mockup website nyata di slide pertama agar kredibilitas langsung terlihat tanpa basa-basi.",
            "steps": ["01: Website Desktop+HP", "02: Detail Section", "03: Poster Visual", "04: Ringkasan UX"],
        },
        {
            "id": "story_led",
            "label": "Story-Led (Manifesto → Poster → Website)",
            "desc": "Mulai dari konteks masalah & konsep antarmuka, kuatkan dengan poster kampanye, lalu buka tampilan website.",
            "steps": ["01: Konsep & Cerita", "02: Poster Visual", "03: Website Desktop+HP", "04: Detail Section"],
        },
    ]

    reels_steps_map = {
        "scroll_reveal_showcase": [
            "1) Hook tipografi kinetik (kata turun bergiliran)",
            "2) Reveal hero website asli di HP",
            "3) Scroll mobile terkontrol (easing + jeda section)",
            "4) Demo fitur nyata: tab / tombol kontak disorot",
            "5) Penutup showcase netral",
        ],
        "before_after_ux": [
            "1) Masalah UX umum (anonim, bukan klaim bisnis nyata)",
            "2) Ilustrasi mobile padat (sebelum)",
            "3) Wipe ke website konsep asli + scroll (sesudah)",
            "4) Interaksi nyata yang lebih jelas",
            "5) Penutup showcase netral",
        ],
        "kinetic_editorial": [
            "1) Pembuka tipografi raksasa",
            "2) Satu wawasan desain utama",
            "3) 3 detail antarmuka nyata (modular grid)",
            "4) Ritme scroll slow-fast-slow",
            "5) Pernyataan penutup kinetik",
        ],
    }
    reels_sequences = [
        {
            "id": "auto",
            "label": "Otomatis (Scroll Reveal)",
            "desc": "Alur Reels default: hook tipografi kinetik → reveal hero → scroll mobile terkontrol → demo fitur nyata → penutup netral @goandalan.",
            "steps": reels_steps_map["scroll_reveal_showcase"],
        }
    ] + [
        {
            "id": k,
            "label": v["label"],
            "desc": v["description"],
            "steps": reels_steps_map.get(k, reels_steps_map["scroll_reveal_showcase"]),
        }
        for k, v in REELS_SEQUENCE_PRESETS.items()
    ]

    voice_desc_map = {
        "V1": "Hangat, santai tapi sopan; cocok untuk kedai kopi, bakery, studio kreatif, dan bisnis gaya hidup.",
        "V2": "Tenang, formal, kredibel, dan bebas slang; wajib untuk klinik, hukum, arsitektur, dan B2B.",
        "V3": "Dekat, visual-oriented, dan luwes; cocok untuk barbershop, fashion, dan brand lokal urban.",
        "V4": "Rapi, profesional, berbasis struktur; cocok untuk konsultan, edukasi, dan layanan korporat.",
        "V5": "Lugas, tegas, berenergi; cocok untuk bengkel custom, gym, streetwear, dan komunitas.",
        "V6": "Ramah, bercerita, membumi; cocok untuk kuliner rumahan, wisata, villa, dan kerajinan lokal.",
    }
    voices = [
        {
            "id": "auto",
            "label": "Otomatis (Sesuai Kategori)",
            "desc": "Memilih voice V1–V6 otomatis sesuai kategori bisnis (kategori klinis/hukum otomatis dikunci formal tanpa slang).",
            "register": "auto",
        }
    ] + [
        {
            "id": k,
            "label": f"{k} — {v['name']} ({v['register']})",
            "desc": voice_desc_map.get(k, f"Gaya {v['name']} ({v['register']}), sapaan '{v['sapaan']}'."),
            "register": v["register"],
        }
        for k, v in VOICE_ARCHETYPES.items()
    ]

    hook_desc_map = {
        "HOOK-Q1": "Pertanyaan reflektif yang langsung menyentuh sudut pandang pelanggan pertama kali.",
        "HOOK-K1": "Kontras tajam yang membedakan website fungsional vs sekadar brosur digital (aman untuk formal).",
        "HOOK-D1": "Menyorot 1 detail tipografi/antarmuka spesifik yang bikin tampilan jauh lebih tenang.",
        "HOOK-B1": "Klaim tegas 3 detik pertama di layar HP untuk menahan perhatian penonton.",
        "HOOK-N1": "Memperkenalkan karakter brand fiktif secara lugas dan transparan sejak baris pertama.",
        "HOOK-L1": "Struktur angka ringkas yang merangkum isi konten dalam satu kalimat padat.",
    }
    hooks = [
        {
            "id": "auto",
            "label": "Otomatis (Rotasi Anti-Duplikat §11)",
            "desc": "Memilih pola hook terbaik secara otomatis sambil menjaga tidak ada pola yang berulang 2× berturut-turut.",
            "template": "Memilih pola hook paling sesuai kategori & riwayat 10 konten terakhir.",
        }
    ] + [
        {
            "id": h["id"],
            "label": f"{h['id']} · {h['hook_type'].replace('_', ' ').title()}",
            "desc": hook_desc_map.get(h["id"], h["hook_type"]),
            "template": h["template"],
        }
        for h in CAPTION_HOOKS
    ]
    audio_modes = [
        {"id": k, "label": v["label"], "desc": v["desc"]}
        for k, v in AUDIO_MODE_OPTIONS.items()
    ]
    motion_intensities = [
        {"id": "auto", "label": "Otomatis (Sesuai Gaya Visual & Niche)", "desc": "Menyesuaikan ritme & transisi otomatis dengan visual bisnis (kategori formal dikunci tenang tanpa overshoot)."},
        {"id": "snappy", "label": "Snappy / Graphic (Cepat & Energetik)", "desc": "Akselerasi tajam, stagger cepat, dan hold singkat. Cocok untuk street, neo-brutalist & pop."},
        {"id": "balanced", "label": "Balanced / Warm (Halus & Dinamis)", "desc": "Keseimbangan ritme natural antara scroll dan tipografi. Sangat pas untuk kafe, produk, dan retail modern."},
        {"id": "refined", "label": "Refined / Quiet (Elegan, Tenang & Tanpa Bouncing)", "desc": "Transisi sinematik tenang, penahanan baca lebih panjang, easing halus tanpa pantulan. Wajib untuk klinik, hukum, & arsitektur."},
    ]
    durations = [
        {"id": 8.0, "label": "8 Detik (Fast Paced / Hyper-Concise)", "desc": "Format kilat dengan punchline cepat, cocok untuk hook agresif dan retensi tinggi."},
        {"id": 10.0, "label": "10 Detik (Standar Showcase IG)", "desc": "Durasi optimal untuk Instagram Reels showcase: jeda baca nyaman di tiap section."},
        {"id": 12.0, "label": "12 Detik (Attract Customer · Ringkas)", "desc": "Pas untuk naskah V/O 35–42 kata dengan scroll mobile + CTA DM kata KONSEP."},
        {"id": 14.0, "label": "14 Detik (Attract Customer · Rekomendasi V/O)", "desc": "Pacing lega untuk naskah V/O 40–55 kata, BGM ducking halus, dan detail antarmuka."},
        {"id": 15.0, "label": "15 Detik (Deep Narrative / Maksimal)", "desc": "Ruang penuh untuk edukasi masalah UMKM + demonstrasi scroll HP + CTA."},
    ]
    from creative_agent import reels_intelligence as ri

    vo_styles = list(ri.VO_STYLE_OPTIONS)
    bgm_tracks = ri.list_bgm_options()
    return {
        "art_directions": art_directions,
        "carousel_sequences": carousel_sequences,
        "reels_sequences": reels_sequences,
        "voices": voices,
        "hooks": hooks,
        "audio_modes": audio_modes,
        "motion_intensities": motion_intensities,
        "durations": durations,
        "vo_styles": vo_styles,
        "bgm_tracks": bgm_tracks,
    }


def _compute_recommended_defaults(lead: dict[str, Any]) -> dict[str, str]:
    from creative_agent.niche_resolver import resolve_niche_blueprint
    from creative_agent.copy_engine import route_voice_for_lead

    bp = resolve_niche_blueprint(
        category=lead.get("category") or "Bisnis Lokal",
        business_name=lead.get("anonymized_name") or lead.get("business_name") or "",
        city=lead.get("city") or "",
    )
    routing = route_voice_for_lead(lead)
    return {
        "art_direction_preset": bp.get("carousel_style_key") or "editorial_magazine",
        "carousel_sequence": "reveal_first" if routing["caption_voice"] == "formal_editorial" else "campaign_to_website",
        "reels_sequence": "scroll_reveal_showcase",
        "voice_id": routing["voice"],
        "caption_voice": routing["caption_voice"],
        "hook_pattern_id": "HOOK-K1" if routing["caption_voice"] == "formal_editorial" else "HOOK-Q1",
    }


def _resolve_lead_id_for_content_item(item_id: int, db_path: Path | None = None) -> int:
    """Resolve `item_id` accepting either `lead_id` (standard route) or `content_reviews.id`."""
    with db.get_conn(db_path) as conn:
        by_lead = conn.execute("SELECT lead_id FROM content_reviews WHERE lead_id = ?", (item_id,)).fetchone()
        if by_lead:
            return int(by_lead["lead_id"])
        by_rev = conn.execute("SELECT lead_id FROM content_reviews WHERE id = ?", (item_id,)).fetchone()
        if by_rev:
            return int(by_rev["lead_id"])
    lead = db.get_lead(item_id, db_path=db_path)
    if lead:
        return int(lead["id"])
    raise ReviewNotFoundError(f"Item konten ID {item_id} tidak ditemukan.")


def create_draft_brief_from_recycle(
    lead_id: int,
    actor: str = "Reviewer",
    db_path: Path | None = None,
) -> dict[str, Any]:
    """Anonymize prospect metadata and create/reset a `draft_brief` entry WITHOUT rendering PNG/video."""
    lead = db.get_lead(lead_id, db_path=db_path)
    if not lead:
        raise ReviewNotFoundError(f"Lead ID {lead_id} tidak ditemukan.")

    assert_recycle_allowed(lead_id, db_path=db_path)

    import demo_generator as dg

    anon_name = (lead.get("anonymized_name") or "").strip() or dg.generate_fictional_name(lead)
    updated_lead = db.update_lead(
        lead_id,
        {
            "status": "RECYCLED_CONTENT",
            "is_anonymized": 1,
            "anonymized_name": anon_name,
            "contacted_at": None,
            "follow_up_due_at": None,
        },
        db_path=db_path,
    )
    assert updated_lead is not None

    # If a pre-existing concept.html/index.html existed on disk with real business data, sanitize it immediately
    # (pure fast HTML string rewrite — zero Playwright / PNG / video rendering!)
    demo_dir = settings.DEMOS_DIR / updated_lead["slug"]
    if (demo_dir / "concept.html").exists():
        dg.generate_concept_html_for_lead(lead_id, anonymize=True)
    if (demo_dir / "index.html").exists():
        dg.generate_full_demo_for_lead(lead_id, anonymize=True, update_status=False)

    now = db.iso_now()
    with db.get_conn(db_path) as conn:
        conn.execute("BEGIN IMMEDIATE")
        existing = conn.execute("SELECT * FROM content_reviews WHERE lead_id = ?", (lead_id,)).fetchone()
        if existing:
            if existing["review_status"] in {"approved", "posted"}:
                raise ReviewConflictError(
                    f"Konten sudah berstatus '{existing['review_status']}'. Tidak dapat diubah kembali ke draft_brief."
                )
            conn.execute(
                """
                UPDATE content_reviews
                SET review_status = 'draft_brief',
                    source = 'recycled_lead',
                    content_format = 'carousel',
                    updated_at = ?
                WHERE id = ?
                """,
                (now, existing["id"]),
            )
            review_id = existing["id"]
        else:
            cur = conn.execute(
                """
                INSERT INTO content_reviews (
                    lead_id, source, review_status,
                    content_format, art_direction_preset, sequence_type,
                    voice_id, hook_pattern_id, creative_note,
                    current_version, created_at, updated_at
                ) VALUES (?, 'recycled_lead', 'draft_brief', 'carousel', 'auto', 'auto', 'auto', 'auto', '', 0, ?, ?)
                """,
                (lead_id, now, now),
            )
            review_id = cur.lastrowid

        _log_activity(
            conn,
            review_id,
            actor,
            "draft_brief_created",
            {"anonymized_name": anon_name, "content_format": "carousel"},
        )

    detail = get_review_detail(lead_id, db_path=db_path)
    return {
        "lead": updated_lead,
        "review": detail,
        "anonymized_name": anon_name,
    }


def create_reels_ideas_briefs(
    *,
    actor: str = "Reviewer",
    topic: str = "",
    limit: int = 3,
    runner: Any = None,
    db_path: Path | None = None,
) -> dict[str, Any]:
    """Scrape real Indonesian business pain points (Agent-Reach + fallback) and create `reels` `draft_brief` cards."""
    from creative_agent import reels_intelligence as ri

    scraped = ri.scrape_reels_ideas(topic=topic, limit=limit, runner=runner, timeout=25)
    now = db.iso_now()
    created_briefs: list[dict[str, Any]] = []

    for idx, idea in enumerate(scraped.get("ideas") or [], start=1):
        import uuid as _uuid

        anon_name = str(idea.get("anon_name") or f"Konsep Reels #{idx}").strip()
        pain_code = str(idea.get("pain_code") or "PAIN-WA").strip().upper()
        reel_hook_id = str(idea.get("reel_hook_id") or "REEL-HOOK-1").strip().upper()
        uniq = _uuid.uuid4().hex[:6]
        slug_base = f"reels-{db.slugify(pain_code)}-{db.slugify(anon_name)}-{uniq}"
        synthetic_biz_name = f"{anon_name} [{pain_code}-{uniq}]"

        lead, _ = db.upsert_lead(
            {
                "slug": slug_base,
                "business_name": synthetic_biz_name,
                "anonymized_name": anon_name,
                "category": str(idea.get("category") or "Bisnis Lokal"),
                "design_style": str(idea.get("design_style") or ""),
                "city": str(idea.get("city") or settings.DEFAULT_CITY),
                "ux_flaw": str(idea.get("ux_flaw") or ""),
                "status": "RECYCLED_CONTENT",
                "source_query": f"reels_idea:{pain_code}:{idea.get('source_note') or 'bank'}",
            },
            db_path=db_path,
        )
        lead = db.update_lead(
            lead["id"],
            {
                "is_anonymized": 1,
                "anonymized_name": anon_name,
                "status": "RECYCLED_CONTENT",
            },
            db_path=db_path,
        )
        assert lead is not None

        vo_script = str(idea.get("vo_script") or "").strip()
        seq_type = str(idea.get("sequence_type") or "before_after_ux")
        if seq_type not in VALID_REELS_SEQUENCES:
            seq_type = "before_after_ux"

        with db.get_conn(db_path) as conn:
            conn.execute("BEGIN IMMEDIATE")
            existing = conn.execute("SELECT id FROM content_reviews WHERE lead_id = ?", (lead["id"],)).fetchone()
            if existing:
                review_id = existing["id"]
                conn.execute(
                    """
                    UPDATE content_reviews
                    SET source = 'reels_idea_scrape',
                        review_status = 'draft_brief',
                        content_format = 'reels',
                        sequence_type = ?,
                        vo_script = ?,
                        pain_code = ?,
                        reel_hook_id = ?,
                        updated_at = ?
                    WHERE id = ?
                    """,
                    (seq_type, vo_script, pain_code, reel_hook_id, now, review_id),
                )
            else:
                cur = conn.execute(
                    """
                    INSERT INTO content_reviews (
                        lead_id, source, review_status,
                        content_format, art_direction_preset, sequence_type,
                        voice_id, hook_pattern_id, audio_mode,
                        vo_script, vo_style, bgm_track, pain_code, reel_hook_id,
                        creative_note, current_version, created_at, updated_at
                    ) VALUES (?, 'reels_idea_scrape', 'draft_brief', 'reels', 'auto', ?, 'auto', 'auto', 'voiceover_and_music', ?, 'auto', 'auto', ?, ?, ?, 0, ?, ?)
                    """,
                    (
                        lead["id"],
                        seq_type,
                        vo_script,
                        pain_code,
                        reel_hook_id,
                        str(idea.get("hook_headline") or "")[:240],
                        now,
                        now,
                    ),
                )
                review_id = cur.lastrowid
            _log_activity(
                conn,
                review_id,
                actor,
                "reels_idea_scraped",
                {
                    "pain_code": pain_code,
                    "reel_hook_id": reel_hook_id,
                    "source_mode": scraped.get("source_mode"),
                },
            )

        created_briefs.append(get_review_detail(lead["id"], db_path=db_path))

    return {
        "ok": True,
        "source_mode": scraped.get("source_mode") or "fallback_umkm_bank",
        "query": scraped.get("query") or "",
        "compacted_scrape": scraped.get("compacted_scrape") or {},
        "created_count": len(created_briefs),
        "briefs": created_briefs,
    }


def save_posted_metrics(
    lead_id: int,
    *,
    actor: str,
    views: int = 0,
    saves: int = 0,
    shares: int = 0,
    dm_in: int = 0,
    db_path: Path | None = None,
) -> dict[str, Any]:
    """Save real Instagram post performance metrics (`views`, `saves`, `shares`, `dm_in`) on a `posted` item."""
    from creative_agent import reels_intelligence as ri
    from creative_agent import token_optimizer as topt

    lead = db.get_lead(lead_id, db_path=db_path)
    if not lead:
        raise ReviewNotFoundError(f"Lead ID {lead_id} tidak ditemukan.")

    v_cnt = max(0, int(views or 0))
    sv_cnt = max(0, int(saves or 0))
    sh_cnt = max(0, int(shares or 0))
    dm_cnt = max(0, int(dm_in or 0))
    now = db.iso_now()
    metrics_obj = {
        "views": v_cnt,
        "saves": sv_cnt,
        "shares": sh_cnt,
        "dm_in": dm_cnt,
        "updated_at": now,
        "updated_by": actor,
    }

    with db.get_conn(db_path) as conn:
        conn.execute("BEGIN IMMEDIATE")
        rev = conn.execute("SELECT * FROM content_reviews WHERE lead_id = ?", (lead_id,)).fetchone()
        if not rev:
            raise ReviewNotFoundError("Item review tidak ditemukan.")
        if rev["review_status"] != "posted":
            raise ReviewConflictError(
                f"Metrik IG hanya dapat disimpan untuk konten berstatus 'posted' (status saat ini: '{rev['review_status']}')."
            )
        conn.execute(
            "UPDATE content_reviews SET metrics_json = ?, updated_at = ? WHERE id = ?",
            (json.dumps(metrics_obj, ensure_ascii=False), now, rev["id"]),
        )
        _log_activity(conn, rev["id"], actor, "metrics_saved", metrics_obj)
        rev_dict = dict(rev)

    if (rev_dict.get("content_format") or "") == "reels":
        vo_txt = str(rev_dict.get("vo_script") or "")
        ri.log_reels_event(
            lead=lead,
            original_vo_script=vo_txt,
            final_vo_script=vo_txt,
            pain_code=str(rev_dict.get("pain_code") or ""),
            reel_hook_id=str(rev_dict.get("reel_hook_id") or ""),
            voice=str(rev_dict.get("voice_id") or ""),
            vo_style=str(rev_dict.get("vo_style") or "auto"),
            bgm_track=str(rev_dict.get("bgm_track") or "auto"),
            views=v_cnt,
            saves=sv_cnt,
            shares=sh_cnt,
            dm_in=dm_cnt,
            notes=f"posted_metrics_by:{actor}",
        )

    topt.build_learning_digest(db_path=db_path, write_file=True)
    return get_review_detail(lead_id, db_path=db_path)


def _copy_reels_live_assets_to_snapshot(lead: dict[str, Any], reels_res: dict[str, Any], target_dir: Path) -> dict[str, Any]:
    target_dir.mkdir(parents=True, exist_ok=True)
    video_path = Path(reels_res["video_path"]) if reels_res.get("video_path") else None
    cover_path = Path(reels_res["cover_path"]) if reels_res.get("cover_path") else None
    spec_obj = reels_res.get("spec") or {}

    if video_path and video_path.exists():
        shutil.copy2(video_path, target_dir / "reels.mp4")
    if cover_path and cover_path.exists():
        shutil.copy2(cover_path, target_dir / "cover_reels.png")
    if spec_obj:
        (target_dir / "reels_spec.json").write_text(json.dumps(spec_obj, indent=2, ensure_ascii=False), encoding="utf-8")

    raw_caption = reels_res.get("caption") or ""
    caption_body, hashtags = _split_caption_hashtags(raw_caption)
    return {
        "caption": caption_body,
        "hashtags": hashtags,
        "qa_report": reels_res.get("qa_report") or {},
        "slide_texts": reels_res.get("on_screen_texts") or [],
        "beat_script": reels_res.get("beat_script") or [],
        "spec": spec_obj,
    }


def generate_content_from_brief(
    item_id: int,
    *,
    actor: str,
    content_format: str = "carousel",
    art_direction_preset: str = "auto",
    sequence_type: str = "auto",
    voice_id: str = "auto",
    hook_pattern_id: str = "auto",
    audio_mode: str = "voiceover_and_music",
    motion_intensity: str = "auto",
    target_duration: float = 10.0,
    vo_script: str = "",
    vo_style: str = "auto",
    bgm_track: str = "auto",
    creative_note: str = "",
    note: str = "",
    db_path: Path | None = None,
) -> dict[str, Any]:
    """Generate Carousel or Reels from a `draft_brief` (or re-generate from `changes_requested`) into `pending_review`."""
    lead_id = _resolve_lead_id_for_content_item(item_id, db_path=db_path)
    lead = db.get_lead(lead_id, db_path=db_path)
    if not lead:
        raise ReviewNotFoundError(f"Lead ID {lead_id} tidak ditemukan.")
    if lead["status"] != "RECYCLED_CONTENT" or not int(lead.get("is_anonymized") or 0):
        raise ReviewValidationError(
            "Hanya konten teranonimisasi (RECYCLED_CONTENT) yang dapat di-generate di Tab Review Konten."
        )

    fmt = (content_format or "carousel").strip().lower()
    if fmt not in VALID_CONTENT_FORMATS:
        raise ReviewValidationError("content_format harus 'carousel' atau 'reels'.")

    ad_preset = (art_direction_preset or "auto").strip() or "auto"
    seq_type = (sequence_type or "auto").strip() or "auto"
    if fmt == "carousel" and seq_type not in VALID_CAROUSEL_SEQUENCES:
        seq_type = "auto"
    elif fmt == "reels" and seq_type not in VALID_REELS_SEQUENCES:
        seq_type = "auto"

    v_id_raw = (voice_id or "auto").strip()
    v_id = "auto" if v_id_raw.lower() in {"", "auto"} else v_id_raw.upper()
    if v_id not in VALID_VOICE_IDS:
        v_id = "auto"

    h_id_raw = (hook_pattern_id or "auto").strip()
    h_id = "auto" if h_id_raw.lower() in {"", "auto"} else h_id_raw.upper()
    if h_id not in VALID_HOOK_PATTERNS:
        h_id = "auto"

    clean_note = (creative_note or "").strip()[:300]
    eff_audio = (audio_mode or "voiceover_and_music").strip().lower()
    if eff_audio not in VALID_AUDIO_MODES:
        eff_audio = "voiceover_and_music"

    eff_motion = (motion_intensity or "auto").strip().lower()
    if eff_motion not in {"auto", "snappy", "balanced", "refined"}:
        eff_motion = "auto"

    rev = db.get_review_by_lead(lead_id, db_path=db_path)
    if rev and rev["review_status"] in {"approved", "posted"}:
        raise ReviewConflictError(
            f"Konten sudah berstatus '{rev['review_status']}'. Minta revisi terlebih dahulu sebelum generate ulang."
        )

    orig_vo_script = str((rev or {}).get("vo_script") or "").strip()
    clean_vo_script = (vo_script or "").strip()[:600] or orig_vo_script
    eff_vo_style = (vo_style or (rev or {}).get("vo_style") or "auto").strip() or "auto"
    eff_bgm_track = (bgm_track or (rev or {}).get("bgm_track") or "auto").strip() or "auto"
    pain_code = str((rev or {}).get("pain_code") or "").strip()
    reel_hook_id = str((rev or {}).get("reel_hook_id") or "").strip()
    is_attract_reels = bool((rev or {}).get("source") == "reels_idea_scrape" or pain_code)

    try:
        eff_dur = float(target_duration or (13.0 if is_attract_reels else 10.0))
    except Exception:
        eff_dur = 13.0 if is_attract_reels else 10.0
    eff_dur = max(8.0, min(45.0, eff_dur))

    next_v = (int(rev["current_version"]) + 1) if (rev and int(rev["current_version"]) >= 1) else 1
    snap_dir = _snapshot_dir(lead, next_v)
    if snap_dir.exists():
        shutil.rmtree(snap_dir, ignore_errors=True)

    config_snapshot = {
        "content_format": fmt,
        "art_direction_preset": ad_preset,
        "sequence_type": seq_type,
        "voice_id": v_id,
        "hook_pattern_id": h_id,
        "audio_mode": eff_audio if fmt == "reels" else "silent",
        "motion_intensity": eff_motion if fmt == "reels" else "auto",
        "target_duration": eff_dur if fmt == "reels" else 0.0,
        "vo_style": eff_vo_style if fmt == "reels" else "auto",
        "bgm_track": eff_bgm_track if fmt == "reels" else "auto",
        "vo_script": clean_vo_script if fmt == "reels" else "",
        "pain_code": pain_code,
        "reel_hook_id": reel_hook_id,
        "creative_note": clean_note,
    }

    try:
        if fmt == "reels":
            import reels_generator as rg
            from creative_agent import reels_intelligence as ri

            reels_res = rg.generate_reels_package_for_lead(
                lead_id,
                anonymize=True,
                art_direction_preset=None if ad_preset == "auto" else ad_preset,
                sequence_type=None if seq_type == "auto" else seq_type,
                voice_id=None if v_id == "auto" else v_id,
                hook_pattern_id=None if h_id == "auto" else h_id,
                audio_mode=eff_audio,
                creative_note=clean_note,
                target_duration=eff_dur,
                motion_intensity=None if eff_motion == "auto" else eff_motion,
                vo_script=clean_vo_script,
                vo_style=eff_vo_style,
                bgm_track=eff_bgm_track,
                pain_code=pain_code,
                reel_hook_id=reel_hook_id,
                attract_cta=is_attract_reels,
            )
            copied = _copy_reels_live_assets_to_snapshot(lead, reels_res, snap_dir)
            beat_script = copied["beat_script"]
            final_rendered_vo = str(reels_res.get("vo_script") or clean_vo_script)
            actual_dur = float(((reels_res.get("spec") or {}).get("video") or {}).get("duration_sec") or eff_dur)
            config_snapshot["target_duration"] = actual_dur
            # Zero-token deterministic edit logging for Reels V/O scripts
            if orig_vo_script or clean_vo_script:
                ri.log_reels_event(
                    lead=lead,
                    original_vo_script=orig_vo_script or final_rendered_vo,
                    final_vo_script=final_rendered_vo,
                    pain_code=pain_code,
                    reel_hook_id=reel_hook_id,
                    voice=str((reels_res.get("spec") or {}).get("voice_id") or v_id),
                    vo_style=str(reels_res.get("vo_style") or eff_vo_style),
                    bgm_track=str(reels_res.get("bgm_track") or eff_bgm_track),
                    duration_sec=actual_dur,
                    notes=f"generated_by:{actor}",
                )
            clean_vo_script = final_rendered_vo
        else:
            import carousel_generator as cg

            cg.generate_concept_package_for_lead(
                lead_id,
                anonymize=True,
                art_direction_preset=None if ad_preset == "auto" else ad_preset,
                sequence_type=None if seq_type == "auto" else seq_type,
                voice_id=None if v_id == "auto" else v_id,
                hook_pattern_id=None if h_id == "auto" else h_id,
                creative_note=clean_note,
            )
            copied = _copy_live_assets_to_snapshot(lead, snap_dir)
            beat_script = []

        leak_report = check_anonymization_leak(
            lead,
            copied["caption"],
            copied["hashtags"],
            copied["slide_texts"],
        )
        _raise_if_leak(leak_report)
    except Exception:
        shutil.rmtree(snap_dir, ignore_errors=True)
        raise

    rel_dir = str(snap_dir.relative_to(settings.BASE_DIR)).replace("\\", "/")
    now = db.iso_now()
    ver_note = (note or "").strip() or (
        f"Generate {fmt.upper()} v{next_v} (style={ad_preset}, seq={seq_type}, voice={v_id}, hook={h_id})"
    )

    with db.get_conn(db_path) as conn:
        conn.execute("BEGIN IMMEDIATE")
        fresh = conn.execute("SELECT * FROM content_reviews WHERE lead_id = ?", (lead_id,)).fetchone()
        if fresh:
            if fresh["review_status"] in {"approved", "posted"}:
                shutil.rmtree(snap_dir, ignore_errors=True)
                raise ReviewConflictError(f"Status berubah menjadi '{fresh['review_status']}'.")
            review_id = fresh["id"]
            next_review_status = "revised" if (fresh["review_status"] == "changes_requested" and next_v > 1) else "pending_review"
            conn.execute(
                """
                UPDATE content_reviews
                SET review_status = ?,
                    content_format = ?,
                    art_direction_preset = ?,
                    sequence_type = ?,
                    voice_id = ?,
                    hook_pattern_id = ?,
                    audio_mode = ?,
                    vo_script = ?,
                    vo_style = ?,
                    bgm_track = ?,
                    creative_note = ?,
                    current_version = ?,
                    approved_version = NULL,
                    approved_by = '',
                    approved_at = NULL,
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    next_review_status,
                    fmt, ad_preset, seq_type, v_id, h_id, eff_audio,
                    clean_vo_script, eff_vo_style, eff_bgm_track,
                    clean_note, next_v, now, review_id,
                ),
            )
        else:
            cur = conn.execute(
                """
                INSERT INTO content_reviews (
                    lead_id, source, review_status,
                    content_format, art_direction_preset, sequence_type,
                    voice_id, hook_pattern_id, audio_mode,
                    vo_script, vo_style, bgm_track,
                    creative_note, current_version, created_at, updated_at
                ) VALUES (?, 'recycled_lead', 'pending_review', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    lead_id, fmt, ad_preset, seq_type, v_id, h_id, eff_audio,
                    clean_vo_script, eff_vo_style, eff_bgm_track,
                    clean_note, next_v, now, now,
                ),
            )
            review_id = cur.lastrowid

        conn.execute(
            """
            INSERT INTO content_versions (
                review_id, version_number, content_format, caption, hashtags, slides_dir,
                config_json, beat_script_json, qa_report_json, leak_check_json,
                created_by, created_at, note
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                review_id,
                next_v,
                fmt,
                copied["caption"],
                copied["hashtags"],
                rel_dir,
                json.dumps(config_snapshot, ensure_ascii=False),
                json.dumps(beat_script, ensure_ascii=False),
                json.dumps(copied["qa_report"], ensure_ascii=False),
                json.dumps(leak_report, ensure_ascii=False),
                actor,
                now,
                ver_note,
            ),
        )
        _log_activity(
            conn,
            review_id,
            actor,
            "generated_content",
            {"version": next_v, **config_snapshot},
        )

    return get_review_detail(lead_id, db_path=db_path)


def assert_recycle_allowed(lead_id: int, db_path: Path | None = None) -> None:
    """Block `/recycle` with HTTP 409 if the lead's review is already `approved` or `posted`."""
    review = db.get_review_by_lead(lead_id, db_path=db_path)
    if review and review["review_status"] in {"approved", "posted"}:
        raise ReviewConflictError(
            f"Konten ini sudah berstatus '{review['review_status']}' (versi v{review['approved_version'] or review['current_version']}). "
            f"Proses /recycle diblokir agar snapshot yang sudah disetujui/diposting tidak tertimpa."
        )


def submit_for_review(
    lead_id: int,
    actor: str = "Admin",
    note: str = "Submit awal ke antrean review",
    source: str = "recycled_lead",
    db_path: Path | None = None,
) -> dict[str, Any]:
    """Create initial `v1` snapshot (`pending_review`) or new revision if already in unapproved review."""
    lead = db.get_lead(lead_id, db_path=db_path)
    if not lead:
        raise ReviewNotFoundError(f"Lead ID {lead_id} tidak ditemukan.")
    if lead["status"] != "RECYCLED_CONTENT" or not int(lead.get("is_anonymized") or 0):
        raise ReviewValidationError(
            "Hanya konten hasil daur ulang (RECYCLED_CONTENT & teranonimisasi) yang dapat masuk ke alur Review Konten."
        )

    existing = db.get_review_by_lead(lead_id, db_path=db_path)
    if existing:
        if existing["review_status"] in {"approved", "posted"}:
            raise ReviewConflictError(
                f"Konten sudah berstatus '{existing['review_status']}'. Gunakan alur revisi khusus atau ubah status terlebih dahulu."
            )
        return revise_content(
            lead_id=lead_id,
            actor=actor,
            regenerate=False,
            use_live_assets=True,
            note=note or "Update snapshot dari hasil render ulang",
            db_path=db_path,
        )

    snap_dir = _snapshot_dir(lead, 1)
    copied = _copy_live_assets_to_snapshot(lead, snap_dir)
    leak_report = check_anonymization_leak(
        lead,
        copied["caption"],
        copied["hashtags"],
        copied["slide_texts"],
    )
    if not leak_report["passed"]:
        shutil.rmtree(snap_dir, ignore_errors=True)
        _raise_if_leak(leak_report)

    rel_dir = str(snap_dir.relative_to(settings.BASE_DIR)).replace("\\", "/")
    now = db.iso_now()

    with db.get_conn(db_path) as conn:
        conn.execute("BEGIN IMMEDIATE")
        dup = conn.execute("SELECT id FROM content_reviews WHERE lead_id = ?", (lead_id,)).fetchone()
        if dup:
            raise ReviewConflictError("Konten ini sudah disubmit ke antrean review oleh sesi lain.")

        cur = conn.execute(
            """
            INSERT INTO content_reviews (
                lead_id, source, review_status, current_version,
                created_at, updated_at
            ) VALUES (?, ?, 'pending_review', 1, ?, ?)
            """,
            (lead_id, source, now, now),
        )
        review_id = cur.lastrowid
        conn.execute(
            """
            INSERT INTO content_versions (
                review_id, version_number, caption, hashtags, slides_dir,
                qa_report_json, leak_check_json, created_by, created_at, note
            ) VALUES (?, 1, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                review_id,
                copied["caption"],
                copied["hashtags"],
                rel_dir,
                json.dumps(copied["qa_report"], ensure_ascii=False),
                json.dumps(leak_report, ensure_ascii=False),
                actor,
                now,
                note,
            ),
        )
        _log_activity(conn, review_id, actor, "submitted", {"version": 1, "source": source})

    return get_review_detail(lead_id, db_path=db_path)


def request_changes(
    lead_id: int,
    actor: str,
    corrections: list[dict[str, Any]],
    expected_status: str | None = None,
    db_path: Path | None = None,
) -> dict[str, Any]:
    """Reviewer requests changes (`pending_review`/`revised`/`approved` -> `changes_requested`)."""
    cleaned = []
    for item in corrections or []:
        note = str(item.get("note") or "").strip()
        if not note:
            continue
        slide_idx = item.get("slide_index")
        if slide_idx is not None and slide_idx != "":
            slide_idx = int(slide_idx)
            if slide_idx not in {1, 2, 3, 4}:
                raise ReviewValidationError("slide_index harus antara 1 sampai 4 (atau kosong untuk catatan umum).")
        else:
            slide_idx = None
        cleaned.append({"slide_index": slide_idx, "note": note})

    if not cleaned:
        raise ReviewValidationError("Masukkan minimal satu catatan koreksi sebelum meminta revisi.")

    now = db.iso_now()
    with db.get_conn(db_path) as conn:
        conn.execute("BEGIN IMMEDIATE")
        rev = conn.execute("SELECT * FROM content_reviews WHERE lead_id = ?", (lead_id,)).fetchone()
        if not rev:
            raise ReviewNotFoundError("Item review tidak ditemukan.")
        cur_status = rev["review_status"]
        if expected_status and cur_status != expected_status:
            raise ReviewConflictError(
                f"Status konten sudah berubah menjadi '{cur_status}' oleh pengguna lain. Muat ulang halaman sebelum melanjutkan."
            )
        if "changes_requested" not in ALLOWED_TRANSITIONS.get(cur_status, set()):
            raise ReviewConflictError(
                f"Tidak dapat meminta revisi dari status '{cur_status}'."
            )

        for c in cleaned:
            conn.execute(
                """
                INSERT INTO content_corrections (
                    review_id, version_number, slide_index, note, status, created_by, created_at
                ) VALUES (?, ?, ?, ?, 'open', ?, ?)
                """,
                (rev["id"], rev["current_version"], c["slide_index"], c["note"], actor, now),
            )

        conn.execute(
            """
            UPDATE content_reviews
            SET review_status = 'changes_requested',
                approved_version = NULL,
                approved_by = '',
                approved_at = NULL,
                updated_at = ?
            WHERE id = ?
            """,
            (now, rev["id"]),
        )
        _log_activity(
            conn,
            rev["id"],
            actor,
            "changes_requested",
            {
                "from_status": cur_status,
                "version": rev["current_version"],
                "corrections_count": len(cleaned),
            },
        )

    return get_review_detail(lead_id, db_path=db_path)


def resolve_correction(
    lead_id: int,
    correction_id: int,
    actor: str,
    db_path: Path | None = None,
) -> dict[str, Any]:
    """Admin marks an open correction as resolved."""
    now = db.iso_now()
    with db.get_conn(db_path) as conn:
        conn.execute("BEGIN IMMEDIATE")
        rev = conn.execute("SELECT * FROM content_reviews WHERE lead_id = ?", (lead_id,)).fetchone()
        if not rev:
            raise ReviewNotFoundError("Item review tidak ditemukan.")
        corr = conn.execute(
            "SELECT * FROM content_corrections WHERE id = ? AND review_id = ?",
            (correction_id, rev["id"]),
        ).fetchone()
        if not corr:
            raise ReviewNotFoundError(f"Koreksi ID {correction_id} tidak ditemukan.")
        if corr["status"] == "resolved":
            return get_review_detail(lead_id, db_path=db_path)

        conn.execute(
            """
            UPDATE content_corrections
            SET status = 'resolved', resolved_by = ?, resolved_at = ?
            WHERE id = ?
            """,
            (actor, now, correction_id),
        )
        conn.execute("UPDATE content_reviews SET updated_at = ? WHERE id = ?", (now, rev["id"]))
        _log_activity(
            conn,
            rev["id"],
            actor,
            "correction_resolved",
            {"correction_id": correction_id, "slide_index": corr["slide_index"]},
        )

    return get_review_detail(lead_id, db_path=db_path)


def revise_content(
    lead_id: int,
    actor: str,
    regenerate: bool = False,
    use_live_assets: bool = False,
    uploaded_files: dict[str, tuple[str, bytes]] | None = None,
    caption: str | None = None,
    hashtags: str | None = None,
    note: str = "",
    expected_status: str | None = None,
    db_path: Path | None = None,
) -> dict[str, Any]:
    """Admin creates a new version (`v{n+1}`), revokes any prior approval, and transitions to `revised`."""
    lead = db.get_lead(lead_id, db_path=db_path)
    if not lead:
        raise ReviewNotFoundError(f"Lead ID {lead_id} tidak ditemukan.")

    rev = db.get_review_by_lead(lead_id, db_path=db_path)
    if not rev:
        raise ReviewNotFoundError("Item review tidak ditemukan. Submit terlebih dahulu.")
    if expected_status and rev["review_status"] != expected_status:
        raise ReviewConflictError(
            f"Status konten sudah berubah menjadi '{rev['review_status']}' oleh pengguna lain."
        )
    if "revised" not in ALLOWED_TRANSITIONS.get(rev["review_status"], set()):
        raise ReviewConflictError(f"Tidak dapat membuat revisi pada status '{rev['review_status']}'.")

    with db.get_conn(db_path) as conn:
        prev_ver = conn.execute(
            "SELECT * FROM content_versions WHERE review_id = ? AND version_number = ?",
            (rev["id"], rev["current_version"]),
        ).fetchone()
        if not prev_ver:
            raise ReviewNotFoundError("Versi sebelumnya tidak ditemukan.")
        prev_ver_dict = dict(prev_ver)

    next_v = int(rev["current_version"]) + 1
    next_dir = _snapshot_dir(lead, next_v)
    if next_dir.exists():
        shutil.rmtree(next_dir, ignore_errors=True)
    next_dir.mkdir(parents=True, exist_ok=True)

    cur_fmt = str(rev.get("content_format") or prev_ver_dict.get("content_format") or "carousel").lower()
    new_beat_script_json = prev_ver_dict.get("beat_script_json") or "[]"
    new_config_json = prev_ver_dict.get("config_json") or "{}"

    try:
        if regenerate:
            if cur_fmt == "reels":
                import reels_generator as rg

                ad_p = str(rev.get("art_direction_preset") or "auto")
                seq_p = str(rev.get("sequence_type") or "auto")
                v_p = str(rev.get("voice_id") or "auto")
                h_p = str(rev.get("hook_pattern_id") or "auto")
                aud_p = str(rev.get("audio_mode") or "voiceover_and_music")
                vo_s = str(rev.get("vo_script") or "")
                vo_st = str(rev.get("vo_style") or "auto")
                bgm_t = str(rev.get("bgm_track") or "auto")
                pain_c = str(rev.get("pain_code") or "")
                rh_id = str(rev.get("reel_hook_id") or "")
                reels_res = rg.generate_reels_package_for_lead(
                    lead_id,
                    anonymize=True,
                    art_direction_preset=None if ad_p == "auto" else ad_p,
                    sequence_type=None if seq_p == "auto" else seq_p,
                    voice_id=None if v_p == "auto" else v_p,
                    hook_pattern_id=None if h_p == "auto" else h_p,
                    audio_mode=aud_p,
                    creative_note=str(rev.get("creative_note") or ""),
                    vo_script=vo_s,
                    vo_style=vo_st,
                    bgm_track=bgm_t,
                    pain_code=pain_c,
                    reel_hook_id=rh_id,
                    attract_cta=bool(rev.get("source") == "reels_idea_scrape" or pain_c),
                )
                copied = _copy_reels_live_assets_to_snapshot(lead, reels_res, next_dir)
                new_caption = caption if caption is not None else copied["caption"]
                new_hashtags = hashtags if hashtags is not None else copied["hashtags"]
                new_qa = copied["qa_report"]
                slide_texts = copied["slide_texts"]
                new_beat_script_json = json.dumps(copied.get("beat_script") or [], ensure_ascii=False)
            else:
                import carousel_generator as cg

                cg.generate_concept_package_for_lead(lead_id, anonymize=True)
                copied = _copy_live_assets_to_snapshot(lead, next_dir)
                new_caption = caption if caption is not None else copied["caption"]
                new_hashtags = hashtags if hashtags is not None else copied["hashtags"]
                new_qa = copied["qa_report"]
                slide_texts = copied["slide_texts"]
        elif use_live_assets:
            copied = _copy_live_assets_to_snapshot(lead, next_dir)
            new_caption = caption if caption is not None else copied["caption"]
            new_hashtags = hashtags if hashtags is not None else copied["hashtags"]
            new_qa = copied["qa_report"]
            slide_texts = copied["slide_texts"]
        else:
            prev_dir = settings.BASE_DIR / prev_ver_dict["slides_dir"]
            for fname in ASSET_KEY_TO_FILENAME.values():
                src = prev_dir / fname
                if src.exists():
                    shutil.copy2(src, next_dir / fname)
            for extra_json in ("reels_spec.json",):
                src_j = prev_dir / extra_json
                if src_j.exists():
                    shutil.copy2(src_j, next_dir / extra_json)
            for asset_key, (fname, raw_bytes) in (uploaded_files or {}).items():
                if asset_key not in ASSET_KEY_TO_FILENAME:
                    raise ReviewValidationError(f"Asset key tidak valid: {asset_key}")
                _save_uploaded_asset_bytes(raw_bytes, fname, next_dir / ASSET_KEY_TO_FILENAME[asset_key])
            new_caption = caption if caption is not None else prev_ver_dict["caption"]
            new_hashtags = hashtags if hashtags is not None else prev_ver_dict["hashtags"]
            try:
                new_qa = json.loads(prev_ver_dict.get("qa_report_json") or "{}")
            except Exception:
                new_qa = {}
            slide_texts = _extract_slide_texts_from_spec(settings.DEMOS_DIR / lead["slug"] / "ig")

        # If hashtags passed embedded in caption and hashtags not separately set, normalize cleanly
        if caption is not None and hashtags is None:
            new_caption, extracted_tags = _split_caption_hashtags(new_caption)
            if extracted_tags:
                new_hashtags = extracted_tags

        leak_report = check_anonymization_leak(lead, new_caption, new_hashtags, slide_texts)
        _raise_if_leak(leak_report)
    except Exception:
        shutil.rmtree(next_dir, ignore_errors=True)
        raise

    rel_dir = str(next_dir.relative_to(settings.BASE_DIR)).replace("\\", "/")
    now = db.iso_now()

    with db.get_conn(db_path) as conn:
        conn.execute("BEGIN IMMEDIATE")
        fresh = conn.execute("SELECT * FROM content_reviews WHERE id = ?", (rev["id"],)).fetchone()
        if not fresh:
            raise ReviewNotFoundError("Item review tidak ditemukan.")
        if expected_status and fresh["review_status"] != expected_status:
            shutil.rmtree(next_dir, ignore_errors=True)
            raise ReviewConflictError(
                f"Status konten berubah menjadi '{fresh['review_status']}' sebelum revisi tersimpan."
            )
        if int(fresh["current_version"]) != int(rev["current_version"]):
            shutil.rmtree(next_dir, ignore_errors=True)
            raise ReviewConflictError("Versi baru sudah dibuat oleh sesi lain. Muat ulang halaman lalu coba lagi.")
        if "revised" not in ALLOWED_TRANSITIONS.get(fresh["review_status"], set()):
            shutil.rmtree(next_dir, ignore_errors=True)
            raise ReviewConflictError(f"Tidak dapat merevisi konten pada status '{fresh['review_status']}'.")

        revoked_approval = fresh["review_status"] == "approved"
        conn.execute(
            """
            INSERT INTO content_versions (
                review_id, version_number, content_format, caption, hashtags, slides_dir,
                config_json, beat_script_json, qa_report_json, leak_check_json, created_by, created_at, note
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                fresh["id"],
                next_v,
                cur_fmt,
                new_caption,
                new_hashtags,
                rel_dir,
                new_config_json,
                new_beat_script_json,
                json.dumps(new_qa, ensure_ascii=False),
                json.dumps(leak_report, ensure_ascii=False),
                actor,
                now,
                note or f"Revisi versi v{next_v}",
            ),
        )
        conn.execute(
            """
            UPDATE content_reviews
            SET review_status = 'revised',
                current_version = ?,
                approved_version = NULL,
                approved_by = '',
                approved_at = NULL,
                updated_at = ?
            WHERE id = ?
            """,
            (next_v, now, fresh["id"]),
        )
        _log_activity(
            conn,
            fresh["id"],
            actor,
            "revised",
            {
                "version": next_v,
                "regenerate": regenerate,
                "uploaded_keys": sorted((uploaded_files or {}).keys()),
                "revoked_previous_approval": revoked_approval,
                "note": note,
            },
        )

    return get_review_detail(lead_id, db_path=db_path)


def approve_content(
    lead_id: int,
    actor: str,
    expected_status: str | None = None,
    expected_version: int | None = None,
    db_path: Path | None = None,
) -> dict[str, Any]:
    """Reviewer approves the current version (`pending_review` or `revised` -> `approved`)."""
    now = db.iso_now()
    with db.get_conn(db_path) as conn:
        conn.execute("BEGIN IMMEDIATE")
        rev = conn.execute("SELECT * FROM content_reviews WHERE lead_id = ?", (lead_id,)).fetchone()
        if not rev:
            raise ReviewNotFoundError("Item review tidak ditemukan.")
        cur_status = rev["review_status"]
        cur_v = int(rev["current_version"])
        if expected_status and cur_status != expected_status:
            raise ReviewConflictError(
                f"Status konten sudah berubah menjadi '{cur_status}' oleh pengguna lain."
            )
        if expected_version is not None and cur_v != int(expected_version):
            raise ReviewConflictError(
                f"Versi konten sudah diperbarui ke v{cur_v}. Tinjau versi terbaru sebelum menyetujui."
            )
        if "approved" not in ALLOWED_TRANSITIONS.get(cur_status, set()):
            raise ReviewConflictError(
                f"Konten berstatus '{cur_status}' tidak dapat langsung disetujui."
            )

        ver = conn.execute(
            "SELECT * FROM content_versions WHERE review_id = ? AND version_number = ?",
            (rev["id"], cur_v),
        ).fetchone()
        if not ver:
            raise ReviewNotFoundError(f"Snapshot versi v{cur_v} tidak ditemukan.")
        try:
            leak = json.loads(ver["leak_check_json"] or "{}")
        except Exception:
            leak = {"passed": False}
        if not leak.get("passed", False):
            raise AnonymizationLeakError(
                "Konten tidak dapat disetujui karena pemeriksaan kebocoran anonimisasi belum lolos.",
                leak_report=leak,
            )

        conn.execute(
            """
            UPDATE content_reviews
            SET review_status = 'approved',
                approved_version = ?,
                approved_by = ?,
                approved_at = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (cur_v, actor, now, now, rev["id"]),
        )
        _log_activity(conn, rev["id"], actor, "approved", {"approved_version": cur_v})

    return get_review_detail(lead_id, db_path=db_path)


def mark_posted(
    lead_id: int,
    actor: str,
    posted_url: str = "",
    posted_at: str | None = None,
    expected_status: str | None = None,
    db_path: Path | None = None,
) -> dict[str, Any]:
    """Reviewer marks an `approved` item as `posted`."""
    now = db.iso_now()
    ts_posted = (posted_at or "").strip() or now
    clean_url = (posted_url or "").strip()

    with db.get_conn(db_path) as conn:
        conn.execute("BEGIN IMMEDIATE")
        rev = conn.execute("SELECT * FROM content_reviews WHERE lead_id = ?", (lead_id,)).fetchone()
        if not rev:
            raise ReviewNotFoundError("Item review tidak ditemukan.")
        cur_status = rev["review_status"]
        if expected_status and cur_status != expected_status:
            raise ReviewConflictError(
                f"Status konten sudah berubah menjadi '{cur_status}' oleh pengguna lain."
            )
        if cur_status != "approved":
            raise ReviewConflictError(
                f"Hanya konten berstatus 'approved' yang dapat ditandai sudah diposting (status saat ini: '{cur_status}')."
            )

        conn.execute(
            """
            UPDATE content_reviews
            SET review_status = 'posted',
                posted_at = ?,
                posted_url = ?,
                posted_by = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (ts_posted, clean_url, actor, now, rev["id"]),
        )
        _log_activity(
            conn,
            rev["id"],
            actor,
            "marked_posted",
            {"approved_version": rev["approved_version"], "posted_url": clean_url, "posted_at": ts_posted},
        )

    return get_review_detail(lead_id, db_path=db_path)


def add_comment(
    lead_id: int,
    author: str,
    role: str,
    body: str,
    db_path: Path | None = None,
) -> dict[str, Any]:
    text = (body or "").strip()
    if not text:
        raise ReviewValidationError("Isi komentar tidak boleh kosong.")
    now = db.iso_now()
    with db.get_conn(db_path) as conn:
        conn.execute("BEGIN IMMEDIATE")
        rev = conn.execute("SELECT id FROM content_reviews WHERE lead_id = ?", (lead_id,)).fetchone()
        if not rev:
            raise ReviewNotFoundError("Item review tidak ditemukan.")
        conn.execute(
            """
            INSERT INTO content_comments (review_id, author, role, body, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (rev["id"], author, role, text, now),
        )
        conn.execute("UPDATE content_reviews SET updated_at = ? WHERE id = ?", (now, rev["id"]))
        _log_activity(conn, rev["id"], author, "comment_added", {"role": role})
    return get_review_detail(lead_id, db_path=db_path)


def record_caption_copied(
    lead_id: int,
    actor: str,
    db_path: Path | None = None,
) -> dict[str, Any]:
    """Return full copyable caption strictly from `approved_version` when approved/posted, and log copy event."""
    with db.get_conn(db_path) as conn:
        conn.execute("BEGIN IMMEDIATE")
        rev = conn.execute("SELECT * FROM content_reviews WHERE lead_id = ?", (lead_id,)).fetchone()
        if not rev:
            raise ReviewNotFoundError("Item review tidak ditemukan.")
        target_v = (
            int(rev["approved_version"])
            if rev["review_status"] in {"approved", "posted"} and rev["approved_version"]
            else int(rev["current_version"])
        )
        ver = conn.execute(
            "SELECT caption, hashtags FROM content_versions WHERE review_id = ? AND version_number = ?",
            (rev["id"], target_v),
        ).fetchone()
        if not ver:
            raise ReviewNotFoundError(f"Versi v{target_v} tidak ditemukan.")
        _log_activity(conn, rev["id"], actor, "caption_copied", {"version": target_v})

    cap = ver["caption"] or ""
    tags = ver["hashtags"] or ""
    full_text = f"{cap}\n\n{tags}".strip() if tags else cap
    return {
        "ok": True,
        "version": target_v,
        "caption": cap,
        "hashtags": tags,
        "full_caption": full_text,
    }


def resolve_preview_asset(
    lead_id: int,
    version_number: int,
    asset_key: str,
    db_path: Path | None = None,
) -> Path:
    if asset_key not in ASSET_KEY_TO_FILENAME:
        raise ReviewNotFoundError("Aset tidak dikenal.")
    with db.get_conn(db_path) as conn:
        rev = conn.execute("SELECT id FROM content_reviews WHERE lead_id = ?", (lead_id,)).fetchone()
        if not rev:
            raise ReviewNotFoundError("Item review tidak ditemukan.")
        ver = conn.execute(
            "SELECT slides_dir FROM content_versions WHERE review_id = ? AND version_number = ?",
            (rev["id"], version_number),
        ).fetchone()
        if not ver:
            raise ReviewNotFoundError(f"Versi v{version_number} tidak ditemukan.")
    fpath = _safe_resolve_under_demos(settings.BASE_DIR / ver["slides_dir"] / ASSET_KEY_TO_FILENAME[asset_key])
    if not fpath.exists():
        raise ReviewNotFoundError(f"File aset '{asset_key}' tidak tersedia pada v{version_number}.")
    return fpath


def resolve_approved_download_asset(
    lead_id: int,
    asset_key: str,
    actor: str,
    db_path: Path | None = None,
) -> tuple[Path, str]:
    """Return `(file_path, download_filename)` strictly from `approved_version` & log activity."""
    if asset_key not in ASSET_KEY_TO_FILENAME:
        raise ReviewValidationError(f"Kunci aset tidak valid: '{asset_key}'.")

    lead = db.get_lead(lead_id, db_path=db_path)
    if not lead:
        raise ReviewNotFoundError("Lead tidak ditemukan.")

    with db.get_conn(db_path) as conn:
        conn.execute("BEGIN IMMEDIATE")
        rev = conn.execute("SELECT * FROM content_reviews WHERE lead_id = ?", (lead_id,)).fetchone()
        if not rev:
            raise ReviewNotFoundError("Item review tidak ditemukan.")
        if rev["review_status"] != "approved" or not rev["approved_version"]:
            raise ReviewConflictError(
                f"Download aset hanya tersedia saat status 'approved' (status saat ini: '{rev['review_status']}')."
            )
        app_v = int(rev["approved_version"])
        ver = conn.execute(
            "SELECT slides_dir FROM content_versions WHERE review_id = ? AND version_number = ?",
            (rev["id"], app_v),
        ).fetchone()
        if not ver:
            raise ReviewNotFoundError(f"Snapshot versi approved v{app_v} tidak ditemukan.")

        fpath = _safe_resolve_under_demos(settings.BASE_DIR / ver["slides_dir"] / ASSET_KEY_TO_FILENAME[asset_key])
        if not fpath.exists():
            raise ReviewNotFoundError(f"Aset '{asset_key}' tidak tersedia pada versi v{app_v}.")

        _log_activity(conn, rev["id"], actor, "asset_downloaded", {"version": app_v, "asset_key": asset_key})

    ext = fpath.suffix.lower() or ".png"
    download_name = f"{_anon_slug(lead)}_v{app_v}_{asset_key}{ext}"
    return fpath, download_name


def build_approved_zip_bytes(
    lead_id: int,
    items: list[str] | None,
    actor: str,
    db_path: Path | None = None,
) -> tuple[bytes, str]:
    """Package selected (or all) assets strictly from `approved_version` into a ZIP without recompression."""
    lead = db.get_lead(lead_id, db_path=db_path)
    if not lead:
        raise ReviewNotFoundError("Lead tidak ditemukan.")

    with db.get_conn(db_path) as conn:
        conn.execute("BEGIN IMMEDIATE")
        rev = conn.execute("SELECT * FROM content_reviews WHERE lead_id = ?", (lead_id,)).fetchone()
        if not rev:
            raise ReviewNotFoundError("Item review tidak ditemukan.")
        if rev["review_status"] != "approved" or not rev["approved_version"]:
            raise ReviewConflictError(
                f"Download ZIP hanya tersedia saat status 'approved' (status saat ini: '{rev['review_status']}')."
            )
        app_v = int(rev["approved_version"])
        ver = conn.execute(
            "SELECT slides_dir FROM content_versions WHERE review_id = ? AND version_number = ?",
            (rev["id"], app_v),
        ).fetchone()
        if not ver:
            raise ReviewNotFoundError(f"Snapshot versi approved v{app_v} tidak ditemukan.")

        sdir = _safe_resolve_under_demos(settings.BASE_DIR / ver["slides_dir"])
        requested = [x.strip() for x in (items or []) if x.strip()]
        if requested:
            for k in requested:
                if k not in ASSET_KEY_TO_FILENAME:
                    raise ReviewValidationError(f"Item ZIP tidak valid: '{k}'.")
            selected_keys = requested
        else:
            selected_keys = [k for k, fn in ASSET_KEY_TO_FILENAME.items() if (sdir / fn).exists()]

        buf = io.BytesIO()
        included: list[str] = []
        slug = _anon_slug(lead)
        with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_STORED) as zf:
            for k in selected_keys:
                fpath = sdir / ASSET_KEY_TO_FILENAME[k]
                if fpath.exists():
                    ext = fpath.suffix.lower() or ".png"
                    zf.write(fpath, arcname=f"{slug}_v{app_v}_{k}{ext}")
                    included.append(k)

        if not included:
            raise ReviewValidationError("Tidak ada file aset yang cocok untuk dikemas ke ZIP.")

        _log_activity(conn, rev["id"], actor, "zip_downloaded", {"version": app_v, "items": included})

    return buf.getvalue(), f"{slug}_v{app_v}.zip"


def list_review_queue(
    status_filter: str | None = None,
    db_path: Path | None = None,
) -> dict[str, Any]:
    """Return anonymized review queue items & summary counts (ZERO real business fields exposed)."""
    with db.get_conn(db_path) as conn:
        rows = conn.execute(
            """
            SELECT r.*, l.anonymized_name, l.business_name, l.category, l.city, l.design_style, l.ux_flaw, l.phone_raw, l.phone_wa
            FROM content_reviews r
            JOIN leads l ON l.id = r.lead_id
            ORDER BY
                CASE r.review_status
                    WHEN 'draft_brief' THEN 0
                    WHEN 'changes_requested' THEN 1
                    WHEN 'revised' THEN 2
                    WHEN 'pending_review' THEN 3
                    WHEN 'approved' THEN 4
                    WHEN 'posted' THEN 5
                    ELSE 6
                END,
                r.updated_at DESC
            """
        ).fetchall()

        items: list[dict[str, Any]] = []
        open_corrections_all: list[dict[str, Any]] = []
        for r in rows:
            rd = dict(r)
            if status_filter and rd["review_status"] != status_filter:
                continue
            lead_stub = {
                "id": rd["lead_id"],
                "anonymized_name": rd["anonymized_name"],
                "business_name": rd["business_name"],
                "category": rd["category"],
                "city": rd["city"],
                "ux_flaw": rd["ux_flaw"],
                "phone_raw": rd["phone_raw"],
                "phone_wa": rd["phone_wa"],
            }
            anon_name = _anon_name(lead_stub)
            anon_slug = _anon_slug(lead_stub)

            display_v = (
                int(rd["approved_version"])
                if rd["review_status"] in {"approved", "posted"} and rd["approved_version"]
                else int(rd["current_version"])
            )
            ver = (
                conn.execute(
                    "SELECT * FROM content_versions WHERE review_id = ? AND version_number = ?",
                    (rd["id"], display_v),
                ).fetchone()
                if display_v > 0
                else None
            )
            ver_dict = dict(ver) if ver else {}
            assets = _list_version_assets(rd["lead_id"], ver_dict) if ver_dict else []
            cover_asset = next((a for a in assets if a["key"] == "cover_reels"), None)
            first_img_asset = next((a for a in assets if a.get("media_type", "").startswith("image/")), None)
            thumb_url = (cover_asset or first_img_asset or {}).get("preview_url", "")

            corrs = [
                dict(c)
                for c in conn.execute(
                    "SELECT * FROM content_corrections WHERE review_id = ? ORDER BY id DESC",
                    (rd["id"],),
                ).fetchall()
            ]
            open_corrs = [c for c in corrs if c["status"] == "open"]
            for oc in open_corrs:
                open_corrections_all.append(
                    {
                        **oc,
                        "lead_id": rd["lead_id"],
                        "anon_name": anon_name,
                        "review_status": rd["review_status"],
                    }
                )

            try:
                qa_obj = json.loads(ver_dict.get("qa_report_json") or "{}")
            except Exception:
                qa_obj = {}
            try:
                leak_obj = json.loads(ver_dict.get("leak_check_json") or "{}")
            except Exception:
                leak_obj = {"passed": True, "leaks": []}
            try:
                metrics_obj = json.loads(rd.get("metrics_json") or "{}")
            except Exception:
                metrics_obj = {}

            items.append(
                {
                    "review_id": rd["id"],
                    "lead_id": rd["lead_id"],
                    "source": rd["source"],
                    "anon_name": anon_name,
                    "anon_slug": anon_slug,
                    "category": rd["category"],
                    "city": rd["city"],
                    "design_style": rd["design_style"],
                    "ux_flaw_sanitized": _sanitize_ux_flaw_for_brief(lead_stub, anon_name),
                    "review_status": rd["review_status"],
                    "content_format": rd.get("content_format") or "carousel",
                    "art_direction_preset": rd.get("art_direction_preset") or "auto",
                    "sequence_type": rd.get("sequence_type") or "auto",
                    "voice_id": rd.get("voice_id") or "auto",
                    "hook_pattern_id": rd.get("hook_pattern_id") or "auto",
                    "audio_mode": rd.get("audio_mode") or "voiceover_and_music",
                    "vo_script": rd.get("vo_script") or "",
                    "vo_style": rd.get("vo_style") or "auto",
                    "bgm_track": rd.get("bgm_track") or "auto",
                    "pain_code": rd.get("pain_code") or "",
                    "reel_hook_id": rd.get("reel_hook_id") or "",
                    "metrics": {
                        "views": int(metrics_obj.get("views") or 0),
                        "saves": int(metrics_obj.get("saves") or 0),
                        "shares": int(metrics_obj.get("shares") or 0),
                        "dm_in": int(metrics_obj.get("dm_in") or 0),
                        "updated_at": metrics_obj.get("updated_at") or "",
                    },
                    "creative_note": rd.get("creative_note") or "",
                    "recommended_defaults": _compute_recommended_defaults(lead_stub),
                    "current_version": int(rd["current_version"]),
                    "approved_version": rd["approved_version"],
                    "approved_by": rd["approved_by"],
                    "approved_at": rd["approved_at"],
                    "posted_at": rd["posted_at"],
                    "posted_url": rd["posted_url"],
                    "posted_by": rd["posted_by"],
                    "updated_at": rd["updated_at"],
                    "thumbnail_url": thumb_url,
                    "open_corrections_count": len(open_corrs),
                    "qa_status": qa_obj.get("status", ""),
                    "qa_score": qa_obj.get("score"),
                    "leak_passed": bool(leak_obj.get("passed", True)),
                }
            )

    return {
        "counts": db.get_review_counts(db_path=db_path),
        "items": items,
        "open_corrections": open_corrections_all,
        "library_options": get_library_options(),
    }


def get_review_detail(lead_id: int, db_path: Path | None = None) -> dict[str, Any]:
    """Return full strictly anonymized review detail, version snapshots, corrections, comments & activity."""
    with db.get_conn(db_path) as conn:
        row = conn.execute(
            """
            SELECT r.*, l.anonymized_name, l.business_name, l.category, l.city, l.design_style, l.ux_flaw, l.phone_raw, l.phone_wa
            FROM content_reviews r
            JOIN leads l ON l.id = r.lead_id
            WHERE r.lead_id = ?
            """,
            (lead_id,),
        ).fetchone()
        if not row:
            raise ReviewNotFoundError(f"Review untuk lead ID {lead_id} tidak ditemukan.")
        rd = dict(row)
        lead_stub = {
            "id": rd["lead_id"],
            "anonymized_name": rd["anonymized_name"],
            "business_name": rd["business_name"],
            "category": rd["category"],
            "city": rd["city"],
            "ux_flaw": rd["ux_flaw"],
            "phone_raw": rd["phone_raw"],
            "phone_wa": rd["phone_wa"],
        }
        anon_name = _anon_name(lead_stub)
        anon_slug = _anon_slug(lead_stub)

        ver_rows = conn.execute(
            "SELECT * FROM content_versions WHERE review_id = ? ORDER BY version_number ASC",
            (rd["id"],),
        ).fetchall()
        versions: list[dict[str, Any]] = []
        for vr in ver_rows:
            vd = dict(vr)
            try:
                qa_obj = json.loads(vd.get("qa_report_json") or "{}")
            except Exception:
                qa_obj = {}
            try:
                leak_obj = json.loads(vd.get("leak_check_json") or "{}")
            except Exception:
                leak_obj = {"passed": True, "leaks": []}
            try:
                cfg_obj = json.loads(vd.get("config_json") or "{}")
            except Exception:
                cfg_obj = {}
            try:
                beat_obj = json.loads(vd.get("beat_script_json") or "[]")
            except Exception:
                beat_obj = []
            spec_file = settings.BASE_DIR / vd["slides_dir"] / "reels_spec.json"
            reels_spec_obj = {}
            if spec_file.exists():
                try:
                    reels_spec_obj = json.loads(spec_file.read_text(encoding="utf-8"))
                except Exception:
                    reels_spec_obj = {}
            cap = vd["caption"] or ""
            tags = vd["hashtags"] or ""
            full_cap = f"{cap}\n\n{tags}".strip() if tags else cap
            versions.append(
                {
                    "id": vd["id"],
                    "version_number": int(vd["version_number"]),
                    "content_format": vd.get("content_format") or rd.get("content_format") or "carousel",
                    "config": cfg_obj,
                    "beat_script": beat_obj,
                    "reels_spec": reels_spec_obj,
                    "caption": cap,
                    "hashtags": tags,
                    "full_caption": full_cap,
                    "char_count": len(full_cap),
                    "qa_report": qa_obj,
                    "leak_check": leak_obj,
                    "created_by": vd["created_by"],
                    "created_at": vd["created_at"],
                    "note": vd["note"],
                    "assets": _list_version_assets(lead_id, vd),
                }
            )

        corrections = [
            dict(c)
            for c in conn.execute(
                "SELECT * FROM content_corrections WHERE review_id = ? ORDER BY version_number DESC, id ASC",
                (rd["id"],),
            ).fetchall()
        ]
        comments = [
            dict(c)
            for c in conn.execute(
                "SELECT * FROM content_comments WHERE review_id = ? ORDER BY id ASC",
                (rd["id"],),
            ).fetchall()
        ]
        activity_raw = conn.execute(
            "SELECT * FROM content_activity WHERE review_id = ? ORDER BY id DESC LIMIT 60",
            (rd["id"],),
        ).fetchall()
        activity: list[dict[str, Any]] = []
        for a in activity_raw:
            ad = dict(a)
            try:
                meta = json.loads(ad.get("metadata_json") or "{}")
            except Exception:
                meta = {}
            activity.append(
                {
                    "id": ad["id"],
                    "actor": ad["actor"],
                    "action": ad["action"],
                    "metadata": meta,
                    "created_at": ad["created_at"],
                }
            )

    active_v = (
        int(rd["approved_version"])
        if rd["review_status"] in {"approved", "posted"} and rd["approved_version"]
        else int(rd["current_version"])
    )
    has_downloaded = any(
        a["action"] in {"asset_downloaded", "zip_downloaded"}
        and int(a["metadata"].get("version", -1)) == active_v
        for a in activity
    )
    has_copied = any(
        a["action"] == "caption_copied"
        and int(a["metadata"].get("version", -1)) == active_v
        for a in activity
    )

    try:
        metrics_obj = json.loads(rd.get("metrics_json") or "{}")
    except Exception:
        metrics_obj = {}

    return {
        "review_id": rd["id"],
        "lead_id": rd["lead_id"],
        "source": rd["source"],
        "anon_name": anon_name,
        "anon_slug": anon_slug,
        "category": rd["category"],
        "city": rd["city"],
        "design_style": rd["design_style"],
        "ux_flaw_sanitized": _sanitize_ux_flaw_for_brief(lead_stub, anon_name),
        "review_status": rd["review_status"],
        "content_format": rd.get("content_format") or "carousel",
        "art_direction_preset": rd.get("art_direction_preset") or "auto",
        "sequence_type": rd.get("sequence_type") or "auto",
        "voice_id": rd.get("voice_id") or "auto",
        "hook_pattern_id": rd.get("hook_pattern_id") or "auto",
        "audio_mode": rd.get("audio_mode") or "voiceover_and_music",
        "vo_script": rd.get("vo_script") or "",
        "vo_style": rd.get("vo_style") or "auto",
        "bgm_track": rd.get("bgm_track") or "auto",
        "pain_code": rd.get("pain_code") or "",
        "reel_hook_id": rd.get("reel_hook_id") or "",
        "metrics": {
            "views": int(metrics_obj.get("views") or 0),
            "saves": int(metrics_obj.get("saves") or 0),
            "shares": int(metrics_obj.get("shares") or 0),
            "dm_in": int(metrics_obj.get("dm_in") or 0),
            "updated_at": metrics_obj.get("updated_at") or "",
        },
        "creative_note": rd.get("creative_note") or "",
        "recommended_defaults": _compute_recommended_defaults(lead_stub),
        "current_version": int(rd["current_version"]),
        "approved_version": rd["approved_version"],
        "approved_by": rd["approved_by"],
        "approved_at": rd["approved_at"],
        "posted_at": rd["posted_at"],
        "posted_url": rd["posted_url"],
        "posted_by": rd["posted_by"],
        "created_at": rd["created_at"],
        "updated_at": rd["updated_at"],
        "active_version": active_v,
        "versions": versions,
        "corrections": corrections,
        "open_corrections_count": sum(1 for c in corrections if c["status"] == "open"),
        "resolved_corrections_for_review": [
            c for c in corrections if c["status"] == "resolved" and int(c["version_number"]) < int(rd["current_version"])
        ],
        "comments": comments,
        "activity": activity,
        "checklist": {
            "downloaded": has_downloaded,
            "caption_copied": has_copied,
            "posted": rd["review_status"] == "posted",
        },
    }
