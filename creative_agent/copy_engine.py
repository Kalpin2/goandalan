"""Deterministic Copy Intelligence Engine for @goandalan (`copy_intelligence_library.md`).

Implements:
- Integrity assertion on `skills/instagram-creative-agent/references/copy_intelligence_library.md`
- Deterministic voice pre-routing `V1`–`V6` synchronized with P7 `caption_voice` (`formal_editorial` vs `casual_gw`)
- Variation control (§11): tracks last 10 outputs per channel to avoid repeating opener IDs, first 5 words, or consecutive caption hooks
- 20% Exploration budget (§12.3 #5): 1 of 5 drafts on regular-priority leads tests a matching `candidate` pattern from `copy_candidates.md`
- Hard-fail validator (§10.1) & banned phrase audit (§10.3)
- Append-only learning logger (`copy_learning_log.md`) recording `original_draft`, human `final_text`, `edit_summary`, pattern IDs, & automatic outcome updates (`INTERESTED` / `IGNORED_48H`)
"""

from __future__ import annotations

import json
import re
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config import settings
from creative_agent.carousel_planner import FORMAL_INDUSTRY_TOKENS, select_caption_voice

REFERENCES_DIR = settings.BASE_DIR / "skills" / "instagram-creative-agent" / "references"
COPY_LIBRARY_PATH = REFERENCES_DIR / "copy_intelligence_library.md"
COPY_CANDIDATES_PATH = REFERENCES_DIR / "copy_candidates.md"
COPY_LEARNING_LOG_PATH = REFERENCES_DIR / "copy_learning_log.md"

_LOG_LOCK = threading.Lock()


def assert_copy_library_integrity(library_path: Path | None = None) -> Path:
    """Verify `copy_intelligence_library.md` exists and is non-empty."""
    path = library_path or COPY_LIBRARY_PATH
    if not path.exists() or path.stat().st_size == 0:
        raise FileNotFoundError(
            f"Copy Intelligence Library missing or empty at: {path}"
        )
    return path


assert_copy_library_integrity()


# ---------------------------------------------------------------------------
# Voice archetypes V1–V6 synced with P7 `caption_voice` (§3 & §3.1)
# ---------------------------------------------------------------------------
VOICE_ARCHETYPES: dict[str, dict[str, Any]] = {
    "V1": {
        "name": "Hangat-Lokal",
        "register": "casual",
        "caption_voice": "casual_gw",
        "sapaan": "Kak",
        "energy": "warm",
        "allow_emoji": True,
    },
    "V2": {
        "name": "Tenang-Profesional",
        "register": "formal",
        "caption_voice": "formal_editorial",
        "sapaan": "Bapak/Ibu",
        "energy": "calm",
        "allow_emoji": False,
    },
    "V3": {
        "name": "Santai-Gaul",
        "register": "casual",
        "caption_voice": "casual_gw",
        "sapaan": "Kak",
        "energy": "playful",
        "allow_emoji": True,
    },
    "V4": {
        "name": "Premium-Minimal",
        "register": "formal",
        "caption_voice": "formal_editorial",
        "sapaan": "Bapak/Ibu",
        "energy": "calm",
        "allow_emoji": False,
    },
    "V5": {
        "name": "Bold-Langsung",
        "register": "neutral",
        "caption_voice": "casual_gw",
        "sapaan": "Kak",
        "energy": "bold",
        "allow_emoji": False,
    },
    "V6": {
        "name": "Pengrajin-Bercerita",
        "register": "neutral",
        "caption_voice": "casual_gw",
        "sapaan": "Kak",
        "energy": "warm",
        "allow_emoji": False,
    },
}

_VOICE_CATEGORY_RULES: tuple[tuple[tuple[str, ...], str, str], ...] = (
    # Clinical, legal, finance, education -> V2 Tenang-Profesional (formal_editorial)
    (
        FORMAL_INDUSTRY_TOKENS + ("accounting", "school", "sekolah", "kursus"),
        "V2",
        "V1",
    ),
    # Hospitality luxury -> V4 Premium-Minimal (formal_editorial)
    (
        ("hotel", "villa", "resort", "spa", "fine dining", "glamping", "sanctuary", "retreat"),
        "V4",
        "V2",
    ),
    # Streetwear, barber, tattoo, gym -> V5 Bold-Langsung
    (
        ("streetwear", "barber", "pangkas", "cukur", "grooming", "tattoo", "gym", "fitness", "pilates", "studio olahraga"),
        "V5",
        "V3",
    ),
    # Craft, batik, ceramics, furniture -> V6 Pengrajin-Bercerita
    (
        ("batik", "keramik", "ceramic", "craft", "kriya", "furniture", "mebel", "kayu", "tenun", "artisan"),
        "V6",
        "V1",
    ),
    # Salon, bridal, photography -> V1 / V4
    (
        ("salon", "bridal", "wedding", "foto", "photo", "fotografi", "florist"),
        "V1",
        "V4",
    ),
    # Cafe, bakery, warung, F&B casual -> V1 Hangat-Lokal
    (
        ("kopi", "coffee", "roast", "cafe", "kafe", "bakery", "roti", "pastry", "warung", "resto", "bistro", "kuliner", "matcha", "kedai"),
        "V1",
        "V3",
    ),
)


# ---------------------------------------------------------------------------
# Hard-fail regexes & §10.3 banned phrases
# ---------------------------------------------------------------------------
URL_PATTERN = re.compile(
    r"(https?://\S+|www\.\S+|\b(?:wa\.me|linktr\.ee|bit\.ly|t\.me|instagram\.com)/\S+|\b[a-z0-9-]+\.(?:com|id|co\.id|net|org|io|site|page)(?:/\S*)?\b)",
    flags=re.IGNORECASE,
)
ALAN_PATTERN = re.compile(r"\balan\b", flags=re.IGNORECASE)
EMOJI_PATTERN = re.compile(r"[\U0001F300-\U0001FAFF\u2600-\u27BF]")

BANNED_PHRASES_10_3: tuple[str, ...] = (
    "solusi terbaik",
    "terpercaya dan profesional",
    "kami adalah perusahaan",
    "perkenalkan nama saya",
    "sehubungan dengan",
    "dengan hormat",
    "kesempatan emas",
    "jangan sampai ketinggalan",
    "dijamin",
    "100% puas",
    "hanya hari ini",
    "buruan",
    "gratis!!!",
    "semoga sehat selalu",
    "cuma mengingatkan",
    "sudah dibaca belum",
)

