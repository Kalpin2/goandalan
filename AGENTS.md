# AGENTS.md — @goandalan Master Agent Instructions

Dokumen ini menjadi pintu masuk utama aturan kerja untuk seluruh AI agent (termasuk **Alan**) yang bekerja di workspace `D:\goandalan`.

## 1. Dokumen Panduan Wajib

1. **[go_alan_master_ig_agent_operating_manual.md](./go_alan_master_ig_agent_operating_manual.md)** — Identitas brand `@goandalan` ("gw sama alan"), dinamika karakter Gw vs. Alan, aturan Cold DM tanpa link di pesan pertama, dan human approval gates.
2. **[agents_md_modul_produksi_konten_goandalan.md](./agents_md_modul_produksi_konten_goandalan.md)** — Spesifikasi produksi konten (Carousel, Reels, Beat-Sync, QA teknis, anonimisasi).
3. **[carousel_design_system_website_showcase.md](./carousel_design_system_website_showcase.md)** — **Panduan WAJIB** untuk seluruh perancangan dan rendering carousel Instagram *website showcase* (Adaptive Website Showcase).
4. **[skills/instagram-creative-agent/references/copy_intelligence_library.md](./skills/instagram-creative-agent/references/copy_intelligence_library.md)** — **Panduan WAJIB** untuk seluruh penulisan copy (Instagram Caption, Cold DM #1, Follow-Up 48 jam, dan Cold Call Script) melalui `creative_agent/copy_engine.py` (pre-routing voice `V1`–`V6`, rotasi 10 output terakhir §11, 20% exploration budget, hard-fail validator §10.1, dan pencatatan `copy_learning_log.md` + `copy_candidates.md`).
5. **`D:\AI WORKSPACE\repos\Panniantong-Agent-Reach\agent_reach\skill\SKILL.md`** — Referensi skill read-only **`agent-reach`** (diinstal terisolasi di `D:\AI WORKSPACE\tools\Agent-Reach\.venv`) yang disambungkan via `creative_agent/lead_enricher.py` untuk riset `ux_flaw` website & `ig_observation` prospek `NEW` pasca-scrape. **ATURAN KERAS:** mode baca/search saja, **DILARANG** login atau menyalin sesi akun utama `@goandalan` (wajib akun riset terpisah bila mengaktifkan login channel `instagram`).

---

## 2. Alur Pembuatan Demo & Produksi Website (3 Fase — 10 Status `leads` Tetap)

Seluruh pipeline (`demo_generator.py`, `app.py`, `templates/mini_app.html`) wajib mematuhi aturan 3 fase berikut **tanpa menambah atau mengubah 10 status valid di `database.py`** (`NEW`, `CONCEPT_READY`, `CONTACTED_DM`, `CONTACTED_CALL`, `IGNORED_48H`, `INTERESTED`, `FULL_DEMO_READY`, `DP_PAID`, `WON`, `RECYCLED_CONTENT`):

1. **Pre-INTERESTED (`NEW` → `CONCEPT_READY` → `CONTACTED_DM` / `CONTACTED_CALL`):**
   * **DILARANG** meng-generate HTML landing page (`site/demos/<slug>/index.html`) sebelum prospek merespons `INTERESTED` (endpoint `POST /api/leads/{id}/full-demo` mengembalikan HTTP `409` untuk status pre-INTERESTED).
   * Cukup siapkan metadata prospek (default `auto_generate=False`) dan/atau aset ringan Tahap A (`concept.html` / `concept_preview.png`) secara opsional bila dibutuhkan untuk antrean Cold DM.
2. **Prospek `INTERESTED` → `FULL_DEMO_READY` (Demo Landing Page 1-Halaman Pre-DP):**
   * Jalankan `POST /api/leads/{id}/full-demo` (`production=False`, default) atau `python demo_generator.py --slug <slug> --mode full` untuk menghasilkan **single-page landing page demo yang ringkas dan cepat di-render**: **Hero + Ringkasan Layanan/Menu Utama (`#layanan`) + Info Lokasi/Jam, FAQ Ringkas (`#faq`) & Tombol Kontak WA (`#kontak`)**, tetap memakai styling anti-slop sesuai Niche-to-Goal dan floating badge `preview konsep oleh @goandalan · mikir bareng alan`.
   * Kirim link demo 1-halaman ini via DM/WA sambil menanyakan detail *requirement* klien (daftar menu/layanan final, foto asli, jam buka, domain, kebutuhan halaman tambahan).
3. **Setelah `DP_PAID` → Website Produksi Penuh → `WON`:**
   * Setelah DP diterima (`DP_PAID`), bangun **website produksi penuh multi-section** sesuai *requirement* klien melalui Tab 3 (`🚀 Build Website Produksi (Lepas Watermark)` / `POST /api/leads/{id}/full-demo` dengan `{"production": true}` atau `python demo_generator.py --slug <slug> --mode full --production`).
   * Mode produksi otomatis **melepas floating watermark konsep `@goandalan`** dan menyertakan section penuh (`#cerita` Craft & Ruang). Setelah verifikasi final bersama klien, lakukan handoff dan ubah status ke `WON`.

---

## 3. Standar Wajib Produksi Carousel Instagram (Adaptive Website Showcase)

Setiap kali merancang atau merender carousel IG untuk memamerkan website demo, agent **wajib** mematuhi `carousel_design_system_website_showcase.md`:

* **Bukan Satu Template Tunggal:** Gaya visual, palet warna, pairing font, *storytelling method*, dan komposisi 4 slide harus adaptif mengikuti karakter bisnis dan `design_style` website demo (tidak memaksakan background krem `#F6F3EC` untuk semua bisnis).
* **Website sebagai Bintang Utama:** Gunakan screenshot asli dari HTML demo (`desktop`, `mobile`, dan *close-up* section nyata). Jangan menutupi UI dengan dekorasi atau mengganti UI dengan klaim/teks palsu.
* **Variasi Komposisi 4 Slide (`1080x1350px` @2x → `2160x2700px`):**
  * **Slide 1 (Hook / Cover):** Headline spesifik brand + *split composition* atau *editorial typography overlay* dengan potongan hero website asli.
  * **Slide 2 (Context / Concept):** *Photo/direction + interface* atau *asymmetric layout* untuk arah desain & pengalaman pengguna secara ringkas.
  * **Slide 3 (Website Reveal — Porsi Screenshot Terbesar):** *Overlapping devices* (Desktop + Mobile) atau *clean browser window / device-free screenshot* yang tajam & terbaca di layar HP.
  * **Slide 4 (Features / Experience Walkthrough):** *UI close-up / annotated interface* atau *modular grid showcase* bagian nyata dari demo.
* **Konten Demo, Bukan Iklan Jasa:** **DILARANG** menaruh CTA iklan jasa (seperti *"DM sekarang untuk buat website"*, *"Hubungi kami"*) di Slide 4 maupun hard-selling di caption. Gunakan penutup showcase netral (*"Inside the experience"*, *"Explore the interface"*, *"A closer look"*, *"Website concept · @goandalan"*).
* **Akurasi Mutlak:** **DILARANG** mengarang rating, jumlah pelanggan, testimoni, atau fitur yang tidak benar-benar ada di HTML demo.

### Dua Mode Kerja Carousel (`creative_agent/` + Skill `instagram-creative-agent` untuk `agy` CLI)

1. **Mode Interaktif (Art Director Review — Sesi Chat / `agy` CLI):**
   * Skill terpasang di **[skills/instagram-creative-agent/SKILL.md](./skills/instagram-creative-agent/SKILL.md)** (beserta referensi lengkap di `skills/instagram-creative-agent/references/`, termasuk `typography_intelligence_library.md`, `learning_log.md`, dan `library_candidates.md`). Sebelum merancang carousel interaktif di `agy` CLI, agent **wajib** membaca `SKILL.md` tersebut bersama `carousel_design_system_website_showcase.md` dan `typography_intelligence_library.md`.
   * Engine modular berada di `creative_agent/` (`typography_engine.py`, `niche_resolver.py`, `creative_director.py`, `carousel_planner.py`, `visual_designer.py`, `design_reviewer.py`, `cli.py`) mendukung seluruh **12 gaya visual**, **30 art direction tipografi**, **4-layer `typography_direction`**, dan **Self-Expanding Niche-to-Goal Engine**.
   * Agent **wajib** menjalankan alur interaktif 9 langkah: analisis bisnis → audit aset → 2–3 konsep berbeda → jelaskan art direction & 4-layer `typography_direction` → tampilkan tabel storyboard 4 slide & `carousel_spec.json` (`python -m creative_agent.cli plan`) → tanya hanya info kurang → **tunggu persetujuan user** → revisi terarah (`python -m creative_agent.cli revise`) tanpa ulang dari nol → render 4 PNG + **Contact Sheet 2×2** + `cover_grid.png` + `qa_report.json` (`python -m creative_agent.cli render`) → otomatis catat ke `learning_log.md`.

2. **Mode Otomatis Pipeline (`carousel_generator.py` & `reels_generator.py` — Non-Interaktif):**
   * Aktif saat dijalankan lewat Mini App (`app.py`, Tab 4 `Brief / Siap Generate` → `POST /api/content/{id}/generate`), batch generator, atau CLI `python carousel_generator.py`.
   * **Carousel:** Memanggil `niche_resolver` + `typography_engine` + 4 peran `creative_agent/` secara non-interaktif, menghasilkan 4 PNG (`2160x2700px`), `contact_sheet.png` (grid 2×2), `cover_grid.png`, `concept_preview.png`, `caption.txt`, `carousel_spec.json`, `art_direction.json`, `qa_report.json`, serta otomatis mencatat ke `learning_log.md` (dan `library_candidates.md` dengan `status: candidate` bila ada gap — **DILARANG** mempromosikan ke `typography_intelligence_library.md` tanpa persetujuan eksplisit user).
   * **Reels 9:16 (`reels_generator.py` + `reels_capture.py`, `reels_motion.py`, `reels_plates.py`, `reels_compose.py`, `reels_qa.py`):** Menghasilkan `reels.mp4` (`1080×1920`, 30 fps H.264 `yuv420p` + AAC 44.1kHz stereo, 8–12 dtk), `cover_reels.png` (aman crop 4:5), `caption.txt`, `reels_spec.json`, dan `qa_report.json` (18 cek termasuk IG safe zone `x64–960 / y290–1580`, lantai font `>= 32px`, interaksi DOM nyata, dan `check_anonymization_leak`) pada 3 struktur 5-beat (`scroll_reveal_showcase`, `before_after_ux`, `kinetic_editorial`). Detail audit & desain arsitektur terdokumentasi di **[docs/REELS_ENGINE_AUDIT.md](./docs/REELS_ENGINE_AUDIT.md)**.

---

## 4. Self-Expanding Niche-to-Goal & Mandatory Pre-Clone Audit Gate

* **Niche-to-Goal Engine (`creative_agent/niche_resolver.py`):** Setiap prospek baru dipetakan otomatis dari `business_category` → `primary_business_goal` → `website_section_architecture` (anti-slop, tanpa kotak stat `<1 dtk` atau grid card kaku) → `website_visual_theme` → `4-layer typography_direction`.
* **Mandatory Pre-Clone Security Gate (NVIDIA SkillSpector):** Jika kategori/gaya membutuhkan skill yang belum ada di `D:\AI WORKSPACE\obsidian-vault\hermes\MASTER-OBSIDIAN-HERMES\04-REPOSITORIES\REPOSITORY-REGISTRY.md`, jalankan alur **scout (`skill-87`) → audit `D:\AI WORKSPACE\tools\SkillSpector\.venv\Scripts\skillspector.exe` → clone ke `D:\AI WORKSPACE\repos\` (HANYA jika lolos) → update `REPOSITORY-REGISTRY.md` & `FINAL-AUDIT-REPORT.md`**.

---

## 5. Arsitektur Hemat Token & Self-Learning (`creative_agent/token_optimizer.py`)

* **Aturan Wajib Slice-Only Reading:** Agen **DILARANG** membaca file log mentah penuh (`copy_learning_log.md`, `reels_learning_log.md`, `learning_log.md`) ke dalam konteks LLM. Agen **WAJIB** hanya membaca ringkasan padat **`skills/instagram-creative-agent/references/learning_digest.json`** (maksimal ~1.200 token) ditambah potongan pola relevan hasil pre-router Python (`get_relevant_pattern_slice`).
* **Pre-Clean Scrape & Zero-Token Edit Diff:** Seluruh output mentah `agent-reach` wajib dibersihkan lewat `compact_scrape_text` (maks `700` karakter/sumber, maks `4` sumber/batch). Setiap editan manusia pada copy atau Script V/O Reels dihitung secara deterministik via `compute_edit_delta` (**0 token LLM**).
* **Evaluasi Kandidat Terbatas:** Endpoint `POST /api/learning/evaluate` memperbarui `learning_digest.json` secara deterministik dan mengusulkan maksimal **3 kandidat baru** (`status: candidate`, `approved_by_user: false`) ke `copy_candidates.md` / `reels_candidates.md` tanpa pernah auto-promote.
* **Pemisahan Peran Konten IG:**
  * **Carousel (`4:5`)** via `POST /api/leads/{id}/recycle` (Tab 2) → khusus pamer hasil desain website.
  * **Reels (`9:16`)** via `POST /api/content/reels-ideas/scrape` (Tab 4) → khusus *Attract Customer* berbasis masalah nyata UMKM (`PAIN-*`, `REEL-HOOK-*`, V/O adaptif `edge-tts`, BGM procedural target `assets/bgm/` dengan FFmpeg `sidechaincompress` ducking, dan CTA `DM kata KONSEP`).

---

## 6. 4 Pilar Project Goals `@goandalan` (Panduan Utama Agen)

1. **Validasi Pasar (`DP_PAID`) dengan Modal Rp 0:** Scrape → Kurasi & *IG Observation* → Foto Preview tanpa link → `INTERESTED` → Demo Penuh 1-Halaman → `DP_PAID` → Website Produksi → `WON`.
2. **Aktivasi Etalase Feed `@goandalan` & Ritme Outreach Harian:** Upload 6 portofolio awal (pin 3 gaya kontras) + konsisten kirim 3–5 Cold DM personal/hari.
3. **Menghidupkan *Self-Learning* Hemat Token dari Sinyal Nyata:** Kumpulkan minimal 20 sampel interaksi lapangan (editan sebelum **Salin**, rasio balasan `INTERESTED`/`IGNORED_48H`, koreksi Reviewer, dan metrik postingan IG `Views`/`Saves`/`Shares`/`DM Masuk`) ke `learning_digest.json`.
4. **Memutar *Zero-Waste Content Flywheel*:** Carousel (`4:5`) pamer website dari prospek 48 jam + Reels (`9:16`) V/O & BGM adaptif dari masalah nyata bisnis di media sosial.

> **Keputusan Deploy Publik (`site/`):** **Deploy website katalog publik `site/` DITUNDA** hingga pengecekan manual user dan fase validasi outreach awal berjalan. Jangan men-deploy `site/` ke hosting publik atau menjalankan server/tunnel secara permanen tanpa instruksi eksplisit user.

---

## 7. Hard Guardrails

* **DILARANG** auto-post ke Instagram atau auto-send DM.
* **DILARANG** mengarang metrik performa, rating, atau testimoni klien (termasuk kotak slop `<1 dtk AKSES HP`).
* **DILARANG** mempromosikan kandidat di `library_candidates.md`, `copy_candidates.md`, atau `reels_candidates.md` ke library inti (`status: approved`) tanpa persetujuan eksplisit user.
* **DILARANG** membocorkan nama bisnis / nomor WA asli saat `is_anonymized=True` / status `RECYCLED_CONTENT`.
