"""Build rubric v1.4.0 — fix relative_strength (25% weight, the largest dispute cluster).

THE DEFECT, visible in the output rather than inferred:

  Sephora Singapore   me 2  Sean 5
     form: "The premium beauty destination. Exclusive international brands list with us
            first before going to the mass chains."  7% share vs Watsons' 18%
     My ladder put it at 2 = "weaker than almost every occupant; fringe or declining".

  Sephora is not competing with Watsons for the mass market. It OWNS the premium beauty
  destination -- the international brands list there FIRST. Judged as a head-on share fight
  against Watsons it looks marginal; judged on the situation it actually competes in, it is
  dominant. Same shape for Don Don Donki (owns Japanese imports / late-night, not the weekly
  shop), Polar Puffs (owns old-school local pastry), ROA, Bonefirm.

  ROOT CAUSE: my ladder anchors on "the median occupant OF THE SET", and the set is read as
  every named competitor. So a specialist that dominates a DISTINCT SITUATION is scored as
  though it were losing a head-on fight it never entered. Sean's own principle, stated
  earlier: positioning is about PRODUCT CATEGORIES, not industries.

  A SECOND, MECHANICAL CAUSE: the form's `undercut_on` field is the business SELF-DECLARING
  its weakness, and the scorer is treating that confession as the verdict. Every one of the
  big misses has a candid undercut_on ("most baskets still go to FairPrice"). Honesty in the
  form is being punished. Same class of error as the DR defect: judging the SUBMISSION
  rather than the BUSINESS.

TWO CHANGES (single dimension, others asserted byte-identical):
  1. Position is judged PER SITUATION the business competes in, not as one share fight
     against the whole named set. Dominating a distinct situation is strength.
  2. Self-reported weakness in `undercut_on` is context, NOT evidence. Corroborate the
     position against physical facts; do not score the confession.
"""
import copy
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
src = json.loads((HERE / "rubric-v1.3.2.json").read_text())
new = copy.deepcopy(src)

RS_INSTR = (
    "Judge relative_strength: for each buying SITUATION the business actually competes in, "
    "how strong is its hold compared with the named occupants of that situation? "
    "IMPORTANT: judge the business per situation, NOT as one share fight against the whole "
    "named set. Businesses that serve different situations are not head-on rivals even when "
    "they appear in the same industry -- positioning is about product categories, not "
    "industries. A specialist that owns a distinct situation (the premium destination, the "
    "late-night Japanese-import run, the old-school local pastry) is strong on that "
    "situation even if it is small in overall share, and must NOT be scored as marginal "
    "merely because a mass-market occupant is bigger. A business is only marginal if it "
    "holds no situation at all. "
    "CORROBORATE against physical facts. The form's `undercut_on` field is the business "
    "declaring its own weakness -- treat it as context, not as the verdict. Candid honesty "
    "in a submission is not evidence of a weak position, and a business must not be marked "
    "down for admitting what it does not do."
)

RS_LEVELS = [
    "Absent. Holds no position in any situation it enters -- not a factor buyers weigh.",
    "Marginal. Holds no situation of its own: it competes head-on and loses on the same "
    "axis as larger occupants, with nothing buyers would choose it for.",
    "At parity. Holds its situations at roughly the level of the other occupants, with no "
    "clear advantage or disadvantage on any of them.",
    "Strong. Holds at least one situation more firmly than most other occupants of it -- a "
    "recognised position buyers select it for, even if it is smaller overall.",
    "Dominant. The reference occupant of at least one situation it competes in -- the "
    "business others are defined against, whether or not it is the largest overall.",
]

new["questions"]["relative_strength"]["instructions"] = RS_INSTR
new["questions"]["relative_strength"]["levels"] = RS_LEVELS
assert new["_meta"]["version"] == "1.3.2"
new["_meta"]["version"] = "1.4.0"
new["version"] = "1.4.0"
new["_changelog"] = src.get("_changelog", []) + [{
    "version": "1.4.0",
    "change": "relative_strength: judge position PER SITUATION, not as one share fight "
              "against the whole named set. `undercut_on` is context, not evidence.",
    "why": "Sephora (owns the premium destination; 7% share) scored 2 vs Sean's 5. The "
           "ladder anchor 'median occupant of the set' made every specialist look marginal "
           "against a larger mass-market occupant. Same class as the DR defect: judging the "
           "submission instead of the business.",
}]

for d in ("mental_advantage", "defensibility", "competitive_room", "market_headroom",
          "demand_reach"):
    assert new["questions"][d] == src["questions"][d], "control failed: %s" % d

(HERE / "rubric-v1.4.0.json").write_text(json.dumps(new, indent=2) + "\n")
print("wrote rubric-v1.4.0.json  (_meta.version=%s)" % new["_meta"]["version"])
print("CONTROL PASSED: other five dimensions byte-identical to v1.3.2")
print()
print("PREDICTIONS TO TEST:")
print("  Sephora RS  2 -> >=4   (his 5)")
print("  Don Don Donki RS 2 -> >=4  (his 4)")
print("  Polar Puffs RS 2 -> >=4  (his 4)")
print("  Bonefirm RS 2 -> >=4  (his 4)")
print("  A closed bubble tea outlet DR must stay 2  (regression guard)")
