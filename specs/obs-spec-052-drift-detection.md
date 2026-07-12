# obs-spec-052 — Drift Detection

**Spec ID:** obs-spec-052
**Title:** Drift detection — token composition drift, normalization, time-series visualization
**Status:** ✅ Live — v2 (2026-07-10)
**Owner:** Main
**Depends on:** obs-spec-050 (data model)
**Master plan ref:** v0.5.0 "Capability Monitoring Layer" · §3.5 Drift Analysis v2

---

## 1. Detection Algorithm

### 1.1 Data Source

Drift is computed from `chisel_trims` — periodic snapshots of each agent's token composition (identity, skills, memory, tools, guidance tokens). The watch daemon collects trims every 30s for active agents.

**Window bug (fixed in v2):** Previously used `get_trims(limit=50)` which capped the 7-day window to the last 50 entries. For fast-sampled agents (30s interval), 50 entries = 25 minutes. For slow-sampled agents (4-5h interval), 50 entries = 10+ days. **Fix:** Use time-based query (`WHERE timestamp > week_ago`) with no row limit.

### 1.2 Three Normalization Methods

Three independent methods are computed and stored. All use a 50-token floor on the denominator to prevent denominator amplification artifacts (e.g., hermes identity: 1→344 tokens = +4814% because week_avg=7).

#### Option A — Rolling Window (trajectory)

```
delta_tokens = current - week_avg
delta_pct    = (current - week_avg) / max(week_avg, 50) * 100
breach       = abs(delta_tokens) > 50 AND abs(delta_pct) > 10%
```

- **Measures:** "How different is today from the 7-day rolling average?"
- **Best for:** detecting sudden changes (restarts, config edits, one-time bloat)
- **Shows:** spike → decay as window catches up
- **Stored in:** `chisel_drift` with `method='rolling'`

#### Option B — Week-over-Week (sustained growth)

```
this_week_avg  = average of last 7 days of trim data
last_week_avg  = average of 7-14 days ago
delta_pct      = (this_week_avg - last_week_avg) / max(last_week_avg, 50) * 100
breach         = abs(this_week_avg - last_week_avg) > 50 AND abs(delta_pct) > 10%
```

- **Measures:** "Is the agent's brain permanently larger than last week?"
- **Best for:** detecting sustained growth (compounding cost problems)
- **Shows:** step change → stays flagged until next week
- **Stored in:** `chisel_drift` with `method='wow'`

#### Option C — Absolute Tokens (raw delta, no percentage)

```
delta_tokens = current - week_avg
breach       = abs(delta_tokens) > 50
```

- **Measures:** "How many more tokens is this agent using today vs its 7-day average?"
- **Best for:** honest cost visibility — a 50-token increase costs the same regardless of baseline
- **Shows:** raw token growth, no denominator artifacts, no math tricks
- **Stored in:** `chisel_drift` with `method='absolute'`

### 1.3 Thresholds

| Severity | Condition |
|----------|-----------|
| `breach` | abs(delta_tokens) > 50 AND abs(delta_pct) ≥ 10% |
| `warning` | abs(delta_tokens) > 30 AND abs(delta_pct) ≥ 5% |
| `info` | abs(delta_tokens) > 10 AND abs(delta_pct) ≥ 2% |

The absolute token check (`delta_tokens > 50`) prevents flagging tiny changes on near-zero baselines. Both conditions must be true.

### 1.4 DB Schema

```sql
-- Existing chisel_drift table (extended with method column)
CREATE TABLE IF NOT EXISTS chisel_drift (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_name TEXT NOT NULL,
    component TEXT NOT NULL,
    current_tokens INTEGER NOT NULL,
    week_avg_tokens INTEGER NOT NULL,
    delta_pct REAL NOT NULL,
    breached INTEGER NOT NULL DEFAULT 0,
    timestamp INTEGER NOT NULL,
    method TEXT NOT NULL DEFAULT 'rolling'  -- 'rolling' or 'wow'
);
CREATE INDEX IF NOT EXISTS idx_chisel_drift_agent_ts ON chisel_drift(agent_name, timestamp);
```

---

## 2. API Endpoints

### 2.1 `GET /api/drift-summary`

Returns HTML partial with per-agent sparklines (Option A) and week-over-week stat (Option B).

**Response:** HTML with embedded Chart.js sparklines. Each row shows:
- Agent name + most-drifted component
- Canvas sparkline (7-day trajectory, Option A)
- Peak drift, current drift, breach count
- Week-over-week delta (Option B) as secondary stat

### 2.2 `GET /api/drift-summary?method=wow`

Returns HTML partial with week-over-week comparison as primary view.

---

## 3. Dashboard Components

### 3.1 Drift Tab (✅ Live — v2)

- **Header:** "Drift Timeline · N agents · X with breaches · 7-day sparklines"
- **Per-agent row:** Agent name, component label, sparkline canvas, peak/current/breach stats
- **Sparkline:** Chart.js line chart with gradient fill, bezier curves, retina-crisp
- **Tooltip:** HTML tooltip positioned outside canvas — shows date + delta% on hover
- **Axis labels:** Actual date range (e.g., "Jul 03" → "Jul 10")
- **Week-over-week stat:** Shown as secondary text in each row

### 3.2 Compare Tab (unchanged)

Side-by-side table showing current snapshot: Agent, Framework, Tokens, Composition bar, Drift %, Errors, Circuit, Last seen. No overlap with Drift tab (snapshot vs trajectory).

---

## 4. Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Denominator artifacts | Zero false breaches from near-zero baselines | Audit of 100 drift events |
| Window consistency | All agents use same 7-day window | Verify query uses time-based filter, not row limit |
| WoW accuracy | Step changes detected within 1 day | Manual verification of known changes |

---

## 5. File Changes

| File | Change |
|------|--------|
| `src/observeco/watch_consumers.py` | Fix window bug: replace `limit=50` with time-based query. Add 50-token floor. Add Option B computation. |
| `src/observeco/chisel/drift.py` | Add 50-token floor. Add Option B computation. |
| `src/observeco/db.py` | Add `get_trims_since()` method. Add `method` column to `log_drift()`. |
| `src/observeco/dashboard/server.py` | Update `/api/drift-summary` to show both Option A and Option B. |
| `src/observeco/dashboard/templates/index_new.html` | Update Drift tab description. |
