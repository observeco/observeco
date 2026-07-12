# obs-spec-081: Incident Skill Auto-Creation (L3 Learning Loop)

**Status:** 🔴 Spec — not yet implemented
**Product:** ObserveCo
**Depends on:** obs-spec-015 (Auto-Heal L1/L2), §3.25 (LLM-Powered Intelligence Service)
**Inspiration:** [Hermes Incident Commander](https://github.com/Lethe044/hermes-incident-commander) — autonomous SRE agent that writes a prevention SKILL.md after every novel incident

## §1 Problem

ObserveCo's heal pipeline (L1/L2) diagnoses and remediates agent failures, but **learns nothing from them**. The same crash pattern triggers the same LLM diagnosis call every time — $0.02 per incident, forever. A memory leak that crashes Kepler weekly costs ~$1/month in LLM calls for the same diagnosis the system already produced last week.

The deferred "heal feedback loop" consumer in §3.25 (shallow consumer #7) only evaluates 5 pulse ticks post-restart. It doesn't extract the failure pattern, doesn't create a reusable prevention skill, and doesn't shortcut future diagnoses.

## §2 Solution

After a successful heal (L1 auto-restart or LLM-assisted diagnosis), the LLM analyzes the failure pattern and writes a **prevention SKILL.md** to `~/.observeco/prevention/`. On the next failure, the system checks prevention skills first via FTS5 pattern matching. If a skill matches the error signature, the known fix is applied directly — skipping the full LLM diagnosis pipeline (faster, zero LLM cost).

```
Current:  DETECT → DIAGNOSE (static → LLM) → REMEDIATE → VERIFY → done
                    ↑ LLM cost per novel failure ($0.02)

With L3:  DETECT → CHECK PREVENTION SKILLS (FTS5) → match?
           ├─ YES → apply known fix → VERIFY → done (zero LLM cost)
           └─ NO  → DIAGNOSE (static → LLM) → REMEDIATE → VERIFY
                    → LEARN: write prevention SKILL.md → done
                    ↑ LLM cost once, then zero for this pattern
```

## §3 Scope — L3 Learning Loop

| Step | What happens | LLM cost |
|------|-------------|----------|
| 1. Incident detected | Pulse/check/alert fires on agent failure | Zero (existing infra) |
| 2. Prevention skill check | FTS5 search `prevention_skills` table for error signature match | Zero (local SQLite) |
| 3a. Match found | Apply remediation from skill. Skip LLM diagnosis. | Zero |
| 3b. No match | Run existing heal pipeline (static patterns → LLM escalation if novel) | $0.02 (existing) |
| 4. Successful heal | LLM extracts: failure pattern, root cause, fix applied, verification metrics | $0.02 (new call) |
| 5. Skill creation | LLM writes SKILL.md: trigger conditions, diagnostic steps, remediation, verification | Same call as step 4 |
| 6. Skill stored | Written to `~/.observeco/prevention/{timestamp}-{pattern}.md` + indexed in DB | Zero |
| 7. Next occurrence | Step 2 finds the skill → applies fix directly | Zero LLM |

## §4 Cost Trajectory

| Timeline | Novel failures | Known patterns | LLM cost/week |
|----------|---------------|-----------------|---------------|
| Week 1 | 8 | 0 | $0.16 |
| Week 4 | 3 | 5 | $0.06 (5 free) |
| Week 12 | 1 | 7 | $0.02 (7 free) |

The system gets cheaper to run as it learns your infrastructure's failure modes.

## §5 DB Schema

```sql
CREATE TABLE IF NOT EXISTS prevention_skills (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_name TEXT NOT NULL,
    pattern_hash TEXT NOT NULL,         -- SHA256 of normalized error signature
    trigger_conditions TEXT NOT NULL,   -- JSON: {error_type, error_substring, agent_state}
    skill_path TEXT NOT NULL,           -- path to SKILL.md
    diagnosis TEXT,                     -- LLM diagnosis text
    remediation TEXT NOT NULL,          -- fix applied
    success_count INTEGER DEFAULT 0,    -- times this skill was successfully applied
    fail_count INTEGER DEFAULT 0,      -- times remediation from this skill failed verification
    deprecated INTEGER DEFAULT 0,      -- auto-deprecated after 2 consecutive verification failures
    created_at TEXT DEFAULT (datetime('now')),
    last_used_at TEXT,
    UNIQUE(pattern_hash, agent_name)
);

-- FTS5 virtual table for pattern matching
CREATE VIRTUAL TABLE IF NOT EXISTS prevention_skills_fts USING fts5(
    pattern_hash,
    agent_name,
    error_signature,
    diagnosis,
    content='prevention_skills',
    content_rowid='id'
);
```

## §6 Error Signature Extraction

```python
def extract_error_signature(error_log: str, agent_name: str, agent_state: dict) -> str:
    """Extract a normalized error signature for FTS5 matching.

    Strips timestamps, PIDs, file paths, and other volatile data.
    Keeps: error type, error message core, agent state at failure.
    """
    # ponytail: naive regex stripping — doesn't handle obfuscated or
    # multi-line stack traces well. Upgrade: LLM-assisted extraction if
    # regex match confidence < 0.7 against existing prevention skills.
    signature = re.sub(r'\d{4}-\d{2}-\d{2}.*?\d{2}:\d{2}:\d{2}', '', error_log)
    signature = re.sub(r'PID\s*\d+', 'PID', signature)
    signature = re.sub(r'/[^\s]+\.py', '<file>', signature)
    signature = re.sub(r'0x[0-9a-fA-F]+', '0xADDR', signature)
    return f"{agent_name}:{agent_state.get('status')}:{signature.strip()[:500]}"
```

## §7 Prevention Skill Template

```markdown
---
name: prevention-{agent}-{pattern}
version: "1.0"
created: {timestamp}
agent: {agent_name}
pattern_hash: {hash}
trigger_conditions:
  error_type: {type}
  error_substring: "{substring}"
  agent_state: {state}
---

# Prevention: {diagnosis_title}

## Trigger
Agent `{agent_name}` fails with: {error_description}

## Root Cause
{llm_diagnosis}

## Remediation
{fix_steps}

## Verification
{verification_criteria}

## History
- Created: {timestamp} after {agent_name} incident
- Applied: {success_count} times
- Last used: {last_used_at}
```

## §8 CLI

```bash
observeco heal --learn           # Enable learning loop (creates prevention skills after heal)
observeco heal --learn --show    # List all prevention skills
observeco heal --learn --test    # Dry-run: match current errors against prevention skills
observeco prevention list        # List all prevention skills
observeco prevention show <id>    # Show a specific prevention skill
observeco prevention remove <id> # Delete a prevention skill
observeco prevention export       # Export all skills as JSON (for backup/sharing)
```

## §9 Safety

- **Advisory application**: The heal pipeline still runs full VERIFY even when applying a known fix from a prevention skill. If verification fails, the full diagnostic pipeline runs.
- **Auto-deprecation**: If a prevention skill's remediation fails verification 2× consecutively, the skill is auto-deprecated (`deprecated=1`). Deprecated skills are not matched but are retained for audit trail.
- **Per-agent scoping**: Prevention skills are per-agent. A skill for Kepler's crash pattern doesn't auto-apply to Dreamer. (Pro: cross-fleet pattern sharing — suggest skills for similar agents.)
- **Opt-in only**: Requires `auto_heal.learn: true` in config or `--learn` flag. Default off. No regression when disabled.
- **LLM cost guard**: Skill creation uses the same `llm_service.ask()` budget pool ($0.02/call). If daily budget exhausted, heal still works but no new prevention skills are created (graceful degradation — static fallback).
- **Dangerous remediations**: Same rule as auto-heal. `pip_install`, `code_fix` never auto-execute from prevention skills. They always need human approval. Only known-safe patterns (restart, trim, cooldown) auto-apply.

## §10 What This Does NOT Do

- ❌ Does not write skills to `~/.hermes/skills/` (Hermes' skill directory) — prevention skills live in `~/.observeco/prevention/` to avoid polluting user's skill space
- ❌ Does not auto-execute dangerous remediations (same rule as auto-heal)
- ❌ Does not share prevention skills between agents automatically (Pro: cross-fleet pattern sharing)
- ❌ Does not replace the LLM diagnosis pipeline — it short-circuits it for known patterns only

## §11 Free vs Pro

| Feature | Free | Pro |
|---------|------|-----|
| Prevention skill creation | ✅ BYOK (own LLM key) | ✅ Same |
| Prevention skill application | ✅ Faster heal on known patterns | ✅ Same |
| Prevention skill management CLI | ✅ | ✅ |
| Dashboard UI for prevention skills | ❌ | ✅ List, view, promote, deprecate |
| Cross-fleet pattern sharing | ❌ | ✅ Skills from one agent suggested for similar agents |
| Promotion gating | ❌ | ✅ Configurable: N auto-applies, then human review required |

## §12 Failure Modes

| Failure | Fallback |
|---------|----------|
| FTS5 match returns false positive (different root cause, similar signature) | Verification step fails → full diagnostic pipeline runs → prevention skill fail_count incremented |
| LLM fails to generate skill during creation | Heal still succeeds, no skill created. Next occurrence runs full pipeline again. |
| Daily LLM budget exhausted | Heal works, no new skills created. Existing skills still matched and applied. |
| Prevention skill file corrupted/missing | DB entry found but file unreadable → skip, run full pipeline. Log warning. |
| FTS5 table out of sync with skill files | `observeco prevention list` detects orphan entries → prompts cleanup |

## §13 Acceptance Criteria

- [ ] AC1: After successful LLM-assisted heal, a prevention skill is written to `~/.observeco/prevention/`
- [ ] AC2: Same error pattern recurring → prevention skill found via FTS5 → fix applied without LLM call
- [ ] AC3: `observeco prevention list` shows all prevention skills with success count + last used
- [ ] AC4: Prevention skill with 2 consecutive verification failures → auto-deprecated (not deleted)
- [ ] AC5: `--learn` flag off → no prevention skills created, heal works normally (zero regression)
- [ ] AC6: Daily LLM budget exhausted → heal works, no new skills created (graceful degradation)
- [ ] AC7: Prevention skill for agent A doesn't auto-apply to agent B
- [ ] AC8: Dangerous remediation in prevention skill (pip_install, code_fix) → not auto-executed, requires human approval
- [ ] AC9: `observeco prevention remove <id>` deletes skill file + DB entry + FTS5 index

## §14 Effort

~2d total:
- **Day 1**: Error signature extraction + FTS5 matching + `prevention_skills` DB table + heal pipeline integration (check prevention before LLM escalation)
- **Day 2**: LLM skill generation prompt + CLI commands + auto-deprecation logic + end-to-end test