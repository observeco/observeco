# ObserveCo Consulting Design System — where it lives

This is the system **www.observeco.com** is built on. Use it for all ObserveCo
content (site, figures, decks, video/reel overlays). Do not invent a parallel
palette — a second palette is how the reel ended up in clash with its own figures.

## The files

| File | Role |
|---|---|
| `website/assets/draft.css` | **The live system.** All 15 site pages `<link>` this. If you want to match observeco.com, match this. |
| `design/live-tokens.css` | **The token source that matches production.** The `:root` block extracted verbatim from `draft.css`, verified 39/39 properties identical. Copy the `:root` verbatim into a new artifact, or hand this file to an external design tool. |
| `design/consulting-tokens.css` | **Earlier draft — NOT production.** Documents a status palette and a dark projection theme that were never shipped, and diverges from live on spacing (4px grid vs 8px), type scale, and radii. Read it for rationale; do not copy it as current values. |
| `design/tokens-RETIRED-dark-telemetry.css` | **Retired. Do not use, do not upload.** The pre-pivot navy `#0f172a` / green `#22c55e` palette. Was named `tokens.css`, which is how it got handed to a design tool by mistake on 2026-11-01. |
| `design/consulting-design-system-rationale.md` | Why light-first, plus the old→new token mapping table. |
| `design/observeco-consulting-redesign.html` | Reference implementation (~35KB) of the system in page form. |

## The tokens that matter most

```
--canvas   #f7f6f3   warm bond paper — NOT pure white, NOT navy
--surface  #ffffff   cards
--line     #e4e2dc   hairline
--insight  #0e6e5c   THE accent — insight teal
--coral    #b84a2f   warm complement (negative / price states)
--amber    #c99a3f   secondary warm (trends, markers)
--ink      #1b1f24   primary text, near-black
```

Type: **serif display** for authority (`Iowan Old Style`, Palatino, Georgia),
**Inter** for body, **mono** only for labels/identifiers.

## The rule that gets broken

**Dark navy / cyan is the RETIRED telemetry system.** `#0f172a`/`#22c55e` (and its
offshoots `#0a0f14`/`#38bdf8`) were replaced when the product surface moved from a
dev cockpit to a consulting deliverable. `consulting-design-system-rationale.md`
documents that migration explicitly.

Dark survives only as `[data-theme="dark"]`, for projection rooms.

If a new artifact is dark navy with a cyan accent, it is on the dead system. That is
a defect, not a style choice — it will clash with every figure and every page.

## Why it drifted once already

The `20260920` longevity reel was authored in `#0a0f14`/`#38bdf8` while its own
embedded figures were cream `#f7f6f3` + `#0e6e5c`. The reel's own source comment
claimed "palette matches the article figures: deep navy, cyan accent" — the comment
was true when written and never updated when the figures moved to the consulting
system. **Check the comment against the artifact, not just the artifact against the
comment.**

Fixed in `ig-reel-longevity-v2.mp4` (2026-09-20).

## Known-good reference

`content-writing/20260920/fig-lon-01-shrink.html` is a clean example: paper canvas,
white card, hairline border, insight-teal accent, pastel tint chips, serif headings.
Reuse that structure rather than starting from scratch.

## Measured values production actually uses (verified 2026-11-01)

Read from computed styles on the live site, not inferred from a token file. These
supersede anything in `consulting-tokens.css` that disagrees.

**Type — responsive pairs, not a step scale.** A single px value is the mistake:
the kit's 34/26/20 ladder matched nothing.

| Role | Desktop | Mobile | Rule |
|---|---|---|---|
| H1 / page title | **56px** | **36px** | `clamp(36px, 6.2vw, 56px)` |
| H2 / section head | **36px** | **26px** | `clamp(26px, 4vw, 36px)` |
| H2, dark band | 38px | 26px | `clamp(1.6rem, 3.4vw, 2.4rem)` |
| H3 | 20px | 20px | variants at 16 / 19 / 21 |
| KPI numeral (`.stat-card .num`) | **38px** w700 serif | **38px** | does not shrink |
| Body | **17px** | **16px** | |
| Small | 15 / 14 / 13 / 12 / 11 / 10 | — | mono for labels |

**Spacing.** `--space-1..6` = 8 / 16 / 24 / 40 / 64 / 88. Not the 4px grid in
`consulting-tokens.css`; same token names, different values.

**Radii.** `--radius` 10px and `--radius-lg` 14px only. Pills are hardcoded
`border-radius: 9999px` on `.chip`, `.word-chip`, `.trend-chip`, `.tier-pill` and
`.outcome-card .oc-illus`; `.reel-btn` uses 999px; dots use 50%. There is no
`--radius-pill` token — define one locally rather than treating pills as off-system.

**Motion and shadows have no tokens.** Transitions cluster at 0.2s (14 uses), then
0.25 / 0.3 / 0.35. There are 18 distinct `box-shadow` literals. Take both from
`observeco-consulting-redesign.html`, which is where the intended values live.

**State colours — measured contrast on paper:**

| Pair | Ratio | Verdict |
|---|---|---|
| Teal on 8% teal tint (`.watch-callout`) | 5.09:1 | AA body |
| Teal on 15% teal tint (`.rank-badge`) | 4.62:1 | AA body |
| Coral on 10% coral tint | 4.19:1 | AA large only — use `--coral-hover` `#9c3d25` (5.47:1) for body text |
| Coral on paper | 4.79:1 | AA body |
| `--fg-2` on `--surface-2` (`.tier-pill`) | 6.94:1 | AA body |
| **Amber as text on its 12% tint** | **2.16:1** | **fails everything** |

**Amber is a tint and a marker, never words.** At 2.38:1 on paper and 2.16:1 on its
own tint it cannot carry text. Use an amber tint with ink on top.

**Charts are a two-colour semantic pair, not a categorical cycle.** Green = ours /
after; coral = theirs / before / worse (`.bar-fill.before`, `.cmp-fill.before`,
`.rival-line`, `.split-keep`, `.scale-fill.wrong`); amber = a pin or marker. The only
sequencing rule in the stylesheet is `.dot-row .dot:nth-child(n+6) → coral`. For a
five-series categorical chart — which the live site never has — use the muted segment
palette in `consulting-tokens.css` and label it documented-not-live.

## Handing this system to an external design tool

- Give it **`live-tokens.css`** (2.8 KB). Never `draft.css` (138 KB of page-specific
  rules) and never `consulting-tokens.css` (a draft with wrong spacing and type).
- **Name the retired palette as forbidden.** A tool that only sees the new hexes will
  otherwise helpfully re-derive a dark variant; it needs the explicit do-not list.
- **Ask for desktop/mobile pairs**, not single sizes, and warn that spacing values
  change under a token swap so components tuned to the old grid need re-checking.
- Verify the result against the public site — `observeco.com`, `/method.html`,
  `/books.html`, `/press.html`, `/whitepapers.html` — not against a stylesheet.

Open defects found during that audit: `DESIGN-DEFECT-LOG.md` in this folder.
