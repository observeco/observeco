"""Tests for the generic empty-response retry in HermesBenchmarkAdapter.

Regression test (06df7c3): a provider that returns empty content with exit 0
(reasoning models that exhaust their output budget) must be retried like a
5xx/429 — never scored as a legitimate 0. This must apply to ALL models,
not a hardcoded per-provider special case.
"""

import subprocess
from unittest.mock import patch

from observeco.benchmark.adapters.hermes import HermesBenchmarkAdapter


class _FakeProc:
    returncode = 0
    stdout = "   \n\n  "  # whitespace-only → empty after cleaning
    stderr = ""

    def communicate(self, timeout=None):
        return (self.stdout, self.stderr)


def _task(model="any/model"):
    class T:
        pass
    t = T()
    t.input_text = "test prompt"
    t.context_text = ""
    t.model = model
    t.temperature = 0.0
    return t


def test_empty_output_retries_and_marks_provider_error():
    adapter = HermesBenchmarkAdapter(model="any/model", timeout=30)
    calls = {"n": 0}

    def fake_popen(*args, **kwargs):
        calls["n"] += 1
        return _FakeProc()

    with patch("subprocess.Popen", side_effect=fake_popen):
        result = adapter.run_task("default", _task())

    # Retried _MAX_RETRIES+1 times, then flagged provider_error — never a 0
    from observeco.benchmark.adapters.hermes import _MAX_RETRIES
    assert calls["n"] == _MAX_RETRIES + 1
    assert result["provider_error"] is True
    assert result["tokens"] == 0


def test_empty_output_retry_loop_exhausts_attempts():
    """After exhausting retries, the result is provider_error (excluded),
    so the grid never records a fake 0 for an empty completion."""
    adapter = HermesBenchmarkAdapter(model="any/model", timeout=30)

    with patch("subprocess.Popen", return_value=_FakeProc()):
        result = adapter.run_task("default", _task())

    assert result.get("provider_error") is True
    assert result.get("output", "") == ""
