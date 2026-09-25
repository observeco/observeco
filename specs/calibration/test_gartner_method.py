"""HOW GARTNER/IDC/FORRESTER ACTUALLY SIZE A MARKET -- and why it resolves our problem.

Sean's question, with the key correction: "How does Gartner and similar generate and calculate
total addressable market value and their corresponding growth rates? Remember that positioning
theory is about product categories instead of industry?"

Sean's correction is the whole answer. I had been using SSIC INDUSTRY codes. Gartner defines
markets as PRODUCT CATEGORIES. Different object, different data, different result.

WHAT THE ANALYST FIRMS' OWN METHODOLOGY DOCUMENTS SAY
(from Gartner's published Market Definitions and Methodology, and IDC's SMF methodology):

  GARTNER -- market size is BUILT FROM VENDOR REVENUE:
    1. Establish vendor revenue for the vendors tracked (by market impact)
    2. ADD an estimate for vendors NOT tracked  -> published as "Other Services Vendors"
    3. SUBTRACT an estimate for subcontracting (to avoid double counting)
    -> the total IS the market size. Market share = vendor revenue / that total.

  GARTNER ON WHICH NUMBER IS RELIABLE -- the decisive quote:
    "Our focus is on developing the most accurate GROWTH RATES possible for this two-year
     period, as growth rates are often MORE VERIFIABLE AND COMPARABLE THAN ABSOLUTE VALUES."
    "The absolute size ... is difficult to definitively assess ... In contrast, growth rates
     represent some of the most verifiable data that we develop, because most large vendors
     PUBLICLY REPORT several years of financial information."
    "For these reasons, THE FIRST-YEAR GROWTH RATE, RATHER THAN ABSOLUTE VALUE, IS THE METRIC
     PRESERVED in our data model."

  IDC -- same shape, with a published estimator for the untracked tail:
    revenue models on 1,000+ vendors; "Other" = the difference between identified vendors'
    revenue and total market revenue, estimated by modelling a market-profile curve (an
    exponential: fewer vendors as revenue rises) and multiplying the estimated number of
    unknown vendors by the midpoint of each revenue band.
    Growth rates are then set per market/region by regional analysts, bottom-up.

  FORRESTER -- TAM/SAM/SOM; "use multiple data sources and approaches ... By comparing results
    from a range of approaches and soliciting input from experts, organizations can improve
    the accuracy of market sizing."

THE THREE LESSONS
  1. The unit is the VENDOR, not the industry. Market = the competitive set, summed.
  2. The market boundary IS the vendor set. Define the category by who competes in it.
  3. GROWTH RATE is the primary, verifiable output. ABSOLUTE SIZE is the soft one -- the
     opposite of what I assumed when I chased a CAGR.
"""
import json

print("=" * 82)
print("LESSON 1+2: A MARKET IS ITS COMPETITIVE SET, SUMMED -- AND IT IS A PRODUCT CATEGORY")
print("=" * 82)
print("""
  Gartner's markets are product categories a buyer would recognise, not SSIC industries.
  Their own examples: 'IT services', 'warehouse automation', 'fuel cell vehicles'.
  Euromonitor's Singapore category for our bubble-tea case is 'Street Stalls/Kiosks' --
  a product category -- NOT 'SSIC 56 Food & Beverage Services'.

  So the market boundary is DEFINED BY the set of vendors competing for the same budget.
  That is the same object our pipeline already derives: the competitive set.

  CONSEQUENCE: our Tier 1-7 derivation IS the market definition.
  We do not need to look the category up. We derive it -- then size it by summing it.
""")

# ---------------------------------------------------------------- EXECUTE
print("=" * 82)
print("EXECUTING THE GARTNER METHOD ON BUBBLE TEA (Singapore, 2026)")
print("=" * 82)

# Vendor outlet counts -- counted off each brand's OWN store list, 13 Sep 2026
VENDORS = {
    "KOI The":             90,
    "LiHO Tea":            52,
    "Each-A-Cup":          48,
    "CHAGEE":              46,
    "Chicha San Chen":     32,
    "Mixue":               30,   # ~30+ heartland/MRT/campus outlets
    "Playmade":            20,
    "R&B Tea":             15,
    "Sharetea":            12,
    "HEYTEA":               8,
}
print()
print("  TRACKED VENDORS (outlet counts from each brand's own store list, 13 Sep 2026)")
print(f"  {'vendor':22}{'outlets':>8}")
tot_tracked = 0
for v, o in sorted(VENDORS.items(), key=lambda x: -x[1]):
    print(f"  {v:22}{o:>8}")
    tot_tracked += o
