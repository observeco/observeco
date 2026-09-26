# FINDING — Bands re-calibrated to the scale's anchors (0.7.0), and "Fragile" is unreachable

**Date:** 2026-09-25
**Trigger:** Sean — *"re-calibrate."* Plus: *"whether your own self assessment indicates the need for
larger data samples?"*
**Script:** `recalibrate_bands.py`
**Verdict:** **Bands now derive from the scale's own anchors instead of hand-rounded tens. One
unexpected structural finding: the 'Fragile' band is mathematically unreachable — the gates have
already replaced it. Sample-size answer: yes, emphatically — but the binding constraint is ZERO
human labels, not case count.**

---

## 1. The principle — anchors, not data

I did **not** fit the bands to the corpus. That would encode my 20 skewed, partly self-authored
cases — the same error as the 0.6.0 reframe.

**The composite a business gets when EVERY dimension sits at the same anchor is a property of the
scale arithmetic, not of any data:**

| every dimension at… | 5-dim (inelastic) | 4-dim (A3, elastic) |
|---|---:|---:|
| level 1 | 19.17 | 19.02 |
| **level 2** — "very little" | **38.33** | 38.04 |
| **level 3** — "at expectation" | **57.50** | 57.06 |
| **level 4** — "good" | **76.67** | 76.08 |
| level 5 — "strong" | 95.83 | 95.10 |

**The two dimension sets agree within 0.74 pts.** So the anchors are stable under A3 — A3 does not
move the boundaries, which is exactly what we needed to know before using them.

**And the original bands were never arbitrary — they were these anchors rounded to tens:**

| boundary | was | anchor | off by |
|---|---:|---:|---:|
| Contested starts | 40 | **38** | 2 |
| Viable starts | 60 | **58** | 2 |
| Strong starts | 75 | **77** | −2 |

**Re-calibration is snapping them back to the exact anchors.** Applied:

```
Fragile              5 – 37
Contested           38 – 57
Viable, conditional 58 – 76
Strong              77 – 100
```

**This corrects a real mislabel.** The old "Strong ≥ 75" floor sat **below** the anchor for "good on
every dimension" (77). A business could be labelled **Strong while scoring under good on every
dimension**. Now Strong requires genuinely reaching it.

**koi is the case that exposed it** — 76, labelled Strong under the old bands, correctly **"Viable,
conditional"** under the anchors. koi was never a banding *outlier*; it was the boundary being two
points low.

---

## 2. UNEXPECTED — "Fragile" is mathematically UNREACHABLE

**Every gate fires when a display drops below 2.** So any case that receives a composite at all has
**every dimension at 2 or above.** The minimum reachable composite is therefore
**all-dims-at-2 = 38.33, which rounds to 38.**

**The Fragile band is 5–37. Nothing can land in it.** It is an empty band in the report's
vocabulary.

**The reading:** **"Fragile" has already been replaced by "GATE."** Before the gates existed, a
hopeless business received a low composite and the word "Fragile." Now it is refused outright, with
no composite. The band is vestigial — it describes a region of the scale the gates made
unreachable.

**Two options:**
- **Keep it** as a documented artifact (it costs nothing; `band_of()` still covers 5–37).
- **Remove it** and start the scale at "Contested," so the band names match the reachable range.

**Flagging rather than fixing** — it changes the report's vocabulary, which is a product decision
for Sean, not a measurement.

**Note this is a *second* instance of the same structural pattern as the gates themselves:** a
mechanism defined over a region no case can reach. The gates were inert because their thresholds sat
below the model's range; Fragile is empty because the gates' floor sits above its range.

---

## 3. Effect on the corpus — 2 cases cross, both onto the anchor

| case | pre-A3 | A3 | new band |
|---|---:|---:|---|
| C5 Michelin hawker | 75 Viable | **77 Strong** | crosses up |
| E2 Coupang | 75 Viable | **77 Strong** | crosses up |
| koi | 76 | 76 Viable | corrected (was Strong) |

**Both crossings land exactly ON the anchor (77)** — the correct side of "good on every dimension."
A3 lifts elastic composites (intended: a near-constant was being spread across 15%), and the anchor
boundary catches them at the right place.

