# OBS-SPEC-095 — Business Review Lead Engine

**Status:** DRAFT v5 — architecture, gaps integrated.
**Date:** 2026-09-23
**Owner:** Sean
**Name:** KIV (D1)
**v5 change:** Blind-spot appendix removed and its content integrated into the owning sections.
The ten questions (§1.1) now frame the document. **§5.4 is new and changes the scoring model** —
a gate layer in front of the weighted composite. Accountability (§8), monitoring, jurisdiction
(§9) and asset protection are now architectural sections rather than footnotes.

---

## 1. The product

A page on observeco.com that explains what a full competitive analysis contains, and offers a
free light-touch business review in exchange for name, email and ~15 answers. The review is
generated automatically and emailed. It returns **five dimension scores, a composite index, a
verdict sentence and the one gate that would falsify the position** — a flavour of the full
report, with the substance withheld. Its job is qualification, not volume.

**Scoring doctrine (non-negotiable):** *Jev types the judgments. Code computes the score.*
Jev is a System One labeller returning calibrated probabilities, not an oracle. Every dimension
score must be traceable to a named judgment.

### 1.1 The ten questions this design must answer

The product publishes a **machine-made judgment about someone's business, under Sean's name**.
That act has ten distinct obligations, and each is a pillar of this spec. They are stated here
so every later section can be checked against them.

| # | Pillar | The question | Section |
|---|---|---|---|
| Q1 | **Validity** | Does the number mean anything? Is agreement with six cases evidence of accuracy — or just agreement? | §5.6, §10 |
| Q2 | **Scoring model** | Can a fatal flaw in one dimension be outvoted by strength in four? | §5.2–5.4 |
| Q3 | **Input integrity** | Is the input trustworthy — and can a stranger make us email a victim? | §3.6–3.9 |
| Q4 | **Evidence integrity** | Is the evidence real, or a block page wearing a competitor's name? | §4 |
| Q5 | **Output integrity** | Does the report hold up when a sceptical prospect reads it? Is it reproducible? | §6.3–6.4 |
| Q6 | **Accountability** | Who owns a wrong answer, when the site promises "a person owns every recommendation"? | §8.1 |
| Q7 | **Operability** | Can we run it — and would we know if it silently stopped? | §8.2–8.5 |
| Q8 | **Legality** | PDPA, DNC and any regime beyond Singapore. | §3, §9 |
| Q9 | **Asset protection** | The rubric is the method. What stops a competitor lifting it? | §8.6 |
| Q10 | **Product boundary** | Where does free stop, and does it route to the right paid tier? | §7.2, §8.7 |

**Q2 is the one that changed the design.** See §5.4.

### 1.2 Committed decisions

| # | Decision |
|---|---|
| D2 | **Supabase** as the datastore, and the system of record for contacts and consent |
| D3 | Nurture is **low priority now**; the architecture must support blasting later without re-scoping |
| D4 | Ship the capture-only stage **before** calibration clears |
| D5 | Enrichment uses **the Hermes web-search-scraping-protocol** |
| D6 | Weights are a hypothesis, refined by calibration |
| D7 | A dimension that cannot clear is **dropped and stated**, not forced |
| D8 | Email: **Resend** for transactional, **Brevo** for marketing (§6.1–6.2) |
| D9 | Marketing subdomain: **`mail.observeco.com`** (to create) |
| D10 | Phone is collected **optionally**, as a matching key — never an outbound channel (§3.5) |

---

## 2. Architecture overview

Five layers, plus two cross-cutting concerns that apply at every layer.

```
L1  CAPTURE      form · consent record · contact · trust boundary       [must not fail]
L2  ENRICHMENT   web-search-scraping-protocol · validity gate           [best-effort]
L3  SCORING      Jev · rubric JSON · gates + composite in code          [gated]
L4  DELIVERY     transactional stream · marketing stream                [must not fail]
L5  CRM          pipeline · stages · suppression · retention · durability

CROSS-CUTTING    monitoring (§8.2) · jurisdiction (§9)
```

**The governing principle is asymmetric failure:** the report must exist even when every external
dependency is down. **L1 and L4 must never fail. L2 may fail freely. L3 is the only gated layer.**
A dead API key degrades depth — never existence.

The **trust boundary** enters at L1 and must be enforced at L2 and L3: nothing a submitter
supplies is trusted, and nothing the open web supplies is trusted until it passes the validity
gate (§4.1).

---

## 3. L1 — Capture

### 3.1 PDPA is an architecture concern, not a page footer

The obligations that produce structural requirements, not copy:

| PDPA obligation | Architectural consequence |
|---|---|
| **Consent must be purpose-specific** | A boolean `consent=true` is not a consent record. Store purpose, timestamp, source, and **the exact consent text version shown**. |
| **Notification** | Purpose, data collected, and a contact point stated at the point of collection. |
| **Withdrawal as easy as giving** | Self-service preference centre. Withdrawal is not a support ticket. |
| **Retention limitation** | A period must be named — see §7.5. "Forever" is not a retention policy. |
| **Transfer limitation** | Every processor registered with its data category and location (§3.3). |
| **Do Not Call (DNC)** | **A separate regime.** Applies to outbound phone/WhatsApp marketing (§3.5). |
| **Breach notification** | Contact data must be identifiable and deletable as a set (§7.4). |
| **Accuracy** | A report is a dated snapshot. Its inputs must record when they were claimed (§7.3). |

### 3.2 The two-purpose consent model

