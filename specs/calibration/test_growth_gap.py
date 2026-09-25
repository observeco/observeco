"""STEP D corrected -- annualise monthly formations against annual cessations.

Dataset key formats differ: formations are keyed '2026Aug' (monthly), cessations are
keyed '2025' (annual). The earlier loop matched on k[:4] against a 7-char key, so it
found nothing. Fixed here by parsing both formats explicitly.
"""
import json
import urllib.request
from collections import defaultdict

BASE = "https://data.gov.sg/api/action/datastore_search"


def fetch(rid: str, limit: int = 400) -> list:
    url = f"{BASE}?resource_id={rid}&limit={limit}"
    with urllib.request.urlopen(url, timeout=60) as r:
        return json.load(r)["result"]["records"]


def cagr(a: float, b: float, years: int) -> float:
    r = (b / a) ** (1 / years) - 1
    assert abs(a * (1 + r) ** years - b) < max(1e-6, abs(b) * 1e-9), "CAGR self-check"
    return r * 100


def annualise_monthly(row, year):
    """Sum '2025Jan'..'2025Dec' keys into a yearly total."""
    vals = [float(row[k]) for k in row
            if len(k) == 7 and k[:4] == year and row.get(k) not in (None, "")]
    return (sum(vals), len(vals)) if vals else (None, 0)


print("=" * 80)
print("DEMAND GROWTH vs SUPPLY GROWTH -- free, government, no founder input")
print("=" * 80)

# ---------------------------------------------------------------- DEMAND
recs = fetch("d_7a24e1f85969c45ad68a89f7acf4e7a8")
by = {r["DataSeries"].strip(): r for r in recs}
fs = by["Food And Food Serving Services"]
demand_g = cagr(float(fs["2018"]), float(fs["2023"]), 5)
print()
print(f"DEMAND (SingStat household expenditure, Food & Food Serving Services)")
print(f"  S${float(fs['2018']):,.1f}/mo -> S${float(fs['2023']):,.1f}/mo  =  "
      f"{demand_g:.2f}%/yr")

# ---------------------------------------------------------------- SUPPLY
fm = fetch("d_739ef616852dcc1ecdb4a1c8bd0dcc8b")
cs = fetch("d_29a0c196717b76f2329e193bc60ea7c2")


def fb(rows):
    return [r for r in rows
            if "food" in str(r.get("DataSeries", "")).lower()
            and "beverage" in str(r.get("DataSeries", "")).lower()]


f_row, c_row = fb(fm)[0], fb(cs)[0]

print()
print("SUPPLY (ACRA, Food & Beverage Services)")
print(f"  {'year':6}{'formations':>12}{'mo':>4}{'cessations':>12}{'net':>10}")
table = {}
for y in [str(x) for x in range(2015, 2026)]:
    ft, fn = annualise_monthly(f_row, y)
    cv = c_row.get(y)
    ct = float(cv) if cv not in (None, "") else None
    if ft is None or ct is None or fn < 12:
        continue
    table[y] = (ft, ct, ft - ct)
    print(f"  {y:6}{ft:>12,.0f}{fn:>4}{ct:>12,.0f}{ft-ct:>10,.0f}")

yrs = sorted(table)
y0, y1 = yrs[0], yrs[-1]
supply_g = cagr(table[y0][0], table[y1][0], int(y1) - int(y0))
net0, net1 = table[y0][2], table[y1][2]
print()
print(f"  formation CAGR {y0}->{y1}: {supply_g:.2f}%/yr "
      f"({table[y0][0]:,.0f} -> {table[y1][0]:,.0f}/yr)")
print(f"  net formation   {y0}->{y1}: {net0:,.0f} -> {net1:,.0f}")

print()
print("=" * 74)
print(f"  DEMAND growth  {demand_g:>6.2f}%/yr   (household spend intensity)")
print(f"  SUPPLY growth  {supply_g:>6.2f}%/yr   (new F&B entity formations)")
print(f"  GAP            {demand_g - supply_g:>6.2f}pp")
print("=" * 74)
if demand_g > supply_g:
    print("  demand outgrows supply -> TIGHTENING -> headroom positive")
else:
    print("  supply outgrows demand -> CROWDING -> headroom negative")

print()
print("LIMITS OF THIS SIGNAL:")
print("  * SSIC SECTION level -- all ~40k F&B entities pooled. No 'bubble tea'.")
print("  * formations count ENTITIES, not capacity. 10 tiny stalls != 1 new plant.")
print("  * a section can crowd while one niche inside it is supply-starved.")
print("  * Singapore-only; ASML has no SSIC series at all.")
print()
print("  => real, free, indefinite CONTEXT signal at section granularity.")
print("     Not the business's own headroom, and cannot be.")
