# AGENTS.md — Modul Produksi Konten (Carousel + Reels + Beat-Sync) `@goandalan`

Panduan ini untuk agent yang bertugas memproduksi **carousel**, **reels demo**, **reels edukasi**, dan **reels jedag-jedug berbasis sound (`reel_beatsync`)** secara otomatis dari hasil build demo website. Baca seluruh aturan sebelum mengeksekusi tugas apa pun.

## 1. Tujuan & Struktur Output

Setiap kali satu demo site selesai dibuat, agent menghasilkan satu paket konten siap upload di dalam folder versi (`v1`, `v2`, dst.):

```text
output/<slug>/v1/
├── carousel_01.png ... carousel_0N.png   # 1080x1350 (render 2x -> 2160x2700)
├── reel.mp4                              # 1080x1920, H.264, yuv420p (30fps; atau 60fps khusus reel_beatsync)
├── reel_cover.png                        # 1080x1920 (area tengah 1080x1350 aman untuk grid 4:5)
├── caption.txt                           # Siap copy-paste
└── meta.json                             # Log: versi, durasi, BPM/drop (jika beatsync), engine suara, status QA
```

Agent **dilarang mengupload** ke Instagram atau mengirim DM secara otomatis. Upload dilakukan manual oleh manusia.

## 2. Aturan Brand & Dinamika Karakter (Wajib)

### Identitas Visual (`@goandalan`)

| Elemen | Nilai Standar |
| :--- | :--- |
| Handle | `@goandalan` |
| Background Utama (Warm Paper) | `#F6F3EC` |
| Surface / Card (Soft Linen) | `#EDE8DD` |
| Teks Utama (Charcoal Ink) | `#1E1E1E` |
| Teks Sekunder (Warm Stone) | `#6B675F` |
| Warna Aksen (Pilih 1 permanen) | `#3E4E3C` (Muted Olive) atau `#9A523B` (Terracotta) |
| Tipografi Judul | `Instrument Serif` (fallback: `Georgia, serif`) |
| Tipografi Isi & UI | `Plus Jakarta Sans` (fallback: `Inter, sans-serif`) |
| Tipografi Label / Issue | `JetBrains Mono` (uppercase, tracking `0.08em`) |
| Header Kecil | `ISSUE 01 · @goandalan` (nomor urut naik per post) |
| Gaya Visual | Warm editorial, tenang, margin lega, frame browser/HP flat bersih |
| Gaya Beat-Sync (Jedag-Jedug) | **Editorial Kinetic Cut**: hard-cut tajam pas di beat, *punch-zoom* halus (maks 1.08x), *damped micro-shake* tipis (maks 8px), atau *flash-cut* warna krem `#F6F3EC` (1–2 frame) saat *bass drop*. |
| Dilarang | Efek RGB split/glitch neon, transisi putar 3D norak, glow warna-warni, stiker meme/emoji berlebihan, mockup 3D miring |

Semua template HTML wajib memakai CSS variables (`--bg`, `--surface`, `--ink`, `--muted`, `--accent`).

### Dinamika Karakter ("Gw" vs. "Alan")

* **"Gw" (Manusia / Narator):** Menulis caption dan narasi dari sudut pandang orang pertama (`gw`). Santai, hangat, pragmatis, fokus ke kemudahan bisnis tanpa jargon teknis.
* **"Alan" (Partner Fiktif / AI Agent):** Digambarkan sebagai partner perfeksionis yang gak pernah tidur dan bawel soal detail UI (misal spacing 2px atau loading lambat).
* **Aturan Emas:** Sebut Alan **maksimal 1 kali** per caption atau hook. Gunakan Alan untuk pamer kualitas pengerjaan secara halus—jangan pernah menjadikan Alan alasan atas keterlambatan atau kesalahan.

## 3. Struktur Folder Workspace

