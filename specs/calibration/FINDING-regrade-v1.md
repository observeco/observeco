# FINDING — the v1.0.0 regrade: 120 businesses, and where we still disagree

**Source.** `~/Downloads/regrade-sheet.numbers` (not `grading-sheet.csv` — that file has
0 filled rows; the live regrade is the Numbers document). Extracted to `sean-regrade-raw.csv`.
**All 120 rows filled, all six dimensions, 61 holistic scores, 2 notes.**

---

## GUARD: the grades are real

A filled count can be an artefact, so the distributions were checked first:

```
YOUR_RS    n=120  mean 3.07  range 1-5
YOUR_MA    n=120  mean 3.24  range 1-5
YOUR_DEF   n=120  mean 2.48  range 1-6
YOUR_CR    n=119  mean 2.65  range 1-4
YOUR_MH    n=7    mean 3.14  range 3-4     <- 106 marked n/a
YOUR_DR    n=120  mean 3.67  range 2-5
```

Differentiated, within scale bounds, correctly using 1–6 only for defensibility.
Not defaults, not a formula spilling down.

---

## THE STRONGEST VALIDATION IN THE PROJECT: market_headroom applicability

`market_headroom` is dropped whenever the A3 elasticity classifier finds the market
capacity-elastic. That is a **judgement**, and it was the dimension most vulnerable to
being an invention. He reached it independently:

```
he n/a AND I dropped   : 112   <- independent agreement not to score
I dropped, he scored   :   2
he n/a, I scored       :   1   (VICOM)
both scored            :   5
agreement on applicability: 98%
```

**112 cases where he, unprompted, declined to score the same dimension I declined to
score.** The one exception is VICOM — the inelastic/regulatory case — where he said n/a
and I scored 3. Worth a question: he may have judged the market differently, or not known
VICOM's regulatory position.

---

## Agreement improved substantially on the re-anchored definitions

```
dim    n    his mu  my mu   mean d   exact   >=2 apart
RS    120   3.07    2.78    +0.28     75%      4%
MA    120   3.24    2.80    +0.44     66%     11%
DEF   119   2.45    2.12    +0.34     75%     12%
CR    119   2.65    2.44    +0.21     77%      5%
MH      5   3.20    3.40    -0.20     80%      0%
DR    116   3.62    3.28    +0.34     69%     10%
```

**Exact agreement 66–80%.** Under the OLD definitions (his first grading) exact agreement
was 41–71%. The re-anchoring of `mental_advantage` and the addition of `position_strength`
both improved it: MA exact 41% → 66%, and RS — the brand-new dimension — reaches **75%
exact, 4% ≥2 apart**, the second-best agreement of any dimension.

## position_strength is NOT redundant with mental_advantage

The risk with the new dimension was that it double-counted MA. Tested two ways:

```
his RS vs my_new_RS   r=0.85   mean|d|=0.30   exact 75%
his RS vs my_new_MA   r=0.82   mean|d|=0.42   exact 62%
```

His RS tracks MY RS **better than** my MA — the prediction recorded in
`FINDING-human-labels.md`. His RS and his MA are correlated (r=0.73 within his own grades)
but distinct: identical in 58% of cases, and he assigns RS **below** MA in 30 cases and
above in 17. The dimension adds information.

**And it separates rivals inside a landscape**, which `competitive_room` cannot:

```
his RS within-category sd   furniture 1.26 | gym 1.24 | bubble-tea 1.00 | kopitiam 0.96
my  RS within-category sd   same pattern
competitive_room            constant in 11 of 17 categories
```

`competitive_room` is sd 0.00 in electronics and home-not-permitted; RS never is.

---

## DISAGREEMENT IS ONE-DIRECTIONAL — and that makes it systematic

```
cases where HIS is >=2 above mine : 52   (DEF 15, MA 14, DR 12, CR 6, RS 5)
cases where MINE is >=2 above his :  0
```

**Zero cases in the other direction.** A disagreement with no cases on one side is not
noise. It is a level shift:

```
dim    shift   his sd   my sd
RS      +0.28    1.10    1.00
MA      +0.44    1.13    1.05
DEF     +0.36    1.21    1.07
CR      +0.21    0.60    0.55
DR      +0.38    0.82    0.68
```

**The standard deviations are nearly equal.** He is not using more of the scale than I am —
he is using the same scale shifted up. That distinction matters: a spread difference would
mean my level descriptions were anchored too tightly; **a level shift means specific level
WORDING is anchored differently and should be re-worded, not rescaled.**

## Ordering is largely preserved

```
mean rank correlation across 16 categories: 0.79
categories with rho >= 0.70             : 12 of 16
perfect agreement (rho = 1.00)          : gym, furniture, home-nails, home-facial,
                                          home-creative, home-tuition
ORDER DISAGREES                          : electronics 0.20, bakery 0.35,
                                          home-not-permitted 0.40
```

Order agreement of 0.79 means the instrument is **broadly telling the same story**. The
four weak categories are where to look for the real problems.

---

## ARTEFACT CAUGHT BEFORE IT WAS REPORTED

An analysis showed `|my score − his SCORE| = 0.2`, which would have been implausibly good
convergence on the composite. **It is not convergence.** Checked for copying:

```
his YOUR_SCORE vs my_new_score : 59 of 61 EXACTLY equal (97%)
genuine deviations             : KOI (his 70, mine 77), ObserveCo (his 60, mine 54)
```

**He copied my score into `YOUR_SCORE` for convenience.** The composite agreement figure is
an **artefact and must not be reported as agreement.** The per-dimension analysis is
unaffected — those numbers are his own and are independently distributed.

This also explains the 11 rows where his SCORE contradicted his own dimensions: the copied
score replaced his implied composite.

---

## What he did NOT do

- **Left `YOUR_SCORE` blank in 59 of 120 rows** — so only 2 rows carry a genuine holistic
  judgement.
- **Wrote notes in only 2 rows.** Why he scored what he scored is largely unrecoverable, so
  the questions below are the substitute.
- **Used band RANGES himself in 28 of 120 cases (23%)** — independently the same behaviour
  my band-interval produced in 32 cases. Independent support for the interval approach.
- **Marked MH n/a 106 times** (see above).

---

## Sources
`extract_regrade.py` (numbers-parser extraction), `verify_regrade.py` (guards + agreement),
`reconcile_regrade.py` (MH applicability, per-dimension disagreements),
`reconcile_specifics.py` (case-level detail), `test_rs_independence.py` (RS vs MA),
`analyse_disagreement.py` (level-vs-spread, rank agreement),
`check_score_copying.py` (the artefact check).
