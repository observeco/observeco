# ObserveCo Capability Monitoring Layer — Comprehensive Test Plan (v0.5.0)

**Version:** 1.0.0  
**Date:** 2026-07-04  
**Author:** Hermes Agent  
**Scope:** Capability monitoring layer — canary runner, drift detection, config timeline, grid report, DirectModelAdapter, dashboard API, dashboard UI, CLI, DB schema  
**Spec References:** obs-spec-051, obs-spec-052, obs-spec-053, obs-spec-054, obs-spec-055

---

## Summary

| Metric | Count |
|--------|-------|
| **Total tests** | 205 |
| **Auto** | 170 |
| **Manual** | 35 |
| **P0** | 29 |
| **P1** | 76 |
| **P2** | 83 |
| **P3** | 17 |

### Per-Component Breakdown

| Component | Total | Auto | Manual | P0 | P1 | P2 | P3 |
|-----------|-------|------|--------|----|----|----|----|
| 1. DB Schema (migrations 50-51) | 14 | 14 | 0 | 4 | 6 | 2 | 2 |
| 1b. Import Boundary | 2 | 2 | 0 | 0 | 2 | 0 | 0 |
| 2. Scorer (5 assertion types) | 18 | 18 | 0 | 4 | 6 | 7 | 1 |
| 3. TaskExecutor | 8 | 8 | 0 | 1 | 4 | 2 | 1 |
| 4. CanaryRunner (run + CRUD) | 24 | 22 | 2 | 4 | 8 | 10 | 2 |
| 5. BaselineManager | 12 | 12 | 0 | 3 | 5 | 3 | 1 |
| 6. DriftDetector | 14 | 12 | 2 | 2 | 6 | 6 | 0 |
| 7. ConfigTimelineDetector | 12 | 10 | 2 | 2 | 4 | 5 | 1 |
| 8. DirectModelAdapter | 10 | 10 | 0 | 2 | 3 | 3 | 2 |
| 9. CapabilityGridRunner | 10 | 8 | 2 | 1 | 4 | 5 | 0 |
| 10. Dashboard API routes | 26 | 24 | 2 | 3 | 11 | 10 | 2 |
| 11. Dashboard UI (capability tab) | 14 | 0 | 14 | 0 | 1 | 11 | 2 |
| 12. CLI commands | 16 | 12 | 4 | 0 | 6 | 9 | 1 |
| 13. E2E Flows | 5 | 0 | 5 | 2 | 3 | 0 | 0 |
| 14. Edge Cases | 12 | 12 | 0 | 0 | 5 | 6 | 1 |
| 15. Security | 6 | 4 | 2 | 1 | 3 | 1 | 1 |
| 16. Resilience | 4 | 4 | 0 | 0 | 1 | 3 | 0 |

---

## Severity Classification

| Level | Meaning | Ship Block? | Response |
|-------|---------|-------------|----------|
| **P0** | Data loss, security hole, broken core flow (canary run → score → baseline → drift) | Yes | Fix before any further testing |
| **P1** | Feature broken but workaround exists, degraded UX, incorrect behavior | Yes | Fix before human test |
| **P2** | Cosmetic issue, edge case, missing polish | No | Fix post-launch unless P0/P1 clear |
| **P3** | Nice-to-have, future optimization, documentation gap | No | Deferred to next sprint |

---

## Gate Criteria

| Gate | Requirement |
|------|-------------|
| **Auto suite pass** | All 113 auto tests ✅ (0 P0/P1 failures) |
| **Manual suite pass** | All 35 manual tests ✅ on first human run |
| **E2E flows pass** | 5/5 integration flows ✅ (P0=100%) |
| **Security tests pass** | 0 exploitable findings |
| **Ready for human test** | All above gates met |

---

## Fixture & Isolation Strategy

| Resource | Auto Tests | Manual/E2E |
|----------|-----------|------------|
| **Database** | In-memory SQLite (`:memory:`) with migrations 50-51 applied per test class | Real `pulse.db` (backup first) |
| **LLM/Model API** | Fully mocked — `unittest.mock` for adapter responses | Real provider (ollama local) |
| **File system** | `tmp_path` fixture for config files, SOUL.md, profile dirs | Real `~/.hermes/` |
| **Time** | `freezegun` for datetime mocking | Real time |
| **Hermes binary** | Mocked `subprocess.run` for `hermes config show` | Real binary |

---

## Phase 1: Foundation — DB Schema, Imports, Config

### 1. DB Schema (Migrations 50-51) — 12 tests

| ID | Description | Severity | Method | Pass Criteria |
|----|-------------|----------|--------|---------------|
| 1.1 | Migration 50 creates all 8 tables: canary_tasks, canary_runs, canary_results, canary_baselines, drift_events, config_snapshots, grid_runs, grid_results | P0 | Auto | `SELECT name FROM sqlite_master WHERE type='table'` returns all 8 |
| 1.2 | Migration 50 creates all indexes: idx_canary_runs_agent, idx_canary_results_run, idx_drift_events_agent, idx_config_snapshots_agent | P0 | Auto | `SELECT name FROM sqlite_master WHERE type='index'` returns all 4 |
| 1.3 | Migration 51 adds `split` column to canary_tasks with default 'all' | P0 | Auto | `PRAGMA table_info(canary_tasks)` includes `split TEXT NOT NULL DEFAULT 'all'` |
| 1.4 | Migration 51 adds `provider_error` column to canary_results with default 0 | P0 | Auto | `PRAGMA table_info(canary_results)` includes `provider_error INTEGER NOT NULL DEFAULT 0` |
| 1.5 | Migration 51 adds `blended_score` column to grid_results | P1 | Auto | `PRAGMA table_info(grid_results)` includes `blended_score REAL` |
| 1.6 | canary_tasks has correct columns: id, name, description, prompt, assertions, timeout, model, trials, built_in, split, created_at | P1 | Auto | Column count = 11, all types match schema |
| 1.7 | canary_runs has correct columns: id, agent_name, config_hash, config_label, started_at, completed_at, status, pass_count, hang_count, fail_count, total_tasks, total_cost, total_tokens, error | P1 | Auto | Column count = 14, all types match schema |
| 1.8 | canary_results has correct FK constraints: run_id → canary_runs(id), task_id → canary_tasks(id) | P1 | Auto | INSERT with invalid FK raises IntegrityError |
| 1.9 | grid_results has UNIQUE constraint on (grid_run_id, task_id, model, config) | P2 | Auto | Duplicate insert raises IntegrityError |
| 1.10 | canary_baselines has UNIQUE constraint on (agent_name, config_hash, expires_at) | P2 | Auto | Duplicate insert raises IntegrityError |
| 1.11 | Migration 50 is idempotent — running twice doesn't error | P3 | Auto | Second run of migration 50 SQL returns without error |
| 1.12 | Migration 51 is idempotent — running twice doesn't error (ALTER TABLE ADD COLUMN on existing column is a no-op) | P3 | Auto | Second run of migration 51 SQL returns without error |

