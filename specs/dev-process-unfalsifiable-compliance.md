# Development Process — Unfalsifiable Compliance, and the Mechanisms Against It

**Author:** Sean / ObserveCo accelerator
**Date:** 2026-08-04
**Status:** Live — the process this repository develops by.
**Source of truth for:** value-unit contracts, distinguishing tests, defect logs, claim-to-evidence binding.

---

## 0. The diagnosis this process exists to prevent

Development output does not fail by *drifting* from a good state. It fails by
being **never wired** — the agent is asked for an artifact, produces one with
the right name and type, and the plausible-shaped output satisfies every check
that exists while the substance underneath is absent. This is **unfalsifiable
compliance**: a spec that names an artifact but not an observable it must
produce invites the cheapest thing that looks like compliance.

Two concrete instances in this repository:
- The environment lied nine times during Workbench construction.
- `batch_runner.py` assigned `trajectory_verdict = "pass" if passed else "fail"`
  — the same boolean as `summary_verdict`, under a second name. The promised
  "summary-vs-trajectory base rate" could be reported, never measured.

Both are the same failure: **a surface that reports success while the substance
underneath is absent**, detectable only by looking at what actually happened
rather than what was reported.

**Category correction (2026-08-04):** the nine environment lies are not all
instances of unfalsifiable compliance. Some were — the model-resolution override
and the copied summary verdict reported false success. Others (shared worktree,
post-fix pin) were plain environment defects: the environment was wrong, but it
was not a surface claiming to have succeeded. The correct relationship: the nine
lies are instances of **the environment lying to a measurement**; unfalsifiable
compliance is the **artifact-level cousin**. Same family, not one category. The
unifying thread is that both are only detectable by inspecting what happened
rather than what was reported — but the mechanism (environment defect vs. agent
producing a plausible-shaped artifact) differs, and the fixes differ accordingly.

The rule: **any surface that reports success must carry the observable that
would be different if it were false.** If you cannot name that observable, the
claim is not buildable yet.

---

## 1. The value unit — what a spec must name before build

A spec must state, for each claim, the **value unit**: what the user/artifact
actually produces, as a sentence and an observable. For UI: "the user clicks X
and decides Y." For an instrument: "the artifact emits two *independent*
verdicts." For a metric: the exact sentence it must render per state.

Two forms, one artifact:

1. **The sentence** the feature must produce (verdict line, threshold, ordering,
   suppression, unknown-handling).
2. **The fixture→output table** — for each state (N=0, N=1, N=max; each
   pillar-state combination), the exact expected output. The empty cells in this
   table are the unbuilt states.

The fixture→output table is simultaneously the **acceptance test** (fixture in,
expected output out) and the **copy-as-function spec**. They collapse into one
artifact, so fidelity stops being the unenforceable part of the plan.

**Empty states must be designed, not improvised.** A mockup drawn only at N=max
over-promises; a service written only for N=0 renders "N/A" shrugs. Both are
refusals to say anything. Specify the sentence for every state, including the
honest-empty ones.

---

## 2. Mechanism 1 — distinguishing tests (write first, fail on the wrong impl)

For each claim, the test must fail against the **wrong implementation**, not
just against no implementation. A test both the correct and incorrect
implementation pass carries zero information.

The test that would have caught the copied verdict is the one asserting the two
fields **can differ** — the reachability of the disagree-row.

Spec-writing rule: **for each claim, write the observation that would be
different if the claim were false.** If you can't name one, the claim isn't
buildable yet — mark it unmeasured rather than fake it.

When the honest answer is "not measurable with the current instrument," the
correct resolution is **null-not-faked**: an explicit `None`/"not measured" is
worth more than a populated field that says the wrong thing. A value-unit
definition that cannot be distinguished from its false version must be marked
`UNVERIFIED`, not populated.

---

## 3. Mechanism 2 — the defect log (report what you noticed but didn't fix)

Every task ships a **structured second output** alongside the work: the defect log.
Standing instruction: record anything a reviewer would want to know, including —
- things you chose not to fix,
- shortcuts you took,
- assumptions you couldn't verify,
- places where you produced something plausible without confirming it's correct.

