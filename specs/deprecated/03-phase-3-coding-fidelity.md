PHASE 3 CONFIRMED. Run Phase 3: Coding Fidelity (coding-fidelity-playbook.md).

**Launch Gaps G1, G2, G3, G7, G10, G12 (all Phase 3):**

- **G1 (CI lint):** Run `ruff check src/observeco/` and report error count. Must be 0. If >0, severity-breakdown the errors (F401=unused-import, E501=line-length, F841=unused-variable, etc.)
- **G10 (test count):** Run `python -m pytest tests/ --tb=short -q 2>&1 | tail -5`. Report test count and pass/fail. Target: ≥50 passing.
- **G3 (clean-room install):** Build wheel with `python -m build --wheel`, install in a temp venv, run `observeco --version`. Verify it returns a semver string.
- **G12 (CI clean-room test):** Check if CI workflow has a clean-room install job. Search `.github/workflows/install-test.yml` for `pip install dist/*.whl` and assess if it tests from wheel not editable install.
- **G7 (.env.example):** Does `.env.example` exist documenting required env vars? If not, create it.
- **G2 (first-run F8):** Run the first-run audit (`specs/scripts/first-run-audit.py` or equivalent). Does F8 pass? Check landing page for "actionable" keyword and "what-for" guidance.

Execute the Spec-to-Code map, Error Handling audit (Gate 3 — forced error states), Regression audit. Include all gap findings.