### 1b. Import Boundary — 2 tests

| ID | Description | Severity | Method | Pass Criteria |
|----|-------------|----------|--------|---------------|
| 1.13 | Capability modules don't import forbidden OS/runtime modules (psutil, yaml, socket) | P1 | Auto | AST scan of all `src/observeco/capability/*.py` shows no forbidden imports |
| 1.14 | DirectModelAdapter doesn't import psutil or socket (uses urllib only) | P1 | Auto | AST scan of `direct_model.py` shows no psutil/socket imports |

---

## Phase 2: Core Logic — Scorer, TaskExecutor, CanaryRunner, Baseline, Drift, Timeline, Grid

### 2. Scorer (5 assertion types) — 18 tests

| ID | Description | Severity | Method | Pass Criteria |
|----|-------------|----------|--------|---------------|
| 2.1 | `exact_match` passes when output matches target exactly (whitespace-trimmed) | P0 | Auto | `score([{type:'exact_match', target:'hello'}], 'hello')` → `(True, 1.0, ...)` |
| 2.2 | `exact_match` fails when output differs | P1 | Auto | `score([{type:'exact_match', target:'hello'}], 'world')` → `(False, 0.0, ...)` |
| 2.3 | `contains` passes when all keywords present (case-insensitive) | P0 | Auto | `score([{type:'contains', keywords:['foo','bar']}], 'Foo and BAR')` → `(True, 1.0, ...)` |
| 2.4 | `contains` fails when some keywords missing | P1 | Auto | `score([{type:'contains', keywords:['foo','bar']}], 'foo only')` → `(False, 0.5, ...)` |
| 2.5 | `contains` with `min_match` passes at partial match | P2 | Auto | `score([{type:'contains', keywords:['a','b','c'], min_match:2}], 'a b')` → `(True, 0.667, ...)` |
| 2.6 | `contains` with empty keywords returns fail | P2 | Auto | `score([{type:'contains', keywords:[]}], 'anything')` → `(False, 0.0, ...)` |
| 2.7 | `numeric_range` passes when extracted number is within [min, max] | P0 | Auto | `score([{type:'numeric_range', min:0, max:100}], 'score: 42')` → `(True, 1.0, ...)` |
| 2.8 | `numeric_range` fails when number is outside range | P1 | Auto | `score([{type:'numeric_range', min:0, max:10}], 'score: 42')` → `(False, 0.0, ...)` |
| 2.9 | `numeric_range` with tolerance passes at boundary | P2 | Auto | `score([{type:'numeric_range', min:0, max:10, tolerance:2}], 'score: 12')` → `(True, 1.0, ...)` |
| 2.10 | `numeric_range` fails when no number found in output | P2 | Auto | `score([{type:'numeric_range', min:0, max:10}], 'no numbers')` → `(False, 0.0, ...)` |
| 2.11 | `regex` passes when pattern matches output | P0 | Auto | `score([{type:'regex', pattern:'error \\\\d+'}], 'error 404')` → `(True, 1.0, ...)` |
| 2.12 | `regex` fails when pattern doesn't match | P1 | Auto | `score([{type:'regex', pattern:'error \\\\d+'}], 'success')` → `(False, 0.0, ...)` |
| 2.13 | `regex` with invalid pattern returns fail with error message | P2 | Auto | `score([{type:'regex', pattern:'[invalid'}], 'x')` → `(False, 0.0, ...)` |
| 2.14 | `llm_judge` returns fail with "not implemented" message | P2 | Auto | `score([{type:'llm_judge', criteria:'good'}], 'output')` → `(False, 0.0, "llm_judge: not implemented")` |
| 2.15 | Unknown assertion type returns fail with error message | P2 | Auto | `score([{type:'unknown_type'}], 'output')` → `(False, 0.0, "Unknown assertion type: unknown_type")` |
| 2.16 | Empty assertions list returns fail | P1 | Auto | `score([], 'output')` → `(False, 0.0, "No assertions defined")` |
| 2.17 | Multiple assertions: all must pass for overall pass | P1 | Auto | `score([{type:'contains',keywords:['a']},{type:'contains',keywords:['b']}], 'a b')` → `(True, 1.0, ...)` |
| 2.18 | `bootstrap_ci` returns (0,0) for <2 values | P3 | Auto | `Scorer.bootstrap_ci([0.5])` → `(0.0, 0.0)` |

### 3. TaskExecutor — 8 tests

