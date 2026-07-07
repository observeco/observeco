# ObserveCo Capability Monitoring — UX Spec

## Overview

Capability Monitoring adds a new layer to the ObserveCo dashboard: instead of just knowing *if* an agent is alive, you know *how well* it performs. This spec covers all screens, their states, and the user flow.

---

## 1. User Flow

```
Install → observeco watch → Passive Monitoring (health, tokens, drift)
  → "Agent is alive but is it any good?" → Define 3 tasks
    → Run Canary → First Baseline → Config Changes
      → Auto-Segment → New Baseline → Drift Detected
        → Alert Sent → Investigate → Fix & Re-run
```

**Key insight:** The flow is passive-first. The user doesn't need to do anything to get value — the canary card appears in the fleet view automatically. Only when they want to define custom tasks do they need to interact.

---

## 2. Screen: Canary Report Card

### 2.1 Compact Fleet Card (Variant A)

**Where it lives:** In the existing fleet view, as a card per agent below the health status row.

**What it shows:**
- Agent name + model + config hash
- 4 stat boxes: Pass Rate, Accuracy (CI), Hangs, Recovery Rate
- Drift indicator (▲/▼ vs baseline)
- "View details" link → opens expanded view

**States:**

| State | What the user sees | Action |
|-------|-------------------|--------|
| **No canary run yet** | Grey card: "No baseline — run canary to start" | "Run Canary" button |
| **First run complete** | Green card with stats, "First baseline created" badge | View details |
| **Drift detected** | Red drift indicator, yellow/red stat highlights | View details → drift chart |
| **Config changed** | "New config detected" badge, auto-segmenting | View timeline |
| **Error** | Red card: "Canary failed — check agent" | Re-run button |

### 2.2 Expanded Per-Agent View (Variant B)

**Triggered by:** Clicking "View details" on the compact card, or clicking the agent name in the fleet view.

**What it shows:**
- Agent header: name, model, config, overall accuracy score
- Full task table: 9 rows with Status, Accuracy (CI), Δ vs Baseline, Cost, Recovery
- Summary footer: pass count, hang count, fail count, drift magnitude
- Action buttons: Grid Report, Re-run Canary

**States:**

| State | What the user sees |
|-------|-------------------|
| **Loading** | Skeleton rows (pulsing grey bars) |
| **Loaded** | Full table with color-coded cells |
| **Empty** | "No tasks defined. Create your first benchmark task." + CTA |
| **Error** | "Failed to load canary results" + retry button |
| **Partial data** | Some rows show data, some show "pending" — agent may still be running |

---

## 3. Screen: Drift Chart

**The hero piece.** This is the viral shareable chart — the one the user screenshots and posts.

**Layout:**
1. **Drift badge** — 🔴 Drift detected · X% drop over N days
2. **Headline** — "Config unchanged, quality dropped X%"
3. **Subhead** — Plain English explanation
4. **Meta row** — Baseline date, window, run count, p-value
5. **Chart.js line chart** — 14-day accuracy trend with:
   - Green zone (baseline period)
   - Red zone (drift period)
   - Dashed baseline line
   - Annotation: "▼ -X% drift, p=0.003"
6. **Summary cards** — Baseline accuracy, Current accuracy, Drift magnitude
7. **Per-task drift breakdown** — Table with trend bars
8. **Actions** — Grid Report, Re-run Canary, Create Alert

**States:**

| State | What the user sees |
|-------|-------------------|
| **No drift** | Green badge: "✅ No drift detected. Last check: 2m ago" |
| **Drift detected** | Red badge, headline, chart with drift zone |
| **Insufficient data** | Yellow badge: "⚠️ Need 7+ runs to detect drift. 3/7 complete." |
| **Loading** | Chart skeleton (pulsing rectangle) |
| **Error** | "Drift analysis unavailable" + retry |

