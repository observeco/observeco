# ObserveCo Dashboard — Complete Design Brief for Claude Design

> **Handoff date:** 2026-06-30
> **Product:** ObserveCo — Runtime observability for AI agents
> **Current version:** v0.3.0 "Hermes Beachhead"
> **Stack:** Python 3.10+ / FastAPI / htmx / SQLite / Chart.js (server-side Jinja2 templates, NOT React)
> **Target:** Design a dashboard that surfaces the richest possible insights from the data we actually collect
> **Current dashboard:** 6,500-line monolithic `templates/index.html` with 9 flat tabs — needs scalable UX architecture

---

## 0. The Product & Its Data

### 0.1 What ObserveCo Does

ObserveCo monitors a fleet of AI agents running on a local machine (typically a Mac Mini). It runs as a background daemon (`observeco watch`) that polls agents every 30 seconds, scrapes their config files (SOUL.md), and logs everything to a local SQLite database. The dashboard reads from this single database.

**The positioning:** "Tells you if your Hermes agents are working, what they're doing, and where your money goes."

**The user:** A solo developer or small team running 5-20 AI agents on one machine. They open the dashboard at 3am because an agent stopped responding. They need to know in 5 seconds: is my fleet OK? And in 30 seconds: what do I do about it?

**Key differentiators vs competitors (Datadog, Grafana, LangFuse):** Local-first (no cloud, no telemetry), understands AI agent semantics (tokens, context windows, prompt drift, circuit breakers, auto-heal), and is bidirectional — not just "show problems" but "fix them."

### 0.2 The Live Data (from Sean's real fleet, 2026-06-30)

| Data Source | Row Count | What It Means |
|---|---|---|
| `token_logs` | **215,238** | Every LLM call made by every agent — tokens in/out, model, cost, component breakdown |
| `chisel_trims` | **245,399** | Every snapshot of every agent's SOUL.md decomposed into identity/skills/memory/tools/guidance |
| `chisel_drift` | **163,560** | Week-over-week change per component per agent (+3% tokens in skills this week) |
| `pulse_log` | **13,438** | Health check results every 30s per agent — alive/dead/error + latency |
| `clawforge_garden` | **3,158** | Memory hygiene scans — duplicates found, contradictions flagged, stale entries |
| `trace_spans` | **1,639** | OTel distributed tracing spans — agent-to-agent handoff chains |
| `errors` | **672** | Every failure event with classified error type and severity |
| `compress_log` | **650** | Every compression run — before/after token counts, savings %, mode (lite/full) |
| `alert_log` | **200** | Every alert delivered — which channel, what event, delivery status |
| `l2_trending` | **280** | Proactive degradation signals — memory bloat, stuck agents, upstream failures |
| `heal_events` | **1** | Heal actions taken — auto-restart, L2 trim, garden cleanup |
| `pathway_nodes/edges` | **111 nodes, 80 edges** | Communication topology — which agents talk to which, via what mechanism |
| `turn_log` | **0** | (Empty — legacy table, data now in token_logs) |

**What this means for UX:** We have RICH data. 215K token records, 245K component snapshots, 163K drift data points, 13K pulse checks. The dashboard is NOT starved for data. The challenge is surfacing the RIGHT insights from this firehose without overwhelming the user.

---

## 1. The Complete Data Model — What Exists & What Questions It Answers

### 1.1 Core Tables

#### `pulse_log` — Agent Health Heartbeats (13,438 rows)
```sql
agent_name, status (alive|dead|error), latency_ms, error_message, timestamp, instance_id, metadata
```
**Answers:** Is agent X alive? How long has it been down? What was the error? Is the watch daemon itself healthy?

#### `circuit_breakers` — Failure Trip State (0 rows currently — no agents down)
```sql
agent_name, failure_count, max_retries=3, tripped, cooldown_until, last_failure
```
**Answers:** Has agent X failed too many times? Is the guard stopping checks? When will it retry?

#### `errors` — Classified Failures (672 rows)
```sql
agent_name, error_type (timeout|connection_refused|resource_not_found|http_5xx|other),
severity (info|warning|error|critical), error_message, timestamp
```
**Answers:** What's breaking? Is it a new error pattern or recurring? Which agents are most error-prone?

