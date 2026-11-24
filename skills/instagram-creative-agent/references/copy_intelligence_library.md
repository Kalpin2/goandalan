# Copy Intelligence Library

Knowledge and instruction base for an AI agent that writes **Instagram captions, Cold DMs, Cold Call scripts, and follow-ups** for the @goandalan outreach and content system. Every output must be tailored to the specific client or prospect, sound like natural Bahasa Indonesia, and be bold and convincing without ever being dishonest.

This library is a living document. Section 12 defines how the agent expands and improves it from real outcomes.

------------------------------------------------------------------------

## 0. How the agent uses this library

For every piece of copy, in this order:

1.  **Read the client profile** (section 2). Separate known facts from inferences.
2.  **Fill the copy plan** (section 9) before writing a single sentence.
3.  **Draft** using patterns from sections 6-8.
4.  **Self-check** against section 10. Fix or regenerate. Hard fails are never shipped.
5.  **Output** the primary draft plus one alternate with a different lever.
6.  **Log** the pattern IDs used (section 12) so the system can learn.

Never skip the plan. Copy that skips the plan is usually generic.

------------------------------------------------------------------------

## 1. Core model: five layers (do not mix them)

| Layer | Question it answers | Examples |
|----|----|----|
| 1. Client | Who exactly are we talking to? | category, city, register, pain, specific detail |
| 2. Voice | How should it sound? | Hangat-Lokal, Tenang-Profesional, Bold-Langsung |
| 3. Persuasion | Why would they act? | specificity, already-done, zero-risk, gap |
| 4. Structure | What shape is the message? | hook, bridge, offer, ask |
| 5. Channel | What constraints apply? | caption, Cold DM #1, call, follow-up |

Weak copy usually mixes layers: a strong lever in the wrong voice, a good voice with no structure, or a great structure that ignores channel limits. Decide each layer separately.

------------------------------------------------------------------------

## 2. Client intelligence profile

### 2.1 Inputs available from the system

`business_name` (or `anonymized_name` for recycled content), `category`, `city`, `style_label` / `design_style`, `has_website`, `rating`, `priority_score`, `ux_flaw`, `ig_observation`, `notes`, phone availability, and `art_direction` / `qa_report` for generated assets.

### 2.2 Profile schema (agent fills this)

``` yaml
client_profile:
  display_name: ""            # anonymized_name when is_anonymized = 1
  category: ""
  city: ""
  known:                      # facts straight from lead data
    has_website: true|false
    ux_flaw: ""
    ig_observation: ""        # the one specific IG detail
    rating: null
  inferred:                   # label every guess as inferred
    register: casual | neutral | formal
    sapaan: Kak | Bapak/Ibu | Mas/Mbak | Anda
    energy: calm | warm | playful | bold
    trust_need: low | medium | high
    likely_pain: ""           # only if supported by known fields
  proof_available: []         # only real, user-provided proof
  needs_observation: true|false
```

### 2.3 Rules

-   **Evidence first.** A pain point or claim must trace to `known` fields. If it cannot, it is an inference and must be phrased as a question or a soft observation, never a fact.
-   **No observation, no fake detail.** If `ig_observation` is empty, set `needs_observation: true`. Either write the weaker category-level version and mark it so, or tell the user an observation is needed. Never invent a specific detail.
-   **Mirror the prospect's own register.** If their bio or captions are casual, with emoji and slang, soften the tone. If formal, stay formal. Mirror about 80%, do not imitate slang you would not naturally use; forced gaul reads as cringe.
-   **Sapaan default** is "Kak" for small businesses. Use "Bapak/Ibu" for clinics, legal, finance, education, hotels, and any prospect whose own voice is formal. Do not mix "Anda" with "Kak" in the same message.

------------------------------------------------------------------------

## 3. Voice library (tone archetypes)

