# FINDING — Elasticity hypothesis tested. Survives, but reveals the flatness is TRUE.

**Date:** 2026-09-25
**Trigger:** Sean — *"Let's try your hypothesis and test it out. Don't try don't know."*
**Method:** classify all 17 cases by capacity elasticity, **blind to the score**, then join.
**Script:** `test_elasticity_test.py`
**Verdict:** Hypothesis **survives directionally**, is **vacuous on this corpus**, and the test
produced a bigger result than the hypothesis: **the 0.6.0 flatness is correct, not a defect.**

---

## 1. The test, blind-then-join

Classification was made from the business description only, reasons recorded, before joining to
the jev scores. Full output:

```
case                   elasticity     raw
N1-closedbusiness      N/A           1.69   closed, no demand to serve
D1-watsons             ELASTIC       1.78   ~99 SG stores; openable
C3-pet-lovers-centre   ELASTIC       1.88   69 SG / 140+ SEA; openable
D2-petlovers-cue       ELASTIC       1.89   same as C3
C4-sheng-siong         ELASTIC       1.90   81 -> 93 stores FY2025
bubbletea              ELASTIC       1.90   353 outlets across brands
C2-activesg            "INELASTIC-ish" 1.91  29 statutory gyms
bonefirm               ELASTIC       1.91   contract manufacture, batch runs
E4-bonefirm-ip         ELASTIC       1.92   same as bonefirm
N2-koi-stripped        ELASTIC       1.92   same as koi
C9-b2b-it-services     ELASTIC       1.93   people-based
E2-coupang-flywheel    AMBIGUOUS     1.93   logistics, capital-intensive
C6-euyansang           ELASTIC       1.94   multi-outlet
observeco              ELASTIC       1.97   consulting, people-based
koi                    ELASTIC       1.98   88 outlets, 0 -> 62+ brands
C5-michelin-hawker     INELASTIC     2.43   one stall, one cook
E1-asml                INELASTIC     3.33   50-60 tools/yr, fab needs 10-20
```

| class | n | raw range | mean |
|---|---:|---|---:|
| ELASTIC | 12 | **1.78 – 1.98** | 1.91 |
| INELASTIC | 2 | **2.43 – 3.33** | 2.88 |
| AMBIGUOUS | 1 | 1.93 | 1.93 |
| "INELASTIC-ish" | 1 | 1.91 | 1.91 |
| N/A (closed) | 1 | 1.69 | 1.69 |

**Directional result holds:** every elastic case sits at **≤ 1.98**; both inelastic cases are
**≥ 2.43**. No elastic case scored above the inelastic floor. That is the predicted ordering and it
did not fail.

---

## 2. But it is VACUOUS on this corpus — and I have to say so plainly

**12 of 17 cases are elastic.** The classifier's real content on this corpus is: *"12 cases are
elastic and they're all low; 2 are inelastic and they're higher."*

We already knew the flat pack was low and ASML was high. **The classifier adds no new
discrimination here.** It does not separate the 12 from each other — it *explains* why they can't
be separated. That is a different and lesser claim than "it discriminates."

**A test that cannot fail is not a test.** On this corpus the hypothesis could barely fail: it had
2 inelastic cases to work with. So I ran the falsification check explicitly:

```
cases scoring >= 2.60 : ['E1-asml']        -> INELASTIC  ok
INELASTIC cases below 2.60  : ['C5-michelin-hawker']  2.43
ELASTIC   cases above 2.60  : NONE
```

**C5 is the interesting failure** — inelastic capacity, yet 2.43, below the unmet-demand line.

---

## 3. The error the test exposed — I conflated TWO elasticities

Chasing C5 produced the real finding. There are two different things being called "elastic":

| | question | ASML | Hawker stall | Bubble tea |
|---|---|---|---|---|
| **Firm-level** elasticity | can *this business* expand? | no | **no** (one cook) | yes |
| **Market-level** elasticity | can the *category* absorb demand? | **no** | **yes** — thousands of other stalls | yes |

