"""Tests for the Lifecycle Enforcement Layer."""

import json
import time
from pathlib import Path
from observeco.lifecycle.enforcer import LifecycleEnforcer, LIFECYCLE_STATES


def _make_enforcer(tmp_path):
    """Create an enforcer with a temp state file."""
    state_file = tmp_path / "lifecycle.json"
    return LifecycleEnforcer(state_file=state_file)


# ── Feature lifecycle tests ────────────────────────────────────────

class TestFeatureLifecycle:
    def test_register_feature(self, tmp_path):
        enforcer = _make_enforcer(tmp_path)
        f = enforcer.register_feature("fleet-cards", spec="specs/fleet.md", owner="Pragma")
        assert f.name == "fleet-cards"
        assert f.state == "design"
        assert f.spec == "specs/fleet.md"
        assert f.owner == "Pragma"

    def test_register_idempotent(self, tmp_path):
        enforcer = _make_enforcer(tmp_path)
        enforcer.register_feature("fleet-cards")
        enforcer.register_feature("fleet-cards")  # second call
        assert len(enforcer.features) == 1

    def test_advance_one_step(self, tmp_path):
        enforcer = _make_enforcer(tmp_path)
        enforcer.register_feature("fleet-cards")
        result = enforcer.advance("fleet-cards", "spec", evidence={
            "spec_file": "specs/fleet.md",
            "scope": "agent cards only",
            "success_criteria": "Sean identifies dead agent in <5s",
        })
        assert result["ok"] is True
        assert enforcer.features["fleet-cards"].state == "spec"

    def test_advance_skip_state_blocked(self, tmp_path):
        enforcer = _make_enforcer(tmp_path)
        enforcer.register_feature("fleet-cards")
        result = enforcer.advance("fleet-cards", "build")  # skip spec
        assert result["ok"] is False
        assert "Cannot skip" in result["message"]

    def test_advance_backwards_blocked(self, tmp_path):
        enforcer = _make_enforcer(tmp_path)
        enforcer.register_feature("fleet-cards")
        enforcer.advance("fleet-cards", "spec", evidence={
            "spec_file": "x", "scope": "x", "success_criteria": "x",
        })
        result = enforcer.advance("fleet-cards", "design")  # backwards
        assert result["ok"] is False
        assert "Cannot go from" in result["message"]

    def test_full_lifecycle(self, tmp_path):
        enforcer = _make_enforcer(tmp_path)
        enforcer.register_feature("fleet-cards")

        # design → spec
        r1 = enforcer.advance("fleet-cards", "spec", evidence={
            "spec_file": "specs/fleet.md",
            "scope": "agent cards",
            "success_criteria": "identifiable in <5s",
        })
        assert r1["ok"]

        # spec → build
        r2 = enforcer.advance("fleet-cards", "build", evidence={
            "spec_file": "specs/fleet.md",
        })
        assert r2["ok"]

        # build → test
        r3 = enforcer.advance("fleet-cards", "test", evidence={
            "unit_tests_pass": True,
            "unit_tests": "19/19 pass",
            "api_verified": True,
            "api_result": "all endpoints 200",
            "ui_verified": True,
            "ui_result": "screenshot verified",
        })
        assert r3["ok"]

        # test → deploy
        r4 = enforcer.advance("fleet-cards", "deploy", evidence={
            "live_proof": True,
            "proof_detail": "curl /api/agents → 200",
            "sean_approved": True,
            "approved_by": "Sean",
            "rollback_command": "git revert HEAD",
        })
        assert r4["ok"]

        # deploy → maintain
        r5 = enforcer.advance("fleet-cards", "maintain", evidence={
            "health_baseline": "L1 ✅ L2 ✅ L3 ✅ L4 ✅",
        })
        assert r5["ok"]

        assert enforcer.features["fleet-cards"].state == "maintain"

    def test_gate_failure_blocks_advance(self, tmp_path):
        enforcer = _make_enforcer(tmp_path)
        enforcer.register_feature("fleet-cards")
        enforcer.advance("fleet-cards", "spec", evidence={
            "spec_file": "x", "scope": "x", "success_criteria": "x",
        })
        enforcer.advance("fleet-cards", "build")

        # Try to advance to test without providing test evidence
        result = enforcer.advance("fleet-cards", "test", evidence={})
        assert result["ok"] is False
        assert "Gates failed" in result["message"]

    def test_waiver_allows_gate_bypass(self, tmp_path):
        enforcer = _make_enforcer(tmp_path)
        enforcer.register_feature("fleet-cards")
        enforcer.advance("fleet-cards", "spec", evidence={
            "spec_file": "x", "scope": "x", "success_criteria": "x",
        })
        enforcer.advance("fleet-cards", "build")

        # Advance to test with waiver for missing gates
        result = enforcer.advance("fleet-cards", "test", evidence={
            "unit_tests_pass": True,
            "unit_tests": "19/19",
            "waiver_reason": "Sean override — ship now",
        })
        assert result["ok"] is True
        assert len(enforcer.features["fleet-cards"].waivers) == 1

    def test_persistence(self, tmp_path):
        state_file = tmp_path / "lifecycle.json"
        enforcer1 = LifecycleEnforcer(state_file=state_file)
        enforcer1.register_feature("fleet-cards")
        enforcer1.advance("fleet-cards", "spec", evidence={
            "spec_file": "x", "scope": "x", "success_criteria": "x",
        })

        # Load from disk
        enforcer2 = LifecycleEnforcer(state_file=state_file)
        assert "fleet-cards" in enforcer2.features
        assert enforcer2.features["fleet-cards"].state == "spec"