```text
content/
├── templates/
│   ├── carousel.html           # Template slide 4:5
│   ├── reel_wrapper.html       # Pembungkus 9:16 (frame HP + header + hook + safe zone)
│   └── edu_card.html           # Template kartu teks untuk reel_edu & intro beat-sync
├── assets/
│   ├── audio/                  # File sound/lagu dari manusia (.mp3/.wav/.m4a) untuk reel_beatsync
│   ├── voice/                  # Sampel suara / rekaman human voice untuk reel_edu
│   └── pronounce.json          # Kamus pelafalan TTS (mis. "WA": "we a")
├── scripts/
│   ├── run_all.py              # Entrypoint utama per slug
│   ├── auto_carousel.py
│   ├── auto_reel.py            # reel_scroll / reel_before_after / reel_flow
│   ├── auto_edu_reel.py        # reel_edu (voice over + subtitle)
│   ├── auto_beatsync.py        # reel_beatsync (jedag-jedug berbasis sound)
│   └── common.py               # Helper ffprobe, SRT, QA checks, versioning
├── input/<slug>/brief.json
└── output/<slug>/v1/
```

## 4. Spesifikasi Input: `brief.json`

Agent membaca file ini per prospek/konten. Jika field wajib kosong, **berhenti dan laporkan**, jangan mengarang.

```json
{
  "slug": "kopi-senja",
  "type": "reel_beatsync",
  "issue": 2,
  "consent_public": false,
  "business_name": "Kopi Senja",
  "anonymized_name": "Kedai Kopi Lokal",
  "demo_url": "http://localhost:4173/kopi-senja",
  "old_url": "https://web-lama.example.com",
  "hook": "web lama bikin pusing → gw sama alan beresin.",
  "beatsync": {
    "sound_file": "assets/audio/sound_drop_01.mp3",
    "audio_start": 0.0,
    "max_duration": 12.0,
    "drop_at": null,
    "style": "before_after_drop",
    "intensity": "medium",
    "extra_demo_urls": []
  },
  "flow_selectors": [
    "[data-flow='step-1']",
    "[data-flow='step-2']",
    "[data-flow='cta']"
  ],
  "slides": [
    {
      "tag": "MASALAH",
      "title": "Menu PDF 12MB bikin orang keburu nutup tab.",
      "body": "80% pengunjung datang dari bio IG lewat HP. Kalau harus zoom-in file berat, mereka batal pesan."
    }
  ],
  "scenes": [
    {
      "text": "Tiga hal yang bikin pengunjung langsung nutup website bisnis lo.",
      "title": "3 alasan pengunjung kabur",
      "visual": "card"
    }
  ]
}
```

* Nilai `type`: `carousel`, `reel_scroll`, `reel_before_after`, `reel_flow`, `reel_edu`, `reel_beatsync`.
* Nilai `beatsync.style`:
  * `clean_punch`: Intro singkat 1–2 beat → pas *drop*, potong cepat antar section website (hero, menu, detail UI, mobile view, CTA) dengan *punch-zoom* di tiap beat.
  * `before_after_drop`: Fase sebelum *drop* menampilkan `old_url` (atau kartu masalah) dengan zoom pelan membangun tensi → tepat di *drop*, banting (*hard-cut* + *flash* krem 1 frame) ke hasil web baru dan ganti section tiap beat.
  * `fast_showcase`: Kompilasi beberapa demo sekaligus (`demo_url` + `extra_demo_urls`), ganti proyek tiap 1–2 beat.
* Nilai `beatsync.intensity`: `subtle` (zoom 1.04x, tanpa shake), `medium` (zoom 1.08x + damped shake 6px — default), `punchy` (zoom 1.12x + damped shake 10px + 1-frame flash `#F6F3EC` saat drop).
* **Aturan Anonimisasi (`consent_public: false`):** Jangan memakai kotak blur di video/gambar. Sebelum mengambil screenshot atau merekam video, agent mengganti teks nama brand/kontak asli di DOM halaman demo dengan `anonymized_name` agar hasil visual tetap bersih.

## 5. Pipeline Carousel (Wajib Ikuti `carousel_design_system_website_showcase.md`)

Seluruh produksi carousel IG **wajib** mengikuti panduan **`carousel_design_system_website_showcase.md`** (*Adaptive Website Showcase*). Jangan lagi memakai satu template tunggal (background krem `#F6F3EC` + serif) untuk semua bisnis.

