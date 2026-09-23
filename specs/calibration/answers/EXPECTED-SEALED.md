# Calibration Label Sheet (SEALED)

> ## ⛔ SEAN — DO NOT OPEN THIS FILE UNTIL AFTER YOUR BLIND SCORING RUN
>
> This file holds the **expected outcome per case**: the band Jev must land in, the dimension
> shape, and the gate states.
>
> Your blind run (D16) is worthless if you read this first. The entire purpose of your run is
> to produce an **independent** human baseline — if you have the expected answer in your head,
> you will reproduce it and we will have measured nothing. That is the failure mode this file
> exists to prevent.
>
> **Sequence:** score all six cases blind → then open this file → then look at Jev's output.

---

## How these labels were derived

The analysis's own **executive summary verdict** for each engagement, converted into the
five dimensions and the gate states. The analysis is the ground truth — it is the thing the
product claims to approximate.

**The label is the conclusion, reverse-applied to the starting inputs.** Jev sees only the
starting inputs (the `inputs/*.json` files). It must reach the conclusion.

## Scoring scale (for the blind run)

Each dimension scored 1–5. Gates (G1–G5) fire when a dimension falls below its floor.
See `specs/obs-spec-095-business-review-lead-engine.md` §5.4.

| Score | Meaning |
|---|---|
| 5 | Strong — clearly favourable |
| 4 | Good |
| 3 | Adequate / contested |
| 2 | Weak |
| 1 | Failing — the gate floor |

| Gate | Floor | Note |
|---|---|---|
| G1 Market headroom | ≥ 2 | Category trap |
| G2 Competitive pressure | ≥ 2 | Priced to the floor |
| G3 Position availability | ≥ 2 | Position occupied |
| G4 Defensibility | ≥ 2 | Nothing to defend |
| G5 Demand reach | ≥ 2 | No identifiable buyer |
| G6 Input sufficiency | — | Separate path |

**⚠ Floor semantics.** **1 means failing**, so every floor is ≥ 2. The first draft set most floors
to 1, which made a score of **1 pass the very gate it was supposed to fire** — CaiCa's
defensibility of 1 would have passed G4 instead of firing it. Caught by
`specs/calibration/check_blind_run.py`. **This correction applies to the spec too (§5.4).**

---

## Labels

### 01 — Bonefirm

| Dimension | Expected | Why |
|---|---|---|
| Market headroom | **4** | Menopause supplement market is real, growing, and the Asia-specific gap is documented |
| Competitive pressure | **3** | Crowded from both directions (retail calcium at the floor, global menopause brands above) but no one owns the intersection |
| Position availability | **4** | The bone/joint × menopause intersection is genuinely empty |
| Defensibility | **2** | **The weak one.** NEM is a commodity; the formula has no clinical proof; the position is copyable. The analysis's own advantage quadrant puts the only durable moat in trust and education, which is hard to build |
| Demand reach | **3** | A segment exists (silent-risk-aware woman) but is not the demographic the founder named |

- **Composite: 63 → Viable, conditional (60–74)**
- **Gates: all pass**
- **The ONE GATE:** whether women actually buy the *stack* — the premium's fairness rests on the
  comparator being real. The analysis names this B1.

### 02 — GreenPackers

| Dimension | Expected | Why |
|---|---|---|
| Market headroom | **4** | Real category, regulatory tailwind |
| Competitive pressure | **2** | BioPak's structural moat (domain, channel) is severe, verified |
| Position availability | **2** | The obvious claims (home-compostable, eco) are already taken |
| Defensibility | **2** | Only the microplastic-tested angle is open, and it is unverified |
| Demand reach | **3** | Real B2B buyers exist, but the channel is owned by the incumbent |

- **Composite: 49 → Contested (40–59)**
- **Gates: all pass**, but pressure and position sit at the floor
- **⚠ J3 CANDIDATE.** The analysis says *"fringe, <1%; guerrilla warfare is the only play"* — which
  reads Fragile-adjacent. But the *strategy* (flanking entry) is a Contested response. **Flag for
  hand-read; do not force.** This is exactly the §10.6-J3 case the protocol exists for.

### 03 — PetDirectory

