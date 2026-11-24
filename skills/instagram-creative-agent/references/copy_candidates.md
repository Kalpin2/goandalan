# Copy Candidates

Pattern candidates awaiting testing or explicit user approval per section 12.3–12.6 of `copy_intelligence_library.md`.
Do **not** treat any entry here as part of the core library until `status: approved` and `approved_by_user: true`.

## How to add a candidate

Copy the schema from section 12.5 of `copy_intelligence_library.md`, fill every field, and set `status: candidate` and `approved_by_user: false`.
About 1 in 5 drafts (20% exploration budget) on regular-priority leads may test a matching `candidate` pattern.

------------------------------------------------------------------------

## Candidates

```yaml
pattern:
  id: OPEN-C9
  channel: dm
  slot: opener
  template: "{sapaan}, saya baru lihat {detail_ig} di IG {nama_usaha}—vibe-nya sudah kuat, tinggal halaman web yang seimbang biar calon tamu cepat cek info."
  levers: [L1, L4]
  voice_fit: [V1, V3, V6]
  works_for: ["coffee", "cafe", "bakery", "kuliner", "craft"]
  caution: ["Requires real ig_observation; skip on formal clinics/hotels"]
  distinct_from: "OPEN-S2 — bridges directly to guest info lookup instead of abstract contrast."
  evidence: { uses: 0, replies: 0, interested: 0, declined: 0, ignored: 0, human_edited: 0 }
  source: research
  confidence: low
  status: candidate
  approved_by_user: false
```
