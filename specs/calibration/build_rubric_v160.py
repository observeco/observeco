"""Build rubric v1.6.0 — fix defensibility (Best Denki 1/4, Gain City 1/4).

THE DEFECT, same class as RS, DR and MA:

  Best Denki   DEF me 1  Sean 4
     differentiator: "Japanese retail service standards with trained staff who can explain
                      the difference between models."
     My level 1: "No moat. There is no differentiator at all, or the one claimed is a
                  purchasable input an..."
     My level 4: "Protected. A genuine accumulated barrier a challenger cannot cheaply
                  assemble: scale built over years (a store network, ...)"

  I scored the DIFFERENTIATOR THE FORM CLAIMED. The claimed differentiator (service
  standards) IS cheaply copyable -- so 1. But Best Denki operates a national store network
  and supply relationships built over decades, which is EXACTLY level 4's example list.
  The business HOLDS a level-4 barrier that the form did not happen to name.

  Gain City: same shape. Both hold store networks; both scored 1.

  ROOT CAUSE: defensibility was graded on the answer to "what do you do differently?" when
  the dimension asks "what obstructs a challenger?", and those are different questions. The
  form answers the first; the dimension needs the second, corroborated against physical
  facts.

ONE CHANGE: score the ACCUMULATED BARRIERS THE BUSINESS ACTUALLY HOLDS, corroborated
against physical evidence, not the differentiator the form claims. A claimed differentiator
that is copyable does not by itself establish level 1 -- the question is whether ANY real
barrier exists.

GUARD against over-correction (v1.4.0's mistake): holding a barrier is not automatic for
everyone. A single-outlet or home-based operator with no accumulated assets has none, and
must stay low. The test is the CHALLENGER'S COST to assemble it, not the incumbent's size.
"""
import copy
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
src = json.loads((HERE / "rubric-v1.5.0.json").read_text())
new = copy.deepcopy(src)

DEF_INSTR = (
    "Judge defensibility: how hard is it for a challenger to take this position? Judge the "
    "CHALLENGER'S COST, not the incumbent's effort. "
    "Score the ACCUMULATED BARRIERS THE BUSINESS ACTUALLY HOLDS, corroborated against "
    "physical evidence -- NOT the differentiator the submission happens to claim. "
    "The submitted differentiator is often the copyable one (a service standard, a claim, a "
    "recipe), and a business may hold real barriers it did not think to mention: a store "
    "network built over years, supply relationships, a distribution footprint, regulatory "
    "approvals, a physical asset base, accumulated brand equity. Ask what a well-resourced "
    "challenger would actually have to assemble to displace it. "
    "A copyable claimed differentiator does NOT by itself put a business at 1: only the "
    "ABSENCE of any real barrier does. Equally, holding a barrier is not automatic -- a "
    "single-outlet, home-based or asset-light operator with nothing accumulated has none and "
    "belongs low. The test is the cost to the CHALLENGER of assembling what the incumbent "
    "holds, never the incumbent's own hard work or stated claims. Note that effort already "
    "spent is not itself a barrier unless it left something a challenger cannot cheaply buy."
)

DEF_LEVELS = [
    "No barrier. Nothing obstructs a challenger: no accumulated asset, no network, no "
    "approval, nothing to assemble. A new entrant could offer the same thing immediately.",
    "Shallow. The only thing held is a claimed difference a competitor can copy in weeks by "
    "buying the same thing -- a message, an off-the-shelf input, a service standard. No "
    "accumulated asset.",
    "Replicable. Real work is required of the challenger, but nothing obstructs them beyond "
    "the cost of doing it: skills, a recipe, a small loyal base, a single premises.",
    "Protected. A genuine accumulated barrier a challenger cannot cheaply assemble -- scale "
    "built over years (a store network, a distribution footprint), entrenched supply "
    "relationships, a physical asset base, or regulatory approvals.",
    "Durable. The barrier would take a well-resourced challenger a decade or more, or "
    "requires assets they could not assemble at all.",
    src["questions"]["defensibility"]["levels"][5],
]

new["questions"]["defensibility"]["instructions"] = DEF_INSTR
new["questions"]["defensibility"]["levels"] = DEF_LEVELS
assert new["_meta"]["version"] == "1.5.0"
new["_meta"]["version"] = "1.6.0"
new["version"] = "1.6.0"
new["_changelog"] = src.get("_changelog", []) + [{
    "version": "1.6.0",
    "change": "defensibility: score the accumulated barriers the business HOLDS "
              "(corroborated), not the differentiator the form CLAIMS. A copyable claim "
              "alone does not put a business at 1.",
    "why": "Best Denki and Gain City scored 1 vs Sean's 4 -- I graded the claimed "
           "differentiator (Japanese service standards, copyable) while both hold the store "
           "networks and supply relationships that are level 4's own example. Same defect "
           "class as RS, DR and MA: reading the submission instead of the business.",
}]

for d in ("relative_strength", "mental_advantage", "competitive_room", "market_headroom",
          "demand_reach"):
    assert new["questions"][d] == src["questions"][d], "control failed: %s" % d

(HERE / "rubric-v1.6.0.json").write_text(json.dumps(new, indent=2) + "\n")
print("wrote rubric-v1.6.0.json  (_meta.version=%s)" % new["_meta"]["version"])
print("CONTROL PASSED: other five dimensions byte-identical to v1.5.0")
print()
print("PREDICTIONS: Best Denki DEF 1->3-4 (his 4), Gain City 1->3-4 (4)")
print("GUARDS (must NOT inflate): home studios / single-outlet operators stay <=3,")
print("  Sephora RS >=4, closed bubble tea outlet DR=2, True Fitness MA stays low")
