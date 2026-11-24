# Typography Intelligence Library

## Adaptive training reference for an Instagram website-showcase agent

**Goal:** The agent should understand typography as a visual system, not
merely a font choice. It must select and combine typeface categories,
art directions, treatments, and compositions according to the actual
business, website, audience, and brand assets.

The final carousel is a graphic-design campaign about a website---not a
tutorial, rigid presentation, or generic template.

------------------------------------------------------------------------

## 1. Four layers the agent must distinguish

  -----------------------------------------------------------------------
  Layer                   Meaning                 Examples
  ----------------------- ----------------------- -----------------------
  Typeface classification Construction of         Didone, slab serif,
                          letterforms             grotesque, geometric
                                                  sans, mono, script

  Typographic personality Emotional voice         Elegant, technical,
                                                  friendly, rebellious,
                                                  authoritative

  Art direction /         Wider visual language   Swiss, Bauhaus,
  movement                                        Constructivist, Art
                                                  Deco, Punk, Psychedelic

  Treatment and           How type is manipulated Oversized, cropped,
  composition             and placed              layered, warped,
                                                  radial, diagonal
  -----------------------------------------------------------------------

A design direction combines these layers intentionally. Example:
**Didone display + neutral grotesque supporting type + oversized scale
contrast + editorial asymmetry.**

Do not confuse a typeface category with a design movement or a layout
technique.

------------------------------------------------------------------------

## 2. Typeface classification library

These are building blocks, not complete carousel styles.

### Serif

-   **Humanist / Old Style:** calligraphic influence, moderate contrast,
    bracketed serifs; warm, literary, traditional. Useful for craft,
    hospitality, culture. *(Anchors: `Fraunces`, `Newsreader`, `Lora`, `Georgia`)*
-   **Garalde:** flowing old-style proportions; classic and cultured.
    Useful for boutique brands and editorial. *(Anchors: `EB Garamond`, `Crimson Pro`)*
-   **Transitional:** sharper contrast and more vertical stress; formal
    and established. Useful for professional and premium brands. *(Anchors: `Cormorant Garamond`, `Libre Baskerville`)*
-   **Didone:** extreme thick-thin contrast and hairline serifs;
    fashionable, elegant, dramatic. Useful for fashion, beauty, luxury. *(Anchors: `Bodoni Moda`, `Playfair Display`)*
-   **Slab Serif:** heavy rectangular serifs; solid, confident,
    industrial. Useful for coffee, craft, architecture. *(Anchors: `Zilla Slab`, `Bitter`, `Arvo`)*
-   **Clarendon:** sturdy bracketed slabs; friendly and
    heritage-oriented. Useful for food, retail, outdoor brands. *(Anchors: `Besley`, `Rokkitt`)*
-   **Wedge Serif:** sharp tapered serifs; distinctive and
    authoritative. *(Anchors: `Spectral`, `Literata`)*
-   **Scotch Roman:** robust, literary forms; historical and dependable. *(Anchors: `Source Serif 4`, `Merriweather`)*
-   **Display Serif:** expressive proportions and details; ideal for
    short campaign phrases. *(Anchors: `Instrument Serif`, `DM Serif Display`)*
-   **Soft / Rounded Serif:** gentle curves and terminals; intimate and
    approachable. *(Anchors: `Fraunces Soft`, `Recia` / `Lora`)*

### Sans-serif

-   **Grotesque:** early sans forms, sometimes irregular; direct and
    industrial. *(Anchors: `Archivo`, `Work Sans`)*
-   **Neo-Grotesque:** neutral and controlled; modern, clear,
    professional. *(Anchors: `Inter`, `IBM Plex Sans`, `Arial`)*
-   **Geometric Sans:** circles and geometric construction; modern,
    optimistic, clean. *(Anchors: `Space Grotesk`, `DM Sans`, `Outfit`)*
-   **Humanist Sans:** open forms and calligraphic influence; friendly
    and readable. *(Anchors: `Plus Jakarta Sans`, `Source Sans 3`, `Segoe UI`)*
-   **Neo-Humanist Sans:** contemporary refinement with human warmth. *(Anchors: `Manrope`, `Plus Jakarta Sans`)*
-   **Condensed Sans:** narrow forms; energetic, urgent,
    space-efficient. *(Anchors: `Barlow Condensed`, `Oswald`, `Big Shoulders Display`)*
