# ObserveCo Dashboard — Product Spec v1

**Product:** Runtime observability for your AI agents — built for Hermes, works with anything  
**Status:** Draft  
**Author:** Main (per Sean direction 2026-05-22)  
**Location:** `specs/unified-dashboard.md` (ObserveCo monorepo)  
**Supersedes:** `ERIS-product-spec-v1.md` (dashboard section), `CHISEL-product-spec-v1.md` (dashboard section)

---

## 1. One-Liner

A single-pane dashboard that shows every agent's health status, context profile, recent errors, and optimization suggestions — `pip install` and agents discovered in under 60 seconds, first health data within 90s, no cloud required. Supports both **Hermes** (session-start compression, component decomposition) and **OpenClaw** (intent-aware loading, memory hygiene, skill intelligence). Free tier is fully functional; Pro features are visible but locked.

---

## 2. Why Unified

The old ERIS + CHISEL split was architecturally neat but wrong for users. An AI agent fleet owner doesn't think in terms of "runtime integrity" vs "context observability." They think:

- *Is my fleet healthy right now?*
- *What changed this week?*
- *What's going wrong?*
- *Why is my agent's context growing and how do I fix it?*

One dashboard. Two agent frameworks under the hood. Each collects different data because each has different architecture — Hermes is session-start, reference-file-heavy; OpenClaw is persistent, file-driven, and workspace-oriented. The dashboard unifies them into one view.

**Hermes data:** pulse health, circuit breaker state, chisel token breakdown (decomposed system prompt by identity/skills/memory/tools/guidance), chisel drift trends.

**OpenClaw data:** pulse health, ClawForge context profiler (MEMORY.md size, skill usage, workspace bloat), intent-aware loading savings, memory debt score, skill intelligence heatmap.

---

## 3. Installation

| Requirement | Detail |
|---|---|
| **Runtime** | Python 3.10+ |
| **Dependencies** | None beyond stdlib + pip-installable packages |
| **OS** | macOS, Linux, WSL |
| **Install** | `pip install observeco && observeco dashboard` |
| **First run** | Scans local agent configs → starts monitoring → dashboard opens with live loading states in <60s. First health data within ~30s. First token data after first agent session. |
| **No cloud, no Docker, no API keys** | All data local. No telemetry leaves the machine. |

### How Agent Detection Works

The dashboard does NOT guess. It reads from a well-known config convention:

1. **Explicit config** — User provides `observeco.yml` or `~/.observeco/agents.json` listing agent names, roles, and health check commands/URLs
2. **Auto-detect** — Scans common agent framework configs (Hermes `.hermes/`, LangGraph `langgraph.json`, CrewAI `crew.yaml`, custom `AGENTS.md`), extracts agent names + heartbeat endpoints
3. **Fallback** — User manually adds via `observeco agents add <name> --check <cmd|url>`

No magic. The user always knows what's being monitored and can override.

---

## 4. Architecture

```
pip install observeco
    ├── pulse check       — agent liveness heartbeat
    ├── pulse circuit     — N-failure trip → auto-block → cooldown
    ├── chisel trim       — system prompt compression (Hermes — token savings)
    ├── chisel drift      — token allocation diff over time (Hermes)
    ├── clawforge profile — context profiler (OpenClaw — MEMORY.md, skills, workspace)
    ├── clawforge load    — intent-aware context loader (OpenClaw — ContextEngine hook)
    ├── clawforge garden  — memory hygiene agent (OpenClaw — dedup, archive, flag)
    └── observeco dashboard — local web UI, ships with library
```

**Under the hood:**

| Source | Framework | Collects | Storage |
|--------|-----------|----------|---------|
| `pulse check` | Both | Agent alive/dead/error status per tick | Local SQLite (`~/.observeco/pulse.db`) |
| `pulse circuit` | Both | Failure count, trip state, cooldown timer | Same SQLite |
| `chisel trim` | Hermes | Token breakdown per session (identity, skills, memory, tools, guidance) | Same SQLite |
| `chisel drift` | Hermes | 7-day rolling diff per component per agent | Same SQLite (aggregated) |
| `clawforge profile` | OpenClaw | MEMORY.md size, skill count per turn, workspace file sizes, history depth | Same SQLite |
| `clawforge load` | OpenClaw | Intent-aware loading — classification result, sources loaded vs skipped, tokens saved per turn | Same SQLite |
| `clawforge garden` | OpenClaw | Memory debt score: duplicates found, contradictions flagged, stale entries archived | Same SQLite |

All data stays local. The dashboard reads from this single SQLite file.

### 4.1 Agent Framework Support — v1 Honest State

| Framework | `pulse check` | `pulse circuit` | `chisel trim` | `chisel drift` | `clawforge *` | Context Profile | Value at Install |
|-----------|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **Hermes** | ✅ | ✅ | ✅ | ✅ | ⬜ | ✅ Full component decomposition | 100% |
| **OpenClaw** | ✅ (health endpoint) | ◐ (no native circuit) | ⬜ | ⬜ | ✅ v1 | ✅ Intent-aware + memory score | ~85% |
| **Ollama** | ✅ (health endpoint) | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ~20% |
| **LangChain/LangGraph** | ◐ (if health endpoint) | ◐ (no native circuit) | ⬜ | ⬜ | ⬜ | ⬜ | ~15% |
| **CrewAI** | ◐ (if health endpoint) | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ~10% |
| **Custom Python** | ◐ (if health endpoint) | ⬜ | ◐ (stdin pipe) | ⬜ | ⬜ | ⬜ | ~10% |
| **AutoGen** | ◐ (if health endpoint) | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ~5% |

**Key:**
- ✅ = Works out of the box
- ◐ = Works if user has a health endpoint / pipes stdin
- ⬜ = Not supported in v1

**The honest pitch:** v1 covers two first-class frameworks — **Hermes** (full Chisel suite: component decomposition, session-start compression, drift tracking) and **OpenClaw** (ClawForge suite: intent-aware loading, memory hygiene, context profiler). Each gets its own optimizer because they have fundamentally different architectures. For other frameworks, the health check CLI works and the dashboard shows whatever data exists. Framework integrations ship as v2, prioritized by community demand.

**Tech decisions (with rationale):**

| Choice | Decision | Why |
|--------|----------|-----|
| **Web server** | **FastAPI** (not Flask, not http.server) | Async by default, auto-docs, fast. Flask is synchronous — blocking DB reads under load. http.server lacks routing. |
| **Frontend** | **htmx + minimal vanilla JS** (not Next.js, not React) | Dashboard is a read-heavy app with simple interactions (filter, click-to-expand). Next.js adds 100MB+ deps for what htmx does in 14KB. A React SPA is over-engineered for "show table, click row, see details." |
| **DB** | SQLite via stdlib `sqlite3` | Zero setup. Ships with Python. Handles 200 agents easily (~2M rows/year). No need for Postgres until >1000 agents. |
| **Charts** | Pure CSS bar charts + inline SVG sparklines | No charting library dependency. Token breakdown bars are just `width: X%` divs. Drift sparklines are `<polyline>` SVG. |