| ID | Description | Severity | Method | Pass Criteria |
|----|-------------|----------|--------|---------------|
| 3.1 | `execute()` with valid adapter returns TaskResult with output and latency | P0 | Auto | Mock adapter returns `{output:'ok', model_used:'test'}` → result.output == 'ok', latency_ms > 0 |
| 3.2 | `execute()` with no adapter returns error TaskResult | P1 | Auto | `TaskExecutor(adapter=None).execute(task, 'agent')` → result.error == "No adapter configured" |
| 3.3 | `execute()` propagates `timed_out` flag from adapter | P1 | Auto | Mock adapter returns `{timed_out: True}` → result.hang == True |
| 3.4 | `execute()` propagates `provider_error` flag from adapter | P1 | Auto | Mock adapter returns `{provider_error: True}` → result.provider_error == True |
| 3.5 | `execute()` propagates adapter exception as hang | P1 | Auto | Mock adapter raises Exception → result.hang == True, result.error contains exception message |
| 3.6 | `execute()` passes task prompt to adapter correctly | P2 | Auto | Mock adapter captures `input_text` arg → matches task['prompt'] |
| 3.7 | `execute()` respects timeout parameter | P2 | Auto | Mock adapter receives timeout arg matching the task's timeout value |
| 3.8 | `execute()` measures wall-clock latency, not just adapter-reported | P3 | Auto | Mock adapter sleeps 0.01s → result.latency_ms >= 10 |

### 4. CanaryRunner — 18 tests

| ID | Description | Severity | Method | Pass Criteria |
|----|-------------|----------|--------|---------------|
| 4.1 | `run()` with valid tasks returns CanaryReport with correct pass/fail counts | P0 | Auto | 2 tasks × 3 trials, all pass → pass_count=6, fail_count=0, overall_accuracy=1.0 |
| 4.2 | `run()` with no tasks returns empty CanaryReport | P1 | Auto | Empty canary_tasks table → report.total_tasks == 0 |
| 4.3 | `run()` stores results in canary_results table | P0 | Auto | After run, `SELECT COUNT(*) FROM canary_results WHERE run_id=?` == tasks × trials |
| 4.4 | `run()` creates canary_runs record with 'running' then 'completed' status | P0 | Auto | Run record exists with status='completed', completed_at is set |
| 4.5 | `run()` with `split='dev'` only runs dev-split tasks | P1 | Auto | Create tasks with split='dev' and split='test' → only dev tasks executed |
| 4.6 | `run()` with `split='test'` only runs test-split tasks | P1 | Auto | Create tasks with split='dev' and split='test' → only test tasks executed |
| 4.7 | `run()` with specific task_ids runs only those tasks | P1 | Auto | 3 tasks exist, run with task_ids=[task1, task2] → 2 tasks executed |
| 4.8 | `run()` detects blowups: one trial collapses while others pass | P2 | Auto | 3 trials, 2 pass (acc=1.0), 1 fails (acc=0.0) → blowup_count >= 1 |
| 4.9 | `run()` computes config_hash from agent name + model + prompts | P2 | Auto | Same agent + same tasks → same config_hash; different tasks → different hash |
| 4.10 | `run()` with provider_error marks trial as fail with provider_error flag | P1 | Auto | Adapter returns provider_error=True → result status='fail', provider_error=1 in DB |
| 4.11 | `create_task()` inserts a new task into canary_tasks | P0 | Auto | `create_task({name:'test', prompt:'x', assertions:[]})` → `{'ok': True}`, task exists in DB |
| 4.12 | `create_task()` returns error for duplicate task ID | P1 | Auto | `create_task()` twice with same ID → second returns `{'ok': False, 'error': ...}` |
| 4.13 | `create_task()` with missing 'prompt' field raises KeyError | P2 | Auto | `create_task({name:'test'})` → returns error dict |
| 4.14 | `delete_task()` removes task from canary_tasks | P1 | Auto | After delete, `SELECT * FROM canary_tasks WHERE id=?` returns None |
| 4.15 | `delete_task()` on non-existent ID returns ok (idempotent) | P2 | Auto | `delete_task('nonexistent')` → `{'ok': True}` |
| 4.16 | `list_tasks()` returns all tasks ordered by created_at DESC | P2 | Auto | 3 tasks inserted → list returns 3 tasks, newest first |
| 4.17 | `get_task()` returns task with parsed assertions JSON | P2 | Auto | Task with assertions JSON string → returned dict has parsed list |
| 4.18 | `get_task()` returns None for non-existent task | P2 | Auto | `get_task('nonexistent')` → None |
| 4.19 | `update_task()` updates specified fields only | P2 | Auto | Update name + timeout → other fields (prompt, assertions) unchanged |
| 4.20 | `update_task()` with no valid fields returns error | P3 | Auto | `update_task('id', {})` → `{'ok': False, 'error': 'No fields to update'}` |
| 4.21 | `list_runs()` returns recent runs for an agent | P2 | Auto | 5 runs for agent 'test' → list returns 5 runs ordered by started_at DESC |
| 4.22 | `get_run_results()` returns all results for a run with task names | P2 | Auto | Run with 3 tasks → 3 results returned, each with task_name |
| 4.23 | **Manual:** Canary run with real adapter produces sensible output | P1 | Manual | Run with real Hermes adapter → output is non-empty, latency is reasonable |
| 4.24 | **Manual:** Canary run with 0 trials override produces no results | P3 | Manual | `run(trials=0)` → report with 0 trials executed |

### 5. BaselineManager — 12 tests

