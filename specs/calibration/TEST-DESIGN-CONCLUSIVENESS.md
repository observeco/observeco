# Can the toolkit test be conclusive? — evidence and limits

**Date:** 2026-09-28
**Question (Sean):** *"If my riskiest assumption doesn't pay do you realise I do not have a viable
business model to begin with? So why can't the diagnostic toolkit be my test with proper building of
the benchmark, so that the results can be as conclusive as possible?"*

**Short answer:** it can be conclusive about a **narrow, pre-specified threshold** above a stated
sample size. It **cannot** be conclusive about the business model — and the base rate for the target
segment is already unfavourable before any test runs.

---

## 1. What the test CAN establish

| Purpose | Rule | At our scale |
|---|---|---|
| **Zero-result bound** (rule of three) | No paying engagement in *N* trials → 95% upper bound = **3/N** | 100 → "<3%"; **300 → "<1%"**; 500 → "<0.6%". Unreliable below N=30 |
| **Precision** of a single rate | **n = 1/B²** for ±B | ±5pp → **384**; ±3pp → **1,111**. Independent of population size |
| **Two-arm comparison** (80% power, 5% α) | Evan Miller: `n = 16·σ²/δ²` | 5%→10% ≈ **435/arm**; 10%→20% ≈ **199/arm**; 2%→5% ≈ **588/arm** |

**Practical floor: pre-commit to 300 completed submissions before any go/no-go.** At ~100 per arm on a
comparative question you have **~52% power** for a 10%→20% difference — a coin flip.

**⚠ Peeking invalidates the result.** Continuous monitoring can turn a nominal 5% error rate into
**26.1%**. Even ten looks means you need a reported **1.0%** for a true 5%. Fix N and the decision rule
before launch, or use a sequential/always-valid method. *(Evan Miller; Johari, Pekelis & Walsh.)*

**⚠ Low power misleads rather than merely missing.** Below ~50% power a "significant" result is
typically a large overestimate (Type M); below ~10% it is often the wrong sign (Type S).
*(Gelman & Carlin.)*

---

## 2. What it CANNOT establish — the identifiability limit

A null result is consistent with **four different problems**, with opposite remedies:

| Possible cause of an empty result | Remedy |
|---|---|
| The tool is bad | Rebuild |
| **The segment is wrong** | **Retarget** |
| The offer or price is wrong | Reprice |
| No distribution | Fix reach |

**A test that cannot separate these is not evidence for or against the business model.**

**Intentions are not behaviour:** a medium-to-large change in intention produces only a small-to-medium
change in behaviour (d+ = .36), and intentions are enacted about **half** the time. *So the primary
outcome must be money received — not "would you buy", not NPS, not intent.*

---

## 3. ⚠⚠ The base rate is already unfavourable

**VERIFIED VERBATIM** — UK Longitudinal Small Business Survey 2023, via Enterprise Research Centre
(*Understanding micro-businesses*, Oct 2025):

> *"In 2023, only **24% of micro-businesses used external advice in the past 12 months, down from 31%
> in 2015**. They remain less likely to seek external support than small (**34%**) and medium-sized
> businesses (**45%**). The gap between micro and medium-sized firms has consistently been around 20
> percentage points since 2015."*

Companion figures: **16%** for businesses with **no employees** (2019–2023, flat). And **within** the
minority who seek advice, consultants are a minority channel:

> *"Small and medium-sized and small businesses were more likely than micro businesses to have sought
> information and advice from consultants or general business advisers (**47%, 51% and 32%
> respectively**)."*

**Accountants dominate the paid-advice market for this segment. Consultants are the minority channel
even among the minority who buy advice.**

### The offer evidence is worse than the survey evidence

**VERIFIED VERBATIM** — Bruhn, Karlan & Schoar, World Bank, Puebla Mexico RCT (n=432):

> *"Out of the 150 enterprises in the treatment group, 80 then took up the consulting services. The
> remaining 70 treatment group enterprises **declined to participate in the program although they had
> initially signed a letter of interest** saying that they would participate if offered a spot."*
> … *"Among the enterprises in the treatment group, **only 53% chose to participate** in the subsidized
> consulting program once offered a spot."*
> … *"most of the enterprises in the treatment group that declined participation … gave **liquidity
> constraints** as the reason."*

**Read that again:** firms that *asked* for subsidised consulting, and *signed* for it, declined **half
the time** when offered. Subsidy was 70–90% of a US$11,856 fee.

**And willingness to pay is low before experience, rising only after delivery** — ILO (*What Works in
SME Development*, Issue Brief 9): 23% (Vietnam) and 65% (Tanzania) would pay US$150 pre-training, rising
to 53% and 100% after. The ILO's conclusion is ours: ***"potential demand is high, but the effective
demand is low."***

