# @goandalan — Outreach, Demo Pipeline & Review/Publish Mini App

Mobile-first FastAPI + Alpine.js dashboard untuk **@goandalan** (*gw sama alan*) dengan **Full-Screen Login Gate**, **Dark Mode default**, autentikasi berbasis `.env` + cookie `HttpOnly`, dan pemisahan peran **Admin (Dev)** vs **Reviewer (Cold DM, Bisnis & Konten IG)**:

- **Tab 1 (`Outreach`):** Antrean Cold DM (`CONCEPT_READY`) berbasis metadata prospek + foto konsep Tahap A opsional (tanpa HTML landing page sebelum `INTERESTED`), draft Cold DM #1 tanpa link, dan skrip Cold Call.
- **Tab 2 (`Timer 48j`):** Pantau countdown 48 jam (`CONTACTED_DM`/`CONTACTED_CALL` → `IGNORED_48H`), eskalasi `INTERESTED` → **Demo Landing Page 1-Halaman (Pre-DP)**, serta tombol **Daur Ulang ke Konten IG** (`RECYCLED_CONTENT`).
- **Tab 3 (`Pipeline`):** Metrik pipeline, filter prospek aktif (`INTERESTED`, `FULL_DEMO_READY`, `DP_PAID`, `WON`), build **Website Produksi Penuh (Lepas Watermark)** setelah `DP_PAID`, serta Google Maps scraper & tambah prospek manual (khusus Admin).
- **Tab 4 (`Review Konten`):** Alur **Review & Publish** terversi khusus untuk konten hasil daur ulang (`RECYCLED_CONTENT` / `is_anonymized = 1`) dengan perlindungan kebocoran anonimisasi (`check_anonymization_leak`).

---

## Autentikasi, Sesi & Pembagian Hak Akses

### 1. Konfigurasi `.env` (Fail-Closed — Tanpa Password Default)
Salin `.env.example` menjadi `.env` lalu isi keempat variabel kredensial berikut secara lokal (**jangan pernah commit `.env`**, sudah masuk `.gitignore` dan `.envignore`):

```dotenv
IG_USERNAME=goandalan
IG_URL=https://instagram.com/goandalan
BRAND_NAME=gw sama alan
HOST=0.0.0.0
PORT=8000
DB_PATH=leads.db
SITE_DIR=site
FOLLOW_UP_HOURS=48
DEFAULT_CITY=Jakarta

# Kredensial Login (WAJIB diisi di .env lokal — fail-closed bila kosong)
ADMIN_USN=isi_username_admin
ADMIN_PASS=isi_password_admin_kuat
REVIEW_USN=isi_username_reviewer
REVIEW_PASS=isi_password_reviewer_kuat

# Hosting & Keamanan
HTTPS_ENABLED=true
CORS_ALLOWED_ORIGINS=
MAX_UPLOAD_BYTES=15728640
```

### 2. Sesi Cookie `HttpOnly` & Sliding Window 7 Hari
- Login via `POST /api/auth/login` memvalidasi kredensial secara *constant-time* (`hmac.compare_digest`), dilengkapi **rate limit & progressive lockout server-side** (maks 5 gagal / 15 menit → HTTP `429` + `Retry-After`) dan delay konstan pada kegagalan.
- Token sesi (`secrets.token_urlsafe(32)`) disimpan dalam bentuk hash SHA-256 pada tabel `auth_sessions` SQLite dan dikirim melalui cookie `HttpOnly; SameSite=Strict` (`Secure` otomatis saat HTTPS). Tidak ada token di URL query string (`?token=`) maupun password di `localStorage`/`sessionStorage`.
- **Reviewer (`REVIEW_USN` / `REVIEW_PASS`):** Masa berlaku sesi **7 hari (sliding window, `max-age=604800`)** — diperpanjang otomatis tiap aktivitas (throttle 1 jam). Jika tidak aktif > 7 hari, sesi hangus otomatis (`401`) dan halaman login tampil kembali.
- **Admin (`ADMIN_USN` / `ADMIN_PASS`):** Masa berlaku sesi **12 jam (`max-age=43200`)**.
- Form login mendukung *native browser password autofill* (`autocomplete="username"` & `autocomplete="current-password"`).

### 3. Matriks Hak Akses (Server-Side RBAC)

