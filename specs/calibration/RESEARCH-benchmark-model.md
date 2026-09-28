# Research — the benchmark model, and how comparable firms handle it

**Date:** 2026-09-28
**Question (Sean):** how do companies that give free survey results in exchange for contact
information, and hold the research data in house, handle it? Plus a path forward.

**Method.** Five parallel research streams (free-assessment design; contribution→dataset consent;
risk/liability; consultancy GTM; benchmark operational mechanics). Every claim below carries a
verification status. **Verification status is the important column** — subagent output is a
self-report, and I re-fetched and quoted the decision-critical pages myself.

| Status | Means |
|---|---|
| **VERIFIED** | I fetched the source myself and the quoted text is on the page |
| **REPORTED** | Subagent claim; source URL named but I could not re-fetch it (or did not) |
| **BLOCKED** | Source returns a JS shell / paywall / error to my fetcher |

---

## 1. The model, and who runs it

**Benchmark reciprocity**: the contributor gives data, receives a comparison, and the firm keeps
the aggregate. Confirmed across the survey/consortium set.

**VERIFIED — Levels.fyi states the business openly to contributors.** This is the single clearest
statement of the model found:

> *"We also license that same published data to employers and other customers for a fee. That is
> our business, and it is what lets us keep most of the Services free for the people who submit."*
> — https://www.levels.fyi/about/privacy.html

and, on what the licensed record carries:

> *"It carries the pay details, never your name, email address or contact details, and recipients
> are contractually barred from trying to identify you."* — same page

**⚠ The commercially important detail:** the same page publishes a record showing **employer, title,
level and location**, and warns *"please read what we can and cannot promise about anonymity."*
So Levels.fyi's model is **not** true anonymisation. It is **pseudonymous data with quasi-identifiers
retained and disclosed**, protected by contract on the recipient side. That is a **third path**
between §7.7's two boxes (identifiable / truly anonymised), and it appears to be the one that
actually works commercially at scale.

**REPORTED — reciprocity shapes, named:** Mercer (participant discount, not free access: *"you can
access with a 50% discount as a participant"*); PwC Saratoga (*"free-for-participants benchmarking
offering"*); APQC (contributor-only percentile; non-members USD 5,000; *"You are not allowed to
share or use the report outside of your organization"*); Payscale (*"receive a personalized pay
report and contribute to important research"*); DORA (nothing personalised — a deferred published
report, and raw data never released); GitLab (sweepstakes, not data access).

**The pattern:** the reciprocity is nearly always **real and named** — you get *something* back.
The exceptions (DORA, GitLab) substitute prizes or brand participation for a benchmark.

---

## 2. The minimum-cell rule — and it is real, with a number

**VERIFIED — Payscale publishes its own suppression rule and it contains a floor of 5 plus a
broadening step.** This is the most directly useful finding in the whole research set:

> *"When you view a salary report, you may see a message that says, "Data withheld for privacy" ...
> These methods include: removal of various combinations of information, presenting an average or
> aggregate or multiple data points, **limiting the base number of employers in any analysis to five
> or more**, and **pulling back from a local search to a broader geographic area**."*
> — https://www.payscale.com/about/privacy-policy

**Both halves of §7.7.1's proposed design are corroborated by a practitioner who publishes the
rule:** a floor (**five or more**), and **widening rather than suppressing** (local → broader
geography). §7.7.1 proposed widen-rather-than-suppress as an inference; here it is, in the wild.

**REPORTED — others:** PwC (*"we don't publish benchmarks where specific organisational results can
be identified by third parties"*); WTW (*"a report containing aggregated data based on the minimum
group size as specified"*); Levels.fyi (hide or generalise fields *"until we hold enough comparable
submissions"* — **I could NOT find this text on the page cited**, see §6); Lattice (a segment
*"emerges"* only with sufficient data); FICO (refuses outright below six months of history);
Google PageSpeed/CrUX (renders *"No Data"*, falls back page→origin, excludes thin sites).

**Failure modes are handled by escalate-then-degrade, never refuse-and-never-fabricate:**
PageSpeed shows *"No Data"* rather than a number; Trustpilot does the opposite, shrinking a thin
score toward a prior. Two legitimate strategies — but both are explicit.

