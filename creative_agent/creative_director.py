"""Role 1: Creative Director — Business analysis, asset audit, 2-3 concepts & art direction."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from creative_agent.niche_resolver import resolve_niche_blueprint
from creative_agent.style_registry import (
    STORYTELLING_METHODS,
    STYLE_LIBRARY_12,
    extract_palette_from_image,
    resolve_style_key,
)
from creative_agent.typography_engine import plan_typography_direction


# Industry -> 3 meaningfully different visual concepts (never just color swaps)
INDUSTRY_CONCEPT_TRIOS: dict[str, tuple[str, str, str]] = {
    "coffee": ("organic_warm", "collage_scrapbook", "editorial_magazine"),
    "cafe": ("playful_pop", "organic_warm", "collage_scrapbook"),
    "barber": ("swiss_minimal", "cinematic_premium", "bold_brutalist"),
    "clinic": ("data_infographic", "swiss_minimal", "organic_warm"),
    "dental": ("data_infographic", "swiss_minimal", "digital_product"),
    "food": ("product_first", "cinematic_premium", "playful_pop"),
    "resto": ("cinematic_premium", "product_first", "editorial_magazine"),
    "hotel": ("cinematic_premium", "editorial_magazine", "organic_warm"),
    "farm": ("organic_warm", "swiss_minimal", "product_first"),
    "saas": ("digital_product", "data_infographic", "swiss_minimal"),
    "fashion": ("editorial_magazine", "bold_brutalist", "collage_scrapbook"),
    "properti": ("cinematic_premium", "editorial_magazine", "swiss_minimal"),
    "default": ("editorial_magazine", "swiss_minimal", "hybrid_art_directed"),
}


class CreativeDirector:
    """Analyzes business context, audits available assets, and recommends art directions."""

    def analyze_business(self, brief: dict[str, Any]) -> dict[str, Any]:
        brand_name = (brief.get("brand_name") or brief.get("business_name") or "Brand Lokal").strip()
        industry = (brief.get("industry") or brief.get("category") or "Bisnis Lokal").strip()
        city = (brief.get("city") or "").strip()
        project_status = (brief.get("project_status") or "concept").strip().lower()
        if project_status not in {"live", "prototype", "concept", "demo"}:
            project_status = "concept"

        return {
            "brand_name": brand_name,
            "industry": industry,
            "city": city,
            "project_status": project_status,
            "target_audience": (brief.get("target_audience") or f"Calon pelanggan {industry.lower()} yang mengakses via Instagram mobile").strip(),
            "website_goal": (brief.get("website_goal") or "Memperjelas informasi layanan, jam buka, dan alur kontak/booking di layar HP").strip(),
            "brand_personality": (brief.get("brand_personality") or "").strip(),
            "language": (brief.get("language") or "id").strip(),
            "design_style_hint": (brief.get("design_style") or "").strip(),
        }

    def audit_assets(self, assets: dict[str, Any]) -> dict[str, list[str]]:
        """Classify assets into Available, Missing, Optional, and Assumption."""
        available: list[str] = []
        missing: list[str] = []
        optional: list[str] = []
        assumptions: list[str] = []

        checks = [
            ("desktop_screenshot", "Screenshot Desktop Hero", True),
            ("mobile_screenshot", "Screenshot Mobile Hero", True),
            ("desktop_detail", "Screenshot Detail Section (Desktop)", False),
            ("mobile_detail", "Screenshot Detail Section (Mobile)", False),
            ("logo", "Logo Brand", False),
            ("reference_image", "Reference Image / Moodboard", False),
            ("custom_font", "Custom Font File", False),
        ]
        for key, label, required in checks:
            val = assets.get(key)
            exists = bool(val) and (isinstance(val, str) and (Path(val).exists() or val.startswith("http")))
            if exists:
                available.append(f"{label} ({Path(val).name})")
            elif required:
                missing.append(label)
            else:
                optional.append(label)

        if not assets.get("logo"):
            assumptions.append("Menggunakan typographic wordmark brand (bukan logo rekaan).")
        if not assets.get("reference_image"):
            assumptions.append("Palet warna diambil dari design_style website demo / karakter industri.")

        return {
            "available": available,
            "missing": missing,
            "optional": optional,
            "assumptions": assumptions,
        }

    def recommend_concepts(
        self,
        analysis: dict[str, Any],
        reference_image: str | None = None,
    ) -> list[dict[str, Any]]:
        """Generate 3 meaningfully distinct creative direction concepts."""
        ind_lower = f"{analysis['industry']} {analysis['brand_name']}".lower()
        trio = INDUSTRY_CONCEPT_TRIOS["default"]
        for tok, keys in INDUSTRY_CONCEPT_TRIOS.items():
            if tok != "default" and tok in ind_lower:
                trio = keys
                break

        preferred_key = resolve_style_key(analysis.get("design_style_hint"), analysis["industry"])
        ordered_keys: list[str] = [preferred_key] + [k for k in trio if k != preferred_key]
        ordered_keys = ordered_keys[:3]

        ref_palette = extract_palette_from_image(reference_image) if reference_image else None

        concepts: list[dict[str, Any]] = []
        for idx, style_key in enumerate(ordered_keys, start=1):
            spec = STYLE_LIBRARY_12[style_key]
            story_key = spec["storytelling_default"]
            story = STORYTELLING_METHODS[story_key]
            palette = dict(spec["palette"])
            if ref_palette and idx == 1:
                palette.update({k: v for k, v in ref_palette.items() if k in palette})

            concepts.append(
                {
                    "option": idx,
                    "style_key": style_key,
                    "primary_style": spec["label"],
                    "secondary_style": spec["secondary_default"],
                    "storytelling_key": story_key,
                    "storytelling_method": story["label"],
                    "storytelling_arc": story["arc"],
                    "palette": palette,
                    "typography": {
                        "display": spec["font_display"].split(",")[0].strip(" '\""),
                        "body": spec["font_body"].split(",")[0].strip(" '\""),
                        "mono": spec["font_mono"].split(",")[0].strip(" '\""),
                    },
                    "compositions": dict(spec["compositions"]),
                    "closing_label": spec["closing_label"],
                    "rationale": spec["direction_summary"],
                    "reference_palette_applied": bool(ref_palette and idx == 1),
                }
            )
        return concepts

    def build_art_direction(
        self,
        analysis: dict[str, Any],
        chosen_style: str | None = None,
        storytelling_override: str | None = None,
        reference_image: str | None = None,
        palette_override: dict[str, str] | None = None,
        custom_fonts: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Lock a concrete art direction dict for planning & rendering."""
        style_key = resolve_style_key(chosen_style or analysis.get("design_style_hint"), analysis["industry"])
        spec = STYLE_LIBRARY_12[style_key]
        story_key = storytelling_override if storytelling_override in STORYTELLING_METHODS else spec["storytelling_default"]
        story = STORYTELLING_METHODS[story_key]

        palette = dict(spec["palette"])
        ref_applied = False
        if reference_image:
            extracted = extract_palette_from_image(reference_image)
            if extracted:
                palette.update({k: v for k, v in extracted.items() if k in palette})
                ref_applied = True
        if palette_override:
            palette.update({k: v for k, v in palette_override.items() if v})

        niche_bp = resolve_niche_blueprint(
            category=analysis["industry"],
            business_name=analysis["brand_name"],
            city=analysis.get("city", ""),
            preferred_demo_style=analysis.get("design_style_hint") or None,
        )
        typo_dir = plan_typography_direction(
            brand_name=analysis["brand_name"],
            industry=analysis["industry"],
            audience=analysis.get("target_audience", ""),
            style_hint=style_key,
        )
        t_fonts = typo_dir["fonts"]
        fonts = {
            "fonts_url": t_fonts["fonts_url"],
            "font_display": (custom_fonts or {}).get("display") or t_fonts["font_display"],
            "font_body": (custom_fonts or {}).get("body") or t_fonts["font_body"],
            "font_mono": (custom_fonts or {}).get("mono") or t_fonts["font_mono"],
            "custom_font_file": (custom_fonts or {}).get("font_file", ""),
        }

        return {
            "style_key": style_key,
            "primary_style": spec["label"],
            "secondary_style": spec["secondary_default"],
            "storytelling_key": story_key,
            "storytelling_method": story["label"],
            "storytelling_arc": story["arc"],
            "palette": palette,
            "fonts": fonts,
            "geometry": dict(spec["geometry"]),
            "compositions": dict(spec["compositions"]),
            "closing_label": "Website Concept",
            "direction_summary": spec["direction_summary"],
            "reference_image": reference_image or "",
            "reference_palette_applied": ref_applied,
            "typography_direction": typo_dir,
            "niche_blueprint": {
                "niche_key": niche_bp["niche_key"],
                "niche_label": niche_bp["niche_label"],
                "primary_business_goal": niche_bp["primary_business_goal"],
                "website_section_architecture": niche_bp["website_section_architecture"],
                "photo_set": niche_bp["photo_set"],
                "registry_audit": niche_bp["registry_audit"],
            },
        }
