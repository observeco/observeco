# ObserveCo v0.2.0 — Engineering Test Plan (Rebuilt)

**Author:** Main
**Date:** 2026-06-10

## 0. Foundations (Read First)

Instead of reproducing the full 200+ test table here (it's stale — most entries are marked ❓), the **active** test plan is the 8-phase lifecycle test in this directory (`00-100x-lifecycle-testing-starter.md` + `01-phase-*.md` through `08-phase-8-meta-evolution.md`). 

Each phase includes:
1. **Playbook execution** (requirements, design, coding, UX, governance, fidelity, meta)
2. **Launch gap gates** (G1–G13) — pre-release must-pass items discovered during build audit

### Policy for the comprehensive test plan

- New tests should go in `tests/test_plumbing_sprint_review/` as proper pytest files
- Each test file maps to one fail mode from the lifecycle phases
- The comprehensive table in this file is a historical reference only — do NOT maintain it; migrate failing tests to `tests/` as pytest fixtures
- After the lifecycle test completes, this file should be replaced with a pointer to the actual test suite

### Key Integration Flows (11 total)
1. Fresh install → CLI help → —version
2. Clean-room sdist install → dashboard start → 200 OK
3. Dashboard → agents → pulse check → results DB
4. Dashboard → trial status → Pro upgrade → Stripe checkout → webhook → license activation
5. Dashboard → admin key gen → activate → Pro badge
6. Billing → configure → stripe key → checkout → portal
7. Chisel → trim drift compress on a profile
8. Heal → agent restart → verification
9. CRM → generate key → revoke → list keys
10. MCP → stdio mode → tool calls → response
11. Doctor → diagnostics → report