# ── Health trigger tests ───────────────────────────────────────────

class TestHealthTriggers:
    def test_dead_agent_flagged(self, tmp_path):
        enforcer = _make_enforcer(tmp_path)
        health = {
            "accelerator": {
                "status": "dead",
                "dead_since": time.time() - (10 * 86400),  # 10 days
            }
        }
        flags = enforcer.check_health_triggers(health)
        assert len(flags) == 1
        assert flags[0].agent == "accelerator"
        assert flags[0].trigger == "dead"
        assert flags[0].severity == "critical"

    def test_recently_dead_not_flagged(self, tmp_path):
        enforcer = _make_enforcer(tmp_path)
        health = {
            "accelerator": {
                "status": "dead",
                "dead_since": time.time() - (3 * 86400),  # 3 days
            }
        }
        flags = enforcer.check_health_triggers(health)
        assert len(flags) == 0

    def test_high_drift_flagged(self, tmp_path):
        enforcer = _make_enforcer(tmp_path)
        health = {
            "pragma": {
                "status": "alive",
                "drift_pct": 8.5,
            }
        }
        flags = enforcer.check_health_triggers(health)
        assert len(flags) == 1
        assert flags[0].trigger == "drift_high"

    def test_low_drift_not_flagged(self, tmp_path):
        enforcer = _make_enforcer(tmp_path)
        health = {
            "pragma": {
                "status": "alive",
                "drift_pct": 2.0,
            }
        }
        flags = enforcer.check_health_triggers(health)
        assert len(flags) == 0

    def test_high_error_rate_flagged(self, tmp_path):
        enforcer = _make_enforcer(tmp_path)
        health = {
            "pragma": {
                "status": "alive",
                "error_count": 25,
                "check_count": 100,
            }
        }
        flags = enforcer.check_health_triggers(health)
        assert len(flags) == 1
        assert flags[0].trigger == "error_rate"

    def test_deduplication(self, tmp_path):
        enforcer = _make_enforcer(tmp_path)
        health = {
            "pragma": {
                "status": "alive",
                "drift_pct": 8.0,
            }
        }
        flags1 = enforcer.check_health_triggers(health)
        assert len(flags1) == 1

        # Same health — should not re-flag
        flags2 = enforcer.check_health_triggers(health)
        assert len(flags2) == 0

    def test_resolve_flag(self, tmp_path):
        enforcer = _make_enforcer(tmp_path)
        health = {
            "pragma": {
                "status": "alive",
                "drift_pct": 8.0,
            }
        }
        enforcer.check_health_triggers(health)
        enforcer.resolve_flag("pragma", "drift_high")
        assert len(enforcer.active_flags()) == 0


