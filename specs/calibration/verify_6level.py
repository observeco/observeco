"""Verify the 0.5.0 six-level defensibility migration end to end."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
r = json.loads((HERE / "rubric.json").read_text())
m = r["_meta"]
counts = m["level_counts"]
W = m["weights"]
print("rubric", m["version"], "| level_counts", json.dumps(counts))
print()

for case in ("E4-bonefirm-ip", "bonefirm", "C9-b2b-it-services", "E1-asml", "koi"):
    p = HERE / "runs" / f"jev-{case}.json"
    if not p.exists():
        continue
    x = json.loads(p.read_text())
    dims = x["dimensions_display_1to5"]
    un = x.get("dimensions_unscored") or []
    scored = [k for k in W if k not in un]
    tw = sum(W[k] for k in scored)
    wu = {k: W[k] / tw * 100 for k in scored}
    manual = round(sum(dims[k] / counts[k] * wu[k] for k in scored))
    print(f"{case:22} recorded={x['composite']} manual={manual} "
          f"{'OK' if manual == x['composite'] else 'MISMATCH'}")
    for k in ("market_headroom", "competitive_room", "mental_advantage",
              "defensibility", "demand_reach"):
        if k in un:
            print(f"    {k:20} withheld")
            continue
        contrib = dims[k] / counts[k] * wu[k]
        print(f"    {k:20} {dims[k]}/{counts[k]}  = {dims[k]/counts[k]:.3f} x "
              f"{wu[k]:.1f}  -> {contrib:5.2f}")
    print(f"    {'TOTAL':20} {'':10} -> {sum(dims[k]/counts[k]*wu[k] for k in scored):5.2f} "
          f"-> rounded {manual}")
    print()

print("DISPLAY LABEL CHECK — defensibility is 6-level, so '/5' is now WRONG:")
for case in ("E4-bonefirm-ip", "bonefirm", "E1-asml"):
    p = HERE / "runs" / f"jev-{case}.json"
    if not p.exists():
        continue
    x = json.loads(p.read_text())
    d = x["dimensions_display_1to5"]["defensibility"]
    print(f"  {case:22} shows '{d}' -> should render '{d}/{counts['defensibility']}'")
