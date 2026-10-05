"""IS THE COMPRESSION THE MODEL'S BELIEF, OR THE ARGMAX/ROUNDING MAPPING?

The instrument reads the instrument's level as int(round(E[level])) + 1, where E[level] is the
probability-weighted mean of the level distribution. AVERAGING ALWAYS PULLS TOWARD THE MIDDLE: if the
model is torn between 4 and 5 it reports a mean of 4.5, and rounding sends it to 4 -- the same
shrinkage a bimodal belief produces.

THE TEST. From the SAME stored probabilities, compute three readings:
  1. the current one   : int(round(E[level])) + 1        (probability-weighted mean, rounded)
  2. the model's ARGMAX: the single most probable level   (what the model actually picked)
  3. the MEDIAN level  : the level at cumulative 50%      (a middle reading, less peaked than argmax)

Then compare each against Sean's grades on all 120. If ARGMAX or MEDIAN beats the mean, the compression
is a MAPPING artefact and NO PROSE CHANGE IS NEEDED -- which would explain why three prose fixes failed.
"""
import glob, json, csv, statistics as st
from collections import Counter

BASE = "/Users/seanfzc/projects/observeco-main/specs/calibration"

human = {}
for r in csv.DictReader(open(f"{BASE}/sean-regrade-raw.csv")):
    cid = (r.get("case_id") or "").strip().lower()
    if cid:
        human[cid] = r


def num(x):
    try:
        return float(x)
    except Exception:
        return None


DIMS = [("position_strength", "YOUR_RS"), ("mental_advantage", "YOUR_MA"),
        ("defensibility", "YOUR_DEF"), ("competitive_room", "YOUR_CR"),
        ("demand_reach", "YOUR_DR")]


def argmax_level(probs):
    """the model's own pick: highest-probability level"""
    if not probs:
        return None
    items = sorted(((float(v), k) for k, v in probs.items()), reverse=True)
    return int(items[0][1]) + 1


def median_level(probs):
    """level at cumulative 50%"""
    if not probs:
        return None
    items = sorted((int(k), float(v)) for k, v in probs.items())
    tot = sum(v for _, v in items)
    if tot <= 0:
        return None
    run = 0.0
    for k, v in items:
        run += v
        if run / tot >= 0.5:
            return k + 1
    return items[-1][0] + 1


def mean_level(probs):
    if not probs:
        return None
    w = sum((int(k) + 1) * float(v) for k, v in probs.items())
    tot = sum(float(v) for v in probs.values())
    return w / tot if tot else None


# gather per-case readings from the stored runs
runs = []
for p in sorted(glob.glob(f"{BASE}/runs-par/jev-*.json")):
    d = json.load(open(p))
    c = (d.get("case") or "").lower()
    if c in human:
        runs.append((c, d.get("probabilities") or {}))

print("runs joined to human grades: %d" % len(runs))
print()
hdr = "%-20s %-10s %6s %8s %8s %9s %9s"
for label, fn in (("CURRENT (mean)", mean_level), ("ARGMAX", argmax_level), ("MEDIAN", median_level)):
    print("=" * 88)
    print("READING: %s" % label)
    print("=" * 88)
    print(hdr % ("dimension", "", "n", "his mu", "inst mu", "mean err", "EXACT"))
    for dim, ycol in DIMS:
        rows = []
        for c, probs in runs:
            y = num(human[c].get(ycol))
            if y is None:
                continue
            pr = probs.get(dim) or {}
            m = fn(pr)
            if m is None:
                continue
            # normalise defensibility's 6 levels / others' 5 are already 1-based from the key+1
            rows.append((y, round(m)))
        if len(rows) < 10:
            continue
        exact = sum(1 for y, m in rows if abs(y - m) < 0.5)
        print(hdr % (dim, "", len(rows), "%.2f" % st.mean([y for y, _ in rows]),
                     "%.2f" % st.mean([m for _, m in rows]),
                     "%+.2f" % st.mean([m - y for y, m in rows]),
                     "%.0f%%" % (100 * exact / len(rows))))
    print()
