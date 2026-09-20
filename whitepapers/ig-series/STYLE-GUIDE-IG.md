# IG Carousel Series — Style Guide (portrait-native)

## Why portrait-native, not resized cards

The 64 `insight-visuals/` cards are **1200×~1000 landscape** (aspect 1.13–1.54:1).
Dropped onto IG's 1080×1350 (4:5) canvas they fill only 29–48% of the height — a
landscape card floating in dead space.

These slides are therefore **rebuilt portrait-native at 1080×1350**, reusing the
card's *tokens and copy*, not its geometry. This follows the standing rule:
port content onto the design system, don't hack a foreign aspect ratio.

## Canvas

| Property | Value |
|---|---|
| Slide size | **1080 × 1350** (4:5 portrait — IG's max feed real estate) |
| Full-bleed | Yes — canvas fills the whole slide, no floating card |
| Padding | 88px 96px (generous — thumb-scroll legibility) |
| Safe margin | 96px from all edges (IG crops ~4:5 exactly; keep copy inside) |

## Tokens (inherited verbatim from `insight-visuals/STYLE-GUIDE.md`)

```css
:root {
  --canvas: #f7f6f3;           /* Light paper background */
  --surface: #ffffff;          /* Card surface */
  --surface-muted: #efeee9;    /* Muted fills */
  --ink: #1b1f24;              /* Primary text */
  --ink-2: #4a525c;            /* Secondary text */
  --ink-3: #6b737e;            /* Muted / label text */
  --accent: #0e6e5c;           /* Primary teal */
  --accent-strong: #0a5447;    /* Dark teal emphasis */
  --accent-tint: #e7f1ee;      /* Light teal background */
  --accent-line: #c6dcd4;      /* Teal border */
  --critical: #b42318;
  --critical-tint: #fbeae7;
  --warning: #9a6500;
  --warning-tint: #fbf0d8;
  --line: #e4e2dc;
}
```

## Typography (scaled UP for 1080px width)

The card scale (38px h1) is too small at 1080px. Slide scale:

| Role | Font | Size / weight |
|---|---|---|
| Slide headline (cover) | Playfair Display | **76px** / 800 / 1.05 |
| Slide headline (stat slide) | Playfair Display | **54px** / 800 / 1.1 |
| **Hero stat** | Playfair Display | **132px** / 800 / 0.95 |
| Stat unit | Inter | 22px / 500 / ink-3 |
| Body | Inter | 24px / 400 / 1.55 |
| Overline | Inter | 17px / 600 / uppercase / 0.14em / accent |
| Slide counter | Inter | 16px / 600 / ink-3 |

## Slide archetypes (rotate — never repeat twice in a row)

| # | Archetype | Purpose | Key feature |
|---|---|---|---|
| 1 | **Front cover** (bare) | Establish the source | Full-bleed real book cover, no chrome. Opens every post. |
| 2 | **Cover / Hook** | Earn the swipe | Oversized Playfair headline + swipe cue |
| 3 | **Big Number** | One stat, full impact | 132px hero number + context line |
| 4 | **Comparison** | A vs B vs C | Stacked columns, teal intensity ramp |
| 5 | **Bar Chart** | Scale gap | Horizontal bars, value labels |
| 6 | **Payoff / Insight** | The "so what" | accent-tint panel + optional `.mission` line |
| 7 | **Steps** | A named process | Numbered cards, `.steps` / `.step` |
| 8 | **Ledger** | N unrelated before→after results | Per-row outcome text, **no shared axis** |
| 9 | **Question grid** | The questions the buyer cannot answer | `.qgrid` / `.q` — 2×2, teal dot markers |
| 10 | **Back cover** (artifact) | Close the loop | Small real back cover + context. Closes every post. |

### Archetype pitfall — Ledger vs Bar Chart

Only use **Bar Chart** when every value shares ONE unit and ONE axis. When the rows
are *different* metrics (e.g. Avis share % vs Wang Lao Ji revenue ¥), bars encode a
false proportional comparison. Use **Ledger** instead: state each row's own
before→after and claim no shared scale. (Post 02, slide 07.)

`.cols` variants: default = ranked 3-col (teal ramp). `.cols.text` shrinks the
value type to 40px for phrase values. `.cols.neutral` greys the top rule when the
columns are equal-weight options rather than a ranking.

Extra copy blocks: `.nots` (what the answer is NOT — × chips) and `.mission`
(the offer stated as a belief, e.g. *"You may be small. But your strategy
shouldn't be."*).

## Slide furniture

Every slide carries the full set — **except the bare front cover**, which has no
header rule and no footer chrome by design (the cover artwork is the hook, and
wrapping it in a template drains its authority).

- **Top-left:** overline (Part/Chapter ref)
- **Top-right:** `NN / TT` slide counter
- **Bottom-left:** ObserveCo logo mark + wordmark + series tag
- **Bottom-right:** source attribution (small, ink-3)

**Counter caution:** `NN / TT` is literal per-slide text. Inserting or removing a
slide silently breaks it (post 01 shipped `02 / 06` alongside `04 / 07`…`07 / 07`
with 6 slides on disk). Fix every counter when the slide count changes;
`verify_gates.py:counter_seq()` now enforces sequential `NN` and one consistent `TT`.

## Forbidden

- No dark backgrounds (`#0f172a`, `#1e293b`, `#273548`)
- No blue/purple accents (`#3b82f6`, `#8b5cf6`, `#6366f1`)
- No fonts other than Playfair Display + Inter
- No more than **10 slides** per carousel (IG hard limit)
- No lorem ipsum — every number traces to a verified source
- **No internal document terms** (`whitepaper`, `White Paper`) and **no bare series
  index in the footer wordmark** (`ObserveCo / Book 1` — an unexplained "Book 1" is
  noise to a reader; the tag is `/ Singapore`).

> **Amended 2026-09-19 — the book IS named.** Naming the book by **title** is now
> not just allowed but required: every post opens on the front cover and closes on
> the back cover. The earlier rule ("a reader must never be told there is a book")
> was **wrong** — it made every figure read as an unsourced assertion, which is the
> exact weakness the book exists to fix. The book is the authority behind the
> claims. Only document-internal vocabulary stays banned. Enforced by
> `no document-term leak` in `verify_gates.py`.

Blue (`#3b82f6`) and purple (`#8b5cf6`) are **forbidden**. Encode data hierarchy
with teal intensity instead:

| Rank | Token | Use |
|---|---|---|
| Strongest | `#0a5447` (accent-strong) | Highest value in a comparison |
| Middle | `#0e6e5c` (accent) | Second value |
| Weakest | `#9a6500` (warning) | Third value / the constrained tier |

## File naming

`post{NN}-slide{NN}-{slug}.html` → renders to `post{NN}-slide{NN}-{slug}.png`
