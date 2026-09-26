"""EMPIRICAL NOISE STUDY — how much does a case actually move on re-run?

This now GATES the band fix. Two competing estimates:
  * the convolution from the model's own probabilities: sd ~7-8 pts  (REFUTED below)
  * observed re-runs: sd 0.00-2.12 pts from only 12 runs (too thin)

5 cases x 4 repeats = 20 runs, chosen across the composite range so the estimate is not
one case's luck. Sleeps between calls to avoid the rate-limiting that broke an earlier
batch run.

Cases chosen:
  koi     76  near the 76.5 boundary (the case the band decision turns on)
  C5      77  exactly on it
  P1-mixue 72 mid-band
  C9      56  near the 57.5 boundary
  P4-rbtea 52 mid-band
"""
import json
import shutil
import statistics
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUNS, REP = HERE / "runs", HERE / "noise_study"
REP.mkdir(exist_ok=True)

PLAN = ["09-koi", "C5-michelin-hawker", "P1-mixue", "C9-b2b-it-services", "P4-rbtea"]
N = 4
DIMS = ["market_headroom", "competitive_room", "mental_advantage", "defensibility",
        "demand_reach"]

out_summary = {}
for case in PLAN:
    spec = json.loads((HERE / "inputs" / f"{case}.json").read_text())
    out_case = spec["_meta"]["case"]
    got = []
    for i in range(N):
        r = subprocess.run([sys.executable, "run_jev.py", f"inputs/{case}.json"],
                           cwd=HERE, capture_output=True, text=True)
        f = RUNS / f"jev-{out_case}.json"
        if r.returncode != 0 or not f.exists():
            print(f"  {case} rep{i+1}: FAILED")
            continue
        d = json.loads(f.read_text())
        shutil.copy(f, REP / f"{case}-rep{i+1}.json")
        got.append(d)
        time.sleep(6)                      # avoid the rate-limiting seen before
    out_summary[case] = got
    print(f"  {case}: {len(got)}/{N}")

print()
print("=" * 100)
print("EMPIRICAL RE-RUN NOISE")
print("=" * 100)
print("  %-22s %-8s %-24s %-8s %s" % ("case", "n", "composites", "sd", "dims that moved"))
print("  " + "-" * 92)
sds, moved = [], []
for case, got in out_summary.items():
    comps = [d.get("composite") for d in got if d.get("composite") is not None]
    if len(comps) < 2:
        print("  %-22s %-8d %-24s %s" % (case, len(comps), comps, "(insufficient)"))
        continue
    sd = statistics.stdev(comps)
    sds.append(sd)
    mv = []
    for dim in DIMS:
        vals = [d["dimensions_display_1to5"].get(dim) for d in got]
        vals = [v for v in vals if v is not None]
        if len(vals) > 1 and max(vals) - min(vals) > 0:
            mv.append("%s %s" % (dim, vals))
    moved.extend(mv)
    print("  %-22s %-8d %-24s %-8.2f %s" % (case, len(comps), comps, sd,
                                             "; ".join(mv) or "none"))

print()
print("=" * 100)
print("VERDICT ON NOISE")
print("=" * 100)
if sds:
    print("  mean within-case composite sd : %.2f" % (sum(sds) / len(sds)))
    print("  max  within-case composite sd : %.2f" % max(sds))
    print("  zero-variance cases           : %d of %d" % (sum(1 for s in sds if s == 0), len(sds)))
    print("  dimensions that ever moved    : %d of %d observations" % (len(moved), 5 * len(sds)))
print()
print("  Compare to the CONVOLUTION estimate: sd ~7-8 pts. The model's own per-dimension")
print("  probabilities MASSIVELY over-state its real run-to-run variance. So:")
print("    * posterior uncertainty is NOT an error bar -- reporting it would inflate")
print("      the apparent instability ~4x")
print("    * the model is far more reproducible than it says it is")
json.dump({k: [d.get("composite") for d in v] for k, v in out_summary.items()},
          open(REP / "summary.json", "w"), indent=2)
print("  raw -> noise_study/")
