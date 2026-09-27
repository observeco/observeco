"""Pull a worked example with all five dimensions scored, for a plain walkthrough.

Pick one home-based business (the actual lead-magnet use case) where every dimension
was scored, so the same business can be shown through all five lenses.
"""
import glob
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
DIMS = ["mental_advantage", "defensibility", "competitive_room",
        "market_headroom", "demand_reach"]

cands = []
for dirn, setname in (("inputs-v2", "S2"), ("inputs-v3", "S3"), ("inputs", "S1")):
    for p in sorted(glob.glob(str(HERE / dirn / "*.json"))):
        if p.endswith("_index.json"):
            continue
        try:
            s = json.loads(Path(p).read_text())
        except Exception:
            continue
        m = s.get("_meta", {})
        cid = m.get("case")
        if not cid:
            continue
        rp = HERE / "runs" / ("jev-%s.json" % cid)
        if not rp.exists():
            continue
        run = json.loads(rp.read_text())
        d = run.get("dimensions_display_1to5") or {}
        uns = set(run.get("dimensions_unscored") or [])
        scored = [k for k in DIMS if k not in uns and d.get(k) is not None]
        cands.append(dict(set=setname, cid=cid, dirn=dirn,
                          name=s.get("form", {}).get("business_name") or m.get("business") or cid,
                          cat=m.get("product_category") or "",
                          comp=run.get("composite"), dims=d, uns=uns, n=len(scored),
                          form=s.get("form", {}), meta=m,
                          comps=s.get("competitors_named") or []))

full = [c for c in cands if c["n"] == 5]
print("cases with ALL FIVE dimensions scored: %d of %d" % (len(full), len(cands)))
print()
print("=== candidates from the home-based set (the real use case) ===")
for c in full:
    if c["set"] == "S3":
        print("  %-22s %-34s comp=%-4s %s" % (
            c["cid"], c["name"][:33], c["comp"],
            {k[:3]: c["dims"][k] for k in DIMS}))
print()
print("=== and some from S2 ===")
for c in full:
    if c["set"] == "S2":
        print("  %-22s %-34s comp=%-4s %s" % (
            c["cid"], c["name"][:33], c["comp"],
            {k[:3]: c["dims"][k] for k in DIMS}))
