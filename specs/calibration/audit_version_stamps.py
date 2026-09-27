"""AUDIT the version-stamp chain across every rubric and every run directory.

WHY THIS MATTERS: run_jev.py stamps each run file with `_meta.version` and the harness
REFUSES a mixed-version run ("** FATAL: mixed rubric versions **"). My build scripts set
the top-level `version` but NOT `_meta.version`. If that is true across versions, then:
  - every run carries a STALE stamp;
  - the mixed-version guard is DEFEATED (two different rubrics stamp the same number);
  - any comparison made on the strength of the stamp is unsound.

The scores themselves come from the level text, so the runs may still be valid -- but I
must know exactly which rubric each run directory actually used before believing any result.
"""
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent

print("=" * 88)
print("1. RUBRIC FILES — declared version vs _meta.version")
print("=" * 88)
print()
print("  %-26s %-12s %-14s %s" % ("file", "top-level", "_meta.version", "verdict"))
rubrics = {}
for p in sorted(HERE.glob("rubric*.json")):
    v = json.loads(p.read_text())
    top = v.get("version")
    meta = (v.get("_meta") or {}).get("version")
    ok = "OK" if top == meta else "*** MISMATCH ***"
    rubrics[p.name] = (top, meta)
    print("  %-26s %-12s %-14s %s" % (p.name, top, meta, ok))

print()
print("=" * 88)
print("2. RUN DIRECTORIES — what stamp did each run write?")
print("=" * 88)
print()
print("  %-14s %-18s %-8s %s" % ("dir", "stamped version", "files", "note"))
for d in sorted(HERE.glob("runs*")):
    if not d.is_dir():
        continue
    stamps = {}
    for f in d.glob("jev-*.json"):
        try:
            s = json.loads(f.read_text()).get("rubric_version")
        except Exception:
            s = "?"
        stamps[s] = stamps.get(s, 0) + 1
    note = ""
    if len(stamps) > 1:
        note = "*** MIXED — guard did not fire ***"
    print("  %-14s %-18s %-8d %s"
          % (d.name, ", ".join("%s(%d)" % (k, v) for k, v in sorted(stamps.items())),
             sum(stamps.values()), note))

print()
print("=" * 88)
print("3. THE CRITICAL TEST — do the FILES actually differ where the stamps agree?")
print("=" * 88)
print()
print("  If two run dirs stamp the SAME version but were built from DIFFERENT rubric")
print("  files, the stamp is worthless and the run content is the only evidence.")
print()


def dr_level2(fname):
    try:
        v = json.loads((HERE / fname).read_text())
        return " ".join(v["questions"]["demand_reach"]["levels"][1].split())
    except Exception as e:
        return "ERR %s" % e


for fname in sorted(rubrics):
    t = dr_level2(fname)
    fixed = "CORROBORATION FLOOR" if "at least 3" in t else "old wording"
    print("  %-26s stamps %-9s  DR level2: %s" % (fname, rubrics[fname][1], fixed))

print()
print("  Cross-check: does runs-v13 content actually reflect the v1.3.0 fix?")
print()
import glob
n_fixed = 0
tot = 0
for f in HERE.glob("runs-v13/jev-*.json"):
    r = json.loads(f.read_text())
    disp = r.get("dimensions_display_1to5") or {}
    dr = disp.get("demand_reach")
    tot += 1
    if dr is not None and dr >= 3:
        n_fixed += 1
print("    runs-v13: %d/%d cells with DR >= 3" % (n_fixed, tot))
n_fixed12 = 0
tot12 = 0
for f in HERE.glob("runs-v12/jev-*.json"):
    r = json.loads(f.read_text())
    disp = r.get("dimensions_display_1to5") or {}
    dr = disp.get("demand_reach")
    tot12 += 1
    if dr is not None and dr >= 3:
        n_fixed12 += 1
print("    runs-v12: %d/%d cells with DR >= 3" % (n_fixed12, tot12))
print()
print("    -> runs-v13 should have visibly MORE cells at >=3 if the fix applied.")
