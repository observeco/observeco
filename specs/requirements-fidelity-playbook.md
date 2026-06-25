# Requirements & Spec Fidelity Playbook — The Upstream Gate

**Product:** ObserveCo (and all future software projects)
**Status:** Living — update as lessons accumulate
**Version:** 3.2 — 2026-06-10
**Version History:**
| Version | Date | What changed |
|---------|------|-------------|
| 1.0 | 2026-05-30 | Initial creation |
| 3.1 | 2026-05-31 | Standardization pass: all 7 playbooks bumped to v3.1. Fixed stale playbook-count references. Confirmed cross-references to Playbook Inventory (requirements-fidelity-playbook.md §Playbook Inventory) and Layer F First-Run Audit (master-fidelity-gate.md §2 Layer F). Removed stray empty FILE tags. |
| 2.0 | 2026-05-30 | Added Playbook Inventory, fixes "5 playbooks" refs |
| 2.1 | 2026-05-31 | Standardization pass: uniform versioning, cross-ref to Playbook Inventory in all docs, Golden Gate naming normalization |
| 3.2 | 2026-06-10 | Added Trap 7 (Payment Flow State Coverage), Trap 8 (Tier-Specific Empty States). Added Lessons Learned section with 2 entries. |

**Source:** Real failure — the watch daemon architecture fix was *correctly implemented* against an *incomplete spec*. The thread-in-dashboard approach was never ruled out by the requirements because the requirements never specified lifecycle, cross-platform, or data-continuity constraints.

This playbook sits **upstream** of coding-fidelity-playbook.md, ux-testing-playbook.md, and system-design-testing-playbook.md. It catches the class of problem where the code and architecture are perfect — but the spec was wrong.

## Playbook Inventory

The full playbook system has 11 documents, organized by flow:

| Order | Playbook | Role |
|-------|----------|------|
| 1 | requirements-fidelity-playbook.md | Spec hardening (upstream gate) |
| 2 | spec-gated-workflow-playbook.md | 4-phase gated spec process (SPECIFY → PLAN → TASKS → IMPLEMENT) |
| 3 | coding-fidelity-playbook.md | Code matches spec |
| 4 | ui-testing-playbook.md | Visual consistency & design system integrity |
| 5 | ux-testing-playbook.md | Human experience lens |
| 6 | system-design-testing-playbook.md | Architecture & daemon lens |
| 7 | agent-governance-playbook.md | Session mastery for agents |
| 8 | orchestration-anti-patterns-playbook.md | Multi-agent governance patterns |
| 9 | security-stride-playbook.md | STRIDE threat model + OWASP LLM Top 10 |
| 10 | master-fidelity-gate.md | Integration gate (combines all playbooks) |
| 11 | playbook-evolution-meta.md | Self-improvement loop |

Refer to this inventory when the playbook system is referenced in other documents. When a section says "all 6 playbooks" or "all playbooks", it refers to playbooks 1-6 as the core set.

---

## 1. Thesis

**A perfect implementation of an ambiguous spec is still wrong.**

The three sibling playbooks assume the spec, mockup, and master-plan.md are correct and complete. In practice, 40–60% of downstream failures originate here: ambiguous language, missing edge states, contradictory mockups, or "I'll know it when I see it" requirements.

This document is not a spec template. It is a **spec hardening process** — a repeatable way to catch the class of problem, not the instance.

| The other playbooks catch | This playbook catches |
|--------------------------|----------------------|
| Does the code match the spec? | Is the spec complete enough to code from? |
| Does the UI render correctly? | Are all states (empty, loading, error, partial) described? |
| Does the daemon survive a crash? | Was "what happens on crash?" ever specified? |
| Are the lenses scored ≥4? | Were the acceptance criteria defined before scoring? |

---

## 2. The 8 Spec Traps

Every ambiguous, contradictory, or incomplete spec falls into one of these eight traps.

### Trap 1: Assumed Happy Path Only

**Pattern:** The spec describes what happens when everything works. Nothing about what happens when it doesn't.

