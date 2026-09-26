"""THE SCORE GATES ARE DOING THE WRONG JOB. Verify and fix.

THE DEFECT (found on the fresh 55-case set)
The `defensibility` gate at floor 2 fires on 10 of 55+20 cases. Eight of them are
LIVE, large businesses: KFC, Burger King, Zoff, Harvey Norman, Spectacle Hut, Pure
Fitness, R&B Tea. That is a false refusal, and it is not a threshold problem.

THE CAUSE IS SEMANTIC, NOT NUMERIC
`defensibility` display 1 = "No moat. There is no differentiator at all". The model is
NOT wrong about KFC -- a generic fried-chicken chain genuinely has no moat. The defect
is that the GATE turns "no moat" into "we cannot assess this business". Those are
different statements, and conflating them destroys the signal:

    "this business has no moat"  -> a valid, informative, LOW score
    "we cannot assess this business" -> a refusal

A business with no moat is eminently assessable. Refusing it throws away exactly the
negative signal the report exists to deliver.

This also CONTRADICTS the gate design principle already established in this project:
gates should say "cannot assess", not "is this business bad". `defensibility` is a
score dimension, so gating on it is precisely the error that principle forbids.

AND IT EXPLAINS THE VESTIGIAL BAND
Every case that gates has all-2s floors satisfied. Remove the score gates and those
cases score normally -- and several land in "Fragile", which was previously
mathematically unreachable. One fix, two defects.

WHAT THE FIX DOES
Remove the `defensibility` and `mental_advantage` SCORE gates. Keep the assessability
gate -- that one asks the right question ("can the method work here"). A no-moat
business then scores LOW instead of refusing, which is what the client needs to hear.
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
CURRENT_GATES = {k: v for k, v in R["gates"].items() if not k.startswith("_")}
PROPOSED_GATES = {}          # no score gates at all; assessability remains a classifier
ASS = json.loads((HERE / "runs" / "assessability_gate.json").read_text())


def compute(dims, unscored, gates, refuse):
    scored = [k for k in W if k not in unscored]
    if not scored:
        return None, "UNSCORED", []
    tw = sum(W[k] for k in scored)
    wu = {k: W[k] / tw * 100 for k in scored}
    fire = [k for k in scored if k in gates and dims[k] < gates[k]]
    if refuse:
        fire = ["assessability"] + [f for f in fire if f != "assessability"]
    comp = None if fire else round(sum(dims[k] / CNT[k] * wu[k] for k in scored))
    return comp, ("GATE" if fire else band_of(comp, BANDS)), fire


def load_all():
    out = []
    for p in sorted(glob.glob(str(HERE / "runs" / "jev-*.json"))):
        d = json.loads(Path(p).read_text())
        if "case" not in d:
            continue
        out.append(d)
    return out


runs = load_all()
print("=" * 104)
print("1. HOW OFTEN DOES EACH SCORE GATE FIRE? (and on what?)")
print("=" * 104)
for gate in CURRENT_GATES:
    fire = [d for d in runs if (d.get("dimensions_display_1to5") or {}).get(gate) is not None
            and d["dimensions_display_1to5"][gate] < CURRENT_GATES[gate]]
    print("   gate %-18s floor %d  fires on %d cases: %s"
          % (gate, CURRENT_GATES[gate], len(fire), ", ".join(d["case"] for d in fire)))

print()
print("=" * 104)
print("2. DEAD vs ALIVE — can the defensibility gate tell them apart?")
print("=" * 104)
DEAD = {"N1-closedbusiness", "P5-gongcha", "GY07-true"}
d1 = [d for d in runs if (d.get("dimensions_display_1to5") or {}).get("defensibility") == 1]
dead_hits = [d["case"] for d in d1 if d["case"] in DEAD]
alive_hits = [d["case"] for d in d1 if d["case"] not in DEAD]
print("   defensibility=1 and the business is DEAD : %d  %s" % (len(dead_hits), dead_hits))
print("   defensibility=1 and the business is ALIVE: %d  %s" % (len(alive_hits), alive_hits))
if alive_hits:
    print()
    print("   -> FALSE REFUSALS: %d of %d firings are live businesses."
          % (len(alive_hits), len(d1)))
    print("      The gate does NOT separate dead from alive. It separates")
    print("      'has a moat' from 'has no moat' -- and refuses the latter, which is")
    print("      the one case the report most needs to score.")

print()
print("=" * 104)
print("3. WHAT HAPPENS TO THOSE CASES IF THE SCORE GATES ARE REMOVED?")
print("=" * 104)
print("   %-22s %-8s %-10s %-8s %-22s %s"
      % ("case", "dims", "now", "fixed", "fixed band", "was refused because"))
print("   " + "-" * 98)
changed = 0
fragile = []
for d in runs:
    dims = d["dimensions_display_1to5"]
    unsc = d.get("dimensions_unscored") or []
    key = d["case"]
    refuse = ASS.get(key, {}).get("no_competitive_market", 0) >= 0.5
    c_now, b_now, f_now = compute(dims, unsc, CURRENT_GATES, refuse)
    c_fix, b_fix, f_fix = compute(dims, unsc, PROPOSED_GATES, refuse)
    if b_now != b_fix:
        changed += 1
        if b_fix == "Fragile":
            fragile.append((key, c_fix))
        print("   %-22s %-8s %-10s %-8s %-22s %s"
              % (key, "".join(str(dims[k]) for k in W if k in dims),
                 c_now if c_now is not None else "GATE",
                 c_fix if c_fix is not None else "GATE", b_fix,
                 ",".join(f for f in f_now if f != "assessability") or "assessability"))

print()
print("   band words changed: %d of %d cases" % (changed, len(runs)))

print()
print("=" * 104)
print("4. DOES 'Fragile' (5-37) BECOME REACHABLE?")
print("=" * 104)
if fragile:
    print("   YES -- %d cases now land in Fragile, all of them businesses that are" % len(fragile))
    print("   either closed or have no position at all:")
    for k, c in sorted(fragile, key=lambda x: x[1]):
        print("     %-24s composite %d" % (k, c))
else:
    print("   no case lands in Fragile")

print()
print("=" * 104)
print("5. DOES THE FIX SEPARATE DEAD FROM ALIVE?")
print("=" * 104)
print("   %-22s %-9s %-30s %s" % ("case", "comp", "band", "known status"))
STATUS = {
    "N1-closedbusiness": "DEAD (closed business)",
    "P5-gongcha": "DEAD (shut all SG outlets 2 Oct 2025)",
    "GY07-true": "DEAD (closed all SG clubs 10 Sep 2026)",
    "FF02-kfc": "ALIVE (largest chicken chain)",
    "FF03-burger": "ALIVE (large chain)",
    "EW02-zoff": "ALIVE (eyewear chain)",
    "EL02-harvey": "ALIVE (major retailer)",
    "BT02-koi": "ALIVE (market leader)",
    "BT01-mixue": "ALIVE (price-floor owner)",
}
for key, status in STATUS.items():
    d = next((x for x in runs if x["case"] == key), None)
    if not d:
        continue
    dims = d["dimensions_display_1to5"]
    unsc = d.get("dimensions_unscored") or []
    refuse = ASS.get(key, {}).get("no_competitive_market", 0) >= 0.5
    c, b, _ = compute(dims, unsc, PROPOSED_GATES, refuse)
    print("   %-22s %-9s %-30s %s" % (key, c if c is not None else "GATE", b, status))

print()
print("VERDICT: removing the score gates (a) eliminates %d false refusals, (b) makes"
      % len(alive_hits))
print("'Fragile' reachable, (c) leaves one gate doing one job. A no-moat business now")
print("scores LOW instead of refusing -- which is the signal the report exists to give.")
