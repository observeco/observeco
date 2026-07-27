# Formal Playbook Audit: obs-spec-057 (Benchmark Methodology Upgrade)

**Audit date:** 2026-07-06
**Auditor:** Hermes Agent (playbook-based formal audit)
**Playbooks applied:** requirements-fidelity-playbook, coding-fidelity-playbook, system-design-testing-playbook
**Specs audited:** obs-spec-057 (Benchmark Methodology Upgrade), plus cross-checks against obs-spec-050, 051, 052, 055, master plan §57, agent-quality-management-brief §11

---

## Executive Summary

**9 findings total:** 1 CRITICAL, 3 HIGH, 4 MEDIUM, 1 LOW

obs-spec-057 is a well-structured upgrade spec that correctly identifies the weaknesses in the current canary system and proposes appropriate fixes. However, it contains one critical gap (missing `canary_judge_cache` and `canary_task_baselines` schema definitions), several hidden constraints around the LLM judge implementation, and a migration plan that doesn't account for the existing data in `canary_tasks`.

**Master Fidelity Gate scores (estimated):**

| Layer | Score | Threshold | Status |
|-------|-------|-----------|--------|
| A: Requirements Fidelity | 11/14 | ≥11 | ✅ PASS |
| B: Coding Fidelity | 9/14 | ≥11 | ❌ FAIL |
| C: UX Fidelity | 10/14 | ≥11 | ❌ FAIL |
| D: System-Design Fidelity | 13/18 | ≥14 | ❌ FAIL |
| **Total** | **43/60** | **≥47 (80%)** | **❌ FAIL** |

Improvement over spec-050-055 audit (was 39/60) — primarily due to better requirements structure and ground-truth verification of code claims. Still fails due to missing schema definitions, state matrices, and lifecycle tests.

---

## CRITICAL Findings

### C-1: New tables `canary_judge_cache` and `canary_task_baselines` have no schema definition

**Severity:** CRITICAL — blocks implementation

**Which trap/rule:** Requirements-fidelity Trap 5 (Hidden Constraints — references tables without defining schema), Coding-fidelity bug pattern 4.3 (Spec-to-implementation gap)

**Evidence:**
- **Spec-057 §2.2:** "Cache stored in `canary_judge_cache` table"
- **Spec-057 §2.3:** "New table: `canary_task_baselines` — per-task baseline accuracy per agent+config"
- **Spec-057 §8 File Changes:** Lists both tables in migration but provides **zero schema** — no CREATE TABLE, no column definitions, no indexes
- **Cross-check:** obs-spec-050 §3 defines full CREATE TABLE for all 8 capability tables. Spec-057 introduces 2 new tables but follows none of the same rigour

**Analysis:** A developer implementing this spec will need to design the table schema from scratch with no guidance. This is the same class of failure as spec-051's missing migration file reference in the prior audit. The tables need column definitions, types, constraints, indexes, and relationships documented.

**Fix:** Add a §2.7 section with full CREATE TABLE statements for both new tables, following the format of obs-spec-050 §3. Include:
- `canary_judge_cache`: (cache_key TEXT PK, task_id TEXT, output_hash TEXT, score REAL, reasoning TEXT, model_used TEXT, created_at TEXT)
- `canary_task_baselines`: (id TEXT PK, agent_name TEXT, config_hash TEXT, task_id TEXT, accuracy REAL, ci_lower REAL, ci_upper REAL, run_count INTEGER, created_at TEXT, expires_at TEXT)

---

## HIGH Findings

### H-1: LLM judge implementation references `observeco.llm_service.call_llm` without verifying it exists

**Severity:** HIGH — wrong approach / blocks implementation

**Which trap/rule:** Requirements-fidelity Trap 5 (Hidden Constraints), Coding-fidelity bug pattern 4.10 (Hallucinated objects)

**Evidence:**
- **Spec-057 §2.2 code sample:** `from observeco.llm_service import call_llm`
- **Code verification:** The master plan §3.25 says "LLM-Powered Intelligence Service — shared `llm_service`" is ✅ Live — but the actual service interface has not been verified. The spec doesn't document the function signature, parameters, or return type
- **Master plan §3.25:** "Uses `OBSERVECO_LLM_API_KEY` (bring-your-own-key). Static fallbacks when no key configured."

**Analysis:** The spec imports `call_llm` from `llm_service` without verifying:
1. Does `call_llm` exist as a public function?
2. What is its signature? (prompt, model, temperature, max_tokens?)
3. What does it return? (string? dict? AIMessage?)
4. How does the fallback work when no API key is configured?

