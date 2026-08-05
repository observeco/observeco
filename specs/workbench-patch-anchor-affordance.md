# Patch-anchor affordance — spec v0 (first harness edit candidate)

## The validated problem

23 sessions in the rejection pool showed `old_string` patch-anchor failures.
Two splits reduce the face-value count to an actionable 14:

| Split | Result |
|---|---|
| failures vs friction | 14 actionable (cost something), 5 self-correcting friction |
| sub-mechanism | ambiguous-only 5, notfound-only 4, both 5 |

**Two sub-mechanisms, opposite problems:**
- **Ambiguous** ("Found 2/8 matches, provide more context") — anchor too generic.
- **Not-found** ("Could not find a match" / "Did you mean one of these") — anchor too specific, or the agent patching stale file content.

One affordance may address both — or the fix for each makes the other worse. This
is why the proposal cites the split, not the whole cluster.

## What the affordance is NOT

A matcher-tolerance change (looser matching, substring fallback). That is the
equivalent of tuning the classifier: fewer visible errors, more silent wrong
edits. The goal is NOT to make the patch tool more forgiving.

## What it IS — a sanctioned path to the legitimate goal

The agent's goal is a correct, unique edit. The affordance gives it a reliable
path to that, as a WORKFLOW change, not a tolerance change.

**Primary shape — read-then-anchor flow:**
- Before patching, the agent reads the exact target region and anchors on a
  unique string actually present (not reconstructed from memory/stale content).
- This addresses **not-found** (stale anchor) directly.

**Secondary shape — uniqueness precheck that fails loudly:**
- On anchor failure, the tool returns the **candidate matches** and the region
  around them, so the agent can disambiguate rather than guess.
- This addresses **ambiguous** (too-generic anchor) — gives the agent the info
  to make the anchor unique.

**Not proposed:** any change that accepts a non-unique anchor silently.

## Lab-test design (registered BEFORE the spec, loop never run)

**The pinnability reality:** only ~3 of the 14 actionable sessions pin
(8 are `no_repo_write` rejects, 3 `no_action_verb`, 3 `cron_job_output`).
So the lab test CANNOT be "replay all 14 with/without the affordance."

**Contrastive-replay lab test:**
- Replay the ~3 pinnable sessions with and without the affordance (contrastive
  adjudication: which trajectory better satisfies the original request).
- Run the promoted pool (C1, C2-revised, 164758) as a **regression check** —
  the affordance must not regress the 3/3 passes.

**Exit metric:** the affordance must not degrade any promoted-pool pass AND
must show improvement on ≥1 pinnable patch-anchor session. Given n≈3 pinnable,
the bar is deliberately modest — the edit is a workflow affordance whose main
value is preventing the 14-session failure class, measured by the pinnable subset.

## The failure flag — still needed, orthogonal

This spec is for the backlog affordance. The prospective failure flag (reason
field, flagged-by-Sean vs inferred) feeds the EpisodeLog going forward. The
backlog affordance and the prospective flag are independent; the affordance is
higher-leverage now because it has 14-session support already on disk.

## Honest scope

14 actionable sessions, ~3 pinnable, two sub-mechanisms. This is a strong FIRST
harness edit — the branch has done what it was built to do (a real failure
class, measured, with a proposable fix) — but the lab test is contrastive on a
small pinnable subset, not a 14-session with/without. The claim is scoped to
"prevents the patch-anchor failure class," demonstrated on the pinnable subset
plus a regression check — not "improves all 14."