Identity first (first name, last name, email) so abandoned forms remain contactable. That creates
**two distinct purposes**, which must not be bundled:

1. **Report delivery** — required to deliver what was asked for.
2. **Follow-up / nurture** — optional, separately given, separately withdrawable.

A single checkbox covering both is the common PDPA failure. The architecture carries
**per-purpose consent rows**, so withdrawing one does not revoke the other.

The "finish your review" nudge for abandoned forms falls under purpose 1 (it completes the
requested action) — but that first email must not carry marketing content. That constraint
belongs in the template layer.

### 3.3 Processor register

| Processor | Holds | Location | Note |
|---|---|---|---|
| Supabase | contacts, consent, reports | confirm region | |
| Resend | email address, message content | **US** — transfer clause needed | transactional |
| Brevo | email address, message content, **contact records** | **EU** | marketing. Processor only — §6.4 |
| TypeSafe (Jev) | **form answers + enriched public text only** | US | §5.5 |
| Google (Places, if used) | business query strings | US | not personal data |

### 3.4 `privacy.html` is a launch prerequisite

Current text states: *"We don't run servers that store your data"*, *"There are no ObserveCo
servers that process or store your data"*, *"We never share your data with third parties. No
third-party data processors."* All three become false on launch. Blocking, not cleanup.

### 3.5 The phone number — a different regime

**Collecting a phone number is not the same kind of act as collecting an email.** Three distinct
rule-sets switch on, and two are not PDPA.

**1. It may not be personal data at all — or it may be.** PDPA s4(5) excludes *business contact
information* given solely for business purposes (corporate email, business title, office phone).
A **mobile number is not presumptively business contact information**, and a sole proprietor's
personal mobile is personal data. The schema records `phone_kind` ∈ {business_line,
personal_mobile, unknown}. Treating it as exempt by default is the error.

**2. DNC is a separate regime and it is strict.** It governs *outbound* messages to Singapore
telephone numbers across three registers (No Voice Call, No Text Message, No Fax Message).

| Constraint | Consequence |
|---|---|
| Must check the register **before sending**, unless we hold **clear and unambiguous consent in evidential form** | Consent must be stored as evidence, not assumed |
| A check is valid for **21 days** | Store the check timestamp **on the number**, not the campaign |
| Only **8-digit numbers starting 3, 6, 8 or 9** are accepted | Validate at capture |
| Bulk checking is a **CSV upload, up to 24h**, charged **per number** | A batch job, not a request-path call |
| The *ongoing relationship* exemption covers **text and fax only — never voice** | A WhatsApp follow-up is covered; a **phone call is not** |
| The exemption requires an **opt-out facility inside every message**, reply number live **30 days** | Mandatory, not optional |

**3. WhatsApp adds a private rule-set.** Meta requires opt-in before messaging; since Nov 2024
that may be general (not WhatsApp-specific) if it complies with local law — but it must state
that the person is opting in and **name the business**. Outside a **24-hour customer-service
window**, only **pre-approved templates** may be sent, correctly categorised (utility vs
marketing), with a **per-user marketing-template limit**. Miscategorisation carries platform
penalties.

**Design decision (D10) — phone is a matching key, not a marketing channel.**

We **never send outbound WhatsApp.** The report email carries the same `wa.me` link the rest of
the site already uses, so contact stays **user-initiated** and outside DNC entirely. The number's
job is **inbound matching**: when someone WhatsApps, we resolve the number to a lead and see
their report and stage.

That gets the CRM linkage without opening a regulated outbound channel. If outbound is ever
wanted it needs a fourth consent purpose, an evidential consent record, a DNC check with its
21-day stamp, and an in-message opt-out — none built speculatively.

### 3.6 The input contract

The form is the system's primary input, so its field set is an architectural contract, not UI
copy.

| Step | Fields | Required |
|---|---|---|
| 1 You | First name · Last name · Email · Phone *(optional)* | name + email |
| 2 Business | Business name · Website · Role · **Company size band** | business name |
| 3 Market | Category / what you sell · City | category |
| 4 Position | Current positioning sentence *(or "we don't have one")* · What you believe makes you different · What competitors undercut you on | position |
| 5 Numbers | Your price point · Their price point · How many competitors you can name | drives depth |

**Email is the only hard delivery dependency.** Every other field improves the report; none
blocks it (§4.4). The **cannot-refuse contract** holds: the answers alone must carry all five
scores.

**Company size band is not optional padding (Q10).** Your own
`observeco-consulting-pivot-positioning.md` splits the market into two bookends — 0–9 employees
and 10–500 — with different products and prices aimed at each. Without the band, the free report
cannot route to the right offer and the CRM cannot segment the way the strategy already does.

**Every field is a claim, not a fact.** Self-reported price points and competitor counts are
unverifiable. The report records them as **claimed** and says so; it must never present a
prospect's assertion as a verified finding. This is the discipline the client analyses already
apply — GreenPackers' five certification claims were checked, and two did not resolve.

### 3.7 The form is an open relay, and this is the most serious gap in the design ⚠

**Anyone can POST an arbitrary address to the form and cause observeco.com to email that person
a report about a business they have no relationship with.**

Consequences, worst first:

1. **We process and mail personal data of people who never consented** — a PDPA problem created
   by a third party, using our domain.
2. **Domain reputation collapse.** `sean.foo@observeco.com` is your primary address and
   `observeco.com` carries DKIM. Bulk unsolicited sends from a domain with no sending history is
   how a domain gets blacklisted — and that would take the **transactional** stream down with it:
   licence emails, report deliveries, the lot.
