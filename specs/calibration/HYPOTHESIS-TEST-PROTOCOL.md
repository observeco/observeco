# HYPOTHESIS-TEST PROTOCOL — separating the three explanations

**Purpose.** The v1.2.0 result: fixing the `defensibility` wording halved disputes on
that dimension (14% → 7%) but **45 cases still differ by ≥2**. Before changing any more
wording I need to know *why* we disagree. There are three candidate explanations and
they need different fixes — and two of them need no further grading from you at all.

---

## What the existing data already tells us

**Regression of your score on mine — `his = a + b × mine` (v1.2.0):**

| dim | n | slope b | intercept a | r | verdict |
|---|---|---|---|---|---|
| RS | 120 | 0.94 | +0.46 | **0.85** | same construct, small offset |
| MA | 120 | 0.82 | +0.94 | **0.77** | same construct, small offset |
| DEF | 120 | 0.82 | +0.62 | **0.79** | same construct, small offset |
| CR | 119 | **0.55** | +1.31 | **0.50** | **weak — possibly a different construct** |
| DR | 113 | **0.45** | +2.18 | **0.40** | **weak — possibly a different construct** |
| MH | 5 | — | — | — | too few scored to say |

**This changes the diagnosis.** A level shift would show the SAME slope (≈1) on every
dimension with a positive intercept. Instead the slope collapses on CR and DR:
**for every point I move on `demand_reach`, you move only 0.45.** That is not an offset,
it is a different construct. RS, MA and DEF behave as the offset hypothesis predicts.

## The three hypotheses, and the fix each implies

| # | Hypothesis | Signature | Fix if true |
|---|---|---|---|
| **H-A** | You grade ABSOLUTE ('how good is this business?'); my scale asks 'compared with WHAT?' | similar slope, offset largest on the dimensions whose wording demands the most benchmark-holding | reword the instructions to state the comparison more explicitly |
| **H-B** | Same frame, but my level LADDER is calibrated too low | your picks reproduce my numbers when you place businesses on *my* level text | re-anchor the levels; your scores are the corrected ones |
| **H-C** | For CR and DR we are measuring DIFFERENT CONSTRUCTS | slope ≪ 1 and low correlation on those two only | rewrite those two definitions, not their anchors |

**The data already points at H-C for CR and DR** (slope 0.55 / 0.45, r 0.50 / 0.40 vs
0.77–0.85 elsewhere). H-A is weakly supported: the mean offset is **+0.32 on the three
benchmark-heavy dimensions** (MA/RS/DEF) against **+0.01 on the two market dimensions**
(CR/MH) — the ordering H-A predicts, though n=5 dimensions is thin evidence.

## A confound that affects everything, and must be resolved first

**You had my scores visible in the adjacent column, and you copied my composite in 59
of 61 filled rows.** So the column was being read. Your *dimension* scores have their own
distributions (so they were not copied), but they could still have been **influenced**.

I tested for the anchoring signature (agreement should improve at the extremes of my own
distribution if you were being pulled toward my values): **correlation +0.13, no
signature found.** But that test is weak, and the zero-difference categories it produced
(electronics, eyewear, furniture) are explained by both of us scoring them uniformly —
not by agreement. **So the confound is unresolved, and Test 2 below is what settles it.**

---

## TEST 1 — The anchor map  (settles H-B) · 10 businesses · ~15 min

**Method.** You see the five level texts for one dimension at a time, plus a business
with its context. You pick the level that describes it. No numbers, no reference column.

**This is the decisive test for H-B.** If you place businesses on my level text and the
result reproduces my numbers, my anchors are correct and H-B is dead. If you
systematically pick one level higher, the anchors are too low and **your scores are the
corrected ones** — the fix is to re-write the level ladder, not the instructions.

The businesses below span my range and their positions are **externally verifiable**,
which is what makes the comparison meaningful rather than a matter of taste.

### RS — level texts