**Fix:** Verify the actual `llm_service` interface and update the code sample to match. Document: function signature, return type, fallback behavior when no key. Add a constraint: "LLM-judge requires `OBSERVECO_LLM_API_KEY` — falls back to `semantic_similarity` or `contains` assertion when not set."

---

### H-2: `semantic_similarity` assertion introduces sentence-transformers dependency without install spec

**Severity:** HIGH — missing dependency documentation

**Which trap/rule:** Requirements-fidelity Trap 5 (Hidden Constraints), Coding-fidelity bug pattern (missing dependency)

**Evidence:**
- **Spec-057 §2.2:** "`semantic_similarity` | `expected`, `threshold` (default 0.7) | Compute cosine similarity between output and expected output using sentence-transformers"
- **Spec-057 §6 Constraints #2:** "sentence-transformers dep | SHOULD | 80MB model, for `semantic_similarity`"
- **Code verification:** `search_files` for "sentence-transformers" or "sentence_transformers" in the ObserveCo codebase returns zero results — this is a brand new dependency not in `pyproject.toml`
- The model (all-MiniLM-L6-v2) is 80MB on disk

**Analysis:** Adding an 80MB ML model as a dependency for one assertion type is significant. The spec says "SHOULD" but doesn't define:
1. Which model specifically? (all-MiniLM-L6-v2? paraphrase-MiniLM-L6-v2?)
2. Is it lazy-loaded or installed at setup?
3. What happens when it's not installed — graceful fallback or crash?
4. Does it need GPU? (Mac Mini M-series has Metal — does the model use it?)

**Fix:** Add to §2.2: "Uses `sentence-transformers/sentence-transformers` package with `all-MiniLM-L6-v2` model (80MB). Lazy-loaded on first `semantic_similarity` assertion. If package not installed, falls back to `contains` assertion with a warning log. Add `sentence-transformers` to `pyproject.toml` optional dependencies under `[project.optional-dependencies] sim = ["sentence-transformers>=2.2"]`."

---

### H-3: `code_executable` assertion has no sandbox security model

**Severity:** HIGH — security risk

**Which trap/rule:** System-design-testing playbook — security/lifecycle lens, Requirements-fidelity Trap 5

**Evidence:**
- **Spec-057 §2.2:** "`code_executable` | `language` | Execute generated code in a sandbox, check for runtime errors"
- **Spec-057 §6 Constraints #3:** "Code execution sandbox | SHOULD | Use `subprocess` + `timeout` + restricted env vars"
- **Spec-057 §7 Risks:** "Code execution is unsafe | Low | Security risk | Sandbox: no network, no filesystem write"
- No actual sandbox implementation specified — just "use subprocess + timeout + restricted env vars"

**Analysis:** The risk is marked "Low" but the mitigation list (no network, restricted env, timeout, no filesystem write) is insufficient for a real sandbox. On macOS, subprocess with restricted env vars does NOT prevent:
- Fork bombs (can hit process limits)
- Filesystem reads (can read ~/.ssh, ~/.aws, etc. — even without write)
- Network access (unless `--no-network` or network namespace isolation)
- Memory exhaustion (no cgroup limits on macOS)

The spec needs to either: (a) use a proper sandbox (Docker container, nsjail, or similar), or (b) restrict `code_executable` to languages with built-in sandboxing (e.g., WebAssembly, or Python with `RestrictedPython`), or (c) clearly document the security limitations.

**Fix:** Update §6 Constraints #3 to MUST and specify the actual isolation mechanism. Recommended: use Python's `subprocess` with `subprocess.TimeoutExpired`, `env={"PATH": "/usr/bin:/bin", "HOME": "/tmp"}`, `cwd="/tmp/sandbox"`, and document residual risks. Or defer `code_executable` to v0.7.0 and start with safer assertion types.

---

## MEDIUM Findings

### M-1: Migration plan doesn't account for existing data in `canary_tasks`

**Severity:** MEDIUM — data integrity

**Which trap/rule:** System-design-testing playbook — migration/data lifecycle

**Evidence:**
- **Spec-057 §2.1:** "Migration: `ALTER TABLE canary_tasks ADD COLUMN ...` for each new column"
- **Code verification:** There are currently 9 tasks in `canary_tasks` with live data (confirmed via DB query in prior conversation)
- The spec doesn't specify default values for existing rows
- `category` defaults to NULL — existing tasks will have NULL category, meaning the category breakdown won't work for historical data

