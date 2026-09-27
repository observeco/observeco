"""Which dimensions does a TYPICAL case actually show? And do any definitions overlap?

The confusion may be structural: if market_headroom is dropped in most cases, then the
instrument Sean reads does not match the instrument we describe. Measure it, then audit
each dimension's question for genuine overlap.
"""
import glob
import json
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
DIMS = ["mental_advantage", "defensibility", "competitive_room",
        "market_headroom", "demand_reach"]

shown = Counter()
combos = Counter()
n = 0
for p in glob.glob(str(HERE / "runs" / "jev-*.json")):
    r = json.loads(Path(p).read_text())
    d = r.get("dimensions_display_1to5") or {}
    uns = set(r.get("dimensions_unscored") or [])
    if not d:
        continue
    n += 1
    present = tuple(sorted(k for k in DIMS if k not in uns and d.get(k) is not None))
    combos[present] += 1
    for k in present:
        shown[k] += 1

print("=" * 78)
print("WHAT A TYPICAL CASE ACTUALLY SHOWS  (n=%d runs)" % n)
print("=" * 78)
for k in DIMS:
    print("  %-18s shown in %3d/%d  (%.0f%%)" % (k, shown[k], n, 100 * shown[k] / n))
print()
print("Most common combinations of dimensions actually present:")
for c, cnt in combos.most_common(6):
    print("  %3d cases: %s" % (cnt, " + ".join(x[:9] for x in c) or "(none)"))
print()

print("=" * 78)
print("DEFINITION OVERLAP AUDIT — what each dimension is measured AGAINST")
print("=" * 78)
r = json.loads((HERE / "rubric.json").read_text())
anchors = {
    "mental_advantage": "a business OF ITS SIZE (size expectation)",
    "defensibility": "a hypothetical rival trying to COPY it",
    "competitive_room": "the market's STRUCTURE (concentration, price floor)",
    "market_headroom": "the CATEGORY's demand vs supply",
    "demand_reach": "this business's OWN BUYERS",
}
print()
for k in DIMS:
    ins = " ".join(str(r["questions"][k].get("instructions", "")).split())
    print("%s" % k.upper())
    print("  measured against : %s" % anchors[k])
    print("  first sentence   : %s" % ins[:118])
    print()

print("=" * 78)
print("WHERE THE OVERLAP ACTUALLY BITES")
print("=" * 78)
print()
print("market_headroom vs demand_reach -- BOTH talk about demand and buyers:")
print("  MH: 'is there more DEMAND in this category than is being SERVED?'   -> the CATEGORY")
print("  DR: 'a reachable group of buyers who would pay, can THIS business find them?' -> the BUSINESS")
print("  Same words ('demand', 'buyers'), different subject. Confusable.")
print()
print("competitive_room vs market_headroom -- BOTH about the market:")
print("  CR: 'how much space does competition leave'      -> STRUCTURE (who else is there)")
print("  MH: 'is demand being served'                     -> SUPPLY vs DEMAND (are buyers stuck)")
print("  Both 'market' words, neither about the business.")
print()
print("mental_advantage is the odd one out: it is the only RELATIVE-to-size measure,")
print("so its '5' is unreachable for a big company unless rivals lag, and its '3' can")
print("mean a dominant brand simply performing as expected.")
