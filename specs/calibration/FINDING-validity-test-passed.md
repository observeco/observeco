# FINDING — VALIDITY TEST PASSED against an EXTERNAL label, and the band cliff quantified

**Date:** 2026-09-25
**Trigger:** Sean — *"keep persistently experimenting, testing and iterating until you have arrived
at something credible and robust."*
**Scripts:** `build_price_test.py`, `analyse_price_test.py`, `test_robustness_repeats.py`,
`audit_boundary_proximity.py`
**Verdict:** **PASSED. 5 of 5 pre-registered predictions correct, both falsification conditions
confirmed, refusal stable 5/5 on repeat, and the decisive case is one the model had never seen and
whose death is externally documented. Plus one methodological error of mine caught and corrected, and
the band cliff now quantified at 26% of the corpus.**

---

## 1. The test — first validity check with an EXTERNAL label

`FINDING-price-premium-tested.md` established that price premium is a usable label *where the
category spreads price*. Bubble tea spreads it **267%**. So this test scores seven businesses in one
category, holding the derived competitive set **constant**, with the label being **published prices
the model has never seen** plus **one externally documented death**.

Predictions were sealed in the input files before any run.

| case | price | price position | ma | df | **posavg** | composite | band |
|---|---:|---|---:|---:|---:|---:|---|
| **koi** | S$4.50 | mid-premium (leader) | 4 | 5 | **4.5** | 76 | Viable, conditional |
| **P1 Mixue** | **S$1.50** | **value floor** | **5** | 3 | **4.0** | 72 | Viable, conditional |
| **P2 Chicha** | S$5.50 | premium | 4 | 3 | **3.5** | 63 | Viable, conditional |
| **P3 HEYTEA** | S$5.50 | premium | 4 | 3 | **3.5** | 66 | Viable, conditional |
| **P4 R&B Tea** | S$3.60 | budget | 3 | 2 | **2.5** | 52 | Contested |
| **bubble tea (CaiCa)** | — | mid, shrinking | 2 | 2 | **2.0** | 48 | Contested |
| **P5 Gong Cha** | S$4.50 | **mid, no distinct position** | 2 | **1** | **1.5** | **GATE** | **GATE** |

*(posavg = mean of the two positioning dimensions, `mental_advantage` and `defensibility`)*

---

## 2. The decisive result — Gong Cha

**Gong Cha shut all 29 Singapore outlets on 2 October 2025.** The model has never seen the price
sheets; the death is externally documented; my input was reconstructed from filings and menu
archives because a dead business cannot self-report.

**It was REFUSED.**

```
composite: None    band: GATE    gates firing: ['defensibility']
defensibility 1/6  (interval 1-1)
```

**This is the first independent confirmation in the project.** Gong Cha is now only the second case
ever to gate — the other is N1, the closed business.

**And it gated for the right reason.** The refusal rests on **`defensibility` = 1** (no moat at all)
and **`mental_advantage` = 2** — the two **positioning** dimensions. `demand_reach` returned
0.01 coverage (no judgment passed) and `competitive_room` was 2. **The refusal is driven by
positioning, not by reach or market.**

**The strongest single result — same price, opposite positioning:**

| | price | positioning avg | band |
|---|---:|---:|---|
| **KOI** | **S$4.50** | **4.5** | Viable, conditional |
| **Gong Cha** | **S$4.50** | **1.5** | **GATE** |

**Identical price point. Opposite outcome.** Price alone cannot explain this — which is exactly the
claim that price premium is a *valid but conditional* label rather than a mechanical one.

---

## 3. Prediction check — 5 of 5

| prediction (sealed before run) | result | verdict |
|---|---|---|
| KOI high | posavg 4.5, highest | ✅ |
| **Mixue high (owns the value floor)** | **posavg 4.0, second-highest** | ✅ |
| Chicha high | 3.5 | ✅ |
| HEYTEA high | 3.5 | ✅ |
| R&B Tea low | 2.5 | ✅ |
| **Gong Cha lowest** | **1.5, GATED** | ✅ |

**Falsification conditions, both sealed in advance:**

- **C1 "Gong Cha is the weakest"** → **CONFIRMED.** Refused; lowest positioning in the category.
- **C2 "Mixue does NOT score as weak as the undifferentiated middle"** → **CONFIRMED.**
  Mixue 4.0 vs R&B Tea 2.5.

**C2 is the one I was least sure of, and it is the most theoretically important.** A rubric that
merely rewarded premium pricing would have scored Mixue low. **It scored Mixue second-highest** —
`mental_advantage` = **5/5**, the maximum. The model read "owns the cheapest position outright, and
held it through a price rise" as a **real position**, not as absence of one.

**So the rubric sees BOTH ends of the category and correctly puts the crowded middle at the bottom.**

---

## 4. The ordering is U-SHAPED, not monotonic — as positioning theory predicts