### 1.2 Token & Context Tables (The Rich Data)

#### `token_logs` — Per-LLM-Call Records (215,238 rows — THE richest table)
```sql
agent_name, turn_id, total_tokens, input_tokens, output_tokens,
cache_creation_tokens, cache_read_tokens,
identity_tokens, skills_tokens, memory_tokens, tools_tokens, guidance_tokens,
model, provider, cost, latency_ms, tool_calls (JSON array),
source (watch|otel|manual|unknown), session_id, workflow_name, service_name,
anomaly_score, recorded_at
```
**Answers:** How many tokens did Kepler use today? Which model costs the most? What's the cache hit rate? Which component (skills/memory/tools) is growing fastest? Are any calls anomalously expensive? What tools are used per turn?

**Critical UX insight:** The `source` column tells us HOW we got the data:
- `watch` (153,905 rows) = has full component breakdown (identity/skills/memory/tools/guidance) — parsed from SOUL.md
- `otel` (12,884 rows) = has input/output/cache but NO component breakdown — from OTel traces
- `manual`/`unknown` = from CLI or fallback — variable quality

The dashboard MUST show data quality confidence to the user.

#### `chisel_trims` — Component Snapshots (245,399 rows)
```sql
agent_name, identity_tokens, skills_tokens, memory_tokens, tools_tokens, guidance_tokens,
total_tokens, savings_ratio, mode, timestamp
```
**Answers:** What did hound's SOUL.md look like yesterday vs today? Which component grew? Did compression help?

#### `chisel_drift` — 7-Day Change Detection (163,560 rows)
```sql
agent_name, component (identity|skills|memory|tools|guidance),
current_tokens, week_avg_tokens, delta_pct, breached, timestamp
```
**Answers:** Which agent's system prompt is growing? Is skills bloat >10%? Should the user be warned?

#### `compress_log` — Compression History (650 rows)
```sql
agent_name, mode (lite|full), before_tokens, after_tokens, savings, savings_pct,
file_path, backup_path, triggered_by, timestamp
```
**Answers:** How many tokens has compression saved total? What's the fleet-wide savings? Is Lite or Full mode more effective?

### 1.3 Memory & Context Tables

#### `clawforge_garden` — Memory Hygiene (3,158 rows)
```sql
agent_name, duplicates, contradictions, stale_entries, debt_score (0-100),
memory_md_size, timestamp
```
**Answers:** Is an agent's memory becoming inconsistent? Are there contradictions the user should fix? What's the memory debt trend?

#### `clawforge_profiles` — Context Composition
```sql
agent_name, memory_md_size, skill_count, workspace_files, history_depth,
total_estimated_tokens, timestamp
```
**Answers:** How big is each agent's context? Which agent has the most skills? Which has the deepest history?

### 1.4 Healing & Recovery Tables

#### `heal_events` — Auto-Heal Actions (1 row — feature is backend-built, UI not yet shipped)
```sql
agent_name, event_type (l1_restart|l2_trim|l2_garden|circuit_reset|manual_heal|escalation),
status (success|failure|escalated|cooldown), duration_ms, details, created_at
```
**Answers:** Did auto-heal fix this crash? How long did recovery take? What was the diagnosis?

#### `l2_trending` — Proactive Degradation Signals (280 rows)
```sql
agent_name, trend_type (memory_bloat|stuck|drift|upstream_fail),
signal_label, severity, metric_value, threshold, auto_action, resolved, timestamp
```
**Answers:** Is an agent slowly getting worse? Was it caught before the user noticed? Did auto-heal resolve it?

#### `heal_config` — Per-Agent Heal Settings
```sql
agent_name, auto_heal, auto_heal_l2, max_restarts_per_hour, drift_threshold, memory_debt_threshold
```
**Answers:** What are the heal thresholds per agent? Is auto-heal enabled? Should we warn the user that it's off?

### 1.5 Alert & Notification Tables

#### `alert_subscriptions` — Delivery Channels
```sql
channel (telegram|webhook|email|discord), target, event_types, enabled
```
**Answers:** Where do alerts go? Which channels are active? What event types get delivered?

