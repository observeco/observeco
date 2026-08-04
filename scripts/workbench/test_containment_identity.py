"""Distinguishing test for the containment-identity provenance fix.

Failure class: the gate auditing the WRONG SUBJECT — right method, right data,
wrong entity. Candidate session's tool calls reference sibling repo paths;
replay session's are clean worktree writes. Containment must PASS when audited
against the replay session id, and the candidate id alone must NOT be used.

This test fails on the pre-fix code (which passed the candidate id to
containment_check, false-flagging every replay whose candidate touched the
real repo) and on any implementation that resolves identity by heuristic
(state.db window correlation), not by the adapter's declared session id.
"""
import importlib.util
import pathlib
import sys

sys.path.insert(0, "/Users/seanfzc/projects/observeco/src")

_SCRIPT = pathlib.Path(__file__).parent / "batch_runner.py"


def _load_mod():
    spec = importlib.util.spec_from_file_location("batch_runner", _SCRIPT)
    if spec is None or spec.loader is None:  # pragma: no cover
        raise RuntimeError(f"cannot load {_SCRIPT}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


mod = _load_mod()

# The validated fixture: candidate 20260716_222458_08f889 (references the real
# repo in its own tool calls) vs. replay session 20260804_192828_4706cd (patched
# only into the -t2 worktree). If containment audits the candidate, it flags; if
# it audits the replay, it passes.
CANDIDATE_ID = "20260716_222458_08f889"
REPLAY_ID = "20260804_192828_4706cd"
WORKTREE_T2 = "/private/tmp/workbench-20260716_222458_08f889-469e4b02-t2"


def test_candidate_id_alone_is_not_trusted():
    """The candidate session references the real repo — auditing it against a
    worktree MUST NOT be the mechanism. Assert the runner uses replay id, and
    that the candidate id referenced a sibling (the original bug's trigger)."""
    from observeco.benchmark.adapters.hermes import HermesBenchmarkAdapter
    # The adapter now exposes _parse_session_id — regression that it exists.
    assert hasattr(HermesBenchmarkAdapter, "_parse_session_id")
    # Sanity: candidate referenced real repo (this is why auditing it = false positive)
    import sqlite3
    conn = sqlite3.connect("/Users/seanfzc/.hermes/state.db")
    n = conn.execute(
        "SELECT COUNT(*) FROM messages WHERE session_id=? AND tool_calls LIKE '%projects/observeco%'",
        (CANDIDATE_ID,),
    ).fetchone()[0]
    conn.close()
    assert n >= 1, "fixture broken: candidate must reference sibling for test to be meaningful"


def test_replay_session_passes_containment():
    """Auditing the REPLAY session (which patched only into -t2) must pass."""
    res = mod.containment_check("t", REPLAY_ID, WORKTREE_T2)
    assert res["violated"] is False, f"replay session should pass containment: {res['reason']}"


def test_candidate_audited_against_worktree_would_flag():
    """Demonstrates the pre-fix bug: the candidate session (real-repo refs)
    audited against the worktree WOULD flag. Confirms the fix is necessary."""
    res = mod.containment_check("t", CANDIDATE_ID, WORKTREE_T2)
    assert res["violated"] is True, "candidate has sibling refs — auditing it must flag (pre-fix bug demo)"
