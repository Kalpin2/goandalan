# Reels Intelligence Library (@goandalan)

Panduan wajib untuk seluruh produksi **Instagram Reels 9:16 (`1080×1920`, 30 fps, durasi 12–15 detik)** milik `@goandalan` (*gw sama alan*) dengan fokus utama **Attract Customer** (menarik pemilik bisnis lokal Indonesia lewat masalah nyata operasional & UX digital mereka).

> **Pemisahan Peran Konten:**
> - **Carousel (`4:5`)** via `/recycle` Tab 2 → khusus **pamer hasil desain website** (grid profil tetap fokus showcase).
> - **Reels (`9:16`)** via `Cari Ide Reels` Tab 4 → khusus **Attract Customer** (masalah nyata pemilik usaha + demonstrasi mobile UI solusi + CTA `DM kata KONSEP`).

---

## 1. Taksonomi Masalah Bisnis Nyata (`PAIN-*`)

| Kode | Masalah Nyata Pemilik Usaha | Segmen Target Utama | Solusi yang Ditunjukkan di Layar HP |
| :--- | :--- | :--- | :--- |
| **`PAIN-WA`** | Admin kewalahan membalas pertanyaan berulang (harga, jam buka, lokasi, menu) di chat WA/DM yang membuat calon pelanggan menunggu lama dan pindah ke kompetitor. | Kafe, Klinik, Bakery, Barbershop, Bengkel | Halaman mobile 1-scroll dengan daftar layanan/menu jelas, jam buka, dan tombol WA terarah. |
| **`PAIN-TRUST`** | Bisnis sudah punya rating bagus di Maps & IG rapi, tetapi terlihat kurang meyakinkan dibanding kompetitor karena hanya mengandalkan link aggregator atau belum punya halaman web resmi. | Klinik Gigi/Derma, Studio Pilates, Legal, B2B, Konsultan | Antarmuka editorial bersih, profil dokter/tim & spesialisasi jernih, kredibel tanpa gimmick. |
| **`PAIN-BOOKING`** | Alur reservasi/jadwal berantakan lewat chat bolak-balik sehingga jadwal bentrok, calon pasien/tamu malas bertanya, atau batal datang. | Klinik, Pilates, Barbershop, Salon, Bengkel | Ringkasan jadwal praktik/slot layanan + tombol reservasi WA 1-klik yang langsung membawa konteks layanan. |
| **`PAIN-ADS`** | Sudah keluar biaya iklan IG/Google Ads, tetapi trafik mendarat ke bio/WA mentah tanpa penjelasan layanan sehingga biaya iklan boncos dan rasio closing rendah. | Klinik Estetika, F&B, Retail, Bengkel Custom, B2B | Landing page cepat di HP (`390×844`) yang menjawab 3 pertanyaan utama dalam 5 detik pertama. |
| **`PAIN-MOBILE`** | Website lama atau katalog masih berbentuk PDF / file Drive / tampilan desktop sempit sehingga pelanggan HP harus zoom-in dan langsung menutup halaman. | Kafe, Bakery, Resto, Klinik, Retail | Tipografi mobile terbaca (`>= 32px` pada plate / proporsional di `390×844`), tab layanan interaktif, nol PDF. |

---

## 2. Pola Hook Pembuka Reels (`REEL-HOOK-*`)

Setiap hook wajib **<= 12 kata**, terbaca di 2 detik pertama di dalam IG Safe Zone (`x: 64–960`, `y: 290–1580`), dan langsung mengenai masalah pemilik usaha:

| ID | Pola Hook | Cocok Untuk | Catatan Register |
| :--- | :--- | :--- | :--- |
| **`REEL-HOOK-1`** | Pertanyaan langsung soal kebocoran chat/admin: *"Berapa pelanggan batal datang gara-gara nunggu balasan WA?"* | `PAIN-WA`, `PAIN-BOOKING` | Formal: ganti *gara-gara/nunggu* → *karena menunggu*. |
| **`REEL-HOOK-2`** | Kontras IG bagus vs halaman info lemah: *"IG sudah rapi, tapi calon klien masih bingung cek layanan?"* | `PAIN-TRUST`, `PAIN-MOBILE` | Aman untuk formal & kasual. |
| **`REEL-HOOK-3`** | Biaya iklan vs halaman mendarat: *"Iklan jalan terus, tapi kliknya cuma mentok di link bio?"* | `PAIN-ADS`, `PAIN-WA` | Formal: *"Iklan sudah berjalan, tetapi pengunjung belum menemukan info utama?"* |
| **`REEL-HOOK-4`** | Menu/katalog PDF di layar HP: *"Masih kirim katalog PDF yang harus di-zoom di layar HP?"* | `PAIN-MOBILE`, `PAIN-WA` | Aman untuk F&B, retail, klinik. |
| **`REEL-HOOK-5`** | Reservasi & jadwal praktik: *"Calon klien mau booking, tapi harus chat panjang dulu?"* | `PAIN-BOOKING`, `PAIN-TRUST` | Sangat kuat untuk klinik, pilates, salon, barbershop. |