* **Ukuran Logical:** `1080x1350` (4:5), dirender dengan `device_scale_factor=2` (output `2160x2700` PNG tajam).
* **Jumlah Slide:** 4 slide dengan komposisi visual yang bervariasi antar-slide dan screenshot website asli menjadi bintang utama:
  1. **Slide 1 (Hook / Cover):** Headline spesifik brand + *split composition* / *editorial typography overlay* dengan potongan visual hero website asli.
  2. **Slide 2 (Context / Concept):** *Photo/direction + interface* atau *asymmetric layout* menjelaskan arah desain & pengalaman pengguna secara ringkas.
  3. **Slide 3 (Website Reveal — Porsi Screenshot Terbesar):** *Overlapping devices* (Desktop + Mobile) atau *device-free / clean browser window* yang tajam & mudah dibaca di layar HP.
  4. **Slide 4 (Features / Experience Walkthrough):** *UI close-up / annotated interface* atau *modular grid showcase* yang menyoroti bagian nyata dari HTML demo. **Dilarang memasang CTA iklan jasa** (mis. "DM sekarang untuk buat website")—gunakan penutup netral (*"Inside the experience"*, *"Explore the interface"*, *"A closer look"*, *"Website concept · @goandalan"*).
* **Dua Mode Kerja:**
  1. **Mode Interaktif (Art Director Review — Sesi Chat):** Saat user meminta merancang carousel spesifik di chat, jalankan **Tahap 1–7** pada `carousel_design_system_website_showcase.md`: parse brief & audit kelengkapan materi → rekomendasikan *creative direction* (gaya utama, pendamping, storytelling, palet, tipografi) → tampilkan tabel storyboard 4 slide → **tunggu persetujuan & revisi user sebelum produksi/render final**.
  2. **Mode Otomatis Pipeline (`carousel_generator.py`):** Saat berjalan di pipeline Mini App / batch otomatis, sistem secara otomatis menyinkronkan *primary style*, palet warna, tipografi, *storytelling method*, dan variasi komposisi 4 slide dengan `design_style` & industri lead, lalu mengekstrak fakta UI langsung dari HTML demo (nol fitur/rating/testimoni karangan) dan menyimpan ringkasan arah desain di `art_direction.json`.
* **Aturan Akurasi & Caption:**
  * Dilarang mengarang rating, jumlah pelanggan, testimoni, harga, atau fitur yang tidak ada di HTML demo.
  * `caption.txt` menceritakan konsep & pengalaman websitenya secara natural (sudut pandang orang pertama `"gw"`, maksimal 1 mention natural tentang Alan, tanpa hard-selling).

## 6. Pipeline Reels (`1080x1920`, H.264)

### Aturan Safe Zone Instagram & Grid Crop (Wajib)

1. **UI Safe Zone (`1080x1920`):**
   * **Atas (`0–220px`):** Kosongkan (tertutup status bar & ikon kamera IG).
   * **Bawah (`1540–1920px` / margin bawah `380px`):** Kosongkan (tertutup caption, username, dan bar audio IG).
   * **Kanan (`960–1080px` / margin kanan `120px`):** Hindari teks/elemen penting (tertutup tombol Like, Comment, Share).
   * **Area Konten Utama:** Wajib berada di kotak `x: 60..960px`, `y: 220..1540px`.
2. **4:5 Profile Grid Crop:** Saat Reel tampil di grid profil IG, Instagram memotong area tengah `1080x1350` (`y: 285..1635px`). Pastikan hook utama dan bagian atas frame HP masuk dalam area tengah ini, dan ekspor `reel_cover.png` dengan komposisi yang selaras dengan feed.

### Persiapan Sebelum Merekam / Screenshot Halaman Web (Warmup)

Sebelum mengambil visual dari `demo_url` atau `old_url`:

1. Buka halaman dengan viewport mobile (`390x844`, `is_mobile=True`, `device_scale_factor=2`), tunggu `networkidle`.
2. Jalankan *warmup scroll* cepat ke bawah lalu kembali ke `scrollY = 0` agar semua gambar `loading="lazy"` termuat sempurna.
3. Sembunyikan banner cookie atau widget chat mengambang yang menghalangi layar utama (khusus pada `demo_url`).