**Empty state (no canary runs):**
```
┌─────────────────────────────────────────────┐
│  📊 No drift data yet                       │
│                                             │
│  Run your first canary to establish a       │
│  baseline. Drift detection needs at least   │
│  7 runs over 7+ days to be meaningful.      │
│                                             │
│  [Run Canary]  [Define Tasks]               │
└─────────────────────────────────────────────┘
```

---

## 4. Screen: Task Definition

**Two modes:** Form (guided) and YAML (power user). Toggle between them.

### 4.1 Task List

**What it shows:**
- Built-in tasks (6, read-only) + user-defined tasks (editable)
- Per-task: name, assertion type, timeout, status dot
- Actions: Edit, Duplicate, Delete

**States:**

| State | What the user sees |
|-------|-------------------|
| **Has tasks** | List of tasks with action buttons |
| **No custom tasks** | "Define your first benchmark task" + CTA |
| **All built-in only** | "6 built-in tasks available. Add custom tasks to extend." |
| **Error loading** | "Failed to load tasks" + retry |

### 4.2 Task Editor (YAML mode)

**What it shows:**
- Raw YAML editor with monospace font
- Fields: name, description, prompt template, assertions (type, target, min/max/tolerance/keywords), timeout, model override, trials
- Cancel / Save buttons

**States:**

| State | What the user sees |
|-------|-------------------|
| **New task** | Empty template with placeholder values |
| **Editing** | Pre-filled with existing task YAML |
| **Validation error** | Red border on YAML editor + error message: "Invalid YAML: line 3, column 12" |
| **Saving** | Button shows spinner, disabled |
| **Saved** | Toast: "Task saved" → returns to task list |
| **Error saving** | Toast: "Failed to save — check YAML syntax" |

### 4.3 Task Editor (Form mode)

Same fields as YAML mode, but rendered as form inputs:
- Text inputs for name, description
- Textarea for prompt template
- Select for assertion type
- Number inputs for timeout, trials
- Select for model override

---

## 5. Screen: Config Timeline

**What it shows:**
- Agent selector pills (Main, Dreamer, Hound, PA)
- Vertical timeline with events:
  - Drift detected (red dot)
  - Prompt updated (yellow dot)
  - Model switched (green dot)
  - Tool manifest updated (blue dot)
  - First baseline (green dot)
- Each event card: title, timestamp, description, git hash, baseline segment badge
- Baseline legend at bottom

**States:**

| State | What the user sees |
|-------|-------------------|
| **Has history** | Full timeline with events |
| **No config changes** | "No config changes detected. All runs in a single baseline segment." |
| **Loading** | Skeleton timeline (pulsing cards) |
| **Error** | "Failed to load config history" + retry |

**Empty state (first install):**
```
┌─────────────────────────────────────────────┐
│  📋 No config history yet                    │
│                                             │
│  Config changes are auto-detected from      │
│  SOUL.md edits and git commits. Run your    │
│  first canary to establish a baseline.      │
│                                             │
│  [Run Canary]                               │
└─────────────────────────────────────────────┘
```

---

## 6. Screen: Grid Report

**What it shows:**
- Filter controls: Agent, Config, Show (all/passing/failing)
- Matrix table: Tasks (rows) × Model+Config (columns)
- Each cell: Accuracy score (color-coded) + cost + trajectory flags
- Flag types: `loop` (yellow), `unsafe` (red), `shortcut` (blue)
- Footer: summary stats + "Run Full Grid" button

**States:**

| State | What the user sees |
|-------|-------------------|
| **Has data** | Full grid with color-coded cells |
| **No data** | "Run a grid to compare models and configs" + CTA |
| **Partial** | Some cells show "pending" — still running |
| **Loading** | Skeleton grid (pulsing cells) |
| **Error** | "Grid report unavailable" + retry |
| **Filtered** | Only matching rows shown, filter pills visible |

**Empty state:**
```
┌─────────────────────────────────────────────┐
│  📊 No grid data yet                         │
│                                             │
│  Run a grid to compare how different models  │
│  and configs perform on your benchmark tasks.│
│  Each cell shows accuracy, cost, and any     │
│  trajectory flags (loops, unsafe actions).   │
│                                             │
│  [Run Grid]  [Define Tasks]                 │
└─────────────────────────────────────────────┘
```

