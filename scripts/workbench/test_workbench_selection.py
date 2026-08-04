"""Fixture tests for Workbench selection.

The distinguishing test from spec v0.1: derived fields must match EXACTLY,
and non-derivable / unverifiable fields must be null (never guessed). A schema
test is worthless — well-formed JSON with plausible-but-wrong derived values
passes schema. This asserts exactness.

Fixture: session 20260716_222458_08f889 (the validated _semantic_similarity
candidate). Known-correct derived values established by hand.
"""
import importlib.util
import pathlib

_SCRIPT = pathlib.Path(__file__).parent / "selection.py"


def _load_mod():
    spec = importlib.util.spec_from_file_location("selection", _SCRIPT)
    if spec is None or spec.loader is None:  # pragma: no cover
        raise RuntimeError(f"cannot load {_SCRIPT}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


mod = _load_mod()

FIXTURE_SID = "20260716_222458_08f889"
KNOWN_SHA = "fb05b55"
KNOWN_BUDGET = 252
KNOWN_REL = "src/observeco/capability/canary.py"
KNOWN_MARKER = "_semantic_similarity"


def test_derived_sha_matches_exactly():
    sha = mod.recover_start_sha(FIXTURE_SID)
    assert sha == KNOWN_SHA, f"sha {sha} != known {KNOWN_SHA}"


def test_derived_budget_matches_exactly():
    dur = mod.session_duration(FIXTURE_SID)
    budget = max(dur * 3, 180)
    assert budget == KNOWN_BUDGET, f"budget {budget} != known {KNOWN_BUDGET}"


def test_derived_rel_path_matches_exactly():
    rel = mod.most_frequent_write_rel(FIXTURE_SID)
    assert rel == KNOWN_REL, f"rel {rel} != known {KNOWN_REL}"


def test_derived_marker_matches_exactly():
    task = mod.first_user_message(FIXTURE_SID)
    marker = mod.subject_symbol(task)
    assert marker == KNOWN_MARKER, f"marker {marker} != known {KNOWN_MARKER}"


def test_marker_absent_at_pin_and_present_in_completion():
    # This is the FAIL_TO_PASS cross-check — marker must be absent at pin,
    # present in the original completion.
    absent = mod.marker_absent_at_pin(KNOWN_SHA, KNOWN_REL, KNOWN_MARKER)
    assert absent is True, f"marker should be absent at pin, got {absent}"
    present = mod.marker_in_completion(FIXTURE_SID, KNOWN_REL, KNOWN_MARKER)
    assert present is True, "marker should be present in original completion"


def test_select_session_emits_draft_with_derived_exact():
    log = []
    draft = mod.select_session(FIXTURE_SID, log)
    assert draft is not None, "fixture should produce a candidate draft"
    assert draft["sha"] == KNOWN_SHA
    assert draft["budget"] == KNOWN_BUDGET
    assert draft["rel"] == KNOWN_REL
    # authored fields must be null or present-but-human, never guessed
    assert draft["task_description"] is None, "description is authored, must be null"
    # marker may be set if cross-check passes; if set it must be the known value
    if draft["marker"] is not None:
        assert draft["marker"] == KNOWN_MARKER
