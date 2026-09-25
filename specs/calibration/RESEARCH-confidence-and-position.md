# RESEARCH — Confidence Handling & Position Availability

**Date:** 2026-09-23
**Question (Sean):** *"Let's look into confidence handling and position availability. Can you
perhaps research online on how to solve such issues? We have a new web search protocol with
perplexity."*

**Protocol used:** `web-search-scraping-protocol` v2.0. Backend verified live before use
(`perplexity` registered + available, `_managed_web_search()=True`, no explicit
`search_backend` → line 169 of `tools/web_tools.py` resolves to perplexity). Note: one call
fell back to the keyless tier with an explicit `backend_error` — the protocol's
failure-mode-flagging worked as designed and is disclosed here rather than smoothed over.

---

## 1. Headline finding

**The two problems are one problem, and positioning science already solved it.**

`position_availability` is broken because it asks an **absolute** question about a
**relative** phenomenon. The literature is unambiguous that mental availability is *always*
relative and *must* be normalised against brand size:

> "Mental Advantage occurs when the number of links between a brand and a Category Entry
> Point is **higher than statistically expected, given the brand's size** and the attribute's
> prototypicality."
> — quantilope / Romaniuk (Ehrenberg-Bass)

Our dimension asks *"is a position available for you to take?"* — a vacancy search. The
science asks *"do you over-index on this buying situation relative to what a brand of your
size should?"* — a **relative** measure. That single change fixes KOI (leader scored 2),
fixes CaiCa (failing scored 2), and unifies challenger and incumbent cases under one formula,
which is exactly what our rubric failed to do.

---

## 2. Problem A — `position_availability`

### 2.1 The evidence

| Case | Ground truth | Our score | Problem |
|---|---|---|---|
| KOI | market leader, ~20% share, owns top-of-mind | **2** | leader scored worse than a failing brand |
| CaiCa | failing, 6 outlets → 3 | **2** | same score as the leader |
| C5 hawker | Michelin star since 2016 | **4** | correct, but for an unrelated reason |
| C3/C6/C4/C2 | strong operators | 3,3,3,3 | no discrimination at all |

Our conclusion from controls: **directionally plausible, uniformly unreliable.** Mean
confidence 0.40, minimum 0.19 — the least confident dimension in every single run, while
carrying 25% of the composite weight.

### 2.2 What the science says

**Category Entry Points (CEPs)** are the buying situations that trigger recall — *when,
where, why, with whom, feeling what, doing what*. They are **situations, not features,
benefits, or audiences**:

> "'Creamy texture' is a product attribute. 'Making a sandwich for the kids' packed lunch' is
> a Category Entry Point."

**Mental availability** = the probability the brand is retrieved in a buying situation.

Four standard metrics (all relative to competitors):

| Metric | Measures | Our analogue |
|---|---|---|
| **Mental Market Share** | share of all CEP associations in the category | replaces our "position" |
| **Mental Penetration** | % of buyers linking brand to ≥1 CEP | our "demand reach" |
| **Network Size** | avg number of CEPs linked per buyer | **new — we have no analogue** |
| **Share of Mind** | strength on specific high-value cues vs competitors | our "competitive room" |

**Predicted predictive power:** quantilope's 2024 meta-analysis across 100+ brands found
**MMS vs sales r = 0.83, R² = 0.69** — one survey metric explaining ~70% of sales variance.
This is the strongest validity claim available for any scoring dimension in our rubric.

### 2.3 The operationalisation (this is the part that matters)

quantilope's automation gives the exact rule, and it requires **no consumer survey**:

> "Cells in green are attributes that score **5% or more above the expected score** for that
> brand/attribute relationship (advantages). Cells in red are attributes that score **5% or
> more below** the expected score (disadvantages). Cells in white are 'on par'."

**Expected** is a function of (a) brand size and (b) the CEP's prototypicality — both of
which we already derive. So we can compute this **from the derivation we already run.**

### 2.4 Proposed rewrite

Rename and redefine the dimension:

| | Old | New |
|---|---|---|
| **Name** | `position_availability` | `mental_advantage` |
| **Question** | "Is there a position left to take?" | "Does this business over-index on buying situations relative to what its size predicts?" |
| **Comparison** | absolute | **relative — measured against expectation, not against zero** |
| **Scale** | 1–5 absolute | over/on-par/under-index, then mapped to 1–5 |
| **Works for** | challengers only | **challengers AND incumbents** |