---

## 7. Error States (Cross-Cutting)

### 7.1 Network / Backend Errors

```
┌─────────────────────────────────────────────┐
│  ⚠️ Connection lost                          │
│                                             │
│  Unable to reach the ObserveCo daemon.       │
│  Check that `observeco watch` is running.   │
│                                             │
│  [Retry]  [Check Daemon Status]             │
└─────────────────────────────────────────────┘
```

### 7.2 Agent Not Found

```
┌─────────────────────────────────────────────┐
│  🔍 Agent "X" not found                      │
│                                             │
│  This agent was removed or renamed.         │
│  Canary data for this agent is archived.     │
│                                             │
│  [View Fleet]                               │
└─────────────────────────────────────────────┘
```

### 7.3 Daemon Not Running

```
┌─────────────────────────────────────────────┐
│  ⚠️ observeco watch is not running           │
│                                             │
│  The monitoring daemon must be active to     │
│  collect canary data. Start it with:         │
│  `observeco watch`                           │
│                                             │
│  [Start Daemon]  [How it Works →]           │
└─────────────────────────────────────────────┘
```

---

## 8. Loading States (Cross-Cutting)

All data-fetching screens use the same skeleton pattern:

```
┌──────────────────────────────┐
│  ████████  ██████  ████████  │  ← pulsing grey bars
│  ████████  ██████  ████████  │
│  ████████  ██████  ████████  │
└──────────────────────────────┘
```

- Background: `var(--bg)` (#0f172a)
- Pulse color: `var(--border)` (#334155)
- Animation: 1.5s ease-in-out pulse loop
- Max duration: 10s before showing error state

---

## 9. Toast Notifications

| Action | Toast | Duration |
|--------|-------|----------|
| Re-run canary | "Re-running canary..." | 2.5s |
| Save task | "Task saved" | 2.5s |
| Delete task | "Task deleted" | 2.5s |
| Export CSV | "Exporting CSV..." | 2.5s |
| Create alert | "Creating alert rule..." | 2.5s |
| Error | "Failed to save — check YAML syntax" | 4s (red border) |

Position: bottom-right, stacked. Auto-dismiss.

---

## 10. Design System Compliance

All screens use the existing ObserveCo design tokens:
- `--bg`, `--surface`, `--fg`, `--accent`, `--border`
- `--status-healthy`, `--status-warning`, `--status-critical`
- `--font-body`, `--font-mono`
- `--radius-md`, `--radius-lg`, `--radius-pill`
- Standard header with logo + tier badge
- Standard toast container (bottom-right)

---

## 11. Accessibility

- All interactive elements are keyboard-accessible (buttons, selects, links)
- Color is never the sole indicator — status text accompanies color (e.g., "🔴 Breach" not just red text)
- Color-coded cells have sufficient contrast (green on dark: 4.5:1+, red on dark: 5:1+)
- Form inputs have visible focus states (green border)
- Tables use proper `<th>` elements with scope attributes
- Toast notifications include both icon and text

---

## 12. File Inventory

| File | Type | Description |
|------|------|-------------|
| `user-flow.excalidraw` | Excalidraw | Install → first baseline → drift alert flow |
| `canary-report-card.html` | HTML mockup | Variant A (compact fleet card) + Variant B (expanded per-agent) |
| `drift-chart.html` | HTML mockup | Chart.js line chart with baseline/drift zones, summary cards, per-task breakdown |
| `task-definition.html` | HTML mockup | Task list + YAML editor + form mode (hidden) |
| `config-timeline.html` | HTML mockup | Vertical timeline with agent selector, event cards, baseline segments |
| `grid-report.html` | HTML mockup | Model × Config matrix with color-coded accuracy cells and trajectory flags |
| `ux-spec.md` | Markdown | This document — all states, flows, error/empty/loading patterns |
