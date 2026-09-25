# FINDING — The duopoly leg exists, and the axis was wrong

**Date:** 2026-09-25
**Trigger:** Sean — *"Why not find a good duopoly case and try to establish?"*
**Context:** I had asserted (in chat, no test) that the concentrated-oligopoly middle had
"no sourced measure." That assertion was made from a standing start. This file tests it.
**Verdict:** **The assertion was wrong. The duopoly leg is measurable — AND the monopoly/duopoly/
fragmented axis is the wrong axis.**

---

## 1. The claim I made, and what testing it showed

| my assertion | tested result |
|---|---|
| "monopoly leg real (ASML backlog/revenue 1.19)" | **correct** |
| "fragmented leg real (SSIC entry/exit)" | **correct** |
| "concentrated middle — no sourced measure" | **FALSE. Two clean duopolies publish a usable instrument.** |

**I did not test before declaring the gap.** Same error pattern as the earlier "defect" that turned
out to be the instrument working.

---

## 2. Duopoly case A — Boeing / Airbus (global commercial aircraft)

A textbook duopoly: two players, ~99% of large commercial aircraft, both with published order books.

| measure | value | source |
|---|---|---|
| Airbus commercial backlog (end-2025) | **8,754 aircraft** | globalair.com |
| Airbus order book value | **€539.7B** | selborneresearch |
| Airbus 2025 deliveries | **793 aircraft** | selborneresearch |
| Airbus A320-family derived backlog cover | **~11.8 years** | selborneresearch |
| Boeing 737 derived backlog cover | **~9.9 years** | selborneresearch |
| Boeing company backlog (Q2-2026) | **$715B** | globalair.com |
| Global aerospace: years to clear backlog | **~12–14 years** | centreforaviation |
| 2025 net orders: Boeing 1,173 vs Airbus 889 | Boeing's first order win since 2018 | bostonwarwick |

**Both duopolists are supply-constrained and demand exceeds capacity** — *"Deliveries can't keep
up"*; *"Record aircraft orders keep climbing"*; Airbus ramping A320 toward 70–75/month by end-2027.

**The instrument is the same one ASML uses: demand ÷ capacity, read off the order book.**

---

## 3. Duopoly case B — Watsons / Guardian (Singapore health & beauty)

A duopoly in a **Singapore-relevant, SME-adjacent** category.

| measure | Watsons | Guardian (DFI) |
|---|---|---|
| stores (SG) | **~99** | **~126** |
| value share 2025 | **18%** (16% in 2020) | **14%** |
| combined | **32%** | (Sephora next at 7%) |

Source: Euromonitor *Health and Beauty Specialists in Singapore*; watsons.com.sg; rocketreach.

**Note the contrast with aircraft:** Watsons and Guardian are *not* supply-constrained. Capacity is
**elastic** — you open a store in months. Euromonitor reports the category as "concentrated, with
leading companies increasing their dominance," and the observable is **price and promotion
intensity**, not an order book: *"there are over 100 Watsons and Guardian outlets each"* and
*"Guardian and Watsons' many promotions"* — price-matching behaviour, the classic duopoly outcome.

---

## 4. The finding that matters — the axis is wrong

Two duopolies, **two completely different observables**:

| | capacity | observable | what it shows |
|---|---|---|---|
| ASML (monopoly) | **inelastic** | backlog ÷ revenue = **1.19 yr** | unmet demand |
| Boeing/Airbus (duopoly) | **inelastic** | backlog cover = **10–12 yr** | unmet demand |
| Watsons/Guardian (duopoly) | **elastic** | share stability + promo intensity | demand met, contested |
| bubble tea (fragmented) | **elastic** | entry ÷ exit (SSIC) | demand met, contested |

**Monopoly and duopoly split across the divide — and two duopolies land on opposite sides.**
So monopoly/duopoly/fragmented does **not** determine the observable.

**The dividing line is ELASTIC vs INELASTIC CAPACITY:**

- **Inelastic supply** → demand that can't be served **accumulates as an order book**. The instrument
  is backlog ÷ revenue. Available exactly where the phenomenon can occur.
- **Elastic supply** → demand is served quickly, so competition shows up as **churn and price
  war**. The instrument is entry ÷ exit plus promotion intensity.

