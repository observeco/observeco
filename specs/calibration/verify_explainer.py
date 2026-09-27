"""Verify every factual claim in DIMENSIONS-EXPLAINED.md against the files.
A document that explains the instrument must not itself be wrong.
"""
import glob
import json
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
DIMS = ["mental_advantage", "defensibility", "competitive_room",
        "market_headroom", "demand_reach"]
ok = []


def chk(label, got, want):
    good = got == want
    ok.append(good)
    print("  [%s] %-58s got=%s want=%s" % ("OK" if good else "FAIL", label, got, want))


R = json.loads((HERE / "rubric.json").read_text())
W = R["_meta"]["weights"]
print("=== weights (doc says 25/25/20/15/15) ===")
chk("weights", [W[k] for k in DIMS], [25, 25, 20, 15, 15])

print()
print("=== defensibility scale is 1-6 (doc says so) ===")
lv = R["questions"]["defensibility"].get("levels") or []
chk("defensibility levels", len(lv), 6)
chk("mental_advantage levels", len(R["questions"]["mental_advantage"].get("levels") or []), 5)

print()
print("=== market_headroom dropped in ~85% ===")
n = drop = 0
shown = Counter()
for p in glob.glob(str(HERE / "runs" / "jev-*.json")):
    r = json.loads(Path(p).read_text())
    d = r.get("dimensions_display_1to5") or {}
    if not d:
        continue
    n += 1
    uns = set(r.get("dimensions_unscored") or [])
    for k in DIMS:
        if k not in uns and d.get(k) is not None:
            shown[k] += 1
chk("runs counted", n, 133)
chk("market_headroom shown", shown["market_headroom"], 20)
print("     -> dropped %.0f%% of cases (doc says 85%%)" % (100 * (n - shown["market_headroom"]) / n))

print()
print("=== the four-dimension combination is 78% ===")
combos = Counter()
for p in glob.glob(str(HERE / "runs" / "jev-*.json")):
    r = json.loads(Path(p).read_text())
    d = r.get("dimensions_display_1to5") or {}
    if not d:
        continue
    uns = set(r.get("dimensions_unscored") or [])
    combos[tuple(sorted(k for k in DIMS if k not in uns and d.get(k) is not None))] += 1
top, cnt = combos.most_common(1)[0]
chk("most common combo size", len(top), 4)
print("     -> %.0f%% of cases (doc says 78%%)" % (100 * cnt / n))

print()
print("=== the two anchor cases ===")
for cid, nm, want in (("C5-michelin-hawker", "Tai Hwa", 5), ("GY07-true", "True Fitness", 1)):
    r = json.loads((HERE / "runs" / ("jev-%s.json" % cid)).read_text())
    d = r.get("dimensions_display_1to5") or {}
    chk("%s mental_advantage" % nm, d.get("mental_advantage"), want)

print()
print("=== McDonald's 47 vs Jollibee 57 ===")
for cid, want in (("FF01", 47), ("FF05", 57)):
    c = glob.glob(str(HERE / "runs" / ("jev-%s*.json" % cid)))
    r = json.loads(Path(c[0]).read_text())
    chk("%s composite" % cid, r.get("composite"), want)

print()
print("=== competitive_room variance share 19.2%, constant 11/17, order identical 9/15 ===")
import statistics
from collections import defaultdict
rows = []
for dirn in ("inputs-v2", "inputs-v3"):
    idx = json.loads((HERE / dirn / "_index.json").read_text())
    for cid in idx["companies"]:
        meta = json.loads((HERE / dirn / (cid + ".json")).read_text())["_meta"]
        pp = HERE / "runs" / ("jev-%s.json" % meta["case"])
        if not pp.exists():
            continue
        run = json.loads(pp.read_text())
        d = run.get("dimensions_display_1to5") or {}
        u = set(run.get("dimensions_unscored") or [])
        rows.append(dict(cat=idx["companies"][cid]["cat"], comp=run.get("composite"),
                         dims={k: (None if k in u else d.get(k)) for k in DIMS}))
cats = defaultdict(list)
for r in rows:
    cats[r["cat"]].append(r)
k = "competitive_room"
allv = [r["dims"][k] for r in rows if r["dims"][k] is not None]
gm = statistics.mean(allv)
sst = sum((v - gm) ** 2 for v in allv)
ssw = 0
const = nc = 0
for c, g in cats.items():
    vs = [r["dims"][k] for r in g if r["dims"][k] is not None]
    if len(vs) < 2:
        continue
    nc += 1
    if statistics.stdev(vs) == 0:
        const += 1
    m = statistics.mean(vs)
    ssw += sum((v - m) ** 2 for v in vs)
print("  [%s] within-share %.1f%% (doc says 19.2%%)" %
      ("OK" if abs(100 * ssw / sst - 19.2) < 0.3 else "FAIL", 100 * ssw / sst))
print("  [%s] constant in %d/%d (doc says 11/17)" %
      ("OK" if (const, nc) == (11, 17) else "FAIL", const, nc))
print()
print("=" * 66)
print("ALL CHECKS: %d/%d passed" % (sum(ok), len(ok)))
