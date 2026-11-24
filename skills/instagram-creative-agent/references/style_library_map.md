# Style ↔ Typography Intelligence Library Crosswalk (12 ↔ 30 ↔ 44)

Maps the **12 adaptive carousel styles** (`creative_agent/style_registry.py`) ↔ the **30 art-direction movements** (`§3` of `typography_intelligence_library.md`, exact numbering `1–30`) ↔ **44 typographic building-block entries** across `typography_intelligence_library.md` (§2 classifications, §4 treatments, §5 compositions, §6 pairing recipes).

> **Audit note:** Every number in the middle column (`#1`–`#30`) is verified 1:1 against `## 3. Typographic art-direction styles` in `typography_intelligence_library.md`.

---

## 1. Master Crosswalk: 12 Styles ↔ 30 Art Directions (§3) ↔ Library Entries

| # | `style_registry.py` Key (12) | §3 Art-Direction Numbers & Names (1–30) | Primary Typeface Classifications (§2) | Signature Treatments (§4) & Compositions (§5) |
| :-: | :--- | :--- | :--- | :--- |
| 01 | `editorial_magazine` | **#1** Contemporary Editorial · **#3** Newspaper / Broadsheet · **#4** Art Magazine | Display Serif · Garalde · Humanist Sans | `extreme_scale_contrast`, `microtype` · `asymmetric_editorial`, `scattered_editorial` |
| 02 | `bold_brutalist` | **#9** Constructivism · **#18** Swiss Punk / New Wave · **#19** Neo-Brutalist | Condensed Sans · Grotesk Display · Monospaced | `oversized_display`, `outline_type`, `rotated_typography` · `diagonal_momentum`, `frame_breaking` |
| 03 | `digital_product` | **#6** Swiss / International Typographic Style · **#25** Techno / Futuristic · **#29** Corporate Expressive | Neo-Grotesque · Extended Sans · Monospaced | `monospace_metadata`, `tight_tracking` · `screenshot_led`, `modular_grid` |
| 04 | `swiss_minimal` | **#6** Swiss / International Typographic Style · **#7** Modernist / New Typography · **#8** Bauhaus · **#20** Minimalist | Geometric Sans · Neo-Grotesque · Monospaced | `extreme_scale_contrast`, `wide_tracking` · `split_canvas`, `top_heavy`, `modular_grid` |
| 05 | `collage_scrapbook` | **#12** Dada / Anti-Design · **#16** Punk / DIY Zine · **#17** Grunge / Deconstructive Editorial · **#27** Neo-Vintage / Heritage Revival | Slab Serif · Marker / Handwritten · Sign Painting | `overprint_color_blocking`, `handwritten_annotation`, `grain / noise`, `distressed type` · `scattered_editorial`, `layered_depth` |
| 06 | `cinematic_premium` | **#2** Luxury Editorial · **#10** Art Deco · **#23** 3D / Dimensional | Didone · Transitional Serif · Humanist Sans | `wide_tracking`, `image_text_integration`, `shadow typography` · `type_as_frame`, `bottom_heavy` |
| 07 | `playful_pop` | **#13** Psychedelic · **#14** Pop Art · **#15** Memphis · **#24** Liquid / Inflated · **#30** Playful Typographic Branding | Rounded Sans · Grotesk Display · Casual Script | `oversized_display`, `repeated typography`, `wave baseline`, `punctuation_as_graphic` · `monumental_headline`, `typographic_staircase` |
| 08 | `organic_warm` | **#27** Neo-Vintage / Heritage Revival · **#28** Organic / Natural | Humanist / Old Style Serif · Soft / Rounded Serif · Slab Serif · Humanist Sans | `split_word_treatment`, `image_text_integration`, `overprint_color_blocking` · `monumental_headline`, `asymmetric_editorial` |
| 09 | `technical_blueprint` | **#11** Futurism · **#22** Kinetic-inspired · **#25** Techno / Futuristic · **#26** Neo-Retro / Y2K | Square / Technical Sans · Extended Sans · Monospaced · Pixel / Bitmap | `echo_ghost_type`, `monospace_metadata`, `numeral_led_design` · `diagonal_momentum`, `vertical_edge`, `modular_grid` |
| 10 | `product_first` | **#5** Catalog / Product Editorial · **#21** Maximalist | Display Serif · Clarendon · Grotesk Display · Humanist Sans | `cropped_typography`, `overprint_color_blocking`, `image_text_integration` · `image_interruption`, `caption_led` |
| 11 | `data_infographic` | **#6** Swiss / International Typographic Style · **#29** Corporate Expressive | Neo-Grotesque · Geometric Sans · Monospaced | `numeral_led_design`, `monospace_metadata`, `microtype` · `caption_led`, `screenshot_led`, `modular_grid` |
| 12 | `hybrid_art_directed` | **#4** Art Magazine · **#7** Modernist / New Typography · **#18** Swiss Punk / New Wave · **#21** Maximalist | Didone / Display Serif + Condensed / Extended Sans | `layered typography`, `split_word_treatment`, `outline_type` · `layered_depth`, `frame_breaking`, `split_canvas` |

