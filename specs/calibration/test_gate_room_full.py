"""gate_room boolean over the FULL 20-case corpus.

FINDING-gate-boolean-test.md validated the boolean on n=6 with ONE positive (N1).
That is the thin-evidence pattern this project has been caught in repeatedly, so the
fix is not actionable until it is n=20. This is that run.

PRE-REGISTERED PREDICTION (written before running):
  gate_room fires ONLY on cases with no stated differentiator. Specifically:
    MUST fire    : N1-closedbusiness (no differentiator: "used the same supplier",
                   "drinks were similar")
    MUST NOT fire: every case with a stated differentiator, at margin > 0.3.
  UNCERTAIN (flagged in advance, not fitted after): N2-koi-stripped, 08-bubbletea
  FALSIFIED IF: a case with a clear differentiator exceeds 0.50.
"""
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from run_jev import build_state, call_jev, read_env_key  # noqa: E402

# cases with a stated differentiator -- predicted NOT to fire
HAS_DIFFERENTIATOR = {
    "01-bonefirm", "07-observeco", "09-koi", "C2-activesg", "C3-pet-lovers-centre",
    "C4-sheng-siong", "C5-michelin-hawker", "C6-euyansang", "C9-b2b-it-services",
    "D1-watsons", "D2-petlovers-cue", "E1-asml", "E2-coupang-flywheel",
    "E4-bonefirm-ip", "F1-boeing-airbus", "F2-watsons-guardian", "F3-vicom",
}
UNCERTAIN = {"N2-koi-stripped", "08-bubbletea"}
MUST_FIRE = {"N1-closedbusiness"}

GATE_ROOM = {
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
}

rubric = json.loads((HERE / "rubric.json").read_text())
if not read_env_key("TYPESAFE_API_KEY"):
    print("no key"); sys.exit(2)

prev = HERE / "runs" / "gate_boolean_test.json"
store = json.loads(prev.read_text()) if prev.exists() else {}

inputs = sorted(p.stem for p in (HERE / "inputs").glob("*.json"))
print("corpus cases: %d" % len(inputs))
print()

rows = []
for case in inputs:
    if case in store and "gate_room" in store[case]:
        probs = store[case]["gate_room"][1]
        src = "cached"
    else:
        payload = json.loads((HERE / "inputs" / f"{case}.json").read_text())
        res = call_jev(build_state(payload), GATE_ROOM, rubric["_meta"]["model"])
        if res is None:
            print("  %-22s JEV UNAVAILABLE" % case); continue
        a = (res.get("answers") or {}).get("gate_room") or {}
        probs = a.get("probabilities") or {}
        store.setdefault(case, {})["gate_room"] = [
            max(probs, key=lambda k: float(probs[k])) if probs else a.get("choice"), probs]
        src = "fresh"
        time.sleep(3)
    fires = float(probs.get("no_room_at_all", 0)) > 0.50
    rows.append((case, float(probs.get("no_room_at_all", 0)), fires, src))
    prev.write_text(json.dumps(store, indent=2, sort_keys=True) + "\n")   # survive a timeout

rows.sort(key=lambda r: -r[1])
print("=" * 78)
print("gate_room BOOLEAN — P(no room at all), all %d cases" % len(rows))
print("=" * 78)
print("%-24s %7s  %-6s %s" % ("case", "P(none)", "gate", "note"))
print("-" * 78)
for case, p, fires, src in rows:
    note = ""
    if case in MUST_FIRE:
        note = "MUST FIRE" + ("" if fires else "  <-- MISSED")
    elif case in UNCERTAIN:
        note = "uncertain (flagged in advance)"
    elif case in HAS_DIFFERENTIATOR:
        note = "has differentiator" + ("  <-- OVER-FIRED" if fires else "")
    print("%-24s %7.2f  %-6s %s" % (case, p, "FIRES" if fires else "pass", note))

print()
fired = [c for c, p, f, s in rows if f]
over = [c for c in fired if c in HAS_DIFFERENTIATOR]
missed = [c for c, p, f, s in rows if c in MUST_FIRE and not f]
print("  fired            : %d of %d  %s" % (len(fired), len(rows), fired))
print("  over-fired       : %s" % (over or "none"))
print("  missed must-fire : %s" % (missed or "none"))
print()
print("  VERDICT: %s" % (
    "FALSIFIED — fired on a case with a clear differentiator" if over else
    "MISSED — did not fire on the closed business" if missed else
    "PASSED — fires only where it should"))
d = [p for c, p, f, s in rows if c in HAS_DIFFERENTIATOR]
if d:
    print("  max P(none) among differentiator cases: %.2f  (separation %.2f)" % (max(d), 0.87 - max(d) if 'n1' else 0))
