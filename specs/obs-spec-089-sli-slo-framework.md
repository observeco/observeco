# obs-spec-089: SLI/SLO Framework + Burn-Rate Alerts

**Status:** 🔴 Spec (2026-07-20) — New
**Product:** ObserveCo (Free + Pro)
**Depends on:** obs-spec-050 (data model), existing `compute_l2_baselines()`, existing `drift_events` table
**Owner:** Main

---

## §1 Problem

ObserveCo has binary alive/dead health and per-agent baselines (RSS, P95, error rate) but **no quantified reliability targets**. Every observability platform (Grafana, Datadog, SigNoz) has SLI/SLO — without it, ObserveCo is a monitoring tool, not an observability platform.

**Gap:** You can see "agent X is alive" but not "agent X has 99.2% uptime this month, consuming 8% of its error budget." You can see "error rate spiked" but not "burn rate is 3x the allowable threshold — escalate."

---

## §2 Architecture

### §2.1 SLI Definitions (3 core + extensible)

| SLI | Source | Window | Default Target |
|-----|--------|--------|----------------|
| **Uptime** | `pulse_log` — alive/total probes | 30d rolling | 99.5% |
| **Error rate** | `errors` — error count / total turns | 30d rolling | <5% |
| **Latency P95** | `pulse_log` — latency_ms | 30d rolling | <5s |

Extensible via config: users define custom SLIs from any numeric column in pulse_log, errors, or token_logs.

### §2.2 SLO Targets

Stored in new `slo_targets` table:

```sql
CREATE TABLE IF NOT EXISTS slo_targets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_name TEXT NOT NULL,
    sli_name TEXT NOT NULL,          -- 'uptime' | 'error_rate' | 'latency_p95' | custom
    target_pct REAL NOT NULL,        -- e.g. 99.5 for 99.5%
    window_days INTEGER NOT NULL DEFAULT 30,
    burn_rate_warning REAL DEFAULT 2.0,   -- 2x burn rate → warning
    burn_rate_critical REAL DEFAULT 5.0,  -- 5x burn rate → critical
    enabled INTEGER NOT NULL DEFAULT 1,
    created_at INTEGER NOT NULL,
    UNIQUE(agent_name, sli_name)
);
```

### §2.3 Error Budget

Computed per SLO per window:

```
error_budget_total = total_events * (1 - target_pct)
error_budget_consumed = failing_events
error_budget_remaining = error_budget_total - error_budget_consumed
burn_rate = error_budget_consumed / (elapsed_time / window_time * error_budget_total)
```

### §2.4 Burn-Rate Alerts

Multi-window approach (standard practice):

| Window | Burn Rate | Action |
|--------|-----------|--------|
| 1h | ≥2x | Warning alert |
| 1h | ≥5x | Critical alert |
| 6h | ≥2x | Warning alert |
| 6h | ≥5x | Critical alert |

Alerts fire into the existing `alert_delivery_log` and `alert_subscriptions` system. No new delivery infra needed.

### §2.5 Dashboard Display

- **Fleet card:** SLO badge per agent (🟢 99.2% / 🟡 97.1% / 🔴 94.5%)
- **Agent detail:** SLO tab with per-SLI time-series + error budget gauge
- **Fleet view:** SLO compliance summary row (X agents meeting SLO, Y breaching)

---

## §3 Implementation

### Phase 1: Backend (~200 lines)

| File | Change |
|------|--------|
| `db.py` | Add `slo_targets` table, `get_slo_targets()`, `set_slo_target()`, `compute_sli()`, `compute_error_budget()`, `compute_burn_rate()` |
| `capability/sli_slo.py` | New file: SLI computation from pulse_log/errors, SLO evaluation, burn rate calculation, alert trigger |
| `watch_consumers.py` | Add SLO evaluation tick (every 5min, lightweight — reads from pre-computed aggregates) |

### Phase 2: Dashboard (~100 lines)

| File | Change |
|------|--------|
| `dashboard/server.py` | Add `/api/slo-summary`, `/api/slo-detail/{agent}` endpoints |
| `dashboard/templates/` | SLO badge in fleet card, SLO tab in agent detail modal |

### Phase 3: CLI (~50 lines)

| File | Change |
|------|--------|
| `cli.py` | Add `observeco slo list/set/show` commands |

---

## §4 Edge Cases

- **Cold start:** First 24h has insufficient data — show "collecting..." instead of 0%
- **Agent with no pulse data:** SLO shows N/A, not 0%
- **Window transition:** At window boundary, old data drops off — SLO may jump. Show both current and trailing-7d for stability
- **Burn rate on low-traffic agents:** <100 events in window → burn rate is unreliable. Show "insufficient data" instead of false alarm
- **Multiple SLIs per agent:** Each evaluated independently. Agent is "breaching SLO" if any SLI fails

---

## §5 Pro Gating

- **Free:** 3 core SLIs (uptime, error rate, latency P95), 7d window, dashboard display
- **Pro:** Custom SLIs, configurable windows (30d/90d), burn-rate alerts, multi-window detection, SLO history export

---

## §6 Success Criteria

| Metric | Target |
|--------|--------|
| SLI computation accuracy | Within 1% of manual count on 1000-event sample |
| Burn rate false positives | <1 per agent per week |
| Dashboard render time | <200ms for 20 agents |
