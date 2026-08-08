# ObserveCo verification gate.
#
#   make verify        — run the referential-integrity audit AND the full test suite
#   make verify-audit  — referential-integrity audit only
#   make verify-tests  — full test suite only
#
# Every target fails (nonzero exit) if its command fails. `verify` chains the
# audit first so a failure there stops the gate before tests run.

.PHONY: verify verify-audit verify-tests

verify: verify-audit verify-tests
	@echo "=== VERIFY PASS ==="

verify-audit:
	@echo "=== Referential-integrity audit ==="
	uv run python scripts/audit_referential_integrity.py --allowlist scripts/audit-allowlist.json

verify-tests:
	@echo "=== Full test suite ==="
	uv run pytest tests/ -q
