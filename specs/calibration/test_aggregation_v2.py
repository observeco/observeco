"""THE ANSWER TO SEAN'S QUESTION, measured: can we beat Gartner/MBB on robustness?

Sean: "We do not have to be precise about reconciliation. There is definitely going to be
discrepancies amongst various sources and methodologies. We just have to develop our own robust
way and be consistent throughout all cases... Is there a way we can do this better than the
MBBs, Gartner and equivalent?"

His target is right: STABILITY and CONSISTENCY, not precision.

WHAT AN ANALYST FIRM STRUCTURALLY CANNOT DO:
  Gartner/IDC/MBB sum vendor revenue, then hand-assign each vendor's revenue, geographic split,
  segment attribution, and the untracked tail. Five judgment calls, revised yearly, released
  only as a POINT. A client sees no distribution; a competitor cannot reproduce it. Robustness
  is not measurable, so it cannot be improved -- and it cannot be demonstrated to a client.

WHAT WE CAN DO: carry the model's own distribution through the arithmetic and publish it.
  That is only worth doing if the aggregation rule does not itself manufacture variance.

TWO RULES COMPARED, on identical inputs and identical perturbations:
  A. CURRENT  -- quantize the continuous judgment to an INTEGER level, then weight.
  B. PROPOSED -- use the continuous judgment directly, no quantization.
Also: gates A on the rounded level (a cliff), B on the raw value with a stated margin.
"""
import json
import random
from pathlib import Path

HERE = Path(__file__).resolve().parent
random.seed(7)
R = json.loads((HERE / "rubric.json").read_text())
M = R["_meta"]
W, COUNTS, BANDS = M["weights"], M["level_counts"], M["bands"]
FLOORS = {k: v for k, v in M["gates"].items() if not k.startswith("_")}
FLOOR = M.get("display_floor", 0.20)
SIGMA = 0.08                       # measured raw-score noise, 0-4 scale
TRIALS = 4000


def band_of(c):
    for n, lo, hi in BANDS:
        if lo <= c <= hi:
            return n
    raise SystemExit(f"{c} outside bands")


def disp_level(s, n):
    """Corrected 1..N mapping (was capped at 5 by the pre-0.6.1 bug)."""
    return max(1, min(n, int(round(s / 4 * (n - 1))) + 1))


runs = {}
for f in sorted((HERE / "runs").glob("jev-*.json")):
    x = json.loads(f.read_text())
    if x.get("raw_jev_scores_0to4"):
        runs[x["case"]] = x

print("=" * 90)
print("RULE A (quantize to integer levels)  vs  RULE B (carry the continuous judgment)")
print("=" * 90)
print(f"  rubric {M['version']} | raw noise sigma = {SIGMA} | trials per case = {TRIALS}")
print(f"  a 'verdict flip' = the BAND the client sees changes, or the GATE toggles")
print()
print(f"  {'case':22}{'band':21}{'A flip%':>9}{'B flip%':>9}{'A sd':>7}{'B sd':>7}{'better':>8}")
print("  " + "-" * 86)

