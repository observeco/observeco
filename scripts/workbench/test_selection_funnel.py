"""Distinguishing tests for the selection funnel fixes.

Two fixes, both gated as classes rather than patched instances:

1. cron-content gate (17th-instance law): a session with source=telegram but
   cron-job CONTENT must be rejected. Screen on the TRAJECTORY (content), not
   the summary column. This is the distinguishing test the user called for —
   the fixture is a telegram-source session carrying cron output.

2. entanglement gate: two sequential sessions pinning the same SHA with the
   same target file are one task (a 'find X' then 'replace X' pair). Only the
   first is emitted; the later must be rejected. Without this, both replay a
   shared world.
"""
import importlib.util
import pathlib
import sys

sys.path.insert(0, "/Users/seanfzc/projects/observeco-main/scripts/workbench")

_SCRIPT = pathlib.Path(__file__).parent / "selection.py"


def _load_mod():
    spec = importlib.util.spec_from_file_location("selection", _SCRIPT)
    if spec is None or spec.loader is None:  # pragma: no cover
        raise RuntimeError(f"cannot load {_SCRIPT}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


mod = _load_mod()


def test_telegram_source_with_cron_content_rejected():
    """A telegram-source session whose CONTENT is cron output must be rejected.
    This fails on the pre-fix code, which screened only on source != 'cron' and
    let telegram-source cron content through as a candidate."""
    cron_task = (
        '[Replying to: "Cronjob Response: Canary Benchmark — Daily 03:00 '
        '(job_id: b3fbde1b48f1)"]\n⚠️ Cron failed...'
    )
    assert mod.is_cron_content(cron_task) is True


def test_real_task_content_not_rejected():
    """A genuine user task must NOT be flagged as cron content (no over-matching)."""
    real_task = "Add the _semantic_similarity assertion type to the Scorer class in canary.py"
    assert mod.is_cron_content(real_task) is False


def test_entangled_same_sha_same_rel_rejected():
    """A second draft sharing pin SHA AND target file with an earlier draft is
    entangled — the later must be rejected (would replay a shared world)."""
    pool = [{"sha": "fb05b55", "rel": "src/observeco/dashboard/server.py"}]
    assert mod.is_entangled("fb05b55", "src/observeco/dashboard/server.py", pool) is True


def test_distinct_rel_not_entangled():
    """Different target file (different task) is not entangled even at same SHA."""
    pool = [{"sha": "fb05b55", "rel": "src/observeco/dashboard/server.py"}]
    assert mod.is_entangled("fb05b55", "src/observeco/db.py", pool) is False


def test_distinct_sha_not_entangled():
    """Different pin SHA (different world) is not entangled."""
    pool = [{"sha": "fb05b55", "rel": "src/observeco/dashboard/server.py"}]
    assert mod.is_entangled("abc1234", "src/observeco/dashboard/server.py", pool) is False
