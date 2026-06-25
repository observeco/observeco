# Orchestration Anti-Patterns Playbook — Multi-Agent Governance

**Product:** ObserveCo (and all future multi-agent projects)
**Status:** Living — update as lessons accumulate
**Version:** 1.0 — 2026-06-12
**Version History:**
| Version | Date | What changed |
|---------|------|-------------|
| 1.0 | 2026-06-12 | Initial creation — adapted from Addy Osmani's agent-skills orchestration-patterns reference |

**Source:** Real risk — ObserveCo runs multiple agents (Hound, Pragma, Aleph, Dreamer, Pickles) that communicate through shared state. Without governance, agents can create routing loops, lose context through summarization, and silently overwrite each other's work.

This playbook sits **alongside** agent-governance-playbook.md. It governs how agents interact with each other, not how individual agents manage their sessions.

---

## 1. Thesis

**The user is the orchestrator.** Agents do not invoke other agents. Skills are mandatory hops *inside* an agent's workflow, not across agents.

Every multi-agent failure traces to one root: **an agent made a decision that should have been made by the human.** The agent routed to the wrong persona, paraphrased context and lost nuance, or triggered a cascade that no one was monitoring.

---

## 2. The Governing Rule

```
The user (or a slash command) is the orchestrator.
Personas do not invoke other personas.
Skills are mandatory hops inside a persona's workflow, not across them.
```

This is not a suggestion. It is a constraint that prevents the four anti-patterns below.

---

## 3. The 5 Endorsed Patterns

### Pattern 1: Direct Invocation (No Orchestration)
- Single agent, single perspective, single artifact
- One round trip — the baseline to compare against
- **Use when:** The work is one perspective on one artifact describable in one sentence

### Pattern 2: Single-Persona Slash Command
- Wraps one agent + project skills as a reusable entry point
- Cost: same as direct invocation (just a saved prompt)
- **Anti-signal:** If the command body is mostly "decide which persona to call," delete it

### Pattern 3: Parallel Fan-Out with Merge ✅
- Multiple agents operate concurrently on the same input → merge step synthesises
- **Requires:** Genuinely independent sub-tasks, each benefits from own context window, merge fits in main context, wall-clock latency matters
- **Validation checklist:**
  - [ ] Ordering independence? (Can A and B run in any order?)
  - [ ] Different *kinds* of findings? (Not just different perspectives on same thing)
  - [ ] Context budget? (Does merge fit in main context?)
  - [ ] Latency gain noticeable? (Is parallelism worth the coordination cost?)

**Example:** `/ship` runs code-reviewer, security-auditor, test-engineer in parallel, then synthesises reports.

### Pattern 4: Sequential Pipeline as User-Driven Commands
- User runs lifecycle commands in order: `/spec` → `/plan` → `/build` → `/test` → `/review` → `/ship`
- **No orchestrator agent** — the user IS the orchestrator
- **Why not automate:** LLM orchestrators (a) lose nuance summarising hand-offs, (b) skip human checkpoints, (c) double token cost

### Pattern 5: Research Isolation (Context Preservation)
- Spawn a research sub-agent when reading large amounts that shouldn't pollute main context
- **Use when:** Main session needs focus, result is much smaller than input, decision quality benefits from breathing room
- Prefer built-in exploration tools over custom research personas

---

## 4. The 4 Anti-Patterns

### Anti-Pattern A: Router Persona ("Meta-Orchestrator")

**What it looks like:**
```
User → Router Agent → decides which persona to call → calls persona → returns result
```

**Why it's bad:**
- Pure routing layer — no domain value
- 2× paraphrasing hops (user → router → persona)
- User already knew what they wanted
- Router adds latency and token cost with zero decision quality improvement

**The fix:** Delete the router. Let the user (or slash command) invoke the persona directly.

**Detection:** If a persona's primary job is "decide which other persona to call," it's a router. Delete it.

---

### Anti-Pattern B: Persona Calls Another Persona

**What it looks like:**
```
Agent A → needs something → calls Agent B → Agent B summarises → Agent A loses context
```

