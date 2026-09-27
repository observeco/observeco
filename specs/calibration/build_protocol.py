"""Generate HYPOTHESIS-TEST-PROTOCOL.md — three tests that separate the competing
explanations for the remaining disagreement, each isolating ONE thing.

The tests are designed around what the existing data already showed:
  - Test 1 (regression shape) found the gap is NOT a uniform shift: slopes are b<1 on
    CR (0.55) and DR (0.45), meaning those two have WEAK correlation with mine
    (r ~ 0.50 and 0.40) while RS/MA/DEF are strong (r 0.85 / 0.77 / 0.79).
  - So there is a THIRD hypothesis the original two did not cover: for CR and DR we may
    be measuring different constructs, not the same construct at different anchor points.
"""
import csv
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
V12 = json.loads((HERE / "rubric-v1.2.0.json").read_text())
DIMS = ["relative_strength", "mental_advantage", "defensibility",
        "competitive_room", "market_headroom", "demand_reach"]
ABBR = {"relative_strength": "RS", "mental_advantage": "MA", "defensibility": "DEF",
        "competitive_room": "CR", "market_headroom": "MH", "demand_reach": "DR"}

# cases spanning my scale for the anchor map, chosen for EXTERNALLY VERIFIABLE position
ANCHOR_CASES = [
    ("P5-gongcha", "Gong Cha Singapore — shut all 29 SG outlets Oct 2025"),
    ("N1-closedbusiness", "A closed bubble tea outlet — single mall unit, now shut"),
    ("NP03-a", "A home catering service — statute forbids catering from HDB"),
    ("HN01-tee", "Tee (DOT) Nail Bar — a small home nail studio"),
    ("GY07-true", "True Fitness — 14 clubs, collapsed"),
    ("BT02-koi", "KOI Thé — 88-90 outlets, category leader"),
    ("FF01-mcdonalds", "McDonald's Singapore — 150+ outlets, market leader"),
    ("E1-asml", "ASML — the only supplier of EUV lithography machines"),
    ("C5-michelin-hawker", "Hill Street Tai Hwa — one hawker stall, MICHELIN star"),
    ("FU01-ikea", "IKEA Singapore — 3 stores, category-defining"),
]

idx = json.loads((HERE / "inputs-v4" / "_index.json").read_text())
rows = list(csv.DictReader(open(HERE / "sean-regrade-raw.csv")))
by = {r["company"]: r for r in rows}

mine = {}
for p in (HERE / "runs-v12").glob("jev-*.json"):
    r = json.loads(p.read_text())
    d = r.get("dimensions_display_1to5") or {}
    u = set(r.get("dimensions_unscored") or [])
    mine[r["case"]] = {k: (None if k in u else d.get(k)) for k in DIMS}

L = []
A = L.append
A("# HYPOTHESIS-TEST PROTOCOL — separating the three explanations")
A("")
A("**Purpose.** The v1.2.0 result: fixing the `defensibility` wording halved disputes on")
A("that dimension (14% → 7%) but **45 cases still differ by ≥2**. Before changing any more")
A("wording I need to know *why* we disagree. There are three candidate explanations and")
A("they need different fixes — and two of them need no further grading from you at all.")
A("")
A("---")
A("")
A("## What the existing data already tells us")
A("")
A("**Regression of your score on mine — `his = a + b × mine` (v1.2.0):**")
A("")
A("| dim | n | slope b | intercept a | r | verdict |")
A("|---|---|---|---|---|---|")
A("| RS | 120 | 0.94 | +0.46 | **0.85** | same construct, small offset |")
A("| MA | 120 | 0.82 | +0.94 | **0.77** | same construct, small offset |")
A("| DEF | 120 | 0.82 | +0.62 | **0.79** | same construct, small offset |")
A("| CR | 119 | **0.55** | +1.31 | **0.50** | **weak — possibly a different construct** |")
A("| DR | 113 | **0.45** | +2.18 | **0.40** | **weak — possibly a different construct** |")
A("| MH | 5 | — | — | — | too few scored to say |")
A("")
A("**This changes the diagnosis.** A level shift would show the SAME slope (≈1) on every")
A("dimension with a positive intercept. Instead the slope collapses on CR and DR:")
A("**for every point I move on `demand_reach`, you move only 0.45.** That is not an offset,")
A("it is a different construct. RS, MA and DEF behave as the offset hypothesis predicts.")
A("")