**Why this fixes the KOI case.** KOI over-indexes on "reliable everyday tea" and "trusted
chain" relative to a brand its size. That is a Mental **Advantage** — a positive score.
CaiCa under-indexes: it is a brand with six outlets and no recalled cue, so its associations
fall *below* what its size predicts. **Same formula, opposite signs, no inversion bug.**

**Why this also explains C5 at 4.** A single hawker stall owning a Michelin star is an
enormous over-index relative to what a one-stall operation should command. Correct for the
right reason.

### 2.5 Two supporting additions

**(a) Network Size is a dimension we lack.** The literature flags the failure mode we keep
hitting: *"a brand famous for exactly one situation is fragile."* Bonefirm is famous for one
thing (menopausal joint pain) — narrow network. KOI is linked to many occasions. **This
distinguishes them in a way no current dimension does.** It also gives the free report a
genuinely new, teachable insight.

**(b) Absence mapping** (Sagum white-space method) — score each competitor-channel/occasion
for intensity, then flag zones where **demand is high and competitor attention is low**. This
is the derivable version of "white space" and maps directly onto our existing derivation
stage. Confirms the derivation approach is the right shape.

---

## 3. Problem B — confidence handling

### 3.1 The evidence, and the surprise

**The peer-reviewed finding is the OPPOSITE of our symptom.** LLM judges are documented as
**overconfident**, not underconfident:

| Model | Accuracy | ECE ↓ | MCE ↓ |
|---|---:|---:|---:|
| DeepSeek-R1-0528 | 85.4 | **7.17** | 70.0 |
| GPT-4.1 | 63.1 | 34.9 | 70.0 |
| **DeepSeek-V3-0324** | 50.6 | **47.9** | 70.0 |
| GPT-4o | 49.7 | 47.1 | 58.1 |
| Mistral-Nemo | 19.4 | 68.9 | 78.7 |

*(ECE = expected calibration error; lower is better. TH-Score penalises overconfident errors.)*

> "State-of-the-art LLMs exhibit this issue prominently, leading to **inflated confidence
> scores that do not reflect true performance**."

**Our Jev output is the anomaly: it reports 0.19–0.86 and occasionally exactly 0.00.** A
judge that under-reports confidence is either (a) unusually well-calibrated, or (b)
measuring something that is not confidence.

We already proved (b): **our "confidence" tracks competitor-evidence coverage, not model
certainty.** The literature confirms the diagnosis — a self-reported confidence with no
calibration set has **no established meaning.** It cannot be validated, so it must not be
displayed as though it were a probability.

### 3.2 Three concrete defects, with fixes

**Defect B-1 — "confidence" is a misnomer.**
We established it measures evidence coverage. The literature supports reporting these as
**two separate quantities**:

| Quantity | Source | What it legitimately says |
|---|---|---|
| **Evidence coverage** | how much competitor evidence was retrievable | how much we looked at |
| **Judgment spread** | the model's raw probability distribution | how close the call was |

Neither is "confidence" in the calibrated sense. **Proposal: rename the displayed quantity to
`evidence_coverage`, and show judgment spread separately.** Never present either as a
probability that the score is correct.

**Defect B-2 — the display floor is missing.**
Three exact zeros in 55 measurements. A 0.00 is **not a low score** — it is a dead-even
distribution, the model reporting *no preference at all*. Rendering a number at 0.00
coverage as a judgment is a fabrication. **Proposal: below the floor, render
`insufficient evidence to score`** — which the spec already specifies as the `unscored`
contract, and which the control runs proved the model will return when input is thin.

**Defect B-3 — point estimates are the wrong output shape.**
The correct reporting standard is an **interval that separates two uncertainty sources**:

> "Our framework constructs confidence intervals that account for uncertainty from **both the
> test dataset and a human-labeled calibration dataset.**"
> — 2511.21140 (v4, May 2026)

**We have no human-labelled calibration set.** Therefore we can honestly report only the
first source. **Proposal: report a judgment interval (e.g. "3, plausibly 2–4") from the raw
distribution, and state plainly that the calibration component is not yet quantified.** This
is the same finding as the project's #1 blocker, arriving from the literature independently.

### 3.3 The score-compression finding, cross-checked

The Likert literature explains our 2–4 clustering:

> "The defining difference between scale types is the 'Neutral' option; odd scales (3, 5, 7)
> allow for indifference, whereas even scales (4, 6) are **forced-choice models that
> eliminate the middle ground.**"

And on resolution: *"Reliability gains flatten after about 5–7 categories."*