### 6.1 `reel_scroll` — Smooth Scroll Walkthrough (8–10 detik, 30fps, `-an`)

1. Mulai perekaman Playwright setelah warmup selesai.
2. Jalankan animasi scroll halus (`easeInOutCubic` via `requestAnimationFrame`) dari atas ke footer selama `8000 ms`.
3. **Panggil `context.close()` terlebih dahulu** agar file `.webm` tersimpan utuh.
4. Komposisikan dengan FFmpeg ke canvas `1080x1920` warna `#F6F3EC`, potong `0.5s` pertama, encode `30fps`, `libx264`, `yuv420p`, `-an`.
5. Tambahkan header `ISSUE 0N · @goandalan` dan teks `hook` di dalam area aman (`y >= 240px`).

### 6.2 `reel_before_after` — Perbandingan Web Lama vs. Baru (7–9 detik, 30fps, `-an`)

1. Rekam `old_url` (tampilan HP `390x844`) selama `2.5 detik`.
2. Rekam `demo_url` selama `6 detik` dengan smooth scroll.
3. Gabungkan dengan FFmpeg `xfade=transition=wipeleft:duration=0.5`, encode `1080x1920`, `30fps`, `-an`.
4. Tambahkan label kecil `SEBELUM` dan `SESUDAH (VERSI @GOANDALAN)` di dalam safe zone.
5. Jika `old_url` gagal dimuat (timeout `15s` / HTTP error), **batalkan tipe ini**, catat di `meta.json`, dan fallback ke `reel_scroll`.

### 6.3 `reel_flow` — Simulasi Alur Klik di HP (7–9 detik, 30fps, `-an`)

1. Semua template demo generator wajib menyematkan atribut standar `data-flow="step-1"`, `step-2`, dan `cta`.
2. Jika selector dari `flow_selectors` tidak ditemukan di DOM, hentikan tipe ini dan laporkan—jangan menebak koordinat klik.
3. Inject indikator sentuhan (lingkaran transparan halus `#1E1E1E` opacity `0.25`) pada titik klik sebelum memicu navigasi/scroll.

### 6.4 `reel_edu` — Reel Edukasi dengan Narasi & Subtitle (20–40 detik, 30fps, audio VO)

1. Setiap scene berisi **1 kalimat pendek (maksimal 15 kata)**.
2. Generate audio per scene (Bagian 7), ukur durasi eksak dengan `ffprobe`.
3. Render visual tiap scene (`card`, `screenshot`, atau `scroll`) sesuai durasi audio + jeda napas `0.25s`.
4. Gabungkan seluruh klip, normalisasi audio, dan bakar subtitle (Bagian 8).

### 6.5 `reel_beatsync` — Video Jedag-Jedug Berbasis Sound (7–15 detik, **60fps**, audio dari user)

Modul ini menghasilkan video *beat-synced* tajam yang tetap terlihat berkelas (gaya *editorial kinetic cut*), menggunakan file audio yang diberikan manusia di `beatsync.sound_file`.

#### Langkah 1: Analisis Audio (`librosa` / `scipy`)
1. Validasi file `beatsync.sound_file` ada dan terbaca. Jika tidak ada, **berhenti dan laporkan**.
2. Potong audio mulai `audio_start` sepanjang `max_duration` (default `10–12 detik`, maksimal `15 detik`).
3. Deteksi beat dan energi bass:
   * Ekstrak tempo (`bpm`) dan daftar timestamp beat (`beats[]`) menggunakan `librosa.beat.beat_track` + `librosa.onset.onset_detect` (disnap ke beat terdekat).
   * Hitung kurva energi frekuensi rendah (`< 150 Hz` / kick & bass) untuk mendeteksi momen **Drop** (lonjakan energi terbesar setelah detik ke-1.5).
   * Jika manusia mengisi `beatsync.drop_at` di `brief.json` (bukan `null`), **wajib pakai angka manual tersebut** sebagai titik drop utama.