| ID | Description | Severity | Method | Pass Criteria |
|----|-------------|----------|--------|---------------|
| 5.1 | `compute_baseline()` with < min_runs returns None | P0 | Auto | 2 runs exist, min_runs=3 → returns None |
| 5.2 | `compute_baseline()` with >= min_runs creates baseline with correct accuracy | P0 | Auto | 3 runs with 80% pass rate → baseline accuracy ≈ 0.8 |
| 5.3 | `compute_baseline()` expires previous active baseline for same config | P1 | Auto | After new baseline, old baseline has expires_at set |
| 5.4 | `get_active_baseline()` returns the most recent unexpired baseline | P1 | Auto | Multiple baselines for same config → returns latest with expires_at=NULL |
| 5.5 | `compare()` returns None when no baseline exists | P1 | Auto | No baseline for agent+config → returns None |
| 5.6 | `compare()` returns DriftResult with correct drift_pct when baseline exists | P0 | Auto | Baseline acc=0.8, current acc=0.5 → drift_pct ≈ -30.0 |
| 5.7 | `compare()` severity='breach' when |drift| >= 5% AND p < 0.01 | P1 | Auto | Large drift with low p-value → severity='breach' |
| 5.8 | `compare()` severity='warning' when |drift| >= 3% AND p < 0.05 | P1 | Auto | Moderate drift with moderate p-value → severity='warning' |
| 5.9 | `compare()` severity='info' when |drift| >= 1% AND p < 0.05 | P2 | Auto | Small drift with moderate p-value → severity='info' |
| 5.10 | `compare()` identifies breached tasks (|task_drift| >= 5%) | P2 | Auto | One task drops 10% → appears in breached_tasks list |
| 5.11 | `compare()` handles edge case: n1=0 or n2=0 returns info severity | P2 | Auto | Zero-count baseline or run → returns DriftResult with severity='info' |
| 5.12 | `compare()` handles edge case: se=0 returns info severity | P3 | Auto | When pooled proportion is 0 or 1 → returns DriftResult with severity='info' |

### 6. DriftDetector — 14 tests

| ID | Description | Severity | Method | Pass Criteria |
|----|-------------|----------|--------|---------------|
| 6.1 | `check()` with no baseline auto-computes baseline from recent runs | P0 | Auto | 3+ runs exist → baseline created, returns None |
| 6.2 | `check()` with baseline and significant drift stores drift_event | P0 | Auto | Baseline exists, current run has -10% drift → drift_event inserted in DB |
| 6.3 | `check()` with baseline and no significant drift returns None | P1 | Auto | Baseline exists, current run matches baseline → returns None, no event stored |
| 6.4 | `check()` stores correct drift_pct, p_value, severity in drift_events | P1 | Auto | Verify stored values match DriftResult fields |
| 6.5 | `get_latest()` returns most recent drift event for agent | P1 | Auto | 3 events for agent → returns the newest |
| 6.6 | `get_latest()` returns None when no events exist | P2 | Auto | No events for agent → returns None |
| 6.7 | `get_history()` returns drift events + accuracy time series + baseline | P1 | Auto | 2 events + 5 runs + 1 baseline → all present in response |
| 6.8 | `get_history()` handles empty state (no events, no runs) | P2 | Auto | No data → returns dict with empty lists, baseline=None |
| 6.9 | `get_detail()` returns current run, baseline, drift, per-task breakdown | P1 | Auto | After drift event → all 4 sections populated with correct values |
| 6.10 | `get_detail()` returns None when no drift exists | P2 | Auto | No drift events → returns None |
| 6.11 | `acknowledge()` sets acknowledged=1 on drift event | P2 | Auto | After acknowledge → `SELECT acknowledged FROM drift_events WHERE id=?` returns 1 |
| 6.12 | `_load_config()` merges user config with defaults | P2 | Auto | User config has `drift.threshold_breach: 10` → merged config has threshold_breach=10 |
| 6.13 | **Manual:** Drift detection with real data produces sensible severity | P1 | Manual | Run canary, modify config, run again → drift detected with correct direction |
| 6.14 | **Manual:** Drift chart in dashboard shows correct time series | P2 | Manual | Multiple runs → chart shows accuracy points + baseline line |

### 7. ConfigTimelineDetector — 12 tests

| ID | Description | Severity | Method | Pass Criteria |
|----|-------------|----------|--------|---------------|
| 7.1 | `check_all_agents()` returns empty list when no config changes | P0 | Auto | No changes since last snapshot → returns [] |
| 7.2 | `check_all_agents()` detects SOUL.md content change | P0 | Auto | Modify SOUL.md → returns snapshot with change_type='prompt_update' |
| 7.3 | `check_all_agents()` detects model switch via hermes config show | P1 | Auto | Mock `hermes config show` returning different model → change_type='model_switch' |
| 7.4 | `check_all_agents()` detects tool config change | P1 | Auto | Modify profile YAML → change_type='tool_update' |
| 7.5 | `check_all_agents()` creates baseline snapshot on first check | P1 | Auto | No prior snapshots → change_type='baseline' |
| 7.6 | `_assign_segment()` reuses existing segment for same config_hash | P2 | Auto | Same hash → same segment letter |
| 7.7 | `_assign_segment()` assigns next available letter for new hash | P2 | Auto | Segments A, B exist → new hash gets C |
| 7.8 | `_assign_segment()` falls back to Z when all 26 letters used | P3 | Auto | 26 segments exist → next gets 'Z' |
| 7.9 | `_detect_soul_change()` returns None when no SOUL.md exists | P2 | Auto | Agent has no SOUL.md → returns None |
| 7.10 | `_detect_model_change()` returns None when hermes binary not found | P2 | Auto | Mock `shutil.which('hermes')` returns None → returns None |
| 7.11 | **Manual:** Config timeline shows real SOUL.md changes in dashboard | P1 | Manual | Edit SOUL.md, run check → timeline shows prompt_update event |
| 7.12 | **Manual:** Config timeline shows model switch after config change | P2 | Manual | Change model in Hermes config, run check → timeline shows model_switch |

### 8. DirectModelAdapter — 10 tests

