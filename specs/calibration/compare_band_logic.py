"""compare_band_logic.py — why do the fixed scripts disagree with band_agreement_harness.py?"""
import csv, json
from pathlib import Path
HERE = Path(__file__).resolve().parent
V = json.loads((HERE/"rubric-v1.8.0.json").read_text())
W = V["_meta"]["weights"]; BANDS = V["_meta"]["bands"]
COUNTS = {d: len(V["questions"][d]["levels"]) for d in W}
ABBR = {"relative_strength":"RS","mental_advantage":"MA","defensibility":"DEF",
        "competitive_room":"CR","market_headroom":"MH","demand_reach":"DR"}
idx = json.loads((HERE/"inputs-v4"/"_index.json").read_text())
by = {r["company"]: r for r in csv.DictReader(open(HERE/"sean-regrade-raw.csv"))}

print("COUNTS per dim:", COUNTS)
print("W per dim     :", W)
print()

def num(x):
    x = ("" if x is None else str(x)).strip()
    if x.lower() in ("n/a","na","","-","none","nan"): return None
    try: return float(x)
    except Exception: return None

def band_of(s):
    if s is None: return None
    for nm, lo, hi in BANDS:
        if lo <= s <= hi: return nm
    return BANDS[0][0] if s < BANDS[0][1] else BANDS[-1][0]

# implementation A = mine (renormalise then sum v/count*used)
def compA(vals):
    sc = [k for k in W if vals.get(k) is not None]
    if not sc: return None
    tot = sum(W[k] for k in sc)
    used = {k: W[k]/tot*100 for k in sc}
    return round(sum(vals[k]/COUNTS[k]*used[k] for k in sc))

# implementation B = test_target_segment (fixed)
def compB(vals):
    acc = tot = 0.0
    for d, v in vals.items():
        if v is None: continue
        acc += W[d] * (v/COUNTS[d]) * 100.0
        tot += W[d]
    return acc/tot if tot else None

diff = 0; n = 0
rows=[]
for cid, e in idx["companies"].items():
    if e["cat"] == "home-not-permitted": continue
    f = HERE/"runs-v18"/("jev-%s.json" % cid)
    if not f.exists(): continue
    run = json.loads(f.read_text())
    if run.get("composite") is None: continue
    r = by.get(e["name"]) or {}
    hd = {d: num(r.get("YOUR_"+ABBR[d])) for d in W}
    a, b = compA(hd), compB(hd)
    if a is None or b is None: continue
    n += 1
    if abs(a-b) > 0.51:
        diff += 1
        rows.append((e["name"], a, b, band_of(a), band_of(b)))
print(f"cases compared: {n}   composite differs (>0.5): {diff}")
for nm, a, b, ba, bb in rows[:12]:
    print(f"   {nm[:34]:34} A={a:5.1f} ({ba})   B={b:5.1f} ({bb})")
print()
from collections import Counter
ca = Counter(band_of(compA({d: num((by.get(e["name"]) or {}).get("YOUR_"+ABBR[d])) for d in W}))
             for cid, e in idx["companies"].items()
             if e["cat"] != "home-not-permitted"
             and (HERE/"runs-v18"/("jev-%s.json" % cid)).exists()
             and json.loads((HERE/"runs-v18"/("jev-%s.json" % cid)).read_text()).get("composite") is not None)
print("Sean band dist, implementation A:", dict(ca))
cb = Counter(band_of(compB({d: num((by.get(e["name"]) or {}).get("YOUR_"+ABBR[d])) for d in W}))
             for cid, e in idx["companies"].items()
             if e["cat"] != "home-not-permitted"
             and (HERE/"runs-v18"/("jev-%s.json" % cid)).exists()
             and json.loads((HERE/"runs-v18"/("jev-%s.json" % cid)).read_text()).get("composite") is not None)
print("Sean band dist, implementation B:", dict(cb))
