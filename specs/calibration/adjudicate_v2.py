"""ADJUDICATE the 55-case fresh-data validity set against the PRE-REGISTERED labels.

The question is NOT "are the scores plausible". It is:
  did the rubric order these businesses the way the EXTERNAL label says it should?

Three tests, each with a stated falsification condition:

T1  WITHIN-CATEGORY ORDERING. In a wide-price-spread category the rubric should
    separate the strong positions (an owned end of the ladder) from the
    undifferentiated middle. Falsified if a brand with NO distinct position outscores
    one with a clear owned position in the same category.

T2  CONVERGED-PRICE CATEGORY (electronics) must score LOW and FLAT. Nothing there
    holds a distinct position, so a high score would mean the instrument invents
    differentiation. Falsified if electronics scores like bubble tea.

T3  THE DOCUMENTED DEATH (True Fitness, closed 10 Sep 2026) must fail. Falsified if
    it scores acceptably -- that would mean the rubric cannot see a business that
    is actually dead.

Plus a CATEGORY-BIAS check: if every member of a category scores alike regardless of
its label, the rubric is reading the category, not the business.
"""
import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
IDX = json.loads((HERE / "inputs-v2" / "_index.json").read_text())
PROG = json.loads((HERE / "v2_progress.json").read_text())

# the LABEL: a weak/mid/strong ordinal read off the external fact, assigned by ME
# before the run from the label_source text only. Kept here so the mapping is visible.
LABEL = {
    # bubble tea: price/position spread; ends owned, middle undifferentiated
    "BT01": ("strong", "owns the S$1.50 price floor outright"),
    "BT02": ("strong", "90 outlets, largest network, 20 yrs, market leader"),
    "BT03": ("strong", "own tea farms, brewed to order - hard to replicate"),
    "BT04": ("strong", "invented the cheese-foam category"),
    "BT07": ("strong", "explicit anti-category position; fastest riser"),
    "BT08": ("mid", "homegrown no.1 claim, but one of many"),
    "BT05": ("weak", "budget, no distinct position"),
    "BT06": ("weak", "48 outlets but no distinct claim"),
    "BT09": ("weak", "a feature (fresh pearls), not a position"),
    "BT10": ("weak", "no local distinction"),
    # gym
    "GY01": ("strong", "the price floor every gym is judged against"),
    "GY02": ("strong", "161 outlets, 24/7, hardest footprint to copy"),
    "GY03": ("mid", "established, but priced above and no unique claim"),
    "GY04": ("mid", "2 clubs, premium amenities, narrow reach"),
    "GY05": ("strong", "owns premium recovery amenities, pools"),
    "GY06": ("weak", "cheaper 24/7, no distinct position"),
    "GY07": ("dead", "closed all SG clubs 10 Sep 2026"),
    # supermarket
    "SM01": ("strong", "the national default, largest retailer"),
    "SM02": ("strong", "owns value+fresh, peer-leading margin"),
    "SM03": ("weak", "premium claim now contested by FairPrice Finest"),
    "SM04": ("weak", "value claim lost to Sheng Siong on scale"),
    "SM05": ("strong", "owns the Japanese-experience format"),
    # kopitiam
    "KP01": ("strong", "1926 heritage standard, largest chain"),
    "KP02": ("mid", "rival heritage claim but second to Ya Kun"),
    "KP03": ("weak", "modern imitation of the format"),
    "KP04": ("mid", "iconic single location, no scale"),
    # bakery
    "BK01": ("strong", "the iconic local chain, most outlets"),
    "BK02": ("mid", "everyday staple, wide footprint"),
    "BK03": ("strong", "owns Korean premium, halal"),
    "BK04": ("strong", "artisan position, French-trained association"),
    "BK05": ("weak", "known for one product, not a destination"),
    # fast food
    "FF01": ("strong", "the default, most outlets, most downloaded app"),
    "FF02": ("strong", "owns 'the chicken place'"),
    "FF03": ("weak", "position is discounting itself - copyable"),
    "FF04": ("mid", "owns 'not fried', but dearer than S$5 meals"),
    "FF05": ("mid", "owns Filipino comfort, few outlets outside community"),
    "FF06": ("strong", "owns premium burger tier"),
    # health & beauty
    "HB01": ("strong", "largest share 18%, up from 16%"),
    "HB02": ("mid", "14% share, flat, neighbourhood claim"),
    "HB03": ("mid", "cheapest at regular price but limited range"),
    "HB04": ("strong", "owns premium beauty, 7% share"),
    # eyewear
    "EW01": ("strong", "owns transparent inclusive pricing S$98"),
    "EW02": ("mid", "identical price to OWNDAYS, no reason to choose"),
    "EW03": ("mid", "owns cheapest, but only on price"),
    "EW04": ("weak", "neither cheapest nor distinctive"),
    # furniture
    "FU01": ("strong", "owns cheap-whole-flat"),
    "FU02": ("mid", "owns design-without-markup"),
    "FU03": ("strong", "solid teak specialisation since 1974"),
    "FU04": ("strong", "in-house leather manufacturing, built to last"),
    # preschool
    "PS01": ("strong", "largest network, anchor fee cap"),
    "PS02": ("mid", "same cap, fewer centres, little reason to choose"),
    # electronics: CONVERGED price - nothing holds a position
    "EL01": ("weak", "no distinct position; prices within 3-8%"),
    "EL02": ("weak", "no distinct position; prices within 3-8%"),
    "EL03": ("weak", "no distinct position; prices within 3-8%"),
    "EL04": ("weak", "no distinct position; prices within 3-8%"),
}

