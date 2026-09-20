# ObserveCo — Data Presentation Architecture

> **Status:** Foundational spec — read before any further visual iteration.
> **Purpose:** Define what data binds to which UI component, and how raw rows become actionable insight.
> **Category thesis:** ObserveCo is **agent-specific observability** — a new product category, not "Datadog for agents." Every element here is judged against one test: *could Grafana show this same thing?* If yes, it's table-stakes. If no, it's the moat.

---

## How to read this document

The 47-table SQLite database is the substrate. This spec defines the **pipeline** (tables → aggregation → UI) and the **insight layer** (raw value → "so what?") for the four questions that only agent-specific observability can answer:

- **Q1 — What did the agent actually do?** (behavior)
- **Q2 — Why did it do that?** (causation)
- **Q3 — Is it getting worse?** (trajectory)
- **Q4 — Where is the money going?** (attribution)

Traditional APM answers "is it up, how fast, how many errors." Those are necessary but they are not the product. The product is the four questions above.

---

# Section 1 — The 4 Questions → Data Pipeline → UI Binding

## Q1 · What did the agent actually do?

**Traditional monitoring says:** "Service returned 200 OK."
**ObserveCo says:** "Agent used 4 tools this turn — `search_files`(3), `read_file`(2), `web_search`(1) — 2,400 tokens, $0.0037. Skills component grew 8%. Memory was accessed but returned no relevant results."

| Aspect | Specification |
|---|---|
| **Tables** | `token_logs` (tokens in/out, model, provider, cost, latency, **component breakdown**, cache hits, anomaly score), `trace_spans` (agent-to-agent handoff chains), `pulse_log` (alive/dead/error + latency per 30s beat) |
| **Aggregation** | Per-turn tool-call list with counts; component sizes (identity/skills/memory/tools/guidance) at start of turn; latency per tool call; cache read vs create split; rolled up per `agent_name` over the selected window |
| **UI components** | Agent card **Compose** row (5-segment token bar) · Health row **pulse mini-panel** (last 6 beats, latency per beat) · expanded card rows · (future) per-turn tool-call list in agent detail |
| **ObserveCo-only insight** | No other tool decomposes a `SOUL.md` snapshot into 5 named components and shows **which one grew this turn**. The `watch` pipeline parses SOUL.md; the `otel` pipeline supplies per-call truth. Two pipelines, one card. |
| **"So what?"** | "Skills grew 12% this week — 3 new rule blocks added. 2 of 8 skills never fire. Compress unused skills to recover ~1,800 tokens/turn." |

## Q2 · Why did it do that?

**Traditional monitoring says:** "No change detected."
**ObserveCo says:** "Skills has grown 18% this week — 3 rules added Tuesday. Memory debt rose 14 → 48. Correlates with the 23% error-rate jump that started Wednesday."

| Aspect | Specification |
|---|---|
| **Tables** | `chisel_drift` (7-day per-component change + breach thresholds), `l2_trending` (proactive degradation signals: memory bloat, stuck agents, upstream failures), `clawforge_garden` (duplicates, contradictions, stale entries, debt score), `circuit_breakers` / heal/circuit events (failure patterns) |
| **Aggregation** | Per-component 7-day delta; drift breaches flagged against thresholds (§2-F); memory-debt trend direction; correlation of drift onset with error-rate change; circuit trip cause chain |
| **UI components** | Agent card **Guard** row (circuit state + reason) · **Drift** tab (per-component deltas) · **Memory Garden** debt score · alerts panel cause line |
| **ObserveCo-only insight** | Correlating component drift with memory debt: "memory grew 28% because 3 new skills each loaded an extra context file." Grafana has no concept of "the agent's brain has parts." |
| **"So what?"** | "This agent is slowing because memory is accumulating stale entries. Garden found 2 contradictions and 3 duplicates — archiving them drops debt 48 → ~22." |

## Q3 · Is it getting worse?

**Traditional monitoring says:** "No errors reported."
**ObserveCo says:** "Context utilization is 72% (was 58% last week). 2 of 8 skills never trigger; 1 guidance rule fires every turn, the rest zero. At this rate the agent hits 90% context pressure by day 9."

