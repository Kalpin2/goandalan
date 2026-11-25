"""Adaptive Reels Intelligence: Target BGM Synthesizer, Adaptive V/O Routing, Pain-Point Idea Scraper & Learning Logger."""

from __future__ import annotations

import json
import math
import re
import struct
import threading
import wave
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from config import settings
from creative_agent.carousel_planner import CASUAL_SLANG_PATTERN, FORMAL_INDUSTRY_TOKENS
from creative_agent.token_optimizer import (
    REELS_LEARNING_LOG_PATH,
    compact_scrape_text,
    compute_edit_delta,
)

AUDIO_SAMPLE_RATE = 44100
BGM_DIR = settings.BASE_DIR / "assets" / "bgm"
_REELS_LOG_LOCK = threading.Lock()

FORMAL_VO_TOKENS: tuple[str, ...] = FORMAL_INDUSTRY_TOKENS + (
    "pilates",
    "reformer",
    "wellness",
    "fisioterapi",
    "physiotherapy",
    "hotel",
    "villa",
    "resort",
    "spa",
    "konsultasi",
)

ENERGETIC_BGM_TOKENS: tuple[str, ...] = (
    "bengkel",
    "garage",
    "custom",
    "automotive",
    "otomotif",
    "motor",
    "mobil",
    "barber",
    "pangkas",
    "cukur",
    "grooming",
    "retail",
    "streetwear",
    "gym",
    "fitness",
    "toko",
)

HOSPITALITY_BGM_TOKENS: tuple[str, ...] = (
    "kopi",
    "coffee",
    "roast",
    "cafe",
    "kafe",
    "kedai",
    "bakery",
    "bakehouse",
    "roti",
    "pastry",
    "kuliner",
    "resto",
    "warung",
    "bistro",
    "matcha",
    "florist",
)

VO_STYLE_OPTIONS: list[dict[str, str]] = [
    {
        "id": "auto",
        "label": "Auto Adaptif (Sesuai Kategori)",
        "desc": "Klinik/Pilates/Legal/B2B otomatis sopan-tenang (0 slang); Kafe/Bakery/Barbershop/Bengkel hangat-santai.",
    },
    {
        "id": "formal_gadis",
        "label": "Sopan-Tenang · Gadis (Formal)",
        "desc": "id-ID-GadisNeural nada tenang profesional, 0 kata slang, cocok untuk klinik, pilates, hukum, dan B2B.",
    },
    {
        "id": "formal_ardi_calm",
        "label": "Sopan-Tenang · Ardi (Formal)",
        "desc": "id-ID-ArdiNeural ritme tenang dan berwibawa tanpa slang untuk bisnis profesional.",
    },
    {
        "id": "casual_ardi",
        "label": "Hangat-Santai · Ardi (Persona Alan)",
        "desc": "id-ID-ArdiNeural natural santai ala percakapan untuk kafe, bakery, barbershop, bengkel, dan retail.",
    },
]

DEFAULT_BGM_SPECS: dict[str, dict[str, str]] = {
    "calm_editorial": {
        "filename": "calm_editorial.wav",
        "label": "Calm Editorial (Klinik / Pilates / Profesional)",
        "desc": "Pad ambient lembut & tenang (~76 BPM) yang menjaga wibawa bisnis kesehatan, legal, dan B2B.",
    },
    "warm_hospitality": {
        "filename": "warm_hospitality.wav",
        "label": "Warm Hospitality (Kafe / Bakery / Kuliner)",
        "desc": "Electric piano lo-fi hangat (~94 BPM) dengan pulse halus, pas untuk hospitality & kuliner lokal.",
    },
    "energetic_craft": {
        "filename": "energetic_craft.wav",
        "label": "Energetic Craft (Bengkel / Barbershop / Retail)",
        "desc": "Groove bersih & modern (~112 BPM) untuk bengkel custom, barbershop, grooming, dan retail.",
    },
}


def is_formal_vo_category(category: str, brand_name: str = "") -> bool:
    hay = f"{category} {brand_name}".lower()
    return any(tok in hay for tok in FORMAL_VO_TOKENS)


