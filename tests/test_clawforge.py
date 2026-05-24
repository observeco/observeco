"""Tests for clawforge modules — profile, load, garden."""
from observeco.clawforge.garden import _find_contradictions, _find_duplicates
from observeco.clawforge.load import _classify_intent, run_load
from observeco.clawforge.profile import _estimate_tokens as profile_estimate_tokens

SAMPLE_MEMORY_LINES = [
    "# Memory",
    "- The user prefers Python over JavaScript",
    "## User Info",
    "- The user's name is Alex",
    "- Project uses FastAPI",
    "- The user prefers Python over JavaScript",  # duplicate
    "- The user prefers Python over JavaScript",  # duplicate
    "## Platform Notes",
    "- The user likes dark mode",
    "- The agent does not support Windows",
    "## Configuration",
    "- Default timeout is 30 seconds",
    "- Uses local LLM by default",
    "## Capabilities",
    "- The agent supports Windows",              # contradiction (not within 3 lines of "does not support")
]


def test_classify_intent_debug():
    intent, confidence = _classify_intent("fix error bug crash exception broken")
    assert intent == "debug"
    assert confidence > 0.0


def test_classify_intent_status():
    intent, confidence = _classify_intent("what is going on summary status report")
    assert intent == "status"


def test_classify_intent_feature():
    intent, confidence = _classify_intent("can you add a new feature to export data")
    assert intent == "feature-request"


def test_classify_intent_config():
    intent, confidence = _classify_intent("change the configuration settings")
    assert intent == "config-change"

def test_classify_intent_general():
    intent, confidence = _classify_intent("hello how are you today")
    assert intent == "general-query"


def test_find_duplicates():
    dups = _find_duplicates(SAMPLE_MEMORY_LINES)
    assert len(dups) >= 1
    # Should find "prefers Python over JavaScript" as duplicate
    found = False
    for dup in dups:
        if "Python" in str(dup) and "JavaScript" in str(dup):
            found = True
    assert found, f"Should find Python/JS duplicate in: {dups}"


def test_find_contradictions():
    contras = _find_contradictions(SAMPLE_MEMORY_LINES)
    assert len(contras) >= 1


def test_find_duplicates_empty():
    assert _find_duplicates([]) == []


def test_find_duplicates_no_dupes():
    lines = ["- A", "- B", "- C"]
    assert _find_duplicates(lines) == []


def test_find_contradictions_empty():
    assert _find_contradictions([]) == []


def test_profile_estimate():
    assert profile_estimate_tokens(100) == 25
    assert profile_estimate_tokens(0) == 1  # max(1, chars/4)


def test_run_load_runs():
    try:
        run_load()  # Should not crash without stdin
    except SystemExit:
        pass
