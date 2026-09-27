"""Robust duplicate detection across the v4 corpus.

Found a miss: 'KOI Thé Singapore' and 'KOI The Singapore' normalise differently because
\bthe\b does not match the accented form, so the pair survived dedup. Fix: strip accents
(unicodedata) and use a similarity check on top of exact normalised equality, so near
misses surface for review rather than silently passing.

Reports:
  A. exact normalised duplicates (must be zero)
  B. near-duplicates by token similarity (for judgement)
"""
import difflib
import glob
import json
import re
import unicodedata
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
STOP = {"singapore", "sg", "pte", "ltd", "group", "the", "co", "inc", "llc"}


def norm(name):
    # strip accents FIRST so 'The'/'Thé' collapse together
    n = unicodedata.normalize("NFKD", str(name or ""))
    n = "".join(c for c in n if not unicodedata.combining(c))
    n = n.lower()
    n = re.sub(r"[^a-z0-9]+", " ", n)
    return " ".join(t for t in n.split() if t not in STOP)


idx = json.loads((HERE / "inputs-v4" / "_index.json").read_text())
names = {cid: e["name"] for cid, e in idx["companies"].items()}
print("cases in v4: %d" % len(names))

# ---- A. exact normalised duplicates -----------------------------------------
groups = defaultdict(list)
for cid, nm in names.items():
    groups[norm(nm)].append((cid, nm))

exact = {k: v for k, v in groups.items() if len(v) > 1}
print()
print("A. EXACT normalised duplicates: %d" % len(exact))
for k, v in sorted(exact.items()):
    print("   '%s'" % k)
    for cid, nm in v:
        print("      %-24s %s" % (cid, nm))

# ---- B. near-duplicates ------------------------------------------------------
keys = sorted(groups.keys())
print()
print("B. NEAR-duplicates (token similarity >= 0.82), for review:")
seen = set()
found = 0
for i, a in enumerate(keys):
    for b in keys[i + 1:]:
        if not a or not b:
            continue
        r = difflib.SequenceMatcher(None, a, b).ratio()
        if r >= 0.82:
            found += 1
            print("   %.2f  '%s'  ~  '%s'" % (r, a, b))
            for cid, nm in groups[a]:
                print("            A: %-22s %s" % (cid, nm))
            for cid, nm in groups[b]:
                print("            B: %-22s %s" % (cid, nm))
if not found:
    print("   none")
print()
print("=> %d exact duplicates, %d near-duplicate pairs to judge."
      % (len(exact), found))