**Analysis:** `ALTER TABLE ADD COLUMN` in SQLite adds the column with NULL for all existing rows. The spec needs a post-migration data update script to populate `category`, `difficulty`, and `temperature` for the 9 existing tasks. Without this, the category breakdown in the dashboard will show "unknown" for all historical results.

**Fix:** Add a migration step: "After ALTER TABLE, run UPDATE statements to set category, difficulty, and temperature for the 9 existing built-in tasks using the category table defined in §2.6."

---

### H-2 → M-2: `canary_task_baselines` per-task drift fix requires historical per-task data that may not exist

**Severity:** MEDIUM — statistical validity gap

**Which trap/rule:** Coding-fidelity bug pattern 4.3 (Spec-to-implementation gap), Requirements-fidelity Trap 4 (Wrong success metrics)

**Evidence:**
- **Spec-057 §2.3:** "AFTER (correct): compares single task accuracy vs THAT TASK'S baseline"
- The `canary_task_baselines` table needs per-task accuracy history to compute a baseline
- Current `canary_results` table stores per-task accuracy per run — but the `BaselineManager.compute_baseline()` method aggregates at the run level (`pass_count / total_tasks`), not per-task
- The spec doesn't define how per-task baselines are computed — from which data, using what method, minimum runs

**Analysis:** The fix is correct conceptually but the implementation requires:
1. A new `compute_per_task_baseline()` method in `BaselineManager`
2. Defining what "per-task accuracy" means across multiple runs (average accuracy? pass rate?)
3. Minimum runs per task per config_hash before a per-task baseline can be created (currently min_runs=3 at the run level)
4. How to handle tasks that were skipped (due to template variables) in some runs

**Fix:** Add to §2.3: "Per-task baseline is computed from the last N completed runs where the task was not skipped. Per-task accuracy = mean of trial accuracies across runs. Minimum 3 runs with that task completed. Stored in `canary_task_baselines` with (agent_name, config_hash, task_id) as the key."

---

### M-3: Temperature control assumes Hermes adapter supports temperature override

**Severity:** MEDIUM — hidden constraint

**Which trap/rule:** Requirements-fidelity Trap 5 (Hidden Constraints)

**Evidence:**
- **Spec-057 §2.3:** "The Hermes adapter passes `--temperature` flag or sets it in the API call"
- **Code verification (canary.py:234-244):** `TaskExecutor.execute()` builds a task object and calls `self.adapter.run_task(agent_name, task_obj)`. The task object has fields: id, task_name, agent_name, input_text, context_text, expected_output — **no temperature field**
- **Code verification (benchmark/adapters/hermes.py):** The adapter calls `hermes chat -q "..."` via subprocess — no temperature flag is passed

**Analysis:** The spec says the adapter "passes `--temperature` flag" but:
1. The task object built by TaskExecutor doesn't include a temperature field
2. The adapter's `run_task()` method doesn't accept a temperature parameter
3. `hermes chat` CLI may or may not support a `--temperature` flag (unverified)

**Fix:** §2.3 should state: "Add `temperature` field to the task object constructed in `TaskExecutor.execute()`. Update `HermesBenchmarkAdapter.run_task()` to accept and pass `--temperature` to `hermes chat` CLI. Verify `hermes chat` supports this flag — if not, use the Hermes Python API directly with temperature parameter."

---

### M-4: Inspect AI integration (§3.1) references an external framework without version or API verification

**Severity:** MEDIUM — underspecified dependency

**Which trap/rule:** Requirements-fidelity Trap 5 (Hidden Constraints), Coding-fidelity bug pattern 4.10

**Evidence:**
- **Spec-057 §3.1:** "Inspect AI (UK AISI) is the recommended evaluation framework"
- "MIT licensed, Python-native" — not verified against current license
- "Canary tasks can be exported as Inspect AI task definitions" — no export format specified
- Phase 4 task says "Inspect AI export format | ~4h | New `capability/inspect_export.py`" — but no format spec

**Analysis:** The spec recommends a framework without verifying:
1. Current version and API stability
2. Whether Inspect AI supports the assertion types ObserveCo needs (LLM judge, code execution, etc.)
3. Whether the export import path is feasible
4. Whether Inspect AI is actively maintained (UK AISI project status)

**Fix:** Add a §3.1.1 "Verification" subsection: "Inspect AI v0.3+ supports custom scorers, LLM-as-judge, and task import/export via Python API. Verify current version and API before implementation. If Inspect AI is unavailable or incompatible, fall back to maintaining the custom Scorer with the enhancements from §2.2."

