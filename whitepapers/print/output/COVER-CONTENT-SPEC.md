# ObserveCo Two-Book Cover Content & Print Spec

Front cover, back cover, spine (middle) copy for both ObserveCo books, plus the print
geometry Spectrum needs to incorporate the design. Content is grounded in the actual
manuscripts — every line is verified against `book1-map-manuscript.md` and
`book2-from-small-to-big-manuscript.md`.

**Design owner:** Spectrum (ObserveCo product designer). This doc is the content brief;
Spectrum incorporates the copy into the print cover layouts.

---

## Print geometry (both books — factor the middle/spine)

| | Book 1 — Small Island, Crowded Market | Book 2 — How a Small Business Gets Chosen |
|---|---|---|
| Trim size | Digest 5.5 × 8.5 in (140 × 216 mm) | Digest 5.5 × 8.5 in (140 × 216 mm) |
| Page count (shipped FINAL) | 268 pp | 252 pp |
| Spine width @ 80gsm | **≈ 10.9 mm** | **≈ 10.2 mm** |
| Paper stock calc | spine = pages/2 × 0.0032 in/leaf | spine = pages/2 × 0.0032 in/leaf |
| Bleed | 3 mm all round | 3 mm all round |
| Cover design system | Light-first, cream `#f5f2ec`, accent green `#1b6b57` | Light-first, cream `#f5f2ec`, accent rust `#b5651d` |
| Series labels | "BOOK ONE — THE GROUND" / "THE MAP AND THE METHOD" | "BOOK TWO — THE MOVE" / "THE MAP AND THE METHOD" |

> **Confirm with printer:** the 80gsm / 0.0032-in leaf thickness is the pipeline default.
> If the print run uses a different stock (e.g. 100gsm or a coated cover), the spine width
> in millimetres changes and the back-panel + spine text block must be re-derived. Treat
> the 10.9 / 10.2 mm values as **starting points to confirm with the printer.**

---

# BOOK 1 — Small Island, Crowded Market

## Front cover

- **Series kicker (top):** THE MAP AND THE METHOD · BOOK ONE
- **Title:** Small Island, Crowded Market
- **Subtitle:** What every Singapore business owner should know about the ground they compete on
- **Author:** SEAN FOO
- **Lower strap:** Every figure confidence-labelled
- **Design note to Spectrum:** cover the "ground" literally — the Singapore map / terrain
  motif. Accent green. One headline claim only ("the ground you compete on"); no feature dump.

## Back cover (blurb, three paragraphs)

> When I set out to understand the Singapore business landscape, I expected to confirm what
> everyone already knows. Instead I found a market that is genuinely unlike any other — and
> the findings kept surprising me. A small island where 371,000 businesses chase the
> attention of 5.9 million people. Where the money comes from three engines that most
> owners never see. Where four demographic waves are quietly moving who buys, and what
> they will pay.
>
> This book is the big-picture view I could not find anywhere else. Read it, and you will
> see the ground you compete on the way the people who built it see it — not as a crowded
> market, but as a structure you can finally understand.
>
> Particularly for the aspiring and the many future successful Singaporean entrepreneurs,
> this book will tell you which industries a small business can actually win in.

## Spine (middle)

- **Title (rotated, reading top-to-bottom):** Small Island, Crowded Market
- **Author (rotated):** SEAN FOO
- **Series mark:** THE MAP AND THE METHOD · BOOK ONE (or just the "·1" numeral if narrow)
- **Layout note:** 10.9 mm spine fits title + author only; the series kicker may be omitted
  on the spine if it crowds the 10.9 mm width.

---

# BOOK 2 — How a Small Business Gets Chosen

## Front cover