BANNED_HARDSELL_CAPTIONS: tuple[str, ...] = (
    "dm sekarang",
    "hubungi kami untuk",
    "pesan website",
    "jasa pembuatan website",
)

DISCLOSURE_MARKERS: tuple[str, ...] = (
    "konsep fiktif",
    "brand fiktif",
    "fiktif untuk",
    "studi kasus fiktif",
    "nama dan detailnya dibuat ulang",
)


# ---------------------------------------------------------------------------
# Pattern Libraries (§6.4, §6.5, §7.3, §7.5, §7.7)
# ---------------------------------------------------------------------------
DM_OPENERS: list[dict[str, Any]] = [
    {
        "id": "OPEN-S1",
        "needs_obs": True,
        "requires_web": None,
        "voices": ("V1", "V3", "V6"),
        "levers": ["L1", "L2", "L3"],
        "template": "{sapaan}, {detail_ig} di IG {nama_usaha} itu menarik, kelihatan banget ada yang dipikirin, bukan asal posting.",
    },
    {
        "id": "OPEN-S2",
        "needs_obs": True,
        "requires_web": None,
        "voices": ("V1", "V2", "V4", "V6"),
        "levers": ["L1", "L4"],
        "template": "{sapaan}, {detail_ig} di Instagram {nama_usaha} sudah kuat kesannya. Yang belum ada baru halaman web yang sama rapinya di luar IG.",
    },
    {
        "id": "OPEN-G1",
        "needs_obs": True,
        "requires_web": False,
        "voices": ("V5", "V3", "V1"),
        "levers": ["L4", "L1"],
        "template": "{sapaan}, langsung saja: {nama_usaha} belum punya website resmi, padahal {detail_ig} di IG sudah siap dilihat calon pelanggan.",
    },
    {
        "id": "OPEN-D1",
        "needs_obs": False,
        "requires_web": None,
        "voices": ("V1", "V2", "V4", "V5", "V6"),
        "levers": ["L2", "L3"],
        "template": "{sapaan}, saya sudah menyusun konsep halaman depan website untuk {nama_usaha} dengan sentuhan {detail_ig}. Belum dipublish, baru simpanan internal.",
    },
    {
        "id": "OPEN-C1",
        "needs_obs": False,
        "requires_web": None,
        "voices": ("V1", "V3", "V5", "V6"),
        "levers": ["L5", "L2"],
        "template": "{sapaan}, kalau {nama_usaha} punya halaman web sendiri yang nyambung dengan {detail_ig}, kira-kira tampilan depannya sudah saya buatkan.",
    },
    {
        "id": "OPEN-U1",
        "needs_obs": False,
        "requires_web": True,
        "voices": ("V2", "V4", "V1", "V5"),
        "levers": ["L4", "L2"],
        "template": "{sapaan}, tampilan online {nama_usaha} sudah punya bahan bagus, terutama {detail_ig}. Satu hal yang bisa dibuat lebih ringan: {ux_flaw_ramah}.",
    },
]

DM_BRIDGES: dict[str, str] = {
    "formal": "Saya Alan. Saya sudah menyiapkan satu foto preview konsep versi desktop dan HP agar informasi utama {nama_usaha} cepat terbaca.",
    "bold": "Saya Alan. Konsep halaman depannya sudah jadi dalam bentuk foto preview konsep versi HP dan desktop, bukan template kosong.",
    "warm": "Saya Alan, biasa bantu usaha {kategori_lower} punya tampilan online yang rapi. Konsepnya sudah jadi dalam bentuk foto preview konsep versi HP.",
}

DM_ASKS: list[dict[str, Any]] = [
    {
        "id": "ASK-1",
        "formal": False,
        "offer": "Bentuknya foto preview konsep gratis tanpa kewajiban apa-apa.",
        "ask": "Boleh saya kirim fotonya di sini, {sapaan}?",
    },
    {
        "id": "ASK-2",
        "formal": False,
        "offer": "Kalau tidak cocok, abaikan saja tanpa rasa sungkan.",
        "ask": "Mau saya kirim foto preview konsepnya sekarang?",
    },
    {
        "id": "ASK-3",
        "formal": False,
        "offer": "Tidak minta komitmen apa-apa dulu, cukup lihat saja.",
        "ask": "Boleh saya kirim lewat sini?",
    },
    {
        "id": "ASK-4",
        "formal": True,
        "offer": "Tidak ada biaya maupun kewajiban apa pun.",
        "ask": "Berkenan jika saya kirimkan foto preview konsepnya, {sapaan}?",
    },
]

FOLLOWUP_PATTERNS: list[dict[str, str]] = [
    {
        "id": "FU-1",
        "template": "{sapaan}, tambahan kecil: umumnya calon pengunjung {nama_usaha} membuka info dari HP, jadi saya sudah sertakan juga tampilan mobile di foto preview konsepnya. Boleh saya kirim?",
    },
    {
        "id": "FU-2",
        "template": "{sapaan}, kalau memang belum waktunya tidak apa-apa sama sekali. Cukup balas 'nanti' dan saya tidak akan mengganggu lagi. Foto preview konsep {nama_usaha} tetap saya simpan.",
    },
    {
        "id": "FU-3",
        "template": "{sapaan}, untuk karakter {nama_usaha} menurut {sapaan} lebih pas gaya visual yang hangat atau yang minimal bersih? Saya bisa sesuaikan foto preview konsepnya sebelum dikirim.",
    },
    {
        "id": "FU-5",
        "template": "{sapaan}, ini pesan terakhir dari saya supaya tidak mengganggu. Kalau suatu hari ingin melihat foto preview konsep untuk {nama_usaha}, tinggal balas di sini. Sukses terus untuk {nama_usaha}.",
    },
]

