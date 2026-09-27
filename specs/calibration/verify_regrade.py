"""Verify the regrade values are real, then compare his six-dimension grades to mine.

Guards first: a "filled" count can be an artefact (a formula, a stray default). Check the
actual distributions before analysing anything.
"""
import csv
import json
import statistics
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
SHORT = ["relative_strength", "mental_advantage", "defensibility",
         "competitive_room", "market_headroom", "demand_reach"]
DIMS = ["RS", "MA", "DEF", "CR", "MH", "DR"]
FULL = dict(zip(DIMS, SHORT))
W = json.loads((HERE / "rubric-v1.0.0.json").read_text())["_meta"]["weights"]

rows = list(csv.DictReader(open(HERE / "sean-regrade-raw.csv")))
print("rows: %d" % len(rows))

NA = ("n/a", "na", "n.a.", "n.a", "-", "", "none", "nan")


def num(x):
    x = ("" if x is None else str(x)).strip()
    if x.lower() in NA:
        return None
    try:
        return float(x)
    except Exception:
        return None


print()
print("=" * 80)
print("GUARD — what did he actually enter?")
print("=" * 80)
for d in DIMS:
    vals = [num(r.get("YOUR_" + d)) for r in rows]
    got = [v for v in vals if v is not None]
    nas = sum(1 for r in rows
              if str(r.get("YOUR_" + d) or "").strip().lower() in ("n/a", "na"))
    rng = ("%g-%g" % (min(got), max(got))) if got else "-"
    print("  YOUR_%-4s n=%-4d mean=%.2f  range=%-7s n/a=%d"
          % (d, len(got), statistics.mean(got) if got else 0, rng, nas))

sc = [num(r.get("YOUR_SCORE")) for r in rows]
scg = [v for v in sc if v is not None]
bnd = Counter((r.get("YOUR_BAND") or "").strip() for r in rows)
notes = sum(1 for r in rows if (r.get("YOUR_NOTES") or "").strip())
print("  YOUR_SCORE n=%d mean=%.1f range=%g-%g"
      % (len(scg), statistics.mean(scg) if scg else 0,
         min(scg) if scg else 0, max(scg) if scg else 0))
print("  YOUR_BAND  : %s" % dict(bnd))
print("  notes entered: %d" % notes)

print()
print("=" * 80)
print("PER-DIMENSION AGREEMENT  (his v1.0.0 regrade vs my v1.0.0)")
print("=" * 80)
print()
print("  %-5s %4s %8s %8s %8s %7s %9s" %
      ("dim", "n", "his mu", "my mu", "mean d", "exact", ">=2 apart"))
for d in DIMS:
    pairs = []
    for r in rows:
        h = num(r.get("YOUR_" + d))
        m = num(r.get("my_new_" + d))
        if h is not None and m is not None:
            pairs.append((h, m))
    if not pairs:
        continue
    ds = [h - m for h, m in pairs]
    exact = sum(1 for x in ds if x == 0)
    big = sum(1 for x in ds if abs(x) >= 2)
    print("  %-5s %4d %8.2f %8.2f %+8.2f %6d%% %8d%%" % (
        d, len(ds), statistics.mean(h for h, _ in pairs),
        statistics.mean(m for _, m in pairs), statistics.mean(ds),
        100 * exact / len(ds), 100 * big / len(ds)))
print()
print("  mean d = HIS minus MINE (positive = he grades higher)")

print()
print("=" * 80)
print("COMPOSITE")
print("=" * 80)
print()
print("  Consistency: does his YOUR_SCORE match his own dimension entries?")
bad = 0
for r in rows:
    h = {d: num(r.get("YOUR_" + d)) for d in DIMS}
    s = num(r.get("YOUR_SCORE"))
    n_ = den = 0.0
    for d in DIMS:
        if h[d] is None:
            continue
        n_ += h[d] * W[FULL[d]]
        den += W[FULL[d]]
    if den and s is not None:
        calc = round(19.1667 * (n_ / den), 0)
        if abs(calc - s) > 2:
            bad += 1
print("  rows where SCORE differs from his own dims by >2: %d of %d" % (bad, len(rows)))

# his implied composite vs mine
print()
print("  His implied composite (from his dims) vs my recorded composite:")
cp = []
for r in rows:
    h = {d: num(r.get("YOUR_" + d)) for d in DIMS}
    n_ = den = 0.0
    for d in DIMS:
        if h[d] is None:
            continue
        n_ += h[d] * W[FULL[d]]
        den += W[FULL[d]]
    m = num(r.get("my_new_score"))
    if den and m is not None:
        cp.append((r["company"], r["category"], round(19.1667 * (n_ / den), 1), m))
if cp:
    ds = [h - m for _, _, h, m in cp]
    print("     n=%d  mean diff (his-mine) %+.1f  mean|diff| %.1f"
          % (len(cp), statistics.mean(ds), statistics.mean(abs(x) for x in ds)))
