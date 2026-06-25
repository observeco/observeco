"""Tests for staleness detection module.

Verifies render_staleness() thresholds, color classes, and edge cases.
Spec: obs-spec-023-service-architecture.md §17.3
"""

from __future__ import annotations

import time
from observeco.staleness import render_staleness, add_last_updated, get_threshold


def test_green_below_60s():
    """Metrics updated <60s ago should be green and not stale."""
    result = render_staleness(time.time() - 10, "pulse")
    assert result["color_class"] == "green"
    assert result["is_stale"] is False
    assert "updated" in result["label"]


def test_yellow_between_60s_and_threshold():
    """Metrics between 60s and threshold should be yellow and not stale."""
    result = render_staleness(time.time() - 90, "tokens")  # 1.5 min, threshold=300s
    assert result["color_class"] == "yellow"
    assert result["is_stale"] is False


def test_red_beyond_threshold():
    """Metrics beyond threshold should be red and stale."""
    result = render_staleness(time.time() - 300, "pulse")  # 5 min, threshold=60s
    assert result["color_class"] == "red"
    assert result["is_stale"] is True
    assert "stale" in result["label"]


def test_drift_has_longer_threshold():
    """Drift metric should have 1h threshold."""
    assert get_threshold("drift") == 3600


def test_drift_below_threshold_is_not_stale():
    """Drift at 30min should be yellow, not red."""
    result = render_staleness(time.time() - 1800, "drift")  # 30 min
    assert result["color_class"] == "yellow"
    assert result["is_stale"] is False


def test_clock_skew_clamped():
    """Future timestamps should clamp to 0s ago."""
    result = render_staleness(time.time() + 3600, "pulse")
    assert result["seconds_ago"] == 0
    assert result["color_class"] == "green"


def test_add_last_updated():
    """add_last_updated should add a timestamp to the response."""
    resp = {"data": [1, 2, 3]}
    result = add_last_updated(resp)
    assert "last_updated" in result
    assert isinstance(result["last_updated"], float)
    assert result["data"] == [1, 2, 3]


def test_unknown_metric_type_uses_default():
    """Unknown metric types should use default 5min threshold."""
    result = render_staleness(time.time() - 600, "unknown_type")  # 10 min
    assert result["color_class"] == "red"
    assert result["is_stale"] is True
