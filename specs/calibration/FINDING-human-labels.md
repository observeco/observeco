# FINDING — the first human labels (56 cases), and the two definitions that reconcile

**Source:** Sean's grades in `~/Downloads/grading-sheet.numbers`, entered 26–27 Sep before the
D1–D3 realignment. **55 cases** joined to a run and carry at least one grade; 132 rows
present. Extracted with `numbers-parser` (the file is a zipped IWA bundle; no Numbers app
installed) to `sean-grades-raw.csv`.

This is the first independent human judgement the project has ever had. Everything before
it was my own scoring validated against external facts (prices, closures, outlet counts).

---

## Headline: his grades are HIGHER on every dimension, and that is not error

| Dim | n | his mean | my mean | mean diff (his−mine) | exact | ≥2 apart |
|---|---|---|---|---|---|---|
| MA | 55 | 3.67 | 3.02 | **+0.67** | 41% | 32% |
| DEF | 53 | 2.91 | 2.57 | +0.34 | 64% | 16% |
| CR | 55 | 2.59 | 2.31 | +0.29 | 56% | 3% |
| MH | 14 | 3.43 | 3.14 | +0.29 | 71% | 0% |
| DR | 48 | 3.60 | 3.46 | +0.15 | 47% | 10% |

**A uniform positive offset on all five dimensions is the signature of two different scales,
not of random error.** If he were simply noisier, the differences would cancel. They don't.

Composite: **his − mine = +8.0 mean, 12.1 mean absolute.** The largest gaps are all
large well-known businesses with a strong market position:

```
McDonald's Singapore    mine 47   his 87   +40
True Fitness            mine 27   his 59   +32
Watsons (S1)            mine 47   his 78   +31
KFC Singapore           mine 47   his 78   +31
PCF Sparkletots         mine 52   his 82   +30
CHAGEE                  mine 52   his 81   +29
Ya Kun Kaya Toast       mine 56   his 81   +25
IKEA                    mine 56   his 78   +22
```

The only large NEGATIVE gap is **ObserveCo itself** (mine 65, his 43, −22) — he grades his
own business harder than I do. Worth noting for its own sake.

## The MA dispute, settled empirically

Hypothesis: he grades MA as **absolute awareness**; I grade it size-**relative**.
Prediction: he scores MA higher specifically for large/famous businesses. **Confirmed.**

```
Watsons            his 5  mine 2  +3
True Fitness       his 4  mine 1  +3     <- the business that DIED
Giant              his 5  mine 2  +3
Gong Cha           his 4  mine 2  +2
CHAGEE             his 5  mine 3  +2
McDonald's         his 5  mine 3  +2
```

**He scores MA higher in 26 cases, lower in 6, same in 23.** The disagreements are
concentrated exactly where the two constructs diverge — big, famous, but not over-performing
their size. He reads "is this business known?"; the rubric reads "does it over-index for its
size?" Both are coherent. They are different questions.

**The most informative single case: True Fitness.** He grades it MA=4 — correctly, it *was* a
major known brand. The rubric graded it 1, and it died. Neither of us is wrong: he is
describing how well known it was; the rubric is describing that being known did not convert
into being retrieved for a buying occasion. **That distinction is the product's actual
insight** — and it is currently buried inside one dimension's wording rather than being
stated.

## Duplicates: he graded them the same, as he said

```
Sheng Siong      (C4 / SM02)                IDENTICAL
Chicha San Chen  (P2 / BT03)                IDENTICAL
HEYTEA           (P3 / BT04)                IDENTICAL
Mixue            (P1 / BT01)                IDENTICAL
Bonefirm         (bonefirm / E4)            IDENTICAL
Pet Lovers       (C3 / D2)                  IDENTICAL
Watsons          (D1 / F2 / HB01)           D1 = F2 identical; HB01 uniformly −1
```

**6 of 7 duplicate pairs graded identically.** His judgement is *repeatable* across
re-presentation. The rubric's is not — the same businesses scored differently from different
forms: Mixue 65 vs 72, Sheng Siong 65 vs 69, Chicha 57 vs 63, Watsons 46 / 51 / 57.

**So the comparison is: his repeatability 6/7 (86%); mine roughly 0/10 exact.** That is the
sharpest reliability contrast the project has produced, and it is a direct argument for his
dedup — duplicates measure *my* input sensitivity, not the business.

*(Retained as a datapoint: the form-variation sensitivity is worth its own test, since it has
to be flagged in `FINDING-relative-strength-axis.md` when the corpus is rebuilt.)*

---

## THE RECONCILIATION — his reading gets a dimension, mine keeps its meaning

Sean's decisions (D1–D3) plus the new dimension resolve the conflict cleanly:

- **`mental_advantage` — AMENDED to his construct.** *"Among the buyers you can actually
  serve, how familiar/retrieved are you?"* This keeps the size-relativity (a home baker's
  addressable market is its estate) but removes the undocumented "expected of a business its
  size" benchmark that I flagged as a defect. It is now anchored on a *definable* denominator.

- **`position_strength` — NEW.** *"Quality of the current position relative to competitors."*
  The yardstick is the **named occupants of the derived competitive set**. This is the axis
  the objective always required and the instrument never had.

**The two are complementary, not redundant:**

| | answers | reads |
|---|---|---|
| `mental_advantage` | do you over-index **for your size**? | the *opportunity* — the position you could take |
| `position_strength` | how strong is your **actual standing** vs the set? | the *fact* — where you really are |

**Testable prediction:** his MA grades, being an absolute reading of standing, should
correlate better with the new `position_strength` than with the amended size-relative
`mental_advantage`. If that holds on the regrade, it confirms the two scales are genuinely
distinct and that the new dimension has absorbed his construct rather than duplicating it.

`demand_reach` (D2) and `competitive_room` / `market_headroom` (D3) are **unchanged** —
his explicit decisions.

---

## Limits of this evidence

- **55 of 132 cases graded**, and concentrated on the CORE tier; the EXTRA tier is largely
  ungraded. Band-level claims are not supportable at this n.
- **Graded against the PRE-realignment sheet.** The comparison above is valid for the old
  definitions only; the regrade is what tests the new ones.
- **No free-text notes were stored** (0 of 56 rows), so *why* he scored each case is unknown.
  The numeric agreement is real; the reasoning behind it is not recoverable from this file.
- **The composite formula is validated** against my recorded composites (mean |error| 0.74,
  max 3.0) before being applied to his values, so the composite comparison is like-for-like.
