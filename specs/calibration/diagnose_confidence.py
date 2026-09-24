"""Test whether the low-confidence dimensions share a cause.

Hypothesis to falsify: low confidence appears on the dimensions whose judgment
requires COMPETITOR evidence, which the input pipeline never collects.

If true: the two competitor-dependent dimensions should be the lowest-confidence
ones, consistently across cases.
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent

# Does answering this dimension require evidence about OTHER businesses?
NEEDS_COMPETITOR = {
    "market_headroom": False,        # category/market facts — partially derivable
    "competitive_room": True,        # competitor strength + price floor
    "position_availability": True,   # what competitors CLAIM
    "defensibility": False,          # the business's own build
    "demand_reach": False,           # the business's own customer
}

CASES = ["bonefirm", "observeco"]

rows = []
for case in CASES:
    p = HERE / "runs" / f"jev-{case}.json"
    if not p.exists():
        continue
    run = json.loads(p.read_text())
    for dim, conf in run["confidence"].items():
        rows.append((case, dim, conf, run["dimensions_display_1to5"][dim],
                     NEEDS_COMPETITOR[dim]))

print(f"{'case':12}{'dimension':24}{'conf':>7}{'score':>7}{'needs competitor':>18}")
print("-" * 70)
for case, dim, conf, score, needs in rows:
    print(f"{case:12}{dim:24}{conf:>7.2f}{score:>7}{str(needs):>18}")

print()
dep = [r[2] for r in rows if r[4]]
ind = [r[2] for r in rows if not r[4]]
print(f"competitor-dependent dimensions : n={len(dep)}  "
      f"mean conf {sum(dep)/len(dep):.2f}  values {sorted(round(x,2) for x in dep)}")
print(f"self-reportable dimensions      : n={len(ind)}  "
      f"mean conf {sum(ind)/len(ind):.2f}  values {sorted(round(x,2) for x in ind)}")
print()

# Rank-based check per case: where do the competitor dimensions sit?
print("Rank of confidence within each case (1 = lowest):")
for case in CASES:
    crows = [r for r in rows if r[0] == case]
    if not crows:
        continue
    ranked = sorted(crows, key=lambda r: r[2])
    for i, (_, dim, conf, _s, needs) in enumerate(ranked, 1):
        flag = "  <- competitor-dependent" if needs else ""
        print(f"  {case:12} #{i}  {dim:24}{conf:.2f}{flag}")
    print()

# The claim never fetched: competitor POSITIONING
print("Evidence the pipeline actually collected:")
print("  competitor NAMES      : yes (owner self-report, both cases)")
print("  competitor PRICE      : Bonefirm only (founder volunteered it)")
print("  competitor POSITIONING: NO — no competitor site was ever fetched")
print()
print("If position_availability is the lowest-confidence dimension in both cases,")
print("the cause is the missing evidence type, not the model and not the input volume.")
