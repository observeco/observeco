"""CAN WE BE MORE ROBUST THAN GARTNER/MBB? Test the aggregation rule, not the data.

Sean: "We do not have to be precise about reconciliation. There is definitely going to be
discrepancies amongst various sources and methodologies. We just have to develop our own robust
way and be consistent throughout all cases is where I am leading towards. Is there a way we can
do this better than the MBBs, Gartner and equivalent?"

He is right that precision is the wrong target. The right target is STABILITY: the same
business must produce the same verdict, and the verdict must not flip on noise.

WHERE AN ANALYST FIRM CANNOT FOLLOW US:
  Gartner/IDC/MBB size a market by summing vendors, then hand-assign each vendor's REVENUE,
  its GEOGRAPHIC SPLIT, its SEGMENT ATTRIBUTION, and the UNTRACKED TAIL -- by analyst judgment.
  Those five allocations are all judgment, they are revised yearly ("definitions and
  assumptions are revised on a yearly basis"), and they are NEVER released as a distribution.
  So a client cannot see the uncertainty, and a competitor cannot reproduce the number.
  The published figure is a POINT. Reproducibility is impossible by construction.

WHAT WE CAN DO THAT THEY CANNOT: carry the uncertainty THROUGH the arithmetic and publish it.
That is only possible if the aggregation rule is stable enough that uncertainty does not
compound into verdict flips.

SO: measure the aggregation rule itself.
  * composite = sum over scored dims of (display_level / level_count * renormalised_weight)
    -- i.e. the model's CONTINUOUS judgment is ROUNDED TO AN INTEGER LEVEL, then weighted.
  * The rounding is the suspected variance amplifier: at a boundary, raw 1.95 -> level 2 and
    raw 2.05 -> level 3, a whole level = ~4-5 composite points, from a raw gap of 0.10.

MEASURED NOISE (from earlier repeat runs): raw sigma ~ 0.08 on the 0-4 scale.
"""
import json
import random
from pathlib import Path

HERE = Path(__file__).resolve().parent
random.seed(20260925)

RUBRIC = json.loads((HERE / "rubric.json").read_text())
META = RUBRIC["_meta"]
W = META["weights"]
COUNTS = META["level_counts"]
FLOORS = {k: v for k, v in META["gates"].items() if not k.startswith("_")}
BANDS = META["bands"]

SIGMA = 0.08          # measured raw-score noise, 0-4 scale
NOISE_PP = SIGMA / 4  # as a fraction of the 0-4 scale


def band_of(c):
    for name, lo, hi in BANDS:
        if lo <= c <= hi:
            return name
    raise SystemExit(f"composite {c} outside bands")


def composite_from_levels(levels, unscored=()):
    """CURRENT rule: integer display level / level_count, x renormalised weight."""
    scored = [k for k in W if k not in unscored]
    tw = sum(W[k] for k in scored)
    return round(sum(levels[k] / COUNTS[k] * (W[k] / tw * 100) for k in scored))


def composite_from_raw(raws, unscored=()):
    """PROPOSED: continuous raw / 4, x renormalised weight. No quantization step."""
    scored = [k for k in W if k not in unscored]
    tw = sum(W[k] for k in scored)
    return round(sum(max(0.0, min(4.0, raws[k])) / 4 * (W[k] / tw * 100)
                     for k in scored))


def gate_fires_levels(levels):
    return [k for k in FLOORS if levels.get(k) is not None and levels[k] < FLOORS[k]]


def gate_fires_raw(raws):
    """Gate on the RAW judgment, with a stated margin instead of a rounding cliff."""
    return [k for k in FLOORS
            if raws.get(k) is not None and raws[k] < (FLOORS[k] - 1) + 0.25]


# ---------------------------------------------------------------- real cases
runs = {}
for f in sorted((HERE / "runs").glob("jev-*.json")):
    try:
        x = json.loads(f.read_text())
    except Exception:
        continue
    if "raw_jev_scores_0to4" in x:
        runs[x["case"]] = x

print("=" * 84)
print("THE AGGREGATION RULE IS THE VARIANCE AMPLIFIER -- not the data")
print("=" * 84)
print(f"  rubric {META['version']} | measured raw noise sigma = {SIGMA} (0-4 scale)")
print(f"  cases with raw scores on disk: {len(runs)}")
print()

