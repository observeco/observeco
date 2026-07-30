# Playbook Audit — 2026-07-22

**Auditor:** Spectrum
**Playbook:** `lopopolo/harness-engineering/playbooks/improve-harness.md` (Bounded-Job Playbook)
**Scope:** obs-spec-082 (Coverage Tab — Replace Discover Panel)

---

## Audit Criteria

The bounded-job playbook defines 8 steps. Each spec is scored against each step:

| Step | Requirement |
|------|-------------|
| 1. Record the job contract | Target, external state, fixed worker config, accepted outcome, evidence |
| 2. Observe the baseline | Observable evidence, not summary alone |
| 3. Locate the earliest failed handoff | Classify the gap (context/capability/domain/authority/proof/feedback/worker) |
| 4. State one intervention hypothesis | Smallest reversible change, expected mechanism |
| 5. Implement and verify at the claim boundary | Native checks + user journey |
| 6. Run a fresh trajectory | Same conditions, fresh session, isolated state |
| 7. Retain, revise, or remove | Decision with evidence, carrying cost |
| 8. Preserve a compact result record | Structured output with known limits |

---

## obs-spec-082: Coverage Tab — Replace Discover Panel

| Step | Score | Notes |
|------|-------|-------|
| **1. Job contract** | ✅ PASS | §1 Problem clearly states the target (Discover panel), the failure mode (~10 patch rounds without resolution), the root cause (overlay container is wrong for this interaction model), and the accepted outcome (stable tab with table, no overlay). Evidence: documented patch history and launch-blocking status. |
| **2. Baseline** | ✅ PASS | §2 What Exists inventories all relevant components with file locations, line numbers, and status. Documents the existing Discover panel (badge, panel div, scanner, API, CSS, JS, dismissed_gaps table, prevention_skills table, tab system, learning section). |
| **3. Failed handoff** | ✅ PASS | Gap classified as **worker** in §1 (the overlay container — `position: fixed` with HTMX swaps — is the wrong worker for a browsable list with per-row actions). The dashboard's existing tab+table pattern (Fleet, Alerts, Error Timeline) is the correct worker. |
| **4. Intervention hypothesis** | ✅ PASS | §3 Architecture defines the intervention: kill the overlay, convert badge to nav link, add Coverage tab with table layout. Expected mechanism: "no overlay, no OOB, no event bubbling, no z-index conflicts — uses dashboard's existing tab pattern." Smallest reversible change: yes — adds a tab without removing the old panel first (§8 Migration sequence: implement new endpoints first, then add tab, then remove old code). |
| **5. Verify at claim boundary** | ✅ PASS | §7 Success Criteria has 13 numbered criteria with specific verification commands (curl, browser, grep, pytest). Covers: badge count via JSON endpoint, tab navigation, add/dismiss/bulk actions, empty state, no overlay remnants, event bubbling absence, learning section. Missing: "verify _render_coverage() returns valid HTML" — **Fix:** Add criterion #14: "`curl /api/discover/coverage` returns valid HTML with `coverage-table` and `coverage-learning` divs." |
| **6. Fresh trajectory** | ✅ PASS | §8 Migration defines a 7-step sequence that implements new endpoints before removing old ones — preserves rollback capability. §5 Edge Cases covers all states (no gaps, all dismissed, special characters, mobile) — these function as fresh-trajectory scenarios. |
| **7. Retain/revise/remove** | ✅ PASS | §9 "What This Eliminates" documents the carrying cost of the old overlay (8 specific problems). The Retention decision is explicit: **remove** the overlay, replace with tab. The spec does not specify a rollback condition — **Minor:** Add "If Coverage tab causes dashboard load time >2s, revert to badge-only (no tab, no panel)." |
| **8. Compact result** | ✅ PASS | §9 elimination table concisely maps each old problem to why it's gone. Spec is 259 lines — well-scoped, no filler. |

**Verdict:** ✅ PASS with 1 minor note (rollback condition) and 1 optional criterion (add #14 to §7 for HTML validity check).

---

## Summary

| Spec | Status | Notes |
|------|--------|-------|
| obs-spec-082 Coverage Tab | ✅ PASS | 2 minor: add HTML validity check to §7 (criteria #14), add rollback condition to §8. Both optional — spec is structurally sound. |

**Overall:** PASS. The spec is well-structured, correctly identifies the root cause (wrong container), and proposes the right fix (use dashboard's existing tab pattern). The 13 success criteria are specific and testable. The migration sequence preserves rollback. No structural issues.