4. Simpan `bpm`, `drop_time`, dan `beats[]` ke `meta.json` untuk transparansi QA.

#### Langkah 2: Pengumpulan Shot Visual (Multi-Angle)
Daripada memutar 1 gambar berulang-ulang, ambil **6–10 shot tajam** berukuran `1080x1920` (dibungkus warna `#F6F3EC` atau *close-up* komponen bersih di dalam safe zone):
* **Shot Intro (sebelum drop):** Kartu judul hook editorial (`ISSUE 0N` + hook) dan/atau tangkapan layar `old_url` (jika mode `before_after_drop`).
* **Shot Drop & Beat (setelah drop):**
  1. Hero section versi mobile (`390x844` di dalam frame HP)
  2. Hero section versi desktop (`1440x900` di dalam browser frame)
  3. Close-up bagian menu/katalog/fitur utama
  4. Close-up detail tipografi / kartu produk (zoomed crop)
  5. Bagian testimoni / galeri / peta lokasi
  6. Close-up tombol CTA / WhatsApp order
  7. Full overview / outro card `@goandalan`
* *(Jika mode `fast_showcase`, kumpulkan 2–3 shot per URL dari `demo_url` dan `extra_demo_urls`).*

#### Langkah 3: Render Frame-Accurate Tanpa Jitter (Python OpenCV/NumPy → FFmpeg Pipe)
**Larangan teknis:** Jangan memakai filter `zoompan` FFmpeg untuk jedag-jedug karena sering menghasilkan getaran (*jitter*) pembulatan piksel pada transisi cepat. Gunakan pipeline Python berikut:

1. Generate frame pada **`60fps`** (`dt = 1/60s`) menggunakan `OpenCV` (`cv2.warpAffine` dengan `INTER_LINEAR`) atau `NumPy` dan langsung pipe raw BGR bytes ke stdin FFmpeg (`-f rawvideo -pix_fmt bgr24 -s 1080x1920 -r 60 -i -`).
2. **Aturan gerak per beat (berdasarkan waktu relatif `t_beat` sejak beat terakhir):**
   * **Fase Sebelum Drop:** *Slow push-in* konstan (`scale = 1.00 -> 1.05` linear) agar membangun tensi.
   * **Tepat di Drop (`t == drop_time`):** Ganti shot ke Hero baru + *flash-cut* krem `#F6F3EC` (opacity `0.65 -> 0.0` dalam 3 frame / `50ms`) + *punch-zoom* puncak.
   * **Setiap Beat Setelah Drop:** Ganti ke shot berikutnya (atau setiap 2 beat jika BPM > 140 agar mata tidak pusing). Terapkan kurva peluruhan eksponensial yang licin:
     * **Punch Zoom:** `scale(t) = 1.0 + A_zoom * exp(-10 * t_beat)` (langsung melompat ke `1.08x` pas hentakan beat, lalu memantul halus kembali ke `1.0x`).
     * **Damped Micro-Shake (mode `medium`/`punchy`):**
       `dx = A_shake * sin(45 * t_beat) * exp(-12 * t_beat)`
       `dy = (A_shake * 0.6) * cos(38 * t_beat) * exp(-12 * t_beat)`
     * Nilai default (`medium`): `A_zoom = 0.08`, `A_shake = 6.0` px.
3. **Finalisasi Audio & Muxing:**
   * Gabungkan stream video `libx264` (`-crf 18`, `-pix_fmt yuv420p`) dengan potongan audio user (`-c:a aac -b:a 192k`).
   * Terapkan normalisasi audio musik (`-af loudnorm=I=-14:TP=-1.0:LRA=11`) + fade-out `0.35s` di akhir audio agar tidak terpotong kasar.
   * Ekspor `reel_cover.png` dari frame Hero terbaik (tanpa blur gerakan) dengan header `ISSUE 0N · @goandalan`.

## 7. Audio & Voice Over

