# obs-spec-050 — Capability Monitoring: Data Model

**Spec ID:** obs-spec-050
**Title:** Capability monitoring data model — canary, grid, drift, config timeline
**Status:** DRAFT
**Owner:** Main
**Supersedes:** obs-spec-024 §4 (capability layer data model)
**Master plan ref:** v0.5.0 "Capability Monitoring Layer"

---

## 1. New DB Tables

All tables in `~/.observeco/pulse.db` (existing SQLite DB, path from `db.py:DB_PATH`).

### 1.1 `canary_tasks` — task definitions

```sql
CREATE TABLE canary_tasks (
    id          TEXT PRIMARY KEY,  -- slug: "chart-interpretation"
    name        TEXT NOT NULL,    -- "Chart interpretation"
    description TEXT,
    prompt      TEXT NOT NULL,    -- template with {{ var }} placeholders
    assertions  TEXT NOT NULL,    -- JSON array: [{type, target, min?, max?, tolerance?, keywords?}]
    timeout     INTEGER NOT NULL DEFAULT 60,  -- seconds, matches HermesBenchmarkAdapter default
    model       TEXT,             -- optional model override
    trials      INTEGER NOT NULL DEFAULT 3,
    built_in    INTEGER NOT NULL DEFAULT 0,  -- 1 = shipped with ObserveCo
    split       TEXT NOT NULL DEFAULT 'all', -- dev | test | all (HF-inspired: prevents overfitting)
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);
```

Assertion types: `exact_match`, `contains`, `numeric_range`, `regex`, `llm_judge`.

**Note:** `assertions` is stored as a JSON string in the DB. The Scorer must call `json.loads()` before accessing fields like `.type`, `.target`, etc.

### 1.2 `canary_runs` — per-run results

```sql
CREATE TABLE canary_runs (
    id          TEXT PRIMARY KEY,  -- uuid
    agent_name  TEXT NOT NULL,
    config_hash TEXT NOT NULL,     -- sha256 of resolved config (model + prompt + tools)
    config_label TEXT,             -- "baseline-v3"
    started_at  TEXT NOT NULL,
    completed_at TEXT,
    status      TEXT NOT NULL DEFAULT 'running',  -- running | completed | failed
    total_tasks INTEGER NOT NULL,
    pass_count  INTEGER,
    hang_count  INTEGER,
    fail_count  INTEGER,
    total_cost  REAL,
    total_tokens INTEGER,
    error       TEXT               -- if status=failed
);
CREATE INDEX idx_canary_runs_agent ON canary_runs(agent_name, started_at);
```

### 1.3 `canary_results` — per-task results within a run

```sql
CREATE TABLE canary_results (
    id          TEXT PRIMARY KEY,
    run_id      TEXT NOT NULL REFERENCES canary_runs(id),
    task_id     TEXT NOT NULL REFERENCES canary_tasks(id),
    status      TEXT NOT NULL,     -- pass | fail | hang | provider_error
    accuracy    REAL,              -- 0.0–1.0 or NULL if hang
    ci_lower    REAL,
    ci_upper    REAL,
    cost        REAL,
    tokens      INTEGER,
    latency_ms  INTEGER,
    recovery    TEXT,              -- NULL | "auto-recovered" | "manual"
    trajectory  TEXT,              -- JSON: full agent trajectory for debugging
    error       TEXT,
    provider_error INTEGER NOT NULL DEFAULT 0,  -- 1 = failure was provider-side (5xx/429)
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX idx_canary_results_run ON canary_results(run_id);
```

### 1.4 `canary_baselines` — config-aware baselines

```sql
CREATE TABLE canary_baselines (
    id          TEXT PRIMARY KEY,
    agent_name  TEXT NOT NULL,
    config_hash TEXT NOT NULL,
    config_label TEXT,
    run_count   INTEGER NOT NULL,  -- how many runs this baseline is built from
    accuracy    REAL NOT NULL,      -- mean accuracy
    ci_lower    REAL,
    ci_upper    REAL,
    created_at  TEXT NOT NULL,
    expires_at  TEXT,               -- NULL = active, set when superseded
    UNIQUE(agent_name, config_hash, expires_at)
);
```

### 1.5 `drift_events` — detected drift