#### `alert_log` — Delivery History (200 rows)
```sql
channel, target, event_type, message, delivered, delivery_error, created_at
```
**Answers:** Did the Telegram alert actually arrive? Is a channel failing? What was the last alert sent?

### 1.6 Topology & Trace Tables

#### `pathway_nodes` + `pathway_edges` — Communication Map (111 nodes, 80 edges)
```sql
nodes: id, name, type (filesystem|cron|agent|platform|consumer|router|daemon|watcher|gateway|service)
edges: source_id, target_id, status (green|yellow|red|teal|unknown), mechanism, confidence
```
**Answers:** How do agents communicate? Which connections are broken? Where are the dead ends?

#### `trace_spans` — OTel Distributed Traces (1,639 rows)
```sql
trace_id, span_id, parent_span_id, agent_name, span_name,
start_time_ns, end_time_ns, status, attributes (JSON)
```
**Answers:** What's the full chain when agent A delegates to agent B? Where's the bottleneck? Which hop failed?

### 1.7 Licensing & Billing Tables
```sql
token_pricing: provider, model, input_per_1m, output_per_1m, cache_read_per_1m
llm_provider_registry: 13 providers (8 cloud + 5 local) with base URLs and default models
agent_kill_log: manual kill switch audit trail
self_monitor_budget: ObserveCo's own LLM usage tracking
```

### 1.8 The Dashboard MUST Answer These Questions (from the data above)

| Tier | Question | Data Source | Current Answer? |
|---|---|---|---|
| **5-second** | Is my fleet OK? | `pulse_log` + `circuit_breakers` | Partial — shows counts, not a verdict |
| **30-second** | What's broken and what do I do? | `errors` + `circuit_breakers` + `heal_events` | Modal drill-down only, requires clicking |
| **1-minute** | Which agent costs the most? | `token_logs` (cost, total_tokens) | Token Analytics tab — requires navigation |
| **5-minute** | Is context bloat a problem? | `chisel_drift` (delta_pct, breached) | Drift tab — buried |
| **Investigation** | Why did this agent crash? | `errors` + `pulse_log` + `l2_trending` | Drill-down modal with confidence score |
| **Strategic** | Where is my money going? | `token_logs` + `token_pricing` | Token Analytics tab with cost breakdown |
| **Diagnostic** | Which skills are never used? | `skill_usage` + `token_logs` (tool_calls) | Skills Audit modal |
| **Topology** | How do my agents communicate? | `pathway_nodes` + `pathway_edges` | Separate Pathway Map page |
| **Trend** | Are things getting better or worse? | `chisel_drift` + `compress_log` + `l2_trending` | Partially in Drift tab |

---

## 2. Backend Architecture — How Data Flows

```
[AI Agent]                          [ObserveCo]
    │                                    │
    ├─ SOUL.md ──────────────────►  watch daemon (every 30s)
    │   (identity/skills/             │  parses SOUL.md → chisel_trims
    │    memory/tools/guidance)       │  computes drift → chisel_drift
    │                                 │  runs pulse check → pulse_log
    ├─ LLM API call ─────────────►  otel listener (port 4318)
    │   (tokens, model, cost)        │  receives spans → token_logs
    │                                 │
    ├─ Hermes post-turn hook ────►  POST /api/tokens/log
    │   (fire-and-forget)            │  → token_logs (with component breakdown)
    │                                 │
    ├─ Agent crash ──────────────►  watch daemon detects dead
    │                                 │  runs heal diagnosis → heal_events
    │                                 │  trips circuit → circuit_breakers
    │                                 │
    └─ Memory file change ───────►  clawforge garden scan
                                      → clawforge_garden

[Dashboard User]
    │
    ├─ opens http://localhost:8123
    │  FastAPI renders Jinja2 templates with htmx
    │
    ├─ htmx GET /api/agents → returns HTML partials
    ├─ htmx GET /api/agent-detail/hound?tab=health → returns modal HTML
    ├─ htmx POST /api/heal/trigger → triggers heal, returns status
    └─ 30s auto-refresh via setInterval → /api/agents
```

