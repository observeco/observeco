"""Build rubric v1.2.0 — the CLEAN single-variable test I should have run first.

MY ERROR IN v1.1.0: I changed FOUR dimensions at once (DEF, CR, DR, MH), so I cannot
attribute the result. The data then showed:
    DEF  >=2-apart 14% -> 7%   IMPROVED (the targeted fix worked)
    CR   exact     77% -> 65%  REGRESSED
    DR   exact     67% -> 54%  REGRESSED (shift 0.39 -> 0.63)
    MH   identical (dropped in 105 of 120 cases, so immaterial)
A four-variable change that improves one and harms two is not a fix.

REVERSAL REASONING:
  Q1 (DEF) -- a genuine DEFECT in my wording: "effort already spent earns nothing"
      excluded accumulated SCALE, a standard barrier to entry. Worth changing.
  Q2 (CR)  -- his message was "if I have the scoring wrong based on your definition,
      please correct mine", and I concluded MY definition stood (Book 1 supports the
      capped/price-contested reading). So CR should NOT have been rewritten. Revert.
  Q3 (DR)  -- he was explaining what HIS score meant, not complaining about my wording.
      My v1.0.0 definition already graded definability; adding CLARITY explicitly and
      demoting reachability made agreement WORSE. Revert.
  Q4 (RS)  -- no change agreed. Already unchanged.
  Q5 (MA)  -- no change agreed. Already unchanged.
  Q6 (MH)  -- he was RIGHT about VICOM (COE caps vehicle supply, so inspection demand is
      capped). Keep the instruction fix, but note it is UNTESTED: MH is dropped in 105 of
      120 cases, so it can affect at most 5.

So v1.2.0 = v1.0.0 with ONLY the DEF change (Q1) and the MH instruction note (Q6).
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
base = json.loads((HERE / "rubric-v1.0.0.json").read_text())
v11 = json.loads((HERE / "rubric-v1.1.0.json").read_text())
src = json.loads(json.dumps(base))          # work from v1.0.0
META = src["_meta"]

# ---- KEEP: DEF (Q1) — the one real wording defect ---------------------------
src["questions"]["defensibility"]["instructions"] = \
    v11["questions"]["defensibility"]["instructions"]
src["questions"]["defensibility"]["levels"] = \
    v11["questions"]["defensibility"]["levels"]
src["questions"]["defensibility"]["_revised"] = v11["questions"]["defensibility"]["_revised"]

# ---- KEEP: MH (Q6) — instruction note only, untested ------------------------
src["questions"]["market_headroom"]["instructions"] = \
    v11["questions"]["market_headroom"]["instructions"]
src["questions"]["market_headroom"]["_revised"] = \
    v11["questions"]["market_headroom"]["_revised"]

# ---- REVERT: CR (Q2) and DR (Q3) to v1.0.0 ---------------------------------
# (base already holds the v1.0.0 text; nothing to restore -- stated here for the record)
assert src["questions"]["competitive_room"]["levels"] == \
    base["questions"]["competitive_room"]["levels"]
assert src["questions"]["demand_reach"]["levels"] == \
    base["questions"]["demand_reach"]["levels"]

META["version"] = "1.2.0"
META["_changelog_1_2_0"] = [
    "CLEAN SINGLE-VARIABLE TEST. v1.1.0 changed four dimensions at once and could not be "
    "attributed: DEF improved (>=2-apart 14%->7%) while CR (exact 77%->65%) and DR "
    "(67%->54%) regressed. Reverted to v1.0.0 for CR and DR.",
    "KEPT: DEF (Q1). 'Effort already spent earns nothing' was a genuine defect -- it "
    "excluded accumulated SCALE, a standard barrier to entry. Now distinguishes flow "
    "effort (earns nothing) from stock barriers (count); test is the challenger's cost.",
    "KEPT: MH (Q6) instruction note on regulated demand caps (COE-limited vehicle "
    "inspections). UNTESTED -- MH is dropped in 105 of 120 cases, so it can affect at "
    "most 5.",
    "REVERTED: CR (Q2). His message was 'correct me if I am wrong', and the analysis "
    "concluded my definition stood (Book 1: a capped market defaults to undercutting). "
    "Rewriting the levels was not warranted by the evidence.",
    "REVERTED: DR (Q3). He was explaining what HIS score meant, not complaining about the "
    "wording. v1.0.0 already graded definability; adding CLARITY explicitly and demoting "
    "reachability made agreement worse.",
    "RS (Q4) and MA (Q5) unchanged throughout.",
]
META["_method_note"] = (
    "ONE VARIABLE AT A TIME. A revision must be attributable: change one dimension's "
    "wording, re-run, measure. v1.1.0 violated this and cost a full corpus run."
)

out = HERE / "rubric-v1.2.0.json"
out.write_text(json.dumps(src, indent=2))
print("wrote %s" % out.name)
print("  version: %s" % META["version"])
print()
for k in ("relative_strength", "mental_advantage", "defensibility",
          "competitive_room", "market_headroom", "demand_reach"):
    changed = src["questions"][k].get("levels") != base["questions"][k].get("levels")
    print("  %-18s %s" % (k, "CHANGED" if changed else "same as v1.0.0"))