> Judge ONLY relative strength: how strong is this business's CURRENT POSITION against the competitors in its DERIVED COMPETITIVE SET? The yardstick is the NAMED occupants of that set -- not the market in general, not a hypothetical rival, and not a business of the same size. First establish the buying situations in the category and the derived competitive set. Then, for each, ask where this business ACTUALLY STANDS against those specific occupants: share of the occasions, footprint (outlets, coverage, catchment), price position, and any documented buyer preference. Judge the OBSERVED standing on published or stated evidence -- never the business's own claim about itself, and never size alone,

- **1.** Absent from the set. It does not hold a position against the named occupants at all -- it is not a factor buyers weigh for any situation in this category.
- **2.** Marginal. Present but weaker than almost every occupant of the set; a fringe or declining option that holds no situation against those specific rivals.
- **3.** At parity. Holds its position at roughly the level of the median occupant of the set; no clear advantage or disadvantage against those specific rivals.
- **4.** Strong. Holds one or more situations more firmly than most occupants of the set; ranked near the top of its derived set on footprint, preference or price position.
- **5.** Dominant. The clear leader within its derived set on the situations that matter -- the reference point the other occupants position themselves against.

### MA — level texts

> Judge ONLY mental advantage: among the buyers this business can ACTUALLY SERVE, how strongly is it retrieved when a buying occasion fires? First establish the ADDRESSABLE SEGMENT -- the buyers within this business's realistic reach given its size and footprint. A home baker's addressable segment is its estate, not the island; a national chain's is the island. Then, for each buying situation inside that segment, ask whether this business is the one that comes to mind, and how firmly. This is RELATIVE TO THE ADDRESSABLE SEGMENT, never absolute: a large brand holding its segment against expected erosion is an advantage, and a tiny business owning an occasion across its segment is also an advant

- **1.** Not retrieved. Within its addressable segment it is not a first thought for any buying occasion, and is barely recognised as an option at all.
- **2.** Weakly present. Known inside the segment but retrieved for no occasion more than any other option; an also-ran that buyers would accept but never seek.
- **3.** At expectation for the segment. Retrieved for its occasions at roughly the level a business of its reach would be expected to achieve; neither advantaged nor disadvantaged.
- **4.** Strong retrieval. The first or near-first thought within its addressable segment for one or more valuable, frequently-occurring buying occasions.
- **5.** Owns the segment. The default first thought within its addressable segment for one or more valuable occasions, and rivals are not close on those occasions.

### DEF — level texts

> Judge ONLY defensibility: how DURABLE is this business's position -- how long would it take a well-resourced competitor to take it from them, and what obstructs the attempt? This is the DURABILITY of the position that relative_strength describes, NOT a second measure of the position itself. Distinguish two things carefully. (1) EFFORT THE FOUNDER SPENT -- 'we worked hard', 'we have been going for years', 'we care more' -- earns nothing on its own; how hard something was to build is not what makes it hard to take. (2) ACCUMULATED BARRIERS -- assets a challenger cannot cheaply assemble: scale built over decades (a store network, a distribution system, a supply chain), a brand sustained by heav

- **1.** No moat. Nothing obstructs a challenger. There is no differentiator at all, or the one claimed is a purchasable input any competitor can relabel this quarter.
- **2.** Shallow. A competitor can copy it in weeks by buying the same thing -- a claim, a message, an off-the-shelf ingredient, a standard fit-out. No accumulated barrier.
- **3.** Replicable. A competitor must do real work of their own, but nothing obstructs them beyond the cost of doing it: the approach is visible and a committed challenger gets there in months, not years.
- **4.** Protected. A genuine accumulated barrier a challenger cannot cheaply assemble: scale built over years (a store network, distribution, supply chain), a brand sustained by heavy long-term spending, an owned channel, a proprietary dataset, accumulated trust, a patent or trade secret, an exclusive supply arrangement, or a licence. Taking the position means years and substantial capital, not months.
- **5.** Durable. The barrier would take a well-resourced challenger a decade or more, or requires assets they cannot assemble at all -- a national network, decades of accumulated trust, an exclusive relationship or licence, a dataset nobody else holds.
- **6.** Compounding. Several barriers reinforce each other, so that even a well-funded challenger given time could not replicate the position.