**Inelastic cases untouched.** A3's effect remains confined to elastic markets.

---

## 4. The sample-size question — Sean asked directly

**Yes. Emphatically. But the binding constraint is not the number of cases — it is that there are
ZERO independent human labels.**

**More cases of the same kind would not help.** 100 more cases scored by Jev with no human
reference produces 100 more unvalidated numbers. **Scaling an unvalidated instrument scales the
error.** Every "validation" in this project has been one of:

1. **My own hand-labels** (the elasticity classification) — the model was blind to them, which
   helps, but the labels are mine. **Circular.**
2. **Pre-registered predictions on n=2–3 cases** (F1/F2/F3) — real, and the strongest evidence we
   have, but three cases.
3. **Post-hoc fitted rules** (0.6.0, the aggregation rule, CAGR) — the ones that later collapsed.

**What is actually needed, in priority order:**

**(a) Human labels first — ~30 cases.** Not 300. Thirty human-labelled submissions would let us
measure rank agreement between Jev and an expert, and — more valuable — find the cases where they
**disagree** and hand-adjudicate them. That is the difference between "20 unvalidated numbers" and
"a measured instrument." **This is the single highest-value thing available and it has been the
#1 blocker for the entire project.**

**(b) A different KIND of case.** The corpus is built by me, deliberately loaded with controls and
squeezed markets (Sheng Siong vs FairPrice, Watsons vs Guardian). Real submissions have a
different distribution. **This already bit us** — I had to caveat that `competitive_room`'s low
scores might be corpus composition rather than a real finding.

**(c) Cases that SHOULD be refused — ~10.** Exactly **one** case in the corpus is designed to fail.
Two gates are now the only refusal mechanism and "two gates are enough" is **untested**. Without
more genuinely unviable businesses we cannot know whether the gates over-fire or under-fire.

**(d) Inelastic cases — ~15–20.** Headroom only scores where supply is inelastic, and we have
**three**. Inelastic markets are rare, which is precisely *why* A3 exists — so this may be
intrinsically hard to fill. **It is also the honest limit of A3: the dimension is well-designed
and barely testable.**

**(e) The noise floor matters more urgently than n, and is cheaper.** The measured per-dimension
noise is **σ ≈ 0.08 raw** from a few repeat-runs. The band boundaries are **1-point steps**. If the
composite noise is anywhere near 1 point, **near-boundary cases are coin flips** — and the report
states a *word*, not a number.

**The cheapest high-value experiment available: 10 repeat-runs of 5 cases (~50 calls).** That
measures σ_composite properly and tells us whether the band boundaries are meaningful **at all**.
**Doing this before collecting 30 human labels is right, because if the boundaries are noise, the
labels are measuring a cliff that isn't there.** This is the same discipline as checking the
instrument before trusting the reading.

---

## 5. Recommended sequence

1. **Measure σ_composite** — 10 repeat-runs × 5 cases. ~50 calls. Cheap, and it gates everything else.
2. **Then collect ~30 human-labelled submissions**, with expert band/verdict calls.
3. **Then** decide whether the band table needs intervals rather than cliffs.

**Do not** grow the corpus by having Jev score more unlabelled cases. That is the one option that
looks like progress and isn't.

---

## 6. What this does NOT establish

- **The anchors are exact; the bands are now principled, not validated.** "All dims at 4 = Strong" is
  an interpretive claim I am making about the scale's meaning. It is coherent and internally
  consistent — it is not evidence that these boundaries match expert judgement.
- **The 2-point crossings (C5, E2) are near-boundary moves.** Under my own noise concern in §4(e),
  both may be within the noise floor. **I have not measured that.**
- **The "Fragile is unreachable" finding assumes the gate floors stay at 2.** If gates are deleted —
  as earlier findings proposed, and as Sean has since pushed back on — the floor moves and Fragile
  becomes reachable again. **The finding is conditional on the gate set.**
- **σ ≈ 0.08 is from prior work and a small number of repeat-runs.** It may itself be an
  underestimate, which would make the boundary-cliff problem worse, not better.
- **A3's classifier still rests on 20 cases with my labels.** Nothing in this re-calibration
  addresses that.
- **Still zero human labels.** Unchanged, and now explicitly the acknowledged top blocker.