---

## 3. Pacing V/O Adaptif (35–55 Kata → 12–15 Detik)

1. **Target Panjang Naskah:** **35–55 kata** Bahasa Indonesia natural (kecepatan baca ~3.2–3.8 kata/detik → pas **12–15 detik** tanpa terburu-buru).
2. **Struktur 3 Bagian Naskah V/O:**
   - **Detik 0–3 (Hook Masalah — 8–14 kata):** Sentuh 1 masalah nyata pemilik bisnis (`PAIN-*`).
   - **Detik 3–11 (Demo Solusi di HP — 18–28 kata):** Jelaskan apa yang terlihat di scroll website mobile `390×844` (layanan utama, jam/jadwal, interaksi tab/CTA nyata).
   - **Detik 11–15 (Penutup CTA — 8–12 kata):** Ajak secara tenang tanpa hard-sell agresif: *"Mau lihat konsep versi bisnis Anda/kamu? DM kata KONSEP."*
3. **Aturan V/O Adaptif Sesuai Kategori Bisnis (`edge-tts`):**
   - **Formal / Kesehatan / Profesional (`clinic`, `pilates`, `legal`, `b2b`, `dokter`, `notaris`, `konsultan`, `hotel`):**
     - **0 kata slang** (`gw`, `gue`, `lo`, `lu`, `nih`, `banget`, `gak`, `bikin`, `kepoin`).
     - Suara default: **`id-ID-GadisNeural`** (sopan-tenang, rate `+2%`) atau **`id-ID-ArdiNeural`** nada tenang (rate `+0%`).
     - Sapaan: *Anda / Bapak-Ibu*.
   - **Kasual / Kreatif (`cafe`, `coffee`, `bakery`, `barbershop`, `automotive`, `bengkel`, `retail`, `kuliner`):**
     - Bahasa hangat-santai natural ala percakapan (tetap sopan, tanpa lebay).
     - Suara default: **`id-ID-ArdiNeural`** (persona Alan, rate `+5%`).
     - Sapaan: *kamu / pemilik usaha*.

---

## 4. Pemetaan BGM Procedural Sesuai Target (`assets/bgm/`)

Musik latar bebas royalti (`12–15` detik loop-safe) dipilih otomatis sesuai karakter bisnis dan di-mix dengan **FFmpeg `sidechaincompress` ducking** agar otomatis mengecil halus saat V/O berbicara:

| Track File | Karakter Audio | Target Bisnis |
| :--- | :--- | :--- |
| `calm_editorial.wav` | Pad elektrik lembut & tenang (~76 BPM, harmonik halus) | Klinik, Pilates, Legal, B2B, Arsitektur, Hotel |
| `warm_hospitality.wav` | Electric piano lo-fi hangat & akrab (~94 BPM) | Kafe, Coffee Roastery, Bakery, Kuliner, Florist |
| `energetic_craft.wav` | Pulse ritmis bersih & modern (~112 BPM) | Bengkel Custom, Barbershop, Grooming, Retail, Streetwear |

File `.mp3`/`.wav` tambahan yang diletakkan di `assets/bgm/` otomatis terbaca di selector UI Tab 4.

---

## 5. Protokol Self-Learning Hemat Token (Metrik IG & Editan Naskah)

1. **Zero-Token Edit Tracking:** Setiap kali manusia mengedit Script V/O sebelum render, Python menghitung `compute_edit_delta` (`word_delta`, `sapaan_changed`, `emoji_removed`, `shortened`) dan mencatatnya ke `reels_learning_log.md` tanpa memanggil LLM.
2. **Metrik Nyata Postingan IG (`Sudah Diposting` Tab 4):** Reviewer/Admin mengisi `Views`, `Saves`, `Shares`, dan `DM Masuk` pada konten berstatus `posted`.
3. **Slice-Only Evaluation (`/api/learning/evaluate`):** Agen **DILARANG** membaca seluruh `reels_learning_log.md` mentah. Evaluasi wajib membaca ringkasan padat `learning_digest.json` (<= ~1.200 token) dan maksimal mengusulkan **3 kandidat baru** (`status: candidate`, `approved_by_user: false`) ke `reels_candidates.md`.
4. **Hard Gate Promosi:** Kandidat di `reels_candidates.md` **tidak boleh** dipromosikan ke file library inti ini tanpa persetujuan eksplisit user.