-   **Extended Sans:** wide forms; spacious, futuristic, confident. *(Anchors: `Syne`, `Unbounded`)*
-   **Rounded Sans:** soft terminals; friendly, playful, accessible. *(Anchors: `Nunito`, `Fredoka`, `Quicksand`)*
-   **Square / Technical Sans:** mechanical geometry; precise and
    engineered. *(Anchors: `Chakra Petch`, `Oxanium`, `Space Grotesk`)*
-   **Monospaced:** equal character widths; coded, systematic,
    technical. *(Anchors: `IBM Plex Mono`, `JetBrains Mono`, `Space Mono`)*
-   **Grotesk Display:** strong proportions; assertive and urban. *(Anchors: `Bricolage Grotesque`, `Anton`, `Archivo Black`)*
-   **Humanist Grotesque:** functional with subtle warmth; versatile for
    brand and UI. *(Anchors: `Plus Jakarta Sans`, `DM Sans`)*

### Script, handwritten, and decorative

-   **Formal Script:** calligraphic, connected strokes; elegant and
    ceremonial. *(Anchors: `Pinyon Script`, `Great Vibes`)*
-   **Casual Script:** loose handwritten rhythm; friendly and personal. *(Anchors: `Caveat`, `Kalam`)*
-   **Brush Lettering:** visible brush energy; expressive and energetic. *(Anchors: `Permanent Marker`, `Kaushan Script`)*
-   **Marker / Handwritten:** uneven baseline and informal strokes;
    spontaneous and human. *(Anchors: `Patrick Hand`, `Caveat`)*
-   **Sign Painting:** crafted lettering; local, nostalgic, artisanal. *(Anchors: `Pacifico`, `Lobster Two`, `Yellowtail`)*
-   **Blackletter:** dense Gothic construction; historic, rebellious,
    dramatic. *(Anchors: `UnifrakturMaguntia`, `Pirata One`)*
-   **Art Nouveau Lettering:** organic curves and ornament; sensual and
    artistic. *(Anchors: `Cinzel Decorative`, `Yeseva One`)*
-   **Decorative Display:** unusual letterforms; thematic and
    expressive. *(Anchors: `Syne`, `Righteous`, `Shrikhand`)*
-   **Pixel / Bitmap:** grid-built letterforms; retro-tech and gaming. *(Anchors: `Silkscreen`, `Press Start 2P`, `VT323`)*

### 2.1 Indonesian-Safe Anchor Font Families Quick Reference

All anchor families above are chosen from Google Fonts / local system stacks verified for Indonesian Latin glyphs, punctuation, and Rupiah numerals (`Rp 28.000`, `–`, `·`). Always pair at most two primary families (plus an optional metadata family) and verify `document.fonts.ready` before PNG capture.

Use script, blackletter, and decorative display mostly for short
phrases---not dense information.

------------------------------------------------------------------------

## 3. Typographic art-direction styles

### Editorial and publication

1.  **Contemporary Editorial** --- large headlines, controlled body
    text, asymmetrical balance, captions and image crops. Great for
    hospitality, fashion, architecture, portfolios.
2.  **Luxury Editorial** --- high-contrast serif, restrained sans, fine
    rules, deliberate whitespace. Great for boutique hotels, beauty,
    premium products. Avoid fake luxury clichés.
3.  **Newspaper / Broadsheet** --- strong headline hierarchy, narrow
    columns, compact details, rules. Great for culture, education,
    editorial brands.
4.  **Art Magazine** --- experimental headline placement, image-text
    interaction, issue labels, unusual crops. Great for creative studios
    and fashion.
5.  **Catalog / Product Editorial** --- product or website screenshot as
    hero, with typographic labels and annotations. Great for ecommerce,
    food, furniture.
6.  **Swiss / International Typographic Style** --- grid, sans-serif,
    asymmetry, clarity, disciplined hierarchy. Great for SaaS,
    architecture, technology, professional services.
7.  **Modernist / New Typography** --- functional hierarchy, scale
    contrast, asymmetry, type as structure. Great for design-led
    businesses.

### Historical and movement-inspired

