"""TEST — would quantifying market_headroom as an addressable-market CAGR work?

Sean's proposal: "Can we quantify the market headroom in the typically way in which an
addressable market CAGR is calculated?"

Rather than opine, test it: take the ACTUAL CAGRs published for our test cases' real
categories (researched 2026-09-25), map them to a 1-5 scale the way any monotone mapping
would, and measure the separation against the unmet-demand framing that is currently in
rubric 0.6.0.

If CAGR separates the cases better than unmet demand, adopt it. If not, report that.
"""
from pathlib import Path

HERE = Path(__file__).resolve().parent

# ---------------------------------------------------------------- researched CAGRs
# Every figure below is a PUBLISHED forecast for the case's actual category, found by
# web search on 2026-09-25. Where firms disagree, all figures are listed -- the spread is
# itself one of the findings.
CAGR = {
    "E1-asml": {
        "category": "semiconductor lithography equipment",
        "source": "Mordor 9.37 | Persistence 9.6 | Straits 9.73 | TMR 8.4 | GII/TBRC 7.4",
        "values": [9.37, 9.6, 9.73, 8.4, 7.4]},
    "bubbletea": {
        "category": "Singapore bubble tea",
        "source": "DeepMarketInsights 7.56 | 6Wresearch 6.8",
        "values": [7.56, 6.8]},
    "C3-pet-lovers-centre": {
        "category": "Singapore pet care",
        "source": "DeepMarketInsights 5.54 | DMI pet 6.77 | 6Wresearch 6.8",
        "values": [5.54, 6.77, 6.8]},
    "C6-euyansang": {
        "category": "Singapore herbal/TCM",
        "source": "Vyansa 1.58 | 6W medicinal herbs 5.2 | Reed 6.75",
        "values": [1.58, 5.2, 6.75]},
}

# ASML's OWN realised revenue CAGR, for the contrast case (listed company, audited data)
ASML_REV = (18.611, 32.667, 2021, 2025)   # FY2021 EUR bn -> FY2025 EUR bn

print("=" * 78)
print("TEST: CAGR-as-headroom vs the unmet-demand framing now in rubric 0.6.0")
print("=" * 78)
print()
print("STEP 1 -- what CAGR does each category actually carry?")
print("-" * 78)
print(f"{'case':24}{'category':34}{'CAGR range':>16}")
for case, d in CAGR.items():
    v = d["values"]
    print(f"{case:24}{d['category'][:33]:34}{min(v):>6.2f}-{max(v):<7.2f}")
print()
print("  source detail:")
for case, d in CAGR.items():
    print(f"    {case:24} {d['source']}")

print()
print("STEP 2 -- compute ASML's own revenue CAGR (audited, no estimate involved)")
print("-" * 78)
a, b, y0, y1 = ASML_REV
n = y1 - y0
asml_cagr = ((b / a) ** (1 / n) - 1) * 100
# verify by a different method: compounded forward from a
check = a * (1 + asml_cagr / 100) ** n
print(f"  FY{y0} EUR {a}bn -> FY{y1} EUR {b}bn over {n} years")
print(f"  CAGR = ({b}/{a})^(1/{n}) - 1 = {asml_cagr:.2f}%")
print(f"  cross-check: {a} x (1+{asml_cagr/100:.4f})^{n} = EUR {check:.3f}bn "
      f"(target {b}, delta {abs(check-b):.4f})")

print()
print("STEP 3 -- map CAGR to a 1-5 level, as any monotone mapping must")
print("-" * 78)
# Anchor set declared explicitly so the mapping is auditable, not hidden.
# Chosen to be generous to CAGR: wide enough to fit every observed value usefully.
BANDS = [(0, 1), (2, 2), (5, 3), (8, 4), (10.01, 5)]


def to_level(c: float) -> float:
    """Linear interpolation between anchor points -> a continuous 1-5 level."""
    pts = [(0.0, 1.0), (2.0, 2.0), (5.0, 3.0), (8.0, 4.0), (10.0, 5.0)]
    if c <= pts[0][0]:
        return 1.0
    if c >= pts[-1][0]:
        return 5.0
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        if x0 <= c <= x1:
            return y0 + (y1 - y0) * (c - x0) / (x1 - x0)
    return 1.0