| Dimension | Expected | Why |
|---|---|---|
| Market headroom | **4** | SGD 412M market, growing 12.5%/yr |
| Competitive pressure | **4** | Genuinely few direct competitors; owns the category search term |
| Position availability | **4** | "The trusted full-service pet directory" is unclaimed |
| Defensibility | **3** | The database (534 listings) is real but not hard to copy |
| Demand reach | **2** | **The weak one — at the floor.** No traffic, no demand engine, no social presence |

- **Composite: 69 → Viable, conditional (60–74)**
- **Gate G5 does NOT fire** (demand = 2, floor is 2) — it sits exactly on the floor
- **The ONE GATE:** whether demand can be generated at all — *"534 listings × 0 visitors = 0 value."*

### 04 — CaiCa

| Dimension | Expected | Why |
|---|---|---|
| Market headroom | **3** | Category is real and large |
| Competitive pressure | **2** | CHAGEE dominates at 4.7–4.9★ with ~46 stores |
| Position availability | **2** | Both claimed angles (local, healthier) are shared, copyable or contradicted |
| Defensibility | **1** | **Failing.** No durable reason-to-purchase; the product itself repels it |
| Demand reach | **3** | Bubble tea buyers obviously exist |

- **G4 FIRES** — Defensibility 1 is below the floor of 2
- **Output: GATE, not a composite.** The report states there is currently no differentiator rather
  than scoring it. The weighted composite would have given 41 (Contested) — **the gate corrects a
  materially wrong answer**, which is the §5.4 argument proved on a real case.
- **The ONE GATE:** the product. Not the positioning.

### 05 — SG Fitness venture

| Dimension | Expected | Why |
|---|---|---|
| Market headroom | **3** | Giant market, but saturated at every tier |
| Competitive pressure | **2** | Top owned, bottom owned, middle died (True Fitness liquidation) |
| Position availability | **4** | Two flank lanes genuinely empty (therapeutic, quiet/sensory) |
| Defensibility | **3** | Trust+clean is a floor others *could* adopt but no incumbent defends |
| Demand reach | **4** | The Prime-Years cohort is identifiable, solvent and underserved |

- **Composite: 64 → Viable, conditional (60–74)**
- **Gates: all pass**
- **The ONE GATE:** whether the specific demographic will actually pay a premium outside the
  state tier.

### 06 — SaladShop venture

| Dimension | Expected | Why |
|---|---|---|
| Market headroom | **3** | Real but bounded category |
| Competitive pressure | **2** | CBD saturated top and value tier; heartland value is owned |
| Position availability | **3** | CBD is taken; the heartland premium tier is genuinely thin |
| Defensibility | **3** | Concept differentiation (Japanese/Korean) is copyable but first-moverable |
| Demand reach | **3** | Clear segments, but the wallet is contested by meal-prep and hawkers |

- **Composite: 56 → Contested (40–59)**
- **Gates: all pass**
- **The ONE GATE:** whether the heartland premium customer exists at a sustainable price.

---

## Expected distribution

| Case | Expected output |
|---|---|
| Bonefirm | Viable, conditional (63) |
| GreenPackers | Contested (49) — **J3 candidate** |
| PetDirectory | Viable, conditional (69) |
| CaiCa | **GATE — G4 fires** |
| SG Fitness | Viable, conditional (64) |
| SaladShop | Contested (56) |

**Three distinct outcomes — one gate fire, two Contested, three Viable. No Fragile, no Strong.**

A scorer that returns **Strong** for anything has failed. A scorer that returns the **same output
for all six** has no discriminating power regardless of accuracy.

**⚠ Two corrections this sheet has already been through — both found by
`check_blind_run.py`, neither by reading:**

1. **Floor semantics.** Floors were set to 1, so a score of 1 *passed* the gate it was meant to
   fire. CaiCa's defensibility of 1 would have cleared G4. Every floor is now ≥ 2.
2. **Label source.** The first labels were taken from each analysis's **market-standing** sentence
   ("fringe, <1% share") instead of its **viability** sentence. That is not the same thing —
   Bonefirm is *also* "<1%, #5+" yet the analysis calls it feasible. **Current market share is not
   a dimension of viability**, and treating it as one was a straight error.