### CR — level texts

> Judge ONLY competitive room: how much space does competition leave for this business to operate and earn? Higher means MORE room — a fragmented, uncontested market. Lower means less room — concentrated incumbents, price-driven commoditisation, or a floor price set by a much larger player. Assess concentration, the strength of the named competitors, and whether the market competes primarily on price. Do not consider the business's own positioning or quality.

- **1.** No room. Dominated by concentrated incumbents, competing almost entirely on price, with no viable margin left.
- **2.** Very little. A dominant player or a severe price floor; the business is structurally squeezed.
- **3.** Some. Crowded and price-contested, but gaps exist for a small operator.
- **4.** Good. Competitive but fragmented; several players coexist without a single dominant one crushing the rest.
- **5.** Strong. Uncontested, fragmented, with no dominant player and no established price floor.

### MH — level texts

> Judge ONLY market headroom: is there more DEMAND in this category than is currently being SERVED? Judge whether buyers are getting what they need, or whether demand is going unmet -- people waiting, being rationed, turned away, going without, or paying inflated prices because supply cannot keep up. Do NOT judge how crowded the category is, and do NOT judge whether a new entrant would be welcomed; those are separate questions. WHERE DEMAND IS ITSELF CAPPED BY REGULATION there is no unmet demand to serve, however necessary the service: if a rule limits how many buyers can exist -- for example vehicle inspections, where the COE system caps the number of vehicles that can be registered -- then s

- **1.** No demand. There is no identifiable buying demand for this category at all.
- **2.** Demand is served. Buyers can get this easily; supply meets or exceeds what is wanted, and the category is flat or shrinking.
- **3.** Demand is met, contested. Real, steady demand, but supply already satisfies it -- a new entrant must take share from an incumbent rather than serve unmet need.
- **4.** Demand exceeds supply. Buyers wait, are rationed, or pay inflated prices because supply cannot keep up, and the shortfall is growing.
- **5.** Demand far exceeds supply. The category cannot serve the demand that exists; buyers are allocated, queued or going without, and the constraint is the binding limit on the whole market.

### DR — level texts

> Judge ONLY demand reach: is there an identifiable, reachable group of buyers who would pay for this, and can this business find them? Higher means more reachable. Consider whether the customer is described in a way that identifies a real group with a trigger to buy, whether that group is concentrated somewhere the business can reach it, and whether it is willing to pay the stated price. A demographic such as an age band is NOT a reachable segment on its own. Do not consider whether the market is large.

- **1.** No identifiable buyer. The customer is undefined, or defined so broadly no one can be targeted.
- **2.** Weak. Only a demographic is named; no trigger, no channel, and no evidence they will pay this price.
- **3.** Moderate. A describable segment with a plausible trigger, but no established route to reach them.
- **4.** Good. A clearly identified segment with a trigger and at least one credible channel to reach it.
- **5.** Strong. A tightly defined, concentrated, paying segment that the business can reach directly and cheaply.

### The 10 anchor businesses

| # | Business | Why its position is externally checkable |
|---|---|---|
| 1 | Gong Cha Singapore — shut all 29 SG outlets Oct 2025 | — |
| 2 | A closed bubble tea outlet — single mall unit, now shut | — |
| 3 | A home catering service — statute forbids catering from HDB | — |
| 4 | Tee (DOT) Nail Bar — a small home nail studio | — |
| 5 | True Fitness — 14 clubs, collapsed | — |
| 6 | KOI Thé — 88-90 outlets, category leader | — |
| 7 | McDonald's Singapore — 150+ outlets, market leader | — |
| 8 | ASML — the only supplier of EUV lithography machines | — |
| 9 | Hill Street Tai Hwa — one hawker stall, MICHELIN star | — |
| 10 | IKEA Singapore — 3 stores, category-defining | — |

