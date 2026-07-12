# obs-spec-059 — Quality Benchmark Card Row

**Spec ID:** obs-spec-059
**Title:** Quality benchmark card row in fleet view — per-category accuracy with expandable detail
**Status:** ✅ Live (2026-07-10)
**Owner:** Main
**Depends on:** obs-spec-050 (data model), obs-spec-051 (canary runner)
**Master plan ref:** v0.5.0 "Capability Monitoring Layer" · Mockup B (qb-card-row-mockup.html)

---

## 1. What It Is

A compact quality benchmark row in each fleet agent card, showing overall canary accuracy with an expandable per-category breakdown. Implements Variant C from the mockup (Expandable Detail Row).

---

## 2. Fleet Card Row

### 2.1 Collapsed State

Each agent card shows a `QUALITY BENCHMARK` row with:
- **Label:** "QUALITY BENCHMARK" (left-aligned)
- **Accuracy %:** Color-coded: green ≥70%, amber ≥40%, red <40%
- **Sub-text:** Pass count / total tasks (e.g., "5/9 pass") + hang count if any
- **Chevron:** ▼ indicating expandability
- **Drift indicator:** If a drift event exists, shows drift severity badge

### 2.2 Empty State

If no canary runs exist: shows "no data" with a "▶ Run" button that triggers a canary run.

### 2.3 Running State

If a canary is currently running: shows "⏳" with "running" sub-text.

### 2.4 Expanded State

Clicking the row toggles a detail panel showing:
- Per-category table: category name, pass/fail count, accuracy %
- Judge reasoning snippet for the worst-performing task
- Data loaded via htmx from `/api/capability/canary/card?agent=NAME`

---

## 3. Data Source

Queries `canary_runs` + `canary_results` + `canary_tasks` for the latest completed run per agent. Per-category accuracy computed by grouping results by `canary_tasks.category`.

---

## 4. Interaction Design

| Action | Result |
|--------|--------|
| Click "QUALITY BENCHMARK" row | Toggles expandable detail panel |
| Click "▶ Run" (empty state) | Triggers canary run via `POST /api/capability/canary/run` |
| Click "View details →" | Navigates to Capability tab |

---

## 5. Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Card row render | < 100ms per agent | Server-side render time |
| Expand/collapse | Instant (client-side) | No network call |
| Detail load | < 500ms | htmx response time |

---

## 6. File Changes

| File | Change |
|------|--------|
| `src/observeco/dashboard/routes/fleet.py` | Add `_canary_row()`, `_canary_pass_sub()`, quality benchmark row in agent card rendering |
| `src/observeco/dashboard/routes/capability.py` | Add `/api/capability/canary/card` endpoint for expanded detail |
