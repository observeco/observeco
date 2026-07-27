# obs-spec-061 — Harness Optimization Evaluation Framework

**Spec ID:** obs-spec-061
**Title:** Falsifiable evaluation framework for harness optimization — test-time scaling baselines, generalization gate, and memorization detection
**Status:** DRAFT
**Owner:** Main
**Depends on:** obs-spec-057 (benchmark methodology — dev/test split, assertion system), obs-spec-051 (canary runner), obs-spec-055 (task definition)
**Blocks:** obs-spec-056 (harness optimization loop — MUST NOT ship without this spec implemented)
**Master plan ref:** v0.6.0 "Agent Quality Management"
**Created:** 2026-07-15
**Reference:** Wang et al., "Rethinking the Evaluation of Harness Evolution for Agents" (arXiv:2607.12227, 2026)

---

## 1. Problem Statement

obs-spec-056 describes an Automated Harness Optimization Loop: an LLM proposer reads canary trajectories, proposes harness edits, evaluates on the dev split, and promotes if blended score improves by ≥1pp over the incumbent. This protocol has two fundamental flaws exposed by Wang et al. (2026):

### 1.1 No Test-Time Scaling Baseline

Harness evolution is itself an iterative search procedure that repeatedly evaluates and revises candidate harnesses using task feedback. Without comparing against simple test-time scaling baselines (parallel sampling, sequential refinement) under matched compute/feedback budgets, it is impossible to determine whether reported gains arise from improved harness design or from additional search alone. The paper empirically demonstrates that on Terminal-Bench 2.1 with GPT-5.4 and Claude Opus 4.6, automatic harness evolution does NOT consistently outperform simple test-time scaling.

**Implication for ObserveCo:** Shipping spec #56 without a baseline means any reported "improvement" may be indistinguishable from "we ran the agent more times." The feature would be scientifically unfalsifiable.

### 1.2 Overfitting to the Dev Split

When the same task set is used for both harness search and final evaluation, reported gains reflect adaptation to those specific tasks. The paper shows that when evolved harnesses are evaluated on held-out tasks, generalization is limited.

**Implication for ObserveCo:** spec #56's promotion gate only checks dev-split improvement (≥1pp). It does NOT run the promoted harness on the test split to verify generalization. A harness that overfits to dev tasks would be promoted — and then fail on the test split in production canary runs.

### 1.3 Memorization Over Distillation

The paper found that harness edits are typically task-specific rules ("always run X before Y", "dataset Z has property W") embedded in prompts, rather than general strategies. The "copy-and-adapt compounding" pattern in spec #56 is exactly the pattern prone to this.

**Implication for ObserveCo:** Without a mechanism to classify proposed edits as task-specific vs generalizable, the optimization loop may accumulate task-specific memorizations that pad dev scores without improving real agent quality.

### 1.4 Hard Failure Core Untouched

The paper shows harness evolution improves easy/medium tasks while the hard core remains unsolved. A 1pp aggregate gain could be "all easy tasks got easier, hard tasks unchanged" — which is not useful for users trying to determine if their agent is actually getting better.

---

## 2. Design

### 2.1 Test-Time Scaling Baselines

Two baseline modes added to the canary runner, runnable alongside harness optimization:

#### 2.1.1 Parallel Sampling (`--mode parallel-sampling`)

Run k independent rollouts of the same task with the current (unmodified) harness. Aggregate by majority vote on binary assertions, or by LLM judge median score on graded assertions. Report pass@1 (average across rollouts) and pass@k (any rollout succeeds).

**Implementation:**
- Reuse existing `CanaryRunner.run_task()` — call it k times with the same task and harness
- Aggregate: for binary assertions, majority vote (≥50% pass = pass); for `llm_judge`, take median of k scores
- Budget parameter: `--budget N` controls k (default: 5)
- No harness modification — identical harness for all rollouts
- Temperature: use task's configured temperature (0.0 by default for reproducibility)

#### 2.1.2 Sequential Refinement (`--mode sequential-refinement`)

Run a rollout, then feed the result + assertion feedback back to the agent for one revision pass. Repeat up to r rounds. Report final-round accuracy.

**Implementation:**
- Round 1: standard `CanaryRunner.run_task()` — capture output + assertion results
- Round 2..r: re-run with augmented prompt: "Your previous answer was: {output}. Assertion results: {pass/fail per assertion with reasoning}. Revise your answer."
- Budget parameter: `--refinement-rounds R` (default: 3)
- No harness modification — the refinement happens at the task level, not the harness level
- Assertion feedback is the same feedback harness evolution receives (fair comparison)

#### 2.1.3 Budget Matching

