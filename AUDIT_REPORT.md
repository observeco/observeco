# ObserveCo Codebase Audit: Data Continuity & Hardcoded Ecosystem Wiring

**Audit date:** 2026-06-17  
**Codebase:** `/Users/seanfzc/projects/observeco` (src/observeco)  
**Scope:** Dashboard reads, DB schema, CLI, auth, pulse, chisel, tracking, proxy, config, tests

---

## Part 1: Data Continuity — Every Table the Dashboard Reads

The dashboard (`server.py`) opens a single `db = Database()` module-level instance. All reads go through the same SQLite `.pulse.db` file. The critical question: **who writes each table, and do they survive dashboard restarts?**

### Table: Dashboard Reads → Writer → Independence

| # | Table | Dashboard Reader(s) | Writer(s) | Process Independence | Staleness Risk |
|---|-------|---------------------|-----------|---------------------|----------------|
| 1 | `pulse_log` | `get_recent_pulses()`, `get_agent_status_summary()`, `get_phase()`, `get_instances()`, alert panels, agent detail, fleet summary | `db.log_pulse()` — called by `pulse/check.py` (CLI), `pulse/__init__.py` (daemon), `watch.py` (daemon) | **✅ INDEPENDENT** — watch daemon + pulse CLI write regardless of dashboard process | Low — daemon writes every 30s |
| 2 | `agent_configs` | `get_agents()`, agent detail, fleet comparison, brain API (hardcoded exclusion `WHERE agent_name NOT IN ('stdin','test-agent-ci')`) | `db.register_agent()` — called by `config.py` auto-discovery, CLI `agents add`, dashboard `/api/discover` | **⚠️ PARTIAL** — auto-discovery runs independently, but dashboard can also write | Low |
| 3 | `errors` | `get_errors()`, `get_errors_since()`, error timeline (§6.5), alert panels, agent detail tabs | `db.log_error()` — auto-called from `log_pulse()` on error/dead status, also webhook server, CLI | **✅ INDEPENDENT** — pulse checker writes on every cycle | Low |
| 4 | `circuit_breakers` | `get_circuit_breakers()`, alerts panel, fleet summary, agent detail guard tab | `db.record_failure()`, `db.reset_breaker()`, `db.set_threshold()`, auto-clear on read | **✅ INDEPENDENT** — pulse checker writes on failure detection | Low |
| 5 | `chisel_trims` | `get_trims()`, token detail tab (§6.3 Tokens), fleet compare, brain analysis | `db.log_trim()` — called by `chisel/trim.py` (CLI), `chisel/watch.py` (daemon) | **✅ INDEPENDENT** — Chisel CLI or daemon writes on compression events | Medium — written only on trim runs |
| 6 | `chisel_drift` | `get_drift()`, drift tabs, fleet summary (avg drift), brain analysis, alerts | `db.log_drift()` — called by `chisel/drift.py`, `chisel/watch.py` | **✅ INDEPENDENT** | Medium — written on each trim which may be infrequent |
| 7 | `clawforge_profiles` | `get_profiles()`, token detail (OpenClaw frame), garden tab | `db.log_profile()` — called by `clawforge/garden.py`, `clawforge/load.py` | **✅ INDEPENDENT** | Medium — only when ClawForge runs |
| 8 | `clawforge_garden` | `get_gardens()`, garden detail tab, fleet garden summary | `db.log_garden()` — called by `clawforge/garden.py` | **✅ INDEPENDENT** | Medium |
| 9 | `clawforge_loads` | `get_loads()`, token detail savings | `db.log_load()` — called by `clawforge/load.py` | **✅ INDEPENDENT** | Medium |
| 10 | `heal_config` | `get_heal_config()` (dashboard) | `db.set_heal_config()` — dashboard UI | **❌ COUPLED** — only dashboard writes | Low (UI-driven) |
| 11 | `heal_events` | `get_heal_events()` | `db.log_heal_event()` — called by `heal/` module | **✅ INDEPENDENT** | Medium — written on heal actions |
| 12 | **`token_logs`** | Dashboard token analytics, `/api/token-history/snapshot`, `/api/token-history` per-agent, brain analysis, trend charts | `db.log_token_turn()` — called by **5 independent sources**: proxy/server, otel_listener, tracking SDK patchers, watch.py, CLI | **✅ INDEPENDENT** — proxy server, OTel listener, SDK run as separate processes | Low — written on every LLM call captured |
| 13 | **`token_history`** | `/api/token-history` fleet-wide (90-day trend chart) | `POST /api/token-history/snapshot` — **a dashboard route only** | **❌ COUPLED (CRITICAL)** — No cron/scheduler exists. Snapshot only written when someone explicitly hits the POST endpoint or if the dashboard is running and a cron triggers it. In practice: **token_history stays empty after a fresh install** unless external cron is set up. | **🔴 HIGH** — no auto-writer |
| 14 | `compress_log` | `/api/watch-daemon-status`, brain analysis (fleet savings averages), `/api/brain` | `db.log_trim()` writes to `compress_log` (separate table) in `chisel/trim.py:300,543` and `chisel/watch.py:113` | **✅ INDEPENDENT** | Medium |
| 15 | `_meta` | `get_phase()`, `is_first_run()`, `get_no_llm()`, `get_discovery_candidates()` | Dashboard routes, set_phase() etc. | **❌ COUPLED** — dashboard lifecycle | Low |
| 16 | `feedback` | `get_feedback()`, `/v1/feedback` GET | `POST /v1/feedback` (dashboard route) | **❌ COUPLED** | Low |
| 17 | `restart_log` | `get_recent_restarts()`, `get_restart_summary()`, `get_agent_false_alarm_ratio()` | `db.log_restart()` — called by `pulse/check.py` | **✅ INDEPENDENT** | Medium — written on restarts only |
| 18 | `auth_sessions` | Auth middleware reads on every dashboard request | `db.save_session()`, `db.delete_session()`, `db.purge_expired_sessions()` — dashboard auth | **❌ COUPLED** — dashboard lifecycle | Low |
| 19 | `dead_letter_queue` | `dlq_get_pending()`, `dlq_stats()` | `db.dlq_add()`, `db.dlq_mark_*()` — event ingestion paths | **✅ INDEPENDENT** | Low |
| 20 | `telemetry_events` | `get_telemetry()` (dashboard/debug) | `db.save_telemetry()` — called by telemetry_client | **✅ INDEPENDENT** | Low |
| 21 | `pathway_nodes/edges` | `pathway_get_nodes/edges/graph()` | `pathway_add_node/edge()`, `pathway_scan()` (auto-detection) | **✅ INDEPENDENT** | Low |
| 22 | `action_log` | (not directly in dashboard reads scanned, but available) | Heal/chisel modules | **✅ INDEPENDENT** | Low |
| 23 | `self_monitor_budget` | `get_self_monitor_usage()` | `db.log_self_monitor()` from LLM service | **✅ INDEPENDENT** | Low |
| 24 | `agent_kill_log` | `get_kill_log()` | `db.log_kill()` | **✅ INDEPENDENT** | Low |

