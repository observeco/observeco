# Health Improvement Ideas — Verified Analysis

**Author:** Hermes Agent (independent verification)
**Date:** 2026-06-26
**Method:** Read actual codebase (`db.py`, `tracking/tokens.py`, `heal/__init__.py`, `dashboard/server.py`, `alerts/push.py`, `health.py`, master plan, competitive analysis)

---

## Category 1: Cost Blindness (Strong → Strongest)

| # | Idea | Verdict | Effort | Impact | Notes |
|---|------|---------|--------|--------|-------|
| 1 | "Show me the money" mode | ✅ **Keep** | **Easy (~2h)** | **High** | DB already has `token_pricing` table with per-model rates, `token_logs.cost` column, and `compute_cost_tiered()` in `tracking/tokens.py`. The dashboard already has a budget planner at `/api/budget-planner`. This is a **Jinja2 template overlay** — add `$` equivalents to existing token displays. No new backend. |
| 2 | Provider cost comparison | 🔄 **Improve** | **Medium (~4h)** | **Medium** | `token_pricing` table has 8+ providers with per-model rates. The budget planner already has a provider dropdown. But "what if you moved to Ollama" requires comparing *actual* token usage against *hypothetical* pricing — a pure frontend calculation. **Simplify:** Add a "What if?" dropdown to the existing budget planner widget that re-computes costs at different provider rates. No new endpoint needed. |
| 3 | Cost anomaly detection | ✅ **Keep** | **Easy (~3h)** | **High** | `token_logs` has `anomaly_score` column and `token_budgets` has `anomaly_threshold_sigma`. The `compute_anomaly()` function in `tracking/tokens.py` is a **stub that returns None** — needs implementation. The data is there: `SELECT cost, recorded_at FROM token_logs WHERE agent_name=? ORDER BY recorded_at`. Simple z-score against 7-day rolling mean. **ponytail:** z-score assumes normal distribution; upgrade to MAD (median absolute deviation) for robustness. |
| 4 | Budget alerts with one-click enable | ✅ **Keep** | **Easy (~2h)** | **High** | `token_budgets` table exists with `max_daily_tokens`, `max_turn_cost`, `anomaly_threshold_sigma`. Push alert infra (`alerts/push.py`) is live with Telegram/Discord/webhook/email. The missing piece: a **budget check cron** that compares daily spend against budget and fires `push_alert()`. Already spec'd as G2.1 in master plan. **One-liner check:** `SELECT SUM(cost) FROM token_logs WHERE recorded_at > ?` vs budget. |

### Verdict on Cost Blindness
**3 keep, 1 improve.** Ideas 1, 3, 4 are solid and buildable with existing data. Idea 2 is fine but can be simplified to a frontend-only widget. **Priority: 3 (anomaly) → 4 (budget alerts) → 1 (money overlay).**

---

## Category 2: Debugging Blindness (Moderate → Strongest)

| # | Idea | Verdict | Effort | Impact | Notes |
|---|------|---------|--------|--------|-------|
| 5 | "Why did this happen?" button | 🔄 **Improve** | **Medium (~1d)** | **High** | The **heal system already does this** (`heal/__init__.py:_diagnose_agent`). It reads pulse_log + errors + circuit_breakers + restart_log + chisel_drift + memory_garden, runs 7 static patterns, then escalates to LLM. The dashboard already has `/api/trigger-heal` which shows diagnosis HTML. **This idea is 80% built.** What's missing: a per-error "Why?" button that calls `_diagnose_agent` for a single error event (not the whole fleet). **Simplify:** Add a "Why?" link to each error row in the error timeline modal that calls `/api/trigger-heal?agent=X` and scrolls to the diagnosis. |
| 6 | Failure pattern recognition | ❌ **Kill** | **Hard (~3d)** | **Medium** | Cross-agent, cross-time pattern detection is a **data science problem**, not a CRUD feature. The `errors` table has `error_type` and `error_message` but no structured failure taxonomy. You'd need to cluster error messages (NLP or regex), correlate timestamps across agents, and maintain a pattern database. The **heal system's LLM escalation** already does this for single-agent diagnosis. For cross-agent patterns, the ROI is low — most users have 2-6 agents, not 50. **Replace with:** A simpler "Similar failures" section on the error detail modal that shows other agents with the same `error_type` in the last 24h. That's a single SQL query. |
| 7 | Error correlation | 🔄 **Improve** | **Easy (~3h)** | **Medium** | Co-occurrence analysis on error timestamps is a SQL window function: `SELECT a.agent_name, b.agent_name, COUNT(*) FROM errors a JOIN errors b ON ABS(a.timestamp - b.timestamp) < 300 AND a.agent_name < b.agent_name GROUP BY ...`. But this is **noisy** — two agents failing at the same time doesn't mean they share a dependency. **Simplify:** Use the existing `pathway_edges` table (Communication Pathway Map) which already models agent→service dependencies. Show "When X fails, these Y agents are affected" by querying the graph. This is already spec'd as #21 in the master plan. |
| 8 | Session timeline view | ❌ **Kill** | **Hard (~3d)** | **High** | The `turn_log` table has per-turn data (tokens, skills_used, guidance_hit, timestamp) and `token_logs` has model, latency_ms, tool_calls. But there's **no session grouping** — turns are individual rows with no `session_id` or `conversation_id` to group them into a timeline. The post-turn webhook (#43) sends `topic_id` but that's optional. **This is a foundational data model change, not a UI overlay.** However, the master plan already has #37 (Post-Turn Webhook) and #55 (Trace Tree Dashboard) which cover this. **Replace with:** Build the session grouping first (add `session_id` to turn_log), then the timeline is a Gantt chart over existing data. But this is a ~3d project. De-prioritize until session data exists. |

