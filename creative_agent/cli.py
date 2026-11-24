"""Unified CLI for the 4-Role Instagram Creative Agent (Hermes Desktop & Local Pipeline).

Commands:
    python -m creative_agent.cli styles
    python -m creative_agent.cli plan --brand "Kopi Sore" --industry "Coffee Roastery" --html path/to/index.html --out path/to/out
    python -m creative_agent.cli revise --spec path/to/carousel_spec.json --style cinematic_premium
    python -m creative_agent.cli render --spec path/to/carousel_spec.json --out path/to/out [--only 2]
    python -m creative_agent.cli qa --spec path/to/carousel_spec.json --out path/to/out
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from creative_agent.carousel_planner import CarouselPlanner
from creative_agent.creative_director import CreativeDirector
from creative_agent.design_reviewer import DesignReviewer
from creative_agent.style_registry import STYLE_LIBRARY_12, list_12_styles
from creative_agent.typography_engine import record_carousel_to_learning_log
from creative_agent.visual_designer import VisualDesigner


def cmd_styles(_args: argparse.Namespace) -> None:
    print("12 Adaptive Visual Styles (carousel_design_system_website_showcase.md):")
    for idx, s in enumerate(list_12_styles(), start=1):
        print(f"  {idx:02d}. {s['key']:<22} | {s['label']} | Story: {s['storytelling_default']}")


def cmd_plan(args: argparse.Namespace) -> None:
    out_dir = Path(args.out).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    director = CreativeDirector()
    planner = CarouselPlanner()
    designer = VisualDesigner()

    brief = {
        "brand_name": args.brand,
        "industry": args.industry,
        "city": args.city or "",
        "project_status": args.status,
        "design_style": args.style or "",
        "domain": args.domain or "",
    }
    analysis = director.analyze_business(brief)

    assets: dict[str, Any] = {}
    facts: dict[str, Any] = {"project_status": args.status.upper(), "is_full_demo": args.status == "demo"}
    if args.html:
        captured = designer.capture_from_html(Path(args.html), out_dir, is_full_demo=(args.status == "demo"))
        assets.update(captured["assets"])
        facts = captured["facts"]
    if args.desktop:
        assets["desktop_screenshot"] = str(Path(args.desktop).resolve())
    if args.mobile:
        assets["mobile_screenshot"] = str(Path(args.mobile).resolve())
    if args.logo:
        assets["logo"] = str(Path(args.logo).resolve())
    if args.reference_image:
        assets["reference_image"] = str(Path(args.reference_image).resolve())

    audit = director.audit_assets(assets)
    concepts = director.recommend_concepts(analysis, reference_image=args.reference_image)
    art_dir = director.build_art_direction(
        analysis,
        chosen_style=args.style or concepts[0]["style_key"],
        storytelling_override=args.storytelling,
        reference_image=args.reference_image,
    )
    spec = planner.build_spec(
        brief=analysis,
        art_direction=art_dir,
        facts=facts,
        assets=assets,
        issue_num=args.issue,
        selected_headline_idx=args.headline_idx,
    )

    spec_path = planner.save_spec(spec, out_dir / "carousel_spec.json")
    storyboard_md = planner.format_storyboard_markdown(spec)
    (out_dir / "storyboard.md").write_text(storyboard_md, encoding="utf-8")

    print("=== ASSET AUDIT ===")
    print("Available:", audit["available"] or ["-"])
    print("Missing:", audit["missing"] or ["-"])
    print("Optional:", audit["optional"] or ["-"])
    print("\n=== 3 RECOMMENDED CONCEPTS ===")
    for c in concepts:
        print(f"  [{c['option']}] {c['style_key']} — {c['primary_style']} + {c['secondary_style']} | Story: {c['storytelling_method']}")
    print("\n=== STORYBOARD (SLIDE 01-04) ===")
    print(storyboard_md)
    print(f"\n[OK] Spec saved (no PNG rendered yet): {spec_path}")


def cmd_revise(args: argparse.Namespace) -> None:
    spec_path = Path(args.spec).resolve()
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    planner = CarouselPlanner()

    patch: dict[str, Any] = {}
    if args.style:
        patch["style_key"] = args.style
    if args.storytelling:
        patch["storytelling_key"] = args.storytelling
    if args.reference_image:
        patch["reference_image"] = str(Path(args.reference_image).resolve())
    if args.caption:
        patch["caption"] = args.caption

    slide_patches = []
    for n in (1, 2, 3, 4):
        hl = getattr(args, f"headline_{n}", None)
        sub = getattr(args, f"sub_{n}", None)
        if hl or sub:
            sp: dict[str, Any] = {"n": n}
            if hl:
                sp["headline_html"] = hl
            if sub:
                sp["subhead"] = sub
            slide_patches.append(sp)
    if slide_patches:
        patch["slides"] = slide_patches

    updated = planner.revise_spec(spec, patch)
    planner.save_spec(updated, spec_path)
    (spec_path.parent / "storyboard.md").write_text(planner.format_storyboard_markdown(updated), encoding="utf-8")
    print(f"[OK] Targeted revision saved to {spec_path}")
    print(planner.format_storyboard_markdown(updated))


def cmd_render(args: argparse.Namespace) -> None:
    spec_path = Path(args.spec).resolve()
    out_dir = Path(args.out).resolve() if args.out else spec_path.parent
    spec = json.loads(spec_path.read_text(encoding="utf-8"))

    designer = VisualDesigner()
    reviewer = DesignReviewer()

    res = designer.render_slides(spec, out_dir, only_slide=args.only, scale=args.scale)
    (out_dir / "caption.txt").write_text(spec.get("caption", ""), encoding="utf-8")
    qa = reviewer.review(spec, out_dir)
    record_carousel_to_learning_log(spec, qa)

    print(f"[OK] Rendered {len(res['slides'])} slides to {out_dir}")
    for s in res["slides"]:
        print(f"  - {s['name']} ({s['width']}x{s['height']}, {s['size_bytes']//1024} KB)")
    cs = res["contact_sheet"]
    print(f"[OK] Contact Sheet 2x2: {cs['path']} ({cs['width']}x{cs['height']}, {cs['size_bytes']//1024} KB)")
    print(f"[OK] Cover Grid Crop:   {res['cover_grid']['path']}")
    print(f"[QA] Status={qa['status']} | Score={qa['score']}/100 ({qa['passed_checks']}/{qa['total_checks']})")
    if qa["warnings"]:
        print("[QA WARN]", "; ".join(qa["warnings"]))
    if qa["revisions"]:
        print("[QA REVISIONS]", "; ".join(qa["revisions"]))


def cmd_qa(args: argparse.Namespace) -> None:
    spec_path = Path(args.spec).resolve()
    out_dir = Path(args.out).resolve() if args.out else spec_path.parent
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    qa = DesignReviewer().review(spec, out_dir)
    print(json.dumps(qa, indent=2, ensure_ascii=False))


def main() -> None:
    parser = argparse.ArgumentParser(description="@goandalan 4-Role Instagram Creative Agent CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("styles", help="Tampilkan daftar 12 gaya visual adaptif")

    p_plan = sub.add_parser("plan", help="Tahap 1-6: Audit aset, 3 konsep, storyboard, & carousel_spec.json")
    p_plan.add_argument("--brand", required=True)
    p_plan.add_argument("--industry", required=True)
    p_plan.add_argument("--city", default="")
    p_plan.add_argument("--domain", default="")
    p_plan.add_argument("--status", choices=["concept", "demo", "prototype", "live"], default="concept")
    p_plan.add_argument("--style", choices=list(STYLE_LIBRARY_12.keys()))
    p_plan.add_argument("--storytelling")
    p_plan.add_argument("--html", help="Path file HTML demo untuk capture screenshot & fakta DOM")
    p_plan.add_argument("--desktop", help="Path screenshot desktop manual")
    p_plan.add_argument("--mobile", help="Path screenshot mobile manual")
    p_plan.add_argument("--logo", help="Path logo brand")
    p_plan.add_argument("--reference-image", help="Path gambar referensi untuk ekstraksi palet warna")
    p_plan.add_argument("--issue", type=int, default=1)
    p_plan.add_argument("--headline-idx", type=int, default=0)
    p_plan.add_argument("--out", required=True)

    p_rev = sub.add_parser("revise", help="Tahap 8: Revisi terarah pada carousel_spec.json tanpa ulang dari awal")
    p_rev.add_argument("--spec", required=True)
    p_rev.add_argument("--style", choices=list(STYLE_LIBRARY_12.keys()))
    p_rev.add_argument("--storytelling")
    p_rev.add_argument("--reference-image")
    p_rev.add_argument("--caption")
    for n in (1, 2, 3, 4):
        p_rev.add_argument(f"--headline-{n}")
        p_rev.add_argument(f"--sub-{n}")

    p_ren = sub.add_parser("render", help="Tahap 9: Render 4 PNG + Contact Sheet 2x2 + Cover Grid + QA")
    p_ren.add_argument("--spec", required=True)
    p_ren.add_argument("--out")
    p_ren.add_argument("--only", type=int, choices=[1, 2, 3, 4], help="Render ulang 1 slide spesifik saja")
    p_ren.add_argument("--scale", type=int, choices=[1, 2], default=2)

    p_qa = sub.add_parser("qa", help="Jalankan Design Reviewer QA pada output yang sudah dirender")
    p_qa.add_argument("--spec", required=True)
    p_qa.add_argument("--out")

    args = parser.parse_args()
    {"styles": cmd_styles, "plan": cmd_plan, "revise": cmd_revise, "render": cmd_render, "qa": cmd_qa}[args.command](args)


if __name__ == "__main__":
    main()
