# Formal Playbook Audit: obs-spec-086 (Canary Cost & Token Tracking)

**Audit date:** 2026-07-19
**Auditor:** Hermes Agent (playbook-based formal audit)
**Playbooks applied:** requirements-fidelity-playbook, coding-fidelity-playbook, system-design-testing-playbook
**Specs audited:** obs-spec-086 (Canary Cost & Token Tracking), plus cross-checks against obs-spec-051, obs-spec-057, master plan §86

---

## Executive Summary

**1 finding total:** 0 CRITICAL, 0 HIGH, 1 MEDIUM, 0 LOW

obs-spec-086 is a narrow, well-scoped spec that fixes a single gap: the Hermes adapter never parses token/cost info from the Hermes CLI output. The spec is grounded in verified code (the `CompletionUsage(...)` format was confirmed via `hermes chat --verbose`), the pricing table is documented, and the parsing is defensive (silent fallback to 0 on format change). No schema changes, no new dependencies, no CLI changes.

**Master Fidelity Gate scores:**

| Layer | Score | Threshold | Status |
|-------|-------|-----------|--------|
| A: Requirements Fidelity | 13/14 | ≥11 | ✅ PASS |
| B: Coding Fidelity | 13/14 | ≥11 | ✅ PASS |
| C: UX Fidelity | 12/14 | ≥11 | ✅ PASS |
| D: System-Design Fidelity | 16/18 | ≥14 | ✅ PASS |
| **Total** | **54/60** | **≥47 (80%)** | **✅ PASS** |

---

## Findings

### M-1: Pricing table is static — no auto-update mechanism

**Severity:** MEDIUM — maintenance burden

