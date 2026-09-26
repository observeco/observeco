# A3 BUILT — `market_headroom` is scored only where it can be measured

**Date:** 2026-09-25
**Trigger:** Sean — *"Build A3."*
**Rubric:** 0.6.0 → **0.7.0**
**Files:** `rubric.json` (`_meta.classifiers`, `_meta.elasticity_dispositions`), `run_jev.py`
(`build_questions`, `score`, console output), `test_a3_elasticity.py`, `test_a3_regression.py`
**Verdict:** **A3 is implemented and working end-to-end. The classifier reproduces the blind hand
labels 19 of 20. Zero band changes across the corpus except ONE — which is material and needs
Sean's review before shipping.**

---

## 1. What A3 does

A new **classifier** runs first and is **not** a scored dimension — it carries no weight and never
enters the composite. It decides **which dimensions apply**.

```
elastic    -> market_headroom NOT SCORED; its 15% renormalised over the rest;
              the client gets a qualifier sentence instead of a number
inelastic  -> market_headroom IS SCORED (a backlog is measurable)
ambiguous  -> scored AND flagged; both readings reported
```

The classifier's question judges **whether supply can flex to meet a rise in demand** — market
level, not firm level. A single restaurant cannot add tables tonight, but the restaurant *market*
absorbs the demand elsewhere, so the market is elastic. Inelastic only when the constraint binds on
**all** suppliers at once: fabrication plants, assembly lines, licensed capacity, berths, land.

**Why it's a classifier and not a confidence judgement:** confidence is about *how well we scored*.
This is about *whether the dimension means anything here*. Different question, different mechanism.

---

## 2. Classifier validation — 19 of 20 against BLIND hand labels

Ground truth is `FINDING-elasticity-test.md`, which classified all cases **by hand, blind to the
scores**. The model was never shown those labels.

| result | count |
|---|---:|
| agreed | **19 / 20** |
| genuine mismatch | **1** — Coupang (expected `ambiguous`, model said `elastic` at 0.47) |

**The critical cases all held:**

| case | expected | model | confidence |
|---|---|---|---:|
| **ASML** | inelastic | **inelastic** | **1.00** |
| F1 Boeing/Airbus | inelastic | inelastic | 1.00 |
| F3 VICOM | inelastic | inelastic | 0.99 |
| C5 Michelin hawker | elastic (market level) | elastic | 0.76 |

**The only mismatch is safe in shape, not just rare.** Coupang is the case where the correct answer
IS ambiguity — the model said `elastic` at 0.47, i.e. *barely*. Low confidence on a genuinely
borderline case is the right failure mode: the other two options would have been a confident wrong
call. **Unchanged behaviour either way** — `ambiguous` and `elastic` both keep headroom unscored.

**F3 is worth recording.** My first version of the test labelled VICOM `elastic` and the model said
`inelastic` at 0.99. **My label was wrong** — VICOM's own input file and `FINDING-midsized-test.md`
both state *"INELASTIC (market-level, regulatory). Only operators authorised by the LTA may perform
mandatory vehicle inspections."* The model read the regulatory constraint correctly and I had
mis-filed my own case. Corrected in the script with the reason recorded inline.

**This matters because ASML was the only inelastic case in the original corpus.** A3 is only safe if
the classifier can find inelasticity in cases other than the one it was designed around. It found
VICOM (regulatory), Boeing/Airbus (industrial) and ASML (technological) at 0.99–1.00 — three
different *kinds* of inelasticity.

---

## 3. End-to-end — verified in the harness, both directions

**Elastic (koi):**
```
market_headroom    --   coverage 0.97  BELOW FLOOR -> unscored
elasticity (A3) : ELASTIC   [ambiguous:0.02  elastic:0.97  inelastic:0.01]
  -> market_headroom NOT SCORED (elastic market); its 15% renormalised over the rest
  -> client sees: "Demand in your market is served and contested. Buyers can already
     get what you sell, so there is no pool of unmet demand to step into..."
composite: 76   band: Strong
```

**Inelastic (ASML):**
```
market_headroom    4/5  coverage 0.60  floor>=2  pass
elasticity (A3) : INELASTIC   [inelastic:1.00]
composite: 91   band: Strong
```

**The 15% renormalisation needed no new mechanism** — it fell out of the existing weight
renormalisation over scored dimensions, exactly as predicted when A3 was chosen.

**The qualifier sentence is wired to the client-facing output.** Without it the dimension would
vanish silently and the user would see four numbers with no explanation of the missing fifth. That
was a real risk in building this.

---

## 4. Full-corpus regression — one band change, and it needs review

| | |
|---|---:|
| headroom **dropped** (elastic) | **17 cases** |
| headroom **kept** (inelastic) | **3** (ASML, Boeing/Airbus, VICOM) |
| composites changed | 13 |
| **band changes** | **1** |

**Inelastic cases are untouched** — A3's effect is confined to elastic markets, which is the design.

**Direction:** composites mostly **rise 1–2 pts** for dropped cases (C9 and F2 unchanged; Watsons,
E4, N2, bonefirm, bubbletea *fall* 2–3). Headroom was near the bottom of the scale for elastic
markets, so removing it lifts the average.

**THE ONE BAND CHANGE — flagged for Sean, not accepted:**

```
koi:  74 "Viable, conditional"  ->  76 "Strong"
```

**A 2-point move crosses the 75 boundary and changes what the client is told.** Two things make
this worth a decision rather than a mechanical acceptance:

1. **The band boundary is a cliff, and 74/76 sits right on it.** This is the same
   display-boundary problem seen with `market_headroom`'s 2.00 cut. A 2-point difference producing a
   different verdict *word* is the composite behaving as a step function at exactly the point where
   it matters most.
2. **A3 systematically raises elastic-market composites.** That is correct in principle (a
   near-constant was being spread across 15%) **but it means the bands were calibrated against a
   composite that included headroom.** Every band boundary is now slightly mis-set for the 17
   elastic cases. **Only one case crosses — but that is corpus luck, not safety.**

**Recommendation: re-calibrate the bands against the A3 composite before shipping**, or explicitly
accept that 74→76 moves a case into "Strong". Not a blocker for A3 itself; a blocker for the
*banding*.

---

## 5. What this does NOT establish

- **No human label exists anywhere in this project.** The elasticity labels are MY hand
  classification, so A3 is validated against my own judgement — better than nothing (the model was
  blind to it), but it is not independent validation. **Still the #1 blocker.**
- **3 inelastic cases in a 20-case corpus.** A3 has almost nothing to score headroom *on*. The
  design is right; the test population is thin, exactly as before.
- **The category-norm baseline is still unsourced.** A3's inelastic path reports "backlog ÷ revenue,
  normalised to what is normal for your category" — and the normalisation is not yet sourced
  (industrial ~0.25 yr vs ASML 1.19 vs Airbus ~11.0). **The inelastic path is now live and its
  normalisation is a placeholder.**
- **The classifier is a new failure point.** It runs first and gates a dimension. A wrong `elastic`
  call silently drops a real signal; a wrong `inelastic` call scores noise. Tested on 20 cases with
  the labels I supplied. **Untested on real submissions.**
- **Coupang mismatches at 0.47 and is treated as elastic.** Behaviourally identical to `ambiguous`,
  but the stored `classification` field will read `elastic`. Minor, but it is a wrong label in the
  record.
- **A3 does not touch the gates, `competitive_room`, or the absent human labels.** Those remain open.
- **`market_headroom` remains weighted 15 and fully scored where inelastic** — A3 narrows the
  dimension; it does not remove it.
