# Corroboration package — C5-michelin-hawker

**Model:** `jev-1.13.0` · **rubric** `0.4.1` · **generated** 2026-09-25T06:59:15+00:00

**Verdict:** composite **73** · band **Viable, conditional** · no gates fired

---

## 1. What Jev said

| dimension | score | raw (0-4) | coverage | 80% interval | most-mass level |
|---|---:|---:|---:|---|---|
| Market headroom | **3/5** | 2.32 | 0.68 | 3–4 | level 3 @ 0.65 |
| Competitive room | **3/5** | 1.61 | 0.55 | 2–3 | level 3 @ 0.48 |
| Mental advantage | **5/5** | 3.75 | 0.79 | 4–5 | level 5 @ 0.79 |
| Defensibility | **3/5** | 2.26 | 0.34 | 2–4 | level 4 @ 0.47 |
| Demand reach | **4/5** | 3.1 | 0.65 | 4–5 | level 4 @ 0.60 |

Input sufficiency: **sufficient**

### The exact distributions

```
Market headroom                    {"0": 0.0, "1": 0.02, "2": 0.65, "3": 0.3, "4": 0.03}
Competitive room                   {"0": 0.01, "1": 0.44, "2": 0.48, "3": 0.07, "4": 0.0}
Mental advantage                   {"0": 0.0, "1": 0.01, "2": 0.03, "3": 0.17, "4": 0.79}
Defensibility                      {"0": 0.05, "1": 0.14, "2": 0.32, "3": 0.47000000000000003, "4": 0.02}
Demand reach                       {"0": 0.01, "1": 0.0, "2": 0.13, "3": 0.6, "4": 0.26}
```

---

## 2. What the number means

**The rubric level matching the displayed score, quoted verbatim.** This is a structural fact about the distribution — not an explanation the model produced. Where the highest-mass level differs from the displayed score, that is flagged: it means the judgment sits BETWEEN two levels and the rounded display is hiding it.

- **Market headroom = 3/5** — level 3:
  > Moderate. A real category with real buyers, but flat, or structurally unfavourable to new entrants.
- **Competitive room = 3/5** — level 3:
  > Some. Crowded and price-contested, but gaps exist for a small operator.
- **Mental advantage = 5/5** — level 5:
  > Strongly over-indexes. It is the first retrieval for one or more valuable, frequently-occurring buying situations, beyond what its size predicts; rivals are not close on those situations.
- **Defensibility = 3/5** — level 3:
  > Real but replicable. A competitor must do genuine development work of their own — a formulation, a process, or a technical system — so copying takes them months, not weeks. Still nothing they cannot eventually build.
  - ⚠️ **rounding warning:** the highest mass is on level 4 (47%) — the raw value 2.26 sits between level 3 and level 4. Treat the display as approximate.
    > Durable. Copying takes a competitor a year or more, or requires assets they do not have — accumulated trust, an owned distribution channel, a proprietary dataset, or years of relationship.
- **Demand reach = 4/5** — level 4:
  > Good. A clearly identified segment with a trigger and at least one credible channel to reach it.

---

## 3. What it saw

### The owner's own claims (verbatim from the submission)

- **positioning_sentence:** Singapore's best bak chor mee. The only hawker stall in the country with a Michelin star.
- **differentiator:** We hold one MICHELIN Star and have held it every single year since 2016 — the only hawker stall in Singapore to do so. Our mee pok is cooked to order and dressed with a specific vinegar-chilli-soy blend, layered with crispy dried plaice, pork liver and crackling. We have been popular since long before the star, and people queue for it even at off-peak hours.
- **undercut_on:** Price. We charge $8-15 a bowl, which is two to three times what other bak chor mee stalls charge. Plenty of stalls sell a bowl for $4-5 and some customers will not pay our price or wait in our queue.

### Owner-named competitors

- Other bak chor mee stalls (the general hawker-competitor set — many, individually small)
- Song Fa Bak Kut Teh (heritage hawker brand, queues, expansion into malls)
- Tai Hwa's own former staff who have opened their own stalls
- The surrounding Crawford Lane / Lavender food options for the same lunch occasion
- Home cooking / instant noodles for the same meal

### The derived competitive set (what the scorer was actually given)

**TIER 0 DEFAULT**
  - cooking at home
  - instant noodles
  - skipping lunch
  - eating whatever is nearest
  - *why:* Cheaper and no queue. For a weekday lunch the default is convenience, not a starred hawker stall.

**TIER 1 CHEAP SUBSTITUTE**
  - any of the ~100+ other bak chor mee stalls islandwide at S$4-5
  - other hawker noodle stalls (fishball, wanton, prawn noodle) at S$4-6
  - food court noodle outlets
  - *why:* Half the price or less, no queue, and for most eaters a bowl of noodles is a bowl of noodles.

**TIER 2 DIRECT SET**
  - the handful of other celebrated bak chor mee stalls (e.g. Seng Kee, Ah Seng, MacPherson)
  - other Michelin-listed hawker stalls (Bib Gourmand set)
  - Tai Hwa alumni stalls
  - *why:* Same dish, same occasion, comparable quality reputation. The Michelin guide itself lists alternatives.

**TIER 3 CATEGORY INCUMBENT**
  - Hill Street Tai Hwa itself — the ONLY hawker stall with a Michelin star, held since 2016
  - the broader 'famous Singapore hawker' tier: Song Fa, Tian Tian, Maxwell's chicken rice — brands with queues and heritage
  - *why:* The buyer shopping for 'the best bak chor mee' or 'a Michelin meal' has a short list. Tai Hwa is at the top of it for bak chor mee. But the buyer shopping for 'lunch near Lavender' has no such list.

**TIER 4 ADJACENT CROSSOVER**
  - bak kut teh (Song Fa)
  - other Michelin-listed cheap eats
  - food courts and cafes near Lavender
  - *why:* Same lunch occasion, different dish. A Michelin-hunting tourist weighing Tai Hwa against Tian Tian chicken rice is making one decision.

**TIER 5 PROFESSIONAL ROUTE**
  - *why:* n/a — no professional or institutional path for noodles.

**TIER 6 INDIRECT**
  - grocery inflation reducing hawker-frequency
  - WFH reducing CBD-area lunch traffic
  - *why:* Dilutes the number of hawker lunch occasions.

### The blindspot delta

- owner named: **5** · derived direct set: **3**
- tier-3 incumbent the owner may not see: ['Hill Street Tai Hwa itself — the ONLY hawker stall with a Michelin star, held since 2016', "the broader 'famous Singapore hawker' tier: Song Fa, Tian Tian, Maxwell's chicken rice — brands with queues and heritage"]

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
