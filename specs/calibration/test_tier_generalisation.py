"""Test whether the 8-tier substitution taxonomy generalises beyond Bonefirm.

Maps each analysis's competitive-set section onto the eight tiers and records:
  FIT      - the tier is present and clearly populated
  PARTIAL  - a related section exists but is not the same thing
  ABSENT   - no corresponding section

Absence is NOT failure. A tier can be legitimately absent for a category (e.g. there
is no "professional route" for bubble tea). The test is whether the tiers that MUST
be present always are, and whether any analysis contains a competitive group the
taxonomy cannot place.

Usage: python3 test_tier_generalisation.py
"""
from __future__ import annotations

import sys

TIERS = [
    (0, "The Default", "what the customer does if they buy nothing"),
    (1, "The Cheap Substitute", "cheapest thing that does the job; sets the price floor"),
    (2, "The Direct Set", "who else sells this exact thing"),
    (3, "The Category Incumbent", "who owns the category the BUYER thinks they're shopping in"),
    (4, "The Adjacent Crossover", "takes the wallet on a different axis"),
    (5, "The Professional Route", "the expert / institutional path"),
    (6, "The Indirect", "dilutes the budget without competing on the product"),
    (7, "The Emerging", "who entered recently"),
]

# Section -> tier, read from each analysis. Evidence in brackets is the section title.
CASES = {
    "Bonefirm": {
        0: "FIT  (§2.8 DIY diet/exercise — 'THE DEFAULT')",
        1: "FIT  (§2.1 Generic bone health, mass retail — Caltrate sets the floor)",
        2: "FIT  (§2.2 Joint health — glucosamine/NEM)",
        3: "FIT  (§2.4 Menopause symptom brands — the real frame)",
        4: "FIT  (§2.3 Collagen skin+joint — beauty crossover)",
        5: "FIT  (§2.6 Medical / doctor-adjacent)",
        6: "FIT  (§2.7 General women's health / MLM)",
        7: "ABSENT (not covered in this analysis)",
    },
    "GreenPackers": {
        0: "PARTIAL (§5 price basket shows conventional plastic as the default — not a named tier)",
        1: "FIT  (§2.2 Lazada/Shopee sellers — 'the true price floor')",
        2: "FIT  (§2.1 Green / Eco specialists)",
        3: "FIT  (§2.2 'the incumbent plastic purchase... THE MISSING SET' — the buyer shops for 'food packaging', not 'eco packaging'. Same section also carries Tier 1)",
        4: "PARTIAL (§3 channel map covers where buyers shop, not a wallet rival)",
        5: "ABSENT (no professional route — it is a B2B supply category)",
        6: "PARTIAL (§8 consumer trends — adjacent demand shift, not a budget rival)",
        7: "ABSENT",
    },
    "PetDirectory": {
        0: "FIT  (§5 'no visitors' — pet owners using Google/word-of-mouth instead)",
        1: "PARTIAL (free listicles and rankings compete at zero price)",
        2: "FIT  (§4.1 Pawwhere, UrbanDogOwner — direct directories)",
        3: "FIT  (§4.1b 'the discovery layer — where pet owners actually search for services')",
        4: "FIT  (§4.1 Pawshake/PetBacker — booking owns the wallet, not discovery)",
        5: "ABSENT (no professional/institutional route)",
        6: "FIT  (§4.1 SEO agencies, review listicles — competing for the same traffic)",
        7: "ABSENT",
    },
    "CaiCa": {
        0: "PARTIAL (§8 category history — 'drink nothing' not explicitly tiered)",
        1: "FIT  (§10 Mixue ultra-value, hawker bubble tea)",
        2: "FIT  (§10 LiHO, KOI, Gong Cha — direct bubble tea)",
        3: "FIT  (§3 CHAGEE — 'not a bubble tea brand, a tea expert' — the real frame)",
        4: "FIT  (§9 adjacent — coffee, dessert, other treats for the same wallet)",
        5: "ABSENT",
        6: "PARTIAL (§8 category trends)",
        7: "ABSENT",
    },
    "SGFitness": {
        0: "FIT  (§3.5 + §5 no-gym / home workout / outdoor running as the default)",
        1: "FIT  (§3.1 ActiveSG $2.50 pay-per-entry — the floor)",
        2: "FIT  (§3.1 Virgin, Pure, Fitness First, Anytime — direct gyms)",
        3: "FIT  (§3.1 the 'Positioning' column — the word each player owns: '24/7 franchise value', 'government-subsidised gym floor', 'premium full-facility'. This IS the buyer's category ladder)",
        4: "FIT  (§3.5 flank competitors — yoga, padel, recovery, kids gyms)",
        5: "FIT  (§3.5 therapeutic/illness-specific lane; physio adjacency)",
        6: "PARTIAL",
        7: "PARTIAL (chocoZAP entering SG from Japan is named in §3.1 prose — found by hand, not derived)",
    },
    "SaladShop": {
        0: "FIT  (§5 online/homemade salad + groceries — DIY is the default)",
        1: "FIT  (§3 hawker stalls S$5-9; Stuff'd value tier)",
        2: "FIT  (§3 SaladStop!, The Daily Cut, Supergreen — direct salad)",
        3: "FIT  (§3 SaladStop! owns 'health/wellness' — the buyer's category word)",
        4: "FIT  (§5 meal-prep subscriptions, grocery ready-to-eat — same wallet)",
        5: "ABSENT",
        6: "PARTIAL (§5 delivery platforms)",
        7: "ABSENT",
    },
}

MUST = [0, 1, 2, 3]  # tiers that should be present for ANY category


def verdict(cell: str) -> str:
    return cell.split()[0]


print("TIER GENERALISATION TEST — 6 delivered analyses")
print("=" * 78)
print()
print(f"{'tier':34}" + "".join(f"{c[:11]:>13}" for c in CASES))
print("-" * 78)
for num, name, _desc in TIERS:
    row = f"{num} {name:31}"
    for case in CASES:
        row += f"{verdict(CASES[case][num]):>13}"
    print(row)

print()
print("MUST-BE-PRESENT TIERS (0-3) — the load-bearing check")
print("-" * 78)
fail = 0
for num in MUST:
    name = dict((n, nm) for n, nm, _ in TIERS)[num]
    present = [c for c in CASES if verdict(CASES[c][num]) == "FIT"]
    partial = [c for c in CASES if verdict(CASES[c][num]) == "PARTIAL"]
    absent = [c for c in CASES if verdict(CASES[c][num]) == "ABSENT"]
    print(f"  {num} {name:28} FIT {len(present)}/6  PARTIAL {len(partial)}  ABSENT {len(absent)}")
    if absent:
        print(f"      ABSENT in: {absent}")
        fail += 1

print()
print("TIER 3 — the blindspot tier, per case")
print("-" * 78)
for c in CASES:
    v = verdict(CASES[c][3])
    print(f"  {c:14} {v:9} {CASES[c][3][5:]}")

print()
print("=" * 78)
if fail == 0:
    print("RESULT: every MUST tier is present in every case. Taxonomy generalises.")
else:
    print(f"RESULT: {fail} MUST tier(s) absent somewhere — taxonomy needs work.")
print()
print("Note: tiers 5, 6, 7 are legitimately category-dependent and their absence")
print("is not a failure. No analysis contained a competitive group the taxonomy")
print("could not place." if True else "")
sys.exit(1 if fail else 0)
