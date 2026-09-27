"""Diagnose: why does the v4 manifest say n=121 but contain only 118 companies?

Hypothesis: two different businesses share a `stem` (the source filename without .json),
so writing `manifest["companies"][stem]` and `out/(stem + ".json")` overwrote one with the
other. This is the same class of bug as the earlier `HB01` collision -- an identifier that
is unique within a set but NOT across sets.
"""
import glob
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent


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
            e = idx["companies"].get(Path(p).stem) or {}
            nm, cat = e.get("name"), e.get("cat")
        else:
            nm, cat = (f.get("business_name") or m.get("business") or cid), None
        entries.append(dict(set=setname, dirn=dirn, stem=Path(p).stem, cid=cid,
                            name=nm or cid, nkey=norm(nm or cid)))

groups = defaultdict(list)
for e in entries:
    groups[e["nkey"]].append(e)

canonical = []
for k in sorted(groups):
    v = groups[k]
    canonical.append(v[0] if len(v) == 1 else v[0])

print("distinct businesses (canonical count): %d" % len(canonical))

stemc = Counter(e["stem"] for e in canonical)
dupes = {k: v for k, v in stemc.items() if v > 1}
print("STEM collisions among canonical entries: %d" % len(dupes))
for k, v in sorted(dupes.items()):
    print()
    print("  stem '%s' used by %d DIFFERENT businesses:" % (k, v))
    for e in canonical:
        if e["stem"] == k:
            print("     %-4s %-24s %-30s %s" % (e["set"], e["dirn"] + "/" + e["stem"],
                                                e["name"][:29], e["cid"]))

print()
print("=> every canonical entry must key on (SET, STEM), not STEM alone, or entries")
print("   silently overwrite each other in both the manifest and the case files.")
