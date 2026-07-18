# obs-spec-054 — Grid Report

**Spec ID:** obs-spec-054
**Title:** Grid report — model × config comparison matrix
**Status:** DRAFT
**Owner:** Main
**Depends on:** obs-spec-050 (data model), obs-spec-051 (canary runner)
**Master plan ref:** v0.5.0 "Capability Monitoring Layer"

---

## 1. What It Is

A matrix of (model × config) cells, each showing per-task accuracy with CI, flags, and cost. The grid decomposes model capability from harness quality — the user reads by pairing, not by isolated component.

---

## 2. CLI Entry Point

```
observeco grid run [--agent AGENT] [--models MODELS] [--configs CONFIGS] [--tasks TASKS]
observeco grid list [--agent AGENT]
observeco grid compare [--run-id ID] [--baseline]
```

- `grid run` — runs the full grid: all models × all configs × all tasks
- `grid list` — shows recent grid runs
- `grid compare` — compares two grid runs or a run against baseline

---

## 3. Runner

The existing codebase has a `GridRunner` in `benchmark/grid/runner.py` that uses τ-bench environments (retail/airline). This spec defines a **new** `CapabilityGridRunner` for the capability monitoring system, separate from the τ-bench GridRunner. The two serve different purposes: τ-bench GridRunner tests agent performance on standard benchmarks; CapabilityGridRunner tests agent performance on user-defined canary tasks across model×config combinations.

Reuses `CanaryRunner` internally:

```python
class CapabilityGridRunner:
    def __init__(self, db, canary_runner):
        self.db = db
        self.canary = canary_runner

    def run(self, agent_name, models, configs, tasks=None):
        # For each (model, config) pair:
        #   1. Temporarily switch agent config
        #   2. Run canary suite (3 trials per task)
        #   3. Aggregate per-task accuracy = mean across trials
        #   4. CI computed from trial-level data via bootstrap (same method as canary)
        #   5. Store aggregate in grid_results (one row per task×model×config)
        # Return GridReport
        pass
```

**Default models:** deepseek-v4-flash, deepseek-v4-pro, ornith:latest
**Default configs:** baseline-v3, baseline-v2
**Default tasks:** all 9 canary tasks

---

## 4. API Endpoint

### `GET /api/capability/grid?agent=NAME&run_id=ID`

```json
{
  "agent": "Main",
  "run_id": "uuid",
  "date": "2026-07-02",
  "models": ["deepseek-v4-flash", "deepseek-v4-pro", "ornith:latest"],
  "configs": ["baseline-v3", "baseline-v2"],
  "tasks": ["Extract structured data", "Follow multi-step instructions", ...],
  "cells": [
    {
      "task": "Extract structured data",
      "model": "deepseek-v4-flash",
      "config": "baseline-v3",
      "accuracy": 92.0,
      "ci_lower": 88.0,
      "ci_upper": 96.0,
      "cost": 0.004,
      "flags": [],
      "hang": false
    },
    ...
  ],
  "summary": "Read by pairing: deepseek-v4-flash × baseline-v3 wins on cost-adjusted accuracy. deepseek-v4-pro × baseline-v3 wins on raw accuracy but costs 6× more. ornith:latest trails on all configs."
}
```

---

## 5. Dashboard Component

### 5.1 Controls

- Agent selector (dropdown)
- Config filter (dropdown: All / baseline-v3 / baseline-v2)
- Show filter (dropdown: All / Passing only / Failing only)
- Export CSV button

### 5.2 Grid Table

**Header rows:**
- Row 1: Model name + config label (colspan=3 per model)
- Row 2: Acc (CI) | Flags | Cost (repeated per model)

**Body rows:** One per task. Each cell shows:
- Accuracy with CI: `92% [88–96]` (color-coded: green ≥80%, yellow ≥60%, red <60%)
- Flags column: `—` or 🔄 (loop) or ⚠️ (unsafe) or 🔵 (shortcut)
- Cost: `$0.004`

**Hang cells:** Show "Hang" instead of accuracy, no CI.

### 5.3 Footer

"Read by pairing" guidance text (from Gladwell Fix #3):

> **Read by pairing:** deepseek-v4-flash × baseline-v3 wins on cost-adjusted accuracy. deepseek-v4-pro × baseline-v3 wins on raw accuracy but costs 6× more. ornith:latest trails on all configs. — Model and harness interact; read grid by pairing, not isolated components.

### 5.4 "Run Full Grid" Button

Triggers a new grid run. Shows a spinner progress indicator during execution (use existing htmx polling pattern to refresh status every 5s until complete).

---

## 6. ponytail: Grid runs are sequential (one model × config at a time). For 3 models × 2 configs × 9 tasks × 3 trials = 162 individual task runs, this could take 30+ minutes. Upgrade path: parallelize by model (each model runs in a separate subprocess), then add a progress bar.

**Note on `hang` field:** `grid_results.hang` is stored as INTEGER (0/1) in SQLite. The API serializes this to JSON boolean (`true`/`false`). The mockup shows `—` for no hang, 🔄 for loop, ⚠️ for unsafe — these are the `flags` column, not `hang`.

---

## 7. Template Strategy Note

The dashboard template (`dashboard/templates/index.html`) is a 6,525-line monolith (336KB). All capability monitoring sections (drift chart, grid table, timeline, task editor) should be added as new sections within this file, using unique `id` attributes for anchor navigation:

- `#drift-chart` — drift detection section
- `#grid-report` — grid report section
- `#config-timeline` — config timeline section
- `#task-editor` — task definition section

Each section is a self-contained `<div>` with its own htmx triggers. No section depends on another section's DOM state. This keeps the monolith approach workable while avoiding cross-section coupling. A future refactor may split into separate template files with server-side includes.

---

## 9. Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Grid report load | < 2s for 9 tasks × 4 configs | Dashboard render time |
| Grid run completion | 162 cells in < 30 min | `grid_runs.completed_at - started_at` |
| CSV export | < 1s for full grid | Export button response time |

---

## 10. Dashboard State Table

| Component | Loading State | Empty State | Error State |
|-----------|-------------|-------------|-------------|
| Grid controls | Dropdowns greyed out, "Loading..." | "No agents available" | "Could not load filters" |
| Grid table | Skeleton table (3 rows × 4 columns of grey bars) | "No grid runs yet — run a grid to compare models and configs" | "Grid data unavailable — run grid again" |
| Footer summary | "Computing summary..." | "Run a grid to see comparison" | "Summary unavailable" |
| "Run Full Grid" button | Shows spinner, disabled during run | "Run Full Grid" (enabled) | "Grid run failed — retry" |

---

## 11. File Changes

| File | Change |
|------|--------|
| `src/observeco/capability/grid.py` | New — GridRunner |
| `src/observeco/cli.py` | Add `grid` command group |
| `src/observeco/dashboard/server.py` | Add `/api/capability/grid` route |
| `src/observeco/dashboard/templates/index.html` | Add grid report section |
