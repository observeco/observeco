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

## Measurement update — verdict RETRACTED and reversed, then SOURCE-VERIFIED

An earlier counterfactual reported a 79% false-fire rate on successful patches,
which would have made the affordance net-negative. That conclusion was WRONG —
it was a current-state artifact, not a real rate.

**Why (structural):** the patch tool errors on non-unique anchors (only 10/1028
successful patches used `replace_all`). A successful non-replace_all patch
therefore REQUIRED a unique anchor at patch time.

**Why (source-verified):** read `fuzzy_match.py:173-179` — the
`if len(matches) > 1 and not replace_all:` error fires for EVERY strategy in the
9-match chain (exact, line_trimmed, ..., context_aware). No first-match-wins, no
fuzzy-ambiguity fallback. `_SIMILARITY_STRATEGIES` (block_anchor, context_aware)
even REFUSE `replace_all` on approximate matches. `replace_all=True` is the ONLY
exception, and it's excluded.

**Measured (actual tool at current state, 995 successful non-replace_all
patches):** 357 still match (precheck would NOT fire), 638 fail now (all drift —
file changed since), 23 no-file. The 638 are drift by the confirmed invariant.

**Catch rate:** drift can only REDUCE a would-fire on a genuinely-failed anchor.
So the 98% actionable catch rate is a LOWER BOUND; true catch is ≥98%.

## The three-row table (the honest measurement)

| Row | Rate | Basis |
|---|---|---|
| Catches the failure class | **≥98%** | lower bound (drift only reduces catch) |
| Doesn't interrupt working patches | **~0%** | source-verified uniqueness enforcement |
| Fires on self-correcting cases | **12/12** | real, separate — loud fire where tool recovers anyway (a small win, stated not absorbed) |

**Verdict:** the affordance is **viable** — it catches ≥98% of the failure
class, interrupts ~0% of working patches, and fires loudly where the tool would
have recovered anyway. Proceed with the specced read-then-anchor flow.

## Lesson (generalized)

"The ratio is robust" was a claim about confound behavior made without checking.
Confounds are asymmetric by default; proportional inflation is the special case.
The named class — *an instrument answering a different question than it appears
to* — now has three instances: wrong entity (containment identity), wrong state
(current-vs-pinned drift), wrong population (two-baseline overreach).