---

## LOW Findings

### L-1: Master plan §57 row uses "v0.6.0" version tag but obs-spec-056 also uses "v0.6.0"

**Severity:** LOW — versioning clarity

**Evidence:**
- **Master plan §57:** "Spec (v0.6.0)" — Benchmark Methodology Upgrade
- **Master plan §56:** "Spec (v0.6.0)" — Automated Harness Optimization Loop
- Both specs target the same version

**Analysis:** Having two specs target the same version is fine — they can be parallel workstreams. But the dependency should be clarified: obs-spec-056 (harness optimization) depends on obs-spec-057's dev/test split (§2.5) and per-task baselines. obs-spec-057 should be implemented first.

**Fix:** Add to master plan §57: "Blocks obs-spec-056 (harness optimization requires dev/test split and per-task baselines)."

---

## Cross-Spec Consistency Matrix

| Claim | Spec-057 | Spec-050 | Spec-051 | Spec-052 | Spec-055 | Reality |
|-------|----------|----------|----------|----------|----------|---------|
| New tables defined | `canary_judge_cache`, `canary_task_baselines` | Full schema for 8 tables | N/A | N/A | N/A | **Missing schema** — C-1 |
| `llm_service.call_llm` exists | Used in code sample | N/A | Deferred to v1.1 | N/A | N/A | **Unverified** — H-1 |
| Adapter supports temperature | "passes `--temperature` flag" | N/A | ❌ — §2.2 lists adapter fields, no temperature | N/A | N/A | **Unverified** — M-3 |
| `canary_tasks` mutable | ALTER TABLE ADD COLUMN | Defines table with specific columns | N/A | N/A | Defines task schema | ✅ — compatible |
| Assertion types (current) | References 5 existing types | N/A | Lists 5 types | N/A | Lists 5 types | ✅ — matches (exact_match, contains, numeric_range, regex, llm_judge) |
| Assertion types (new) | Adds 6 new types | N/A | N/A | N/A | N/A | ✅ — all new, no conflicts |
| Per-task drift fix | Compare vs per-task baseline | N/A | Aggregate only | Aggregate only | N/A | ✅ — 057 fixes existing spec gap |
| Trials default | Increase 3 → 10 | N/A | Default 3 | N/A | Default 3 | ✅ — 057 supersedes 051/055 |
| Template variables | Eliminate all | N/A | Tasks have templates | N/A | Tasks have templates, §2.2 | ✅ — 057 supersedes |
| Dev/test split | Define 3 dev, 6 test | N/A | `split` column exists, all=all | N/A | N/A | ✅ — 057 activates unused feature |
| sentence-transformers dep | New dep | N/A | N/A | N/A | N/A | **Not in pyproject.toml** — H-2 |

---

## Master Fidelity Gate Scoring

### Layer A: Requirements Fidelity (14 pts, threshold ≥11) — ✅ PASS

| Item | Score | Notes |
|------|-------|-------|
| A1: RDR written | 2/3 | No formal RDR, but problem statement + design + constraints are clear |
| A2: 6 spec traps checked | 2/3 | Most traps addressed; 3 hidden constraints found (H-1, H-2, M-3) |
| A3: State matrix ≥4 states | 1/2 | No state matrix for new assertion types or new tables |
| A4: Success metrics | 2/3 | §5 has 6 measurable metrics — good. But no false-positive rate target for LLM judge |
| A5: Constraints register | 2/2 | §6 has 5 constraints with type annotations. Improved from specs 050-055 |
| A6: Cross-references verified | 2/1 | Cross-refs to spec-050, 051, 055 are valid. Master plan row accurate. |
| **Total** | **11/14** | **✅ PASS** |

### Layer B: Coding Fidelity (14 pts, threshold ≥11) — ❌ FAIL

| Item | Score | Notes |
|------|-------|-------|
| B1: Spec grounding | 2/3 | Most claims verified — identified llm_service unverified (H-1), adapter temperature unverified (M-3) |
| B2: Implementation fidelity | 1/3 | Missing table schema (C-1), code_executable sandbox underspecified (H-3) |
| B3: No f-string leaks | 2/2 | N/A for spec audit |
| B4: TestClient assertions | 1/2 | No test plan in spec |
| B5: Dependency verification | 1/2 | sentence-transformers not verified (H-2), llm_service not verified (H-1) |
| B6: Master plan updated | 2/2 | Master plan updated, agent-quality-brief updated |
| **Total** | **9/14** | **❌ FAIL** |