**Performance target:** Dashboard page loads in <500ms on a 2019 MacBook with 50 agents. No caching needed until >200 agents.

---

### 4.2 ClawForge — OpenClaw Context Optimizer

ClawForge is NOT a port of Chisel. Chisel solves "system prompt grew — which component?" by decomposing a reference file at session start. ClawForge solves a different problem: "my agent's context keeps growing — where's the bloat and how do I stop it?"

OpenClaw agents are persistent, file-driven, and workspace-oriented. Their context bloat comes from different sources than Hermes:

| Bloat Source | Chisel Approach | ClawForge Approach |
|---|---|---|
| MEMORY.md accumulation | N/A (Hermes has no equivalent file) | **Memory gardener** — periodic review: merge duplicates, archive stale, flag contradictions |
| Skill instruction sprawl | N/A | **Skill usage intelligence** — track which skills fire per turn; load full only for >20% usage |
| Workspace file creep | N/A | **Intent-aware loading** — classify incoming message, load only relevant files |
| Session-start bootstrap | Compress upfront | **Predictive compaction** — pre-response hook forecasts token usage, demotes low-value content |
| Token composition | Component breakdown (identity/skills/memory/tools/guidance) | **Source breakdown** — MEMORY.md / skills / workspace / history / bootstrapping |

#### 4.2.1 Core Philosophy

Don't compress everything upfront. Make context loading **lazy, intent-aware, and pluggable** via OpenClaw's ContextEngine lifecycle hooks. The goal is to keep the agent's effective context under 40–60% of its window while preserving capability.

| Principle | What It Means |
|-----------|---------------|
| **Lazy loading** | Never load what isn't needed. Classify intent first, load second. |
| **Hygiene over compression** | MEMORY.md gardening prevents bloat at the source instead of compressing after the fact. |
| **Predictive not reactive** | Pre-response hook forecasts token usage and triggers compaction before the turn, not after. |
| **Observable** | Every decision (loaded X, skipped Y, saved Z tokens) writes to the same SQLite the dashboard reads from. |

#### 4.2.2 ContextEngine Plugin

Drop-in plugin that hooks into OpenClaw's ContextEngine lifecycle:

| Hook | What ClawForge Does | Token Savings (est.) |
|------|---------------------|---------------------|
| **bootstrap** | Load minimal context: SOUL.md + core instructions + recent MEMORY.md summary. No full MEMORY.md. No full workspace. | 40–60% on first turn |
| **ingest** | Run intent classifier on incoming message. Load matching skills, matching MEMORY.md entries (vector search), matching workspace files. | 30–50% per turn |
| **pre-response** | Estimate current context + predicted response. If >85% of window: demote lowest-value content (oldest MEMORY entries, least-used skills, oldest conversation episodes). If >95%: trigger compaction. | Prevents OOM before it happens |

#### 4.2.3 ClawForge CLI Commands

| Command | What It Does | v1 Status |
|---------|-------------|-----------|
| `observeco clawforge profile` | Reads OpenClaw agent config, shows current context composition — MEMORY.md size, skill count, workspace file sizes, conversation history depth, estimated tokens per source | ✅ v1 |
| `observeco clawforge load` | Dry-run the intent-aware classifier on a message. Shows which sources would load, which would be skipped, and estimated token savings. `probe` flag: actually run it against a live agent. | ✅ v1 |
| `observeco clawforge garden` | Run memory hygiene: scan MEMORY.md for duplicates, contradictions, stale facts (>30d with no reads). Produces a report: "3 duplicates found, 1 contradiction, 2 stale entries." `--apply` flag: execute the suggestions. | ✅ v1 |
| `observeco clawforge history` | Show per-turn loading stats over time — tokens saved by intent-aware loading, skill usage frequency, MEMORY.md growth trend | ✅ v1 |

#### 4.2.4 Intent-Aware Loader (Core Innovation)

Before each agent turn, a lightweight classifier (keyword + embedding match, using a local tiny model) classifies the incoming message by intent:

| Intent Class | Sources Loaded | Sources Skipped |
|-------------|---------------|-----------------|
| **Debug / error fix** | Relevant skills (2-3), relevant MEMORY entries, workspace code files | All other skills, all other MEMORY, non-code workspace files |
| **Feature request** | Relevant skills + relevant MEMORY + feature-related workspace docs | History, code files, unused skills |
| **Status / summary** | SOUL.md + MEMORY.md summary + history summary | Full MEMORY.md, all skills, workspace files |
| **Configuration change** | Relevant config files + SOUL.md | MEMORY.md, skills, workspace code |
| **General query** | SOUL.md + relevant MEMORY entries + 1-2 most-used skills | Full MEMORY.md, all skills, workspace |

The classifier is pluggable — default is keyword + TF-IDF for speed (<10ms per classification). Optionally swap in a small embedding model for semantic matching.

#### 4.2.5 Skill Usage Intelligence

Track which skills fire per turn. After 50 turns of data:

| Usage Frequency | Skill Loading Strategy |
|----------------|----------------------|
| **>20% of turns** | Load full instructions |
| **5–20% of turns** | Load compressed version (auto-summarized from full instructions) |
| **<5% of turns** | Load name + purpose only. Fetch full on demand. |

This replaces Chisel's "token breakdown by component" with ClawForge's "token breakdown by data source" — a dashboard metric that makes sense for OpenClaw architecture.

#### 4.2.6 Memory Hygiene (ClawForge Garden)

Not "track how much memory grew this week" but "find and fix memory problems automatically."

| Metric | What It Measures | Dashboard Display |
|--------|-----------------|-------------------|
| **Memory debt score** | Weighted: duplicates × 0.3 + contradictions × 0.5 + stale entries × 0.2 | Single number (0-100). 0 = pristine. >50 = needs attention. |
| **Duplicate count** | Entries saying the same thing | "3 duplicates found in MEMORY.md" |
| **Contradiction count** | Entries saying opposite things (e.g., "agent uses GPT-4" vs "agent uses Claude") | "2 contradictions flagged — resolve?" |
| **Stale entries** | Entries with no reads in 30+ days | "5 entries are stale — archive?" |
| **Growth rate** | MEMORY.md byte size trend over time | Sparkline + absolute change |

#### 4.2.7 Dashboard Integration (OpenClaw Context Tab)

The dashboard already has three agent card metrics for both Hermes and OpenClaw agents — health, circuit, and "context." For ClawForge, the context metric shows:

| Card Metric | Hermes Agent Shows | OpenClaw Agent Shows |
|-------------|-------------------|---------------------|
| **Health dot** | 🟢 Pulse OK / 🟡 Warning / 🔴 Dead | Same |
| **Circuit** | Open / Closed / N/A | N/A (no circuit concept yet) |
| **Context status** | Token bar: ████ identity ████ skills ████ memory ██ tools ██ guidance | ClawForge score: `🧠 42` (memory debt 42/100) |

**Agent detail (expanded card) — Context tab:**

| Section | Hermes Shows | OpenClaw Shows |
|---------|-------------|----------------|
| **Breakdown** | Identity / skills / memory / tools / guidance bar chart | Source breakdown: MEMORY.md / skills / workspace / history / bootstrap |
| **Savings** | "CHISEL saved 3,412 tokens (22%)" | "ClawForge reduced per-turn context by 52% this session" |
| **Trend** | 7-day per-component drift | Memory debt score trend + skill usage heatmap + workspace bloat trend |
| **Garden** | N/A | "3 duplicates merged, 1 contradiction flagged, 2 stale entries archived" |

---

## 5. Color System

Dashboard colors are semantic, not decorative. Every hex value has a job.

| Role | Hex | Tailwind | Use |
|------|-----|----------|-----|
| **Healthy** | `#22c55e` | green-500 | Status dot, heartbeat OK, token savings (negative drift) |
| **Warning** | `#eab308` | yellow-500 | 1-2 missed heartbeats, drift >10%, near-threshold |
| **Critical** | `#ef4444` | red-500 | Dead agent, tripped circuit, hard failure |
| **Info / Baseline** | `#3b82f6` | blue-500 | Learning phase, no baseline yet, neutral information |
| **Token: Identity** | `#6366f1` | indigo-500 | Token breakdown bar — agent identity block |
| **Token: Skills** | `#8b5cf6` | violet-500 | Token breakdown bar — skills/tools section |
| **Token: Memory** | `#ec4899` | pink-500 | Token breakdown bar — memory/context block |
| **Token: Tools** | `#14b8a6` | teal-500 | Token breakdown bar — tool schemas section |
| **Token: Guidance** | `#f97316` | orange-500 | Token breakdown bar — guidance/prose section |
| **Token: Growth** | `#f97316` | orange-500 | Positive drift >5% (needs attention — distinct from Warning) |
| **Neutral** | `#6b7280` | gray-500 | Locked Pro tiles, empty states, placeholder text |
| **Background** | `#0f172a` | slate-900 | Dashboard background (dark theme default) |
| **Card bg** | `#1e293b` | slate-800 | Agent card backgrounds |
| **Border** | `#334155` | slate-700 | Card borders, dividers |

**Why two oranges?** `#eab308` (Warning yellow) is for pulse-related issues — missed heartbeats, degraded state. `#f97316` (orange) is for token growth specifically — a different category of concern. The eye learns to distinguish: yellow = "something is flaky right now," orange = "cost is creeping up."

**Color pairing rules:**
- Status dots use the Health/Warning/Critical palette (green/yellow/red)
- Token bars use the Token palette (indigo/violet/pink/teal/orange) — never green/yellow/red, which would confuse status with composition
- Positive drift (compression working = good) uses green `#22c55e`
- Negative drift (growing = bad) uses orange `#f97316`

---

## 6. Layout Wireframe

The dashboard is one page with three zones. No tabs, no separate views, no navigation.

```
┌────────────────────────────────────────────────────────────────┐
│ 🟢 Fleet Header (sticky top)                                  │
│ 12 agents  ◆  10 🟢 1 🟡 1 🔴  ◆  ⚠️ 2 tripped circuits  ◆  │
│ Tokens: +3.2% this week 📈                                     │
├────────────────────────────────┬───────────────────────────────┤
│ Left Rail: Agent Cards         │ Right Rail: Alerts Panel     │
│                                │                              │
│ 🟢 hound         12s ago      │ 🔴 CRITICAL                  │
│   Tokens: ████████ 4.2K      │  hermes-triage circuit        │
│   Drift: +3% ▁▂▃▅            │  tripped 3m ago               │
│   Error: —                    │                              │
│                                │ 🟡 WARNING                   │
│ 🟢 pragma         8s ago      │  kepler drift +18% this      │
│   Tokens: ████ 2.1K          │  week (threshold: 10%)        │
│   Drift: -1% ▃▂▁             │                              │
│   Error: —                    │                              │
│                                │ 🔵 INFO                      │
│ 🔴 hermes-triage  45s ago     │  hound heartbeat 2σ from     │
│   Tokens: ██████ 3.8K        │  baseline                     │
│   Drift: +5% ▃▄▆█            │                              │
│   Error: Failed tick #3       │                              │
│                                │ [🔒 Pro] Push delivery       │
│ 🟡 kepler         3m ago      │  enabled with Pro → learn    │
│   Tokens: ████████████ 8.1K  │  more                        │
│   Drift: +18% ▃▄▆█████       │                              │
│   Error: —                    │                              │
├────────────────────────────────┴───────────────────────────────┤
│ Error Timeline (last 24h) — filterable                         │
│                                                               │
│ ⚡ 03:15  kepler     Circuit trip     4 failures, auto-reset   │
│    ████████░░░░░░░░░░ 3m 12s resolved                          │
│ 💔 01:02  hermes-dev Heartbeat miss   2× missed, restored      │
│    ████░░░░░░░░░░░░░░ 1m 04s resolved                          │
│ 📈 00:47  kepler     Drift breach     +18.4% (threshold 10%)   │
│    ██████████████████ 14m 22s → ongoing                        │
└────────────────────────────────────────────────────────────────┘
```

**Layout rules:**
- **Fleet header is sticky** — never scrolls away. User always sees the fleet summary.
- **Left rail (agent cards) + right rail (alerts panel)** — the two most information-dense zones sit side by side. Right rail width: 320px fixed.
- **Error timeline full-width at bottom** — secondary investigation zone. Scroll or look down when things go wrong.
- **No tabs, no separate pages** — everything is on one scroll. The layout IS the navigation.

### 6.1 Fleet Header (Always Visible)

| Element | Source | Detail |
|---------|--------|--------|
| **Total agents** | pulse db | Count of registered agents |
| **Healthy / Warning / Critical** | pulse + circuit | Green >98% heartbeats in last 5m. Yellow 90-98%. Red <90% or any tripped breaker. |
| **Tripped circuits** | pulse circuit | Count of open breakers. Red badge if >0. |
| **Token drift** | chisel drift | `+X% this week` with up/down arrow. Red if >10%. |

The header answers the "5-second wow" — at a glance, is my fleet OK?

