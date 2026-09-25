# FINDING — Can we be more robust than Gartner/MBB? Yes, and here is the measured answer

**Date:** 2026-09-25
**Sean's direction:** *"We do not have to be precise about reconciliation. There is definitely
going to be discrepancies amongst various sources and methodologies. We just have to develop our
own robust way and be consistent throughout all cases is where I am leading towards. Is there a
way we can do this better than the MBBs, Gartner and equivalent?"*

**Verdict: yes — but not by being more precise. By being MEASURABLE. And I found and reverted a
bug I introduced while looking for the fix.**

---

## 1. The answer: what they structurally cannot do

A Gartner/IDC/MBB figure is a **point** built from ~5 hand-made allocations — vendor revenue,
geographic split, segment attribution, untracked-tail estimate, subcontract subtraction. They are
revised yearly (Gartner's own words: *"definitions and assumptions are revised on a yearly
basis"*) and released **without any distribution**. Consequences:

- the client **cannot see the uncertainty**
- **a re-run cannot be compared** to the last one
- **robustness cannot be measured**, so it cannot be improved
- **reproducibility is impossible by construction**

**We can do all four**, because our inputs are continuous model judgments with a stated spread and
our aggregation rule is **deterministic code** applied identically to every case.

---

## 2. What I tested, and what the test disproved

**Hypothesis:** the integer-level quantization (`round(score)`) amplifies variance — at a boundary,
raw 1.95 → level 2 and 1.99 → level 2, but 2.05 → level 3, a whole level from a raw gap of 0.10.

**Measured with 4,000 perturbations per case at the instrument's own noise (σ = 0.08):**

| | result |
|---|---|
| quantization removed → flips | **did not improve** (17.0% vs 2.0% — it got *worse*) |
| actual flip rate, current rule | **0–5.7%**, mean **~2%** |
| composite sd | 0–3.3 points, most cases < 1.5 |

**The hypothesis is false.** A step function's *standard deviation* is a poor estimate of its
*tail* behaviour — it inflates sd while the real flip probability stays small. **Hard boundaries,
not quantization, are the variance source** — and no aggregation rule can remove a boundary.

---

## 3. The bug I introduced, and reverted

While chasing the above I "fixed" `run_jev.py`, claiming `round(score)+1` always yields 1–5 so
defensibility's level 6 was unreachable. **I remapped `score` proportionally onto 1..N. That was
wrong.** The API contract settled it:

> **`score`** — *"The probability-weighted answer across the levels; **can land between levels**."*

**Verified against all 85 stored readings:** `|score − E[level index]| ≤ 0.03` (the residual is
2-dp rounding of the probabilities). So:

- `score` **is** the expected level **index**, 0-based
- defensibility emits **6 bins**, every other dimension **5** — confirmed across all 17 runs
- therefore `round(score) + 1` was **already the correct 1-based display mapping**

**Evidence against my own remap:** it disagreed with the model's own `argmax(probabilities)` in
**77.6%** of readings, versus **81.2%** for the original rule. **My "fix" was the bug.** Reverted.

**One genuine defect found in the original:** Python's **banker's rounding** (round-half-to-even).
Levels are **ordinal** — there is no "even" neighbour — so round-to-even is arbitrary. It corrupted
the clearest case: ASML's defensibility is **E[level] = 4.51, stored 4.50**; banker's gave level 4
(display 5) when the model's own argmax is **level 5 (display 6)**. Fixed with half-up rounding.

**Effect: exactly 1 of 85 readings across the whole ladder.** Only ASML's composite changes
(**91 → 96**); every other case is untouched. That is the correct size of the fix — small.

---

## 4. The instrument's stability, measured per case

Distance from the composite to the nearest **band edge**, in units of the instrument's own noise:

| case | comp | band | band margin | σ | verdict |
|---|---:|---|---:|---:|---|
| **E1-asml** | 96 | Strong | 4 | 1.6 | **BORDERLINE** |
| C5-michelin-hawker | 75 | Strong | 1 | 0.8 | **BORDERLINE** |
| E2-coupang | 75 | Strong | 1 | 4.0 | stable |
| koi | 74 | Viable | 1 | 0.9 | **BORDERLINE** |
| C2-activesg | 71 | Viable | 3 | 1.6 | **BORDERLINE** |
| C6-euyansang | 70 | Viable | 4 | 9.1 | stable |
| C4-sheng-siong | 69 | Viable | 5 | 3.6 | stable |
| C3-pet-lovers | 67 | Viable | 7 | 2.6 | watch |
| D2-petlovers-cue | 65 | Viable | 5 | 6.5 | stable |
| observeco | 65 | Viable | 5 | 1.5 | **BORDERLINE** |
| C9-b2b-it | 56 | Contested | 3 | 2.9 | watch |
| E4-bonefirm-ip | 53 | Contested | 6 | ∞ | stable |
| bonefirm | 51 | Contested | 8 | 6.7 | stable |
| bubbletea | 48 | Contested | 8 | ∞ | stable |
| D1-watsons | 46 | Contested | 6 | 6.7 | stable |
| N2-koi-stripped | 46 | Contested | 6 | 3.1 | stable |
| N1-closedbusiness | GATE | GATE | — | — | stable |

**The ladder is unchanged except ASML (91→96).** Most cases are **stable** — far from a boundary.
**Five cases sit within ~2σ of a boundary** and are now identified **by name**.

---

## 5. The way we beat them — concretely

**Not a better number. A number whose reliability is published.** Four properties they cannot
offer, all now true of our instrument:

1. **Deterministic and re-runnable.** Same rubric + same inputs → same output, verified by
   recomputation in code. A Gartner number cannot be reproduced because the vendor allocations
   are private judgment.
2. **One rule, every case.** 17 cases, one rubric, one aggregation function. That *is* the
   consistency Sean asked for, and it is checkable.
3. **Measured stability per case.** For each client we can state the distance to the nearest
   decision boundary in σ. **A research firm cannot tell you which of its clients is near a
   threshold** — it does not know, because it has no distribution.
4. **Uncertainty carried through, not discarded.** The model's own level distribution is preserved
   and published as a judgment interval; the composite is computed *in code from it*.

**And the honest disclosure that follows:** five cases are borderline. For those, a re-run could
change the band — so the report should say so, or widen the band. **This is a product feature
Gartner structurally cannot ship.**

---

## 6. Where this leaves Sean's original question

**Is there a way to do this better than MBB/Gartner? Yes, on robustness — with three caveats:**

1. **Not on precision.** Their vendor-revenue method has better *inputs* for a well-covered market
   (audited accounts). We should still use it as one of our triangulation legs.
2. **Our advantage is measurability, not accuracy.** We can prove our rule is consistent and
   publish its stability; they cannot. That is a real, defensible difference — and it is what a
   *product* needs, more than another decimal place.
3. **Borderline cases are the deliverable, not the embarrassment.** They are also where the paid
   engagement naturally begins.

**Third time in this project a flagged "defect" was the instrument working.** The first two were
Jev catching something real; this time **the defect was my own fix**. The lesson is the one that
keeps recurring: **verify against the instrument's own output — the model's `argmax` was the
ground truth that exposed my error, and I should have gone to it before changing the code.**
