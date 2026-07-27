# Bug Report: forge profile cannot handle obs-spec-060 implementation

**Date:** 2026-07-12
**Reporter:** Main (Hound)
**Severity:** HIGH (blocks delegation of non-trivial multi-file tasks to forge)

## Symptom

Two consecutive forge attempts to implement obs-spec-060 failed:

1. **Attempt 1** (full 5-deliverable brief + full spec): `Context length exceeded: max compression attempts (3) reached.` — ornith-9B (local, ~16K context) could not ingest the spec + multiple source-file reads.
2. **Attempt 2** (Deliverable 1 only, tightened brief): Timed out after 600s with no output.

## Root Cause

The forge profile runs `ornith-9B` locally at ~16 tok/s. It cannot:
- Hold a ~13KB spec + 5 source files in its ~16K context window
- Sustain a multi-file implementation task within a 600s foreground timeout

The orchestration contract says: "If a profile has failed 2+ consecutive attempts on the same task, you may handle it directly and file a bug report for the profile."

## Resolution

Main implemented all 5 deliverables directly (history_tasks.py, db.py migration 61, cli.py suggest-tasks, canary.py two-pass runner, capability.py 4 endpoints). All verified passing.

## Recommended Fix for forge

- Route non-trivial multi-file tasks to a larger-context model (deepseek-v4-flash via Ollama Pro) instead of ornith-9B
- OR split large tasks into single-file deliverables (≤200 lines each) with pre-extracted facts (no spec/source-file reading required)
- OR raise forge's context window / use a model with ≥32K context

## Verification of direct implementation

- `py_compile` passes on all 5 files
- `observeco canary suggest-tasks --limit 3` → 3 drafts saved to `canary_task_drafts`
- Migration 61 applied: `source_session` column on `canary_tasks`, `canary_task_drafts` table created
- Approve flow: draft → `canary_tasks` with `built_in=0` + `source_session` set
- Source-session endpoint: returns 5 messages from `~/.hermes/state.db`
- Reject flow: deletes draft
- `llm_judge_unavailable=1` fallback confirmed (no API key configured)
