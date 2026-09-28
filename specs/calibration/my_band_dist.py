"""my_band_dist.py — my own band distribution, harness formula."""
import csv, json
from pathlib import Path
from collections import Counter
HERE = Path(__file__).resolve().parent
V = json.loads((HERE/"rubric-v1.8.0.json").read_text())
BANDS = V["_meta"]["bands"]
idx = json.loads((HERE/"inputs-v4"/"_index.json").read_text())
def band_of(s):
    for nm, lo, hi in BANDS:
        if lo <= s <= hi: return nm
    return BANDS[0][0] if s < BANDS[0][1] else BANDS[-1][0]
mine=[]
for cid, e in idx["companies"].items():
    if e["cat"]=="home-not-permitted": continue
    f = HERE/"runs-v18"/("jev-%s.json" % cid)
    if not f.exists(): continue
    r=json.loads(f.read_text())
    if r.get("composite") is None: continue
    mine.append(band_of(r["composite"]))
print("MY band distribution (n=%d):" % len(mine))
for b in [x[0] for x in BANDS]:
    print(f"   {b:22} {mine.count(b):3}")
