# ObserveCo — Product Feature Audit

**Author:** Main  
**Date:** 2026-05-26  
**Purpose:** Complete inventory of all context/token management tools we've built internally (Hermes ecosystem), what was spec'd for ObserveCo, what's currently in production, and what's free vs paid vs lost.

---

## Part 1: Internal Tools (Built Before ObserveCo, Running in Hermes Ecosystem)

These were built to solve our own problems operating 14 Hermes agents + Kepler (OpenClaw) on a single M4 Mac Mini. They are **not part of ObserveCo** — they run inside each Hermes agent at runtime. Users do not install them separately.

### 1.1 Chisel Compression (Previously Called "Caveman")

| Attribute | Value |
|-----------|-------|
| **Historical names** | Caveman → CHISEL → Chisel |
| **What it does** | Shrinks each agent's system prompt at session start by compressing verbose guidance blocks. Does NOT track or measure tokens — it compresses them. |
| **Modes** | **Off** (no compression), **Lite** (compresses 6 guidance blocks — tool-use rules, format instructions, platform hints), **Full** (compresses guidance + memory blocks + user profile + context files) |
| **Where it lives** | Hermes `run_agent.py` (~5370-5530), activated by `HERMES_COMPRESSION_LEVEL` env var |
| **Activation** | `HERMES_COMPRESSION_LEVEL=lite` in `~/.hermes/.env` — covers all Hermes daemons and CLI sessions |
| **Cadence** | Once per session at startup. No crons. One shot. |
| **Framework** | Hermes only (internal to Hermes Agent) |
| **Status** | ✅ Production — active, runs automatically every session |

### 1.2 Chisel Trim Analysis (Previously Called "Caveman Trim")

| Attribute | Value |
|-----------|-------|
| **Historical names** | Caveman trim → Chisel decomposition → Chisel trim analysis |
| **What it does** | Reads an agent's system prompt (SOUL.md) and classifies tokens into 5 sections: identity, skills, memory, tools, guidance. **Does NOT compress** — it measures and classifies. |
| **Where it lives** | Originally inside Hermes as a measurement function. Extracted into ObserveCo `src/observeco/chisel/trim.py`. |
| **Framework** | Hermes only (SOUL.md-based agents) |
| **Status** | ✅ Production in ObserveCo — automatic via watch daemon every 30s |

### 1.3 Chisel Drift (Previously Called "Caveman Drift")

| Attribute | Value |
|-----------|-------|
| **Historical names** | Caveman drift → Chisel drift |
| **What it does** | Shows 7-day trend: is each agent's token allocation growing or stable? Per-component drift tracking. |
| **Where it lives** | Originally in Hermes. Extracted into ObserveCo `src/observeco/chisel/drift.py`. |
| **Framework** | Hermes only |
| **Status** | ✅ Production in ObserveCo — displayed in Tokens tab |

### 1.4 Pulse Check (Agent Liveness)

| Attribute | Value |
|-----------|-------|
| **Historical names** | Agent heartbeat → Pulse check |
| **What it does** | Probes each agent by health check URL, shell command, or process name (`pgrep`). Returns alive/dead/error with latency. |
| **Where it lives** | Originally in Hermes ecosystem. Extracted into ObserveCo `src/observeco/pulse/check.py`. |
| **Framework** | Framework-agnostic (works with any agent that exposes a health check) |
| **Status** | ✅ Production in ObserveCo — runs every 30s via watch daemon |

### 1.5 Circuit Breakers

| Attribute | Value |
|-----------|-------|
| **Historical names** | Agent circuit breaker → Pulse circuit |
| **What it does** | N-failure detection. If an agent fails N times (default: 3), trips the breaker to stop hammering. Auto-cooldown after 5 minutes. |
| **Where it lives** | Originally in Hermes. Extracted into ObserveCo `src/observeco/pulse/circuit.py`. |
| **Framework** | Framework-agnostic |
| **Status** | ✅ Production in ObserveCo — runs every 30s via watch daemon |

### 1.6 Self-Heal

| Attribute | Value |
|-----------|-------|
| **Historical names** | Agent auto-recovery → Heal |
| **What it does** | Detects dead agents via pulse check and attempts to restart them. Diagnoses: dead agent, tripped circuit, memory leak. |
| **Where it lives** | ObserveCo `src/observeco/heal.py` |
| **Framework** | Framework-agnostic |
| **Status** | ✅ Production in ObserveCo — button in dashboard triggers it. Auto-heal is Pro only. |

### 1.7 ClawForge (Context Profile — OpenClaw Only)

| Attribute | Value |
|-----------|-------|
| **Historical names** | ClawForge (no prior name) |
| **What it does** | Profiles OpenClaw agent context composition: MEMORY.md size, skill count, workspace bloat, memory debt (duplicates, contradictions, stale entries), intent-aware loading savings |
| **Sub-commands** | `profile` (context composition), `load` (intent-aware classifier), `garden` (memory hygiene — dedup, archive, flag contradictions), `history` (per-turn loading stats over time) |
| **Where it lives** | ObserveCo `src/observeco/clawforge/` |
| **Framework** | OpenClaw only |
| **Status** | ✅ Production in ObserveCo — CLI and dashboard integration |

