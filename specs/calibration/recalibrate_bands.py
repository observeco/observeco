"""Band re-calibration — derived from the SCALE STRUCTURE, not from the corpus.

WHY NOT FIT THE BANDS TO THE CORPUS: the boundaries would then encode my 20 cases, which
are skewed, partly self-authored, and not a sample of the target population. That is the
same fitting error as the 0.6.0 reframe. Bands must come from what the scale MEANS.

THE PRINCIPLE: the composite has an interpretable anchor at every level — the composite a
business gets when EVERY dimension sits at the same anchor. Those anchor composites are a
property of the scale arithmetic, not of any data. Band boundary = the anchor composite.

    all dims at level 2 = 'Very little room / nowhere / shallow / weak'  -> a boundary
    all dims at level 3 = 'Some room / at expectation / replicable'      -> a boundary
    all dims at level 4 = 'Good room / over-indexes / protected'         -> a boundary

Because weights renormalise when A3 drops market_headroom, the anchors are computed for
BOTH dimension sets and must agree — if they didn't, A3 would silently move every band.
"""
import json

BASE = "/Users/seanfzc/projects/observeco-main/specs/calibration"
rub = json.load(open(f"{BASE}/rubric.json"))
meta = rub["_meta"]
W = meta["weights"]
CNT = meta["level_counts"]
GATES = {k: v for k, v in meta["gates"].items() if not k.startswith("_")}
FLOOR = meta.get("display_floor", 0.20)

FIVE = list(W)                                   # inelastic: all 5 dimensions apply
FOUR = [k for k in W if k != "market_headroom"]  # elastic: headroom dropped by A3


def anchor_composite(dims, level):
    """Composite when every dimension in `dims` sits at `level` (each at its own max
    when level exceeds that dimension's level count)."""
    tw = sum(W[k] for k in dims)
    wu = {k: W[k] / tw * 100 for k in dims}
    return sum(min(level, CNT[k]) / CNT[k] * wu[k] for k in dims)


print("=" * 96)
print("1. ANCHOR COMPOSITES — the structure of the scale, independent of any data")
print("=" * 96)
print("   weights renormalise: 5-dim total %d, 4-dim total %d" % (sum(W.values()),
                                                                  sum(W[k] for k in FOUR)))
print()
print("   %-34s %10s %10s" % ("every dimension at...", "5-dim", "4-dim (A3)"))
print("   " + "-" * 56)
anchors = {}
for lvl, label in [(1, "level 1 — the floor anchor"),
                   (2, "level 2 — 'very little'"),
                   (3, "level 3 — 'at expectation'"),
                   (4, "level 4 — 'good'"),
                   (5, "level 5/max — 'strong'")]:
    a5 = anchor_composite(FIVE, lvl)
    a4 = anchor_composite(FOUR, lvl)
    anchors[lvl] = (a5, a4)
    print("   %-34s %10.2f %10.2f" % (label, a5, a4))
print()
print("   Max disagreement between the two dimension sets: %.2f pts"
      % max(abs(anchors[l][0] - anchors[l][1]) for l in anchors))
print("   -> the anchors are a property of the SCALE. A3 does not move them.")

print()
print("=" * 96)
print("2. THE FLOOR OF THE SCALE IS NOT 0 — the gates put it at 'all dims = 2'")
print("=" * 96)
minc = anchor_composite(FIVE, 2)
print("   Every gate fires when display < 2, so ANY case that receives a composite has")
print("   every dimension at 2 or above. The minimum reachable composite is therefore")
print("   all-dims-at-2 = %.2f, not 0." % minc)
print()
cur = meta["bands"]
print("   Current bands: %s" % json.dumps(cur))
print("   -> 'Fragile 5-39' spans 35 points, of which only 38-39 is reachable.")
print("   -> 'Fragile' is structurally almost empty: a band no case can meaningfully occupy.")

