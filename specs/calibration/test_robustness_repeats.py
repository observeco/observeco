"""ROBUSTNESS — is the Gong Cha refusal REPRODUCIBLE, and what is composite noise?

The headline result rests on ONE run. If Gong Cha's gate flips on re-run, the finding
is a coin toss and must be reported as such. This also measures sigma_composite, which
I flagged as the thing that gates every other decision (band boundaries are 1-point
steps; if noise is near 1 point, near-boundary cases are coin flips).

Protocol:
  * Gong Cha x 5  -- does defensibility stay at the gate floor?
  * KOI x 3, Chicha x 2, Mixue x 2  -- per-dimension + composite spread
  * store every repeat; never overwrite the canonical run
"""
import json
import shutil
import statistics
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUNS = HERE / "runs"
REPEATS = HERE / "repeats"
REPEATS.mkdir(exist_ok=True)

PLAN = [("P5-gongcha", 5), ("09-koi", 3), ("P2-chicha", 2), ("P1-mixue", 2)]
DIMS = ["market_headroom", "competitive_room", "mental_advantage", "defensibility",
        "demand_reach"]

results = {}
for case, n in PLAN:
    # the run file is named after the input's _meta.case, which is NOT always the
    # input filename (inputs/09-koi.json -> runs/jev-koi.json). Resolve it properly.
    out_case = json.loads((HERE / "inputs" / f"{case}.json").read_text())["_meta"]["case"]
    src = RUNS / f"jev-{out_case}.json"
    if src.exists():
        shutil.copy(src, REPEATS / f"{case}-canonical.json")
    got = []
    for i in range(n):
        r = subprocess.run([sys.executable, "run_jev.py", f"inputs/{case}.json"],
                           cwd=HERE, capture_output=True, text=True)
        d = RUNS / f"jev-{out_case}.json"
        if r.returncode != 0 or not d.exists():
            print(f"  {case} rep{i+1}: FAILED exit {r.returncode}")
            continue
        shutil.copy(d, REPEATS / f"{case}-rep{i+1}.json")
        got.append(json.loads(d.read_text()))
    results[case] = got
    print(f"  {case}: {len(got)}/{n} repeats recorded")

print()
print("=" * 100)
print("1. GONG CHA -- does the refusal REPRODUCE?")
print("=" * 100)
g = results.get("P5-gongcha", [])
print("  %-6s %-9s %-11s %-7s %-8s %s" %
      ("rep", "defensib", "mental_adv", "gates", "composite", "band"))
print("  " + "-" * 76)
for i, d in enumerate(g, 1):
    dims = d["dimensions_display_1to5"]
    print("  %-6d %-9s %-11s %-7s %-8s %s" %
          (i, dims.get("defensibility"), dims.get("mental_advantage"),
           ",".join(d.get("gates_firing") or []) or "-",
           d.get("composite"), d.get("band")))
gated = sum(1 for d in g if d.get("band") == "GATE")
print()
print("  refused %d of %d repeats" % (gated, len(g)))
if g:
    df = [d["dimensions_display_1to5"].get("defensibility") for d in g]
    print("  defensibility values: %s  (gate floor = 2)" % df)
    print("  -> %s" % ("STABLE -- the refusal is a property of the case, not noise"
                       if gated == len(g) else
                       "UNSTABLE -- the headline result is a coin toss and must be "
                       "reported as such"))

print()
print("=" * 100)
print("2. COMPOSITE / DIMENSION NOISE  (sigma) -- this gates every other decision")
print("=" * 100)
print("  %-14s %-8s %-22s %-22s" % ("case", "n", "composite values", "composite sd"))
print("  " + "-" * 76)
allcomp = []
for case, got in results.items():
    if case == "P5-gongcha":
        continue
    comps = [d.get("composite") for d in got if d.get("composite") is not None]
    if len(comps) < 2:
        continue
    sd = statistics.stdev(comps)
    allcomp.extend(comps)
    print("  %-14s %-8d %-22s %.2f" % (case, len(comps), comps, sd))

print()
print("  per-dimension spread (display points across repeats):")
for case, got in results.items():
    if case == "P5-gongcha" or len(got) < 2:
        continue
    print("    %s" % case)
    for dim in DIMS:
        vals = [d["dimensions_display_1to5"].get(dim) for d in got]
        vals = [v for v in vals if v is not None]
        if len(vals) < 2:
            print("      %-18s %s (single value)" % (dim, vals))
            continue
        rng = max(vals) - min(vals)
        print("      %-18s %-16s range %d %s" %
              (dim, vals, rng, "<-- MOVES" if rng else "stable"))

print()
print("=" * 100)
print("3. IMPLICATION FOR THE 1-POINT BAND BOUNDARIES")
print("=" * 100)
if allcomp:
    sd = statistics.stdev(allcomp) if len(allcomp) > 1 else 0.0
    print("  pooled composite sd = %.2f points" % sd)
    print("  band boundaries are 1-point steps (37|38, 57|58, 76|77)")
    if sd >= 1.0:
        print("  -> NOISE >= THE STEP SIZE. Near-boundary cases are coin flips and the")
        print("     band WORD is not reproducible for them. Boundaries need intervals,")
        print("     not cliffs.")
    else:
        print("  -> noise below the step size; boundaries can discriminate, though")
        print("     cases within ~1 sd of a boundary remain unreliable.")
else:
    print("  insufficient repeats to estimate")
json.dump({k: [d.get("composite") for d in v] for k, v in results.items()},
          open(RUNS / "repeat_runs.json", "w"), indent=2)
print()
print("  raw repeats -> repeats/")
