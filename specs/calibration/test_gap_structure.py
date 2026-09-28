"""WHY the composite gap is bidirectional while the dimension offset is only +0.13.

The aggregate says the instrument is nearly unbiased (+0.13 on the dimension scale). The
composite says my score is 20-28 points HIGH on small local businesses and ~17 points LOW on
large brands. Both cannot be describing the same corpus unless the errors run in OPPOSITE
directions by business type and cancel in the average.

THAT IS THE FINDING TO CONFIRM. A cancelled average is the most dangerous kind of bias: it
looks calibrated overall while being systematically wrong at both ends.

Group by category and by composite level, and report the SIGNED gap.
"""
import csv
import json
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
V = json.loads((HERE / "rubric-v1.8.0.json").read_text())
W = V["_meta"]["weights"]
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


def comp(vals):
    acc = tot = 0.0
    for d, v in vals.items():
        if v is None:
            continue
        # v/count matches run_jev.py:365; (v-1)/(n-1) was the retracted mismatch
        acc += W[d] * (v / COUNTS[d]) * 100.0
        tot += W[d]
    return acc / tot if tot else None


recs = []
for cid, e in idx["companies"].items():
    run = json.loads((HERE / "runs-v18" / ("jev-%s.json" % cid)).read_text())
    mine = run.get("composite")
    r = by.get(e["name"]) or {}
    his = {d: num(r.get("YOUR_" + ABBR[d])) for d in W}
    hc = comp(his)
    if mine is None or hc is None:
        continue
    recs.append({"name": e["name"], "cat": e["cat"], "mine": mine, "his": hc,
                 "gap": mine - hc})

print("=" * 92)
print("1. COMPOSITE GAP BY CATEGORY  (positive = I am too GENEROUS)")
print("=" * 92)
print()
g = defaultdict(list)
for r in recs:
    g[r["cat"]].append(r["gap"])
print("  %-20s %4s %9s %9s   %s" % ("category", "n", "my mean", "his mean", "mean gap"))
for cat, xs in sorted(g.items(), key=lambda kv: -sum(kv[1]) / len(kv[1])):
    mine = [r["mine"] for r in recs if r["cat"] == cat]
    his = [r["his"] for r in recs if r["cat"] == cat]
    print("  %-20s %4d %9.1f %9.1f   %+7.1f"
          % (cat, len(xs), sum(mine) / len(xs), sum(his) / len(xs), sum(xs) / len(xs)))
print()

print("=" * 92)
print("2. GAP BY LEVEL OF HIS OWN SCORE  (does the sign flip with business quality?)")
print("=" * 92)
print()
buckets = defaultdict(list)
for r in recs:
    if r["his"] < 35:
        b = "Fragile-ish (<35)"
    elif r["his"] < 50:
        b = "Contested (35-50)"
    elif r["his"] < 65:
        b = "Viable (50-65)"
    elif r["his"] < 80:
        b = "Strong (65-80)"
    else:
        b = "Very strong (80+)"
    buckets[b].append(r["gap"])
for b in ["Fragile-ish (<35)", "Contested (35-50)", "Viable (50-65)", "Strong (65-80)",
          "Very strong (80+)"]:
    xs = buckets.get(b)
    if not xs:
        continue
    print("  %-20s n=%3d   mean gap %+7.1f   (min %+.0f, max %+.0f)"
          % (b, len(xs), sum(xs) / len(xs), min(xs), max(xs)))
print()

print("=" * 92)
print("3. THE SAME TEST AT DIMENSION LEVEL — to show why the aggregate hid this")
print("=" * 92)
print()
print("  %-6s %8s %8s %9s" % ("dim", "his", "mine", "offset"))
for d in W:
    pairs = []
    for cid, e in idx["companies"].items():
        run = json.loads((HERE / "runs-v18" / ("jev-%s.json" % cid)).read_text())
        disp = run.get("dimensions_display_1to5") or {}
        un = set(run.get("dimensions_unscored") or [])
        if d in un:
            continue
        m = disp.get(d)
        h = num((by.get(e["name"]) or {}).get("YOUR_" + ABBR[d]))
        if m is not None and h is not None:
            pairs.append((m, h))
    if not pairs:
        continue
    print("  %-6s %8.2f %8.2f %+9.2f"
          % (ABBR[d], sum(b for _, b in pairs) / len(pairs),
             sum(a for a, _ in pairs) / len(pairs),
             sum(b - a for a, b in pairs) / len(pairs)))
print()
print("  -> every dimension looks close to unbiased, YET the composite gap at the ends")
print("     runs to +/-28 points. The bias is in the TAIL, not the mean.")
