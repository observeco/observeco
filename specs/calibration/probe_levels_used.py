"""Exact display-level usage per dimension. Headline claim: market_headroom uses
fewer display levels than any other dimension. Verify before asserting."""
import json, glob
from collections import Counter
BASE = "/Users/seanfzc/projects/observeco-main/specs/calibration"
rub = json.load(open(f"{BASE}/rubric.json"))
meta = rub["_meta"]
DIMS = list(meta["weights"])
counts = meta.get("level_counts") or {}

runs = [json.load(open(p)) for p in sorted(glob.glob(f"{BASE}/runs/jev-*.json"))]
runs = [d for d in runs if d.get("case")]

print("=" * 96)
print("DISPLAY-LEVEL USAGE PER DIMENSION  (n=%d cases)" % len(runs))
print("=" * 96)
for dim in DIMS:
    n = counts.get(dim, 5)
    c = Counter()
    for d in runs:
        v = d.get("dimensions_display_1to5", {}).get(dim)
        if v is not None:
            c[v] += 1
    used = sorted(c)
    unused = [i for i in range(1, n + 1) if i not in c]
    dist = "  ".join("%d:%d" % (k, c[k]) for k in used)
    print("  %-18s range 1-%d   used %d/%d levels" % (dim, n, len(used), n))
    print("  %-18s   distribution: %s" % ("", dist))
    print("  %-18s   NEVER USED : %s" % ("", unused if unused else "none"))
    print()

print("=" * 96)
print("RAW-VALUE SPREAD PER DIMENSION")
print("=" * 96)
for dim in DIMS:
    n = counts.get(dim, 5)
    vals = [d["raw_jev_scores_0to4"][dim] for d in runs
            if d.get("raw_jev_scores_0to4", {}).get(dim) is not None]
    if not vals:
        continue
    vals = sorted(float(v) for v in vals)
    span = vals[-1] - vals[0]
    # how much of the 0..n-1 range is actually traversed?
    print("  %-18s n=%-3d  raw %.2f - %.2f  span %.2f  of range 0-%d (%.0f%% of scale)"
          % (dim, len(vals), vals[0], vals[-1], span, n - 1, span / (n - 1) * 100))
