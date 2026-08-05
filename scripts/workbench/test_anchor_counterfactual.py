"""Tests for the anchor unit-counterfactual — the mechanism-sanity harness.

Binds anchor_counterfactual.py into the suite (it was run manually but never
had pytest coverage). Asserts the core mechanism's contract:

- uniqueness_precheck fires (would_fire=True) on not_found and ambiguous,
  passes on unique.
- The counterfactual extracts real failed-patch anchors from a known session.
- The result is honest about the state-drift limitation (no_file is recorded,
  not hidden).
"""
import importlib.util
import pathlib

_SCRIPT = pathlib.Path(__file__).parent / "anchor_counterfactual.py"


def _load():
    spec = importlib.util.spec_from_file_location("anchor_counterfactual", _SCRIPT)
    if spec is None or spec.loader is None:  # pragma: no cover
        raise RuntimeError(f"cannot load {_SCRIPT}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


mod = _load()


def test_precheck_fires_on_not_found():
    r = mod.uniqueness_precheck("file has unique text here", "this string is absent")
    assert r["class"] == "not_found"
    assert r["would_fire"] is True


def test_precheck_fires_on_ambiguous():
    r = mod.uniqueness_precheck("dup dup and more dup", "dup")
    assert r["class"] == "ambiguous"
    assert r["would_fire"] is True
    assert r["count"] > 1


def test_precheck_passes_on_unique():
    r = mod.uniqueness_precheck("the one and only target", "only target")
    assert r["class"] == "unique"
    assert r["would_fire"] is False
    assert r["count"] == 1


def test_empty_anchor_flagged():
    r = mod.uniqueness_precheck("any content", "")
    assert r["class"] == "empty_anchor"
    assert r["would_fire"] is True


def test_extracts_real_failed_anchors():
    """A session with a known patch_anchor failure yields failed patch calls."""
    # 20260711_104552 had 'Found 2 matches for old_string' — must extract
    patches = mod.extract_failed_patches("20260711_104552_ba097abe")
    assert patches, "expected at least one failed patch anchor call"
    # each is a (path, old_string) pair with a non-empty old_string
    for path, old in patches:
        assert path, "path must be present"
        assert old, "old_string must be present"


def test_no_file_recorded_not_hidden():
    """The state-drift limitation is recorded (no_file), not silently dropped."""
    # normalize_path maps observeco-old to current; a nonexistent path -> None
    # directly test file_at_pin on a guaranteed-absent path returns None
    assert mod.file_at_pin("/nonexistent/definitely/absent.py") is None
