"""Control-set analysis v2 — on the REFRAMED dimension (rubric 0.3.0).

Compares the ladder before and after position_availability -> mental_advantage, and checks
the two things the change must deliver:
  * monotonic ordering of mental_advantage against ground truth
  * whether the relative framing INFLATES small players (the live risk flagged in
    FINDING-position-reframe-tested.md)
"""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
DIMS_OLD = ["market_headroom", "competitive_room", "position_availability",
            "defensibility", "demand_reach"]

# case -> (ground truth, composite BEFORE the reframe, description, size band)
CASES = {
    "N1-closedbusiness":    ("DEAD",     None, "closed business", "micro"),
    "bubbletea":         ("FAILING",  53, "CaiCa 6 outlets -> 3, brand not recalled", "small"),
    "N2-koi-stripped":      ("STRIPPED", 53, "KOI minus its differentiator", "large"),
    "C9-b2b-it-services":   ("CROWDED",  53, "B2B managed IT, 6+ undifferentiated rivals", "small"),
    "bonefirm":          ("UNPROVEN", 59, "feasible subject to one condition", "micro"),
    "C4-sheng-siong":       ("STRONG*",  62, "listed #2 vs an 88%-concentrated top 3", "large"),
    "observeco":         ("UNPROVEN", 63, "my own business - contaminated", "micro"),
    "koi":               ("LEADER",   66, "20% share, 88 outlets, 20 yrs", "large"),
    "C3-pet-lovers-centre": ("LEADER",   67, "largest SEA pet retail, since 1973", "large"),
    "C6-euyansang":         ("LEADER",   67, "146 yrs, S$800M acquisition", "large"),
    "C5-michelin-hawker":   ("STRONG*",  68, "Michelin star every yr since 2016, 1 stall", "micro"),
    "C2-activesg":          ("LEADER*",  59, "public gym, subsidised, owns cheapest access", "large"),
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
    truth, old_comp, desc, size = CASES[case]
    ma = r["dimensions_display_1to5"].get("mental_advantage")
    ma_old = r["dimensions_display_1to5"].get("position_availability")
    cov = (r.get("evidence_coverage") or {}).get("mental_advantage")
    unscored = r.get("dimensions_unscored") or []
    iv = (r.get("judgment_intervals") or {}).get("mental_advantage") or {}
    rows.append({"case": case, "truth": truth, "old": old_comp,
                 "new": r["composite"], "band": r["band"], "desc": desc,
                 "size": size, "ma": ma, "ma_old": ma_old, "cov": cov,
                 "unscored": unscored, "iv": iv})

rows.sort(key=lambda x: -(x["new"] or 0))

print("=" * 100)
print("THE LADDER AFTER THE REFRAME  (rubric 0.3.0, mental_advantage)")
print("=" * 100)
print(f"{'new':>5}{'old':>6}  {'band':12}{'truth':10}{'MA':>4}{'cov':>7}  {'interval':>9}  case")
print("-" * 100)
for x in rows:
    o = x["old"] if x["old"] is not None else "GATE"
    ma = x["ma"] if x["ma"] is not None else "-"
    cov = f"{x['cov']:.2f}" if isinstance(x["cov"], (int, float)) else "-"
    b = x["iv"].get("band_80pct_display_1to5")
    bs = f"{b[0]}-{b[1]}" if b else "-"
    flag = " UNSCORED" if x["case"] in (x["unscored"] or []) else ""
    print(f"{x['new'] or 0:>5}{str(o):>6}  {x['band'][:12]:12}{x['truth']:10}{ma:>4}{cov:>7}  {bs:>9}  {x['case']}{flag}")

print()
print("SEPARATION — old vs new")
print("-" * 100)
leaders = [x["new"] for x in rows if x["truth"].startswith("LEADER")]
troubled = [x["new"] for x in rows if x["truth"] in ("FAILING", "STRIPPED", "CROWDED")]
leaders_old = [x["old"] for x in rows if x["truth"].startswith("LEADER") and x["old"]]
troubled_old = [x["old"] for x in rows if x["truth"] in ("FAILING", "STRIPPED", "CROWDED") and x["old"]]
print(f"  OLD: leaders {sorted(leaders_old)}  troubled {sorted(troubled_old)}")
print(f"       gap = {min(leaders_old) - max(troubled_old)} points")
print(f"  NEW: leaders {sorted(leaders)}  troubled {sorted(troubled)}")
print(f"       gap = {min(leaders) - max(troubled)} points")

print()
print("MONOTONICITY — is mental_advantage ordered against ground truth?")
print("-" * 100)
order = {"DEAD": 0, "FAILING": 1, "STRIPPED": 2, "CROWDED": 3, "UNPROVEN": 4,
         "STRONG*": 5, "LEADER*": 6, "LEADER": 7}
ma_rows = sorted([x for x in rows if x["ma"] is not None],
                 key=lambda x: (order.get(x["truth"], 4), x["ma"]))
for x in ma_rows:
    print(f"  {x['truth']:10} MA={x['ma']}/5  {x['case']:24} {x['desc']}")

print()
print("INFLATION RISK CHECK — does the relative framing reward smallness?")
print("-" * 100)
for x in sorted(rows, key=lambda x: x["size"]):
    if x["ma"] is None:
        continue
    print(f"  {x['size']:6} MA={x['ma']}/5  {x['truth']:10} {x['case']}")
micro = [x["ma"] for x in rows if x["size"] == "micro" and x["ma"]]
large = [x["ma"] for x in rows if x["size"] == "large" and x["ma"]]
if micro and large:
    print(f"  micro mean MA {sum(micro)/len(micro):.2f}   large mean MA {sum(large)/len(large):.2f}")

print()
print("CONFIDENCE FIX — did the floor catch anything?")
print("-" * 100)
n_un = sum(1 for x in rows if x["unscored"])
print(f"  runs with at least one dimension below the 0.20 coverage floor: {n_un}/{len(rows)}")
for x in rows:
    if x["unscored"]:
        print(f"    {x['case']:24} unscored: {x['unscored']}")
zero = [(x["case"], k) for x in rows for k, v in (x["cov"] is not None and
        json.loads((HERE / 'runs' / f'jev-{x["case"]}.json').read_text()) or {}).get("evidence_coverage", {}).items()
        if v == 0.0] if False else []
