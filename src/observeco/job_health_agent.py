"""Job Health severity classification — maps signal types to P0/P1/P2/P3.

Loaded from `job_health_severity.json` so severities and SLAs can be tuned
without code changes.  Every signal type in the job-health taxonomy (§2.3
of obs-spec-018-addendum-job-health.md) has a mapping.

Usage:
    from observeco.job_health_agent import classify, Severity

    result = classify("empty_output")
    print(result.severity)   # "P1"
    print(result.alert_sla)  # 300
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

_CONFIG_PATH = Path(__file__).parent / "job_health_severity.json"


@dataclass(frozen=True)
class Severity:
    """Resolved severity level for a signal type."""

    level: str  # "P0" | "P1" | "P2" | "P3"
    label: str  # "critical" | "high" | "medium" | "low"
    alert_sla_seconds: Optional[int]  # None → log only (P3)
    description: str
    reason: str  # why this signal type got this severity


class _SeverityRegistry:
    """ponytail: single-global, lazy-loaded from JSON.  Upgrade path: watch
    the config file and reload on mtime change, or plug into observeco's
    config hot-reload if that mechanism is built later."""

    def __init__(self) -> None:
        self._mapping: dict[str, dict] = {}
        self._levels: dict[str, dict] = {}
        self._loaded = False

    def _load(self) -> None:
        if self._loaded:
            return
        with open(_CONFIG_PATH) as f:
            data = json.load(f)
        self._levels = data["severity_levels"]
        self._mapping = data["signal_mapping"]
        self._loaded = True

    def classify(self, signal_type: str) -> Severity:
        self._load()
        entry = self._mapping.get(signal_type)
        if entry is None:
            # Unknown signal types are treated as P2 — degraded, alertable
            # but not blocking.  This is a safe default that prevents silent
            # failures while a new detection type is being rolled out.
            return Severity(
                level="P2",
                label="medium",
                alert_sla_seconds=1800,
                description="Performance degraded — alert within 30 minutes",
                reason=f"Unknown signal type '{signal_type}' — classified as P2 by default.",
            )
        sev = entry["severity"]
        level_def = self._levels[sev]
        return Severity(
            level=sev,
            label=level_def["label"],
            alert_sla_seconds=level_def["alert_seconds"],
            description=level_def["description"],
            reason=entry["reason"],
        )

    def list_types(self) -> list[str]:
        self._load()
        return sorted(self._mapping.keys())

    def reload(self) -> None:
        """Force re-read of the config file."""
        self._loaded = False
        self._load()


_registry = _SeverityRegistry()

# ── public API ──────────────────────────────────────────────────────────


def classify(signal_type: str) -> Severity:
    """Return the severity classification for *signal_type*.

    Signal types are the 15 values from the job-health taxonomy:
    empty_output, stale_output, corrupt_output, error_in_output,
    volume_collapse, progressive_shrinkage, latency_degradation,
    output_duplication, concurrent_overlap, cascading_failure,
    temp_file_leak, zombie_process, config_drift, output_path_drift,
    schedule_anomaly.
    """
    return _registry.classify(signal_type)


def list_signal_types() -> list[str]:
    """Return every known signal type, sorted alphabetically."""
    return _registry.list_types()


# ── self-check (run directly) ───────────────────────────────────────────

if __name__ == "__main__":
    import sys

    ok = 0
    fail = 0

    types = list_signal_types()
    expected = 15
    if len(types) != expected:
        print(f"FAIL: expected {expected} signal types, got {len(types)}")
        fail += 1
    else:
        print(f"OK: {len(types)} signal types registered")
        ok += 1

    # Every known type must resolve to a valid severity
    for st in types:
        result = classify(st)
        if result.level not in ("P0", "P1", "P2", "P3"):
            print(f"FAIL: {st} → invalid severity {result.level}")
            fail += 1
        elif result.alert_sla_seconds is None and result.level != "P3":
            print(f"FAIL: {st} ({result.level}) should have an SLA, got None")
            fail += 1
        elif result.alert_sla_seconds is not None and result.level == "P3":
            print(f"FAIL: {st} (P3) should have null SLA, got {result.alert_sla_seconds}")
            fail += 1
        else:
            ok += 1

    # Verify specific severity assignments
    checks = [
        ("cascading_failure", "P0"),
        ("empty_output", "P1"),
        ("corrupt_output", "P1"),
        ("error_in_output", "P1"),
        ("volume_collapse", "P1"),
        ("concurrent_overlap", "P1"),
        ("output_path_drift", "P1"),
        ("stale_output", "P2"),
        ("progressive_shrinkage", "P2"),
        ("latency_degradation", "P2"),
        ("output_duplication", "P2"),
        ("zombie_process", "P2"),
        ("config_drift", "P2"),
        ("schedule_anomaly", "P2"),
        ("temp_file_leak", "P3"),
    ]
    for st, expected_sev in checks:
        result = classify(st)
        if result.level != expected_sev:
            print(f"FAIL: {st} → {result.level} (expected {expected_sev})")
            fail += 1
        else:
            ok += 1

    # Unknown type falls back to P2
    unknown = classify("made_up_type_xyz")
    if unknown.level != "P2":
        print(f"FAIL: unknown type → {unknown.level} (expected P2)")
        fail += 1
    else:
        print("OK: unknown type → P2 (safe default)")
        ok += 1

    # SLA values are correct
    sla_checks = [
        ("P0", 0),
        ("P1", 300),
        ("P2", 1800),
        ("P3", None),
    ]
    for level, expected_sla in sla_checks:
        actual = _registry._levels[level]["alert_seconds"]
        if actual != expected_sla:
            print(f"FAIL: {level} SLA = {actual} (expected {expected_sla})")
            fail += 1
        else:
            ok += 1

    print(f"\n{ok} checks passed, {fail} failed")
    sys.exit(0 if fail == 0 else 1)
