# v4 — Workbench: A Personal SWE-bench That Grows From Your Own Agent's Completed Work

**Status:** Design v4 (post-Track-0 measurement)
**Terminating condition met:** clean recomputed k=3 table produced; instrument under version control with regression tests.
**Honest ledger:** verdicts recomputed from transcript evidence, not natively produced (the native clean run is a 30-minute nice-to-have, not a blocker). n=2 on self-replay — the instrument works; the pool-wide replay rate is pending.

---

## 0. The thesis, stated once

Every benchmark reports the summary. The trajectory is the truth. On the construction of this benchmark itself, **nine environment failures were found, and in every case where summary and trajectory disagreed, the trajectory was right** — summary-only evidence would have produced a wrong verdict in all nine. That is not a rate: we investigated these cases *because* something looked wrong, so the sample is disagreement-biased, and how often summary and trajectory agree is unmeasured. What is measured, and striking, is that not one of the nine disagreements resolved in the summary's favor. This is the empirical spine of the document, and it is load-bearing: it is the observed reason the benchmark's own harness needed environment discipline, which would otherwise have silently corrupted every number the grid produced.

Workbench is the private, personal instantiation of the SWE-bench construction methodology: benchmark instances mined from your own completed sessions, contamination-impossible by construction (private repo, tasks postdate any relevant training run), distribution-matched by definition. A personal SWE-bench. The novelty is the data source and the automation of curation; the methodology is convergent with the most validated benchmark lineage in the field, which we re-derived from first principles over eleven rounds of measurement.

## 1. The measured state (Track 0 result)

The four-number table, recomputed from transcript evidence under corrected gates:

| Metric | Value | Note |
|---|---|---|
| Write-target sessions (30d) | 42 | Up from a guessed 150/month; measured |
| Objective (grid-eligible) | 12/42 (29%) | Stable across two measurement methods |
| Clean self-replay | 2/2 candidates, 3/3 trials each | Recomputed; n=2, rate pending |
| Environment lies extracted | 9 | All closed, 4 under regression test |

**The instrument works** — pin, spawn-with-explicit-cwd, containment, precondition gate, scorer, run record. **The funnel's replay rate is pending** — 2/2 says nothing yet about pool-wide rate.

## 2. Two-tier curation

Not all real work is scorable. Only Tier A feeds the grid; Tier B feeds the harness and drift branches.

- **Tier A — objective outcome, pinnable environment.** Spec/interface-decoupled: "add assertion type X to class Y," "replace CSS with design-system classes." Scoreable by deterministic marker, re-runnable at any git state, anti-circular by construction. → grid-eligible.
- **Tier B — contextual, welded to a moment.** Most repo surgery, fuzzy refactors, investigations. Not reproducibly scoreable. → harness episodes + drift only.

The grid is fed by a minority of real work, because only that minority is trustworthy enough to compare models on. A small honest grid beats a large noisy one.

## 3. Environment discipline — why any number Workbench emits is believable

A benchmark result is only as trustworthy as the environment discipline behind it. This is the product claim, not a bug list. Workbench treats environment isolation as a first-class gate, because nine documented ways the environment can lie were found during construction — each would have silently corrupted a number, and each is now an enforced gate or a recorded provenance field:

1. **tool_name column None** → parse tool-call JSON, not the column.
2. **model resolution override** → assert `model_used == intended` after every run; mark record contaminated on mismatch.
3. **cwd / session-cwd unpinned** → explicit `cwd=WORKTREE` at spawn; never inherit ambient cwd.
4. **shared worktree across trials** → fresh worktree per trial.
5. **post-fix pin** (agent no-ops on already-solved world) → precondition gate: verify target absent at pin before each trial.
6. **solution leakage** (answer key one directory over) → containment assertion: writes confined to worktree, sibling-repo reads flagged.
7. **relative-path resolution against runner cwd** → resolve against worktree root (under regression test).
8. **double-append of trial record** → single append (under regression test).
9. **agent-side provenance absent** → record session cwd, model, budget, skill set, harness config hash; bind to session ID.

When environment discipline is absent, any of these produces a verdict the summary reports as trustworthy and the trajectory proves wrong. When it is present, a result you see is a result you can trust — and if a run is contaminated, the run record says exactly how. That is the difference between "we ran a benchmark" and "you should believe the number." It is also the method paper's spine: the discipline is the argument for why any of Workbench's outputs carry weight. (Nine environment failures were found during construction; where summary and trajectory disagreed, the trajectory was right every time — a disagreement-biased sample, not a base rate.)

**Two failure signs, one class.** Trial 2 demonstrated wandering-induced false *negative* (capable model scored as failure for an environment-induced error). The same mechanism *inflates* on a different task shape — a session in the real repo given a merged-answer task "verifies" and reports success. One class, two signs; containment retires both.

## 4. Paired grid + coarse routing

Routing is resolved at coarse granularity until volume accumulates. The grid is a **paired design** — same task through each model at the same pinned state — analyzed with McNemar on discordant pairs. Fine-grained per-category model selection leans on the synthetic grid (controllable N); the real-task grid *validates* that synthetic winners hold on real distribution.

The routing output is an **empirical model card** — the grid's frontier as machine-readable capability metadata, consumable by any meta-router (including GoA-style routers and Hermes's own dispatcher). This is the one adoptable idea from the collaboration-literature: routing on measured capability, not README claims.

## 5. Harness branch (primary value)

Every failed real task — Tier B included — is an episode written to the harness `EpisodeLog`. The harness loop proposes edits grounded in real observed failures, lab-tests them against the promoted pool, and promotes winners through the existing fairness gate.

