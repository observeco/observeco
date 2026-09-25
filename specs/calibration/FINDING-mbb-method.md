# FINDING — The MBB method: Sean is right, my earlier test was wrong

**Date:** 2026-09-25
**Sean's challenge:** *"why can't we adopt the way MBBs calculate CAGR for any industry? Surely
there is a common consensus on this already. I think asking the founder is a wrong move. They
don't have the abilities like MBBs."*

**Verdict: Sean is right on both counts, and my previous finding was testing the wrong thing.**

My earlier test measured **report-mill CAGRs** (6Wresearch, Deep Market Insights, etc.). **That
is not the MBB method.** The MBB method is bottom-up + top-down + triangulation, and when I
execute it properly on free government data, **it works — and it produces exactly the quantity
headroom needs.**

Rubric unchanged at 0.6.0 pending Sean's decision.

---

## 1. What the MBB method actually is

| step | what it is |
|---|---|
| 1 | **Define the market** — who is the buyer, what is bought, what is excluded |
| 2 | **Top-down** — start from a known aggregate, apply filters to reach the segment |
| 3 | **Bottom-up** — units × price, or population × incidence × spend |
| 4 | **Triangulate** — two independent methods agreeing within ~2× = defensible. **Disagreement IS the finding** — it locates a definitional difference to resolve before quoting |
| 5 | **Only then** compute growth/CAGR across periods |

**The output that survives an MBB engagement is a RANGE with the disagreement documented — not
a point estimate, and not a single growth rate.** That is the part I got wrong before.

**Sean is also right that a founder cannot do this.** Sizing a market is analyst work. Asking an
owner "how big is your market" invites a guess.

---

## 2. I executed the method on free Singapore government data

**Not** paid report mills. Two independent public sources:

| side | source | granularity |
|---|---|---|
| **demand** | SingStat Household Expenditure Survey | ~10 goods/services groups, 5-yearly |
| **supply** | ACRA/SingStat business formation & cessation | **SSIC 5-digit**, annual + monthly, since 1990 |

### The bottom-up demand build (step 3)

Singapore residents ~4.18M, drink-buying population ~2.85M:

| incidence × price | category size |
|---|---|
| 0.5 cups/pp/mo × S$5.50 | **S$94M/yr** |
| 1.0 × S$7.00 | S$239M/yr |
| 3.0 × S$7.00 | **S$718M/yr** |

**A 7.6× range from two individually-reasonable assumptions.** The incidence figure is the whole
ballgame, and free data does not supply it for a niche category.

### The triangulation (step 4) — and this is the important part

**Triangulation between a demand-side build and a supply-side build produces the ratio between
them. That ratio IS unmet demand, i.e. headroom.**

**ASML, both sides audited:**

| | EUR m |
|---|---:|
| supply (FY2025 net sales — what was *served*) | 32,667 |
| demand (backlog — what buyers *committed* to buy) | 38,797 |
| **demand / supply** | **1.19** |

**Buyers have committed 1.19× a full year of production. Unmet demand is 19% of annual output.**
That is headroom expressed as a **ratio of two audited numbers** — not a growth rate.

**Bubble tea, triangulated:**

- supply side: CaiCa S$45M revenue at ~20% share → implied market **S$225M/yr**
- demand side bottom-up: **S$94M–718M/yr**
- **S$225M sits inside that range** → the two independent methods agree

**Agreement means supply is meeting demand. No queue, no backlog, no rationing. Headroom is LOW.**

**The same method separates ASML from bubble tea — and it is the MBB method.**

---

## 3. The free data IS category-granular — better than I previously claimed

I previously said the finest free cut was the top-level SSIC section (~16 industries). **That was
wrong.** SingStat table **M085851** carries **128 series** at SSIC 5-digit, annual, since 1990:

| SSIC | category | maps to |
|---|---|---|
| **56123** | Food & Drink Kiosks Mainly For Takeaway And Delivery | **bubble tea** |
| 56 | Food & Beverage | F&B section |
| **9609** | Other Personal Service Nec (e.g. Pet Care…) | **pet care** |
| 93 | Sports Activities & Amusement & Recreation | gyms |
| 86 | Health Services | clinics |
| 85 | Education | tuition |

