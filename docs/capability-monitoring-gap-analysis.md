# Capability Monitoring — Structured Gap Analysis

**Date:** 2026-07-04  
**Scope:** Mockups vs Current Implementation vs Design System (v2 Strong-Fit)  
**Files analyzed:** 17 source files across mockups/, design/, src/observeco/dashboard/

---

## Executive Summary

The current implementation has **functional parity** for most capability monitoring screens (drift chart, grid report, task definition) but **lacks visual parity** with the mockups. The HTML partials in `capability.py` use inline styles instead of the v2 Strong-Fit design system classes that are already defined in `observeco-dashboard.css`. The **config timeline** has no HTML partial at all — only a JSON API endpoint. The **canary report card** (compact fleet card variant) is not rendered in the fleet view. State handling (loading/error skeletons) is missing for all capability screens.

---

## 1. Canary Report Card

### Mockup: `mockups/capability-monitoring/canary-report-card.html`
- **Variant A:** Compact fleet card with status dot, agent name, model, 4 stat boxes (Pass Rate, Accuracy CI, Hangs, Recovery), drift indicator, "View details" link
- **Variant B:** Expanded per-agent view with full task table (Status, Accuracy CI, Δ vs Baseline, Cost, Recovery), summary footer, action buttons

### Current Implementation
- `index_new.html` renders agent cards with health status, tokens, errors, brain, compose — but **no canary stats**
- `capability.py` has `/api/capability/canary/status` (JSON) and `/api/capability/canary/run` (POST) but **no HTML partial** for the compact fleet card
- The fleet view (`/api/fleet/agents`) renders agent cards without canary data

### Gaps

| Gap | Priority | Details |
|-----|----------|---------|
| No compact canary card in fleet view | **P0** | The fleet agent cards don't show pass rate, accuracy CI, hangs, recovery, or drift indicator. Need to add canary stats to the agent card rendering in `routes/fleet.py` |
| No "View details" → expanded view flow | **P1** | The mockup has a "View details" link that opens the expanded per-agent view. No routing or partial exists for this |
| No "Run Canary" button on empty state | **P1** | UX spec says grey card with "No baseline — run canary to start" for agents with no canary runs |
| No drift indicator on agent cards | **P1** | Mockup shows ▲/▼ drift vs baseline on each card. Current cards show token drift but not accuracy drift |
| Missing states: loading skeleton, error, partial data | **P2** | UX spec defines loading (skeleton rows), error ("Failed to load canary results"), partial data ("pending") states |

### Code Changes Needed
1. **`routes/fleet.py`** — Add canary stats (pass_rate, accuracy_ci, hangs, recovery, drift) to agent card rendering
2. **`capability.py`** — Add `/api/capability/canary/card?agent=NAME` HTML partial for the compact fleet card
3. **`templates/index_new.html`** — Add htmx trigger to load canary cards alongside agent cards
4. **New partial** — Expanded per-agent view with task table (Variant B)

---

## 2. Drift Chart

### Mockup: `mockups/capability-monitoring/drift-chart.html`
- Drift badge (🔴 Drift detected · X% drop over N days)
- Headline: "Config unchanged, quality dropped X%"
- Subhead: Plain English explanation
- Meta row: Baseline date, window, run count, p-value
- Chart.js line chart with baseline/drift zone annotations (chartjs-plugin-annotation)
- 3 summary cards: Baseline accuracy, Current accuracy, Drift magnitude
- Per-task drift breakdown table with trend bars
- Action buttons: Grid Report, Re-run Canary, Create Alert

### Current Implementation
- `capability.py` `drift_chart_partial()` returns hero section, meta, summary cards, chart container, task table, triage path
- Uses inline styles throughout — **not using design system classes**
- Chart.js is used but **missing chartjs-plugin-annotation** for baseline/drift zone visual annotations
- Task table uses inline styles instead of `.drift-table` classes from mockup

### Gaps

