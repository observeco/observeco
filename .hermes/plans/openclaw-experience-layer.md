# OpenClaw Experience Layer — 5-Feature Rollout Specification

**Context:** Sean said "I've been envisioning five distinct features for OpenClaw users" — the Common Good layer that sits on top of ObserveCo's data collection and makes it visually useful for OpenClaw operators. These are NOT five standalone features; they are five **surface views** over a unified data model.

---

## Data Model (Shared Foundation)

Single query layer feeding all five views:

```json
{
  "agent_name": "hermes-main",
  "framework": "hermes",
  "health": {
    "pulse_status": "alive",
    "uptime_hours": 72,
    "last_pulse_ago": 15,
    "total_events": 1240,
    "error_count_24h": 2
  },
  "brain": {
    "total_tokens": 124500,
    "components": { "identity": 20000, "skills": 55000, "memory": 15000, "tools": 7500, "guidance": 27000 },
    "drift_items": [],
    "grade": "B"
  },
  "garden": {
    "memory_debt_score": 35,
    "duplicates": 3,
    "contradictions": 1,
    "stale_entries": 2,
    "last_scan": "2026-06-04"
  },
  "restarts": {
    "total": 8,
    "healthy": 6,
    "crash": 1,
    "toctou": 1
  },
  "chisel": {
    "savings_pct": 28,
    "savings_tokens": 45000,
    "recent_trims": []
  },
  "overfitting": {
    "score": 65,
    "severity": "🟡 medium",
    "flagged_items": []
  },
  "relevance": {
    "context_window_pct": 42,
    "sources_loaded": 180,
    "sources_skipped": 15,
    "tokens_saved": 32000
  }
}
```

**Backend:** New unified endpoint `/api/openclaw/agent-summary` that composes data from:
- `pulse_log` — health status
- `clawforge_profiles` — memory/skill/token sizes
- `clawforge_garden` — memory debt, duplicates, contradictions
- `clawforge_loads` — sources loaded/skipped, tokens saved
- `chisel_trims` — compression savings
- `restart_log` — restart classification
- `plugin_tracking` — context window %, sources

---

## Feature 1: Companion Mode for Launcher/TUI

**Goal:** Make `observeco` output directly actionable in an OpenClaw TUI/Launcher — not just "start your agent" but "your agent needs attention in these 3 areas."

**User sees:** When they run `observeco` in their OpenClaw TUI:
```
┌─────────────────────────────────────────┐
│ ⚡ OpenClaw Companion              v0.1 │
├─────────────────────────────────────────┤
│ hermes-main ......... ● alive  72h up  │
│ hermes-pa .......... ● alive  48h up  │
│ openclaw-agent ..... ● alive  24h up  │
├─────────────────────────────────────────┤
│ ⚠  hermes-main: memory drift (skill) ↑12%  │
│ ⚠  openclaw: high overfitting score (72)    │
│ 📢  hermes-pa: 3 unresolved errors          │
├─────────────────────────────────────────┤
│   alias  openclaw  ...  @openclaw/agent     │
│   alias  hermes  .....  @hermes/agent       │
├─────────────────────────────────────────┤
│ 🧠 Brain  | 🧹 Garden  | 🔄 Restarts   │
│ 📊 Chisel | 🎯 Fit    | 🔍 Relevance   │
└─────────────────────────────────────────┘
```

**Implementation:**
- `observeco companion` CLI command → prints rich terminal status bar
- `observeco companion --json` → machine-readable JSON for TUI widgets
- Powers "command-line ears" feature: the launcher checks companion status before agent start

**API impact:** New `/api/openclaw/companion` endpoint returning fleet summary with severity annotations.

---

## Feature 2: Shared Agent Profile View

**Goal:** One-stop page showing ALL available data for ONE agent — health, brain, garden, chisel, restarts, fit, relevance — as a scrolling detail page in the dashboard.

**User sees:** Click any agent card → new tab "🤖 Agent Profile" that replaces the 5-tab drill-modal with a single scrollable page:

```
┌─ hermes-main ───────────────────────────┐
│ 🟢 Alive · 72h uptime · 15s since pulse │
├─────────────────────────────────────────┤
│ Health    🟢 Good   2 errors/24h         │
│ Brain     🧠 124K tok  Grade: B         │
│ Garden    🧹 Score 35  3 dupes, 1 con   │
│ Chisel    📊 28% saved  45K tok saved   │
│ Restarts  🔄 8 total  1 crash           │
│ Overfit   🎯 Score 65  🟡 medium         │
│ Relevance 🔍 42% ctx · 15 skipped/180   │
├─────────────────────────────────────────┤
│ [Actions ▼] [Fix] [Back to Fleet]       │
└─────────────────────────────────────────┘
```

**Implementation:**
- New `/api/openclaw/agent-profile?agent=<name>` → full agent data
- New tab in dashboard: `tabProfile` with `loadAgentProfile(agentName)` JS function
- Replaces the drill-modal detail-tab-bar with a single scrollable card
- Details: each section is collapsible with `toggleSection()`

**Architecture note:** This duplicates the existing 5-tab drill modal. May want to eventually merge them, but for this rollout keep them separate — a quick "full picture" page vs the 5-tab drill-down.

---

## Feature 3: Chisel Awareness Column in Fleet View

**Goal:** Show each agent's compression savings directly in the fleet card — "awareness without a click."

