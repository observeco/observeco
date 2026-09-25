# FINDING — C3/C5 ordering resolved; the top-anchor split FAILED; a gate defect surfaced

**Date:** 2026-09-25
**Rubric:** 0.4.1 (0.4.0 split attempted and reverted)
**Sean:** *"Resolve the C3/C5 ordering before anything else. Split the top anchor."*

---

## PART 1 — The C3/C5 ordering: RESOLVED, and my flag was WRONG

### The decisive test

Reading C3's own differentiator answered the second hypothesis on sight — **every claim in it is
a size fact**: *"the largest"*, *"widest range"*, *"a footprint no other pet retailer
approaches"*, *"our scale lets us"*.

Under a **relative** framing, a business whose every claim is a size claim has **nothing to
over-index on** — "at expectation" is arithmetically correct. So either the dimension is
input-sensitive, or the 3/5 is a real finding.

**Test — isolate the input.** Identical business, category, price, customer and derived set.
**Only the differentiator text changes**, adding a situational cue the owner could plausibly
have stated (*"the situation we own is the new pet… when someone brings home their first
puppy"*).

> **`D2-petlovers-cue` → MA 3/5 — UNCHANGED.**

**Input sensitivity is FALSIFIED.** Adding a stated retrieval cue did not move the score.

### The blank control

**`D1-watsons`** — dominant incumbent (18% share, 100+ outlets, Euromonitor 2025),
low-salience category, **no distinctive claim** — customers pick the nearest branch.

> **MA 2/5** (interval 1–2), composite **45 Contested**.

### The resolution

| MA | Case | What it owns |
|---:|---|---|
| **5** | C2 ActiveSG | *"the cheapest way to exercise"* |
| **5** | C5 Michelin hawker | *"the best bak chor mee"* |
| **4** | KOI / C6 Eu Yan Sang / C4 Sheng Siong | trusted everyday tea / 146-yr heritage / value |
| **3** | **C3 Pet Lovers Centre** | **size only** |
| **2** | **D1 Watsons** | **none — proximity** |
| **2** | N2 stripped / CaiCa | removed / failing |
| **1** | N1 closed | dead |

**C3 at 3 and Watsons at 2 are correct.** The hawker beats the pet chain because a hawker stall
is genuinely **retrieved** — it is the first answer to "great bak chor mee" — while a 69-store
chain is **not the first answer to anything**.

**This is the Ehrenberg-Bass finding and my flag inverted it: brands are chosen by being
retrieved, not by being large.** Size buys **reach**, not **retrieval**.

**And the rubric separates the two**: PLC scores `demand_reach` **4** (wide physical reach) but
`mental_advantage` **3**. The hawker is the reverse. Two constructs, two dimensions.

### What I got wrong

I flagged a defect on the reasoning *"the biggest operator should not score below the smallest."*
That assumption is **wrong under positioning theory** — it presumes size and mental availability
move together, the exact assumption CEP research refutes.

**Second time in this project a flagged defect was the instrument working.** First: the "low
confidence" theme (it was evidence coverage). Same root cause both times — **I judged output
against an intuition instead of against the theory the dimension implements.**

---

## PART 2 — The top-anchor split: ATTEMPTED, FAILED, REVERTED

### What I did (0.4.0)

Reserved **level 5** for *"the default retrieval — the FIRST name a typical buyer reaches
for"*, and made **level 4** *"over-indexes for its size but is not anyone's default."*

### Result — it did not do the job

| Case | before | after | intended |
|---|---:|---:|---|
| **C5 hawker** | 5 (5–5 @0.80) | **5** (4–5 @0.67) | **should drop to 4** |
| **C2 ActiveSG** | 5 | **5** (5–5 @0.86) | stay 5 |
| C3 Pet Lovers | 3 | **4** ↑ | — |
| N2 stripped | 2 | **3** ↑ | — |
| C6 Eu Yan Sang | 4 | **5** ↑ | — |

**The separation it was built for did not happen** — C5 and C2 both still 5/5. C5's *interval*
softened (5–5 → 4–5), so the wording had *some* effect, but not enough to cross a level.

**And it made things worse elsewhere.** C3 moved 3→4, **destroying the diagnostic clarity Part 1
had just established**; N2 and C6 also drifted up. The new level-4 text was easier to satisfy
than the old one, so mass shifted upward.

**Reverted to 0.4.0's predecessor wording as 0.4.1.** The failed attempt is kept in
`dimension_change_log` for audit rather than erased.

**Conclusion: separating "over-indexes for its size" from "is the default answer" by anchor text
alone does not work.** If the distinction is real and wanted, it needs to be **two questions**,
not two levels of one question.

---

## PART 3 — A more serious defect the split exposed

**`bubbletea` (CaiCa) flipped from 53 Contested to GATE.**

```
defensibility distribution: {0: 0.51, 1: 0.48}   EV = 0.50
display = int(round(0.50)) + 1 = 1  ->  gate fires  ->  GATE, no composite
```

**The gate boundary sits exactly at raw 0.50, and our measured run-to-run noise is 0.08.**

> **A judgment of 0.50 ± 0.08 decides a GATE outcome.** The business's whole verdict flips on
> whether the model returns 0.48 or 0.51.

This is worse than the ordering question. A **gate** is the safety layer that decides whether the
report *is* a scored report at all — and it is being fired by noise, not by a finding. Earlier
runs of the same case produced 53/Contested; CaiCa's own delivered analysis says *"there is no
differentiator"* would be a defensible read, so the **right answer is genuinely contested** —
which means the gate should either be **confidence-weighted** (require decisive coverage before
it can fire) or the boundary should carry a **dead-band** where the verdict is reported as
*"on the boundary"* rather than flipping.

**This is the first defect found in this project that affects whether a real client sees a score
or a refusal.** It should be fixed before the gates are trusted in production.

---

## What changed

| | |
|---|---|
| **`D1-watsons`** | new control — dominant, low-salience, no cue → MA 2, composite 45 |
| **`D2-petlovers-cue`** | new control — decisive input-sensitivity probe → MA unchanged at 3 |
| **Rubric 0.4.1** | top-anchor split reverted; failed attempt logged |
| **C3/C5 ordering** | **resolved** — not a defect; my flag was wrong |
| **Gate boundary** | **new defect** — 0.50 boundary vs 0.08 noise |
| **Coverage floor** | now **7 withheld judgments** across the ladder |

## Open, in priority order

1. **Gate boundary defect** (Part 3) — decides whether a client sees a score or a refusal.
2. **Zero human labels** — unchanged, still #1 validity blocker.
3. **Anchor split, redone as two questions** if the distinction is wanted.
4. **Weights** still uncalibrated (15/20/25/25/15), declared not derived.
