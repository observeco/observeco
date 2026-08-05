"""Tests for the C2 task revision record.

Binds c2-revised-task.py into the suite so the flagged generator path has real
regression coverage. Asserts the revision's OUTPUT CONTRACT:

- It is a RECORDED revision (original preserved, not an in-place edit).
- It names the three tables explicitly (phantom obs-spec-061 dropped) so a
  replayed model is scored against a fully-specified outcome contract.
- It anchors the agent to the worktree (at the current location / do not look
  outside) — the anchor whose loss caused real containment violations.
- The generated candidate JSON is well-formed and matches the contract.
"""
import importlib.util
import json
import pathlib

_SCRIPT = pathlib.Path(__file__).parent / "selections" / "c2-revised-task.py"


def _load():
    spec = importlib.util.spec_from_file_location("c2rev", _SCRIPT)
    if spec is None or spec.loader is None:  # pragma: no cover
        raise RuntimeError(f"cannot load {_SCRIPT}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


mod = _load()
R = mod.REVISED


def test_is_recorded_revision_not_inplace_edit():
    assert R["revision"] == 2
    assert R["revision_reason"]
    # original task preserved for audit
    assert "obs-spec-056" in R["original_task"]


def test_phantom_spec_reference_removed():
    # The revision must not reference the phantom spec that confused replay
    # agents, but the ORIGINAL task (preserved for audit) may retain it.
    assert "obs-spec-061" not in R["task"]
    assert "obs-spec-061" in R["original_task"]  # preserved, not silently edited away


def test_three_tables_named_explicitly():
    for t in ["harness_optimization_runs", "harness_eval_runs", "harness_edits"]:
        assert t in R["task"], f"table {t} must be named"


def test_anchored_to_worktree():
    # The anchor whose loss caused real containment violations.
    assert "at the current location" in R["task"]
    assert "do not look outside" in R["task"]


def test_marker_and_pin_valid():
    assert R["marker"] == "harness_optimization_runs"
    assert R["marker_strength"] == "strong"
    assert R["sha"] == "fb05b55"
    assert R["rel"] == "src/observeco/db.py"


def test_generated_json_matches_contract():
    """Running the generator must emit a candidate whose load-bearing fields
    match the REVISED contract — so the JSON and the source never diverge."""
    import subprocess
    out = "/tmp/workbench-c2-revised.json"
    r = subprocess.run(
        ["/Users/seanfzc/projects/observeco-cap/.venv/bin/python", str(_SCRIPT)],
        capture_output=True, text=True, timeout=30,
    )
    assert r.returncode == 0, r.stderr
    cand = json.load(open(out))[0]
    for k in ("id", "marker", "sha", "rel", "repo_root", "budget", "assertion"):
        assert cand[k] == R[k], f"{k}: {cand[k]} != {R[k]}"