---

## Part 2: What Was Spec'd for ObserveCo

### 2.1 Original Product Split (Now Unified)

Before the unified dashboard spec, there were **two separate product concepts**:

| Old Product | Focus | What Happened |
|-------------|-------|--------------|
| **ERIS** | Runtime integrity — pulse health, circuit breakers, self-heal, snapshot documentation | Merged into unified ObserveCo dashboard |
| **CHISEL** | Context observability — system prompt compression, token breakdown, drift tracking | Merged into unified ObserveCo dashboard |

The unified dashboard spec (`specs/unified-dashboard.md`) replaced both with a single product: **ObserveCo**.

### 2.2 Spec'd CLI Commands vs Current Reality

| Spec'd Command | In Spec | In Production | Notes |
|---------------|---------|---------------|-------|
| `observeco pulse check` | ✅ v1 critical | ✅ Live | Watch daemon does this automatically |
| `observeco pulse circuit` | ✅ v1 critical | ✅ Live | Watch daemon auto-records failures |
| `observeco chisel trim` | ✅ v1 critical | ✅ Live | **But:** Spec'd as CLI pipe (`echo ... \| observeco chisel trim`). Now automatic via watch daemon. CLI still exists but is deprecated. |
| `observeco chisel drift` | ✅ v1 critical | ✅ Live | Shown in Tokens tab |
| `observeco clawforge profile` | ✅ v1 critical | ✅ Live | OpenClaw context profile |
| `observeco clawforge load` | ✅ v1 critical | ✅ Live | Intent-aware classifier |
| `observeco clawforge garden` | ✅ v1 critical | ✅ Live | Memory hygiene |
| `observeco clawforge history` | ✅ v1 | ✅ Live | Per-turn loading stats |
| `observeco dashboard` | ✅ v1 critical | ✅ Live | FastAPI + htmx, 5 tabs |
| `observeco agents add` | 🟡 Launch+7d | ✅ Live | Manual agent registration |
| `observeco agents discover` | ✅ v1 | ✅ Live | Auto-detects Hermes + OpenClaw agents |
| `observeco alerts list` | 🟡 Launch+14d | ❌ Not built | Post-launch feature |

### 2.3 Spec'd Dashboard Tabs vs Current Reality

| Tab | Spec'd | In Production | Notes |
|-----|--------|---------------|-------|
| Fleet view | ✅ | ✅ | Agent cards with health dots |
| Token breakdown (Hermes) | ✅ | ✅ | Bar chart: identity/skills/memory/tools/guidance |
| Token breakdown (OpenClaw) | ✅ | ✅ | Source breakdown: MEMORY.md/skills/workspace/history/bootstrap |
| Drift trend | ✅ | ✅ | 7-day per-component drift line |
| Error history | ✅ | ✅ | Last 10 errors per agent |
| Circuit breaker state | ✅ | ✅ | Open/Closed/Tripped |
| Self-heal trigger | ✅ | ✅ | Button runs heal check |
| Memory Garden (OpenClaw) | ✅ | ✅ | Duplicates, contradictions, debt score |
| Alert relay (push) | 🔒 Pro | ❌ Not configured | Needs webhook/Telegram setup. Stripe wired. |
| Never-pruned history | 🔒 Pro | ❌ Not built | Free shows 24h |
| Fleet comparison side-by-side | 🔒 Pro | ❌ Not built | |
| Optimal budget planner | 🔒 Pro | ❌ Not built | |
| Multi-machine relay | 🔒 Pro | ❌ Not built | |
| Snapshot (markdown+SVG doc) | ⚠️ v1.1 | 🔴 Code exists but inactive | Held back for D+14 |
| MCP serve | ❌ v1.2 | 🔴 Not built | Held back for D+14+ |

---

## Part 3: Free vs Paid — Current Reality

### 3.1 Free (MIT License — Unlimited Agents, Unlimited Users)

| Feature | Works Today? | Notes |
|---------|-------------|-------|
| Fleet view (all agents, health dots, last check-in) | ✅ | |
| Pulse check (alive/dead/error per agent) | ✅ | Automatic via watch daemon |
| Circuit breakers (N-failure detection + auto-cooldown) | ✅ | |
| Token breakdown bar chart (Hermes — identity/skills/memory/tools/guidance) | ✅ | Automatic via watch daemon |
| Token breakdown (OpenClaw — ClawForge source breakdown) | ✅ | |
| 7-day drift trend per component | ✅ | |
| Error history (last 24h per agent) | ✅ | |
| Heal button (trigger diagnosis + restart) | ✅ | Manual click |
| In-dashboard alerts (visible in UI, no push) | ✅ | |
| Memory Garden (duplicates, contradictions, debt score — OpenClaw) | ✅ | |
| All CLI commands | ✅ | pulse, circuit, chisel, clawforge, dashboard |
| Local SQLite storage | ✅ | No cloud, no telemetry |
| MIT License | ✅ | Fork, modify, embed freely |

