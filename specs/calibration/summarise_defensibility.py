"""Defensibility ladder summary — where every case sits, and why level 4 was not reached."""
import json
import glob
from pathlib import Path

HERE = Path(__file__).resolve().parent

print("FULL DEFENSIBILITY LADDER (rubric 0.4.x)")
print(f"{'D':>2}  {'case':26}{'raw':>6}{'cov':>6}  top-mass  distribution")
rows = []
for f in glob.glob(str(HERE / "runs" / "jev-*.json")):
    r = json.loads(Path(f).read_text())
    if r.get("rubric_version") not in ("0.4.0", "0.4.1"):
        continue
    d = r["dimensions_display_1to5"].get("defensibility")
    if d is None:
        continue
    dist = r["probabilities"]["defensibility"]
    top = max(dist, key=lambda k: dist[k])
    rows.append((d, r["case"], r["raw_jev_scores_0to4"]["defensibility"],
                 r["evidence_coverage"]["defensibility"], int(top) + 1, dist))
rows.sort(reverse=True)
for d, c, raw, cov, tl, dist in rows:
    print(f"{d:>2}  {c:26}{raw:>6.2f}{cov:>6.2f}  L{tl} @ {dist[str(tl-1)]:.2f}   {json.dumps(dist)}")

print()
print("=== THE 3/4 BOUNDARY, VERBATIM ===")
r = json.loads((HERE / "rubric.json").read_text())
L = r["questions"]["defensibility"]["levels"]
print("  L3:", L[2])
print()
print("  L4:", L[3])
print()
print("  L5:", L[4])
print()
print("=== WHERE IP LANDS IN THE LEVEL TEXT (rubric 0.5.0, 6 levels) ===")
print("  L3 'Replicable' names: formulation | process | technical system")
print("      -> development required, but NOTHING OBSTRUCTS beyond the effort")
print("  L4 'Protected'  adds : a barrier obstructing copying beyond the effort")
print("      -> trade secret not reverse-engineerable | patent that blocks |")
print("         undisclosed process/ratio/sequence | supply arrangement unobtainable")
print("  L5 'Durable'  names  : accumulated trust | owned distribution |")
print("                         proprietary dataset | years of relationship")
print("  L6 'Compounding'     : reinforcing advantages, not replicable even given time")
print()
print("  Sean's decision: 'a well-protected single formulation should not score the same as")
print("  something copyable in months.' L3 vs L4 is exactly that distinction.")

print()
print("E4 vs BONEFIRM — same business, IP depth added:")
for c in ("bonefirm", "E4-bonefirm-ip"):
    p = HERE / "runs" / f"jev-{c}.json"
    if not p.exists():
        continue
    x = json.loads(p.read_text())
    print(f"  {c:20} D={x['dimensions_display_1to5']['defensibility']} "
          f"raw={x['raw_jev_scores_0to4']['defensibility']:.2f} "
          f"cov={x['evidence_coverage']['defensibility']:.2f} "
          f"comp={x['composite']} {x['band']}")
    print(f"    {'':18} dist={json.dumps(x['probabilities']['defensibility'])}")