---

## 3. What the contributor sees: number, band, or narrative

**REPORTED (all high-confidence in the stream, not re-verified by me):**

| Firm | What is shown |
|---|---|
| HubSpot Website Grader | **1–100**, deliberately — *"transparent grades help motivate"* |
| Moz | 0–100 with heavy disclaimers |
| Gartner | maturity *"best defined as a range"* — band, not point |
| Google Search Console | banded status, and **withholds any status until a data threshold is met** |
| Google Lighthouse | *"treat the score as a distribution of scores, rather than a single number"* |
| Bain / BCG / McKinsey | benchmark percentile against a 250–1,200+/10,000+ company pool |

**The design implication:** a precise number is defensible on **objective sub-dimensions**; the
**judgment-heavy composite should be banded**. That is exactly the split the spec already has (§5.8,
D2 — band + narrative, no number). The research supports it rather than challenging it.

**On precision instability:** Google's own docs say a Lighthouse score moves with **no code change**.
That is the measured case for banding a composite, and it is independent of our own noise-floor
measurement (±0.4 pts) — two unrelated instruments, same conclusion.

---

## 4. The `we cannot assess you` case

**REPORTED, consistent across sources.** The mature pattern is **escalate then degrade**:
score what you can, label the rest insufficient, state the minimum threshold, never fabricate.
Google's CrUX threshold is deliberately undisclosed; thin origins are excluded and the tool says so.

**This validates §3.10's floor and the two-refusal design (§5.4)**, and it adds one concrete
suggestion: **state the minimum answer threshold to the user** rather than only failing silently.

---

## 5. Risk, liability, AI disclosure — with one live conflict

### 5.1 AI disclosure: a real (if not immediate) obligation

**VERIFIED — EU AI Act Article 50**, fetched from primary text:

> *"Providers of AI systems ... generating synthetic audio, image, video or text content, shall
> ensure that the outputs of the AI system are marked in a machine-readable format and detectable
> as artificially generated or manipulated."*

and the prominence test:

> *"The information ... shall be provided to the natural persons concerned in a clear and
> distinguishable manner at the latest at the time of the first interaction or exposure."*

**⚠ THE CONFLICT — and it is a genuine design trap.** Article 50(4) exempts AI-generated text where
*"the AI-generated content has undergone a process of human review or editorial control and where a
natural or legal person holds editorial responsibility."*

So **human review REMOVES a disclosure obligation.** But §8.1 of the spec deliberately promises the
free report is **not** human-reviewed — to avoid borrowing the credibility of the paid engagement's
"a person owns the answer" promise. **Those two positions are consistent only while we stay
outside the EU's scope.** A Singapore firm *is* caught where its output is used in the EU.

**REPORTED:** Singapore has **no** mandatory AI-content disclosure rule (MTI, Nov 2025: *"no plans
to introduce specific disclosure requirements"*); IMDA's chatbot transparency guidelines are
voluntary. So the exposure is EU-only, and small — but the fix is cheap: the report already carries
an AI-only caveat (§8.1), so this is a wording check, not a new feature.

### 5.2 The closest failure analogue — and it was a free tool grading small businesses

**REPORTED (FTC pages would not render for me — BLOCKED):** *FTC v DoNotPay*. The allegation
structure is the warning: a service that **checked a small business website for legal violations
based on an email address**, which the FTC alleged **was not effective**; and the company
**did not test whether its "AI lawyer" operated at the level of a human lawyer**, and hired no
attorneys to check. Outcome: monetary relief plus a prohibition on professional-substitution claims.

**The transferable lesson for our report:** the exposure is not "the score was wrong". It is
**claiming a substitute for professional judgement without having validated it, and without having
said so.** §8.1's rule (never borrow the paid engagement's accountability language) is the correct
control, and this case is its justification.

