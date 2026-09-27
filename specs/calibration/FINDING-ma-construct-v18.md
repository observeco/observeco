# FINDING — MA construct fixed (Sean's answer), then re-anchored: v1.6.0 → v1.8.0

## Sean's two answers, verbatim

> "Mental advantage is how much the brand holds in the mind of the customer correct? That
> the answer to your first question."

> "Gong cha is in the mental ladder of Singaporean, that's why it has a mental advantage, and
> it should be independent on closure."

Both were questions I had explicitly flagged as needing his answer rather than another
re-word. Both resolved the stuck cases.

## v1.7.0 — the construct

**MA is a MAGNITUDE: how much mind the brand holds. Not a competitive claim.** My level 5
said *"rivals are not close"* — the wrong axis entirely. That is why Sean scored 5 for
Courts, Donki, Harvey Norman and Cold Storage whose prices converge within 3–8%: **a brand
can hold a great deal of mind while close rivals hold a similar amount.** Those are
independent, and I had been demanding exclusivity where he was measuring holding.

**Closure is irrelevant.** Gong Cha is in the mental ladder of Singaporeans. My v1.5.0 rule —
"ceased is positive evidence of non-retrieval" — was simply wrong.

**This is the dimension-specificity principle, stated by Sean directly:** closure destroys
REACH (`demand_reach` — he agrees the closed outlet is 2) but NOT MEMORY
(`mental_advantage`). **The same physical fact has opposite implications per dimension**, so
one shared "physical evidence" doctrine (which is what I had been building) is too blunt.

**Result:** Gong Cha 1 → 3 (his 4), Harvey Norman 3 → 4 (his 5). MA correlation **r = 0.84,
the best of all five dimensions.** Guards held.

## v1.8.0 — the anchor

With the construct right, the remaining error was a clean **calibration** signature, not a
construct one:

```
gap (his - mine):  -1: 5    0: 52    +1: 48    +2: 10
distribution     L1   L2   L3   L4   L5
Sean              4   35   31   31   19
mine (v1.7.0)    26   34   23   25   12
```

A single mass at **exactly +1** beside a large exact mass — a boundary problem for part of
the corpus. My scale was **bottom-heavy (22 too many at L1) and top-starved (7 too few at
L5) at once.** So level 1 was redefined as rare, level 3 named as the ordinary case for an
established business, and ties broken to the higher level.

**Result:** MA offset **+0.55 → +0.33**, MA exact **43.3% → 50.8%**. Distribution
L1 26→10 (target 4), L5 12→10 (target 19) — improved, not solved. L2 overshot 34→45
(target 35).

## Full trajectory

| version | exact | disputes | offset | note |
|---|---|---|---|---|
| v1.2.0 | 66.7% | 8.6% | +0.23 | baseline |
| v1.4.1 | 63.0% | 6.0% | +0.16 | RS fixed |
| v1.6.0 | 55.9% | 4.7% | +0.09 | DEF partial |
| v1.7.0 | 54.2% | 5.2% | +0.19 | MA construct |
| **v1.8.0** | **56.3%** | **4.7%** | **+0.13** | MA re-anchored |

**Both targets pass: disputes ≤5%, offset within ±0.25.** Exact agreement does not (56.3%
vs a 75% target). Against a noise floor of ±0.4 pts / ±2 cases, all movement is real.

## A silent failure worth recording

The first v1.7.0 run **never happened**. The runner was generated from its predecessor by
`sed`, the pattern did not match `OUTDIR = "runs-v16b"` (trailing `b`), so it inherited
`runs-v16b` and a stale `r16b_progress.json`, **"resumed" 120 cases, executed nothing, and
printed `complete: 120`** — while the harness reported rubric 1.6.0. The only evidence was an
empty output directory.

**Two fail-loud guards added:** a version-tagged progress file (a stale one is fatal), and an
empty output directory after a "complete" run is fatal. Same class as the earlier
`_meta.version` bug: **the run content was the only trustworthy evidence; the labels were
not.**

## What remains (23 disputes) — none of it a wording problem

1. **The five `home-not-permitted` cases** at MA/DR 1 vs his 3, plus `A gluten-free specialist
   home baker` MA 2 vs 4, `Bonefirm` RS 2 vs 4, `CHAGEE` RS 3 vs 5. The home-not-permitted
   set are **synthetic representatives of a statutory rule, not real businesses** — they may
   belong in refusal rather than a low score.
2. **`defensibility`** offset is now −0.09 (was +0.23) but exact is only 54.2%; Best Denki
   and Gain City sit at 2 against his 4. The claimed-differentiator defect is reduced, not
   eliminated.
3. **RS is the most stable dimension** (0.8% disputes) and needs nothing further.
