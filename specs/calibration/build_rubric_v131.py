"""Build rubric v1.3.1 — close the hole my own v1.3.0 fix opened.

THE REGRESSION I CAUSED: a CLOSED bubble tea outlet moved 2 -> 3. Sean scored it 2; my
v1.3.0 fix made my answer WORSE. The rule says "any business demonstrably trading is at
least 3" -- and a closed outlet was trading once. That is exactly the error the dimension
exists to prevent: "used to reach buyers" is not "reaches buyers now".

ONE CHANGE: the floor applies only to a business CURRENTLY trading. A business that has
ceased trading (closed, dormant, no live price) does not get it.
"""
import copy
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
src = json.loads((HERE / "rubric-v1.3.0.json").read_text())
new = copy.deepcopy(src)

DR_INSTR = src["questions"]["demand_reach"]["instructions"]
# tighten "trading" to a present-tense condition
DR_INSTR = DR_INSTR.replace(
    "A business that is trading -- charging a stated price, with outlets, a published price "
    "list, or a trading history -- has demonstrably already reached paying customers.",
    "A business that is CURRENTLY trading -- charging a stated price now, with live outlets, "
    "a current price list, or recent trade -- has demonstrably reached paying customers. A "
    "business that has CEASED trading (closed, dormant, or with no live price) does NOT get "
    "this floor: having reached buyers in the past is not reaching them now."
)
DR_INSTR += (
    " A business that has ceased trading does not qualify for the trading floor, and its "
    "reach is judged on its current state alone."
)

DR_LEVELS = [
    "No identifiable buyer. The customer is undefined, OR the business cannot legally "
    "serve the buyers it names (for example a use not permitted at that premises), OR the "
    "business has ceased trading and reaches no one.",
    "Weak. A buyer group is named only as a demographic or category, AND there is no "
    "physical evidence of CURRENT reach: not trading now, no live price, no route. Any "
    "business currently trading is at least 3.",
    src["questions"]["demand_reach"]["levels"][2],
    src["questions"]["demand_reach"]["levels"][3],
    src["questions"]["demand_reach"]["levels"][4],
]

new["questions"]["demand_reach"]["instructions"] = DR_INSTR
new["questions"]["demand_reach"]["levels"] = DR_LEVELS
assert new["_meta"]["version"] == "1.3.0"
new["_meta"]["version"] = "1.3.1"
new["version"] = "1.3.1"
new["_changelog"] = src.get("_changelog", []) + [{
    "version": "1.3.1",
    "change": "demand_reach: the trading floor now requires CURRENT trade. A ceased business "
              "(closed or dormant) is judged on its current state and gets no floor.",
    "why": "v1.3.0 regressed the closed bubble tea outlet 2 -> 3 (Sean scored it 2). 'Was "
           "trading' is not 'reaches buyers now' -- the precise error the dimension exists "
           "to prevent.",
}]

for d in ("relative_strength", "mental_advantage", "defensibility",
          "competitive_room", "market_headroom"):
    assert new["questions"][d] == src["questions"][d], "control failed: %s" % d

(HERE / "rubric-v1.3.1.json").write_text(json.dumps(new, indent=2) + "\n")
print("wrote rubric-v1.3.1.json  (_meta.version=%s)" % new["_meta"]["version"])
print("CONTROL PASSED: other five dimensions byte-identical")
print()
print("level 1 now:", DR_LEVELS[0])
print()
print("level 2 now:", DR_LEVELS[1])