| Gap | Priority | Details |
|-----|----------|---------|
| Inline styles instead of design system classes | **P0** | All HTML in `drift_chart_partial()` uses inline styles. Should use `.swc`, `.verdict`, `.section`, `.section-header`, `.section-body`, `.drift-table` classes |
| Missing chartjs-plugin-annotation | **P1** | Mockup uses chartjs-plugin-annotation for baseline zone (green), drift zone (red), and drift arrow annotation. Current chart has no zone annotations |
| No "So What" insight card | **P1** | The drift chart should include a `.swc.alert` or `.swc.watch` card explaining what the drift means in plain English |
| Missing states: "No drift" (green badge), insufficient data (yellow badge), loading skeleton, error | **P1** | Current implementation only has empty state. Missing: "✅ No drift detected", "⚠️ Need 7+ runs" (3/7 complete), chart skeleton, error state |
| No "Create Alert" button | **P2** | Mockup has a "Create Alert" button. Current has "Create Alert" in the chart header but it's a no-op |
| Trend bars use fixed width instead of proportional | **P2** | Mockup shows proportional trend bars (width based on drift magnitude). Current uses `min(abs(delta), 30)` which caps at 30px |
| No "Share" button for viral chart | **P2** | Mockup describes this as "the viral shareable chart" but no share/screenshot functionality |

### Code Changes Needed
1. **`capability.py` `drift_chart_partial()`** — Replace inline styles with design system classes (`.section`, `.drift-hero`, `.drift-badge`, `.drift-headline`, `.drift-subhead`, `.drift-meta`, `.drift-summary`, `.drift-card`, `.drift-table`, `.btn`, `.btn-primary`, `.btn-outline`, `.btn-danger`)
2. **`templates/index_new.html`** — Add chartjs-plugin-annotation CDN script
3. **`capability.py`** — Add proper state handling: `_drift_no_drift_html()`, `_drift_insufficient_data_html()`, `_drift_loading_html()`, `_drift_error_html()`
4. **`observeco-dashboard.css`** — Add `.drift-hero`, `.drift-badge`, `.drift-headline`, `.drift-subhead`, `.drift-meta`, `.drift-summary`, `.drift-card`, `.drift-table`, `.drift-bar`, `.drift-fill` classes (or add them inline in the partial)

---

## 3. Task Definition

### Mockup: `mockups/capability-monitoring/task-definition.html`
- Task list with status dots (green/yellow), name, assertion type, timeout, assertions count
- Action buttons: Edit, Duplicate, Delete
- "New Task" and "Import YAML" buttons
- YAML editor with monospace font, syntax-like display
- Form mode with inputs: name, description, prompt template, assertion type select, timeout, model override, trials
- Toggle between Form/YAML modes

### Current Implementation
- `capability.py` `task_list_partial()` returns task list with status dots, action buttons
- `capability.py` `task_editor_partial()` returns YAML editor + form mode with toggle
- **Uses inline styles throughout** — not using design system classes
- Has all functional features (list, edit, duplicate, delete, YAML, form, toggle)

### Gaps

| Gap | Priority | Details |
|-----|----------|---------|
| Inline styles instead of design system classes | **P0** | Should use `.section`, `.section-header`, `.section-title`, `.task-list`, `.task-item`, `.task-item-info`, `.task-item-name`, `.task-item-meta`, `.task-item-actions`, `.yaml-preview`, `.form-group`, `.form-label`, `.form-input`, `.form-textarea`, `.form-select`, `.form-row`, `.btn`, `.btn-primary`, `.btn-outline`, `.btn-sm`, `.btn-icon` |
| Missing "built-in" vs "user-defined" visual distinction | **P1** | Mockup shows 3 user-defined + 6 built-in tasks. Current doesn't visually distinguish built-in (read-only) from custom (editable) |
| Missing model override field in form mode | **P1** | Mockup form has "Model Override" select with options (default, deepseek-v4-flash, deepseek-v4-pro, gemma4:31b). Current form doesn't have this field |
| Missing validation error state | **P2** | UX spec: "Invalid YAML: line 3, column 12" with red border. Current has no validation UI |
| Missing saving spinner | **P2** | UX spec: "Button shows spinner, disabled" during save. Current has no loading state on save button |
| Missing "No custom tasks" empty state | **P2** | UX spec: "Define your first benchmark task" + CTA when no custom tasks exist (but built-in tasks are present) |

