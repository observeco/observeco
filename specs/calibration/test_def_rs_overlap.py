"""Two checks before I revise the rubric.

1. DEF vs RS in HIS grades. His Q1 answer says DEF reflects decades+capital (an asset
   barrier). My RS also reflects position. If his DEF and RS are near-identical, the
   revision risks making them redundant. Measure it.

2. Book 1's actual claim on fast food / capped markets, to check Q2 against the source
   rather than my memory.
"""
import csv
import statistics
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
rows = list(csv.DictReader(open(HERE / "sean-regrade-raw.csv")))


def num(x):
    x = ("" if x is None else str(x)).strip()
    if x.lower() in ("n/a", "na", "", "-", "none", "nan"):
        return None
    try:
        return float(x)
    except Exception:
        return None


def ps(a, b):
    out = []
    for r in rows:
        x, y = num(r.get(a)), num(r.get(b))
        if x is not None and y is not None:
            out.append((x, y))
    return out


def pearson(p):
    if len(p) < 3:
        return None
    xs, ys = [a for a, _ in p], [b for _, b in p]
    mx, my = statistics.mean(xs), statistics.mean(ys)
    cov = sum((x - mx) * (y - my) for x, y in p)
    dx = sum((x - mx) ** 2 for x in xs) ** 0.5
    dy = sum((y - my) ** 2 for y in ys) ** 0.5
    return cov / (dx * dy) if dx and dy else None


print("=" * 80)
print("HIS DEF vs HIS RS — are they distinct constructs in his grading?")
print("=" * 80)
print()
p = ps("YOUR_DEF", "YOUR_RS")
d = [a - b for a, b in p]
print("  n=%d  r=%.2f  mean|DEF-RS|=%.2f  identical=%.0f%%"
      % (len(p), pearson(p), statistics.mean(abs(x) for x in d),
         100 * sum(1 for x in d if x == 0) / len(d)))
print("  mean his DEF=%.2f  mean his RS=%.2f"
      % (statistics.mean(a for a, _ in p), statistics.mean(b for _, b in p)))
print("  DEF minus RS: %s" % dict(sorted(Counter(d).items())))
print()
print("  (for comparison, HIS MA vs HIS RS:)")
p2 = ps("YOUR_MA", "YOUR_RS")
print("  n=%d  r=%.2f  mean|MA-RS|=%.2f" % (len(p2), pearson(p2),
                                             statistics.mean(abs(a - b) for a, b in p2)))
print()
print("  Interpretation: if DEF-RS are highly correlated, a revision that makes DEF")
print("  reward assets/scale would collapse them into one construct.")

print()
print("=" * 80)
print("MY OWN DEF vs MY RS — same check on the instrument")
print("=" * 80)
print()
p = ps("my_new_DEF", "my_new_RS")
d = [a - b for a, b in p]
print("  n=%d  r=%.2f  mean|DEF-RS|=%.2f  identical=%.0f%%"
      % (len(p), pearson(p), statistics.mean(abs(x) for x in d),
         100 * sum(1 for x in d if x == 0) / len(d)))

print()
print("=" * 80)
print("HOW MANY CASES SIT AT HIS DEF >= 4 (where the Q1 dispute lives)")
print("=" * 80)
print()
hi = [(r["company"], num(r.get("YOUR_DEF")), num(r.get("my_new_DEF")),
       num(r.get("YOUR_RS")), num(r.get("my_new_RS")))
      for r in rows if (num(r.get("YOUR_DEF")) or 0) >= 4]
print("  cases he scored DEF >= 4: %d of 120" % len(hi))
print()
print("  %-32s %6s %6s %6s %6s" % ("company", "hisDEF", "myDEF", "hisRS", "myRS"))
for nm, hd, md, hr, mr in sorted(hi, key=lambda x: -(x[1] or 0))[:22]:
    print("  %-32s %6g %6s %6s %6s" % (nm[:31], hd, md, hr, mr))
print()
print("  If his DEF>=4 cases also have high RS, the two dimensions agree -- which is")
print("  fine for consistency but means DEF is measuring STANDING, not copy-protection.")
