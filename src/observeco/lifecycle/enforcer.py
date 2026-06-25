"""Lifecycle Enforcement Layer for ObserveCo.

Tracks features through design → spec → build → test → deploy → maintain.
Connects fleet dashboard health data to automatic flag creation.
Provides scope collision detection before builds start.

Usage:
    from observeco.lifecycle.enforcer import LifecycleEnforcer

    enforcer = LifecycleEnforcer()
    enforcer.register_feature("fleet-agent-cards", spec="specs/fleet-cards.md")
    enforcer.advance("fleet-agent-cards", "build", evidence={"branch": "feat/fleet-cards", "tests": "19/19 pass"})
    enforcer.check_health_triggers()  # auto-flags degraded agents
    enforcer.check_scope_collision("feat/new-feature", files=["src/observeco/dashboard/server.py"])
"""

import json
import time
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional

from observeco.constants import DRIFT_WARN_PCT, DRIFT_CRITICAL_PCT


# ── Constants ──────────────────────────────────────────────────────

LIFECYCLE_STATES = ["design", "spec", "build", "test", "deploy", "maintain"]

STATE_FILE = Path.home() / ".observeco" / "lifecycle.json"

HEALTH_THRESHOLDS = {
    "dead_days": 7,         # Auto-flag if agent dead > 7 days
    "drift_high_count": 5,  # Auto-flag if drift high for 5+ consecutive checks
    "error_rate_pct": 20,   # Auto-flag if error rate > 20% of checks
}


# ── Data classes ───────────────────────────────────────────────────

@dataclass
class FeatureState:
    name: str
    state: str = "design"
    spec: str = ""
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    evidence: dict = field(default_factory=dict)
    gates_passed: list = field(default_factory=list)
    gates_failed: list = field(default_factory=list)
    waivers: list = field(default_factory=list)
    deployed_version: str = ""
    last_verified: float = 0.0
    owner: str = ""


@dataclass
class HealthFlag:
    agent: str
    trigger: str          # "dead", "drift_high", "error_rate"
    severity: str         # "warning", "critical"
    detected_at: float = field(default_factory=time.time)
    details: str = ""
    resolved: bool = False
    resolved_at: float = 0.0


@dataclass
class ScopeCollision:
    feature_a: str
    feature_b: str
    shared_files: list = field(default_factory=list)
    severity: str = "warning"
    detected_at: float = field(default_factory=time.time)


# ── Enforcer ───────────────────────────────────────────────────────

