"""CORRECTION OF MY OWN CORRECTION.

I claimed run_jev.py had a bug -- `int(round(s)) + 1` always yielding 1..5 so that
defensibility's level 6 was unreachable -- and "fixed" it by remapping proportionally
onto 1..N. That remap was WRONG. Here is the evidence.

THE MODEL EMITS AN EXPLICIT DISTRIBUTION, and its bin count tells you the dimension's scale:
  defensibility distributions have SIX bins (0..5)
  every other dimension has FIVE bins (0..4)
and the returned `score` is the EXPECTED VALUE over that dimension's own bins.

So `int(round(score)) + 1` -- the ORIGINAL code -- is the correct construction: it maps the
expected value back onto the dimension's own 1..N display scale, and N is 6 for defensibility
and 5 for the rest. My proportional remap stretched a 6-bin expected value onto a 6-point
scale as if it were a 0-4 score, inflating every defensibility reading.
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
COUNTS = json.loads((HERE / "rubric.json").read_text())["_meta"]["level_counts"]


def half_up(v):
    """Round half away from zero -- NOT Python's banker's rounding."""
    import math
    return math.floor(v + 1.5) - 1 if v >= 0 else -((-v + 0.5) // 1)


print("=" * 92)
print("BIN COUNTS -- what scale is the model actually answering on?")
print("=" * 92)
print(f"  {'case':22}{'defensibility bins':>20}{'other dims bins':>18}")
print("  " + "-" * 60)
seen = {}
for f in sorted((HERE / "runs").glob("jev-*.json")):
    x = json.loads(f.read_text())
    pr = x.get("probabilities") or {}
    d = pr.get("defensibility") or {}
    nb_d = len(d) if isinstance(d, dict) else 0
    others = {k: len(v) for k, v in pr.items()
              if k != "defensibility" and isinstance(v, dict) and v}
    seen.setdefault("d", set()).add(nb_d)
    for v in others.values():
        seen.setdefault("o", set()).add(v)
    print(f"  {x['case']:22}{nb_d:>20}"
          f"{str(sorted(set(others.values()))):>18}")
print()
print(f"  defensibility bin counts observed across all runs: {sorted(seen.get('d', []))}")
print(f"  other dimensions' bin counts observed:            {sorted(seen.get('o', []))}")

print()
print("=" * 92)
print("WHICH MAPPING AGREES WITH THE MODEL'S OWN MOST-LIKELY LEVEL?")
print("=" * 92)
print("  argmax(probabilities) IS the model's stated most-likely level -- the natural display.")
print("  It is the ground truth against which any mapping must be judged.")
print()
print(f"  {'case/dim':30}{'score':>7}{'argmax':>8}{'orig':>7}{'halfup':>8}{'myremap':>9}"
      f"{'agree?':>22}")
print("  " + "-" * 90)
tot = agree_o = agree_h = agree_r = 0
for f in sorted((HERE / "runs").glob("jev-*.json")):
    x = json.loads(f.read_text())
    pr = x.get("probabilities") or {}
    raw = x.get("raw_jev_scores_0to4") or {}
    for k, p in pr.items():
        if not isinstance(p, dict) or not p:
            continue
        s = raw.get(k)
        if s is None:
            continue
        n = COUNTS.get(k, 5)
        try:
            am = int(max(p.items(), key=lambda kv: kv[1])[0]) + 1
        except Exception:
            continue
        orig = int(round(s)) + 1                        # Python banker's rounding
        hu = int(half_up(s)) + 1                        # half-up
        remap = max(1, min(n, int(round(s / 4 * (n - 1))) + 1))   # MY remap
        tot += 1
        agree_o += (orig == am)
        agree_h += (hu == am)
        agree_r += (remap == am)
        if not (orig == am == hu == remap):
            print(f"  {x['case'][:18]+'/'+k:30}{s:>7.2f}{am:>8}{orig:>7}{hu:>8}"
                  f"{remap:>9}"
                  f"{f'  orig={orig==am} halfup={hu==am} remap={remap==am}':>22}")

print("  " + "-" * 90)
print(f"  agreements with argmax, out of {tot} readings:")
print(f"    original int(round(s))+1  (banker's) : {agree_o:>3}  ({agree_o/tot:.1%})")
print(f"    half-up rounding                     : {agree_h:>3}  ({agree_h/tot:.1%})")
print(f"    MY PROPORTIONAL REMAP                : {agree_r:>3}  ({agree_r/tot:.1%})  <- the bug")
