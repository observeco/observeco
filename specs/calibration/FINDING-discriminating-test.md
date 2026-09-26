# FINDING — The discriminating test passed. Elasticity is the axis.

**Date:** 2026-09-25
**Trigger:** Sean — *"A3 and B1"* (A3 = headroom scored only where measurable; B1 = add the two duopoly test cases first).
**Method:** two cases added with **pre-registered, opposite predictions sealed in the input files before the run**; predictions were written to disk, then the run was made.
**Script:** `run_jev.py` (unchanged harness, rubric 0.6.0, jev-1.13.0)
**Verdict:** **Both predictions passed. Separation 1.28. The elasticity hypothesis survives a test that could have failed.**

---

## 1. The design — why this test is different

The 17-case corpus was **vacuous** for this hypothesis: 12 of 17 are market-elastic, so the
classifier could only *explain* the flatness, never be *disconfirmed* by it. A test that cannot
fail proves nothing.

F1/F2 fix that with **the same structure and opposite predictions**:

| | structure | market-level supply | predicted headroom |
|---|---|---|---|
| **F1 Boeing/Airbus** | duopoly | **INELASTIC** (tooling, certification, years) | **HIGH** |
| **F2 Watsons/Guardian** | duopoly | **ELASTIC** (a store opens in months) | **LOW** |

Same duopoly structure. Opposite prediction. **If structure drove the reading, both would be
HIGH. If supply elasticity drives it, they separate.** The two competing explanations make
different predictions, so the test discriminates between them.

Predictions were written into the `_meta.pre_registered_prediction` field of each input file
**before execution**, so they could not be fitted to the result.

---

## 2. Result

| case | market_headroom raw | display | coverage |
|---|---:|---:|---:|
| **F1 Boeing/Airbus** | **3.20** | 4 | 0.67 |
| **F2 Watsons/Guardian** | **1.92** | 3 | 0.93 |

**Separation: 1.28.**

```
pre-registered F1 >= 2.5  :  got 3.20  -> PASS
pre-registered F2 ~1.8-2.0:  got 1.92  -> PASS
```

Against the existing corpus:

```
elastic pack (12 cases)   1.78 - 1.98     F2 = 1.92  -> INSIDE the pack
ASML (inelastic)          3.33            F1 = 3.20  -> 0.13 below ASML
```

**F2 landed exactly where the elastic pack lives** (1.92, within the 0.20 band). **F1 landed next
to ASML** — the only other inelastic case — and far above the pack.

**This is the first result in this project where a prediction was registered in advance and the
model confirmed it.** Contrast with the four earlier hypothesis tests that were fitted after the
fact (0.6.0 headroom reframe, CAGR, backlog-cover, aggregation rule).

---

## 3. What it establishes

**1. Supply elasticity, not player count, is the axis.** F2 has *identical duopoly structure* to F1
and scored at the opposite end. Structure cannot explain the separation; elasticity does. The
original monopoly/duopoly/fragmented axis is now refuted by a controlled comparison, not by
argument.

**2. Concentration and headroom are genuinely different axes.** F2 is *concentrated* — Watsons 18%,
Guardian 14%, Sephora 7%; the two leaders hold ~32% — yet headroom is LOW. A concentrated market
with elastic supply does not accumulate unmet demand, because a rival can simply open another
store. **Concentration governs who captures value; elasticity governs whether demand is met.**

**3. The model reads elasticity from the evidence without being told.** Neither input file contains
the words "elastic" or "inelastic" as a scored variable, and `market_headroom` is not asked about
capacity. The model inferred it from the business descriptions — delivery backlogs and certification
on one side, store openings and price-matching on the other. **This is the key result for
derivation:** the classifier may not need to be built as a separate step if the scored dimension
already responds to it.

**4. The A3 design is validated in principle.** Headroom carries real information where supply is
inelastic (F1 3.20, ASML 3.33 — separated from the pack by 1.2+) and correctly reports "served"
where it is elastic. Scoring it only where measurable is now evidence-backed rather than a hunch.

---

## 4. What it does NOT establish

- **n=2 inelastic cases, now n=2 (F1, ASML).** Two cases confirming a prediction is much stronger
  than two cases fitting one — but it is still two. The hypothesis is *corroborated*, not *proven*.
- **F1 is a very large, very famous company.** Its 3.20 may partly reflect the model recognising
  Boeing/Airbus as an extraordinary case, not reading the elasticity mechanism. A mid-sized
  inelastic market would be a harder test. **This is the soft spot and it is real.**
- **F2's `demand_reach` fell below floor** (coverage 0.17 → unscored) and `defensibility` coverage
  was 0.34. Its composite (57, Contested) rests on four dimensions, not five. The F2 headroom
  reading itself is well-covered (0.93) so the test result stands, but the case is not a clean
  five-dimension control.
- **The category-norm baseline problem is untouched.** F1's absolute backlog cover (~10 yr) is
  normal for aircraft; the raw score does not encode that. Normalisation is still unsourced.
- **Concentration is not yet built as a scored axis.** §3.2 asserts it is a different axis; it has
  not been implemented or tested.
- **A3's weight handling is unbuilt.** Removing headroom from the elastic path changes the
  renormalisation behaviour; the harness already supports variable dimension sets but the new path
  is untested.

---

## 5. Consequence for the design (A3, as decided)

| market supply | headroom | instrument | status |
|---|---|---|---|
| **INELASTIC** | **scored**, normalised to category norm | backlog ÷ revenue | measured: ASML 1.19 yr; Airbus ~11.8 yr; Boeing 737 ~9.9 yr |
| **ELASTIC** | **qualifier** — "served and contested" | concentration + entry÷exit (churn) | validated by F2 = 1.92, inside pack |
| **AMBIGUOUS** | report both, state disagreement | — | Coupang only, n=1 |

The renormalisation machinery already exists (spec has variable dimension sets with runtime weight
renormalisation), so A3 does not require a new mechanism — but the elastic path needs building and
testing before it ships.
