"""prove_rounding_flip.py — does banding the UNROUNDED composite flip bands?"""
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

def num(x):
    x = ("" if x is None else str(x)).strip()
    if x.lower() in ("n/a","na","","-","none","nan"): return None
    try: return float(x)
    except Exception: return None

def band_of(s):
    for nm, lo, hi in BANDS:
        if lo <= s <= hi: return nm
    return BANDS[0][0] if s < BANDS[0][1] else BANDS[-1][0]

def comp_raw(vals):
    sc=[k for k in W if vals.get(k) is not None]
    if not sc: return None
    tot=sum(W[k] for k in sc)
    return sum(vals[k]/COUNTS[k]*(W[k]/tot*100) for k in sc)

flips=[]; n=0
for cid, e in idx["companies"].items():
    if e["cat"]=="home-not-permitted": continue
    f = HERE/"runs-v18"/("jev-%s.json" % cid)
    if not f.exists(): continue
    if json.loads(f.read_text()).get("composite") is None: continue
    raw = comp_raw({d: num((by.get(e["name"]) or {}).get("YOUR_"+ABBR[d])) for d in W})
    if raw is None: continue
    n+=1
    r_rounded = band_of(round(raw)); r_raw = band_of(raw)
    if r_rounded != r_raw:
        flips.append((e["name"], raw, r_rounded, r_raw))
print(f"cases: {n}   band flips from rounding alone: {len(flips)}")
for nm, raw, br, bw in flips:
    print(f"   {nm[:36]:36} raw={raw:7.3f}  rounded->{br:20} unrounded->{bw}")
print()
print("BOUNDARIES:", [(b[0], b[1], b[2]) for b in BANDS])
print()
# now: how many of his cases sit within 0.5 of a boundary?
near=0
for cid, e in idx["companies"].items():
    if e["cat"]=="home-not-permitted": continue
    f = HERE/"runs-v18"/("jev-%s.json" % cid)
    if not f.exists(): continue
    if json.loads(f.read_text()).get("composite") is None: continue
    raw = comp_raw({d: num((by.get(e["name"]) or {}).get("YOUR_"+ABBR[d])) for d in W})
    if raw is None: continue
    for _, lo, hi in BANDS:
        if abs(raw-lo)<0.5 or abs(raw-hi+1)<0.5: near+=1; break
print(f"his cases within 0.5 of a band boundary: {near}")
