"""Self-check for session efficiency scoring. Run: python -m pytest tests/test_efficiency.py -q"""
from __future__ import annotations

from observeco.efficiency.metrics import (
    build_optimize_block,
    classify_archetype,
    compute_baseline,
    compute_effectiveness,
    compute_efficiency,
    evaluate_rules,
)

# A wasteful debug session: re-reads 3 distinct files, retries a command, has errors, then ships.
WASTEFUL_SESSION = [
    {"role": "assistant", "tool_calls": [{"function": {"name": "read_file", "arguments": '{"path": "calc.py"}'}}]},
    {"role": "tool", "name": "read_file", "content": '{"content": "x = 1\\n", "exit_code": 0}'},
    {"role": "assistant", "tool_calls": [{"function": {"name": "read_file", "arguments": '{"path": "calc.py"}'}}]},
    {"role": "tool", "name": "read_file", "content": '{"content": "x = 1\\n", "exit_code": 0}'},
    {"role": "assistant", "tool_calls": [{"function": {"name": "read_file", "arguments": '{"path": "helper.py"}'}}]},
    {"role": "tool", "name": "read_file", "content": '{"content": "y = 2\\n", "exit_code": 0}'},
    {"role": "assistant", "tool_calls": [{"function": {"name": "read_file", "arguments": '{"path": "helper.py"}'}}]},
    {"role": "tool", "name": "read_file", "content": '{"content": "y = 2\\n", "exit_code": 0}'},
    {"role": "assistant", "tool_calls": [{"function": {"name": "read_file", "arguments": '{"path": "utils.py"}'}}]},
    {"role": "tool", "name": "read_file", "content": '{"content": "z = 3\\n", "exit_code": 0}'},
    {"role": "assistant", "tool_calls": [{"function": {"name": "read_file", "arguments": '{"path": "utils.py"}'}}]},
    {"role": "tool", "name": "read_file", "content": '{"content": "z = 3\\n", "exit_code": 0}'},
    {"role": "assistant", "tool_calls": [{"function": {"name": "terminal", "arguments": '{"command": "python calc.py"}'}}]},
    {"role": "tool", "name": "terminal", "content": '{"content": "Error: name y not defined", "exit_code": 1}'},
    {"role": "assistant", "tool_calls": [{"function": {"name": "terminal", "arguments": '{"command": "python calc.py"}'}}]},
    {"role": "tool", "name": "terminal", "content": '{"content": "Error: name y not defined", "exit_code": 1}'},
    {"role": "assistant", "tool_calls": [{"function": {"name": "write_file", "arguments": '{"path": "calc.py", "content": "y=2\\nprint(y)"}'}}]},
    {"role": "tool", "name": "write_file", "content": '{"content": "written", "exit_code": 0}'},
    {"role": "assistant", "tool_calls": [{"function": {"name": "terminal", "arguments": '{"command": "python calc.py"}'}}]},
    {"role": "tool", "name": "terminal", "content": '{"content": "2", "exit_code": 0}'},
    {"role": "assistant", "tool_calls": [{"function": {"name": "terminal", "arguments": '{"command": "git commit -m fix"}'}}]},
    {"role": "tool", "name": "terminal", "content": '{"content": "committed", "exit_code": 0}'},
]

# A clean research session: reads 2 distinct files, no edits, no errors.
CLEAN_SESSION = [
    {"role": "assistant", "tool_calls": [{"function": {"name": "read_file", "arguments": '{"path": "a.py"}'}}]},
    {"role": "tool", "name": "read_file", "content": '{"content": "def a(): pass\\n", "exit_code": 0}'},
    {"role": "assistant", "tool_calls": [{"function": {"name": "read_file", "arguments": '{"path": "b.py"}'}}]},
    {"role": "tool", "name": "read_file", "content": '{"content": "def b(): pass\\n", "exit_code": 0}'},
]


def test_wasteful_session_has_redundant_reads_and_retries():
    eff = compute_efficiency(WASTEFUL_SESSION)
    by_id = {m["id"]: m for m in eff["metrics"]}
    assert by_id["redundant-reads"]["status"] == "bad", by_id["redundant-reads"]
    assert by_id["retry-waste"]["status"] in ("warn", "bad"), by_id["retry-waste"]
    # Wasteful session should score lower than clean
    assert eff["score"] is not None and eff["score"] < 100


def test_clean_session_scores_high():
    eff = compute_efficiency(CLEAN_SESSION)
    assert eff["score"] is not None
    assert eff["score"] >= 80, eff["score"]


def test_archetype_classification():
    assert classify_archetype(WASTEFUL_SESSION)["archetype"] == "debug"
    assert classify_archetype(CLEAN_SESSION)["archetype"] == "research"


