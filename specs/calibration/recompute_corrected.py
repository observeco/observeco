"""Recompute every stored composite under the CORRECTED (reverted) rule, and re-test stability.

Two changes under test, both now justified by evidence rather than assumption:
  1. REVERT my proportional remap. `score` is the expected level INDEX (API contract + all 85
     stored readings agree to 0.03), so `round(score)+1` is the correct 1-based display.
  2. Round HALF-UP instead of Python's banker's rounding. Levels are ordinal; round-half-to-even
     is arbitrary and it corrupted the clearest case (ASML defensibility E[level]=4.51 stored
     4.50 -> banker's gave display 5, the model's own argmax is 6).
"""
import json
import random
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

HERE = Path(__file__).resolve().parent
random.seed(11)
M = json.loads((HERE / "rubric.json").read_text())["_meta"]
W, COUNTS, BANDS = M["weights"], M["level_counts"], M["bands"]
FLOORS = {k: v for k, v in M["gates"].items() if not k.startswith("_")}
FLOOR = M.get("display_floor", 0.20)


def band_of(c):
    for n, lo, hi in BANDS:
        if lo <= c <= hi:
            return n
    raise SystemExit(f"{c} outside bands")


def level_banker(s, n):
    return max(1, min(n, int(round(s)) + 1))


def level_halfup(s, n):
    return max(1, min(n, int(Decimal(str(s)).quantize(Decimal("1"),
                                                      rounding=ROUND_HALF_UP)) + 1))


runs = {}
for f in sorted((HERE / "runs").glob("jev-*.json")):
    x = json.loads(f.read_text())
    if x.get("raw_jev_scores_0to4"):
        runs[x["case"]] = x


def setup(x):
    raw = {k: v for k, v in (x["raw_jev_scores_0to4"] or {}).items() if v is not None}
    cov = x.get("evidence_coverage") or {}
    unscored = [k for k in W
                if not isinstance(cov.get(k), (int, float)) or cov[k] < FLOOR]
    scored = [k for k in W if k not in unscored and k in raw]
    tw = sum(W[k] for k in scored)
    return raw, scored, {k: W[k] / tw * 100 for k in scored}


def comp(raw, scored, wu, lvfn):
    d = {k: lvfn(raw[k], COUNTS[k]) for k in scored}
    if [k for k in scored if d[k] < FLOORS[k]]:
        return None
    return round(sum(d[k] / COUNTS[k] * wu[k] for k in scored))


print("=" * 94)
print("A. WHERE BANKER'S ROUNDING DIFFERED FROM HALF-UP (the only real defect)")
print("=" * 94)
print(f"  {'case':22}{'raw':>7}{'banker':>8}{'half-up':>9}{'argmax':>8}{'  half-up agrees'}")
diff = 0
for case, x in sorted(runs.items()):
    pr = x.get("probabilities") or {}
    raw = x.get("raw_jev_scores_0to4") or {}
    for k, p in pr.items():
        if not isinstance(p, dict) or not p or raw.get(k) is None:
            continue
        s = raw[k]
        n = COUNTS.get(k, 5)
        b, h = level_banker(s, n), level_halfup(s, n)
        if b != h:
            diff += 1
            am = int(max(p.items(), key=lambda kv: kv[1])[0]) + 1
            print(f"  {case[:16]+'/'+k:22}{s:>7.2f}{b:>8}{h:>9}{am:>8}"
                  f"{str(h == am):>16}")
print(f"  readings affected: {diff} of 85")

print()
print("=" * 94)
print("B. LADDER: banker's vs half-up")
print("=" * 94)
print(f"  {'case':22}{'banker':>8}{'band':>22}{'half-up':>9}{'band':>22}{'changed'}")
print("  " + "-" * 90)
rows = []
for case, x in sorted(runs.items()):
    raw, scored, wu = setup(x)
    if len(raw) < 3:
        continue
    cb = comp(raw, scored, wu, level_banker)
    ch = comp(raw, scored, wu, level_halfup)
    bb = "GATE" if cb is None else band_of(cb)
    bh = "GATE" if ch is None else band_of(ch)
    rows.append((case, cb, bb, ch, bh))
    print(f"  {case:22}{str(cb):>8}{bb[:21]:>22}{str(ch):>9}{bh[:21]:>22}"
          f"{('  <-- ' + str(cb) + ' -> ' + str(ch)) if cb != ch else '':>12}")

print()
print("  ladder (half-up), highest first:")
for case, cb, bb, ch, bh in sorted(rows, key=lambda t: -(t[3] or 0)):
    cs = "GATE" if ch is None else str(ch)
    print(f"    {cs:>5}  {bh:22}{case}")

print()
print("=" * 94)
print("C. STABILITY UNDER NOISE (half-up rule, sigma=0.08, 4000 trials)")
print("=" * 94)
SIG = 0.08
T = 4000
print(f"  {'case':22}{'comp':>6}{'band':>22}{'flip%':>8}{'sd':>7}{'margin':>8}"
      f"{'sigma':>7}{'  verdict'}")
print("  " + "-" * 92)
for case, cb, bb, ch, bh in sorted(rows, key=lambda t: -(t[3] or 0)):
    x = runs[case]
    raw, scored, wu = setup(x)
    base = comp(raw, scored, wu, level_halfup)
    if base is None:
        print(f"  {case:22}{'GATE':>6}{'GATE':>22}{'--':>8}{'--':>7}{'--':>8}{'--':>7}"
              f"  stable (gates)")
        continue
    vals, flips = [], 0
    base_band = band_of(base)
    for _ in range(T):
        p = {k: v + random.gauss(0, SIG) for k, v in raw.items()}
        c = comp(p, scored, wu, level_halfup)
        if c is None or band_of(c) != base_band:
            flips += 1
        elif c is not None:
            vals.append(c)
    m = sum(vals) / len(vals) if vals else base
    sd = ((sum((q - m) ** 2 for q in vals) / (len(vals) - 1)) ** 0.5) if len(vals) > 1 else 0.0
    edges = [lo for _n, lo, _h in BANDS] + [hi for _n, _l, hi in BANDS]
    margin = min(abs(base - e) for e in edges if abs(base - e) > 0)
    ratio = margin / sd if sd > 0 else float("inf")
    verdict = "STABLE" if ratio >= 3 else ("watch" if ratio >= 2 else "BORDERLINE")
    print(f"  {case:22}{base:>6}{base_band[:21]:>22}{flips/T*100:>7.1f}%{sd:>7.2f}"
          f"{margin:>8.0f}{ratio:>7.1f}  {verdict}")