**Key architectural constraints for design:**
1. Every interaction is a GET or POST to a FastAPI endpoint. No client-side state management.
2. The server returns HTML partials (not JSON). htmx swaps them into the DOM.
3. The dashboard is ONE page. No client-side routing. No SPA.
4. Chart.js is available for time-series charts (loaded via `<script src="/static/chart.umd.min.js">`)
5. Cytoscape.js is used for the Pathway Map visualization
6. SQLite is the single data source — queries must be fast (<200ms for fleet view with 50 agents)

---

## 3. Master Plan — What's Live, What's Coming, What's Far

### 3.1 ✅ Live Now (v0.3.0)

| Feature | What It Does | Dashboard Status |
|---|---|---|
| **Fleet View** | Agent cards with status dot, token bar, drift, error badge | 5 clickable metric rows per card |
| **Pulse Check** | Alive/dead/error every 30s | 48-dot pulse timeline in drill-down modal |
| **Circuit Breakers** | N-failure trip → 4h cooldown | Guard status row on cards |
| **Token Breakdown** | Component decomposition (identity/skills/memory/tools/guidance) | Token bar on each card + Brain Analysis tab |
| **Drift Tracking** | 7-day per-component change | Drift tab with per-agent breakdown |
| **Error History** | Last 24h errors with classification | Error badge on cards + drill-down modal |
| **Brain Analysis** | Token composition, compression preview/apply, savings comparison | Dedicated tab with 4 sections |
| **Token Analytics** | Chart.js time-series, cost estimation, cache efficiency | Dedicated tab with per-model breakdown |
| **Memory Garden** | Duplicates, contradictions, stale entries, debt score | Fleet summary + per-agent detail |
| **Alerts Panel** | In-dashboard severity-coded feed with discovery gap badges | Right rail (320px on desktop) |
| **Heal Button** | Manual trigger — diagnoses + restarts dead agents | Heal tab (backend built, dashboard UI minimal) |
| **Pathway Map** | Communication topology graph (111 nodes, 80 edges) | Separate page (Cytoscape.js) |
| **Glossary** | 51 context-sensitive tooltip topics | "?" icon on every card row |
| **Discover Widget** | Scan for unmonitored agents, one-click add | Badge in fleet header |
| **Fleet Comparison** | Side-by-side agent matrix | Compare tab |
| **Data Quality Bar** | Source accuracy indicator (Estimated/Partial/Accurate) | Token Analytics tab (hidden unless you click it) |

### 3.2 🔴 Planned — Short Term (v0.4.0, next 2-4 weeks)

| Feature | What It Will Do | Signal Richness for UX |
|---|---|---|
| **Auto-Heal Dashboard UI** | Toggle auto-heal per agent, status card, heal history table, threshold editor | 🔴 HIGH — surfaces the hero feature |
| **Anomalies Inbox** | Fleet-wide issue surfacing: dead agents, drift spikes, error bursts, tripped circuits, red plugins, cost spikes — severity feed with plain-English explanation | 🔴 HIGH — replaces alert hunting with prioritized feed |
| **Context Health Score** | Single 0-100 number per agent: "how healthy is this agent's brain?" — combines memory bloat, drift delta, error rate, context utilization | 🟡 MEDIUM — single metric, high insight density |
| **Budget Alerts** | Daily/cost/anomaly threshold alerts → push via Telegram/webhook/email | 🟡 MEDIUM |
| **Provider Billing API** | Query OpenAI/Anthropic/DeepSeek billing endpoints → compute "attribution gap" (92% attributed, 8% unattributed) | 🟡 MEDIUM |
| **Tool Efficiency Ranking** | Per-tool cost, error rate, latency — red/yellow/green. Recommendations ("disable this tool") | 🟡 MEDIUM |
| **Context Source Utilization** | Which skills/memory sections are actually used vs loaded by default → "these 2 skills add 1,400 tokens but are rarely used" | 🟢 LOW |

### 3.3 🔴 Planned — Medium Term (v1.0)

