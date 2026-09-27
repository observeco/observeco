"""Build rubric v1.1.0 — the level-anchor revision, driven by Sean's Q1-Q6.

HIS ANSWERS AND WHAT EACH IMPLIES:

Q1  DEF = "hard to attack because it took decades and huge capital."
    => MY WORDING WAS DEFECTIVE. I wrote "effort already spent does not make something
    defensible", intending to stop "we worked hard" scoring. But it also reads as
    excluding "we built 150 outlets over 40 years", which IS a barrier to entry --
    capital requirements and scale economies are standard barriers. The fix distinguishes
    FLOW effort (earns nothing) from STOCK barriers (do count). Test is the CHALLENGER'S
    COST, never the incumbent's effort.

Q2  CR = "fragmented but walled by dominant players"; he asked me to correct him, and
    points at Book 1's capped-market analysis.
    => MY DEFINITION STANDS and Book 1 supports it: "when the market is capped and the
    players are many, the default move is to undercut... the natural physics of a small,
    crowded room". So fast food is price-contested (CR 2). BUT my level 4 word
    "fragmented" invited a count-the-players reading. Reworded to make the test the
    NEWCOMER'S ABILITY TO EARN, with player-count explicitly not the question.

Q3  DR = "these companies have understood and mapped out who their customers are clearly."
    => Absorbed. CLARITY is now the first of two criteria, REACHABILITY the second. This
    matches his D2 reason for keeping my definition ("whether they have clearly identified
    their customer group"). One residue flagged as a question: clarity of the REAL buyer
    vs clarity in the SUBMISSION.

Q4  RS = "positioning of the company relative to competitors" -- the agreed definition.
    => No change to the definition. His Sephora correction (his 5, my 2) is accepted; the
    gap is that no per-dimension REASONING is stored, so I could not defend my own score.

Q5  MA = "how much they have captured the mental space of the segment", scored on intent
    to be known, not the legal bar.
    => MA definition unchanged (D1 settled). But the five home-not-permitted cases are
    SYNTHETIC representatives, not real businesses -- they cannot be scored on mental
    space captured. Flagged for refusal rather than rescoring.

Q6  MH = "unmet demand vs supply"; no unmet demand for vehicle inspection because COE
    restrictions cap vehicle supply.
    => HE IS RIGHT. A regulated cap on the number of vehicles caps inspection demand.
    My 3 was too high. The instructions now state that where demand is itself capped by
    regulation, there is no unmet demand to serve.
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
src = json.loads((HERE / "rubric-v1.0.0.json").read_text())
META = src["_meta"]

# ---------------------------------------------------------------- DEF (Q1)
src["questions"]["defensibility"]["instructions"] = (
    "Judge ONLY defensibility: how DURABLE is this business's position -- how long would "
    "it take a well-resourced competitor to take it from them, and what obstructs the "
    "attempt? This is the DURABILITY of the position that relative_strength describes, "
    "NOT a second measure of the position itself. Distinguish two things carefully. "
    "(1) EFFORT THE FOUNDER SPENT -- 'we worked hard', 'we have been going for years', "
    "'we care more' -- earns nothing on its own; how hard something was to build is not "
    "what makes it hard to take. (2) ACCUMULATED BARRIERS -- assets a challenger cannot "
    "cheaply assemble: scale built over decades (a store network, a distribution system, "
    "a supply chain), a brand sustained by heavy long-term spending, an owned channel, a "
    "proprietary dataset, accumulated trust, a patent or trade secret, an exclusive supply "
    "agreement, or a regulatory licence. Accumulated barriers DO count, however they were "
    "built: a position that took forty years and enormous capital to construct is genuinely "
    "expensive for a challenger to replicate. THE TEST IS ALWAYS THE CHALLENGER'S COST, "
    "never the incumbent's effort: ask what a well-funded rival would have to spend, and "
    "how long, to take this position. If the answer is 'buy the same input and relabel "
    "it', there is no durability. If the answer is 'build 150 outlets and a national supply "
    "chain', there is a great deal."
)
src["questions"]["defensibility"]["levels"] = [
    "No moat. Nothing obstructs a challenger. There is no differentiator at all, or the "
    "one claimed is a purchasable input any competitor can relabel this quarter.",
    "Shallow. A competitor can copy it in weeks by buying the same thing -- a claim, a "
    "message, an off-the-shelf ingredient, a standard fit-out. No accumulated barrier.",
    "Replicable. A competitor must do real work of their own, but nothing obstructs them "
    "beyond the cost of doing it: the approach is visible and a committed challenger gets "
    "there in months, not years.",
    "Protected. A genuine accumulated barrier a challenger cannot cheaply assemble: scale "
    "built over years (a store network, distribution, supply chain), a brand sustained by "
    "heavy long-term spending, an owned channel, a proprietary dataset, accumulated trust, "
    "a patent or trade secret, an exclusive supply arrangement, or a licence. Taking the "
    "position means years and substantial capital, not months.",
    "Durable. The barrier would take a well-resourced challenger a decade or more, or "
    "requires assets they cannot assemble at all -- a national network, decades of "
    "accumulated trust, an exclusive relationship or licence, a dataset nobody else holds.",
    "Compounding. Several barriers reinforce each other, so that even a well-funded "
    "challenger given time could not replicate the position.",
]
src["questions"]["defensibility"]["_revised"] = (
    "2026-09-27 v1.1.0 (Sean Q1): 'effort already spent earns nothing' was too broad -- it "
    "excluded accumulated SCALE, which is a standard barrier to entry. Now distinguishes "
    "flow effort (still earns nothing) from stock barriers (count). Test = challenger's "
    "cost. Makes McDonald's DEF 4-5 defensible, where the old wording forced 2."
)

# ---------------------------------------------------------------- CR (Q2)
src["questions"]["competitive_room"]["instructions"] = (
    "Judge ONLY competitive room: how much room does this MARKET leave for a small "
    "operator like this one to enter and earn a margin? Judge the MARKET, never the "
    "business. THE NUMBER OF PLAYERS IS NOT THE QUESTION: a market with many players can "
    "still leave good room, and a market with two can leave none. Ask what happens to a "
    "competent newcomer who enters. Specifically: (a) is there a price floor set by a much "
    "larger player that a newcomer must match; (b) do incumbents hold scale or distribution "
    "advantages that stop a newcomer reaching comparable cost; (c) does the market compete "
    "mainly on price, so margins are thin for everyone? High room means a competent "
    "newcomer can enter and earn. Low room means they are structurally squeezed however "
    "good they are. A market that is fragmented AND price-contested scores LOW, because the "
    "many players are undercutting each other. Do NOT consider the business's own "
    "positioning or quality."
)
src["questions"]["competitive_room"]["levels"] = [
    "No room. Incumbents' scale sets a price and a cost floor no newcomer can match, and "
    "the market competes almost entirely on price. No viable margin for a new entrant.",
    "Very little. A dominant player or a severe price floor leaves a newcomer structurally "
    "squeezed -- they can enter only by accepting thin or negative margins.",
    "Some. Crowded and price-contested, but a newcomer with a real point of difference can "
    "carve out a viable niche and earn.",
    "Good. Not price-driven: several players coexist profitably and a competent newcomer "
    "can enter without having to match a crushing price floor.",
    "Strong. Uncontested or lightly contested, with no dominant player and no established "
    "price floor. A competent newcomer can enter and price for a healthy margin.",
]
src["questions"]["competitive_room"]["_revised"] = (
    "2026-09-27 v1.1.0 (Sean Q2): the word 'fragmented' in level 4 invited a "
    "count-the-players reading. Fast food scored 4 on that reading but is in fact a capped, "
    "price-contested market (Book 1: 'the natural physics of a small, crowded room'). The "
    "test is now explicitly the NEWCOMER'S ABILITY TO EARN, with player-count stated as not "
    "the question."
)

# ---------------------------------------------------------------- DR (Q3)
src["questions"]["demand_reach"]["instructions"] = (
    "Judge ONLY demand reach: has this business clearly identified a REAL, REACHABLE group "
    "of buyers, and can it get in front of them? Two things must both hold. First, CLARITY: "
    "is the customer described precisely enough to be a group someone could target -- a "
    "specific situation, need, or type of buyer -- rather than a broad demographic or "
    "'everyone'? Second, REACHABILITY: is that group reachable through at least one channel "
    "this business can actually use, and willing to pay the stated price? A demographic such "
    "as an age band is NOT a segment: it names no trigger and no route to them. Do NOT judge "
    "whether the market is large, and do NOT judge how well the business is already reaching "
    "them -- this is about whether the buyer is definable and reachable at all."
)
src["questions"]["demand_reach"]["levels"] = [
    "No identifiable buyer. The customer is undefined, or defined so broadly that no one "
    "could be targeted.",
    "Weak. Only a demographic or a category is named -- no trigger, no channel, and no "
    "evidence they would pay this price.",
    "Moderate. A describable segment with a plausible trigger, but no established route by "
    "which this business can reach them.",
    "Good. A clearly identified segment with a trigger, and at least one credible channel "
    "the business can use to reach them.",
    "Strong. A tightly defined, concentrated, paying segment, clearly identified and "
    "reachable directly and cheaply through a channel the business controls.",
]
src["questions"]["demand_reach"]["_revised"] = (
    "2026-09-27 v1.1.0 (Sean Q3): his reading -- 'have they clearly understood and mapped "
    "out who their customers are' -- is now the explicit first criterion (CLARITY), with "
    "REACHABILITY second. Residue flagged as a question: clarity of the REAL buyer vs "
    "clarity in the SUBMISSION."
)

# ---------------------------------------------------------------- MH (Q6)
src["questions"]["market_headroom"]["instructions"] = (
    "Judge ONLY market headroom: is there more DEMAND in this category than is currently "
    "being SERVED? Judge whether buyers are getting what they need, or whether demand is "
    "going unmet -- people waiting, being rationed, turned away, going without, or paying "
    "inflated prices because supply cannot keep up. Do NOT judge how crowded the category "
    "is, and do NOT judge whether a new entrant would be welcomed; those are separate "
    "questions. WHERE DEMAND IS ITSELF CAPPED BY REGULATION there is no unmet demand to "
    "serve, however necessary the service: if a rule limits how many buyers can exist -- "
    "for example vehicle inspections, where the COE system caps the number of vehicles that "
    "can be registered -- then supply can meet the capped demand and headroom is LOW or "
    "NOT APPLICABLE, even though every buyer must buy. Equally, a large category where "
    "supply already meets demand has little headroom, however big it is, because any new "
    "entrant must take share rather than serve unmet need."
)
src["questions"]["market_headroom"]["_revised"] = (
    "2026-09-27 v1.1.0 (Sean Q6): he correctly marked VICOM n/a -- COE restrictions cap the "
    "number of vehicles, so inspection demand is capped and no unmet demand can persist. My "
    "3 was too high. Regulated demand caps are now stated in the instructions."
)

# ---------------------------------------------------------------- meta
META["version"] = "1.1.0"
META["_changelog_1_1_0"] = [
    "Q1 DEF: distinguishes FLOW effort (earns nothing) from STOCK barriers (count). Scale "
    "built over decades is a legitimate barrier to entry; the test is the challenger's "
    "cost, not the incumbent's effort. Removes the defect that forced McDonald's DEF to 2.",
    "Q2 CR: the test is now the NEWCOMER'S ABILITY TO EARN; player-count is explicitly not "
    "the question. Fast food remains 2 (capped, price-contested -- Book 1's 'small, crowded "
    "room'), but the wording no longer invites a fragmentation reading.",
    "Q3 DR: CLARITY of the buyer is now the first criterion, REACHABILITY the second. "
    "Absorbs Sean's reading without dropping reachability.",
    "Q6 MH: regulated demand caps stated explicitly -- COE-limited vehicle inspections have "
    "no unmet demand to serve.",
    "Q4 RS and Q5 MA definitions unchanged. RS weights unchanged.",
]
META["_known_gaps"] = [
    "No per-dimension REASONING is stored in run files, so a disputed score cannot be "
    "explained after the fact. This blocked resolution of the Sephora RS dispute (Q4).",
    "Five home-not-permitted cases are SYNTHETIC representatives, not real businesses. They "
    "cannot be scored on mental space captured (Q5). They should be refused, not rescored.",
]

out = HERE / "rubric-v1.1.0.json"
out.write_text(json.dumps(src, indent=2))
print("wrote %s" % out.name)
print("  version: %s" % META["version"])
print("  changes: DEF (Q1), CR (Q2), DR (Q3), MH (Q6)")
print("  unchanged by decision: RS (Q4), MA (Q5)")
print()
for k in ("defensibility", "competitive_room", "demand_reach", "market_headroom"):
    q = src["questions"][k]
    print("  %-18s %d levels  revised" % (k, len(q.get("levels") or [])))