```sql
CREATE TABLE drift_events (
    id              TEXT PRIMARY KEY,
    agent_name      TEXT NOT NULL,
    baseline_id     TEXT REFERENCES canary_baselines(id),
    run_id          TEXT REFERENCES canary_runs(id),
    config_hash     TEXT NOT NULL,
    config_label    TEXT,
    drift_pct       REAL NOT NULL,  -- negative = decline
    p_value         REAL,
    ci_lower        REAL,
    ci_upper        REAL,
    severity        TEXT NOT NULL,  -- breach | warning | info
    breached_tasks  TEXT,           -- JSON array of task_ids
    acknowledged    INTEGER NOT NULL DEFAULT 0,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX idx_drift_events_agent ON drift_events(agent_name, created_at);
```

### 1.6 `config_snapshots` — auto-detected config changes

```sql
CREATE TABLE config_snapshots (
    id          TEXT PRIMARY KEY,
    agent_name  TEXT NOT NULL,
    config_hash TEXT NOT NULL,
    config_label TEXT,
    change_type TEXT NOT NULL,     -- baseline | model_switch | prompt_update | tool_update | drift
    description TEXT,
    git_commit  TEXT,
    accuracy    REAL,              -- accuracy at this point
    segment     TEXT,              -- "A" | "B" | "C" — for timeline grouping
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX idx_config_snapshots_agent ON config_snapshots(agent_name, created_at);
```

### 1.7 `grid_runs` — grid report results

```sql
CREATE TABLE grid_runs (
    id          TEXT PRIMARY KEY,
    agent_name  TEXT NOT NULL,
    started_at  TEXT NOT NULL,
    completed_at TEXT,
    status      TEXT NOT NULL DEFAULT 'running',
    models      TEXT NOT NULL,     -- JSON array of model names
    configs     TEXT NOT NULL,     -- JSON array of config labels
    total_cells INTEGER NOT NULL,
    total_cost  REAL,
    error       TEXT
);
```

### 1.8 `grid_results` — per-cell results

```sql
CREATE TABLE grid_results (
    id          TEXT PRIMARY KEY,
    grid_run_id TEXT NOT NULL REFERENCES grid_runs(id),
    task_id     TEXT NOT NULL REFERENCES canary_tasks(id),
    model       TEXT NOT NULL,
    config      TEXT NOT NULL,
    accuracy    REAL,
    ci_lower    REAL,
    ci_upper    REAL,
    cost        REAL,
    tokens      INTEGER,
    blended_score REAL,            -- accuracy + allpass_weight * all_pass_rate - cost_lambda * tokens/1M
    flags       TEXT,              -- JSON array: ["loop", "unsafe", "shortcut"]
    hang        INTEGER NOT NULL DEFAULT 0,
    UNIQUE(grid_run_id, task_id, model, config)
);
```

---

## 2. Migration Strategy

Migration is added as a new entry in the existing inline `MIGRATIONS` list in `db.py`:

