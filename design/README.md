# ObserveCo Consulting Design System — where it lives

This is the system **www.observeco.com** is built on. Use it for all ObserveCo
content (site, figures, decks, video/reel overlays). Do not invent a parallel
palette — a second palette is how the reel ended up in clash with its own figures.

## The files

| File | Role |
|---|---|
| `website/assets/draft.css` | **The live system.** All 15 site pages `<link>` this. If you want to match observeco.com, match this. |
| `design/consulting-tokens.css` | **Token source.** The `:root` block draft.css is derived from. Copy the `:root` verbatim into a new artifact. |
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
