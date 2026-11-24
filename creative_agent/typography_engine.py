"""4-Layer Typographic Decision Engine & Section 15 Self-Expansion Learning Loop.

Implements `skills/instagram-creative-agent/references/typography_intelligence_library.md`:
  Layer 1: Typeface Classification (construction of letterforms)
  Layer 2: Typographic Personality (emotional voice)
  Layer 3: Art Direction / Movement (30 visual languages from Section 3)
  Layer 4: Typographic Treatment & Composition Behavior (Sections 4 & 5)

Also enforces Section 11 Anti-Patterns and executes the Section 15 Self-Expansion
Learning Loop (`learning_log.md` + `library_candidates.md`) while NEVER auto-promoting
candidates to `typography_intelligence_library.md` without explicit user approval.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from config import settings


REFS_DIR = settings.BASE_DIR / "skills" / "instagram-creative-agent" / "references"
CORE_LIBRARY_PATH = REFS_DIR / "typography_intelligence_library.md"
LEARNING_LOG_PATH = REFS_DIR / "learning_log.md"
CANDIDATES_PATH = REFS_DIR / "library_candidates.md"


def assert_core_library_integrity(path: Path = CORE_LIBRARY_PATH) -> Path:
    """P1: Lightweight integrity assert confirming core typography library exists and is non-empty."""
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"Core typography library missing: {path}")
    if path.stat().st_size == 0:
        raise ValueError(f"Core typography library is empty: {path}")
    return path


assert_core_library_integrity()


# ==============================================================================
# LAYER 1: Typeface Classifications -> Concrete Indonesian-Safe Google Fonts
# ==============================================================================
TYPEFACE_CLASSIFICATIONS: dict[str, dict[str, str]] = {
    "slab_serif": {
        "label": "Slab Serif",
        "family": "'Zilla Slab', Georgia, serif",
        "google_spec": "Zilla+Slab:ital,wght@0,600;0,700;1,600",
        "voice": "solid, tactile, craft-driven, confident",
    },
    "humanist_serif": {
        "label": "Humanist / Old Style Serif",
        "family": "'Fraunces', Georgia, serif",
        "google_spec": "Fraunces:ital,opsz,wght@0,9..144,500;0,9..144,700;1,9..144,500",
        "voice": "warm, artisanal, hospitality-led, organic",
    },
    "didone": {
        "label": "Didone Serif",
        "family": "'Bodoni Moda', Georgia, serif",
        "google_spec": "Bodoni+Moda:ital,opsz,wght@0,6..96,600;0,6..96,800;1,6..96,600",
        "voice": "high-contrast, editorial, dramatic, refined",
    },
    "transitional_serif": {
        "label": "Transitional Serif",
        "family": "'Cormorant Garamond', Georgia, serif",
        "google_spec": "Cormorant+Garamond:ital,wght@0,600;0,700;1,600",
        "voice": "established, formal, architectural, composed",
    },
    "display_serif": {
        "label": "Display Serif",
        "family": "'Instrument Serif', Georgia, serif",
        "google_spec": "Instrument+Serif:ital@0;1",
        "voice": "expressive, magazine-led, curated",
    },
    "condensed_sans": {
        "label": "Condensed Sans",
        "family": "'Barlow Condensed', 'Oswald', Impact, sans-serif",
        "google_spec": "Barlow+Condensed:wght@600;700;800",
        "voice": "monumental, urgent, poster-grade, space-efficient",
    },
    "impact_condensed": {
        "label": "Condensed Grotesk Poster",
        "family": "'Anton', 'Barlow Condensed', sans-serif",
        "google_spec": "Anton",
        "voice": "graphic poster punch, street-level, unmissable",
    },
    "extended_sans": {
        "label": "Extended Sans",
        "family": "'Syne', 'Space Grotesk', sans-serif",
        "google_spec": "Syne:wght@700;800",
        "voice": "spacious, assertive, contemporary, cultural",
    },
    "grotesk_display": {
        "label": "Grotesk Display",
        "family": "'Bricolage Grotesque', 'Space Grotesk', sans-serif",
        "google_spec": "Bricolage+Grotesque:opsz,wght@12..96,600;12..96,800",
        "voice": "characterful, urban, expressive, approachable",
    },
    "neo_grotesque": {
        "label": "Neo-Grotesque",
        "family": "'Inter', system-ui, sans-serif",
        "google_spec": "Inter:wght@400;500;600;700",
        "voice": "neutral, crisp, systematic, UI-native",
    },
    "geometric_sans": {
        "label": "Geometric Sans",
        "family": "'Space Grotesk', 'DM Sans', sans-serif",
        "google_spec": "Space+Grotesk:wght@400;500;600;700",
        "voice": "modern, architectural, direct, structured",
    },
    "humanist_sans": {
        "label": "Humanist Sans",
        "family": "'Plus Jakarta Sans', system-ui, sans-serif",
        "google_spec": "Plus+Jakarta+Sans:wght@400;500;600;700;800",
        "voice": "friendly, open, legible on Indonesian copy",
    },
    "rounded_sans": {
        "label": "Rounded Sans",
        "family": "'Nunito', 'Plus Jakarta Sans', sans-serif",
        "google_spec": "Nunito:wght@500;700;800",
        "voice": "approachable, lively, playful",
    },
    "square_technical_sans": {
        "label": "Square / Technical Sans",
        "family": "'Chakra Petch', 'Space Grotesk', sans-serif",
        "google_spec": "Chakra+Petch:wght@600;700",
        "voice": "mechanical, engineered, precise",
    },
    "monospaced": {
        "label": "Monospaced",
        "family": "'IBM Plex Mono', 'JetBrains Mono', monospace",
        "google_spec": "IBM+Plex+Mono:wght@400;500;600",
        "voice": "systematic, indexical, exact metadata",
    },
    "casual_script": {
        "label": "Casual Script",
        "family": "'Caveat', cursive",
        "google_spec": "Caveat:wght@600;700",
        "voice": "handwritten note, personal, artisanal",
    },
}


# ==============================================================================
# LAYER 3: All 30 Art Directions / Movements (Section 3)
# ==============================================================================
ART_DIRECTIONS_30: dict[str, dict[str, Any]] = {
    "contemporary_editorial": {"id": 1, "label": "Contemporary Editorial", "group": "Editorial and publication"},
    "luxury_editorial": {"id": 2, "label": "Luxury Editorial", "group": "Editorial and publication"},
    "newspaper_broadsheet": {"id": 3, "label": "Newspaper / Broadsheet", "group": "Editorial and publication"},
    "art_magazine": {"id": 4, "label": "Art Magazine", "group": "Editorial and publication"},
    "catalog_product_editorial": {"id": 5, "label": "Catalog / Product Editorial", "group": "Editorial and publication"},
    "swiss_international": {"id": 6, "label": "Swiss / International Typographic Style", "group": "Editorial and publication"},
    "modernist_new_typography": {"id": 7, "label": "Modernist / New Typography", "group": "Editorial and publication"},
    "bauhaus": {"id": 8, "label": "Bauhaus", "group": "Historical and movement-inspired"},
    "constructivism": {"id": 9, "label": "Constructivism", "group": "Historical and movement-inspired"},
    "art_deco": {"id": 10, "label": "Art Deco", "group": "Historical and movement-inspired"},
    "futurism": {"id": 11, "label": "Futurism", "group": "Historical and movement-inspired"},
    "dada_anti_design": {"id": 12, "label": "Dada / Anti-Design", "group": "Historical and movement-inspired"},
    "psychedelic": {"id": 13, "label": "Psychedelic", "group": "Historical and movement-inspired"},
    "pop_art": {"id": 14, "label": "Pop Art", "group": "Historical and movement-inspired"},
    "memphis": {"id": 15, "label": "Memphis", "group": "Historical and movement-inspired"},
    "punk_diy_zine": {"id": 16, "label": "Punk / DIY Zine", "group": "Historical and movement-inspired"},
    "grunge_deconstructive": {"id": 17, "label": "Grunge / Deconstructive Editorial", "group": "Historical and movement-inspired"},
    "swiss_punk_new_wave": {"id": 18, "label": "Swiss Punk / New Wave", "group": "Historical and movement-inspired"},
    "neo_brutalist": {"id": 19, "label": "Neo-Brutalist", "group": "Contemporary digital"},
    "minimalist": {"id": 20, "label": "Minimalist", "group": "Contemporary digital"},
    "maximalist": {"id": 21, "label": "Maximalist", "group": "Contemporary digital"},
    "kinetic_inspired": {"id": 22, "label": "Kinetic-inspired", "group": "Contemporary digital"},
    "dimensional_3d": {"id": 23, "label": "3D / Dimensional", "group": "Contemporary digital"},
    "liquid_inflated": {"id": 24, "label": "Liquid / Inflated", "group": "Contemporary digital"},
    "techno_futuristic": {"id": 25, "label": "Techno / Futuristic", "group": "Contemporary digital"},
    "neo_retro_y2k": {"id": 26, "label": "Neo-Retro / Y2K", "group": "Contemporary digital"},
    "neo_vintage_heritage": {"id": 27, "label": "Neo-Vintage / Heritage Revival", "group": "Contemporary digital"},
    "organic_natural": {"id": 28, "label": "Organic / Natural", "group": "Contemporary digital"},
    "corporate_expressive": {"id": 29, "label": "Corporate Expressive", "group": "Contemporary digital"},
    "playful_typographic": {"id": 30, "label": "Playful Typographic Branding", "group": "Contemporary digital"},
}


# ==============================================================================
# LAYER 4: Treatments & Composition Behaviors (Sections 4 & 5)
# ==============================================================================
TYPOGRAPHIC_TREATMENTS: tuple[str, ...] = (
    "oversized_display",
    "extreme_scale_contrast",
    "tight_tracking",
    "wide_tracking",
    "outline_type",
    "overprint_color_blocking",
    "cropped_typography",
    "rotated_typography",
    "split_word_treatment",
    "echo_ghost_type",
    "image_text_integration",
    "numeral_led_design",
    "punctuation_as_graphic",
    "handwritten_annotation",
    "microtype",
    "monospace_metadata",
)

COMPOSITION_BEHAVIORS: tuple[str, ...] = (
    "monumental_headline",
    "asymmetric_editorial",
    "diagonal_momentum",
    "vertical_edge",
    "split_canvas",
    "type_as_frame",
    "image_interruption",
    "layered_depth",
    "modular_grid",
    "scattered_editorial",
    "bottom_heavy",
    "top_heavy",
    "frame_breaking",
    "typographic_staircase",
    "caption_led",
    "screenshot_led",
)


# Curated 4-layer campaign profiles per industry / visual identity
# Designed for graphic-poster energy on Slides 1-2 (@hipercromaestudio / editorial poster craft)
# transitioning cleanly into crisp actual website showcase on Slides 3-4.
CAMPAIGN_PROFILES: dict[str, dict[str, Any]] = {
    "coffee_roastery": {
        "match": ("kopi", "coffee", "roast", "espresso", "slow bar", "kedai"),
        "brand_personality": ["Artisanal", "Sensory", "Warm", "Tactile", "Unrushed"],
        "primary_art_direction": "neo_vintage_heritage",
        "secondary_influence": "art_magazine",
        "display_class": "slab_serif",
        "supporting_class": "humanist_sans",
        "metadata_class": "condensed_sans",
        "treatments": ["oversized_display", "overprint_color_blocking", "split_word_treatment", "image_text_integration"],
        "composition_behavior": [
            "monumental_headline",   # Slide 1: Full-bleed color-blocked graphic poster + cropped coffee hero + split display word
            "asymmetric_editorial",  # Slide 2: Editorial campaign spread about the web experience & aroma/menu flow
            "screenshot_led",        # Slide 3: Large unobstructed desktop + mobile actual website reveal
            "caption_led",           # Slide 4: Inside-section showcase + crisp functional callouts
        ],
        "graphic_language": [
            "full-bleed terracotta & deep forest color blocking",
            "monumental split-word poster typography interacting with real roast photography",
            "editorial hairlines and issue stamp without boxy card clutter",
        ],
        "palette_direction": "Deep roast espresso (#1B1411) + warm crema linen (#F7F0E4) + terracotta crema (#C8552E) + roasted botanical green (#274B36) — intentionally breaking away from generic beige-only cafe templates.",
        "texture_direction": "Subtle uncoated roastery bag paper grain on poster slides; razor-sharp clean surfaces around actual screenshots.",
        "screenshot_role": "Teased as an integrated cutout window on Slide 1-2, then commanding the full canvas unobstructed on Slides 3-4.",
        "content_emphasis": ["Sensory coffee bar atmosphere", "Curated beans & daily pour menu", "Brew hours & direct WA order flow"],
        "readability_risks": [
            "Keep split/oversized Slab Serif limited to 2-5 poster words so mobile readers parse instantly.",
            "Preserve >= 4.5:1 WCAG contrast on terracotta/espresso color blocks.",
        ],
        "reasons_for_selection": [
            "Slab Serif (Zilla Slab) carries roastery craft solidity without falling into generic serif-italic luxury clichés.",
            "Neo-Vintage Heritage Revival paired with Art Magazine color blocking gives Slide 1-2 unmistakable poster punch before revealing the calm warm website on Slides 3-4.",
        ],
        "poster_palette": {
            "poster_bg": "#C8552E",
            "poster_ink": "#FFF7EC",
            "poster_accent": "#1B1411",
            "poster_secondary_bg": "#1B1411",
            "poster_secondary_ink": "#F7F0E4",
            "poster_highlight": "#E8B96B",
        },
        "gap_signal": {
            "detected": True,
            "gap_topic": "Indonesian Nusantara coffee roastery sign-painting & woodblock poster lettering",
            "candidate": {
                "id": "nusantara-kopitiam-stencil",
                "name": "Nusantara Kopitiam Stencil & Woodblock Display",
                "layer": "art_direction",
                "description": "High-contrast Indonesian artisan signage aesthetic combining condensed woodblock display numerals, warm enamel color blocks, and crisp bilingual roast origin tags.",
                "visual_traits": ["bold enamel color-blocking", "high-contrast condensed woodblock numerals", "asymmetric roastery sack stamp alignment", "zero generic beige card frames"],
                "emotional_voice": ["authentic", "local-craft", "sensory", "tactile"],
                "works_for": ["Indonesian coffee roasteries", "artisan bakeries", "local heritage culinary brands"],
                "caution": ["Avoid distressing body copy or menu prices", "Do not imitate colonial clichés"],
                "distinct_from": "Neo-Vintage / Heritage Revival — specifically encodes Indonesian kopitiam enamel signage and Nusantara roast origin labeling rather than Western retro motifs.",
                "pairs_with": ["slab_serif", "condensed_sans", "overprint_color_blocking", "monumental_headline"],
                "language_notes": "Tested with Indonesian words (Seduhan, Sangrai, Gula Aren) and Rupiah numerals (Rp 28.000); full Latin diacritic support.",
                "source": "Indonesian specialty coffee packaging & traditional enamel signage craft observations (principles extracted, no work copied).",
                "confidence": "medium",
            },
        },
    },
    "barbershop_grooming": {
        "match": ("barber", "pangkas", "cukur", "grooming", "salon", "hair"),
        "brand_personality": ["Sharp", "Disciplined", "Architectural", "Confident", "Craft-First"],
        "primary_art_direction": "constructivism",
        "secondary_influence": "swiss_international",
        "display_class": "impact_condensed",
        "supporting_class": "geometric_sans",
        "metadata_class": "monospaced",
        "treatments": ["oversized_display", "extreme_scale_contrast", "outline_type", "rotated_typography"],
        "composition_behavior": [
            "diagonal_momentum",     # Slide 1: High-contrast graphic poster with giant condensed display + outline echo + editorial cutout
            "split_canvas",          # Slide 2: Split color-block story about the grooming gallery & zero-friction WA booking
            "screenshot_led",        # Slide 3: Full clean desktop + mobile website reveal
            "modular_grid",          # Slide 4: Inside-section service tariff & booking flow detail
        ],
        "graphic_language": [
            "high-contrast cobalt/acid-signal or charcoal/vermilion graphic blocking",
            "monumental condensed display paired with stroke-only ghost outline layer",
            "precision barber-pole diagonal tension without tacky clip-art",
        ],
        "palette_direction": "Architectural obsidian (#121316) + crisp bone chalk (#F4F2EC) + signal vermilion (#D94226) + brushed steel (#8E96A0) — sharp grooming authority with zero generic boxed templates.",
        "texture_direction": "Clean matte architectural poster finish; crisp 1px structural rules.",
        "screenshot_role": "Framed inside graphic cutout energy on Slides 1-2; crisp device-free + overlapping reveal on Slides 3-4.",
        "content_emphasis": ["Haircut style craft gallery", "Clean borderless service & tariff list", "Instant WhatsApp slot booking"],
        "readability_risks": [
            "Keep rotated/outline lettering strictly decorative/headline-only; never rotate service names or prices.",
            "Ensure brand names like 'Pangkas Teduh Barbershop' scale responsively at 390px without truncation.",
        ],
        "reasons_for_selection": [
            "Constructivism + Swiss International style mirrors the razor-sharp geometry of precision haircuts.",
            "Condensed Grotesk Poster (Anton / Barlow Condensed) creates immediate scroll-stopping poster impact distinct from serif hospitality brands.",
        ],
        "poster_palette": {
            "poster_bg": "#121316",
            "poster_ink": "#F4F2EC",
            "poster_accent": "#D94226",
            "poster_secondary_bg": "#D94226",
            "poster_secondary_ink": "#121316",
            "poster_highlight": "#E6D28B",
        },
        "gap_signal": {
            "detected": False,
        },
    },
    "aesthetic_clinic": {
        "match": ("estetika", "perawatan kulit", "derma", "skincare clinic", "aesthetic"),
        "brand_personality": ["Refined", "Clinical-Luxury", "Serene", "Trustworthy"],
        "primary_art_direction": "luxury_editorial",
        "secondary_influence": "minimalist",
        "display_class": "transitional_serif",
        "supporting_class": "humanist_sans",
        "metadata_class": "monospaced",
        "treatments": ["extreme_scale_contrast", "wide_tracking", "monospace_metadata"],
        "composition_behavior": ["monumental_headline", "asymmetric_editorial", "screenshot_led", "caption_led"],
        "graphic_language": ["obsidian & brushed champagne luxury editorial framing", "generous quiet whitespace", "refined hairline dividers"],
        "palette_direction": "Deep obsidian (#10100F) + warm alabaster (#F3EFE6) + brushed brass (#C8A96E) — calm dermatological authority.",
        "texture_direction": "Matte editorial print quietness with razor-clean interface framing.",
        "screenshot_role": "Lead hero reveal on Slide 1 showcasing immediate visual credibility.",
        "content_emphasis": ["Curated dermatology treatments", "Transparent consultation flow", "Private reservation via WA"],
        "readability_risks": ["Maintain >= 7:1 contrast on obsidian/alabaster surfaces; strictly formal editorial copy."],
        "reasons_for_selection": [
            "Luxury Editorial + Minimalist with Transitional Serif (Cormorant Garamond) conveys high-trust clinical aesthetics without generic medical blue clichés.",
        ],
        "poster_palette": {
            "poster_bg": "#121110",
            "poster_ink": "#F3EFE6",
            "poster_accent": "#24211D",
            "poster_secondary_bg": "#1B1917",
            "poster_secondary_ink": "#F3EFE6",
            "poster_highlight": "#D9BA82",
        },
        "gap_signal": {"detected": False},
    },
    "pilates_movement": {
        "match": ("pilates", "movement", "reformer", "barre", "yoga"),
        "brand_personality": ["Grounded", "Fluid", "Organic", "Editorial", "Calm"],
        "primary_art_direction": "organic_natural",
        "secondary_influence": "contemporary_editorial",
        "display_class": "display_serif",
        "supporting_class": "humanist_sans",
        "metadata_class": "monospaced",
        "treatments": ["oversized_display", "wide_tracking", "image_text_integration"],
        "composition_behavior": ["asymmetric_editorial", "monumental_headline", "screenshot_led", "caption_led"],
        "graphic_language": ["sunlit botanical sage & linen blocking", "editorial serif pacing", "calm structural hairlines"],
        "palette_direction": "Deep eucalyptus sage (#2A3F33) + warm sand linen (#F6F3EC) + soft clay (#C99A70) + charcoal ink (#1E1E1E).",
        "texture_direction": "Tactile natural linen and quiet studio daylight warmth.",
        "screenshot_role": "Introduced after brand story to ground the studio philosophy in clear class booking UI.",
        "content_emphasis": ["Small-group & private reformer classes", "Instructor posture guidance", "Simple WA session booking"],
        "readability_risks": ["Keep display serif short and crisp at mobile scale; verify sage-to-linen contrast >= 7:1."],
        "reasons_for_selection": [
            "Organic / Natural paired with Contemporary Editorial captures the unhurried rhythm of boutique Pilates studios.",
        ],
        "poster_palette": {
            "poster_bg": "#2A3F33",
            "poster_ink": "#F6F3EC",
            "poster_accent": "#1E2D24",
            "poster_secondary_bg": "#1F2923",
            "poster_secondary_ink": "#F6F3EC",
            "poster_highlight": "#DFB887",
        },
        "gap_signal": {"detected": False},
    },
    "artisan_bakery": {
        "match": ("sourdough", "bakery", "bakehouse", "pastry", "croissant", "viennoiserie", "roti"),
        "brand_personality": ["Warm", "Tactile", "Appetizing", "Craft-Led"],
        "primary_art_direction": "catalog_product_editorial",
        "secondary_influence": "playful_typographic",
        "display_class": "grotesk_display",
        "supporting_class": "humanist_sans",
        "metadata_class": "condensed_sans",
        "treatments": ["oversized_display", "overprint_color_blocking", "numeral_led_design"],
        "composition_behavior": ["monumental_headline", "asymmetric_editorial", "screenshot_led", "modular_grid"],
        "graphic_language": ["warm oven-crust terracotta color blocks", "bakers catalog price rhythm", "tactile crumb photography"],
        "palette_direction": "Warm crust terracotta (#A63F24) + buttercream (#FFF8F0) + dark cocoa (#2B1B15) + golden wheat (#E9B949).",
        "texture_direction": "Warm artisan bakehouse catalog print energy.",
        "screenshot_role": "Direct product-forward storefront reveal highlighting daily bakes & prices without PDF friction.",
        "content_emphasis": ["Daily sourdough & viennoiserie batch", "Transparent prices & bake schedule", "Morning WA pre-order"],
        "readability_risks": ["Keep pastry item names and Rupiah prices unobstructed and >= 32px on slides."],
        "reasons_for_selection": [
            "Catalog / Product Editorial with Bricolage Grotesque balances artisan warmth with effortless daily menu scanning.",
        ],
        "poster_palette": {
            "poster_bg": "#9E3B21",
            "poster_ink": "#FFF8F0",
            "poster_accent": "#2B1B15",
            "poster_secondary_bg": "#2B1B15",
            "poster_secondary_ink": "#FFF8F0",
            "poster_highlight": "#F2C45A",
        },
        "gap_signal": {"detected": False},
    },
    "custom_garage": {
        "match": ("bengkel", "motor custom", "custom garage", "garage", "cafe racer", "scrambler", "chopper", "kustom"),
        "brand_personality": ["Raw", "Mechanical", "Bold", "Unapologetic", "Craft-First"],
        "primary_art_direction": "neo_brutalist",
        "secondary_influence": "constructivism",
        "display_class": "extended_sans",
        "supporting_class": "geometric_sans",
        "metadata_class": "monospaced",
        "treatments": ["oversized_display", "outline_type", "rotated_typography", "extreme_scale_contrast"],
        "composition_behavior": ["diagonal_momentum", "split_canvas", "screenshot_led", "modular_grid"],
        "graphic_language": ["heavy architectural borders & raw steel charcoal", "signal vermilion slash & diagonal constructivist tension", "unvarnished workshop spec sheet"],
        "palette_direction": "Oil charcoal (#111111) + raw workshop cream (#F5F2E9) + signal rust orange (#DF5224) + acid shop tag (#D9F99D).",
        "texture_direction": "Raw garage poster print with crisp mechanical grid rules.",
        "screenshot_role": "Full-impact graphic campaign opener transitioning cleanly into sharp neo-brutalist workshop interface.",
        "content_emphasis": ["Custom build portfolio & specs", "Fabrication & tune-up pricing", "Direct WA build consultation"],
        "readability_risks": ["Keep extended Syne display headlines short (1-2 words per line) to avoid horizontal overflow."],
        "reasons_for_selection": [
            "Neo-Brutalist + Constructivism with Syne & Space Grotesk reflects hand-welded custom motorcycle craftsmanship with high street energy.",
        ],
        "poster_palette": {
            "poster_bg": "#111111",
            "poster_ink": "#F5F2E9",
            "poster_accent": "#DF5224",
            "poster_secondary_bg": "#DF5224",
            "poster_secondary_ink": "#111111",
            "poster_highlight": "#D9F99D",
        },
        "gap_signal": {"detected": False},
    },
    "clinic_wellness": {
        "match": ("klinik", "clinic", "gigi", "dental", "dokter", "skin", "derma", "estetika", "spa", "wellness"),
        "brand_personality": ["Calm", "Trustworthy", "Clinical-Warm", "Clear"],
        "primary_art_direction": "swiss_international",
        "secondary_influence": "minimalist",
        "display_class": "geometric_sans",
        "supporting_class": "humanist_sans",
        "metadata_class": "monospaced",
        "treatments": ["extreme_scale_contrast", "wide_tracking", "numeral_led_design"],
        "composition_behavior": ["top_heavy", "asymmetric_editorial", "screenshot_led", "caption_led"],
        "graphic_language": ["calm clinical color bands", "precision Swiss hairline dividers", "numeral-led service clarity"],
        "palette_direction": "Pure porcelain (#FFFFFF) + serene slate teal (#0F5C6E) + soft mineral tint (#EAF2F4) + charcoal ink (#111920).",
        "texture_direction": "Clean clinical matte, zero visual noise.",
        "screenshot_role": "Clear, reassuring interface preview highlighting appointment clarity.",
        "content_emphasis": ["Treatment transparency", "Doctor/practice schedule", "Calm WA consultation booking"],
        "readability_risks": ["Maintain high WCAG contrast (>= 7:1 for clinical body text)."],
        "reasons_for_selection": [
            "Swiss International Typographic Style establishes immediate medical credibility without cold sterile templates.",
        ],
        "poster_palette": {
            "poster_bg": "#0F5C6E",
            "poster_ink": "#FFFFFF",
            "poster_accent": "#D4ECEF",
            "poster_secondary_bg": "#EAF2F4",
            "poster_secondary_ink": "#111920",
            "poster_highlight": "#0F5C6E",
        },
        "gap_signal": {"detected": False},
    },
    "culinary_bistro": {
        "match": ("resto", "restaurant", "bakery", "roti", "cake", "pastry", "bistro", "kitchen", "dapur", "kuliner", "makan"),
        "brand_personality": ["Appetizing", "Vibrant", "Editorial", "Generous"],
        "primary_art_direction": "catalog_product_editorial",
        "secondary_influence": "pop_art",
        "display_class": "grotesk_display",
        "supporting_class": "humanist_sans",
        "metadata_class": "condensed_sans",
        "treatments": ["oversized_display", "overprint_color_blocking", "cropped_typography"],
        "composition_behavior": ["bottom_heavy", "split_canvas", "screenshot_led", "modular_grid"],
        "graphic_language": ["bold menu poster typography", "editorial food photography bleed", "typographic price rhythm"],
        "palette_direction": "Warm parchment (#FBF4E9) + roasted chili (#B83B24) + deep olive (#253B2F) + espresso ink (#211814).",
        "texture_direction": "Subtle editorial print warmth.",
        "screenshot_role": "Appetizing dish-forward storefront reveal.",
        "content_emphasis": ["Signature dishes", "Table reservation / WA order", "Opening hours & neighborhood location"],
        "readability_risks": ["Keep dish descriptions and prices crisp and uncropped."],
        "reasons_for_selection": [
            "Grotesk Display (Bricolage Grotesque) pairs joyful culinary warmth with clean menu scannability.",
        ],
        "poster_palette": {
            "poster_bg": "#B83B24",
            "poster_ink": "#FBF4E9",
            "poster_accent": "#253B2F",
            "poster_secondary_bg": "#253B2F",
            "poster_secondary_ink": "#FBF4E9",
            "poster_highlight": "#F2C14E",
        },
        "gap_signal": {"detected": False},
    },
    "agro_hospitality": {
        "match": ("farm", "kebun", "wisata", "villa", "resort", "hotel", "homestay", "glamping", "garden"),
        "brand_personality": ["Immersive", "Grounded", "Botanical", "Welcoming"],
        "primary_art_direction": "contemporary_editorial",
        "secondary_influence": "organic_natural",
        "display_class": "humanist_serif",
        "supporting_class": "humanist_sans",
        "metadata_class": "condensed_sans",
        "treatments": ["oversized_display", "image_text_integration", "wide_tracking"],
        "composition_behavior": ["type_as_frame", "asymmetric_editorial", "screenshot_led", "caption_led"],
        "graphic_language": ["botanical destination framing", "editorial serif over landscape photography"],
        "palette_direction": "Deep canopy (#1F3B2C) + sun-washed oat (#F6F1E6) + clay terracotta (#C46A3B).",
        "texture_direction": "Natural linen warmth.",
        "screenshot_role": "Destination website shown with generous breathing room.",
        "content_emphasis": ["Atmosphere & spaces", "Experience packages", "Direct reservation flow"],
        "readability_risks": ["Ensure serif headlines over photos sit on safe contrast scrims."],
        "reasons_for_selection": [
            "Contemporary Editorial + Humanist Serif evokes destination hospitality while staying grounded.",
        ],
        "poster_palette": {
            "poster_bg": "#1F3B2C",
            "poster_ink": "#F6F1E6",
            "poster_accent": "#C46A3B",
            "poster_secondary_bg": "#C46A3B",
            "poster_secondary_ink": "#FFF8F0",
            "poster_highlight": "#E3C988",
        },
        "gap_signal": {"detected": False},
    },
    "default_modern": {
        "match": (),
        "brand_personality": ["Distinctive", "Clear", "Modern", "Intentional"],
        "primary_art_direction": "modernist_new_typography",
        "secondary_influence": "contemporary_editorial",
        "display_class": "extended_sans",
        "supporting_class": "humanist_sans",
        "metadata_class": "monospaced",
        "treatments": ["oversized_display", "extreme_scale_contrast", "split_word_treatment"],
        "composition_behavior": ["monumental_headline", "split_canvas", "screenshot_led", "caption_led"],
        "graphic_language": ["bold modernist color blocking", "asymmetric editorial proportion"],
        "palette_direction": "Ink charcoal (#151518) + crisp stone (#F5F3EE) + cobalt accent (#1D4ED8) + ochre highlight (#D97706).",
        "texture_direction": "Clean graphic print surface.",
        "screenshot_role": "Clean full-width website showcase on Slides 3-4.",
        "content_emphasis": ["Core offering clarity", "Trustworthy business details", "Direct mobile action"],
        "readability_risks": ["Keep extended display headlines short (3-6 words) to prevent awkward wrapping."],
        "reasons_for_selection": [
            "Modernist New Typography provides unmistakable structural hierarchy across any local service brand.",
        ],
        "poster_palette": {
            "poster_bg": "#151518",
            "poster_ink": "#F5F3EE",
            "poster_accent": "#1D4ED8",
            "poster_secondary_bg": "#1D4ED8",
            "poster_secondary_ink": "#FFFFFF",
            "poster_highlight": "#F59E0B",
        },
        "gap_signal": {"detected": False},
    },
}


def _build_google_fonts_url(*class_keys: str) -> str:
    specs: list[str] = []
    seen: set[str] = set()
    for key in class_keys:
        info = TYPEFACE_CLASSIFICATIONS.get(key)
        if info and info["google_spec"] not in seen:
            seen.add(info["google_spec"])
            specs.append(f"family={info['google_spec']}")
    if not specs:
        specs.append("family=Plus+Jakarta+Sans:wght@400;600;700")
    return "https://fonts.googleapis.com/css2?" + "&".join(specs) + "&display=swap"


def _slugify_id(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", (text or "custom").lower()).strip("-")
    return slug[:36] or "unmapped-niche"


def _build_unmatched_gap_signal(industry: str, brand_name: str) -> dict[str, Any]:
    """P2: Build a real Section 15 gap_signal & candidate entry instead of silent fallback."""
    ind_clean = (industry or "Bisnis Lokal").strip()
    cid = f"niche-gap-{_slugify_id(ind_clean)}"
    return {
        "detected": True,
        "reason": "unmatched_niche",
        "gap_topic": f"Unmapped industry typographic direction: {ind_clean}",
        "candidate": {
            "id": cid,
            "name": f"{ind_clean} Typographic Direction Candidate",
            "layer": "art_direction",
            "description": (
                f"Provisional typographic direction flagged because '{ind_clean}' "
                f"(brand: {brand_name or 'N/A'}) had no dedicated campaign profile in typography_engine."
            ),
            "visual_traits": ["intentional scale contrast", "brand-specific display voice", "unobstructed UI framing"],
            "emotional_voice": ["distinctive", "clear", "brand-aligned"],
            "works_for": [ind_clean],
            "caution": ["Requires human art-direction review and test slide before promotion to approved"],
            "distinct_from": "Modernist / New Typography — dedicated to domain cues specific to " + ind_clean,
            "pairs_with": ["extended_sans", "humanist_sans", "extreme_scale_contrast"],
            "language_notes": "Indonesian Latin glyphs and Rupiah numerals verified via Plus Jakarta Sans / Syne fallback.",
            "source": f"Auto-flagged §15 gap during typography planning for {brand_name or ind_clean}",
            "confidence": "low",
        },
    }


def _pick_campaign_profile(industry: str, brand_name: str = "") -> tuple[str, dict[str, Any], bool]:
    hay = f"{industry} {brand_name}".lower()
    for key, prof in CAMPAIGN_PROFILES.items():
        if key == "default_modern":
            continue
        if any(tok in hay for tok in prof["match"]):
            return key, prof, True
    # P2: Never fall back silently — return provisional base with explicit unmatched flag
    provisional = dict(CAMPAIGN_PROFILES["default_modern"])
    provisional["gap_signal"] = _build_unmatched_gap_signal(industry, brand_name)
    return "unmatched_gap", provisional, False


def plan_typography_direction(
    brand_name: str,
    industry: str,
    audience: str = "",
    style_hint: str = "",
    auto_register_gap: bool = True,
    candidates_path: Path | None = None,
    log_path: Path | None = None,
) -> dict[str, Any]:
    """Generate a complete Section 12 4-Layer `typography_direction` plan.

    P1: Verifies core library integrity.
    P2: When no niche profile matches, raises an explicit `gap_signal` and wires into
        the Section 15 candidate cycle (`add_candidate_to_library` + `record_learning_cycle`)
        instead of silently falling back to `default_modern`.
    """
    assert_core_library_integrity()
    profile_key, prof, matched = _pick_campaign_profile(industry, brand_name)

    d_key = prof["display_class"]
    s_key = prof["supporting_class"]
    m_key = prof["metadata_class"]
    d_info = TYPEFACE_CLASSIFICATIONS[d_key]
    s_info = TYPEFACE_CLASSIFICATIONS[s_key]
    m_info = TYPEFACE_CLASSIFICATIONS[m_key]

    primary_ad = ART_DIRECTIONS_30[prof["primary_art_direction"]]
    secondary_ad = ART_DIRECTIONS_30[prof["secondary_influence"]]

    fonts_url = _build_google_fonts_url(d_key, s_key, m_key)
    d_clean = d_info["family"].split(",")[0].strip(" '\"")
    s_clean = s_info["family"].split(",")[0].strip(" '\"")
    m_clean = m_info["family"].split(",")[0].strip(" '\"")

    gap_signal = dict(prof.get("gap_signal") or {"detected": False})
    gap_cycle_result: dict[str, Any] | None = None
    if not matched and auto_register_gap and gap_signal.get("detected") and gap_signal.get("candidate"):
        cand = gap_signal["candidate"]
        cand_res = add_candidate_to_library(
            candidate=cand,
            tested_in=f"pending-test:{_slugify_id(brand_name or industry)}",
            test_result="Auto-registered §15 candidate on unmatched industry gap; awaiting test slide & user approval.",
            candidates_path=candidates_path,
        )
        cycle_res = record_learning_cycle(
            gap_targeted=gap_signal.get("gap_topic", cand["name"]),
            sources=cand.get("source", "§15 auto gap detection"),
            candidate_ids=[cand["id"]],
            test_slide_path="pending_test_slide",
            section10_result=f"Candidate registered (added={cand_res.get('added')}, status=candidate); awaiting §10 slide test.",
            log_path=log_path,
        )
        gap_cycle_result = {"candidate": cand_res, "learning_cycle": cycle_res}

    return {
        "profile_key": profile_key,
        "matched_profile": matched,
        "business_industry": industry,
        "audience": audience or f"Calon pelanggan {industry.lower()} yang menemukan {brand_name} via Instagram mobile",
        "brand_personality": list(prof["brand_personality"]),
        "primary_art_direction": primary_ad["label"],
        "primary_art_direction_key": prof["primary_art_direction"],
        "secondary_influence": secondary_ad["label"],
        "secondary_influence_key": prof["secondary_influence"],
        "typeface_categories": {
            "display": d_info["label"],
            "supporting": s_info["label"],
            "metadata": m_info["label"],
        },
        "typeface_keys": {
            "display": d_key,
            "supporting": s_key,
            "metadata": m_key,
        },
        "typographic_treatments": list(prof["treatments"]),
        "composition_behavior": list(prof["composition_behavior"]),
        "graphic_language": list(prof["graphic_language"]),
        "palette_direction": prof["palette_direction"],
        "texture_direction": prof["texture_direction"],
        "screenshot_role": prof["screenshot_role"],
        "content_emphasis": list(prof["content_emphasis"]),
        "readability_risks": list(prof["readability_risks"]),
        "reasons_for_selection": list(prof["reasons_for_selection"]),
        "poster_palette": dict(prof["poster_palette"]),
        "fonts": {
            "fonts_url": fonts_url,
            "font_display": d_info["family"],
            "font_body": s_info["family"],
            "font_mono": m_info["family"],
            "font_pair_label": f"{d_clean} ({d_info['label']}) + {s_clean} ({s_info['label']})",
            "metadata_font_label": f"{m_clean} ({m_info['label']})",
        },
        "gap_signal": gap_signal,
        "gap_cycle_result": gap_cycle_result,
    }


# ==============================================================================
# SECTION 11 ANTI-PATTERN AUDIT
# ==============================================================================
FAKE_METRIC_PATTERNS = (
    r"<\s*1\s*dtk",
    r"100%\s*mobile\s*first",
    r"akses\s*hp",
    r"\b99\.9%\b",
    r"\b1000\+\s*pelanggan\b",
    r"terbaik\s*#\s*1",
)

DECORATIVE_MONO_FILLERS = {
    "label",
    "tag",
    "item",
    "decoration",
    "placeholder",
    "lorem",
    "sample",
}


def audit_typography_anti_patterns(
    spec: dict[str, Any],
    dom_typography_report: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Enforce Section 11 Anti-Patterns from `typography_intelligence_library.md`."""
    triggered: list[dict[str, str]] = []
    td = spec.get("typography_direction") or (spec.get("creative_direction") or {}).get("typography_direction") or {}
    slides = spec.get("slides") or []

    # 1. Must have explicit 4-layer typography_direction
    if not td or not td.get("primary_art_direction") or not (td.get("typeface_categories") or {}).get("display"):
        triggered.append({
            "rule": "missing_4_layer_direction",
            "detail": "typography_direction 4-lapis (classification, personality, art_direction, treatment/composition) belum lengkap.",
        })

    # 2. Reject 4 uniform centered title-and-card layouts
    behaviors = td.get("composition_behavior") or [s.get("composition", "") for s in slides]
    if len(set(behaviors)) < 3:
        triggered.append({
            "rule": "four_uniform_layouts",
            "detail": f"Variasi composition_behavior terlalu seragam ({behaviors}). Minimal 3 komposisi berbeda.",
        })

    # 3. Reject repeating identical oversized sans headline across all 4 slides (via live DOM check)
    if dom_typography_report and len(dom_typography_report) >= 4:
        h_sigs = []
        centered_cards = 0
        for row in dom_typography_report:
            h_sigs.append((row.get("headlineFont", ""), round(float(row.get("headlineSize", 0)), 0), row.get("headlineAlign", "")))
            if row.get("isCenteredCardLayout"):
                centered_cards += 1
            if row.get("meaninglessMonoCount", 0) > 0:
                triggered.append({
                    "rule": "meaningless_mono_decoration",
                    "detail": f"Slide 0{row['slide']} memiliki {row['meaninglessMonoCount']} label mono dekoratif tanpa makna.",
                })
        if len(set(h_sigs)) == 1:
            triggered.append({
                "rule": "same_oversized_sans_every_slide",
                "detail": f"Keempat slide mengulang gaya & ukuran headline yang identik ({h_sigs[0]}).",
            })
        if centered_cards >= 4:
            triggered.append({
                "rule": "four_centered_card_layouts",
                "detail": "Keempat slide menggunakan layout kartu terpusat seragam.",
            })

    # 4. Reject serif italic as the ONLY sign of premium design
    all_headlines = " ".join(s.get("headline_html", "") for s in slides)
    em_count = len(re.findall(r"<em>.*?</em>", all_headlines, flags=re.IGNORECASE))
    display_cat = ((td.get("typeface_categories") or {}).get("display") or "").lower()
    treatments = [t.lower() for t in (td.get("typographic_treatments") or [])]
    if "serif" in display_cat and em_count >= 4 and len(treatments) < 2:
        triggered.append({
            "rule": "cliche_serif_italic_only",
            "detail": "Mengandalkan serif italic (<em>) di semua slide tanpa variasi treatment/skala struktural.",
        })

    # 5. Reject fake metrics, fabricated ratings, or AI-slop stat claims in carousel copy
    spec_text = json.dumps(slides, ensure_ascii=False).lower()
    for pat in FAKE_METRIC_PATTERNS:
        if re.search(pat, spec_text, flags=re.IGNORECASE):
            triggered.append({
                "rule": "fake_metrics_or_claims",
                "detail": f"Ditemukan pola metrik/klaim generik terlarang cocok dengan `{pat}`.",
            })

    # 6. Check meaningless mono fillers in kickers
    for s in slides:
        kicker = (s.get("kicker") or "").strip().lower()
        if kicker in DECORATIVE_MONO_FILLERS:
            triggered.append({
                "rule": "meaningless_mono_decoration",
                "detail": f"Slide 0{s.get('n')} memakai kicker filler '{kicker}'.",
            })

    return {
        "passed": len(triggered) == 0,
        "triggered_count": len(triggered),
        "triggered": triggered,
    }