| Feature | Signal Richness |
|---|---|
| **Trace Tree Waterfall** — full agent handoff chain visualization (delegator → executor, tools used, latency per hop, cost) | 🔴 HIGH |
| **Alert Management Surface** — unified view/acknowledge/resolve/snooze all alert types with delivery status and history | 🔴 HIGH |
| **Session Baseline Diffing** — save fleet snapshot, compare subsequent runs: "cost up 23% vs baseline, agent X health dropped 15 points" | 🟡 MEDIUM |
| **CI Quality Gates** — `observeco gate --fail-under-health 80` for GitHub Actions/GitLab CI | 🟢 LOW |
| **Static Report Export** — self-contained HTML/JSON/Markdown report, shareable with non-technical stakeholders | 🟢 LOW |
| **Agent Relapse Prevention** — timeline correlating config changes with degradation signals — "what changed and broke things?" | 🟡 MEDIUM |

### 3.4 🔴 Planned — Long Term (v1.1+)

| Feature |
|---|
| **Multi-Source Log Parser** — parse Claude Code, Codex CLI, Gemini CLI, Cursor, Aider session logs |
| **Multi-Machine Relay** — agents on different machines report to one dashboard |
| **MCP Protocol** — `observeco mcp serve` on port 9120 → any MCP client can query agent health |
| **Cross-Agent Signal Flow** — track signal delivery between agents, detect sent-but-never-acknowledged |
| **OpenClaw Runtime Plugin** — intent-aware context loading, 40-60% fewer tokens per turn |

---

## 4. Current UX Problems (What the Design Must Fix)

### 4.1 The 5-Second Test Failed
The fleet header shows "12 agents · 10 🟢 1 🟡 1 🔴" — which is DATA, not a VERDICT. The user has to interpret the numbers. Replace with: **"🟢 Fleet Healthy — 10 agents operating normally. dreamer degraded. raven dead."**

### 4.2 9 Flat Tabs = Navigation Overwhelm
Fleet, Tokens, Drift, Errors, Alerts, Settings, Compare, Brain, Token Analytics — all equal weight. By v1.0 this will be 14+ tabs. Domain grouping needed: Monitor (Fleet/Alerts/Errors), Analyze (Tokens/Brain/Drift/Compare), Intelligence (Anomalies/Health/Traces), Settings.

### 4.3 Data Quality Is Hidden
The Data Quality Bar only loads when Token Analytics tab is clicked. The user can't see "hey, your OTEL data is stale" from the Fleet view. Move data quality confidence indicators to the fleet header and every agent card.

### 4.4 Discovery Gap Is Great But Hidden
The alerts panel shows "happened at 03:15 · you discovered at 07:00 — 3h 45m gap" — but only in the alerts tab. This is the #1 conversion driver for Pro. Make it visible fleet-wide.

### 4.5 Heal Is Built But Invisible
The heal backend works (diagnose → propose → execute). But the dashboard shows a minimal Heal tab with no toggle, no status card, no history. This is the hero feature and it's buried.

### 4.6 Every Interaction Opens a Modal
Click health row → modal. Click errors row → modal. Click tokens row → modal. The modals are information-rich but modal fatigue is real. Consider inline expansion on cards for frequent interactions.

### 4.7 No "What Matters Most" Prioritization
All agent cards are equal. All alerts are equal. All errors are equal. But a dead agent matters more than a token drift of +2%. The UI should prioritize by severity.

---

## 5. Design System Token Reference (EXACT VALUES — DO NOT CHANGE)

