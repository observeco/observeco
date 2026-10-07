"""Two-sided test for check_report_drift.py.

A guard that only ever says PASS is worthless -- it must be shown to FAIL on the real defect it
exists to catch. This does both directions:

  A. current code           -> exit 0 (no drift)
  B. the OLD competitive_room wording -> exit 1 (drift detected)
  C. the OLD defensibility wording    -> exit 1 (drift detected)

B and C are injected by monkeypatching DIM_MEANING in-process, so the repo is never modified.
"""
import importlib
import io
import sys
from contextlib import redirect_stdout
from pathlib import Path

BASE = Path("/Users/seanfzc/projects/observeco-main/specs/calibration")
sys.path.insert(0, str(BASE))


def run_guard() -> tuple[int, str]:
    import check_report_drift as g
    import generate_report as gr
    importlib.reload(g)
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = g.main()
    return code, buf.getvalue()


def with_def(dim: str, text: str) -> tuple[int, str]:
    import generate_report as gr
    original = gr.DIM_MEANING[dim]
    gr.DIM_MEANING[dim] = text
    try:
        return run_guard()
    finally:
        gr.DIM_MEANING[dim] = original


print("A. CURRENT code")
code, out = run_guard()
print("   exit", code, "->", "✅ PASS (expected)" if code == 0 else "✗ FAIL — expected pass")
a_ok = code == 0

print("\nB. OLD competitive_room wording (the real defect)")
old_cr = ("How much margin is left for you after the big players set the "
          "price.")
code, out = with_def("competitive_room", old_cr)
fired = "competitive_room" in out and code == 1
print("   exit", code, "->", "✅ FIRES (expected)" if fired else "✗ DID NOT FIRE")
if fired:
    for ln in out.splitlines():
        if ln.strip().startswith("-"):
            print("     ", ln.strip()[:120])

print("\nC. OLD defensibility wording (the direct contradiction)")
old_df = "How hard it would be for a rival to copy what makes you different."
code, out = with_def("defensibility", old_df)
fired2 = "defensibility" in out and code == 1
print("   exit", code, "->", "✅ FIRES (expected)" if fired2 else "✗ DID NOT FIRE")

print("\nD. the CURRENT defensibility wording must NOT fire (negation-aware)")
cur_df = ("How hard it would be for a rival to copy your position — judged by what they "
          "would have to assemble, not by the difference you claim.")
code, out = with_def("defensibility", cur_df)
# ⚠ assert on the EXIT CODE, not on whether the word appears: the verbose listing names every
# dimension on every run, so a substring test is always true. (Caught by running it.)
clean = (code == 0) and ("DRIFT DETECTED" not in out)
print("   exit", code, "->", "✅ clean (expected)" if clean else "✗ FALSE POSITIVE")

# E. ⚠ THE CASE THAT PROVED THE GUARD WAS TOO NARROW: drift in GATE_TEXT, not DIM_MEANING.
# The first guard read DIM_MEANING only, so it passed while GATE_TEXT carried the same
# contradiction. GATE_TEXT is read ALONE under "THE ONE THING THAT DECIDES IT", so this is the
# surface where the defect matters most.
print("\nE. drift in GATE_TEXT (the surface read alone) -- must FIRE")
import generate_report as _gr
_orig_gate = _gr.GATE_TEXT["defensibility"]
_gr.GATE_TEXT["defensibility"] = "whether what makes you different survives a competitor deciding to copy it"
try:
    code, out = run_guard()
finally:
    _gr.GATE_TEXT["defensibility"] = _orig_gate
fired3 = (code == 1) and ("defensibility" in out)
print("   exit", code, "->", "✅ FIRES (expected)" if fired3 else "✗ DID NOT FIRE")

print("\nALL TWO-SIDED CHECKS PASS:", a_ok and fired and fired2 and clean and fired3)
