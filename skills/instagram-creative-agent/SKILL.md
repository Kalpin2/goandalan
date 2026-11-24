---
name: instagram-creative-agent
description: Adaptive 4-slide IG website showcase creative agent.
---

# Instagram Creative Agent (Adaptive Website Showcase)

Modular 4-role creative agent for designing, planning, rendering, and QA-reviewing **4-slide Instagram website showcase carousels** (`1080x1350px` @2x → `2160x2700px`) with a **2×2 Contact Sheet** preview.

**Core Domain Spec:** `D:\goandalan\carousel_design_system_website_showcase.md`  
**Local Engine:** `D:\goandalan\creative_agent\` (100% local Playwright HTML/CSS → PNG, zero paid APIs).

---

## 1. The 4 Modular Roles

1. **Creative Director (`creative_director.py`):** Analyzes business industry, audience, and goal; audits available assets (`Available` / `Missing` / `Optional` / `Assumption`); extracts color palettes from reference images/logos; selects a 4-layer `typography_direction` (`typography_engine.py`) and recommends **2–3 meaningfully distinct visual concepts** from the **12-style library**.
2. **Carousel Planner (`carousel_planner.py`):** Builds flexible 4-slide storyboards per `§9` (default `01_cover`..`04_details` or adaptive sequences like `reveal_first` / `story_led`), adapts `caption_voice` (`formal_editorial` for clinical/legal/finance/B2B vs `casual_gw` for indie/creative), enforces strict honesty, and writes editable `carousel_spec.json`.
3. **Visual Designer (`visual_designer.py`):** Renders 4-layer graphic campaign + actual website slides using local Playwright Chromium + Indonesian-safe Google Fonts (`>= 32px` mobile body floor on `1080px` canvas), outputs 4 separate `2160x2700` PNGs + `contact_sheet.png` (2×2) + `cover_grid.png` (3:4 profile crop preview).
4. **Design Reviewer (`design_reviewer.py`):** Audits DOM overflow, WCAG contrast (`>= 4.5:1`), `typography_system` (role separation, `>= 32px` floor, scale contrast, §11 anti-patterns), composition variety, and strict guardrails (zero unsolicited sales CTAs, formal `caption_voice`, max 1 mention of Alan) → writes `qa_report.json`.

---

## 2. Interactive 9-Step Workflow (Mandatory in `agy` CLI / Chat Sessions)

Never jump straight to rendering PNGs during an interactive session. Follow this exact gate:

1. **Analyze Business:** Extract brand name, industry, target audience, website goal, personality, and project status (`live` / `prototype` / `concept` / `demo`). Do not re-ask already provided info.
2. **Audit Assets:** List `Available`, `Missing`, `Optional`, and `Assumption`.
3. **Recommend 2–3 Distinct Concepts:** Choose meaningfully different styles & storytelling methods from `references/12-styles-matrix.md` (never just color swaps of one template).
4. **Explain Art Direction:** Present primary + secondary style, storytelling method, palette (including extracted reference palette if provided), typography, and 4-slide composition plan.
5. **Present 4-Slide Storyboard:** Display the `01`–`04` storyboard table + 3 headline options + save draft `carousel_spec.json` via:
   ```powershell
   python -m creative_agent.cli plan --brand "<Brand>" --industry "<Industry>" --html "<path/to/demo.html>" --out "<output_dir>"
   ```
6. **Ask Only Relevant Missing Info:** Ask 1–4 brief clarifying questions ONLY if missing information affects the design. Skip if the brief is already complete.
7. **Wait for User Approval (Hard Gate):** Ask whether the creative direction and storyboard look right or need changes before rendering.
8. **Apply Targeted Revisions:** When the user requests tweaks, patch ONLY the changed parts without restarting discovery:
   ```powershell
   python -m creative_agent.cli revise --spec "<output_dir>/carousel_spec.json" --style <style_key> --headline-1 "<new headline>"
   ```
9. **Render Final Slides + Contact Sheet + QA (After Approval Only):**
   ```powershell
   python -m creative_agent.cli render --spec "<output_dir>/carousel_spec.json" --out "<output_dir>"
   ```
   *(Single-slide re-roll: add `--only 2`.)*  
   Present the rendered file paths, `contact_sheet.png`, and `qa_report.json` summary.

---

## 3. Hard Guardrails

* **NEVER** auto-publish to Instagram or auto-send DMs. Always hand off PNGs + `contact_sheet.png` + `caption.txt` for manual human publishing.
* **NEVER** place unsolicited agency/sales CTAs (e.g., *"DM sekarang untuk buat website"*, *"Hubungi kami"*) on Slide 4 or hard-sell in `caption.txt`. Use neutral showcase closings (*"Inside the experience"*, *"Explore the interface"*, *"A closer look"*, *"Designed around the brand"*, *"Website concept"*).
* **NEVER** invent ratings, customer counts, testimonials, statistics, or features absent from the HTML demo / brief.
* **ALWAYS** keep real website screenshots legible and unobstructed — zero decorative clutter covering UI.
* **Dual-Mode Pipeline Safety:** For non-interactive `@goandalan` Mini App / batch runs, `carousel_generator.py` (4:5 carousel) and `reels_generator.py` (9:16 30fps Reels via `reels_capture.py`, `reels_motion.py`, `reels_plates.py`, `reels_compose.py`, `reels_qa.py`) invoke `creative_agent` automatically without blocking for user input, enforcing the same typography/copy libraries, IG safe zones (`x:64–960`, `y:290–1580`), `>= 32px` font floor, and `check_anonymization_leak` checks (see `D:\goandalan\docs\REELS_ENGINE_AUDIT.md`).

## 4. Reference Files (Read According to Stage)

* `references/typography_intelligence_library.md` — **Mandatory pre-plan read.** Core 4-layer typographic intelligence (typeface classifications with Indonesian anchor fonts, 30 art directions, treatments, compositions, §11 anti-patterns, and §15 self-expansion rules).
* `references/style_library_map.md` — **Read during concept selection & style bridging.** Exact crosswalk mapping the 12 `style_registry.py` keys ↔ 30 art directions (§3 `#1`–`#30`) ↔ 44 operational library entries.
* `references/12-styles-matrix.md` — **Read during concept discovery.** Summary of the 12 visual styles, 10 storytelling methods, and 8-style `demo_generator.py` bridge.
* `references/spec-schema.md` — **Read during planning & targeted revision.** Editable `carousel_spec.json` structure & CLI revision flags.
* `references/qa-rubric.md` — **Read before & after rendering.** Automated `design_reviewer.py` checks (`typography_system`, `>= 32px` mobile font floor, WCAG contrast, guardrails) and pass thresholds.
* `references/learning_log.md` — **Append-only after every QA-reviewed carousel.** Chronological log of completed carousels, triggered anti-patterns, and §15 learning cycles.
* `references/library_candidates.md` — **Read/append during §15 gap cycles.** Holds unapproved typographic candidates (`status: candidate | tested | retired`, `review_by`, `approved_by_user: false`); never auto-merge into core library without explicit user approval.
* `references/copy_intelligence_library.md` — **Mandatory pre-draft read for all copy.** 5-layer copy system (Client Profile, Voice `V1`–`V6`, Persuasion Levers `L1`–`L7`, Structure, Channel), hard-fail validator (§10.1), variation control (§11), and learning protocol (§12), wired to `creative_agent/copy_engine.py`.
* `references/copy_candidates.md` — **Read/append during §12 copy learning cycles.** Holds unapproved copy pattern candidates (`status: candidate | testing | retired`, `approved_by_user: false`) used under the 20% exploration budget on regular-priority leads.
* `references/copy_learning_log.md` — **Append-only copy learning log (§12.2).** Records `original_draft`, human-edited `final_text`, `edit_summary`, pattern IDs, and automatic lead outcomes (`interested` / `ignored_48h`); strictly anonymized for recycled captions.