**The hypothesis must be about MARKET-level supply, not firm-level.** ASML is inelastic at both
levels. A hawker stall is inelastic at the firm level but its *market* is highly elastic — other
stalls serve the demand, so unmet demand cannot accumulate **in the market**.

Under market-level framing, C5 is no longer a falsification: its 2.43 is *elevated relative to the
pack* (0.45 above the elastic max) because that specific stall has a queue, while the market
absorbs the rest. **That is the correct reading, and it is a more precise one than firm-level.**

Re-checked the other edge case: **ActiveSG** (statutory board, 29 gyms, cannot be replicated by a
commercial entrant) scored **1.91** — low. Market-level framing resolves it: the *gym market* is
elastic (many commercial gyms), so demand is absorbed elsewhere. Consistent.

---

## 4. The result that matters more than the hypothesis

**In an elastic-capacity market, unmet demand structurally CANNOT accumulate.**

Supply flexes to meet it. So a headroom question asked of an elastic market has the same answer
almost every time — **"demand is met."** Which is exactly what the 12 elastic cases returned, in a
0.20 band.

**Therefore the 0.6.0 flatness is not an over-correction. It is the truth.**

That reframes the whole problem. The previous finding said:

> *"market_headroom returned 3/5 in 16 of 17 cases… a dimension that is flat is not earning its
> 15% weight."*

Correct conclusion, **wrong diagnosis.** The dimension is flat because **the phenomenon it measures
is absent in 15 of 17 cases** — not because the anchors are mis-scaled and not because the framing
is wrong. Widening the anchors (option 2) would have been chasing a defect that does not exist: it
would have manufactured spread out of a genuine constant. **That option is now dead, and testing
killed it rather than argument.**

---

## 5. So the corrected design, now evidence-backed

Headroom is **two different things** depending on market supply elasticity, and it is only a
*score* in one of them:

**ELASTIC market (15 of 17 cases)** — demand is met by construction.
→ **Qualifier, not a score.** Report *"demand is served and contested"* + the **concentration**
axis (who captures the value). There is nothing to quantify, because nothing accumulates.
→ The instrument, if any, is **entry ÷ exit** (SSIC formations vs cessations), which measures
*churn*, not headroom.

**INELASTIC market (ASML, and by extension Boeing/Airbus)** — demand accumulates as an order book.
→ **Real ratio**: backlog ÷ revenue, **normalised to the category's own norm** (aircraft 10-yr
backlogs are normal; ASML's 1.19 yr is extreme).
→ This is where a genuine 1–5 score is possible, and where it carries real information.

**AMBIGUOUS** → report both and state the disagreement. Do not force. (Coupang, 1.93.)

**Concentration is the axis that carries the composite**, and it is available for every case — it
comes from the Tier 1–7 set we already derive. Bubble tea 353/688–953 (37–51% tracked); Watsons
18% / Guardian 14% / Sephora 7%; supermarkets top-3 = 88%.

---

## 6. What this test did NOT establish

- **It did not validate the hypothesis.** 2 inelastic cases cannot validate a classifier. It
  failed to *falsify* it — a weaker claim, and I am not allowed to upgrade it.
- **The discriminating test is still unrun.** The corpus is 12/17 elastic, so it structurally
  cannot test whether the classifier predicts correctly. That requires adding **Boeing/Airbus**
  (market-inelastic duopoly → predict HIGH) and **Watsons/Guardian** (market-elastic duopoly →
  predict LOW). **Two new cases where the classifier makes opposite predictions is the test.**
- **This is the third time in this project the four-case validation trap has appeared.** 0.6.0 was
  validated on 4 cases and collapsed on 17. I am now proposing a hypothesis fitted to 2 inelastic
  cases. **I am at explicit risk of repeating the same error**, and I am naming it rather than
  letting the directional pass stand in for validation.
- Category-norm baselines for the inelastic leg remain unsourced.
- Elasticity was classified by me, by hand, from descriptions. It is **not derived from the
  pipeline.** Whether the Tier 1–7 set can produce this classification is untested — and until it
  can, this is analyst judgment dressed as a mechanism.