| ID | Archetype | Traits | Sample line | Avoid |
|----|----|----|----|----|
| V1 | Hangat-Lokal | warm, neighborly, short sentences | "Kak, tempatnya hangat banget kelihatan dari fotonya." | corporate words, long clauses |
| V2 | Tenang-Profesional | calm, precise, respectful, no slang | "Kesan yang tenang di Instagram Bapak/Ibu layak terbawa ke website." | hype, exclamation marks |
| V3 | Santai-Gaul | playful, light humor, conversational | "Feed-nya udah enak dilihat, sayang kalau cuma berhenti di situ." | forced slang, jokes at their expense |
| V4 | Premium-Minimal | few words, confident, restrained | "Sebuah halaman yang sama tenangnya dengan tempat Anda." | emoji, discounts talk, urgency |
| V5 | Bold-Langsung | direct, punchy, point in line one | "Langsung saja: belum ada website, padahal kontennya sudah siap." | insults, shouting, pressure |
| V6 | Pengrajin-Bercerita | story-led, respectful of craft, sensory | "Setiap motif itu keputusan kecil. Website juga begitu." | tech jargon, generic startup talk |

### 3.1 Default mapping (override with the prospect's own voice when visible)

| Category signal | Default voice | Secondary |
|----|----|----|
| cafe, bakery, warung, F&B casual | V1 | V3 |
| streetwear, barbershop, tattoo, gym | V5 | V3 |
| hotel, villa, spa, fine dining | V4 | V2 |
| clinic, dentist, legal, accounting, school | V2 | V1 |
| batik, ceramics, craft, furniture | V6 | V1 |
| salon, bridal, photography | V1 | V4 |
| unknown | V1 (neutral, warm) | V2 |

**Override rule:** if the prospect's own language contradicts the default (a playful clinic, a formal streetwear brand), follow the prospect.

------------------------------------------------------------------------

## 4. Persuasion levers (for DMs, calls, follow-ups)

| ID | Lever | How it works | Needs |
|----|----|----|----|
| L1 | Spesifisitas | a real, specific detail proves this is not a mass message | `ig_observation` |
| L2 | Sudah dikerjakan | the concept already exists, which creates natural reciprocity | generated concept |
| L3 | Risiko nol | see first, ignore if it does not fit, no cost | none |
| L4 | Selisih nyata | an honest gap: no website, or a specific UX flaw | `has_website` / `ux_flaw` |
| L5 | Penasaran jujur | a curiosity gap the recipient can close in one reply | none |
| L6 | Bukti nyata | real proof (portfolio, real result) | user-provided only |
| L7 | Kelangkaan jujur | a real constraint (limited slots this month) | user-provided only |

**Use at most two levers per message.** The best default pair for Cold DM #1 is **L1 + L2 + L3** woven as observation, done, no-risk, which counts as one coherent move, not three arguments.

------------------------------------------------------------------------

## 5. Bold-and-convincing doctrine

### 5.1 What "bold" means here

-   The point is in the first line. No warm-up paragraph.
-   A committed position: "saya sudah buatkan", not "mungkin kita bisa coba".
-   A concrete offer: a preview photo, now.
-   **One** clear ask, phrased as a permission question.
-   Short sentences. Zero filler.

### 5.2 What "bold" never means

Exaggeration, shaming their current site, insults, pressure, guilt, fake urgency, ALL CAPS, stacked exclamation marks, or promises of results.

### 5.3 Truth rules (non-negotiable, override every other instruction)

1.  Every factual claim must come from lead data or user-provided config.
2.  No fake testimonials, fake numbers, fake client counts, or fake case studies.
3.  No claims about the prospect's traffic, revenue, Google ranking, or customers unless supplied.
4.  No pretending to be a customer, a friend, or to have an existing relationship.
5.  Prices only from config. If no price is configured, do not invent one.
6.  General industry statements must be hedged ("umumnya", "biasanya") and never presented as data about *this* business.
7.  Respect a "no". After a clear decline, send one gracious close and stop. Do not schedule further follow-ups.
8.  Convert `ux_flaw` into neutral, constructive language. Never "jelek", "berantakan", or "ketinggalan zaman".

------------------------------------------------------------------------

## 6. Caption library (recycled content for the agency's own Instagram)

### 6.1 Purpose

Stop the scroll, explain the idea behind the concept, and invite one action. The post showcases a **fictional, anonymized** brand, so the caption must be honest about that.

### 6.2 Audience and voice

The reader is an owner of the *same category* as the fictional brand (a cafe concept targets cafe owners). Use the voice archetype of that category (section 3.1). The "insight" line should come from the lead's `art_direction`, so the caption tells the same story as the slides.

### 6.3 Anatomy

