# Working Backwards — ObserveCo Workbench (v3)

## Press Release

**ObserveCo Workbench: Your Harness Gets Better Because of the Work It Already Did — and You Can Prove It**

Workbench turns the real tasks your agents complete into two compounding assets: a verified episode log that drives measurable harness improvement, and a self-growing benchmark that — as evidence accumulates — tells you which model to trust for which work.

Agent observability platforms trace what your agents do. Benchmark frameworks test what they can do on tasks somebody invented. Neither closes the loop that decides whether delegation is trustworthy: *did the harness get better because of last month's failures, and can I prove the gain on the work I actually rely on?*

Workbench closes it with a loop that runs on the work itself:

**Capture.** Completed sessions are read from the agent's session store through a pluggable SessionSource adapter and split into discrete task units, each carrying the model, profile, and config_hash that produced it.

**Curate.** Only tasks with an objective, checkable outcome are candidates for promotion. Assertions are generated from the outcome contract — "what would the user check to confirm this is done" — never from any model's solution path, and an anti-circularity gate rejects assertions that reference implementation steps. Tasks whose outcome is contextual or fuzzy (most refactors, judgment calls, exploratory work) are explicitly Tier B: never scored pass/fail, never in the grid, but eligible to become harness evidence when there is behavioral proof of failure.

**Verify.** A candidate task enters the benchmark pool only after passing **self-replay**: its pinned environment (git SHA + lockfile, fixture DB, or container) is restored and the *original* model and config re-run it; the task qualifies only if the original reproduces its own outcome in at least 2 of 3 runs. One gate eliminates broken pins and flaky tasks together, and the three runs seed the task's baseline for free. Tasks that can't be pinned — live services, external APIs, ongoing churn — are Tier B by definition. Pinned tasks age: each records its pin date, retires when its target files no longer exist at HEAD or after a configurable age cap, and the dashboard shows the pool's age distribution so nobody routes next year's models on last year's codebase.

**Grid.** Verified tasks run through the model × config matrix as a paired experiment — every model sees the same task at the same pinned state, k=3 runs per cell, outcomes paired on majority result. Paired analysis (McNemar on discordant pairs) resolves real differences with a fraction of the data independent sampling needs and eliminates task-mix confounding. config_hash isolation guarantees "the harness got better" is never confused with "we switched models." The grid runs as a scheduled overnight batch — real tasks cost real minutes and real cents to re-run, and the system budgets both explicitly rather than pretending re-runs are free.

**Improve.** This is the primary value branch. Every verified failure — Tier A grid failures, plus Tier B failures backed by behavioral evidence (the user retried, corrected, abandoned, or flagged the task) — is written to the harness EpisodeLog. Weak-judge-only "failures" are quarantined and cannot be cited by the proposer, preserving the Phantom Guardrail's evidentiary standard. The harness loop proposes edits grounded in these real episodes, lab-tests them against the verified task pool, and promotes winners through the evaluation-fairness gate at equal budget. Every accepted harness edit lands as a new config, and the grid measures its real-task lift with the model held constant.

**Route.** Routing is delivered in two honest stages. *Stage 1 (month one):* the pooled paired comparison across all verified tasks answers a single question with real statistical power — "what should my default model be?" *Stage 2 (volume-gated):* per-domain efficient frontiers unlock only when a domain accumulates enough discordant pairs to resolve a difference; until then the cell says "insufficient data to compare" and the synthetic grid carries fine-grained selection, with the real-task grid validating that synthetic winners hold on the real distribution. Any resolved recommendation is config-driven and applyable, not decorative.

**Export.** Every grid cycle can emit an anonymized, shareable report — "212 real tasks, 3 models, here is the frontier, here is the measured harness gain" — rendered as the same class of artifact as ObserveCo's drift charts. This is the branch that faces outward: the report is the proof object for external validity, the consulting engagements, and the growth loop. Workbench doesn't compete with the stranger-install critical path; it manufactures the evidence that path needs.

The result reads like this: "This month your agents completed 212 real tasks. Eleven verified bug-fix failures support a harness change (fuzzy filename search); the lab test shows a 12% lift on the verified pool and it passed the fairness gate at equal budget — applied as config v14. On the pooled paired grid, deepseek-v4-flash is your recommended default at one-quarter the cost of the alternative with no resolvable accuracy deficit; per-domain frontiers unlock at current volume in ~2 more months. Exportable report ready." Not a benchmark of invented tasks. A flywheel built from the work that matters.

---

## FAQ

