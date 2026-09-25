# Control Case Plan — OBS-SPEC-095 calibration

**Date:** 2026-09-23
**Status:** design. Purpose: make the rubric's validity a measured property rather than an
impression.

---

## 1. The problem this solves

**The rubric has been tested on 4 cases. Every one was either a known-troubled business or my
own construction.** The KOI control proved the rubric *can* produce a high band, but one control
cannot distinguish "the rubric works" from "the rubric happened to work on KOI."

Two specific defects are already visible and neither is fixed:
- `position_availability` inverts for incumbents (KOI, market leader, scored 2 of 5)
- `no gates have ever fired` on a Jev run (0/4) — the safety layer is untested in practice

**A systematic control set is the only way to tell a working instrument from a lucky one.**

---

## 2. Design principles

**P1 — Vary one thing at a time.** Each control is chosen to isolate a *specific* variable.
A set of five similar strong businesses would prove nothing; five controls that differ in
different ways can locate a defect.

**P2 — Include cases where the answer is UNAMBIGUOUS.** The core failure of the first four
cases was that no case had an obvious right answer. Controls must be picked so that reasonable
people agree on the band.

**P3 — Use large-sample, externally-validated ground truth where it exists.** Some categories
have published market data, financial filings, or award/ranking data. That is a source of truth
independent of my judgment — which is the thing the project most lacks (§ problem 5 in the
prior review).

**P4 — Include negative controls.** A case that MUST score poorly. Without one, a rubric that
never says "bad" cannot be distinguished from a rubric that cannot say "bad."

**P5 — Predict before running.** Every control records the expected band *and the expected
discriminating dimension* BEFORE the run. A post-hoc explanation is not evidence.

---

## 3. The control set

Ten controls in three groups plus a negative control. Ordered by what each isolates.

### Group A — Validity against external ground truth (does it track reality?)

| # | Control | Variable isolated | Externally-validated ground truth |
|---|---|---|---|
| C1 | **KOI Thé** ✅ done | Strong incumbent, same category as a failing case | ~20% share, 13% growth, S$45M at 23% margin, 20 yrs |
| C2 | **ActiveSG** (government gym) | Strong incumbent with NO commercial motive — a different kind of leader | 29 gyms, S$2.50/entry; statutory board, published |
| C3 | **Pet Lovers Centre** | Strong incumbent, different category, retail+services | Market leader, "Singapore's Trusted Leader in Pet Services", multi-decade |

**Why these three:** each is a *documented* leader in a *different* category. If the rubric
scores all three high and the troubled cases low, it tracks reality across categories. If it
only works in bubble tea, the KOI result was noise.

### Group B — Category structure (does it handle structure, or only strength?)

| # | Control | Variable isolated | Why it is unambiguous |
|---|---|---|---|
| C4 | **Sheng Siong** (supermarket) | Strong in a category with a MASSIVE incumbent (FairPrice = ~statutory) | #2 player, listed company, published financials |
| C5 | **A hawker stall with a Michelin Bib** | Strong micro-business, near-zero "moat" in the classic sense | Bib Gourmand = external validation, no brand assets |
| C6 | **A successful TCM clinic chain** | Strong in a category where the competitor set is *unstructured* | Multi-outlet = market evidence |

**Why these:** C4 tests whether the rubric handles a strong player facing a much stronger one
(should be mid-band, not high). **C5 is the sharpest test in the set** — a Michelin-listed
hawker is unambiguously successful yet has almost none of what the rubric calls defensibility.
If it scores low, the rubric equates "successful" with "defensible", which would be a real error.
C6 tests an unstructured category where the derivation may fail.

### Group C — The derivation's own coverage (does the front-end work everywhere?)

| # | Control | Variable isolated |
|---|---|---|
| C7 | **A clinic** (MOH-regulated) | Registry exists — tests the registry path |
| C8 | **A tutoring centre** | Registry exists (MOE/ECDA-adjacent), fragmented |
| C9 | **A B2B service firm** (no registry, no storefront) | **No registry, no consumer mind — tests whether the derivation can work at all** |