```css
:root {
  /* ── Surface Palette ── */
  --bg: #0f172a;
  --surface: #1e293b;
  --surface-hover: #253349;
  --surface-active: #334155;
  --border: #334155;
  --border-soft: #273548;

  /* ── Status Palette (health semantics — NEVER used on token bars) ── */
  --status-healthy: #22c55e;    /* 🟢 Pulse OK, circuit closed */
  --status-warning: #eab308;    /* 🟡 Degraded, 1-2 missed heartbeats */
  --status-critical: #ef4444;   /* 🔴 Dead agent, tripped circuit */
  --status-info: #3b82f6;       /* 🔵 Learning phase, baseline */

  /* ── Token Composition Palette (component breakdown — NEVER used for status) ── */
  --token-identity: #6366f1;    /* Indigo */
  --token-skills: #8b5cf6;      /* Violet */
  --token-memory: #ec4899;      /* Pink */
  --token-tools: #14b8a6;       /* Teal */
  --token-guidance: #f97316;    /* Orange */

  /* ── Text Palette ── */
  --fg: #f8fafc;
  --fg-2: #94a3b8;
  --fg-3: #64748b;
  --accent: #22c55e;
  --accent-on: #0c1628;
  --warn: #eab308;
  --danger: #ef4444;
  --meta: #3b82f6;

  /* ── Typography ── */
  --font-sans: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  --font-mono: 'JetBrains Mono', ui-monospace, 'SF Mono', Menlo, Consolas, monospace;
  --text-xs: 11px; --text-sm: 12px; --text-base: 14px; --text-lg: 18px; --text-xl: 24px;

  /* ── Spacing (4px grid) ── */
  --space-1: 4px; --space-2: 8px; --space-3: 12px;
  --space-4: 16px; --space-6: 24px; --space-8: 32px;

  /* ── Shape ── */
  --radius-sm: 4px; --radius-md: 8px; --radius-lg: 12px; --radius-pill: 9999px;

  /* ── Motion ── */
  --motion-fast: 100ms; --motion-base: 150ms;
  --ease-standard: cubic-bezier(0.2, 0, 0, 1);

  /* ── Elevation ── */
  --elev-ring: 0 0 0 1px var(--border);
  --elev-raised: 0 24px 72px rgba(0, 0, 0, 0.42);
}
```

**CRITICAL RULES:**
- Status colors (green/yellow/red) must NEVER appear on token composition bars
- Token colors (indigo/violet/pink/teal/orange) must NEVER appear on status indicators
- DARK THEME ONLY. No light mode. No theme toggle. Mission-control aesthetic.
- NO gradient backgrounds, glassmorphism, or rainbow palettes
- JetBrains Mono for ALL numeric data. Inter for labels and navigation.
- Minimum 44px hit targets on interactive elements

---

## 6. Component Specifications

### 6.1 Fleet Verdict Bar (Sticky Top — THE most important element)
**Answers the 5-second question: "Is my fleet OK?"**

Show: A single sentence with an icon that changes color.
- 🟢 All healthy → "All 12 agents operating normally" (green background tint)
- 🟡 Degradation → "10 agents healthy · 1 degraded · 1 dead" (amber background tint, clickable agent names)
- 🔴 Critical → "2 agents DOWN — raven (dead 2h), dreamer (circuit tripped)" (red background tint, clickable)

Include: Agent count, tripped circuits badge (if >0), cumulative alert gap ("4 alerts · 8h total undiscovered downtime"), and a data quality indicator.

### 6.2 Agent Card
For each agent, show:
1. **Status dot** — green/yellow/red with subtle glow
2. **Agent name** + framework badge (Hermes/OpenClaw/Ollama)
3. **Last seen** — "12s ago" / "2h ago" / "3d ago" (red if >1h)
4. **5 clickable metric rows** with progressive disclosure:
   - Health — mini pulse timeline (last 6 dots instead of 48) + "View details →"
   - Guard — "✅ OK" or "🔴 STOPPED" + "See why →"
   - Errors — count badge + "Last: timeout 14m ago →"
   - Brain size — "42K tokens · +3% this week" + token bar → 
   - Composition — 5-segment colored bar with "See breakdown →"
5. **Delete button** (×, shows on hover)
6. **Data quality badge** — if source is `watch` only, show "Estimated ⚠️", if `otel` data present, show "Accurate ✅"

**Progressive disclosure idea:** Collapsed card shows only status dot + name + last seen + error badge + token bar. Click to expand all 5 metric rows. This reduces cognitive load as fleet grows.

### 6.3 Alerts Panel (Right Rail — 320px on desktop)
Grouped by severity with real-time gap calculation:
- 🔴 CRITICAL: dead agents, tripped circuits
- 🟡 WARNING: drift >10%, degraded, near-threshold
- 🔵 INFO: anomalies, baseline learning

Each alert shows: time since event + discovery delay. New alerts have a green "NEW" indicator. Cumulative gap banner at top: "8h 47m undiscovered downtime."

### 6.4 Error Timeline (Full-Width Bottom)
Reverse-chronological feed across ALL agents. Gantt-style duration bars show how long each incident lasted. Filterable by agent, severity, type, date range.

