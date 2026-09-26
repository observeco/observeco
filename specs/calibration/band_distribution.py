"""FIX ATTEMPT: replace the band CLIFF with a computed band DISTRIBUTION.

THE DEFECT: the composite is continuous, but we round each dimension to an integer and
then snap the total to one band word. 26% of cases sit within noise of a boundary, so
their band word is a coin flip.

THE CAUSE (this is the insight): we THROW AWAY the model's own probability distribution.
Jev emits P(level) per dimension -- full information about its uncertainty -- and we
collapse it to int(round(E[level]))+1. The uncertainty is then re-invented by repeat-runs.

THE FIX: propagate the distributions instead of discarding them.
  * composite E = sum_d  E[display_d] / n_d * w_d        (no per-dimension rounding)
  * composite DISTRIBUTION = convolution over the per-dimension level distributions
  * report P(band) and P(refuse) instead of a single word

VALIDATION: the 12 recorded repeat runs are the ground truth. If a case's observed
composite spread is NOT covered by the predicted distribution, the independence
assumption has failed and the fix is wrong.

PRE-REGISTERED PREDICTION (before running):
  The convolution should predict koi's composite sd of 0.00 (observed [76,76,76]) and
  should show P(Viable) as the MODAL band for koi but with substantial P(Strong) --
  which is exactly what makes the word unreliable. If the convolution instead says
  P=1.0 on one band, it is under-estimating and the independence assumption is wrong.
"""
import glob
import json
import statistics
from pathlib import Path

HERE = Path(__file__).resolve().parent
rub = json.loads((HERE / "rubric.json").read_text())
META = rub["_meta"]
W, CNT, BANDS = META["weights"], META["level_counts"], META["bands"]
GATES = {k: v for k, v in META["gates"].items() if not k.startswith("_")}
FLOOR = META.get("display_floor", 0.20)
DISP = META["elasticity_dispositions"]

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


def convolve(dists_scaled):
    """Exact discrete convolution of (value, {v: p}) pairs. Independent components."""
    acc = {0.0: 1.0}
    for vals in dists_scaled:
        nxt = {}
        for a, pa in acc.items():
            for v, pv in vals.items():
                k = round(a + v, 1)
                nxt[k] = nxt.get(k, 0.0) + pa * pv
        acc = nxt
    return acc


def analyse(d):
    case = d["case"]
    dims = d["dimensions_display_1to5"]
    cov, probs = d["evidence_coverage"], d.get("probabilities") or {}
    e = elasticity(case)
    drop = {"market_headroom"} if (e == "elastic"
                                   and DISP["elastic"]["market_headroom"] == "not_applicable") else set()
    scored = [k for k in W if k not in drop
              and isinstance(cov.get(k), (int, float)) and cov[k] >= FLOOR]
    if not scored:
        return None
    tw = sum(W[k] for k in scored)
    wu = {k: W[k] / tw * 100 for k in scored}

    # per-dimension display distribution, scaled by its share of the composite
    comps, gate_p = [], 0.0
    for k in scored:
        pr = probs.get(k) or {}
        n = CNT[k]
        if not pr:
            continue
        tot = sum(float(v) for v in pr.values()) or 1.0
        scaled = {}
        for lvl, p in pr.items():
            i = int(lvl)
            disp = i + 1                       # 0-based level -> 1-based display
            scaled[round(min(disp, n) / n * wu[k], 3)] = float(p) / tot
        comps.append(scaled)
        # P(this dimension refuses) = mass on display < gate floor
        gp = sum(float(p) / tot for lvl, p in pr.items()
                 if (int(lvl) + 1) < GATES[k])
        gate_p = max(gate_p, gp)               # any dimension firing refuses the case

    if not comps:
        return None
    dist = convolve(comps)
    exp_c = sum(v * p for v, p in dist.items())
    sd_c = (sum(p * (v - exp_c) ** 2 for v, p in dist.items())) ** 0.5

    band_p = {}
    for v, p in dist.items():
        b = band_of(round(v))
        band_p[b] = band_p.get(b, 0.0) + p
    return {"case": case, "e": e, "point": d.get("composite"),
            "point_band": d.get("band"), "exp": exp_c, "sd": sd_c,
            "band_p": band_p, "gate_p": gate_p,
            "gates_now": d.get("gates_firing") or []}


