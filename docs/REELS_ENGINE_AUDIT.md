# GoAndalan Reels Engine — Audit, Compatibility & Integration Design

_Scope: upgrade the existing Python + Playwright + Pillow + FFmpeg Reels system in `D:\goandalan`. No React/Node stack, no second rendering engine._

## 1. Existing-system discovery (before changes)

| Layer | Files | What it did |
|---|---|---|
| Orchestration | `reels_generator.py` (`generate_reels_package_for_lead`) | Concept HTML → screenshots → 4 static HTML plates → crossfaded slideshow with one scrolling phone → FFmpeg MP4 (24 fps) + cover + caption + QA. |
| Capture | `_capture_reels_source_screenshots` | One full-page mobile screenshot (390×844 @2x), one desktop hero. No lazy-image sweep, no interaction capture, no section awareness. |
| Visual intelligence | `creative_agent/niche_resolver.py`, `typography_engine.py`, `style_registry.py` (12 styles, 30 art directions, 4-layer `typography_direction`), `creative_director.py`, `visual_designer.py` | Category → goal → section architecture → palette/fonts. Reused untouched. |
| Copy intelligence | `creative_agent/copy_engine.py`, `copy_intelligence_library.md` | V1–V6 voices, `HOOK-*`, formal anti-slang guard, disclosure, learning log. Reused untouched. |
| QA | `design_reviewer.py` (carousel), inline 3-check Reels QA | Reels QA only checked "mp4 exists / cover exists / no sales CTA". No safe-zone, audio, black-frame or leak checks. |
| Workflow | `app.py`, `database.py`, `content_review.py`, `templates/mini_app.html` | Tab 2 `/recycle` → Tab 4 `draft_brief` → `POST /api/content/{id}/generate` → `pending_review` → `approved` → `posted`, vN snapshots, `check_anonymization_leak`, admin vs reviewer RBAC. **Contract preserved.** |

Weak points found: plates ignored IG safe zones (text at y=112 / y>1780, 22–26 px labels, phone to y=1636); `before_after_ux` and `kinetic_editorial` were only a kicker-text change over the same 4 plates; no kinetic typography (static plates + crossfade); linear-ish single scroll with no reading holds; no real interaction; `silent` mode emitted no audio stream; 24 fps; ffmpeg stderr pipe was unread (Windows deadlock risk — fixed earlier).

## 2. External repositories — security gate & findings

Mandatory gate: `skillspector scan <url> --no-llm --format json` **before** any clone/install. Nothing was cloned or installed. For repos whose scan could not complete, metadata, license and SKILL.md/README text were read **read-only over HTTPS** (GitHub API / raw files) — no code executed.

| # | Repository | SkillSpector result | License | Verdict |
|---|---|---|---|---|
| 1 | HyperFrames (`heygen-com/hyperframes`) | **Scan incomplete** — `Transitive git ingest truncated (byte_budget_exhausted)`; no report produced (repo ≈ 555 MB / 12.4k files) | Apache-2.0 | **NOT CLONED** (gate not passed). Concepts only (see §4). |
| 2 | Herk Edit Kit (`nateherkai/herk-edit-kit`) | **Scan incomplete** — `time_budget_exhausted` | MIT | **NOT CLONED**. Concepts only (storytelling/motion doctrine). |
| 3 | Remotion skills (remotion.dev/skills) | n/a (web docs) | — | Reference only; React/Node stack explicitly **not** adopted. |
| 4 | OpenMontage (`OpenMontageInc/OpenMontage`) | **Scan incomplete** — `byte_budget_exhausted` | **AGPL-3.0** | **SKIP** — copyleft network clause is incompatible with a commercial agency tool; heavy provider/GPU stack. |
| 5 | OpenFilm (`openfilm/openfilm`) | **Scan incomplete** — `byte_budget_exhausted` | MIT | **NOT CLONED** — Electron/TypeScript monorepo + desktop editor; duplicates our renderer. |
| 6 | Video Use (`browser-use/video-use`) | **CRITICAL** (score 100, `DO_NOT_INSTALL`; 1 CRITICAL `TT3` in `helpers/transcribe.py`, 11 HIGH) | — | **UNAVAILABLE / SKIP** (fails triage). |
| 7 | Video 3D Kit (`artosku/video-3d-kit`) | **HIGH ×140**, `DO_NOT_INSTALL` (score 90; coverage 16 %) | — | **UNAVAILABLE / SKIP** (fails triage; Three.js 3D is out of scope). |

No registry/`AGENTS.md` entry was added for external repos because none were adopted.

