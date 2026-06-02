# ObserveCo

> ObserveCo tells you if your AI agents are working, what they're doing, and where your money goes.

```bash
pip install 'observeco[dashboard]' && observeco dashboard
```

<div align="center">

[![MIT License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue)](pyproject.toml)
[![CI](https://github.com/observeco/observeco/actions/workflows/ci.yml/badge.svg)](https://github.com/observeco/observeco/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/observeco)](https://pypi.org/project/observeco/)
[![GitHub stars](https://img.shields.io/github/stars/observeco/observeco?style=social)](https://github.com/observeco/observeco)

</div>

---

## The Problem

Every AI agent operator has this story: an agent was silently failing for weeks. Context bloating 15% per week. Memory full of duplicates and contradictions. Nobody noticed until a user complained.

This is normal. The tools to fix it don't exist — yet.

---

## What Ships Now (v0.1)

12 features. One `pip install`. 60 seconds to first health data.

### Fleet Health
| Feature | Command | What it does |
|---------|---------|-------------|
| **Pulse Check** | `observeco pulse check` | Agent liveness — alive / dead / error. Auto-detects from config. |
| **Circuit Breaker** | `observeco pulse circuit` | N-failure trip → auto-block → cooldown. Stops cascade failures. |
| **Safety Guard** | built-in | Noise reduction — only surfaces real issues, not flapping |
| **Heal Button** | dashboard | One-click restart for dead agents. Manual trigger, you're in control. |

### Token Intelligence
| Feature | Command | What it does |
|---------|---------|-------------|
| **Context Trim** | `observeco context trim` (or `observeco chisel trim`) | System prompt compression with per-component token breakdown |
| **Drift Tracking** | `observeco context drift` (or `observeco chisel drift`) | 7-day rolling token drift trend per component per agent |
| **Skill Audit** | `observeco context skills` (or `observeco chisel skills`) | Find bloated, duplicate, or unused skills eating context |

### Memory & Context
| Feature | Command | What it does |
|---------|---------|-------------|
| **Memory Garden** | `observeco memory garden` (or `observeco clawforge garden`) | Find duplicates, contradictions, stale entries in agent memory |
| **Context Profiler** | `observeco context profile` (or `observeco clawforge profile`) | See what's in your agent's context — MEMORY.md, skills, workspace |
| **Intent Classifier** | `observeco context load` (or `observeco clawforge load`) | Dry-run which sources would load per message type |

### Dashboard & Alerts
| Feature | Access | What it does |
|---------|--------|-------------|
| **Fleet View** | `observeco dashboard` | All agents at a glance — green/yellow/red status cards |
| **In-Dashboard Alerts** | free | See alerts when you open the dashboard. Shows discovery gap ("happened 3am, found 7am") |
| **Error Timeline** | free | Full error history with context snapshots |
| **Push Alerts** | v0.3 (D+7) | Telegram / webhook / email — know before you check |

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
- **Telemetry:** Optional crash/usage reports to help improve ObserveCo. Opt-out via `OBSERVECO_TELEMETRY=off`. No data collected otherwise.

---

## Roadmap

| Version | Timing | What |
|---------|--------|------|
| **v0.1** | Now | 12 features — monitoring + diagnostics + dashboard |
| **v0.2** | D+3 | Auto-heal (93% coverage) + Extended history |
| **v0.3** | D+7 | Chisel compression + Push alerts (Telegram/webhook/email) |
| **v1.1** | D+14 | OpenClaw runtime plugin (`@observeco/clawforge-plugin`) |

**What's the OpenClaw plugin?** A Node.js plugin that hooks into the ContextEngine to load only what's needed per turn. Your agents stop carrying 100k tokens of context they never use. That's the v1.1 headline.

---

## Supported Frameworks

| Framework | Health | Circuit | Tokens | Memory | Dashboard |
|-----------|:------:|:-------:|:------:|:------:|:---------:|
| **Hermes** | ✅ Auto | ✅ | ✅ | ✅ | ✅ Full |
| **OpenClaw** | ✅ | ◐ | ◐ | ✅ | ✅ ~85% |
| **Ollama** | ✅ | ⬜ | ⬜ | ⬜ | ✅ Basic |
| **LangChain** | ◐ | ◐ | ⬜ | ⬜ | ✅ Basic |
| **CrewAI** | ◐ | ⬜ | ⬜ | ⬜ | ✅ Basic |
| **Custom** | ◐ | ◐ | ◐ | ⬜ | ✅ Basic |

✅ = Auto-detect & works · ◐ = Works with config · ⬜ = Coming

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). First-time contributors welcome — look for "good first issue" labels.

---

Built with ❤️ for the AI agent community. MIT licensed.