A("## The three hypotheses, and the fix each implies")
A("")
A("| # | Hypothesis | Signature | Fix if true |")
A("|---|---|---|---|")
A("| **H-A** | You grade ABSOLUTE ('how good is this business?'); my scale asks 'compared with WHAT?' | similar slope, offset largest on the dimensions whose wording demands the most benchmark-holding | reword the instructions to state the comparison more explicitly |")
A("| **H-B** | Same frame, but my level LADDER is calibrated too low | your picks reproduce my numbers when you place businesses on *my* level text | re-anchor the levels; your scores are the corrected ones |")
A("| **H-C** | For CR and DR we are measuring DIFFERENT CONSTRUCTS | slope ≪ 1 and low correlation on those two only | rewrite those two definitions, not their anchors |")
A("")
A("**The data already points at H-C for CR and DR** (slope 0.55 / 0.45, r 0.50 / 0.40 vs")
A("0.77–0.85 elsewhere). H-A is weakly supported: the mean offset is **+0.32 on the three")
A("benchmark-heavy dimensions** (MA/RS/DEF) against **+0.01 on the two market dimensions**")
A("(CR/MH) — the ordering H-A predicts, though n=5 dimensions is thin evidence.")
A("")

A("## A confound that affects everything, and must be resolved first")
A("")
A("**You had my scores visible in the adjacent column, and you copied my composite in 59")
A("of 61 filled rows.** So the column was being read. Your *dimension* scores have their own")
A("distributions (so they were not copied), but they could still have been **influenced**.")
A("")
A("I tested for the anchoring signature (agreement should improve at the extremes of my own")
A("distribution if you were being pulled toward my values): **correlation +0.13, no")
A("signature found.** But that test is weak, and the zero-difference categories it produced")
A("(electronics, eyewear, furniture) are explained by both of us scoring them uniformly —")
A("not by agreement. **So the confound is unresolved, and Test 2 below is what settles it.**")
A("")

A("---")
A("")
A("## TEST 1 — The anchor map  (settles H-B) · 10 businesses · ~15 min")
A("")
A("**Method.** You see the five level texts for one dimension at a time, plus a business")
A("with its context. You pick the level that describes it. No numbers, no reference column.")
A("")
A("**This is the decisive test for H-B.** If you place businesses on my level text and the")
A("result reproduces my numbers, my anchors are correct and H-B is dead. If you")
A("systematically pick one level higher, the anchors are too low and **your scores are the")
A("corrected ones** — the fix is to re-write the level ladder, not the instructions.")
A("")
A("The businesses below span my range and their positions are **externally verifiable**,")
A("which is what makes the comparison meaningful rather than a matter of taste.")
A("")

for d in DIMS:
    q = V12["questions"][d]
    A("### %s — level texts" % ABBR[d])
    A("")
    A("> " + " ".join(str(q.get("instructions", "")).split())[:700])
    A("")
    for i, lv in enumerate(q.get("levels") or [], 1):
        A("- **%d.** %s" % (i, " ".join(str(lv).split())))
    A("")

A("### The 10 anchor businesses")
A("")
A("| # | Business | Why its position is externally checkable |")
A("|---|---|---|")
for i, (cid, why) in enumerate(ANCHOR_CASES, 1):
    A("| %d | %s | %s |" % (i, why, "—"))
A("")
A("**What to send back:** for each of the 10, a number 1–5 (1–6 for DEF) per dimension.")
A("If a business cannot be judged on a dimension, write `n/a`. **Do not consult my column** —")
A("I will not show it until you have finished.")
A("")

