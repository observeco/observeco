# AI Agent Governance & Session Mastery Playbook

**Product:** ObserveCo development workflow (and all future agent-driven projects)
**Status:** Living — update as lessons accumulate
**Version:** 3.2 — 2026-06-10
**Version History:**
| Version | Date | What changed |
|---------|------|-------------|
| 1.0 | 2026-05-30 | Initial creation — 5 session failure modes, priming protocol, HOUND.md mandate, tool-use guardrails, session discipline gate |
| 3.1 | 2026-05-31 | Standardization pass: all 7 playbooks bumped to v3.1. Fixed stale playbook-count references. Confirmed cross-references to Playbook Inventory (requirements-fidelity-playbook.md §Playbook Inventory) and Layer F First-Run Audit (master-fidelity-gate.md §2 Layer F). Removed stray empty FILE tags. |
| 2.1 | 2026-05-31 | Standardization pass: uniform versioning, cross-ref to Playbook Inventory, rename "Session Discipline" → "Golden Gate" |
| 3.2 | 2026-06-10 | Added Priming Item 6 (Payment Pipeline Priming — verify payment flow end-to-end before marking feature done). Added Lessons Learned section with 1 entry. |

**Source:** Real failure — 4 rework cycles on the watch daemon because the agent (me) didn't manage its own session discipline: no checkpoint on the first bad idea, no mandatory re-prime after context drift, no tool-use guardrails.

This playbook is **meta**: it governs how agents use the other nine playbooks (requirements-fidelity, coding-fidelity, UX-testing, system-design-testing, UI-testing, spec-gated-workflow, orchestration-anti-patterns, security-stride, and the evolution meta-playbook). Without this, even perfect playbooks get undermined by context pollution, over-confidence loops, and 9-minute streaming drift.

---

## 1. Thesis

**The agent is the most expensive dependency in the system. It must be managed with the same discipline as a production daemon.**

Every failure in a 60+ minute AI coding session traces to one root: the agent's context window becomes polluted, its confidence exceeds its accuracy, and it starts making decisions based on what it *assumes* rather than what it *verified*. The code compiles. The tests pass. The architecture is wrong.

This document is not a style guide for writing code. It is an **agent operating manual** — a repeatable way to keep the AI driver focused, honest, and effective across long sessions.

---

## 2. The 5 Session Failure Modes

| # | Failure mode | What it looks like | Root cause |
|---|-------------|-------------------|------------|
| 1 | **Context drift** | Agent starts quoting old versions of files, misremembers previous decisions, hallucinates functions that don't exist | >45 minutes without re-priming; agent confuses its own output with reality |
| 2 | **Over-confidence loop** | Agent outputs "All checks pass" without actually running them; skips verification because "the fix was trivial" | No mandatory verification step; agent scores its own homework |
| 3 | **Premature narrowing** | Agent picks the first viable solution and spends 4 cycles optimising it before discovering the architecture is wrong | No forced "alternatives considered" step before implementation |
| 4 | **Verification autonomy failure** | Agent declares victory based on compile-time checks alone; never tests at runtime | No mandate to "never assume, always screenshot + DOM dump before claiming fixed" |
| 5 | **Tool-use blindness** | Agent edits files but never reads them back; calls APIs but never checks the response; asserts success without evidence | No guardrail requiring every side-effect to produce a verifiable trace |

---

## 3. Session Priming Protocol

### 3.1 The Prime Block

Every new session — and every session that exceeds 45 minutes without a checkpoint — must start with:

