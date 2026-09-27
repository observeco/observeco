"""Build rubric v1.3.2 — put ceased businesses at the RIGHT level.

TWO CORRECTIONS ALREADY MADE, both caught by testing rather than reasoning:

  v1.2.0  closed outlet scored 2   Sean scored 2   -> v1.2.0 was RIGHT here
  v1.3.0  closed outlet scored 3   WRONG (trading floor applied to a dead business)
  v1.3.1  closed outlet scored 1   WRONG the other way (lumped with 'no buyer')
  v1.3.2  closed outlet must score 2

The error in v1.3.1 was CONFLATING TWO DIFFERENT LEVEL-1 CONDITIONS. Level 1 should mean
"there is no identifiable buyer" or "the business cannot legally serve buyers". A business
that has ceased trading has an IDENTIFIABLE buyer group -- it simply cannot reach them any
more. That is the definition of level 2, and Sean's 2 for the closed outlet says exactly that.

So: remove the ceased-trading clause from level 1, and make level 2 explicitly the home for
ceased/dormant businesses.

CHECKED AGAINST EVERY CASE SEAN RULED ON:
  A closed bubble tea outlet   his 2  -> must be 2   (ceased, buyer identifiable)
  A dormant home baker         his 2  -> must be 2   (dormant, buyer identifiable)
  A home massage service       his 3  -> must be 1   (he AGREED with my 1: not permitted)
  Best Denki / 24-7 / Zoff     his 4-5 -> must be >=3 (currently trading)
"""
import copy
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
src = json.loads((HERE / "rubric-v1.3.1.json").read_text())
new = copy.deepcopy(src)

DR_INSTR = src["questions"]["demand_reach"]["instructions"]
DR_INSTR = DR_INSTR.replace(
    " A business that has ceased trading does not qualify for the trading floor, and its "
    "reach is judged on its current state alone.",
    " A business that has ceased trading does not qualify for the trading floor: it has an "
    "identifiable buyer group but no longer reaches it, which is level 2, not level 1. "
    "Level 1 is reserved for a business with NO identifiable buyer, or one that cannot "
    "legally serve the buyers it names."
)

DR_LEVELS = [
    "No identifiable buyer. The customer is undefined, OR the business cannot legally "
    "serve the buyers it names (for example a use not permitted at that premises).",
    "Weak. EITHER a buyer group is named only as a demographic or category with no evidence "
    "of current reach, OR the business has ceased or gone dormant so that it no longer "
    "reaches the buyers it once served. A ceased business belongs here, not at 1: its buyer "
    "group is identifiable, it simply cannot reach them. Any business CURRENTLY trading is "
    "at least 3.",
    src["questions"]["demand_reach"]["levels"][2],
    src["questions"]["demand_reach"]["levels"][3],
    src["questions"]["demand_reach"]["levels"][4],
]

new["questions"]["demand_reach"]["instructions"] = DR_INSTR
new["questions"]["demand_reach"]["levels"] = DR_LEVELS
assert new["_meta"]["version"] == "1.3.1"
new["_meta"]["version"] = "1.3.2"
new["version"] = "1.3.2"
new["_changelog"] = src.get("_changelog", []) + [{
    "version": "1.3.2",
    "change": "demand_reach: a ceased/dormant business is level 2, not level 1. Level 1 is "
              "reserved for no-identifiable-buyer or cannot-legally-serve. The trading floor "
              "still requires CURRENT trade.",
    "why": "v1.3.1 sent ceased businesses to level 1, contradicting Sean's 2 for both the "
           "closed bubble tea outlet and the dormant home baker. A ceased business has an "
           "identifiable buyer group but no current route -- exactly level 2.",
}]

for d in ("relative_strength", "mental_advantage", "defensibility",
          "competitive_room", "market_headroom"):
    assert new["questions"][d] == src["questions"][d], "control failed: %s" % d

(HERE / "rubric-v1.3.2.json").write_text(json.dumps(new, indent=2) + "\n")
print("wrote rubric-v1.3.2.json  (_meta.version=%s)" % new["_meta"]["version"])
print("CONTROL PASSED: other five dimensions byte-identical")
print()
print("EXPECTED after this run (the four cases Sean ruled on):")
print("  A closed bubble tea outlet  2   (was 1 in v1.3.1)")
print("  A dormant home baker        2   (was 1 in v1.3.1)")
print("  A home massage service      1   (must not move)")
print("  Best Denki / 24-7 / Zoff   >=3  (must not regress)")