3. **Model spend** from abuse.
4. **Spam-trap poisoning** — permanent, and unfixable once done.

**Architectural consequence: the send is gated on email confirmation.** The submitter confirms
the address before the report is emailed. That proves the address is theirs and yields a
defensible consent timestamp. It is a real UX cost — some leads are lost at the confirmation
step — traded against not being an open relay. **This is a decision for Sean (§12).**

Companion controls, non-negotiable regardless of that decision: per-IP and per-address rate
limits, a bot check at submission, and a **hard daily send ceiling that alerts** rather than
silently exceeding.

### 3.8 Input quality floor

The cannot-refuse contract says a report is always produced. Nothing may distinguish
**comprehensive input** from **`asdf` in every field**. Garbage in produces a confident score
with a verdict sentence, **emailed to a real person under your name** as though it were analysis.

Needed: a measured **input-quality gate** — the minimum signal that must be present before a
score is produced — and a rule that a below-floor submission receives template C instead of a
score. This is the input-side twin of the calibration gate, and it is currently unspecified.

It is one of the gates in §5.4, deliberately, because a bad-input report and a category-trap
report are the same class of failure: the system must be able to decline to score rather than
produce a confident number.

### 3.9 Untrusted input must be contained

Two vectors specific to this form:

- **The website field is an SSRF vector.** We fetch what a stranger typed. Must be scheme- and
  host-validated, denied for private/link-local ranges, fetch-timeout bounded, and never used as
  a filesystem path or a server-side request target beyond a plain GET.
- **Free-text answers are prompt-injection carriers.** "My competitors" is a text field. A
  submitter can place adversarial instructions in it. Content from the form must reach Jev as
  **data in a structured field**, never as instructions, and the enriched web text (§4) is
  equally untrusted.

---

## 4. L2 — Enrichment

Using the Hermes `web-search-scraping-protocol` rather than a hand-rolled scraper. It already
owns the routing (`SEARCH → FETCH → EXTRACT → ESCALATE → GRADE`) and — critically — **it already
owns the problem that would silently corrupt this pipeline.**

### 4.1 The validity gate is mandatory

Measured over 10 mixed URLs: **6 (60%) returned a Cloudflare challenge, an access-denied body, or
a CSS-dense shell as "content" — with no error.** `fetch_markdown` returns a non-empty string;
nothing upstream flags it. A figure regex even matched numbers inside the challenge page's
`<style>` block.

**Why this is architecture, not a bug:** enrichment output is fed to Jev as evidence. If a block
page arrives as ordinary text, **Jev scores a Cloudflare challenge as though it were a
competitor's website**, and the report is confidently wrong.

The protocol's remedy — challenge signature + prose density (>10% CSS-ish) + single-unbounded-line
— is **mandatory, not optional**, and must run before anything reaches L3. It is code, not a model
call, and it has zero residue on a known set. This is the highest-risk seam in the system.

### 4.2 GRADE supplies the "what we couldn't check" section

The protocol's reward layer produces the structured verdict the report needs: grounding for
synthesis tasks, coverage for enumeration. That maps onto the report's confidence band and its
*"what we checked / what we couldn't check"* block.

**The honest-limits section is generated from the grading layer, not written by the model.**
Limits the pipeline observed are real; limits a model narrates are plausible fiction.

### 4.3 Enrichment must not overstate

The free report **cannot** do what the paid engagement does — cross-check competitor claims
against public registries. GreenPackers' analysis found that **of five certification claims,
two did not resolve.** The free report must state registry verification as something it did
**not** do, in the report body, not buried.

Every enriched claim carries its source and fetch timestamp. A claim whose source failed the
validity gate is **absent**, not softened — an unverifiable assertion presented confidently is
worse than a gap.

### 4.4 What enrichment feeds

| Input | Feeds dimension |
|---|---|
| ACRA / data.gov.sg (open, SSIC-filterable) | Market headroom |
| Competitor set via search | Competitive pressure |
| Competitor messaging via fetch | Position availability |
| Competitor size/tenure | Defensibility |

### 4.5 Non-load-bearing by construction

Per the cannot-refuse contract: **the form answers alone must carry all five scores.** Enrichment
is best-effort behind a hard timeout. A failed fetch degrades depth, never existence.

---

## 5. L3 — Scoring

### 5.1 The five dimensions

| # | Dimension | Weight | What it measures |
|---|---|---|---|
| 1 | Market headroom | 15% | Is there room to be chosen at all? |
| 2 | Competitive pressure | 20% | How crowded and price-contested? |
| 3 | Position availability | 25% | Does the word you want already have an owner? |
| 4 | Defensibility | 25% | Hard-to-copy × hard-to-build |
| 5 | Demand reach | 15% | Is there an identifiable, reachable, paying segment? |

Weighted toward 3 and 4 because the brief is *viability through differentiation*, not industry
attractiveness.

### 5.2 Variable dimension set (required by D7)

A dimension that cannot clear is dropped and stated. **The scorer and the report renderer must
support N dimensions from day one** — weights renormalised at runtime, not hardcoded in the
template. A hardcoded five-bar layout makes a four-dimension ship a rewrite.

### 5.3 One rubric, two implementations

The Python calibration harness and the production scorer must read **the same rubric JSON**.
Otherwise calibration validates a scorer that is not the one shipped. This is the most likely way
to fool ourselves.

