"""Compose a landscape-level diagnosis: quantisation, dropped dims, and the
within-category orderings that matter most.
"""
import glob
import json
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent

sc = Counter()
dims = Counter()
for p in glob.glob(str(HERE / "runs" / "jev-*.json")):
    r = json.loads(Path(p).read_text())
    c = r.get("composite")
    if c is not None:
        sc[c] += 1
    for u in (r.get("dimensions_unscored") or []):
        dims[u] += 1

print("=== COMPOSITE QUANTISATION ===")
print("distinct composite values across %d scored cases: %d" % (sum(sc.values()), len(sc)))
for v, n in sc.most_common(10):
    print("   %3d  x%d" % (v, n))
print()
print("cases sharing their composite with >=3 others: %d of %d"
      % (sum(n for v, n in sc.items() if n >= 3), sum(sc.values())))
print()
print("=== which dimensions get dropped (A3 / coverage) ===")
for k, n in dims.most_common():
    print("   %-18s %d" % (k, n))
print()

print("=== the five within-category orderings I most distrust ===")
groups = {
    "fast-food": ["FF01", "FF02", "FF03", "FF05", "FF06", "FF04"],
    "furniture": ["FU01", "FU02", "FU03", "FU04"],
    "electronics": ["EL01", "EL02", "EL03", "EL04"],
    "gym": ["GY01", "GY02", "GY03", "GY04", "GY05", "GY06", "GY07"],
    "bubble-tea": ["BT01", "BT02", "BT03", "BT04", "BT05", "BT06", "BT07", "BT08",
                   "BT09", "BT10"],
}
for g, ids in groups.items():
    print()
    print("--- %s ---" % g)
    for cid in ids:
        cand = glob.glob(str(HERE / "runs" / ("jev-%s*.json" % cid)))
        if not cand:
            print("   %-8s (no run)" % cid)
            continue
        r = json.loads(Path(cand[0]).read_text())
        d = r.get("dimensions_display_1to5") or {}
        uns = r.get("dimensions_unscored") or []
        print("   %-8s score=%-4s  MA=%s DEF=%s CR=%s MH=%s DR=%s  dropped=%s" % (
            cid, r.get("composite"),
            d.get("mental_advantage"), d.get("defensibility"),
            d.get("competitive_room"),
            "n/a" if "market_headroom" in uns else d.get("market_headroom"),
            d.get("demand_reach"),
            ",".join(uns) or "-"))
