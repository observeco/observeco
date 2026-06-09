# User Profile → Feature Map

> **What ObserveCo is maximally good for, and for whom.**
>
> ObserveCo is a **runtime observability platform for AI agents** — not a framework, not an orchestrator. It watches running agents (Hermes, OpenClaw, Ollama, custom), detects problems before they compound, and surfaces what your agent ecosystem is actually doing — regardless of how many frameworks you're running.

---

## By Agent Framework

### You run **Hermes** agents (SOUL.md in `~/.hermes/profiles/` or `~/.hermes/agents/`)

| You get | You don't get |
|---------|---------------|
| ✅ Full auto-discovery — finds every SOUL.md agent automatically | ❌ Native agent-to-agent communication |
| ✅ Token compression (chisel trim/drift/skills) for SOUL.md and skill bloat | ❌ Task scheduling |
| ✅ L2 trends — memory bloat, stuck conversations, drift, upstream failure detection | |
| ✅ Watch daemon (pulse every 30s, drift every 5min, garden every 15min) | |
| ✅ Dashboard showing all agents with config path | |
| ✅ Heal (auto-diagnose + auto-fix for common Hermes failures) | |

**Best experience on ObserveCo.** Every feature works for you out of the box.

---

### You run **OpenClaw** agents (in `~/.openclaw/workspace/`)

| You get | You don't get |
|---------|---------------|
| ✅ Full auto-discovery — finds every SOUL.md in the OpenClaw workspace | ❌ Token compression (OpenClaw uses plugin-based SOP) |
| ✅ Context profiling (clawforge profile) — per-agent context window breakdown | ❌ Chisel config scanner (Hermes-specific) |
| ✅ Intent-aware context loading (clawforge load) | |
| ✅ MEMORY.md hygiene (clawforge garden) | |
| ✅ Plugin tracking — bootstrap/ingest/pre-response hook points logged to DB | |
| ✅ L2 trends, pulse, heal | |

**Full first-class support.** OpenClaw-specific features mirror Hermes in scope.

---

### You run **Ollama** models (port 11434)

| You get | You don't get |
|---------|---------------|
| ✅ Auto-discovery from running processes | ❌ Token compression |
| ✅ Pulse check (alive/dead per model) | ❌ Context profiling |
| ✅ Circuit breaker (trip after N failures) | ❌ Plugin tracking |
| ✅ Dashboard visibility | ❌ Heal (no agent lifecycle to manage) |
| ✅ L2 trend scanning | |

**You get monitoring, not management.** ObserveCo watches Ollama models and tells you when they crash, but cannot optimise them.

---

### You run **custom agents** (CrewAI, LangChain, AutoGen, custom Python, Node.js bot — registered manually)

| You get | You don't get |
|---------|---------------|
| ✅ Pulse check (if health_check URL is configured) | ❌ Auto-discovery (must add manually via `observeco agents add <name>`) |
| ✅ Circuit breaker | ❌ Context profiling |
| ✅ Dashboard | ❌ Token compression |
| ✅ Webhook ingestion (if your agent emits OEF-format webhooks) | ❌ All framework-specific features |
| ✅ L2 trends | |
| ✅ Heal (best-effort — restart on death) | |
| ✅ Alerts (Telegram/webhook/email) | |

**Functional but add-only.** You register manually and get the monitoring surface, but nothing framework-specific.

---

### You run **no agents at all** (just curious)

| You get | You don't get |
|---------|---------------|
| ✅ `observeco agents discover` shows what's running on your machine | ❌ Everything that needs an agent |
| ✅ LLM-powered discovery scans `ps aux` / `lsof -i` for anything that looks like an agent process | |
| ✅ Dashboard provides a live view of your machine's process landscape | |

**You're browsing.** ObserveCo finds nothing and tells you clearly what to do next.

---

## By Operating System

### You're on **macOS**

| Feature | Status |
|---------|:------:|
| CLI (all commands) | ✅ Full |
| Auto-discovery (config dirs) | ✅ `~/.hermes/`, `~/.openclaw/`, `~/.ollama/` |
| Auto-discovery (LLM scan) | ✅ `ps aux` + `lsof -i` |
| Watch daemon | ✅ launchd-based |
| Desktop app (pywebview) | ✅ Native Cocoa window + system tray |
| Heal (agent recovery) | ✅ Full |
| Chisel daemon | ✅ launchd-compatible |

**Primary target.** Full feature coverage.

---

### You're on **Linux**

| Feature | Status |
|---------|:------:|
| CLI (all commands) | ✅ Full |
| Auto-discovery (config dirs) | ✅ Same paths |
| Auto-discovery (LLM scan) | ✅ `ps aux` + `lsof -i` |
| Watch daemon | ✅ systemd / supervisord |
| Desktop app (pywebview) | ⚠️ GTK, system tray varies by desktop environment |
| Heal (agent recovery) | ✅ Full (POSIX signals) |
| Chisel daemon | ✅ POSIX signals |

**Near-parity with macOS.** Desktop app is rougher but everything else works identically.

---

### You're on **Windows**

