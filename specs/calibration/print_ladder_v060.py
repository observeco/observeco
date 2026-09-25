"""Print the 0.6.0 ladder and test whether market_headroom still discriminates."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
runs = {}
for f in sorted((HERE / "runs").glob("jev-*.json")):
    x = json.loads(f.read_text())
    runs[x["case"]] = x

# ground truth labels, independent of the rubric
TRUTH = {
    "N1-closedbusiness": "DEAD", "bubbletea": "FAILING", "N2-koi-stripped": "STRIPPED",
    "C9-b2b-it-services": "CROWDED", "bonefirm": "UNPROVEN", "E4-bonefirm-ip": "UNPROVEN",
    "observeco": "UNPROVEN", "C4-sheng-siong": "STRONG*", "C5-michelin-hawker": "STRONG*",
    "C2-activesg": "LEADER*", "C3-pet-lovers-centre": "LEADER", "C6-euyansang": "LEADER",
    "koi": "LEADER", "E1-asml": "MONOPOLY", "E2-coupang-flywheel": "DOMINANT",
    "D1-watsons": "DOMINANT", "D2-petlovers-cue": "LEADER",
}

rows = sorted(runs.values(), key=lambda x: -(x.get("composite") or 0))
print(f"{'comp':>4}  {'band':11}{'truth':11}{'HR':>6}{'hr_raw':>7} | case")
print("-" * 74)
for x in rows:
    c = x.get("composite")
    cs = "GATE" if c is None else str(c)
    d = x["dimensions_display_1to5"]
    t = TRUTH.get(x["case"], "?")
    print(f"{cs:>4}  {x['band'][:11]:11}{t:11}{str(d['market_headroom'])+'/5':>6}"
          f"{x['raw_jev_scores_0to4']['market_headroom']:>7.2f} | {x['case']}")

print()
print("DOES market_headroom STILL DISCRIMINATE?")
print("-" * 74)
hr = [(x["dimensions_display_1to5"]["market_headroom"],
       x["raw_jev_scores_0to4"]["market_headroom"], x["case"])
      for x in rows if "market_headroom" in x["dimensions_display_1to5"]]
levels = {}
for lv, _raw, _c in hr:
    levels[lv] = levels.get(lv, 0) + 1
print(f"  observed display levels: {sorted(levels.items())}")
raws = [r for _l, r, _c in hr]
print(f"  raw spread: {min(raws):.2f}-{max(raws):.2f} = {max(raws)-min(raws):.2f}")
print(f"  distinct display levels used: {len(levels)} of 5")

print()
print("  cases at each level:")
for lv in sorted(levels, reverse=True):
    at = [c for l, _r, c in hr if l == lv]
    print(f"    {lv}/5  ({len(at)}): {', '.join(at)}")

print()
print("COMPOSITE MOVEMENT 0.5.0 -> 0.6.0 (headroom reframe only):")
prev = {"E1-asml": 92, "E2-coupang-flywheel": 78, "koi": 77, "C5-michelin-hawker": 75,
        "C6-euyansang": 73, "C2-activesg": 71, "observeco": 70, "D2-petlovers-cue": 68,
        "C4-sheng-siong": 66, "C3-pet-lovers-centre": 65, "bonefirm": 56,
        "E4-bonefirm-ip": 56, "C9-b2b-it-services": 56, "bubbletea": 51,
        "N2-koi-stripped": 50, "D1-watsons": 46}
for x in rows:
    c = x.get("composite")
    if c is None or x["case"] not in prev:
        continue
    d = c - prev[x["case"]]
    if abs(d) >= 2:
        print(f"  {x['case']:24} {prev[x['case']]:>3} -> {c:>3}  ({d:+d})")
