"""Diagnostic: why does grading-sheet.csv have fewer rows than GRADING-SHEET.md?

Independent rebuild of what the CSV SHOULD contain, compared against what it has.
"""
import csv
import glob
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent

want = []
for p in sorted(glob.glob(str(HERE / "inputs" / "*.json"))):
    m = json.loads(Path(p).read_text()).get("_meta", {})
    if m.get("case") and (HERE / "runs" / ("jev-%s.json" % m["case"])).exists():
        want.append(("S1 original corpus", m["case"]))

for dirn, setname in (("inputs-v2", "S2 55-company cross-category"),
                      ("inputs-v3", "S3 52 home-based business")):
    for cid in json.loads((HERE / dirn / "_index.json").read_text())["companies"]:
        m = json.loads((HERE / dirn / (cid + ".json")).read_text())["_meta"]
        if (HERE / "runs" / ("jev-%s.json" % m["case"])).exists():
            want.append((setname, m["case"]))

have = [(r["set"], r["case_id"]) for r in csv.DictReader(
    open(HERE / "grading-sheet.csv", newline=""))]

ws, hs = set(want), set(have)
print("want (unique): %d   have (unique): %d" % (len(ws), len(hs)))
missing = ws - hs
extra = hs - ws
print()
print("MISSING from csv: %d" % len(missing))
for s, c in sorted(missing):
    print("   %-32s %s" % (s, c))
print()
print("EXTRA in csv (not expected): %d" % len(extra))
for s, c in sorted(extra):
    print("   %-32s %s" % (s, c))
print()
# duplicates within the csv?
dupes = [x for x in set(have) if have.count(x) > 1]
print("duplicate (set,case) rows in csv: %s" % (dupes or "none"))