### Code Changes Needed
1. **`capability.py` `task_list_partial()`** — Replace inline styles with design system classes
2. **`capability.py` `task_editor_partial()`** — Replace inline styles, add model override field, add validation error UI, add saving spinner
3. **`observeco-dashboard.css`** — Add `.task-list`, `.task-item`, `.task-item-info`, `.task-item-name`, `.task-item-meta`, `.task-item-actions`, `.yaml-preview`, `.form-group`, `.form-label`, `.form-input`, `.form-textarea`, `.form-select`, `.form-row`, `.btn-sm`, `.btn-icon` classes

---

## 4. Config Timeline

### Mockup: `mockups/capability-monitoring/config-timeline.html`
- Agent selector pills (Main, Dreamer, Hound, PA) with `.agent-pill.active` styling
- Vertical timeline with vertical line, dots (green/yellow/red/blue), event cards
- Event cards: title, change type, timestamp, description with `<code>` elements, git hash, baseline segment badge
- Baseline legend at bottom with color swatches

### Current Implementation
- `capability.py` `config_timeline()` returns **JSON only** — no HTML partial
- Data is available: events with date, type, title, description, segment, accuracy, git_commit
- No visual timeline rendering exists

### Gaps

| Gap | Priority | Details |
|-----|----------|---------|
| **No HTML partial for timeline** | **P0** | The entire visual timeline UI is missing. Only JSON API exists |
| No agent selector pills | **P0** | Mockup has pill-style agent selector. Not implemented |
| No vertical timeline with dots and cards | **P0** | The core visual component is missing |
| No baseline segment badges/legend | **P1** | Mockup has `.baseline-badge.segment-a/b/c` and `.baseline-legend` |
| Missing states: loading skeleton, error, "No config changes" | **P1** | UX spec defines skeleton timeline, error state, and "No config changes detected" empty state |
| Missing "First install" empty state | **P2** | UX spec: "No config history yet" with "Run Canary" CTA |

### Code Changes Needed
1. **`capability.py`** — Add `/api/capability/timeline/partial?agent=NAME` HTML partial
2. **New HTML partial** — Render agent selector pills, vertical timeline with events, baseline legend
3. **`observeco-dashboard.css`** — Add `.agent-selector`, `.agent-pill`, `.agent-pill.active`, `.timeline`, `.timeline-line`, `.timeline-event`, `.timeline-date`, `.timeline-dot`, `.timeline-card`, `.timeline-card-header`, `.timeline-card-title`, `.timeline-card-desc`, `.baseline-badge`, `.baseline-legend` classes
4. **`templates/index_new.html`** — Add htmx trigger for timeline partial

---

## 5. Grid Report

### Mockup: `mockups/capability-monitoring/grid-report.html`
- Filter controls: Agent, Config, Show (all/passing/failing), Export CSV
- Matrix table: Tasks (rows) × Model+Config (columns)
- Each cell: Accuracy score (color-coded: high/medium/low/na) + CI + cost + trajectory flags
- Flag types: `loop` (yellow), `unsafe` (red), `shortcut` (blue)
- Footer: summary stats + "Run Full Grid" button

### Current Implementation
- `capability.py` `grid_table_partial()` returns filter controls, matrix table, footer
- **Uses inline styles** — not using design system classes
- Has all functional features (filters, matrix, color-coded cells, flags, cost, summary, export)

### Gaps

| Gap | Priority | Details |
|-----|----------|---------|
| Inline styles instead of design system classes | **P0** | Should use `.grid-controls`, `.filter-group`, `.grid-select`, `.grid-table`, `.cell-score`, `.cell-score.high/medium/low/na`, `.cell-ci`, `.cell-cost`, `.cell-flags`, `.flag-loop`, `.flag-unsafe`, `.flag-shortcut`, `.grid-footer`, `.summary` |
| Missing "So What" insight card | **P1** | Should include a `.swc.insight` card explaining the key takeaway from the grid (e.g., "deepseek-v4-flash × baseline-v3 wins on cost-adjusted accuracy") |
| Missing states: loading skeleton, error, partial data, filtered | **P1** | UX spec defines skeleton grid (pulsing cells), error state, partial data ("pending" cells), filtered state (filter pills visible) |
| No "Run Full Grid" loading state | **P2** | Button should show spinner while grid is running |

