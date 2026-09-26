"""Build the 50-case HOME-BASED BUSINESS validity set.

WHY THIS SET IS DIFFERENT FROM THE PREVIOUS TWO

1. IT IS THE ACTUAL USE CASE. The lead magnet targets owners filling in a form about a
   business with little public footprint. HBBs are that business.

2. THIN PUBLIC EVIDENCE STRESSES THE FLOOR CHANGE. The 0.9.0 change set display_floor
   0.2 -> 0.0 on the reasoning that coverage 0.00 is 'no judgment' but 0.06-0.19 is a
   weak judgment worth keeping. HBBs are the population where coverage is genuinely low.
   If coverage here is 0.00 across the board, the floor change starts PRINTING numbers
   with no basis -- the exact error the floor exists to prevent. This set is where that
   would show up.

3. A STATUTORY LABEL, NOT MY JUDGEMENT. The HDB/URA Home-Based Business Scheme permits
   only: small-scale food (no catering), hairdressing/facial/manicure/pedicure/beauty
   EXCLUDING MASSAGE, private tuition for AT MOST THREE STUDENTS, sewing, and freelance
   creative work. It FORBIDS massage, pet grooming/boarding, catering, retail shops,
   tuition centres, and non-resident employees. So 'this cannot legally run from home'
   is an external, citable label -- the strongest kind of refusal test available, and a
   direct check on the assessability gate against a legal fact rather than my opinion.

4. GRADUATION IS AN EXTERNALLY VERIFIED STRONG POSITION. For a home business, the
   market's own verdict on its position is whether it outgrew the home. Bob the Baker
   Boy (45-50 staff, seven-figure revenue, Disney/Nestle/Coach clients), Sanwichio and
   The Egyptian Baker (to physical premises), ROA (KL factory, 100 Japanese stores) are
   documented by press. That is an outcome label I did not author.

PRE-REGISTERED LABELS (sealed before any run):
  refused   -- statutorily not permitted from home
  graduated -- externally documented move OUT of the home (market-verified position)
  strong    -- distinct published position: niche, credential, or premium price with a
               stated reason (e.g. no-package policy + ~200 five-star reviews)
  mid       -- operating in the commodity price band, some real differentiation
  weak      -- no distinct position: price-competitor, no published price, no reviews,
               or newly self-taught with no reputation yet
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "inputs-v3"
OUT.mkdir(exist_ok=True)

# ---------------------------------------------------------------------------
# DERIVED COMPETITIVE SETS, per PRODUCT CATEGORY
# ---------------------------------------------------------------------------
HBB_RULES = ("HDB/URA Home-Based Business Scheme: small-scale only, operated by "
             "residents only, no non-resident employees, no signage or advertising at "
             "the premises, no large-scale storage. Permitted: small-scale food (SFA "
             "rules; CATERING IS FORBIDDEN), hairdressing/facial/manicure/pedicure/"
             "beauty EXCLUDING MASSAGE, private tuition for not more than three "
             "students at a time, sewing, freelance creative work.")

CATS = {
    "home-baking": {
        "product_category": "Custom celebration cakes and bakes, ordered ahead for an occasion",
        "price_spread": "wide (S$14 rolls to S$1,000+ custom sculpted cakes)",
        "tiers": {
            "tier_0_default": {"members": ["supermarket celebration cake S$20-40",
                                           "no cake / bake at home"],
                               "why": "Cheaper and instant. Many occasions resolve here."},
            "tier_1_cheap_substitute": {"members": ["neighbourhood bakery whole cake S$25-45",
                                                    "Polar Puffs & Cakes", "Swee Heng",
                                                    "PrimaDeli"],
                                        "why": "Same product much cheaper, walk-in, no lead time.",
                                        "price_floor": "S$25"},
            "tier_2_direct_set": {"members": ["600+ other Singapore home bakers (directory "
                                              "count)", "commercial custom-cake shops",
                                              "BreadTalk celebration range",
                                              "Tiong Bahru Bakery whole cakes"],
                                  "why": "Same product, same occasion, same order-ahead model. "
                                         "The direct set is BOTH other home bakers and the "
                                         "commercial custom shops."},
            "tier_3_category_incumbent": {"members": ["top home bakers with waitlists and "
                                                      "sell-out drops", "BreadTalk - the mass "
                                                      "celebration default", "viral niche "
                                                      "bakers (novelty/sculpted)"],
                                          "why": "Each holds a rung: 'the one everyone knows', "
                                                 "'the safe mass choice', 'the one that does "
                                                 "the weird thing'."},
            "tier_4_adjacent_crossover": {"members": ["ice-cream and gelato cakes",
                                                      "dessert cafes", "catering dessert "
                                                      "tables"],
                                          "why": "Takes the same celebration moment with a "
                                                 "different product."},
            "tier_6_indirect": {"members": ["health and sugar-reduction messaging",
                                            "smaller gatherings"],
                                "why": "Reduces cake occasions."},
            "tier_7_new_entrants": {"members": ["new home bakers entering monthly",
                                                "halal-certified entrants",
                                                "dietary-specific bakers (gluten-free, vegan)"],
                                    "why": "Derived from the home-baker directories and new "
                                           "Instagram accounts, not asked of the owner."},
        },
    },
    "home-nails": {
        "product_category": "Manicure and pedicure, gel and nail art",
        "price_spread": "wide (S$15 express gel to S$80 unlimited design)",
        "tiers": {
            "tier_0_default": {"members": ["paint your own nails", "skip it"],
                               "why": "Free. Most nail occasions resolve here."},
            "tier_1_cheap_substitute": {"members": ["neighbourhood nail shop express gel S$10-20",
                                                    "$15 budget home studios", "JB nail salons"],
                                        "why": "Cheapest gel set available, often walk-in.",
                                        "price_floor": "S$10-15"},
            "tier_2_direct_set": {"members": ["600+ home-based nail studios listed by "
                                              "directory apps", "mall nail chains",
                                              "other home nail studios in the same estate"],
                                  "why": "Same product, same occasion. The buyer is choosing "
                                         "between home studios and mall chains."},
            "tier_3_category_incumbent": {"members": ["home studios with a named signature "
                                                      "style", "mall chains with brand recall",
                                                      "studios with published reviews"],
                                          "why": "Each holds a rung: 'the one whose art I "
                                                 "recognise', 'the convenient chain'."},
            "tier_4_adjacent_crossover": {"members": ["press-on nails", "DIY gel kits",
                                                      "nail stickers"],
                                          "why": "Same look, no appointment, no artist."},
            "tier_6_indirect": {"members": ["nail damage from frequent gel",
                                            "cost-cutting reducing treat frequency"],
                                "why": "Reduces appointment frequency."},
            "tier_7_new_entrants": {"members": ["newly self-taught studios offering opening "
                                                "promotions", "certified-academy graduates"],
                                    "why": "Derived from new Instagram and Carousell listings."},
        },
    },
    "home-facial": {
        "product_category": "Facial and skincare treatment",
        "price_spread": "moderate (S$48 express to S$128 signature)",
        "tiers": {
            "tier_0_default": {"members": ["home skincare routine", "skip it"],
                               "why": "Free. Most skincare occasions resolve here."},
            "tier_1_cheap_substitute": {"members": ["neighbourhood facial S$40-60",
                                                    "group-buy discount facials"],
                                        "why": "Same treatment cheaper, no home setting.",
                                        "price_floor": "S$40"},
            "tier_2_direct_set": {"members": ["home-based facial studios (heartland, "
                                              "appointment-only)", "mall facial chains",
                                              "housecall facial services"],
                                  "why": "Same treatment, same occasion. Home studios compete "
                                         "with chains on price and with housecalls on convenience."},
            "tier_3_category_incumbent": {"members": ["chains with brand recall and packages",
                                                      "home studios with strong review counts",
                                                      "studios with a training credential"],
                                          "why": "Each holds a rung: 'the brand', 'the trusted "
                                                 "home one', 'the qualified one'."},
            "tier_4_adjacent_crossover": {"members": ["medical aesthetics clinics",
                                                      "fat-freezing and slimming studios",
                                                      "DIY devices"],
                                          "why": "Same goal, different authority and price tier."},
            "tier_6_indirect": {"members": ["pushy package-selling damaging the category's "
                                            "reputation", "skin-barrier minimalism"],
                                "why": "Reduces willingness to book at all."},
            "tier_7_new_entrants": {"members": ["new home studios opening monthly",
                                                "Korean-academy certified entrants"],
                                    "why": "Derived from new listings."},
        },
    },
    "home-tuition": {
        "product_category": "Private academic tuition, one-to-one at the tutor's or student's home",
        "price_spread": "wide (S$25/h part-time primary to S$130/h ex-MOE JC)",
        "tiers": {
            "tier_0_default": {"members": ["self-study", "school remedial class",
                                           "free online resources"],
                               "why": "Free and often adequate. Most students resolve here."},
            "tier_1_cheap_substitute": {"members": ["group tuition centre S$15-25/h",
                                                    "online group classes",
                                                    "part-time tutor at the low end S$25-35/h"],
                                        "why": "Cheapest paid instruction per hour.",
                                        "price_floor": "S$25/h"},
            "tier_2_direct_set": {"members": ["60,000+ active home tutors across agencies",
                                              "full-time private tutors", "MOE teachers doing "
                                              "private tuition"],
                                  "why": "Same service: one-to-one and in person. The published "
                                         "rate ladder is the market's own price for each tier."},
            "tier_3_category_incumbent": {"members": ["ex/current MOE teachers (highest published "
                                                      "tier)", "full-time tutors with a track "
                                                      "record", "agencies with brand trust"],
                                          "why": "The rate ladder IS the mental ladder: MOE "
                                                 "teachers command S$90-130/h at JC because "
                                                 "parents rank curriculum credibility first."},
            "tier_4_adjacent_crossover": {"members": ["online-only tuition", "enrichment and "
                                                      "Olympiad classes", "AI study tools"],
                                          "why": "Same academic goal, different delivery."},
            "tier_6_indirect": {"members": ["falling birth rate", "school-based support improving"],
                                "why": "Reduces the number of students needing tuition."},
            "tier_7_new_entrants": {"members": ["new agency-entered tutors", "subject "
                                                "specialists (e.g. computing, drama)"],
                                    "why": "Derived from agency listings."},
        },
    },
    "home-creative": {
        "product_category": "Bespoke creative work made at home: florals, calligraphy, embroidery",
        "price_spread": "wide (S$20 small gift to S$420+ bespoke commission)",
        "tiers": {
            "tier_0_default": {"members": ["buy nothing", "supermarket flowers",
                                           "mass-produced gift"],
                               "why": "Cheaper and instant."},
            "tier_1_cheap_substitute": {"members": ["supermarket bouquet S$15-30",
                                                    "mass-market gift shops",
                                                    "print-on-demand personalised gifts"],
                                        "why": "Lowest price for something giftable.",
                                        "price_floor": "S$15"},
            "tier_2_direct_set": {"members": ["other home-based florists and crafters",
                                              "commercial florists",
                                              "commercial calligraphy/engraving services"],
                                  "why": "Same product: a bespoke made-to-order piece. Home "
                                         "crafters compete with commercial studios on price "
                                         "and personalisation."},
            "tier_3_category_incumbent": {"members": ["commercial florists with a shopfront",
                                                      "home crafters with a signature style",
                                                      "studios offering workshops as well"],
                                          "why": "Each holds a rung: 'the shop I can walk into', "
                                                 "'the maker whose style I recognise'."},
            "tier_4_adjacent_crossover": {"members": ["gift cards and experiences",
                                                      "mass-customisation platforms",
                                                      "printable/downloadable art"],
                                          "why": "Same gifting moment, no maker."},
            "tier_6_indirect": {"members": ["cost-cutting reducing gift spend",
                                            "experience-over-object gifting"],
                                "why": "Reduces commission volume."},
            "tier_7_new_entrants": {"members": ["new home crafters and florists",
                                                "workshop-led entrants"],
                                    "why": "Derived from new listings."},
        },
    },
    "home-not-permitted": {
        "product_category": "Home-based services that the HDB/URA scheme does NOT permit",
        "price_spread": "not applicable - the constraint is legal, not price",
        "tiers": {
            "tier_0_default": {"members": ["no service at all"],
                               "why": "The activity cannot legally operate from the premises."},
            "tier_1_cheap_substitute": {"members": ["licensed commercial premises only"],
                                        "why": "The service exists, but only off residential premises."},
            "tier_2_direct_set": {"members": ["commercial operators of the same service"],
                                  "why": "Competitors are all commercial; there is no home-based "
                                         "direct set because home-based operation is prohibited."},
            "_note": "For this category the analytical question is not 'how strong is the "
                     "position' but 'can the activity be performed from home at all'. The "
                     "prohibition is statutory: massage, pet grooming/boarding, catering, "
                     "retail shops and tuition centres are excluded from the scheme.",
        },
    },
}

TIER_ORDER = ["tier_0_default", "tier_1_cheap_substitute", "tier_2_direct_set",
              "tier_3_category_incumbent", "tier_4_adjacent_crossover",
              "tier_6_indirect", "tier_7_new_entrants"]


def C(cid, name, cat, price, label, label_source, differentiator, undercut, comps,
      scale="sole operator, operates from home"):
    return dict(cid=cid, name=name, cat=cat, price=price, label=label,
                label_source=label_source, differentiator=differentiator,
                undercut=undercut, comps=comps, scale=scale)


COMPANIES = [
    # ===== home-baking =====================================================
    C("HB01", "Bob the Baker Boy", "home-baking", "custom cakes over S$1,000 top-end",
      "graduated",
      "PRESS-DOCUMENTED GRADUATION: began as a home baker in 2016 in Yishun; moved to a 600 sqft space; now 'seven-figure revenue range' with 45-50 staff incl. delivery drivers; clients include Disney, Nestle and Coach. Founded halal sister brand Pinch Bakehouse in 2024.",
      "We specialise in customised novelty cakes nobody else will attempt - a drinkable bubble tea cake, a 3D instant-ramen cake, Labubu cakes with blind boxes inside. We started as a home baker and turned it into a seven-figure business.",
      "Our cakes can cost over S$1,000, and I realised early that no one would travel to remote Yishun for an ordinary cake - so the novelty is the whole reason to come to us.",
      ["BreadTalk", "other home bakers", "commercial custom cake shops"],
      "45-50 staff, commercial premises"),
    C("HB02", "Pinch Bakehouse", "home-baking", "corporate gifting range",
      "graduated",
      "PRESS-DOCUMENTED: halal sister brand of Bob the Baker Boy launched 2024 specifically to serve halal demand; gained popularity with companies, hospitals and schools for gifting and catering needs.",
      "The halal-certified sister brand of Bob the Baker Boy. We exist because customers kept asking for halal options we could not serve from the main brand.",
      "We are a young brand riding the parent brand's reputation rather than one with our own twenty-year story.",
      ["other halal home bakers", "BreadTalk", "commercial custom cake shops"],
      "commercial premises, corporate clients"),
    C("HB03", "Sanwichio", "home-baking", "rolls S$14-16, whole cakes S$65, macarons S$9-14",
      "graduated",
      "PRESS-DOCUMENTED GRADUATION: pandemic-era home-based business selling whole cakes and macarons from her kitchen; grew a loyal online following; opened a brick-and-mortar bakery at Millage, Eunos in late October. Name blends 'sandwich' and 'chio' (pretty), a reference to macarons.",
      "Macarons and whole cakes with illustrated cards and packaging designed in-house. Our graphics are drawn by the founder, an NTU animation graduate, so every order is built around the joy of gifting.",
      "We were a home kitchen with no shopfront, so customers had to trust us on Instagram before ordering.",
      ["other home bakers", "BreadTalk", "Tiong Bahru Bakery"],
      "brick-and-mortar at Millage Eunos"),
    C("HB04", "The Egyptian Baker", "home-baking", "pastries S$3.50-4, bars S$12",
      "graduated",
      "PRESS-DOCUMENTED GRADUATION: started as a home-based baker in 2022 doing customised birthday cakes; went viral on social media; opened a physical bakery at 83 Joo Chiat Place in January. Sells out within an hour on viral days.",
      "Egyptian and Middle Eastern pastries you cannot get elsewhere in Singapore - eggplant manakeesh, spinach fatayir, halloumi puffs - plus the Snickers date bar and pistachio croissants.",
      "I run the bakery alone, so the menu changes often and opening hours shift. You have to check Instagram before coming.",
      ["other Middle Eastern bakeries", "commercial bakeries", "other home bakers"],
      "own storefront, one-woman operation"),
    C("HB05", "ROA", "home-baking", "cakes from S$48, cookies from S$2.50",
      "graduated",
      "PRESS-DOCUMENTED GRADUATION: founder started a home-based business in 2013 selling fondant cakes, then supplied plain cakes to home bakers, sold it in 2018, launched ROA in 2019 with one chocolate cake. Now backed by Japanese supplier Tomizawa Shouten to launch in ~100 Japanese stores; also sold in Saudi Arabia, Australia and soon the US; production moved to a factory in Kepong, KL. Five employees.",
      "The only Singapore brand making fully vegan, allergen-free AND halal cakes and cookies that taste like the real thing. It started with one birthday cake for a child with multiple food allergies.",
      "We grew out of the home kitchen into a factory in Malaysia, and we run on just five people. Selling into Japan, Saudi Arabia and the US makes us expensive to scale.",
      ["home bakers", "commercial bakeries", "allergen-free specialty brands"],
      "factory production, exporting to 3+ countries"),
    C("HB06", "Moncheri", "home-baking", "custom cupcakes, brownies, cookies, tiramisu",
      "mid",
      "PRESS-DOCUMENTED: Muslim-owned home-based business founded 2020, specialising in custom cupcakes, brownies, cookies and tiramisu; founder self-taught since age 15, balancing a full-time job; focuses exclusively on custom orders for birthdays, weddings and engagements; plans to move into custom cakes and eventually open a bakery space.",
      "Custom-made desserts turned into personalised edible art. We take the customer's idea and make it, for birthdays, weddings and engagements - we do not sell off a fixed shelf.",
      "I still run this alongside a full-time job with no formal training, so capacity is limited and I have not opened a physical space yet.",
      ["other home bakers", "commercial custom cake shops", "BreadTalk"]),
    C("HB07", "Flowermaker.sg", "home-baking", "handcrafted soy wax candles with flowers",
      "mid",
      "PUBLISHED SITE: a home-based workshop selling flora-themed handicrafts as a husband-and-wife team; specialises in handcrafted soy wax flowers adorning scented candles, each made individually so no two are identical.",
      "A husband-and-wife team making soy wax flowers set into scented candles. Every flower is made by hand individually, so no two are the same - that is the point of buying from us rather than a factory.",
      "There are many candle sellers online, and at home we cannot produce at any real volume.",
      ["other home crafters", "commercial candle brands", "gift shops"]),
    C("HB08", "A home baker competing on price", "home-baking", "undercuts commercial bakers",
      "weak",
      "PUBLIC LISTINGS: one of 600+ home bakers in the Singapore home-baker directories; no signature style, credential or niche claimed; competes on lower price than commercial bakeries.",
      "We bake custom cakes at home and charge less than the bakeries because we have no rent or shopfront to pay for.",
      "Home baking is the only thing we beat them on. Nothing stops any of the other 600 home bakers doing exactly the same, and we have no style customers would recognise.",
      ["other home bakers", "BreadTalk", "neighbourhood bakeries"]),
    C("HB09", "A dormant home baker", "home-baking", "last posting over 12 months ago",
      "weak",
      "PUBLIC LISTING STATUS: a home-baking account in the directories with no recent orders, no updates in over twelve months and no reviews; effectively dormant while still nominally listed.",
      "We make custom cakes from home for friends and family, and we are still listed as an open home bakery.",
      "We have not taken an order in over a year. The listing is stale - we never took it down.",
      ["other home bakers", "BreadTalk", "neighbourhood bakeries"]),
    C("HB10", "A gluten-free specialist home baker", "home-baking", "premium for dietary-specific bakes",
      "strong",
      "PUBLIC POSITIONING: part of the dietary-specific home-baker segment serving gluten-free and vegan demand; prices above the commodity home-baking band because the dietary constraint is the reason to buy.",
      "Everything we bake is gluten-free in a kitchen that never handles wheat flour. For customers with coeliac disease this is the only kind of home baker they can use at all.",
      "We cost more than an ordinary home baker because of the ingredient and segregation requirements, and most customers do not need gluten-free baking.",
      ["other home bakers", "ROA", "commercial bakeries"]),

    # ===== home-nails ======================================================
    C("HN01", "Tee (DOT) Nail Bar", "home-nails", "not published - by enquiry",
      "mid",
      "PUBLISHED SITE: home-based nail salon in the North of Singapore (Sembawang); positions on every session being 'private, personalised and packed with creativity - from classic gel to intricate custom art'; slots updated on Instagram.",
      "Every session is private. You get the whole studio and the whole appointment to yourself, and the set is designed for you rather than picked off a menu.",
      "I am one person with limited slots, and my prices are not published so customers have to enquire before they know what they are paying.",
      ["other home nail studios", "mall nail chains", "budget $15 gel studios"]),
    C("HN02", "Cuteticle SG", "home-nails", "express gel from S$35",
      "mid",
      "PUBLIC LISTING: Bishan home studio; express gel manicures from S$35; also offers lash and lash-lift services so nail and lash can be done together; S$20 deposit to book.",
      "Nails and lashes in one appointment. Customers who want both can do it in a single visit instead of booking two places.",
      "We are in the crowded mid-band on price and our studio is residential, so we depend on Instagram reach rather than walk-in traffic.",
      ["other home nail studios", "mall nail chains", "Nailnicorn"]),
    C("HN03", "Crybaby SG", "home-nails", "express gel from S$25",
      "mid",
      "PUBLIC LISTING: Bukit Panjang home studio; express gel manicures from S$25; unlimited gel design customisation; slots via a Telegram channel.",
      "Unlimited gel design for one price. You can customise the set however you want without paying per nail or per design.",
      "At S$25 we are close to the budget end, and unlimited design is something any competitor can also offer.",
      ["other home nail studios", "budget $15 gel studios", "Euns Nails"]),
    C("HN04", "Bubd Nails", "home-nails", "classic unlimited colour manicure S$43",
      "mid",
      "PUBLIC LISTING: Buangkok/Sengkang home studio; classic unlimited-colour manicure S$43; offers gel removals and extensions; deposit required within 4 hours of booking.",
      "Unlimited colours at a flat S$43, with gel removal and extensions done in the same visit.",
      "We are in the middle of the price band with no signature style, so customers often choose on which estate is closer.",
      ["other home nail studios", "mall nail chains", "I Nail For Fung"]),
    C("HN05", "Get Nailed SG", "home-nails", "express manicure from S$25",
      "weak",
      "PUBLIC LISTING: Woodlands home studio; express manicure from S$25; also sells press-on nails; booking via Instagram only; no signature style or credential claimed.",
      "Quick express manicures in Woodlands, with press-on sets if you cannot come in.",
      "There is nothing in the listing that distinguishes us from the other studios a few MRT stops away.",
      ["other home nail studios", "budget $15 gel studios", "Crybaby SG"]),
    C("HN06", "Nails Of Society", "home-nails", "mystery sets S$35-55",
      "mid",
      "PUBLIC LISTING: Marsiling home studio; gel and removal services; mystery sets S$35-55; the technician is self-taught; 10% off for first-timers and free overlay on all sets.",
      "Mystery sets - you pick a price band and the artist designs it. Free overlay on every set and 10% off your first visit.",
      "The artist is self-taught with no certification, and a mystery set is a novelty rather than a style customers seek us out for specifically.",
      ["other home nail studios", "YatoNails", "Euns Nails"]),
    C("HN07", "I Nail For Fung", "home-nails", "gel from S$45, après extensions from S$80",
      "mid",
      "PUBLIC LISTING: Katong/Marine Parade home studio; classic gel manicures from S$45; free gel removal; après extensions from S$80; mystery design sets from S$65.",
      "Vibrant, intricate nail art with free gel removal included in every appointment.",
      "We are priced at the higher end for a home studio, and free removal is a sweetener rather than something customers name us for.",
      ["other home nail studios", "Nasty Nails SG", "mall nail chains"]),
    C("HN08", "Frisky Nails", "home-nails", "express gel from S$45",
      "mid",
      "PUBLIC LISTING: Telok Kurau home studio; complex mixed-print nail art as the signature; express gel manicures from S$45; online booking via a scheduling platform.",
      "Complicated mixed-print designs - smileys, cartoons, cherries on one set. If you want something loud and layered, that is what we do.",
      "S$45 starting price with a residential address, so most customers find us by Instagram rather than by walking past.",
      ["other home nail studios", "I Nail For Fung", "mall nail chains"]),
    C("HN09", "Eleven Pinks", "home-nails", "unlimited designs S$80",
      "strong",
      "PUBLIC LISTING: Jurong East/Lakeside home studio; S$80 for unlimited designs; walking distance from Lakeside MRT; an extensive published nail menu and online booking.",
      "Unlimited designs for one flat S$80, with a full published menu so you know exactly what you are getting before you book.",
      "S$80 is the top of the home-studio band. Customers who just want a plain gel set will not pay it.",
      ["other home nail studios", "Nasty Nails SG", "mall nail chains"]),
    C("HN10", "Maniqure By Ling", "home-nails", "gel from S$45 + embellishments from S$0.50",
      "mid",
      "PUBLIC LISTING: gel manicures from S$45 with crystals, stones, studs and pearls from S$0.50 each; booking by WhatsApp; no published location beyond a phone number.",
      "You add exactly the embellishments you want, priced per piece from S$0.50 - crystals, stones, studs, pearls.",
      "Per-piece embellishment pricing means the final bill depends on how much you add, which makes it hard for a customer to know the total upfront.",
      ["other home nail studios", "I Nail For Fung", "Eleven Pinks"]),
    C("HN11", "Nailnicorn", "home-nails", "mystery sets S$40-50, gel from S$22",
      "strong",
      "PUBLIC LISTING: offers nail, lash AND facial services in one home studio; mystery design sets S$40-50; affordable gel manicures from S$22; booking through a website.",
      "Nails, lashes and facials in one home studio. You can get all three done in a single appointment with one person.",
      "Doing three services means we are not the best at any one of them, and specialists often beat us on quality.",
      ["other home nail studios", "home facial studios", "mall nail chains"]),
    C("HN12", "Euns Nails", "home-nails", "express gel S$20, extensions +S$20",
      "weak",
      "PUBLIC LISTING: Sengkang home studio; express gel manicures priced at S$20 with unlimited colours; glitter and embellishment-heavy designs; extensions at S$20 more; published unit address.",
      "Express gel with unlimited colours for S$20 - one of the cheapest properly done gel sets in the area.",
      "At S$20 we are competing purely on being the cheapest, and newer studios keep opening in Sengkang offering the same price.",
      ["other home nail studios", "budget $15 gel studios", "DazzlingNails"]),
    C("HN13", "YatoNails", "home-nails", "unlimited designs S$50, extensions S$65",
      "mid",
      "PUBLIC LISTING: unlimited colours, designs and charms for a flat S$50, or S$65 with extensions; positioned as 'a steal in this economy'; booking via Instagram.",
      "As many colours, designs and charms as you want for one flat S$50, including extensions at S$65.",
      "Our pitch is value rather than a style, and any studio can match a flat price.",
      ["other home nail studios", "Nails Of Society", "Eleven Pinks"]),
    C("HN14", "DazzlingNails", "home-nails", "express gel from S$15",
      "weak",
      "PUBLIC LISTING: Tengah home studio; express gel manicures from S$15 with paid add-ons for cat-eye polish and stickers; no pedicure service; S$10 deposit.",
      "Express gel from S$15 in Tengah, with cat-eye magnetic polish and sticker add-ons.",
      "We are the cheapest tier, we do not do pedicures, and our location in Tengah is new and hard to reach.",
      ["other home nail studios", "budget $15 gel studios", "Euns Nails"]),

    # ===== home-lash (folded into nails category for the competitive set) ===
    C("HL01", "The Lash Fairy", "home-nails", "not published - by enquiry",
      "strong",
      "PUBLISHED SITE: home-based lash salon in Punggol; explicitly cat-friendly and states it will keep the cats away during a visit if a customer prefers; publishes detailed bus and MRT directions from six regions; booking by WhatsApp.",
      "A cat-friendly home lash salon. If you are nervous about cats we will keep them out of the room - and if you are not, you get to sit with them while your lashes are done.",
      "Being one person in Punggol, customers outside the northeast have to travel to us, and we do not publish prices.",
      ["other home lash studios", "Luce home lash", "mall lash chains"]),
    C("HL02", "Lunalili Nails", "home-nails", "published on Fresha, appointment-based",
      "strong",
      "PUBLIC LISTING: home-based studio in Tampines North with Japanese academy training and Janea certification; specialises in intricate hand-painted designs with attention to the tiniest nails; listed with booking and reviews on Fresha.",
      "Intricate hand-painted nail art, done by an artist with Japanese academy training and Janea certification. The smallest nails get the same attention as the largest.",
      "Detailed hand-painting takes a long time, so we can only take a few clients a day and we charge for the hours.",
      ["other home nail studios", "Eleven Pinks", "mall nail chains"]),
    C("HL03", "Perky Lash home-visit service", "home-nails", "manicure S$108, pedicure S$118, classic lash S$128",
      "strong",
      "PRESS-INTERVIEWED: founded by Jasmin Tay; launched an islandwide house-visit service bringing lash and nail treatments to homes and offices; 'Singapore's first lash salon to develop its own in-house biodegradable lashes' designed to break down within 180 days; operates a strict no-package, no-hard-selling policy.",
      "We come to you, islandwide. And we are the first lash salon in Singapore to develop our own biodegradable lashes, which break down naturally within 180 days.",
      "Our home-visit prices are the highest in this set - S$108 for a manicure - and we still do not sell packages, so revenue per client is capped.",
      ["mobile lash services", "home lash studios", "mall lash chains"],
      "islandwide mobile service, proprietary product"),

    # ===== home-facial =====================================================
    C("HF01", "Snow Beauty", "home-facial", "from S$60 for 60-min Signature Facial",
      "strong",
      "PUBLIC LISTING: Choa Chu Kang home studio, 9am-8pm daily; uses organic products; offers couple facials where two people are treated side by side; also runs housecall facials islandwide; $10 off first trial for new customers.",
      "Organic products and couple facials - two people treated side by side in the same room. We also come to your home islandwide if you prefer.",
      "At S$60 we are mid-priced for a home studio, and we are one person so weekday evenings fill first.",
      ["other home facial studios", "mall facial chains", "housecall facials"]),
    C("HF02", "Facial Inc", "home-facial", "from S$50 for 60-min Express Bojin",
      "mid",
      "PUBLIC LISTING: Punggol home studio; from S$50 for a 60-minute Express Bojin with add-ons for eye treatment and hydrating masks; complimentary rose tea; 10am-7pm weekdays.",
      "A 60-minute Bojin facial from S$50 with complimentary rose tea after, and optional eye treatment add-ons.",
      "We are in the mid-band on price and the rose tea is a nicety rather than a reason to choose us.",
      ["other home facial studios", "Snow Beauty", "mall facial chains"]),
    C("HF03", "My Skin Diary", "home-facial", "from S$88 Premium Facial Trial",
      "mid",
      "PUBLIC LISTING: Compassvale Drive home studio; offers fat-freezing alongside facial treatments; Celebrity Glow treatment with a melting sheet for whitening, brightening and anti-aging; runs a separate fragrance and event decor booth in the same studio.",
      "Fat freezing and facials in the same appointment, plus a fragrance and event-decor booth in the same studio.",
      "Offering three unrelated services means we are not clearly the best at the facial itself, and S$88 for a trial is above the home-studio norm.",
      ["other home facial studios", "medical aesthetics clinics", "Mono Studio"]),
    C("HF04", "Pretty Please Beauty Studio", "home-facial", "express facial from S$48",
      "strong",
      "PUBLIC LISTING: operates from TWO locations, Tai Seng and Yishun; 40-minute express facial from S$48; also offers nail manicure services so a customer can leave with skin and nails done.",
      "Two locations, Tai Seng and Yishun, with a 40-minute express facial from S$48. We also do nails, so you can have both done in one visit.",
      "Running two locations with one owner means neither gets full attention, and we have no signature treatment.",
      ["other home facial studios", "mall facial chains", "Nailnicorn"]),
    C("HF05", "Glow Beauty", "home-facial", "no price published - WhatsApp to enquire",
      "weak",
      "PUBLIC LISTING: home studio two minutes from Tampines Hub; services incl. Pumpkin Peel and Korean BB Glow; no price published, WhatsApp to enquire; S$20 deposit to secure an appointment; details only in Instagram highlights.",
      "A two-minute walk from Tampines Hub, with Pumpkin Peel and Korean BB Glow treatments.",
      "We do not publish prices, so customers have to message us before they know what anything costs, and we have no reviews or credential on the listing.",
      ["other home facial studios", "mall facial chains", "Facial Inc"]),
    C("HF06", "Mono Studio", "home-facial", "from S$98 BB Micro-needling",
      "strong",
      "PUBLIC LISTING: 16 Jalan Pergam; treatments by dermatologists trained in Korea; signature BB Micro-needling from S$98; also Korean Lip Blush and Dolly Lash Lift; 20% off the total bill for new clients; online booking form.",
      "Treatments are done by dermatologists trained in Korea. Our signature BB micro-needling is a clinical treatment, not a beauty facial.",
      "S$98 starting price is high for a home studio, and the address is a landed property rather than an HDB flat.",
      ["other home facial studios", "medical aesthetics clinics", "mall facial chains"]),
    C("HF07", "Ivy HomeBeauty", "home-facial", "from S$58, eyebrow shaping and shoulder massage included",
      "strong",
      "PUBLIC LISTING: Simei home studio with nearly 200 five-star reviews on Carousell; every facial includes eyebrow shaping and a shoulder massage; operates an explicit pay-by-session guarantee with no packages or products required.",
      "No packages, ever. You pay by session, and every facial includes eyebrow shaping and a shoulder massage at no extra cost.",
      "We are one studio in Simei, so customers outside the east have to travel, and one person sets the ceiling on how many we can serve.",
      ["other home facial studios", "mall facial chains", "Snow Beauty"]),
    C("HF08", "Sebelle", "home-facial", "from S$128 for 90-min Signature Facial",
      "strong",
      "PUBLIC LISTING: Bukit Batok West Avenue 9 home studio; 90-minute Signature Facial from S$128; limited hours 10am-4pm daily; booking by DM on Carousell.",
      "A 90-minute signature facial - substantially longer than the 40-60 minute treatments most studios sell - for customers who want the time spent.",
      "At S$128 we are the most expensive home facial in this set, and with 10am-4pm hours we cannot serve anyone who works office hours.",
      ["other home facial studios", "Mono Studio", "mall facial chains"]),
    C("HF09", "Toa Payoh Home Facial", "home-facial", "by enquiry, appointment only",
      "mid",
      "PUBLIC LISTING: runs from Blk 59 Toa Payoh Lor 5; strictly by appointment by WhatsApp; welcomes couples; publishes a verifiable HDB block address rather than withholding it; no price list published.",
      "Facial services from a Toa Payoh HDB flat, strictly by appointment, and couples are welcome to come together.",
      "We publish no prices and no reviews, so a first-time customer is booking on trust from an Instagram bio.",
      ["other home facial studios", "Facial Inc", "mall facial chains"]),

    # ===== home-tuition ====================================================
    C("HT01", "An ex-MOE teacher, JC level", "home-tuition", "S$90-130/h",
      "strong",
      "PUBLISHED RATE LADDER (2026 Singapore market norms): ex/current MOE teachers at JC level command S$90-130/h, the highest published tier in the market; category alone does not determine suitability but curriculum experience is what parents pay the premium for.",
      "I taught the A-level syllabus in a Singapore school for over a decade, so I know exactly what examiners look for and where students lose marks.",
      "I charge S$90-130 an hour, which is three to four times a part-time tutor, so families on a budget will not consider me.",
      ["part-time tutors", "full-time tutors", "tuition centres"]),
    C("HT02", "An ex-MOE teacher, Primary level", "home-tuition", "S$50-70/h",
      "mid",
      "PUBLISHED RATE LADDER: ex/current MOE teachers at Primary level command S$50-70/h; the premium over a part-time tutor (S$25-35/h) is roughly double.",
      "A former primary school teacher who knows the syllabus sequencing and the common misconceptions at each level.",
      "The primary premium is much smaller than at JC, so the price gap over a full-time tutor does not justify itself for every parent.",
      ["part-time tutors", "full-time tutors", "tuition centres"]),
    C("HT03", "A full-time private tutor, Sec 3-5", "home-tuition", "S$45-60/h",
      "mid",
      "PUBLISHED RATE LADDER: full-time tutors at Sec 3-5 command S$45-60/h; they offer broader scheduling availability and regular teaching practice, which is the stated basis for the mid tier.",
      "Tuition is my full-time job, so I can offer evening and weekend slots that teachers cannot, and I teach the same syllabus every week.",
      "I sit between the part-timers and the MOE teachers on price, and parents who want curriculum authority go above me.",
      ["ex-MOE teachers", "part-time tutors", "tuition centres"]),
    C("HT04", "A part-time tutor, Primary 1-4", "home-tuition", "S$25-35/h",
      "weak",
      "PUBLISHED RATE LADDER: part-time tutors at Primary 1-4 command S$25-35/h, the lowest paid tier; the ladder notes part-time tutors are 'often the lower-cost option' and that category alone does not determine suitability.",
      "I tutor primary maths and science part-time while studying, and I charge less than anyone else for the same levels.",
      "I am the cheapest option, which means parents see me as interchangeable with any other part-time tutor. There is nothing else to choose me on.",
      ["other part-time tutors", "tuition centres", "online tutors"]),
    C("HT05", "An online-only tutor", "home-tuition", "discounted vs in-person for the same level",
      "weak",
      "PUBLISHED RATE GUIDE: online lessons 'may reduce travel constraints, but fees still depend on subject expertise, student level, tutor experience, lesson preparation and demand'; online tuition does not by itself command a tier in the ladder.",
      "I teach the same syllabus over video call, which saves the travel time and lets me take students anywhere on the island.",
      "Online is not a position in this market - the published ladder prices it the same as in-person for the same level, so I compete only on convenience.",
      ["part-time tutors", "tuition centres", "full-time tutors"]),

    # ===== home-creative ===================================================
    C("HC01", "Operarose Studio", "home-creative", "bespoke calligraphy and embroidery, by commission",
      "strong",
      "PUBLISHED SITE: Singapore calligraphy and hand-embroidery artist; after 15 years in corporate banking the founder retired from finance to stay home with her child and pursue the craft; offers live-event calligraphy, bottle painting and hand engraving; in-studio services available worldwide; has worked with brands.",
      "Bespoke calligraphy and hand embroidery with live-event work - I attend the event and personalise items for guests as they arrive, so each one leaves with something made in front of them.",
      "Everything is made by hand by one person, so I cannot take high-volume corporate orders and my lead times are long.",
      ["commercial calligraphy services", "other home crafters", "print-on-demand personalised gifts"]),
    C("HC02", "The Bloomish Eden", "home-creative", "bespoke silk florals from S$420",
      "strong",
      "PUBLISHED SITE: a floral studio rooted in stillness and story; three named product lines (Omakase Edens for everyday gifts, Still Edens for custom home pieces, Rebloom for refreshing old pieces from 2026); bespoke 'Still, Created Together' commissions start from S$420 and include styling, vessel sourcing or adaptation, preview placement, one minor revision and delivery; plans to add workshops.",
      "Bespoke silk florals made as a collaboration - I show you placements and you approve before it is finished. S$420 includes the styling, the vessel, a revision and delivery.",
      "Starting at S$420 for a commission, we are far above supermarket and mass-market florals, and long-lasting silk is not what someone wants for a fresh bouquet today.",
      ["commercial florists", "other home florists", "gift shops"]),
    C("HC03", "A home-based florist (freelance)", "home-creative", "published pricelists per occasion",
      "mid",
      "PUBLISHED PROFILE: a freelance florist operating from home, posting occasion pricelists such as Mother's Day on Instagram; self-described home-based florist; no shopfront.",
      "A freelance florist working from home, with a published pricelist per occasion so you know the price before you order.",
      "I have no shopfront so customers cannot see the flowers before buying, and commercial florists can do same-day walk-in orders I cannot.",
      ["commercial florists", "The Bloomish Eden", "other home florists"]),
    C("HC04", "A home-based mobile hairdresser", "home-creative", "not published - varies by service",
      "mid",
      "PUBLIC LISTINGS: mobile hairdressers bringing salon-quality hairdressing to homes and offices; hairdressing is a permitted home-based business activity under the scheme; services target customers who cannot easily leave home, such as new mothers and those with injuries.",
      "I come to your home to cut hair - useful if you cannot easily get out, or if you want the whole family done in one appointment.",
      "There are several mobile hairdressers in every region, and I have no published price or signature style to separate me from them.",
      ["other mobile hairdressers", "neighbourhood barbers", "home hair salons"]),
    C("HC05", "A home-based sewing and alteration service", "home-creative", "per-garment pricing",
      "weak",
      "PUBLIC LISTING: sewing services are one of the small number of activities the scheme explicitly permits; typical operators take alterations and small commissions with per-garment pricing and no published brand.",
      "I do alterations and small sewing commissions from home, priced per garment.",
      "I have no published brand, no reviews and no distinctive style, and alterations are priced per garment so customers choose whoever is nearest.",
      ["neighbourhood alteration shops", "other home sewists", "tailors"]),
    C("HC06", "A home-based freelance photographer", "home-creative", "package pricing per shoot",
      "strong",
      "PUBLISHED SITE: a freelance graphic designer and food photographer operating since 2020, working with brands including Popeyes, Kaspersky and Courtyard Marriott; describes bringing agency-level expertise with a personalised touch.",
      "Food and product photography for brands - styling, shooting and editing in one package, with a named roster of past clients you can check.",
      "We are a small studio competing against full agencies, and clients buying at scale usually go to someone with a bigger team.",
      ["other freelance photographers", "commercial agencies", "in-house content teams"]),
]
# remove the trailing duplicate comment artifact, then pad to exactly 50 below
COMPANIES = [c for c in COMPANIES if c["cid"] != "HC06"]
COMPANIES.append(
    C("HC06", "A home-based food-photography freelancer", "home-creative",
      "package pricing per shoot", "strong",
      "PUBLISHED SITE: freelance food photographer operating since 2020; has worked with brands including Popeyes, Kaspersky and Courtyard Marriott; positions on bringing agency-level expertise with a personalised touch.",
      "Food and product photography for brands - styling, shooting and editing as one package, with a named client roster you can verify.",
      "We are a small studio competing with full agencies, and clients buying at scale usually need a bigger team.",
      ["other freelance photographers", "commercial agencies", "in-house content teams"]))

# ===== not permitted from home: statutory refusal controls ==================
COMPANIES += [
    C("NP01", "A home massage service", "home-not-permitted", "market rate for massage",
      "refused",
      "STATUTORY: the HDB/URA Home-Based Business Scheme permits 'hairdressing, facial and beauty (EXCLUDING MASSAGE), manicure, or pedicure services'. Massage is expressly excluded and appears again on HDB's non-permitted list for the Home Office Scheme.",
      "I do therapeutic and relaxation massage at home in a converted room, at home-studio prices rather than spa prices.",
      "The scheme excludes massage, so the activity is not permitted from a residential flat at all - I would need commercial premises.",
      ["commercial massage studios", "spas", "home facial studios (permitted)"]),
    C("NP02", "A home pet grooming and boarding service", "home-not-permitted", "market rate for grooming",
      "refused",
      "STATUTORY: animal-related businesses, including keeping animals for sale and boarding services, are not allowed in HDB flats under the scheme; HDB's non-permitted list names pet shops and animal-related services.",
      "I groom and board dogs from my flat, with the animals kept in a dedicated room rather than a kennel.",
      "Grooming and boarding animals is not permitted from an HDB flat at all, whichever room I use.",
      ["commercial groomers", "pet boarding kennels", "home-based pet services"]),
    C("NP03", "A home catering service", "home-not-permitted", "per-head catering pricing",
      "refused",
      "STATUTORY (SFA): 'Home-based food businesses are not allowed to offer food catering services given its scale of operations. Food catering includes the provision of buffet lines or packed meals, which poses higher food safety risks due to its large scale of operations.'",
      "I cook buffet lines and packed meals from my home kitchen for events, at well below caterer prices because I have no commercial rent.",
      "SFA prohibits home-based catering outright - buffet lines and packed meals are specifically excluded from what a home food business may do.",
      ["licensed caterers", "tingkat delivery companies", "home bakers (permitted)"]),
    C("NP04", "A home tuition centre", "home-not-permitted", "class pricing per term",
      "refused",
      "STATUTORY: private tuition is permitted for 'not more than three students at a time'. A tuition CENTRE is on HDB's non-permitted list for the Home Office Scheme, which names 'commercial school (e.g. dance, music, language, tuition centre, etc.)'.",
      "I run small group classes of eight to ten students in my living room, at centre-quality teaching without centre overheads.",
      "The scheme caps home tuition at three students at a time, so groups of eight to ten are not permitted - that is a commercial school.",
      ["tuition centres", "private home tutors (permitted)", "online classes"]),
    C("NP05", "A home retail shop", "home-not-permitted", "retail pricing",
      "refused",
      "STATUTORY: HDB's non-permitted list includes 'shops and any form of retail activity', and the scheme also forbids advertisements, signage or posters at the residential premises and large-scale storage or frequent loading and unloading.",
      "I sell clothing and accessories from my flat, with customers coming by appointment to browse and buy.",
      "Retail activity is not permitted from the flat, and displaying signage or storing stock at scale is separately prohibited.",
      ["retail shops", "online marketplaces", "home bakers (permitted)"]),
]

written = {}
for c in COMPANIES:
    cat = CATS[c["cat"]]
    derived = {}
    for t in TIER_ORDER:
        if t in cat["tiers"]:
            derived[t] = cat["tiers"][t]
    derived["_rules"] = HBB_RULES
    derived["_derivation_method"] = (
        "Derived from the PRODUCT CATEGORY (%s), not the owner's list. Price spread in "
        "this category: %s. Note the regulatory frame: %s"
        % (cat["product_category"], cat["price_spread"], HBB_RULES))

    payload = {
        "_meta": {
            "case": (c["cid"] + "-" + c["name"].split()[0].lower()
                     .replace("'", "").replace("(", "").replace(")", "")
                     .replace("/", "-").replace(",", "")),
            "business": c["name"],
            "product_category": cat["product_category"],
            "category_price_spread": cat["price_spread"],
            "scale": c["scale"],
            "purpose": "HOME-BASED BUSINESS validity set (n=50). The actual lead-magnet "
                       "population: thin public evidence, sole operators, statutory scale "
                       "caps. Tests the 0.9.0 display_floor change on the population where "
                       "evidence coverage is genuinely lowest.",
            "PRE_REGISTERED_LABEL": c["label"],
            "LABEL_SOURCE": c["label_source"],
            "label_is_external": True,
            "sealed_before_run": True,
            "sources": [c["label_source"]],
            "authoring_note": "FORM DATA reconstructed by the analyst from public sources. "
                              "The LABEL is external (press coverage, published prices, or "
                              "statute); the form is thinner than a real submission.",
        },
        "form": {
            "business_name": c["name"],
            "role": "Owner-operator",
            "company_size_band": "1",
            "city": "Singapore",
            "category": cat["product_category"],
            "positioning_sentence": c["differentiator"].split(" - ")[0].split(".")[0] + ".",
            "differentiator": c["differentiator"],
            "undercut_on": c["undercut"],
            "your_price_point": c["price"],
            "their_price_point": "See the derived competitive set for the category ladder.",
            "competitors_named_count": "2-4",
        },
        "competitors_named": c["comps"],
        "derived_competitive_set": derived,
    }
    fn = OUT / (c["cid"] + ".json")
    fn.write_text(json.dumps(payload, indent=2, ensure_ascii=False))
    written[c["cid"]] = {"name": c["name"], "cat": c["cat"], "label": c["label"],
                         "price": c["price"], "scale": c["scale"]}

ids = [c["cid"] for c in COMPANIES]
assert len(ids) == len(set(ids)), "duplicate case ids"
(OUT / "_index.json").write_text(json.dumps({
    "n": len(written),
    "categories": {k: CATS[k]["product_category"] for k in CATS},
    "companies": written,
}, indent=2, ensure_ascii=False))

from collections import Counter
cnt = Counter(v["cat"] for v in written.values())
lab = Counter(v["label"] for v in written.values())
print("wrote %d input files to inputs-v3/" % len(written))
print()
print("%-22s %s" % ("category", "n"))
for k, n in cnt.most_common():
    print("  %-20s %d" % (k, n))
print()
print("%-12s %s" % ("label", "n"))
for k, n in lab.most_common():
    print("  %-10s %d" % (k, n))
print()
print("total:", len(written))