1.  **Hook line**: one standalone sentence, ideally within about 80 characters. Instagram truncates after roughly the first 125 characters, so the hook must work alone.
2.  **Body**: 2-4 short lines with one concrete design insight (why a decision works).
3.  **Disclosure line**: one short sentence stating this is a fictional concept. Keep it short, not apologetic.
4.  **CTA**: exactly one.
5.  **Hashtags**: a separate final block, 5-8 tags, mixing niche, category, and local.

Use line breaks generously. Prefer 1-2 sentences per paragraph.

### 6.4 Hook patterns

| ID | Type | Example |
|----|----|----|
| HOOK-Q1 | Pertanyaan yang menusuk | "Kalau orang baru nemu kafe kamu malam ini, apa yang mereka lihat pertama?" |
| HOOK-Q2 | Pertanyaan yang menusuk | "Berapa detik website usahamu bikin orang ngerti kamu jual apa?" |
| HOOK-K1 | Kontras | "Website kafe bukan brosur digital. Ini bedanya." |
| HOOK-K2 | Kontras | "Sama-sama punya website. Yang satu dibaca, yang satu ditutup." |
| HOOK-D1 | Satu detail | "Satu detail kecil di slide 3 yang bikin semuanya terasa mahal." |
| HOOK-D2 | Satu detail | "Perhatiin jarak antar barisnya. Di situ rahasianya." |
| HOOK-B1 | Klaim berani yang dibuktikan slide | "Tiga detik pertama menentukan: lanjut scroll atau lanjut pesan." |
| HOOK-T1 | Mini-tip | "Satu aturan biar tulisan di HP nggak ketutup foto." |
| HOOK-N1 | Karakter fiktif | "Kenalan: Kopi Pelita. Kafenya fiktif, rapinya nyata." |
| HOOK-L1 | Hitungan jujur | "4 slide, 1 ide: kenapa judul besar kadang lebih menjual." |

Only use counts that are literally true (the number of slides, rules, steps).

### 6.5 CTA patterns

| ID | Type | Example |
|----|----|----|
| CTA-S1 | Simpan | "Simpan buat referensi kalau lagi bikin website usahamu." |
| CTA-D1 | DM kata kunci | "Mau konsep seperti ini untuk usahamu? DM kata KONSEP." |
| CTA-T1 | Tag | "Tag pemilik kafe yang perlu lihat ini." |
| CTA-Q1 | Pertanyaan | "Menurutmu slide mana yang paling kuat? Tulis angkanya." |

One CTA per caption. Do not stack "simpan, share, DM, dan follow".

### 6.6 Full example

```
Kalau orang baru nemu kafe kamu malam ini, apa yang mereka lihat pertama?

Di konsep ini kami mulai dari satu keputusan: judul besar yang kebaca sekali lirik di layar HP, sisanya mengalah. Hasilnya, pengunjung langsung tahu ini tempat apa, buka jam berapa, dan harus ngapain.

(Konsep fiktif untuk portofolio, nama dan detailnya dibuat ulang.)

Mau konsep serupa untuk usahamu? DM kata KONSEP.

#desainwebsite #websiteumkm #desainkafe #brandingumkm #desainigcarousel
```

### 6.7 Anonymization rules (hard guardrail)

The caption, hashtags, and any alt text must never contain the original business name, WA number, address, or recognizable unique details. Use `anonymized_name` only. Do not hint at the real business ("kafe di dekat pantai X" if that identifies it).

### 6.8 Emoji, formatting, language

-   0-2 emoji, only if the voice allows. None for V2 and V4.
-   No ALL CAPS except a short keyword CTA. No stacked "!!!".
-   Natural Bahasa Indonesia. Do not translate English slogans literally.

### 6.9 Caption anti-patterns

Generic openings ("Halo sobat..."), starting with the agency's name, burying the hook after greetings, three CTAs, fake urgency ("promo hari ini saja"), claims of results, and the disclosure line missing.

------------------------------------------------------------------------

## 7. Cold DM library

### 7.1 Hard constraints inherited from the system

-   Cold DM #1 contains **no URL** and no link of any kind.
-   The name "Alan" appears **at most once**.
-   It offers to send the **preview photo**, and the human sends it manually.
-   Nothing is sent automatically. The agent only drafts.
-   Target length **45-80 words**, at most 4 short paragraphs, **one** question at the end.

### 7.2 Anatomy