* **`reel_scroll`, `reel_before_after`, `reel_flow`:** Render tanpa track audio (`-an`) agar manusia bebas menempelkan musik langsung di Instagram.
* **`reel_beatsync`:** Wajib memakai audio dari `beatsync.sound_file` yang disediakan manusia (jangan mencampur suara TTS di atasnya kecuali diminta eksplisit).
* **`reel_edu`:** Gunakan urutan prioritas berikut (berhenti di opsi pertama yang berhasil & lolos QA):
  1. **Rekaman Suara Manusia (`assets/voice/<slug>_s0.wav`, dst.):** Jika sudah disediakan, pakai langsung.
  2. **Indonesian Neural TTS (`edge-tts` `id-ID-ArdiNeural` atau Piper `id_ID`):** Ringan (0 VRAM), pelafalan bahasa Indonesia natural.
  3. **Local Voice Cloning (`chatterbox-tts` / Voice Studio):** *Mode eksperimental.* Wajib tandai `needs_audio_review: true` di `meta.json` karena risiko aksen Melayu (`ms`) pada kosakata Jakarta (`gw/lo`).
  4. **Fallback Manual:** Render tanpa suara dan set `needs_human_voice: true` di `meta.json`.

### Aturan Teknis Audio Lokal (Laptop GTX 1650 4GB)

* Muat model GPU **sekali** per run, lalu bersihkan memori (`del model; torch.cuda.empty_cache()`) sebelum FFmpeg berjalan. Jika terkena CUDA OOM, ulangi otomatis di CPU.
* Terapkan kamus pelafalan `assets/pronounce.json` sebelum teks masuk ke TTS (contoh: `"WA": "we a"`, `"UI": "yu ai"`, `"UX": "yu eks"`, `"PDF": "pe de ef"`).
* Normalisasi volume VO ke `-16 LUFS` (`-af loudnorm=I=-16:TP=-1.5:LRA=11`).

## 8. Subtitle (`reel_edu`)

Subtitle wajib dibakar (*hardcoded*) pada `reel_edu`:

* Generate file `.srt` langsung dari teks scene dan durasi `ffprobe`.
* Posisi di atas area caption IG (`MarginV=420` pada resolusi `1920px`, rata tengah, lebar maksimal `820px`).
* Maksimal **2 baris** per tampilan subtitle, font sans bersih (`Plus Jakarta Sans` / `Arial`), warna teks `#1E1E1E` di atas box krem `#EDE8DD`.

## 9. Ritme Konten Awal (Batch 1: 6 Post)

Selang-seling format agar grid profil terlihat seperti majalah kurasi:

| Urutan | Tipe | Isi Konten | Pin? |
| :--- | :--- | :--- | :--- |
| **01** | `carousel` | Showcase proyek pertama + kenalan singkat karakter "gw sama Alan" | **PIN** |
| **02** | `reel_beatsync` | Jedag-jedug rapi (`before_after_drop` atau `clean_punch`) demo bisnis lokal #1 | — |
| **03** | `carousel` | Mini case study #2 (masalah → cara mikir → hasil akhir) | — |
| **04** | `reel_before_after` | Before/After web lokal yang dirapikan (smooth walkthrough) | **PIN** |
| **05** | `carousel` | Notes ringan (*"3 hal yang bikin Alan langsung nutup tab web orang"*) | — |
| **06** | `carousel` | How to work with us (alur santai dari DM ke live) | **PIN** |

## 10. Aturan Caption (`caption.txt`)

1. **Baris 1 (Hook):** Kalimat pembuka pendek yang nyambung dengan konsep website di slide/reel.
2. **Isi (2–3 paragraf pendek):** Ceritakan arah desain, mood visual, dan pengalaman pengguna websitenya secara santai (`gw` / `kita`), selipkan **maksimal 1 referensi ringan tentang Alan**. Hindari bahasa jualan kaku atau klaim palsu.
3. **Penutup Showcase Netral (Default):** Untuk carousel *website showcase* (`carousel_design_system_website_showcase.md`), **jangan pasang hard-selling / CTA iklan jasa** di slide maupun caption kecuali diminta eksplisit oleh user. Tutup dengan refleksi ringan atau pertanyaan natural soal tampilan/pengalamannya.
4. **Hashtag:** Maksimal 3–5 hashtag relevan di baris paling bawah (contoh: `#websiteshowcase #webdesignindonesia #uidesign #goandalan`).

