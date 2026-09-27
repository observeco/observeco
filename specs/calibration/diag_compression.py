"""TWO things before deciding: (1) which dimension carries the +13 compression on the
target segment, (2) whether the target-segment counts are inflated by TEMPLATE REPLICATES.

(2) matters because a corpus of near-identical synthetic profiles makes "26 of 34" look like
26 independent errors when it may be a handful of distinct profiles repeated. That is the
same defect class as the duplicate entries Sean flagged earlier, and it would change how much
confidence the numbers deserve.

(1) matters because a compression that lives in ONE dimension is fixable; one spread evenly
across five is a calibration re-map.
"""
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
V = json.loads((HERE / "rubric-v1.8.0.json").read_text())
W = V["_meta"]["weights"]
BAND_LIST = V["_meta"]["bands"]
ABBR = {"relative_strength": "RS", "mental_advantage": "MA", "defensibility": "DEF",
        "competitive_room": "CR", "market_headroom": "MH", "demand_reach": "DR"}
COUNTS = {d: len(V["questions"][d]["levels"]) for d in W}

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
    return BAND_LIST[0][0] if s < BAND_LIST[0][1] else BAND_LIST[-1][0]


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
    disp = run.get("dimensions_display_1to5") or {}
    un = set(run.get("dimensions_unscored") or [])
    r = by.get(e["name"]) or {}
    his = {d: num(r.get("YOUR_" + ABBR[d])) for d in W}
    hc = comp(his)
    if run.get("composite") is None or hc is None:
        continue
    recs.append({"cid": cid, "name": e["name"], "cat": e["cat"],
                 "mine": run.get("composite"), "his": hc,
                 "mb": band_of(run.get("composite")), "hb": band_of(hc),
                 "mdims": {d: (None if d in un else disp.get(d)) for d in W},
                 "hdims": his})

TARGET = [r for r in recs if r["hb"] in (BAND_LIST[0][0], BAND_LIST[1][0])]
print("=" * 92)
print("1. TEMPLATE REPLICATION in the target segment")
print("=" * 92)
print()
sig = Counter()
for r in TARGET:
    key = (r["cat"], tuple(sorted((d, r["mdims"][d]) for d in W
                                  if r["mdims"][d] is not None)),
           round(r["mine"], 1))
    sig[key] += 1
print("  target-segment cases:            %d" % len(TARGET))
print("  DISTINCT profiles (cat+dims+comp): %d" % len(sig))
print()
print("  profiles appearing more than once:")
for key, n in sorted(sig.items(), key=lambda kv: -kv[1])[:10]:
    if n > 1:
        print("    %2dx  cat=%-14s composite=%.0f" % (n, key[0], key[2]))
print()
eff = len(sig)
print("  >>> EFFECTIVE independent n is about %d, not %d." % (eff, len(TARGET)))
print("      Counts like '26 of 34' overstate the evidence by the replication factor.")
print()

print("=" * 92)
print("2. WHICH DIMENSION CARRIES THE COMPRESSION on the target segment?")
print("=" * 92)
print()
print("  %-6s %5s %8s %8s %9s %10s" % ("dim", "n", "his", "mine", "raw gap", "as pts"))
print("  " + "-" * 60)
tot_pts = 0.0
for d in W:
    pairs = []
    for r in TARGET:
        m, h = r["mdims"][d], r["hdims"][d]
        if m is not None and h is not None:
            pairs.append((m, h))
    if not pairs:
        continue
    mg = sum(a for a, _ in pairs) / len(pairs)
    hg = sum(b for _, b in pairs) / len(pairs)
    gap = hg - mg
    pts = W[d] * gap / (COUNTS[d] - 1)
    tot_pts += pts
    print("  %-6s %5d %8.2f %8.2f %+9.2f %+10.2f"
          % (ABBR[d], len(pairs), mg, hg, gap, pts))
print("  " + "-" * 60)
print("  %-6s %5s %8s %8s %9s %+10.1f" % ("TOTAL", "", "", "", "", tot_pts))
print()
print("  (as-pts = contribution to the composite gap, so the sum should approach the")
print("   observed target-segment gap)")
print()
obs = sum(r["mine"] - r["his"] for r in TARGET) / len(TARGET)
print("  observed mean composite gap on target segment: %+.1f points" % obs)
print()
print("  THE COMPRESSION IS %s" % (
    "CONCENTRATED in one dimension" if max(
        abs(W[d] * (sum(b for _, b in [(r['mdims'][d], r['hdims'][d]) for r in TARGET
                                       if r['mdims'][d] is not None and r['hdims'][d] is not None]) /
                    max(1, len([r for r in TARGET if r['mdims'][d] is not None
                                and r['hdims'][d] is not None])) -
                    sum(a for a, _ in [(r['mdims'][d], r['hdims'][d]) for r in TARGET
                                       if r['mdims'][d] is not None and r['hdims'][d] is not None]) /
                    max(1, len([r for r in TARGET if r['mdims'][d] is not None
                                and r['hdims'][d] is not None]))) / (COUNTS[d] - 1))
        for d in W) > 0.6 * abs(tot_pts) else "SPREAD across dimensions"))