```
posavg  4.5  koi        S$4.50   leader, 20yr trust, no advertising
posavg  4.0  Mixue      S$1.50   VALUE FLOOR
         ─── the two ends of the category, both defensible
posavg  3.5  Chicha     S$5.50   premium craft
posavg  3.5  HEYTEA     S$5.50   premium signature
posavg  2.5  R&B Tea    S$3.60   budget, no distinct position
posavg  2.0  CaiCa      —        shrinking
posavg  1.5  Gong Cha   S$4.50   MID, no distinct position  → DIED
```

**Price is NOT monotonic with positioning.** The highest positioning is at S$4.50 and S$1.50 — not
at the top price. **The category supports a value end and a premium end; the undifferentiated middle
is where the businesses die.** That is textbook positioning theory, and the rubric reproduces it from
evidence without being told.

---

## 5. Robustness — the refusal reproduces 5 out of 5

Since the headline rests on one run, I re-ran it.

```
Gong Cha x 5:   defensibility = [1, 1, 1, 1, 1]   gates = defensibility every time
                refused 5 of 5
```

**Not noise. A property of the case.**

---

## 6. MY ERROR, caught and corrected — the noise estimate

My first robustness run reported **"pooled composite sd = 5.22 points."** **That was wrong.** It
pooled repeats across *different cases*, so it measured how much KOI differs from Mixue —
**between-case variance, which is signal, not noise.**

**The correct measure is within-case:**

| case | repeats | composite | sd |
|---|---|---|---:|
| koi | [76, 76, 76] | — | **0.00** |
| Mixue | [72, 72] | — | **0.00** |
| Chicha | [66, 63] | — | **2.12** |

**So noise is usually ZERO and occasionally ~3 points from a single dimension flipping**
(Chicha's `demand_reach` moved 4→3; every other dimension across every repeat was stable).

**The corrected number matters in the opposite direction from my error:** 5.22 overstated the
instability badly. The real figure is 0 in most cases, 3 at worst.

---

## 7. The band cliff, now quantified — 26% of the corpus

With noise = up to 3 points and boundaries at 1-point steps:

**6 of 23 scored cases sit within 3 points of a boundary — and their band WORD is therefore not
reproducible:**

| case | composite | band | distance |
|---|---:|---|---:|
| F2-watsons-guardian | 57 | Contested | **0** |
| **koi** | **76** | **Viable, conditional** | **0** |
| C5-michelin-hawker | 77 | Strong | 1 |
| C9-b2b-it-services | 56 | Contested | 1 |
| E2-coupang-flywheel | 77 | Strong | 1 |
| C2-activesg | 73 | Viable, conditional | 3 |

**These are precisely the cases I have been making banding decisions about all session.** koi sits
**1 point below** the 77 boundary — the re-calibration I applied *this session* moved it there. C5
and E2 sit **exactly on** it.

**Honest reading, both halves:**
- **The re-calibration was right.** The boundary now derives from the scale's anchor
  ("good on every dimension" = 77), not from hand-rounded tens.
- **But the band WORD remains a cliff for near-boundary cases.** Moving the boundary to a principled
  place does not fix a 1-point display step against ~3-point worst-case noise.

**This is the same defect class as `market_headroom`'s 2.00 display boundary** — a continuous quantity
rendered as a step. **It has now surfaced in the composite, which means it is systemic, not
dimension-specific.**

---

## 8. What this does NOT establish — stated plainly

- **n=7 in one category, and 5 of those forms were reconstructed by me from public sources.** For a
  live business, self-report would differ from my reconstruction and could score differently.
  **The test is cleanest for Gong Cha, where reconstruction was unavoidable.**
- **This validates a WITHIN-CATEGORY ORDERING, not absolute calibration.** It shows the rubric
  ranks seven bubble tea businesses the way price position says it should. **It does not show that
  a 76 means what we think it means.**
- **One category is not a sample.** Bubble tea was chosen because it spreads price 267%. **Nothing
  here generalises to categories where price converges** — and there the label is undefined, per the
  earlier finding.
- **Gong Cha's death is not proven to be positioning-driven.** It shut mid-tier with no distinct
  position — consistent with the hypothesis — but the exit could have been franchisor-level or
  corporate. **I have not established causation.** The rubric agreeing with the outcome is
  corroboration, not proof the rubric was right for the right reason.
- **Still no human expert label.** The label here is *price*, which is external and published, but
  it is a proxy for positioning, not an expert's positioning judgement. **This is the strongest
  validation in the project and it is still not a human label.**
- **6 dimensions/repeats is a thin noise estimate.** "0.00 in most cases, 3 at worst" comes from
  12 repeat runs. The worst case is a single observation.
- **The 26% boundary figure depends on the assumed noise of 3.** If true noise is higher, more cases
  are unreliable; if lower, fewer.
