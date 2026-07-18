# Prompt for Pragma: Master Plan & Specs Update

**Objective:** Update `specs/observeco-master-plan.md` to reframe ObserveCo from "a good dashboard for agents" into "the product that defines agent observability as a category." Every change below reinforces the category argument: agents are not LLM apps, and the tools built for LLM tracing cannot see agent-runtime problems.

**Self-contained — do not open other files unless instructed.** The key reference is `docs/competitive-analysis.md` (already updated with live research). This prompt tells you exactly what text to replace, add, and where.

---

## §1. Product Identity — Reframe the Category

### Replace the one-liner and positioning

Current (line 13-14 of the master plan):

```
| **One-liner** | ObserveCo tells you if your Hermes agents are working, what they're doing, and where your money goes |
| **Positioning** | "ObserveCo tells you if your Hermes agents are working, what they're doing, and where your money goes." — Locked 2026-06-29 |
```

Replace with:

```
| **One-liner** | Agent observability is a new category. ObserveCo defines it — runtime health, not just LLM tracing. |
| **Positioning** | "AI agents are not LLM apps. They hallucinate, bloat, drift, cascade-fail, and burn money silently. The tools built for REST APIs and LLM apps can't see any of this. Agent observability is a new category — and ObserveCo defines it." — Updated 2026-06-30 |
```

### Add §1.1 The Category Argument

Insert after the Product Identity table (after line 23) as a new subsection:

```markdown
### 1.1 The Category Argument: Why Agents Need Their Own Observability

**The wedge:** Every other tool asks *"what did the model return?"* ObserveCo asks *"is my agent healthy?"* — a fundamentally different question, for a fundamentally different runtime.

| Dimension | LLM App (Chat/RAG) | AI Agent | What Breaks | Who Catches It |
|-----------|-------------------|----------|-------------|----------------|
| **Failure mode** | Bad response | Silent degradation, context bloat, drift, cascade failure | You notice when a user complains | **Only ObserveCo** — pulse + circuit + drift + heal |
| **Cost model** | Per-token (predictable) | Per-token × loops × retries × sub-agents (explosive) | $500 overnight from a runaway loop | **Only ObserveCo** — per-agent cost + anomaly detection |
| **State** | Stateless (response in, response out) | Context window = state — bloats, corrupts, drifts | Agent gets dumber over weeks, you can't tell why | **Only ObserveCo** — brain analysis + memory garden + compression |
| **Debugging** | Prompt inspection | "Step 4 broke but I can't see step 2" — multi-hop cascade failures | Hours of manual log spelunking | **Only ObserveCo** — trace tree + anomaly inbox |
| **Health** | Response latency | Alive but broken — running but producing garbage | Wasted tokens on a dead agent | **Only ObserveCo** — composite health score + behavioural monitoring |
| **Cascade risk** | None (single call) | One agent's failure poisons downstream agents | Fleet-wide meltdown from one bad agent | **Only ObserveCo** — circuit breaker + signal flow map |

#### Competitive matrix (simplified — see full analysis at `docs/competitive-analysis.md`)

| Feature | ObserveCo | Phoenix | LangFuse | OpenLIT | Codeburn | AgentTrace |
|---------|:--------:|:-------:|:--------:|:-------:|:--------:|:----------:|
| Fleet health | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Token spend | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Cache hit rate | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| Context bloat detection | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Drift tracking | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Brain compression | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Auto-restart / Heal | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Circuit breaker | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Push alerts | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Local-first (no cloud) | ✅ | ❌ | ❌ | ✅ | ✅ | ✅ |
| MIT license (pure) | ✅ | ❌ | ❌ (open core) | ✅ (Apache 2.0) | ✅ | ✅ |

**The gap:** 9 features in the matrix where ObserveCo is the **only** tool that has them. That's not coincidence — it's the category definition.

#### Market validation: Codeburn signal

Codeburn, a simple cost tracker for AI coding agents that does nothing more than count tokens/$, has **8,300 GitHub stars in under 1 year** (769 commits, active community). This proves:

1. The market is **desperate** for agent-specific tooling — they'll star a basic cost tracker
2. Nobody has defined the category yet — the door is open
3. Codeburn's limitation (cost tracking only) is exactly the gap ObserveCo fills

If cost-data-only gets 8.3k★, a full-fledged agent observability platform that answers "is my agent healthy?" has room to define an entirely new category.

```

---

## §2. Feature Matrix — Reprioritize by Competitive Urgency

The current feature matrix (§2) is ordered by original spec chronology. **Reorder it by competitive urgency** using a new `Priority` column. The existing rows keep their original feature numbers — the priority column overrides the sort order.

### Add priority column

Insert `| **Priority** |` as the **second column** (after `#`) in the table header. The full header becomes:

```
| # | **Priority** | Feature | Category | Status | Free (now) | Pro (future) | Effort | Spec |
```

### Priority tiers

Assign these priorities. Features not listed below default to **P1** (shipped).

**P0 — Must ship before public launch (closes category-defining gaps):**

| # | Feature | Rationale |
|---|---------|-----------|
| 58 | Cost Estimation Engine (tokens→$) | #1 Reddit pain point. "Where your money goes" is incomplete without dollar conversion. ~2d. |
| 71 | Generic Discovery Layer (ollama list, psutil, port scanner) | Non-Hermes users see empty fleet — blocks all non-beachhead adoption. ~5.5h. |
| — | Auto-Heal Dashboard UI (toggle, status card, history table) | Backend built — dashboard has empty cards. Pro users can't use what they paid for. ~1d. |
| — | Push Alerts Dashboard UI (subscription management, delivery log, test button, Discord) | Backend built — no configure-from-dashboard experience. Discord is #2 requested channel. ~1.5d. |

**P1 — Shipped / Launch+Week 1 (closes "but what about X" objections):**

| # | Feature | Rationale |
|---|---------|-----------|
| All shipped features | Everything currently ✅ Live | Already built, already differentiating. |
| 53 | OTel Trace Ingestion (OTLP listener, port 4318) | Kills "Hermes-only" perception — zero-instrument entry for 28 frameworks. ~2d. |
| 27 | Context Health Score (0–100 from bloat, drift, error rate) | "Is my agent's brain healthy?" — the question no competitor answers. ~2d. |
| 33 | Anomalies Inbox (fleet-wide issue surfacing) | "Your agent has 3 problems right now" — turns passive monitoring into active alerting. ~3d. |
| T2 | Evaluation / Quality Scoring (per-turn quality score, tool efficiency) | Without this, we can only say "running" — not "producing good output." ~2d. |

**P2 — Launch+Month 1 (category cementing):**

| # | Feature | Rationale |
|---|---------|-----------|
| 59 | Composite Health Score (0–100, combining tool failure, anomalies, uptime, drift) | The single number buyers compare across agents. ~2d. |
| 60 | Anomaly Detection Taxonomy (no_tools, high_cost, long_gaps, retry_loops, context_pressure) | Catches subtle failures circuit breaker misses. ~3d. |
| — | Deterministic Replay (lightweight — `observeco replay --turn <id>`) | #1 debugging pain point on Reddit. ~3d. |
| 61 | CI Quality Gates (`observeco gate --fail-under-health`) | Turns dashboard into active quality gate. ~2d. |
| 63 | Static Report Export (self-contained HTML/JSON/Markdown) | Shareable with non-technical stakeholders, requires no running server. ~1.5d. |
| 62 | Session Baseline Diffing (save fleet state, compare runs) | Automatic regression detection — "cost up 23% vs baseline." ~2d. |

**P3 — Launch+Month 2-3 (adoption scaling):**

| # | Feature | Rationale |
|---|---------|-----------|
| 57 | Multi-Source Log Parser (Claude Code, Codex, Cursor, Gemini, Aider) | Currently Hermes-only. Non-Hermes users see nothing. ~4d. |
| — | LangGraph adapter (callback handler → POST to ObserveCo) | 53M PyPI downloads/month — "where all the chaos happens." ~3d. |
| — | CrewAI adapter (task-level observability callback) | 14M PyPI downloads/month. ~2d. |

### Sort order

In the reordered table:

1. **P0 features** first (uns shipped, highest urgency)
2. **P1 shipped features** second (the product as it exists today — what already ships)
3. **P1 planned features** third (launch+1 week)
4. **P2 features** fourth
5. **P3 features** fifth
6. **Deferred / removed** last (existing deferred rows stay at bottom)

Keep every existing row — do not delete any feature. The priority column simply overrides sort order.

---

## §3. Add New §4: Honest Gaps

**Location:** Insert as a new top-level section between the current §3 (Feature Deep Dives) and the existing sections below. Number it §4 and renumber old §4+ → §5+.

**Content:**

