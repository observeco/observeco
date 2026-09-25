# Corroboration package — C2-activesg

**Model:** `jev-1.13.0` · **rubric** `0.4.1` · **generated** 2026-09-25T06:59:16+00:00

**Verdict:** composite **72** · band **Viable, conditional** · no gates fired

---

## 1. What Jev said

| dimension | score | raw (0-4) | coverage | 80% interval | most-mass level |
|---|---:|---:|---:|---|---|
| Market headroom | **3/5** | 1.87 | 0.81 | 2–3 | level 3 @ 0.79 |
| Competitive room | **2/5** | 0.98 | 0.82 | 2–2 | level 2 @ 0.81 |
| Mental advantage | **5/5** | 3.6 | 0.67 | 4–5 | level 5 @ 0.74 |
| Defensibility | **withheld** | 1.5 | 0.0 | — | below coverage floor — no judgment |
| Demand reach | **4/5** | 2.64 | 0.42 | 3–5 | level 4 @ 0.51 |

Input sufficiency: **sufficient**

### The exact distributions

```
Market headroom                    {"0": 0.01, "1": 0.16, "2": 0.79, "3": 0.04, "4": 0.0}
Competitive room                   {"0": 0.12, "1": 0.81, "2": 0.05, "3": 0.02, "4": 0.0}
Mental advantage                   {"0": 0.0, "1": 0.03, "2": 0.07, "3": 0.16, "4": 0.74}
Demand reach                       {"0": 0.07, "1": 0.06, "2": 0.19, "3": 0.51, "4": 0.17}
```

---

## 2. What the number means

**The rubric level matching the displayed score, quoted verbatim.** This is a structural fact about the distribution — not an explanation the model produced. Where the highest-mass level differs from the displayed score, that is flagged: it means the judgment sits BETWEEN two levels and the rounded display is hiding it.

- **Market headroom = 3/5** — level 3:
  > Moderate. A real category with real buyers, but flat, or structurally unfavourable to new entrants.
- **Competitive room = 2/5** — level 2:
  > Very little. A dominant player or a severe price floor; the business is structurally squeezed.
- **Mental advantage = 5/5** — level 5:
  > Strongly over-indexes. It is the first retrieval for one or more valuable, frequently-occurring buying situations, beyond what its size predicts; rivals are not close on those situations.
- **Demand reach = 4/5** — level 4:
  > Good. A clearly identified segment with a trigger and at least one credible channel to reach it.

---

## 3. What it saw

### The owner's own claims (verbatim from the submission)

- **positioning_sentence:** The most affordable way to exercise in Singapore — no contract, no barrier.
- **differentiator:** We are a national public programme, not a commercial gym. At S$2.50 per entry and S$30 a month for unlimited access, we are structurally the cheapest way to exercise in Singapore and no commercial operator can undercut us — our pricing is subsidised as a public health objective, not set to make a profit. We hold 29 gyms islandwide, located in the heartlands where commercial premium gyms do not operate. We also have no contract and no sales pressure, which is precisely what the market's most common complaints are about.
- **undercut_on:** Nothing on price — we set the floor. What we lose on is facilities and experience: our gyms are functional rather than premium, with fewer classes, less equipment depth, and no spa or pool-side amenities at most locations. Customers who can afford better sometimes pay for it.

### Owner-named competitors

- Anytime Fitness (161 gyms, S$70-158/mo, 24/7)
- 24/7 Fitness (the former Gymmboxx rollup, 22 outlets, S$98-178/mo)
- Virgin Active, Pure Fitness, Fitness First (premium, S$178-400+/mo)
- Free alternatives — running, park exercise, home workouts
- Community centre gyms and HDB fitness corners

### The derived competitive set (what the scorer was actually given)

**TIER 0 DEFAULT**
  - not exercising at all
  - home workouts
  - running and park exercise
  - HDB fitness corners (free)
  - *why:* Free. For many people the real competition is inertia, not another gym.

**TIER 1 CHEAP SUBSTITUTE**
  - ActiveSG (S$2.50/entry, S$30/mo — the floor)
  - community centre gyms
  - HDB fitness corners
  - free outdoor exercise
  - *why:* Structurally the cheapest access. No commercial operator can price below a subsidised national programme.

**TIER 2 DIRECT SET**
  - Anytime Fitness (161 gyms, S$70-158/mo)
  - 24/7 Fitness (22 outlets, S$98-178/mo)
  - Fitness First (14 clubs, from S$200/mo)
  - Virgin Active (6 clubs, S$178-400/mo)
  - Pure Fitness (12 locations)
  - Platinum Fitness (4 locations, S$150-300/mo)
  - True Fitness (10 outlets — CLOSED 10 Sep 2026, liquidated)
  - *why:* Same service, same occasion. The market is saturated at every price tier and the middle tier just died in a liquidation.

**TIER 3 CATEGORY INCUMBENT**
  - ActiveSG — 'government-subsidised gym floor', owns cheapest access and no-contract
  - Virgin Active / Pure — owns premium full-facility
  - Anytime — owns 24/7 franchise value
  - F45 / Barry's — own boutique class-based HIIT
  - *why:* The SGFitness analysis's §3.1 records the word each player owns. Each tier of the market has a distinct owner, which is why the middle had no word and True Fitness died there.

**TIER 4 ADJACENT CROSSOVER**
  - boutique studios (yoga, pilates, padel)
  - recovery clubs
  - outdoor activity clubs
  - sports teams and leagues
  - *why:* Takes the same fitness time and money through a different format.

**TIER 5 PROFESSIONAL ROUTE**
  - physiotherapy and rehabilitation clinics
  - hospital sports medicine
  - therapeutic/illness-specific exercise programmes
  - *why:* The governed path — and the SGFitness analysis identified therapeutic/illness-specific as one of two genuinely empty flank lanes.

**TIER 6 INDIRECT**
  - rising cost of living squeezing discretionary memberships
  - WFH changing exercise habits and location
  - sports nutrition and wearables taking fitness spend
  - *why:* Changes whether a gym membership is bought at all.

### The blindspot delta

- owner named: **5** · derived direct set: **7**
- tier-3 incumbent the owner may not see: ["ActiveSG — 'government-subsidised gym floor', owns cheapest access and no-contract", 'Virgin Active / Pure — owns premium full-facility', 'Anytime — owns 24/7 franchise value', "F45 / Barry's — own boutique class-based HIIT"]

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
