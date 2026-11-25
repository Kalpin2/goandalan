# Reels Learning Log

Catatan kronologis *append-only* untuk produksi Reels `@goandalan`: menyimpan delta editan manusia pada Script V/O (`0` token LLM via `token_optimizer.compute_edit_delta`), pasangan `PAIN-*` + `REEL-HOOK-*`, konfigurasi V/O & BGM, serta metrik nyata Instagram (`Views`, `Saves`, `Shares`, `DM Masuk`).

> **Aturan Token:** Agen **DILARANG** membaca seluruh file log mentah ini ke prompt. Gunakan `learning_digest.json` melalui `creative_agent/token_optimizer.py`.

---

## Reels log schema

```yaml
reels_log:
  lead_id: ""
  date: ""
  display_name: ""
  category: ""
  pain_code: ""
  reel_hook_id: ""
  voice: ""
  vo_style: ""
  bgm_track: ""
  duration_sec: 0
  word_count: 0
  word_delta: 0
  sapaan_changed: ""
  emoji_removed: 0
  shortened: false
  original_vo_script: ""
  final_vo_script: ""
  edit_summary: ""
  views: 0
  saves: 0
  shares: 0
  dm_in: 0
  notes: ""
```

---

## Log entries

### Reels Log: Seduh Pagi Roastery (PAIN-WA) --- 2026-11-24

```yaml
reels_log:
  lead_id: "37"
  date: "2026-11-24T18:15:29+00:00"
  display_name: "Seduh Pagi Roastery"
  category: "Coffee Roastery"
  pain_code: "PAIN-WA"
  reel_hook_id: "REEL-HOOK-1"
  voice: "V1"
  vo_style: "casual_ardi"
  bgm_track: "warm_hospitality"
  duration_sec: 10.0
  word_count: 47
  word_delta: 0
  sapaan_changed: ""
  emoji_removed: 0
  shortened: false
  original_vo_script: "Berapa pelanggan batal mampir hari ini cuma karena kelamaan nunggu balasan chat WA soal menu dan jam buka? Di konsep halaman mobile ini, menu andalan, lokasi Maps, sampai tombol pesan langsung kebaca dalam tiga detik tanpa ribet. Mau lihat konsep versi usaha kamu? Langsung DM kata KONSEP."
  final_vo_script: "Berapa pelanggan batal mampir hari ini cuma karena kelamaan nunggu balasan chat WA soal menu dan jam buka? Di konsep halaman mobile ini, menu andalan, lokasi Maps, sampai tombol pesan langsung kebaca dalam tiga detik tanpa ribet. Mau lihat konsep versi usaha kamu? Langsung DM kata KONSEP."
  edit_summary: "unchanged"
  views: 0
  saves: 0
  shares: 0
  dm_in: 0
  notes: "generated_by:UI Verifier"
```
