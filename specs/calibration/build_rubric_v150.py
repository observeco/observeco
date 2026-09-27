"""Build rubric v1.5.0 — fix mental_advantage (offset +0.46, disputes 11.7%, largest).

THE DEFECT, visible in the diagnostic:

  Harvey Norman  me 2  Sean 5    Courts  me 3  Sean 5
  Best Denki     me 2  Sean 4    Donki   me 3  Sean 5

  Harvey Norman's stated position: "Large-format showrooms where you can compare the whole
  range in one visit." My ladder scored it 2 = "retrieved for NO occasion more than any
  other option; an also-ran". But "I want to see the whole range side by side before
  buying" IS an occasion, and Harvey Norman is a first thought for it. Its ADDRESSABLE
  SEGMENT is not "all electronics buyers" -- it is buyers who want to compare in person.
  Against that segment it is a reference point.

THREE CAUSES, all the same class as RS and DR:

  1. THE SEGMENT WAS THE INDUSTRY, NOT THE ADDRESSABLE SEGMENT. I judged Harvey Norman
     against "electronics" and Donki against "supermarket", so each was compared to every
     occupant of a broad industry instead of its own buyers. Sean's own principle again:
     positioning is about product categories, not industries.

  2. THE `undercut_on` CONFESSION WAS TREATED AS THE VERDICT. Every one of these carries a
     candid self-criticism ("no price reason to choose us", "most baskets go to FairPrice").
     Same mechanical cause as RS. Honesty in the form was being punished.

  3. THE SCORE DEPENDED ON WHETHER *I* COULD ARTICULATE AN OCCASION. This is the giveaway:
     McDonald's scored 5 while Courts scored 3, though both are mass-market and equally
     known. The only difference is that I happened to name a retrieval occasion for
     McDonald's. That is the "score the submission, not the business" error in its purest
     form -- the model's fluency was standing in for the market's memory.

ONE CHANGE: retrieval is judged for the occasions the business's OWN addressable segment
has, against other occupants of that segment; and because the submission cannot prove the
ABSENCE of market memory, a low score now requires positive evidence.
"""
import copy
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
src = json.loads((HERE / "rubric-v1.4.1.json").read_text())
new = copy.deepcopy(src)

MA_INSTR = (
    "Judge mental_advantage: how strongly is this business retrieved from memory within its "
    "ADDRESSABLE SEGMENT for the buying occasions that segment has? "
    "The segment is the group of buyers this business can actually serve, NOT the whole "
    "industry it sits in. A business that serves a distinct buyer group must be judged "
    "against the occupants of THAT group, not against every occupant of a broad industry -- "
    "positioning is about product categories, not industries. A large-format showroom is "
    "retrieved by buyers who want to compare in person; a mid-market mass retailer is "
    "retrieved by buyers who want a known name and a local store. Both can be reference "
    "points for their own segment at the same time. "
    "CORROBORATE against physical evidence. A business with a large, established presence "
    "-- many outlets, a long trading history, sustained revenue at a published price -- is "
    "demonstrably retrieved by its segment. The submission cannot prove the ABSENCE of "
    "market memory, so a score of 1 or 2 requires positive evidence that the business is "
    "NOT retrieved (it has ceased trading, it is not recognised, or its segment cannot name "
    "it), not merely that the form did not describe an occasion. The form's `undercut_on` "
    "field is the business declaring its own weakness: that is context, not evidence, and "
    "candour must not be scored as absence of mental presence. "
    "Judge whether the SEGMENT retrieves it, not whether you can personally articulate an "
    "occasion for it."
)

MA_LEVELS = [
    "Not retrieved. Positive evidence the segment does not recognise it -- ceased, dormant, "
    "or unknown even to the buyers it names.",
    "Weakly present. Recognised as an option but retrieved for no occasion more than its "
    "rivals are; buyers would accept it but do not reach for it.",
    "At expectation for its segment. Retrieved for its occasions at roughly the level other "
    "occupants of the same addressable segment achieve, with no clear retrieval advantage.",
    "Strong retrieval. The first or near-first thought within its addressable segment for at "
    "least one valuable, frequently-occurring buying occasion.",
    "Owns the segment. The default first thought within its addressable segment for one or "
    "more valuable occasions, and rivals are not close.",
]

new["questions"]["mental_advantage"]["instructions"] = MA_INSTR
new["questions"]["mental_advantage"]["levels"] = MA_LEVELS
assert new["_meta"]["version"] == "1.4.1"
new["_meta"]["version"] = "1.5.0"
new["version"] = "1.5.0"
new["_changelog"] = src.get("_changelog", []) + [{
    "version": "1.5.0",
    "change": "mental_advantage: judge retrieval within the business's ADDRESSABLE SEGMENT "
              "(not the industry); 1-2 require positive evidence of non-retrieval; "
              "undercut_on is context, not evidence.",
    "why": "Harvey Norman scored 2 vs Sean's 5 while McDonald's scored 5 and Courts 3, all "
           "mass-market and equally known -- the score turned on whether the model could "
           "articulate an occasion, i.e. on submission fluency rather than market memory. "
           "Same defect class as the RS and DR fixes.",
}]

for d in ("relative_strength", "defensibility", "competitive_room", "market_headroom",
          "demand_reach"):
    assert new["questions"][d] == src["questions"][d], "control failed: %s" % d

(HERE / "rubric-v1.5.0.json").write_text(json.dumps(new, indent=2) + "\n")
print("wrote rubric-v1.5.0.json  (_meta.version=%s)" % new["_meta"]["version"])
print("CONTROL PASSED: other five dimensions byte-identical to v1.4.1")
print()
print("PREDICTIONS: Harvey Norman 2->>=4 (his 5), Best Denki 2->>=4 (4),")
print("             Courts 3->>=4 (5), Donki 3->>=4 (5)")
print("GUARDS (must NOT inflate): True Fitness stays low, home studios stay low,")
print("             closed bubble tea outlet DR stays 2, Sephora RS stays >=4")
