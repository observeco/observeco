"""THE PRODUCT-LEVEL TEST — but first, fix a measurement error I have been making.

I have been tuning against DIMENSION-LEVEL exact agreement. But the product does not show
six dimension scores to a client -- it shows a composite and a BAND. So the criterion that
matters for closure may be BAND agreement, which I have never measured.

WORSE, I CANNOT USE HIS COMPOSITE: check_score_copying.py showed 59 of 61 filled rows
copied my composite. Any band agreement computed from his composite is an artefact.

THE FIX: compute HIS composite FROM HIS DIMENSION SCORES using the rubric weights. That
removes the copying entirely -- it asks "if a client's six dimension answers were his, what
band would our own scorer produce, and does it match the band he would give?"

If band agreement is high while dimension exact is 56%, then the disagreement is granularity
below the product's resolution and the instrument may already be fit to close.
"""
import csv
import json
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
V = json.loads((HERE / "rubric-v1.8.0.json").read_text())
META = V["_meta"]
W = META["weights"]
BANDS = META["bands"]
COUNTS = {"relative_strength": 5, "mental_advantage": 5, "defensibility": 6,
          "competitive_room": 5, "market_headroom": 5, "demand_reach": 5}
ABBR = {"relative_strength": "RS", "mental_advantage": "MA", "defensibility": "DEF",
        "competitive_room": "CR", "market_headroom": "MH", "demand_reach": "DR"}

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


def band_of(score):
    """MUST round first, exactly as run_jev.py:365-366 does.

    The band table is integer-only and the ranges do NOT tile the number line: there are gaps
    at 37-38, 57-58 and 76-77. A fractional composite such as 37.037 or 57.407 matches no band,
    and the old fallback returned "?" -- silently dropping the case from the agreement count.
    Rounding is what the harness does, so rounding is what the measurement must do.

    Bands are stored as [name, min, max] lists, not dicts.
    """
    if score is None:
        return None
    score = round(score)
    for b in BANDS:
        if isinstance(b, (list, tuple)) and len(b) >= 3:
            nm, lo, hi = b[0], b[1], b[2]
        elif isinstance(b, dict):
            nm, lo, hi = (b.get("band") or b.get("name")), b.get("min"), b.get("max")
        else:
            continue
        if lo is not None and hi is not None and lo <= score <= hi:
            return nm
    # clamp to the extreme band rather than dropping the case
    first = BANDS[0]
    return first[0] if score < first[1] else BANDS[-1][0]


def composite(vals):
    """vals: dim -> 1..n or None. Renormalise over scored dims, as run_jev does."""
    tot_w = 0.0
    acc = 0.0
    for d, v in vals.items():
        if v is None:
            continue
        w = W.get(d, 0)
        n = COUNTS[d]
        # v/n matches run_jev.py:365; (v-1)/(n-1) was the retracted mismatch
        acc += w * (v / n) * 100.0
        tot_w += w
    return (acc / tot_w) if tot_w else None


mine = {}
for p in (HERE / "runs-v18").glob("jev-*.json"):
    r = json.loads(p.read_text())
    disp = r.get("dimensions_display_1to5") or {}
    un = set(r.get("dimensions_unscored") or [])
    mine[r["case"]] = {"dims": {k: (None if k in un else disp.get(k)) for k in W},
                       "composite": r.get("composite"),
                       "band": r.get("band")}

print("=" * 90)
print("1. DIMENSION exact vs BAND agreement")
print("=" * 90)
print()
same_band = tot = 0
gap_dist = Counter()
adj_band = 0
ORDER = ["Fragile", "Contested", "Viable, conditional", "Strong"]
mismatches = []
for cid, e in idx["companies"].items():
    r = by.get(e["name"]) or {}
    his = {}
    for d in W:
        v = num(r.get("YOUR_" + ABBR[d]))
        if d == "competitive_room" and v is None:
            v = None
        his[d] = v
    m = mine.get(cid) or {}
    if not any(v is not None for v in his.values()) or not m.get("dims"):
        continue
    hc = composite(his)
    mc = m.get("composite")
    if hc is None or mc is None:
        continue
    hb, mb = band_of(hc), band_of(mc)
    tot += 1
    if hb == mb:
        same_band += 1
    else:
        mismatches.append((e["name"], e["cat"], round(mc, 1), mb, round(hc, 1), hb))
        try:
            if abs(ORDER.index(hb) - ORDER.index(mb)) == 1:
                adj_band += 1
        except ValueError:
            pass
    gap_dist[round(abs(hc - mc))] += 1

print("  cases with both composites computable: %d" % tot)
print("  SAME BAND:            %d  (%.1f%%)" % (same_band, 100 * same_band / tot))
print("  adjacent band:        %d  (%.1f%%)" % (adj_band, 100 * adj_band / tot))
print("  two or more bands apart: %d (%.1f%%)"
      % (tot - same_band - adj_band, 100 * (tot - same_band - adj_band) / tot))
print()
print("  composite gap distribution (|his - mine|):")
for k in sorted(gap_dist)[:14]:
    print("    %2d pts : %d" % (k, gap_dist[k]))
print()
print("  BAND MISMATCHES (%d):" % len(mismatches))
print("  %-32s %-14s %8s %-9s %8s %-9s" % ("company", "category", "myComp", "myBand",
                                          "hisComp", "hisBand"))
for nm, cat, mc, mb, hc, hb in sorted(mismatches, key=lambda x: -abs(x[4] - x[2]))[:20]:
    print("  %-32s %-14s %8.1f %-9s %8.1f %-9s" % (nm[:31], cat[:13], mc, mb, hc, hb))
