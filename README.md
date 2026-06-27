# ObserveCo

> ObserveCo tells you if your AI agents are working, what they're doing, and where your money goes.

```bash
pip install 'observeco[dashboard]' && observeco dashboard
```

> **v0.3.1 — Hermes plugin (beta) — PR in review.** 18 features. 610 tests. Built and dogfooded on a 7-agent fleet running on a single M4 Mac Mini.

<p align="center">
  <img src="docs/assets/dashboard-screenshot.png" alt="ObserveCo Dashboard" width="720">
  <br><em>Fleet view with health dots, token bars, drift sparklines, and error timeline. One pip install.</em>
</p>

<div align="center">

[![MIT License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue)](pyproject.toml)
[![CI](https://github.com/observeco/observeco/actions/workflows/ci.yml/badge.svg)](https://github.com/observeco/observeco/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/observeco)](https://pypi.org/project/observeco/)
[![GitHub stars](https://img.shields.io/github/stars/observeco/observeco?style=social)](https://github.com/observeco/observeco)

</div>

---

## 🛠️ Hermes Integration

ObserveCo includes a **beta plugin for Hermes Agent** that exports real-time telemetry from every agent conversation — no sidecars, no proxies, no manual instrumentation.

**What the plugin exports (11 hooks):**

| Hook | Data |
|------|------|
| `post_api_request` | Token usage (input, output, cache, cost, model, provider) |
| `api_request_error` | LLM failures with error message |
| `on_session_start` / `on_session_end` | Session lifecycle |
| `pre_tool_call` / `post_tool_call` | Tool invocation + result summary |
| `subagent_start` / `subagent_stop` | Child agent spawn + completion |
| `pre_gateway_dispatch` | Incoming message routing |

**Quick start for Hermes users:**

```bash
# 1. Enable the plugin
hermes plugins enable observability/observeco

# 2. Set the endpoint
echo 'HERMES_OBSERVECO_ENDPOINT=http://127.0.0.1:4318' >> ~/.hermes/.env

# 3. Restart the gateway
launchctl kickstart -k gui/$(id -u)/ai.hermes.gateway

# 4. Start the OTEL listener & dashboard
observeco otel listen start --port 4318
observeco dashboard
```

The plugin is currently under review upstream via [PR #52357](https://github.com/NousResearch/hermes-agent/pull/52357). Full integration guide at [`docs/hermes-plugin-integration.md`](docs/hermes-plugin-integration.md).

---

## The Problem

Every AI agent operator has this story: an agent was silently failing for weeks. Context bloating 15% per week. Memory full of duplicates and contradictions. Nobody noticed until a user complained.

This is normal. The tools to fix it don't exist — yet.

---

## Service Architecture

ObserveCo runs as a service with health monitoring and auto-recovery.

### Start / Stop / Restart

```bash
# Start the service
observeco service start

# Check status
observeco service status

# Stop the service
observeco service stop

# Restart the service
observeco service restart
```

### Components

| Component | Port | Purpose |
|-----------|------|---------|
| OTEL Listener | 4318 | Receives traces from agents |
| Dashboard | 8787 | Web UI for visualization |

### Health Monitoring

ObserveCo monitors two levels of health:

**Level 1: Operational** (runs every 30s)
- OTEL listener responding
- Dashboard responding
- Database writable
- Ports available

**Level 2: Functional** (runs every 60s)
- Data flowing (recent events)
- Schema current
- Disk usage <80%
- Resources healthy (CPU, memory)

### Auto-Recovery

Failed components are automatically restarted:
- Max 3 restart attempts in 5 minutes
- Port conflicts resolved by killing old processes
- Database locks retried with backoff

### Updates

Check for updates on dashboard load:
- "Update available: v0.3.0 (you have v0.2.0)"
- Click "Update now" to upgrade
- Service restarts automatically

---

## From the Trenches (Dogfood)

> We run 7 autonomous agents on an M4 Mac Mini — Hermes, Kepler, Hound, Dreamer, Aleph, PA, and an orchestrator. They talk via ACPS signals, trigger on file changes, get scheduled via cron. For months we ran `ps aux | grep python` and hoped for the best.

> **Then we built ObserveCo.** It caught Hermes' SOUL.md growing 15% week-over-week. It showed Kepler's context carrying 40k tokens of memory it never used. It exposed 3 silent circuit trips in 2 days that nobody saw. These are not edge cases — they're the normal state of any agent fleet older than a week.

---

## What Ships Now (v0.3.1)

18 features. One `pip install`. 60 seconds to first health data.

### Fleet Health
| Feature | What it does |
|---------|-------------|
| **Pulse Check** | Agent liveness — alive / dead / error. Auto-detects from config. |
| **Circuit Breaker** | N-failure trip → auto-block → cooldown. Stops cascade failures. |
| **Heal Button** | One-click restart for dead agents. Manual trigger, you're in control. |
| **Auto-Heal** | Per-agent toggle, L2 thresholds. Watch daemon auto-restarts dead agents. |
| **Push Alerts** | Telegram, Discord, and email alerts when agents break. Delivery log, test button. |

### Token Intelligence
| Feature | What it does |
|---------|-------------|
| **Token Breakdown** | Per-component token breakdown (identity, skills, memory, tools, guidance) |
| **Drift Tracking** | 7-day rolling token drift trend per component per agent |
| **Token Analytics** | Chart.js time-series dashboard with cost estimation and cache efficiency |
| **Brain Analysis** | Find bloated, duplicate, or unused skills. Compression preview with per-skill actions. |

### Memory & Context
| Feature | What it does |
|---------|-------------|
| **Memory Garden** | Find duplicates, contradictions, stale entries in agent memory |
| **Fleet Comparison** | Side-by-side agent matrix — tokens, composition, drift, errors, circuit status |

### Dashboard & Alerts
| Feature | What it does |
|---------|-------------|
| **Fleet View** | All agents at a glance — green/yellow/red status cards |
| **In-Dashboard Alerts** | See alerts when you open the dashboard. Shows discovery gap. |
| **Error Timeline** | Full error history with context snapshots |
| **Glossary** | 20+ entries with hint buttons across all tabs |
| **Confidence Framework** | FP/FN risk badges on every card |

### Pro Features
| Feature | What it does |
|---------|-------------|
| **Pro License** | Generate & revoke admin keys, self-serve billing via Stripe |
| **Drift Alerts UI** | Configure drift thresholds from the dashboard |
| **Circuit Breaker Config** | Turn-rate alerting, budget cap, manual kill switch |

---

## Quick Start

```bash
pip install 'observeco[dashboard]'

# Check your agent fleet
observeco pulse check

# See what's eating your context
echo "Your system prompt" | observeco chisel trim

# Find memory bloat
observeco clawforge garden

# Launch the dashboard
observeco dashboard
```

---

<!-- Pro removed — all features free for now. See .internal/specs/commercial-scope.md -->

## The Discovery Gap

Every yellow banner in the dashboard shows two timestamps:

> ⚠️ **Kepler** — heartbeat missed
> Happened: 03:15 · Discovered: 07:00 · **Gap: 3h 45m**

That gap is where agents fail silently. ObserveCo makes it visible.

In v0, you see the gap when you open the dashboard. In v0.3 (D+7), push alerts close it — Telegram notifications fire within 3 seconds of detection.

---

## Why ObserveCo?

| Instead of... | ObserveCo |
|---------------|-----------|
| **Datadog** ($15+/host/mo, cloud-only) | `pip install`, local-first, free, understands tokens + memory debt + circuit breakers |
| **Grafana + Prometheus** (2-hour setup, no context concept) | 60 seconds to first health data, agent-aware dashboards |
| **LangSmith** (LangChain-only, $59/mo) | Framework-agnostic, open source, works offline |
| **Nothing** (failing silently) | You'll know when your agents are sick, bloated, or broken |

---

## The Stack

```
pip install observeco
├── pulse        — liveness, circuit breaker, safety guard
├── chisel       — token compression, drift, skill audit
├── clawforge    — memory garden, context profiler, intent loader
└── dashboard    — local web UI (FastAPI + htmx, no npm)
```

- **Storage:** Local SQLite (`~/.observeco/pulse.db`) — zero setup
- **Web server:** FastAPI + htmx — no build step, ships with CLI
- **CLI:** Typer — shell completion, rich output
- **Telemetry:** Opt-in crash/usage reports. Set `OBSERVECO_TELEMETRY=on` to help improve ObserveCo. No data collected by default.

---

## Roadmap

| Version | Status | What |
|---------|--------|------|
| **v0.2** | ✅ Shipped | Token Analytics + Data Infrastructure |
| **v0.3** | ✅ Shipped | Auto-heal, Push Alerts, Pro Licensing, Fleet Comparison, Hermes Plugin |
| **v0.3.1** | 🔥 Now | Hermes Agent Observability Plugin — 11 hooks, PR #52357 (in review) |
| **v0.4** | 🔜 Branch active | **ClawForge OpenClaw plugin** — ContextEngine, intent classifier, stats pipeline |
| **v0.5** | 📋 Planned | Making the Theatre Real — real risk predictions, context bloat detection, L2 heal |
| **v0.6** | 📋 Planned | Beachhead — public release readiness, `observeco init`, generic discovery |
| **v1.0** | 📋 Planned | Per-turn tracking, OTel trace ingestion, trace tree dashboard |

**What's the ClawForge plugin?** A Node.js plugin that hooks into the ContextEngine to load only what's needed per turn. Your agents stop carrying 100k tokens of context they never use. Already built in v0.4 — install via `observeco clawforge plugin install`.

---

## Supported Frameworks

| Framework | Health | Circuit | Tokens | Memory | Dashboard | Hermes Plugin |
|-----------|:------:|:-------:|:------:|:------:|:---------:|:-------------:|
| **Hermes** | ✅ Auto | ✅ | ✅ | ✅ | ✅ Full | ✅ PR in review (11 hooks) |
| **OpenClaw** | ✅ | ◐ | ◐ | ✅ | ✅ ~85% | ⬜ |
| **Ollama** | ✅ | ⬜ | ⬜ | ⬜ | ✅ Basic | ⬜ |
| **Custom** | ◐ | ◐ | ◐ | ⬜ | ✅ Basic | ⬜ |

✅ = Auto-detect & works · ◐ = Works with config · ⬜ = Coming

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). First-time contributors welcome — look for "good first issue" labels.

---

Built with ❤️ for the AI agent community. MIT licensed.

### Glossary

Hover the "?" icons on any agent card in the dashboard to get instant definitions of:
- **Health** (status dot) — green/yellow/red lifecycle
- **Guard** (circuit breaker) — N-failure auto-stop
- **Errors** — per-agent error badge (24h window)
- **Brain size** (drift) — 7-day token growth trend
- **Composition** (token bar) — identity/skills/memory/tools/guidance breakdown

Each popup includes FAQ. Click the topic header to open the full modal.

---

### 🔐 Observability Boundaries (Threat Model)

ObserveCo monitors **agent processes, health, token usage, and inter-agent communication paths**. It does **not** monitor:

- **API key compromise** — ObserveCo sees which provider you use but never stores API keys. Key hygiene is your responsibility.
- **Prompt injection / data poisoning** — ObserveCo monitors agent health, not conversation content. A poisoned agent that behaves normally will not trigger alerts.
- **Network-level attacks** — We monitor platform connectivity (Telegram/WhatsApp/Discord gateway health) but not TLS termination, DNS, or DDoS.
- **Supply chain attacks** — Plugin dependencies are your risk. ObserveCo can detect bloated skills but not malicious ones.
- **Storage encryption** — All data is local SQLite on your machine. Encrypt your disk; we don't add a separate encryption layer.

**What a kill switch can do:** Stop a runaway agent process immediately (SIGTERM → SIGKILL after 5s). Audit-logged. Human-initiated only.
**What a kill switch cannot do:** Prevent the agent from restarting (auto-restart daemons will re-launch unless you also remove the agent config).
**What auto-heal does:** Restart dead agents, reset tripped circuits, trim bloated memory. Configurable thresholds. Circuit breaker stops after 3 failures.
**What auto-heal does NOT do:** Modify config files, delete agents, change system settings, or execute any action with irreversible side effects.