```
═══════════════════════════════════════════════════
SESSION PRIME — [DATE] [TIME]
═══════════════════════════════════════════════════

Active priorities (from MISSIONS.json):
1. [priority 1]
2. [priority 2]
3. [priority 3]

|Loaded playbooks:
□ requirements-fidelity-playbook.md — spec hardening first
□ coding-fidelity-playbook.md — code matches spec
□ ux-testing-playbook.md — human lens
□ system-design-testing-playbook.md — architecture lens
□ ui-testing-playbook.md — UI interaction lens
□ agent-governance-playbook.md — session discipline (this file)
□ master-fidelity-gate.md — integration gate
□ spec-gated-workflow-playbook.md — 4-phase spec gate
□ orchestration-anti-patterns-playbook.md — multi-agent governance
□ security-stride-playbook.md — security threat model

Session discipline:
□ I will NOT propose a solution before checking all 10 playbooks
□ I will NOT skip verification ("All checks pass" is not proof)
□ I will NOT accept my own first idea without considering alternatives
□ I WILL output screenshots + DOM dumps before claiming a fix
□ I WILL checkpoint every 30 minutes or 5 patches (whichever comes first)
□ I WILL ask for human sign-off before merging ANY infrastructure change
□ I WILL NOT claim a feature is "done" without verifying which layers are complete (backend? dashboard? both?)
□ I WILL be precise in status reporting: "Push Alerts backend is done; dashboard UI remains" not "Push Alerts is done"
□ I WILL verify payment flow end-to-end before marking any paid feature done — session ID mapping, encryption key round-trip, trial/Pro activation call. Each sub-state independently tested.
```

### 3.2 The HOUND.md Mandate

**HOUND.md** (or the equivalent agent-priming file) must contain:

```markdown
# HOUND.md — Agent Operating Rules

## Always Load at Session Start
1. requirements-fidelity-playbook.md — §2 Spec Traps + §3 Pre-Spec Protocol
2. coding-fidelity-playbook.md — §2 5 Pillars + §8 Golden Gate
3. ux-testing-playbook.md — §2 5 Human Layers + §7 Golden Gate
4. system-design-testing-playbook.md — §2 Pre-Code Protocol + §5 9 Lenses
5. ui-testing-playbook.md — §2 UI Interaction Layers + §7 Golden Gate
6. master-fidelity-gate.md — §2 Combined Checklist (all layers)
7. spec-gated-workflow-playbook.md — §3.1 Surface Assumptions + §3.2 Write the Spec
8. orchestration-anti-patterns-playbook.md — §3 Endorsed Patterns + §4 Anti-Patterns
9. security-stride-playbook.md — §2 STRIDE Threat Model + §3 3-Tier Boundary

## Before Every Patch
- Run cross-ref-verify.sh to check spec references are current
- Run data-pipeline-audit.sh to check writer/reader completeness
- Check: does this change affect pulse_log, chisel_trims, chisel_drift,
  clawforge_garden, pathway_*, or circuit_breakers? If yes, run the
  full §4 lifecycle test suite from system-design-testing-playbook

## Before Marking "Done"
1. Screenshot the changed UI (full page, no cropping)
2. Dump the relevant DOM sections
3. Capture the API response (curl the endpoint)
4. Run the playbook-specific Golden Gate
5. Only then: output "Ready for human review"

## Hard Rules
- Never use `"""(triple-quote)` without `f` prefix for HTML strings
- Never use `os.fork()` without a `sys.platform == "win32"` fallback
- Never assume a heartbeat file proves a process is alive
- Every `SELECT` must have a matching `INSERT` somewhere
- Every daemon must have start/stop/status
```

---

## 4. Context-Drift Prevention

### 4.1 The 45-Minute Rule

**Rule:** Every 45 minutes, force a session reset + re-prime. This is non-negotiable.

```markdown
╔══════════════════════════════════════════════════╗
║           45-MINUTE CHECKPOINT                   ║
╠══════════════════════════════════════════════════╣
║ Time elapsed: 45 min                            ║
║ Current context: [what we've been doing]         ║
║                                                  ║
║ Actions:                                         ║
║ □ Save all changes (git commit or stash)         ║
║ □ Export decision log (what was decided, why)    ║
║ □ Re-prime with all 10 playbooks                  ║
║ □ Confirm: are we still working on the right     ║
║   thing, or did the spec drift?                  ║
║ □ Get human sign-off before continuing            ║
╚══════════════════════════════════════════════════╝
```

### 4.2 Context Reset Protocol

When context drift is detected (or suspected):

```
1. STOP all work in progress
2. Export current state:
   - git diff (pending changes)
   - Decision log (key decisions this session, with rationale)
   - File inventory (what was created/modified)
3. Write session summary to .hermes/session-log/YYYY-MM-DD-HHMM.md
4. Start NEW session with fresh prime block
5. Load the session log as context
6. Resume from last checkpoint
```

### 4.3 Drift Detection Checklist

Watch for these signs that the agent is drifting:

```
☐ Agent starts quoting file contents that don't match the current state
☐ Agent says "as I mentioned earlier" but the earlier point is misremembered
☐ Agent proposes solutions that were already rejected
☐ Agent's confidence increases while output quality decreases
☐ Agent stops running verification tools and just asserts "all good"
☐ Agent says "this is simple" about something that wasn't simple 30 minutes ago
```

---

## 5. Checkpoint Discipline

### 5.1 The 5-Patch / 30-Minute Rule

**Rule:** Every 5 patches OR every 30 minutes (whichever comes first), force a mandatory human-sign-off checkpoint.

```
Checkpoint threshold reached:
  □ 5 patches written, OR
  □ 30 minutes elapsed

Before requesting human review:
  □ Run playbook-specific Golden Gate for this change
  □ Run data-pipeline-audit.sh (if infrastructure)
  □ Run cross-ref-verify.sh (if spec references changed)
  □ Screenshot the output (if UI)
  □ Dump the relevant API responses (if backend)
  □ Write decision log for this checkpoint

Human must sign off before:
  □ More patches are written
  □ The next checkpoint begins
  □ Any infrastructure change is deployed
```

### 5.2 The Decision Log

Every checkpoint must produce a log entry:

```markdown
## Checkpoint: [YYYY-MM-DD HH:MM]

### What was done
[patch descriptions, files changed]

### What was verified
[what gates passed, what screenshots look like]

### What was decided
[key decisions with rationale]

### What is uncertain
[open questions, trade-offs deferred]

### Next steps
[what the next block of work is]
```

### 5.3 The Revert Threshold

**Rule:** If a patch requires 3+ rework iterations to get right, revert it and restart with the upstream playbook (requirements → coding → UX → system — in that order).

```
Revert threshold activated:
  3+ rework iterations on the same patch

Protocol:
  1. Revert the patch (git revert)
  2. Re-prime with requirements-fidelity-playbook.md
  3. Was the spec complete? If no: fix spec first.
  4. Was the architecture considered? If no: run system-design §2 pre-code protocol.
  5. Was the implementation the first idea? If yes: enumerate alternatives.
  6. Only then: re-implement.
```

---

## 6. Tool-Use Guardrails

### 6.1 The "Never Assume" Rule

**Rule:** Every tool call that modifies external state must be followed by a read-back verification BEFORE the next operation.

```python
# BAD: write file → continue without verification
write_file(path, content)
# ... 5 more operations ...
# → Bug discovered 10 minutes later

# GOOD: write file → read it back → verify before next step
write_file(path, content)
read_back = read_file(path)
assert content in read_back, "Write-verify mismatch"
```

| Operation | Must verify by | Example |
|-----------|---------------|---------|
| `write_file` | `read_file` the same file | Content matches |
| `patch` | `read_file` the file | Patch applied correctly |
| HTML output | Browser load + screenshot | Renders correctly, no JS errors |
| API endpoint | `curl` the endpoint | Returns 200, response shape matches |
| Daemon start | `status()` check | PID file exists, process alive |
| DB write | `SELECT` from the table | Row inserted with correct timestamp |
| Git commit | `git log --oneline -1` | Message correct, files match |
| Subprocess spawn | Process list check + heartbeat | Alive on expected interval |

### 6.2 The Screenshot Mandate

**Rule:** For any UI change, the agent MUST output a screenshot before claiming the fix is complete.

```
Mandatory before "done":
  □ Full-page screenshot of the changed view
  □ Console output (browser_console()) — zero JS errors
  □ API response shape (curl the relevant endpoint)
  □ Before/after comparison (if structural change)
```

### 6.3 The "Show Your Work" Rule

**Rule:** Every assertion of "it works" must be accompanied by the evidence the agent used to determine that.

```
BAD:  "All checks pass."
GOOD: "Test output: 12/12 lifecycle tests pass. 
       API response: {'status': 'running', 'pid': 58701}. 
       Screenshot: dashboard shows live pulses at 12s ago. 
       Console: zero errors."
```

---

## 7. Multi-Agent Handoff Rules

### 7.1 When to Specialise

| Task type | Spawn a specialised agent for | What to give them |
|-----------|------------------------------|-------------------|
| UI fidelity check | UX-only subagent | ux-testing-playbook.md + mockup URL |
| Architecture critic | System-only subagent | system-design-testing-playbook.md + ADR |
| Spec hardener | Requirements-only subagent | requirements-fidelity-playbook.md + original ticket |
| CI gate runner | Gate-only subagent | all 10 playbooks + feature name |
| Code review | Coding-fidelity-only agent | coding-fidelity-playbook.md + PR diff |
| Spec-gated workflow | Spec-hardening subagent | spec-gated-workflow-playbook.md + feature spec |
| Orchestration critic | Multi-agent governance subagent | orchestration-anti-patterns-playbook.md + agent topology |
| Security reviewer | Threat-model subagent | security-stride-playbook.md + system boundary |

### 7.2 Handoff Protocol

```markdown
## Handoff: [Task]

### Context for subagent
- What we're building: [description]
- What playbook to use: [which one]
- What to verify: [specific checklist items]
- Current state: [files, configs, running processes]

### What NOT to do
- Do not write code unless explicitly asked
- Do not propose alternatives unless explicitly asked
- Do not modify files — output findings only

### Output format
[ ]
[ ]
[ ]
```

### 7.3 The "Second Pair of Eyes" Rule

**Rule:** For any infrastructure change, system architecture decision, or spec-hardening task, a second agent (or same agent in a fresh session) must review the output before human review.

```
Mandatory second review for:
  □ Any daemon lifecycle change
  □ Any cross-platform decision
  □ Any database schema change
  □ Any spec that defines constraints
  □ Any ADR with trade-offs

Reviewer instructions:
  1. Start fresh session (no context from original)
  2. Load only: the playbook(s) + the output being reviewed
  3. Apply playbook Golden Gate as if this were new work
  4. Report: PASS with evidence / FAIL with evidence
```

---

## 8. Agent Performance Telemetry

### 8.1 What to Track

Every session should log:

| Metric | How to measure | Target | What it reveals |
|--------|---------------|--------|-----------------|
| Rework cycles | Count of patches rejected or reverted per feature | <2 | Was the spec complete? Was the architecture considered? |
| Time to first human rejection | Minutes from session start to first "this is wrong" | >20 min | Was the pre-code protocol skipped? |
| Verification gaps | Number of "I assert it works" without evidence | 0 | Is the agent following the "show your work" rule? |
| Checkpoint compliance | Checkpoints taken / checkpoints required | 100% | Is session discipline being followed? |
| Playbook bypasses | Count of decisions made without checking the relevant playbook | 0 | Are the playbooks being used as process or reference? |

### 8.2 Session Log Template

```markdown
## Session Log — [YYYY-MM-DD HH:MM → HH:MM]

### Feature
[what was built]

### Playbooks Applied
- [ ] requirements-fidelity-playbook.md — spec hardened? Y/N
- [ ] coding-fidelity-playbook.md — code fidelity gate? Y/N
- [ ] ux-testing-playbook.md — human lens? Y/N
- [ ] system-design-testing-playbook.md — architecture lens? Y/N

### Checkpoints
[ ] 00:30 — [state / sign-off]
[ ] 01:00 — [state / sign-off]
[ ] 01:30 — [state / sign-off]

### Rework
[ ] Iterations: ___
[ ] Root cause of each iteration:
[ ] Was the root cause traced to a playbook gap?

### Verification Gaps
[ ] Number of unfounded assertions: ___
[ ] Evidence provided for each? Y/N

### Playbook Gaps Identified
[ ] Any bug that reached the user that wasn't caught by playbooks?
[ ] If yes: which playbook section needs updating?

### Overall
[ ] Time to "done": ___
[ ] Rework cycles: ___
[ ] Verdict: playbooks worked / playbooks need update (linked to Lessons Learned)
```

---

## 9. The Golden Gate

Before ending ANY coding session:

```
□ 1. ALL patches committed or stashed with messages
□ 2. Decision log written for every checkpoint
□ 3. Session log from §8.2 filled in
□ 4. Any playbook gaps identified and linked to future update
□ 5. No "I'll fix it tomorrow" — either fixed or documented as decision log
□ 6. Human sign-off on last checkpoint
□ 7. If UI changed: screenshot archived
□ 8. If infrastructure changed: lifecycle tests pass
□ 9. Context not drifting? (re-read first 10 messages — does narrative match?)
□ 10. If session >4 hours: forced restart recommended
```

---

## 10. Lessons Learned Log

### 2026-05-30 — Initial Creation

| What was missing | What happened | Session discipline gap | Fix applied |
|-----------------|---------------|-----------------------|-------------|
| No 45-minute rule | 2-hour session → context drift → agent re-proposing rejected ideas | §3 | Added 45-minute checkpoint mandate |
| No "alternatives considered" step | First viable idea shipped without considering threads vs daemon | §3.1 | Added "I will NOT accept my own first idea" to prime block |
| No tool-use guardrails | Patches applied but not read back → discovered after 3 patches | §6 | Added "every write must be read back" table |
| No evidence mandate | "All checks pass" delivered without actual test output | §6.3 | Added "Show Your Work" rule |
| No session log | No record of rework cycles, root causes, or playbook gaps | §8 | Added telemetry + session log |

### 2026-05-31 — Standardization Pass

| What was missing | What happened | Session discipline gap | Fix applied |
|-----------------|---------------|-----------------------|-------------|
| §9 heading "Session Discipline" — not consistent with "Golden Gate" used in other 6 playbooks | Naming inconsistency across system | §9 | Renamed to "## 9. The Golden Gate" — matches coding-fidelity, ux, system-design, master-gate conventions. |
| No Version History table — inline version string only | Missing metadata | §8 | Added Version History table with 1.0 → 2.1 entries. |
| No cross-reference to Playbook Inventory | Cross-reference gap | §3.2 | Added reference to requirements-fidelity-playbook.md §Playbook Inventory. |

---

## Appendix A: Quick Reference — The 10-Second Session Health Check

1. When did I last re-prime? (>45 min ago → re-prime now)
2. Have I been verifying or assuming? (every "it works" without evidence)
3. Is this the first solution I thought of? (if yes: enumerate alternatives)
4. Have I taken a checkpoint? (>30 min or >5 patches → checkpoint now)
5. Is my context drifting? (quoting old file states → reset)

## Appendix B: The "Agent Is Drifting" Tell

| Tell | What it means | Fix |
|------|---------------|-----|
| "As I mentioned earlier" but the earlier mention is wrong | Context drift | Re-prime + checkpoint |
| "This is trivial" | Over-confidence | Force: what could go wrong? |
| "All tests pass" without test output | Verification autonomy failure | Show evidence |
| "Let me just fix one more thing" | No checkpoint discipline | Stop. Checkpoint. Re-prime. |
| "The same approach as before" | Premature narrowing | Force alternatives enumeration |
| [silence + rapid patches] | No read-back verification | Pause. Read. Check. Continue. |
| [no checkpoint in >30 min] | Discipline failure | Stop. Now. |

---

## Lessons Learned

| Date | Project | What happened | Root cause | Gap | Fix applied |
|------|---------|---------------|-----------|------|-------------|
| 2026-06-09 | ObserveCo | Stripe payment success → Pro not activated — 3 independent bugs missed across 3 sessions | No priming item for payment pipeline verification — agent assumed "payment works" without end-to-end verification | Priming Item 6 | Added "verify payment flow end-to-end before marking feature done" to priming block |

*The agent is the most expensive dependency. This playbook governs it with the same rigour we govern our daemons.*
