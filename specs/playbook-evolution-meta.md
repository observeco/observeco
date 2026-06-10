# Playbook Evolution & Self-Improvement Loop — The Meta-Playbook

**Product:** The ObserveCo playbook system itself
**Status:** Living — update as lessons accumulate
**Version:** 3.2 — 2026-06-10
**Version History:**
| Version | Date | What changed |
|---------|------|-------------|
| 1.0 | 2026-05-30 | Initial creation — 3 feedback loops, escape rule, freshness check |
| 3.1 | 2026-05-31 | Standardization pass: all 7 playbooks bumped to v3.1. Fixed stale playbook-count references. Confirmed cross-references to Playbook Inventory (requirements-fidelity-playbook.md §Playbook Inventory) and Layer F First-Run Audit (master-fidelity-gate.md §2 Layer F). Removed stray empty FILE tags. |
| 2.1 | 2026-05-31 | Standardization pass: uniform versioning, cross-ref to Playbook Inventory, standard lessons entry |
| 3.2 | 2026-06-10 | Updated stale playbook count from 7 to 8 (added ui-testing-playbook). Added Lessons Learned section with 1 entry. |

**Source:** Real insight — 5 playbooks exist but nothing ensures they stay alive, accurate, and improving. Sean's feedback: "If a human catches something an AI missed, the playbook was incomplete — update it before fixing the code."

This is the **meta-playbook**. It does not describe how to build features. It describes how to maintain the playbooks that describe how to build features.

---

## 1. Thesis

**If a human catches something the playbooks missed, the playbooks were incomplete — update them before fixing the code.**

This is the single most important rule in the entire playbook system. It means:

1. Every bug escape is a **PLAYBOOK FAILURE** first, a **CODE FAILURE** second.
2. The playbook update is the **PRIMARY deliverable**. The code fix is the **SECONDARY deliverable**.
3. If the same class of bug escapes twice, the playbook system is broken — not just the playbook section.

Without this meta-loop, every playbook converges to irrelevance. It becomes a static document that people stop reading because "it didn't catch the last bug."

---

## 2. Version History Table

Every playbook in the system must have this table at the top of its file:

```markdown
**Version:** X.Y — YYYY-MM-DD
**Version History:**
| Version | Date | What changed |
|---------|------|-------------|
| 1.0 | 2026-05-24 | Initial creation |
| 1.1 | 2026-05-25 | Added §4 error patterns |
| 2.0 | 2026-05-30 | Added 9 lenses, Hound prompts, agent priming |
```

The current system's version table:

| Playbook | Current Version | Latest Update |
|----------|----------------|---------------|
| requirements-fidelity-playbook.md | 2.1 | 2026-05-31 |
| coding-fidelity-playbook.md | 2.1 | 2026-05-31 |
| ux-testing-playbook.md | 2.1 | 2026-05-31 |
| system-design-testing-playbook.md | 2.1 | 2026-05-31 |
| agent-governance-playbook.md | 2.1 | 2026-05-31 |
| master-fidelity-gate.md | 2.1 | 2026-05-31 |
| **this file** | 2.1 | 2026-05-31 |

---

## 3. Escape-Driven Playbook Updates

### 3.1 The Golden Rule (Enforced)

**Rule:** When a bug reaches the user, the protocol is:

```
1. REPRODUCE the bug (screenshot, log, or reproduction steps)
2. IDENTIFY which playbook should have caught it
   - Ambiguous spec? → requirements-fidelity-playbook.md
   - Wrong implementation? → coding-fidelity-playbook.md
   - Bad UX? → ux-testing-playbook.md
   - Wrong architecture? → system-design-testing-playbook.md
   - Bad session discipline? → agent-governance-playbook.md
3. UPDATE the playbook's Lessons Learned with:
   - What happened
   - Which playbook section should have caught it
   - What new check, lens, or trap to add
4. FIX the code
5. VERIFY the playbook now catches this in future: re-run the relevant gate
```

**Order matters:** Playbook update comes BEFORE code fix. If you fix the code first, the playbook update gets skipped.

