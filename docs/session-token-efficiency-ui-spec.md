# Session Token Efficiency — UI/UX Improvement Spec

**Version:** 1.0  
**Date:** 2026-07-14  
**Author:** Spectrum  
**Status:** Proposal (not production-ready)

---

## Executive Summary

The current Session Token Efficiency tab shows a **static snapshot**: a model×archetype matrix with distribution histograms. This spec adds:

1. **Time trends** — efficiency over time (line/area charts)
2. **Pivot views** — switch between by-model, by-archetype, combined matrix
3. **Filters** — time period (7d/30d/all/custom) and minimum session threshold (n≥X)
4. **Actionable insights** — regression alerts, best/worst performers, drift detection

**Design principle:** Fewest components that deliver utility. Reuse existing design tokens. No new dependencies.

---

## Current State (Verified)

| Aspect | Current Implementation |
|--------|----------------------|
| **Data source** | `~/.hermes/state.db` — `sessions` table (id, model, started_at, ended_at) + `messages` table |
| **Sessions** | ~2939 total, spanning 1781768944 to 1784037642 epoch (~June 2025 – July 2026) |
| **Backend** | `src/observeco/dashboard/routes/efficiency.py` — `_build_model_archetype_matrix()` |
| **Frontend** | `src/observeco/dashboard/static/js/app.js` — `renderEffCellHistogram()` (Chart.js) |
| **Template** | `src/observeco/dashboard/templates/index_new.html` — Brain tab calls `/api/efficiency/brain` |
| **Metrics** | `src/observeco/efficiency/metrics.py` — 11 metrics + archetype + effectiveness |
| **Current cells** | 5 cells with n≥1; histogram guard at n≥5 (app.js:774) |

---

## Proposed Layout

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  📊 Session Token Efficiency  [fleet-wide · unattributed]                   │
├─────────────────────────────────────────────────────────────────────────────┤
│  [View: Matrix ▼]  [Period: Last 30d ▼]  [Min sessions: 5 ▼]  [⚙️ Alerts]  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  📈 Trend: Mean Efficiency Over Time                                │   │
│  │  [Line chart: X=day/week, Y=mean efficiency, one line per model]   │   │
│  │                                                                     │   │
│  │  Toggle: [All models] [Top 5] [Compare...]                         │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  🏆 Insights                                                        │   │
│  │  • deepseek-v4-flash ↑ 12pts (30d vs prior) — best improver        │   │
│  │  • debug archetype ↓ 8pts — regression alert ⚠️                     │   │
│  │  • 3 models crossed 80+ threshold this week                         │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  Model × Archetype Matrix (current view)                            │   │
│  │  ┌──────────┬─────────┬─────────┬─────────┬─────────┬─────────┐    │   │
│  │  │ Model    │ debug   │ research│ feature │ ops     │ edit    │    │   │
│  │  ├──────────┼─────────┼─────────┼─────────┼─────────┼─────────┤    │   │
│  │  │ model-a  │ 78 (n=) │ 82 (n=) │   —     │ 71 (n=) │   —     │    │   │
│  │  │ model-b  │   —     │ 65 (n=) │ 88 (n=) │   —     │ 79 (n=) │    │   │
│  │  └──────────┴─────────┴─────────┴─────────┴─────────┴─────────┘    │   │
│  │                                                                     │   │
│  │  Click cell → shows distribution histogram (existing behavior)     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## New Components

### 1. Filter Bar

**Location:** Below section header, above trend chart  
**Purpose:** Control what data is shown

| Control | Options | Default | Behavior |
|---------|---------|---------|----------|
| **View** | Matrix, By Model, By Archetype | Matrix | Switches primary visualization |
| **Period** | Last 7d, Last 30d, Last 90d, All time, Custom range | Last 30d | Filters sessions by `started_at` |
| **Min sessions** | Slider 1–20, or "All" | 5 | Hides cells/series with n < threshold |
| **Alerts** | Toggle on/off | Off | Shows regression/improvement callouts |

**Implementation:** Standard `<select>` elements + range slider, styled with ObserveCo tokens.

---

### 2. Trend Chart

**Type:** Line chart (Chart.js, existing dependency)  
**X-axis:** Time buckets (day for 7d/30d, week for 90d/all)  
**Y-axis:** Mean efficiency score (0–100)  
**Series:** One line per model (color-coded, max 8 visible, others grouped as "Other")