## 11. QA Checklist Otomatis (Wajib Sebelum Selesai)

Jalankan pengecekan otomatis dan simpan hasilnya ke `meta.json`:

* **Teknis Video & Gambar:**
  * Carousel: `1080x1350` (atau `2160x2700`), format PNG valid, ukuran < 15 MB/file.
  * Reel: `1080x1920`, codec `h264`, pixel format `yuv420p`, `30fps` (atau `60fps` untuk `reel_beatsync`), durasi sesuai rentang tipe, ukuran < 100 MB.
  * Tidak ada frame hitam/putih kosong di `0.0s` pertama maupun `0.2s` terakhir.
* **Khusus `reel_beatsync`:**
  * Track audio aktif dan selisih durasi audio vs video `< 0.15 detik`.
  * Minimal `4` cut sinkron beat terdeteksi; `bpm`, `drop_time`, dan `total_cuts` tercatat di `meta.json`.
  * Tidak ada distorsi/clipping gambar keluar canvas saat *punch-zoom* atau *micro-shake* (gunakan *overscan* / cropping aman).
* **Visual & Safe Zone:**
  * Tidak ada teks atau frame HP yang masuk ke zona terlarang IG (`y < 220px`, `y > 1540px`, `x > 960px`).
  * Halaman demo termuat utuh (tidak ada 404, gambar broken, atau popup menutupi layar).
* **Audio & Subtitle (`reel_edu`):**
  * Semua scene punya durasi audio > `0.5s`, tidak ada jeda hening > `1.5s`, dan file `.srt` sinkron.
* **Privasi & Akurasi:**
  * Jika `consent_public` bernilai `false`, pastikan nama asli prospek dan nomor WA asli tidak muncul di frame maupun caption.

Jika QA gagal, agent boleh memperbaiki maksimal **2 kali**. Jika masih gagal, set `"status": "needs_review"` di `meta.json` dan jelaskan penyebabnya secara spesifik.

## 12. Aturan Keras (Guardrails)

1. **Dilarang memakai AI video generator (Veo, Sora, dll.)** untuk memalsukan tampilan website. Semua visual web harus berasal dari tangkapan layar / rekaman browser asli atas kode HTML/CSS yang benar-benar berfungsi.
2. **Dilarang mengarang testimoni, nama klien, atau statistik performa.**
3. **Dilarang auto-post ke IG atau auto-send DM.**
4. **Dilarang menimpa output lama.** Selalu buat folder versi baru (`output/<slug>/v1`, `v2`, dst.).
5. **Dilarang menghapus file di luar folder `output/` dan `tmp/`.**
6. **Dilarang menebak input yang kurang.** Jika `brief.json` atau file sound tidak lengkap, hentikan proses dan laporkan.

## 13. Perintah Standar CLI

```bash
# Jalankan seluruh paket aset (carousel + reel + caption + QA) untuk satu prospek
python scripts/run_all.py --slug kopi-senja

# Hanya render carousel
python scripts/auto_carousel.py --slug kopi-senja

# Hanya render reel demo standar
python scripts/auto_reel.py --slug kopi-senja --type reel_scroll
python scripts/auto_reel.py --slug kopi-senja --type reel_before_after

# Render reel jedag-jedug berbasis sound (override start & drop opsional)
python scripts/auto_beatsync.py --slug kopi-senja --sound assets/audio/sound_drop_01.mp3
python scripts/auto_beatsync.py --slug kopi-senja --sound assets/audio/sound_drop_01.mp3 --start 14.5 --drop 3.2 --style before_after_drop

# Render reel edukasi dengan voice over + subtitle
python scripts/auto_edu_reel.py --slug edu-01
```

Setelah selesai, agent wajib memberikan ringkasan singkat berisi: lokasi folder versi (`output/<slug>/vN`), jenis aset yang berhasil dibuat, durasi reel (serta BPM & titik drop jika `reel_beatsync`), status QA, dan poin yang perlu dicek manusia sebelum di-upload.