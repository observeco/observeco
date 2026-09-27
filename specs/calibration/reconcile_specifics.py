"""Reconcile the specific disagreements that matter, with the evidence to hand.

Priority questions for Sean:
  A. DEF on large retailers: he scores MUCH higher (McDonald's +3, KFC +3, and 15 cases
     overall). This is the biggest single systematic gap.
  B. CR on fast-food: he scores ALL SIX at 4 where I scored all six at 2. Not a
     disagreement about a business -- a disagreement about the MARKET.
  C. DR on electronics retail: he scores 5 where I score 2.
  D. Sephora RS=5 vs my 2, the largest RS gap.
"""
import csv
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
idx = json.loads((HERE / "inputs-v4" / "_index.json").read_text())
rows = list(csv.DictReader(open(HERE / "sean-regrade-raw.csv")))
by = {r["company"]: r for r in rows}


def show(cid, fields=("YOUR_RS", "my_new_RS", "YOUR_MA", "my_new_MA",
                      "YOUR_DEF", "my_new_DEF", "YOUR_CR", "my_new_CR",
                      "YOUR_DR", "my_new_DR")):
    e = idx["companies"].get(cid)
    if not e:
        print("  %-26s (not in v4)" % cid)
        return
    r = by.get(e["name"])
    if not r:
        print("  %-26s (no regrade row)" % cid)
        return
    print("  %s  [%s]" % (e["name"], e["cat"]))
    print("     his : RS=%s MA=%s DEF=%s CR=%s DR=%s"
          % (r.get("YOUR_RS"), r.get("YOUR_MA"), r.get("YOUR_DEF"),
             r.get("YOUR_CR"), r.get("YOUR_DR")))
    print("     mine: RS=%s MA=%s DEF=%s CR=%s DR=%s"
          % (r.get("my_new_RS"), r.get("my_new_MA"), r.get("my_new_DEF"),
             r.get("my_new_CR"), r.get("my_new_DR")))
    ctx = " ".join(str(r.get("context") or "").split())
    print("     context: %s" % ctx[:190])


print("=" * 84)
print("A. DEFENSIBILITY ON LARGE RETAILERS  (his much higher)")
print("=" * 84)
print()
for cid in ("FF01-mcdonalds", "FF02-kfc", "SM01-ntuc", "HB04-sephora"):
    show(cid)
    print()

print("=" * 84)
print("B. competitive_room ON FAST-FOOD  (all six of his = 4, all six of mine = 2)")
print("=" * 84)
print()
print("  He scored EVERY fast-food case CR=4. I scored every one CR=2.")
print("  This is a disagreement about the MARKET, not about any business.")
print()
for cid in ("FF01-mcdonalds", "FF05-jollibee", "FF06-shake"):
    show(cid)
    print()

print("=" * 84)
print("C. demand_reach ON ELECTRONICS  (his 5, mine 2-3)")
print("=" * 84)
print()
for cid in ("EL02-harvey", "EL03-best"):
    show(cid)
    print()

print("=" * 84)
print("D. THE LARGEST RS GAP — Sephora")
print("=" * 84)
print()
show("HB04-sephora")

print()
print("=" * 84)
print("E. WHERE I SCORED HIGHER THAN HIM (the reverse direction)")
print("=" * 84)
print()


def num(x):
    x = ("" if x is None else str(x)).strip()
    if x.lower() in ("n/a", "na", "", "-", "none", "nan"):
        return None
    try:
        return float(x)
    except Exception:
        return None


worst = []
for r in rows:
    for d in ("RS", "MA", "DEF", "CR", "DR"):
        h, m = num(r.get("YOUR_" + d)), num(r.get("my_new_" + d))
        if h is not None and m is not None and (m - h) >= 2:
            worst.append((r["company"], r["category"], d, h, m, m - h))
worst.sort(key=lambda x: -x[5])
print("  cases where MINE is >=2 ABOVE his: %d" % len(worst))
for nm, cat, d, h, m, dd in worst[:14]:
    print("     %-32s %-14s %s: his=%g mine=%g  +%g" % (nm[:31], cat[:13], d, h, m, dd))
print()
print("  (for contrast, cases where HIS is >=2 above mine, by dimension: )")
from collections import Counter
c = Counter()
for r in rows:
    for d in ("RS", "MA", "DEF", "CR", "DR"):
        h, m = num(r.get("YOUR_" + d)), num(r.get("my_new_" + d))
        if h is not None and m is not None and (h - m) >= 2:
            c[d] += 1
print("     %s" % dict(c))
c2 = Counter()
for r in rows:
    for d in ("RS", "MA", "DEF", "CR", "DR"):
        h, m = num(r.get("YOUR_" + d)), num(r.get("my_new_" + d))
        if h is not None and m is not None and (m - h) >= 2:
            c2[d] += 1
print("     (mine above his: %s)" % dict(c2))