| Aspect | Specification |
|---|---|
| **Tables** | `chisel_trims` (SOUL.md snapshots trended over time), `chisel_drift` (breached flag), `heal_events` (recovery attempts + outcome), `pulse_log` (health trend), `compress_log` (intervention history + savings) |
| **Aggregation** | 30-day trend line per component; week-over-week comparison; context-window utilization projected forward; automatic regression detection (slope > threshold); heal-attempt frequency trend |
| **UI components** | Agent card **Brain** row trend arrow · **Drift** tab 7-day sparklines · **Verdict bar** trend indicator · (future) Context Health Score 0–100 |
| **ObserveCo-only insight** | Context-window utilization over time **with per-component attribution** — "memory grows 5%/week, hits 80% capacity in 14 days." This is a forecast about the agent's brain, impossible without SOUL.md history. |
| **"So what?"** | "You're ~14 days from a forced context truncation unless you compress or archive. Skills is the fastest-growing segment — target it first." |

## Q4 · Where is the money going?

**Traditional monitoring says:** "$X total spend."
**ObserveCo says:** "91% of spend is in 3 agents. 22% goes to cache creation that's never read. Agent X costs $0.14/turn, Y costs $2.10/turn for the same task — 15× on identical `claude-sonnet-4`. 8% of spend is unattributed (no telemetry plugin)."

| Aspect | Specification |
|---|---|
| **Tables** | `token_logs` (cost + model + provider + **component breakdown** + cache split), `token_pricing` / `llm_provider_registry` (rate tables, 13 providers), `compress_log` (before/after + savings %), intent-aware loader savings |
| **Aggregation** | Per-agent daily cost; per-model cost; cache efficiency rate (read ÷ (read+create)); attribution gap % (rows lacking `otel` source); cumulative compression savings; **cost per component** |
| **UI components** | Agent card **Brain** row cost ($/24h) · **Token Analytics** tab (time-series + cost) · **Brain Analysis** tab (compression preview/apply + savings comparison) |
| **ObserveCo-only insight** | **Cost per component** — "42% of spend is skills tokens. Lite compression saves $0.52/day on skills alone." No other tool can attribute dollars to a region of the prompt. |
| **"So what?"** | "X is $0.14/turn, Y is $2.10/turn for the same task — 15× gap. Check whether Y needs Full compression or is reloading memory every turn." |

---

# Section 2 — Threshold & Classification Rules

These are the rules the dashboard uses to turn numbers into decisions. They are the contract between backend computation and frontend rendering; both sides must agree on them.

## A. Agent Health State Machine

Evaluate top-to-bottom; **first match wins**.

| Condition | State |
|---|---|
| `pulse_status = dead` AND `last_seen > 5m` | **CRITICAL** |
| `pulse_status = error` AND `consecutive_errors ≥ 3` | **WARNING** |
| `pulse_status = error` AND `consecutive_errors < 3` | **INFO** (transient) |
| `pulse_status = alive` AND `drift > 10%` | **WARNING** (unless already CRITICAL) |
| `pulse_status = alive` AND `errors_24h > 5` | **WARNING** |
| `pulse_status = alive` AND `debt_score > 60` | **INFO** (needs attention) |
| `pulse_status = alive` AND `errors_24h = 0` AND `drift < 10%` AND `debt_score < 30` | **HEALTHY** |
| no pulse data for `> 4h` | **UNKNOWN** (not dead — may simply not be monitored) |

> **Design note:** UNKNOWN ≠ CRITICAL. Rendering UNKNOWN as red is the single most common way to make an agent dashboard lie. UNKNOWN uses the gray neutral dot, never the critical red.

## B. Fleet Verdict Thresholds

| Condition | Verdict | Sentence template |
|---|---|---|
| Any CRITICAL agent | 🔴 Red | "{n} agents need attention — {names}" |
| Any WARNING, no CRITICAL | 🟡 Amber | "All agents operational — {n} showing signs" |
| All HEALTHY, some UNKNOWN | 🟢 Green + note | "All monitored agents healthy. {n} with unknown status." |
| All HEALTHY | 🟢 Green | "Fleet healthy — all {n} agents operating normally" |

