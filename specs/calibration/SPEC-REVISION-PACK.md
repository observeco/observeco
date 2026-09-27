# SPEC REVISION PACK — OBS-SPEC-095

Recommended revisions to bring the spec in line with the calibrated instrument. Organised by
severity, because one of these is a contradiction that would ship a broken report.

**Every replacement below is written to be pasted, not paraphrased.** Line numbers are from
the current 1,095-line draft (v5).

---

# TIER 1 — CORRECTNESS DEFECTS (the spec contradicts the calibrated instrument)

## R1 ⚠ §5.1's "five dimensions" no longer describes the instrument

**Current (lines 454–462):**

| # | Dimension | Weight | What it measures |
|---|---|---|---|
| 1 | Market headroom | 15% | Is there room to be chosen at all? |
| 2 | Competitive pressure | 20% | How crowded and price-contested? |
| 3 | Position availability | 25% | Does the word you want already have an owner? |
| 4 | Defensibility | 25% | Hard-to-copy × hard-to-build |
| 5 | Demand reach | 15% | Is there an identifiable, reachable, paying segment? |

**Problem.** This is **0.9.0**, and it is not what calibration produced. Three of the five
weights have moved and two dimensions have changed meaning:

- `position availability` (25%) **no longer exists** — it was replaced by `relative_strength`,
  which measures the position *held against the derived competitive set* rather than whether a
  word is unclaimed.
- `competitive pressure` **is now `competitive_room`** and its meaning **reversed**. 0.9.0
  treated a crowded market as *bad*; the calibrated dimension scores a **fragmented** market
  as favourable. The spec has the polarity backwards.
- `mental_advantage` (20%) **is missing entirely** — it is the dimension Sean's own answer
  redefined (how much the brand holds in the mind of the customer).
- `market_headroom` fell **15% → 10%** because A3 drops it in 95% of cases.

**Replacement for §5.1:**

> ### 5.1 The six dimensions
>
> | # | Dimension | Weight | What it measures |
> |---|---|---|---|
> | 1 | Relative strength | 25% | For each buying situation it competes in, how firmly does it hold that situation against the named occupants of it? Judged **per situation**, never as one share fight: positioning is about product categories, not industries. |
> | 2 | Mental advantage | 20% | How much mind the brand holds in its segment. A **magnitude**, not a competitive claim — a brand can hold a great deal of mind while close rivals hold a similar amount. **Independent of closure.** |
> | 3 | Defensibility | 20% | The challenger's cost to displace it: the accumulated barriers the business **holds**, not the differentiator its form claims. |
> | 4 | Competitive room | 15% | Landscape, not business. Fragmented and uncontested = 5; few giants and a price war = 1. |
> | 5 | Market headroom | 10% | Is there unmet demand? Dropped automatically where supply is capacity-elastic (A3). |
> | 6 | Demand reach | 10% | Can it find and reach an identifiable paying group? Addressability, not demand size. |
>
> **Positioning dimensions carry 70%** (relative strength + mental advantage + defensibility),
> because the brief is *viability through differentiation*, not industry attractiveness.
>
> **Weights are a hypothesis refined by calibration (D6).** The values above are the outcome of
> calibration against 120 human-graded businesses across 27 categories — see §10.7.

## R2 ⚠ §3.10's per-dimension signals reference dimensions that no longer exist

**Current (lines 299–306):** a table mapping each input to a gate, naming `Market headroom (G1)`,
`Competitive pressure (G2)`, `Position availability (G3)`, `Defensibility (G4)`,
`Demand reach (G5)`.

**Problem.** Every one of those gate IDs is void (see R3), and two of the five dimension names
are void (see R1).

**Replacement:**

> **What the input must carry.** One signal per scored dimension:
>
> | Input signal | Feeds | Absent means |
> |---|---|---|
> | Category / what the business does and to whom | Market headroom · Competitive room | Non-specific enough to place in a category |
> | A positioning or differentiator sentence | Relative strength · Mental advantage · Defensibility | A **non-position** — see below |
> | Named competitors (may be empty) | Relative strength | Derived by enrichment, never trusted from the form |
> | A price point or price band | Competitive room | Absent **and** unenrichable |
> | Who its customers are | Demand reach · Mental advantage | A buyer group that cannot be identified |
>
> **The floor refuses; it does not score low.** Below the floor the scorer returns
> `REFUSED_INPUT_QUALITY` with the missing signals named (G6, §5.4). Reporting a low score for
> an unanswerable submission would attribute the submitter's brevity to their business — the
> same defect class as scoring the form instead of the business, which §10.7 records as the
> single most repeated error in calibration.

