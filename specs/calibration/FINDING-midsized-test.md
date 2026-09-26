# FINDING — Mid-sized test passed, and it FALSIFIED the original hypothesis while confirming the refined one

**Date:** 2026-09-25
**Trigger:** Sean — *"the mid-sized case first."* (Chosen to remove the fame confound from F1.)
**Case:** F3 VICOM Ltd — mid-sized (S$119.5m revenue), obscure outside Singapore, regulated duopoly.
**Method:** prediction pre-registered in the input file before the run.
**Verdict:** **Prediction passed. The ORIGINAL hypothesis is FALSIFIED by this case. The REFINED hypothesis is confirmed. The fame confound is removed.**

---

## 1. Result

| | supply | demand vs capacity | predicted | got |
|---|---|---|---|---:|
| **F3 VICOM** | **INELASTIC** (LTA authorises every centre) | **met** — stagnant car population, flat fees, eroding share, low waits | **LOW ~1.8-2.0** | **1.57** |

```
pre-registered: LOW, falsified if raw >= 2.6
got:            1.57  -> PASS (and overshot to the low side)
```

Full run: `market_headroom 3/5 (raw 1.57, coverage 0.64)`, composite 64, Viable-conditional.

**1.57 is now the LOWEST headroom reading in the 20-case corpus** — below N1 closed business (1.69).
The gap is 0.12, which is at the edge of the 0.08 noise floor, so the honest reading is that VICOM
and the closed business sit at effectively the same floor.

---

## 2. The original hypothesis is FALSIFIED — and this case is why

**Original (as written in `FINDING-duopoly-leg.md`):** *inelastic supply → unmet demand accumulates.*

**VICOM is a counterexample.** Supply is genuinely inelastic — the LTA authorises every inspection
centre, and a competitor cannot open one without authorisation. That is as hard a regulatory
barrier as exists locally. **And demand is fully met.** Revenue grew 11.97% over a *decade* while
operating profit and net profit slightly **declined**; growth is described as limited by a stagnant
car population and a fixed standardised fee; share eroded from 75%+ to 72.3%; published live centre
traffic shows waits under 20 minutes at most centres.

**So inelasticity alone does not produce unmet demand.** The original hypothesis was too strong and
this case kills it.

**Refined, and confirmed:**

> **Elasticity governs OBSERVABILITY. Demand-vs-capacity governs the SCORE.**
> Inelastic supply is what makes a backlog or queue *possible* — it is why unmet demand can
> accumulate and remain visible where it does occur. Whether it actually accumulates depends on
> the demand-to-capacity balance.

That is the correct two-part statement, and F3 is the case that forced it.

---

## 3. The model reads the MECHANISM, not the barrier — and not the fame

This is the result that matters most.

**Same elasticity class, opposite outcomes:**

| case | supply | demand | headroom |
|---|---|---|---:|
| F1 Boeing/Airbus | inelastic | **unmet** (10-yr backlog) | **3.20** |
| F3 VICOM | inelastic | **met** (saturated, eroding) | **1.57** |
| ASML | inelastic | **unmet** (1.19 yr backlog) | **3.33** |

Two inelastic cases at opposite ends. **Elasticity is held constant; the reading tracks the
demand/capacity balance.** The dimension is measuring the right thing.

**And F3 is mid-sized, so fame cannot explain it.** F1's 3.20 could have been the model
recognising Boeing. F3 is a S$119.5m Singapore inspection company — no model has a strong prior
about it. It read the mechanism from the evidence (stagnant car population, flat fees, eroding
share, low centre traffic) and scored it low. **The fame confound is removed.**

**Critically — the model did NOT confuse a barrier to entry with an opportunity.** This was the
explicit risk: a regulated duopoly with statutory authorisation looks "protected". Had the model
scored it high, the dimension would be measuring *protection*, not *opportunity* — a fatal defect.

**It scored defensibility 3.19 → display 4 (predicted 4)** and headroom 1.57 → 3.

**That is exactly correct routing:** the regulatory obstruction went into **defensibility** (where
"Protected" belongs), and no opportunity was inferred from it. The two dimensions are doing
genuinely distinct work. This is the cleanest structural separation seen in the project.

---

## 4. Falsification summary across all three F-cases

| case | prediction | result | verdict |
|---|---|---|---|
| F1 Boeing/Airbus | HIGH ≥2.5 | 3.20 | PASS |
| F2 Watsons/Guardian | LOW ~1.9 | 1.92 | PASS |
| F3 VICOM | LOW ~1.8-2.0 | **1.57** | PASS (overshot low) |

Three pre-registered predictions, three confirmed, on cases chosen because they could fail.
For contrast: the 0.6.0 headroom reframe, the CAGR test, backlog-cover and the aggregation rule
were all assessed **after** the fact.

---

## 5. What this changes for A3

The A3 design survives and is now stronger than when it was chosen:

- **INELASTIC + unmet** → real ratio (backlog ÷ revenue, category-normalised). ASML 1.19 yr;
  Airbus ~11.8 yr. Scored.
- **INELASTIC + met** → qualifier. VICOM: regulated, protected, and *no opportunity from market
  demand*. This is a case the old crowding framing would have scored high (statutory protection!)
  and the unmet-demand framing now correctly scores at the floor.
- **ELASTIC** → qualifier. F2 1.92, inside the pack.
- **AMBIGUOUS** → report both. Coupang only.

**A3 is better justified than when decided, because F3 proves the risk it was designed to avoid is
real and handled.**

---

## 6. What this does NOT establish

- **n=3 inelastic cases** (ASML, F1, F3). Three confirmed predictions is meaningfully stronger than
  two, still small. Corroborated, not proven.
- **VICOM undershot its predicted band** (1.57 vs predicted 1.8-2.0). "LOW" was right; the band was
  wrong. Either the bottom of the scale is compressed, or "stagnant and eroding" reads *worse* than
  "no demand" — VICOM scored below a closed business. **Unexplained, and worth understanding before
  shipping** — a profitable market leader reading below a defunct business is counterintuitive.
- **The scale has no demonstrated bottom resolution.** If the true floor is ~1.5 and 12 elastic
  cases sit 1.78-1.98, the usable range is narrower than a 1-5 display implies.
- **Still unsourced:** the category-norm baseline for the inelastic ratio. A3 depends on it.
- **Concentration is still not built as a scored axis**, though F2 and F3 both support that it is a
  separate axis.
- **The elastic path and weight renormalisation remain unbuilt and untested.**

---

## 7. Recommended next step

The hypothesis is now well-corroborated. Two candidate next moves:

1. **Build the elastic path + concentration axis (A3 implementation).** The evidence supports it.
2. **Investigate the VICOM anomaly first** — why a profitable, dominant, protected duopolist reads
   *below* a closed business. If the floor is compressed, that affects every case in the corpus and
   is a scoring defect, not a curiosity.

**My view: (2) before (1).** A compressed floor is a measurement defect that would propagate into
everything built on top of it, and it is cheap to check. Building A3 on an unexamined scale is the
same order of error as the 0.6.0 reframe — shipping on four confirming cases without looking at the
distribution.
