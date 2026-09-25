"""Control-set analysis: does the rubric discriminate across the full ladder?

Aggregates every control run and checks the properties the plan predicted:
rank separation, position_availability behaviour, and the confidence defect.
"""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
DIMS = ["market_headroom", "competitive_room", "position_availability",
        "defensibility", "demand_reach"]

# label = ground truth about the business, independent of the rubric
CASES = {
    "N1-closedbusiness":   ("DEAD",        "closed business"),
    "bubbletea":           ("FAILING",     "CaiCa — 6 outlets to 3, brand not recalled"),
    "N2-koi-stripped":     ("STRIPPED",    "KOI with its differentiator removed"),
    "C9-b2b-it-services":  ("CROWDED",     "B2B managed IT, 6+ undifferentiated rivals"),
    "C2-activesg":         ("LEADER*",     "public gym, subsidised, owns cheapest access"),
    "C3-pet-lovers-centre":("LEADER",      "largest SEA pet retail chain, since 1973"),
    "C4-sheng-siong":      ("STRONG*",     "listed #2 vs an 88%-concentrated top 3"),
    "koi":                 ("LEADER",      "20% share, 13% growth, 20 years"),
    "C6-euyansang":        ("LEADER",      "146 yrs, S$800M acquisition, household name"),
    "C5-michelin-hawker":  ("STRONG*",     "Michelin star every year since 2016"),
    "bonefirm":            ("UNPROVEN",    "feasible subject to one condition"),
    "observeco":           ("UNPROVEN",    "my own business — contaminated"),
}


def band(c):
    if c is None:
        return "GATE"
    if c <= 39:
        return "Fragile"
    if c <= 59:
        return "Contested"
    if c <= 74:
        return "Viable"
    return "Strong"


rows = []
for f in sorted((HERE / "runs").glob("jev-*.json")):
    r = json.loads(f.read_text())
    case = r["case"]
    if case not in CASES:
        continue
    truth, desc = CASES[case]
    rows.append((r["composite"] or 0, truth, case, desc, r))

rows.sort(reverse=True)

print("THE CONTROL LADDER — ranked by composite")
print("=" * 92)
print(f"{'comp':>5}  {'band':12}{'truth':10}{'case':24}ground truth")
print("-" * 92)
for comp, truth, case, desc, _r in rows:
    print(f"{comp:>5}  {band(comp):12}{truth:10}{case:24}{desc}")

print()
print("SEPARATION CHECK")
print("-" * 92)
grp = {}
for comp, truth, case, _d, _r in rows:
    grp.setdefault(truth, []).append(comp)
for t in ("DEAD", "FAILING", "STRIPPED", "CROWDED", "UNPROVEN", "STRONG*", "LEADER*", "LEADER"):
    if t in grp:
        v = sorted(grp[t])
        print(f"  {t:10} n={len(v)}  composites {v}"
              f"  {'(range ' + str(v[0]) + '-' + str(v[-1]) + ')' if len(v) > 1 else ''}")

if "LEADER" in grp and "FAILING" in grp:
    print()
    print(f"  lowest LEADER  : {min(grp['LEADER'])}")
    print(f"  highest FAILING: {max(grp['FAILING'])}")
    sep = min(grp["LEADER"]) - max(grp["FAILING"])
    print(f"  separation     : {sep} points"
          f"  -> {'CLEAN' if sep > 0 else 'OVERLAP — rubric cannot separate'}")

print()
print("POSITION_AVAILABILITY — the dimension I claimed was 'wired backwards'")
print("-" * 92)
print(f"  {'case':24}{'truth':10}{'score':>6}{'conf':>7}")
for comp, truth, case, _d, r in rows:
    pa = r["dimensions_display_1to5"]["position_availability"]
    cf = r["confidence"]["position_availability"]
    flag = "  <-- ZERO CONFIDENCE" if cf == 0.0 else ""
    print(f"  {case:24}{truth:10}{pa:>6}{cf:>7.2f}{flag}")

print()
print("CONFIDENCE DEFECT")
print("-" * 92)
zero = [(case, d) for _c, _t, case, _d, r in rows for d in DIMS
        if r["confidence"][d] == 0.0]
print(f"  exact-zero confidence events: {len(zero)}")
for case, d in zero:
    print(f"    {case:24}{d}")
print()
print("  A zero is not a low score — it is the model reporting a dead-even")
print("  distribution with no preference at all. It should not be displayed.")