**This also explains why the crowding framing failed on ASML.** Crowding asks a question about
*rivals* — "is there room for a new entrant?" ASML has no entrants, so it scored as *closed*. But
closed-to-rivals is not the same as closed-to-opportunity. The crowding question **conflated
"contested" with "shut."** Unmet-demand fixed that but then asked a demand question of elastic-supply
markets, where demand is *always* served — hence the flatness.

---

## 5. The threshold problem — the honest catch

Absolute backlog-cover does **not** transfer across categories:

| benchmark | backlog cover |
|---|---:|
| normal industrial order book | ~0.25 yr |
| **ASML** | **1.19 yr** (4.8× normal) |
| **Airbus** | **~11.0 yr** (44× normal) |
| **Boeing 737** | **~9.9 yr** (40× normal) |

Aircraft carry 10-year backlogs **as normal business practice** — airlines order years ahead. So by
absolute value the aircraft duopoly looks **~9× more starved** than ASML, when in category terms
**ASML is the extreme one**.

**Therefore backlog-cover must be normalised against the category's own norm** — a stated baseline,
not a global threshold. Otherwise the measure ranks by industry ordering convention, not by
scarcity. This is the same class of bug as the CAGR rejection (an absolute number blind to the
constraint).

**Second catch: availability.** An order book exists only where supply is inelastic — aircraft,
semiconductor equipment, shipbuilding, defence. It does **not** exist for our actual population
(bubble tea, supplements, TCM, hawkers). So this leg is *precise but narrow*: it will apply to a
minority of the 17 cases. That is not a defect — the instrument is available exactly where the
phenomenon occurs — but it means it cannot carry the composite alone.

---

## 6. Corrected design

Replace the monopoly/duopoly/fragmented axis with a two-axis classification:

**Axis 1 — capacity elasticity** (decides *which instrument* answers "is demand met?"):

| condition | instrument | status |
|---|---|---|
| **Inelastic** — supply can't flex | backlog ÷ revenue, **normalised to category norm** | **established** — ASML 1.19; Airbus ~11.0; Boeing 737 ~9.9 |
| **Elastic** — supply can flex | entry ÷ exit (SSIC formations vs cessations) | **established** — M085851, 128 series, post-2020 spans |
| **Ambiguous** | both, and report disagreement | honest gap — do not force |

**Axis 2 — concentration** (decides *who captures the value*, not whether demand is met):
derived from the Tier 1–7 set we already build. Bubble tea 353 outlets of 688–953 tracked (37–51%);
Watsons 18% / Guardian 14% / Sephora 7%; supermarkets top-3 = 88% (Euromonitor).

**Axis 2 is where the monopoly/duopoly/fragmented vocabulary properly belongs** — it shapes the
recommendation (can this position be taken from an incumbent?), not the headroom measurement.

---

## 7. What this changes

1. **The three-model proposal is sound and now has all three legs tested** — but split by
   *capacity elasticity*, not by *player count*.
2. **The prior rejection of backlog-cover was also premature.** It was written off as *"available
   only where not needed."* Tested: it is available precisely where it is needed. Keep it, with
   category normalisation.
3. **The classifier still gates the build** (unchanged from my earlier pushback): capacity elasticity
   must be determined before the instrument is chosen, and derivation should come from the Tier 1–7
   set we already produce.
4. **Two honest gaps remain:** category-norm baselines for the inelastic leg, and the ambiguous
   middle. Do not dress either up as quantified.

---

## 8. What this does NOT establish

- Boeing/Airbus and Watsons/Guardian are **not in the 17-case calibration set.** They are
  existence proofs that the legs are measurable, not calibration evidence. Adding them is a
  separate decision.
- Aircraft backlog-cover figures are **third-party derived** (selborneresearch, centreforaviation),
  not audited company statements as ASML's were.
- The elastic/inelastic split is **my hypothesis fitted to four cases.** Four cases can show a
  hypothesis fits; they cannot show it generalises. This is exactly the error that produced the
  0.6.0 over-correction — validated on four, collapsed on seventeen.
- **The category-norm baseline problem is unsolved.** I have no source for "normal backlog cover"
  per category beyond the ~0.25 industrial figure.