class LifecycleEnforcer:
    """Enforces lifecycle gates for ObserveCo features."""

    def __init__(self, state_file: Optional[Path] = None):
        self.state_file = state_file or STATE_FILE
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self._load()

    def _load(self):
        """Load state from disk."""
        if self.state_file.exists():
            data = json.loads(self.state_file.read_text())
            self.features = {
                k: FeatureState(**v) for k, v in data.get("features", {}).items()
            }
            self.health_flags = [
                HealthFlag(**f) for f in data.get("health_flags", [])
            ]
            self.scope_collisions = [
                ScopeCollision(**c) for c in data.get("scope_collisions", [])
            ]
        else:
            self.features = {}
            self.health_flags = []
            self.scope_collisions = []

    def _save(self):
        """Persist state to disk."""
        data = {
            "features": {k: asdict(v) for k, v in self.features.items()},
            "health_flags": [asdict(f) for f in self.health_flags],
            "scope_collisions": [asdict(c) for c in self.scope_collisions],
            "last_updated": time.time(),
        }
        self.state_file.write_text(json.dumps(data, indent=2))

    # ── Feature lifecycle ──────────────────────────────────────────

    def register_feature(self, name: str, spec: str = "", owner: str = "") -> FeatureState:
        """Register a new feature in the lifecycle."""
        if name in self.features:
            return self.features[name]
        feature = FeatureState(name=name, spec=spec, owner=owner)
        self.features[name] = feature
        self._save()
        return feature

    def advance(self, name: str, target_state: str, evidence: dict | None = None) -> dict:
        """Advance a feature to the next lifecycle state.

        Returns: {"ok": bool, "message": str, "gates": list}
        """
        if name not in self.features:
            return {"ok": False, "message": f"Feature '{name}' not registered", "gates": []}

        if target_state not in LIFECYCLE_STATES:
            return {"ok": False, "message": f"Invalid state: {target_state}", "gates": []}

        feature = self.features[name]
        current_idx = LIFECYCLE_STATES.index(feature.state)
        target_idx = LIFECYCLE_STATES.index(target_state)

        # Can only advance forward, one step at a time
        if target_idx <= current_idx:
            return {"ok": False, "message": f"Cannot go from {feature.state} to {target_state} (must advance forward)", "gates": []}

        if target_idx - current_idx > 1:
            return {"ok": False, "message": f"Cannot skip states: {feature.state} → {target_state}", "gates": []}

        # Run gate checks for the target state
        gates = self._run_gates_for_state(name, target_state, evidence or {})
        failed = [g for g in gates if not g["passed"]]

        if failed:
            # Check if waiver is provided in evidence
            waiver_reason = (evidence or {}).get("waiver_reason")
            if not waiver_reason:
                # Gates failed, no waiver — block advancement
                feature.gates_failed = failed
                self._save()
                return {
                    "ok": False,
                    "message": f"Gates failed for {target_state}: {[g['name'] for g in failed]}",
                    "gates": gates,
                }

        # Advance
        feature.state = target_state
        feature.updated_at = time.time()
        feature.evidence.update(evidence or {})
        feature.gates_passed.extend([g for g in gates if g["passed"]])
        if failed:
            feature.waivers.append({
                "state": target_state,
                "waived_gates": [g["name"] for g in failed],
                "waived_at": time.time(),
                "reason": (evidence or {}).get("waiver_reason", "Sean override"),
            })
        self._save()
        return {"ok": True, "message": f"Advanced to {target_state}", "gates": gates}

    def _run_gates_for_state(self, feature_name: str, state: str, evidence: dict | None = None) -> list:
        """Run gate checks for a specific lifecycle state."""
        gates = []
        if evidence is None:
            evidence = {}

        if state == "spec":
            gates.append({
                "name": "spec_complete",
                "passed": bool(evidence.get("spec_file")),
                "detail": f"Spec file: {evidence.get('spec_file', 'NOT PROVIDED')}",
            })
            gates.append({
                "name": "scope_bounded",
                "passed": bool(evidence.get("scope")),
                "detail": f"Scope: {evidence.get('scope', 'NOT BOUNDED')}",
            })
            gates.append({
                "name": "success_defined",
                "passed": bool(evidence.get("success_criteria")),
                "detail": f"Success: {evidence.get('success_criteria', 'NOT DEFINED')}",
            })

        elif state == "build":
            gates.append({
                "name": "spec_approved",
                "passed": self.features[feature_name].state == "spec",
                "detail": "Feature must be in 'spec' state before build",
            })
            gates.append({
                "name": "scope_no_carryover",
                "passed": not evidence.get("scope_carryover", False),
                "detail": "Build must not exceed spec scope",
            })

        elif state == "test":
            gates.append({
                "name": "l1_unit_tests",
                "passed": bool(evidence.get("unit_tests_pass")),
                "detail": f"Unit tests: {evidence.get('unit_tests', 'NOT RUN')}",
            })
            gates.append({
                "name": "l2_api_verification",
                "passed": bool(evidence.get("api_verified")),
                "detail": f"API: {evidence.get('api_result', 'NOT VERIFIED')}",
            })
            gates.append({
                "name": "l3_ui_verification",
                "passed": bool(evidence.get("ui_verified")),
                "detail": f"UI: {evidence.get('ui_result', 'NOT VERIFIED')}",
            })

        elif state == "deploy":
            gates.append({
                "name": "l4_live_proof",
                "passed": bool(evidence.get("live_proof")),
                "detail": f"Live proof: {evidence.get('proof_detail', 'NOT PROVIDED')}",
            })
            gates.append({
                "name": "sean_approval",
                "passed": bool(evidence.get("sean_approved")),
                "detail": f"Approved by: {evidence.get('approved_by', 'NOT APPROVED')}",
            })
            gates.append({
                "name": "rollback_plan",
                "passed": bool(evidence.get("rollback_command")),
                "detail": f"Rollback: {evidence.get('rollback_command', 'NOT PROVIDED')}",
            })

        elif state == "maintain":
            gates.append({
                "name": "deploy_verified",
                "passed": self.features[feature_name].state == "deploy",
                "detail": "Feature must be deployed before maintenance",
            })
            gates.append({
                "name": "health_baseline",
                "passed": bool(evidence.get("health_baseline")),
                "detail": f"Baseline: {evidence.get('health_baseline', 'NOT SET')}",
            })

        return gates

    def get_feature(self, name: str) -> Optional[dict]:
        """Get feature state as dict."""
        if name not in self.features:
            return None
        return asdict(self.features[name])

    def list_features(self, state: str | None = None) -> list:
        """List all features, optionally filtered by state."""
        features = list(self.features.values())
        if state:
            features = [f for f in features if f.state == state]
        return [asdict(f) for f in features]

    # ── Health-triggered auto-flags ────────────────────────────────

    def check_health_triggers(self, agent_health: dict | None = None) -> list:
        """Check fleet health data and auto-create flags.

        Args:
            agent_health: dict of {agent_name: {"status": str, "dead_since": float, "drift_pct": float, "error_count": int, "check_count": int}}

        Returns: list of new HealthFlag objects created
        """
        if not agent_health:
            return []

        new_flags = []
        now = time.time()

        for agent, health in agent_health.items():
            status = health.get("status", "unknown")

            # Dead agent check
            if status == "dead":
                dead_since = health.get("dead_since", 0)
                dead_days = (now - dead_since) / 86400 if dead_since else 0
                if dead_days >= HEALTH_THRESHOLDS["dead_days"]:
                    flag = HealthFlag(
                        agent=agent,
                        trigger="dead",
                        severity="critical",
                        details=f"Agent dead for {dead_days:.0f} days (threshold: {HEALTH_THRESHOLDS['dead_days']})",
                    )
                    new_flags.append(flag)

            # Drift check
            drift_pct = health.get("drift_pct", 0)
            if abs(drift_pct) > DRIFT_WARN_PCT:  # early warning threshold
                flag = HealthFlag(
                    agent=agent,
                    trigger="drift_high",
                    severity="warning" if abs(drift_pct) < DRIFT_CRITICAL_PCT else "critical",
                    details=f"Drift at {drift_pct:+.1f}% (threshold: ±{DRIFT_WARN_PCT}%)",
                )
                new_flags.append(flag)

            # Error rate check
            error_count = health.get("error_count", 0)
            check_count = health.get("check_count", 1)
            error_rate = (error_count / check_count * 100) if check_count > 0 else 0
            if error_rate >= HEALTH_THRESHOLDS["error_rate_pct"]:
                flag = HealthFlag(
                    agent=agent,
                    trigger="error_rate",
                    severity="warning" if error_rate < 50 else "critical",
                    details=f"Error rate {error_rate:.0f}% ({error_count}/{check_count} checks, threshold: {HEALTH_THRESHOLDS['error_rate_pct']}%)",
                )
                new_flags.append(flag)

        # Deduplicate — don't re-flag same agent+trigger if already active
        active_flags = {(f.agent, f.trigger) for f in self.health_flags if not f.resolved}
        truly_new = [f for f in new_flags if (f.agent, f.trigger) not in active_flags]

        self.health_flags.extend(truly_new)
        self._save()
        return truly_new

    def resolve_flag(self, agent: str, trigger: str):
        """Mark a health flag as resolved."""
        for flag in self.health_flags:
            if flag.agent == agent and flag.trigger == trigger and not flag.resolved:
                flag.resolved = True
                flag.resolved_at = time.time()
        self._save()

    def active_flags(self) -> list:
        """Get all unresolved health flags."""
        return [asdict(f) for f in self.health_flags if not f.resolved]

    # ── Scope collision detection ──────────────────────────────────

    def check_scope_collision(self, feature_name: str, files: list, all_features_files: dict | None = None) -> list:
        """Check if proposed files overlap with other active features.

        Args:
            feature_name: Name of the feature being planned
            files: List of files this feature will touch
            all_features_files: dict of {other_feature_name: [files_it_touches]}

        Returns: list of ScopeCollision objects
        """
        if not all_features_files:
            return []

        collisions = []
        for other_name, other_files in all_features_files.items():
            if other_name == feature_name:
                continue
            # Check if the other feature is in an active state (not maintain)
            other = self.features.get(other_name)
            if other and other.state in ("build", "test"):
                shared = set(files) & set(other_files)
                if shared:
                    collision = ScopeCollision(
                        feature_a=feature_name,
                        feature_b=other_name,
                        shared_files=list(shared),
                        severity="critical" if len(shared) > 3 else "warning",
                    )
                    collisions.append(collision)

        self.scope_collisions.extend(collisions)
        self._save()
        return collisions

    # ── Maintenance ledger ─────────────────────────────────────────

    def maintenance_ledger(self) -> str:
        """Generate a compact maintenance ledger for all features."""
        lines = ["MAINTENANCE LEDGER", "=" * 50, ""]

        for name, feature in sorted(self.features.items()):
            state_icon = {
                "design": "🎨", "spec": "📝", "build": "🔨",
                "test": "🧪", "deploy": "🚀", "maintain": "🔧",
            }.get(feature.state, "❓")

            last_verified = "never"
            if feature.last_verified:
                days_ago = (time.time() - feature.last_verified) / 86400
                last_verified = f"{days_ago:.0f}d ago"

            lines.append(f"{state_icon} {name}")
            lines.append(f"   State: {feature.state}")
            lines.append(f"   Owner: {feature.owner or 'unassigned'}")
            lines.append(f"   Last verified: {last_verified}")
            if feature.waivers:
                lines.append(f"   ⚠️ Waivers: {len(feature.waivers)} (gates bypassed)")
            lines.append("")

        # Active health flags
        active = self.active_flags()
        if active:
            lines.append("ACTIVE HEALTH FLAGS")
            lines.append("-" * 50)
            for flag in active:
                icon = "🔴" if flag["severity"] == "critical" else "🟡"
                lines.append(f"   {icon} {flag['agent']}: {flag['trigger']} — {flag['details']}")
            lines.append("")

        # Scope collisions
        unresolved = [c for c in self.scope_collisions if c.severity]
        if unresolved:
            lines.append("SCOPE COLLISIONS")
            lines.append("-" * 50)
            for c in unresolved:
                lines.append(f"   ⚡ {c.feature_a} ↔ {c.feature_b}: {len(c.shared_files)} shared files")
            lines.append("")

        return "\n".join(lines)


# ── CLI entry point ────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    enforcer = LifecycleEnforcer()

    if len(sys.argv) < 2:
        print(enforcer.maintenance_ledger())
        sys.exit(0)

    cmd = sys.argv[1]

    if cmd == "list":
        state_filter = sys.argv[2] if len(sys.argv) > 2 else None
        features = enforcer.list_features(state_filter)
        for f in features:
            print(f"  {f['name']}: {f['state']} (owner: {f['owner']})")

    elif cmd == "register":
        name = sys.argv[2] if len(sys.argv) > 2 else input("Feature name: ")
        spec = sys.argv[3] if len(sys.argv) > 3 else ""
        enforcer.register_feature(name, spec=spec)
        print(f"Registered: {name}")

    elif cmd == "flags":
        flags = enforcer.active_flags()
        if flags:
            for f in flags:
                icon = "🔴" if f["severity"] == "critical" else "🟡"
                print(f"  {icon} {f['agent']}: {f['trigger']} — {f['details']}")
        else:
            print("  No active flags")

    elif cmd == "ledger":
        print(enforcer.maintenance_ledger())

    else:
        print(f"Unknown command: {cmd}")
        print("Usage: python -m observeco.lifecycle.enforcer [list|register|flags|ledger]")