| Peran | Akses Diizinkan | Diblokir (`HTTP 403`) |
| :--- | :--- | :--- |
| **Reviewer** (`REVIEW_USN`) | Dashboard (`/api/dashboard`), kurasi hasil scrape (`NEW` → `CONCEPT_READY` atau tolak/hapus `NEW`/`CONCEPT_READY`), ubah seluruh status Cold DM & deal pipeline (`NEW`, `CONCEPT_READY`, `CONTACTED_DM`, `CONTACTED_CALL`, `IGNORED_48H`, `INTERESTED`, `DP_PAID`, `WON`, `RECYCLED_CONTENT`), seluruh aksi Reviewer Tab 4 (`corrections`, `approve`, download satuan/ZIP, `caption-copied`, `posted`, `comments`) | Scrape (`/api/jobs/scrape`), generate/build website (`/concept`, `/full-demo`, status teknis `FULL_DEMO_READY`), tambah lead manual (`/api/leads`), hapus lead yang sudah melewati `CONCEPT_READY`, aksi dev Tab 4 (`/submit`, `/revise`, `/corrections/{id}/resolve`) |
| **Admin** (`ADMIN_USN`) | Akses penuh pipeline teknis: scrape, tambah lead, render Tahap A, build Demo 1-Halaman Pre-DP & Website Produksi Penuh (lepas watermark), submit/revise v2+ carousel, selesaikan koreksi, komentar | Keputusan editorial khusus Reviewer (`approve`, `corrections`, `posted`, download publish) |
| **Publik** (Tanpa Login) | `/` (Login Gate), `/health`, `/demos/*` (halaman demo prospek, kecuali `/reviews/`), `/portfolio/index.html` | Seluruh `/api/*` (`401`), `/.env`, `/leads.db`, `*.py`, `/skills/`, `/creative_agent/`, `/demos/*/reviews/*` (`403`/`404`) |

---

## Review & Publish Workflow (Tab 4)

State review disimpan di tabel terpisah (`content_reviews`, `content_versions`, `content_corrections`, `content_activity`, `content_comments`) tanpa menambah atau mengubah 10 status valid tabel `leads`:

```text
pending_review ──► approved ──► posted
      │               │
      ▼               ▼
changes_requested ◄───┘
      │
      ▼
   revised ──► approved ──► posted
```

* Snapshot versi disimpan *byte-for-byte* (tanpa rekompresi) di `site/demos/{anon_slug}/reviews/{lead_id}/v{n}/` dan diisolasi dari static route `/demos/*` (hanya dapat diakses lewat endpoint terautentikasi `/api/content/*`).
* Upload gambar revisi memvalidasi ekstensi, ukuran maks, **magic bytes** (`PNG`/`JPEG`/`WebP`), `Path.resolve().is_relative_to()` anti-path-traversal, serta `check_anonymization_leak()` (`HTTP 422` jika data asli bisnis bocor).

---

## Intelligent Reels Production Engine (9:16, 1080×1920, 30 fps)

Modul produksi Reels diorkestrasi oleh `reels_generator.py` dengan arsitektur modular ringan berbasis **Python + Playwright + Pillow + FFmpeg** (tanpa stack React/Node tambahan), terintegrasi penuh dengan `typography_intelligence_library.md`, `copy_intelligence_library.md`, dan Tab 4 (`Brief / Siap Generate` → `POST /api/content/{id}/generate`):