**Why it's bad:**
- Violates single-perspective design (each persona has ONE perspective)
- Loses context through summarization (Agent B's full context → summary → Agent A)
- Hides cost (user doesn't see Agent B's token usage)
- Multiplies failure modes (Agent A fails, Agent B fails, hand-off fails)

**The fix:** Agent A should either do the work itself, or the user should invoke Agent B separately and pass the result to Agent A.

**Detection:** If Agent A's code contains `delegate_task` or `spawn` targeting Agent B, it's a persona-calls-persona violation.

---

### Anti-Pattern C: Sequential Orchestrator That Paraphrases

**What it looks like:**
```
User → Orchestrator → summarises task for Agent 1 → Agent 1 completes →
Orchestrator summarises result for Agent 2 → Agent 2 completes →
Orchestrator summarises final result for user
```

**Why it's bad:**
- Loses human checkpoints (user never reviews between agents)
- Accumulated drift across pipeline (each paraphrase loses nuance)
- Doubles token cost (orchestrator processes every hand-off)
- Removes user agency (user sees final result, not intermediate decisions)

**The fix:** User-driven sequential pipeline (Pattern 4). User runs each command, reviews, decides next step.

**Detection:** If an agent's job is to "coordinate" other agents without doing domain work, it's a sequential orchestrator. Replace with user-driven commands.

---

### Anti-Pattern D: Deep Persona Trees

**What it looks like:**
```
Agent A → calls Agent B → calls Agent C → calls Agent D → leaf work
```

**Why it's bad:**
- Each layer adds latency and tokens with zero decision value
- Debugging nightmare (which layer introduced the error?)
- Leaf personas lose context through multiple summarizations
- Cost compounds exponentially

**The fix:** Maximum depth of 1. Agent A can call leaf workers, but leaf workers cannot call other agents.

**Detection:** If `spawn_depth > 1`, the tree is too deep. Flatten it.

---

## 5. ObserveCo Agent Architecture

Our agents follow the endorsed patterns:

| Agent | Role | Invocation |
|-------|------|-----------|
| **Hound** | CEO — strategy, approvals, managing agents | Direct (Telegram topic 1) |
| **Pragma** | COO — builds, verification, agent health | Direct (Telegram topic 2072) |
| **Aleph** | Second Brain wiki, knowledge graph | Direct (Telegram topic 29) |
| **Dreamer** | Pattern detection, signal synthesis | Direct (Telegram topic 1165) |
| **Pickles** | PA — filtering, briefs | Direct (Telegram topic 2) |

### Communication Rules
- Agents communicate through the **shared intelligence directory**, not direct invocation
- Hound reads flags and verifications, decides and responds in the agent's topic
- Pragma reads decisions from `intelligence/decisions/` and executes
- No agent calls another agent directly — all communication is through shared state

### The User Is the Orchestrator
- Sean reads briefs and decides what to action
- Sean triggers specific agents for specific tasks
- No agent autonomously triggers another agent's work
- Exception: watchdog scripts write flags (automated detection, not agent invocation)

---

## 6. Verification Checklist

- [ ] No router personas (agents that only route to other agents)
- [ ] No agent calls another agent directly
- [ ] No sequential orchestrator that paraphrases between agents
- [ ] Maximum spawn depth of 1 (no deep trees)
- [ ] All agent communication through shared intelligence directory
- [ ] User is the orchestrator for all multi-agent workflows
- [ ] Parallel fan-out only for genuinely independent sub-tasks
- [ ] Every agent has a single, clear perspective

---

## 7. Integration with Existing Playbooks

| Playbook | How this integrates |
|----------|-------------------|
| agent-governance-playbook.md | This playbook governs inter-agent patterns; agent-governance governs intra-agent session discipline |
| spec-gated-workflow-playbook.md | Phase boundaries are human checkpoints that prevent agent-driven orchestration |
| system-design-testing-playbook.md | Agent architecture tested as part of system design verification |
| master-fidelity-gate.md | Orchestration patterns feed into the integration gate's system design layer (Layer D) |
| ux-testing-playbook.md | Multi-agent UX interactions affect human-perception checks in ux-testing |
| coding-fidelity-playbook.md | Coding fidelity ensures agent outputs match spec before hand-off |
| requirements-fidelity-playbook.md | Requirements spec defines the boundaries within which agents operate |
| security-stride-playbook.md | STRIDE threat model covers multi-agent communication channels and data flows |
| ui-testing-playbook.md | UI interaction patterns in multi-agent outputs are verified by ui-testing |
