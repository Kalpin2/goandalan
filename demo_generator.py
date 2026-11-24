"""Anti-Slop, Goal-Driven Multi-Style Demo Site Generator for @goandalan.

Pre-INTERESTED (Optional Stage A — CONCEPT_READY):
    Only prepares lightweight metadata or optional editorial above-the-fold concept page
    (`site/demos/<slug>/concept.html`) when needed for the Cold DM queue.
    NEVER generates `index.html` landing page before the prospect responds `INTERESTED`.

Stage B — INTERESTED -> FULL_DEMO_READY (Pre-DP Single-Page Landing Demo, `production=False`):
    Generates a concise, fast-rendering 1-page landing page demo (`site/demos/<slug>/index.html`)
    focused on first impression: Hero + Main Services/Menu Summary + Location/Hours, Compact FAQ
    & WhatsApp Contact CTA, with Niche-to-Goal anti-slop styling and floating badge
    `preview konsep oleh @goandalan · mikir bareng alan`.

Stage C — DP_PAID -> WON (Full Production Website, `production=True`):
    Builds the complete multi-section production website per client requirements
    (including `#cerita` craft/space band) and strips the `@goandalan` concept watermark pill.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import shutil
from pathlib import Path
from typing import Any
from urllib.parse import quote

import database as db
from config import settings
from creative_agent.niche_resolver import resolve_niche_blueprint


# 8 Boutique Multi-Style Design Themes (Zero AI-Slop purple gradients; anti-boxy editorial surfaces)
STYLE_THEMES: dict[str, dict[str, Any]] = {
    "warm_organic_hospitality": {
        "label": "Warm Organic Hospitality",
        "source": "Editorial Botanical Roastery Warmth (Warm Linen + Deep Espresso + Terracotta)",
        "fonts_url": "https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,500;0,9..144,700;1,9..144,500&family=IBM+Plex+Mono:wght@400;500&family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap",
        "font_display": "'Fraunces', Georgia, serif",
        "font_body": "'Plus Jakarta Sans', system-ui, sans-serif",
        "font_mono": "'IBM Plex Mono', monospace",
        "bg": "#FAF6EE",
        "surface": "#F2EADF",
        "surface_alt": "#E9DFCF",
        "ink": "#1C1917",
        "muted": "#5A524B",
        "accent": "#284B36",
        "accent_2": "#C45A32",
        "accent_ink": "#FAF6EE",
        "badge_bg": "rgba(40, 75, 54, 0.10)",
        "badge_ink": "#284B36",
        "border": "rgba(28, 25, 23, 0.14)",
        "footer_bg": "#1B1613",
        "footer_ink": "#FAF6EE",
        "radius": "10px",
        "btn_radius": "999px",
        "layout": "editorial_hospitality",
        "uppercase_display": False,
    },
    "figcraft_sharp_grid": {
        "label": "FigCraft Sharp Architectural",
        "source": "Swiss Architectural Craft Grid (0px Precision Rules + Bone Chalk + Signal Vermilion)",
        "fonts_url": "https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@600;700;800&family=IBM+Plex+Mono:wght@400;500;600&family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap",
        "font_display": "'Barlow Condensed', 'Plus Jakarta Sans', sans-serif",
        "font_body": "'Plus Jakarta Sans', system-ui, sans-serif",
        "font_mono": "'IBM Plex Mono', monospace",
        "bg": "#F6F4EE",
        "surface": "#ECE9E0",
        "surface_alt": "#E3DFD3",
        "ink": "#121417",
        "muted": "#4C5159",
        "accent": "#C93E23",
        "accent_2": "#121417",
        "accent_ink": "#FFFFFF",
        "badge_bg": "#ECE9E0",
        "badge_ink": "#121417",
        "border": "rgba(18, 20, 23, 0.18)",
        "footer_bg": "#121417",
        "footer_ink": "#F6F4EE",
        "radius": "0px",
        "btn_radius": "0px",
        "layout": "architectural_craft",
        "uppercase_display": True,
    },
    "dark_moody_luxury": {
        "label": "Dark Moody Luxury",
        "source": "Boutique Dark Editorial (Obsidian + Brushed Brass Gold)",
        "fonts_url": "https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,500;0,600;1,500&family=IBM+Plex+Mono:wght@400;500&family=Manrope:wght@400;500;600&display=swap",
        "font_display": "'Cormorant Garamond', Georgia, serif",
        "font_body": "'Manrope', sans-serif",
        "font_mono": "'IBM Plex Mono', monospace",
        "bg": "#10100F",
        "surface": "#181715",
        "surface_alt": "#22201D",
        "ink": "#F3EFE6",
        "muted": "#A9A194",
        "accent": "#C8A96E",
        "accent_2": "#E5CFA3",
        "accent_ink": "#11100E",
        "badge_bg": "rgba(200, 169, 110, 0.14)",
        "badge_ink": "#E5CFA3",
        "border": "rgba(243, 239, 230, 0.16)",
        "footer_bg": "#090908",
        "footer_ink": "#F3EFE6",
        "radius": "2px",
        "btn_radius": "2px",
        "layout": "dark_editorial",
        "uppercase_display": False,
    },
    "clean_swiss_minimal": {
        "label": "Clean Swiss Minimal",
        "source": "Swiss Typographic Grid (High-Contrast Clinical / Studio)",
        "fonts_url": "https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=Inter:wght@400;500;600&family=Space+Grotesk:wght@500;600;700&display=swap",
        "font_display": "'Space Grotesk', Inter, sans-serif",
        "font_body": "'Inter', system-ui, sans-serif",
        "font_mono": "'IBM Plex Mono', monospace",
        "bg": "#FFFFFF",
        "surface": "#F3F6F8",
        "surface_alt": "#E8EFF2",
        "ink": "#0E1318",
        "muted": "#505B67",
        "accent": "#0F5C6E",
        "accent_2": "#1546A0",
        "accent_ink": "#FFFFFF",
        "badge_bg": "#E8F3F5",
        "badge_ink": "#0F5C6E",
        "border": "#D9E1E8",
        "footer_bg": "#0E1318",
        "footer_ink": "#FFFFFF",
        "radius": "4px",
        "btn_radius": "4px",
        "layout": "swiss_editorial",
        "uppercase_display": False,
    },
    "neo_brutalist_street": {
        "label": "Neo-Brutalist Street",
        "source": "Bold Editorial Street Type (High Contrast + Crisp Rules)",
        "fonts_url": "https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@500;600&family=Space+Grotesk:wght@400;500;600;700&family=Syne:wght@700;800&display=swap",
        "font_display": "'Syne', 'Space Grotesk', sans-serif",
        "font_body": "'Space Grotesk', sans-serif",
        "font_mono": "'IBM Plex Mono', monospace",
        "bg": "#F5F2E9",
        "surface": "#ECE7D9",
        "surface_alt": "#D9F99D",
        "ink": "#111111",
        "muted": "#454545",
        "accent": "#DF5224",
        "accent_2": "#111111",
        "accent_ink": "#FFFFFF",
        "badge_bg": "#D9F99D",
        "badge_ink": "#111111",
        "border": "#111111",
        "footer_bg": "#111111",
        "footer_ink": "#F5F2E9",
        "radius": "0px",
        "btn_radius": "0px",
        "layout": "architectural_craft",
        "uppercase_display": True,
    },
    "vibrant_modern_cafe": {
        "label": "Vibrant Modern Cafe",
        "source": "Warm Crema + Espresso + Terracotta Editorial",
        "fonts_url": "https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,600;12..96,700&family=IBM+Plex+Mono:wght@400;500&family=Plus+Jakarta+Sans:wght@400;500;600&display=swap",
        "font_display": "'Bricolage Grotesque', sans-serif",
        "font_body": "'Plus Jakarta Sans', sans-serif",
        "font_mono": "'IBM Plex Mono', monospace",
        "bg": "#FFF8F0",
        "surface": "#F6E7D7",
        "surface_alt": "#EDD7C0",
        "ink": "#2B1B15",
        "muted": "#6E5449",
        "accent": "#C84B31",
        "accent_2": "#284B36",
        "accent_ink": "#FFF8F0",
        "badge_bg": "rgba(200, 75, 49, 0.12)",
        "badge_ink": "#9C321D",
        "border": "rgba(43, 27, 21, 0.15)",
        "footer_bg": "#2B1B15",
        "footer_ink": "#FFF8F0",
        "radius": "12px",
        "btn_radius": "999px",
        "layout": "editorial_hospitality",
        "uppercase_display": False,
    },
    "modern_editorial": {
        "label": "Modern Editorial",
        "source": "Indie Magazine Warm Paper & Deep Olive",
        "fonts_url": "https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&family=IBM+Plex+Mono:wght@400;500&family=Plus+Jakarta+Sans:wght@400;500;600&display=swap",
        "font_display": "'Instrument Serif', Georgia, serif",
        "font_body": "'Plus Jakarta Sans', sans-serif",
        "font_mono": "'IBM Plex Mono', monospace",
        "bg": "#F6F3EC",
        "surface": "#EDE8DD",
        "surface_alt": "#E5DFD2",
        "ink": "#1E1E1E",
        "muted": "#625E56",
        "accent": "#3B4D39",
        "accent_2": "#9A523B",
        "accent_ink": "#F6F3EC",
        "badge_bg": "rgba(59, 77, 57, 0.12)",
        "badge_ink": "#3B4D39",
        "border": "rgba(30, 30, 30, 0.14)",
        "footer_bg": "#1E1E1E",
        "footer_ink": "#F6F3EC",
        "radius": "6px",
        "btn_radius": "999px",
        "layout": "editorial_hospitality",
        "uppercase_display": False,
    },
    "coastal_terracotta": {
        "label": "Coastal Terracotta & Linen",
        "source": "Sun-Baked Sand + Clay Terracotta + Coastal Teal",
        "fonts_url": "https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&family=Playfair+Display:ital,wght@0,500;0,600;1,500&display=swap",
        "font_display": "'Playfair Display', Georgia, serif",
        "font_body": "'DM Sans', sans-serif",
        "font_mono": "'IBM Plex Mono', monospace",
        "bg": "#F8F1E7",
        "surface": "#EFE3D3",
        "surface_alt": "#E5D4BE",
        "ink": "#2B211B",
        "muted": "#6C5B4F",
        "accent": "#9A523B",
        "accent_2": "#2F5D5B",
        "accent_ink": "#F8F1E7",
        "badge_bg": "rgba(47, 93, 91, 0.14)",
        "badge_ink": "#2F5D5B",
        "border": "rgba(43, 33, 27, 0.14)",
        "footer_bg": "#2B211B",
        "footer_ink": "#F8F1E7",
        "radius": "8px",
        "btn_radius": "999px",
        "layout": "editorial_hospitality",
        "uppercase_display": False,
    },
}


CATEGORY_PRESETS: dict[str, dict[str, Any]] = {
    "coffee": {
        "match": ("kopi", "coffee", "roast", "cafe", "kafe", "espresso", "matcha", "kedai"),
        "preferred_styles": ["warm_organic_hospitality", "vibrant_modern_cafe", "modern_editorial"],
        "badge": "SLOW BAR & ROASTERY",
        "headline": "Seduhan tenang, biji segar dari sangrai pekan ini.",
        "sub": "Ruang mampir untuk kerja fokus, ngobrol pelan, atau ambil es kopi susu sebelum mulai hari—menu harian, notes rasa, dan jam seduh langsung jernih di HP.",
        "cta_label": "Pesan via WhatsApp",
        "cta_short": "Pesan WA",
        "secondary_label": "Lihat Kurasi Menu",
        "section_title": "Kurasi beans & seduhan hari ini",
        "section_sub": "Tanpa file PDF berat—varian, karakter rasa, dan harga langsung terbaca rapi.",
        "gallery_kicker": "RUANG & SANGRAI",
        "gallery_title": "Dari meja cupping ke cangkir pagi.",
        "gallery_notes": [
            ("SMALL-BATCH ROAST", "Disangrai tiap pekan dalam batch kecil agar aroma tetap jernih, baik diminum hitam maupun bersama susu."),
            ("MEJA SEDUH & WFC", "Cahaya alami pagi, meja kayu lapang, stopkontak di tiap sudut, dan Wi-Fi stabil tanpa musik bising."),
        ],
        "items": [
            {"tag": "HOUSE BLEND", "name": "Es Kopi Susu Gula Aren", "desc": "Double ristretto medium-dark roast, susu segar dingin, gula aren organik.", "price": "Rp 28.000"},
            {"tag": "MANUAL BREW", "name": "Single Origin V60", "desc": "Rotasi beans nusantara mingguan (Gayo, Flores, atau Jawa Barat) — floral & clean finish.", "price": "Rp 36.000"},
            {"tag": "NON-COFFEE", "name": "Ceremonial Uji Matcha", "desc": "Matcha grade seremonial dikocok manual dengan chasen, manis tipis seimbang.", "price": "Rp 38.000"},
            {"tag": "BAKERY", "name": "Butter Croissant Hangat", "desc": "Dipanggang tiap pagi, lapisan renyah mentega Prancis yang pas menemani filter coffee.", "price": "Rp 32.000"},
        ],
        "highlights": [
            ("01", "Roast profile transparan", "Setiap cangkir mencantumkan asal beans, proses pascapanen, dan catatan rasa."),
            ("02", "Suasana tenang buat kerja", "Ruang lapang dengan pencahayaan pagi dan stopkontak di setiap meja."),
            ("03", "Ambil langsung lewat WA", "Pre-order dari jalan sebelum tiba di bar, tinggal ambil tanpa menunggu."),
        ],
        "faqs": [
            ("Apakah tersedia pilihan susu oat / non-dairy?", "Ya, semua menu berbasis susu dapat diganti oat milk atau soy milk."),
            ("Bisa pesan biji kopi giling sesuai alat seduh di rumah?", "Bisa—sebutkan alat seduh (V60, espresso, tubruk, atau cold brew) saat pesan via WA."),
            ("Apakah nyaman untuk bekerja membawa laptop?", "Tersedia meja kerja dengan stopkontak dan koneksi Wi-Fi khusus pengunjung."),
        ],
        "hours": "Setiap hari · 07.30 – 21.30 WIB",
        "wa_prefill": "Halo {name}, saya lihat halaman preview dan mau tanya / pesan kopi ya.",
        "fictional_pool": ["Kopi Sore Roasters", "Ruang Seduh Lokal", "Kedai Hening Coffee", "Sapa Pagi Roastery"],
        "photo_captions": {
            "hero": "Slow bar pagi dengan manual pour-over & cahaya alami",
            "secondary": "Small-batch Arabica disangrai segar tiap pekan",
            "accent": "Es Kopi Susu Gula Aren & Butter Croissant hangat",
        },
    },
    "barber": {
        "match": ("barber", "pangkas", "cukur", "salon", "hair", "grooming"),
        "preferred_styles": ["figcraft_sharp_grid", "dark_moody_luxury", "modern_editorial"],
        "badge": "GROOMING & BARBERSHOP",
        "headline": "Potongan rapi yang tetap enak dilihat dua minggu setelahnya.",
        "sub": "Konsultasi singkat sebelum gunting dimulai—galeri gaya potongan jelas, daftar tarif bersih tanpa ribet, dan slot booking WhatsApp tanpa antre.",
        "cta_label": "Booking Slot via WA",
        "cta_short": "Booking WA",
        "secondary_label": "Lihat Layanan & Tarif",
        "section_title": "Daftar layanan & tarif transparan",
        "section_sub": "Cek durasi, rincian perawatan, dan tarif langsung dari HP sebelum berangkat.",
        "gallery_kicker": "GALERI GAYA & CRAFT",
        "gallery_title": "Presisi detail di setiap sisi potongan.",
        "gallery_notes": [
            ("SCISSOR-OVER-COMB & FADE", "Penyesuaian gradasi mengikuti bentuk kepala dan arah tumbuh rambut asli—bukan sekadar satu pola untuk semua."),
            ("STERILIZED TOOLS & HOT TOWEL", "Gunting baja Jepang, clipper matte presisi, dan handuk hangat disterilkan sebelum setiap kursi baru."),
        ],
        "items": [
            {"tag": "45 MIN · SIGNATURE", "name": "Precision Haircut + Wash", "desc": "Konsultasi bentuk kepala, potongan detail, keramas, handuk hangat & styling.", "price": "Rp 75.000"},
            {"tag": "25 MIN · GROOMING", "name": "Beard Trim & Hot Towel", "desc": "Rapikan garis jenggot dan kumis dengan handuk hangat & soothing balm.", "price": "Rp 45.000"},
            {"tag": "65 MIN · COMPLETE", "name": "Full Grooming Package", "desc": "Haircut, cuci rambut, pijat kepala ringan, beard trim, dan hair tonic.", "price": "Rp 110.000"},
            {"tag": "30 MIN · TREATMENT", "name": "Scalp Refresh & Tonic", "desc": "Pembersihan kulit kepala menyegarkan untuk aktivitas harian yang padat.", "price": "Rp 60.000"},
        ],
        "highlights": [
            ("01", "Pilih layanan & jam", "Cek daftar perawatan dan tentukan slot waktu yang paling pas buat jadwal lo."),
            ("02", "Konfirmasi lewat WA", "Satu klik WhatsApp untuk mengunci kursi dan memilih barber favorit."),
            ("03", "Datang langsung duduk", "Tiba sesuai jam booking tanpa antre panjang di ruang tunggu."),
        ],
        "faqs": [
            ("Apakah harus booking dulu atau bisa walk-in?", "Walk-in tetap dilayani sesuai ketersediaan kursi, tetapi booking via WA menjamin slot tanpa antre."),
            ("Berapa lama satu sesi haircut lengkap?", "Sekitar 40–45 menit termasuk konsultasi bentuk rambut, keramas, dan styling."),
            ("Bisa pilih barber tertentu?", "Bisa—sebutkan nama barber pilihan saat konfirmasi slot di WhatsApp."),
        ],
        "hours": "Selasa – Minggu · 10.00 – 21.00 WIB",
        "wa_prefill": "Halo {name}, saya mau cek slot booking potong rambut hari ini / besok.",
        "fictional_pool": ["Pangkas Rapi Studio", "Tatanan Grooming House", "Potong Tenang Barber", "Ruang Cukur Lokal"],
        "photo_captions": {
            "hero": "Ruang pangkas arsitektural dengan pencahayaan presisi",
            "secondary": "Teknik scissor-over-comb & temple fade detail",
            "accent": "Peralatan steril & handuk hangat standar tiap sesi",
        },
    },
    "aesthetic_clinic": {
        "match": ("estetika", "perawatan kulit", "derma", "skincare clinic", "aesthetic"),
        "preferred_styles": ["dark_moody_luxury", "modern_editorial", "clean_swiss_minimal"],
        "badge": "ESTETIKA & DERMATOLOGI",
        "headline": "Perawatan kulit terukur untuk hasil sehat yang tetap natural.",
        "sub": "Setiap sesi diawali analisis kondisi kulit bersama dokter—rincian perawatan, durasi tindakan, dan reservasi jadwal privat tersaji tenang di layar HP.",
        "cta_label": "Jadwalkan Konsultasi",
        "cta_short": "Reservasi WA",
        "secondary_label": "Lihat Kurasi Perawatan",
        "section_title": "Kurasi perawatan kulit & estimasi",
        "section_sub": "Protokol dermatologi yang jelas tanpa jargon berlebihan, disusun ringkas untuk kenyamanan calon pasien.",
        "gallery_kicker": "RUANG & PROTOKOL",
        "gallery_title": "Ketenangan ruang privat dengan standar medis ketat.",
        "gallery_notes": [
            ("ANALISIS KULIT PERSONAL", "Dokter memetakan kondisi skin barrier dan pigmentasi terlebih dahulu sebelum merekomendasikan tindakan."),
            ("RUANG TINDAKAN PRIVAT", "Penjadwalan berbasis reservasi menjaga suasana klinik tetap tenang, steril, dan tepat waktu."),
        ],
        "items": [
            {"tag": "45 MIN · DIAGNOSTIK", "name": "Konsultasi Dokter & Analisis Kulit", "desc": "Pemetaan kondisi pori, hidrasi, dan pigmentasi untuk rencana perawatan personal.", "price": "Rp 250.000"},
            {"tag": "60 MIN · SIGNATURE", "name": "Medical Hydra-Barrier Infusion", "desc": "Pembersihan lembut dan infusi serum penenang untuk mengembalikan kilau sehat kulit.", "price": "Rp 780.000"},
            {"tag": "40 MIN · LASER", "name": "Laser Toning & Pigment Clarity", "desc": "Perataan warna kulit dan noda bekas jerawat dengan minim waktu pemulihan.", "price": "Rp 1.150.000"},
            {"tag": "50 MIN · REGENERATIF", "name": "Collagen Biostimulator Plan", "desc": "Program bertahap untuk menjaga kekenyalan kulit dengan hasil halus dan proporsional.", "price": "Konsultasi"},
        ],
        "highlights": [
            ("01", "Evaluasi dokter di awal", "Setiap rekomendasi tindakan disesuaikan dengan kondisi aktual kulit pasien."),
            ("02", "Estimasi transparan", "Durasi tindakan, perawatan pasca-sesi, dan rentang biaya dijelaskan sebelum prosedur."),
            ("03", "Reservasi tanpa antre", "Konfirmasi jadwal privat melalui WhatsApp langsung dengan admin klinik."),
        ],
        "faqs": [
            ("Apakah wajib konsultasi dokter sebelum tindakan laser?", "Ya, pemeriksaan awal memastikan parameter perawatan aman sesuai kondisi kulit Anda."),
            ("Apakah tersedia perawatan tanpa downtime?", "Tersedia beberapa protokol hidrasi dan laser ringan yang aman untuk aktivitas hari yang sama."),
            ("Bagaimana cara menjadwalkan kunjungan?", "Pilih jadwal yang diinginkan melalui tombol reservasi WhatsApp untuk penguncian slot."),
        ],
        "hours": "Selasa – Minggu · 10.00 – 20.00 WIB",
        "wa_prefill": "Halo {name}, saya ingin menanyakan jadwal konsultasi dokter dan ketersediaan slot perawatan.",
        "fictional_pool": ["Klinik Rona Derma", "Loka Estetika Clinic", "Seri Skin Sanctuary", "Nala Dermatology Studio"],
        "photo_captions": {
            "hero": "Lounge konsultasi tenang dengan pencahayaan arsitektural lembut",
            "secondary": "Ruang tindakan privat berstandar higienis",
            "accent": "Formulasi perawatan kulit kurasi klinis",
        },
    },
    "pilates": {
        "match": ("pilates", "movement", "reformer", "barre", "yoga"),
        "preferred_styles": ["modern_editorial", "warm_organic_hospitality", "coastal_terracotta"],
        "badge": "REFORMER PILATES & MOVEMENT",
        "headline": "Gerak yang tenang, napas teratur, dan postur yang kembali selaras.",
        "sub": "Kelas grup kecil maksimal 6 reformer dan sesi privat terpandu—jadwal harian, level kelas, dan booking sesi langsung rapi di layar HP.",
        "cta_label": "Booking Sesi via WA",
        "cta_short": "Booking WA",
        "secondary_label": "Lihat Kelas & Paket",
        "section_title": "Pilihan kelas & paket sesi",
        "section_sub": "Cocok untuk pemula maupun praktisi rutin—semua durasi dan tarif tampil jernih tanpa perlu bolak-balik chat.",
        "gallery_kicker": "RUANG & RITME",
        "gallery_title": "Studio penuh cahaya alami untuk fokus tanpa terburu-buru.",
        "gallery_notes": [
            ("GRUP KECIL MAKSIMAL 6 ORANG", "Instruktur memantau alignment tulang belakang, napas, dan transisi gerak setiap peserta secara personal."),
            ("REFORMER KAYU & ALAT TERAWAT", "Peralatan dibersihkan tiap pergantian sesi dalam ruang tenang dengan sirkulasi cahaya pagi."),
        ],
        "items": [
            {"tag": "55 MIN · PEMULA", "name": "Reformer Foundations", "desc": "Pengenalan kontrol napas, aktivasi core, dan keseimbangan tubuh di atas reformer.", "price": "Rp 240.000"},
            {"tag": "55 MIN · ALL LEVEL", "name": "Align & Core Flow", "desc": "Rangkaian gerak mengalir untuk kekuatan inti, mobilitas pinggul, dan stabilitas bahu.", "price": "Rp 260.000"},
            {"tag": "60 MIN · 1-ON-1", "name": "Private Postural Assessment", "desc": "Sesi privat penuh yang disesuaikan dengan kebutuhan postur, pemulihan, atau target gerak.", "price": "Rp 550.000"},
            {"tag": "5 SESI · PAKET", "name": "Starter 5-Class Pack", "desc": "Paket fleksibel berlaku 60 hari untuk membangun konsistensi latihan mingguan.", "price": "Rp 1.100.000"},
        ],
        "highlights": [
            ("01", "Ramah untuk pemula", "Kelas Foundations membimbing dari dasar tanpa tekanan tempo cepat."),
            ("02", "Kapasitas ruang terbatas", "Maksimal 6 reformer per sesi agar koreksi postur tetap akurat."),
            ("03", "Booking & reschedule mudah", "Kunci slot pagi atau sore cukup lewat satu pesan WhatsApp."),
        ],
        "faqs": [
            ("Apakah pemula yang belum pernah Pilates bisa langsung ikut?", "Bisa—kami sarankan mulai dari kelas Reformer Foundations atau 1x sesi Private Assessment."),
            ("Apa yang perlu dibawa saat latihan?", "Cukup kenakan pakaian olahraga nyaman dan kaus kaki anti-slip (grip socks)."),
            ("Berapa jam batas maksimal reschedule?", "Perubahan jadwal kelas dapat dilakukan hingga 12 jam sebelum sesi dimulai."),
        ],
        "hours": "Setiap hari · 07.00 – 20.00 WIB",
        "wa_prefill": "Halo {name}, saya ingin cek jadwal kelas Pilates dan ketersediaan slot minggu ini.",
        "fictional_pool": ["Sela Movement Pilates", "Teras Gerak Studio", "Napas Reformer House", "Laras Pilates Space"],
        "photo_captions": {
            "hero": "Ruang reformer bermandikan cahaya pagi dan material kayu alami",
            "secondary": "Tata ruang tenang berkapasitas terbatas untuk fokus penuh",
            "accent": "Detail peralatan kayu & ruang jeda seusai sesi",
        },
    },
    "bakery": {
        "match": ("sourdough", "bakery", "bakehouse", "pastry", "croissant", "viennoiserie", "roti"),
        "preferred_styles": ["vibrant_modern_cafe", "coastal_terracotta", "warm_organic_hospitality"],
        "badge": "ARTISAN SOURDOUGH & PASTRY",
        "headline": "Fermentasi pelan 24 jam, keluar oven hangat setiap pagi.",
        "sub": "Sourdough kulit renyah dan pastry laminasi mentega Prancis dipanggang dalam batch harian—cek menu, jadwal oven, dan pre-order loaf langsung lewat HP.",
        "cta_label": "Pre-Order via WA",
        "cta_short": "Order WA",
        "secondary_label": "Lihat Menu Panggang",
        "section_title": "Daftar panggang harian & harga",
        "section_sub": "Tanpa PDF berat—pilih varian sourdough dan viennoiserie favorit sebelum batch pagi habis.",
        "gallery_kicker": "DAPUR FERMENTASI",
        "gallery_title": "Ragi alami, mentega pilihan, dan ritme oven pagi.",
        "gallery_notes": [
            ("NATURAL LEVAIN 24 JAM", "Adonan difermentasi dingin tanpa ragi instan agar aroma gandum keluar utuh dan lebih ramah di perut."),
            ("BATCH PAGI & SIANG", "Croissant dan pastry keluar oven pukul 07.30, disusul country sourdough hangat pukul 09.30."),
        ],
        "items": [
            {"tag": "750G · SIGNATURE", "name": "Country Sourdough Loaf", "desc": "Kulit karamel renyah dengan remah lembap terbuka dari starter alami berumur tahunan.", "price": "Rp 68.000"},
            {"tag": "VIENNOISERIE", "name": "Caramelized Kouign-Amann", "desc": "Lapisan adonan mentega berbalut gula karamel garing di tepi dan lembut di tengah.", "price": "Rp 36.000"},
            {"tag": "MORNING BAKE", "name": "Almond Pain au Chocolat", "desc": "Pastry laminasi renyah isi cokelat gelap 70% dengan krim almon panggang.", "price": "Rp 42.000"},
            {"tag": "SPICED BUN", "name": "Cardamom Cinnamon Knot", "desc": "Roti brioche empuk dipilin manual bersama kapulaga tumbuk segar dan kayu manis.", "price": "Rp 34.000"},
        ],
        "highlights": [
            ("01", "Jadwal oven transparan", "Tahu persis jam keluar oven supaya datang pas roti masih hangat."),
            ("02", "Pre-order aman via WA", "Kunci loaf utuh atau box pastry sebelum kehabisan stok harian."),
            ("03", "Bisa potong sesuai selera", "Sebutkan potongan tipis atau tebal saat konfirmasi pesanan."),
        ],
        "faqs": [
            ("Kapan waktu terbaik untuk pre-order sourdough utuh?", "Pre-order H-1 sampai pukul 18.00 WIB menjamin loaf langsung disisihkan dari batch pagi."),
            ("Bagaimana cara menyimpan sourdough di rumah?", "Simpan di kantong kertas pada suhu ruang hingga 2 hari, atau iris lalu bekukan di freezer hingga 3 minggu."),
            ("Apakah tersedia paket box untuk hampers atau acara kantor?", "Tersedia box isi 6 dan 12 pastry dengan pemesanan minimal H-2 via WhatsApp."),
        ],
        "hours": "Rabu – Senin · 07.30 – 18.00 WIB",
        "wa_prefill": "Halo {name}, saya mau cek stok batch hari ini / pre-order sourdough & pastry.",
        "fictional_pool": ["Ragi Pagi Bakehouse", "Tepung & Waktu Bakery", "Lapis Hangat Viennoiserie", "Remah Pagi Sourdough"],
        "photo_captions": {
            "hero": "Etalase bakehouse pagi dengan sourdough dan pastry hangat",
            "secondary": "Potongan country sourdough beremah terbuka & kulit karamel",
            "accent": "Croissant almon dan cardamom bun di atas keramik hangat",
        },
    },
    "custom_garage": {
        "match": ("bengkel", "motor custom", "custom garage", "garage", "cafe racer", "scrambler", "chopper", "kustom"),
        "preferred_styles": ["neo_brutalist_street", "figcraft_sharp_grid", "dark_moody_luxury"],
        "badge": "CUSTOM MOTORCYCLE GARAGE",
        "headline": "Bangun motor berkarakter—rapi di rangka, jujur di mesin.",
        "sub": "Dari konsep sketsa, fabrikasi tangki & subframe, sampai kelistrikan rapi untuk dipakai harian—cek layanan, estimasi, dan jadwal slot bengkel langsung di HP.",
        "cta_label": "Konsultasi Build via WA",
        "cta_short": "Chat Garage",
        "secondary_label": "Lihat Layanan Workshop",
        "section_title": "Layanan workshop & estimasi awal",
        "section_sub": "Semua tahap pengerjaan dijelaskan terbuka dari awal tanpa biaya siluman di tengah jalan.",
        "gallery_kicker": "WORKSHOP & FABRIKASI",
        "gallery_title": "Las presisi, proporsi pas, dan siap diajak jalan jauh.",
        "gallery_notes": [
            ("FABRIKASI HAND-BUILT", "Tangki plat galvanis, subframe, dan dudukan jok dibentuk langsung mengikuti postur pengendara."),
            ("KELISTRIKAN & MESIN HARIAN", "Bukan cuma bagus difoto—wiring harness dirapikan ulang agar motor tetap andal dipakai harian."),
        ],
        "items": [
            {"tag": "CUSTOM BUILD", "name": "Full Build Scrambler / Cafe Racer", "desc": "Rombak menyeluruh rangka belakang, bodi plat, kaki-kaki, knalpot, dan finishing cat.", "price": "Mulai Rp 18 jt"},
            {"tag": "FABRIKASI", "name": "Tangki, Subframe & Jok Custom", "desc": "Pembuatan tangki hand-shaped, penyesuaian rangka, dan jok kulit tahan cuaca.", "price": "Mulai Rp 4,5 jt"},
            {"tag": "MECHANICAL", "name": "Tune-Up & Rewiring Kelistrikan", "desc": "Servis karburator/injeksi, perapian kabel bodi tersembunyi, dan cek pengapian.", "price": "Mulai Rp 850 rb"},
            {"tag": "FINISHING", "name": "Custom Paint & Pinstripe", "desc": "Pengecatan oven matte/gloss, garis pinstripe manual, dan proteksi clear coat.", "price": "Mulai Rp 2,8 jt"},
        ],
        "highlights": [
            ("01", "Konsultasi bahan & budget", "Diskusi motor basis, gaya riding, dan estimasi biaya sebelum bongkar."),
            ("02", "Update progres mingguan", "Foto perkembangan fabrikasi dan mesin dikirim rutin lewat WhatsApp."),
            ("03", "Test ride sebelum serah terima", "Setiap unit dicek ergonomi, rem, dan kelistrikan di jalan sebelum pulang."),
        ],
        "faqs": [
            ("Motor basis apa saja yang bisa digarap?", "Kami biasa menggarap basis 150cc–650cc seperti Scorpio, W175, Tiger, Binter, hingga Royal Enfield."),
            ("Berapa lama estimasi pengerjaan full custom build?", "Rata-rata 6 sampai 10 minggu tergantung tingkat kerumitan fabrikasi dan ketersediaan part."),
            ("Bisa datang langsung ke bengkel untuk ngobrol konsep?", "Bisa banget—kirim jadwal kedatangan lewat WA biar mekanik utama sedang tidak sibuk di lift."),
        ],
        "hours": "Selasa – Minggu · 10.00 – 19.00 WIB",
        "wa_prefill": "Halo {name}, saya mau konsultasi konsep custom motor / cek slot bengkel.",
        "fictional_pool": ["Besi Tua Custom Garage", "Rangka Baja Workshop", "Pijar Kustom Motor", "Bengkel Garis Keras"],
        "photo_captions": {
            "hero": "Unit custom scrambler hasil bangun di ruang workshop beton",
            "secondary": "Detail tangki besi hand-welded dan mesin berpendingin udara",
            "accent": "Meja kerja mekanik dengan perkakas baja & part kustom",
        },
    },
    "clinic": {
        "match": ("klinik", "clinic", "gigi", "dental", "dokter", "skin", "derma", "estetika", "fisioterapi", "therapy", "spa", "wellness"),
        "preferred_styles": ["clean_swiss_minimal", "warm_organic_hospitality"],
        "badge": "KLINIK & PERAWATAN",
        "headline": "Perawatan tenang, penjelasan jelas, tanpa bikin tegang.",
        "sub": "Setiap prosedur dijelaskan sejak awal beserta estimasi biaya—supaya pasien datang dengan jadwal pasti dan rasa nyaman.",
        "cta_label": "Jadwalkan Konsultasi",
        "cta_short": "Reservasi WA",
        "secondary_label": "Lihat Layanan",
        "section_title": "Layanan utama klinik",
        "section_sub": "Rincian tindakan dan jadwal praktik disusun ringkas agar mudah dipahami di HP.",
        "gallery_kicker": "STANDAR PERAWATAN",
        "gallery_title": "Ruang tenang dengan komunikasi transparan.",
        "gallery_notes": [
            ("KONSULTASI JELAS DI AWAL", "Dokter menjelaskan opsi tindakan serta estimasi biaya sebelum prosedur dimulai."),
            ("RESERVASI TANPA MENUNGGU LAMA", "Jadwal praktik teratur via WhatsApp menjaga kenyamanan ruang tunggu."),
        ],
        "items": [
            {"tag": "KONSULTASI", "name": "Pemeriksaan & Rencana Perawatan", "desc": "Evaluasi menyeluruh dengan penjelasan bahasa sehari-hari yang mudah dipahami.", "price": "Mulai Rp 150.000"},
            {"tag": "PREVENTIF", "name": "Perawatan Rutin & Pembersihan", "desc": "Prosedur lembut dan higienis untuk menjaga kesehatan jangka panjang.", "price": "Mulai Rp 350.000"},
            {"tag": "ESTETIKA", "name": "Perawatan Estetika Natural", "desc": "Hasil halus dan proporsional sesuai kebutuhan pribadi pasien.", "price": "Konsultasi"},
            {"tag": "FOLLOW-UP", "name": "Kontrol Berkala", "desc": "Pemantauan progres pasca tindakan dengan pengingat jadwal via WhatsApp.", "price": "Sesuai paket"},
        ],
        "highlights": [
            ("01", "Jadwal praktik teratur", "Reservasi via WhatsApp mengurangi waktu tunggu di ruang depan."),
            ("02", "Komunikasi transparan", "Estimasi tindakan disampaikan jelas sebelum prosedur dimulai."),
            ("03", "Ruang bersih & menenangkan", "Suasana hangat yang jauh dari kesan dingin ruang tunggu lama."),
        ],
        "faqs": [
            ("Apakah perlu reservasi sebelum datang?", "Disarankan reservasi via WA agar jadwal dokter langsung terkunci."),
            ("Apakah estimasi biaya dijelaskan sebelum tindakan?", "Ya, dokter selalu menjelaskan opsi tindakan dan estimasinya di awal."),
            ("Tersedia jadwal sore atau akhir pekan?", "Tersedia sesi praktik sore hingga pukul 20.00 dan hari Sabtu."),
        ],
        "hours": "Senin – Sabtu · 09.00 – 20.00 WIB",
        "wa_prefill": "Halo {name}, saya ingin tanya jadwal konsultasi dan reservasi pasien.",
        "fictional_pool": ["Klinik Teduh Care", "Ruang Sehat Studio", "Klinik Gigi Tenang", "Sapa Medika Lokal"],
        "photo_captions": {
            "hero": "Ruang konsultasi hangat dan tenang",
            "secondary": "Standar kebersihan & kenyamanan pasien",
            "accent": "Detail peralatan perawatan higienis",
        },
    },
    "agro_hospitality": {
        "match": ("farm", "kebun", "wisata", "villa", "resort", "hotel", "homestay", "glamping", "florist", "tanaman", "taman", "garden"),
        "preferred_styles": ["warm_organic_hospitality", "coastal_terracotta"],
        "badge": "DESTINASI & HOSPITALITY",
        "headline": "Ruang bernapas yang hangat—dari kebun sampai meja makan.",
        "sub": "Jadwal kunjungan, paket aktivitas, dan reservasi langsung dalam satu halaman bersih yang nyaman dibuka di HP.",
        "cta_label": "Reservasi via WhatsApp",
        "cta_short": "Reservasi WA",
        "secondary_label": "Lihat Paket & Tiket",
        "section_title": "Paket kunjungan & aktivitas",
        "section_sub": "Durasi, fasilitas, dan tarif tampil jernih tanpa perlu bolak-balik chat.",
        "gallery_kicker": "SUASANA DESTINASI",
        "gallery_title": "Pengalaman ruang terbuka yang tenang.",
        "gallery_notes": [
            ("RAMAH KELUARGA", "Jalur teduh, area santai lapang, dan fasilitas bersih di seluruh kawasan."),
            ("RESCHEDULE FLEKSIBEL", "Perubahan jadwal kunjungan mudah dilakukan hingga H-1 sebelum kedatangan."),
        ],
        "items": [
            {"tag": "TERLARIS", "name": "Akses Kunjungan Harian", "desc": "Nikmati seluruh area terbuka, taman, dan ruang santai keluarga.", "price": "Rp 50.000"},
            {"tag": "TERPANDU", "name": "Tur & Sesi Pengalaman", "desc": "Aktivitas berpemandu berdurasi 90 menit untuk keluarga maupun grup kecil.", "price": "Rp 120.000"},
            {"tag": "WORKSHOP", "name": "Kelas & Makan Siang Lokal", "desc": "Pengalaman memasak / berkarya langsung dengan bahan segar pilihan.", "price": "Rp 250.000"},
            {"tag": "PRIVATE", "name": "Paket Kunjungan Grup", "desc": "Jadwal khusus untuk komunitas, sekolah, atau acara keluarga.", "price": "Custom"},
        ],
        "highlights": [
            ("01", "Konfirmasi slot cepat", "Pilih hari kunjungan dan amankan kuota langsung lewat WhatsApp."),
            ("02", "Ramah keluarga & anak", "Jalur aman, area teduh, dan fasilitas bersih di seluruh lokasi."),
            ("03", "Reschedule fleksibel", "Perubahan jadwal kunjungan mudah hingga H-1 sebelum kedatangan."),
        ],
        "faqs": [
            ("Apakah anak-anak mendapat tarif khusus?", "Ya, tersedia tarif khusus anak-anak dan bebas biaya untuk balita."),
            ("Bisa reschedule kalau cuaca hujan?", "Bisa menjadwalkan ulang secara gratis hingga 24 jam sebelumnya."),
            ("Apakah tersedia area parkir luas?", "Tersedia area parkir mobil dan motor langsung di dekat pintu masuk."),
        ],
        "hours": "Setiap hari · 08.00 – 19.00",
        "wa_prefill": "Halo {name}, saya mau tanya ketersediaan jadwal & reservasi kunjungan.",
        "fictional_pool": ["Kebun Teduh Sanctuary", "Loka Hijau Retreat", "Sari Bumi Garden", "Teras Alam Villa"],
        "photo_captions": {
            "hero": "Area santai terbuka penuh cahaya alami",
            "secondary": "Bahan segar dan sajian hangat dari kebun",
            "accent": "Meja santai sore untuk keluarga",
        },
    },
    "food": {
        "match": ("resto", "restaurant", "bakmi", "bakery", "roti", "cake", "pastry", "bistro", "kitchen", "dapur", "warung", "makan", "sushi", "ramen", "kuliner"),
        "preferred_styles": ["coastal_terracotta", "vibrant_modern_cafe", "modern_editorial"],
        "badge": "DAPUR & KULINER",
        "headline": "Rasa rumahan yang jujur, disajikan hangat setiap hari.",
        "sub": "Bahan segar pilihan, resep konsisten, dan jalur reservasi meja atau pesan bawa pulang yang praktis lewat HP.",
        "cta_label": "Pesan / Reservasi WA",
        "cta_short": "Pesan WA",
        "secondary_label": "Lihat Menu Favorit",
        "section_title": "Menu favorit dapur",
        "section_sub": "Langsung pilih hidangan tanpa perlu download PDF besar atau zoom gambar buram.",
        "gallery_kicker": "DAPUR & SAJIAN",
        "gallery_title": "Dimasak segar sesuai pesanan setiap hari.",
        "gallery_notes": [
            ("BAHAN SEGAR HARIAN", "Racikan bumbu dapur sendiri dengan porsi konsisten untuk makan di tempat maupun takeaway."),
            ("RESERVASI MEJA CEPAT", "Amankan meja untuk makan malam keluarga atau jam makan siang lewat satu klik WA."),
        ],
        "items": [
            {"tag": "BEST SELLER", "name": "Menu Spesial Dapur", "desc": "Dimasak fresh saat dipesan dengan bumbu racikan sendiri.", "price": "Rp 48.000"},
            {"tag": "COMFORT", "name": "Paket Lengkap Harian", "desc": "Porsi pas untuk makan siang atau makan malam bareng keluarga.", "price": "Rp 62.000"},
            {"tag": "SHARING", "name": "Platter Hangat Untuk Berdua", "desc": "Pilihan camilan dan sajian pendamping paling sering dipesan ulang.", "price": "Rp 85.000"},
            {"tag": "FRESH DRINK", "name": "Minuman Racikan Segar", "desc": "Dibuat dari bahan alami tanpa sirup berlebihan.", "price": "Rp 24.000"},
        ],
        "highlights": [
            ("01", "Selalu dimasak segar", "Porsi konsisten untuk makan di tempat maupun bungkus pulang."),
            ("02", "Reservasi meja cepat", "Cukup satu klik WhatsApp untuk amankan meja jam ramai."),
            ("03", "Cocok buat pesanan grup", "Tersedia paket khusus untuk acara kantor atau kumpul keluarga."),
        ],
        "faqs": [
            ("Apakah bisa reservasi meja untuk rombongan?", "Bisa—kirim jumlah tamu dan jam kedatangan lewat WhatsApp."),
            ("Apakah semua menu tersedia untuk takeaway?", "Ya, semua menu utama dikemas rapi untuk dibawa pulang."),
            ("Apakah tersedia opsi vegetarian / non-pedas?", "Tersedia, cukup infokan preferensi saat memesan."),
        ],
        "hours": "Setiap hari · 10.00 – 22.00 WIB",
        "wa_prefill": "Halo {name}, saya mau reservasi meja / pesan menu hari ini.",
        "fictional_pool": ["Dapur Hangat Bistro", "Meja Sore Kitchen", "Roti & Rasa Bakery", "Sajian Lokal House"],
        "photo_captions": {
            "hero": "Sajian hangat langsung dari dapur harian",
            "secondary": "Suasana meja makan yang nyaman",
            "accent": "Bahan pilihan segar setiap pagi",
        },
    },
    "general": {
        "match": (),
        "preferred_styles": ["modern_editorial", "figcraft_sharp_grid", "clean_swiss_minimal"],
        "badge": "BISNIS LOKAL TERKURASI",
        "headline": "Layanan rapi, informasi jelas, langsung terhubung tanpa muter-muter.",
        "sub": "Layanan utama, jam operasional, alamat, dan kontak WhatsApp tersusun jernih dalam satu halaman editorial.",
        "cta_label": "Hubungi via WhatsApp",
        "cta_short": "Chat WA",
        "secondary_label": "Lihat Layanan",
        "section_title": "Layanan & informasi utama",
        "section_sub": "Dirancang ringan dan nyaman dibaca di layar smartphone.",
        "gallery_kicker": "CARA KERJA",
        "gallery_title": "Detail transparan dari awal sampai selesai.",
        "gallery_notes": [
            ("INFORMASI TANPA HAMBATAN", "Semua rincian layanan dan estimasi tampil langsung tanpa perlu mencari di banyak tautan."),
            ("KONTAK LANGSUNG", "Terhubung ke tim melalui WhatsApp dengan alur konsultasi yang ringkas."),
        ],
        "items": [
            {"tag": "LAYANAN 01", "name": "Konsultasi & Paket Utama", "desc": "Solusi inti yang paling sering dipilih pelanggan dengan alur transparan.", "price": "Tanya estimasi"},
            {"tag": "LAYANAN 02", "name": "Layanan Kustom Sesuai Kebutuhan", "desc": "Disesuaikan dengan jadwal dan spesifikasi yang kamu butuhkan.", "price": "Mulai terjangkau"},
            {"tag": "LAYANAN 03", "name": "Paket Berkala / Langganan", "desc": "Pilihan hemat dan praktis untuk kebutuhan rutin bulanan.", "price": "Info via WA"},
            {"tag": "LAYANAN 04", "name": "Dukungan Cepat", "desc": "Tim responsif siap bantu jawab pertanyaan sebelum kamu memutuskan.", "price": "Gratis tanya"},
        ],
        "highlights": [
            ("01", "Respon cepat & ramah", "Langsung terhubung ke tim yang menangani kebutuhan lo."),
            ("02", "Detail rapi & transparan", "Harga dan alur pengerjaan disampaikan jelas sejak awal."),
            ("03", "Ringan di layar HP", "Teks dan navigasi terasa lega di layar smartphone."),
        ],
        "faqs": [
            ("Bagaimana cara mulai konsultasi?", "Klik tombol WhatsApp di halaman ini untuk langsung ngobrol dengan tim."),
            ("Apakah estimasi biaya diberikan di awal?", "Ya, setiap paket atau pengerjaan selalu diawali rincian jelas."),
            ("Jam berapa layanan aktif merespon?", "Kami aktif setiap Senin sampai Sabtu pukul 09.00–20.00 WIB."),
        ],
        "hours": "Senin – Sabtu · 09.00 – 20.00 WIB",
        "wa_prefill": "Halo {name}, saya lihat halaman profilnya dan mau tanya soal layanan yang tersedia.",
        "fictional_pool": ["Ruang Karya Lokal", "Studio Tenang Jaya", "Karya Harian Studio", "Rumah Layanan Rapi"],
        "photo_captions": {
            "hero": "Ruang layanan profesional & terkurasi",
            "secondary": "Detail pengerjaan rapi dan terukur",
            "accent": "Standar kualitas di setiap sesi",
        },
    },
}


def pick_preset(category: str, business_name: str = "") -> tuple[str, dict[str, Any]]:
    haystack = f"{category} {business_name}".lower()
    for key, preset in CATEGORY_PRESETS.items():
        if key == "general":
            continue
        if any(token in haystack for token in preset["match"]):
            return key, preset
    return "general", CATEGORY_PRESETS["general"]


def select_style_for_lead(lead: dict[str, Any], force_style: str | None = None) -> tuple[str, dict[str, Any]]:
    requested = (force_style or lead.get("design_style") or "").strip()
    if requested in STYLE_THEMES:
        return requested, STYLE_THEMES[requested]

    bp = resolve_niche_blueprint(lead.get("category", ""), lead.get("business_name", ""), lead.get("city", ""))
    rec_style = bp.get("website_visual_theme")
    if rec_style in STYLE_THEMES:
        return rec_style, STYLE_THEMES[rec_style]

    _, preset = pick_preset(lead.get("category", ""), lead.get("business_name", ""))
    pool = preset.get("preferred_styles") or list(STYLE_THEMES.keys())
    seed = f"{lead.get('slug', '')}:{lead.get('business_name', '')}".encode("utf-8")
    digest = int(hashlib.sha256(seed).hexdigest(), 16)
    chosen_key = pool[digest % len(pool)]
    return chosen_key, STYLE_THEMES[chosen_key]


def generate_fictional_name(lead: dict[str, Any]) -> str:
    if lead.get("anonymized_name"):
        return str(lead["anonymized_name"]).strip()
    _, preset = pick_preset(lead.get("category", ""), lead.get("business_name", ""))
    pool = preset["fictional_pool"]
    digest = int(hashlib.sha256(lead["slug"].encode("utf-8")).hexdigest(), 16)
    return pool[digest % len(pool)]


def _esc(val: Any) -> str:
    return html.escape(str(val or ""), quote=True)


def _sync_media_for_demo(demo_dir: Path, photo_set: dict[str, str]) -> dict[str, str]:
    """Copy curated high-res niche photos into `site/demos/<slug>/media/` so pages are 100% self-contained."""
    media_dir = demo_dir / "media"
    media_dir.mkdir(parents=True, exist_ok=True)
    rel_paths: dict[str, str] = {}
    for slot, rel_src in photo_set.items():
        src = settings.BASE_DIR / rel_src
        if src.exists():
            dst = media_dir / f"{slot}{src.suffix}"
            if not dst.exists() or dst.stat().st_size != src.stat().st_size:
                shutil.copy2(src, dst)
            rel_paths[slot] = f"./media/{dst.name}"
        else:
            rel_paths[slot] = ""
    return rel_paths


def _common_style_css(theme: dict[str, Any], concept_only: bool = False, production: bool = False) -> str:
    headline_transform = (
        "text-transform: uppercase; letter-spacing: -0.015em; line-height: 0.96;"
        if theme["uppercase_display"]
        else "letter-spacing: -0.025em; line-height: 1.04;"
    )
    if production:
        body_pad = "padding-bottom: 0;"
    elif concept_only:
        body_pad = "padding-bottom: 36px;"
    else:
        body_pad = "padding-bottom: 84px;"
    is_sharp = theme["radius"] == "0px"

    return f"""
    :root {{
      --bg: {theme['bg']};
      --surface: {theme['surface']};
      --surface-alt: {theme['surface_alt']};
      --ink: {theme['ink']};
      --muted: {theme['muted']};
      --accent: {theme['accent']};
      --accent-2: {theme['accent_2']};
      --accent-ink: {theme['accent_ink']};
      --badge-bg: {theme['badge_bg']};
      --badge-ink: {theme['badge_ink']};
      --border: {theme['border']};
      --footer-bg: {theme['footer_bg']};
      --footer-ink: {theme['footer_ink']};
      --radius: {theme['radius']};
      --btn-radius: {theme['btn_radius']};
      --font-display: {theme['font_display']};
      --font-body: {theme['font_body']};
      --font-mono: {theme['font_mono']};
    }}

    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    html {{ scroll-behavior: smooth; overflow-x: hidden; }}
    body {{
      background: var(--bg);
      color: var(--ink);
      font-family: var(--font-body);
      line-height: 1.6;
      -webkit-font-smoothing: antialiased;
      overflow-x: hidden;
      max-width: 100vw;
      {body_pad}
    }}
    img {{ max-width: 100%; display: block; }}
    .container {{ width: 100%; max-width: 1180px; margin: 0 auto; padding: 0 20px; }}
    @media (min-width: 820px) {{ .container {{ padding: 0 36px; }} }}

    .display {{
      font-family: var(--font-display);
      font-weight: 700;
      {headline_transform}
    }}
    .mono-tag {{
      font-family: var(--font-mono);
      font-size: 11px;
      font-weight: 500;
      letter-spacing: 0.1em;
      text-transform: uppercase;
      color: var(--accent);
    }}

    /* === RESPONSIVE HEADER — NEVER TRUNCATES LONG BRAND NAMES AT 390PX === */
    header {{
      position: sticky;
      top: 0;
      z-index: 30;
      background: color-mix(in srgb, var(--bg) 94%, transparent);
      backdrop-filter: blur(8px);
      border-bottom: 1px solid var(--border);
    }}
    .nav-inner {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      min-height: 64px;
      padding: 12px 0;
      gap: 12px;
    }}
    .brand-mark {{
      display: inline-flex;
      align-items: center;
      gap: 8px;
      font-family: var(--font-display);
      font-size: clamp(17px, 4.4vw, 25px);
      font-weight: 700;
      line-height: 1.12;
      color: var(--ink);
      text-decoration: none;
      white-space: normal;
      overflow: visible;
      text-overflow: clip;
      flex: 1 1 auto;
      min-width: 0;
      {'text-transform: uppercase; letter-spacing: 0.02em;' if theme['uppercase_display'] else 'letter-spacing: -0.02em;'}
    }}
    .nav-links {{
      display: none;
      gap: 28px;
      font-size: 14px;
      color: var(--muted);
      flex-shrink: 0;
    }}
    .nav-links a {{ color: inherit; text-decoration: none; }}
    .nav-links a:hover {{ color: var(--ink); }}
    @media (min-width: 860px) {{
      .nav-links {{ display: flex; }}
      .brand-mark {{ flex: 0 1 auto; }}
    }}

    .nav-cta {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      background: var(--accent);
      color: var(--accent-ink);
      text-decoration: none;
      font-size: 12px;
      font-weight: 600;
      padding: 9px 14px;
      border-radius: var(--btn-radius);
      white-space: nowrap;
      flex-shrink: 0;
      letter-spacing: {'0.06em; text-transform: uppercase;' if is_sharp else '0.01em;'}
    }}
    .nav-cta .cta-full {{ display: none; }}
    .nav-cta .cta-short {{ display: inline; }}
    @media (min-width: 640px) {{
      .nav-cta {{ font-size: 13px; padding: 10px 18px; }}
      .nav-cta .cta-full {{ display: inline; }}
      .nav-cta .cta-short {{ display: none; }}
    }}

    /* === EDITORIAL HERO (PHOTO-LED, ZERO BOXED SLOP CARDS) === */
    .hero {{
      padding: 32px 0 42px;
      border-bottom: 1px solid var(--border);
    }}
    .hero-grid {{
      display: grid;
      grid-template-columns: 1fr;
      gap: 28px;
      align-items: end;
    }}
    @media (min-width: 860px) {{
      .hero {{ padding: 52px 0 60px; }}
      .hero-grid {{ grid-template-columns: 1.02fr 1.08fr; gap: 48px; align-items: center; }}
    }}
    .hero-eyebrow {{
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 10px;
      margin-bottom: 16px;
      font-family: var(--font-mono);
      font-size: 11px;
      letter-spacing: 0.1em;
      text-transform: uppercase;
      color: var(--accent);
    }}
    .eyebrow-sep {{ opacity: 0.4; }}
    .hero h1 {{
      font-size: clamp(36px, 7.6vw, 68px);
      margin-bottom: 18px;
    }}
    .hero-sub {{
      font-size: 16px;
      color: var(--muted);
      max-width: 520px;
      margin-bottom: 24px;
    }}
    .hero-actions {{
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
      margin-bottom: 28px;
    }}
    .btn-primary {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      background: var(--accent);
      color: var(--accent-ink);
      text-decoration: none;
      font-weight: 600;
      font-size: 14px;
      padding: 13px 24px;
      min-height: 44px;
      border-radius: var(--btn-radius);
      transition: opacity 0.15s ease, transform 0.15s ease;
      cursor: pointer;
    }}
    .btn-primary:hover {{ opacity: 0.9; transform: translateY(-1px); }}
    .btn-primary:active {{ transform: translateY(0); }}
    .btn-secondary {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      background: transparent;
      color: var(--ink);
      border-bottom: 1.5px solid var(--ink);
      text-decoration: none;
      font-weight: 600;
      font-size: 14px;
      padding: 12px 4px;
    }}

    /* Borderless horizontal key facts strip (replaces heavy hero-card & slop stat boxes) */
    .hero-facts {{
      display: grid;
      grid-template-columns: 1fr;
      gap: 14px;
      padding-top: 20px;
      border-top: 1px solid var(--border);
    }}
    @media (min-width: 540px) {{
      .hero-facts {{ grid-template-columns: repeat(2, 1fr); gap: 18px; }}
    }}
    .hero-fact-row {{ display: flex; flex-direction: column; gap: 2px; }}
    .hero-fact-label {{
      font-family: var(--font-mono);
      font-size: 10px;
      letter-spacing: 0.1em;
      text-transform: uppercase;
      color: var(--muted);
    }}
    .hero-fact-val {{ font-size: 14px; font-weight: 600; color: var(--ink); }}

    .hero-media {{
      position: relative;
      overflow: hidden;
      border-radius: var(--radius);
      background: var(--surface);
    }}
    .hero-media img {{
      width: 100%;
      aspect-ratio: 16 / 11;
      object-fit: cover;
      object-position: center;
    }}
    .media-caption {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
      padding: 10px 2px 0;
      font-family: var(--font-mono);
      font-size: 11px;
      color: var(--muted);
    }}

    /* Concept-only clean borderless signature strip */
    .signature-ledger {{
      margin-top: 32px;
      padding-top: 22px;
      border-top: 1px solid var(--border);
      display: grid;
      grid-template-columns: 1fr;
      gap: 14px;
    }}
    @media (min-width: 720px) {{
      .signature-ledger {{ grid-template-columns: repeat(3, 1fr); gap: 28px; }}
    }}
    .sig-item {{
      display: flex;
      justify-content: space-between;
      align-items: baseline;
      gap: 12px;
      padding-bottom: 12px;
      border-bottom: 1px solid var(--border);
    }}
    .sig-item strong {{ font-size: 15px; font-weight: 600; color: var(--ink); }}
    .sig-item span {{ font-family: var(--font-mono); font-size: 13px; color: var(--accent); white-space: nowrap; }}

    /* === FULL DEMO SECTIONS (EDITORIAL HAIRLINES + PHOTOGRAPHY — ZERO BOXY GRIDS) === */
    section {{
      padding: 58px 0;
      border-bottom: 1px solid var(--border);
    }}
    .section-top {{
      display: flex;
      flex-direction: column;
      gap: 10px;
      margin-bottom: 34px;
      max-width: 680px;
    }}
    .section-top h2 {{ font-size: clamp(30px, 5vw, 52px); }}
    .section-top p {{ font-size: 15px; color: var(--muted); }}

    /* Editorial split: photo + clean borderless menu/tariff ledger */
    .editorial-split {{
      display: grid;
      grid-template-columns: 1fr;
      gap: 32px;
      align-items: start;
    }}
    @media (min-width: 860px) {{
      .editorial-split {{ grid-template-columns: 0.85fr 1.15fr; gap: 52px; }}
    }}
    .editorial-photo-col {{ display: flex; flex-direction: column; gap: 16px; }}
    .editorial-photo-frame {{
      overflow: hidden;
      border-radius: var(--radius);
      background: var(--surface);
    }}
    .editorial-photo-frame img {{ width: 100%; aspect-ratio: 4 / 3; object-fit: cover; }}
    .editorial-photo-tall img {{ aspect-ratio: 4 / 5; }}

    .ledger-list {{
      display: flex;
      flex-direction: column;
      border-top: 1.5px solid var(--ink);
    }}
    .ledger-row {{
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 6px 20px;
      padding: 20px 0;
      border-bottom: 1px solid var(--border);
      align-items: baseline;
    }}
    .ledger-tag {{
      grid-column: 1 / -1;
      font-family: var(--font-mono);
      font-size: 11px;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: var(--accent);
    }}
    .ledger-row h3 {{ font-size: 19px; font-weight: 700; color: var(--ink); }}
    .ledger-price {{
      font-family: var(--font-mono);
      font-size: 15px;
      font-weight: 600;
      color: var(--ink);
      white-space: nowrap;
    }}
    .ledger-row p {{
      grid-column: 1 / -1;
      font-size: 14px;
      color: var(--muted);
      max-width: 520px;
    }}

    /* Asymmetric Craft / Space Band */
    .story-band {{
      background: var(--surface);
      padding: 56px 0;
      border-bottom: 1px solid var(--border);
    }}
    .story-grid {{
      display: grid;
      grid-template-columns: 1fr;
      gap: 32px;
      align-items: center;
    }}
    @media (min-width: 860px) {{
      .story-grid {{ grid-template-columns: 1.05fr 0.95fr; gap: 52px; }}
    }}
    .story-points {{
      display: flex;
      flex-direction: column;
      margin-top: 24px;
      border-top: 1px solid var(--border);
    }}
    .story-point {{
      display: grid;
      grid-template-columns: 44px 1fr;
      gap: 14px;
      padding: 18px 0;
      border-bottom: 1px solid var(--border);
      align-items: start;
    }}
    .story-num {{
      font-family: var(--font-mono);
      font-size: 13px;
      font-weight: 600;
      color: var(--accent);
      padding-top: 2px;
    }}
    .story-point h3 {{ font-size: 17px; font-weight: 700; margin-bottom: 4px; }}
    .story-point p {{ font-size: 14px; color: var(--muted); }}

    /* Borderless FAQ & Visit Location */
    .faq-visit-grid {{
      display: grid;
      grid-template-columns: 1fr;
      gap: 40px;
    }}
    @media (min-width: 860px) {{
      .faq-visit-grid {{ grid-template-columns: 1.15fr 0.85fr; gap: 56px; }}
    }}
    .faq-list {{ border-top: 1px solid var(--border); }}
    .faq-item {{ border-bottom: 1px solid var(--border); padding: 18px 0; }}
    .faq-item summary {{
      font-weight: 600;
      font-size: 15px;
      cursor: pointer;
      list-style: none;
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
    }}
    .faq-item summary::-webkit-details-marker {{ display: none; }}
    .faq-item summary::after {{ content: "+"; font-family: var(--font-mono); color: var(--accent); font-size: 18px; }}
    .faq-item[open] summary::after {{ content: "−"; }}
    .faq-item p {{ margin-top: 10px; font-size: 14px; color: var(--muted); }}

    .visit-panel {{
      background: var(--surface);
      padding: 32px 28px;
      border-radius: var(--radius);
      display: flex;
      flex-direction: column;
      gap: 18px;
    }}
    .visit-panel h3 {{ font-size: clamp(26px, 3.6vw, 38px); }}
    .visit-meta {{
      display: flex;
      flex-direction: column;
      gap: 12px;
      padding: 14px 0;
      border-top: 1px solid var(--border);
      border-bottom: 1px solid var(--border);
      font-size: 14px;
    }}
    .visit-meta strong {{ display: block; font-family: var(--font-mono); font-size: 10px; letter-spacing: 0.1em; text-transform: uppercase; color: var(--muted); margin-bottom: 2px; }}

    footer {{
      background: var(--footer-bg);
      color: var(--footer-ink);
      padding: 32px 0;
    }}
    .footer-inner {{
      display: flex;
      flex-wrap: wrap;
      justify-content: space-between;
      gap: 12px;
      font-family: var(--font-mono);
      font-size: 12px;
      opacity: 0.85;
    }}

    /* FLOATING @GOANDALAN PREVIEW PILL */
    .goandalan-pill {{
      position: fixed;
      left: 50%;
      bottom: 16px;
      transform: translateX(-50%);
      z-index: 50;
      display: inline-flex;
      align-items: center;
      gap: 8px;
      background: rgba(24, 24, 23, 0.92);
      backdrop-filter: blur(8px);
      -webkit-backdrop-filter: blur(8px);
      color: #F6F3EC;
      text-decoration: none;
      font-family: 'IBM Plex Mono', monospace;
      font-size: 11px;
      letter-spacing: 0.04em;
      padding: 9px 18px;
      border-radius: 999px;
      box-shadow: 0 10px 28px rgba(0, 0, 0, 0.25);
      border: 1px solid rgba(246, 243, 236, 0.16);
      white-space: nowrap;
      max-width: calc(100vw - 32px);
      overflow: hidden;
      text-overflow: ellipsis;
      pointer-events: auto;
      transition: opacity 0.2s ease, transform 0.2s ease;
    }}
    .goandalan-pill:hover {{
      background: rgba(18, 18, 17, 0.98);
      transform: translateX(-50%) translateY(-1px);
    }}
    .goandalan-dot {{ width: 6px; height: 6px; border-radius: 50%; background: #A7C4A0; flex-shrink: 0; }}
    """


def _build_context(
    lead: dict[str, Any],
    anonymize: bool,
    force_style: str | None = None,
    demo_dir: Path | None = None,
) -> dict[str, Any]:
    preset_key, preset = pick_preset(lead.get("category", ""), lead.get("business_name", ""))
    style_key, theme = select_style_for_lead(lead, force_style=force_style)
    niche_bp = resolve_niche_blueprint(
        category=lead.get("category", ""),
        business_name=lead.get("business_name", ""),
        city=lead.get("city", ""),
        preferred_demo_style=style_key,
    )

    display_name = generate_fictional_name(lead) if anonymize else lead["business_name"]
    display_category = lead.get("category") or "Bisnis Lokal"
    display_city = lead.get("city") or settings.DEFAULT_CITY
    display_address = (
        f"Area {display_city} (Alamat disamarkan untuk konsep studi kasus)"
        if anonymize
        else (lead.get("address") or f"{display_city}, Indonesia")
    )

    if anonymize:
        wa_href = settings.IG_URL
        wa_display = "Konsep Studi Kasus · @goandalan"
        maps_href = "#"
    else:
        wa_num = lead.get("phone_wa") or ""
        prefill = preset["wa_prefill"].format(name=display_name)
        if wa_num:
            wa_href = f"https://wa.me/{wa_num}?text={quote(prefill)}"
            wa_display = lead.get("phone_raw") or f"+{wa_num}"
        else:
            wa_href = settings.IG_URL
            wa_display = "Hubungi langsung"
        maps_href = f"https://www.google.com/maps/search/?api=1&query={quote(display_name + ' ' + display_address)}"

    media = _sync_media_for_demo(demo_dir, niche_bp["photo_set"]) if demo_dir else {}
    return {
        "preset_key": preset_key,
        "preset": preset,
        "niche_bp": niche_bp,
        "style_key": style_key,
        "theme": theme,
        "display_name": display_name,
        "display_category": display_category,
        "display_city": display_city,
        "display_address": display_address,
        "wa_href": wa_href,
        "wa_display": wa_display,
        "maps_href": maps_href,
        "media": media,
    }


def render_concept_hero_html(
    lead: dict[str, Any],
    anonymize: bool = False,
    force_style: str | None = None,
    demo_dir: Path | None = None,
) -> tuple[str, str]:
    """Stage A: Render editorial photo-led Hero Concept HTML (zero slop boxes, zero mobile brand truncation)."""
    target_dir = demo_dir or (settings.DEMOS_DIR / lead["slug"])
    ctx = _build_context(lead, anonymize=anonymize, force_style=force_style, demo_dir=target_dir)
    theme = ctx["theme"]
    preset = ctx["preset"]
    media = ctx["media"]
    hero_src = media.get("hero", "")
    hero_cap = preset["photo_captions"]["hero"]

    sig_items = "".join(
        f'<div class="sig-item"><strong>{_esc(it["name"])}</strong><span>{_esc(it["price"])}</span></div>'
        for it in preset["items"][:3]
    )

    doc = f"""<!DOCTYPE html>
<html lang="id">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{_esc(ctx['display_name'])} — Konsep Halaman ({_esc(theme['label'])})</title>
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="{theme['fonts_url']}" rel="stylesheet" />
  <style>{_common_style_css(theme, concept_only=True)}</style>
</head>
<body>
  <header>
    <div class="container nav-inner">
      <a href="#top" class="brand-mark">{_esc(ctx['display_name'])}</a>
      <nav class="nav-links">
        <a href="#layanan">Menu &amp; Layanan</a>
        <a href="#cerita">Suasana</a>
        <a href="#kontak">Lokasi</a>
      </nav>
      <a href="{_esc(ctx['wa_href'])}" class="nav-cta">
        <span class="cta-full">{_esc(preset['cta_label'])} →</span>
        <span class="cta-short">{_esc(preset['cta_short'])} →</span>
      </a>
    </div>
  </header>

  <main id="top">
    <div class="container">
      <div class="hero" style="border-bottom: 0;">
        <div class="hero-grid">
          <div>
            <div class="hero-eyebrow">
              <span>{_esc(preset['badge'])}</span>
              <span class="eyebrow-sep">·</span>
              <span>{_esc(ctx['display_city'])}</span>
            </div>
            <h1 class="display">{_esc(preset['headline'])}</h1>
            <p class="hero-sub">{_esc(preset['sub'])}</p>
            <div class="hero-actions">
              <a href="{_esc(ctx['wa_href'])}" data-flow="cta" class="btn-primary">{_esc(preset['cta_label'])}</a>
              <a href="#layanan" data-flow="step-1" class="btn-secondary">{_esc(preset['secondary_label'])} →</a>
            </div>

            <div class="hero-facts">
              <div class="hero-fact-row">
                <span class="hero-fact-label">Jam Operasional</span>
                <span class="hero-fact-val">{_esc(preset['hours'])}</span>
              </div>
              <div class="hero-fact-row">
                <span class="hero-fact-label">Lokasi</span>
                <span class="hero-fact-val">{_esc(ctx['display_address'])}</span>
              </div>
            </div>
          </div>

          <figure class="hero-media">
            <img src="{_esc(hero_src)}" alt="{_esc(hero_cap)}" />
            <figcaption class="media-caption">
              <span>{_esc(hero_cap)}</span>
              <span>{_esc(ctx['display_city'])}</span>
            </figcaption>
          </figure>
        </div>

        <div class="signature-ledger" id="layanan" data-flow="step-2">
          {sig_items}
        </div>
      </div>
    </div>
  </main>
</body>
</html>
"""
    return doc, ctx["style_key"]


def render_demo_html(
    lead: dict[str, Any],
    anonymize: bool = False,
    force_style: str | None = None,
    demo_dir: Path | None = None,
    production: bool = False,
) -> tuple[str, str]:
    """Render single-page Pre-DP landing demo (`production=False`) or full production site (`production=True`)."""
    target_dir = demo_dir or (settings.DEMOS_DIR / lead["slug"])
    ctx = _build_context(lead, anonymize=anonymize, force_style=force_style, demo_dir=target_dir)
    theme = ctx["theme"]
    preset = ctx["preset"]
    media = ctx["media"]

    hero_src = media.get("hero", "")
    sec_src = media.get("secondary", "")
    acc_src = media.get("accent", "")
    caps = preset["photo_captions"]

    ledger_html = "".join(
        f"""
        <article class="ledger-row">
          <span class="ledger-tag">{_esc(item['tag'])}</span>
          <h3>{_esc(item['name'])}</h3>
          <span class="ledger-price">{_esc(item['price'])}</span>
          <p>{_esc(item['desc'])}</p>
        </article>
        """
        for item in preset["items"]
    )

    story_points_html = "".join(
        f"""
        <div class="story-point">
          <span class="story-num">{_esc(num)}</span>
          <div>
            <h3>{_esc(title)}</h3>
            <p>{_esc(desc)}</p>
          </div>
        </div>
        """
        for num, title, desc in preset["highlights"]
    )

    faqs_html = "".join(
        f"""
        <details class="faq-item">
          <summary>{_esc(q)}</summary>
          <p>{_esc(a)}</p>
        </details>
        """
        for q, a in preset["faqs"]
    )

    map_link_html = (
        f'<a href="{_esc(ctx["maps_href"])}" class="btn-secondary" target="_blank" rel="noopener noreferrer">Buka Peta Lokasi →</a>'
        if not anonymize
        else ""
    )

    mode_meta = "production-full" if production else "pre-dp-landing"
    nav_story_link = '<a href="#cerita">Craft &amp; Ruang</a>' if production else ""
    story_section_html = (
        f"""
    <div class="story-band" id="cerita">
      <div class="container">
        <div class="story-grid">
          <div>
            <span class="mono-tag">02 / {_esc(preset['gallery_kicker'])}</span>
            <h2 class="display" style="font-size: clamp(30px, 4.8vw, 48px); margin-top: 10px;">{_esc(preset['gallery_title'])}</h2>
            <div class="story-points">
              {story_points_html}
            </div>
          </div>
          <figure class="editorial-photo-frame editorial-photo-tall">
            <img src="{_esc(acc_src)}" alt="{_esc(caps['accent'])}" loading="lazy" decoding="async" />
            <figcaption class="media-caption" style="padding: 12px 2px 0;">
              <span>{_esc(caps['accent'])}</span>
            </figcaption>
          </figure>
        </div>
      </div>
    </div>
"""
        if production
        else ""
    )
    faq_num = "03" if production else "02"
    contact_num = "04" if production else "03"
    watermark_pill_html = (
        ""
        if production
        else f"""
  <a class="goandalan-pill" href="{_esc(settings.IG_URL)}" target="_blank" rel="noopener noreferrer">
    <span class="goandalan-dot"></span>
    <span>preview konsep oleh @{_esc(settings.IG_USERNAME)} · mikir bareng alan</span>
  </a>"""
    )

    doc = f"""<!DOCTYPE html>
<html lang="id">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <meta name="goandalan-demo-mode" content="{mode_meta}" />
  <title>{_esc(ctx['display_name'])} — {_esc(ctx['display_category'])}</title>
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="{theme['fonts_url']}" rel="stylesheet" />
  <style>{_common_style_css(theme, concept_only=False, production=production)}</style>
</head>
<body>
  <header>
    <div class="container nav-inner">
      <a href="#top" class="brand-mark">{_esc(ctx['display_name'])}</a>
      <nav class="nav-links">
        <a href="#layanan">Layanan &amp; Menu</a>
        {nav_story_link}
        <a href="#faq">FAQ</a>
        <a href="#kontak">Lokasi &amp; Kontak</a>
      </nav>
      <a href="{_esc(ctx['wa_href'])}" class="nav-cta" target="_blank" rel="noopener noreferrer">
        <span class="cta-full">{_esc(preset['cta_label'])} →</span>
        <span class="cta-short">{_esc(preset['cta_short'])} →</span>
      </a>
    </div>
  </header>

  <main id="top">
    <div class="container">
      <div class="hero">
        <div class="hero-grid">
          <div>
            <div class="hero-eyebrow">
              <span>{_esc(preset['badge'])}</span>
              <span class="eyebrow-sep">·</span>
              <span>{_esc(ctx['display_city'])}</span>
            </div>
            <h1 class="display">{_esc(preset['headline'])}</h1>
            <p class="hero-sub">{_esc(preset['sub'])}</p>
            <div class="hero-actions">
              <a href="{_esc(ctx['wa_href'])}" data-flow="cta" class="btn-primary" target="_blank" rel="noopener noreferrer">{_esc(preset['cta_label'])}</a>
              <a href="#layanan" data-flow="step-1" class="btn-secondary">{_esc(preset['secondary_label'])} →</a>
            </div>
            <div class="hero-facts">
              <div class="hero-fact-row">
                <span class="hero-fact-label">Jam Operasional</span>
                <span class="hero-fact-val">{_esc(preset['hours'])}</span>
              </div>
              <div class="hero-fact-row">
                <span class="hero-fact-label">Alamat</span>
                <span class="hero-fact-val">{_esc(ctx['display_address'])}</span>
              </div>
            </div>
          </div>

          <figure class="hero-media">
            <img src="{_esc(hero_src)}" alt="{_esc(caps['hero'])}" decoding="async" />
            <figcaption class="media-caption">
              <span>{_esc(caps['hero'])}</span>
              <span>{_esc(ctx['display_name'])}</span>
            </figcaption>
          </figure>
        </div>
      </div>

      <section id="layanan" data-flow="step-2">
        <div class="section-top">
          <span class="mono-tag">01 / {_esc(preset['badge'])}</span>
          <h2 class="display">{_esc(preset['section_title'])}</h2>
          <p>{_esc(preset['section_sub'])}</p>
        </div>

        <div class="editorial-split">
          <div class="editorial-photo-col">
            <figure class="editorial-photo-frame">
              <img src="{_esc(sec_src)}" alt="{_esc(caps['secondary'])}" loading="lazy" decoding="async" />
            </figure>
            <p class="media-caption"><span>{_esc(caps['secondary'])}</span></p>
          </div>
          <div class="ledger-list">
            {ledger_html}
          </div>
        </div>
      </section>
    </div>
{story_section_html}
    <div class="container">
      <section id="faq" style="border-bottom: 0;">
        <div class="faq-visit-grid">
          <div>
            <span class="mono-tag">{faq_num} / PERTANYAAN UMUM</span>
            <h2 class="display" style="font-size: clamp(28px, 4.2vw, 42px); margin: 10px 0 24px;">Hal yang sering ditanyakan sebelum datang.</h2>
            <div class="faq-list">
              {faqs_html}
            </div>
          </div>

          <aside class="visit-panel" id="kontak">
            <span class="mono-tag">{contact_num} / LOKASI, JAM &amp; KONTAK WA</span>
            <h3 class="display">Mampir ke {_esc(ctx['display_name'])}.</h3>
            <div class="visit-meta">
              <div><strong>Alamat</strong>{_esc(ctx['display_address'])}</div>
              <div><strong>Jam Buka</strong>{_esc(preset['hours'])}</div>
              <div><strong>WhatsApp</strong>{_esc(ctx['wa_display'])}</div>
            </div>
            <div style="display: flex; flex-wrap: wrap; gap: 14px; align-items: center;">
              <a href="{_esc(ctx['wa_href'])}" class="btn-primary" target="_blank" rel="noopener noreferrer">{_esc(preset['cta_label'])} →</a>
              {map_link_html}
            </div>
          </aside>
        </div>
      </section>
    </div>
  </main>

  <footer>
    <div class="container footer-inner">
      <span>{_esc(ctx['display_name'])} · {_esc(ctx['display_city'])}</span>
      <span>{_esc(preset['hours'])}</span>
    </div>
  </footer>
{watermark_pill_html}
</body>
</html>
"""
    return doc, ctx["style_key"]


def rebuild_portfolio_index(site_dir: Path | None = None) -> Path:
    """Update site/index.html ONLY with leads that have a full multi-section demo built."""
    out_dir = site_dir or settings.SITE_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    leads = db.list_leads()
    published_statuses = {"FULL_DEMO_READY", "DP_PAID", "WON", "RECYCLED_CONTENT"}
    demo_leads = []
    for l in leads:
        slug = l.get("slug")
        demo_rel = l.get("demo_path")
        has_file = False
        if demo_rel and (settings.BASE_DIR / demo_rel).exists():
            has_file = True
        elif slug and (settings.DEMOS_DIR / slug / "index.html").exists():
            has_file = True
            demo_rel = f"site/demos/{slug}/index.html"
            db.update_lead(l["id"], {"demo_path": demo_rel, "demo_url": f"/demos/{slug}/index.html"})
            l["demo_path"] = demo_rel
            l["demo_url"] = f"/demos/{slug}/index.html"
        if has_file and l.get("status") in published_statuses:
            demo_leads.append(l)

    cards_html: list[str] = []
    for idx, lead in enumerate(demo_leads, start=1):
        is_anon = bool(lead.get("is_anonymized"))
        title = (lead.get("anonymized_name") or generate_fictional_name(lead)) if is_anon else lead["business_name"]
        _, theme = select_style_for_lead(lead)
        badge = "CONCEPT CASE STUDY" if is_anon else (lead.get("category") or "SELECTED WORK")
        slug = lead["slug"]
        href = f"./demos/{slug}/index.html"
        flaw = lead.get("ux_flaw") or "Halaman editorial ringan dan jernih untuk layar HP."
        cards_html.append(
            f"""
            <a class="demo-row" href="{_esc(href)}">
              <div class="row-meta">
                <span class="mono-badge">{idx:02d} / {_esc(badge)}</span>
                <span class="mono-style">{_esc(theme['label'])}</span>
              </div>
              <h2 class="serif">{_esc(title)}</h2>
              <p class="desc">{_esc(flaw)}</p>
              <div class="row-footer">
                <span class="row-pill">Mobile 390px Verified</span>
                <span class="row-link">buka live preview →</span>
              </div>
            </a>
            """
        )

    if not cards_html:
        cards_html.append(
            """
            <div class="empty-box">
              <p class="mono">KATALOG FULL DEMO</p>
              <p style="margin-top: 8px; color: var(--muted);">Demo penuh yang sudah di-approve / di-generate untuk prospek tertarik akan tampil otomatis di sini.</p>
            </div>
            """
        )

    html_doc = f"""<!DOCTYPE html>
<html lang="id">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>gw sama alan (@{_esc(settings.IG_USERNAME)}) — Selected Work</title>
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&family=IBM+Plex+Mono:wght@400;500&family=Plus+Jakarta+Sans:wght@400;500;600&display=swap" rel="stylesheet" />
  <style>
    :root {{
      --bg: #F6F3EC;
      --surface: #EDE8DD;
      --surface-hover: #E5DFD2;
      --ink: #1C1917;
      --muted: #625E56;
      --accent: #284B36;
      --accent-hover: #1e3b2b;
      --border: rgba(28, 25, 23, 0.14);
      --card-bg: rgba(255, 255, 255, 0.45);
      --card-border: rgba(28, 25, 23, 0.12);
      --badge-bg: rgba(40, 75, 54, 0.08);
      --badge-ink: #284B36;
    }}
    @media (prefers-color-scheme: dark) {{
      :root {{
        --bg: #121110;
        --surface: #1B1A18;
        --surface-hover: #242220;
        --ink: #F4EFE6;
        --muted: #A39D93;
        --accent: #86B093;
        --accent-hover: #A7C4A0;
        --border: rgba(244, 239, 230, 0.14);
        --card-bg: rgba(27, 26, 24, 0.5);
        --card-border: rgba(244, 239, 230, 0.12);
        --badge-bg: rgba(134, 176, 147, 0.12);
        --badge-ink: #A7C4A0;
      }}
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    html, body {{
      overflow-x: hidden;
      max-width: 100vw;
    }}
    body {{
      background: var(--bg);
      color: var(--ink);
      font-family: 'Plus Jakarta Sans', sans-serif;
      line-height: 1.6;
      -webkit-font-smoothing: antialiased;
    }}
    .wrap {{
      max-width: 900px;
      margin: 0 auto;
      padding: 36px 20px 72px;
    }}
    .topbar {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding-bottom: 18px;
      border-bottom: 1px solid var(--border);
      font-family: 'IBM Plex Mono', monospace;
      font-size: 11px;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: var(--muted);
      flex-wrap: wrap;
      gap: 8px;
    }}
    .hero {{ padding: 44px 0 32px; }}
    .serif {{ font-family: 'Instrument Serif', Georgia, serif; font-weight: 400; letter-spacing: -0.02em; line-height: 1.04; }}
    .hero h1 {{ font-size: clamp(38px, 7vw, 68px); margin-bottom: 14px; }}
    .hero h1 em {{ font-style: italic; color: var(--accent); }}
    .hero p {{ font-size: 16px; color: var(--muted); max-width: 580px; }}
    .mono {{ font-family: 'IBM Plex Mono', monospace; font-size: 11px; letter-spacing: 0.08em; text-transform: uppercase; color: var(--muted); }}
    .mono-badge {{ font-family: 'IBM Plex Mono', monospace; font-size: 11px; letter-spacing: 0.08em; text-transform: uppercase; color: var(--accent); font-weight: 500; }}
    .mono-style {{ font-family: 'IBM Plex Mono', monospace; font-size: 11px; letter-spacing: 0.06em; color: var(--muted); }}
    .list {{ border-top: 1.5px solid var(--ink); margin-top: 8px; }}
    .demo-row {{
      display: flex;
      flex-direction: column;
      gap: 12px;
      padding: 28px 20px;
      margin: 0 -20px;
      border-bottom: 1px solid var(--border);
      text-decoration: none;
      color: inherit;
      transition: background 0.2s ease, transform 0.15s ease;
      border-radius: 8px;
    }}
    .demo-row:hover {{
      background: var(--surface);
    }}
    .row-meta {{ display: flex; justify-content: space-between; gap: 8px; flex-wrap: wrap; align-items: center; }}
    .demo-row h2 {{ font-size: clamp(28px, 4.5vw, 40px); color: var(--ink); line-height: 1.15; }}
    .demo-row p.desc {{ font-size: 15px; color: var(--muted); max-width: 660px; line-height: 1.55; }}
    .row-footer {{ display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 10px; padding-top: 4px; }}
    .row-pill {{
      display: inline-flex;
      align-items: center;
      gap: 5px;
      font-family: 'IBM Plex Mono', monospace;
      font-size: 10px;
      letter-spacing: 0.06em;
      text-transform: uppercase;
      padding: 3px 9px;
      border-radius: 999px;
      background: var(--badge-bg);
      color: var(--badge-ink);
    }}
    .row-link {{
      font-family: 'IBM Plex Mono', monospace;
      font-size: 12px;
      color: var(--accent);
      font-weight: 500;
      transition: color 0.15s ease, transform 0.15s ease;
    }}
    .demo-row:hover .row-link {{ color: var(--accent-hover); transform: translateX(2px); }}
    .empty-box {{ padding: 36px 0; border-bottom: 1px solid var(--border); }}
    .cta-box {{
      margin-top: 48px;
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      padding-top: 24px;
      border-top: 1px solid var(--border);
    }}
    .cta-btn {{
      display: inline-flex;
      align-items: center;
      background: var(--ink);
      color: var(--bg);
      text-decoration: none;
      font-family: 'IBM Plex Mono', monospace;
      font-size: 13px;
      padding: 12px 22px;
      border-radius: 999px;
      transition: opacity 0.15s ease, transform 0.15s ease;
    }}
    .cta-btn:hover {{ opacity: 0.9; transform: translateY(-1px); }}
  </style>
</head>
<body>
  <div class="wrap">
    <div class="topbar">
      <span>GW &amp; ALAN</span>
      <span>@{_esc(settings.IG_USERNAME)} · SELECTED WORK</span>
    </div>

    <header class="hero">
      <h1 class="serif">Mikir bareng <em>Alan.</em><br>Orangnya fiktif, hasilnya real.</h1>
      <p>Kumpulan preview &amp; studi kasus website bisnis lokal dengan karakter visual unik per brand.</p>
    </header>

    <main class="list">
      {''.join(cards_html)}
    </main>

    <footer class="cta-box">
      <div>
        <div class="mono">SELECTED WEBSITE CONCEPTS</div>
        <p style="color: var(--muted); font-size: 14px; margin-top: 4px;">arsip preview konsep website lokal · @{_esc(settings.IG_USERNAME)}</p>
      </div>
      <a class="cta-btn" href="{_esc(settings.IG_URL)}" target="_blank" rel="noopener noreferrer">@{_esc(settings.IG_USERNAME)} →</a>
    </footer>
  </div>
</body>
</html>
"""
    index_path = out_dir / "index.html"
    index_path.write_text(html_doc, encoding="utf-8")
    return index_path


def generate_concept_html_for_lead(
    lead_id: int,
    anonymize: bool = False,
    force_style: str | None = None,
) -> dict[str, Any]:
    """Stage A: Build editorial concept HTML only (does NOT generate full index.html or update site/index.html)."""
    lead = db.get_lead(lead_id)
    if not lead:
        raise ValueError(f"Lead ID {lead_id} tidak ditemukan.")

    slug = lead["slug"]
    demo_dir = settings.DEMOS_DIR / slug
    demo_dir.mkdir(parents=True, exist_ok=True)
    concept_file = demo_dir / "concept.html"

    html_content, chosen_style = render_concept_hero_html(
        lead, anonymize=anonymize, force_style=force_style, demo_dir=demo_dir
    )
    concept_file.write_text(html_content, encoding="utf-8")

    updates: dict[str, Any] = {"design_style": chosen_style}
    if anonymize:
        updates["is_anonymized"] = 1
        updates["anonymized_name"] = generate_fictional_name(lead)
    updated_lead = db.update_lead(lead_id, updates)

    return {
        "lead": updated_lead,
        "concept_file": str(concept_file),
        "design_style": chosen_style,
        "style_label": STYLE_THEMES[chosen_style]["label"],
    }


def generate_full_demo_for_lead(
    lead_id: int,
    anonymize: bool = False,
    force_style: str | None = None,
    update_status: bool = True,
    production: bool = False,
) -> dict[str, Any]:
    """Generate 1-page Pre-DP landing demo (`production=False`) or full production site (`production=True`)."""
    lead = db.get_lead(lead_id)
    if not lead:
        raise ValueError(f"Lead ID {lead_id} tidak ditemukan.")

    slug = lead["slug"]
    demo_dir = settings.DEMOS_DIR / slug
    demo_dir.mkdir(parents=True, exist_ok=True)
    demo_file = demo_dir / "index.html"

    fictional_name = generate_fictional_name(lead) if anonymize else (lead.get("anonymized_name") or "")
    html_content, chosen_style = render_demo_html(
        lead,
        anonymize=anonymize,
        force_style=force_style,
        demo_dir=demo_dir,
        production=production,
    )
    demo_file.write_text(html_content, encoding="utf-8")

    rel_demo_path = str(demo_file.relative_to(settings.BASE_DIR)).replace("\\", "/")
    updates: dict[str, Any] = {
        "design_style": chosen_style,
        "demo_path": rel_demo_path,
        "demo_url": f"/demos/{slug}/index.html",
    }
    if anonymize:
        updates["is_anonymized"] = 1
        updates["anonymized_name"] = fictional_name
        updates["status"] = "RECYCLED_CONTENT"
    elif update_status and lead["status"] not in {"DP_PAID", "WON"}:
        updates["status"] = "FULL_DEMO_READY"

    updated_lead = db.update_lead(lead_id, updates)
    index_path = rebuild_portfolio_index()

    return {
        "lead": updated_lead,
        "demo_file": str(demo_file),
        "index_file": str(index_path),
        "design_style": chosen_style,
        "style_label": STYLE_THEMES[chosen_style]["label"],
        "anonymized": anonymize,
        "mode": "production" if production else "pre_dp_landing",
        "watermark_removed": bool(production),
    }


generate_demo_for_lead = generate_full_demo_for_lead


def list_available_styles() -> list[dict[str, str]]:
    return [
        {"key": k, "label": v["label"], "source": v["source"]}
        for k, v in STYLE_THEMES.items()
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description="@goandalan Anti-Slop Multi-Style Demo Generator")
    parser.add_argument("--slug", help="Slug lead tertentu")
    parser.add_argument("--lead-id", type=int, help="ID lead tertentu")
    parser.add_argument("--mode", choices=["concept", "full"], default="concept", help="Stage A concept atau Stage B/C landing/production")
    parser.add_argument("--production", action="store_true", help="Mode produksi penuh (lepas watermark konsep, setelah DP_PAID)")
    parser.add_argument("--style", choices=list(STYLE_THEMES.keys()), help="Override design style")
    parser.add_argument("--anonymize", action="store_true", help="Gunakan brand fiktif")
    parser.add_argument("--list-styles", action="store_true", help="Tampilkan semua style tersedia")
    args = parser.parse_args()

    if args.list_styles:
        for s in list_available_styles():
            print(f"- {s['key']}: {s['label']} ({s['source']})")
        return

    db.init_db()
    lead = db.get_lead(args.lead_id) if args.lead_id else db.get_lead_by_slug(args.slug or "")
    if not lead:
        rebuild_portfolio_index()
        print(f"[OK] Rebuilt portfolio index at {settings.SITE_DIR / 'index.html'}")
        return

    if args.mode == "concept":
        res = generate_concept_html_for_lead(lead["id"], anonymize=args.anonymize, force_style=args.style)
        print(f"[OK] Stage A concept HTML: {res['concept_file']} (style={res['design_style']})")
    else:
        res = generate_full_demo_for_lead(
            lead["id"],
            anonymize=args.anonymize,
            force_style=args.style,
            production=args.production,
        )
        print(f"[OK] Stage B/C HTML ({res['mode']}): {res['demo_file']} (style={res['design_style']})")


if __name__ == "__main__":
    main()