### 5.4 The composite must be gated, not merely weighted ⚠

**This is the most important correction in this revision.**

With the weights in §5.1, a submission scoring **0 on Market headroom — a textbook category
trap — and 5/5 on every other dimension reaches 85/100, band "Strong."** A weighted sum lets
strength in four dimensions compensate for a fatal flaw in the fifth. That is precisely the error
the Category Trap check exists to catch, and it is the single most dangerous property of the
scoring model as originally written.

TypeSafe's own composite-scoring guidance says the same thing: weights suit **compensating**
preferences, and an *"any serious violation"* rule needs **separate conditions**.

**Fix — the score is two parts.**

**Part 1: gates (hard preconditions).** Evaluated before any composite. A failing gate does not
reduce the score; it changes what the report **is**.

| Gate | Condition | If failed |
|---|---|---|
| **G1** Category trap | Market headroom ≥ 2/5 | Report states *category trap* — no composite is shown |
| **G2** Commodity floor | Competitive pressure ≥ 1/5 | Report states the market is priced to the floor |
| **G3** No open position | Position availability ≥ 1/5 | Report states the position is occupied |
| **G4** Nothing to defend | Defensibility ≥ 1/5 | Report states there is currently no differentiator |
| **G5** No identifiable buyer | Demand reach ≥ 1/5 | Report states the customer is undefined |
| **G6** Input floor | §3.8 minimum signal met | Template C — no score |

**Part 2: the weighted composite**, computed only when all six gates pass. Bands: Fragile (5–39) ·
Contested (40–59) · Viable, conditional (60–74) · Strong (75–95), clamped to 5–95 so no score can
imply certainty the method lacks.

**The gate thresholds are hypotheses**, calibrated exactly as the weights are (§10).

A gate failure is still a **useful report** — arguably more useful, because it names the one
thing that is wrong rather than averaging it away. It is also the honest answer, and the version
a prospect can act on.

### 5.5 The verdict and the one gate must be computed, not written

If a language model writes the verdict sentence, two identical submissions can produce different
verdicts — and §10.2's reproducibility claim becomes false. **A report we cannot reproduce is a
report we cannot defend.**

- **The verdict is a predicate** over (band, weakest dimension, failed gates). The sentence is a
  **template** filled from it, not generated.
- **THE ONE GATE is an argmin** over weighted contribution, tie-broken by confidence then by
  dimension order. Deterministic, and explainable when a prospect asks why.

Jev supplies judgments. Code supplies the verdict. That is the doctrine in §1, applied to the
sentence and not just the number.

### 5.6 Unit discipline (measured)

Jev returns **one aggregate verdict for a multi-item state** (verified: 42 inputs → 1 answer) and
**blends differently-scoped inputs into ~0.50 confidence**. Therefore:

- Per-competitor judgments **fan out one call each**; code aggregates.
- One narrow judgment per call. Never a batch.
- **Confidence is label-set-width dependent:** `conf = (n·p − 1)/(n − 1)` — confirmed against
  TypeSafe's own documentation. A five-level score needs a different gate from the 3-option
  choices gated at 0.70 in `ask_jev.py`.

### 5.7 Egress boundary

Jev sees **form answers and enriched public text only.** Never the CRM, never other contacts,
never client analyses. Deliberate egress decision, recorded in the processor register (§3.3).

### 5.8 The rubric is the asset, and it sits behind a free form

The five dimensions, their weights, the gate thresholds and the band boundaries **are the method**.
A competitor can submit once, receive a report, and reverse-engineer a meaningful part of it.

The substance is withheld (§7.2), so the exposure is bounded — but it is real. **The report shows
scores and reasoning without exposing the criteria text, the weights or the gate thresholds.** No
debug output, no raw Jev payloads, no rubric version in email bodies.

### 5.9 Dependency on a single model vendor

TypeSafe is a single, versioned dependency (`jev-1.13.0`) for the product's core judgment. If it
changes behaviour (§11.1), raises prices, or disappears, the scorer stops. The rubric JSON (§5.3)
is the mitigation: it is the transferable asset, and a different model can be evaluated against
the same calibration corpus. That evaluation is a real cost and should be scoped before it is
needed, not during an outage.

---

## 6. L4 — Delivery

### 6.1 The cost question, answered honestly

At realistic volume (~100 leads/month × ~4 emails ≈ 400 emails/month), **every option is free.**
The SES advantage materialises only above roughly 500K emails/month.

| Provider | Free tier | Paid entry | At 1M/mo | Notes |
|---|---|---|---|---|
| **Resend** | 3,000/mo (100/day cap) | $20 / 50K | ~$400 | Already half-wired here |
| **Brevo** | 9,000/mo (300/day) | $9 / 5K | ~$249 | Marketing + automation; EU |
| **AWS SES** | 3,000/mo | $0.10 / 1K | **~$100** | No UI, no templates; sandbox exit by support case |
| SendGrid | **none** (60-day trial) | $19.95 / 50K | enterprise | Free tier retired May 2025 |
| Postmark | 100/mo | $15 / 10K | ~$1,800 | Best transactional; discourages marketing |

**Do not switch to SendGrid.** It costs more than the current setup and buys nothing. The
cheapest genuine option is SES, and it is only cheap in money — it costs templates, suppression
handling and reputation work, which is what we would otherwise have to build. Resend already sends
*through* SES (`send.observeco.com` MX → `feedback-smtp.ap-northeast-1.amazonses.com`); we are
paying for the wrapper.

