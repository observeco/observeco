"""Stale data detection per-metric for ObserveCo dashboard.

Provides helpers to detect and display staleness on every chart/table cell.
Spec: obs-spec-023-service-architecture.md §17.3

ponytail: Server-side timestamps are simpler than WebSocket push.
If real-time staleness is needed, switch to SSE or WebSocket for push updates.

Self-check: python -m pytest tests/test_staleness.py -v
"""

from __future__ import annotations

import time
from typing import Any

# Thresholds per metric type (seconds)
THRESHOLDS: dict[str, int] = {
    "pulse": 60,
    "tokens": 300,       # 5 min
    "drift": 3600,       # 1 h
    "error_log": 300,    # 5 min
    "heal_log": 300,     # 5 min
    "alert_log": 300,    # 5 min
}

DEFAULT_THRESHOLD = 300  # 5 min


def get_threshold(metric_type: str) -> int:
    return THRESHOLDS.get(metric_type, DEFAULT_THRESHOLD)


def render_staleness(timestamp: float, metric_type: str = "pulse") -> dict[str, Any]:
    """Return staleness info for a given timestamp.

    Returns dict with:
      - label: human-readable staleness string
      - color_class: 'green' | 'yellow' | 'red'
      - is_stale: bool
      - seconds_ago: int
    """
    now = time.time()
    seconds_ago = int(now - timestamp)
    threshold = get_threshold(metric_type)

    if seconds_ago < 0:
        # Clock skew — clamp to 0
        seconds_ago = 0

    if seconds_ago < 60:
        label = f"updated {seconds_ago}s ago"
        color_class = "green"
        is_stale = False
    elif seconds_ago < threshold:
        label = f"updated {_fmt_minutes(seconds_ago)} ago"
        color_class = "yellow"
        is_stale = False
    else:
        label = f"stale — last update {_fmt_minutes(seconds_ago)} ago"
        color_class = "red"
        is_stale = True

    return {
        "label": label,
        "color_class": color_class,
        "is_stale": is_stale,
        "seconds_ago": seconds_ago,
    }


def add_last_updated(response: dict[str, Any]) -> dict[str, Any]:
    """Add last_updated timestamp to any API response dict."""
    response["last_updated"] = time.time()
    return response


def _fmt_minutes(seconds: int) -> str:
    mins = seconds // 60
    if mins < 60:
        return f"{mins}m"
    hours = mins // 60
    rem_mins = mins % 60
    if rem_mins == 0:
        return f"{hours}h"
    return f"{hours}h {rem_mins}m"


if __name__ == "__main__":
    # Self-check: verify thresholds and color classes
    now = time.time()
    for name, secs, expected in [
        ("fresh", 10, "green"),
        ("warn", 120, "yellow"),
        ("stale", 600, "red"),
        ("drift_ok", 1800, "yellow"),
        ("clock_skew", -3600, "green"),
    ]:
        result = render_staleness(now - secs, "pulse" if name != "drift_ok" else "drift")
        ok = "✓" if result["color_class"] == expected else "✗"
        print(f"  {ok} {name}: {result['label']} ({result['color_class']})")
    print("  Self-check complete.")
