# MemoHarness Playbook Audit — ObserveCo v0.7.0 Spec Updates
**Date:** 2026-07-19
**Auditor:** coding-fidelity + requirements-fidelity + system-design playbooks
**Scope:** Master plan lines 65-68 (row #56), 2649-2653 (roadmap v0.7.0), 2670-2674 (What Ships When), obs-spec-056 line 9 vs actual codebase

---

## TL;DR

The v0.7.0 MemoHarness upgrade references describe capabilities that **do not exist in the codebase**. The entire "dual-layer experience bank," "per-case retrieval by similarity," and "6 editable control dimensions" are **spec-only**. The underlying v0.6.0 harness optimizer has a documented no-op (`_apply_edit`) rendering promotion meaningless. Every line of the v0.7.0 spec change claims infrastructure that has zero lines of implementation.

---

## Finding Summary

| # | Severity | Finding | Playbook Trap |
|---|----------|---------|---------------|
| 1 | **CRITICAL** | Entire MemoHarness experience bank is spec-only — zero code | Coding-fidelity 4.3 (spec-to-implementation gap), Requirements-fidelity Trap 1 |
| 2 | **CRITICAL** | LeakageAudit from spec §2.4 does not exist in code | Coding-fidelity 4.9 (spec misinterpretation) |
| 3 | **HIGH** | 6 control dimensions don't exist — HarnessConfig has 5 axes, different names | Requirements-fidelity Trap 6 (contradictory refs) |
| 4 | **HIGH** | Spec architecture diagram (Proposer, PromotionGate, LeakageAudit classes) is fiction | Coding-fidelity 4.10 (hallucinated objects) |
| 5 | **HIGH** | _apply_edit is a documented no-op — optimization loop cannot change anything | Coding-fidelity 4.14 (no-op where spec implies evolution) |
| 6 | **MEDIUM** | Success metrics (§7) are untestable because harness never changes | Requirements-fidelity Trap 4 |
| 7 | **MEDIUM** | No experience bank tables exist (no vector store, no similarity search) | System-design Trap 2 (coverage gap) |
| 8 | **LOW** | `proposer_model` parameter in spec does not exist in constructor | Coding-fidelity 4.9 |

---

## Detailed Findings

### CRITICAL #1: MemoHarness experience bank is entirely spec-only

**Spec claims (3 locations):**

1. **Master plan row #56 (line 68):** "v0.7.0 upgrade: Experience-based adaptation (MemoHarness 2026): dual-layer experience bank, per-case retrieval by similarity, 6 editable control dimensions (context, tools, orchestration, memory, decoding, output)"
2. **Roadmap v0.7.0 (line 2653):** "dual-layer experience bank (per-case diagnoses + global patterns from pulse_log/errors/token_logs), per-case retrieval by similarity, 6 editable control dimensions"
3. **What Ships When (line 2674):** "Experience-based harness adaptation (MemoHarness 2026): dual-layer experience bank, per-case retrieval, 6 control dimensions"
4. **obs-spec-056 line 9:** "v0.7.0 upgrade: Huang et al., 'MemoHarness: Agent Harnesses That Learn from Experience'"

**Code reality:**
```
$ grep -r "MemoHarness\|experience_bank\|control_dimension\|per.case.*retrieval" src/ --include="*.py"
(no matches)
```

- **No experience bank tables** in `db.py`. The only harness-related tables are `harness_optimization_runs`, `harness_edits`, `harness_eval_runs` (Migration 62) — these track optimization metadata, not experiences.
- **No vector/similarity search** anywhere in the capability module.
- **No code reads pulse_log/errors/token_logs for experience-based adaptation** — those tables exist for monitoring, not for harness evolution.
- **No control dimension mutation infrastructure.** `HarnessConfig` is a frozen dataclass with 5 static axes.

**Classification:** CONFIDENT — spec is wrong, code is right (v0.7.0 was never built).

**Impact:** Anyone reading the master plan believes this feature exists or is close. The spec claims 4d effort but the feature has had 0 hours of implementation.

**Recommendation:** Either (a) move v0.7.0 to a "Planned" section with no checkmarks, or (b) add a `🔴 Not Started` status badge to row #56. Do NOT leave it as if it's part of the same feature row as v0.6.0 without clear demarcation.

---

### CRITICAL #2: LeakageAudit from spec §2.4 missing in code

**Spec claim (obs-spec-056 §2.4):**
```python
class LeakageAudit:
    def check(self, candidate, report) -> bool:
        """Reject if candidate touched the test split."""
        for task_id in [r["task_id"] for r in report.per_task]:
            task = self._get_task(task_id)
            if task and task.get("split") == "test":
                return False
        return True
```
Spec §5 constraint #6: "Leakage audit is non-negotiable. Any candidate that touches test split is rejected. No exceptions."

**Code reality:** No `LeakageAudit` class exists anywhere. The `HarnessOptimizer.optimize()` method runs on both dev and test splits (lines 224, 256) but there is **zero code that checks whether test-split tasks were touched during dev-split optimization**. The leakage audit is simply missing.

**Classification:** UNCERTAIN — the spec explicitly says "non-negotiable" but the code has zero implementation. No commit message or ADR explains the omission.

**Recommendation:** Flag to user: "Spec §2.4 describes LeakageAudit as non-negotiable, but the code has zero leakage checking. Was this deferred or forgotten?"

---

### HIGH #3: 6 control dimensions don't exist — HarnessConfig has 5 axes

**Spec claims:** "6 editable control dimensions: context, tools, orchestration, memory, decoding, output"

**Code reality:** `HarnessConfig` (`benchmark/grid/configs.py`) has 5 axes:
1. Per-call timeout + retry policy (`call_timeout_seconds`, `max_retries`, `retry_delay_seconds`)
2. Tool-result/error feedback (`tool_feedback_mode`)
3. Context management (`context_mode`, `context_window_turns`)
4. Self-check (`self_check`)
5. System prompt style (`system_prompt_style`)

These are **static configuration variations for grid evaluation** — they are NOT "editable control dimensions" that the harness optimizer can mutate. They don't map to the spec's claimed dimensions: no "orchestration" axis, no "decoding" axis, no "output" axis. "Tools" maps loosely to `tool_feedback_mode`. "Memory" maps loosely to `context_mode`. That's 2/6.

**Classification:** CONFIDENT — spec dimension names are aspirational, code axes are what was actually built.

**Recommendation:** Update the spec to reflect the 5 actual axes or rename the master plan to remove the specific 6-dimension claim until implemented.

---

### HIGH #4: Spec architecture diagram describes classes that don't exist

**Spec claims (obs-spec-056 §2.1-2.4):**
- `class HarnessOptimizer` with `self.proposer = Proposer(model=proposer_model)`, `self.gate = PromotionGate()`, `self.audit = LeakageAudit()`
- `class Proposer` with `.propose()` method
- `class PromotionGate` with `.score()`, `.get_incumbent_score()`, `.promote()` methods
- `class LeakageAudit` with `.check()` method

**Code reality:** 
- `Proposer` does not exist — `_propose_edit()` is a method on `HarnessOptimizer`
- `PromotionGate` does not exist — `_check_promotion()` is a method on `HarnessOptimizer`
- `LeakageAudit` does not exist — no leakage checking at all
- `HarnessOptimizer.__init__` takes `(db, runner)`, NOT `(db, canary_runner, proposer_model)`

**Classification:** CONFIDENT — spec was aspirational architecture, real code consolidated into methods.

**Recommendation:** Update obs-spec-056 §2 architecture section to match the actual code structure, or note that the standalone class decomposition was deferred.

---

### HIGH #5: _apply_edit is a documented no-op

**Code evidence (harness.py lines 7-11, 249-250, 267):**
```python
# Module-level ponytail:
# ponytail: The apply-edit step is a no-op on the actual agent harness because we
# cannot hot-swap SOUL.md mid-run without profile management.

# In optimize():
# ponytail: _apply_edit is a no-op (can't hot-swap agent profile).
# We re-run against the same agent.

# Promotion:
best_harness = incumbent_snapshot  # ponytail: snapshot doesn't change
```

**What this means:** The optimization loop proposes edits, evaluates them (on the unchanged agent), and "promotes" them — but the agent **never actually changes**. The loop only measures proposer quality, not harness evolution. The `promoted=True` flag in `harness_optimization_runs` means "the proposal would have improved things" — not "the agent's harness has been upgraded."

**Roadmap acknowledges this** (line 2653): "Fixes: apply-edit no-op, frontier inheritance, candidate tracking" — but the master plan row #66 still says "Promotion gate (blended score ≥1pp over incumbent)" without noting the edit is never applied.

**Classification:** CONFIDENT — documented in code, partially acknowledged in roadmap, NOT acknowledged in feature row #56.

**Recommendation:** The feature row should explicitly state "Evaluation-only: edits are proposed and scored but NOT applied to the live agent (cannot hot-swap SOUL.md)." The roadmap's "fixes" list confirms this is a known gap — make it visible in the status row.

---

### MEDIUM #6: Success metrics are untestable because harness never changes

**Spec §7 success metrics:**
- "Frontier improvement: Measurable score gain over vanilla baseline" — tracked via `harness_frontier.score` vs baseline
- "Promotion rate: 20-40% of candidates promoted"
- "Loop completion: 95% of iterations complete without infra error"

**Code reality:** 
- `harness_frontier` table does NOT exist. The spec says Migration 52 should create it, but the actual Migration 62 creates `harness_optimization_runs`, `harness_edits`, `harness_eval_runs` — no frontier table.
- Since `_apply_edit` is a no-op, "frontier improvement" is meaningless — the harness never changes, so there's nothing to compare against a baseline.
- Promotion rate measures proposer quality, not harness improvement.

**Classification:** CONFIDENT — metrics reference a table that doesn't exist and measure a mutation that doesn't happen.

**Recommendation:** Replace success metrics with what's actually measurable: "Proposer quality: % of edits classified as 'generalizable'" and "Proposer cost: <$0.50 per iteration." Remove frontier-based metrics until edit application works.

---

### MEDIUM #7: No experience bank infrastructure (tables, similarity, retrieval)

**Spec claims:** "dual-layer experience bank (per-case diagnoses + global patterns from pulse_log/errors/token_logs)"

**Reality of existing tables:**
- `pulse_log` — heartbeat records (agent_name, status, latency, timestamp) — exists
- `errors` — error log (agent_name, error_type, error_message, severity, timestamp) — exists
- `token_logs` — per-turn token usage (agent_name, turn_id, total_tokens, cost, etc.) — exists

These tables ARE the raw data the spec claims will feed the experience bank. But:
- **Zero code reads these tables for adaptation purposes**
- **No aggregation/pattern-extraction from these tables**
- **No `harness_experiences` table to store extracted patterns**
- **No similarity search infrastructure** (no embeddings, no vector store)

The closest thing to similarity search in the codebase is in `history_tasks.py` line 98: `ponytail: naive keyword overlap, not embeddings`.

**Classification:** CONFIDENT — the raw data sources exist but the adaptation layer that reads them does not.

**Recommendation:** Add explicit "Pre-requisites not yet built" flags to the roadmap v0.7.0 entry.

---

### LOW #8: `proposer_model` parameter mismatch

**Spec (obs-spec-056 §2.1):**
```python
class HarnessOptimizer:
    def __init__(self, db, canary_runner, proposer_model="claude-opus-4.8"):
```

**Code:**
```python
class HarnessOptimizer:
    def __init__(self, db: Database | None = None, runner: CanaryRunner | None = None):
```

No `proposer_model` parameter. The model is determined by whatever `llm_service.ask()` routes to at runtime.

**Classification:** CONFIDENT — cosmetic spec drift.

**Recommendation:** Update spec constructor signature.

---

## Requirements-Fidelity 6-Trap Assessment

### Trap 1: Happy Path Only — **FAIL**
- **No failure states described** for the experience bank. What happens when pulse_log is empty? What if errors table has zero rows for an agent? What if the similarity search returns no matches?
- The spec describes what the system *should* do ("learns from its own execution history") but zero error/empty/degraded states.

### Trap 2: Visuals Without States — **N/A**
- No mockups exist for the MemoHarness features. This is a pure infrastructure spec.

### Trap 3: Lifecycle Not Specified — **FAIL**
- How does the experience bank initialize? Warm-start vs cold-start?
- What happens when the agent's profile is deleted? Does the experience bank re-accumulate?
- How often is the bank updated? On every canary run? Periodically?
- What's the stale-experience pruning policy?

### Trap 4: No Success Metrics — **FAIL**
- Spec §7 metrics exist but are untestable (see Finding #6).
- No quantitative metric for "experience-based adaptation working" — no retrieval precision, no dimension-change effectiveness.

### Trap 5: Hidden Constraints — **WARNING**
- The spec claims 4d effort for the full MemoHarness upgrade. Given that the underlying v0.6.0 loop has 834 lines with 14 documented ponytails, 4d seems aggressively optimistic.
- Cross-platform constraint: if the experience bank uses embeddings (implied by "similarity"), that introduces a dependency (sentence-transformers, numpy) not in the current requirements.

### Trap 6: Contradictory Refs — **FAIL**
- **Master plan row #56 vs roadmap v0.7.0:** The feature row lists v0.6.0 and v0.7.0 as a single row (#56) with a combined estimate of ~9d — implying they're both in the same status category. But v0.6.0 is built (code exists, ponytails documented) while v0.7.0 has zero implementation.
- **obs-spec-056 §8 File Changes vs reality:** Spec lists `src/observeco/capability/optimizer.py` as the file — actual file is `src/observeco/capability/harness.py`. Spec lists Migration 52 — actual is Migration 62. Spec lists `harness_candidates`/`harness_frontier` tables — actual tables are `harness_optimization_runs`/`harness_edits`/`harness_eval_runs`.
- **Roadmap "fixes" vs feature row:** Roadmap acknowledges "apply-edit no-op" as a v0.7.0 fix, but the feature row describes the promotion gate as if it works.

---

## System-Design Assessment

### Data Pipeline for the Claimed Experience Bank

**Spec claim:** Writers = canary results + pulse_log + errors + token_logs → experience bank → similarity retrieval → harness adaptation

**Actual pipeline:**
```
Writers exist:           Readers don't:
pulse_log (daemon)   →  (nothing reads this for harness adaptation)
errors (daemon)      →  (nothing reads this)
token_logs (watch)   →  (nothing reads this)
canary_results (CLI) →  HarnessOptimizer._propose_edit() reads canary_results.per_task
                        but ONLY for the current run — no historical cross-referencing
```

**Gap:** The spec describes a "dual-layer" bank (per-case diagnoses + global patterns) but there's no infrastructure to extract per-case diagnoses from raw pulse/error/token data, and no infrastructure to aggregate global patterns across runs.

### Lifecycle Chain

**Spec implication:** Agent runs → canary evaluates → harness learns from pulse/error/token history → harness adapts → agent runs better

**Actual chain:** Agent runs → canary evaluates → LLM proposes edit → loop evaluates same unchanged agent → record stored in harness_optimization_runs → nothing changes

**Key missing link:** There is no bridge between "we observed the agent's execution patterns" and "we changed the agent's runtime behavior."

---

## Coding-Fidelity Assessment

| Pillar | Status | Detail |
|--------|--------|--------|
| Spec Grounding | ❌ | Spec references MemoHarness paper but code has zero MemoHarness concepts |
| Implementation Fidelity | ❌ | No experience bank, no retrieval, no 6 dimensions, no leakage audit |
| Verification Autonomy | ❌ | Success metrics reference non-existent frontier table |
| Anti-Hallucination | ❌ | Spec claims Proposer/PromotionGate/LeakageAudit classes that don't exist |
| Evolution & Regression | ❌ | Master plan shows combined v0.6.0+v0.7.0 status without indicating v0.7.0 isn't built |

---

## Fix Recommendations (Priority Order)

### Immediate (before next spec review)
1. **Split feature row #56** into two rows: #56 (v0.6.0 — built with known no-ops) and #56b (v0.7.0 — not started). Different status badges.
2. **Update obs-spec-056 §2** to match actual code: method-based architecture, actual table names (Migration 62, not 52), actual file names (harness.py, not optimizer.py).
3. **Add explicit status to feature row #56:** "✅ Built (v0.6.0, evaluation-only — edits not applied)" — not "🔴 Spec."

### Short-term (when v0.7.0 planning begins)
4. **Write a standalone obs-spec for v0.7.0** that defines the experience bank schema, similarity search infrastructure, and 6 control dimensions with concrete definitions.
5. **Fix the no-op** before adding experience-based adaptation — a system that learns from experience but can't change anything is a dead end.
6. **Add the leakage audit** — it's labeled "non-negotiable" in the spec.

### Nice-to-have
7. Rename `harness_candidates`/`harness_frontier` references in spec to match actual schema names.
8. Add `proposer_model` parameter to `HarnessOptimizer.__init__`.

---

## Confidence Summary

| Classification | Count | Items |
|---------------|-------|-------|
| CONFIDENT (proven divergence) | 6 | #1, #3, #4, #5, #6, #7, #8 |
| UNCERTAIN (need user input) | 1 | #2 (LeakageAudit — was it deferred or forgotten?) |

The user must clarify whether LeakageAudit was intentionally omitted (scope cut during implementation) or accidentally forgotten.
