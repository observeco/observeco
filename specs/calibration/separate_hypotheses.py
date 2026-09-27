"""Separate the two hypotheses using EXISTING data before asking Sean for more time.

H-A (FRAME): he grades absolute ('how good is this business?'); my scale asks 'compared
     with what?'. Signature: a uniform positive OFFSET with equal spread.
H-B (ANCHORS): same frame, my level ladder is calibrated too low. Signature: same
     offset, but his placement onto MY level TEXT would reproduce my numbers.

Both predict an offset, so the offset alone cannot separate them. What DOES differ:

  Test 1 -- REGRESSION SHAPE. his = a + b*mine.
     b ~ 1, a > 0        -> uniform offset (consistent with either)
     b < 1               -> compression: he uses a narrower range (or anchored on my column)
     b > 1               -> expansion
  Test 2 -- RELATIVIZATION ORDERING. H-A predicts the offset is LARGEST where my wording
     demands the most benchmark-holding, and SMALLEST where the question is nearly
     absolute. If the offsets do not order that way, H-A loses support.
  Test 3 -- A CONFOUND THAT THREATENS THE WHOLE COMPARISON. He had my scores visible in
     the adjacent column, and he copied my composite in 59 of 61 rows. If his dimension
     scores are also anchored on mine, the agreement figures are contaminated.
"""
import csv
import json
import statistics
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
DIMS = ["RS", "MA", "DEF", "CR", "MH", "DR"]
SHORT = ["relative_strength", "mental_advantage", "defensibility",
         "competitive_room", "market_headroom", "demand_reach"]
FULL = dict(zip(DIMS, SHORT))
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


# my v1.2.0 scores
mine = {}
for p in (HERE / "runs-v12").glob("jev-*.json"):
    r = json.loads(p.read_text())
    d = r.get("dimensions_display_1to5") or {}
    u = set(r.get("dimensions_unscored") or [])
    mine[r["case"]] = {k: (None if k in u else d.get(k)) for k in SHORT}

# ---- Test 1 -----------------------------------------------------------------
print("=" * 84)
print("TEST 1 — REGRESSION SHAPE  his = a + b*mine   (v1.2.0 baseline)")
print("=" * 84)
print()
print("  %-5s %5s %8s %8s %8s %8s" % ("dim", "n", "slope b", "intercept a", "R2", "his sd/my sd"))
for d in DIMS:
    ps = []
    for r in rows:
        h = num(r.get("YOUR_" + d))
        m = (mine.get(r["case_id"]) or {}).get(FULL[d])
        if h is not None and m is not None:
            ps.append((h, m))
    if len(ps) < 5:
        continue
    hs = [h for h, _ in ps]
    ms = [m for _, m in ps]
    mh, mm = statistics.mean(hs), statistics.mean(ms)
    cov = sum((m - mm) * (h - mh) for h, m in ps)
    var = sum((m - mm) ** 2 for _, m in ps)
    b = cov / var if var else 0
    a = mh - b * mm
    pred = [a + b * m for _, m in ps]
    ss_res = sum((h - p) ** 2 for (h, _), p in zip(ps, pred))
    ss_tot = sum((h - mh) ** 2 for h in hs)
    r2 = 1 - ss_res / ss_tot if ss_tot else 0
    print("  %-5s %5d %8.2f %8.2f %8.2f %8.2f"
          % (d, len(ps), b, a, r2, statistics.stdev(hs) / statistics.stdev(ms)))
print()
print("  b ~ 1 with a > 0  = uniform offset (frame OR anchors)")
print("  b < 1             = compression (narrower range, or anchored on my column)")
print("  b > 1             = expansion")

# ---- Test 2 -----------------------------------------------------------------
print()
print("=" * 84)
print("TEST 2 — RELATIVIZATION ORDERING")
print("=" * 84)
print()
# how much does each dimension's QUESTION force a benchmark?
relativ = {
    "MA": 3,   # 'relative to what a business of its size would expect' -- heavy benchmark
    "RS": 3,   # 'vs the named occupants of the derived set' -- heavy benchmark
    "DEF": 2,  # 'what would a challenger have to spend' -- counterfactual benchmark
    "DR": 1,   # 'has the business defined its buyer' -- mostly a property of the business
    "CR": 0,   # about the MARKET, not the business -- nearly absolute about the market
    "MH": 0,   # about the MARKET -- nearly absolute
}
obs = {}
for d in DIMS:
    ps = []
    for r in rows:
        h = num(r.get("YOUR_" + d))
        m = (mine.get(r["case_id"]) or {}).get(FULL[d])
        if h is not None and m is not None:
            ps.append(h - m)
    if ps:
        obs[d] = statistics.mean(ps)