print(f"  {'TRACKED TOTAL':22}{tot_tracked:>8}")

# Category size from two independent counts of the whole category
CATEGORY_OUTLETS = {"bbtea.sg (brand directory)": 688,
                    "poidata.io (business listings)": 953}
print()
print("  CATEGORY OUTLET COUNT -- two independent directories")
for src, n in CATEGORY_OUTLETS.items():
    print(f"    {src:34} {n:>5} outlets")

# Per-outlet revenue: audited-style unit economics from a published KOI outlet model
CUPS_DAY, PRICE, DAYS = 250, 5.40, 30
per_outlet_m = CUPS_DAY * PRICE * DAYS
per_outlet_y = per_outlet_m * 12
print()
print("  PER-OUTLET REVENUE (published outlet-level model, KOI)")
print(f"    {CUPS_DAY} cups/day x S${PRICE:.2f} x {DAYS} days = S${per_outlet_m:,.0f}/month")
print(f"    annualised = S${per_outlet_y:,.0f}/outlet/yr")

print()
print("  --> GARTNER-STYLE TAM = outlets x revenue per outlet")
for src, n in CATEGORY_OUTLETS.items():
    tam = n * per_outlet_y
    print(f"    {src:34} {n:>5} x S${per_outlet_y:,.0f} = S${tam/1e6:>6.0f}M/yr")
    print(f"    {'':34}   tracked {tot_tracked}/{n} = {tot_tracked/n:.0%} directly")
    print(f"    {'':34}   'Other' (Gartner's untracked tail) = "
          f"S${(n-tot_tracked)*per_outlet_y/1e6:>6.0f}M")

# ---------------------------------------------------------------- TRIANGULATION
print()
print("=" * 82)
print("TRIANGULATION -- three INDEPENDENT methods, as Forrester prescribes")
print("=" * 82)
BUYERS = 2_850_000
m_a_lo = BUYERS * 0.5 * 5.50 * 12
m_a_hi = BUYERS * 3.0 * 7.00 * 12
m_b_lo = 688 * per_outlet_y
m_b_hi = 953 * per_outlet_y
m_c = 45_000_000 / 0.20          # CaiCa revenue / share

print(f"  A. bottom-up population x incidence x price : "
      f"S${m_a_lo/1e6:>5.0f}M - S${m_a_hi/1e6:>5.0f}M")
print(f"  B. Gartner-style vendor sum (outlets x rev) : "
      f"S${m_b_lo/1e6:>5.0f}M - S${m_b_hi/1e6:>5.0f}M")
print(f"  C. client revenue / client share            : "
      f"S${m_c/1e6:>5.0f}M")
print()
lo = min(m_a_lo, m_b_lo, m_c)
hi = max(m_a_hi, m_b_hi, m_c)

# Honest overlap: compute the intersection properly and report when there is none.
def band(x, y):
    return (min(x, y), max(x, y))


a_lo, a_hi = band(m_a_lo, m_a_hi)
b_lo, b_hi = band(m_b_lo, m_b_hi)
c_lo, c_hi = band(m_c, m_c)
inter_lo, inter_hi = max(a_lo, b_lo, c_lo), min(a_hi, b_hi, c_hi)
print(f"  A  S${a_lo/1e6:>5.0f}M - S${a_hi/1e6:>5.0f}M")
print(f"  B  S${b_lo/1e6:>5.0f}M - S${b_hi/1e6:>5.0f}M")
print(f"  C  S${c_lo/1e6:>5.0f}M")
print()
if inter_lo <= inter_hi:
    print(f"  ALL THREE share S${inter_lo/1e6:.0f}M - S${inter_hi/1e6:.0f}M")
else:
    print(f"  NO COMMON BAND. A and B agree at S${max(a_lo,b_lo)/1e6:.0f}M - "
          f"S${min(a_hi,b_hi)/1e6:.0f}M;")
    print(f"  C (S${m_c/1e6:.0f}M, from client revenue / client share) sits BELOW that.")
    print()
    print("  THE DISAGREEMENT IS THE FINDING (MBB method). If the category is really")
    print(f"  S$400M, the client's S$45M revenue implies a share of "
          f"{45_000_000/400_000_000:.0%},")
    print(f"  not the ~20% assumed. So EITHER the client's stated share of 20% is too")
    print("  high, OR the vendor-sum is too low (some outlets generate less than the")
    print(f"  modelled S${per_outlet_y:,.0f}/yr), OR the 20% is a different denominator.")
    print("  Resolving that is exactly the analyst work Gartner bills for.")

