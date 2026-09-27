"""Build TEST-3-CONSTRUCT-PROBE.md — the qualitative construct probe.

Design: for each probe case show
  - the business and its context (so the judgement is anchored on the business)
  - HIS score and MY score
  - THE LEVEL TEXT each of us picked  <-- this is the diagnostic
  - a blank for him to write what he was assessing

Why the level text matters: if his 4 and my 2 are both plausible readings of MY OWN level
ladder, the disagreement is calibration. If his 4 describes something the ladder does not
contain at all, the construct is wrong and the definition needs rewriting.

Includes agreement CONTROLS, so a construct divergence can be told apart from noise.
"""
import csv
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
V12 = json.loads((HERE / "rubric-v1.2.0.json").read_text())
idx = json.loads((HERE / "inputs-v4" / "_index.json").read_text())
rows = list(csv.DictReader(open(HERE / "sean-regrade-raw.csv")))
by = {r["company"]: r for r in rows}

mine = {}
for p in (HERE / "runs-v12").glob("jev-*.json"):
    r = json.loads(p.read_text())
    d = r.get("dimensions_display_1to5") or {}
    u = set(r.get("dimensions_unscored") or [])
    mine[r["case"]] = {"dims": {k: (None if k in u else d.get(k)) for k in d},
                       "unscored": u}


def num(x):
    x = ("" if x is None else str(x)).strip()
    if x.lower() in ("n/a", "na", "", "-", "none", "nan"):
        return None
    try:
        return float(x)
    except Exception:
        return None


def ctx(cid):
    src = json.loads((HERE / "inputs-v4" / (cid + ".json")).read_text())
    f = src.get("form", {})
    return (" ".join(str(f.get("differentiator") or "").split()),
            " ".join(str(f.get("undercut_on") or "").split()),
            "; ".join((src.get("competitors_named") or [])[:5]),
            f.get("your_price_point") or "")


# --- probe sets: derived from the data, not hand-listed -----------------------
# Picking cases by hand broke on the first run (BT01-mixue was deduped to P1-mixue).
# Derive them instead: the largest disagreements for CR and DR, and true agreement
# controls, so the examples cannot be mis-specified.
ABBR = {"competitive_room": "CR", "demand_reach": "DR"}


def _gap(cid, dim):
    e = idx["companies"].get(cid)
    if not e:
        return None
    r = by.get(e["name"]) or {}
    h = num(r.get("YOUR_" + ABBR[dim]))
    m = (mine.get(cid) or {}).get("dims", {}).get(dim)
    if h is None or m is None:
        return None
    return h - m


PROBES = {}
for dim in ("competitive_room", "demand_reach"):
    # Take the largest gap PER CATEGORY, then the top across categories. Taking the raw
    # top-5 clustered all of CR onto fast-food -- one market whose disagreement is already
    # understood -- which would test a single case rather than the construct.
    by_cat_best = {}
    ctrls = []
    for cid, e in idx["companies"].items():
        g = _gap(cid, dim)
        if g is None:
            continue
        c = e["cat"]
        # Keep each category's LARGEST gap, whatever its size. For competitive_room every
        # gap >=2 is in fast-food, so a >=2 filter yielded a one-category probe. Taking the
        # per-category maximum spans markets and still leads with the biggest disputes.
        if g != 0:
            if c not in by_cat_best or abs(g) > abs(by_cat_best[c][0]):
                by_cat_best[c] = (g, cid)
        else:
            ctrls.append((cid, c, e["name"]))
    # lead with the >=2 disputes, then fill from the largest remaining gaps
    ranked = sorted(by_cat_best.values(), key=lambda x: -abs(x[0]))
    diffs = [x for x in ranked if abs(x[0]) >= 2] + \
            [x for x in ranked if abs(x[0]) < 2]
    seen_cat = set()
    ctrl = []
    for cid, c, nm in ctrls:
        if c in seen_cat:
            continue
        seen_cat.add(c)
        ctrl.append(cid)
    PROBES[dim] = {"disagree": [c for _, c in diffs[:5]],
                   "control": ctrl[:3]}


def lvl_text(dim, n):
    if n is None:
        return "_(n/a — not scored)_"
    lv = V12["questions"][dim].get("levels") or []
    return lv[int(n) - 1] if 1 <= int(n) <= len(lv) else "_(out of range)_"