### 6.2 Agent Cards

Each agent gets one card. Default view shows all. Search/filter box at top.

| Column | Data | Source |
|--------|------|--------|
| **Agent name** | Name + role tag | Config |
| **Status dot** | 🟢 Pulse OK, 🟡 Heartbeat missed 1-2x, 🔴 Dead or circuit tripped | pulse check + circuit |
| **Last check-in** | Relative time ("12s ago", "3m ago") | pulse check |
| **Circuit** | Open / Closed / N/A + cooldown remaining | pulse circuit |
| **Token profile** | Mini bar: ████ identity ██████ skills ████ memory ██ tools ██ guidance | chisel trim |
| **Drift** | `+X% this week` with sparkline (7 tiny bars) | chisel drift |
| **Last error** | Most recent failure + timestamp | pulse circuit log |

Click a card → expands to detail view.

### 6.3 Agent Detail (Expanded Card)

Shown on click:

**Health tab:**
- Pulse history for last 24h (green/yellow/red dots timeline)
- Circuit trip events: timestamp, failure count at trip, recovery action taken
- Last 10 errors with timestamps and error messages
- Manual "Reset circuit" button (CLI equivalent: `pulse circuit reset <agent>`)

**Token tab:**
- Breakdown bar chart: identity / skills / memory / tools / guidance (absolute tokens + % of total)
- Before/after toggle: "CHISEL saved 3,412 tokens (22%) this session"
- 7-day drift line: per-component trend. Which component is growing fastest?
- "This agent's system prompt grew X% in 7 days" — bold if >5%

**Alerts tab:**
- Recent circuit trips (time, error count, recovery action)
- Drift threshold breaches (component, % change, date)
- Alert delivery config (Pro only — see §6)

### 6.4 Alerts Panel (Right Rail)

| Severity | Rule | Display |
|----------|------|---------|
| 🔴 Critical | Circuit breaker tripped | Pinned to top, red badge on header |
| 🟡 Warning | Drift >10% in any component | Listed in alerts panel |
| 🔵 Info | Agent heartbeat >2σ from baseline | Listed in alerts panel |

**Free:** Alerts display in-dashboard only.
**Pro:** Push delivery — Telegram, webhook, or CLI ping when alerts fire. No polling required.

### 6.5 Error Timeline

Reverse-chronological feed across ALL agents. Located full-width below the left+right rails.

| Element | Detail | Visual |
|---------|--------|--------|
| **Icon** | ⚡ Circuit trip / 💔 Heartbeat miss / 📈 Drift breach / ✅ Recovery | Icon prefix on each row, at a glance |
| **Time** | When the event occurred | Left-aligned, monospace |
| **Agent** | Which agent — clickable | Click → scrolls to and expands that agent's card |
| **Event** | Event type label | Circuit trip / Heartbeat miss / Drift breach / Recovery |
| **Detail** | Error message or circuit count | Descriptive text |
| **Duration bar** | Miniature Gantt bar: `████████░░░░░░ 3m 12s` | Visual time perception. Filled portion = duration, empty = resolved. Full bar = ongoing. |
| **Severity** | 🔴 Critical / 🟡 Warning / 🔵 Info | Row left border in severity colour |

**Row color coding by severity:**
- 🔴 Critical rows: red `#ef4444` 2px left border, red tinted background
- 🟡 Warning rows: yellow `#eab308` 2px left border, yellow tinted background
- 🔵 Info rows: blue `#3b82f6` 2px left border, blue tinted background

Filterable by: agent, event type, severity, date range.

### Pro Preview on Alert Rows

Each alert row that WOULD have triggered a push notification in Pro shows a subtle label:

```
⚡ 03:15  kepler    Circuit trip   4 failures, auto-reset
   ████████░░░░ 3m 12s resolved    [📡 Push] [🔒 Pro]
```

The `[🔒 Pro]` tag on each real alert is NOT a mockup. It's a real alert that was detected. The data exists. The free tier just can't deliver it. This is the conversion engine — every alert that fires with `[🔒 Pro]` is a micro-conversion opportunity.

---

## 6. Free vs Pro

### Free (MIT OSS — unlimited users, unlimited agents)

| Feature | Details |
|---------|---------|
| **Fleet view** | All agents, status dots, last check-in |
| **Token breakdown** | Per-agent bar chart, before/after toggle |
| **7-day drift** | Per-component trend line |
| **Error history** | Last 24h of errors per agent |
| **In-dashboard alerts** | Alerts visible in the UI (no push delivery) |
| **License** | MIT — fork, modify, embed freely. |

### Pro ($29/mo per deployment)

| Feature | Why Paid |
|---------|----------|
| 📡 **Alert relay** | Push notifications via Telegram, webhook, or CLI when circuits trip or drift exceeds thresholds. Free shows alerts in-dashboard; Pro delivers them to you. |
| 🕰️ **90-day history** | Error timeline, drift trends, pulse history extended from 7d to 90d |
| 📋 **Fleet comparison** | Side-by-side token profiles across all agents. "Hound is 42K, Kepler is 28K. Content Agent grew 200%." |
| 🎯 **Optimal budget planner** | "Recommended allocation for this agent: 82K total. Your current system prompt is 98K — save 16K by redistributing." Based on aggregated calibration data. |
| 🚨 **Drift alerts** | Proactive when any agent's system prompt grows beyond configurable threshold. |
| ⚡ **Circuit auto-recovery** | Configurable auto-reset after N minutes of cooldown (vs manual reset in free). |
| 🔄 **Multi-machine relay** | Agents on different machines report to one dashboard view. |
| 🔓 **Unlimited** | No cap on agents, history, or alert channels. |

### Enterprise (Custom pricing)

| Feature | Details |
|---------|---------|
| **SSO** | SAML/OIDC |
| **On-prem relay** | Self-hosted relay server, no outbound telemetry |
| **Custom calibration** | Calibration runs for proprietary agent configs |
| **API access** | Programmatic dashboard data export |

---

## 7. The Conversion Funnel

The dashboard IS the conversion engine.

- **Every Pro feature is visible** as a grayed-out card with exact description + price
- **Free users see their data** — they know if they have 7 agents, know their token drift is 18%, know they've had 3 circuit trips this week
- **Pro features use your REAL data** — "In the last 24h, this alert would have fired 3 times" (not mockups)
- **Upgrade CTA** — Stripe checkout with 30-day free trial. No charge at signup. Auto-converts at D+30 with email reminder at D+25. First 30 days free, then $9/mo Solo or $49/mo Team.

No dark patterns. No time bombs. No data hostage.

### 7.1 Locked Tile Interaction Design

Every Pro feature tile has four states:

| State | Visual | Behavior |
|-------|--------|----------|
| **1. Default (resting)** | 50% opacity grayscale. Feature name, icon, price badge visible. | Sits in the UI like a real element. User can see what it would show. |
| **2. Hover** | Opacity shifts to 80%. "Preview" button appears. Price badge stays. | Cursor indicates interactivity. No click-through yet. |
| **3. Preview modal (on click)** | Full-opacity modal showing the feature using the user's OWN data with a subtle watermark/overlay. | User sees exactly what they're missing, quantified with their numbers. |
| **4. CTA (on "Start free trial" click)** | Modal changes to: "Start your 30-day free trial — $9/mo Solo or $49/mo Team after trial. No charge today." | Stripe checkout with `trial_period_days=30`. Email reminder at D+25 before auto-convert. |

**Preview modal content for each Pro feature:**

| Pro Feature | Preview Content |
|-------------|----------------|
| 📡 **Alert relay** | "In the last 24h, 3 alerts would have pushed to you: (1) circuit trip at 14:02, (2) drift breach at 09:15, (3) heartbeat miss at 03:44." |
| 🕰️ **90-day history** | Shows the 7-day error timeline with a subtle "🔒 90-day history — 72 more days available with Pro" watermark across the right portion. |
| 📋 **Fleet comparison** | Shows 3 agents side-by-side with a `blur(8px)` overlay on agents 4+. "12 agents in your fleet — compare all with Pro." |
| 🎯 **Optimal budget planner** | "Your agent kepler is 8.1K tokens. Fleet calibration data suggests optimal allocation is 6.2K. Pro unlocks the recommendation." |
| 🚨 **Drift alerts** | "kepler drift at +18% was detected 14 minutes before any manual check. Pro would have alerted you immediately." |

The key insight: **these use the user's OWN data.** The preview modal is not a screenshot of someone else's dashboard.

### 7.2 Token Profile Bar — Visual Spec

The token bar on each agent card is NOT just a data point. It's a visual health signal.

**Component ordering:** Sorted by token count, largest first. The eye naturally goes to "what's using the most."

**Component colours — Hermes mode (Chisel decomposition):**

| Component | Hex | Bar Colour |
|-----------|-----|------------|
| Identity | `#6366f1` | ████ Indigo |
| Skills | `#8b5cf6` | ████ Violet |
| Memory | `#ec4899` | ████ Pink |
| Tools | `#14b8a6` | ████ Teal |
| Guidance | `#f97316` | ████ Orange |

**Component colours — OpenClaw mode (ClawForge source breakdown):**

| Source | Hex | Bar Colour |
|--------|-----|------------|
| MEMORY.md | `#ec4899` | ████ Pink |
| Skills | `#8b5cf6` | ████ Violet |
| Workspace | `#14b8a6` | ████ Teal |
| History | `#6366f1` | ████ Indigo |
| Bootstrap | `#f97316` | ████ Orange |

The palette is shared between modes — the labels change depending on which optimizer produced the data. The eye learns: pink = memory source, violet = skills source, teal = operational data, indigo = structural/identity data, orange = the "other" category (guidance in Hermes, bootstrap overhead in OpenClaw).

These are distinct from the status palette (green/yellow/red) to avoid confusion.

**Card rendering:**
- Total tokens shown as a number: `4.2K` right-aligned on the card
- Bar width = component tokens ÷ total tokens. Widths are relative within the card.
- No gaps between segments — bar is one continuous coloured strip
- Hover on any segment → tooltip shows component name + exact token count: "Skills: 1,847 tokens"

**Comparison mode (before/after toggle):**
- When toggled, the single bar splits into TWO **half-height bars** stacked vertically
- Top bar = before compression. Bottom bar = after compression.
- Each segment is the same colour in both bars. Difference in width = compression savings per component.
- A savings callout appears: "CHISEL saved 3,412 tokens (22%)"
- Toggle is ON by default if any session has compression data. OFF if all sessions are uncompressed.

### 7.3 Responsive Breakpoints

| Viewport | Layout Behavior |
|----------|----------------|
| **>1280px** (desktop) | Full three-zone: sticky header + left rail (agent cards) + right rail (alerts, 320px) + bottom timeline |
| **768-1280px** (laptop, iPad landscape) | Two-zone: left rail takes full width below header. Right rail collapses to a collapsible "Alerts" toggle button at top-right. Timeline below cards. |
| **<768px** (mobile, iPad portrait) | Single column. Agent cards switch to a **list view** (name + status dot + total tokens + last check-in only). No token bar or drift sparkline on cards. Filter/sort bar at top. Alerts as a collapsible panel. Timeline collapses to last 5 events with "view all" link. |
| **All** | Fleet header collapses to a single summary row on narrow screens: "12 agents · 10 🟢 1 🟡 1 🔴  · ⚠️ 2 trips" |

No hamburger menus. No separate mobile views. Everything is the same page, just reflowed.

### 7.4 Error State Designs

| Scenario | What User Sees | What Happens Next |
|----------|---------------|-------------------|
| **Pulse DB corrupted** | Banner at top of dashboard: "⚠️ Health data may be stale — pulse.db read error. Run `observeco doctor` to diagnose." Cards show last-known-good data with gray status dots. | CLI tool `observeco doctor` checks DB integrity, reports corruption, and offers to rebuild from pulse log if available. |
| **Monitor daemon died** | Banner: "⚠️ Monitoring stopped 2h 14m ago. Data shown is from last checkpoint. Run `observeco start` to resume." Agent cards show "last check-in: 2h ago" in gray. No new status dots. | `observeco start` re-launches the background daemon. Resume without data loss. |
| **Config file unreadable** | Banner: "Could not read `~/.observeco/agents.json` — check file permissions." Dashboard loads with 0 agents and shows the manual add prompt instead. | User fixes permissions or re-runs `observeco agents add`. Configuration is never silently ignored. |
| **No agents configured** | (Handled in first-run — see §8) Setup mode. Not an error state. | Guided add flow. |
| **pulse.db doesn't exist yet** | (Handled in first-run — see §8) Three-phase progressive loading. Not an error state. | Auto-creates on first pulse tick. |

**Visual treatment for all banners:**
- Fixed-position banner below the fleet header
- Icon prefix: ⚠️ for warnings, ❌ for critical
- Background: `#fef2f2` (red-50) for critical errors, `#fefce8` (yellow-50) for warnings
- Action link always provided — never a dead-end error message

Every error state gives the user a next action, not just a red banner.

---

## 8. First-Run Experience

What happens when a new user runs `observeco dashboard` for the first time:

