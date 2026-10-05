"""DOES THE "CEILING" FINDING SURVIVE A FRESH RUN?

6.7.20 claimed: the instrument has almost no top anchor (competitive_room top level never awarded,
demand_reach top 3 vs his 22), and the gap grows with level.

That was computed from the ASSISTANT grade columns stored in sean-regrade-raw.csv (my_new_*).
6.7.21 showed those columns are NOT a live instrument run. So recompute the SAME analysis from the
FRESH runs on disk (runs-par/jev-*.json, 120 cases, same model) and compare.

If the ceiling pattern holds on fresh runs, 6.7.20 stands. If it vanishes, 6.7.20 is an artefact.
"""
import glob, json, csv, os, statistics as st
from collections import Counter, defaultdict

BASE = "/Users/seanfzc/projects/observeco-main/specs/calibration"

human = {}
for r in csv.DictReader(open(f"{BASE}/sean-regrade-raw.csv")):
    human[(r.get("case_id") or "").strip().lower()] = r


def num(x):
    try:
        return float(x)
    except Exception:
        return None


# fresh instrument output
fresh = {}
for p in glob.glob(f"{BASE}/runs-par/jev-*.json"):
    d = json.load(open(p))
    case = d.get("case") or (d.get("_meta") or {}).get("case")
    if case:
        fresh[case.lower()] = d.get("dimensions_display_1to5") or {}

# stored assistant columns from the CSV (what 6.7.20 used)
COLS = {"position_strength": ("YOUR_RS", "my_new_RS", 5),
        "mental_advantage":  ("YOUR_MA", "my_new_MA", 5),
        "defensibility":     ("YOUR_DEF", "my_new_DEF", 6),
        "competitive_room":  ("YOUR_CR", "my_new_CR", 4),
        "demand_reach":      ("YOUR_DR", "my_new_DR", 5)}

print("=" * 100)
print("FRESH RUN vs THE STORED CSV COLUMNS — same dimension, same cases")
print("=" * 100)
print("   %-20s %10s %10s %10s %10s" % ("dimension", "CSV mean", "FRESH mean", "his mean", "CSV->FRESH"))
for dim, (ycol, mcol, top) in COLS.items():
    csvs, frs, his = [], [], []
    for case, h in human.items():
        y = num(h.get(ycol))
        if y is not None:
            his.append(y)
            c = num(h.get(mcol))
            if c is not None:
                csvs.append(c)
            f = (fresh.get(case) or {}).get(dim)
            if isinstance(f, (int, float)):
                frs.append(f)
    if not frs:
        print("   %-20s  (no fresh data)" % dim)
        continue
    print("   %-20s %10.2f %10.2f %10.2f %+10.2f"
          % (dim, st.mean(csvs), st.mean(frs), st.mean(his), st.mean(frs) - st.mean(csvs)))

print()
print("=" * 100)
print("DOES THE CEILING SURVIVE? top-level AWARD COUNTS, on FRESH runs")
print("=" * 100)
for dim, (ycol, mcol, top) in COLS.items():
    hy, fc, cc = 0, 0, 0
    for case, h in human.items():
        y = num(h.get(ycol))
        f = (fresh.get(case) or {}).get(dim)
        c = num(h.get(mcol))
        if y is not None and y >= top:
            hy += 1
        if isinstance(f, (int, float)) and f >= top:
            fc += 1
        if c is not None and c >= top:
            cc += 1
    print("   %-20s top level %d :  SEAN %3d | CSV cols %3d | FRESH RUN %3d"
          % (dim, top, hy, cc, fc))

print()
print("=" * 100)
print("AND THE GAP-BY-LEVEL TEST, on FRESH runs (does it still grow with his level?)")
print("=" * 100)
for dim, (ycol, mcol, top) in COLS.items():
    by = defaultdict(list)
    for case, h in human.items():
        y = num(h.get(ycol))
        f = (fresh.get(case) or {}).get(dim)
        if y is not None and isinstance(f, (int, float)):
            by[int(round(y))].append(y - f)
    if not by:
        continue
    parts = ["L%d %+.2f(n=%d)" % (lv, st.mean(by[lv]), len(by[lv]))
             for lv in sorted(by) if len(by[lv]) >= 3]
    slope = "?"
    ks = [lv for lv in sorted(by) if len(by[lv]) >= 3]
    if len(ks) >= 2:
        slope = "RISING" if st.mean(by[ks[-1]]) > st.mean(by[ks[0]]) + 0.2 else "flat/falling"
    print("   %-20s %s  -> %s" % (dim, "  ".join(parts), slope))