def resolve_vo_profile(
    category: str,
    *,
    vo_style: str = "auto",
    brand_name: str = "",
) -> dict[str, Any]:
    """Resolve adaptive Indonesian TTS voice, speech rate, and formality flag."""
    req = (vo_style or "auto").strip().lower()
    cat_formal = is_formal_vo_category(category, brand_name)

    if req == "formal_gadis":
        return {"style": "formal_gadis", "voice": "id-ID-GadisNeural", "rate": "+2%", "is_formal": True}
    if req == "formal_ardi_calm":
        return {"style": "formal_ardi_calm", "voice": "id-ID-ArdiNeural", "rate": "+0%", "is_formal": True}
    if req == "casual_ardi":
        # Protect clinical/legal/pilates/b2b from slang even if casual requested, or keep voice casual if non-formal
        if cat_formal:
            return {"style": "formal_ardi_calm", "voice": "id-ID-ArdiNeural", "rate": "+0%", "is_formal": True}
        return {"style": "casual_ardi", "voice": "id-ID-ArdiNeural", "rate": "+5%", "is_formal": False}

    # Default auto adaptive
    if cat_formal:
        return {"style": "formal_gadis", "voice": "id-ID-GadisNeural", "rate": "+2%", "is_formal": True}
    return {"style": "casual_ardi", "voice": "id-ID-ArdiNeural", "rate": "+5%", "is_formal": False}


def sanitize_formal_vo_text(text: str) -> str:
    """Ensure zero casual slang leaks into formal/clinical/pilates/legal/B2B V/O scripts."""
    out = re.sub(r"\b(gw|gue)\b", "kami", text or "", flags=re.IGNORECASE)
    out = re.sub(r"\b(lo|lu|kamu)\b", "Anda", out, flags=re.IGNORECASE)
    out = re.sub(r"\b(bikin)\b", "membuat", out, flags=re.IGNORECASE)
    out = re.sub(r"\b(gampang)\b", "mudah", out, flags=re.IGNORECASE)
    out = re.sub(r"\b(gak|nggak|ga)\b", "tidak", out, flags=re.IGNORECASE)
    out = re.sub(r"\b(nih|banget|dong|sih)\b", "", out, flags=re.IGNORECASE)
    out = re.sub(r"\s{2,}", " ", out).strip()
    return out


