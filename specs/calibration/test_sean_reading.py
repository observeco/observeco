"""Test Sean's reading of mental_advantage and demand_reach against the corpus.

His read:
  MA = "how well you are ALREADY KNOWN to your expected customer, for the size of your
        INTENDED MARKET"
  DR = "how much of your buyers have you ACTUALLY FOUND"

Two testable claims:
  T1. If MA is about being KNOWN, the most famous player in a category should top it.
  T2. If MA's anchor were MARKET size, every small business in a big market scores low.
"""
import glob
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
DIMS = ["mental_advantage", "defensibility", "competitive_room",
        "market_headroom", "demand_reach"]


def get(cid):
    c = glob.glob(str(HERE / "runs" / ("jev-%s*.json" % cid)))
    if not c:
        return None
    return json.loads(Path(c[0]).read_text())


print("=" * 80)
print("T1 — IF MA MEASURED 'BEING KNOWN', THE MOST FAMOUS PLAYER WOULD TOP EACH CATEGORY")
print("=" * 80)
groups = {
    "fast-food (McDonald's = market leader, 150+ outlets)":
        [("FF01", "McDonald's"), ("FF02", "KFC"), ("FF03", "Burger King"),
         ("FF05", "Jollibee"), ("FF04", "Subway"), ("FF06", "Shake Shack")],
    "supermarket (NTUC FairPrice = largest, 125 stores)":
        [("SM01", "NTUC FairPrice"), ("SM02", "Sheng Siong"), ("SM03", "Cold Storage"),
         ("SM05", "Don Don Donki"), ("SM04", "Giant")],
    "health-beauty (Watsons = largest share, 18%)":
        [("HB01", "Watsons"), ("HB02", "Guardian"), ("HB03", "Unity"), ("HB04", "Sephora")],
}
for g, items in groups.items():
    print()
    print("--- %s ---" % g)
    for cid, nm in items:
        r = get(cid)
        if not r:
            continue
        d = r.get("dimensions_display_1to5") or {}
        print("   %-16s MA=%s" % (nm, d.get("mental_advantage")))

print()
print("=" * 80)
print("T1b — A VERY WELL-KNOWN BUSINESS THAT WAS RETRIEVED FOR NOTHING")
print("=" * 80)
for cid, nm in (("GY07-true", "True Fitness (14 clubs, major brand, now dead)"),
                ("GY02-anytime", "Anytime Fitness (161 outlets)")):
    r = get(cid)
    d = r.get("dimensions_display_1to5") or {}
    print("   %-48s MA=%s" % (nm, d.get("mental_advantage")))

print()
print("=" * 80)
print("T2 — IF THE ANCHOR WERE MARKET SIZE, NO TINY BUSINESS COULD SCORE HIGH")
print("=" * 80)
print("(home-based operators: tiny business, big market. Business-size anchor allows 4-5.)")
tiny = []
for dirn in ("inputs-v3",):
    idx = json.loads((HERE / dirn / "_index.json").read_text())
    for cid in idx["companies"]:
        meta = json.loads((HERE / dirn / (cid + ".json")).read_text())["_meta"]
        r = get(meta["case"])
        if not r:
            continue
        d = r.get("dimensions_display_1to5") or {}
        tiny.append((d.get("mental_advantage"), idx["companies"][cid]["name"],
                     idx["companies"][cid].get("cat")))
tiny.sort(key=lambda x: -(x[0] or 0))
print("   tiny businesses scoring MA=4 or 5: %d" % sum(1 for t in tiny if (t[0] or 0) >= 4))
for v, nm, cat in tiny[:6]:
    print("      MA=%s  %-36s [%s]" % (v, nm[:35], cat))

print()
print("=" * 80)
print("T3 — DEMAND_REACH: IS IT A CAPTURE RATE ('how much found') OR ADDRESSABILITY?")
print("=" * 80)
r = json.loads((HERE / "rubric.json").read_text())
print()
print("Rubric L5 verbatim:")
print("  ", r["questions"]["demand_reach"]["levels"][4])
print()
print("L1 verbatim:")
print("  ", r["questions"]["demand_reach"]["levels"][0])
print()
print("A capture rate would be a % or a count. The levels contain neither -- they grade")
print("the DEFINABILITY of the group and the existence of a CHANNEL. Spread in corpus:")
from collections import Counter
c = Counter()
for p in glob.glob(str(HERE / "runs" / "jev-*.json")):
    rr = json.loads(Path(p).read_text())
    d = rr.get("dimensions_display_1to5") or {}
    u = set(rr.get("dimensions_unscored") or [])
    if "demand_reach" not in u and d.get("demand_reach") is not None:
        c[d["demand_reach"]] += 1
for k in sorted(c):
    print("   L%d: %d cases" % (k, c[k]))