### 6.5 Agent Detail Modal
5 tabs inside: Health (pulse timeline + confidence), Guard (failure history + settings), Errors (annotated timeline + verdict), Tokens (component breakdown + before/after compression), Memory (garden score + duplicates/contradictions/stale).

### 6.6 Navigation: Domain Groups
Instead of 9+ flat tabs:
- **Monitor** — Fleet (default), Alerts, Error Timeline
- **Analyze** — Tokens, Brain, Drift, Compare
- **Intelligence** — Anomalies (future), Health Score (future), Trace Waterfall
- **Settings** — Heal, Alerts Config, Data Retention, Billing

### 6.7 Empty State Placeholders for Future Features
Show 3 clearly-designed placeholder cards for Anomalies Inbox, Context Health Score, and Trace Waterfall — each with what the feature will do, an estimated ship date, and a visual preview of the card format.

---

## 7. Four Required States Per Component

| State | Trigger | Visual |
|---|---|---|
| **Loading** | Data being fetched | Skeleton bars / pulse animation. Never a blank page. |
| **Empty** | No data exists | Calm gray-neutral state with icon, explanation, and action. "No agents discovered. Run `observeco agents discover`." |
| **Data** | Data present | Full rendering as specified. |
| **Error** | Data unavailable (daemon down, DB corrupt) | Amber banner: "⚠️ Monitoring stopped 2h ago. Run `observeco start`." Show last-known-good data with stale indicator. |

---

## 8. Responsive Breakpoints

| Width | Behavior |
|---|---|
| **>1280px** | Full three-zone layout: sticky header + card grid + 320px alerts rail + full-width timeline |
| **768–1280px** | Two-zone: cards full-width + alerts collapse to toggle button |
| **<768px** | Single column: list view (name + status dot + token count), timeline shows last 5 events |

---

## 9. The Deliverables

Produce **three self-contained HTML files**, each with embedded CSS (using the token system above) and vanilla JS. Each must demonstrate all four states (loading, empty, data, error).

| # | File | Approach |
|---|---|---|
| 1 | `ObserveCo Dashboard v1 — Conservative.html` | Polish existing design. Tab bar navigation. Card grid. Focus on: fleet verdict sentence, subtle transitions, spacing refinement, data quality badges on cards, and a richer alert panel with discovery gap. |
| 2 | `ObserveCo Dashboard v2 — Strong-Fit.html` | Domain-grouped navigation. Three-zone layout: verdict bar → card grid (70%) + alerts panel (30%) → timeline. Progressive card disclosure (collapsed → expand). Future feature placeholders. This is the recommended direction. |
| 3 | `ObserveCo Dashboard v3 — Divergent.html` | Inbox-style priority feed. Most critical agent/alert first. Command-palette search (Cmd+K) for agents. Maximum data density. Minimal chrome. Think "you're debugging at 3am, you need answers NOW." |

**Each file must:**
- Use the EXACT hex values from §5
- Show realistic mock data from the data model in §1
- Handle all 4 states
- Be a single file openable in a browser with no build step
- Use Inter + JetBrains Mono from Google Fonts CDN

---

## 10. Anti-Slop Guardrails

**NEVER:**
- Gradient backgrounds — ObserveCo is flat, dark, precise
- Glassmorphism or blur effects
- Light mode or theme toggle
- Decorative SVG illustrations
- Placeholder testimonials
- "Insights" / "Growth" / "Scale" sections
- Rainbow palettes (constrained to §5 above)
- Fake metrics not in the data model

**ALWAYS:**
- Exact hex values from §5
- Monospace for all numeric data (JetBrains Mono)
- Minimum 44px hit targets
- Focus states on all interactive elements
- Respect `prefers-reduced-motion` for animations
- Data legible at a glance (someone debugging at 3am)

---

## 11. How To Think About This

The design problem is NOT "make a pretty dashboard." It's:

**"We have 215,238 token records, 163,560 drift data points, 13,438 health checks, and 672 errors across 12 agents. The user opens this at 3am because something broke. They need to know in 5 seconds if the fleet is OK, in 30 seconds what to do about it, and in 5 minutes whether things are getting better or worse. Design the surface that makes these answers inevitable."**

Everything you design should be testable against this scenario.
