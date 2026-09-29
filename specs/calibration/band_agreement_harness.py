"""band_agreement_harness.py — band agreement with BOTH sides on the HARNESS formula.

WHY THIS EXISTS
---------------
Six analysis scripts (test_band_agreement.py, test_target_segment.py, test_gap_structure.py,
test_renormalisation.py, diag_compression.py, verify_composite_replication.py) compute Sean's
composite with (v-1)/(n-1). The harness computes level/count (run_jev.py:365). So the earlier
band-agreement numbers compared MY harness composite against SEAN'S min-max composite -- two
different scales. The compression figure that came out of that (+13.0) was retracted; the
band numbers that came out of it were never re-derived.

This script computes both sides with the harness formula and reports band agreement only.
"""
import csv
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
V = json.loads((HERE / "rubric-v1.8.0.json").read_text())
W = V["_meta"]["weights"]
BANDS = V["_meta"]["bands"]
ORDER = [b[0] for b in BANDS]
COUNTS = {d: len(V["questions"][d]["levels"]) for d in W}
# 1.19.0 rename (D54): live key is position_strength; frozen runs keep the legacy key.
LEGACY_DIM_ALIAS = {"position_strength": "relative_strength"}
CSV_COL = {"position_strength": "RS", "relative_strength": "RS"}  # recorded history; do not rename
ABBR = {"position_strength": "PS", "relative_strength": "PS",
        "mental_advantage": "MA", "defensibility": "DEF",
        "competitive_room": "CR", "market_headroom": "MH", "demand_reach": "DR"}

idx = json.loads((HERE / "inputs-v4" / "_index.json").read_text())
by = {r["company"]: r for r in csv.DictReader(open(HERE / "sean-regrade-raw.csv"))}


def num(x):
    x = ("" if x is None else str(x)).strip()
    if x.lower() in ("n/a", "na", "", "-", "none", "nan"):
        return None
    try:
        return float(x)
    except Exception:
        return None


def band_of(s):
    for nm, lo, hi in BANDS:
        if lo <= s <= hi:
            return nm
    if s < BANDS[0][1]:
        return BANDS[0][0]
    return BANDS[-1][0]


def comp(vals):
    """EXACT replication of run_jev.py:365 — sum(v / count * renormalised weight)."""
    scored = [k for k in W if vals.get(k) is not None]
    if not scored:
        return None
    total = sum(W[k] for k in scored)
    used = {k: W[k] / total * 100 for k in scored}
    return round(sum(vals[k] / COUNTS[k] * used[k] for k in scored))


recs = []
for cid, e in idx["companies"].items():
    if e["cat"] == "home-not-permitted":
        continue
    f = HERE / "runs-v18" / ("jev-%s.json" % cid)
    if not f.exists():
        continue
    run = json.loads(f.read_text())
    mine = run.get("composite")
    if mine is None:
        continue
    r = by.get(e["name"]) or {}
    # CSV_COL, not ABBR: the recorded human-grade columns keep their original names (YOUR_RS)
    # and must not follow a dimension rename. Same bug as measure_alignment.py had.
    his_dims = {d: num(r.get("YOUR_" + CSV_COL.get(d, ABBR[d]))) for d in W}
    # CR is CLOSED and ADOPTED: his number is the answer, so use it on both sides.
    if his_dims.get("competitive_room") is not None:
        mine_dims = run.get("dimensions_display_1to5") or {}
    hc = comp(his_dims)
    if hc is None:
        continue
    recs.append({"name": e["name"], "cat": e["cat"], "mine": mine, "his": hc,
                 "mb": band_of(mine), "hb": band_of(hc)})

print("=" * 92)
print("BAND AGREEMENT — both composites on the HARNESS formula (run_jev.py:365)")
print("=" * 92)
print(f"  reference: {HERE/'rubric-v1.8.0.json'}")
print(f"  run dir  : runs-v18")
print(f"  cases    : {len(recs)}  (home-not-permitted excluded, matching D4 refusal)")
print()


def report(label, sub):
    if not sub:
        return None
    n = len(sub)
    same = sum(1 for r in sub if r["mb"] == r["hb"])
    far = sum(1 for r in sub
              if abs(ORDER.index(r["mb"]) - ORDER.index(r["hb"])) >= 2)
    print("  %-24s n=%3d   same %5.1f%%   within-1 %5.1f%%   TWO+ OFF %5.1f%% (%d)"
          % (label, n, 100 * same / n, 100 * (n - far) / n, 100 * far / n, far))
    return n, 100 * (n - far) / n, 100 * far / n


print("  BY HIS TRUE BAND:")
for b in ORDER:
    report("   " + b, [r for r in recs if r["hb"] == b])
print()
n, w1, f2 = report("ALL", recs)
target = [r for r in recs if r["hb"] in (ORDER[0], ORDER[1])]
print()
print("  TARGET SEGMENT (D3: his band == Fragile or Contested):")
tn, tw1, tf2 = report("   weak-positioning", target)
print()
print("=" * 92)
print("  CLOSE CONDITION (D1): >=90% within one band, <=5% two-or-more off")
print("=" * 92)
print(f"    ALL            : {w1:.1f}% within-1 / {f2:.1f}% two+ off   "
      f"{'PASS' if w1 >= 90 and f2 <= 5 else 'FAIL'}")
print(f"    TARGET SEGMENT : {tw1:.1f}% within-1 / {tf2:.1f}% two+ off   "
      f"{'PASS' if tw1 >= 90 and tf2 <= 5 else 'FAIL'}")
print()
print("  SAME-BAND (exact band) RATE:")
print(f"    ALL  : {100*sum(1 for r in recs if r['mb']==r['hb'])/len(recs):.1f}%")
print()
print("=" * 92)
print("  PROMOTION — business I place HIGHER than he does")
print("=" * 92)
prom = [r for r in recs if ORDER.index(r["mb"]) > ORDER.index(r["hb"])]
print(f"    I am MORE generous: {len(prom)} of {len(recs)}")
print(f"    I am HARSHER:       {sum(1 for r in recs if ORDER.index(r['mb']) < ORDER.index(r['hb']))}")
cross = [r for r in recs if r["hb"] == ORDER[0] and r["mb"] != ORDER[0]]
tot_f = sum(1 for r in recs if r["hb"] == ORDER[0])
print(f"    Fragile moved OUT of Fragile: {len(cross)} of {tot_f}")
print("=" * 92)
print("  FOR THE SPEC (copy these):")
print(f"    band agreement, all cases          : {100*sum(1 for r in recs if abs(ORDER.index(r['mb'])-ORDER.index(r['hb']))<=1)/len(recs):.1f}%  (n={len(recs)})")
print(f"    two-or-more bands off              : {100*sum(1 for r in recs if abs(ORDER.index(r['mb'])-ORDER.index(r['hb']))>=2)/len(recs):.1f}%")
print(f"    target segment within one band     : {tw1:.1f}%  (n={tn})")
print(f"    target segment two-or-more off     : {tf2:.1f}%")
print(f"    exact band (not the bar)           : {100*sum(1 for r in recs if r['mb']==r['hb'])/len(recs):.1f}%")
print("=" * 92)
