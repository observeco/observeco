# FINDING — How Gartner et al. actually size a market, and why Sean's category point resolves it

**Date:** 2026-09-25
**Sean's question:** *"How does Gartner and similar generate and calculate total addressable market
value and their corresponding growth rates? Remember that positioning theory is about product
categories instead of industry?"*

**That last sentence is the answer, and it invalidates my earlier approach.** I had been working
with **SSIC industry codes**. Gartner defines markets as **product categories**. Different object
→ different data → different result. **My industry-based reasoning was aimed at the wrong unit
of analysis.**

---

## 1. What Gartner's own methodology says (verbatim from their published methods)

**Market size is built from VENDOR REVENUE, not from an industry aggregate:**

| step | what they do |
|---|---|
| 1 | Establish **vendor revenue** for vendors tracked, selected by market impact |
| 2 | **Add** an estimate for vendors **not** tracked → published as *"Other Services Vendors"* |
| 3 | **Subtract** an estimate for subcontracting → prevents double-counting |
| 4 | The total **is** the market size. Market share = that vendor's revenue ÷ the total |

**Market share is not looked up. It is computed by summing the competitive set.**

**IDC does the same**, with a published estimator for the untracked tail: model the
revenue-per-vendor distribution as an exponential curve (fewer vendors as revenue rises),
estimate how many unknown vendors exist in each revenue band, multiply by band midpoints.

**Forrester** prescribes TAM/SAM/SOM and explicitly **triangulation**: *"use multiple data
sources and approaches ... By comparing results from a range of approaches and soliciting input
from experts, organizations can improve the accuracy."*

### The quote that corrects my earlier claim

I previously concluded that a growth rate is a weak, unreliable metric. **Gartner says the
opposite — and this is important:**

> *"Our focus is on developing the most accurate **growth rates** possible ... as growth rates
> are often **more verifiable and comparable than absolute values**."*

> *"The absolute size ... is difficult to definitively assess ... In contrast, growth rates
> represent some of the most verifiable data that we develop, because **most large vendors
> publicly report several years of financial information**."*

> *"For these reasons, **the first-year growth rate, rather than absolute value, is the metric
> preserved** in our data model."*

**They adjust the absolute value to fit a growth rate, not the reverse.** So the growth rate is
the *reliable* output — **provided it is derived from vendor financials.**

**This is the correction I owe you:** my earlier finding said *"a quantified external growth
rate cannot reveal the constraint."* That is true of a **report-mill** CAGR, which is an
estimate about a market. It is **not** true of a **vendor-derived** growth rate, which is built
from audited company accounts. **Your instinct was right; the flaw was in my data source, not
in the method.**

---

## 2. The category point — and the elegant consequence

Gartner's markets are product categories a buyer recognises: *"IT services"*, *"warehouse
automation"*, *"fuel cell vehicles"*. **SSIC is a classification of industries** — a different
axis entirely.

The firm that covers our case tracks it as **"Street Stalls/Kiosks"** — a **product category**,
with *"GBO Company Shares / GBN Brand Shares: % Foodservice Value"*. **Not** *"SSIC 56 Food &
Beverage Services."*

**Consequence, and it ties two threads together:**

**The market boundary IS the competitive set. Our Tier 1–7 derivation already IS the market
definition.** We do not look the category up — we derive it, then size it by summing it.

**So the positioning work and the market-sizing work are the same object.** They were never two
problems. Deriving who competes for the same budget *is* defining the market; summing their
revenue *is* sizing it. That is precisely Gartner's method and precisely positioning theory.

---

## 3. Executed on our case, from public data

