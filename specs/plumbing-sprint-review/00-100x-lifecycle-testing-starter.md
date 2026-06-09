# 100x Full Lifecycle Testing & Release Mode — ObserveCo v0.2.0

## Mission

We have completed the latest sprint. Before marking anything final or starting the next sprint, we will run the complete end-to-end lifecycle testing process from all 7 playbooks.

**This test incorporates launch-readiness checks.** Beyond the standard 8-phase lifecycle, each phase now includes explicit launch-gap gates (G1–G13) that must pass before a v0.2.0 release is greenlit.

## Launch Gaps (Must Address Per Phase)

| ID | Gap | Phase | Severity | Pass Criterion |
|----|-----|-------|----------|----------------|
| G1 | CI failing — 419 ruff lint errors across 8 matrix configs | Phase 3 | P0 | `ruff check src/observeco/` returns 0 errors |
| G2 | F8 first-run fails — "actionable" keyword missing from landing page | Phase 3 | P1 | First-run audit passes F8 sub-check |
| G3 | No clean-room install test — always tests via editable install | Phase 3 | P0 | `pip install dist/*.whl` → `observeco --version` works in temp venv |
| G4 | No CHANGELOG.md | Phase 6 | P2 | File exists with at least v0.1.0 and v0.2.0 entries |
| G5 | No SECURITY.md | Phase 5 | P2 | File exists with disclosure contact |
| G6 | No CODE_OF_CONDUCT.md | Phase 5 | P2 | File exists with standard terms |
| G7 | No .env.example | Phase 3 | P2 | File exists documenting all required env vars |
| G8 | No error/troubleshooting/FAQ docs | Phase 1 | P2 | At minimum a TROUBLESHOOTING.md or FAQ.md section in README |
| G9 | No migration system — no hook for v0.1→v0.2 schema upgrades | Phase 2 | P1 | Migration module exists with v0.1→v0.2 path |
| G10 | Test count unknown — comprehensive test plan (200+ tests) all marked ❓ | Phase 3 | P0 | Test suite runs ≥50 passing tests (including lifecycle tests) |
| G11 | No automated release checklist | Phase 6 | P1 | Release checklist document exists with pre-publish gates |
| G12 | No clean-room install test in CI | Phase 3 | P1 | CI has a job that builds sdist, installs in fresh venv, runs smoke test |
| G13 | No startup environment validation | Phase 2 | P2 | Doctor/diagnostics module validates deps, ports, config on first run |

We will do this **one phase at a time**. After each phase you must output:

"PHASE X COMPLETE — Evidence: [summary]"

Then stop and wait for my explicit confirmation before starting the next phase.

The 8 phases (each with launch-gap gate items):

1. **Requirements Fidelity** — G8 (troubleshooting docs)
2. **System Design** — G9 (migration system), G13 (env validation)
3. **Coding Fidelity** — G1 (CI lint), G2 (first-run), G3 (clean install), G7 (.env.example), G10 (test count), G12 (CI install test)
4. **UX Human Lens** — Prepare human test protocol only
5. **Agent Governance** — G5 (SECURITY.md), G6 (CODE_OF_CONDUCT.md)
6. **Master Fidelity Gate** — G4 (CHANGELOG.md), G11 (release checklist)
7. **Human Test** — I will run it and report back
8. **Meta & Evolution** — Lessons Learned

Start with Phase 1 only.
Output the full SCOPE header first, then begin Phase 1.
