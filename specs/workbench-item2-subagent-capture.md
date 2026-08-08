# Workbench — Item 2: Subagent spawn capture (critical path)

**Why this is the critical path.** The full history is 4,574 sessions (~640/wk),
40× the 98-session window. 9 fail-before/pass-after candidates; 8 are subagent
sessions with `repo=NONE` — unpinnable. The workload is invisible to the funnel
for one recordable reason: a provenance gap, not a volume gap. Capture converts
the subagent volume into pinnable candidates; delegation and capture compound
only if the conversion rate holds.

## Scope: subagent spawn capture

At subagent spawn, record:

1. **cwd** — the working directory the subagent starts in.
2. **git_repo_root** — the repo root (if any).
3. **git_branch** — the branch checked out.
4. **git_sha** — the commit at spawn. **NEW COLUMN** (does not exist).
5. **dirty-tree state as CONTENT, not a flag** — the uncommitted diff against
   HEAD at spawn. A boolean "was dirty" tells you why a replay failed but not
   how to fix it. Capturing the diff means a replay can reconstruct the actual
   working state: "pinnable via SHA plus patch." This is likely the single field
   that determines whether conversion is 20% or 80%. Cheap at spawn, impossible
   afterward.
6. **parent_session_id** — the orchestrator's session id. 8 of 9 candidates are
   subagents; when a replay behaves differently, the orchestrator's context is
   what you'll want. Same reasoning as replay-session-id binding: record the
   relationship at the moment it's known. (Currently only 90/159 subagent
   sessions have it; the 8 candidates all have `parent=NONE`.)

## First deliverable: measure the self-replay conversion rate

**Before projecting anything**, run a real self-replay on captured subagent
sessions:

- **Original model and config** — not a substitute.
- **Fresh worktree** per trial.
- **k=3 with the ≥2/3 threshold** — the standard gate.
- **The gap that matters:** "the pin resolves" ≠ "the original outcome
  reproduces." The conversion measurement must be a real self-replay run, not a
  check that the SHA restores cleanly. This is where three previous projections
  in this project went wrong.

**Honest range:** 9/4,574 is a ceiling, not an estimate. A recorded SHA pins the
commit, not uncommitted working-tree state. The real conversion rate is between
1/4,574 and 9/4,574. Measure it, then project:
- 80% conversion → ~1 month to 5 candidates → v4 back in view.
- 20% conversion → ~4 months → coupling weaker than it looks.

## Verification

- A fixture asserting a subagent session carries populated cwd, repo root,
  branch, SHA, dirty-diff content, and parent_session_id. Must fail against
  current code (none of these are captured today).

## Defect log

1. `git_sha` column does not exist in the sessions schema — must be added.
2. Subagent sessions record no spawn provenance (cwd/repo/branch/SHA) — the
   single recordable reason 8 of 9 fail-before/pass-after candidates are
   unpinnable.
3. `parent_session_id` is only populated on 90/159 subagent sessions; the 8
   candidates all have `parent=NONE`.
4. The self-replay conversion rate is unknown and must be measured before any
   v4 projection is trusted.