print(f"  anchor points: {[(int(x), int(y)) for x, y in [(0,1),(2,2),(5,3),(8,4),(10,5)]]}")
print()
print(f"{'case':24}{'CAGR mean':>10}{'-> level':>10}{'  (min-max level)'}")
cagr_levels = {}
for case, d in CAGR.items():
    v = d["values"]
    mean = sum(v) / len(v)
    lv = to_level(mean)
    lo, hi = to_level(min(v)), to_level(max(v))
    cagr_levels[case] = lv
    print(f"{case:24}{mean:>9.2f}%{lv:>10.2f}{f'   ({lo:.2f}-{hi:.2f})'}")
lv_asml = to_level(asml_cagr)
print(f"{'asml-own-revenue':24}{asml_cagr:>9.2f}%{lv_asml:>10.2f}   (n/a - company, not market)")

print()
print("STEP 4 -- does CAGR separate the two cases that matter?")
print("-" * 78)
gap_cagr = cagr_levels["E1-asml"] - cagr_levels["bubbletea"]
print(f"  CAGR            ASML {cagr_levels['E1-asml']:.2f}  bubbletea "
      f"{cagr_levels['bubbletea']:.2f}  -> gap {gap_cagr:+.2f}")

# the framing currently in rubric 0.6.0, measured in experiment_headroom_reframe.py
UNMET = {"E1-asml": 3.33, "bubbletea": 1.88, "C9-b2b-it-services": 1.95,
         "N1-closedbusiness": 1.67}
gap_unmet_raw = UNMET["E1-asml"] - UNMET["bubbletea"]
# put both on a comparable 0-1 scale to compare fairly
cagr_span = gap_cagr / 4
unmet_span = gap_unmet_raw / 4
print(f"  unmet demand    ASML {UNMET['E1-asml']:.2f}  bubbletea "
      f"{UNMET['bubbletea']:.2f}  -> gap {gap_unmet_raw:+.2f}")
print()
print(f"  as a fraction of scale:  CAGR {cagr_span:.1%}  vs  unmet demand {unmet_span:.1%}")
print(f"  ratio: unmet demand separates {unmet_span/cagr_span:.1f}x wider")

print()
print("STEP 5 -- the killer: the published CAGRs barely differ")
print("-" * 78)
allc = [sum(d["values"]) / len(d["values"]) for d in CAGR.values()]
print(f"  every researched category CAGR falls in "
      f"{min(allc):.2f}% - {max(allc):.2f}%  (span {max(allc)-min(allc):.2f}pp)")
print("  the research industry forecasts ASML's category at ~9% and bubble tea at ~7%.")
print("  It does not see a supply-starved monopoly as an unusual-growth market.")
print("  So CAGR cannot encode Sean's insight, however it is mapped.")

print()
print("STEP 6 -- data availability for the actual customer base")
print("-" * 78)
print("  cases with a published category CAGR: 4 of 17 (ASML, bubbletea, pet, TCM)")
print("  cases with NONE (no published market report exists): 13 of 17")
print("    -> bonefirm, observeco, koi, C2, C4, C5, C9, D1, D2, E2, E4, N1, N2")
print("  the typical ObserveCo lead is an unlisted SME in a niche the research")
print("  houses do not cover. CAGR is available precisely for the businesses that")
print("  do NOT need a free report (large, listed, well-covered categories).")

print()
print("STEP 7 -- source reliability, same category")
print("-" * 78)
tcm = CAGR["C6-euyansang"]["values"]
print(f"  Singapore herbal/TCM CAGR: {', '.join(f'{x}%' for x in sorted(tcm))}")
print(f"  spread {min(tcm)}% - {max(tcm)}% = {max(tcm)/min(tcm):.1f}x disagreement between")
print("  firms measuring the same category in the same year.")
bt = CAGR["bubbletea"]["values"]
print(f"  Singapore bubble tea market SIZE: 6W/DMI report USD 11.79M-17.12M (2025);")
print("  Tridge trade data shows USD 201M of imports (2023).")
print("  ~17x disagreement on the size of the same market.")
print("  These are SEO/report-mill publishers, not audited sources.")