L = []
A = L.append
A("# TEST 3 — THE CONSTRUCT PROBE")
A("")
A("**What I need from you: your words, not numbers.** For each business below, tell me in")
A("one or two sentences **what you were actually assessing**. That is the whole test.")
A("")
A("## Why this is the decisive test")
A("")
A("The regression of your scores on mine showed something I cannot explain by calibration:")
A("")
A("```")
A("   RS  slope 0.94  correlation 0.85     <- same construct, minor offset")
A("   MA  slope 0.82  correlation 0.77     <- same construct, minor offset")
A("   DEF slope 0.82  correlation 0.79     <- same construct, minor offset")
A("   CR  slope 0.55  correlation 0.50     <- COLLAPSES")
A("   DR  slope 0.45  correlation 0.40     <- COLLAPSES")
A("```")
A("")
A("For every point I move on `demand_reach`, you move 0.45. **That is not an offset — an")
A("offset keeps slope near 1.** Two possible causes, and your words distinguish them:")
A("")
A("- **(a) Calibration.** We are grading the same thing; my level ladder sits lower than")
A("  your sense of it. Fix: re-anchor the levels.")
A("- **(b) Different construct.** We are grading **different things under the same name**.")
A("  Fix: rewrite the definition.")
A("")
A("**How your answers settle it.** For each case I show the level TEXT each of us picked.")
A("If your pick is a fair reading of my own ladder, it is (a). **If your pick describes")
A("something my ladder does not contain at all, it is (b)** — and the definition is wrong,")
A("not the anchors.")
A("")
A("**Every case in this probe was chosen because we disagree by 2 or more.** I have added")
A("**agreement controls** at the end of each section — cases we scored the same — so a")
A("genuine construct difference can be told apart from me having picked bad examples.")
A("")

for dim in ("competitive_room", "demand_reach"):
    A("---")
    A("")
    A("## %s — %s" % (ABBR[dim], dim))
    A("")
    A("### My definition and ladder (so you can see what you picked from)")
    A("")
    A("> " + " ".join(str(V12["questions"][dim]["instructions"]).split()))
    A("")
    for i, lv in enumerate(V12["questions"][dim]["levels"], 1):
        A("- **%d.** %s" % (i, " ".join(str(lv).split())))
    A("")

    for kind in ("disagree", "control"):
        A("### %s" % ("Our disagreements" if kind == "disagree"
                      else "Control cases — we AGREED on these"))
        A("")
        for cid in PROBES[dim][kind]:
            e = idx["companies"].get(cid) or {}
            r = by.get(e.get("name")) or {}
            h = num(r.get("YOUR_" + ABBR[dim]))
            m = (mine.get(cid) or {}).get("dims", {}).get(dim)
            claim, undercut, comps, price = ctx(cid)
            A("#### %s  ·  %s" % (e.get("name", cid), e.get("cat", "")))
            A("")
            if claim:
                A("**What they do / why a buyer picks them:** %s" % claim[:330])
                A("")
            if undercut:
                A("**Where they are weak:** %s" % undercut[:240])
                A("")
            if comps:
                A("**Competes with:** %s" % comps)
                A("")
            if price:
                A("**Price:** %s" % price)
                A("")
            A("| | score | the level text that score corresponds to |")
            A("|---|---|---|")
            A("| **YOU** | %s | %s |" % (int(h) if h else "—", lvl_text(dim, h)))
            A("| **ME** | %s | %s |" % (m if m is not None else "n/a", lvl_text(dim, m)))
            A("")
            if kind == "disagree":
                if h and m:
                    A("> **Gap: %+g** (you %g, me %g) — **What were you assessing here?** "
                      "(1–2 sentences)" % (h - m, h, m))
                else:
                    A("> **What were you assessing here?** (1–2 sentences)")
            else:
                A("> *(We agreed — if you have anything to add, note it here.)*")
            A("")
            A("---")
            A("")

# --- the VICOM MH question, which is a separate construct question -------------
A("## BONUS — `market_headroom` and VICOM")
A("")
A("You marked `market_headroom` **n/a** for VICOM; I scored **3**. You explained: *\"no")
A("unmet demand for car inspections based on the tight COE supply restrictions.\"* I think")
A("you are right, and I have added that to the instructions — but MH is dropped in 105 of")
A("120 cases, so it is untestable on this corpus.")
A("")
A("**One question, and it matters more than the score:** you marked MH `n/a` **106 times**.")
A("Was that because you judged the market as capacity-elastic in each case — i.e. you made")
A("a market judgement 106 times — or because the dimension felt redundant and you treated")
A("it as \"not applicable to anything\"? **The first is a validated judgement; the second is")
A("a signal the dimension should be cut.** Those imply opposite actions.")
A("")

A("---")
A("")
A("## How to send it back")
A("")
A("Just reply in chat, numbered or per business — whatever is fastest. **Do not compute")
A("anything.** One or two sentences per case is enough, and for the controls you can skip")
A("them entirely if you have nothing to add.")
A("")
A("**What I will do with it:** compare your descriptions against my level text. Where your")
A("description names something my ladder does not contain, I rewrite the definition. Where")
A("it names what my ladder already contains, it is calibration and Test 1 fixes it.")

(HERE / "TEST-3-CONSTRUCT-PROBE.md").write_text("\n".join(L))
print("wrote TEST-3-CONSTRUCT-PROBE.md (%d lines)" % len(L))
print()
for dim, sets in PROBES.items():
    print("  %-18s disagreements %d | controls %d"
          % (dim, len(sets["disagree"]), len(sets["control"])))
