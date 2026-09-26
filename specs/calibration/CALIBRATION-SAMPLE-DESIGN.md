# CALIBRATION SAMPLE DESIGN — stratified by data availability × outcome

**Date:** 2026-09-25
**Trigger:** Sean — *"For the human labelled cases, can we be a bit more systematic? Check online for
all bankrupt cases to set the floor. Then you have listed companies that set the bar. Then what you
do is to assess listed companies with good data set because of reporting requirements, but are
experiencing issues to work the middle? After you are done with this. Then test with non listed
singapore companies."*
**Status:** DESIGN — not yet executed. Two research findings below change the plan materially.

---

## 1. Why this design is right

The blocker has been that labels require ground truth, and small businesses have none. **Listed
companies have mandatory, audited, publicly-filed ground truth.** Stratifying by data availability ×
outcome is the correct instinct — it takes the hardest part (labelling) and picks the population
where it is already solved.

**The three tiers Sean specified:**

| tier | source of truth | why it's labelable |
|---|---|---|
| **FLOOR** — bankrupt | MinLaw compulsory-liquidation records; SGX delisting announcements | Unambiguous event, legally recorded |
| **MIDDLE** — listed, in trouble | **auditor's going-concern opinion**; qualified opinion; going-concern trading suspension | **A professional judgement, filed under regulation** |
| **BAR** — healthy listed | audited financials; dividends; order books | Continuous good data |
| **THEN** — non-listed SG | ACRA + SSIC; no ground truth | The real target population, tested last |

---

## 2. FINDING A — ground truth has never been this good: the auditor's going-concern opinion

**The middle tier has an expert label I did not expect.**

An audit report stating **"material uncertainty related to going concern"** is:
- a **professional judgement** by a qualified auditor,
- made **under regulation** (ISA 570),
- **filed publicly** with SGX,
- and **dated before the outcome**.

**This is as close to an independent human label as exists in this project.** It is not my opinion,
not the model's, and not derived from the outcome — it is an expert saying "in my judgement this
business may not survive."

Live 2025 examples found: **Pan Hong** (FY2025 auditor's comments, material uncertainty re: going
concern) and a second issuer with a **qualified opinion AND material uncertainty** (FY2025).

**Additional machine-findable middle-tier signals:**
- **Trading suspension on going-concern grounds** — since Oct 2025, SGX RegCo suspends only where
  "clear evidence of going concern issues... commencement of formal insolvency or restructuring
  proceedings." A suspension under the new rule is itself a labelled event.
- **The 3-year suspension cure limit** (SGX RegCo, May 2026) — a company that hits it is labelled.

**This makes the middle tier the strongest tier in the design**, not the weakest.

---

## 3. FINDING B — the SGX financial watch-list was REMOVED on 29 Oct 2025

**My first instinct was to use the SGX watch-list as the middle-tier source. It no longer exists.**

SGX RegCo deleted it effective **29 October 2025** (public consultation May 2025) as part of a
shift to a disclosure-based regime, alongside:
- trading suspensions now limited to **clear going-concern evidence**,
- public trading queries replaced by **private engagement**,
- a lower **S$10M profit test** for listing.

**Consequence for the design:** the middle tier must be built from **going-concern opinions and
suspension events**, not from watch-list membership. Watch-list *history* (pre-Oct-2025) is still
usable for retrospective cases, but it is a closed dataset — **no new entries will ever be added.**

**This is a live-source decay finding.** Any design that assumed the watch-list would have been
building on a removed source — the same class of error as the CAGR/backlog instruments that were
available only where not needed.

---

## 4. THE PROBLEM I HAVE TO FLAG — "bankrupt" does not mean "bad positioning"

**This is the most important design risk, and it is not obvious.**

The floor labels **financial failure**. Our rubric measures **positioning viability**. These are
correlated but they are **not the same thing**, and the Singapore data proves it:

| company | what actually killed it | was its *positioning* weak? |
|---|---|---|
| **Hyflux** | **leverage and a botched restructuring** — membrane technology was genuinely world-class; it failed on debt taken on for a failed Middle East expansion | **NO — arguably strong** |
| **Ezra / Swiber / Ezion / Swissco** | **commodity, undifferentiated, highly-levered offshore marine** — they all did the same thing with no differentiation and died **together** when oil crashed | **YES — textbook positioning failure** |

**If the rubric scores Hyflux's positioning HIGH, that is not a falsification — it may be correct.**
Hyflux is a *financial* failure with a defensible product. Treating it as a floor case would
penalise the rubric for being right.

**Therefore the floor must be stratified by WHY the business failed:**

```
FLOOR-A — POSITIONING FAILURES  (good floor cases)
  undifferentiated commodity players that died together:
  Ezra, Swiber, Ezion, Swissco, Nam Cheong, Triyards
  -> the rubric SHOULD score these low. If it scores them high, the rubric is broken.

FLOOR-B — FINANCIAL-STRUCTURE FAILURES  (NOT floor cases)
  defensible product, destroyed by leverage/execution/one bad bet:
  Hyflux
  -> a HIGH score here is not a failure. These belong in a separate
     "strong positioning, did not survive" category and are diagnostic, not pass/fail.
```

**Without this split, the floor tier would be invalid** — it would mix two different phenomena and
produce a contradiction that looks like a rubric failure but is a labelling failure.

