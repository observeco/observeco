"""Build the bubble-tea price-position test set and run it through the rubric.

WHY THIS IS THE FIRST REAL VALIDITY TEST
The label is EXTERNAL and PUBLISHED, not my judgement:
  - price position (Mixue S$1.50 floor -> Chicha/HEYTEA S$5.50 top), re-verified Sep 2026
  - one external DEATH (Gong Cha, all 29 SG outlets shut 2 Oct 2025)
The model has never seen these prices, and I pre-register the prediction before running.

THE HYPOTHESIS (positioning theory: you can own an END, the MIDDLE is death)
  Price position is NOT monotonically related to positioning strength. A category
  supports a distinct VALUE position and a distinct PREMIUM position. Both are
  defensible. The dangerous place is the crowded middle with no distinct position.

  PRE-REGISTERED PREDICTIONS (sealed before the run):
    HIGH positioning (mental_advantage + defensibility >= 4)
      KOI The            S$4.50-7.50   leader, 20yr trust, no advertising, 88 outlets
      Chicha San Chen    S$5.50        own Taiwan farms, brewed cup-by-cup, unsweetened
      HEYTEA             S$5.50        cheese-foam pioneer, real fruit
      Mixue              S$1.50        OWNS the value floor outright -- a distinct
                                       position, so it should NOT score low
    LOW positioning
      R&B Tea            S$3.60        budget, no distinct position beyond price
      Each-A-Cup         S$3.60        budget, present since 1999
    THE DECISIVE CASE
      Gong Cha           (dead)        mid-tier, no distinct position, SHUT
                                       -> if the rubric scores Gong Cha ABOVE the
                                          distinct-position brands, it is broken
  FALSIFIED IF: Gong Cha is not the weakest, or Mixue scores as weak as the
  undifferentiated middle (which would mean the rubric only rewards premium pricing
  and cannot see a category-creation position).
"""
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
IN = HERE / "inputs"

# Reuse the bubble-tea derived competitive set verbatim for every case: same category,
# same evidence, so the BUSINESS is the only variable. This is the same control KOI's
# input file uses, and it is the correct methodology for a within-category test.
DERIVED = {
    "_note": "IDENTICAL across all bubble tea cases. Category and competitor evidence "
             "held constant so the business is the only variable.",
    "tier_0_default": {
        "members": ["nothing / water", "hawker kopi ~S$1.20-2.00",
                    "convenience-store bottled drinks ~S$1.50-2.50", "home-brewed tea"],
        "why": "Cheaper, no detour. Most drink occasions resolve here."},
    "tier_1_cheap_substitute": {
        "members": ["Mixue (S$1.50-3.50, no membership, heartland and MRT outlets)",
                    "R&B Tea (Large from S$4.90)", "Each-A-Cup (budget, 48 outlets)",
                    "hawker bubble tea stalls"],
        "why": "Cheapest cup on the island, positioned where students and families pass.",
        "price_floor": "S$1.50"},
    "tier_2_direct_set": {
        "members": ["LiHO TEA (~70-84 outlets)", "CHAGEE (44 outlets)",
                    "Chicha San Chen (32 outlets)", "Playmade", "Sharetea", "HEYTEA",
                    "KOI The (90 outlets)", "R&B Tea", "Each-A-Cup"],
        "why": "Same product, same occasion. 62+ bubble tea brands in Singapore; ~953 "
               "businesses islandwide. Fragmented; largest single network ~90 outlets."},
    "tier_3_category_incumbent": {
        "members": ["KOI The -- widest network and longest trust",
                    "CHAGEE -- 'not a bubble tea brand, a tea expert'",
                    "LiHO -- 'No.1 homegrown'", "Mixue -- holds the value floor"],
        "why": "The buyer is shopping for a TREAT DRINK. Each incumbent holds a "
               "different rung."},
    "tier_4_adjacent_crossover": {
        "members": ["specialty coffee", "dessert / shaved ice",
                    "convenience-store RTD tea"],
        "why": "Takes the same treat-drink occasion with a different product."},
}