### Verdict on Debugging Blindness
**1 keep, 2 improve, 2 kill.** Idea 5 is the strongest — it's 80% built already. Ideas 6 and 8 are too ambitious for the current data model. **Priority: 5 (Why button) → 7 (error correlation via pathway graph) → defer 6 and 8.**

---

## Category 3: Context/Memory Bloat (Strongest → maintain + evolve)

| # | Idea | Verdict | Effort | Impact | Notes |
|---|------|---------|--------|--------|-------|
| 9 | "What changed?" timeline | ❌ **Kill** | **Hard (~3d)** | **Medium** | This is **already spec'd as #28 (Agent Relapse Prevention)** in the master plan. The idea is correct but the implementation is non-trivial: you need file mtime tracking for SOUL.md, config changes, plugin installs — and correlate them with drift/error spikes. The `chisel_drift` table has per-component drift deltas, but there's **no file change event log** to correlate against. You'd need a new table or a filesystem watcher. **Already planned as #28.** Don't build twice. |
| 10 | Proactive bloat warnings | ✅ **Keep** | **Easy (~2h)** | **High** | `token_logs` has per-turn component token counts. `chisel_drift` has weekly drift deltas. A linear projection is: `SELECT AVG(total_tokens) FROM token_logs WHERE agent_name=? AND recorded_at > ?` grouped by day, then `slope = (last - first) / days`. Compare against context window (default 128K). **One endpoint, one dashboard widget.** No new tables. **ponytail:** linear projection assumes constant growth; upgrade to exponential smoothing for bursty agents. |
| 11 | Skill usage heatmap | 🔄 **Improve** | **Medium (~4h)** | **Medium** | The `plugin_tracking` table has `sources_loaded` and `sources_skipped` per agent per hook point. The `skill_usage` table has `triggered` and `turn_count` per skill. But these are **Hermes/ClawForge-specific** — they only populate if the agent uses the ClawForge plugin. For generic agents, there's no skill-level data. **Already spec'd as #40 (Context Source Utilisation Tracker)** in the master plan. **Simplify:** Build the heatmap from `skill_usage` table where data exists, show "no data" for agents without ClawForge. Don't build a generic skill tracker. |

### Verdict on Context/Memory Bloat
**1 keep, 1 improve, 1 kill.** Idea 10 is the strongest — simple, buildable, high impact. Idea 9 is already planned. Idea 11 is already planned as #40. **Priority: 10 (bloat warnings) → 11 (heatmap as #40) → skip 9 (already planned).**

---

## Category 4: Missing Runtime Health (Strong → Strongest)