**Features:**
- Hover tooltip: date, model, mean efficiency, session count for that bucket
- Click legend item: toggle series visibility
- Annotations: mark significant events (e.g., "model update" if detected)
- Responsive: collapses to single series on mobile

**Data shape (backend response):**
```json
{
  "trend": {
    "labels": ["2026-06-15", "2026-06-16", ...],
    "datasets": [
      {"label": "deepseek-v4-flash", "data": [72, 74, 71, ...], "n": [12, 15, 8, ...]},
      {"label": "qwen3.5:latest", "data": [68, 69, 70, ...], "n": [5, 7, 6, ...]}
    ]
  }
}
```

---

### 3. Insights Panel

**Location:** Between trend chart and matrix  
**Purpose:** Surface actionable signals without user digging

**Alert types:**
| Type | Trigger | Display |
|------|---------|---------|
| **Regression** | Efficiency dropped ≥10pts vs prior period | Red text, ⚠️ icon |
| **Improvement** | Efficiency rose ≥10pts vs prior period | Green text, ↑ icon |
| **Threshold crossed** | Model/archetype crossed 80+ or fell below 50 | Blue text, 🏆 icon |
| **Low sample** | Previously n≥5, now n<5 (statistically thin) | Yellow text, ⚠️ icon |
| **New entrant** | Model/archetype combo with no prior data | Purple text, 🆕 icon |

**Implementation:** Static HTML list, regenerated on filter change. No real-time updates.

---

### 4. Pivot Selector

**Location:** Filter bar (View dropdown)  
**Purpose:** Change the primary grouping

| View | What it shows | Use case |
|------|---------------|----------|
| **Matrix** | Model × Archetype grid (current) | Compare performance across both dimensions |
| **By Model** | Ranked list of models with trend sparklines | "Which model should I use?" |
| **By Archetype** | Ranked list of archetypes with model breakdown | "How does my debugging efficiency compare to feature work?" |

**Implementation:** Client-side view switch using same underlying data, or refetch with `?view=model` param.

---

## Interaction Model

### Filter Change Flow

```
User changes filter (e.g., Period: Last 7d)
    ↓
Frontend debounces 150ms (prevent rapid-fire requests)
    ↓
GET /api/efficiency/brain?period=7d&min_n=5&view=matrix
    ↓
Backend queries state.db with time bucket + n threshold
    ↓
Frontend receives new data
    ↓
Re-render: trend chart → insights → matrix (in that order)
    ↓
Update URL query params (for shareability)
```

### Cell Click (existing, preserved)

```
User clicks matrix cell
    ↓
Dropdown selector populated (if multiple cells match)
    ↓
Histogram renders (existing Chart.js instance)
    ↓
Caption shows: n, mean, median, above/below mean, bookends
```

### Alert Dismissal

```
User clicks ⚠️ on regression alert
    ↓
Alert dismissed (localStorage: dismissed_alerts: {alert_id: timestamp})
    ↓
Same alert won't show for 7 days (configurable)
```

---

## Backend Requirements

### New API Parameters

`GET /api/efficiency/brain`

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `period` | string | `30d` | `7d`, `30d`, `90d`, `all`, or `custom` |
| `start` | epoch | (auto) | Custom period start (with `period=custom`) |
| `end` | epoch | (auto) | Custom period end (with `period=custom`) |
| `min_n` | int | `5` | Minimum session count to show cell/series |
| `view` | string | `matrix` | `matrix`, `model`, `archetype` |
| `group_by` | string | `day` | Time bucket: `day`, `week`, `month` |

### New Response Fields

Current response (preserved):
```json
{
  "empty": false,
  "models": [...],
  "archetypes": [...],
  "per_model": {...},
  "chart": {...},
  "cells": [...],
  "headline": "..."
}
```

**Add:**
```json
{
  "trend": {
    "labels": ["2026-06-15", ...],
    "datasets": [{"label": "...", "data": [...], "n": [...]}]
  },
  "insights": [
    {"type": "regression|improvement|threshold|low_sample|new",
     "subject": "deepseek-v4-flash",
     "dimension": "model|archetype",
     "message": "...",
     "delta": -12,
     "alert_id": "reg_deepseek-v4-flash_20260714"}
  ],
  "period": {
    "start": 1781768944,
    "end": 1784037642,
    "label": "Last 30d"
  }
}
```

---

## Data Availability Analysis

### What state.db Already Provides

