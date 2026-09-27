"""Measure how much the CURRENT rubric discriminates WITHIN a competitive landscape.

The reframe says the composite should say "can this business successfully penetrate
its segment". If that is true, then within a single product category -- where the
occupants are known and their relative strength is observable -- the composite must
ORDER them sensibly and SPREAD them. This measures both.

Outputs, per category:
  - the ordering the rubric produces
  - the spread (max - min)
  - whether the spread is smaller than band noise (3.0) -> cannot tell them apart

Plus the outcome-labelled cases, where an external fact exists about whether
penetration actually succeeded.
"""
import glob
import json
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
NOISE = json.loads((HERE / "rubric.json").read_text())["_meta"]["band_noise"]

rows = []


def add(setname, cat, cid, name, case_id, extra=None):
    p = HERE / "runs" / ("jev-%s.json" % case_id)
    if not p.exists():
        return
    run = json.loads(p.read_text())
    rows.append(dict(set=setname, cat=cat, cid=cid, name=name,
                     score=run.get("composite"),
                     dims=run.get("dimensions_display_1to5") or {},
                     gates=run.get("gates_firing") or [], extra=extra or {}))


for dirn, setname in (("inputs-v2", "S2"), ("inputs-v3", "S3")):
    idx = json.loads((HERE / dirn / "_index.json").read_text())
    for cid in idx["companies"]:
        meta = json.loads((HERE / dirn / (cid + ".json")).read_text())
        ent = idx["companies"][cid]
        add(setname, str(ent.get("cat") or meta.get("_meta", {}).get("product_category") or "?"),
            cid, ent["name"], meta["_meta"]["case"], ent)

print("=" * 78)
print("PART 1 — does the composite DISCRIMINATE inside a known landscape?")
print("=" * 78)
cats = defaultdict(list)
for r in rows:
    cats[(r["set"], r["cat"])].append(r)

flat = []
for k in sorted(cats):
    grp = sorted(cats[k], key=lambda r: -(r["score"] or -1))
    ss = [r["score"] for r in grp if r["score"] is not None]
    if len(ss) < 2:
        continue
    spread = max(ss) - min(ss)
    flag = ""
    if spread < NOISE:
        flag = "  <-- SPREAD BELOW NOISE: cannot tell these apart"
        flat.append((k, spread))
    print()
    print("%s / %s   n=%d  spread=%d%s" % (k[0], k[1][:44], len(grp), spread, flag))
    for r in grp:
        sc = r["score"]
        tag = "GATE" if sc is None else str(sc)
        print("    %-22s %-34s %s" % (r["cid"], r["name"][:33], tag))

print()
print("=" * 78)
print("PART 2 — outcome labels: did penetration actually succeed?")
print("=" * 78)
print("(external facts: documented closure, documented growth out of the home,")
print(" published market position)")
print()
for r in sorted(rows, key=lambda r: (r["score"] is None, r["score"] or 0)):
    ex = r["extra"] or {}
    lab = str(ex.get("label") or "")
    if lab and lab not in ("—", "None", ""):
        sc = r["score"]
        print("  %-22s %-30s %-12s score=%s" % (
            r["cid"], r["name"][:29], lab[:11], "GATE" if sc is None else sc))