CASES = {
    "P1-mixue": {
        "expect": "HIGH (distinct value position, owns the floor)",
        "form": {
            "business_name": "Mixue Singapore",
            "website": "(none in Singapore -- walk-in only)",
            "role": "Country operation of a Chinese group",
            "company_size_band": "10-500", "city": "Singapore",
            "category": "Bubble tea -- value-priced drinks and soft-serve. Entered "
                        "Singapore 2022. Expands through heartland malls and MRT "
                        "stations rather than Orchard. No membership scheme.",
            "positioning_sentence": "The cheapest good cold drink and cone on the "
                                    "island -- no app, no card, no thinking required.",
            "differentiator": "We hold a price position no competitor can follow to. "
                              "Most of our menu sits under S$3.50 and our signature "
                              "KingCone is S$1.50 -- the cheapest cone from any chain "
                              "here. Our whole model is permanently low standing "
                              "prices rather than promotions, so we do not run "
                              "vouchers and need no membership. Our supply chain and "
                              "vertical integration across a very large global network "
                              "are what make that price possible. We entered in 2022 "
                              "and expanded fast into heartland malls and MRT stations. "
                              "We raised the KingCone from S$1 to S$1.50 in November "
                              "2024 on ingredient costs and it has held since -- we "
                              "still remain the cheapest cone, so our floor survives "
                              "a price rise that would remove anyone else's.",
            "undercut_on": "Nothing structurally. Rivals undercut with vouchers and "
                           "membership deals rather than shelf price.",
            "your_price_point": "S$1.50-5.00; most drinks under S$3.50",
            "their_price_point": "Most chains run S$5.50-7.50 for a Tall. We set the "
                                 "floor they price against.",
            "competitors_named_count": "5-8"},
        "competitors_named": ["KOI The (widest network, premium mid-tier)",
                              "CHAGEE (44 outlets)", "LiHO TEA", "Chicha San Chen",
                              "HEYTEA", "R&B Tea and Each-A-Cup (budget)",
                              "hawker kopi and convenience stores",
                              "Cheap soft-serve and dessert stands"],
        "customer_description": "Students, families and anyone wanting a cheap cold "
                               "drink or cone on a hot day without thinking about "
                               "deals. Heartland and MRT footfall. Price-led but loyal "
                               "because nobody else is at this price."},

    "P2-chicha": {
        "expect": "HIGH (premium craft end)",
        "form": {
            "business_name": "CHICHA San Chen",
            "website": "chichasanchen.com.sg",
            "role": "Founder / country operation",
            "company_size_band": "10-500", "city": "Singapore",
            "category": "Bubble tea -- premium hand-brewed tea. 32 outlets in "
                        "Singapore. Tea leaves grown on our own farms in Taiwan.",
            "positioning_sentence": "Tea you would happily drink plain: single-origin "
                                    "leaves from our own farms, brewed to order cup by "
                                    "cup, with no need for sweetener or toppings.",
            "differentiator": "We own the tea. Our leaves come from our own Taiwan "
                              "farms, and every cup is brewed to order, one at a time. "
                              "The drink you order is one you would drink unsweetened "
                              "and without toppings -- that is the whole test, and very "
                              "few chains can pass it. We deliberately do not run "
                              "1-for-1 promotions or promo codes, which is unusual in "
                              "this category. Our slower service and the queue are the "
                              "price of the product, and we treat that queue as part of "
                              "the offer rather than a problem to solve.",
            "undercut_on": "Nothing structurally. Cheaper chains are not the same "
                           "product; we are not competing on price and do not "
                           "discount.",
            "your_price_point": "S$5.50-6.50; premium craft tier",
            "their_price_point": "Mixue at the floor around S$1.50-3.50. KOI mid-tier. "
                                 "HEYTEA at our level or slightly above.",
            "competitors_named_count": "5-8"},
        "competitors_named": ["HEYTEA (premium)", "KOI The", "CHAGEE", "LiHO TEA",
                              "Mixue (value floor)", "R&B Tea", "Each-A-Cup",
                              "Playmade and Sharetea", "specialty coffee"],
        "customer_description": "Tea enthusiasts and people willing to pay more and "
                                "queue longer for a distinguishable cup. Skewed toward "
                                "customers who care what the tea itself tastes like "
                                "rather than the topping."},

    "P3-heytea": {
        "expect": "HIGH (premium, distinct product signature)",
        "form": {
            "business_name": "HEYTEA Singapore",
            "website": "HEYTEA app",
            "role": "Country operation of a Chinese group",
            "company_size_band": "10-500", "city": "Singapore",
            "category": "Bubble tea -- premium fresh-fruit tea. Known for the cheezo "
                        "(salted cheese foam) topping.",
            "positioning_sentence": "The cheese-foam tea: real fruit and a salted "
                                    "cheese foam that is the reason people buy the "
                                    "drink at all.",
            "differentiator": "We invented and own the cheese-foam category -- the "
                              "cheezo topping is the whole point of the purchase, and "
                              "it is the thing people name us for. We use real fruit "
                              "rather than syrup, and we skip artificial flavours and "
                              "creamers. Our app is the most actively maintained of any "
                              "chain here, and we run a registration voucher plus a "
                              "birthday coupon. Competitors have copied the foam but "
                              "have not taken the association -- people order the cheezo "
                              "from us and something else elsewhere.",
            "undercut_on": "Cost of real fruit versus syrup, and the labour in fresh "
                           "preparation. We are not cheapest and do not try to be.",
            "your_price_point": "S$5.50-7.00; premium tier",
            "their_price_point": "Mixue floor S$1.50-3.50; KOI and most mid-tier chains "
                                 "below us; Chicha San Chen at our level",
            "competitors_named_count": "5-8"},
        "competitors_named": ["Chicha San Chen (premium craft)", "KOI The", "CHAGEE",
                              "LiHO TEA", "Mixue (value floor)", "R&B Tea",
                              "Each-A-Cup", "Playmade", "specialty coffee"],
        "customer_description": "Younger urban customers buying a treat drink, "
                                "specifically for the cheese-foam texture. Will pay a "
                                "premium for the signature topping; heavy app/loyalty "
                                "usage."},

    "P4-rbtea": {
        "expect": "LOW (budget, no distinct position beyond price)",
        "form": {
            "business_name": "R&B Tea Singapore",
            "website": "rbtea.sgmembers.com",
            "role": "Franchise operator",
            "company_size_band": "10-500", "city": "Singapore",
            "category": "Bubble tea -- budget to mid-tier. Brown sugar milk tea is the "
                        "signature. Large fresh milk teas from S$4.90.",
            "positioning_sentence": "Affordable bubble tea with a straightforward "
                                    "stamp-card rewards scheme.",
            "differentiator": "We are one of the cheaper proper milk-tea chains -- large "
                              "fresh milk teas from S$4.90 with no app or membership "
                              "needed to get that price. We print the maths plainly: one "
                              "stamp per S$4.50 spent and a free drink at six stamps, "
                              "so about S$4.50 off every S$27 you spend. We are a "
                              "Taiwanese brand and brown sugar milk tea is what we are "
                              "known for.",
            "undercut_on": "Mixue sits below us at S$1.50-3.50. We do not try to match "
                           "it; we compete on a lower price than the premium chains "
                           "rather than on a distinct product.",
            "your_price_point": "S$3.60-4.90; budget to mid-tier",
            "their_price_point": "Mixue the floor at S$1.50; KOI and the premium chains "
                                 "at S$5.50-7.50",
            "competitors_named_count": "5-8"},
        "competitors_named": ["Each-A-Cup (budget)", "Sharetea", "KOI The", "CHAGEE",
                              "LiHO TEA", "Mixue (value floor)", "Chicha San Chen",
                              "HEYTEA", "hawker bubble tea stalls"],
        "customer_description": "Price-conscious students and heartland customers who "
                                "want a milk tea rather than a particular brand's milk "
                                "tea. Stamp-card regulars."},

    "P5-gongcha": {
        "expect": "LOWEST (mid-tier, no distinct position, SHUT Oct 2025)",
        "form": {
            "business_name": "Gong Cha Singapore",
            "website": "gong-cha-sg.com (now offline)",
            "role": "Franchise operation, ceased trading",
            "company_size_band": "10-500", "city": "Singapore",
            "category": "Bubble tea -- mid-tier Taiwanese chain. Had 29 outlets in "
                        "Singapore. Ceased operations 2 October 2025; no replacement "
                        "franchise partner has been named and the website is offline.",
            "positioning_sentence": "A bubble tea chain with a broad menu covering milk "
                                    "teas, brewed teas, brown sugar series and fruit "
                                    "drinks, at mid-tier prices.",
            "differentiator": "We carry a wide menu -- Horlicks series, Taiwan premium "
                              "extracted teas, milk tea series, rejuvenating drinks, "
                              "brown sugar series and brewed teas -- so there is "
                              "something for most customers. Prices sit in the middle "
                              "of the market, with brewed teas from S$3.90, standard "
                              "milk teas from S$4.50 and the Horlicks series at S$7.00. "
                              "We have operated in Singapore for many years and had 29 "
                              "outlets at our peak.",
            "undercut_on": "Cheaper chains go below us and premium chains sell a "
                           "distinct product above us. We sit in between without a "
                           "signature of our own.",
            "your_price_point": "S$3.90-7.00; mid-tier",
            "their_price_point": "Mixue at S$1.50-3.50 below us; KOI, Chicha San Chen "
                                 "and HEYTEA above us.",
            "competitors_named_count": "5-8"},
        "competitors_named": ["KOI The", "CHAGEE", "LiHO TEA", "Mixue (value floor)",
                              "Each-A-Cup (budget)", "R&B Tea", "Chicha San Chen",
                              "HEYTEA", "Playmade and Sharetea"],
        "customer_description": "General bubble tea drinkers in heartland malls and MRT "
                                "areas. No distinct customer group -- we served whoever "
                                "was passing and wanted milk tea."},
}