| ID | Description | Severity | Method | Pass Criteria |
|----|-------------|----------|--------|---------------|
| 8.1 | `run_task()` returns output from model API call | P0 | Auto | Mock `urllib.request.urlopen` returns valid response → output matches content |
| 8.2 | `run_task()` returns provider_error=True on HTTP 429/5xx | P0 | Auto | Mock returns HTTP 429 → provider_error=True |
| 8.3 | `run_task()` returns timed_out=False + error on HTTP 4xx (non-provider) | P1 | Auto | Mock returns HTTP 400 → provider_error=False, error="HTTP 400" |
| 8.4 | `run_task()` returns provider_error=True on connection failure | P1 | Auto | Mock raises URLError → provider_error=True |
| 8.5 | `run_task()` returns error when no prompt provided | P1 | Auto | Empty prompt → error="No prompt provided" |
| 8.6 | `_resolve_provider()` resolves 'deepseek/deepseek-chat' correctly | P2 | Auto | Returns deepseek base URL + model name + auth headers |
| 8.7 | `_resolve_provider()` resolves 'custom-ollama/...' to localhost | P2 | Auto | Returns localhost:11434 base URL |
| 8.8 | `_resolve_provider()` falls back to Hermes config custom_providers | P2 | Auto | Hermes config has custom_providers entry → uses that base_url |
| 8.9 | `_resolve_provider()` falls back to built-in map for unknown provider | P3 | Auto | Unknown provider → logs warning, returns localhost:11434/v1 |
| 8.10 | `run_task()` estimates tokens and cost from prompt/output length | P3 | Auto | 100-char prompt + 200-char output → tokens > 0, cost > 0 |

### 9. CapabilityGridRunner — 10 tests

| ID | Description | Severity | Method | Pass Criteria |
|----|-------------|----------|--------|---------------|
| 9.1 | `run()` executes all model × config × task combinations | P0 | Auto | 2 models × 2 configs × 3 tasks × 3 trials = 36 cells → 36 grid_results rows |
| 9.2 | `run()` returns error when no tasks exist | P1 | Auto | Empty canary_tasks → result has error="No canary tasks defined" |
| 9.3 | `run()` stores grid_runs record with correct metadata | P1 | Auto | Run record has models, configs, total_cells, status='completed' |
| 9.4 | `run()` computes per-cell accuracy with bootstrap CI | P1 | Auto | 3 trials with accuracies [0.5, 1.0, 1.0] → mean_accuracy ≈ 0.833, CI bounds present |
| 9.5 | `run()` flags provider errors in cell flags | P2 | Auto | Adapter returns provider_error → flags contains "provider_error" |
| 9.6 | `run()` flags hangs in cell hang field | P2 | Auto | Adapter returns timed_out → hang > 0 |
| 9.7 | `compute_blended_score()` computes correct score from accuracy, all_pass_rate, tokens | P2 | Auto | `compute_blended_score(0.8, 0.5, 1000)` → 0.8 + 0.5*0.5 - 0.005*0.001 = 1.049995 |
| 9.8 | `load_grid_config()` merges user config with defaults | P2 | Auto | User config has `grid.allpass_weight: 0.7` → merged config has allpass_weight=0.7 |
| 9.9 | **Manual:** Grid run with real models produces sensible comparison | P1 | Manual | Run grid with 2+ models → results show accuracy differences between models |
| 9.10 | **Manual:** Grid report in dashboard shows correct heatmap | P2 | Manual | After grid run → dashboard shows model × config × task matrix |

---

## Phase 3: Dashboard API Endpoints

### 10. Dashboard API Routes — 16 tests

| ID | Description | Severity | Method | Pass Criteria |
|----|-------------|----------|--------|---------------|
| 10.1 | `GET /api/capability/drift` returns drift detail for agent | P0 | Auto | With drift data → 200, response has current, baseline, drift, tasks |
| 10.2 | `GET /api/capability/drift` returns empty state when no drift | P1 | Auto | No drift data → 200, current=None, baseline=None, drift=None |
| 10.3 | `GET /api/capability/drift/history` returns time series + events | P1 | Auto | With data → 200, response has points, baseline, drift_events |
| 10.4 | `POST /api/capability/drift/{id}/acknowledge` marks event acknowledged | P1 | Auto | 200, `{'ok': True}`, event acknowledged in DB |
| 10.5 | `GET /api/capability/grid` returns grid report with cells | P0 | Auto | With grid data → 200, response has cells, models, configs, tasks |
| 10.6 | `GET /api/capability/grid` returns empty state when no grid runs | P1 | Auto | No grid runs → 200, cells=[], models=[], configs=[], tasks=[] |
| 10.7 | `GET /api/capability/timeline` returns config events + drift events merged | P1 | Auto | With data → 200, response has segments, events (sorted by date desc) |
| 10.8 | `GET /api/capability/timeline` returns empty state when no snapshots | P2 | Auto | No snapshots → 200, segments={}, events=[] |
| 10.9 | `GET /api/capability/tasks` returns enriched task list with last run data | P1 | Auto | 3 tasks, 1 with last run → 3 tasks returned, 1 has last_accuracy/last_status |
| 10.10 | `POST /api/capability/tasks` creates a new task | P0 | Auto | Valid data → 200, `{'ok': True, 'task_id': ...}` |
| 10.11 | `DELETE /api/capability/tasks/{id}` deletes a task | P1 | Auto | 200, `{'ok': True}`, task removed from DB |
| 10.12 | `GET /api/capability/tasks/{id}` returns task with parsed assertions | P1 | Auto | 200, task dict with assertions as list |
| 10.13 | `GET /api/capability/tasks/{id}` returns 404 for non-existent task | P2 | Auto | 404, `{'error': 'Task not found'}` |
| 10.14 | `PUT /api/capability/tasks/{id}` updates task fields | P2 | Auto | 200, `{'ok': True}`, task updated in DB |
| 10.15 | `POST /api/capability/canary/run` starts async canary run | P1 | Auto | 200, `{'ok': True, 'message': ...}`, canary_runs record created |
| 10.16 | `GET /api/capability/canary/status` returns live progress | P1 | Auto | 200, response has running, completed, pass_count, fail_count, hang_count |
| 10.17 | `POST /api/capability/grid/run` starts async grid run | P1 | Auto | 200, `{'ok': True}`, grid_runs record created |
| 10.18 | `GET /api/capability/drift/chart` returns drift HTML partial | P2 | Auto | 200, Content-Type text/html, contains drift hero section |
| 10.19 | `GET /api/capability/grid/table` returns grid HTML partial | P2 | Auto | 200, Content-Type text/html, contains grid table |
| 10.20 | `GET /api/capability/timeline/events` returns timeline HTML partial | P2 | Auto | 200, Content-Type text/html, contains timeline events |
| 10.21 | `GET /api/capability/tasks/list` returns task list HTML partial | P2 | Auto | 200, Content-Type text/html, contains task rows |
| 10.22 | `GET /api/capability/tasks/list` returns empty state HTML when no tasks | P2 | Auto | No tasks → 200, HTML contains "No Tasks Defined" message |
| 10.23 | `GET /api/capability/tasks/{id}/editor` returns task editor HTML partial | P2 | Auto | 200, Content-Type text/html, contains YAML editor + form mode |
| 10.24 | `GET /api/capability/tasks/{id}/editor` returns 404 HTML for non-existent task | P3 | Auto | 200, HTML contains "Task not found" |
| 10.25 | **Manual:** All API endpoints return correct HTTP status codes for auth scenarios | P2 | Manual | With/without X-ObserveCo-Token → correct 200/401/403 |
| 10.26 | **Manual:** API endpoints handle concurrent requests without race conditions | P3 | Manual | Simultaneous canary run + status poll → no DB errors |

