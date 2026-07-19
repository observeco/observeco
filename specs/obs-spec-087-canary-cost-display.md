# obs-spec-087 — Canary Cost & Token Display in Dashboard

**Spec ID:** obs-spec-087
**Title:** Display real cost and token data from canary runs in the dashboard
**Status:** ✅ IMPLEMENTED (2026-07-19)
**Owner:** Main
**Depends on:** obs-spec-086 (canary cost tracking — adapter now returns cost/tokens)
**Master plan ref:** v0.6.0 "Agent Quality Management"
**Created:** 2026-07-19

---

## 1. Problem Statement

The Hermes adapter now returns real cost and token data from canary runs (obs-spec-086). The data is stored in `canary_runs.total_cost` and `canary_runs.total_tokens`, and in `canary_results.cost` and `canary_results.tokens` per-task. But the dashboard never reads or renders these fields.

**Current dashboard displays:**
- Fleet card (Quality Benchmark modal): Pass Rate, Accuracy, Hangs, Recovery — no cost/tokens
- Fleet row (agent card): accuracy %, pass count — no cost/tokens
- QB categories endpoint: per-category accuracy breakdown — no cost/tokens
- Per-task drift chart: accuracy time-series — no cost/tokens

**Impact:** Users see "Cost: $0.0000" in the CLI output but the dashboard shows no cost information. The blended score in the harness optimizer (`cost_lambda * tokens/1M`) is invisible.

---

## 2. Design

### 2.1 Fleet Card — Add Cost & Token Stats

**File:** `src/observeco/dashboard/routes/fleet.py` — `_canary_card()` function

**Change:** Add `total_cost` and `total_tokens` to the SQL query (line 401-402), then render two new stat boxes in the card HTML.

```python
# Current query (line 401):
"SELECT id, pass_count, fail_count, hang_count, total_tasks, "
"started_at, config_hash FROM canary_runs "

# New query:
"SELECT id, pass_count, fail_count, hang_count, total_tasks, "
"started_at, config_hash, total_cost, total_tokens FROM canary_runs "
```

Add two new stat boxes after the existing "Recovery" stat:

```html
<div class="canary-stat">
  <div class="canary-stat-num">${cost:.4f}</div>
  <div class="canary-stat-label">Cost</div>
</div>
<div class="canary-stat">
  <div class="canary-stat-num">{fmt_tokens(tokens)}</div>
  <div class="canary-stat-label">Tokens</div>
</div>
```

Use the existing `_fmt_tokens()` helper (used by the Brain row) for token formatting. Cost formatted as `$0.0402` (4 decimal places, always shows cents).

**Layout:** 6 stat boxes in a 3×2 grid (currently 4 in a 2×2). The card is already responsive — adding 2 more boxes fits the existing grid pattern.

### 2.2 Fleet Row — Add Cost to Quality Benchmark Row

**File:** `src/observeco/dashboard/routes/fleet.py` — `_canary_row()` and `_canary_pass_sub()` functions

**Change:** Add cost to the row-sub text alongside the pass count.

```python
# _canary_row currently returns just accuracy %:
# '<span class="row-val" style="color:{color}">{acc:.0f}%</span>'

# New: add cost indicator
cost_str = f'${canary_row["total_cost"]:.2f}' if canary_row.get("total_cost") else ''
return f'<span class="row-val" style="color:{color}">{acc:.0f}%</span> <span class="row-sub-cost">{cost_str}</span>'
```

And in `_canary_pass_sub`, add cost to the pass count text:

```python
# Current:
parts = f'{canary_row["pass_count"]}/{canary_row["total_tasks"]} pass{hang_str}'

# New (fleet row uses 2 decimal places per §6 constraint):
cost_str = f' · ${canary_row["total_cost"]:.2f}' if canary_row.get("total_cost") else ''
parts = f'{canary_row["pass_count"]}/{canary_row["total_tasks"]} pass{hang_str}{cost_str}'
```

**Note:** The fleet row query at line 402 already selects from `canary_runs` — just needs `total_cost` and `total_tokens` added to the SELECT.

### 2.3 QB Categories Endpoint — Add Cost Per Category

**File:** `src/observeco/dashboard/routes/fleet_qb.py` — `qb_categories()` function

**Change:** Add `cost` and `tokens` to the per-category breakdown. The query at line 27-32 joins `canary_results` with `canary_tasks` — add `cr.cost` and `cr.tokens` to the SELECT.

