"""Quantify the one-directional disagreement, and check his holistic SCORE.

Three tests:
  1. Is it a LEVEL shift (uniform offset) or a SPREAD difference (he uses more of the
     scale)? These need different fixes: a level shift is recalibration; a spread
     difference means my level descriptions are anchored too tightly.
  2. Rank agreement within each category -- does the ORDER match even when the numbers
     do not? For a diagnostic, order is what matters most.
  3. His holistic YOUR_SCORE vs (a) his own dims and (b) my score. If his holistic score
     is closer to MINE than to his own dims, he applied a judgement his dimensions do not
     express -- worth knowing either way.
"""
import csv
import json
import statistics
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
SHORT = ["relative_strength", "mental_advantage", "defensibility",
         "competitive_room", "market_headroom", "demand_reach"]
DIMS = ["RS", "MA", "DEF", "CR", "MH", "DR"]
FULL = dict(zip(DIMS, SHORT))
W = json.loads((HERE / "rubric-v1.0.0.json").read_text())["_meta"]["weights"]
idx = json.loads((HERE / "inputs-v4" / "_index.json").read_text())
rows = list(csv.DictReader(open(HERE / "sean-regrade-raw.csv")))


def num(x):
    x = ("" if x is None else str(x)).strip()
    if x.lower() in ("n/a", "na", "", "-", "none", "nan"):
        return None
    try:
        return float(x)
    except Exception:
        return None


print("=" * 84)
print("1. LEVEL SHIFT or SPREAD DIFFERENCE?")
print("=" * 84)
print()
print("  %-5s %8s %8s %8s %8s %8s" %
      ("dim", "his mu", "my mu", "shift", "his sd", "my sd"))
for d in DIMS:
    hs = [num(r.get("YOUR_" + d)) for r in rows]
    ms = [num(r.get("my_new_" + d)) for r in rows]
    hs = [v for v in hs if v is not None]
    ms = [v for v in ms if v is not None]
    if len(hs) < 3 or len(ms) < 3:
        print("  %-5s %8.2f %8.2f   (too few)" % (d, statistics.mean(hs), statistics.mean(ms)))
        continue
    print("  %-5s %8.2f %8.2f %+8.2f %8.2f %8.2f"
          % (d, statistics.mean(hs), statistics.mean(ms),
             statistics.mean(hs) - statistics.mean(ms),
             statistics.stdev(hs), statistics.stdev(ms)))
print()
print("  If sd is similar for both, this is a LEVEL shift -> fix by re-anchoring the")
print("  level wording, not by changing the scale's range.")

print()
print("=" * 84)
print("2. RANK AGREEMENT WITHIN CATEGORY  (does the ORDER match?)")
print("=" * 84)
print()
cats = defaultdict(list)
for r in rows:
    e = idx["companies"].get(r["case_id"]) or {}
    h = sum(num(r.get("YOUR_" + d)) or 0 for d in ("RS", "MA", "DEF", "CR", "DR"))
    m = sum(num(r.get("my_new_" + d)) or 0 for d in ("RS", "MA", "DEF", "CR", "DR"))
    if e:
        cats[e["cat"]].append((e["name"], h, m))


def spearman(xs, ys):
    n = len(xs)
    if n < 3:
        return None
    rx = {v: i for i, v in enumerate(sorted(xs))}
    ry = {v: i for i, v in enumerate(sorted(ys))}
    d2 = sum((rx[a] - ry[b]) ** 2 for a, b in zip(xs, ys))
    return 1 - (6 * d2) / (n * (n * n - 1))


rhos = []
for c in sorted(cats):
    v = cats[c]
    if len(v) < 3:
        continue
    xs = [x[1] for x in v]
    ys = [x[2] for x in v]
    rho = spearman(xs, ys)
    rhos.append(rho)
    flag = ""
    if rho is not None and rho < 0.5:
        flag = "   <-- ORDER DISAGREES"
    print("  %-16s n=%-3d rho=%s%s" % (c, len(v), "%.2f" % rho if rho is not None else "n/a", flag))
print()
if rhos:
    print("  mean rank correlation across categories: %.2f  (n=%d categories)"
          % (statistics.mean(rhos), len(rhos)))
    print("  categories with rho >= 0.7: %d of %d" % (sum(1 for r in rhos if r >= 0.7), len(rhos)))

print()
print("=" * 84)
print("3. HIS HOLISTIC SCORE — closer to his dims, or to mine?")
print("=" * 84)
print()
print("  %-32s %10s %10s %10s" % ("company", "his dims", "his SCORE", "my score"))
n_his = n_my = 0
dh, dm = [], []
for r in rows:
    s = num(r.get("YOUR_SCORE"))
    if s is None:
        continue
    n_ = den = 0.0
    for d in DIMS:
        v = num(r.get("YOUR_" + d))
        if v is None:
            continue
        n_ += v * W[FULL[d]]
        den += W[FULL[d]]
    implied = 19.1667 * (n_ / den) if den else None
    m = num(r.get("my_new_score"))
    if implied is None:
        continue
    dh.append(abs(implied - s))
    if m is not None:
        dm.append(abs(m - s))
        n_my += 1
    n_his += 1
if dh:
    print()
    print("  |his dims - his SCORE| : mean %.1f  (n=%d)" % (statistics.mean(dh), n_his))
    print("  |my score - his SCORE| : mean %.1f  (n=%d)" % (statistics.mean(dm), len(dm)))
    closer = "HIS OWN DIMS" if statistics.mean(dh) < statistics.mean(dm) else "MY SCORE"
    print("  => his holistic score is closer to %s" % closer)