---

## Phase 4: CLI Commands

### 11. CLI Commands — 10 tests

| ID | Description | Severity | Method | Pass Criteria |
|----|-------------|----------|--------|---------------|
| 11.1 | `observeco canary run --agent=test` runs canary and prints report | P1 | Auto | With seeded tasks → exit 0, output contains "Canary Report" and accuracy |
| 11.2 | `observeco canary run` with no tasks prints error message | P2 | Auto | No tasks → exit 0, output contains "No tasks found" |
| 11.3 | `observeco canary list --agent=test` lists recent runs | P2 | Auto | With runs → exit 0, output contains "Canary Runs" and run table |
| 11.4 | `observeco canary baseline --agent=test` computes baseline | P1 | Auto | With 3+ runs → exit 0, output contains "Baseline created" |
| 11.5 | `observeco canary baseline --force` recomputes with 1 run | P2 | Auto | With 1 run → exit 0, output contains "Baseline created" |
| 11.6 | `observeco grid run --agent=test` runs grid and prints results | P1 | Auto | With tasks → exit 0, output contains "Capability Grid" and cell count |
| 11.7 | `observeco grid list --agent=test` lists recent grid runs | P2 | Auto | With runs → exit 0, output contains "Grid Runs" |
| 11.8 | `observeco grid compare --agent=test` displays grid report | P2 | Auto | With completed run → exit 0, output contains "Grid Report" |
| 11.9 | `observeco task list` lists all canary tasks | P2 | Auto | With tasks → exit 0, output contains "Canary Tasks" |
| 11.10 | `observeco task create --yaml=file.yaml` creates task from YAML | P1 | Auto | Valid YAML → exit 0, output contains "Task created" |
| 11.11 | `observeco task delete <id>` deletes a task | P2 | Auto | Existing task → exit 0, output contains "Task deleted" |
| 11.12 | `observeco task validate <file.yaml>` validates YAML | P2 | Auto | Valid YAML → exit 0, output contains "YAML valid" |
| 11.13 | **Manual:** `observeco canary run` with real adapter produces sensible output | P1 | Manual | Real Hermes adapter → output is non-empty, latency reasonable |
| 11.14 | **Manual:** `observeco grid run` with real models produces comparison | P1 | Manual | 2+ real models → results show accuracy differences |
| 11.15 | **Manual:** `observeco task create` interactive mode creates task | P2 | Manual | Interactive input → task created in DB |
| 11.16 | **Manual:** `observeco task validate` with invalid YAML reports error | P3 | Manual | Invalid YAML → exit 0, output contains "Validation failed" |

---

## Phase 5: Dashboard UI (Capability Tab)

### 12. Dashboard UI — 8 tests

| ID | Description | Severity | Method | Pass Criteria |
|----|-------------|----------|--------|---------------|
| 12.1 | **Manual:** Capability tab loads all 4 sections (drift, grid, timeline, tasks) | P1 | Manual | Click "🎯 Capability" tab → all 4 sections render without JS errors |
| 12.2 | **Manual:** Drift section shows hero card with current vs baseline accuracy | P2 | Manual | With drift data → hero card shows accuracy, CI, drift percentage, severity |
| 12.3 | **Manual:** Drift section shows per-task breakdown table | P2 | Manual | With drift data → table shows each task with accuracy, baseline, delta, severity |
| 12.4 | **Manual:** Grid report shows model × config × task matrix | P2 | Manual | With grid data → matrix shows accuracy per cell, color-coded |
| 12.5 | **Manual:** Config timeline shows events with type icons and descriptions | P2 | Manual | With snapshots → timeline shows prompt_update, model_switch, tool_update events |
| 12.6 | **Manual:** Task management section shows task list with status indicators | P2 | Manual | With tasks → list shows name, assertion types, timeout, last accuracy |
| 12.7 | **Manual:** New task form creates task and refreshes list | P2 | Manual | Fill form, click Create → task appears in list, no JS errors |
| 12.8 | **Manual:** Empty state renders correctly for all 4 sections | P2 | Manual | No data → each section shows appropriate empty state message |
| 12.9 | **Manual:** "Run Canary" button triggers canary and shows progress | P2 | Manual | Click Run Canary → progress indicator shows, completes with toast |
| 12.10 | **Manual:** "Run Grid" button triggers grid and refreshes report | P2 | Manual | Click Run Grid → grid runs, report refreshes automatically |
| 12.11 | **Manual:** Task editor (YAML + Form mode) loads and saves correctly | P2 | Manual | Click Edit on task → editor shows, switch modes, save → task updated |
| 12.12 | **Manual:** Delete task shows confirmation and removes task | P2 | Manual | Click Delete → task removed from list |
| 12.13 | **Manual:** Responsive layout works at 375px, 768px, 1280px widths | P3 | Manual | Resize browser → no overlapping elements, all content readable |
| 12.14 | **Manual:** Keyboard navigation works for all interactive elements | P3 | Manual | Tab through all buttons/inputs → focus visible, Enter activates |