- **Series kicker (top):** THE MAP AND THE METHOD · BOOK TWO
- **Title:** How a Small Business Gets Chosen
- **Subtitle:** Lessons from Established Singapore Brands
- **Author:** SEAN FOO
- **Lower strap:** Including where positioning fails
- **Design note to Spectrum:** the "choice" motif (the customer's hand / the decision).
  Accent rust (`#b5651d`). One hero claim ("how you get chosen"); the "where positioning
  fails" honesty line is the hook that separates this from every other positioning book.

## Back cover (blurb, three paragraphs)

> The stories of Singapore's brands are missing from the shelves. Walk into any bookstore
> and you will find Apple, Amazon, Starbucks and Nike — but you will search in vain for the
> brands that built this island. This book is a tribute to the ones that came before us: the
> brands that shone a path and lit a beacon for the aspiring.
>
> In the minds of many Singaporeans, some brands are remembered for owning certain words. Tiger Balm owns "relief" — the green jar
> that has sat in Singapore homes for generations, the one you reach for when the ache will
> not go away. Old Chang Kee owns "curry puff" — the golden pastry that has fed generations
> of hungry commuters, the one you queue for at the MRT on the way home. Sheng Siong owns
> "the deal" — the supermarket that built a fortune on the promise of a bargain, the one
> that tells you it will not be beaten on price. Each owns one word in the customer's mind,
> and that is why they get chosen.
>
> Written in the hope that it inspires more Singapore brands, current and future, to reach
> for legacy status — and to add to the richness of the Singapore brand heritage.

## Spine (middle)

- **Title (rotated):** How a Small Business Gets Chosen
- **Author (rotated):** SEAN FOO
- **Series mark:** THE MAP AND THE METHOD · BOOK TWO
- **Layout note:** 10.2 mm spine. Title is longer — may need a shorter spine rendering
  ("Gets Chosen" or "How a Small Business Gets Chosen" at a smaller size). Confirm against
  the 10.2 mm width.

---

## How these relate to each other (both books' back covers)

The two books are a sequence, and the back covers should signal it:

- **Book 1 (THE GROUND)** = the map. "Read this to know the terrain."
- **Book 2 (THE MOVE)** = the method. "Read this to know how you get chosen."
- Both carry the shared series banner "THE MAP AND THE METHOD" so a reader holding either
  recognises the pair. The Book 1 back blurb says nothing about positioning method — it
  sells the map. The Book 2 back blurb opens on the method and the honest failure line.

---

## Files for Spectrum to incorporate into

- Shipped FINAL PDFs (the ones that carry the index/covers/gate):
  `whitepapers/print/output/book1-FINAL.pdf` and `whitepapers/print/output/book2-FINAL.pdf`
- Reference generator (spine geometry + existing cover layout):
  `build-pipeline-final.zip` → `covers.py` (the `spine = pages/2 * PAPER` formula and the
  full-width cover layout with front / spine / back panels).
- Master plan (direction, must not be violated):
  `whitepapers/BOOK-MASTER-PLAN.md`

## Design rules that must hold

1. **Light-first ObserveCo 'consulting' system** — paper `#f7f6f3`-family, no heavy
   dark-first treatment unless Spectrum overrides with an explicit sign-off.
2. **One hero claim per front cover** — the ground / the move. No feature dumps.
3. **Every figure confidence-labelled** (Book 1 strap) and **the failure line** (Book 2
   strap) are honest-hook positioning, not decoration. Keep them legible.
4. **Accent:** Book 1 = green (`#1b6b57`); Book 2 = rust (`#b5651d`). Do not swap.
5. **Spine width is page-count-derived** — confirm the stock with the printer before
   locking the back-panel layout, because the back-panel text block position depends on it.

## Design brief for Spectrum — 3 DISTINCTLY DIFFERENT compositions per book

**READ FIRST: `_pipeline/BOOK-COVER-CRAFT-BRIEF.md`** — the research brief on what makes
a professional book cover. The client rejected the previous set as "too low quality, looks
like a kid's drawing." The previous covers were FLAT PIL drawings (solid accent rectangles,
plain text, no depth, no hierarchy). You MUST adopt the craft principles in that brief:
real premium typefaces, tonal depth in the background (not flat fills), typography as the
hero, accent used as a detail (not a giant slab), deliberate balanced whitespace, everything
on a grid. Do NOT draw flat shapes.

Spectrum must propose **three structurally different full-wrap cover designs for EACH book**
(six designs total). The three per book MUST differ in **composition/layout structure**, not
just colour, type size, or a swapped motif. If the three front panels have the same
skeleton, that is ONE design and it FAILS.

The three directions below are structurally different skeletons. Follow them literally —
do not collapse them back into the same template.

### Book 1 — Small Island, Crowded Market (accent green #1b6b57)

- **Option A — "THE MAP" (motif-led, full-bleed):** The front is dominated by a Singapore
  map / terrain motif rendered in the green accent on cream. The title sits ON or WITHIN
  the map, not in a separate band. The map IS the cover. No top band, no bottom void —
  the motif fills the panel. **The map must look like a real map** (use real Singapore
  geography — the island outline, coastline, terrain), not a blob. If you cannot render a
  recognisable map, this option fails — prefer a clean stylised coastline over a blob.
  **ADOPT THE OBSERVECO INTRO MAP DESIGN** (see the "Adopt the ObserveCo intro map" section
  below): the map is drawn as fragmented zones with white gaps between them, on a subtle
  grid, with a radial-gradient background. This is the exact quality bar.
- **Option B — "THE CROWD" (data/typography-led):** A dense, structured composition that
  reads as a crowded market — e.g. a grid of small marks/dots/businesses filling the panel,
  with the title set large over the grid. The density IS the design. Title + subtitle
  integrated into the grid, not floating in a void. **The marks must be crisp and
  deliberate** (a clean dot grid, not random scatter), and the title must sit clearly over
  them.
