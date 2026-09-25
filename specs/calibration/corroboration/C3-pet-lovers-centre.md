# Corroboration package — C3-pet-lovers-centre

**Model:** `jev-1.13.0` · **rubric** `0.4.1` · **generated** 2026-09-25T06:59:14+00:00

**Verdict:** composite **67** · band **Viable, conditional** · no gates fired

---

## 1. What Jev said

| dimension | score | raw (0-4) | coverage | 80% interval | most-mass level |
|---|---:|---:|---:|---|---|
| Market headroom | **4/5** | 2.74 | 0.68 | 3–4 | level 4 @ 0.62 |
| Competitive room | **2/5** | 1.02 | 0.96 | 2–2 | level 2 @ 0.95 |
| Mental advantage | **3/5** | 2.49 | 0.47 | 2–4 | level 3 @ 0.51 |
| Defensibility | **4/5** | 2.89 | 0.85 | 4–4 | level 4 @ 0.89 |
| Demand reach | **4/5** | 2.62 | 0.43 | 3–5 | level 4 @ 0.56 |

Input sufficiency: **sufficient**

### The exact distributions

```
Market headroom                    {"0": 0.0, "1": 0.0, "2": 0.32, "3": 0.62, "4": 0.06}
Competitive room                   {"0": 0.02, "1": 0.95, "2": 0.03, "3": 0.0, "4": 0.0}
Mental advantage                   {"0": 0.0, "1": 0.07, "2": 0.51, "3": 0.27, "4": 0.15}
Defensibility                      {"0": 0.02, "1": 0.04, "2": 0.02, "3": 0.89, "4": 0.03}
Demand reach                       {"0": 0.08, "1": 0.09, "2": 0.12, "3": 0.5599999999999999, "4": 0.15}
```

---

## 2. What the number means

**The rubric level matching the displayed score, quoted verbatim.** This is a structural fact about the distribution — not an explanation the model produced. Where the highest-mass level differs from the displayed score, that is flagged: it means the judgment sits BETWEEN two levels and the rounded display is hiding it.

- **Market headroom = 4/5** — level 4:
  > Good. A real, growing category in which new entrants do visibly get chosen.
- **Competitive room = 2/5** — level 2:
  > Very little. A dominant player or a severe price floor; the business is structurally squeezed.
- **Mental advantage = 3/5** — level 3:
  > At expectation. Linked to its buying situations at roughly the level its size predicts; neither advantaged nor disadvantaged.
- **Defensibility = 4/5** — level 4:
  > Durable. Copying takes a competitor a year or more, or requires assets they do not have — accumulated trust, an owned distribution channel, a proprietary dataset, or years of relationship.
- **Demand reach = 4/5** — level 4:
  > Good. A clearly identified segment with a trigger and at least one credible channel to reach it.

---

## 3. What it saw

### The owner's own claims (verbatim from the submission)

- **positioning_sentence:** The largest and oldest pet care retail chain in Singapore and Southeast Asia — a household name since 1973.
- **differentiator:** We have 51 years of accumulated trust and the widest and freshest product range in the market. We are the first and largest pet care retail chain in Southeast Asia, with 69 stores in Singapore alone — a footprint no other pet retailer here approaches. We hold exclusive brand partnerships, including bringing international brands like ANIGENE into Singapore, which gives us product access competitors cannot match. Our scale lets us hold national distribution and supplier terms that smaller retailers cannot get.
- **undercut_on:** Price. Online sellers and smaller independent pet shops undercut us on price, and general e-commerce platforms sell the same branded pet food cheaper with no storefront cost. Some customers know exactly what they want and just buy it online.

### Owner-named competitors

- Online sellers and e-commerce marketplaces selling the same branded pet food
- Smaller independent pet shops
- Grocery and hypermarket pet aisles
- Other pet retail chains (Kohepets, Pet Safari)
- The vet clinic as the alternative source of pet care advice and products

