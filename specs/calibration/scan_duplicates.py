"""Inventory DUPLICATE companies across the three corpus sets.

Sean: "there are many duplicate entries for the same companies. I would actually grade
them the same. Suggest we remove duplicates."

Normalises names and finds businesses appearing more than once, so the rebuild keeps one
canonical entry per business. Reports where the duplicates DISAGREE, because a duplicate
that scored differently is also a repeatability datapoint.
"""
import glob
import json
import re
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
DIMS = ["mental_advantage", "defensibility", "competitive_room",
        "market_headroom", "demand_reach"]


def norm(name):
    n = (name or "").lower()
    n = re.sub(r"\b(singapore|sg|pte|ltd|group|the)\b", " ", n)
    n = re.sub(r"[^a-z0-9]+", " ", n)
    return " ".join(n.split())


entries = []
for dirn, setname in (("inputs", "S1"), ("inputs-v2", "S2"), ("inputs-v3", "S3")):
    idx_p = HERE / dirn / "_index.json"
    idx = json.loads(idx_p.read_text()) if idx_p.exists() else None
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
        f = s.get("form", {})
        if idx:
            key = Path(p).stem
            nm = (idx["companies"].get(key) or {}).get("name")
            cat = (idx["companies"].get(key) or {}).get("cat")
        else:
            nm = f.get("business_name") or m.get("business") or cid
            cat = m.get("product_category") or m.get("category")
        rp = HERE / "runs" / ("jev-%s.json" % cid)
        run = json.loads(rp.read_text()) if rp.exists() else {}
        d = run.get("dimensions_display_1to5") or {}
        u = set(run.get("dimensions_unscored") or [])
        entries.append(dict(
            set=setname, dirn=dirn, cid=cid, key=Path(p).stem, name=nm or cid,
            nkey=norm(nm or cid), cat=cat, comp=run.get("composite"),
            dims={k: (None if k in u else d.get(k)) for k in DIMS},
            gate=run.get("gates_firing") or [], path=str(p)))

groups = defaultdict(list)
for e in entries:
    groups[e["nkey"]].append(e)

dups = {k: v for k, v in groups.items() if len(v) > 1}
print("=" * 84)
print("DUPLICATE BUSINESSES ACROSS THE CORPUS")
print("=" * 84)
print()
print("total case entries : %d" % len(entries))
print("distinct businesses: %d" % len(groups))
print("businesses appearing more than once: %d  (extra entries: %d)"
      % (len(dups), sum(len(v) - 1 for v in dups.values())))
print()
for k in sorted(dups):
    v = dups[k]
    print("-" * 84)
    print("  %s   (%d entries)" % (v[0]["name"], len(v)))
    for e in sorted(v, key=lambda x: x["set"]):
        c = "GATE" if e["comp"] is None else e["comp"]
        print("     %-4s %-22s %-24s comp=%-5s %s" % (
            e["set"], e["dirn"] + "/" + e["key"], e["cid"], c,
            {kk[:3]: e["dims"][kk] for kk in DIMS if e["dims"][kk] is not None}))
    # do the duplicates agree?
    comps = [e["comp"] for e in v if e["comp"] is not None]
    if len(set(comps)) > 1:
        print("     ** SAME BUSINESS, DIFFERENT SCORES: %s **" % sorted(comps))
    dimsets = [tuple(e["dims"][kk] for kk in DIMS) for e in v
               if any(e["dims"][kk] is not None for kk in DIMS)]
    if len(set(dimsets)) > 1:
        print("     ** dimension vectors differ **")
print()
print("=" * 84)
print("CANONICAL SET SIZE AFTER DEDUP")
print("=" * 84)
print()
print("  %d businesses -> %d unique" % (len(entries), len(groups)))
bycat = defaultdict(int)
for k, v in groups.items():
    bycat[v[0]["cat"] or "?"] += 1
for c in sorted(bycat, key=lambda x: -bycat[x]):
    print("     %-22s %d" % (c, bycat[c]))
