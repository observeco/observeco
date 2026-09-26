# FINDING — The boolean gate fix was tested. It works for one dimension and fails for two — and the failures are correct-by-construction

**Date:** 2026-09-25
**Trigger:** `FINDING-floor-investigation.md` §6 recommended converting the gates from a
threshold on a continuous score into a **boolean the model answers directly**. That was a
*recommendation*. This tests it before anyone builds on it.
**Script:** `test_gate_boolean.py` → `runs/gate_boolean_test.json`
**Verdict:** **The boolean fix is VALIDATED for `competitive_room`, and REFUTED for
`market_headroom` and `demand_reach` — not because the fix is wrong, but because those two gates
guard states no submitted business can be in. Result: one gate is genuinely broken, two gates
should be DELETED, and the A3 recommendation for headroom now has a second independent argument.**

---

## 1. What was tested

Each gate was re-asked as a **two-option choice** stating the gate's meaning directly, with an
explicit "there is none at all" option — so the model must commit, independent of where it puts
probability mass on a continuous scale.

| gate | question asked | fires on |
|---|---|---|
| `gate_demand` | "Considering ONLY the product CATEGORY, is there any identifiable buying demand at all, from any supplier?" | `no_demand_at_all` |
| `gate_room` | "Does this business have ANY meaningful competitive room — any space in the customer's mind not already fully occupied?" | `no_room_at_all` |
| `gate_reach` | "Can this business reach enough customers to be viable at all?" | `no_reachable_customers` |

Run on 6 cases: N1 (closed — the only case that currently gates), F3 VICOM, D1 Watsons,
08-bubbletea, C9, N2 koi-stripped.

---

## 2. Result

| case | current continuous display (hd/cr/dr) | gates firing now | gate_demand | gate_room | gate_reach |
|---|---|---|---|---:|---:|---:|
| **N1 closed** | 3 / 2 / 2 | mental_adv, defensibility | 0.00 | **0.87 ✅ FIRES** | 0.43 |
| F3 VICOM | 3 / 2 / 5 | none | 0.00 | 0.18 | 0.00 |
| D1 Watsons | 3 / 2 / 3 | none | 0.00 | 0.26 | 0.00 |
| 08-bubbletea | – | none | 0.00 | 0.08 | 0.01 |
| C9 b2b IT | 3 / 3 / 4 | none | 0.00 | 0.02 | 0.01 |
| N2 koi-stripped | 3 / 3 / 3 | none | 0.00 | 0.19 | 0.00 |