1.  **Line 1, Hook**: a specific observation (L1) or a direct gap (L4).
2.  **Line 2, Bridge**: what was done (L2), with the single mention of "Alan".
3.  **Line 3, Offer**: preview photo, zero risk (L3).
4.  **Line 4, Ask**: a permission question.

### 7.3 Opener patterns

| ID | Type | Template |
|----|----|----|
| OPEN-S1 | Detail spesifik | "Kak, {detail_ig} di IG {nama_usaha} itu menarik, kelihatan banget ada yang dipikirin, bukan asal posting." |
| OPEN-S2 | Detail + kontras | "{detail_ig} di IG {nama_usaha} kuat. Yang belum ada: tempat yang sama rapinya di luar Instagram." |
| OPEN-G1 | Gap langsung (no website) | "Kak, langsung saja: {nama_usaha} belum punya website, padahal {detail_ig}." |
| OPEN-D1 | Sudah jadi | "Kak, saya sudah buatkan konsep tampilan website untuk {nama_usaha}. Belum dipublish, belum ada yang lihat selain saya." |
| OPEN-C1 | Penasaran | "Kak, kalau {nama_usaha} punya website, halaman pertamanya akan terlihat seperti ini. Gambarnya sudah saya buat." |
| OPEN-Q1 | Pertanyaan | "Kak, kalau ada yang baru lihat IG {nama_usaha} lalu ingin pesan, sekarang mereka tinggal ngapain?" |
| OPEN-U1 | Observasi UX (has website) | "Kak, website {nama_usaha} sudah punya bahan bagus. Satu hal yang menurut saya bisa lebih ringan: {ux_flaw_ramah}." |

### 7.4 Bridge patterns

-   "Saya Alan, biasa bantu usaha {kategori} punya tampilan online yang rapi."
-   "Dari situ saya buatkan konsepnya, lengkap versi HP."
-   "Saya Alan. Konsepnya sudah jadi, bukan template kosong."

### 7.5 Offer and ask patterns

| ID | Offer | Ask |
|----|----|----|
| ASK-1 | "Bentuknya foto preview, gratis, tanpa kewajiban." | "Boleh saya kirim fotonya, Kak?" |
| ASK-2 | "Kalau tidak cocok, abaikan saja." | "Mau saya kirim sekarang?" |
| ASK-3 | "Saya tidak minta apa-apa dulu, cukup lihat." | "Boleh saya kirim lewat sini?" |
| ASK-4 | (formal) "Tidak ada biaya maupun kewajiban." | "Berkenan jika saya kirimkan foto preview-nya?" |

### 7.6 Complete examples

**A. Kafe, tanpa website, V1 Hangat-Lokal**

```
Kak, {detail_ig} di IG {nama_usaha} itu menarik, kelihatan banget ada yang dipikirin, bukan asal posting.

Dari situ saya buatkan konsep tampilan website untuk {nama_usaha}. Saya Alan, biasa bantu usaha kafe punya tempat online yang rapi. Belum dipublish, baru berupa foto preview.

Boleh saya kirim fotonya, Kak? Kalau nggak cocok, abaikan saja 🙏
```

**B. Streetwear, tanpa website, V5 Bold-Langsung**

```
Kak, langsung aja: {nama_usaha} belum punya website, padahal {detail_ig}. Terlalu bagus buat cuma hidup di feed.

Saya Alan. Konsep tampilannya sudah saya buat, lengkap versi HP. Foto preview siap dikirim, gratis, tanpa kewajiban.

Mau lihat?
```

**C. Hotel, V4 Premium-Minimal / V2 formal**

```
Selamat siang, Bapak/Ibu. {detail_ig} di Instagram {nama_usaha} memberi kesan yang tenang dan terjaga. Kesan itu layak terbawa ke halaman website.

Saya Alan. Saya telah menyusun satu konsep tampilan untuk {nama_usaha}, dalam bentuk foto preview. Tidak ada biaya maupun kewajiban.

Berkenan jika saya kirimkan?
```

**D. Sudah punya website dengan kekurangan UX, V2**

```
Kak, website {nama_usaha} sudah punya bahan yang bagus. Satu hal yang menurut saya bisa dibuat lebih ringan: {ux_flaw_ramah}.

Saya Alan. Saya sempat buat konsep tampilan yang menjawab itu, bentuknya foto preview, bukan penawaran.

Boleh saya kirim, Kak?
```

