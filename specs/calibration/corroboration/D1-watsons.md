# Corroboration package — D1-watsons

**Model:** `jev-1.13.0` · **rubric** `0.4.1` · **generated** 2026-09-25T06:59:21+00:00

**Verdict:** composite **44** · band **Contested** · no gates fired

---

## 1. What Jev said

| dimension | score | raw (0-4) | coverage | 80% interval | most-mass level |
|---|---:|---:|---:|---|---|
| Market headroom | **3/5** | 2.0 | 0.88 | 3–3 | level 3 @ 0.88 |
| Competitive room | **2/5** | 0.82 | 0.74 | 1–2 | level 2 @ 0.70 |
| Mental advantage | **2/5** | 0.72 | 0.52 | 1–2 | level 2 @ 0.48 |
| Defensibility | **2/5** | 1.3 | 0.27 | 1–3 | level 2 @ 0.31 |
| Demand reach | **withheld** | 1.68 | 0.0 | — | below coverage floor — no judgment |

Input sufficiency: **sufficient**

### The exact distributions

```
Market headroom                    {"0": 0.01, "1": 0.05, "2": 0.88, "3": 0.06, "4": 0.0}
Competitive room                   {"0": 0.24, "1": 0.7, "2": 0.06, "3": 0.0, "4": 0.0}
Mental advantage                   {"0": 0.43, "1": 0.48, "2": 0.04, "3": 0.05, "4": 0.0}
Defensibility                      {"0": 0.29, "1": 0.31, "2": 0.22, "3": 0.18, "4": 0.0}
```

---

## 2. What the number means

**The rubric level matching the displayed score, quoted verbatim.** This is a structural fact about the distribution — not an explanation the model produced. Where the highest-mass level differs from the displayed score, that is flagged: it means the judgment sits BETWEEN two levels and the rounded display is hiding it.

- **Market headroom = 3/5** — level 3:
  > Moderate. A real category with real buyers, but flat, or structurally unfavourable to new entrants.
- **Competitive room = 2/5** — level 2:
  > Very little. A dominant player or a severe price floor; the business is structurally squeezed.
- **Mental advantage = 2/5** — level 2:
  > Over-indexes nowhere but is present. It appears in the category but owns no situation more strongly than its size alone would predict.
- **Defensibility = 2/5** — level 2:
  > Shallow. A competitor can copy it in weeks without doing any development of their own — a claim, a message, or an off-the-shelf ingredient.

---

## 3. What it saw

### The owner's own claims (verbatim from the submission)

- **positioning_sentence:** Your everyday health and beauty store, everywhere.
- **differentiator:** We are the largest health and beauty retailer in Singapore with around 18% market share, more than 100 outlets, and the only loyalty programme among the three main chains. We also run pharmacy e-consultation services, which no competitor in our segment offers. Our scale means we carry the widest brand range and can sustain promotions the smaller chains cannot match.
- **undercut_on:** Nothing, on price. All three main chains price within cents of each other and match each other's promotions. We are not cheaper and do not try to be. What we lose on is that nobody chooses us for anything specific — customers pick whichever chain is nearest.

### Owner-named competitors

- Guardian Health & Beauty (137 stores, DFI Retail Group, ~14% share)
- Unity Pharmacy (60+ stores, NTUC FairPrice)
- Supermarkets — FairPrice, Cold Storage, Sheng Siong now carry the same categories
- Online — Shopee, Lazada, iHerb for repeat purchases

### The derived competitive set (what the scorer was actually given)

**TIER 0 DEFAULT**
  - not buying — using up what is at home
  - supermarket aisle during the weekly grocery shop
  - borrowing from a household member
  - *why:* Most personal-care purchases are subsumed into a grocery trip rather than being a destination decision.

**TIER 1 CHEAP SUBSTITUTE**
  - Sheng Siong / FairPrice / Giant own-brand toiletries
  - Daiso (flat pricing)
  - value stores and neighbourhood provision shops
  - Shopee and Lazada for repeat consumables
  - *why:* The commodity end of personal care has moved to supermarkets and marketplaces.

**TIER 2 DIRECT SET**
  - Guardian Health & Beauty (137 stores)
  - Unity Pharmacy (60+ stores)
  - Watsons (100+ stores)
  - *why:* Three chains, near-identical pricing and range, competing almost entirely on location and promotion timing.

**TIER 3 CATEGORY INCUMBENT**
  - Watsons — largest share (18%) and the only loyalty programme
  - Guardian — historically the pharmacy brand, now pivoting to mass-market
  - Unity — cheapest at regular price, smallest range
  - *why:* The category has no distinctive-word incumbent. Ownership is by outlet proximity, not by owning a phrase in the buyer's mind. This is the diagnostic point.

**TIER 4 ADJACENT CROSSOVER**
  - Sephora and cosmetics specialists (premium beauty)
  - specialist skincare retailers
  - pharmacies attached to clinics
  - convenience stores (7-Eleven) carrying toiletries
  - *why:* Takes the same spend through a different format or a more specialist framing.

**TIER 5 PROFESSIONAL ROUTE**
  - doctors and polyclinics for medication
  - dermatologists and aesthetic clinics for skin
  - hospital pharmacies
  - *why:* The governed path for anything beyond over-the-counter.

**TIER 6 INDIRECT**
  - e-commerce shifting repeat purchases away from stores
  - private-label growth in supermarkets
  - cost-of-living shifting staples to value channels
  - *why:* Changes where the category is bought at all.

### The blindspot delta

- owner named: **4** · derived direct set: **3**
- tier-3 incumbent the owner may not see: ['Watsons — largest share (18%) and the only loyalty programme', 'Guardian — historically the pharmacy brand, now pivoting to mass-market', 'Unity — cheapest at regular price, smallest range']

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
