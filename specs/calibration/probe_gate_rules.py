"""Which gate RULE would actually work?

Current rule: gate fires when display < 2, i.e. raw < 0.5 (all mass on level 0).
That never happens on 3 of 5 dimensions, so the gate is inert.

Testing candidate rules against the 20-case corpus. A usable rule must fire on a
small, sensible subset -- not zero (decorative) and not most (useless).
"""
import json, glob, decimal
BASE = "/Users/seanfzc/projects/observeco-main/specs/calibration"
rub = json.load(open(f"{BASE}/rubric.json"))
meta = rub["_meta"]
DIMS = list(meta["weights"])
counts = meta.get("level_counts") or {}
FLOOR = 2  # every gate floor in the rubric

runs = [json.load(open(p)) for p in sorted(glob.glob(f"{BASE}/runs/jev-*.json"))]
runs = [d for d in runs if d.get("case")]

# known-should-gate cases, from the control plan
SHOULD_GATE = {"N1-closedbusiness"}


def disp(raw, n):
    return max(1, min(n, int(decimal.Decimal(str(raw)).quantize(
        decimal.Decimal("1"), rounding=decimal.ROUND_HALF_UP)) + 1))


print("=" * 100)
print("PER-CASE BOTTOM MASS  (what each gate could key on)")
print("=" * 100)
print("%-22s %s" % ("case", "  ".join("%-26s" % d for d in DIMS)))
print("-" * 100)
for d in runs:
    cells = []
    for dim in DIMS:
        n = counts.get(dim, 5)
        pr = (d.get("probabilities") or {}).get(dim) or {}
        raw = d.get("raw_jev_scores_0to4", {}).get(dim)
        if raw is None or not pr:
            cells.append("%-26s" % "-")
            continue
        l0 = float(pr.get("0", 0))
        l01 = l0 + float(pr.get("1", 0))
        cells.append("%-26s" % ("p0=%.2f p01=%.2f disp=%d" % (l0, l01, disp(raw, n))))
    print("%-22s %s" % (d["case"], "  ".join(cells)))

print()
print("=" * 100)
print("CANDIDATE GATE RULES -- how many of 20 cases would fire?")
print("=" * 100)
rules = {
    "A current:  display < 2      (raw < 0.5)": lambda pr, raw, n: disp(raw, n) < 2,
    "B raw      < 1.0             ": lambda pr, raw, n: raw < 1.0,
    "C raw      < 1.5             ": lambda pr, raw, n: raw < 1.5,
    "D p(level0) > 0.50           ": lambda pr, raw, n: float(pr.get("0", 0)) > 0.50,
    "E p(level0) > 0.30           ": lambda pr, raw, n: float(pr.get("0", 0)) > 0.30,
    "F p(l0)+p(l1) > 0.70         ": lambda pr, raw, n: (float(pr.get("0", 0))
                                                        + float(pr.get("1", 0))) > 0.70,
    "G p(l0)+p(l1) > 0.90         ": lambda pr, raw, n: (float(pr.get("0", 0))
                                                        + float(pr.get("1", 0))) > 0.90,
}

for label, fn in rules.items():
    fires = {dim: [] for dim in DIMS}
    for d in runs:
        for dim in DIMS:
            n = counts.get(dim, 5)
            pr = (d.get("probabilities") or {}).get(dim) or {}
            raw = d.get("raw_jev_scores_0to4", {}).get(dim)
            if raw is None or not pr:
                continue
            if fn(pr, raw, n):
                fires[dim].append(d["case"])
    parts = []
    for dim in DIMS:
        c = len(fires[dim])
        mark = " " if c else "!"          # ! = still inert
        parts.append("%s%s:%-2d" % (mark, dim[:9], c))
    print("  %-42s %s" % (label, "  ".join(parts)))
    allf = sorted({c for dim in DIMS for c in fires[dim]})
    hit = [c for c in allf if c in SHOULD_GATE]
    print("  %-42s   -> cases fired: %s%s"
          % ("", len(allf), allf if len(allf) <= 8 else str(allf[:8]) + "..."))
    print("  %-42s   -> catches N1 (should gate): %s"
          % ("", "YES" if hit else "NO"))
    print()

print("=" * 100)
print("NOTE ON market_headroom")
print("=" * 100)
print("  market_headroom asks about the MARKET, not the business. N1's business is dead")
print("  but its market (bubble tea) has demand -- so headroom correctly does NOT gate N1.")
print("  A 'no demand at all for this category' market is one no customer would submit.")
print("  Its inertness may therefore be CORRECT-BY-CONSTRUCTION, not a defect.")
print("  That is a different diagnosis from competitive_room / demand_reach, which have")
print("  no such argument and may simply be mis-thresholded.")