### 7.7 Follow-up halus (after the 48-hour timer)

Rules: a follow-up must bring **something new** (a detail, a choice, an easy exit). "Cuma mengingatkan" or "sudah dibaca belum?" is forbidden. No guilt. Always include an easy way to say no.

| ID | Pattern | Example |
|----|----|----|
| FU-1 | Nilai baru | "Kak, tambahan kecil: umumnya pengunjung buka dari HP, jadi saya sertakan juga versi HP-nya. Boleh saya kirim fotonya?" |
| FU-2 | Pintu keluar mudah | "Kak, kalau memang belum waktunya tidak apa-apa. Cukup balas 'nanti' dan saya tidak ganggu lagi. Fotonya tetap saya simpan." |
| FU-3 | Pilihan sempit | "Kak, untuk {nama_usaha} lebih cocok yang hangat atau yang minimal? Saya bisa sesuaikan konsepnya." |
| FU-4 | Detail baru | "Kak, saya baru lihat {detail_baru} di IG {nama_usaha}. Itu bikin saya ubah satu bagian konsepnya. Mau lihat versinya?" |
| FU-5 | Penutup elegan (final) | "Kak, ini pesan terakhir dari saya supaya tidak mengganggu. Kalau suatu hari butuh, tinggal balas di sini. Sukses terus untuk {nama_usaha}." |

Maximum **two** follow-ups per prospect, then mark the lead as done for outreach.

### 7.8 Objection replies (DM and call)

| Objection | Reply direction | Example |
|----|----|----|
| "Sudah ada IG, cukup." | Agree first, then show the different job | "Setuju, IG kuat untuk {kategori}. Website bukan pengganti, tapi tempat orang cek jam, lokasi, dan pesan tanpa scroll. Lihat dulu konsepnya?" |
| "Berapa harganya?" | Price only from config; else redirect to the concept | "Tergantung halaman yang dibutuhkan, makanya saya tunjukkan konsepnya dulu supaya kita bicara dari hal nyata, bukan angka di awang-awang." |
| "Nanti dulu / lagi sibuk." | Respect time, leave the door open | "Siap, Kak. Saya simpan dulu, kabari kapan pun enaknya." |
| "Sudah ada yang bikin." | Position as free reference | "Bagus. Anggap saja foto ini referensi gratis, siapa tahu berguna." |
| "Ini bot / spam?" | Be honest | "Bukan, Kak. Saya Alan, manusia, dan pesan ini saya kirim sendiri." |
| "Tidak tertarik." | One gracious close, stop | "Baik, Kak, terima kasih sudah dibalas. Sukses terus untuk {nama_usaha}." |

------------------------------------------------------------------------

## 8. Cold call library

### 8.1 Structure (matches the dashboard's three blocks)

| Block | Duration | Job |
|----|----|----|
| Pembuka | about 10 sec | name, ask for permission to continue, set a tiny time promise |
| Inti | about 15 sec | one specific detail plus what was built (L1 + L2) |
| Tutup | about 10 sec | ask permission to send the preview photo, zero risk |

### 8.2 Rules

-   Speak plainly. Write sentences meant to be **said**, not read: short, no semicolons, no stacked clauses.
-   Say the name at the start. Ask permission before continuing.
-   No emoji, no formatting in the spoken text.
-   The only ask: permission to send the photo, with a channel choice ("WhatsApp atau Instagram, mana yang lebih nyaman?").
-   If there is no answer, do not redial repeatedly. Send a DM instead. Maximum two call attempts in total.

### 8.3 Full example (V1 / V2 adaptable)

```
[Pembuka]
Halo, selamat {siang}. Dengan {Bapak/Ibu/Kak} pemilik {nama_usaha}? Saya Alan. Saya tidak akan lama, sekitar 30 detik. Boleh?

[Inti]
Saya sempat lihat {detail_ig} di Instagram {nama_usaha}. Dari situ saya buatkan konsep tampilan website, sudah jadi, bukan template kosong. {kalimat gap, hanya jika ada datanya}

[Tutup]
Boleh saya kirim foto preview-nya? Lewat WhatsApp atau Instagram, mana yang lebih nyaman? Kalau tidak cocok, tinggal diabaikan, tidak ada biaya.
```

### 8.4 Gatekeeper