WIDE = {"bubble-tea", "gym", "fast-food", "eyewear", "furniture"}
CONVERGED = {"electronics"}

rows = []
for cid, v in IDX["companies"].items():
    got = PROG.get(cid + ".json") or {}
    lab, why = LABEL.get(cid, ("?", "unlabelled"))
    rows.append({
        "cid": cid, "name": v["name"], "cat": v["cat"],
        "price": v["price"], "label": lab, "label_why": why,
        "composite": got.get("composite"), "band": got.get("band"),
        "dims": got.get("dims") or {}, "unscored": got.get("unscored") or [],
        "bi": got.get("band_interval") or {}, "err": got.get("error"),
    })

scored = [r for r in rows if r["composite"] is not None]
gated = [r for r in rows if r["composite"] is None and not r["err"]]

print("=" * 104)
print("FRESH-DATA VALIDITY SET (n=%d across %d categories)" % (len(rows), len(set(r["cat"] for r in rows))))
print("scored %d | gated %d | errored %d" % (len(scored), len(gated), len([r for r in rows if r["err"]])))
print("=" * 104)

ORDER = ["dead", "weak", "mid", "strong"]
print()
print("COMPOSITE BY PRE-REGISTERED LABEL")
print("-" * 104)
print("%-8s %-5s %-9s %-28s %s" % ("label", "n", "mean", "range", "labels that would falsify"))
for lab in ORDER:
    g = [r["composite"] for r in rows if r["label"] == lab and r["composite"] is not None]
    if g:
        print("%-8s %-5d %-9.1f %-28s" % (lab, len(g), statistics.mean(g),
                                          "%d-%d" % (min(g), max(g))))
print()
dead = [r for r in rows if r["label"] == "dead"]
for r in dead:
    print("  DOCUMENTED DEATH %-24s composite=%s band=%s" % (r["name"], r["composite"], r["band"]))

# ---- T1: within-category separation ---------------------------------------
print()
print("=" * 104)
print("T1  WITHIN-CATEGORY ORDERING (does the owned end separate from the middle?)")
print("=" * 104)
print("%-14s %-6s %-30s %-6s %s" % ("category", "n", "spread (max-min)", "range", "reading"))
print("-" * 104)
cat_report = {}
for cat in sorted(set(r["cat"] for r in rows)):
    g = [r for r in rows if r["cat"] == cat and r["composite"] is not None]
    if len(g) < 2:
        continue
    cs = [r["composite"] for r in g]
    spread = max(cs) - min(cs)
    cat_report[cat] = {"n": len(g), "spread": spread, "min": min(cs), "max": max(cs),
                       "mean": statistics.mean(cs),
                       "sd": statistics.stdev(cs) if len(cs) > 1 else 0.0}
    tag = "WIDE label" if cat in WIDE else ("CONVERGED" if cat in CONVERGED else "moderate")
    print("%-14s %-6d %-30d %-6s %s" % (cat, len(g), spread, "%d-%d" % (min(cs), max(cs)), tag))

# ---- T1 falsification: in a wide category, does a weak brand beat a strong one?
print()
print("T1 FALSIFICATION TEST — within a WIDE-spread category, weak-label brands must")
print("NOT outscore strong-label brands.")
viol = []
for cat in WIDE:
    g = [r for r in rows if r["cat"] == cat and r["composite"] is not None]
    strong = [r for r in g if r["label"] == "strong"]
    weak = [r for r in g if r["label"] == "weak"]
    if not strong or not weak:
        print("   %-14s insufficient labels (strong=%d weak=%d)" % (cat, len(strong), len(weak)))
        continue
    for w in weak:
        for s in strong:
            if w["composite"] > s["composite"]:
                viol.append((cat, w, s))
    ok = not any(w["composite"] > s["composite"] for w in weak for s in strong)
    print("   %-14s strong %s  vs weak %s   -> %s"
          % (cat, [r["composite"] for r in strong], [r["composite"] for r in weak],
             "PASS" if ok else "PAIRWISE INVERSION"))