### The derived competitive set (what the scorer was actually given)

**TIER 0 DEFAULT**
  - feeding table scraps or generic food
  - doing nothing about grooming
  - home grooming
  - *why:* Cheaper. A pet can be fed without a specialist retailer.

**TIER 1 CHEAP SUBSTITUTE**
  - grocery and hypermarket pet aisles (FairPrice, Sheng Siong, Giant)
  - e-commerce marketplaces (Shopee, Lazada, Amazon)
  - online-only pet retailers (Kohepets)
  - subscription food delivery services
  - *why:* Same branded product, lower price, delivered. No storefront cost to carry.

**TIER 2 DIRECT SET**
  - Pet Safari (physical pet retail chain)
  - Kohepets (online pet retailer)
  - independent pet shops islandwide
  - pet speciality chains
  - *why:* Same category, same product, competing for the same pet-owner purchase.

**TIER 3 CATEGORY INCUMBENT**
  - Pet Lovers Centre — 'Singapore's Trusted Leader in Pet Services'; the household name
  - *why:* The owner shopping for pet supplies in Singapore has PLC at the top of their list. The PetDirectory analysis itself records this: 'Pet Lovers Centre | 'Singapore's Trusted Leader in Pet Services' — brand recognition | You're the neutral directory; they're a retailer.'

**TIER 4 ADJACENT CROSSOVER**
  - veterinary clinics (as a competing source of products and advice)
  - grooming specialists
  - pet insurance
  - pet boarding and daycare
  - *why:* Takes the same pet-care wallet on a different service axis.

**TIER 5 PROFESSIONAL ROUTE**
  - AVS-licensed veterinary practices
  - AVS licensing as the regulatory gate for boarding
  - *why:* The governed path — relevant because AVS licensing defines who can legally operate boarding.

**TIER 6 INDIRECT**
  - rising cost of living reducing discretionary pet spend
  - adoption rates and pet ownership trends
  - *why:* Changes the size of the pet-owning base itself.

### The blindspot delta

- owner named: **5** · derived direct set: **4**
- tier-3 incumbent the owner may not see: ["Pet Lovers Centre — 'Singapore's Trusted Leader in Pet Services'; the household name"]

---

## 4. Reason provenance — read this before judging the reasons

**Jev returns no reasoning.** The API response is a typed answer only — score, legend, probabilities, confidence — measured at ~17 output tokens. The documentation states System One models are built for fast, focused judgments and that 'analyse this and determine the best course of action' is the wrong shape of question for them.

So the rows above are, precisely:

| element | provenance |
|---|---|
| score, distribution, interval, coverage | **MEASURED** — returned by the model |
| the most-mass level text | **QUOTED** from the rubric — a fact about the distribution |
| the evidence basis | **RECORDED** — the state that was sent |
| the blindspot delta | **COMPUTED** — owner list vs derived set |
| *any causal story ('it scored 2 because…')* | **NOT ESTABLISHED.** Not measured, not returned by the model, and deliberately not invented here. |

**Where a cause CAN be established, it is established by perturbation, not by narration** — running the same case with one input changed and measuring the movement. The project already holds several such measurements (e.g. removing KOI's differentiator moves `mental_advantage` 4→2; adding a 'new pet' cue to Pet Lovers Centre moves it 0). Those are real reasons. This package does not generate them for cases where they have not been run.

---

## 5. What I am asking you to do

Judge the **score**, given the evidence in section 3. Not the reasons — because there are no reasons to judge, only a number and the evidence it was given. Specifically:

1. Is each score **within one level** of what you would give, given the SAME evidence?
2. Where you disagree — is it the score that is wrong, or the **evidence** that is wrong (section 3 is what the scorer saw; if it is missing something you know, that is an input defect, not a scoring defect)?
3. Is there a dimension you would **withhold** that was scored, or one that was withheld you would score?