**Decision:** **Resend** for transactional, **Brevo** for marketing (D8). Both **swappable**.

The decisions that would reopen this: marketing sends > ~9,000/month, transactional > 3,000/month,
or total > ~500K/month (SES becomes materially cheaper). None are near.

### 6.2 Two streams

**Never send marketing through your transactional path.** Complaint rates from a blast degrade
shared IP reputation, and then report emails start landing in spam.

| Stream | Subdomain | Provider | Carries | Unsubscribe |
|---|---|---|---|---|
| Transactional | `send.observeco.com` (exists) | Resend | report, holding, need-more-detail, confirmation | not required, still advised |
| Marketing | `mail.observeco.com` (**to create**) | **Brevo** | nurture, blasts | **required** |

Both authenticate by **DKIM alignment**; neither relies on SPF (Brevo's stays unaligned on shared
IPs; Resend's is already incomplete — §11 F4). DMARC `p=none` **reports rather than rejects**, so
a misconfiguration degrades silently. Verify each domain reaches *Authenticated* in its provider
dashboard before trusting it.

`mail.observeco.com` does not exist yet — no A record, no TXT. DNS is Cloudflare
(`isabel`/`ivan.ns.cloudflare.com`).

### 6.3 The provider abstraction

D3 requires blasting later to be a **configuration change, not a rebuild**:

```
EmailProvider
  send_transactional(to, template, vars, reply_to)
  send_bulk(to, template, vars, unsubscribe_token)
```

Registered by name, selected per stream by config. The existing
`src/observeco/emails/sender.py` + `templates.py` registry is the layer to extend — add a
`stream` field per template rather than replacing the registry.

### 6.4 Brevo is a processor, never a contact store

Brevo is not only a sender — it **stores contacts** (100k free), has contact attributes, and ships
a **website tracker** that collects "identified contacts" who "have not necessarily subscribed to
receive your emails."

Used carelessly that creates a **shadow CRM with its own consent state**. The failure is specific:
Supabase says "withdrew marketing consent on 12 Oct"; Brevo still holds them in a marketable list.
**A second copy of personal data with no synchronised purpose record is a PDPA problem regardless
of which copy is "authoritative."**

| Rule | Reason |
|---|---|
| Supabase is the **system of record**; Brevo holds a **projection** | One authoritative consent state |
| Push **only contacts with active marketing consent** | Never mirror the whole CRM |
| On withdrawal, **propagate deletion to Brevo** | Withdrawal must be as easy as giving |
| **Do not install Brevo's website tracker** | It collects non-subscribers as contacts |
| Do not use Brevo forms/landing pages as the entry point | Consent is captured and versioned by us |
| Suppression lives in Supabase (§6.5) | A provider swap must not resurrect unsubscribed contacts |

**Treat any contact present in Brevo but absent from Supabase as a defect to reconcile, not a
lead.**

### 6.5 Own your suppression list

Bounce and complaint suppression lives **in Supabase, checked before every send** — not only in the
provider. Providers differ, and a provider swap must not resurrect unsubscribed contacts. Provider
webhooks (`email.bounced`, `email.complained`) write into it.

### 6.6 Unsubscribe must be real

`_UNSUBSCRIBE_LINK` currently points to `https://observeco.com/unsubscribe` → **404**. Needs a
signed-token endpoint, no login required. PDPC's most common enforcement action is ignoring
opt-outs.

### 6.7 The report must survive its own delivery

The email is the product surface, so it carries the same integrity requirements as the page:

- **Plain, terminal-readable HTML.** No reliance on images, web fonts or external CSS — the
  `logo.png` 404 (§11 F3) is exactly this failure class, and it would have shipped a broken brand
  mark to every prospect.
- **Disclaimer present in the body** — what the report is and is not, and that no human reviewed
  it. If a prospect acts on a 62 and it goes badly, that line is the difference between a report
  and advice.
- **Reproducible and attributable** — it carries its provenance (§10.2), so it can be defended.
- **Readable at 360px and in a text-only client.** The bar visualisations must degrade to text.

### 6.8 The 30s wall

`vercel.json` caps `api/**/*.js` at `maxDuration: 30`. Jev + enrichment + email exceeds this. **The
report is queued and worked asynchronously** — the request path only validates, records, and
returns "on its way."

---

## 7. L5 — CRM, data model, retention

### 7.1 Full pipeline (defined now so nothing is re-scoped later)

| Stage | Entry | Exit | Automatable |
|---|---|---|---|
| 0 Captured | Form submitted | Confirmed / report queued | ✅ |
| 1 Report delivered | Email sent | Open / click | ✅ |
| 2 Engaged | Opened, no reply | Reply or call booked | ✅ |
| 3 Conversation | Replied / WhatsApp | Sean has spoken to them | ❌ |
| 4 Qualified | Call done | Fit decided | ❌ |
| 5 Proposal | Price quoted | Accept / decline | semi |
| 6 Won | Paid | Delivered | semi |
| 7 Delivered | Engagement closed | Renewal offered | ❌ |
| 8 Watch | Subscription active | Churn | semi |
| 9 Lost / Nurture / Dormant | — | Re-approach | ✅ |

The schema carries all ten stages from day one, so scaling is a **mapping, not a redesign.**

### 7.2 Company size routes the offer (Q10)

Company size band (§3.6) is what lets the free report point at the right paid tier — the 0–9
bookend toward the Differentiation Strategy, the 10–500 bookend toward the Watch or the deep-dive.
Without it the report ends in a generic CTA and the qualification job fails.

**The free report's success metric is not report quality. It is the fraction of recipients who
book a call.** That number is the design target (§8.2), and it is currently unmeasured.

### 7.3 The claimed-facts rule

Every figure a submitter supplies is stored with `claimed_at` and marked `source: self_reported`.
Nothing self-reported is ever presented as verified (§3.6). The report distinguishes:

- **Claimed** — what the prospect told us
- **Observed** — what enrichment found and the validity gate passed
- **Not checked** — registries, financials, anything the free report cannot verify (§4.3)

### 7.4 Entities and the deletion guarantee

**Entities:** Contact · Company · Report (versioned artifact) · Activity (records *who initiated* —
§3.5) · Deal (stage, value, Stripe linkage) · Sequence · **Consent** · **Suppression** ·
**Enrichment cache**.

**RLS:** deny anon entirely on every new table; service-role only. The existing licensing schema
grants `licenses_anon_select` with `USING (true)` — anyone holding the anon key reads every row.
That policy must not be cloned.

**Breach/erasure requirement:** a contact must be identifiable and deletable **as a set** across
every table — including the enrichment cache, the report artifacts, the Brevo projection and the
Activity log. Without that, a PDPA access or erasure request cannot be answered, and the breach
notification obligation cannot be met.

### 7.5 Retention must name a period

§3.1 requires a retention policy; a policy without a period is not one. Three categories, each
needing an explicit choice from Sean:

| Data | Provisional | Rationale |
|---|---|---|
| Consent records | Keep longest — outlive the contact | They are the **evidence** that made processing lawful |
| Reports (artifacts) | Medium — e.g. 24 months | Defensible if a prospect disputes a score |
| Contacts who never converted | Shortest | Least value, most risk |
| Enrichment cache | Short — days | Public data, cheap to refetch, but stale claims mislead |

### 7.6 The system of record has no durability story

Supabase is now the **sole** record for contacts, consent and reports. Losing it means losing the
consent evidence — the thing that makes the marketing lawful.

Needs the same discipline as the existing `sqlite-durability` and drift-durability work:
scheduled export, **verified restore** (not just a backup file that has never been opened), and
**consent rows exported somewhere independent of the operational database**. A backup that lives
in the same provider as the data is not a durability story.

---

## 8. Accountability, operations, and asset protection

### 8.1 Who owns a wrong answer (Q6)

The site promises, on `/method`: *"A person answers for every recommendation"* and *"AI does the
analysis. A person owns the answer."*

**The free report deliberately breaks that promise** — it is generated and sent with no human in
the loop. That is a defensible trade (free, instant, caveated), but it creates a specific
obligation: **the report must not borrow the credibility of a promise it does not keep.**

Concretely:

- The free report **never** uses the phrase "a person reviews/owns every recommendation."
- The AI-only caveat sits **in the report body and the hero**, not in a footnote.
- The **paid** engagement may use that language, because it is true there.

**Named authority.** Someone must be able to stop the pipeline. The degradation ladder (§10.4) is
automatic, but a human override is needed for the case where the scorer is producing bad reports
and the canary has not yet caught it. That is **Sean's call, and the kill switch must be a
one-action operation** — a feature flag, not a deploy.

**The report speaks under Sean's personal email address.** That is a deliberate signal (a human is
reachable) and a real exposure (a machine's judgment carrying a person's name). It only stays
defensible while the caveat is honest.