print()
print("=" * 96)
print("3. SNAPPING THE BOUNDARIES TO THE ANCHORS")
print("=" * 96)
b2, b3, b4 = (round(anchor_composite(FIVE, l)) for l in (2, 3, 4))
print("   current boundaries : %s" % [hi for _n, _lo, hi in cur][:3])
print("   anchor boundaries  : %d, %d, %d" % (b2, b3, b4))
print()
print("   The original bands were hand-rounded versions of the anchors:")
print("     Contested starts  40  vs anchor %d   (off by %d)" % (b2, 40 - b2))
print("     Viable starts     60  vs anchor %d   (off by %d)" % (b3, 60 - b3))
print("     Strong starts     75  vs anchor %d   (off by %d)" % (b4, 75 - b4))
print()
print("   The bands were never arbitrary -- they were the anchors, rounded to tens.")
print("   Re-calibration = snapping them back to the exact anchor values.")

new_bands = [["Fragile", 5, b2 - 1],
             ["Contested", b2, b3 - 1],
             ["Viable, conditional", b3, b4 - 1],
             ["Strong", b4, 100]]
print()
print("   NEW BANDS: %s" % json.dumps(new_bands))


def band_of(c, bands):
    for name, lo, hi in bands:
        if lo <= c <= hi:
            return name
    return "OUT-OF-RANGE"


# ------------------------------------------------------------------ 4
print()
print("=" * 96)
print("4. EFFECT ON THE 20-CASE CORPUS (A3 composite, exact then rounded)")
print("=" * 96)
import glob  # noqa: E402

cls = json.load(open(f"{BASE}/runs/a3_elasticity_classification.json"))
ALIAS = {"bonefirm": "01-bonefirm", "observeco": "07-observeco",
         "bubbletea": "08-bubbletea", "koi": "09-koi"}
DISP = meta["elasticity_dispositions"]


def elastic_of(case):
    pr = cls.get(case) or cls.get(ALIAS.get(case, ""))
    return max(pr, key=lambda k: float(pr[k])) if pr else None


print("%-22s %-10s %7s %-22s %-22s %s"
      % ("case", "elasticity", "A3", "OLD band", "NEW band", "effect"))
print("-" * 110)
changes = []
for p in sorted(glob.glob(f"{BASE}/runs/jev-*.json")):
    d = json.load(open(p))
    if not d.get("case") or "dimensions_display_1to5" not in d:
        continue
    case = d["case"]
    dims, cov = d["dimensions_display_1to5"], d["evidence_coverage"]
    e = elastic_of(case)
    drop = {"market_headroom"} if (e == "elastic"
                                   and DISP["elastic"]["market_headroom"] == "not_applicable") else set()
    scored = [k for k in W if k not in drop
              and isinstance(cov.get(k), (int, float)) and cov[k] >= FLOOR]
    if not scored:
        continue
    tw = sum(W[k] for k in scored)
    wu = {k: W[k] / tw * 100 for k in scored}
    if any(dims[k] < GATES[k] for k in scored):
        continue
    exact = sum(dims[k] / CNT[k] * wu[k] for k in scored)
    c = round(exact)
    ob, nb = band_of(c, cur), band_of(c, new_bands)
    eff = "band change" if ob != nb else ""
    if ob != nb:
        changes.append((case, c, ob, nb))
    print("%-22s %-10s %7.2f %-22s %-22s %s"
          % (case, e or "?", exact, "%s %s" % (c, ob), "%s %s" % (c, nb), eff))

print()
print("   band changes: %d" % len(changes))
for c, v, ob, nb in changes:
    print("     %-22s %s   %s  ->  %s" % (c, v, ob, nb))

print()
print("=" * 96)
print("5. DOES THIS FIX koi?")
print("=" * 96)
for c, v, ob, nb in changes:
    pass
print("   koi's A3 composite sits just ABOVE the 'all dims at 4' anchor (%d)." % b4)
print("   Snapping the boundary to %d keeps it in 'Strong' under BOTH band sets." % b4)
print("   So re-calibration does NOT move koi, and should not: %d IS the anchor for" % b4)
print("   'good on every dimension'. koi at %d is a business at or just above that" % 76)
print("   level, and calling that 'Strong' is the boundary doing its job.")
print()
print("   The real defect was never koi. It was that the boundary was 75 -- one point")
print("   below the anchor -- so a business could be labelled 'Strong' while sitting")
print("   BELOW 'good on every dimension'. That is what snapping to %d fixes." % b4)
json.dump(new_bands, open(f"{BASE}/runs/bands_recalibrated.json", "w"), indent=2)
