"""Is the NEW position_strength dimension doing independent work, or is it redundant?

Two questions:
  Q1. Within HIS grades, are RS and MA the same number? If he graded them almost
      identically, either the definitions overlap or he read them as one thing.
  Q2. Does his RS track MY RS better than MY MA? If yes, he was grading the construct I
      intended. If his RS tracks my MA, the new dimension is not adding information.
"""
import csv
import json
import statistics
from pathlib import Path

HERE = Path(__file__).resolve().parent
NA = ("n/a", "na", "n.a.", "n.a", "-", "", "none", "nan")


def num(x):
    x = ("" if x is None else str(x)).strip()
    if x.lower() in NA:
        return None
    try:
        return float(x)
    except Exception:
        return None


rows = list(csv.DictReader(open(HERE / "sean-regrade-raw.csv")))


def pair(a, b):
    out = []
    for r in rows:
        x, y = num(r.get(a)), num(r.get(b))
        if x is not None and y is not None:
            out.append((x, y))
    return out


def pearson(ps):
    if len(ps) < 3:
        return None
    xs = [a for a, _ in ps]
    ys = [b for _, b in ps]
    mx, my = statistics.mean(xs), statistics.mean(ys)
    cov = sum((x - mx) * (y - my) for x, y in ps)
    dx = sum((x - mx) ** 2 for x in xs) ** 0.5
    dy = sum((y - my) ** 2 for y in ys) ** 0.5
    return cov / (dx * dy) if dx and dy else None


def mae(ps):
    return statistics.mean(abs(a - b) for a, b in ps)


def exact(ps):
    return 100 * sum(1 for a, b in ps if a == b) / len(ps)


print("=" * 84)
print("Q1. WITHIN HIS GRADES — is his RS the same as his MA?")
print("=" * 84)
print()
ps = pair("YOUR_RS", "YOUR_MA")
print("  n=%d   correlation r=%.2f   mean|RS-MA|=%.2f   exact identical=%.0f%%"
      % (len(ps), pearson(ps), mae(ps), exact(ps)))
print("  mean his RS=%.2f  mean his MA=%.2f" % (
    statistics.mean(a for a, _ in ps), statistics.mean(b for _, b in ps)))
diff = [a - b for a, b in ps]
from collections import Counter
print("  RS minus MA distribution: %s" % dict(sorted(Counter(diff).items())))
print()
print("  (for contrast, the same test on MY OWN scores:)")
pm = pair("my_new_RS", "my_new_MA")
print("  n=%d   correlation r=%.2f   mean|RS-MA|=%.2f   exact identical=%.0f%%"
      % (len(pm), pearson(pm), mae(pm), exact(pm)))

print()
print("=" * 84)
print("Q2. WHICH OF MY DIMENSIONS DOES HIS RS TRACK BEST?")
print("=" * 84)
print()
print("  %-24s %8s %8s %8s" % ("his RS vs my ...", "r", "mean|d|", "exact"))
for m in ("my_new_RS", "my_new_MA", "my_new_DEF", "my_new_CR", "my_new_DR"):
    ps = pair("YOUR_RS", m)
    if len(ps) < 3:
        continue
    print("  %-24s %8.2f %8.2f %7.0f%%" % (m, pearson(ps), mae(ps), exact(ps)))

print()
print("=" * 84)
print("Q2b. AND THE REVERSE — which of his dims tracks my RS best?")
print("=" * 84)
print()
for h in ("YOUR_RS", "YOUR_MA", "YOUR_DEF", "YOUR_CR", "YOUR_DR"):
    ps = pair(h, "my_new_RS")
    if len(ps) < 3:
        continue
    print("  %-12s vs my_new_RS : r=%.2f  mean|d|=%.2f" % (h, pearson(ps), mae(ps)))

print()
print("=" * 84)
print("Q3. IS HIS RS DISCRIMINATING, OR IS HE USING ONE VALUE EVERYWHERE?")
print("=" * 84)
print()
from collections import Counter as C
print("  his RS values : %s" % dict(sorted(C("" if num(r.get('YOUR_RS')) is None
                                           else int(num(r.get('YOUR_RS')))
                                           for r in rows).items())))
print("  my RS values  : %s" % dict(sorted(C("" if num(r.get('my_new_RS')) is None
                                           else int(num(r.get('my_new_RS')))
                                           for r in rows).items())))
print()
# within-category spread of his RS: is he differentiating rivals?
idx = json.loads((HERE / "inputs-v4" / "_index.json").read_text())
from collections import defaultdict
cats = defaultdict(list)
for r in rows:
    e = idx["companies"].get(r["case_id"]) or {}
    v = num(r.get("YOUR_RS"))
    if e and v is not None:
        cats[e["cat"]].append((e["name"], v))
print("  his RS WITHIN each category (the test of whether it separates rivals):")
for c in sorted(cats):
    vs = [v for _, v in cats[c]]
    if len(vs) >= 2:
        print("     %-16s %s   sd=%.2f" % (c, vs, statistics.stdev(vs)))
