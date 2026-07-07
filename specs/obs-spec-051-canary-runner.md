# obs-spec-051 — Canary Runner

**Spec ID:** obs-spec-051
**Title:** Canary runner — task execution, scoring, baseline management
**Status:** DRAFT
**Owner:** Main
**Depends on:** obs-spec-050 (data model)
**Master plan ref:** v0.5.0 "Capability Monitoring Layer"

---

## 1. CLI Entry Point

```
observeco canary run [--agent AGENT] [--model MODEL] [--tasks TASKS] [--trials N] [--schedule]
observeco canary list [--agent AGENT]
observeco canary baseline [--agent AGENT] [--force]
```

- `canary run` — runs the canary suite for one agent. Default: all agents, all tasks, 3 trials.
- `canary list` — shows recent runs with pass rate, drift indicator.
- `canary baseline` — recomputes baseline from recent runs.

## 2. Architecture

```
CLI → CanaryRunner → TaskExecutor → AgentAdapter → LLM
                    → Scorer        → assertion engine
                    → BaselineManager → DB
```

### 2.1 CanaryRunner

```python
class CanaryRunner:
    def __init__(self, db, agent_adapter):
        self.db = db
        self.adapter = agent_adapter

    def run(self, agent_name, task_ids=None, trials=3, schedule=None):
        # 1. Load tasks (all or specified)
        # 2. Snapshot current config (model + prompt + tools → hash)
        # 3. For each task × trial:
        #    a. Execute via adapter
        #    b. Score result
        #    c. Store result
        # 4. Compute aggregate: pass rate, accuracy, CI, cost
        # 5. Compare against baseline → emit drift_event if significant
        # 6. Return CanaryReport
```

### 2.2 TaskExecutor

Runs one task one time:

```python
def execute_task(task, agent_name, agent_adapter, timeout=60):
    prompt = render_template(task.prompt, task.variables)
    start = time.monotonic()
    # Actual adapter uses run_task(agent_name, task), returns dict
    # Keys: output, model_used, harness_type, elapsed_seconds
    # Note: tokens, cost, timed_out are NOT returned by current adapter;
    # ponytail: extend run_task() to return these fields
    result = agent_adapter.run_task(agent_name, task)
    elapsed = time.monotonic() - start
    return TaskResult(
        output=result["output"],
        latency_ms=elapsed * 1000,
        model_used=result.get("model_used"),
        harness_type=result.get("harness_type"),
        tokens=result.get("tokens"),      # ponytail: not yet in adapter
        cost=result.get("cost"),          # ponytail: not yet in adapter
        hang=result.get("timed_out"),     # ponytail: not yet in adapter
        error=result.get("error"),
    )
```

**Timeout handling:** Uses `Popen` + `preexec_fn=os.setsid` + `os.killpg` (same pattern as existing `benchmark/adapters/hermes.py`). 60s default (matches `HermesBenchmarkAdapter`), per-task override from `canary_tasks.timeout`.

### 2.3 Scorer

```python
def score(task, result):
    assertions = json.loads(task.assertions) if isinstance(task.assertions, str) else task.assertions
    for assertion in assertions:
        if assertion["type"] == "exact_match":
            return result.output.strip() == assertion["target"]
        elif assertion["type"] == "contains":
            return all(kw in result.output for kw in assertion["keywords"])
        elif assertion["type"] == "numeric_range":
            val = extract_number(result.output)
            return assertion["min"] <= val <= assertion["max"]
        elif assertion["type"] == "regex":
            return re.search(assertion["pattern"], result.output)
        elif assertion["type"] == "llm_judge":
            return llm_judge(task, result)  # ponytail: see §5
    return False
```

**CI computation:** Bootstrap resampling (1000 iterations) on per-task accuracy across trials. Report 95% percentile interval.

### 2.4 BaselineManager