# Verify the formula reproduces recorded composites before changing anything.
print("STEP 1 -- verify the current rule reproduces the recorded composite")
print("-" * 84)
print(f"  {'case':24}{'recorded':>9}{'recomputed':>12}{'  match'}")
bad = 0
for case, x in sorted(runs.items()):
    lv = x.get("dimensions_display_1to5", {})
    unscored = tuple(k for k in W if lv.get(k) is None)
    levels = {k: lv[k] for k in W if lv.get(k) is not None}
    if not levels:
        continue
    rec = x.get("composite")
    got = None if gate_fires_levels(levels) else composite_from_levels(levels, unscored)
    ok = "yes" if rec == got else "NO"
    if rec != got:
        bad += 1
    print(f"  {case:24}{str(rec):>9}{str(got):>12}  {ok}")
print(f"  mismatches: {bad}")

# ---------------------------------------------------------------- perturbation
print()
print("=" * 84)
print("STEP 2 -- perturb every raw score by N(0, sigma) and count VERDICT FLIPS")
print("=" * 84)
print("  A 'verdict flip' = the BAND the client sees changes, or the GATE toggles.")
print("  That is what actually damages a lead magnet -- not a few points of score.")
print()

TRIALS = 4000
rows = []
for case, x in sorted(runs.items()):
    raws = {k: v for k, v in x.get("raw_jev_scores_0to4", {}).items() if v is not None}
    if len(raws) < 3:
        continue
    unscored = tuple(k for k in W if k not in raws)

    # baseline, both rules
    base_lv = None if gate_fires_levels(x["dimensions_display_1to5"]) else \
        composite_from_levels(x["dimensions_display_1to5"], unscored)
    base_raw = None if gate_fires_raw(raws) else composite_from_raw(raws, unscored)
    base_lv_band = None if base_lv is None else band_of(base_lv)
    base_raw_band = None if base_raw is None else band_of(base_raw)

    lv_flips = raw_flips = 0
    lv_vals, raw_vals = [], []
    for _ in range(TRIALS):
        p = {k: v + random.gauss(0, SIGMA) for k, v in raws.items()}
        # current rule: perturb, then ROUND TO INTEGER LEVEL (this is the amplifier)
        plv = {}
        for k, v in p.items():
            n = COUNTS[k]
            lv = int(round(max(0.0, min(4.0, v)) / 4 * n))
            plv[k] = max(1, min(n, lv))
        if gate_fires_levels(plv):
            c_lv = None
        else:
            c_lv = composite_from_levels(plv, unscored)
            lv_vals.append(c_lv)
        if (c_lv is None) != (base_lv is None):
            lv_flips += 1
        elif c_lv is not None and band_of(c_lv) != base_lv_band:
            lv_flips += 1

        # proposed rule: continuous raw, no quantization
        if gate_fires_raw(p):
            c_raw = None
        else:
            c_raw = composite_from_raw(p, unscored)
            raw_vals.append(c_raw)
        if (c_raw is None) != (base_raw is None):
            raw_flips += 1
        elif c_raw is not None and band_of(c_raw) != base_raw_band:
            raw_flips += 1

    def sd(v):
        if len(v) < 2:
            return 0.0
        m = sum(v) / len(v)
        return (sum((x - m) ** 2 for x in v) / (len(v) - 1)) ** 0.5

    rows.append((case, base_lv, base_lv_band, sd(lv_vals), lv_flips / TRIALS,
                 base_raw, base_raw_band, sd(raw_vals), raw_flips / TRIALS))

print(f"  {'case':22}{'band':18}{'CURRENT flip%':>14}{'PROPOSED flip%':>15}{'improve':>9}")
print("  " + "-" * 78)
tot_lv = tot_raw = 0
for (case, bl, bb, sl, fl, br, bb2, sr, fr) in rows:
    tot_lv += fl
    tot_raw += fr
    imp = "n/a" if fl == 0 else f"{fl/max(fr,1e-9):.1f}x"
    print(f"  {case:22}{str(bb)[:17]:18}{fl*100:>13.1f}%{fr*100:>14.1f}%{imp:>9}")
n = max(len(rows), 1)
print("  " + "-" * 78)
print(f"  {'MEAN':22}{'':18}{tot_lv/n*100:>13.1f}%{tot_raw/n*100:>14.1f}%"
      f"{(tot_lv/max(tot_raw,1e-9)):>8.1f}x")

print()
print("  composite standard deviation under perturbation (points):")
print(f"  {'case':22}{'CURRENT sd':>12}{'PROPOSED sd':>13}{'reduction':>11}")
for (case, bl, bb, sl, fl, br, bb2, sr, fr) in rows:
    red = "n/a" if sl == 0 else f"{sl/max(sr,1e-9):.1f}x"
    print(f"  {case:22}{sl:>12.2f}{sr:>13.2f}{red:>11}")