print("  %-5s %12s %12s" % ("dim", "benchmark?", "observed shift"))
for d in sorted(DIMS, key=lambda x: -relativ[x]):
    print("  %-5s %12d %+12.2f" % (d, relativ[d], obs.get(d, 0)))
print()
hi = [obs[d] for d in DIMS if relativ[d] >= 2 and d in obs]
lo = [obs[d] for d in DIMS if relativ[d] == 0 and d in obs]
print("  mean shift, heavy-benchmark dims (MA/RS/DEF) : %+.2f" % statistics.mean(hi))
print("  mean shift, market dims (CR/MH)              : %+.2f" % statistics.mean(lo))
print()
print("  H-A predicts the heavy-benchmark dims shift MORE than the market dims.")
if statistics.mean(hi) > statistics.mean(lo):
    print("  -> ordering CONSISTENT with H-A (but n=5 dims, weak evidence)")
else:
    print("  -> ordering CONTRADICTS H-A")

# ---- Test 3 -----------------------------------------------------------------
print()
print("=" * 84)
print("TEST 3 — THE CONFOUND: was he anchored on my visible column?")
print("=" * 84)
print()
print("  We know he copied my COMPOSITE in 59 of 61 filled rows. So he was reading my")
print("  column. Question: are his DIMENSION scores also anchored?")
print()
# anchoring signature: agreement should be HIGHER where my score was more extreme
# (anchoring pulls him toward my value most when mine is furthest from his prior)
print("  Within-category agreement, to remove category composition:")
cats = defaultdict(list)
for r in rows:
    e = idx["companies"].get(r["case_id"]) or {}
    if e:
        cats[e["cat"]].append(r)
print()
print("  %-18s %6s %8s" % ("category", "n", "mean|h-m| RS"))
for c in sorted(cats):
    v = cats[c]
    ds = []
    for r in v:
        h = num(r.get("YOUR_RS"))
        m = (mine.get(r["case_id"]) or {}).get("relative_strength")
        if h is not None and m is not None:
            ds.append(abs(h - m))
    if len(ds) >= 3:
        print("  %-18s %6d %8.2f" % (c, len(ds), statistics.mean(ds)))

print()
print("  ANCHORING TEST: does |his - mine| grow as my score deviates from the")
print("  category mean? If he anchored, he was pulled TOWARD my value, so we should")
print("  see agreement HIGHEST at the extremes of my own distribution.")
rows_ = []
for c in cats:
    v = [r for r in cats[c] if num(r.get("YOUR_RS")) is not None
         and (mine.get(r["case_id"]) or {}).get("relative_strength") is not None]
    if len(v) < 4:
        continue
    mvals = [(mine[r["case_id"]]["relative_strength"]) for r in v]
    cmean = statistics.mean(mvals)
    for r in v:
        m = mine[r["case_id"]]["relative_strength"]
        h = num(r.get("YOUR_RS"))
        rows_.append((abs(m - cmean), abs(h - m)))
if len(rows_) >= 8:
    xs = [a for a, _ in rows_]
    ys = [b for _, b in rows_]
    mx, my = statistics.mean(xs), statistics.mean(ys)
    cov = sum((a - mx) * (b - my) for a, b in rows_)
    dx = sum((a - mx) ** 2 for a in xs) ** 0.5
    dy = sum((b - my) ** 2 for b in ys) ** 0.5
    r = cov / (dx * dy) if dx and dy else 0
    print("  correlation(|my RS - category mean|, |his RS - my RS|) = %+.2f  (n=%d)"
          % (r, len(rows_)))
    print("  negative -> agreement is BETTER at my extremes = anchoring signature")
    print("  ~zero    -> no anchoring signature in this measure")