This is the primary economic value, and it's worth being precise about why. Routing saves dollars; harness improvement compounds. A harness gain lifts every future task of that type, and it is the one branch whose output is not bounded by Sean's review bandwidth — a promoted edit, once graduated through the ladder, applies and the improvement accrues. The doc's value hierarchy is deliberate: **harness improvement > trust/coverage > dollar routing.** Routing is the enabler; harness improvement is the payoff.

**Selection-bias honesty (the load-bearing disclosure).** The curation gates select for easy-to-verify tasks, which are biased toward what the agent already handles well. That creates a validity gap the doc does not paper over: the harness loop's *evidence* comes from Tier B failures (behavioral signals: retried, corrected, abandoned), but its *measured lift* is on Tier A tasks (the verified pool). An edit is proposed from one population and validated on another. The honest handling is two-part:

- **Contrastive replay** validates edits on the pinnable-but-unassertable subset — Tier B sessions that are restorable even though not assertion-scorable. Show the judge the old trajectory and the new trajectory against the original request, ask which better satisfies it. Comparative judgment is a categorically easier and better-calibrated task than absolute pass/fail — the pairwise-LLM-judging literature documents position and verbosity bias and standardizes the mitigations: order randomization plus swap-and-rerun with ties on disagreement (one extra judge call). At a handful of episodes per proposed edit, human adjudication is the ground truth with the judge as triage.
- **Disclosed scope.** Lift measured on Tier A is reported as "verifiable improvement on verifiable work"; impact on contextual Tier B is explicitly unmeasured unless contrastive replay validates the specific failing episodes. We never claim Tier B improvement from Tier A evidence.

The distinction this rests on: **replayable ≠ assertable.** Pinnable-but-unassertable tasks exist (the ambiguous refactor in a committed repo) and are the natural home for contrastive validation; unpinnable tasks (gone forever as replay targets) are disclosed, not scored. A-for-the-replayable-subset with contrastive adjudication, disclosure for the rest.

## 6. Autonomy ladder

Promoted configs graduate through rungs, not a switch:

1. **Propose** → 2. **Lab test** (on promoted pool) → 3. **Shadow** (K live tasks alongside incumbent) → 4. **Apply**

Graduation to auto-apply is pre-registered: N consecutive shadow passes with zero reversals **AND** the contrastive-replay validation is live. The headline "your harness gets better from the work it already did" is true on a schedule, not today.

## 7. Assertion hierarchy

Tests-as-assertions are preferred over LLM-generated outcome contracts wherever they exist — a real test suite is an assertion generator with zero circularity risk. Where no test exists, outcome contracts are generated from the user's acceptance criteria ("what would you check to confirm this is done"), never from any model's solution path. Anti-circularity is a promote-time gate.

## 8. Falsification tests (pre-registered)

- **Grid starvation:** <2 broad domains yield a significant McNemar result after 30 days → routing branch dropped, harness+drift kept.
- **Circularity leak:** >3/20 spot-checked assertions check path not outcome → disable auto-promote.
- **Pin failure:** >30% of candidate Tier A tasks unpinnable on inspection → gate too loose.
- **No harness value:** zero edits pass fairness gate in 60 days → reassess.
- **Discrimination:** easy tasks (weak baseline also passes) route to canary, not grid — they're regression sentinels, not grid fuel.

## 9. What is proven vs. pending

**Proven:** the instrument works (2/2 candidates 3/3 under corrected gates, verified pro completion at pin); the funnel exists (42 write-target, 29% objective); the methodology is convergent with SWE-bench construction; nine environment failures found and closed, four under regression test, and in every one the trajectory was right against the summary.

**Pending:** the pool-wide replay rate (the ten-candidate batch — pre-registered protocol, gray-zone branch applies). **Correction (2026-08-04):** the **summary-vs-trajectory base rate is NOT yet measurable.** The instrument does not emit a trajectory verdict — `batch_runner.py` previously assigned both `summary_verdict` and `trajectory_verdict` to the same marker-check boolean, which would have let the base-rate claim be *reported* without being *measured*. The verdict is now split honestly: the runner emits `summary_verdict` (marker check) + `containment_verdict` (deterministic provenance: confinement + leakage, catches inflation and confirms containment — NOT trajectory-truth) and sets `trajectory_verdict` to **None** (never a copy of summary). A containment violation sets `needs_review=True` and the candidate is quarantined (excluded from the grid) until an adjudicator clears it. Measuring the actual base rate requires an **LLM-judge trajectory pass** over transcripts (one judge call per run, BYOK token cost, order-randomized pairwise adjudication per §5) — that pass is the prerequisite, not a field the current instrument can fill. The native clean batch (nice-to-have) and fine-grained routing volume also remain pending.

**Explicit non-overclaim:** 2/2 is n=2. The instrument is the finding. The rate is pending. This doc is written so that the next measurement either clears a bar or refutes one — it does not assume a bar was cleared.

## 10. Export

Three artifacts, three audiences:
- **3a — aggregate report:** demo serving the growth loop. Honest framing: "this is what Workbench produced for one user."
- **3b — stranger-install:** the proof object. A stranger runs `workbench init` on their Hermes and gets their own report.
- **3c — method paper:** the argument. Data is private; method isn't. Leads with the personal-SWE-bench framing, the discrimination gate, contrastive-replay validation, the funnel numbers, and the environment-discipline spine (nine failures found, trajectory right in every disagreement, base rate measured once the ten-task field logs it).

---

*Written from the terminating table. Eleven rounds ago this was a press release asserting a 47-task weekly dashboard from a curation engine that didn't exist. The distance was carried by refusing to report a number known to be dirty — twice, at cost, including when it was the number being chased.*
