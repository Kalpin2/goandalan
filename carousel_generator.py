"""Dual-mode adapter connecting @goandalan Mini App / batch pipeline to `creative_agent/`.

Non-interactive / automatic mode:
    Called by `app.py`, background batch jobs, or `python carousel_generator.py --slug <slug>`.
    Runs the full 4-role pipeline automatically without blocking for terminal input:
    CreativeDirector -> CarouselPlanner -> VisualDesigner (4 PNGs + 2x2 Contact Sheet + Cover Grid
    + Stage A concept_preview.png) -> DesignReviewer (qa_report.json).

Interactive 9-step mode (Hermes Desktop / chat):
    Use `python -m creative_agent.cli plan | revise | render | qa`.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import database as db
import demo_generator as dg
from config import settings
from creative_agent import (
    STYLE_LIBRARY_12,
    CarouselPlanner,
    CreativeDirector,
    DesignReviewer,
    VisualDesigner,
    add_candidate_to_library,
    record_carousel_to_learning_log,
    record_learning_cycle,
    resolve_niche_blueprint,
    resolve_style_key,
    draft_recycled_caption,
)


def generate_concept_package_for_lead(
    lead_id: int,
    issue_num: int | None = None,
    anonymize: bool | None = None,
    force_style: str | None = None,
    reference_image: str | None = None,
    logo_path: str | None = None,
    only_slide: int | None = None,
    slide_sequence: str | None = None,
    caption_voice: str | None = None,
    art_direction_preset: str | None = None,
    sequence_type: str | None = None,
    voice_id: str | None = None,
    hook_pattern_id: str | None = None,
    creative_note: str = "",
) -> dict[str, Any]:
    """Run non-interactive 4-role Creative Agent pipeline for a lead with explicit library overrides."""
    lead = db.get_lead(lead_id)
    if not lead:
        raise ValueError(f"Lead ID {lead_id} tidak ditemukan.")

    use_anon = bool(lead.get("is_anonymized")) if anonymize is None else anonymize

    eff_style = (
        art_direction_preset
        if art_direction_preset and str(art_direction_preset).lower() != "auto"
        else force_style
    )
    eff_seq = (
        sequence_type
        if sequence_type and str(sequence_type).lower() != "auto"
        else slide_sequence
    )
    eff_voice_id = (
        str(voice_id).strip().upper()
        if voice_id and str(voice_id).strip().lower() != "auto"
        else None
    )
    eff_hook_id = (
        str(hook_pattern_id).strip().upper()
        if hook_pattern_id and str(hook_pattern_id).strip().lower() != "auto"
        else None
    )
    eff_cap_voice = caption_voice
    if not eff_cap_voice and eff_voice_id in {"V2", "V4"}:
        eff_cap_voice = "formal_editorial"

    # Ensure demo_generator uses a valid 8-style demo key while creative_agent supports all 12 styles
    demo_style_override = eff_style if eff_style in dg.STYLE_THEMES else None
    concept_res = dg.generate_concept_html_for_lead(lead_id, anonymize=use_anon, force_style=demo_style_override)
    lead = concept_res["lead"]
    demo_style_key = concept_res["design_style"]
    carousel_style_key = resolve_style_key(eff_style or demo_style_key, lead.get("category", ""))

    slug = lead["slug"]
    demo_dir = settings.DEMOS_DIR / slug
    ig_dir = demo_dir / "ig"
    ig_dir.mkdir(parents=True, exist_ok=True)

    full_html = demo_dir / "index.html"
    is_full_demo = full_html.exists() and lead["status"] in {"FULL_DEMO_READY", "DP_PAID", "WON"}
    source_html = full_html if is_full_demo else Path(concept_res["concept_file"])

    director = CreativeDirector()
    planner = CarouselPlanner()
    designer = VisualDesigner()
    reviewer = DesignReviewer()

    # 1. Capture real multi-angle screenshots + verified DOM facts
    captured = designer.capture_from_html(source_html, ig_dir, is_full_demo=is_full_demo)
    assets = dict(captured["assets"])
    if logo_path and Path(logo_path).exists():
        assets["logo"] = str(Path(logo_path).resolve())
    if reference_image and Path(reference_image).exists():
        assets["reference_image"] = str(Path(reference_image).resolve())
    facts = captured["facts"]

    # 2. Creative Director — business analysis & locked 12-style art direction
    display_name = dg.generate_fictional_name(lead) if use_anon else lead["business_name"]
    analysis = director.analyze_business(
        {
            "brand_name": display_name,
            "industry": lead.get("category") or "Bisnis Lokal",
            "city": lead.get("city") or settings.DEFAULT_CITY,
            "project_status": "demo" if is_full_demo else "concept",
            "design_style": carousel_style_key,
            "domain": f"{db.slugify(display_name)}.id",
        }
    )
    art_dir = director.build_art_direction(
        analysis,
        chosen_style=carousel_style_key,
        reference_image=reference_image,
    )

    # 3. Carousel Planner — 4-slide storyboard, editable spec, & strict honesty/showcase checks
    resolved_issue = issue_num if issue_num is not None else max(2, int(lead["id"]) + 1)
    spec = planner.build_spec(
        brief=analysis,
        art_direction=art_dir,
        facts=facts,
        assets=assets,
        issue_num=resolved_issue,
        slide_sequence=eff_seq,
        caption_voice=eff_cap_voice,
    )
    spec["brief_config"] = {
        "content_format": "carousel",
        "art_direction_preset": eff_style or "auto",
        "sequence_type": eff_seq or "auto",
        "voice_id": eff_voice_id or "auto",
        "hook_pattern_id": eff_hook_id or "auto",
        "creative_note": creative_note or "",
    }
    spec_path = planner.save_spec(spec, ig_dir / "carousel_spec.json")
    (ig_dir / "storyboard.md").write_text(planner.format_storyboard_markdown(spec), encoding="utf-8")

    # 4. Visual Designer — render 4 PNGs (2160x2700) + 2x2 Contact Sheet + Cover Grid + Stage A DM photo
    if use_anon:
        recycled_cap = draft_recycled_caption(
            lead={**lead, "is_anonymized": 1, "anonymized_name": display_name},
            art_direction=art_dir,
            facts=facts,
            caption_voice_override=eff_cap_voice,
            voice_id_override=eff_voice_id,
            hook_pattern_id=eff_hook_id,
            content_format="carousel",
            creative_note=creative_note,
        )
        if recycled_cap["validation"]["passed"]:
            spec["caption"] = recycled_cap["caption"]
            spec["copy_patterns_used"] = recycled_cap["patterns_used"]
            spec["copy_voice"] = recycled_cap["voice"]
            spec["project"]["caption_voice"] = recycled_cap["caption_voice"]
            planner.save_spec(spec, ig_dir / "carousel_spec.json")

    render_res = designer.render_slides(spec, ig_dir, only_slide=only_slide, scale=2)
    caption_file = ig_dir / "caption.txt"
    caption_file.write_text(spec["caption"], encoding="utf-8")

    preview_info = designer.render_concept_preview_photo(
        spec=spec,
        desktop_rel="ig/desktop.png",
        mobile_rel="ig/mobile.png",
        demo_dir=demo_dir,
    )

    # 5. Design Reviewer (QA) — automated DOM, WCAG contrast, Section 11 Anti-Patterns & guardrail audit
    qa_report = reviewer.review(spec, ig_dir)

    # 6. Section 15 Self-Expansion Learning Loop — record carousel + optional 1-cycle candidate research
    log_result = record_carousel_to_learning_log(spec, qa_report)
    learning_cycle_result: dict[str, Any] | None = None
    if log_result.get("gap_detected"):
        gap_sig = log_result.get("gap_signal") or {}
        cand = gap_sig.get("candidate")
        if cand:
            test_slide_png = ig_dir / f"candidate_test_{cand['id']}.png"
            hero_photo_path = Path(assets.get("hero_photo") or assets.get("desktop_screenshot") or "")
            designer.render_candidate_test_slide(cand, display_name, hero_photo_path, test_slide_png)
            cand_res = add_candidate_to_library(
                candidate=cand,
                tested_in=f"{slug} ({test_slide_png.name})",
                test_result="Rendered 2160x2700 test slide; distinct enamel/woodblock craft hierarchy; legible Indonesian copy; status remains `candidate` awaiting explicit user approval.",
            )
            learning_cycle_result = record_learning_cycle(
                gap_targeted=gap_sig.get("gap_topic", cand["name"]),
                sources=cand.get("source", "Indonesian craft & typography archive observations"),
                candidate_ids=[cand["id"]],
                test_slide_path=str(test_slide_png),
                section10_result=f"PASS visual test slide ({test_slide_png.name}); candidate_added={cand_res.get('added')}",
            )

    typo_dir = art_dir.get("typography_direction") or {}
    niche_bp = art_dir.get("niche_blueprint") or {}
    art_direction_record = {
        "slug": slug,
        "brand_name": display_name,
        "project_status": facts["project_status"],
        "demo_style": demo_style_key,
        "carousel_style": carousel_style_key,
        "slide_sequence": spec["project"].get("slide_sequence", "campaign_to_website"),
        "caption_voice": spec["project"].get("caption_voice", "casual_gw"),
        "style_label": art_dir["primary_style"],
        "primary_style": art_dir["primary_style"],
        "secondary_style": art_dir["secondary_style"],
        "storytelling_method": art_dir["storytelling_method"],
        "palette": art_dir["palette"],
        "typography": spec["creative_direction"]["font_pair_label"],
        "typography_direction": typo_dir,
        "niche_blueprint": niche_bp,
        "compositions": [s["composition"] for s in spec["slides"]],
        "closing_label": art_dir["closing_label"],
        "contact_sheet": render_res["contact_sheet"]["path"],
        "cover_grid": render_res["cover_grid"]["path"],
        "qa_status": qa_report["status"],
        "qa_score": qa_report["score"],
        "learning_log": log_result,
        "learning_cycle": learning_cycle_result,
        "slides": render_res["slides"],
    }
    (ig_dir / "art_direction.json").write_text(
        json.dumps(art_direction_record, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    rel_preview = str(Path(preview_info["path"]).relative_to(settings.BASE_DIR)).replace("\\", "/")
    rel_carousel_dir = str(ig_dir.relative_to(settings.BASE_DIR)).replace("\\", "/")
    updates: dict[str, Any] = {
        "design_style": demo_style_key,
        "concept_preview_path": rel_preview,
        "carousel_dir": rel_carousel_dir,
    }
    if use_anon:
        updates["status"] = "RECYCLED_CONTENT"
    elif lead["status"] == "NEW":
        updates["status"] = "CONCEPT_READY"

    updated_lead = db.update_lead(lead_id, updates)

    return {
        "lead": updated_lead,
        "design_style": demo_style_key,
        "carousel_style": carousel_style_key,
        "style_label": art_dir["primary_style"],
        "art_direction": art_direction_record,
        "spec_file": str(spec_path),
        "concept_preview": preview_info,
        "contact_sheet": render_res["contact_sheet"],
        "cover_grid": render_res["cover_grid"],
        "qa_report": qa_report,
        "ig_dir": str(ig_dir),
        "slides": render_res["slides"],
        "caption_file": str(caption_file),
        "caption": spec["caption"],
    }


generate_carousel_for_lead = generate_concept_package_for_lead


def recycle_lead_to_content(lead_id: int) -> dict[str, Any]:
    """Anonymize concept (+ full demo if built) and regenerate all PNGs + 2x2 Contact Sheet."""
    lead = db.get_lead(lead_id)
    if not lead:
        raise ValueError(f"Lead ID {lead_id} tidak ditemukan.")

    full_exists = (settings.DEMOS_DIR / lead["slug"] / "index.html").exists()
    demo_res = None
    if full_exists:
        demo_res = dg.generate_full_demo_for_lead(lead_id, anonymize=True, update_status=False)

    pkg_res = generate_concept_package_for_lead(lead_id, anonymize=True)
    dg.rebuild_portfolio_index()
    return {
        "lead": pkg_res["lead"],
        "demo": demo_res,
        "carousel": pkg_res,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="@goandalan Adaptive Carousel Pipeline Adapter (Non-Interactive)")
    parser.add_argument("--slug", help="Slug lead")
    parser.add_argument("--lead-id", type=int, help="ID lead")
    parser.add_argument("--issue", type=int, help="Nomor Issue")
    parser.add_argument(
        "--style",
        choices=sorted(set(list(dg.STYLE_THEMES.keys()) + list(STYLE_LIBRARY_12.keys()))),
        help="Override design/carousel style (supports all 12 styles)",
    )
    parser.add_argument("--reference-image", help="Path gambar referensi untuk ekstraksi palet")
    parser.add_argument("--logo", help="Path logo brand")
    parser.add_argument("--only", type=int, choices=[1, 2, 3, 4], help="Re-render 1 slide spesifik saja")
    parser.add_argument(
        "--sequence",
        choices=["campaign_to_website", "reveal_first", "story_led"],
        help="Preset urutan 4 slide (P4)",
    )
    parser.add_argument(
        "--voice",
        choices=["formal_editorial", "casual_gw"],
        help="Override caption_voice (P7)",
    )
    parser.add_argument("--anonymize", action="store_true", help="Render versi brand fiktif (aman untuk IG)")
    args = parser.parse_args()

    db.init_db()
    lead = db.get_lead(args.lead_id) if args.lead_id else db.get_lead_by_slug(args.slug or "")
    if not lead:
        raise SystemExit("Lead tidak ditemukan. Berikan --slug atau --lead-id yang valid.")

    res = generate_concept_package_for_lead(
        lead["id"],
        issue_num=args.issue,
        anonymize=args.anonymize,
        force_style=args.style,
        reference_image=args.reference_image,
        logo_path=args.logo,
        only_slide=args.only,
        slide_sequence=args.sequence,
        caption_voice=args.voice,
    )
    ad = res["art_direction"]
    cs = res["contact_sheet"]
    qa = res["qa_report"]
    print(f"[OK] {lead['slug']} | {ad['primary_style']} + {ad['secondary_style']} | Story: {ad['storytelling_method']}")
    for s in res["slides"]:
        print(f"  - {s['name']} ({s['width']}x{s['height']}, {s['size_bytes']//1024} KB)")
    print(f"[OK] Contact Sheet 2x2: {cs['path']} ({cs['width']}x{cs['height']}, {cs['size_bytes']//1024} KB)")
    print(f"[QA] Status={qa['status']} | Score={qa['score']}/100 ({qa['passed_checks']}/{qa['total_checks']})")


if __name__ == "__main__":
    main()