(figures are P(the gate's "none at all" option); the gate fires when this is the majority)

---

## 3. `gate_room` — the fix WORKS, and cleanly

**Fires at 0.87 on the closed business. Maximum 0.26 anywhere else.**

This is exactly the discrimination the continuous rule could not achieve. `competitive_room`'s
display is 2 or 3 on all 20 cases (never 1), so the `< 2` threshold was unreachable. Asked
directly, the model commits decisively. **Margin 0.87 vs 0.26 — a 3.3× separation, not a
boundary call.**

**It also does not over-fire, and the near-misses are principled:**

- **F3 VICOM 0.18** — a statutory duopoly competitor. The obvious risk was that "protected
  market" reads as "no room". It didn't: the model correctly finds room for a competitor.
- **D1 Watsons 0.26** — highest of the non-closed cases, and it *should* be: `competitive_room`
  raw 0.89 is the lowest in the corpus. The gradient is ordered correctly.
- **08-bubbletea 0.08** — the legacy contested case. Lowest non-closed reading, consistent with
  its CONTESTED status under the old crowded framing.

**Gradient is correct in direction and magnitude. This fix is validated.**

---

## 4. `gate_demand` — the fix FAILS, and that is the right answer

**Every single case, including the closed business, returns 0.00 on `no_demand_at_all`.**
Unanimous "some demand exists", at probability 1.00.

**This is not a failure of the model. It is the correct answer to the question — and it proves
the gate is unreachable by construction.**

`market_headroom` asks about the **category**, not the business. N1's *business* is dead, but its
*category* (bubble tea) obviously has demand. **The model is right.**

**So the headroom gate guards a state no submitted business can occupy: a category with no
buying demand at all.** A business in such a category has no customers, no revenue and no reason
to fill in a business-review form. The gate is not mis-thresholded — it is **guarding an
unreachable state.** No threshold or wording change will make it fire, because there is nothing
for it to fire on.

**This is a second, independent argument for A3.** The first was distributional (headroom is flat
in elastic markets). This one is structural: **headroom's GATE is also inert, for a different
reason.** A3 says "make headroom a qualifier where it can't be scored" — and the gate evidence now
says the same thing from the other direction: *there is no state in which headroom should refuse a
report.* Both point to removing headroom from the gate set.

---

## 5. `gate_reach` — the fix fails, and the correct action is DELETE

Returns 0.00 on every case except N1 at 0.43 — and even there the majority is `some_route_exists`
(0.57).

**Same structural argument:** any business that reaches a form has *some* route to customers —
it registered, it may have a website, it took the trouble to submit. "Cannot reach any customer
at all" is a state that never arrives. The gate is unreachable for the same reason as
`gate_demand`.

**Recommendation: delete the gate, keep the dimension.** `demand_reach` has the third-widest raw
span in the rubric (72% of scale, mean 2.69) — it is a *working scoring dimension*. Only its gate
is inert. **The defect is the gate, not the dimension. Delete the gate.**

---

## 6. Corrected recommendation — replacing the one I made an hour ago

My earlier recommendation was: *"convert the gates into booleans."* That was one fix applied to
three problems that turn out to be different:

| gate | diagnosis | fix | validated? |
|---|---|---|---|
| **competitive_room** | genuinely **broken** — threshold below reachable range | **boolean** | **YES — 0.87 vs 0.26** |
| **market_headroom** | **unreachable by construction** — no category is demandless | **remove the gate** (A3's qualifier path) | structure proven; A3 already chosen |
| **demand_reach** | **unreachable by construction** — every business has some route | **remove the gate** | structure proven |
| mental_advantage | working | none | — |
| defensibility | working | none | — |

**Net change: one gate fixed, two gates deleted. The rubric goes from 5 gates (3 inert) to 3
gates, all of which can actually fire.**

This is a cleaner outcome than "convert everything to booleans" — and it is only visible because
the fix was tested rather than assumed. **Had I built the boolean conversion for all five gates,
I would have replaced one broken gate with one working + two differently-broken gates**, and the
"5 gates" would have looked repaired while remaining two-thirds decorative.

---

## 7. What this does NOT establish

- **n=6, with one positive.** The `gate_room` validation rests on a single firing case. The
  *separation* (0.87 vs 0.26) is wide and the gradient is correctly ordered, which is real
  evidence — but it is one positive. **Should be re-run over the full 20-case corpus before
  shipping.**
- **N1 is my own constructed case.** The only positive is a case I built. Its gate-relevant
  features (dead business, no differentiator) were chosen by me.
- **`gate_reach` at 0.43 on N1 is unexplained.** The model gives a closed business 43% on "cannot
  reach any customer". That is higher than I'd expect and may indicate the question is
  ambiguous for a defunct business. **Unresolved.**
- **Deleting a gate is a product decision, not a measurement.** "No submitted business can be in
  a demandless category" is an assumption about who uses the form. It is well-supported but it is
  an assumption, and a future channel (a distressed-business segment, a B2B category that
  collapses) could violate it.
- **The three F-cases are mine**, so 3 of the 20 corpus cases share one authorial hand.
- **I have not measured what deleting two gates does to the composite distribution.** Removing
  gates changes which reports are refused; the band cut-points were never tuned against a
  gate-set of three.
- **`competitive_room` is still the worst-scoring dimension** (mean raw 1.32, 32% of scale,
  2 display levels). Fixing its gate does not fix its scoring. **That is the next investigation
  and it is separate from this one.**

---

## 8. Recommended sequence (superseding §6 of the floor investigation)

1. **Re-run the boolean gate test over all 20 cases** (~15 min) to move `gate_room` from n=1 to
   n=20. Cheap, and it is the only validation standing between this and implementation.
2. **Implement: `competitive_room` gate → boolean; delete the `market_headroom` and `demand_reach`
   gates.**
3. **Then investigate `competitive_room`'s scoring** — 20% weight, 32% of scale, worst in rubric,
   never examined.
4. **Then A3**, now with two independent arguments behind it.