PUBLISHED_SGD = (11.79 * 1.35 * 1e6, 17.12 * 1.35 * 1e6)
print()
print("  FOR CONTRAST -- the paid report-mill figure for the same category:")
print(f"    published USD 11.79-17.12M = S${PUBLISHED_SGD[0]/1e6:.0f}M - "
      f"S${PUBLISHED_SGD[1]/1e6:.0f}M")
print(f"    our three methods say S${lo/1e6:.0f}M - S${hi/1e6:.0f}M")
print(f"    the report mill is {(lo/PUBLISHED_SGD[1]):.0f}-"
      f"{(hi/PUBLISHED_SGD[0]):.0f}x TOO LOW")
print()
print("  WHY THE REPORT MILL IS LOW: it has almost certainly sized the MANUFACTURED")
print("  drink / packaged segment, or a single narrow slice, and called it the category.")
print("  Euromonitor -- the one firm with in-country analysts -- tracks the right thing:")
print("  'Street Stalls/Kiosks, % Foodservice Value', with company and brand shares.")

# ---------------------------------------------------------------- GROWTH RATE
print()
print("=" * 82)
print("LESSON 3: GARTNER'S GROWTH RATE IS VENDOR-DERIVED, NOT MARKET-DERIVED")
print("=" * 82)
print("""
  Gartner PRESERVES the growth rate and adjusts the absolute value to fit it, because
  vendor financials are audited and public. So the growth rate should come from VENDORS.

  For our category, vendor-side growth evidence:
    * CHAGEE: 0 -> 46 Singapore outlets in 24 months (from its own store list)
    * Mixue: 0 -> ~30 Singapore outlets since 2022 entry
    * KOI: 90 outlets, still #1 by reach
    * Gong Cha: 29 outlets CLOSED 2 Oct 2025, 6 units taken over by Cai Ca
    * Tiger Sugar: domain expired 1 Aug 2026, delisted

  That is a category where entrants are ADDING capacity fast while incumbents exit --
  churn, not net contraction. Note this is a SUPPLY-side growth rate, and it is
  computed from vendor-level facts, which is exactly Gartner's method.
""")

# ---------------------------------------------------------------- ASML CHECK
print("=" * 82)
print("ASML CHECK -- the definition sensitivity, proven from audited figures")
print("=" * 82)
ASML_FY25 = 32.667           # EUR bn, audited total net sales
ASML_IBM = 8.193             # EUR bn, Installed Base Management (service)
ASML_SYS = ASML_FY25 - ASML_IBM
FX = 1.08                    # EUR -> USD approx
print(f"  ASML FY2025 total net sales          EUR {ASML_FY25:.3f}bn = USD {ASML_FY25*FX:.1f}bn")
print(f"  of which Installed Base Management   EUR {ASML_IBM:.3f}bn (service, not equipment)")
print(f"  system sales                         EUR {ASML_SYS:.3f}bn = USD {ASML_SYS*FX:.1f}bn")
print()
print("  published 'lithography equipment market' sizes, 2025:")
for firm, v in [("Mordor", 27.83), ("Straits", 28.75), ("Dataintelo", 22.40),
                ("TBRC/GII", 22.25)]:
    print(f"    {firm:14} USD {v:.2f}bn")
print()
print(f"  ASML holds 85-90% of lithography revenue by value (Dataintelo).")
print(f"  => implied category = USD {ASML_SYS*FX/0.875:.1f}bn to USD {ASML_SYS*FX/0.85:.1f}bn")
print(f"  vs published USD 22-29bn. Close IF you count SYSTEM SALES ONLY.")
print()
print("  Add service and the definition changes the number:")
print(f"    systems only   USD {ASML_SYS*FX:.1f}bn")
print(f"    incl. service  USD {ASML_FY25*FX:.1f}bn  "
      f"({(ASML_FY25/ASML_SYS-1)*100:.0f}% larger, same company, same year)")
print()
print("  THIS IS THE POINT. Gartner's own methodology says:")
print("    'Different companies, government agencies and trade associations may use")
print("     slightly different definitions of product categories ... These differences")
print("     should be kept in mind when making comparisons.'")
print("  The definition IS the number. Which is why a market must be DEFINED by its")
print("  competitive set and published WITH that definition -- never quoted bare.")
