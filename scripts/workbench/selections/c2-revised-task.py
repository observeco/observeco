#!/usr/bin/env python3
"""Revised C2 task for Workbench replay.

REVISION RECORD:
- task_id: 20260716_111506_aaf7a1 (original session)
- revision: 2
- reason: original task text referenced obs-spec-061, which is a PHANTOM spec
  (zero hits at pin fb05b55). Transcript inspection showed all 3 replay trials
  confused-before-work, asking "obs-spec-061 doesn't exist — what's the third
  table?" and timing out. This is a task-defect, not a capability failure.
- change: dropped the phantom "obs-spec-061" reference; named the three tables
  explicitly (harness_optimization_runs, harness_eval_runs, harness_edits)
  per the ORIGINAL session's ground-truth completion.
- original task text preserved below for audit.
- This is a RECORDED REVISION, not an in-place edit. A replayed model is now
  scored against a fully-specified outcome contract (the named tables), so a
  pass means it created those tables — not that it guessed the third.

ORIGINAL task text:
  "Add migration 63 to ObserveCo's db.py: 3 new tables for harness optimization
   (obs-spec-056 + obs-spec-061)."

REVISED task text (this file):
  "Add migration 63 to ObserveCo's db.py with exactly three new tables for
   harness optimization: harness_optimization_runs, harness_eval_runs, and
   harness_edits. Each needs a reasonable schema consistent with its name and
   the existing migrations in the MIGRATIONS list. Register migration 63 in the
   MIGRATIONS list. Do not invent additional tables; the three named tables are
   the complete deliverable."
"""
import json

REVISED = {
    "id": "20260716_111506_aaf7a1",
    "revision": 2,
    "revision_reason": "phantom obs-spec-061 reference removed; three tables named explicitly",
    "original_task": "Add migration 63 to ObserveCo's db.py: 3 new tables for harness optimization (obs-spec-056 + obs-spec-061).",
    "task": (
        "Add migration 63 to the db.py file at the current location (the "
        "repository you are working in) with exactly three new tables for "
        "harness optimization: harness_optimization_runs, harness_eval_runs, and "
        "harness_edits. Each needs a reasonable schema consistent with its name "
        "and the existing migrations in the MIGRATIONS list. Register migration 63 "
        "in the MIGRATIONS list. Do not invent additional tables; the three named "
        "tables are the complete deliverable. Work only within the current "
        "repository directory — do not look outside it for another copy of db.py."
    ),
    "marker": "harness_optimization_runs",
    "marker_strength": "strong",
    "sha": "fb05b55",
    "rel": "src/observeco/db.py",
    "repo_root": "observeco",
    "assertion": "subject_symbol",
    "budget": 180,
    "budget_method": "work_span_x3",
    "budget_cap": 1800,
    "model": "deepseek-v4-pro",
}

if __name__ == "__main__":
    with open("/tmp/workbench-c2-revised.json", "w") as f:
        json.dump([REVISED], f, indent=2)
    print("wrote revised C2 candidate to /tmp/workbench-c2-revised.json")
    print("  marker:", REVISED["marker"])
    print("  sha:", REVISED["sha"], "rel:", REVISED["rel"])
    print("  tables named: harness_optimization_runs, harness_eval_runs, harness_edits")