---

## Phase 6: Integration — End-to-End Flows

### 13. E2E Flows — 5 tests

| ID | Description | Severity | Method | Pass Criteria | Dependencies |
|----|-------------|----------|--------|---------------|--------------|
| 13.1 | **Full canary lifecycle:** Create task → run canary → view results in CLI → view in dashboard | P0 | Manual | Task created, canary runs, results stored, CLI shows report, dashboard shows drift | None |
| 13.2 | **Baseline + drift lifecycle:** Run canary 3x → baseline computed → modify config → run again → drift detected | P0 | Manual | Baseline created after 3 runs, drift detected after config change, severity matches change magnitude | 13.1 |
| 13.3 | **Grid lifecycle:** Create tasks → run grid → view grid report in CLI → view in dashboard | P1 | Manual | Grid runs all cells, CLI shows comparison table, dashboard shows matrix | 13.1 |
| 13.4 | **Config timeline lifecycle:** Edit SOUL.md → run timeline check → view timeline in dashboard | P1 | Manual | SOUL.md change detected, timeline shows prompt_update event | None |
| 13.5 | **Dashboard task management:** Create task via UI → edit via YAML → edit via form → delete | P1 | Manual | All CRUD operations work from dashboard, list refreshes after each | None |

### 13b. E2E Dependency Chain

```
13.1 (canary lifecycle) ──→ 13.2 (baseline + drift)
13.1 (canary lifecycle) ──→ 13.3 (grid lifecycle)
13.4 (config timeline) ── independent
13.5 (dashboard task mgmt) ── independent
```

---

## Phase 7: Edge Cases, Resilience, Security

### 14. Edge Cases — 12 tests

| ID | Description | Severity | Method | Pass Criteria |
|----|-------------|----------|--------|---------------|
| 14.1 | Empty DB: all API endpoints return valid empty-state responses | P1 | Auto | No data in any table → all endpoints return 200 with empty collections |
| 14.2 | No tasks: canary run returns empty report gracefully | P1 | Auto | `CanaryRunner.run()` with empty canary_tasks → report.total_tasks == 0 |
| 14.3 | Provider timeout: adapter times out → hang recorded, not crash | P1 | Auto | Mock adapter raises timeout → TaskResult.hang=True, no exception propagated |
| 14.4 | Provider 500 error: adapter returns HTTP 500 → provider_error=True | P1 | Auto | Mock returns HTTP 500 → provider_error=True, status='fail' |
| 14.5 | Provider 429 rate limit: adapter returns 429 → provider_error=True | P1 | Auto | Mock returns HTTP 429 → provider_error=True, status='fail' |
| 14.6 | Corrupt assertions JSON: Scorer handles gracefully | P2 | Auto | `score()` with malformed assertion dict → returns (False, 0.0, error message) |
| 14.7 | Very long task output (10K+ chars): Scorer handles without crash | P2 | Auto | 10K char output → score returns correct result, no memory error |
| 14.8 | Concurrent canary runs: two runs for same agent don't corrupt each other | P2 | Auto | Two simultaneous runs → both complete, results stored correctly |
| 14.9 | Stuck 'running' status: cleanup marks runs >30min as 'failed' | P2 | Auto | Run with status='running' and started_at >30min ago → status='failed' after cleanup |
| 14.10 | Missing config file: DriftDetector uses defaults | P2 | Auto | No `~/.observeco/config.json` → uses DEFAULT_DRIFT_CONFIG |
| 14.11 | Missing Hermes binary: ConfigTimelineDetector returns None for model check | P2 | Auto | `shutil.which('hermes')` returns None → `_detect_model_change()` returns None |
| 14.12 | Grid with 0 models: CapabilityGridRunner uses defaults | P3 | Auto | `run(models=[])` → uses DEFAULT_MODELS |

### 15. Security — 6 tests

| ID | Description | Severity | Method | Pass Criteria |
|----|-------------|----------|--------|---------------|
| 15.1 | SQL injection: task IDs with SQL metacharacters don't cause injection | P0 | Auto | Task ID `' OR '1'='1` → no unexpected data returned |
| 15.2 | XSS: task names with HTML/JS don't execute in dashboard | P1 | Auto | Task name `<script>alert(1)</script>` → HTML-escaped in API response |
| 15.3 | API token required: endpoints reject requests without valid token | P1 | Manual | No X-ObserveCo-Token header → 401/403 |
| 15.4 | No API key leakage: error messages don't expose API keys | P1 | Auto | Provider error with key in URL → error message redacts key |
| 15.5 | Path traversal: task file paths don't escape base directory | P2 | Auto | Task YAML path `../../etc/passwd` → rejected or sanitized |
| 15.6 | Rate limiting: rapid API calls don't overwhelm the server | P3 | Manual | 100 rapid requests → server remains responsive, no crash |

### 16. Resilience — 4 tests

| ID | Description | Severity | Method | Pass Criteria |
|----|-------------|----------|--------|---------------|
| 16.1 | DB connection failure: graceful error, not crash | P1 | Auto | Mock `_get_conn()` raises → error returned, no unhandled exception |
| 16.2 | Partial grid failure: one model fails, others complete | P2 | Auto | Model A fails, Model B succeeds → results for Model B stored, Model A has error flags |
| 16.3 | Large task set (50+ tasks): canary run completes within reasonable time | P2 | Auto | 50 tasks × 3 trials → completes in < 5 min (with mocked adapter) |
| 16.4 | Recovery after crash: stuck 'running' status cleaned up on next API call | P2 | Auto | Run stuck in 'running' → next status call marks it 'failed' |

---

## Structural Integrity Verification

### Row Count Cross-Check

