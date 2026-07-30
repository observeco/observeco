# obs-spec-091: Fleet Baseline Diffing

**Status:** 🔴 Spec (2026-07-20) — New
**Product:** ObserveCo (Free + Pro)
**Depends on:** Existing `canary_baselines`, `canary_task_baselines`, `compute_l2_baselines()`, `drift_events` tables
**Owner:** Main

---

## §1 Problem

ObserveCo tracks per-agent baselines (RSS, P95, error rate, canary accuracy) and drift events. But there is **no fleet-level view** that answers: "Is the whole fleet healthier or worse than last week? Which agent is the outlier? Has cost gone up 23% across all agents?"

SigNoz triggered this gap — their session baseline diffing is more mature. The Grafana competitive watch also flagged it: "We track per-agent but have no ability to save fleet baselines and diff against them."

**Goal:** Save a snapshot of fleet state as a baseline JSON. Compare subsequent snapshots to detect regressions: "cost up 23% vs baseline, agent X health dropped 15 points."

---

## §2 Study Findings (2026-07-20)

### §2.1 What Already Exists

| Component | Status | Evidence |
|-----------|--------|----------|
| Per-agent canary baselines | ✅ Built | `canary_baselines` table, `canary_task_baselines` table |
| L2 baselines (RSS, P95, errors) | ✅ Built | `compute_l2_baselines()` in `db.py` |
| Drift detection | ✅ Built | `drift_events` table, `capability/drift.py` |
| Config-aware baselines | ✅ Built | `config_hash` column in baseline tables |
| Fleet-level comparison | ❌ Missing | No cross-agent aggregate view |

### §2.2 What's Needed

Not a new data model — a **dashboard view** that queries existing per-agent baselines, computes fleet aggregates, and shows diff. No new DB tables, no new collection infrastructure.

### §2.3 Harness-Engineering Reference Context

The `lopopolo/harness-engineering` repo (593⭐, CC-BY-4.0) provides three directly relevant patterns:

**1. The Bounded-Job Playbook (playbooks/improve-harness.md):**
The 6-step loop maps directly to what fleet baseline diffing should enable:
```
baseline → earliest gap → smallest owning intervention → native verification → fresh rerun → retain, revise, or remove
```
The playbook's "Record the job contract" step (target revision, external state, fixed worker config, accepted outcome, evidence) is exactly what a fleet baseline snapshot should capture. The "Preserve a compact result record" template at the end is a reference for the baseline JSON schema.

**2. The Authority Thesis (docs/authority/):**
"Keep capability and authority as separate contracts" — baselines should be **read-only snapshots**, not mutable state. A baseline is evidence, not policy. The diff view shows what changed; it does not auto-apply fixes. This prevents the baseline system from becoming a source of truth that drifts from the actual fleet state.

**3. The Fixed-Worker Thesis (docs/fixed-worker/):**
"Hold the worker constant during one adoption epoch" — baselines must be tied to specific worker configurations (model, provider, agent version). A baseline taken under deepseek-v4-flash is not comparable to one under kimi-k3. The diff view should warn when comparing across different worker configurations.

---

## §3 Architecture

### §3.1 Baseline Snapshot Schema

No new DB tables. A baseline is a JSON file stored at `~/.observeco/baselines/<name>.json`:

```json
{
  "name": "2026-07-20-weekly",
  "created_at": "2026-07-20T09:00:00Z",
  "worker_config": {
    "model": "deepseek-v4-flash",
    "provider": "ollama-cloud"
  },
  "agents": {
    "dreamer": {
      "uptime_pct": 99.2,
      "error_rate_pct": 2.1,
      "latency_p95_ms": 3400,
      "canary_accuracy": 87.5,
      "drift_events_7d": 3,
      "token_cost_7d": 0.42
    },
    "hound": {
      "uptime_pct": 100.0,
      "error_rate_pct": 0.0,
      "latency_p95_ms": 1200,
      "canary_accuracy": null,
      "drift_events_7d": 0,
      "token_cost_7d": 0.08
    }
  },
  "fleet_aggregates": {
    "agent_count": 12,
    "avg_uptime": 98.7,
    "avg_error_rate": 1.8,
    "total_token_cost_7d": 3.42,
    "total_drift_events_7d": 14
  }
}
```

### §3.2 CLI Commands

| Command | Description |
|---------|-------------|
| `observeco baseline save --name weekly` | Save current fleet state as baseline |
| `observeco baseline list` | List saved baselines |
| `observeco baseline diff --from weekly --to latest` | Show diff between two baselines |
| `observeco baseline show weekly` | Show baseline contents |

### §3.3 Dashboard View

- **Baseline tab in fleet view:** "Fleet Baseline" section with:
  - Save baseline button
  - Baseline list with timestamps
  - Diff view: side-by-side comparison of two baselines
  - Regression highlights: red for metrics that worsened >10%, green for improved >10%
- **Auto-baseline:** Daily cron saves a baseline at 09:00 (reuses existing cron infra)

### §3.4 Diff Computation

```python
def compute_diff(baseline_a: dict, baseline_b: dict) -> dict:
    """Compare two baselines, return structured diff.
    
    For each agent and each metric:
    - delta_pct = (b - a) / max(a, epsilon) * 100
    - direction = "improved" | "worsened" | "unchanged"
    - severity = "critical" if delta_pct > 20 else "warning" if > 10 else "info"
    """
```

---

## §4 Implementation

### Phase 1: Backend (~100 lines)

| File | Change |
|------|--------|
| `capability/baseline.py` | Add `save_fleet_baseline()`, `list_baselines()`, `load_baseline()`, `compute_diff()` |
| `cli.py` | Add `observeco baseline save/list/diff/show` commands |

### Phase 2: Dashboard (~50 lines)

| File | Change |
|------|--------|
| `dashboard/server.py` | Add `/api/baseline/save`, `/api/baseline/list`, `/api/baseline/diff` endpoints |
| `dashboard/templates/` | Baseline section in fleet view |

---

## §5 Edge Cases

- **Cold start:** First baseline requires at least 24h of data per agent. Agents with no data show N/A.
- **Worker config mismatch:** Diff view warns when baselines were taken under different model/provider configs
- **Agent added/removed:** Diff shows new agents as "new" and removed agents as "gone" — not as regressions
- **Empty baseline:** No agents registered → save creates empty baseline, diff shows "no agents to compare"
- **Large fleet:** 50+ agents → baseline JSON is ~50KB. Diff computation is O(n) per agent, fine for <100 agents

---

## §6 Pro Gating

- **Free:** Save/load baselines, manual diff view, 7-day auto-baseline retention
- **Pro:** Automated daily baselines, regression alerts (push when diff exceeds threshold), multi-baseline comparison (3+), baseline history export

---

## §7 Success Criteria

| Metric | Target |
|--------|--------|
| Baseline save time | <1s for 20 agents |
| Diff computation | <500ms for 20 agents |
| False regression alerts | <1 per week (worker config mismatch excluded) |
