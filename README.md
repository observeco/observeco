# ObserveCo

> **ObserveCo is now a differentiation-strategy consultancy for Singapore small businesses.** We study your real competitive set and hand you the one differentiator most likely to win for your market — in days, at a fraction of a big firm's cost. → **[observeco.com](https://observeco.com)**

> This repository is the open-source **agent-observability tool** that ObserveCo builds and runs on itself — proof of the AI-native capability behind the consultancy. It tells you if your AI agents are working, what they're doing, where your money goes — and whether they're getting worse.

```bash
pip install 'observeco[dashboard]' && observeco dashboard
```

> **v0.5.0 — Capability Monitoring Layer.** Passive monitoring (always-on, zero tokens) + active probing (deliberate, user-controlled cost). Config-aware baselines. Open adapter spec. MIT licensed.

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

## 🔌 Native Hermes Agent Integration

ObserveCo ships a **native Hermes plugin** that exports real-time telemetry from every agent conversation — no sidecars, no proxies, no manual instrumentation.

**What the plugin exports (11 hooks):**

| Hook | Data |
|------|------|
| `post_api_request` | Token usage (input, output, cache, cost, model, provider) |
| `api_request_error` | LLM failures with error message |
| `on_session_start` / `on_session_end` | Session lifecycle |
| `pre_tool_call` / `post_tool_call` | Tool invocation + result summary |
| `subagent_start` / `subagent_stop` | Child agent spawn + completion |
| `pre_gateway_dispatch` | Incoming message routing |

**Quick start for Hermes users on macOS:**

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