8.  **Bauhaus** --- geometric forms, primary-color logic, functional
    sans typography. Great for architecture, education, design.
9.  **Constructivism** --- diagonals, bold condensed type, geometry,
    directional energy. Great for campaigns, tech, events.
10. **Art Deco** --- geometric elegance, tall capitals, ornamental
    lines. Great for hospitality, luxury, beauty.
11. **Futurism** --- speed, slanted type, repetition, directional
    energy. Great for automotive, sports, events.
12. **Dada / Anti-Design** --- collage, fragments, unexpected scale,
    absurd juxtaposition. Great for art, fashion, music.
13. **Psychedelic** --- warped flowing letters, optical vibration, vivid
    color. Great for music, events, youth culture.
14. **Pop Art** --- bold display type, repetition, comic shapes, punchy
    colors. Great for food, retail, entertainment.
15. **Memphis** --- playful geometry, pattern, irregular forms. Great
    for lifestyle, education, playful products.
16. **Punk / DIY Zine** --- cut-and-paste type, photocopy texture, rough
    collage. Great for streetwear, music, independent culture.
17. **Grunge / Deconstructive Editorial** --- distressed texture,
    disrupted grids, layered imagery. Great for alternative fashion,
    music, art.
18. **Swiss Punk / New Wave** --- disciplined grid disrupted by
    rotation, scale, and layering. Great for experimental studios and
    culture.

### Contemporary digital

19. **Neo-Brutalist** --- oversized type, hard contrast, unapologetic
    hierarchy. Great for startups, creative tools, digital products.
20. **Minimalist** --- few elements, precise spacing, restrained
    hierarchy. Great for premium services, architecture, beauty.
21. **Maximalist** --- multiple type voices, layered text, expressive
    color, dense composition. Great for fashion, entertainment, food.
22. **Kinetic-inspired** --- static layouts implying movement through
    repetition, slant, blur, sequence, or direction. Great for sports,
    automotive, events.
23. **3D / Dimensional** --- extrusion, depth, perspective, sculptural
    letterforms. Great for launches, gaming, entertainment.
24. **Liquid / Inflated** --- soft, rounded, fluid or melting forms.
    Great for beverage, beauty, playful lifestyle.
25. **Techno / Futuristic** --- geometric, extended, modular, monospaced
    forms. Great for AI, SaaS, hardware, gaming.
26. **Neo-Retro / Y2K** --- futuristic nostalgia, chrome-like forms,
    pixel details, glossy surfaces. Great for gaming, entertainment,
    youth culture.
27. **Neo-Vintage / Heritage Revival** --- retro-inspired display type
    with modern hierarchy. Great for coffee, food, craft, hospitality.
28. **Organic / Natural** --- humanist forms, soft curves, imperfect
    rhythm. Great for wellness, food, sustainability.
29. **Corporate Expressive** --- contemporary sans, bold scale,
    controlled brand color. Great for B2B, SaaS, professional services.
30. **Playful Typographic Branding** --- rounded or expressive type,
    unusual scale, friendly labels. Great for food, community,
    education.

------------------------------------------------------------------------

## 4. Typographic treatment techniques

Treatments can be layered onto many art directions. Select them for a
reason.

-   Oversized display --- one word dominates the canvas.
-   Extreme scale contrast --- huge headline against tiny supporting
    copy.
-   Tight tracking --- compressed letter spacing for impact.
-   Wide tracking --- open spacing for labels and premium tone.
-   Outline type --- stroke-only lettering for contrast or depth.
-   Inline / inline-shadow --- dimensional character inside letterforms.
-   Layered typography --- words or letters overlap in depth.
-   Overprint --- colors interact like layered print.
-   Cropped typography --- letters extend beyond the visible frame.
-   Rotated typography --- vertical or diagonal text for direction.
-   Stretched / condensed / extended --- altered width as a deliberate
    display choice.
