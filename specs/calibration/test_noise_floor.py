"""THE NOISE CONTROL — is the v1.2 -> v1.6 improvement real, or run-to-run variance?

THE PROBLEM WITH EVERYTHING I HAVE REPORTED: I measured each version against ITSELF. If
re-running the SAME rubric produces different scores, then a movement of 1-3 disputes
between versions may be nothing but noise, and "disputes improved 8.5% -> 4.7%" could be an
artefact of having drawn one lucky sample at the end.

THE TEST: I have two runs of the SAME rubric v1.6.0 (runs-v16 and runs-v16b). Measure the
noise floor first, then ask whether the between-version movement exceeds it.

This is the determinism question that matters: a rubric whose own scores move on re-run
cannot be tuned by 1-point adjustments at all.
"""
import csv
import json
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
DIMS = ["relative_strength", "mental_advantage", "defensibility",
        "competitive_room", "market_headroom", "demand_reach"]
ABBR = {"relative_strength": "RS", "mental_advantage": "MA", "defensibility": "DEF",
        "competitive_room": "CR", "market_headroom": "MH", "demand_reach": "DR"}


def num(x):
    x = ("" if x is None else str(x)).strip()
    if x.lower() in ("n/a", "na", "", "-", "none", "nan"):
        return None
    try:
        return float(x)
    except Exception:
        return None


def load(rd):
    out = {}
    for p in (HERE / rd).glob("jev-*.json"):
        r = json.loads(p.read_text())
        disp = r.get("dimensions_display_1to5") or {}
        un = set(r.get("dimensions_unscored") or [])
        out[r["case"]] = {k: (None if k in un else disp.get(k)) for k in DIMS}
    return out


idx = json.loads((HERE / "inputs-v4" / "_index.json").read_text())
rows = list(csv.DictReader(open(HERE / "sean-regrade-raw.csv")))
by = {r["company"]: r for r in rows}
CLOSED = {"competitive_room"}


def alignment(run):
    tot_n = tot_ex = tot_disp = 0
    offs = []
    for d in DIMS:
        if d in CLOSED:
            continue
        pairs = []
        for cid, e in idx["companies"].items():
            m = (run.get(cid) or {}).get(d)
            h = num((by.get(e["name"]) or {}).get("YOUR_" + ABBR[d]))
            if m is not None and h is not None:
                pairs.append((m, h))
        n = len(pairs)
        if n < 3:
            continue
        tot_n += n
        tot_ex += sum(1 for a, b in pairs if a == b)
        tot_disp += sum(1 for a, b in pairs if abs(b - a) >= 2)
        offs.append(sum(b - a for a, b in pairs) / n)
    return (100 * tot_ex / tot_n, 100 * tot_disp / tot_n,
            sum(offs) / len(offs), tot_disp)


print("=" * 88)
print("1. THE NOISE FLOOR — same rubric v1.6.0, two independent runs")
print("=" * 88)
print()
a, b = load("runs-v16"), load("runs-v16b")
n_cells = n_diff = 0
diffs = Counter()
for cid in set(a) & set(b):
    for d in DIMS:
        x, y = a[cid].get(d), b[cid].get(d)
        n_cells += 1
        if x != y:
            n_diff += 1
            diffs[y - x if (x is not None and y is not None) else "n/a"] += 1
print("  cells compared: %d" % n_cells)
print("  cells that CHANGED between two runs of the SAME rubric: %d (%.1f%%)"
      % (n_diff, 100 * n_diff / n_cells))
print("  direction of change: %s" % dict(diffs))
print()
e1 = alignment(a)
e2 = alignment(b)
print("  alignment, run A: exact %.1f%%  disputes %.1f%%  offset %+.2f  (%d disputes)"
      % e1)
print("  alignment, run B: exact %.1f%%  disputes %.1f%%  offset %+.2f  (%d disputes)"
      % e2)
print()
print("  >>> NOISE FLOOR: exact +/-%.1f pts, disputes +/-%.1f pts, %d dispute cases"
      % (abs(e1[0] - e2[0]), abs(e1[1] - e2[1]), abs(e1[3] - e2[3])))
print()

print("=" * 88)
print("2. IS THE v1.2.0 -> v1.6.0 MOVEMENT ABOVE THE NOISE FLOOR?")
print("=" * 88)
print()
traj = [("v1.2.0", "runs-v12"), ("v1.3.2", "runs-v132"), ("v1.4.1", "runs-v141"),
        ("v1.5.0", "runs-v15"), ("v1.6.0", "runs-v16")]
print("  %-9s %9s %10s %9s %s" % ("version", "exact", "disputes", "offset", "disputes(c)"))
rowsout = []
for name, rd in traj:
    try:
        r = alignment(load(rd))
        rowsout.append((name, r))
        print("  %-9s %8.1f%% %9.1f%% %+8.2f %6d" % (name, r[0], r[1], r[2], r[3]))
    except Exception as ex:
        print("  %-9s (missing: %s)" % (name, ex))
print()
if rowsout:
    first, last = rowsout[0][1], rowsout[-1][1]
    print("  total movement v1.2.0 -> v1.6.0:")
    print("    exact     %+.1f pts   (noise floor +/-%.1f)"
          % (last[0] - first[0], abs(e1[0] - e2[0])))
    print("    disputes  %+.1f pts   (noise floor +/-%.1f)"
          % (last[1] - first[1], abs(e1[1] - e2[1])))
    print("    dispute cases %+d      (noise floor +/-%d)"
          % (last[3] - first[3], abs(e1[3] - e2[3])))
    print()
    dsig = abs(last[1] - first[1]) > abs(e1[1] - e2[1])
    esig = abs(last[0] - first[0]) > abs(e1[0] - e2[0])
    print("    disputes improvement is %s the noise floor"
          % ("ABOVE" if dsig else "WITHIN"))
    print("    exact change is %s the noise floor" % ("ABOVE" if esig else "WITHIN"))
print()

print("=" * 88)
print("3. WHAT THE NOISE MEANS")
print("=" * 88)
print()
print("  If the noise floor is comparable to the between-version movement, then the")
print("  entire v1.2 -> v1.6 'improvement' may be sampling, and 1-point rubric tuning")
print("  cannot be validated on this corpus at all. The honest response then is not")
print("  another version -- it is to state the measurement limit.")
