# Editable Spec Schema (`carousel_spec.json`) & CLI Commands

## Core CLI Flow (`cwd = D:\goandalan`)

```powershell
# 1. List all 12 styles
python -m creative_agent.cli styles

# 2. Plan & audit (writes carousel_spec.json + storyboard.md, zero PNG render)
python -m creative_agent.cli plan --brand "Kopi Sore" --industry "Coffee Roastery" --html site/demos/kopi-sore/index.html --out output/kopi-sore

# 3. Targeted revision (edits only specified fields without restarting)
python -m creative_agent.cli revise --spec output/kopi-sore/carousel_spec.json --style cinematic_premium --headline-1 "Seduhan malam <em>Kopi Sore.</em>"

# 4. Render 4 separate PNGs + 2x2 contact_sheet.png + cover_grid.png + qa_report.json
python -m creative_agent.cli render --spec output/kopi-sore/carousel_spec.json --out output/kopi-sore

# 5. Single-slide re-render after a minor edit
python -m creative_agent.cli render --spec output/kopi-sore/carousel_spec.json --out output/kopi-sore --only 2
```

## Key Top-Level Fields in `carousel_spec.json`
- `project`: `brand_name`, `industry`, `city`, `domain`, `project_status`, `issue_num`, `handle`, `caption_voice` (`formal_editorial` | `casual_gw`), `slide_sequence`, `allow_sales_cta` (default `false`)
- `creative_direction`: `style_key`, `primary_style`, `secondary_style`, `storytelling_key`, `palette`, `fonts`, `geometry`, `compositions`, `closing_label`
- `typography_direction`: 4-layer Section 12 schema (`typeface_categories`, `brand_personality`, `primary_art_direction`, `typographic_treatments`, `composition_behavior`, `gap_signal`)
- `assets`: `desktop_screenshot`, `mobile_screenshot`, `desktop_detail`, `mobile_detail`, optional `logo`, `reference_image`
- `slides[]`: 4 flexible objects (`n: 1..4`, `name`, `kind`: `poster|story|reveal|details`, `role`, `composition`, `kicker`, `headline_html`, `subhead`, slide-specific visuals & verified callouts)
- `caption`: adaptive `caption_voice` copy (`formal_editorial` with zero `"gw/lo"` slang for formal/clinical sectors; `casual_gw` for indie/creative brands; max 1 mention of Alan, zero hard-selling CTA)
