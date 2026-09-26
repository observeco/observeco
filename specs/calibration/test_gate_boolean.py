"""Does an explicit BOOLEAN gate question fire where the continuous dimension cannot?

Diagnosis from FINDING-floor-investigation.md: the gates key on a continuous score,
and the model never returns display 1 on market_headroom / competitive_room /
demand_reach -- so those gates can never fire. A boolean asks the gate's actual
meaning directly, independent of where the model puts its probability mass.

This tests the proposed fix BEFORE recommending it. If the boolean is just as inert,
the fix is wrong and the recommendation changes.
"""
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from run_jev import build_state, call_jev, read_env_key  # noqa: E402

CASES = [
    ("N1-closedbusiness", "closed business — the ONLY case that currently gates"),
    ("F3-vicom", "inelastic + met — should NOT gate on demand"),
    ("D1-watsons", "competitive_room raw 0.89 — lowest room in corpus"),
    ("08-bubbletea", "legacy GATE-boundary case (53) — contested"),
    ("C9-b2b-it-services", "competitive_room raw ~0.9 range"),
    ("N2-koi-stripped", "stripped variant"),
]

# Each gate question asks the gate's MEANING directly, with an explicit
# "there is none at all" option. Two options, so the model must choose.
GATE_QUESTIONS = {
    "gate_demand": {
        "type": "choice",
        "instructions": "Considering ONLY the product CATEGORY this business competes in, "
                        "is there any identifiable buying demand for that category at all, "
                        "from any supplier? Judge the category, not this specific business.",
        "criteria": {
            "no_demand_at_all": "The category has no identifiable buying demand from any "
                                "supplier — nobody is buying this kind of product at all.",
            "some_demand_exists": "There is identifiable buying demand for this category.",
        },
    },
    "gate_room": {
        "type": "choice",
        "instructions": "Does this business have ANY meaningful competitive room — any space "
                        "in the customer's mind, or any way to be chosen over the competitors "
                        "listed, that is not already fully occupied by them?",
        "criteria": {
            "no_room_at_all": "No meaningful competitive room exists — every position a "
                              "customer could want is already occupied by a competitor, "
                              "and this business has no way to be preferred.",
            "some_room_exists": "There is some meaningful competitive room available.",
        },
    },
    "gate_reach": {
        "type": "choice",
        "instructions": "Can this business reach enough customers to be viable at all, "
                        "given what is known about how it would get to market?",
        "criteria": {
            "no_reachable_customers": "No viable route to enough customers exists at all — "
                                      "the business cannot reach a customer base.",
            "some_route_exists": "There is some viable route to customers.",
        },
    },
}

rubric = json.loads((HERE / "rubric.json").read_text())
key = read_env_key("TYPESAFE_API_KEY")
if not key:
    print("no TYPESAFE_API_KEY"); sys.exit(2)

print("=" * 100)
print("BOOLEAN GATE TEST — does asking the gate's meaning directly fire where the")
print("continuous dimension cannot?  (current rule: display < 2 => never fires)")
print("=" * 100)
print()

results = {}
for case, note in CASES:
    p = HERE / "inputs" / f"{case}.json"
    if not p.exists():
        print(f"  {case}: input not found"); continue
    payload = json.loads(p.read_text())
    # the run files are keyed by the case name inside _meta, not the filename
    run = HERE / "runs" / f"jev-{case}.json"
    state = build_state(payload)
    res = call_jev(state, GATE_QUESTIONS, rubric["_meta"]["model"])
    if res is None:
        print(f"  {case}: JEV UNAVAILABLE"); continue
    ans = (res.get("answers") or {})
    row = {}
    for g in GATE_QUESTIONS:
        a = ans.get(g) or {}
        probs = a.get("probabilities") or {}
        # the boolean's own vote
        choice = max(probs, key=lambda k: float(probs[k])) if probs else a.get("choice")
        row[g] = (choice, probs)
    results[case] = row

    cur = json.loads(run.read_text()) if run.exists() else {}
    cur_disp = cur.get("dimensions_display_1to5", {})
    cur_fires = cur.get("gates_firing", [])
    print(f"  {case}   ({note})")
    print(f"    current continuous: hd={cur_disp.get('market_headroom')} "
          f"cr={cur_disp.get('competitive_room')} dr={cur_disp.get('demand_reach')}"
          f"  -> gates firing: {cur_fires or 'none'}")
    for g, (choice, probs) in row.items():
        inert = "  <-- FIRES (would gate)" if str(choice).startswith("no_") else ""
        print(f"    {g:14} {choice:22} {json.dumps(probs, sort_keys=True)}{inert}")
    print()
    time.sleep(2)

(out := HERE / "runs" / "gate_boolean_test.json").write_text(
    json.dumps(results, indent=2, sort_keys=True) + "\n")
print(f"raw -> {out.relative_to(HERE)}")
