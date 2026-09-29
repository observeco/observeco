"""Build rubric v1.0.0 — the six-dimension realignment.

Sean's decisions (D1-D3 + new dimension):
  D1  mental_advantage AMENDED to his construct: size-anchored on the ADDRESSABLE SEGMENT.
  D2  demand_reach UNCHANGED (his explicit preference for my definition).
  D3  competitive_room + market_headroom stay in the score.
  NEW position_strength: quality of the current position relative to competitors.

Written as a NEW file so 0.9.0 survives as the baseline for comparison after his regrade.
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
src = json.loads((HERE / "rubric.json").read_text())

META = src["_meta"]

# ---------------------------------------------------------------- D1: amend MA
MA_INSTR = (
    "Judge ONLY mental advantage: among the buyers this business can ACTUALLY SERVE, how "
    "strongly is it retrieved when a buying occasion fires? First establish the ADDRESSABLE "
    "SEGMENT -- the buyers within this business's realistic reach given its size and "
    "footprint. A home baker's addressable segment is its estate, not the island; a national "
    "chain's is the island. Then, for each buying situation inside that segment, ask whether "
    "this business is the one that comes to mind, and how firmly. This is RELATIVE TO THE "
    "ADDRESSABLE SEGMENT, never absolute: a large brand holding its segment against expected "
    "erosion is an advantage, and a tiny business owning an occasion across its segment is "
    "also an advantage. Judge RETRIEVAL inside the segment, not familiarity at large -- a "
    "business can be widely known and still be nobody's first thought."
)
MA_LEVELS = [
    "Not retrieved. Within its addressable segment it is not a first thought for any buying "
    "occasion, and is barely recognised as an option at all.",
    "Weakly present. Known inside the segment but retrieved for no occasion more than any "
    "other option; an also-ran that buyers would accept but never seek.",
    "At expectation for the segment. Retrieved for its occasions at roughly the level a "
    "business of its reach would be expected to achieve; neither advantaged nor "
    "disadvantaged.",
    "Strong retrieval. The first or near-first thought within its addressable segment for "
    "one or more valuable, frequently-occurring buying occasions.",
    "Owns the segment. The default first thought within its addressable segment for one or "
    "more valuable occasions, and rivals are not close on those occasions.",
]

# ------------------------------------------------- NEW: position_strength
RS_INSTR = (
    "Judge ONLY relative strength: how strong is this business's CURRENT POSITION against "
    "the competitors in its DERIVED COMPETITIVE SET? The yardstick is the NAMED occupants of "
    "that set -- not the market in general, not a hypothetical rival, and not a business of "
    "the same size. First establish the buying situations in the category and the derived "
    "competitive set. Then, for each, ask where this business ACTUALLY STANDS against those "
    "specific occupants: share of the occasions, footprint (outlets, coverage, catchment), "
    "price position, and any documented buyer preference. Judge the OBSERVED standing on "
    "published or stated evidence -- never the business's own claim about itself, and never "
    "size alone, since a large occupant can still be losing position to a smaller one. "
    "3 = parity with the median occupant of the set. Above 3 = it holds more than the median "
    "occupant. Below 3 = it holds less."
)
RS_LEVELS = [
    "Absent from the set. It does not hold a position against the named occupants at all -- "
    "it is not a factor buyers weigh for any situation in this category.",
    "Marginal. Present but weaker than almost every occupant of the set; a fringe or "
    "declining option that holds no situation against those specific rivals.",
    "At parity. Holds its position at roughly the level of the median occupant of the set; "
    "no clear advantage or disadvantage against those specific rivals.",
    "Strong. Holds one or more situations more firmly than most occupants of the set; "
    "ranked near the top of its derived set on footprint, preference or price position.",
    "Dominant. The clear leader within its derived set on the situations that matter -- the "
    "reference point the other occupants position themselves against.",
]

src["questions"]["mental_advantage"]["instructions"] = MA_INSTR
src["questions"]["mental_advantage"]["levels"] = MA_LEVELS
src["questions"]["mental_advantage"]["_amended"] = (
    "2026-09-27 (Sean D1): anchor changed from 'what a business of its size would be "
    "expected to own' (an undefined benchmark) to 'the ADDRESSABLE SEGMENT'. His construct."
)

src["questions"]["relative_strength"] = {
    "type": "score",
    "instructions": RS_INSTR,
    "levels": RS_LEVELS,
    "_added": ("2026-09-27 (Sean): the axis the objective always required -- 'positioning "
               "and differentiation RELATIVE TO COMPETITION' -- and the instrument never "
               "had. Anchored on the derived competitive set, not on size expectation."),
}

# ------------------------------------------------------------ weights (6 dims)
NEW_WEIGHTS = {
    "relative_strength": 25,   # the objective: where you actually stand
    "mental_advantage": 20,    # retrieval among your addressable buyers
    "defensibility": 20,       # can you hold it
    "competitive_room": 15,    # is there space in this market
    "market_headroom": 10,     # is there unmet demand
    "demand_reach": 10,        # have you defined your buyer
}
META["weights"] = NEW_WEIGHTS
META["version"] = "1.0.0"
META["_changelog_1_0_0"] = [
    "NEW relative_strength (25%) -- position vs the DERIVED competitive set. Fixes the "
    "missing axis: McDonald's SG 150+ outlets scored 47 vs Jollibee 26 outlets 57.",
    "mental_advantage AMENDED (25->20%) to Sean's construct: retrieved among the buyers you "
    "can actually serve. Removes the undefined 'expected of its size' benchmark.",
    "defensibility 25->20%, competitive_room 20->15%, market_headroom 15->10%, "
    "demand_reach 15->10% to make room without growing the instrument's total burden.",
    "The 70/30 positioning-vs-other split is preserved: relative_strength + mental_advantage "
    "+ defensibility = 65% positioning; competitive_room + market_headroom = 25% landscape; "
    "demand_reach = 10% addressability.",
    "demand_reach definition UNCHANGED (Sean D2). competitive_room and market_headroom stay "
    "in the score (Sean D3).",
]

# band edges: recompute from the level-mean convention (all-2 / all-3 / all-4)
# weighted mean x 19.1667 scaling is version-specific; keep the existing band edges but
# record that they must be RE-DERIVED after the first v4 run.
META["_bands_note"] = (
    "Band edges are carried from 0.9.0 and MUST be re-derived after the first v1.0.0 run "
    "with six dimensions. Do not treat band WORDS from this rubric as calibrated yet."
)

out = HERE / "rubric-v1.0.0.json"
out.write_text(json.dumps(src, indent=2))
print("wrote %s" % out.name)
print("  version   : %s" % META["version"])
print("  dimensions: %s" % list(src["questions"].keys()))
print("  weights   : %s" % json.dumps(NEW_WEIGHTS))
print("  total     : %d" % sum(NEW_WEIGHTS.values()))
print()
print("  MA levels : %d" % len(MA_LEVELS))
print("  RS levels : %d" % len(RS_LEVELS))
print()
print("  positioning share: %d%%" % (
    NEW_WEIGHTS["relative_strength"] + NEW_WEIGHTS["mental_advantage"]
    + NEW_WEIGHTS["defensibility"]))
print("  landscape share  : %d%%" % (
    NEW_WEIGHTS["competitive_room"] + NEW_WEIGHTS["market_headroom"]))
print("  addressability   : %d%%" % NEW_WEIGHTS["demand_reach"])