## R3 ⚠ §5.4's six gates were REMOVED by calibration — and the reason is in the spec's own history

**Current (lines 494–520):** Part 1 six gates; floors of ≥2; "the weighted composite, computed
only when all six gates pass".

**Problem — and this is the most serious item in this pack.** Calibration removed **all score
gates**, and the measured reason is precise:

> `defensibility ≥ 2` (G4) fired on 10 of 75 cases, and **8 of those 10 were live, large
> businesses** — KFC, Burger King, Zoff, Harvey Norman, Spectacle Hut, Pure Fitness, Virgin
> Active, R&B Tea. The model was not wrong about them: a generic fried-chicken chain genuinely
> has no moat. **The gate turned "this business has no moat" into "we cannot assess this
> business." Those are different statements.** A no-moat business is eminently assessable, and
> refusing it throws away exactly the negative signal the report exists to deliver.

That is the same self-inflicted-wound pattern the spec already caught once, at line 507:
*"the first draft set most floors to 1, which made a score of 1 pass the very gate it was meant
to fire."* **The floors were fixed; the gates themselves were the wrong instrument.** Removing
them eliminated 8 false refusals out of 10 firings.

**Replacement for §5.4:**

> ### 5.4 Two refusals, and no score gates
>
> **There are no score gates.** Calibration tested them and removed them (see §10.7). A gate
> turns *"this business has no moat"* into *"we cannot assess this business"* — different
> statements, and the second one discards the negative signal the report exists to deliver.
> A low dimension score is a **finding**, reported, not a refusal.
>
> **Two refusals remain, and both mean "we cannot answer", never "the answer is bad":**
>
> | Refusal | Trigger | Output |
> |---|---|---|
> | **Assessability** | The business cannot be analysed from any input (the classifier's `refuse_when` choice) | `REFUSED_UNASSESSABLE` — no composite |
> | **Input quality** | The §3.10 floor is not met | `REFUSED_INPUT_QUALITY`, naming the missing signals — no composite |
>
> **A single model call is not a third refusal.** The assessability classifier is asked first
> and carries no weight; it selects whether the instrument can judge the business at all.
>
> **Composite.** Computed whenever any dimension is scored, over the scored dimensions only,
> with weights renormalised at runtime and the weights actually used recorded (§5.2).
>
> `composite = round( Σ (level_i / count_i) × weight_used_i )`
>
> Note the formula: the level is divided by its **count**, not by `count − 1`. The lowest level
> therefore contributes `1/count`, so the composite **floor is ≈20, not 0**. This was the source
> of a reported defect that turned out to be a replication error (§10.7) — worth stating
> because it is easy to "fix" a scale that is not broken.
>
> **Bands** (calibrated): Fragile 5–37 · Contested 38–57 · Viable, conditional 58–76 · Strong
> 77–100. Band edges are derived from level-means, so they do **not** move when weights move.
>
> **Band agreement is the launch criterion**, not dimension exactness (§10.6).

## R4 ⚠ §5.4's "85/100 for a category trap" worked example is void

**Current (line 484):** *"a submission scoring 0 on Market headroom — a textbook category trap
— and 5/5 on every other dimension reaches 85/100, band 'Strong.'"*

**Problem.** `market_headroom` is 10%, not 15%, so the arithmetic no longer holds; and the fix
proposed in that paragraph (gates) is the fix calibration removed. The *concern* is still
valid — **a weighted sum lets strength in some dimensions compensate for a fatal flaw in
another** — but the remedy changed.

**Replacement:**

> **The compensating-flaw concern is real and is handled by disclosure, not gating.** A
> weighted sum lets strength in one dimension mask a fatal flaw in another. Calibration
> established (§10.7) that gating is the wrong remedy here, because refusing the report loses
> the finding. The remedy is that the report **always names the weakest dimension and the
> single largest weighted shortfall** (the "one gate", §5.5) as a computed predicate — so a
> compensating flaw is stated in the verdict rather than averaged away or suppressed.
>
> **Weight concentration is the second control.** Positioning carries 70% across three
> correlated dimensions, so a submission cannot reach the top band on market attractiveness
> alone.

## R5 §10.6's launch gate tests the wrong thing, and cannot currently be run

**Current (lines 1003–1005):** *"'Clears' = same band per case, every dimension within ±1
level, all gates stable, controls fail."*

**Problem.** Two defects. (a) **"every dimension within ±1 level" is not achievable** — the
measured dimension-exact agreement is 56.5% and the bar was replaced by band agreement (Sean,
D1). (b) **The gate cannot be run at all: 5 of its 6 canary cases do not exist in the corpus.**

**Replacement:**

> ### 10.6 Launch gate
>
> **Ship the scored report when the instrument clears the following, on the corpus in §10.1:**
>
> | Criterion | Bar | Measured today |
> |---|---|---|
> | Band agreement | ≥90% of cases within **one band** of the reference label | **100%** (n=114) |
> | Gross band error | ≤5% of cases **two or more bands** off | **0%** |
> | Disputes at dimension level | ≤5% of dimension scores **≥2 levels** apart | **2.8%** (13 of ~460) |
> | Negative controls | Every control must **fail**, each with its own predicted failure reason | **not built** |
>
> **Dimension-exact agreement is explicitly NOT the bar.** It sits at 56.5%, and demanding it
> would hold the product to a granularity a five-point human-judged scale does not support.
> The client sees a band and a narrative, never a number (§5.8), so band agreement is the
> measure that matches what can be wrong from the client's side.
>
> **Disagreement triage — judge-vs-corpus disagreement is UNRESOLVED until hand-read.** Never
> default to "Jev is wrong"; that has been the wrong call before.
>
> | Branch | Condition | Action |
> |---|---|---|
> | J1 | Hand-read confirms Jev missed | Fix criterion/unit; Jev was wrong |
> | J2 | Hand-read confirms the analysis missed it | Correct the label — **a finding about our own method** |
> | J3 | Both defensible | Dimension genuinely ambiguous → **drop it and state it** (D7) |

---

# TIER 2 — THE SPEC'S OWN BLIND SPOTS

## R6 §5.3 requires two implementations; only one exists

**Current (lines 473–477):** *"The Python calibration harness and the production scorer must
read the same rubric JSON... This is the most likely way to fool ourselves."*

**Problem.** The spec predicted the failure and it has occurred. **There is no production
scorer** — `jev` appears only inside `specs/calibration/`. All 120 calibration runs were made
by the harness. And the file a scorer *would* load, `specs/calibration/rubric.json`, is still
**0.9.0 — five dimensions, and `relative_strength` absent.** So calibration has validated an
instrument that nothing serves.

**Add after §5.3:**

> ### 5.3.1 The rubric promotion step (new — a build gate, not a note)
>
> Two implementations must read the same file, and **which file is a build decision with a
> gate**, because the failure mode is silent: a calibrated rubric that nothing loads produces
> no error and no symptom until a client sees a score from the old model.
>
> | Step | Requirement |
> |---|---|
> | 1 | The chosen rubric is promoted to `specs/calibration/rubric.json` — the single path both implementations read |
> | 2 | The promoted file's `_meta.version` **must** equal its top-level `version`; the harness fails loudly on a mismatch |
> | 3 | Superseded rubrics are retained as `rubric-v<X>.json` for the audit trail, never left as the live file |
> | 4 | A report is not served unless the loaded rubric's `_meta.version` is the promoted one |
>
> **Status: step 1 is NOT done.** The live file is 0.9.0. Until it is promoted, every
> calibration result in §10.7 describes a rubric that is not in service.

## R7 §10.1's canary corpus is 5 of 6 missing, and it is not the same thing as a calibration corpus

**Current (lines 924–939):** a six-case table, described as *"the calibration corpus"*.

**Problem.** Of the six, **only Bonefirm exists.** And the 120-case corpus built in calibration
is a *different instrument* — a population sample for measuring agreement, not a fixed
regression set for detecting drift. The spec conflates them by calling the six "the calibration
corpus".

**Add to §10.1:**

> ### 10.1.1 Two corpora, two jobs — do not conflate them
>
> | | Canary corpus (§10.1) | Calibration corpus (§10.7) |
> |---|---|---|
> | Size | 6 fixed cases | 120 businesses, 27 categories |
> | Input | form-shaped, from real engagements | form-shaped, mixed real and authored |
> | Purpose | **detect drift** — same input, fixed expected output, run on a schedule | **measure agreement** — how closely the instrument tracks a human grader |
> | Changes? | **Never.** A canary whose fixture moves detects nothing | Grows as coverage gaps close |
> | Failure meaning | The model or the rubric moved | The instrument is not yet calibrated |
>
> **The canary corpus is incomplete.** Five of six cases (GreenPackers, CaiCa, PetDirectory,
> SGFitness, SaladShop) do not exist in any corpus. **§10.6's launch gate cannot be run until
> they are restored as form-shaped inputs.** This is a build item, not a documentation item.
>
> **The six were authored by the same person.** §10.5 item 2 already warns they are *"not drawn
> from the population the free form actually sees"*; the 120-case corpus addresses that, which
> is why both are needed.

## R8 §10.5 item 5 says the human baseline is missing. It now exists.

**Current (lines 993–999):** *"There is no human baseline... The cheapest fix for #5 is one
hour of work: Sean scores the six cases from the form-shaped inputs, blind... that single
number — human agreement versus model agreement — is the only evidence that the instrument
measures something real."*

**Problem.** This is now false in the direction that undersells the work. **Sean has graded all
120 cases blind at dimension level** — twenty times the scale the paragraph asks for — and
those grades are the reference labels for everything in §10.7.

**Replacement for item 5:**

> 5. **The human baseline now exists, and it changed the design.** The §10.5 draft called for
>    one hour of blind human scoring on six cases. In calibration, Sean graded **120 businesses
>    across 27 categories** at dimension level, blind to the instrument's scores, plus a
>    separate composite regrade. That is the reference set for §10.7.
>
>    Its findings were not merely reassuring — each one moved the method:
>    - His grades **redefined `mental_advantage`** (how much mind the brand holds; independent
>      of closure) and **confirmed `competitive_room`'s polarity** the reverse of 0.9.0.
>    - He **halved the disputes** on `defensibility` by naming what the dimension should
>      measure ("took decades and huge capital") — the instrument had been scoring the
>      differentiator a form *claims* rather than the barrier a business *holds*.
>    - **59 of 61 of his composite entries copied the instrument's own score into the adjacent
>      column.** Dimension scores had their own distributions so they were not copied, but this
>      is why **composites in §10.7 are recomputed from his dimension scores**, never taken
>      from his composite column.
>
>    **One caveat survives and must be stated:** a single grader's labels can be calibrated to
>    rather than calibrated *against*. A second independent grader would separate the two, and
>    is not available.

---

# TIER 3 — A NEW SECTION: WHAT CALIBRATION ACTUALLY ESTABLISHED

## R9 Add §10.7 — the calibration record

**Why this section is needed at all.** The spec currently argues for a method it describes as
unvalidated. Calibration has since produced measured results, several of which **contradict the
spec as written** (R1–R5) and one of which **reversed a design decision the spec calls "the most
important correction in this revision"** (R3). Without this section a future reader will
re-litigate settled questions — or worse, re-add the gates.

**Add as §10.7:**

> ### 10.7 What calibration established (v1.2.0 → v1.8.0)
>
> **Method.** 120 businesses across 27 categories, form-shaped inputs, scored under a rubric
> whose every change was isolated to one dimension with the other five asserted byte-identical
> as a control. Reference labels: Sean's blind dimension grades.
>
> **A single defect class accounted for every improvement: the instrument was reading the
> SUBMISSION instead of the BUSINESS.**
>
> | Dimension | What it read | What it must read |
> |---|---|---|
> | `demand_reach` | whether the form *named* a channel | whether the business demonstrably reaches buyers — currently trading sets a floor of 3 |
> | `relative_strength` | one share fight against every named competitor | the position held **per situation**, corroborated |
> | `mental_advantage` | whether the *model* could articulate a retrieval occasion | whether the *segment* holds the brand in mind |
> | `defensibility` | the differentiator the form **claims** | the accumulated barriers the business **holds** |
>
> **Two recurring mechanical causes.** (1) The form's `undercut_on` field is the business
> self-reporting its weakness, and it was being scored as the verdict — **candour was
> punished.** (2) **Absence of detail in a form was read as absence in the world.** A business
> with seven outlets was scored as having no route to buyers because the form was terse.
>
> **Corroboration is dimension-specific.** The same physical fact has *opposite* implications
> per dimension: closure destroys **reach** (`demand_reach`) but not **memory**
> (`mental_advantage`). A single shared "physical evidence" rule is too blunt — this was tested
> and failed.
>
> **Measured trajectory** (noise floor ±0.4 pts / ±2 cases, established by re-running one
> rubric twice; 19 of 720 cells moved, symmetrically):
>
> | | exact | disputes ≥2 | offset |
> |---|---|---|---|
> | v1.2.0 baseline | 66.7% | 8.6% | +0.23 |
> | v1.6.0 | 55.9% | 4.7% | +0.09 |
> | v1.8.0 | 56.5% | **2.8%** | +0.09 |
>
> **Exact agreement fell while disputes halved, and that is the intended trade.** Exact
> disagreement was converted into *adjacent* disagreement: cells at gap 0 fell 319 → 271 while
> gap ≥2 fell **41 → 23**. A wrong band misleads a client; an adjacent one does not. Since the
> client sees a band, disputes are the measure that matches the product.
>
> **Product-level result:** band agreement **100% within one band, 0% two or more off** (n=114),
> and **85% exact on the target segment** (businesses the grader placed in the lower two bands)
> — which is the segment D3 names as the lead magnet's audience.
>
> **What calibration did NOT establish.**
> - **Agreement, not accuracy.** The reference labels are one human's; correlated error between
>   the instrument and that human would agree and still both be wrong.
> - **A second grader is absent**, so calibration-to versus calibration-against is unresolved.
> - **The weakest region is the top end** (−7.7 mean composite offset for businesses the grader
>   rated 80+), which is off-target but real.
> - **Seven cases in the lowest band** is a thin cell; the Fragile-band figures rest on n=3 for
>   the extreme.
> - **A defect I reported and then retracted.** I reported that the composite was "compressed"
>   (+13 at the low end, −4.5 at the high end). It was **my own replication bug** — I used
>   `(level−1)/(count−1)` where the harness uses `level/count`, so I was comparing a floor-0
>   scale against a floor-20 one. Verified and retracted. **Recorded here because the corrected
>   figures are what §5.4's formula note protects against.**
>
> **The single lesson worth carrying:** any re-implementation of a harness calculation must be
> verified against the harness's own stored output **before** any finding is built on it. One
> cheap call would have caught the retracted finding.

---

# TIER 4 — SMALLER CONSISTENCY FIXES

| # | Location | Fix |
|---|---|---|
| R10 | §1.2 committed decisions | Add **D11: no score gates** (calibration finding); **D12: band agreement is the launch criterion** (replaces dimension exactness); **D13: positioning carries 70%** across three correlated dimensions |
| R11 | §5.2 (line 469) | *"support N dimensions from day one"* — now demonstrated: `market_headroom` is dropped in **95% of cases**, so the four- and five-dimension render paths are the **normal** case, not an edge case. Say so. |
| R12 | §5.8 (line 554) | *"The five dimensions..."* → **six**; and add that the **level texts** are the most reverse-engineerable asset, since one submission reveals them |
| R13 | §8.6, §11.1 | Anywhere citing `jev-1.13.0` as the pinned model: the rubric now records `model` as **`jev-latest`**, so the pin is not actually enforced by the rubric. Either pin it in the rubric or state that the pin lives elsewhere |
| R14 | §10.2 | Provenance list should add **`weights_used`** and **`rubric_meta_version`** — the first because weights renormalise at runtime, the second because the retracted bug shows two version fields can disagree |
| R15 | Header (line 3) | `Status: DRAFT v5` → **v6**, with a changelog entry naming R1–R9 |

---

# RECOMMENDED ORDER

1. **R3** (remove the gates) — it is a correctness defect that would ship a broken report, and it
   **reverses a decision the spec calls its most important correction**. Also R4, which depends on it.
2. **R1 + R2 + R5** — the dimension set, the input signals and the launch gate all describe a
   retired model. Together they are the "the spec does not describe the instrument" cluster.
3. **R6** (promote the rubric) — otherwise §10.7 describes a file nothing loads.
4. **R9** (§10.7) — the record that stops R1–R5 being re-litigated.
5. **R8** — corrects an understatement that would send someone to redo finished work.
6. **R7** — canary restore; a build item the spec should name as a prerequisite.
7. **R10–R15** — consistency.

**Two items are build work, not spec work, and should be tracked as such:** the production
scorer (R6 step 1) and the five missing canary cases (R7).