**What to send back:** for each of the 10, a number 1–5 (1–6 for DEF) per dimension.
If a business cannot be judged on a dimension, write `n/a`. **Do not consult my column** —
I will not show it until you have finished.

---

## TEST 2 — Blind scoring on FRESH businesses  (settles anchoring + H-A) · 40 businesses · ~60 min

**Why fresh businesses.** You have now seen all 120. A blind re-run on those is
contaminated by memory, so this test uses businesses **not in the corpus**.

**Method.** 40 businesses, chosen across the same product categories, scored with **only
the definitions — no reference column, no my-scores, no old scores.**

**What it settles, in order of importance:**

1. **Anchoring.** Your new scores vs your old scores on comparable businesses. If they
   match, your grading is stable and the differences from me are real. If they move
   toward mine, the first pass was anchored and every agreement figure to date is
   contaminated — that would be the single most important finding in the project.
2. **H-A.** Your new scores vs mine, with no visual anchor. The cleanest available
   comparison of frames.
3. **Reliability.** How stable your own judgement is across presentations. My own
   instrument is only ~0/10 exact on duplicate presentations; your first pass was 6/7.

**Honest power limit.** n=40 estimates the slope to roughly ±0.15, enough to see whether
a dimension's slope is near 1 or near 0.5 — the distinction that matters. It is **not**
enough to resolve a 0.2-point offset. If we need that, it takes n≈60 per the power
calculation, and I would say so before you spend the time.

---

## TEST 3 — The construct probe  (settles H-C) · 6 businesses · ~20 min, written

**This is the test the data most strongly calls for**, and it is qualitative — no numbers.

**Method.** I give you the cases where we differ most on `competitive_room` and
`demand_reach`, and you write one or two sentences on **what you were assessing**. I then
compare your account against my level text.

**If your account describes a different thing than my levels do, the definition is wrong**
and gets rewritten. If it describes the same thing, the disagreement is calibration and
Test 1 handles it.

The pairs I would use, chosen because we disagree maximally and the market is knowable:

### CR

| Business | Your score | My score | Question |
|---|---|---|---|
| McDonald's Singapore | 4.0 | 2 | *In one or two sentences: what were you assessing here?* |
| Burger King Singapore | 4.0 | 2 | *In one or two sentences: what were you assessing here?* |
| IKEA Singapore | 3.0 | 2 | *In one or two sentences: what were you assessing here?* |
| Courts Singapore | 2.0 | 2 | *In one or two sentences: what were you assessing here?* |

### DR

| Business | Your score | My score | Question |
|---|---|---|---|
| Harvey Norman Singapore | 5.0 | 2 | *In one or two sentences: what were you assessing here?* |
| Best Denki Singapore | 5.0 | 2 | *In one or two sentences: what were you assessing here?* |
| BreadTalk | 5.0 | 3 | *In one or two sentences: what were you assessing here?* |

---

## What I do with each outcome

| Result | Action |
|---|---|
| Test 1 reproduces my numbers | anchors are correct; H-B dead; the fix is instructions, not levels |
| Test 1 is systematically one higher | **my anchors are too low**; rewrite the level ladders using your placements as the reference |
| Test 2 ≈ your old scores | your grading is stable; the disagreement is genuine and between us |
| Test 2 moves toward mine | **everything measured so far is contaminated** — rebuild the comparison blind |
| Test 3 describes a different construct | rewrite that definition; the slope collapse is the proof |
| Test 3 describes the same construct | it is a calibration problem; Test 1 fixes it |

## Order, and why

**Run Test 3 first** (~20 min). It is the cheapest and the data points at it hardest —
the slope collapse on CR and DR is the largest unexplained effect in the corpus.
**Then Test 1** (~15 min) — it is 10 businesses and it kills or confirms H-B outright.
**Then Test 2** (~60 min) only if 1 and 3 leave the frame question open. Test 2 is the
expensive one and it is the least likely to change the build.

**Total for 1 and 3: about 35 minutes, and between them they resolve the two hypotheses
the evidence supports.** I would not spend the 60 minutes on Test 2 until we see those.