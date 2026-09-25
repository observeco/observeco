"""Recompute all composites under the FIXED mapping, and check ASML reaches level 6.

The 0.5.0 migration split defensibility to 6 levels but run_jev.py still mapped the raw score
with `int(round(s))+1`, which always yields 1..5. Consequences:
  * level 6 was UNREACHABLE -- a monopolist could never display 'Compounding'
  * dims/counts for defensibility maxed at 5/6, understating its weight
This recomputes every stored run from its raw scores under the corrected mapping.
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
R = json.loads((HERE / "rubric.json").read_text())
M = R["_meta"]
W, COUNTS, BANDS = M["weights"], M["level_counts"], M["bands"]
FLOORS = {k: v for k, v in M["gates"].items() if not k.startswith("_")}
FLOOR = M.get("display_floor", 0.20)


def band_of(c):
    for name, lo, hi in BANDS:
        if lo <= c <= hi:
            return name
    raise SystemExit(f"composite {c} outside bands")


def old_map(s):
    return max(1, min(5, int(round(s)) + 1))


def new_map(s, n):
    return max(1, min(n, int(round(s / 4 * (n - 1))) + 1))


print("=" * 88)
print("RECOMPUTED COMPOSITES UNDER THE FIXED 1..N MAPPING")
print("=" * 88)
print(f"  {'case':22}{'raw DEF':>8}{'old':>5}{'new':>5}{'old comp':>10}{'new comp':>10}"
      f"{'new band':>20}")
print("  " + "-" * 84)
rows = []
for f in sorted((HERE / "runs").glob("jev-*.json")):
    x = json.loads(f.read_text())
    raw = {k: v for k, v in (x.get("raw_jev_scores_0to4") or {}).items() if v is not None}
    cov = x.get("evidence_coverage") or {}
    if not raw:
        continue
    unscored = [k for k in W
                if not isinstance(cov.get(k), (int, float)) or cov[k] < FLOOR]
    scored = [k for k in W if k not in unscored and k in raw]
    tw = sum(W[k] for k in scored)
    wu = {k: W[k] / tw * 100 for k in scored}
    d_old = {k: old_map(raw[k]) for k in raw}
    d_new = {k: new_map(raw[k], COUNTS[k]) for k in raw}
    fires_old = [k for k in scored if d_old[k] < FLOORS[k]]
    fires_new = [k for k in scored if d_new[k] < FLOORS[k]]
    c_old = None if fires_old else round(sum(d_old[k] / COUNTS[k] * wu[k] for k in scored))
    c_new = None if fires_new else round(sum(d_new[k] / COUNTS[k] * wu[k] for k in scored))
    b_new = "GATE" if c_new is None else band_of(c_new)
    rows.append((x["case"], raw.get("defensibility"), d_old.get("defensibility"),
                 d_new.get("defensibility"), c_old, c_new, b_new))
    print(f"  {x['case']:22}{raw.get('defensibility',0):>8.2f}"
          f"{d_old.get('defensibility'):>5}{d_new.get('defensibility'):>5}"
          f"{str(c_old):>10}{str(c_new):>10}{b_new:>20}")

print()
print("  DEFENSIBILITY NOW REACHES LEVEL 6 (previously impossible):")
for c, r, o, n, co, cn, b in rows:
    if n >= 6:
        print(f"    {c}: raw {r:.2f} -> level {n}/6  ({b})")

print()
print("  WHERE THE MAPPING CHANGED THE VERDICT:")
ch = [(c, co, cn, b) for c, r, o, n, co, cn, b in rows if co != cn]
if ch:
    for c, co, cn, b in ch:
        print(f"    {c:22} {co} -> {cn}  ({b})")
else:
    print("    none")

# ---------------------------------------------------------------- full ladder
print()
print("=" * 88)
print("LADDER UNDER THE FIXED MAPPING")
print("=" * 88)
for c, r, o, n, co, cn, b in sorted(rows, key=lambda t: -(t[5] or 0)):
    cs = "GATE" if cn is None else str(cn)
    print(f"  {cs:>5}  {b:22}{c}")