CAPTION_HOOKS: list[dict[str, Any]] = [
    {
        "id": "HOOK-Q1",
        "hook_type": "question",
        "formal_ok": False,
        "template": "Kalau orang baru nemu {cat_lower} kamu malam ini, apa yang mereka lihat pertama?",
    },
    {
        "id": "HOOK-K1",
        "hook_type": "contrast",
        "formal_ok": True,
        "template": "Website {cat_lower} bukan sekadar brosur digital. Ini perbedaannya.",
    },
    {
        "id": "HOOK-D1",
        "hook_type": "detail",
        "formal_ok": True,
        "template": "Satu keputusan tipografi di slide 3 yang bikin tampilan {cat_lower} jauh lebih tenang.",
    },
    {
        "id": "HOOK-B1",
        "hook_type": "bold_claim",
        "formal_ok": True,
        "template": "Tiga detik pertama di layar HP menentukan: lanjut membaca atau langsung menutup tab.",
    },
    {
        "id": "HOOK-N1",
        "hook_type": "character",
        "formal_ok": False,
        "template": "Kenalan dengan {brand_name}. Brand-nya fiktif, tapi struktur tampilannya nyata.",
    },
    {
        "id": "HOOK-L1",
        "hook_type": "count",
        "formal_ok": True,
        "template": "4 slide, 1 ide utama: bagaimana struktur halaman {cat_lower} dibuat langsung terbaca di HP.",
    },
]

CAPTION_CTAS: list[dict[str, Any]] = [
    {
        "id": "CTA-S1",
        "formal_ok": True,
        "template": "Simpan sebagai referensi saat menyusun ulang tampilan website usaha Anda.",
        "casual_template": "Simpan buat referensi kalau lagi merapikan tampilan website usahamu.",
    },
    {
        "id": "CTA-Q1",
        "formal_ok": True,
        "template": "Menurut Anda, bagian antarmuka mana yang paling membantu pengunjung?",
        "casual_template": "Menurutmu slide mana yang paling pas buat karakter bisnisnya? Tulis angkanya.",
    },
]


# ---------------------------------------------------------------------------
# Client Profile & Deterministic Voice Pre-Routing (§2 & §3)
# ---------------------------------------------------------------------------
def route_voice_for_lead(
    lead: dict[str, Any],
    caption_voice_override: str | None = None,
    voice_id_override: str | None = None,
) -> dict[str, Any]:
    """Deterministically route `V1`–`V6` synced with P7 `caption_voice` (`formal_editorial` vs `casual_gw`).

    Hard guardrail: clinical/legal/B2B categories NEVER receive casual slang even if a casual voice is selected.
    """
    category = (lead.get("category") or "Bisnis Lokal").strip()
    brand_name = (lead.get("display_name") or lead.get("anonymized_name") or lead.get("business_name") or "").strip()
    hay = f"{category} {brand_name}".lower()

    auto_formal = select_caption_voice(category, brand_name) == "formal_editorial"
    p7_voice = select_caption_voice(category, brand_name, override=caption_voice_override)
    if auto_formal:
        p7_voice = "formal_editorial"

    voice_id = "V1"
    secondary_voice = "V2"
    explicit_vid = (voice_id_override or "").strip().upper()
    if explicit_vid in VOICE_ARCHETYPES:
        voice_id = explicit_vid
        secondary_voice = "V2" if voice_id != "V2" else "V4"
    else:
        for tokens, primary_v, sec_v in _VOICE_CATEGORY_RULES:
            if any(tok in hay for tok in tokens):
                voice_id = primary_v
                secondary_voice = sec_v
                break

    # Synchronize strictly with P7 caption_voice (enforce formal editorial on clinical/legal/B2B)
    if p7_voice == "formal_editorial" and voice_id not in {"V2", "V4"}:
        voice_id = "V2"
        secondary_voice = "V4"
    elif caption_voice_override == "casual_gw" and not auto_formal and voice_id in {"V2", "V4"} and explicit_vid not in VOICE_ARCHETYPES:
        voice_id = "V1"
        secondary_voice = "V3"

    meta = VOICE_ARCHETYPES[voice_id]
    resolved_cap_voice = "formal_editorial" if (auto_formal or meta["caption_voice"] == "formal_editorial") else meta["caption_voice"]
    return {
        "voice": voice_id,
        "secondary_voice": secondary_voice,
        "archetype": meta["name"],
        "caption_voice": resolved_cap_voice,
        "register": "formal" if resolved_cap_voice == "formal_editorial" else meta["register"],
        "sapaan": meta["sapaan"],
        "energy": meta["energy"],
        "allow_emoji": False if resolved_cap_voice == "formal_editorial" else meta["allow_emoji"],
    }


def build_client_profile(lead: dict[str, Any], is_recycled: bool = False) -> dict[str, Any]:
    """Build §2.2 Client Intelligence Profile separating `known` facts from `inferred` traits."""
    routing = route_voice_for_lead(lead)
    display_name = (
        (lead.get("anonymized_name") or f"Konsep Lokal #{lead.get('id', '')}").strip()
        if is_recycled or int(lead.get("is_anonymized") or 0)
        else (lead.get("business_name") or "Bisnis Lokal").strip()
    )
    ig_obs = (lead.get("ig_observation") or "").strip()
    return {
        "display_name": display_name,
        "category": (lead.get("category") or "Bisnis Lokal").strip(),
        "city": (lead.get("city") or settings.DEFAULT_CITY).strip(),
        "known": {
            "has_website": bool(lead.get("has_website")),
            "ux_flaw": (lead.get("ux_flaw") or "").strip(),
            "ig_observation": ig_obs,
            "rating": lead.get("rating"),
        },
        "inferred": {
            "register": routing["register"],
            "sapaan": routing["sapaan"],
            "energy": routing["energy"],
            "trust_need": "high" if routing["voice"] in {"V2", "V4"} else "medium",
            "likely_pain": (lead.get("ux_flaw") or "").strip(),
        },
        "proof_available": [],
        "needs_observation": not bool(ig_obs),
        "routing": routing,
    }


# ---------------------------------------------------------------------------
# Candidate Loader (20% Exploration Budget) & Log History Reader (§11 & §12)
# ---------------------------------------------------------------------------
def load_copy_candidates(
    channel: str | None = None,
    candidates_path: Path | None = None,
) -> list[dict[str, Any]]:
    """Parse `status: candidate` (and `testing`) pattern blocks from `copy_candidates.md`."""
    path = candidates_path or COPY_CANDIDATES_PATH
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8", errors="ignore")
    blocks = re.findall(r"```yaml\s*(.*?)```", text, flags=re.DOTALL | re.IGNORECASE)
    results: list[dict[str, Any]] = []
    for blk in blocks:
        if "pattern:" not in blk:
            continue
        item: dict[str, Any] = {}
        for line in blk.splitlines():
            s = line.strip()
            if ":" not in s or s.startswith("#") or s == "pattern:":
                continue
            k, v = s.split(":", 1)
            k = k.strip()
            v = v.strip()
            if v.startswith('"') and v.endswith('"'):
                v = v[1:-1]
            elif v.startswith("[") and v.endswith("]"):
                inner = v[1:-1].strip()
                v = [x.strip().strip('"').strip("'") for x in inner.split(",") if x.strip()] if inner else []
            item[k] = v
        status = str(item.get("status") or "").lower()
        if status not in {"candidate", "testing"}:
            continue
        if channel and str(item.get("channel") or "").lower() != channel.lower():
            continue
        if item.get("id") and item.get("template"):
            results.append(item)
    return results


