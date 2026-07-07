# obs-spec-052 — Drift Detection

**Spec ID:** obs-spec-052
**Title:** Drift detection — statistical comparison, alerting, shareable chart
**Status:** DRAFT
**Owner:** Main
**Depends on:** obs-spec-050 (data model), obs-spec-051 (canary runner)
**Master plan ref:** v0.5.0 "Capability Monitoring Layer"

---

## 1. Detection Algorithm

### 1.1 Trigger

Drift is checked after every canary run completes. The `CanaryRunner` calls `BaselineManager.compare()` which:

1. Loads the active baseline for this agent + config_hash
2. Compares current run accuracy vs baseline accuracy
3. Computes: drift_pct, p_value (two-sample z-test), 95% CI
4. If |drift_pct| > threshold AND p < 0.05 → emit drift_event

### 1.2 Thresholds

| Severity | Condition |
|----------|-----------|
| `breach` | |drift_pct| ≥ 5% AND p < 0.01 |
| `warning` | |drift_pct| ≥ 3% AND p < 0.05 |
| `info` | |drift_pct| ≥ 1% AND p < 0.05 |

Configurable via `~/.observeco/config.json` (existing config mechanism):

```json
{
  "drift": {
    "threshold_breach": 5.0,
    "threshold_warning": 3.0,
    "threshold_info": 1.0,
    "p_value_breach": 0.01,
    "p_value_warning": 0.05,
    "min_runs_for_baseline": 3
  }
}
```

### 1.3 Per-Task Drift

In addition to aggregate drift, each task is compared individually:

- Same z-test on per-task accuracy across trials
- Tasks with |drift| > threshold are flagged in `drift_events.breached_tasks`
- The drift chart shows per-task breakdown (baseline vs current, Δ, trend bar)

---

## 2. API Endpoints

### 2.1 `GET /api/capability/drift?agent=NAME`

Returns latest drift events for an agent. **Note:** This is a new endpoint under the `/api/capability/` prefix. The existing `/api/drift-summary` endpoint (server.py:3153) serves context drift data and is separate from the capability drift system.

```json
{
  "agent": "Main",
  "current": {
    "accuracy": 79.2,
    "ci": [76.1, 82.3],
    "run_id": "uuid",
    "date": "2026-07-02"
  },
  "baseline": {
    "accuracy": 82.4,
    "ci": [80.1, 84.7],
    "run_count": 5,
    "date": "2026-06-18"
  },
  "drift": {
    "pct": -3.2,
    "p_value": 0.003,
    "ci": [-5.1, -1.3],
    "severity": "breach"
  },
  "tasks": [
    {"name": "Chart interpretation", "baseline": 46.3, "current": 34.0, "delta": -12.3, "severity": "breach"},
    {"name": "Summarize conversation", "baseline": 80.5, "current": 76.0, "delta": -4.5, "severity": "warning"}
  ]
}
```

### 2.2 `GET /api/capability/drift/history?agent=NAME&days=14`

Returns time series for the drift chart:

```json
{
  "points": [
    {"date": "2026-06-19", "accuracy": 82.1, "baseline": 82.4},
    {"date": "2026-06-20", "accuracy": 82.8, "baseline": 82.4},
    ...
  ],
  "baseline": {"value": 82.4, "start": "2026-06-18", "end": "2026-06-25"},
  "drift_events": [
    {"date": "2026-07-02", "pct": -3.2, "severity": "breach"}
  ]
}
```

---

## 3. Dashboard Components

### 3.1 Drift Chart (Chart.js)

New dependency: Chart.js v4.4.0. The chart from Spectrum's mockup maps directly:

- Line chart: accuracy over time (green line)
- Dashed line: baseline (grey, constant)
- Shaded zones: baseline period (green tint), drift period (red tint)
- Annotation arrow: "▼ -3.2% drift · p=0.003"
- Y-axis: 70–90% range

### 3.2 Drift Hero Section

- Badge: "🔴 Drift detected · 3.2% drop over 14 days"
- Headline: "Config unchanged, quality dropped 3.2%"
- Subhead: "Same model, same prompt, same tools — but accuracy is declining."
- Meta: baseline date, window, run count, p-value

### 3.3 Summary Cards

Three cards: Baseline Accuracy, Current Accuracy, Drift Magnitude (with CI).

### 3.4 Per-Task Drift Table

Columns: Task, Baseline, Current, Δ, Trend bar (width = |drift|), Status (breach/warning/stable).

### 3.5 Action Buttons

- "📊 Grid Report" → navigates to grid report section in dashboard (same page, scroll to `#grid-report`)
- "🔄 Re-run Canary" → triggers immediate canary run via `POST /api/capability/canary/run`
- "🔔 Create Alert" → opens alert creation flow. **Note:** The alert creation dialog is a new component to be built as part of this spec (the existing alert system has push endpoints but no creation UI).

### 3.6 Shareable View (Gladwell Fix #4)

Add a "📸 Share" button that opens a modal with:
- Headline only
- Chart (baseline zone → drift zone)
- Drift arrow with p-value
- No chrome, no table, no buttons
- "Copy to clipboard" or "Download as PNG" action

**Implementation:** The shareable view is a CSS-only overlay. Same chart canvas, just hides surrounding elements. Use native `canvas.toDataURL()` for PNG export (zero new dependencies).

---

## 4. Triage Path (Gladwell Fix #5)

Add a subtle "Triage path" section below the drift hero:

```
1. Check config timeline → was there an intentional change?
2. Re-run canary → is the drift real or noise?
3. Run grid report → which config performs best now?
4. Create alert → get notified if it gets worse
```

Collapsed by default, expandable via "💡 Triage path" toggle.

---

## 6. Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Drift detection FPR | False positive rate < 5% | Manual audit of first 100 drift events |
| Drift detection latency | < 1s after canary run | Time from run complete to drift_event |
| Shareable view load | < 500ms | Modal open time |
| Triage path discoverability | User finds it within 3 clicks | UX test |

---

## 7. Dashboard State Table

| Component | Loading State | Empty State | Error State |
|-----------|-------------|-------------|-------------|
| Drift hero section | Skeleton text "Checking for drift..." | "No drift detected — run a canary to establish a baseline" | "Drift check failed — run canary manually" |
| Drift chart | Chart.js placeholder with spinner | "Not enough data — canary has run 2/5 times needed for baseline" | "Chart data unavailable — check server logs" |
| Summary cards | Skeleton cards (grey bars) | "No baseline data yet" | "Error computing summary" |
| Per-task drift table | Skeleton rows (3 grey lines) | "Run a canary to see per-task drift" | "Task data unavailable" |
| Shareable view modal | Spinner overlay | N/A (only opens when drift exists) | "Could not generate shareable view" |

---

## 8. File Changes

| File | Change |
|------|--------|
| `src/observeco/capability/drift.py` | New — DriftDetector, statistical comparison |
| `src/observeco/dashboard/server.py` | Add `/api/capability/drift` routes |
| `src/observeco/dashboard/templates/index.html` | Add drift chart section, shareable view |
| `src/observeco/db.py` | Add drift_events queries |
