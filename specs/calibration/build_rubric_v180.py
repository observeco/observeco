"""Build rubric v1.8.0 — re-anchor the mental_advantage ladder to Sean's 120 labels.

WHY NOW, AND WHY THIS IS NOT FITTING TO NOISE

v1.7.0 fixed the CONSTRUCT (his answer: MA = how much the brand holds in the mind of the
customer; independent of closure) and it worked:
  - MA correlation jumped to r = 0.84, the BEST of all five dimensions.
  - Gong Cha 1 -> 3 (he scores 4): closure no longer suppresses it.
  - Guards held: closed bubble tea outlet MA 1 (his 1), Sephora RS 4, closed outlet DR 2.

But the LEVEL OFFSET got worse: +0.45 -> +0.55.

THE SHAPE OF THE REMAINING ERROR -- and this is what makes it a calibration problem, not a
construct one:
  gap (his - mine):  -1: 5    0: 52    +1: 48    +2: 10
  A single mass at exactly +1, sitting beside a large exact mass. That is a boundary
  problem for part of the corpus, not random error and not a different construct.

  distribution    L1   L2   L3   L4   L5
  Sean             4   35   31   31   19
  mine (v1.7.0)   26   34   23   25   12
  My scale is BOTTOM-HEAVY (22 too many at L1) and TOP-STARVED (7 too few at L5) at once.

THE DIAGNOSIS: my level 1 is far too easy to land in, and my 4/5 bars are too high.
"Absent from the mind" should be rare -- Sean uses it 4 times in 120. I use it 26 times.

THE RE-ANCHOR (driven by his labels, which is what a calibration corpus is for):
  1  genuinely unknown -- the segment could not name it at all. RARE.
  2  recognised only if prompted; no unprompted recall.
  3  familiar; surfaces when the category is considered. THE ORDINARY CASE for an
     established business with a real local presence.
  4  among the first names thought of, unprompted.
  5  the defining association for the category or occasion.

Explicit distribution guidance is included so the ladder cannot be read as bottom-heavy.
"""
import copy
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
src = json.loads((HERE / "rubric-v1.7.0.json").read_text())
new = copy.deepcopy(src)

MA_INSTR = src["questions"]["mental_advantage"]["instructions"]
MA_INSTR += (
    " CALIBRATION GUIDANCE for the levels. Level 1 should be UNCOMMON: reserve it for a "
    "brand the segment could not name at all if asked. Level 2 is for a brand recognised "
    "only when prompted. LEVEL 3 IS THE ORDINARY CASE for an established business with a "
    "real local presence and a known trade -- do not place such a business below 3. Level 4 "
    "is for a brand that comes to mind unprompted and is among the first names the segment "
    "thinks of. Level 5 is the defining association for its category or occasion. When "
    "weighing between two adjacent levels for a business that is established and known, "
    "choose the HIGHER one."
)

MA_LEVELS = [
    "Unknown to the mind. The segment could not name the brand at all if asked; it holds no "
    "mental space. Rare -- reserve for genuinely obscure businesses.",
    "Recognised only when prompted. The name is familiar if seen, but the segment would not "
    "think of it unprompted and it does not surface when the category comes up.",
    "Present and familiar. Surfaces when the category is considered and is a known option; "
    "the ordinary position of an established business with a real local presence.",
    "Strongly held. Comes to mind unprompted and is among the first names the segment "
    "thinks of for its occasions; a substantial share of mind.",
    "Deeply held. The defining association -- the first name that comes to mind, standing "
    "for the category or the occasion itself.",
]

new["questions"]["mental_advantage"]["instructions"] = MA_INSTR
new["questions"]["mental_advantage"]["levels"] = MA_LEVELS
assert new["_meta"]["version"] == "1.7.0"
new["_meta"]["version"] = "1.8.0"
new["version"] = "1.8.0"
new["_changelog"] = src.get("_changelog", []) + [{
    "version": "1.8.0",
    "change": "mental_advantage levels RE-ANCHORED to Sean's 120 labels: level 1 made rare, "
              "level 3 named as the ordinary case for an established business, tie-break to "
              "the higher level.",
    "why": "After the v1.7.0 construct fix the MA correlation is the best of all five "
           "dimensions (r=0.84) but the offset is +0.55, with the gap distribution a single "
           "mass at exactly +1 (48 cases) beside 52 exact. That is a boundary problem, not "
           "a construct problem. His distribution is L1 4 / L2 35 / L3 31 / L4 31 / L5 19; "
           "mine was L1 26 / L2 34 / L3 23 / L4 25 / L5 12 -- bottom-heavy and top-starved.",
}]

for d in ("relative_strength", "defensibility", "competitive_room", "market_headroom",
          "demand_reach"):
    assert new["questions"][d] == src["questions"][d], "control failed: %s" % d

(HERE / "rubric-v1.8.0.json").write_text(json.dumps(new, indent=2) + "\n")
print("wrote rubric-v1.8.0.json  (_meta.version=%s)" % new["_meta"]["version"])
print("CONTROL PASSED: other five dimensions byte-identical to v1.7.0")
print()
print("TARGET distribution to move toward:  L1 4  L2 35  L3 31  L4 31  L5 19")
print("Current (v1.7.0):                    L1 26 L2 34  L3 23  L4 25  L5 12")
print()
print("GUARDS: True Fitness MA (his 1), closed bubble tea outlet MA (his 1),")
print("        Sephora RS 4, closed outlet DR 2 -- none may regress")
