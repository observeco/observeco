# Corroboration package — C9-b2b-it-services

**Model:** `jev-1.13.0` · **rubric** `0.4.1` · **generated** 2026-09-25T06:59:21+00:00

**Verdict:** composite **58** · band **Contested** · no gates fired

---

## 1. What Jev said

| dimension | score | raw (0-4) | coverage | 80% interval | most-mass level |
|---|---:|---:|---:|---|---|
| Market headroom | **3/5** | 2.31 | 0.67 | 3–4 | level 3 @ 0.63 |
| Competitive room | **3/5** | 1.78 | 0.78 | 2–3 | level 3 @ 0.74 |
| Mental advantage | **3/5** | 1.69 | 0.35 | 2–4 | level 2 @ 0.49 |
| Defensibility | **2/5** | 0.74 | 0.77 | 1–2 | level 2 @ 0.73 |
| Demand reach | **4/5** | 2.63 | 0.61 | 3–4 | level 4 @ 0.56 |

Input sufficiency: **sufficient**

### The exact distributions

```
Market headroom                    {"0": 0.01, "1": 0.02, "2": 0.63, "3": 0.33, "4": 0.01}
Competitive room                   {"0": 0.0, "1": 0.24, "2": 0.74, "3": 0.02, "4": 0.0}
Mental advantage                   {"0": 0.05, "1": 0.49, "2": 0.18, "3": 0.28, "4": 0.0}
Defensibility                      {"0": 0.27, "1": 0.73, "2": 0.0, "3": 0.0, "4": 0.0}
Demand reach                       {"0": 0.0, "1": 0.02, "2": 0.37, "3": 0.56, "4": 0.05}
```

---

## 2. What the number means

**The rubric level matching the displayed score, quoted verbatim.** This is a structural fact about the distribution — not an explanation the model produced. Where the highest-mass level differs from the displayed score, that is flagged: it means the judgment sits BETWEEN two levels and the rounded display is hiding it.

- **Market headroom = 3/5** — level 3:
  > Moderate. A real category with real buyers, but flat, or structurally unfavourable to new entrants.
- **Competitive room = 3/5** — level 3:
  > Some. Crowded and price-contested, but gaps exist for a small operator.
- **Mental advantage = 3/5** — level 3:
  > At expectation. Linked to its buying situations at roughly the level its size predicts; neither advantaged nor disadvantaged.
  - ⚠️ **rounding warning:** the highest mass is on level 2 (49%) — the raw value 1.69 sits between level 3 and level 2. Treat the display as approximate.
    > Over-indexes nowhere but is present. It appears in the category but owns no situation more strongly than its size alone would predict.
- **Defensibility = 2/5** — level 2:
  > Shallow. A competitor can copy it in weeks without doing any development of their own — a claim, a message, or an off-the-shelf ingredient.
- **Demand reach = 4/5** — level 4:
  > Good. A clearly identified segment with a trigger and at least one credible channel to reach it.

---

## 3. What it saw

### The owner's own claims (verbatim from the submission)

- **positioning_sentence:** One accountable team for every layer of your IT, instead of juggling eight vendors.
- **differentiator:** We publish our rates. Almost nobody else in Singapore managed IT does — every comparison with competitors turns into four meetings and a custom quote. We also hold bizSAFE Level 3 for site work, and we align compliance work to PDPA and, for regulated clients, MAS expectations. Our clients name us as the single owner of every service line, so nothing falls between two suppliers.
- **undercut_on:** Price at the low end and incumbency at the high end. Smaller providers quote per-ticket rates below our retainer, and the larger MSPs have longer relationships and more engineers.

### Owner-named competitors

- One in-house IT hire (the alternative to buying)
- Separate single-service vendors (the status quo we replace)
- The larger established MSPs with longer client relationships
- Cheaper per-ticket IT support shops

### The derived competitive set (what the scorer was actually given)

**TIER 0 DEFAULT**
  - doing nothing — tolerating IT problems
  - the owner or an office manager handling IT ad hoc
  - an informal arrangement with a tech-savvy staff member
  - *why:* Free, and for a small SME a working laptop is a working laptop until it isn't. The default is to absorb the problem rather than buy a service.

**TIER 1 CHEAP SUBSTITUTE**
  - per-ticket or break-fix IT support shops
  - freelance IT technicians
  - a single in-house hire at the low end
  - consumer-grade SaaS tools bought ad hoc
  - *why:* Pay for what breaks, nothing monthly, no contract. For an SME with occasional problems this looks cheaper than a retainer.

**TIER 2 DIRECT SET**
  - Advance IT (SME-focused, SG-based team, 99.5% retention claim)
  - FunctionEight (20+ yrs, regional, Asia partner for Western firms)
  - iXiZ Technology (est. 2006, per-user rate from S$2/user/day)
  - Rezolva (est. 2012, publishes 8 service lines and 3 named tiers)
  - TYPENT (4 productized outcomes with defined SLAs)
  - Techease Solutions (explicitly 'transparent, fee-only, vendor-agnostic')
  - *why:* Same service, same retainer model, same SME target. Six credible providers findable in ONE search — crowded and undifferentiated.

**TIER 3 CATEGORY INCUMBENT**
  - the larger established MSPs (longer relationships, more engineers, enterprise logos)
  - the in-house IT department as the mental default
  - *why:* The buyer is not shopping for 'managed IT' — they are shopping for 'make my IT stop being a problem'. The category word is a supplier-side term. Owners who have never bought managed IT have no mental ladder for it at all; they have one for 'my IT guy'.

**TIER 4 ADJACENT CROSSOVER**
  - IT hardware resellers who bundle support
  - accounting/HR outsourcing firms bundling IT
  - cybersecurity-only specialists
  - cloud resellers (Microsoft/Google partners)
  - *why:* Takes the same SME IT budget on a narrower or adjacent scope.

**TIER 5 PROFESSIONAL ROUTE**
  - audit and compliance firms for MAS/PDPA obligations
  - CSA-recognised cybersecurity consultants
  - bizSAFE/certification bodies
  - *why:* The governed path — relevant because compliance is part of what the buyer needs.

**TIER 6 INDIRECT**
  - SaaS consolidation reducing the need for managed support
  - cloud migration reducing on-prem hardware needs
  - AI tools reducing helpdesk volume
  - *why:* Shrinks the underlying problem the service exists to solve.

### The blindspot delta

- owner named: **4** · derived direct set: **6**
- tier-3 incumbent the owner may not see: ['the larger established MSPs (longer relationships, more engineers, enterprise logos)', 'the in-house IT department as the mental default']

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