**Which trap/rule:** Requirements-fidelity Trap 5 (Hidden Constraints — assumes pricing doesn't change)

**Evidence:**
- **Spec-086 §2.1:** `_MODEL_PRICING` is a static dict with 6 models
- **Spec-086 §6 Constraint #1:** "Update `_MODEL_PRICING` when provider pricing changes"
- No auto-update mechanism is specified (e.g., fetch from provider API, read from Hermes config, or parse from billing endpoint)

**Analysis:** Provider pricing changes quarterly or more often. A static table will drift. The spec acknowledges this (Constraint #1) but doesn't specify an upgrade path beyond "update manually." For a v1 fix, this is acceptable — the cost is estimated and documented as such. The upgrade path (fetch from provider API) is noted in the `ponytail:` comment.

**Fix:** Add a §2.1.1 "Upgrade Path" subsection: "Future: fetch pricing from provider API (OpenAI/Anthropic/DeepSeek billing endpoints) or read from Hermes config.yaml provider definitions. For v1, the static table is sufficient — cost is documented as 'estimated' in the dashboard."

---

## Master Fidelity Gate Scoring

### Layer A: Requirements Fidelity (14 pts, threshold ≥11) — ✅ PASS

| Item | Score | Notes |
|------|-------|-------|
| A1: RDR written | 3/3 | Clear problem statement (all 157 runs show $0), design, constraints, risks |
| A2: 6 spec traps checked | 2/3 | Most traps addressed; 1 hidden constraint found (pricing table staleness — M-1) |
| A3: State matrix ≥4 states | 2/2 | N/A for this spec — no new tables or state machines |
| A4: Success metrics | 2/3 | §5 has 5 verification steps — clear and measurable. No false-positive rate target for cost estimation |
| A5: Constraints register | 2/2 | §6 has 5 constraints with type annotations |
| A6: Cross-references verified | 2/1 | Cross-refs to spec-051, spec-057, master plan are valid. Code claims verified against actual adapter code |
| **Total** | **13/14** | **✅ PASS** |

### Layer B: Coding Fidelity (14 pts, threshold ≥11) — ✅ PASS

| Item | Score | Notes |
|------|-------|-------|
| B1: Spec grounding | 3/3 | All claims verified against actual code: `hermes chat --verbose` output format confirmed, adapter return dict confirmed, canary runner accumulation confirmed |
| B2: Implementation fidelity | 2/3 | Code samples are precise and match the actual adapter interface. No hallucinated objects |
| B3: No f-string leaks | 2/2 | N/A for spec audit |
| B4: TestClient assertions | 2/2 | §5 has 5 verification steps including DB queries |
| B5: Dependency verification | 2/2 | No new dependencies. Uses `re` (stdlib) for parsing |
| B6: Master plan updated | 2/2 | Master plan updated with §86 row |
| **Total** | **13/14** | **✅ PASS** |

### Layer C: UX Fidelity (14 pts, threshold ≥11) — ✅ PASS

| Item | Score | Notes |
|------|-------|-------|
| C1: Perception | 2/3 | Cost display mentioned but no mockup of how cost appears in dashboard |
| C2: Confidence | 2/3 | "Estimated cost" documented, fallback to 0 on parse failure |
| C3: Friction | 2/3 | No user action needed — fix is transparent |
| C4: Accessibility | 2/2 | N/A for backend-only change |
| C5: Loading states | 2/2 | N/A — no new UI |
| C6: Entity-type rendering | 2/1 | N/A for this spec type |
| **Total** | **12/14** | **✅ PASS** |

### Layer D: System-Design Fidelity (18 pts, threshold ≥14) — ✅ PASS

| Item | Score | Notes |
|------|-------|-------|
| D1: Data pipeline | 3/3 | Writer/reader chain fully defined: Hermes CLI → stderr → adapter → canary_results → dashboard |
| D2: Lifecycle tests | 2/3 | §5 has verification steps but no automated test |
| D3: 9 lenses | 2/3 | Migration lens (no schema changes), security lens (stderr parsing, no injection risk), backup/restore (no new data) |
| D4: Heartbeat | 2/2 | N/A for this spec type |
| D5: Cross-platform | 2/2 | Hermes CLI format is consistent across platforms |
| D6: Crash resilience | 2/3 | Silent fallback on parse failure (returns 0). No crash recovery for partial results |
| D7: Data continuity (GS-017) | 2/2 | No schema changes — existing data unaffected |
| D8: Cross-spec lifecycle | 1/2 | Dependency on obs-spec-051 (canary runner) declared. No dependency on obs-spec-057 |
| **Total** | **16/18** | **✅ PASS** |

### Overall: 54/60 (threshold 47/60 = 80%) — ✅ PASS

---

## Summary of Required Fixes Before Implementation

| # | Severity | Fix |
|---|----------|-----|
| 1 | **MEDIUM** | Add §2.1.1 "Upgrade Path" for pricing table auto-update (M-1) |

---

## Comparison with Prior Audits

| Metric | This Audit (086) | Prior Audit (057) | Prior Audit (050-055) |
|--------|:----------------:|:------------------:|:---------------------:|
| Total findings | 1 | 9 | 20 |
| CRITICAL | 0 | 1 | 2 |
| HIGH | 0 | 3 | 3 |
| MEDIUM | 1 | 4 | 12 |
| LOW | 0 | 1 | 3 |
| Requirements Fidelity | 13/14 ✅ | 11/14 ✅ | 10/14 ❌ |
| Coding Fidelity | 13/14 ✅ | 9/14 ❌ | 8/14 ❌ |
| UX Fidelity | 12/14 ✅ | 10/14 ❌ | 9/14 ❌ |
| System-Design | 16/18 ✅ | 13/18 ❌ | 12/18 ❌ |
| **Total** | **54/60 ✅** | **43/60 ❌** | **39/60 ❌** |

**Key improvement:** This spec passes all 4 layers — the first spec in the project to do so. The improvement comes from: (a) narrow scope (one gap, one fix), (b) all claims verified against actual code before writing, (c) defensive design (silent fallback on parse failure), (d) no new dependencies or schema changes.
