# ObserveCo — Pre-Launch Audit: Findings + Revision Requests

**Auditor:** Hound  
**Date:** 2026-05-28  
**To:** Sean / Dev team  
**Status:** Findings for revision, not final

---

## Part 1: Audit Findings (11 items, severity-graded)

### 🔴 CRITICAL — Will Block Traction

#### C1. Config keys rendered as agent cards

**Problem:** Agent auto-discovery reads every top-level key from Hermes `config.yaml` as an agent. Dashboard renders 65 agent cards — 51 of which are config sections (`allowed_chats`, `api_keys`, `api_server`, `approval`, `args`, `boards`, `models`, etc.) that have no business being agents.

**Impact:** A new user with Hermes sees a broken dashboard. A user without Hermes sees 0 agents. Both experiences fail on first impression.

**Fix:** Auto-discovery must filter to entries with valid agent metadata (health_check, config_path, or SOUL.md path). Config key sections should never be promoted as agents.

#### C2. Spec onboarding (3-phase progressive loading) not implemented in dashboard

**The spec** (§8) describes a beautiful phased experience: animated placeholder cards → "Observing your fleet..." → status dots appearing one-by-one → phase explanations for non-Hermes users.

**The reality:** Phase banner is empty. `phase-1` is detected but the banner JS only has messages for phase-0 and phase-1 — and those are generic. There are zero instructions for post-install next steps.

**Fix:** Implement the full 3-phase progression from spec. Empty states must guide action, not just display "no data."

#### C3. Framework section labels drive non-Hermes users away

**Problem:** `/api/agents` endpoint renders agents inside `<div class="agent-section" id="section-hermes">`, splitting the fleet into "Hermes" vs "Other." A LangChain user sees their agents literally categorized as not-fitting-in.

**Impact:** Framework labeling actively alienates the majority of the agent-building community who don't use Hermes.

**Fix:** Remove framework section labels from fleet view. All agents in one grid. Framework context belongs in agent detail panels, not as a sorting category.

---

### 🟡 HIGH — Will Cause User Confusion

#### H1. Dashboard Pro messaging overwhelms Free/OSS identity

26 references to Pro features vs 0 references to free, MIT, or open source. First impression is "paid tool with limited free tier" rather than "generous open-source tool."

**Fix:** Add "Free forever MIT" badge in header. Balance locked tiles so free features feel complete, not like a teaser.

#### H2. Every empty state should guide action

| Section | Current | Should say |
|---------|---------|------------|
| Restart quality | "No restart data yet" | "Restart data appears during pulse monitoring. Run `observeco pulse check` to start." |
| Heal log | ✅ Good — gives CLI command | Keep as-is |
| Error timeline | "No errors — good sign!" | ✅ Good — reassuring |

**Fix:** Every empty state follows: what's missing → why → when it will appear → what to do if it doesn't.

#### H3. README positions Hermes-first, not agent-agnostic-first

README lists 7 CLI commands — 5 are Hermes/OpenClaw-specific. Tagline says "built for Hermes, works with anything." A CrewAI/LangGraph user sees 5 of 7 features they can't use.

**Fix:** Restructure README to lead with cross-framework features (`pulse check`, `pulse circuit`, `dashboard`) before framework-specific optimizers. Quickstart should start with "I installed it, now what?"

---

### 🟢 LOW — Polish Items (ship-able with tracking)

#### L1. Token bar segment tooltips not implemented

Spec describes hover tooltips showing component name + exact token count (`Skills: 1,847 tokens`). Not in dashboard.

#### L2. "Restart Quality" endpoint returns empty

Data table and mockup exist in spec but `GET /api/restart-quality` returns "no data" — collection pipeline not wired.

#### L3. CLI first-run message doesn't guide next steps

Running `observeco dashboard` for the first time shows no explanatory output.

---

## Part 2: Fleet Scope — Should Services/Workflows Be in the Dashboard?

**Decision:** Yes, but classified separately from agents.

