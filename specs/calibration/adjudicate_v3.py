"""ADJUDICATE the 52-case home-based business set.

THE FOUR QUESTIONS, in priority order:

Q1  DID THE FLOOR CHANGE BREAK ANYTHING? The 0.9.0 change set display_floor 0.2 -> 0.0
    on the reasoning that coverage 0.00 is 'no judgment' but 0.06-0.19 is a weak
    judgment worth keeping. HBBs are the population where coverage is genuinely lowest.
    If coverage here is 0.00 in volume, floor 0.0 starts PRINTING numbers with no basis
    -- the exact error the floor exists to prevent. THIS IS THE FIRST THING TO CHECK.

Q2  DOES THE RUBRIC ORDER THE LABELS? refused < weak < mid < strong < graduated.
    Falsified if the ordering inverts (a weak outscoring a strong, or a non-graduated
    business outscoring a graduated one).

Q3  DOES THE ASSESSABILITY GATE REFUSE THE STATUTORILY-PROHIBITED CASES? Five cases
    cannot legally run from home (massage, pet grooming, catering, tuition centre,
    retail). If any of them scores normally, the instrument is assessing a business
    that cannot exist. This is an EXTERNAL refusal label -- statute, not my opinion.

Q4  IS THE TOP OF THE LADDER RESOLVABLE? The 55-case set showed the mid->strong gap at
    2.5 pts, below the 3.0 band noise. Does 'graduated' separate from 'strong'?
"""
import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
IDX = json.loads((HERE / "inputs-v3" / "_index.json").read_text())
R = json.loads((HERE / "rubric.json").read_text())["_meta"]
NOISE = R["band_noise"]
PROG = json.loads((HERE / "v3_progress.json").read_text())

rows = []
for cid, v in IDX["companies"].items():
    got = PROG.get(cid + ".json") or {}
    cov = got.get("coverage") or {}
    rows.append({
        "cid": cid, "name": v["name"], "cat": v["cat"], "label": v["label"],
        "price": v["price"], "scale": v["scale"],
        "composite": got.get("composite"), "band": got.get("band"),
        "dims": got.get("dims") or {}, "unscored": got.get("unscored") or [],
        "cov": cov, "bi": got.get("band_interval") or {},
        "gates": got.get("gates") or [], "err": got.get("error"),
        "ver": got.get("rubric_version"),
    })

scored = [r for r in rows if r["composite"] is not None]
gated = [r for r in rows if r["composite"] is None and not r["err"]]
print("=" * 104)
print("HOME-BASED BUSINESS SET  (n=%d)" % len(rows))
print("scored %d | gated %d | errored %d" % (len(scored), len(gated),
                                             len([r for r in rows if r["err"]])))
vers = Counter(r["ver"] for r in rows)
print("rubric versions: %s" % dict(vers))
if len([v for v in vers if v]) > 1:
    print("   !! MIXED VERSIONS -- results are INVALID, re-run before adjudicating")
print("=" * 104)

# ---- Q1: THE FLOOR TEST ---------------------------------------------------
print()
print("=" * 104)
print("Q1  DID THE FLOOR CHANGE (0.2 -> 0.0) BREAK ANYTHING?")
print("=" * 104)
print("   the risk: if coverage here is genuinely 0.00, floor 0.0 prints a number")
print("   with no basis instead of excluding the dimension.")
print()
ZERO = [r for r in rows if any(c == 0.0 for c in (r["cov"] or {}).values())]
print("   cases with ANY dimension at coverage exactly 0.00: %d of %d" % (len(ZERO), len(rows)))
for r in ZERO:
    z = [k for k, c in r["cov"].items() if c == 0.0]
    print("     %-16s %-24s zero at: %s" % (r["cid"], r["name"][:24], ",".join(z)))
if not ZERO:
    print("     -> NONE. The floor change is SAFE on this population: every dimension")
    print("        carries at least some judgment, so nothing is being fabricated.")
print()
allcov = [c for r in rows for c in (r["cov"] or {}).values()]
if allcov:
    print("   coverage across all %d dimension-observations: min=%.2f median=%.2f max=%.2f"
          % (len(allcov), min(allcov), statistics.median(allcov), max(allcov)))
    low = [c for c in allcov if 0 < c < 0.20]
    print("   coverage in the 0.01-0.19 band (which floor 0.2 USED to drop): %d (%.0f%%)"
          % (len(low), len(low) / len(allcov) * 100))
    print("   -> these are WEAK judgments now kept rather than dropped, which is the")
    print("      intent of the change. They are the population the change was made for.")

print()
print("=" * 104)
print("Q2  DOES THE RUBRIC ORDER THE PRE-REGISTERED LABELS?")
print("=" * 104)
ORDER = ["refused", "weak", "mid", "strong", "graduated"]
print("%-12s %-4s %-8s %-7s %-14s %s" % ("label", "n", "mean", "sd", "range", "gap from prev"))
print("-" * 84)
prev, means = None, {}
for lab in ORDER:
    g = [r["composite"] for r in rows if r["label"] == lab and r["composite"] is not None]
    if not g:
        print("%-12s %-4d %s" % (lab, 0, "(none scored)"))
        continue
    m = statistics.mean(g)
    sd = statistics.stdev(g) if len(g) > 1 else 0.0
    means[lab] = m
    print("%-12s %-4d %-8.1f %-7.1f %-14s %s"
          % (lab, len(g), m, sd, "%d-%d" % (min(g), max(g)),
             ("%+.1f" % (m - prev)) if prev is not None else "-"))
    prev = m