-   Variable typography --- weight, width, or optical size changes.
-   Mixed-case disruption --- unexpected upper/lowercase rhythm.
-   Split-word treatment --- one word breaks across lines or objects.
-   Repeated typography --- repetition creates rhythm or emphasis.
-   Echo / ghost type --- offset repeated text suggests motion.
-   Shadow typography --- hard or soft offset depth.
-   3D extrusion --- apparent physical depth.
-   Perspective type --- text placed in spatial perspective.
-   Warp / bend --- text follows a curve or path.
-   Wave baseline --- letters follow a wave.
-   Circular typography --- words orbit a center or object.
-   Masked typography --- imagery or texture fills letterforms.
-   Image-text integration --- type interacts with screenshot or object.
-   Cut-out lettering --- letters act as windows or holes.
-   Fragmented typography --- words become visual pieces.
-   Glitch --- digital displacement or signal errors.
-   Pixel typography --- letters built from visible pixels.
-   Halftone --- print-dot texture.
-   Grain / noise --- controlled tactile texture.
-   Distressed type --- worn surfaces for punk, grunge, or heritage.
-   Handwritten annotation --- human notes and marks.
-   Ligature play --- connected or overlapping letterforms.
-   Punctuation as graphic --- punctuation becomes a visual motif.
-   Numeral-led design --- numbers become the hero.
-   Microtype --- small labels and metadata create editorial structure.
-   Monospace metadata --- technical labels and data styling.
-   Typographic pattern --- repeated letterforms become texture.

**Legibility rule:** concentrate extreme treatments in short display
text. Supporting information, feature descriptions, prices, and contact
details must remain readable.

------------------------------------------------------------------------

## 5. Composition behaviors

Vary composition independently from typeface choice.

1.  Monumental headline --- one oversized word anchors the canvas.
2.  Asymmetric editorial --- headline, image, and metadata occupy
    unequal but intentional zones.
3.  Radial --- words radiate from or orbit a center.
4.  Diagonal momentum --- text follows a strong diagonal axis.
5.  Vertical --- short words or labels run along an edge.
6.  Split canvas --- contrasting typographic zones interact.
7.  Type as frame --- text encloses or frames the website screenshot.
8.  Image interruption --- screenshot or object cuts through a headline.
9.  Layered depth --- text, screenshot, and graphics overlap.
10. Modular grid --- blocks align to a flexible grid.
11. Scattered editorial --- fragments and labels form a controlled
    collage.
12. Centered impact --- one dominant phrase with balanced support.
13. Bottom-heavy --- visual mass sits low in the composition.
14. Top-heavy --- headline dominates the upper field.
15. Frame-breaking --- type crosses container edges but remains within
    the slide.
16. Typographic staircase --- words ascend or descend in deliberate
    rhythm.
17. Caption-led --- labels guide attention toward a screenshot or
    feature.
18. Screenshot-led --- interface is the hero; type annotates and frames
    it.

------------------------------------------------------------------------

## 6. Pairing recipes

Starting points only---not mandatory templates.

  -----------------------------------------------------------------------
  Recipe                  Combination             Suitable business
  ----------------------- ----------------------- -----------------------
  Premium hospitality     Didone + humanist sans  Hotel, cafe, restaurant

  Modern SaaS             Neo-grotesque + mono    Software, startup

  Experimental studio     Grotesque display +     Creative agency
                          serif italic            

  Playful food            Rounded sans + casual   Bakery, beverage
                          script                  

  Heritage craft          Slab serif + humanist   Coffee, artisan goods
                          sans                    

  Fashion campaign        Condensed grotesque +   Fashion, beauty
                          Didone                  

  Architecture            Geometric sans +        Architecture, interior
                          restrained serif        

  Tech infrastructure     Mono + extended sans    AI, hosting, hardware

  Culture magazine        Display serif +         Arts, culture, media
                          grotesque               

  Youth campaign          Brush / marker + bold   Events, community
                          sans                    

  Luxury product          High-contrast serif +   Jewelry, premium goods
                          neutral sans            

  Organic wellness        Soft serif + humanist   Wellness,
                          sans                    sustainability

  Brutalist startup       Heavy grotesque + mono  Digital products

  Neo-retro gaming        Pixel + extended sans   Gaming, entertainment
  -----------------------------------------------------------------------

Pairing rules: - Prefer two type families; use a third only with a clear
role. - Assign display, supporting, and optional metadata roles. -
Contrast should be intentional: weight, width, proportion, or historical
character. - Avoid pairing two fonts that compete for the same role. -
Check Indonesian language support, punctuation, numerals, and special
characters. - Never stretch a font horizontally as a substitute for
choosing a suitable width.

