"""Audit the calibration state: score compression, demand_reach behaviour, and
confidence spread across every run so far.

Purpose: replace impressions with numbers before deciding what needs work.
"""
from __future__ import annotations

import glob
import json
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
DIMS = ["market_headroom", "competitive_room", "position_availability",
        "defensibility", "demand_reach"]

runs = []
for f in sorted(glob.glob(str(HERE / "runs" / "jev-*.json"))):
    runs.append(json.loads(Path(f).read_text()))

print(f"runs: {len(runs)}  ({', '.join(r['case'] for r in runs)})")
print()

# --- score compression -------------------------------------------------------
print("SCORE DISTRIBUTION (all dimensions, all runs)")
print("-" * 58)
all_scores = []
for r in runs:
    all_scores += list(r["dimensions_display_1to5"].values())
c = Counter(all_scores)
for level in (1, 2, 3, 4, 5):
    n = c.get(level, 0)
    print(f"  score {level}: {n:3}  {'#' * n}")
print(f"  total {len(all_scores)} measurements")
print(f"  range used: {min(all_scores)}-{max(all_scores)}  (scale is 1-5)")
spread = len(set(all_scores))
print(f"  distinct levels used: {spread}/5")
print()

# --- per-dimension -----------------------------------------------------------
print("PER-DIMENSION SCORE + CONFIDENCE")
print("-" * 58)
print(f"  {'dimension':24}{'scores':>16}{'mean conf':>11}{'min conf':>10}")
for d in DIMS:
    sc = [r["dimensions_display_1to5"][d] for r in runs]
    cf = [r["confidence"][d] for r in runs]
    print(f"  {d:24}{str(sc):>16}{sum(cf)/len(cf):>11.2f}{min(cf):>10.2f}")
print()

# --- demand_reach specifically ----------------------------------------------
print("DEMAND_REACH — the dimension flagged low twice")
print("-" * 58)
for r in runs:
    print(f"  {r['case']:12} score {r['dimensions_display_1to5']['demand_reach']}/5"
          f"   conf {r['confidence']['demand_reach']:.2f}")
dr_conf = [r["confidence"]["demand_reach"] for r in runs]
other = [r["confidence"][d] for r in runs for d in DIMS if d != "demand_reach"]
print(f"  mean conf demand_reach: {sum(dr_conf)/len(dr_conf):.2f}"
      f"   vs other dims: {sum(other)/len(other):.2f}")
print()

# --- confidence vs score -----------------------------------------------------
print("CONFIDENCE BAND vs SCORE (is low conf attached to mid-range scores?)")
print("-" * 58)
low = [(r["case"], d, r["dimensions_display_1to5"][d])
       for r in runs for d in DIMS if r["confidence"][d] < 0.50]
high = [(r["case"], d, r["dimensions_display_1to5"][d])
        for r in runs for d in DIMS if r["confidence"][d] >= 0.70]
print(f"  below 0.50 confidence (n={len(low)}): "
      f"scores {sorted(s for _,_,s in low)}")
print(f"  at/above 0.70 confidence (n={len(high)}): "
      f"scores {sorted(s for _,_,s in high)}")
print()

# --- gates ------------------------------------------------------------------
print("GATE EVENTS")
print("-" * 58)
for r in runs:
    if r["gates_firing"]:
        print(f"  {r['case']}: FIRING {r['gates_firing']} -> band {r['band']}")
print(f"  gates fired in {sum(1 for r in runs if r['gates_firing'])}/{len(runs)} runs")
print()

# --- what is NOT evidenced ---------------------------------------------------
print("COVERAGE OF THE WORK TO DATE")
print("-" * 58)
print(f"  analyses mapped to tiers ............ 6")
print(f"  derivations executed by hand ........ 1  (bubble tea)")
print(f"  cases scored with a derived set ..... 1  (bubble tea)")
print(f"  cases scored WITHOUT one ............ 2  (bonefirm, observeco)")
print(f"  real prospect submissions ever run .. 0")
print(f"  independently-labelled calibration .. 0  (all labels written by the scorer)")