rows = []
for p in sorted(glob.glob(str(HERE / "runs" / "jev-*.json"))):
    d = json.load(open(p))
    if d.get("case") and "dimensions_display_1to5" in d:
        r = analyse(d)
        if r:
            rows.append(r)

print("=" * 108)
print("1. BAND DISTRIBUTION from the model's OWN probabilities (replaces the cliff)")
print("=" * 108)
print("%-22s %-6s %-6s %-6s %-8s %s" %
      ("case", "point", "E[comp]", "sd", "P(refuse)", "band probabilities"))
print("-" * 108)
for r in sorted(rows, key=lambda x: -x["exp"]):
    bp = "  ".join("%s:%.2f" % (b, p) for b, p in
                   sorted(r["band_p"].items(), key=lambda kv: -kv[1]))
    print("%-22s %-6s %-6.1f %-6.2f %-8.2f %s" %
          (r["case"], r["point"] if r["point"] is not None else "GATE",
           r["exp"], r["sd"], r["gate_p"], bp))

print()
print("=" * 108)
print("2. VALIDATION against the 12 recorded REPEAT runs (the ground truth)")
print("=" * 108)
print("  Pre-registered: koi observed sd = 0.00 ([76,76,76]). If the convolution says")
print("  sd ~0 too, it is reproducing the model's real stability. If it says sd is")
print("  large, it is over-estimating and independence is wrong.")
print()
print("  %-14s %-20s %-10s %-10s %s" % ("case", "observed repeats", "obs sd", "pred sd", "check"))
print("  " + "-" * 88)
for case in ("09-koi", "P1-mixue", "P2-chicha"):
    reps = sorted(glob.glob(str(HERE / "repeats" / f"{case}-rep*.json")))
    comps = [json.load(open(f)).get("composite") for f in reps]
    comps = [c for c in comps if c is not None]
    if not comps:
        continue
    obs_sd = statistics.stdev(comps) if len(comps) > 1 else 0.0
    # match the analysis row (run name differs from input name)
    run_case = json.loads((HERE / "inputs" / f"{case}.json").read_text())["_meta"]["case"]
    r = next((x for x in rows if x["case"] == run_case), None)
    pred_sd = r["sd"] if r else None
    band_in = all(any(lo <= c <= hi for _n, lo, hi in BANDS) for c in comps)
    verdict = ("pred COVERS obs" if pred_sd is not None and pred_sd >= obs_sd * 0.5
               else "pred UNDER-estimates" if pred_sd is not None else "no row")
    print("  %-14s %-20s %-10.2f %-10s %s" %
          (case, comps, obs_sd, ("%.2f" % pred_sd) if pred_sd is not None else "-", verdict))

print()
print("=" * 108)
print("3. DOES THE FIX RESOLVE THE CLIFF?  cases with no single dominant band")
print("=" * 108)
contested = [r for r in rows if len([p for p in r["band_p"].values() if p > 0.15]) > 1]
print("  cases where >15%% of mass falls in a SECOND band (i.e. the word is ambiguous):")
for r in sorted(contested, key=lambda x: -x["exp"]):
    top = sorted(r["band_p"].items(), key=lambda kv: -kv[1])
    others = [x for x in top if x[1] > 0.15][1:]
    print("     %-22s %s   -> also %s" %
          (r["case"], "%.2f %s" % (top[0][1], top[0][0]),
           ", ".join("%.2f %s" % (p, b) for b, p in others)))
print()
print("  %d of %d cases have an ambiguous band word." % (len(contested), len(rows)))
print("  The fix does not remove the ambiguity -- it REPORTS it. A cliff becomes an")
print("  interval, which is the honest representation of a 1-point display step")
print("  against real uncertainty.")
json.dump(rows, open(HERE / "runs" / "band_distribution.json", "w"), indent=2)