| Data Need | Available? | Source |
|-----------|------------|--------|
| Session timestamps | ✅ | `sessions.started_at` (epoch) |
| Model per session | ✅ | `sessions.model` |
| Session messages | ✅ | `messages` table (session_id FK) |
| Efficiency computation | ✅ | `metrics.py` functions (compute_efficiency, classify_archetype) |

### What Requires New Queries

| Data Need | Gap | Solution |
|-----------|-----|----------|
| Time-bucketed aggregates | ❌ | New SQL: `GROUP BY strftime('%Y-%m-%d', started_at, 'unixepoch')` |
| Period-over-period comparison | ❌ | Two queries (current + prior period), compute delta in Python |
| Per-model time series | ❌ | `GROUP BY model, time_bucket` |
| Per-archetype time series | ❌ | Requires archetype classification per session, then group |
| Drift detection | ❌ | Compute rolling mean + std dev, flag outliers |

### SQL Patterns Needed

**Time-bucketed mean efficiency:**
```sql
SELECT
  strftime('%Y-%m-%d', started_at, 'unixepoch') AS day,
  model,
  AVG(efficiency_score) AS mean_eff,
  COUNT(*) AS n
FROM sessions s
JOIN efficiency_scores e ON s.id = e.session_id
WHERE started_at BETWEEN ? AND ?
GROUP BY day, model
ORDER BY day;
```

**Note:** This assumes an `efficiency_scores` table exists. Current implementation computes efficiency on-the-fly from session messages. **This is a key gap** — either:
1. Create a materialized `efficiency_scores` table (written when sessions complete), or
2. Accept slower queries (re-compute efficiency for all sessions in period on each request)

**Recommendation:** Option 1. Add a `efficiency_scores` table with columns:
- `session_id` (TEXT, FK)
- `agent_name` (TEXT)
- `archetype` (TEXT)
- `score` (REAL)
- `effectiveness_score` (REAL)
- `computed_at` (REAL)

This is already partially implemented in `metrics.py:325-332` (`_db.save_efficiency_score()`), but only fires when `agent_name != "unknown"`.

---

## Accessibility

- All charts: keyboard-navigable legend, screen-reader descriptions via `aria-label`
- Color choices: WCAG AA contrast (existing ObserveCo palette already compliant)
- Filters: `<label>` elements, proper `for` attributes
- Alerts: `role="alert"` for dynamic content, but don't auto-announce (user-initiated filter changes)

---

## Performance Targets

| Metric | Target |
|--------|--------|
| Initial load (all time, no filters) | <2s |
| Filter change (cached period) | <500ms |
| Filter change (uncached, custom range) | <2s |
| Max sessions scanned per request | 500 (configurable) |

**Optimization levers:**
- Cache period aggregates in memory (5min TTL)
- Limit scan to recent N sessions (configurable, default 500)
- Pre-compute efficiency scores at session end (not on read)

---

## Migration Path

**Phase 1 (backend-only):**
1. Add `period`, `min_n`, `view` params to `/api/efficiency/brain`
2. Implement time-bucketed queries
3. Add `trend` and `insights` to response

**Phase 2 (frontend):**
1. Add filter bar UI
2. Wire trend chart
3. Wire insights panel
4. Add pivot views

**Phase 3 (polish):**
1. Alert dismissal (localStorage)
2. URL state (query params for shareability)
3. Custom date range picker

---

## Out of Scope (For Now)

- Real-time updates (WebSocket push)
- Per-agent breakdown (blocked on Hermes emitting agent identity — obs-spec-083 §9)
- Export to CSV/PDF
- Saved views/favorites
- Anomaly detection ML (rule-based alerts are sufficient for v1)

---

## Assumptions

| Assumption | Risk if Wrong |
|------------|---------------|
| Efficiency scores are already being written to `efficiency_scores` table | May need to backfill or accept on-the-fly computation cost |
| Chart.js is already loaded (it is — `index_new.html:8`) | N/A — verified |
| Users care more about trends than absolute values | If wrong, trend chart is wasted real estate |
| 500-session scan limit is sufficient for "All time" view | May need to increase for long-running instances |

**Which ones are wrong?** Flag any assumption that doesn't match your deployment reality.

---

## Success Criteria

1. User can see efficiency trend for their primary model over last 30d
2. User can identify which archetype has the biggest regression this week
3. User can filter out statistically thin cells (n<5) without manual inspection
4. Load time remains acceptable (<2s) even with "All time" selected

---

*[End of spec]*
