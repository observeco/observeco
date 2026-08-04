"""Regression tests for the Workbench verdict split (corrected scope).

Guards the specific bug: batch_runner.py previously assigned BOTH
summary_verdict and trajectory_verdict to the same deterministic `passed`
boolean — a copied value under two names, which made the doc's
"trajectory is the truth" spine uninstrumented while appearing measured.

Corrected scope (workbench-v4 §0):
  - summary_verdict      = marker check (what a naive summary reports).
  - containment_verdict  = deterministic provenance from the transcript
                           (confinement + leakage). NOT trajectory-truth.
  - trajectory_verdict   = None. Never a copy of summary_verdict. Deferred
                           to an LLM-judge trajectory pass (token cost per run).
  - needs_review         = True iff containment violated (quarantine).

These are structural tests against the runner source, matching the existing
test_workbench_batch.py style, so they pass/fail without spawning agents.
"""
import importlib.util
import pathlib

_SCRIPT = pathlib.Path(__file__).parent / "batch_runner.py"


def _load_mod():
    spec = importlib.util.spec_from_file_location("batch_runner", _SCRIPT)
    if spec is None or spec.loader is None:  # pragma: no cover
        raise RuntimeError(f"cannot load {_SCRIPT}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


mod = _load_mod()
SRC = _SCRIPT.read_text()


def test_trajectory_verdict_never_copied_from_summary():
    """THE regression: trajectory_verdict must never be assigned from the
    marker check (`passed`). This is the specific lie the corrected scope
    forbids — a copied value under two names."""
    import re
    # Any assignment of trajectory_verdict must be to None only.
    assigns = re.findall(
        r'entry\["trajectory_verdict"\]\s*=\s*([^\n]+)', SRC
    )
    assert assigns, "trajectory_verdict should be assigned at least once (to None)"
    for a in assigns:
        assert a.strip() == "None", f"trajectory_verdict must be null, got: {a.strip()}"


def test_containment_verdict_computed_from_transcript():
    """containment_verdict must be set from the containment check, and set on
    BOTH the violated and clean paths (a violated run must record explicit
    'violated', not silently miss the field)."""
    assert "entry[\"containment_verdict\"] = \"violated\"" in SRC
    assert "entry[\"containment_verdict\"] = \"clean\"" in SRC


def test_needs_review_set_on_both_paths():
    """needs_review must be recorded before the containment branch, so a
    violation yields needs_review=True (quarantine) and a clean run yields
    False — never an unset field."""
    assert "entry[\"needs_review\"] = bool(containment[\"violated\"])" in SRC
    # needs_review is set immediately after containment, before any continue.
    assert SRC.index("entry[\"needs_review\"]") < SRC.index("if containment[\"violated\"]")


def test_summary_verdict_remains_marker_check():
    """summary_verdict still reflects the marker check — that is its contract."""
    assert "entry[\"summary_verdict\"] = \"pass\" if passed else \"fail\"" in SRC


def test_unmeasured_trials_never_yield_fail():
    """17th fix: a candidate whose trials are all unmeasured (session_id not
    captured, or infra-aborted with no completed trials) must be UNMEASURED,
    never FAIL. Absence of evidence is not negative evidence — treating
    unmeasured trials as failures would deflate exactly like trial-2's false
    negative. This fails on the pre-fix code, where an all-unmeasured candidate
    derived `passes=0` -> `FAIL`."""
    # The status derivation must distinguish measured from unmeasured trials.
    assert "measured = [t for t in trials if t[\"status\"] in (\"pass\", \"fail\")]" in SRC
    # UNMEASURED must be a real outcome, gated on measured_count, not a bare
    # `PASS if passes>=2 else FAIL` that turns absence into a failure.
    assert '"UNMEASURED"' in SRC
    # The all-unmeasured trial status is recorded explicitly, not left pending.
    assert "entry[\"status\"] = \"unmeasured\"" in SRC


def test_unmeasured_trial_records_null_not_fake():
    """An unmeasured trial records null verdicts (unmeasured), never a
    fabricated pass or fail — null-not-faked applied to the verdict itself."""
    assert "entry[\"summary_verdict\"] = \"unmeasured\"" in SRC
    assert "entry[\"containment_verdict\"] = \"unmeasured\"" in SRC