```markdown
## 4. Honest Gaps — What Competitors Have That We Don't

*Documented 2026-06-30. Updated by competitive analysis batch. Source: `docs/competitive-analysis.md`*

This section is an explicit inventory of what competitors have that ObserveCo does
not — categorised by how relevant each gap is to agent observability. Our goal is
not to build every feature. It is to close every 🔴 gap before public launch,
evaluate 🟡 gaps post-launch, and accept ⚪ as out of scope.

### 🔴 Relevant to Agent Observability — Gaps We Should Close

| Feature | Who Has It | Why It Matters | Effort | Priority |
|---------|-----------|---------------|--------|:--------:|
| **Evaluation / Quality Scoring** | Phoenix, LangFuse, DeepEval, Promptfoo, AgentNeo | Without this, we can say "agent is running" but not "agent is producing good output." An agent that's alive but hallucinating is worse than dead. | ~2d | P1 |
| **Deterministic Replay** | Observability & Replay project, coding agent tools | The #1 Reddit debugging pain point: "Step 4 broke but I can't see step 2." Tracing shows *what* — replay shows *why*. | ~3d | P2 |
| **CI Quality Gates** | AgentTrace, Promptfoo, DeepEval | Turns observability from passive dashboard into active quality gate. `observeco gate --fail-under-health` returns exit code for CI. | ~2d | P2 |
| **Session Baseline Diffing** | AgentTrace | Save fleet state as baseline, compare subsequent runs. "Cost up 23% vs baseline — agent X health dropped 15 points." | ~2d | P2 |
| **Multi-Source Log Parser** | Codeburn (31 agents), Phoenix (30+ frameworks) | Currently Hermes-only. Non-Hermes users see nothing. Single highest adoption blocker. | ~4d | P3 |
| **Cost Estimation ($)** | LangFuse, AgentTrace, Codeburn | Tokens → dollars. The #1 pain point across all Reddit threads. | ~2d | P0 |
| **Static Report Export** | AgentTrace | Self-contained HTML/JSON report, one file, no backend required. Shareable with non-technical stakeholders. | ~1.5d | P2 |
| **Anomaly Detection Taxonomy** | AgentTrace, Arize AX (Signal) | Beyond up/down. Catches: no_tools, high_cost, long_gaps, retry_loops, context_pressure. | ~3d | P2 |
| **Composite Health Score** | AgentTrace | Single 0–100 number per agent combining tool failure rate, anomalies, token efficiency, uptime, drift stability. This is what buyers compare across agents — "agent X is 92, agent Y is 47." | ~2d | P2 |

### 🟡 Adjacent to Agent Observability — Nice to Have, Not Core

| Feature | Who Has It | Why It's Adjacent |
|---------|-----------|-------------------|
| **Multi-framework support (30+)** | Phoenix, LangFuse, OpenLIT | Relevant for adoption but an integration surface, not the category definition. Deferred to post-v1.0. |
| **Swarm / Multi-agent visualisation** | Arize AX (paid), LangFuse (beta) | We have the Communication Pathway Map — covers multi-agent visibility. Deeper work deferred. |
| **AI engineering agent (Alyx)** | Arize AX (paid) | An AI agent that debugs traces. Novel but gimmicky — overlaps with our LLM Intelligence Service (#25). |
| **Signal / automated root cause** | Arize AX (paid) | Overlaps with our Anomalies Inbox (#33). Would be worth a dedicated PR post-launch but not pre-launch. |

### ⚪ Not Relevant to Agent Observability — Different Category

| Feature | Who Has It | Why It's Not Agent Observability |
|---------|-----------|----------------------------------|
| **Prompt management (version control, serving)** | LangFuse, Phoenix | LLM engineering — not about agent runtime health. |
| **Datasets & experiments** | LangFuse, Phoenix, DeepEval | LLM development — not about runtime monitoring. |
| **Playground (interactive prompt testing)** | LangFuse, Phoenix | Prompt engineering — not about agent health. |
| **GPU monitoring** | OpenLIT | Infrastructure monitoring — not agent-specific. |
| **Guardrails (input/output validation)** | Guardrails AI, NeMo | Safety — complementary but separate category. |
| **MCP server** | Phoenix | Integration protocol — useful but not observability. |
| **Cloud/SaaS hosting** | LangFuse Cloud, Arize AX | Deployment model. We are local-first by design. |
| **Team collaboration (multi-user, RBAC)** | LangFuse, Arize AX | Enterprise feature — not for beachhead. Post-v2.0. |
| **Compliance-grade audit trail** | Enterprise tools | Regulated industries — not core category. |
| **Financial controls (budget enforcement)** | NORNR-style | Governance — not observability. |
```

---

## §4. Update Competitive References

The master plan contains scattered references to competitive analysis. Three updates needed:

### 4.1 Cross-reference in master plan header

Replace any reference to old `docs/competitive-landscape.md` or similar with:

```
**Competitive reference:** `docs/competitive-analysis.md` (updated 2026-06-30 — now covers 7 tools, 27+ features, Reddit pain point extraction, and priority-ordered gap analysis)
```

### 4.2 Remove or redirect stale competitor mentions

Search for hardcoded competitor comparisons in the master plan. Any mention comparing ObserveCo to a competitor that contradicts the new analysis must be updated. Flag any inconsistencies.

### 4.3 Add competitive rationale to feature entries

For each P0 feature that corresponds to a closed gap (Cost Estimation → closes token→$ gap), add a parenthetical rationale: `(*Closes §4 — Cost Estimation gap*)`. This creates traceability between the Honest Gaps section and the feature matrix.

