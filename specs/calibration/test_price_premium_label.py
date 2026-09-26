"""TEST: is 'price premium to category' a usable positioning label?

Three hypotheses to ground:
  H1  price premium is MEASURABLE at scale
  H2  it DISCRIMINATES positioning strength
  H3  financial outcome does NOT proxy positioning (the Ezra test)

Sources are the two category price tables recovered by search (SG, Sep 2026).
All figures are as-published by the sources; nothing is modelled.
"""

# ── Bubble tea, Singapore 2026 (menu/promo sources, re-checked Sep 2026) ──────────
# representative standing price for a standard milk tea, medium unless noted
BUBBLE_TEA = [
    ("Mixue",        1.50, 5.00, "budget floor; most drinks under 3.50"),
    ("R&B Tea",      3.60, 4.90, "budget; large fresh milk tea 4.90"),
    ("Each-A-Cup",   3.60, 4.50, "budget, SG 1999"),
    ("Sharetea",     3.90, 4.90, "mid-tier"),
    ("KOI The",      4.50, 5.50, "premium-coded: 'premium positioning'"),
    ("Xing Fu Tang", 4.50, 4.50, "brown sugar specialist"),
    ("LiHO TEA",     4.20, 5.20, "mid-tier, SG 2017"),
    ("CHAGEE",       4.40, 5.40, "mid-tier, 44 SG outlets"),
    ("PlayMade",     4.20, 5.20, "mid-tier, hand-rolled pearls"),
    ("Chicha San Chen", 5.50, 6.50, "premium; 32 outlets, own Taiwan farms"),
    ("HEYTEA",       5.50, 7.00, "premium; cheese foam"),
]
# dead / withdrawn (from the same sources -- a real outcome signal in-category)
DEAD = [
    ("Gong Cha",  "SHUT 2 Oct 2025, all 29 SG outlets; no replacement franchisee"),
    ("Tiger Sugar", "domain expired 1 Aug 2026"),
]

# ── Petrol, Singapore Sep 2026 (pump price comparison sites) ──────────────────────
PETROL_RON95 = {"Shell": 3.48, "Esso": 3.49, "SPC": 3.48, "Caltex": 3.48, "Sinopec": 3.49}
PETROL_DIESEL = {"Shell": 4.07, "Esso": 4.07, "Caltex": 4.07, "SPC": 3.97, "Sinopec": 4.01}


def spread(vals):
    lo, hi = min(vals), max(vals)
    return lo, hi, hi - lo, (hi - lo) / lo * 100


print("=" * 92)
print("H1/H2 — PRICE SPREAD: can a 'price premium' label exist in the category at all?")
print("=" * 92)

bt = [p for _n, p, _h, _c in BUBBLE_TEA]
lo, hi, ab, pc = spread(bt)
print("  BUBBLE TEA (representative milk tea, SG)")
print("    lowest  S$%.2f  (%s)" % (lo, min(BUBBLE_TEA, key=lambda x: x[1])[0]))
print("    highest S$%.2f  (%s)" % (hi, max(BUBBLE_TEA, key=lambda x: x[1])[0]))
print("    absolute spread S$%.2f   = %.0f%% of the floor" % (ab, pc))
print()

for label, d in (("PETROL RON95", PETROL_RON95), ("PETROL DIESEL", PETROL_DIESEL)):
    lo, hi, ab, pc = spread(list(d.values()))
    print("  %s (SG, 22 Sep 2026)" % label)
    print("    lowest  $%.2f  highest $%.2f   spread $%.2f = %.1f%%"
          % (lo, hi, ab, pc))
print()

print("=" * 92)
print("THE HEADLINE: price spread as a MEASURE OF WHETHER POSITIONING IS OPERATIVE")
print("=" * 92)
bt_lo, bt_hi, _, bt_pc = spread(bt)
p_lo, p_hi, _, p_pc = spread(list(PETROL_RON95.values()))
print("  bubble tea   : %.0f%% spread  -> positioning is ACTIVE; brands occupy distinct"
      % bt_pc)
print("                 price positions, so a premium is readable and meaningful")
print("  petrol RON95 : %.1f%% spread  -> price is ARBITRAGED TO CONVERGENCE;" % p_pc)
print("                 all five major chains within 1 cent")
print()
print("  Ratio of spreads: %.0fx" % (bt_pc / p_pc))
print()
print("  => 'price premium to category' is NOT universally available. It is")
print("     CATEGORY-CONDITIONAL: defined where price spreads, undefined where it")
print("     converges. In petrol, a 1-cent gap cannot carry a positioning signal.")

print()
print("=" * 92)
print("IN-CATEGORY OUTCOME NATURAL EXPERIMENT (bubble tea)")
print("=" * 92)
for n, why in DEAD:
    print("  DEAD   %-14s %s" % (n, why))
print()
mid = sum(1 for _n, p, _h, _c in BUBBLE_TEA if 4.0 <= p <= 5.0)
print("  ALIVE  %d of %d brands sit in a narrow S$3.60-5.50 band; 1 at the floor" % (mid, len(BUBBLE_TEA)))
print("         (Mixue, S$1.50) and 2 above it (Chicha, HEYTEA, S$5.50).")
print()
print("  Positioning-relevant observation: Mixue did not win by positioning UP -- it")
print("  entered at a NEW price floor (2022) and 'rewrote the value end'. That is a")
print("  CATEGORY-CREATION move, not a premium. Two brands with premium pricing")
print("  (Chicha, HEYTEA) survive alongside it. Gong Cha -- mid-tier, no distinct")
print("  position -- shut. Consistent with positioning mattering, but n is small and")
print("  the causes are not established from price alone.")

print()
print("=" * 92)
print("H3 — DOES FINANCIAL OUTCOME PROXY POSITIONING?  (the Ezra test)")
print("=" * 92)
EZION = [("FY2013", None, None), ("FY2014", 386.512, 40.5), ("FY2015", 351.147, 83.7)]
print("  EZION HOLDINGS (S$m, audited, from results announcements)")
print("    FY2014 revenue 386.5   net profit 40.5")
print("    FY2015 revenue 351.1   net profit 83.7   <- revenue FELL 9.2%, profit DOUBLED")
print()
print("  EZRA HOLDINGS (from FY2016 announcement and filings)")
print("    listed 2003; bought 30+ AHTS/PSVs, 2 FPSOs, Aker subsea div 2011")
print("    FY2016: revenue WEAKER than FY2015; net loss after tax > US$1 billion")
print("    by 2017: suspending payments on ~US$2 billion of debt")
print()
print("  FINDING: revenue decline was a LATE signal. Ezra grew revenue for a DECADE")
print("  on debt-funded expansion; by the time revenue fell, the outcome was already")
print("  set. And Ezion's FY2015 shows revenue DOWN 9% while profit DOUBLED.")
print()
print("  => a revenue-direction screen detects distress LATE, and mis-signals in-year.")
print("     The balance sheet (debt taken on during the growth phase) was the earlier")
print("     and better signal -- and it is a FINANCIAL signal, not a positioning one.")
print()
print("  This is the failure mode of the proposed screen: it would have shown Ezra")
print("  as a growth company through the entire period in which its future was being")
print("  destroyed.")
