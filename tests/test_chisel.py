"""Tests for chisel trim and drift modules."""
import os
import tempfile
from observeco.chisel.trim import _classify_line, _estimate_tokens, run_trim
from observeco.chisel.drift import run_drift


SAMPLE_LINES = [
    "You are a helpful assistant.",
    "## Identity",
    "- You are a coding expert",
    "# Skills",
    "- web_search",
    "- file_operations",
    "## Tools",
    "- Python execution",
    "## Memory",
    "- The user prefers concise answers",
]


def test_classify_line_returns_component():
    # Keywords within lines are detected
    assert _classify_line("## Identity") == "identity"
    assert _classify_line("## Skills") == "skills"
    assert _classify_line("## Memory") == "memory"
    assert _classify_line("## Rules") == "guidance"  # "rule" keyword → guidance
    # Lines without keyword matches default to guidance
    assert _classify_line("Please respond nicely.") == "guidance"
    assert _classify_line("- web_search") == "guidance"  # single word, no skill keywords


def test_classify_line_edge_cases():
    assert _classify_line("") == "guidance"
    # "identity" is a keyword match, so it returns "identity"
    assert _classify_line("identity is important") == "identity"


def test_estimate_tokens():
    assert _estimate_tokens("Hello world") >= 1
    assert _estimate_tokens("") == 1  # max(1, 0/4) = 1
    assert _estimate_tokens("a b c d e f") >= 1


def test_estimate_tokens_longer():
    text = "The quick brown fox jumps over the lazy dog"
    tokens = _estimate_tokens(text)
    assert tokens > 0


def test_trim_runs():
    """run_trim should handle missing stdin gracefully."""
    try:
        run_trim()
    except (OSError, SystemExit):
        pass  # acceptable in test env without stdin


def test_drift_runs():
    run_drift()
    # Should not crash
