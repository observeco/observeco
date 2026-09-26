"""Blast-radius: is the floor compression specific to market_headroom, or systemic?

If EVERY dimension has mass piled low, the issue is the model's distributional
prior, not the anchors. If only market_headroom is compressed, it is the anchors.
Those two diagnoses have different fixes, so this separates them.
"""
import json, glob
BASE = "/Users/seanfzc/projects/observeco-main/specs/calibration"
rub = json.load(open(f"{BASE}/rubric.json"))
meta = rub["_meta"]
DIMS = list(meta["weights"])
counts = meta.get("level_counts") or {}

rows = []
for p in sorted(glob.glob(f"{BASE}/runs/jev-*.json")):
    d = json.load(open(p))
    if d.get("case"):
        rows.append(d)

print("=" * 104)
print("PER-DIMENSION MASS DISTRIBUTION  (n=%d cases)" % len(rows))
print("=" * 104)
print("%-18s %-7s %6s | %s" % ("dimension", "levels", "raw mn", "mean probability per level (normalised)"))
print("-" * 104)

for dim in DIMS:
    n = counts.get(dim, 5)
    raw = [d["raw_jev_scores_0to4"].get(dim) for d in rows
           if d.get("raw_jev_scores_0to4", {}).get(dim) is not None]
    # accumulate mean mass per level, normalising each case's vector to sum to 1
    acc = {i: 0.0 for i in range(n)}
    k = 0
    for d in rows:
        pr = (d.get("probabilities") or {}).get(dim)
        if not pr:
            continue
        tot = sum(float(v) for v in pr.values()) or 1.0
        for i in range(n):
            acc[i] += float(pr.get(str(i), 0)) / tot
        k += 1
    if not k:
        continue
    acc = {i: v / k for i, v in acc.items()}
    vec = " ".join("%d:%.2f" % (i, acc[i]) for i in range(n))
    hi = max(acc.values())
    top_levels = [i for i in range(n) if acc[i] > 0.15]
    print("%-18s %-7d %6.2f | %s" % (dim, n, min(raw), vec))
    print("%-18s %-7s %6s |   levels with mass>0.15: %s   (max %.2f)"
          % ("", "", "", top_levels, hi))

print()
print("=" * 104)
print("INTERPRETATION KEY")
print("=" * 104)
print("  If market_headroom shows levels>0.15 concentrated at the BOTTOM while other")
print("  dimensions spread across several levels -> the ANCHORS are the problem.")
print("  If ALL dimensions pile at the bottom -> the model's PRIOR is the problem.")
print()

# where does each dimension's *most likely* level sit, on average?
print("=" * 104)
print("MEAN ARGMAX LEVEL PER DIMENSION  (0-indexed; 0 = lowest anchor)")
print("=" * 104)
for dim in DIMS:
    n = counts.get(dim, 5)
    vals, am = [], []
    for d in rows:
        pr = (d.get("probabilities") or {}).get(dim)
        r = d.get("raw_jev_scores_0to4", {}).get(dim)
        if r is not None:
            vals.append(float(r))
        if pr:
            am.append(int(max(pr, key=lambda x: float(pr[x]))))
    if not vals:
        continue
    print("  %-18s mean raw %.2f / %d    argmax mean %.2f    argmax spread %d-%d"
          % (dim, sum(vals) / len(vals), n - 1, sum(am) / len(am) if am else -1,
             min(am) if am else -1, max(am) if am else -1))