def _parse_recent_logs(
    channel: str,
    limit: int = 10,
    log_path: Path | None = None,
) -> list[dict[str, Any]]:
    """Read the last `limit` structured entries for `channel` from `copy_learning_log.md`."""
    path = log_path or COPY_LEARNING_LOG_PATH
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8", errors="ignore")
    marker = "## Log entries"
    body = text.split(marker, 1)[1] if marker in text else text
    blocks = re.findall(r"```yaml\s*(.*?)```", body, flags=re.DOTALL | re.IGNORECASE)
    parsed: list[dict[str, Any]] = []
    for blk in blocks:
        if "copy_log:" not in blk:
            continue
        rec: dict[str, Any] = {}
        for line in blk.splitlines():
            s = line.strip()
            if ":" not in s or s == "copy_log:":
                continue
            k, v = s.split(":", 1)
            k = k.strip()
            v = v.strip()
            if v.startswith('"') and v.endswith('"'):
                try:
                    v = json.loads(v)
                except Exception:
                    v = v[1:-1]
            elif v.startswith("[") and v.endswith("]"):
                try:
                    v = json.loads(v)
                except Exception:
                    inner = v[1:-1].strip()
                    v = [x.strip().strip('"').strip("'") for x in inner.split(",") if x.strip()] if inner else []
            rec[k] = v
        if rec.get("channel") == channel:
            parsed.append(rec)
    return parsed[-limit:]


def _first_five_words(text: str) -> str:
    words = re.findall(r"[a-zA-Z0-9]+", (text or "").lower())
    return " ".join(words[:5])


def _soften_ux_flaw(flaw: str) -> str:
    clean = (flaw or "").strip().rstrip(".")
    if not clean:
        return "alur info menu dan kontak WA di HP bisa dibuat lebih ringkas"
    for harsh, gentle in (
        ("jelek", "bisa dirapikan"),
        ("berantakan", "bisa ditata lebih ringkas"),
        ("ketinggalan zaman", "bisa dibuat lebih segar"),
        ("buruk", "bisa ditingkatkan"),
    ):
        clean = re.sub(harsh, gentle, clean, flags=re.IGNORECASE)
    return clean[0].lower() + clean[1:] if len(clean) > 1 else clean.lower()


def _count_words(text: str) -> int:
    # Treat bracketed placeholder `[isi 1 detail spesifik IG mereka]` as ~4 natural words if present
    normalized = re.sub(r"\[[^\]]+\]", "detail spesifik ig mereka", text or "")
    return len(re.findall(r"[A-Za-z0-9À-ÿ'-]+", normalized))


# ---------------------------------------------------------------------------
# Hard-Fail Validator (§10.1 & §10.3)
# ---------------------------------------------------------------------------
def validate_copy(
    text: str,
    channel: str,
    lead: dict[str, Any] | None = None,
    is_recycled: bool = False,
) -> dict[str, Any]:
    """Run hard-fail §10.1 + banned-phrase §10.3 checks. Hard fails MUST never ship."""
    hard_fails: list[str] = []
    warnings: list[str] = []
    raw = (text or "").strip()
    low = raw.lower()
    word_count = _count_words(raw)
    alan_count = len(ALAN_PATTERN.findall(raw))

    if not raw:
        hard_fails.append("Teks copy kosong.")

    # §10.3 Banned phrases
    for phrase in BANNED_PHRASES_10_3:
        if phrase in low:
            hard_fails.append(f"Frasa terlarang (§10.3) terdeteksi: '{phrase}'.")

    # Stacked exclamation marks
    if "!!!" in raw:
        hard_fails.append("Tanda seru beruntun ('!!!') dilarang.")

    if channel == "cold_dm_1":
        if URL_PATTERN.search(raw):
            hard_fails.append("URL atau tautan dilarang di dalam Cold DM #1 (§10.1).")
        if alan_count > 1:
            hard_fails.append(f"Nama 'Alan' muncul {alan_count}× (maksimal 1× di Cold DM #1).")
        if word_count < 45 or word_count > 80:
            hard_fails.append(f"Jumlah kata Cold DM #1 di luar rentang 45–80 kata (aktual: {word_count} kata).")
        q_count = raw.count("?")
        if q_count > 1:
            hard_fails.append(f"Cold DM #1 memiliki {q_count} tanda tanya (maksimal 1 pertanyaan izin).")
        elif q_count == 0:
            warnings.append("Cold DM #1 sebaiknya diakhiri satu pertanyaan izin yang jelas.")
        if "foto preview" not in low:
            warnings.append("Cold DM #1 sebaiknya menawarkan foto preview konsep.")

    elif channel == "caption":
        if alan_count > 1:
            hard_fails.append(f"Nama 'Alan' muncul {alan_count}× (maksimal 1×).")
        for cta in BANNED_HARDSELL_CAPTIONS:
            if cta in low:
                hard_fails.append(f"CTA hard-selling dilarang pada caption: '{cta}'.")
        if is_recycled:
            if not any(m in low for m in DISCLOSURE_MARKERS):
                hard_fails.append("Baris disclosure konsep fiktif wajib ada pada caption konten daur ulang (§10.1).")
            if lead:
                anon_name = (lead.get("anonymized_name") or "").strip().lower()
                real_name = (lead.get("business_name") or "").strip()
                if real_name and real_name.lower() != anon_name and real_name.lower() in low:
                    hard_fails.append("Kebocoran nama bisnis asli pada caption konten daur ulang (§10.1).")
                digits_only = re.sub(r"\D+", "", raw)
                for pfield in ("phone_raw", "phone_wa"):
                    pdigits = re.sub(r"\D+", "", str(lead.get(pfield) or ""))
                    if len(pdigits) >= 8 and pdigits in digits_only:
                        hard_fails.append("Kebocoran nomor WA/telepon asli pada caption konten daur ulang (§10.1).")
                        break
                real_addr = (lead.get("address") or "").strip()
                if real_addr and len(real_addr) >= 8 and "disamarkan" not in real_addr.lower():
                    seg = real_addr.split(",")[0].strip().lower()
                    if (len(seg) >= 8 and seg in low) or real_addr.lower() in low:
                        hard_fails.append("Kebocoran alamat asli pada caption konten daur ulang (§10.1).")

    elif channel == "followup":
        if alan_count > 1:
            hard_fails.append(f"Nama 'Alan' muncul {alan_count}× (maksimal 1×).")
        if URL_PATTERN.search(raw):
            hard_fails.append("Follow-up pra-izin sebaiknya tidak menyertakan URL langsung.")

    return {
        "passed": len(hard_fails) == 0,
        "hard_fails": hard_fails,
        "warnings": warnings,
        "word_count": word_count,
        "alan_mentions": alan_count,
    }


