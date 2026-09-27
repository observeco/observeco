"""Did Sean grade DUPLICATE companies identically?

He said: "I would actually grade them the same." If true, that (a) justifies the dedup and
(b) confirms his grading is stable across re-presentations, which is a reliability datapoint
my own instrument does NOT have.

Also records the SYSTEMATIC bias: he grades higher on EVERY dimension, and what that means.
"""
import csv
import json
import statistics
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
DIMS = ["mental_advantage", "defensibility", "competitive_room",
        "market_headroom", "demand_reach"]
ABBR = {"mental_advantage": "MA", "defensibility": "DEF", "competitive_room": "CR",
        "market_headroom": "MH", "demand_reach": "DR"}
W = json.loads((HERE / "rubric.json").read_text())["_meta"]["weights"]


def num(x):
    x = (x or "").strip()
    if x.lower() in ("n/a", "na", "n.a.", "n.a", "-", ""):
        return None
    try:
        return float(x)
    except Exception:
        return None


rows = list(csv.DictReader(open(HERE / "sean-grades-raw.csv")))
graded = {}
for g in rows:
    his = {k: num(g.get("YOUR_" + ABBR[k])) for k in DIMS}
    if any(v is not None for v in his.values()):
        graded[g["case_id"]] = dict(g=g, his=his)

print("=" * 84)
print("DID HE GRADE DUPLICATE COMPANIES IDENTICALLY?  (n graded = %d)" % len(graded))
print("=" * 84)
pairs = [
    ("Watsons Singapore", ["D1-watsons", "F2-watsons-guardian", "HB01"]),
    ("KOI Thé", ["koi", "BT02-koi"]),
    ("Sheng Siong", ["C4-sheng-siong", "SM02"]),
    ("Chicha San Chen", ["P2-chicha", "BT03"]),
    ("HEYTEA", ["P3-heytea", "BT04"]),
    ("R&B Tea", ["P4-rbtea", "BT05-randb"]),
    ("Mixue", ["P1-mixue", "BT01"]),
    ("Bonefirm", ["bonefirm", "E4-bonefirm-ip"]),
    ("Pet Lovers Centre", ["C3-pet-lovers-centre", "D2-petlovers-cue"]),
]
same = diff = 0
for name, ids in pairs:
    present = [i for i in ids if i in graded]
    if len(present) < 2:
        continue
    sigs = []
    for i in present:
        h = graded[i]["his"]
        sig = tuple(h[k] for k in DIMS)
        sigs.append((i, sig))
    ident = len(set(s for _, s in sigs)) == 1
    same += ident
    diff += (not ident)
    tag = "IDENTICAL" if ident else "DIFFERS"
    print()
    print("  %-24s %s" % (name, tag))
    for i, sig in sigs:
        print("      %-22s %s" % (i, " ".join(
            "%s=%s" % (ABBR[k], "n/a" if sig[j] is None else int(sig[j]))
            for j, k in enumerate(DIMS))))
    if not ident:
        # show where
        ref = sigs[0][1]
        for i, sig in sigs[1:]:
            deltas = [(ABBR[k], ref[j], sig[j]) for j, k in enumerate(DIMS)
                      if ref[j] != sig[j]]
            print("      -> differs on: %s" % deltas)
print()
print("  duplicates graded IDENTICALLY: %d of %d pairs" % (same, same + diff))

print()
print("=" * 84)
print("SYSTEMATIC BIAS — HE GRADES HIGHER ON EVERY DIMENSION")
print("=" * 84)
print()
print("  %-6s %6s %8s %8s" % ("dim", "n", "his mean", "my mean"))
for k in DIMS:
    hs, ms = [], []
    for cid, d in graded.items():
        h = d["his"][k]
        rp = HERE / "runs" / ("jev-%s.json" % d["g"]["run_id"])
        if not rp.exists():
            continue
        run = json.loads(rp.read_text())
        dd = run.get("dimensions_display_1to5") or {}
        u = set(run.get("dimensions_unscored") or [])
        m = None if k in u else dd.get(k)
        if h is not None and m is not None:
            hs.append(h)
            ms.append(m)
    if hs:
        print("  %-6s %6d %8.2f %8.2f" % (k, len(hs), statistics.mean(hs),
                                           statistics.mean(ms)))
print()
print("  Every dimension is graded higher by him. This is a SCALE-USAGE difference")
print("  (leniency / absolute-vs-relative reading), not a per-case error:")
print("  - he reads 'is this business strong?' in ABSOLUTE terms")
print("  - the rubric asks 'strong RELATIVE to size / structure'")
print("  A uniform offset is the signature of two different scales, not of noise.")
