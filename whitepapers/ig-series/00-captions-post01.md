# Post 01 — Three Engines

**Slides:** 6 · `post01-slide01..06-three-engines.png` · 1080×1350
**Shape:** bookend — opens with the front cover, closes with the back cover
**Source:** book *Small Island, Crowded Market* (Book 1) · card `03-three-engines.html`

---

## Caption

> **Small Island, Crowded Market.** That is the book this came from.
>
> A worker in wholesale trade creates **S$494,000** of value a year.
> A public servant: **S$116,000**.
> A person running an F&B shop: **S$32,000**.
>
> That's a 15× gap. And it is not because one of them works 15× harder.
>
> The global worker is more *leveraged*. Three things stand behind them — the world's market, capital, and a brand people trust.
>
> The domestic worker has none of those.
>
> But here's the part most SME owners miss: **brand is the one asset a small business can build too.**
>
> You cannot conjure a global market. You cannot raise institutional capital. But you can build a name that people trust — and that is the only lever that closes any of this gap.
>
> This is one of 64 findings in the book. Every figure is confidence-labelled and sourced — because a claim you can't check is just an opinion.
>
> Which engine is your business standing in? 👇
>
> Source: SingStat, value added per worker by industry, 2025.
>
> #SingaporeSME #SingaporeBusiness #SMEsg #BrandStrategy #SingaporeEconomy #SmallBusinessSG #MarketingSingapore #BusinessGrowth

---

## Slide-by-slide

| # | Archetype | Content |
|---|---|---|
| 1 | **Front cover** (full-bleed) | Shipped cover artwork + "this series is drawn from the book…" |
| 2 | Big number | **S$494K** per worker — 15× the domestic layer |
| 3 | Comparison | Three columns: Global / Govt / Domestic, teal intensity ramp |
| 4 | Bar chart | Seven industries, exact proportional widths |
| 5 | Payoff | "The gap is not about effort" + CTA question |
| 6 | **Back cover** (artifact) | Shipped back cover + "one of 64 findings, confidence-labelled" |

## Data provenance

Every figure traces to card `03-three-engines.html`:

| Slide | Figure | Source |
|---|---|---|
| 2, 3 | S$494K / S$116K / S$32K per worker | SingStat, value added per worker by industry, 2025 |
| 4 | 7-industry ladder (S$494K → S$32K) | Same |

Bar widths verified as exact proportional representations (max error 0.00pp).
Cover crops verified against the shipped wrap — no redrawing.

---

# Series plan

**See `SERIES-PLAN.md`** — the amended plan. Every post is bookend-framed: it opens
with the real front cover and closes with the real back cover, so the reader always
knows the content comes from a real, sourced, confidence-labelled study.

The 64 cards ordered in `BOOK1-ORDER.md` remain the raw material. A carousel is
**one argument of 5–7 slides**, not one card.

## Build commands

```bash
cd whitepapers/ig-series
env -u PYTHONPATH -u VIRTUAL_ENV /usr/bin/python3 make_covers.py  # extract cover panels
python3 build_ig_slides.py       # regenerate slide HTML
bash verify_ig.sh post01         # full gate chain
```

> **Cover amendment (2026-09-19):** slides now open (front) and close (back) with the
> book covers. The earlier "never name the book" rule is reversed — see `SERIES-PLAN.md`
> for why. The leak gate was narrowed to block only internal document terms and the
> unexplained footer series index; the book title is now permitted and required.
