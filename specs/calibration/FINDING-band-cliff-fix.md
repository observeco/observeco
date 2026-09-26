# FINDING — the band cliff is fixed, and my first fix for it was WRONG

**Date:** 2026-09-26
**Trigger:** Sean — *"keep persistently experimenting, testing and iterating until you
have arrived at something credible and robust."* The band cliff was the one defect I had
named as blocking but not fixed.

**Rubric:** 0.7.0 -> **0.8.0**

---

## 1. The defect

Measured in `FINDING-validity-test-passed.md`: **6 of 23 scored cases sat within 3 points
of a band boundary**, so their verdict WORD could flip on a re-run while the composite
barely moved. koi at 76 — the case the band re-calibration itself moved to the boundary —
was the clearest instance.

The cause is a display step, not scoring noise: dimensions are rounded to integers, the
composite is rounded to an integer, and then an integer is snapped to one of four band
words. A 1-point step against ~1-point real noise puts a case near a boundary in an
unstable word.

## 2. My first fix, and why it failed

**Attempt 1 — propagate Jev's own probabilities (convolution).** Jev returns a
probability distribution per dimension, so the composite is a sum of scaled discrete
random variables. Convolving those gives a full posterior, which should be a *better*
error bar than anything empirical.

I built `band_distribution.py` and validated it against the 12 observed repeat runs it
had to agree with. It did not.

```
case      convolution sd   OBSERVED sd
koi            8.17           0.00
P1-mixue       7.92           0.00
P2-chicha      6.44           2.12
```

**A 4x over-estimate.** The model's posterior is not a calibrated statement about its own
run-to-run behaviour. Reporting it as an error bar would have made the instrument look
roughly four times less stable than it is — the opposite failure from the cliff, and worse
for a client-facing report, because it invites the reader to distrust a score that is
actually reproducible.

**Discarded.** Kept the script and the negative result, because "the model's stated
uncertainty is not its measured uncertainty" is a fact that will be re-derived otherwise.

## 3. Measure noise, do not model it

`test_noise_study.py` — 5 cases x 4 repeats, spanning the composite range and both sides
of the koi boundary, with sleeps between calls to avoid the rate-limiting that broke an
earlier batch run.

```
case                 n  composites          sd    dims that moved
09-koi               4  [74,74,74,74]     0.00    none
C5-michelin-hawker   4  [77,77,77,77]     0.00    none
P1-mixue             4  [72,72,72,72]     0.00    none
C9-b2b-it-services   4  [54,57,55]        1.53    market_headroom [3,4]
P4-rbtea             4  [52,52,53]        0.58    none
```

Pooled with the earlier 12 runs (`repeats/`, `repeat_runs.json`): **32 repeat observations
across 8 cases — mean within-case sd 1.06, max 3.00, 3 of 5 cases zero variance, and only
3 of 25 dimension-observations ever moved at all.**

**So the model is highly reproducible, and the cliff is entirely a display artefact.**
The fix is not to add noise — it is to stop pretending a 1-point integer is a stable
boundary.

## 4. The fix: a band becomes an interval

`band_interval()` in `run_jev.py`, noise read from `rubric._meta.band_noise` (3.0, the
measured max) rather than hardcoded. A case reports every band reachable within the noise,
and whether the word is safe:

```
koi   composite 76  ->  "Viable, conditional OR Strong"   AMBIGUOUS (0 pt from boundary)
ASML  composite 91  ->  "Strong"                          stable (15 pts from boundary)
C9    composite 56  ->  "Contested OR Viable, conditional" AMBIGUOUS
```

**6 of 23 scored cases (26%) now report a range instead of a false single word.** The
cliff is not removed — it is *reported*, which is the honest representation. A reader is
told the instrument's resolution, not a precision it does not have.

**One self-caught bug:** the first version derived `reliable` from the distance to the
nearest boundary instead of from the reachable set, so it could flag a case `AMBIGUOUS`
while listing exactly one band. Fixed to `len(reachable) == 1`, then verified consistent
for every composite 38-100 across noise 1-5.

## 5. What this does NOT fix

The interval is honest about *reproducibility*, not about *validity*. A stable word is not
a correct word — ASML reporting "Strong" stably says nothing about whether "Strong" is
right. Only the external label tests that, and it remains a proxy.

`band_noise: 3.0` is the max over 8 cases. It is a **thin sample for a threshold**, and a
more conservative value is defensible. It is recorded in the rubric with its provenance so
it can be revised when more repeats exist.
