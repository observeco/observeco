"""Migrate market_headroom from a CROWDING question to an UNMET-DEMAND question (rubric 0.6.0).

SEAN'S INSIGHT (the trigger): "when I think about the market headroom for ASML, should there
even be a credible albeit small competitor, it should really open up the space? The problem now
is the market is congested because ASML has the monopoly and can't expand beyond its current
capacity"

VERIFIED AGAINST EVIDENCE BEFORE CHANGING ANYTHING:
  * ASML produces ~50-60 EUV systems/year; a leading-edge fab needs 10-20 -> the world can
    commission only ~3-4 new leading-edge fabs per year.
  * Backlog ~EUR 38.8bn = ~1.5 years of revenue; most 2027 output already committed.
  * Lead times push fab commissioning 12-24 months past announced schedules.
  * Buyers (TSMC, Samsung, Intel) "compete for finite ASML allocation".
  Sean's mechanism is confirmed: demand far exceeds supply, and the congestion is CAUSED by
  the monopoly being unable to expand capacity. A second supplier would ADD capacity and
  therefore EXPAND the market.

THE DEFECT: the old question asked "is there room for a new or small ENTRANT to be chosen?" --
a CROWDING question. It returned 3/5 for ASML (because the market is closed to entrants) and
4/5 for crowded bubble tea. So a saturated market scored HIGHER on headroom than a market
starved of supply. Worse, it made market_headroom a near-DUPLICATE of competitive_room: both
asked about crowding, and NEITHER measured unmet demand.

THE FIX: market_headroom now asks whether DEMAND EXCEEDS SUPPLY.
This divides labour cleanly with competitive_room:
  market_headroom   = is there unmet demand?      (is the opportunity real)
  competitive_room  = how hard is it to take?      (is the opportunity reachable)
This also matches the white-space framing from the research (high demand + low competitor
attention = opportunity).

MEASURED BEFORE ADOPTING (experiment_headroom_reframe.py):
                        OLD    NEW
  E1 ASML               1.95   3.33   (supply-constrained: 1.5yr backlog, rationed)
  08 bubbletea          2.84   1.88   (62+ brands, demand served)
  C9 b2b                2.34   1.95   (6+ undifferentiated rivals)
  N1 closed             2.32   1.67   (no demand)
  gap: ASML - best other   -0.89  ->  +1.38
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
p = HERE / "rubric.json"
r = json.loads(p.read_text())
m = r["_meta"]

q = r["questions"]["market_headroom"]
q["instructions"] = (
    "Judge ONLY market headroom: is there more DEMAND in this category than is currently being "
    "SERVED? Judge whether buyers are getting what they need, or whether demand is going unmet "
    "-- people waiting, being rationed, turned away, going without, or paying inflated prices "
    "because supply cannot keep up. Do NOT judge how crowded the category is, and do NOT judge "
    "whether a new entrant would be welcomed; those are separate questions. A category served by "
    "a single supplier who cannot expand fast enough to meet orders is NOT a trap -- it is "
    "under-supplied, and unmet demand is headroom. Equally, a large category where supply "
    "already meets demand has little headroom, however big it is, because any new entrant must "
    "take share from someone rather than serve unmet need."
)
q["levels"] = [
    "No demand. There is no identifiable buying demand for this category at all.",
    "Demand is served. Buyers can get this easily; supply meets or exceeds what is wanted, and the category is flat or shrinking.",
    "Demand is met, contested. Real, steady demand, but supply already satisfies it -- a new entrant must take share from an incumbent rather than serve unmet need.",
    "Demand exceeds supply. Buyers wait, are rationed, or pay inflated prices because supply cannot keep up, and the shortfall is growing.",
    "Demand far exceeds supply. The category cannot serve the demand that exists; buyers are allocated, queued or going without, and the constraint is the binding limit on the whole market.",
]

m["version"] = "0.6.0"
m["level_counts"] = {k: len(v["levels"]) for k, v in r["questions"].items()
                     if isinstance(v, dict) and v.get("type") == "score"}
m["dimension_division_of_labour"] = (
    "market_headroom asks whether UNMET DEMAND exists (is the opportunity real). "
    "competitive_room asks how hard it is for an operator to take share (is the opportunity "
    "reachable). Before 0.6.0 both asked a crowding question and were near-duplicates; neither "
    "measured unmet demand at all."
)
m["dimension_change_log"].append({
    "version": "0.6.0",
    "change": "market_headroom: CROWDING framing -> UNMET-DEMAND framing; levels rewritten to kind-distinct anchors",
    "reason": (
        "Sean: 'the market is congested because ASML has the monopoly and can't expand beyond "
        "its current capacity.' Verified: ~50-60 EUV tools/yr, 10-20 per fab, ~EUR 38.8bn "
        "backlog (~1.5 yrs), 2027 output largely committed, buyers competing for allocation. "
        "The old question returned 3/5 for ASML and 4/5 for crowded bubble tea -- a saturated "
        "market outscored a supply-starved one. It also duplicated competitive_room."
    ),
    "evidence": "experiment_headroom_reframe.py: ASML 1.95->3.33; bubbletea 2.84->1.88; "
                "gap vs best-other -0.89 -> +1.38",
})

# keep the old wording for audit
m.setdefault("_superseded", {})["market_headroom_0_5_0"] = {
    "change": "crowding framing -> unmet-demand framing",
    "definition": {
        "instructions": (
            "Judge ONLY market headroom: is there room for a new or small entrant to be chosen "
            "in this category at all? Consider whether the category the business names is a real "
            "category a buyer would recognise, whether it is growing or shrinking, and whether "
            "new entrants do get chosen in it."),
        "levels": [
            "No headroom. The category named is a trap -- contested, or an artefact of how the business describes itself.",
            "Very little. The category is real but shrinking, or so broad the business cannot be placed within it.",
            "Moderate. A real category with real buyers, but flat, or structurally unfavourable to new entrants.",
            "Good. A real, growing category in which new entrants do visibly get chosen.",
            "Strong. A large, growing category with documented, growing demand and plenty of room for new entrants.",
        ],
    },
    "why_retired": "Measured a crowding question, not unmet demand; scored a saturated market above a supply-starved one, and duplicated competitive_room.",
}

p.write_text(json.dumps(r, indent=2) + "\n")
print("rubric ->", m["version"])
print("level_counts:", json.dumps(m["level_counts"]))
print()
print("market_headroom, new levels:")
for i, l in enumerate(q["levels"]):
    print(f"  {i+1}) {l[:112]}{'...' if len(l) > 112 else ''}")