| Feature | Status |
|---------|:------:|
| CLI (all commands) | ✅ Full |
| Auto-discovery (config dirs) | ✅ Same paths (POSIX via WSL) |
| Auto-discovery (LLM scan) | ❌ No `lsof` — tasklist-based fallback, partial |
| Watch daemon | ⚠️ Custom PID file + polling |
| Desktop app (pywebview) | ⚠️ Supported by pywebview but untested |
| Heal (agent recovery) | ⚠️ SIGBREAK fallback, partial |
| Chisel daemon | ❌ Untested |

**Usable CLI-only.** No desktop, no lsof-based discovery, no daemon integration. Commands work.

---

## By Notification/Channel Integration

### You want alerts on **Telegram**

| Feature | Status |
|---------|:------:|
| Alert push (outbound) | ✅ `observeco alerts subscribe telegram <chat_id>` |
| Event ingestion (inbound) | ✅ TelegramAdapter — messages, callback queries via webhook server |
| Requirements | Bot token in `~/.observeco/telegram_bot_token`, webhook server running |

**First-class.** Full push and pull.

---

### You want alerts on **Slack**

| Feature | Status |
|---------|:------:|
| Alert push (outbound) | ❌ Not implemented natively — use `observeco alerts subscribe webhook <incoming-webhook-url>` as workaround |
| Event ingestion (inbound) | ✅ SlackAdapter — `app_mention`, message events via webhook server |

**Inbound only.** Slack can send events into ObserveCo, but ObserveCo cannot push alerts to Slack natively.

---

### You want alerts on **Discord**

| Feature | Status |
|---------|:------:|
| Alert push (outbound) | ❌ Not implemented natively — use `observeco alerts subscribe webhook <channel-webhook-url>` as workaround |
| Event ingestion (inbound) | ✅ DiscordAdapter — slash commands, PING via webhook server |

**Inbound only.** Same pattern as Slack.

---

### You want alerts on **WhatsApp**

| Feature | Status |
|---------|:------:|
| Alert push (outbound) | ❌ Not implemented |
| Event ingestion (inbound) | ❌ Not implemented |

**Zero support.**

---

### You want alerts on **Email**

| Feature | Status |
|---------|:------:|
| Alert push (outbound) | ✅ `observeco alerts subscribe email <addr>` — uses local sendmail or SMTP config |
| Event ingestion (inbound) | ❌ No email adapter |

**Push only.** One-way.

---

### You want a **generic webhook**

| Feature | Status |
|---------|:------:|
| Alert push (outbound) | ✅ `observeco alerts subscribe webhook <url>` — HTTP POST |
| Event ingestion (inbound) | ✅ Any OEF-format webhook |
| Webhook server | ✅ `observeco webhook` launches FastAPI on port 9120, ingests Slack/Discord/Telegram events |

**Universal bridge.** Can push to anything that accepts an HTTP POST.

---

## By LLM Provider (for ObserveCo's own LLM features)

ObserveCo uses LLMs internally for: agent discovery enrichment, heal escalation, alert enrichment, pathway anomaly detection, and personalised feedback. The `llm_service/` module auto-detects available providers from environment variables and local servers.

| Provider | Detection | Auto-select priority |
|----------|-----------|:--------------------:|
| **Anthropic** (Claude) | `ANTHROPIC_API_KEY` | 🥇 Cloud #1 |
| **OpenAI** (GPT-4o) | `OPENAI_API_KEY` | 🥇 Cloud #2 |
| **DeepSeek** | `DEEPSEEK_API_KEY` | 🥇 Cloud #3 |
| **Google** (Gemini) | `GOOGLE_API_KEY` | 🥇 |
| **Mistral** | `MISTRAL_API_KEY` | 🥇 |
| **Groq** | `GROQ_API_KEY` | 🥇 |
| **Together** | `TOGETHER_API_KEY` | 🥇 |
| **OpenRouter** | `OPENROUTER_API_KEY` or `sk-or-*` key prefix | 🥇 |
| **Ollama** (local) | `http://localhost:11434` reachable | 🥈 Local #1 |
| **LM Studio** (local) | `http://localhost:1234` reachable | 🥈 |
| **vLLM** (local) | `http://localhost:8000` reachable | 🥈 |
| **TextGen WebUI** (local) | `http://localhost:5000` reachable | 🥈 |
| **LocalAI** (local) | `http://localhost:8080` reachable | 🥈 |

**Auto-selection order:** Anthropic → OpenAI → DeepSeek → Google → Mistral → Groq → Together → OpenRouter → Ollama → LM Studio → vLLM → TextGen → LocalAI.

**No LLM?** ObserveCo degrades gracefully — static fallbacks for discovery, no heal escalation, no alert enrichment. Your agents are still monitored and dashboards still work.

**Cost tracking:** Per-consumer budget. Tier 1 (deep/mission-critical) defaults to $0.02/call. Tier 2 (shallow/value-add) defaults to $0.005/call. Cache with configurable TTL. License-gated: trial/Pro tiers unlock LLM features; free tier uses static fallbacks only.

**Billing integration:** Stripe Checkout + webhooks + license provisioning via `observeco billing`. Solo ($9/mo) and Team ($29/mo) plans. Trial period configurable via `OBSERVECO_TRIAL_DAYS` env var.