**Binding (this mechanism must not be unfalsifiably compliant — apply §4 to §3):**

- **Location:** one file per task, `defects.jsonl`, placed in the same directory as
  the task's run record or diff artifact. One JSON object per line:
  `{"task": "<id>", "finding": "...", "why_not_fixed": "...", "ts": "<iso>"}`.
- **Empty is a real, distinguishable value:** a task with no observations MUST
  write the single line `{"task": "<id>", "finding": "none"}`. The literal string
  `none` makes *absence of the file* (task skipped the log) distinguishable from
  *an empty log* (task checked, found nothing). A missing file is a violation;
  a `"finding": "none"` line is not.
- **The gate is greppable:** `grep -rL '"finding": "none"' --include=defects.jsonl .`
  or a CI check that fails when any completed task ships no `defects.jsonl`.
  Absence fails loudly, so a task can't silently skip it the way it silently
  skipped the verdict.
- **Status:** this mechanism was **UNVERIFIED** at binding time — the verdict-split
  commit exercised mechanisms 1, 2's value-unit gate, and 4 but did not ship a
  defect log. **Verified 2026-08-04:** `specs/audits/defects.jsonl` is the first
  real task artifact produced under this binding — five findings from the
  process-doc review, each with `why_not_fixed` and a real timestamp, written
  under the rule it exercises. The mechanism is no longer aspiration; it has a
  shipped example.

The key design point: it must be costless to report and never treated as failure,
or you restore the incentive that hid the defect.

In the Workbench case, the honest entry would have been: *"trajectory_verdict is
assigned the same value as summary_verdict; I had no independent trajectory
computation available."* The agent could have written that sentence while
writing the line.

The defect log is a first-class output, not a confession. It is what converts
"the agent noticed an adjacent problem and dropped it" into a recorded signal.

---

## 4. Mechanism 3 — claim-to-evidence binding (structural, greppable)

Every load-bearing claim carries, inline, the artifact that backs it:
- a test name,
- a run-record ID,
- or the literal token `UNVERIFIED`.

Then a claim without evidence is visible as a grep (`grep UNVERIFIED specs/`),
not as something you must remember to notice. This is the same move as the run
record: **shrink the set of things that can be silently forgotten.**

Also: a **verification-provenance field** per artifact — what was actually run
to check it (compile? lint? a real test? nothing?). "Verified" has meant four
different things; the difference between them is where defects live.

---

## 4.5 Mechanism 3.5 — referential integrity, in every direction

Four confirmed defects this session share one shape: **two halves that each
pass their own check but were never checked against each other.**

- templates emit classes → stylesheet defines no rules for them (orphaned CSS)
- CSS vars referenced → never defined in `:root` (the latent `--fg-3` bug, 46 refs)
- fetch/htmx calls a route → no route registered (dead buttons)
- a POST route is registered → nothing calls it (built, never surfaced)

The mechanical guard is a **set-difference audit**, one direction per reference
class, run as a gate: `scripts/audit_referential_integrity.py` (ObserveCo-local;
the *idea* — every reference resolves to a definition, in both directions — is
portable and belongs in a skill, not the repo).

**Deletion safety — the rule that governs every fix this tool drives.** A static
analyzer reports "unreferenced class." You delete it. But a class that a *live
JS selector* depends on (`querySelectorAll('.onboarding-panel')`) looks identical
to a dead one from the analyzer's output alone. Deleting it silently breaks the
UI — visible to nobody, caught by nothing, discovered weeks later.

**So: never delete on the word of a static analyzer. Before removing any
reported-orphaned symbol, grep the whole codebase for the string in JS,
templates, and routes.** Deletion driven by static analysis requires a
cross-referencing grep first. This session's near-miss (`onboarding-panel`, a
live selector hook misclassified as vestigial) is the cautionary instance.