The verdict is a **sentence**, never a count. "12 agents · 10🟢 1🟡 1🔴" is raw data; the verdict is the read.

## C. Discovery Gap Severity

`gap = discovered_at − happened_at`

| Gap | Treatment |
|---|---|
| `< 15m` | no badge (acceptable poll delay) |
| `15m – 2h` | amber badge: "discovered {gap} late" |
| `> 2h` | red badge: "CRITICAL gap — {gap}" |
| cumulative `> 4h` across active alerts | summary banner at top of alerts rail |

## D. Data Quality Tier (per agent)

| Tier | Label | Definition |
|---|---|---|
| 1 | **Accurate ✅** | OTEL-sourced `token_logs` in last 24h **and** watch daemon running |
| 2 | **Mixed** | OTEL data present but stale (>24h) **and** watch data present |
| 3 | **Estimated ⚠️** | watch-only, no OTEL data, daemon running |
| 4 | **Stale** | no data of any kind in last 4h |

Fleet-level quality = **% of agents in Tier 1**. Surfaced in the verdict bar data-quality chip so staleness is visible *from the fleet view*, not buried in Token Analytics.

## E. Cache Efficiency Scoring

`cache_rate = cache_read_tokens ÷ (cache_read_tokens + cache_create_tokens)`

| Rate | Treatment |
|---|---|
| `> 60%` | green — "Excellent — saving ${X}/day" |
| `30 – 60%` | amber — "${Y} savings left on the table" |
| `< 30%` | red — "Poor — enable cache or check provider config" |
| no data | gray — "Cache tracking not available" |

## F. Drift Classification

| Delta | Class | Treatment |
|---|---|---|
| `< 5%` | normal | green |
| `5 – 10%` | watch | amber |
| `> 10%` | breach | red — actionable |
| `> 20%` | critical | red + pulse animation — immediate |

Per-component drift drives component-level suggestions: "skills +18% → suggest compression target."

## G. Memory Debt Thresholds

| Score | State | Treatment |
|---|---|---|
| `0 – 30` | healthy | green |
| `31 – 60` | needs attention | amber — suggest garden scan |
| `61 – 100` | critical | red — garden scan overdue |

## H. Heal Effectiveness Score

`effectiveness = success_heals ÷ total_heals × 100`

| Score | Treatment |
|---|---|
| `> 90%` | green — "Heal effective" |
| `70 – 90%` | amber — "Some failures" |
| `< 70%` | red — "Heal may be making things worse — review config" |

## I. Anomaly Score (future, v0.4)

Flag when **any** holds:
- z-score of `cost_per_turn` `> 3σ` above the agent's 7-day moving average
- `tool_call_count > 20` (unusual tool explosion)
- `consecutive_pulse_errors > 5` (degraded, not dead)

Source: `token_logs.anomaly_score`, plus on-the-fly computation from `token_logs.cost`.

---

# Section 3 — Endpoint Specification

FastAPI + htmx. Most endpoints return **HTML partials** (htmx swaps), not JSON. The `Q?` column ties each endpoint to the four questions of Section 1.