```python
# In db.py:MIGRATIONS — add after the last entry:
(50, """
CREATE TABLE IF NOT EXISTS canary_tasks (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    description TEXT,
    prompt      TEXT NOT NULL,
    assertions  TEXT NOT NULL,
    timeout     INTEGER NOT NULL DEFAULT 60,
    model       TEXT,
    trials      INTEGER NOT NULL DEFAULT 3,
    built_in    INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS canary_runs (
    id          TEXT PRIMARY KEY,
    agent_name  TEXT NOT NULL,
    config_hash TEXT NOT NULL,
    config_label TEXT,
    started_at  TEXT NOT NULL,
    completed_at TEXT,
    status      TEXT NOT NULL DEFAULT 'running',
    total_tasks INTEGER NOT NULL,
    pass_count  INTEGER,
    hang_count  INTEGER,
    fail_count  INTEGER,
    total_cost  REAL,
    total_tokens INTEGER,
    error       TEXT
);
CREATE INDEX IF NOT EXISTS idx_canary_runs_agent ON canary_runs(agent_name, started_at);
CREATE TABLE IF NOT EXISTS canary_results (
    id          TEXT PRIMARY KEY,
    run_id      TEXT NOT NULL REFERENCES canary_runs(id),
    task_id     TEXT NOT NULL REFERENCES canary_tasks(id),
    status      TEXT NOT NULL,
    accuracy    REAL,
    ci_lower    REAL,
    ci_upper    REAL,
    cost        REAL,
    tokens      INTEGER,
    latency_ms  INTEGER,
    recovery    TEXT,
    trajectory  TEXT,
    error       TEXT,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_canary_results_run ON canary_results(run_id);
CREATE TABLE IF NOT EXISTS canary_baselines (
    id          TEXT PRIMARY KEY,
    agent_name  TEXT NOT NULL,
    config_hash TEXT NOT NULL,
    config_label TEXT,
    run_count   INTEGER NOT NULL,
    accuracy    REAL NOT NULL,
    ci_lower    REAL,
    ci_upper    REAL,
    created_at  TEXT NOT NULL,
    expires_at  TEXT,
    UNIQUE(agent_name, config_hash, expires_at)
);
CREATE TABLE IF NOT EXISTS drift_events (
    id              TEXT PRIMARY KEY,
    agent_name      TEXT NOT NULL,
    baseline_id     TEXT REFERENCES canary_baselines(id),
    run_id          TEXT REFERENCES canary_runs(id),
    config_hash     TEXT NOT NULL,
    config_label    TEXT,
    drift_pct       REAL NOT NULL,
    p_value         REAL,
    ci_lower        REAL,
    ci_upper        REAL,
    severity        TEXT NOT NULL,
    breached_tasks  TEXT,
    acknowledged    INTEGER NOT NULL DEFAULT 0,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_drift_events_agent ON drift_events(agent_name, created_at);
CREATE TABLE IF NOT EXISTS config_snapshots (
    id          TEXT PRIMARY KEY,
    agent_name  TEXT NOT NULL,
    config_hash TEXT NOT NULL,
    config_label TEXT,
    change_type TEXT NOT NULL,
    description TEXT,
    git_commit  TEXT,
    accuracy    REAL,
    segment     TEXT,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_config_snapshots_agent ON config_snapshots(agent_name, created_at);
CREATE TABLE IF NOT EXISTS grid_runs (
    id          TEXT PRIMARY KEY,
    agent_name  TEXT NOT NULL,
    started_at  TEXT NOT NULL,
    completed_at TEXT,
    status      TEXT NOT NULL DEFAULT 'running',
    models      TEXT NOT NULL,
    configs     TEXT NOT NULL,
    total_cells INTEGER NOT NULL,
    total_cost  REAL,
    error       TEXT
);
CREATE TABLE IF NOT EXISTS grid_results (
    id          TEXT PRIMARY KEY,
    grid_run_id TEXT NOT NULL REFERENCES grid_runs(id),
    task_id     TEXT NOT NULL REFERENCES canary_tasks(id),
    model       TEXT NOT NULL,
    config      TEXT NOT NULL,
    accuracy    REAL,
    ci_lower    REAL,
    ci_upper    REAL,
    cost        REAL,
    tokens      INTEGER,
    flags       TEXT,
    hang        INTEGER NOT NULL DEFAULT 0,
    UNIQUE(grid_run_id, task_id, model, config)
);
""")
```

Then bump `SCHEMA_VERSION` from 50 to 51 in `db.py` (migration 51 adds `split`, `provider_error`, and `blended_score` columns — inspired by HF harness-optimization findings).

All tables use `CREATE TABLE IF NOT EXISTS` — idempotent. No data migration needed (new feature, no existing data to transform).

---

## 3. Existing Tables Not Changed

- `pulse_log` — unchanged (passive monitoring continues)
- `token_logs` — unchanged
- `drift` table in chisel — unchanged (context drift, separate from capability drift)
- `agents` — unchanged

---

## 4. Data Continuity (GS-019)

### 4.1 State Matrix

| Table | Empty State | Populated State | Stale State |
|-------|-------------|-----------------|-------------|
| `canary_tasks` | "No tasks defined — create your first task" | Task list with status indicators | N/A (tasks are user-defined) |
| `canary_runs` | "No canary runs yet — run `observeco canary run`" | Run history with pass rate, drift | Runs older than 90d pruned |
| `canary_results` | Empty when no runs exist | Per-task accuracy, CI, cost | Prune blocked if parent exists (FK enforced) |
| `canary_baselines` | "No baseline — run canary 3+ times" | Active baseline per config | Expired baselines auto-cleaned |
| `drift_events` | "No drift detected" | Drift events with severity | Acknowledged events retained 30d |
| `config_snapshots` | "No config changes detected" | Timeline of changes | N/A (append-only) |
| `grid_runs` | "No grid runs yet" | Grid run history | Runs older than 30d pruned |
| `grid_results` | Empty when no grid runs | Per-cell accuracy matrix | Pruned with parent run |

### 4.2 Migration Backup