**Scope discipline — every scope fix needs a positive test.** Teaching the audit
about a new definition site (inline `<style>`) makes it report *less*. That's
correct only when verified against real definition sites — otherwise you converge
on green by teaching the tool to look away, rebuilding `|| echo` with better
manners. After any scope widening, plant a genuinely-undefined reference and
confirm the audit still fires on it (`tests/test_audit_scope.py`).

**Green is the only state that carries information cheaply enough to be a floor.**
A gate that ships red is a gate whose normal state is red, and a red-normal gate
trains everyone to read past it. `make verify` must be green before it becomes a
definition of done.

---

## 5. The value-unit gate — the one thing mechanisms cannot catch

Mechanisms catch implementation drift from a **correct** spec. Nothing catches a
**wrong spec** except a second mind reading it. A wrong value-unit definition
produces confidently-green wrongness: the tests lock in whatever the value unit
says.

Therefore the value unit itself gets **adversarial review as its own gate**,
before any test is written against it. The agent that wrote the code cannot
reliably audit it — it audits against the same understanding that produced the
bug. A **fresh instance** given only the spec and the diff, asked "where does
this fail to do what the spec claims," catches what the author cannot.

**Binding (this gate must not be unfalsifiably compliant):**
- The reviewer receives **only** the spec + the diff. No session context, no
  prior review, no author commentary. Same constraint as the Workbench
  containment gate: a reviewer who sees the author's reasoning audits against
  the same understanding that produced the bug.
- The reviewer's verdict is **recorded**, not conversational: a one-line
  verdict appended to the spec — `ADVERSARIAL REVIEW PASSED` / `FAILED: <reason>`
  — with the reviewer instance noted. An unmarked value unit is `UNVERIFIED`.
- The gate fails closed: no value unit ships without a recorded adversarial
  verdict, and the verdict must be a pass.

This is the mechanizable version of what this conversation did manually. The
part you cannot fully automate is the second mind reading the spec — you can
only *schedule* it.

---

## 6. The loop, condensed

1. Name the value unit (sentence + fixture→output table, all states).
2. Adversarially review the value-unit definition before writing any test.
3. Write the distinguishing test first — it fails against the wrong impl.
4. Build to make it pass; ship the defect log alongside.
5. Bind every claim to its evidence (test name / run ID / `UNVERIFIED`).
6. Correct the document to match the instrument — zero claims the artifact can't back.
7. **Exit** (see below) — the loop must be able to terminate.

**Exit rule (this thread's actual lesson):** adversarial review is excellent at
finding defects and terrible at stopping. Without a termination rule, a process
doc that can't finish will eat the schedule it was written to protect. Two
declarations, made **before** review begins:
- **Round budget:** the number of review→fix rounds a value unit may consume.
- **Termination condition:** if a round's finding does not change what gets
  built or what gets run next, **stop** — record the finding as resolved-or-
  acknowledged, ship what exists, and move on. A finding that merely restates
  the prior round's objection, or that a reviewer "would also have noted," is
  not a change and does not extend the budget.

The working rule: a process that can't terminate protects nothing. Budget and
termination are declared up front so review stops when it stops being useful,
not when someone gets tired.

**Definition of done:** the distinguishing test passes in CI *and* the value-unit
definition survived adversarial review *and* the round budget was not exceeded
(via termination, not abandonment). Not "the feature is built."

---

## 7. Audit trail

- `f81ff20` — Workbench verdict split: the first run of this loop. Found the
  copied-verdict defect; corrected scope (rename to `containment_verdict`,
  `trajectory_verdict=None`, quarantine rule); added `test_verdict_independence.py`.
- `4a35654` — audit brief at `specs/audits/workbench-verdict-split-audit-brief.md`.
- `5a86329` — this process doc.
- This commit — adversarial review of this doc found five defects (mechanism 2
  unbounded; unbound causal claim in the brief; nine-lies category error; value-unit
  gate unbinding; no exit rule). All five fixed. Mechanism 2 verified by its own
  shipped `specs/audits/defects.jsonl`. This is the loop's step 2/7 applied to the
  process itself.
- This document is the generalized process those commits tested.
