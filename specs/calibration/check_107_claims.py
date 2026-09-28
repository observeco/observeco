"""check_107_claims.py — verify the three derived claims in spec S10.7."""
import csv, json
from pathlib import Path
HERE = Path(__file__).resolve().parent
V = json.loads((HERE / "rubric-v1.8.0.json").read_text())
W = V["_meta"]["weights"]; BANDS = V["_meta"]["bands"]
COUNTS = {d: len(V["questions"][d]["levels"]) for d in W}
ABBR = {"relative_strength": "RS", "mental_advantage": "MA", "defensibility": "DEF",
        "competitive_room": "CR", "market_headroom": "MH", "demand_reach": "DR"}
idx = json.loads((HERE / "inputs-v4" / "_index.json").read_text())
by = {r["company"]: r for r in csv.DictReader(open(HERE / "sean-regrade-raw.csv"))}

def num(x):
    x = ("" if x is None else str(x)).strip()
    if x.lower() in ("n/a","na","","-","none","nan"): return None
    try: return float(x)
    except Exception: return None

def band_of(s):
    for nm, lo, hi in BANDS:
        if lo <= s <= hi: return nm
    return BANDS[0][0] if s < BANDS[0][1] else BANDS[-1][0]

def comp(vals):
    sc = [k for k in W if vals.get(k) is not None]
    if not sc: return None
    tot = sum(W[k] for k in sc)
    return round(sum(vals[k]/COUNTS[k]*(W[k]/tot*100) for k in sc))

recs = []
for cid, e in idx["companies"].items():
    if e["cat"] == "home-not-permitted": continue
    f = HERE/"runs-v18"/("jev-%s.json" % cid)
    if not f.exists(): continue
    run = json.loads(f.read_text()); mine = run.get("composite")
    if mine is None: continue
    hc = comp({d: num((by.get(e["name"]) or {}).get("YOUR_"+ABBR[d])) for d in W})
    if hc is None: continue
    recs.append({"mine": mine, "his": hc, "gap": mine-hc, "hb": band_of(hc), "mb": band_of(mine)})

print("=" * 92)
print("S10.7 DERIVED CLAIMS — re-verified on the harness formula")
print("=" * 92); print()
from collections import Counter
c = Counter(r["hb"] for r in recs)
print("  CLAIM: lowest band is a thin cell, extreme figures rest on n=3")
print("    his-band counts:", dict(c))
frag = [r for r in recs if r["hb"] == BANDS[0][0]]
print(f"    HIS Fragile n={len(frag)}   mean gap {sum(r['gap'] for r in frag)/len(frag):+.1f}")
print()
print("  CLAIM: -7.7 mean composite offset for businesses graded 80+")
hi = [r for r in recs if r["his"] >= 80]
if hi:
    print(f"    his composite >=80: n={len(hi)}   mean offset {sum(r['gap'] for r in hi)/len(hi):+.1f}")
else:
    print("    his composite >=80: n=0  (no case reaches 80 on the harness formula)")
hi2 = [r for r in recs if r["his"] >= 70]
print(f"    his composite >=70: n={len(hi2)}   mean offset {sum(r['gap'] for r in hi2)/len(hi2):+.1f}")
print()
print("  by band, mean offset (mine - his):")
ORDER=[b[0] for b in BANDS]
for b in ORDER:
    sub=[r for r in recs if r["hb"]==b]
    if sub: print(f"    {b:22} n={len(sub):3}  offset {sum(r['gap'] for r in sub)/len(sub):+6.1f}")
print()
gaps=[r["gap"] for r in recs]
print(f"  overall mean offset: {sum(gaps)/len(gaps):+.2f}   (harness reports +0.09 on levels)")
print("=" * 92)