```bash
# Total test rows
grep -cE '^\| [0-9]+\.[0-9]+ ' test-plan.md
# Expected: 148

# Auto
grep -c '| Auto |' test-plan.md
# Expected: 113

# Manual
grep -c '| Manual |' test-plan.md
# Expected: 35

# P0/P1/P2/P3
grep -c '| P0 |' test-plan.md
# Expected: 28
grep -c '| P1 |' test-plan.md
# Expected: 42
grep -c '| P2 |' test-plan.md
# Expected: 48
grep -c '| P3 |' test-plan.md
# Expected: 30
```

### Duplicate Section Detection

```bash
grep '^## [0-9]\+\.' test-plan.md | sort | uniq -d
# Expected: no output (no duplicate section numbers)
```

---

## Execution Order

```
Phase 1 — Foundation (blocking)
  → 1. DB Schema (migrations 50-51)
  → 1b. Import Boundary

Phase 2 — Core Logic (unit tests, mocked deps)
  → 2. Scorer
  → 3. TaskExecutor
  → 4. CanaryRunner
  → 5. BaselineManager
  → 6. DriftDetector
  → 7. ConfigTimelineDetector
  → 8. DirectModelAdapter
  → 9. CapabilityGridRunner

Phase 3 — API Endpoints (with TestClient)
  → 10. Dashboard API routes

Phase 4 — CLI Commands (with CliRunner)
  → 11. CLI commands

Phase 5 — Dashboard UI (manual)
  → 12. Dashboard UI capability tab

Phase 6 — Integration (manual E2E)
  → 13. E2E flows

Phase 7 — Edge Cases, Security, Resilience
  → 14. Edge cases
  → 15. Security
  → 16. Resilience
```

---

## Existing Test Coverage

The following tests already exist in `tests/capability/` and should be preserved:

| File | Tests | Status |
|------|-------|--------|
| `test_env_snapshot.py` | 6 tests (defaults, probed_at, mutation, independence, errors) | ✅ Existing |
| `test_import_boundary.py` | 4 tests (forbidden imports, features dir, cost/tool path resolution) | ✅ Existing |
| `test_probe.py` | 12 tests (find_process, read_config, fingerprint, ports, store, session, orchestration) | ✅ Existing |
| `test_tier_selection.py` | 10 tests (cost_tracking tiers, tool_call tiers) | ✅ Existing |

These cover the probe/env-snapshot layer but NOT the capability monitoring layer (canary, drift, timeline, grid, adapters, API, CLI, DB schema). The 148 tests in this plan fill that gap.

---

## Appendix: API Route Inventory

All `/api/capability/` routes:

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/capability/canary/run` | Start async canary run |
| GET | `/api/capability/canary/status` | Check canary progress |
| GET | `/api/capability/drift` | Drift detail for hero section |
| GET | `/api/capability/drift/history` | Drift time series |
| POST | `/api/capability/drift/{id}/acknowledge` | Acknowledge drift event |
| GET | `/api/capability/drift/chart` | Drift chart HTML partial |
| GET | `/api/capability/grid` | Grid report JSON |
| POST | `/api/capability/grid/run` | Start async grid run |
| GET | `/api/capability/grid/table` | Grid table HTML partial |
| GET | `/api/capability/timeline` | Config timeline JSON |
| GET | `/api/capability/timeline/events` | Timeline HTML partial |
| GET | `/api/capability/tasks` | Task list JSON |
| POST | `/api/capability/tasks` | Create task |
| GET | `/api/capability/tasks/list` | Task list HTML partial |
| GET | `/api/capability/tasks/{id}` | Get single task |
| PUT | `/api/capability/tasks/{id}` | Update task |
| DELETE | `/api/capability/tasks/{id}` | Delete task |
| GET | `/api/capability/tasks/{id}/editor` | Task editor HTML partial |

## Appendix: CLI Command Inventory

| Command | Subcommand | Purpose |
|---------|-----------|---------|
| `observeco canary` | `run` | Run canary suite |
| `observeco canary` | `list` | List recent canary runs |
| `observeco canary` | `baseline` | Compute/recompute baseline |
| `observeco grid` | `run` | Run model × config grid |
| `observeco grid` | `list` | List recent grid runs |
| `observeco grid` | `compare` | Display grid report |
| `observeco task` | `list` | List canary tasks |
| `observeco task` | `create` | Create task (YAML or interactive) |
| `observeco task` | `delete` | Delete a task |
| `observeco task` | `validate` | Validate task YAML |

## Appendix: DB Table Inventory (Migrations 50-51)

| Table | Columns | Purpose |
|-------|---------|---------|
| `canary_tasks` | id, name, description, prompt, assertions, timeout, model, trials, built_in, split, created_at | Task definitions |
| `canary_runs` | id, agent_name, config_hash, config_label, started_at, completed_at, status, pass_count, hang_count, fail_count, total_tasks, total_cost, total_tokens, error | Canary run records |
| `canary_results` | id, run_id, task_id, status, accuracy, ci_lower, ci_upper, cost, tokens, latency_ms, trajectory, error, provider_error, created_at | Per-trial results |
| `canary_baselines` | id, agent_name, config_hash, config_label, run_count, accuracy, ci_lower, ci_upper, created_at, expires_at | Computed baselines |
| `drift_events` | id, agent_name, baseline_id, run_id, config_hash, config_label, drift_pct, p_value, ci_lower, ci_upper, severity, breached_tasks, acknowledged, created_at | Drift detection events |
| `config_snapshots` | id, agent_name, config_hash, config_label, change_type, description, git_commit, accuracy, segment, created_at | Config change timeline |
| `grid_runs` | id, agent_name, started_at, completed_at, status, models, configs, total_cells, total_cost, error | Grid run records |
| `grid_results` | id, grid_run_id, task_id, model, config, accuracy, ci_lower, ci_upper, cost, tokens, flags, hang, blended_score | Per-cell grid results |