| Endpoint | Params | Response | Data source | Query pattern | Refresh | Q? |
|---|---|---|---|---|---|---|
| `GET /api/fleet/verdict` | — | HTML: verdict bar | `pulse_log` + `circuit_breakers` + `chisel_drift` | Latest pulse per agent + circuit trip count + max drift → run §2-B | 30s | Q3 |
| `GET /api/agents` | `?status=&q=&page=` | HTML: agent cards | `pulse_log` + `chisel_trims` + `chisel_drift` + `errors` + `circuit_breakers` + `clawforge_garden` + `token_logs` | Latest per agent, grouped/sorted by §2-A state | 30s | Q1·Q2 |
| `GET /api/agent-detail/{name}` | `?tab=health\|guard\|errors\|tokens\|memory` | HTML: detail/inline tab content | `pulse_log` + circuit events + `errors` + `chisel_trims` + `chisel_drift` + `clawforge_garden` + `token_logs` | Aggregated by `agent_name`, time-window scoped | on demand | Q1·Q2·Q3·Q4 |
| `GET /api/alerts` | — | HTML: alerts panel | `circuit_breakers` + `chisel_drift` + `errors` + `alert_log` | Severity-sorted; compute discovery gap (§2-C) per row | 60s | Q2 |
| `GET /api/error-timeline` | `?days=&agent=&severity=` | HTML: timeline rows | `errors` + `pulse_log` | Reverse-chronological; compute Gantt offset+width per event | on demand | Q1 |
| `GET /api/token-analytics` | `?agent=&days=` | HTML: charts + breakdown | `token_logs` + `token_pricing` + `compress_log` | Time-series by hour/day; per-component cost rollup | on demand | Q4 |
| `GET /api/data-quality` | — | JSON (verdict-bar chip) | `token_logs` (source count) + `pulse_log` (freshness) | Per-agent source distribution → §2-D tiering | 60s | Q4 |
| `GET /api/drift/{name}` | `?days=` | HTML: per-component sparklines | `chisel_drift` + `chisel_trims` | 7/30-day delta per component; breach flags (§2-F) | on demand | Q2·Q3 |
| `GET /api/brain/{name}` | `?mode=preview\|apply` | HTML: compression preview/apply | `chisel_trims` + `compress_log` + `token_logs` | Before/after token counts + projected savings | on demand | Q3·Q4 |
| `GET /api/heal` | `?agent=` | HTML: heal status + history | `heal_events` + `heal_config` + `circuit_breakers` | Toggle/status/history; compute effectiveness (§2-H) | 30s | Q2·Q3 |

> **Note on the original "modal" detail endpoint:** `agent-detail` is retained but its default render target is the **inline mini-panel** (per the modal-fatigue fix), with the full surface available on explicit "open detail." Same endpoint, two mount points.

---

# Section 4 — What NOT to Surface

Of 47 tables, most are substrate, not signal. Surfacing them is how a dashboard becomes noise. Each entry below is hidden by default; the "becomes visible when" column is the *only* condition that promotes it.