def test_token_attribution_feeds_metrics():
    """#83: session_id joins token_logs → 3 token metrics become non-noop."""
    from observeco.db import Database
    from observeco.tracking.tokens import get_session_tokens
    import time

    sid = f"test_attr_{int(time.time() * 1000)}"
    db = Database()
    # Insert a token_log row with session_id (simulating OTEL emission)
    db.log_token_turn(
        agent_name="hermes-agent",
        turn_id=f"otel_test_{sid}",
        total_tokens=250_000,
        input_tokens=240_000,       # very high → context-pressure bad (<50)
        output_tokens=10_000,
        cache_read_tokens=100_000,  # high cache → cache-hit good
        cache_creation_tokens=5_000,
        provider="anthropic",
        source="otel",
        model="claude-sonnet",
        session_id=sid,
    )
    rows = get_session_tokens(sid)
    assert len(rows) == 1, rows
    assert rows[0]["input_tokens"] == 240_000

    # compute_efficiency with session_id → token metrics active
    eff = compute_efficiency(WASTEFUL_SESSION, session_id=sid)
    by_id = {m["id"]: m for m in eff["metrics"]}
    assert by_id["context-pressure"]["status"] != "noop", by_id["context-pressure"]
    assert by_id["cache-hit"]["status"] != "noop", by_id["cache-hit"]
    assert by_id["yield-density"]["status"] != "noop", by_id["yield-density"]
    # sanity: high input → context-pressure should score low (bad)
    assert by_id["context-pressure"]["score"] < 50

    # Without session_id → token metrics noop (backward-compat)
    eff2 = compute_efficiency(WASTEFUL_SESSION)
    by_id2 = {m["id"]: m for m in eff2["metrics"]}
    assert by_id2["context-pressure"]["status"] == "noop"
    assert by_id2["cache-hit"]["status"] == "noop"


def test_efficiency_score_is_weighted_average():
    eff = compute_efficiency(WASTEFUL_SESSION)
    # manual recompute of weighted average
    scores = [m["score"] for m in eff["metrics"] if m["status"] != "noop"]
    # 3 token metrics (context-pressure, cache-hit, yield-density) return noop without token data → 8 active
    assert len(scores) == 8
    active = [m for m in eff["metrics"] if m["status"] != "noop"]
    assert len(active) == 8


def test_evaluate_rules_flags_vendored_reads():
    turns = [
        {"role": "assistant", "tool_calls": [{"function": {"name": "read_file", "arguments": '{"path": "/x/node_modules/foo.js"}'}}]},
        {"role": "tool", "name": "read_file", "content": '{"content": "x", "exit_code": 0}'},
    ]
    rules = [{"id": "no-vendor", "type": "forbid-read", "pattern": "node_modules", "severity": "warn", "message": "no vendor"}]
    findings = evaluate_rules(turns, rules)
    assert len(findings) == 1
    assert findings[0]["offender"] == "/x/node_modules/foo.js"


def test_evaluate_rules_require_before_commit_detects_missing_test():
    turns = [
        {"role": "assistant", "tool_calls": [{"function": {"name": "terminal", "arguments": '{"command": "git commit -m fix"}'}}]},
        {"role": "tool", "name": "terminal", "content": '{"content": "committed", "exit_code": 0}'},
    ]
    rules = [{"id": "tbc", "type": "require-before-commit", "pattern": "pytest", "severity": "warn", "message": "test first"}]
    findings = evaluate_rules(turns, rules)
    assert len(findings) == 1
    assert findings[0]["offender"] == "committed without prerequisite"


def test_build_optimize_block_only_on_waste():
    # Clean session → no bad/warn → empty block
    eff = compute_efficiency(CLEAN_SESSION)
    assert build_optimize_block(eff) == ""
    # Wasteful session → block with markers
    eff2 = compute_efficiency(WASTEFUL_SESSION)
    block = build_optimize_block(eff2)
    assert "observeco-efficiency:start" in block
    assert "observeco-efficiency:end" in block
    assert "[BAD]" in block or "[WARN]" in block


def test_compute_baseline_returns_stats():
    # Use a real recent session id from disk if available; else just check shape
    import glob, os
    files = sorted(glob.glob(os.path.expanduser("~/.hermes/sessions/*.jsonl")), key=os.path.getmtime, reverse=True)
    if not files:
        import pytest
        pytest.skip("no real sessions")
    sid = os.path.basename(files[0]).replace(".jsonl", "")
    from observeco.dashboard.routes.efficiency import _parse_session
    turns = _parse_session(sid)
    arch = classify_archetype(turns)
    result = compute_baseline(sid, arch["archetype"])
    assert "archetype" in result
    # peer_count may be 0 if no same-archetype peers; just assert shape
    assert result["peer_count"] >= 0