**The offshore marine cluster is unusually valuable:** many firms, same commodity offering, same
fate, same period. That is a natural experiment in "no differentiation → no survival" and it is the
best floor material available anywhere.

---

## 5. SECOND PROBLEM — the INPUT unit does not match the form

**Our rubric scores a form** (business name, category, differentiator, positioning sentence,
competitors named, customer description). **An annual report is not that form.**

To score Hyflux I must **construct** the form answers from filings. **Whoever writes the input is
authoring the measurement.** If I write "differentiator: membrane technology" I have made a
judgement that drives `defensibility` and `mental_advantage`.

**The honest consequence — which dimensions this design can actually validate:**

| dimension | validatable from public filings? | why |
|---|---|---|
| **market_headroom** | **YES — well** | about the CATEGORY, which is publicly knowable |
| **competitive_room** | **YES — well** | about competitors, who are public |
| **demand_reach** | **partially** | customer segments inferable from disclosures |
| **defensibility** | **weakly** | the *claim* is the owner's; I'd be substituting my reading |
| **mental_advantage** | **weakly** | requires buying-situation survey data, not in filings |

**So this design validates the MARKET half of the rubric strongly and the FIRM half weakly.**

**That is still a large gain** — the market half includes `market_headroom`, whose A3 build is
freshest and least tested, and `competitive_room`, the worst-performing dimension. **But it must not
be reported as "the rubric is validated."** It is a partial validation with a named boundary.

**Mitigation — separate the two halves:**
1. **Market-half cases (all tiers):** construct the *category and competitor* inputs from public
   sources; score only `market_headroom` + `competitive_room`; compare to the label. **Clean.**
2. **Firm-half cases (middle + bar tiers only):** the going-concern/healthy label plus any
   published strategy statements. **Weaker, disclose it.**

---

## 6. The design

### Tier 1 — FLOOR-A: positioning failures (~6 cases)
Undifferentiated commodity clusters that failed together. **Prediction: LOW composite.**
Candidates: **Ezra, Swiber, Ezion, Swissco, Nam Cheong, Triyards** (+ Emas Offshore).
Source: MinLaw; SGX delisting/liquidation announcements.

### Tier 2 — FLOOR-B: strong positioning, did not survive (~2 cases, NOT pass/fail)
**Hyflux** (+ one other) — diagnostic only. A HIGH score is an *expected* result, not a failure.
These test whether the rubric distinguishes "bad business" from "good business, bad balance sheet."

### Tier 3 — MIDDLE: listed, going-concern material uncertainty (~10 cases)
**The strongest tier.** Label = the auditor's own words.
Candidates: **Pan Hong**, the FY2025 qualified-opinion issuer, plus companies suspended on
going-concern grounds under the Oct-2025 rule, and restructured survivors (**Marco Polo Marine,
Pacific Radiance, Nam Cheong**).
**Prediction: MIDDLE composite — should not read Strong, need not read Fragile.**

### Tier 4 — BAR: healthy listed (~10 cases)
Strong audited financials, dividends, healthy order books (e.g. the S$17.8bn net order book issuer
in the results presentation found above). **Prediction: HIGH composite.**

### Tier 5 — REAL TARGET: non-listed Singapore companies (~10 cases)
ACRA + SSIC data. No ground truth. **This is where the rubric meets the population it serves**,
and it is deliberately last — it is the only tier that tests the real use case.

**Total: ~38 cases.** Enough for rank agreement and, more importantly, honest disagreement analysis.

---

## 7. CRITICAL — delisting ≠ failure (a trap avoided)

The 2025 "delisting wave" (~16 companies) is **mostly voluntary privatisation, not distress**:
CapitaLand Investment, iFast, SLB Development, PEC, Econ Healthcare, Sinarmas Land, ICP,
Amara Holdings, Procurri, Ban Leong.

**These are healthy companies being taken private.** Using them as floor cases would invert the
label — a rubric scoring them HIGH would be correct while looking like a false positive.

**Rule: the floor is built ONLY from compulsory liquidation, judicial management leading to winding
up, or mandatory delisting following insolvency.** Voluntary delisting is excluded unless
insolvency is documented.

---

## 8. What this does NOT establish

- **It does not validate the firm half of the rubric.** `defensibility` and `mental_advantage`
  cannot be scored from public filings without me authoring the input. **Named boundary.**
- **The labels still are not "expert positioning judgements."** A going-concern opinion is an expert
  *financial-survival* judgement. It is far better than nothing and it is not the same claim as
  "an expert agrees with this positioning score." **Correlated, not identical.**
- **Survivorship is inverted, not removed.** I select cases *because* they failed, so the outcome is
  known before scoring. Pre-registration mitigates this; it does not eliminate it.
- **`market_headroom` for these cases will mostly be ELASTIC**, so A3 will drop it — meaning tiers
  1–5 mostly test `competitive_room` and the four firm-side dimensions, **not A3's inelastic path**.
  A3's inelastic path is still validated on 3 cases only.
- **The going-concern middle tier is a formal-audit population**, not representative of ordinary
  SMEs — they are much larger and have auditors. **The non-listed SG tier is the only representative
  one, and it is the tier with no labels.**
- **I have not yet verified the candidate companies' filings are retrievable** (links.sgx.com,
  FinancialFilings, company IR sites). Named by search only.
- **Sample size ~38 remains modest**, and only ~6 cases carry the strongest floor label.