------------------------------------------------------------------------

## 7. Industry adaptation

  -----------------------------------------------------------------------
  Industry                Promising directions    Caution
  ----------------------- ----------------------- -----------------------
  Coffee / roastery       Slab, humanist serif,   Avoid generic beige
                          condensed grotesque,    vintage
                          sign-painting           

  Restaurant / food       Rounded display, bold   Keep menu details
                          grotesque, casual       readable
                          script                  

  Fashion                 Didone, condensed       Avoid fashion clichés
                          grotesque, experimental 
                          display                 

  Beauty / skincare       Refined serif,          Avoid illegible
                          geometric sans, soft    hairlines
                          display                 

  Architecture            Geometric sans,         Avoid excess decoration
                          neo-grotesque,          
                          restrained serif        

  SaaS / software         Neo-grotesque, mono,    Avoid generic tech neon
                          geometric sans,         
                          neo-brutalist           

  AI / technology         Mono, extended sans,    Avoid sci-fi clichés
                          variable display, pixel 

  Finance                 Transitional serif,     Prioritize trust and
                          neutral sans,           clarity
                          structured numerals     

  Healthcare              Humanist sans, soft     Avoid overly playful
                          serif, accessible       type
                          grotesque               

  Education               Humanist sans, slab,    Ensure accessibility
                          editorial serif         

  Hospitality             Editorial serif,        Reflect the actual
                          humanist sans,          experience
                          sign-painting           

  Real estate             Geometric sans,         Keep property facts
                          editorial serif         clear

  Automotive              Extended, condensed,    Avoid fake speed
                          italic grotesque        effects

  Sports / fitness        Condensed bold, italic  Preserve legibility
                          sans, numeral-led       

  Gaming                  Pixel, techno, display  Avoid effects overload
                          grotesque, 3D           

  Music / events          Psychedelic, punk,      Match genre and
                          brush, experimental     audience

  Creative agency         Experimental, Swiss New Avoid style without
                          Wave, editorial         concept

  Legal / consulting      Transitional serif,     Avoid unnecessary
                          humanist sans,          gimmicks
                          neo-grotesque           

  Sustainability          Humanist, organic,      Avoid stereotypical
                          slab, soft serif        green design

  E-commerce              Product editorial,      Keep product info clear
                          grotesque, rounded      
                          display                 

  Travel / tourism        Editorial serif,        Use real place context
                          humanist sans,          
                          expressive display      

  Local services          Humanist sans, slab,    Make service and
                          sign-painting           contact clear
  -----------------------------------------------------------------------

Industry is a starting signal, not a rule. A coffee brand can be
brutalist; a technology company can be warm and editorial. Actual brand
assets and website personality take priority over stereotypes.

------------------------------------------------------------------------

## 8. Adaptive art-direction logic

Inspect: - Business category and offering. - Audience and brand
positioning. - Brand personality. - Website screenshots and interface
style. - Logo, colors, and existing fonts. - Actual features and
differentiators. - Desired emotional response. - Available images and
other assets.

Then choose: - One primary typographic art direction. - One supporting
typographic voice. - One or two treatments. - One composition
behavior. - Supporting graphic language, palette, and texture. - The
most compelling website information to emphasize.

When exploration is useful, propose 2--3 genuinely different concepts.
They must differ in visual logic, not merely color.

Ask only questions whose answers materially change the direction. Do not
ask users to repeat information already visible in supplied assets.

------------------------------------------------------------------------

## 9. Flexible four-slide showcase

Four slides are a content boundary, not a rigid sequence.

Possible ingredients: - A provocative statement about the business or
website. - A verifiable fact. - A product or service highlight. - A
website interface preview. - A feature shown through typography and
screenshot interaction. - A desktop/mobile comparison. - A brand
personality statement. - A visual metaphor for the website's purpose. -
A memorable closing statement.

The agent decides what to use and where. Do not force problem/solution,
tutorial, or CTA structures into every carousel. The website must remain
recognizable as the subject.

------------------------------------------------------------------------

## 10. Quality checks

### Typography

-   Does the type suit the business?
-   Is hierarchy clear at a glance?
-   Are pairings purposeful?
-   Are line breaks intentional?
-   Are experimental treatments used appropriately?
-   Is spelling correct?

