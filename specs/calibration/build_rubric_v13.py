"""Build rubric v1.3.0 — the demand_reach corroboration fix (single variable).

SEAN'S CHARGE, and he is right:
  "Best Denki, 24/7 Fitness, Zoff Singapore are able to generate revenue which means it is
   able to reach out to successfully attract customers. That automatically challenges your
   'no evidence they will pay this price'."
  "BreadTalk has no issues generating revenue and reaching out to the demand. I would not
   condemn them to their lack of halal certification or artisan abilities to give them a 3.
   They are fit for purpose for their customer segment."

THE DEFECT, located in the instruction text:
  "Consider whether the customer is DESCRIBED in a way that identifies a real group..."
                          ^^^^^^^^
  The dimension tests the QUALITY OF THE SUBMISSION, not the business. A business trading
  at a published price through 7 outlets is scored as though it had no route to buyers,
  because the form did not name one.

  And level 2 reads "no evidence they will pay this price" -- FALSE for any business
  already charging it. Trading IS the evidence.

TWO CHANGES (and nothing else):
  1. Add an explicit CORROBORATION rule: judge the business, not the form. Trading evidence
     sets a FLOOR (cannot be scored 1 or 2), it does not set the score.
  2. Rewrite the levels so "demonstrably reaches buyers" is the floor at 3, and 4/5 measure
     HOW WELL (deliberate channel; direct and cheap).

PRESERVED DELIBERATELY: level 1 keeps "cannot legally serve them", so the home-massage case
Sean agreed with (his words: "Your home massage service number is correct, I am wrong")
still scores 1. Without that, a not-permitted business would be scored 3 for optimism.
"""
import copy
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
src = json.loads((HERE / "rubric-v1.2.0.json").read_text())
new = copy.deepcopy(src)

DR_INSTR = (
    "Judge ONLY demand reach: is there an identifiable, reachable group of buyers who "
    "would pay for this, and can this business find them? Higher means more reachable. "
    "A demographic such as an age band is NOT a reachable segment on its own. Do not "
    "consider whether the market is large. "
    "CORROBORATE AGAINST PHYSICAL EVIDENCE. Judge the BUSINESS, not the quality of the "
    "submission. A business that is trading -- charging a stated price, with outlets, a "
    "published price list, or a trading history -- has demonstrably already reached paying "
    "customers. Absence of detail in the submission is an INPUT-QUALITY problem, not "
    "evidence that no buyer exists, and such a business MUST NOT be scored 1 or 2. The "
    "question for a trading business is HOW WELL it reaches them: concentrated or "
    "scattered, deliberately or incidentally, directly or through costly intermediaries. "
    "The one case where trading does not establish reach is where the business cannot "
    "legally serve the buyers at all."
)

DR_LEVELS = [
    "No identifiable buyer. The customer is undefined, OR the business cannot legally "
    "serve the buyers it names (for example a use not permitted at that premises), which "
    "is the one case where trading does not establish reach.",
    "Weak. A buyer group is named only as a demographic or category, AND there is no "
    "physical evidence of reach: not trading, no published price, no route. Any business "
    "demonstrably trading is at least 3.",
    "Moderate. A describable segment that the business demonstrably reaches, but the route "
    "is generic or incidental -- no deliberate, targeted channel is in evidence.",
    "Good. A clearly identified segment, demonstrably reached, with at least one credible "
    "and deliberate channel.",
    "Strong. A tightly defined, concentrated, paying segment that the business reaches "
    "directly and cheaply.",
]

# _meta.version is authoritative -- the harness asserts the two agree, so BOTH must be set.
assert new["_meta"]["version"] == "1.2.0", "unexpected baseline _meta"
new["_meta"]["version"] = "1.3.0"

assert new["questions"]["demand_reach"]["instructions"] != DR_INSTR
new["questions"]["demand_reach"]["instructions"] = DR_INSTR
new["questions"]["demand_reach"]["levels"] = DR_LEVELS
new["version"] = "1.3.0"
new["_changelog"] = src.get("_changelog", []) + [{
    "version": "1.3.0",
    "change": "demand_reach: added the corroboration rule (judge the business, not the "
              "submission). Trading evidence now sets a floor of 3. Level 1 keeps the "
              "cannot-legally-serve case.",
    "why": "Sean: trading businesses (Best Denki, 24/7 Fitness, Zoff, BreadTalk) were being "
           "scored as having no route to buyers because the FORM did not name one. The "
           "dimension was testing submission quality, not reach.",
}]

# CONTROL: prove every other dimension is byte-identical
for d in ("relative_strength", "mental_advantage", "defensibility",
          "competitive_room", "market_headroom"):
    assert new["questions"][d] == src["questions"][d], "control failed: %s changed" % d
assert new["weights"] if "weights" in new else True

(HERE / "rubric-v1.3.0.json").write_text(json.dumps(new, indent=2) + "\n")
print("wrote rubric-v1.3.0.json")
print()
print("CONTROL PASSED: all five other dimensions byte-identical to v1.2.0")
print()
print("demand_reach instructions, new text:")
print(" ", DR_INSTR[:200], "...")
print()
print("level 2 now reads:")
print(" ", DR_LEVELS[1])