| Example | What was specified | What was missing |
|---------|-------------------|-----------------|
| Watch daemon | "Polls registered agents every N seconds" | What happens when the daemon crashes? When the terminal closes? When the user runs it twice? When the DB is corrupted? |
| Dashboard cards | "Shows agent status and last pulse" | What does a card show when there's no pulse data? When the daemon is dead? During the first 30 seconds after install? |
| Feature lock | "Pro tiles show upgrade CTA" | What happens when the API endpoint for upgrades is unreachable? When the user is on a free plan and clicks? After upgrade—do tiles unlock in real-time or after refresh? |

**Detection:** Run the spec through this litmus test:

```
☐ For every "happy path" described, is there a corresponding failure path?
☐ Does the spec describe what happens on FIRST LOAD?
☐ Does the spec describe what happens on EMPTY STATE?
☐ Does the spec describe what happens on ERROR?
☐ Does the spec describe what happens on PARTIAL DATA?
☐ Does the spec describe what happens on TIMEOUT?
```

**Fix pattern:** Every feature specification must include a section titled **"States & Edge Cases"** that enumerates at minimum: success, empty, loading, error, partial, stale, and timeout.

### Trap 2: Visuals Described But Not States

**Pattern:** The mockup shows a perfect-looking screenshot. The spec lists visual elements. Neither describes how those elements change over time.

| Example | Mockup shows | What's missing |
|---------|-------------|----------------|
| Agent card | Green status dot, token bar, "12s ago" | What colour is the dot when the agent hasn't been seen in 12 hours? What's the animation when status transitions from green to red? Does the token bar animate on update or snap? |
| Drift chart | 7-point line chart with up/down trends | Is the chart interactive (tooltip on hover?) Does it auto-scroll to latest data? What does "no data" look like? |
| Pathway map | 86 nodes, 277 edges, filters | What happens when filters produce zero visible edges? Does the graph re-layout or stay frozen? Are nodes draggable? |

**Detection:**

```
☐ For every visual element in the mockup, does the spec describe its full state machine?
☐ What does this element look like at t=0 (first load)?
☐ What does it look like at t=30s (data arrives)?
☐ What does it look like at t=5min (data goes stale)?
☐ What does it look like at t=∞ (data never arrives)?
```

**Fix pattern:** Add a **Visual State Machine** section to every feature spec that lists all visual states for each mockup element, with screenshots or descriptions for each state.

### Trap 3: Lifecycle Not Specified

**Pattern:** The spec describes what a component does at steady state. Nothing about what happens when it starts, stops, crashes, restarts, or faces a stale condition.

| Example | What was specified | What was missing |
|---------|-------------------|-----------------|
| Watch daemon | "Polls registered agents every 30s" | Start-up behaviour (no data yet), crash behaviour, restart after failure, cleanup of stale state |
| Agent card | "Shows agent status" | Initial load state, stale data indicator, transition from stale→fresh, error state |

**Lifecycle coverage checklist:**

```
☐ Start: What happens on first load / first run?
☐ Run: What happens at steady state?
☐ Update: What happens when data transitions (empty→present→stale→fresh)?
☐ Crash: What happens on failure — retry? graceful degradation? alert?
☐ Reboot: What happens after a crash — resume? reset? rebuild from scratch?
☐ Cleanup: What happens on close / unmount — persist? discard? notify?
☐ Stale detection: How is staleness measured? What triggers re-fetch?
```

**Fix pattern:** Every lifecycle-bearing component must enumerate the full lifecycle matrix.

### Trap 4: No Success Metrics

**Pattern:** The spec says "the feature should work" or "improve performance." No quantitative way to tell if it succeeded.

| Example | What was specified | What was missing |
|---------|-------------------|-----------------|
| Watch daemon | "Monitor registered agents" | How fresh must pulse data be? What's the acceptable age threshold? How fast must failure be detected? |
| Dashboard | "Show agent health" | What's the definition of "healthy"? What's the target uptime? What's the acceptable data staleness window? |