**User sees:** Each fleet card gets a new row:
```
┌─ hermes-main ◈──────────────┐
│ 🟢 Alive · 72h · agent      │
│ Brain 124K · Drift: skills ↑│
│ 💎  Chisel: 28% saved 🟢     │
└─────────────────────────────┘
```

**Implementation:**
- `/api/agents` endpoint already returns per-agent data. Add `chisel_savings_pct` to each agent dict.
- Fleet card template adds: `<div class="agent-metric-row"><span style="color:#14b8a6;">💎</span> Chisel: {pct}% saved <status_color indicator></div>`
- Color logic: >30% 🟢, 15-30% 🟡, <15% 🔴

**Data source:** `chisel_trims` table — average savings_ratio over last N trims per agent.

---

## Feature 4: Broadcast Mode — Anomalies Dashboard Tab

**Goal:** Surface fleet-wide anomalies as a single tab: agents that need help right now.

**User sees:** New tab in the dashboard:
```
┌─ 📢 Alerts Inbox ────────────────────────────┐
│ ┌─────────────────────────────────────────┐   │
│ │ hermes-main · memory drift skills ↑12% │   │
│ │ 🔴 critical · 2h ago                   │   │
│ │ [Dismiss] [View agent] [Fix]           │   │
│ ├─────────────────────────────────────────┤   │
│ │ openclaw  · error rate spike 15/h      │   │
│ │ 🟡 warning · 30m ago                    │   │
│ │ [Dismiss] [View agent] [Fix]           │   │
│ └─────────────────────────────────────────┘   │
└───────────────────────────────────────────────┘
```

**Implementation:**
- New `/api/anomalies` endpoint: scans pulse_log, chisel_drift, errors, l2_trending for recent anomalies
- Uses existing `alert_subscriptions` and `alert_log` tables — anomalies = pattern matched alerts that haven't been dismissed
- "Dismiss" = mark resolved in L2 trending / dead_letter_queue
- "View agent" = opens agent profile (Feature 2)
- "Fix" = intelligent action (prompt user to run chisel trim, restart agent, etc.)

**What qualifies as anomaly:**
- Agent status = dead or error for >5 min
- Drift metric > threshold (tokens up 15%+ week over week)
- Error rate > 5 in last hour
- Circuit breaker tripped
- Restart quality dropped to crash (3+ crashes in last 24h)

---

## Feature 5: Journey Entry Points

**Goal:** New tab: "Start Here" / "Onboarding Flow" showing OpenClaw users how to get value step by step.

**User sees:** A new onboarding-style tab:
```
┌─ 🌱 Get Started with ObserveCo ───────────────────┐
│                                                     │
│ ✅ Step 1: Install CLI                              │
│    pip install observeco                            │
│    observeco dashboard                             │
│                                                     │
│ ✅ Step 2: Discovered 3 agents                      │
│    hermes-main, hermes-pa, openclaw-agent          │
│    View in Fleet tab →                             │
│                                                     │
│ ⬜ Step 3: Watch your Brain Analysis                │
│    See token breakdown, drift, grade               │
│    Open Brain tab →                                │
│                                                     │
│ ⬜ Step 4: Reduce token usage 28%                   │
│    Run chisel compress on hermes-main              │
│    Open Chisel view →                              │
│                                                     │
│ ⬜ Step 5: Set up Push Alerts                       │
│    Get Telegram/Slack alerts when agents go down   │
│    Open Alerts tab →                               │
└─────────────────────────────────────────────────────┘
```

**Implementation:**
- New `/api/onboarding/status` endpoint: checks which journey milestones are complete
- Milestones: CLI installed, agent discovered, brain viewed, chisel run, alert set up
- Data sources: telemetry_events (install), agent_configs (agents discovered), feature detection
- New tab in dashboard: `tabJourney` with loadJourney() JS
- Uses existing `is_first_run()` logic — show prominently on first visit

---

## Rollout Sequence

| Phase | Features | Dependencies | Effort |
|-------|----------|-------------|--------|
| **P1: Agent Profile** | Feature 2 + Feature 3 | Unify data model first | 3h |
| **P2: Companion** | Feature 1 | P1 data model | 2h |
| **P3: Broadcast** | Feature 4 | P1 + P2 | 3h |
| **P4: Onboarding** | Feature 5 | P1 | 2h |

**Total: ~10h**

---

## Unified API Endpoints Summary

| Endpoint | Purpose | Phase |
|----------|---------|-------|
| `/api/openclaw/agent-summary?agent=<name>` | Full profile data for one agent | P1 |
| `/api/openclaw/companion` | Fleet summary with severity annotations | P2 |
| `/api/openclaw/companion?format=json` | Machine-readable companion data | P2 |
| `/api/anomalies` | Fleet-wide anomalies needing attention | P3 |
| `/api/anomalies/{id}/dismiss` | Dismiss anomaly | P3 |
| `/api/onboarding/status` | Journey milestone progress | P4 |

**Existing endpoints to extend:**
- `/api/agents`: add `chisel_savings_pct` and `overfitting_score` to per-agent data (P1 for Feature 3)

---

## UI: New Tab in Dashboard Nav

Add after the existing Plugin tab:
```
<button class="tab-btn" onclick="switchTab('profile', this)">🤖 Profile</button>
```
(Replaces drill-modal detail view — only shown when an agent is selected)

```
<button class="tab-btn" onclick="switchTab('anomalies', this)">📢 Anomalies</button>
```
(Feature 4)

```
<button class="tab-btn" onclick="switchTab('journey', this)">🌱 Get Started</button>
```
(Feature 5 — shown on first-run only, or accessible from a small "Help" link)