A("---")
A("")
A("## TEST 2 — Blind scoring on FRESH businesses  (settles anchoring + H-A) · 40 businesses · ~60 min")
A("")
A("**Why fresh businesses.** You have now seen all 120. A blind re-run on those is")
A("contaminated by memory, so this test uses businesses **not in the corpus**.")
A("")
A("**Method.** 40 businesses, chosen across the same product categories, scored with **only")
A("the definitions — no reference column, no my-scores, no old scores.**")
A("")
A("**What it settles, in order of importance:**")
A("")
A("1. **Anchoring.** Your new scores vs your old scores on comparable businesses. If they")
A("   match, your grading is stable and the differences from me are real. If they move")
A("   toward mine, the first pass was anchored and every agreement figure to date is")
A("   contaminated — that would be the single most important finding in the project.")
A("2. **H-A.** Your new scores vs mine, with no visual anchor. The cleanest available")
A("   comparison of frames.")
A("3. **Reliability.** How stable your own judgement is across presentations. My own")
A("   instrument is only ~0/10 exact on duplicate presentations; your first pass was 6/7.")
A("")
A("**Honest power limit.** n=40 estimates the slope to roughly ±0.15, enough to see whether")
A("a dimension's slope is near 1 or near 0.5 — the distinction that matters. It is **not**")
A("enough to resolve a 0.2-point offset. If we need that, it takes n≈60 per the power")
A("calculation, and I would say so before you spend the time.")
A("")

A("---")
A("")
A("## TEST 3 — The construct probe  (settles H-C) · 6 businesses · ~20 min, written")
A("")
A("**This is the test the data most strongly calls for**, and it is qualitative — no numbers.")
A("")
A("**Method.** I give you the cases where we differ most on `competitive_room` and")
A("`demand_reach`, and you write one or two sentences on **what you were assessing**. I then")
A("compare your account against my level text.")
A("")
A("**If your account describes a different thing than my levels do, the definition is wrong**")
A("and gets rewritten. If it describes the same thing, the disagreement is calibration and")
A("Test 1 handles it.")
A("")
A("The pairs I would use, chosen because we disagree maximally and the market is knowable:")
A("")

probe = {
    "competitive_room": ["FF01-mcdonalds", "FF03-burger", "FU01-ikea", "EL01-courts"],
    "demand_reach": ["EL02-harvey", "EL03-best", "BK01-breadtalk"],
}
for d, ids in probe.items():
    A("### %s" % ABBR[d])
    A("")
    A("| Business | Your score | My score | Question |")
    A("|---|---|---|---|")
    for cid in ids:
        e = idx["companies"].get(cid) or {}
        r = by.get(e.get("name")) or {}
        h = (r.get("YOUR_" + ABBR[d]) or "").strip()
        m = mine.get(cid, {}).get(d)
        A("| %s | %s | %s | *In one or two sentences: what were you assessing here?* |"
          % (e.get("name", cid), h or "—", m if m is not None else "n/a"))
    A("")

A("---")
A("")
A("## What I do with each outcome")
A("")
A("| Result | Action |")
A("|---|---|")
A("| Test 1 reproduces my numbers | anchors are correct; H-B dead; the fix is instructions, not levels |")
A("| Test 1 is systematically one higher | **my anchors are too low**; rewrite the level ladders using your placements as the reference |")
A("| Test 2 ≈ your old scores | your grading is stable; the disagreement is genuine and between us |")
A("| Test 2 moves toward mine | **everything measured so far is contaminated** — rebuild the comparison blind |")
A("| Test 3 describes a different construct | rewrite that definition; the slope collapse is the proof |")
A("| Test 3 describes the same construct | it is a calibration problem; Test 1 fixes it |")
A("")
A("## Order, and why")
A("")
A("**Run Test 3 first** (~20 min). It is the cheapest and the data points at it hardest —")
A("the slope collapse on CR and DR is the largest unexplained effect in the corpus.")
A("**Then Test 1** (~15 min) — it is 10 businesses and it kills or confirms H-B outright.")
A("**Then Test 2** (~60 min) only if 1 and 3 leave the frame question open. Test 2 is the")
A("expensive one and it is the least likely to change the build.")
A("")
A("**Total for 1 and 3: about 35 minutes, and between them they resolve the two hypotheses")
A("the evidence supports.** I would not spend the 60 minutes on Test 2 until we see those.")

(HERE / "HYPOTHESIS-TEST-PROTOCOL.md").write_text("\n".join(L))
print("wrote HYPOTHESIS-TEST-PROTOCOL.md (%d lines)" % len(L))
print()
print("Test 1: %d anchor businesses, 6 dimensions each" % len(ANCHOR_CASES))
print("Test 3: %d probe cases" % sum(len(v) for v in probe.values()))