"Saya ingin menyampaikan sesuatu soal tampilan online {nama_usaha} untuk Bapak/Ibu pemilik. Kapan waktu yang pas untuk beliau?"

Do not claim a relationship, an appointment, or an urgent matter that is not true.

### 8.5 Call objections

Reuse section 7.8 but shorten every reply to **one or two spoken sentences**, then return to the ask or exit politely.

------------------------------------------------------------------------

## 9. Copy planning schema (agent fills before drafting)

``` yaml
copy_plan:
  channel: caption | cold_dm_1 | followup | cold_call
  client_profile_ref: ""
  voice: V1 | V2 | V3 | V4 | V5 | V6
  sapaan: ""
  levers: []                 # max 2 (cold_dm_1 may use L1+L2+L3 as one move)
  patterns_used: []          # IDs: HOOK-*, OPEN-*, ASK-*, FU-*, CTA-*
  specific_detail_used: true|false
  claims_made: []            # each with its data source
  claims_unsupported: []     # must be empty before output
  word_count_target: ""
  differs_from_last_output: ""   # how this avoids repeating recent copy
  needs_observation: true|false
```

------------------------------------------------------------------------

## 10. Self-check rubric

### 10.1 Hard fails (never ship, regenerate)

-   URL or link inside Cold DM #1.
-   "Alan" appears more than once in a DM.
-   Original business name, WA number, or address appears in recycled content copy.
-   Any claim not traceable to data or config (fake number, testimonial, price, ranking).
-   Pressure, guilt, shaming, or fake urgency.
-   More than one question or ask in a DM.
-   Disclosure line missing from a recycled-content caption.
-   Message continues after the prospect declined.

### 10.2 Scored dimensions (1-5 each, every dimension must be 4 or higher)

1.  **Specificity**: at least one real detail, not a template.
2.  **Hook strength**: would the first line make a stranger keep reading?
3.  **Boldness with integrity**: committed and direct, yet fully truthful.
4.  **Voice fit**: matches the prospect's register and category.
5.  **Clarity of ask**: one ask, easy to answer in one word.
6.  **Naturalness**: sounds like a real Indonesian person, no translated marketing speak.
7.  **Brevity**: within length targets, no filler sentence.

Maximum **two** regeneration rounds. If still below 4, ship the best draft and flag the weak dimension for the human.

### 10.3 Banned phrases

"solusi terbaik", "terpercaya dan profesional", "kami adalah perusahaan", "perkenalkan nama saya ... dari ...", "sehubungan dengan", "dengan hormat" (in DMs), "kesempatan emas", "jangan sampai ketinggalan", "dijamin", "100% puas", "hanya hari ini", "buruan", "gratis!!!", "semoga sehat selalu" as an opener, and "cuma mengingatkan".

------------------------------------------------------------------------

## 11. Variation control

Prospects in the same city and category often compare messages. Avoid obvious mass-sending:

-   Do not reuse the same opener ID for consecutive leads in the same category and city.
-   Do not start two messages with the same first five words.
-   Rotate hook types in captions: never the same hook type more than twice in a row.
-   Vary sentence rhythm and the ask wording (ASK-1 to ASK-4).
-   Keep the last 10 outputs per channel in the log and compare before drafting.

------------------------------------------------------------------------

## 12. Self-expansion and learning protocol

The agent cannot change its own model. It improves by recording what it wrote, what happened, and what the human changed, then proposing better patterns for approval.

### 12.1 Learning signals (strongest first)

1.  **Human edits to drafts.** The difference between the agent's draft and the text the human actually sent or posted is the most direct signal of voice fit.
2.  **Outcomes.** Lead status transitions: CONTACTED -> INTERESTED (win) versus IGNORED_48H (no response), plus reply text pasted by the user.
3.  **Reviewer corrections.** Social media team corrections in the review workflow (category, note, slide).
4.  **Post metrics (optional, manual).** Saves, shares, DMs triggered by a caption.
5.  **Research.** Copywriting references, strong local examples, and category-specific language the agent was missing.

### 12.2 What to log per piece of copy

``` yaml
copy_log:
  lead_id: ""
  channel: caption | cold_dm_1 | followup | cold_call
  date: ""
  category: ""
  city: ""
  has_website: true|false
  voice: ""
  sapaan: ""
  patterns_used: []
  levers: []
  word_count: 0
  had_specific_detail: true|false
  original_draft: ""
  final_text: ""              # what the human actually used
  edit_summary: ""            # e.g. "shortened, removed emoji, changed Kak to Bapak"
  outcome: no_reply | replied_neutral | interested | declined | ignored_48h | n/a
  outcome_at: ""
  notes: ""
```

