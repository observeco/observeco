"""Self-check for LLM-as-a-Verifier scoring logic.

Tests the pure functions (_token_to_score, _expected_score_from_logprobs,
_parse_discrete_score) without requiring an LLM API call.

Run: pytest tests/capability/test_llm_verifier_scoring.py -v
"""

from __future__ import annotations

import math

from observeco.capability.canary import Scorer


# ── _token_to_score ──────────────────────────────────────────────────────

def test_token_to_score_valid():
    assert Scorer._token_to_score("1") == 1.0
    assert Scorer._token_to_score("10") == 10.0
    assert Scorer._token_to_score("20") == 20.0
    assert Scorer._token_to_score(" 15 ") == 15.0


def test_token_to_score_invalid():
    assert Scorer._token_to_score("0") is None      # below range
    assert Scorer._token_to_score("21") is None      # above range
    assert Scorer._token_to_score("abc") is None     # non-numeric
    assert Scorer._token_to_score("") is None        # empty
    assert Scorer._token_to_score("3.5") == 3.5      # float within range


# ── _expected_score_from_logprobs ────────────────────────────────────────

def test_expected_score_clear_winner():
    """When one token has ~100% probability, expected score ≈ that token's score."""
    logprobs = [
        {
            "token": "18",
            "logprob": -0.01,
            "top_logprobs": [
                {"token": "18", "logprob": -0.01},
                {"token": "17", "logprob": -5.0},
                {"token": "19", "logprob": -6.0},
            ],
        }
    ]
    score = Scorer._expected_score_from_logprobs(logprobs)
    assert score is not None
    # 18 on 1-20 scale → (18-1)/(20-1) = 17/19 ≈ 0.895
    assert abs(score - 17.0/19.0) < 0.02


def test_expected_score_uniform():
    """When two tokens have equal probability, expected score is their average."""
    logprobs = [
        {
            "token": "10",
            "logprob": -0.7,
            "top_logprobs": [
                {"token": "10", "logprob": math.log(0.5)},
                {"token": "14", "logprob": math.log(0.5)},
            ],
        }
    ]
    score = Scorer._expected_score_from_logprobs(logprobs)
    assert score is not None
    # avg(10, 14) = 12 → (12-1)/19 ≈ 0.579
    assert abs(score - 11.0/19.0) < 0.01


def test_expected_score_no_valid_tokens():
    """Returns None when no top_logprobs contain valid score tokens."""
    logprobs = [
        {
            "token": "<",
            "logprob": -0.1,
            "top_logprobs": [
                {"token": "<", "logprob": -0.1},
                {"token": "score", "logprob": -2.0},
            ],
        }
    ]
    assert Scorer._expected_score_from_logprobs(logprobs) is None


def test_expected_score_empty():
    assert Scorer._expected_score_from_logprobs([]) is None
    assert Scorer._expected_score_from_logprobs([{"token": "5", "logprob": -0.1, "top_logprobs": []}]) is None


def test_expected_score_finds_score_position():
    """Should skip non-score tokens and find the first position with valid scores."""
    logprobs = [
        {
            "token": "<",
            "logprob": -0.01,
            "top_logprobs": [
                {"token": "<", "logprob": -0.01},
                {"token": "score", "logprob": -3.0},
            ],
        },
        {
            "token": "15",
            "logprob": -0.05,
            "top_logprobs": [
                {"token": "15", "logprob": -0.05},
                {"token": "14", "logprob": -3.0},
            ],
        },
    ]
    score = Scorer._expected_score_from_logprobs(logprobs)
    assert score is not None
    # Should find position 1 with score 15 → (15-1)/19 ≈ 0.737
    assert abs(score - 14.0/19.0) < 0.02


# ── _parse_discrete_score ────────────────────────────────────────────────

def test_parse_discrete_score_tag():
    assert Scorer._parse_discrete_score("<score>15</score>") == 14.0/19.0
    assert Scorer._parse_discrete_score("blah <score>1</score> blah") == 0.0


def test_parse_discrete_score_colon():
    assert Scorer._parse_discrete_score("Score: 18") == 17.0/19.0
    assert Scorer._parse_discrete_score("score=10") == 9.0/19.0


def test_parse_discrete_score_bare_number():
    # Last valid 1-20 number in text
    assert Scorer._parse_discrete_score("I rate this 12") == 11.0/19.0
    # When multiple valid numbers exist, takes the last one
    assert Scorer._parse_discrete_score("score 8 then 15") == 14.0/19.0


def test_parse_discrete_score_none():
    assert Scorer._parse_discrete_score("no score here") is None
    assert Scorer._parse_discrete_score("0 21 100") is None  # none in 1-20


# ── Normalization invariant ──────────────────────────────────────────────

def test_score_normalization_range():
    """All scores must be in [0.0, 1.0] after normalization."""
    for val in [1, 5, 10, 15, 20]:
        score = Scorer._token_to_score(str(val))
        assert score is not None
        normalized = (score - Scorer._SCORE_MIN) / (Scorer._SCORE_MAX - Scorer._SCORE_MIN)
        assert 0.0 <= normalized <= 1.0


if __name__ == "__main__":
    # Quick self-check without pytest
    test_token_to_score_valid()
    test_token_to_score_invalid()
    test_expected_score_clear_winner()
    test_expected_score_uniform()
    test_expected_score_no_valid_tokens()
    test_expected_score_empty()
    test_expected_score_finds_score_position()
    test_parse_discrete_score_tag()
    test_parse_discrete_score_colon()
    test_parse_discrete_score_bare_number()
    test_parse_discrete_score_none()
    test_score_normalization_range()
    print("All self-checks passed.")