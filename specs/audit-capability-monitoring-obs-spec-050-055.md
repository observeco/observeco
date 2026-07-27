# Formal Playbook Audit: obs-spec-050 through 055

**Audit date:** 2026-07-02
**Auditor:** Hermes Agent (playbook-based formal audit)
**Playbooks loaded:** requirements-fidelity-playbook (v3.2), coding-fidelity-playbook (v3.4), system-design-testing-playbook (v3.4), ux-testing-playbook (v3.24), master-fidelity-gate (v3.4)
**Specs audited:** obs-spec-050 (Data Model), obs-spec-051 (Canary Runner), obs-spec-052 (Drift Detection), obs-spec-053 (Config Timeline), obs-spec-054 (Grid Report), obs-spec-055 (Task Definition UI)

---

## Executive Summary

**20 findings total:** 2 CRITICAL, 3 HIGH, 12 MEDIUM, 3 LOW

The specs are well-structured and internally consistent on the surface, but a formal playbook audit reveals significant gaps that the previous manual audit missed. The most critical issues are **cross-spec contradictions** (spec-051 claims a file path that doesn't exist, contradicting spec-050) and **spec claims about existing code that don't match reality** (adapter interface, Chart.js dependency, existing GridRunner architecture).

**Master Fidelity Gate scores (estimated):**
| Layer | Score | Threshold | Status |
|-------|-------|-----------|--------|
| A: Requirements Fidelity | 10/14 | ≥11 | ❌ FAIL |
| B: Coding Fidelity | 8/14 | ≥11 | ❌ FAIL |
| C: UX Fidelity | 9/14 | ≥11 | ❌ FAIL |
| D: System-Design Fidelity | 12/18 | ≥14 | ❌ FAIL |
| **Total** | **39/60** | **≥47 (80%)** | **❌ FAIL** |

---

## CRITICAL Findings

### C-1: Spec-051 claims migration file at non-existent path (Trap 6: Contradictory Refs)

**Severity:** CRITICAL — blocks build

**Which trap/rule:** Requirements-fidelity Trap 6 (Contradictory Refs), Coding-fidelity bug pattern 4.3 (Spec-to-implementation gap)

**Evidence:**
- **Spec-051 §6 File Changes table:** `src/observeco/db/migrations/050_capability_monitoring.py` | New — table creation
- **Spec-050 §2 Migration Strategy:** Shows the migration as an inline entry in `db.py:MIGRATIONS` — no separate file
- **Code verification:** `search_files` for `migrations/` under `src/observeco/db/` returns **zero results**. No `db/migrations/` directory exists. All migrations are inline in `db.py:MIGRATIONS` as `(version, sql_string)` tuples.

**Analysis:** Spec-050 correctly describes the inline migration pattern. Spec-051 contradicts this by claiming a separate file at `db/migrations/050_capability_monitoring.py`. This is a cross-spec contradiction. If a developer follows spec-051, they'll create a file that the migration system never reads (the auto-run pipeline only processes `MIGRATIONS` list entries).

**Fix:** Remove the `db/migrations/050_capability_monitoring.py` entry from spec-051 §6. The migration is inline in `db.py:MIGRATIONS` as spec-050 correctly shows.

---

### C-2: Spec-051 §2.2 describes TaskExecutor interface that doesn't match actual HermesBenchmarkAdapter (Trap 5: Hidden Constraints)

**Severity:** CRITICAL — blocks build

**Which trap/rule:** Requirements-fidelity Trap 5 (Hidden Constraints — assumes adapter interface that doesn't exist), Coding-fidelity bug pattern 4.10 (Hallucinated objects)

**Evidence:**
- **Spec-051 §2.2 TaskExecutor code:**
  ```python
  result = agent_adapter.run(prompt, timeout=timeout)
  return TaskResult(
      output=result.text,
      tokens=result.tokens,
      cost=result.cost,
      hang=result.timed_out,
      error=result.error,
  )
  ```
- **Actual `HermesBenchmarkAdapter.run_task()` signature** (`benchmark/adapters/hermes.py:33`):
  ```python
  def run_task(self, agent_name: str, task: BenchmarkTask) -> dict:
  ```
- **Actual return value** (hermes.py:89-94):
  ```python
  return {
      "output": output,
      "model_used": model_used,
      "harness_type": "hermes",
      "elapsed_seconds": elapsed,
  }
  ```

**Analysis:** The spec assumes the adapter has a `.run(prompt, timeout=timeout)` method that returns an object with `.text`, `.tokens`, `.cost`, `.timed_out`, `.error` properties. The actual adapter has `.run_task(agent_name, task)` that returns a dict with `output`, `model_used`, `harness_type`, `elapsed_seconds`. No `tokens`, `cost`, or `timed_out` fields exist. The spec describes a **different adapter interface** than what exists in the codebase. A developer implementing from this spec will either:
1. Write a wrapper that doesn't match the actual adapter
2. Try to call `.run()` which doesn't exist
3. Access `.tokens`/`.cost`/`.timed_out` which don't exist in the return dict

**Fix:** Update the TaskExecutor code to match the actual `HermesBenchmarkAdapter` interface:
```python
result = agent_adapter.run_task(agent_name, task)
# result is a dict with keys: output, model_used, harness_type, elapsed_seconds
# Note: tokens, cost, timed_out are NOT returned by the current adapter
```

---

## HIGH Findings

### H-1: Spec-052 §3.1 claims "Reuses the existing Chart.js dependency" but no Chart.js exists in the codebase (Trap 5: Hidden Constraints)

**Severity:** HIGH — wrong data/broken UX

**Which trap/rule:** Requirements-fidelity Trap 5 (Hidden Constraints — assumes dependency exists), Coding-fidelity bug pattern 4.10 (Hallucinated objects)

**Evidence:**
- **Spec-052 §3.1:** "Reuses the existing Chart.js dependency. The chart from Spectrum's mockup maps directly"
- **Code verification:** `search_files` for `chart.js`, `Chart.js`, `chart.min` in `index.html` returns **zero results**. No Chart.js CDN link, no Chart.js script tag, no Chart.js usage anywhere in the 6525-line template.

**Analysis:** The spec claims Chart.js is an existing dependency that can be "reused." It is not. The drift chart section will need to add Chart.js as a new dependency. This affects the entire drift chart implementation — the spec assumes zero new dependencies when in fact a significant new library must be added.

**Fix:** Update spec-052 §3.1 to acknowledge Chart.js is a new dependency that must be added. Include the CDN URL or npm package reference. Update the template strategy note in spec-054 §7 to mention Chart.js as a new dependency.

---

### H-2: Spec-052 §3.6 claims "html2canvas for PNG export (already a common dep)" but it doesn't exist (Trap 5: Hidden Constraints)

**Severity:** HIGH — wrong data/broken UX

**Which trap/rule:** Requirements-fidelity Trap 5 (Hidden Constraints), Coding-fidelity bug pattern 4.10

**Evidence:**
- **Spec-052 §3.6:** "html2canvas for PNG export (already a common dep, or use native canvas.toDataURL())"
- **Code verification:** `search_files` for `html2canvas` and `canvas.toDataURL` in `index.html` returns **zero results**. Neither exists in the template.

**Analysis:** The spec claims html2canvas is "already a common dep" — it is not. The fallback option `canvas.toDataURL()` also doesn't exist in the codebase. The shareable view feature requires a new dependency or new implementation.

**Fix:** Update spec-052 §3.6 to either (a) add html2canvas as a new dependency, or (b) commit to the `canvas.toDataURL()` approach and add the implementation. Remove the "already a common dep" claim.

---

### H-3: Spec-054 §3 describes GridRunner that reuses CanaryRunner, but existing code has a completely different GridRunner (Trap 5: Hidden Constraints)

**Severity:** HIGH — wrong approach

**Which trap/rule:** Requirements-fidelity Trap 5 (Hidden Constraints — assumes architecture that doesn't match existing code), Coding-fidelity bug pattern 4.3 (Spec-to-implementation gap)

**Evidence:**
- **Spec-054 §3 GridRunner:**
  ```python
  class GridRunner:
      def __init__(self, db, canary_runner):
          self.db = db
          self.canary = canary_runner
      def run(self, agent_name, models, configs, tasks=None):
          # For each (model, config) pair:
          #   1. Temporarily switch agent config
          #   2. Run canary suite (3 trials per task)
          #   3. Aggregate per-task accuracy
  ```
- **Existing code** (`benchmark/grid/runner.py`): Has a `GridRunner` class that uses `HermesTauAgent` and `tau_bench` environments (retail/airline), not `CanaryRunner`. It iterates models × configs × tasks × trials using τ-bench, not canary tasks.

**Analysis:** The spec describes a new GridRunner that wraps CanaryRunner, but the codebase already has a GridRunner with a completely different architecture (τ-bench based, not canary-based). The spec doesn't mention this existing implementation at all. A developer implementing from this spec will either:
1. Create a second GridRunner alongside the existing one (duplication)
2. Not realize the existing GridRunner exists and needs to be refactored

**Fix:** Spec-054 must acknowledge the existing `benchmark/grid/runner.py` GridRunner and describe how the new capability monitoring GridRunner relates to it. Options: (a) refactor the existing GridRunner to use CanaryRunner, (b) keep both with different names, (c) deprecate the existing one.

---

## MEDIUM Findings

### M-1: Spec-050 §4.3 claims "SQLite does not enforce foreign keys by default" but code sets PRAGMA foreign_keys=ON

**Severity:** MEDIUM — partial incorrectness

**Which trap/rule:** Coding-fidelity bug pattern 4.3 (Spec-to-implementation gap)

**Evidence:**
- **Spec-050 §4.3:** "SQLite does not enforce foreign keys by default (`PRAGMA foreign_keys = OFF`). After any prune operation, run: [orphan cleanup queries]"
- **Code verification** (db.py:902): `self._conn.execute("PRAGMA foreign_keys=ON")` — the code DOES enable FK enforcement.

**Analysis:** The orphan cleanup queries are still good practice (belt-and-suspenders — they handle orphans created before the PRAGMA was set, or from direct DB manipulation). But the spec's justification is misleading. With `PRAGMA foreign_keys=ON`, SQLite will reject DELETEs on parent rows that have child references (since the spec's tables don't use `ON DELETE CASCADE`). The orphan cleanup queries are still needed because pruning operations might need to handle this, but the spec should acknowledge that FK enforcement IS active.

**Fix:** Update §4.3 to say: "SQLite foreign keys are enabled (`PRAGMA foreign_keys=ON` at db.py:902), but the tables lack `ON DELETE CASCADE`. After any prune operation, run orphan cleanup queries to handle any child rows whose parents were deleted."

---

### M-2: Spec-051 §2.2 references "same pattern as existing lm_eval_adapter.py" but the pattern is in hermes.py

**Severity:** MEDIUM — partial incorrectness

**Which trap/rule:** Coding-fidelity bug pattern 4.3 (Spec-to-implementation gap)

**Evidence:**
- **Spec-051 §2.2:** "Timeout handling: Uses `Popen` + `preexec_fn=os.setsid` + `os.killpg` (same pattern as existing `lm_eval_adapter.py`)."
- **Code verification:** The `Popen` + `preexec_fn=os.setsid` + `os.killpg` pattern is in `benchmark/adapters/hermes.py` (lines 45-63), not in `lm_eval_adapter.py`.

**Fix:** Change reference from `lm_eval_adapter.py` to `benchmark/adapters/hermes.py`.

---

### M-3: Spec-054 §7 claims index.html is 344KB but actual is 336KB

**Severity:** MEDIUM — partial incorrectness

**Which trap/rule:** Requirements-fidelity Trap 4 (Wrong success metrics — stale claim)

**Evidence:**
- **Spec-054 §7:** "The dashboard template (`dashboard/templates/index.html`) is a 6,525-line monolith (344KB)."
- **Code verification:** `ls -lh` shows 336KB (not 344KB). Line count (6525) is correct.

**Fix:** Update to "336KB" or remove the size claim.

---

### M-4: Spec-055 §5 lists 9 built-in tasks that don't match existing benchmark engine's 9 canary tasks

**Severity:** MEDIUM — partial incorrectness

**Which trap/rule:** Requirements-fidelity Trap 6 (Contradictory Refs — spec describes different task system than existing code)

**Evidence:**
- **Spec-055 §5:** 9 tasks: Extract structured data, Follow multi-step instructions, Arithmetic reasoning, Summarize conversation, Tool selection, Time-bound response, Chart interpretation, Document Q&A, Code generation
- **Existing code** (`benchmark/engine.py:69-83`): 9 canary tasks: `bbh_cot_fewshot_boolean_expressions`, `bbh_cot_fewshot_navigate`, `bbh_cot_fewshot_web_of_lies`, `gsm8k_cot`, `ifeval`, `mbpp`, `triviaqa`, `bbq_generate`, `arc_challenge_chat`

**Analysis:** The spec describes a completely different task system (YAML-defined, assertion-based) than the existing benchmark engine (lm-eval-harness based). The spec doesn't mention the existing benchmark system at all. These are two different task systems — the spec's tasks are for capability monitoring, the existing tasks are for lm-eval benchmarks. But the spec should acknowledge the existing system and explain how the new one relates.

**Fix:** Add a note in spec-055 §5 explaining that these 9 tasks are for the capability monitoring system (separate from the existing lm-eval benchmark tasks in `benchmark/engine.py`). Clarify the relationship between the two task systems.

---

### M-5: Spec-051 CLI has no `--model` flag but spec-055 §2.2 references it

**Severity:** MEDIUM — cross-spec contradiction

**Which trap/rule:** Requirements-fidelity Trap 6 (Contradictory Refs)

**Evidence:**
- **Spec-051 §1 CLI:** `observeco canary run [--agent AGENT] [--tasks TASKS] [--trials N] [--schedule]` — no `--model` flag
- **Spec-055 §2.2:** "CLI `--model M` flag overrides the task's `model` override."

**Analysis:** Spec-055 references a `--model` CLI flag that spec-051 doesn't define. Either spec-051 is missing the flag, or spec-055 is wrong.

**Fix:** Add `--model` flag to spec-051's CLI definition, or remove the reference from spec-055.

---

### M-6: Spec-052 API endpoints use `/api/capability/` prefix but existing drift endpoints use `/api/drift-summary`

**Severity:** MEDIUM — naming inconsistency

**Which trap/rule:** System-design-testing playbook — naming consistency

**Evidence:**
- **Spec-052 §2.1:** `GET /api/capability/drift?agent=NAME`
- **Spec-052 §2.2:** `GET /api/capability/drift/history?agent=NAME&days=14`
- **Existing code** (server.py:3153): `@app.get("/api/drift-summary")`
- **Existing code** (server.py:7309): `@app.post("/api/check-drift-alerts")`

**Analysis:** The existing drift endpoints use `/api/drift-summary` and `/api/check-drift-alerts`. The new spec uses `/api/capability/drift`. This inconsistency could cause confusion. The new endpoints should either use the same prefix or the old ones should be deprecated.

**Fix:** Either (a) use `/api/capability/drift` for new endpoints and document that old `/api/drift-summary` is separate, or (b) align with existing naming convention.

---

### M-7: Spec-050 §4.4 says "pruning runs as part of the existing 3am maintenance cron" but PruneConsumer runs on 24h interval from start time

**Severity:** MEDIUM — partial incorrectness

**Which trap/rule:** Requirements-fidelity Trap 5 (Hidden Constraints — assumes cron schedule that doesn't match implementation)

**Evidence:**
- **Spec-050 §4.4:** "Pruning runs as part of the existing 3am maintenance cron."
- **Code verification** (watch_consumers.py:24): `PRUNE_INTERVAL = 86400` — 24h interval from consumer start, not 3am cron.

**Analysis:** The existing PruneConsumer runs every 24h from when the watch daemon starts, not at a fixed 3am time. The spec assumes a cron-based schedule that doesn't match the actual implementation.

**Fix:** Update spec-050 §4.4 to match the actual implementation: "Pruning runs every 24h via the existing PruneConsumer in watch_consumers.py."

---

### M-8: Spec-051 §4 references "Hermes cron infrastructure" without specifying which system

**Severity:** MEDIUM — underspecified dependency

**Which trap/rule:** Requirements-fidelity Trap 5 (Hidden Constraints)

**Evidence:**
- **Spec-051 §4:** "The cron job is managed by Hermes cron infrastructure. It survives daemon restarts."
- No reference to which Hermes cron system (launchd? hermes cron? system cron?).

**Analysis:** The spec references an external dependency ("Hermes cron infrastructure") without specifying what it is or how to use it. This is an underspecified dependency that will cause implementation issues.

**Fix:** Add a reference to the specific Hermes cron system (e.g., `hermes cron` CLI, launchd plist, etc.) and how to create/update/remove jobs.

---

### M-9: Spec-050 §2 migration version 50 creates a 19-version gap (32-49)

**Severity:** MEDIUM — design concern

**Which trap/rule:** System-design-testing playbook — migration integrity

**Evidence:**
- **Spec-050 §2:** Migration entry is `(50, ...)` and "bump SCHEMA_VERSION from 31 to 50"
- **Code verification:** Current `SCHEMA_VERSION = 31`, last migration is `(31, ...)`

**Analysis:** Jumping from version 31 to 50 creates a 19-version gap. While this works technically (the migration loop runs all pending migrations in order), it's unusual and could cause confusion. If someone later adds migration 32, it would run after migration 50 (since the loop runs in order). This is architecturally valid but worth documenting.

**Fix:** Add a comment in the spec explaining why version 50 was chosen (e.g., "Version 50 aligns with obs-spec-050 spec ID for traceability").

---

### M-10: Spec-050 §4.1 state matrix says canary_results "Orphaned if parent run pruned" but FK enforcement is ON

**Severity:** MEDIUM — partial incorrectness

**Which trap/rule:** Requirements-fidelity Trap 4 (Wrong success metrics)

**Evidence:**
- **Spec-050 §4.1:** `canary_results` stale state: "Orphaned if parent run pruned"
- **Code verification** (db.py:902): `PRAGMA foreign_keys=ON` is set

**Analysis:** With `PRAGMA foreign_keys=ON` and the `REFERENCES canary_runs(id)` constraint (without `ON DELETE CASCADE`), deleting a parent `canary_runs` row will **fail** with a FK violation, not silently orphan child rows. The state matrix should say "Prune blocked if child rows exist" or the tables need `ON DELETE CASCADE`.

**Fix:** Either (a) add `ON DELETE CASCADE` to all FK constraints, or (b) update the state matrix to reflect that pruning will need to delete child rows first (which the orphan cleanup queries in §4.3 handle).

---

### M-11: Spec-053 §1.1 references `hermes config` or `config.yaml` for model/config detection but no TOML config exists

**Severity:** MEDIUM — underspecified

**Which trap/rule:** Requirements-fidelity Trap 5 (Hidden Constraints)

**Evidence:**
- **Spec-053 §1.2:** "Detected by comparing the current agent config (from `hermes config` or `config.yaml`) against the last snapshot"
- **Code verification:** No TOML config in the project. Config is YAML-based via Hermes config files.

**Analysis:** The spec references `config.yaml` which is correct (Hermes uses YAML), but also mentions `hermes config` which is a CLI command. The spec should be more specific about which config source to use.

**Fix:** Clarify that config is read from Hermes YAML config files, not TOML.

---

### M-12: Spec-052 §3.5 "Create Alert" button references "existing alert system" but no alert creation dialog exists

**Severity:** MEDIUM — underspecified dependency

**Which trap/rule:** Requirements-fidelity Trap 5 (Hidden Constraints)

**Evidence:**
- **Spec-052 §3.5:** "\"🔔 Create Alert\" → opens alert creation dialog (uses existing alert system)"
- **Code verification:** The existing alert system has push endpoints but no alert creation dialog/UI in the dashboard.

**Analysis:** The spec references an "existing alert system" with a creation dialog, but no such dialog exists in the dashboard. This is either a planned feature that doesn't exist yet, or the spec assumes UI that hasn't been built.

**Fix:** Clarify whether the alert creation dialog exists or needs to be built as part of this spec.

---

## LOW Findings

### L-1: Spec-050 §2 says "bump SCHEMA_VERSION from 31 to 50" — version number is arbitrary

**Severity:** LOW — clarity

**Evidence:** The version jump from 31 to 50 is large but functional. The spec should explain the rationale.

**Fix:** Add a comment: "Version 50 chosen to match obs-spec-050 spec ID for traceability."

---

### L-2: Spec-054 §5.4 "Run Full Grid" button "Shows progress indicator during execution" — no progress indicator pattern defined

**Severity:** LOW — clarity

**Evidence:** The spec says the button shows a progress indicator but doesn't specify what kind (spinner? progress bar? percentage?). The existing dashboard has no standard progress indicator pattern.

**Fix:** Reference an existing progress indicator pattern or define one.

---

### L-3: Spec-055 §4.2 says "syntax highlighting (basic — just colour the YAML)" — no existing YAML editor in the codebase

**Severity:** LOW — clarity

**Evidence:** The spec describes a YAML editor with syntax highlighting but there's no existing code editor component in the dashboard to reuse.

**Fix:** Acknowledge this is a new component, not a reuse of an existing one.

---

## Cross-Spec Consistency Matrix

| Claim | Spec-050 | Spec-051 | Spec-052 | Spec-053 | Spec-054 | Spec-055 | Reality |
|-------|----------|----------|----------|----------|----------|----------|---------|
| Migration location | Inline in db.py | Separate file | N/A | N/A | N/A | N/A | **Inline** — spec-051 wrong |
| Adapter interface | N/A | `.run(prompt, timeout)` | N/A | N/A | N/A | N/A | **`run_task(agent_name, task)`** — spec-051 wrong |
| Chart.js exists | N/A | N/A | ✅ "Reuses" | N/A | N/A | N/A | **Doesn't exist** — spec-052 wrong |
| GridRunner architecture | N/A | N/A | N/A | N/A | Wraps CanaryRunner | N/A | **τ-bench based** — spec-054 wrong |
| CLI --model flag | N/A | ❌ Not in CLI | N/A | N/A | N/A | ✅ Referenced | **Contradiction** between 051 and 055 |
| Task system | N/A | N/A | N/A | N/A | N/A | 9 assertion tasks | **lm-eval tasks exist** — different system |
| html2canvas exists | N/A | N/A | ✅ "common dep" | N/A | N/A | N/A | **Doesn't exist** |
| index.html size | N/A | N/A | N/A | N/A | 344KB | N/A | **336KB** |
| Pruning schedule | 3am cron | N/A | N/A | N/A | N/A | N/A | **24h interval** |
| FK enforcement | OFF by default | N/A | N/A | N/A | N/A | N/A | **ON** at db.py:902 |

---

## Master Fidelity Gate Scoring

### Layer A: Requirements Fidelity (14 pts, threshold ≥11)

| Item | Score | Notes |
|------|-------|-------|
| A1: RDR written | 2/3 | No formal RDR, but spec structure is clear |
| A2: 6 spec traps checked | 1/3 | Traps 5 and 6 fail (multiple hidden constraints, contradictory refs) |
| A3: State matrix ≥4 states | 2/2 | Spec-050 §4.1 has good state matrix |
| A4: Success metrics | 1/3 | Spec-055 §6 has metrics, but spec-051/052/053/054 have none |
| A5: Constraints register | 1/2 | No formal constraints register, but some implicit constraints noted |
| A6: Cross-references verified | 1/1 | Partially — some cross-refs correct, but 051↔055 contradiction exists |
| **Total** | **8/14** | **❌ FAIL** |

### Layer B: Coding Fidelity (14 pts, threshold ≥11)

| Item | Score | Notes |
|------|-------|-------|
| B1: Spec grounding | 1/3 | Specs reference code but don't verify claims |
| B2: Implementation fidelity | 1/3 | Multiple claims about existing code are wrong |
| B3: No f-string leaks | 2/2 | N/A for spec audit |
| B4: TestClient assertions | 1/2 | No test plan in specs |
| B5: Dependency verification | 1/2 | Chart.js and html2canvas claimed but don't exist |
| B6: Master plan updated | 2/2 | Specs reference master plan |
| **Total** | **8/14** | **❌ FAIL** |

### Layer C: UX Fidelity (14 pts, threshold ≥11)

| Item | Score | Notes |
|------|-------|-------|
| C1: Perception | 2/3 | Dashboard sections described but no mockups |
| C2: Confidence | 2/3 | Error states mentioned but not detailed |
| C3: Friction | 2/3 | Loading states mentioned for grid, not for others |
| C4: Accessibility | 1/2 | No accessibility considerations |
| C5: Emotional load | 1/2 | Empty states described but no first-run guidance |
| C6: Entity-type rendering | 1/1 | N/A for these specs |
| **Total** | **9/14** | **❌ FAIL** |

### Layer D: System-Design Fidelity (18 pts, threshold ≥14)

| Item | Score | Notes |
|------|-------|-------|
| D1: Data pipeline | 2/3 | Writer/reader chain partially defined |
| D2: Lifecycle tests | 1/3 | No lifecycle tests defined |
| D3: 9 lenses | 2/3 | Some lenses covered (migration, backup) |
| D4: Heartbeat | 2/2 | N/A for data-layer specs |
| D5: Cross-platform | 1/2 | No cross-platform considerations |
| D6: Crash resilience | 2/3 | Backup/restore mentioned, no crash tests |
| D7: Data continuity (GS-019) | 2/2 | Spec-050 §4 has good GS-019 coverage |
| **Total** | **12/18** | **❌ FAIL** |

### Overall: 37/60 (threshold 47/60 = 80%) — ❌ FAIL

---

## Summary of Required Fixes Before Build

1. **CRITICAL:** Fix spec-051 §6 — remove `db/migrations/050_capability_monitoring.py` reference
2. **CRITICAL:** Fix spec-051 §2.2 — update TaskExecutor to match actual HermesBenchmarkAdapter interface
3. **HIGH:** Fix spec-052 §3.1 — acknowledge Chart.js is a new dependency
4. **HIGH:** Fix spec-052 §3.6 — remove "already a common dep" claim for html2canvas
5. **HIGH:** Fix spec-054 §3 — acknowledge existing GridRunner and describe relationship
6. **MEDIUM:** Fix spec-050 §4.3 — update FK enforcement justification
7. **MEDIUM:** Fix spec-051 §2.2 — correct lm_eval_adapter.py reference to hermes.py
8. **MEDIUM:** Fix spec-054 §7 — correct 344KB to 336KB
9. **MEDIUM:** Fix spec-055 §5 — add note about relationship to existing benchmark tasks
10. **MEDIUM:** Fix spec-051/055 — resolve --model flag contradiction
11. **MEDIUM:** Fix spec-052 — resolve /api/capability/ vs /api/drift-summary naming
12. **MEDIUM:** Fix spec-050 §4.4 — correct pruning schedule description
13. **MEDIUM:** Fix spec-051 §4 — specify which Hermes cron system
14. **MEDIUM:** Fix spec-050 §4.1 — update canary_results stale state for FK enforcement
15. **MEDIUM:** Fix spec-053 §1.2 — clarify config source
16. **MEDIUM:** Fix spec-052 §3.5 — clarify alert creation dialog status
