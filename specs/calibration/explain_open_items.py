"""Explain the three 'still open' items with concrete numbers."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
runs = {}
for f in sorted((HERE / "runs").glob("jev-*.json")):
    x = json.loads(f.read_text())
    if x.get("rubric_version") == "0.5.0":
        runs[x["case"]] = x

print("ITEM 1 — THE LEVEL-5 MAGNET: different businesses, same score")
print()
seen = {}
for case, x in runs.items():
    d = x["dimensions_display_1to5"]["defensibility"]
    cov = x["evidence_coverage"]["defensibility"]
    if d == 5:
        seen[case] = (cov, x["raw_jev_scores_0to4"]["defensibility"])
print("  Everything that scored 5/6 'Durable':")
for c, (cov, raw) in sorted(seen.items(), key=lambda kv: -kv[1][1]):
    print(f"    {c:24} raw {raw:.2f}  coverage {cov:.2f}")
if seen:
    raws = [v[1] for v in seen.values()]
    covs = [v[0] for v in seen.values()]
    print(f"    -> {len(seen)} cases, raw spread {min(raws):.2f}-{max(raws):.2f} "
          f"= {max(raws)-min(raws):.2f}, coverage {min(covs):.2f}-{max(covs):.2f}")
print("    measured run-to-run noise = 0.08")

print()
print("ITEM 2 — ASML: two of the five dimensions give nonsense for a monopoly")
print()
a = runs.get("E1-asml")
if a:
    for k in ("market_headroom", "competitive_room", "mental_advantage",
              "defensibility", "demand_reach"):
        d = a["dimensions_display_1to5"].get(k)
        cov = a["evidence_coverage"].get(k)
        un = k in (a.get("dimensions_unscored") or [])
        note = "WITHHELD (coverage 0.00)" if un else f"{d}/6" if k == "defensibility" else f"{d}/5"
        print(f"    {k:20} {note:26} coverage {cov}")

print()
print("ITEM 3 — HUMAN LABELS: how many exist?")
print()
import subprocess
s = HERE / "runs" / "sean-blind-bonefirm.json"
if s.exists():
    d = json.loads(s.read_text())
    print(f"    sean-blind-bonefirm.json exists: scored_by={d['scored_by']!r}, "
          f"key_compared={d.get('key_compared')}")
print("    total human-labelled cases: 1 (Bonefirm, 23 Sep)")
print(f"    total model-scored cases   : {len(runs)} (rubric 0.5.0)")
print("    human labels applied to the CURRENT rubric: 0 of them")