### 🔴 Critical Data Continuity Gaps

1. **token_history has no writer** (P0). The `POST /api/token-history/snapshot` route exists but needs a cron job to call it daily. The 90-day trend chart will show no data unless the user manually hits this endpoint or sets up a cron. This is the only dashboard-read table with a gap.

2. **Pulse file fallback** (`db.py:1249-1289`): When `pulse_log` is empty, `get_recent_pulses()` falls back to reading JSON files from `~/.hermes/state/pulses/` (via `DEFAULT_PULSE_DIRS`). This is a fallback, not a primary path, marked with a `ponytail:` comment that it should be configurable.

3. **`get_agent_status_summary()`** (db.py:2210-2236) uses a subquery (`WHERE id IN (SELECT MAX(id) FROM pulse_log GROUP BY agent_name)`) to get latest status per agent. Falls back to pulse files if DB empty. Pattern is sound but the subquery may not be optimal at scale.

---

## Part 2: Hardcoded Ecosystem Wiring

### Table: Hardcoded Reference → Impact → Fix Priority

| # | Reference | File(s):Line | Ecosystem-Specific? | Breaks for Non-Hermes User? | Confidence | Priority |
|---|-----------|-------------|---------------------|----------------------------|------------|----------|
| 1 | **`noreply@observeco.com`** default sender | `emails/sender.py:36` | ✅ Yes — ObserveCo domain | Email fails to send silently. Overridable via `OBSERVECO_EMAIL_FROM` but if unset, Resend will reject from unverified domain. | **High** | **P1** |
| 2 | **`support@observeco.com`** hardcoded | `billing.py:90,376,411,436` | ✅ Yes | User gets ObserveCo support address, not their own. Configurable? No env override. | **High** | **P1** |
| 3 | **`checkout@observeco.app`** fallback email | `dashboard/server.py:951` | ✅ Yes | When no email provided to checkout, it defaults to observeco.app domain. | **High** | **P1** |
| 4 | **`https://observeco.com/logo.png`** | `emails/templates.py:48` | ✅ Yes | Broken image in all email templates. No override. | **High** | **P1** |
| 5 | **`https://observeco.com/unsubscribe`** | `emails/templates.py:25` | ✅ Yes | Links go to observeco.com, not self-hosted instance. | **High** | **P1** |
| 6 | **`https://observeco.com/privacy`** | `emails/templates.py:64` | ✅ Yes | Same as above. | **High** | **P1** |
| 7 | **`https://observeco.com/support`** | `emails/templates.py:66` | ✅ Yes | Same as above. | **High** | **P1** |
| 8 | **`127.0.0.1:1234`** (BlueBubbles/iMessage) | `dashboard/server.py:2490` | ✅ Yes — ecosystem-specific platform | Random port scan that breaks silently if BlueBubbles not installed | **High** | **P2** |
| 9 | **`127.0.0.1:3000`** (WhatsApp bridge) | `dashboard/server.py:2504` | ✅ Yes | Same — ecosystem-specific | **High** | **P2** |
| 10 | **`127.0.0.1:8642`** (WhatsApp default) | `dashboard/server.py:2476`, `dashboard/config.py:214` | ✅ Yes | Overridable via `WHATSAPP_PORT`, but default is Hermes-ecosystem-specific | **Medium** | **P2** |
| 11 | **`127.0.0.1:9120`** (iMessage default) | `dashboard/server.py:2483`, `dashboard/config.py:215` | ✅ Yes | Overridable via `IMESSAGE_PORT` | **Medium** | **P2** |
| 12 | **`api.telegram.org/botINVALID/getMe`** | `dashboard/server.py:2497` | ❌ No (intentional — just checks DNS) | Uses fake token "INVALID" — only tests if Telegram API is reachable. Harmless. | **High** | **P3** |
| 13 | **`~/.hermes/` default path** | `config.py:32` | ✅ Yes — Hermes-ecosystem | Overridable via `OBSERVECO_HERMES_HOME`, but default assumes Hermes install | **High** | **P2** |
| 14 | **`~/.openclaw/workspace/` scan** | `config.py:111` | ✅ Yes — OpenClaw-ecosystem | Scans OpenClaw-specific path | **Medium** | **P2** |
| 15 | **`hermes-agent` → 'infrastructure'** | `db.py:438` (Migration 24) | ✅ Yes — hardcodes agent name | Running `hermes-agent` from outside Hermes ecosystem gets misclassified | **High** | **P1** |
| 16 | **`hermes-test%`, `test%`, `test2%` → 'test'** | `db.py:439` (Migration 24) | ✅ Yes | Wildcards assume certain naming conventions | **Medium** | **P2** |
| 17 | **Seeded config_format_registry paths** | `db.py:474-481` (Migration 26) | ✅ Yes — `~/.hermes/profiles/`, `~/.openclaw/workspace/` | Scans framework-specific config paths | **High** | **P2** |
| 18 | **Test fixture: `/home/user/.hermes/config.yaml`** | `tests/capability/test_env_snapshot.py:51,59` | ✅ Yes | Tests use Hermes-specific paths as hardcoded fixtures (unlikely to break user but shows ecosystem assumption) | **High** | **P2** |
| 19 | **`ai.hermes.`, `ai.openclaw.` launchd prefixes** | `config.py:222-223` | ✅ Yes — Hermes/OpenClaw daemon naming | launchd scanner only matches these prefixes | **Medium** | **P2** |
| 20 | **OpenClaw plugin sources** | `dashboard/config.py:192-197` | ✅ Yes — `~/.openclaw/plugins/*` | Hardcoded plugin paths for OpenClaw ecosystem | **Low** | **P2** |
| 21 | **`DEFAULT_UPSTREAM = "https://api.openai.com"`** | `proxy/server.py:38` | ❌ No (OpenAI is universal) | Standard default — not ecosystem-specific | **Low** | **P3** |
| 22 | **Unused `billing.json` default emails** | `billing.py:88,90` | ✅ Yes | Default fields contain ObserveCo-branded emails | **Medium** | **P1** |
| 23 | **Hardcoded provider pricing seeds** | `db.py:498-506` (Migration 27) | ❌ No (standard LLM pricing) | These are baseline rate cards — useful for any LLM user. Acceptable. | **High** | **P3** |
| 24 | **Hardcoded LLM provider registry URLs** | `db.py:525-540` (Migration 28) | ❌ No | These are standard provider API URLs (openai.com, anthropic.com, etc.) — universal. | **High** | **P3** |
| 25 | **`~/.hermes/cron/` fallback for pathway scan** | `db.py:2408` | ✅ Yes — Hermes-ecosystem cron directory | Fallback path for cron auto-discovery | **Low** | **P2** |
| 26 | **`~/.openclaw/cron/` fallback** | `db.py:2408` | ✅ Yes — OpenClaw-ecosystem | Same | **Low** | **P2** |
| 27 | **DeepSeek rates as yearly cost baseline** | `dashboard/server.py:1525,1583` | ❌ No (reasonable default) | "at $0.15/M tok, DeepSeek rates" is a display hint, not a hard constraint | **Medium** | **P3** |
| 28 | **`HERMES_PORT` default 1234** | `dashboard/config.py:216` | ✅ Yes — Hermes-specific gateway port | Overridable but defaults to Hermes Gateway port | **Medium** | **P2** |
| 29 | **Hardcoded `127.0.0.1` everywhere** | Various in dashboard/server.py | ❌ No (localhost is universal) | These are all local health-checks against localhost — correct for any installation | **High** | **P3** |
| 30 | **`ai.observeco.`, `com.observeco.`, `com.hermes.` launchd prefixes** | `config.py:222-223` | ✅ Yes | Second tier of launchd prefixes includes ObserveCo-specific services | **Low** | **P2** |
| 31 | **`observeco.com` domain in comments/docstrings** | Various | ✅ Yes | Cosmetic — no runtime impact | **Low** | **P3** |

