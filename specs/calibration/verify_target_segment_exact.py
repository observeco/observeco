"""verify_target_segment_exact.py — is "85% exact on the target segment" true?

The spec (S10.7) claims: band agreement 100% within one band (n=114), and
"85% exact on the target segment".

"Exact" must mean EXACT BAND MATCH (same band), because D2 says the client sees a band and
D1 makes band agreement the bar. Dimension-exact is explicitly NOT the bar (R5).

Verify with both sides on the harness formula (run_jev.py:365).
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
ABBR = {"relative_strength": "RS", "mental_advantage": "MA", "defensibility": "DEF",
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
    if s is None:
        return None
    for nm, lo, hi in BANDS:
        if lo <= s <= hi:
            return nm
    return BANDS[0][0] if s < BANDS[0][1] else BANDS[-1][0]


def comp(vals):
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
    hd = {d: num(r.get("YOUR_" + ABBR[d])) for d in W}
    hc = comp(hd)
    if hc is None:
        continue
    # per-dimension exact on the target segment too
    md = run.get("dimensions_display_1to5") or {}
    un = set(run.get("dimensions_unscored") or [])
    recs.append({"name": e["name"], "mine": mine, "his": hc,
                 "mb": band_of(mine), "hb": band_of(hc),
                 "dim_exact": sum(1 for d in W
                                  if hd[d] is not None and d not in un
                                  and md.get(d) == hd[d]),
                 "dim_n": sum(1 for d in W
                              if hd[d] is not None and d not in un and md.get(d) is not None)})

target = [r for r in recs if r["hb"] in (ORDER[0], ORDER[1])]

print("=" * 92)
print('VERIFY: the spec claims "85% exact on the target segment"')
print("=" * 92)
print()


def line(label, sub):
    n = len(sub)
    same = sum(1 for r in sub if r["mb"] == r["hb"])
    w1 = sum(1 for r in sub if abs(ORDER.index(r["mb"]) - ORDER.index(r["hb"])) <= 1)
    print("  %-34s n=%3d  exact-band %5.1f%%   within-1 %5.1f%%"
          % (label, n, 100 * same / n, 100 * w1 / n))
    return 100 * same / n


line("ALL", recs)
ex_t = line("TARGET SEGMENT (Fragile or Contested)", target)
print()
print("  --- what the 85% could have meant ---")
tot_e = sum(r["dim_exact"] for r in target)
tot_n = sum(r["dim_n"] for r in target)
print("  (a) exact BAND on target segment      : %.1f%%" % ex_t)
print("  (b) exact DIMENSION cells on target   : %.1f%%  (%d/%d)"
      % (100 * tot_e / tot_n if tot_n else 0, tot_e, tot_n))
print("  (c) band agreement within-1 on target : %.1f%%"
      % (100 * sum(1 for r in target if abs(ORDER.index(r['mb']) - ORDER.index(r['hb'])) <= 1) / len(target)))
print()
print("  VERDICT: the claim is %s" % (
    "CONFIRMED as exact-band" if abs(ex_t - 85) <= 3 else
    "WRONG as exact-band (%.1f%% vs 85%%)" % ex_t))
print("=" * 92)
