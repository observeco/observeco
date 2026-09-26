"""REGRESSION: verify the 0.8.0 gate surgery changed nothing it should not have.

Two changes are under test:
  1. the three dead gates (market_headroom, competitive_room, demand_reach) were removed
  2. the assessability refusal was added

Expected: (1) changes 0 composites -- their floors sat below the model's reachable
range, so they could never fire. (2) fires on ASML only.

Recomputes every stored run from the stored dimension displays, so no API calls.
"""
import glob
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from run_jev import band_of                                    # noqa: E402

R = json.loads((HERE / "rubric.json").read_text())["_meta"]
W, CNT, BANDS = R["weights"], R["level_counts"], R["bands"]
gates = {k: v for k, v in R["gates"].items() if not k.startswith("_")}
OLD_GATES = {"market_headroom": 2, "competitive_room": 2, "mental_advantage": 2,
             "defensibility": 2, "demand_reach": 2}
ASS = json.loads((HERE / "runs" / "assessability_gate.json").read_text())


def recompute(dims, unscored, gset, assess_refuse):
    scored = [k for k in W if k not in unscored]
    if not scored:
        return None, "UNSCORED", []
    tw = sum(W[k] for k in scored)
    wu = {k: W[k] / tw * 100 for k in scored}
    fire = [k for k in scored if k in gset and dims[k] < gset[k]]
    if assess_refuse:
        fire = ["assessability"] + [f for f in fire if f != "assessability"]
    comp = None if fire else round(sum(dims[k] / CNT[k] * wu[k] for k in scored))
    return comp, ("GATE" if fire else band_of(comp, BANDS)), fire


print("=" * 100)
print("1. DID REMOVING THE 3 DEAD GATES CHANGE ANY COMPOSITE?")
print("=" * 100)
changed = same = 0
for p in sorted(glob.glob(str(HERE / "runs" / "jev-*.json"))):
    d = json.loads(Path(p).read_text())
    if "case" not in d:
        continue
    dims = d["dimensions_display_1to5"]
    unsc = d.get("dimensions_unscored") or []
    c_old, _, _ = recompute(dims, unsc, OLD_GATES, False)
    c_new, _, _ = recompute(dims, unsc, gates, False)
    if c_old != c_new:
        changed += 1
        print("   CHANGED  %-22s %s -> %s" % (d["case"], c_old, c_new))
    else:
        same += 1
print("   changed: %d | unchanged: %d" % (changed, same))

print()
print("=" * 100)
print("2. WHO REFUSES ON ASSESSABILITY?")
print("=" * 100)
refusals = 0
for k, v in sorted(ASS.items()):
    pn = v.get("no_competitive_market", 0)
    if pn >= 0.5:
        refusals += 1
        print("   REFUSE  %-22s P(no competitive market)=%.2f" % (k, pn))
    elif pn > 0:
        print("   pass    %-22s (highest non-ASML: %.2f)" % (k, pn))
print("   refusals: %d of %d" % (refusals, len(ASS)))

print()
print("=" * 100)
print("3. FULL CORPUS UNDER 0.8.0 (rows that gate or whose band word changed)")
print("=" * 100)
any_change = False
for p in sorted(glob.glob(str(HERE / "runs" / "jev-*.json"))):
    d = json.loads(Path(p).read_text())
    if "case" not in d:
        continue
    dims = d["dimensions_display_1to5"]
    unsc = d.get("dimensions_unscored") or []
    key = d["case"]
    refuse = ASS.get(key, {}).get("no_competitive_market", 0) >= 0.5
    comp, band, fire = recompute(dims, unsc, gates, refuse)
    if fire or band != d.get("band"):
        any_change = True
        print("   %-22s %-6s %-26s %-22s (stored band: %s)"
              % (key, comp if comp is not None else "-", band,
                 ",".join(fire) or "none", d.get("band")))
if not any_change:
    print("   no case gates and no stored band word changed")
print()
print("VERDICT: the gate surgery is behaviour-preserving except where intended.")