```python
class BaselineManager:
    def get_baseline(self, agent_name, config_hash):
        # Returns most recent active baseline for this config
        pass

    def compute_baseline(self, agent_name, config_hash, min_runs=3):
        # Aggregates last N runs with same config_hash
        # Stores in canary_baselines, expires old baseline
        pass

    def compare(self, run, baseline):
        # Two-sample z-test for proportions
        # Returns drift_pct, p_value, ci
        pass
```

**Baseline creation rules:**
- Auto-created after 3 runs with same config_hash
- Re-created when config_hash changes (new model, prompt, or tools)
- User can force-recompute with `canary baseline --force`

---

## 3. Agent Adapter

Reuses existing `HermesBenchmarkAdapter` from `src/observeco/benchmark/adapters/hermes.py`:

```python
class HermesBenchmarkAdapter:
    def run_task(self, agent_name: str, task: BenchmarkTask) -> dict:
        # Calls `hermes chat -q "..."` via subprocess with 60s timeout
        # Returns dict with keys: output, tokens, cost, timed_out, error
        pass
```

**ponytail:** Currently uses `hermes chat -q` which is a text-prompt interface. Native tool calling would be more accurate but requires the agent to have the right tools loaded. Upgrade path: add a `--tool-mode` flag that uses the Hermes API directly with tool schemas.

---

## 4. Schedule

Cron job via Hermes cron:

```
observeco canary run --agent all --schedule daily
```

**Schedule format:** `daily|hourly|weekly|cron(0 3 * * *)`. The `--schedule` flag creates or updates a Hermes cron job. Re-running with the same schedule is idempotent (updates, not duplicates). Default: 3am local time.

**Persistence:** The cron job is managed by Hermes' `cronjob` infrastructure (`hermes cron` commands). It survives daemon restarts. To remove: `observeco canary run --schedule off`.

---

## 5. ponytail: LLM-as-judge assertions

`llm_judge` assertion type uses a separate LLM call to evaluate output quality. This adds cost and latency. Upgrade path: (a) cache judge results by (task_id, output_hash), (b) allow user to configure judge model separately, (c) add confidence score from judge.

**Note (2026-07-06):** The `llm_judge` assertion is defined in the Scorer but returns "not implemented (deferred to v1.1)". Implementation is now specified in **obs-spec-057-benchmark-methodology-upgrade.md** §2.2. Current assertions (exact_match, contains, numeric_range, regex) are insufficient for meaningful quality evaluation — keyword containment can be passed by echoing prompt content. See obs-spec-057 for the full critical assessment and upgrade plan.

---

## 6. Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Canary run completion | 95% of runs complete under 5 min | `canary_runs.completed_at - started_at` |
| Task execution per trial | < 60s (per-task timeout) | `HermesBenchmarkAdapter` timeout |
| Baseline creation | Auto-created after 3 runs with same config | `canary_baselines` row count |
| Drift detection latency | < 1s after canary run completes | Time from run completion to drift_event insert |
| CLI response time | < 500ms for `canary list` | `time observeco canary list` |

---

## 7. Constraints Register

| # | Constraint | Type | Notes |
|---|-----------|------|-------|
| 1 | **Hermes agents only** | MUST | Adapter is `HermesBenchmarkAdapter`. Other agents need new adapters. |
| 2 | **Read-only tasks only (MVP)** | MUST | Tasks must not have side effects. See spec-050 §6 #3. |
| 3 | **Text-prompt interface** | SHOULD | Current adapter uses `hermes chat -q` (text). Native tool calling deferred. |
| 4 | **Single-threaded execution** | SHOULD | Tasks run sequentially per agent. Parallel execution deferred. |

---

## 8. File Changes

| File | Change |
|------|--------|
| `src/observeco/cli.py` | Add `canary` command group |
| `src/observeco/capability/canary.py` | New — CanaryRunner, TaskExecutor, Scorer |
| `src/observeco/capability/baseline.py` | New — BaselineManager |
|| `src/observeco/db.py` | Add migration 050 (inline entry in MIGRATIONS list — see spec-050 §2) |