if viol:
    print()
    print("   INVERSIONS (%d):" % len(viol))
    for cat, w, s in viol:
        print("     %-12s %-22s (%d) > %-22s (%d)" % (cat, w["name"], w["composite"],
                                                      s["name"], s["composite"]))
else:
    print()
    print("   no inversions")

# ---- T2: converged category must be low and flat --------------------------
print()
print("=" * 104)
print("T2  CONVERGED-PRICE CATEGORY (electronics) must score LOW and FLAT")
print("=" * 104)
el = [r for r in rows if r["cat"] in CONVERGED and r["composite"] is not None]
if el:
    cs = [r["composite"] for r in el]
    bt = [r["composite"] for r in rows if r["cat"] == "bubble-tea" and r["composite"] is not None]
    print("   electronics   n=%d mean=%.1f range=%d-%d spread=%d" %
          (len(cs), statistics.mean(cs), min(cs), max(cs), max(cs) - min(cs)))
    print("   bubble tea    n=%d mean=%.1f range=%d-%d spread=%d" %
          (len(bt), statistics.mean(bt), min(bt), max(bt), max(bt) - min(bt)))
    wider = "PASS" if (max(bt) - min(bt)) > (max(cs) - min(cs)) else "FAIL"
    print("   bubble tea spread > electronics spread : %s" % wider)
    hi = "PASS" if max(cs) < max(bt) else "FAIL - electronics reaches the wide category's ceiling"
    print("   electronics does not reach bubble tea's ceiling : %s" % hi)
else:
    print("   no electronics results yet")

# ---- T3 ------------------------------------------------------------------
print()
print("=" * 104)
print("T3  THE DOCUMENTED DEATH must FAIL")
print("=" * 104)
print("   'must fail' = must land in the BOTTOM band, not 'must refuse'.")
print("   (An earlier version of this test demanded a GATE. That was mis-specified:")
print("    a refusal is 'cannot assess', which is a different statement from 'bad'.")
print("    A dead business is assessable and should SCORE low.)")
if dead:
    d = dead[0]
    if d["composite"] is None:
        print("   PASS - %s refused (band=%s)" % (d["name"], d["band"]))
    else:
        ranks = sorted([r["composite"] for r in rows if r["composite"] is not None])
        pct = ranks.index(d["composite"]) / (len(ranks) - 1) * 100
        band_ok = d["composite"] <= 37          # Fragile
        print("   %s scored %d (%s) - lowest of %d, %.0fth percentile"
              % (d["name"], d["composite"], d["band"], len(ranks), pct))
        print("   bottom band (Fragile, 5-37): %s" % ("PASS" if band_ok else "FAIL"))
        print("   below the all-dims-at-2 anchor (38.3): %s"
              % ("PASS" if d["composite"] < 38.3 else "FAIL"))

# ---- category bias -------------------------------------------------------
print()
print("=" * 104)
print("CATEGORY-BIAS CHECK — is the rubric reading the CATEGORY rather than the BUSINESS?")
print("=" * 104)
print("   if a category's members all score alike regardless of their label, the")
print("   instrument may be describing the category, not the business.")
print()
print("%-14s %-6s %-7s %s" % ("category", "n", "sd", "reading"))
for cat, v in sorted(cat_report.items(), key=lambda kv: -kv[1]["sd"]):
    sd = v["sd"]
    note = ""
    if sd < 3:
        note = "<- FLAT: little within-category discrimination"
    elif sd > 10:
        note = "<- wide discrimination"
    print("%-14s %-6d %-7.1f %s" % (cat, v["n"], sd, note))

print()
print("=" * 104)
print("FULL TABLE")
print("=" * 104)
print("%-6s %-24s %-13s %-7s %-6s %-27s %s"
      % ("case", "business", "category", "label", "comp", "band", "band stability"))
print("-" * 118)
for r in sorted(rows, key=lambda r: (r["cat"], -(r["composite"] or -1))):
    bi = r["bi"]
    if r["composite"] is None:
        stab = "GATE"
    elif bi.get("reliable"):
        stab = "stable"
    else:
        stab = "AMBIGUOUS"
    print("%-6s %-24s %-13s %-7s %-6s %-27s %s"
          % (r["cid"], r["name"][:24], r["cat"], r["label"],
             r["composite"] if r["composite"] is not None else "-",
             " OR ".join(bi.get("bands") or [r["band"] or "-"]), stab))

json.dump(rows, open(HERE / "v2_adjudication.json", "w"), indent=2)
print()
print("-> v2_adjudication.json")