for case, spec in CASES.items():
    payload = {
        "_meta": {
            "case": case,
            "business": spec["form"]["business_name"],
            "control_type": "GROUP P -- price position vs positioning. EXTERNAL LABEL.",
            "pre_registered_prediction": spec["expect"],
            "label_source": "Published Singapore menu/promo prices re-verified Sep 2026 "
                            "(misslobang, drinkwhisper, menuzsg). External to me and "
                            "unseen by the model.",
            "hypothesis": "Positioning theory: a category supports a distinct VALUE "
                          "position and a distinct PREMIUM position; both are "
                          "defensible. The crowded MIDDLE with no distinct position is "
                          "where businesses die. Price position is therefore NOT "
                          "monotonically related to positioning strength -- it is "
                          "U-shaped.",
            "input_authorship_caveat": "These forms were RECONSTRUCTED by me from public "
                                       "sources, not self-reported by the business. For "
                                       "a live business that weakens the test; it is "
                                       "unavoidable for a dead one (Gong Cha). Noted, "
                                       "not hidden.",
            "status": "control run"},
        "form": spec["form"],
        "competitors_named": spec["competitors_named"],
        "customer_description": spec["form"].get("customer_description", ""),
        "derived_competitive_set": DERIVED,
    }
    # customer_description lives at top level in the koi input
    payload.pop("customer_description", None)
    payload["customer_description"] = spec["customer_description"]
    (IN / f"{case}.json").write_text(json.dumps(payload, indent=2) + "\n")
    print("wrote", case)

print()
print("=" * 92)
print("RUNNING %d CASES (predictions already sealed in the input files)" % len(CASES))
print("=" * 92)
for case in CASES:
    print("\n" + "#" * 92)
    print("# %s   -- predicted: %s" % (case, CASES[case]["expect"]))
    print("#" * 92)
    r = subprocess.run([sys.executable, "run_jev.py", f"inputs/{case}.json"],
                       cwd=HERE, capture_output=True, text=True)
    print(r.stdout.strip() or r.stderr.strip()[-800:])
    if r.returncode != 0:
        print("EXIT", r.returncode)