```python
# Current query:
"SELECT cr.accuracy, cr.status, ct.category, ct.difficulty, ct.name as task_name, "
"cr.error, cr.id as result_id "

# New query:
"SELECT cr.accuracy, cr.status, ct.category, ct.difficulty, ct.name as task_name, "
"cr.error, cr.id as result_id, cr.cost, cr.tokens "
```

Add cost/token aggregation to the category data:

```python
cat_data[cat]["cost"] += r["cost"] or 0.0
cat_data[cat]["tokens"] += r["tokens"] or 0
```

And include in the response:

```python
categories = sorted(
    [{"name": c, "pass": d["pass"], "total": d["total"], "accuracy": ...,
      "cost": round(d["cost"], 6), "tokens": d["tokens"]}
     for c, d in cat_data.items()],
    ...
)
```

### 2.4 Per-Task Drift Chart — Add Cost Per Run

**File:** `src/observeco/dashboard/routes/capability.py` — per-task drift endpoint (line 1096)

**Change:** Add `total_cost` and `total_tokens` to the runs query.

```python
# Current:
"SELECT id, started_at FROM canary_runs "

# New:
"SELECT id, started_at, total_cost, total_tokens FROM canary_runs "
```

Include in the response so the frontend can display cost per run in the chart tooltip.

### 2.5 Frontend Template — No Changes Needed

The fleet card and fleet row are rendered server-side as HTML partials (FastAPI `HTMLResponse`). The QB categories and per-task drift chart are JSON endpoints consumed by JavaScript in `index_new.html`. No template changes needed — the data flows through existing rendering paths.

---

## 3. Migration

No schema changes. All columns (`total_cost`, `total_tokens` in `canary_runs`; `cost`, `tokens` in `canary_results`) already exist from obs-spec-050.

---

## 4. CLI

No CLI changes. The CLI already displays cost/tokens in the canary report output (verified in obs-spec-086).

---

## 5. Verification

1. Open dashboard → fleet view → check Quality Benchmark row shows cost
2. Click agent card → Quality Benchmark modal → check canary card shows Cost and Tokens stats
3. Click "View details" → per-category breakdown shows cost per category
4. Check per-task drift chart tooltip shows cost per run
5. Run `observeco canary run --agent default --tasks arithmetic-reasoning` → verify CLI shows cost, then refresh dashboard to see it appear

---

## 6. Constraints

| # | Constraint | Type | Description |
|---|------------|------|-------------|
| 1 | Zero-cost runs | MUST | Show "$0.00" for runs with no cost data (historical runs before obs-spec-086). Don't hide the stat — it's useful to know cost tracking is active. |
| 2 | Cost formatting | MUST | Fleet card: 4 decimal places (`$0.0402`). Fleet row: 2 decimal places (`$0.04`). Tokens: use `_fmt_tokens()` helper (K/M suffix). |
| 3 | Null handling | MUST | `total_cost` and `total_tokens` can be NULL for historical runs. Default to 0.0/0 in display. |
| 4 | Responsive layout | SHOULD | 6 stat boxes in the canary card should wrap to 3×2 on narrow screens. Test at 320px width. |

---

## 7. Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| Card layout breaks with 6 stats | Low | The card uses CSS grid with `grid-template-columns: 1fr 1fr`. Adding 2 more children just adds 2 more cells. Test at narrow widths. |
| Cost formatting inconsistent | Low | Use the same `_fmt_tokens()` helper already used by the Brain row. Cost formatting is a simple f-string. |
| Historical runs show $0.00 | Low | Correct behavior — they have no cost data. The stat shows cost tracking is active. |

---

## 8. File Changes

| File | Change | Type |
|------|--------|------|
| `src/observeco/dashboard/routes/fleet.py` | Add `total_cost`, `total_tokens` to canary card query + render 2 new stat boxes | Modify |
| `src/observeco/dashboard/routes/fleet.py` | Add `total_cost` to fleet row query + display in `_canary_row()` and `_canary_pass_sub()` | Modify |
| `src/observeco/dashboard/routes/fleet_qb.py` | Add `cr.cost`, `cr.tokens` to query + include in category response | Modify |
| `src/observeco/dashboard/routes/capability.py` | Add `total_cost`, `total_tokens` to per-task drift runs query | Modify |
| `specs/obs-spec-087-canary-cost-display.md` | This spec | New |
| `specs/observeco-master-plan.md` | Add row for obs-spec-087 | Modify |