**Why these:** every derivation so far has been consumer-facing with findable competitors.
C9 is the hard case: a B2B service with no registry and no consumer category. **If the
derivation cannot construct a set there, we need to know that now**, because it determines
whether the free report needs a "we can't analyse your category" path.

### Negative controls — must score poorly

| # | Control | Why it must fail |
|---|---|---|
| N1 | **A struck-off / closed business** | Objectively dead. If the rubric scores it mid-band, it cannot detect failure. Already partly tested: CaiCa's G4 fired on a *hand-written* label, never on a Jev output |
| N2 | **The same strong case with its differentiator stripped** (KOI minus its trust story: no history, no network, no brand) | Isolates whether `defensibility` responds to the actual differentiator or to the general impression of competence |

**N2 is the true negative control** — it holds everything constant except the variable the
rubric claims to measure. Spec §8.6 says a scorer that cannot fail is not a scorer. **N1 and
N2 are how we prove this one can.**

---

## 4. What each control predicts (recorded BEFORE running)

| # | Control | Predicted band | Predicted discriminating dimension | Rationale |
|---|---|---|---|---|
| C1 | KOI | Viable/Strong | defensibility | ✅ CONFIRMED at 66, Viable — defensibility +2 |
| C2 | ActiveSG | Strong | position_availability | Owns "cheapest access, no contract" — G1's inversion test |
| C3 | Pet Lovers Centre | Strong | defensibility | Longest trust, largest retail footprint |
| C4 | Sheng Siong | Viable | competitive_room | Strong but facing a dominant incumbent |
| C5 | Michelin hawker | **Viable or Contested** | **defensibility** | **The key test:** successful but no classic moat |
| C6 | TCM clinic chain | Viable | defensibility | Trust-based, unstructured category |
| C7 | Clinic | Viable | market_headroom | Regulated, registry data available |
| C8 | Tutoring centre | Contested | competitive_room | Fragmented, price-driven |
| C9 | B2B service firm | **GATE or refuse** | — | **Tests whether the derivation works without a registry** |
| N1 | Closed business | GATE (fired) | defensibility | Must fail — tests gate firing on a real run |
| N2 | KOI minus differentiator | **Contested, not Viable** | defensibility | Must drop ~10+ points from C1 |

**The three that matter most:**
- **C5** — if a Michelin hawker scores high on defensibility, the dimension is measuring "is
  this business good" not "is it defensible".
- **N1** — if a dead business scores mid-band, the gates are decorative.
- **N2** — the only control that isolates the rubric's central claim.

---

## 5. Success criteria

The control set validates the rubric if ALL of:

1. **Rank correlation holds.** All three Group-A leaders score above all known-troubled cases
   (CaiCa 53). Not just KOI.
2. **C5 does not score defensibility ≥ 4.** If it does, the dimension is broken and must be
   rewritten as a *specific* claim about copy-resistance, not a general impression.
3. **Both negative controls fail as predicted.** N1 fires a gate. N2 drops ≥10 points from C1.
4. **C9 either derives a usable set or refuses cleanly.** Silent under-derivation is the worst
   outcome — worse than refusal.
5. **At least one gate fires on a Jev output**, not on a hand-written label. Currently 0/4.

**Failure of any one criterion is a finding, not a setback.** The point of the set is to make
the rubric's weaknesses locatable.

---

## 6. Method notes

**Ground truth must be external where possible.** For C2–C4 and C7–C8 the categories have
public registries or published data. That gives a source of truth **not authored by me** —
which addresses the project's largest structural weakness (every label so far was written by
the scorer).

**Predictions are recorded before the run** (§4). Any post-hoc revision must be logged with
the original prediction visible.

**The derivation runs first, always.** Each control gets a derived competitive set before
scoring, so category and evidence are held constant across the control and its comparison case
(as C1/KOI and CaiCa share one derived set).

**Sean labels any three.** Still outstanding and still the highest-value gap: three blind human
labels would give the first independent check on whether the scorer tracks a human.
