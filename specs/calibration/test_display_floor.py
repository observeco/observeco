"""THE DISPLAY FLOOR AND ITS OWN RATIONALE DISAGREE. Test which floor is right.

The rubric's `display_floor_note` states the floor's purpose:
    "a coverage of 0.00 is a dead-even distribution = no judgment at all; printing a
     score for it fabricates a finding."
That is an argument for a floor at, or just above, ZERO.

The floor is actually set at 0.2. So it drops dimensions that DO carry a judgment --
McDonald's demand_reach at 0.12 is a weak signal, not "no judgment at all". Dropping it
changes the weight denominator, which makes the case's composite non-comparable with a
case that kept it (measured: mean shift 2.4 pts, max 8, 3 band words affected).

So the floor is doing two jobs and conflating them:
  1. "this dimension has NO judgment"      -> a floor near 0.0 is right
  2. "this dimension has a WEAK judgment"  -> should be FLAGGED, not dropped

TEST: try floors 0.00 / 0.05 / 0.10 / 0.20 and measure, on the 55-case set:
  - how many cases keep a common dimension set
  - whether the pre-registered label ordering gets better or worse
  - how many band words move
The right floor is the one that maximises comparability WITHOUT inventing judgments.
"""
import glob
import json
import statistics
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
R = json.loads((HERE / "rubric.json").read_text())["_meta"]
W, CNT, BANDS = R["weights"], R["level_counts"], R["bands"]
FULL = sorted(W)

IDX = json.loads((HERE / "inputs-v2" / "_index.json").read_text())["companies"]
LABEL = {}
for cid in IDX:
    LABEL[cid] = IDX[cid].get("cat")

# the same pre-registered ordinal labels as adjudicate_v2.py
ORD = {
    "GY07": "dead",
    "BT05": "weak", "BT06": "weak", "BT09": "weak", "BT10": "weak", "GY06": "weak",
    "SM03": "weak", "SM04": "weak", "KP03": "weak", "BK05": "weak", "FF03": "weak",
    "EW04": "weak", "EL01": "weak", "EL02": "weak", "EL03": "weak", "EL04": "weak",
    "BT08": "mid", "GY03": "mid", "GY04": "mid", "KP02": "mid", "KP04": "mid",
    "BK02": "mid", "FF04": "mid", "FF05": "mid", "HB02": "mid", "HB03": "mid",
    "EW02": "mid", "EW03": "mid", "FU02": "mid", "PS02": "mid",
    "BT01": "strong", "BT02": "strong", "BT03": "strong", "BT04": "strong",
    "BT07": "strong", "GY01": "strong", "GY02": "strong", "GY05": "strong",
    "SM01": "strong", "SM02": "strong", "SM05": "strong", "KP01": "strong",
    "BK01": "strong", "BK03": "strong", "BK04": "strong", "FF01": "strong",
    "FF02": "strong", "FF06": "strong", "HB01": "strong", "HB04": "strong",
    "EW01": "strong", "FU01": "strong", "FU03": "strong", "FU04": "strong",
    "PS01": "strong",
}

runs = []
for p in sorted(glob.glob(str(HERE / "runs" / "jev-*.json"))):
    d = json.loads(Path(p).read_text())
    if "case" not in d or d.get("rubric_version") != "0.9.0":
        continue
    cid = d["case"].split("-")[0]
    d["_cid"] = cid
    runs.append(d)

# market_headroom is dropped STRUCTURALLY by A3 (elastic market) and that is a tested,
# intended decision -- not the defect under test. Treat it as excluded by design.
STRUCTURAL = "market_headroom"


def band_of(c):
    for name, lo, hi in BANDS:
        if lo <= c <= hi:
            return name
    return "?"


def score(d, floor):
    cov = d.get("evidence_coverage") or {}
    dims = d.get("dimensions_display_1to5") or {}
    unsc = []
    for k in FULL:
        if k == STRUCTURAL and k in (d.get("dimensions_unscored") or []):
            unsc.append(k)                       # A3 drop: keep, it is by design
            continue
        c = cov.get(k)
        if not isinstance(c, (int, float)) or c < floor:
            unsc.append(k)
    scored = [k for k in FULL if k not in unsc]
    if not scored:
        return None, "UNSCORED", unsc
    tw = sum(W[k] for k in scored)
    return round(sum(dims[k] / CNT[k] * W[k] / tw * 100 for k in scored)), band_of(
        round(sum(dims[k] / CNT[k] * W[k] / tw * 100 for k in scored))), unsc


