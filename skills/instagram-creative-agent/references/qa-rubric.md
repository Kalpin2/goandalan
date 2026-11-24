# Design Reviewer QA Rubric (`design_reviewer.py`)

Every rendered carousel is automatically evaluated and logged into `qa_report.json`:

1. **`composition_variety`**: At least 3 distinct composition patterns across the 4 slides (prevents monotonous 4-identical-boxes templates).
2. **`wcag_contrast`**: Primary ink on background and surface must meet WCAG 2.1 AA (`>= 4.5:1`).
3. **`output_pngs_4x5`**: All 4 separate slides defined in `spec["slides"]` (flexible naming per `§9`, e.g., `01_cover.png`..`04_details.png` or `01_reveal.png`..`04_experience.png`) exist at exact `1080x1350` or `2160x2700` (4:5 portrait).
4. **`contact_sheet_2x2`**: `contact_sheet.png` (2×2 labeled review grid) exists alongside `cover_grid.png` (3:4 profile grid crop simulation).
5. **`dom_layout_and_legibility`**: Live Playwright check confirming zero horizontal/vertical overflow (`<= 4px`), zero broken images, no severe screenshot aspect-ratio clipping, and readable mobile body font floor (`>= 32px` at `1080px` 1x canvas, preventing `< 6px` unreadable text on phone screens).
6. **`typography_anti_patterns`**: Enforces `§11` of `typography_intelligence_library.md` (zero repeated identical headline across all 4 slides, zero serif-italic-only clichés, zero meaningless mono fillers, zero fake metrics, zero 4-centered-card uniform decks).
7. **`typography_system`**: Audits the complete 4-layer typographic system — distinct role separation (`display` / `supporting` / `metadata`), enforced mobile body font floor (`>= 32px` @ 1x), intentional scale hierarchy (`headline / body >= 1.35x` with cross-slide size variation), and zero `§11` anti-patterns.
8. **`showcase_guardrails`**: Zero banned sales/agency CTA phrases on any slide or in `caption.txt` (unless `allow_sales_cta: true`), formal `caption_voice` compliance (zero `"gw/lo"` slang on clinical/legal/finance/B2B brands), and at most 1 mention of `Alan` in `caption.txt`.