**Fix pattern:** Every feature must have ≥1 quantitative success metric, including: threshold, measurement method, and pass/fail condition.

### Trap 5: Constraints Not Called Out

**Pattern:** The spec assumes a single environment (macOS, single-user, always-on). The deployment reality includes Windows, multi-instance, first-time setup, or concurrent users.

| Example | What was assumed | Real constraint |
|---------|-----------------|----------------|
| Watch daemon | POSIX processes | Windows has no `os.fork()` — must use `DETACHED_PROCESS` or `multiprocessing` |
| Dashboard | Always running | What happens on first install? No data yet. What happens after 30 days of uptime? |
| Agent list | Fixed set | What happens when a new agent is registered mid-session? |

**Fix pattern:** Maintain a **Constraints Register** — hard constraints (must work) and soft constraints (nice to have), each with a verifiable test.

**Shared-mode constraint example:**
| Constraint | Type | Verifiable test |
|-----------|------|----------------|
| Multiple instances write to same SQLite | Hard | WAL mode enabled, concurrent inserts don't block |
| Instance identity per pulse | Hard | `instance_id` column in pulse_log populated per daemon |
| Shared path must be writable | Hard | Write-test on server start; fall back to local mode if unwritable |
| Network share latency < 500ms | Soft | Dashboard response time with remote DB path |
| No telemetry cross-contamination | Hard | Each instance uses its own opt-in file, not the shared DB |

**Scale constraint example (100+ agents):**
| Constraint | Type | Verifiable test |
|-----------|------|----------------|
| Agent list renders at 100+ without timeout | Hard | `/api/agents?page=1&per_page=25` responds <1.5s with 100 synthetic agents |
| Search/filter response < 300ms | Hard | Filter by status: `/api/agents?status=alive` responds <300ms |
| Pagination controls hidden when <25 agents | Hard | 0 or 1 agent → no pagination widget in HTML |
| No search bar when 0 agents | Hard | `/api/agents?q=` returns empty state without search UI |
| Default pagination: 25 per page | Hard | `per_page` default is 25, configurable via query param |

### Trap 6: Contradictory Cross-References

**Pattern:** The spec says X in §3.7, says contradictory Y in §15. Both are correct independently. Together, they're impossible.

| Example | Where | What it says |
|---------|------|-------------|
| Master plan §3.7 vs §15 | Auto-heal for Free vs Pro | §3.7 says "Free agents auto-heal after 3 missed pulses." §15 says "Auto-heal is a Pro-only feature." |

**Detection:** For every cross-reference, verify both sides agree. If they don't, the contradiction must be resolved before any code is written.

**Fix pattern:** Every spec document must have a **Cross-Reference Verification** pass before entering implementation.

### Trap 7: Feature Status Without Layer Decomposition

**Pattern:** A feature is tracked as a single row in the spec or master plan: "Push Alerts: ✅ Live." But only the backend is done — the dashboard UI doesn't exist. Anyone reading the plan assumes the feature is fully user-facing. The single status conceals a two-layer gap.

**Real example (ObserveCo, 2026-06-08):** Master plan showed Push Alerts and Auto-Heal as ✅ Live. Audit revealed backends were complete but no dashboard UI existed. Users couldn't configure or view these features.

**Detection:** For every feature row in a spec or plan, ask: "Can this feature be ✅ Live in backend but ❌ Not built in dashboard?" If yes, the feature must be tracked with a two-part status or split rows.

**Fix pattern:** Every feature that touches the UI must have a two-part status in the plan: `Backend: ✅ / Dashboard: ✅`. A feature is only "✅ Live" when BOTH are verified complete.

### Trap 8: First-Run State Not Specified

**Pattern:** The spec describes what the dashboard looks like with 15 agents and 6 months of data. Nothing describes what it looks like on first launch with zero agents, zero pulses, and an empty database. The first-run user sees a blank page and interprets it as "broken" not "empty."