---

## By ObserveCo Feature Surface

| Feature group | Commands | Who it's for |
|---|---|---|
| **Pulse** (health) | `observeco pulse check`, `observeco pulse circuit` | Everyone running agents — real-time alive/dead/error + circuit breaker |
| **Watch** (daemon) | `observeco watch start/stop/status/once` | Anyone who wants 24/7 automated monitoring without thinking about it |
| **Tokens** (cost) | `observeco tokens log/status/trends/budget` | Anyone paying for LLM API calls — anomaly detection, budget thresholds |
| **Chisel** (compression) | `observeco chisel trim/drift/skills/artifacts/compress/config/watch` | **Hermes users** only — managing prompt-token bloat in SOUL.md and skills |
| **ClawForge** (context) | `observeco clawforge profile/load/garden` | **OpenClaw users** only — context window profiling, intent-aware loading, MEMORY.md hygiene |
| **Context** (generic aliases) | `observeco context trim/drift/skills/profile/load` | All users — brand-agnostic wrappers so you don't need to know the names |
| **Memory** | `observeco memory garden` | All users with MEMORY.md files |
| **Heal** | `observeco heal` | Agent operators — auto-diagnose + fix common failures |
| **L2** (trending) | `observeco l2 scan/status` | Power users — proactive detection of memory bloat, stuck conversations, drift, upstream failures |
| **Alerts** | `observeco alerts subscribe/unsubscribe/list/log` | Anyone who wants to be paged on their phone |
| **Graph** | `observeco graph` | Ecosystem architects — dependency graphing |
| **Dashboard** | `observeco dashboard` (port 9119) | Everyone — live fleet view, terminals, trends, config, plugins |
| **Desktop** | `observeco desktop` | **macOS** users who want a native window instead of browser tab |
| **Webhook** | `observeco webhook` (port 9120) | Teams that pipe Slack/Discord/Telegram events through the risk engine |
| **Snapshot** | `observeco snapshot` | Documentation writers — living document from real agent ecosystem data |
| **Prune** | `observeco prune` | Storage-conscious users — retention-based data cleanup |
| **Billing** | `observeco billing configure/status/set-key/list-keys` | Paying users on Solo/Team tier |
| **Plugins** | `observeco plugin log/stats` | OpenClaw plugin developers — hook tracking |

---

## By Use Case (quick)

| "I want to..." | Does ObserveCo do this? | How |
|---|---|---|
| ...monitor 10 Hermes agents on my Mac | ✅ Yes — best case | Auto-detect, watch daemon, chisel compression, dashboard |
| ...monitor OpenClaw agents on a Linux server | ✅ Yes — full support | Auto-detect, clawforge profiling, pulse, L2 trends |
| ...get paged when my agent crashes | ✅ Yes | `observeco alerts subscribe telegram <chat_id>` |
| ...see which agents are burning tokens | ✅ Yes | `observeco tokens trends`, dashboard token tab |
| ...auto-fix my stuck Hermes agent | ✅ Yes | `observeco heal` — auto-diagnose and restart |
| ...enrich alert messages with LLM analysis | ✅ Yes | LLM service auto-detects keys, enriches alerts |
| ...see a live graph of my agent dependencies | ✅ Yes | `observeco graph` |
| ...monitor Ollama models | ✅ Yes | Auto-discovery, pulse, circuit breaker |
| ...monitor a CrewAI agent | ⚠️ Partial | Register manually, health check URL, pulse works |
| ...push alerts to Slack/Discord natively | ❌ No | Use `observeco alerts subscribe webhook <incoming-url>` |
| ...push alerts to WhatsApp | ❌ No | Not supported |
| ...run on Windows as a desktop app | ❌ No | CLI works, desktop is macOS only |
| ...have no LLM API keys at all | ⚠️ Works but limited | Static fallbacks for LLM features, monitoring still works |
| ...manage billing for a team | ✅ Yes | Stripe integration, `observeco billing`, Solo/Team plans |
| ...auto-discover what's running on a new machine | ✅ Yes | Tier 1 config scan + Tier 3 LLM scan of `ps aux`/`lsof` |

---

## Summary

| Profile | Verdict |
|---|---|
| **Hermes user on macOS** | 🟢 Best experience. Every feature works. |
| **Hermes + OpenClaw user on Linux** | 🟢 Intended full-power use case. |
| **Ollama-only user on any OS** | 🟡 Monitoring works, no agent management. |
| **Custom agent user on any OS** | 🟡 Register manually, get the monitoring surface. |
| **Windows user** | 🟠 CLI works, desktop and daemon are rough. |
| **Slack/Discord-first user** | 🟠 Inbound only — use webhook bridge for outbound. |
| **WhatsApp user** | 🔴 Not supported. |
| **No LLM keys** | 🟡 Monitoring still works, LLM features degrade gracefully. |
| **Solo dev with 1 agent** | 🟢 Simple setup, quick wins. |
| **Team with 10+ agents** | 🟢 Dashboard, shared DB, alerts, billing all scale. |