print("=" * 100)
print("FLOOR SWEEP — comparability vs invented judgment")
print("=" * 100)
print("%-7s %-14s %-30s %-34s %s"
      % ("floor", "full-set cases", "weak/mid/strong means", "monotonic?", "band moves"))
print("-" * 100)

base = None
results = {}
for floor in (0.00, 0.05, 0.10, 0.20):
    by = defaultdict(list)
    nsets = 0
    for d in runs:
        c, b, unsc = score(d, floor)
        d["_floor_%s" % floor] = (c, b, tuple(unsc))
        if not [u for u in unsc if u != STRUCTURAL]:
            nsets += 1
        if c is not None and d["_cid"] in ORD:
            by[ORD[d["_cid"]]].append(c)
    means = {k: statistics.mean(v) for k, v in by.items() if v}
    order = ["dead", "weak", "mid", "strong"]
    seq = [means.get(k) for k in order if k in means]
    mono = all(seq[i] <= seq[i + 1] for i in range(len(seq) - 1))
    if base is None:
        moves = "-"
        base = {d["case"]: d["_floor_%s" % floor][1] for d in runs}
    else:
        moves = sum(1 for d in runs
                    if d["_floor_%s" % floor][1] != base.get(d["case"]))
    results[floor] = {"full": nsets, "means": means, "mono": mono, "moves": moves}
    print("%-7.2f %-14s %-30s %-34s %s"
          % (floor, "%d of %d" % (nsets, len(runs)),
             " ".join("%s=%.1f" % (k[0].upper(), means[k]) for k in order if k in means),
             "YES" if mono else "NO", moves))

print()
print("=" * 100)
print("SEPARATION QUALITY — does the label ordering hold, and by how much?")
print("=" * 100)
print("%-7s %-22s %-22s %s" % ("floor", "weak -> mid gap", "mid -> strong gap", "reading"))
for floor in (0.00, 0.05, 0.10, 0.20):
    m = results[floor]["means"]
    wm = m.get("mid", 0) - m.get("weak", 0)
    ms = m.get("strong", 0) - m.get("mid", 0)
    note = ""
    if ms < R["band_noise"]:
        note = "mid vs strong gap < band noise (%.1f)" % R["band_noise"]
    print("%-7.2f %-22.1f %-22.1f %s" % (floor, wm, ms, note))

print()
print("=" * 100)
print("WHAT EACH FLOOR DROPS — is it judgment or noise?")
print("=" * 100)
print("   coverage of every dimension that the 0.20 floor drops but a lower floor keeps:")
print()
print("   %-24s %-18s %s" % ("case", "dimension", "coverage"))
drops = []
for d in runs:
    cov = d.get("evidence_coverage") or {}
    for k in FULL:
        if k == STRUCTURAL:
            continue
        c = cov.get(k)
        if isinstance(c, (int, float)) and 0.0 < c < 0.20:
            drops.append((d["case"], k, c))
for case, k, c in sorted(drops, key=lambda x: x[2]):
    print("   %-24s %-18s %.2f" % (case, k, c))
print()
if drops:
    cs = [c for _, _, c in drops]
    print("   n=%d | min %.2f | median %.2f | max %.2f" % (len(cs), min(cs),
                                                           statistics.median(cs), max(cs)))
    exactly_zero = sum(1 for c in cs if c == 0.0)
    print("   coverage exactly 0.00 (the note's stated case): %d of %d" % (exactly_zero, len(cs)))
    print()
    print("   -> the note argues for dropping at 0.00 ('dead-even = no judgment').")
    print("      At 0.20 the floor also drops coverage of %.2f-%.2f, which is NOT"
          % (min(cs), max(cs)))
    print("      'no judgment' -- it is a weak judgment, and dropping it changes the")
    print("      denominator, which is what makes cases non-comparable.")
