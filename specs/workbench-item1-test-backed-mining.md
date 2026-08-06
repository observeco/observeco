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

**Where the losses actually fell (the corrected binding constraint):**

| Stage | Loss | Cumulative left |
|---|---|---|
| 98 sessions | — | 98 |
| Ran a test | 75 lost | 23 |
| Recoverable command + target | **19 lost** | 4 |
| Fail-before / pass-after | **3 lost** | 1 |
| Pin cleanly | **1 lost** | 0 |

The pin killed only the **last** candidate. The binding constraint on the
test-backed path is **not the missing SHA** — it is that this workload rarely
produces a recoverable, targeted test invocation with a fail-then-pass
transition. 19 of 23 were gone before pinning was even consulted, 3 more at
fail-before/pass-after.

This corrects the earlier framing that item 2 (prospective capture) is
"load-bearing for item 1's question." Capture fixes the last gate (pinning)
but does nothing about the 19 lost at recoverable-test-command. Even with
perfect capture, this same 98-session window yields **one** candidate — and one
candidate cannot answer the discrimination question. At the observed 1-in-98
rate, five test-backed candidates take roughly a year to accumulate. **That is
a path to resolving the confound in 2027, not a near-term unlock.**

So item 2 should be built as **provenance hygiene** — it's cheap, it compounds,
and every reconstruction-archeology session in this thread argues for it — but
not as the unlock for the grid. If the doc records it as "the binding
constraint on the test-backed path," a future reader will expect the grid to
resume once capture lands, and it won't.

**A sharper v5 finding:** the test-backed question is unanswerable
retroactively, yes. But 23 sessions ran tests and only 4 produced a recoverable,
targeted invocation — that is evidence about the workload independent of any
pin: **this workload rarely works in a test-first loop where a specific test
transitions red-to-green.** That's a real property, it explains why the
assertion-vocabulary lever didn't open, and it belongs in the v5 grid-resumption
condition. The condition should read: *resumes if five test-backed candidates
accumulate under prospective capture* — with the note that at the observed rate
that's a year away, so the grid stays retired in practice.

**Defect log:** (1) No `git_sha` column exists in Hermes sessions — pin state is
never captured (item 2 fixes). (2) The decision log stores truncated session
ids (e.g. `_90ac` vs `_90ac4ba0`), risking prefix-collision; my first scan
mis-joined on them. (3) The migration candidate's fail-before/pass-after is real
but unpinnable — recorded as a candidate for a prospective re-run under capture.
(4) The funnel's dominant loss — no recoverable targeted test invocation — is a
workload property, not a tooling gap, and no capture change addresses it.