- **Option C — "THE STRUCTURE" (minimal editorial):** A clean, centered serif title with
  deliberate generous whitespace, a single thin accent rule, very restrained. Classic
  premium business book. The whitespace is INTENTIONAL and balanced — title vertically
  centered, not crammed at top with a void below. **This is the type-led premium option —
  the typography must be excellent** (strong serif, real hierarchy).

### Book 2 — How a Small Business Gets Chosen (accent rust #b5651d)

- **Option A — "THE CHOICE" (motif-led):** A hand / decision motif — the customer's hand
  reaching, or one word highlighted among many. The motif is the hero. Rust accent. Title
  integrated with the motif, not in a separate band. **The motif must be recognisable and
  well-drawn** — if you cannot draw a convincing hand, use a clean abstract decision motif
  (a highlighted word, a pointer) rather than a crude hand.
- **Option B — "THE WORDS" (typography-led):** The three brand words — "relief", "curry
  puff", "the deal" — ARE the cover. A typographic composition where these words (and the
  brands that own them) are set large and prominent, with the title woven through. The
  words carry the design. **This is a typography showcase — the words must be set with
  real craft** (strong type, hierarchy, the brands as small labels).
- **Option C — "THE METHOD" (minimal editorial):** Clean centered title, the failure-line
  strap ("Including where positioning fails") as a deliberate element, restrained rust
  accent, balanced whitespace. Premium editorial. **Type-led, excellent typography.**

### Hard requirements for EVERY option

- Use the settled back-cover copy verbatim (no rewording).
- Honour the light-first system (cream #f5f2ec-family), one hero claim per front, correct
  accent per book.
- **CRAFT BAR (from BOOK-COVER-CRAFT-BRIEF.md):** real premium typefaces (Georgia serif /
  Helvetica Neue sans — load the actual font files), tonal depth in the background (subtle
  gradient/vignette, NOT flat fills), typography as the hero, accent as a detail (not a
  giant slab), deliberate balanced whitespace, everything on a grid. 2-3 fonts max.
- Render as a full-wrap proof (back + spine + front, correct trim + bleed + spine width)
  at 300 dpi PNG, plus a 1200×630 social card.
- **No dead void:** the front panel must be balanced — no large empty gap between the title
  block and the bottom. If a design uses whitespace, it must be deliberate and centered,
  not a top-crammed title with a blank middle.
- **Verify the three DIFFER:** after rendering, dump an ASCII color-map of each front panel
  and confirm the three have different skeletons (different band positions, different
  content distribution). If two look the same in the ASCII map, redesign one.

### Visual self-QA (MANDATORY — this is what failed before)

You have NO vision tool. You MUST inspect each rendered PNG programmatically before
delivery: dump a coarse ASCII color-map of the front panel (classify pixels as
cream/white/accent/ink, print a grid) and actually READ the layout. Check: content spans
the full width, no dead void, text regions present, accent in the right place, and the
three options per book are structurally distinct. Do this for every design. Do not report
"no void" unless the ASCII map shows it.

**Additionally, self-check the CRAFT:** confirm you used real font files (not PIL's default
bitmap font), that the background has tonal depth (not a flat fill), and that the accent is
a detail not a slab. If any option is a flat shape drawing, redesign it before delivery.

## Adopt the ObserveCo intro map (Book 1 Option A)

The client wants Book 1 Option A to adopt the **opening 3.2s overlay map** on
`www.observeco.com` — the Singapore map with white spaces. This is the exact quality bar.

**The design (from the live site, `website/index.html`):**
- The map is drawn as **fragmented zones** — many small irregular polygons that together
  form the Singapore island, with **white/cream gaps between the zones** (the "white
  spaces"). It is NOT one solid blob.
- The zones sit on a **subtle grid** (thin lines, ~44px spacing) that fades out via a
  radial mask.
- The background is a **radial-gradient + linear-gradient** (a soft glow at top, dark
  field below) — tonal depth, not flat.
- Zones have a **soft drop-shadow** and a subtle **breathe/flash animation** (the live
  site animates them; the static cover just needs the fragmented-zone look).
- A **sheen** sweeps across (a diagonal light band) — optional for the static cover.

**The exact SVG** (61 zone paths, viewBox `4 0 707 459`) is saved at
`_pipeline/sg-map-svg.html`. Spectrum should render these zone paths to reproduce the
fragmented Singapore map.

**Colour adaptation for the books:**
- **Book 1:** the map zones are **teal/green** (ObserveCo accent `#1b6b57` family — the
  site uses `rgba(63,182,155,…)` teal; for the book use the green `#1b6b57` accent). The
  white spaces between zones stay cream/white.
- **Book 2:** the map zones are the **book 2 orange/amber** colour (rust `#b5651d` family).

**Layout for the cover:** the map fills roughly **half the front panel** (the client said
"half the page in front cover"). The title sits over or beside the map. The other half
carries the title/subtitle/strap. Keep the fragmented-zone map as the hero visual.

Present all six as a set for Sean to choose from. Do NOT pick a single direction
unilaterally.