# ---------------------------------------------------------------------------
# Draft Generators (Cold DM #1, Follow-Up, Cold Call, Recycled Caption)
# ---------------------------------------------------------------------------
def _select_dm_opener(
    lead: dict[str, Any],
    profile: dict[str, Any],
    recent_logs: list[dict[str, Any]],
    candidates: list[dict[str, Any]],
    exclude_ids: set[str] | None = None,
) -> tuple[dict[str, Any], str]:
    """Select opener avoiding recent repeats (§11) with 20% exploration budget on regular leads (§12.3)."""
    routing = profile["routing"]
    voice = routing["voice"]
    has_web = profile["known"]["has_website"]
    cat = profile["category"].lower()
    city = profile["city"].lower()
    priority = int(lead.get("priority_score") or 50)
    blocked = set(exclude_ids or set())

    # Avoid repeating last opener ID for same category & city (§11)
    same_market_last = [
        r for r in recent_logs
        if str(r.get("category") or "").lower() == cat and str(r.get("city") or "").lower() == city
    ]
    if same_market_last:
        for pid in (same_market_last[-1].get("patterns_used") or []):
            if str(pid).startswith("OPEN-"):
                blocked.add(str(pid))
    elif recent_logs:
        for pid in (recent_logs[-1].get("patterns_used") or []):
            if str(pid).startswith("OPEN-"):
                blocked.add(str(pid))

    # 20% Exploration budget: 1 in 5 drafts uses a matching candidate on regular-priority leads (< 85)
    total_dm_logs = len(recent_logs)
    if (
        candidates
        and priority < 85
        and ((total_dm_logs + 1) % 5 == 0)
        and not profile["needs_observation"]
    ):
        matching_cands = [
            c for c in candidates
            if c.get("id") not in blocked
            and (not c.get("voice_fit") or voice in c.get("voice_fit"))
            and (
                not c.get("works_for")
                or any(tok.lower() in cat for tok in (c.get("works_for") or []))
            )
        ]
        if matching_cands:
            chosen = matching_cands[0]
            return {
                "id": chosen["id"],
                "template": chosen["template"],
                "levers": chosen.get("levers") or ["L1", "L2"],
                "is_candidate": True,
            }, str(chosen["id"])

    # Filter core openers by website state & voice fit
    eligible = [
        op for op in DM_OPENERS
        if (op["requires_web"] is None or op["requires_web"] == has_web)
        and op["id"] not in blocked
    ]
    if not eligible:
        eligible = [
            op for op in DM_OPENERS
            if (op["requires_web"] is None or op["requires_web"] == has_web)
        ] or list(DM_OPENERS)

    voice_matched = [op for op in eligible if voice in op["voices"]]
    pool = voice_matched or eligible

    # Deterministic rotation based on lead_id + log count so consecutive leads vary
    idx = (int(lead.get("id") or 0) + len(recent_logs)) % len(pool)
    return pool[idx], ""


def _render_dm_text(
    lead: dict[str, Any],
    profile: dict[str, Any],
    opener: dict[str, Any],
    ask_obj: dict[str, Any],
) -> str:
    routing = profile["routing"]
    sapaan = routing["sapaan"]
    nama_usaha = profile["display_name"]
    kategori_lower = profile["category"].lower()
    detail_ig = profile["known"]["ig_observation"] or "[isi 1 detail spesifik IG mereka]"
    ux_flaw_ramah = _soften_ux_flaw(profile["known"]["ux_flaw"])

    line1 = opener["template"].format(
        sapaan=sapaan,
        nama_usaha=nama_usaha,
        detail_ig=detail_ig,
        ux_flaw_ramah=ux_flaw_ramah,
    )
    if routing["register"] == "formal":
        bridge = DM_BRIDGES["formal"].format(nama_usaha=nama_usaha, kategori_lower=kategori_lower)
    elif routing["voice"] == "V5":
        bridge = DM_BRIDGES["bold"].format(nama_usaha=nama_usaha, kategori_lower=kategori_lower)
    else:
        bridge = DM_BRIDGES["warm"].format(nama_usaha=nama_usaha, kategori_lower=kategori_lower)

    offer = ask_obj["offer"]
    ask = ask_obj["ask"].format(sapaan=sapaan)
    text = f"{line1}\n\n{bridge} {offer}\n\n{ask}"

    # Ensure strict 45–80 word band (§7.1 & §10.1)
    wc = _count_words(text)
    if wc < 45:
        pad = (
            f"Seluruh informasi utama, jam buka, dan jalur kontak {nama_usaha} sudah kami rapikan agar nyaman dibaca di layar HP."
            if routing["register"] == "formal"
            else f"Menu utama, jam buka, dan info lokasi {nama_usaha} sudah disusun rapi supaya langsung nyaman dibaca dari layar HP."
        )
        text = f"{line1}\n\n{bridge} {pad} {offer}\n\n{ask}"
    elif wc > 80:
        # Compact bridge without losing Alan mention or "foto preview konsep"
        short_bridge = f"Saya Alan. Konsep halaman depan {nama_usaha} sudah jadi dalam bentuk foto preview konsep versi HP."
        text = f"{line1}\n\n{short_bridge} {offer}\n\n{ask}"
    return text