- **`reels_capture.py` (`CaptureConfig`, `capture_site`):** Menangkap halaman portofolio/konsep lokal (`site/demos/<slug>/index.html` atau `concept.html`) atau URL publik terverifikasi (`allow_remote_url=True` dengan SSRF guard) pada viewport mobile `390×844` @2x/@3x DPR; menunggu font & lazy images stabil, mendeteksi posisi section, serta menangkap interaksi nyata (highlight tombol CTA & perpindahan tab bila tersedia di DOM).
- **`reels_motion.py`:** 10 kurva easing (`out_quart`, `in_out_quint`, `out_back`, dll.), *waterfall* staggered word entry, *nudge curve* (10/65/25), profil gerak adaptif (`snappy`, `refined`, `balanced` — kategori formal/klinik dikunci `refined` tanpa overshoot), serta konstanta **Instagram 9:16 safe zone** (`x: 64–960`, `y: 290–1580`, lantai font `>= 32px`, dan crop tengah grid 4:5 `y: 285–1635`).
- **`reels_plates.py` & `reels_compose.py`:** Merender plate HTML/CSS sesuai arah tipografi + layer transparan untuk animasi per-kata/per-tile pada 3 struktur cerita 5-beat (`scroll_reveal_showcase`, `before_after_ux`, `kinetic_editorial`), scroll mobile terkontrol dengan jeda baca, wipe transisi, dan tap ring interaksi nyata.
- **`reels_qa.py`:** Audit otomatis 18-cek (`qa_report.json`): dimensi 1080×1920 H.264 `yuv420p`, 30 fps, durasi 8–12 dtk, stream audio AAC 44.1kHz stereo & sinkronisasi A/V, deteksi black/freeze frame, safe zone IG & 4:5 cover crop, lantai font >= 32px, keaslian DOM website, guardrail showcase, serta `check_anonymization_leak`.
- **Mode Audio Reels (`audio_mode`):** `voiceover_and_music` (default — `edge-tts` Bahasa Indonesia + musik ambient lo-fi royalty-free), `voiceover_only`, `music_only`, dan `silent` (menghasilkan track AAC senyap agar aman untuk Instagram & tombol unmute browser tetap aktif).
- **Konfigurasi opsional `.env`:** `REELS_DURATION_SEC=10.0` (rentang 8.0–12.0 detik).
- **Audit, Atribusi & Lisensi:** Lihat [`docs/REELS_ENGINE_AUDIT.md`](./docs/REELS_ENGINE_AUDIT.md). Tidak ada kode repositori eksternal yang disalin/diinstal; konsep gerak dipelajari secara read-only dari dokumentasi publik (HyperFrames Apache-2.0, Herk Edit Kit MIT) dan diimplementasikan ulang murni di Python.
- **Troubleshooting singkat:**
  - *Tombol unmute browser nonaktif pada video lama:* Pastikan server `python app.py` sudah di-restart lalu klik generate ulang agar `reels.mp4` membawa track AAC 44.1kHz.
  - *Offline saat `voiceover_and_music`:* Generator otomatis fallback aman ke `music_only` (ambient sintetis lokal).
  - *FFmpeg tidak ditemukan di PATH:* Generator otomatis menyimpan fallback `frames_fallback/beat_*.png` tanpa crash.

---

## Enrichment Prospek Read-Only via Agent-Reach (`creative_agent/lead_enricher.py`)

Pipeline mendukung enrichment otomatis opsional setelah job scrape selesai (`_run_scrape_job`) khusus untuk prospek berstatus `NEW` yang belum memiliki `ig_observation`, menggunakan CLI **Agent-Reach** (`D:\AI WORKSPACE\tools\Agent-Reach\.venv\Scripts\agent-reach.exe`) dalam mode **read-only**:

- **Channel default aktif:** `web`, `youtube`, `github`, plus channel `instagram` (hanya aksi baca/pencarian: `profile`, `posts`, `search`).
- **Website UX Flaw (`agent-reach read <url>`):** Jika prospek memiliki URL website publik (non-localhost/non-private IP), helper membaca halaman utama untuk merangkum temuan `ux_flaw` nyata (mis. link aggregator, menu masih PDF, belum ada tautan WhatsApp langsung, atau konten halaman terlalu minim di HP).
- **Instagram Observation (`agent-reach instagram posts/profile <handle>`):** Jika prospek memiliki handle/link Instagram dan channel `instagram` aktif, helper mengambil 1 observasi spesifik nyata dari postingan terbaru atau bio untuk mengisi `ig_observation`. Jika channel belum login (`NEED_LOGIN`), terkena rate-limit (`RATE_LIMITED`), atau diblokir (`PLATFORM_BLOCKED`), helper langsung berhenti tanpa mengulang dan **tidak pernah mengarang detail**.

> **ATURAN WAJIB KEAMANAN AKUN INSTAGRAM:**
> **DILARANG KERAS** melakukan login, menautkan browser, atau menyalin sesi/cookie akun utama **`@goandalan`** ke `agent-reach` maupun `opencli`. Jika ingin mengaktifkan sesi baca pada channel `instagram`, **WAJIB menggunakan akun riset terpisah khusus read-only** dan tidak pernah melakukan aksi tulis (DM/komen/like/post otomatis).

Variabel opsional di `.env`:
```dotenv
AGENT_REACH_BIN=D:\AI WORKSPACE\tools\Agent-Reach\.venv\Scripts\agent-reach.exe
ENABLE_POST_SCRAPE_ENRICHMENT=true
```

---

## Menjalankan Server & Pengujian

```powershell
# Jalankan dashboard
python app.py

# Kompilasi sintaks
python -m py_compile config.py database.py content_review.py reels_motion.py reels_capture.py reels_plates.py reels_compose.py reels_qa.py reels_generator.py app.py smoke_test.py test_content_review.py

# Jalankan test Auth, Sliding Session 7 Hari, RBAC, Security & Review Workflow
python test_content_review.py

# Jalankan smoke test 2-stage / 3-phase pipeline
python smoke_test.py
```