1. CLI checks `~/.observeco/` — empty → enters setup mode
2. Shows: "No agents configured. Discover automatically or add manually?"
3. If auto-discover chosen: scans cwd + home for agent configs. Lists found agents.
4. If manual: prompts for agent name + check command/URL
5. Writes config to `~/.observeco/agents.json`. Starts pulse monitoring immediately.
6. Dashboard opens in browser. Fleet header shows "1 agent — learning baseline..."
7. After first pulse tick (~30s), status dots turn green/yellow/red.
8. First chisel data appears after first agent session. Token breakdown starts populating.

**Empty state design:** Dashboard never shows a blank page. Three progressive phases:

| Time | What User Sees |
|------|---------------|
| **0-10s** (after install) | Animated placeholder cards: "Observing your fleet — discovering agents..." Agent names detected from config scan shown in gray |
| **10-90s** (pulse starting) | Status dots appear one by one as first heartbeats arrive. Yellow (no baseline yet). Fleet header shows "Learning baseline..." |
| **90s+** (first data) | Green/yellow/red dots stabilize. Token profile bar shows "No token data — run Hermes agents to see breakdown." Non-Hermes users see this permanently (the CLI + dashboard still work for health checks). First chisel data appears after first Hermes session. |

The user always knows what phase they're in and what to expect next. No silent waiting.

---

## 9. The Moat: Bidirectional Observability

### 9.1 The Broken Premise

Every observability tool shares the same broken assumption: **observability is read-only.** They collect data, display it, and leave the human to act.

This is wrong for AI agents. Agents self-modify. Their behavior degrades non-monotonically (context bloat, skill drift, prompt rot). A human checking a dashboard every morning is too slow — by the time you see the degradation, the agent has been producing bad output for hours.

**Traditional observability:**
```
Agent → Metrics → Dashboard → Human sees → Human fixes  (minutes to hours)
```

**ObserveCo v2 (Bidirectional):**
```
Agent → Metrics → Detector → Healer → Agent fixed  (seconds)
```

### 9.2 The Three Moat Pillars

ObserveCo is not a monitoring dashboard. It is a **runtime integrity layer for AI agents** — it detects degradation, heals it, documents what happened, and lets other agents query the history. No competitor can copy this because they're all cloud-based and can't touch your filesystem.

| Competitor | Why they can't heal | Why they can't snapshot | Why they can't MCP |
|------------|---------------------|------------------------|---------------------|
| **Arize Phoenix** | Cloud SDK — can't SSH into your machine | No auto-discovery to render | No local data to expose |
| **LangFuse** | Python SDK wrapping — can't restart daemons | No fleet data to compose | No agent-aware protocol |
| **Helicone** | Proxy-based — can't modify agent configs | No context or drift data | Proxy intercepts don't know agent state |
| **OpenLIT** | Cloud dashboard — can't execute recovery | No memory hygiene data | No local-first architecture |
| **ObserveCo** | Local-first with CLI access to the host | Has auto_detect + pulse + chisel + garden data | Already runs locally and discovers all agents |

### 9.3 Pillar 1: Self-Healing (`observeco heal`)

**Tension strategy:** This is the headline feature — the thing that changes the product category. It does NOT ship in v0. What ships instead is the *preview*: observation mode that detects the same patterns, diagnoses the same root causes, but stops at a yellow banner saying "Run `observeco heal` to auto-fix." Users see exactly what would happen. The only missing piece is the user's permission to execute. By v1.1, they've already seen the tool correctly diagnose 10+ failures and trust it enough to flip the switch.

| v0 ships | v1.1 adds | Why this builds tension |
|----------|-----------|------------------------|
| **Observation mode** — detects crash patterns, drift, memory debt; writes yellow banner with suggested command | Auto-execution of same diagnosis+fix pipeline | User sees "the tool knew what was wrong and I had to click vs it just fixed itself" — makes them impatient for automation |
| Dashboard banners: "Agent Kepler: 3 memory errors detected. Suggested: restart with memory cap" | One-click apply from banner, then fully autonomous | Each banner is a reminder that the tool is smarter than most users expect |

**What's fully specced for v1.1 (complete design below):**

```python
# v1.1 — includes circuit breaker on heal and snapshot-before-restart

HEAL_CIRCUIT = {}  # agent_name -> {failures: int, last_failure: timestamp, cooldown_until: timestamp}
MAX_HEAL_RETRIES = 3
COOLDOWN_HOURS = 4

def heal_cycle(agent_name, status, db):
    # --- Circuit breaker check ---
    record = HEAL_CIRCUIT.get(agent_name, {"failures": 0, "cooldown_until": 0})
    if time.time() < record["cooldown_until"]:
        db.write_healing_event(agent_name, "circuit_open", "escalation_mode — manual acknowledgment required")
        return  # Do nothing. Human must acknowledge.
    
    if status == "dead":
        # --- Snapshot before restart ---
        try:
            snapshot_before = observeco.snapshot(agent_name, prefix=f"pre-heal-{agent_name}")
        except Exception:
            pass  # Best-effort — don't let snapshot failure block heal
        
        last_five = db.get_recent_errors(agent_name, 5)
        try:
            if all("out of memory" in e for e in last_five):
                restart_agent(agent_name, env={"PYTHONMEM": "512m"})
                action = "restarted_with_cap"
            elif all("module not found" in e for e in last_five):
                subprocess.run(["pip", "install", "-e", "."], cwd=agent_repo, check=True)
                restart_agent(agent_name)
                action = "module_installed"
            elif all("timeout" in e for e in last_five):
                db.set_cooldown(agent_name, 300)
                action = "cooldown_set"
        except Exception as e:
            # --- Heal failed — increment circuit breaker ---
            record["failures"] += 1
            if record["failures"] >= MAX_HEAL_RETRIES:
                record["cooldown_until"] = time.time() + (COOLDOWN_HOURS * 3600)
                # Write critical flag for human acknowledgment
                with open(f"intelligence/flags/{agent_name}-heal-failure.flag", "w") as f:
                    f.write(f"CRITICAL: {agent_name} heal failed {record['failures']}x. "
                           f"Last error: {e}. Circuit open until {record['cooldown_until']}.")
            HEAL_CIRCUIT[agent_name] = record
            db.write_healing_event(agent_name, "heal_failed", str(e))
            return
        
        db.write_healing_report(agent_name, action_taken, success)
    elif drift > threshold:
        trim_result = run_trim(agent_name)
        db.write_healing_event(agent_name, "context_drift", f"trimmed {trim_result.savings} tokens")
```

**v1 state:** Observation-only — daemon detects degradation, writes recommendations to dashboard (yellow banners with suggested action). Does NOT execute.

**v1.1 state:** Opt-in execution (`observeco heal` ships as a new CLI command). Daemon monitors, suggests, and when `--auto-heal` is set, executes. Includes circuit breaker on heal itself (3 failures in 1h → escalation mode: write critical flag, no retry for 4h, human must acknowledge).

