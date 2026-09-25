# FINDING — Should market headroom be quantified as an addressable-market CAGR?

**Date:** 2026-09-25
**Sean's proposal:** *"Can we quantify the market headroom in the typically way in which an
addressable market CAGR is calculated? Let me know if that is a good approach and solves our
issue."*
**Verdict: it is not a good approach, and the test shows exactly why — but it points at the
right quantity, which we can get.**

Rubric unchanged at 0.6.0. Nothing was adopted from this test.

---

## The test

Rather than opine, I researched the **actual published CAGRs** for our test cases' real
categories and measured whether CAGR separates the cases the way we need.

## Result 1 — CAGR cannot encode the insight, because it barely varies

| case | category | published CAGR |
|---|---|---:|
| **ASML** | semiconductor lithography equipment | 7.40–9.73% |
| bubble tea | Singapore bubble tea | 6.80–7.56% |
| Pet Lovers | Singapore pet care | 5.54–6.80% |
| Eu Yan Sang | Singapore herbal/TCM | 1.58–6.75% |

**Every category lands in 4.5%–8.9%.** Mapped to a 1–5 level, ASML gets **4.45** and bubble tea
**3.73** — a gap of **0.72**. The unmet-demand framing already in 0.6.0 gives **3.33 vs 1.88** —
a gap of **1.45**, i.e. **2.0× wider separation**.

**The research industry forecasts ASML's category at ~9% and bubble tea at ~7%.** It does not see
a supply-starved monopoly as an unusual-growth market.

## Result 2 — the fatal flaw: CAGR is blind to the constraint

**CAGR measures the market as it IS — including its constraint.** ASML's category CAGR of ~9% is
the growth rate *of a market that cannot grow faster than ASML ships tools*. The shortage is
**inside** the number. Every CAGR we could buy would say "normal growing market" about the single
most supply-constrained market on earth.

**Headroom is a demand-supply GAP. CAGR is a growth rate.** A market can grow 20% and be fully
served; it can grow 2% and be rationed. These are different quantities:
- 20% growth, fully served → high CAGR, **no headroom**
- 2% growth, supply-starved → low CAGR, **high headroom**

**Growth is capped by supply, so a constrained market looks ordinary. That is precisely backwards
for this dimension.**

## Result 3 — the data does not exist for our actual customers

**4 of 17 cases have a published category CAGR. 13 have none** — bonefirm, observeco, koi, C2, C4,
C5, C9, D1, D2, E2, E4, N1, N2.

**The typical ObserveCo lead is an unlisted SME in a niche the research houses do not cover.**
CAGR is available *precisely for the businesses that do not need a free report* (large, listed,
well-covered categories) and unavailable for the ones that do. As a core score it would be
**uncomputable for the median lead**.

## Result 4 — the sources are unreliable at 4–17×

| category | disagreement |
|---|---|
| Singapore herbal/TCM CAGR | **1.58% / 5.2% / 6.75%** — a **4.3× spread** between firms pricing the same category in the same year |
| Singapore bubble tea market size | **USD 11.79M–17.12M** (6W/DMI, 2025) vs **USD 201M** of imports (Tridge, 2023) — **~17×** on the size of the same market |

These are SEO/report-mill publishers, not audited sources. **Scoring a client's report on numbers
that vary 17× by source is not defensible** — and a score that moves when the source changes is a
score that can be argued with, which is the opposite of what a lead magnet needs.

---

## What the test DID surface — the right quantity, quantified

**ASML's own revenue CAGR is 15.1%** (FY2021 €18.611bn → FY2025 €32.667bn, audited), against its
category's ~8.9%. **The company grows ~1.7× faster than its market.**

And the constraint is directly measurable in the order book:

| metric | ASML FY2025 |
|---|---:|
| backlog | **€38,797m** |
| FY2025 revenue | **€32,667m** |
| **backlog cover** | **1.19 years (14.3 months)** |
| mid-2026 guidance | +11.7% |

**Backlog cover 1.19 years** — against ~0.25 for a normal industrial order book and ~1.00 for
capacity described as "sold out". **ASML is 1.2× sold out.** That number *is* Sean's claim,
quantified: *"demand far exceeds supply"* in a single audited figure.

**But it requires an order book.** Available for: capital equipment, B2B contract manufacturing,
SaaS. **Not available for: restaurants, bubble tea, retail, salons, tuition, clinics, gyms, F&B.**
**ASML is the only case in our 17 that publishes one.**

**The measurable quantity is available exactly where it is not needed, and unavailable exactly
where it is needed.**

---

## Recommendation

**Do not adopt CAGR. Do not adopt backlog cover either** — it fails the same availability test.

**Adopt the SELF-REPORTED version of backlog cover**, which is the only form of this signal
available for every SME:

> *"Are you turning customers away, at capacity, or holding a waitlist?"*

That is backlog cover in self-report form — the demand-supply gap, expressed by the one person
who knows it. It requires no market report, no order book, and no publisher. It is available for
all 17 cases including every SME.

**And use CAGR as CONTEXT, not as a score.** *"Your category grows ~7%/yr (source)"* is genuinely
useful to a business owner and costs us nothing to state — but it is **cited background**, not a
scored input, so a 4.3× source disagreement cannot move anyone's number.

**This resolves the dimension cleanly:**
- **score** the demand-supply gap (owner-reportable, available for all, encodes Sean's insight)
- **cite** the category CAGR (context, never scored)
- **state** the headroom type (*no demand / served / unmet*) as a qualifier, per the 0.6.0 finding

**The deeper lesson:** CAGR measures a market's *growth*, which is bounded by supply and therefore
cannot reveal a supply shortage. **A quantified external metric cannot see the constraint, because
the constraint is baked into it.** Sean's insight is fundamentally about the demand-supply gap — and
that gap is only visible from inside the business.