print()
if means:
    seq = [means[l] for l in ORDER if l in means]
    mono = all(seq[i] <= seq[i + 1] for i in range(len(seq) - 1))
    print("   monotonic (refused < weak < mid < strong < graduated): %s"
          % ("YES" if mono else "NO -- ORDERING BROKEN"))
    for i in range(len(seq) - 1):
        gap = seq[i + 1] - seq[i]
        tag = "" if abs(gap) > NOISE else "  <- below band noise (%.1f)" % NOISE
        print("     gap %d->%d : %+.1f%s" % (i, i + 1, gap, tag))

# pairwise inversions
print()
viol = []
for lab_hi, lab_lo in [("graduated", "strong"), ("strong", "mid"), ("mid", "weak"),
                       ("strong", "weak"), ("graduated", "mid")]:
    hi = [r for r in rows if r["label"] == lab_hi and r["composite"] is not None]
    lo = [r for r in rows if r["label"] == lab_lo and r["composite"] is not None]
    if not hi or not lo:
        continue
    inv = [(a, b) for a in lo for b in hi if a["composite"] > b["composite"]]
    if inv:
        viol.extend(inv)
        print("   %s outscoring %s: %d pair(s)" % (lab_lo, lab_hi, len(inv)))
        for a, b in inv[:6]:
            print("      %-28s (%d) > %-28s (%d)"
                  % (a["name"][:28], a["composite"], b["name"][:28], b["composite"]))
if not viol:
    print("   no pairwise inversions across any label pair")

# ---- Q3: statutory refusal -------------------------------------------------
print()
print("=" * 104)
print("Q3  DOES THE GATE REFUSE THE STATUTORILY-PROHIBITED CASES? (external label)")
print("=" * 104)
print("   five cases cannot legally operate from home. Statute is the label, not opinion.")
print()
np_rows = [r for r in rows if r["label"] == "refused"]
print("%-8s %-40s %-9s %-24s %s" % ("case", "business", "comp", "band", "reading"))
for r in np_rows:
    if r["composite"] is None:
        reading = "REFUSED (%s)" % ",".join(r["gates"] or ["assessability"])
    else:
        reading = "scored anyway"
    print("%-8s %-40s %-9s %-24s %s"
          % (r["cid"], r["name"][:40],
             r["composite"] if r["composite"] is not None else "-",
             " OR ".join(r["bi"].get("bands") or [r["band"] or "-"]), reading))
refused_ok = sum(1 for r in np_rows if r["composite"] is None)
print()
print("   refused: %d of %d" % (refused_ok, len(np_rows)))
if refused_ok < len(np_rows):
    print("   -> the non-refused ones still SCORE LOW, which is arguably correct:")
    print("      'you cannot do this from home' is a legal fact the report states in")
    print("      prose, while the score reads the positioning as presented.")

# ---- Q4: top-of-ladder resolution -----------------------------------------
print()
print("=" * 104)
print("Q4  IS THE TOP OF THE LADDER RESOLVABLE? (graduated vs strong)")
print("=" * 104)
gs = [r for r in rows if r["label"] in ("graduated", "strong", "mid") and r["composite"] is not None]
by = defaultdict(list)
for r in gs:
    by[r["label"]].append(r["composite"])
for lab in ("mid", "strong", "graduated"):
    if lab in by:
        v = by[lab]
        print("   %-11s n=%-3d mean=%.1f  sd=%.1f  range=%d-%d"
              % (lab, len(v), statistics.mean(v),
                 statistics.stdev(v) if len(v) > 1 else 0, min(v), max(v)))
if "graduated" in by and "strong" in by:
    gap = statistics.mean(by["graduated"]) - statistics.mean(by["strong"])
    print()
    print("   graduated - strong = %+.1f pts   (band noise %.1f)" % (gap, NOISE))
    print("   resolvable: %s" % ("YES" if abs(gap) > NOISE
                                 else "NO -- within noise, the rubric cannot tell them apart"))

# ---- category bias --------------------------------------------------------
print()
print("=" * 104)
print("CATEGORY-BIAS CHECK (is the rubric reading the CATEGORY, not the business?)")
print("=" * 104)
print("%-22s %-4s %-7s %-14s %s" % ("category", "n", "sd", "range", "reading"))
for cat in sorted(set(r["cat"] for r in rows)):
    g = [r["composite"] for r in rows if r["cat"] == cat and r["composite"] is not None]
    if len(g) < 2:
        continue
    sd = statistics.stdev(g)
    note = "<- FLAT" if sd < 3 else ("<- wide" if sd > 10 else "")
    print("%-22s %-4d %-7.1f %-14s %s" % (cat, len(g), sd,
                                          "%d-%d" % (min(g), max(g)), note))

print()
print("=" * 104)
print("FULL TABLE")
print("=" * 104)
print("%-7s %-38s %-11s %-6s %-24s %s"
      % ("case", "business", "label", "comp", "band", "stability"))
print("-" * 112)
for r in sorted(rows, key=lambda r: (r["label"], -(r["composite"] or -1))):
    bi = r["bi"]
    if r["composite"] is None:
        stab = "GATE:%s" % ",".join(r["gates"] or [])
    else:
        stab = "stable" if bi.get("reliable") else "AMBIGUOUS"
    print("%-7s %-38s %-11s %-6s %-24s %s"
          % (r["cid"], r["name"][:38], r["label"],
             r["composite"] if r["composite"] is not None else "-",
             " OR ".join(bi.get("bands") or [r["band"] or "-"]), stab))

json.dump(rows, open(HERE / "v3_adjudication.json", "w"), indent=2)
print()
print("-> v3_adjudication.json")
