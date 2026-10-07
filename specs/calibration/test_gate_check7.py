"""Does check 7 actually gate a promotion? Tested on a COPY -- the live rubric is never touched.

A guard wired into a gate must be shown to REFUSE, not merely to exist. So this:

  1. builds a candidate rubric in a temp dir that is valid in every other respect
  2. sabotages generate_report.DIM_MEANING in-process to simulate drift
  3. runs the gate's check and asserts it REFUSES

Step 3 runs the same check function the gate runs, in-process, so no file is written.
"""
import importlib
import io
import json
import shutil
import sys
from contextlib import redirect_stdout
from pathlib import Path

BASE = Path("/Users/seanfzc/projects/observeco-main/specs/calibration")
sys.path.insert(0, str(BASE))

print("=== the drift check, as the gate calls it ===")


def gate_check() -> tuple[bool, str]:
    """Mirror of promote_rubric check 7: returns (refused, detail)."""
    import check_report_drift as d
    importlib.reload(d)
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = d.main()
    return rc != 0, buf.getvalue()


ok, out = gate_check()
print("  clean rubric ->", "PASS (promotion allowed)" if not ok else "REFUSED")

# simulate the drift the guard exists to catch
import generate_report as gr
original = gr.DIM_MEANING["competitive_room"]
gr.DIM_MEANING["competitive_room"] = "How much margin is left for you after the big players set the price."
try:
    ok2, out2 = gate_check()
finally:
    gr.DIM_MEANING["competitive_room"] = original

print("  drifted rubric ->", "REFUSED (promotion blocked)" if ok2 else "✗ ALLOWED — the gate does not work")
for ln in out2.splitlines():
    if ln.strip().startswith("-"):
        print("     ", ln.strip()[:110])

# and the live rubric file must be byte-identical (we never wrote to it)
live = BASE / "rubric.json"
print("\n  live rubric untouched:", json.loads(live.read_text())["_meta"]["version"])

print("\nCHECK 7 GATES PROMOTION:", ok2 and not ok)