def draft_cold_dm(
    lead: dict[str, Any],
    log_path: Path | None = None,
    candidates_path: Path | None = None,
) -> dict[str, Any]:
    """Generate primary + alternate Cold DM #1 compliant with §7, §10.1, §11, and §12.3."""
    profile = build_client_profile(lead, is_recycled=False)
    routing = profile["routing"]
    recent_logs = _parse_recent_logs("cold_dm_1", limit=10, log_path=log_path)
    candidates = load_copy_candidates(channel="dm", candidates_path=candidates_path)

    recent_first5 = {_first_five_words(str(r.get("final_text") or r.get("original_draft") or "")) for r in recent_logs}
    ask_pool = [a for a in DM_ASKS if a["formal"] == (routing["register"] == "formal")] or DM_ASKS
    ask_obj = ask_pool[(int(lead.get("id") or 0) + len(recent_logs)) % len(ask_pool)]

    excluded: set[str] = set()
    primary_text = ""
    chosen_opener: dict[str, Any] = DM_OPENERS[0]
    exploration_id = ""
    validation: dict[str, Any] = {}

    for _round in range(3):
        chosen_opener, exploration_id = _select_dm_opener(
            lead, profile, recent_logs, candidates, exclude_ids=excluded
        )
        candidate_text = _render_dm_text(lead, profile, chosen_opener, ask_obj)
        val = validate_copy(candidate_text, "cold_dm_1", lead=lead)
        f5 = _first_five_words(candidate_text)
        primary_text = candidate_text
        validation = val
        if val["passed"] and f5 not in recent_first5:
            break
        excluded.add(chosen_opener["id"])

    # Alternate draft with a different opener & lever
    alt_excluded = excluded | {chosen_opener["id"]}
    alt_opener, _ = _select_dm_opener(lead, profile, recent_logs, [], exclude_ids=alt_excluded)
    alt_ask = ask_pool[(ask_pool.index(ask_obj) + 1) % len(ask_pool)]
    alt_text = _render_dm_text(lead, profile, alt_opener, alt_ask)

    patterns_used = [chosen_opener["id"], ask_obj["id"]]
    levers = list(chosen_opener.get("levers") or ["L1", "L2", "L3"])
    if "L3" not in levers and len(levers) < 3:
        levers.append("L3")

    copy_plan = {
        "channel": "cold_dm_1",
        "client_profile_ref": profile["display_name"],
        "voice": routing["voice"],
        "caption_voice": routing["caption_voice"],
        "sapaan": routing["sapaan"],
        "levers": levers[:3],
        "patterns_used": patterns_used,
        "specific_detail_used": not profile["needs_observation"],
        "word_count_target": "45-80",
        "needs_observation": profile["needs_observation"],
        "exploration_candidate": exploration_id,
    }

    return {
        "primary": primary_text,
        "alternate": alt_text,
        "voice": routing["voice"],
        "archetype": routing["archetype"],
        "caption_voice": routing["caption_voice"],
        "sapaan": routing["sapaan"],
        "patterns_used": patterns_used,
        "levers": levers[:3],
        "copy_plan": copy_plan,
        "validation": validation,
        "needs_observation": profile["needs_observation"],
        "exploration_candidate": exploration_id,
    }


def draft_followup(lead: dict[str, Any], log_path: Path | None = None) -> dict[str, Any]:
    """Generate §7.7 value-adding follow-up after 48h timer (no guilt / no 'cuma mengingatkan')."""
    profile = build_client_profile(lead, is_recycled=False)
    routing = profile["routing"]
    recent_logs = _parse_recent_logs("followup", limit=10, log_path=log_path)
    idx = (int(lead.get("id") or 0) + len(recent_logs)) % len(FOLLOWUP_PATTERNS)
    pat = FOLLOWUP_PATTERNS[idx]
    text = pat["template"].format(
        sapaan=routing["sapaan"],
        nama_usaha=profile["display_name"],
    )
    validation = validate_copy(text, "followup", lead=lead)
    return {
        "primary": text,
        "voice": routing["voice"],
        "sapaan": routing["sapaan"],
        "patterns_used": [pat["id"]],
        "levers": ["L3"],
        "validation": validation,
    }


def draft_cold_call(lead: dict[str, Any]) -> dict[str, Any]:
    """Generate §8 spoken 3-block Cold Call script tailored to voice & sapaan."""
    profile = build_client_profile(lead, is_recycled=False)
    routing = profile["routing"]
    sapaan = routing["sapaan"]
    name = profile["display_name"]
    obs = profile["known"]["ig_observation"]
    flaw = _soften_ux_flaw(profile["known"]["ux_flaw"])

    pembuka = (
        f"Halo, selamat siang. Dengan {sapaan} pemilik atau admin {name}? "
        f"Saya Alan. Saya tidak akan lama, sekitar 30 detik. Boleh?"
    )
    obs_sentence = (
        f"Saya sempat lihat {obs} di Instagram {name}."
        if obs
        else f"Saya sempat lihat profil {name} di Google Maps dan Instagram."
    )
    inti = (
        f"{obs_sentence} Dari situ saya buatkan foto preview konsep halaman depan versi HP, "
        f"supaya {flaw}."
    )
    tutup = (
        f"Boleh saya kirim foto preview konsepnya? Lewat WhatsApp atau DM Instagram @{settings.IG_USERNAME}, "
        f"mana yang lebih nyaman? Kalau tidak cocok tinggal diabaikan, tidak ada biaya."
    )
    return {
        "pembuka": pembuka,
        "inti": inti,
        "tutup": tutup,
        "voice": routing["voice"],
        "sapaan": sapaan,
        "patterns_used": ["CALL-3BLK"],
    }


