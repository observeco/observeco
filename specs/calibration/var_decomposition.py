"""Variance decomposition per dimension: WITHIN-category vs BETWEEN-category.

THIS IS THE DECISIVE TEST for the reframe.

A dimension that measures a business's position RELATIVE TO ITS COMPETITORS must vary
WITHIN a product category -- that is where competitors live. A dimension that is a
property of the MARKET or CATEGORY (not the business) will be nearly constant inside a
category and vary only between categories.

So: fraction of total variance that is within-category.
  high  -> the dimension can distinguish rivals in the same landscape  (RELATIVE)
  low   -> the dimension describes the category, not the business      (STRUCTURAL)
"""
import glob
import json
import statistics
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
DIMS = ["mental_advantage", "defensibility", "competitive_room",
        "market_headroom", "demand_reach"]

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
                         dims={k: (None if k in uns else d.get(k)) for k in DIMS}))

cats = defaultdict(list)
for r in rows:
    cats[r["cat"]].append(r)

print("=" * 80)
print("VARIANCE DECOMPOSITION — can this dimension tell rivals apart?")
print("=" * 80)
print("within-category variance share = how much of a dimension's variation happens")
print("BETWEEN competitors in the same landscape. High = relative. Low = structural.")
print()

for k in DIMS:
    # grand mean
    allv = [r["dims"][k] for r in rows if r["dims"][k] is not None]
    if len(allv) < 5:
        print("%-18s  (too few scored)" % k)
        continue
    gm = statistics.mean(allv)
    ss_total = sum((v - gm) ** 2 for v in allv)
    ss_within = 0.0
    for c, grp in cats.items():
        vs = [r["dims"][k] for r in grp if r["dims"][k] is not None]
        if len(vs) < 2:
            continue
        cm = statistics.mean(vs)
        ss_within += sum((v - cm) ** 2 for v in vs)
    share = ss_within / ss_total if ss_total else 0
    # mean within-category sd, and how many categories are perfectly constant
    sds = []
    const = 0
    ncat = 0
    for c, grp in cats.items():
        vs = [r["dims"][k] for r in grp if r["dims"][k] is not None]
        if len(vs) < 2:
            continue
        ncat += 1
        sd = statistics.stdev(vs)
        sds.append(sd)
        if sd == 0:
            const += 1
    print("%-18s within-share %5.1f%%   mean within-cat sd %.2f   "
          "constant categories %d/%d" % (k, share * 100,
                                         statistics.mean(sds) if sds else 0,
                                         const, ncat))
print()
print("=" * 80)
print("READING")
print("=" * 80)
print("competitive_room's within-share is the one to watch: if it is near zero it is a")
print("property of the CATEGORY, not of the business, and cannot express relative strength")
print("no matter how it is weighted.")
print()
print("=== per-category competitive_room, to show it directly ===")
for c in sorted(cats):
    vs = [r["dims"]["competitive_room"] for r in cats[c]
          if r["dims"]["competitive_room"] is not None]
    if vs:
        print("   %-16s CR: %s" % (c, vs))
