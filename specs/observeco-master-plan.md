# ObserveCo — Master Plan (Single Source of Truth)
**Document status:** Live — v0.5.0 "Capability Monitoring Layer"
**Last updated:** 2026-07-19 (v9) — v0.7.0 Adaptive Harness Layer added (MemoHarness 2026)
**Scope:** Hermes agents on macOS (local Mac Mini). True agent-specific observability (tracing + structured logging + evaluation + behavioral monitoring) + capability monitoring (canary + grid + config-aware baselines + drift detection). OpenClaw and multi-framework support deferred to future release.
**Author:** Main

---

## 1. Product Identity

| Attribute | Value |
|-----------|-------|
| **One-liner** | ObserveCo tells you if your AI agents are working, what they're doing, where your money goes — and whether they're getting worse |
| **Positioning** | "ObserveCo tells you if your AI agents are working, what they're doing, where your money goes — and whether they're getting worse." — Updated 2026-07-02 |
| **Primary Target** | Hermes users running agents locally on macOS (Mac Mini). Local-first, Hermes-native observability. |
| **What it does** | CLI + dashboard that discovers your Hermes agents, monitors their health, analyses token usage, detects drift, auto-heals failures, and uses your own LLM to diagnose crashes, classify alerts, and guide first-run setup — all local, no cloud |
||| **License** | MIT (free forever for Hermes users — all currently-built features open, no gating, no trial needed). **LLM features use your own API key** (`OBSERVECO_LLM_API_KEY` — bring-your-own-key, no inference costs on us). Static fallbacks when no key configured. **Future Pro tier** (after beachhead validated) will offer advanced features (push alerts, extended history, auto-heal) via 30-day trial. Trial would start on explicit Pro feature access, not on install. Pro tier pricing deferred until beachhead validated. See `specs/commercial-strategy-v2.md` for full rationale. |
| **Free badge** | `Free forever · MIT license · No cloud · Hermes native` — always visible in dashboard header and README |
| **Supersedes** | ERIS (runtime integrity) + CHISEL (context observability) — merged into single product |
| **Framework support** | **Hermes (primary).** OpenClaw and multi-framework support deferred to post-v1.0. |
| **Storage** | Local SQLite (`~/.observeco/pulse.db`) — all data local, no telemetry |
| **Install** | `pip install observeco[dashboard] && observeco dashboard` |

---

## 2. Feature Matrix (Complete)

| # | Feature | Category | Status | Free (now) | Pro (future, post-beachhead) | Effort | Spec |
|---|---------|----------|--------|------|-------------|--------|------|
| 1 | Fleet view — per-agent cards with status, token bar, drift, error badge | Dashboard | ✅ Live | ✅ | ✅ | — | — |
|| 1a | Fleet view: type-based grouping (Agents / Services / Workflows) | Dashboard | ✅ Live | ✅ | ✅ | — | observeco-master-plan.md §3.1 |
|| 1b | Fleet view: delete per agent (× button → removes from DB + persists exclusion in agents.json to prevent re-discovery) | Dashboard | ✅ Live | ✅ | ✅ | — | observeco-master-plan.md §3.1 |
| 1c | Fleet view: missing-agent feedback button in header | Dashboard | ✅ Live | ✅ | ✅ | — | observeco-master-plan.md §3.1 |
| 1d | Fleet view: 5 clickable metric rows per card (Health/Guard/Errors/Brain size/Composition) | Dashboard | ✅ Live | ✅ | ✅ | — | observeco-master-plan.md §3.1 |
| 1e | Fleet view: drill-down modals (Health pulse timeline + annotated timeline + categorized verdict, Guard failure history + settings + explanation, Error timeline + verdict + Pro upsell) | Dashboard | ✅ Live | ✅ | ✅ | — | observeco-master-plan.md §3.2-3.6 |
| 2 | Pulse check (alive/dead/error) | Monitoring | ✅ Live | ✅ | ✅ | — | — |
| 3 | Circuit breakers (N-failure + auto-cooldown) | Monitoring | ✅ Live | ✅ | ✅ | — | — |
| 4 | Token breakdown bar chart (SOUL.md by watch daemon) | Analysis | ✅ Live | ✅ | ✅ | — | — |
| | 4a | Brain Analysis: Savings Comparison + Compression UI (Manual preview/apply, Lite/Full, Auto-Watch Pro teaser) | Analysis | ✅ Live | ✅ Preview + Lite Apply | ✅ Full + Auto-Watch | — | brain-analysis.html mockup |
| | 4b | Compression Backend: /api/chisel/compress, `chisel compress` CLI, Lite/Full algorithms, backup/restore | Analysis | ✅ Live | ✅ Lite | ✅ Full | — | — |
| | 4c | Token Optimiser Data Layer: DB tables (turn_log, skill_usage, guidance_fire, compress_log), /api/optimiser/stats endpoint | Analysis | ✅ Live | ✅ Demo data | ✅ Real data at 200+ turns | — | — |
| | 4d | Auto-Compression Daemon: `chisel watch start/stop/status`, polling-based skill-compression monitoring | Analysis | ✅ Live | ✅ Daemon runs Lite | ✅ Daemon runs Full | — | — |
|| 5 | 7-day drift trend per component | Analysis | ✅ Live — v2 (2026-07-10) | ✅ | ✅ | — | observeco-master-plan.md §3.5 |
| 6 | Error history (last 24h) | Dashboard | ✅ Live | ✅ | ✅ | — | — |
| 7 | Heal tab (manual trigger + /api/trigger-heal diagnosis — broken onclick quoting fixed, duplicate button removed from API response) | Self-Heal | ✅ Live | ✅ | ✅ | — | — |
| 8 | In-dashboard alerts — severity-coded feed + discovery gaps + cumulative downtime banner + NEW badge | Alerts | ✅ Live | ✅ Discovery gap badges, cumulative downtime banner, NEW/unviewed indicators, push delivery (Telegram, Discord, webhook, email) | ✅ Same (Pro adds auto-heal integration + subscription management + delivery log) | — | — |
| 9 | Memory Garden (dupes, contradictions, debt score) | Analysis | ✅ Fleet summary (Brain Analysis) + ✅ Per-agent detail (agent modal) | ✅ | ✅ | — | observeco-master-plan.md §Memory Garden |
| 10 | ClawForge CLI (profile/load/garden/history) | CLI | ✅ Live | ✅ | ✅ | — | — |
| 11 | All CLI commands (pulse, circuit, chisel, clawforge) | CLI | ✅ Live | ✅ | ✅ | — | — |
| 12 | Local SQLite, zero cloud, zero telemetry | Infrastructure | ✅ Live | ✅ | ✅ | — | — |
| | | | | | | | |
|| **46** | **Fleet Comparison Tab** — side-by-side agent comparison matrix: tokens, composition bars, drift, errors, circuit, last seen | Dashboard | ✅ Live | ✅ Data table (all agents) | ✅ Same | ~1d | observeco-master-plan.md |
| **PLANNED** | | | | | | | |
||| 13 | System prompt compression (`observeco chisel compress`) | Analysis | ✅ Live — CLI + auto-watch daemon + dashboard savings card | ✅ `--mode lite` (guidance compression) + `--dry-run` | ✅ `--mode full` (memory culling + skill dedup + context refactor) + auto-watch daemon + dashboard savings | ~2.5d | observeco-master-plan.md §13 |
||| 14 | Cloud token tracking — post-turn webhook (Hermes hook → `POST /api/tokens/log`) + provider billing API fallback | Monitoring | ✅ Backend endpoint + ✅ DB migration 29 + ✅ Hermes hook + ✅ Dashboard Token Analytics tab: 5-chart grid (Token Composition stacked bar [Input/Output/Cache/Est], Tokens/Turn, Output/Input, Cache Hit Rate, Cost/Turn — each efficiency chart with benchmark bands) + verdict card + cache-by-agent chart + confidence indicator + breakdown sorted by cost + % column + per-turn timeline / ✅ Model field wired in OTEL parser | ✅ 24h component breakdown per agent + per-provider cost + gap % + cost verdict + per-agent cache rates | ✅ Never-pruned history + anomaly (+3σ) + budget alerts (daily/cost/anomaly) + fleet comparison | ~3d | observeco-master-plan.md §14 |
||| 15 | Auto-heal (watch daemon trigger, auto-restart + L2 proactive + L3 learning loop) | Self-Heal | ✅ Backend (L1 auto-restart, L2 proactive, LLM escalation, HealCircuit) / ❌ Dashboard UI (toggle, status card, heal history, per-agent config) / 🔴 L3 spec (obs-spec-081) | ✅ manual Heal button + dashboard alerts + L2 trends / ❌ Dashboard config UI | ✅ L1 crash recovery (~5s) + L2 proactive + structured diagnosis (7%) + dashboard config UI + L3 prevention skill auto-creation + FTS5 pattern matching | ~1d + L2 built + ~2d L3 spec | observeco-master-plan.md §15 + obs-spec-081 |
|| 16 | OpenClaw runtime plugin (`@observeco/clawforge-plugin`) — dashboard stats + hooks now auth-exempt (401 fix) | Analysis | 🔴 Deferred (post-v1.0) | ✅ (MIT, free forever) + dashboard stats + demo data | ✅ Intent classifier training + custom demotion rules + fleet comparison + budget alerts | ~7d (backend + dashboard) | observeco-master-plan.md §3.16 |
||| 17 | Push alerts (Telegram, webhook, email) — Discord pending | Alerts | ✅ Backend (Telegram, webhook, email delivery) / 🔴 Discord / ❌ Dashboard UI (subscription management, delivery log, test button) | ✅ Backend delivery (Telegram, webhook, email) / ❌ Dashboard subscription UI | ✅ Auto-heal integration + subscription management + Discord delivery + dashboard UI | ~3d (engine + CLI + API + dashboard) | observeco-master-plan.md §17 |
||| 18 | Extended history (7d, pruning cron at 3am) | Dashboard | ✅ Live — error tab range selector (24h/7d/30d/90d) + prune cron + L2 baselines | ✅ 7d + L2 baselines (RSS, P95, errors, upstream) | ✅ Never-pruned + L2 trend baselines (14d/21d/30d/90d) + configurable retention per data type | ~4d | observeco-master-plan.md §18 |
|||| **50** | **Capability Monitoring Data Model** — 8 new DB tables: canary_tasks, canary_runs, canary_results, canary_baselines, drift_events, config_snapshots, grid_runs, grid_results | **Infrastructure** | 🔴 Spec | ✅ All tables (local SQLite) | ✅ Same | ~1d | obs-spec-050-capability-monitoring-data.md |
|||| **51** | **Canary Runner** — task execution, scoring (8 assertion types), baseline management, CI via bootstrap resampling, config-aware baselines, daily schedule (3am cron) | **Capability** | ✅ Live — v2 (2026-07-10) | ✅ CLI + dashboard + daily cron | ✅ Same | ~2d | obs-spec-051-canary-runner.md |
||||| **52** | **Drift Detection** — statistical comparison (z-test), configurable thresholds (breach/warning/info), per-task drift breakdown, shareable chart view, triage path, per-task accuracy time-series chart with category filters | **Capability** | ✅ Live — v2 (2026-07-10) | ✅ Dashboard + drift chart + per-task chart + shareable view | ✅ Push alerts on drift breach | ~2d | obs-spec-052-drift-detection.md + obs-spec-058-per-task-drift-chart.md |
|||| **53** | **Config Timeline** — auto-detected SOUL.md/config changes, segment badges, drift event linking, agent selector | **Capability** | 🔴 Spec | ✅ Dashboard timeline + agent selector | ✅ Same | ~1.5d | obs-spec-053-config-timeline.md |
|||| **54** | **Grid Report** — model × config comparison matrix, CI per cell, flags column (loop/unsafe/shortcut), "read by pairing" guidance, CSV export | **Capability** | 🔴 Spec | ✅ Dashboard grid table + export | ✅ Same | ~2d | obs-spec-054-grid-report.md |
||||| **55** | **Task Definition UI** — YAML editor + form mode, 5 assertion types, template variables, 9 built-in tasks, import/export, model override field, built-in vs custom visual distinction, LLM judge reasoning panel | **Capability** | ✅ Live | ✅ CLI + dashboard editor + judge reasoning panel | ✅ Same | ~1.5d | obs-spec-055-task-definition.md |
||||| **58** | **Per-Task Drift Chart** — multi-line Chart.js chart with per-task accuracy time series, category filter chips, severity-tagged legend, click-to-toggle task visibility | **Capability** | ✅ Live (2026-07-10) | ✅ Dashboard per-task chart | ✅ Same | ~1d | obs-spec-058-per-task-drift-chart.md |
||||| **59** | **Quality Benchmark Card Row** — compact canary accuracy row in fleet agent cards with expandable per-category breakdown (Variant C) | **Capability** | ✅ Live (2026-07-10) | ✅ Fleet card row + expandable detail | ✅ Same | ~1d | obs-spec-059-quality-benchmark-card.md |
|||||| **56** | **Automated Harness Optimization Loop** — Meta-Harness loop (Niklaus/HF 2026): LLM proposer reads canary trajectories, copies current best harness, adds one mechanism; lab evaluates on dev split (3 trials); promotion gate (blended score ≥1pp over incumbent); leakage audit (reject if test split touched); copy-and-adapt compounding. CLI: `observeco harness optimize --agent AGENT --iterations N`. Requires: dev/test split (§50), blended score (§54), provider retry (adapter), blowup detection (canary). **v0.7.0 upgrade:** Experience-based adaptation (MemoHarness 2026): dual-layer experience bank (per-case diagnoses + global patterns), per-case retrieval by similarity, 6 editable control dimensions (context, tools, orchestration, memory, decoding, output). | **Capability** | 🔴 Spec (v0.6.0) | ✅ CLI + loop history + promoted mechanisms log | ✅ Same + dashboard visualization of frontier progression | ~5d (v0.6.0) + ~4d (v0.7.0 upgrade) | obs-spec-056-harness-optimization-loop.md |
||| 19 | In-dashboard Glossary & FAQ | Dashboard | ✅ Live — 51 topics with detail + FAQ | ✅ | ✅ | ~3h (built) | observeco-master-plan.md §3.20 |
||||||| **57** | **Benchmark Methodology Upgrade** — LLM-as-a-Verifier assertions (1-20 scale, K=3, logprob-based expected score), reference outputs, per-task drift fix, temperature control, concrete fixtures (no template variables), dev/test split activation, category/difficulty metadata, Inspect AI alignment. Fixes: weak assertions (keyword containment), n=3 bootstrap instability, aggregate vs per-task drift, template variable skipping. 🔗 Blocks obs-spec-056 (harness optimization requires dev/test split and per-task baselines from obs-spec-057). | **Capability** | ✅ Live — v3 (2026-07-11) — all sub-items complete: 8 assertion types (incl. llm_judge/logprob-verifier, json_schema, ordering, tool_call_validation), per-task drift fix, z-test n1 fix, bootstrap n≥5 guard, trials=10, temperature control via Hermes CLI `--temperature` (patch at `patches/hermes-cli-temperature.patch`), daily 3am cron, llm_judge→algorithmic fallback when no API key (extracts logic tokens, not raw keywords — robust to naming variations). `code-generation` task uses llm_judge. **Production-verified 2026-07-11:** end-to-end canary run works (4 tasks, 50% accuracy on free model), 54/54 tests pass. Model selection: dynamic priority chain (per-task > `OBSERVECO_CANARY_MODEL` env var > adapter > Hermes default), `.env` auto-loaded at import time. | ✅ All | ✅ Same | ~5d | obs-spec-057-benchmark-methodology-upgrade.md |
|||||||| **60** | **History-Assisted Task Generation** — mine real agent conversations from `~/.hermes/state.db`, cluster by topic, LLM proposes canary task drafts with assertions. User reviews/edits/approves via dashboard task editor (human-anchored ground truth). Approved tasks run alongside 10 generic tasks in daily canary via Hermes adapter (with `-p default` — skills, tools, SOUL.md). Two-tier scoring: generic (model capability) + user-defined (agent quality on real work). CLI: `observeco canary suggest-tasks --agent default --limit 10`. Rejects fully-automated approach — LLM proposes, user disposes. | **Capability** | 🔴 Spec → ✅ **Built** (2026-07-12) | ✅ CLI + dashboard pending-review tab (Active/Pending toggle) + source-session modal + two-tier canary score | ✅ Same | ~1d | obs-spec-060-history-assisted-task-generation.md |\n||||||| **86** | **Canary Cost & Token Tracking** — parse token usage from Hermes CLI `--verbose` stderr output, estimate cost from a pricing table, return real cost/tokens from the Hermes adapter. All 157 canary runs show $0.0000/0 tokens because the adapter never parses the token info Hermes already emits. Fix: add `--verbose` flag, parse `CompletionUsage(...)` from stderr, add pricing table for cost estimation, return `cost`/`tokens` in adapter response. No schema changes needed. | **Capability** | 🔴 Spec (v0.6.0) | ✅ Real cost/tokens in canary runs + dashboard | ✅ Same | ~2h | obs-spec-086-canary-cost-tracking.md |
|| ~~**20**~~ | ~~**Skill Audit**~~ — ~~merged into Brain Analysis~~ | ~~**Analysis**~~ | ~~**✅ Merged**~~ | ~~✅~~ | ~~✅~~ | ~~—~~ | ~~—~~ |
||| 21 | Communication Pathway Map (subgraph folding, cron edge metadata, FK constraint fix, daemon heartbeat metadata, sticky header) | Diagnostics | ✅ Live | ✅ Interactive graph with 111 nodes + 80 edges + 77 cron_delivery edges + platform node + dead ends + subgraph folding + detail panel with metadata | ✅ Detail panel + drag + auto-alert | ~3d (built) + 1d (FK fix) | observeco-master-plan.md §3.19 |
|||| 22 | Agent Health Detection Engine (process health + OTel + cross-framework + platform connectivity + crash analysis) | Infrastructure | ✅ Layers 1-2 / 🔴 P2-P5 (platform connectivity, crash analysis, costs, comm tracing, CI/CD) | ✅ Layers 1-2 only (process health, OTel, cross-framework) | ✅ Same (no gating) | ~P0-P6 | observeco-master-plan.md §3.22 |
|||| **23** | **Skill Artifacts + Cards System** (`observeco chisel artifacts` + `chisel cards`) | **Analysis** | **✅ Live** | ✅ Cached compressed `.md.compressed` per skill, `cards.json` (156 cards), `manifests.json`, CLI `observeco chisel cards` for top-30 rank, `observeco chisel artifacts --refresh` to rebuild. SkillOS `_load_skill_content()` prefers compressed cache over raw. `max_skill_content_bytes` reduced 8192→4096. | ✅ Same for all | ~1d | observeco-master-plan.md §3.23 |
||| **24** | **Config Hygiene Audit** (`observeco chisel config`) — scans Hermes config for duplicated prompts, low cache TTL, stale references. **Synergy:** shares token counting, YAML parsing, and savings estimation with `chisel/skill_compress.py`. Same pipeline, different target. | **Analysis** | **✅ Live** | ✅ CLI audit report with line-by-line findings + `--fix` flag + dashboard widget | ✅ Dashboard widget with scheduled auto-fix | ~1d | observeco-master-plan.md §3.24 |
||| **25** | **LLM-Powered Intelligence Service** — shared `llm_service` that every module calls for deeper diagnosis, alert enrichment, personalized first-run guidance, and per-agent summaries. Uses `OBSERVECO_LLM_API_KEY` (bring-your-own-key). Static fallbacks when no key configured. | **AI** | **✅ Live — v1** | ✅ BYOK — user provides their own LLM API key. Static fallbacks when no key. | ✅ All 7 consumers (3 deep + 4 shallow) | ~5d (3d built, 2 deferred) | observeco-master-plan.md §3.25 |
|||| **26** | **Self-serve billing management** — License status card (plan, trial countdown, action buttons), Stripe Customer Portal for paid subs, Cancel Trial with trial hardening (one-time offer), end-of-trial banner, 3 Stripe webhooks (subscription.deleted/updated/invoice.payment_failed) | **Commercial** | **✅ Live** | ✅ Free features always free. LLM uses BYOK (`OBSERVECO_LLM_API_KEY`). Trial = full Pro unlock (future). After trial: Free. | ✅ Pro features | ~4h | §3.28 |
|||| ~~**42** | **Transparent API Proxy** (`observeco proxy start`) — MITM proxy for **local LLM token tracking only** (ollama, llama.cpp). Routes by API key prefix, captures token usage from responses. Cloud LLM tracking delegated to post-turn webhook (§43).~~ **REMOVED 2026-06-19** — SDK-sidecar (`observeco instrument`) replaces the MITM proxy. Proxy was in the execution path with SSE torn-read risk and no supervisor process. SDK instrumentation is out-of-band, framework-aware, and zero crash risk. See `specs/adr-proxy-attribution.md` for deprecation record. | **REMOVED** | ❌ Deprecated | ❌ | ❌ | ~2d (built, then removed) | specs/adr-proxy-attribution.md (deprecated) |
|||| **43** | **Post-Turn Webhook (Cloud Token Tracking – Hermes)** — Agent-side fire-and-forget POST after every LLM turn. Payload: agent_name, turn_id, model, provider, total_tokens, component breakdown (identity/skills/memory/tools/guidance), latency_ms, tool_calls, topic_id. Sent to `POST /api/tokens/log` (endpoint exists + extended with model/latency/tool_calls/topic_id). Webhook is **primary** cloud tracking mechanism. Proxy covers local only. | **Monitoring** | ✅ Backend endpoint (`/api/tokens/log`) + ✅ DB migration 29 + ✅ **Hermes hook built** (fire-and-forget daemon thread, 2s timeout, OBSERVECO_URL configurable) / 🔴 Dashboard trend charts | ✅ 24h component breakdown per agent + per-provider cost attribution + per-model breakdown + per-topic model usage | ✅ Never-pruned history + anomaly detection (+3σ) + budget alerts (daily/cost/anomaly) + fleet comparison | ~1d (built) | specs/obs-spec-043-hermes-post-turn-hook.md |
||||| **44** | **Provider Billing API Fallback** — Query OpenAI/Anthropic/DeepSeek billing endpoints for aggregate token totals. Used to compute **attribution gap**: "92% attributed, 8% unattributed." Catches agents not instrumented with the webhook. | **Monitoring** | 🔴 Planned | ✅ Aggregate cloud spend total + gap % indicator on dashboard | ✅ Same | ~1d | specs/adr-proxy-attribution.md |
||||| **17b** | **Action Buttons in Push Notifications** — Telegram inline keyboards (restart/cooldown/trim), Discord buttons, webhook action URLs. Calls `/api/heal-action/{agent}/{action}`. Requires heal system `_execute_action()` (already built) + push alert infra (already built). | **Alerts** | 🔴 Planned | ❌ Pro | ✅ Same | ~4h | observeco-master-plan.md §3.17b |
||||| **64** | **Agent Health Report Card** — weekly digest via push alert. Aggregates 7d of: pulse uptime %, auto-heal count, circuit trips, compressions, token cost. One SQL query per metric, one Jinja2 template. All data exists in pulse_log, heal_events, circuit_events, compress_log, token_logs. | **Alerts** | 🔴 Planned | ✅ Weekly digest in dashboard | ✅ Push delivery + trend comparison | ~3h | observeco-master-plan.md §3.64 |
|||
||| **Hermes Observability Layer (v0.4.0 — new)** |
||| | | | | | | | |
|||| **T1** | **Tracing Layer** — integrate hermes-otel plugin, span hierarchy (root → subagent → tool), waterfall view, replay | **Observability** | 🔴 v0.4.0 | ✅ Per-agent span timeline + waterfall | ✅ Full trace tree + replay + export | ~3d | observeco-master-plan.md §3.T1 |
|||| **T2** | **Evaluation Layer** — Hermes eval export, basic evals (quality score, tool efficiency, retry flag, hallucination flag), quality trends per agent | **Observability** | 🔴 v0.4.0 | ✅ Eval event ingestion + quality trend per agent | ✅ Quality regression detection + correlation with drift/health + fleet quality comparison | ~2d | observeco-master-plan.md §3.T2 |
|||| **T3** | **Behavioral Monitoring** — Anomalies Inbox + taxonomy (no_tools, high_cost, long_gaps, retry_loops, context_pressure), Context Health Score, Relapse Prevention, Tool Efficiency, Context Source Utilisation | **Intelligence** | 🔴 v0.4.0 | ✅ Anomaly feed + severity + explanation + Context Health Score | ✅ Push alerts + auto-heal integration + anomaly attribution + resolution tracking | ~4d | observeco-master-plan.md §3.T3 |
|||| **T4** | **Unified Agent Data Model** — shared backend query layer (`agent_profile_service`) feeding Tracing, Evaluation, Behavioral Monitoring. Single `/api/agent/{id}/profile` endpoint. | **Infrastructure** | 🔴 v0.4.0 | ✅ | ✅ | ~1d | observeco-master-plan.md §3.T4 |
|||
|| **Quality Standards (ongoing — tracked here, not in feature rows above)** |
|| | | | | | | |
|||| **S1** | **Product Surface Overfitting Scan** — systematic scan of the product surface for Hermes-centric assumptions: defaults, paths, CLI text, docs examples, marketing copy, error messages, onboarding, API responses, config templates. Applied at 3 lifecycle gates: Gate 1 (spec time), Gate 2 (implementation), Gate 3 (diff — what changed this sprint). Not a feature — a **quality standard**. | **Quality** | **✅ Standard** | ✅ All | ✅ All | — | lifecycle-testing-protocol §Phase 1/3/8, playbook-evolution-meta §Product Surface Overfitting Escape |
||
|||

### 3.26 Security & Code Quality Debt (Deferred Audit Fixes — 2026-07-10)

> **Source:** Full codebase security/quality audit (3 parallel subagents) on 2026-07-10. 25 findings triaged into fixed / deferred / not-applicable. This section tracks the **deferred** items so they are not re-audited from scratch and have recorded reasoning. Billing/licensing code was explicitly excluded from the audit per scope.

**Already fixed in the same audit pass (for context):**
- `_html_escape` now escapes `'` and `"` (XSS root cause, 6 files + server.py)
- `server.py:3335` `\\n` → `\n` (MEMORY.md corruption bug)
- `fleet_qb.py:65` accuracy fix (was reporting binary pass rate as overall accuracy) + `fleet_qb.py:32` `(run["id"])` → `(run["id"],)` (endpoint was 500-crashing on all agents with runs)
- `server.py` cookie `secure=True` → conditional on `OBSERVECO_HTTPS`
- `server.py:7770` Telegram token preview → status-only (no credential leak)
- `oauth2.py:113` `_pending_states` bounded to 1000 entries
- 9× `except Exception: pass` in server.py + detail.py/fleet.py bare excepts → `logger.exception/warning`
- Personal references removed: `auth.py` "ref Sean's requirement", `enforcer.py` "Sean override", `telemetry_server.py` 5× "Sean" → "admin", `db.py` "Sean's decision" → "design decision"
- Location-specific test data: `capability.py` "Singapore rail line...Clementi to Jurong" → generic "metro line...city center to airport"
- Version mismatch fixed: `__init__.py` 0.2.0 → 0.5.0, template `0.3.0` → `{{VERSION}}` injected from backend at serve time
- Package manager allowlist: `doctor/cli.py` added `uv pip install`, `pipx install`, `poetry add`, `conda install`
- **Port centralization (2026-07-10):** All hardcoded ports moved to `dashboard/config.py` `PORTS` dataclass with env-var overrides. 19 files updated.
- **Watch intervals centralized (2026-07-10):** 11 hardcoded constants in `watch_consumers.py` moved to `dashboard/config.py` `WATCH_INTERVALS` dataclass with env-var overrides (`OBSERVECO_WATCH_<NAME>_SECONDS`).
- **LLM service config centralized (2026-07-10):** Hardcoded model names (`claude-sonnet-4-20250514`, `gpt-4o`, `gemini-2.0-flash`, `llama3.1`), `max_tokens=2048`, and timeouts (`30`/`60`) moved to `dashboard/config.py` `LLM` dataclass with env-var overrides (`OBSERVECO_LLM_<NAME>`). Ollama URL also uses `PORTS.ollama`.

**Deferred (with reasoning):**

| ID | Finding | Severity | Deferral reason | Blast radius if fixed | Re-audit trigger |
|----|---------|----------|-----------------|----------------------|------------------|
| D1 | `observeco run` spawns agent command with no `timeout=` | High | Agent runtime is *meant* to run indefinitely — a timeout would kill legitimate long-running agents. Tradeoff not worth it. If implemented, use a long opt-in timeout (e.g. 3600s) gated behind a flag, not a default. | Low (1 line) | If a hung agent command is observed blocking the CLI |
| D2 | No rate limiting on any endpoint (`/api/garden/scan`, `/api/skills-audit`, `/api/restart-quality/scan` spawn subprocesses / walk FS) | High | Structural change across all endpoints. Needs a design pass (SlowAPI vs simple in-memory limiter, which endpoints, what limits). DoS risk is localhost-only (low actual exposure). | Medium (new middleware + per-endpoint config) | If dashboard becomes remotely accessible, or if subprocess-spawning endpoints are hit in a loop |
| D3 | Dashboard token accepted via `?token=` query param (auth.py:128, realtime.py:83/98) | Medium | Breaking change for curl/TestClient users who rely on the query param. Needs deprecation plan (warn + remove after N versions) not silent removal. Header `X-ObserveCo-Token` is already the primary path. | Low (remove 1 fallback) but breaks existing usage | v0.6.0 release (bundle deprecation with version bump) |
| D4 | Errors return HTTP 200 (htmx can't distinguish success from error programmatically) | Medium | Cross-cutting htmx behavior change. Frontend relies on 200 + error HTML swap. Changing status codes could break swap logic. Better fix: add `HX-Trigger: error` header (non-breaking) + log exceptions. | Medium (all route files + frontend swap handlers) | When monitoring/alerting on dashboard errors is needed |
| D5 | `token_analytics.py` `include_source` injected raw into onclick | Low | `include_source` is a controlled enum (`"all"`/`"accurate"`), not user input. Original code already escapes agent names in option values via `_html_escape(a)`. Lower risk than audit implied. `_html_escape` fix (above) covers agent names. | Low (5 lines) | If `include_source` becomes user-controlled |
| D6 | N+1 DB queries in fleet loop (`get_trims`/`get_gardens`/`get_recent_pulses` per agent) | Low | 50 agents = 150+ queries, but fleet is currently <20 agents. Premature optimisation. Batch-fetch when agent count grows. | Medium (data flow refactor) | When agent count exceeds ~20 |
| D7 | `db.py` `_init_db` mixes `executescript` (auto-commit) with manual commits | Low | Migration transaction semantics are risky to change. Current migrations all succeeded on this machine. | High (migration behavior) | Next schema migration |
| D8 | Free-text `status` columns (`canary_runs.status`, `event_type`) with no enum/CHECK constraint | Low | Typos create unreachable states but no data loss. Needs migration + CHECK constraints. | High (schema migration) | When a status typo is observed causing a bug |
| D9 | `db.py` dynamic SQL column names via f-string (filtered through hardcoded sets) | Low | Pattern is fragile but currently safe (sets are hardcoded, not user input). Add validation if the set expands. | Low | If column names become dynamic/user-derived |
| D10 | Watch daemon silently swallows exceptions on 6+ paths | Low | Same class as D4/D11 — logging improvement, no behavior change. Lower priority than the 9 already fixed in server.py. | Low (logging) | When watch daemon misbehavior is observed |
| D11 | No input validation on query params (`days`/`hours` negative or huge; `include_source` not whitelisted) | Low | FastAPI `Query(ge=1, le=365)` constraints are trivial but touch many endpoints. `include_source` is already internally validated (line 175). | Zero (add constraints) | v0.6.0 cleanup pass |
| D12 | Subprocess spawning without PID tracking (server.py:6664/7232) — dashboard restarts accumulate zombie processes | Low | Operational issue, not a code bug per se. Process supervisor (launchd/systemd) is the proper fix, not in-process PID files. | Medium | If zombie accumulation is observed in production |
| D13 | Heartbeat file TOCTOU race (server.py:448) | Low | `exists()` then `read()` — tiny race window, only fails on concurrent delete (rare). Replace with try/except read. | Zero | If heartbeat read errors are observed |
| D14 | OAuth2 provider mutable on GET (`/auth/login?provider=xxx` mutates global state) | Low | Provider is validated against `PROVIDERS` dict before use (line 132); unknown providers return None. Low actual risk. | Low | If multi-provider support is added |

**Not applicable (verified during audit):**
- Migration 11 `DROP TABLE pathway_nodes` — already ran successfully on this machine (`pathway_nodes` exists, `_v11` stale table gone). No data loss.
- SQL injection — all user-supplied values use parameterized queries (`?` placeholders). Only f-string SQL is column names filtered through hardcoded sets (D9).
- Hardcoded secrets — all from env vars / generated files / `secrets.token_*()`.
- Resource leaks in DB connections — per-thread connections via `threading.local()`, intentional design, no pool exhaustion observed.

---

||| **Context Intelligence Layer (new 2026-06-06)** |
|| | | | | | | |
||| **27** | **Context Health Score** (0–100) — single number per agent answering "is my agent's brain healthy right now?" Computed from memory bloat, drift delta, context window utilisation trend, error rate, sources-skipped ratio. Warning <70, alert <50. | **Intelligence** | 🔴 Spec | ✅ Dashboard display + trend arrow | ✅ Push alerts on threshold breach + historical regression detection + fleet comparison | ~2d | observeco-master-plan.md §3.30 |
||| **28** | **Agent Relapse Prevention** — timeline view correlating SOUL.md edits, plugin installs/removes, config changes with degradation signals (drift spikes, error bursts, context health drops). Answers "what changed and broke things?" | **Intelligence** | 🔴 Spec | ✅ 7d timeline with annotations | ✅ Full history + regression correlation engine + auto-attribution | ~2d | observeco-master-plan.md §3.31 |
||| **29** | **Plugin Firewall Score** — per-plugin ranking by token cost per call, error rate, latency impact, success rate. Red/yellow/green. "Plugin X costs $0.03/call and fails 12% — disable it?" | **Intelligence** | 🔴 Spec | ✅ Per-agent plugin cost table | ✅ Cross-fleet comparison + auto-disable recommendation + budget threshold alerts | ~1.5d | observeco-master-plan.md §3.32 |
||| **30** | **Context Fire Drill** — simulation that projects whether an agent would survive a 50-turn conversation using existing profile data. Reports: what hits the limit first, which skills get evicted, estimated degradation point. | **Intelligence** | 🔴 Spec | ❌ Pro only | ✅ Full simulation + scenario comparison + historical projection | ~2d | observeco-master-plan.md §3.33 |
||| **31** | **Session Insurance** — local checkpoint of last N agent conversation context states. On crash or context corruption: "here's what it knew before that." Restore to checkpoint. | **Intelligence** | 🔴 Spec | ✅ Auto-checkpoint every 10 turns (local only) | ✅ Unlimited checkpoints + selective restore + pre-edit snapshots | ~2.5d | observeco-master-plan.md §3.34 |
||
|| **Unified Data Model (all Context Intelligence features read from one layer)** |
||| **32** | **Unified Agent Data Model** — shared backend query layer (`agent_profile_service`) that feeds Agent Profile, Companion Mode, Anomalies Inbox, Journey, and all Context Intelligence views. Single `/api/agent/{id}/profile` endpoint returns composite payload. | **Infrastructure** | 🔴 Spec | ✅ | ✅ | ~1d (extract after 2 consumers exist) | observeco-master-plan.md §3.35 |
||| **33** | **Anomalies Inbox** — fleet-wide issue surfacing. Reads pulse_log, chisel_drift, errors, context_health, config_events, circuit_breakers, plugin_tracking, l2_trending, token_logs, session_checkpoints. Surfaces dead agents, drift spikes, error bursts, context health drops, unexplained degradation, tripped circuits, red plugins, token cost spikes, crash+checkpoint pairs. The activation moment — "your agent has 3 problems right now." | **Intelligence** | 🔴 Spec | ✅ Dashboard tab + severity feed + NEW badge | ✅ Push alerts + auto-heal integration + anomaly attribution + resolution tracking | ~3d | observeco-master-plan.md §3.37 |
||| **34** | **Companion Mode** — `observeco companion` CLI command. Terminal status summary: fleet overview + context health + top plugins + active anomalies. Same data model, different surface. Powers OpenClaw launcher integration ("command-line ears"). | **CLI** | 🔴 Spec | ✅ Terminal output + colour coding | ✅ Interactive mode + watch mode + JSON output | ~2d | observeco-master-plan.md §3.38 |
||| **35** | **Journey / Onboarding** — "Get Started" tab tracking user milestones: agent discovered, brain viewed, chisel run, alert configured, fire drill run, first anomaly resolved. Context Fire Drill button + Session Insurance section. | **Dashboard** | 🔴 Spec | ✅ Milestone tracker + side panel | ✅ Contextual help + personalised recommendations | ~2d | observeco-master-plan.md §3.39 |
||| **36** | **Alert Management Surface** — unified place to view, acknowledge, resolve, snooze, and configure all alert types. Reads alert_log + alert_subscriptions + anomaly alerts + circuit breaker events + budget alerts. Shows delivery status, alert history, and trend. The missing layer between "we detect" (Anomalies Inbox) and "we deliver" (Push Alerts). | **Dashboard** | 🔴 Spec | ✅ Alert feed + actions + routing config + delivery status | ✅ Bulk actions + alert rules engine + trend analysis + escalation chains | ~3d | observeco-master-plan.md §3.40 |
||
|| **Dynamic Execution Layer (new 2026-06-07 — closes the OpenClaw/Hermes APM gap)** |
||| **37** | **Post-Turn Webhook** (superseded-by #43 — merged into Hermes post-turn hook) — structured JSON event emitted by OpenClaw plugin + Hermes wrapper after every agent turn. Payload: agent, turn_id, timestamp, tokens (input/output), tools_called, tool_errors, latency_ms, context_sources_loaded, context_sources_skipped, model. Observeco watch daemon receives via local HTTP endpoint or file sink. The single highest-value addition — gives Observeco per-turn execution data for our ecosystem users. | **Infrastructure** | 🔴 Spec | ✅ Webhook receiver + SQLite storage + basic timeline | ✅ Anomaly detection on latency/token spikes + cross-agent comparison + cost attribution | ~3d | observeco-master-plan.md §3.41 → superseded by specs/obs-spec-043-hermes-post-turn-hook.md |
|||| **38** | **Hermes Evaluation Trace Export** — structured JSON export of Hermes internal evaluation signals (quality score, tool efficiency, retry flag, hallucination flag) per turn. Reads from Hermes evaluation internals, writes to Observeco `eval_events` table. Gives Observeco *quality signals* — not just "how many tokens" but "was this turn good." | **Infrastructure** | 🔴 Superseded by §3.T2 | ✅ Eval event ingestion + quality trend per agent | ✅ Quality regression detection + correlation with drift/health + fleet quality comparison | ~2d | observeco-master-plan.md §3.T2 |
||| **39** | **Tool Efficiency Ranking** — derived from post-turn webhook data. Ranks every tool/skill by: cost per call, error rate, latency impact, success rate. Red/yellow/green. Surfaces "disable this tool" recommendations. Feeds Plugin Firewall (§3.32) with per-tool granularity (§3.32 is per-plugin, this is per-tool-call). | **Intelligence** | 🔴 Spec | ✅ Per-agent tool cost table + top-3 recommendations | ✅ Cross-fleet comparison + auto-disable suggestions + budget threshold alerts | ~1.5d | observeco-master-plan.md §3.43 |
||| **40** | **Context Source Utilisation Tracker** — derived from post-turn webhook data (context_sources_loaded vs context_sources_skipped). Tracks which skills/memory sections are actually used per turn vs loaded by default. Surfaces "these 2 skills add 1,400 tokens but are rarely used — remove from defaults." Feeds Context Fire Drill (§3.33) with real utilisation data. | **Intelligence** | 🔴 Spec | ✅ Per-agent utilisation table + lazy-load recommendations | ✅ Cross-fleet comparison + auto-suggest default demotion + trend analysis | ~1.5d | observeco-master-plan.md §3.44 |
||| **41** | **Structured Diagnostic Context for LLM Troubleshooting** | **Intelligence** | 🔴 Spec | ✅ Triggered troubleshooting + payload + LLM diagnosis + fix commands | ✅ Cross-agent patterns + fleet learning + export | ~4d | observeco-master-plan.md §3.45 |
||| **Agent Safety Guardrails** | **(new 2026-06-08 — Kepler–Hound debate: Token Rogue Scenarios, phases G1/G2/G3)** | | | | | | | | | |
||| **G1.1** | **Self-Monitoring Budget Cap** — ObserveCo's own LLM diagnosis calls tracked from separate token pool with non-configurable floor (100K tokens/day) and default ceiling (500K tokens/day). Token-based (not cost-based) to support multiple LLM providers. Graceful degradation at 100%. | **Infrastructure** | 🔴 Planned | ✅ Self-usage widget + budget status | ✅ Same | ~1d | observeco-master-plan.md §14.3.G1.1 |
||| **G1.2** | **Manual Kill Switch** — STOP button per agent card with 2-step confirmation. API endpoint for programmatic kill (`POST /api/agents/{id}/stop`). Every kill audit-logged. No auto-kill in v1. | **Dashboard + API** | 🔴 Planned | ✅ STOP button + confirmation + audit log | ✅ Same | ~2d | observeco-master-plan.md §14.3.G1.2 |
||| **G1.3** | **Activity-Based Circuit Breaker Config** — expose existing circuit breaker settings in dashboard UI. Activity thresholds (turns/min) alongside failure thresholds. | **Dashboard** | 🔴 Planned | ✅ Config UI for activity thresholds | ✅ Same | ~0.5d | observeco-master-plan.md §14.3.G1.3 |
||| **G1.4** | **Turn-Rate Alerting** — turns/minute metric per agent. Dashboard widget. Alert fires when rate exceeds configurable threshold (default 30 turns/min). | **Monitoring + Alerts** | 🔴 Planned | ✅ Turn-rate widget + threshold alert | ✅ Same | ~1d | observeco-master-plan.md §14.3.G1.4 |
||| **G1.5** | **Tool-Call Count Per Turn** — track tool calls per agent turn. Dashboard metric. Anomalous volume (>20 tools/turn) flagged. | **Monitoring** | 🔴 Planned | ✅ Tool-count widget + anomaly flag | ✅ Same | ~0.5d | observeco-master-plan.md §14.3.G1.5 |
||| **G1.6** | **Threat Model Documentation** — explicit published boundaries: what ObserveCo monitors, what it doesn't. README + /docs page. Honesty as competitive moat. | **Documentation** | 🔴 Planned | — | — | ~0.5d | observeco-master-plan.md §14.3.G1.6 |
||| **G2.1** | **Aggregate Fleet Spend Alerts** — alert when total fleet token spend exceeds daily/hourly budget. Requires §17 push alert infra. | **Alerts** | 🔴 Planned | ❌ Pro | ✅ Fleet-level budget alerts + threshold config | ~2d | observeco-master-plan.md §14.3.G2.1 |
||| **G2.2** | **Alert → Wait → Auto-Stop** — configurable escalation: detect → alert → wait Ns → auto-stop if no response. Opt-in only, never default-on. Requires G1.2 kill switch. | **Self-Heal + Alerts** | 🔴 Planned | ❌ Pro | ✅ Auto-escalation with configurable timeout | ~3d | observeco-master-plan.md §14.3.G2.2 |
||| **G2.3** | **Parent-Child Agent Lineage Tracking** — fleet view shows agent parent-child relationships. 100 sub-agents → 1 root cause. | **Dashboard** | 🔴 Planned | ✅ Lineage view | ✅ Same | ~3d | observeco-master-plan.md §14.3.G2.3 |
||| **G2.4** | **Output Consistency Analysis** — detect identical/near-identical tool calls across cycles. Flags stale-state pinning. | **Intelligence** | 🔴 Planned | ❌ Pro | ✅ Repetition detection + stale-state alerts | ~2d | observeco-master-plan.md §14.3.G2.4 |
||| **G2.5** | **Configurable Drift Lookback** — extend drift chart (§5) with 30/60/90-day lookback windows. | **Dashboard** | 🔴 Planned | ✅ All lookback windows | ✅ Same | ~0.5d | observeco-master-plan.md §14.3.G2.5 |
||| **G3.1** | **Cross-Agent Signal Flow Visibility** — track signal delivery between agents. Detect sent-but-never-acknowledged. Surface 'alive but not producing.' | **Intelligence** | 🔴 Planned | ❌ Pro | ✅ Signal flow map + deadlock detection | ~5d | observeco-master-plan.md §14.3.G3.1 |
||| **G3.2** | **Sophisticated Auto-Escalation** — multi-level escalation chains, severity-based timeouts, integration with §36 alert management. Opt-in Pro. | **Self-Heal + Alerts** | 🔴 Planned | ❌ Pro | ✅ Policy engine + escalation chains | ~3d | observeco-master-plan.md §14.3.G3.2 |
|||| **G3.3** | **Per-Turn Model Attribution** — track which model was used per turn. Diagnostic value for model escalation detection. | **Monitoring** | 🔴 Planned | ❌ Pro | ✅ Per-turn model label + cost attribution | ~1d | observeco-master-plan.md §14.3.G3.3 |
||
||| **Cross-Agent Observability (new 2026-06-10 — Multi-Agent Delegation & Telemetry)** |
||||| **53** | **OTel Trace Ingestion** — `post_to_observeco()` wired into `signal_tracer.py`. Every `delegate_task`/`task_result`/`bridge_signal` hop emits an OTel span to OTLP endpoint. Listener stores spans in new `trace_spans` table. Foundation for all multi-agent visibility. | **Infrastructure** | 🔴 Planned | ❌ Free (data layer only — all local) | ✅ Trace export (remote dashboard + aggregate fleet views) | ~2d | observeco-master-plan.md §3.53 |
||||| **54** | **delegate_task Protocol in signal_router** — wire the new `delegate_task`/`task_result`/`delegate_escalation` signal types into `signal_router.py`. Add tool-to-agent capability matching in `ecosystem.json`. Timeout, retry, escalation lifecycle enforced. GS-011 §Task Delegation Lifecycle. | **Infrastructure** | 🔴 Planned | ✅ All local delegation | ✅ Cross-ecosystem delegation + tool-based routing | ~2d | observeco-master-plan.md §3.54 |
||||| **55** | **Trace Tree Dashboard** — waterfall view of agent handoff chains. Each `delegate_task` hop shows: delegator → executor, tools used, latency per hop, token cost, status (completed/failed/escalated). Full chain from root initiator to leaf executor. Search/filter by task_id, agent, time range. Pro: export trace as JSON/PDF. | **Dashboard** | 🔴 Planned | ❌ Pro (LLM-intensive rendering) | ✅ Full trace tree + cross-fleet comparison + anom detection on chain latency/broken chains | ~3d |
||||| **56** | **A2A Adapter (Remote Agent Support)** — expose ObserveCo-local agents as A2A-discoverable endpoints (`/.well-known/agent.json`) and call remote A2A agents via HTTP JSON-RPC. Bridges local `delegate_task` protocol with Google A2A standard. Enables multi-machine agent swarms with uniform observability. Aligns with Hermes Issue #514. | **Infrastructure** | 🔴 Planned | ❌ A2A is Pro-only | ✅ Remote agent delegation + Agent Card discovery | ~5d | observeco-master-plan.md §3.56 |
||
|| **Session Intelligence Layer (new 2026-06-16 — agenttrace-inspired features)** |
||||| **57** | **Multi-Source Log Parser Engine** — extensible parser-per-source architecture supporting Claude Code, Codex CLI, Gemini CLI, Qwen Code, Cline, Aider, Cursor exports, Hermes DB, OpenClaw, Kimi CLI, Copilot logs, and generic JSON/JSONL. Each source gets a dedicated parser module with format detection (`DetectFormat`). ObserveCo currently detects Hermes + OpenClaw agents only — this expands to any agent that writes session logs. Reference: agenttrace (github.com/luoyuctl/agenttrace). | **Infrastructure** | 🔴 Planned | ✅ All parsers (local data, no gating) | ✅ Same | ~4d | observeco-master-plan.md §3.57 |
||||| **58** | **Cost Estimation Engine** — built-in model pricing table mapping model names → $/token (input/output/cache). Auto-estimates per-session, per-agent, per-day, per-model cost from token counts already tracked. Dashboard widget: total estimated spend, spend-by-model breakdown, spend trend. Currently ObserveCo tracks tokens but not dollars. Reference: agenttrace pricing table pattern. | **Monitoring** | 🔴 Planned | ✅ 24h cost breakdown per agent + per-model | ✅ Never-pruned cost history + budget alerts (daily/spike/anomaly) + fleet cost comparison + provider billing API cross-check | ~2d | observeco-master-plan.md §3.58 |
||||| **59** | **Composite Health Score (0–100)** — single rolled-up number per agent combining: tool failure rate, anomaly count, token efficiency, pulse uptime, drift stability. Warning <70, Critical <50. Dashboard displays score + trend arrow per agent card. Currently ObserveCo has binary pulse (alive/dead) but no composite health number. This is what buyers compare across agents. Reference: agenttrace health scoring. | **Intelligence** | 🔴 Planned | ✅ Dashboard score + trend arrow | ✅ Push alerts on threshold breach + historical regression + fleet comparison | ~2d | observeco-master-plan.md §3.59 |
||||| **60** | **Anomaly Detection Taxonomy** — beyond up/down crash detection. Categorises: `no_tools` (session ran without tool calls), `high_cost` (cost spike vs baseline), `long_gaps` ( latency between turns), `retry_loops` (repeated tool failures + retries), `context_pressure` (context window approaching limit). Each anomaly surfaced in Anomalies Inbox (§33) with severity + plain-English explanation. ObserveCo circuit breaker catches crashes but not these subtler failure modes. Reference: agenttrace anomaly types. | **Intelligence** | 🔴 Planned | ✅ Anomaly feed in dashboard + severity + explanation | ✅ Push alerts + auto-heal integration + anomaly attribution + resolution tracking | ~3d | observeco-master-plan.md §3.60 |
||||| **61** | **CI Quality Gates** — `observeco gate` CLI command + `--fail-under-health`, `--fail-on-critical`, `--max-tool-fail-rate` flags. Returns exit code 0/1 for CI integration. Generates JSON/HTML report artifact. Turns observability from passive dashboard into active quality gate. Works with GitHub Actions, GitLab CI, Jenkins. Pro: custom gate policies + trend regression detection. Reference: agenttrace CI integration. | **DevOps** | 🔴 Planned | ✅ Basic health/fail-rate gates + JSON report | ✅ Custom gate policies + regression detection + HTML report + CI integration guides | ~2d | observeco-master-plan.md §3.61 |
||||| **62** | **Session Baseline Diffing** — save a snapshot of fleet state (cost, tokens, health, anomalies) as a baseline JSON. Compare subsequent runs against it to detect regressions: "cost up 23% vs baseline, agent X health dropped 15 points." Dashboard shows diff view. ObserveCo has baselines for RSS/p95 but not for session-level agent behaviour. Reference: agenttrace `--baseline` flag. | **Intelligence** | 🔴 Planned | ✅ Save/load baselines + diff view in dashboard | ✅ Automated daily baselines + regression alerts + multi-baseline comparison | ~2d | observeco-master-plan.md §3.62 |
||||| **63** | **Static Report Export** — self-contained HTML/JSON/Markdown report generation. One file, no backend required, shareable with non-technical stakeholders. `observeco report --format html -o report.html`. Includes: fleet summary, cost breakdown, health trends, anomaly list, top sessions. ObserveCo dashboard currently requires server running — this enables offline sharing. Reference: agenttrace `--overview -f html`. | **Dashboard** | 🔴 Planned | ✅ HTML + JSON + Markdown export | ✅ Custom report templates + scheduled email delivery + white-label branding | ~1.5d | observeco-master-plan.md §3.63 |
||
|| **Commercial Strategy Features (2026-06-19)** |
||||| **64** | **`hermes_home()` + `openclaw_home()`** — single source-of-truth functions in `dirs.py` that check `OBSERVECO_HERMES_HOME` env var → `~/.hermes/` → XDG config → `hermes config path` CLI. Same for openclaw. Replaces 13 `~/.hermes` + 7 `~/.openclaw` hardcodes. | **Infrastructure** | 🔴 P0 | ✅ All | ✅ All | ~1h | specs/commercial-strategy-v2.md §3.2 |
||||| **65** | **Lazy path constants** — `config_scanner.py` and other path constants become functions (not module-level) so they honour the env var at call time, not import time. | **Infrastructure** | 🔴 P0 | ✅ All | ✅ All | ~1h | specs/commercial-strategy-v2.md §P0-2 |
||||| **66** | **Generic Hermes discovery** — refactor 13 `~/.hermes` hardcodes → `dirs.hermes_home()` + 7 `~/.openclaw` → `dirs.openclaw_home()`. All path dependencies consolidated in `dirs.py`. | **Infrastructure** | 🔴 P0 | ✅ All | ✅ All | ~2h | specs/commercial-strategy-v2.md §P0-3/4 |
||||| **67** | **Remove personal artifacts** — strip `seanfzc.ics`, `seanfzc_calendar.json`, `"kepler"` special-case, `~/AGENTS.md`/`~/SOUL.md` home-root scan, 4 fake plugins + 3 fake services, `"hound"` default exemption. Ship with zero Sean artifacts. | **Cleanup** | 🔴 P0 | ✅ All | ✅ All | ~1h | specs/commercial-strategy-v2.md §3.3 |
||||| **68** | **Fix `require_pro()`** — currently checks hardcoded 150/month invocation cap instead of `LicenseState.is_pro`. Rewrite to: `return load().is_pro`. Belt-and-suspenders enforcement breaks Pro gating. | **Bugfix** | 🔴 P0 | ✅ All | ✅ All | 5min | specs/commercial-strategy-v2.md §6.1 |
||||| **69** | **Dashboard banner** — "X agent invocations this month" from `COUNT(turn_logs)`. Shows agent invocation count, frames value. Single SQL query + banner div. | **Dashboard** | 🔴 P1 | ✅ All | ✅ All | ~1h | specs/commercial-strategy-v2.md §3.1 |
||||| **70** | **Graceful degradation** — every Hermes-specific feature guards on `hermes_home()` returning `None`: dashboard section shows "Hermes agent: not detected", chisel shows "Install Hermes to use skill compression", etc. No crashes on clean Mac Mini. | **Infrastructure** | 🔴 P1 | ✅ All | ✅ All | ~2h | specs/commercial-strategy-v2.md §3.4 |
||||| **71** | **Generic discovery layer** — `ollama list` scanner → models, `~/.claude/projects/` scanner → Claude Code projects, `psutil` process scanner → running agents, port scanner → running services. Dashboard shows per-framework tag per agent (Hermes / Claude Code / Ollama / Generic). | **Infrastructure** | 🔴 P2 | ✅ All | ✅ All | ~5.5h | specs/commercial-strategy-v2.md §Phase 2 |
||||| **72** | **`observeco init`** — runs discovery, writes `~/.observeco/config.yaml` with found agents, paths, and ports. First-run setup for clean installs. | **CLI** | 🔴 P1 | ✅ All | ✅ All | ~2h | specs/commercial-strategy-v2.md §P1-5 |
||||| **73** | **Env var namespace consolidation** — `OBSERVECO_HERMES_HOME`, `OBSERVECO_OPENCLAW_HOME`, all config env vars documented in `observeco config --help`. | **Infrastructure** | 🔴 P1 | ✅ All | ✅ All | ~1h | specs/commercial-strategy-v2.md §P1-3/4 |
| **74** | **Fix `require_pro()`** — should return `load().is_pro`. | **Bugfix** | 🟢 Done (verified 2026-07-12) — `license.py:1018` already `return True` (beachhead stub). No change needed. | — | — | 0 | specs/commercial-strategy-v2.md §P0-10 |
| **75** | **Delete `invocation_counter.py`** — dead 5/day cap code. | **Cleanup** | 🟢 Done (verified 2026-07-12) — file does not exist in tree; banner uses `COUNT(turn_logs)`. No change needed. | — | — | 0 | specs/commercial-strategy-v2.md §P0-11 |
| **76** | **BYOK for LLM features** — `OBSERVECO_LLM_API_KEY` detection + `gate.py:should_call()` key check. | **AI** | 🟢 Done (verified 2026-07-12) — `gate.py:95-97` already returns `False` when key absent; `_detect_llm_providers` already detects the key. No change needed. | — | — | 0 | specs/commercial-strategy-v2.md §P0-12 |
| **77** | **BYOK for Chisel LLM** — `chisel/llm_client.py:get_api_key()` key detection. | **AI** | 🟢 Done (verified 2026-07-12) — `llm_client.py:100` already reads `OBSERVECO_LLM_API_KEY`. No change needed. | — | — | 0 | specs/commercial-strategy-v2.md §P0-13 |
| **78** | **Fix `gateway_monitor.py` constants** — use `dirs.hermes_home()`/`dirs.openclaw_home()`. | **Infrastructure** | 🟢 Done (verified 2026-07-12) — `gateway_monitor.py:44-52` already imports from `hermes_home()`/`openclaw_home()`. No change needed. | — | — | 0 | specs/commercial-strategy-v2.md §P0-14 |
| **78b** | **Fix `dashboard/otel.py` `/v1/traces`** — `log_trim()` called with wrong kwarg names (`identity_tokens` etc.) → 500 on any OTEL span. Secondary ingestion path (Hermes uses standalone `:4318` listener). | **Bugfix** | 🟢 Fixed (2026-07-12) — corrected kwargs to `log_trim(identity=, skills=, memory=, tools=, guidance=, total=, savings=)`. Route now non-500. | — | — | ~10min | — |
||| **79** | **`observeco discover`** — dashboard widget that scans cron jobs, agent configs, and running processes for gaps vs what's tracked. Shows gaps with **Add** buttons — one click registers the agent and starts monitoring. No CLI, no read-only report. | **Dashboard** | 🟢 Built (2026-07-12) — `discover/scanner.py` (cron+config+process scans, 5min cache) + `discover/api.py` (`/api/discover/gaps`, `/panel`, `/add`) + htmx badge+panel in `index_new.html` + CSS. 3/3 tests pass. Verified live: 104 real gaps, Add registers agent. | — (all shipped) | ✅ All | ~3h | observeco-master-plan.md §3.64 |
|||| **80** | **Conversational Dashboard Copilot** — natural language control of the ObserveCo dashboard via Page Agent. FAB trigger + Cmd+Shift+K, Page Agent built-in panel themed to ObserveCo dark tokens. | **Dashboard** | ✅ Live — FAB + panel | ✅ All (one script tag, no backend changes) | ✅ Same | 1h | observeco-master-plan.md §3.65 |
|81 | Incident Skill Auto-Creation (L3 Learning Loop) — after successful heal of a novel failure, LLM extracts the failure pattern and writes a prevention SKILL.md. Next occurrence → known fix applied via FTS5 match, skipping LLM diagnosis (zero LLM cost). System gets cheaper as it learns your failure modes. | **Self-Heal + AI** | 🟢 Built (2026-07-12) — MVP: `prevention_skills`+FTS5 schema, `heal/prevention.py` (extract/check/write/apply/deprecate), L3 check-first + learn-after wired into `run_heal` (gated by `heal_config.learn`), CLI `observeco prevention list/show/remove/enable/disable`. Dangerous remediations (pip_install/code_fix) never auto-run. 6/6 tests pass; prod E2E verified. Dashboard UI + cross-fleet = deferred (Pro). | ✅ Same + dashboard UI + cross-fleet sharing + promotion gating | ~2d (est) → ~1d actual (MVP scope) | obs-spec-081-incident-skill-auto-creation.md |
| **82** | **Session Efficiency Scoring** — 11 context-efficiency metrics (redundant reads, read amplification, retry waste, edit thrash, etc.) per session. Task archetype classification (research/debug/feature/ops/edit). Two-axis scoring: efficiency + effectiveness (did it ship?). One-click optimize memory wrote back to AGENTS.md. Custom rule packs. Per-archetype baselines. Token-based metrics (context-pressure, cache-hit, yield-density) now LIVE via #83 session_id join. | **Analysis** | 🟢 Phase 1+2+3 Built + token metrics live (2026-07-12) — full 11-metric scoring active on :8899, 9/9 tests pass. | — (all shipped) | ~700 lines (7 files) | obs-spec-062-session-efficiency-scoring.md |
| **83** | **Token-Log Session Attribution** — populate `token_logs.session_id` (empty across 507K rows) so #82's 3 token metrics (context-pressure, cache-hit, yield-density) can join sessions. Hermes `observability/otel` plugin emits `hermes.session_id` per LLM-call span; ObserveCo's `otel_listener.py` now captures it + `log_token_turn()` stores it + `compute_efficiency()` feeds the 3 metrics. No Hermes change, no migration. | **Analysis** | 🟢 Built (2026-07-12) — listener captures `hermes.session_id`, token metrics live on :8899 (verified: injected test span → context-pressure/cache-hit/yield-density all scored from real token_logs join). 9/9 tests pass. | — (all shipped) | ~70 lines (4 files) | obs-spec-083-token-session-attribution.md |
|||
||---|
|
## 3. Feature Deep Dives

### 3.1 Fleet View (✅ Type grouping live — flat grid remains until drill-downs built)

**Tagline:** *See every agent in one place — alive, broken, or hiding.*

**What it is:** A dashboard screen with agent cards in a single flat grid grouped by **type** (Agents · Services · Workflows), not by framework. Each card shows the entity's status, last check, and type-appropriate metrics.

> ⚠️ **Features marked NOT BUILT are spec'd only** — see kanban tasks for build priority.
> - Drill-down modals (pulse timeline, guard failure history, annotated error timeline)

**Now live:** Type-based grouping in collapsible sections, show/hide × buttons, missing-agent feedback bar, 5-clickable metric rows per card (Health/Guard/Errors/Brain size/Composition), and full 5-tab drill-down modal (Health/Guard/Errors/Tokens/Memory). Composition row shows inline token bar without redundant "See details" link (brain size row has the link). All fleet view components shipped.

**How auto-discovery works (live):** The system discovers entities automatically, classifying them by type:

| Type | Example | Source | Metrics shown |
|------|---------|--------|---------------|
| **Agent** | Dreamer, Kepler | Hermes profiles, OpenClaw config, `observeco agent add` | Pulse, tokens, drift, memory |
| **Service** | Hound heartbeat, PA sweep | launchd plists, daemon processes | Pulse, uptime, failure count |
| **Workflow** | Signal synthesis, News digest | Cron manifests | Last run, next run, success/fail rate |
| ❌ Config key | `allowed_chats`, `api_keys` | **Filtered out** — no agent metadata | Nothing |

**Config key filter:** Auto-discovery must filter to entries with valid agent metadata (health_check, config_path, or SOUL.md path). Config key sections from Hermes `config.yaml` are never promoted as agents.

**Framework labels in fleet view:** Each agent card shows framework as secondary metadata after type: `Kepler · Agent · OpenClaw`. Framework is auto-detected from config source (Hermes profile dir, OpenClaw workspace, Ollama config, explicit `--framework` flag, or inferred from config path). It must render correctly for ANY framework value, not just known ones.

**Implementation rules:**
- Cards display: `{name} · {type} · {framework}` or just `{name} · {type}` when framework is `custom`/unknown
- Detail modal framework section: always shows the actual framework value (never hardcodes to "Hermes" or "OpenClaw")
- Default framework when unknown: pass through the raw DB value or show a generic label — never default to "Hermes"
- Framework dropdown for `agent add`: options are "Agent" (default), "Service", "Workflow" — framework is set separately as optional metadata
- CLI commands: primary names reflect the interface (`observeco chisel compress`, `observeco chisel skills`), with generic aliases planned for future releases (`observeco context trim`)

**Show/hide per agent (NOT BUILT — mocked only):** Click the × button on any card to hide it. (Note: not implemented — all agents shown always.)

**"Missing an agent?" feedback button (NOT BUILT — mocked only):** A built-in input in the dashboard header. (Note: not implemented.)

**What this means for you:** Instead of running `ps aux | grep hound` or asking "is Kepler alive?", you look at one screen. Green dots mean everything is fine. Red dots need attention — and you can see *what kind* of attention (dead? bloated? slow?) without opening a terminal.

**Free:** Full fleet view (flat grid), unlimited agents, status dots, token bars, drift sparklines, error badges.
**Pro:** Same (Pro unlocks push alerts, auto-heal, never-pruned history — not per-agent viewing controls).

**Onboarding flow (first-run):** See `specs/unified-dashboard.md §8` for the 3-phase progressive loading spec. **Not yet implemented in dashboard code.**

**Empty state guidance — every section follows this pattern:**
| What's missing | Why | When it will appear | What to do if it doesn't |
|---------------|-----|-------------------|--------------------------|
| Probe data | Agent not yet checked | After first pulse tick (~30s) | Run `observeco pulse check` |
| Token breakdown | Agent hasn't been used in a session yet | After first agent interaction | Check agent is running and active |
| Restart quality | No restart events recorded | After Heal button is pressed or auto-heal fires | Keep agent running normally |
| Error timeline | No errors detected | Immediately (empty = good) | ✅ "No errors — good sign!" already correct |

> ⚠️ Type-based grouping, show/hide × buttons, missing-agent feedback button, and 5 clickable metric drill-downs are mocked in fleet-dashboard.html but not yet built. See kanban tasks for build priority.
**Mockup:** `mockups/fleet-dashboard.html`

### 3.2 Pulse Check (✅ Live)

**Tagline:** *Every 30 seconds, someone knocks on each agent's door. If nobody answers, you know.*

**What it is:** The heartbeat of the entire system. Every 30 seconds, the watch daemon tries to reach every registered agent — by hitting its health URL, running a shell command, or checking if its process is alive. The result (alive / dead / error) goes straight into the database and shows up on the Fleet View cards.

**How it works under the hood:**

```
Every 30s → for each agent:
  1. Has a health URL? → HTTP GET (timeout 10s)
  2. Has a health command? → shell it (timeout 10s)
  3. No checks configured? → pgrep -f agent_name
  4. If dead → record failure + check if guard should trip
  5. Write result (status, latency, error message) → SQLite
```

**What the human sees (live):**

- **On the Fleet View card:** Status dot (🟢 alive / 🔴 dead / 🟡 error) shown inline. Card click opens inline agent detail tab with Health/Tokens/Memory sections, not a drill-down modal.

|- **5 clickable metric rows (Health/Guard/Errors/Brain size/Composition)** with "See details ›" labels. All rows are wired to live backend endpoints via `loadTab()`.
  - **Click Health →** drill-down modal opens with 4 sections:
    1. **Pulse timeline** — Up to 48 colour-coded dots (24 hours). Green = OK, yellow = warning, red = error. Legend included.
    2. **Annotated timeline** — Table: Time | Status | What happened. Each error row shows severity icon + label + message.
    3. **Categorized Summary** — The system categorises errors into 5 types (timeout, connection refused, resource not found, HTTP 5xx, other) and provides plain-English explanations + verdict.
    4. **Latest check** — Table: Time | Result | Latency.
  - **Click Guard →** drill-down modal opens with 4 sections:
    1. **Status** — "🔴 Guard is STOPPED" or "✅ Guard is OK" with explanation.
    2. **Failure timeline** — Table of errors that triggered the guard + plain-English summary.
    3. **What the guard does** — Explanation of 3-failure trip, cooldown, auto-retry.
    4. **Settings** — Failures before stop, cooldown period, auto-retry status.
  - **Click Errors →** drill-down modal opens with 3 sections:
    1. **Error timeline** — Table: Time | What happened, severity-colored.
    2. **What this means** — Plain-English verdict (0 errors = clean, 1 = transient, 2+ = ongoing problem).
    3. **Pro upsell** — Preview card showing what longer history unlocks.

**Why this is better than coloured dots:** Coloured dots tell you *when*. The annotated timeline and summary tell you *why* — "timed out" vs "dependency not found" vs "HTTP 500" each point to different root causes and different fixes. Without this, you see red and guess.

**What the human might miss (but should know):**

| Scenario | What happens | What pulse check shows |
|----------|-------------|----------------------|
| Agent process crashed | pgrep returns nothing | 🔴 Down — "no matching process" |
| Agent is running but hung | HTTP endpoint times out | 🔴 Down — "timeout after 10s" |
| Agent is running but returning errors | HTTP 500 | 🟡 Warning — "HTTP 500" |
| Health endpoint is unreachable | Connection refused | 🔴 Down — "connection refused" |
| Everything is fine | HTTP 200 or exit code 0 | 🟢 Alive — sub-second response |

**How pulse check talks to the rest of the product:**

| Consumed by | What it uses pulse data for |
|------------|---------------------------|
| **Fleet View** (Health row) | Shows the latest status dot and last check-in time |
| **Safety Guard** (next feature) | Tracks consecutive failures — trips after 3 to stop hammering |
| **Error history** | Logs every failure as an error entry with the raw message |
| **Heal button** | Reads pulse status to decide if a restart is needed |
| **Auto-heal (Pro)** | Same as heal button but fires automatically |
| **Push alerts (Pro)** | Sends Telegram / email when pulse goes from alive → dead |

**What this means for you:** Without pulse check, you find out an agent is dead when it doesn't respond to your message — minutes or hours later. With pulse check, you know within 30 seconds. And with the drill-down, you don't just see "it's down" — you see *why* ("connection refused" vs "timeout" vs "HTTP 500" tell you different things to do).

**Free:** Automatic every 30s via watch daemon, full drill-down in Fleet View.
**Pro:** Same (Pro unlocks auto-heal and push alerts, not pulse checking itself — pulse is the foundation everything else depends on).
**API endpoint:** `GET /health` or shell command — whichever each agent provides.

### 3.3 Safety Guard (✅ Live)

**Tagline:** *After 3 failures, the guard stops knocking. Silence until cooldown ends.*

**What it is:** A noise filter. Without it, a dead agent gets checked every 30 seconds — generating error messages, filling your logs, wasting resources. After 3 consecutive failures, the guard trips. It stops checking that agent and enters cooldown (~4 hours). After cooldown, it tries again automatically.

**How it works under the hood:**

```
Pulse detects failure → record_failure() increments counter
→ failures < 3?     Keep monitoring (every 30s)
→ failures >= 3?    Trip guard, enter cooldown
                    Stop probing for ~4 hours
                    When cooldown expires, try one probe
                    → Success? Reset counter, resume normal monitoring
                    → Failure? Re-enter cooldown
```

**What the human sees:**

- **On the Fleet View card:** The **Guard** row shows "✅ Guard OK" (green) or "🔴 Stopped (failed 3x)" (red). Hover shows "See details ›" — click it.

- **Click Guard →** drill-down modal opens with 4 sections:

  1. **Status** — Current state:
     - "🔴 Guard is STOPPED — not checking this agent" if tripped
     - "✅ Guard is OK — monitoring normally" if not
  2. **Failures that triggered the guard** — The annotated failure history showing exactly what went wrong and when:
  
  | Time | | What happened |
  |------|---|---------------|
  | 09:37 | 🔴 | Pulse timeout after 10s — connection refused |
  | 09:34 | 🔴 | Pulse timeout after 10s — connection refused |
  | 09:31 | 🔴 | Health endpoint returned 500 |
  | 09:28 | 🔴 | Agent process not found (pgrep) |
  
  With a summary in plain English: "The guard triggered after 3 consecutive failures. In total, 4 errors were logged before it stopped checking."
  
  3. **What the guard does** — Plain English explanation of why it exists and how it prevents alert fatigue.
  
  4. **Settings** — Configuration table:
  | | |
  |---|---|
  | Failures before stop | 3 |
  | Cooldown period | ~4 hours (active/ready) |
  | Auto-retry after cooldown | Yes |

**What the human might miss (but should know):**

| Scenario | What happens | What the guard shows |
|----------|-------------|---------------------|
| Agent crashed, quickly restarted | 1-2 failures, guard doesn't trip | "✅ Guard OK — 0 consecutive failures" |
| Agent crashed, stays dead | 3+ failures, guard trips | "🔴 Stopped (failed 3x)" with failure log |
| Agent recovered during cooldown | Cooldown expires, probe succeeds | Guard resets automatically |
| Agent recovered, then crashed again | New failure streak starts from 0 | Guard counts fresh 3 failures independently |

**How the guard talks to the rest of the product:**

| Consumed by | What it uses guard data for |
|------------|---------------------------|
| **Fleet View** (Guard row) | Shows "✅ Guard OK" or "🔴 Stopped" |
| **Heal button** | Before attempting restart, checks if guard is tripped — if yes, warns "guard is in cooldown" |
| **Push alerts (Pro)** | Fires Telegram notification when guard trips |
| **Auto-heal (Pro)** | Bypasses guard cooldown for configured agents |

**Value calculation — what the guard saved you from:**

Pulse probes are HTTP requests, not LLM calls — they spend zero tokens. But each failure writes **two rows** to SQLite (`pulse_log` + `errors`), and those accumulate. Here's the math for a single agent that goes down:

| Metric | Without guard | With guard |
|--------|--------------|------------|
| **HTTP checks per day** | 2,880 (every 30s × 24h) | ~8 (3 to trip + 1 per 4h cooldown × 5 cycles max) |
| **DB writes per day** | 5,760 (2 per check × 2,880 checks) | ~16 (2 per check × 8 checks) |
| **DB growth per day** | ~432 KB | ~1.2 KB |
| **DB growth per year** | ~158 MB | ~438 KB |
| **Reduction** | — | **99.7% fewer checks** |

That 2nd metric — **DB writes per day** — is the real cost. Each write to `pulse_log` is ~70 bytes (agent_name + status + latency + error_message + timestamp). Each write to `errors` is ~80 bytes (agent_name + error_type + severity + message + timestamp). Two writes per probe, every 30 seconds, forever until you notice and restart the agent.

In practice:
- **Without guard:** 5,760 SQLite INSERTs per dead-agent-day. That's 1.05M rows/year per dead agent piling up in your pulse_log and errors tables. Every dashboard load, every heal diagnosis query (`get_recent_pulses(agent, 5)`), every error-history panel reads through that growing table.
- **With guard:** ~16 INSERTs per dead-agent-day. The table stays at ~2,920 rows/year instead of 1,051,200.

In plain English: if Kepler goes down at midnight and stays down all day, without the guard your SQLite DB grows by **432 KB** by morning from pulse noise alone — your dashboard is red, your DB is bloated, and every query across the errors table has 2,880 more rows to scan. With the guard, you see **3 errors** (the failures that triggered the trip) followed by silence. Your DB grows by **1.2 KB**. You know it went down at midnight, you know why, and you're not accumulating 432 KB of dead weight every day you're not watching.

For your fleet of 12 agents, if 2 are down simultaneously:
- **Without guard:** 11,520 DB writes = ~864 KB/day
- **With guard:** ~32 writes = ~2.4 KB/day
- That's your DB staying lean vs. accumulating 5 GB/year of noise.

The guard doesn't just reduce noise — it preserves the **signal** by making sure every error you see is a meaningful event, not a repeat — and keeps your SQLite lean so it doesn't slow down over time.

**Free:** Automatic detection, auto-cooldown, full drill-down in Fleet View.
**Pro:** Configurable thresholds (change 3 failures to N) + auto-recovery timer (change cooldown period).

### 3.4 Brain Analysis (✅ Live — Sections 1-3 built, Section 4 Pro-teaser mockup)

**Tagline:** *See what feeds your agents. See what you can save.*

**What it is:** A unified page that merges observation (token composition, drift, usage timeline) with action (compression preview/apply, auto-watch, token optimiser). The default view shows the fleet total across all agents so dollar savings are meaningful. Switching to a single agent shows per-agent granularity.

**Status:** Seven sections rendered in the Brain tab:
- **Section 1 — Token Breakdown (✅ Live):** Per-component bars (identity/skills/memory/tools/guidance) sorted by size, component explanations
- **Section 2 — Savings Comparison (✅ Live):** 3-bar chart (Original/Lite/Full), provider cost dropdown, 4 summary boxes, Pro upsell
- **Section 3 — Compression (✅ Live):** Manual tab with Lite/Full toggle, before/after diff preview, Apply/Copy Diff actions. Backend: `/api/chisel/compress` POST endpoint, `observeco chisel compress --agent <name> --mode lite|full` CLI. Lite compresses guidance (replacements: MUST→must, should→should, dedup identical rules). Full additionally culls memory sections to active content + deduplicates skills. Backup auto-created at `.md.bak`.
- **Section 4 — Token Optimiser (✅ Live with demo data):** Learning progress bar, projected savings. Backend: `/api/optimiser/stats` endpoint queries `turn_log`, `skill_usage`, `guidance_fire`, `compress_log` tables. Real data populates as agents accumulate turns (goal: 200).
- **Section 5 — Drift & Usage (✅ Live):** 7-day component drift SVGs + 24-column per-turn timeline
- **Section 6 — Auto-Compression Daemon (✅ Live):** `chisel watch start/stop/status` CLI commands. Monitors SOUL.md files for modifications, auto-compresses, logs to `compress_log`. Heartbeat file at `~/.observeco/.chisel_watch_heartbeat.json`.
- **Bottom tier summary (✅ Live):** Free vs Pro comparison table

**Mockup:** `mockups/brain-analysis.html`
**Obsoletes:** `mockups/token-breakdown.html`, `mockups/chisel-compress.html` (to be removed when brain-analysis is implemented)

---

**Section 1 — Token Breakdown (same as free composition view)**

Each agent's system prompt (SOUL.md) classified into 5 components — identity, skills, memory, tools, guidance — shown as horizontal bars plus an explanation column.

- **Default view:** Fleet total across all registered agents (e.g. "44,700 total across 6 agents")
- **Dropdown:** "All Agents (fleet total)" is the default; per-agent options available
- Each bar shows token count and percentage
- Right column explains what each component IS: skills = task instructions, tools = functions/APIs, memory = user context, guidance = behavioural rules, identity = role/personality

**Free:** Included.

---

**Section 2 — Savings Comparison (3-bar chart with $ conversion)**

Compares Original vs CHISEL Lite (Free) vs CHISEL Full (Pro) side by side:

```
Original  ████████████████████████████████  4,200 tok
Lite      ████████████████████████▌          3,276 tok  (-22%) → $0.02/day
Full      ████████████████████               2,730 tok  (-35%) → $0.03/day
```

Features:
- **Provider cost dropdown** — configurable to match the user's actual provider:
  - DeepSeek v4 Flash ($0.15/M input)
  - Ollama Pro ($0.15/M input)
  - Zhipu ($0.10/M input)
  - Ollama Local (FREE — no API cost)
  - Custom (freeform $/M input)
- **$ savings update in real-time** as provider or agent selection changes
- **4 summary boxes:** Lite saves/turn (%), Full saves/turn (%), Tokens saved/day, Dollars saved/day
- **Pro upsell banner below:** "Full compression saves $0.83/day vs Lite's $0.52 — that's $113/year extra"

**Dollar math:** `(raw_tokens - compressed_tokens) × 50 turns/day × provider_rate / 1,000,000`

When provider is set to "FREE (local)", dollar values show "FREE" instead of numbers.

**Free:** Lite compression bar + per-agent $ savings.
**Pro:** Full compression bar + fleet $ savings (meaningful numbers).

---

**Section 3 — Compression: Manual vs Automatic**

A two-tab toggle makes the workflow clear:

**🛠️ Manual tab (Free + Pro):** "Preview & Apply"

| Step | Action | What happens |
|------|--------|-------------|
| 1 | ▶️ Run Preview | See the diff side-by-side. No file modified. Lite vs Full toggle changes the preview. |
| 2 | 💾 Apply to File | Writes compressed version to agent's SOUL.md. Backup auto-created. |
| — | 📋 Copy Diff | Copies the diff report to clipboard. |

- **Lite (Free) vs Full (Pro)** toggle changes the preview and the mode tag
- Lite: compress guidance blocks (22% savings)
- Full: +memory culling +skill dedup +context refactor (35% savings)

**🤖 Auto tab (Pro, locked):** "Watch Daemon"

Every time SOUL.md is edited, the watch daemon detects the change and runs compression automatically. Shows a live log preview:

```
18:32  hound SOUL.md modified — auto-compressing...
18:32  ✅ 4,200 → 3,276 tok (-22%)
18:32  Backup: hound.SOUL.md.bak.20260526
18:33  dreamer SOUL.md modified — auto-compressing...
18:33  Full compress: 3,800 → 2,470 tok (-35%)
────────────────────────────────────
📊 Cumulative fleet savings this week: 47,812 tokens saved
```

**Free:** Manual Preview + Apply (up to Lite mode).
**Pro:** Full mode in Manual + Auto-Watch daemon.

---

**Section 4 — Token Optimiser (Pro)**

A learning engine that goes beyond rule-based compression. After enough turns of data, it identifies what an agent actually uses vs what's dead weight.

**Learning progress:**

```
████████████░░░░░░░  58% — learned from 116 turns (goal: 200)
```

- Tracks which skills are actually triggered in conversation
- Identifies guidance rules that never fire
- Detects memory sections that grow but are never referenced
- After reaching 200 turns of data, produces a pruning recommendation

**Projected savings tiers:**

| Tier | Savings | Method |
|------|---------|--------|
| Lite (Free) | -22% | Rule-based guidance compression |
| Full (Pro) | -35% | Deeper rewrite across all components |
| **Lite + Optimiser** | **-43% to -47%** | Compression + learned pruning |

At 50 turns/day, enough data is collected in ~2 days.

**Optimiser findings example:**
- 3 of 8 skills never triggered → candidates for removal
- 2 of 5 guidance rules stale → candidates for archival
- Memory sections unused → insufficient data (needs more turns)

**Free:** Not included.
**Pro:** Included with Full compression. Recommendations become available after the agent reaches 200 turns of tracked data.

---

**Section 5 — Drift & Usage (same as §3.5)**

- 7-day component drift sparklines (SVG with area fill)
- 24-column per-turn token timeline
- Pro upgrade prompt: never-pruned history + fleet-wide comparison

---

**Bottom tier summary:**

| 🔓 FREE | 🔒 PRO ($9/mo Solo · $49/mo Team) |
|---------|-----------------------------------|
| CHISEL Lite: 22% savings/turn | CHISEL Full + Optimiser: up to 47% savings |
| Per-agent breakdown & drift | Full compression (memory + skills + context) |
| 24h per-turn timeline | Auto-Watch daemon |
| 7-day component trends | Token Optimiser (learns from 200 turns) |
| | Never-pruned history & fleet comparison |
| | Cumulative fleet savings dashboard |

**Mockup:** `mockups/brain-analysis.html`
**Obsoletes:** `mockups/token-breakdown.html`, `mockups/chisel-compress.html` (to be removed when brain-analysis is implemented)

### 3.5 Drift Analysis v2 (✅ Live — 2026-07-10)

**Tagline:** *See which agents are growing — and whether it's a real problem or a math artifact.*

**What it is:** A time-series view of token composition drift per agent, showing trajectory (sparkline), peak drift, current drift, and breach count. Differentiates from the Compare tab (current snapshot) by showing how drift evolved over time.

**Status:** ✅ Live — v2 with Chart.js sparklines, HTML tooltips, real date labels, per-agent most-drifted-component selection.

**Known issues (v2):**

1. **Window bug** — `watch_consumers.py` uses `get_trims(limit=50)` which caps the 7-day window to the last 50 entries. For fast-sampled agents (accelerator, hermes, skeptical: every 30s), 50 entries = 25 minutes. For slow-sampled agents (archive, kanban: every 4-5h), 50 entries = 10+ days. The `week_ago` filter is applied after the cap, so it's ineffective for fast agents. **Fix:** Replace `limit=50` with a proper time-based query (`WHERE timestamp > week_ago`).

2. **Denominator amplification** — `delta_pct = (current - week_avg) / week_avg * 100` produces misleadingly large percentages when `week_avg` is near zero (e.g., hermes identity: 1→344 tokens = +4814% because week_avg=7). **Fix:** Apply a floor of 50 tokens to the denominator.

3. **Rolling window healing artifact** — A permanent one-time change (e.g., subconscious guidance 103→172) shows as a spike that "heals" over 7 days as the old data ages out. The metric returns to 0% while the agent is permanently larger. **Fix:** Add week-over-week comparison (Option B) alongside the rolling window (Option A).

**Normalization strategy (three methods, all displayed):**

**Option A — Rolling window with floor (trajectory):**
```
delta_tokens = current - week_avg
delta_pct    = (current - week_avg) / max(week_avg, 50) * 100
breach       = abs(delta_tokens) > 50 AND abs(delta_pct) > 10%
```
- Measures: "How different is today from the 7-day rolling average?"
- Best for: detecting sudden changes (restarts, config edits, one-time bloat)
- Shows: spike → decay as window catches up

**Option B — Week-over-week (sustained growth):**
```
this_week_avg  = average of last 7 days of trim data
last_week_avg  = average of 7-14 days ago
delta_pct      = (this_week_avg - last_week_avg) / max(last_week_avg, 50) * 100
breach         = abs(this_week_avg - last_week_avg) > 50 AND abs(delta_pct) > 10%
```
- Measures: "Is the agent's brain permanently larger than last week?"
- Best for: detecting sustained growth (compounding cost problems)
- Shows: step change → stays flagged until next week

**Option C — Absolute tokens (raw delta, no percentage):**
```
delta_tokens = current - week_avg
breach       = abs(delta_tokens) > 50
```
- Measures: "How many more tokens is this agent using today vs its 7-day average?"
- Best for: honest cost visibility — a 50-token increase costs the same regardless of baseline
- Shows: raw token growth, no denominator artifacts, no math tricks
- No percentage at all — the most transparent metric

**Dashboard display:**
- Drift tab shows Option A sparkline (trajectory) as the primary view
- Option B shown as secondary stat: "Week-over-week: +X.X%"
- Option C shown as secondary stat: "Δ tokens: +X"
- All three use the same time-based query (fix the window bug first)
- All three use the same 50-token absolute floor for breach detection

**Implementation plan:**
1. Fix window bug: replace `get_trims(limit=50)` with `get_trims_since(agent, week_ago)` using a time-based query
2. Add 50-token floor to `delta_pct` computation in both `watch_consumers.py` and `chisel/drift.py`
3. Add Option B computation: query trims from 7-14 days ago, compute week-over-week delta
4. Add Option C computation: raw absolute token delta (no percentage)
5. Store all three in `chisel_drift` table (add `method` column: `rolling` / `wow` / `absolute`)
6. Update dashboard Drift tab to show all three metrics per agent row
7. Update `obs-spec-052-drift-detection.md` with the new normalization spec

**Free:** Both Option A and Option B, full Drift tab with sparklines.
**Pro:** Same (no gating — drift is a core diagnostic).

### 3.6 Error History (✅ Live)

**Tagline:** *Every error, annotated. Not just a log line — context that tells you whether to worry.*

**What it is:** A per-agent error log showing every error with timestamp, message, and severity. The modal provides plain-English interpretation so you know if any given error needs action or is noise.

**How it works:** The Pulse system (`run_check`) writes failures to the `errors` table: `(agent_name, error_type, error_message, severity, timestamp)`. Errors come from pulse probes that return `status='dead'` or `status='error'`, plus circuit breaker trips.

```python
# src/observeco/db.py:408
log_error(agent_name, error_type, error_message, severity)
# severity levels: info, warning, error, critical
```

The `get_errors(agent_name, limit=N)` query reads from the same table, ordered by timestamp descending.

**What the human sees:**

- **On the Fleet View card:** The **Errors** row shows a badge:
  - "None" (grey) — no errors in the current window. **Empty state guidance:** If this agent hasn't been probed yet (no pulse data at all), show: "No probe data yet — run `observeco pulse check` to start monitoring."
  - "3 in last 24h" (amber badge with `!` icon) — errors exist
  - The count is the number of error rows for that agent in the time window

- **Click Errors →** drill-down modal opens with two sections:

  1. **Error timeline** — A table with:
  
  | Time | What happened |
  |------|---------------|
  | 09:32 | 🟡 Build failed — spec mismatch on output format |
  | 09:14 | 🟡 Build timed out after 30s |
  | 08:45 | 🔴 Dependency "requests" not found |

  Each entry shows the raw error message from the pulse probe. Severity is color-coded:
  - 🔴 (red) — timeouts, connection refusals, process-not-found
  - 🟡 (amber) — build failures, transient errors

  2. **What this means** — Plain English verdict:

  | Error count | Verdict |
  |-------------|---------|
  | 0 | "No errors means this agent has been running cleanly for the last 24 hours." |
  | 1 | "One error in 24 hours is usually transient — network hiccup or temporary overload." |
  | 2+ | "Multiple errors suggest an ongoing problem. Check the guard status to see if monitoring has been stopped automatically." |

**Edge cases:**

| Scenario | What the human sees |
|----------|-------------------|
| Agent running cleanly | "None" with no badge |
| Single transient error | "1 error" with amber badge — verdict says likely temporary |
| Guard-tripped agent | Multiple errors with red badge — verdict points to guard status |
| Agent with no heartbeats | No errors table means no probe data, not "no errors" — distinct empty state |

**Value calculation — what 90-day history actually means for new vs existing users:**

Data starts accumulating the **moment you install ObserveCo and run `observeco pulse check`**. There is no backfill from Hermes/OpenClaw agent logs — the watch daemon generates all pulse data from scratch.

This means:
- **Day 1 user:** 90d history is empty. But **regression detection starts being useful at week 2** — once you have two weeks of data to compare.
- **Month 3 user:** Full 90d trend — degradation, seasonal patterns, post-update regressions.

The Pro teaser for new users shouldn't pretend they have 90 days. It should sell the **trend engine, not the bucket size**:

> *"Data starts today. After 2 weeks, Pro's regression engine spots your agent getting worse before you notice it."*

**Free:** Last 24 hours of errors per agent.
**Pro:** Full history from day of installation onward (never pruned) + weekly trend charts + regression detection (alerts when error rate doubles week-over-week).
**Mockup:** `mockups/fleet-dashboard.html` (Errors drill-down modal)

### 3.7 Heal Button (✅ Live)

| | |
|---|---|
| **What** | Manual trigger — diagnoses dead agent, attempts restart, writes critical flags on failure |
| **How it works** | `src/observeco/heal/__init__.py` → inline HealCircuit ring buffer, snapshot-before-heal, LLM escalation fallback — no external circuit breaker dependency |
| **Free** | Manual button in dashboard |
| **Pro** | Auto-trigger on dead detection (per-feature §15) |
| **Mockup** | `mockups/auto-heal.html` |

**Implementation pattern — HealProposal (read-only diagnosis, explicit execution):** `_diagnose_agent()` returns a proposal dict (`{diagnosis, action, action_args, message}`) without side effects. `run_heal()` presents proposals to the loop; only `_execute_action()` mutates system state. This means:
- `_diagnose_agent()` is safe to call anywhere — dashboard, pulse watch, cron, a dry-run mode
- Heal actions never happen without an explicit execution step
- A future auto-heal can chain: diagnose → check HealCircuit → if safe, execute

**HealCircuit — in-memory ring buffer, not a separate subsystem:** The heal module maintains `HEAL_CIRCUIT = {}` — a per-agent dict with `{failures, cooldown_until}`. No separate circuit breaker DB table. No 3-failure trip to an external system. Simple: 3 consecutive heal failures → 4h cooldown, enforced in-memory. On process restart, HealCircuit resets (no stale cooldowns surviving a restart). This is intentional — the heal circuit is a crash-loop guard, not a persistent state machine. (ponytail: in-memory means a heal daemon restart resets all cooldowns. If this causes too many restarts-on-restart, migrate to a cooldown stamp file in `~/.observeco/heal_cooldowns/`.)

**Auto-restart opt-in (see §3.15 Auto-Heal for details):** Separate feature. Auto-restart only applies to known-safe crash patterns (process dead, memory leak, TOCTOU loop). Never auto-runs `pip_install` or `code_fix`. Controlled by a config section `auto_heal.restart_patterns` — empty list = disabled. When enabled, the watch daemon can call `_execute_action("restart", ...)` directly for known-safe patterns without human/LLM confirmation.

### 3.8 In-Dashboard Alerts (✅ Live)

**The value driver:** Free alerts show **what** happened and **when you discovered it**. The gap between event and discovery is visible — it becomes the reason to upgrade to push.

**What it is:** Circuit trips, drift breaches, and heartbeat misses displayed in the dashboard UI. Free tier shows alerts with a **discovery gap badge**:

> *"hermes-triage circuit tripped — happened 03:15 · You discovered 07:00 (when you opened dashboard) — 3h 45m gap"*

This makes the cost of "pull-based alerting" tangible. Every time the user opens the dashboard, they see exactly how much time passed before they knew about each event.

**The cumulative gap:** A banner at the top of the alert feed totals the undiscovered downtime:

> *"8h 47m total undiscovered downtime across 4 alerts in the last 24h"*

This number grows the longer the user goes between dashboard visits — directly motivating the push upgrade.

**Free:** Visible in dashboard only — alerts show with discovery gap badges and cumulative delay summary.
**Pro:** Push delivery (per-feature 3.17) — zero gap, notification within 3 seconds.

### 3.9 Memory Garden (✅ Live — Fleet Summary + Per-Agent)

| | |
|---|---|
| **Fleet summary** (Brain Analysis tab) | ✅ `/api/garden-summary` — agents_scanned, total_duplicates, total_contradictions, total_stale, avg_debt_score, fleet_grade |
| **Per-agent detail** (agent card modal) | ✅ `?tab=garden` on `/api/agent-detail/{name}` — score, grade, dupe/contradiction/stale counts |
| **CLI scan** | ✅ `clawforge garden` command |
| **Data source** | `clawforge_garden` table in pulse.db |

| | |
|---|---|
| **What** | Scans OpenClaw MEMORY.md for duplicates, contradictions, stale entries. Reports debt score (0-100). |
| **How it works** | `src/observeco/clawforge/garden.py` |
| **Free** | Manual scan via `observeco clawforge garden` |
| **Pro** | Same |

### 3.10 ClawForge CLI (✅ Live)

| | |
|---|---|
| **What** | `profile` (context composition), `load` (intent classifier dry-run), `garden` (memory hygiene), `history` (per-turn stats) |
| **Free** | All four commands |
| **Pro** | Same |

### 3.13 System Prompt Compression (🔴 Planned)

**Tagline:** *Your SOUL.md is a book. Make it a tweet.*

**What it is:** `observeco chisel compress` reads SOUL.md, applies Chisel Lite (guidance dedup/rewording) or Full (guidance + memory culling + skill dedup + context refactor). CLI exists and works. Remaining: auto-watch daemon, dashboard card, Brain Analysis integration.

#### RDR — Phase 2 (Auto-Watch Daemon)

```
Problem: Compression is manual. User runs it once, saves tokens, then SOUL.md
         grows back over 30 days and they forget to run it again. Token bloat
         returns silently.
Solution: `observeco chisel compress --auto-watch` — fswatch-based file watcher
          on SOUL.md paths, 5s debounce, applies Full compression, writes `.chisel` version.
Key constraint: Debounce prevents compress-on-every-keystroke. Circuit breaker:
               3 failures → 10min cooldown. No compress while user mid-edit.
Success metric: Auto-watch triggers within 5s of file save completion. <1% false
               positives (compressing when user is still editing).
```

#### States — Phase 2

| State | Behavior |
|-------|----------|
| Daemon launched, no files changed | "Watching SOUL.md for changes..." |
| File changed, within 5s debounce | "Debouncing (3s remaining)..." |
| Debounce expired, compress queued | Running `chisel compress --mode [lite/full]` |
| Compress succeeded | Saved X tokens (Y%) |
| Compress failed (file locked) | Retry in 5s (max 3) |
| All retries exhausted | Critical flag: "Compression failed after 3 retries — file may be corrupt" |
| Circuit breaker tripped (3 failures in 10min) | 10min cooldown, resume automatically |
| Daemon stopped (SIGTERM/user) | Saves last state, resumes on restart |

#### Acceptance Criteria — Phase 2

- [ ] AC1: Auto-watch detects file save → runs compress within 5s of debounce
- [ ] AC2: Debounce timer resets on each subsequent save event
- [ ] AC3: Max 1 compress per 30s per file (prevents bulk-save storms)
- [ ] AC4: Circuit breaker: 3 failures = 10min cooldown, auto-resume
- [ ] AC5: Free: auto-watch runs Lite mode. Pro: auto-watch runs Full mode.

**Phase 3 (Dashboard Card):** Cumulative savings display, compression history chart with daily breakdown sparkline, auto-watch on/off indicator. Renders in <500ms. Free sees Lite savings only. Pro sees Full savings + per-file breakdown.

**Phase 4 (Brain Analysis Integration):** Brain Analysis shows "Compress" action button per bloated skill. Click → runs compress on parent SOUL.md targeting the bloated skill content. Push alert when threshold detected.

**Effort:** ~2.5 days (1 auto-watch daemon + 1 dashboard card + 0.5 Brain Analysis integration)

### 3.14 Cloud Token Tracking — Post-Turn Webhook (Primary) + Provider API (Fallback)
**Supersedes the previous §3.14 (Per-Turn Token Tracking).** Proxy (former §42) is deprecated — SDK-sidecar replaces it for local LLM tracking. Cloud tracking via webhook only.

**Tagline:** *Every agent turn costs something. Know exactly what — and who paid for it.*

**Architecture — Two lanes:**

| Lane | Mechanism | Coverage | Attribution | Risk | Status |
|------|-----------|----------|-------------|------|--------|
| **Primary** | Hermes-side post-turn hook → `POST /api/tokens/log` | All Hermes cloud LLM calls | Full: agent_name + model + provider + component breakdown | Zero (fire-and-forget) | ✅ Built — daemon thread, 2s timeout |
| **Fallback** | Provider billing API (OpenAI/Anthropic/DeepSeek) | Any cloud API call regardless of agent | Aggregate per-provider only. No per-agent. No component. | Low (read-only query) | 🔴 Planned |

**What the Hermes hook delivers per turn (the webhook data):**

| Field | Source | Example |
|-------|--------|---------|
| agent_name | Hermes config | `"main"` |
| turn_id | Hermes session | `"turn_abc123"` |
| model | Response body | `"deepseek-v4-flash"` |
| provider | Resolved from config | `"custom-ollama"` |
| total_tokens | Usage from response | `8432` |
| identity_tokens | Context start | `420` |
| skills_tokens | Skill content loaded | `3200` |
| memory_tokens | Memory content | `1800` |
| tools_tokens | Tool descriptions | `600` |
| guidance_tokens | System prompts | `200` |
| latency_ms | Wall-clock | `3400` |
| tool_calls | Tools invoked | `["search_files", "read_file"]` |
| topic_id | Telegram topic (if applicable) | `29` |

#### RDR

```
Problem: Users know their agents use tokens, but have no per-turn visibility into
         where tokens go (identity vs skills vs memory vs tools vs guidance). Cost
         attribution is manual spreadsheet work. Proxy captures cloud totals but
         cannot provide component breakdown or attribution by agent.
Solution: Agent-side hook POSTs structured token payload per turn to `POST /api/tokens/log`. Dashboard shows
          timeline + component breakdown + anomaly detection. Provider billing API
          fills the gap for uninstrumented agents.
Key constraint: POST per turn must be fire-and-forget — never block agent response.
               Payload max 4KB. Cache in agent for up to 3s if endpoint is down.
Success metric: >95% of agent turns produce a POST within 2s of completion. <0.5%
               of agent turns delayed by >50ms due to token tracking.
```

#### States

| State | Display |
|-------|---------|
| No token data yet (agent just discovered) | "Collecting token data..." |
| 24h of data available | Timeline view + component breakdown per agent |
| Agent not configured to POST | "Agent not sending token data — install plugin" |
| Webhook endpoint unreachable | "⚠ Last POST timed out — check agent connectivity" |
| Budget threshold breached ($) | Push alert via §17 + dashboard banner |
| Anomaly detected (>3σ turn cost) | 🔴 Spike marker on timeline + annotation |
| Daily budget exhausted | "Daily budget exhausted — agent may be throttled" |
| Never-pruned (Pro) | Full history + component trend chart across 30/90d |
| Gap detected (provider API > webhook total) | "Attribution gap: X% of tokens unaccounted for" |

#### What This Still Doesn't Catch (Honest)

These are documented scope limits — not bugs. Users are told upfront what ObserveCo can and can't see.

| Scenario | Why we can't catch it | Impact |
|----------|----------------------|--------|
| **1. Non-Hermes agents without their own hook** (raw curl scripts, custom Python scripts calling OpenAI SDK directly) | No webhook installed. No provider API-level agent attribution. | Those tokens appear in the provider billing aggregrate but show as "unattributed" gap. |
| **2. OpenClaw agents without §16 plugin** | Post-turn hook not available. OpenClaw uses Node.js/npm SDK with different instrumentation path. | No per-agent, per-turn, or component-level data. Only aggregate provider total. |
| **3. Multiple instances of the same agent** (two Hermes agents named "main") | Webhook reports agent_name from config — if both are named "main", they're indistinguishable. | Dashboard merges both into one line. No way to tell which "main" spent what. |

Mitigation for gaps #1/#2: Provider billing API (Lane 2) catches *total* cloud spend. The gap % tells the user how much they're missing. If it's high, they know they have uninstrumented agents.

Mitigation for gap #3: Instance-specific agent naming — user's responsibility. ObserveCo can add a config validation warning if duplicate agent names are detected.

#### Phase Breakdown

- **Phase 1 (✅ exists):** `POST /api/tokens/log` endpoint receives token data. DB tables `turn_log`, `skill_usage`, `guidance_fire`, `compress_log` store it. DB migration 29 adds model, latency_ms, tool_calls, topic_id columns.
- **Phase 2 (✅ built):** Hermes-side post-turn hook — after every turn, POST token payload to `POST /api/tokens/log`. Fire-and-forget daemon thread, 2s timeout, OBSERVECO_URL configurable. See specs/obs-spec-043-hermes-post-turn-hook.md.
- **Phase 3 (✅ built):** Dashboard Token Analytics tab with: 5-chart grid (Chart 1 Token Composition stacked bar [Input/Output/Cache/Est]; Charts 2-5 efficiency ratios Tokens/Turn, Output/Input, Cache Hit Rate, Cost/Turn — each with benchmark bands) + verdict card (top spender + cache trend + recommendation) + per-agent cache bar chart + confidence indicator (source accuracy %). See `specs/obs-spec-020-token-analytics-dashboard.md`.
- **Phase 4 (🔴 needs build):** Budget thresholds (daily/cost/anomaly sigma) → push alerts via §17 infrastructure.
- **Phase 5 (🔴 needs build):** Provider billing API integration — query OpenAI/Anthropic/DeepSeek, compare vs webhook aggregates, compute gap %.

#### Acceptance Criteria

- [ ] AC1: Hermes agent wrapper POSTs token data to `/api/tokens/log` after every turn
- [ ] AC2: No Hermes turn is delayed >50ms by the POST (fire-and-forget)
- [ ] AC3: ✅ Dashboard timeline renders 24h of token data per agent, component breakdown visible. Verdict card shows top spender + cache trend + recommendation. Cache-by-agent chart shows per-agent hit rates. Confidence indicator shows source accuracy %.
- [ ] AC4: Pro user sees never-pruned history with component trend chart
- [ ] AC5: Budget threshold (daily) triggers push alert via §17
- [ ] AC6: Anomaly detection flags >3σ spikes on chart with annotation
- [ ] AC7: Gap % indicator shows when provider billing API total exceeds webhook total
- [ ] AC8: OpenClaw gap is separately flagged if §16 not installed

**Effort:** ~3 days (1 Hermes hook + 1 dashboard + 0.5 anomaly + 0.5 provider API)

### 3.15 Auto-Heal (✅ Backend / ❌ Dashboard UI)

**The value, in one sentence:** Free = you notice a crash and click Heal. Pro = the system detects and recovers the crash within 5 seconds — you never know it happened.

**What it is:** The watch daemon automatically triggers `run_heal()` when pulse detects a dead agent. Detection-to-recovery: ~5 seconds. No human click, no SSH, no context switch.

**Current status:** Backend fully built (`src/observeco/heal/__init__.py` — 569 lines). L1 auto-restart, L2 proactive detection, snapshot-before-heal, HealCircuit, LLM escalation all working via CLI (`observeco heal --auto-heal`). **Dashboard UI missing** — no toggle, no status card, no per-agent config. The upsell promises "auto-detects, auto-restarts, predicts failures" but a Pro user activating a key sees only the static scenario comparison grid.

**Auto-restart opt-in:** Auto-restart is a *separate* toggle from auto-heal. When enabled, the daemon may call `_execute_action("restart", ...)` directly for known-safe patterns (process dead, memory leak, TOCTOU loop) without human or LLM confirmation. `pip_install`, `code_fix`, `garden_cleanup`, `cooldown`, and `acknowledge` NEVER auto-execute — they always need the full heal pipeline or human approval. Controlled by `auto_heal.restart_patterns` in config (list of diagnosis labels). Empty list = disabled.

**Safer than it sounds:** `_diagnose_agent()` returns a read-only proposal. HealCircuit (in-memory, 3-failure, 4h cooldown) prevents restart storms. Snapshot-before-heal captures full state before any action. The risk is process flapping — a restart that kills then immediately re-crashes — bounded by HealCircuit's 3-retry ceiling.

#### RDR — Dashboard UI

```
Problem: Auto-heal exists on the backend but has no dashboard controls. Pro users
         paid for auto-detection & auto-recovery but see no way to enable, disable,
         or monitor it. The upsell promises working features — the dashboard ships
         empty cards.
Solution: Dashboard panel with per-agent toggle + status card + heal history table.
Key constraint: Must degrade gracefully when heal daemon not running.
               Toggle must persist across server restarts.
Success metric: Pro user can enable auto-heal in <2 clicks from Fleet view.
```

#### Dashboard UI States

| State | Display |
|-------|---------|
| Heal daemon not running | "🔴 Heal daemon not running" + "Start daemon" button |
| Daemon running, no agents configured | Toggle available but off by default |
| Auto-heal enabled, idle | 🟢 Auto-heal enabled · "Waiting for issues" |
| Auto-restart also enabled | 🟢 Auto-heal + auto-restart enabled |
| Healing in progress | 🟡 Healing agent X... · spinner + elapsed time |
| Heal completed successfully | ✅ Healed agent X in 4.2s |
| Heal failed (circuit tripped) | 🔴 Circuit tripped · waiting 4h cooldown |
| Cooldown period | ⏳ Cooldown until HH:MM · N restarts this hour |
| L2 tolerance exceeded | Warning — drift >15% for agent, auto-heal scheduled |
| Free user sees toggle disabled | "Pro feature — upgrade to enable" tooltip |

#### Acceptance Criteria (Dashboard UI)

- [ ] AC1: Toggle enabled → heal daemon picks up config change ≤30s
- [ ] AC2: Toggle disabled → existing heal events still tracked, no auto action
- [ ] AC3: Status card shows daemon running/stopped within 5s of page load
- [ ] AC4: Heal history table shows last 20 events with outcome (agent, timestamp, reason, result)
- [ ] AC5: L2 threshold changes (drift %, memory debt) persist across server restart
- [ ] AC6: Free user sees toggle but it's disabled with "Pro feature" tooltip
- [ ] AC7: Auto-restart toggle only appears when auto-heal is enabled — separate config with same persistence

**What the human sees with Free:** You wake up at 7am, open the dashboard — Kepler has a red dot. Pulse log shows it crashed at 3am. Guard tripped at 3:01. Agent was dead for 4 hours. You click Heal, it recovers.

**What the human sees with Pro:** You wake up at 7am, open the dashboard — all green dots. One log entry: "Kepler auto-healed at 03:00:35 — 1 retry, success." (Optional Telegram notification sent at 3am if you want it.)

**Why Pro exists:** The tier boundary is clear — **manual trigger vs automatic trigger.** Free gives you the tool to heal when you notice. Pro gives you the system that heals before you notice.

| Dimension | Free (manual heal) | Pro (auto-heal) |
|-----------|-------------------|-----------------|
| Detection-to-recovery | Human-dependent (4h+ overnight) | ~5 seconds automatic |
| Overnight coverage | None — agent dead until morning | Full — crash at 3am, recovered by 3:00:35 |
| Context switches per crash | 1+ (notice → diagnose → click) | 0 (system handles, you get a log) |
| Recovery notification | None — discover when you check | Telegram/email sent immediately |
| Retry logic | Fixed: 3 retries, 4h cooldown | Configurable: 1-10 retries, custom cooldown |
| Yearly time saved (1 crash/week) | 0 (you did the work) | ~3.5 hours (52 context switches avoided) |

**Free:** Basic auto-heal (3 retries, 4h cooldown) — triggered manually via Heal button.
**Pro:** Configurable retries, cooldown, logging + notification — triggered automatically on dead detection.
**Effort:** ~1 day (dashboard UI only — backend already built)
**Depends on:** Nothing — heal logic already exists in `heal/__init__.py`
**Mockup:** `mockups/auto-heal.html`

#### L3 — Learning Loop (🔴 Spec — see obs-spec-081)

**The value, in one sentence:** L1/L2 heal the failure. L3 *writes a prevention skill* so the next time the same error appears, the fix is applied without calling the LLM — zero cost, zero latency.

After a successful LLM-assisted heal of a novel failure:
1. LLM extracts: failure pattern, root cause, fix applied, verification metrics
2. System writes a prevention SKILL.md to `~/.observeco/prevention/`
3. Indexed in SQLite FTS5 for fast pattern matching

Next time the same error signature appears:
1. FTS5 finds the prevention skill → known fix applied directly
2. Verification step still runs (safety gate — always)
3. If verification fails → full diagnostic pipeline runs + skill fail_count incremented

**Cost trajectory:** Week 1: ~$0.16/week LLM. Week 12: ~$0.02/week. The system gets cheaper as it learns your infrastructure.

**Spec:** `obs-spec-081-incident-skill-auto-creation.md`
**Inspiration:** [Hermes Incident Commander](https://github.com/Lethe044/hermes-incident-commander)
**Effort:** ~2d
**Free/Pro:** Prevention skill creation + application = BYOK (Free). Dashboard UI + cross-fleet pattern sharing + promotion gating = Pro.

### 3.16 OpenClaw Runtime Plugin (🔴 Deferred — post-v1.0)

> ⚠️ **Deferred.** Hermes is the priority for v0.4.0+. This section is retained for reference when multi-framework support resumes post-v1.0.

**Tagline:** *Load only what your agent needs, when it needs it — 40-60% fewer tokens per turn.*

**What it is:** A drop-in Node.js plugin (`@observeco/clawforge-plugin`) that replaces OpenClaw's built-in ContextEngine (`legacy`) with an intent-aware one. Instead of loading every skill, memory entry, and workspace file into every prompt, the plugin classifies each user message's intent and loads only the relevant subset. Three lifecycle hooks — bootstrap, ingest, pre-response — intercept the context assembly pipeline at each stage.

**Why this exists:** OpenClaw's default ContextEngine loads all registered context sources (SOUL.md, MEMORY.md, all skills, workspace files) into every turn. For a fleet of 6 agents with 50+ skills and growing MEMORY.md files, this means 40,000+ input tokens per turn — most of which are irrelevant to the current question. A debug question doesn't need the weather skill. A status check doesn't need the full memory history. Intent-aware loading cuts this waste without changing the agent's behaviour — same quality, fewer tokens.

**Mockup:** `mockups/openclaw-plugin.html`

#### RDR: ClawForge Context Engine Plugin

```
Problem: OpenClaw loads all context sources every turn — 40K+ tokens, most irrelevant. Wastes tokens, slows responses.
Solution: Intent-aware ContextEngine plugin that classifies each message and loads only relevant context.
Key constraint: Must not degrade response quality. Classification <5ms. Plugin must work with zero config.
Success metric: >40% token reduction per turn with <5% quality regression on 50-turn evaluation.

States explicitly specified:
[x] Happy path (intent classified, relevant context loaded, stats posted)
[x] Empty state (no skills installed — loads SOUL.md only)
[x] Loading state (plugin initializing — legacy engine used as fallback)
[x] Error state (classifier fails — falls back to loading all context)
[x] Partial data (some skills have no metadata — loaded as unknown intent)
[x] Stale data (stats endpoint unreachable — cached locally, retried)
[x] Timeout state (classification >5ms — use keyword fallback)
[x] Degraded state (plugin crashes mid-turn — legacy engine takes over)

Lifecycle specified:
[x] Start: Plugin loads on gateway start. Registers ContextEngine. No external calls.
[x] Run: Each turn: classify → load subset → estimate tokens → demote if needed → POST stats.
[x] Crash: OpenClaw falls back to legacy ContextEngine automatically. No agent downtime.
[x] Reboot: Plugin re-registers on next gateway start. No state to recover.
[x] Cleanup: Stats pruned per retention config (24h free, unlimited pro).
[x] Stale detection: Stats POST failure → retry with exponential backoff (3 attempts).
```

#### States & edge cases

| State | What Shows |
|-------|-----------|
| Plugin installed but not activated | Agent uses legacy engine. Plugin status: "Installed. Run `observeco clawforge plugin --activate` to enable." |
| Plugin activated, first turn | Bootstrap hook fires. Loads SOUL.md + MEMORY summary. Dashboard shows first savings entry. |
| Normal turn (intent classified) | Ingest hook fires. Loads matching skills. Stats POSTed. Dashboard shows per-turn savings. |
| Intent confidence <0.3 | Falls back to loading default context set (all skills). No savings this turn. |
| Classifier error | Logs warning. Falls back to legacy loading. Agent continues normally. |
| Stats POST fails (network) | Stats cached locally in plugin-stats.db. Retried on next POST. No data loss. |
| Plugin crashes mid-turn | OpenClaw detects unhandled exception. Falls back to legacy engine. Agent response continues. |
| Plugin disabled via config | Legacy engine active. Plugin stats frozen at last known state. |
| ObserveCo server down | Stats POST fails silently. Cached locally. No impact on agent behaviour. |
| Large context (>70% window) | Pre-response hook demotes lowest-value content. Stats record demotion event. |

#### Lifecycle

- **Start:** Plugin loads when OpenClaw gateway starts. Registers as ContextEngine via `api.registerContextEngine`. No external API calls on startup.
- **Run:** Each user message triggers: classify intent (5ms) → load matching context → estimate tokens → demote if >70% window → POST stats. Continuous operation.
- **Crash:** OpenClaw catches unhandled exception in plugin. Falls back to legacy ContextEngine. Agent continues responding with full context. User sees no interruption.
- **Reboot:** Gateway restart → plugin re-registers → context engine active. No state recovery needed (plugin is stateless between turns).
- **Cleanup:** Stats pruned daily (24h free, unlimited pro). Plugin code is immutable npm package.
- **Stale detection:** Stats POST failure → exponential backoff (1s, 2s, 4s). After 3 failures → cache locally, retry on next turn.

#### Constraints register

| Constraint | Type | Verification |
|-----------|------|-------------|
| Classification latency <5ms | Hard | Benchmark 1000 classifications, P99 <5ms |
| Zero-config activation | Hard | Fresh install → `--activate` → working. No manual skill mapping. |
| No quality regression | Hard | 50-turn evaluation: response quality within 5% of legacy engine |
| Plugin crash doesn't kill agent | Hard | Kill plugin process mid-turn, verify agent responds via legacy fallback |
| Stats POST failure doesn't block agent | Hard | Kill ObserveCo server, verify agent still responds normally |
| Works with 0-100+ skills | Hard | Test with 0, 10, 50, 100 skills. All load correctly. |
| Compatible with OpenClaw 2026.5+ | Hard | Test on OpenClaw 2026.5.7 (current) |
| No external API dependency for local classifier | Hard | `classifyModel: "local"` works without internet |
| Plugin size <500KB | Hard | `npm pack` → verify tarball size |
| Stats payload <1KB per turn | Hard | Measure JSON payload size for 100 turns |

#### Success metrics

| Metric | Target | Measurement |
|--------|--------|------------|
| Token reduction per turn | >40% average | Compare context_before vs context_after across 200 turns |
| Classification accuracy | >80% correct intent | Manually label 100 messages, compare to classifier output |
| Classification latency | <5ms P99 | Benchmark 1000 classifications |
| Agent response quality | Within 5% of legacy | Blind evaluation: 50 turns, compare legacy vs clawforge responses |
| User comprehension | New user activates in <2min | User test: install → activate → see first savings |
| Stats reporting uptime | >99% of turns have stats | Track: turns with stats / total turns |
| Plugin crash recovery | 0 user-visible failures | Kill plugin 10 times mid-turn, verify 0 failed agent responses |
| Savings persistence | Stats survive plugin restart | Restart plugin, verify historical stats still accessible |

---

#### Architecture

The plugin registers as an **exclusive ContextEngine** via OpenClaw's `plugins.slots.contextEngine` config. This is a first-class plugin slot — only one ContextEngine can be active at a time. The built-in `legacy` engine loads everything; `clawforge` loads selectively.

```
Your OpenClaw Agent
  └── ContextEngine (slot: "clawforge")
       └── @observeco/clawforge-plugin
            │
            ├── 🟢 Bootstrap Hook (session start)
            │   └── Load: SOUL.md (identity) + MEMORY.md summary
            │   └── Skip: all skills, workspace files, detailed memory
            │   └── Savings: ~40-60% of full context on first turn
            │
            ├── 🔍 Ingest Hook (each user message)
            │   └── Classify intent from user message
            │   └── Load: skills matching intent + relevant MEMORY entries
            │   └── Skip: unrelated skills + stale memory sections
            │   └── Savings: ~30-50% per turn (varies by intent specificity)
            │
            └── 📊 Pre-Response Hook (before model call)
                └── Estimate total context tokens vs window limit
                └── If >70% of window: demote lowest-value content
                └── Demotion order: stale memory → unused skills → workspace context
                └── Reports stats to ObserveCo SQLite
```

#### OpenClaw Integration Points

The plugin uses these specific OpenClaw APIs:

| API | Purpose | SDK Import Path |
|-----|---------|------------------|
| `api.registerContextEngine(id, factory)` | Register as exclusive ContextEngine | `openclaw/plugin-sdk/plugin-entry` |
| `api.on('before_prompt_build', handler)` | Inject dynamic context before model call | `openclaw/plugin-sdk/plugin-entry` |
| `api.on('agent_end', handler)` | Capture per-turn token stats post-response | `openclaw/plugin-sdk/plugin-entry` |
| `api.on('gateway_start', handler)` | Start background services (stats writer) | `openclaw/plugin-sdk/plugin-entry` |
| `api.on('session_start', handler)` | Initialize per-session context cache | `openclaw/plugin-sdk/plugin-entry` |
| `api.pluginConfig` | Read user configuration from `plugins.entries.clawforge.config` | `api` object (auto-injected) |

**ContextEngine registration:**
```typescript
import { definePluginEntry } from "openclaw/plugin-sdk/plugin-entry";

export default definePluginEntry({
  id: "clawforge",
  name: "ClawForge Context Engine",
  register(api) {
    api.registerContextEngine("clawforge", (availableTools, citationsMode) => ({
      async assemble(context) {
        // Intent-aware context assembly goes here
        return { systemPrompt: "...", context: "..." };
      }
    }));
  }
});
```

**Activation in config:**
```json
{
  "plugins": {
    "slots": {
      "contextEngine": "clawforge"
    },
    "entries": {
      "clawforge": {
        "enabled": true,
        "config": {
          "classifyModel": "local",
          "intentThreshold": 0.3,
          "demoteThreshold": 0.7,
          "statsPath": "~/.observeco/plugin-stats.db"
        }
      }
    }
  }
}
```

---

#### Lifecycle Hooks — Detailed Behaviour

**Hook 1: Bootstrap (session start)**

Fires once per new session. Loads the minimum viable context:
- ✅ SOUL.md (agent identity — always needed)
- ✅ MEMORY.md summary (last 5 entries, not full history)
- ✅ Active tools list (names only, not descriptions)
- ❌ All skill files (loaded on-demand by ingest)
- ❌ Workspace files (AGENTS.md, USER.md, etc. — loaded on-demand)
- ❌ Full MEMORY.md history

**Token savings:** Bootstrap loads ~2,000-3,000 tokens instead of ~8,000-12,000 tokens (full context). **60-75% reduction on first turn.**

**Hook 2: Ingest (each user message)**

Classifies the user's intent, then loads only matching context sources:

| Intent Category | Skills Loaded | MEMORY Loaded | Workspace Files |
|----------------|---------------|---------------|------------------|
| `debug/error-fix` | Error handling + relevant tool skills | Recent error entries | None |
| `status/health` | Health monitoring skills | None | AGENTS.md |
| `feature/build` | Development + relevant tool skills | Recent project entries | AGENTS.md, USER.md |
| `general/chat` | Communication skills | Last 3 entries | SOUL.md only |
| `cron/automate` | Automation + scheduling skills | Recent cron entries | None |

**Classification method:** Lightweight keyword + embedding classifier. No external LLM call — uses a local TF-IDF model or simple keyword matching trained on the user's actual message patterns. Classification runs in <5ms.

**Token savings:** Typical turn loads ~4,000-6,000 tokens instead of ~8,000-12,000 tokens. **30-50% reduction per turn.**

**Hook 3: Pre-Response (before model call)**

Estimates total context size. If context exceeds 70% of the model's window:
1. Identify lowest-value content by recency and relevance score
2. Demote in order: stale MEMORY entries → unused skill descriptions → workspace context
3. Log demotion event with token counts

**Demotion threshold:** Configurable via `demoteThreshold` (default: 0.7 = 70% of window).

---

#### API Surface

The plugin exposes these methods to the ObserveCo ecosystem:

| Method | Source | What It Does |
|--------|--------|-------------|
| `POST /api/tokens/log` | ObserveCo server | Plugin POSTs per-turn stats after each agent_end |
| `GET /api/plugin/stats` | ObserveCo server | Dashboard reads cumulative savings |
| `GET /api/plugin/turns` | ObserveCo server | Dashboard reads per-turn breakdown |
| `observeco clawforge plugin --activate` | CLI | Register plugin + verify hooks |
| `observeco clawforge plugin --status` | CLI | Show plugin status + savings |
| `observeco clawforge plugin --deactivate` | CLI | Revert to legacy ContextEngine |

**Per-turn stat payload (POSTed after each turn):**
```json
{
  "agent_name": "kepler",
  "turn_id": "2026-05-28T10:32:15Z",
  "intent": "debug/error-fix",
  "intent_confidence": 0.87,
  "context_before": 12400,
  "context_after": 6800,
  "tokens_saved": 5600,
  "savings_pct": 0.45,
  "sources_loaded": ["SOUL.md", "error-handling", "memory-recent"],
  "sources_skipped": ["weather", "calendar", "web-search", "memory-archive"],
  "demotions": 0,
  "window_limit": 128000,
  "window_used_pct": 0.053,
  "provider": "deepseek",
  "model": "deepseek-v4"
}
```

---

#### Data Flow

```
OpenClaw Agent turn starts
  │
  ├── session_start hook → init context cache
  │
  ├── user message arrives
  │   │
  │   ├── bootstrap hook (first turn only)
  │   │   └── loads SOUL.md + MEMORY summary → ~2,500 tok
  │   │
  │   ├── ingest hook (every turn)
  │   │   ├── classify intent (local, <5ms)
  │   │   ├── select matching skills + MEMORY entries
  │   │   └── inject into prompt context → ~5,000 tok
  │   │
  │   └── pre-response hook (before model call)
  │       ├── estimate total tokens
  │       ├── if >70% window: demote lowest-value
  │       └── finalize context
  │
  ├── model call (with lean context)
  │
  └── agent_end hook
      ├── capture token counts (before/after)
      ├── compute savings
      └── POST stats to ObserveCo API
          └── stored in ~/.observeco/pulse.db (token_logs table)
              └── dashboard shows per-turn savings timeline
```

---

#### Token Savings Model

**Per-turn savings estimates (based on typical OpenClaw agent with 50+ skills):**

| Turn Type | Full Context | Intent-Aware | Savings | % |
|-----------|-------------|-------------|---------|---|
| Debug question | 12,400 tok | 5,800 tok | 6,600 tok | 53% |
| Status check | 12,400 tok | 3,200 tok | 9,200 tok | 74% |
| Feature request | 12,400 tok | 7,100 tok | 5,300 tok | 43% |
| General chat | 12,400 tok | 4,500 tok | 7,900 tok | 64% |
| Cron/automation | 12,400 tok | 5,200 tok | 7,200 tok | 58% |
| **Weighted avg** | **12,400 tok** | **5,200 tok** | **7,200 tok** | **~47%** |

**Fleet savings (6 agents × 50 turns/day):**

| Metric | Without Plugin | With Plugin | Daily Savings |
|--------|---------------|-------------|---------------|
| Fleet tokens/day | 3,720,000 | 1,560,000 | 2,160,000 tokens |
| DeepSeek ($0.15/M) | $0.56/day | $0.23/day | $0.33/day |
| Claude Sonnet ($3/M) | $11.16/day | $4.68/day | $6.48/day |
| Annual (DeepSeek) | $204 | $84 | **$120/year saved** |
| Annual (Claude Sonnet) | $4,074 | $1,708 | **$2,366/year saved** |

**Cost anchor:** "The plugin saves ~$120/year on DeepSeek and ~$2,366/year on Claude Sonnet for a fleet of 6 agents. That's 1.1x to 21.9x the Pro price. On local models (Ollama), the benefit is speed — 47% fewer tokens means ~47% faster time-to-first-token per turn."

---

#### Configuration

The plugin reads config from `plugins.entries.clawforge.config` in OpenClaw's config file:

```json
{
  "plugins": {
    "entries": {
      "clawforge": {
        "config": {
          "classifyModel": "local",
          "intentThreshold": 0.3,
          "demoteThreshold": 0.7,
          "statsPath": "~/.observeco/plugin-stats.db",
          "observecoEndpoint": "http://localhost:8420",
          "enablePreResponse": true,
          "logSkippedSources": false
        }
      }
    }
  }
}
```

| Config Key | Default | Description |
|-----------|---------|-------------|
| `classifyModel` | `"local"` | Intent classifier: `"local"` (TF-IDF, no API) or `"openai"` (GPT-4o-mini, higher accuracy) |
| `intentThreshold` | `0.3` | Minimum confidence to load intent-specific context. Below this, loads default set |
| `demoteThreshold` | `0.7` | Context window usage % that triggers pre-response demotion |
| `statsPath` | `"~/.observeco/plugin-stats.db"` | Local SQLite path for per-turn stats |
| `observecoEndpoint` | `"http://localhost:8420"` | ObserveCo server URL for stats reporting |
| `enablePreResponse` | `true` | Enable/disable pre-response demotion hook |
| `logSkippedSources` | `false` | Log every skipped source (verbose, for debugging) |

**Zero-config experience:** After install, the plugin works with all defaults. The only required step is setting `contextEngine: "clawforge"` in OpenClaw config.

---

#### Free vs Pro Tier

The plugin itself is **free and open source** (MIT) — it's a community tool, not an ObserveCo revenue gate. The tier split is on the **dashboard analytics** that consume the plugin's stats:

| Feature | Free | Pro |
|---------|------|-----|
| Plugin install + activation | ✅ | ✅ |
| Bootstrap hook (minimal context) | ✅ | ✅ |
| Ingest hook (intent-aware loading) | ✅ | ✅ |
| Pre-response hook (demotion) | ✅ | ✅ |
| Local stats (per-turn in SQLite) | ✅ 24h window | ✅ never-pruned |
| Dashboard savings display | ✅ | ✅ |
| Per-turn timeline (24h) | ✅ | ✅ never-pruned + anomaly detection |
| Intent classifier training | ❌ local TF-IDF only | ✅ custom classifier from usage data |
| Fleet-wide savings comparison | ❌ | ✅ cross-agent comparison |
| Budget threshold alerts | ❌ | ✅ push when agent crosses daily token budget |
| Custom demotion rules | ❌ | ✅ configure demotion order + thresholds |

**Why free:** The plugin's value is saving tokens. Gate-keeping it behind Pro defeats the purpose — users need to experience the savings before they'll pay for deeper analytics. The same pattern as every other ObserveCo free feature: free = the tool, Pro = the intelligence layer on top.

---

#### Implementation Phases

**Phase 1 — Plugin scaffold + bootstrap hook (~2 days)**

- Create `@observeco/clawforge-plugin` package
- `openclaw.plugin.json` manifest with `contracts: { tools: [] }` (no tools — hooks only)
- `definePluginEntry` with `registerContextEngine("clawforge", factory)`
- Bootstrap hook: load SOUL.md + MEMORY.md summary only
- `openclaw plugins install npm:@observeco/clawforge-plugin` works
- `plugins.slots.contextEngine = "clawforge"` activates the engine
- **Verification:** `openclaw plugins inspect clawforge --runtime --json` shows context engine registered

**Phase 2 — Ingest hook + intent classifier (~2 days)**

- Build local TF-IDF intent classifier (no external API dependency)
- 5 intent categories: debug, status, feature, general, cron
- Ingest hook: classify intent → select matching skills + MEMORY entries
- Intent cache per session (avoids re-classifying similar messages)
- **Verification:** Debug question loads only error-handling skills. Status check loads only health skills. Token count drops ~40%.

**Phase 3 — Pre-response hook + stats reporting (~1.5 days)**

- Pre-response hook: estimate tokens, demote if >70% window
- Demotion logic: stale memory → unused skills → workspace files
- POST stats to ObserveCo `POST /api/tokens/log` endpoint
- Local SQLite stats writer (`~/.observeco/plugin-stats.db`)
- **Verification:** Turn with large context gets demoted. Stats appear in ObserveCo dashboard.

**Phase 4 — Dashboard integration (~1.5 days)**

- New "Runtime Savings" card in Brain Analysis page (§3.4)
- Per-turn savings timeline (24h Free / never-pruned Pro)
- Savings vs dry-run comparison ("Plugin saved X% vs what `clawforge load --probe` estimated")
- Intent distribution pie chart (what % of turns are debug vs status vs general)
- **Verification:** Dashboard shows real-time savings from plugin turns.

**Total effort:** ~7 days

---

#### Dependencies

| Dependency | Type | Status | Notes |
|-----------|------|--------|-------|
| OpenClaw SDK (`openclaw/plugin-sdk/*`) | Runtime | ✅ Available | `definePluginEntry`, `registerContextEngine`, hooks |
| OpenClaw ContextEngine slot | Runtime | ✅ Available | `plugins.slots.contextEngine` exclusive slot |
| OpenClaw hook API (`api.on(...)`) | Runtime | ✅ Available | `before_prompt_build`, `agent_end`, `session_start`, `gateway_start` |
| ObserveCo server (`POST /api/tokens/log`) | Runtime | ✅ Exists | Per-turn stats endpoint (from §14) |
| ObserveCo SQLite (`~/.observeco/pulse.db`) | Runtime | ✅ Exists | Stats storage (shared with §14 token_logs table) |
| Intent classifier (TF-IDF) | Build-time | 🔴 To build | No external dependency — ~200 lines of JS |
| ObserveCo CLI (`observeco clawforge plugin`) | Build-time | 🔴 To build | Install + activate + status commands |

**No OpenClaw source code changes required.** The plugin uses only public SDK APIs.

---

#### Testing Strategy

| Test | Method | Pass Criteria |
|------|--------|--------------|
| Plugin installs | `openclaw plugins install npm:@observeco/clawforge-plugin` | No errors, `plugins list` shows `clawforge` |
| Plugin activates | Set `contextEngine: "clawforge"` + restart gateway | `plugins inspect clawforge --runtime --json` shows ContextEngine registered |
| Bootstrap loads minimal context | Compare token count with/without plugin | Bootstrap loads <3,500 tok (vs ~10,000+ full) |
| Intent classification accuracy | Send 50 test messages across 5 categories | >80% correct classification (local TF-IDF) |
| Ingest loads relevant skills | Debug message → only error skills loaded | Loaded skills match intent category |
| Pre-response demotion fires | Send message that pushes context >70% window | Demotion log entry appears, context below threshold |
| Stats report to ObserveCo | Complete 10 turns | 10 stat rows in `token_logs` table |
| No regression on quality | Run 20-turn conversation, compare responses | Response quality within 5% of baseline (no hallucinated answers) |
| Graceful fallback | Disable plugin mid-session | Reverts to legacy ContextEngine, no errors |
| Performance overhead | Measure hook execution time | <10ms per hook (no user-perceptible latency) |

**Integration test:** Install plugin → run 50-turn conversation → verify dashboard shows savings timeline → verify SQLite has per-turn stats → verify no quality regression.

---

#### What the Human Sees

**Before (no plugin):** Every turn loads the full 12,400-token context. A debug question loads weather, calendar, and web-search skills it will never use. A status check loads all development skills. Tokens are wasted on every single turn.

**After (with plugin):** Same agent, same quality. Debug questions load 5,800 tokens (53% less). Status checks load 3,200 tokens (74% less). The agent responds just as well — because it never needed those unused skills for this particular question.

**Dashboard shows:**
- "ClawForge plugin: ✅ Active on kepler"
- "This session: saved 31,240 tokens across 24 turns (47% avg reduction)"
- Per-turn timeline: each turn shows loaded vs skipped sources
- Intent distribution: "52% debug, 23% status, 15% feature, 10% general"

**Install experience:**
```bash
$ openclaw plugins install npm:@observeco/clawforge-plugin
✅ Plugin installed: @observeco/clawforge-plugin v0.1.0

$ openclaw config set plugins.slots.contextEngine clawforge
✅ ContextEngine set to "clawforge"

$ openclaw gateway restart
✅ Gateway restarted
✅ ClawForge plugin registered
✅ bootstrap hook: active
✅ ingest hook: active  
✅ pre-response hook: active
```

### 3.17 Push Alerts (✅ Backend / ❌ Dashboard UI)

**The value, in one sentence:** Free shows you alert history when you open the dashboard — hours after the event. Pro pushes every alert to Telegram, Discord, or email within 3 seconds. You know before your agent fails twice.

**What it is:** When a circuit trips, drift exceeds threshold, or heartbeat is missed, the alert delivery module (`src/observeco/alerts/push.py` — 205 lines) pushes a notification to Telegram, Discord, webhook, or email. Free users see the same alerts in-dashboard — but only when they open it.

**Current status:** Backend fully built — Telegram, webhook, email delivery working. Subscription management, delivery logging, event-type filtering all functional. **Discord not yet implemented** (needs Discord webhook integration). **Dashboard UI missing** — no subscription management UI, no delivery log view, no test button. The upsell promises "Telegram/Slack/email push" but a Pro user activating a key sees only the static scenario comparison grid.

**The gap-aware design:** Free users see every alert with a "discovery gap" badge showing how late they found out:
> *"⚡ hermes-triage circuit tripped — happened 03:15 · You discovered 07:00 (when you opened dashboard) — 3h 45m gap"*

This makes the Pro value visible even in the free tier: the gap becomes the pain point.

**What the human sees with Free:** Opens dashboard at 7am. Sees 4 alerts with discovery gaps totalling 8h 47m. Knows there was trouble, but only after it's long over.

**What the human sees with Pro:** Gets a Telegram notification at 3:15am: "⚠️ hermes-triage circuit tripped — 3 consecutive failures." Can investigate immediately or go back to sleep. Dashboard shows all alerts with "✅ Notified at 03:15:03" tags.

| Dimension | Free (in-dashboard) | Pro (push) |
|-----------|-------------------|------------|
| Alert discovery latency | When you open dashboard (hours) | <3 seconds from event |
| Overnight visibility | None — alerts pile up unseen | Full — notification arrives immediately |
| Undiscovered downtime (24h) | **8h 47m** avg across 4 alerts | **0s** |
| Context switches | High (you check proactively) | Low (alert finds you when relevant) |
| Alert channels | Dashboard only | Telegram · Discord · Webhook · Email |
| Customizable thresholds | Fixed (drift >10%, 3 miss heartbeat) | Configurable per alert type |
| Wasted attention per week | ~30 min (checking for alerts) | ~0 min (alerts come to you) |

**Free:** ❌ In-dashboard only — alerts show with discovery gap badges.
**Pro:** ✅ Telegram + webhook + email, multi-channel routing, custom thresholds. Zero discovery gap.

#### RDR — Dashboard UI

```
Problem: Push alerts deliver to Telegram/webhook/email but (a) Discord is missing,
         (b) there's no dashboard UI to manage subscriptions, and (c) no delivery
         log to verify alerts are flowing. The upsell promises "Telegram/Slack/email
         push" — a Pro user activating a key sees a static grid with no config.
Solution: Add Discord delivery + dashboard subscription management panel +
          delivery log + test button.
Key constraint: Must support all 4 channels (Telegram, Discord, webhook, email)
               with consistent delivery semantics. Dashboard must work without
               any channel configured.
Success metric: User can configure a new alert channel in <30s via dashboard.
```

#### Dashboard UI States

| State | Display |
|-------|---------|
| No channels configured | "No alert channels configured" + "Add Channel" button |
| Channel active | 🟢 Telegram connected · verified |
| Channel pending verification | 🟡 Webhook configured · "Send test" to verify |
| Channel failed (3 consecutive) | 🔴 Email delivery failed · "Last error: Connection timeout" |
| Delivery log empty | "No alerts delivered yet — they'll appear here when triggered" |
| Delivery log populated | Table: timestamp × agent × alert type × channel × status |
| Test alert sent | Modal: "✅ Test alert sent to Telegram" |
| Test alert failed | Modal: "Test alert failed — Invalid webhook URL" |
| Free tier | Channel list visible but all "Pro feature" disabled |

#### Acceptance Criteria

- [ ] AC1: User can configure Telegram chat ID → test alert sent & verified
- [ ] AC2: User can configure Discord webhook URL → test alert sent via embed
- [ ] AC3: User can configure webhook URL → POST with JSON payload received
- [ ] AC4: Delivery log shows status for each alert (sent/failed/pending)
- [ ] AC5: Failed delivery shows error message in log
- [ ] AC6: Channel marked 🔴 after 3 consecutive failures
- [ ] AC7: Discord webhook sends colour-coded embeds (🔴 error / 🟡 warning / 🟢 recovery)
- [ ] AC8: Free user sees UI but test/save disabled with "Pro feature" tooltip
**Effort:** ~3 days
**Mockup:** `mockups/push-alerts.html`

### 3.18 Extended History (🔴 Planned)

**Tagline:** *The longer you run ObserveCo, the smarter it gets — but only if it remembers.*

**What it is:** Dashboard queries expanded from 7d (Free) to full history (Pro). Powers Auto-Heal Layer 2's trend baseline engine — history depth determines which L2 detection signals are available.

#### RDR

```
Problem: Data accumulates daily but only 7d is visible. L2 detection signals need
         14d+ baselines to be meaningful — P95 drift needs 14d, output patterns
         need 21d, multi-signal patterns need 30d. 7d free retention loses value
         that compounds over time.
Solution: Free gets 7d with daily prune. Pro gets never-pruned full history + L2
          baseline engine for 14d/21d/30d/90d windows + range selector in dashboard.
Key constraint: Same SQLite, same code path, different WHERE clause. Pruning cron
               at 3am must complete in <30s for 20-agent fleet.
Success metric: Query performance for never-pruned Pro stays under 200ms for any range.
```

#### States

| State | Display |
|-------|---------|
| First run (no data) | "Collecting data — history will appear as agents are monitored" |
| <7d of data | Partial timeline with "N days of data collected" note |
| 7d available (Free) | Full 7d timeline. Older data pruned yesterday at 3am |
| Never-pruned (Pro, 30d+) | Full history + range selector (7d/14d/30d/90d/all) |
| Full L2 detection (14d+) | P95 drift detection active |
| Full L2 detection (21d+) | Output hallucination trend active |
| Full L2 detection (30d+) | Multi-signal pattern detection active |

#### Acceptance Criteria

- [ ] AC1: Daily prune cron at 3am removes entries >7d for Free users
- [ ] AC2: Prune completes in <30s for 20-agent fleet
- [ ] AC3: L2 baseline engine supports --range=14d/21d/30d/90d
- [ ] AC4: Dashboard chart range selector (7d/14d/30d/90d/all) works
- [ ] AC5: Pro never-pruned: all data retained unless user explicitly configures otherwise

**Effort:** ~4 days (1 data layer, 2 baseline engine, 1 dashboard)

### 3.19 Communication Pathway Map (✅ Live — Hermes primary)

> ℹ️ This feature also detects OpenClaw agents via launchd plist scanning. OpenClaw support is retained for existing users but not actively developed. Hermes is the priority for v0.4.0+.

**Tagline:** *Where did my message go? Every delivery path in your ecosystem, traced from source to consumer.*

**What it is:** An interactive graph that shows every message delivery path — cron → agent → platform → human. Every path starts at a **source** and terminates at a **consumer**. Paths that don't reach a consumer are **dead ends** — the core diagnostic. Detects 7 failure scenarios.

**Key insight — Store-and-Forward vs Dead Ends:** Not every edge with no visible human/platform consumer is a failure. Cron jobs delivering to `local` (filesystem) use a **Store-and-Forward** pattern — writes to a durable store that other processes consume independently. These are healthy paths, not dead ends. The graph now distinguishes:
- **Green (filesystem):** cron→`filesystem` node — data written to durable store, available for consumption
- **Red (dead end):** genuinely unreachable target (failed delivery, dead consumer, no known store)

**Why this exists:** Information gets routed wrong all over the ecosystem — cron → dead inbox, agent → wrong outbox, direct writes bypassing the router, alias misrouting, intelligence tier misplacement, bridge failures, stale inboxes. The map makes every invisible failure visible.

**Non-negotiable rules:**
- Every green (healthy) and yellow (concern) edge MUST connect two entities. No dangling lines.
- Dead ends (red) are a distinct visual: dashed red line from source → red × stop marker. The stop marker is NOT a node — it's a terminal icon.
- No overlapping nodes. Dagre ranked layout (`rankDir='LR'`) ensures this.
- All nodes are draggable. Dagre is the starting layout; users reposition to declutter.

**Entity model:**

| Type | Icon | Shape | Color | Example |
|------|------|-------|-------|---------|
| Source (cron) | ⏰ | Rounded rect | Amber | `cron-morning-brief` |
| Agent | 🧠⚡📋 | Rounded rect | Indigo or Purple | `Dreamer`, `Hound`, `Kepler` |
| Daemon | 👻 | Rounded rect | Pink | `Platform Daemon`, `Consume Daemon` |
| Watcher | 👁️ | Rounded rect | Rose | `Intelligence Watcher`, `Update Watcher` |
| Gateway | 🌐 | Rounded rect | Violet | `ai.hermes.gateway`, `ai.openclaw.gateway` |
| Platform | 📱 | Rounded rect | Cyan | `Telegram`, `WhatsApp` |
| Consumer | 📖 | Ellipse | Teal | `Sean` |
| Router | 🔀 | Rounded rect | Blue | `Signal Router` |
| Mesh | 🔗 | Diamond | Lime | `openclaw-mesh-peer` |
| Filesystem | 💾 | Ellipse | Slate | `filesystem` (Store-and-Forward) |

**Edge status colors:**

| Status | Line | Meaning | Has Both Ends? |
|--------|------|---------|----------------|
| 🟢 Green | Solid 2.5px | Complete path to consumer | YES (source + target) |
| 🟢 Green (fs) | Solid 2px, slate | Store-and-Forward to filesystem | YES (cron→filesystem) |
| 🟡 Yellow | Solid 2.5px + ? icon | Connection exists, concern | YES |
| 🔴 Red | Dashed 2px + × marker | Dead end — no consumer | Only source |
| — Teal | Dashed 1.5px | Consumption path (agent→human) | YES |

**7 detectable failure scenarios:**

| # | Scenario | Edge Status | How Detected |
|---|----------|-------------|-------------|
| 1 | Cron deliver-to-dead-target | 🔴 Red | cron → inbox nobody reads → no consumer |
| 2 | Signal routing to wrong outbox | 🟡/🔴 | agent → non-standard outbox path |
| 3 | Direct inbox write (bypass router) | 🟡 Yellow | agent → inbox, no router in path |
| 4 | Agent alias routing mismatch | 🟡 Yellow | signal → alias inbox, verify semantic |
| 5 | Intelligence tier misrouting | 🔴 Red | write → wrong tier → no consumer |
| 6 | Cross-platform bridge failure | 🔴 Red | agent → dead bridge → dead end |
| 7 | Stale agent inbox (unconsumed) | 🟡 Yellow | inbox → agent that doesn't process it within expected window |
| 8 | Store-and-Forward (filesystem) | 🟢 Green | cron→filesystem→agent — healthy, no fix needed |

**What data it reads:** Agent configs from pulse.db (framework-agnostic), cron job specs (Hermes `~/.hermes/cron/jobs.json`), signal inbox routing (`~/.hermes/signals/*/inbox/`), platform bridge states, agent daemon states from pulse check. Edge metadata stores full deliver target strings (e.g., `telegram:-1001234567890:17585`) so the map can show specific group/chat IDs rather than just platform names.

**Edge metadata model:** Each `pathway_edges` row has a `metadata` column (JSON TEXT, default `{}`). When a cron edge is created during scan, the cron's full `deliver` field is stored in metadata as `{"deliver": "telegram:-1001234567890:17585"}`. This powers:
- Detail panel: shows "Delivers to: telegram:-1001234567890:17585" on edge click
- Inline labels: edges with specific platform targets get a compact label on the edge (truncated to fit)
- Left-to-right pipeline: sources (left) → platforms/channels (center) → consumers (right), with per-channel delivery targets visible

**Data collection:** Hybrid passive + active, 8-step scan pipeline:
| Step | Source | What It Detects | Generic? |
|------|--------|-----------------|----------|
| 1 | Known consumer nodes | Hardcoded (e.g. "Sean") | ✅ Yes |
| 2 | Platform nodes | Auto-detected from cron `deliver`/`delivery` targets. No more hardcoded list. | ✅ Yes |
| 3 | Signal Router | Static router node | ✅ Yes |
| 4 | `agent_configs` from pulse.db | All registered agents → Telegram (pulse check) | ✅ Yes |
| 5 | Cron job scheduler files | Auto-discovers `~/.hermes/cron/jobs.json` + `~/.openclaw/cron/jobs.json` + any path in `OBSERVECO_PATHWAY_CRON_DIR` env var (colon-separated). Parses both Hermes string-`deliver` and OpenClaw dict-`delivery` formats. Creates platform nodes from delivery targets on-the-fly. | ✅ Configurable, framework-agnostic |
| 6 | Agent signal inboxes | Agent-to-agent routing from signal `from`/`to` fields via `OBSERVECO_PATHWAY_SIGNALS_DIR`. Deduplicates by `signal_id` (highest severity wins). Reads all 5 subdirectories: inbox, archive, outbox, quarantine, failed. | ✅ Configurable, framework-agnostic |
| 7 | Daemon/watcher/gateway discovery | Scans macOS launchd plists matching `ai.hermes.*`, `ai.openclaw.*`, `com.hermes.*`. Auto-classifies by name pattern: `*daemon` → daemon, `*watcher` → watcher, `*gateway*` → gateway, `*mesh*` → mesh. Framework detected from plist prefix. | ✅ macOS, both frameworks |
| 8 | OpenClaw agent discovery | Reads `~/.openclaw/openclaw.json` agents.list for framework-agnostic agent registration. Labels agents with `(OpenClaw)` in detail panel. | ✅ OpenClaw |

Framework-agnostic detection (steps 1-4) works for any observeco user. Steps 5-6 auto-discover both Hermes `~/.hermes/cron/jobs.json` and OpenClaw `~/.openclaw/cron/jobs.json` paths (overridable via `OBSERVECO_PATHWAY_CRON_DIR` and `OBSERVECO_PATHWAY_SIGNALS_DIR`). Step 7 detects background daemons, watchers, and gateways via macOS launchd plists (`ai.hermes.*`, `ai.openclaw.*`, `com.hermes.*`), auto-classified by name pattern. Step 8 registers OpenClaw agents from `openclaw.json` — no AGENTS.md scanning needed.

**Confidence indicators on each edge:**

| Score | Source | Display |
|-------|--------|---------|
| 100 | Verified by ACPS router | No badge |
| 75 | Detected from signal_router pass-through | "auto-detected" |
| 50 | Detected from filesystem events | Dashed outline |
| 25 | Manually declared by user | "Manual" badge |
| 0 | Inferred from config, never observed | "Inferred" + dotted line |

**Interactions (Pro):** Node click → right detail panel (name, type, status, connected edges, issues, fix button). Edge click → source→target, status, mechanism, scenario, metadata (deliver target, group IDs). Hover → highlight node + dim non-connected neighbors (Datadog pattern). Pan/zoom: mouse wheel + drag empty space. Drag: all nodes repositionable, saved to localStorage.

**Filters (Pro):** By status: All / Complete / Concerns / Dead ends. By agent: pick one, show only its edges + connected nodes. Implementation: `display:none` — non-matching elements disappear entirely.

**v1 scope:** Data collection + Cytoscape.js rendering + dagre layout + click/hover/drag + detail panel + filters + confidence indicators. Out of scope: multi-machine paths, historical trends, multiple consumers, auto-fix buttons, non-Telegram bridges, OpenClaw hub contract detection.

**Tech stack:** Cytoscape.js (CDN) + dagre layout + HTML detail panel. Single-file HTML, no build step.

| Feature | Free | Pro |
|---------|------|-----|
| Static snapshot + dead-end detection | ✅ | ✅ |
| Color-coded edges + stop markers | ✅ | ✅ |
| Click node → detail panel | ❌ | ✅ |
| Draggable nodes | ❌ | ✅ |
| Filter by status / agent | ❌ | ✅ |
| Live auto-refresh | ❌ | ✅ |
| Auto-alert on red path | ❌ | ✅ |

**Current status:** ✅ Live. 160 nodes, 587 edges detected — 569 green, 0 red, 18 yellow. Covers 53 agents, 85 cron jobs, 11 daemons, 7 watchers, 2 gateways, 1 platform, 1 filesystem. 54 cron→local false positives reclassified as Store-and-Forward (green → filesystem node). 18 yellow = signal consumption concerns (unconsumed inbox signals). Genuine dead ends eliminated.

**Daemon/watcher/gateway/mesh detection:** Step 7 scans macOS launchd plists matching `ai.hermes.*`, `ai.openclaw.*`, and `com.hermes.*`. Each plist is auto-classified by name pattern: names ending in `-daemon` or `daemon` → daemon node, `*watcher*` → watcher node, `*gateway*` → gateway node, `*mesh*` → mesh node. The framework (Hermes vs OpenClaw) is detected from the plist name prefix. This replaces the old two-phase approach (Phase 1 agent metadata / Phase 2 fallback) with a single framework-agnostic launchd scan that discovers all background services across both ecosystems.

**Recent fixes (2026-06-04 / 2026-06-07 / 2026-06-08):**
- **Subgraph folding:** New "Collapse Leaves/Expand All" toggle in toolbar. Groups leaf agents under hub nodes (platforms/routers/agents with 5+ connections), hides children + edges, and appends a count badge to the hub label. Non-destructive — hidden nodes retain their data for detail panel clicks.
- **Sticky header + summary bar:** Both pinned via `position: sticky` so buttons (Reset Layout, Refresh, filters) don't scroll away inside the dashboard iframe.
- **Hover dimming guard:** Protected against firing during dagre layout animation (prevents the intermittent "wrong node lights up" bug). Uses `layoutRunning` flag.
- **FK constraint fix for cron edges:** `pathway_scan` step 5 now creates platform nodes (telegram, whatsapp, etc.) with `source='manual'` before inserting edges that reference them. Without this, `PRAGMA foreign_keys = ON` caused silent `IntegrityError` on cron edge insertion — platform nodes were deleted by step 1's `DELETE FROM pathway_nodes WHERE source='auto'`. Fix ensures all cron delivery edges persist across scans.
- **Edge metadata on cron edges:** `pathway_scan` step 5 now stores the cron job's full `deliver` target in `metadata` column (e.g. `{"deliver": "telegram:-1001234567890:17585"}`). Detail panel displays "Deliver To: telegram:-1001234567890:17585" on edge tap. All pathway edges now carry metadata.
- **Generic ecosystem discovery (2026-06-08):** Complete framework-agnostic rework. Cron scanner now auto-discovers both `~/.hermes/cron/jobs.json` and `~/.openclaw/cron/jobs.json` (plus any `OBSERVECO_PATHWAY_CRON_DIR` env var paths). Parses both Hermes string-`deliver` and OpenClaw dict-`delivery` formats. Signal scanner deduplicates by `signal_id` (highest severity wins) and reads all 5 subdirectories: inbox, archive, outbox, quarantine, failed. Launchd scanner extended from `ai.hermes.*` to also cover `ai.openclaw.*` and `com.hermes.*` plists, auto-classifying as daemon/watcher/gateway/mesh by name pattern. OpenClaw agents discovered from `~/.openclaw/openclaw.json` agents.list. DB schema expanded: `pathway_nodes.CHECK(type IN (...))` now includes `daemon`, `watcher`, `gateway`, `service`, `mesh`. Frontend renders all 9 node types with distinct icons and colors. Total coverage: 160 nodes (54 agents, 85 crons, 11 daemons, 7 watchers, 2 gateways, 1 platform, 1 router, 1 consumer), 587 edges (526 green, 54 red, 7 yellow).

**Mockup:** `mockups/pathway-map-v5.html` — 434 lines, column pipeline layout, Cytoscape.js-ready.

#### 3.19.1 Pathway Map v2 — Layout & UX Improvements (✅ Live, June 2026)

**What this is:** Five quality-of-life improvements addressing the root causes of the "pathway map failed to render" error and making the graph usable for 111+ node ecosystems.

**⚠️ Root cause of render failure:** The error fires on the 5th `initializeCy()` retry when dagre layout throws on a large graph. Dagre's O(n²) complexity on 111 nodes × 80 edges can trigger a JS execution timeout in WebKit/Safari, especially when the container was initially hidden (ResizeObserver fallback fires) or when CDN scripts are still loading. The primary fix: try all 3 layouts (cola → cose → dagre) with fallbacks, and use ™Web Worker™ for constraint solving.

**5 improvements:**

| # | Feature | What It Solves | Free/Pro |
|---|---------|---------------|----------|
| 1 | **Smart layout fallback chain** | cola (best quality for dense graphs) → cose (force-directed fallback) → dagre (hierarchical last resort). Each layout tries; if it fails/crashes, the next one fires via `cy.layout().run()` exception handler. Web Worker isolation for layout computation (cola/cose run off main thread). | ✅ Both |
| 2 | **Edge bundling** | `cytoscape-edge-bend` plugin or manual bundled-edge rendering. Edges sharing a source+target group are drawn as a single Bézier bundle with tick marks for each constituent edge. Reduces visual clutter when 50+ edges converge on one hub node. | ✅ Both |
| 3 | **Time-based particle animation** | Animated particles along edges showing message flow direction. Uses `cytoscape-cose-bilkent` style edge animations or custom `requestAnimationFrame` particle system. Particles pulse from source → target in a 3s loop cycle. Toggle on/off via toolbar button. Green edges get green particles, red edges get red, etc. | ❌ Pro |
| 4 | **Focus mode (subgraph zoom)** | Click a node → "Focus" button in detail panel → zooms to that node's 1-hop neighborhood. Everything outside the focus zone dims to 15% opacity. Esc or "Exit Focus" button restores full view. Built on existing subgraph folding infrastructure. | ❌ Pro |
| 5 | **Historical replay (timeline)** | New SQLite table `pathway_edge_history` with columns: `edge_id`, `status`, `timestamp`. Collects state snapshots on each pathway scan. Frontend has a scrubber bar (date range slider) that replays edge status changes as an animation. Green→red transitions visible over time. | ❌ Pro |

**Implementation notes:**

- **Layout fallback (#1):** Implemented in `initializeCy()` — the function signature changes to accept a layout name parameter. The main `fetchGraph()` → `initializeCy()` pipeline becomes `fetchGraph()` → `tryLayout('cola')` → `catch → tryLayout('cose')` → `catch → tryLayout('dagre')` → `catch → showError()`. Web Worker via `Blob` URL for cola/cose computation. The `layoutRunning` flag guards are preserved.
- **Edge bundling (#2):** Post-processing pass after layout settles. Iterates edge pairs, groups by (source, target) direction. Bundled edges store their constituent IDs as a data attribute. Click on a bundle shows a popout list of individual edges in the detail panel.
- **Particle animation (#3):** Custom `requestAnimationFrame` loop that places small circles on each edge path. `edge.midpoint()` gives position at each frame. Particle speed proportional to edge length (longer = faster fps multiplier). Toggle button in toolbar — off by default.
- **Focus mode (#4):** Creates a focused `cy.nodes()` collection for the target node's neighborhood. Non-neighbor nodes get `opacity: 0.15`, non-neighbor edges get `opacity: 0.05`. A semi-transparent overlay rectangle draws around the focus zone. Restore via re-applying the original style.
- **Historical replay (#5):** Backend: new `pathway_edge_history` table, `pathway_record_snapshot()` function called at end of `pathway_scan()`, new endpoint `GET /api/pathway-snapshots?minutes=1440`. Frontend: `<input type="range">` on the timeline bar, labeled with timestamps. Scrubbing the slider re-fetches that snapshot and re-applies edge colors.

**Edge bundling algorithm:**
```
For each pair of edges (e1, e2):
  if e1.source === e2.source AND e1.target === e2.target:
    mark both as bundled under key `e1.source→e1.target`
Render each bundle as a single edge with Bézier curve
Each constituent edge gets a tick mark perpendicular to the bundle curve
Bundle count badge at midpoint (e.g., "3 edges → Sean")
Detail panel on bundle click: expandable list of individual edges
```

**Particle animation algorithm:**
```
For each visible edge at time t:
  progress = (t * speed) % 1.0  // 0→1 loop
  pos = edge.getPointAt(progress) // along the curve
  render particle at pos with edge's status color
  particle trail: 3 decaying opacity copies behind it (trail effect)
Speed = 1.0 / edge.length (normalized to graph bbox diagonal)
```

**Focus mode algorithm:**
```
onFocus(node):
  closedNeighborhood = node.closedNeighborhood()
  cy.elements().not(closedNeighborhood).forEach(el => {
    el.data('__original_opacity', el.style('opacity'))
    el.style('opacity', closedNeighborhood.has(el) ? 1.0 : 0.15)
    el.style('pointer-events', closedNeighborhood.has(el) ? 'yes' : 'no')
  })
onExitFocus():
  cy.elements().forEach(el => {
    el.style('opacity', el.data('__original_opacity') || 1.0)
    el.style('pointer-events', 'yes')
  })
```

**Historical replay data flow:**
```
pathway_scan() → pathway_record_snapshot() → INSERT INTO pathway_edge_history
  Edge: GET /api/pathway-snapshots?minutes=1440 → [{timestamp, edges: [{id, status}...]}, ...]
  Frontend: scrubber emits timestamp → fetch snapshots → applyEdgeStatuses(timestamp)
  applyEdgeStatuses() iterates visible edges, sets style('line-color') from snapshot status
  Animation: requestAnimationFrame loop interpolates between snapshots at 30fps
```

**Edge health history (Pro feature):** A new mini-timeline in the edge detail panel shows the last 7 days of status changes as a compact sparkline. Each pixel column represents a 30-minute bucket. Green/yellow/red pixels correspond to health. Computed client-side from `pathway_edge_history` data.

**Accessibility (UX Playbook audit):**
- All animations respect `prefers-reduced-motion` — particle animation and historical replay pause immediately when `@media (prefers-reduced-motion: reduce)` is active.
- Focus mode: no animation on enter/exit when reduced-motion is active.
- Edge bundle tick marks have `pointer-events: none` to avoid trapping keyboard navigation.
- Focus mode overlay has `aria-hidden="true"` — non-focused elements hidden from screen reader tree.
- Historical replay scrubber has proper ARIA labels: timeline slider labelled "Message flow replay", time display labelled "Snapshot timestamp".

#### 3.19.2 Signal Consumption Health (✅ Live, June 2026)

**What this is:** A new pathway scan step (Step 9) that checks whether agent-to-agent signals are actually *consumed*, not just delivered. A signal that reaches an inbox but never gets processed is a concern — even if the pathway edge between two agents is technically connected.

**Problem it solves:** The old model only checked edge presence (does A → B exist?). But A → B existing with a stale unconsumed signal is worse than no edge at all — it means the pathway is *nominally* healthy while the consumer silently offline.

**How it works:**

1. **Step 9 scans signal outboxes** for unconsumed signals (`consumed: false` or missing `consumed_at`)
2. For each unconsumed signal, derives an **expected consumption window** from its metadata
3. Compares actual staleness vs expected window → assigns status

**Cadence-aware window derivation:**

| Source | Expected Window | Why |
|--------|----------------|-----|
| Signal `retry_until` field | Explicit — use `retry_until - written_at` | Sender defined the deadline |
| Cron schedule (if source is a cron) | Next cron interval (e.g. `0 9 * * 1` = 168h) | Consumer's natural polling cycle |
| No info available | 7 days | Conservative — avoids false positives for weekly/monthly cadences |

**Status assignment:**

| Condition | Status | Meaning |
|-----------|--------|---------|
| Signal consumed normally | 🟢 Green | Healthy pathway |
| Unconsumed but within expected window × 1 | 🤫 Silent (no edge created) | Nothing wrong yet |
| Unconsumed, exceeded window × 2 | 🟡 Yellow | Concern — consumer may be down or stuck |
| Unconsumed, exceeded window × 6 (or 30+ days) | 🔴 Red | Dead — nobody has consumed this in extended period |

**Implementation:** New Step 9 in `pathway_scan()`:

```python
# Step 9: Signal consumption health
# Scan agent inboxes and outboxes for unconsumed signals
# Compare signal age against expected consumption window
for each unconsumed signal:
    window = derive_expected_window(signal)
    age = now - written_at
    if age > window * 2:
        status = 'yellow'
    if age > window * 6 or age > 30d:
        status = 'red'
    create/update pathway_edge with consumption status
```

**Detection signals consumed by Step 9:**
- Agent inbox signals (`~/.hermes/signals/{agent}/inbox/`)
- Agent outbox signals (`~/.hermes/signals/{agent}/outbox/`)
- Global outbox signals (`~/.hermes/signals/outbox/`)
- Global archive signals (`~/.hermes/signals/archive/`) — confirmed consumed → green
- Signal `consumed` flag, `consumed_at`, `retry_until`, `written_at` fields

**LLM escalation guard (Step 9 mitigator):** Step 9's signal scan can trigger LLM diagnosis when a red signal is found — but an LLM per red signal is expensive and creates a positive feedback loop (unconsumed signal → diagnostic signal → another unconsumed signal → another diagnosis). Guard:

| Rule | Behavior |
|------|----------|
| Max N diagnostics per hour | Configurable (default: 3), tracked per-agent. Stored as a counter file `~/.observeco/signal_diag/<agent>.count` with hourly expiry (timestamp + count). |
| Rate-limit window | A counter file contains `{count, window_start_epoch}`. Incremented each time LLM diagnosis fires in Step 9. When count >= N, red signals still appear but are marked `(diagnosis rate-limited)` — no further LLM call until the window resets. |
| Idempotent detection | If the same signal appears red in consecutive scans (signal never consumed), do NOT re-diagnose. Only diagnose when a *new* unconsumed signal crosses the red threshold. Tracked by signal filename in an LRU set (max 50 entries), memory-only. |
| Diagnosis model | Free (local LLM ≥4B params or rule-based) — never a cloud model. Pay-per-token diagnosis on a monitoring tool is the exact failure pattern §3.10 Error Anomaly Detection warns about. The diagnostic is a cheap classification (`dead_process | stuck_on_loop | config_error | unknown`), not a novel analysis. |
| Hallucination feedback loop | Step 9's own diagnostic signals (`"signal_diagnostic"` type) are excluded from Step 9 scanning. Agent's own consumer health signals never trigger their own diagnosis. Tag: `observeco_internal: true` in signal payload. |

**Self-test (LLM escalation guard):**
```python
# Run: python -c "from observeco.pulse.pathway import Step9Guard; g = Step9Guard(); assert g.can_diagnose('test_agent'); g.record_diagnosis('test_agent'); assert not g.can_diagnose('test_agent') if g.count == 3 else True"
# Expected: no assertion error. Verifies: counter increments, rate limit works, cross-scan dedup for same signal.
```

**New pathway_types added:**
| Type | Status | Meaning |
|------|--------|---------|
| `signal_healthy` | Green | Consumed normally within expected window |
| `signal_stale` | Yellow | Unconsumed for 2× expected window |
| `signal_dead` | Red | Unconsumed for 6× expected window or 30+ days |

**Future scope — cron output freshness:** For `local`/filesystem deliveries, Optionally check `~/.hermes/cron/output/{job_id}/` for recency. If a cron hasn't produced output in > 2× its schedule interval, flag yellow (cron may be failing silently). Not yet implemented — deferred for v0.3.

---

### 3.20 Glossary & FAQ Panel (✅ Live)

**Tagline:** *Don't make users Google what a circuit breaker is.*

**What it is:** In-dashboard glossary, definitions, and FAQ section explaining what every metric means — targeted at humans who see agent status dots, circuit badges, drift %, and token bars but don't know what they actually mean.

#### RDR

```
Problem: New users see dashboard metrics (pulse, circuit, drift, error badge) but
         don't understand what they mean or how to interpret them. Bridge the
         "under the hood" gap without forcing users to leave the dashboard.
Solution: "?" icon on every card metric → opens glossary modal/overlay with 8 topics.
          Three-tier content per topic: one-liner, detailed explanation, FAQ.
Key constraint: Must work offline (no external docs). No redirect to external page.
               Free tier gets full content (not Pro-gated).
Success metric: New user can understand any metric in <15s via glossary.
```

#### States

| State | Display |
|-------|---------|
| Topic loading | Skeleton text placeholder |
| Topic rendered | Formatted content: one-liner + explanation + FAQ |
| Topic not found | "Glossary topic not found — it may have been removed" |
| API error | "Could not load glossary — try again" + retry button |
| Offline | Static content embedded in JS (fallback) |

#### Topics (8)

| Topic | One-liner | Appears on |
|-------|-----------|-----------|
| Status dot | 🟢 alive / 🔴 dead / 🟡 error | Agent card header |
| Circuit breaker | N-failure detection, auto-cooldown | Agent card Guard row |
| Token bar | Identity + skills + memory + tools + guidance | Agent card Brain size |
| Drift sparkline | Component behaviour change over 7 days | Agent card Composition |
| Error badge | Count of errors in last 24 hours | Agent card Errors row |
| Pulse check | 30s health check per agent | Health modal |
| Heal button | Manual trigger + auto-heal (Pro) | Heal panel |
| Alerts panel | Alert types + discovery gap | Right-rail alerts |

#### Acceptance Criteria

- [ ] AC1: "?" icon appears next to each of the 8 metrics on fleet cards
- [ ] AC2: Click → modal opens with correct topic content
- [ ] AC3: Modal includes one-liner, detailed explanation, FAQ per topic
- [ ] AC4: Works offline (static JS fallback if API unavailable)
- [ ] AC5: All topics render in <200ms

**Effort:** ~3 hours

---

### ~~3.21 Skill Audit (`observeco chisel skills`)~~ — ~~Merged into Brain Analysis~~

|| | |
|---|---|---|
||| **What** | Scan all Hermes skill files (`~/.hermes/skills/*/SKILL.md`), measure each skill's token cost, report the worst offenders ranked by size. Auto-Heal L2 integration: bloated skill detected during circuit trip alert context. Inspired by @steipete's pattern: agents write bloated skills, every skill description + body is loaded into context every session. |
||| **Origin** | Peter Steinberger (@steipete) noted on X that most skill descriptions are verbose books loaded into every context. He wrote a tool to find worst offenders. This is the same idea applied to `~/.hermes/skills`. |
||| **How it works** | `observeco chisel skills` command walks `~/.hermes/skills/`, reads each `SKILL.md`, parses YAML frontmatter, measures: description tokens + body tokens + section breakdown (identity, skills, memory, tools, guidance). Reports: per-skill ranked table, per-category cumulative cost, cumulative fleet total. Auto-watch (Pro) stores scans in `~/.observeco/skill_audit.db` for drift tracking. |
||| **Free** | CLI scan + ranked table (per-skill + per-category). One-time snapshot. |
||| **Pro** | Auto-scan (weekly cron) + per-skill drift tracking (Δ vs last scan) + threshold alerts (>3,000 tokens or >30% scan-to-scan growth → Telegram push) + trend chart (12-week sparkline per skill) + integration with Auto-Heal push alerts (bloated skill context in circuit trip diagnostics). |
||| **Tiering** | **Free** → Discovery: `observeco chisel skills` shows the problem exists. **Pro** → Continuous vigilance: auto-watch catches bloat the week it starts, not the month you remember. |
||| **Effort** | ~3 days (1 drift DB + 1 auto-scan cron + 1 dashboard card) |
||| **Depends on** | `observeco chisel skills` CLI (✅ exists), push alert infrastructure (✅ from §17) |
||| **Implementation** | Phase 1: existing CLI (no change). Phase 2: new SQLite DB `~/.observeco/skill_audit.db` with `skill_scans` table (agent_name, skill_name, total_tokens, section_tokens breakdown, last_used, usage_7d, cost_per_turn, tier). Phase 3: `observeco chisel skills --auto-watch` subcommand + cron scheduling + threshold check + push alert on breach. Phase 4: dashboard card with ranked table, drift column, trend sparkline, auto-watch toggle banner. |
||| **Mockup** | `mockups/skills-audit.html` |
||| **Related** | Already have skill description truncation (120-char cap `build_skills_system_prompt()`). This complements it by making the size transparent. Together they form: measure → expose → truncate (in Hermes). |

### 3.22 Agent Health Detection Engine (🔴 Planned — market-informed)

> ℹ️ This section was written when OpenClaw was co-equal with Hermes. For v0.4.0+, Hermes is the primary target. OpenClaw and multi-framework support deferred to post-v1.0.

**Market research source:** `~/.hermes/intelligence/analysis/market-needs-research.md`
**Key findings: existing tools (Langfuse, Arize Phoenix, LangSmith) monitor LLM traces. Nobody monitors agent PROCESSES.**

#### Product Positioning

> **"Langfuse shows you what your agents said. ObserveCo shows you whether they're still breathing."**

**ObserveCo's differentiator:** Health-first, traces-second. Cross-framework by default. Platform-aware. Process-level. Affordable for solo devs ($9/mo).

#### Market Data That Drove This Design

| Rank | Pain Point | Source | Existing Tools |
|------|-----------|--------|----------------|
| 1 | **"Is my agent alive?"** — no process health visibility | HN "How are you monitoring AI agents?" | **Nobody does this** |
| 2 | **"Fragmented stack"** — Team A uses LangGraph, Team B uses CrewAI, no unified view | HN (chirdeeps) | **Nobody does this** |
| 3 | **"No audit trail for post-mortems"** | HN | Partial (Langfuse traces) |
| 4 | **"Surprise LLM bills"** — untracked token usage | HN | Proxy tools only |
| 5 | **"Messaging bot is connected?"** — no platform health check | Implied | **Nobody does this** |

**Framework adoption reality (PyPI downloads, last 30 days):**
LangChain 282M · LangGraph 53M · Pydantic AI 41M · CrewAI 14M · LlamaIndex 12M · Agno 3.6M. Users run 2-3 frameworks. No single-framework solution works.

**Key quote that defines the market:**
> *"Observability and governance cannot live inside the agent framework. They have to live in an independent execution layer."* — HN comment

**ObserveCo is that independent layer.**

---

#### What We Build (Launch — P0)

| Priority | Feature | Why Market Needs It | Competition |
|----------|---------|--------------------|-------------|
| **P0** | Agent process health (pgrep + launchd + Docker + systemd) | #1 pain point: "Is my agent alive?" | **Nobody** ⚡ |
| **P0** | OTel listener on port 4318 | 28 frameworks auto-emit. Zero-instrument entry point. | Phoenix does this, but ObserveCo adds process health on top |
| **P0** | Cross-framework unified dashboard | Fragmented stack = one pane for all frameworks | **Nobody** ⚡ |
| **P0** | Platform connectivity health (Telegram, Discord, Slack, webhooks) | Devs need to know if their bot is connected | **Nobody** ⚡ |
| **P1** | Docker container process health | ~60% of production agents run in Docker | **Nobody** ⚡ |
| **P1** | Crash log analysis (OOM, segfault, kill signals) | Post-mortem need cited on HN | **Nobody** ⚡ |
| **P2** | Cost per agent/model | #4 pain point — surprise bills | Proxy tools only |

#### What We Defer (Post-Launch)

| Feature | Why Defer | Future Trigger |
|---------|-----------|---------------|
| Bidirectional messaging gateway (send/receive on all platforms) | Pathway Map needed this, but market wants HEALTH first not messaging first | Phase 2 |
| Multi-agent comm tracing (inter-agent conversation visibility) | InsAIts exists but tiny; market not screaming for this yet | Phase 3 |
| CI/CD integration (GitHub Actions hooks) | 70% use it but no observability tool does this well | Phase 4 |
| Windows-specific probes | OTel listener covers Windows agents anyway via OTLP | Phase 4 |

---

#### Architecture

**The ObserveCo detection stack (4 layers):**

```
Layer 1 — Process Health (P0)
┌──────────────────────────────────────────────┐
│  pgrep -f agent_name          (macOS/Linux)  │
│  launchctl list               (macOS)        │
│  systemctl list-units         (Linux)        │
│  docker ps                    (Docker)       │
│  tasklist / Get-Process       (Windows)      │
│  → Status: alive / dead / error             │
│  → Every 30s, stored in pulse.db            │
└──────────────────────────────────────────────┘

Layer 2 — OTel Span Ingestion (P0)
┌──────────────────────────────────────────────┐
│  OTLP listener on port 4318/4317             │
│  Accepts spans from OpenInference (28 pkgs)  │
│  Extracts: agent_name, tool_calls, LLM calls │
│  → Feeds: pulse.db, pathway map, token track │
└──────────────────────────────────────────────┘

Layer 3 — Platform Connectivity (P0)
┌──────────────────────────────────────────────┐
│  Telegram bot: getMe() → connected status    │
│  Discord: gateway heartbeat alive            │
│  Slack: API test → connected                 │
│  WhatsApp webhook: last received timestamp   │
│  Email IMAP: login test → connected          │
│  → Status per platform in dashboard          │
└──────────────────────────────────────────────┘

Layer 4 — Cross-Framework Dashboard (P0)
┌──────────────────────────────────────────────┐
│  Single view: agents from any framework      │
│  Shows: alive/dead, framework label, tokens  │
│  Click → per-agent detail (health timeline)  │
│  All frameworks in one tab — not one per     │
└──────────────────────────────────────────────┘
```

---

#### Implementation Phases

| Phase | Scope | Systems Covered | Effort | Launch? |
|-------|-------|----------------|--------|---------|
| **P0** | Agent process health (pgrep + launchd + Docker + systemd) + OTel listener + platform connectivity + cross-framework dashboard | All frameworks (health), Hermes, OpenClaw, Docker, Telegram, Discord, Slack, webhooks | 6-8d | ✅ **Launch** |
| **P1** | Crash log analysis + Docker container expand + cost per agent estimates | OOM/segfault detection, full Docker integration | 3d | ⏳ Phase 1.1 |
| **P2** | Cost per model + budget thresholds + anomaly detection | Per-agent cost tracking | 4d | ⏳ Phase 2 |
| **P3** | Messaging gateway (bidirectional adapters: Telegram, Discord, Slack, Signal) | 4 send+receive platforms | 6d | ⏳ Phase 3 |
| **P4** | OS expansion (Windows services) + CI/CD hooks + extended adapters | Windows + GitHub Actions + 4 more platforms | 6d | ⏳ Phase 4 |
| **P5** | Plugin system + community adapter contributions | Community framework | 5d | ⏳ Phase 5 |

---

#### Reference implementations

| Reference | Stars | What to Learn |
|-----------|-------|---------------|
| Arize-ai/openinference | 1k★ | 28 Python instrumentations, OTel-native, standard ports (4318/4317) |
| traceloop/openllmetry | 7k★ | OTel semantic conventions for gen_ai |
| Hermes gateway (local) | — | 16 adapter BasePlatformAdapter ABC (for platform connectivity) |
| OpenClaw (local) | — | 35 channels + channel catalog JSON (for connectivity) |
| vectordotdev/vector | 22k★ | Multi-OS log/metric collection agent pattern (for crash logs) |
| hertzbeat | 7.3k★ | Open-source monitoring — protocol-level health checks, JMX, alerting |

---

#### Market-Ready Score: ~65%

| Capability | Market Expectation | Launch | Score |
|------------|------------------|--------|-------|
| Agent process health (any framework) | Must have | ✅ pgrep + launchd + Docker + systemd | **100%** |
| OTel span ingestion (28 frameworks) | Must have | ✅ OTel listener on 4318 | **100%** |
| Cross-framework unified dashboard | High value | ✅ Single pane for all frameworks | **80%** |
| Platform connectivity (Telegram/Discord/Slack) | Medium | ✅ Config-aware gateway probe (reads Hermes config, fallback chain) | **75%** |
| **Known issue (fixed):** Gateway probe hardcoded port 8642. Hermes API server defaults to 8642 but webhook server defaults to 8644 — only one may be running. Fix: read port from Hermes config.yaml (`gateway.api_server.port` → `webhook.port` → env var → try [8642, 8644]). See `server.py` `/api/platforms` endpoint. |
| Crash log analysis | Medium | ⚠️ Basic (stderr, kill detection) | **30%** |
| Cost per agent/model | High value | ❌ Phase 2 | **0%** |
| Multi-agent comm tracing | Low for MV1 | ❌ Phase 3 | **0%** |
| CI/CD integration | Medium | ❌ Phase 4 | **0%** |

**The 65% covers the gap nobody fills: agent process health + cross-framework + platform connectivity.** The remaining 35% is Phase 2-5 differentiation.

|## Free Tier — What You Get Immediately
|
|`pip install observeco[dashboard] && observeco dashboard` → instantly:
|
|- ✅ Fleet view with all your agents (Hermes, OpenClaw, Claude Code, Ollama, generic processes)
|- ✅ Auto-detected agents from Hermes + OpenClaw configs + generic discovery (ollama, psutil, ports)
|- ✅ Pulse check every 30s (alive/dead/error)
|- ✅ Circuit breaker (N-failure detection, auto-cooldown)
|- ✅ Token breakdown bar chart per agent (identity/skills/memory/tools/guidance)
|- ✅ 7-day drift trend per component
|- ✅ Error history (24h per agent)
|- ✅ Heal button (manual trigger)
|- ✅ In-dashboard alerts
|- ✅ Memory Garden (duplicates, contradictions, debt score)
|- ✅ All CLI commands: `pulse check`, `pulse circuit`, `chisel trim`, `chisel drift`, `chisel skills`, `clawforge profile/load/garden/history`, `dashboard`
|- ✅ Local SQLite — no cloud, no telemetry
|- ✅ MIT License — unlimited agents, unlimited users
|- ✅ **Agent invocation banner** — "X invocations this month" framed as value signal, not paywall. All features free for Hermes users.
|
|**Commercial model:** Free for Hermes users, forever. All features open. No invocation cap. No feature gating. **LLM features use your own API key** (`OBSERVECO_LLM_API_KEY` — bring-your-own-key). Static fallbacks when no key configured. The banner is the only monetisation signal — it frames how much LLM value you're tracking. Pro tier pricing deferred until beachhead validated. See `specs/commercial-strategy-v2.md`.

---

|## 5. Pro Tier — Future (Post-Beachhead Validation)

| Feature | Planned Solo ($9/mo) | Status |
|---------|--------------------|--------|
| Push alerts (Telegram, Discord, webhook, email) | ✅ All channels + zero discovery gap | ✅ Backend (Telegram/webhook/email) / ❌ Dashboard UI + Discord ~1.5d |
| Extended history (never-pruned) | ✅ Full history + L2 baselines up to 90d | ✅ Backend / 🔴 Prune cron + L2 baseline engine + range selector ~4d |
| Auto-heal (configurable L1+L2) | ✅ Auto-detect + auto-recover ~5s | ✅ Backend (L1+L2+CLI) / ❌ Dashboard UI ~1d |
| Chisel compress auto-watch | ✅ Auto-watch daemon + Full compression | ✅ CLI exists / 🔴 Auto-watch daemon + dashboard + Brain Analysis hook ~2.5d |
| Per-turn token tracking (never-pruned) | ✅ Full history + anomaly detection + budget alerts | ✅ Backend (endpoint + DB tables) / 🔴 Agent hooks + trend engine + alerts + dashboard ~4d |
| LLM Intelligence (7 consumers) | ✅ All 7 consumers (deep + shallow) permanently | ✅ Live — v1, 5 of 7 built, 2 deferred with fallbacks |
| Self-serve billing | ✅ License card, trial cancel, Grace portal | ✅ Live — Feature #26 |
| ~~Skill Audit auto-scan~~ | ~~✅ Weekly auto-scan + drift tracking + threshold alerts~~ | ~~✅ Merged into Brain Analysis~~ |
| Glossary & FAQ | ✅ Full glossary (Free tier too) | ✅ Live — 51 topics with detail + FAQ |

|**Pricing:** TBD — deferred until beachhead validated. Solo $9/mo anticipated. Team tier ($49/mo) delayed.
|30-day free trial via Stripe. Licensing infra: Supabase (licenses DB) + Vercel (API + admin dashboard). See `specs/stripe-integration.md`.

||**⚠️ Reality check:** Backend for most Pro features is built (heal engine, push delivery, token tracking, compress CLI, LLM service). **Dashboard UIs are the gap** — users activating a Pro key see a comparison grid, not working controls. The 30-day trial unlocks the LLM Intelligence Service (all 7 consumers) immediately. After trial, LLM shuts off, other features remain visible as upsells. Stripe checkout + webhook + license validation are built but waiting on Vercel/Supabase deployment (paying users managed offline for now).
|
|**Current priority:** Beachhead first (Phase 0 / Phase 1). All features free for Hermes users. Pro pricing ships after we prove the product works on someone else's machine. See `specs/commercial-strategy-v2.md`.
|
|---
|
|### 3.17b Action Buttons in Push Notifications (🔴 Planned)
|
|**Tagline:** *From "something is wrong" to "here's the fix" in one tap.*
|
|**What it is:** Action buttons embedded in push alert notifications. Telegram inline keyboards (restart/cooldown/trim), Discord buttons, webhook action URLs. Each button calls `/api/heal-action/{agent}/{action}` which invokes the heal system's `_execute_action()`.
|
|**How it works:**
|
|```
|Push alert fires → notification includes action buttons
|→ User taps "Restart" → POST /api/heal-action/kepler/restart
|→ Heal system runs _execute_action('restart', 'kepler')
|→ Result sent back as follow-up notification
|```
|
|**Available actions:**
|- `restart` — restart agent process
|- `cooldown` — reset circuit breaker cooldown
|- `trim` — run chisel trim on agent
|- `garden` — run memory garden cleanup
|- `ignore` — acknowledge alert, suppress duplicates for 1h
|
|**What's already built:**
|- Heal system `_execute_action()` with restart/cooldown/pip_install/trim/garden_cleanup — ✅ Live
|- Push alert delivery (Telegram, webhook, email) — ✅ Backend
|- `/api/trigger-heal` endpoint — ✅ Live
|
|**What needs building:**
|- `/api/heal-action/{agent}/{action}` endpoint — simple wrapper around `_execute_action()`
|- Telegram inline keyboard payload in push alert format
|- Discord button payload in embed format
|- Webhook action URL generation
|- Follow-up notification on action result
|
|**Free:** ❌ Pro only (requires push alert infra)
|**Pro:** ✅ All actions + follow-up notifications
|
|**Effort:** ~4h
|
|---
|
|### 3.64 Agent Health Report Card (🔴 Planned)
|
|**Tagline:** *Your fleet's weekly checkup, delivered to your phone.*
|
|**What it is:** A weekly digest push alert that aggregates 7 days of fleet health data. One SQL query per metric, one Jinja2 template. Delivered via existing push alert infra.
|
|**Metrics (all from existing tables):**
|- **Uptime %** — `SELECT AVG(status='alive') FROM pulse_log WHERE recorded_at > ?`
|- **Auto-heal count** — `SELECT COUNT(*) FROM heal_events WHERE timestamp > ? AND outcome='success'`
|- **Circuit trips** — `SELECT COUNT(*) FROM circuit_events WHERE timestamp > ?`
|- **Compressions run** — `SELECT COUNT(*) FROM compress_log WHERE timestamp > ?`
|- **Token cost** — `SELECT SUM(cost) FROM token_logs WHERE recorded_at > ?`
|- **Fleet size** — `SELECT COUNT(DISTINCT agent_name) FROM agents`
|
|**Format:**
|```
|📊 Your Fleet This Week
|━━━━━━━━━━━━━━━━━━━
|🟢 Uptime: 99.2%
|🔄 Auto-heals: 3
|⛔ Circuit trips: 1
|✂️ Compressions: 2
|💰 Spend: $14.23
|👥 Agents: 6
|
|Saved $8.47 vs last week by circuit breakers.
|```
|
**What's already built:**
- All data tables (pulse_log, heal_events, circuit_events, compress_log, token_logs) — ✅ Live
- Push alert delivery (Telegram, webhook, email) — ✅ Backend
- Jinja2 templating — ✅ Live (used by dashboard)

**What needs building:**
- Weekly cron job (scheduled push alert)
- 6 SQL queries (one per metric)
- Jinja2 template for the digest format
- Trend comparison vs previous week

**Free:** ✅ Weekly digest in dashboard
**Pro:** ✅ Push delivery + trend comparison

**Effort:** ~3h

---

### 3.T1 Tracing Layer (🔴 v0.4.0 — new)

**Tagline:** *Every agent turn, every tool call, every subagent — traced from root to leaf.*

**What it is:** A full OpenTelemetry-based tracing layer that captures every Hermes agent interaction as a structured span tree. Integrates the `hermes-otel` plugin (or native Hermes observability hooks) to emit spans for: session start/end, API requests, tool calls, subagent spawns, and gateway dispatches. Spans are ingested by the ObserveCo OTEL listener and rendered as a waterfall view.

**Why this exists:** Without tracing, you see token counts and health status but not *what happened* in a turn. Did the agent call 3 tools or 12? Did a subagent fail silently? Tracing answers these questions.

**Span hierarchy:**
```
Session (root span)
├── API Request (LLM call)
│   ├── Tool Call: search_files
│   ├── Tool Call: read_file
│   └── Tool Call: write_file
├── Subagent Spawn
│   ├── Subagent API Request
│   │   └── Tool Call: web_search
│   └── Subagent Complete
└── Session End
```

**What's already built:**
- Hermes observeco plugin (11 hooks) — ✅ exists, disabled in config
- OTEL listener on port 4318 — ✅ exists, writes to observeco.db (currently 0 bytes)
- Hermes post-turn webhook — ✅ built, fire-and-forget daemon thread

> ⚠️ **Risk:** The Hermes observeco plugin was disabled for unknown reasons. Enabling it may cause Hermes gateway instability (crashes, latency spikes, or hook failures). **Rollback:** `hermes plugins disable observability/observeco` + `launchctl kickstart -k gui/$(id -u)/ai.hermes.gateway` — reverts to proxy-based token tracking with no data loss. Test on a non-critical agent first.

> ⏱️ **De-risking step (before T1 build):** Enable the plugin on a non-critical agent (e.g., Dreamer or PA) for 24h and verify stability. If stable, proceed with T1. If unstable, revert and debug before building the waterfall view. This step is included in the v0.4.0 estimate (~1d buffer).

**What needs building:**
- Wire OTEL listener to write spans to pulse.db (single DB, not two)
- Enable hermes-otel plugin in config
- Span ingestion + storage in `trace_spans` table
- Waterfall view in dashboard (per-agent, per-session)
- Span replay (reconstruct agent state at any point in a session)

**States:**

| State | Display |
|-------|---------|
| No traces yet (plugin disabled) | "Enable the Hermes OTEL plugin to start tracing" |
| Traces flowing | Per-agent span timeline + waterfall |
| Span tree available | Expandable tree: root → subagent → tool calls |
| Replay mode | Step through spans in chronological order |

**Free:** Per-agent span timeline + waterfall view (24h window)
**Pro:** Full trace tree + replay + export + never-pruned history

**Effort:** ~3d (1d wiring + 1d waterfall UI + 1d replay)

---

### 3.T2 Evaluation Layer (🔴 v0.4.0 — new)

**Tagline:** *Not just how many tokens — was this turn any good?*

**What it is:** Structured export of Hermes internal evaluation signals per turn. Reads quality score, tool efficiency, retry flag, and hallucination flag from Hermes evaluation internals, writes to ObserveCo `eval_events` table. Gives quality signals — not just "how many tokens" but "was this turn good."

**Why this exists:** Token tracking tells you cost. Health monitoring tells you liveness. Neither tells you if the agent is *performing well*. A hallucinating agent that's alive and cheap is worse than a dead one — at least the dead one isn't producing bad output.

**Data per turn:**

| Field | Source | Example |
|-------|--------|---------|
| agent_name | Hermes config | `"main"` |
| turn_id | Hermes session | `"turn_abc123"` |
| quality_score | Hermes eval | `0.87` (0-1) |
| tool_efficiency | Derived | `0.65` (useful calls / total calls) |
| retry_flag | Hermes eval | `false` |
| hallucination_flag | Hermes eval | `false` |
| latency_ms | Wall-clock | `3400` |
| model | Response body | `"deepseek-v4-flash"` |

**What's already built:**
- Hermes post-turn webhook — ✅ built
- `/api/tokens/log` endpoint — ✅ exists
- Hermes evaluation internals — ❌ **NOT YET BUILT.** The Hermes agent does not currently export `quality_score`, `tool_efficiency`, `retry_flag`, or `hallucination_flag` per turn. These signals must be built into a Hermes plugin or hook before T2 can ingest them. See §3.42 (superseded) for the original spec.

**What needs building:**
- **Hermes-side eval export mechanism** — new plugin hook or post-turn payload extension that emits quality signals (~2-3d, Hermes codebase)
- Eval event ingestion endpoint (`POST /api/eval/log`)
- `eval_events` table in pulse.db
- Quality trend chart per agent (7d rolling)
- Quality regression detection (alert when score drops >15% vs 7d baseline)

**Dependency:** T2 is blocked on the Hermes eval export mechanism. The ObserveCo-side ingestion (endpoint + table + dashboard) can be built in parallel, but no data will flow until Hermes emits it.

**Free:** Eval event ingestion + quality trend per agent (24h)
**Pro:** Quality regression detection + correlation with drift/health + fleet quality comparison

**Effort:** ~4-5d total (2-3d Hermes eval export + 2d ObserveCo ingestion/dashboard)

---

### 3.T3 Behavioral Intelligence Layer (🔴 v0.4.0 — new)

**Tagline:** *Your agent has 3 problems right now. Here they are.*

**What it is:** A unified intelligence layer that combines anomaly detection, context health scoring, relapse prevention, tool efficiency ranking, and context source utilisation into a single Behavioral Intelligence view. The activation moment: "your agent has 3 problems right now."

**Components:**

**T3a — Anomalies Inbox + Taxonomy:** Fleet-wide issue surfacing. Reads pulse_log, chisel_drift, errors, context_health, config_events, circuit_breakers, plugin_tracking, l2_trending, token_logs, session_checkpoints. Categorises anomalies into taxonomy:

| Type | Detection | Example | Status |
|------|-----------|---------|--------|
| `no_tools` | Session ran without tool calls | "Agent ran 5 turns without calling any tools" | ✅ v0.4.0 |
| `high_cost` | Cost spike vs baseline | "Turn cost 3.2σ above 7d average" | ✅ v0.4.0 |
| `long_gaps` | Latency between turns | "15min gap between turns — agent may be stuck" | ✅ v0.4.0 |
| `retry_loops` | Repeated tool failures + retries | "Tool X failed 8 times in 3 turns" | ✅ v0.4.0 |
| `context_pressure` | Context window approaching limit | "Context at 85% of window — 3 skills at risk of eviction" | 🔴 Deferred to v0.5.0 — requires model→window_size mapping table (not yet built) |

**T3b — Context Health Score (0–100):** Single number per agent answering "is my agent's brain healthy right now?" Computed from: memory bloat, drift delta, context window utilisation trend, error rate, sources-skipped ratio. Warning <70, alert <50.

**T3c — Agent Relapse Prevention:** Timeline view correlating SOUL.md edits, plugin installs/removes, config changes with degradation signals (drift spikes, error bursts, context health drops). Answers "what changed and broke things?"

**T3d — Tool Efficiency Ranking:** Derived from post-turn webhook data. Ranks every tool/skill by: cost per call, error rate, latency impact, success rate. Red/yellow/green. Surfaces "disable this tool" recommendations.

**T3e — Context Source Utilisation Tracker:** Tracks which skills/memory sections are actually used per turn vs loaded by default. Surfaces "these 2 skills add 1,400 tokens but are rarely used — remove from defaults."

**What's already built:**
- Most data sources exist (pulse_log, chisel_drift, errors, circuit_breakers, token_logs)
- Post-turn webhook — ✅ built
- Context Health Score — spec'd as §27
- Anomalies Inbox — spec'd as §33

> ⚠️ **Data quality precondition:** The anomaly detection engine requires clean data to produce meaningful results. Currently: `errors` = 1,265 rows (all `watch_probe_failed` — noise), `circuit_breakers` = 0 rows (never fired), `token_logs.cost` = $0.00 (not populated). **T3a should not be deployed until v0.3.2 Fix 2 (watch probe) and Fix 5 (circuit_events migration) are complete.** The engine can be built in parallel with those fixes, but the anomaly feed will produce garbage until data is clean.

**What needs building:**
- Anomaly detection engine (taxonomy classifier)
- Context Health Score computation
- Relapse Prevention timeline
- Tool Efficiency ranking
- Context Source Utilisation tracker
- Unified Behavioral Intelligence dashboard tab

**Free:** Anomaly feed + severity + explanation + Context Health Score (24h)
**Pro:** Push alerts + auto-heal integration + anomaly attribution + resolution tracking + never-pruned history

**Effort:** ~4d (1d anomaly engine + 1d health score + 1d relapse + 1d dashboard)

---

### 3.T4 Unified Agent Data Model (🔴 v0.4.0 — new)

**Tagline:** *One query, one payload, every view.*

**What it is:** A shared backend query layer (`agent_profile_service`) that feeds Tracing, Evaluation, Behavioral Monitoring, and all existing views. Single `/api/agent/{id}/profile` endpoint returns a composite payload: health, tokens, traces, evals, anomalies, context health, tool efficiency, source utilisation.

**Why this exists:** Currently, each dashboard tab makes separate API calls to different endpoints. The fleet view calls `/api/agents`, the token tab calls `/api/tokens/log`, the health tab calls `/api/pulse`. This means: N+1 queries per page load, inconsistent data (different timestamps), and no unified view of an agent's state.

> ⚠️ **Build order:** T4 should be built **before or in parallel with T1's dashboard views.** All new dashboard code (waterfall, anomaly feed, quality trends) should use the unified endpoint from day one, not be migrated to it later. Building T1's waterfall against the current multi-endpoint architecture means rewriting it when T4 ships.

**What needs building:**
- `agent_profile_service.py` — composite query layer
- `/api/agent/{id}/profile` endpoint
- Migrate existing dashboard tabs to use the unified endpoint
- Caching layer (5s TTL) to avoid hammering pulse.db

**Free:** Unified endpoint + composite payload
**Pro:** Same (no gating — this is infrastructure)

**Effort:** ~1d

### 3.65 Conversational Dashboard Copilot (Feature #80)

**Status:** ✅ Live — FAB trigger + Page Agent panel, themed to ObserveCo dark tokens

**Integration:** One `<script>` tag in the dashboard's `<head>`. No backend changes. No new API endpoints. Page Agent reads the existing DOM and executes actions via JavaScript in the page context.

**Tagline:** *Your dashboard, now with a conversational operator. Heal, compare, filter, summarize — all in natural language.*

**What it is:** Page Agent — an in-page JavaScript GUI agent — embedded in the ObserveCo dashboard. Operators can type or speak commands instead of clicking through tabs, tables, and charts. The agent uses the operator's own LLM (Ornith, OpenAI, etc.) — no cloud dependency, no data leaving the machine.

**How it works under the hood:**

```
Operator: "Heal the degraded agents and show me the new fleet health summary"
  → Page Agent reads the DOM (fleet cards, status dots, heal buttons)
  → Identifies degraded agents (red/yellow status dots)
  → Clicks each heal button, waits for htmx response
  → Re-reads the updated DOM
  → Summarizes the new health state to the operator
```

**Key design decisions:**
- Uses `?autoInit=false` — Page Agent loads but does NOT auto-show a UI panel. The operator can activate it via `window.PageAgent` in the console, or a future UI affordance.
- Uses the `custom-ollama/ornith:latest` model — the operator's local Ornith instance. No API key needed, no cloud calls.
- Page Agent runs in the existing auth context (`__OBSERVECO_TOKEN` is already on the page). All DOM actions go through the same fetch interceptor.

**What it enables that doesn't exist today:**

| Pattern | Before (no copilot) | After (Page Agent) |
|---------|--------------------|--------------------|
| Heal + verify | Click Heal tab → click button → wait → check fleet view | "Heal all degraded agents and show me the new health summary" |
| Cross-agent comparison | Manual: open each agent's modal, read numbers, compare | "Compare Hermes vs OpenClaw token usage over 24 hours" |
| Config changes | Find the right settings form, fill it in | "Set circuit breaker to 5 failures for all agents" |
| Error triage | Scroll error timeline, mentally summarize | "Summarize the top 3 errors from the timeline" |
| Routine monitoring | Keep dashboard open, scan manually | "Pause monitoring on hound and alert me on Telegram if it fails" |
| Voice commands | Not possible | Voice while coding: "Pause monitoring on agent 'hound' and alert me on Telegram if it fails again" |

**Known limitations (ponytails):**
- **Canvas charts:** Page Agent can't see `<canvas>`-rendered chart data. If sparklines render in Canvas, the agent sees only the container element. Fix: ensure chart data is also present in the DOM (aria-labels, data attributes, or a hidden data table).
- **htmx partial swaps:** Agent reads DOM at command time. If a section swaps via htmx after the agent has already read it, the agent may use stale state. Workaround: call `agent.execute()` in an htmx callback after swap.
- **Multi-page workflows:** Basic Page Agent is single-page. If heal operations redirect, the chrome extension or MCP server is needed to maintain context. For htmx single-page apps this is less of an issue.
- **Async execution:** Page Agent makes its own LLM calls. The dashboard doesn't wait. Healing "in one sentence" means the operator says it, Page Agent acts, operator reviews — not fully autonomous recovery.

**Free:** Included. One script tag, no backend changes.
**Pro:** Same (no gating — this is a client-side UI enhancement).

**Effort:** 1h (1 script tag, 1 config line)

---

## 6. Not Building (Explicit Scope Boundaries)

| Feature | Why Not | Notes |
|---------|---------|-------|
| Never-Say-Die 4-layer fallback | Tied to Hermes Agent runtime | Replace with auto-heal (#3.15) |
| Kepler dual SOULs consistency | Operational protocol, not product | Internal SOP, not in ObserveCo scope |
| Intent-aware loading as standalone ObserveCo feature | Requires OpenClaw SDK runtime plugin | Built as separate `@observeco/clawforge-plugin` Node.js package |
| Original Caveman/CHISEL naming | Superseded by ObserveCo | Only relevant for historical context |
| Compromised API key detection (S10) | ObserveCo monitors agents, not API provider usage | Hard boundary — see §14.6. Users must set provider-level usage caps |
| Data integrity / cache poisoning detection (S16) | Application-layer concern. Corrupted data produces normal agent behavior | Hard boundary — see §14.6 |
| Fully automated spend-rate enforcement | False positive on automated kill = trust destroyed. Kill switch is manual v1, auto-escalation v2+ opt-in only | Layered approach — see §14.5 |
||| Inline API proxying / request blocking | **Deprecated.** Former §42 MITM proxy removed 2026-06-19. Replaced by SDK-sidecar (`observeco instrument`) — out-of-band, framework-aware, zero crash risk. Cloud LLM tracking uses post-turn webhook (§43) + provider billing API fallback (§44). | ~~See `specs/adr-proxy-attribution.md`~~ → `specs/adr-proxy-attribution.md` (deprecated — proxy removal record) |
|| **Compliance-grade audit trail** | Immutable, cryptographically signed audit log of every agent action (SOC 2, HIPAA). Requires append-only storage, hash chain signing, 1-7 year retention. | **Deferred.** Shared by every OSS tool in this space — no competitor under $50K/year offers it. If enterprise users demand it, partner with a compliance-focused logging platform rather than building in-house. |
|| **Cross-agent signal flow visibility (G3.1)** | Track signal delivery between agents, detect sent-but-never-acknowledged, surface "alive but not producing." Requires agent-side instrumentation across Hermes + OpenClaw ecosystems. | **Deferred.** Already spec'd as G3.1 in master plan §14.3. ~5d effort. Deferred until post-launch — single-machine observability covers 90% of target market. |

---

## 7. Architecture Overview

### 7.1 Process Architecture — Two Independent Processes

ObserveCo runs as **two independent processes** that share a common SQLite database. They are NOT a client-server pair — they are peer processes with different responsibilities.

```
┌──────────────────────────────────────────────────────────┐
│                  YOUR SYSTEM                              │
│                                                          │
│  ┌─────────────────────┐   ┌──────────────────────────┐  │
│  │  observeco watch    │   │  observeco dashboard     │  │
│  │  (data collector)   │   │  (web UI reader)         │  │
│  │                     │   │                          │  │
│  │  PID: 23941         │   │  PID: 62697              │  │
│  │  Started: 11:33am   │   │  Started: when you need  │  │
│  │  Runs: continuous   │   │          the UI          │  │
│  │                     │   │                          │  │
│  │  What it does:      │   │  What it does:           │  │
│  │  • Probes agents    │   │  • Serves /api/* from    │  │
│  │    every 30s        │──┼──▶  pulse.db (read-only)  │  │
│  │  • Writes pulse,    │   │  • Renders HTML pages    │  │
│  │    trims, drift,    │   │  • Auto-launches watch   │  │
│  │    garden to        │   │    if it's not running   │  │
│  │    ~/.observeco/    │   │  • Read-only consumer    │  │
│  │    pulse.db         │   │                          │  │
│  └─────────────────────┘   └──────────────────────────┘  │
│         │                              │                 │
│         └──────────┬───────────────────┘                 │
│                    ▼                                     │
│        ┌────────────────────────┐                        │
│        │  ~/.observeco/pulse.db │                        │
│        │  (shared SQLite)       │                        │
│        │  - watch daemon WRITES │                        │
│        │  - dashboard READS     │                        │
│        └────────────────────────┘                        │
└──────────────────────────────────────────────────────────┘
```

**Critical rules for anyone working on the system:**

| Rule | Why |
|------|-----|
| **Watch daemon is the data collector. Dashboard is a read-only consumer.** | The watch daemon writes pulse, trims, drift, garden, pathway. The dashboard only reads. Killing the dashboard does NOT stop data collection. |
| **Killing/restarting the dashboard is safe.** | The watch daemon continues collecting data. When the dashboard restarts, it resumes reading from the same DB — no data is lost, no probes are missed. |
| **Killing the watch daemon IS visible.** | Data stops updating. Dashboard shows stale data with "last seen Xm ago". Phase banner detects the gap. |
| **Dashboard auto-launches the watch daemon** on startup if it's not running (`_ensure_watch_running()`). | If you `observeco watch stop` and then `observeco dashboard`, the dashboard will re-launch the watch daemon automatically. |
| **Multiple dashboard instances can accumulate** if server.py is invoked directly (not through `observeco dashboard`). | Each `uvicorn.run()` without going through the CLI creates a separate process on a different port. Always use `observeco dashboard` to start. |

### 7.2 Data Flow Diagram

```
Your AI Agents (any framework)
    |
    ├── Hermes agents: Pulse health via pgrep + SOUL.md analysis
    ├── OpenClaw agents: Pulse health via health endpoint
    └── Custom agents: CLI health check commands or HTTP endpoints
    |
    ▼
[observeco watch] — background daemon, every 30s
    ├── Auto-discover new agents from Hermes/OpenClaw configs
    ├── Probe each agent (health URL, command, or process name)
    ├── Record pulse + circuit breaker state → SQLite
    ├── Analyse SOUL.md → token breakdown → SQLite
    └── (Planned) Trigger heal on dead detection
    |
    ▼
[SQLite — ~/.observeco/pulse.db]
    ├── pulse_log — alive/dead/error history
    ├── circuit_breakers — failure count, trip state, cooldown
    ├── chisel_trims — token breakdown per agent per tick
    ├── chisel_drift — 7-day per-component trend
    ├── clawforge_profiles — MEMORY.md size, skill count
    ├── clawforge_loads — intent-aware loading stats
    ├── clawforge_garden — memory debt score, duplicate count
    ├── agent_configs — registered agents
    └── errors — agent error log
    |
    ▼
[observeco dashboard] — FastAPI + htmx, local web UI
    ├── Fleet view: all agent cards with health dots
    ├── Token breakdown: per-agent bar chart + drift
    ├── Memory Garden: OpenClaw memory debt score
    ├── Alerts: circuit trips, drift breaches
    └── Heal: manual (free) / auto (Pro)
```
|
|---
|
### 3.64 `observeco discover` — One-Click Gap Scanner (🔴 Spec)

**Tagline:** *See what you're not monitoring. Fix it with one click.*

**User story:**

1. User opens the ObserveCo dashboard
2. Sees a "Discover" button (or auto-loading gap badge) in the header
3. Clicks it → a panel slides open showing a list of gaps:
   - "News Digest cron is not monitored — **Add**"
   - "Kepler config found but not tracked — **Add**"
   - "Ollama process running but not registered — **Add**"
4. Clicks **Add** on any row → agent is registered, monitoring starts, row disappears
5. When all gaps are resolved: "✅ No gaps found — everything is being monitored"

**That's it.** No CLI. No read-only report. The user sees a problem and fixes it in the same place.

**What the scanner checks:**

| Scan | Source | What it checks |
|------|--------|---------------|
| **Cron jobs** | `~/.hermes/cron/jobs.json` | Scheduled jobs not in DB — suggests adding as agents |
| **Agent configs** | `~/.hermes/config.yaml`, `~/.hermes/profiles/*/`, OpenClaw profiles | Agent profiles found in config but not in DB |
| **Running processes** | `psutil.process_iter()` | Processes that look like agents (Python/Node agent frameworks, listening on common ports) not in DB |

**Dashboard widget:**

A compact card in the dashboard header area showing:
- **Badge:** "3 gaps found" with severity colour (green = 0, yellow = 1-5, red = 6+)
- **Expandable list:** Each row: `[Name] — [reason]` + **Add** button
- **Add button:** Calls `POST /api/agents/add` with the detected name/framework, then removes that row from the list
- **Auto-refresh:** Re-scans on dashboard page load (cached 5min)
- **Empty state:** "✅ No gaps found — everything is being monitored" in green

**Implementation rules:**

- **Backend:** `src/observeco/discover/scanner.py` — scan logic. `GET /api/discover/gaps` returns gap list. `POST /api/discover/add` registers a single gap as an agent
- **Dashboard:** htmx widget in `index.html` — fetches gaps on load, renders list with Add buttons. Add button fires htmx POST, server returns updated row (removed) or error
- **No new dependencies** — stdlib + `psutil` (already a dep)
- Cron scan reads `~/.hermes/cron/jobs.json` via `dirs.hermes_home()`
- Agent config scan reads `~/.hermes/config.yaml` + profile dirs via `dirs.hermes_home()`
- Process scan uses `psutil.process_iter()` with keyword filtering
- Cross-references against `db.get_agents()` to find gaps
- 5min in-memory cache on the GET endpoint

**States & Edge Cases:**

| State | Behaviour | Output |
|-------|-----------|--------|
| Gaps found | List of gaps with Add buttons | Each row: name + reason + Add button |
| Everything tracked | Empty state | "✅ No gaps found — everything is being monitored" |
| No Hermes | `hermes_home()` returns None | "ℹ Hermes not detected. Run `observeco init` to set up." |
| No DB | No agents registered yet | "ℹ No agents in database yet. Gaps will appear once agents are configured." |
| Add succeeds | Row removed from list, agent starts monitoring | Row fades out, badge count decrements |
| Add fails | Row stays, error shown inline | "Failed to add — [reason]" in red on that row |
| Partial scan | Some sources readable, some not | Shows what it could read, flags unreadable sources |
| Timeout | Process scan hangs | 5s timeout, skips gracefully with note |

**Lifecycle:**

| Phase | Behaviour |
|-------|----------|
| Start (first run) | Scans everything, shows all gaps |
| Run (steady state) | Same scan on page load — stateless, no daemon |
| Crash | N/A — stateless API endpoint, no daemon |
| Reboot | N/A — no persistent state |

**Success metric:** Dashboard gap widget loads in <500ms (cached). Add button registers the agent and removes the row in <1s. User can go from "see gap" to "fixed" in one click.

**Free:** Full widget, all scans, one-click add.
**Pro:** Same (no gating — this is a core onboarding/awareness feature).

**Cross-references:**
- `auto_detect.py` — existing 3-tier agent discovery (process-based). `discover` is broader (cron + configs + processes) and adds the one-click fix loop.
- `observeco init` — first-run setup. `discover` is the ongoing version: run anytime to find and fix what's missing.
- `dirs.hermes_home()` — single source of truth for Hermes paths (Feature #64).

ponytail: Process scan uses `psutil` keyword filter. Ceiling: misses agents running as non-Python/Node processes. Upgrade path: add process_iter with full name matching against known agent frameworks.

---
|
|## 8. Build Roadmap

| Phase | Features | Cumulative Effort | Notes |
|-------|----------|-------------------|-------|
| **Now** | Everything in ✅ Live — 12 features | ✅ Done | Ship current code |
|| **v0.4.0 — Hermes Beachhead** | **Phase 1:** Unified Agent Data Model (T4, ~1d). **Phase 2:** Wire OTEL listener to pulse.db + Enable hermes-otel plugin (~1d). **Phase 3:** Tracing Layer (T1, ~3d). **Phase 4:** Behavioral Monitoring (T3, ~4d). Evaluation Layer (T2) deferred to v0.5.0. | **~11d** | ✅ **Shipped.** True agent-specific observability for Hermes on macOS. |
|| **v0.5.0 — Capability Monitoring Layer** | **Canary** — regression tripwire (9 tasks, lm-eval backend, hang tracking, 60s timeout). **Grid** — capability measurement (τ-bench + SWE-bench, model × harness config × task matrix, Wilson CI, trajectory flags). **Config-aware baselines** — file hashing, auto-segment on change. **Drift detection** — statistical honesty layer, sequential/statistical test before alert. **Adapter strategy** — ship one adapter (Hermes), publish open spec. **Scoring model** — deterministic signals + user assertions (default), opt-in LLM-as-judge (v0.6.0). | **~4d** (built) | **Current focus.** Observation without judgment is just logging. This layer adds the judgment. |
||| **v0.6.0 — Intelligence Layer** | Log-to-suggested-tasks (auto-generation with review/approve), opt-in LLM-as-judge scoring, alert integrations, Context Health Score, Relapse Prevention, Tool Efficiency ranking | **~6d** | Builds on v0.5.0 data. Makes intelligence claims real. |
||| **v0.7.0 — Adaptive Harness Layer** | Experience-based harness adaptation (MemoHarness 2026): dual-layer experience bank (per-case diagnoses + global patterns from pulse_log/errors/token_logs), per-case retrieval by similarity, 6 editable control dimensions (context, tools, orchestration, memory, decoding, output). Fixes: apply-edit no-op, frontier inheritance, candidate tracking. | **~4d** | Builds on v0.6.0 harness optimizer. Makes harness evolution actually work. |
| **Phase 0** (blocks public release) | `hermes_home()` in `dirs.py`, Lazy path constants, Refactor hardcodes → dirs functions, Remove personal artifacts, Fix `require_pro()`, Delete `invocation_counter.py`, Add BYOK to `llm_service` + `chisel/llm_client.py` | **~12h** | **Ship-stoppers.** Without these, the product has Sean's agents, Sean's files, a broken license gate. |
| **Phase 1** (beachhead readiness) | Dashboard banner, Graceful degradation, Env var consolidation, `observeco init`, `observeco discover` | **~9h** (14h cum.) | Product works on `pip install && observeco dashboard` on any Mac Mini with Hermes. |
| **Phase G1** (safety) | Self-monitoring budget cap, Manual kill switch, Circuit breaker config, Turn-rate alerting, Tool-count metric, Threat model docs | ~5.5d | Token-rogue guardrails. |
| **Phase 2** | Extended history, Auto-heal dashboard UI, Skill audit, Generic discovery layer | ~3d | Zero-dependency + generic discovery. |
| **Phase 3** | System prompt compression, Push alerts dashboard UI | ~5d | |
| **Phase G2** (Month 2) | Fleet spend alerts, Alert→wait→auto-stop, Lineage tracking, Output consistency, Drift lookback | ~10.5d | |
| **Phase G3** (Month 3+) | Signal flow visibility, Auto-escalation, Model attribution | ~9d | |
| **Future: Multi-framework** | OpenClaw runtime plugin, A2A adapter, Cross-framework dashboard, Claude Code/Ollama generic discovery | ~15d | **Deferred to post-v1.0.** Hermes is the priority. |

**Total planned effort:** ~10d (v0.4.0) + ~6d (v0.5.0) + ~12h (Phase 0) + ~9h (Phase 1) + ~5.5d (G1) + ~3d (Phase 2) + ~5d (Phase 3) + ~10.5d (G2) + ~9d (G3) + ~15d (Multi-framework) = **~65-70 days across all features**.

ponytail: Phase 0/1 effort is ~18h (~2.5d) — once these ship, the product is publishable as "ObserveCo for Hermes — free forever, no signup."

### What Ships When

| Shipment | What | Value to User |
|----------|------|---------------|
| **v0.4.0 — Hermes Beachhead** | Tracing Layer (T1), Evaluation Layer (T2), Behavioral Monitoring (T3), Unified Agent Data Model (T4), OTEL listener wired to pulse.db, Hermes OTEL plugin enabled | **True agent-specific observability.** See every turn, every tool call, every subagent. Know if your agent is performing well, not just alive. |
| **v0.5.0 — Capability Monitoring Layer** | Canary (regression tripwire), Grid (capability measurement), config-aware baselines, drift detection, adapter spec, deterministic scoring | **Observation without judgment is just logging.** Know if your agent is getting worse — and why. |
|| **v0.6.0 — Intelligence Layer** | Log-to-suggested-tasks, opt-in LLM-as-judge, alert integrations, Context Health Score, Relapse Prevention | **Proactive intelligence.** Your agent has 3 problems right now — here they are. |
|| **v0.7.0 — Adaptive Harness Layer** | Experience-based harness adaptation (MemoHarness 2026): dual-layer experience bank, per-case retrieval, 6 control dimensions | **Harness evolution that actually works.** Your agent learns from its own execution history. |
| **Phase 0** (D+0) | Generic Hermes discovery via `hermes_home()`, zero personal artifacts, `require_pro()` fix | **Blocks public release.** Without this, first non-Sean user sees broken product. |
| **Phase 1** (D+1) | Agent invocation banner, graceful degradation, `observeco init`, env var docs | **First public-ready release.** Any Mac Mini Hermes user gets full ObserveCo. |
| **Phase G1** (D+2) | G1 guardrails + generic discovery | Safety layer v1. |
| **Phase 2** (D+7) | Extended history + auto-heal + Skill audit | Users see token history, agents auto-recover, skill bloat measured |
| **Phase 3** (D+14) | System prompt compression, Push alerts | |
| **Phase G2** (Month 2) | Fleet alerts, auto-stop escalation, lineage tracking, output consistency, drift lookback | Pro-level safety escalation. |
| **Phase G3** (Month 3+) | Signal flow visibility, sophisticated auto-escalation, per-turn model attribution | Ecosystem-level deadlock detection + escalation policy engine. |
| **Future: Multi-framework** (Post-v1.0) | OpenClaw runtime plugin, A2A adapter, Cross-framework dashboard, Generic discovery | Multi-framework support. Deferred until Hermes beachhead is validated. |

---

## 9. Go-to-Market & Launch Strategy

**Source:** `specs/marketing-plan.md` (full psychological analysis)
**Core thesis:** Nobody buys monitoring because they want monitoring. They buy because of three invisible forces: **Token Anxiety** (\"how much am I burning right now?\"), **Ignorance Dread** (\"my agents could be failing and I'd never know\"), **Competence Shame** (\"I built this and I don't understand it\").

### 9.1 Launch Sequence

| Phase | Timing | Action | Purpose |
|-------|--------|--------|---------|
| **The Ghost** | D-7 | Anonymous comment on r/openclaw pricing thread: \"I built a tool that shows where every token goes. DM for early access.\" | 3-5 beta testers who ASKED for it, not sold to |
| **The Tease** | D-3 | One X post: pain statement, no link, no screenshot. Forces people to ask. | 50+ \"where can I get this?\" replies — audience primed |
| **The Revelation** | D-0 | X Article (3,000 words) + Show HN + Reddit posts + X thread. All point to `pip install observeco && observeco dashboard` | Three channels, three jobs: depth, legitimacy, relatability. Same story. |
| **The Silence** | D+0 → D+14 | Reply to every comment within 1h. Fix bugs within 24h. Ship nothing new. Let yellow banners build frustration. | Community pressure builds naturally. By D+7, users ask \"when auto-fix?\" without us prompting. |
| **The Payoff** | D+14 | v1.1 launch leads with a community comment asking \"why doesn't it just fix it?\" | Fulfillment, not announcement. The user who asked becomes the hero. |

### 9.2 Channels (0 Stars — Only These Three)

| Channel | Job | Why It Works |
|---------|-----|-------------|
| **HN Show HN** | Legitimacy | Zero karma gate. One frontpage = 500+ visitors. HN users LOVE discovering unknown projects. The sniff test: working `pip install`, real screenshots, open source MIT, authentic story. |
| **X (Sean's personal account)** | Authenticity | \"I built this\" on a personal account is 10x more credible than a brand account with 0 followers. X Article = depth layer (3,000 words, 7 screenshots, 1 GIF). |
| **Reddit (r/LocalLLM, r/AI_Agents)** | Relatability | These are the exact users — running local agents, feeling the pain, already discussing token costs openly. Reddit is where the pricing thread lives. |

**Deferred channels:** Discord (wait for 500+ stars — empty channels kill credibility), blog/website (GitHub README IS the website), YouTube (only if users ask for it), LinkedIn brand account (never — \"indie dev builds tool\" is authentic; \"ObserveCo announces\" at 0 stars is cringe).

### 9.3 Tension Mechanics (How v0 Makes Users Crave v1.1)

Every yellow banner in v0 is deliberate:

| Surface | What User Sees | Effect |
|---------|---------------|--------|
| Fleet view | \"Agent Kepler: 3 memory errors detected. Suggested: restart with memory cap.\" | **Trust** (tool correctly identified) + **Frustration** (won't just fix it) |
| Drift tracking | \"15% growth this week. Suggested: run chisel trim.\" | **Awareness** + **Desire** (\"make it automatic\") |
| Circuit breaker | \"Circuit open. 3/3 failures in 5 minutes. No auto-retry until acknowledged.\" | **Relief** (no cascade) + **Impatience** (\"why can't I set auto-heal?\") |
| Memory garden | \"Kepler: 7 duplicates, 2 contradictions. Suggested: run garden --apply.\" | **Shame** (memory is a mess) + **Dependence** (rely on the suggestion) |

**Critical rule:** Every banner ends with **the exact command that will work in v1.1.** Users learn the syntax by reading. The transition from \"see\" to \"fix\" is invisible.

**v1.1 countdown:** Footer on every dashboard page: *\"v1.1 coming ~[date]: self-healing (✅), snapshot docs (⚠️ needs 7+ days live data), MCP queries (❌ deferred). [Learn more](GitHub issue).\"* Do NOT say \"coming soon\" — give a specific date.

### 9.4 Distribution Assets Required

| Asset | Produced D-3 | Purpose |
|-------|-------------|---------|
| 7 screenshots of **anxiety moments** (not product features) | ✅ | 1. Red dot + yellow banner. 2. Bloated token breakdown. 3. Circuit breaker tripped. 4. Drift chart. 5. Memory garden. 6. Yellow observation banner. 7. Terminal GIF |
| Terminal GIF: `pip install` → `observeco dashboard` → agents visible in 15 seconds | ✅ | Shows speed to value. No config steps, no waiting, no loading states. |
| X Article: \"Your AI agents are getting dumber every day\" | ✅ | 3,000 words, 7 screenshots, 1 GIF. Sits on X permanently as the single story reference. |
| HN Show HN post | ✅ | Title hits Token Anxiety directly. Real screenshots from real agents (not mockups). Comparison table. |
| Reddit posts (r/LocalLLM + r/AI_Agents) | ✅ | Adapted to each sub's community tone. |

### 9.5 Anti-Patterns (Don't Do These)

| Don't | Instead |
|-------|---------|
| \"We\" language (0 stars → corporate voice is fake) | **\"I built this\"** — one person solving their own problem |
| Feature-table marketing (spec sheet ≠ story) | **\"My agents burned $120/day. I couldn't see why. So I built a dashboard.\"** |
| \"Enterprise-ready\" language (no one needs SSO yet) | **\"Local-first. pip install. No cloud.\"** |
| Announcing v1.1 at launch (tells users to wait) | Let yellow banners build the tension. Users discover the roadmap through frustration. |
| Building a Discord before 500 users (empty = dead) | GitHub Issues IS the community. Every issue is public, searchable. |
| Multiple channels on launch day (none done well) | One X Article (depth), one HN post (legitimacy), one Reddit post (relatability). |
| Pricing before trust (mentions of $9/$49 in launch copy) | Free tier for 30 days. Pricing in GitHub README footer only. The product sells itself first. |
| Asking for the sale (\"Sign up now\" etc.) | **\"pip install observeco\"** — zero friction, zero commitment. |

### 9.6 Success Criteria

| Metric | Target | Means |
|--------|--------|-------|
| GitHub stars (D+1) | 100-300 | HN frontpage hit. Below = didn't resonate. |
| GitHub stars (D+14) | 500-1,000 | Organic growth + v0 value. \"Real\" metric before v1.1. |
| GitHub stars (D+15) | 800-2,000 | v1.1 bump. Tension-to-payoff conversion. |
| X Article views (D+7) | 5,000-15,000 | Article is the permanent reference. |
| Users asking \"when auto-fix?\" | 10+ public comments by D+7 | Tension is working. |
| PyPI downloads (week 1) | 500-2,000 | HN/Reddit conversion. |
| v1.1 installs (first 48h) | 300-1,000 | v0 users returned. |

### 9.7 Word of Mouth Engine

Every user has three natural sharing moments:

1. **Install** (60s): Screenshot fleet view. \"3 agents, 1 dead, I didn't know.\"
2. **Drift discovery** (first day): \"My agent grew 15% this week — had no idea.\"
3. **Observation banner** (first failure): \"Tool detected a memory leak and won't fix it. Waiting for auto-heal.\"

**Make sharing frictionless:** Dashboard has a \"Share\" button that copies a PNG to clipboard (no login, no cloud). Pre-filled text: *\"My agents have been running blind. Finally found a dashboard that shows what's happening. pip install observeco\"* CTA points to GitHub.

### 9.8 Milestone Progression

| Stars | What Changes | What Stays |
|-------|-------------|------------|
| 0-50 | Individual replies to every comment. GitHub Issues = community. | No Discord, no website, no newsletter. |
| 50-200 | First user screenshots replace mockups. Add GitHub Discussions. | No paid ads, no influencer outreach. |
| 200-500 | Landing page (observeco.com → GitHub). CONTRIBUTORS guide. | No Discord yet. Wait for demand. |
| 500-2,000 | v1.1 lands — inflection point. Discord if >10 msgs/day on GitHub. | Still no paid ads. Still one person. |
| 2,000+ | Consider community site. | Authenticity is the moat. Don't lose it scaling the wrong way. |

## 10. Feature Value Pitches

**Method:** 5-point structure (What It Is → How It Helps AI Agents → How It Helps Humans → Why It's Free → Tier Justification)
**Applied:** The 3 Meta-Principles — Brand Alignment → Free Feature Scarcity → Compelling Reason to Purchase

### ✅ Live Features

Live features are fully built and included in `pip install observeco[dashboard]`. These pitches explain why each one exists in the product and why it's free.

#### 1. Fleet View

**What It Is**
A dashboard screen that groups every registered agent by **type** (Agents · Services · Workflows), not by framework. Each agent shows as a card with five clickable metric rows: Health, Guard, Errors, Brain size, and Composition. Agents are auto-discovered from config scans and manual registration. No framework labels in fleet view — all agents appear in one unified grid regardless of their underlying framework.

**How It Helps AI Agents**
Zero. Agents don't know they're being watched.

**How It Helps Humans**
Before Fleet View, checking agent status meant: `ps aux | grep hound`, opening Kepler's dashboard, SSH-ing into a server, or asking Telegram "is everything running?" That's 4+ separate actions every time you want a pulse. Fleet View collapses it to one glance.

Without it: you check agents individually whenever something feels off. With it: green dots tell you everything is fine. Red dots need attention — and you see *what kind* (dead, bloated, slow) without opening a terminal.

**Why It's Free**
**Front door.** Fleet View is the user's first experience with ObserveCo. If they install it and see a blank page or a loading spinner, they uninstall. The card-based layout with live status dots is the "aha" moment: *"All my agents in one place."*

Gate 2 test: If Fleet View were removed, would a new user notice within 3 sessions? Yes — it's literally the main screen. It earns its place as the front door.

---

#### 2. Pulse Check

**What It Is**
Every 30 seconds, the watch daemon probes each registered agent (HTTP health URL, shell command, or process name). Result (alive/dead/error) written to SQLite with latency and error message. The foundation every other monitoring feature depends on.

**How It Helps AI Agents**
Indirect. A dead agent gets detected within 30s instead of waiting for the next human message. Faster detection means faster recovery.

**How It Helps Humans**
Without Pulse Check: you find out an agent is dead when it doesn't respond to your message — minutes or hours later. With Pulse Check: you know within 30 seconds. The drill-down shows *why* it's dead (connection refused vs timeout vs HTTP 500), which tells you what to do differently.

**Cost anchor:** "Pulse probes are HTTP requests, not LLM calls — they spend zero tokens. Each probe costs $0.00. The value is speed of detection: 30 seconds instead of hours."

**Why It's Free**
**Prerequisite.** Everything else depends on pulse data: Safety Guard reads it, Error History stores it, Heal Button checks it, Auto-Heal (Pro) triggers from it. If pulse were hidden behind Pro, every downstream feature would break. It's the foundation, not the premium.

---

#### 3. Safety Guard

**What It Is**
After 3 consecutive pulse failures, the guard stops probing that agent and enters cooldown (~4 hours). After cooldown, it tries one probe. If the agent recovered, monitoring resumes. If not, cooldown restarts.

**How It Helps AI Agents**
Zero. Agents don't know they're being checked or un-checked.

**How It Helps Humans**
Without the guard: a dead agent gets checked 2,880 times/day, writing 5,760 rows to SQLite (~432 KB/day). Your logs fill with noise, your DB grows, and every dashboard query has to scan through thousands of redundant rows.

With the guard: ~8 checks/day, ~16 writes (~1.2 KB/day). You see exactly the 3 failures that triggered the trip, then silence.

| Metric | Without guard | With guard |
|--------|--------------|------------|
| HTTP checks/day | 2,880 (every 30s × 24h) | ~8 (3 to trip + 1 per 4h cooldown) |
| DB writes/day | 5,760 (2 per check) | ~16 |
| DB growth/day | ~432 KB | ~1.2 KB |
| DB growth/year | ~158 MB | ~438 KB |
| **Reduction** | — | **99.7% fewer writes** |

**Cost anchor:** "Each probe is a GET /health — costs $0.00 regardless of volume. The real cost is 5,760 SQLite writes per day per dead agent. That's 432 KB of DB growth. Every dashboard load scans through these rows. The guard prevents this accumulation."

**Why It's Free**
**Noise filter.** Without the guard, ObserveCo itself would be annoying — filling your error history with 2,880 identical "connection refused" entries per day. The guard prevents the product from being its own worst enemy. Paying to silence product noise is bad product.

**Pro upgrade:** Configurable thresholds (change 3 failures to N) + auto-recovery timer (change cooldown period). This is **configuration depth** — power users pay for tuning.

#### 4. Startup Race Mitigation (🔴 Planned)

**What It Is:** A grace period inserted before the watch daemon runs its first pulse cycle on any agent. Without this, the daemon's 30s probe fires before a freshly-restarted agent has finished bootstrapping — detecting a "dead" agent that was simply still booting.

**Problem:** Agent restarts (manual heal, auto-heal, or user-initiated) take variable time. A Hermes agent might need 15s to load model weights; a Docker container might need 40s to pull a new image. The watch daemon probes every 30s. If an agent takes 35s to boot, it catches a probe at 30s → pulse failure → guard trips → heal fires → restart → infinite restart loop.

**Solution:** Per-agent `startup_grace_period` (default: 60s) — during boot sequence, the pulse daemon skips probes and marks the agent as `"BOOTING"`. After the grace period, normal probing begins.

**How it works:**

1. **Heal's `_execute_action("restart", ...)` writes a stamp file** `~/.observeco/startup_grace/<agent_name>.stamp` with `{restarted_at: epoch_s, grace_period: 60}` **before** executing the restart
2. **Pulse daemon checks stamp files** on each 30s cycle. If `<agent_name>.stamp` exists and `now - restarted_at < grace_period`, the probe is skipped and the state is reported as `"BOOTING"` (separate state from `"ALIVE"`/`"DEAD"`)
3. **Stamp cleanup:** After grace period expires, the stamp is stale. Pulse daemon deletes it when `now - restarted_at > grace_period`, then continues with normal probing
4. **Dashboard displays "BOOTING" state** as a blue dot (not green/red) with remaining grace time: `"🚦 BOOTING (43s remaining)"`

| State | Dot | Behavior |
|-------|-----|----------|
| Normal probing | 🟢/🔴 | Standard pulse check |
| Within grace period | 🔵 BOOTING | No probe, no guard trip, no heal trigger |
| After grace → pulse success | 🟢 | Normal monitoring resumes |
| After grace → pulse failure | 🔴 | Standard guard trip + heal if configured |

**Edge cases:**
- **Manual restart (SSH/kill -9):** No stamp file written → no grace period → normal probe detects dead → normal heal. This is correct — if the user killed the agent manually, they want the system to detect it.
- **Pulse daemon restarts mid-grace:** Stamp files survive because `~/.observeco/startup_grace/` is on disk, not memory. On daemon restart, all stamps are re-read and remaining grace periods respected.
- **Stale stamp from crashed daemon:** If the daemon crashes after writing a stamp but before the agent restarts, the stamp stays on disk. Pulse daemon's cycle 0 (first probe loop) scans stamps, deletes any where `now - restarted_at > max(3600, grace_period*10)` as stale orphans. Agents with an orphan stamp get a normal probe immediately.
- **Multiple restarts during grace:** If heal restarts an agent again while it's still in its grace period, the stamp is overwritten with the new `restarted_at`. This is correct — the clock resets.

**Acceptance Criteria:**
- [ ] AC1: Agent within grace period shows `"BOOTING"` state, not dead
- [ ] AC2: After grace, agent with working process shows `"ALIVE"`
- [ ] AC3: After grace, agent with dead process shows `"DEAD"` and triggers guard/heal
- [ ] AC4: Manual kill (no stamp) → no grace → immediate DEAD detection
- [ ] AC5: Daemon restart during grace → stamps re-read, remaining grace respected
- [ ] AC6: Stale orphan stamps cleaned up on daemon cycle 0
- [ ] AC7: Dashboard shows blue dot + remaining seconds for booting agent

**Implementation:**
- New file: `src/observeco/pulse/startup_grace.py` (optional — could inline in `watch.py` cycle logic)
- DB schema: no new table — stamp files are JSON on disk in `~/.observeco/startup_grace/`
- Pulse daemon cycle change: in the per-agent probe loop, check stamp file before deciding to probe
- Heal change: `_execute_action("restart", ...)` writes stamp before `os.system()` or subprocess call
- Dashboard change: pulse API returns state enum (`ALIVE | DEAD | BOOTING | ERROR`) → frontend renders blue dot for BOOTING

**Self-test:**
```python
# python -c "
# import tempfile, os, time, json
# d = tempfile.mkdtemp()
# stamp = os.path.join(d, 'test_agent.stamp')
# ts = time.time()
# open(stamp, 'w').write(json.dumps({'restarted_at': ts, 'grace_period': 60}))
# assert os.path.exists(stamp)
# time.sleep(0.2)
# assert time.time() - ts < 60  # still in grace
# os.remove(stamp)
# assert not os.path.exists(stamp)
# print('OK')
# "
```

#### 5. Brain Analysis

**What It Is**
A unified page showing every agent's system prompt broken into 5 components (identity, skills, memory, tools, guidance). Shows token totals, 7-day drift, savings comparison (Original vs Lite vs Full compression), manual compression with preview/apply, auto-watch daemon (Pro), and Token Optimiser (Pro).

**How It Helps AI Agents**
Direct. The Token Optimiser identifies skills that never fire and guidance rules that never activate — candidates for removal. Leaner prompts → faster responses, lower cost.

**How It Helps Humans**
Without Brain Analysis: humans don't know how bloated their prompts are or which component is the problem. With it: composition breakdown shows each component's share, savings comparison shows real dollars, Optimiser recommends pruning.

**Value quantification (6 agents, 50 turns/day, DeepSeek $0.15/M input):**

| Dimension | No compression | Lite (Free) | Full + Optimiser (Pro) |
|-----------|---------------|-------------|------------------------|
| Fleet tokens/turn | 44,700 | 34,866 (-22%) | 23,691 (-47%) |
| Dollars saved/year | $0 | $27 | $57 |
| Effort | None | Manual preview/apply | Auto-watch (set and forget) |

**Cost anchor:** "Tokens cost money. Lite saves ~$27/year for 6 agents. Full + Optimiser saves ~$57/year — 2x savings for $9/mo."

**Why The Observation Side Is Free**
**Quality of life + UX completion.** Every user wrote their SOUL.md — they should see what's in it. Component explanations make the dashboard make sense.

**Pro upgrade:** Full compression (35% vs 22%), auto-watch daemon, Token Optimiser (up to 47%). **Automation premium.**

**Nod test:** "Without Pro, you manually run compression (2 min per edit). With Pro, every SOUL.md edit triggers automatic compression. Lite saves 22%; Full saves 35%. Worth $9/mo if you edit SOUL.md more than once a month."

---

#### 6. Error History

**What It Is**
Per-agent error log with timestamp, message, and severity. Drill-down modal categorises errors and provides plain-English verdict.

**How It Helps AI Agents**
Zero.

**How It Helps Humans**
Without Error History: you see a red dot and guess. With it: every error has a message, category, and verdict explaining what to do.

**Why It's Free**
**Quality of life.** If your agent is down, you need to know why. 24h covers "what happened while I was sleeping."

**Pro upgrade:** Never-pruned history + weekly trend charts + regression detection. **Data depth** — trend analysis requires history.

**Nod test (new users):** "Without Pro, you see last night's errors. With Pro, you see trending — is it getting better or worse?"
**Nod test (established):** "24h shows 3 errors. 90d shows 2/week → 15/week — your agent is degrading. That's worth $9/mo."

---

#### 7. Heal Button

**What It Is**
Manual dashboard button: diagnose dead agent, attempt restart, write critical flags on failure. Uses circuit breaker (3 retries, 4h cooldown).

**How It Helps AI Agents**
Direct. Restarts without SSH.

**How It Helps Humans**
Without Heal: SSH → pgrep → kill → restart (30-60s). With Heal: one click (2s).

| Dimension | Manual (SSH) | Heal Button |
|-----------|-------------|-------------|
| Time | 30-60s | 2s |
| Context switch | High | Low |

**Why It's Free**
**Prerequisite.** Auto-Heal (Pro) is "trigger Heal button automatically."

**Pro upgrade:** Auto-Heal — automatic on dead detection. **Trust escalation.**

**Nod test:** "Without Pro, you click Heal when you notice. With Pro, agents crashing at 3am are back up by 3:00:35. Worth $9/mo if any agent runs while you sleep."

---

#### 8. In-Dashboard Alerts

**What It Is**
Banners in the dashboard UI when circuits trip, drift exceeds threshold, or heartbeat misses. Free tier shows alerts with **discovery gap badges** — the time between "happened" and "discovered" is visible.

**How It Helps AI Agents**
Zero.

**How It Helps Humans**
Without: you check each card for red dots, unsure what happened while you were gone. With: a banner shows every alert from the last 24h, each with a discovery gap badge ("happened 03:15, discovered 07:00 — 3h 45m gap"). A cumulative banner totals the undiscovered downtime: "8h 47m across 4 alerts."

This discovery gap is intentional — it makes the cost of pull-based alerting visible and directly motivates the push upgrade.

**Why It's Free**
**Noise filter + quality of life.** Charging to see what broke is bad UX. But the free version adds a visible friction point (the discovery gap) that shows the user what they're missing.

**Pro upgrade:** Push alerts (Telegram, webhook, email) — zero discovery gap. **Interruption value** — alerts that find you instantly.

---

#### 9. Memory Garden

**What It Is**
Scans OpenClaw MEMORY.md for duplicates, contradictions, stale entries. Reports debt score (0-100).

**How It Helps AI Agents**
Direct. Cleaner memory → better context.

**How It Helps Humans**
Without: memory grows indefinitely, human doesn't know what's stale. With: debt score + suggestions.

| Dimension | Manual | Memory Garden |
|-----------|--------|---------------|
| Time to audit | 5-15 min | CLI command |
| Thoroughness | Misses 30-50% | 100% |

**Why It's Free**
**UX completion.** OpenClaw experience is incomplete without it.

---

#### 10. ClawForge CLI

**What It Is**
Four commands: `profile`, `load`, `garden`, `history`.

**Why It's Free**
**Architectural.** OpenClaw runtime tools shipped with ObserveCo for convenience.

---

#### 11. All CLI Commands

**What It Is**
Full CLI suite: `pulse check`, `pulse circuit`, `chisel trim`, `chisel drift`, `chisel skills`, `clawforge profile/load/garden/history`, `dashboard`.

**Why It's Free**
**Architectural.** Local-first means terminal access. Charging for `--help` violates the brand.

---

#### 12. Local SQLite

**What It Is**
All data in `~/.observeco/pulse.db`. Zero cloud.

**Why It's Free**
**Architectural.** Paying for local storage contradicts "your agents, your control."

---

### 🔴 Planned Features

#### 14. System Prompt Compression (`observeco chisel compress`)

**What It Is**
Reads SOUL.md, applies Chisel compression algorithms, writes compressed version. Two tiers: **Lite** (Free) compresses guidance rules — ~22% reduction. **Full** (Pro) compresses guidance + memory culling + skill dedup + context refactoring — ~35% reduction. Manual preview/apply (Free), auto-watch daemon (Pro) that triggers on every SOUL.md edit.

**How It Helps AI Agents**
Direct. Fewer input tokens per session means faster response times across every turn. A 4,200-token SOUL.md compressed to 2,730 tokens (Full) saves 1,470 tokens per session — every session, every agent, every day. On local models (qwen3.5), that's measurable latency reduction per turn.

**How It Helps Humans**
**Free experience:** Run `observeco chisel compress --dry-run`. See a before/after comparison: "Original: 4,200 tokens → Lite: 3,276 tokens (−22%) — $15/year saved." You preview, you apply. Next time you edit SOUL.md, the bloat returns. You run it again — if you remember.

**Pro experience:** Edit your SOUL.md at any time. Within 60 seconds, auto-watch detects the change, runs Full compression, and writes the compressed version. You never think about it. Dashboard shows: "Last compressed: 3 mins ago. Cumulative savings this month: $1.80 (6 agents × 3 edits × 1,470 tokens saved)."

| Dimension | Uncompressed | Lite (Free — manual) | Full (Pro — auto-watch) |
|-----------|-------------|---------------------|------------------------|
| Tokens/turn | 4,200 | 3,276 (−22%) | 2,730 (−35%) |
| Fleet (6) $/year (DeepSeek) | $70 | $55 (−$15) | $46 (−$24) |
| Fleet (6) $/year (Claude Sonnet) | $1,385 | $1,080 (−$305) | $900 (−$485) |
| Effort | — | 1 manual command per edit | Zero (set and forget) |
| Recovery after edit | Bloat returns immediately | Manual re-run | Auto-triggered within 60s |
| Components compressed | None | Guidance rules only | Guidance + memory culling + skill dedup + context refactor |

**Saving rates relative to Pro price ($108/year):**

| Provider | Lite (Free — manual) | Full (Pro — auto-watch) |
|----------|---------------------|------------------------|
| DeepSeek | Saves $15/year → 1.4x breakeven | Saves $24/year → 2.2x breakeven |
| Claude Sonnet | Saves $305/year → 3.8x breakeven | Saves $485/year → 5.5x breakeven |

**Compression methods per tier:**

| Method | Lite (Free) | Full (Pro) | Technique |
|--------|------------|------------|-----------|
| Guidance rule dedup | ✅ | ✅ | Merge identical rules, remove redundant constraints |
| Guidance rule rewording | ✅ | ✅ | "do not ever under any circumstances do X" → "never do X" |
| Memory entry culling | ❌ | ✅ | Remove entries >30d stale with zero recent invocations |
| Skill description truncation | ❌ | ✅ | 120-char cap (already exists in `build_skills_system_prompt()`) |
| Cross-skill dedup | ❌ | ✅ | Detect skills with overlapping capabilities, merge references |
| Context refactoring | ❌ | ✅ | Reorder sections for minimal token overhead (tools before memory, etc.) |
| Section-level drift detection | ❌ | ✅ | Compare token count per section vs last compression — flag sections that grew |

**How it connects to Brain Analysis and Token Tracking (§14):**
- Brain Analysis tells you *which* skills are bloated. Compression *fixes* them.
- Token Tracking tells you *how much* bloat costs per turn. Compression *reduces* the cost.
- **The three features form a cycle:** Token Tracking identifies the problem → Brain Analysis pinpoints the cause → Compression applies the fix.
- When a Brain Analysis auto-scan detects a skill that crossed threshold (>3,000 tokens or >30% growth), the compression auto-watch can trigger a Full compression pass on that skill's parent SOUL.md — chaining the two Pro features.

**Cost anchor:** "Token savings are real. Full compression saves $24/year per fleet of 6 agents on DeepSeek — 2.2x the Pro price. On Claude Sonnet it saves $485/year — 5.5x Pro. On local models, the benefit is speed: 22% faster session starts across every agent. Every millisecond of latency reduction compounds across every turn, every agent, every day."

**Why Lite is Free**
**Quality of life + discovery.** Guidance compression is a universal need — every SOUL.md has redundant rules. Running `--dry-run` once shows the user the exact dollar value of compression. The same pattern as Brain Analysis's CLI scan: prove the problem exists, then sell the automation.

**Pro upgrade:** Full compression (35% vs 22%) + auto-watch daemon (triggers on every SOUL.md edit). **Automation premium + depth premium.** Same pattern as Brain Analysis: manual tool is free, continuous vigilance is Pro.

**Tier Justification**
**Depth + automation.** Lite compresses guidance only — the easiest, safest compression pass. Full compresses everything: guidance, memory, skills, context structure — each pass requires different analysis and carries different risk (memory culling can remove a reference the human still needs; skill dedup can merge two skills that should stay separate). Auto-watch makes Full compression practical: if memory culling flags a false positive, the next edit auto-corrects. Manual Full compression would be risky without a safety net. Auto-watch IS the safety net.

**Implementation**

**Phase 1 — Compression engine (existing, ~day)**  
Chisel compression logic already exists in `src/observeco/chisel/`. Confirms: Lite (guidance dedup + rewording) works, Full (memory culling + skill dedup + context refactor) works. CLI commands `observeco chisel compress --dry-run` and `--apply` exist. **No change needed for compression engine.**

**Phase 2 — Auto-watch daemon (~1 day)**  
`observeco chisel compress --auto-watch` — Pro-only subcommand. Creates a `watchdog`-based file watcher on `~/.hermes/agents/*/SOUL.md` and OpenClaw equivalent. On any `on_modified` event:
1. Wait 5 seconds (debounce — avoids triggering on partial writes)
2. Run Full compression on the modified SOUL.md
3. Write compressed version to `~/.hermes/agents/<name>/SOUL.md.chisel` (or overwrite in-place based on config)
4. Log: `"[chisel-watch] compressed SOUL.md for hound: 4,200 → 2,730 (−35%)"`
5. If compression savings exceed configurable threshold (default: >15%): optionally fire push alert

**Free tier check:**
```python
if config.tier == "free":
    print("Auto-watch requires Pro. Run `observeco chisel compress` manually.")
    sys.exit(0)
```

**Phase 3 — Dashboard card (~1 day)**  
Add "Chisel Compression" card to dashboard (Pro-only):
- Last compressed timestamp per agent
- Cumulative savings: "Saved 18,200 tokens across 6 agents this month ($1.80)"
- Compression history chart: per-agent token count over last 12 compressions
- "Auto-watch enabled" indicator with agent list and last-run timestamps
- Manual trigger button: "Compress Now" (applies Full + logs)

**Phase 4 — Brain Analysis integration (~0.5 days)**  
When a Brain Analysis auto-scan fires a threshold alert, the push alert payload includes a "Compress" CTA: "Skill `database` crossed 3,000 tokens. Run `observeco chisel compress --agent hound` or enable auto-watch to prevent recurrence."

**Total effort:** ~2.5 days (1 auto-watch daemon + 1 dashboard card + 0.5 integration)

**Nod test:** "Without Pro, you manually run `observeco chisel compress` when you remember — and bloat that accumulated since your last edit stays compressed. With Pro, every SOUL.md edit triggers auto-compression within 60 seconds. Full compression saves 35% vs Lite's 22% — and auto-watch catches new bloat before it compounds. On DeepSeek, Full saves $24/year per fleet. On Claude Sonnet, $485/year. Worth $9/mo if you edit SOUL.md more than once a month."

---

#### 14. Per-Turn Token Tracking

**What It Is**
Each agent POSTs token usage after every conversation turn via webhook — agent name, turn timestamp, total tokens, component breakdown (identity, skills, memory, tools, guidance), and provider used. Dashboard shows per-turn timeline (24h Free / full history Pro), component breakdown, cost-per-turn, and trend detection.

**How It Helps AI Agents**
Zero. Agents POST data but don't read it.

**How It Helps Humans**
**Free experience:** See today's 24 columns — each column is one agent turn, height = total tokens consumed. Hover to see exact count. Component breakdown shows which section (skills, tools, memory, etc.) is the biggest drain. Knows today's spend.

**Pro experience:** Same data, but with full history from install. At month 3:
- Component trend: "Your `skills` section grew from 3,200 to 5,100 tokens over 90 days — +59%"
- Per-agent cost trend: "Kepler spent $4.20 last week vs $2.80 the week before — +50%. Driver: 3 hallucinated turns with 45K token cost each."
- Anomaly detection: "Kepler turn at 03:47 consumed 41,200 tokens — 6.2x its 90-day average of 6,600"
- Threshold alert: "Hound crossed $2.00/day average — investigate before month-end surprise"

| Dimension | Without | Free | Pro |
|-----------|---------|------|-----|
| Cost visibility | Budget only | Today's per-turn spend | Full history + trend + anomaly |
| Granularity | None | Per-turn totals + component breakdown | Same, with component-level trend over time |
| Optimization | Guesses | Data-driven (today's data) | Data-driven (full trend — "this section grew X%") |
| Anomaly detection | None | None | "Turn cost >3σ from rolling average → flagged" |
| Component trend | None | Snapshot (current breakdown) | "Skills grew 59% over 90 days" |
| Threshold alerts | None | None | Push when agent crosses configurable daily/weekly budget |
| Fleet comparison | None | None | Side-by-side per-agent cost rank |

**Cost anchor:** "Agents POST token usage via webhook — each POST is <1KB. A fleet of 6 agents at 50 turns/day generates ~300KB/day. ~9MB/month. Zero cloud cost to store. The premium is the trend engine and anomaly detection that reads it."

**Shared infrastructure with Extended History:** Token tracking shares the same data retention policy (§18) and the same `~/.observeco/pulse.db` SQLite database. The `token_logs` table has a `retention_tier` column. Free queries filter `WHERE timestamp > now() - interval '7 days'`. Pro queries drop the filter. The L2 baseline engine reads token component trends as a secondary signal — same cron, same query pattern, different time range. **Building Extended History builds 60% of this feature.**

**Pro upgrade:** Never-pruned history + fleet comparison + component trend (per-section drift over time) + anomaly detection (>3σ turn cost) + budget threshold alerts. **Data depth + vigilance.** Same tier boundary as Extended History — Free sees today, Pro sees the trajectory.

**Shared table schema (extends pulse.db):**
```sql
-- Already exists for pulse. Token data stored in same DB.
CREATE TABLE token_logs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  agent_name TEXT,
  turn_id TEXT,
  total_tokens INTEGER,
  identity_tokens INTEGER,
  skills_tokens INTEGER,
  memory_tokens INTEGER,
  tools_tokens INTEGER,
  guidance_tokens INTEGER,
  provider TEXT,       -- 'deepseek', 'claude', 'openai', etc.
  cost REAL,           -- computed from provider rate * total_tokens
  anomaly_score REAL   -- NULL for Free; computed for Pro (deviation from rolling avg)
);

CREATE INDEX idx_token_logs_agent ON token_logs(agent_name, recorded_at DESC);
CREATE INDEX idx_token_logs_anomaly ON token_logs(recorded_at, total_tokens) WHERE anomaly_score IS NOT NULL;
```

**Implementation**

**Phase 1 — Webhook + storage (~1 day)**  
`POST /api/tokens/log` endpoint already exists (from original Per-Turn spec, now extended with model/latency/tool_calls/topic_id). Confirms: accept `{agent_name, turn_id, total_tokens, components:{...}, provider, model, latency_ms, tool_calls, topic_id}`, write to `token_logs` table. Free tier stores with `anomaly_score = NULL`. No change needed.

**Phase 2 — Component trend engine (~1 day)**  
Extends the same L2 baseline cron from §18 Phase 2. After computing RSS/P95/output baselines, also computes:
- Per-agent, per-component token trend over last N days
- Component growth rate: `(current - baseline) / baseline * 100`
- Anomaly flag: total_tokens > rolling_avg * 3 (simple 3σ heuristic)

```python
# In l2_baseline cron, after pulse baselines:
for agent in registered_agents:
    # 7d baseline (Free and Pro)
    baseline = db.execute("SELECT avg(total_tokens), stddev(total_tokens) FROM token_logs WHERE agent_name=? AND recorded_at > now() - 7d", agent)
    # Pro: full-history baseline
    if config.tier == "pro":
        full_baseline = db.execute("SELECT avg(total_tokens), stddev(total_tokens) FROM token_logs WHERE agent_name=?", agent)
        # Component trends (needs 14d+)
        component_trends = db.execute("""
            SELECT skills_tokens, memory_tokens, tools_tokens, guidance_tokens
            FROM token_logs WHERE agent_name=? 
            AND recorded_at > now() - 90d
            GROUP BY strftime('%W', recorded_at)
        """, agent)
        # Detect growth: compare week 1 avg vs week 12 avg
```

**Phase 3 — Budget thresholds + push alerts (~1 day)**  
Configurable per-agent: `max_daily_tokens`, `max_turn_cost`, `max_component_growth_pct`. When breached → push alert via existing §17 infrastructure. Alert payload includes: "Kepler: 41,200 tokens/turn — 6.2x baseline. Likely cause: repeated model hallucination loop."

**Phase 4 — Dashboard component trend chart (~1 day)**  
Extends existing 7-day drift chart to full history (Pro only). Adds:
- "Component Growth" chart: line chart per component over full history
- "Cost Trend" chart: daily cost over time with projected month-end
- "Anomaly Table": flagged turns with reason and cost impact

**Total effort:** ~4 days (1 webhook + 1 trend engine + 1 alerts + 1 dashboard). Shares 60% with §18 Extended History — if that's built first, this is ~2 days.

**Tier Justification**
**Data depth + trend detection.** Today's spend answers "how much." Full history answers "how much is this costing me over time?" — which is the question every solo operator asks when they see their API bill spike. Component trends reveal which parts of the agent are getting more expensive. Anomaly detection catches the turns that shouldn't happen. Free gives you the raw data. Pro gives you the patterns.

**Nod test:** "Without Pro, you see today's spend — 24 columns of per-turn data. With Pro, you see 90 days of per-turn, per-component data. 'Your agent spent 45K tokens this week — up from 28K last week. The driver is the guidance section which grew 60%.' Anomaly detection flags turns that cost 6x the normal. Budget threshold alerts buzz when you're trending toward a surprise bill. Worth $9/mo if your agent spend matters."

---

#### 15. Auto-Heal

**What It Is**
Watch daemon auto-triggers `run_heal()` on dead detection (Layer 1), plus trend-based proactive detection of degradation before failure (Layer 2). Detection-to-recovery: ~5 seconds for crashes, pre-emptive for degradation trends. Configurable retries, cooldown, notification. Integrated with Push Alerts (Pro): notifications fire only when all auto-heal paths are exhausted or the failure is in the 7% that needs human diagnosis — silent on success.

**The Three-Layer Coverage Spectrum**

The 1000x insight: the remaining 20% of failures don't fail suddenly — they degrade first. Memory leaks grow +6%/h for 6 hours before OOM. Stuck agents pause for 3x their response time before you notice. Hallucinating agents drift from their output baseline over hours. Every "non-crash" failure leaves a detectable signature before it becomes fatal. If we watch the trends — not the crash — we catch and auto-heal pre-emptively.

Every signal Layer 2 needs already exists in the agent ecosystem: RSS from every `ps` call (pulse files already track it), response time P95 from cron/signal timestamps (state/metrics/), output structure from signal payloads, connection status from pulse health checks. No new agents. No new daemons. Just trend tracking over existing metrics — exactly what GS-013 already defines.

| Layer | What | Detection Signal | Auto-Heal Action | Coverage | Status |
|-------|------|-----------------|-----------------|----------|--------|
| **Layer 1** · Reactive | Process crash, OOM, zombie, timeout, crash-loop | Pulse health check fails | Graceful restart (~5s) | ~75% of failures | ✅ Shipped |
| **Layer 2** · Proactive | Memory bloat | RSS growth >5%/h for 3 samples | Pre-emptive graceful restart (~90% success) | ~18% of failures | 🆕 New |
| | Stuck/deadlocked | No output >3x P95 response time | SIGABRT + core dump + restart (~80% success) | | |
| | Agent stasis | Pulse file >2× interval stale, but process alive. Common cause: `subprocess.run(capture_output=True)` masked silent health check failure. | Restart with error logging enabled. Post-restart diagnostic: check agent logs for failed subprocess.run() calls in tick(). (~90% success) | | |
| | Hallucinating | Output structure drift >3σ from 7d baseline | Restart with fallback model (~50% success) | | |
| | Upstream failure | Connection refused in first retries | Circuit breaker + buffer + backoff (~70% success) | | |
| **Human-needed** · Structured Diagnosis | Config errors, logic bugs, disk full | Auto-heal exhausts retries or can't act | Push alert with diagnostic report (not cryptic logs) | ~7% of failures | 🔍 Honest |

**Net auto-resolution rate:** Layer 1 (75%) + Layer 2 (18%) = **93% of all failures resolve without human touch.** The remaining 7% arrive with a structured diagnostic report — turning "what broke?" from 15 minutes to 30 seconds.

**Diagnostic report format (the 7%):** When auto-heal can't resolve, the push alert carries:
- **Failure class** (config error vs logic bug vs disk full vs persistent crash-loop)
- **Evidence trail** — time series of attempted heals, detected signals, model fallbacks attempted
- **Likely cause** — auto-inferred from signal patterns (e.g. "RSS returns to 500MB+ within 30min of restart → likely cache accumulation")
- **Action** — what the human should investigate (e.g. "review signal retention policy")

**How It Helps AI Agents**
Direct. Layer 1 restarts within seconds of crash. Layer 2 prevents the crash entirely. Multiple incidents per night handled without human involvement.

**How It Helps Humans**
**Free experience:** Kepler crashes at 3am. You wake at 7am, open dashboard — red dot. Dead for 4 hours. You click Heal. Recovery: 4 hours + 1 context switch.

**Pro experience (L1 — crash recovery succeeds):** Kepler crashes at 3am. Layer 1 detects and restarts at 3:00:35. You wake at 7am — green dot. Push alert never fires. Log: "Auto-healed at 03:00:40."

**Pro experience (L2 — proactive detection prevents crash):** Memory leak starts at 10pm. Layer 2 tracks RSS trend crossing >5%/h at 11pm. Pre-emptive restart at 11:05pm. RSS drops to baseline. The OOM that would have killed Kepler at 3am never happens. You never know there was trouble.

**Pro experience (L1+L2 exhausted — structured diagnosis):** Kepler OOM-crashes 3 times. Auto-heal retries exhaust. Push alert fires at 3:15 with full diagnosis: "3x restarts in 2h, RSS returns to 500MB+ within 30min. Likely cause: cache accumulation. Top candidate: signal_buffer (last 7d: 12MB → 480MB). Action: review signal retention policy." You wake at 7am already knowing what to fix.

| Dimension | 🔓 Free (no auto-heal) | 🔒 Layer 1 (crash recovery) | 🔒 Layer 1 + Layer 2 (proactive) |
|-----------|----------------------|----------------------------|--------------------------------|
| Coverage | 0% | 75% (process crashes) | 93% (crashes + degradation) |
| Detection style | You discover when you check | Reactive (after failure) | Proactive (before failure) |
| Downtime per incident | Hours (until you notice) | ~5 seconds | 0 seconds (prevented) |
| Notifications | 0 — discover in dashboard | 0 on success / 1 on stuck | 0 on success / 1 with diagnosis |
| Signal needed | None | Health check (pulse) | Trends: RSS, P95, output structure |
| Retry logic | Fixed: 3 retries, 4h cooldown | Configurable: 1-10 retries | Same, with trend-based auto-escalation |
| Human-touch failures saved/yr | 0 | ~39 (75% of 52 weekly crashes) | ~48 (93% of 52) |

**Tier Justification**
**Trust escalation + silence premium.** Manual heal is free. Layer 1 (automated crash recovery) is premium. Layer 2 (proactive degradation detection) is the same premium — it reduces the human-touch failures from ~39/year to ~4/year. Pro isn't about more notifications; it's about making those notifications rare and meaningful. Every buzz on Pro means either "all auto-heal paths are exhausted" or "this failure needs a human." That's the difference between monitoring (free) and stewardship (Pro): monitoring makes noise, stewardship filters it down to the 7% that matter.

**Nod test:** "Without Pro, every crash stays dead until you check the dashboard. With Pro Layer 1, routine process crashes heal in 5 seconds — you never know. With Pro Layer 2, memory leaks, stuck agents, and hallucinations are caught pre-emptively before they crash — you never know. 93% of all failures resolve without you. The 7% that can't arrive with a complete diagnostic report. Worth $9/mo if any agent runs while you sleep."

---

#### 16. OpenClaw Runtime Plugin

**What It Is**
Node.js plugin that replaces OpenClaw's built-in ContextEngine with an intent-aware one. Three lifecycle hooks — bootstrap, ingest, pre-response — classify each user message and load only the relevant skills, memory entries, and workspace files. Same agent quality, 40-60% fewer input tokens per turn.

**How It Helps AI Agents**
Direct. Fewer input tokens means faster time-to-first-token and lower API costs. A 12,400-token context cut to 5,200 tokens saves 7,200 tokens per turn — every turn, every agent, every day. On local models (Ollama), that's ~47% faster response start. On API models, that's ~47% lower input cost.

**How It Helps Humans**
**Free experience:** Install the plugin, set one config line (`contextEngine: "clawforge"`), restart gateway. Agent loads only relevant context per turn. Dashboard shows per-turn savings: "This session: saved 31,240 tokens across 24 turns (47% avg reduction)."

**Pro experience:** Same plugin, but with never-pruned stats, intent classifier training (learns from your actual usage patterns), fleet-wide savings comparison, and budget threshold alerts (push when agent crosses daily token budget).

| Dimension | Without Plugin | With Plugin (Free) | With Plugin (Pro) |
|-----------|---------------|-------------------|-------------------|
| Context per turn | 12,400 tok (full) | 5,200 tok (intent-aware) | Same |
| Savings per turn | 0 | ~7,200 tok (47%) | Same |
| Daily fleet cost (DeepSeek) | $0.56 | $0.23 | Same |
| Annual savings (DeepSeek) | $0 | $120/year | $120/year |
| Annual savings (Claude Sonnet) | $0 | $2,366/year | $2,366/year |
| Per-turn stats | None | 24h timeline | Never-pruned + anomaly detection |
| Intent classifier | N/A | Local TF-IDF (5 categories) | Custom trained on usage data |
| Budget alerts | None | None | Push when agent crosses daily token budget |

**Cost anchor:** "The plugin saves ~$120/year on DeepSeek and ~$2,366/year on Claude Sonnet for a fleet of 6 agents. On local models, the benefit is speed — 47% fewer tokens means faster response start. The plugin is MIT and free forever; Pro unlocks the analytics layer."

**Why It's Free**
**Community tool.** The plugin saves tokens. Gate-keeping it behind Pro defeats the purpose. Users need to experience the savings before they'll pay for deeper analytics. Same pattern as every other ObserveCo free feature: free = the tool, Pro = the intelligence layer.

**Nod test:** "Without Pro, you install the plugin and save 47% on input tokens — dashboard shows per-turn savings for 24h. With Pro, you see never-pruned history, trained intent classifier, fleet comparison, and budget alerts. Worth $9/mo if your agent spend matters and you want to optimize further."

**Implementation**
- Phase 1 (~2d): Plugin scaffold + bootstrap hook + ContextEngine registration
- Phase 2 (~2d): Ingest hook + local TF-IDF intent classifier (5 categories)
- Phase 3 (~1.5d): Pre-response demotion hook + stats reporting to ObserveCo
- Phase 4 (~1.5d): Dashboard integration (savings timeline, intent distribution)
- **Total:** ~7 days

**Depends on:** OpenClaw SDK (public API only), ObserveCo `POST /api/tokens/log` endpoint (from §14)
**No OpenClaw source changes required.**

---

#### 17. Push Alerts

**What It Is**
Alert delivery module pushes to Telegram, webhook, or email when circuits trip, drift breaches, or heartbeat misses. **Integrated with Auto-Heal:** on routine crashes, the system restores without alerting you — push fires only when auto-heal exhausts its retries and the circuit trips. Free users see the same alerts in-dashboard with **discovery gap badges** (happened 03:15, discovered 07:00 — 3h 45m gap).

**How It Helps AI Agents**
Zero.

**How It Helps Humans**
**Free experience:** Open dashboard at 7am. See 4 alerts with discovery gaps totalling **8h 47m**. You know there was trouble, but only after it's long over.

**Pro experience (routine crash):** Kepler crashes at 3am. Nothing buzzes. At 7am you open the dashboard — green dot. Log: "Auto-healed at 03:00:35." You don't even know there was trouble.

**Pro experience (stuck crash):** Kepler crashes at 3am. Auto-heal fails 3 times. Circuit trips. Telegram buzzes at 3:15: "Auto-heal failed — Kepler unreachable. Manual intervention required." You know before your agent fails twice.

| Dimension | Free (in-dashboard) | Pro (push + auto-heal) |
|-----------|-------------------|------------------------|
| Alert discovery latency | When you open dashboard (hours) | <3 seconds from circuit trip — **but only on failure** |
| Routine crash behavior | Dead until you check | Healed silently — **zero alerts** |
| Stuck crash behavior | Dead until you check | Push alert immediately |
| Signal-to-noise ratio | Poor — every crash visible | Excellent — alert means "something is wrong; auto-heal couldn't fix it" |
| Undiscovered downtime (24h) | **8h 47m** across 4 alerts | **0s** — either healed or alerted instantly |
| Context switches | High (you check proactively) | Low — alert finds you **only when something needs you** |
| Alert channels | Dashboard only | Telegram · Discord · Webhook · Email |
| Customizable thresholds | Fixed | Configurable per alert type |

**Cost anchor:** "Each notification costs $0.00. The cost IS the interruption — it has real attention value. Push alerts are premium precisely because we gate them: on Pro, alerts only fire when the system can't fix itself. That makes every buzz meaningful."

**Tier Justification**
**Interruption value + intelligent filtering.** Free shows alerts when you look. Pro closes the gap between "happened" and "known" to zero — **but only when it matters**. Routine crashes heal silently. You never know. A stuck crash buzzes immediately. You know before it becomes a problem. The tier boundary isn't just pull vs push — it's noise vs signal.

**Nod test:** "Without Pro, a circuit trip at 3am waits until you open the dashboard at 7am — 4 hours of unknown downtime. With Pro, routine crashes heal silently; you never know. Stuck crashes buzz your Telegram immediately. Worth $9/mo if any of your agents operate while you're away from the dashboard."

---

#### 18. Extended History

**What It Is**
Dashboard queries expanded from 24h to 7d (Free) or full history from install (Pro — never pruned). Powers Auto-Heal Layer 2's trend baseline engine, Pulse trend charts, and error regression detection.

**How It Helps Auto-Heal L2**
Direct — the trend baseline engine depends on it. L2 detects degradation by comparing current signals against rolling baselines. Those baselines need history depth:

| Baseline type | Min data needed | What's detectable | Free | Pro |
|--------------|----------------|-------------------|------|-----|
| RSS memory | 7 days of hourly samples | Growth rate >5%/h sustained | ✅ 7d (min viable) | ✅ Full history (tighter thresholds) |
| P95 response time | 14 days | Latency drift >2σ | ❌ (pruned at 7d) | ✅ Full (detects slow degradation) |
| Output structure | 21 days | Hallucination drift >3σ | ❌ | ✅ Full |
| Combined multi-signal | 30 days | Correlated degradation patterns | ❌ | ✅ Full |

**The compounding insight:** At day 1, Free and Pro baselines are identical. At week 2, Free still has 7 days (pruned). Pro has 14 days — enough to detect P95 drift. At month 3, Pro has 90 days — enough to detect seasonal patterns, weekly cycles, and slow-moving correlation failures. **Pro's value compounds with time. The longer you run it, the smarter L2 gets.**

**How It Helps Humans**
**Free experience:** 7-day window. Good for "what happened this week." Can't answer "is this getting worse over time?" because week-1 baseline is already pruned.

**Pro experience:** Full history since install. At month 3:
- Error trend: "3/week in month 1, 15/week in month 3 — your agent is degrading"
- RSS baseline: "Baseline was 200MB in month 1, now 340MB — you have a leak"
- L2 detection: "This week's drift pattern matches the 3 weeks before last OOM event"

| Dimension | Free | Pro |
|-----------|------|-----|
| Query window | Up to 7 days | Full history from install |
| Pulse history | 7d | Never pruned |
| Error history | 7d | Never pruned |
| Drift/token history | 7d | Never pruned |
| L2 trend baselines | 7d (minimal — RSS only) | Rolling 7d/14d/21d/30d/90d |
| L2 detection coverage | RSS bloat only (Layer 1 + partial L2) | Full L2: memory, P95, output, upstream |
| Data storage | ~3MB/week per fleet | ~3MB/week per fleet (same — just not deleted) |

**Data Retention Policy**

| Data type | Free retention | Pro retention | Pruning mechanism | Storage cost |
|-----------|---------------|---------------|-------------------|--------------|
| Pulse checks (alive/dead/error) | 7 days | Never pruned | SQLite DELETE WHERE timestamp < cutoff | ~0.5MB/agent/month |
| Error history | 7 days | Never pruned | Same | ~0.3MB/agent/month |
| Drift snapshots | 7 days | Never pruned | Same | ~1.2MB/agent/month |
| Token usage logs | 7 days | Never pruned | Same | ~0.8MB/agent/month |
| L2 trend samples (RSS, P95) | 7 days (kept for baseline calc) | Never pruned | Same | ~0.1MB/agent/month |
| L2 baseline cache | Recomputed daily from 7d | Recomputed daily from full history | Cache keyed by date range | In-memory, ~20KB |

**Implementation**

**Phase 1 — Data layer (no UI changes, ~1 day)**
```python
# Retention config (read from config.yaml, tier-aware)
retention:
  free:
    pulse: "7d"     # DELETE WHERE timestamp < now() - interval '7 days'
    errors: "7d"
    drift: "7d"
    tokens: "7d"
    l2_samples: "7d"
  pro:
    pulse: "unlimited"   # never prune
    errors: "unlimited"
    drift: "unlimited"
    tokens: "unlimited"
    l2_samples: "unlimited"
```

Add a daily pruning cron: `observeco pulse prune` — runs at 3am, reads `config.retention`, deletes rows older than cutoff for current tier. Pro tier exits immediately (no rows to prune). The cron checks the agent's license key / tier config to determine which retention to apply — same code path, different cutoff.

**Phase 2 — L2 baseline engine (uses existing data, ~2 days)**
- `observeco l2 baseline --agent <name>` — computes rolling baselines from stored history
- `observeco l2 baseline --all` — computes for all registered agents
- Runs as a cron every 4 hours (or on-demand when L2 detection triggers)
- Output: `~/.observeco/l2_baselines.json` — cached for L2 trigger decisions
- Free: computes only RSS baseline from 7d window
- Pro: computes all 4 baselines (RSS, P95, output, upstream) from full history

**Phase 3 — Dashboard query expansion (~1 day)**
- Change `?range=7d` default to `observeco dashboard --range=7d` (Free) / `--range=full` (Pro)
- Pro query: `SELECT * FROM pulse WHERE agent = ?` — no time filter
- Free query: same, with `AND timestamp > now() - interval '7 days'`
- Same SQLite, same query path, different WHERE clause. Zero cloud.

**Total effort:** ~4 days (1 + 2 + 1)

**Tier Justification**
**Data depth + compounding value.** 7 days of history is enough to answer "what happened this week." Full history enables trend detection — which feeds directly into Auto-Heal L2's baseline engine. The first month of Pro looks like Free. By month 3, Pro knows your agent's seasonal patterns. Free doesn't have enough data to build those baselines because week 1 is already pruned by the time week 3 rolls around. **Pro's value compounds. Free's value is the same on day 1 as day 100.**

**Cost anchor:** "90-day history for 6 agents fits in ~4MB of SQLite. Zero cloud cost. The premium isn't storage — it's the trend data that feeds L2 detection, error regression, and degradation alerts. You're paying for compound insight, not bytes."

**Nod test:** "Without Pro, every week prunes to 7 days — you can see what happened, but you can't see what's trending. L2 detects RSS bloat (needs 7d) but not P95 drift (needs 14d) or hallucination drift (needs 21d). With Pro, history accumulates from day 1. By week 2, L2 has 14 days of P95 — drift detection activates. By month 3, L2 has 90 days — it knows your agent's seasonal patterns and catches slow-moving failures Free never sees. Worth $9/mo if you plan to run agents for more than a week."

---

#### 19. Glossary & FAQ

**What It Is**
In-dashboard "?" icons explaining every metric: one-line definition, detailed explanation, FAQ.

**How It Helps AI Agents**
Zero.

**How It Helps Humans**
Without: "🔴 Dead," "Circuit OK," "Drift +7%" are meaningless. With: every term has a lay explanation.

**Why It's Free**
**UX completion.** Dashboard doesn't make sense without explanation. Removing it breaks the experience.

---

#### ~~20. Skill Audit (`observeco chisel skills`)~~ — ~~Merged into Brain Analysis~~

**What It Is**
Scans `~/.hermes/skills/*/SKILL.md`, measures each skill's token cost, reports worst offenders ranked. Free: manual CLI scan on demand. Pro: auto-scan weekly + drift tracking + token thresholds + push alerts on bloat.

**How It Helps AI Agents**
Direct. Bloated skills load into every session — every agent turn, every cron, every interaction. Trimming reduces per-session token cost across the entire fleet. A single bloated skill at 4,200 tokens adds 8.4M tokens/year at 50 turns/day — $1.26/year on DeepSeek, $42/year on Claude Sonnet. Scale that across 40+ skills and it compounds fast.

**How It Helps Humans**
**Free experience:** Run `observeco chisel skills`. See a ranked table: "weather: 4,200 tokens, last used 3 months ago. database: 3,100 tokens, +60% in 4 weeks." You manually prune. Three weeks later, the bloat is back and you don't know.

**Pro experience:** Weekly auto-scan fires every Monday. Drift tracking compares each scan: "database: 3,100 → 4,900 tokens (+58% in 2 weeks). Threshold alert: 'database skill crossed 3,000 tokens — consider pruning or reviewing rules.'" Push alert delivers to Telegram before next session starts.

| Dimension | Before cleanup | Free (manual trim) | Pro (auto-watch) |
|-----------|---------------|-------------------|-----------------|
| Tokens/session (6 agents) | 44,700 | 26,820 (-40%) | 17,880 (-60%) |
| $/year (DeepSeek $0.15/M) | $124 | $73 (-$51) | $47 (-$77) |
| $/year (Claude Sonnet $3/M) | $2,476 | $1,460 (-$1,016) | $940 (-$1,536) |
| Effort | — | 1 manual CLI run | Zero (set and forget) |
| Bloat discovered | Never (no baseline) | When you remember to scan | Within 7 days of bloat starting |
| Drift visibility | None | Snapshot only | Trend chart: "this skill grew 40% in 2 weeks" |
| Threshold alerts | None | None | Push to Telegram when skill crosses limit |

**Saving rates relative to Pro price ($108/year):**

| Provider | Free (manual trim) | Pro (auto-watch) |
|----------|-------------------|-----------------|
| DeepSeek | Saves $51/year → 5.6x breakeven | Saves $77/year → 8.5x breakeven |
| Claude Sonnet | Saves $1,016/year → 10.2x breakeven | Saves $1,536/year → 15.4x breakeven |

**Cost anchor:** "Zero tokens to run the scan itself. The saved resource is tokens consumed every session — every agent turn for every agent. Trimming the top 10 skills saves $51/year on DeepSeek alone (5.6x the Pro price). On Claude Sonnet, it saves $1,536/year (15.4x the Pro price). The scan is free. The automation and drift tracking are Pro."

**Detection signals tracked per skill (stored in `~/.observeco/skill_audit.db`):**

| Signal | Source | Used for | Drift period |
|--------|--------|----------|-------------|
| Token count | SKILL.md loaded + rendered | Ranked table, threshold alerts | Each scan |
| Section breakdown | identity, skills, memory, tools, guidance | Composition analysis, section-level drift | Each scan |
| Last used timestamp | Skill invocation log (cron/signal history) | Staleness detection, "consider pruning" | Daily |
| Usage frequency | Invocations per 7d rolling window | "Used 0x in last 30 days" flag | Weekly |
| Token/turn contribution | (Skill token count) × (usage frequency) | Cost-per-skill ranking | Weekly |
| Section-level drift | Δ tokens per section vs last scan | "This section grew 200 tokens" | Each scan |

**Tier comparison table:**

| Feature | 🔓 Free | 🔒 Pro |
|---------|---------|--------|
| Manual scan (`observeco chisel skills`) | ✅ | ✅ (same CLI) |
| Ranked worst-offenders table | ✅ | ✅ |
| Section breakdown per skill | ✅ | ✅ |
| Cost-per-skill calculation | ✅ | ✅ |
| Auto-scan (weekly cron) | ❌ | ✅ |
| Drift tracking (comparison vs last scan) | ❌ | ✅ |
| Token threshold alerts (Telegram) | ❌ | ✅ |
| Bloated skill alert on circuit trip | ❌ | ✅ (fires with Auto-Heal push alert context) |
| Trend chart (token count over last 12 weeks) | ❌ | ✅ |

**Tier Justification**
**Discovery vs automation.** The CLI scan shows the problem exists — run it once, see which skills are bloated, prune them. But bloat is a continuous process. A skill that's 400 tokens today can be 4,000 tokens six months later as rules accumulate. Pro's auto-watch catches it the week it happens, not the month you remember. The tier boundary: one-time audit vs continuous vigilance. Drift tracking turns "I ran a scan" into "I have a trend."

**Implementation**

**Phase 1 — Scan engine (existing, ~day)**  
`observeco chisel skills` already exists as a CLI command. Confirms: scans SKILL.md per skill, tokenizes, ranks by cost. Output is a table in terminal. This forms the Free tier. **No change needed.**

**Phase 2 — Persistent storage + drift tracking (~1 day)**  
Add `~/.observeco/skill_audit.db` (SQLite, single table):

```sql
CREATE TABLE skill_scans (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  scanned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  agent_name TEXT,
  skill_name TEXT,
  total_tokens INTEGER,
  identity_tokens INTEGER,
  skills_tokens INTEGER,
  memory_tokens INTEGER,
  tools_tokens INTEGER,
  guidance_tokens INTEGER,
  last_used TIMESTAMP,
  usage_7d INTEGER,
  cost_per_turn REAL,
  tier TEXT  -- 'free' or 'pro'
);

CREATE INDEX idx_skill_scans_agent ON skill_scans(agent_name, scanned_at DESC);
CREATE INDEX idx_skill_scans_threshold ON skill_scans(tier, scanned_at, total_tokens);
```

Each scan inserts a row. Drift is computed as `SELECT total_tokens FROM skill_scans WHERE agent_name = ? AND skill_name = ? ORDER BY scanned_at DESC LIMIT 2` — simple delta.

**Phase 3 — Auto-scan cron (~1 day)**  
`observeco chisel skills --auto-watch` — Pro-only subcommand. Creates a cron that:
- Runs weekly (configurable: every 7 days)
- Runs the same scan command
- Compares against last scan (drift detection)
- If skill crossed threshold (default: >3,000 tokens or >30% growth in scan-to-scan): fires push alert
- Stores scan in `skill_audit.db`
- Re-computes trend chart data (12 rolling scans for chart rendering)

**Free tier check in cron:**
```python
if config.tier == "free":
    print("Skill audit auto-watch requires Pro. Run `observeco chisel skills` manually.")
    sys.exit(0)
```

Same code path, different tier check. Pro users get the cron. Free users get the hint.

**Phase 4 — Dashboard integration (~1 day)**  
Add "Brain Analysis" card to dashboard (Pro-only):
- Ranked table (same as CLI) with Pro badge
- Drift column: "↗ +40% vs last scan" or "↘ -12% vs last scan"
- Threshold indicator: skill over limit shown in red
- Trend sparkline: 12-week token count per skill (mini chart, inline)
- "Auto-watch enabled" toggle banner at top

**Total effort:** ~3 days (1 drift DB + 1 cron + 1 dashboard card)

**Nod test:** "Without Pro, you run `observeco chisel skills` when you remember — and skills that bloated since your last scan stay hidden. With Pro, weekly auto-scans catch bloat the week it happens. Drift tracking shows 'your `database` skill grew 60% in 4 weeks — time to review.' On DeepSeek alone, manual trimming saves $51/year. Pro auto-watch saves $77/year by catching bloat before it compounds. 5.6x the Pro price. On Claude Sonnet: 15.4x. Worth $9/mo if you have more than 10 skills."

---

### Synthesis

| Question | Free answers | Pro answers |
|----------|-------------|-------------|
| **"Is my system healthy right now?"** | Fleet View, pulse, circuit, 24h errors | Same |
| **"What happened while I was away?"** | Last 24h, 7d drift | Full history from day 1 |
| **"Is my system getting better or worse?"** | 7d drift trend | Trends + regression + patterns |
| **"What is this costing me?"** | Per-turn breakdown (24h) + component snapshot | Full history + component trend + anomaly detection + budget alerts |
| **"Will someone fix it while I sleep? Tell me only if stuck?"** | Heal button (manual) + dashboard alerts (discovery gap) | Auto-heal L1 (crash recovery ~5s silent) + L2 (proactive detection prevents 93% of failures) + push alerts **only on exhaustion** |
| **"Are my skills bloating my sessions?"** | `observeco chisel skills` manual scan | Auto-watch (weekly) + drift tracking + threshold alerts to Telegram |
| **"Is my memory/SOUL.md healthy?"** | Manual scan | Auto-watch + thresholds |
| **"Is my SOUL.md wasting tokens?"** | `observeco chisel compress --dry-run` (manual Lite) | Auto-watch Full (35%) + memory culling + skill dedup + context refactor |

**Bottom line:** Free answers "Is my system healthy right now?" Pro answers "Is my system trending healthy over time — without me watching?"

**Three gates, all passed:**
1. **Brand Alignment:** Every feature reinforces "agent observability for solo operators."
2. **Free Feature Scarcity:** Every free feature is front door, prerequisite, noise filter, quality of life, or UX completion.
3. **Compelling Purchase Reason:** Every Pro feature passes the nod test — specific problem + before/after + cost anchor. Pro is a different capability class, not "better free."

---

### 3.23 Skill Artifacts + Cards System (`observeco chisel artifacts` + `chisel cards`)

|| | |
|---|---|---|
| **What** | Per-skill compressed cache artifacts (`.md.compressed`, `.md.manifest`, `.md.card`) generated by a batch rule-based pass. Consolidated `cards.json` (156 skill cards, ~45KB) for fast metadata access. `manifests.json` for token tracking. |
| **Implementation** | `chisel/skill_compress.py` — `batch_compress_skills()` scans `~/.hermes/skills/`, splits frontmatter from body, applies rule-based guidance compression to body text, writes 3 artifacts per skill. CLI `observeco chisel artifacts --refresh` triggers full rebuild. `observeco chisel cards` shows top-30 ranked table. |
| **Integration** | SkillOS `_load_skill_content()` (Hermes Agent) patched to prefer `.md.compressed` over raw `.md` when manifest is verified. `max_skill_content_bytes` reduced from 8192→4096 since compressed cache is denser. |
| **Savings** | 854,529→844,668 tokens (9,861, 1.2%) across 156 skills. Each `.compressed` artifact is 0-12.7% smaller than original. Highest savings: linear (24.3%), felo-twitter-writer (12.7%), outlines (9.6%), segment-anything (9.3%). |
| **Free** | All. The compression engine and artifacts are MIT — they make the product better for everyone. |
| **Pro** | n/a (no gating) |
| **Effort** | ~1d (module + CLI + SkillOS patch + batch run) |
| **Depends on** | SkillOS selector (✅ exists), skill files on disk (✅ 156 found) |

---

### 3.24 Config Hygiene Audit (`observeco chisel config`)

**Tagline:** *Find what's wasting tokens before it compounds.*

**What it is:** A CLI tool that reads a Hermes `config.yaml` and flags known token-wasting patterns. Same class of findings that saved ~10K tok/session in our testing — surfaced automatically instead of requiring manual audit.

**Synergy with chisel:** This lives in `observeco/chisel/config_scanner.py`, sharing `_count_tokens()`, YAML parsing utilities, and savings estimation format with `skill_compress.py`. The `observeco chisel` CLI namespace keeps it alongside `chisel skills`, `chisel cards`, `chisel artifacts` — all under the same "find and fix token waste" mental model. Not `doctor`, because this isn't about system health — it's about removing persistent token bloat, exactly like skill compression.

**Discoveries this feature is based on (real data):**

| Finding | Before | After | Tokens saved per session |
|---------|--------|-------|--------------------------|
| Duplicated Reasoning Standards in 7 channel prompts | Each topic had the same 200-tok boilerplate | Moved to shared `system_prompt` (cached) | ~1,200 |
| Low `cache_ttl: 5m` | Only 1 in 3 turns hit cached prefix | Changed to 30m | ~60% on multi-turn sessions |
| Stale ref `intelligence/strategic-proposals/` | Kepler's handover pointed to dead directory | Updated to `signals/outbox/` in AGENTS.md | Behavioral correctness |

**Checks the audit performs:**
1. **Duplicate prompt sections** — Scans `telegram.channel_prompts` for identical blocks (same reasoning standards, voice rules, escalation boilerplate). Reports count and estimated duplicated tokens.
2. **Low cache TTL** — Flags `prompt_caching.cache_ttl < 15m` with estimated cache miss rate per average session duration.
3. **Stale file references** — Checks if paths referenced in prompts (`intelligence/`, `strategic-proposals/`, `signals/outbox/`) actually exist on disk. Reports dead links.
4. **Whitespace/compression opportunities** — Reports config entries with unusually long raw strings (>2KB) that could use prompt dedup or compression.
5. **Orphaned agent references** — If a topic's channel prompt mentions an agent that no longer has a workspace profile, flag it.

**CLI:**
- `observeco doctor config [--hermes-home ~/.hermes]` — single scan, report to stdout
- `observeco doctor config --watch` — daemon mode, re-scan on config.yaml modification
- `observeco doctor config --fix` — apply auto-fixable findings (dedup prompts, raise TTL) with diff preview

**Dashboard widget (Free: diagnostics, Pro: auto-fix):**
- Config health score (0-100) with findings listed — visible to all
- Free sees diagnostics + Pro upsell banner with token waste estimate
- Pro sees one-click Fix buttons + daily scan status
- One-click fixes (Pro):
  - **Extract duplicated Reasoning Standards** — removes from all channel prompts, prepends to shared `system_prompt` (single cached copy)
  - **Raise cache TTL** — sets `prompt_caching.cache_ttl` to 30m
  - **Correct stale references** — auto-finds replacement paths by scanning intelligence/signals directories
  - **Remove orphan agent references** — redacts "You are [agent]" lines for agents with no workspace profile
- Trend chart showing config hygiene over time (is it getting better or worse?) — future

**Free:** CLI scan (single report) + dashboard diagnostics (read-only).
**Pro:** Dashboard diagnostics + one-click Fix buttons + daily scheduled scan (6am). **Pro saves real tokens** — extraction to system_prompt means one shared cached copy instead of N copies per session.

**Effort:** ~1d (module + CLI + dashboard widget)

**Depends on:** `~/.hermes/config.yaml` (works on any Hermes config, not just Sean's)

---

### 3.25 LLM-Powered Intelligence Service (`llm_service/`)

**Tagline:** *Your own LLM, finding agents, diagnosing crashes, and guiding first-run — before you notice anything wrong.*
**Status:** ✅ Live — v1 built in 3 days. 3 deep consumers (agent discovery, onboarding wizard, heal escalation) + 4 shallow consumers (per-agent summary, health check suggestion, error translation, CLI --no-llm). 2 deferred (alert enrichment, pathway anomaly — have working static fallbacks). 1 promoted to deep (heal feedback loop → **L3 learning loop**, see obs-spec-081 — prevention skill auto-creation after novel incidents). **LLM features use your own API key** (`OBSERVECO_LLM_API_KEY` — bring-your-own-key). When no key is configured, all consumers fall back to static responses. No inference costs on ObserveCo. See §1 License for full BYOK rationale.
**Effort:** ~5d

**What it is:** Extracted from the working `doctor/llm.py` (391 lines, 11+ providers) into a shared service layer that every ObserveCo module uses. Priority-ordered: deep in 3 mission-critical consumers, shallow in 6 value-add consumers.

**Architecture:**

```
llm_service/
├── __init__.py          # ask(), detect_providers(), clear_cache()
├── cost_tracker.py      # daily budget cap, per-call tracking
├── cache.py             # SHA256(prompt+context) → response with TTL
├── gate.py              # license.is_pro check, skip for trivial calls

ask(system_prompt, user_context, max_cost_cents=0.02, cache_ttl_secs=300)
→ "fixed diagnosis" | "alert body" | "guide text" | static fallback
```

**Priority: Tier 1 — Deep (mission-critical)**

These 3 consumers get full LLM context. If LLM fails, the user experience is broken without it. Max budget per call: $0.02. Cache: 5min TTL.

| # | Consumer | Current behaviour | With LLM (trial/Pro) | Effort | Why mission-critical |
|---|----------|------------------|---------------------|--------|---------------------|
| **1** | **Agent discovery & population** (`auto_detect.py`) | Scans 6 known directories (Hermes profiles, OpenClaw, Docker, launchd, systemd, agents.json). Misses Python scripts in tmux/screen, Node servers on custom ports, unnamed daemons. User sees 0 agents and churns. | On first dashboard launch (PHASE_ZERO), if static discovery returns < 2 agents or total is 0, call `llm_service.ask()` with the output of `ps aux`, `lsof -i`, common port scans (3000-9999), and running processes. LLM returns candidates: "Found 3 running processes: 'my_bot' (Python, port 3001), 'node-server' (Node, port 8080), 'kepler' (Hermes). Add them?" User confirms → agents added with suggested health checks. | ~1d | **The #1 death moment.** User installs, runs dashboard, sees 0 agents. They don't know where to look. LLM finds what's actually running. Without this, Segment 2 (hobbyists) churns in 30 seconds. |
| **2** | **First-run onboarding wizard** (new PHASE_ZERO) | Empty dashboard with CLI instructions: "Run `observeco agents add <name>`" — conversion leak. | After LLM discovery populates agents, LLM generates a personalized 3-step onboarding guide: "Welcome! I found 3 agents on your machine. Your Anthropic key is set up — I'll use it for crash diagnosis. Step 1: Watch daemon auto-started. Step 2: Pulse data arriving in 30s. Step 3: Dashboard populates live. Here's what you're seeing..." Specific to OS, detected agents, LLM provider. | ~1d | **Second death moment.** Even if agents are found, user needs to understand what they're looking at. Personalized guide converts install to active use. |
| **3** | **Heal escalation on novel failures** (`heal/__init__.py`) | 7 static patterns (circuit, TOCTOU, memory leak, timeout, module, drift, debt). First unknown crash → heal returns `None` → agent stays dead with "unknown" diagnosis → user loses trust. | Step 1 (fast, free, always): 7 static patterns. Step 2 (LLM, trial/Pro): if static returns nothing, pack last 50 lines of pulse history + error log + crash snippet into `llm_service.ask(diagnose_context)`. LLM returns diagnosis + fix suggestion. "Agent crashed with config parsing error — config.yaml line 93 has a stray tab character." Stateless fallback if LLM unavailable. | ~1d | **Trust breaker.** First time something breaks and tool says "dead (unknown)", user learns it's not reliable. LLM turns "dead" into "here's why and how to fix it." |

**Priority: Tier 2 — Shallow (value-add)**

These 6 consumers use LLM to enrich existing behaviour. If LLM fails, the feature degrades gracefully to current static behaviour. Max budget per call: $0.005 (shorter prompts, heavier caching).

| # | Consumer | Current behaviour | With LLM (trial/Pro) | Effort |
|---|----------|------------------|---------------------|--------|
| 4 | **Alert enrichment** (`watch.py` push_alert) | Flat: "🔴 Agent dead: Kepler" — same message every time | LLM classifies: "same crash pattern as last 3 — suppress (no alert)" vs "new failure mode — enrich body with explanation." Duplicate pattern → silence + update internal counter. New pattern → "🔴 New crash pattern in Kepler — config.yaml line 93 stray tab. Auto-heal attempted 3x, circuit open until 07:35." Falls back to flat message if LLM unavailable. | ~0.5d |
| 5 | **Per-agent dashboard summary** (`dashboard/server.py`) | Raw metrics: "Alive, 42ms latency, 3 errors, 2,400 tokens" | LLM generates: "Running well. 4 restarts today (all auto-healed). Memory debt 68 (3 contradictions). Drift stable at +5%. Costs: ~$0.03/day." Updated hourly, cached 1h TTL. Falls back to raw metrics if LLM unavailable. | ~0.5d |
| 6 | **Health check suggestion on agent add** (`cli.py` agents_add) | User runs `observeco agents add my-bot --framework custom` — must know to pass `--health-check` | LLM scans open ports and running processes, suggests: "I see port 8080 open with a Node process. Try `observeco agents add my-bot --health-check http://localhost:8080/health`" Falls back to current CLI help text. | ~0.5d |
| 7 | **Heal feedback loop** (`heal/__init__.py`) — **PROMOTED to deep: L3 Learning Loop** (see obs-spec-081) | Was: heal reports "restarted agent — success" with no learning. **Now:** after successful heal of a novel failure, LLM extracts failure pattern + writes a prevention SKILL.md to `~/.observeco/prevention/`. Next occurrence → FTS5 match → known fix applied directly, skipping LLM diagnosis ($0.02 saved per known-pattern incident). System gets cheaper as it learns your infrastructure. Shallow fallback: 5-pulse-tick post-restart evaluation (current behaviour, no skill creation). | ~2d (spec — obs-spec-081) |
| 8 | **Pathway anomaly summary** (`dashboard/server.py`) | Raw edge statuses: "3 edges red, 2 yellow, 22 green" | Weekly LLM summary: "3 edge changes this week — Telegram→Hound degraded (API rate limit). No new agents discovered." Falls back to raw counts. | ~0.3d |
| 9 | **Error translation from obscure sources** (`heal/` + `watch/`) | Error messages passed through verbatim: "HermesProtocolError: Session mismatch signal opcode == 0x03, expected 0x02" | LLM translates to plain English: "Session mismatch — your Hermes agent and gateway have different session IDs. Restart the gateway to re-sync." Falls back to raw error text. | ~0.3d |

**License gating:**

| Phase | What user sees |
|-------|---------------|
| **First 30 days (new-user grace)** | **Tier 1 (deep)** — always ON to show ObserveCo's value. Agent discovery, first-run guide, heal escalation. These are the proof points — without grace, new users see a dashboard with static fallback and wonder why they installed it. **Tier 2 (shallow)** — ON only if trial/Pro active. Alert enrichment, per-agent summaries, health check suggestions, heal feedback, pathway anomaly, error translation require subscription. |
| **After 30 days (free)** | **Tier 1 (deep)** — shut off. Static fallback. User saw value during grace and knows what they're missing. **Tier 2 (shallow)** — also shut off. |
| **Trial (30-day)** | Full LLM intelligence — both tiers. |
| **Pro $9/mo** | Full LLM intelligence permanently. |
| **Opt-out (`--no-llm` / Settings toggle)** | Everything uses static fallback. No trial clock consumed. Respects privacy-first users. Dashboard Settings provides toggle with warning popup explaining the disadvantages. |

**Design rationale:** Tier 1 (deep) always ON during the 30-day grace period because these are the proof points — agent discovery, onboarding guide, heal escalation. Without them, a new user sees a dashboard with static fallbacks and has no reason to upgrade. Tier 2 (shallow) are enhancement-level conveniences — alert enrichment, per-agent summaries, health check suggestions, heal feedback, pathway anomaly, error translation. The core monitoring (pulse, alerts, errors, heals) works without them. By keeping Tier 2 behind Pro/trial even during grace, we create upgrade incentive while still proving ObserveCo's value through Tier 1.

**Cache & cost control:**

| Guard | Default | Rationale |
|-------|---------|-----------|
| Daily budget cap | $0.10/day | Prevents bill shock on heavy crash days. Config via `OBSERVECO_LLM_BUDGET` env var. |
| Per-call limit (Tier 1) | $0.02 | Deep diagnosis with full context. |
| Per-call limit (Tier 2) | $0.005 | Short prompts, heavy caching. |
| Response cache TTL | 5 min (Tier 1) / 1h (Tier 2 alert summary) | SHA256 of (system_prompt + context). Same error → $0.00 in same window. |
| Budget exhausted | All consumers transparently fall back | No silent skips. No partial LLM showing stale data alongside static data. |
| Provider priority | Cloud first (best), local second (free), static third (guaranteed) | Local Ollama is free for user but less capable. Static fallback is free and always available. |

**Provider detection (extends existing working `doctor/llm.py`):**

Detected in order at startup:

```
ANTHROPIC_API_KEY       → claude-sonnet-4
OPENAI_API_KEY          → gpt-4o
OPENAI_API_KEY sk-or-   → openrouter
DEEPSEEK_API_KEY        → deepseek-chat
GOOGLE_API_KEY          → gemini-2.0-flash
MISTRAL_API_KEY         → mistral-large
GROQ_API_KEY            → llama-3.1-70b
TOGETHER_API_KEY        → llama-3-70b
Ollama localhost:11434  → llama3.1
LM Studio localhost:1234 → default
vLLM localhost:8000     → default
```

No provider keys stored or transmitted. Calls go direct from user machine to chosen provider. Detection cached once at startup.

**Why 3 deep + 6 shallow (not 9 equally):**

| Depth | Calls/day estimate | Cost/day (cloud) | Cost/mo |
|-------|-------------------|-------------------|---------|
| 3 deep (always on) | ~2-5 calls | ~$0.02-0.05 | ~$0.60-1.50 |
| 6 shallow (cached) | ~3-8 calls but 90% cache hit | ~$0.003-0.005 effective | ~$0.10-0.15 |
| **Total** | | **~$0.03/day** | **~$0.70-1.65/mo** |

The deep calls are the ones that matter most and the ones users will notice failing. The shallow calls are frosting — nice when they work, invisible when they fall back.

**Implementation plan (~5d total):**

1. **Day 1: Extract `llm_service/` module** from `doctor/llm.py`
   - Move: `detect_providers()`, `get_auto_provider()`, all provider callers out of doctor/llm.py into llm_service/
   - Add: `cost_tracker.py`, `cache.py`, `gate.py`
   - Keep: doctor prompts, parsing, safety validation in doctor/ (still callable as CLI)

2. **Day 2: Wire deep consumer #1 — Agent discovery**
   - In `auto_detect.py`: after static discovery returns < 2 agents, call `llm_service.ask(system_scan_context)` → parse candidate agents → present to user in dashboard wizard
   - New function: `run_llm_discovery()` — runs `ps aux`, `lsof -i`, common port checks, feeds to LLM
   - Dashboard: PHASE_ZERO wizard template showing discovery results + agent add confirmation

3. **Day 3: Wire deep consumer #2 — First-run wizard**
   - After discovery completes, LLM generates personalized 3-step guide
   - Dashboard renders guide as inline wizard in PHASE_ZERO
   - Auto-transitions to PHASE_SETUP when first pulse data arrives

4. **Day 4: Wire deep consumer #3 — Heal escalation**
   - `_diagnose_agent()`: if static returns None, call `llm_service.ask(diagnose_context)` with pulse history + error log
   - Parse returned diagnosis + suggested action
   - Wire into heal's snapshot-before-action safety pattern (LLM diagnosis saved to investigation log)
   - Falls back to "undiagnosed" if LLM fails

5. **Day 5: Wire all 6 shallow consumers + CLI toggles**
   - Alert enrichment: classify in `push_alert()` before delivery
   - Per-agent summary: `/api/agent-summary/{name}` endpoint, 1h cache
   - Health check suggestion: `agents_add` CLI suggests
   - Heal feedback loop: post-restart evaluation → **L3 Learning Loop** (see obs-spec-081 — prevention skill auto-creation after novel incidents, FTS5 pattern matching, zero-LLM-cost heal on known patterns)
   - Pathway anomaly summary: weekly cached
   - Error translation: pass unknown error format to LLM
   - `--no-llm` flag + config key + opt-out trial skip

---

### 3.26 Telemetry & User Feedback Pipeline

**Tagline:** *Your app phones home with your permission — crash data, usage patterns, installation success — so we know where to fix.*
**Status:** 🟡 Live (local) — `telemetry_client.py` (222 lines) wired to local event bus. Every `send()`/`send_sync()` call publishes `telemetry_{event_type}` to rotating JSONL stream. HTTP POST to `observeco.com/api/telemetry` still blocked (no Vercel endpoint). Local event stream available for CronCutter/consumer reading.
**Effort:** ~1.5d

**What it is:** A privacy-first feedback pipeline. `telemetry_client.py` (222 lines) already exists with machine_id, fire-and-forget thread, opt-in file at `~/.observeco/.telemetry_opt_in`. But it has nowhere to send data.

**Missing (everything):**
- No Vercel endpoint receiving events
- No Supabase `telemetry_events` table
- No DNS record for telemetry.observeco.ai
- No dashboard opt-in modal in PHASE_ZERO
- No Settings toggle in dashboard
- No telemetry_client calls wired into any ObserveCo module

**Architecture (proposed):**

```
User Machine                    Cloud (Vercel + Supabase)
┌─────────────────────┐         ┌─────────────────────────────┐
│ observeco dashboard  │──POST──→│ observeco.com/api/telemetry │
│                      │ HTTPS  │ (add route to existing      │
│ telemetry_client.py  │         │  Vercel project)           │
│                      │         │                             │
│ ~/.observeco/        │         │ Supabase: telemetry_events │
│ .telemetry_opt_in    │         │ (new table, append-only)   │
└─────────────────────┘         └─────────────────────────────┘
```

**Opt-in flow (needs build):**

| Step | What happens | Status |
|------|-------------|--------|
| 1 | On first dashboard launch (PHASE_ZERO), show modal: "Help us improve ObserveCo?" | ❌ Not built |
| 2 | If Yes: `telemetry_client.set_opt_in(True)` | ✅ `set_opt_in()` exists |
| 3 | All subsequent reads `_is_opted_in()` before sending | ✅ Already works |
| 4 | Settings page toggle in dashboard | ❌ Not built |
| 5 | Vercel endpoint receives events, stores in Supabase | ❌ Not built |
| 6 | DNS `telemetry.observeco.ai` → Vercel | ❌ Not set |

Note: Since `observeco.com` already points to Vercel, the telemetry endpoint can be `observeco.com/api/telemetry` — no separate domain needed. Save the SSL cert cost.

**Events sent (opt-in only):**

| Event type | When | Payload (all anonymous) |
|-----------|------|------------------------|
| `install` | First dashboard launch | `{machine_id, os, python_version, observeco_version}` |
| `agent_count` | Every 24h | `{machine_id, agent_count, alive_count, dead_count}` |
| `heal_result` | After heal runs | `{machine_id, diagnosis, action, success}` — no agent names |
| `llm_usage` | After each llm_service call | `{machine_id, consumer_name, tokens_used, cost, cache_hit}` |
| `crash` | Watch daemon / unhandled exception | `{machine_id, error_type, traceback_first_frame}` |
| `license_event` | Trial start / Pro activate / expiry | `{machine_id, event_type}` |
| `dashboard_session` | Dashboard opened | `{machine_id, duration_sec, tabs_viewed}` |
| `trial_expiry` | 30-day trial ends | `{machine_id}` |

**NEVER sent:** Agent names, SOUL.md, pulse data, error messages, API keys, env vars, file paths, email addresses, license keys, agent configs.

**Vercel endpoint:** Add to existing `observeco.com` Vercel project:

```json
POST /api/telemetry
{
  "event": "heal_result",
  "version": "0.2.0",
  "machine_id": "a1b2c3d4e5f67890",
  "payload": {"diagnosis": "memory_leak", "success": true}
}
```

Response: `200 OK` — always. No body. Fire-and-forget client never waits.

**Supabase table (to create):**

```sql
CREATE TABLE telemetry_events (
  id BIGSERIAL PRIMARY KEY,
  event TEXT NOT NULL,
  version TEXT,
  machine_id TEXT,
  os TEXT,
  python TEXT,
  payload JSONB DEFAULT '{}',
  received_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_telemetry_event ON telemetry_events(event);
CREATE INDEX idx_telemetry_day ON telemetry_events(received_at::date);
```

**Effort breakdown: ~1.5d**
- 1h: Add telemetry route to observeco.com Vercel project (`api/telemetry.ts`)
- 1h: Create `telemetry_events` table in Supabase
- 2h: Opt-in modal in PHASE_ZERO dashboard template + Settings toggle
- 2h: Wire telemetry_client calls into watch.py (heal_result, crash, license_event)
- 1h: 24h agent_count cron in watch daemon
- 1h: Dashboard session tracking (frontend heartbeat)
- 1h: End-to-end test: local → Vercel → Supabase

---

### 3.27 Stripe + Licensing + CRM Build Plan

**Tagline:** *Turn Pro trials into paid subscriptions. Know who's using what.*
**Status:** ⚠️ Client code built — **nothing deployed on Vercel or Supabase.** `observeco.com` serves a static landing page only (no API routes). Supabase project exists but empty. All client-side code works but has no backend to talk to.
**Effort:** ~1d + Sean credentials

**What exists today:**

| Component | Status | Location |
|-----------|--------|----------|
| Stripe Solo product (`prod_UZb0uXir0y6lLz`) | ✅ Done | Stripe dashboard |
| Stripe live credentials (key, publishable, webhook secret) | ✅ Done | Hermes credentials file |
| `billing.py` — checkout, webhook, status endpoints, trial config | ✅ Done | `src/observeco/billing.py` (254 lines) |
| `license.py` — local trial token, Pro key entry, online validation, 30-day auto-trial | ✅ Done | `src/observeco/license.py` (257 lines) |
| `licenses_api.py` — dashboard `/api/licenses/status`, `/activate`, `/trial`, `/validate` | ✅ Done | `src/observeco/dashboard/licenses_api.py` (90 lines) |
| Supabase project (`vuyhjbmvyimapdbcjjt.supabase.co`) | ✅ Created but empty — no tables | Supabase |
| Vercel project (observeco.com) | ✅ Static landing page only — **no API routes deployed** | Vercel |

**What needs to be built (nothing is deployed):**

| Component | Time | Depends on |
|-----------|------|------------|
| 1. Supabase schema: products + licenses tables + telemetry_events table | 30 min | Supabase service key (from Sean) |
| 2. Vercel API routes (6 endpoints + telemetry) in observeco.com project | 2.5h | Supabase schema deployed |
| 3. Update `license.py` to POST to `observeco.com/api/licenses/validate` | 30 min | Vercel endpoint live |
| 4. Update `telemetry_client.py` to POST to `observeco.com/api/telemetry` | 15 min | Vercel endpoint live |
| 5. Admin dashboard HTML (license management) | 1.5h | Vercel routes deployed |
| 6. Stripe webhook config (point to observeco.com) | 15 min | Vercel endpoint live |
| 7. End-to-end test: trial → Pro → expiry → LLM gate | 30 min | All of the above |

Note: No separate domains needed. Everything lives at `observeco.com/api/*` — reuses existing Vercel SSL, DNS, and project config.

**Vercel API routes to add to observeco.com:**

| Route | Method | Purpose |
|-------|--------|---------|
| `/api/stripe/webhook` | POST | Stripe checkout.session.completed → create license |
| `/api/licenses/validate` | POST | Validate a license key (called by ObserveCo client) |
| `/api/trials/start` | POST | Generate trial license |
| `/api/admin/licenses` | GET | List all licenses (auth-protected) |
| `/api/admin/licenses` | POST | Issue free Pro license (auth-protected) |
| `/api/admin/stats` | GET | Active/trial/expired counts (auth-protected) |
| `/api/telemetry` | POST | Receive anonymous usage events |

**Supabase schema (execute in Supabase SQL editor):**

```sql
CREATE TABLE products (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  name TEXT NOT NULL, slug TEXT UNIQUE NOT NULL,
  stripe_price_id TEXT, features JSONB DEFAULT '[]',
  trial_days INT DEFAULT 0, price_display TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);
INSERT INTO products (name, slug, stripe_price_id, features, trial_days, price_display)
VALUES
  ('Free', 'free', NULL, '["fleet_view", "pulse_check", "circuit_breakers", "token_breakdown", "drift_trend", "error_history", "heal_button", "alerts", "memory_garden", "cli_tools"]', 0, '$0'),
  ('Solo', 'solo', 'price_solo_monthly', '["free_features", "pro_badge", "license_validation", "llm_intelligence"]', 30, '$9/mo');

CREATE TABLE licenses (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  product_slug TEXT REFERENCES products(slug),
  email TEXT NOT NULL, name TEXT,
  license_key TEXT UNIQUE NOT NULL,
  status TEXT DEFAULT 'trialing' CHECK (status IN ('trialing','active','expired','cancelled')),
  trial_ends_at TIMESTAMPTZ, expires_at TIMESTAMPTZ,
  stripe_subscription_id TEXT, stripe_customer_id TEXT,
  issued_by TEXT DEFAULT 'self' CHECK (issued_by IN ('self','stripe','admin')),
  metadata JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT now(), updated_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_licenses_key ON licenses(license_key);
CREATE INDEX idx_licenses_email ON licenses(email);

CREATE TABLE telemetry_events (
  id BIGSERIAL PRIMARY KEY,
  event TEXT NOT NULL, version TEXT,
  machine_id TEXT, os TEXT, python TEXT,
  payload JSONB DEFAULT '{}',
  received_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_telemetry_event ON telemetry_events(event);
CREATE INDEX idx_telemetry_day ON telemetry_events(received_at::date);
```

**How trial re-up works (the clock-reset rule):**

| Scenario | What happens |
|----------|-------------|
| First-run, no trial | `license.start_trial()` generates 30d offline token when user explicitly clicks "Start Free Trial" or accesses a Pro feature. No auto-trial on install. |
| Trial active, user subscribes Pro | Stripe webhook creates active license in Supabase. Local license.json gets Pro key. Trial clock irrelevant. |
| Trial expires, user did nothing | `license.is_pro` returns False. LLM gate stops all calls. Static fallback active. Dashboard banner: "Trial ended — subscribe $9/mo" |
| Trial expired, user subscribes later | Stripe webhook creates active license. Local license.json gets Pro key. LLM restored. |
| Pro active, user cancels | Stripe webhook → license status = cancelled. Local reverts to free + "resubscribe" banner. |

**No cloud lock-in:** Trial works fully offline. Pro validation only touches cloud for key auth. Cached 24h if Stripe/Vercel is down.

**Admin dashboard** (served from Vercel, protected by API key):

```
┌──────────────────────────────────────────────────────────┐
│ 🛡️ ObserveCo Licenses          [+ Issue Free License]     │
├──────────────────────────────────────────────────────────┤
│ Filter: [All ▼] [Active 12] [Trial 8] [Expired 3]       │
├──────────┬──────────┬─────────┬────────┬─────────────────┤
│ Email    │ Name     │ Product │ Status │ Created          │
├──────────┼──────────┼─────────┼────────┼─────────────────┤
│ a@b.com  │ Alice    │ Solo    │ Active │ 2026-06-01      │
│ c@d.com  │ Bob      │ Solo    │ Trial  │ 2026-06-01      │
└──────────┴──────────┴─────────┴────────┴─────────────────┘
```

**Effort: ~1d total** (plus credentials from Sean to access Supabase + Stripe)
- 30min: Execute Supabase schema (products + licenses + telemetry_events)
- 2.5h: 7 Vercel API routes in observeco.com `api/` directory (TypeScript serverless functions)
- 1.5h: Admin dashboard HTML
- 30min: Update `license.py` validate URL + `telemetry_client.py` telemetry URL to point to observeco.com
- 30min: Stripe webhook config in Stripe dashboard
- 30min: End-to-end test

---

### 3.28 Self-Serve Billing Management

**Tagline:** *Know your plan. Manage your subscription. Cancel in one click.*

**Status:** ✅ Live — Feature #26 complete
**Effort:** ~4h total
**Customer principle:** The user should see their billing status clearly, manage it without contacting anyone, and never feel trapped.
**Test suite:** 270 tests (P0=100%, P1=95%+, P2=80%+) — see `spec/plumbing-sprint-review/comprehensive-test-plan.md`
**Success metrics:**
- License status card renders in ≤500ms (static SSR, no network call on page load)
- billing.json write completes in ≤200ms (local file, encrypt+rotating+lock)
- billing.log stays under 4MB for single-user (RotatingFileHandler, 1MB×3 backups — real usage ~20KB/month)
- File lock acquisition succeeds on first attempt ≥99% (single-process)
- File lock acquisition succeeds within 500ms under multi-process contention (10 retries × 50ms)
**Acceptance criteria:**
- [AC1] License card shows correct state for each of Trial / Cancelled / Expired / Pro / Free-Exhausted
- [AC2] Cancel Trial writes `trial_consumed=true` and transitions card to Cancelled state within 1s of click
- [AC3] Re-trial after cancel shows Free-Exhausted — no second trial
- [AC4] Concurrent process A writes customer, process B reads immediately after — B sees A's write (file lock)
- [AC5] billing.log rotates when it exceeds 1MB — logs are not lost, oldest entry is discarded
- [AC6] 270-test suite passes with 0 failures
**Known constraints (documented, all closed in v0.2.0):**
- Multi-process safety: ✅ resolved via file-level lock (`_acquire_file_lock` / `.billing.lock` atomic O_EXCL)
- Log rotation: ✅ resolved via `RotatingFileHandler` (1MB × 3 backups)
- Thread safety: ✅ resolved via `threading.Lock`

**Design philosophy:**
- License keys are internal plumbing, not customer-facing — show "Pro ✓" or "Free", not `OBS-3B207C38`
- Stripe sends receipts/invoices/retry emails — we don't build that
- One-click Cancel Trial (no survey — add one later if churn data justifies it)
- Paid subscribers get Stripe-hosted Customer Portal (update payment, cancel, invoices) — no custom UI
- Trial is a single-use entitlement per email address — not a clock you can reset by deleting `license.json`

**Customer-facing views:**

**During trial:**
```
┌────────────────────────────────────────────────────────────┐
│  🚀 Solo plan · 23 days left in free trial                 │
│  No charge until 1 July. Cancel anytime.                   │
│                                                            │
│  [Subscribe via Stripe $9/mo]  [Cancel Trial]              │
└────────────────────────────────────────────────────────────┘
```

**After cancelling trial:**
```
┌────────────────────────────────────────────────────────────┐
│  Trial cancelled. Your data is safe — all Pro features     │
│  are locked. Subscribe anytime to unlock them.             │
│                                                            │
│  [Resubscribe $9/mo →]                                     │
└────────────────────────────────────────────────────────────┘
```

**When trial expires:**
```
┌────────────────────────────────────────────────────────────┐
│  ⚠️ Your free trial ended on 1 July.                       │
│  You're on Free plan — Pro features (Brain, Alerts, ...)   │
│  are locked. Data stays.                                   │
│                                                            │
│  [Subscribe $9/mo]  [Dismiss]                              │
└────────────────────────────────────────────────────────────┘
```

**Pro subscriber (paid):**
```
┌────────────────────────────────────────────────────────────┐
│  ✅ Pro · Solo $9/mo                                       │
│  Next billing: 1 August 2026                               │
│                                                            │
│  [Manage Billing →]  (Stripe Customer Portal)              │
└────────────────────────────────────────────────────────────┘
```

**Build plan:**

| # | Component | Files | Time | Details |
|---|-----------|-------|------|---------|
| 1 | License status card UI | `server.py` template block + `index.html` | 1h | Banner showing plan, trial days left, action buttons. Appears above the agent grid. Reactive — updates via existing `/api/licenses/status` endpoint |
| 2 | Cancel Trial endpoint | `licenses_api.py` | 30min | `POST /api/billing/cancel-trial` → sets license.json `license_type=free`, marks `trial_consumed=true`. Does NOT delete local data. Dashboard banner switches to cancelled state |
| 3 | Cancel Trial UI | `server.py` + `index.html` | 30min | Confirmation dialog: "Cancel trial? You'll lose Pro features when the trial ends. Your data stays." Two buttons: [Yes, cancel] [Keep trial] |
| 4 | Stripe Customer Portal | `billing.py` | 30min | `POST /api/billing/portal` → `stripe.billing_portal.Session.create(customer=customer_id)` → returns portal URL. Redirect user. Only shown when user has active Stripe subscription |
| 5 | Stripe webhooks (CRM) | `commercial_api.py` on Vercel | 1h | Add 3 webhook event handlers to existing `/api/commercial/stripe/webhook` endpoint: `customer.subscription.deleted` → mark license `cancelled`, `customer.subscription.updated` → sync plan/status, `invoice.payment_failed` → mark `past_due` (7-day grace before lock) |
| 6 | End-of-trial banner | `server.py` + `index.html` | 30min | Check `trial_end < now` on dashboard load. Show warning banner. Dismissable |
| 7 | Trial hardening | `license.py` | 15min | When `ensure_trial()` called, check if `trial_consumed=true` in `license.json`. If yes, skip trial and stay Free. Re-trial requires a new email + Stripe Checkout (Stripe enforces the limit) |

**What we deliberately DON'T build:**
- ❌ Custom cancellation survey — Stripe portal has one, add custom after 100 churns
- ❌ Invoice PDF download link — Stripe emails it
- ❌ Payment failure handling — Stripe auto-retries + emails customer
- ❌ Credit card update UI — Stripe portal handles this
- ❌ Plan upgrade/downgrade UI — Stripe portal handles this
- ❌ Email notifications — Stripe Billing automations handle this
- ❌ License key display — users don't need to see it
- ❌ Team tier ($49) — delayed post-v1

**How trial hardening works:**
| Scenario | What happens | Vectors left open |
|----------|-------------|-------------------|
| Same email re-trial | CRM stores `trial_consumed=true` per email. Blocked | None |
| Same machine, delete `license.json` | `trial_consumed` flag survives in local `license.json`. If wiped, local trial regenerates but skimpy — **acceptable risk at early stage** | Accidental reset possible, loses 1 trial |
| Different email, same machine | Local trial generates anew. CRM doesn't know. **Acceptable risk** — value of trial-hopping through email aliases is low. Stripe Checkout requires payment method which filters casual gamers | Email aliases |
| Stripe-based re-trial | Stripe blocks: same customer ID → no second `trial_period_days` | None |

**Grace period philosophy:** 7-day grace after trial expiry before Pro features hard-lock. During grace, show warning banner but keep Pro features accessible. After 7 days, soft-lock with "Upgrade to unlock" overlay. Data never deleted during grace.

---

### 3.29 Confidence, False-Positive/FN Detection & Recommendations

**Status:** ✅ Live — Feature #27 complete (commit 3e19d17+)
**Effort:** ~2h total
**Tagline:** *Every flag tells you how sure we are and what to do about it.*

**Customer principle:** A red flag without a recommendation is just anxiety. A green flag without a confidence score is a trap. Every signal must tell the user: (1) how sure we are, (2) how likely it is to be wrong, and (3) what to do next.

**How it works:** A single `_compute_confidence()` function cross-references 4 data signals (pulse state duration, consecutive check count, source agreement, error pattern stability) to produce a confidence level, FP risk, FN risk, and recommendation for every agent card metric row and every detail tab.

**Confidence levels:**
- 🟢 **High** (4/4 signals agree) — State persisted >2h, 3+ consecutive checks, all sources agree, error pattern is stable
- 🟡 **Medium** (2-3/4 signals agree) — State <30min, 1-2 checks, sources disagree, errors vary
- ⚪ **Low** (0-1/4 signals agree) — Single source, just changed, isolated reading, first check

**Risk axes:**
- **FP risk** (false positive — alarm when nothing's wrong): Low / Moderate / High
- **FN risk** (false negative — quiet when something IS wrong): Low / Moderate / High

**Per-signal contribution:**

| Signal | What it measures | High confidence means |
|--------|-----------------|---------------------|
| **Duration** | How long has this state persisted? | >2h = high confidence. 1 miss could be transient. |
| **Consecutive count** | How many checks in a row agree? | 3+ consecutive = high. Single = low. |
| **Source agreement** | Do pulse + errors + circuit breaker agree? | All 3 say dead = high. Only 2/3 = medium. |
| **Pattern stability** | Are errors consistent or random? | Same root cause every time = high. Random = medium/low. |

**Recommendations by condition:**

| Condition | Confidence | FP risk | FN risk | Recommendation |
|-----------|-----------|---------|---------|---------------|
| Agent dead, long duration | 🔵 High | ✅ Low | ✅ Low | `➤ Agent has been down for X days. Start manually: observeco start <name>` |
| Agent dead, recent | 🟡 Med | ⚠️ Moderate | ✅ Low | `➤ Agent may be down. Run observeco pulse check <name> to confirm.` |
| Guard tripped | 🔵 High | ✅ Low | ✅ Low | `➤ Guard stopped after 3 failures. Wait ~4h cooldown or restart agent.` |
| Guard not tripped, agent dead | 🔵 High | ✅ Low | ✅ Low | `➤ Agent is down — guard can't check it. Start the agent first.` |
| Multiple errors, dead agent | 🔵 High | ✅ Low | ✅ Low | `➤ X errors from a dead agent. Restart the agent to stop the noise.` |
| Multiple errors, alive agent | 🟡 Med | ⚠️ Moderate | ✅ Low | `➤ X errors — could be transient or ongoing. Run observeco heal --diagnose.` |
| Single error | ⚪ Low | ❌ High | ✅ Low | `➤ Single error — likely transient. No action unless it repeats.` |
| Stale running (alive but old) | 🟡 Med | ✅ Low | ❌ High | `➤ Last check was Xh ago. Agent could have died since. Run observeco pulse check.` |
| Perfect health, many checks | 🔵 High | ✅ Low | ✅ Low | `➤ All clear — all checks passed.` |
| Perfect health, few checks | ⚪ Low | ✅ Low | ❌ High | `➤ No issues yet — but only X checks recorded. Continue monitoring.` |

**Where it shows on the page:**

| Location | What the user sees |
|----------|-------------------|
| **Agent card Health row** | `● Running` + 🟢 High confidence dot + recommendation inline (smaller text below row) |
| **Agent card Guard row** | `⚠️ Agent is down` + 🔵 High confidence + FP risk: Low |
| **Agent card Errors row** | `⚠️ 6 in last 24h` + 🔵 High confidence + recommendation inline |
| **Health detail tab** | Confidence header with FP/FN risk badges + full recommendation section |
| **Guard detail tab** | Confidence header with source agreement breakdown + recommendation |
| **Errors detail tab** | Confidence header + FP risk badge + recommendation before Pro upsell |
| **Handled separately:** | Stale status → shows FN risk prominently ("could be hiding something") |

**Specific false-positive and false-negative guardrails:**
- **FP guard: Green status with no recent pulses** → FN risk: High → warns user "could be missing data"
- **FP guard: Red status with single miss** → Confidence: Low → says "transient — wait 2 min"
- **FP guard: Guard stopped but agent recovered** → Reflected in recommendation ("agent may be fine, guard will auto-reset")
- **FN guard: Multiple errors with low confidence** → Shows FP risk alongside to prevent panic
- **FN guard: Perfect health on new agent** → Shows "only N checks recorded — not yet conclusive"

**What we deliberately DON'T build:**
- ❌ ML-based confidence — uses deterministic rules from existing DB signals
- ❌ Historical confidence trends — single snapshot per check
- ❌ User-configurable thresholds — sensible defaults for v1
- ❌ Per-user recommendation preferences — same recommendations for all

**Test coverage:** Tests for `_compute_confidence()` covering: dead agent long duration, single missed pulse, stale running, perfect health, guard tripped, single error, mixed signals.

## Phase 7 — Structural Improvements for Segment 1 & 2 Reliability

**Status:** ✅ **Complete** — All 4 sub-phases + 2 supplementary items live as of 2026-06-04.

**Trigger:** Independent probability assessment (June 2026). Current product scores 85% for Segment 1 (daily Hermes user), 60% for Segment 2 (hobbyist/any framework). Phase 7 targets 98% / 95% through 4 structural architecture changes.

**Effort:** ~12d total (10-12d planned + ~1d token tracking + ~1d skill artifacts)

---

### 7.1 Event Pipeline — Kill the Monolithic Watch Loop

**Status:** ✅ Live — Phase 7.1 complete (Days 1-5). Rotating JSONL event stream (`EventStream` class) + `publish()`/`subscribe()`/`get_events()` API. All 6 secondary cycles extracted into independent thread consumers in `watch_consumers.py` (DriftConsumer, GardenConsumer, PathwayConsumer, HealConsumer, PruneConsumer). Cyclic 2-7 removed from main loop in `watch.py`. Main loop now only probes + writes heartbeat. 9 consumer tests + 7 event-bus tests pass.
**Effort:** ~4-5d

**Problem:** `watch.py:_run_loop()` does everything in sequence in one thread — probe agents, trim SOUL.md, compute drift (5min), scan garden (15min), scan pathway (15min), auto-heal dead agents, push alerts, write heartbeat. A crash in any sub-task stalls the entire pipeline. If garden scan crashes on corrupted MEMORY.md, drift and pathway scans don't run this cycle either.

**Current architecture (fragile):**

```
watch daemon _run_loop()
  ├─ probe all agents (sequential)
  ├─ trim SOUL.md for alive agents
  ├─ compute drift (every 5min)
  ├─ scan garden (every 15min)  ← crash here stalls everything
  ├─ scan pathway (every 15min) ← doesn't run if garden crashed
  ├─ auto-heal dead agents (L1 + push)
  ├─ token snapshot log
  └─ write heartbeat file
```

**Target architecture (resilient):**

```
watch daemon main loop                Egress: JSON event per cycle
  │ (probe agents + write heartbeat)     {event_type, agent_name, status, latency, ts}
  │
  └─→ event → subscription_bus ─┬─ consumer: drift_calculator
                                  ├─ consumer: garden_scanner
                                  ├─ consumer: pathway_scanner
                                  ├─ consumer: heal_worker
                                  ├─ consumer: alert_delivery
                                  └─ consumer: heartbeat_writer
```

Each consumer is an isolated subprocess/thread with its own failure domain. A garden crash → DLQ entry + consumer restart. Probes, drift, pathway, heartbeat all continue unaffected.

**Key changes:**
- Main loop only probes agents + writes heartbeat (fast, simple, always runs)
- Events written to a local JSON event stream (`~/.observeco/events/` with rotating files)
- 5 consumers read from the stream independently
- Each consumer has its own try/except + restart cycle
- DLQ integration for repeated consumer failures

**What this changes:**
- Segment 1: Watch daemon doesn't silently lose cycles. Garden bug → garden consumer restarts, everything else continues. **85% → 95%.**
- Segment 2: First install doesn't crash on unexpected file structures. Everything works every cycle.
- Bonus: Every consumer is independently unit-testable with a mock event stream.

**Effort breakdown: ~4-5d**
- Day 1: Event schema + subscription bus + event stream writer
- Day 2: Extract drift + garden into consumer subprocesses
- Day 3: Extract pathway + heal + alert consumers
- Day 4: DLQ integration + consumer restart logic
- Day 5: Test all 5 consumers in isolation + end-to-end under failure conditions

---

### 7.2 Parallel Probe Engine

**Status:** ✅ Live — Phase 7.2 complete. Sequential probe loop replaced with `ThreadPoolExecutor(max_workers=10)` + `as_completed(timeout=45)`. Individual probe timeout 30s. 3 parallel probe tests pass.
**Effort:** ~2d

**Problem:** `_probe_agent()` blocks sequentially. 12 agents × 10s timeout = up to 120s per cycle under degraded conditions. The 30s interval is aspirational — under degraded conditions, cycles are skipped. This imposes a hard ceiling on fleet size (~15 agents before the daemon can't keep up with its own interval).

**Current architecture (sequential):**

```python
for agent in agents:
    probe(agent)  # 12 agents × 2s each = 24s per cycle
```

**Target architecture (parallel):**

```python
with ThreadPoolExecutor(max_workers=10) as pool:
    list(pool.map(probe_agent, agents))  # max(2s) = 2s per cycle
```

**Key changes:**
- Replace `for agent in agents: _probe_agent(agent)` loop with `ThreadPoolExecutor(max_workers=10)`
- `_probe_agent()` remains unchanged — fast probes (pgrep, launchd) complete immediately, slow probes (HTTP) run in parallel
- Connection pooling via reuse of existing `httpx.Client` across probe cycles
- Graceful timeout: any probe exceeding 30s is cancelled individually, not blocking the fleet

**What this changes:**
- Segment 1 (12 agents): Fleet probe goes from ~6-24s to ~6s (max latency, not sum). 30s interval is actually 30s.
- Segment 2: Removes the hard ceiling. Fleet can grow from 3 to 15+ agents without hitting the interval wall.
- Future: Makes "auto-discover new agents between cycles" viable.

**Effort breakdown: ~2d**
- Day 1: Replace sequential loop with ThreadPoolExecutor + connection pooling
- Day 2: Test at 5, 10, 15, 20 agents with mixed probe types (fast + slow)

---

### 7.3 First-Run State Machine (PHASE_ZERO + PHASE_SETUP)

**Status:** ✅ Live — Phase 7.3 complete. 3-phase state machine with interactive PHASE_ZERO discovery wizard (htmx CTA button → static + LLM discovery → confirm agents → phase transition), PHASE_SETUP with 4-stage progress bar and LLM-generated personalized guide, PHASE_LIVE full dashboard. Irreversible phase transitions. DB-backed persistence. 8 tests pass. Next: Phase 7.2 parallel probes.
**Effort:** ~4-5d

**Problem:** The dashboard has one rendering mode — "live with whatever data exists." If no agents or pulse data exist, the page renders agent cards with zeroes, token bars at 0, drift with no data. There is no concept of "this user has never used ObserveCo before."

**Current (single state):**

```
dashboard serves one template → live mode with whatever data exists
```

**Target (3-phase state machine):**

```
app.state.phase = determine_phase()

PHASE_ZERO: "Welcome to ObserveCo"
  - One-page guide, no fleet/analysis/settings tabs
  - Single CTA: "Let's find your agents" → runs discovery
  - Shows discovery results (agents found via static + LLM)
  - Telemetry opt-in modal
  - Transitions to PHASE_SETUP when first agent confirmed

PHASE_SETUP: "Your first agent is being observed"
  - Agent card appears with "Waiting for pulse data..."
  - LLM-generated personalized guide (integrates §3.25)
  - Progress bar: discovered → watched → pulse arriving → dashboard live
  - Transitions to PHASE_LIVE when pulse data exists

PHASE_LIVE: Full dashboard as it exists today
```

**Implementation:**
- Phase detector: `determine_phase()` checks agents.json entries, pulse_log row count, heartbeat file
- State persisted in `_meta` table: `first_run_complete`, `onboarding_complete`
- Phase transitions are irreversible
- Dashboard is one template with phase-driven sections, not three separate HTML files

**What this changes:**
- Segment 1: Skips to PHASE_LIVE immediately (has agents + pulse data). Zero friction.
- Segment 2: Lands on guided "get started" page, not an empty dashboard with CLI instructions. **Converts installs to active users.**

**Effort breakdown: ~4-5d**
- Day 1: Phase detector + DB state + PHASE_ZERO template
- Day 2: Agent discovery wizard in PHASE_ZERO (integrates with §3.25 LLM)
- Day 3: PHASE_SETUP template + personalized guide
- Day 4: Phase transition logic + verify PHASE_LIVE regression-free
- Day 5: End-to-end test: fresh install → discovery → pulse → live

---

### 7.4 Probe Driver Registry

**Status:** ✅ Live — Phase 7.4 complete. `BaseProbe` abstract class + `@register` decorator + 6 typed probes (Http, Launchd, Docker, Systemd, Shell, Pgrep) in `probe/registry.py`. `resolve_probe()` resolves agents to correct probe via health_check scheme. `_probe_agent()` in `pulse/check.py` now delegates to `resolve_probe().probe()` — 132-line if/else removed. 11 registry tests + 6 integration tests pass.
**Effort:** ~3d

**Problem:** `_probe_agent()` in `pulse/check.py` is a 132-line if/else chain with 6 probe types (HTTP, launchd, Docker, systemd, shell command, pgrep). Adding a new probe type requires editing the if/else chain. The function is untestable as a unit.

**Current (132-line if/else):**

```python
def _probe_agent(agent):
    if agent.health_check starts with http://:   # HTTP probe
    elif agent.health_check starts with launchd::  # launchd probe
    elif agent.health_check starts with docker::   # Docker probe
    elif agent.health_check starts with systemd::  # systemd probe
    elif agent.health_check:  # shell command
    else:  # pgrep by process name
```

**Target (registry + typed configs):**

```python
# probe/registry.py
PROBES: dict[str, type[BaseProbe]] = {}

class BaseProbe:
    @abstractmethod
    async def probe(self, config: ProbeConfig) -> ProbeResult: ...

# probe/http.py
@register("http", "https")
class HttpProbe(BaseProbe):
    def probe(self, config) -> ProbeResult:
        return httpx.get(config.target, timeout=config.timeout)
```

Agent config becomes typed per probe:
```json
{"type": "http", "target": "http://localhost:8000/health", "timeout": 10}
{"type": "docker", "container": "kepler", "timeout": 5}
{"type": "pgrep", "process_name": "hound"}
```

**Key changes:**
- Abstract `BaseProbe` with `probe()` interface
- `@register()` decorator maps URL schemes or type strings to probe classes
- 6 existing probe types migrated into individual files under `src/observeco/probe/`
- `AgentConfig` updated with typed `probe_config` dict + backward compat for legacy `health_check` string

**What this changes:**
- Segment 1: No direct impact (pgrep works).
- Segment 2: A hobbyist with Python script + Node bot + Docker container gets first-class platform support. Adding a new probe (grpc, tcp_port, unix_socket) becomes a 30-line file.
- Future: Third-party probes (Redis, Kafka, Minecraft) without forking the codebase.

**Effort breakdown: ~3d**
- Day 1: BaseProbe + registry + migrate HTTP, launchd, Docker probes
- Day 2: Migrate systemd, shell, pgrep + update AgentConfig + backward compat
- Day 3: Tests for each probe in isolation + end-to-end mixed fleet test

### 7.7 Stale Daemon Guard & Stale Agent Cleanup

**Status:** ✅ Live — Phase 7.7 complete. 7.7a: Watch heartbeat freshness banner on dashboard (amber warning when daemon stale >90s, PID liveness check via os.kill, `observeco watch start` CTA). 7.7b: Stale agent auto-cleanup in watch daemon cycle 0.5 — agents >24h stale with zero pulse data removed, count logged to heartbeat metadata. 3 stale agents purged on first run. 277/277 tests passing.
**Effort:** ~0.5d

**Problem:** Two gaps discovered in Phase 7.4 probe deployment:

1. **Stale watch daemon hides probe coverage gaps.** The probe registry works but if the user restarts (git pull, `observeco watch restart`), the old daemon keeps running with stale code. The dashboard shows "○ Not pulse-monitored" for service agents but the real issue is the daemon hasn't restarted — not that probes don't work. No dashboard warning for this.

2. **DB-only stale agents accumulate.** `agent_configs` table holds agents registered by older discovery runs (e.g. `hermes`, `test-agent`, `Holiday Scraper`) that `load_config()` no longer returns. These get probed by the watch daemon → `PgrepProbe` returns `dead` → pulse_log fills with "no matching process" noise. No cleanup mechanism.

**Solution:**

**7.7a — Watch heartbeat freshness banner on dashboard:**
- Read `.watch_heartbeat.json` from `_DATA_DIR`
- If age > 120s (missed 4 cycles): show amber banner: "⚠️ Watch daemon may be stale — restart with `observeco watch restart`"
- If no heartbeat file: show similar banner
- Display on dashboard header, auto-dismiss after 8s (same pattern as phase banner)

**7.7b — Stale agent auto-cleanup:**
- Watch daemon cycle 1: run `purge_stale_agents()` — remove entries from `agent_configs` whose names don't appear in `load_config()`
- Threshold: agents with `last_seen` > 7d AND zero pulse data are auto-removed
- Log count of removed agents to daemon heartbeat metadata

**What this changes:**
- Segment 1: Dashboard now warns when monitoring stack itself is stale. Stale agent cleanup prevents noise.
- Segment 2: Same guard protects non-Hermes users from silent probe failure.

---

**Phase 7 total impact:**

| # | Change | Days | Seg 1 | Seg 2 |
|---|--------|------|-------|-------|
|| 7.1 | Event pipeline | 4-5 | ✅ +10% (85→95%) | ✅ +5% (60→65%) |
|| 7.2 | Parallel probes | 2 | ✅ +3% (95→98%) | ✅ +7% (65→72%) |
|| 7.3 | First-run state machine | 4-5 | ✅ 0% (already live) | ✅ **+23%** (72→95%) |
|| 7.4 | Probe registry | 3 | ✅ 0% | ✅ +3% (95→98%) |
|| 7.5 | Token tracking in watch daemon | 1 | ✅ Operational data quality | ✅ Operational data quality |
|| 7.6 | Skill artifacts + cards system | 1 | ✅ SkillOS cache performance | ✅ SkillOS cache performance |
|| | **Combined** | **13-15d** | **85% → 98%** | **60% → 98%** |

---

| Era | What We Called It |
|-----|------------------|
| Pre-April 2026 | **Caveman** — codename for prompt compression |
| April–May 2026 | **CHISEL** — replaced "caveman." **ERIS** (runtime integrity) + **CHISEL** (context) split |
| May 2026+ | **ObserveCo** — unified product. **Chisel** = classification algorithm. **ClawForge** = OpenClaw counterpart. |

## Appendix: Files Referenced

| File | Purpose |
|------|---------|
| `specs/pulse-depth-spec.md` | Detailed spec for 6 planned features |
| `specs/product-feature-audit.md` | Complete inventory of internal tools vs ObserveCo |
| `specs/unified-dashboard.md` | Original dashboard spec (free vs Pro) |
|| `specs/observeco-master-plan.md` | THIS FILE — single source of truth (includes §10 Feature Value Pitches) |
| `mockups/fleet-dashboard.html` | Interactive mockup: fleet view (free) |
| `mockups/brain-analysis.html` | Interactive mockup: unified token breakdown + compression page |
| `mockups/token-breakdown.html` | ⚠️ Obsolete — replaced by `brain-analysis.html` |
| `mockups/auto-heal.html` | Interactive mockup: self-heal (free manual / Pro auto) |
| `mockups/push-alerts.html` | Interactive mockup: alert relay (Pro locked) |
| `mockups/chisel-compress.html` | ⚠️ Obsolete — replaced by `brain-analysis.html` |
| `mockups/openclaw-plugin.html` | Interactive mockup: OpenClaw runtime plugin (planned) |
| `mockups/skills-audit.html` | Interactive mockup: skill audit ranked list (planned) |

---

## Appendix: Cross-Platform Gap Analysis (v2.1 — 2026-05-29)

**Source:** Independent gap analysis + code review + master plan v2.1
**Status:** Active — Phase 1 execution

### A.1 Current Cross-Platform State

| Feature | macOS | Linux | Windows |
|---|---|---|---|
| CLI | ✅ | ✅ | ✅ (with fixes) |
| Config location | ~/.config/observeco/ | ~/.config/observeco/ | %APPDATA%/observeco/ |
| Colors | ✅ | ✅ | ✅ (colorama) |
| Headless mode | N/A | ✅ (no ANSI) | N/A |
| Keychain | Keychain | Secret Service | Credential Manager |
| Installer | Homebrew | apt/snap | MSI/Chocolatey |

### A.2 New Modules Added (Phase 1)

| Module | Purpose | Status |
|---|---|---|
| `risk_engine.py` | Tool-call JSON parser, 4 risk levels | ✅ Added |
| `session_log.py` | Tamper-evident SHA-256 hash chain logging | ✅ Added |
| `hooks/outcome-tracking.js` | Auto-capture user feedback | ✅ Added |
| `hooks/model-routing.js` | Classify tasks, route to models | ✅ Added |
| `hooks/self-healing.js` | Per-tool-call retry + fallback | ✅ Added |
| `hooks/knowledge-graph.js` | Query intelligence layer before research | ✅ Added |

### A.3 Phase 1 Tasks (Updated)

| # | Task | Owner | Status |
|---|---|---|---|
| 1.1 | Naming resolved (ObserveCo = company) | Kepler | ✅ |
| 1.2 | README fixed (removed false npm claim) | Kepler | ✅ |
| 1.3 | pyproject.toml ready for PyPI | Hound | ✅ |
| 1.4 | Cross-platform paths (platformdirs) | Hound | ✅ |
| 1.5 | Cross-platform colors (colorama + headless) | Hound | ✅ |
| 1.6 | Risk engine v2 (tool-call JSON parser) | Hound | ✅ |
| 1.7 | Platform-aware dangerous patterns | Hound | ✅ |
| 1.8 | OpenClaw hook integration | Hound | ✅ |
| 1.9 | Tamper-evident session logs (hash chain) | Hound | ✅ |
| 1.10 | OS keychain (keyring + fallback) | Hound | ✅ |
| 1.11 | Security audit | TBD | ⬜ |

### A.4 Code Review Findings (Resolved)

| ID | Severity | Issue | Fix |
|---|---|---|---|
| SEC-001 | Critical | Secrets plaintext in fallback | File permissions (0o600) added |
| SEC-002 | High | Secrets file world-readable | chmod on write |
| CROSS-001 | High | ANSI detection fails in Git Bash | Multiple env var checks added |
| CROSS-002 | High | macOS data dir uses Linux path | macOS path added |
| PKG-001 | Medium | keyring overly restrictive | Made optional dependency |

### A.5 Phase 2 Roadmap (Cross-Platform)

| # | Task | Effort |
|---|---|---|
| 2.1 | MCP server (universal agent adapter) | 1 week |
| 2.2 | Slack adapter | 3 days |
| 2.3 | Discord adapter | 3 days |
| 2.4 | Telegram adapter | 2 days |
| 2.5 | Dashboard (htmx + FastAPI) | 1 week |
| 2.6 | WebSocket real-time monitoring | 3 days |
| 2.7 | Team features (shared policies) | 3 days |
| 2.8 | Docker image | 1 day |

### A.6 Intelligent Troubleshooter — observeco doctor (Added 2026-05-29)

**Concept:** Use the user's own cloud LLM to diagnose and fix installation/configuration issues. Zero cost to ObserveCo, infinite knowledge.

**Module:** `src/observeco/doctor/`

| File | Purpose |
|---|---|
| `diagnostics.py` | 25+ environment checks (packages, env vars, config, network, permissions, LLM providers) |
| `llm.py` | Multi-provider LLM integration (Anthropic, OpenAI, Google, Ollama) with auto-detect |
| `feedback.py` | Anonymized error feedback collection to central server |
| `cli.py` | CLI commands for doctor run/diagnose/providers |

**CLI Commands:**
- `observeco doctor run` — Full diagnosis + AI-powered fixes
- `observeco doctor run --auto-fix` — Apply fixes automatically (CI/scripting)
- `observeco doctor run --provider anthropic` — Force specific LLM
- `observeco doctor run --json` — JSON output for programmatic use
- `observeco doctor diagnose` — Quick health check (no fixes)
- `observeco doctor providers` — List available LLM providers

**Privacy-First Feedback:**
- No PII collected (no emails, API keys, file contents)
- Only diagnostic check results + fix outcomes
- User must explicitly opt in (runs on doctor execution)
- Opt-out: `OBSERVECO_NO_TELEMETRY=1`
- Data encrypted in transit (HTTPS)

**Feedback Collection Flow:**
```
User runs doctor → diagnostics collected → LLM fixes issues → outcome logged
    ↓
Anonymized payload sent to api.observeco.ai/v1/feedback
    ↓
Central server aggregates patterns: "30% of Slack users miss bot token scope"
    ↓
System prompt updated automatically → next user gets better advice
```

### A.7 LLM Provider Expansion (2026-05-29)

**Coverage:** 13 LLM providers auto-detected from environment variables.

| Category | Providers |
|---|---|
| Cloud (major) | Anthropic, OpenAI, DeepSeek, Google/Gemini, Mistral, Groq |
| Cloud (extended) | Together AI, OpenRouter |
| Local servers | Ollama, LM Studio, vLLM, TextGen, LocalAI |

**Auto-select preference:** Cloud providers (more capable) > local servers.

**OpenAI-compatible API:** `_call_openai_compatible()` handles DeepSeek, Mistral, Groq, Together, OpenRouter, and all local servers.

**Fallback:** If no provider detected, falls back to static help docs.

---

### A.8 Public API v1 (2026-05-29)

**Base URL:** `/api/v1`
**Authentication:** Bearer token via Authorization header

| Endpoint | Method | Description |
|---|---|---|
| `/health` | GET | Health check (no auth) |
| `/fleet` | GET | Fleet status overview |
| `/agents` | GET | List all agents |
| `/agents/{id}` | GET | Agent details |
| `/agents/{id}/health` | GET | Agent health history |
| `/agents/{id}/errors` | GET | Agent error history |
| `/agents/{id}/tokens` | GET | Token usage breakdown |
| `/events` | POST | Ingest OEF events |
| `/events` | GET | List recent events |
| `/risks` | GET | Risk classification summary |
| `/risks/classify` | POST | Classify a tool call |
| `/doctor/diagnostics` | GET | Run diagnostics |

---

### A.9 Telegram Adapter (2026-05-29)

**Features:**
- HTML messages with inline keyboards
- Webhook verification (X-Telegram-Bot-Api-Secret-Token)
- Approval workflow via inline buttons
- Set webhook URL programmatically

**Env vars:** OBSERVECO_TG_BOT_TOKEN, OBSERVECO_TG_CHAT_ID, OBSERVECO_WEBHOOK_SECRET

---

### A.10 Docker Image (2026-05-29)

**Build:** Multi-stage, Python 3.12-slim, non-root user
**Port:** 8080 (dashboard)
**Health check:** GET /api/health
**.dockerignore:** Prevents .git, secrets, data, docs from leaking into image

---

### A.11 OAuth2 Authentication (2026-05-29)

**Providers:** Google, GitHub, generic OIDC, local mode
**Session:** Cookie-based, 7-day expiry, Secure + SameSite=lax
**CSRF:** State parameter verified on callback
**Dashboard endpoints:** /auth/login, /auth/callback, /auth/logout, /auth/me

---

## FINAL STATUS — 2026-05-29 22:55 GMT+8

### All Phases Complete

| Phase | Tasks | Status |
|---|---|---|
| Phase 1 — Foundation | 11/11 | ✅ Complete |
| Phase 2 — Production Ready | 8/8 | ✅ Complete |
| Phase 3 — World Class | 7/7 | ✅ Complete |
| **Total** | **26/26** | **✅ Complete** |

### Independent Reviews

10 reviews completed. All critical and high issues resolved.

### Published

- PyPI: `pip install observeco` (v0.1.0)
- GitHub: `github.com/observeco/observeco`
- Docker: Multi-stage image ready
- Landing page: Cloudflare Pages deployed

### Remaining

- Custom domains: observeco.ai + observeco.com (2 min in Cloudflare dashboard)

### Commits

18 commits pushed to GitHub. All code reviewed and merged.

---

## Phase 8 — Harness Adapter Expansion (Post-Launch)

**Trigger:** mem0's "State of Memory in Agent Harness" article (Jun 2026) — 27K views, 494 bookmarks. Confirms harness diversity is real and growing. Hermes + OpenClaw coverage is strong, but Claude Code / Codex CLI / Cursor users get a thin experience.

**Current state vs mem0's harness taxonomy:**

| mem0 Harness | Detected | Health | Tokens/Memory | What's needed |
|-------------|----------|--------|--------------|--------------|
| **Hermes** | ✅ Full | ✅ Full | ✅ Full | Nothing |
| **OpenClaw** | ✅ Full | ✅ Full | ✅ Full | Nothing |
| **Claude Code** | ❌ Process only | ✅ Alive/dead | ❌ None | HarnessAdapter for `~/.claude/projects/*/` |
| **Codex CLI** | ❌ Process only | ✅ Alive/dead | ❌ None | HarnessAdapter for `.codex/` SQLite DB |
| **Cursor** | ❌ Not detected | ✅ If process runs | ❌ None | HarnessAdapter for `.cursor/` |
| **Custom script** | ✅ LLM discovery | ✅ Process check | ❌ None | Manual agent add works |

**Goal:** Move from "Hermes + OpenClaw" to "any major harness" without rewriting the probe engine.

**Effort:** ~3d total (2.5d build + 0.5d test/document)

### 8.1 HarnessAdapter Interface — 30 min

Extract the existing probe/discovery logic behind a clean ABC so new adapters drop in as files.

```python
# src/observeco/adapters/base.py
class HarnessAdapter(ABC):
    """Plug an agent harness into ObserveCo."""
    
    @staticmethod
    @abstractmethod
    def detect() -> list[AgentConfig]:
        """Find agents of this harness type on the system."""
        ...
    
    @abstractmethod
    def get_memory_path(self) -> Optional[Path]:
        """Path to harness memory store (MEMORY.md, SQLite, etc.)."""
        ...
    
    @abstractmethod
    def get_token_estimate(self) -> Optional[dict]:
        """Token breakdown per component, or None if unknown."""
        ...
```

**Current adapters to refactor into this pattern:**

| Existing module | Becomes |
|----------------|---------|
| `config.py:_load_hermes_agents()` | `adapters/hermes.py:HermesAdapter` |
| `config.py:_load_openclaw_agents()` | `adapters/openclaw.py:OpenClawAdapter` |
| `clawforge/profile.py:_find_openclaw_agent()` | Merged into `OpenClawAdapter` |

**Key constraint:** The probe engine (`pulse/check.py`) does NOT change — it already probes by URL scheme, not by framework. The adapter only feeds agent metadata + token/memory data into the pipeline.

### 8.2 Claude Code Adapter — ~1d

**Source data:**

| Path | Contents | What we extract |
|------|----------|----------------|
| `~/.claude/projects/*/memory/MEMORY.md` | Agent-written notes, 200 line / 25KB cap | Memory Garden scan (same as Hermes MEMORY.md) |
| `~/.claude/projects/*/CLAUDE.md` | Human-authored config | Token estimate (config size) |
| `~/.claude/projects/*/memory/` | Subdirs: user/, feedback/, project/, reference/ | Token breakdown per category |

**Detection:** Look for `~/.claude/projects/` directory → each subdir is one Claude Code project/agent. Filter to active ones via `ps aux | grep claude`.

**Token analysis:** Read CLAUDE.md + MEMORY.md + all 4 subdirs → estimate tokens via same tokenizer used for SOUL.md analysis.

**Memory Garden:** Apply same duplicate/contradiction/debt scan to MEMORY.md.

**What shows in dashboard:**
- Agent name: `claude-{project_name}`
- Framework label: `Agent · Claude Code`
- Token breakdown: CLAUDE.md + memory/ subdirs
- Memory Garden: ✅ Same scan as Hermes
- Drift: ✅ Over time as MEMORY.md grows

### 8.3 Codex CLI Adapter — ~1d

**Source data:**

| Path | Contents | What we extract |
|------|----------|----------------|
| `.codex/memory/` | SQLite DB with user/project/guide tiers | Token estimate per DB query |
| `.codex/config` | CLI config | Agent metadata |

**Detection:** Scan common locations (`~/.codex/`, cwd `.codex/`, `$CODEX_DIR`). Match running processes.

**Token analysis:** Read SQLite memory tables → count stored entries → estimate tokens via average entry size. Simpler than Claude Code because Codex has a known DB schema.

**Note:** Codex memory has 24h staleness — entries older than 24h are archived. This is a useful datum for the dashboard ("memory last refreshed: X hours ago").

### 8.4 Cursor Adapter — ~0.5d

**Source data:**

| Path | Contents | What we extract |
|------|----------|----------------|
| `.cursorrules` | Agent instructions | Token estimate (file size → tokens) |
| `.cursor/` | Rules, snippets, context files | Token breakdown |

**Detection:** Check for `.cursorrules` in common paths (home, `~/projects/*/`). Cursor is primarily a GUI editor — process detection may miss it. Supplement with file-based detection.

**Token analysis:** Single-pass — read `.cursorrules` + `.cursor/` dir, estimate tokens. No MEMORY.md equivalent, so Memory Garden is N/A for Cursor.

**What shows in dashboard:**
- Agent name: `cursor-{project_name}`
- Framework label: `Agent · Cursor`
- Token breakdown: Rules + snippets only
- Memory Garden: ❌ Not applicable (no MEMORY.md equivalent)

### 8.5 Discovery Pipeline Update

**Current flow (`auto_detect.py`):**
```
Tier 1: Hermes config → OpenClaw workspace → observeco.yml
Tier 2: LLM process discovery fallback
```

**Updated flow:**
```
Tier 1: All HarnessAdapters run (parallel, 5s timeout each)
  ├─ HermesAdapter (existing, fast)
  ├─ OpenClawAdapter (existing, fast)
  ├─ ClaudeCodeAdapter (new)
  ├─ CodexCLIAdapter (new)
  └─ CursorAdapter (new)
Tier 2: LLM process discovery (when Tier 1 returns < 2 agents)
```

**Each adapter runs independently.** A crash in CursorAdapter doesn't block Hermes detection. This is the same isolation principle as Phase 7.1 event bus.

### 8.6 Not in Scope for Phase 8

| Feature | Why Not | Notes |
|---------|---------|-------|
| LangChain/CrewAI/LlamaIndex deep integration | OTel listener on 4318 already captures OpenInference spans from all 28 frameworks | Harness adapters are for INFRASTRUCTURE-level observability. Framework-level observability goes through OTel. |
| Auto-heal for Claude Code processes | Possible but risky — Claude Code sessions are usually interactive | Defer until post-launch feedback |
| Bidirectional gateway for non-Hermes | Not a harness problem | Separate Phase 3 work |
| Windows harness detection | Phase 4 deferral | |

### 8.7 Priority Order

| # | Adapter | Effort | Value | Users Reached |
|---|---------|--------|-------|--------------|
| **1** | HarnessAdapter interface | 30 min | Unlocks all others | Foundation |
| **2** | Claude Code | 1d | High — Claude Code is #1 coding agent | 100K+ daily users |
| **3** | Codex CLI | 1d | Medium — growing fast | 50K+ daily users |
| **4** | Cursor | 0.5d | Medium — large GUI userbase | 200K+ daily users |

**Recommendation:** Adapters 2+3 cover the two biggest coding-agent harnesses. Build those first. Cursor is GUI-heavy and harder to detect — lowest ROI of the three.

### 8.8 Harness-Agnostic Marketing Position

**After Phase 8, the messaging becomes:**

> *"ObserveCo monitors your agents — Claude Code, Codex, Cursor, Hermes, OpenClaw, or custom — on a single dashboard. One pane for every agent on your machine."*

**Before Phase 8 (today), the honest position is:**

> *"Full observability for Hermes and OpenClaw. Process-level health for any other agent framework."*

---

*Document continues. Phase 8 is post-launch work — all items above are 🔴 Planned, not built.*

**Trigger:** Inspired by necmttn's livetrace project — real-time span streaming to frontend UIs.

### 4.1 OpenTelemetry Bridge
- Map OEF events → OTel spans (tool_call → span, risk_alert → event, error → span with error status)
- Export to any OTel-compatible backend (Datadog, Grafana, Jaeger, Zipkin)
- Use existing `dashboard/otel.py` endpoint as foundation

### 4.2 WebSocket Real-Time Streaming
- Add WebSocket endpoint to dashboard for live event streaming
- Replace polling with push-based updates
- Support filtered streams (by agent, risk level, event type)

### 4.3 OTel Span Format for OEF
- Extend OEF with OTel-compatible fields (trace_id, span_id, parent_span_id)
- Enable distributed tracing across agent runs
- Correlate with existing failure correlation module

### A.12 OpenTelemetry Bridge (2026-05-29)

**Module:** `src/observeco/otel_bridge.py`

Converts OEF events to OTel-compatible spans for export to any observability backend.

| Feature | Description |
|---|---|
| OEF → OTel | Map tool_call, risk_alert, error, heartbeat events to OTel spans |
| OTLP export | JSON format for Datadog, Grafana, Jaeger |
| Jaeger export | Jaeger-compatible span format |
| Deterministic IDs | trace_id and span_id derived from event data |
| Rich attributes | agent.id, agent.runtime, tool.name, risk.level, error.type |

### A.13 WebSocket Real-Time Streaming (2026-05-29)

**Module:** `src/observeco/realtime.py`

| Endpoint | Type | Description |
|---|---|---|
| `/ws/events` | WebSocket | Live event streaming with filters |
| `/api/v1/stream/sse` | SSE | Fallback for environments without WebSocket |
| `/api/v1/stream/status` | HTTP | Streaming status (clients, buffer size) |

**Features:**
- Filtered streams: agent, risk_level, event_type
- Buffer: last 50 events for new clients
- Auto-cleanup of disconnected clients

### A.14 CLI Commands (Phase 4)

| Command | Description |
|---|---|
| `observeco otel export` | Export session as OTel trace |
| `observeco otel export --format jaeger` | Export in Jaeger format |
| `observeco otel export --session <id>` | Export specific session |

---

## FINAL STATUS — 2026-05-29 23:55 GMT+8

### All Phases Complete

| Phase | Tasks | Status |
|---|---|---|
| Phase 1 — Foundation | 11/11 | ✅ Complete |
| Phase 2 — Production Ready | 8/8 | ✅ Complete |
| Phase 3 — World Class | 7/7 | ✅ Complete |
| Phase 4 — OTel + Real-Time | 3/3 | ✅ Complete |
| **Total** | **29/29** | **✅ Complete** |

### Independent Reviews

11 reviews completed. All critical and high issues resolved.

### Published

- PyPI: `pip install observeco` (v0.1.0)
- GitHub: `github.com/observeco/observeco`
- Docker: Multi-stage image ready
- Landing page: Cloudflare Pages deployed
- Homebrew: Formula ready

### Remaining

- Custom domains: observeco.ai + observeco.com (2 min in Cloudflare dashboard)

### Commits

20+ commits pushed to GitHub. All code reviewed and merged.

---

*This document is the single source of truth for ObserveCo. All tasks complete. Ready for launch.*

---

### 3.30 Context Health Score (🔴 Spec)

**Tagline:** *The check engine light for your agent's brain.*

**What it is:** A single number (0–100) per agent that answers "is my agent's context healthy right now?" The user doesn't need to understand context windows, drift, or memory bloat. They see 42 and they know something's wrong. Everything else in the dashboard feeds into why it's 42.

**The problem it solves:** Silent context collapse. An agent works fine for 10 turns, then starts forgetting things on turn 11 because context window pressure triggered silent eviction. The user doesn't notice until they get a weird response. By then, the conversation is already degraded. There is no check engine light.

#### RDR: Context Health Score

```
Problem: Users have no way to know if their agent's context is healthy until it breaks.
Solution: Composite score (0-100) from 6 signals, displayed on fleet cards and agent profile.
Key constraint: Must compute in <500ms with 20 agents. Must degrade gracefully when plugin data unavailable.
Success metric: Score correlates >0.7 with manual "is this agent working well?" assessment across 50 sessions.

States explicitly specified:
[x] Happy path (all 6 signals available, score computed)
[x] Empty state (no pulse data yet — agent just discovered)
[x] Loading state (computing, spinner on gauge)
[x] Error state (scoring engine crash — show last known score + ⚠ badge)
[x] Partial data state (plugin not installed — 5 of 6 signals, weight redistributes)
[x] Stale data state (no pulse in >5min — show score with "stale" badge + last-computed timestamp)
[x] Timeout state (computation >2s — show last known score + recompute in background)
[x] Degraded state (3+ signals unavailable — show "Insufficient data" instead of number)

Lifecycle specified:
[x] Start: first pulse triggers initial computation. Displays "—" until first score.
[x] Run: recomputed every pulse cycle (30s). Cached in pulse_log.
[x] Crash: scoring engine exception logged, last known score preserved with ⚠ badge.
[x] Reboot: resumes from last cached score in pulse_log.
[x] Cleanup: old scores pruned with pulse_log retention (7d free, unlimited pro).
[x] Stale detection: timestamp on score. >5min = stale badge. >1h = "monitoring may be stopped."
```

#### States & edge cases

| State | What Shows |
|-------|-----------|
| No pulse data yet (agent just discovered) | Score shows "—" with "Collecting data..." label |
| All 6 signals available | Full score with radar breakdown |
| Plugin not installed (sources_skipped unavailable) | Score from 5 signals, weight redistributed pro-rata. Badge: "Partial (plugin not installed)" |
| 3+ signals unavailable | "Insufficient data" — no number displayed |
| Score <70 | 🟡 Yellow badge on fleet card |
| Score <50 | 🟠 Orange + dashboard warning banner |
| Score <40 | 🔴 Red + push alert (Pro) or prominent dashboard banner (Free) |
| Stale data (>5min since last pulse) | Score with "stale" badge + timestamp |
| Stale data (>1h) | "Monitoring may be stopped" + last known score |
| Loading | Spinner on gauge, placeholder number |
| Scoring engine error | Last known score + ⚠ badge + "Recomputing..." |

#### Lifecycle

- **Start:** First pulse triggers initial computation. Displays "—" until first score.
- **Run:** Recomputed every pulse cycle (30s). Cached in `pulse_log` as `context_health_score` column.
- **Crash:** Scoring engine exception logged. Last known score preserved with ⚠ badge. Next successful pulse overwrites.
- **Reboot:** Resumes from last cached score in `pulse_log`. No recalculation needed on startup.
- **Cleanup:** Old scores pruned with `pulse_log` retention (7d free, unlimited pro).
- **Stale detection:** Timestamp on score. >5min = stale badge. >1h = "monitoring may be stopped".

#### Score composition (weighted):

| Signal | Weight | Source | Direction |
|--------|--------|--------|----------|
| Memory bloat | 20% | MEMORY.md size trend (tokens, 7d) | Higher = worse |
| Drift delta | 20% | `chisel_drift` table, 7d slope | Upward = worse |
| Context window utilisation | 20% | Plugin per-turn logs (when available) or estimated from SOUL.md + skills loaded | >70% sustained = worse |
| Error rate (24h) | 20% | `pulse_log` error entries / total pulses | Higher = worse |
| Sources-skipped ratio | 10% | ClawForge plugin stats (loaded vs skipped per turn) | High skip = healthy (efficient filtering). Low skip with high token count = bloated |
| Stale signal depth | 10% | Agent inbox unconsumed count (GS-013 metric) | Higher = worse |

**Score bands:**

| Band | Display | Trigger | Action |
|------|---------|---------|--------|
| 80–100 | 🟢 Green | Healthy | None |
| 60–79 | 🟡 Yellow | Warning — something trending wrong | Dashboard badge |
| 40–59 | 🟠 Orange | Degraded — active problem | Dashboard alert + recommended action |
| 0–39 | 🔴 Red | Critical — agent brain is failing | Push alert (Pro) or prominent dashboard banner (Free) |

**Where it appears:**
- **Fleet view:** Small badge on each agent card (colour + number)
- **Agent Profile (P1):** Prominent score gauge at top, with breakdown radar chart showing each sub-signal
- **Anomalies Inbox (P3):** Score drops >20 points in 24h surface as a high-priority anomaly
- **Companion Mode (P2):** `🧠 Context Health: 72 (↓3 this week)` in terminal summary

**Free vs Pro:**

| Feature | Free | Pro |
|---------|------|-----|
| Current score | ✅ | ✅ |
| 7d trend arrow | ✅ | ✅ |
| Sub-signal breakdown | ✅ Top 3 contributors | ✅ Full radar chart + historical |
| Push alerts on threshold breach | ❌ Dashboard only | ✅ Telegram/webhook/email |
| Regression detection (score vs 14d baseline) | ❌ | ✅ |
| Fleet comparison | ❌ | ✅ |

**Implementation notes:**

- Score recomputed on every pulse cycle (30s). Cached in `pulse_log` as `context_health_score` column.
- Sub-signals stored as JSON blob in `context_health_breakdown` column for drill-down.
- When ClawForge plugin is not installed, `sources_skipped_ratio` returns null and weight redistributes pro-rata across remaining signals.
- Scoring weights configurable via `observeco config set context_health.weights '{...}'`.

**Constraints register:**

| Constraint | Type | Verification |
|-----------|------|-------------|
| Computation latency <500ms per agent | Hard | Benchmark with 20 agents, all signals |
| Degrades when signals missing | Hard | Remove plugin data → score still computes (weight redistributes) |
| Score range 0–100 always (not 0–97 or 101) | Hard | Unit test: all inputs → score in [0,100] |
| No external API call for scoring | Hard | Scoring is pure math on local DB data. No LLM needed. |
| Cross-platform: scoring runs on Python 3.10+ | Hard | py_compile on Windows + Mac |

**Success metrics:**

| Metric | Target | Measurement |
|--------|--------|------------|
| Score accuracy | >0.7 correlation with human assessment | 50-session audit: human rates agent "working well?" y/n, compare to score band |
| Score stability | <10pt swing per pulse in healthy agent | 24h observation of stable agent, measure variance |
| Detection latency | Score drops >20pts within 2 pulse cycles of real degradation | Inject memory bloat, measure time to score change |
| User comprehension | New user understands score in <10s | "What does 42 mean?" user test — no docs |

**Effort:** ~2 days (1d scoring engine + 0.5d dashboard widget + 0.5d fleet badge)

> ⚠️ **Model flag:** Weighted scoring formula and score composition are reasoning tasks — requires thinking about signal weighting, normalisation, edge cases (all signals missing?), and graceful degradation → use Kimi 2.6. Dashboard widget and fleet badge are pattern tasks → use DeepSeek V4 Flash. See §13.3.

---

### 3.31 Agent Relapse Prevention ("What Changed?") (🔴 Spec)

**Tagline:** *That edit broke something. Here's proof.*

**What it is:** A timeline view that annotates every SOUL.md edit, plugin install/remove, config change, and knowledge gap discovery on a single line. Then overlays degradation signals — drift spikes, error bursts, context health drops — so correlation is immediately visible.

**The problem it solves:** Configuration drift. A user tweaked SOUL.md two weeks ago, added a plugin, changed a setting. Everything worked. Now something's off. They don't know what changed. There's no git blame for agent configuration.

#### RDR: Agent Relapse Prevention

```
Problem: Users tinker with config but never track what changed. When something breaks, they can't correlate cause.
Solution: Timeline correlating config events (SOUL.md edit, plugin install, config change) with degradation signals (drift, errors, context health drops).
Key constraint: Event capture must be <2s from filesystem change to DB write. Timeline must render 90d of events in <1s.
Success metric: >70% of degradation events correctly attributed to a specific config change.

States explicitly specified:
[x] Happy path (changes recorded, degradation overlaid)
[x] Empty state (no config changes — agent at defaults)
[x] Loading state (timeline skeleton with date placeholders)
[x] Error state (event log unreadable — diagnostic message)
[x] Partial data (changes exist but no degradation — green annotations)
[x] Stale data (no events >24h and agent running — "No recent changes")
[x] Timeout state (timeline load >1s — show cached timeline)
[x] Degraded state (event log corrupted — "Run observeco doctor events")

Lifecycle specified:
[x] Start: Event capture begins on first watch daemon start.
[x] Run: fswatch fires on SOUL.md/MEMORY.md changes.
[x] Crash: Event log writes atomic (temp + rename). Partial events never appear.
[x] Reboot: Resumes from last event. Does not retroactively scan.
[x] Cleanup: Events >90d pruned (free: 7d).
[x] Stale detection: >24h with no events and agent running = "No recent changes."
```

#### States & edge cases

| State | What Shows |
|-------|-----------|
| No config changes recorded | "No changes detected. Start editing SOUL.md or installing plugins to build timeline." |
| Changes exist but no degradation | Timeline shows events with green annotations: "No impact detected" |
| Correlation engine disagrees with user intuition | Show confidence level + "Report incorrect attribution" link |
| Loading | Skeleton timeline with date placeholders |
| Error reading event log | "Could not load change history. Run `observeco doctor events` to diagnose." |

#### Lifecycle

- **Start:** Event capture begins on first watch daemon start. Pre-existing edits not captured (no git history scan for v1).
- **Run:** fswatch fires on SOUL.md/MEMORY.md changes. Plugin lifecycle hooks fire on install/remove.
- **Crash:** Event log writes are atomic (write-to-temp + rename). Partial events never appear.
- **Reboot:** Resumes from last event. Does not retroactively scan for missed events.
- **Cleanup:** Events >90d pruned (free: 7d). Config event patches compacted after 30d.
- **Stale detection:** Event log timestamp checked. If >24h with no events and agent is running: "No recent changes."

**Data sources (event capture):**

| Event Type | Source | Captured Automatically? |
|------------|--------|------------------------|
| SOUL.md edit | fswatch daemon (chisel watch) | ✅ Via existing compression daemon |
| Plugin install/remove | OpenClaw plugin registry / ObserveCo plugin tracking | ✅ Plugin lifecycle hooks |
| Config change | `config.yaml` / `openclaw.json` fswatch | 🔴 Needs file watcher |
| Skill add/remove | Skills directory scan | ✅ Via skill audit |
| Memory edit (MEMORY.md) | fswatch | ✅ Via compression daemon |
| Cron job create/delete | Cron job registry scan | 🔴 Needs scanner |

**Degradation overlay signals:**

| Signal | Source | Display |
|--------|--------|--------|
| Context Health Score drop | §3.30 | Red marker, magnitude |
| Drift spike (>5%) | `chisel_drift` | Orange marker |
| Error burst (>3 in 1h) | `pulse_log` | Red marker |
| Memory debt score increase | Memory Garden | Yellow marker |
| Token cost spike (>2x baseline) | Token tracking (§14) | Orange marker |

**The timeline UI:**

```
Mon ────● SOUL.md edit (+340 tok)──────────────────────────────
Tue ──────────● Plugin installed: weather ─────────────────────
Wed ──────────────── ▼ Drift +8% ──────────────────────────────
Thu ───────────────────── ▼ Context Health: 78→54 ─────────────
Fri ─────────────────────────── ● Config changed ──────────────
Sat ──────────────────────────────── ▼ Error burst (5 in 1h) ──
```

**Correlation engine (Pro):** Identifies the most likely causal event for a degradation signal. Uses temporal proximity (degradation within 48h of a change) plus directional plausibility (a SOUL.md edit that increased token count by 40% is a strong candidate for a subsequent context health drop). Reports as: "Likely cause: SOUL.md edit on Monday (+340 tokens, +8% bloat). Context health dropped from 78→54 within 72h."

**Free vs Pro:**

| Feature | Free | Pro |
|---------|------|-----|
| 7d annotated timeline | ✅ | ✅ |
| Event + degradation overlay | ✅ | ✅ |
| Correlation engine (auto-attribution) | ❌ Manual inspection | ✅ Auto-attribution + confidence |
| Config change tracking | ❌ SOUL.md + plugins only | ✅ All sources |
| Historical timeline (>7d) | ❌ | ✅ Full history |

**Where it appears:**
- **Agent Profile (P1):** Dedicated "What Changed" tab below Context Health Score
- **Anomalies Inbox (P3):** Unexplained degradation with nearby config events surfaces as anomaly

**Implementation notes:**
- New table: `config_events(id, agent_name, event_type, description, delta_tokens, timestamp)`
- SOUL.md diffs stored as patch files (not full snapshots) in `~/.observeco/events/`
- Correlation engine: temporal window scan (48h look-back) + weighted scoring. Not ML — rule-based heuristics with explainable output.

**Constraints register:**

| Constraint | Type | Verification |
|-----------|------|-------------|
| Event capture latency <2s from filesystem change to DB write | Hard | fswatch latency benchmark |
| Timeline renders 90d of events in <1s | Hard | Load test with 200 events |
| Diffs stored as patches (not full snapshots) | Hard | Verify `~/.observeco/events/` contains .patch files |
| Correlation engine: temporal window 48h, explainable output | Hard | Unit test: known causal pair → correct attribution |
| No requirement for git history | Hard | Works without any git repo |

**Success metrics:**

| Metric | Target | Measurement |
|--------|--------|------------|
| Event capture completeness | >95% of SOUL.md edits captured | Controlled test: edit SOUL.md 20x, verify 19+ in event log |
| Correlation accuracy | >70% of degradation events correctly attributed | Inject 10 known-cause degradations, verify attribution |
| User comprehension | User identifies "what changed" in <30s | User test: show timeline, ask "what caused the issue?" |

**Effort:** ~2 days (0.5d event capture + 0.5d timeline UI + 1d correlation engine)

> ⚠️ **Model flag:** Event capture and timeline UI are pattern tasks → use DeepSeek V4 Flash. Correlation engine (temporal ordering, causal attribution, confidence scoring, ruling out coincidences) is a reasoning task → use Kimi 2.6. See §13.3.

---

### 3.32 Plugin Firewall Score (🔴 Spec)

**Tagline:** *Which plugin is eating your tokens and breaking your agent?*

**What it is:** Per-plugin ranking by token cost per call, error rate, latency impact, and success rate. Red/yellow/green traffic light. Makes plugin quality visible for the first time.

**The problem it solves:** Plugin misbehaviour. A plugin is eating tokens, causing latency, or subtly changing agent behaviour. No visibility into which plugin is doing what, because OpenClaw abstracts that. Users install plugins, forget about them, and they quietly drain tokens and degrade responses.

#### RDR: Plugin Firewall Score

```
Problem: Plugins are opaque. Users install them, forget about them, they drain tokens and degrade responses.
Solution: Per-plugin ranking by token cost, error rate, latency, success rate. Red/yellow/green traffic light.
Key constraint: Must read from existing plugin-stats.db (no new instrumentation). Aggregation <1s for 20 plugins.
Success metric: Cost estimation accuracy ±20% of actual provider billing over 7d.

States explicitly specified:
[x] Happy path (all plugin data available, ratings computed)
[x] Empty state (no plugins installed — "Install a plugin to see cost analysis")
[x] Loading state (computing ratings, spinner on table)
[x] Error state (plugin-stats.db unreadable — "Run observeco doctor plugins")
[x] Partial data (plugin installed but <10 calls — "Insufficient data")
[x] Stale data (no hook events >24h — "Data may be stale" badge)
[x] Timeout state (aggregation >1s — show cached ratings)
[x] Degraded state (plugin-stats.db missing — "Install ClawForge or trace-hook plugin")

Lifecycle specified:
[x] Start: First query returns empty if no plugin data.
[x] Run: Aggregation recompute hourly. Traffic lights cached.
[x] Crash: Last cached ratings preserved with timestamp.
[x] Reboot: Reads existing plugin-stats.db. No recalculation.
[x] Cleanup: Plugin stats >30d pruned (free: 7d).
[x] Stale detection: Last hook event >24h = stale badge.
```

#### States & edge cases

| State | What Shows |
|-------|-----------|
| No plugins installed | "No plugins detected. Install a plugin to see cost analysis." + link to ClawForge docs |
| Plugin installed but no hook stats yet | "Plugin tracking active. Data available after 24h of agent activity." |
| Plugin data available but <10 calls | Show table with "Insufficient data (N calls). Ratings improve at 10+ calls." |
| All plugins green | Table with green ratings. "All plugins healthy." summary |
| One plugin red | Red rating highlighted. "Plugin X: consider disabling. $Y/day, Z% error rate." actionable recommendation |

#### Lifecycle

- **Start:** First query to `/api/agent/{name}/plugins`. Returns empty if no plugin data.
- **Run:** Aggregation recompute hourly. Traffic lights cached between recomputes.
- **Crash:** Last cached ratings preserved with timestamp.
- **Reboot:** Reads existing plugin-stats.db. No recalculation needed.
- **Cleanup:** Plugin stats >30d pruned (free: 7d).
- **Stale detection:** If last hook event >24h old: "Plugin data may be stale" badge.

**Per-plugin metrics:**

| Metric | Source | Calculation |
|--------|--------|------------|
| Token cost per call | Plugin hook stats (before_tool_call → after_tool_call token delta) | Mean tokens consumed per invocation |
| Call frequency | Hook event count | Invocations per 24h |
| Error rate | Hook error events / total hook events | % |
| Latency impact | Hook execution duration (ms) | P50 + P95 |
| Success rate | Tool result success/fail | % |
| Daily cost estimate | Token cost × call frequency × provider rate | USD/day |

**Traffic light thresholds:**

| Rating | Criteria | Display |
|--------|-----------|---------|
| 🟢 Green | Error rate <2%, latency P95 <500ms, cost < $0.01/day | No action |
| 🟡 Yellow | Error rate 2–10%, or latency P95 500ms–2s, or cost $0.01–0.10/day | Monitor |
| 🔴 Red | Error rate >10%, or latency P95 >2s, or cost >$0.10/day | Recommend disable |

**Where it appears:**
- **Agent Profile (P1):** Plugin table with traffic lights, sortable by any column
- **Fleet view:** Aggregate plugin cost badge per agent card (total $/day from all plugins)
- **Anomalies Inbox (P3):** Plugin turning red within 24h surfaces as anomaly
- **Companion Mode (P2):** Top 3 most expensive plugins in terminal summary

**Data dependency:** Requires the ClawForge plugin (§3.16) or OpenClaw trace-hook plugin to be installed and reporting per-turn hook stats. When neither is installed, Plugin Firewall shows "Install plugin tracking to enable" with install instructions.

**Free vs Pro:**

| Feature | Free | Pro |
|---------|------|-----|
| Per-agent plugin table | ✅ | ✅ |
| Traffic light ratings | ✅ | ✅ |
| Daily cost estimate | ✅ | ✅ |
| Cross-fleet plugin comparison | ❌ | ✅ |
| Auto-disable recommendation | ❌ | ✅ |
| Budget threshold alerts | ❌ | ✅ |

**Implementation notes:**
- Reads from `plugin-stats.db` (ClawForge) or ObserveCo trace-hook plugin data
- Aggregation: rolling 24h window, recomputed hourly
- No new data collection — processes existing hook timing data

**Constraints register:**

| Constraint | Type | Verification |
|-----------|------|-------------|
| Reads from existing plugin-stats.db (no new instrumentation) | Hard | Verify no new data-collection code |
| Aggregation <1s for 20 plugins | Hard | Benchmark |
| Traffic light thresholds configurable | Soft | `observeco config set plugin_firewall.thresholds '{...}'` |
| Works with ClawForge plugin OR ObserveCo trace-hook | Hard | Test both data sources independently |

**Success metrics:**

| Metric | Target | Measurement |
|--------|--------|------------|
| Cost estimation accuracy | ±20% of actual provider billing | Compare estimate vs invoice over 7d |
| Detection latency for red plugin | <1h from threshold crossing to red rating | Inject high-error plugin, measure time to red |

**Effort:** ~1.5 days (0.5d aggregation + 1d UI table + traffic light logic)

---

### 3.33 Context Fire Drill (🔴 Spec)

**Tagline:** *Will your agent survive tomorrow?*

**What it is:** A simulation that projects whether an agent would survive a long conversation (N turns) using its current profile data. Reports: what hits the context limit first, which skills would get evicted, estimated degradation point, and recommended actions to extend runway.

**The problem it solves:** Reactive, not proactive. Users find out their agent can't handle a long conversation *during* the long conversation. By then, context is already corrupted and the session is lost.

#### RDR: Context Fire Drill

```
Problem: Users discover context overflow mid-conversation. By then, the session is lost.
Solution: Simulation projecting agent survival across N turns with configurable scenarios.
Key constraint: Must complete <3s. Must work with agent profile data only (no agent instrumentation).
Success metric: Degradation point predicted ±20% of actual conversation endpoint.

States explicitly specified:
[x] Happy path (simulation completes, shows verdict)
[x] Empty state (no turn history — "Run 10+ turns first")
[x] Loading state (spinner during simulation, <3s)
[x] Error state (insufficient profile data — diagnostic message)
[x] Partial data (limited turn history — low confidence warning)
[x] Stale data (profile data >1h old — warning)
[x] Timeout state (simulation >3s — show cached result if available)
[x] Degraded state (SOUL.md missing — "Cannot simulate")

Lifecycle specified:
[x] Start: Runs on-demand, not a daemon. No persistent state.
[x] Run: Reads profile snapshot at invocation time.
[x] Crash: No state to lose. Each invocation independent.
[x] Reboot: N/A — stateless.
[x] Cleanup: No state to clean.
[x] Stale detection: N/A — always reads fresh data.
```

#### States & edge cases

| State | What Shows |
|-------|-----------|
| Agent just discovered (no turn history) | "Not enough data for simulation. Run 10+ turns first." |
| <10 turns of history | "Limited data. Simulation accuracy improves with more turns." Show simulation with low confidence |
| No SOUL.md data | "Cannot simulate: agent profile (SOUL.md) not found." |
| Simulation exceeds context window at turn 12 | "⚠️ Degradation at turn 12. First evicted: [skill name]." |
| All scenarios pass | "✅ Agent survives 50 turns across all scenarios." |

#### Lifecycle

- **Start:** Simulation runs on-demand (button click or CLI). Not a daemon.
- **Run:** Reads current profile snapshot at invocation time.
- **Crash:** No persistent state. Each invocation is independent.
- **Reboot:** N/A — stateless.
- **Cleanup:** No state to clean.
- **Stale detection:** N/A — always reads fresh data.

**Simulation model:**

1. Load current profile: SOUL.md tokens, skills loaded, MEMORY.md size, typical turn size (from token tracking data)
2. Project N turns (default: 50) with realistic growth: each turn adds ~200–600 tokens (user message + agent response + tool calls)
3. Identify eviction point: when context window utilisation exceeds 70%, which skills get demoted first? (Uses ClawForge's demotion order: stale memory → unused skills → workspace context)
4. Report: turns until degradation, turns until critical, first evicted skill, first evicted memory section

**Output example:**

```
🔥 Context Fire Drill — kepler

Current context: 8,400 tokens (6.5% of 128K window)
Projected after 50 turns: 31,200 tokens (24.4%)

Verdict: ✅ Survives 50 turns with current config

Sensitivity:
  • If turn size averages 800 tok (heavy tool use): ⚠️ Degradation at turn 38
  • If MEMORY.md grows >15KB: ⚠️ Degradation at turn 42
  • If 3 more skills added: ⚠️ Degradation at turn 31

First evicted: weather skill (turn 31, heavy scenario)
First memory loss: entries >30d old (turn 38, heavy scenario)

Recommendation: Current config is healthy. Re-run after major SOUL.md edits.
```

**Scenarios:**

| Scenario | Turn Size | Memory Growth | Skills Added | Context Limit |
|----------|-----------|---------------|-------------|---------------|
| Light (chat) | 200 tok | None | 0 | 128K |
| Normal (mixed) | 400 tok | +50 tok/turn | 0 | 128K |
| Heavy (debug + tools) | 800 tok | +100 tok/turn | +3 | 128K |
| Worst case (all tools) | 1,200 tok | +200 tok/turn | +5 | 128K |

**Where it appears:**
- **Agent Profile (P1):** "Run Fire Drill" button in Context Health section
- **Companion Mode (P2):** `observeco fire-drill --agent kepler` CLI command

**Free vs Pro:**

| Feature | Free | Pro |
|---------|------|-----|
| Run simulation | ❌ | ✅ |
| Scenario comparison | ❌ | ✅ |
| Historical projection (based on past conversations) | ❌ | ✅ |
| Scheduled fire drills (weekly auto-run) | ❌ | ✅ |

**Note:** Fire Drill is Pro-only because the primary value is proactive prevention — a Pro mindset. Free users get the Context Health Score (reactive); Pro users get to simulate the future (proactive).

**Constraints register:**

| Constraint | Type | Verification |
|-----------|------|-------------|
| Simulation completes <3s | Hard | Benchmark with 50-turn projection |
| No agent instrumentation required | Hard | Simulation reads only static profile data + aggregate turn stats |
| Scenario parameters configurable | Soft | CLI flags: `--turns N --turn-size N --skills N` |
| Projection accuracy: ±20% of actual degradation point | Hard | Validate against 20 known-conversation-endpoints |

**Success metrics:**

| Metric | Target | Measurement |
|--------|--------|------------|
| Prediction accuracy | Degradation turn predicted ±20% of actual | Run fire drill, then real 50-turn conversation, compare |
| User action rate | >30% of fire drill users take recommended action | Track: ran drill → then ran chisel compress or edited SOUL.md |

**Effort:** ~2 days (1d simulation engine + 0.5d UI + 0.5d CLI)

---

### 3.34 Session Insurance (🔴 Spec)

**Tagline:** *Your agent lost its mind at 3pm. Here's what it knew before that.*

**What it is:** Local checkpointing of agent conversation context state. Every N turns (default: 10), ObserveCo captures a lightweight snapshot of the agent's effective context — not the full transcript, but the key state: SOUL.md hash, loaded skills list, MEMORY.md hash, recent turn count, context window utilisation. If the agent crashes or context corrupts, the user can restore from the last checkpoint.

**The problem it solves:** Every agent user has lost a session and felt that gut punch. The agent was working great, then something broke — context overflow, silent eviction, corrupted memory, crash. The conversation is gone. There's no undo.

#### RDR: Session Insurance

```
Problem: Users lose agent sessions and have no way to recover. Context corruption or crash means the conversation is gone.
Solution: Local checkpointing of agent context state every N turns. On crash: provide resume kit with last known state.
Key constraint: Checkpoint write <100ms. Crash detection <60s. Resume kit must be text-only (pasteable).
Success metric: >99% of crash events produce a checkpoint. User resumes session in <2 min using kit.

States explicitly specified:
[x] Happy path (checkpoint exists, agent alive — "Last checkpoint: turn 23, 2h ago")
[x] Empty state (no checkpoints yet — "First checkpoint at turn 10")
[x] Loading state (saving checkpoint — brief spinner)
[x] Error state (checkpoint corrupted — "Integrity check failed")
[x] Partial data (plugin not installed — checkpoint lacks turn count and skills)
[x] Stale data (last checkpoint >24h and agent active — "May be stale")
[x] Timeout state (checkpoint write >100ms — write in background, don't block agent)
[x] Degraded state (crash detected but no checkpoint — "No checkpoint available for this crash")

Lifecycle specified:
[x] Start: Checkpointing begins after first 10 turns.
[x] Run: Every 10 turns, capture snapshot.
[x] Crash: Checkpoint write is atomic (temp + rename). Crash triggers immediate checkpoint.
[x] Reboot: Resumes turn counter from last checkpoint.
[x] Cleanup: Checkpoints >30d pruned (free: 7d, max 7 checkpoints).
[x] Stale detection: Last checkpoint >24h and agent active = stale badge.
```

#### States & edge cases

| State | What Shows |
|-------|-----------|
| No checkpoints yet (<10 turns) | "Session Insurance active. First checkpoint at turn 10." |
| Checkpoint exists, agent alive | "Last checkpoint: turn 23, 2h ago. Context Health: 78." No action needed |
| Agent crashed, checkpoint available | 🚨 "Agent crashed at [time]. Last checkpoint: turn 23 (15min before crash). [View checkpoint] [Export resume kit]" |
| Checkpoint corrupted | "Checkpoint integrity check failed. Next checkpoint at turn N+10." |
| Manual checkpoint | "✅ Checkpoint saved." button feedback |

#### Lifecycle

- **Start:** Checkpointing begins after first 10 turns. Displays "active" indicator.
- **Run:** Every 10 turns, capture snapshot. Crash triggers immediate checkpoint.
- **Crash:** Checkpoint write is atomic (temp + rename). Partial checkpoint never appears.
- **Reboot:** Resumes turn counter from last checkpoint. Does not require a full conversation replay.
- **Cleanup:** Checkpoints >30d pruned (free: 7d, max 7 checkpoints).
- **Stale detection:** If last checkpoint >24h and agent is active: "Checkpoint may be stale — run manual checkpoint."

**What gets checkpointed (lightweight — not full transcripts):**

| Field | Size | Purpose |
|-------|------|---------|
| `soul_md_hash` | 32 bytes | Detect identity drift |
| `soul_md_size_tokens` | 4 bytes | Context footprint |
| `skills_loaded` | ~200 bytes | Which skills were active |
| `memory_md_hash` | 32 bytes | Detect memory corruption |
| `memory_md_size_tokens` | 4 bytes | Memory footprint |
| `context_window_pct` | 4 bytes | How full the window was |
| `turn_count` | 4 bytes | Conversation depth |
| `recent_tool_calls` | ~500 bytes | Last 10 tool invocations |
| `context_health_score` | 4 bytes | §3.30 score at checkpoint |
| `timestamp` | 8 bytes | When |

**Total per checkpoint:** ~1KB. 50 checkpoints = 50KB. Negligible storage.

**Restore flow:**

1. User opens Agent Profile, sees "⚠️ Last session ended abnormally"
2. Clicks "View last checkpoint"
3. Sees: "Checkpoint from 2:47pm (13 turns in). Context Health: 81. Skills: github, browser-automation, himalaya. Memory: 4.2KB."
4. Options: "Restore skills list" / "Export snapshot" / "Compare to current state"

**Restore is advisory, not magic.** ObserveCo can't inject context back into a running OpenClaw session. What it CAN do:
- Tell the user exactly which skills to reload
- Show what MEMORY.md looked like before corruption
- Provide a "session resume kit" — a text block the user pastes as the first message to re-establish context: "I'm continuing from where we left off. Load skills: X, Y, Z. My memory file was last healthy at [hash]."

**Crash detection trigger:**
- Agent process dies unexpectedly (pulse check detects dead state)
- Context Health Score drops >30 points in <1h
- Error rate exceeds 50% in a 10-turn window
- Manual trigger: "Save checkpoint now" button

**Where it appears:**
- **Agent Profile (P1):** "Last Checkpoint" section with timestamp + restore options
- **Anomalies Inbox (P3):** Crash with available checkpoint surfaces as auto-restorable anomaly

**Free vs Pro:**

| Feature | Free | Pro |
|---------|------|-----|
| Auto-checkpoint every 10 turns | ✅ Local only, 7d retention | ✅ Unlimited retention |
| Crash detection + notification | ✅ Dashboard | ✅ Push alert |
| Session resume kit | ✅ | ✅ |
| Pre-edit snapshots (before SOUL.md changes) | ❌ | ✅ |
| Selective restore (pick which fields to restore) | ❌ | ✅ |
| Checkpoint comparison (diff two snapshots) | ❌ | ✅ |

**Implementation notes:**
- New table: `session_checkpoints(id, agent_name, turn_count, payload_json, created_at, trigger)`
- Checkpointing is passive — reads from existing data (SOUL.md hashes, plugin stats, pulse data). No active instrumentation of the agent itself.
- The "session resume kit" is a formatted text template populated from checkpoint data.

**Data pipeline:**
```
Agent turn ends (plugin hook)
  │
  ├── Turn counter increments
  │
  ├── Every 10th turn:
  │   ├── Hash SOUL.md + MEMORY.md
  │   ├── Read loaded skills list from plugin stats
  │   ├── Compute context_health_score
  │   ├── Write to session_checkpoints table (atomic)
  │   └── Delete oldest checkpoint if >retention limit
  │
  └── Crash detected (pulse dead OR health drop >30pts):
      ├── Immediate checkpoint (best-effort, may use cached data)
      └── Flag for anomaly inbox
```

**SPOF audit:** Checkpoint engine is passive — reads from existing data sources (plugin hooks, pulse data). No new data collection. If plugin not installed, checkpointing degrades to SOUL.md + MEMORY.md hash only (no turn count, no loaded skills).

**Constraints register:**

| Constraint | Type | Verification |
|-----------|------|-------------|
| Checkpoint write <100ms | Hard | Benchmark (1KB payload, SQLite WAL) |
| Checkpoint size <2KB per snapshot | Hard | Verify payload JSON size |
| Crash detection latency <60s | Hard | Kill agent process, verify crash checkpoint written within 60s |
| Resume kit is text-only (no binary, no script) | Hard | Verify output is pasteable text |
| Checkpoint integrity check (hash verify) | Hard | Corrupt a checkpoint file, verify detection |

**Success metrics:**

| Metric | Target | Measurement |
|--------|--------|------------|
| Checkpoint reliability | >99% of crash events produce a checkpoint | Kill 100 agent processes, verify 99+ checkpoints |
| Resume kit effectiveness | User resumes session in <2 min using kit | User test: crash agent, give resume kit, time to productive conversation |
| Storage footprint | <100KB per agent per month | Measure checkpoint storage after 30d of daily use |

**Effort:** ~2.5 days (1d checkpoint engine + 0.5d restore UI + 1d crash detection + resume kit)

---

### 3.35 Unified Agent Data Model (🔴 Spec)

**Tagline:** *One query layer, five surface views. Build the consumers first, extract the shared layer when patterns emerge.*

**What it is:** A composite data query that aggregates everything ObserveCo knows about an agent into a single payload. All five Context Intelligence features (§3.30–§3.34) plus the rollout surfaces (Agent Profile, Companion Mode, Anomalies Inbox, Journey) read from this layer.

**Design principle:** Build backwards. P1 (Agent Profile) ships with inline queries. When P3 (Anomalies Inbox) needs 70% of the same data, extract the shared layer. Premature abstraction on a product still finding its surface is how you get a beautiful ORM that fits nothing.

**Composite payload shape:**

```json
{
  "agent_name": "kepler",
  "identity": {
    "framework": "openclaw",
    "platform": "telegram",
    "status": "alive",
    "last_pulse": "2026-06-06T14:30:00+08:00"
  },
  "context_health": {
    "score": 78,
    "trend_7d": -3,
    "band": "yellow",
    "breakdown": {
      "memory_bloat": 15,
      "drift_delta": 12,
      "window_utilisation": 18,
      "error_rate": 5,
      "sources_skipped": 8,
      "stale_signals": 10
    }
  },
  "plugins": [
    {"name": "trace-hook", "rating": "green", "cost_per_day": 0.002, "error_rate": 0.01},
    {"name": "weather", "rating": "yellow", "cost_per_day": 0.04, "error_rate": 0.03}
  ],
  "changes": [
    {"type": "soul_edit", "when": "2026-06-03", "delta_tokens": 340},
    {"type": "plugin_install", "when": "2026-06-04", "name": "weather"}
  ],
  "recent_anomalies": [
    {"type": "drift_spike", "when": "2026-06-05", "magnitude": 8.2}
  ],
  "last_checkpoint": {
    "turn_count": 13,
    "timestamp": "2026-06-06T14:47:00+08:00",
    "context_health": 81
  },
  "fire_drill": {
    "survives_50_turns": true,
    "degradation_point_heavy": 38
  }
}
```

**API endpoint:** `GET /api/agent/{name}/profile` — returns full composite.

**Partial queries:** Each section is also independently queryable for surfaces that only need one piece:
- `GET /api/agent/{name}/context-health` — just §3.30
- `GET /api/agent/{name}/plugins` — just §3.32
- `GET /api/agent/{name}/changes` — just §3.31
- `GET /api/agent/{name}/checkpoint` — just §3.34

**Consumers:**

| Consumer | What It Reads | Priority |
|----------|-------------|----------|
| Agent Profile (P1) | Full composite | P1 |
| Anomalies Inbox (P3) | `recent_anomalies` + `context_health` + `changes` | P3 |
| Companion Mode (P2) | `identity` + `context_health` summary + top plugins | P2 |
| Journey (P4) | `identity` + boolean flags (has viewed brain, has run chisel, has alerts) | P4 |
| Fleet View | `context_health.score` + `plugins` aggregate cost per agent | P1 |

**Effort:** ~1 day (extraction from existing P1 inline queries once P3 is being built). NOT built upfront.

---

### 3.36 Cross-Reference Verification (Context Intelligence Layer)

**Per requirements-fidelity-playbook Trap 6.** All cross-references in §3.30–§3.35 verified:

| Reference | Points To | Status |
|-----------|-----------|--------|
| §3.30 sources_skipped_ratio → ClawForge plugin (§3.16) | ClawForge plugin tracks loaded/skipped sources per turn | ✅ Agrees |
| §3.30 stale_signal_depth → GS-013 metric | External standard, not ObserveCo spec | ✅ No contradiction (read-only dependency) |
| §3.31 event capture → chisel watch daemon (§3.13) | Existing compression daemon already monitors SOUL.md via fswatch | ✅ Agrees (reuses existing watcher) |
| §3.32 plugin data → plugin-stats.db (§3.16) | ClawForge plugin writes per-turn hook stats to plugin-stats.db | ✅ Agrees |
| §3.34 checkpoint data → plugin hooks (§3.16) | Plugin hooks provide turn count and loaded skills | ✅ Agrees. Degrades gracefully without plugin |
| §3.35 composite payload → all §3.30–§3.34 | Each sub-section independently queryable | ✅ No contradiction |
| §11 rollout P1 → §3.30, §3.31, §3.32 | All three spec'd in this document | ✅ Agrees |
| Free vs Pro gating across §3.30–§3.34 | Each feature has explicit Free/Pro table | ✅ No contradictions between sections |

**Tier mapping consistency check:**

| Feature | Free gets | Pro gets | Contradiction? |
|---------|----------|---------|----------------|
| §3.30 Context Health | Score + 7d trend + top 3 contributors | Full radar + push alerts + regression detection + fleet comparison | No |
| §3.31 Relapse Prevention | 7d timeline + overlay | Full history + correlation engine + all event sources | No |
| §3.32 Plugin Firewall | Per-agent table + traffic lights + cost | Cross-fleet comparison + auto-disable + budget alerts | No |
| §3.33 Fire Drill | ❌ Pro only | Full simulation + scenarios + scheduled drills | No (explicit Pro-only by design) |
| §3.34 Session Insurance | Auto-checkpoint 10 turns + 7d + crash notify + resume kit | Unlimited + selective restore + pre-edit snapshots + diff | No |

---

### 3.37 Anomalies Inbox (🔴 Spec)

**Tagline:** *Your agent has 3 problems right now. Here they are.*

**What it is:** A fleet-wide issue surfacing layer that reads from every data source in ObserveCo and surfaces actionable anomalies to the user. It's the activation moment — the feature that makes users care about Context Health Scores, Plugin Firewall ratings, and drift trends. Without the Inbox, those metrics sit on a dashboard nobody watches.

**The problem it solves:** Users don't know something's wrong until they get a weird response or a bill shock. By then, the damage is done. The Anomalies Inbox surfaces issues proactively — before the user notices.

#### RDR: Anomalies Inbox

```
Problem: Users discover agent problems only after damage (weird response, bill shock, session loss).
Solution: Fleet-wide anomaly scanner that surfaces issues proactively with severity, context, and recommended actions.
Key constraint: Must scan all data sources in <2s. Must not produce false positives that erode trust.
Success metric: >80% of surfaced anomalies are actionable (user takes response within 24h).

States explicitly specified:
[x] Happy path (anomalies found, displayed with severity + context)
[x] Empty state (no anomalies — "All agents healthy")
[x] Loading state (scanning — spinner on each section)
[x] Error state (data source unreachable — "部分扫描失败" badge)
[x] Partial data (some sources available, others not — show what's available)
[x] Stale data (last scan >5min — "Last scan: 5m ago" badge)
[x] Timeout state (scan >2s — show cached anomalies + "Scanning..." badge)
[x] Degraded state (all sources down — "Cannot scan — check ObserveCo daemon")

Lifecycle specified:
[x] Start: Scan on dashboard load + every 60s while tab is open.
[x] Run: Continuous scan cycle. New anomalies surface in real-time.
[x] Crash: Last scan results cached. Dashboard shows cached + "stale" badge.
[x] Reboot: Resumes from cached anomalies. No data loss.
[x] Cleanup: Resolved anomalies archived after 30d (free: 7d).
[x] Stale detection: Scan timestamp on every anomaly. >5min = stale badge.
```

#### Anomaly types (10 sources)

| # | Anomaly Type | Source | Severity | Detection Method | Free | Pro |
|---|-------------|--------|----------|-----------------|------|-----|
| 1 | **Dead agent** | pulse_log | 🔴 Critical | No pulse in >2min (2 cycles) | ✅ | ✅ |
| 2 | **Drift spike** | chisel_drift | 🟠 High | Drift delta >5% in 24h | ✅ | ✅ |
| 3 | **Error burst** | errors table | 🟠 High | >3 errors in 1h window | ✅ | ✅ |
| 4 | **Context health drop** | context_health (§3.30) | 🟠 High | Score drops >20pts in 24h | ✅ | ✅ |
| 5 | **Unexplained degradation** | context_health + config_events (§3.31) | 🟡 Medium | Score drop with no nearby config event | ✅ | ✅ + correlation engine |
| 6 | **Tripped circuit breaker** | circuit_breakers | 🔴 Critical | `tripped=1` | ✅ | ✅ |
| 7 | **Plugin turning red** | plugin_tracking (§3.32) | 🟡 Medium | Plugin rating changed from green→yellow or yellow→red in 24h | ✅ | ✅ |
| 8 | **Token cost spike** | token_logs (§14) | 🟡 Medium | Turn cost >3σ from rolling average | ❌ Pro only | ✅ + budget thresholds |
| 9 | **Crash + checkpoint available** | session_checkpoints (§3.34) | 🔴 Critical | Agent crashed, checkpoint exists for restore | ✅ | ✅ + auto-restore option |
| 10 | **Stale agent inbox** | signal inboxes | 🟡 Medium | >5 unconsumed signals in agent inbox >48h | ✅ | ✅ |

#### Anomaly data structure

```json
{
  "id": "anom_abc123",
  "type": "context_health_drop",
  "severity": "high",
  "agent_name": "kepler",
  "title": "Context Health dropped 24pts in 24h",
  "description": "Score fell from 78 to 54 between Jun 4-5. No config changes detected in this window.",
  "detected_at": "2026-06-06T14:30:00+08:00",
  "source": "context_health",
  "metric_before": 78,
  "metric_after": 54,
  "delta": -24,
  "recommended_action": "Check for memory bloat or increased error rate. Run Context Fire Drill to project impact.",
  "related_events": [
    {"type": "config_event", "when": "2026-06-03", "description": "SOUL.md edited (+340 tokens)"}
  ],
  "status": "open",
  "acknowledged_by": null,
  "resolved_at": null
}
```

#### Scan pipeline

```
┌─────────────────────────────────────────────────────────────┐
│                    Anomaly Scanner                          │
│                                                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ pulse_log│  │chisel_   │  │ errors   │  │ context_ │   │
│  │          │  │drift     │  │          │  │ health   │   │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘   │
│       │              │              │              │         │
│  ┌────┴─────┐  ┌────┴─────┐  ┌────┴─────┐  ┌────┴─────┐   │
│  │ circuit_ │  │ plugin_  │  │ token_   │  │ session_ │   │
│  │ breakers │  │ tracking │  │ logs     │  │checkpoint│   │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘   │
│       │              │              │              │         │
│  ┌────┴─────┐  ┌────┴─────┐                           │
│  │ config_  │  │ signal   │                           │
│  │ events   │  │ inboxes  │                           │
│  └────┬─────┘  └────┬─────┘                           │
│       │              │                                 │
│       └──────┬───────┘                                 │
│              ▼                                         │
│     ┌────────────────┐                                 │
│     │  Dedup + Rank  │  ← severity × age × agent      │
│     └────────┬───────┘                                 │
│              ▼                                         │
│     ┌────────────────┐                                 │
│     │  anomalies     │  → dashboard + push alerts     │
│     │  (in-memory)   │                                 │
│     └────────────────┘                                 │
└─────────────────────────────────────────────────────────────┘
```

**Scan cycle:**
1. Read all 10 data sources in parallel (asyncio.gather)
2. Run each source's detector function → produces list of raw anomalies
3. Deduplicate: same type + same agent + detected within 1h = merge (keep latest)
4. Rank: severity (critical > high > medium > info) × age (newer = higher) × agent importance
5. Return top 50 anomalies sorted by rank

**Dedup rule:** An anomaly is "the same" if: type matches AND agent matches AND detected within 1h. Merged anomalies update `detected_at` to latest and increment a `recurrence_count` field.

#### States & edge cases

| State | What Shows |
|-------|-----------|
| No anomalies | "✅ All agents healthy. Last scan: 12s ago." + green checkmark |
| 1-3 anomalies | Anomaly cards sorted by severity. "3 issues found" in header |
| 4+ anomalies | Anomaly cards + "Show all N" toggle. Header shows critical count: "2 critical, 3 warnings" |
| All agents dead | Red banner: "⚠️ All agents unreachable. Check ObserveCo daemon." + all anomaly cards |
| Some sources unreachable | Anomalies from available sources + "部分扫描失败 — 3/10 sources online" badge |
| Stale scan (>5min) | Cached anomalies + "Last scan: 8m ago — scanning..." badge |
| Scan timeout (>2s) | Show cached results + "Scan taking longer than expected" |
| Anomaly resolved | Card moves to "Resolved" tab with checkmark + timestamp |
| Acknowledged anomaly | Card dims (opacity 0.5) + "Acknowledged by user" badge |

#### Lifecycle

- **Start:** First scan on dashboard load. Results cached in memory.
- **Run:** Re-scan every 60s while Anomalies tab is open. Tab inactive = scan paused (saves resources).
- **Crash:** Last scan results cached in `~/.observeco/anomaly_cache.json`. Dashboard shows cached + stale badge.
- **Reboot:** Reads anomaly cache. If cache <5min old, shows cached. If older, triggers fresh scan.
- **Cleanup:** Resolved anomalies archived after 30d (free: 7d). Open anomalies never pruned.
- **Stale detection:** Each anomaly has `detected_at`. >5min since last scan = stale badge on header.

#### Severity classification

| Severity | Criteria | Display | Push (Pro) |
|----------|----------|---------|------------|
| 🔴 Critical | Dead agent, tripped circuit, crash+checkpoint | Red card, top of list | ✅ Immediate |
| 🟠 High | Drift spike >5%, error burst >3/h, context health drop >20pts | Orange card | ✅ Within 5min |
| 🟡 Medium | Plugin turning red, unexplained degradation, stale inbox, cost spike | Yellow card | ✅ Batched (hourly) |
| ℹ️ Info | New agent discovered, checkpoint saved, chisel completed | Grey card, collapsed by default | ❌ Dashboard only |

#### Recommended actions per anomaly type

| Anomaly Type | Recommended Action | Links To |
|-------------|-------------------|----------|
| Dead agent | "Check agent process. Run `observeco heal <agent>` to restart." | Heal button |
| Drift spike | "Review recent SOUL.md edits. Run Chisel to compress." | Agent Profile → What Changed tab |
| Error burst | "Check agent logs. May be API rate limiting or plugin failure." | Agent Profile → Logs |
| Context health drop | "Run Context Fire Drill to project impact. Check memory bloat." | Agent Profile → Context Health |
| Unexplained degradation | "No config change detected. Possible external factor. Monitor." | Agent Profile → What Changed |
| Tripped circuit | "Agent hit failure limit. Auto-heal exhausted. Manual intervention needed." | Heal button |
| Plugin turning red | "Disable or replace plugin. Check Plugin Firewall for details." | Agent Profile → Plugin Firewall |
| Token cost spike | "Unusual turn cost detected. Check for context bloat or model change." | Agent Profile → Token Usage |
| Crash + checkpoint | "Agent crashed. Restore from checkpoint?" | Session Insurance → Restore |
| Stale inbox | "Agent not consuming signals. Check daemon status." | Companion Mode |

#### Free vs Pro

| Feature | Free | Pro |
|---------|------|-----|
| Anomaly detection (all 10 types) | ✅ | ✅ |
| Dashboard anomaly feed | ✅ | ✅ |
| Severity classification | ✅ | ✅ |
| NEW badge on new anomalies | ✅ | ✅ |
| Resolved tab | ✅ 7d history | ✅ 30d history |
| Push alerts (Telegram/webhook/email) | ❌ Dashboard only | ✅ Per-severity routing |
| Anomaly attribution (auto-cause) | ❌ Manual inspection | ✅ Correlation engine |
| Anomaly recurrence tracking | ❌ | ✅ Pattern detection |
| Bulk acknowledge/resolve | ❌ | ✅ |
| Anomaly trend (are there more anomalies this week?) | ❌ | ✅ Weekly trend chart |

**Effort:** ~3 days (1d scanner engine + 1d dashboard UI + 1d anomaly cards + dedup)

**Constraints register:**

| Constraint | Type | Verification |
|-----------|------|-------------|
| Full scan completes <2s | Hard | Benchmark with 10 agents, all 10 sources |
| Dedup merges same-type anomalies within 1h window | Hard | Unit test: 3 identical anomalies within 1h → 1 merged |
| Max 50 anomalies returned per scan | Hard | Inject 100 anomalies, verify top 50 returned |
| Severity classification deterministic | Hard | Same input → same severity, every time |
| Discovery gap uses UTC timestamps | Hard | Test across DST boundary |
| Cached anomalies survive process restart | Hard | Kill scanner, verify cache file exists |

**Success metrics:**

| Metric | Target | Measurement |
|--------|--------|------------|
| False positive rate | <10% of resolved alerts marked "not actually a problem" | Track: resolution_action = "false_positive" / total resolved |
| Detection latency | Anomaly surfaced within 1 scan cycle (60s) of data availability | Inject anomaly data, measure time to appear in feed |
| User action rate | >60% of surfaced anomalies get an action within 24h | Track: anomalies with action / total anomalies |
| Scan uptime | >99% of scans complete without error | Track: failed scans / total scans |

> ⚠️ **Model flag:** Scanner engine, dashboard UI, and anomaly cards are pattern tasks → use DeepSeek V4 Flash. Rule engine design (reading 10+ data sources, correlating by timestamp, assigning severity, suppressing duplicates, attributing root cause with composable predicates) is the hardest reasoning task in the build → use Kimi 2.6. See §13.3.

---

### 3.38 Companion Mode (🔴 Spec)

**Tagline:** *Your agent ecosystem, in a single terminal command.*

**What it is:** `observeco companion` — a CLI command that prints a terminal status summary of the entire agent fleet. Same data model as the dashboard, different surface. Designed for OpenClaw launcher integration ("command-line ears") and power users who live in the terminal.

**The problem it solves:** Not everyone wants to open a browser to check agent health. Power users and OpenClaw launchers need a fast, scriptable status check that works in a terminal.

#### RDR: Companion Mode

```
Problem: Dashboard requires a browser. Power users and launchers need terminal-native status.
Solution: CLI command that reads the same data model and prints a colour-coded terminal summary.
Key constraint: Must complete <2s. Must work without a running dashboard. Must be scriptable (JSON output).
Success metric: User gets actionable status in <5s from running the command.

States explicitly specified:
[x] Happy path (fleet status printed with colour coding)
[x] Empty state (no agents discovered — "Run observeco agent discover")
[x] Loading state (scanning — spinner with progress)
[x] Error state (ObserveCo DB unavailable — "Cannot connect to pulse.db")
[x] Partial data (some agents unreachable — shown in red)
[x] Stale data (last pulse >5min — shown with ⚠ badge)
[x] Timeout state (scan >2s — show cached + "Warning: slow scan")
[x] Degraded state (DB corrupted — "Run observeco doctor db")

Lifecycle specified:
[x] Start: Runs on-demand. No daemon.
[x] Run: Single execution. Reads DB, prints, exits.
[x] Crash: No persistent state. Re-run is the recovery.
[x] Reboot: N/A — stateless.
[x] Cleanup: No state to clean.
[x] Stale detection: Pulse timestamps checked. >5min = ⚠ badge.
```

#### Output format

```
$ observeco companion

┌─────────────────────────────────────────────────────────────┐
│  ObserveCo Fleet — Sat 6 Jun 2026, 5:03 PM                │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  🟢 hound        87  ● Alive   22.9K tok  0 errors         │
│  🟢 raven        87  ● Alive   20.4K tok  0 errors         │
│  🟢 skeptical    87  ● Alive   19.5K tok  0 errors         │
│  🟢 pragma       81  ● Alive   22.6K tok  0 errors         │
│  🟢 dreamer      81  ● Alive   20.6K tok  0.2% err         │
│  🟢 pa           80  ● Alive   21.5K tok  1.4% err ⚠       │
│  🟡 aleph        79  ● Alive   21.2K tok  0.6% err         │
│  🟡 kepler       77  ⚠ Stale   20.1K tok  2 signals        │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│  📊 Fleet: 8 agents · 6 healthy · 2 warning · 0 critical  │
│  🔪 Chisel: 2 ready · 1 compressed                         │
│  ⚠️  Anomalies: 3 active (1 critical, 2 warnings)           │
└─────────────────────────────────────────────────────────────┘
```

#### CLI flags

| Flag | Description |
|------|-------------|
| `--json` | Output as JSON (for scripting) |
| `--watch` | Re-print every 10s (live mode) |
| `--agent <name>` | Show only one agent |
| `--anomalies` | Show only anomalies |
| `--compact` | Single-line-per-agent format |
| `--no-colour` | Disable ANSI colour codes |

#### JSON output shape

```json
{
  "timestamp": "2026-06-06T17:03:00+08:00",
  "fleet_summary": {
    "total": 8, "healthy": 6, "warning": 2, "critical": 0
  },
  "agents": [
    {
      "name": "hound",
      "context_health": 87,
      "status": "alive",
      "context_est_tokens": 22911,
      "error_rate": 0.0,
      "stale_signals": 0,
      "plugins": [],
      "anomalies": []
    }
  ],
  "anomalies_summary": {
    "total": 3, "critical": 1, "high": 0, "medium": 2
  }
}
```

#### Free vs Pro

| Feature | Free | Pro |
|---------|------|-----|
| Basic fleet status | ✅ | ✅ |
| Colour-coded output | ✅ | ✅ |
| Context health scores | ✅ | ✅ |
| Anomaly count | ✅ | ✅ |
| `--json` output | ✅ | ✅ |
| `--watch` live mode | ❌ | ✅ |
| `--anomalies` filter | ❌ | ✅ |
| Plugin cost summary | ❌ | ✅ |
| Historical comparison ("worse than yesterday") | ❌ | ✅ |

**Effort:** ~2 days (1d CLI + data reading + 1d output formatting + watch mode)

#### States & edge cases

| State | What Shows |
|-------|-----------|
| No agents discovered | "No agents found. Run `observeco agent discover` first." |
| All agents healthy | Green status dots, health scores, "Fleet: 8 agents · 8 healthy" |
| Some agents unhealthy | Red/amber dots for unhealthy agents, anomaly count in summary |
| DB unavailable | "Cannot connect to pulse.db. Is ObserveCo daemon running?" |
| Stale data (>5min) | Agents shown with ⚠ badge + "Last check: 8m ago" |
| Watch mode active | Refreshing every 10s, spinner in corner |
| JSON output | Raw JSON, no colours, no formatting |

#### Lifecycle

- **Start:** Runs on-demand. No daemon. Reads pulse.db directly.
- **Run:** Single execution (or 10s loop in watch mode). Prints, exits.
- **Crash:** No persistent state. Re-run is the recovery.
- **Reboot:** N/A — stateless.
- **Cleanup:** No state to clean.
- **Stale detection:** Pulse timestamps checked. >5min = ⚠ badge.

**Constraints register:**

| Constraint | Type | Verification |
|-----------|------|-------------|
| Output completes <2s | Hard | Benchmark with 8 agents |
| Works without running dashboard | Hard | Stop dashboard, verify companion still works |
| JSON output is valid | Hard | `python -m json.tool` on --json output |
| Watch mode refreshes every 10s ±1s | Hard | Time 10 refreshes, measure interval |
| No-colour mode strips ANSI codes | Hard | Pipe to `cat -v`, verify no escape sequences |
| Exit code 0 on success, 1 on error | Hard | Test both paths |

**Success metrics:**

| Metric | Target | Measurement |
|--------|--------|------------|
| Time to actionable status | <5s from command to understanding | User test: run command, time to "I know what to do" |
| Watch mode adoption | >20% of companion users try --watch | Track: watch mode invocations / total companion invocations |
| JSON output usage | >10% of companion users use --json | Track: --json invocations / total companion invocations |

---

### 3.39 Journey / Onboarding (🔴 Spec)

**Tagline:** *Your first 10 minutes with ObserveCo, guided.*

**What it is:** A "Get Started" tab that tracks which milestones the user has completed and guides them through the remaining ones. Reduces time-to-value from "installed but confused" to "seeing my agent's health in 3 minutes."

**The problem it solves:** Users install ObserveCo, see an empty dashboard, and leave. Onboarding converts installs into active users by showing progress and contextual help.

#### RDR: Journey / Onboarding

```
Problem: Users install ObserveCo, see empty dashboard, don't know what to do next.
Solution: Milestone tracker that shows progress and guides through setup steps.
Key constraint: Must not block dashboard usage. Milestones must be completable in <10 min total.
Success metric: >60% of new users complete 3+ milestones within first session.

States explicitly specified:
[x] Happy path (milestones displayed, progress bar showing completion)
[x] Empty state (first visit — hero banner with welcome message)
[x] Loading state (checking milestone completion — spinner)
[x] Error state (cannot check milestone status — "Skip for now" button)
[x] Partial data (some milestones unknown — show as pending)
[x] Stale data (milestone status >1h old — background re-check)
[x] Timeout state (milestone check >3s — show cached status)
[x] Degraded state (cannot determine milestone status — "Set up manually")

Lifecycle specified:
[x] Start: First visit shows hero banner. Milestones checked on load.
[x] Run: Milestones re-checked on each dashboard load. Progress updates in real-time.
[x] Crash: No persistent state beyond milestone completion flags.
[x] Reboot: Milestones re-checked from source data on next load.
[x] Cleanup: Milestones persist indefinitely. Hero banner dismissible.
[x] Stale detection: N/A — milestones are boolean, not time-series.
```

#### Milestones

| # | Milestone | How Completed | Effort |
|---|-----------|---------------|--------|
| 1 | **Install CLI** | `pip install observeco` detected | 30s |
| 2 | **Discover agents** | `observeco agent discover` finds ≥1 agent | 1min |
| 3 | **View Brain Analysis** | User opens Brain Analysis tab for any agent | 30s |
| 4 | **Run Chisel** | User runs `observeco chisel compress` or clicks Compress | 2min |
| 5 | **Set up alerts** | User configures Telegram webhook or email | 3min |
| 6 | **Run Context Fire Drill** | User clicks "Run Fire Drill" on any agent (Pro) | 1min |
| 7 | **Resolve first anomaly** | User acknowledges or resolves an anomaly | 1min |
| 8 | **View Companion** | User runs `observeco companion` | 30s |

**Progress:** 8 milestones. Progress bar = completed / 8. Hero banner shows until 3+ milestones complete, then auto-collapses.

#### Side panel (per-milestone detail)

Clicking a milestone opens a side panel with:
- **Completed:** What was done, when, link to view the result
- **Pending:** What to do, step-by-step instructions, estimated time
- **Locked:** Why it's locked (prerequisite not met), what to do first

#### Free vs Pro

| Feature | Free | Pro |
|---------|------|-----|
| Milestone tracker | ✅ | ✅ |
| Progress bar | ✅ | ✅ |
| Side panel with instructions | ✅ | ✅ |
| Hero banner (dismissable) | ✅ | ✅ |
| Milestones 1-5 | ✅ | ✅ |
| Milestones 6-8 (Fire Drill, anomaly resolve, Companion) | ❌ Locked | ✅ |
| Personalised recommendations ("Based on your fleet, try X next") | ❌ | ✅ |
| Milestone completion history | ❌ | ✅ |

**Effort:** ~2 days (1d milestone engine + 1d UI + side panel)

#### States & edge cases

| State | What Shows |
|-------|-----------|
| First visit (0 milestones) | Hero banner expanded, progress bar at 0%, all steps pending |
| 3+ milestones complete | Hero banner auto-collapsed, "Welcome — progress saved" note |
| All milestones complete | "🎉 All milestones complete! You're set up." + confetti |
| Milestone check fails | "Could not verify milestone status. [Skip for now]" |
| Side panel open | Panel slides in from right, milestone detail + actions |
| Side panel closed | Back to milestone list, progress bar visible |

#### Lifecycle

- **Start:** Milestones checked on dashboard load. Hero banner shown on first visit.
- **Run:** Milestones re-checked on each dashboard load. Progress updates in real-time.
- **Crash:** Milestone completion flags persist in DB. No data loss.
- **Reboot:** Re-checks milestones from source data on next load.
- **Cleanup:** Milestones persist indefinitely. Hero banner dismissible.
- **Stale detection:** N/A — milestones are boolean, not time-series.

**Constraints register:**

| Constraint | Type | Verification |
|-----------|------|-------------|
| Milestone check completes <3s | Hard | Benchmark with 8 milestones |
| Hero banner dismissable and persists dismissal | Hard | Dismiss, refresh, verify collapsed |
| Side panel opens/closes in <200ms | Hard | Visual test: click → panel visible |
| Milestones detect completion from real data (not just clicks) | Hard | Verify each milestone checks actual completion condition |
| No blocking of dashboard usage | Hard | Verify all dashboard tabs work while Journey tab is active |

**Success metrics:**

| Metric | Target | Measurement |
|--------|--------|------------|
| 3+ milestones in first session | >60% of new users | Track: milestone count on first dashboard load |
| Time to first meaningful action | <3min from install to first agent health view | Track: install timestamp → first agent profile view |
| Milestone completion rate | >80% of started milestones get completed | Track: completed / started per milestone |
| Hero banner dismissal rate | >50% dismiss after 3+ milestones | Track: dismiss events / users with 3+ milestones |

---

### 3.40 Alert Management Surface (🔴 Spec)

**Tagline:** *Every alert, every channel, one place. Acknowledge, resolve, or snooze — then get back to work.*

**What it is:** A unified management layer sitting between anomaly detection (§3.37) and push delivery (§3.17). It answers: "What alerts do I have? What did I do about them? Are they being delivered? What should I configure differently?" Without this surface, alerts are scattered across anomaly cards, push delivery logs, circuit breaker state, and budget threshold notifications. The user has no single place to manage them.

**The problem it solves:** Alert fatigue and alert blindness. Users either ignore alerts because there's no way to manage them, or miss critical alerts because they're buried in a feed with no action surface. The Alert Management Surface turns alerts from "noise" into "workflow" — acknowledge, resolve, snooze, configure, track.

#### RDR: Alert Management Surface

```
Problem: Alerts are scattered across anomaly cards, push logs, circuit state, budget notifications. No unified management.
Solution: Unified alert feed with actions (acknowledge, resolve, snooze), routing config, delivery status, and history.
Key constraint: Must load <2s with 500 alerts. Must not lose state on browser refresh (persisted to DB).
Success metric: >70% of critical alerts acknowledged within 1h of detection.

States explicitly specified:
[x] Happy path (alerts listed with severity, actions, delivery status)
[x] Empty state (no alerts — "All clear. No active alerts.")
[x] Loading state (fetching alerts — skeleton rows)
[x] Error state (alert_log unreachable — "Cannot load alerts. Retrying...")
[x] Partial data (some delivery channels down — "Telegram: offline" badge)
[x] Stale data (last delivery check >5min — "Delivery status may be stale" badge)
[x] Timeout state (feed load >2s — show cached alerts + "Loading newer alerts...")
[x] Degraded state (all channels down — "Push alerts disabled. Dashboard only." banner)

Lifecycle specified:
[x] Start: Load alerts on dashboard open. Auto-refresh every 30s.
[x] Run: New alerts appear at top with animation. Resolved alerts move to History tab.
[x] Crash: Last alert state cached in browser localStorage. Re-renders on reload.
[x] Reboot: Re-fetches from alert_log. No data loss (alerts persist in DB).
[x] Cleanup: Resolved alerts archived after 30d (free: 7d). Open alerts never pruned.
[x] Stale detection: Delivery status timestamp checked. >5min = stale badge.
```

#### Alert types (unified from all sources)

| # | Alert Type | Source | Severity | Has Push? | Has Action? |
|---|-----------|--------|----------|-----------|-------------|
| 1 | Agent dead | pulse_log | 🔴 Critical | ✅ (Pro) | ✅ Heal |
| 2 | Circuit tripped | circuit_breakers | 🔴 Critical | ✅ (Pro) | ✅ Reset + Heal |
| 3 | Crash + checkpoint | session_checkpoints | 🔴 Critical | ✅ (Pro) | ✅ Restore |
| 4 | Drift spike | chisel_drift | 🟠 High | ✅ (Pro) | ✅ Chisel |
| 5 | Error burst | errors | 🟠 High | ✅ (Pro) | ✅ View logs |
| 6 | Context health drop | context_health | 🟠 High | ✅ (Pro) | ✅ Fire Drill |
| 7 | Plugin turning red | plugin_tracking | 🟡 Medium | ✅ (Pro) | ✅ Disable plugin |
| 8 | Token cost spike | token_logs | 🟡 Medium | ✅ (Pro) | ✅ View breakdown |
| 9 | Stale inbox | signal inboxes | 🟡 Medium | ❌ | ✅ Check daemon |
| 10 | Unexplained degradation | context_health + config_events | 🟡 Medium | ✅ (Pro) | ✅ View timeline |
| 11 | Budget threshold | token_budgets | 🟡 Medium | ✅ (Pro) | ✅ Adjust budget |
| 12 | Push delivery failed | alert_log | ℹ️ Info | ❌ | ✅ Retry |

#### Alert data structure

```json
{
  "id": "alert_xyz789",
  "type": "circuit_tripped",
  "severity": "critical",
  "agent_name": "kepler",
  "title": "Circuit breaker tripped — 3 consecutive failures",
  "description": "Kepler failed 3 pulse checks in a row. Circuit breaker engaged at 03:15. Auto-heal attempted restart but agent remained unresponsive.",
  "source": "circuit_breakers",
  "detected_at": "2026-06-06T03:15:00+08:00",
  "discovered_at": "2026-06-06T03:15:03+08:00",
  "discovery_gap_seconds": 3,
  "status": "open",
  "acknowledged_by": null,
  "acknowledged_at": null,
  "resolved_at": null,
  "resolution_action": null,
  "snoozed_until": null,
  "push_delivered": true,
  "push_channel": "telegram",
  "push_delivered_at": "2026-06-06T03:15:03+08:00",
  "push_error": null,
  "recurrence_count": 0,
  "related_anomaly_id": "anom_abc123",
  "recommended_action": "Reset circuit breaker and restart agent. If persistent, check agent logs."
}
```

#### Alert feed layout

```
┌─────────────────────────────────────────────────────────────────┐
│  🔔 Alerts                                        3 open · 12 resolved │
├─────────────────────────────────────────────────────────────────┤
│  [Open]  [Resolved]  [History]  [Config]                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  🔴 kepler · Circuit breaker tripped · 3:15 AM                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ 3 consecutive failures. Auto-heal exhausted.             │   │
│  │ Delivered to Telegram at 03:15:03 (3s gap)               │   │
│  │                                                          │   │
│  │ [🔧 Heal]  [✓ Acknowledge]  [⏰ Snooze 1h]  [→ Resolve] │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                 │
│  🟠 aleph · Error burst · 2:47 AM                               │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ 7 errors in 60 minutes. Likely bridge-down flag spam.     │   │
│  │ Delivered to Telegram at 02:47:12 (12s gap)               │   │
│  │                                                          │   │
│  │ [📋 Logs]  [✓ Acknowledge]  [⏰ Snooze]  [→ Resolve]    │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                 │
│  🟡 pa · Plugin turning red · 1:30 AM                           │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ weather plugin: error rate 12% (was 2%). $0.04/day.       │   │
│  │ Not delivered (Free tier — dashboard only)                │   │
│  │                                                          │   │
│  │ [🔌 Disable]  [✓ Acknowledge]  [⏰ Snooze]  [→ Resolve] │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ── More alerts (show 3 more) ──                                │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### Alert actions

| Action | What It Does | Available To |
|--------|-------------|-------------|
| **Acknowledge** | Marks alert as seen. Dims card (opacity 0.5). Stops discovery-gap counter. | Free + Pro |
| **Resolve** | Marks alert as resolved. Moves to Resolved tab. Records resolution action + timestamp. | Free + Pro |
| **Snooze** | Hides alert for N hours (1h, 4h, 12h, 24h). Re-surfaces after snooze expires. | Free + Pro |
| **Heal** | Triggers agent restart via heal module. Shows progress spinner. Updates alert with heal result. | Free + Pro |
| **View Logs** | Opens agent log tail in side panel. | Free + Pro |
| **Disable Plugin** | Disables the offending plugin via plugin tracking. Shows confirmation. | Free + Pro |
| **Adjust Budget** | Opens budget config for the agent. | Free + Pro |
| **Restore Checkpoint** | Triggers session restore from last checkpoint. | Free + Pro |
| **Retry Delivery** | Re-attempts failed push delivery. Shows delivery status. | Pro |
| **Bulk Acknowledge** | Acknowledge all alerts matching filter (severity, agent, type). | Pro |
| **Bulk Resolve** | Resolve all alerts matching filter. | Pro |

#### Alert routing configuration (Config tab)

| Setting | Free | Pro |
|---------|------|-----|
| View current routing rules | ✅ | ✅ |
| Default: all critical → Telegram | ✅ | ✅ |
| Configure per-type routing | ❌ | ✅ |
| Configure per-agent routing | ❌ | ✅ |
| Multi-channel (Telegram + webhook + email) | ❌ | ✅ |
| Severity threshold per channel | ❌ | ✅ |
| Custom webhook URLs | ❌ | ✅ |
| Mute rules ("don't alert me about X for Y hours") | ❌ | ✅ |

**Default routing rules (Free):**
```
All critical alerts → Telegram (if configured)
All high alerts → Dashboard only
All medium alerts → Dashboard only
All info alerts → Dashboard only (collapsed)
```

**Pro routing rules (configurable):**
```
Agent dead → Telegram + Email (immediate)
Circuit tripped → Telegram (immediate) + Webhook
Drift spike → Telegram (batched hourly)
Error burst → Telegram (batched hourly)
Context health drop → Telegram (daily digest)
Plugin red → Dashboard only
Cost spike → Telegram (daily digest)
Stale inbox → Dashboard only
Budget threshold → Telegram (immediate)
```

#### Delivery status tracking

For every alert, the delivery status is tracked:

| Status | Meaning | Display |
|--------|---------|--------|
| ✅ Delivered | Push sent and acknowledged by channel | "Delivered to Telegram at 03:15:03" |
| ⏳ Pending | Push queued, not yet sent | "Queued for delivery..." |
| ❌ Failed | Push failed (channel down, rate limit, auth error) | "Failed: Telegram rate limit. [Retry]" |
| ⏸️ Snoozed | Alert snoozed, delivery paused | "Snoozed until 07:15" |
| — Not pushed | Free tier or channel not configured | "Dashboard only (Free)" |

#### Discovery gap display

Every alert shows the gap between when the event happened and when the user discovered it:

| Gap | Display |
|-----|--------|
| <10s | "✅ Notified at 03:15:03 (3s after event)" — green |
| 10s-5min | "Notified at 03:15:12 (12s after event)" — default |
| 5min-1h | "Discovered at 07:00 (3h 45m after event)" — amber |
| >1h | "Discovered at 07:00 (4h 45m after event)" — red, prominent |

#### Alert history and trend (Pro)

| Metric | What It Shows |
|--------|-------------|
| Alerts per day (7d chart) | Are there more alerts this week than last? |
| Mean time to acknowledge | How fast are you responding? |
| Mean time to resolve | How fast are you fixing? |
| Top alert types | Which anomalies are most common? |
| Top agents by alert count | Which agent is the troublemaker? |
| Delivery success rate | Are your push channels working? |

#### States & edge cases

| State | What Shows |
|-------|-----------|
| No alerts | "✅ All clear. No active alerts." + green checkmark |
| 1-3 open alerts | Alert cards sorted by severity (critical first) |
| 4+ open alerts | Alert cards + "Show all N" toggle. Header: "2 critical, 3 warnings" |
| All alerts resolved | "✅ All resolved. N alerts handled today." + resolved count |
| Push channel down | "⚠️ Telegram offline — alerts dashboard-only" banner |
| Delivery failed on critical | Red retry button + "Push failed: [error]. [Retry]" |
| Snoozed alert re-surfaces | Card re-appears at top with "⏰ Snooze expired" badge |
| User acknowledges critical | Card dims. "Acknowledged by user at 14:32" timestamp |
| Bulk action in progress | Progress bar: "Resolving 5 alerts... 3/5 done" |

#### Lifecycle

- **Start:** Load alert feed on dashboard open. Join alert_log + anomalies + circuit_breakers.
- **Run:** Auto-refresh every 30s. New alerts appear at top with slide-in animation.
- **Crash:** Last feed state cached in localStorage. Re-renders on reload.
- **Reboot:** Re-fetches from DB. No data loss.
- **Cleanup:** Resolved alerts archived after 30d (free: 7d). Open alerts never pruned.
- **Stale detection:** Delivery status timestamp checked. >5min = stale badge on delivery status.

#### Alert rules engine (Pro)

Configurable rules that determine when alerts fire and where they go:

```yaml
# ~/.observeco/alert-rules.yaml
rules:
  - name: "critical-agent-down"
    match:
      type: ["agent_dead", "circuit_tripped"]
      severity: ["critical"]
    actions:
      - channel: telegram
        immediate: true
      - channel: email
        immediate: true
    cooldown: 30m  # Don't re-alert for same agent within 30min

  - name: "drift-monitoring"
    match:
      type: ["drift_spike", "context_health_drop"]
      severity: ["high"]
    actions:
      - channel: telegram
        batch: hourly  # Batch and send hourly digest
    cooldown: 6h

  - name: "cost-watch"
    match:
      type: ["token_cost_spike", "budget_threshold"]
    actions:
      - channel: telegram
        batch: daily  # Daily digest
    cooldown: 24h

  - name: "mute-noise"
    match:
      type: ["stale_inbox"]
      agent: ["aleph"]  # Aleph's bridge-down spam
    actions:
      - channel: dashboard_only  # Don't push
    cooldown: 48h
```

#### Free vs Pro

| Feature | Free | Pro |
|---------|------|-----|
| Alert feed (all types) | ✅ | ✅ |
| Severity classification | ✅ | ✅ |
| Acknowledge / Resolve / Snooze | ✅ | ✅ |
| Discovery gap display | ✅ | ✅ |
| Delivery status display | ✅ | ✅ |
| Contextual action buttons | ✅ | ✅ |
| Resolved tab (7d history) | ✅ | ✅ 30d |
| Push delivery status tracking | ✅ | ✅ |
| Config view (read-only) | ✅ | ✅ |
| Configure routing rules | ❌ | ✅ |
| Multi-channel routing | ❌ | ✅ |
| Bulk acknowledge/resolve | ❌ | ✅ |
| Alert rules engine (YAML) | ❌ | ✅ |
| Alert history + trend charts | ❌ | ✅ |
| Mute rules | ❌ | ✅ |
| Per-agent routing | ❌ | ✅ |
| Delivery retry | ❌ | ✅ |

**Effort:** ~3 days (1d alert feed + actions + 1d routing config + delivery status + 1d rules engine + history)

**Constraints register:**

| Constraint | Type | Verification |
|-----------|------|-------------|
| Feed load <2s with 500 alerts | Hard | Load test with 500 synthetic alerts |
| Auto-refresh doesn't cause flicker | Hard | Visual test: new alerts slide in, existing don't jump |
| Alert state persists to DB (not just localStorage) | Hard | Refresh browser, verify alerts reload from DB |
| Snooze timer accurate ±30s | Hard | Snooze for 1min, verify re-surface time |
| Bulk action handles 50+ alerts in <5s | Hard | Bulk resolve 50 alerts, benchmark |
| Alert rules YAML parsed safely (no injection) | Hard | Fuzz test with malicious YAML input |
| Discovery gap calculation uses UTC (not local time) | Hard | Test across timezone boundary |

**Success metrics:**

| Metric | Target | Measurement |
|--------|--------|------------|
| Time to acknowledge critical | <1h median | Track: detected_at → acknowledged_at for critical alerts |
| Time to resolve | <4h median | Track: detected_at → resolved_at for all alerts |
| Alert action rate | >70% of alerts get an action (ack/resolve/snooze) | Track: alerts with action / total alerts |
| Delivery success rate | >95% | Track: delivered / total push attempts |
| User comprehension | New user understands alert feed in <15s | User test: "What would you do about this alert?" |
| False positive rate | <10% of resolved alerts marked "not actually a problem" | Track: resolution_action = "false_positive" / total resolved |

---

### 3.41 Post-Turn Webhook (🔴 Spec)

**Tagline:** *Every turn, a receipt. Every receipt, a story.*

**What it is:** A structured JSON event emitted by the OpenClaw plugin (`@observeco/clawforge-plugin`) and Hermes CLI wrapper after every agent turn. ObserveCo's watch daemon receives these events via a local HTTP endpoint (`POST /api/webhooks/turn`) or file sink (`~/.observeco/turn_events/`), stores them in SQLite, and surfaces them in the dashboard.

**Why this exists:** For CrewAI/LangChain users, framework traces provide per-turn execution data. For OpenClaw/Hermes users, that data exists inside the runtime but isn't surfaced to ObserveCo. This webhook closes that gap — it's the single highest-value addition for our ecosystem users.

> ⚠️ **Model flag:** HTTP endpoint and file sink are pattern tasks → use DeepSeek V4 Flash. The correlation logic that joins turn_events with pulse_log (Phase 6 in §12.5) is a reasoning task → use Kimi 2.6. See §13.3.

#### RDR: Post-Turn Webhook

```
Problem: OpenClaw/Hermes users have no per-turn execution data in ObserveCo.
         CrewAI/LangChain users get this from framework traces. Our users get nothing.
Solution: Post-turn webhook — structured JSON emitted after every turn, received
          by Observeco watch daemon, stored in SQLite.
Key constraint: Must not add latency to agent response. Webhook is fire-and-forget.
                Receiver must handle out-of-order events (network delay).
Success metric: >95% of turns captured within 5s of completion.
                Dashboard timeline loads <500ms with 1000 events.

States explicitly specified:
[x] Happy path (event received, stored, displayed in timeline)
[x] Empty state (no events yet — "Start using your agent to see turn data")
[x] Loading state (fetching events — skeleton rows in timeline)
[x] Error state (malformed payload — logged, skipped, agent continues)
[x] Partial data (some fields missing — use defaults, display available)
[x] Stale data (no events >1h while agent is active — "Webhook may be disconnected" badge)
[x] Timeout state (HTTP endpoint unreachable — fall back to file sink)
[x] Degraded state (file sink full — oldest events pruned, warning shown)

Lifecycle specified:
[x] Start: Webhook receiver starts with watch daemon on port (configurable, default 9125).
           File sink directory created if not exists. No events until first turn completes.
[x] Run: Events arrive via HTTP POST or file drop. Stored to turn_events table.
         Dashboard auto-refreshes every 30s.
[x] Crash: Last batch of events persisted (WAL mode). On restart, receiver resumes
           from last successful write. No data loss for in-flight events.
[x] Reboot: File sink events on disk are re-imported on startup. HTTP events lost
            if not yet received (acceptable — single-turn loss, not batch).
[x] Cleanup: Events pruned after 7d (free) / never-pruned (pro). Pruning cron at 3am.
[x] Stale detection: If agent pulse is alive but no turn events for >1h,
                     dashboard shows "Webhook may be disconnected" badge.

Cross-references verified:
[x] §3.16 (OpenClaw plugin) — agrees: plugin emits post-turn hook events
[x] §3.32 (Plugin Firewall) — no overlap: §3.32 is per-plugin, §3.41 is per-turn
[x] §3.33 (Context Fire Drill) — §3.41 provides real utilisation data for §3.33
[x] §12.5 Phase 4 — agrees: webhook receiver is Phase 4 in build plan
```

**What it captures:**

```json
{
  "agent": "kepler",
  "turn_id": "abc123",
  "timestamp": 1717708800,
  "tokens": {"input": 4200, "output": 890},
  "tools_called": ["web_search", "read"],
  "tool_errors": 0,
  "latency_ms": 3400,
  "context_sources_loaded": ["SOUL.md", "MEMORY.md", "skills/github"],
  "context_sources_skipped": ["skills/comfyui", "skills/ascii-art"],
  "model": "anthropic/claude-sonnet-4-20250514"
}
```

**Database schema:**

```sql
CREATE TABLE IF NOT EXISTS turn_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_name TEXT NOT NULL,
    turn_id TEXT UNIQUE,
    timestamp INTEGER NOT NULL,
    tokens_input INTEGER DEFAULT 0,
    tokens_output INTEGER DEFAULT 0,
    tools_called TEXT,  -- JSON array
    tool_errors INTEGER DEFAULT 0,
    latency_ms INTEGER DEFAULT 0,
    context_sources_loaded TEXT,  -- JSON array
    context_sources_skipped TEXT,  -- JSON array
    model TEXT
);
CREATE INDEX IF NOT EXISTS idx_turn_events_agent_ts ON turn_events(agent_name, timestamp);
```

**State matrix:**

| State | Visual | Behaviour | Data condition |
|-------|--------|-----------|---------------|
| Success | Timeline with colour-coded dots | Normal flow, auto-refresh 30s | Events present, fresh (<5min old) |
| Empty | "Start using your agent to see turn data" | Placeholder with install instructions | No events in DB |
| Loading | Skeleton rows in timeline | Spinner while fetching | API call in progress |
| Error | "Event skipped — malformed payload" in log | Logged, skipped, agent continues | Payload failed JSON parse or missing required fields |
| Partial | Timeline with some fields blank | Display available data, grey out missing | Some fields null in payload |
| Stale | "Webhook may be disconnected" badge | Badge appears if agent alive but no events >1h | Agent pulse alive, no events for >1h |
| Timeout | "Webhook receiver unreachable — using file sink" | Fallback to file sink | HTTP POST to receiver failed |
| Degraded | "Event storage full — oldest events pruned" | Prune oldest, keep newest | File sink or DB at capacity |

**Constraints register:**

| Constraint | Type | Verifiable test |
|-----------|------|----------------|
| No added latency to agent response | Hard | Webhook is fire-and-forget (async). Agent response time unaffected by receiver status. |
| Payload max 4KB | Hard | Reject payloads >4KB with 413. Log warning. |
| Out-of-order delivery tolerated | Hard | Events stored by timestamp, not arrival order. turn_id UNIQUE prevents duplicates. |
| Concurrent write safety | Hard | SQLite WAL mode. Concurrent inserts from multiple agents don't block. |
| File sink max 100MB | Hard | Prune oldest when exceeded. Warning shown in dashboard. |
| Receiver port configurable | Soft | Default 9125, configurable via `--webhook-port` flag or config. |
| No external network calls | Hard | Receiver only listens on localhost. No telemetry, no cloud. |

**Success metrics:**

| Metric | Target | Measurement |
|--------|--------|------------|
| Turn capture rate | >95% of turns captured | Compare agent turn count vs turn_events count over 24h |
| Capture latency | <5s from turn completion to DB write | timestamp(turn completion) → timestamp(DB insert) |
| Dashboard load time | <500ms with 1000 events | `/api/agent/{name}/turns` response time |
| Malformed payload rate | <1% of received events | turn_events WHERE tools_called IS NULL / total received |
| File sink fallback activation | <0.1% of uptime | Time in degraded mode / total uptime |

**Tier:**

| Feature | Free | Pro |
|---------|------|-----|
| Post-turn event capture + basic timeline | ✅ | ✅ |
| Anomaly detection on latency/token spikes | ✅ | ✅ |
| Cross-agent cost comparison | ❌ | ✅ |
| Per-conversation cost attribution | ❌ | ✅ |
| Historical trend analysis (30d+) | ❌ | ✅ |

**Estimated effort:** ~3d (1d webhook receiver + 1d storage + 1d dashboard timeline)

**Dependencies:** OpenClaw plugin (§3.16) must be installed to emit events. Hermes wrapper must be updated to emit events. File sink fallback for users without HTTP endpoint.

---

### 3.42 Hermes Evaluation Trace Export (🔴 Superseded by §3.T2)

> ⚠️ **This section is superseded by §3.T2 (Evaluation Layer).** The T2 deep-dive in the Hermes Observability Layer section is the authoritative specification. This section is retained for historical reference only.

**Tagline:** *Not just how many tokens — was this turn any good?*

**What it is:** A structured JSON export of Hermes's internal evaluation signals per turn. Hermes already computes quality signals internally (tool usage efficiency, retry detection, hallucination flags). This feature exports them to ObserveCo's `eval_events` table so the analysis layer can correlate quality with context health, drift, and cost.

#### RDR: Hermes Evaluation Trace Export

```
Problem: ObserveCo can measure token cost but not output quality. Users know
         "how much" but not "was it any good." Hermes computes quality signals
         internally but doesn't export them.
Solution: Export Hermes eval signals (quality_score, tool_efficiency, retried,
          hallucination_flag) to Observeco eval_events table.
Key constraint: Must not slow down Hermes runtime. Export is async, best-effort.
                OpenClaw users don't have this — feature is Hermes-specific.
Success metric: >90% of eval events captured within 10s of turn completion.
                Quality regression detected within 24h of onset (±0.1 score drop).

States explicitly specified:
[x] Happy path (eval event received, stored, quality trend displayed)
[x] Empty state (no eval events — "Hermes eval export not enabled. See docs.")
[x] Loading state (fetching quality trend — skeleton chart)
[x] Error state (malformed eval payload — logged, skipped)
[x] Partial data (some eval fields missing — display available, grey missing)
[x] Stale data (no eval events >24h while agent active — "Eval export may be disconnected")
[x] Timeout state (export pipeline unreachable — log warning, continue)
[x] Degraded state (Hermes runtime too old to export eval — "Upgrade Hermes for quality tracking")

Lifecycle specified:
[x] Start: eval_events table created on first run. No data until first turn with eval.
[x] Run: Eval events arrive async after turn completion. Stored to eval_events table.
         Dashboard quality trend auto-refreshes every 60s.
[x] Crash: In-flight eval events lost (acceptable — single-turn, best-effort).
           On restart, pipeline resumes from next turn.
[x] Reboot: Existing eval_events data persists. No re-import needed.
[x] Cleanup: Eval events pruned after 30d (free) / never-pruned (pro).
[x] Stale detection: If agent pulse is alive but no eval events for >24h,
                     dashboard shows "Eval export may be disconnected" badge.
[x] Version gate: If Hermes version < minimum, export disabled with upgrade prompt.

Cross-references verified:
[x] §3.30 (Context Health Score) — agrees: quality_score feeds into health computation
[x] §3.31 (Relapse Prevention) — agrees: quality regression is a degradation signal
[x] §3.37 (Anomalies Inbox) — agrees: quality drops surface as anomalies
[x] §3.41 (Post-Turn Webhook) — complementary: §3.41 = execution data, §3.42 = quality data
[x] §12.5 Phase 5 — agrees: eval export is Phase 5 in build plan
```

> ⚠️ **Model flag:** Export pipeline and schema are pattern tasks → use DeepSeek V4 Flash. Quality regression detection algorithm (distinguishing normal variance from real regression) is a reasoning task → use Kimi 2.6. See §13.3.

**What it captures:**

```json
{
  "agent": "hound",
  "turn_id": "def456",
  "timestamp": 1717708800,
  "evaluation": {
    "quality_score": 0.87,
    "tool_usage_efficiency": 0.92,
    "retried": false,
    "hallucination_flag": false
  },
  "tokens": {
    "identity": 820,
    "skills": 2100,
    "memory": 1400,
    "tools": 600,
    "guidance": 1280
  }
}
```

**Database schema:**

```sql
CREATE TABLE IF NOT EXISTS eval_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_name TEXT NOT NULL,
    turn_id TEXT UNIQUE,
    timestamp INTEGER NOT NULL,
    quality_score REAL,
    tool_usage_efficiency REAL,
    retried INTEGER DEFAULT 0,
    hallucination_flag INTEGER DEFAULT 0,
    tokens_identity INTEGER DEFAULT 0,
    tokens_skills INTEGER DEFAULT 0,
    tokens_memory INTEGER DEFAULT 0,
    tokens_tools INTEGER DEFAULT 0,
    tokens_guidance INTEGER DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_eval_events_agent_ts ON eval_events(agent_name, timestamp);
```

**State matrix:**

| State | Visual | Behaviour | Data condition |
|-------|--------|-----------|---------------|
| Success | Quality trend line chart (7d) with score + efficiency | Normal flow, auto-refresh 60s | Eval events present, fresh (<24h old) |
| Empty | "Hermes eval export not enabled. See docs." | Placeholder with setup instructions | No eval events in DB |
| Loading | Skeleton chart lines | Spinner while fetching | API call in progress |
| Error | "Eval event skipped — malformed payload" in log | Logged, skipped, agent continues | Payload failed validation |
| Partial | Chart with some metrics greyed out | Display available metrics | Some eval fields null |
| Stale | "Eval export may be disconnected" badge | Badge appears if agent alive but no eval >24h | Agent pulse alive, no eval events for >24h |
| Timeout | "Eval export pipeline unreachable" | Log warning, continue without eval | Export pipeline HTTP call failed |
| Degraded | "Upgrade Hermes for quality tracking" | Disable eval export, show upgrade prompt | Hermes version < minimum required |

**Constraints register:**

| Constraint | Type | Verifiable test |
|-----------|------|----------------|
| No added latency to Hermes runtime | Hard | Export is async (separate thread/process). Agent response time unaffected. |
| Eval payload max 2KB | Hard | Reject payloads >2KB with 413. Log warning. |
| Quality score 0.0–1.0 range | Hard | Reject scores outside [0.0, 1.0]. Log warning, skip event. |
| OpenClaw users see clear "not available" state | Hard | When no Hermes runtime detected, show "Hermes eval not available" — never show empty chart. |
| Hermes version minimum | Soft | Export requires Hermes ≥v0.9.0. Below this, disable with upgrade prompt. |
| No external network calls | Hard | Export pipeline only writes to local SQLite. No telemetry, no cloud. |

**Success metrics:**

| Metric | Target | Measurement |
|--------|--------|------------|
| Eval capture rate | >90% of turns with eval data | Compare agent turn count (from §3.41) vs eval_events count |
| Capture latency | <10s from turn completion to DB write | timestamp(turn completion) → timestamp(DB insert) |
| Quality regression detection | Within 24h of onset | Time from ±0.1 score drop to anomaly surfaced |
| False quality alert rate | <5% of quality alerts are false positives | Quality alerts resolved as "not actually degraded" / total quality alerts |
| Dashboard load time | <500ms with 30d of eval events | `/api/agent/{name}/quality` response time |

**Tier:**

| Feature | Free | Pro |
|---------|------|-----|
| Eval event ingestion + quality trend per agent | ✅ | ✅ |
| Quality regression detection | ❌ | ✅ |
| Quality × drift correlation | ❌ | ✅ |
| Fleet quality comparison | ❌ | ✅ |

**Estimated effort:** ~2d (1d export pipeline + 1d dashboard quality trend)

**Dependencies:** Hermes runtime must expose evaluation internals. OpenClaw does not have equivalent eval signals — this is Hermes-specific.

---

### 3.43 Tool Efficiency Ranking (🔴 Spec)

**Tagline:** *Your tools have a report card. Most of them are failing.*

**What it is:** Derived intelligence from post-turn webhook data (§3.41). Ranks every tool and skill by cost-effectiveness: cost per call, error rate, latency impact, success rate. Surfaces red/yellow/green status and "disable this tool" recommendations.

#### RDR: Tool Efficiency Ranking

```
Problem: Users don't know which tools are worth their token cost. Some tools
         are expensive and unreliable. Others are cheap and never fail. No
         visibility into per-tool cost-effectiveness.
Solution: Aggregate turn_events by tools_called. Rank by cost/error/latency.
          Red/yellow/green. Surface "disable this tool" recommendations.
Key constraint: Must aggregate from §3.41 turn_events (no independent data source).
                Aggregation must complete <2s for 50 tools × 7 days of data.
Success metric: Cost estimation accuracy ±15% of actual provider billing.
                User disables a red tool within 7 days of seeing recommendation.

States explicitly specified:
[x] Happy path (tool ranking table displayed with cost/error/status)
[x] Empty state (no tools called yet — "Use your agent to generate tool data")
[x] Loading state (computing rankings — spinner on table)
[x] Error state (turn_events unreadable — "Run observeco doctor")
[x] Partial data (tool called <5 times — "Insufficient data for ranking")
[x] Stale data (no turn events >7d — "Data may be stale" badge)
[x] Timeout state (aggregation >2s — show cached rankings)
[x] Degraded state (cost data unavailable — show tool usage without cost column)

Lifecycle specified:
[x] Start: Rankings computed on first dashboard load after events exist.
           No data → empty state with instructions.
[x] Run: Rankings recompute every 5min or on dashboard refresh.
         Cached in memory, invalidated on new event arrival.
[x] Crash: Cached rankings lost. Recompute on next dashboard load (acceptable — <2s).
[x] Reboot: Cache empty. Recompute from turn_events on first access.
[x] Cleanup: Rankings are derived (not stored). Always computed from live turn_events.
[x] Stale detection: If turn_events last event >7d old, show stale badge.

Cross-references verified:
[x] §3.32 (Plugin Firewall) — complementary, not contradictory:
     §3.32 = per-plugin (OpenClaw plugins like clawforge-plugin)
     §3.43 = per-tool-call (actual tools called during execution)
     Different granularity, different data source (plugin-stats.db vs turn_events)
[x] §3.41 (Post-Turn Webhook) — depends on: §3.43 reads from turn_events
[x] §3.44 (Context Source Utilisation) — complementary: §3.43 = tool cost,
     §3.44 = source utilisation. Both derived from §3.41.
[x] §3.33 (Context Fire Drill) — §3.43 provides tool cost data for fire drill projections
```

> ⚠️ **Model flag:** Aggregation queries and cost math are pattern tasks → use DeepSeek V4 Flash. Multi-provider cost attribution (handling DeepSeek/OpenAI/Ollama/cached tokens edge cases) is a reasoning task → use Kimi 2.6. See §13.3.

**How it works:**

1. Aggregates `turn_events` by `tools_called`
2. For each tool: avg tokens consumed, avg latency, error rate, call count
3. Computes cost using configured provider rates
4. Assigns status: GREEN (efficient + reliable), YELLOW (one metric concerning), RED (multiple failures)
5. Generates recommendations: "Browser-automation costs $0.031/call and fails 12% — disable it?"

**What the user sees:**

```
TOOL EFFICIENCY: Hound — last 7 days

  Tool                Cost/Call   Error Rate   Status   Recommendation
  ─────────────────────────────────────────────────────────────────────
  web_search          $0.008      0%           🟢       —
  read (file)         $0.001      0%           🟢       —
  exec (shell)        $0.004      3%           🟡       Monitor
  browser-automation  $0.031      12%          🔴       Disable or investigate

  Total tool cost: $0.18/day
  Potential savings: $0.06/day (disable browser-automation)
```

**State matrix:**

| State | Visual | Behaviour | Data condition |
|-------|--------|-----------|---------------|
| Success | Ranked table with cost/error/status columns | Normal flow, recompute every 5min | turn_events present, ≥5 calls per tool |
| Empty | "Use your agent to generate tool data" | Placeholder with instructions | No turn_events with tools_called |
| Loading | Skeleton table rows | Spinner while aggregating | Aggregation in progress |
| Error | "Cannot compute rankings — run observeco doctor" | Error message | turn_events table unreadable |
| Partial | Table with "Insufficient data" badge on low-call tools | Show available, badge insufficient | Tool called <5 times |
| Stale | "Data may be stale" badge | Badge if last event >7d | No turn_events for >7d |
| Timeout | Show cached rankings + "Recomputing..." | Use cache, recompute async | Aggregation >2s |
| Degraded | Table without cost column | Show usage/error only | Provider cost rates unavailable |

**Constraints register:**

| Constraint | Type | Verifiable test |
|-----------|------|----------------|
| Aggregation <2s for 50 tools × 7d | Hard | Benchmark: 50 tools × 10K events aggregates in <2s |
| Cost accuracy ±15% | Hard | Compare tool cost estimates vs provider billing over 7d |
| No independent data source | Hard | §3.43 ONLY reads from turn_events (§3.41). No separate instrumentation. |
| Minimum 5 calls for ranking | Hard | Tools with <5 calls show "Insufficient data" badge, no ranking |
| Cached in memory, not DB | Soft | Rankings are derived, not stored. Recomputed on access. |
| Cross-platform cost rates | Soft | Provider cost rates configurable per user (DeepSeek, OpenAI, Ollama, etc.) |

**Success metrics:**

| Metric | Target | Measurement |
|--------|--------|------------|
| Cost estimation accuracy | ±15% of actual billing | Compare estimated tool cost vs provider dashboard over 7d |
| Recommendation action rate | >30% of red tools disabled within 7d | Tools flagged red → disabled in config within 7d |
| Aggregation performance | <2s for 50 tools × 10K events | Benchmark aggregation query |
| Dashboard load time | <500ms with 50 tools × 7d | `/api/agent/{name}/tools` response time |
| False red flag rate | <10% of red flags reversed by user | Red tools re-enabled within 48h / total red flags |

**Feeds into:** Plugin Firewall (§3.32) — this provides per-tool-call granularity while §3.32 provides per-plugin granularity. Both views complement each other.

**Tier:**

| Feature | Free | Pro |
|---------|------|-----|
| Per-agent tool cost table + top-3 recommendations | ✅ | ✅ |
| Cross-fleet tool comparison | ❌ | ✅ |
| Auto-disable suggestions | ❌ | ✅ |
| Budget threshold alerts per tool | ❌ | ✅ |

**Estimated effort:** ~1.5d (aggregation query + dashboard widget)

**Dependencies:** Requires §3.41 (Post-Turn Webhook) to be emitting data.

---

### 3.44 Context Source Utilisation Tracker (🔴 Spec)

**Tagline:** *You're loading 40K tokens. You're using 12K. Here's what to drop.*

**What it is:** Derived intelligence from post-turn webhook data (§3.41). Tracks which context sources (skills, memory sections, workspace files) are actually used per turn vs loaded by default. Surfaces lazy-load recommendations and demotion suggestions.

#### RDR: Context Source Utilisation Tracker

```
Problem: Users load 40K+ tokens of context per turn but only use a fraction.
         No visibility into which sources are actually used vs loaded by default.
         Wasted tokens = wasted money.
Solution: Aggregate turn_events by context_sources_loaded vs context_sources_skipped.
          Track load frequency per source. Flag low-utilisation, high-cost sources.
Key constraint: Must aggregate from §3.41 turn_events (no independent data source).
                Must distinguish "loaded but not needed" from "loaded and used."
Success metric: Token savings recommendation accuracy ±20% of actual reduction
                when user follows recommendation.
                Fire Drill accuracy improves ≥15% when fed real utilisation data.

States explicitly specified:
[x] Happy path (utilisation table displayed with load freq/cost/status)
[x] Empty state (no context data yet — "Use your agent to generate utilisation data")
[x] Loading state (computing utilisation — spinner on table)
[x] Error state (turn_events unreadable — "Run observeco doctor")
[x] Partial data (source tracked <10 turns — "Insufficient data for utilisation")
[x] Stale data (no turn events >7d — "Data may be stale" badge)
[x] Timeout state (aggregation >2s — show cached utilisation)
[x] Degraded state (token cost data unavailable — show load frequency without cost)

Lifecycle specified:
[x] Start: Utilisation computed on first dashboard load after events exist.
           No data → empty state with instructions.
[x] Run: Utilisation recompute every 5min or on dashboard refresh.
         Cached in memory, invalidated on new event arrival.
[x] Crash: Cached utilisation lost. Recompute on next dashboard load (acceptable — <2s).
[x] Reboot: Cache empty. Recompute from turn_events on first access.
[x] Cleanup: Utilisation is derived (not stored). Always computed from live turn_events.
[x] Stale detection: If turn_events last event >7d old, show stale badge.

Cross-references verified:
[x] §3.33 (Context Fire Drill) — §3.44 provides real utilisation data for §3.33.
     Before §3.44: Fire Drill uses static token estimates.
     After §3.44: Fire Drill uses actual load frequency × token cost.
     Fire Drill accuracy improves ≥15% with real data.
[x] §3.41 (Post-Turn Webhook) — depends on: §3.44 reads from turn_events
[x] §3.43 (Tool Efficiency Ranking) — complementary: §3.43 = tool cost,
     §3.44 = source utilisation. Both derived from §3.41.
[x] §3.16 (OpenClaw plugin) — §3.16 controls what gets loaded, §3.44 measures what gets used.
     Feedback loop: §3.44 recommendations → §3.16 lazy-load config changes.
```

> ⚠️ **Model flag:** Aggregation queries and utilisation math are pattern tasks → use DeepSeek V4 Flash. Fire Drill integration (merging utilisation data with survival simulation, fallback logic) is a reasoning task → use Kimi 2.6. See §13.3.

**How it works:**

1. Aggregates `turn_events` by `context_sources_loaded` and `context_sources_skipped`
2. For each source: load frequency (% of turns), avg tokens consumed, last used timestamp
3. Computes utilisation score: loaded ÷ total turns
4. Flags sources with low utilisation (<20% of turns) and high token cost (>500 tokens)
5. Generates recommendations: "Skills/comfyui adds 1,400 tokens but is loaded in 8% of turns — remove from defaults?"

**What the user sees:**

```
CONTEXT UTILISATION: Hound — last 7 days

  Source              Load Freq   Tokens   Status   Recommendation
  ─────────────────────────────────────────────────────────────────────
  SOUL.md             100%        3,200    🟢       Always needed
  skills/github       94%         820      🟢       Frequently used
  skills/web-search   87%         440      🟢       Frequently used
  MEMORY.md           100%        1,400    🟢       Always needed
  skills/comfyui      8%          1,400    🔴       Remove from defaults
  skills/ascii-art    12%         680      🟡       Consider lazy-loading

  Total loaded: 42,100 tokens/turn
  Actually used: 14,200 tokens/turn
  Potential savings: 2,080 tokens/turn (remove 2 low-utilisation skills)
```

**State matrix:**

| State | Visual | Behaviour | Data condition |
|-------|--------|-----------|---------------|
| Success | Ranked table with load freq/cost/status columns | Normal flow, recompute every 5min | turn_events present, ≥10 turns tracked |
| Empty | "Use your agent to generate utilisation data" | Placeholder with instructions | No turn_events with context data |
| Loading | Skeleton table rows | Spinner while aggregating | Aggregation in progress |
| Error | "Cannot compute utilisation — run observeco doctor" | Error message | turn_events table unreadable |
| Partial | Table with "Insufficient data" badge on low-turn sources | Show available, badge insufficient | Source tracked <10 turns |
| Stale | "Data may be stale" badge | Badge if last event >7d | No turn_events for >7d |
| Timeout | Show cached utilisation + "Recomputing..." | Use cache, recompute async | Aggregation >2s |
| Degraded | Table without cost column | Show load frequency only | Token cost data unavailable |

**Constraints register:**

| Constraint | Type | Verifiable test |
|-----------|------|----------------|
| Aggregation <2s for 30 sources × 7d | Hard | Benchmark: 30 sources × 10K events aggregates in <2s |
| Utilisation accuracy ±20% | Hard | Compare recommended savings vs actual reduction when user follows recommendation |
| No independent data source | Hard | §3.44 ONLY reads from turn_events (§3.41). No separate instrumentation. |
| Minimum 10 turns for utilisation | Hard | Sources tracked <10 turns show "Insufficient data" badge |
| Cached in memory, not DB | Soft | Utilisation is derived, not stored. Recomputed on access. |
| Fire Drill integration | Soft | §3.44 feeds real utilisation into §3.33 when both are available |

**Success metrics:**

| Metric | Target | Measurement |
|--------|--------|------------|
| Savings recommendation accuracy | ±20% of actual reduction | Compare estimated savings vs actual token reduction after user follows recommendation |
| Fire Drill accuracy improvement | ≥15% with real utilisation data | Compare Fire Drill prediction accuracy before/after §3.44 data |
| Recommendation action rate | >25% of red sources demoted within 14d | Sources flagged red → removed from defaults within 14d |
| Aggregation performance | <2s for 30 sources × 10K events | Benchmark aggregation query |
| Dashboard load time | <500ms with 30 sources × 7d | `/api/agent/{name}/utilisation` response time |
| False red flag rate | <10% of red flags reversed by user | Red sources re-added within 48h / total red flags |

**Feeds into:** Context Fire Drill (§3.33) — replaces static token estimates with real utilisation data. Fire Drill can now project: "If you remove these 2 skills, you gain 8 extra turns before degradation."

**Tier:**

| Feature | Free | Pro |
|---------|------|-----|
| Per-agent utilisation table + lazy-load recommendations | ✅ | ✅ |
| Cross-fleet utilisation comparison | ❌ | ✅ |
| Auto-suggest default demotion | ❌ | ✅ |
| Utilisation trend analysis (are you using more or less over time?) | ❌ | ✅ |

**Estimated effort:** ~1.5d (aggregation query + dashboard widget)

**Dependencies:** Requires §3.41 (Post-Turn Webhook) to be emitting data.

---

### 3.45 Structured Diagnostic Context for LLM Troubleshooting (🔴 Spec)

**Tagline:** *ObserveCo measures. The LLM reasons. Together, they fix.*

**What it is:** A user-triggered feature that assembles a structured diagnostic payload from ObserveCo's data layers and sends it to the user's configured LLM for troubleshooting. ObserveCo does not try to be the knowledge authority — it is the **structured data layer** that makes any LLM good at diagnosing agent problems.

**Why this exists:** Users see red on a dashboard and don't know what to do. ObserveCo has all the diagnostic data (pulse, tokens, drift, errors, utilisation, circuit breaker state) but today just displays it as raw numbers. The missing piece is **interpretation** — turning "SOUL.md drift +18%, context utilisation 82%" into "run `chisel compress --mode lite` to fix context pressure." The LLM provides the interpretation. ObserveCo provides the structured data.

#### RDR: Structured Diagnostic Context

```
Problem: Users see red/yellow on agent cards but don't know what to do.
         ObserveCo has diagnostic data but no interpretation layer.
         Users resort to asking ChatGPT with vague descriptions.
Solution: User clicks "Troubleshoot" button. ObserveCo assembles a structured
          diagnostic payload from its data layers. Sends to user's configured LLM.
          LLM diagnoses and recommends fix with specific commands.
Key constraint: ObserveCo is the DATA layer, not the KNOWLEDGE layer.
                The LLM reasons from structured context, not from curated patterns.
                Diagnostic payload must be complete enough for the LLM to diagnose
                without any ObserveCo-specific pattern database.
Success metric: >70% of users report the diagnosis was actionable (user survey).
                Fix recommendation accuracy >60% (fix resolves the issue).
                Payload assembly <1s. LLM response displayed in <15s.

States explicitly specified:
[x] Happy path (payload assembled, LLM responds, diagnosis displayed)
[x] Empty state (no diagnostic data yet — "Run your agent for a few minutes first")
[x] Loading state (assembling payload + waiting for LLM — spinner + progress)
[x] Error state (LLM unreachable — "Check your provider config" + retry)
[x] Partial data (some signals missing — include available, note gaps)
[x] Stale data (data >1h old — "Data may be stale" warning before sending)
[x] Timeout state (LLM response >30s — show partial response + "Still thinking...")
[x] Degraded state (LLM provider rate-limited — show raw payload + "Copy to clipboard" for manual paste to ChatGPT/Claude)

Lifecycle specified:
[x] Start: No payload until user clicks Troubleshoot button.
           Button appears on agent card + Anomalies Inbox action.
[x] Run: On click → assemble payload (200ms) → send to LLM → stream response.
         Response displayed in real-time as LLM generates it.
[x] Crash: If LLM stream interrupted, show partial response + "Connection lost" + [🔄 Retry] button.
[x] Reboot: Previous troubleshooting sessions logged in troubleshoot_log table.
            User can review past diagnoses.
[x] Cleanup: Troubleshoot sessions retained 30d (free) / never-pruned (pro).
[x] Stale detection: If payload data >1h old, show warning before sending.

Cross-references verified:
[x] §3.25 (LLM-Powered Intelligence) — complementary: §3.25 = automated diagnosis,
     §3.45 = user-triggered diagnosis. Same LLM service, different trigger.
[x] §3.30 (Context Health Score) — feeds into payload as primary health signal
[x] §3.31 (Relapse Prevention) — feeds into payload as change history
[x] §3.37 (Anomalies Inbox) — §3.45 is the "action" when user clicks troubleshoot
     on an anomaly card
[x] §3.41 (Post-Turn Webhook) — feeds turn-level execution data into payload
[x] §3.42 (Eval Trace) — feeds quality signals into payload
[x] §3.43 (Tool Efficiency) — feeds tool cost/error data into payload
[x] §3.44 (Context Utilisation) — feeds utilisation data into payload
```

#### The Diagnostic Payload

The core of this feature. A structured JSON object that contains everything the LLM needs to diagnose the agent's problem. No curated patterns needed — the data speaks for itself.

```json
{
  "agent": {
    "name": "kepler",
    "type": "agent",
    "framework": "openclaw",
    "model": "anthropic/claude-sonnet-4-20250514"
  },
  "health": {
    "status": "alive",
    "uptime": "47h 23m",
    "last_pulse": "2s ago",
    "circuit_breaker": "ok",
    "error_count_24h": 4,
    "error_types": ["timeout", "connection_refused"]
  },
  "context_health": {
    "score": 54,
    "trend": "declining",
    "trend_delta": -18,
    "trend_period": "7d",
    "breakdown": {
      "memory_bloat": 0.23,
      "drift_delta": 0.18,
      "context_utilisation": 0.82,
      "error_rate": 0.032,
      "sources_skipped_ratio": 0.15
    }
  },
  "tokens": {
    "per_turn_avg": 5200,
    "per_turn_baseline": 3800,
    "delta": "+37%",
    "breakdown": {
      "identity": 820,
      "skills": 2100,
      "memory": 1400,
      "tools": 600,
      "guidance": 1280
    },
    "cost_per_turn": 0.007,
    "cost_provider": "deepseek-v4-flash"
  },
  "drift": {
    "sool_md_change_pct": 18,
    "period": "7d",
    "edits": [
      {"date": "2026-06-05", "delta": "+2400 tokens", "section": "guidance"},
      {"date": "2026-06-03", "delta": "+800 tokens", "section": "skills"}
    ]
  },
  "tools": [
    {"name": "web_search", "calls": 23, "cost_per_call": 0.008, "error_rate": 0.0, "status": "green"},
    {"name": "read", "calls": 47, "cost_per_call": 0.001, "error_rate": 0.0, "status": "green"},
    {"name": "browser-automation", "calls": 14, "cost_per_call": 0.031, "error_rate": 0.12, "status": "red"}
  ],
  "context_sources": {
    "total_loaded": 42100,
    "actually_used": 14200,
    "wasted": 27900,
    "low_utilisation": [
      {"source": "skills/comfyui", "load_freq": 0.08, "tokens": 1400},
      {"source": "skills/ascii-art", "load_freq": 0.12, "tokens": 680}
    ]
  },
  "recent_events": [
    {"time": "2026-06-05 14:00", "event": "SOUL.md edited (+2400 tokens)"},
    {"time": "2026-06-04 11:00", "event": "Plugin browser-automation installed"},
    {"time": "2026-06-03 09:00", "event": "Context health 78→72"}
  ],
  "troubleshooting_history": [
    {"date": "2026-05-28", "symptoms": "high token usage", "fix": "chisel compress --mode lite", "resolved": true}
  ]
}
```

#### System Prompt for LLM

```
You are an AI agent operations specialist. You have access to the full diagnostic
data for an AI agent running on ObserveCo, a local-first agent monitoring platform.

Your job:
1. Identify the root cause(s) of the agent's problems
2. Recommend specific, actionable fixes with exact commands
3. Estimate the cost impact of the fix
4. Suggest prevention measures

Rules:
- Only recommend fixes that are safe and reversible
- Always include the exact CLI command or config change
- If multiple issues exist, prioritise by impact (cost savings first, then reliability)
- If data is missing for a signal, note it and don't guess
- Rate your confidence: high / medium / low
- If you're unsure, say so — don't fabricate a diagnosis

Diagnostic data:
{diagnostic_payload}
```

#### Response Format

The LLM should return structured output:

```json
{
  "diagnosis": "Context pressure caused by SOUL.md bloat and low-utilisation skills",
  "confidence": "high",
  "root_causes": [
    {
      "issue": "SOUL.md drift +18% over 7 days",
      "impact": "Context utilisation at 82%, causing LLM retries",
      "evidence": "Token usage up 37% (3800→5200/turn), correlating with edits on Jun 3-5"
    },
    {
      "issue": "browser-automation plugin failing 12% of calls",
      "impact": "$0.042/day wasted on failed calls",
      "evidence": "14 calls, 2 failures, highest cost-per-call of any tool"
    },
    {
      "issue": "2 skills loaded but rarely used (comfyui 8%, ascii-art 12%)",
      "impact": "2,080 tokens/turn wasted on unused context",
      "evidence": "Load frequency from turn_events data"
    }
  ],
  "recommended_fixes": [
    {
      "priority": 1,
      "action": "Compress SOUL.md",
      "command": "observeco chisel compress --agent kepler --mode lite",
      "expected_savings": "-1,400 tokens/turn",
      "cost_impact": "-$0.003/turn (-$0.30/day)"
    },
    {
      "priority": 2,
      "action": "Disable browser-automation plugin",
      "command": "observeco config set plugins.browser-automation.enabled false",
      "expected_savings": "-12% error rate, -$0.042/day",
      "cost_impact": "-$0.042/day"
    },
    {
      "priority": 3,
      "action": "Remove low-utilisation skills from defaults",
      "command": "observeco config set skills.defaults '[\"github\", \"web-search\"]'",
      "expected_savings": "-2,080 tokens/turn",
      "cost_impact": "-$0.003/turn"
    }
  ],
  "prevention": [
    "Set up drift alerts (§3.31) to catch SOUL.md bloat early",
    "Review tool efficiency weekly (§3.43) to catch failing plugins",
    "Run Context Fire Drill (§3.33) before adding new skills"
  ]
}
```

#### Response Validation

The LLM may not always return valid JSON. ObserveCo must handle this gracefully:

**Validation pipeline:**

```
validate_llm_response(raw_response):
  1. Try JSON.parse(raw_response)
     → Success: validate required fields (diagnosis, confidence, root_causes, recommended_fixes)
     → Missing fields: fill defaults (confidence = "low", root_causes = [], recommended_fixes = [])
     → Proceed to command validation
  2. JSON.parse fails: try extracting JSON from markdown code block (```json...```)
     → Success: proceed to step 1
     → Fails: treat as raw text
  3. Raw text fallback:
     → Display as plain text diagnosis (no structured rendering)
     → Show "⚠️ LLM did not return structured response" badge
     → Still show [📋 Copy] and [💾 Save Session] buttons
     → Log as `response_format: "raw_text"` in troubleshoot_log
```

**Command validation:**

```
validate_fix_commands(fixes):
  for each fix in fixes:
    1. Check command against SAFE_COMMANDS allowlist (see below)
    2. If command NOT in allowlist:
       → Strip the fix from recommended_fixes
       → Add to "warnings" array: "Command not verified: {command}"
       → Show warning in UI: "⚠️ This command was not auto-verified. Copy it to run manually."
    3. If command IS in allowlist:
       → Verify agent_name in command matches target agent
       → Show [▶ Execute] button (enabled)
```

**Response format compliance:**

| LLM Response | Handling |
|-------------|----------|
| Valid JSON with all fields | Render structured diagnosis |
| Valid JSON with missing fields | Fill defaults, render with "Partial response" badge |
| JSON inside markdown code block | Extract, parse, render |
| Plain text / markdown | Render as raw text with "⚠️ Unstructured response" badge |
| Empty response | Show "LLM returned empty response. Try again." |
| Timeout (>30s) | Show partial response + "Still thinking..." + [⏹ Stop] button |
| Truncated JSON | Show raw text with "⚠️ Response interrupted" badge |

#### Command Safety Allowlist

Only commands that are safe (no data loss) and reversible can be executed via the [▶ Execute] button. All other commands are displayed but require manual copy-paste.

**Allowlist:**

| Command Pattern | Safe | Reversible | Notes |
|----------------|------|------------|-------|
| `observeco chisel compress --agent <name> --mode lite` | ✅ | ✅ | Creates backup before overwriting |
| `observeco chisel compress --agent <name> --mode full` | ✅ | ✅ | Creates backup before overwriting |
| `observeco config set <key> <value>` | ✅ | ✅ | Reversible by setting back to previous value |
| `observeco agent remove <name>` | ⚠️ | ⚠️ | Shows confirmation dialog first |
| `observeco clawforge garden --agent <name>` | ✅ | ✅ | Read-only analysis, no changes |
| `observeco pulse check` | ✅ | ✅ | Read-only, no changes |
| `observeco heal <name>` | ⚠️ | ⚠️ | Restarts agent — shows confirmation |
| `observeco doctor` | ✅ | ✅ | Read-only diagnostics |
| Any `rm`, `delete`, `drop` command | ❌ | ❌ | Never allow via Execute — display only |
| Any command not in allowlist | ❌ | ❌ | Display with warning, require manual execution |

**Allowlist maintenance:** The allowlist is shipped with ObserveCo and updated on version upgrades. Users cannot modify the allowlist (security constraint).

#### Privacy Boundary

The diagnostic payload is designed to be sent to an external LLM provider. The following data rules ensure user privacy:

**IN the payload (safe to send):**

| Data | Why It's Safe |
|------|--------------|
| Agent name | User's own agent, not PII |
| Health status (alive/dead/error) | Operational metric, not personal |
| Context health score | Derived number, no content |
| Token counts per component | Aggregate metrics, no content |
| Drift percentage | Derived number, no content |
| Tool names and error rates | Operational metrics |
| Context source names and load frequency | Operational metrics |
| Error types (timeout, HTTP 500) | Operational metrics |
| Config event types (plugin installed, SOUL.md edited) | Operational metadata |
| Troubleshooting history (fixes applied, resolved) | User's own actions |

**NOT in the payload (never sent):**

| Data | Why It's Excluded |
|------|------------------|
| SOUL.md content | Agent personality/instructions — sensitive |
| MEMORY.md content | User's personal context — sensitive |
| Any file content (skills, configs) | User's intellectual property |
| Agent responses / conversation history | User's conversations — sensitive |
| API keys, tokens, credentials | Security — never transmit |
| User identity, email, IP | PII — never transmit |
| Full error messages (may contain paths/content) | May leak sensitive info — truncate to error type only |

**Payload sanitisation:** Before assembly, the payload is sanitised:
- Error messages truncated to type only ("timeout" not "timeout reading /Users/sean/.hermes/profiles/hound/SOUL.md")
- Config event descriptions contain type only, not full diff
- Troubleshooting history contains fix command, not the diagnostic payload from that session

#### Concurrency Control

| Scenario | Behaviour |
|---------|----------|
| User clicks Troubleshoot on agent A, then agent B | Second click blocked — "Diagnosis in progress for kepler. Wait or cancel first." |
| User clicks Troubleshoot on same agent while streaming | Blocked — "Diagnosis already in progress for this agent." |
| User clicks Re-diagnose while streaming | Cancels current stream, starts new session with fresh payload |
| Multiple users on same dashboard | Each user gets independent session (session-scoped, not global lock) |
| LLM stream中断 mid-response | Show partial response + "Connection lost" + [🔄 Retry] button. Retry sends fresh payload. |

#### Cross-Platform Considerations

| Platform | CLI Command | Behaviour |
|----------|------------|----------|
| macOS / Linux | `observeco chisel compress ...` | Standard POSIX |
| Windows | `observeco chisel compress ...` | Same — ObserveCo is Python, CLI is cross-platform |
| Windows (WSL) | `observeco chisel compress ...` | Same as POSIX |
| Headless (no dashboard) | `observeco troubleshoot <agent>` | CLI-only mode — same payload, terminal output |

**No platform-specific logic needed.** ObserveCo CLI is Python-based and cross-platform. Fix commands work identically on all platforms. The dashboard is browser-based and platform-independent.

#### First-Run / Empty State

| Scenario | What the User Sees |
|---------|--------------------|
| Fresh install, no agents discovered | Troubleshoot button hidden (no agent to troubleshoot) |
| Agent discovered, no pulse data yet | Troubleshoot button visible but greyed out — "Collecting data... (wait 30s)" |
| Agent discovered, first pulse received | Troubleshoot button enabled. Click shows: "Diagnostic data available for first time. Run your agent for a few minutes to get richer diagnostics." |
| Agent with full data | Normal troubleshooting flow |
| Agent with partial data (some signals missing) | Payload assembled with available data. LLM response includes: "Note: Some diagnostic signals were unavailable. Diagnosis is based on partial data." |

#### What the User Sees

```
┌─────────────────────────────────────────────────────────────┐
│  🔧 Troubleshooting kepler...                               │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  📊 Assembling diagnostic data... ✓                         │
│  🤖 Sending to Claude Sonnet... ✓                           │
│  💬 Generating diagnosis...                                 │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  DIAGNOSIS: Context pressure + failing plugin       │   │  
│  │  Confidence: ●●●○○ Medium-High                      │   │  
│  │                                                      │   │  
│  │  Root causes:                                        │   │  
│  │  1. SOUL.md drift +18% → context at 82%             │   │  
│  │  2. browser-automation failing 12% → $0.042/day     │   │  
│  │  3. 2 unused skills → 2,080 tokens wasted           │   │  
│  │                                                      │   │  
│  │  Recommended fixes:                                  │   │  
│  │  ┌──────────────────────────────────────────────┐   │   │  
│  │  │ 1. Compress SOUL.md                         │   │   │  
│  │  │    observeco chisel compress --agent kepler  │   │   │  
│  │  │    Saves: $0.30/day                          │   │   │  
│  │  │    [📋 Copy]  [▶ Execute]                     │   │   │  
│  │  ├──────────────────────────────────────────────┤   │   │  
│  │  │ 2. Disable browser-automation                │   │   │  
│  │  │    observeco config set plugins...false       │   │   │  
│  │  │    Saves: $0.042/day                         │   │   │  
│  │  │    [📋 Copy]  [▶ Execute]                     │   │   │  
│  │  ├──────────────────────────────────────────────┤   │   │  
│  │  │ 3. Remove unused skills                      │   │   │  
│  │  │    observeco config set skills.defaults...    │   │   │  
│  │  │    Saves: $0.003/day                         │   │   │  
│  │  │    [📋 Copy]  [▶ Execute]                     │   │   │  
│  │  └──────────────────────────────────────────────┘   │   │  
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  [📋 Copy All]  [💾 Save Session]  [🔄 Re-diagnose]         │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### Local Learning (Fully Offline)

After each troubleshooting session, ObserveCo logs the outcome:

```sql
CREATE TABLE IF NOT EXISTS troubleshoot_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_name TEXT NOT NULL,
    timestamp INTEGER NOT NULL,
    diagnosis_summary TEXT,
    fixes_recommended TEXT,  -- JSON array
    fix_applied TEXT,         -- which fix user clicked
    resolved INTEGER,         -- did it work? (user feedback)
    payload_hash TEXT         -- hash of diagnostic payload (for pattern matching)
);
```

On subsequent troubleshooting sessions, ObserveCo includes prior history in the payload:

```json
"troubleshooting_history": [
  {
    "date": "2026-05-28",
    "symptoms": "high token usage",
    "fix": "chisel compress --mode lite",
    "resolved": true
  },
  {
    "date": "2026-06-01",
    "symptoms": "browser-automation errors",
    "fix": "disabled plugin",
    "resolved": true
  }
]
```

The LLM sees: "Last time you saw this, X worked." This is the user's own learning loop — fully local, no network needed.

#### Entry Points

| Surface | Trigger | What Happens |
|---------|---------|-------------|
| Agent card | Click "🔧 Troubleshoot" button | Assemble payload for this agent, send to LLM |
| Anomalies Inbox | Click "🔧 Troubleshoot" on anomaly card | Pre-filter payload to anomaly context |
| Companion Mode | `observeco troubleshoot <agent>` | CLI version — same payload, terminal output |
| Push alert | "Troubleshoot" link in Telegram/email alert | Deep link to dashboard with pre-loaded diagnosis |

#### Payload Assembly Logic

```
assemble_diagnostic_payload(agent_name):
  1. pulse_data     = query pulse_log WHERE agent = ? ORDER BY timestamp DESC LIMIT 1
  2. health_score   = query context_health WHERE agent = ? ORDER BY timestamp DESC LIMIT 1
  3. token_data     = query turn_events WHERE agent = ? (last 24h aggregation)
  4. drift_data     = query chisel_drift WHERE agent = ? ORDER BY timestamp DESC LIMIT 1
  5. tool_data      = query turn_events tools_called aggregation WHERE agent = ?
  6. utilisation    = query turn_events context_sources aggregation WHERE agent = ?
  7. error_data     = query errors WHERE agent = ? (last 24h)
  8. events_data    = query config_events WHERE agent = ? (last 7d)
  9. history_data   = query troubleshoot_log WHERE agent = ? ORDER BY timestamp DESC LIMIT 5
  10. merge into diagnostic_payload JSON
  11. validate: all required fields present, no null critical fields
  12. return payload
```

Assembly time: <1s (all queries are indexed, single-table lookups).

#### Constraints Register

| Constraint | Type | Verification |
|-----------|------|-------------|
| Payload assembly <1s | Hard | Benchmark: 10 agents, all data sources |
| Payload max 8KB | Hard | Truncate low-signal fields if exceeded |
| No prompt content in payload | Hard | Only structured metrics, never SOUL.md text or agent responses |
| LLM response streamed | Hard | First token displayed within 3s of payload sent |
| User's LLM provider used | Hard | Respect `observeco config get llm.provider` — never use ObserveCo's own API key |
| Offline fallback | Hard | If LLM unreachable, show payload summary + "Copy to clipboard" for manual paste |
| Fix commands validated | Hard | Each recommended command verified against SAFE_COMMANDS allowlist before displaying |
| No auto-execution | Hard | Fixes require explicit user click — never auto-apply |
| Concurrency: one session per agent | Hard | Second troubleshoot request on same agent blocked until first completes |
| Response validation | Hard | Invalid JSON → raw text fallback with badge. Missing fields → defaults filled |
| Payload sanitisation | Hard | Error messages truncated to type only. No file paths, no content, no PII |
| Cross-platform CLI | Hard | All fix commands are Python CLI — identical on macOS/Linux/Windows |
| First-run empty state | Hard | Button hidden when no agents, greyed out when no data, enabled after first pulse |

#### Success Metrics

| Metric | Target | Measurement |
|--------|--------|------------|
| Payload assembly time | <1s | benchmark with 10 agents |
| Time to first LLM token | <3s | payload sent → first response token |
| Time to full diagnosis | <15s | payload sent → complete diagnosis displayed |
| User action rate | >50% of diagnoses result in a fix applied | fixes applied / diagnoses viewed |
| Fix resolution rate | >60% of applied fixes resolve the issue | user feedback: resolved y/n |
| User satisfaction | >70% report diagnosis was actionable | post-session survey (1-question) |
| Repeat usage | >40% of users troubleshoot again within 7d | return rate |

#### Tier

| Feature | Free | Pro |
|---------|------|-----|
| Triggered troubleshooting (click button) | ✅ | ✅ |
| Full diagnostic payload | ✅ | ✅ |
| LLM diagnosis with recommendations | ✅ (uses user's own LLM) | ✅ |
| Fix execution via dashboard (click to run) | ✅ | ✅ |
| Troubleshooting history (last 5 sessions) | ✅ | ✅ |
| Cross-agent pattern recognition ("this worked for other agents like yours") | ❌ | ✅ |
| Fleet-wide learning (anonymised patterns from all users) | ❌ | ✅ |
| Export diagnosis as markdown/PDF | ❌ | ✅ |

#### Estimated effort

~4d (1d payload assembly + 1d LLM integration + 1d response display + 1d entry points + local learning)

#### Dependencies

- §3.25 (LLM-Powered Intelligence) — uses same LLM service for provider routing
- §3.41 (Post-Turn Webhook) — provides turn-level data for payload
- §3.43 (Tool Efficiency) — provides tool ranking data for payload
- §3.44 (Context Utilisation) — provides utilisation data for payload
- User must have LLM provider configured (`observeco config set llm.provider`)

---

### 3.53 OTel Trace Ingestion (🔴 Planned)

**Tagline:** *Every agent handoff leaves a trace. ObserveCo sees the whole chain.*

**What it is:** Wires `signal_tracer.py` → `otel_listener.py` into the production signal routing path. Every time an agent emits a `delegate_task`, `task_result`, `delegate_escalation`, or `bridge_signal`, the signal is enriched with OTel trace fields (`trace_id`, `span_id`, `parent_span_id`, `hop_count`) and a span is POSTed to the local ObserveCo OTel listener at `http://127.0.0.1:4318/v1/traces`. The listener stores spans in a new `trace_spans` SQLite table. This is the data foundation for every multi-agent visibility feature (§3.54-3.56).

**Why this exists separately from the signal router:** The signal router delivers files. The OTel pipeline is a *sidecar* — it does not block delivery. If the listener is down, signals still route. OTel is best-effort telemetry, not a delivery dependency.

#### RDR: OTel Trace Ingestion

```
Problem: Current signals carry trace_id/span_id fields (SIGNAL_SCHEMA.md)
         but nothing calls enrich_signal() or post_to_observeco().
         The fields are dead letters. Cross-agent trace trees cannot
         be reconstructed because nobody emits spans.
Solution: Wire signal_tracer.py into:
          (a) signal_router.py — enrich every routed signal with trace
              fields, POST span to OTel listener asynchronously.
          (b) ACPS session runners (run_{agent}_session.sh) — when
              writing a response signal, propagate parent trace context
              from the incoming signal.
          (c) otel_listener.py — new trace_spans table + query API.
Key constraint: OTel is never a delivery dependency. Best-effort POST
                with 3s timeout. Listener down → signal gets trace
                fields but no span persisted. No retry.
Success metric: >90% of delegate_task signals produce a complete span
                chain (SUBMITTED → WORKING → COMPLETED). Span ingest
                latency <100ms from signal write. Zero regression in
                signal delivery latency (router still <1m).
```

#### Architecture

```
signal_router.py (1m cron)
  │
  ├── Reads outbox/, validates, delivers to inbox
  │
  └── enrich_signal() ← new: injects trace_id/span_id if missing
      │
      └── post_to_observeco() ← new: async POST to OTel listener
          │                        (fire-and-forget, 3s timeout)
          ▼
  otel_listener.py (port 4318)
      │
      ├── /v1/traces ← receives OTel spans in OTLP JSON format
      │
      └── trace_spans table (SQLite) ← new
          ├── trace_id TEXT
          ├── span_id TEXT
          ├── parent_span_id TEXT
          ├── name TEXT (e.g. "signal.delegate_task")
          ├── kind TEXT ("internal")
          ├── start_time_unix_nano INTEGER
          ├── end_time_unix_nano INTEGER
          ├── status TEXT ("OK" | "ERROR")
          ├── attributes TEXT (JSON blob — from/to/type/hop_count/payload_preview)
          ├── agent_from TEXT
          ├── agent_to TEXT
          ├── hop_count INTEGER
          └── payload_preview TEXT
```

**Trace source table:** Signals that emit spans:

| Signal Type | Span Name | When Emitted |
|-------------|-----------|-------------|
| `delegate_task` | `signal.delegate_task` | On router delivery to executor inbox |
| `task_result` | `signal.task_result` | On router delivery to delegator inbox |
| `delegate_escalation` | `signal.delegate_escalation` | On write to Sean's inbox or delegator |
| `bridge_signal` | `signal.bridge_signal` | On cross-ecosystem routing |
| All others | `signal.{type}` | On every router delivery (for completeness) |

#### Signal Router Integration

In `~/.hermes/scripts/signal_router.py`, add after successful delivery:

```python
from signal_tracer import enrich_signal, signal_to_otel_event, post_to_observeco

def _trace_signal(signal: dict):
    """Enrich and emit OTel span for a routed signal (fire-and-forget)."""
    try:
        enriched = enrich_signal(signal)
        event = signal_to_otel_event(enriched)
        post_to_observeco(event)  # 3s timeout, silent on failure
    except Exception:
        pass  # OTel is best-effort, never block delivery
```

#### ACPS Session Runner Integration

In each `run_{agent}_session.sh`, when writing a response signal:

```bash
# Propagate trace context from incoming signal
INCOMING_TRACE=$(python3 -c "import json; d=json.load(open('$SIGNAL_PATH')); print(d.get('trace_id',''))")
INCOMING_SPAN=$(python3 -c "import json; d=json.load(open('$SIGNAL_PATH')); print(d.get('span_id',''))")

# Write response signal with trace propagation
python3 -c "
import json
sig = {...your response signal...}
sig['trace_id'] = '$INCOMING_TRACE'
sig['parent_span_id'] = '$INCOMING_SPAN'
sig['hop_count'] = int('$HOP_COUNT', 10) + 1 if '$HOP_COUNT' else 1
...
"
```

#### States & Edge Cases

| State | Behaviour |
|-------|-----------|
| Happy path | Signal enriched, span POSTed, listener stores in trace_spans. Waterfall renderable. |
| Listener down (`ConnectionRefusedError`) | `post_to_observeco()` returns False silently. Signal still delivered. Missing span for this hop — chain broken in DB but partially reconstructable. |
| Listener restarting (brief 503) | Same as down — silent skip, next hop works fine. |
| Signal has no trace_id (legacy) | `enrich_signal()` generates new trace_id. This becomes the root of a new trace tree. |
| Signal has trace_id but no parent_span_id | Treated as root span of a sub-chain. Observable as disconnected trace in DB. |
| High signal volume (burst 100+ in 1m) | Each `post_to_observeco()` is a separate HTTP POST. No batching in v1. Acceptable at ecosystem scale (<50 signals/min). For >100/min, add a batch buffer in v2. |
| Malformed signal (missing payload) | Span still emitted with available fields. `payload_preview` set to `"(empty)"` or `"(malformed)"`. |

#### Lifecycle

- **Start:** Agent creates signal in `signals/outbox/`. No OTel involvement until router picks it up.
- **Route:** signal_router delivers to inbox → calls `_trace_signal()` → span emitted.
- **Consume:** ACPS session runner reads signal, propagates trace context to response.
- **Response:** Response signal routed → another span emitted with `parent_span_id` linking back.
- **Archive:** `trace_spans` data never pruned (local SQLite, low volume — ~10KB/day at current ecosystem scale. 1M spans ≈ 100MB).

#### Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Span ingestion latency | <100ms from signal write | `written_at` - `start_time_unix_nano` in trace_spans |
| Delivery latency regression | None — router <60s median | Existing SLI unchanged |
| Span completeness | >90% chains have all hops | Trace with N signals has N spans |
| Listener uptime | >99.9% (launchd managed) | `trace_spans` wrote_at gaps >5m → incident |

#### Tier

| Feature | Free (Local) | Pro |
|---------|-------------|-----|
| Span ingestion (all local signals) | ✅ All spans stored in local SQLite | ✅ Same |
| Query trace_spans via CLI | ✅ `observeco trace list` | ✅ Same |
| Trace export (raw JSON) | ✅ `observeco trace export <trace_id>` | ✅ Same |
| Remote trace aggregation | ❌ | ✅ Aggregate spans from multiple machines |
| Fleet-wide trace tree comparison | ❌ | ✅ Cross-agent chain analysis |

#### Dependencies

- `signal_tracer.py` (exists, needs no changes — `enrich_signal()` and `post_to_observeco()` already work)
- `otel_listener.py` (exists, needs `trace_spans` table + query API + launchd daemon)
- `signal_router.py` (exists, needs OTel integration call after delivery)
- Run `observeco otel start` as a launchd daemon (new plist: `ai.observeco.otel-listener.plist`, KeepAlive)

#### Estimated effort

~2d (0.5d signal_router integration + 0.5d ACPS trace propagation + 0.5d trace_spans table + API + 0.5d launchd daemon + test)

---

### 3.54 delegate_task Protocol in signal_router (🔴 Planned)

**Tagline:** *One agent tells another: "Use your tools. Report back."*

**What it is:** Wires the `delegate_task`/`task_result`/`delegate_escalation` signal types (defined in GS-011 §Task Delegation Lifecycle) into the production `signal_router.py`. Adds tool-to-agent capability matching via `ecosystem.json` — when an agent emits `delegate_task` with `required_tools: ["web_search", "browser"]`, the router resolves which agents declare those capabilities and routes accordingly. Enforces timeout, retry, and escalation lifecycle. Provides the transport layer that §3.53 (OTel) observes and §3.55 (Trace Tree) visualizes.

**Core protocol flow:**

```
Delegator writes delegate_task → router delivers to executor's inbox
Executor picks up from inbox → processes with own tools → writes task_result
Router delivers task_result back to delegator → delegator has result

On failure:
Executor cannot complete → writes delegate_escalation → routed to delegator
Task times out → router writes delegate_escalation itself → routed to delegator
```

**Why this is separate from task orchestration frameworks:** The signal router is a transport layer, not an orchestrator. It delivers signals and enforces lifecycle guarantees (timeout, retry, escalation). It does NOT sequence multi-step work, manage DAGs, or coordinate parallel tasks. An orchestrator (future) would read trace_spans from §3.53 and emit `delegate_task` signals through this router. The router is the dumb pipe; the intelligence sits above it.

#### RDR: delegate_task Protocol

```
Problem: Today, agents coordinate work through the signal bus using
         ad-hoc types (execution_report, coordination) with no
         standard lifecycle. One agent asks "research X" and waits
         indefinitely. No timeout, no retry, no escalation.
         The signal router has no concept of "this signal is a task
         that expects a result."
Solution: Register three new signal types in signal_router.py with
          lifecycle enforcement:
          - delegate_task: submitted by delegator, routed by tool match
          - task_result: returned by executor, includes tool_usage
          - delegate_escalation: can't complete, needs human
          Add capability matching in ecosystem.json.
          Add timeout watcher that fires delegate_escalation on expiry.
Key constraint: Router is transport, not orchestrator. It enforces
                lifecycle but doesn't sequence multi-step work.
Success metric: <5% of delegated tasks end in unhandled timeout.
                >90% of task_results contain valid tool_usage data.
                Zero regression in existing signal delivery (<1m median).
```

#### Capability Matching

Extend `ecosystem.json` with a `capabilities` block per agent:

```json
{
  "agents": {
    "hound": {
      "capabilities": {
        "tools": ["calendar", "wiki", "kanban"],
        "task_types": ["coordinate", "execute"],
        "max_concurrent_tasks": 1
      }
    },
    "kepler": {
      "capabilities": {
        "tools": ["web_search", "browser", "code_editor"],
        "task_types": ["research", "build", "execute"],
        "max_concurrent_tasks": 3
      }
    },
    "pragma": {
      "capabilities": {
        "tools": ["code_editor", "test_runner", "git"],
        "task_types": ["build", "execute", "coordinate"],
        "max_concurrent_tasks": 2
      }
    }
  }
}
```

**Routing resolution:** When `delegate_task` arrives with `required_tools: [..]`:

1. Query ecosystem.json for agents whose `tools` overlap with `required_tools`
2. If exactly one match → route to that agent's inbox
3. If multiple matches → route to the one with lowest `active_task_count / max_concurrent_tasks`
4. If zero matches → reject immediately with `delegate_escalation` to delegator: "No agent has required tools: [web_search]"
5. If match but all at capacity → queue with `status: "QUEUED"`, deliver when a slot opens (v2)

#### Timeout Watcher

New component in signal_router's cron cycle:

```python
def check_delegate_timeouts():
    """Check for delegate_task signals past their timeout_seconds."""
    for task in db.query("""
        SELECT * FROM active_tasks
        WHERE type = 'delegate_task'
        AND status IN ('SUBMITTED', 'WORKING')
        AND written_at + timeout_seconds < now()
    """):
        write_escalation({
            "task_id": task.task_id,
            "status": "FAILED (timeout)",
            "delegator": task.from_agent,
            "executor": task.to_agent,
            "reason": f"Task exceeded {task.timeout_seconds}s timeout. Last status: {task.status}"
        })
```

#### Router Integration

`signal_router.py` additions (new file: `~/.hermes/scripts/signal_router_delegate.py`):

```python
class DelegateRouter:
    """Handles delegate_task lifecycle enforcement."""

    def route_by_capability(self, signal: dict) -> str | None:
        """Resolve target agent by required_tools vs ecosystem.json capabilities."""
        required = set(signal["payload"].get("required_tools", []))
        for agent, config in self.ecosystem["agents"].items():
            available = set(config.get("capabilities", {}).get("tools", []))
            if required.issubset(available):
                return agent
        return None

    def enforce_timeout(self):
        """Check and escalate timed-out tasks."""
        # ... SQL query on active_tasks tracker ...
```

#### States & Edge Cases

| State | Behaviour |
|-------|-----------|
| Happy path | delegate_task → executor's inbox → task_result → delegator's inbox. Full lifecycle. |
| No matching executor | Immediate `delegate_escalation` to delegator: "No agent supports tools [X]" |
| Executor crashes mid-task | Timeout fires after `timeout_seconds` → escalation to delegator. Router does NOT retry (retries are executor-side). |
| Executor returns `FAILED (retryable)` | Router increments retry count, re-delivers to executor (or alternative executor if one exists with same tools). Max 3 retries. |
| All retries exhausted | Router writes `delegate_escalation` to delegator with full failure history. |
| Delegator itself is unavailable | `delegate_escalation` cannot route → goes to signals/failed/. Intelligence watcher flags as `unroutable_escalation`. |
| Concurrent tasks exceed executor capacity | Signal stays in QUEUED state in outbox. Not delivered until executor reports a completed task. Queue depth tracked in `active_tasks` table. |
| Capability overlap (3 agents, same tools) | Round-robin by active_task_count ratio. No priority weighting in v1. |
| Agent's capabilities change mid-flight | Tasks in flight continue to the originally-routed executor. Capability changes only affect NEW tasks. |

#### Lifecycle

- **Submit:** Delegator writes `delegate_task` to outbox. Router validates capabilities, routes to executor inbox.
- **Work:** Executor consumes signal, sets `status: WORKING` on signal file. Processes with own tools.
- **Complete:** Executor writes `task_result` to outbox. Router delivers to delegator. Trace: `hop_count + 1`.
- **Fail:** Executor writes `task_result` with `status: failed`. Router checks `retry_on_failure`. If retryable → re-deliver. If terminal → escalate.
- **Timeout:** Router's cron watcher detects expired tasks every 60s. Writes `delegate_escalation`. No retry.

#### Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Task completion rate | >90% of submitted tasks reach COMPLETED | trace_spans chain analysis |
| Unhandled timeout rate | <5% | delegate_escalation / delegate_task ratio in trace_spans |
| Capability resolution latency | <100ms | from router tick to inbox write |
| False negative capability match | 0% | No task routed to agent that can't execute required_tools |

#### Tier

| Feature | Free (Local) | Pro |
|---------|-------------|-----|
| delegate_task routing (local ecosystem) | ✅ All local agent delegation | ✅ Same |
| Capability matching | ✅ Static ecosystem.json | ✅ Same |
| Timeout enforcement | ✅ 60s watcher | ✅ Same |
| Retry on failure | ✅ Up to 3 retries | ✅ Same |
| Cross-ecosystem delegation (Hermes ↔ OpenClaw ↔ remote A2A) | ❌ | ✅ Bridge signals + remote A2A adapter |

#### Dependencies

- GS-011 §Task Delegation Lifecycle (updated 2026-06-10 — schema, lifecycle states, payload format)
- `ecosystem.json` must be extended with `capabilities` block per agent
- `~/.hermes/scripts/signal_router.py` must import `DelegateRouter`
- New tracker table: `active_tasks` in a lightweight JSON file or SQLite for timeout watcher queries
- OTel trace propagation from §3.53 — every delegate hop MUST carry trace fields

#### Estimated effort

~2d (0.5d capability matching + 0.5d router integration + 0.5d timeout watcher + 0.5d ecosystem.json extension + test)

---

### 3.55 Trace Tree Dashboard (🔴 Planned)

**Tagline:** *Watch your agents talk to each other — every delegation, every result, every timeout.*

**What it is:** A dashboard page that renders agent handoff chains as a waterfall/interactive tree. Reads from the `trace_spans` table (populated by §3.53) and renders each `delegate_task` → `task_result` chain as a visual trace. Each hop shows: who delegated to whom, which tools were used, latency, token cost, and status. Supports search by `trace_id`, `task_id`, agent name, and time range. Provides the human-visual answer to "what are my agents doing to each other?"

**Why this is the third piece:** §3.53 collects the data. §3.54 provides the protocol. §3.55 makes it visible. Without this dashboard, the delegation protocol and OTel spans are invisible infrastructure — technically correct but no human can verify the system is working.

#### RDR: Trace Tree Dashboard

```
Problem: Multi-agent delegation happens on the filesystem bus and
         is invisible. Humans cannot see who delegated to whom,
         whether the task completed, or where the delay was.
         Observability of agent communication is a black box.
Solution: A dashboard page that queries trace_spans and renders:
          - Waterfall view: chronological chain of delegate hops
          - Per-hop detail: tools used, latency, token cost, status
          - Search by task_id, agent name, trace_id, time range
          - Status badges: completed (green), failed (red), escalated (orange)
          - Pro: export as JSON/PDF, cross-fleet comparison, anomaly detection
Key constraint: Must render sub-second even with 10K spans in DB.
                SQLite with proper indexes can handle this.
Success metric: Trace tree renders in <500ms with 100-span chain.
                90% of users can identify a failed handoff within 5s.
```

#### States & Edge Cases

| State | Behaviour |
|-------|-----------|
| Happy path | Waterfall renders showing full chain root → leaf with per-hop metrics. All green. |
| No traces yet (fresh install) | Empty state: "No agent handoffs recorded yet. Run your agents or delegate a task to see the first trace tree." |
| Single hop (one agent, no delegation) | Trace tree shows single span: "Agent worked, no delegation." |
| Disconnected traces (missing parent_span_id) | Rendered as separate trees. Badge: "⚠️ Disconnected — trace data may be incomplete." |
| Very long chain (10+ hops) | Waterfall scrolls vertically. Tree collapses intermediate hops with expand toggle. |
| Failed hop | Red status badge. Tooltip: "Task timed out after 600s. Executor received signal but never reported back." |
| Escalated hop | Orange status badge. Click opens escalation payload. |
| Span with no payload_preview | Shows "(no preview)" — span exists but payload was too large or malformed. |
| Concurrent traces (multiple chains at same time) | Grouped by trace_id. Each trace is a separate tree. |

#### Layout

```
┌──────────────────────────────────────────────────────────────┐
│  Trace Tree Dashboard                                        │
│  [Search by task_id, agent, trace_id...] [Time range: ▼]    │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  Trace: abc123 (2026-06-10 14:00 → 14:08)                    │
│  Status: ✅ Completed  ·  3 hops  ·  Latency: 8m 32s         │
│                                                              │
│  ┌─ Hound ───────────────────────────────────────────────┐   │
│  │  📤 delegate_task → Kepler  ·  type: research         │   │
│  │  Tools requested: web_search + browser                │   │
│  │  Latency: 32s  ·  Spans: 2 (SUBMITTED → WORKING)     │   │
│  └────────────────────────────────────────────────────────┘   │
│       │                                                       │
│       ▼                                                       │
│  ┌─ Kepler ──────────────────────────────────────────────┐   │
│  │  🔧 WORKING  ·  Tools called: 8                      │   │
│  │  Tool errors: 0  ·  Latency: 28.4s                   │   │
│  │  Context: Market research on AI compliance tools...   │   │
│  └────────────────────────────────────────────────────────┘   │
│       │                                                       │
│       ▼                                                       │
│  ┌─ Kepler → Hound ──────────────────────────────────────┐   │
│  │  ✅ task_result  ·  status: completed                 │   │
│  │  Output preview: "AI compliance tools market..."      │   │
│  │  Hop latency: 32s  ·  Total chain: 8m 32s            │   │
│  └────────────────────────────────────────────────────────┘   │
│                                                              │
│  [🔍 View full trace JSON]  [💾 Export]  [🔒 Pro fleet cmp]  │
├──────────────────────────────────────────────────────────────┤
│  ⚡ Anomaly: 2 broken chains detected in last 24h            │
│  · task_id 0198: Kepler never responded (timeout 600s)      │
│  · task_id 0199: No agent matched required tools [database]  │
└──────────────────────────────────────────────────────────────┘
```

#### Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Render time (100-span chain) | <500ms | Browser DevTools → Network tab |
| Anomaly detection precision | >80% | Broken chains correctly flagged |
| User time to identify failed handoff | <5s | Survey / observation |
| % of traces with complete chain | >90% | `hop_count` == expected count |

#### Tier

| Feature | Free | Pro |
|---------|------|-----|
| Trace tree view (last 24h) | ✅ | ✅ |
| Search by task_id / agent | ✅ | ✅ |
| Per-hop detail (tools, latency, status) | ✅ | ✅ |
| Export single trace as JSON | ✅ | ✅ |
| Full history (never pruned) | ❌ (7d retention) | ✅ |
| Cross-fleet comparison | ❌ | ✅ |
| Anomaly detection (broken chains, latency spikes) | ❌ | ✅ |
| Export as PDF | ❌ | ✅ |

#### Dependencies

- §3.53 (OTel Trace Ingestion) — must be deployed first; `trace_spans` table must exist
- HTML template new file: `dashboard/templates/trace-tree.html`
- New API endpoint: `GET /api/traces/{trace_id}`, `GET /api/traces?agent=kepler&time_range=24h`
- SQL index on `trace_spans` (`trace_id`, `written_at`)

#### Estimated effort

~3d (1d API + 1d frontend waterfall rendering + 0.5d search/filter + 0.5d anomaly detection)

---

### 3.56 A2A Adapter (Remote Agent Support) (🔴 Planned)

**Tagline:** *Your local agents are A2A-discoverable. Remote agents are just another delegate target.*

**What it is:** Exposes ObserveCo-local agents as Google A2A-compatible endpoints so remote agent systems (other Hermes instances, non-Hermes frameworks with A2A support) can discover and delegate tasks to them. Also allows delegating tasks TO remote A2A agents, bridging the local `delegate_task` protocol with the standard A2A JSON-RPC over HTTP. Enables multi-machine agent swarms with uniform observability through ObserveCo's trace tree.

Follows Google's A2A specification (Apache 2.0, Linux Foundation). Implements:
- `/.well-known/agent.json` — Agent Card serving
- `POST /a2a/message/send` — JSON-RPC 2.0 task submission
- `POST /a2a/tasks/get` — Task status polling
- `POST /a2a/tasks/cancel` — Task cancellation

**Why this matters for MasterDebater users:** MasterDebater's sequential transcript model breaks at scale. Remote agents (different machines, different frameworks) have no shared filesystem. A2A gives them HTTP as a coordination layer. ObserveCo sits on top of both local and remote handoffs with the same trace tree visualization.

#### RDR: A2A Adapter

```
Problem: Our delegate_task protocol works on one machine. Multi-machine
         agent swarms need an HTTP-based standard. Google's A2A is the
         emerging open standard (Apache 2.0, Linux Foundation).
         Hermes Issue #514 proposes A2A support.
         Without A2A, ObserveCo can only observe single-machine ecosystems.
Solution: A lightweight FastAPI adapter that:
          (a) Serves /.well-known/agent.json listing local agents and their
              capabilities (from ecosystem.json).
          (b) Translates incoming A2A task_submit → delegate_task signal
              → local agent processing → A2A task_result response.
          (c) Outgoing: translates delegate_task (with remote target) →
              HTTP POST to remote A2A endpoint → incoming task_result.
          ObserveCo traces BOTH local and remote hops in the same
          trace_spans table, giving unified visibility.
Key constraint: A2A adapter is a separate process (port 4319), not in
                the signal router. Router stays fast and local-only.
                A2A is a bridge, not the backbone.
Success metric: Remote agent delegation succeeds within 2x local latency.
                Agent Card is parseable by A2A client SDK.
                Trace tree shows remote hops with latency attribution.
```

#### Architecture

```
┌─────────────────────────────────────────────────┐
│  Local Machine (Mac Mini)                       │
│                                                 │
│  signal_router ←─ delegate_task ←─ Local Agent  │
│       │                                          │
│       ├── Local delivery ──→ Local Agent         │
│       │                                          │
│       └── Remote target? ──→ A2A Adapter         │
│                               (port 4319)         │
│                                  │               │
│                                  ├──→ HTTP POST  │
│                                  │    to remote  │
│                                  │    A2A agent  │
│                                  │               │
│  otel_listener (4318) ←──────────── trace spans  │
│       │                                          │
│  trace_tree Dashboard                            │
└─────────────────────────────────────────────────┘
```

#### States & Edge Cases

| State | Behaviour |
|-------|-----------|
| Remote agent reachable | Task submitted via A2A JSON-RPC. Trace span shows `kind: "client"`. Result routed back as `task_result`. |
| Remote agent unreachable | 3 retries with 5s backoff. On exhaustion → `delegate_escalation` to delegator. |
| Remote agent returns malformed response | `task_result` written with `status: failed`, `error: "unparseable response"`. |
| A2A adapter process down | Local delegation unaffected. Remote delegation fails immediately with connection error. |
| No A2A agents configured | Adapter serves Agent Card but rejects outgoing delegation with "No remote A2A agents configured." |

#### Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Remote delegation latency | <2x local | Comparison with equivalent local task |
| Agent Card parseability | 100% valid per A2A spec | Validate against A2A SDK |
| Remote failure detection | <30s | Timeout + retry exhaustion |

#### Tier

| Feature | Free | Pro |
|---------|------|-----|
| A2A Agent Card serving (be discoverable) | ✅ | ✅ |
| Receive tasks from remote A2A agents | ✅ | ✅ |
| Delegate tasks TO remote A2A agents | ❌ (local only) | ✅ |
| Trace remote hops in trace tree | ❌ | ✅ (remote spans marked with `kind: "client"` or `kind: "server"`) |
| Remote agent health monitoring | ❌ | ✅ |

#### Dependencies

- §3.53 (OTel Trace Ingestion) — remote spans stored in same `trace_spans` table
- §3.54 (delegate_task Protocol) — adapter translates delegate_task to A2A JSON-RPC payload
- Google A2A spec (`pip install "a2a-sdk[http-server]"` or implement from spec)
- New process: `observeco a2a start|stop|status` (port 4319, separate from otel_listener port 4318)
- Hermes Issue #514 — alignment with upstream A2A implementation

#### Estimated effort

~5d (1d Agent Card + 1d incoming A2A handler + 1d outgoing A2A client + 1d trace integration + 1d test + docs)

---

## 11. Commercial Lifecycle

**Source:** `specs/commercial-scope.md` has full detail. This section documents the lifecycle states and transitions. Updated 2026-06-19 — beachhead is free-for-Hermes (all features open, no trial needed). Pro pricing deferred.

### 4.1 Lifecycle States (Beachhead Model)

```
pip install observeco 
       │
       ▼
    Free (Hermes users)
  - All features open
  - No trial needed
  - LLM features: BYOK (`OBSERVECO_LLM_API_KEY`)
  - Banner: "X invocations this month"
  - When Pro ships (future): 30-day trial available
       │
       ├────────────────────────────┐
       ▼                            ▼
  Free (non-Hermes)           Pro (future, $9 Solo/mo)
  - Generic discovery only    - Push alerts, extended
  - No Hermes-specific        - History, auto-heal
    features (drift, chisel,  - Stripe subscription
    post-turn hook)           - 30-day trial
```

### 4.2 State Transitions (Beachhead Model)

| From | To | Trigger | Action |
|------|----|---------|--------|
| Free (beachhead) | Trial active (future) | First Pro-locked feature click after Pro tier ships | Create trial.json with 30-day expiry |
| Trial active | Solo active (future) | Stripe Checkout → webhook | Write license file, stop countdown |
| Solo active | past_due | Stripe `invoice.payment_failed` | Set `past_due`, start 3-day grace |
| past_due | Free | Grace expires | Lock Pro features |
| Trial active | Expired | Daily cron | Lock Pro features, show "Trial ended" |
|
|### 4.3 Error/Failure States

| Scenario | Behaviour | Recovery |
|----------|-----------|----------|
| License validation fails (network down) | Offline cache valid for 24h (`CACHE_TTL=86400`) | Retry on next cron cycle or dashboard load |
| License validation fails (cache expired too) | Lock Pro features, show "License check failed" banner | User runs `observeco license refresh` or waits for next cron |
| `trial.json` corrupted/deleted | Trial is lost — user can't get it back (single-creation policy) | Must subscribe or accept Free tier |
| Stripe webhook not received | License state frozen until next daily validation cron | Cron polls Stripe API status |
| Stripe webhook delivery failure | Retry with exponential backoff (3 attempts) | After 3 failures: log to audit, surface in admin dashboard |
| MCP tool called but license expired | `require_pro()` returns 403, error message: "This feature requires an active Pro subscription" | User subscribes or trial remains active |
| Concurrent license checks (race condition) | SQLite WAL mode handles concurrent reads. Writes serialized by lock. | No data loss. Retry on SQLITE_BUSY. |

---

## 12. Constraints Register

### 12.1 Data Store Constraints

| Constraint | Type | Value | Rationale | Verification |
|-----------|------|-------|-----------|-------------|
| `pulse.db` max size | Hard | 500 MB | SQLite performs well up to ~1 GB; 500 MB gives safety margin | Monitor `~/.observeco/pulse.db` size. Auto-warn at 400 MB. |
| `pulse_log` row count per agent | Hard | 500,000 rows (Free: 7-day auto-prune, Pro: user-configurable) | Prevents unbounded SQLite growth. 24h × 2 rows/min × 30 agents = ~86,400 rows/day at max | Pruning cron runs daily at 3am |
| Dashboard concurrent users | Soft | 1 (local) | Dashboard is local-first, single-user by design | Single Flask dev server — not designed for multi-user |
| Dashboard startup time | Soft | <3s from cold start | Acceptable for a CLI-launched dashboard | Timer in startup logs |
| Pulse check latency per agent | Hard | 10s timeout | Agents that don't respond in 10s are marked dead | `requests.get(timeout=10)` |
| Pulse check cycle interval | Hard | 30s (±2s jitter) | Balance between freshness and DB write rate | Cron tick every 30s |
| API payload size | Soft | <10 KB per response | Keeps dashboard responsive over local network | Benchmark on dashboard load |

### 5.2 Environment Constraints

| Constraint | Type | Platforms | Detail |
|-----------|------|-----------|--------|
| Python version | Hard | 3.10+ | Minimum supported. 3.11+ recommended for performance. |
| OS support (launchd) | Hard | macOS | `launchctl` for daemon management |
| OS support (systemd) | Hard | Linux | `systemctl` for daemon management |
| OS support (Docker) | Soft | Linux (Docker) | `docker ps` for container health |
| OS support (Windows) | Planned (Phase 4) | Windows | `tasklist` / `Get-Process` for process health |
| Dashboard browser | Soft | Any modern browser | Chrome, Firefox, Safari, Edge — no IE/legacy |
| LLM for Pro features | Hard | Any OpenAI-compatible endpoint | User provides their own API key. ObserveCo never bundles an LLM key. |
| Offline mode | Hard | All | Core monitoring (pulse, alerts, dashboard) works fully offline. License check caches for 24h. LLM Pro features require internet. |
| Single instance | Hard | One dashboard process per machine | Port 8090 exclusive. Second instance fails on bind. |

### 5.3 Security Constraints

| Constraint | Type | Detail |
|-----------|------|--------|
| No telemetry | Hard | Zero outbound data to cloud. All data in `~/.observeco/pulse.db` local SQLite. |
| License key storage | Hard | Stored in `~/.observeco/license.json`, 0600 permissions, 24h cache |
| Trial token | Hard | Stored in `~/.observeco/trial.json`, created once, never transferred |
| Dashboard access | Soft | Localhost-only (127.0.0.1:8090). Not exposed to network by default. |

---

## 13. Operational SLIs (Service Level Indicators)

Targets for key product metrics. Measured during development and validated pre-launch.

| Feature | SLI | Target | How Measured | Current |
|---------|-----|--------|-------------|---------|
| **Pulse check** | Detection latency (dead → first failure recorded) | <35s (one cycle + margin) | Clock between daemon tick and DB write | ⏳ Not benchmarked |
| **Dashboard** | Time to interactive (cold start) | <3s | `python -m observeco dashboard` → page fully rendered | ⏳ Not benchmarked |
| **Dashboard** | Load time (page refresh with populated fleet) | <1s | Fleet page with 20 agents, all metrics loaded | ⏳ Not benchmarked |
| **Agent discovery** | Discovery complete (auto-scan) | <5s | `observeco agent discover` with 3 Hermes profiles | ⏳ Not benchmarked |
| **Safety Guard** | Trip latency (3 failures → guard engaged) | <95s (3 cycles × 30s + overhead) | Time from failure 1 to guard status change | ⏳ Not benchmarked |
| **License validation** | Cache hit for offline validation | 24h validity | License check every 24h ± 1h cron window | ⏳ Not benchmarked |
| **License validation** | Validation latency (cloud check) | <2s | `POST /api/licenses/validate` response time | ⏳ Not benchmarked |
| **Error history** | Query latency (last 24h, 20 agents) | <500ms | Dashboard error tab with 20 agents | ⏳ Not benchmarked |
| **DB** | SQLite write latency per pulse | <50ms | Single pulse write to `pulse_log` | ⏳ Not benchmarked |
| **DB** | Pruning cron duration (7-day retention) | <30s | 3am cron with 500K rows | ⏳ Not benchmarked |

**⏳ = Not benchmarked (target defined, measurement pending).** Benchmarks run during Phase 7 (human test) and recorded in Phase 8 (meta).

---

**Trigger:** Mike Piccolo's iii.dev worker-bus architecture analysis (May 29, 2026). Three patterns from iii adopted into our existing architecture.

### 5.1 Signal Trace Propagation (OTel Distributed Tracing)

| Feature | Description |
|---------|-------------|
| Signal schema | Added `trace_id`, `span_id`, `parent_span_id`, `hop_count` to signal JSON format |
| Trace propagation | Every agent handoff (Dreamer→Main→Hound→Pragma) carries shared `trace_id` |
| Span per hop | Each signal hop generates unique `span_id`; `parent_span_id` links to previous hop |
| OTel export | `~/.hermes/scripts/signal_tracer.py` converts enriched signals to OTel events at `POST /v1/traces` |
| ObserveCo ingestion | `otel_listener.py` accepts spans from OTel endpoint |
| Trace tree reconstruction | Golden Gate runner can reconstruct full agent handoff chain from stored spans |

**Files:**
- `~/.hermes/scripts/signal_tracer.py` — `make_trace_id()`, `propagate_trace()`, `enrich_signal()`, `signal_to_otel_event()`
- `~/.hermes/signals/SIGNAL_SCHEMA.md` — updated with trace fields

**Depends on:** Existing `otel_listener.py` (`src/observeco/otel_listener.py`) and `otel_bridge.py`

### 5.2 Fail-Closed Verification Gate

**Based on iii's fail-closed design:** if the verifier/approval agent is unreachable or the 5s timeout fires, the action is DENIED. Not allowed. Not retried.

| Scenario | Behavior (THICK mode) | Behavior (THIN mode) |
|----------|----------------------|---------------------|
| Verifier reachable → ALLOW | ✅ Action passes | ✅ Action passes |
| Verifier reachable → DENY | ❌ Action blocked | ✅ Action passes (no gate) |
| Verifier unreachable | ❌ **Blocked** (fail-closed) | ✅ Action passes |
| Verifier timeout (5s) | ❌ **Blocked** (fail-closed) | ✅ Action passes |
| Read-only action (help/status) | ✅ Always passes | ✅ Always passes |
| No verifications on disk | ❌ **Blocked** — "run verify first" | ✅ Action passes |

**Module:** `~/.hermes/scripts/fail_closed_gate.py`

```python
gate = VerificationGate(mode="thick")
result = gate.check_verification("build.tool.deploy", "kepler")
if result.denied:
    print(f"Blocked: {result.reason}")
```

**Config:** `~/.hermes/config/verification_gate.yaml`
- `mode: thick | thin | custom`
- `deny_on_unreachable: true` (iii's default — fail-closed)
- `deny_on_timeout: true` (fail-closed with 5s timeout)
- `allow_unverified_read: true`

### 5.3 Thin/Thick Config Toggle

**Based on iii's insight:** "Thin vs thick is a config change, not a rewrite." Same wire protocol, same trace shape. The slider moves by changing `mode:` in config.

| Mode | Gates Active | Use Case |
|------|-------------|----------|
| **thin** | None (all bypassed) | Autonomous research agents, experimental loops |
| **thick** | verification + approval + policy + admission | Production, customer-facing agents |
| **custom** | Selective enable/disable | Specific workflow needs |

**Toggle path:** Edit `~/.hermes/config/verification_gate.yaml` → change `mode:` line.
**Runtime switch:** `gate.set_mode(ThinThickMode.THIN)` — same gate object, different config.

### 5.X Cross-References

- iii Worker-Composable Agent Harness Architecture — `SecondBrain/3_Resources/AI_Developments/iii Worker-Composable Agent Harness Architecture.md`
- Signal Protocol v2 — `~/.hermes/signals/SIGNAL_SCHEMA.md`
- OTel Bridge — `src/observeco/otel_bridge.py`
- OTel Listener — `src/observeco/otel_listener.py`

---

## 14. Context Intelligence Rollout Plan

**Added:** 2026-06-06. Defines the phased rollout for the Context Intelligence layer (§3.30–§3.35) + unified surface views.

**Design principle:** Five surface views over one shared data model. Build the consumers first, extract the shared layer when patterns emerge (§3.35). Premature abstraction on a product still finding its surface is how you get a beautiful ORM that fits nothing.

### 7.1 Rollout Phases

| Phase | Name | What Ships | Depends On | Effort |
|-------|------|-----------|------------|--------|
| **P1** | Agent Profile + Context Health | Agent Profile page (scrollable, replaces drill-modal as deep dive), Context Health Score (§3.30) on fleet cards + profile, Plugin Firewall data (§3.32) in profile, "What Changed" timeline (§3.31) in profile. Drill-modal stays as quick glance. | Existing pulse.db + chisel data | ~5d |
| **P3** | Anomalies Inbox | Fleet-wide anomaly scanner surfacing dead agents, drift spikes, error bursts, context health drops >20pts/24h, plugins turning red. Reads pulse_log + chisel_drift + errors + context_health + config_events. | P1 data model (partially) | ~3d |
| **P2** | Companion Mode | `observeco companion` CLI command. Terminal status summary: fleet overview + context health + top plugins + active anomalies. Same data model, different surface. Powers OpenClaw launcher integration ("command-line ears"). | P1 + P3 for anomaly data | ~2d |
| **P4** | Journey / Onboarding | "Get Started" tab tracking user milestones: agent discovered ✓, brain viewed ✓, chisel run ✓, alert configured ✓. Context Fire Drill button (§3.33) + Session Insurance section (§3.34). | P1 complete | ~2d |

**Revised priority:** P1 → P3 → P2 → P4. Anomalies Inbox before Companion Mode because anomalies create urgency — the activation moment. Companion Mode is retention (useful for power users), not acquisition (doesn't drive adoption alone). Exception: if OpenClaw launcher integration specifically needs Companion Mode, P2 moves up.

### 7.2 What DOESN'T Change

- **Plugin tab** stays as-is (ClawForge plugin integration). Its `initPlugin()` hook loads plugin-stats and plugin-hooks independently — no overlap with Context Intelligence views.
- **Brain Analysis tab** stays as-is (token breakdown, drift, savings chart).
- **Existing 5-tab drill modal** stays for quick inspection. Agent Profile is the deep-dive companion, not a replacement.

### 7.3 Drill-Modal vs Agent Profile Coexistence

| Surface | Job | Trigger |
|---------|-----|---------|
| Drill modal (existing) | Quick glance — 5 tabs, scan-level detail | Click agent card |
| Agent Profile (P1) | Deep dive — full picture, Context Health, Plugin Firewall, What Changed, Fire Drill, Checkpoint | Click agent name or "View Full Profile" button in modal |

Pattern: modal = scan, profile = investigate. Two different jobs, two different surfaces. Users keep muscle memory.

### 7.5 Mockup Status

| Mockup | Status | Changes Needed |
|--------|--------|----------------|
| `agent-profile.html` | ✅ Aligned | Minor: ObserveCo header + JetBrains Mono + dashboard toast |
| `fleet-with-chisel.html` | ✅ Aligned | Minor: ObserveCo header logo + tier-badge + dashboard toast |
| `journey-onboarding.html` | ✅ Aligned | Minor: ObserveCo header logo + JetBrains Mono + dashboard toast |
| `anomalies-inbox.html` | ✅ Rewritten (19KB) | Dashboard-aligned — logo, mono, tier, toast right |
| `companion-terminal.html` | ✅ Rewritten (13KB) | Dashboard-aligned — logo, mono, tier, terminal output |
| `alert-management.html` | ✅ Built (25KB) | Dashboard-aligned — logo, mono, tier, toast right |

### 7.6 Effort Summary

| Item | Effort | Phase |
|------|--------|-------|
| Context Health Score (§3.30) | ~2d | P1 |
| Agent Relapse Prevention (§3.31) | ~2d | P1 |
| Plugin Firewall Score (§3.32) | ~1.5d | P1 |
| Anomalies Inbox (§3.37) | ~3d | P3 |
| Companion Mode (§3.38) | ~2d | P2 |
| Journey / Onboarding (§3.39) | ~2d | P4 |
| Alert Management Surface (§3.40) | ~3d | P3 |
| Context Fire Drill (§3.33) | ~2d | P4 |
| Session Insurance (§3.34) | ~2.5d | P4 |
| Unified Data Model (§3.35) | ~1d | Extract during P3 |
| Agent Profile page | ~2d | P1 |
| Mockup rewrites (anomalies, companion) | ~2d | P3/P2 |
| Mockup rewrites (alert management) | ~1d | P3 |
| **Total** | **~26d** | |

P1 is the heaviest phase (~5d) because it establishes the foundation: 3 intelligence features + the profile page itself. Subsequent phases are lighter.

### 7.7 Differentiation Note

Context Health Score (§3.30) and Plugin Firewall Score (§3.32) must be visible by P1. If they're not, the product looks like another fleet dashboard. These two features differentiate ObserveCo from every other monitoring tool — they measure **intelligence quality**, not infrastructure health. They need to be in the P1 Agent Profile view, even if the initial implementation is crude.

---

*End of master plan.*

---

## 15. Framework Data Integration — The Real Observability Layer

**Added:** 2026-06-06. Defines how ObserveCo acquires observability data from the frameworks users actually run, and how that data powers the Context Intelligence features.

### 12.1 Strategic Context

ObserveCo's current data comes from infrastructure health signals (pulse checks, errors, circuit breakers). This is necessary but not sufficient. To claim "best local-first observability," we need to correlate infrastructure health with **application-level data** — what the agent actually *did* on each turn.

Local-first users don't install APM tools (Langfuse, Arize). They use **frameworks** (CrewAI, LangChain, LiteLLM, OpenClaw) that already generate observability data via built-in callbacks and SQLite databases. The data exists — we just need to read it.

### 12.2 Data Sources

| Source | What It Captures | How We Read It | Priority |
|--------|-----------------|----------------|----------|
| **ClawBench traces (OpenClaw + Hermes)** | Per-turn: tool calls, model calls, token counts, timing | Read `~/.hermes/traces/traces.db` (already populated) | P0 — our ecosystem, already live |
| **LiteLLM gateway** | Every LLM call: tokens, cost, latency, provider, model, success/fail | Parse `litellm_proxy.db` SQLite | P0 — for non-OpenClaw users |
| **CrewAI callbacks** | Agent interactions, task completion, tool calls | Read callback logs / optional Langfuse export | P1 — if user has it |
| **LangChain callbacks** | Chain steps, retrieval results, LLM calls | Read callback handler output | P1 — if user has it |
| **Hermes agent daemon** | Agent health, signal flow, error patterns | Read agent daemon logs + signal routing | P0 — our ecosystem |

**For OpenClaw/Hermes users:** The trace-hook plugin and hermes-trace wrapper already capture per-turn data into ClawBench's traces.db. No additional instrumentation needed — we built it today. The framework integrations (LiteLLM, CrewAI) are for users outside our ecosystem who need observability on top of their existing agent stack.

### 12.3 Architecture

```
┌─────────────────────────────────────────────────────────┐
│  Path A: OpenClaw/Hermes Users (our ecosystem)          │
│                                                         │
│  OpenClaw Agent                                         │
│    └── trace-hook plugin → traces.db (per-turn data)   │
│  Hermes Agent                                          │
│    └── hermes-trace wrapper → traces.db                │
│  Agent daemon                                          │
│    └── logs + signal routing → health data              │
│                                                         │
│  ObserveCo reads traces.db + daemon logs               │
│  → Already capturing data. No additional instrumentation│
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│  Path B: Framework Users (CrewAI/LangChain/LiteLLM)    │
│                                                         │
│  Agent Framework (CrewAI/LangChain)                    │
│    └── built-in callbacks → logs                       │
│  LLM Gateway (LiteLLM)                                │
│    └── captures every API call → litellm_proxy.db     │
│                                                         │
│  ObserveCo reads framework logs + LiteLLM SQLite       │
│  → No custom SDK instrumentation needed                │
└─────────────────────────────────────────────────────────┘
```

**No OTel pipeline needed** for either path. Path A uses our own tracing (already built). Path B reads what the frameworks already produce.

### 12.4 What This Enables (Correlated Insights)

| APM Data (from framework) | Health Data (from ObserveCo) | Correlated Insight |
|--------------------------|----------------------------|--------------------|
| Turn 11 took 3x longer | Memory at 94% | "Slowdown is context eviction, not model" |
| Error rate jumped 2% → 15% | SOUL.md edited yesterday | "Config change broke prompt effectiveness" |
| Token cost doubled this week | Drift score climbing | "Agent is re-reading context due to retrieval degradation" |
| Agent stopped responding to tool calls | Circuit breaker tripped | "Agent hit failure limit — auto-heal exhausted" |
| Output quality dropped (eval score ↓) | Context window at 85% | "Agent is evicting relevant skills to fit context" |

None of these insights are possible with APM alone or health monitoring alone. They require **correlation across both data layers.**

### 12.5 Build Plan

| Phase | What | Effort | Value | Spec |
|-------|------|--------|-------|------|
| 1 | ClawBench trace reader — parse `traces.db` for OpenClaw + Hermes per-turn data | ~1d | Our ecosystem data (already captured) | Existing |
| 2 | LiteLLM SQLite reader — parse token costs, latency, provider breakdown | ~2d | External framework data | Existing |
| 3 | Hermes daemon log reader — parse agent health + signal flow | ~1d | Our ecosystem data | Existing |
| **4** | **Post-Turn Webhook receiver — `POST /api/webhooks/turn` endpoint + SQLite storage + file sink fallback** | **~3d** | **Per-turn execution data for OpenClaw/Hermes users** | **§3.41** |
| **5** | **Hermes Evaluation Trace Export — eval_events ingestion pipeline + quality trend** | **~2d** | **Quality signals (was this turn good?)** | **§3.42** |
| 6 | Correlation engine — join framework traces + health signals by timestamp + agent_id | ~4d | Cross-layer insights | Existing |
| 7 | Dashboard updates — Insights tab, fleet view with framework data, agent profile cost/latency | ~3d | User sees correlated data | Existing |
| **8** | **Tool Efficiency Ranking — aggregate turn_events by tools_called, cost/error/latency ranking** | **~1.5d** | **"Disable this tool" recommendations** | **§3.43** |
| **9** | **Context Source Utilisation — aggregate loaded vs skipped sources, lazy-load recommendations** | **~1.5d** | **"Remove these skills from defaults" recommendations** | **§3.44** |
| 10 | Master plan + mockup updates | ~1d | Documentation aligned | Existing |
| **Total** | | **~22.5d** | | |

**Note:** Phases 4–5 are the Dynamic Execution Layer — they close the APM gap for OpenClaw/Hermes users. Phase 4 (Post-Turn Webhook) is the single highest-value addition. Phases 8–9 are derived intelligence that becomes available once Phase 4 data flows in.

**Dependency chain:** Phase 4 → Phase 8 + Phase 9 (derived from webhook data). Phase 5 → Phase 6 correlation (quality signals feed correlation engine).

> ⚠️ **Model flag for §12.5:** Phases 1–3 (trace readers) and Phases 7–10 (dashboard, ranking, utilisation) are pattern tasks → use DeepSeek V4 Flash. Phase 6 (correlation engine — joining framework traces + health signals by timestamp) is a reasoning task → use Kimi 2.6. See §13.3.

> ⚠️ **Model flag for §3.45:** Diagnostic payload assembly is a pattern task → use DeepSeek V4 Flash. The system prompt design and response format schema are reasoning tasks → use Kimi 2.6. See §13.3.

### 12.6 Privacy Angle

ObserveCo captures **token counts and timing**, not actual prompt content. This is a differentiator vs Langfuse (which captures full prompt text). The privacy story: "We know how many tokens your agent used and how long it took — we never see what it said."

### 12.7 Key Insight from Research

Local-first users use **frameworks**, not APMs. They build agents with CrewAI or LangChain, call LLMs through LiteLLM or direct SDK, and rely on console logs for debugging. The frameworks already generate observability data — they just don't aggregate or analyse it. ObserveCo's job is to read what the frameworks produce and surface the insights.

**For our ecosystem (OpenClaw/Hermes):** The trace-hook plugin and hermes-trace wrapper capture per-turn data into ClawBench's traces.db. The Dynamic Execution Layer (§3.41–§3.44) adds post-turn webhooks, eval trace export, tool efficiency ranking, and context source utilisation — closing the APM gap for our ecosystem users. With these additions, OpenClaw/Hermes users get the same dynamic analysis quality as CrewAI/LangChain users, plus Observeco's unique context intelligence that no framework provides.

**For external framework users:** The LiteLLM angle is particularly strong: if a user runs LiteLLM (many do for multi-provider support), every LLM call goes through it. It captures tokens, cost, latency, provider, model, and success/failure. We get full APM data for free by reading its SQLite DB.

---

## 16. LLM Model Recommendation for ObserveCo Build

**Added:** 2026-06-07. Defines which LLM models to use for developing and building ObserveCo's remaining spec items, optimised for quality-per-dollar.

### 13.1 Model Selection Rationale

ObserveCo's remaining build (~22.5d) consists of two task types:

1. **Pattern-based tasks** (80%): Schema creation, HTTP endpoints, SQL aggregation, dashboard widgets that reuse existing HTML patterns. These follow established conventions in the codebase. Quality requirement: accurate code generation, not creative problem-solving.

2. **Reasoning-heavy tasks** (15%): Correlation engine design, anomaly detection algorithms, multi-provider cost math, cross-feature integration, rule engine architecture. These require multi-step reasoning, edge case analysis, and systems design.

3. **Boilerplate** (5%): Template generation, test scaffolding, documentation. Free models suffice.

### 13.2 Recommended Models

| Model | Price (in/out per M) | Score | Context | Use For | Est. Cost |
|-------|---------------------|-------|---------|---------|----------|
| **DeepSeek V4 Flash (Max)** | $0.14 / $0.28 | 75 | 1M | Primary coding — schemas, endpoints, queries, widgets | ~$5 |
| **Kimi 2.6** | $0.95 / $4.00 | 84 | 256K | Architecture, algorithms, integration design | ~$12 |
| **Free models** (Qwen3.6-27B, MiMo-V2-Flash) | $0 / $0 | 73 / 59 | 262K / 256K | Boilerplate, templates, simple generation | $0 |
| **Total** | | | | | **~$17** |

### 13.3 Task-to-Model Mapping

#### DeepSeek V4 Flash — Pattern Tasks

| Spec | Task | Why DeepSeek Works |
|------|------|--------------------|
| §3.41 | SQLite schema (`CREATE TABLE turn_events`) | Copy-paste with column name changes |
| §3.41 | HTTP endpoint (`POST /api/webhooks/turn`) | Straightforward FastAPI route |
| §3.41 | File sink fallback (write JSON to directory) | File I/O, no reasoning needed |
| §3.41 | Dashboard timeline HTML | Reuse existing dot-table pattern |
| §3.42 | SQLite schema (`CREATE TABLE eval_events`) | Copy-paste with column name changes |
| §3.42 | Export pipeline (read Hermes internals → write DB) | Data pipeline, straightforward |
| §3.42 | Quality trend chart (SVG sparkline) | Reuse existing drift chart pattern |
| §3.43 | Aggregation query (`SELECT tools_called, AVG(...)`) | Standard SQL GROUP BY |
| §3.43 | Cost calculation math (tokens × provider rate) | Simple multiplication |
| §3.43 | Status assignment (if/else for red/yellow/green) | Threshold logic |
| §3.43 | Dashboard table widget | Reuse existing skill audit table pattern |
| §3.44 | Aggregation query (`SELECT context_sources_loaded`) | Standard SQL GROUP BY |
| §3.44 | Utilisation score math (loaded ÷ total turns) | Simple division |
| §3.44 | Recommendation generation (if utilisation <20% AND tokens >500) | Threshold logic |
| §3.44 | Dashboard table widget | Reuse existing pattern |
| §12.5 | ClawBench trace reader | SQLite parsing, straightforward |
| §12.5 | LiteLLM SQLite reader | SQLite parsing, straightforward |
| §12.5 | Hermes daemon log reader | Log parsing, straightforward |

#### Kimi 2.6 — Reasoning Tasks

| Spec | Task | Why Kimi Is Needed |
|------|------|--------------------|
| §12.5 | **Correlation engine** — join turn_events + pulse_log by timestamp + agent_id | Temporal correlation with edge cases: timestamp tolerance (±30s?), missing data, LEFT JOIN strategy, null handling. DeepSeek gives naive INNER JOIN. Kimi thinks through data quality issues. |
| §3.37 | **Anomalies Inbox rule engine** — read 10+ data sources, produce prioritised anomalies | Hardest architectural problem. Join across 10 tables, correlate by timestamp, assign severity, suppress duplicates, attribute root cause. DeepSeek gives 10 independent if/else chains. Kimi designs composable predicates. |
| §3.42 | **Quality regression detection** — distinguish normal variance from real regression | Signal processing: rolling averages, standard deviation thresholds, minimum consecutive drops before alerting. DeepSeek gives naive threshold. Kimi gives proper anomaly detection. |
| §3.43 | **Multi-provider cost attribution** — handle DeepSeek/OpenAI/Ollama/cached tokens | Matrix of edge cases: different providers, different models, cached vs non-cached, streaming vs non-streaming, Ollama = $0. DeepSeek misses the Ollama case. Kimi handles the full matrix. |
| §3.44 | **Fire Drill integration** — merge utilisation data with survival simulation | Systems integration: two independent data sources merge, fallback logic when one is missing, utilisation-weighted degradation prediction. Requires understanding both features' data models. |
| §3.30 | **Context Health Score algorithm** — compute 0-100 composite from 5 signals | Weighted scoring with normalisation: memory bloat, drift delta, context utilisation trend, error rate, sources-skipped ratio. Requires thinking about signal weighting and edge cases (all signals missing?). |
| §3.31 | **Relapse Prevention correlation** — link config changes to degradation signals | Causal attribution: SOUL.md edit → drift spike → error burst. Requires temporal ordering, confidence scoring, and ruling out coincidences. |

#### Free Models — Boilerplate

| Task | Model | Why Free Works |
|------|-------|---------------|
| Test scaffolding | Qwen3.6-27B | Follow existing test patterns |
| Documentation markdown | MiMo-V2-Flash | Template-based writing |
| Config file generation | Qwen3.6-27B | YAML/JSON templates |
| CI/CD pipeline yaml | Qwen3.6-27B | Copy-paste with modifications |

### 13.4 Decision Rule

> **If the task is "write code that follows a pattern I've already built" → DeepSeek V4 Flash.**
> **If the task is "design the algorithm that decides what the code does" → Kimi 2.6.**
> **If the task is "generate boilerplate from a template" → Free model.**

### 13.5 Cost Summary

| Model | Tasks | Est. Tokens | Est. Cost |
|-------|-------|-------------|----------|
| DeepSeek V4 Flash | ~120 pattern tasks | ~25M tokens | ~$5 |
| Kimi 2.6 | ~15 reasoning tasks | ~8M tokens | ~$12 |
| Free models | ~20 boilerplate tasks | ~10M tokens | $0 |
| **Total** | **~155 tasks** | **~43M tokens** | **~$17** |

---

## 17. Token Rogue Guardrails — Threat Model & Build Phases

**Added:** 2026-06-10 (Kepler–Hound Debate Rounds 1–3, Sean-confirmed. Token-based ceiling per user directive: "token rather than fixed cost because users can use different LLMs")
**Status:** Approved — Sean-confirmed
**Source:** `~/.hermes/intelligence/kepler/debate-token-rogue-scenarios-outcome.md`

An agent or agent service burning tokens uncontrollably is not one problem — it's a taxonomy of 16 failure modes. This section maps every scenario ObserveCo can face, defines which ones we detect, which we prevent, and which are hard boundaries. Each gap is costed and assigned to a build phase.

### 14.1 Threat Model — 16 Scenarios

| # | Scenario | Origin | Speed | Detection | Prevention | Gap |
|---|----------|--------|-------|-----------|-------------|-----|
| 1 | Infinite loop (recursive tool calls) | Agent code / LLM | Sudden burst | ✅ During (pulse + circuit breaker) | Partial (activity-based config) | P1: expose config UI |
| 2 | Prompt injection → unbounded tool use | External attack | Sudden burst | ⚠️ Medium (tool count metric) | ❌ | P1: tool-call count widget |
| 3 | Context window bloat (no compression) | Agent code / misconfig | Gradual drift | ✅ Well detected | ❌ (runtime scope) | None |
| 4 | Runaway sub-agent spawning | Agent code / LLM | Exponential burst | ⚠️ Partial (lineage missing) | ❌ | P2: parent-child lineage |
| 5 | Stuck retry loop (API errors → retries) | Infrastructure | Gradual bleed | ✅ Well detected (ratio + errors) | ❌ | Trivial: dashboard query |
| 6 | Model escalation (switch to expensive model) | Agent code / LLM | Step-function | ✅ Well detected (cost delta) | ❌ | Trivial: already caught |
| 7 | Parallel session flood (same API key) | Misconfiguration | Linear burst | ⚠️ Partial (registered only) | ❌ | P1: aggregate fleet alerts |
| 8 | Adversarial max output (inflated responses) | External attack | Per-interaction | ✅ After fact | ❌ (runtime scope) | None |
| 9 | Context leak between sessions | Agent code bug | Gradual drift | ✅ Well detected | ❌ (runtime scope) | None |
| 10 | Compromised API key (third party) | External attack | Catastrophic burst | ❌ **Hard boundary** | ❌ | Document boundary |
| 11 | Watch daemon goes rogue | Internal bug | Gradual/sudden | ❌ **Critical gap** | ❌ | **P0: self-monitoring** |
| 12 | Slow drift creep (weeks) | Accumulating features | Very gradual | ✅ Well detected (drift chart) | ❌ | Trivial: configurable lookback |
| 13 | CHISEL compression failure → token inversion | Agent runtime | Step-function | ✅ Already caught | ❌ | None |
| 14 | Stale state pinning (repeats same work) | Agent design flaw | Sustained bleed | ⚠️ Spec (repetition detection) | ❌ | P2: output consistency |
| 15 | Multi-agent cascade deadlock | Ecosystem design | Sustained bleed | ⚠️ Spec (signal flow) | ❌ | P3: cross-agent visibility |
| 16 | Cache poisoning (corrupted data → spin) | Infrastructure | Sudden burst | ❌ Weak / out of scope | ❌ | Document boundary |

### 14.2 Coverage Summary

- **7 well-detected (no build gap):** S3, S5, S6, S8, S9, S12, S13
- **4 partially detected (build gaps):** S1, S2, S4, S7
- **3 weak/out-of-scope (future gaps):** S14, S15, S16
- **2 hard boundaries (document, not fix):** S10, S16
- **1 critical gap (must fix before Pro launch):** S11

### 14.3 Build Phases

#### Phase G1 — Ship with Launch (~5.5 days)

*Blocks Pro launch. Non-negotiable.*

| # | Gap | Spec Ref | Effort | Category | Free/Pro |
|---|-----|----------|--------|----------|----------|
| G1.1 | **Self-monitoring budget cap** — ObserveCo's own LLM diagnosis calls tracked from a separate token pool. **Token-based (not fixed $$)** because users may use different LLMs. Default: 500K tokens/day. Hard floor: 100K tokens/day. Graceful degradation at 100%. | §14.3.G1.1 | ~1d | Infrastructure | Both |
| G1.2 | **Manual kill switch** — STOP button with 2-step confirmation. API endpoint for programmatic kill. No auto-kill in v1. | §14.3.G1.2 | ~2d | Dashboard + API | Both |
| G1.3 | **Activity-based circuit breaker config** — expose circuit breaker settings in dashboard UI. Trip on turns/min exceeding configurable threshold. | §14.3.G1.3 | ~0.5d | Dashboard | Both |
| G1.4 | **Turn-rate alerting** — turns/min per agent. Dashboard widget. Alert at configurable threshold (default 30/min). | §14.3.G1.4 | ~1d | Monitoring + Alerts | Both |
| G1.5 | **Tool-call count per turn** — track tool calls per turn. Anomalous volume (>20/turn) flagged. | §14.3.G1.5 | ~0.5d | Monitoring | Both |
| G1.6 | **Threat model documentation** — published boundaries: what's monitored, what's not. README + /docs. | §14.3.G1.6 | ~0.5d | Documentation | — |

##### G1.1 — Self-Monitoring Budget Cap

**Problem:** If heal system or LLM-powered diagnosis enters a loop, it consumes unbounded tokens on self-diagnosis.

**Solution:** Separate token counter for all 7 LLM consumers. Default ceiling 500K tokens/day. Non-configurable floor 100K tokens/day. Graceful degradation at 100% — all self-diagnosis LLM calls blocked, static fallbacks used.

**States:**

| State | Behavior |
|-------|----------|
| Below floor (100K) | Normal operation |
| Between floor and ceiling | Normal, self-usage widget shows % |
| At ceiling (500K) | All self-diagnosis LLM blocked. Static fallbacks. Banner: "Self-diagnosis paused — budget exhausted. Resets at midnight." |
| Near ceiling (90%+) | Dashboard warning banner |
| Reset at midnight | Counter resets to 0 |
| Crash/restart | Counter persists in SQLite, resumes from last value |

**ACs:**
- [ ] AC1: Separate counter tracks all 7 LLM consumer calls independently
- [ ] AC2: Default ceiling 500K tokens/day enforced
- [ ] AC3: At ceiling, all 7 consumers fall back to static responses gracefully
- [ ] AC4: Counter persists across server restarts
- [ ] AC5: Dashboard shows self-usage widget with %

##### G1.2 — Manual Kill Switch

**Problem:** A rogue agent cannot be stopped from the dashboard. User must SSH into the machine.

**Solution:** STOP button per agent card with 2-step confirmation. `POST /api/agents/{id}/stop`.

**States:**

| State | Display |
|-------|---------|
| Agent running normally | STOP button visible (red, subtle) |
| Step 1 clicked | "Are you sure?" dialog with agent name |
| Confirmed | "Stopping agent..." spinner |
| Success | Card shows 🔴 "Manually stopped" |
| Failed (permission) | "Could not stop agent — insufficient permissions" |
| Failed (process gone) | "Agent already stopped" |

**ACs:**
- [ ] AC1: STOP button on every agent card
- [ ] AC2: 2-click confirmation: 1st → dialog, 2nd → execute. ESC cancels.
- [ ] AC3: POST /api/agents/{id}/stop kills process (SIGTERM → 5s → SIGKILL)
- [ ] AC4: Kill event audit-logged in `heal_log` with timestamp

##### G1.3 — Activity-Based Circuit Breaker Config

**Problem:** Circuit breaker trips on failures only. A runaway agent doing 100 turns/min (all successful) won't trip.

**Solution:** Expose existing circuit breaker settings in dashboard UI. Add turns/min activity threshold alongside failure thresholds.

**ACs:**
- [ ] AC1: Dashboard shows circuit breaker config per agent
- [ ] AC2: Turns/min threshold configurable alongside failure thresholds
- [ ] AC3: Changing threshold persists across server restart

##### G1.4 — Turn-Rate Alerting

**Problem:** No visibility into agent turn rate. Silent runaway burns tokens unnoticed.

**Solution:** Dashboard widget showing turns/min per agent. Alert when rate exceeds configurable threshold (default 30/min).

**ACs:**
- [ ] AC1: Dashboard widget shows current turn rate per agent
- [ ] AC2: Alert fires when threshold exceeded
- [ ] AC3: Threshold configurable per agent

##### G1.5 — Tool-Call Count Per Turn

**Problem:** An agent making 50 tool calls per turn is anomalous. No metric to detect.

**Solution:** Track tool calls per turn. Dashboard metric. Flag >20 tools/turn.

**ACs:**
- [ ] AC1: Tool count tracked per turn
- [ ] AC2: Dashboard widget shows average tool calls per turn
- [ ] AC3: Anomalous volume flagged with visual indicator

##### G1.6 — Threat Model Documentation

**Problem:** Users don't know what ObserveCo monitors vs what it doesn't. False sense of security.

**Solution:** Published boundaries in README + /docs page. What's monitored, what's not, what kill switch can/can't do, what auto-heal does/doesn't fix.

**ACs:**
- [ ] AC1: README has "What ObserveCo Monitors" section with explicit scope
- [ ] AC2: /docs page has detailed threat model

#### Phase G2 — Post-Launch, Month 2 (~10.5 days)

| # | Gap | Spec Ref | Effort | Category | Free/Pro |
|---|-----|----------|--------|----------|----------|
| G2.1 | **Aggregate fleet spend alerts** — dashboard alert when total fleet token spend exceeds daily/hourly budget. Covers S7 (parallel session flood). Requires alert infrastructure from §17 push alerts. | §14.3.G2.1 | ~2d | Alerts | Pro |
| G2.2 | **Alert → wait → auto-stop** — configurable escalation: detect anomaly → send alert → wait N seconds → auto-stop agent if no human response. Opt-in only, never default-on. Requires kill switch API from G1.2. | §14.3.G2.2 | ~3d | Self-Heal + Alerts | Pro |
| G2.3 | **Parent-child agent lineage tracking** — fleet view shows agent parent-child relationships. 100 runaway sub-agents become 1 root cause. Covers S4. | §14.3.G2.3 | ~3d | Dashboard | Both |
| G2.4 | **Output consistency analysis** — detect when agent produces identical or near-identical tool calls across cycles. Flags stale-state pinning. Covers S14. | §14.3.G2.4 | ~2d | Intelligence | Pro |
| G2.5 | **Configurable drift lookback** — extend drift trend chart (§5) with configurable lookback window (7/30/60/90 days). Query parameter change, not new architecture. Covers S12 long-term. | §14.3.G2.5 | ~0.5d | Dashboard | Both |

#### Phase G3 — Ecosystem, Month 3+ (~9 days)

| # | Gap | Spec Ref | Effort | Category | Free/Pro |
|---|-----|----------|--------|----------|----------|
| G3.1 | **Cross-agent signal flow visibility** — track signal delivery between agents. Detect sent-but-never-acknowledged signals. Surface 'alive but not producing' pattern. Covers S15. | §14.3.G3.1 | ~5d | Intelligence | Pro |
| G3.2 | **Sophisticated auto-escalation** — configurable timeout policies, escalation chains, multi-level severity response. Extends G2.2 with richer policy engine. Opt-in Pro, never default-on. | §14.3.G3.2 | ~3d | Self-Heal + Alerts | Pro |
| G3.3 | **Per-turn model attribution** — track which model was used per turn. Diagnostic value for S6 (model escalation). Nice-to-have; cost delta already catches the spend spike. | §14.3.G3.3 | ~1d | Monitoring | Pro |

### 14.4 Self-Monitoring Architecture (G1.1 Detail)

**Principle:** The doctor needs its own instruments.

ObserveCo's watch daemon and LLM diagnosis features consume tokens. These MUST be tracked and capped independently from agent monitoring.

**Architecture decisions:**

1. **Separate token pool.** ObserveCo's own LLM calls draw from a self-monitoring budget, not the user's agent monitoring budget.
2. **Token-based ceiling, not cost-based.** Users can configure different LLMs (OpenAI, Anthropic, Ollama, DeepSeek) with different pricing. A fixed dollar cap ($5/day) penalizes cheap-model users and under-protects expensive-model users. Token-based ceiling adapts to any model — the ceiling stays meaningful regardless of whether the user runs Ollama (free) or Claude Opus ($15/M tokens).
3. **Non-configurable floor.** Minimum: 100K tokens/day for self-diagnosis. Below this, the LLM diagnosis feature cannot function reliably.
4. **Default ceiling.** 500K tokens/day. Sufficient for ~250 diagnosis calls at 2K tokens each. Adjustable upward by user, never below floor.
5. **Graceful degradation.** When self-monitoring budget reaches 80%, log warning. At 100%, disable LLM diagnosis but continue all other monitoring (pulse, token tracking, drift, error history). Dashboard shows 'LLM diagnosis paused — daily self-monitoring budget reached.'
6. **Visibility.** Dashboard shows ObserveCo's own token usage in a dedicated widget: tokens used today / ceiling, diagnosis calls made, budget status.

### 14.5 Kill Switch Architecture (G1.2 Detail)

**Principle:** Detection terminates in an action surface, not necessarily an automated action.

**v1 (G1.2 — Manual):**
- STOP button on each agent card in fleet view
- 2-step confirmation modal: 'Are you sure? This will immediately terminate agent [name]. Active turns will be interrupted.'
- API endpoint: `POST /api/agents/{id}/stop`
- No auto-kill. Every kill requires human confirmation.
- Kill action: sends SIGTERM to agent process. If process doesn't terminate within 10s, sends SIGKILL.
- Audit: every kill action logged with timestamp, user, agent, and reason (manual button press or API call).

**v2 (G2.2 — Alert → wait → auto-stop):**
- Extends kill switch with configurable auto-escalation
- Alert fires → N-second wait (configurable, default 300s) → if not acknowledged → auto-stop
- Opt-in only per agent. Default: disabled.
- Requires explicit user acknowledgment of auto-kill policy during setup.
- Every auto-kill logged with full context: what triggered the alert, wait duration, whether human was notified.

**v3 (G3.2 — Sophisticated escalation):**
- Multi-level escalation chains
- Severity-based timeout policies (critical = 60s, high = 300s, medium = never auto-kill)
- Integration with alert management surface (§36)

**Why no fully automated spend enforcement:** An observability tool that kills agents without human confirmation is a single point of failure. False positive on a kill = trust-destroying event. The layered approach preserves the principle (detection terminates in action) while minimizing blast radius.

### 14.6 Hard Boundaries (Document, Don't Fix)

These scenarios are outside ObserveCo's monitoring boundary by design:

| # | Scenario | Why Out of Scope | What to Tell Users |
|---|----------|------------------|--------------------|
| S10 | Compromised API key | ObserveCo monitors agent activity, not API key usage at the provider level. A stolen key used directly via curl generates zero ObserveCo events. | 'Set provider-level usage caps (OpenAI: Settings → Billing → Usage limits). Rotate keys regularly. ObserveCo monitors your agents, not your API keys.' |
| S16 | Cache poisoning | Data integrity is an application-layer concern. ObserveCo sees agent behavior, not data correctness. Poisoned data produces normal-looking agent activity. | 'ObserveCo monitors agent behavior patterns. If your agent's input data is corrupted, the agent's behavior may appear normal. Validate data integrity at the application layer.' |

### 14.7 Pre-Mortem

1. **Kill switch without confirmation → healthy agent dies.** A misclick on the dashboard kills a production agent mid-task. Operator blames ObserveCo.
   - **Mitigation:** Two-step confirmation. No single-click kills. Ever. (G1.2)

2. **Self-monitoring budget too low → LLM diagnosis silently fails.** Customer sets aggressive cap, diagnosis breaks, customer thinks ObserveCo is broken.
   - **Mitigation:** Non-configurable floor (100K tokens/day). Graceful degradation with visible status message. (G1.1)

3. **Threat model becomes sales objection.** Competitors use our honesty against us: 'ObserveCo admits they can't detect prompt injection!'
   - **Mitigation:** Frame as transparency advantage: 'We publish our threat model because you deserve to know where your monitoring ends. Our competitors don't publish theirs — not because they catch everything, but because they haven't done the analysis.' (G1.6)

---

## 18. Session Intelligence Layer (agenttrace-inspired — new 2026-06-16)

**Context:** Evaluated [agenttrace](https://github.com/luoyuctl/agenttrace) v0.4.6 against our 9,782 Hermes sessions. It parsed $1,740 estimated cost, 7.72B tokens, 81K tool calls, and 12 anomalies from local logs — proving the pattern works at scale. Seven features identified as high-value additions to ObserveCo. All are implementation patterns, not competitive IP — agenttrace is MIT licensed.

**Validation data (our fleet, via agenttrace):**
- 9,782 sessions analysed
- $1,740.74 estimated lifetime cost
- 7.72B total tokens
- 81,368 tool calls (0% failure rate)
- Top burn: deepseek-v4-flash ($783), MiMo-V2.5 ($504), GLM-5.1 ($180)
- 12 anomalies detected (all `no_tools` type)

### 3.57 Multi-Source Log Parser Engine (Feature #57)

**Tagline:** *Read session logs from any agent framework — not just Hermes and OpenClaw.*

**What it is:** An extensible parser architecture where each agent source (Claude Code, Codex CLI, Gemini CLI, Cursor, Aider, Cline, Kimi CLI, Copilot, generic JSON/JSONL) gets a dedicated parser module. A `DetectFormat` function identifies the source from file structure/content, then routes to the correct parser. Each parser extracts: roles, timestamps, model, token usage, tool calls, tool errors, and session metadata.

**Why this matters:** ObserveCo currently detects Hermes + OpenClaw agents only. The real market is multi-framework teams. A LangChain team using Claude Code + Cursor + Aider needs observability too. This parser engine makes ObserveCo framework-agnostic at the log level.

**Architecture:**
```
observeco/parsers/
  __init__.py          — DetectFormat() dispatcher
  base.py              — BaseParser ABC: parse(session_log) → SessionData
  hermes_db.py         — Hermes state.db (already exists)
  openclaw.py          — OpenClaw session JSON (already exists)
  claude_code.py       — ~/.claude/projects/ JSONL
  codex_cli.py         — ~/.codex/sessions/ JSON
  gemini_cli.py        — ~/.gemini/tmp/ transcripts
  cursor.py            — Cursor export format
  aider.py             — .aider.chat.history.md
  cline.py             — VS Code globalStorage tasks
  kimi_cli.py          — Kimi session logs
  generic_jsonl.py     — Any {role, content, timestamp} JSONL
```

**Parser interface:**
```python
class BaseParser(ABC):
    @abstractmethod
    def detect(self, path: Path) -> bool: ...
    @abstractmethod
    def parse(self, path: Path) -> SessionData: ...

class SessionData:
    agent_name: str
    model: str
    turns: list[Turn]
    tokens: TokenUsage
    tool_calls: list[ToolCall]
    started_at: datetime
    ended_at: datetime
```

**Effort:** ~4d (base + 6 parsers + format detection + tests)
**Reference:** agenttrace parser architecture, docs/parser-guide.md

---

### 3.58 Cost Estimation Engine (Feature #58)

**Tagline:** *Know what your agents cost — in dollars, not just tokens.*

**What it is:** A pricing table mapping model names → $/token (input, output, cache separately). Applied to token counts already tracked by ObserveCo to produce cost estimates per session, per agent, per day, per model, and fleet-total.

**Why this matters:** ObserveCo tracks tokens but doesn't convert to dollars. "7.72B tokens" is abstract. "$1,740 lifetime, $783 on deepseek-v4-flash" is actionable. Cost is the metric buyers report to their boss.

**Pricing table structure:**
```python
MODEL_PRICING = {
    # provider/model → (input_per_1m, output_per_1m, cache_per_1m)
    "deepseek-v4-flash":    (0.15, 0.30, 0.01),
    "glm-5.1":              (0.60, 2.50, 0.10),
    "kimi-k2.5":            (0.55, 2.19, 0.15),
    "claude-sonnet-4.5":    (3.00, 15.00, 0.30),
    "gpt-5.3":              (2.50, 10.00, 1.25),
    "ollama-local":         (0.0, 0.0, 0.0),  # free
    # ... auto-updated from provider pricing pages
}
```

**Dashboard widgets:**
- Fleet total cost (large number, trend arrow)
- Cost-by-model breakdown (horizontal bars)
- Cost-by-agent breakdown (table)
- Daily cost trend (7d/30d/90d)
- Cost-per-session distribution (top 10 most expensive sessions)

**Data source:** Token counts from `token_logs` table (populated by §14 post-turn webhook + former §42 proxy — proxy row now deprecated but table data remains). Pricing from maintained model table. Total = Σ(input_tokens × input_rate + output_tokens × output_rate + cache_tokens × cache_rate).

**Effort:** ~2d (pricing table + calculation engine + dashboard widgets + CLI)

---

### 3.59 Composite Health Score (Feature #59)

**Tagline:** *One number tells you if your agent is healthy — or heading for trouble.*

**What it is:** A 0–100 composite score per agent, combining multiple signals into a single at-a-glance metric. Separate from Context Health Score (§27) which measures brain/context quality — this measures operational health.

**Why this matters:** ObserveCo has pulse (alive/dead) and circuit breaker (tripped/not). But "alive" doesn't mean "healthy." An agent with 15% tool failure rate, 3 retry loops, and escalating costs is technically alive but operationally degraded. Buyers need a single number to compare agents and prioritise attention.

**Scoring formula (weighted composite):**
```
Health Score = 
    (pulse_uptime × 0.30) +
    (tool_success_rate × 0.25) +
    (anomaly_penalty × 0.20) +
    (cost_stability × 0.15) +
    (latency_stability × 0.10)

Where:
  pulse_uptime       = % of pulse checks returning alive (24h window)
  tool_success_rate  = 1 - (tool_failures / total_tool_calls)
  anomaly_penalty    = max(0, 1 - (anomaly_count × 0.15))
  cost_stability     = 1 - min(1, cost_variance / mean_cost)  // spikes penalised
  latency_stability  = 1 - min(1, latency_variance / mean_latency)
```

**Dashboard display:**
- Each agent card: score badge (🟢 90+ / 🟡 70-89 / 🔴 <70) + trend arrow (↑↓→)
- Click score → drill-down showing each component's contribution
- Fleet average score in header

**Alerts:**
- Score drops below 70 → warning alert
- Score drops below 50 → critical alert + auto-heal trigger (Pro)
- Score drops >20 points in 24h → regression alert

**Effort:** ~2d (scoring engine + dashboard widget + alert hooks)

---

### 3.60 Anomaly Detection Taxonomy (Feature #60)

**Tagline:** *Catch the failure modes that don't crash your agent — just waste your money.*

**What it is:** A structured anomaly classification system that detects subtle agent degradation patterns beyond binary crash detection. Each anomaly type has: detection logic, severity level, plain-English explanation, and recommended action.

**Why this matters:** ObserveCo's circuit breaker catches crashes. But an agent that's alive yet burning tokens in retry loops, or running 93-turn sessions without calling any tools, or suddenly costing 5x more than yesterday — that's broken too. These patterns are invisible without dedicated detection.

**Anomaly types:**

| Type | Detection Logic | Default Severity | Example |
|------|----------------|-----------------|--------|
| `no_tools` | Session has 0 tool calls but >2 turns | Low | Agent gave 5 responses without using any tools — possible hallucination |
| `high_cost` | Session cost >3σ above agent's mean | High | Single session cost $3.27 vs $0.05 average |
| `long_gaps` | >60s gap between consecutive turns | Medium | Agent stalled for 4 minutes mid-session |
| `retry_loops` | Same tool called >3× consecutively with failures | High | Agent retried web_search 7 times after 403 errors |
| `context_pressure` | Token count >80% of model context window | Medium | Session hit 156K of 200K context limit |
| `cost_spike` | Daily cost >2× 7-day rolling average | High | Today's spend $12 vs $5/day average |
| `token_burn` | Single turn >500K tokens | Medium | One turn consumed 785K tokens |

**Integration with Anomalies Inbox (§33):** Each detected anomaly writes to the anomaly feed with: agent_name, anomaly_type, severity, session_id, details, detected_at, status (new/acknowledged/resolved). The Anomalies Inbox renders these with severity-coloured badges.

**Integration with Push Alerts (§17):** High-severity anomalies trigger push alerts (Pro).

**Integration with Composite Health Score (§59):** Anomaly count feeds the `anomaly_penalty` component.

**Effort:** ~3d (7 detectors + severity scoring + dashboard feed + tests)

---

### 3.61 CI Quality Gates (Feature #61)

**Tagline:** *Fail the build if your agents are degraded — observability as a quality gate, not just a dashboard.*

**What it is:** A CLI command (`observeco gate`) that evaluates fleet health against configurable thresholds and returns exit code 0 (pass) or 1 (fail). Designed for CI/CD integration: GitHub Actions, GitLab CI, Jenkins, pre-commit hooks.

**Why this matters:** Dashboards are passive — someone has to look at them. CI gates are active — they block deployments when agents are unhealthy. This transforms ObserveCo from "nice to check" to "must pass before ship." It's the feature that makes ObserveCo part of the engineering workflow, not just a monitoring afterthought.

**CLI interface:**
```bash
# Basic gates
observeco gate --fail-under-health 80
observeco gate --fail-on-critical
observeco gate --max-tool-fail-rate 15
observeco gate --max-anomaly-severity medium

# Combined gates
observeco gate \
  --fail-under-health 80 \
  --fail-on-critical \
  --max-tool-fail-rate 15 \
  --format json \
  --output gate-result.json

# Compare against baseline
observeco gate --baseline last-week.json --max-regression 10
```

**Exit codes:**
- 0 = all gates passed
- 1 = one or more gates failed
- 2 = error (ObserveCo not running, no data, etc.)

**Output formats:**
- `json` — machine-readable, for CI artifacts
- `html` — self-contained report for issue links / PR comments
- `markdown` — for GitHub PR checks
- `text` — terminal summary

**CI integration example (GitHub Actions):**
```yaml
- name: Agent Health Gate
  run: |
    observeco gate \
      --fail-under-health 80 \
      --fail-on-critical \
      --max-tool-fail-rate 15 \
      --format json \
      --output agent-health-report.json
- uses: actions/upload-artifact@v4
  if: always()
  with:
    name: agent-health
    path: agent-health-report.json
```

**Pro tier:** Custom gate policies (YAML-defined rule chains), regression detection against historical baselines, scheduled gate runs with alert delivery, CI integration guides for 5+ platforms.

**Effort:** ~2d (gate evaluation engine + CLI + 4 output formats + CI docs)

---

### 3.62 Session Baseline Diffing (Feature #62)

**Tagline:** *Save a snapshot. Compare next week. Catch regressions before they ship.*

**What it is:** Save fleet state (cost, tokens, health scores, anomaly counts, tool failure rates) as a baseline JSON. Compare subsequent runs against it to detect regressions with quantified deltas.

**Why this matters:** Without baselines, you can't answer "did last week's config change make things better or worse?" You see current numbers but have no reference point. Baselines turn raw metrics into trend intelligence.

**CLI interface:**
```bash
# Save current state as baseline
observeco baseline save --name "pre-config-change" -o baseline.json

# Compare current state against baseline
observeco baseline diff --against baseline.json

# Output: regression report
# Cost:      $12.40/day  (+23% vs baseline $10.08/day)  ⚠️
# Health:    94 avg     (-4 pts vs baseline 98)          ✅
# Anomalies: 7 count    (+4 vs baseline 3)              ⚠️
# Tokens:    890M/day   (+8% vs baseline 824M/day)      ✅
```

**Dashboard:**
- Baseline comparison view: side-by-side metric cards with delta arrows
- Trend chart with baseline line overlaid
- "Create baseline" button on fleet dashboard

**What gets snapshotted:**
```json
{
  "timestamp": "2026-06-16T07:00:00Z",
  "name": "pre-config-change",
  "fleet": {
    "total_cost": 12.40,
    "total_tokens": 890000000,
    "avg_health": 94,
    "anomaly_count": 7,
    "tool_fail_rate": 0.8,
    "active_agents": 12,
    "by_agent": { ... },
    "by_model": { ... }
  }
}
```

**Pro tier:** Automated daily/weekly baselines, regression alerts ("cost up >20% vs 7-day baseline"), multi-baseline comparison (compare against last week, last month, pre-deploy).

**Effort:** ~2d (snapshot engine + diff logic + CLI + dashboard view)

---

### 3.63 Static Report Export (Feature #63)

**Tagline:** *One file. Full fleet picture. Share it with anyone — no server, no login, no setup.*

**What it is:** `observeco report` generates a self-contained HTML/JSON/Markdown file with fleet summary, cost breakdown, health trends, anomaly list, and top sessions. The HTML report is a single file with inline CSS — no external dependencies, no backend needed, opens in any browser.

**Why this matters:** ObserveCo's dashboard requires the server running. For sharing with stakeholders who don't have ObserveCo installed (boss, client, external team), a static report is the path of least resistance. Attach it to an email, link it in a Slack thread, upload it as a CI artifact.

**CLI interface:**
```bash
# Full report (HTML — default)
observeco report -o fleet-report.html

# JSON for programmatic consumption
observeco report -f json -o report.json

# Markdown for GitHub/Notion
observeco report -f markdown -o report.md

# Filtered report (last 7 days, specific agents)
observeco report --since 7d --agent kepler --agent hound -o weekly.html
```

**HTML report contents:**
1. **Header** — ObserveCo branding, timestamp, fleet size
2. **Summary cards** — Total sessions, total tokens, total cost, avg health, tool failure rate
3. **Cost-by-model** — Horizontal bars with $ amounts
4. **Health trend** — Sparkline showing fleet health over time
5. **Top 10 sessions** — Table sorted by cost (most expensive first)
6. **Anomalies** — Table with severity, type, session, age
7. **Per-agent breakdown** — Table with sessions, tokens, cost, health per agent

**JSON report contents:** Same data, machine-readable. Suitable for feeding into other dashboards, archival, or programmatic analysis.

**Pro tier:** Custom report templates (logo, colours, sections), scheduled email delivery (weekly report every Monday), white-label branding (remove ObserveCo branding for resellers).

**Effort:** ~1.5d (report engine + HTML template + JSON schema + CLI)

---

## 19. Observability Fail-Safes (Missing)

**Context:** 2026-06-18 analysis identified 15 fail-safes that typical observability solutions provide but ObserveCo doesn't. All items cross-referenced against existing specs. P0 = trust erosion on Day 1, P1 = within first week, P2 = nice-to-have.

| # | Fail-Safe | Priority | Spec'd? | Existing Coverage |
|---|-----------|----------|---------|-------------------|
| 1 | **Process supervision** — launchd/systemd, auto-restart on crash/reboot | **P0** | ✅ Spec'd in obs-spec-023 §17.1 | — |
| 2 | **Startup validation** — verify deps (DB, ports, config) with clear errors | **P0** | ✅ Spec'd in obs-spec-023 §17.2 | — |
| 3 | **Stale data detection per-metric** — every chart shows "last updated X ago" | **P0** | ⚠️ Partial | obs-spec-023 §8.4 (global banner only) |
| 4 | **Disk space management** — monitor before write, alert before filling disk | **P0** | ⚠️ Partial | obs-spec-023 §7.3/§8.1 (spec'd, not implemented) |
| 5 | **Data integrity verification** — SQLite PRAGMA integrity_check, schema validation, WAL recovery | **P0** | ✅ Spec'd in obs-spec-023 §17.5 | — |
| 6 | **Self-monitoring / Meta-monitoring** — daemon heartbeat, cycle counter, escalation | **P0** | ⚠️ Partial | obs-spec-023 §9.3 (heartbeat exists, escalation missing) |
| 7 | **Bounded data retention** — configurable policy with clear drop rules | **P1** | ⚠️ Partial | obs-spec-023 §7.4 (spec'd, not implemented) |
| 8 | **Graceful degradation under load** — drop samples rather than crash | **P1** | ❌ Not spec'd | — |
| 9 | **Upgrade safety** — migration verification, pre-upgrade health checks, rollback | **P1** | ⚠️ Partial | obs-spec-023 §10 (spec'd, not implemented) |
| 10 | **Configuration validation** — validate config on startup, warn about invalid values | **P1** | ❌ Not spec'd | — |
| 11 | **Health endpoint** — expose /health or /ready for external monitoring | **P1** | ⚠️ Partial | obs-spec-023 §8 (spec'd, not implemented) |
| 12 | **Structured logging** — consistent log levels, structured output | **P1** | ❌ Not spec'd | — |
| 13 | **Backup/restore** — export/import or backup mechanisms | **P2** | ⚠️ Partial | obs-spec-023 §7.2/§7.3 (spec'd, not implemented) |
| 14 | **Rate limiting on ingestion** — prevent misconfigured agents from flooding DB | **P2** | ❌ Not spec'd | — |
| 15 | **Data pipeline monitoring** — track events ingested/processed/stored, alert on pipeline lag | **P2** | ❌ Not spec'd | — |

**Cross-references:**
- `expectations-gap.md §2026-06-18 Update` — full analysis with severity ranking and partial-coverage notes
- `obs-spec-023 §17` — 6 P0 items with implementation guidance, state enumeration updates, and failure modes table updates
- `obs-spec-023 §1` — state enumeration (6 new P0 states added)
- `obs-spec-023 §3.2` — failure modes table (6 new P0 failure modes added)

**Action items:**
1. P0 items (1-6) → add to KANBAN.md P0 section, block launch
2. P1 items (7-12) → add to KANBAN.md P1 section, target D+7
3. P2 items (13-15) → add to KANBAN.md P2 section, target D+30
4. Update obs-spec-023 implementation plan (Batch 5) to cover P0 items

### 16.1 Smart Prompting Guide for DeepSeek-v4-flash Implementation

Since we implement with DeepSeek-v4-flash (less powerful than Claude), each P0 fail-safe needs explicit anti-pattern warnings and DO/DON'T guidance:

| P0 Item | #1 Anti-Pattern | Must Include |
|---------|----------------|--------------|
| Process supervision | Writes template but forgets install/uninstall logic | Restart limit (3 in 5 min) for PID-file fallback |
| Startup validation | Generic error message + sys.exit(1) | Structured messages: f"Error: {detail}\nFix: {action}" |
| Stale data per-metric | Adds last_updated to new endpoints, forgets existing ones | Search ALL @app.get/@app.post — every one needs it |
| Disk space management | shutil.disk_usage() on every write (no cache) | Cache 30s, account for WAL size, auto-resume at 1GB free |
| Data integrity | Trusts the wrong ponytail — runs full integrity_check on 1GB DB | Check DB size: <100MB → integrity_check, >100MB → quick_check |
| Self-monitoring | Assumes heartbeat file is always valid JSON | Wrap json.loads() in try/except, treat any error as "daemon may be down" |

### 16.2 Anti-Pattern Reference (All P0 Items)

**General anti-patterns for DeepSeek-v4-flash:**
1. Writes the happy path, forgets the error path. Every function needs: "What happens if X is None? What happens if the file doesn't exist? What happens if JSON is malformed?"
2. Produces generic error messages unless given templates. Always provide: "Error message MUST follow this format: 'Error: {what went wrong}\nFix: {what the user should do}'"
3. Takes the shortest path. If you don't say "do NOT use bare except:", they will. If you don't say "do NOT exit on warning", they will.
4. Does not add self-checks unless explicitly told. Every P0 implementation needs one test that fails if the logic breaks.
5. Does not handle edge cases (empty files, corrupted data, race conditions) unless explicitly enumerated.

**Per-P0 anti-patterns:**

Process supervision: DO NOT write the template file without the install/uninstall logic. The template is useless without launchctl load / systemctl enable. DO NOT use subprocess.run() without checking return code. DO NOT forget to stop the running service before uninstalling.

Startup validation: DO NOT use bare print("Error: something failed"). Every error message must tell the user WHAT went wrong and HOW to fix it. DO distinguish FATAL checks (exit 1) from WARNING checks (continue with warning).

Stale data per-metric: DO NOT add last_updated to new endpoints but forget existing ones. Search ALL @app.get and @app.post decorators. DO NOT write renderStaleness() in JS but forget to call it in the auto-refresh loop.

Disk space management: DO NOT call shutil.disk_usage() on every write without caching. For 12 agents probed every 30s, that's 24 stat() calls per minute. DO account for WAL file size in the free-space calculation.

Data integrity: CRITICAL — the ponytail in the spec says integrity_check is O(n) on table count. THIS IS WRONG. integrity_check reads every page — O(n) on DB size. For DBs > 100MB, use PRAGMA quick_check instead. DO start dashboard in READ-ONLY degraded mode on integrity failure — don't exit.

Self-monitoring: DO NOT let json.loads() raise an exception on corrupted heartbeat. DO wrap heartbeat reading in try/except — on any error, treat as "daemon may be down". DO delete heartbeat file on graceful shutdown (SIGTERM handler).

---

## 17. MLflow Integration — Eval Experiment Tracking

**Status:** 🔴 Spec (MLflow 3.14.0 installed in ObserveCo venv)

### 17.1 What MLflow gives us

MLflow is an experiment tracker. Each "run" logs params, metrics, and artifacts. The UI lets you compare runs side-by-side. ObserveCo already tracks *operational* data (tokens, drift, health) but has no *eval quality* history — "was agent X better last week than today?"

### 17.2 Integration architecture

```
Gate playbook run
  │
  ├── mlflow.start_run(run_name="hound-eval-2026-06-22")
  │     ├── log_param("agent", "hound")
  │     ├── log_param("config_hash", "abc123")
  │     ├── log_param("playbook", "ux-golden-gate")
  │     ├── log_metric("pass_rate", 0.92)
  │     ├── log_metric("latency_p50_ms", 3400)
  │     ├── log_metric("cost_per_turn", 0.023)
  │     ├── log_metric("drift_delta_pct", 1.2)
  │     └── log_artifact("playbook_output.json")
  │
  └── mlflow.end_run()
```

### 17.3 What gets tracked per eval run

| Field | Source | Example |
|-------|--------|---------|
| agent | Gate runner | `hound` |
| config_hash | Agent config digest | `sha256:...` |
| playbook | Playbook name | `ux-golden-gate` |
| pass_rate | Playbook result | `0.92` |
| latency_p50 | Turn latency | `3400` |
| cost_per_turn | Token cost | `0.023` |
| drift_delta | Chisel drift | `1.2` |
| turn_count | Total turns | `47` |
| tool_error_rate | Tool failures / total | `0.03` |
| artifact | Full output | `playbook_output.json` |

### 17.4 How ObserveCo consumes MLflow data

**Phase 1 — Dashboard widget (P0):**
- `/api/mlflow/trends` endpoint queries MLflow Tracking API for runs by agent
- Returns pass_rate over time, latency trend, cost trend
- Dashboard shows a "Quality Trend" chart alongside token/drift charts
- Filter by agent, playbook, date range

**Phase 2 — Regression detection (P1):**
- Compare last 3 runs vs previous 10 for each agent
- Alert if pass_rate drops >10% or latency increases >30%
- Surface in Anomalies Inbox (§33) as "quality regression"

**Phase 3 — CI gate integration (P2):**
- `observeco gate --mlflow` reads latest MLflow run for the agent
- `--fail-under-health 70` exits 1 if pass_rate < 0.7
- Generates comparison report: "hound: 92% → 78% (regression detected)"

### 17.5 MLflow server lifecycle

MLflow runs as a local tracking server alongside the ObserveCo dashboard:

```bash
# Start (managed by ObserveCo daemon)
mlflow server --host 127.0.0.1 --port 5000 \
  --backend-store-uri sqlite:///$DATA_DIR/mlflow.db \
  --default-artifact-root $DATA_DIR/mlflow-artifacts

# ObserveCo dashboard proxies /mlflow/ to localhost:5000
# So users access MLflow UI at /mlflow/ on the dashboard port
```

### 17.6 Pro gating

| Feature | Free | Pro |
|---------|------|-----|
| Eval run logging | ✅ (always on) | ✅ |
| Quality trend chart (7d) | ✅ | ✅ |
| Quality trend chart (90d) | ❌ | ✅ |
| Regression alerts | ❌ | ✅ |
| CI gate integration | ❌ | ✅ |
| Cross-agent comparison | ❌ | ✅ |

### 17.7 ponytail: known ceilings

- **Single-user tracking server** — MLflow's default SQLite backend doesn't scale to multi-user. Upgrade: PostgreSQL backend for team deployments.
- **No dedup on re-runs** — re-running the same eval creates a new run. Upgrade: check `mlflow.search_runs()` for existing run with same config_hash before creating.
- **Artifact storage is local** — artifacts live on disk. Upgrade: S3/GCS artifact store for team deployments.

### 17.8 Implementation order

1. Add `mlflow.start_run()` / `end_run()` wrapper in gate runner
2. Add `/api/mlflow/trends` endpoint in dashboard server
3. Add "Quality Trend" chart widget to dashboard
4. Add regression detection (compare last 3 vs previous 10)
5. Add CI gate flags
6. Add MLflow UI proxy at `/mlflow/`

---

## 18. Data Quality Tier System — Pipeline Health & User Guidance

**Status:** ✅ Live (v1 built 2026-06-22)

### 18.1 Problem

ObserveCo collects token data from multiple sources with vastly different quality levels. The dashboard showed all data mixed together with no indication of quality. Users saw charts and had no way to know if they were looking at real usage or estimates. When OTEL data stopped flowing (plugin disabled, listener crashed, endpoint wrong), the chart silently switched to watch estimates with no warning.

### 18.2 Tier Model

| Tier | Label | Accuracy | Source | Setup |
|------|-------|----------|--------|-------|
| 0 | **Estimated** | ±80% | Watch daemon (config size heuristics) | Zero — works out of the box |
| 1 | **Accurate** | ±5% | OTEL plugin (real per-call token data) | `hermes plugins enable observability/otel` |
| 2 | **Full** | ±1% | SDK patchers or proxy (exact API response) | `sitecustomize.py` or proxy config |

### 18.3 Components

| Component | File | What it does |
|-----------|------|-------------|
| Pipeline health check | `src/observeco/pipeline/health.py` | Detects active sources, determines tier, checks OTEL listener + plugin status |
| Health API endpoint | `src/observeco/dashboard/server.py` | `GET /api/pipeline/health` returns tier, per-source stats, upgrade path |
| Data quality widget | `src/observeco/dashboard/templates/index.html` | Badge (Estimated/Accurate/Full), freshness indicator, stale warning, upgrade prompt |
| Setup command | `src/observeco/cli.py` | `observeco setup` — checks plugin, listener, data flow; prints tier and next steps |
| Chart source labeling | `src/observeco/dashboard/templates/index.html` | Tooltip shows source per bucket; estimated buckets visually distinguished |

### 18.4 API Response

```json
{
  "tier": "estimated",
  "otel_stale": true,
  "sources": {
    "watch": { "active": true, "last_data": "2026-06-22T04:41:22Z", "rows_24h": 16326 },
    "otel": { "active": false, "last_data": "2026-06-15T12:37:50Z", "rows_24h": 0,
              "listener_running": true, "plugin_enabled": true },
    "sdk": { "active": false, "last_data": null, "rows_24h": 0 },
    "proxy": { "active": false, "last_data": null, "rows_24h": 0 }
  },
  "upgrade_path": "Run `observeco setup` to verify your OTEL pipeline"
}
```

### 18.5 Upgrade Paths

| Current tier | Upgrade action | Target tier |
|-------------|---------------|-------------|
| Estimated (plugin not enabled) | `hermes plugins enable observability/otel` | Accurate |
| Estimated (listener not running) | `observeco otel listen start` | Accurate |
| Estimated (both OK, no data yet) | `observeco setup` to verify | Accurate |
| Accurate | Add SDK patchers or proxy | Full |

### 18.6 ponytail: known ceilings

- **Hermes-specific plugin check** — `_check_hermes_otel_plugin_enabled()` reads `~/.hermes/config.yaml`. Non-Hermes users always show as Estimated. Upgrade: add a generic `OTEL_EXPORTER_OTLP_ENDPOINT` env var check.
- **No auto-restart** — if the OTEL listener crashes, the dashboard shows a warning but doesn't restart it. Upgrade: launchd plist with `KeepAlive` for auto-restart.
|- **Single-user** — pipeline health assumes a single Hermes installation. Upgrade: multi-user fleet health aggregation.

---

## 19. Compression Durability (Known Issue — Not Pursuing)

**Status:** ⏸️ Investigated, logged, not pursuing.

**Symptom:** Hound's SOUL.md compression (Jun 16, identity=1,617 / guidance=78) reverted to pre-compression state (identity=130 / guidance=1,564) between Jun 19 22:58 and Jun 21 16:15. The file mtime shows Jun 14 07:51 — the file was restored to exactly that version.

**Root cause:** Unknown. The SOUL.md was overwritten by an external process (not the watch daemon, not `_ensure_default_soul_md`, not a git revert). Candidates: manual restore, Hermes update reseeding profile files, Time Machine restore.

**Impact:** Drift shows 0% because the reversion happened ~6 days ago and the current values now match the 7-day rolling average. The drift algorithm is correct — the compression spike has aged out of the window.

**Why not pursuing:** The compression tool works correctly (3 days of persisted data proves it). The durability problem is a file-management issue outside ObserveCo's scope. If compression needs to stick, the fix is to protect the SOUL.md from reversion at the filesystem level (chflags, launchd guard, git-tracked source of truth) — not in ObserveCo.

**Re-evaluation trigger:** If compression reversion happens again after a manual re-apply, or if the reversion mechanism is identified as an ObserveCo process.

## 20. External Patches (Hermes CLI)

ObserveCo depends on one patch to the **Hermes Agent core** (`~/.hermes/hermes-agent/`) that cannot live in the ObserveCo repo:

| Patch | Purpose | Files | Re-apply |
|-------|---------|-------|----------|
| `patches/hermes-cli-temperature.patch` | Adds `--temperature` flag to `hermes chat` so canary tasks can control sampling temperature per run | `cli.py`, `hermes_cli/_parser.py`, `hermes_cli/cli_agent_setup_mixin.py`, `hermes_cli/main.py` | `cd ~/.hermes/hermes-agent && git apply /Users/seanfzc/projects/observeco/patches/hermes-cli-temperature.patch` |

**Why a patch, not core PR:** The Hermes core enforces a "narrow waist" rule — new CLI flags are accepted only at the edges. `--temperature` is a legitimate local need (ObserveCo canary control) but isn't upstreamed. The patch is small (4 files, ~90 lines) and isolated; if `git apply` fails after a Hermes update, the 4 edits are manual and anchored on stable method signatures (`HermesCLI.__init__`, `cli_main`, `cmd_chat`, `build_top_level_parser`).

**Verification:** `python -c "from hermes_cli._parser import build_top_level_parser; p,_,c = build_top_level_parser(); print(any('--temperature' in a.option_strings for a in c._actions))"` → `True`

**Known Hermes CLI bugs (2026-07-11):**
- `--safe-mode` silently strips `-m` model override → Hermes reports `model "" not found`. The adapter does NOT use `--safe-mode` for this reason. Canary tasks are self-contained prompts — they don't need AGENTS.md/memory isolation.
- `-p <profile>` + `-m <model>` works correctly when `--safe-mode` is NOT used. The adapter passes both flags — the canary tests the agent with its profile (skills, tools, SOUL.md) and the canary model. Verified 2026-07-12.

---

### 3.66 Session Efficiency Scoring (Feature #82)

**Status:** 🔴 Spec → obs-spec-062-session-efficiency-scoring.md
**Source:** Agent-Blackbox (MIT, Taewoo Park) — 11 context-efficiency metrics adapted for Hermes session data.

**Tagline:** *Every session gets a fuel-economy score from observed data — and one click writes the fix so the next run is cheaper.*

**What it is:** Per-session scoring on two axes:
- **Efficiency (0–100):** How economically did the agent use its context window? 11 weighted metrics: redundant reads, read amplification, retry waste, edit thrash, context pressure, large injections, yield density, tool overhead, big file reads, exploration waste, cache hit ratio.
- **Effectiveness (0–100):** Did the task actually land? From edits, commits, test exit codes, errors — separate from efficiency so a wasteful run that shipped reads differently than a clean run that failed.

**Additional intelligence:**
- **Task archetype classification** — deterministic, no model. Classifies runs as research/debug/feature/ops/edit so the score is fair (a research run isn't penalised for reading widely).
- **Per-archetype baselines** — "score 40 vs your usual 87 for research (4 runs)" — compared against same-archetype, same-project peers, not global averages.
- **Accumulative optimize memory** — one click writes a reversible block to `AGENTS.md` that accumulates across runs. Patterns seen repeatedly converge high; one-offs decay. The daemon's efficiency profile persists across sessions.
- **Custom rule packs** — drop a `rules.json` per project for project-specific guardrails (forbid-read node_modules, require-before-commit tests, etc.).

**What data it uses:** Hermes session JSONL (`~/.hermes/sessions/*.jsonl`) for tool call tracing (reads, edits, retries) + `token_logs` table for token-based metrics (context pressure, yield density, cache hit). **Ponytail (2026-07-12):** token-based metrics are `noop` — `token_logs.session_id` is empty across all 507,567 rows (verified), so no reliable session join exists yet. The 8 structural/behavioral metrics are fully live; the 3 token metrics activate only after `session_id` is populated in `log_token_turn()` (watch-daemon change, out of scope for #82).

**Where it lives:** New 6th tab in the Agent Detail modal ("Efficiency"), not Fleet tab. Session table with archetype chips + expandable efficiency card per session.

**Phases:**

| Phase | What | Files | Lines |
|-------|------|-------|-------|
| 1 | 11 metric computation + archetype + effectiveness (from existing data) | `efficiency/metrics.py` + `routes/efficiency.py` | ~350 |
| 2 | Efficiency tab in detail modal + optimize memory button | `routes/detail.py` + CSS | ~150 |
| 3 | Custom rule packs + per-archetype baselines | Modify existing baselines | ~100 |

**Effort:** ~500 lines, 6 files.
**Pro gating:** None — all free. Efficiency scoring is core product value, not upsell.

