"""Self-check for benchmark engine — no frameworks, no fixtures."""
import json
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from observeco.benchmark.engine import BenchmarkEngine, BenchmarkTask

engine = BenchmarkEngine()

# ── Legacy scorer tests ────────────────────────────────────────────────────

def test_keyword_exact_match():
    """All expected terms present."""
    task = BenchmarkTask(expected_output="hello world")
    hr = {"output": "hello world"}
    r = engine._legacy_score(task, hr)
    assert r["score"] == 1.0, f"Expected 1.0, got {r['score']}"

def test_keyword_partial_match():
    """Some terms present."""
    task = BenchmarkTask(expected_output="def is_palindrome return True False")
    hr = {"output": "def is_palindrome(s): return s == s[::-1]"}
    r = engine._legacy_score(task, hr)
    assert r["score"] == 0.6, f"Expected 0.6, got {r['score']}"

def test_keyword_no_match():
    """No terms present."""
    task = BenchmarkTask(expected_output="hello world")
    hr = {"output": "goodbye universe"}
    r = engine._legacy_score(task, hr)
    assert r["score"] == 0.0, f"Expected 0.0, got {r['score']}"

def test_keyword_punctuation():
    """Punctuation stripped from tokens."""
    task = BenchmarkTask(expected_output="hello")
    hr = {"output": "Hello."}
    r = engine._legacy_score(task, hr)
    assert r["score"] == 1.0, f"Expected 1.0, got {r['score']}"

def test_keyword_decimal():
    """Decimal numbers kept intact. 'cents' matches in both."""
    task = BenchmarkTask(expected_output="0.05 five cents")
    hr = {"output": "Ball = $0.05. That's 5 cents."}
    r = engine._legacy_score(task, hr)
    # Overlap: {0.05, cents} / {0.05, five, cents} = 2/3 ≈ 0.667
    assert abs(r["score"] - 0.667) < 0.01, f"Expected ~0.667, got {r['score']}"

def test_keyword_json():
    """JSON tokens extracted correctly."""
    task = BenchmarkTask(expected_output="name year")
    hr = {"output": '[{"name":"Python","year":1991}]'}
    r = engine._legacy_score(task, hr)
    assert r["score"] == 1.0, f"Expected 1.0, got {r['score']}"

def test_keyword_empty_expected():
    """No expected output returns 0."""
    task = BenchmarkTask(expected_output="")
    hr = {"output": "some output"}
    r = engine._legacy_score(task, hr)
    assert r["score"] == 0.0

def test_keyword_empty_actual():
    """Empty actual output returns 0."""
    task = BenchmarkTask(expected_output="hello world")
    hr = {"output": ""}
    r = engine._legacy_score(task, hr)
    assert r["score"] == 0.0

# ── lm-eval flow tests ─────────────────────────────────────────────────────

def test_suite_unknown():
    """Unknown suite returns error."""
    r = engine.run_lm_eval(agent_name="test", suite="nonexistent")
    assert r["ok"] is False
    assert "Unknown suite" in r["error"]

def test_no_tasks():
    """No tasks or suite returns error."""
    r = engine.run_lm_eval(agent_name="test")
    assert r["ok"] is False
    assert "No tasks" in r["error"]

def test_compare_no_results():
    """Baseline comparison with no stored results."""
    r = engine.compare_baseline(agent_name="nonexistent_agent")
    assert r["ok"] is True
    assert r["total_tasks"] == 0

# ── Run ──────────────────────────────────────────────────────────────────
# The test_* functions above are collected and run directly by pytest.
# (Previously this module ran them itself in a loop and called sys.exit(),
# which crashed pytest with INTERNALERROR during collection. Removed.)
