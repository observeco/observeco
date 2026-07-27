# obs-spec-058 — Per-Task Drift Chart

**Spec ID:** obs-spec-058
**Title:** Per-task accuracy time-series chart with category filters and LLM judge reasoning
**Status:** ✅ Live (2026-07-10)
**Owner:** Main
**Depends on:** obs-spec-050 (data model), obs-spec-052 (drift detection)
**Master plan ref:** v0.5.0 "Capability Monitoring Layer" · Mockup A (drift-chart-mockup.html)

---

## 1. What It Is

A multi-line Chart.js chart showing per-task accuracy over time, replacing the single aggregate accuracy line with 9 task-level trend lines. Each task gets its own colored line, severity-tagged in the legend, with category filter chips and click-to-inspect LLM judge reasoning.

---

## 2. Data Endpoint

### `GET /api/capability/drift/per-task-history?agent=NAME&days=21`

Returns per-task accuracy time series:

```json
{
  "tasks": [
    {
      "task_id": "arithmetic-reasoning",
      "name": "Arithmetic reasoning",
      "category": "reasoning",
      "difficulty": "easy",
      "points": [
        {"date": "2026-07-01", "accuracy": 85.0},
        {"date": "2026-07-02", "accuracy": 82.0}
      ],
      "baseline": 83.5,
      "current": 82.0,
      "delta": -1.5,
      "severity": "stable"
    }
  ]
}
```

**Implementation:** `src/observeco/dashboard/routes/capability.py` — `per_task_drift_history()` at `/api/capability/drift/per-task-history`. Queries `canary_results` joined with `canary_runs` and `canary_tasks`, groups by `task_id`, computes baseline (mean of first half of points), current (mean of second half), delta, and severity.

**Category inference:** `canary_tasks.category` column may not exist in all schemas. A `_infer_category()` heuristic maps task names to categories (reasoning, coding, extraction, tool_use, instruction_following, safety) based on keyword matching. Upgrade path: `ALTER TABLE canary_tasks ADD COLUMN category TEXT`.

---

## 3. Dashboard Component

### 3.1 Toggle

Hidden by default under a "📈 Show per-task breakdown" button below the aggregate drift chart. Clicking toggles visibility and lazy-loads the data.

### 3.2 Category Filter Chips

Pill-style chips at the top: "All Tasks" (default active) + one chip per detected category. Clicking a chip filters the chart to show only tasks in that category.

### 3.3 Multi-Line Chart

Chart.js line chart with:
- One line per task, each with a distinct color from a 9-color palette
- Bezier curve tension (0.3) for smooth lines
- Y-axis: 0–100% accuracy
- X-axis: date labels
- Hover tooltip showing task name + accuracy %
- Click legend item to toggle individual task visibility

### 3.4 Legend

Below the chart, each task shown with:
- Color dot matching the line
- Task name
- Severity tag if breached/warning: `BREACH -12%` (red) or `WARNING -4.5%` (amber)
- Click to toggle visibility (opacity 0.4 when hidden)

### 3.5 Detail Panel (Future)

Clicking a task line opens a detail panel showing:
- Task name
- Baseline accuracy %, Current accuracy %, Drift %
- LLM judge reasoning (loaded from `/api/capability/canary/judge-reasoning?task_id=X`)

**Status:** Panel container exists but judge reasoning loading is deferred — the endpoint exists but the click-to-load wiring is not yet connected.

---

## 4. Interaction Design

| Action | Result |
|--------|--------|
| Click "Show per-task breakdown" | Lazy-loads data, renders chart + legend |
| Click category chip | Filters chart to that category's tasks |
| Click legend item | Toggles that task's line visibility |
| Hover any data point | Tooltip shows task name + accuracy % |
| Click task line (future) | Opens detail panel with judge reasoning |

---

## 5. Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Chart render time | < 1s for 9 tasks × 21 days | Browser DevTools |
| Filter response | Instant (client-side) | No network call |
| Data load | < 500ms for 9 tasks | API response time |

---

## 6. File Changes

| File | Change |
|------|--------|
| `src/observeco/dashboard/routes/capability.py` | Add `/api/capability/drift/per-task-history` endpoint + per-task chart HTML/JS in `drift_chart_partial()` |
| `src/observeco/capability/drift.py` | Add `get_per_task_history()` method to `DriftDetector` |
