"""Print the 0.5.0 ladder honestly — from the run artifacts, not from a hand-typed table."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
W = ("market_headroom", "competitive_room", "mental_advantage",
     "defensibility", "demand_reach")
rows = []
for f in sorted((HERE / "runs").glob("jev-*.json")):
    r = json.loads(f.read_text())
    d = r.get("dimensions_display_1to5") or {}
    if "defensibility" not in d:
        continue
    rows.append((r.get("composite") if r.get("composite") is not None else 0,
                 r["case"], r["band"], r.get("rubric_version"),
                 d.get("defensibility"), r.get("composite")))
rows.sort(reverse=True)
print(f"{'comp':>4}  {'band':11}{'rubr':7}{'D':>5}  case")
print("-" * 62)
for c, case, band, rv, dfn, comp in rows:
    cs = "GATE" if comp is None else str(c)
    print(f"{cs:>4}  {band[:11]:11}{(rv or '?')[:6]:7}{str(dfn)+'/6':>5}  {case}")
