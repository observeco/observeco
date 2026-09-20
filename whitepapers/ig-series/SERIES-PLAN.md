# IG Carousel Series — Plan (amended 2026-09-19)

**Amendment:** every post is now **bookend-framed** — it opens with the real front
cover and closes with the real back cover. A reader never has to guess where the
content comes from.

Superseded: the earlier plan in `00-captions-post01.md` treated the book as an
internal artifact to be hidden. That was wrong. The book is the authority behind
every claim, and naming it is the credibility, not a leak.

---

## The problem this fixes

The first plan produced standalone data carousels. A reader scrolled three slides of
S$494K and S$32K with **no idea these numbers came from a real, sourced,
confidence-labelled study**. The figures looked like unsourced assertions — the exact
weakness the book exists to fix.

A post that says "someone measured this" is weaker than one that says "this is from a
book that measured this."

## The shape of every post

| Slot | Archetype | Job |
|---|---|---|
| **1** | **Front cover** (full-bleed) | Establish: this comes from a real book. Caption states the book's one-line claim. |
| 2 | Hook | The finding that earns the swipe |
| 3–n−1 | Content | Comparison / bars / steps / ledger / grid — the argument |
| **n** | **Back cover** (artifact + context) | Close the loop: "one of 64 findings", sourced and confidence-labelled |

**6–9 slides per post.** IG's hard limit is 10. The back cover is the closing slide
because it answers the question the front cover raised. Post 01 runs 6 slides
(one finding, tight); post 02 runs 9 (it follows the homepage's full positioning arc).
The gate asserts ≤10 per post and a sequential `NN / TT` counter sequence.

### Why the cover is full-bleed on slide 1

The cover artwork **is** the hook — it does more work than any headline I could write.
Wrapping it in the usual header rule, overline and footer would shrink it to an image
inside a template and drain its authority. Slide 1 therefore runs in `bare` mode: no
chrome, cover centred, one caption line beneath.

### Why the back cover is a small artifact, not full-bleed

The back cover is dense blurb text. It reads as rubbish at thumbnail size but works as
**proof of a physical object** — a small framed image beside two lines of context.
Full-bleed on the last slide would waste the slide; small-beside-text makes the artefact
do the convincing.

## Assets — extracted from the shipped artwork, never redrawn

| Asset | Source | Size |
|---|---|---|
| `assets/cover-front.png` | `print/output/final-design/exported/COVER-book1-Signboard-FINAL-print.png` (front panel crop) | 544×840 |
| `assets/cover-back.png` | same file (back panel crop) | 220×340 |

The wrap is 3429×2550 at 3×; panels split `back 550 │ spine 43 │ front 550` design px.
`make_covers.py` performs the crop — the covers are **never** redrawn or re-typeset.

Verified: `book1_front_cover.png` is byte-identical to the front panel of the shipped
wrap (pixel diff bbox `None`), confirming the crop source is the canonical artwork.

## The 12 posts

Each takes the bookend shape. Source cards from `../insight-visuals/BOOK1-ORDER.md`.

| # | Post | Source cards | The argument | Status |
|---|---|---|---|---|
| 1 | **Three Engines** | 03, 04, 05 | The structural gap + the brand lever | ✅ built (6 slides) |
| 2 | **What Is ObserveCo?** | live site | What the business actually does | ✅ built (9 slides) |
| 3 | **The Crowded Market** | 06, 07, 08, 09 | Density, churn, price wars | pending |
| 4 | **Who Owns Singapore's Money** | 10, 11, 12, 19 | The state as competitor | pending |
| 5 | **Five Streams** | 20, 21, 22, 23 | Choosing your revenue stream | pending |
| 6 | **What the Money Buys** | 24, 25, 26, 27 | Spending that is actually moving | pending |
| 7 | **The Waves** | 32, 36, 37, 38 | Demographics reshaping demand | pending |
| 8 | **Walls and Doors** | 43, 44, 45, 58 | Where a giant owns 80% vs nobody owns 20% | pending |
| 9 | **How Singapore Buys** | 17, 18 | The referral economy | pending |
| 10 | **The Grey Market** | 34, 35, 29 | Ageing: three markets, not one | pending |
| 11 | **Capital Traps** | 30, 31, 36 | CPF, COE, the house | pending |
| 12 | **Why Now** | 62, 63, 64 | Digital economy + the AI adoption gap | pending |
| 13 | **Small Is Not the Problem** | 08, 42, 61 | Positioning beats size | pending |

Post 2 is an explainer and sits **before** the Book-1 run — it answers the prior
question a cold audience has. The rest argue from the book.

## Amended rules

1. **The book is named.** Title is allowed and encouraged on the cover slides, and in
   the overline. Banned: internal document terms (`whitepaper`), and a bare unexplained
   series index in the footer wordmark.
2. **Every post opens with the front cover and closes with the back cover.** No
   exceptions — this is the amendment.
3. Covers come from the shipped artwork via `make_covers.py`. Never redraw them.
4. Everything else holds: one design system, 1080×1350, real sourced data, no
   forbidden tokens, ≤10 slides.

## Build

```bash
cd whitepapers/ig-series
env -u PYTHONPATH -u VIRTUAL_ENV /usr/bin/python3 make_covers.py   # extract panels
python3 build_ig_slides.py                                         # generate HTML
bash verify_ig.sh post                                             # full gate chain
```

Gates now include: exact 1080×1350 · real render on `#f7f6f3` · no forbidden tokens ·
**book context allowed, document terms blocked** · furniture present on chromed slides
(the bare cover is exempt by design) · **referenced cover assets resolve on disk** ·
HTML well-formed · ≤10 slides per post · column-ranking semantics · **counter sequence**
(`NN / TT` sequential and agreeing on the total) · bar proportionality · text-collision ·
font pre-flight.

### Post 02 is the exception to the bookend rule's *content* — not its shape

Post 2 still opens and closes on the covers, but its body is **the live homepage's
positioning sequence**, not a book finding: problem → unfairness → who we are →
the promise → the mission. It carries **no pricing slide** — the S$500 / cost-of-
being-wrong argument stays on the site, where the reader is already evaluating.
Putting it in a cold IG scroll reads as a sales pitch and cuts the arc short.