def draft_recycled_caption(
    lead: dict[str, Any],
    art_direction: dict[str, Any],
    facts: dict[str, Any],
    handle: str | None = None,
    caption_voice_override: str | None = None,
    voice_id_override: str | None = None,
    hook_pattern_id: str | None = None,
    content_format: str = "carousel",
    creative_note: str = "",
    log_path: Path | None = None,
) -> dict[str, Any]:
    """Generate §6 recycled-content Instagram caption synced with P7 `caption_voice`, voice/hook overrides & mandatory disclosure."""
    is_recycled = bool(lead.get("is_anonymized")) or lead.get("status") == "RECYCLED_CONTENT"
    profile = build_client_profile(lead, is_recycled=is_recycled)
    routing = route_voice_for_lead(
        lead,
        caption_voice_override=caption_voice_override,
        voice_id_override=None if (voice_id_override or "").lower() in {"", "auto"} else voice_id_override,
    )
    ig_user = (handle or settings.IG_USERNAME).lstrip("@")

    brand_name = profile["display_name"]
    category = profile["category"]
    cat_lower = category.lower()
    style_name = (art_direction.get("primary_style") or "adaptive editorial").lower()
    items = facts.get("items") or []
    is_reels = str(content_format or "carousel").lower() == "reels"

    # Rotate hook types (§11) unless explicit hook_pattern_id override is requested
    recent_logs = _parse_recent_logs("caption", limit=10, log_path=log_path)
    recent_hook_ids = [
        pid
        for r in recent_logs[-2:]
        for pid in (r.get("patterns_used") or [])
        if str(pid).startswith("HOOK-")
    ]
    is_formal = routing["caption_voice"] == "formal_editorial"
    req_hook = (hook_pattern_id or "").strip().upper()
    explicit_hook = next((h for h in CAPTION_HOOKS if h["id"] == req_hook), None)
    if explicit_hook is not None:
        hook_obj = explicit_hook
    else:
        hook_pool = [h for h in CAPTION_HOOKS if (h["formal_ok"] or not is_formal)]
        filtered_hooks = [h for h in hook_pool if recent_hook_ids.count(h["id"]) < 2] or hook_pool
        hook_obj = filtered_hooks[(int(lead.get("id") or 0) + len(recent_logs)) % len(filtered_hooks)]

    cta_obj = CAPTION_CTAS[(int(lead.get("id") or 0) + len(recent_logs)) % len(CAPTION_CTAS)]

    hook_line = hook_obj["template"].format(brand_name=brand_name, cat_lower=cat_lower)
    if is_reels:
        hook_line = (
            hook_line.replace("di slide 3", "di video ini")
            .replace("4 slide, 1 ide utama:", "10 detik, 1 ide utama:")
        )
    if is_formal:
        # Enforce zero casual slang if user explicitly chose a casual hook on a formal/clinical brand
        hook_line = re.sub(r"\b(bikin)\b", "membuat", hook_line, flags=re.IGNORECASE)
        hook_line = re.sub(r"\b(nemu)\b", "menemukan", hook_line, flags=re.IGNORECASE)
        hook_line = re.sub(r"\b(kamu)\b", "Anda", hook_line, flags=re.IGNORECASE)
        hook_line = re.sub(r"\b(gw|gue|lo|lu|nih|banget)\b", "", hook_line, flags=re.IGNORECASE)
        hook_line = re.sub(r"\s{2,}", " ", hook_line).strip()

    cta_line = cta_obj["template"] if is_formal else cta_obj["casual_template"]
    if is_reels and not is_formal:
        cta_line = cta_line.replace("slide mana", "bagian mana")

    format_phrase = "video showcase singkat" if is_reels else "eksplorasi konsep"
    note_clean = " ".join((creative_note or "").strip().split())[:140]
    note_sentence = f" Fokus arahan kali ini: {note_clean.rstrip('.')}." if note_clean else ""

    if is_formal:
        item_note = (
            f"Seluruh {len(items)} layanan utama, jadwal operasional, serta jalur reservasi disusun agar langsung terbaca jernih di layar ponsel."
            if items
            else "Struktur layanan utama, jam operasional, dan jalur reservasi ditata bersih agar mudah dipahami di layar ponsel."
        )
        body_para = (
            f"Pada {format_phrase} {brand_name} ({cat_lower}), pendekatan visual {style_name} dipilih agar antarmuka mencerminkan kredibilitas dan ketenangan identitasnya. "
            f"{item_note}{note_sentence}\n\n"
            f"Proporsi tipografi, kontras warna, dan tata letak mobile ditinjau bersama Alan hingga setiap detail informasi mudah dipindai tanpa hambatan."
        )
    else:
        item_note = (
            f"Semua {len(items)} item utama, jam buka, sampai jalur akses cepat langsung terbaca rapi di layar HP tanpa perlu zoom."
            if items
            else "Struktur layanan utama, jam operasional, dan jalur akses cepat langsung terbaca tenang di layar HP."
        )
        body_para = (
            f"Di {format_phrase} {brand_name} ({cat_lower}), pendekatan visual {style_name} dipakai supaya tampilan webnya nyambung dengan karakter tempatnya—bukan template seragam. "
            f"{item_note}{note_sentence}\n\n"
            f"Tata letak dan jarak tipografinya dirapikan bareng Alan supaya begitu dibuka di HP, pengunjung langsung paham tempat ini tentang apa."
        )

    disclosure_line = (
        "(Konsep fiktif untuk studi kasus portofolio, nama dan detailnya dibuat ulang.)"
        if is_recycled
        else ""
    )

    cat_tag = re.sub(r"[^a-z0-9]+", "", cat_lower) or "bisnislokal"
    fmt_tag = "#reelswebdesign" if is_reels else "#websiteshowcase"
    hashtags = f"{fmt_tag} #webdesignindonesia #uidesign #desain{cat_tag[:16]} #{ig_user}"

    parts = [hook_line, body_para]
    if disclosure_line:
        parts.append(disclosure_line)
    parts.append(cta_line)
    parts.append(hashtags)
    full_caption = "\n\n".join(parts) + "\n"

    validation = validate_copy(full_caption, "caption", lead=lead, is_recycled=is_recycled)
    return {
        "caption": full_caption,
        "voice": routing["voice"],
        "caption_voice": routing["caption_voice"],
        "patterns_used": [hook_obj["id"], cta_obj["id"]],
        "validation": validation,
    }


# ---------------------------------------------------------------------------
# Learning Signal Logger & Automatic Outcome Sync (§12.1 & §12.2)
# ---------------------------------------------------------------------------
def summarize_human_edit(original_draft: str, final_text: str) -> str:
    """Compute concise deterministic summary comparing agent draft vs human-sent text (0 LLM tokens)."""
    from creative_agent.token_optimizer import compute_edit_delta

    return compute_edit_delta(original_draft, final_text)["summary"]


