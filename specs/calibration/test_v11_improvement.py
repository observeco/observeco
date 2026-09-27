"""Did v1.1.0 close the level shift?  Before/after against Sean's regrade.

The revision targeted a specific defect: agreement was one-directional (52 cases where he
was >=2 above me, 0 the other way), with near-equal standard deviations, i.e. a LEVEL shift
not a spread difference. If the revised wording worked, the shift shrinks and exact
agreement rises. If it did not, the wording was not the problem.
"""
import csv
import json
import statistics
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
DIMS = ["RS", "MA", "DEF", "CR", "MH", "DR"]
SHORT = ["relative_strength", "mental_advantage", "defensibility",
         "competitive_room", "market_headroom", "demand_reach"]
FULL = dict(zip(DIMS, SHORT))
V10 = json.loads((HERE / "rubric-v1.0.0.json").read_text())["_meta"]["weights"]
V11 = json.loads((HERE / "rubric-v1.2.0.json").read_text())["_meta"]["weights"]

rows = list(csv.DictReader(open(HERE / "sean-regrade-raw.csv")))


def num(x):
    x = ("" if x is None else str(x)).strip()
    if x.lower() in ("n/a", "na", "", "-", "none", "nan"):
        return None
    try:
        return float(x)
    except Exception:
        return None


def load(d):
    out = {}
    for p in (HERE / d).glob("jev-*.json"):
        r = json.loads(p.read_text())
        dims = r.get("dimensions_display_1to5") or {}
        u = set(r.get("dimensions_unscored") or [])
        out[r.get("case")] = {"comp": r.get("composite"),
                              "dims": {k: (None if k in u else dims.get(k)) for k in SHORT}}
    return out


a = load("runs-v4")
b = load("runs-v12")
print("v1.0.0 runs: %d   v1.1.0 runs: %d" % (len(a), len(b)))

print()
print("=" * 84)
print("PER-DIMENSION: v1.0.0 (baseline) vs v1.2.0 (DEF wording only) against his grades")
print("=" * 84)
print()
print("  %-5s %-28s %-28s" % ("", "v1.0.0", "v1.2.0"))
print("  %-5s %6s %7s %7s %9s %6s %7s %7s %9s"
      % ("dim", "shift", "exact", ">=2", "my mu", "shift", "exact", ">=2", "my mu"))
for d in DIMS:
    line = ["  %-5s" % d]
    for src, tag in ((a, "old"), (b, "new")):
        hs, ms = [], []
        for r in rows:
            h = num(r.get("YOUR_" + d))
            run = src.get(r.get("case_id"))
            m = run["dims"].get(FULL[d]) if run else None
            if h is not None and m is not None:
                hs.append(h)
                ms.append(m)
        if not hs:
            line.append("%6s %7s %7s %9s" % ("-", "-", "-", "-"))
            continue
        ds = [h - m for h, m in zip(hs, ms)]
        line.append("%6.2f %6.0f%% %6.0f%% %9.2f"
                    % (statistics.mean(ds),
                       100 * sum(1 for x in ds if x == 0) / len(ds),
                       100 * sum(1 for x in ds if abs(x) >= 2) / len(ds),
                       statistics.mean(ms)))
    print(" ".join(line))
print()
print("  shift = mean( HIS - MINE ).  exact = identical.  >=2 = real disputes.")

print()
print("=" * 84)
print("DIRECTIONALITY — the diagnostic that identified the defect")
print("=" * 84)
print()
for src, tag in ((a, "v1.0.0"), (b, "v1.2.0")):
    above = below = 0
    for r in rows:
        for d in DIMS:
            h = num(r.get("YOUR_" + d))
            run = src.get(r.get("case_id"))
            m = run["dims"].get(FULL[d]) if run else None
            if h is None or m is None:
                continue
            if h - m >= 2:
                above += 1
            elif m - h >= 2:
                below += 1
    print("  %s : his >=2 ABOVE mine = %d   |   mine >=2 above his = %d"
          % (tag, above, below))

print()
print("=" * 84)
print("THE Q1 CASES SPECIFICALLY (DEF, the largest gap: 15 disagreements)")
print("=" * 84)
print()
print("  %-32s %6s %8s %8s" % ("company", "hisDEF", "my v1.0", "my v1.1"))
for cid in ("FF01-mcdonalds", "FF02-kfc", "SM01-ntuc", "HB04-sephora",
            "EL02-harvey", "HB03-unity", "EL03-best"):
    row = next((r for r in rows if r.get("case_id") == cid), None)
    if not row:
        continue
    h = num(row.get("YOUR_DEF"))
    m0 = (a.get(cid) or {}).get("dims", {}).get("defensibility")
    m1 = (b.get(cid) or {}).get("dims", {}).get("defensibility")
    print("  %-32s %6s %8s %8s" % (row["company"][:31], h, m0, m1))

print()
print("=" * 84)
print("COMPOSITE — his dims imply vs my score (v1.0.0 and v1.1.0)")
print("=" * 84)
print()
for src, w, tag in ((a, V10, "v1.0.0"), (b, V11, "v1.2.0")):
    ds = []
    for r in rows:
        run = src.get(r.get("case_id"))
        if not run or run["comp"] is None:
            continue
        n_ = den = 0.0
        for d in DIMS:
            v = num(r.get("YOUR_" + d))
            if v is None:
                continue
            n_ += v * w[FULL[d]]
            den += w[FULL[d]]
        if den:
            ds.append(19.1667 * (n_ / den) - run["comp"])
    if ds:
        print("  %s : mean(his implied - my score) %+.1f   mean|d| %.1f   n=%d"
              % (tag, statistics.mean(ds), statistics.mean(abs(x) for x in ds), len(ds)))

print()
print("=" * 84)
print("MH APPLICABILITY — unchanged? (he said n/a 106x)")
print("=" * 84)
print()
for src, tag in ((a, "v1.0.0"), (b, "v1.2.0")):
    both = onlyme = onlyhim = neither = 0
    for r in rows:
        run = src.get(r.get("case_id"))
        if not run:
            continue
        hn = str(r.get("YOUR_MH") or "").strip().lower() in ("n/a", "na")
        mn = run["dims"].get("market_headroom") is None
        if hn and mn:
            both += 1
        elif mn:
            onlyme += 1
        elif hn:
            onlyhim += 1
        else:
            neither += 1
    print("  %s : both n/a %d | I dropped only %d | he n/a only %d | both scored %d"
          % (tag, both, onlyme, onlyhim, neither))