**Q: How do you score a real task with no assertion?**
Two-tier honesty. Tier A (objective outcome, pinnable, self-replay-verified) gets outcome-contract assertions and is grid-eligible. Tier B is never scored pass/fail — it carries a weak judge note for discovery only and can become harness evidence solely with behavioral proof of failure. We never compare models on data we can't score reliably, and we never let the harness loop cite a failure nobody verifiably observed. A small honest grid beats a large noisy one; a small honest episode log beats a large hallucinated one.

**Q: Aren't the assertions circular — derived from one model's successful trajectory?**
The generator is given the user's original request and asked what the user would check to confirm completion — never what the model did. The anti-circularity gate rejects assertions referencing implementation steps, and because the gate is itself LLM-judged, it is audited: every gate decision records a rationale, and a rolling random sample (not just rejects) is human-spot-checked. Circularity leak is a pre-registered kill condition, below.

**Q: What happens when the repo moves and "fix the N+1" is already fixed?**
Self-replay is the answer, and it is a hard gate: no task enters the pool unless its pinned environment demonstrably reproduces the original outcome. Pinning means SHA + lockfile at minimum, container where needed — a SHA alone does not pin package registries or external services, which is exactly what self-replay catches. Unpinnable work is Tier B. Pinned work decays, so the pool has a retirement policy and a visible age distribution. We never re-run a task against a different world and call it the same task, and we never keep a fossil in the pool and call it representative.

**Q: One run per model per task — isn't a "discordant pair" just two coin flips?**
Yes, which is why there are no single-run cells. Every (task, model) cell is k=3 runs, paired on majority outcome. Nondeterminism is a measured property, not an ignored one: a task whose *original* config can't reproduce itself 2-of-3 never enters the pool, and per-cell run variance is reported alongside the pass result.

**Q: Can this actually resolve per-domain routing in 30 days?**
No, and the doc stops pretending. The arithmetic: ~150 sessions/month → ~25 verified tasks after the objective-outcome, pinnability, and self-replay gates → ~6 per domain → 1–2 discordant pairs per model comparison per domain. McNemar needs roughly 6+ directional discordant pairs. Per-domain routing therefore resolves in quarters. What *does* resolve in month one is the pooled comparison — one global default-model recommendation with real power. Routing v1 is that single decision; per-domain frontiers are a volume-gated v2 milestone. Any dashboard cell that can't resolve a difference says so; it is never drawn as a confident Pareto point.

**Q: What does re-running real tasks actually cost?**
More than pennies, and it's budgeted honestly. Real coding tasks re-run at roughly $0.10–$1.00 and 2–10 minutes each. A monthly cycle of ~25 tasks × 3 models × 3 runs is ~225 runs: tens of dollars and 10–30 hours of wall-clock. That is an overnight scheduled batch with an explicit spend cap and a queue, not a background trickle. Judge and curation costs remain small; grid compute is the real line item and it is displayed, not hidden.

**Q: What does a wrong model choice actually cost, then — why route at all?**
Dollar routing is near-zero at this volume. The real stakes: coverage (a model failing 30% on a task class makes you stop delegating the class), trust (failures on real work force re-checking, which is worse than no agent), and harness compounding (the dominant value — one accepted harness edit lifts every future task of its type). That is why the PR leads with the harness flywheel and treats routing as the accumulating dividend.

**Q: Isn't "glm wins refactors" the showcase example?**
It was, and it contradicted the doc's own gates — refactors are the least assertable category and are mostly Tier B unless a test suite is the outcome contract. The showcase examples are now bug-fix and feature tasks, where outcome contracts are real. Refactor evidence flows to the harness branch, where it belongs.

**Q: Is this the comfortable build or the important one?**
It is the important one only under two enforceable commitments. First, genericity is a design artifact, not a sentence: a one-page adapter interface — SessionSource, EnvPin, Runner — written before Slice 0, with Hermes as the first implementation. Every place the pipeline currently names a Hermes internal becomes an interface call. Second, the Export branch ships in v1, because an internal flywheel nobody outside can see does nothing for ObserveCo's actual bottleneck (external validation, stranger-installability). If either commitment slips, this is the comfortable build and should be treated as such.

**Q: Does this replace canary and the synthetic grid?**
It completes them. Canary remains the fast always-on regression tripwire; the synthetic grid remains the controlled lab with unlimited N for fine-grained isolation; Workbench's verified grid is the representative complement on real distribution. One schema, one judge chain. Verified tasks that later regress become canary candidates; synthetic-grid winners are validated against real distribution before being trusted. Three views, one quality platform.

---

## Architecture