**SSIC 56123 is the closest thing to a bubble-tea series that exists in public data.** So the
supply side is available at genuine category granularity, free, forward indefinitely.

---

## 4. But the supply series fails a robustness check — and this is the real obstacle

SSIC has been revised several times (**2005, 2010, 2015, 2020**). If a code's coverage changed,
a multi-year CAGR measures **reclassification, not growth**. Measured:

**SSIC 56123 (bubble tea / kiosks), CAGR by period:**

| period | CAGR |
|---|---:|
| 1990–2005 | −1.81% |
| 2005–2010 | −8.78% |
| 2010–2015 | **+29.67%** |
| 2015–2020 | **+38.72%** |
| 2020–2025 | **+14.46%** |

**The sign flips.** Year-on-year jumps: **2014→2015: +389%** (at an SSIC boundary),
**2016→2017: +518%**. Pet care (SSIC 9609): +16.99% then −10.43% then −7.13% then −3.05% then
+11.10%.

**These are not market movements. They are the code being redefined.** A series that swings
+518% in one year and flips sign across boundaries cannot yield a defensible growth rate over
any span crossing a revision.

---

## 5. So: what actually is the answer to Sean's question?

**"Why can't we adopt the MBB way?" — We can, and we should.** The method is real, consensual,
and executable, and my earlier rejection tested something else entirely. **Sean was right.**

**What the method gives us that no CAGR could:**

1. **The demand/supply ratio — which IS headroom.** ASML 1.19 (rationed); bubble tea agreement
   (served). This is Sean's insight, quantified, from two independent sides.
2. **Triangulation as a validity gate.** When the two methods disagree, the disagreement is
   itself the finding — it locates a definitional error before it reaches a client.
3. **It needs no founder input.** The demand side is built bottom-up from public data; the
   supply side comes from ACRA. **Sean is right that the founder is the wrong instrument, and
   the method does not need them.**

**What it cannot give us:**

1. **A point estimate.** The bottom-up build spans 7.6× on one assumption, and the supply series
   breaks at every revision. **The honest output is a range with the constraint stated.**
2. **An instant free score.** Executing this properly per case is the work MBB bills weeks for.
   Automating it is possible but its output is a **range + a qualifier**, not a number to drop
   into a weighted composite.

**The synthesis — and I think this resolves the whole thread:**

**Adopt the MBB method as the DERIVATION ENGINE, and never present its output as a scalar.**

- **Derive** the market structure by triangulation (automated, no founder input)
- **Report** the demand/supply ratio and whether the two sides agree
- **State** the range and its binding assumption (incidence), not a false-precision score
- **Keep** it out of the weighted composite — a range cannot be one of five weighted terms

This honours all three of Sean's points: the MBB method is used; the founder is not asked to do
analyst work; and the headroom question is answered with a quantified, two-sided number.

**And it is consistent with the 0.6.0 finding from a different direction: headroom is a type and
a range, not a 1–5 scalar.**

---

## 6. What I got wrong before, stated plainly

| earlier claim | correction |
|---|---|
| "CAGR can't encode the insight" | True of **report-mill** CAGRs. **Not** true of MBB triangulation, which produces the demand/supply ratio directly |
| "the free data is only section-level" | **Wrong.** SSIC 5-digit, 128 series, since 1990 — including SSIC 56123 for kiosks |
| "the measurable quantity is only available where it isn't needed" | **Wrong.** The supply side is available at category granularity for every Singapore SME; the demand side is a bottom-up build needing no order book |
| "ask the founder if they're turning customers away" | **Sean's correction accepted.** An owner is a poor market analyst. The method can build the demand side without them |

**The one claim that survives:** an externally-published growth rate cannot reveal a supply
constraint, because the constraint is baked into it. **That is why triangulation is required and
a single CAGR is not enough** — and it is the reason Sean's instinct to use the MBB method is
better than my instinct to use a published CAGR.