### Capabilities studied (read-only) and re-implemented natively
* **HyperFrames skills** (`motion-doctrine`, `cut-the-curve`, `seam-craft`): velocity-matched seams, *waterfall* staggered entry, slow-fast-slow *nudge* (10/65/25), power4 eases, opaque stage ground (no white flash at seams). → Re-implemented as `reels_motion.py` easings, `waterfall_progress`, `nudge_curve`, opaque plates.
* **Herk Edit Kit** (`video-storytelling`, `MOTION_PHILOSOPHY.md`, `website-to-hyperframes`): one idea per beat (~1.5 s scenes), motion must perform (no idle wobble), capture-then-compose workflow with gates. → 5 scenes/Reel, no decorative wobble, capture/compose/QA split into modules with a QA gate.
* **Remotion skills**: timing/easing vocabulary only.
* **OpenMontage**: audio/QA ideas (sync, black-frame checks) — implemented independently with `ffprobe`/`ffmpeg` filters.

## 3. Compatibility & duplication matrix

| Capability | Existing | Candidate pattern | Decision |
|---|---|---|---|
| Kinetic typography | None (static plates) | HyperFrames waterfall entry / Herk word beats | **ADD** (native Pillow compositor: per-word eased entry from a transparent text layer) |
| Website scroll capture | single full-page PNG | HyperFrames capture / Video Use | **ADAPT** → `reels_capture.py` (fonts + lazy images settle, section offsets, DPR 2/3, config object) |
| Mobile interaction demo | none | Video Use | **ADD** (only real DOM tabs / CTA; tap ring drawn over real screenshots; never invented) |
| Before/After UX transition | kicker text only | Herk / HyperFrames seams | **ADAPT** (generic-pattern illustration → eased wipe → real site; never claims a real business has the flaw) |
| Motion & easing presets | one cubic | Remotion / HyperFrames curves | **MERGE** → `reels_motion.py` (10 easings, nudge, 3 motion profiles by style/category; formal categories never overshoot) |
| On-screen captions | Pillow/HTML plates | Herk karaoke captions | **KEEP** HTML plates (typography library fonts); **ADD** safe-zone + ≥32 px floor |
| Audio / timing sync | edge-tts + synth ambient + amix | OpenMontage | **KEEP**; **ADAPT**: `atempo` fit, silent-safe AAC for `silent`, `-t` hard cut, duration derives from VO |
| Render / encode | PIL → FFmpeg pipe | HyperFrames (Node/Chromium), Remotion (React) | **KEEP** (30 fps, CRF 20, `yuv420p`, `+faststart`); **SKIP** external renderers |
| Cover | copy of hook plate | skills | **ADAPT**: 1080×1920, all text inside 4:5 center crop (y285–1635) |
| Safe-zone / visual QC | none for Reels | OpenMontage QA | **ADD** → `reels_qa.py` |
| Storytelling & hooks | `copy_engine` + library | Herk storytelling | **KEEP** engine; **ADAPT** story beats per sequence (A/B/C) |
| 3D / AI video generation | — | Video 3D Kit, OpenMontage | **SKIP** |

Duplications removed: the old 350-line inline HTML plate string + inline compositor now live in focused modules; `reels_generator.py` stays the orchestrator.

## 4. Integration architecture (smallest modular upgrade)

```
reels_generator.py  (orchestrator — signatures & output files preserved)
 ├─ reels_capture.py   CaptureConfig + capture_site(): 390×844 @2x/3x, fonts+lazy-image settle, tall page,
 │                     hero, section tops, real CTA highlight pair, real tab-switch pair, desktop hero
 ├─ reels_plates.py    render_plate_set(): safe-zone plates from the typography library; `base`+`layer` PNGs
 │                     for kinetic/staggered items; DOM audit (text boxes, min font)
 ├─ reels_motion.py    easings, waterfall, nudge, scroll plan, motion profiles, SAFE_ZONE/PHONE geometry
 ├─ reels_compose.py   SceneComposer: per-sequence 5-scene plan → frames (reveal/zoom/phone/feature, wipe/crossfade)
 └─ reels_qa.py        ffprobe/ffmpeg + DOM-audit + guardrail + leak QC → qa_report.json
```
Contracts kept: `generate_reels_package_for_lead(...)` signature (only optional kwargs added), `POST /api/content/{id}/generate`, outputs `reels.mp4`, `cover_reels.png`, `caption.txt`, `qa_report.json`, `reels_spec.json`; `beat_script` item shape unchanged (now 5 beats). RBAC, `check_anonymization_leak` and Tab 4 flow untouched.

