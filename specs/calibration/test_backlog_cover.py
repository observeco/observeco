"""Is there a BETTER quantified headroom measure than CAGR?

The CAGR test surfaced a clue: ASML's OWN revenue CAGR (15.1%) is ~1.7x its category's
(~8.9%). That gap says ASML grows faster than its market -- dominance. But Sean's claim is
about SUPPLY CONSTRAINT, and that lives in the order book, not the growth rate.

So test the quantity that actually encodes "demand exceeds supply": BACKLOG COVER
(committed orders / annual revenue). It is audited, it needs no market report, and it is
exactly the number that says whether buyers are rationed.
"""
from pathlib import Path

# ASML FY2025, from the Q4-2025 press release (audited, EUR millions)
ASML = {"backlog": 38_797, "fy2025_rev": 32_667, "fy2024_rev": 28_263,
        "lo": 34_000, "hi": 39_000,
        "euv_units": 300, "net_income": 9_609, "gross_margin": 52.8}

print("=" * 78)
print("BACKLOG COVER as the quantified headroom measure")
print("=" * 78)
print()
cover = ASML["backlog"] / ASML["fy2025_rev"]
cover_months = cover * 12
print("ASML (audited):")
print(f"  backlog end-FY2025        EUR {ASML['backlog']:>6,}m")
print(f"  FY2025 total net sales    EUR {ASML['fy2025_rev']:>6,}m")
print(f"  backlog cover             {cover:.2f} years = {cover_months:.1f} months")
print()
print(f"  2026 guidance EUR {ASML['lo']:,}m - {ASML['hi']:,}m")
implied = (ASML["lo"] + ASML["hi"]) / 2 / ASML["fy2025_rev"] - 1
print(f"  mid guidance {implied:+.1%} vs FY2025 -> backlog alone covers "
      f"{cover/ (1+implied):.2f} years of GROWING revenue")
print()
print("  benchmark for context:")
for label, mult in [("a normal industrial order book", 0.25),
                    ("a strong backlog business", 0.50),
                    ("heavily sold-out capacity", 1.00)]:
    print(f"    {label:32} ~{mult:.2f} yr cover")
print(f"    {'ASML':32} {cover:.2f} yr cover   <- {cover/1.0:.1f}x 'sold out'")

print()
print("-" * 78)
print("DOES IT ENCODE SEAN'S CLAIM?")
print("-" * 78)
print(f"  'can't expand beyond its current capacity'  -> cover {cover:.2f}yr = yes")
print("  'buyers are rationed'                      -> 300 EUV units/yr; a leading-edge")
print("                                                fab needs 10-20 -> ~3-4 fabs/yr max")
print("  'demand far exceeds supply'                -> backlog > 1 full year of revenue")
print("  CAGR of the CATEGORY (~8.9%) says NONE of this. It sees a normal 9% market.")
print("  The constraint is invisible to CAGR because CAGR measures the market AS IT IS,")
print("  including its constraint. Backlog cover measures the constraint itself.")

print()
print("-" * 78)
print("BUT: availability for the ACTUAL customer")
print("-" * 78)
print("  backlog cover requires an ORDER BOOK. Who has one?")
for who, has in [("capital equipment / B2B contract manufacturers", True),
                 ("SaaS / subscription", True),
                 ("construction / renovation", True),
                 ("restaurants, bubble tea, retail, salons", False),
                 ("tuition, clinics, gyms, F&B SME", False)]:
    print(f"    {'YES' if has else 'NO ':4} {who}")
print()
print("  ASML is the ONLY case in our 17 that publishes an order book.")
print("  For a bubble-tea shop there is no backlog and no market report.")
print("  The equivalent signal exists only in the owner's head:")
print("    'are you turning customers away / at capacity / with a waitlist?'")
print()
print("  => the measurable quantity is available exactly where it is not needed")
print("     (large listed businesses, already well covered) and unavailable exactly")
print("     where it is needed (the SME lead the free report serves).")
