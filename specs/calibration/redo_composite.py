"""REDO the composite analysis with the CORRECT formula.

MY BUG: I replicated the composite as sum((v-1)/(n-1) * w) -- a 0-100 mapping where the
lowest level contributes 0. The harness does sum(v/n * w), where the lowest level
contributes 1/n. So the harness floor is about 20, not 0, and my replication was wrong on
119 of 120 cases.

CONSEQUENCE: every composite finding I reported is suspect and must be re-measured:
  - the "compression" (monotone +13.0 to -4.5)
  - the band agreement (96.5% within one band)
  - the promotion counts (26 of 34 Fragile businesses promoted)
None of them can stand until they are recomputed on the correct formula.

STEP 1 must be: prove the replication now matches the harness on every case.
"""
import csv
import json
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
V = json.loads((HERE / "rubric-v1.8.0.json").read_text())
W = V["_meta"]["weights"]
BAND_LIST = V["_meta"]["bands"]
ABBR = {"relative_strength": "RS", "mental_advantage": "MA", "defensibility": "DEF",
        "competitive_room": "CR", "market_headroom": "MH", "demand_reach": "DR"}
COUNTS = {d: len(V["questions"][d]["levels"]) for d in W}
ORDER = [b[0] for b in BAND_LIST]

idx = json.loads((HERE / "inputs-v4" / "_index.json").read_text())
rows = list(csv.DictReader(open(HERE / "sean-regrade-raw.csv")))
by = {r["company"]: r for r in rows}


def num(x):
    x = ("" if x is None else str(x)).strip()
    if x.lower() in ("n/a", "na", "", "-", "none", "nan"):
        return None
    try:
        return float(x)
    except Exception:
        return None


def band_of(s):
    for nm, lo, hi in BAND_LIST:
        if lo <= s <= hi:
            return nm
    return BAND_LIST[0][0] if s < BAND_LIST[0][1] else BAND_LIST[-1][0]


def comp(vals):
    """EXACT replication of run_jev.py: sum(v / count * weights_used), renormalised."""
    scored = [k for k in W if vals.get(k) is not None]
    if not scored:
        return None
    total_w = sum(W[k] for k in scored)
    used = {k: W[k] / total_w * 100 for k in scored}
    return round(sum(vals[k] / COUNTS[k] * used[k] for k in scored))


# ---- STEP 1: prove the replication now matches -------------------------------
print("=" * 92)
print("STEP 1 — REPLICATION CHECK (must match the harness on every case)")
print("=" * 92)
print()
bad = tot = 0
for cid, e in idx["companies"].items():
    f = HERE / "runs-v18" / ("jev-%s.json" % cid)
    if not f.exists():
        continue
    run = json.loads(f.read_text())
    stored = run.get("composite")
    if stored is None:
        continue
    disp = run.get("dimensions_display_1to5") or {}
    un = set(run.get("dimensions_unscored") or [])
    mine = comp({d: (None if d in un else disp.get(d)) for d in W})
    tot += 1
    if mine != stored:
        bad += 1
        if bad <= 8:
            print("  MISMATCH %-32s harness=%s mine=%s" % (e["name"][:31], stored, mine))
print("  cases checked: %d   MATCH: %d   MISMATCH: %d" % (tot, tot - bad, bad))
print()
if bad:
    raise SystemExit("replication still wrong -- do not trust anything below")
print("  Replication verified. Proceeding.")
print()

# ---- STEP 2: rebuild the record set ------------------------------------------
recs = []
for cid, e in idx["companies"].items():
    if e["cat"] == "home-not-permitted":
        continue
    run = json.loads((HERE / "runs-v18" / ("jev-%s.json" % cid)).read_text())
    disp = run.get("dimensions_display_1to5") or {}
    un = set(run.get("dimensions_unscored") or [])
    r = by.get(e["name"]) or {}
    his = {d: num(r.get("YOUR_" + ABBR[d])) for d in W}
    hc = comp(his)
    mc = run.get("composite")
    if hc is None or mc is None:
        continue
    recs.append({"name": e["name"], "cat": e["cat"], "mine": mc, "his": hc,
                 "mb": band_of(mc), "hb": band_of(hc),
                 "mdims": {d: (None if d in un else disp.get(d)) for d in W},
                 "hdims": his})

print("=" * 92)
print("STEP 2 — BAND AGREEMENT, corrected formula")
print("=" * 92)
print()


def rep(label, sub):
    if not sub:
        return
    n = len(sub)
    same = sum(1 for r in sub if r["mb"] == r["hb"])
    adj = sum(1 for r in sub if r["mb"] != r["hb"]
              and abs(ORDER.index(r["mb"]) - ORDER.index(r["hb"])) == 1)
    far = n - same - adj
    print("  %-24s n=%3d  same %5.1f%%  within-1 %5.1f%%  TWO+ OFF %5.1f%% (%d)"
          % (label, n, 100 * same / n, 100 * (same + adj) / n, 100 * far / n, far))


rep("ALL", recs)
print()
for b in ORDER:
    rep("  his band: " + b[:20], [r for r in recs if r["hb"] == b])
print()
target = [r for r in recs if r["hb"] in (ORDER[0], ORDER[1])]
rep("TARGET (weak SMEs)", target)
print()

print("=" * 92)
print("STEP 3 — IS THE COMPRESSION REAL? (corrected)")
print("=" * 92)
print()
buckets = defaultdict(list)
for r in recs:
    if r["his"] < 35:
        b = "Fragile-ish (<35)"
    elif r["his"] < 50:
        b = "Contested (35-50)"
    elif r["his"] < 65:
        b = "Viable (50-65)"
    elif r["his"] < 80:
        b = "Strong (65-80)"
    else:
        b = "Very strong (80+)"
    buckets[b].append(r["mine"] - r["his"])
for b in ["Fragile-ish (<35)", "Contested (35-50)", "Viable (50-65)", "Strong (65-80)",
          "Very strong (80+)"]:
    xs = buckets.get(b)
    if xs:
        print("  %-20s n=%3d   mean gap %+7.1f   (min %+.0f, max %+.0f)"
              % (b, len(xs), sum(xs) / len(xs), min(xs), max(xs)))
print()
allg = [r["mine"] - r["his"] for r in recs]
print("  overall mean gap %+.1f   (was reported as +13.0 at the Fragile end)"
      % (sum(allg) / len(allg)))
print()
print("  DIRECTION OF BAND ERRORS:")
up = sum(1 for r in recs if ORDER.index(r["mb"]) > ORDER.index(r["hb"]))
dn = sum(1 for r in recs if ORDER.index(r["mb"]) < ORDER.index(r["hb"]))
print("    I am MORE generous: %d     I am HARSHER: %d" % (up, dn))
print()
frag = [r for r in recs if r["hb"] == ORDER[0]]
out = [r for r in frag if r["mb"] != ORDER[0]]
print("  Fragile businesses I move OUT of Fragile: %d of %d" % (len(out), len(frag)))
