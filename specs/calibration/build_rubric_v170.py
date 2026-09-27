"""Build rubric v1.7.0 — mental_advantage redefined on Sean's answer.

SEAN, verbatim:
  "Mental advantage is how much the brand holds in the mind of the customer correct?
   That the answer to your first question."
  "Gong cha is in the mental ladder of Singaporean, that's why it has a mental advantage,
   and it should be independent on closure."

WHAT THIS SETTLES, and both were questions I had flagged as needing his answer:

1. THE CONSTRUCT. MA is HOW MUCH THE BRAND HOLDS IN THE MIND OF THE CUSTOMER -- a pure
   magnitude of mental holding. My level 5 said "rivals are not close", which is a
   COMPETITIVE claim and the wrong axis entirely. That is why Sean scores 5 for Courts,
   Donki, Harvey Norman and Cold Storage (prices converge within 3-8%) while I scored 3-4:
   I was demanding exclusivity where he was measuring how much mind the brand occupies.
   A brand can hold a great deal of mind while its rivals are close. Those are independent.

2. CLOSURE IS IRRELEVANT. "It should be independent on closure." Gong Cha (closed all 29
   SG outlets) scored 1 under my v1.5.0 rule that treated cessation as evidence of
   non-retrieval. WRONG: Gong Cha is in the mental ladder of Singaporeans, so it holds a
   mental advantage regardless of whether it still trades. Sean scores it 4.

   THIS IS THE DIMENSION-SPECIFICITY PRINCIPLE, now stated by Sean directly: closure
   destroys REACH (demand_reach -- he agrees the closed outlet is 2) but NOT MEMORY
   (mental_advantage). The SAME physical fact has OPPOSITE implications per dimension, so
   corroboration rules must be dimension-specific. My one shared "physical evidence"
   doctrine was too blunt -- v1.6.0 got this right for DR and wrong for MA.

THE LADDER is now a magnitude scale: how much of the customer's mind the brand holds, from
absent to the defining association. No competitive clause, no closure clause.
"""
import copy
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
src = json.loads((HERE / "rubric-v1.6.0.json").read_text())
new = copy.deepcopy(src)

MA_INSTR = (
    "Judge mental_advantage: HOW MUCH THE BRAND HOLDS IN THE MIND OF THE CUSTOMER. This is "
    "a measure of mental holding only -- the share of mind the brand occupies within its "
    "addressable segment. "
    "It is NOT a competitive measure: a brand can hold a great deal of mind while close "
    "rivals hold a similar amount, so do NOT require the business to be uncontested, "
    "dominant, or have rivals who 'are not close'. Judge the magnitude of what it holds in "
    "the mind, not its exclusivity. "
    "It is INDEPENDENT OF CLOSURE. Mental presence persists after a business stops trading: "
    "a brand that is part of the mental ladder of its market still holds a mental advantage "
    "even if it has closed, gone dormant, or left the market. Never reduce this score "
    "because the business has ceased trading, and never treat cessation as evidence of "
    "absent mind. "
    "CORROBORATE against evidence of MENTAL presence, not trading status: longevity in the "
    "market, ubiquity, whether the brand is the one people name when the category comes up, "
    "whether it defines the category or an occasion, how large a share of the segment would "
    "recognise and recall it. The form's `undercut_on` field is the business declaring its "
    "own weakness -- context, never evidence, and candour must not be scored as absence of "
    "mental presence. Judge whether the SEGMENT holds it in mind, not whether you can "
    "personally articulate an occasion for it."
)

MA_LEVELS = [
    "Absent from the mind. The segment would not know the brand or recall it at all; it "
    "holds no mental space.",
    "Faintly held. Barely present: the segment might recognise the name if prompted, but "
    "would not think of it on its own.",
    "Present. A recognised option that surfaces when the category is considered -- real "
    "mental space, but ordinary for a business of its reach.",
    "Strongly held. Comes to mind unprompted for its occasions, and is among the first names "
    "the segment thinks of; a substantial share of mind.",
    "Deeply held. The defining association -- the brand that first comes to mind and stands "
    "for the category or the occasion itself; the greatest mental holding in its segment.",
]

new["questions"]["mental_advantage"]["instructions"] = MA_INSTR
new["questions"]["mental_advantage"]["levels"] = MA_LEVELS
assert new["_meta"]["version"] == "1.6.0"
new["_meta"]["version"] = "1.7.0"
new["version"] = "1.7.0"
new["_changelog"] = src.get("_changelog", []) + [{
    "version": "1.7.0",
    "change": "mental_advantage redefined on Sean's answer: HOW MUCH THE BRAND HOLDS IN THE "
              "MIND OF THE CUSTOMER. Removed the competitive clause ('rivals are not "
              "close') and made it explicitly INDEPENDENT OF CLOSURE.",
    "why": "Sean: 'Mental advantage is how much the brand holds in the mind of the "
           "customer... Gong cha is in the mental ladder of Singaporean, that's why it has "
           "a mental advantage, and it should be independent on closure.' My level 5 "
           "demanded exclusivity (wrong axis -- explains the 5s for Courts/Donki/Harvey "
           "Norman/Cold Storage whose prices converge within 3-8%), and v1.5.0 scored "
           "closed Gong Cha 1 vs his 4. Closure destroys REACH (demand_reach, he agrees 2) "
           "but not MEMORY (mental_advantage) -- corroboration must be dimension-specific.",
}]

for d in ("relative_strength", "defensibility", "competitive_room", "market_headroom",
          "demand_reach"):
    assert new["questions"][d] == src["questions"][d], "control failed: %s" % d

(HERE / "rubric-v1.7.0.json").write_text(json.dumps(new, indent=2) + "\n")
print("wrote rubric-v1.7.0.json  (_meta.version=%s)" % new["_meta"]["version"])
print("CONTROL PASSED: other five dimensions byte-identical to v1.6.0")
print()
print("PREDICTIONS:")
print("  Gong Cha      1 -> 4   (his 4) -- closure must NOT suppress it")
print("  Courts        4 -> 5   (his 5)")
print("  Donki         3 -> 5   (his 5)")
print("  Harvey Norman 3 -> 5   (his 5)")
print("  Cold Storage  4 -> 5   (his 5)")
print("  Best Denki    3 -> 4   (his 4)")
print("GUARDS (must STAY low): True Fitness (holds little mind),")
print("  Lash Fairy / small studios (~2), home-not-permitted cases")
print("GUARDS (other dims unchanged): Sephora RS 4, closed outlet DR 2")