### Storytelling structures (5 beats each)
* **A `scroll_reveal_showcase`**: kinetic hook → hero reveal (push-in) → controlled eased scroll with section holds → real feature demo (tab tap or CTA highlight) → neutral closing.
* **B `before_after_ux`**: kinetic "pola umum" problem (from sanitized `ux_flaw`, framed as a generic pattern) → generic cramped-mobile illustration (labelled *ilustrasi umum*) → wipe to the real concept site → real interaction → closing.
* **C `kinetic_editorial`**: oversized hook → one design insight → 3 real UI crops (modular grid, staggered) → rhythmic slow-fast-slow scroll bursts → closing statement.

### Quality & policy decisions
* **Safe zone** (px @1080×1920): x 64–960, y 290–1580 (clears IG top overlay, right rail and caption/audio bar; also inside the 4:5 grid crop 285–1635). Font floor 32 px (illustration wireframe exempt).
* **CTA policy**: the brief asks for a "closing CTA", but `AGENTS.md` forbids service-ad CTAs in showcase content. Resolution: the *website's own* CTA is demonstrated (real), and the closing is a neutral showcase line (`Website Concept · @goandalan`).
* **Audio**: `silent` now ships a silent AAC track (IG-safe, keeps unmute control, user can still add IG music); other modes unchanged. `atempo` (≤1.3) fits long voice-overs; duration 8–12 s (`REELS_DURATION_SEC`, default 10).
* **Anonymization**: problem text is sanitized (`_sanitize_ux_flaw_for_brief`), all on-screen text + caption are passed through `check_anonymization_leak` inside the QA report.

## 5. Licensing
No third-party code was copied. Ideas from Apache-2.0 / MIT docs are re-implemented from scratch (attribution recorded in `reels_motion.py` and README). OpenMontage (AGPL-3.0) deliberately not used. Fonts come from the existing typography library (Google Fonts, OFL). Procedural target BGM tracks (`assets/bgm/*.wav`) are synthesized in-process (100% royalty-free); voice-over uses `edge-tts` (neural TTS; review Microsoft terms before commercial monetization of narrated content).

## 6. Adaptive Reels Engine v2 Upgrade (Overnight Integration)
* **Content Role Separation:**
  * `POST /api/leads/{id}/recycle` (Tab 2) is locked to creating `draft_brief` items with `content_format = "carousel"` (4:5 showcase grid focus).
  * `POST /api/content/reels-ideas/scrape` (Tab 4) creates `draft_brief` items with `content_format = "reels"` focused on **Attract Customer** real Indonesian UMKM pain points (`PAIN-WA`, `PAIN-TRUST`, `PAIN-BOOKING`, `PAIN-ADS`, `PAIN-MOBILE`, `REEL-HOOK-*`) via read-only `agent-reach` (`web/youtube search` + `token_optimizer.compact_scrape_text`, `<= 700` chars/source, `<= 4` sources, `<= 25s` timeout) with an offline Indonesian UMKM pain bank fallback.
* **Adaptive Indonesian V/O + Word-Synced Kinetic Captions:**
  * `creative_agent/reels_intelligence.py` routes formal/health/professional categories (`clinic`, `pilates`, `legal`, `b2b`) to polite-calm Bahasa Indonesia with 0 slang (`id-ID-GadisNeural` / calm `id-ID-ArdiNeural`) and casual/creative niches (`cafe`, `bakery`, `barbershop`, `automotive`, `retail`) to warm-natural `id-ID-ArdiNeural`.
  * `edge-tts` stream captures `WordBoundary`/`SentenceBoundary` timestamps (timeout `<= 30s`, proportional fallback when offline) and `reels_compose.py` overlays crisp kinetic captions strictly inside the IG safe zone (`x: 64–960`, `y: 290–1580`).
* **Procedural Target-Matched BGM + FFmpeg `sidechaincompress` Ducking:**
  * 3 loop-safe 15s royalty-free WAV tracks under `assets/bgm/` (`calm_editorial.wav`, `warm_hospitality.wav`, `energetic_craft.wav`) plus auto-discovery for custom `.mp3`/`.wav` tracks.
  * Mixed with V/O using FFmpeg `sidechaincompress` (BGM smoothly ducks while narrator speaks and rises on pauses), supporting 12–15s Attract Customer pacing (`reels_qa.py` target range `8.0–15.5s`) and CTA screen `DM kata KONSEP`.
* **Token-Efficient Self-Learning:**
  * Editable V/O scripts in Tab 4 diffed at 0 LLM tokens (`token_optimizer.compute_edit_delta` → `reels_learning_log.md`), paired with `POST /api/content/{lead_id}/metrics` (`Views`, `Saves`, `Shares`, `DM Masuk`) and `POST /api/learning/evaluate` → `learning_digest.json` (`<= ~1,200` tokens).