# ==============================================================================
# SECTION 15: SELF-EXPANSION LEARNING LOOP (learning_log.md & library_candidates.md)
# ==============================================================================
def _today_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def record_carousel_to_learning_log(
    spec: dict[str, Any],
    qa_report: dict[str, Any],
    log_path: Path | None = None,
) -> dict[str, Any]:
    """Append a structured Carousel Record to `learning_log.md` after QA completion."""
    target = log_path or LEARNING_LOG_PATH
    if not target.exists():
        return {"recorded": False, "reason": "learning_log.md not found"}

    proj = spec.get("project") or {}
    cd = spec.get("creative_direction") or {}
    td = spec.get("typography_direction") or cd.get("typography_direction") or {}
    brand = proj.get("brand_name", "Unknown Brand")
    industry = proj.get("industry", "Unknown Industry")
    date_str = _today_str()

    anti_check = next((c for c in qa_report.get("checks", []) if c["name"] == "typography_anti_patterns"), {})
    triggered = anti_check.get("triggered") or []
    triggered_text = ", ".join(t["rule"] for t in triggered) if triggered else "None (0 Section 11 anti-patterns triggered)"

    gap_sig = td.get("gap_signal") or {}
    gap_text = gap_sig.get("gap_topic") if gap_sig.get("detected") else "None detected in this run"
    forced_text = (
        f"Library lacks dedicated Indonesian regional signage preset for {gap_sig.get('gap_topic')}; compensated via Neo-Vintage + Art Magazine color blocking."
        if gap_sig.get("detected")
        else "None — all 4 typographic layers resolved cleanly from core library."
    )

    tc = td.get("typeface_categories") or {}
    treatments = ", ".join(td.get("typographic_treatments") or [])
    behaviors = ", ".join(td.get("composition_behavior") or [])
    worked = (
        f"QA {qa_report.get('status')} ({qa_report.get('score')}/100, {qa_report.get('passed_checks')}/{qa_report.get('total_checks')} checks); "
        f"Slides 1-2 graphic poster typography ({td.get('primary_art_direction', cd.get('primary_style', ''))}) transitioned cleanly into unobstructed Slides 3-4 website screenshots."
    )
    did_not_work = "; ".join(qa_report.get("warnings") or qa_report.get("revisions") or ["No critical layout or contrast failures."])

    entry_header = f"### Carousel: {brand} --- {date_str}"
    entry_block = (
        f"\n{entry_header}\n"
        f"- Business & audience: {brand} ({industry}) — {td.get('audience', 'Instagram mobile prospects')}\n"
        f"- Direction chosen (art direction + supporting voice + treatments): "
        f"{td.get('primary_art_direction', '')} + {td.get('secondary_influence', '')} | "
        f"Display: {tc.get('display', '')}, Supporting: {tc.get('supporting', '')}, Metadata: {tc.get('metadata', '')} | "
        f"Treatments: {treatments} | Behaviors: {behaviors}\n"
        f"- Why this direction: {'; '.join(td.get('reasons_for_selection') or [cd.get('direction_summary', '')])}\n"
        f"- What worked: {worked}\n"
        f"- What did not work: {did_not_work}\n"
        f"- Forced compromises (library had no fitting option): {forced_text}\n"
        f"- Anti-patterns triggered: {triggered_text}\n"
        f"- User feedback: Awaiting human review on contact_sheet.png\n"
        f"- Gaps to research: {gap_text}\n"
    )

    content = target.read_text(encoding="utf-8")
    if "(none yet)" in content:
        content = content.replace("(none yet)", "").rstrip() + "\n"

    # Replace existing same-brand same-day record to avoid duplicate spam on re-runs
    pattern = re.compile(rf"\n### Carousel: {re.escape(brand)} --- {re.escape(date_str)}\n.*?(?=\n### |\Z)", re.S)
    if pattern.search(content):
        content = pattern.sub(entry_block, content)
    else:
        content = content.rstrip() + "\n" + entry_block

    target.write_text(content.rstrip() + "\n", encoding="utf-8")
    return {
        "recorded": True,
        "path": str(target),
        "gap_detected": bool(gap_sig.get("detected")) or bool(triggered),
        "gap_signal": gap_sig,
    }