Before applying migration 50, call `db.backup()` (exists at `db.py:1015`). The backup creates a timestamped copy at `~/.observeco/backups/pulse_<timestamp>.db`. If migration fails, the previous schema is preserved in the backup.

### 4.3 FK Orphan Cleanup

SQLite foreign keys are enabled (`PRAGMA foreign_keys=ON` at db.py:902), but the tables lack `ON DELETE CASCADE`. Since FK enforcement blocks parent row deletion while child rows exist, pruning operations must delete child rows first. After any prune operation, run these cleanup queries:

```sql
DELETE FROM canary_results WHERE run_id NOT IN (SELECT id FROM canary_runs);
DELETE FROM drift_events WHERE run_id NOT IN (SELECT id FROM canary_runs);
DELETE FROM grid_results WHERE grid_run_id NOT IN (SELECT id FROM grid_runs);
```

This is handled in the prune cron job (see §4.4).

### 4.4 Pruning Schedule

| Table | Retention | Action |
|-------|-----------|--------|
| `canary_runs` | 90 days | Delete runs older than 90d, child rows first |
| `drift_events` | 30 days (acknowledged) | Delete acknowledged events older than 30d |
| `grid_runs` | 30 days | Delete runs older than 30d, child rows first |
| `canary_baselines` | Indefinite (expired) | Delete baselines with `expires_at < now()` |

Pruning runs every 24h via the existing PruneConsumer in `watch_consumers.py` (PRUNE_INTERVAL=86400).

---

## 5. Success Metrics

| Metric | Target | Measurement | Spec |
|--------|--------|-------------|------|
| Migration applies cleanly | 100% of installs | `SCHEMA_VERSION` reaches 50 without error | 050 |
| FK orphan count after prune | 0 orphans | `SELECT COUNT(*) FROM canary_results WHERE run_id NOT IN (SELECT id FROM canary_runs)` | 050 |
| Backup completes before migration | < 1s | `db.backup()` call time | 050 |
| Prune completes within budget | < 5s for 10K rows | PruneConsumer execution time | 050 |

---

## 6. Constraints Register

| # | Constraint | Type | Notes |
|---|-----------|------|-------|
| 1 | **macOS only** | MUST | Hermes agents run on macOS. All paths use `platformdirs.user_data_dir()`. No Windows/Linux support. |
| 2 | **Hermes agents only** | MUST | Capability monitoring targets Hermes agents. OpenClaw deferred. |
| 3 | **Read-only tasks only (MVP)** | MUST | Tasks must not have side effects. Write operations detected and flagged, not silently allowed. |
| 4 | **Local SQLite only** | MUST | All data in `pulse.db`. No remote/cloud storage. |
| 5 | **Single machine** | MUST | No multi-machine fleet aggregation. |
| 6 | **Ollama Pro models** | SHOULD | Default models assume Ollama Pro availability (deepseek-v4-flash, deepseek-v4-pro, ornith:latest). |
| 7 | **Config hash is approximate** | SHOULD | sha256 of (model + prompt + tool list) — won't detect template rendering changes. |
| 8 | **LLM-as-judge adds cost** | SHOULD | `llm_judge` assertion type uses a separate LLM call. User should configure judge model separately. |

---

## 7. Cross-Cutting RDR

**Problem:** Users running Hermes agents locally have no way to know if their agents' capabilities are degrading over time. Generic benchmarks (τ-bench, SWE-bench) don't predict real performance on user-specific tasks.

**Solution sketch:** A capability monitoring layer that runs user-defined tasks (canary suite) on a schedule, compares results against config-aware baselines, detects statistical drift, and provides a model×config comparison grid.

**Key constraint:** All data local, zero cloud. Tasks must be read-only/idempotent (MVP). Cost must be surfaced before enabling schedules.

**Success metric:** User can answer "Is my agent still working?" in under 30 seconds from dashboard.

**State enumeration:** Fresh install (no tasks, no runs) → First baseline (3+ runs) → Steady state (daily runs, drift monitoring) → Config change (new baseline auto-created) → Drift detected (alert + triage path).

**Lifecycle coverage:** Start (migration auto-applies) → Run (canary runs on schedule) → Crash (next run picks up, no data loss) → Rebuild (migration idempotent) → Cleanup (pruning every 24h).

**Data continuity:** See §4 Data Continuity above.

---

## 8. ponytail: Config hash is a simple sha256 of (model + prompt + tool list). This won't detect prompt template changes that don't change the rendered output. Upgrade path: hash the resolved prompt after template rendering, not the template itself.