Every harness optimization run MUST report alongside it:
- **Harness optimization score** (from spec #56's loop)
- **Parallel sampling score** (same dev tasks, k = total rollouts used by harness optimization)
- **Sequential refinement score** (same dev tasks, r = total rounds used by harness optimization)
- **Baseline (single-shot) score** (same dev tasks, 1 rollout, no modification)

All three methods receive the same total compute budget (measured in agent rollouts). The dashboard shows all four numbers side-by-side. If harness optimization does not beat parallel sampling under matched budget, the optimization run is flagged as "no harness improvement detected — gains attributable to search budget."

### 2.2 Test-Split Generalization Gate

The promotion gate in spec #56 is upgraded from:

**Current (spec #56):** `dev_score ≥ incumbent_dev_score + 1pp`

**New (spec #061):** `dev_score ≥ incumbent_dev_score + 1pp` AND `test_score ≥ incumbent_test_score - 0.5pp`

The candidate harness must:
1. Improve on dev by ≥1pp (existing requirement)
2. NOT regress on test by more than 0.5pp (new requirement — allows noise but catches overfitting)

If the candidate passes dev but fails test, the optimization is logged as "dev-only improvement — overfitting suspected" and the harness is NOT promoted.

**Implementation:**
- After the harness optimization loop produces a candidate harness, run it on the full test split (6 tasks × 10 trials = 60 rollouts)
- Compare against the incumbent harness's most recent test-split baseline
- The test-split evaluation uses the same canary runner configuration (temperature, assertions, scoring)
- Cost: ~60 additional agent rollouts per promotion check (~$0.50-1.00 depending on model)

**Empty state:** If the test split has 0 tasks, skip the generalization gate and log a warning: "No test tasks — generalization cannot be verified. Promotion allowed on dev-only criteria." The dashboard shows a yellow warning badge.

**Error state:** If a rollout crashes (OOM, timeout, provider error), score it as r=0 (per Wang et al. convention). Do NOT retry — crashed rollouts count as failures in the pass@1 average. Log the crash in `harness_eval_runs` with error details.

**Stale baseline:** If the incumbent's test-split baseline was computed >14 days ago or with a different `config_hash`, flag the comparison as "stale baseline — comparison may be invalid" and require a fresh incumbent test-split run before the gate fires.

### 2.3 Edit Classification (Memorization Detection)

After the LLM proposer generates a harness edit, a classifier labels it:

| Label | Description | Example |
|-------|-------------|---------|
| `task-specific` | Rule that only helps the specific dev tasks | "For arithmetic tasks, always show your work step by step" |
| `generalizable` | Strategy that transfers across tasks | "Break complex problems into sub-steps before attempting" |
| `config-fix` | Infrastructure/config correction | "Increase shell timeout from 30s to 120s" |
| `safety` | Guardrail or constraint | "Never delete files without confirmation" |

**Implementation:**
- LLM judge (same infrastructure as canary `llm_judge` assertion) classifies the edit text + diff
- Input: the proposed edit (old harness snippet → new harness snippet)
- Output: label + confidence + reasoning
- Track ratio over time: if >70% of edits in an optimization run are `task-specific`, flag the run as "memorization-dominant — limited generalization expected"
- Dashboard shows the ratio as a stacked bar (task-specific vs generalizable vs config-fix vs safety)
- **Fallback:** If no `OBSERVECO_LLM_API_KEY` configured (same BYOK dependency as canary's `llm_judge`), classify as `unclassified` with confidence=0 and log a warning. The stacked bar shows an "unclassified" segment. The 70% memorization flag does NOT fire when >50% of edits are unclassified.

### 2.4 Difficulty-Stratified Reporting

Break down optimization gains by task difficulty (easy/medium/hard). The promotion report shows:

| Difficulty | Incumbent | Candidate | Delta |
|------------|-----------|-----------|-------|
| Easy | 85% | 88% | +3pp |
| Medium | 60% | 61% | +1pp |
| Hard | 20% | 20% | 0pp |
| **Aggregate** | **55%** | **56%** | **+1pp** |

**Rule:** If the aggregate improvement is ≥1pp but ALL of it comes from easy tasks (medium and hard delta = 0), flag as "easy-task inflation — no real capability improvement."

**Implementation:**
- Query existing `canary_results` joined with `canary_tasks.difficulty`
- Group by difficulty, compute pass@1 per group
- Compare incumbent vs candidate per group
- The flag fires when: `aggregate_delta ≥ 1pp AND medium_delta = 0 AND hard_delta = 0`

### 2.5 Unified Budget Report

Every harness optimization run produces a standardized report:

```
=== Harness Optimization Run #N ===
Agent: default
Date: 2026-07-15
Compute budget: 45 agent rollouts (dev split)

| Method                  | Dev Score | Test Score | pass@k |
|--------------------------|-----------|------------|--------|
| Baseline (single-shot)   | 42.0%     | 40.0%      | 42.0%  |
| Parallel Sampling (k=5)  | 51.0%     | 44.0%      | 68.0%  |
| Sequential Refine (r=3)  | 48.0%     | 43.0%      | —      |
| Harness Optimization      | 50.0%     | 41.0%      | —      |

Verdict: ❌ NO HARNESS IMPROVEMENT
  - Harness (50%) does not beat parallel sampling (51%) on dev
  - Test score regressed by -3pp (overfitting suspected)
  - 80% of edits classified as task-specific (memorization-dominant)
  - All improvement from easy tasks; medium/hard unchanged

Edit Classification:
  task-specific: 8 (80%)
  generalizable: 1 (10%)
  config-fix:    1 (10%)
  safety:        0 (0%)

Promoted: NO (failed generalization gate)
```

---

## 3. Database Changes

### 3.1 New Table: `harness_eval_runs`

```sql
CREATE TABLE harness_eval_runs (
    id              TEXT PRIMARY KEY,
    optimization_run_id TEXT NOT NULL,  -- FK to harness_optimization_runs (spec-056)
    method          TEXT NOT NULL,       -- 'baseline' | 'parallel_sampling' | 'sequential_refinement' | 'harness_optimization'
    split           TEXT NOT NULL,       -- 'dev' | 'test'
    total_rollouts  INTEGER NOT NULL,
    pass_at_1       REAL NOT NULL,
    pass_at_k       REAL,               -- NULL for non-sampling methods
    difficulty_breakdown TEXT,          -- JSON: {easy: {score, delta}, medium: {...}, hard: {...}}
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);
```

### 3.2 New Table: `harness_edits`

```sql
CREATE TABLE harness_edits (
    id              TEXT PRIMARY KEY,
    optimization_run_id TEXT NOT NULL,
    edit_text       TEXT NOT NULL,       -- the proposed change description
    old_snippet     TEXT,                -- harness code before edit
    new_snippet     TEXT,                -- harness code after edit
    classification  TEXT NOT NULL,       -- 'task-specific' | 'generalizable' | 'config-fix' | 'safety'
    classification_confidence REAL NOT NULL,
    classification_reasoning TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now()))
);
```

---

## 4. CLI Interface

```bash
# Run harness optimization with full evaluation framework
observeco harness optimize --agent default --iterations 10

# Run only the baselines (no harness modification) for comparison
observeco harness baseline --agent default --budget 45

# View optimization history with all four methods side-by-side
observeco harness history --agent default --last 10

# The optimize command now requires --include-baselines (default: true)
# to prevent running optimization without the comparison framework
observeco harness optimize --agent default --iterations 10 --no-baselines
# ↑ this flag exists but prints a warning: "Running without baselines — 
#   gains will not be attributable to harness design vs search budget"
```

---

## 5. Dashboard Integration

### 5.1 Optimization Run Detail View

When viewing a harness optimization run, the dashboard shows:

1. **Budget comparison table** — all four methods side-by-side (baseline, parallel sampling, sequential refinement, harness optimization)
2. **Promotion verdict** — ✅ promoted / ❌ rejected with reason
3. **Edit classification chart** — stacked bar of task-specific vs generalizable vs config-fix vs safety
4. **Difficulty-stratified table** — incumbent vs candidate per difficulty level
5. **Generalization check** — dev score vs test score, with overfitting flag

### 5.2 Fleet-Level Optimization Trend

In the Capability tab, a new chart shows optimization runs over time with:
- X-axis: optimization run number
- Y-axis: dev score
- Lines: harness optimization, parallel sampling (baseline), sequential refinement (baseline)
- A persistent gap between harness optimization and baselines = no real harness improvement

---

## 6. Implementation Order

1. **Test-time scaling modes** (parallel sampling, sequential refinement) in canary runner — ~1d
2. **Test-split generalization gate** in harness optimization loop — ~0.5d
3. **Edit classifier** (LLM judge on edit diffs) — ~0.5d
4. **Difficulty-stratified reporting** (SQL queries + dashboard) — ~0.5d
5. **Unified budget report** (CLI + dashboard) — ~0.5d

**Total: ~3d**

---

## 7. Relationship to Existing Specs

| Spec | Relationship |
|------|-------------|
| obs-spec-051 (canary runner) | Adds two new run modes (parallel-sampling, sequential-refinement) |
| obs-spec-056 (harness optimization loop) | **BLOCKS** — #56 must not ship without #61. The promotion gate in #56 is upgraded by #61's generalization gate. |
| obs-spec-057 (benchmark methodology) | Depends on dev/test split (§2.5), assertion system (§2.2), difficulty metadata (§2.6). All exist. |
| obs-spec-054 (grid report) | The grid report can optionally include test-time scaling baselines as a "config" column for comparison. |

---

## 8. Acceptance Criteria

- [ ] `observeco harness optimize --agent default --iterations 3` produces a unified budget report with all four methods
- [ ] Parallel sampling mode runs k rollouts with majority vote aggregation
- [ ] Sequential refinement mode runs r rounds with assertion feedback
- [ ] Promotion gate rejects candidates that regress test split by >0.5pp
- [ ] Edit classifier labels each proposed edit with ≥80% confidence
- [ ] Difficulty-stratified report flags easy-task inflation
- [ ] Dashboard shows optimization run detail with all five sections (§5.1)
- [ ] Dashboard shows loading state during optimization (progress indicator, not blank)
- [ ] Dashboard shows empty state when no optimization runs exist ("No optimization runs yet. Run `observeco harness optimize` to start.")
- [ ] `--no-baselines` flag prints warning but does not block execution
- [ ] All existing canary tests still pass (no regression in canary runner core)
- [ ] Edit classifier falls back to "unclassified" label when no LLM API key configured (graceful degradation, not crash)
- [ ] Stale baseline detection flags comparisons against baselines >14 days old or with different config_hash

---

## 9. Lifecycle Specification

### 9.1 Trigger

- **Manual:** `observeco harness optimize --agent AGENT --iterations N` (CLI)
- **Dashboard:** "Run Optimization" button in Capability tab (calls same backend)
- **NOT scheduled:** Optimization runs are manually triggered only — no auto-cron. The cost (10-15× a normal canary run) makes automatic scheduling dangerous without budget guards (spec #56 may add scheduled optimization in the future, gated by G1.1 budget cap).

### 9.2 Retention

- `harness_eval_runs`: retain 90 days, prune weekly (reuse existing prune cron at 3am Sunday)
- `harness_edits`: retain 90 days, prune with same schedule
- Promotion history (which harness was promoted when): retain indefinitely (small data volume, high diagnostic value)

### 9.3 Cost Summary

A single optimization run with all four methods (budget=45 rollouts):

| Method | Rollouts | Estimated cost (deepseek-v4-flash) |
|--------|----------|-------------------------------------|
| Baseline (single-shot) | 3 (dev tasks) | ~$0.03 |
| Parallel sampling (k=5) | 15 (3 dev × 5) | ~$0.15 |
| Sequential refinement (r=3) | 9 (3 dev × 3 rounds) | ~$0.09 |
| Harness optimization | 15 (3 dev × 5 iterations) | ~$0.15 |
| Test-split generalization | 60 (6 test × 10 trials) | ~$0.60 |
| Edit classification (LLM judge) | ~10 edits | ~$0.02 |
| **Total per optimization run** | **~102 rollouts** | **~$1.04** |

**Note:** Cost scales linearly with iterations and budget. A 10-iteration run with k=10 could cost $3-5. The dashboard should show estimated cost before the user confirms the run.

### 9.4 Dashboard States

| State | When | What renders |
|-------|------|-------------|
| **Empty** | No optimization runs exist for this agent | "No optimization runs yet. Run `observeco harness optimize --agent default` to start." + CLI copy button |
| **Loading** | Optimization in progress (rollouts running) | Progress bar: "Running baseline (1/4)..." with spinner. Partial results not shown until method completes. |
| **Complete** | All four methods finished | Unified budget report (§2.5) + all five dashboard sections (§5.1) |
| **Partial failure** | Some methods crashed | Completed methods shown normally; crashed methods show red badge: "Crashed — see error log" |
| **In-progress + crash** | Optimization crashed mid-run | Completed methods shown; remaining show "Interrupted"; verdict line says "Run incomplete — not all methods evaluated" |

---

## 10. What This Spec Does NOT Do

- Does not implement harness optimization itself (that's spec #56)
- Does not modify the canary runner's existing single-shot mode
- Does not add new assertion types (those are in spec #57)
- Does not address multi-agent harness optimization (single agent only)
- Does not define what constitutes a "harness" — that's spec #56's scope

---

## 11. References

- Wang et al., "Rethinking the Evaluation of Harness Evolution for Agents" (arXiv:2607.12227, 2026) — the paper that exposed the evaluation gaps
- Lee et al., "Meta-Harness: End-to-End Optimization of Model Harnesses" (2026) — the harness evolution method being evaluated
- Snell et al., "Scaling LLM Test-Time Compute Optimally" (2024) — test-time scaling foundations
- Wang et al., "Self-Consistency Improves Chain of Thought Reasoning" (2022) — parallel sampling
- Madaan et al., "Self-Refine: Iterative Refinement with Self-Feedback" (2023) — sequential refinement