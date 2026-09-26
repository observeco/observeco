"""COMPARABILITY: unscored dimensions change the weight denominator, so composites
from cases with different unscored sets are not directly comparable.

THE MECHANISM (correct and intended): a dimension whose evidence coverage falls below
display_floor (0.2) is reported as "unscored" rather than as a fabricated number, and
its weight renormalises over the rest. That is the right behaviour.

THE SIDE EFFECT (not intended): two cases in the same category can then be scored over
DIFFERENT dimension sets. McDonald's demand_reach coverage 0.12 -> dropped; KFC's 0.24
-> kept. So KFC's 48 and McDonald's 45 are averages of different things, and a
difference can come from WHICH dimensions were counted rather than how good the
business is.

This quantifies how often that happens and whether it moves the headline results.
"""
import glob
import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
R = json.loads((HERE / "rubric.json").read_text())["_meta"]
W, CNT, FLOOR = R["weights"], R["level_counts"], R["display_floor"]
FULL = set(W)

rows = []
for p in sorted(glob.glob(str(HERE / "runs" / "jev-*.json"))):
    d = json.loads(Path(p).read_text())
    if "case" not in d or d.get("rubric_version") != "0.9.0":
        continue
    rows.append(d)

print("=" * 96)
print("1. HOW MANY CASES ARE SCORED OVER A REDUCED DIMENSION SET?")
print("=" * 96)
sets = Counter()
for d in rows:
    unsc = tuple(sorted(d.get("dimensions_unscored") or []))
    sets[unsc] += 1
for s, n in sets.most_common():
    label = "FULL (all 5)" if not s else "reduced: missing " + ", ".join(s)
    print("   %-3d cases  %s" % (n, label))
n_reduced = sum(n for s, n in sets.items() if s)
print()
print("   reduced-set cases: %d of %d (%.0f%%)" % (n_reduced, len(rows), n_reduced / len(rows) * 100))

print()
print("=" * 96)
print("2. CAN A CASE'S COMPOSITE BE RECOMPUTED ON THE FULL 5-DIMENSION SET?")
print("=" * 96)
print("   where a dimension was dropped for low coverage, its raw display is still")
print("   recorded. Recomputing on all 5 shows how much the drop moved the composite.")
print()
print("   %-24s %-8s %-9s %-9s %s" % ("case", "dims", "as-run", "all-5", "shift"))
print("   " + "-" * 78)
shifts = []
for d in rows:
    unsc = d.get("dimensions_unscored") or []
    if not unsc:
        continue
    dims = d["dimensions_display_1to5"]
    if any(dims.get(k) is None for k in FULL):
        continue
    full_c = round(sum(dims[k] / CNT[k] * W[k] for k in sorted(FULL)))
    shift = full_c - (d.get("composite") or 0)
    shifts.append(abs(shift))
    flag = "  <-- >2 pts" if abs(shift) > 2 else ""
    print("   %-24s %-8s %-9s %-9d %+d%s"
          % (d["case"], "".join(str(dims[k]) for k in sorted(FULL)),
             d.get("composite"), full_c, shift, flag))
if shifts:
    print()
    print("   mean |shift| = %.1f pts | max = %d | band noise = %.1f"
          % (statistics.mean(shifts), max(shifts), R["band_noise"]))
    over = sum(1 for s in shifts if s > R["band_noise"])
    print("   shifts larger than the band noise: %d of %d" % (over, len(shifts)))

print()
print("=" * 96)
print("3. DOES THE DROP EVER FLIP A BAND WORD?")
print("=" * 96)
BANDS = R["bands"]


def band_of(c):
    for name, lo, hi in BANDS:
        if lo <= c <= hi:
            return name
    return "?"


flips = 0
for d in rows:
    unsc = d.get("dimensions_unscored") or []
    if not unsc or any(d["dimensions_display_1to5"].get(k) is None for k in FULL):
        continue
    dims = d["dimensions_display_1to5"]
    full_c = round(sum(dims[k] / CNT[k] * W[k] for k in sorted(FULL)))
    a, b = band_of(d["composite"]), band_of(full_c)
    if a != b:
        flips += 1
        print("   %-24s as-run %d (%s)  ->  all-5 %d (%s)"
              % (d["case"], d["composite"], a, full_c, b))
if not flips:
    print("   no band word flips")
else:
    print()
    print("   -> %d band words depend on WHICH dimensions were counted" % flips)

print()
print("=" * 96)
print("4. THE FAST-FOOD INVERSION — is it a real instrument error?")
print("=" * 96)
for name, f in [("McDonald's", "jev-FF01-mcdonalds.json"), ("KFC", "jev-FF02-kfc.json"),
                ("Burger King", "jev-FF03-burger.json"), ("Shake Shack", "jev-FF06-shake.json")]:
    try:
        d = json.loads((HERE / "runs" / f).read_text())
    except FileNotFoundError:
        continue
    dm = d["dimensions_display_1to5"]
    print("   %-13s comp=%-4s ma=%-3s def=%-3s cr=%-3s dr=%-3s  unscored=%s"
          % (name, d.get("composite"), dm.get("mental_advantage"),
             dm.get("defensibility"), dm.get("competitive_room"), dm.get("demand_reach"),
             ",".join(d.get("dimensions_unscored") or []) or "-"))
print()
print("   CAUSE: McDonald's demand_reach COVERAGE was 0.12, below the 0.2 floor, so it")
print("   was dropped and its weight renormalised. KFC's was 0.24, kept. Their")
print("   composites average different dimension sets -- so the 45 vs 48 gap is partly")
print("   a denominator artifact, not a positioning judgement.")
print()
print("   The underlying judgment: KFC scored mental_advantage 4, McDonald's 3.")
print("   That is DEFENSIBLE under positioning theory -- the ubiquitous default is not")
print("   a DISTINCT position, while 'the chicken place' is a category slot. But it is")
print("   not what a naive reading of 'McDonald's is the most top-of-mind' would predict,")
print("   so it should be flagged rather than buried.")
