"""Does RENORMALISATION inflate the composite for small businesses?

THE SIGNAL: at the DIMENSION level his scores are slightly higher than mine (offset +0.13).
But at the COMPOSITE level my score is 20-28 points HIGHER than his for small businesses:
  Chin Mee Chin  mine 67  his 39   (+28)
  Four Leaves    mine 67  his 42   (+25)
  mobile hairdresser mine 40 his 19 (+21)
  My Skin Diary  mine 44  his 24   (+20)

Those two facts can only both be true if the COMPOSITE is computed differently from the
dimensions. It is: run_jev renormalises the weights over the SCORED dimensions only, so
when a dimension is dropped (market_headroom is n/a in ~105 of 120), its weight is
redistributed to the rest.

If the dropped dimensions would have been LOW for that business, renormalising over the
remaining (higher) ones INFLATES the composite. That is a structural upward bias
concentrated on small businesses -- exactly the population where dimensions get dropped.

THE TEST: compute his composite two ways from HIS OWN dimension scores --
  (a) renormalised over scored dims  (what the scorer does)
  (b) dropped dims counted at the bottom of the scale (i.e. no redistribution of "good" weight)
and see which version is closer to the composite he would have given. Also measure how much
of my composite overshoot is explained by renormalisation alone.
"""
import csv
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
V = json.loads((HERE / "rubric-v1.8.0.json").read_text())
W = V["_meta"]["weights"]
ABBR = {"relative_strength": "RS", "mental_advantage": "MA", "defensibility": "DEF",
        "competitive_room": "CR", "market_headroom": "MH", "demand_reach": "DR"}
COUNTS = {}
for d in W:
    COUNTS[d] = len(V["questions"][d]["levels"])

idx = json.loads((HERE / "inputs-v4" / "_index.json").read_text())
rows = list(csv.DictReader(open(HERE / "sean-regrade-raw.csv")))
by = {r["company"]: r for r in rows}


def num(x):
    x = ("" if x is None else str(x)).strip()
    if x.lower() in ("n/a", "na", "", "-", "none", "nan"):
        return None
    try:
        return float(x)
    except Exception:
        return None


def comp(vals, mode="renorm"):
    acc = tot = 0.0
    for d, v in vals.items():
        if v is None:
            continue
        n = COUNTS[d]
        # v/n matches run_jev.py:365; (v-1)/(n-1) was the retracted mismatch
        pts = (v / n) * 100.0
        acc += W[d] * pts
        tot += W[d]
    if mode == "renorm":
        return acc / tot if tot else None
    # "no-redistribution": dropped dims contribute 0 points but keep their weight
    return acc / sum(W.values())


print("=" * 92)
print("RENORMALISATION TEST — is the composite inflated for businesses with dropped dims?")
print("=" * 92)
print()

print("  %-30s %-7s %8s %8s %8s" % ("company", "drops", "mine", "his(renorm)", "his(0-wt)"))
cases = ["Chin Mee Chin", "Four Leaves", "Toast Box", "LiHO TEA", "CHICHA San Chen",
         "A home-based mobile hairdresser", "My Skin Diary", "Mono Studio",
         "BreadTalk", "KFC Singapore"]
deltas = []
for nm in cases:
    cid = next((c for c, e in idx["companies"].items() if e["name"] == nm), None)
    if not cid:
        continue
    run = json.loads((HERE / "runs-v18" / ("jev-%s.json" % cid)).read_text())
    disp = run.get("dimensions_display_1to5") or {}
    un = set(run.get("dimensions_unscored") or [])
    mine = run.get("composite")
    r = by.get(nm) or {}
    his = {d: num(r.get("YOUR_" + ABBR[d])) for d in W}
    n_his = sum(1 for v in his.values() if v is not None)
    cr = comp(his, "renorm")
    c0 = comp(his, "noweight")
    print("  %-30s %-7s %8.1f %8s %8s"
          % (nm[:29], "%d/%d" % (len(un), len(W)),
             mine if mine is not None else -1,
             "%.1f" % cr if cr else "-", "%.1f" % c0 if c0 else "-"))
    if cr is not None and c0 is not None:
        deltas.append(cr - c0)

print()
print("  effect of renormalisation on HIS OWN scores (renorm minus no-redistribution):")
if deltas:
    print("    mean %+.1f points, max %+.1f" % (sum(deltas) / len(deltas), max(deltas)))
print()

# corpus-wide: how many cases have dropped dims, and how much inflation
from collections import Counter
drop_counts = Counter()
infl = []
for cid, e in idx["companies"].items():
    run = json.loads((HERE / "runs-v18" / ("jev-%s.json" % cid)).read_text())
    un = set(run.get("dimensions_unscored") or [])
    drop_counts[len(un)] += 1
    r = by.get(e["name"]) or {}
    his = {d: num(r.get("YOUR_" + ABBR[d])) for d in W}
    cr = comp(his, "renorm")
    c0 = comp(his, "noweight")
    if cr is not None and c0 is not None and len(un) > 0:
        infl.append((cr - c0, e["name"], len(un)))
print("  corpus: cases by number of dropped dimensions: %s" % dict(sorted(drop_counts.items())))
if infl:
    infl.sort(reverse=True)
    print("  mean renormalisation uplift across cases with any drop: %+.1f points"
          % (sum(x[0] for x in infl) / len(infl)))
    print()
    print("  LARGEST uplifts:")
    for d, nm, k in infl[:8]:
        print("    %+6.1f  %-34s (%d dropped)" % (d, nm[:33], k))