**Other named failures (REPORTED):** Ofqual 2020 exam algorithm (withdrawn); Dutch benefits
algorithm (government resigned, €2.75m fine); Robodebt (*"neither fair nor legal"*, 500,000+
victims); Zillow Offers (forecast error → line shut, 25% staff cut); Epic Sepsis Model (AUC 0.63 vs
developer claims). **Common thread: an automated judgement applied at scale, with unvalidated
accuracy, without disclosure.** Our §10.7 calibration + §10.6 gate + §8.1 caveat are the three
controls against exactly this.

### 5.3 Abuse economics — the cost is trivial, the exposure is not

**REPORTED:** a ~8k-in/2k-out assessment on a small model ≈ **$0.0024** — about **$24 per 10,000
assessments**. Cost is not the risk. The documented risks are **volume** (one user triggering a
$700 overnight bill) and **adversarial drain** (services that exist to burn a competitor's credits).

**Controls, and one is a trap:** Cloudflare rate limiting and **Turnstile is free with unlimited
challenges** (already chosen, D11). ⚠ **reCAPTCHA v3 *fails open*** — it can return a static high
score when over quota, silently. And **visible CAPTCHAs cost up to ~40% of form conversions.**
So D11's Turnstile choice is well-supported, and the fail-open behaviour is a reason to keep a
**cost ceiling** distinct from a rate limit.

### 5.4 Domain reputation

**REPORTED:** Google (Feb 2024) requires authentication and **spam rate below 0.3%**; 5,000+/day
senders need DMARC and one-click unsubscribe; Yahoo requires one-click `List-Unsubscribe` and
honouring unsubscribes **within 2 days**; Microsoft rejects non-compliant bulk senders from 5 May
2025. Spamhaus DBL lists domains used in unsolicited bulk mail.

**This is exactly §3.7's open-relay argument, now with the requirements cited** — and it is why the
`/unsubscribe` endpoint built earlier this session was not optional.

---

## 6. What I could NOT verify — stated, not smoothed over

| Item | Status |
|---|---|
| **PDPC PDPA s14(2)** exact text | **BLOCKED** — AGC page returned only a table of contents. The structural sections are visible (*"16 Withdrawal of consent"*, *"18 Limitation of purpose and extent"*, *"20 Notification of purpose"*), and the subagent's reading of s14(2) is consistent with the Act's known shape, but **I did not verify the sentence** |
| **FTC DoNotPay** exact wording and $193,000 figure | **BLOCKED** — FTC pages render as JS shells to my fetcher |
| **Levels.fyi minimum-pool quote** | **NOT FOUND** on the cited page. The concept may be real, but the quote as given is not where it was said to be |
| **Opt-in rate for an optional research checkbox** | **NOT MEASURABLE from public sources.** The stream could not find a published figure and declined to substitute one — correctly. Nearest measured proxies: a systematic review of reuse consent averaged 84%, but the one study running both arms measured **21% vs 95.6% — a 4× swing purely from the default**; panel re-contact measured 60.0% opt-in vs 70.8% opt-out |
| **Conversion rates for assessment tools** | No independent benchmark exists. Available numbers are **vendor platform data** (Interact 40.1% start-to-lead; Typeform 47.3% completion; Unbounce 6.6% median landing page) or **unaudited vendor case studies** (ScoreApp 12.8%, £60k/100 completions). The closest independent anchor is freemium SaaS **2–5%** free-to-paid (OpenView 2022, second-hand) |

**A planning inference, labelled as one:** for a separate, unticked, non-required research checkbox
with a value exchange attached, the realistic band is **20–50%** — below the 84% research-reuse
figure because that figure often reflects a different consent architecture, and above the 9% seen
for an unticked checkout marketing box. **This is inference from adjacent designs, not a
measurement, and must be labelled as such if it ever goes in a deck.**

**The one strong, measured consent finding:** **placement beats wording.** Placement moved consent
45.2% → 61.3% in one experiment, and the authors conclude placement had the stronger and more
consistent effect. Framing effects are real but small — and the closest analogue to our appeal
(*"improved study value"*, 84.4%) was **not statistically significant**. Copy still matters on a
low base (one GDPR checkbox A/B test moved clicks ~2.8×).

**Implication:** put the box where it is **seen and understood as the exchange**, not where it is
merely present. That is a placement question, not a copy question.

---

## 7. The GTM findings that most affect the plan

These are from the consultancy stream and they are strategic rather than mechanical.

**REPORTED (mostly medium/low confidence — much of this literature is vendor content):**

1. **The majors give diagnostics away — but the free tier is a HOOK, and its credibility is the
   pool size.** Bain: free digital-readiness survey + a free IT diagnostic benchmarked on **250+
   companies**; the full maturity assessment is **sold**, resting on a proprietary database of
   **~1,200 companies**. BCG: **41 dimensions, 10,000+ benchmarks**. McKinsey: OHI free **to
   nonprofits only**, backed by **7M+ survey responses**. **Our pool is 120. That is the gap.**
2. **Referral dominates.** Hinge: **71%** of buyers find a firm by asking someone; **11%** via
   online search. UK BenchPress: **41%** of new clients from referrals, and only **12%** of firms
   have a referral strategy. **A free tool is not the primary channel — it is a credibility
   artefact for a referral-led sale.**
3. **Consultants struggle more with converting than with generating.** Consulting Success: *"more
   with sales (converting) than marketing (generating)"*. That is precisely the gap a diagnostic
   asset is meant to close — supporting the design intent.
4. **Free assets also fail in named ways:** giving away the answer so findings are taken in-house;
   unattached deliverables (audit emailed with no scheduled call); maintenance creep; and
   **the play becoming obsolete once a firm has a portfolio** — because the free proof stops adding
   conviction.
5. **Pricing, SGD: S$500 sits BELOW every published diagnostic anchor.** Productized audit guides
   put a standalone diagnostic at **$2,000–5,000**; low-ticket qualifiers sit at **$47–250**.
   SG boutique rates are **SGD 150–400/hr** vs SGD 800–1,500+ for majors, with SG SMEs preferring
   **fixed project pricing**. **S$500 is defensible as a triage/qualifier and hard to defend as a
   diagnostic** given the delivery hours.
6. **⚠ THE MOST IMPORTANT FINDING IN THE SET — Singapore already provides the free thing.**
   **10 SME Centres give free business advisory to ~25,000 SMEs a year**, and **from 2027 will add
   "diagnostic toolkits" for capability gaps.** Meanwhile **EDG subsidises up to 50% of eligible
   costs including third-party consultancy fees — but management-consultancy costs require a
   TR 43 / SS 680 certified consultant** (a concrete, checkable gate). SG small-business sentiment
   is also weak: 43% grew in 2025 vs a 62% survey average, second-last of 11 markets.

**That last cluster is a competitive fact worth its own conversation and it was not in the spec.**
Free government advisory is a direct substitute for a free positioning report in the SME segment —
and the EDG certification requirement is both a barrier and an unlock.

---

## 8. What changes in the spec

| # | Change | Basis |
|---|---|---|
| 1 | **Minimum-cell rule: floor 5, widen-not-suppress — corroborated, keep.** Payscale publishes exactly this | **VERIFIED** |
| 2 | **Add the pseudonymous-licensed third path** to §7.7's two-box table. Levels.fyi's model is not anonymisation and it works at scale | **VERIFIED** |
| 3 | **State the minimum answer threshold** to the user, not only fail silently | REPORTED (CrUX/PageSpeed pattern) |
| 4 | **EU AI Act Art 50 is a wording check, not a feature** — keep the AI caveat prominent; note the human-review exemption creates a tension with §8.1 that only stays consistent outside the EU | **VERIFIED** |
| 5 | **Turnstile confirmed; add a cost ceiling distinct from the rate limit** (reCAPTCHA v3 fails open) | REPORTED |
| 6 | **Benchmark placement is a decision, not a detail** — placement beats wording | REPORTED, measured |
| 7 | **The pool-size gap is now explicit**: our 120 vs 250–1,200 (Bain) and 10,000 (BCG) | REPORTED |
| 8 | **D25 recommendation unchanged but better grounded**: floor 8 for our case, because Payscale's 5 protects *employees* who are not each other's competitors, and ours are | inference, stated |
