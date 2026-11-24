"""Role 4: Design Reviewer (QA) — Automated DOM, WCAG contrast, composition & guardrail audit."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from PIL import Image
from playwright.sync_api import sync_playwright

from creative_agent.carousel_planner import (
    BANNED_SALES_CTAS,
    CASUAL_SLANG_PATTERN,
    select_caption_voice,
)
from creative_agent.typography_engine import (
    DECORATIVE_MONO_FILLERS,
    audit_typography_anti_patterns,
)

# P3: Minimum readable body font size on 1080px canvas (~11px physical on mobile phones)
MOBILE_BODY_FONT_FLOOR_PX = 32


def _hex_to_rgb(hex_str: str) -> tuple[int, int, int] | None:
    s = (hex_str or "").strip().lstrip("#")
    if len(s) == 3:
        s = "".join(c * 2 for c in s)
    if len(s) != 6 or not re.fullmatch(r"[0-9a-fA-F]{6}", s):
        return None
    return int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16)


def _rel_luminance(rgb: tuple[int, int, int]) -> float:
    def lin(c: int) -> float:
        v = c / 255.0
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4

    r, g, b = rgb
    return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)


def wcag_contrast_ratio(hex1: str, hex2: str) -> float | None:
    rgb1, rgb2 = _hex_to_rgb(hex1), _hex_to_rgb(hex2)
    if not rgb1 or not rgb2:
        return None
    l1, l2 = _rel_luminance(rgb1), _rel_luminance(rgb2)
    lighter, darker = max(l1, l2), min(l1, l2)
    return round((lighter + 0.05) / (darker + 0.05), 2)


class DesignReviewer:
    """Evaluates rendered carousels for visual hierarchy, legibility, contrast, and guardrails."""

    def review(self, spec: dict[str, Any], out_dir: Path) -> dict[str, Any]:
        checks: list[dict[str, Any]] = []
        warnings: list[str] = []
        revisions: list[str] = []

        # 1. Composition variety check (detect generic/repetitive layouts)
        comps = [s.get("composition", "") for s in spec.get("slides", [])]
        unique_comps = len(set(comps))
        comp_ok = unique_comps >= 3
        checks.append(
            {
                "name": "composition_variety",
                "passed": comp_ok,
                "detail": f"{unique_comps}/4 unique compositions ({', '.join(comps)})",
            }
        )
        if not comp_ok:
            revisions.append("Variasikan komposisi antar-slide agar tidak monoton.")

        # 2. WCAG Contrast check (ink on bg & ink on surface)
        pal = spec["creative_direction"]["palette"]
        cr_bg = wcag_contrast_ratio(pal.get("ink", ""), pal.get("bg", ""))
        cr_surf = wcag_contrast_ratio(pal.get("ink", ""), pal.get("surface", ""))
        contrast_ok = (cr_bg is None or cr_bg >= 4.5) and (cr_surf is None or cr_surf >= 4.5)
        checks.append(
            {
                "name": "wcag_contrast",
                "passed": contrast_ok,
                "detail": f"ink/bg={cr_bg}:1, ink/surface={cr_surf}:1 (target >=4.5:1)",
            }
        )
        if not contrast_ok:
            revisions.append("Tingkatkan kontras warna teks utama terhadap background/surface minimal 4.5:1.")

        # 3. Output files & exact 4:5 retina dimensions (P4: dynamic slide names from spec, never hardcoded)
        spec_slides = spec.get("slides") or []
        expected_names = [
            f"{s.get('name') or str(int(s.get('n', idx + 1))).zfill(2) + '_slide'}.png"
            for idx, s in enumerate(spec_slides)
        ] or ["01_cover.png", "02_context.png", "03_reveal.png", "04_details.png"]
        png_ok = len(expected_names) == 4
        dims_detail: list[str] = []
        for fname in expected_names:
            fpath = out_dir / fname
            if not fpath.exists():
                png_ok = False
                revisions.append(f"File slide hilang: {fname}")
                continue
            with Image.open(fpath) as im:
                w, h = im.size
                dims_detail.append(f"{fname}={w}x{h}")
                if (w, h) not in {(1080, 1350), (2160, 2700)}:
                    png_ok = False
                    revisions.append(f"Ukuran {fname} bukan 4:5 ({w}x{h}).")

        contact_ok = (out_dir / "contact_sheet.png").exists()
        checks.append({"name": "output_pngs_4x5", "passed": png_ok, "detail": ", ".join(dims_detail)})
        checks.append({"name": "contact_sheet_2x2", "passed": contact_ok, "detail": "contact_sheet.png present" if contact_ok else "missing"})
        if not contact_ok:
            revisions.append("Render contact_sheet.png 2x2 untuk review cepat.")

        # 4. Live Playwright DOM overflow, image clipping, & mobile font floor check
        slides_html_path = out_dir / "slides.html"
        dom_ok = True
        dom_notes: list[str] = []
        if slides_html_path.exists():
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page(viewport={"width": 1200, "height": 1500}, device_scale_factor=1)
                page.goto(slides_html_path.resolve().as_uri(), wait_until="networkidle")
                page.evaluate("() => document.fonts.ready")
                dom_report = page.evaluate(
                    """() => {
                      const fillers = new Set(['label', 'tag', 'item', 'decoration', 'placeholder', 'lorem', 'sample']);
                      return Array.from(document.querySelectorAll('.slide')).map((slide, idx) => {
                        const overflowY = slide.scrollHeight - slide.clientHeight;
                        const overflowX = slide.scrollWidth - slide.clientWidth;
                        const imgs = Array.from(slide.querySelectorAll('img')).map(img => {
                          const rect = img.getBoundingClientRect();
                          const natRatio = img.naturalHeight ? img.naturalWidth / img.naturalHeight : 1;
                          const boxRatio = rect.height ? rect.width / rect.height : 1;
                          return {
                            alt: img.alt,
                            broken: !img.complete || img.naturalWidth === 0,
                            ratioDrift: Math.abs(natRatio - boxRatio) / Math.max(natRatio, 0.01),
                          };
                        });
                        const textSizes = Array.from(slide.querySelectorAll('p, li, h3')).map(el =>
                          parseFloat(getComputedStyle(el).fontSize || '0')
                        ).filter(n => n > 0);
                        const minBodyPx = textSizes.length ? Math.min(...textSizes) : 32;
                        const hl = slide.querySelector('h1, h2');
                        const hlStyle = hl ? getComputedStyle(hl) : null;
                        const monoEls = Array.from(slide.querySelectorAll('.mono-kicker, .pill-tag, .poster-kicker'));
                        const meaninglessMonoCount = monoEls.filter(el => fillers.has((el.innerText || '').trim().toLowerCase())).length;
                        const isCenteredCardLayout = Boolean(
                          hlStyle && hlStyle.textAlign === 'center' && slide.querySelectorAll('.callout-card, .journey-card').length >= 3
                        );
                        return {
                          slide: idx + 1,
                          overflowY,
                          overflowX,
                          minBodyPx,
                          brokenImgs: imgs.filter(i => i.broken).length,
                          clippedImgs: imgs.filter(i => i.ratioDrift > 0.48).map(i => i.alt),
                          headlineFont: hlStyle ? hlStyle.fontFamily.split(',')[0].trim() : '',
                          headlineSize: hlStyle ? parseFloat(hlStyle.fontSize || '0') : 0,
                          headlineAlign: hlStyle ? hlStyle.textAlign : 'left',
                          meaninglessMonoCount,
                          isCenteredCardLayout,
                        };
                      });
                    }"""
                )
                browser.close()

            for r in dom_report:
                if r["overflowY"] > 4 or r["overflowX"] > 4:
                    dom_ok = False
                    revisions.append(f"Slide 0{r['slide']} mengalami overflow (dx={r['overflowX']}px, dy={r['overflowY']}px).")
                if r["brokenImgs"] > 0:
                    dom_ok = False
                    revisions.append(f"Slide 0{r['slide']} memiliki gambar broken/tidak termuat.")
                if r["minBodyPx"] < MOBILE_BODY_FONT_FLOOR_PX:
                    dom_ok = False
                    revisions.append(
                        f"Slide 0{r['slide']} teks body {r['minBodyPx']}px di bawah batas minimum mobile {MOBILE_BODY_FONT_FLOOR_PX}px@1x."
                    )
                if r["clippedImgs"]:
                    warnings.append(f"Slide 0{r['slide']} cek rasio gambar: {', '.join(r['clippedImgs'])}.")
                dom_notes.append(f"S0{r['slide']}:ovY={r['overflowY']},minFont={int(r['minBodyPx'])}px")
        else:
            dom_report = []
        checks.append({"name": "dom_layout_and_legibility", "passed": dom_ok, "detail": " | ".join(dom_notes)})

        # 5. Section 11 Typography Anti-Patterns check
        anti_audit = audit_typography_anti_patterns(spec, dom_typography_report=dom_report)
        checks.append(
            {
                "name": "typography_anti_patterns",
                "passed": anti_audit["passed"],
                "detail": (
                    "0 anti-patterns triggered"
                    if anti_audit["passed"]
                    else "; ".join(f"{t['rule']}: {t['detail']}" for t in anti_audit["triggered"])
                ),
                "triggered": anti_audit["triggered"],
            }
        )
        if not anti_audit["passed"]:
            for t in anti_audit["triggered"]:
                revisions.append(f"Anti-pattern Section 11 ({t['rule']}): {t['detail']}")

        # 6. P8: Comprehensive `typography_system` audit (role separation, >=32px floor, scale hierarchy, §11 clean)
        td = spec.get("typography_direction") or (spec.get("creative_direction") or {}).get("typography_direction") or {}
        tc = td.get("typeface_categories") or {}
        roles_assigned = bool(tc.get("display") and tc.get("supporting") and tc.get("metadata"))
        roles_distinct = len({str(tc.get("display", "")).lower(), str(tc.get("supporting", "")).lower()}) >= 2
        body_sizes = [float(r.get("minBodyPx", MOBILE_BODY_FONT_FLOOR_PX)) for r in dom_report] or [float(MOBILE_BODY_FONT_FLOOR_PX)]
        headline_sizes = [float(r.get("headlineSize", 0)) for r in dom_report if float(r.get("headlineSize", 0)) > 0]
        min_body_overall = min(body_sizes)
        font_floor_ok = min_body_overall >= MOBILE_BODY_FONT_FLOOR_PX
        scale_ratio = round((max(headline_sizes) / max(min_body_overall, 1.0)), 2) if headline_sizes else 2.0
        scale_hierarchy_ok = scale_ratio >= 1.35 and (len(set(round(s) for s in headline_sizes)) >= 2 if len(headline_sizes) >= 2 else True)
        typo_sys_ok = roles_assigned and roles_distinct and font_floor_ok and scale_hierarchy_ok and anti_audit["passed"]
        checks.append(
            {
                "name": "typography_system",
                "passed": typo_sys_ok,
                "detail": (
                    f"roles={tc.get('display')}/{tc.get('supporting')}/{tc.get('metadata')} | "
                    f"minBody={int(min_body_overall)}px (>={MOBILE_BODY_FONT_FLOOR_PX}px) | "
                    f"scaleRatio={scale_ratio}x | antiPatterns={anti_audit['triggered_count']}"
                ),
            }
        )
        if not typo_sys_ok:
            revisions.append(
                f"Perbaiki typography_system (roles_assigned={roles_assigned}, roles_distinct={roles_distinct}, "
                f"minBody={min_body_overall}px, scaleRatio={scale_ratio}x)."
            )

        # 7. Guardrails: No unsolicited sales CTA, formal caption_voice check (P7), & max 1 Alan mention
        allow_sales = bool(spec["project"].get("allow_sales_cta"))
        all_slides_text = json.dumps(spec.get("slides") or [], ensure_ascii=False).lower()
        cap_raw = spec.get("caption") or ""
        cap_text = cap_raw.lower()
        cta_clean = True
        if not allow_sales:
            for b in BANNED_SALES_CTAS:
                if b in all_slides_text or b in cap_text:
                    cta_clean = False
                    revisions.append(f"Hapus frasa CTA iklan jasa terlarang: '{b}'.")

        expected_voice = select_caption_voice(
            spec["project"].get("industry", ""),
            spec["project"].get("brand_name", ""),
            override=spec["project"].get("caption_voice"),
        )
        voice_clean = True
        if expected_voice == "formal_editorial" and CASUAL_SLANG_PATTERN.search(cap_raw):
            voice_clean = False
            revisions.append("Caption industri formal/klinis mengandung slang kasual ('gw/lo').")

        alan_count = len(re.findall(r"\balan\b", cap_raw, flags=re.IGNORECASE))
        alan_ok = alan_count <= 1
        if not alan_ok:
            revisions.append(f"Caption menyebut Alan {alan_count} kali (maksimal 1).")

        checks.append(
            {
                "name": "showcase_guardrails",
                "passed": cta_clean and voice_clean and alan_ok,
                "detail": f"sales_cta_free={cta_clean}, caption_voice={expected_voice} (ok={voice_clean}), alan_mentions={alan_count}",
            }
        )

        passed_count = sum(1 for c in checks if c["passed"])
        score = int(round((passed_count / max(1, len(checks))) * 100))
        status = "PASS" if all(c["passed"] for c in checks) else "NEEDS_REVISION"

        report = {
            "status": status,
            "score": score,
            "passed_checks": passed_count,
            "total_checks": len(checks),
            "checks": checks,
            "warnings": warnings,
            "revisions": revisions,
        }
        (out_dir / "qa_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        return report
