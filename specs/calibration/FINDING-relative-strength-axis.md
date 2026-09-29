# FINDING — the instrument has no relative-strength axis

**Trigger.** Sean: *"If my feedback to you is that what is missing is the exact's business
relative strong positioning to their current business landscape, and the overall score is
to judge whether the said business can be successful in penetrating the segment. how would
you go about revising our existing methodology?"*

This is a **coverage challenge** (SOUL Pattern 21), not a disagreement. The analysis missed
an axis. The missing axis was already implied by the original objective —
*"strength of positioning and differentiation relative to competition"* — and the
instrument never implemented the **relative to competition** half.

---

## The receipt

### 1. Every dimension's anchor, audited

| Dimension | Wt | Anchored against | Is that the competitive set? |
|---|---|---|---|
| mental_advantage | 25% | what a business **of this size** should own | **No** — size expectation |
| defensibility | 25% | a **hypothetical** well-resourced copier | **No** — a counterfactual |
| competitive_room | 20% | market **structure** | **No** — the landscape, not the business |
| market_headroom | 15% | category demand vs supply | **No** — the category |
| demand_reach | 15% | the business's **own** buyers | **No** — its own customers |

**No dimension compares this business with its named competitors.** "competitor" appears 20×
in the rubric, always as *context to assess*, never as the thing compared against.

### 2. competitive_room cannot rank rivals — structurally

Variance decomposition over the 107-case corpus (within-category vs between-category):

```
mental_advantage   within-category variance share  60.2%   constant in 3/17 categories
defensibility      within-category variance share  69.1%   constant in 3/16
demand_reach       within-category variance share  51.7%   constant in 1/16
competitive_room   within-category variance share  19.2%   constant in 11/17
market_headroom    (dropped in 113 of 126 scored cases)
```

Raw per-category values make it plain:

```
bakery       CR: [2,2,2,2,2]        electronics  CR: [2,2,2,2]
fast-food    CR: [2,2,2,2,2,2]      furniture    CR: [2,2,2,2]
gym          CR: [2,2,2,2,2,2,2]    supermarket  CR: [2,2,2,2,2]
home-nails   CR: [3,3,3,3,3,3,3,3,3,3,3,2,3,3,3,3,3]
```

A dimension that is **constant inside a category cannot change the order of that
category's members** — it shifts all of them equally. Verified: recomputing the composite
while dropping competitive_room leaves the **within-landscape order IDENTICAL in 9 of 15
categories**. 20% of declared weight is decorative for ranking purposes.

### 3. The anchor that breaks it: McDonald's vs Jollibee

Published facts (this session): **McDonald's Singapore: 150+ restaurants, "market leader in
the quick service restaurant industry", 70M customers/yr. Jollibee Singapore: 26 outlets.**

The rubric's answer:

```
FF01  McDonald's   47   MA=3 DEF=2 CR=2 DR=3
FF05  Jollibee     57   MA=4 DEF=2 CR=2 DR=4     <- 10 points ABOVE the market leader
```

A business with **5.8× the footprint** and the market-leader position scores **10 points
below** a challenger. Not a bug in the arithmetic — a consequence of the design:
MA *divides size out by construction*, CR is constant within the category, MH is dropped.
**The construct "relative strength in the landscape" has no representation anywhere.**

### 4. The composite is heavily quantised

126 scored cases produce **37 distinct composites**; **98 of 126 cases share their composite
with 3 or more others**. Inside a single landscape:

```
home-nails    17 cases -> 8 distinct scores  (9 tied positions)
home-facial    9 cases -> 5 distinct scores  (4 tied)
fast-food      6 cases -> 4 distinct scores  (2 tied)
electronics    4 cases -> 2 distinct scores  (2 tied)
```

So even where the composite is "right", it frequently **cannot separate two competitors**.

---

## The design revision

The reframe makes the composite a **penetration verdict**: can this business take position
in its segment? That requires the composite to be a **comparison**, not an absolute rating.

### The two constructs the redesign needs

**A. position_strength — NEW, and the axis that is missing.**
For each buying situation in the **derived** competitive set: what does this business hold
against the named occupants, and is the gap widening or closing? Anchored on published
facts — outlet counts, share, awards, price points. 3 = parity with the set median, 5 =
dominant, 1 = absent. This is the first dimension that can produce *"you sit 4th of 6 in
your category"*.

**B. The GAP between position_strength and mental_advantage is the product's core message.**
This is why MA should NOT simply be re-anchored to the set:

- `position_strength` = where you actually stand vs the set (honest; low for small
  businesses — and this is the gap the report names)
- `mental_advantage` (size-relative, unchanged) = whether you outperform what your size
  predicts (actionable; the ceiling you could grow into)

Read together they say something a lead magnet can actually sell: *"you are 2nd-tier in your
category, but you punch well above your weight — here is the position you could take."*
Collapsing them into one relative number destroys that message and makes every small
business read "you are weak", which is true, useless, and insulting.

### The structural change

**competitive_room must stop being a business score.** Its 19.2% within-category variance
share is measured, not argued: it describes the **landscape**, not the occupant. Options:

- **C1 — demote to a landscape modifier.** Keep the judgment, remove it from the composite;
  use it to set the scale of the verdict ("in a brutal landscape, a 60 is excellent"). Frees
  20% for position_strength without growing the instrument.
- **C2 — keep it scored, relabel honestly** as `competition_intensity`, and accept that it
  contributes only a per-category constant.
- **C3 — leave it.** Cheapest; 20% of weight stays decorative for ranking.

### What must NOT change

`defensibility` (69.1% within-share) and `demand_reach` (51.7%) genuinely vary between
rivals. They are doing real work and should survive the reframe untouched. `market_headroom`
needs a decision independent of this — it is dropped in 113 of 126 cases and is close to
inert (see `FINDING-display-floor.md`).

---

## The challenge I owe Sean

**"judge whether the said business can be successful in penetrating the segment" is a
PREDICTIVE claim, and this instrument has already failed one test of that kind.**

We measured that it does **not** separate a live business from a dead one on positioning
grounds: **Harvey Norman (live major retailer) 32 vs a closed bubble-tea outlet 31** — a
1-point gap. Adding position_strength makes the *state* description sharper. It does **not**
by itself establish that a high score predicts penetration *success*, which is a forward-
looking outcome claim needing outcome labels we do not have.

Two different claims, two different validations:

- **Positioning validity** — "does the score describe position relative to named rivals?"
  Testable **now** with published outlet counts / share / documented outcomes. 23 cases
  already carry such evidence.
- **Predictive validity** — "does a high score predict that the business succeeds?"
  Needs a longitudinal label (grew / held / closed over N years). We have 5 documented
  graduations and a handful of closures; that is not a base rate.

The honest instrument is a **position description**, not a success forecast. Whether Sean
wants it to also claim prediction is his call, and if so, the label set has to be built
before the claim.

---

## Sources
`var_decomposition.py`, `test_cr_redundancy.py`, `diag_landscape.py`,
`measure_landscape_blindness.py`, `check_position_evidence.py`.
Published facts: McDonald's Singapore help centre (150+ restaurants); EDB / Jollibee
(26 SG outlets); Watsons 18% share 2025 (Euromonitor); NTUC FairPrice 125 stores;
Sheng Siong 77 stores.
