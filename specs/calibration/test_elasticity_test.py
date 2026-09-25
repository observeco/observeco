"""
TEST: capacity elasticity hypothesis.

HYPOTHESIS UNDER TEST (from FINDING-duopoly-leg.md):
    Unmet demand can only accumulate where supply is INELASTIC.
    So capacity elasticity determines which instrument can observe headroom at all.

DISCRIMINATING DESIGN:
    Classify all 17 cases by capacity elasticity using ONLY the business
    description -- blind to the jev headroom score. Then reveal and join.
    A hypothesis that cannot fail is not a test, so we also check whether any
    case is BOTH inelastic and low-scoring, or ELASTIC and high-scoring.
"""
import json, glob, os, sys

BASE = "/Users/seanfzc/projects/observeco-main/specs/calibration"

# ---------------------------------------------------------------- outcomes
out = {}
for p in sorted(glob.glob(f"{BASE}/runs/jev-*.json")):
    d = json.load(open(p))
    c = d.get("case")
    if not c:
        continue
    out[c] = d.get("raw_jev_scores_0to4", {}).get("market_headroom")

# ---------------------------------------------------------------- inputs
desc = {}
for p in sorted(glob.glob(f"{BASE}/inputs/*.json")):
    d = json.load(open(p))
    m = d.get("_meta", {})
    desc[m.get("case")] = (m.get("business") or "", m.get("ground_truth") or "")

# ---------------------------------------------------------------- classifier
# Elasticity = can a supplier add capacity quickly?
#   ELASTIC   : new outlet / new hire / more batch runs -- months
#   INELASTIC : physical, capital, tooling or regulatory ceiling -- years
#
# Classified from the DESCRIPTION ONLY. Reasons recorded so it is auditable.
CLS = {
    "E1-asml": ("INELASTIC",
        "~50-60 EUV tools/yr; leading-edge fab needs 10-20. Physical + tooling ceiling."),
    "E2-coupang-flywheel": ("AMBIGUOUS",
        "Fulfilment/logistics: capacity is capital-intensive but not physically capped."),
    "C5-michelin-hawker": ("INELASTIC",
        "One stall, one cook. Output capped by one person's hours."),
    "C2-activesg": ("INELASTIC-ish",
        "29 government gyms; statutory board. Cannot be replicated by a commercial entrant."),
    "C4-sheng-siong": ("ELASTIC",
        "Supermarket: opens stores (81 -> 93 in FY2025). Supply flexes."),
    "C3-pet-lovers-centre": ("ELASTIC",
        "Pet retail: 69 SG stores, 140+ SEA. Openable."),
    "D1-watsons": ("ELASTIC",
        "Health & beauty: ~99 SG stores; Watsons/Guardian open freely."),
    "D2-petlovers-cue": ("ELASTIC", "Same as C3."),
    "C6-euyansang": ("ELASTIC",
        "TCM retail/clinic chain: multi-outlet, openable."),
    "09-koi": ("ELASTIC",
        "Bubble tea: 88 outlets, and the category went 0 -> 62+ brands fast."),
    "N2-koi-stripped": ("ELASTIC", "Same as koi."),
    "08-bubbletea": ("ELASTIC",
        "Bubble tea: 3 outlets. Entry is cheap -- 353 outlets observed across brands."),
    "07-observeco": ("ELASTIC",
        "Consulting: capacity is people; hire or subcontract."),
    # run-file names (jev-*.json) differ from input-file names for these three.
    # Same classification as above; key alias only.
    "koi": ("ELASTIC",
        "Bubble tea: 88 outlets, and the category went 0 -> 62+ brands fast."),
    "bubbletea": ("ELASTIC",
        "Bubble tea: 3 outlets. Entry is cheap -- 353 outlets observed across brands."),
    "observeco": ("ELASTIC",
        "Consulting: capacity is people; hire or subcontract."),
    "C9-b2b-it-services": ("ELASTIC",
        "B2B IT services: people-based; the category has no ceiling."),
    "bonefirm": ("ELASTIC",
        "Supplement: contract manufacture scales in batch runs."),
    "E4-bonefirm-ip": ("ELASTIC", "Same as bonefirm."),
    "N1-closedbusiness": ("N/A",
        "Closed. No demand to serve -- elasticity is undefined."),
}

# ---------------------------------------------------------------- report
order = sorted(out, key=lambda k: out[k])
print("=" * 92)
print("CAPACITY ELASTICITY vs MEASURED HEADROOM")
print("=" * 92)
print()
print("%-22s %-12s %6s   %s" % ("case", "elasticity", "raw", "reason"))
print("-" * 92)
for c in order:
    e, why = CLS.get(c, ("??", "unclassified"))
    print("%-22s %-12s %6s   %s" % (c, e, out[c], why[:46]))

print()
print("=" * 92)
print("DOES ELASTICITY EXPLAIN THE SPREAD?")
print("=" * 92)
band = {}
for c in out:
    e = CLS.get(c, ("??", ""))[0]
    band.setdefault(e, []).append(out[c])
for e in sorted(band):
    v = band[e]
    print("  %-12s n=%2d   raw %.2f - %.2f   mean %.2f"
          % (e, len(v), min(v), max(v), sum(v) / len(v)))

inel = [c for c in out if CLS[c][0] == "INELASTIC"]
elas = [c for c in out if CLS[c][0] == "ELASTIC"]
print()
print("  ELASTIC   cases: n=%d  max raw = %.2f" % (len(elas), max(out[c] for c in elas)))
print("  INELASTIC cases: n=%d  values = %s"
      % (len(inel), {c: out[c] for c in inel}))

print()
print("=" * 92)
print("FALSIFICATION CHECK -- can this hypothesis fail on this corpus?")
print("=" * 92)
hi = [c for c in out if out[c] >= 2.6]
lo_inel = [c for c in inel if out[c] < 2.6]
print("  cases scoring >= 2.60 (unmet-demand signal): %s" % hi)
for c in hi:
    print("      %-22s elasticity = %s" % (c, CLS[c][0]))
print()
print("  INELASTIC cases scoring BELOW 2.60 (would falsify): %s"
      % (lo_inel if lo_inel else "NONE"))
print("  ELASTIC   cases scoring ABOVE 2.60 (would falsify): %s"
      % ([c for c in elas if out[c] >= 2.6] or "NONE"))
print()

# how many cases can actually carry the inelastic instrument?
n_inel = len(inel)
print("  inelastic cases in corpus : %d of %d" % (n_inel, len(out)))
print("  elastic   cases in corpus : %d of %d" % (len(elas), len(out)))
print()
if len(hi) == len(inel) and n_inel <= 2:
    print("  *** HYPOTHESIS SURVIVES -- but VACUOUSLY. ***")
    print("  It separates %d inelastic case(s) from everything else, and we already" % n_inel)
    print("  knew the flat pack was low and ASML was high. The classifier adds NO")
    print("  new discrimination to this corpus. This test cannot fail here.")