### 8.2 Instrumentation (Q7)

Nothing is currently measured, so there is no way to know whether the page works and no evidence to
tune it. The minimum set:

| Metric | Why |
|---|---|
| Submissions, by step | Where the form loses people |
| Confirmation rate | The cost of the open-relay fix (§3.7) |
| Report delivered / opened / clicked | Whether the report lands and is read |
| WhatsApp clicks → calls booked | **The actual success metric (§7.2)** |
| Deals won, by company-size band | Whether the routing works |
| Gate failures, by gate | Whether the gates are calibrated or just firing |
| Queued / held / failed / retried | Pipeline health (§8.3) |
| Per-report cost | Jev + Places + DNC checks |

### 8.3 The pipeline monitors nothing — and this is an observability company

ObserveCo's entire proposition is that agents must be observable. This spec builds a multi-stage
async pipeline with a gated scorer, a regression canary and a degradation ladder — **and monitors
none of it.** The canary (§10.3) covers the *scorer*; nothing covers the *worker*. An unmonitored
pipeline that silently stops emailing is **precisely the failure ObserveCo sells against.**

Required, and it should use the existing capability rather than a parallel invention:

- **Worker liveness** — did the cron run, and did it drain the queue?
- **Queue depth and age** — the oldest unprocessed row is the leading indicator; a report that is
  6 hours old is broken even if nothing threw.
- **Failure classification** — provider down, model down, enrichment blocked, gate refused.
- **Alert to Sean** on any of the above, through the same channel the rest of the fleet uses.

### 8.4 Failure modes the queue introduces

The queue is necessary (§6.8) and brings its own failures, none currently addressed:

| Failure | Consequence | Mitigation |
|---|---|---|
| **Duplicate processing** | Two emails to one prospect | Idempotency key per report; claim is atomic |
| **Poison message** | One row retried forever, blocking the batch | Bounded retries, then `failed` + alert, never infinite |
| **Stuck `processing`** | Rows claimed by a worker that died | Lease with a timeout; reclaim after expiry |
| **Concurrency** | Two workers claim the same row | Atomic claim (`UPDATE … WHERE status='queued' RETURNING`) |
| **Cron never fires** | Silent stop | Liveness check (§8.3) — Vercel cron is best-effort, not a guarantee |
| **Partial completion** | Email sent, status not updated | Write the artifact **before** the send; the send is the last step |