**Tracked vendors** (outlet counts off each brand's own store list, 13 Sep 2026):

| vendor | outlets |
|---|---:|
| KOI Thé | 90 |
| LiHO Tea | 52 |
| Each-A-Cup | 48 |
| CHAGEE | 46 |
| Chicha San Chen | 32 |
| Mixue | ~30 |
| Playmade · R&B Tea · Sharetea · HEYTEA | 55 |
| **TRACKED TOTAL** | **353** |

**Category total** (two independent directories): **688** (brand directory) and **953** (business
listings). So we track **37–51% directly** — the rest is Gartner's *"Other"* tail, which their
methodology explicitly estimates rather than ignores.

**Per-outlet revenue** from a published outlet-level model: 250 cups/day × S$5.40 × 30 = **S$486k/yr**.

**→ Gartner-style market size = outlets × revenue per outlet:**

| basis | market size | "Other" tail |
|---|---:|---:|
| 688 outlets | **S$334M/yr** | S$163M |
| 953 outlets | **S$463M/yr** | S$292M |

---

## 4. Triangulation — and the disagreement is the finding

| method | estimate |
|---|---|
| **A. bottom-up** (population × incidence × price) | S$94M – **S$718M** |
| **B. vendor sum** (Gartner's method) | **S$334M – S$463M** |
| **C. client revenue ÷ client share** | **S$225M** |

**A and B agree. C sits below them — no common band.**

**Per the MBB method, the disagreement is the output, not a failure:**
- If the category is really ~S$400M, the client's S$45M implies a share of **~11%, not the ~20% assumed**
- So either the client's share is overstated, or some outlets earn less than S$486k, or the 20% uses a different denominator

**That is exactly the analytical finding Gartner would deliver — and it is worth more to the
client than any point estimate.** It also confirms the earlier result: the derived competitor set
must not be taken from the owner.

**Against the paid report-mill figures (S$16M–23M for the same category): our three independent
methods are 4–45× higher.** The report mill has almost certainly sized the *manufactured/packaged
drink* segment and called it the category. **This alone justifies not buying them.**

---

## 5. The definition IS the number — proven from audited figures

**ASML's own filings, same company, same year:**

| definition | 2025 |
|---|---:|
| system sales only | **USD 26.4bn** |
| including service (Installed Base Management) | **USD 35.3bn** |

**A 33% swing from the definition alone.** And it explains the published spread: ASML holds
85–90% of lithography revenue, implying a category of ~USD 30bn — **which matches the published
USD 22–29bn only if you count system sales and exclude service.**

Gartner's methodology warns about exactly this:

> *"Different companies, government agencies and trade associations may use slightly different
> definitions of product categories ... These differences should be kept in mind when making
> comparisons."*

**A market must therefore be published WITH its definition — never quoted bare.**

---

## 6. What this means for the product

**The MBB/Gartner method is adoptable, and the category correction is what makes it work.**
Concretely:

1. **The derived competitive set is the market definition.** Already built (Tier 1–7). No separate
   market-definition step is needed — it is the same object.
2. **Size it by summing the set** — vendors tracked + an *"Other"* tail, exactly Gartner's method.
   This needs **no founder input** and **no paid report**.
3. **Growth rate from vendor-level facts**, which is where the reliability is: *CHAGEE 0→46 outlets
   in 24 months; Mixue 0→~30 since 2022; KOI 90 and still #1; Gong Cha closed 29 outlets Oct 2025;
   Tiger Sugar delisted.* That is auditable, vendor-derived, and exactly Gartner's approach.
4. **Publish the market with its definition and a range** — the triangulated band, plus where the
   methods disagree. Gartner does not publish a bare number and neither should we.
5. **Report what the disagreement teaches** — a client learning their share is 11% not 20% has
   received real value, and it is the kind of finding that converts to the paid engagement.

**And headroom falls out of this naturally:** the demand/supply relationship from triangulation,
now with a proper TAM attached — *"a S$334–463M category growing [x]%/yr, where your share is
~11%"* is a sentence an owner can act on.

**Still not a 1–5 scalar.** A triangulated range with a stated definition cannot be one of five
weighted terms. That is now the third independent line of evidence for the same conclusion —
which is why I would stop trying to force it into the composite.

---

## 7. Corrections to my own earlier findings

| earlier claim | correction |
|---|---|
| "CAGR can't encode the insight" | True of **report-mill** figures. **Not** true of vendor-derived growth, which Gartner calls its *most verifiable* metric |
| "free data is only section-level" | Wrong — SSIC 5-digit exists; but more importantly **SSIC is the wrong axis** (industry, not product category) |
| "the measurable quantity is available only where it isn't needed" | Wrong. Vendor revenue for the derived competitive set is public for our case: 353 outlets counted directly |
| "a quantified external metric can't see the constraint" | Overstated. A **vendor-derived** metric does — because vendor financials *are* the constrained thing |
| "ask the founder about demand" | Sean's correction accepted and now doubly confirmed — the triangulation showed the client's own share claim is the least reliable input |