**Critical safety requirement — snapshot before restart:** Before any heal action that restarts a process (memory cap restart, module install restart), the heal pipeline MUST save an investigation dump:

```python
# Required: snapshot state BEFORE destructive action
investigation_path = f"~/.observeco/heal/{agent_name}-{timestamp}.investigation.md"
investigation = f"""
# Heal Investigation: {agent_name}
## Triggered at: {timestamp}
## Diagnosis: {diagnosis}
## Action: {action_taken}
## Pre-heal state:
- Last 3 errors:
  1. {last_three[0]}
  2. {last_three[1]}
  3. {last_three[2]}
- Last 5 health ticks: {recent_ticks}
- Last known config: {agent_config}
"""
write_investigation(investigation_path, investigation)
```

**Why this is safety, not overhead:** A heal that restarts an agent mid-signal-write destroys evidence of what went wrong. A heal that restarts an OpenClaw agent mid-MEMORY.md write risks file corruption. By saving the last 3 signals, errors, and state before restarting, every heal action produces an auditable trace. This is the #1 reason enterprise monitoring tools are read-only — they don't want liability for destruction. ObserveCo's pre-heal snapshot removes that objection and becomes a marketing asset: "Every healing action preserves the evidence. You can audit exactly what happened."

### 9.4 Pillar 2: Living Snapshot (`observeco snapshot`)

**Target:** v1.1 (D+14)

**Tension strategy:** The snapshot feature is a distribution play — it auto-generates the launch post. It cannot ship without 7+ days of real drift data, which means it physically cannot exist on D-0. But the preview ships: the dashboard already visualizes the same data (drift bars, error timeline, architecture diagram). Users see the individual pieces and can imagine what the full snapshot would look like. The dashboard IS the v0 preview of the living document.

**What's fully specced for v1.1 (complete design below):**

```bash
observeco snapshot --name "7-agents-one-mac-mini" --out launch-paper/
```

**Generated artifacts:**

| Artifact | Source | What It Proves |
|----------|--------|----------------|
| `architecture.svg` | Auto-discovered from Hermes config + ecosystem.json (0-30s after install) | "No agents discovered yet — run `observeco pulse check`" | Shows real agents, real connections, real health endpoints — not a mockup |
| `dependency-graph.svg` | Computed from pulse check history (needs 1+ hours of data) | "Not enough data — check back after agents have been running for at least 1 hour" | Shows which agents communicate with which — real data flow |
| `token-evolution-chart.svg` | From chisel trim history over 7+ days | "Token data accumulates over ~7 days — run `observeco chisel trim` periodically" | Proof that context bloat is real — not a simulated chart |
| `error-timeline.svg` | From pulse log error events | "No error events recorded yet — this is good news" | Real incident frequency — not hand-picked examples |
| `self-healing-log.md` | From observeco heal recovery attempts | "No self-healing events recorded" | The tool fixing itself — alerts that auto-resolved |
| `README.snapshot.md` | Auto-generated narrative from all data | "Snapshot data incomplete — run command again when agents have been monitored longer" | Drafts the actual blog post: "7 agents, 1 Mac Mini, 0 human intervention" |

**The HN pitch:** "We didn't write a launch post. We ran `observeco snapshot` on our live ecosystem and it wrote one for us. Here's 7 real AI agents, their actual health data, real error timelines, and proof that our tool fixes its own problems. The diagram? It's not a mockup — it's generated from running pulse check on actual agents."

**Code complexity:** ~400 lines in `src/observeco/cli/snapshot.py`. Uses existing data, just formats it differently.

### 9.5 Pillar 3: MCP Discovery Protocol (`observeco mcp serve`)

**Target:** v1.1 (D+14)

**Tension strategy:** MCP is the least urgent for v1 adoption — most users don't have MCP clients yet. But the v0 dashboard serves as the preview: health data is available via the FastAPI REST endpoints that the dashboard itself consumes. When users ask "can I query this programmatically?" the answer is "yes — via the dashboard API. The full MCP protocol ships in v1.1." The API endpoint IS the v0 preview.

**What's fully specced for v1.1 (complete design below):**

```bash
observeco mcp serve
# Starts an MCP server on port 9120
# Auto-discovers all Hermes + OpenClaw agents
# Exposes resources:
#   observeco://<agent>/health     -> latest health status
#   observeco://<agent>/config     -> agent config file
#   observeco://<agent>/errors     -> recent error timeline
#   observeco://<agent>/context    -> system prompt token breakdown
#   observeco://fleet              -> all agent summaries
#   observeco://alert/<rule>       -> triggered alert rules
```

**Why this is defensible:**
1. **Dogfooding.** Hermes agents can MCP-query "what's my health?" — the ecosystem gains self-awareness. Dreamer's walks mention "Hound's pulse dropped 20% today."
2. **Interop.** Any MCP client (Claude Desktop, continue.dev, Cursor) can query the agent fleet. This is the "API-first" approach to observability without building a separate REST API.
3. **Launch hook.** "ObserveCo comes with an MCP server. Any AI tool can ask it about agent health." Positions ObserveCo as the data plane for agent systems, not just a dashboard.
4. **Switching cost.** Once users have CI/CD, dashboards, and MCP servers all pointed at ObserveCo, switching costs are significant.

**Code complexity:** ~300 lines implementing the MCP stdio protocol from scratch. **Do NOT add MCP as a pip dependency** — verify `pip install mcp>=1.0` succeeds first. The `mcp` Python package on PyPI is the OpenModelContextProtocol, which is a very young protocol — if it doesn't exist or the version is below 1.0, implement the stdio protocol directly (~500 lines). The protocol itself is simple JSON-RPC over stdin/stdout: `{"jsonrpc": "2.0", "method": "resources/read", "params": {"uri": "observeco://fleet"}, "id": 1}`.

**Protocol version pin:** Document which MCP version ObserveCo implements. The protocol evolves fast — unpinned docs produce broken installs. Pin in pyproject.toml as an optional dependency: `mcp = ["observeco>=1.0"]` only if it actually exists on PyPI.

### 9.6 The One-Sentence Thesis

**v1 thesis (ships now):**
> **Runtime observability for your AI agents — health checks, token profiling, drift tracking, OTel ingestion, auto-collection — all in one `pip install`.**

**v1.1 thesis (D+14):**
> **We don't just show you your agents are broken — we fix them, tell you what happened, and let your other agents ask about them.**

No competitor can say either. They're all cloud-based and read-only. Launching with the v1 thesis and upgrading to the v1.1 thesis at D+14 creates a second distribution wave and lands self-healing on users who've experienced the pain firsthand.

---

## 10. Competitor Positioning

