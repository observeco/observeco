# FINDING — the display floor dropped judgment, not noise (rubric 0.9.0)

**Date:** 2026-09-26
**Trigger:** the fast-food inversion in the 55-case set — Burger King (48) outscoring
McDonald's (45). Chasing the cause found a comparability defect.

**Rubric:** 0.9.0 (display_floor 0.2 -> **0.0**)

---

## 1. The symptom that started this

Pre-registered labels said McDonald's held the strongest fast-food position (the default,
most outlets, most-downloaded F&B app). The rubric scored it **below** Burger King, a
chain whose only claim is coupon discounting.

```
McDonald's    45   ma=3  def=2   unscored: demand_reach, market_headroom
KFC           48   ma=4  def=1   unscored: market_headroom
Burger King   48   ma=4  def=1   unscored: market_headroom
Shake Shack   47   ma=3  def=2   unscored: market_headroom
```

**A difference in the `unscored` column.** McDonald's had `demand_reach` dropped, the
others did not. Two cases in the same category were being averaged over **different
dimension sets**, so the 45 vs 48 gap was partly a denominator artifact rather than a
positioning judgement.

## 2. Why the drop happens (and why it is usually right)

`display_floor` marks a dimension "unscored" when its evidence coverage is too low, and
its weight renormalises over the rest. The rubric states the rationale:

> *"a coverage of 0.00 is a dead-even distribution = no judgment at all; printing a score
> for it fabricates a finding."*

**That reasoning is sound.** Printing a number when the model had no basis for one
invents a finding. McDonald's `demand_reach` coverage was **0.12** — a weak signal, and
dropping it rather than printing a confident number is the right instinct.

## 3. But the floor is set at 0.20, and the rationale is about 0.00

**The floor and its own stated rationale disagree by a factor of infinity.**

Measured across the 55-case set — every dimension the 0.20 floor drops that a lower
floor would keep:

```
SM03-cold      demand_reach       0.06
HB03-unity     demand_reach       0.08
FF01-mcdonalds demand_reach       0.12
HB02-guardian  defensibility      0.13
SM04-giant     demand_reach       0.13
BT02-koi       defensibility      0.14
...
GY05-virgin    demand_reach       0.19
                        n=14  |  min 0.06  |  median 0.14  |  max 0.19
                        coverage EXACTLY 0.00:  0 of 14
```

**Zero of the fourteen are the case the rationale describes.** Every one carries a weak
judgment — 0.06–0.19 — not *no* judgment. `BT02-koi` losing `defensibility` at 0.14 is a
sharp example: that is the market leader with 20 years of accumulated trust, and the
dimension most central to its case was being discarded.

## 4. What the comparability loss actually cost

Recomputing each reduced-set case on all five dimensions:

```
mean |shift|  = 2.4 pts
max    shift  = 8 pts   (SM04-giant 32 -> 40; SM02-sheng 72 -> 64)
band noise    = 3.0 pts
shifts larger than the band noise: 11 of 55
```

**And three band words depended on which dimensions were counted:**

```
BT03-chicha   as-run 57 (Contested)           -> all-5 58 (Viable, conditional)
EW04-spectacle as-run 32 (Fragile)            -> all-5 40 (Contested)
SM04-giant    as-run 32 (Fragile)             -> all-5 40 (Contested)
```

## 5. The floor sweep — which floor is right?

Testing 0.00 / 0.05 / 0.10 / 0.20 on the 55-case set:

```
floor   full-set cases   D/W/M/S means        monotonic?   band moves
0.00    55 of 55         27.0 42.3 51.1 53.3  YES          -
0.05    46 of 55         27.0 41.6 51.0 53.4  YES          0
0.10    44 of 55         27.0 41.5 50.9 53.4  YES          0
0.20    33 of 55         27.0 40.9 50.7 53.8  YES          1
```

**Label monotonicity holds at EVERY floor** — the rubric orders dead < weak < mid <
strong in all four cases. So the floor is not protecting the instrument's accuracy.

The only thing the stricter floor buys is the mid→strong gap: **3.0 at floor 0.20 vs 2.2
at floor 0.00, a gain of 0.8 pt.** The cost is dropping 22 cases out of a common
dimension set.

**0.8 pt of separation is not worth making a third of the corpus non-comparable.**

## 6. The fix

**`display_floor`: 0.2 -> 0.0** — match the floor to its own rationale. A dimension is
excluded when there is **no judgment** (coverage 0.00), not when the judgment is **unsure**.
Weak coverage should be **flagged, not dropped**.

At floor 0.0 all 55 cases share one dimension set (`market_headroom` excepted, dropped
structurally by A3's elasticity rule — a tested, intended decision, not this defect).

## 7. Still open — the honest remainder

**The mid→strong gap is 2.2–3.0 pts, at or below the band noise of 3.0.** That means:

> **The rubric separates *weak* from everything else clearly (+8.9 pts), but it barely
> separates *mid* from *strong*.**

So the instrument is reliable at the **bottom** of the ladder and blunt at the **top**.
A "Viable, conditional" and a "Strong" verdict can differ by less than run-to-run noise.
This is the most important limit in the set and it is not fixed by the floor change —
0.8 pt was all the floor was ever contributing.

**This is now the binding question for the rubric**, ahead of sample size: *can it
distinguish a good position from a great one?* The evidence says: weakly at best.
