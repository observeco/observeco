# Working Backwards — ObserveCo Workbench (v5)

**Status:** Rewritten from measurement, not hypothesis. Every number below is
either measured with its sample size attached, or marked `UNVERIFIED`.

**What changed from v4:** two pre-registered kill conditions fired. The grid
could not resolve model differences on this workload (test 4), and the harness
branch's first edit shipped with its efficacy unmeasured because the affected
population cannot be pinned (test 5, partial). v5 is the product those results
support.

---

## Press Release

**ObserveCo Workbench: Benchmarks Lie. Workbench Is The Discipline That Catches
Them — Built From The Work You Already Did.**

Workbench turns completed agent sessions into pinned, replayable tasks and runs
them under a gate stack that refuses to report a number it cannot stand behind.
It produces three things: regression sentinels that trip when your agent stack
degrades, a routing answer for the class of work it can measure, and verified
episodes of real failure that the harness loop can act on.

The pitch it no longer makes: a per-category model × task grid that tells you
which model to use for each kind of work. We built that, measured it, and it
did not survive contact with the workload. What we found instead is more useful
and considerably less comfortable.

**The finding that reshaped the product.** Three real tasks passed the full
gate stack and reached a clean k=3. Then the weak baseline ran: an 8B local
model passed all three, 3/3, identically to a frontier model. Reading the code
the 8B wrote confirmed real implementations, not stubs. The tasks were easy —
not because the markers were weak, but because the properties that make a task
benchmarkable (single artifact, well specified, pinnable, objective outcome)
correlate with the properties that make it easy. A selection screen optimised
for scoreability selects below the discrimination band.

That result answered the routing question anyway, by emptiness: for this class
of work, use the cheap model. Equal accuracy, lower cost, measured. A grid that
discriminates nothing is a Pareto statement — the cheap model is on the
frontier and nothing sits above it.

**What Workbench actually delivers:**

**Capture** — completed sessions are read passively from the session store and
split into task units carrying model, config, environment, and provenance. Zero
marginal cost; it runs on work you were doing anyway.

**Curate** — tasks with an objective outcome and a pinnable environment are
promoted. Assertions come from the outcome contract, never from a model's
solution path, and tests-as-assertions are preferred wherever a test exists.
Everything else is explicitly Tier B: never scored pass/fail, labelled
not-benchmarkable, routed to harness diagnostics.

**Verify** — a candidate enters the pool only after self-replay at its pinned
start state, and only after passing a discrimination check against a weak
baseline. Tasks the weak baseline also passes are not grid fuel — they are
**canary-grade regression sentinels**, which is a real product: if an 8B model
suddenly fails one, something in your stack broke.

**Hold the world still** — this is the differentiator, and it is the part
nobody else ships. Seventeen distinct ways the measurement environment lied
were found and closed during construction: a session row that reported the
wrong source, a replay agent that inherited the wrong working directory, a
containment gate auditing the wrong session's history, a missing field read as
a negative verdict, a false-positive rate that was entirely file-state drift.
Each is now an enforced gate or a recorded provenance field. A Workbench result
carries the evidence of its own trustworthiness, and when a run is
contaminated, the record says exactly how.

**Improve** — real failures become episodes in the harness log, keyed to the
blocking event rather than the session, and classified so that correctly-fired
safety rails are structurally non-citable. The harness loop proposes edits
grounded in observed failures and gates them before they ship.

**Route** — where evidence resolves, Workbench emits a coarse recommendation as
machine-readable capability metadata. Where it does not resolve, it says
"insufficient data to compare" and draws nothing.

**What a month looks like, measured:** 98 sessions over 31 days; 42 with a
write target; 29% objective enough to be candidates; 2 reviewable drafts after
manual triage of 8 emitted; 3 tasks through a clean k=3; ~20% of screened-out
sessions containing genuine agent struggle (hand-classified, n=20, CI 6–44%);
one shipped harness edit backed by 12 real failure sessions. Those are the
honest denominators. A reader who wants larger ones should know they came from
one workload, one month, one developer.

---

## FAQ

**Q: Why should I believe any number this produces?**
Because the number arrives with its provenance and the gates it passed. Seventeen
environment failures were found during construction, every one by reading the
trajectory rather than the summary row. In every case where summary and
trajectory disagreed, the trajectory was right — a disagreement-biased sample,
not a base rate, but the direction is unambiguous. Each failure is now a gate:
pin at session start, fresh worktree per trial, explicit working directory at
spawn, containment assertion per trial, replay session id captured and bound,
absence recorded as unmeasured rather than as failure. This is the product.

**Q: You built a grid and it found nothing. Why is that not a failure?**
Because "no measurable difference at equal task, equal state, three trials" is a
routing recommendation: use the cheap model. It cost a fraction of what a
per-category frontier would have cost and it answered the decision that was
actually pending. The failure would have been shipping a confident Pareto chart
drawn on intervals that overlap completely.

