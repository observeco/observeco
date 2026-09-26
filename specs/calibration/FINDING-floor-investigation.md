# FINDING — Floor compression investigated: the real defect is 3 of 5 gates are INERT

**Date:** 2026-09-25
**Trigger:** Sean — *"Investigate the floor compression first (my recommendation)."*
**Scripts:** `probe_floor.py`, `probe_blast_radius.py`, `probe_levels_used.py`
**Verdict:** **The anomaly I flagged does not exist — it was my own misreading. The investigation
found a different and more serious defect: three of the five gates can never fire. Also: the
dimension ordering across the corpus is the inverse of what I had been assuming.**

---

## 1. Correction one — the "anomaly" was my error

In `FINDING-midsized-test.md` §6 I flagged:

> *"VICOM (1.57) is BELOW N1 closed business (1.69) — a profitable market leader reading under a
> defunct one. Unexplained."*

**There is no inversion in the delivered output.** I was comparing one dimension's display value in
isolation. The report's verdict comes from the **composite + gate**, and:

| case | headroom | gates firing | composite | band |
|---|---:|---|---:|---|
| **N1 closed** | 3 | **mental_advantage, defensibility** | **None** | **GATE** |
| **F3 VICOM** | 3 | none | **64** | **Viable, conditional** |
| E1 ASML | 4 | none | 91 | Strong |

**N1 is refused by the gate and given no composite. VICOM scores 64.** The system ranks them
correctly — one is refused, one is a conditional viable. My "anomaly" compared a quantity that
isn't the verdict.

**This is the fourth time in this project a flagged defect turned out to be the instrument working,
and the third time the defect was my own.** The pattern is now unmistakable: I flag, then test,
then withdraw.

---

## 2. Correction two — the dimension ordering was the *inverse* of what I assumed

I had been treating `market_headroom` and `competitive_room` as roughly comparable. The mean raw
scores across 20 cases say otherwise:

| dimension | mean raw | levels | **argmax spread** | **raw span (% of scale)** |
|---|---:|---:|---|---:|
| **defensibility** | 2.73 | 6 | **0–5** | 4.45 (**89%**) |
| **mental_advantage** | 2.27 | 5 | **0–4** | 3.60 (**90%**) |
| demand_reach | 2.69 | 5 | 0–4 | 2.87 (72%) |
| **market_headroom** | 2.04 | 5 | **2–3** | 1.76 (44%) |
| **competitive_room** | **1.32** | 5 | **1–4** | **1.29 (32%)** |

**`competitive_room` — which holds the HIGHEST weight of the five at 20% — is the WORST-performing
dimension in the entire rubric.** It has the lowest mean score, the narrowest raw span (32% of its
scale), and it uses only 2 display levels (13 cases at 2, 7 at 3).

`market_headroom` at 15% is the second-worst. **The two dimensions I spent the session attacking
are not the worst problem. `competitive_room` is.**

---

## 3. The actual defect — 3 of 5 gates are structurally INERT

Every gate floor is **2** on the 1–5 display scale. A gate fires when `display < floor`. So a gate
can only fire if the model sometimes returns display **1**.

| dimension | gate floor | display levels actually used (n=20) | can the gate ever fire? |
|---|---:|---|---|
| **market_headroom** | 2 | **3, 4 only** | **NO — never uses 1 or 2** |
| **competitive_room** | 2 | **2, 3 only** | **NO — never uses 1** |
| **demand_reach** | 2 | 2, 3, 4, 5 | **NO — never uses 1** |
| **mental_advantage** | 2 | 1, 2, 3, 4, 5 | YES — uses 1 |
| **defensibility** | 2 | 1, 2, 3, 4, 5 | YES — uses 1 |

**N1's gate fired on exactly the two dimensions that range fully** (mental_advantage, defensibility)
— the only two that *can* fire. This confirms the mechanism and explains a long-standing mystery:

> *"The gates have never fired on a Jev output (0/4 runs). CaiCa's G4 fired on a HAND-WRITTEN label,
> never on a real run."* — N1 input file, written before this investigation

**Now we know why.** The gate thresholds sit below the model's reachable range for three of the five
dimensions. **They are decorative.** A "no demand" market cannot trip the headroom gate, because the
model never goes low enough to trip it. A business with no competitive room cannot trip the
competitive_room gate, for the same reason.

**This is a real, material defect — and it is a GATE defect, not a score defect.**

---

## 4. Why this is NOT an anchor problem — the blast-radius test

The critical question: is the compression specific to `market_headroom`, or is the model's prior
squashed across the whole rubric? Different diagnoses, different fixes.

**Answer: only `market_headroom` and `competitive_room` are compressed. The model's range elsewhere
is healthy.**