| # | Idea | Verdict | Effort | Impact | Notes |
|---|------|---------|--------|--------|-------|
| 12 | Health trend prediction | ❌ **Kill** | **Hard (~3d)** | **Medium** | "73% probability of failing in the next 24 hours" is a **prediction model**, not a query. You'd need logistic regression or a Markov chain on pulse_log + error rate + latency trend. The `l2_trending` table has trend types (memory_bloat, stuck, drift, upstream_fail) with metric values — this is the closest thing to a prediction signal. But a probability score is misleading without calibration. **Replace with:** A simpler "degradation trend" indicator: if pulse latency is up 12%/day AND error rate is up 3x, show "⚠️ Degrading — check within 24h". No probability, no ML. This is already partially built in the heal system's L2 proactive detection. |
| 13 | Agent health report card | ✅ **Keep** | **Easy (~3h)** | **Medium** | All data exists in existing tables: `pulse_log` (uptime), `heal_events` (auto-heals), `circuit_events` (circuit trips), `compress_log` (compressions), `token_logs` (cost). A weekly digest is a **scheduled push alert** that aggregates last 7 days. The push alert infra is live. **One SQL query per metric, one Jinja2 template.** Already partially covered by the master plan's #59 (Composite Health Score) but the weekly digest format is new. |
| 14 | Dependency health map | ❌ **Kill** | **Hard (~2d)** | **Low** | The `pathway_edges` table already models agent→service dependencies (Communication Pathway Map, #21, **already live**). The dashboard already has an interactive graph with 111+ nodes. "When Service X goes down, show affected agents" is **already built** — the pathway map shows edge status (green/yellow/red/teal). **This idea is already shipped.** Don't rebuild it. |
| 15 | One-click health fix from alert | ✅ **Keep** | **Medium (~4h)** | **High** | The heal system (`heal/__init__.py`) has `_execute_action()` with restart, cooldown, pip_install, trim, garden_cleanup actions. The push alert infra (`alerts/push.py`) is live. The missing piece: **action buttons in push notifications**. Telegram supports inline keyboards, Discord supports buttons, webhook payloads can include action URLs. The `/api/trigger-heal` endpoint already accepts agent names. **Simplify:** Add action URLs to push alert payloads. The dashboard heal endpoint already handles the actions. **ponytail:** Telegram inline keyboards require callback data, not URLs — need a separate handler. Upgrade path: add `/api/heal-action/{agent}/{action}` endpoint. |

### Verdict on Missing Runtime Health
**2 keep, 2 kill.** Ideas 13 and 15 are solid. Idea 12 is over-engineered (replace with simpler degradation indicator). Idea 14 is already shipped. **Priority: 15 (one-click fix) → 13 (report card) → skip 12 and 14.**

---

## Ranked Priority List (Top 7)

| Rank | Idea | Category | Effort | Impact | Why |
|------|------|----------|--------|--------|-----|
| 1 | **#5: "Why did this happen?" button** | Debugging | ~1d | High | 80% built already. The heal system already does this diagnosis. Just wire it to individual error rows. |
| 2 | **#15: One-click health fix from alert** | Runtime Health | ~4h | High | Heal actions exist. Push alerts exist. Just wire them together with action buttons. |
| 3 | **#3: Cost anomaly detection** | Cost Blindness | ~3h | High | `anomaly_score` column exists but `compute_anomaly()` is a stub. Fill in the z-score logic. |
| 4 | **#4: Budget alerts with one-click enable** | Cost Blindness | ~2h | High | `token_budgets` table + push alert infra exist. Add a budget check cron. Already spec'd as G2.1. |
| 5 | **#10: Proactive bloat warnings** | Context/Memory | ~2h | High | Simple linear projection on existing `token_logs` data. One endpoint, one widget. |
| 6 | **#1: "Show me the money" mode** | Cost Blindness | ~2h | High | Pure template overlay. `token_pricing` table + `cost` column already exist. |
| 7 | **#13: Agent health report card** | Runtime Health | ~3h | Medium | Weekly digest via existing push alert infra. All data exists. |

---

## New Ideas (Not in Original 15)

These emerged from reading the codebase and finding gaps the original list missed:

### N1: Composite Health Score (replaces #12)
**Effort:** ~3h | **Impact:** High
The master plan has #59 (Composite Health Score, 0-100) spec'd but not built. Combine: pulse uptime (40%), error rate (20%), drift stability (15%), token efficiency (15%), circuit breaker state (10%). All data exists. Show as a number + trend arrow on each agent card. This is **more useful than a probability prediction** and much simpler.

### N2: Anomaly Inbox (replaces #6)
**Effort:** ~2d | **Impact:** High
Already spec'd as #33 in the master plan. A single dashboard tab that surfaces: dead agents, drift spikes, error bursts, context health drops, tripped circuits, token cost spikes. Reads from 10+ existing tables. This is the "activation moment" — "your agent has 3 problems right now." The original idea #6 (failure pattern recognition) is a subset of this.

### N3: Turn-Rate Alerting (G1.4)
**Effort:** ~1d | **Impact:** Medium
Already spec'd as G1.4 in the master plan. Track turns/minute per agent from `turn_log`. Alert when rate exceeds configurable threshold (default 30 turns/min). Catches runaway agents before they burn through budget. Simple: `SELECT COUNT(*) FROM turn_log WHERE agent_name=? AND timestamp > ?` / minutes.

### N4: Tool Efficiency Ranking (replaces #11)
**Effort:** ~1.5d | **Impact:** Medium
Already spec'd as #39. Ranks every tool/skill by cost per call, error rate, latency impact, success rate. Red/yellow/green. Surfaces "disable this tool" recommendations. More actionable than a heatmap.

---

## Summary

**Killed:** 5 ideas (6, 8, 9, 12, 14)
- #6 (failure pattern recognition) — data science problem, low ROI for small fleets
- #8 (session timeline) — foundational data model change, needs session grouping first
- #9 (what changed timeline) — already spec'd as #28 in master plan
- #12 (health trend prediction) — over-engineered, replace with simpler degradation indicator
- #14 (dependency health map) — already shipped as #21

**Improved:** 4 ideas (2, 5, 7, 11)
- #2 → simplify to frontend-only "What if?" widget
- #5 → wire existing heal diagnosis to individual error rows
- #7 → use existing pathway_edges graph instead of timestamp co-occurrence
- #11 → already spec'd as #40, build from existing skill_usage table

**Kept:** 6 ideas (1, 3, 4, 10, 13, 15)
All buildable with existing data/backend. No new tables needed.

**New proposals:** 4 ideas (N1-N4) that fill gaps the original list missed.

**Bottom line:** The strongest 7 ideas (ranked above) can be built in ~3-4 days total. They move Cost Blindness and Debugging Blindness to "Strongest" and add meaningful polish to Runtime Health and Context/Memory.