---

## §5. Codeburn Signal — Add Market Validation

Add a standalone line to the product identity table (under or replacing the "Supersedes" row):

```
| **Market signal** | Codeburn (8.3k★ in <1 year) proves the market is desperate for agent-specific tooling — and Codeburn is just a cost tracker. A full agent observability platform has room to define the category. |
```

Also add a brief reference to the Codeburn comparison in the competitive matrix within §1.1 The Category Argument (already included in the §1.1 template above — just ensure it's there).

---

## What Not to Change

These are **fixed boundaries**. Do not modify them regardless of how compelling a restructuring might seem:

| Boundary | Reason |
|----------|--------|
| **MIT license** — "Free forever for Hermes users" stays. No gating, no trial needed for built features. | Core positioning — "no pricing gate" is our moat alongside local-first. Changing the license destroys trust. |
| **Local-first architecture** — SQLite (`~/.observeco/pulse.db`), zero cloud, zero telemetry. | The differentiator. Every competitor requires Docker, ClickHouse, Postgres, or a cloud account. Local-first is why the right user picks us. |
| **Hermes beachhead scope** — multi-framework / generic discovery is P0 but it's additive to the Hermes foundation, not a replacement. Hermes remains primary. | Without a beachhead, the product diffuses into a generic "supports everything poorly." Hermes users are the first market — serve them deeply. |
| **Feature numbers** — all existing feature numbers (1–79) are stable identifiers referenced in kanban, specs, and ADRs. Do not renumber them — the new priority column overrides sort order. | Renumbering breaks every cross-reference in the codebase, specs, and project management kanban. |
| **Pricing model** — free MIT for core + BYOK for LLM features. Pro tier future, deferred until beachhead validated. No pricing table for Pro. | The commercial-strategy-v2.md spec is the authority. Don't invent Pro pricing here. |
| **Dashboard UI patterns** — do not redesign the dashboard (fleet view cards, modal drill-downs, tabbed agent detail). Only update copy to reflect the category argument. | The UI was user-tested and validated. The update is messaging, not UX. |
| **§3 Feature Deep Dives** — all ~4,000 lines of user-facing explanations. Do not rewrite them. They are written for end-users, not investors. | These sections explain *why* each feature matters in plain English. They're the product's teaching layer. Updates to positioning belong in §1, not §3. |
| **Existing kanban tasks** — do not change or re-prioritise kanban boards. The priority column in §2 is a *planning signal*, not a kanban shuffle. | Kanban is managed separately. This document is spec-level only. |

### If you're tempted to change any of these, stop and ask yourself:
1. Am I about to touch the MIT license statement? → **Don't.**
2. Am I about to rename a feature number? → **Don't. Use the priority column instead.**
3. Am I about to rewrite end-user documentation in §3? → **Don't. Focus on §1 and §2.**
4. Am I about to remove a "Hermes-specific" reference and replace it with "generic"? → **Don't. Multi-framework is additive, not a replacement.**

---

## Summary of Changes

| Section | Change | Action |
|---------|--------|--------|
| **§1 Product Identity** | Reframe one-liner and positioning to category-defining | Replace text; add §1.1 The Category Argument |
| **§1.1 new** | Category argument — 6-dimension table, competitive matrix, Codeburn signal, market validation | Insert new subsection |
| **§2 Feature Matrix** | Add Priority column, reorder by P0→P3 urgency | Add column; assign priorities; re-sort rows |
| **§4 new (formerly §3→§3)** | Honest Gaps — 🔴/🟡/⚪ categorisation | Insert new section; renumber everything below |
| **§4 (old §4→§5)** | Competitive references updated | Point to `docs/competitive-analysis.md`; add gap-closure annotations |
| **Various** | Codeburn signal | Add to product identity table and §1.1 |
| **All** | "What Not to Change" guardrails | Do not touch: MIT license, local-first, Hermes beachhead, feature numbers, pricing model, dashboard UI, §3 deep dives, kanban |

After making all changes, verify:
- [ ] The one-liner reads "Agent observability is a new category. ObserveCo defines it."
- [ ] §1.1 The Category Argument exists with the 6-dimension table and competitive matrix
- [ ] Codeburn (8.3k★) is referenced in §1.1 as market validation
- [ ] §2 Feature Matrix has a `Priority` column with P0/P1/P2/P3 assignments
- [ ] Features are sorted by priority (P0 first → P3 last)
- [ ] §4 Honest Gaps exists with 🔴/🟡/⚪ sections
- [ ] §4+ sections renumbered correctly (old §4→§5, etc.)
- [ ] All competitive references point to `docs/competitive-analysis.md`
- [ ] No changes to: MIT license, local-first architecture, Hermes beachhead, feature numbers, pricing model, dashboard UI, §3 deep dives, or kanban
