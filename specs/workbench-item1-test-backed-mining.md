# Item 1 — Test-backed candidates: mining report

**Verdict against pre-registered criteria:** `<2 candidates survive mining` — the
third reading. Test-backed path is **unavailable in this history**. Stop, report
the breakdown.

## The numbers

| Criterion | Count |
|---|---|
| Sessions inspected | 98 (the funnel pool) |
| Sessions running a test command | 23 |
| With a recoverable test command + target | 4 |
| Satisfying fail-before / pass-after | **1** |
| Pinning cleanly | **0** |
| Surviving candidates | **0** |

## The decisive constraint: provenance, not marker vocabulary

The confound item 1 was designed to test — *is the benchmarkable-≠-easy
correlation specific to symbol markers, or structural?* — **cannot be tested on
this backlog**, because nothing in it can be pinned.

- **No session recorded a start SHA.** There is no `git_sha` column in the
  sessions table at all. 97 of 98 sessions have `git_repo_root = None`; the one
  exception (`20260704_122408_0bcdb6`) records a repo root and branch but no
  SHA, and has **zero fail-before evidence** (0 FAILED markers, pass-only).
- The single genuine test-backed candidate — `20260802_112712_90ac4ba0`, the
  migration-infra session — shows **real fail-before/pass-after in-trajectory**
  (a `TestDowngradeGuard` assert failure at one point, then 24 tests passing;
  3 FAILED + 8 pass markers). But it has no recorded `git_repo_root` and no SHA.
  Pinning it requires reconstructing which commit was HEAD when it ran — an
  inference, which the standing constraint explicitly forbids ("never infer
  what you can declare").

So the honest reading is **not** "test-backed markers don't discriminate."
It is: **the backlog cannot pin, so the test-backed question is unanswerable
retroactively.** The discrimination confound item 1 was built to resolve is
still open — it just can't be resolved on this history.

## Exclusion reasons by category

- **No repo write / no pin** (the bulk): sessions that never touched a tracked
  repo or never recorded their state. Same population that produced the 8→2
  funnel.
- **No test invocation:** 75 of 98 sessions never ran a test command.
- **Test run but no fail-before:** sessions that ran tests only to verify
  already-passing work, or where the failing assertion isn't recoverable as a
  discrete "this test fails at start, passes at end."
- **Test run, fail-before exists, but no pin:** the migration candidate — the
  closest miss. Everything a test-backed marker needs is in its trajectory
  except the one thing the constraint refuses to fabricate: the start SHA.

## What this means

The item-1 decision rule says: with <2 candidates, "neither reading applies.
Test-backed path unavailable in this history. Report the breakdown and stop."
That is the outcome. I am not padding the pool — zero candidates survive.

The constructive finding: **item 2 (prospective capture) is now load-bearing
for item 1's question, not just a compounding improvement.** The only way to
ever test whether test-backed markers escape the benchmarkable-≠-easy
correlation is to record pin state *at the time sessions happen*. The migration
candidate proves the evidence is out there; the missing SHA is what killed it.
This is the same lesson as the seventeen bugs: the measurement failed at the
provenance layer, not the analysis layer.

**Defect log:** (1) No `git_sha` column exists in Hermes sessions — pin state is
never captured. (2) The decision log stores truncated session ids (e.g. `_90ac`
vs `_90ac4ba0`), which risk prefix-collision; my first scan mis-joined on them.
(3) The migration candidate's fail-before/pass-after is real but unpinnable —
recorded for when provenance capture lands, as a strong candidate for a
prospective re-run.