# ---------------------------------------------------------------------------
# Procedural Royalty-Free Target-Matched BGM Generator (loop-safe 15s WAV)
# ---------------------------------------------------------------------------
def _synthesize_procedural_track(kind: str, target_wav: Path, duration_sec: float = 15.0) -> Path:
    sr = AUDIO_SAMPLE_RATE
    # Use integer cycles for seamless loop safety
    dur = max(12.0, float(duration_sec))
    total_samples = int(sr * dur)
    target_wav.parent.mkdir(parents=True, exist_ok=True)

    if kind == "calm_editorial":
        # Soft Rhodes/ambient pad progression: Cmaj9 -> Am9 -> Fmaj9 -> G6 (~76 BPM, dreamy & calm)
        chords = [
            (130.81, 164.81, 196.00, 246.94, 293.66),
            (110.00, 130.81, 164.81, 196.00, 246.94),
            (174.61, 220.00, 261.63, 329.63, 392.00),
            (196.00, 246.94, 293.66, 329.63, 392.00),
        ]
        beat_period = 0.789  # ~76 BPM
        gain = 0.56
        sub_gain = 0.10
        pluck_gain = 0.0
    elif kind == "energetic_craft":
        # Modern rhythmic craft groove: Em7 -> Cmaj7 -> G -> Dsus4 (~112 BPM)
        chords = [
            (164.81, 196.00, 246.94, 293.66),
            (130.81, 164.81, 196.00, 246.94),
            (196.00, 246.94, 293.66, 392.00),
            (146.83, 196.00, 220.00, 293.66),
        ]
        beat_period = 0.5357  # ~112 BPM
        gain = 0.64
        sub_gain = 0.20
        pluck_gain = 0.14
    else:
        # warm_hospitality: Fmaj7 -> Em7 -> Dm7 -> Cmaj7 (~94 BPM warm lo-fi)
        chords = [
            (174.61, 220.00, 261.63, 329.63),
            (164.81, 196.00, 246.94, 293.66),
            (146.83, 174.61, 220.00, 261.63),
            (130.81, 164.81, 196.00, 246.94),
        ]
        beat_period = 0.6383  # ~94 BPM
        gain = 0.62
        sub_gain = 0.15
        pluck_gain = 0.06

    chord_len = dur / len(chords)
    frames = bytearray(total_samples * 4)
    two_pi = 2.0 * math.pi
    pack_into = struct.pack_into

    for i in range(total_samples):
        t = i / float(sr)
        c_idx = min(len(chords) - 1, int(t / chord_len))
        local_t = t - c_idx * chord_len
        chord = chords[c_idx]

        atk = min(1.0, local_t / 0.18)
        rel = min(1.0, max(0.0, (chord_len - local_t) / 0.28))
        env = atk * (0.48 + 0.52 * math.exp(-local_t * 0.42)) * (0.35 + 0.65 * rel)

        val_l = 0.0
        val_r = 0.0
        for idx_f, f in enumerate(chord):
            ph = two_pi * f * t
            tone = 0.14 * math.sin(ph) + 0.032 * math.sin(ph * 2.0)
            # Subtle stereo width per voice
            pan_l = 0.92 if idx_f % 2 == 0 else 1.06
            pan_r = 1.06 if idx_f % 2 == 0 else 0.92
            val_l += tone * pan_l
            val_r += tone * pan_r
        val_l *= env
        val_r *= env

        # Soft root pulse on beat
        bt = t % beat_period
        pulse_env = math.exp(-bt * (13.0 if kind == "energetic_craft" else 9.5))
        root_f = chord[0] * 0.5
        sub = sub_gain * pulse_env * math.sin(two_pi * root_f * t)
        val_l += sub
        val_r += sub

        # Subtle melodic pluck on off-beats for energetic/hospitality tracks
        if pluck_gain > 0.0:
            half_bt = (t + beat_period * 0.5) % beat_period
            pluck_env = math.exp(-half_bt * 18.0)
            note_f = chord[(int(t / beat_period) + 1) % len(chord)] * 2.0
            pluck = pluck_gain * pluck_env * math.sin(two_pi * note_f * t)
            val_l += pluck * 0.95
            val_r += pluck * 1.05

        # Gentle loop-safe edge fade (0.12s in/out so looping has zero click)
        edge_in = min(1.0, t / 0.12)
        edge_out = min(1.0, max(0.0, (dur - t) / 0.15))
        g = edge_in * edge_out * gain
        sl = max(-0.92, min(0.92, val_l * g))
        sr_val = max(-0.92, min(0.92, val_r * g))
        pack_into("<hh", frames, i * 4, int(sl * 32767), int(sr_val * 32767))

    with wave.open(str(target_wav), "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(bytes(frames))
    return target_wav


def ensure_default_bgm_tracks(bgm_dir: Path | None = None) -> dict[str, Path]:
    """Ensure the 3 procedural royalty-free target BGM WAV tracks exist on disk."""
    target_dir = bgm_dir or BGM_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    for key, spec in DEFAULT_BGM_SPECS.items():
        p = target_dir / spec["filename"]
        if not p.exists() or p.stat().st_size < 10000:
            _synthesize_procedural_track(key, p, duration_sec=15.0)
        paths[key] = p
    return paths


def list_bgm_options(bgm_dir: Path | None = None) -> list[dict[str, str]]:
    """Return UI selector options for BGM (Auto + 3 procedural tracks + any custom .mp3/.wav in assets/bgm/)."""
    target_dir = bgm_dir or BGM_DIR
    ensure_default_bgm_tracks(target_dir)
    options: list[dict[str, str]] = [
        {
            "id": "auto",
            "label": "Auto Sesuai Target Bisnis",
            "desc": "Klinik/Pilates/Legal → Calm Editorial; Kafe/Bakery → Warm Hospitality; Bengkel/Barbershop/Retail → Energetic Craft.",
        }
    ]
    seen_files: set[str] = set()
    for key, spec in DEFAULT_BGM_SPECS.items():
        seen_files.add(spec["filename"].lower())
        options.append({"id": key, "label": spec["label"], "desc": spec["desc"]})

    # Discover any user-added .mp3/.wav files in assets/bgm/
    for fpath in sorted(target_dir.iterdir()):
        if not fpath.is_file():
            continue
        if fpath.suffix.lower() not in {".wav", ".mp3"}:
            continue
        if fpath.name.lower() in seen_files:
            continue
        clean_id = f"file:{fpath.name}"
        pretty = fpath.stem.replace("_", " ").replace("-", " ").title()
        options.append(
            {
                "id": clean_id,
                "label": f"Custom BGM: {pretty} ({fpath.suffix.lower()})",
                "desc": f"File musik lokal dari assets/bgm/{fpath.name}.",
            }
        )
    return options


def select_bgm_track(
    category: str,
    *,
    bgm_track: str = "auto",
    brand_name: str = "",
    bgm_dir: Path | None = None,
) -> dict[str, Any]:
    """Resolve the best matching BGM audio file path for a business category or explicit override."""
    target_dir = bgm_dir or BGM_DIR
    defaults = ensure_default_bgm_tracks(target_dir)
    req = (bgm_track or "auto").strip()

    if req.startswith("file:"):
        fname = Path(req[5:]).name
        cand = (target_dir / fname).resolve()
        if cand.is_file() and cand.is_relative_to(target_dir.resolve()) and cand.suffix.lower() in {".wav", ".mp3"}:
            return {"id": req, "label": fname, "path": cand}

    if req in defaults:
        return {"id": req, "label": DEFAULT_BGM_SPECS[req]["label"], "path": defaults[req]}

    hay = f"{category} {brand_name}".lower()
    if is_formal_vo_category(category, brand_name):
        key = "calm_editorial"
    elif any(tok in hay for tok in ENERGETIC_BGM_TOKENS):
        key = "energetic_craft"
    elif any(tok in hay for tok in HOSPITALITY_BGM_TOKENS):
        key = "warm_hospitality"
    else:
        key = "warm_hospitality"

    return {"id": key, "label": DEFAULT_BGM_SPECS[key]["label"], "path": defaults[key]}


# ---------------------------------------------------------------------------
# Attract Customer Reels Idea Scraper (Agent-Reach + Indonesian UMKM Fallback)
# ---------------------------------------------------------------------------
FALLBACK_UMKM_PAIN_BANK: list[dict[str, Any]] = [
    {
        "pain_code": "PAIN-WA",
        "reel_hook_id": "REEL-HOOK-1",
        "category": "Coffee Roastery",
        "city": "Jakarta Selatan",
        "anon_name": "Seduh Pagi Roastery",
        "design_style": "warm_organic_hospitality",
        "sequence_type": "before_after_ux",
        "ux_flaw": "Admin sering kewalahan membalas chat WA berulang soal daftar menu, lokasi, dan jam buka sehingga calon pelanggan menunggu terlalu lama.",
        "hook_headline": "Pelanggan batal datang karena kelamaan nunggu balasan WA?",
        "vo_script": (
            "Berapa pelanggan batal mampir hari ini cuma karena kelamaan nunggu balasan chat WA soal menu dan jam buka? "
            "Di konsep halaman mobile ini, menu andalan, lokasi Maps, sampai tombol pesan langsung kebaca dalam tiga detik tanpa ribet. "
            "Mau lihat konsep versi usaha kamu? Langsung DM kata KONSEP."
        ),
        "source_note": "bank_keluhan_umkm_id",
    },
    {
        "pain_code": "PAIN-BOOKING",
        "reel_hook_id": "REEL-HOOK-5",
        "category": "Klinik Gigi",
        "city": "Jakarta Selatan",
        "anon_name": "Klinik Gigi Tenang",
        "design_style": "clean_swiss_minimal",
        "sequence_type": "scroll_reveal_showcase",
        "ux_flaw": "Calon pasien kesulitan mengecek jadwal dokter dan layanan utama karena informasi tersebar di sorotan IG dan chat manual.",
        "hook_headline": "Calon pasien ingin booking, tapi harus chat panjang dulu?",
        "vo_script": (
            "Calon pasien sering ragu membuat janji temu ketika jadwal dokter dan daftar perawatan tidak langsung terlihat di ponsel. "
            "Pada konsep halaman ini, layanan utama, jadwal praktik, dan tombol reservasi WhatsApp tersusun jernih dalam satu tampilan rapi. "
            "Ingin melihat konsep versi klinik Anda? Silakan DM kata KONSEP."
        ),
        "source_note": "bank_keluhan_umkm_id",
    },
    {
        "pain_code": "PAIN-ADS",
        "reel_hook_id": "REEL-HOOK-3",
        "category": "Bengkel Custom",
        "city": "Bandung",
        "anon_name": "Besi Tua Custom Garage",
        "design_style": "neo_brutalist_street",
        "sequence_type": "before_after_ux",
        "ux_flaw": "Biaya iklan sudah jalan tetapi klik pengunjung hanya mentok di link bio tanpa penjelasan paket servis dan estimasi pengerjaan.",
        "hook_headline": "Iklan jalan terus, tapi klik cuma mentok di link bio?",
        "vo_script": (
            "Iklan sudah jalan tiap minggu, tapi banyak calon pelanggan cuma klik bio lalu pergi tanpa chat. "
            "Beda ceritanya kalau mereka mendarat di halaman mobile yang langsung menampilkan paket servis, galeri garapan, dan tombol konsultasi cepat. "
            "Mau lihat konsep versi bengkel kamu? Langsung DM kata KONSEP."
        ),
        "source_note": "bank_keluhan_umkm_id",
    },
    {
        "pain_code": "PAIN-TRUST",
        "reel_hook_id": "REEL-HOOK-2",
        "category": "Studio Pilates",
        "city": "Jakarta Selatan",
        "anon_name": "Ruang Gerak Pilates",
        "design_style": "modern_editorial",
        "sequence_type": "scroll_reveal_showcase",
        "ux_flaw": "Profil Instagram sudah rapi tetapi calon member baru belum menemukan halaman resmi berisi kelas, paket sesi, dan cara reservasi.",
        "hook_headline": "IG sudah rapi, tapi calon member masih bingung cek kelas?",
        "vo_script": (
            "Instagram studio sudah tertata rapi, namun calon member baru sering masih bertanya soal jenis kelas dan jadwal sesi yang tersedia. "
            "Dengan satu halaman web mobile yang tenang, jadwal kelas, lokasi studio, dan tombol reservasi langsung terbaca jelas. "
            "Ingin melihat konsep versi studio Anda? Silakan DM kata KONSEP."
        ),
        "source_note": "bank_keluhan_umkm_id",
    },
    {
        "pain_code": "PAIN-MOBILE",
        "reel_hook_id": "REEL-HOOK-4",
        "category": "Artisan Bakery",
        "city": "Bandung",
        "anon_name": "Ragi Pagi Bakehouse",
        "design_style": "coastal_terracotta",
        "sequence_type": "kinetic_editorial",
        "ux_flaw": "Katalog roti dan pre-order masih berupa file PDF terpisah sehingga pembeli di HP harus zoom-in dan sering batal order.",
        "hook_headline": "Masih kirim menu PDF yang harus di-zoom di layar HP?",
        "vo_script": (
            "Masih kirim katalog menu PDF yang bikin pembeli harus zoom-in berkali-kali di layar HP? "
            "Lihat bedanya saat menu andalan, jadwal oven harian, dan tombol pesan WA ditata rapi dalam satu halaman mobile yang ringan. "
            "Mau lihat konsep versi toko kamu? Langsung DM kata KONSEP."
        ),
        "source_note": "bank_keluhan_umkm_id",
    },
]

_PAIN_DETECT_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("PAIN-WA", ("wa", "whatsapp", "chat", "admin", "slow respon", "balas")),
    ("PAIN-BOOKING", ("booking", "reservasi", "jadwal", "antre", "antri", "janji")),
    ("PAIN-ADS", ("iklan", "ads", "boncos", "link bio", "linktree", "closing")),
    ("PAIN-MOBILE", ("pdf", "zoom", "lemot", "hp", "mobile", "katalog", "menu")),
    ("PAIN-TRUST", ("percaya", "trust", "kredibel", "resmi", "maps", "website")),
)