### 8.5 Cost ceilings (Q10)

Jev is cheap (measured ~$0.0009 per 40 items) and volume is low, so this is minor — but two costs
scale with **abuse** rather than with success: Google Places at $5/1k, and per-number DNC checks
(§3.5). §3.7's rate limiting is the mitigation; a **spend alert** is the backstop. A ceiling that
is never hit is cheap insurance; a bill discovered at month end is not.

### 8.6 The rubric is the asset (Q9)

See §5.8. The design consequence belongs here too: the report shows **scores and reasoning**;
it never shows the criteria text, the weights, the gate thresholds or raw model payloads. Nor
does it expose `rubric_version` in a body a competitor can read.

---

## 9. Jurisdiction

**PDPA is Singapore law, and the spec has assumed Singapore throughout without saying so.**

| Question | Position needed |
|---|---|
| What happens when a prospect is in the EU/UK? | GDPR applies to offering services to data subjects there — a lawful basis, a fuller notice, and stricter consent |
| Do we accept non-SG submissions at all? | Either the form states the scope, or the consent notice and processor register need a GDPR variant |
| Where do US/other prospects sit? | No equivalent regime, but the processor register still applies |

The cheapest correct answer is likely **to scope the offer to Singapore explicitly** — the product,
the pricing, the registries and the method are all SG-specific. But that is a **decision**, and
leaving it implicit is the one option that is definitely wrong.

---

## 10. Calibration and regression

### 10.1 The calibration corpus

Six real engagements where the correct answer is known:

| Case | What the analysis concluded |
|---|---|
| GreenPackers | Fringe, <1%; guerrilla warfare the only play |
| Bonefirm | Feasible, with one condition (B1) |
| CaiCa | Reason-to-purchase not strong; position must be earned first |
| PetDirectory | Market real, position open, but the demand side is unbuilt |
| SGFitness | White space identified in a specific demographic |
| SaladShop | CBD saturated at every tier; white space outside it |

Labels are **the position as it stood at engagement start**, fed to Jev, which must reproduce the
analysed conclusion — the only correct analogue to production, where Jev scores a form submission
rather than a finished analysis.

### 10.2 Provenance — every report carries

`rubric_version` · `model_id` (as returned by the API) · `prompt_hash` · `input_hash` ·
`enrichment_sources[]` · `dimensions_used[]` · `gates_evaluated` · `generated_at`

A report we cannot reproduce is a report we cannot defend to a paying prospect.

### 10.3 The canary

The six cases run **on a schedule** — the pattern ObserveCo's existing canary infrastructure
already uses. Same inputs, fixed expected outputs.

| Trigger | Response |
|---|---|
| Any case moves band | **Alert Sean** |
| Composite moves > 8 points | Investigate before the next send |
| `model_id` changes | **Alert regardless of scores** — re-baseline and re-verify |
| Any gate changes state | Investigate — the gates are the safety layer |
| Negative control stops failing | **Scorer is broken. Halt.** |

### 10.4 Degradation ladder

| Tier | Condition | Behaviour |
|---|---|---|
| 1 | Canary green | Scorer live |
| 2 | Canary flags, ≤1 case | Serve reports **stamped with the drift notice**; hold the moved dimension |
| 3 | Canary fails, >1 case | **Feature-flag the scorer off.** Capture continues. Reports queue `held` |
| 4 | Model unreachable | Queue `held`; **never substitute a different model silently** |

**Tier 4 is the important one.** Substituting a local model for a judgment task is a documented
failure mode here — a local model scored 12/12 *wrong* at ~0.9 confidence on a comparable taxonomy.
**A confident wrong label is worse than no label.**

Reports already in flight when a regression is detected are **held**, not sent. The holding email
is honest: we are re-running your review. No score is promised and none is withdrawn.

### 10.5 What the calibration gate can and cannot prove (Q1)

This is the weakest part of the design, and it should not be oversold.

1. **It measures agreement, not accuracy.** The label is what a completed analysis concluded — and
   those analyses were themselves AI-assisted work by the same method. Correlated errors would
   agree with each other and still both be wrong. The gate cannot detect a shared bias.
2. **Six cases is a thin corpus**, and all six are hand-shaped engagements by the same author. They
   are **not drawn from the population the free form actually sees** — a stranger's thin,
   self-reported submission is a different distribution.
3. **"Same band, ±1 level" is coarse.** Across four bands and six cases, agreement by luck is
   plausible. The honest reporting is to publish the expected agreement rate **and** the observed
   one, not just a pass/fail.
4. **One negative control proves the scorer *can* fail — not that it fails for the right reason.**
   Several controls are needed, spanning distinct failure modes: an empty field, a self-
   contradictory answer, a generic positioning sentence with no differentiator.
5. **There is no human baseline.** We have never measured what a competent human — Sean — scores
   from the same inputs, blind. Without it we cannot claim Jev approximates good judgment; only
   that it agrees with the documents.

**The cheapest fix for #5 is one hour of work:** Sean scores the six cases from the form-shaped
inputs, blind, before seeing Jev's. That single number — human agreement versus model agreement —
is the only evidence that the instrument measures something real, and it costs almost nothing.