**Real example (ObserveCo, 2026-06-08):** Onboarding overlay blocked navigation tabs on fresh install. Empty states showed misleading "Learning..." labels for metrics that had no data source configured. All described in the Layer F audit — but the spec never required a first-run section.

**Detection:**
1. Every user-facing spec section must include a **First-Run** subsection: "What does this look like with zero data?"
2. If the spec says "the agent card shows error counts" without describing what it shows on first launch (no agents, no errors), the spec is incomplete
3. Check: is the onboarding flow described? What about the state after onboarding but before any agent is added?

**Fix pattern:** Add a "First-Run" row to every feature's state matrix. At minimum: empty database, first login, first agent added, first error received. These states are as important as the happy path.

---

## 3. The Pre-Spec Protocol: Spec Hardening Phase

**Before ANY feature enters the coding pipeline, run this protocol. It takes 15 minutes and saves 4+ hours of rework.**

### 3.1 Step 1: Requirements Decision Record (RDR)

Every feature that reaches a developer must start with an RDR.

```
REQUIREMENTS DECISION RECORD — [FEATURE NAME]

Problem: [what are we solving?]
Solution sketch: [1-2 sentence description]
Key constraint: [the one thing that MUST be true]
Success metric: [quantitative — how do we know it's done?]

States explicitly specified:
☐ Happy path
☐ Empty state
☐ Loading state
☐ Error state
☐ Partial data state
☐ Stale data state
☐ Timeout state
☐ Degraded state

Lifecycle specified:
☐ Start
☐ Run (steady state)
☐ Crash
☐ Reboot / Resume
☐ Cleanup
☐ Stale detection

Cross-references verified:
☐ All §X references checked for agreement
```

### 3.2 Step 2: State Coverage Matrix

For EVERY user story, expand it into a state matrix:

```
Story: [paste user story]
Element: [the visual element or component]

State      | Visual   | Behaviour          | Data condition
-----------|----------|--------------------|---------------
Success    | [mockup] | [normal flow]      | Data present, fresh
Empty      | [desc]   | [placeholder text] | No data exists
Loading    | [desc]   | [spinner/skeleton] | Data being fetched
Error      | [desc]   | [retry/alert]      | API failure
Partial    | [desc]   | [graceful degrade] | Some fields populated
Stale      | [desc]   | [refresh banner]   | Data older than threshold
Timeout    | [desc]   | [timeout message]  | API didn't respond
Degraded   | [desc]   | [reduced function] | Partial system outage
```

**Minimum 4 states per story** (success, empty, loading, error). Infrastructure features add: start, run, crash, reboot, stale.

### 3.3 Step 3: Mockup Translation Checklist

Every mockup must be translated to spec text:

```
☐ Every mockup section has a matching spec section
☐ Section COUNT matches (mockup has 4 sections → spec must specify 4 sections)
☐ Visual hierarchy matches (what's prominent in mockup is prominent in spec)
☐ Empty/loading states are shown in mockup or described in spec
☐ Interactive elements listed with their behaviours
```

### 3.4 Step 4: Constraints Register

```
Feature: [name]

Hard Constraints (MUST):
☐ [constraint 1] — verifiable via [method]
☐ [constraint 2] — verifiable via [method]

Soft Constraints (SHOULD):
☐ [constraint 1] — trade-off acceptable if [condition]

Environment blindspots checked:
☐ Cross-platform (POSIX + Windows)
☐ Multi-instance (can two run at once?)
☐ First-time user (what happens on fresh install?)
☐ Long-running (what happens after 30 days?)
☐ Resource exhaustion (memory, disk, ports)
```

---

## 4. The RDR Template (Compact)

```
RDR: [Short title]

Problem:
What the user needs that they don't have today.

Solution:
One-paragraph description of the proposed solution.

Key constraint:
The single non-negotiable requirement.

Success metric:
How we measure success. Must be quantitative.

Edge states accounted for:
☐ Loading, ☐ Empty, ☐ Error, ☐ Partial, ☐ Stale, ☐ Timeout, ☐ Degraded

Lifecycle coverage:
☐ Start, ☐ Run, ☐ Crash, ☐ Reboot, ☐ Cleanup, ☐ Stale detection

Cross-references verified:
☐ Yes (all linked docs checked for agreement)

--- RDR APPROVED ---
```