def _detect_pain_code(text: str) -> str:
    low = (text or "").lower()
    best_code = "PAIN-WA"
    best_score = 0
    for code, kws in _PAIN_DETECT_RULES:
        sc = sum(1 for kw in kws if kw in low)
        if sc > best_score:
            best_score = sc
            best_code = code
    return best_code


def scrape_reels_ideas(
    *,
    topic: str = "",
    limit: int = 3,
    runner: Callable[[list[str], int], dict[str, Any]] | None = None,
    timeout: int = 25,
) -> dict[str, Any]:
    """Collect real Indonesian business pain points via Agent-Reach (`web/youtube search` + `compact_scrape_text`) with local fallback."""
    from creative_agent import lead_enricher

    cap = max(1, min(4, int(limit)))
    eff_timeout = max(5, min(25, int(timeout)))
    q_topic = (topic or "").strip() or "keluhan umkm balas chat whatsapp website sepi pelanggan indonesia"

    raw_sources: list[dict[str, Any]] = []
    source_mode = "fallback_umkm_bank"

    can_run = runner is not None or bool(lead_enricher.resolve_agent_reach_bin())
    if can_run:
        exec_fn = runner or lead_enricher.run_agent_reach
        queries = [
            ["web", "search", q_topic, "--limit", "4"],
            ["youtube", "search", f"masalah umkm {q_topic}", "--limit", "3"],
        ]
        for args in queries:
            try:
                res = exec_fn(args, eff_timeout)
            except Exception:
                res = {"ok": False, "items": []}
            if res.get("ok") and res.get("items"):
                for item in (res.get("items") or [])[:4]:
                    if isinstance(item, dict):
                        raw_sources.append(
                            {
                                "source": args[0],
                                "title": str(item.get("title") or ""),
                                "text": str(item.get("text") or item.get("snippet") or item.get("description") or ""),
                                "url": str(item.get("url") or ""),
                            }
                        )

    compacted = compact_scrape_text(raw_sources, max_chars=700, max_sources=4) if raw_sources else {
        "sources": [],
        "combined_text": "",
        "source_count": 0,
        "total_chars": 0,
        "original_chars": 0,
        "saved_pct": 0.0,
    }

    ideas: list[dict[str, Any]] = []
    used_pains: set[str] = set()

    if compacted["sources"]:
        source_mode = "agent_reach_compacted"
        for src in compacted["sources"]:
            if len(ideas) >= cap:
                break
            p_code = _detect_pain_code(src["text"])
            if p_code in used_pains:
                # pick next unused fallback pain to keep variety
                alt = next((f["pain_code"] for f in FALLBACK_UMKM_PAIN_BANK if f["pain_code"] not in used_pains), p_code)
                p_code = alt
            used_pains.add(p_code)
            template = next((f for f in FALLBACK_UMKM_PAIN_BANK if f["pain_code"] == p_code), FALLBACK_UMKM_PAIN_BANK[0])
            snippet = src["text"][:150].rsplit(" ", 1)[0].strip() if len(src["text"]) > 150 else src["text"]
            idea = {
                **template,
                "ux_flaw": f"Sinyal pasar ({p_code}): {snippet}" if snippet else template["ux_flaw"],
                "source_note": f"agent_reach:{src['source']}",
                "source_excerpt": src["text"],
            }
            ideas.append(idea)

    # Top up from fallback Indonesian UMKM pain bank if fewer than `cap`
    for fb in FALLBACK_UMKM_PAIN_BANK:
        if len(ideas) >= cap:
            break
        if fb["pain_code"] in used_pains:
            continue
        used_pains.add(fb["pain_code"])
        ideas.append(dict(fb))

    return {
        "source_mode": source_mode,
        "query": q_topic,
        "compacted_scrape": compacted,
        "ideas": ideas[:cap],
    }