| Table | Why it's low-signal | Becomes visible when |
|---|---|---|
| `telemetry_events` | ObserveCo's own install tracking / version pings. Zero user value. | **Never** in user-facing UI. |
| `dead_letter_queue` | Operational delivery detail. | Only inside an alert-delivery investigation when `failed_deliveries > 0`. |
| `config_format_registry` | Config-schema metadata. | Never — internal parsing concern. |
| `self_monitor_budget` | ObserveCo's *own* LLM usage. Mixing it into fleet cost corrupts Q4. | Admin section only, clearly separated from agent spend. |
| `pathway_node_types` | Schema metadata for the topology graph. | Never (the graph reads it, the user doesn't). |
| `token_component_config` | Configuration of how components are parsed. | Settings → advanced, never in fleet view. |
| `action_log` | Redundant with `heal_events` + `compress_log`. | Never independently; kept for audit/export only. |
| `auth_sessions` | Auth infrastructure. | Only on login failure / session-expiry banner. |
| `agent_kill_log` | Operational audit trail. | Agent detail → Settings → History only. |
| `llm_provider_registry` (raw) | Reference table; meaningless alone. | Joined into cost views; never shown as a standalone list. |
| `pathway_nodes` / `pathway_edges` (raw counts) | "111 nodes / 80 edges" is trivia. | Only as the rendered topology map, never as raw counters in the verdict/cards. |

**Principle:** a table earns a pixel by changing a decision. If surfacing it wouldn't change what the 3am operator *does*, it stays in the database.

---

# Section 5 — The "So What?" Layer

This is the layer that separates an observability **product** from a data **viewer**. Every raw value the UI shows must carry a derived, actionable read. The left two columns are what the database holds; the right column is what we render beside it.

| Data point | Raw value | "So what?" insight |
|---|---|---|
| `token_logs.total_tokens` | 42,190 | "42K tokens in context. 31% is skills — 2 of 8 skills never fire. Compressing unused skills saves ~1,800 tokens/turn." |
| `chisel_drift.delta_pct` (skills) | +12.4% | "Skills grew 12.4% this week — 3 new rule blocks added. At this rate it exceeds the context window in ~6 weeks." |
| `clawforge_garden.debt_score` | 48 | "Memory debt 48/100 — 2 contradictions (agent claims GPT-4 one turn, Claude the next). Run a garden scan to resolve." |
| `circuit_breakers.tripped` | true | "Circuit tripped after 3 connection failures. Cooldown until 11:15. Unreachable 2h 14m — start manually or wait out cooldown." |
| `token_logs.cache_read_tokens` | 340 | "Cache read rate 8% — you pay full generation every turn. kepler hits 72%. Check whether cache is enabled in your provider config." |
| `token_logs.source` | `watch` only | "No OTEL data — 78% of token records are estimated from SOUL.md. Install the Hermes telemetry plugin for accurate per-turn cost." |
| `pulse_log.latency_ms` | 980 | "Pulse latency spiked to 980ms at 03:15 — ~1s unresponsive. Not a crash, but it coincides with the memory growth detected the same day." |
| `heal_events.status` | success | "Auto-healed at 03:00:35 — restart took 4.2s, 1 retry. Root cause: memory_bloat flagged by L2 trending at 02:58." |
| `chisel_trims` (skills count) | 8 skills, 2 triggered | "6 of 8 skills haven't fired in 7 days — they're pure context cost. Move them behind intent-aware loading." |
| `token_logs.cost` per-agent vs per-task | X $0.14/turn, Y $2.10/turn | "Same task, same model (`claude-sonnet-4`), 15× cost. Y is likely reloading memory every turn — inspect its loader config." |
| `l2_trending.signal` | memory_bloat | "Proactive signal: memory is bloating *before* errors appear. You have a window to garden-scan now and avoid the degradation entirely." |
| `compress_log.savings_pct` | 34% | "Last Full compression cut this agent 34% (12.4K → 8.2K tokens) with no quality regression. The same profile applies to dreamer." |
| `chisel_drift` (memory) + `errors_24h` | mem +28%, errors +23% | "Memory grew 28% and errors rose 23% the same day — strong correlation. The new context files loaded Tuesday are the likely cause." |
| `pulse_log` consecutive errors | 4 (alive) | "Degraded, not dead — 4 consecutive pulse errors but still responding. This is the window to intervene before the circuit trips." |
| `token_logs.anomaly_score` | 0.71 | "Cost-per-turn is 3.2σ above this agent's 7-day average. Something changed in its behavior today — check the turn-by-turn tool trace." |
| `trace_spans` (delegation depth) | 1 → 3 sub-agents | "This 'single request' fanned out to 3 sub-agents and 11 sub-calls. Flat request counts hide this — the real unit of work is the chain." |

**Rule for builders:** if you can only show the left column, the feature isn't done. The right column is the deliverable.

---

# Section 6 — The Agent-Specific Design Principle

> **Every dashboard element must pass this test:**
> *"Could a traditional monitoring tool (Grafana / Datadog / New Relic) show this same metric with the same insight?"*
>
> **If YES** — the element is **table-stakes**. It must be present, but it is not our differentiator. Style it cleanly, keep it legible, and do not overinvest.
>
> **If NO** — the element is **agent-specific**. It is our moat. Make it prominent, annotate it richly, attach the "so what?" insight. This is what we charge for.

**Table-stakes (YES — present, but quiet):**
- Uptime / status dot
- Latency number
- Error-count badge
- Total spend figure

**Agent-specific (NO — prominent, annotated, the product):**
- 5-segment token composition bar with per-component drift
- Discovery gap badge (when it happened vs when you found out)
- Confidence score with FP/FN risk
- Data-quality chip (otel vs watch — two pipelines, one card)
- Component-level cost breakdown ("42% of spend is skills")
- Memory-debt trend with contradiction detection
- Heal effectiveness with root-cause attribution
- Pulse timeline with **latency per beat** annotated against component drift

**Operational consequence:** when screen space, attention, or build time is scarce, cut from the table-stakes column first. A clean uptime dot that loses 20% of its polish costs us nothing. A token composition bar that loses its drift annotation costs us the category.