# ── Scope collision tests ──────────────────────────────────────────

class TestScopeCollision:
    def test_shared_files_detected(self, tmp_path):
        enforcer = _make_enforcer(tmp_path)
        enforcer.register_feature("feature-a")
        enforcer.advance("feature-a", "spec", evidence={
            "spec_file": "x", "scope": "x", "success_criteria": "x",
        })
        enforcer.advance("feature-a", "build")

        enforcer.register_feature("feature-b")
        enforcer.advance("feature-b", "spec", evidence={
            "spec_file": "y", "scope": "y", "success_criteria": "y",
        })
        enforcer.advance("feature-b", "build")

        collisions = enforcer.check_scope_collision(
            "feature-c",
            files=["server.py", "index.html"],
            all_features_files={
                "feature-a": ["server.py", "db.py"],
                "feature-b": ["server.py", "push.py"],
            },
        )
        assert len(collisions) == 2
        assert "server.py" in collisions[0].shared_files

    def test_no_collision_different_files(self, tmp_path):
        enforcer = _make_enforcer(tmp_path)
        enforcer.register_feature("feature-a")
        enforcer.advance("feature-a", "spec", evidence={
            "spec_file": "x", "scope": "x", "success_criteria": "x",
        })
        enforcer.advance("feature-a", "build")

        collisions = enforcer.check_scope_collision(
            "feature-b",
            files=["unrelated.py"],
            all_features_files={
                "feature-a": ["server.py"],
            },
        )
        assert len(collisions) == 0

    def test_no_collision_maintain_state(self, tmp_path):
        """Features in 'maintain' state don't cause collisions."""
        enforcer = _make_enforcer(tmp_path)
        enforcer.register_feature("feature-a")
        # Advance to maintain
        for state in LIFECYCLE_STATES[1:]:
            enforcer.advance("feature-a", state, evidence={
                "spec_file": "x", "scope": "x", "success_criteria": "x",
                "unit_tests_pass": True, "unit_tests": "ok",
                "api_verified": True, "api_result": "ok",
                "ui_verified": True, "ui_result": "ok",
                "live_proof": True, "proof_detail": "ok",
                "sean_approved": True, "approved_by": "Sean",
                "rollback_command": "git revert HEAD",
                "health_baseline": "ok",
            })

        collisions = enforcer.check_scope_collision(
            "feature-b",
            files=["server.py"],
            all_features_files={"feature-a": ["server.py"]},
        )
        assert len(collisions) == 0


# ── Maintenance ledger tests ───────────────────────────────────────

class TestMaintenanceLedger:
    def test_ledger_output(self, tmp_path):
        enforcer = _make_enforcer(tmp_path)
        enforcer.register_feature("fleet-cards", owner="Pragma")
        ledger = enforcer.maintenance_ledger()
        assert "fleet-cards" in ledger
        assert "design" in ledger
        assert "Pragma" in ledger

    def test_ledger_with_flags(self, tmp_path):
        enforcer = _make_enforcer(tmp_path)
        enforcer.register_feature("fleet-cards")
        enforcer.check_health_triggers({
            "pragma": {"status": "alive", "drift_pct": 8.0},
        })
        ledger = enforcer.maintenance_ledger()
        assert "ACTIVE HEALTH FLAGS" in ledger
        assert "pragma" in ledger
