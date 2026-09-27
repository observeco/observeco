"""Which of his GRADED rows did not join to a v4 business?

If a graded case fails to join, his work is silently dropped from the regrade sheet.
List them so they can be fixed rather than lost.
"""
import csv
import json
import re
import unicodedata
from pathlib import Path

HERE = Path(__file__).resolve().parent


def norm(n):
    n = unicodedata.normalize("NFKD", str(n or ""))
    n = "".join(c for c in n if not unicodedata.combining(c))
    n = n.lower()
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


graded = []
for g in csv.DictReader(open(HERE / "sean-grades-raw.csv")):
    vals = {k: num(g.get("YOUR_" + k)) for k in ["MA", "DEF", "CR", "MH", "DR"]}
    if any(v is not None for v in vals.values()):
        graded.append((g["case_id"], g["company"], norm(g["company"]), g["set"]))

idx = json.loads((HERE / "inputs-v4" / "_index.json").read_text())
v4 = {cid: e for cid, e in idx["companies"].items()}
v4keys = {}
for cid, e in v4.items():
    v4keys.setdefault(norm(e["name"]), []).append(cid)

print("his graded rows: %d" % len(graded))
joined, unjoined = [], []
for cid, nm, k, st in graded:
    if k in v4keys:
        joined.append((cid, nm, v4keys[k]))
    else:
        unjoined.append((cid, nm, k, st))

print("joined to a v4 business : %d" % len(joined))
print("NOT joined              : %d" % len(unjoined))
print()
if unjoined:
    print("=== UNJOINED (his grades at risk of being dropped) ===")
    for cid, nm, k, st in unjoined:
        print("   %-26s %-34s [%s]  norm='%s'" % (cid, nm[:33], st[:14], k))
    print()
    print("Likely cause: the row is a DUPLICATE that dedup removed (its canonical twin")
    print("carries the grade), or its name differs from the v4 canonical name.")
