"""WHERE DOES THE LEVEL SHIFT SIT? Is the instrument COMPRESSING toward the middle while Sean
spreads across the scale, or is it uniformly one level low?

The finding notes say: "a level shift means specific level WORDING is anchored differently and should
be re-worded, not rescaled" -- and that his sd and mine are nearly equal. Test that claim properly:
a near-equal sd with a +0.3 mean shift is a PURE SHIFT. But if the shift is larger at the top of the
scale (famous businesses), it is an ANCHOR problem at specific levels, which is a different fix.

Runs on the 120-case regrade, per dimension, per level.
"""
import csv, statistics as st
from collections import Counter, defaultdict

R = "/Users/seanfzc/projects/observeco-main/specs/calibration"
rows = list(csv.DictReader(open(f"{R}/sean-regrade-raw.csv")))


def num(x):
    try:
        return float(x)
    except Exception:
        return None


PAIRS = [("position_strength", "YOUR_RS", "my_new_RS"),
         ("mental_advantage",  "YOUR_MA", "my_new_MA"),
         ("defensibility",     "YOUR_DEF", "my_new_DEF"),
         ("competitive_room",  "YOUR_CR", "my_new_CR"),
         ("demand_reach",      "YOUR_DR", "my_new_DR")]

print("=" * 100)
print("A. SPREAD vs SHIFT — is his sd really close to the instrument's?")
print("=" * 100)
print("   %-20s %6s %8s %8s %9s %9s" % ("dimension", "n", "his sd", "inst sd", "sd ratio", "mean diff"))
for label, yc, mc in PAIRS:
    ys, ms = [], []
    for r in rows:
        y, m = num(r.get(yc)), num(r.get(mc))
        if y is not None and m is not None:
            ys.append(y); ms.append(m)
    if len(ys) < 3:
        continue
    sy, sm = st.stdev(ys), st.stdev(ms)
    print("   %-20s %6d %8.2f %8.2f %9.2f %+9.2f"
          % (label, len(ys), sy, sm, sy / sm, st.mean(ys) - st.mean(ms)))

print()
print("=" * 100)
print("B. WHERE THE MASS SITS — the level distribution, his vs the instrument")
print("=" * 100)
for label, yc, mc in PAIRS:
    yc_cnt, mc_cnt = Counter(), Counter()
    for r in rows:
        y, m = num(r.get(yc)), num(r.get(mc))
        if y is not None:
            yc_cnt[int(round(y))] += 1
        if m is not None:
            mc_cnt[int(round(m))] += 1
    levels = sorted(set(yc_cnt) | set(mc_cnt))
    print("\n   %s" % label)
    print("      level   %8s %8s" % ("YOU", "INSTR"))
    for lv in levels:
        yn, mn = yc_cnt.get(lv, 0), mc_cnt.get(lv, 0)
        bar_y = "#" * int(yn / 4)
        bar_m = "#" * int(mn / 4)
        print("        %-5d  %4d %-22s %4d %s" % (lv, yn, bar_y, mn, bar_m))

print()
print("=" * 100)
print("C. THE DECISIVE TEST — is the gap bigger at the TOP of the scale?")
print("=" * 100)
print("   (if the shift is uniform, it is a pure level shift; if it grows with level, it is an")
print("    ANCHOR problem at the top -- different fix entirely)")
for label, yc, mc in PAIRS:
    by_level = defaultdict(list)
    for r in rows:
        y, m = num(r.get(yc)), num(r.get(mc))
        if y is not None and m is not None:
            by_level[int(round(y))].append(y - m)
    if not by_level:
        continue
    print("\n   %s" % label)
    print("      your level  n    mean gap (yours - instrument)")
    for lv in sorted(by_level):
        g = by_level[lv]
        if len(g) >= 3:
            print("        %-11d %-4d %+.2f" % (lv, len(g), st.mean(g)))
