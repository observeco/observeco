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

| Gate | Floor |
|---|---|
| G1 Market headroom | ≥ 2 |
| G2 Competitive pressure | ≥ 1 |
| G3 Position availability | ≥ 1 |
| G4 Defensibility | ≥ 1 |
| G5 Demand reach | ≥ 1 |

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

- **Composite band: Contested (40–59) — "winnable, but not on the current plan."**
- **Gates: all pass** (no dimension below its floor)
- **Verdict shape:** feasible, conditional on the gate
- **The ONE GATE:** whether women actually buy the *stack* — the premium's fairness rests on the
  comparator being real. The analysis names this B1.
- **Deliberately NOT scored low:** the founder's superlative and jargon are *presentation* flaws,
  not market flaws. The analysis did not say the business was bad — it said the position needs
  flanking entry and one behavioural check. **A scorer that lands Fragile here is wrong.**

### 02 — GreenPackers

| Dimension | Expected | Why |
|---|---|---|
| Market headroom | **4** | Real category, regulatory tailwind |
| Competitive pressure | **2** | BioPak's structural moat (domain, channel) is severe, verified |
| Position availability | **2** | The obvious claims (home-compostable, eco) are already taken |
| Defensibility | **2** | Only the microplastic-tested angle is open, and it is unverified |
| Demand reach | **3** | Real buyers exist in B2B, but the channel is owned by the incumbent |

- **Composite band: Fragile (5–39)** — the analysis's verdict is *"fringe, guerrilla warfare is
  the only viable play."*
- **Gates: all pass**, but G2 and G3 sit at the floor
- **The ONE GATE:** whether the certifications resolve in public registries. The whole
  "verifiable" position collapses if they don't. The analysis names this A1.

### 03 — PetDirectory

| Dimension | Expected | Why |
|---|---|---|
| Market headroom | **4** | SGD 412M market, growing 12.5%/yr |
| Competitive pressure | **4** | Genuinely few direct competitors; owns the category search term |
| Position availability | **4** | "The trusted full-service pet directory" is unclaimed |
| Defensibility | **3** | The database (534 listings) is real but not hard to copy |
| Demand reach | **2** | **The weak one.** No traffic, no demand engine, no social presence |

- **Composite band: Contested (40–59)**
- **Gates: all pass**
- **Verdict shape:** position open, execution gap
- **The ONE GATE:** whether demand can be generated at all — the analysis's whole thesis is
  "534 listings × 0 visitors = 0 value."

### 04 — CaiCa

| Dimension | Expected | Why |
|---|---|---|
| Market headroom | **3** | Category is real and large |
| Competitive pressure | **2** | CHAGEE dominates at 4.7–4.9★ with ~46 stores |
| Position availability | **2** | Both claimed angles (local, healthier) are shared, copyable or contradicted |
| Defensibility | **1** | **Failing.** No durable reason-to-purchase; the product itself repels it |
| Demand reach | **3** | Bubble tea buyers obviously exist |

- **Composite band: Fragile (5–39)**
- **Gates: G4 FIRES** — Defensibility 1 is at the floor. This case exercises the gate logic.
- **Verdict shape:** the product must be fixed before any position is worth taking
- **The ONE GATE:** the product. Not the positioning.

### 05 — SG Fitness venture

| Dimension | Expected | Why |
|---|---|---|
| Market headroom | **3** | Giant market, but saturated at every tier |
| Competitive pressure | **2** | Top owned, bottom owned, middle died (True Fitness liquidation) |
| Position availability | **4** | Two flank lanes genuinely empty (therapeutic, quiet/sensory) |
| Defensibility | **3** | Trust+clean is a floor others *could* adopt but no incumbent defends |
| Demand reach | **4** | The Prime-Years cohort is identifiable, solvent and underserved |

- **Composite band: Viable, conditional (60–74)**
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
| Demand reach | **3** | Clear segments, but wallet contested by meal-prep and hawkers |

- **Composite band: Contested (40–59)**
- **Gates: all pass**
- **The ONE GATE:** whether the heartland premium customer exists at a sustainable price.

---

## Expected distribution

| Case | Band | Gate fires |
|---|---|---|
| Bonefirm | Contested | none |
| GreenPackers | Fragile | none (G2/G3 at floor) |
| PetDirectory | Contested | none |
| CaiCa | Fragile | **G4** |
| SG Fitness | Viable, conditional | none |
| SaladShop | Contested | none |

**Two Fragile, three Contested, one Viable.** A scorer that returns Strong for anything, or
Fragile for Bonefirm or SG Fitness, has failed. **The spread matters as much as the values** — a
scorer that returns the same band for all six has no discriminating power regardless of accuracy.
