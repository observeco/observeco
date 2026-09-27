"""VERIFY the composite replication against the harness's OWN output.

THE INCONSISTENCY THAT FORCED THIS CHECK: on the target segment my dimension scores and
Sean's differ by a total of only +1.3 composite points (RS +0.53, MA +1.20, DEF -0.51,
CR +0.05, DR 0.00). Yet the observed composite gap is +10.7 points. Those cannot both be
true if I am computing the composite the way the scorer does.

If my replication is wrong, then EVERY composite finding rests on a bad function --
including the compression result (monotone +13.0 to -4.5) and the 96.5% band agreement.
Both would have to be withdrawn.

THE TEST: compute the composite from MY OWN stored dimension scores using my replication,
and compare with the composite the harness actually wrote to the run file. They must match.
If they do not, my replication is the thing that is wrong.
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
V = json.loads((HERE / "rubric-v1.8.0.json").read_text())
W = V["_meta"]["weights"]
COUNTS = {d: len(V["questions"][d]["levels"]) for d in W}
BAND_LIST = V["_meta"]["bands"]

idx = json.loads((HERE / "inputs-v4" / "_index.json").read_text())


def comp(vals, renorm=True):
    acc = tot = 0.0
    for d, v in vals.items():
        if v is None:
            continue
        acc += W[d] * ((v - 1) / (COUNTS[d] - 1)) * 100.0
        tot += W[d]
    if renorm:
        return acc / tot if tot else None
    return acc / sum(W.values())


print("=" * 94)
print("REPLICATION CHECK: comp(my dims) vs the composite the harness wrote")
print("=" * 94)
print()
print("  %-30s %9s %9s %9s %6s" % ("case", "harness", "mine(ren)", "mine(0wt)", "drops"))
bad = 0
tot = 0
worst = []
for cid, e in idx["companies"].items():
    f = HERE / "runs-v18" / ("jev-%s.json" % cid)
    if not f.exists():
        continue
    run = json.loads(f.read_text())
    stored = run.get("composite")
    disp = run.get("dimensions_display_1to5") or {}
    un = set(run.get("dimensions_unscored") or [])
    vals = {d: (None if d in un else disp.get(d)) for d in W}
    r1 = comp(vals, True)
    r0 = comp(vals, False)
    tot += 1
    d1 = abs((r1 or 0) - (stored or 0))
    if d1 > 0.51:
        bad += 1
        worst.append((d1, e["name"], stored, r1, r0, len(un)))
print()
print("  cases checked: %d" % tot)
print("  MATCH (<=0.5):  %d" % (tot - bad))
print("  MISMATCH:       %d" % bad)
print()
if worst:
    worst.sort(reverse=True)
    print("  worst mismatches:")
    print("  %-30s %9s %9s %9s %6s" % ("case", "harness", "mine(ren)", "mine(0wt)", "drops"))
    for d1, nm, s, r1, r0, k in worst[:15]:
        print("  %-30s %9.1f %9.1f %9.1f %6d" % (nm[:29], s or -1, r1 or -1, r0 or -1, k))
print()

# Show a few target-segment cases in full so the mechanism is visible
print("=" * 94)
print("FULL WORKING, six target-segment cases")
print("=" * 94)
print()
SHOW = ["My Skin Diary", "A home-based mobile hairdresser", "Get Nailed SG",
        "Crybaby SG", "Cellini", "The Bloomish Eden"]
for nm in SHOW:
    cid = next((c for c, e in idx["companies"].items() if e["name"] == nm), None)
    if not cid:
        continue
    run = json.loads((HERE / "runs-v18" / ("jev-%s.json" % cid)).read_text())
    disp = run.get("dimensions_display_1to5") or {}
    un = set(run.get("dimensions_unscored") or [])
    print("  %s" % nm)
    print("    stored composite: %s   band: %s" % (run.get("composite"), run.get("band")))
    print("    dropped: %s" % (sorted(un) or "none"))
    print("    my dims : %s" % {d[:3]: disp.get(d) for d in W})
    print("    comp(my dims) renorm=%.1f  no-redistribution=%.1f"
          % (comp({d: (None if d in un else disp.get(d)) for d in W}, True) or -1,
             comp({d: (None if d in un else disp.get(d)) for d in W}, False) or -1))
    print()