### 3.2 The Escape Post-Mortem Template

Every bug escape generates a post-mortem that goes into the relevant playbook:

```markdown
### Escape Post-Mortem: [Bug ID or description]

**What the user saw:** [screenshot or reproduction steps]
**What should have happened:** [correct behaviour]
**Which playbook layer:** [requirements / coding / UX / system / governance]
**Which section of that playbook should have caught it:** [§X.Y]
**Why it escaped:** [reason — wasn't in spec? wasn't in checklist? was in checklist but skipped?]
**Was the playbook up to date?** [Y/N - if N, that's the first problem]
**Fix applied to playbook:** [new trap added / new check item / new lens criterion / new session rule]
**Fix applied to code:** [link to PR]
**Verification:** [how we confirmed the playbook now catches this]
```

### 3.3 The Double-Escape Rule

**Rule:** If the same class of bug escapes twice, the playbook system itself is broken — not just a single section.

```
1. Same bug class escapes twice through the same playbook
2. The playbook's LESSONS LEARNED entry was written but wasn't effective
3. Protocol:
   a. Does the Lessons Learned entry actually ADD a new check to the relevant
      checklist/Golden Gate/verification section? Or was it just documentation?
   b. If no new check was added: the escape was documented but not prevented.
      The fix was INCOMPLETE. Add the check now.
   c. If a check was added but still escaped: the check was at the wrong
      fidelity level. Move it higher (requirements → design → code),
      or add a second-layer verification.
```

### 3.4 The "Playbook Fix First" Checklist

When a bug is reported, BEFORE touching any code:

```
☐ 1. Identified which playbook should have caught this
☐ 2. Written the Escape Post-Mortem in that playbook's Lessons Learned
☐ 3. Added a new check to the relevant section
     (new trap in requirements, new lens criterion in system, new
     gate item in master, new priming rule in governance, etc.)
☐ 4. Verified: does the new check fit? Would it have caught this specific bug?
☐ 5. Updated the playbook's Version History table
☐ 6. Only then: fix the code
```

---

## 4. Quarterly Playbook Health Review

### 4.1 What to Review

Every quarter, run the three expert prompts ON THE PLAYBOOKS THEMSELVES:

**Prompt 1: Requirements Self-Hardening (on requirements-fidelity-playbook.md)**
```markdown
You are in 100x Playbook-Health Mode.

Review requirements-fidelity-playbook.md against its own Thesis and §2 Spec Traps:

1. Does the playbook itself have a complete state matrix?
   - What states does a playbook have? (new, updated, stale, contradictory)
   - What happens when a playbook contradicts another playbook?
   - What happens when a playbook references a dead spec?

2. Does the playbook have lifecycle documentation?
   - Who updates it? When?
   - Who verifies it's still accurate?

3. Does it have success metrics?
   - What does "healthy" look like for this playbook?
   - Escape rate <20%? Version updated this quarter? No open gaps?

4. Are constraints documented?
   - Which users is this playbook for? (AI agents? Humans? Both?)
   - What if the playbook becomes too long to prime in one session?

Report: what would you add or change to make the playbook more effective?
```

**Prompt 2: Coding-Fidelity Self-Audit (on coding-fidelity-playbook.md)**
```markdown
Audit coding-fidelity-playbook.md against its own 5 Pillars:

1. Spec Grounding: does the playbook SPEC itself match reality?
   - Are the bug patterns listed still relevant?
   - Are there NEW bug patterns discovered this quarter?

2. Implementation Fidelity: are the Golden Gate items complete?
   - Any item that's been passed without ever being checked?
   - Any item that's irrelevant now?

3. Verification Autonomy: do the test templates still compile?
   - Run the TestClient template — does it still match the current API?

4. Evolution: update the Version History and Lessons Learned.

Report: outdated sections, missing patterns, new traps needed.
```