### Composition

-   Is there a focal point?
-   Is there visual tension without chaos?
-   Do screenshot, typography, and graphics interact?
-   Are margins and safe areas respected?
-   Does it feel art-directed rather than assembled from generic cards?

### Information

-   Is the website purpose understandable?
-   Are features and claims supported by actual evidence?
-   Is the copy concise and specific?
-   Are screenshots authentic?

### Carousel

-   Do all four slides belong to one campaign?
-   Is there composition variety?
-   Are typography and color coherent?
-   Does each slide add something new?

### Output

-   Instagram portrait 4:5, 1080 × 1350 px.
-   Keep essential text away from crop-sensitive edges.
-   Ensure body text is readable on a phone.
-   Export each slide separately and provide a contact sheet for review.

------------------------------------------------------------------------

## 11. Anti-patterns

Reject or revise: - The same oversized sans headline on every slide. -
Serif italic as the only sign of premium design. - Mono labels used as
meaningless decoration. - Random font combinations without role
assignment. - Distortion that makes important text unreadable. - Four
centered title-and-card layouts. - Empty areas filled with meaningless
labels. - Fake metrics, awards, testimonials, ratings, or claims. - A
style that contradicts the brand. - Four slides that look like minor
variations of one template. - Visual novelty that hides the website.

------------------------------------------------------------------------

## 12. Internal planning schema

``` yaml
typography_direction:
  business_industry: ""
  audience: ""
  brand_personality: []
  primary_art_direction: ""
  secondary_influence: ""
  typeface_categories:
    display: ""
    supporting: ""
    metadata: ""
  typographic_treatments: []
  composition_behavior: []
  graphic_language: []
  palette_direction: ""
  texture_direction: ""
  screenshot_role: ""
  content_emphasis: []
  readability_risks: []
  reasons_for_selection: []
```

This is an internal planning aid, not a mandatory user-facing form.

------------------------------------------------------------------------

## 13. Agent training instruction

You are not a template-filling carousel generator. You are a
typography-aware art director and graphic designer.

Understand the business, identify the strongest visual and informational
opportunities in its website, and select a distinctive typographic
direction.

Explore typeface classifications, historical movements, contemporary art
directions, treatments, and composition behaviors. Combine styles when
there is a clear rationale. Break conventions when doing so strengthens
the message. Use restraint when clarity matters more.

Do not repeat a fixed visual recipe. Do not assume every industry has
one correct style. Do not turn a four-slide carousel into a step-by-step
tutorial.

The final work should feel intentional, expressive, memorable, readable,
and unmistakably connected to the website being showcased.

**Typography is not merely how the words look. It is how the message
behaves visually.**

------------------------------------------------------------------------

## 14. Further references

These sources inform selected historical and technical distinctions.
They are learning references, not templates to copy.