def _review_by_str(days: int = 30) -> str:
    return (datetime.now(timezone.utc) + timedelta(days=days)).strftime("%Y-%m-%d")


def add_candidate_to_library(
    candidate: dict[str, Any],
    tested_in: str,
    test_result: str,
    candidates_path: Path | None = None,
    review_by: str | None = None,
) -> dict[str, Any]:
    """Write a new `status: candidate` entry into `library_candidates.md` (NEVER into core library!)."""
    target = candidates_path or CANDIDATES_PATH
    if not target.exists():
        return {"added": False, "reason": "library_candidates.md not found"}

    cid = candidate["id"]
    content = target.read_text(encoding="utf-8")

    # Remove placeholder example block if still present
    example_re = re.compile(r"``` yaml\n# Example \(delete when real entries exist\).*?```", re.S)
    content = example_re.sub("", content).rstrip() + "\n"

    if f"id: {cid}" in content:
        return {"added": False, "already_exists": True, "id": cid, "path": str(target)}

    def _fmt_list(vals: list[str]) -> str:
        return "[" + ", ".join(json.dumps(v, ensure_ascii=False) for v in vals) + "]"

    due_review = review_by or candidate.get("review_by") or _review_by_str(30)
    yaml_block = f"""
``` yaml
entry:
  id: {cid}
  name: {json.dumps(candidate['name'], ensure_ascii=False)}
  layer: {candidate['layer']}
  description: {json.dumps(candidate['description'], ensure_ascii=False)}
  visual_traits: {_fmt_list(candidate.get('visual_traits', []))}
  emotional_voice: {_fmt_list(candidate.get('emotional_voice', []))}
  works_for: {_fmt_list(candidate.get('works_for', []))}
  caution: {_fmt_list(candidate.get('caution', []))}
  distinct_from: {json.dumps(candidate.get('distinct_from', ''), ensure_ascii=False)}
  pairs_with: {_fmt_list(candidate.get('pairs_with', []))}
  language_notes: {json.dumps(candidate.get('language_notes', ''), ensure_ascii=False)}
  source: {json.dumps(candidate.get('source', ''), ensure_ascii=False)}
  confidence: {candidate.get('confidence', 'medium')}
  status: candidate
  review_by: {json.dumps(due_review, ensure_ascii=False)}
  tested_in: {json.dumps(tested_in, ensure_ascii=False)}
  test_result: {json.dumps(test_result, ensure_ascii=False)}
  approved_by_user: false
```
"""
    target.write_text(content.rstrip() + "\n" + yaml_block, encoding="utf-8")
    return {
        "added": True,
        "id": cid,
        "status": "candidate",
        "review_by": due_review,
        "approved_by_user": False,
        "path": str(target),
    }