---

## Part 3: Summary of Priority Findings

### P0 — Data Loss Risk
| ID | Finding | Detail |
|----|---------|--------|
| P0.1 | **token_history has no automatic writer** | `POST /api/token-history/snapshot` is a dashboard route only — no cron/scheduler triggers it. On fresh install, the 90-day trend chart will show empty data until someone sets up an external cron. All other tables have independent writers. |

### P1 — Breaks Outside Ecosystem
| ID | Finding | File |
|----|---------|------|
| P1.1 | `noreply@observeco.com` hardcoded default email sender | `emails/sender.py:36` |
| P1.2 | `support@observeco.com` hardcoded in billing templates | `billing.py:90,376,411,436` |
| P1.3 | `checkout@observeco.app` fallback in checkout | `dashboard/server.py:951` |
| P1.4 | `observeco.com` URLs in email template HTML | `emails/templates.py:25,48,64,66` |
| P1.5 | `hermes-agent` hardcoded as infrastructure type | `db.py:438` (Migration 24) |
| P1.6 | billing.json default emails (sender, support) | `billing.py:88,90` |

### P2 — Annoying But Not Breaking
| ID | Finding |
|----|---------|
| P2.1 | Hardcoded port scans: BlueBubbles:1234, WhatsApp:3000, WhatsApp:8642, iMessage:9120 |
| P2.2 | `~/.hermes/` default path assumption |
| P2.3 | Hermes/OpenClaw ecosystem hardcodes in config_format_registry migration |
| P2.4 | launchd prefixes `ai.hermes.`, `ai.openclaw.`, etc. |
| P2.5 | OpenClaw plugin paths in dashboard config |
| P2.6 | Test fixtures with `/home/user/.hermes/` paths |
| P2.7 | HERMES_PORT defaults to 1234 |
| P2.8 | agent_type classification with Hermes-specific name patterns |