---

## 2. Full Index Verification: All 30 §3 Art Directions (`1–30` Complete Coverage)

| §3 # | Art Direction (Exact §3 Name) | Primary Mapped `style_registry` Key |
| :-: | :--- | :--- |
| 1 | Contemporary Editorial | `editorial_magazine` |
| 2 | Luxury Editorial | `cinematic_premium` |
| 3 | Newspaper / Broadsheet | `editorial_magazine` |
| 4 | Art Magazine | `editorial_magazine` / `hybrid_art_directed` |
| 5 | Catalog / Product Editorial | `product_first` |
| 6 | Swiss / International Typographic Style | `swiss_minimal` / `digital_product` / `data_infographic` |
| 7 | Modernist / New Typography | `swiss_minimal` / `hybrid_art_directed` |
| 8 | Bauhaus | `swiss_minimal` |
| 9 | Constructivism | `bold_brutalist` |
| 10 | Art Deco | `cinematic_premium` |
| 11 | Futurism | `technical_blueprint` |
| 12 | Dada / Anti-Design | `collage_scrapbook` |
| 13 | Psychedelic | `playful_pop` |
| 14 | Pop Art | `playful_pop` |
| 15 | Memphis | `playful_pop` |
| 16 | Punk / DIY Zine | `collage_scrapbook` |
| 17 | Grunge / Deconstructive Editorial | `collage_scrapbook` |
| 18 | Swiss Punk / New Wave | `bold_brutalist` / `hybrid_art_directed` |
| 19 | Neo-Brutalist | `bold_brutalist` |
| 20 | Minimalist | `swiss_minimal` |
| 21 | Maximalist | `product_first` / `hybrid_art_directed` |
| 22 | Kinetic-inspired | `technical_blueprint` |
| 23 | 3D / Dimensional | `cinematic_premium` |
| 24 | Liquid / Inflated | `playful_pop` |
| 25 | Techno / Futuristic | `digital_product` / `technical_blueprint` |
| 26 | Neo-Retro / Y2K | `technical_blueprint` |
| 27 | Neo-Vintage / Heritage Revival | `organic_warm` / `collage_scrapbook` |
| 28 | Organic / Natural | `organic_warm` |
| 29 | Corporate Expressive | `digital_product` / `data_infographic` |
| 30 | Playful Typographic Branding | `playful_pop` |

---

## 3. 44 Core Library Entries Inventory (Classification + Pairing / Engine Bridge)

To keep the bridge deterministic across code (`creative_agent/typography_engine.py`) and docs (`typography_intelligence_library.md`):
- **16 Active Typeface Classification Anchors** in `typography_engine.TYPEFACE_CLASSIFICATIONS` (mapped directly from the 31 classifications in §2).
- **14 Pairing Recipes** in `typography_intelligence_library.md` §6 (Premium hospitality, Modern SaaS, Experimental studio, Playful food, Heritage craft, Fashion campaign, Architecture, Tech infrastructure, Culture magazine, Youth campaign, Luxury product, Organic wellness, Brutalist startup, Neo-retro gaming).
- **14 Composition Methods** in `style_registry.COMPOSITION_METHODS` (aligned to §5's 18 composition behaviors).
- **Total bridged operational entries:** `16 + 14 + 14 = 44`.
