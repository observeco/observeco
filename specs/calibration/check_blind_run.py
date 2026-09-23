"""Verify the calibration scoring logic: weights sum, gate predicate, and that
each sealed expectation computes to the band the analysis actually concluded."""

import re
from pathlib import Path

p = Path(__file__).resolve().parent / "blind-run.html"
m = re.search(r"<script>(.*?)</script>", p.read_text(), re.S)
assert m, "no <script> block found in blind-run.html"
js = m.group(1)

dims = re.findall(
    r"\{ key:'(\w+)',\s+name:'([^']+)',\s+wt:'(\d+)%', floor:(\d) \}", js
)
assert len(dims) == 5, f"expected 5 dimensions, parsed {len(dims)}"
keys = [k for k, _n, _w, _f in dims]

total = sum(int(w) for _k, _n, w, _f in dims)
print(f"weights sum = {total}")
assert total == 100, f"weights must sum to 100, got {total}"

# NOTE: floor semantics. A score of 1 means "failing", so every floor must be >= 2.
# The first version of the sealed key set most floors to 1, which made a score of 1
# PASS the gate it was supposed to fire. Caught by this check.
floors_ok = all(int(f) >= 2 for _k, _n, _w, f in dims)
print(f"all floors >= 2 (1 = failing): {floors_ok}")
assert floors_ok, "a floor of 1 lets a failing score pass its own gate"

# Sealed expectations, and the band each analysis actually concluded.
# NOTE: labels derived from the analysis's VIABILITY sentence, not its MARKET-STANDING
# sentence. First pass got this wrong -- it took "fringe, <1% share" (a statement about
# current standing) as the viability verdict. Current standing is NOT a dimension of
# viability: Bonefirm is also "<1%, #5+" yet the analysis calls it feasible.
cases = {
    "01 bonefirm":      ((4, 3, 4, 2, 3), "Viable, conditional"),
    "02 greenpackers":  ((4, 2, 2, 2, 3), "Contested"),
    "03 petdirectory":  ((4, 4, 4, 3, 2), "Viable, conditional"),
    "04 caica":         ((3, 2, 2, 1, 3), "GATE"),   # G4 fires, no composite
    "05 sgfitness":     ((3, 2, 4, 3, 4), "Viable, conditional"),
    "06 saladshop":     ((3, 2, 3, 3, 3), "Contested"),
}

BANDS = [("Fragile", 5, 39), ("Contested", 40, 59),
         ("Viable, conditional", 60, 74), ("Strong", 75, 95)]


def band_of(c):
    for name, lo, hi in BANDS:
        if lo <= c <= hi:
            return name
    return "out of range"


print(f"\n{'case':18}{'dims':16}{'comp':>6}  {'computed':22}{'expected':22}{'ok'}")
mismatches = []
outputs = set()
for case, (scores, expected) in cases.items():
    fires = [keys[i] for i, s in enumerate(scores) if s < 2]
    comp = round(sum(scores[i] / 5 * int(dims[i][2]) for i in range(5)))
    got = "GATE" if fires else band_of(comp)
    outputs.add(got)
    if got != expected:
        mismatches.append((case, got, expected, comp, fires))
    flag = "yes" if got == expected else "NO"
    print(f"{case:18}{str(scores):16}{comp:>6}  {got:22}{expected:22}{flag}")

print()
if mismatches:
    print("MISMATCHES:")
    for case, got, expected, comp, fires in mismatches:
        print(f"  {case}: computed {got} ({comp}) vs expected {expected}")
        print(f"    gates firing: {fires or 'none'}")
else:
    print("all six outcomes match the analysis verdicts")

print(f"\ndistinct outcomes across the set: {len(outputs)} -> {sorted(outputs)}")
assert len(outputs) >= 3, "no discriminating power: fewer than 3 distinct outcomes"
print("discriminating power: OK")
print("\nNOTE 02 GreenPackers at 49 (Contested) is a J3 candidate: 'entry must be")
print("flanking' is arguably Fragile-adjacent. Flag for hand-read, do not force.")


