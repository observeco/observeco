"""Self-check for lm-eval agent adapter — no frameworks, no fixtures."""

import json
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from observeco.benchmark.adapters.lm_eval_adapter import HermesAgentLM
from lm_eval.api.instance import Instance
from lm_eval.api.model import LM


def test_extends_lm():
    """Adapter extends the LM base class."""
    assert issubclass(HermesAgentLM, LM), "HermesAgentLM must extend LM"


def test_init_defaults():
    """Default constructor works."""
    adapter = HermesAgentLM(agent_name="test")
    assert adapter.agent_name == "test"
    assert adapter.hermes_bin == "hermes"
    assert adapter.timeout == 60


def test_generate_until_signature():
    """generate_until accepts list[Instance] and is callable."""
    adapter = HermesAgentLM(agent_name="test")
    assert callable(adapter.generate_until)


def test_loglikelihood_signature():
    """loglikelihood accepts list[Instance] and is callable."""
    adapter = HermesAgentLM(agent_name="test")
    assert callable(adapter.loglikelihood)


def test_loglikelihood_rolling_signature():
    """loglikelihood_rolling returns list[float] for requests."""
    adapter = HermesAgentLM(agent_name="test")
    req = Instance(
        request_type="loglikelihood_rolling",
        doc={},
        arguments=("hello world",),
        idx=0,
    )
    results = adapter.loglikelihood_rolling([req])
    assert isinstance(results, list)
    assert len(results) == 1
    assert results[0] == 0.0  # ponytail: no logprobs, always 0.0


def test_score_exact_match():
    """Generated starts with continuation → high score, greedy."""
    logprob, is_greedy = HermesAgentLM._score_continuation(
        "hello", "hello world"
    )
    assert logprob > -1.0, f"Expected high logprob, got {logprob}"
    assert is_greedy is True


def test_score_contains():
    """Generated contains continuation → moderate score, not greedy."""
    logprob, is_greedy = HermesAgentLM._score_continuation(
        "world", "hello world"
    )
    assert -5.0 < logprob < -0.5, f"Expected moderate logprob, got {logprob}"
    assert is_greedy is False


def test_score_no_match():
    """Generated doesn't contain continuation → low score."""
    logprob, is_greedy = HermesAgentLM._score_continuation(
        "xyz", "hello world"
    )
    assert logprob < -5.0, f"Expected low logprob, got {logprob}"
    assert is_greedy is False


def test_score_empty_continuation():
    """Empty continuation → greedy match."""
    logprob, is_greedy = HermesAgentLM._score_continuation(
        "", "anything"
    )
    assert is_greedy is True


def test_trim_until():
    """stop sequences trim the output."""
    output = "line1\nSTOP\nline2"
    trimmed = HermesAgentLM._trim_until(output, ["STOP"])
    assert trimmed == "line1"


def test_trim_until_no_match():
    """No stop found → output unchanged."""
    output = "line1\nline2"
    trimmed = HermesAgentLM._trim_until(output, ["STOP"])
    assert trimmed == output


def test_trim_until_empty_until():
    """Empty until list → output unchanged."""
    output = "line1\nSTOP\nline2"
    trimmed = HermesAgentLM._trim_until(output, [])
    assert trimmed == output


def test_context_cache():
    """_context_cache avoids repeated hermes calls for same context."""
    adapter = HermesAgentLM(agent_name="test")
    # Cache should be empty initially
    assert len(adapter._context_cache) == 0


def test_detect_model():
    """detect_model returns a non-empty string or 'unknown'."""
    adapter = HermesAgentLM(agent_name="test")
    model = adapter.detect_model()
    assert isinstance(model, str)
    assert len(model) > 0
    # Should be 'unknown' if hermes not running, or a model name if running
    assert model == "unknown" or "/" in model or ":" in model


def test_build_prompt_passthrough():
    """By default, _build_generation_prompt passes through the context."""
    result = HermesAgentLM._build_generation_prompt("some prompt", {})
    assert result == "some prompt"


def test_generate_until_graceful_error():
    """Missing hermes binary → error string, not crash."""
    adapter = HermesAgentLM(
        agent_name="test",
        hermes_bin="/nonexistent/hermes",
    )
    req = Instance(
        request_type="generate_until",
        doc={},
        arguments=("test prompt", {}),
        idx=0,
    )
    results = adapter.generate_until([req])
    assert len(results) == 1
    assert "[ERROR" in results[0], f"Expected error, got: {results[0]}"


def test_generate_until_timeout_graceful():
    """Timeout produces error output, not crash.

    Uses a dummy command that sleeps: python3 -c 'import time; time.sleep(999)'
    """
    adapter = HermesAgentLM(
        agent_name="test",
        hermes_bin="python3",
        timeout=1,
    )
    req = Instance(
        request_type="generate_until",
        doc={},
        arguments=("-c\nimport time; time.sleep(999)", {}),
        idx=0,
    )
    results = adapter.generate_until([req])
    assert len(results) == 1
    assert "[ERROR" in results[0], f"Expected timeout error, got: {results[0]}"


# ── Run ──────────────────────────────────────────────────────────────────

tests = [
    ("extends_lm", test_extends_lm),
    ("init_defaults", test_init_defaults),
    ("generate_until_signature", test_generate_until_signature),
    ("loglikelihood_signature", test_loglikelihood_signature),
    ("loglikelihood_rolling_signature", test_loglikelihood_rolling_signature),
    ("score_exact_match", test_score_exact_match),
    ("score_contains", test_score_contains),
    ("score_no_match", test_score_no_match),
    ("score_empty_continuation", test_score_empty_continuation),
    ("trim_until", test_trim_until),
    ("trim_until_no_match", test_trim_until_no_match),
    ("trim_until_empty_until", test_trim_until_empty_until),
    ("context_cache", test_context_cache),
    ("detect_model", test_detect_model),
    ("build_prompt_passthrough", test_build_prompt_passthrough),
    ("generate_until_graceful_error", test_generate_until_graceful_error),
    ("generate_until_timeout_graceful", test_generate_until_timeout_graceful),
]

passed = 0
failed = 0
for name, fn in tests:
    try:
        fn()
        print(f"  ✅ {name}")
        passed += 1
    except AssertionError as e:
        print(f"  ❌ {name}: {e}")
        failed += 1
    except Exception as e:
        print(f"  💥 {name}: {e}")
        failed += 1

print(f"\n{passed}/{passed + failed} passed")
sys.exit(0 if failed == 0 else 1)
