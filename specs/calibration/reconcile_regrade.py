"""Build the reconciliation list: where he and I actually disagree, and the checks that
tell convergent validity from conflict.

Four things:
  1. market_headroom — he marked n/a 106 times. Did MY rubric drop it in the same cases?
     If yes, that is INDEPENDENT agreement on when the dimension does not apply -- the
     strongest validation of the A3 elasticity gate available.
  2. Every dimension's >=2-apart cases, with his and my numbers.
  3. relative_strength's disagreements specifically (the new dimension).
  4. The 11 rows where his own SCORE contradicts his own dimension entries.
"""
import csv
import json
import statistics
from pathlib import Path

HERE = Path(__file__).resolve().parent
SHORT = ["relative_strength", "mental_advantage", "defensibility",
         "competitive_room", "market_headroom", "demand_reach"]
DIMS = ["RS", "MA", "DEF", "CR", "MH", "DR"]
FULL = dict(zip(DIMS, SHORT))
W = json.loads((HERE / "rubric-v1.0.0.json").read_text())["_meta"]["weights"]
NA = ("n/a", "na", "n.a.", "n.a", "-", "", "none", "nan")


def num(x):
    x = ("" if x is None else str(x)).strip()
    return None if x.lower() in NA else (float(x) if _isnum(x) else None)


def _isnum(x):
    try:
        float(x)
        return True
    except Exception:
        return False


def isna(x):
    return str(x or "").strip().lower() in ("n/a", "na")


rows = list(csv.DictReader(open(HERE / "sean-regrade-raw.csv")))

print("=" * 84)
print("1. MARKET_HEADROOM — did he independently agree with the A3 drop?")
print("=" * 84)
print()
both = 0
onlyme = 0
onlyhim = 0
neither = 0
disagree = []
for r in rows:
    h = r.get("YOUR_MH") or ""
    m = r.get("my_new_MH") or ""
    h_na = isna(h) or num(h) is None
    m_na = isna(m) or num(m) is None
    if h_na and m_na:
        both += 1
    elif m_na and not h_na:
        onlyme += 1
    elif h_na and not m_na:
        onlyhim += 1
    else:
        neither += 1
print("  he n/a AND I dropped  : %d   <- INDEPENDENT AGREEMENT on non-applicability"
      % both)
print("  I dropped, he scored  : %d" % onlyme)
print("  he n/a, I scored      : %d" % onlyhim)
print("  both scored           : %d" % neither)
print()
tot = len(rows)
if tot:
    print("  agreement on applicability: %.0f%% of cases" % (100 * (both + neither) / tot))
if onlyhim:
    print()
    print("  HE said n/a where I scored (his judgement that it does not apply, mine it does):")
    for r in rows:
        h = r.get("YOUR_MH") or ""
        m = r.get("my_new_MH") or ""
        if isna(h) and num(m) is not None:
            print("     %-34s he=n/a  me=%s" % (r["company"][:33], m))

print()
print("=" * 84)
print("2. DISAGREEMENTS BY DIMENSION  (|his - mine| >= 2)")
print("=" * 84)
for d in DIMS:
    cases = []
    for r in rows:
        h, m = num(r.get("YOUR_" + d)), num(r.get("my_new_" + d))
        if h is not None and m is not None and abs(h - m) >= 2:
            cases.append((r["company"], r["category"], h, m, h - m))
    print()
    print("--- %s (%d disagreements of %d comparable) ---"
          % (d, len(cases), sum(1 for r in rows
                                if num(r.get("YOUR_" + d)) is not None
                                and num(r.get("my_new_" + d)) is not None)))
    for nm, cat, h, m, dd in sorted(cases, key=lambda x: -abs(x[4])):
        print("     %-32s %-14s his=%g mine=%g  %+g" % (nm[:31], cat[:13], h, m, dd))

print()
print("=" * 84)
print("3. HIS OWN SCORE vs HIS OWN DIMENSIONS (internal consistency)")
print("=" * 84)
print()
bad = []
for r in rows:
    n_ = den = 0.0
    for d in DIMS:
        v = num(r.get("YOUR_" + d))
        if v is None:
            continue
        n_ += v * W[FULL[d]]
        den += W[FULL[d]]
    s = num(r.get("YOUR_SCORE"))
    if den and s is not None:
        calc = 19.1667 * (n_ / den)
        if abs(calc - s) > 3:
            bad.append((r["company"], round(calc, 1), s, round(calc - s, 1)))
print("  rows where his SCORE is >3 away from his own dims: %d" % len(bad))
for nm, calc, s, dd in sorted(bad, key=lambda x: -abs(x[3]))[:12]:
    print("     %-32s his dims imply %6.1f  he wrote %-6g  diff %+g" % (nm[:31], calc, s, dd))
print()
print("  YOUR_SCORE filled: %d of 120  (he left 59 blank)"
      % sum(1 for r in rows if num(r.get("YOUR_SCORE")) is not None))

print()
print("=" * 84)
print("4. HIS BAND LABELS — he used AMBIGUOUS bands himself")
print("=" * 84)
from collections import Counter
c = Counter((r.get("YOUR_BAND") or "").strip() for r in rows)
for k, v in c.most_common():
    tag = "  <- he states a RANGE, not a word" if " OR " in k else ""
    print("   %-40s %d%s" % (k, v, tag))
amb = sum(v for k, v in c.items() if " OR " in k)
print()
print("   cases where HE said the band is a range: %d of %d (%.0f%%)"
      % (amb, len(rows), 100 * amb / len(rows)))
mine_amb = sum(1 for r in rows if " OR " in (r.get("my_new_band") or ""))
print("   cases where MY band interval was ambiguous: %d" % mine_amb)
