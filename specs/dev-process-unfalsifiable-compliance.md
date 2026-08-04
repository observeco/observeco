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

**Empty is a valid answer.** The key design point: it must be costless to report
and never treated as failure, or you restore the incentive that hid the defect.

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

**Definition of done:** the distinguishing test passes in CI *and* the value-unit
definition survived adversarial review. Not "the feature is built."

---

## 7. Audit trail

- `f81ff20` — Workbench verdict split: the first run of this loop. Found the
  copied-verdict defect; corrected scope (rename to `containment_verdict`,
  `trajectory_verdict=None`, quarantine rule); added `test_verdict_independence.py`.
- `4a35654` — audit brief at `specs/audits/workbench-verdict-split-audit-brief.md`.
- This document is the generalized process those commits tested.