For recycled content, store **anonymized names only**.

### 12.3 Learning loop (every 20 pieces of copy, or weekly, whichever comes first)

1.  **Review edits.** Which changes did humans make repeatedly? (shorter, softer, different sapaan, removed claim) Turn each repeated edit into a candidate rule.
2.  **Review outcomes.** Compare pattern groups **within the same category and the same has_website value** so the comparison is fair.
3.  **Find gaps.** Which categories, cities, objections, or situations had no good pattern? Which output hit hard fails or low scores?
4.  **Draft candidate patterns** (max 3 per cycle) using the schema in 12.5. Each must be distinct from existing patterns.
5.  **Test with an exploration budget.** About 1 in 5 drafts may use a `candidate` pattern, logged as such. Do not test candidates on the highest-priority leads until the pattern has some evidence.
6.  **Evaluate.** Move to `testing` after use, `approved` only after enough evidence and explicit user approval.
7.  **Prune.** Retire patterns that repeatedly get declines, edits, or complaints. Merge near-duplicates.
8.  **Report** to the user in the format in 12.7.

### 12.4 Statistical honesty

-   Fewer than **15 sends** per pattern is anecdotal. Call it "leaning", never "proven".
-   Report raw counts alongside percentages (for example, "3 of 14").
-   Do not claim causality. Lead quality (priority score, rating, has_website) and timing confound results. Mention likely confounders.
-   Never overfit to one lucky reply.
-   A new category or city with little data should be handled by profile-building and cautious defaults, not by borrowing conclusions from a different category.

### 12.5 Pattern entry schema

``` yaml
pattern:
  id: ""                      # e.g. OPEN-S9
  channel: caption | dm | call | followup
  slot: hook | opener | bridge | offer | ask | cta | objection_reply
  template: ""
  levers: []
  voice_fit: []
  works_for: []               # categories / situations
  caution: []
  distinct_from: ""           # nearest existing pattern and how this differs
  evidence: { uses: 0, replies: 0, interested: 0, declined: 0, ignored: 0, human_edited: 0 }
  source: observed_outcome | human_edit | reviewer_correction | research
  confidence: low | medium | high
  status: candidate | testing | approved | retired
  approved_by_user: false
```

### 12.6 Learning rules

-   **Truth rules (section 5.3) and hard fails (10.1) cannot be overridden by anything learned.** A pattern that "converts better" but breaks them is rejected.
-   **Human edits outrank statistics.** If the user repeatedly rewrites a pattern, treat that as a stronger signal than a small outcome sample.
-   **Nothing becomes `approved` without the user's explicit approval.**
-   **No duplicates.** If `distinct_from` cannot name a real difference, merge instead.
-   **Keep the core readable.** Candidates and logs live in separate files (`copy_candidates.md`, `copy_learning_log.md`). If this library grows too large, split it by channel and keep an index.
-   **Local language.** Actively collect natural Indonesian phrasing used by real business owners in each category and city, and prefer it over translated marketing language.
-   **Protect prospect privacy.** Logs must not leak into public captions, and recycled content must stay anonymized end to end.

### 12.7 Cycle report format

``` markdown
### Copy learning cycle N
- Period / sample: (n DMs, n captions, n calls)
- Repeated human edits found:
- Outcome signals (with raw counts and confounders):
- Gaps found:
- Candidate patterns added (max 3):
- Patterns recommended for approval:
- Patterns recommended for retirement or merge:
- Risks or things to verify:
```

------------------------------------------------------------------------

## 13. Pre-flight checklist (quick version)

-   [ ] Profile filled, known versus inferred separated
-   [ ] Real specific detail used (or flagged `needs_observation`)
-   [ ] Voice and sapaan match the prospect
-   [ ] One lever pair at most, one ask only
-   [ ] No unsupported claim, no price invented
-   [ ] DM #1: no URL, "Alan" once, 45-80 words
-   [ ] Recycled caption: anonymized and disclosure line present
-   [ ] Not a repeat of recent openers
-   [ ] Pattern IDs logged
