"""Build rubric v1.4.1 — the RS fix over-corrected; add the RECOGNITION requirement.

WHAT v1.4.0 GOT RIGHT: Sephora 2->4, Don Don Donki 2->4, ROA 2->4, Polar Puffs 2->3,
Bonefirm 2->3 (Sean 4-5). The "judge per situation, not one share fight" correction works.

WHAT v1.4.0 BROKE: offset flipped +0.31 -> -0.43 and exact agreement fell 70.8% -> 44.5%.
The new disputes are all the SMALL home operators, and all in my direction:
    The Lash Fairy       RS me 4  him 2
    Mono Studio          RS me 4  him 2
    Tee (DOT) Nail Bar   RS me 4  him 2
    Perky Lash           RS me 4  him 2
    The Bloomish Eden    RS me 4  him 2
    A home-based mobile hairdresser  me 3  him 1

CAUSE: my wording said a specialist that "owns a distinct situation" is strong. Read
literally, a home lash studio owns the situation "home lash services" -- so it scored 4.
But Sean scores 2. A home studio is NOT strong on its niche; it is one interchangeable
option in a commodity niche nobody recognises it for.

THE MISSING CONDITION: a position must be RECOGNISED to count. Sephora is a known premium
destination -- the brands list there first. The Lash Fairy is interchangeable with a
thousand similar studios. Distinctness is not strength unless the MARKET recognises the
occupant as holding it. This keeps the Sephora lift and removes the home-studio lift.

NOT a reversion to share-anchoring: Sephora stays 4-5 on ~7% share, because its position is
recognised. Smallness is not the test -- RECOGNITION is.
"""
import copy
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
src = json.loads((HERE / "rubric-v1.4.0.json").read_text())
new = copy.deepcopy(src)

RS_INSTR = src["questions"]["relative_strength"]["instructions"]
RS_INSTR = RS_INSTR.replace(
    "A specialist that owns a distinct situation (the premium destination, the late-night "
    "Japanese-import run, the old-school local pastry) is strong on that situation even if "
    "it is small in overall share, and must NOT be scored as marginal merely because a "
    "mass-market occupant is bigger. A business is only marginal if it holds no situation "
    "at all. ",
    "A specialist that owns a RECOGNISED position in a distinct situation (the premium "
    "destination, the late-night Japanese-import run, the old-school local pastry) is strong "
    "on that situation even if small in overall share, and must NOT be scored as marginal "
    "merely because a mass-market occupant is bigger. "
    "BUT a position only counts if the MARKET RECOGNISES the business as holding it. A niche "
    "being distinct does not make its occupants strong: a small home-based operator is "
    "normally one interchangeable option among many similar operators, and is at PARITY (3) "
    "at best, or MARGINAL (2) where it has no distinguishing claim buyers actually select it "
    "for. Ask: would buyers choosing in this situation reach for this business by name, or "
    "could any of dozens of similar operators substitute for it? Only the former is a "
    "recognised position. Smallness is NOT the test -- recognition is: Sephora holds a "
    "recognised position on roughly 7% share. "
)

RS_LEVELS = [
    "Absent. Holds no position in any situation it enters -- not a factor buyers weigh.",
    "Marginal. One interchangeable option among many in a situation where buyers have no "
    "reason to select it over similar operators; nothing it is recognised for.",
    src["questions"]["relative_strength"]["levels"][2],
    "Strong. Holds a recognised position in at least one situation -- buyers select it for "
    "something specific, and it is ranked near the top of that situation even if small "
    "overall.",
    src["questions"]["relative_strength"]["levels"][4],
]

new["questions"]["relative_strength"]["instructions"] = RS_INSTR
new["questions"]["relative_strength"]["levels"] = RS_LEVELS
assert new["_meta"]["version"] == "1.4.0"
new["_meta"]["version"] = "1.4.1"
new["version"] = "1.4.1"
new["_changelog"] = src.get("_changelog", []) + [{
    "version": "1.4.1",
    "change": "relative_strength: a position must be MARKET-RECOGNISED to count. A small "
              "interchangeable operator is parity (3) at best, marginal (2) without a "
              "distinguishing claim.",
    "why": "v1.4.0 lifted small home studios to 4 (The Lash Fairy, Mono Studio, Tee Nail Bar "
           "with Sean at 2) while correctly lifting Sephora/Donki/ROA. Distinctness is not "
           "strength without recognition. Smallness is not the test -- Sephora stays 4-5 on "
           "7% share.",
}]

for d in ("mental_advantage", "defensibility", "competitive_room", "market_headroom",
          "demand_reach"):
    assert new["questions"][d] == src["questions"][d], "control failed: %s" % d

(HERE / "rubric-v1.4.1.json").write_text(json.dumps(new, indent=2) + "\n")
print("wrote rubric-v1.4.1.json  (_meta.version=%s)" % new["_meta"]["version"])
print("CONTROL PASSED: other five dimensions byte-identical to v1.4.0")
print()
print("PREDICTIONS TO TEST:")
print("  MUST NOT REGRESS: Sephora >=4, Don Don Donki >=4, ROA >=4, Polar Puffs >=3")
print("  MUST FIX:  The Lash Fairy <=3, Mono Studio <=3, Tee Nail Bar <=3,")
print("             mobile hairdresser <=3, Bloomish Eden <=3")
print("  MUST HOLD: closed bubble tea outlet DR = 2")
