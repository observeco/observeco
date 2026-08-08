# Workbench — Strategic reframe: the workload is 40× larger than the funnel saw

**The finding that changes the plan.** The 98-session manual window was treated
as the workload. The full session history is **4,574 sessions in ~50 days
(~640/week)** — roughly forty times larger. Almost all of it is invisible to the
funnel for **one recordable reason**: a provenance gap, not a volume gap.

## The data

| Population | Sessions | Test-command | Fail-before/pass-after | Pinnable |
|---|---|---|---|---|
| 98-window (manual funnel) | 98 | 23 | 1 | 0 |
| **Full history** | **4,574** | **95** | **9** | **1** |

- 9 fail-before/pass-after sessions across the full history.
- **8 of the 9 are subagent sessions with `repo=NONE`** — unpinnable.
- The one pinnable is a TUI session with a recorded repo root.

## The coupling (the part that was missed)

Delegation grows volume, but the growth is **concentrated in the wrong shape**:
subagent sessions are high-volume and low-pinnability. As currently configured,
more delegation grows the *denominator* (more sessions) without growing the
*numerator* (pinnable candidates) — the same precision-vs-yield trap as the
funnel fixes.

**Delegation is only a path to v4 if capture lands first.** The two levers are
coupled: delegation produces pinnable candidates only when subagent spawn state
is recorded.

## The correction: 9/4,574 is a ceiling, not an estimate

Prospective capture records the SHA at spawn — but subagent sessions run in
**working copies**, which is exactly why they have `repo=NONE`. A recorded SHA
pins the *commit*; it does not pin uncommitted working-tree state. A subagent
operating mid-task in a dirty tree may be working against a state no SHA
describes. Self-replay adjudicates that: some fraction of newly-captured
subagent sessions will pin and reproduce, some will fail because the world at
spawn wasn't a commit. **Nobody knows that fraction.**

Honest range: somewhere between **1/4,574** and **9/4,574**.

## The plan (steers back toward v4)

1. **Item 2 becomes the critical path**, scoped specifically to **subagent spawn
   capture** — cwd, repo root, branch, SHA, **plus dirty-tree state at spawn**
   so self-replay failures are diagnosable rather than mysterious.
2. **First deliverable: measure the self-replay conversion rate** on captured
   subagent sessions *before projecting anything*. If it's 80%, the ~1-month
   number holds and v4 is genuinely back in view. If it's 20%, ~4 months and the
   coupling is weaker than it looks.
3. **Then project.** If conversion holds, delegation and capture compound: more
   delegation produces more pinnable candidates rather than more noise, and v4's
   arithmetic becomes reachable on the author's own workload within a year —
   rather than requiring other users.
4. **Item 4 urgency drops** relative to item 2. If the own-funnel can reach v4
   volume, "does anyone else's workload work" becomes a product-market-fit
   question rather than whether the thing can be measured at all.

## The assertion-vocabulary question returns

9 fail-before/pass-after in 4,574 is still a **0.2% rate at the pre-pinning
stage**. Capture fixes pinning; it does not change how rarely the agents do
red-to-green test work. If v4 needs hundreds of tasks, the assertion-vocabulary
question comes back — and it comes back with **forty times more sessions to
mine**, which is a much better position to ask it from.

## Defect log

1. The 98-session window was treated as the workload for several rounds; the
   full history (4,574) was not consulted until this analysis. The funnel
   numbers were correct for the window but misleading as a statement about the
   workload.
2. Subagent sessions record no spawn provenance (cwd/repo/branch/SHA) — the
   single recordable reason 8 of 9 fail-before/pass-after candidates are
   unpinnable. Item 2 fixes this.
3. The self-replay conversion rate on captured subagent sessions is unknown and
   must be measured before any v4 projection is trusted.
