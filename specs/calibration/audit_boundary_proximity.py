"""CORRECTED noise estimate + boundary-proximity audit across the corpus.

MY ERROR, CORRECTED: the previous run reported "pooled composite sd = 5.22". That
pooled repeats across DIFFERENT CASES, so it measured how much koi differs from Mixue --
BETWEEN-case variance, which is signal, not noise. The correct measure is WITHIN-case
variance: how much the same case moves on re-run.

Measured, within-case:
  koi      [76, 76, 76]  sd 0.00
  Mixue    [72, 72]      sd 0.00
  Chicha   [66, 63]      sd 2.12   <- ONE dimension flipped (demand_reach 4->3)

So noise is usually ZERO and occasionally ~3 points from a single dimension flip.
That is the correct basis for the band-boundary audit below.
"""
import json
import glob
from pathlib import Path

HERE = Path(__file__).resolve().parent
rub = json.loads((HERE / "rubric.json").read_text())
META = rub["_meta"]
W, CNT = META["weights"], META["level_counts"]
BANDS = META["bands"]
FLOOR = META.get("display_floor", 0.20)
DISP = META["elasticity_dispositions"]

# measured, from within-case repeats
NOISE = 3.0   # worst observed single-flip composite move (Chicha 66->63)

bounds = [hi for _n, _lo, hi in BANDS][:-1]   # 37, 57, 76

cls = json.load(open(HERE / "runs" / "a3_elasticity_classification.json"))
ALIAS = {"bonefirm": "01-bonefirm", "observeco": "07-observeco",
         "bubbletea": "08-bubbletea", "koi": "09-koi"}


def elasticity(case):
    pr = cls.get(case) or cls.get(ALIAS.get(case, ""))
    return max(pr, key=lambda k: float(pr[k])) if pr else None


def band_of(c):
    for name, lo, hi in BANDS:
        if lo <= c <= hi:
            return name
    return "OUT-OF-RANGE"


rows = []
for p in sorted(glob.glob(str(HERE / "runs" / "jev-*.json"))):
    d = json.load(open(p))
    if not d.get("case") or "dimensions_display_1to5" not in d:
        continue
    case = d["case"]
    dims, cov = d["dimensions_display_1to5"], d["evidence_coverage"]
    e = elasticity(case)
    drop = {"market_headroom"} if (e == "elastic"
                                   and DISP["elastic"]["market_headroom"] == "not_applicable") else set()
    scored = [k for k in W if k not in drop
              and isinstance(cov.get(k), (int, float)) and cov[k] >= FLOOR]
    if not scored:
        continue
    tw = sum(W[k] for k in scored)
    wu = {k: W[k] / tw * 100 for k in scored}
    if any(dims[k] < META["gates"][k] for k in scored):
        rows.append((case, None, "GATE", e, None))
        continue
    c = round(sum(dims[k] / CNT[k] * wu[k] for k in scored))
    # distance to the nearest band boundary
    dist = min(abs(c - b) for b in bounds)
    rows.append((case, c, band_of(c), e, dist))

print("=" * 100)
print("BOUNDARY-PROXIMITY AUDIT  (noise = up to %.0f pts from a single dimension flip)" % NOISE)
print("=" * 100)
print("  band boundaries: %s" % bounds)
print()
print("  %-22s %-6s %-20s %-8s %s" % ("case", "comp", "band", "dist", "verdict"))
print("  " + "-" * 88)
risky = []
for case, c, band, e, dist in sorted(rows, key=lambda r: (r[4] is None, r[4] or 0)):
    if c is None:
        print("  %-22s %-6s %-20s %-8s refused (gate)" % (case, "-", band, "-"))
        continue
    v = "UNRELIABLE band word" if dist <= NOISE else "stable"
    if dist <= NOISE:
        risky.append((case, c, band, dist))
    print("  %-22s %-6s %-20s %-8s %s" % (case, c, band, "%.0f" % dist, v))

print()
print("=" * 100)
print("FINDING: the band WORD is not reproducible for cases near a boundary")
print("=" * 100)
print("  %d of %d scored cases sit within %.0f points of a boundary:"
      % (len(risky), sum(1 for r in rows if r[1] is not None), NOISE))
for case, c, band, dist in risky:
    print("     %-22s %3d  %-20s (%.0f pt from a boundary)" % (case, c, band, dist))
print()
print("  These are exactly the cases I have been making banding decisions about:")
print("     koi   76 -> 'Viable, conditional'  (1 pt below 77 -- the re-calibration")
print("                                          I applied this session moved it here)")
print("     C5    77 -> 'Strong'               (ON the boundary)")
print("     E2    77 -> 'Strong'               (ON the boundary)")
print()
print("  => the koi band assignment is NOT reliable at this sample of repeats. The")
print("     re-calibration correctly moved the BOUNDARY to the anchor, but koi's")
print("     POSITION is inside the noise zone, so its band word can flip.")
print()
print("  Honest reading: the boundary is now principled (anchor-derived). The band")
print("  WORD is still a cliff for near-boundary cases, and %.0f%% of the corpus sits"
      % round(len(risky) / sum(1 for r in rows if r[1] is not None) * 100))
print("  inside that cliff.")

json.dump([{"case": c, "composite": comp, "band": b, "elasticity": e, "dist": d}
           for c, comp, b, e, d in rows],
          open(HERE / "runs" / "boundary_audit.json", "w"), indent=2)