### P3 — Cosmetic/Minor
| ID | Finding |
|----|---------|
| P3.1 | Provider pricing seeds (useful defaults) |
| P3.2 | LLM provider registry (industry-standard URLs) |
| P3.3 | DeepSeek "as default" rate hint in dashboard |
| P3.4 | `botINVALID` Telegram reachability check |
| P3.5 | Hardcoded localhost checks (correct for all users) |

---

## Part 4: Structural Observations

### Migration 24 agent classification (db.py:437-441)
The migration seeds `agent_configs.type = 'infrastructure'` for `hermes-agent` and `'test'` for agents matching `hermes-test%`, `test%`, or `test2%`. This runs at migration time (version 24), not on every startup, and only affects existing data at migration point. Agents registered after migration keep the default `'agent'` type. **Net impact**: an external user with an agent named "test-agent" would get it classified as 'test', which filters it out of fleet comparison views. The `hermes-agent` classification is harmless for non-Hermes users (no such agent exists).

### Pulse file fallback (db.py:1248-1289)
`DEFAULT_PULSE_DIRS = [hermes_home() / "state" / "pulses"]` — this path is Hermes-specific. If `pulse_log` is empty (e.g., using only Hermes pulse files), the fallback reader reads from a Hermes-specific directory. This is marked with a `ponytail:` comment as "configurable via observeco.yml in future." Acceptable for now but ecosystem-specific.

### `/api/platforms` endpoint (server.py:2467-2553)
Probes 5 local services on hardcoded ports. Gracefully handles failures (catches exceptions, marks as "down"), so no crash. But the UX shows fake status for services the user never had. This is cosmetic, not crashing.

### CLI explore detection (config.py:58-157)
The auto-discovery system assumes Hermes and OpenClaw frameworks exist. It scans `~/.hermes/profiles/`, `~/.hermes/agents/`, `~/.openclaw/workspace/`. For a non-Hermes/non-OpenClaw user, all scans return empty (paths don't exist), so the fallback to `agents.json` and `observeco.yml` works. No crash, but loud ecosystem assumption in default config paths.

---

## Methodology

- **Data continuity**: Every `SELECT ... FROM <table>` in `dashboard/server.py` and `db.py` reader methods was traced to its corresponding `INSERT`/`UPDATE`/`DELETE` in the same file and across the codebase.
- **Hardcoded references**: Grep-based search for domain names, API URLs, port numbers, Hermes/OpenClaw/keywords, file paths, env vars, and Telegram IDs across all target directories.
- **Confidence**: "High" = code confirmed at exact path. "Medium" = pattern strongly implied but path confirmed. "Low" = inferred from broader context.