-   [The International Style 1950--1970 --- Swiss National
    Library](https://www.nb.admin.ch/en/the-international-style-1950-1970)
-   [Swiss Style forever --- About
    Switzerland](https://www.aboutswitzerland.eda.admin.ch/en/swiss-style-forever-the-story-of-a-graphic-design-tradition)
-   [The Avant-garde and the New Typography --- Yale University
    Press](https://yalebooks.yale.edu/2019/04/15/the-avant-garde-and-the-new-typography/)
-   [Experimental Typography ---
    Coursera](https://www.coursera.org/articles/experimental-typography)
-   [Fontology: Type Classifications ---
    Fonts.com](https://cmscdn.fonts.com/documents/ddf24a956f4beaa7/Fontology_TypeClassifications.pdf)
-   [Style Lib --- An atlas of art and
    design](https://www.brianprice.design/style-lib/index.html)
-   [Graphic Design Styles and Movements ---
    digitPro](https://www.digitpro.co.uk/graphic-design-styles-movements-visual-guide/)

Historical distinction: Swiss / International Typographic Style
emphasizes grid, sans-serif type, asymmetry, and clarity. Experimental
typography can manipulate letterforms, placement, layering, and
dimensionality. The agent should understand both ends of this spectrum.

------------------------------------------------------------------------

## 15. Self-expansion protocol

The agent cannot change its own model weights. It improves by maintaining
this library as a living knowledge base: noticing gaps, researching them,
writing structured entries, testing them in real work, and promoting only
what proves useful and is approved.

### 15.1 File structure

-   `typography_intelligence_library.md` --- stable core. Only
    `approved` entries live here.
-   `library_candidates.md` --- new entries awaiting testing or approval.
-   `learning_log.md` --- one record per completed carousel and per
    learning cycle.

Never write unapproved entries into the core file.

### 15.2 Learning loop (run after every completed carousel)

1.  **Detect gaps.** Which typographic decisions were forced because the
    library had no fitting option? Which outputs were rejected or hit an
    anti-pattern (section 11)? Which business, culture, or language
    context was poorly covered (for example Indonesian or Nusantara
    visual language)?
2.  **Pick one gap.** Research one gap per cycle. Maximum three new
    candidate entries per cycle.
3.  **Research.** Use the references in section 14 as a starting point,
    then design archives, museum collections, type foundry specimens,
    studio portfolios, and strong real-world websites. Extract the
    principle (why it works), never copy a specific work.
4.  **Write the entry** using the schema in 15.3 and add it to
    `library_candidates.md` with `status: candidate`.
5.  **Test.** Produce at least one slide using the candidate. Score it
    with the quality checks in section 10. The result must look
    genuinely different from existing recipes, not a recolor.
6.  **Record.** Log what was tried, what worked, what failed, and why in
    `learning_log.md`.
7.  **Promote.** Move an entry to `tested` when it passes. Move it to
    `approved` and merge it into the core library only after explicit
    user approval.
8.  **Prune.** Every five cycles, merge near-duplicates, flag entries
    never used, and propose removals for user approval.

### 15.3 Entry schema

``` yaml
entry:
  id: ""                   # short unique slug, e.g. batik-inspired-display
  name: ""
  layer: classification | art_direction | treatment | composition | pairing
  description: ""          # one or two sentences
  visual_traits: []        # recognizable characteristics
  emotional_voice: []
  works_for: []            # industries / situations
  caution: []              # when not to use it
  distinct_from: ""        # nearest existing entry and how this differs
  pairs_with: []           # compatible entries from other layers
  language_notes: ""       # Indonesian glyph, diacritic, numeral support
  source: ""               # reference link or description of origin
  confidence: low | medium | high
  status: candidate | tested | approved | retired
  review_by: ""            # YYYY-MM-DD — deadline for review, promotion, or retirement
  tested_in: ""            # carousel / project id
  test_result: ""
  approved_by_user: false
```

### 15.4 Rules

-   **Respect the layers.** Every new entry must be assigned to exactly
    one layer from section 1. Do not mix a typeface class, a movement,
    and a technique in one entry.
-   **No duplicates.** If `distinct_from` cannot name a meaningful
    difference, merge into the existing entry instead of adding a new
    one.
-   **Principles, not copies.** Learn why a style works. Do not
    reproduce a specific poster, logo, or campaign.
-   **Evidence over novelty.** An entry is only valuable if it improves
    a real decision. Record the context in which it helped.
-   **Local relevance.** Actively cover Indonesian and Southeast Asian
    contexts (regional lettering traditions, sign painting, packaging,
    street signage, batik and craft aesthetics), and always verify
    Indonesian language support for any font category recommended.
-   **Stay balanced.** Expansion must not bias the agent toward only
    the newest additions. New entries are options, not defaults.
-   **User stays in control.** Nothing enters the core library without
    approval.
-   **Lifecycle & retirement (`review_by` / `status: retired`).** Every
    `candidate` or `tested` entry must set `review_by` (`YYYY-MM-DD`,
    typically +30 days). During pruning (every 5 cycles or past
    `review_by`), unused, superseded, or failing entries transition to
    `status: retired` inside `library_candidates.md` so audit history is
    preserved while retired entries are excluded from active selection.
-   **Keep the core readable.** If the core file grows too large, split
    it by layer and keep an index at the top.

### 15.5 Cycle report format

After each learning cycle, give the user a short report:

``` markdown
### Learning cycle N
- Gap found:
- Candidates added (max 3):
- Tested in:
- Result:
- Recommended for approval:
- Proposed prunes/merges:
```
