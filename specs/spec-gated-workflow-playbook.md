# Spec-Gated Workflow Playbook — The 4-Phase Gate

**Product:** ObserveCo (and all future software projects)
**Status:** Living — update as lessons accumulate
**Version:** 1.0 — 2026-06-12
**Version History:**
| Version | Date | What changed |
|---------|------|-------------|
| 1.0 | 2026-06-12 | Initial creation — adapted from Addy Osmani's agent-skills spec-driven-development pattern |

**Source:** Real failure — multiple ObserveCo features were built against ambiguous requirements, leading to rework cycles. The spec process collapsed Spec→Plan→Tasks into one step, allowing assumptions to propagate unchecked.

This playbook sits **upstream** of coding-fidelity-playbook.md and requirements-fidelity-playbook.md. It enforces a gated workflow where each phase requires human review before proceeding.

---

## 1. Thesis

**Code without a spec is guessing.** The spec is the shared source of truth between agent and human — defining what, why, and how we know it's done.

The most dangerous class of misunderstanding is **unstated assumptions**. The agent fills in gaps silently, builds the wrong thing confidently, and the human discovers the mismatch after implementation.

This playbook enforces **mandatory human review at every phase boundary**. No phase advances without explicit approval.

---

## 2. The 4-Phase Gated Workflow

```
SPECIFY ──→ PLAN ──→ TASKS ──→ IMPLEMENT
   │          │        │          │
   ▼          ▼        ▼          ▼
 Human      Human    Human      Human
 reviews    reviews  reviews    reviews
```

**Rule: DO NOT advance without validation at each gate.**

---

## 3. Phase 1: SPECIFY

### 3.1 Surface Assumptions First

Before writing any spec content, list assumptions as bullet points:

```
ASSUMPTIONS:
- I assume the dashboard is server-rendered (not SPA)
- I assume authentication is already implemented
- I assume the database schema supports this feature

→ Correct me now or I'll proceed with these.
```

This is the **most dangerous** class of misunderstanding. Surfacing assumptions early prevents hours of rework.

### 3.2 Write the Spec (6 Core Areas)

| # | Area | What to cover |
|---|------|--------------|
| 1 | **Objective** | What, why, who is the user, what does success look like |
| 2 | **Commands** | Full executable commands (build, test, lint, dev) — not just tool names |
| 3 | **Project Structure** | Directory layout with descriptions |
| 4 | **Code Style** | One real code snippet beats three paragraphs |
| 5 | **Testing Strategy** | Framework, locations, coverage expectations, test levels |
| 6 | **Boundaries** | Three tiers (see §4) |

### 3.3 Reframe Vague Requirements

When requirements are vague, translate into concrete, measurable conditions:

| Vague | Measurable |
|-------|-----------|
| "Make the dashboard faster" | LCP < 2.5s, initial load < 500ms, CLS < 0.1 |
| "Improve reliability" | 99.9% uptime, p95 latency < 200ms |
| "Better error handling" | All errors produce user-facing message, no 500s in production |

This enables looping and retrying toward a clear goal instead of guessing.

### 3.4 Exit Criteria

- [ ] All 6 core areas covered
- [ ] Human has reviewed and approved
- [ ] Success criteria are specific and testable
- [ ] Boundaries defined (see §4)
- [ ] Spec saved to a file in the repository

---

## 4. The 3-Tier Boundary System

Every spec must define boundaries using these three tiers:

### Always Do
Things the agent can decide and execute autonomously.
- Follow existing code patterns
- Write tests for new logic
- Run linter and formatter
- Update documentation
- Handle edge cases with established patterns

### Ask First
Things that require human confirmation before proceeding.
- New authentication flows
- New sensitive data categories
- New external integrations
- Changes to CORS, rate limiting, or security headers
- Database schema migrations
- Architecture decisions with no existing precedent

### Never Do
Things that must never happen without explicit human instruction.
- Commit secrets or credentials
- Disable security features
- Modify production data directly
- Skip tests to "save time"
- Make architectural decisions not in the spec
- Expose internal error details to users

---

## 5. Phase 2: PLAN

After spec approval, create an implementation plan:

1. Identify major components and their dependencies
2. Determine implementation order (what must be built first)
3. Note risks and mitigation strategies
4. Identify parallel vs. sequential work
5. Define verification checkpoints

