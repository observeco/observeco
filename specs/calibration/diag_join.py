"""Debug: why does the regrade sheet claim all 120 rows have his old grades?
He only graded ~56. A bad join would silently attach the wrong grades to rows.
"""
import csv
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent


def norm(n):
    n = (n or "").lower()
    n = re.sub(r"\b(singapore|sg|pte|ltd|group|the)\b", " ", n)
    return " ".join(re.sub(r"[^a-z0-9]+", " ", n).split())


def num(x):
    x = (x or "").strip()
    if x.lower() in ("n/a", "na", "n.a.", "n.a", "-", ""):
        return None
    try:
        return float(x)
    except Exception:
        return None


gp = HERE / "sean-grades-raw.csv"
print("file exists: %s" % gp.exists())
rows = list(csv.DictReader(open(gp)))
print("raw csv rows: %d" % len(rows))

withvals = 0
his = {}
for g in rows:
    vals = {k: num(g.get("YOUR_" + k)) for k in
            ["MA", "DEF", "CR", "MH", "DR"]}
    vals["SCORE"] = num(g.get("YOUR_SCORE"))
    vals["BAND"] = (g.get("YOUR_BAND") or "").strip()
    if any(v is not None for v in vals.values()):
        withvals += 1
        his.setdefault(norm(g["company"]), []).append(vals)
print("rows with any value: %d" % withvals)
print("distinct normalised company keys: %d" % len(his))
print()
empt = [k for k in his if not k]
print("EMPTY normalised keys: %d" % len(empt))
if empt:
    print("  <- these collapse together; any name normalising to '' would match all of them")
print()
# how many v4 names normalise to ''?
idx = json.loads((HERE / "inputs-v4" / "_index.json").read_text())
hits = 0
for cid, e in idx["companies"].items():
    k = norm(e["name"])
    if k in his:
        hits += 1
print("v4 names that MATCH a his key: %d of %d" % (hits, len(idx["companies"])))
print()
print("sample his keys:", sorted(his)[:8])
print()
print("v4 names normalised:", [(e["name"], norm(e["name"])) for cid, e
                              in list(idx["companies"].items())[:6]])
