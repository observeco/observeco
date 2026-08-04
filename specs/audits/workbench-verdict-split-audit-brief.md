# Workbench Verdict-Split Audit Brief

**Author:** Sean / ObserveCo accelerator
**Date:** 2026-08-04
**Commits:** `077a3a0` (harness tab removal), `f81ff20` (workbench verdict split)
**Status:** Self-contained — no prior session context required.

This brief documents two changes made under a process-discipline exercise. It is
written for an independent reviewer who has never seen the codebase. Every claim
below is verifiable from the repo at commit `f81ff20`.

---

## 1. The finding

`scripts/workbench/batch_runner.py` is the instrument behind `specs/workbench-v4.md`,
a personal SWE-bench benchmark. The document's load-bearing claim is:

> "nine environment failures were found, and in every case where summary and
> trajectory disagreed, the trajectory was right."

The document's **pending** list promised to measure the summary-vs-trajectory
disagreement base rate, logging "a summary-vs-trajectory verdict field for both
agreements and disagreements so the base rate becomes measured rather than assumed."

**The defect:** the instrument did not produce a trajectory verdict. In
`batch_runner.py` the scoring block assigned *both* verdicts to the same
deterministic boolean:

```python
passed = target_present(path, candidate["marker"], candidate["rel"])
entry["summary_verdict"] = "pass" if passed else "fail"
entry["trajectory_verdict"] = "pass" if passed else "fail"
```

Both fields were the marker check, under two names. A disagreement between them
was **impossible to represent**, so the promised base rate could be *reported*
but never *measured*. This is the same class of defect the document's own spine
warns against: a value that looks measured but is not.

**The fix was corrected during review.** A naive fix — computing a "trajectory
verdict" deterministically from tool-call paths and shipping it under that name —
would have been a *mislabelled* value: a containment/provenance check renamed to
`trajectory_verdict` while the doc claims trajectory-beats-summary. That would
have preserved the lie in a better disguise. The corrected design instead:

- **Renamed** the deterministic provenance field to `containment_verdict` (it is
  not trajectory-truth).
- **Set `trajectory_verdict` to `None`** — never a copy of `summary_verdict`. An
  honest "not measured" is preferred over a populated field that says the wrong thing.
- **Named the real prerequisite** for measuring the base rate: an LLM-judge
  trajectory pass over transcripts (token cost stated).
- **Added a quarantine rule** (`needs_review`): a containment violation excludes
  the candidate from the grid until an adjudicator clears it.

## 2. The corrected scope

| Field | Source | Contract |
|---|---|---|
| `summary_verdict` | marker check | what a naive summary reports |
| `containment_verdict` | transcript provenance (confinement + leakage) | catches inflation, confirms confinement — **not** trajectory-truth |
| `trajectory_verdict` | **None** (deferred) | never a copy of `summary_verdict`; requires LLM-judge pass |
| `needs_review` | `containment["violated"]` | True ⇒ candidate quarantined from grid until adjudicated |

## 3. How to verify

```bash
# The corrected instrument + regression tests
uv run pytest scripts/workbench/ -v
# → 10 passed (4 new verdict-split tests + 6 existing containment tests)

# The specific bug cannot return: the only trajectory_verdict ASSIGNMENT is None.
grep -n 'entry\["trajectory_verdict"\]' scripts/workbench/batch_runner.py
# → entry["trajectory_verdict"] = None   (the only assignment; comment mentions remain)
```

The regression test `scripts/workbench/test_verdict_independence.py` asserts
structurally that `trajectory_verdict` is never derived from the marker boolean.
This is the promote-to-gate move: the bug that produced the false claim is now
impossible to reintroduce without failing CI.

## 4. The process lesson being tested

This was the first end-to-end run of a proposed development loop:

1. **Name the value unit** — what the artifact must actually produce (an honest,
   independently-computable trajectory verdict, not a renamed copy).
2. **Write the acceptance test first** — the test that fails on the current code
   and passes only once the value unit is real.
3. **Adversarially review the value-unit definition, not just the test** — the
   naive fix (deterministic "trajectory_verdict") was rejected because it would
   have smuggled the same lie back in under a better name. A test locks in
   whatever the value unit says; a wrong value unit yields confidently-green
   wrongness. So the value-unit definition needs adversarial review as its own gate.
4. **Correct the document to match the instrument** — the pending list now states
   the base rate is *not yet measurable* and names the LLM-judge pass as its
   prerequisite. The document has zero claims its instrument cannot back.

The point of showing this to an auditor is not a green test suite. It is that the
team **found its headline claim uninstrumented, and rather than fake the missing
field, marked it unmeasured and named the cost of measuring it.** A reviewer
reading that learns more about the discipline than one reading passing tests.

## 5. Related change (context, lower priority)

`077a3a0` removed the harness-optimizer **dashboard tab** (route, nav, content,
JS) — the only dashboard surface with zero manual steering, which produced nine
runs of nothing (every run gated-inert by preconditions). The backend CLI
(`observeco harness optimize`) was left intact.

**Causal-boundary correction:** this removal is *not* cited as "a feature the
process couldn't deliver." The process postdates the harness tab by a wide
margin — the tab produced nine inert runs on its own, before any of this. The
process did **not** surface it. It was removed during the same exercise, but the
removal decision and the process are coincident, not causal. An auditor should
read it as: a long-inert surface was deleted while the process was being defined
alongside it. The verdict-split finding in §1–§3 is the process's actual product.

---

### Assumptions an auditor should check

- The base-rate claim is still **historically true** (nine investigated failures,
  trajectory right where they disagreed — a disagreement-biased sample). The fix
  does not dispute history; it stops the instrument from *implying* a base rate
  it cannot measure.
- `trajectory_verdict = None` is a deliberate scope decision. If the auditor
  believes an LLM-judge trajectory pass is cheap enough to ship now, that is the
  natural next increment — but it must be a real transcript adjudication, not a
  deterministic rename.