**So adding points will not help.** Our 5-point scale isn't too coarse — **the problem is the
comfortable midpoint**, and the fix is qualitative, not numerical:

- Our level anchors differ in **degree** ("moderate… good… strong") where they must differ
  in **kind**. The literature agrees: anchors must be qualitatively distinct.
- **Proposal: rewrite level 3 from "moderate" into a definite state** (e.g. "no distinct
  position — the claim is not available and cannot be made available without changing the
  business"), so there is no hedged middle to retreat into. Optionally test a forced-choice
  4-point scale, which the literature specifically recommends for eliminating central
  tendency.

---

## 4. What this changes in the rubric

| # | Change | Addresses | Evidence |
|---|---|---|---|
| **R1** | Replace `position_availability` with **`mental_advantage`** (relative to expected, not absolute) | the weakest dimension, 25% of weight | Romaniuk / E-B via quantilope |
| **R2** | Add **`network_size`** — breadth of buying situations linked | the "famous for one thing" failure mode | E-B: coverage beats depth |
| **R3** | Rename displayed `confidence` → **`evidence_coverage`**; show **judgment spread** separately | mislabelled quantity | the 3 defect tests |
| **R4** | **Never render a score below the coverage floor** — emit `insufficient evidence to score` | 3 exact zeros | our own control runs |
| **R5** | Report **judgment intervals**, not point scores; disclose the missing calibration component | point estimates | 2511.21140 |
| **R6** | Rewrite level anchors to be **qualitatively distinct**; level 3 becomes a definite state | 2–4 compression | Likert forced-choice literature |
| **R7** | Keep the **derivation** stage — the white-space literature confirms it | the set construction | Sagum absence mapping |

**What this does NOT fix, and nothing found can:** the absent human baseline. The literature's
prescription (a human-labelled calibration set) is the same requirement the project already
identified. **No amount of research substitutes for it.**

---

## 5. Sources

| Source | Used for | Type |
|---|---|---|
| Romaniuk / Ehrenberg-Bass, via quantilope *Mental Advantage* + *Mental Availability* | CEPs, MMS, Network Size, 5% threshold | applied institute method |
| quantilope 2024 meta-analysis (100+ brands) | MMS↔sales r=0.83, R²=0.69 | vendor meta-analysis |
| useloops — *Identify and Measure CEPs* | 3-phase method, coverage>depth | practitioner (E-B based) |
| marketingscience.info — *Identifying and Prioritising CEPs* | competitive battery, always relative | institute |
| arXiv 2508.06225v2 — *Overconfidence in LLM-as-a-Judge* | ECE/MCE table, overconfidence | peer-reviewed |
| arXiv 2511.21140v4 — *How to Correctly Report LLM-as-a-Judge Evaluations* | two-source intervals, calibration requirement | peer-reviewed |
| Sagum — *The White Space Advantage* | absence mapping, semantic-gap method | practitioner |
| Likert scale literature (multiple) | forced-choice vs neutral midpoint | methodology |

**Caveat on source quality, stated plainly:** the operational detail (the 5% threshold, the
four metric definitions, the r=0.83 figure) comes from **vendor and practitioner sources**,
not the primary E-B papers. The institute's own pages sit behind commercial enquiry. The
*concepts* are well-attested across independent sources; the *specific thresholds* are a
single vendor's operationalisation and should be treated as a starting hypothesis to
calibrate, not a validated constant.

---

## 6. Predictions — recorded BEFORE implementation

If R1 is correct, re-running the control ladder should produce **monotonic separation on the
new dimension** where the old one had none:

| Case | Ground truth | Old `position_availability` | Predicted `mental_advantage` |
|---|---|---|---|
| N1 closed | dead | — | lowest (no associations at all) |
| CaiCa | failing | 2 | **low** (under-index) |
| C9 B2B | crowded, undifferentiated | — | low–mid |
| C9/C2 mid cases | — | 3 | mid |
| C5 hawker | Michelin star | 4 | **high** (huge over-index for one stall) |
| KOI | market leader | **2 (broken)** | **high** (over-index on trust/everyday) |
| C3 Pet Lovers | dominant | 3 | high |
| C6 Eu Yan Sang | dominant, 146 yrs | 3 | high |

**Falsification test:** if KOI and CaiCa still score within 1 level of each other on
`mental_advantage`, R1 has failed and the dimension should be cut, not patched.

**Second falsification test:** if every high-ground-truth case scores the same level (no
monotonic spread), the dimension is not measuring advantage — it is measuring size.