### 10.6 Launch gate

**Ship the scored report only when Jev clears all six cases and fails the negative controls as
predicted.** "Clears" = same band per case, every dimension within ±1 level, all gates stable,
controls fail.

**Disagreement triage — judge-vs-corpus disagreement is UNRESOLVED until hand-read.** Do not
default to "Jev is wrong"; that has been the wrong call before.

| Branch | Condition | Action |
|---|---|---|
| J1 | Hand-read confirms Jev missed | Fix criterion/unit/gate. Jev was wrong. |
| J2 | Hand-read confirms the analysis missed it | Correct the label — **a finding about our own method** |
| J3 | Both defensible | Dimension genuinely ambiguous → **drop it and state it** (D7) |

---

## 11. Two-stage ship (per D4)

Calibration gates the **scoring** layer only. Capture, payment and delivery do not depend on it.

| Stage | Contents | Gate |
|---|---|---|
| **MVP-0** | Page + form + CRM capture + Stripe for the paid engagement. **No free score.** | Ships when ready |
| **MVP-1** | The free scored report | Calibration clears (§10.6) |

MVP-0 is honest standing alone — it is a lead form for the engagement, which is what the site
already promises. It never promises a score, so **if calibration blocks, no prospect ever learns we
tried.** Prospects captured during MVP-0 gave details for the paid engagement; no "your report is
coming" obligation exists, and the free review can be offered later as a fresh, honest gift.

Three report templates: **A** report · **B** holding (regression) · **C** need-more-detail (inputs
below the floor — names exactly what is missing, never a dead end).

**Principle set, applies to every send:**

1. Never send a score we don't trust.
2. Never claim human review on a free report (§8.1).
3. Always carry the confidence band and "what we couldn't check".
4. Never present a claimed fact as a verified one (§7.3).
5. If we can't score, say precisely what we'd need.
6. Every email carries a working unsubscribe (§6.6 — currently 404).

---

## 12. Verified findings — constraints on the design

Measured, not assumed.

| # | Finding | Consequence |
|---|---|---|
| F1 | `POST /api/stripe/webhook` → **500** in production (expected 400) | Throw before the `try`; leading hypothesis is an unset `STRIPE_SECRET_KEY`. **The Stripe path cannot be verified until resolved.** |
| F2 | That handler inserts `licenses` rows with `product_slug: 'solo'` | Consulting payments need a **separate endpoint** (§7.4) |
| F3 | `logo.png` → 404 (live logo is `assets/logo.svg` → 200); `/unsubscribe` → **404** | F3b is a PDPA blocker (§6.6); F3a is the failure class §6.7 guards against |
| F4 | DKIM present on `observeco.com`; `send.observeco.com` MX is Resend's SES endpoint, but its SPF omits Amazon SES; DMARC `p=none` | Likely functional via DKIM alignment, but **degrading silently** |
| F5 | `sean.foo@observeco.com` is inbound-only (Cloudflare Email Routing) | Sending as it needs only domain authorisation; **set Reply-To explicitly** |
| F6 | `privacy.html` states we run no servers and use no processors | **Launch prerequisite** (§3.4) |
| F7 | `licenses_anon_select` is `USING (true)` | Do not clone this RLS policy (§7.4) |
| F8 | `maxDuration: 30` on `api/**/*.js` | Forces the async queue (§6.8) |
| F9 | **Zero `<form>` elements** across the live site | First-ever data collection |
| F10 | `content-spec-v1.md` promised a free "positioning snapshot"; grep finds it on **no** live page | This feature is that promise, re-scoped |
| F11 | A category trap (0 on Market headroom) reaches **85/100 — "Strong"** under the original weights | **The composite must be gated** (§5.4) |

**Backend note:** the pricing research in §6.1 ran on the keyless fallback because the configured
ddgs backend failed that call. Re-verify figures against the providers' own pages before a
purchasing decision.

---

## 13. Decisions required

| # | Decision | My recommendation |
|---|---|---|
| **D11** | **Email confirmation before send** (§3.7) — the open-relay fix | **Yes.** The domain-reputation risk outweighs the lost leads |
| **D12** | **Input-quality floor** (§3.8) — where G6 fires | Derive from calibration, not intuition |
| **D13** | **Gate thresholds** for G1–G5 (§5.4) | Start at the stated values, calibrate |
| **D14** | **Jurisdiction** (§9) — scope the offer to SG, or build a GDPR path | Scope to SG explicitly |
| **D15** | **Retention periods** (§7.5) | Provisional table stands as the starting point |
| **D16** | **Human baseline** (§10.5) — Sean scores the six cases blind | **Yes.** One hour, and it is the only validity evidence we can get cheaply |
| **D17** | **Nurture cadence and exit rules** (D3) | Defer — low priority, architecture supports it |
| **D18** | **The name** (D1) | KIV |

---

## 14. What this spec does not claim

- That Jev will clear the gate. §10.6 exists because it may not.
- That clearing the gate proves accuracy. §10.5 — it proves agreement.
- That the weights or gate thresholds are correct. They are hypotheses (§5.1, §5.4).
- That enrichment will be reliable — §4.5 makes it non-load-bearing.
- That the current Stripe path works — F1 says it does not.
- That any provider choice is permanent — §6.3 keeps it reversible.
- That the free report can ship before calibration clears — §10.6 is a hard gate.
- That the open-relay risk is closed — it is identified (§3.7) and needs D11.
