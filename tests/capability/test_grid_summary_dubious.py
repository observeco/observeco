"""Tests for dubious-run detection in the grid summary.

Regression test (65decf5): measurement failures (provider_error, judge
failure, timeout, no-response) must NEVER be ranked as quality 0s, and the
summary must flag dubious runs before showing any ranking.
"""

import json

from observeco.dashboard.routes.capability import _generate_grid_summary


def _cell(model, acc, flags=None, hang=False):
    return {
        "task_name": "Arithmetic reasoning",
        "model": model,
        "config": "main",
        "accuracy": acc,
        "cost": 0.001,
        "flags": json.dumps(flags or []),  # DB stores flags as JSON string
        "hang": hang,
    }


def test_dubious_run_flags_provider_failures():
    cells = [
        _cell("deepseek/deepseek-v4-flash", 1.0),
        _cell("deepseek/deepseek-v4-pro", 0.0),          # real quality 0 (answered wrong)
        _cell("xiaomi/mimo-v2.5", 0.0, flags=["provider_error: trial=0"]),
        _cell("xiaomi/mimo-v2.5-pro", 0.0, flags=["provider_error: trial=0"]),
    ]
    html = _generate_grid_summary(cells, ["deepseek/deepseek-v4-flash", "deepseek/deepseek-v4-pro", "xiaomi/mimo-v2.5", "xiaomi/mimo-v2.5-pro"], ["main"])
    # Dubious banner present
    assert "Dubious run" in html
    assert "provider" in html
    # Xiaomi (>=50% failed) excluded from ranking
    assert "mimo-v2.5" not in html.split("Model ranking")[1]
    # Real quality 0 for deepseek-v4-pro still appears (it answered, just wrong)
    assert "deepseek-v4-pro" in html.split("Model ranking")[1]


def test_clean_run_no_dubious_banner():
    cells = [
        _cell("deepseek/deepseek-v4-flash", 0.9),
        _cell("deepseek/deepseek-v4-pro", 0.8),
        _cell("xiaomi/mimo-v2.5", 0.7),
        _cell("xiaomi/mimo-v2.5-pro", 0.6),
    ]
    html = _generate_grid_summary(cells, ["deepseek/deepseek-v4-flash", "deepseek/deepseek-v4-pro", "xiaomi/mimo-v2.5", "xiaomi/mimo-v2.5-pro"], ["main"])
    assert "Dubious run" not in html
    assert "Model ranking" in html


def test_judge_failure_flagged_dubious():
    cells = [
        _cell("deepseek/deepseek-v4-flash", 0.0, flags=["judge_failure"]),
        _cell("deepseek/deepseek-v4-pro", 0.5),
    ]
    html = _generate_grid_summary(cells, ["deepseek/deepseek-v4-flash", "deepseek/deepseek-v4-pro"], ["main"])
    assert "Dubious run" in html
    assert "judge" in html.lower()
    # The judge-failure cell is not ranked as a 0 — model excluded (>=50%)
    assert "deepseek-v4-flash" not in html.split("Model ranking")[1]
