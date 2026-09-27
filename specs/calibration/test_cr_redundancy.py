"""Does competitive_room contribute ANYTHING to ranking competitors in one landscape?

Mathematical claim under test: if a dimension is constant within a category, it cannot
change the ORDER of that category's members -- it shifts all of them equally. So the
within-landscape ranking is produced ONLY by the dimensions that vary within it.

This computes, per category, the rank correlation between:
  - the full 5-dimension composite
  - the 3 dimensions that actually vary within the category (MA, DEF, DR)
If they agree everywhere, then 20% of the declared weight is decorative.
"""
import glob
import json
import statistics
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
DIMS = ["mental_advantage", "defensibility", "competitive_room",
        "market_headroom", "demand_reach"]
W = json.loads((HERE / "rubric.json").read_text())["_meta"]["weights"]

rows = []
for dirn in ("inputs-v2", "inputs-v3"):
    idx = json.loads((HERE / dirn / "_index.json").read_text())
    for cid in idx["companies"]:
        meta = json.loads((HERE / dirn / (cid + ".json")).read_text())["_meta"]
        p = HERE / "runs" / ("jev-%s.json" % meta["case"])
        if not p.exists():
            continue
        run = json.loads(p.read_text())
        d = run.get("dimensions_display_1to5") or {}
        uns = set(run.get("dimensions_unscored") or [])
        rows.append(dict(cat=idx["companies"][cid]["cat"], cid=cid,
                         name=idx["companies"][cid]["name"],
                         comp=run.get("composite"),
                         dims={k: (None if k in uns else d.get(k)) for k in DIMS}))
cats = defaultdict(list)
for r in rows:
    cats[r["cat"]].append(r)


def renorm_position(r):
    """composite using ONLY the dimensions that vary within a landscape (drop CR)."""
    num = den = 0.0
    for k in ("mental_advantage", "defensibility", "demand_reach"):
        v = r["dims"][k]
        if v is None:
            continue
        num += v * W[k]
        den += W[k]
    return (num / den) * 20 if den else None


def spearman(a, b):
    n = len(a)
    if n < 2:
        return None
    ra = {v: i for i, v in enumerate(sorted(a))}
    rb = {v: i for i, v in enumerate(sorted(b))}
    d2 = sum((ra[x] - rb[y]) ** 2 for x, y in zip(a, b))
    return 1 - (6 * d2) / (n * (n * n - 1))


print("=" * 80)
print("DOES competitive_room (20% weight) CHANGE THE ORDER IN A LANDSCAPE?")
print("=" * 80)
print()
agree = 0
total = 0
for c in sorted(cats):
    grp = [r for r in cats[c] if r["comp"] is not None and renorm_position(r) is not None]
    if len(grp) < 3:
        continue
    total += 1
    full = [r["comp"] for r in grp]
    pos = [renorm_position(r) for r in grp]
    rho = spearman(full, pos)
    same = "IDENTICAL" if rho == 1.0 else "differs"
    if rho == 1.0:
        agree += 1
    print("  %-16s n=%-3d rank-corr full vs position-only: %s  %s"
          % (c, len(grp), ("%.3f" % rho) if rho is not None else "n/a", same))
print()
print("categories where dropping competitive_room leaves the ORDER IDENTICAL: %d/%d"
      % (agree, total))
print()
print("=" * 80)
print("HOW MANY DISTINCT RANKS CAN THE COMPOSITE ACTUALLY PRODUCE IN A LANDSCAPE?")
print("=" * 80)
for c in sorted(cats):
    grp = [r for r in cats[c] if r["comp"] is not None]
    if len(grp) < 3:
        continue
    vals = [r["comp"] for r in grp]
    ties = len(vals) - len(set(vals))
    print("  %-16s n=%-3d distinct scores %-3d tied positions %d"
          % (c, len(grp), len(set(vals)), ties))