```
capture ──► boundary ──► raw_task
                            │
                            ▼
              [CURATION — outcome gate + anti-circular]
                    │                     │
              Tier A candidate       Tier B (contextual/unpinnable)
                    │                     │
                    ▼                     ▼
            [SELF-REPLAY GATE]      behavioral-evidence filter
             pin + reproduce 2/3          │            │
                    │               verified fail   weak-judge only
                    ▼                     │            │
             verified_task                ▼            ▼
             (aged, retirable)       EpisodeLog    quarantine
                    │                     ▲         (uncitable)
                    ▼                     │
        [PAIRED GRID  k=3, overnight, budget-capped]
         model × config × task, config_hash isolation
                    │
        ┌───────────┼─────────────────────┐
        ▼           ▼                     ▼
  Tier A failures  [ROUTING]         [EXPORT]
   → EpisodeLog    v1: pooled        anonymized report:
        │          default model     frontier + harness gain
        ▼          v2: per-domain    (external proof object)
  [HARNESS LOOP]   (volume-gated)
  proposer → lab test on verified pool
  → fairness gate (equal budget) → new config
  → grid measures real-task lift (model held constant)
```

The two goals remain the two output branches — harness improvement (verified failures → gated change → measured lift, the compounding value) and model choice (paired grid → staged routing) — plus the third branch, Export, that connects the flywheel to ObserveCo's external critical path. All three consume the same verified-task grid. The grid is still the single engine; the self-replay gate is what makes its fuel trustworthy.

---

## Slices

**Slice 0 — verified curation, end to end.** Adapter interface written first (Hermes impl only). Backfill 30 days → outcome-gate + assertion generation → self-replay verification → first verified pool. Session-as-task; no boundary detector; no routing UI. *Proves:* real work can become reproducible, honestly scorable benchmark tasks. *Exit metric:* verified-pool size and gate pass-rates (see falsification #3).

**Slice 1 — paired grid + pooled routing.** Overnight batch, k=3, budget cap. Deliverable: the global default-model recommendation with paired analysis, and the first grid dashboard with age distribution and "insufficient data" honesty labels.

**Slice 2 — harness branch.** Tier A failures + evidenced Tier B failures → EpisodeLog; first proposer cycle through lab test and fairness gate; measure one accepted edit's real-task lift.

**Slice 3 — export.** Anonymized report generation; one published artifact.

Per-domain routing and the boundary detector are explicitly post-Slice-3, volume-gated.

---

## Falsification tests (pre-registered, and able to fire)

1. **Pool starvation (Slice 0, 30 days):** fewer than 15 verified tasks survive all gates from a 30-day backfill → the gates are too strict for this workload or the workload is too contextual; re-examine the outcome gate before building anything downstream.
2. **Circularity leak (Slice 0):** random audit of 20 auto-generated assertion sets finds >3 checking path rather than outcome → disable auto-promote, require manual assertion approval, retrain the generator prompt.
3. **Pin failure (Slice 0):** >30% of Tier A candidates fail self-replay → either pinning strategy is inadequate (escalate to containers) or the workload is flakier than assumed; grid results would be untrustworthy either way.
4. **Routing vacuity (Slice 1, 60 days):** the pooled comparison cannot resolve any model difference at k=3 across the full verified pool → the models are indistinguishable on this workload; retire the routing branch entirely and state so, keep harness + export.
5. **Harness sterility (Slice 2, 90 days):** zero proposed edits pass the fairness gate, or an accepted edit shows no measurable real-task lift on the next grid cycle → the primary value thesis is failing; stop and reassess before Slice 3.
6. **External irrelevance (Slice 3, 120 days):** the exported report, published once, generates zero inbound signal (stars, replies, install attempts) → Workbench is not serving the external-validation path and must justify itself on internal value alone under tests 4–5.

Note what changed: the old test #1 fired by design (per-domain resolution in 30 days was arithmetically impossible). These can genuinely fire against the build.

---

## Assumptions (v3)

1. The customer is the archetype "developer operating agents who wants to trust delegation," and this claim is *earned* by the adapter interface existing before Slice 0 — not asserted.
2. Harness compounding is the primary economic value; routing is a staged dividend (global default in month one, per-domain in quarters); export is the branch that serves ObserveCo's real critical path.
3. Self-replay verification and pool aging are hard gates, so the verified pool will be small — roughly 25 tasks/month at current volume — and that is the honest size.
4. k=3 paired runs at an explicit overnight budget (tens of dollars, tens of hours monthly) is the minimum credible measurement discipline, and the cost is worth stating on the dashboard rather than hiding.

Which of these is wrong is now answerable by the falsification table rather than by argument — which is the point.
