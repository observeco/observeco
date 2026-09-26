"""ASSESSABILITY gate — "we cannot assess this business", for competitive markets.

Sean's correction: gates SHOULD exist. Their job is to tell the user that certain
businesses or industries cannot be assessed. They must be appropriate for the
businesses we want to serve — competitive markets.

Current 3 gates ask "is this business BAD?" (no demand, no room, no reach). Wrong job,
and they never fire. The right job is "can we assess this at all?"

The clearest unassessable case: a business with NO COMPETITORS. Positioning analysis
finds a place in the customer's mind that rivals haven't taken. With no rivals, the
method has nothing to work on. ASML is exactly that.

PRE-REGISTERED PREDICTIONS (written before running):
  MUST FIRE (cannot assess): E1-asml  -- sole supplier of EUV, no competitor exists
  MUST NOT FIRE (assessable):
    F1-boeing-airbus    -- a DUOPOLY. Boeing and Airbus compete hard for orders.
    F2-watsons-guardian -- a duopoly. Watsons and Guardian compete hard.
    all 17 other cases  -- ordinary businesses in competitive markets
  FALSIFIED IF: a duopoly or an ordinary business fires, OR ASML does not.

The discriminating pair is ASML vs Boeing/Airbus: both are extremely concentrated,
but only ASML has no competitive struggle. If the gate separates those two, it is
measuring assessability rather than size or concentration.
"""
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from run_jev import build_state, call_jev, read_env_key  # noqa: E402

MUST_FIRE = {"E1-asml"}
MUST_NOT_FIRE = {
    "F1-boeing-airbus", "F2-watsons-guardian", "F3-vicom", "N1-closedbusiness",
    "01-bonefirm", "07-observeco", "08-bubbletea", "09-koi", "C2-activesg",
    "C3-pet-lovers-centre", "C4-sheng-siong", "C5-michelin-hawker", "C6-euyansang",
    "C9-b2b-it-services", "D1-watsons", "D2-petlovers-cue", "E2-coupang-flywheel",
    "E4-bonefirm-ip", "N2-koi-stripped",
}

GATE = {
    "assessable": {
        "type": "choice",
        "instructions": "Positioning analysis finds a place in the customer's mind that "
                        "rivals have not already taken. That requires a market in which "
                        "more than one supplier competes for the same customers. "
                        "Does this business operate in such a market? Judge the MARKET "
                        "the business competes in, not the business's own quality.",
        "criteria": {
            "no_competitive_market": "No — this business is effectively the sole supplier, "
                                     "or customers have no meaningful alternative to it. "
                                     "There is no competitive struggle for position.",
            "competitive_market": "Yes — other suppliers compete for the same customers, "
                                  "so there is a struggle for position.",
        },
    },
}

rubric = json.loads((HERE / "rubric.json").read_text())
if not read_env_key("TYPESAFE_API_KEY"):
    print("no key"); sys.exit(2)

cache = HERE / "runs" / "assessability_gate.json"
store = json.loads(cache.read_text()) if cache.exists() else {}

inputs = sorted(p.stem for p in (HERE / "inputs").glob("*.json"))
rows = []
for case in inputs:
    if case in store:
        probs = store[case]
    else:
        payload = json.loads((HERE / "inputs" / f"{case}.json").read_text())
        res = call_jev(build_state(payload), GATE, rubric["_meta"]["model"])
        if res is None:
            print("  %-22s JEV UNAVAILABLE" % case); continue
        a = (res.get("answers") or {}).get("assessable") or {}
        probs = a.get("probabilities") or {}
        store[case] = probs
        cache.write_text(json.dumps(store, indent=2, sort_keys=True) + "\n")
        time.sleep(3)
    p = float(probs.get("no_competitive_market", 0))
    rows.append((case, p, p > 0.50))

rows.sort(key=lambda r: -r[1])
print("=" * 82)
print("ASSESSABILITY GATE — P(no competitive market). High = 'we cannot assess this'")
print("=" * 82)
print("%-24s %7s  %-7s %s" % ("case", "P(no)", "verdict", "expected"))
print("-" * 82)
for case, p, fires in rows:
    if case in MUST_FIRE:
        exp = "MUST FIRE" + ("" if fires else "   <-- MISSED")
    elif case in MUST_NOT_FIRE:
        exp = "must not fire" + ("   <-- OVER-FIRED" if fires else "")
    else:
        exp = "?"
    print("%-24s %7.2f  %-7s %s" % (case, p, "CANNOT" if fires else "assessable", exp))

fired = [c for c, p, f in rows if f]
missed = [c for c, p, f in rows if c in MUST_FIRE and not f]
over = [c for c, p, f in rows if c in MUST_NOT_FIRE and f]
print()
print("  fires on   : %s" % (fired or "nothing"))
print("  missed     : %s" % (missed or "none"))
print("  over-fired : %s" % (over or "none"))
print()
print("  VERDICT: %s" % (
    "FALSIFIED" if (over or missed) else "PASSED — separates the unassessable from the assessable"))
if "E1-asml" in dict((c, p) for c, p, f in rows):
    a = dict((c, p) for c, p, f in rows)["E1-asml"]
    d = [p for c, p, f in rows if c in MUST_NOT_FIRE]
    print("  ASML %.2f  vs  max among assessable %.2f  (separation %.2f)"
          % (a, max(d), a - max(d)))
print()
print("  The pair that matters — both extremely concentrated, only one unassessable:")
for c in ("E1-asml", "F1-boeing-airbus", "F2-watsons-guardian"):
    for cc, p, f in rows:
        if cc == c:
            print("    %-22s %.2f  %s" % (c, p, "CANNOT ASSESS" if f else "assessable"))
