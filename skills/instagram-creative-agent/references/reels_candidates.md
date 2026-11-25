# Reels Candidates

Kandidat pola hook, sudut masalah (`PAIN-*`), atau struktur V/O Reels yang menunggu pengujian atau persetujuan eksplisit user sebelum dipromosikan ke `reels_intelligence_library.md`.

> **Aturan Keras:** Jangan pernah memperlakukan entri di file ini sebagai aturan inti hingga `status: approved` dan `approved_by_user: true`.

---

## Candidates

```yaml
reels_candidate:
  id: REEL-HOOK-C0
  pain_code: PAIN-BOOKING
  voice_fit: [V2, V4]
  hook_template: "Pasien ingin lihat jadwal praktik, tapi harus menunggu admin membalas?"
  vo_target_words: "35-55"
  cta_screen: "DM kata KONSEP"
  distinct_from: "REEL-HOOK-5 — framed specifically for clinical/wellness schedule transparency."
  evidence: { uses: 0, avg_views: 0, avg_saves: 0, avg_shares: 0, dm_in: 0 }
  source: seed_research
  confidence: low
  status: candidate
  approved_by_user: false
```
