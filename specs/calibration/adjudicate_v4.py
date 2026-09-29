"""Adjudicate the v1.0.0 (six-dimension) corpus.

1. Re-derive band edges from the level-mean convention under the NEW weights.
2. Verify the McDonald's/Jollibee inversion is fixed.
3. Check position_strength separates rivals within a landscape (the whole point).
4. Check the other known labels still hold.
"""
import glob
import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
V1 = json.loads((HERE / "rubric-v1.0.0.json").read_text())
W, META = V1["_meta"]["weights"], V1["_meta"]
DIMS = ["relative_strength", "mental_advantage", "defensibility",
        "competitive_room", "market_headroom", "demand_reach"]
COUNTS = {"defensibility": 6}   # 6-level; others 5-level

rows = []
for p in glob.glob(str(HERE / "runs-v4" / "jev-*.json")):
    r = json.loads(Path(p).read_text())
    d = r.get("dimensions_display_1to5") or {}
    u = set(r.get("dimensions_unscored") or [])
    rows.append(dict(case=r.get("case"), comp=r.get("composite"),
                     band=r.get("band"), dims={k: (None if k in u else d.get(k))
                                               for k in DIMS},
                     gates=r.get("gates_firing") or []))
print("runs: %d  scored: %d  refused: %d"
      % (len(rows), len([r for r in rows if r["comp"] is not None]),
         len([r for r in rows if r["comp"] is None])))

print()
print("=" * 80)
print("1. BAND EDGES RE-DERIVED for six dimensions")
print("=" * 80)
print()
print("The edges are where a case sits when every dimension is at level N.")
print("composite = 19.1667 x (weighted mean of display values)")
for n in (2, 3, 4):
    num = sum(min(n, COUNTS.get(k, 5)) * W[k] for k in DIMS)
    den = sum(W[min(n, COUNTS.get(k, 5))] if False else W[k] for k in DIMS)
    m = num / den
    print("   all-%d -> %.2f" % (n, 19.1667 * m))
print()
print("=> same level-mean convention as before, so the SAME band edges hold:")
print("   Fragile 5-37 | Contested 38-57 | Viable, conditional 58-76 | Strong 77-100")
print("   (the scaling constant and level means are unchanged; only the weights moved,")
print("    and weights cancel in the all-N case)")
print()
print("Observed distribution under v1.0.0:")
b = Counter(r["band"] for r in rows if r["band"])
for k, v in b.most_common():
    print("   %-22s %d" % (k, v))

print()
print("=" * 80)
print("2. THE MCDONALD'S / JOLLIBEE INVERSION")
print("=" * 80)
print()
for cid, nm in (("FF01-mcdonalds", "McDonald's SG (150+ outlets, market leader)"),
                ("FF05-jollibee", "Jollibee SG (26 outlets)")):
    p = HERE / "runs-v4" / ("jev-%s.json" % cid)
    if not p.exists():
        print("   %-46s (no run)" % nm)
        continue
    r = json.loads(p.read_text())
    d = r.get("dimensions_display_1to5") or {}
    u = set(r.get("dimensions_unscored") or [])
    oldp = HERE / "runs" / ("jev-%s.json" % cid)
    old = json.loads(oldp.read_text()).get("composite") if oldp.exists() else None
    print("   %-46s RS=%s MA=%s DEF=%s  ->  %s   (old 0.9.0: %s)"
          % (nm, d.get("relative_strength"), d.get("mental_advantage"),
             d.get("defensibility"), r.get("composite"), old))

print()
print("=" * 80)
print("3. DOES relative_strength SEPARATE RIVALS IN ONE LANDSCAPE?")
print("=" * 80)
print("(this is the axis that was missing; competitive_room had 19% within-category")
print(" variance share and could not reorder a category)")
print()
idx = json.loads((HERE / "inputs-v4" / "_index.json").read_text())
bycat = defaultdict(list)
for r in rows:
    e = idx["companies"].get(r["case"]) or {}
    if e:
        bycat[e["cat"]].append((e["name"], r))
for k in ("relative_strength", "competitive_room"):
    from collections import defaultdict as dd
    cats = dd(list)
    for r in rows:
        e = idx["companies"].get(r["case"]) or {}
        if e:
            cats[e["cat"]].append(r)
    allv = [r["dims"][k] for r in rows if r["dims"][k] is not None]
    if len(allv) < 5:
        print("   %-18s (too few scored: %d)" % (k, len(allv)))
        continue
    gm = statistics.mean(allv)
    sst = sum((v - gm) ** 2 for v in allv)
    ssw = 0
    const = nc = 0
    for c, g in cats.items():
        vs = [x["dims"][k] for x in g if x["dims"][k] is not None]
        if len(vs) < 2:
            continue
        nc += 1
        if statistics.stdev(vs) == 0:
            const += 1
        m = statistics.mean(vs)
        ssw += sum((v - m) ** 2 for v in vs)
    print("   %-18s within-category variance share %.1f%%   constant in %d/%d categories"
          % (k, 100 * ssw / sst if sst else 0, const, nc))
print()
print("  per-category relative_strength, the new dimension:")
for c in sorted(bycat):
    vs = [(nm, r["dims"]["relative_strength"]) for nm, r in bycat[c]
          if r["dims"]["relative_strength"] is not None]
    if len(vs) >= 2:
        print("   %-16s %s" % (c, vs))

print()
print("=" * 80)
print("4. KNOWN LABELS STILL HOLD?")
print("=" * 80)
print()
known = [("GY07-true", "True Fitness (documented death)", "low"),
         ("N1-closedbusiness", "closed bubble tea outlet", "low"),
         ("P5-gongcha", "Gong Cha (29 outlets shut 2025)", "low"),
         ("E1-asml", "ASML (monopoly)", "high"),
         ("koi", "KOI (88-90 outlets, leader)", "high"),
         ("C5-michelin-hawker", "Tai Hwa (Michelin star)", "high")]
for cid, label, expect in known:
    p = HERE / "runs-v4" / ("jev-%s.json" % cid)
    if not p.exists():
        print("   %-38s (no run)" % label)
        continue
    r = json.loads(p.read_text())
    print("   %-38s %-6s %-22s [expected %s]"
          % (label, r.get("composite") or "GATE", r.get("band") or "", expect))
