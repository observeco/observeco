# FINDING — the composite is compressed, and the dimension metric was hiding it

## The finding

**I have been tuning against dimension-level exact agreement. The product shows a composite
and a band. Measured at the product level, the instrument has a systematic defect that the
dimension metric cannot see.**

```
gap by level of Sean's own composite (positive = I am too GENEROUS)
  Fragile-ish (<35)   n=35   mean +13.0   (min -2,  max +30)
  Contested  (35-50)  n=31   mean  +8.3
  Viable     (50-65)  n=27   mean  +5.8
  Strong     (65-80)  n=15   mean  +1.8
  Very strong (80+)   n= 8   mean  -4.5   (max -17)
```

**Strictly monotone. My composite scale is COMPRESSED: it does not spread as far as Sean's.**
I am too generous at the bottom and too harsh at the top.

**And every individual dimension looks nearly unbiased:**
```
  RS +0.08   MA +0.33   DEF -0.09   CR 0.00   MH -0.20   DR +0.21
```

**So the defect is not in any dimension — it is in the COMPOUNDING.** Each dimension is
mildly compressed, and the weighted sum of five mildly-compressed dimensions amplifies the
compression into a 17-point swing across the range. **A near-zero mean gap (+0.13) hid a
+-13 error at the tails.** This is the most dangerous kind of bias: it looks calibrated.

## The product-level measurement, which I had never taken

```
cases with both composites computable: 116
SAME BAND:                  56  (48.3%)
ADJACENT band:              56  (48.3%)
TWO OR MORE bands apart:     4  ( 3.4%)
```

**96.6% are within one band.** For a client-facing report, a business placed one band off is
a defensible answer; two bands off is a wrong answer. **4 cases in 116 are two bands off.**

## Why his composite had to be recomputed

`check_score_copying.py` showed **59 of 61 filled rows copied my composite**. So Sean's
`YOUR_SCORE` cannot be used. His composite here is computed **from his own dimension scores**
using the rubric weights — which removes the copying entirely and asks the real question:
"if the six dimension answers were his, what band would our own scorer produce?"

## A secondary cause, measured and quantified

`run_jev.py` renormalises weights over the SCORED dimensions only. `market_headroom` is
dropped in 115 of 120 cases, so its 10% is redistributed to the others.

**Measured effect on Sean's own scores: mean +4.6 points, max +14.6 (ASML).**
So renormalisation explains **+4.6 of the +13.0** bottom-end gap — a real contributor, but
**not the main cause.** I checked this specifically so I would not report a mechanism I had
not quantified.

## What this means for closing

The remaining work is **no longer a wording problem in any dimension**. Two structural
questions have to be answered first, and both are product decisions, not technical ones:

1. **Fix the compression, or accept the bands?** If the band is what the client sees and
   96.6% are within one band, the instrument may already be fit to ship — the compression
   matters only if scores are presented as precise numbers.
2. **Which end is the product's target?** The lead magnet is aimed at SMEs needing help, which
   is where my error is LARGEST (+13.0 for weak businesses). If instead it targets businesses
   already seeking positioning work, the error is −4.5 and the picture is much better.

## Trajectory (dimension level, for continuity)

| version | exact | disputes | offset |
|---|---|---|---|
| v1.2.0 | 66.7% | 8.6% | +0.23 |
| v1.4.1 | 63.0% | 6.0% | +0.16 |
| v1.6.0 | 55.9% | 4.7% | +0.09 |
| v1.7.0 | 54.2% | 5.2% | +0.19 |
| v1.8.0 | 56.3% | 4.7% | +0.13 |
