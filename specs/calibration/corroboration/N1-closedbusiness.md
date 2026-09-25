# Corroboration package — N1-closedbusiness

**Model:** `jev-1.13.0` · **rubric** `0.4.1` · **generated** 2026-09-25T06:59:23+00:00

**Verdict:** composite **None** · band **GATE** · gates firing **['mental_advantage', 'defensibility']**

---

## 1. What Jev said

| dimension | score | raw (0-4) | coverage | 80% interval | most-mass level |
|---|---:|---:|---:|---|---|
| Market headroom | **3/5** | 2.26 | 0.74 | 3–4 | level 3 @ 0.73 |
| Competitive room | **2/5** | 0.87 | 0.81 | 1–2 | level 2 @ 0.77 |
| Mental advantage | **1/5** | 0.28 | 0.77 | 1–2 | level 1 @ 0.73 |
| Defensibility | **1/5** | 0.01 | 0.99 | 1–1 | level 1 @ 0.99 |
| Demand reach | **2/5** | 0.95 | 0.21 | 1–3 | level 1 @ 0.50 |

Input sufficiency: **insufficient**

### The exact distributions

```
Market headroom                    {"0": 0.0, "1": 0.02, "2": 0.73, "3": 0.22, "4": 0.03}
Competitive room                   {"0": 0.18, "1": 0.77, "2": 0.05, "3": 0.0, "4": 0.0}
Mental advantage                   {"0": 0.73, "1": 0.27, "2": 0.0, "3": 0.0, "4": 0.0}
Defensibility                      {"0": 0.99, "1": 0.01, "2": 0.0, "3": 0.0, "4": 0.0}
Demand reach                       {"0": 0.5, "1": 0.15, "2": 0.26, "3": 0.08, "4": 0.01}
```

---

## 2. What the number means

**The rubric level matching the displayed score, quoted verbatim.** This is a structural fact about the distribution — not an explanation the model produced. Where the highest-mass level differs from the displayed score, that is flagged: it means the judgment sits BETWEEN two levels and the rounded display is hiding it.

- **Market headroom = 3/5** — level 3:
  > Moderate. A real category with real buyers, but flat, or structurally unfavourable to new entrants.
- **Competitive room = 2/5** — level 2:
  > Very little. A dominant player or a severe price floor; the business is structurally squeezed.
- **Mental advantage = 1/5** — level 1:
  > Over-index nowhere. Compared with what a business of this size would be expected to own, it is linked to no buying situation beyond bare presence. It has no situation it is retrieved for.
- **Defensibility = 1/5** — level 1:
  > No moat. There is no differentiator at all, or the one claimed is a purchasable input any competitor can relabel this quarter.
- **Demand reach = 2/5** — level 2:
  > Weak. Only a demographic is named; no trigger, no channel, and no evidence they will pay this price.
  - ⚠️ **rounding warning:** the highest mass is on level 1 (50%) — the raw value 0.95 sits between level 2 and level 1. Treat the display as approximate.
    > No identifiable buyer. The customer is undefined, or defined so broadly no one can be targeted.

---

## 3. What it saw

### The owner's own claims (verbatim from the submission)

- **positioning_sentence:** We were a bubble tea shop. We had quite a few flavours.
- **differentiator:** Not really sure we had one. We used the same supplier as a few other shops and the drinks were similar. We had a loyalty card.
- **undercut_on:** Everything. Cheaper shops, bigger chains with apps and promotions. We could not match the pricing or the marketing.

### Owner-named competitors

- A big chain nearby
- The shop two units down

### The derived competitive set (what the scorer was actually given)

**TIER 0 DEFAULT**
  - nothing / water
  - hawker kopi ~S$1.20-2.00
  - convenience-store bottled drinks
  - home-brewed tea
  - *why:* Cheaper, no detour.

**TIER 1 CHEAP SUBSTITUTE**
  - Mixue (S$1.50-3.50, no membership)
  - R&B Tea
  - Each-A-Cup
  - hawker stalls
  - *why:* Cheapest cup on the island.

**TIER 2 DIRECT SET**
  - KOI Thé (90 outlets)
  - LiHO (~70-84)
  - CHAGEE (44)
  - Chicha San Chen (32)
  - Playmade
  - Sharetea
  - HEYTEA
  - *why:* Same product, same occasion. 62+ brands, 953 businesses islandwide. Fragmented but crowded — and the big chains have app-based loyalty and constant promotions.

**TIER 3 CATEGORY INCUMBENT**
  - KOI Thé — the brand credited with starting the modern wave
  - CHAGEE — 'not a bubble tea brand, a tea expert'
  - LiHO — 'No.1 homegrown'
  - *why:* The buyer shops for a treat drink; the top-of-mind brand wins. A single unnamed outlet is not in anyone's mind.

**TIER 4 ADJACENT CROSSOVER**
  - specialty coffee
  - dessert
  - convenience-store RTD tea
  - *why:* Same treat-drink occasion, different product.

### The blindspot delta

- owner named: **2** · derived direct set: **7**
- tier-3 incumbent the owner may not see: ['KOI Thé — the brand credited with starting the modern wave', "CHAGEE — 'not a bubble tea brand, a tea expert'", "LiHO — 'No.1 homegrown'"]

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
