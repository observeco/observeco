# FINDING — Outlier scope decision, dead gates, and a separate weight/discrimination observation

**Date:** 2026-09-25
**Trigger:** Sean — *"We should adopt a 80/20 approach. We can't and shouldn't solve for extreme outliers."*
**Note on the trigger:** "80/20" here is **an expression, not a numeric directive.** It means *focus
on the common case; do not engineer for the tail.* Sean confirmed this explicitly — it is not to be
taken literally, and it licenses no reweighting arithmetic. Sections 1–2 below are the decision that
follows from it. **Sections 3–4 are my own observations, made independently — they are NOT part of
the 80/20 decision and should not be read as one.**
**Verdict:** **ASML and Boeing/Airbus are out of scope. The three dead gates are free to delete
(verified zero-risk). Separately, the dimension weights do not match the dimensions' measured
discriminating power, but that is an observation to carry, not an instruction to act on.**

---

## 1. ASML is out of scope — and it never mattered anyway

Sean's call: ASML and Boeing/Airbus are outliers; the form's population is ordinary SMEs; do not
build for the tail.

**The corpus agrees.** `competitive_room` has **never fired on any case, ever** — under the current
rule or any candidate rule tested. Only **N1 (closed business)** is refused, and it is refused by
`mental_advantage` and `defensibility` — the two dimensions that work.

So the ASML over-fire was a real finding about the *question's* framing, but **it is not a problem
to solve**: in the population this product serves, `competitive_room`'s threshold is never the
deciding factor. Building an incumbent branch for a monopolist would be engineering for a company
that will never fill in the form.

**Recorded, not fixed.** If a future version takes on large incumbents, the framing defect in
`FINDING-gate-boolean-test.md` §"the falsification" is the thing to revisit.

---

## 2. Deleting the three dead gates is free — verified zero risk

The three inert gates (`market_headroom`, `competitive_room`, `demand_reach`) cannot fire. Deleting
them changes **nothing**:

```
composites changed by deleting all 3 inert gates: 0 of 20
```

**Zero risk, verified across the whole corpus.** The only gate that ever fires is on
`mental_advantage` + `defensibility`, both retained.

**Recommendation: delete them.** Five gates (three decorative) become two that actually work. This
is pure cleanup with a measured proof that nothing downstream moves.

The gates themselves are documented as unreachable:
- `market_headroom` — no product category has zero buying demand; every case returned 0.00 on
  "no demand at all" at p=1.00, including the closed business. Correct answer, unreachable state.
- `demand_reach` — any business that reaches a form has some route to customers.
- `competitive_room` — the model never returns display 1 on this dimension (uses 2 and 3 only).

---

## 3. SEPARATE OBSERVATION — weight does not match discrimination

**This section is not part of the 80/20 decision.** It is an independent measurement I made while
investigating the gates. It is recorded because it is true and material, and because it bears
directly on A3 — not because Sean asked for it or because it follows from "80/20."

How many composite points can each dimension actually move?

| dimension | weight | reaches | **moves** | **effective** |
|---|---:|---|---:|---:|
| **defensibility** | 25% | 4/6 | **18.5 pts** | 18.5% |
| **mental_advantage** | 25% | 4/5 | **18.0 pts** | 18.0% |
| demand_reach | 15% | 4/5 | 8.6 pts | 8.6% |
| market_headroom | 15% | 3/5 | 5.3 pts | 5.3% |
| **competitive_room** | **20%** | **2/5** | **5.2 pts** | **5.2%** |

**Two dimensions holding 35% of the nominal weight — `competitive_room` (20%) and `market_headroom`
(15%) — deliver 10.5 composite points between them.** The other two, at 25% each, deliver 36.5.

**`competitive_room` is the sharpest case: 20% of the nominal weight, 5.2% of the movement.** It
never reaches 4 or 5; the model's ceiling on it is 3. A reader of the report is told this factor is
a fifth of the assessment. It is a twentieth.

**This is not a bug — it is what happens when two dimensions are near-constant for the target
population.** For ordinary SMEs in served markets, both are genuinely almost always the same.
The composite is effectively a three-dimension instrument wearing five dimensions' clothing.

---

## 4. The trap to flag before anyone reweights

The obvious move on reading §3 is to rebalance the weights to match the measured discrimination —
give `competitive_room` 5% instead of 20%.

**That would be fitting to the corpus.** This is the exact error this project has made repeatedly
(0.6.0 validated on 4 cases; the aggregation rule; the CAGR test). The distinction:

- **A weight is a NORMATIVE claim** — how much *should* competitive room matter to whether a
  business succeeds? That is a question about the world, not about my 20 cases.
- **The measured spread is a SAMPLE STATISTIC** — how much does competitive room *vary* in my
  corpus, which I built and which is deliberately full of squeezed cases (Sheng Siong vs FairPrice,
  Watsons vs Guardian).

**Reweighting on the second to fix the first is a category error**, and it would produce a rubric
tuned to my sample. The two numbers disagree for an interesting reason — a genuinely important
factor can be nearly constant across a population — and the fix is not to demote it but to **say so
in the report.**

**The honest resolution is the one already chosen:** this is A3. `market_headroom` becomes a
qualifier (a sentence) rather than a score where it can't discriminate. The same logic extends to
`competitive_room`.

---

## 5. What this means for the build — the picture is now simple

Five dimensions, for an ordinary SME:

| dimension | status | action |
|---|---|---|
| **mental_advantage** (18.0 pts) | works | keep |
| **defensibility** (18.5 pts) | works | keep |
| demand_reach (8.6 pts) | works | keep |
| **market_headroom** (5.3 pts) | near-constant for SMEs | **A3: qualifier, not score** |
| **competitive_room** (5.2 pts) | near-constant for SMEs | **qualifier candidate** |

**The composite is driven by two dimensions, not five.** That is the product's real shape, and the
report should say it plainly rather than implying five factors were weighed.

**This also explains the VICOM result.** VICOM scored 64, band "Viable, conditional" — on
`mental_advantage` 3 and `defensibility` 4 and `demand_reach` 5, with the two near-constant
dimensions contributing almost nothing either way. That is the instrument working.

---

## 6. What this does NOT establish

- **The "effective weight" figures are sample statistics from 20 cases, 3 of which I wrote.** They
  show the weights are misaligned *in this corpus*. Whether they are misaligned in the real
  population of form submissions is **untested** — and that population is the whole point.
- **`competitive_room` never firing means it is untested, not proven safe.** A rule that never
  fires has no track record in either direction.
- **Two gates would remain.** Reducing 5 → 2 concentrates refusal power in `mental_advantage` and
  `defensibility`. Whether two gates are sufficient to catch a genuinely unviable business is
  **not answered by this corpus** — only one case is designed to be refused.
- **The outlier decision is a scope decision, not a measurement.** Sean's call is that incumbents
  are out of population. If a real customer turns out to be a regional monopolist, the ASML framing
  defect becomes live again.
- **I have not tested whether a qualifier treatment of `competitive_room` restores any spread** —
  the same unbuilt path as A3.
- **Nothing here validates the rubric against a human label.** Still zero human labels against the
  current rubric; still the #1 validity blocker.
