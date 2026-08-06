# Workbench — Phase 0: Personal-hardcoded inventory

**Audience question deferred** per Sean's direction: publish the technical post
first, let the first respondent define the platform. Do not design the adapter
until a named person's store exists. This inventory is the audience-independent
Phase 0 work — the prerequisite for any install by anyone.

Scope: `scripts/workbench/` plus the adapter it calls
(`observeco/src/observeco/benchmark/adapters/hermes.py`). Each item classified:
**PERSONAL** (Sean's machine/repos — must de-personalize), **STRUCTURAL** (true
of Hermes for anyone — adapter's job), **GENERIC** (already portable).

---

## PERSONAL — assume this user's machine or repos

| # | Location | What | Why it breaks a stranger |
|---|---|---|---|
| P1 | `batch_runner.py:30`, `selection.py:20`, `anchor_counterfactual.py:29` | `REPO = "/Users/seanfzc/projects/observeco"` | Absolute repo path. A stranger's copy is elsewhere. |
| P2 | `batch_runner.py:37-42`, `selection.py:23-25` | Hardcoded repo allowlist (`observeco`, `observeco-main`, `observeco-cap`, `rqgm-core`, `EvoSkill-RQGM`, `open-design`) | Containment checks whitelist *Sean's* repos. Stranger's repos absent → every write flagged or missed. |
| P3 | `batch_runner.py:192`, `test_containment_identity.py:17` | `sys.path.insert(0, "/Users/seanfzc/projects/observeco/src")` | Absolute import of the observeco adapter. Not portable. |
| P4 | `selection.py:67-78,169-170,335` | "is this the observeco repo" regexes hardcoding `observeco` as repo name | The repo-name test is baked in. |
| P5 | `selections/decision-log-20260804.json` | Sean's real 98-session decision log (contains `[Sean Foo]` messages, real prompts) | Personal session data ships in the repo. |
| P6 | `selections/clean-*.json` | Task content hardcodes `src/observeco/...` rel paths | Tasks are observeco-specific; a stranger's repo has no `canary.py`. |

## STRUCTURAL — true of Hermes for anyone (adapter's job, not de-personalizable)

| # | Location | What | Why it's structural |
|---|---|---|---|
| S1 | `STATE_DB = ~/.hermes/state.db` (all scripts) | Hermes session store path | Correct for any Hermes user; the `HermesSessionSource` adapter reads it. |
| S2 | `HermesBenchmarkAdapter` import | Hermes is the *only* runner | This is the adapter seam: `Runner`/`SessionSource`/`EnvPin` generalize it. |
| S3 | worktree spawn + containment | pins at start, fresh worktree, explicit cwd | The gate stack itself — workload-agnostic. |

## GENERIC — already portable

| # | Location | What |
|---|---|---|
| G1 | `episode_log.py`, `anchor_counterfactual.py` core | The mechanism tests; only `STATE_DB` is Hermes-specific. |
| G2 | The 46-test suite | Assertions on mechanisms, not on Sean's data. |
| G3 | The gate logic (fail-before/pass-after, unmeasured-never-fail, no-silent-fallback) | Pure predicates. |

---

## De-personalization order (audience-independent)

1. **P1+P2 — repo resolution.** Replace hardcoded `REPO` + allowlist with
   env/config discovery (`WORKBENCH_REPO` or `git rev-parse --show-toplevel`
   from a given cwd). The allowlist becomes a config list, not a constant.
2. **P3 — adapter import.** Move the observeco adapter behind a `Runner`
   interface; scripts import the interface, not the absolute path. This is the
   seam item 4 will build out once an audience exists.
3. **P4 — repo-name independence.** The "is this the observeco repo" test
   becomes "is this any repo" (path under a git root), parameterized by config.
4. **P5+P6 — seed data.** Move the decision log + observeco tasks out of the
   shipped repo into a `seeds/` dir that's gitignored or example-only. A
   stranger's install starts with zero tasks; the funnel mines *their* sessions.

**Not touched until audience exists:** the `SessionSource`/`EnvPin`/`Runner`
interface itself. Per Sean's reasoning, an interface designed against one
implementation is a rename, not an abstraction. Defer until a named person's
store is being adapted to.

---

## Defect log

1. The decision log containing real session prompts (`[Sean Foo]` messages,
   real user requests) is committed to the repo. If this is ever published as
   the "checkable case study," it ships personal data. Must be scrubbed or moved
   to an example seed before any stranger-facing publish.
2. `batch_runner.py` imports the observeco adapter via absolute `sys.path` —
   the test suite and the runner both assume the observeco repo is present and
   at `/Users/seanfzc/projects/observeco/src`. A stranger running the tests on a
   Hermes-only box would fail at import before testing anything.
3. The repo allowlist in two places (batch_runner, selection) is already
   drifting (observed: selection.py has a different list than batch_runner).
   A single config source is needed, not two constants.
