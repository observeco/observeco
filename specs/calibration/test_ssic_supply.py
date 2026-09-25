"""BREAKTHROUGH TEST -- SSIC-granular SUPPLY data exists free, back to 1993.

SingStat table M085851 'Formation Of All Business Entities By Detailed Industry, Annual'
carries 128 series including category-level codes that map onto our actual cases:

  SSIC 56123          Food & Drink Kiosks Mainly For Takeaway And Delivery  <- bubble tea
  SSIC 56             Food & Beverage
  SSIC 9609           Other Personal Service Nec (e.g. Pet Care And Fortune Telling)
  SSIC 93             Sports Activities And Amusement And Recreation          <- gyms
  SSIC 86             Health Services
  SSIC 85             Education
  SSIC 472            Food & Alcohol (retail)

This is a SUPPLY-side series at CATEGORY granularity -- not the top-level SSIC section
I concluded was the limit. Test whether it produces a usable headroom signal.
"""
import json
import subprocess

URL = "https://tablebuilder.singstat.gov.sg/api/table/tabledata/M085851"


def fetch_table(url: str) -> dict:
    """curl with a User-Agent -- the API 403s urllib."""
    out = subprocess.run(["curl", "-s", "-A", "Mozilla/5.0", url],
                         capture_output=True, text=True, timeout=120)
    return json.loads(out.stdout)["Data"]


def cagr(a: float, b: float, years: int) -> float:
    if a <= 0 or b <= 0 or years <= 0:
        return float("nan")
    r = (b / a) ** (1 / years) - 1
    assert abs(a * (1 + r) ** years - b) < max(1e-6, abs(b) * 1e-9), "CAGR self-check"
    return r * 100


print("=" * 80)
print("SSIC-GRANULAR SUPPLY DATA -- does a category-level headroom signal compute?")
print("=" * 80)

d = fetch_table(URL)
print(f"  {d.get('title')}")
print(f"  frequency {d.get('frequency')} | series {len(d['row'])}")
print(f"  source: {d.get('datasource')}")

TARGETS = {
    "SSIC 56123 - Food & Drink Kiosks Mainly For Takeaway And Delivery": "bubble tea",
    "SSIC 56 - Food & Beverage": "F&B (section proxy)",
    "SSIC 9609 - Other Personal Service Nec (e.g. Pet Care And Fortune Telling Services)": "pet care",
    "SSIC 93 - Sports Activities And Amusement And Recreation Activities": "gyms / ActiveSG",
    "SSIC 86 - Health Services": "clinics",
    "SSIC 85 - Education": "tuition",
    "SSIC 472 - Food & Alcohol": "retail food",
}

rows = {r["rowText"]: r for r in d["row"]}

print()
print("=" * 80)
print("SUPPLY FORMATION TREND per category (new entities registered per year)")
print("=" * 80)
for label, maps in TARGETS.items():
    r = rows.get(label)
    if not r:
        print(f"\n  {label[:70]}: NOT FOUND")
        continue
    cols = r.get("columns", [])
    # columns: [{key, value}] -- key is the period
    series = {}
    for c in cols:
        k = c.get("key", "")
        v = c.get("value")
        try:
            series[k] = float(v)
        except (TypeError, ValueError):
            pass
    yrs = sorted([k for k in series if k.isdigit()])
    if len(yrs) < 6:
        print(f"\n  {label[:70]}: only {len(yrs)} years")
        continue
    y0, y1 = yrs[0], yrs[-1]
    a, b = series[y0], series[y1]
    g = cagr(a, b, int(y1) - int(y0))
    recent = [f"{y}:{series[y]:.0f}" for y in yrs[-4:]]
    print(f"\n  {label[:70]}  [{maps}]")
    print(f"    {y0} -> {y1}: {a:,.0f} -> {b:,.0f} formations/yr")
    print(f"    CAGR {g:+.2f}%/yr    recent: {', '.join(recent)}")

print()
print("=" * 80)
print("WHAT THIS DOES AND DOES NOT GIVE US")
print("=" * 80)
print("""
  GIVES: supply-side growth at CATEGORY granularity, free, ~15+ years, forward forever.
         For bubble tea specifically: SSIC 56123 kiosks-for-takeaway. That is the
         closest thing to a bubble-tea series that exists in public data.
         Rising formations = new capacity entering = crowding pressure.
         Flat/falling formations = closed to new entrants.

  DOES NOT GIVE: demand. This is a SUPPLY series only. Nothing here says whether
         customers want more bubble tea.

  So a GROWTH GAP needs a demand counterpart at the same granularity, and there is
  none free at SSIC 5-digit level. SingStat spend data stops at ~10 goods/services
  groups ('Food And Food Serving Services').

  WHAT IT CAN STILL DO: supply growth alone is a real, defensible CROWDING signal.
  Combined with a demand proxy at a coarser level, it gives a two-level reading:
    demand growth (coarse) vs supply growth (fine).
""")
