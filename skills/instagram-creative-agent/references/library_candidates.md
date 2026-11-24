# Library Candidates

Entries awaiting testing or approval. Do not treat these as part of the
core library until `status: approved`.

## How to add an entry

Copy the schema from section 15.3 of `typography_intelligence_library.md`,
fill every field, and set `status: candidate`.

------------------------------------------------------------------------

## Candidates

``` yaml
entry:
  id: nusantara-kopitiam-stencil
  name: "Nusantara Kopitiam Stencil & Woodblock Display"
  layer: art_direction
  description: "High-contrast Indonesian artisan signage aesthetic combining condensed woodblock display numerals, warm enamel color blocks, and crisp bilingual roast origin tags."
  visual_traits: ["bold enamel color-blocking", "high-contrast condensed woodblock numerals", "asymmetric roastery sack stamp alignment", "zero generic beige card frames"]
  emotional_voice: ["authentic", "local-craft", "sensory", "tactile"]
  works_for: ["Indonesian coffee roasteries", "artisan bakeries", "local heritage culinary brands"]
  caution: ["Avoid distressing body copy or menu prices", "Do not imitate colonial clichés"]
  distinct_from: "Neo-Vintage / Heritage Revival — specifically encodes Indonesian kopitiam enamel signage and Nusantara roast origin labeling rather than Western retro motifs."
  pairs_with: ["slab_serif", "condensed_sans", "overprint_color_blocking", "monumental_headline"]
  language_notes: "Tested with Indonesian words (Seduhan, Sangrai, Gula Aren) and Rupiah numerals (Rp 28.000); full Latin diacritic support."
  source: "Indonesian specialty coffee packaging & traditional enamel signage craft observations (principles extracted, no work copied)."
  confidence: medium
  status: candidate
  tested_in: "seduh-pagi-coffee-roastery (candidate_test_nusantara-kopitiam-stencil.png)"
  test_result: "Rendered 2160x2700 test slide; distinct enamel/woodblock craft hierarchy; legible Indonesian copy; status remains `candidate` awaiting explicit user approval."
  approved_by_user: false
```
