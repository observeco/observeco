"""CRITICAL CHECK before claiming convergence.

'his holistic SCORE is 0.2 from my score' is implausibly good. Two possibilities:
  (a) genuine convergence on the composite, or
  (b) he copied my_new_score into YOUR_SCORE for convenience.

(b) would make the finding an artefact. Test it: count EXACT equalities. If a large
fraction are exactly equal, it is copying, not convergence, and must not be reported
as agreement.
"""
import csv
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


pairs = []
for r in rows:
    h = num(r.get("YOUR_SCORE"))
    m = num(r.get("my_new_score"))
    if h is not None and m is not None:
        pairs.append((r["company"], h, m, h - m))

print("rows with both his SCORE and my score: %d" % len(pairs))
print()
exact = sum(1 for _, h, m, _ in pairs if h == m)
print("EXACTLY equal      : %d of %d (%.0f%%)" % (exact, len(pairs), 100 * exact / len(pairs)))
print("within 1 point     : %d (%.0f%%)"
      % (sum(1 for _, _, _, d in pairs if abs(d) <= 1),
         100 * sum(1 for _, _, _, d in pairs if abs(d) <= 1) / len(pairs)))
print("within 3 points    : %d (%.0f%%)"
      % (sum(1 for _, _, _, d in pairs if abs(d) <= 3),
         100 * sum(1 for _, _, _, d in pairs if abs(d) <= 3) / len(pairs)))
print()
print("difference distribution (his SCORE minus my score):")
for k, v in sorted(Counter(d for _, _, _, d in pairs).items()):
    print("   %+6g : %d" % (k, v))
print()
print("=== the rows, sorted by |diff| ===")
for nm, h, m, d in sorted(pairs, key=lambda x: -abs(x[3]))[:18]:
    print("   %-32s his=%6g  mine=%6g  %+g" % (nm[:31], h, m, d))
print()
if exact / len(pairs) > 0.7:
    print("VERDICT: he copied my score into YOUR_SCORE in the majority of filled rows.")
    print("         The 'closer to my score' result is an ARTEFACT and must not be")
    print("         reported as genuine agreement.")
else:
    print("VERDICT: not wholesale copying -- some genuine convergence, but inspect the")
    print("         large-diff rows above before claiming agreement.")
