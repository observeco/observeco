# Selection step — spec v0.1

**Status:** spec, first revision after adversarial review of v0.
**Correction absorbed:** the cross-check makes markers honest (non-circular) but not sufficient. A stub satisfying the marker passes the marker check and fails the task — the inflation sign, structurally blind to symbol-presence. Fix: marker **strength** field + tests-as-assertions-first.

## Value unit

A candidate draft the batch runner can consume after **N human edits, N stated per candidate** (1–2), and only the authored fields human. A draft is well-formed when derived fields are populated and authored fields are `null` or flagged `provisional`.

## Derived vs. authored split

| Field | Kind | Derivation | Failure mode |
|---|---|---|---|
| session_id / source / model | derived | session row | — |
| repo_root | derived | write-target rule | no write → reject, log "no_repo_write" |
| pin SHA | derived | start-timestamp `git log --until` | no SHA → reject, log "pin_unrecoverable" |
| budget | derived | original duration × 3, min 180s | — |
| rel_path (target file) | derived | most-frequent write target | no write → reject |
| objective / difficulty | derived | classifier | flagged `provisional` (hand-validated, not fixture-tested) |
| **assertion** | **tests-as-assertions-first** | test command + expected exit from trajectory | no test → fall back to subject-symbol |
| **task description** | **authored** | reconstructed standalone prompt | `null` if first message too noisy |

## The marker: honesty vs. sufficiency — two fields, not one

**Marker validity (provenance).** The subject-named cross-check — extract the symbol the task names, verify absent-at-pin and present-in-completion, reject any symbol not in the task text. This makes the marker non-circular (it encodes the outcome the task names, not one model's path). It survives the circularity test.

**Marker strength (evidence).** A marker can be honest and weak: `_semantic_similarity` present proves a symbol was added, not that the assertion works. A stub passes it. The check that catches this is the **discrimination gate** — a marker a weak baseline also satisfies routes the candidate to canary (regression sentinel), not the grid. So selection emits both:

- `marker`: the subject symbol or `null`
- `marker_strength`: `strong` (weak baseline fails it) | `weak` (weak baseline passes — routes to canary) | `stub-possible` (symbol-presence only, known hollow-pass risk)

**Tests-as-assertions-first.** When the session ran tests, prefer the test command + expected exit code over any symbol. A test command is a stronger contract than a symbol and is fully derivable from the trajectory. Ten of the 42 write-target sessions ran tests. Selection tries the test path first, falls back to subject-symbol, and records which was used.

This refines N: test-backed candidates may be **N=1 (description only)** — a real reduction, not a reframing.

## The cursor — with provenance and rejection log

The cursor persists with the selection run's provenance: which sessions were considered, which passed each gate, and the rejections with reasons. A screen that only emits its passes is unauditable. Decision log per session:

```
session X → rejected at write-target gate (no_repo_write)
session Y → rejected at objective gate (fuzzy)
session Z → passed all gates → candidate draft (assertion=tests, strength=strong)
```

Every archaeology in this thread was possible because the trajectory persisted; selection's decisions must persist the same way. "Why was session X never considered?" is answerable from the record.

## Prompt-fidelity attribution

**Prompt-fidelity is a selection concern, not a runner concern.** Selection produces the task description field — the same field whose reconstruction fidelity we flagged as an unexamined exclusion category (a dropped-context reconstruction indicts the reconstruction, not the model). The decision log must capture the **original first-user-message** alongside the authored description, so a later failure attributes correctly.

## The N, stated

- **Test-backed:** N = 1 (write description; assertion derived).
- **Subject-symbol, cross-check passes:** N = 1–2 (write description; confirm marker).
- **Fuzzy / marker null:** N = 2 (write description + marker).

The irreducible human surface is description authoring (and marker authoring where no test and no subject symbol exist). This is not a failure — it keeps markers as outcome contracts rather than extracted paths.

## Distinguishing test (fails the wrong implementation)

A schema test is worthless — well-formed JSON with plausible-but-wrong markers passes any schema check. The test needs:

- A **fixture** with a known-correct candidate (the validated `_semantic_similarity` candidate).
- Assert **derived fields match exactly** (SHA, rel_path, budget).
- Assert **non-derivable / unverifiable fields are `null`, not guessed** — a script filling marker with a plausible wrong value instead of `null` fails.
- Assert **the marker-strength field is present and honestly labeled** — a `weak` marker is not upgraded to `strong` by the emitter.

## Scheduling consequence

A pipeline with a human in the description-and-marker step is not schedulable end-to-end. Selection runs weekly, mines new sessions, queues candidate drafts for 1–2 field review. The cron question stays open until the human surface shrinks to zero — a product decision, not a scheduling one.

## What's NOT in this spec

- No automatic trigger. Selection produces drafts; a human confirms; then the batch runs.
- No marker auto-approval. The cross-check proposes; it doesn't certify. Certification stays human until the fixture test proves the proposal is always right.

## Falsification (named in-spec)

The fixture test decides whether the subject-symbol marker derivation survives contact. If it produces circular or stub-satisfiable markers on real sessions, fall back to `null` + human authoring — no redesign. The spec is written so the fallback is a parameter, not a rewrite.