| dimension | mean mass profile (0 = lowest anchor) | levels with mass > 0.15 |
|---|---|---|
| market_headroom | 0:0.00 **1:0.12 2:0.75** 3:0.09 4:0.04 | **[2] only** — 75% on one level |
| competitive_room | 0:0.06 **1:0.66** 2:0.22 3:0.05 4:0.02 | **[1]** — 66% on one level |
| mental_advantage | 0:0.08 1:0.23 2:0.23 3:0.24 4:0.21 | [1,2,3,4] — even spread |
| defensibility | 0:0.13 1:0.11 2:0.19 3:0.13 **4:0.33** 5:0.10 | [2, 4] |
| demand_reach | 0:0.09 1:0.05 2:0.19 **3:0.44** 4:0.23 | [2,3,4] |

**The model's prior is not squashed.** `mental_advantage` spreads almost perfectly evenly across
four levels; `defensibility` and `demand_reach` both show clear multi-level structure. **So the
compression is specific to the two dimensions in question — it is not a model-wide distributional
artifact.**

That matters, because it rules out the cheapest explanation ("the model just answers low") and
points at the two things genuinely distinctive about `market_headroom`: its question and its
anchors.

---

## 5. What is and is not broken

**NOT broken — the score.** `market_headroom` scores correctly within its narrow band. The
elastic/inelastic mechanism validates (F1 3.20, F2 1.92, F3 1.57, ASML 3.33), it separates
inelastic-unmet from inelastic-met, and it never confuses a barrier to entry with an opportunity.
`raw == E[level]` holds to 0.03 across all 20 cases (0 mismatches). The A3 design stands.

**BROKEN — the gate.** Three of five gates cannot fire. The system cannot detect "no demand",
"no competitive room", or "no reach" through the gate mechanism, because the thresholds are below
the model's floor on those dimensions.

**UNRESOLVED — whether the bottom anchors are *correctly* unreachable.** Two readings, and I cannot
separate them from this corpus:

- **(a) The anchors are mis-scaled.** Level 1 of `market_headroom` reads *"No demand. There is no
  identifiable buying demand for this category at all."* A business that reaches us has *some*
  demand — it registered, it has a website. **Perhaps level 1 is simply unreachable by construction,
  which is correct, and the gate should move rather than the anchor.**
- **(b) The model is reluctant to say "no demand".** It put 0.57 on level 2 for a **closed business**
  rather than reaching for level 1. That suggests a floor prior, not an unreachable anchor.

**The distinguishing test:** re-score N1 with an explicit instruction that a dead business *is*
level 1. If it moves to level 1, the anchors are fine and the gate placement is the fix. If it still
refuses, the anchor's wording is the problem.

---

## 6. Consequence for the build

**The A3 build was going to be the next step. It should not be.**

A3 removes `market_headroom` from the composite for elastic markets. But the composite is not what
is failing — the *gate* is. Building A3 first would rebuild the score path while leaving three inert
gates in place, and A3's whole justification is "headroom is a qualifier where it can't be scored",
which is a *scoring* claim about a system whose *gating* is the actual defect.

**Corrected priority:**

1. **Fix the gates** — either raise the floor above the model's reachable minimum, or convert the
   gate from a threshold on a continuous dimension into a boolean the model answers directly
   ("is there any demand for this category at all?"). **The boolean is the better fix**: it makes the
   gate's meaning independent of where the model happens to put its probability mass.
2. **Then `competitive_room`** — 20% weight, 32% of scale used, 2 display levels, inert gate. It is
   the largest single scoring gap and it has never been examined.
3. **Then A3**, with the knowledge that headroom's narrow band is a *gate* issue, not an anchor
   issue.

---

## 7. What this does NOT establish

- **`competitive_room` has not been diagnosed**, only measured as the worst performer. Its problem
  may be the question, the anchors, or the challenger-framing defect already logged (withheld at
  0.00 coverage on ASML). **Untested.**
- **n=20, and 3 of those are my own F-cases.** The gate-inertness finding rests on no case ever
  scoring display 1 on three dimensions. That is strong but corpus-dependent — real customer inputs
  may reach lower. **The fix should be robust to that, which argues for the boolean.**
- **The two readings in §5 are unresolved.** I have not run the distinguishing test.
- **The raw-span comparison across dimensions with different level counts (5 vs 6) is approximate**
  — span as a percentage of scale is a rough normalisation, not a rigorous one.
- **I have not verified why `competitive_room` is low.** It may be correct: most control cases face
  genuine competitive crowding, and the corpus was deliberately built with squeezed cases (Sheng
  Siong vs FairPrice). **A low mean may be the corpus, not the dimension.**