---

## 5. Mockup Translation Protocol

When building from a mockup:

1. Count the sections in the mockup — this is the MINIMUM section count for the spec
2. For each section, describe:
   - What it shows when data arrives (success)
   - What it shows before data arrives (loading)
   - What it shows when data is empty (empty)
   - What it shows when API fails (error)
3. Cross-reference each mockup section against the spec's section list
4. If section counts mismatch, the spec is incomplete

---

## 6. The Golden Gate — Pre-Implementation Spec Gate

Before ANY feature enters implementation:

```
□ 1. REQUIREMENTS DECISION RECORD: Written, approved, all 6 traps clean
     Pass: YES / NO

□ 2. STATE ENUMERATION: Every visual element has ≥4 states
     (success, empty, loading, error minimum)
     Pass: YES / NO

□ 3. LIFECYCLE SPECIFIED: Start, run, crash, reboot, cleanup, stale detection
     ALL answered
     Pass: YES / NO

□ 4. SUCCESS METRICS: At least 1 quantitative metric per feature
     Pass: YES / NO

□ 5. CONSTRAINTS REGISTER: All hard constraints documented
     Pass: YES / NO

□ 6. MOCKUP TRANSLATION: Every mockup section has a spec counterpart
     Section count matches
     Pass: YES / NO

□ 7. CROSS-REFERENCES VERIFIED: All links point to current documents
     Pass: YES / NO

□ 8. CONSISTENCY CHECK: No contradictory statements between spec sections
     Pass: YES / NO

□ 9. ACCEPTANCE CRITERIA: Defined, pass/fail conditions stated
     Pass: YES / NO

□ 10. TIER MAPPING: What's Free vs Pro, no ambiguity
      Pass: YES / NO
```

**If any NO, the spec must be revised before any developer touches it.**

---

## 7. Lessons Learned Log

### 2026-05-30 — Initial Creation

| What was missing | What happened | Trap | Fix applied |
|-----------------|---------------|------|-------------|
| Lifecycle not specified for watch daemon | Thread-in-dashboard shipped → rejected → 4 rework cycles | Trap 3 | Added §2 Trap 3 + lifecycle section template |
| Only happy path for pulse data | 4 other tables had no writer → coverage gap | Trap 1 | Added state enumeration protocol |
| No success metrics for "agent healthy" | Couldn't measure if watch daemon was working | Trap 4 | Added success criteria template |
| Constraints not called out (cross-platform, lifecycle decoupling) | POSIX-only code, coupled lifecycle | Trap 5 | Added constraints register template |
| Contradictory between master plan §3.7 and §15 | Free vs Pro auto-heal ambiguity | Trap 6 | Added cross-reference verification protocol |

### 2026-05-31 — Standardization Pass

| What was missing | What happened | Trap | Fix applied |
|-----------------|---------------|------|-------------|
| Playbook version inconsistent across system | Version table had stale data — coding-fidelity showed 2.0, other docs had no version | Trap 6 | Added Version History table to all 7 docs. All bumped to 2.1. |
| Golden Gate naming not uniform | UX had "Pre-Ship Gate", agent-governance had "Session Discipline" | Trap 2 — naming confusion | Normalized all to "Golden Gate" everywhere. agent-governance §9 renamed, UX §4.1 renamed. |
| No cross-ref to Playbook Inventory | Files that said "the playbooks" had stale counts | Trap 6 — contradictory refs | Added cross-reference to Playbook Inventory (§Playbook Inventory in this file) from all 7 docs. |

---

## 8. Expert Prompts for Hound

### Prompt A: Spec Hardening (run before any implementation)

