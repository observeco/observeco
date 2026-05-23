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

## 9. The Moat (Why This Isn't Built in a Weekend)

An engineer CAN build "show agents from SQLite, red/green dots" in a weekend. The moat is not the code. It's what the code collects over time.

| What's Easy to Clone | What's Not |
|---------------------|------------|
| Agent list from config | **Circuit breaker as a primitive** — self-healing failure gate with configurable cooldown, exponential backoff, and auto-reset. Not just "is it alive." |
| Red/green status dots | **Token composition data (Hermes)** — per-component breakdown (identity vs skills vs memory vs tools vs guidance) collected from real agent sessions. No other tool understands this. |
| SQLite time-series store | **Intent-aware loading (OpenClaw)** — classifier that decides what to load per message. Requires understanding agent architecture, not just reading a config file. |
| HTTP health checks | **Memory hygiene (OpenClaw)** — ClawForge Garden that finds duplicates, contradictions, and stale entries in MEMORY.md. Automated, not manual. |
| "Token profile" bar chart | **Skill usage intelligence** — tracking which skills fire per turn and auto-summarizing based on usage frequency. 50-turn baseline is real agent operation. |
| Simple uptime monitoring | **Drift detection baseline** — what "normal" drift looks like requires running across hundreds of sessions. Fleet-aggregated calibration data. |
| Status page widget | **Alert signal routing** — not just "send an email." Telegram push, webhook relay, CLI ping. Designed for how agent operators actually work. |

**The library is the data collector. The dashboard is the product. The calibration data is the moat.**

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

## 12. What's NOT in v1

| Scope | Rationale |
|-------|-----------|
| Multi-cloud agent relay | Requires hosted infrastructure. Post-revenue. |
| SSO / SAML / OIDC | Enterprise-only. Not needed for OSS adoption. |
| Stripe billing integration | ✅ **UNBLOCKED** — Sean can get Stripe within 2 weeks. Ships D-0. Checkout + webhook + trial logic built into dashboard. Pro tiles wired to real Stripe checkout. |
| Plugin hub / admission gate | Network-effects play. Premature without users. |
| Tracing / deep profiling | Beyond "is it alive + what's in its context." v2 feature. |
| Mobile app | Native apps are expensive. Dashboard is a responsive web app. |

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
