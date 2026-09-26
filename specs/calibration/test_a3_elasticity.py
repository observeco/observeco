"""A3 classifier validation — does the MODEL's elasticity call reproduce the BLIND labels?

FINDING-elasticity-test.md classified all 17 cases BY HAND, blind to the scores.
That label set is the ground truth here. A3 is only safe to ship if the model
reproduces it -- otherwise A3 is gated on analyst judgement wearing a mechanism's
clothes, which is one of the standing blockers in this project.

The blind labels (from FINDING-elasticity-test.md):
  ELASTIC      n=12   1.78 - 1.98   mean 1.91
  INELASTIC    n= 2   2.43 - 3.33   mean 2.88   (ASML 3.33, C5 hawker 2.43*)
  AMBIGUOUS    n= 1   1.93                    (Coupang)
  INELASTIC-ish n=1   1.91                    (ActiveSG -- statutory gym, gym market elastic)
  N/A          n= 1   1.69                    (N1 closed)

* C5 was re-scoped to elastic on market-level reasoning (a hawker is firm-inelastic
  but the hawker market absorbs demand), so C5 is expected ELASTIC here.

PRE-REGISTERED: the model should return 'elastic' for the 12 elastic + C5 + ActiveSG
(the market, not the firm, is the judgement), 'inelastic' for ASML, and 'ambiguous'
for Coupang. FALSIFIED IF ASML is not inelastic, or if the elastic majority flips.

TOLERANCE: a judgement this subtle will not be perfect. The question is whether errors
are (a) occasional and (b) biased toward 'ambiguous' (safe -- it keeps the score)
rather than toward wrongly dropping a real inelastic case (unsafe -- it hides signal).
"""
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from run_jev import build_state, call_jev, read_env_key  # noqa: E402

# expected label from the blind hand classification
EXPECTED = {
    "01-bonefirm": "elastic", "07-observeco": "elastic", "08-bubbletea": "elastic",
    "09-koi": "elastic", "C2-activesg": "elastic", "C3-pet-lovers-centre": "elastic",
    "C4-sheng-siong": "elastic", "C5-michelin-hawker": "elastic",
    "C6-euyansang": "elastic", "C9-b2b-it-services": "elastic", "D1-watsons": "elastic",
    "D2-petlovers-cue": "elastic", "E2-coupang-flywheel": "ambiguous",
    "E4-bonefirm-ip": "elastic", "F2-watsons-guardian": "elastic",
    # F3-vicom is INELASTIC per its own input file and FINDING-midsized-test.md
    # ("INELASTIC (market-level, regulatory). Only operators authorised by the LTA may
    # perform mandatory vehicle inspections"). An earlier version of this script
    # labelled it "elastic" -- that was MY error, and the model's 0.99 inelastic call
    # was right. Corrected here.
    "F3-vicom": "inelastic",
    "E1-asml": "inelastic", "F1-boeing-airbus": "inelastic",
    "N1-closedbusiness": "elastic", "N2-koi-stripped": "elastic",
}

rubric = json.loads((HERE / "rubric.json").read_text())
if not read_env_key("TYPESAFE_API_KEY"):
    print("no key"); sys.exit(2)

Q = {"market_elasticity": {
    "type": "choice",
    "instructions": rubric["_meta"]["classifiers"]["market_elasticity"]["instructions"],
    "criteria": rubric["_meta"]["classifiers"]["market_elasticity"]["criteria"],
}}

cache = HERE / "runs" / "a3_elasticity_classification.json"
store = json.loads(cache.read_text()) if cache.exists() else {}

rows = []
for case in sorted(EXPECTED):
    if case in store:
        probs = store[case]
    else:
        p = HERE / "inputs" / f"{case}.json"
        if not p.exists():
            print("  %-22s input missing" % case); continue
        res = call_jev(build_state(json.loads(p.read_text())), Q, rubric["_meta"]["model"])
        if res is None:
            print("  %-22s JEV UNAVAILABLE" % case); continue
        a = (res.get("answers") or {}).get("market_elasticity") or {}
        probs = a.get("probabilities") or {}
        store[case] = probs
        cache.write_text(json.dumps(store, indent=2, sort_keys=True) + "\n")
        time.sleep(3)
    got = max(probs, key=lambda k: float(probs[k])) if probs else None
    rows.append((case, EXPECTED[case], got, float(probs.get(got, 0)), probs))

print("=" * 90)
print("A3 ELASTICITY CLASSIFIER vs BLIND HAND LABELS")
print("=" * 90)
print("%-24s %-11s %-11s %5s  %s" % ("case", "expected", "model", "conf", "verdict"))
print("-" * 90)
ok = off = 0
offense = []
for case, exp, got, conf, probs in rows:
    if exp == got:
        v = "OK"; ok += 1
    elif got == "ambiguous":
        v = "safe-miss (ambiguous keeps the score)"; ok += 1
    else:
        v = "MISMATCH"; off += 1; offense.append((case, exp, got, conf))
    print("%-24s %-11s %-11s %5.2f  %s" % (case, exp, got or "-", conf, v))

print()
print("  agreed            : %d of %d" % (ok, len(rows)))
print("  genuine mismatch  : %d" % off)
for c, e, g, cf in offense:
    print("     %-24s expected %s, model said %s (%.2f)" % (c, e, g, cf))
print()
asml = [r for r in rows if r[0] == "E1-asml"]
if asml:
    _c, _e, g, _cf, _p = asml[0]
    print("  CRITICAL — ASML (a wrong call here hides real signal): %s" % g.upper())
    print("  VERDICT: %s" % (
        "FALSIFIED" if (off > 2 or (asml and g != "inelastic")) else
        "USABLE" if off == 0 else
        "USABLE WITH CAVEAT — %d mismatch(es)" % off))