**Q: So the grid is dead?**
Demoted and gated, not dead. The screen that produced the non-discriminating
tasks only ever derived symbol markers. A test-backed marker ("this failing
test now passes") is equally gateable with no ceiling on difficulty, and that
path was never exercised. Registered condition: if a test-backed candidate pool
of five or more materialises and the weak baseline fails at least one, the grid
resumes. Otherwise it stays retired. `UNVERIFIED` until that mining run reports.

**Q: What is a canary-grade task worth, if a weak model passes it?**
It is a regression sentinel. A task an 8B reliably completes is a task whose
failure means something in the stack changed — a tool, a prompt, a config, a
model version. Cheap to run, unambiguous when it trips. The discrimination
check that disqualifies a task from the grid is the same check that qualifies
it as a sentinel; nothing is wasted, it is routed.

**Q: What does the harness branch actually produce?**
Verified episodes, and edits gated on them. First cycle, end to end: a failure
class mined from real sessions (agents failing to match patch anchors), reduced
from a face-value 23 sessions to 12 actionable after separating genuine failures
from self-correcting friction, split by sub-mechanism, counterfactually measured,
condemned by the fairness gate on a 79% false-positive rate, then saved on
appeal when the source showed that rate was entirely file-state drift, then
collapsed on contact with the existing tool from a new precheck mechanism to a
one-line error-message change. Shipped. Its efficacy is `UNVERIFIED` — the
affected population is non-pinnable, so the lab test was infeasible by design.

**Q: One error message, from all that?**
Yes, and the size is the claim. The same cycle prevented four builds: a
redundant precheck that already existed, a matcher-tolerance change that would
have traded loud failures for silent corruption, an abandonment on a drift
artifact, and replay infrastructure for a population that cannot pin. The
discipline that makes a benchmark trustworthy — checking what happened rather
than what was reported — is the same discipline that stops you building the
wrong thing.

**Q: Why not use SWE-bench?**
SWE-bench and its descendants mine public repositories, which buys contamination
(models train on the fix) and distribution mismatch (their issues are not your
work). Workbench is the private, personal instantiation of the same construction
methodology — pin at base commit, require fail-before/pass-after, verify the
environment reproduces. We re-derived those from first principles before finding
the lineage, which is the cheapest external validation available. The novelty is
the data source and the automation of curation. The honest caveat their work
does not have to make: our funnel is thin, and we publish the denominators.

**Q: Does this replace tracing or online evaluation?**
No. Tracing shows what happened. Online eval scores it with generic rubrics.
Workbench re-runs it at a pinned state under gates that make the re-run
comparable to the original. Different question, different instrument.

**Q: What is this worth to someone who is not you?**
Unknown, and that is the next thing to find out. Every number here is one
workload. The gate stack is the portable part — it is generic by construction
(SessionSource, EnvPin, Runner adapters, Hermes as the first implementation) and
the failure taxonomy will apply to anyone replaying agent sessions. The
publishable claim is the method; the numbers are a case study with its
instruments attached.

---

## What v5 removes from v4

- **Per-category efficient frontiers.** Not producible at this volume on this
  workload. Replaced by a single coarse recommendation and an explicit
  "insufficient data" state.
- **The 212-task illustrative dashboard.** Replaced by measured denominators.
- **Measured harness lift as a headline.** Replaced by the shipped edit with its
  efficacy marked `UNVERIFIED` and the reason stated.
- **The grid as the product.** The grid is now a gated hypothesis. The gate
  stack is the product.

## What v5 keeps

- Passive capture at zero marginal cost.
- Two-tier curation with tests-as-assertions preferred.
- Pin-and-verify with self-replay and discrimination checks.
- The full environment gate stack — the seventeen closed failures as enforced
  mechanism.
- The harness branch, fed by Tier-B episodes rather than by a grid.
- The autonomy ladder: propose → lab test → shadow → apply, with graduation
  pre-registered.

## Pre-registered conditions (v5)

1. **Grid resumption:** ≥5 test-backed candidates mined AND weak baseline fails
   ≥1 → grid section resumes. Otherwise retired. *Pending mining run.*
2. **Harness viability:** a second proposable failure cluster with ≥10 actionable
   sessions within 90 days, or the harness branch is a one-shot rather than a
   loop.
3. **External validity:** one person other than the author runs Workbench on
   their own sessions and reports a funnel. Until then every number in this
   document is n=1.
4. **Sentinel value:** a canary-grade task trips on a real stack change within
   180 days, or the regression-sentinel claim is theoretical.

## Assumptions in this rewrite

1. The gate stack, not the grid, is the differentiated product — because it is
   the part no competitor ships and the part with seventeen documented reasons
   to exist.
2. Canary-grade output is a real deliverable rather than a consolation prize.
3. The grid deserves demotion-and-gating rather than retirement, because
   retiring wrongly is expensive and reversible only at great cost while keeping
   a gated hypothesis costs a paragraph.
4. External validity is now the binding constraint, ahead of any further
   measurement on this workload.

Which of these is wrong?
