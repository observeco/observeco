"""THE CLOSE CONDITION, measured on the TARGET SEGMENT.

D1: band agreement is the bar (>=90% within one band, <=5% two or more off).
D2: band + narrative, no number shown.
D3: the target market is WEAK-POSITIONING SMEs.

D3 is what makes this measurement necessary. My composite is compressed and the error is
LARGEST at the weak end (+13.0 for Fragile businesses). A +13 uplift on a business whose
true composite is 25 puts it at 38 -- which CROSSES the Fragile/Contested boundary at 37.
So the compression may be systematically promoting fragile businesses out of the fragile
band, in exactly the segment the product targets.

The overall 96.6% is not the number that matters. The number that matters is band agreement
WITHIN THE TARGET SEGMENT. Measure it separately.
"""
import csv
import json
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
V = json.loads((HERE / "rubric-v1.8.0.json").read_text())
W = V["_meta"]["weights"]
BAND_LIST = V["_meta"]["bands"]
ABBR = {"relative_strength": "RS", "mental_advantage": "MA", "defensibility": "DEF",
        "competitive_room": "CR", "market_headroom": "MH", "demand_reach": "DR"}
COUNTS = {d: len(V["questions"][d]["levels"]) for d in W}
ORDER = [b[0] for b in BAND_LIST]

idx = json.loads((HERE / "inputs-v4" / "_index.json").read_text())
rows = list(csv.DictReader(open(HERE / "sean-regrade-raw.csv")))
by = {r["company"]: r for r in rows}


def num(x):
    x = ("" if x is None else str(x)).strip()
    if x.lower() in ("n/a", "na", "", "-", "none", "nan"):
        return None
    try:
        return float(x)
    except Exception:
        return None


def band_of(s):
    for nm, lo, hi in BAND_LIST:
        if lo <= s <= hi:
            return nm
    # scores can fall outside the declared band ranges (the lowest band starts at 5).
    # Clamp to the nearest band rather than returning '?' -- an unbanded score would
    # silently drop cases from the agreement count.
    if s < min(b[1] for b in BAND_LIST):
        return min(BAND_LIST, key=lambda b: b[1])[0]
    return max(BAND_LIST, key=lambda b: b[2])[0]


def comp(vals):
    acc = tot = 0.0
    for d, v in vals.items():
        if v is None:
            continue
        acc += W[d] * ((v - 1) / (COUNTS[d] - 1)) * 100.0
        tot += W[d]
    return acc / tot if tot else None


recs = []
for cid, e in idx["companies"].items():
    if e["cat"] == "home-not-permitted":
        continue
    run = json.loads((HERE / "runs-v18" / ("jev-%s.json" % cid)).read_text())
    mine = run.get("composite")
    r = by.get(e["name"]) or {}
    his = {d: num(r.get("YOUR_" + ABBR[d])) for d in W}
    hc = comp(his)
    if mine is None or hc is None:
        continue
    recs.append({"name": e["name"], "cat": e["cat"], "mine": mine, "his": hc,
                 "mb": band_of(mine), "hb": band_of(hc)})

print("=" * 92)
print("BAND AGREEMENT ON THE TARGET SEGMENT (D3: weak-positioning SMEs)")
print("=" * 92)
print()


def report(label, subset):
    if not subset:
        return
    n = len(subset)
    same = sum(1 for r in subset if r["mb"] == r["hb"])
    adj = sum(1 for r in subset
              if r["mb"] != r["hb"]
              and abs(ORDER.index(r["mb"]) - ORDER.index(r["hb"])) == 1)
    far = n - same - adj
    print("  %-26s n=%3d   same %5.1f%%   within-1 %5.1f%%   TWO+ OFF %5.1f%% (%d)"
          % (label, n, 100 * same / n, 100 * (same + adj) / n, 100 * far / n, far))


report("ALL", recs)
print()
print("  BY HIS TRUE BAND (where he places the business):")
for b in ORDER:
    report("   " + b, [r for r in recs if r["hb"] == b])
print()
print("  TARGET SEGMENT (his band = Fragile or Contested):")
target = [r for r in recs if r["hb"] in (ORDER[0], ORDER[1])]
report("   weak-positioning", target)
print()

print("=" * 92)
print("THE PROMOTION PROBLEM — fragile businesses I place in a HIGHER band")
print("=" * 92)
print()
promoted = [r for r in recs
            if ORDER.index(r["mb"]) > ORDER.index(r["hb"])]
print("  businesses I place in a HIGHER band than he does: %d of %d"
      % (len(promoted), len(recs)))
by_pair = defaultdict(int)
for r in promoted:
    by_pair[(r["hb"], r["mb"])] += 1
for (hb, mb), n in sorted(by_pair.items(), key=lambda kv: -kv[1]):
    print("    %-20s -> %-20s  %d" % (hb, mb, n))
print()
print("  direction of ALL band errors:")
up = len(promoted)
down = sum(1 for r in recs if ORDER.index(r["mb"]) < ORDER.index(r["hb"]))
print("    I am MORE generous: %d" % up)
print("    I am HARSHER:       %d" % down)
print()
print("  THE BOUNDARY: Fragile ends at 37, Contested begins at 38.")
crossers = [r for r in recs if r["hb"] == ORDER[0] and r["mb"] != ORDER[0]]
print("  Fragile businesses I move OUT of Fragile: %d of %d"
      % (len(crossers), sum(1 for r in recs if r["hb"] == ORDER[0])))
for r in sorted(crossers, key=lambda x: x["his"])[:12]:
    print("    %-34s his %5.1f (%s)  mine %5.1f (%s)  gap %+.1f"
          % (r["name"][:33], r["his"], r["hb"], r["mine"], r["mb"], r["mine"] - r["his"]))
