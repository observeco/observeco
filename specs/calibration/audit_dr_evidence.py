"""Sean's DR challenge: are my scores contradicted by physical evidence?

His claim: "You have blind gaps. Best Denki, 24/7 fitness, zoff singapore are able to
generate revenue which means it is able to reach out to successfully attract customers.
That automatically challenges your 'no evidence they will pay this price'."
Plus: "Breadtalk has no issues with generating revenue and reaching out to the demand."

My DR level 2 says: "Weak. Only a demographic or a category is named -- no trigger, no
channel, and no evidence they would pay this price."

If a business is trading, with outlets and published prices, then evidence they pay this
price EXISTS -- regardless of how thin the submission text is. That would make my scores
wrong on a specific and checkable ground.

This measures the BLAST RADIUS: every case where I scored DR low on text, where physical
evidence of reach exists in the corpus.
"""
import csv
import glob
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
V12 = json.loads((HERE / "rubric-v1.2.0.json").read_text())
idx = json.loads((HERE / "inputs-v4" / "_index.json").read_text())
rows = list(csv.DictReader(open(HERE / "sean-regrade-raw.csv")))
by = {r["company"]: r for r in rows}

mine = {}
for p in (HERE / "runs-v12").glob("jev-*.json"):
    r = json.loads(p.read_text())
    d = r.get("dimensions_display_1to5") or {}
    u = set(r.get("dimensions_unscored") or [])
    mine[r["case"]] = {k: (None if k in u else d.get(k)) for k in d}


def num(x):
    x = ("" if x is None else str(x)).strip()
    if x.lower() in ("n/a", "na", "", "-", "none", "nan"):
        return None
    try:
        return float(x)
    except Exception:
        return None


# Physical evidence of reach: outlets, revenue, prices, trading history, store counts.
EVID = re.compile(
    r"(\d[\d,]*)\s*(outlets?|stores?|clubs?|restaurants?|branches|shops?|supermarkets?)"
    r"|published|store finder|islandwide|revenue|S\$[\d.]|largest|leading|market leader"
    r"|founded|since \d{4}|chain|network", re.I)

print("=" * 84)
print("THE NAMED CASES — what did I score, and what evidence exists?")
print("=" * 84)
named = ["Best Denki Singapore", "24/7 Fitness", "Zoff Singapore", "BreadTalk",
         "A home massage service", "Harvey Norman Singapore"]
for nm in named:
    cid = None
    for c, e in idx["companies"].items():
        if e["name"] == nm:
            cid = c
            break
    if not cid:
        print("  %-30s (not found)" % nm)
        continue
    r = by.get(nm) or {}
    src = json.loads((HERE / "inputs-v4" / (cid + ".json")).read_text())
    meta = src.get("_meta", {})
    ev = " ".join(str(meta.get(k) or "") for k in ("LABEL_SOURCE", "sources"))
    me = (mine.get(cid) or {}).get("demand_reach")
    his = num(r.get("YOUR_DR"))
    print()
    print("  %s  [%s]" % (nm, idx["companies"][cid]["cat"]))
    print("     my DR=%s   his DR=%s" % (me, his))
    print("     price: %s" % (src.get("form", {}).get("your_price_point") or "-")[:80])
    found = EVID.findall(ev)
    print("     evidence in corpus: %s" % (found[:6] if found else "NONE FOUND"))

print()
print("=" * 84)
print("BLAST RADIUS — every case where my DR is LOW but physical evidence exists")
print("=" * 84)
print()
affected = []
for cid, e in idx["companies"].items():
    me = (mine.get(cid) or {}).get("demand_reach")
    if me is None or me > 2:
        continue
    src = json.loads((HERE / "inputs-v4" / (cid + ".json")).read_text())
    meta = src.get("_meta", {})
    form = src.get("form", {})
    ev = " ".join(str(meta.get(k) or "") for k in ("LABEL_SOURCE", "sources"))
    ev += " " + str(form.get("your_price_point") or "")
    hits = EVID.findall(ev)
    r = by.get(e["name"]) or {}
    his = num(r.get("YOUR_DR"))
    affected.append((e["name"], e["cat"], me, his, len(hits),
                     " ".join(str(form.get("your_price_point") or "").split())[:40]))

print("  cases where MY DR <= 2: %d" % len(affected))
with_ev = [a for a in affected if a[4] > 0]
print("  of those, with physical evidence of reach in the corpus: %d" % len(with_ev))
print()
print("  %-34s %-14s %5s %5s %6s" % ("company", "category", "myDR", "hisDR", "evid"))
for nm, cat, me, his, n, pr in sorted(with_ev, key=lambda x: (x[2], x[0]))[:30]:
    print("  %-34s %-14s %5s %5s %6d  %s" % (nm[:33], cat[:13], me, his, n, pr))
print()
if len(with_ev) > 30:
    print("  ... +%d more" % (len(with_ev) - 30))

print()
print("=" * 84)
print("DR DISTRIBUTION — mine vs his")
print("=" * 84)
print()
from collections import Counter
mi = Counter(int(v) for v in ((mine.get(c) or {}).get("demand_reach")
                              for c in idx["companies"]) if v)
hi = Counter(int(v) for v in (num(r.get("YOUR_DR")) for r in rows) if v)
print("  mine: %s" % dict(sorted(mi.items())))
print("  his : %s" % dict(sorted(hi.items())))
print()
print("  mine mean %.2f  his mean %.2f"
      % (sum(k * v for k, v in mi.items()) / sum(mi.values()),
         sum(k * v for k, v in hi.items()) / sum(hi.values())))