### Layer C: UX Fidelity (14 pts, threshold ≥11) — ❌ FAIL

| Item | Score | Notes |
|------|-------|-------|
| C1: Perception | 2/3 | Category breakdown mentioned but no UI mockup or layout spec |
| C2: Confidence | 2/3 | Fallbacks mentioned (contains → semantic_similarity → llm_judge) but no UI for showing which assertion failed |
| C3: Friction | 2/3 | Task creation with new fields mentioned but no form layout |
| C4: Accessibility | 1/2 | No accessibility considerations for new assertion type dropdown |
| C5: Loading states | 2/2 | LLM judge latency acknowledged (caching, cost guard) |
| C6: Entity-type rendering | 1/1 | N/A for this spec type |
| **Total** | **10/14** | **❌ FAIL** |

### Layer D: System-Design Fidelity (18 pts, threshold ≥14) — ❌ FAIL

| Item | Score | Notes |
|------|-------|-------|
| D1: Data pipeline | 2/3 | Writer/reader chain partially defined; missing how canary_judge_cache integrates with Scorer |
| D2: Lifecycle tests | 1/3 | No lifecycle tests for new assertion types or new tables |
| D3: 9 lenses | 2/3 | Migration lens covered (M-1), security lens partially covered (H-3). Backup/restore not mentioned for new tables. |
| D4: Heartbeat | 2/2 | N/A for this spec type |
| D5: Cross-platform | 1/2 | sentence-transformers on Mac Mini (Metal?) not verified. Mac Mini has ARM64. |
| D6: Crash resilience | 2/3 | LLM judge caching acknowledged but no crash recovery for partial judge results |
| D7: Data continuity (GS-017) | 2/2 | Migration plan preserves existing canary_tasks data via ALTER TABLE |
| D8: Cross-spec lifecycle | 1/2 | Dependency on obs-spec-056 not explicitly declared (L-1) |
| **Total** | **13/18** | **❌ FAIL** |

### Overall: 43/60 (threshold 47/60 = 80%) — ❌ FAIL

---

## Summary of Required Fixes Before Implementation

| # | Severity | Fix |
|---|----------|-----|
| 1 | **CRITICAL** | Define schema for `canary_judge_cache` and `canary_task_baselines` tables (C-1) |
| 2 | **HIGH** | Verify `llm_service.call_llm` interface and update code sample (H-1) |
| 3 | **HIGH** | Document sentence-transformers model, lazy loading, install mechanism (H-2) |
| 4 | **HIGH** | Specify code_executable sandbox mechanism or defer to v0.7.0 (H-3) |
| 5 | **MEDIUM** | Add post-migration UPDATE statements for existing 9 tasks (M-1) |
| 6 | **MEDIUM** | Define per-task baseline computation method (M-2) |
| 7 | **MEDIUM** | Verify Hermes adapter temperature support (M-3) |
| 8 | **MEDIUM** | Add Inspect AI API verification subsection (M-4) |
| 9 | **LOW** | Add dependency note: obs-spec-057 blocks obs-spec-056 (L-1) |

---

## Comparison with Prior Audit (specs 050-055)

| Metric | This Audit (057) | Prior Audit (050-055) | Change |
|--------|:----------------:|:--------------------:|--------|
| Total findings | 9 | 20 | Fewer (smaller scope, single spec) |
| CRITICAL | 1 | 2 | Same pattern — missing schema |
| HIGH | 3 | 3 | Same pattern — hidden constraints |
| MEDIUM | 4 | 12 | Better — claims verified against code |
| LOW | 1 | 3 | Similar |
| Requirements Fidelity | 11/14 ✅ | 10/14 ❌ | **Improved** — better constraints, verified cross-refs |
| Coding Fidelity | 9/14 ❌ | 8/14 ❌ | **Improved** — more claims verified, but still missing schema |
| UX Fidelity | 10/14 ❌ | 9/14 ❌ | **Improved** — fallbacks acknowledged but still no mockups |
| System-Design | 13/18 ❌ | 12/18 ❌ | **Improved** — migration lens covered, but new tables have no spec |
| **Total** | **43/60** | **39/60** | **+4 points** — meaningful improvement in verification rigour |

**Key improvement:** This spec actually verifies claims against existing code (canary.py, baseline.py, db.py) and references real data (9 existing tasks, template variable problem). The prior specs were written without code verification. The remaining gap is schema definitions for new tables — the same failure mode as the prior audit.