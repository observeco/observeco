# obs-spec: Analysis Layer Output Examples

**Status:** Draft 2026-06-07
**Product:** ObserveCo
**Purpose:** Concrete examples of what the combined analysis layer produces — framework APM data + Observeco intelligence — with clear value propositions per example.

---

## §1 Data Source Separation

### What Framework APM Provides (Competitor Data)

| Source | What It Captures | Data Shape |
|--------|-----------------|------------|
| CrewAI | Task execution, agent interactions, tool calls | Trace spans per task |
| LangChain | Chain steps, LLM calls, retrieval events | Callback traces |
| LiteLLM | Per-call tokens, cost, latency, provider | SQLite rows (self-hosted gateway) |
| Langfuse | Trace visualization, cost tracking, prompt versioning | OTel spans + UI |
| AgentOps | Session replay, agent behavior patterns | Event logs |
| OpenAI SDK | API responses, token usage | stdout / console |

### What Observeco Uniquely Provides (Nobody Else Has This)

| Feature | Data | Why It Matters |
|---------|------|---------------|
| Pulse health | alive/dead/error every 30s, circuit breaker | Is the agent even running? |
| SOUL.md drift | Component diff % over 7 days | Is the prompt changing without you knowing? |
| Token breakdown | Per-component: identity/skills/memory/tools/guidance | Which part of the prompt is expensive? |
| Skill audit | Tokens per skill, compression savings | Which skills are bloated? |
| Memory garden | Contradictions, duplicates, debt score | Is the agent's memory self-contradicting? |
| Pathway Map | Agent-to-agent routing graph | How do agents talk to each other? |
| Context Health Score | 0–100 composite (spec'd) | Single number: is my agent's brain healthy? |
| Relapse Prevention | Timeline of changes × degradation (spec'd) | What broke things? |
| Plugin Firewall | Per-plugin cost/error/latency ranking (spec'd) | Which plugins are burning money? |
| Context Fire Drill | Turn survival simulation (spec'd) | When will my agent hit its context limit? |
| **Post-Turn Webhook** | **Per-turn: tokens, tools, latency, context sources (spec'd §3.41)** | **What happened on each turn?** |
| **Eval Trace Export** | **Per-turn: quality score, tool efficiency, retry/hallucination flags (spec'd §3.42)** | **Was this turn any good?** |
| **Tool Efficiency Ranking** | **Per-tool: cost/error/latency ranking (spec'd §3.43)** | **Which tools are worth their token price?** |
| **Context Source Utilisation** | **Per-source: load frequency vs usage (spec'd §3.44)** | **Which skills am I paying for but never using?** |

---

## §2 Analysis Layer Output Examples

### Example 1: Cross-Framework Cost Attribution

**What each source sees alone:**

| Source | Data | What It Tells You |
|--------|------|-------------------|
| LiteLLM (competitor APM) | 847 LLM calls today, total cost $4.12 | "How much I spent" |
| Observeco (unique) | Hound's skills section grew 2,100 tokens this week | "Which part of the prompt changed" |

**Combined analysis output:**

```
COST BREAKDOWN: Fleet — $4.12 today (847 calls)
  → Framework APM: 62% from agent routing (4.2s avg latency)
     23% from tool-augmented calls (11.8s avg)
     15% from direct completions (0.9s avg)
  → Observeco: Tool-augmented calls cost 3.4x more because
     they load 2,800 tokens of skill content per call
  → Top cost driver: "browser-automation" skill — 34% of
     tool tokens, 12% error rate
  → Fix: Compress browser-automation skill body
     Projected: -1,100 tokens/call → saves $0.38/day
```

**Value:** LiteLLM tells you *how much* you spent. Observeco tells you *which part of the agent* made it expensive. Neither alone gives you "compress this skill to save $0.38/day."

---

### Example 2: Framework Trace + Drift Correlation

**What each source sees alone:**

| Source | Data | What It Tells You |
|--------|------|-------------------|
| CrewAI trace | research_task took 47s, 3 tool calls, 1 LLM retry | "This task is slow" |
| Observeco drift | SOUL.md drifted +8% since June 2 | "The prompt changed" |

**Combined analysis output:**

```
PERFORMANCE REGRESSION: CrewAI crew "market-research"
  → Framework trace: research_task p95 went from 32s → 47s (+47%)
     LLM retries increased from 0.2/call to 0.8/call
  → Observeco: SOUL.md drift +8% since June 2 — extra guidance
     tokens pushed context utilisation to 78%
  → Correlation: Retries started June 3 — same day drift crossed +5%
  → Root cause: Context pressure → LLM truncates reasoning →
     agent retries with less context → more retries → more tokens
  → Fix: Run `observeco chisel compress --mode lite` on research agent
     Projected: -1,400 tokens → context utilisation back to 65%
     → retries should drop to baseline
```

**Value:** CrewAI trace says "this task is slow." Observeco says "the prompt bloated." Combined: "the bloat *caused* the slowness via retry cascade."

---

### Example 3: Multi-Agent Routing + Memory Health

**What each source sees alone:**

| Source | Data | What It Tells You |
|--------|------|-------------------|
| LangGraph trace | Aleph called Dreamer, Dreamer tool failed | "Tool call failed" |
| Observeco memory garden | Dreamer has 5 contradictions, context health 61 | "Memory is messy" |

**Combined analysis output:**

```
FAILURE CASCADE: Aleph → Dreamer pipeline
  → Framework trace: Dreamer's tool call failed with
     "conflicting context" error (3x in last hour)
  → Observeco: Dreamer memory garden — 5 contradictions detected
     → "Project X deadline: June 15" vs "June 30" (edited Jun 4)
     → "Preferred API: v2" vs "v3" (edited Jun 5)
  → Observeco: Context Health Score dropped 74→61 in 48h
  → Correlation: Tool failures cluster around contradiction-dense
     context regions
  → Diagnosis: Contradictions cause Dreamer to generate
     inconsistent outputs → downstream tools reject them
  → Fix: Resolve contradictions in Dreamer's memory
     Run `observeco clawforge garden --agent dreamer --interactive`
  → Prevention: Enable Anomaly Inbox (§3.37) to surface
     contradiction-error correlations automatically
```

**Value:** LangGraph says "tool failed." Observeco says "why." Combined: "bad memory caused the failure, and here are the 5 specific contradictions to fix."

---

### Example 4: Rate Limit Attribution via Provider Gateway + Drift

**What each source sees alone:**

| Source | Data | What It Tells You |
|--------|------|-------------------|
| LiteLLM gateway | 23 rate-limit errors (429) yesterday | "Provider rejected calls" |
| Observeco drift | Kepler SOUL.md edited 3 times, +2,400 tokens | "Prompt got bigger" |

**Combined analysis output:**

```
RATE LIMIT ATTRIBUTION: Kepler
  → LiteLLM: 23 rate-limit errors (429) on June 5
     → All from OpenAI gpt-4o, all between 14:00-16:00
  → Observeco: SOUL.md edits on June 3-5 added 2,400 tokens
     → Token usage per turn: 3,200 → 5,600 (+75%)
  → Correlation: Token spike = more tokens/min hitting provider
     → Crossed rate limit threshold during peak hours
  → Cost: 23 failed calls × $0.00 = $0 wasted (retried successfully)
     BUT: 23 retries × 5,600 tokens = 128,800 extra tokens
     = $0.386 wasted on retries alone
  → Fix: Compress SOUL.md back to pre-edit size
     Projected: 5,600 → 3,400 tokens/turn → stays under rate limit
```

**Value:** LiteLLM says "rate limits happened." Observeco says "prompt bloat caused them." Combined: "your edits cost you $0.39 in wasted retries."

---

### Example 5: Fleet Anomalies Inbox (Unified Surface)

The Anomalies Inbox (§3.37) reads across framework APM + Observeco health to produce one prioritised feed:

```
🔍 ANOMALIES INBOX — 4 issues detected

🔴 HIGH
  1. Kepler — context health dropped 72→54 in 48h
     → Source: Observeco Context Health Score
     → Framework APM: LLM retry rate up 3x since June 4
     → Attribution: SOUL.md edits +3,200 tokens, no compression
     → Action: Run compression or defer pending edits

🟡 MEDIUM
  2. Hound — browser-automation plugin failing 12% of calls
     → Source: Observeco Plugin Firewall
     → Framework APM: 14 tool calls, 2 failures, $0.042 cost
     → Action: Disable or investigate root cause

🟡 MEDIUM
  3. Raven — token cost $0.18/turn (baseline: $0.04)
     → Source: Observeco Token Tracking
     → Framework APM: LiteLLM logs show unconstrained tool chaining
     → Action: Check for runaway tool loops

🟢 LOW
  4. Aleph → Dreamer pipeline — 3 "conflicting context" errors
     → Source: Observeco Memory Garden (5 contradictions)
     → Framework APM: LangGraph trace shows failure cascade
     → Action: Resolve contradictions in Dreamer's memory
```

**Value:** Framework APM data (what happened). Observeco intelligence (why it happened and what to do). One feed, not five dashboards.

---

## §3 Server-Side Data — Decision

### Recommendation: No. Stay focused.

**Reasons against traditional server metrics (CPU, memory, disk, network):**

1. **Target user runs agents on laptops/desktops.** Not on servers. `htop` and Activity Monitor already cover this. Adding server metrics means competing with tools that are already good at it.

2. **Observeco's moat is agent-specific.** No other tool tracks SOUL.md drift, skill token composition, memory contradictions, or context health scores. Server metrics dilute the positioning toward "just another monitoring tool."

3. **The expensive resource is tokens, not CPU.** An agent at 5% CPU can burn $50/day in LLM API calls. An agent at 95% CPU doing local inference costs $0. CPU usage is a poor proxy for "is my agent healthy?"

4. **Adds complexity without differentiation.** Every monitoring tool tracks server metrics. Observeco doing it too makes it one of many, not the only one for AI agents.

**The narrow exception — agent process health:**

Lightweight process-level metrics (RSS memory, CPU%) are relevant when they answer "is the agent process itself unhealthy?" This is already partially covered by:

| Existing Feature | What It Covers |
|-----------------|---------------|
| Pulse check | Is the process alive? |
| L2 baselines (spec'd) | RSS, P95, error rates |
| Circuit breaker | Is it stuck? |
| Auto-heal | Crash recovery |

These are **agent process health** metrics, not **server infrastructure** metrics. The framing matters:

- "Is my agent's process healthy?" → Observeco's concern ✅
- "Is my server healthy?" → Datadog's concern ❌ (not our lane)

**Bottom line:** Stay focused on the token economy and context intelligence. That's where the pain is, and nobody else is solving it locally. Adding CPU/RAM/disk metrics would be scope creep that moves Observeco away from its unique value toward commodity monitoring.

---

## §4 OpenClaw/Hermes Users — Closing the Dynamic Gap

### The Problem

For CrewAI/LangChain users, framework traces provide per-turn execution data (task duration, tool calls, retries, errors). Observeco ingests those via §12.

For OpenClaw/Hermes users, there is **no external APM layer**. The framework *is* the agent. Observeco has deep static analysis (prompt composition, drift, memory health) and health monitoring (pulse, circuit breaker), but limited dynamic analysis (what happened during execution).

### What Observeco Can See Today (OpenClaw/Hermes users)

| Layer | Data | Source | Quality |
|-------|------|--------|--------|
| Health | alive/dead/error, latency, error type | Pulse check (30s) | ✅ Complete |
| Static context | Token breakdown by component, SOUL.md drift, skill audit, memory garden | Filesystem reads | ✅ Complete |
| Dynamic execution | ??? | Not wired | ❌ Gap |
| Quality signals | ??? | Hermes internal only | ❌ Gap |

### The Solution: Dynamic Execution Layer (§3.41–§3.44)

Four new features close the gap:

| Feature | What It Provides | Spec |
|---------|-----------------|------|
| Post-Turn Webhook | Per-turn: tokens, tools, latency, context sources loaded/skipped | §3.41 |
| Eval Trace Export | Per-turn: quality score, tool efficiency, retry flag, hallucination flag | §3.42 |
| Tool Efficiency Ranking | Which tools are cost-effective, which should be disabled | §3.43 |
| Context Source Utilisation | Which skills/memory are actually used vs loaded by default | §3.44 |

### Analysis Layer Outputs — OpenClaw/Hermes Users (Post-Build)

#### Example 1: Per-Turn Cost Attribution

**Before (today):** Observeco shows total tokens per agent. No per-turn detail.

**After (with §3.41):**

```
COST ATTRIBUTION: Kepler — last 24h
  → 47 turns, total $0.34
  → Peak: Turn 12 — $0.047 (web_search + read + exec — 3 tools)
  → Cheapest: Turn 19 — $0.002 (direct completion, no tools)
  → Average: $0.007/turn
  → Tool cost breakdown: web_search $0.12, read $0.03, exec $0.08
  → Recommendation: exec calls are 3x more expensive than read — 
     check if shell commands can be replaced with file reads
```

**Value:** "How much did this conversation cost?" — answerable for the first time.

#### Example 2: Quality × Context Correlation

**Before (today):** Observeco shows drift is up. Can't tell if quality dropped.

**After (with §3.42):**

```
QUALITY REGRESSION: Hound
  → Eval trace: quality_score dropped 0.91 → 0.78 over 5 days
  → Eval trace: hallucination_flag triggered 3x in last 24h
  → Observeco: SOUL.md drift +12% since June 2
  → Observeco: Context utilisation at 82% (was 65%)
  → Correlation: Quality decline correlates with context pressure
     (R² = 0.89 between utilisation and quality_score)
  → Root cause: Agent evicting relevant skills to fit bloat
  → Fix: Compress SOUL.md → reduce utilisation → restore quality
  → Projected: -2,400 tokens → utilisation back to 65% → 
     quality_score recovers to 0.88+
```

**Value:** "Is my agent getting dumber?" — answerable with data, not vibes.

#### Example 3: Tool Efficiency for Framework-Free Users

**Before (today):** No visibility into which tools are worth their token cost.

**After (with §3.43):**

```
TOOL EFFICIENCY: Hound — last 7 days
  → web_search: 23 calls, $0.008/call, 0% errors → 🟢
  → read: 47 calls, $0.001/call, 0% errors → 🟢
  → exec: 31 calls, $0.004/call, 3% errors → 🟡
  → browser-automation: 14 calls, $0.031/call, 12% errors → 🔴
  → Total tool cost: $0.18/day
  → Potential savings: $0.06/day by disabling browser-automation
```

**Value:** "Which of my tools are actually worth their cost?" — data-driven tool pruning.

#### Example 4: Context Source Utilisation

**Before (today):** Observeco shows token breakdown but not which sources are used.

**After (with §3.44):**

```
CONTEXT UTILISATION: Hound — last 7 days
  → SOUL.md: 100% turns, 3,200 tok → 🟢 always needed
  → skills/github: 94% turns, 820 tok → 🟢 frequently used
  → skills/comfyui: 8% turns, 1,400 tok → 🔴 remove from defaults
  → skills/ascii-art: 12% turns, 680 tok → 🟡 lazy-load
  → Total loaded: 42,100 tok/turn
  → Actually used: 14,200 tok/turn
  → Potential savings: 2,080 tok/turn (remove 2 low-utilisation skills)
  → Fire Drill impact: Removing these 2 skills extends survival
     from 42 turns to 58 turns before degradation
```

**Value:** "I'm loading 42K tokens but only using 14K" — actionable waste identification.

#### Example 5: Fleet Anomalies Inbox — OpenClaw/Hermes flavour

```
🔍 ANOMALIES INBOX — 4 issues detected

🔴 HIGH
  1. Kepler — context health 54, quality_score dropped to 0.72
     → Source: Context Health Score + Eval Trace Export
     → Attribution: SOUL.md edits +3,200 tokens, no compression
     → Action: Compress or defer edits

🟡 MEDIUM
  2. Hound — browser-automation failing 12% of calls
     → Source: Tool Efficiency Ranking
     → Cost: $0.042/day, 14 calls, 2 failures
     → Action: Disable or investigate

🟡 MEDIUM
  3. Raven — exec tool cost $0.12/day (baseline: $0.03)
     → Source: Post-Turn Webhook + Tool Efficiency Ranking
     → Attribution: 3x more exec calls than usual this week
     → Action: Check for runaway shell commands

🟢 LOW
  4. Dreamer — 2 skills loaded <10% of turns but cost 2,100 tok
     → Source: Context Source Utilisation Tracker
     → Action: Remove from defaults or lazy-load
```

**Value:** Four data sources (health, eval, webhook, utilisation) → one prioritised feed. For OpenClaw/Hermes users who have no external APM.

### Build Priority

| Phase | What | Effort | Impact |
|-------|------|--------|--------|
| 1 | §3.41 Post-Turn Webhook | ~3d | Unlocks §3.43 + §3.44 |
| 2 | §3.42 Eval Trace Export | ~2d | Quality signals for Hermes users |
| 3 | §3.43 Tool Efficiency Ranking | ~1.5d | Derived from §3.41 |
| 4 | §3.44 Context Source Utilisation | ~1.5d | Derived from §3.41 |
| **Total** | | **~8d** | **Closes the dynamic gap** |

---

## §5 The One-Liner

Observeco's analysis layer answers questions that neither framework APM nor health monitoring can answer alone:

**"Which change broke things? Which plugin is burning money? When will my agent hit its context limit? What should I fix first?"**

Not "combined infra + APM" but **cross-layer attribution in a domain where the expensive resource is tokens, not CPU.**

For OpenClaw/Hermes users: **"How much did this conversation cost? Is my agent getting dumber? Which tools are worth their token price? Which skills am I paying for but never using?"**