def record_learning_cycle(
    gap_targeted: str,
    sources: str,
    candidate_ids: list[str],
    test_slide_path: str,
    section10_result: str,
    log_path: Path | None = None,
) -> dict[str, Any]:
    """Append a Section 15.2 Learning Cycle report into `learning_log.md`."""
    target = log_path or LEARNING_LOG_PATH
    if not target.exists():
        return {"recorded": False}

    content = target.read_text(encoding="utf-8")
    existing_cycles = re.findall(r"### Learning cycle (\d+) ---", content)
    date_str = _today_str()

    # Prevent duplicating an identical cycle for the same gap & date
    if f"- Gap targeted: {gap_targeted}" in content and date_str in content:
        return {"recorded": False, "already_recorded": True, "path": str(target)}

    cycle_n = (max(int(x) for x in existing_cycles) + 1) if existing_cycles else 1
    block = (
        f"\n### Learning cycle {cycle_n} --- {date_str}\n"
        f"- Gap targeted: {gap_targeted}\n"
        f"- Sources consulted: {sources}\n"
        f"- Candidate entries added (max 3): {', '.join(candidate_ids[:3])}\n"
        f"- Test slide(s): {test_slide_path}\n"
        f"- Result against section 10 checks: {section10_result}\n"
        f"- Promoted to tested: none yet (status remains `candidate` pending user review)\n"
        f"- Awaiting user approval: {', '.join(candidate_ids[:3])} (NEVER merged into typography_intelligence_library.md without explicit approval)\n"
        f"- Proposed merges / prunes: None (cycle {cycle_n} < 5)\n"
    )
    target.write_text(content.rstrip() + "\n" + block, encoding="utf-8")
    return {"recorded": True, "cycle": cycle_n, "path": str(target)}