### Code Changes Needed
1. **`capability.py` `grid_table_partial()`** — Replace inline styles with design system classes
2. **`observeco-dashboard.css`** — Add `.grid-controls`, `.filter-group`, `.grid-select`, `.grid-table`, `.cell-score`, `.cell-score.high/medium/low/na`, `.cell-ci`, `.cell-cost`, `.cell-flags`, `.flag-loop`, `.flag-unsafe`, `.flag-shortcut`, `.grid-footer` classes
3. **`capability.py`** — Add `_grid_loading_html()`, `_grid_error_html()`, `_grid_partial_html()` state handlers

---

## 6. Design System Compliance (Cross-Cutting)

### Design System Files
- `design/tokens.css` — Complete token set with `--surface-hover`, `--surface-active`, `--status-info`, `--token-identity/skills/memory/tools/guidance`, `--elev-flat/ring/raised`, `--focus-ring`, `--motion-fast/base`, `--ease-standard`
- `design/ObserveCo - All States (v2).html` — Loading, empty, data, error states with `.skel`, `.empty-card`, `.state-msg`, `.verdict`, `.card`, `.nav`, `.panel`, `.tl-rows` classes
- `design/ObserveCo - Fleet Prototype (v2).html` — Agent cards with health panel, pulse history, alerts rail, error timeline
- `design/ObserveCo - So What Card Pattern.html` — `.swc` with 4 tones: insight (green), watch (amber), alert (red), neutral (slate)
- `design/ObserveCo - Agent Detail Modal (v2).html` — Modal with tabs, pulse48 grid, guard timeline, token composition, memory debt
- `design/ObserveCo - Token Analytics (v2).html` — Cost trend chart, attribution gap, per-agent cost table, composition, cache efficiency

### Current Implementation
- `observeco-dashboard.css` — Already includes most v2 classes: `.nav`, `.verdict`, `.card`, `.panel`, `.tl-rows`, `.skel`, `.empty-card`, `.swc`, `.scrim`, `.modal`, `.m-head`, `.m-tabs`, `.m-body`, `.grid2`, `.tbl`, `.compbar`, `.state-msg`, `.pulse48`, `.ftl`, `.debt-head`, `.mstat`, `.arch`, `.pro`, `.cache-cell`, `.cache-mini`, `.comp-row`, `.comp-stack`, `.cache-row`, `.cache-track`
- `index_new.html` — Uses v2 layout with `.topbar`, `.nav`, `.verdict`, `.zone2`, `.grid`, `.future`, `.zone3`
- `index.html` — Uses older layout (v1), not v2 Strong-Fit

### Gaps

| Gap | Priority | Details |
|-----|----------|---------|
| Capability partials use inline styles, not CSS classes | **P0** | All 4 capability HTML partials (drift, grid, tasks, timeline) use inline styles. The design system classes are already defined in `observeco-dashboard.css` but not used |
| Missing `--surface-hover` and `--surface-active` in `index.html` | **P1** | `index.html` (v1) doesn't have these tokens. `index_new.html` (v2) does |
| Missing `--status-info` in `index.html` | **P1** | v1 template missing this token |
| Missing `--token-*` palette in `index.html` | **P1** | v1 template uses `--tok-*` instead of `--token-*` |
| Missing `--elev-*` and `--motion-*` tokens | **P2** | `tokens.css` defines elevation and motion tokens not used anywhere |
| No "So What" cards in any capability screen | **P1** | `.swc` class is defined in CSS but not used in drift, grid, or task screens |
| No loading skeletons for capability screens | **P1** | `.skel` class is defined but not used in any capability partial |
| No proper error states for capability screens | **P1** | `.state-msg.err` is defined but not used in capability partials |

---

## 7. State Handling Summary