### Exit Criteria
- [ ] Human reads and signs off ("yes, that's the right approach")
- [ ] Dependencies mapped
- [ ] Risks identified with mitigations
- [ ] Verification checkpoints defined

---

## 6. Phase 3: TASKS

Break the plan into discrete, implementable tasks:

### Task Template
```
- [ ] Task: [description]
  Acceptance: [what "done" looks like]
  Verify: [how to prove it's done]
  Files: [list of files to touch — max 5]
```

### Task Rules
- Each task completable in **one focused session**
- Each task has **explicit acceptance criteria** + **verification step**
- Tasks ordered by **dependency, not importance**
- **No task should touch more than ~5 files**
- If a task touches more than 5 files, split it

### Exit Criteria
- [ ] Every task has acceptance criteria and verification step
- [ ] No task touches more than 5 files
- [ ] Human reviews and approves task list
- [ ] Tasks saved in version control

---

## 7. Phase 4: IMPLEMENT

Execute tasks one at a time:

1. Load only the relevant spec section for the current task
2. Implement the task
3. Run verification step
4. Mark task complete
5. Move to next task

### Rules
- Do not skip ahead to "interesting" tasks
- Do not refactor outside the current task's scope
- Do not add features not in the spec
- If a task reveals a spec error, stop and update the spec first

---

## 8. Keeping the Spec Alive

| When | Action |
|------|--------|
| Decision changes | Update spec first, then implement |
| Scope changes | Reflect added/cut features in spec |
| Commits | Spec lives in version control alongside code |
| PRs | Link back to the spec section each PR implements |

The spec is a **living document**, not a one-time artifact.

---

## 9. Common Rationalizations (Anti-Patterns)

| Rationalization | Reality |
|----------------|---------|
| "Too simple for a spec" | Simple tasks still need acceptance criteria — a 2-line spec is fine |
| "Spec after code" | That's documentation, not specification |
| "Spec will slow us down" | 15-min spec prevents hours of rework |
| "Requirements will change" | That's why the spec is a living document |
| "The user knows what they want" | Even clear requests have implicit assumptions |
| "I can just quickly implement" | You're guessing. Write it down. |

---

## 10. Red Flags (Stop Signals)

- Writing code without written requirements
- Asking "should I just start building?" before defining "done"
- Implementing features not in any spec or task list
- Making architectural decisions without documenting them
- Skipping the spec because "it's obvious"
- A task touching more than 5 files

---

## 11. Verification Checklist

- [ ] Assumptions surfaced and confirmed before spec writing
- [ ] All 6 spec areas covered
- [ ] 3-tier boundaries defined
- [ ] Vague requirements reframed as measurable criteria
- [ ] Human approved spec before moving to plan
- [ ] Plan approved before moving to tasks
- [ ] Every task has acceptance criteria and verification step
- [ ] No task touches more than 5 files
- [ ] Spec saved in version control
- [ ] Spec updated when decisions change

---

## 12. Integration with Existing Playbooks

| Playbook | How this integrates |
|----------|-------------------|
| requirements-fidelity-playbook.md | This playbook **replaces** the ad-hoc spec process with a gated workflow |
| coding-fidelity-playbook.md | Tasks from Phase 3 feed directly into coding-fidelity checks |
| agent-governance-playbook.md | Phase boundaries are human checkpoints that prevent agent drift |
| system-design-testing-playbook.md | Architecture decisions in Phase 2 feed into system design tests |
| ux-testing-playbook.md | UX assumptions surfaced in §3.1 feed into ux-testing checks |
| ui-testing-playbook.md | UI interaction requirements defined in spec feed into ui-testing checks |
| master-fidelity-gate.md | The spec-gated workflow feeds into the master integration gate for pre-ship sign-off |
| orchestration-anti-patterns-playbook.md | Phase boundaries enforce user-as-orchestrator by requiring human approval at each gate |
| security-stride-playbook.md | STRIDE threat model runs during Phase 1 (SPECIFY) as part of spec writing |

Also see [master-fidelity-gate.md §4 Automated + Human Gate Protocol] for how the spec gate feeds the integration gate, and [security-stride-playbook.md §2 STRIDE Threat Model] for security analysis during the SPECIFY phase.