| Type | Example | Dashboard shows | How we detect |
|------|---------|----------------|---------------|
| **Agent** | Hermes daemon, Kepler | Full pulse + token profile + context | Hermes profiles, registered agents |
| **Service** | Daily digest cron, deal scout watcher, hound-watcher | Pulse health + schedule + last run | launchd plists, crons |
| **Workflow** | Kanban dispatcher, signal router | Last run, next run, success/failure | Cron manifest |
| **❌ Config key** | `allowed_chats`, `api_keys` | **Nothing** — filtered out | No agent metadata |

**How to implement:**
- Add `process_type` field to DB: `agent | service | workflow`
- Auto-detect: launchd daemons → services, Hermes profiles → agents, cron jobs → workflows
- Dashboard shows collapsible sections: "Agents (8) · Services (6) · Workflows (12)"
- Each type gets relevant metrics (agents = token health, services = uptime/failures, workflows = last-run/next-run)

**Kanban task already created for this scope expansion** — see `t_a19315a0` (crash classification feature, which includes restart_log for services).

---

## Part 3: Becoming Framework-Agnostic — Path Forward

### The honest state today

| Feature | Works for anyone? | What it needs |
|---------|-----------------|---------------|
| `pulse check` | ✅ Any process | Nothing — genuinely agnostic |
| `pulse circuit` | ✅ Any framework | Nothing |
| Error timeline | ✅ Any framework | Nothing |
| Dashboard fleet view | ✅ Any framework | Nothing |
| Token breakdown | ❌ Hermes-only | Needs system prompt decomposition |
| Drift tracking | ❌ Hermes-only | Needs token data over time |
| Memory hygiene | ❌ OpenClaw-only | Needs MEMORY.md + workspace |
| CLI `--help` | ❌ 5 of 7 commands are Hermes/OpenClaw | CLI reorg needed |

### Step 1: Webhook data contract (highest leverage, lowest effort)

Define ONE POST endpoint any framework can call. Write 10-line integration snippets per framework — community copies them, we don't build adapters.

```bash
POST /api/v1/pulse  {agent_name, status, latency_ms}
POST /api/v1/error  {agent_name, error_type, message, severity}
POST /api/v1/token  {agent_name, components: {identity: 1200, skills: 3400, ...}}
```

### Step 2: CLI reorganisation

```
Cross-framework (top-level):
  observeco pulse check        # Works for everyone
  observeco pulse circuit      # Works for everyone
  observeco dashboard          # Works for everyone
  observeco agent add          # Manual agent registration

Framework-specific (subcommands):
  observeco hermes trim        # Was 'chisel trim'
  observeco hermes drift       # Was 'chisel drift'
  observeco openclaw profile   # Was 'clawforge profile'
  observeco openclaw garden    # Was 'clawforge garden'
```

A non-Hermes user never sees Hermes-specific commands in `--help`.

### Step 3: Dashboard never labels agents by framework

No "section-hermes" vs "section-other." All agents in one fleet. If an agent has no token data, its card shows pulse health + uptime only — still useful, still complete.

### Step 4: The real test

We cannot claim framework-agnosticism without testing on a real non-Hermes machine. Options:
- Deploy to PyPI and watch issues for the first 5 "this doesn't work" reports
- Test on a clean macOS VM with only a dummy script POSTing to the webhook
- Recruit 1-2 beta testers from non-Hermes frameworks

---

## Revision Priority

| Priority | Items | Owner |
|----------|-------|-------|
| **Ship-blocking** | C1 (config keys → agents), C3 (framework labels) | Dashboard |
| **Ship-blocking** | C2 (onboarding flow) | Dashboard + spec |
| **Launch+1 week** | H1 (Pro/Free balance), H2 (empty states), H3 (README) | Docs + UI |
| **Launch+2 weeks** | L1-L3 (polish), Part 2 (services/workflows) | Product |
| **Ongoing** | Part 3 (framework-agnostic webhook contract) | Architecture |

All 11 findings have corresponding kanban tasks. See board for execution tracking.
