"""12-Style Adaptive Design Intelligence Library (carousel_design_system_website_showcase.md).

Supports all 12 visual styles, 10 storytelling methods, 14 composition methods,
demo_style mapping, industry recommendations, and local Pillow reference-image
palette extraction (zero external/paid APIs).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PIL import Image


STORYTELLING_METHODS: dict[str, dict[str, str]] = {
    "origin_to_experience": {
        "label": "Origin to Experience",
        "arc": "Karakter brand -> konsep digital -> website reveal -> fitur pendukung pengalaman.",
    },
    "bold_statement": {
        "label": "Bold Statement",
        "arc": "Pernyataan kuat -> konteks singkat -> bukti visual website -> detail fitur.",
    },
    "problem_solution_proof": {
        "label": "Friction to Clarity Showcase",
        "arc": "Konteks kebutuhan pengunjung -> keputusan arsitektur antarmuka -> tampilan nyata website -> detail interaksi pendukung.",
    },
    "product_reveal": {
        "label": "Product Reveal",
        "arc": "Teaser visual -> reveal tampilan utama -> detail desktop & mobile -> fitur inti.",
    },
    "before_after": {
        "label": "Before -> After",
        "arc": "Kondisi awal (hanya jika nyata) -> arah rombakan -> hasil website -> detail perubahan.",
    },
    "behind_the_design": {
        "label": "Behind the Design",
        "arc": "Ide/arah -> palet & tipografi -> implementasi website -> keputusan detail UI.",
    },
    "feature_led": {
        "label": "Feature-led",
        "arc": "Kebutuhan pengguna -> fitur utama -> pengalaman antarmuka -> ringkasan visual.",
    },
    "immersive_lifestyle": {
        "label": "Immersive / Lifestyle Story",
        "arc": "Bangun suasana -> hubungkan dengan brand -> tampilkan website -> dukungan pengalaman.",
    },
    "user_journey": {
        "label": "Walkthrough / User Journey",
        "arc": "Kebutuhan pengunjung -> langkah pertama -> eksplorasi -> jalur aksi akhir.",
    },
    "proof_trust_led": {
        "label": "Evidence-First Interface Showcase",
        "arc": "Konteks kepercayaan brand -> bukti informasi nyata di website -> struktur layanan & transparansi -> ringkasan pengalaman antarmuka.",
    },
}

COMPOSITION_METHODS: tuple[str, ...] = (
    "full_bleed_hero",
    "split_composition",
    "overlapping_devices",
    "asymmetric_collage",
    "typography_led",
    "ui_closeup",
    "browser_window",
    "layered_cards",
    "photo_interface",
    "grid_showcase",
    "journey_strip",
    "annotated_interface",
    "device_free_screenshot",
    "editorial_typography_overlay",
)


# Complete 12 Visual Directions from carousel_design_system_website_showcase.md Section 4
STYLE_LIBRARY_12: dict[str, dict[str, Any]] = {
    "editorial_magazine": {
        "label": "Editorial & Magazine",
        "secondary_default": "Minimal / Swiss Grid",
        "storytelling_default": "behind_the_design",
        "closing_label": "A closer look",
        "industries": ("fashion", "beauty", "interior", "architecture", "portfolio", "lifestyle", "studio"),
        "fonts_url": "https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&family=JetBrains+Mono:wght@400;500&family=Plus+Jakarta+Sans:wght@400;500;600&display=swap",
        "font_display": "'Instrument Serif', Georgia, serif",
        "font_body": "'Plus Jakarta Sans', sans-serif",
        "font_mono": "'JetBrains Mono', monospace",
        "palette": {
            "bg": "#F6F3EC",
            "surface": "#EDE8DD",
            "ink": "#1E1E1E",
            "muted": "#6B675F",
            "accent": "#3E4E3C",
            "accent_2": "#9A523B",
            "badge_bg": "rgba(62, 78, 60, 0.12)",
            "badge_ink": "#3E4E3C",
            "border": "rgba(30, 30, 30, 0.13)",
        },
        "geometry": {"radius": "16px", "border_width": "1px", "shadow": "0 18px 46px rgba(30,30,30,0.08)", "top_stripe": False, "uppercase_display": False, "dark": False, "brutalist": False, "grid_bg": False},
        "compositions": {
            "slide_1": "editorial_typography_overlay",
            "slide_2": "photo_interface",
            "slide_3": "overlapping_devices",
            "slide_4": "annotated_interface",
        },
        "direction_summary": "Ritme halaman majalah independen dengan Instrument Serif, garis tipis terukur, dan whitespace terkurasi untuk menjaga fokus pada antarmuka.",
    },
    "bold_brutalist": {
        "label": "Bold Typography / Brutalist",
        "secondary_default": "Digital Product / UI Showcase",
        "storytelling_default": "bold_statement",
        "closing_label": "Website concept",
        "industries": ("creative agency", "streetwear", "event", "musik", "komunitas", "gym", "barber", "startup"),
        "fonts_url": "https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@500;700&family=Space+Grotesk:wght@400;500;600;700&family=Syne:wght@700;800&display=swap",
        "font_display": "'Syne', 'Space Grotesk', sans-serif",
        "font_body": "'Space Grotesk', sans-serif",
        "font_mono": "'JetBrains Mono', monospace",
        "palette": {
            "bg": "#F6F4EC",
            "surface": "#FFFDF6",
            "ink": "#111111",
            "muted": "#454545",
            "accent": "#E85D2A",
            "accent_2": "#D9F99D",
            "badge_bg": "#D9F99D",
            "badge_ink": "#111111",
            "border": "#111111",
        },
        "geometry": {"radius": "0px", "border_width": "2px", "shadow": "6px 6px 0px #111111", "top_stripe": False, "uppercase_display": True, "dark": False, "brutalist": True, "grid_bg": False},
        "compositions": {
            "slide_1": "typography_led",
            "slide_2": "journey_strip",
            "slide_3": "overlapping_devices",
            "slide_4": "grid_showcase",
        },
        "direction_summary": "Tipografi display Syne yang kuat, kontras tinggi, dan border solid 2px dengan hard-shadow untuk mencuri perhatian tanpa menutupi UI.",
    },
    "digital_product": {
        "label": "Digital Product / UI Showcase",
        "secondary_default": "Minimal / Swiss Grid",
        "storytelling_default": "feature_led",
        "closing_label": "Explore the interface",
        "industries": ("saas", "aplikasi", "fintech", "edtech", "healthtech", "platform", "dashboard", "e-commerce"),
        "fonts_url": "https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=Inter:wght@400;500;600;700&family=Space+Grotesk:wght@600;700&display=swap",
        "font_display": "'Space Grotesk', 'Inter', sans-serif",
        "font_body": "'Inter', sans-serif",
        "font_mono": "'IBM Plex Mono', monospace",
        "palette": {
            "bg": "#F8FAFC",
            "surface": "#FFFFFF",
            "ink": "#0F172A",
            "muted": "#475569",
            "accent": "#1D4ED8",
            "accent_2": "#0D9488",
            "badge_bg": "#DBEAFE",
            "badge_ink": "#1E40AF",
            "border": "#CBD5E1",
        },
        "geometry": {"radius": "14px", "border_width": "1px", "shadow": "0 16px 40px rgba(15,23,42,0.08)", "top_stripe": False, "uppercase_display": False, "dark": False, "brutalist": False, "grid_bg": False},
        "compositions": {
            "slide_1": "split_composition",
            "slide_2": "journey_strip",
            "slide_3": "browser_window",
            "slide_4": "annotated_interface",
        },
        "direction_summary": "Pendekatan interface-first modern dengan hierarki produk yang presisi, callout fitur nyata, dan keterbacaan antarmuka maksimal.",
    },
    "swiss_minimal": {
        "label": "Minimal / Swiss Grid",
        "secondary_default": "Technical / Architectural",
        "storytelling_default": "user_journey",
        "closing_label": "Explore the interface",
        "industries": ("klinik", "dental", "barbershop", "konsultan", "b2b", "corporate", "arsitektur", "pendidikan"),
        "fonts_url": "https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap",
        "font_display": "'Plus Jakarta Sans', Arial, sans-serif",
        "font_body": "'Plus Jakarta Sans', Arial, sans-serif",
        "font_mono": "'IBM Plex Mono', monospace",
        "palette": {
            "bg": "#F6F4EE",
            "surface": "#ECE9E0",
            "ink": "#121417",
            "muted": "#4C5159",
            "accent": "#C93E23",
            "accent_2": "#121417",
            "badge_bg": "#ECE9E0",
            "badge_ink": "#121417",
            "border": "rgba(18, 20, 23, 0.18)",
        },
        "geometry": {"radius": "0px", "border_width": "1px", "shadow": "none", "top_stripe": True, "uppercase_display": False, "dark": False, "brutalist": False, "grid_bg": False},
        "compositions": {
            "slide_1": "split_composition",
            "slide_2": "journey_strip",
            "slide_3": "device_free_screenshot",
            "slide_4": "grid_showcase",
        },
        "direction_summary": "Grid arsitektural bersudut tajam 0px, garis struktural 1px tanpa shadow, dan aksen kontras tinggi agar info layanan terpindai dalam sekejap.",
    },
    "collage_scrapbook": {
        "label": "Collage / Scrapbook / Mixed Media",
        "secondary_default": "Editorial & Magazine",
        "storytelling_default": "origin_to_experience",
        "closing_label": "Inside the experience",
        "industries": ("bakery", "pastry", "artisan", "craft", "florist", "vintage", "travel", "thrift"),
        "fonts_url": "https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,500;0,9..144,700;1,9..144,500&family=JetBrains+Mono:wght@400;500&family=Plus+Jakarta+Sans:wght@400;500;600&display=swap",
        "font_display": "'Fraunces', Georgia, serif",
        "font_body": "'Plus Jakarta Sans', sans-serif",
        "font_mono": "'JetBrains Mono', monospace",
        "palette": {
            "bg": "#F5EFE6",
            "surface": "#FFFBF4",
            "ink": "#261E19",
            "muted": "#6D5E53",
            "accent": "#B55239",
            "accent_2": "#D9A441",
            "badge_bg": "#F2E2C9",
            "badge_ink": "#5A3A1E",
            "border": "rgba(38, 30, 25, 0.16)",
        },
        "geometry": {"radius": "10px", "border_width": "1px", "shadow": "0 14px 32px rgba(38,30,25,0.10)", "top_stripe": False, "uppercase_display": False, "dark": False, "brutalist": False, "grid_bg": False},
        "compositions": {
            "slide_1": "asymmetric_collage",
            "slide_2": "photo_interface",
            "slide_3": "layered_cards",
            "slide_4": "grid_showcase",
        },
        "direction_summary": "Komposisi berlapis yang terasa personal dan tactile seperti zine terkurasi, sambil menjaga screenshot website tetap tegak dan tajam.",
    },
    "cinematic_premium": {
        "label": "Cinematic / Premium Campaign",
        "secondary_default": "Editorial & Magazine",
        "storytelling_default": "immersive_lifestyle",
        "closing_label": "Designed around the brand",
        "industries": ("hotel", "resort", "fine dining", "properti", "automotive", "luxury", "lounge", "tailor"),
        "fonts_url": "https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,500;0,600;1,500&family=JetBrains+Mono:wght@400;500&family=Manrope:wght@400;500;600&display=swap",
        "font_display": "'Cormorant Garamond', Georgia, serif",
        "font_body": "'Manrope', sans-serif",
        "font_mono": "'JetBrains Mono', monospace",
        "palette": {
            "bg": "#0F0F0E",
            "surface": "#1A1917",
            "ink": "#F3EFE6",
            "muted": "#A69F92",
            "accent": "#C8A96E",
            "accent_2": "#E5CFA3",
            "badge_bg": "rgba(200, 169, 110, 0.14)",
            "badge_ink": "#E5CFA3",
            "border": "rgba(243, 239, 230, 0.15)",
        },
        "geometry": {"radius": "6px", "border_width": "1px", "shadow": "0 24px 56px rgba(0,0,0,0.50)", "top_stripe": False, "uppercase_display": False, "dark": True, "brutalist": False, "grid_bg": False},
        "compositions": {
            "slide_1": "full_bleed_hero",
            "slide_2": "photo_interface",
            "slide_3": "overlapping_devices",
            "slide_4": "annotated_interface",
        },
        "direction_summary": "Atmosfer gelap obsidian dengan aksen brass gold dan serif Cormorant Garamond untuk menonjolkan kesan tenang, eksklusif, dan aspiratif.",
    },
    "playful_pop": {
        "label": "Playful / Colorful / Pop",
        "secondary_default": "Photo-led / Interface",
        "storytelling_default": "origin_to_experience",
        "closing_label": "Inside the experience",
        "industries": ("cafe", "gelato", "dessert", "kids", "edukasi", "komunitas", "hiburan", "snack"),
        "fonts_url": "https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,600;12..96,700&family=JetBrains+Mono:wght@400;500&family=Plus+Jakarta+Sans:wght@400;500;600&display=swap",
        "font_display": "'Bricolage Grotesque', sans-serif",
        "font_body": "'Plus Jakarta Sans', sans-serif",
        "font_mono": "'JetBrains Mono', monospace",
        "palette": {
            "bg": "#FFF8F0",
            "surface": "#FBEAD9",
            "ink": "#2B1B15",
            "muted": "#6E5449",
            "accent": "#C84B31",
            "accent_2": "#E9A825",
            "badge_bg": "rgba(233, 168, 37, 0.24)",
            "badge_ink": "#6B4500",
            "border": "rgba(43, 27, 21, 0.14)",
        },
        "geometry": {"radius": "22px", "border_width": "1px", "shadow": "0 14px 36px rgba(43,27,21,0.09)", "top_stripe": False, "uppercase_display": False, "dark": False, "brutalist": False, "grid_bg": False},
        "compositions": {
            "slide_1": "editorial_typography_overlay",
            "slide_2": "photo_interface",
            "slide_3": "overlapping_devices",
            "slide_4": "grid_showcase",
        },
        "direction_summary": "Palet hangat yang cerah, bentuk pill ramah, dan tipografi Bricolage Grotesque yang ekspresif namun tetap jernih di layar HP.",
    },
    "organic_warm": {
        "label": "Organic / Natural / Warm",
        "secondary_default": "Editorial & Magazine",
        "storytelling_default": "origin_to_experience",
        "closing_label": "Inside the experience",
        "industries": ("coffee", "roastery", "wellness", "spa", "farm", "kebun", "wisata", "organic", "kuliner"),
        "fonts_url": "https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,500;0,9..144,700;1,9..144,500&family=JetBrains+Mono:wght@400;500&family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap",
        "font_display": "'Fraunces', Georgia, serif",
        "font_body": "'Plus Jakarta Sans', sans-serif",
        "font_mono": "'JetBrains Mono', monospace",
        "palette": {
            "bg": "#FAF6EC",
            "surface": "#FFFFFF",
            "ink": "#1F2A24",
            "muted": "#56635B",
            "accent": "#2E5E3E",
            "accent_2": "#C46A3B",
            "badge_bg": "rgba(111, 163, 91, 0.20)",
            "badge_ink": "#2E5E3E",
            "border": "rgba(31, 42, 36, 0.12)",
        },
        "geometry": {"radius": "16px", "border_width": "1px", "shadow": "0 12px 32px rgba(31,42,36,0.08)", "top_stripe": False, "uppercase_display": False, "dark": False, "brutalist": False, "grid_bg": False},
        "compositions": {
            "slide_1": "editorial_typography_overlay",
            "slide_2": "photo_interface",
            "slide_3": "overlapping_devices",
            "slide_4": "annotated_interface",
        },
        "direction_summary": "Palet earthy hangat, tipografi Fraunces yang organik, dan ruang bernapas lega untuk menghadirkan rasa hospitality sejak layar pertama.",
    },
    "technical_blueprint": {
        "label": "Technical / Blueprint / Industrial",
        "secondary_default": "Digital Product / UI Showcase",
        "storytelling_default": "problem_solution_proof",
        "closing_label": "Explore the interface",
        "industries": ("engineering", "manufaktur", "konstruksi", "logistik", "it", "cybersecurity", "bengkel"),
        "fonts_url": "https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=Space+Grotesk:wght@500;600;700&display=swap",
        "font_display": "'Space Grotesk', sans-serif",
        "font_body": "'Space Grotesk', sans-serif",
        "font_mono": "'IBM Plex Mono', monospace",
        "palette": {
            "bg": "#0D1520",
            "surface": "#152233",
            "ink": "#EBF2FA",
            "muted": "#94A8C0",
            "accent": "#38BDF8",
            "accent_2": "#F59E0B",
            "badge_bg": "rgba(56, 189, 248, 0.14)",
            "badge_ink": "#7DD3FC",
            "border": "rgba(148, 168, 192, 0.22)",
        },
        "geometry": {"radius": "2px", "border_width": "1px", "shadow": "none", "top_stripe": True, "uppercase_display": False, "dark": True, "brutalist": False, "grid_bg": True},
        "compositions": {
            "slide_1": "split_composition",
            "slide_2": "journey_strip",
            "slide_3": "device_free_screenshot",
            "slide_4": "annotated_interface",
        },
        "direction_summary": "Visual blueprint teknis bergrid presisi dengan monospace callout yang menonjolkan keandalan sistem dan alur fungsional.",
    },
    "product_first": {
        "label": "Photo-led / Product-first",
        "secondary_default": "Editorial & Magazine",
        "storytelling_default": "product_reveal",
        "closing_label": "A closer look",
        "industries": ("furniture", "keramik", "skincare", "retail", "store", "produk", "resto", "bistro"),
        "fonts_url": "https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600&family=JetBrains+Mono:wght@400;500&family=Playfair+Display:ital,wght@0,500;0,600;1,500&display=swap",
        "font_display": "'Playfair Display', Georgia, serif",
        "font_body": "'DM Sans', sans-serif",
        "font_mono": "'JetBrains Mono', monospace",
        "palette": {
            "bg": "#F8F1E7",
            "surface": "#EFE3D3",
            "ink": "#2B211B",
            "muted": "#6D5B4F",
            "accent": "#9A523B",
            "accent_2": "#2F5D5B",
            "badge_bg": "rgba(47, 93, 91, 0.14)",
            "badge_ink": "#2F5D5B",
            "border": "rgba(43, 33, 27, 0.14)",
        },
        "geometry": {"radius": "18px", "border_width": "1px", "shadow": "0 14px 36px rgba(43,33,27,0.08)", "top_stripe": False, "uppercase_display": False, "dark": False, "brutalist": False, "grid_bg": False},
        "compositions": {
            "slide_1": "full_bleed_hero",
            "slide_2": "photo_interface",
            "slide_3": "browser_window",
            "slide_4": "ui_closeup",
        },
        "direction_summary": "Fokus penuh pada tampilan produk dan katalog digital dengan palet hangat yang tidak bersaing dengan visual utama website.",
    },
    "data_infographic": {
        "label": "Data / Infographic-led",
        "secondary_default": "Digital Product / UI Showcase",
        "storytelling_default": "proof_trust_led",
        "closing_label": "A closer look",
        "industries": ("analytics", "finance", "research", "clinic", "hospital", "operasional", "booking"),
        "fonts_url": "https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=Inter:wght@400;500;600;700&family=Space+Grotesk:wght@600;700&display=swap",
        "font_display": "'Space Grotesk', sans-serif",
        "font_body": "'Inter', sans-serif",
        "font_mono": "'IBM Plex Mono', monospace",
        "palette": {
            "bg": "#FFFFFF",
            "surface": "#F4F6F8",
            "ink": "#0E1116",
            "muted": "#525B6B",
            "accent": "#1546A0",
            "accent_2": "#0F766E",
            "badge_bg": "#E8EFFB",
            "badge_ink": "#1546A0",
            "border": "#DCE2EA",
        },
        "geometry": {"radius": "8px", "border_width": "1px", "shadow": "none", "top_stripe": True, "uppercase_display": False, "dark": False, "brutalist": False, "grid_bg": False},
        "compositions": {
            "slide_1": "split_composition",
            "slide_2": "journey_strip",
            "slide_3": "device_free_screenshot",
            "slide_4": "annotated_interface",
        },
        "direction_summary": "Struktur informatif berbasis fakta nyata dan alur pengguna yang mudah dipindai, didukung bukti tangkapan layar asli tanpa angka karangan.",
    },
    "hybrid_art_directed": {
        "label": "Hybrid / Art-directed Mix",
        "secondary_default": "Editorial + Bold Typography",
        "storytelling_default": "behind_the_design",
        "closing_label": "Designed around the brand",
        "industries": ("brand", "hybrid", "flagship", "concept", "custom"),
        "fonts_url": "https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&family=JetBrains+Mono:wght@400;500&family=Space+Grotesk:wght@500;600;700&display=swap",
        "font_display": "'Instrument Serif', Georgia, serif",
        "font_body": "'Space Grotesk', sans-serif",
        "font_mono": "'JetBrains Mono', monospace",
        "palette": {
            "bg": "#F4F1EA",
            "surface": "#E9E4D8",
            "ink": "#171716",
            "muted": "#5E5A52",
            "accent": "#2E4A3E",
            "accent_2": "#B45309",
            "badge_bg": "rgba(46, 74, 62, 0.14)",
            "badge_ink": "#2E4A3E",
            "border": "rgba(23, 23, 22, 0.18)",
        },
        "geometry": {"radius": "4px", "border_width": "1.5px", "shadow": "none", "top_stripe": True, "uppercase_display": False, "dark": False, "brutalist": False, "grid_bg": False},
        "compositions": {
            "slide_1": "asymmetric_collage",
            "slide_2": "journey_strip",
            "slide_3": "overlapping_devices",
            "slide_4": "grid_showcase",
        },
        "direction_summary": "Perpaduan terarah antara editorial serif dan struktur grid tegas yang menjaga karakter khas brand sambil memaksimalkan bukti visual UI.",
    },
}


# Bridge from demo_generator.STYLE_THEMES (8 demo styles) -> 12-Style Carousel Library
DEMO_STYLE_TO_CAROUSEL_STYLE: dict[str, str] = {
    "warm_organic_hospitality": "organic_warm",
    "figcraft_sharp_grid": "swiss_minimal",
    "dark_moody_luxury": "cinematic_premium",
    "clean_swiss_minimal": "data_infographic",
    "neo_brutalist_street": "bold_brutalist",
    "vibrant_modern_cafe": "playful_pop",
    "modern_editorial": "editorial_magazine",
    "coastal_terracotta": "product_first",
}


def resolve_style_key(style_or_demo_key: str | None, industry: str = "") -> str:
    """Resolve either a 12-style key, an 8-style demo key, or auto-select from industry."""
    raw = (style_or_demo_key or "").strip().lower()
    if raw in STYLE_LIBRARY_12:
        return raw
    if raw in DEMO_STYLE_TO_CAROUSEL_STYLE:
        return DEMO_STYLE_TO_CAROUSEL_STYLE[raw]

    ind = (industry or "").lower()
    for key, spec in STYLE_LIBRARY_12.items():
        if any(tok in ind for tok in spec["industries"]):
            return key
    return "editorial_magazine"


def _rgb_to_hex(rgb: tuple[int, int, int]) -> str:
    return "#{:02X}{:02X}{:02X}".format(*rgb)


def _luminance(rgb: tuple[int, int, int]) -> float:
    r, g, b = [c / 255.0 for c in rgb]
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _saturation(rgb: tuple[int, int, int]) -> float:
    mx, mn = max(rgb), min(rgb)
    return 0.0 if mx == 0 else (mx - mn) / float(mx)


def extract_palette_from_image(image_path: str | Path, num_colors: int = 6) -> dict[str, str] | None:
    """Extract a usable palette (bg, surface, ink, accent, accent_2) from a local reference image or logo."""
    p = Path(image_path)
    if not p.exists():
        return None

    with Image.open(p) as im:
        rgb_img = im.convert("RGB")
        rgb_img.thumbnail((160, 160))
        quant = rgb_img.quantize(colors=max(6, num_colors), method=Image.Quantize.MEDIANCUT)
        raw_pal = quant.getpalette() or []
        counts = sorted(quant.getcolors() or [], reverse=True)

    swatches: list[tuple[int, int, int]] = []
    for _, idx in counts:
        base = idx * 3
        if base + 2 < len(raw_pal):
            swatches.append((raw_pal[base], raw_pal[base + 1], raw_pal[base + 2]))

    if not swatches:
        return None

    dominant = swatches[0]
    dark_mode = _luminance(dominant) < 0.35

    # Pick accent as highest saturation color with decent readability
    accents = sorted(swatches, key=lambda c: (_saturation(c), abs(_luminance(c) - _luminance(dominant))), reverse=True)
    accent_rgb = accents[0]
    accent2_rgb = accents[1] if len(accents) > 1 else accent_rgb

    if dark_mode:
        bg_hex = _rgb_to_hex(dominant)
        surface_rgb = tuple(min(255, c + 16) for c in dominant)
        ink_hex = "#F4F1EA"
        muted_hex = "#A8A39A"
        border_hex = "rgba(244, 241, 234, 0.16)"
    else:
        bg_rgb = tuple(min(255, int(c * 0.18 + 248 * 0.82)) for c in dominant)
        surface_rgb = tuple(min(255, int(c * 0.08 + 255 * 0.92)) for c in dominant)
        bg_hex = _rgb_to_hex(bg_rgb)
        ink_hex = "#1A1A18"
        muted_hex = "#5D5A54"
        border_hex = "rgba(26, 26, 24, 0.14)"

    return {
        "bg": bg_hex,
        "surface": _rgb_to_hex(surface_rgb),
        "ink": ink_hex,
        "muted": muted_hex,
        "accent": _rgb_to_hex(accent_rgb),
        "accent_2": _rgb_to_hex(accent2_rgb),
        "badge_bg": f"{_rgb_to_hex(accent_rgb)}22",
        "badge_ink": ink_hex if dark_mode else _rgb_to_hex(accent_rgb),
        "border": border_hex,
        "extracted_from": str(p.name),
    }


def list_12_styles() -> list[dict[str, Any]]:
    return [
        {
            "key": k,
            "label": v["label"],
            "secondary_default": v["secondary_default"],
            "storytelling_default": STORYTELLING_METHODS[v["storytelling_default"]]["label"],
            "compositions": v["compositions"],
        }
        for k, v in STYLE_LIBRARY_12.items()
    ]