### 3.2 Pro ($9/mo Solo, $49/mo Team — Features Spec'd But NOT Yet Built)

| Feature | Status | What It Would Do |
|---------|--------|-----------------|
| Alert relay (Telegram, email, webhook push) | 🔴 Not built | Push notifications when circuits trip or drift exceeds thresholds. Stripe checkout wired. |
| Never-pruned history (errors, drift, pulse) | 🔴 Not built | Extended retention beyond 24h, never pruned |
| Fleet comparison (side-by-side token profiles) | 🔴 Not built | Compare all agents' token allocation |
| Optimal budget planner | 🔴 Not built | "Recommend allocation: save 16K by redistributing" |
| Drift alerts (proactive when > threshold) | 🔴 Not built | Same as alert relay |
| Circuit auto-recovery (auto-reset after N min) | 🔴 Not built | Configurable vs manual reset |
| Multi-machine relay | 🔴 Not built | Agents on different machines → one dashboard |
| Per-turn token cost per agent (webhook-based) | 🔴 Not built | Each agent POSTs token usage after every turn |

### 3.3 Reality Check

| Asserted in Spec | Reality |
|-----------------|---------|
| "All CLI commands + dashboard working" | ✅ True — all 8+ commands + dashboard operational |
| "Stripe integration live" | ✅ True — checkout redirects, webhooks wired |
| "30-day free trial on all Pro plans" | ⚠️ Partially — Stripe is wired with trial config but NO Pro features are built yet. Users can start a trial and see nothing unlocked. |
| "No credit card required to start the CLI" | ✅ True — CLI is free, no account needed |
| "Pro preview overlay shows real user data" | 🟡 Partial — the `[🔒 Pro]` badge shows on the alert panel but no preview modals with real data exist |
| "Agent dashboard — 5 tabs" | ✅ True — Health, Tokens, Memory, Garden, Alerts |

---

## Part 4: New Features Added to ObserveCo (2026-05-26)

After auditing what was lost in the Hermes→ObserveCo transition, 6 features were spec'd for inclusion. Five are fully doable; one requires a separate OpenClaw plugin package.

| Feature | In ObserveCo? | Why | Effort | Spec |
|---------|-------------|-----|--------|------|
| System prompt compression (`observeco chisel compress`) | ✅ Yes | Pure text manipulation, not Hermes-dependent. Port compression engine from `run_agent.py` as file-in/file-out. | ~2 days | `specs/pulse-depth-spec.md` §1 |
| Per-turn token cost tracking | ✅ Yes | `POST /api/chisel/trim` endpoint + agent-side post-turn hook (Hermes `run_agent.py`, OpenClaw ContextEngine) | ~3 days | `specs/pulse-depth-spec.md` §2 |
| Auto-heal dead agents | ✅ Yes | 3-line integration in watch loop — heal logic (`heal.py`) already exists with circuit breaker and cooldown | ~1 day | `specs/pulse-depth-spec.md` §3 |
| Intent-aware loading at runtime | ✅ Separate plugin | OpenClaw ContextEngine plugin (`@observeco/clawforge-plugin`) — Node.js package that hooks into bootstrap/ingest/pre-response lifecycle. ObserveCo receives reports via API but cannot control loading from outside. | ~5-7 days | `specs/pulse-depth-spec.md` §4 |
| Push alerts (Telegram, webhook, email) | ✅ Yes | Delivery module — alert detection pipeline already exists, only delivery layer missing | ~3 days | `specs/pulse-depth-spec.md` §5 |
| Extended token history (> 24h) | ✅ Yes | Query parameter change — all data already stored in SQLite indefinitely | ~2 hours | `specs/pulse-depth-spec.md` §6 |

### 4.1 What's Still Lost (Will Not Be Ported)

| Feature | Not in ObserveCo | Why |
|---------|-----------------|-----|
| Never-Say-Die Protocol | ❌ | 4-layer fallback chain tied to Hermes Agent architecture. Not product scope. |
| Kepler Dual SOULs consistency check | ❌ | Operational protocol, not product feature. |
| Original Caveman/CHISEL naming | ❌ | Superseded by ObserveCo naming. |

---

## Appendix: Naming History

---

## Appendix: Naming History

| Era | What We Called It |
|-----|------------------|
| Pre-April 2026 | **Caveman** — internal codename for system prompt compression |
| April–May 2026 | **CHISEL** — replaced "caveman." System prompt compression + token breakdown. Two-product split: **ERIS** (runtime integrity) + **CHISEL** (context observability). |
| May 2026+ | **ObserveCo** — unified product replacing ERIS + CHISEL. **Chisel** becomes the name for the token classification algorithm inside ObserveCo. **ClawForge** is the OpenClaw counterpart. |