# ---------------------------------------------------------------------------
# Zero-Token Reels Learning Logger (`reels_learning_log.md`)
# ---------------------------------------------------------------------------
def log_reels_event(
    *,
    lead: dict[str, Any],
    original_vo_script: str,
    final_vo_script: str,
    pain_code: str = "",
    reel_hook_id: str = "",
    voice: str = "",
    vo_style: str = "auto",
    bgm_track: str = "auto",
    duration_sec: float = 12.0,
    views: int = 0,
    saves: int = 0,
    shares: int = 0,
    dm_in: int = 0,
    notes: str = "",
    log_path: Path | None = None,
) -> dict[str, Any]:
    """Append a structured `reels_log` YAML entry with 0-LLM-token edit delta."""
    path = log_path or REELS_LEARNING_LOG_PATH
    display_name = (lead.get("anonymized_name") or f"Konsep Lokal #{lead.get('id', '')}").strip()
    delta = compute_edit_delta(original_vo_script, final_vo_script)
    now_iso = datetime.now(timezone.utc).isoformat(timespec="seconds")

    # Never leak real business name into anonymized Reels log
    safe_orig = original_vo_script or ""
    safe_final = final_vo_script or original_vo_script or ""
    real_name = (lead.get("business_name") or "").strip()
    if real_name and real_name.lower() != display_name.lower():
        safe_orig = re.sub(re.escape(real_name), display_name, safe_orig, flags=re.IGNORECASE)
        safe_final = re.sub(re.escape(real_name), display_name, safe_final, flags=re.IGNORECASE)

    entry = {
        "lead_id": str(lead.get("id") or ""),
        "date": now_iso,
        "display_name": display_name,
        "category": (lead.get("category") or "Bisnis Lokal").strip(),
        "pain_code": (pain_code or "").strip().upper(),
        "reel_hook_id": (reel_hook_id or "").strip().upper(),
        "voice": (voice or "").strip().upper(),
        "vo_style": (vo_style or "auto").strip(),
        "bgm_track": (bgm_track or "auto").strip(),
        "duration_sec": round(float(duration_sec or 0), 2),
        "word_count": delta["final_words"],
        "word_delta": delta["word_delta"],
        "sapaan_changed": delta["sapaan_changed"],
        "emoji_removed": delta["emoji_removed"],
        "shortened": delta["shortened"],
        "original_vo_script": safe_orig,
        "final_vo_script": safe_final,
        "edit_summary": delta["summary"],
        "edit_delta": delta,
        "views": int(views or 0),
        "saves": int(saves or 0),
        "shares": int(shares or 0),
        "dm_in": int(dm_in or 0),
        "notes": notes,
    }

    yaml_block = (
        f"\n### Reels Log: {display_name} ({entry['pain_code'] or 'REELS'}) --- {now_iso[:10]}\n\n"
        f"```yaml\n"
        f"reels_log:\n"
        f"  lead_id: {json.dumps(entry['lead_id'])}\n"
        f"  date: {json.dumps(entry['date'])}\n"
        f"  display_name: {json.dumps(entry['display_name'], ensure_ascii=False)}\n"
        f"  category: {json.dumps(entry['category'], ensure_ascii=False)}\n"
        f"  pain_code: {json.dumps(entry['pain_code'])}\n"
        f"  reel_hook_id: {json.dumps(entry['reel_hook_id'])}\n"
        f"  voice: {json.dumps(entry['voice'])}\n"
        f"  vo_style: {json.dumps(entry['vo_style'])}\n"
        f"  bgm_track: {json.dumps(entry['bgm_track'])}\n"
        f"  duration_sec: {entry['duration_sec']}\n"
        f"  word_count: {entry['word_count']}\n"
        f"  word_delta: {entry['word_delta']}\n"
        f"  sapaan_changed: {json.dumps(entry['sapaan_changed'], ensure_ascii=False)}\n"
        f"  emoji_removed: {entry['emoji_removed']}\n"
        f"  shortened: {'true' if entry['shortened'] else 'false'}\n"
        f"  original_vo_script: {json.dumps(entry['original_vo_script'], ensure_ascii=False)}\n"
        f"  final_vo_script: {json.dumps(entry['final_vo_script'], ensure_ascii=False)}\n"
        f"  edit_summary: {json.dumps(entry['edit_summary'], ensure_ascii=False)}\n"
        f"  views: {entry['views']}\n"
        f"  saves: {entry['saves']}\n"
        f"  shares: {entry['shares']}\n"
        f"  dm_in: {entry['dm_in']}\n"
        f"  notes: {json.dumps(entry['notes'], ensure_ascii=False)}\n"
        f"```\n"
    )

    with _REELS_LOG_LOCK:
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.write_text("# Reels Learning Log\n\n## Log entries\n", encoding="utf-8")
        with path.open("a", encoding="utf-8") as fh:
            fh.write(yaml_block)
    return entry
