"""A3 regression across all 20 cases: what does dropping headroom for elastic markets do?

Uses the CACHED elasticity classifications (runs/a3_elasticity_classification.json) and
the stored per-case dimension scores. No new API calls -- this is an arithmetic
regression on the A3 branch, which is exactly what needs checking before shipping.

For each case it computes the composite BOTH ways:
  BEFORE (pre-A3): all dimensions that clear the coverage floor, headroom included
  AFTER  (A3)    : headroom dropped when the market is elastic, weights renormalised

Reports every band change, because a band change is a change to what the client is told.
"""
import json
import glob
from pathlib import Path

HERE = Path(__file__).resolve().parent
rub = json.loads((HERE / "rubric.json").read_text())
meta = rub["_meta"]
W = meta["weights"]
CNT = meta["level_counts"]
GATES = {k: v for k, v in meta["gates"].items() if not k.startswith("_")}
FLOOR = meta.get("display_floor", 0.20)
DISP = meta["elasticity_dispositions"]

cls = json.loads((HERE / "runs" / "a3_elasticity_classification.json").read_text())

# Four legacy cases are stored under short run names but classified under input
# filenames. Without this the regression silently treats them as unclassified and
# reports "unchanged" for them -- a false pass.
ALIAS = {
    "bonefirm": "01-bonefirm", "observeco": "07-observeco",
    "bubbletea": "08-bubbletea", "koi": "09-koi",
}


def elasticity(case):
    probs = cls.get(case) or cls.get(ALIAS.get(case, ""))
    if not probs:
        return None
    return max(probs, key=lambda k: float(probs[k]))


def band_of(c):
    for name, lo, hi in meta["bands"]:
        if lo <= c <= hi:
            return name
    return "OUT-OF-RANGE"


def composite_for(dims, cov, drop):
    scored = [k for k in W if k not in drop
              and isinstance(cov.get(k), (int, float)) and cov[k] >= FLOOR]
    if not scored:
        return None, [], {}
    tw = sum(W[k] for k in scored)
    wu = {k: W[k] / tw * 100 for k in scored}
    fires = [k for k in scored if dims[k] < GATES[k]]
    if fires:
        return None, fires, wu
    c = round(sum(dims[k] / CNT[k] * wu[k] for k in scored))
    return c, [], wu


rows = []
for p in sorted(glob.glob(str(HERE / "runs" / "jev-*.json"))):
    d = json.load(open(p))
    if not d.get("case") or "dimensions_display_1to5" not in d:
        continue
    case = d["case"]
    dims, cov = d["dimensions_display_1to5"], d["evidence_coverage"]
    e = elasticity(case)
    drop = {"market_headroom"} if (e == "elastic"
                                   and DISP["elastic"]["market_headroom"] == "not_applicable") else set()
    before, _, _ = composite_for(dims, cov, set())
    after, fires, wu = composite_for(dims, cov, drop)
    rows.append((case, e or "?", before, band_of(before) if before else "GATE",
                 after, band_of(after) if after else "GATE", bool(drop)))

print("=" * 104)
print("A3 REGRESSION — 20 cases. Elastic markets lose market_headroom; inelastic keep it.")
print("=" * 104)
print("%-22s %-10s %-16s %-16s %s" % ("case", "elasticity", "BEFORE", "AFTER (A3)", "effect"))
print("-" * 104)
changed = same = 0
for case, e, b, bb, a, ab, dropped in rows:
    if b == a:
        eff = "unchanged"; same += 1
    else:
        d = a - b
        eff = "%+d pts" % d
        if bb != ab:
            eff += "   BAND %s -> %s" % (bb, ab)
            changed += 1
    tag = "drop headroom" if dropped else "keep headroom"
    print("%-22s %-10s %-16s %-16s %s  (%s)"
          % (case, e, "%s %s" % (b, bb), "%s %s" % (a, ab), eff, tag))

print()
nb = sum(1 for r in rows if not r[6])
print("  headroom DROPPED (elastic) : %d cases" % sum(1 for r in rows if r[6]))
print("  headroom KEPT (inelastic)  : %d cases" % nb)
print("  composites changed         : %d" % sum(1 for r in rows if r[2] != r[4]))
print("  BAND changes               : %d" % changed)
print()
print("  A3's effect is confined to elastic-market cases; inelastic cases are untouched.")
print()
print("  NOTE ON DIRECTION: composites RISE for dropped cases, because headroom was the")
print("  near-lowest-scoring dimension for elastic markets. That is the intended")
print("  correction -- the 15% was spreading a near-constant across the score. It is")
print("  also a MATERIAL change to what clients are told, and should be reviewed as a")
print("  banding question, not accepted as mechanical.")