| Tool | What it does | Gap ObserveCo fills |
|------|-------------|-------------------|
| **Datadog** | General infra monitoring — servers, containers, APM | Not designed for AI agents. Doesn't understand tokens, system prompts, or circuit breakers. $15+/host/mo. |
| **Grafana + Prometheus** | Time-series metrics | Requires setup (Prom server, exporters, dashboards). No agent-specific semantics. |
| **New Relic** | APM + infra | Cloud-only. $0.30/hr per host. No offline/local mode. |
| **Simple health checks** (uptimerobot, cron) | Ping/HTTP only | No token profiling, no circuit breaker, no drift detection. Binary alive/dead. |
| **ObserveCo** | Agent-native observability | Two first-class agent frameworks: Hermes (Chisel suite: component decomposition, session compression, drift) and OpenClaw (ClawForge suite: intent-aware loading, memory hygiene, skill intelligence). Circuit breaker aware. Works offline. `pip install` in 60 seconds. Health checks work for any agent with an endpoint. |

**The wedge:** Everyone running agents has the same two problems — "are my agents OK and why did my bill go up this month?" Every other tool answers half the question. ObserveCo answers both from one SQLite file.

---

## 10. Performance Expectations

| Load Level | Agents | Dashboard Load Time | DB Size (1yr) | Notes |
|-----------|--------|-------------------|---------------|-------|
| Solo | 1-3 | <100ms | <5MB | Instant |
| Team | 4-20 | <200ms | <50MB | No concerns |
| Fleet | 21-100 | <500ms | <250MB | Indexes needed on pulse timestamp + agent_id |
| Large | 101-500 | <2s | <1.5GB | Consider archive-old-data toggle or Postgres |
| Enterprise | 500+ | N/A | >3GB | Multi-machine relay + Postgres recommended |

**Indexing strategy:** SQLite gets indexes on `(agent_id, timestamp)` for pulse, `(agent_id, date)` for daily aggregates. Prerequisite: `CREATE INDEX` at init.

---

## 11. Success Criteria (How We Know It's Good)

| Metric | Target | Measurement |
|--------|--------|-------------|
| Install-to-first-data | <60 seconds | Timer from `pip install` to dashboard showing green dots |
| Dashboard load | <500ms on 50 agents | Lighthouse-style perf test |
| First-run confusion | 0 setup questions | User never asks "how do I add an agent?" |
| Pro curiosity | >30% of free users click a grayed-out tile | Dashboard click tracking (local only, opt-in) |
| Alert usefulness | <5% false positive rate on drift alerts | Tracked vs ignored alert ratio |
| Error timeline accuracy | Errors match agent logs | Cross-check against agent's own error output |

---

## 12. What's NOT in v1 (and What IS)

### Ships v1 (Launch)

| Feature | Section | Priority |
|---------|---------|----------|
| Dashboard (fleet view, health dots, token bars, drift, error timeline, memory garden) | §1-8 | **P0 — launch** |
| CLI (pulse, chisel, clawforge, watch, agents) | §4 | **P0 — launch** |
| OTel /v1/traces endpoint | §4 | **P0 — launch** |
| Stripe billing (Solo $9/mo, Team $49/mo, 30-day trial) | §6 | **P0 — launch** |
| Heal observation mode (detects, suggests fixes, does NOT execute) | §9.3 | **P0 — launch** |

### NOT in v1 (held back for tension — fully specced for v1.1)

| Scope | Rationale (Tension Strategy) | Target |
|-------|-----------|--------|
| `observeco heal` (auto-heal execution) | Headline feature — deliberately held back. v0 ships detection+banners that show users *exactly* what auto-heal would do. Every banner builds trust and creates impatience. By v1.1, users have seen 10+ correct diagnoses and are asking "why can't it just DO it?" | **v1.1 (D+14)** |
| `observeco snapshot` (living documentation) | Distribution play — cannot ship without 7+ days of drift data. v0 preview: dashboard already visualizes drift bars, error timelines, architecture. Users see the pieces and imagine the whole. | **v1.1 (D+14)** |
| `observeco mcp serve` (MCP protocol) | Network effects play — most users don't have MCP clients at launch. v0 preview: FastAPI REST endpoints that power the dashboard. When users ask for programmatic access, MCP serves their demand. | **v1.1 (D+14)** |
| Multi-cloud agent relay | Requires hosted infrastructure | Post-revenue |
| SSO / SAML / OIDC | Enterprise-only | v2 |
| Plugin hub / admission gate | Network-effects play | v2 |
| Tracing / deep profiling | Beyond health + context scope | v1.1 |
| Mobile app | Dashboard is responsive web | v1.1 |
| Autonomous heal mode (no approval) | Safety — opt-in only for v1 | v1.1 |
---

## 13. User Stories (Prioritized)

| # | Story | v1 or v2 |
|---|-------|----------|
| 1 | As a solo dev, I install `pip install observeco` and `observeco dashboard` shows my agents running. | v1 |
| 2 | As a fleet owner, I see at a glance if any agent is down or has a tripped circuit breaker. | v1 |
| 3 | As a developer, I can see exactly which component is consuming the most tokens in each agent's system prompt. | v1 |
| 4 | As a team lead, I see that Kepler's system prompt grew 18% this week and can investigate. | v1 |
| 5 | As an operator, I see the last error each agent hit and when. | v1 |
| 6 | **As an OpenClaw agent operator, I see my agent's memory debt score and know exactly which files are bloating my context.** | v1 |
| 7 | **As an OpenClaw developer, I run `observeco clawforge load --probe` and see what my agent would load before it loads it.** | v1 |
| 8 | **As an OpenClaw fleet owner, I see skill usage intelligence across my agents and know which skills are never used.** | v1 |
| 9 | **As an OpenClaw operator, ClawForge Garden finds and flags memory contradictions I didn't know existed.** | v1 |
| 10 | As a Pro user, I get a Telegram ping when a circuit trips instead of polling the dashboard. | v1 Pro |
| 11 | As a Pro user, I see side-by-side context profiles across my 12 agents and know which needs optimization. | v1 Pro |
| 12 | As a Pro user, I get proactive alerts when drift exceeds a threshold I set. | v1 Pro |

---

## 14. Dependencies & Risks

| Dependency | Status | Risk |
|-----------|--------|------|
| Python 3.10+ | ✅ Guaranteed by pulse / chisel CLIs already | Low |
| SQLite | ✅ Built into Python stdlib | Low |
| FastAPI | ✅ Chosen — async, lean, auto-docs | Low — proven |
| htmx | ✅ Chosen — 14KB, no build step, perfect for read-heavy UIs | Low — proven |
| Stripe billing | ✅ **UNBLOCKED** — Sean can get Stripe within 2 weeks. Ships D-0. |
| Multi-machine relay | ❌ Not in v1 | Design decision, not risk |
