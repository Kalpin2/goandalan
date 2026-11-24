"""Role 2: Carousel Planner — 4-slide storyboard, headline options, honesty gate & editable spec."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from config import settings
from creative_agent.creative_director import CreativeDirector
from creative_agent.style_registry import STYLE_LIBRARY_12


BANNED_SALES_CTAS = (
    "dm sekarang untuk buat website",
    "dm sekarang untuk membuat website",
    "hubungi kami untuk konsultasi",
    "pesan website impianmu",
    "dm aja kalau mau ngobrol",
    "order website sekarang",
    "jasa pembuatan website",
)

# P7: Formal / clinical / institutional industries where casual "gw/lo" slang is strictly banned
FORMAL_INDUSTRY_TOKENS = (
    "klinik",
    "clinic",
    "gigi",
    "dental",
    "dokter",
    "medis",
    "estetika",
    "derma",
    "kesehatan",
    "rumah sakit",
    "hospital",
    "farmasi",
    "hukum",
    "legal",
    "notaris",
    "law",
    "keuangan",
    "finance",
    "fintech",
    "akuntan",
    "bank",
    "asuransi",
    "konsultan",
    "consulting",
    "b2b",
    "corporate",
    "arsitektur",
    "architecture",
    "properti",
    "real estate",
    "universitas",
    "pendidikan",
)

CASUAL_SLANG_PATTERN = re.compile(r"\b(gw|gue|lo|lu|nih|banget)\b", flags=re.IGNORECASE)

# P4: Flexible 4-slide sequence presets per §9 (not forced into one rigid 01_cover..04_details order)
SLIDE_SEQUENCE_PRESETS: dict[str, tuple[tuple[str, str, str], ...]] = {
    "campaign_to_website": (
        ("01_cover", "poster", "Graphic Campaign Poster"),
        ("02_context", "story", "Website Experience Story"),
        ("03_reveal", "reveal", "Actual Website — Desktop & Mobile"),
        ("04_details", "details", "Inside Section Walkthrough"),
    ),
    "reveal_first": (
        ("01_reveal", "reveal", "Actual Website — Desktop & Mobile"),
        ("02_details", "details", "Inside Section Walkthrough"),
        ("03_statement", "poster", "Brand Visual Statement"),
        ("04_experience", "story", "Website Experience Summary"),
    ),
    "story_led": (
        ("01_manifesto", "story", "Brand & Interface Concept"),
        ("02_poster", "poster", "Visual Campaign Anchor"),
        ("03_interface", "reveal", "Actual Website — Desktop & Mobile"),
        ("04_walkthrough", "details", "Inside Section Walkthrough"),
    ),
}


def select_caption_voice(industry: str, brand_name: str = "", override: str | None = None) -> str:
    """P7: Adapt caption voice by business formality (forbids 'gw/lo' on formal/clinical industries)."""
    if override in {"formal_editorial", "casual_gw"}:
        return override
    hay = f"{industry} {brand_name}".lower()
    if any(tok in hay for tok in FORMAL_INDUSTRY_TOKENS):
        return "formal_editorial"
    return "casual_gw"


def _clean_font_label(css_font: str) -> str:
    return (css_font or "").split(",")[0].strip().strip("'\"") or "Sans"


class CarouselPlanner:
    """Builds 4-slide website showcase storyboards & editable specs with strict honesty checks."""

    def _build_poster_campaign_copy(
        self,
        brand_name: str,
        industry: str,
        facts: dict[str, Any],
        typo_dir: dict[str, Any],
        niche_bp: dict[str, Any],
    ) -> dict[str, Any]:
        """Craft graphic-poster display phrases & editorial website story for Slides 1-2 & 4."""
        ind = f"{industry} {brand_name}".lower()
        items = facts.get("items") or []
        item_names = [it["name"] for it in items[:3]]
        cta = facts.get("cta_label") or "Pesan via WhatsApp"

        if any(k in ind for k in ("kopi", "coffee", "roast", "cafe")):
            return {
                "s1_top": "SEDUH",
                "s1_bottom": "DIGITAL.",
                "s1_stamp": "SLOW BAR WEB",
                "s2_kicker": f"ATMOSFER & MENU · {brand_name.upper()}",
                "s2_statement": "BUKAN MENU PDF BURAM.",
                "s2_headline_html": f"Hangatnya ruang seduh <em>{brand_name}</em>, kini terasa sejak layar pertama.",
                "s2_subhead": (
                    f"Halaman dirancang melayani tujuan utama kedai: suasana ruang, kurasi beans ({', '.join(item_names[:2]) or 'menu pilihan'}), "
                    f"jam seduh, dan jalur {cta}."
                ),
                "s2_goal_title": "Atmosfer + kurasi seduhan",
                "s2_content_title": "Beans, menu & jam seduh",
                "s2_highlights": [
                    ("01", "Atmosfer ruang nyata", "Fotografi slow bar yang membawa kehangatan kedai sebelum tamu datang."),
                    ("02", "Menu & harga terbaca", f"{len(items) or 4} sajian pilihan tampil bersih tanpa perlu zoom file PDF."),
                    ("03", "Pre-order & arah lokasi", f"Jam buka harian, alamat, dan tombol '{cta}' siap satu sentuhan."),
                ],
                "s4_headline": "Dari kurasi menu sampai jam seduh.",
            }

        if any(k in ind for k in ("barber", "pangkas", "cukur", "grooming")):
            return {
                "s1_top": "POTONG",
                "s1_bottom": "PRESISI.",
                "s1_stamp": "GROOMING WEB",
                "s2_kicker": f"GALERI & SLOT BOOKING · {brand_name.upper()}",
                "s2_statement": "TANPA ANTRE. TANPA TEBAK.",
                "s2_headline_html": f"Ketajaman craft <em>{brand_name}</em> diterjemahkan ke struktur web yang tegas.",
                "s2_subhead": (
                    f"Dibangun untuk goal barbershop: galeri craft potongan, daftar layanan & tarif bersih tanpa kotak berat, "
                    f"dan jalur cepat '{cta}'."
                ),
                "s2_goal_title": "Galeri craft + booking slot",
                "s2_content_title": "Tarif bersih tanpa kotak berat",
                "s2_highlights": [
                    ("01", "Galeri potongan & alat", "Visual craft nyata yang membangun rasa yakin sebelum duduk di kursi."),
                    ("02", "Lembar tarif editorial", f"{len(items) or 4} layanan tersusun dalam garis tipis yang langsung terpindai di HP."),
                    ("03", "Alur booking WA cepat", f"Jadwal buka jelas dan tombol '{cta}' mengunci slot tanpa antre."),
                ],
                "s4_headline": "Tarif bersih & jalur booking slot.",
            }

        if any(k in ind for k in ("estetika", "perawatan kulit", "derma", "skincare clinic", "aesthetic")):
            return {
                "s1_top": "TENANG",
                "s1_bottom": "TERUKUR.",
                "s1_stamp": "DERMA EDITORIAL",
                "s2_kicker": f"PROTOKOL & RESERVASI · {brand_name.upper()}",
                "s2_statement": "JELAS SEJAK KONSULTASI.",
                "s2_headline_html": f"Ketenangan ruang <em>{brand_name}</em> dalam tampilan web yang jernih.",
                "s2_subhead": (
                    f"Dirancang untuk kepercayaan pasien: kurasi tindakan ({', '.join(item_names[:2]) or 'perawatan kulit'}), "
                    f"durasi sesi transparan, dan jalur '{cta}'."
                ),
                "s2_goal_title": "Kredibilitas klinis + reservasi",
                "s2_content_title": "Daftar tindakan & estimasi",
                "s2_highlights": [
                    ("01", "Protokol dermatologi jelas", "Jenis perawatan, durasi sesi, dan estimasi tampil ringkas tanpa jargon rumit."),
                    ("02", "Suasana tenang & privat", "Tipografi editorial berjarak lega mencerminkan ketenangan ruang klinik."),
                    ("03", "Reservasi jadwal pasti", f"Jam praktik jelas dan tombol '{cta}' mengunci sesi tanpa antre."),
                ],
                "s4_headline": "Rincian perawatan & alur konsultasi pasien.",
            }

        if any(k in ind for k in ("pilates", "movement", "reformer", "barre", "yoga")):
            return {
                "s1_top": "GERAK",
                "s1_bottom": "SELARAS.",
                "s1_stamp": "MOVEMENT WEB",
                "s2_kicker": f"KELAS & RUANG · {brand_name.upper()}",
                "s2_statement": "TENANG. TERPANDU.",
                "s2_headline_html": f"Ritme tenang studio <em>{brand_name}</em> terasa sejak halaman pertama.",
                "s2_subhead": (
                    f"Menampilkan suasana ruang reformer, pilihan kelas kecil ({', '.join(item_names[:2]) or 'kelas harian'}), "
                    f"serta jalur cepat '{cta}'."
                ),
                "s2_goal_title": "Atmosfer studio + booking sesi",
                "s2_content_title": "Level kelas & tarif jernih",
                "s2_highlights": [
                    ("01", "Ruang reformer bercahaya", "Visual studio hangat membangun rasa tenang sebelum sesi pertama dimulai."),
                    ("02", "Level kelas mudah dipindai", f"{len(items) or 4} kelas dan paket tampil rapi untuk pemula maupun praktisi rutin."),
                    ("03", "Booking slot satu sentuhan", f"Jadwal harian dan tombol '{cta}' langsung siap di layar ponsel."),
                ],
                "s4_headline": "Pilihan kelas kecil & jadwal sesi studio.",
            }

        if any(k in ind for k in ("sourdough", "bakery", "bakehouse", "pastry", "croissant", "viennoiserie", "roti")):
            return {
                "s1_top": "HANGAT",
                "s1_bottom": "PAGI INI.",
                "s1_stamp": "BAKEHOUSE WEB",
                "s2_kicker": f"KATALOG PANGGANG · {brand_name.upper()}",
                "s2_statement": "KELUAR OVEN. SIAP DIPESAN.",
                "s2_headline_html": f"Aroma pagi <em>{brand_name}</em> tersusun dalam katalog web yang menggugah.",
                "s2_subhead": (
                    f"Menampilkan batch harian ({', '.join(item_names[:2]) or 'sourdough & pastry'}), "
                    f"jam keluar oven, harga jernih, dan jalur '{cta}'."
                ),
                "s2_goal_title": "Katalog panggang + pre-order",
                "s2_content_title": "Menu harian & jadwal oven",
                "s2_highlights": [
                    ("01", "Foto tekstur roti nyata", "Sourdough dan pastry tampil tajam tanpa tersembunyi di balik PDF."),
                    ("02", "Harga & berat transparan", f"{len(items) or 4} sajian harian tersusun bersih dengan label batch yang jelas."),
                    ("03", "Pre-order sebelum habis", f"Jam buka bakehouse dan tombol '{cta}' mempercepat pemesanan loaf."),
                ],
                "s4_headline": "Katalog sourdough harian & alur pre-order.",
            }

        if any(k in ind for k in ("bengkel", "motor custom", "custom garage", "garage", "cafe racer", "scrambler", "kustom")):
            return {
                "s1_top": "RAKIT",
                "s1_bottom": "MESIN.",
                "s1_stamp": "CUSTOM GARAGE",
                "s2_kicker": f"WORKSHOP & SPEK · {brand_name.upper()}",
                "s2_statement": "RAPI DI RANGKA. JUJUR DI MESIN.",
                "s2_headline_html": f"Karakter garang <em>{brand_name}</em> diterjemahkan ke antarmuka tegas.",
                "s2_subhead": (
                    f"Fokus pada kebutuhan rider: layanan fabrikasi & bangun motor ({', '.join(item_names[:2]) or 'custom build'}), "
                    f"estimasi transparan, dan '{cta}'."
                ),
                "s2_goal_title": "Showcase build + konsultasi WA",
                "s2_content_title": "Daftar layanan & estimasi",
                "s2_highlights": [
                    ("01", "Visual workshop autentik", "Foto motor custom dan detail las membangun respek sebelum rider mampir."),
                    ("02", "Spek layanan tanpa basa-basi", f"{len(items) or 4} layanan fabrikasi dan tune-up tersaji langsung dengan kisaran biaya."),
                    ("03", "Cek slot bengkel cepat", f"Jam workshop dan tombol '{cta}' langsung terhubung ke mekanik utama."),
                ],
                "s4_headline": "Rincian layanan workshop & estimasi build.",
            }

        short_brand = brand_name.split()[0].upper() if brand_name else "BRAND"
        return {
            "s1_top": short_brand[:10],
            "s1_bottom": "CONCEPT.",
            "s1_stamp": f"{industry.upper()[:14]}",
            "s2_kicker": f"ARAH WEB · {brand_name.upper()}",
            "s2_statement": "JELAS DI LAYAR HP.",
            "s2_headline_html": f"Karakter asli <em>{brand_name}</em> dalam satu antarmuka tenang.",
            "s2_subhead": niche_bp.get("primary_business_goal") or "Layanan inti, jam operasional, lokasi, dan tombol aksi disusun tanpa clutter.",
            "s2_goal_title": "Hierarki sesuai karakter bisnis",
            "s2_content_title": "Informasi layanan terkurasi",
            "s2_highlights": [
                ("01", "Fokus tujuan bisnis", niche_bp.get("primary_business_goal") or "Informasi utama langsung terbaca."),
                ("02", "Struktur tanpa clutter", f"{len(items) or 4} layanan/produk tampil rapi tanpa kotak berlebihan."),
                ("03", "Aksi mobile langsung", f"Tombol '{cta}' selalu terjangkau di layar smartphone."),
            ],
            "s4_headline": "Detail bagian dalam pengalaman web.",
        }

    def generate_headline_alternatives(self, brand_name: str, industry: str) -> list[dict[str, str]]:
        """Generate 3 specific, non-clickbait cover headline alternatives."""
        ind = (industry or "").lower()
        if any(k in ind for k in ("kopi", "coffee", "roast", "cafe")):
            return [
                {
                    "hook_html": f"Ruang digital sehangat seduhan <em>{brand_name}.</em>",
                    "sub": "Menu harian, jam buka, dan jalur pesan cepat disusun dalam satu tampilan tenang.",
                },
                {
                    "hook_html": f"Cerita kopi <em>{brand_name}</em>, kini dalam satu halaman bersih.",
                    "sub": "Dari pilihan seduhan sampai lokasi kedai, semuanya langsung terbaca di layar HP.",
                },
                {
                    "hook_html": f"Pengalaman berkunjung ke <em>{brand_name}</em> dimulai dari layar pertama.",
                    "sub": "Konsep web mobile-first yang membawa suasana kedai ke genggaman pelanggan.",
                },
            ]
        if any(k in ind for k in ("barber", "pangkas", "cukur", "grooming")):
            return [
                {
                    "hook_html": f"Dari potong rapi ke alur booking <em>{brand_name}.</em>",
                    "sub": "Tarif layanan, jam operasional, dan tombol reservasi langsung terbaca di layar HP.",
                },
                {
                    "hook_html": f"Tampilan setajam hasil potongan <em>{brand_name}.</em>",
                    "sub": "Layanan grooming, jadwal buka, dan akses booking tersusun rapi tanpa langkah berbelit.",
                },
                {
                    "hook_html": f"Cara lebih ringkas mengenal layanan <em>{brand_name}.</em>",
                    "sub": "Struktur presisi untuk cek paket perawatan dan amankan slot kunjungan.",
                },
            ]
        if any(k in ind for k in ("klinik", "clinic", "gigi", "dental", "medis", "skin", "estetika", "derma")):
            return [
                {
                    "hook_html": f"Kejelasan yang menenangkan untuk <em>{brand_name}.</em>",
                    "sub": "Informasi perawatan, jam praktik, dan konsultasi awal tertata bersih tanpa kesan rumit.",
                },
                {
                    "hook_html": f"Informasi pasien <em>{brand_name}</em>, tepat di tempat yang dicari.",
                    "sub": "Dirancang tenang dan terstruktur supaya calon pasien langsung paham alur layanan.",
                },
                {
                    "hook_html": f"Layanan <em>{brand_name}</em> dalam tampilan yang jernih dan terpercaya.",
                    "sub": "Jenis tindakan, jadwal buka, dan jalur reservasi tampil rapi di layar HP.",
                },
            ]
        if any(k in ind for k in ("pilates", "movement", "reformer", "barre", "yoga")):
            return [
                {
                    "hook_html": f"Ritme gerak tenang di <em>{brand_name}.</em>",
                    "sub": "Jadwal kelas kecil, profil reformer, dan booking sesi tersaji bersih di layar HP.",
                },
            ]
        if any(k in ind for k in ("sourdough", "bakery", "bakehouse", "pastry", "croissant", "roti")):
            return [
                {
                    "hook_html": f"Keluar oven hangat setiap pagi di <em>{brand_name}.</em>",
                    "sub": "Daftar sourdough harian, jadwal batch oven, dan pre-order WA langsung terbaca rapi.",
                },
            ]
        if any(k in ind for k in ("bengkel", "motor custom", "custom garage", "garage", "kustom")):
            return [
                {
                    "hook_html": f"Rapi di rangka, jujur di mesin bersama <em>{brand_name}.</em>",
                    "sub": "Layanan fabrikasi, estimasi build, dan jadwal slot bengkel jelas di layar HP.",
                },
            ]
        return [
            {
                "hook_html": f"Wajah digital yang selaras dengan karakter <em>{brand_name}.</em>",
                "sub": f"Konsep antarmuka untuk {industry.lower()} dengan hierarki informasi yang langsung ke inti.",
            },
            {
                "hook_html": f"Dari informasi tersebar ke satu pengalaman jelas di <em>{brand_name}.</em>",
                "sub": "Layanan utama, lokasi, dan akses kontak tersusun bersih untuk desktop maupun HP.",
            },
            {
                "hook_html": f"Melihat <em>{brand_name}</em> dari sudut pandang pengunjung mobile.",
                "sub": "Antarmuka ringan yang memprioritaskan keterbacaan dan kemudahan navigasi.",
            },
        ]

    def build_verified_walkthrough(self, facts: dict[str, Any], brand_name: str) -> list[dict[str, str]]:
        """Extract strictly verified feature highlights from actual HTML DOM facts (zero invention)."""
        items = facts.get("items") or []
        info_rows = facts.get("info_rows") or []
        cta_label = facts.get("cta_label") or "Tombol Aksi Utama"
        faq_count = int(facts.get("faq_count") or 0)

        points: list[dict[str, str]] = []
        if items:
            sample_names = ", ".join(it["name"] for it in items[:2])
            points.append(
                {
                    "num": "01 / KATALOG",
                    "title": f"{len(items)} item tampil langsung",
                    "desc": f"Termasuk {sample_names} dengan detail yang langsung terbaca tanpa zoom.",
                }
            )
        else:
            points.append(
                {
                    "num": "01 / HIERARKI",
                    "title": "Fokus above-the-fold",
                    "desc": f"Identitas {brand_name} dan informasi utama langsung terlihat di layar pertama.",
                }
            )

        if info_rows:
            labels = ", ".join(r["label"].title() for r in info_rows[:3])
            points.append(
                {
                    "num": "02 / INFO INTI",
                    "title": "Kartu ringkas satu pandang",
                    "desc": f"Menampilkan {labels} secara terstruktur di sisi hero.",
                }
            )
        else:
            points.append(
                {
                    "num": "02 / RESPONSIF",
                    "title": "Proporsi desktop & mobile",
                    "desc": "Tipografi dan jarak elemen disesuaikan untuk kenyamanan baca di HP.",
                }
            )

        if faq_count > 0:
            points.append(
                {
                    "num": "03 / INTERAKSI",
                    "title": f"FAQ + '{cta_label}'",
                    "desc": f"Memuat {faq_count} accordion pertanyaan umum dan jalur akses langsung.",
                }
            )
        else:
            points.append(
                {
                    "num": "03 / AKSI LANGSUNG",
                    "title": f"Tombol '{cta_label}'",
                    "desc": "Diposisikan konsisten agar pengunjung langsung melihat langkah berikutnya.",
                }
            )
        return points[:3]

    def build_caption(
        self,
        brand_name: str,
        industry: str,
        art_direction: dict[str, Any],
        facts: dict[str, Any],
        handle: str | None = None,
        caption_voice: str | None = None,
    ) -> str:
        """P7: Adaptive showcase caption (formal editorial for clinical/B2B; casual 'gw' for indie/creative)."""
        ig_user = (handle or settings.IG_USERNAME).lstrip("@")
        voice = select_caption_voice(industry, brand_name, override=caption_voice)
        status_phrase = "preview demo website" if facts.get("is_full_demo") else "eksplorasi konsep website"
        style_name = art_direction.get("primary_style", "adaptive showcase").lower()
        items = facts.get("items") or []

        if voice == "formal_editorial":
            item_note = (
                f"Seluruh {len(items)} layanan utama, jadwal operasional, serta jalur reservasi disusun agar langsung terbaca jernih di layar ponsel."
                if items
                else "Struktur layanan utama, jam operasional, dan jalur reservasi ditata bersih agar mudah dipahami di layar ponsel."
            )
            return (
                f"{status_phrase.capitalize()} untuk {brand_name} ({industry.lower()}).\n\n"
                f"Pendekatan visual {style_name} dipilih agar antarmuka mencerminkan kredibilitas dan ketenangan identitas {brand_name}. "
                f"{item_note}\n\n"
                f"Proporsi tipografi, kontras warna, dan tata letak mobile ditinjau bersama Alan hingga setiap detail informasi mudah dipindai tanpa hambatan.\n\n"
                f"Geser hingga slide terakhir untuk melihat tampilan antarmuka pada desktop maupun mobile.\n\n"
                f"#websiteshowcase #webdesignindonesia #uidesign #{ig_user}\n"
            )

        item_note = (
            f"semua {len(items)} item utama, jam operasional, sampai jalur akses cepat langsung kelihatan rapi di layar HP tanpa perlu zoom."
            if items
            else "struktur layanan utama, jam operasional, dan jalur akses cepat langsung terbaca tenang di layar HP."
        )
        return (
            f"{status_phrase} buat {brand_name} ({industry.lower()}).\n\n"
            f"kali ini gw bawa pendekatan visual {style_name} supaya karakter websitenya beneran nyambung sama identitas tempatnya—bukan sekadar pakai satu template untuk semua bisnis. "
            f"{item_note}\n\n"
            f"draft awal tadi sebenarnya udah cukup bersih, tapi Alan tetap ngotot ngerapihin proporsi jarak di layar mobile sampai tiap bagian terasa pas dilihat.\n\n"
            f"geser sampai slide terakhir buat lihat detail tampilannya di desktop dan HP. menurut lo arah visualnya udah cocok sama karakter {brand_name}?\n\n"
            f"#websiteshowcase #webdesignindonesia #uidesign #{ig_user}\n"
        )

    def build_spec(
        self,
        brief: dict[str, Any],
        art_direction: dict[str, Any],
        facts: dict[str, Any],
        assets: dict[str, Any],
        issue_num: int = 1,
        selected_headline_idx: int = 0,
        allow_sales_cta: bool = False,
        slide_sequence: str | list[tuple[str, str, str]] | None = None,
        caption_voice: str | None = None,
    ) -> dict[str, Any]:
        """Create the complete editable 4-slide `carousel_spec.json` with flexible §9 slide ordering."""
        brand_name = brief["brand_name"]
        industry = brief["industry"]
        city = brief.get("city", "")
        status_badge = facts.get("project_status") or ("DEMO PREVIEW" if facts.get("is_full_demo") else "WEBSITE CONCEPT")
        resolved_voice = select_caption_voice(industry, brand_name, override=caption_voice or brief.get("caption_voice"))

        headlines = self.generate_headline_alternatives(brand_name, industry)
        chosen_hl = headlines[min(max(0, selected_headline_idx), len(headlines) - 1)]
        walkthrough = self.build_verified_walkthrough(facts, brand_name)
        cta_txt = facts.get("cta_label") or "Aksi Utama"
        item_cnt = len(facts.get("items") or [])
        step2_desc = (
            f"{item_cnt} layanan/menu langsung terbaca rapi tanpa perlu membuka dokumen tambahan."
            if item_cnt
            else "Informasi inti bisnis langsung tersusun rapi di atas lipatan layar."
        )

        fonts = art_direction["fonts"]
        d_font = _clean_font_label(fonts["font_display"])
        b_font = _clean_font_label(fonts["font_body"])
        m_font = _clean_font_label(fonts["font_mono"])
        font_pair_label = f"{d_font} + {m_font}" if d_font.lower() == b_font.lower() else f"{d_font} + {b_font}"

        handle = f"@{settings.IG_USERNAME}"
        domain = (brief.get("domain") or f"{re.sub(r'[^a-z0-9]+', '-', brand_name.lower()).strip('-')}.id")
        comps = art_direction["compositions"]
        typo_dir = art_direction.get("typography_direction") or {}
        niche_bp = art_direction.get("niche_blueprint") or {}
        behaviors = typo_dir.get("composition_behavior") or [
            comps["slide_1"],
            comps["slide_2"],
            comps["slide_3"],
            comps["slide_4"],
        ]
        poster_words = self._build_poster_campaign_copy(brand_name, industry, facts, typo_dir, niche_bp)

        # P4: Build modular slide payloads by kind, then order/name flexibly per slide_sequence
        if isinstance(slide_sequence, list) and len(slide_sequence) == 4:
            seq_plan = tuple(slide_sequence)
        else:
            seq_key = slide_sequence if isinstance(slide_sequence, str) and slide_sequence in SLIDE_SEQUENCE_PRESETS else "campaign_to_website"
            seq_plan = SLIDE_SEQUENCE_PRESETS[seq_key]

        kind_payloads: dict[str, dict[str, Any]] = {
            "poster": {
                "composition": behaviors[0] if len(behaviors) > 0 else comps["slide_1"],
                "kicker": f"{status_badge} · {industry}",
                "poster_display_top": poster_words["s1_top"],
                "poster_display_bottom": poster_words["s1_bottom"],
                "poster_stamp": poster_words["s1_stamp"],
                "headline_html": chosen_hl["hook_html"],
                "subhead": chosen_hl["sub"],
                "visual": assets.get("hero_photo") or assets.get("desktop_screenshot", "desktop.png"),
                "visual_preview": assets.get("desktop_screenshot", "desktop.png"),
            },
            "story": {
                "composition": behaviors[1] if len(behaviors) > 1 else comps["slide_2"],
                "kicker": poster_words["s2_kicker"],
                "poster_statement": poster_words["s2_statement"],
                "headline_html": poster_words["s2_headline_html"],
                "subhead": poster_words["s2_subhead"],
                "story_highlights": poster_words["s2_highlights"],
                "journey_steps": [
                    {"num": "01 / TUJUAN WEB", "title": poster_words["s2_goal_title"], "desc": niche_bp.get("primary_business_goal") or art_direction["direction_summary"]},
                    {"num": "02 / ISI NYATA", "title": poster_words["s2_content_title"], "desc": step2_desc},
                    {"num": "03 / AKSI CEPAT", "title": f"Jalur '{cta_txt}'", "desc": "Langsung terbaca di layar HP tanpa perlu cari link berbelit."},
                ],
                "visual": assets.get("secondary_photo") or assets.get("mobile_screenshot", "mobile.png"),
                "visual_mobile": assets.get("mobile_screenshot", "mobile.png"),
            },
            "reveal": {
                "composition": behaviors[2] if len(behaviors) > 2 else comps["slide_3"],
                "kicker": f"ACTUAL INTERFACE · {domain}",
                "headline_html": f"Desktop &amp; mobile untuk {brand_name}.",
                "subhead": f"{typo_dir.get('primary_art_direction') or art_direction['primary_style']} · {status_badge}",
                "visual_desktop": assets.get("desktop_screenshot", "desktop.png"),
                "visual_mobile": assets.get("mobile_screenshot", "mobile.png"),
                "visual_detail": assets.get("desktop_detail", "detail_desktop.png"),
            },
            "details": {
                "composition": behaviors[3] if len(behaviors) > 3 else comps["slide_4"],
                "kicker": "INSIDE THE EXPERIENCE",
                "headline_html": poster_words["s4_headline"],
                "closing_label": "Website Concept",
                "walkthrough_points": walkthrough,
                "visual_desktop_detail": assets.get("desktop_detail", "detail_desktop.png"),
                "visual_mobile_detail": assets.get("mobile_detail", "detail_mobile.png"),
            },
        }

        ordered_slides: list[dict[str, Any]] = []
        for idx, (s_name, s_kind, s_role) in enumerate(seq_plan, start=1):
            base = dict(kind_payloads.get(s_kind, kind_payloads["details"]))
            ordered_slides.append(
                {
                    "n": idx,
                    "name": s_name,
                    "kind": s_kind,
                    "role": s_role,
                    **base,
                }
            )

        spec: dict[str, Any] = {
            "schema_version": "3.1",
            "project": {
                "brand_name": brand_name,
                "industry": industry,
                "city": city,
                "domain": domain,
                "project_status": status_badge,
                "is_full_demo": bool(facts.get("is_full_demo")),
                "issue_num": issue_num,
                "handle": handle,
                "caption_voice": resolved_voice,
                "slide_sequence": slide_sequence if isinstance(slide_sequence, str) else "custom",
                "allow_sales_cta": allow_sales_cta,
            },
            "creative_direction": {
                **art_direction,
                "font_pair_label": (typo_dir.get("fonts") or {}).get("font_pair_label") or font_pair_label,
            },
            "typography_direction": typo_dir,
            "niche_blueprint": niche_bp,
            "assets": assets,
            "headline_alternatives": headlines,
            "slides": ordered_slides,
            "caption": self.build_caption(
                brand_name, industry, art_direction, facts, caption_voice=resolved_voice
            ),
            "facts": facts,
        }

        self.enforce_honesty_and_showcase_rules(spec)
        return spec

    def enforce_honesty_and_showcase_rules(self, spec: dict[str, Any]) -> None:
        """Guardrail check: no unsolicited sales CTAs, formal voice enforcement (P7), max 1 Alan mention."""
        if not spec["project"].get("allow_sales_cta"):
            all_slides_text = json.dumps(spec.get("slides") or [], ensure_ascii=False).lower()
            for banned in BANNED_SALES_CTAS:
                if banned in all_slides_text:
                    raise ValueError(f"Slide mengandung CTA iklan jasa terlarang: '{banned}'")

            cap_lower = (spec.get("caption") or "").lower()
            for banned in BANNED_SALES_CTAS:
                if banned in cap_lower:
                    raise ValueError(f"Caption mengandung CTA iklan jasa terlarang: '{banned}'")

        if spec["project"].get("caption_voice") == "formal_editorial":
            slang_hits = CASUAL_SLANG_PATTERN.findall(spec.get("caption") or "")
            if slang_hits:
                raise ValueError(
                    f"Caption formal/klinis dilarang memakai slang kasual: {sorted(set(slang_hits))}"
                )

        alan_count = len(re.findall(r"\balan\b", spec.get("caption", ""), flags=re.IGNORECASE))
        if alan_count > 1:
            raise ValueError(f"Caption menyebut Alan {alan_count} kali (maksimal 1 kali).")

    def revise_spec(self, spec: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
        """Apply targeted revisions to an existing spec WITHOUT restarting discovery."""
        updated = json.loads(json.dumps(spec))
        director = CreativeDirector()

        if patch.get("style_key") and patch["style_key"] in STYLE_LIBRARY_12:
            new_ad = director.build_art_direction(
                updated["project"],
                chosen_style=patch["style_key"],
                storytelling_override=patch.get("storytelling_key"),
                reference_image=patch.get("reference_image") or updated["creative_direction"].get("reference_image"),
                palette_override=patch.get("palette"),
            )
            d_font = _clean_font_label(new_ad["fonts"]["font_display"])
            b_font = _clean_font_label(new_ad["fonts"]["font_body"])
            m_font = _clean_font_label(new_ad["fonts"]["font_mono"])
            new_ad["font_pair_label"] = f"{d_font} + {m_font}" if d_font.lower() == b_font.lower() else f"{d_font} + {b_font}"
            updated["creative_direction"] = new_ad
            for idx, key in enumerate(("slide_1", "slide_2", "slide_3", "slide_4")):
                updated["slides"][idx]["composition"] = new_ad["compositions"][key]
            updated["slides"][3]["closing_label"] = new_ad["closing_label"]

        if patch.get("palette"):
            updated["creative_direction"]["palette"].update(patch["palette"])

        if patch.get("slides"):
            for slide_patch in patch["slides"]:
                n = int(slide_patch.get("n", 0))
                if 1 <= n <= 4:
                    target = updated["slides"][n - 1]
                    for field in ("headline_html", "subhead", "kicker", "composition", "closing_label", "walkthrough_points"):
                        if field in slide_patch:
                            target[field] = slide_patch[field]

        if "caption" in patch and patch["caption"]:
            updated["caption"] = patch["caption"]

        self.enforce_honesty_and_showcase_rules(updated)
        return updated

    def format_storyboard_markdown(self, spec: dict[str, Any]) -> str:
        """Render the Tahap 6 storyboard table for interactive review."""
        cd = spec["creative_direction"]
        rows = [
            "| Slide | Tujuan | Headline | Visual Utama | Komposisi |",
            "| :---: | :--- | :--- | :--- | :--- |",
        ]
        for s in spec["slides"]:
            hl_plain = re.sub(r"<[^>]+>", "", s.get("headline_html", ""))
            vis = s.get("visual") or s.get("visual_desktop") or s.get("visual_desktop_detail") or "-"
            rows.append(f"| 0{s['n']} | {s['role']} | {hl_plain} | `{Path(str(vis)).name}` | `{s['composition']}` |")

        return (
            f"**Gaya Visual:** {cd['primary_style']} + {cd['secondary_style']}  \n"
            f"**Storytelling:** {cd['storytelling_method']}  \n"
            f"**Palet:** `{cd['palette']['bg']}` · `{cd['palette']['surface']}` · `{cd['palette']['accent']}` · `{cd['palette']['accent_2']}`  \n"
            f"**Tipografi:** {cd['font_pair_label']}\n\n"
            + "\n".join(rows)
        )

    def save_spec(self, spec: dict[str, Any], out_path: Path) -> Path:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(spec, indent=2, ensure_ascii=False), encoding="utf-8")
        return out_path