**Prompt 3: System-Design Self-Audit (on system-design-testing-playbook.md)**
```markdown
Run the FULL §6 Golden Gate on system-design-testing-playbook.md itself:

1. Data pipeline map: what "tables" does this playbook read?
   (Other playbooks, the master plan, actual codebase — are they all current?)

2. Lifecycle tests: does this playbook have a start/stop/status lifecycle?
   - Who starts an update? When?
   - What stops it from growing indefinitely?

3. 9-lens scores for the playbook itself:
   - Lens 1 (Lifecycle): is this playbook being updated independently of the code?
   - Lens 2 (Coverage): does it cover all infrastructure patterns in the codebase?
   - Lens 3 (Crash): what happens when the playbook contradicts itself?
   - Lens 4 (Liveness): how do we know this playbook is still accurate?
   - The rest...

Report: lens scores for the playbook itself. Any <4 needs action.
```

### 4.2 Health Scorecard

| Metric | Current | Target | Trend |
|--------|---------|--------|-------|
| Version age (days since last update) | ___ | <90 | + / = / - |
| Escape rate (last quarter) | ___% | <20% | + / = / - |
| Open playbook gaps (identified, unaddressed) | ___ | <3 | + / = / - |
| Contradictions between playbooks | ___ | 0 | + / = / - |
| % of Lessons Learned that actually added new checks | ___% | 100% | + / = / - |

### 4.3 The "Playbook Has Gone Stale" Trigger

Any of these triggers initiates an immediate playbook review:
- 90+ days since last update
- Escape rate >20% for two consecutive quarters
- A human says "the playbook didn't help with this bug"
- A new platform (Windows, Docker, etc.) is added that the playbook doesn't cover

---

## 5. Version History (This File)

| Version | Date | What changed |
|---------|------|-------------|
| 1.0 | 2026-05-30 | Initial creation — escape-driven updates, quarterly reviews, freshness triggers |
| 2.1 | 2026-05-31 | Standardization pass: uniform versioning, cross-ref to Playbook Inventory, updated system version table, standard lessons entry |

---

## Appendix A: Playbook Freshness Command

Run this monthly:

```bash
#!/usr/bin/env bash
# playbook-freshness.sh
# Check every playbook for staleness.

for f in specs/*-playbook.md specs/master-fidelity-gate.md; do
    if [ ! -f "$f" ]; then continue; fi
    version=$(grep -m1 "Version:" "$f" | grep -oP '[0-9]+\.[0-9]+')
    date=$(grep -m1 "Version:" "$f" | grep -oP '[0-9]{4}-[0-9]{2}-[0-9]{2}')
    days_old=$(( ( $(date +%s) - $(date -d "$date" +%s) ) / 86400 ))
    echo "$f: v$version ($date) — $days_old days old"
    if [ $days_old -gt 90 ]; then
        echo "  ⚠️  STALE — needs quarterly review"
    fi
done
```

---

## Appendix B: The "Playbook Is Dying" Tell

| Tell | What it means | Fix |
|------|---------------|-----|
| "I didn't read the playbook" | It's too long or irrelevant | Trim or split |
| "The playbook didn't cover this" | Escape not fed back | Apply §3.1 protocol |
| Same bug escaped twice | Playbook update was cosmetic, not structural | Apply §3.3 double-escape rule |
| "This is my first time seeing this document" | Not part of onboarding | Add to HOUND.md / CLAUDE.md |
| No version change in 90 days | Stale — not evolving with the codebase | Run quarterly review |
| Lessons Learned without new checks | Documentation, not prevention | Move from "what happened" to "what check to add" |

---

## Lessons Learned

| Date | Project | What happened | Root cause | Fix applied |
|------|---------|---------------|-----------|-------------|
| 2026-06-10 | ObserveCo | 36-hour review found 6 UX traps, 3 coding patterns, 2 spec traps, 1 system pattern, 1 governance gap, 1 gate layer — all from a single payment flow bug cascade | Playbook system had 7 playbooks but no ui-testing-playbook; stale count was wrong | Updated stale count from 7 to 8. Added ui-testing-playbook to inventory. |

*"If a human catches something the playbooks missed, the playbooks were incomplete — update them before fixing the code." This meta-loop makes that rule real.*