The plugin is bundled with Hermes Agent and contributed upstream via [PR #52357](https://github.com/NousResearch/hermes-agent/pull/52357). Full integration guide at [`docs/hermes-plugin-integration.md`](docs/hermes-plugin-integration.md).

---

## The Problem

Every AI agent operator has this story: an agent was silently failing for weeks. Context bloating 15% per week. Memory full of duplicates and contradictions. Nobody noticed until a user complained.

Worse: **you don't know if your agent is getting worse.** Generic benchmarks (MMLU, τ-bench) don't predict real performance. The only valid benchmark is: "Can my agent do the tasks I actually need it to do?"

This is the gap ObserveCo fills.

---

## Two-Mode Monitoring

Observation without judgment is just logging. ObserveCo adds the judgment layer — two modes, different purposes.

### Mode 1 — Passive Monitoring (always-on, zero extra tokens)

Analyzes live production traffic locally. Coarse but continuous — catches "something changed" without spending anything.

- Task success heuristics
- Tool-call error rates
- Loop detection
- Latency and token consumption
- Cost tracking

**This is what ObserveCo already does.** The free, always-on layer. Extends the existing observability infrastructure.

### Mode 2 — Active Probing (deliberate, user-controlled cost)

Scheduled benchmark runs of user-defined tasks against your agent. Cost is surfaced, never hidden — the UI shows estimated tokens/$ per probe schedule before enabling.

- **Canary** — regression tripwire. 9 tasks, cheap, fast, frequent. Detects degradation, not capability.
- **Grid** — capability measurement. Model × harness config × task matrix. Per-task accuracy with confidence intervals, cost, trajectory logs. Read by pairing, never averaged.

**Default schedules are conservative.** 10 tasks × 3 runs/day ≈ 1-2.5M tokens/day. User controls frequency (nightly, weekly, on-demand, on-config-change).

---

## Config-Aware Baselines (The Moat)

Personal agent stacks are file-based (SOUL.md, prompt files, tool manifests, MCP configs). Cloud tools can't see local config changes. ObserveCo can.

- Hash and watch config files
- On change: snapshot and segment the baseline automatically
- The killer output: **"Your agent's success rate dropped 18% this week. Your config is unchanged."** — separating provider-side model drift from self-inflicted changes.

---

## Adapter Strategy

Adapters are a permanent maintenance treadmill — every framework changes quarterly.

**Approach:** Ship one adapter we use daily ourselves (Hermes), publish a clean, documented adapter spec, and let the community build the rest. Community adapters are the only sustainable path to "any-agent support" for an OSS project.

---

## Statistical Honesty

3-10 non-deterministic tasks produce noisy signals. Naive thresholds → false drift alarms → lost trust → churn.

- Each checkpoint runs each task N times (user-configurable, default small but >1)
- Drift alerts fire only after a sequential/statistical test clears, not on a single bad run
- Alerts always report confidence and sample size
- **Under-claim rather than over-claim.** Credibility is the moat.

---

## Research-Validated Thesis

ObserveCo's core hypothesis — that harness quality is a separate axis from model capability — is independently validated by [Hugging Face's harness-optimization experiment](https://huggingface.co/spaces/joelniklaus/harness-optimization) (Niklaus, July 2026):

> A frozen DeepSeek-V4-Pro scoring **0%** on Harvey's Legal Agent Benchmark was left untouched while an automated loop rewrote only the **harness** (runtime wrapper). Result: **0% → 5.0%** whole-task success, **63.4% → 80.1%** criterion pass rate — landing between Sonnet 4.6 and Opus 4.6.

Same model, different harnesses: **3.5% to 80.1%** range. This is exactly what ObserveCo's grid runner measures. Key findings that shaped ObserveCo's capability monitoring:

| Finding | ObserveCo Application |
|---------|----------------------|
| Code fixes (+16pts) > prompt engineering | Grid tags mechanisms as code vs prompt |
| Robustness transfers cross-model; prompts don't | Dev/test split prevents overfitting to eval set |
| Provider failures contaminate scores | Adapter retries transient 5xx/429 errors |
| Per-trial variance from blowups, not noise | Canary flags catastrophic trials as signal |
| Blended score: `accuracy + 0.5×all_pass − 0.005×tokens/1M` | Grid report uses configurable blended score |

**Source:** [Niklaus, "Don't Train the Model, Evolve the Harness," Hugging Face, 2026](https://huggingface.co/spaces/joelniklaus/harness-optimization) · [Code](https://github.com/JoelNiklaus/harness-optimization) · [Meta-Harness paper](https://arxiv.org/abs/2603.28052)

---

## Service Architecture

ObserveCo runs as a service with health monitoring and auto-recovery.

### Quick Start

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
| OTEL Listener | 4318 | Receives traces from Hermes agents |
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
- "Update available: v0.5.0 (you have v0.4.0)"
- Click "Update now" to upgrade
- Service restarts automatically

---

## From the Trenches (Dogfood)

> We run 7 autonomous Hermes agents on an M4 Mac Mini — Kepler, Hound, Dreamer, Aleph, PA, and an orchestrator. They talk via ACPS signals, trigger on file changes, get scheduled via cron. For months we ran `ps aux | grep python` and hoped for the best.

> **Then we built ObserveCo.** It caught Hermes' SOUL.md growing 15% week-over-week. It showed Kepler's context carrying 40k tokens of memory it never used. It exposed 3 silent circuit trips in 2 days that nobody saw. These are not edge cases — they're the normal state of any agent fleet older than a week.

> **Now we run the canary daily.** 9 tasks, 2 minutes, ~$0.002. When the score drops and config is unchanged, we know the provider drifted. When config changes, we know the baseline needs updating. This is the loop.

---

## What Ships Now (v0.5.0)

18+ features. One `pip install`. 60 seconds to first health data.

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

### Capability Monitoring (v0.5.0 — new)
| Feature | What it does |
|---------|-------------|
| **Canary** | Regression tripwire — 9 tasks, cheap, fast, frequent. Detects degradation. |
| **Grid** | Capability measurement — model × harness config × task matrix. Per-task CI, cost, trajectory. |
| **Config Hashing** | Watch config files (SOUL.md, prompts, tool manifests). Auto-segment baselines on change. |
| **Drift Detection** | Statistical honesty layer — alerts fire only after sequential/statistical test clears. |
| **Shareable Drift Charts** | "Config unchanged, quality dropped X%" — viral output for the "did they nerf the model?" discourse. |

### Dashboard & Alerts
| Feature | What it does |
|---------|-------------|
| **Fleet View** | All agents at a glance — green/yellow/red status cards |
| **In-Dashboard Alerts** | See alerts when you open the dashboard. Shows discovery gap. |
| **Error Timeline** | Full error history with context snapshots |
| **Glossary** | 20+ entries with hint buttons across all tabs |
| **Confidence Framework** | FP/FN risk badges on every card |

### Hermes Observability (v0.4.0)
| Feature | What it does |
|---------|-------------|
| **Tracing Layer** | Full span tree per session — root → subagent → tool calls. Waterfall view. |
| **Evaluation Layer** | Quality score, tool efficiency, retry/hallucination flags per turn. Quality trends. |
| **Behavioral Monitoring** | Anomaly detection (no_tools, high_cost, retry_loops). Context Health Score. |
| **Unified Agent Data Model** | Single `/api/agent/{id}/profile` endpoint — health, tokens, traces, evals, anomalies. |

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

# Run a canary check
observeco benchmark run --suite canary --agent hermes-main

# Launch the dashboard
observeco dashboard
```

---

## The Discovery Gap

Every yellow banner in the dashboard shows two timestamps:

> ⚠️ **Kepler** — heartbeat missed
> Happened: 03:15 · Discovered: 07:00 · **Gap: 3h 45m**

That gap is where agents fail silently. ObserveCo makes it visible.

---

## Why ObserveCo?

| Instead of... | ObserveCo |
|---------------|-----------|
| **Datadog** ($15+/host/mo, cloud-only) | `pip install`, local-first, free, understands tokens + memory debt + circuit breakers |
| **Grafana + Prometheus** (2-hour setup, no context concept) | 60 seconds to first health data, agent-aware dashboards |
| **LangSmith** (LangChain-only, $59/mo) | Hermes-native, open source, works offline |
| **Arize / Braintrust** (cloud-only, team-oriented, $50+/mo) | Local-first, individual/small-operator focused, drift monitoring without shipping traces |
| **Nothing** (failing silently) | You'll know when your agents are sick, bloated, broken, or drifting |

---

## The Stack

```
pip install observeco
├── pulse        — liveness, circuit breaker, safety guard
├── chisel       — token compression, drift, skill audit
├── clawforge    — memory garden, context profiler, intent loader
├── benchmark    — canary + grid, config-aware baselines, drift detection
└── dashboard    — local web UI (FastAPI + htmx, no npm)
```

- **Storage:** Local SQLite (`~/.observeco/pulse.db`) — zero setup
- **Web server:** FastAPI + htmx — no build step, ships with CLI
- **CLI:** Typer — shell completion, rich output
- **Telemetry:** Optional crash/usage reports to help improve ObserveCo. Opt-out via `OBSERVECO_TELEMETRY=off`. No data collected otherwise.

---

## Roadmap

| Version | Status | What |
|---------|--------|------|
| **v0.2** | ✅ Shipped | Token Analytics + Data Infrastructure |
| **v0.3** | ✅ Shipped | Auto-heal, Push Alerts, Pro Licensing, Fleet Comparison, Hermes Plugin |
| **v0.3.1** | ✅ Shipped | Official Hermes Agent Observability Plugin — 11 hooks, bundled upstream |
| **v0.4.0** | ✅ Shipped | **Hermes Beachhead** — Tracing Layer, Evaluation Layer, Behavioral Monitoring, Unified Data Model |
| **v0.5.0** | 🔥 Now | **Capability Monitoring Layer** — Canary + Grid, config-aware baselines, drift detection, adapter spec |
| **v0.6.0** | 📋 Planned | Log-to-suggested-tasks (auto-generation with review/approve), opt-in LLM-as-judge scoring, alert integrations |
| **v1.0** | 📋 Planned | Public release readiness, `observeco init`, generic discovery |
| **Future** | 📋 Planned | Fleet features, paid tiers, write-task sandboxing research, comparison engine (only at credible scale) |

---

## Supported Frameworks

| Framework | Health | Circuit | Tokens | Memory | Dashboard | Hermes Plugin | Canary | Grid |
|-----------|:------:|:-------:|:------:|:------:|:---------:|:-------------:|:------:|:----:|
| **Hermes** | ✅ Auto | ✅ | ✅ | ✅ | ✅ Full | ✅ Native (11 hooks) | ✅ | ✅ |
| **OpenClaw** | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ (deferred) | ⬜ | ⬜ |
| **Ollama** | ✅ | ⬜ | ⬜ | ⬜ | ✅ Basic | ⬜ | ⬜ | ⬜ |
| **Custom** | ◐ | ◐ | ◐ | ⬜ | ✅ Basic | ⬜ | ⬜ | ⬜ |

✅ = Auto-detect & works · ◐ = Works with config · ⬜ = Deferred (post-v1.0)

**Adapter strategy:** Ship one adapter (Hermes), publish a clean adapter spec, let the community build the rest. Community adapters are the only sustainable path to "any-agent support" for an OSS project.

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
- **Canary** — regression tripwire. 9 tasks, cheap, fast. Detects degradation.
- **Grid** — capability measurement. Model × harness config × task matrix. Per-task CI, cost, trajectory.

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