| Screen | Loading | Empty | Error | Populated | Partial Data |
|--------|---------|-------|-------|-----------|-------------|
| **Canary Card (Variant A)** | ❌ Missing | ❌ Missing | ❌ Missing | ⚠️ Not implemented | ❌ Missing |
| **Canary Card (Variant B)** | ❌ Missing | ❌ Missing | ❌ Missing | ⚠️ Not implemented | ❌ Missing |
| **Drift Chart** | ❌ Missing | ✅ Basic empty | ❌ Missing | ✅ Functional | ❌ Missing |
| **Task Definition** | ❌ Missing | ✅ Basic empty | ❌ Missing | ✅ Functional | ❌ Missing |
| **Config Timeline** | ❌ Missing | ❌ Missing | ❌ Missing | ❌ Not implemented | ❌ Missing |
| **Grid Report** | ❌ Missing | ✅ Basic empty | ❌ Missing | ✅ Functional | ❌ Missing |

---

## 8. Priority Summary

### P0 — Must fix (blocks visual parity)
1. Replace all inline styles in `capability.py` HTML partials with design system classes
2. Add config timeline HTML partial (currently JSON-only)
3. Add canary report card to fleet view
4. Add loading skeletons and error states to all capability screens

### P1 — Should fix (important for UX quality)
1. Add chartjs-plugin-annotation to drift chart for baseline/drift zone annotations
2. Add "So What" insight cards to drift, grid, and task screens
3. Add "No drift" and "Insufficient data" states to drift chart
4. Add built-in vs user-defined visual distinction in task list
5. Add model override field to task form editor
6. Add agent selector pills to config timeline
7. Add baseline segment badges and legend to timeline
8. Add "View details" → expanded canary view flow
9. Add "Run Canary" button on empty canary states

### P2 — Nice to have
1. Add validation error UI to task editor (red border + error message)
2. Add saving spinner to task editor buttons
3. Add "Share" button for drift chart
4. Add proportional trend bars in drift task table
5. Add `--elev-*` and `--motion-*` tokens to templates
6. Add "First install" empty state for config timeline
7. Add "Create Alert" button functionality

---

## 9. File Change Map

| File | Changes Needed |
|------|---------------|
| `src/observeco/dashboard/routes/capability.py` | Replace inline styles with CSS classes in `drift_chart_partial()`, `task_list_partial()`, `task_editor_partial()`, `grid_table_partial()`. Add `config_timeline_partial()`. Add state handlers (loading, error, partial). Add model override field to form editor |
| `src/observeco/dashboard/routes/fleet.py` | Add canary stats to agent card rendering |
| `src/observeco/dashboard/static/observeco-dashboard.css` | Add `.drift-hero`, `.drift-badge`, `.drift-headline`, `.drift-subhead`, `.drift-meta`, `.drift-summary`, `.drift-card`, `.drift-table`, `.drift-bar`, `.drift-fill`, `.task-list`, `.task-item`, `.task-item-info`, `.task-item-name`, `.task-item-meta`, `.task-item-actions`, `.yaml-preview`, `.form-group`, `.form-label`, `.form-input`, `.form-textarea`, `.form-select`, `.form-row`, `.btn-sm`, `.btn-icon`, `.agent-selector`, `.agent-pill`, `.timeline`, `.timeline-line`, `.timeline-event`, `.timeline-date`, `.timeline-dot`, `.timeline-card`, `.timeline-card-header`, `.timeline-card-title`, `.timeline-card-desc`, `.baseline-badge`, `.baseline-legend`, `.grid-controls`, `.filter-group`, `.grid-select`, `.grid-table`, `.cell-score`, `.cell-score.high/medium/low/na`, `.cell-ci`, `.cell-cost`, `.cell-flags`, `.flag-loop`, `.flag-unsafe`, `.flag-shortcut`, `.grid-footer` |
| `src/observeco/dashboard/templates/index_new.html` | Add htmx triggers for canary cards, config timeline partial. Add chartjs-plugin-annotation CDN |
| `src/observeco/dashboard/templates/index.html` | Migrate to v2 Strong-Fit design (or deprecate in favor of `index_new.html`) |