```
You are now in 100x Spec-Hardening Mode.

Given the following requirement: [paste ticket/spec/feature request]

1. Run the FULL §2 Spec Traps analysis:
   - Trap 1 (happy path only): enumerate all missing states
   - Trap 2 (visuals without states): enumerate all missing visual states
   - Trap 3 (lifecycle not specified): enumerate all missing lifecycle answers
   - Trap 4 (no success metrics): propose at least 1 measurable metric
   - Trap 5 (constraints not called out): list all hard constraints
   - Trap 6 (contradictory refs): verify every cross-reference

2. Write the COMPLETE Requirements Decision Record (§3.4) filled in.

3. Expand the largest user story into a FULL state matrix (§3.2):
   success, empty, loading, error, partial, stale, timeout, degraded

4. Run the full mockup translation checklist (§3.3).

5. Output all 10 Golden Gate items (§6) with PASS / FAIL / NEEDS WORK.

Do not write any code until I say "SPEC APPROVED."
```

### Prompt B: State Audit (run after spec is hardened, before code)

```
Run a complete state-coverage audit on the following feature: [feature]

1. For every visual element:
   - What happens when data arrives? (success)
   - What happens when data is empty? (empty)
   - What happens when API is loading? (loading)
   - What happens when API fails? (error)
   - What happens when data is partial? (partial)
   - What happens when data is stale? (stale)
   - What happens when request times out? (timeout)
   - What happens when system is degraded? (degraded)

2. Output as a matrix: element × state = description.

3. Flag any element with fewer than 4 states as INCOMPLETE.

4. Verify the constraints register against the feature spec.
```

### Prompt C: Cross-Reference Audit

```
Given the feature specification at [path]:

Find every internal cross-reference (§X, §Y, line refs, link-based refs).
For each pair, verify both sides agree.

Output:
- [PATH A] §X → [PATH B] §Y: AGREES — brief on why
- [PATH A] §X → [PATH B] §Y: CONTRADICTS — describe the contradiction

If any CONTRADICTS, the spec must be revised before coding.
```

---

## 9. State Coverage Matrix (Reference Template)

```
| Element | Success | Empty | Loading | Error |
|---------|---------|-------|---------|-------|
| [name]  | [desc]  | [desc] | [desc]  | [desc] |

Additional states: partial, stale, timeout, degraded
```

---

## Appendix A: The 6 Spec Traps — Quick Reference Card

```
Trap 1: Happy path only — missing all failure states
Trap 2: Visuals without states — no loading/empty/error per element
Trap 3: No lifecycle — start/crash/reboot/cleanup unspecified
Trap 4: No success metrics — can't tell if it works
Trap 5: Hidden constraints — assumes single environment
Trap 6: Contradictory refs — §X says one thing, §Y says opposite
Trap 7: Payment flow state coverage — success ≠ done (session ID, encryption, trial start all independent failure points)
Trap 8: Tier-specific empty states — Free vs Pro show different content, spec must define both
```

---

## Appendix B: Cross-Reference Verification Quick Reference

```
Before marking spec as complete:
☐ Every §X, §Y reference points to a real section
☐ Every linked document is current (check Version line)
☐ No contradictory statements between sections
☐ Free vs Pro tier mapping is consistent
```

| As referenced in §X | Stale cross-reference risk | Open §X. Verify agreement. |
|--------------------|--------------------------|---------------------------|

---

## Lessons Learned

| Date | Project | What happened | Root cause | Trap | Fix applied |
|------|---------|---------------|-----------|------|-------------|
| 2026-06-09 | ObserveCo | Stripe payment success → Pro not activated — 3 independent bugs (wrong session ID, encryption key mismatch, missing start_trial()) | Spec said "payment flow" but didn't enumerate sub-states: session creation, encryption, trial start | Trap 7 | Added payment flow state machine to spec template |
| 2026-06-09 | ObserveCo | Free tier shows "Subscribe $9/mo" alongside "Cancel Trial" — confusing dual-state UI | Spec only defined happy path for paid users, not Free tier with trial active | Trap 8 | Added tier-specific empty state requirement to spec template |

*"A perfect implementation of an ambiguous spec is still wrong." This playbook catches the wrongness before a single line of code is written.*
