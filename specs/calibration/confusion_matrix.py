"""CONFUSION MATRIX PER DIMENSION -- which level transitions are broken?

Three prose fixes failed because they targeted the wrong thing. Before re-anchoring all five ladders,
measure WHERE the instrument disagrees with Sean, level by level, from the fresh 120 runs.

For each dimension:
  * a confusion matrix (his level -> instrument level)
  * the DIRECTION of the error at each of his levels (compress-toward-middle?)
  * the specific transitions that break

This tells us whether the ladder needs to be SPREAD (model too peaked) or SHIFTED (anchors wrong),
and which levels are mis-described.
"""
import glob, json, csv, statistics as st
from collections import Counter, defaultdict

BASE = "/Users/seanfzc/projects/observeco-main/specs/calibration"

human = {}
for r in csv.DictReader(open(f"{BASE}/sean-regrade-raw.csv")):
    cid = (r.get("case_id") or "").strip().lower()
    if cid:
        human[cid] = r


def num(x):
    try:
        return float(x)
    except Exception:
        return None


fresh = {}
for p in glob.glob(f"{BASE}/runs-par/jev-*.json"):
    d = json.load(open(p))
    c = d.get("case") or (d.get("_meta") or {}).get("case")
    if c:
        fresh[c.lower()] = d.get("dimensions_display_1to5") or {}

SPECS = [("position_strength", "YOUR_RS", 5), ("mental_advantage", "YOUR_MA", 5),
         ("defensibility", "YOUR_DEF", 6), ("competitive_room", "YOUR_CR", 5),
         ("demand_reach", "YOUR_DR", 5)]

for dim, ycol, N in SPECS:
    pairs = []
    for case, h in human.items():
        y = num(h.get(ycol))
        m = (fresh.get(case) or {}).get(dim)
        if y is not None and isinstance(m, (int, float)):
            pairs.append((int(round(y)), int(round(m))))
    if len(pairs) < 10:
        print("\n%s -- insufficient (n=%d)" % (dim, len(pairs)))
        continue
    print("\n" + "=" * 92)
    print("%s   n=%d   exact %.0f%%   mean err %+.2f"
          % (dim, len(pairs),
             100 * sum(1 for y, m in pairs if y == m) / len(pairs),
             st.mean(m - y for y, m in pairs)))
    print("=" * 92)
    levels = sorted({y for y, _ in pairs})
    print("   his level |   n | instrument distribution (level:count)      | mean inst | pull")
    for lv in levels:
        got = [m for y, m in pairs if y == lv]
        dist = Counter(got)
        show = " ".join("%d:%d" % (k, dist[k]) for k in sorted(dist))
        mean_m = st.mean(got)
        pull = mean_m - lv
        arrow = "UP" if pull > 0.25 else ("DOWN" if pull < -0.25 else "ok")
        print("   %9d | %3d | %-42s | %9.2f | %+0.2f %s" % (lv, len(got), show, mean_m, pull, arrow))
    # the extremes
    lo = [m - y for y, m in pairs if y <= 2]
    hi = [m - y for y, m in pairs if y >= 4]
    print("   at his LOW levels (1-2): mean pull %+.2f (n=%d)" % (st.mean(lo), len(lo)) if lo else "", end="")
    print("   |  at his HIGH levels (4+): mean pull %+.2f (n=%d)" % (st.mean(hi), len(hi)) if hi else "")
