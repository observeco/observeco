"""Tests for _compute_confidence() — confidence scoring + FP/FN risk + recommendations."""
import time
import pytest

# We'll test through the function directly by importing server
from observeco.dashboard.server import _compute_confidence

NOW = int(time.time())
HOUR = 3600
DAY = 86400


def _pulse(status, age_seconds=0):
    return {"timestamp": NOW - age_seconds, "status": status}

def _error(severity="error", message="no matching process", age_seconds=0):
    return {"timestamp": NOW - age_seconds, "severity": severity, "error_message": message, "error_type": "probe_failed"}


class TestComputeConfidence:
    """Covers all spec scenarios from §3.29."""

    def test_dead_agent_long_duration(self):
        """High confidence: dead for 4+ days, 3+ consecutive checks, all sources agree."""
        pulses = [_pulse("dead", age_seconds=i*1800) for i in range(48)]  # 24h of dead pulses
        errors = [_error(age_seconds=i*3600) for i in range(6)]  # 6 errors over 6h
        circuit = {"tripped": False, "failure_count": 0}
        result = _compute_confidence("dead", pulses, errors, circuit, NOW - 4*DAY, NOW)
        assert result["level"] == "high", f"Expected high, got {result['level']}"
        assert result["fp_risk"] == "low"
        assert result["fn_risk"] == "low"
        assert "down" in result["recommendation"].lower() or "dead" in result["recommendation"].lower()

    def test_single_missed_pulse(self):
        """Low confidence: agent alive then one missed pulse."""
        pulses = [_pulse("alive", age_seconds=i*60) for i in range(1, 10)]
        pulses.insert(0, _pulse("dead", age_seconds=0))  # one dead
        errors = []
        circuit = {"tripped": False, "failure_count": 0}
        result = _compute_confidence("dead", pulses, errors, circuit, NOW - 60, NOW)
        assert result["level"] == "low", f"Expected low, got {result['level']}"
        assert result["fp_risk"] == "high"

    def test_stale_running_high_fn(self):
        """Medium confidence: alive but last check >1h ago — high FN risk."""
        pulses = [_pulse("alive")]  # only one, old
        errors = []
        circuit = {"tripped": False, "failure_count": 0}
        result = _compute_confidence("alive", pulses, errors, circuit, NOW - 2*HOUR, NOW)
        assert result["level"] in ("medium", "high"), f"Expected medium/high, got {result['level']}"
        assert result["fn_risk"] == "high", f"Expected high FN risk, got {result['fn_risk']}"

    def test_perfect_health(self):
        """High confidence: 14 consecutive alive checks, no errors."""
        pulses = [_pulse("alive", age_seconds=i*30) for i in range(14)]
        errors = []
        circuit = {"tripped": False, "failure_count": 0}
        result = _compute_confidence("alive", pulses, errors, circuit, NOW - 60, NOW)
        assert result["level"] == "high", f"Expected high, got {result['level']}"
        assert result["fp_risk"] == "low"
        assert result["fn_risk"] == "low"

    def test_guard_tripped(self):
        """High confidence: guard tripped with 3+ consecutive failures."""
        pulses = [_pulse("error", age_seconds=i*30) for i in range(5)]
        errors = [_error(age_seconds=i*30) for i in range(3)]
        circuit = {"tripped": True, "failure_count": 3, "cooldown_until": NOW + 4*HOUR}
        result = _compute_confidence("error", pulses, errors, circuit, NOW - 300, NOW)
        assert result["level"] == "high", f"Expected high, got {result['level']}"

    def test_single_error_low_fp(self):
        """Low confidence: one error, agent alive — high FP risk."""
        pulses = [_pulse("alive", age_seconds=30)]
        errors = [_error(age_seconds=10)]
        circuit = {"tripped": False, "failure_count": 0}
        result = _compute_confidence("alive", pulses, errors, circuit, NOW - 60, NOW)
        # Only 1 source (error), duration < 2h, single check
        assert result["level"] == "low", f"Expected low, got {result['level']}"
        assert result["fp_risk"] == "high", f"Expected high FP risk, got {result['fp_risk']}"

    def test_new_agent_few_checks(self):
        """Medium confidence: only 2 checks, but all sources agree."""
        pulses = [_pulse("alive", age_seconds=i*60) for i in range(2)]
        errors = []
        circuit = {"tripped": False, "failure_count": 0}
        result = _compute_confidence("alive", pulses, errors, circuit, NOW - 120, NOW)
        assert result["level"] in ("low", "medium"), f"Expected low/medium, got {result['level']}"
        assert result["fn_risk"] == "high", f"Expected high FN risk, got {result['fn_risk']}"