### Singapore specifics

- **94.7% of Singapore SMEs have fewer than 25 workers** (337,700 of 356,600). *MOM/EnterpriseSG, 2024.*
- **SME Centres give FREE 1-to-1 advisory to ~25,000 enterprises a year**; EnterpriseSG helped 11,500 in
  2024 — **~7% and ~3% of the SME population annually.** Direct competitors for the free-diagnostic position.
- **The private consulting market is grant-mediated:** EDG funds consultancy costs **only via certified
  consultants.**
- **95.1% of SMEs already adopted at least one digital area (2024)**, so a digital diagnostic is not novel.
- **SCCCI's n=711 survey (93% SMEs) publishes no paid-advisory purchase rate at all**; cost is the top
  concern at 65%. The closest SG survey to this question does not answer it.

---

## 4. The channel problem

- **Referrals + direct human outreach supply nearly two-thirds of new business** even for the
  fastest-growing firms (n=495, ~$85bn revenue).
- **71% of buyers ask another person first; only 11% search online.** *(Hinge Research Institute, n=137,
  2009.)*
- **51.9% of referred prospects rule a firm out before even talking to it** (n=523 firms).

**Consequence: a cold-traffic-only test of a referral-led market returns a misleading null.** It would
look like evidence against the toolkit when the real finding is that the wrong channel was measured.
**The toolkit must be tested as BOTH a cold-acquisition channel and a referral credibility artefact,
and reported separately.**

**The 51.9% figure is also the strongest argument for the artefact itself** — a specific,
evidence-based positioning report is what survives that pre-contact filter.

---

## 5. Conversion evidence — near-total reliance on vendor data

**No published, independently measured figure exists for the exact funnel** *free diagnostic →
paying consulting engagement* in a small professional-services firm.

| Source | Figure | Type |
|---|---|---|
| Interact | 40.1% start-to-lead (42.2% service providers) | **VENDOR** |
| Unbounce | 6.6% median landing page; 6.1% professional services | **VENDOR** |
| Ruler Analytics | 6.1% professional services visitor-to-lead; 52.6% of conversions arrive as **calls** | **VENDOR** |
| Chili Piper | 66.7% form-fill-to-booked-meeting | **VENDOR** |
| Zuko | ~45% form view-to-submit; ~66% start-to-finish | **VENDOR** (via secondary aggregator) |
| First Page Sage | $327 organic CPL; 31% lead-to-MQL; $942 organic CAC | agency portfolio |
| Hinge | referrals 71% / online 11% | independent institute (self-serving) |

**Every single-step number in that table is a company marketing its own conversion technology, not a
measurement of your funnel.** The honest chain (~1,000 visitors → ~61 leads → ~40 conversations → 4–8
clients at 10–20% purchase) is **arithmetic on vendor benchmarks**, not a published result — and it
ignores that web leads are the minority channel and that free-tool users self-select as price-sensitive.

---

## 6. Blocked sources (reported, not hidden)

- **Gartner** B2B buying journey — HTTP 403. The widely cited "17% of purchase time with suppliers"
  figure **could not be verified** and is excluded.
- **Source Global Research** mid-market report — purchase-gated. *(Its stated buyer universe is
  $100m–$3bn revenue — the consulting research industry **does not study micro-SMEs at all**.)*
- **Zuko** benchmark tables — JS-rendered, no readable values; the 45%/66% figures rest on a secondary
  aggregator.
- **SBF National Business Survey 2023-24** — PDF extraction failed (12 of 58 pages need OCR).
- **ACCA Singapore professional services report** — 404.
- **Typeform** data-on-data report — 404 (both the blog and the PR release).
- **Button et al.** *Power failure* and **Amrhein et al.** *Nature* — abstract only; full text paywalled.
- **PubMed** — reCAPTCHA wall.

---

## 7. The recommended test design (pre-register before launch)

1. **Pre-register the funnel and the clock.** Unique visitors → tool starts → completions → submissions
   → booked calls → proposals → **signed engagements with money received.** Fix the analysis date and N
   up front.
2. **Do not peek for stopping decisions.** Use a sequential/always-valid method if monitoring.
3. **Run at least one full business cycle (7 days) — realistically 3–6 months.** Consulting purchase
   cycles are long and novelty spikes decay.
4. **Primary outcome = money.** Booked calls secondary. Intent measures nothing.
5. **Pre-commit to N = 300** completed submissions before go/no-go, and publish the formula.
6. **State the decision rule numerically, including the fail branch** (spec §7.12).
7. **Test both channels** — cold acquisition and referral artefact — reported separately.

**The fail branch that matters:** a null at ≥300 submissions with a **working instrument** is
information about the **market**, not the code. The remedy is **retarget (D32)**, not a rewrite.