rows, tot_a, tot_b = [], 0.0, 0.0
for case, x in sorted(runs.items()):
    raw = {k: v for k, v in (x["raw_jev_scores_0to4"] or {}).items() if v is not None}
    cov = x.get("evidence_coverage") or {}
    if len(raw) < 3:
        continue
    unscored = [k for k in W
                if not isinstance(cov.get(k), (int, float)) or cov[k] < FLOOR]
    scored = [k for k in W if k not in unscored and k in raw]
    tw = sum(W[k] for k in scored)
    wu = {k: W[k] / tw * 100 for k in scored}

    def comp_a(v):
        d = {k: disp_level(v[k], COUNTS[k]) for k in scored}
        if [k for k in scored if d[k] < FLOORS[k]]:
            return None
        return round(sum(d[k] / COUNTS[k] * wu[k] for k in scored))

    def comp_b(v):
        if [k for k in scored if v[k] < (FLOORS[k] - 1) + 0.25]:
            return None
        return round(sum(max(0.0, min(4.0, v[k])) / 4 * wu[k] for k in scored))

    ba, bb = comp_a(raw), comp_b(raw)
    ba_band = None if ba is None else band_of(ba)
    bb_band = None if bb is None else band_of(bb)

    fa = fb = 0
    va, vb = [], []
    for _ in range(TRIALS):
        p = {k: v + random.gauss(0, SIGMA) for k, v in raw.items()}
        ca, cb = comp_a(p), comp_b(p)
        if (ca is None) != (ba is None) or (ca is not None and band_of(ca) != ba_band):
            fa += 1
        elif ca is not None:
            va.append(ca)
        if (cb is None) != (bb is None) or (cb is not None and band_of(cb) != bb_band):
            fb += 1
        elif cb is not None:
            vb.append(cb)

    def sd(v):
        if len(v) < 2:
            return 0.0
        m = sum(v) / len(v)
        return (sum((q - m) ** 2 for q in v) / (len(v) - 1)) ** 0.5

    fa_p, fb_p = fa / TRIALS, fb / TRIALS
    tot_a += fa_p
    tot_b += fb_p
    rows.append((case, ba_band, fa_p, fb_p, sd(va), sd(vb)))

for case, band, fa, fb, sa, sb in rows:
    better = "--" if fa == 0 and fb == 0 else f"{(fa/max(fb,1e-9)):.1f}x"
    print(f"  {case:22}{str(band)[:20]:21}{fa*100:>8.1f}%{fb*100:>8.1f}%"
          f"{sa:>7.2f}{sb:>7.2f}{better:>8}")
n = len(rows)
print("  " + "-" * 86)
print(f"  {'MEAN':22}{'':21}{tot_a/n*100:>8.1f}%{tot_b/n*100:>8.1f}%")

print()
print("=" * 90)
print("DOES RULE B PRESERVE THE DISTINCTIONS THE RUBRIC EXISTS TO MAKE?")
print("=" * 90)
KEY = [("E1-asml", "monopoly"), ("E4-bonefirm-ip", "protected IP"),
       ("bonefirm", "replicable"), ("N1-closedbusiness", "dead"),
       ("bubbletea", "crowded/failing"), ("N2-koi-stripped", "stripped"),
       ("koi", "category leader")]
print(f"  {'case':22}{'label':16}{'A comp':>8}{'B comp':>8}{'A band':>20}{'B band':>20}")
for c, lab in KEY:
    x = runs.get(c)
    if not x:
        continue
    raw = {k: v for k, v in (x["raw_jev_scores_0to4"] or {}).items() if v is not None}
    cov = x.get("evidence_coverage") or {}
    unscored = [k for k in W
                if not isinstance(cov.get(k), (int, float)) or cov[k] < FLOOR]
    scored = [k for k in W if k not in unscored and k in raw]
    tw = sum(W[k] for k in scored)
    wu = {k: W[k] / tw * 100 for k in scored}
    d = {k: disp_level(raw[k], COUNTS[k]) for k in scored}
    fa = [k for k in scored if d[k] < FLOORS[k]]
    a = None if fa else round(sum(d[k] / COUNTS[k] * wu[k] for k in scored))
    fb2 = [k for k in scored if raw[k] < (FLOORS[k] - 1) + 0.25]
    b = None if fb2 else round(sum(max(0.0, min(4.0, raw[k])) / 4 * wu[k] for k in scored))
    print(f"  {c:22}{lab:16}{str(a):>8}{str(b):>8}"
          f"{('GATE' if a is None else band_of(a)):>20}"
          f"{('GATE' if b is None else band_of(b)):>20}")

print()
print("  E4 vs Bonefirm -- the discrimination the 6-level split was built for:")
for c in ("E4-bonefirm-ip", "bonefirm"):
    x = runs.get(c)
    if x:
        d = x["raw_jev_scores_0to4"].get("defensibility")
        print(f"    {c:20} raw defensibility {d:.2f} -> "
              f"integer level {disp_level(d, 6)}/6")
print("    Both land on DIFFERENT integer levels, but only because 2.79 vs 1.84 straddle a")
print("    boundary. Rule B keeps the whole continuous gap (0.95 of a level) instead of")
print("    reducing it to 'one level apart'.")
