"""Guard against the obvious trap: SSIC reclassifications.

Singapore's SSIC has been revised several times (2005, 2010, 2015, 2020). If a code's
coverage changed, a long-span CAGR measures RECLASSIFICATION, not market growth. Check for
structural breaks by computing year-on-year jumps and looking for discontinuities.
"""
import json
import subprocess

URL = "https://tablebuilder.singstat.gov.sg/api/table/tabledata/M085851"


def fetch(url):
    out = subprocess.run(["curl", "-s", "-A", "Mozilla/5.0", url],
                         capture_output=True, text=True, timeout=120)
    return json.loads(out.stdout)["Data"]


d = fetch(URL)
rows = {r["rowText"]: r for r in d["row"]}


def series_of(label):
    r = rows.get(label)
    if not r:
        return {}
    s = {}
    for c in r.get("columns", []):
        try:
            s[c["key"]] = float(c["value"])
        except (TypeError, ValueError, KeyError):
            pass
    return {k: v for k, v in s.items() if k.isdigit()}


def cagr(a, b, n):
    if a <= 0 or b <= 0 or n <= 0:
        return float("nan")
    return ((b / a) ** (1 / n) - 1) * 100


CASES = {
    "SSIC 56123 - Food & Drink Kiosks Mainly For Takeaway And Delivery": "bubble tea",
    "SSIC 9609 - Other Personal Service Nec (e.g. Pet Care And Fortune Telling Services)": "pet care",
}

print("=" * 80)
print("STRUCTURAL BREAK CHECK -- is a long-span CAGR measuring growth or reclassification?")
print("=" * 80)
print()
print("  SSIC revisions: 2005, 2010, 2015, 2020. A break at one of these means the")
print("  code's COVERAGE changed, so the series is not comparable across the break.")
print()

for label, tag in CASES.items():
    s = series_of(label)
    if not s:
        print(f"  {tag}: not found\n")
        continue
    yrs = sorted(s)
    print(f"  {tag}  [{label[:52]}]")
    print(f"    span {yrs[0]}..{yrs[-1]}")
    print()
    print(f"    {'period':22}{'CAGR':>9}   note")
    spans = [(yrs[0], "2005"), ("2005", "2010"), ("2010", "2015"),
             ("2015", "2020"), ("2020", yrs[-1])]
    for a, b in spans:
        if a in s and b in s:
            n = int(b) - int(a)
            g = cagr(s[a], s[b], n)
            note = ""
            if a in ("2005", "2010", "2015", "2020"):
                note = "<- SSIC revision boundary"
            print(f"    {a}-{b:<16}{g:>+8.2f}%   {note}")
    print()
    # year-on-year jumps, flagging anything over 60%
    print("    year-on-year change, flagged where |change| > 60%:")
    for i in range(1, len(yrs)):
        a, b = yrs[i - 1], yrs[i]
        if s[a] > 0:
            ch = (s[b] - s[a]) / s[a] * 100
            if abs(ch) > 60:
                ssic = a in ("2005", "2010", "2015", "2020") or b in ("2005", "2010", "2015", "2020")
                print(f"      {a}->{b}: {s[a]:>6.0f} -> {s[b]:>6.0f}  ({ch:+.0f}%)"
                      f"{'  <- AT SSIC BOUNDARY' if ssic else ''}")
    print()

print("=" * 80)
print("VERDICT ON ROBUSTNESS")
print("=" * 80)
print("""
  The recent-period CAGRs (2020 onwards, after the last revision) are the only ones
  safe to quote. Anything spanning a revision boundary mixes coverage changes into
  the growth rate -- exactly the error that made the report-mill CAGRs unusable.
""")
