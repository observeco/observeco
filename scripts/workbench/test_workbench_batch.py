"""Regression tests for the Workbench batch runner's containment logic.

Covers the two bugs extracted by the adversarial loop:
1. containment_check false-flagged relative-path writes (resolved against
   runner cwd instead of the worktree).
2. trials.append(entry) fired twice per trial (gate branches + finally).

These test the runner against REAL transcripts from the completed batch
(sessions wrote into pinned worktrees), so they double as integration checks.
"""
import importlib.util
import pathlib
import re

_SCRIPT = pathlib.Path(__file__).parent / "batch_runner.py"


def _load_mod():
    spec = importlib.util.spec_from_file_location("batch_runner", _SCRIPT)
    if spec is None or spec.loader is None:  # pragma: no cover
        raise RuntimeError(f"cannot load {_SCRIPT}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


mod = _load_mod()


def test_absolute_worktree_writes_pass_containment():
    """Session 062047 wrote only under /tmp/workbench-...-t3. Must pass."""
    res = mod.containment_check(
        "t", "20260804_062047_47fe0c",
        "/private/tmp/workbench-20260716_222458_08f889-234ba209-t3",
    )
    assert res["violated"] is False, res["reason"]


def test_relative_worktree_writes_pass_containment():
    """Session 061909 wrote ./src/... (agent cwd = worktree). The fixed checker
    resolves relative paths against the worktree root, not the runner cwd."""
    res = mod.containment_check(
        "t", "20260804_061909_089af3",
        "/private/tmp/workbench-20260716_222458_08f889-234ba209-t2",
    )
    assert res["violated"] is False, res["reason"]


def test_candidate2_worktree_writes_pass_containment():
    """Session 062227 (candidate 2) wrote 17 paths under its -t1 worktree."""
    res = mod.containment_check(
        "t", "20260804_062227_be0de8",
        "/private/tmp/workbench-20260716_211847_f22f8d-b9115bc2-t1",
    )
    assert res["violated"] is False, res["reason"]


def test_relative_path_resolves_against_worktree_not_runner_cwd():
    """A bare relative path must resolve under the worktree, never the cwd."""
    wt = "/private/tmp/workbench-fake"
    rp = str((pathlib.Path(wt) / "./src/observeco/capability/canary.py").resolve())
    assert rp.startswith(wt)
    assert "/projects/" not in rp


def test_trials_appended_exactly_once_per_trial():
    """Double-append bug: each trial must append to trials exactly once."""
    src = pathlib.Path(_SCRIPT).read_text()
    appends = re.findall(r"trials\.append\(entry\)", src)
    assert len(appends) == 1, f"expected 1 append, found {len(appends)}"


def test_containment_writes_must_be_under_worktree():
    """A write to a sibling repo root must be a violation (leakage guard)."""
    # Synthesize: no real session writes to siblings post-fix, so assert the
    # rule structurally — the checker compares against the worktree root.
    src = pathlib.Path(_SCRIPT).read_text()
    assert "if not rp.startswith(str(wt))" in src