def log_copy_event(
    *,
    lead: dict[str, Any],
    channel: str,
    original_draft: str,
    final_text: str,
    voice: str = "",
    sapaan: str = "",
    patterns_used: list[str] | None = None,
    levers: list[str] | None = None,
    exploration_candidate: str = "",
    outcome: str = "no_reply",
    notes: str = "",
    is_recycled: bool = False,
    log_path: Path | None = None,
) -> dict[str, Any]:
    """Append a §12.2 `copy_log` YAML entry to `copy_learning_log.md` (strictly anonymized for recycled content)."""
    from creative_agent.token_optimizer import compute_edit_delta

    path = log_path or COPY_LEARNING_LOG_PATH
    is_anon = is_recycled or channel == "caption" or bool(lead.get("is_anonymized"))
    display_name = (
        (lead.get("anonymized_name") or f"Konsep Lokal #{lead.get('id', '')}").strip()
        if is_anon
        else (lead.get("business_name") or "").strip()
    )
    routing = route_voice_for_lead(lead)
    v_code = voice or routing["voice"]
    sap = sapaan or routing["sapaan"]
    delta = compute_edit_delta(original_draft, final_text)
    edit_sum = delta["summary"]
    now_iso = datetime.now(timezone.utc).isoformat(timespec="seconds")
    wc = _count_words(final_text or original_draft)

    # Extra privacy safety: if recycled, ensure real business_name is never written to log text
    safe_orig = original_draft or ""
    safe_final = final_text or original_draft or ""
    if is_anon:
        real_name = (lead.get("business_name") or "").strip()
        if real_name and real_name.lower() != display_name.lower():
            safe_orig = re.sub(re.escape(real_name), display_name, safe_orig, flags=re.IGNORECASE)
            safe_final = re.sub(re.escape(real_name), display_name, safe_final, flags=re.IGNORECASE)

    entry = {
        "lead_id": str(lead.get("id") or ""),
        "channel": channel,
        "date": now_iso,
        "display_name": display_name,
        "category": (lead.get("category") or "Bisnis Lokal").strip(),
        "city": (lead.get("city") or "").strip(),
        "has_website": bool(lead.get("has_website")),
        "voice": v_code,
        "sapaan": sap,
        "patterns_used": list(patterns_used or []),
        "levers": list(levers or []),
        "word_count": wc,
        "word_delta": delta["word_delta"],
        "sapaan_changed": delta["sapaan_changed"],
        "emoji_removed": delta["emoji_removed"],
        "shortened": delta["shortened"],
        "had_specific_detail": bool((lead.get("ig_observation") or "").strip()),
        "exploration_candidate": exploration_candidate or "",
        "original_draft": safe_orig,
        "final_text": safe_final,
        "edit_summary": edit_sum,
        "edit_delta": delta,
        "outcome": outcome,
        "outcome_at": "",
        "notes": notes,
    }

    yaml_block = (
        f"\n### Copy Log: {display_name} ({channel}) --- {now_iso[:10]}\n\n"
        f"```yaml\n"
        f"copy_log:\n"
        f"  lead_id: {json.dumps(entry['lead_id'])}\n"
        f"  channel: {entry['channel']}\n"
        f"  date: {json.dumps(entry['date'])}\n"
        f"  display_name: {json.dumps(entry['display_name'], ensure_ascii=False)}\n"
        f"  category: {json.dumps(entry['category'], ensure_ascii=False)}\n"
        f"  city: {json.dumps(entry['city'], ensure_ascii=False)}\n"
        f"  has_website: {'true' if entry['has_website'] else 'false'}\n"
        f"  voice: {json.dumps(entry['voice'])}\n"
        f"  sapaan: {json.dumps(entry['sapaan'], ensure_ascii=False)}\n"
        f"  patterns_used: {json.dumps(entry['patterns_used'], ensure_ascii=False)}\n"
        f"  levers: {json.dumps(entry['levers'], ensure_ascii=False)}\n"
        f"  word_count: {entry['word_count']}\n"
        f"  word_delta: {entry['word_delta']}\n"
        f"  sapaan_changed: {json.dumps(entry['sapaan_changed'], ensure_ascii=False)}\n"
        f"  emoji_removed: {entry['emoji_removed']}\n"
        f"  shortened: {'true' if entry['shortened'] else 'false'}\n"
        f"  had_specific_detail: {'true' if entry['had_specific_detail'] else 'false'}\n"
        f"  exploration_candidate: {json.dumps(entry['exploration_candidate'], ensure_ascii=False)}\n"
        f"  original_draft: {json.dumps(entry['original_draft'], ensure_ascii=False)}\n"
        f"  final_text: {json.dumps(entry['final_text'], ensure_ascii=False)}\n"
        f"  edit_summary: {json.dumps(entry['edit_summary'], ensure_ascii=False)}\n"
        f"  outcome: {entry['outcome']}\n"
        f"  outcome_at: {json.dumps(entry['outcome_at'])}\n"
        f"  notes: {json.dumps(entry['notes'], ensure_ascii=False)}\n"
        f"```\n"
    )

    with _LOG_LOCK:
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.write_text("# Copy Learning Log\n\n## Log entries\n", encoding="utf-8")
        with path.open("a", encoding="utf-8") as f:
            f.write(yaml_block)
    return entry


def update_copy_outcome(
    lead_id: int | str,
    outcome: str,
    log_path: Path | None = None,
) -> int:
    """Update `outcome` and `outcome_at` in `copy_learning_log.md` for all outreach logs of `lead_id`."""
    norm_outcome = (outcome or "").strip().lower()
    if norm_outcome not in {"interested", "ignored_48h", "declined", "replied_neutral", "no_reply"}:
        return 0
    path = log_path or COPY_LEARNING_LOG_PATH
    if not path.exists():
        return 0

    now_iso = datetime.now(timezone.utc).isoformat(timespec="seconds")
    lead_str = str(lead_id)
    updated_count = 0

    with _LOG_LOCK:
        content = path.read_text(encoding="utf-8")
        pattern = re.compile(
            rf"(lead_id:\s*\"{re.escape(lead_str)}\"\s*\n\s*channel:\s*(?:cold_dm_1|followup|cold_call)[\s\S]*?\n\s*outcome:\s*)([^\n]+)(\n\s*outcome_at:\s*)([^\n]+)",
            flags=re.MULTILINE,
        )

        def _repl(match: re.Match[str]) -> str:
            nonlocal updated_count
            updated_count += 1
            return f'{match.group(1)}{norm_outcome}{match.group(3)}"{now_iso}"'

        new_content = pattern.sub(_repl, content)
        if updated_count > 0:
            path.write_text(new_content, encoding="utf-8")
    return updated_count
