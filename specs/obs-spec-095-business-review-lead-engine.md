# OBS-SPEC-095 — Business Review Lead Engine

**Status:** DRAFT v12 — benchmark mechanics corrected against industry practice.
**Date:** 2026-09-23 (v8–v11: 2026-09-27–28; v12: 2026-09-28)
**Owner:** Sean
**Name:** KIV (D1)
**v5 change:** Blind-spot appendix removed and its content integrated into the owning sections.
The ten questions (§1.1) now frame the document. **§5.4 is new and changes the scoring model** —
a gate layer in front of the weighted composite. Accountability (§8), monitoring, jurisdiction
(§9) and asset protection are now architectural sections rather than footnotes.
**v6 change:** D11 accepted — Turnstile captcha + confirmation before send (§3.7), with the
ordering that makes it the real LLM-spend protection. The two-way benefit is now §7.7: submissions
are primary research, which adds a third consent purpose (D19). **§3.10 is new** — the B2 working
note. D12 remains open.
**v7 change:** D12 accepted — an inadequate submission gets a polite guidance email (template C as
coaching, with minimum-viable examples and a pre-filled resubmit), with **unlimited resubmission**.
Safe because confirmation gates the queue. Added the send-budget rule: all sends count against one
ceiling, and at the ceiling the site stops accepting rather than queueing.
**v8 change — calibration integrated. §5.1 is a SIX-dimension set and §5.4 no longer contains
score gates**; both described 0.9.0 and were corrected against measured results (§10.7 is new).
D13 superseded, D16 fulfilled, D20–D23 added. §10.6's launch criterion is now band agreement
(D20), §5.3.1 records the rubric-promotion build gate, and §10.1.1 separates the canary from the
calibration corpus.
**v9 change — the three open build blockers cleared.** **D23 DONE:** the canary corpus is complete
(6 of 6), baselined and running; **§10.8 is new** and records the build, the result (6 of 6 within
one band, 4 of 6 exact, 0 gross errors) and the caveat that the fixtures are *authored from* the
engagements rather than captured from intake forms. **D22 DONE:** `rubric.json` promoted 0.9.0 →
1.8.0 through a gated script, so the instrument §10.7 validated is now the one in service.
**D19 DECIDED:** a separate unticked research-consent box with a free refusal, and the
"we maintain SG industry datasets" claim is **downgraded to conditional** on the measured opt-in
rate *and* the k-anonymity floor. §10.6's gate table now shows the canary rows passing, leaving
**negative controls** as the single open row.
**v10 change — the research purpose is a TRADE, not a favour.** Modelled on benchmark reciprocity
(salary surveys, benchmarking consortia): the consent **unlocks the benchmark**, so the checkbox is
not "may we use your data" but "see how you compare". This replaces v9's "refusal costs nothing"
with a sharper, load-bearing rule — *the withheld benefit must be the collective good, never the
service*; the scored report is never gated, or the consent is coerced. **§7.7.1 is new** and records
the finding that de-risks the whole premise: **the calibration corpus IS the seed dataset** — 120
businesses across 27 categories, 11 of which already clear a minimum cell of 5 — so the reciprocity
engine can work from day one without a cold-start problem. It also records the **Singapore-specific
re-identification risk** that no generic k-anonymity floor addresses: our contributors are each
each other's direct competitors. §7.2 now carries the benchmark as a leading funnel metric and §8.2
tracks it. **D24 (enrichment provenance) and D25 (minimum cell size) are new and open.**
**v11 change — the design is checked against how comparable firms actually operate.** Research is in
`specs/calibration/RESEARCH-benchmark-model.md`, with a verification status on every claim
(VERIFIED / REPORTED / BLOCKED) because subagent output is a self-report. What changed:
**D25's shape is corroborated** — Payscale publishes a floor of *"five or more"* **plus** geographic
broadening, so both the floor and the widen-not-suppress step are real practice, not inference; but
its 5 protects employees who are not each other's competitors, so ours needs to be higher.
**A third path is added to §7.7's two-box retention table** — Levels.fyi licenses records carrying
employer/title/level/location under contractual anti-re-identification terms, which is *not*
anonymisation and is what appears to work at scale (D26). **§7.9 is new**: Singapore already gives
free business advisory to ~25,000 SMEs a year through 10 SME Centres and adds diagnostic toolkits
in 2027 — so "free" is not the differentiator — and EDG funds consultancy only through TR 43 / SS 680
certified consultants (D27). Turnstile is confirmed and a **cost ceiling distinct from the rate
limit** is required (reCAPTCHA fails open; ~$0.0024 per submission so volume, not unit cost, is the
risk). The §3.10 floor now **states the minimum threshold to the user** rather than only enforcing
it. **EU AI Act Art 50 is a wording check, not a feature** — and its human-review exemption creates a
tension with §8.1 that stays consistent only outside the EU.
**v12 change — a fifth stream CONTRADICTED a decision made in v11, and the correction is recorded
rather than quietly amended.** §7.7.1 had recommended *"widen rather than suppress"* on the reasoning
that suppression strands the thin-cell contributor. **The industry norm is suppression**, and the
formal discipline adds a rule we did not have: **secondary suppression**, so a withheld cell cannot
be recovered by subtraction from published totals. **Three controls were missing entirely**, all now
added: a **concentration cap** (a count floor of 5 does not stop a single dominant contributor being
recoverable — in a concentrated SG category a "5-business median" is roughly that business's price;
industry uses 25/50/70%). **Absence flags leak cell size** — the refusal message must not state the
count, and we should not publish a participant list (Agri Stats 2026 expressly targets both).
**The two-tier disclosure** (Culture Amp: *"emerging"* vs standard) replaces v11's flat floor of 8,
because a flat 8 suppresses 19 of 27 categories while the two-tier keeps the engine alive at 5 and
the stricter guarantee at 8. A **submission identity/validation gate** is added as D28 — fabrication
is caught by identity, not statistics, and our anonymous self-report form has no gate. Two v11
claims gained support: **Milliman's standing promise** — never to use a participant's data *"in other
consulting engagements"* — **independently corroborates §7.8's reuse boundary**, which I had written
as a judgement call; and **panel re-contact is legitimate** if permission was given at the previous
contact and re-contact matches the original assurance (MRS B.11/B.12). **PDPC's Singapore
k-anonymity guidance is 3–5 — below the industry floor of 5.**

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

**⚠ The served file is `website/privacy.html`, not the root `privacy.html`.** `vercel.json` sets
`outputDirectory: "website"` — verified — and two near-duplicate copies exist (199 vs 205 lines,
different content). **Edits must be made to `website/privacy.html` or they will not reach the
live site.**

Four statements in the served copy become false on launch, and the **meta description is one of
them** — so the claim Google renders first is affected, not just body copy:

| Location | Text | Why it becomes false |
|---|---|---|
| `<meta name="description">` | *"Local-first AI agent monitoring — your data never leaves your machine."* | Form submissions leave the submitter's machine into Supabase |
| §1 "the short version" | *"We don't run servers that store your data. We don't have user accounts."* | The CRM stores contacts; leads are records |
| §1 | *"We don't sell your data because we never see it."* | We see the submitted data |
| §2.2 | *"This data never leaves your machine"* | False for the form path |
| § | *"We never share your data with third parties. No third-party data processors."* | Supabase, Resend, Brevo, and the model vendor are all processors (§3.3) |

**This is blocking, not cleanup**, and it is a *rewrite for two regimes* rather than an edit: the
page currently describes a local-only product truthfully, and must describe a product with both a
local path and a hosted data path. **The root `privacy.html` is not served and should be deleted
or reduced to a pointer**, or the next person will edit the wrong file — as this spec's own
finding came close to doing.

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

**Decision (D11, accepted): a captcha at submission + confirmation before send.**

**Captcha — Cloudflare Turnstile.** Free for unlimited challenge volume; Managed mode is free for
everyone; 20 widgets per account; does **not** require the Cloudflare CDN, so it works on a Vercel
site. You already run Cloudflare for DNS, so there is no new vendor. **Research supports this
choice** (`RESEARCH-benchmark-model.md` §5.3): Turnstile is free and unlimited, whereas reCAPTCHA
**fails open** — it can return a static high score when over quota, silently — and **visible**
captchas cost up to ~40% of form conversions.

**A cost ceiling is needed ON TOP of the rate limit, and it is a different control.** The captcha
stops a bot; a rate limit stops a burst; neither stops **slow volume from many addresses** or
**adversarial drain** (services exist specifically to burn a competitor's API credits). Raw model
cost is trivial — roughly **$0.0024 per submission, ~$24 per 10,000 assessments** — so the risk is
not unit cost, it is unbounded volume: a documented case saw **one user trigger a $700 overnight
bill**. **Add a hard spend ceiling that halts the queue**, distinct from the per-IP rate limit and
consistent with the send-budget rule (§11).

**⚠ But the captcha does not protect the thing you want protected, on its own.**

A captcha stops automated *submission*. It does not stop LLM spend. **The model calls happen in the
worker**, and if the worker runs on unconfirmed submissions, a bot that solves one challenge still
triggers a full Jev + enrichment run — and can do it repeatedly with different addresses.

**The confirmation gate is what actually protects the LLM budget**, because it moves *all* model
work behind a verified address. That ordering is the design, not an implementation detail:

```
submit (captcha)  ──> store as `pending`     ──> confirmation email      [zero model cost]
                          │
                          └── confirmed ──> queue ──> enrichment ──> Jev ──> report
                                                                   ↑
                                            nothing reaches this until the address is proven
```

Consequence: **an unconfirmed submission costs nothing but a row and one email.** That is the
strongest spend protection available, and it is free — it falls out of the confirmation gate rather
than requiring a separate budget mechanism.

Residual controls after both: per-IP and per-address rate limits, and a **hard daily send ceiling
that alerts** rather than silently exceeding.

**The two-way benefit.** You are right that this is not one-directional, and it is worth naming
because it changes the data model: a quality submission is not only a report request, it is
**primary research** — self-reported price points, competitor counts, and positioning statements
from SG SMEs. That is the raw material behind the industry-dataset claim your consulting offer
already makes as its moat (§7.7). It also has a consent consequence, which §7.7 sets out.

### 3.8 Input quality floor

The cannot-refuse contract says a report is always produced. Nothing may distinguish
**comprehensive input** from **`asdf` in every field**. Garbage in produces a confident score
with a verdict sentence, **emailed to a real person under your name** as though it were analysis.

Needed: a measured **input-quality gate** — the minimum signal that must be present before a
score is produced — and a rule that a below-floor submission receives template C instead of a
score. This is the input-side twin of the calibration gate, and it is currently unspecified.

It is one of the two refusals in §5.4, deliberately, because a bad-input report and an
unassessable business are the same class of failure: the system must be able to decline to score
rather than produce a confident number. (It is **not** a score gate — those were removed; see
§5.4. A low score is a finding, not a refusal.)

### 3.9 Untrusted input must be contained

Two vectors specific to this form:

- **The website field is an SSRF vector.** We fetch what a stranger typed. Must be scheme- and
  host-validated, denied for private/link-local ranges, fetch-timeout bounded, and never used as
  a filesystem path or a server-side request target beyond a plain GET.
- **Free-text answers are prompt-injection carriers.** "My competitors" is a text field. A
  submitter can place adversarial instructions in it. Content from the form must reach Jev as
  **data in a structured field**, never as instructions, and the enriched web text (§4) is
  equally untrusted.

### 3.10 The input-quality floor (D12, accepted)

A report cannot always be produced, and refusing to score is a **feature**, not a failure: a
confident score on unusable input is worse than an honest request for more detail.

**The governing principle — quality is not a word count.** The floor should measure **what we can
actually judge about their position**, not how much they typed. A 400-character answer naming the
category, three competitors and a price is scorable; 2,000 characters of vision and journey copy
scoring nothing.

**What the input must carry.** One signal per scored dimension:

| Slot | Drives | Refused when |
|---|---|---|
| Category / what the business does and to whom | Market headroom · Competitive room | Absent or non-specific enough to place in a category |
| A positioning or differentiator sentence | Relative strength · Mental advantage · Defensibility | Absent or a **non-position** — see below |
| Competitors, named or counted | Relative strength | Zero, **and** enrichment finds none |
| A price point or price band | Competitive room | Absent, **and** unenrichable |
| A customer description | Demand reach · Mental advantage | Absent |
| City + category for enrichment | All | Absent |

**The floor refuses; it does not score low.** Below the floor the scorer returns
`REFUSED_INPUT_QUALITY` naming the missing signals (§5.4).

**State the minimum to the user, do not only enforce it silently.** The comparable tools that
handle thin data well render an explicit `No Data` and say why (Google PageSpeed: *"does not have
sufficient real-world speed data"*); the ones that handle it badly show nothing. Guidance emails
should name **the minimum answer threshold** rather than simply reporting that the submission fell
short — it converts a refusal into an instruction, which is what template C is for (D12). Reporting a low score for an
unanswerable submission would attribute the submitter's brevity to their business — the same
defect class as scoring the form instead of the business, which §10.7 records as the single most
repeated error in calibration.

**Scoring is possible when every dimension has *either* a form answer *or* a passing enrichment
source.** It is refused when any dimension has neither. That keeps the cannot-refuse contract
honest: we refuse only when we genuinely have nothing, never merely because a field was skipped.

**Three traps to design against:**

1. **Placeholder text.** `asdf`, `test`, `n/a`, `-`, `.`, and strings of one repeated character must
   fail regardless of length. A cheap deterministic check — this is not a model's job.
2. **Repetition inflation.** The same paragraph pasted into three fields satisfies a word count and
   nothing else. Detect duplicate answers across fields.
3. **The generic positioning sentence.** *"We provide quality service and value to our customers"*
   is long, fluent, and **not a position**. A submission whose differentiator slot holds a generic
   sentence is not merely low-quality — **it is the finding.** The report should say so: *"You
   haven't defined what makes you different — that is the first thing to fix."* That is a real
   report, not a refusal, and it makes the "we don't have one" checkbox load-bearing.

   **⚠ Trap 1 and trap 3 route in OPPOSITE directions, and the distinction is deliberate.** A
   *placeholder* (`asdf`, `test`) is treated as **absent** — there is nothing to analyse, so it
   goes to guidance. A *generic but genuine* sentence is treated as **present** — it is a real
   answer that contains no position, so it is a reportable finding. The test is not fluency or
   length; it is whether a human wrote something they meant. A rule that merged the two would
   either refuse scorable submissions or score empty ones.

**Decision (D12, accepted): an inadequate submission receives a polite guidance email, offered
without limit.**

**The model: two outcomes, and neither is a dead end.**

| Outcome | Trigger | Response |
|---|---|---|
| **Report** | Every dimension has a form answer **or** a passing enrichment source | Scored report (template A) |
| **Guidance** | At least one dimension has neither | Polite email (template C) — what to add, minimum viable input, worked examples |

There is no third outcome. A submission is never silently dropped, and no one is ever left with
nothing.

**Template C is a coaching email, not a refusal notice.** It must carry:

1. **What we could and could not work with** — named per slot, not a generic "your input was
   insufficient."
2. **The minimum viable input per missing slot** — the smallest thing that would make it scorable.
3. **A worked example** — ideally a real one from a published client analysis, showing a
   before/after pair at the required level of specificity.
4. **One click to resubmit**, pre-filled with whatever they already gave.

**Unlimited resubmission (Sean's decision).** No attempt cap, no lockout. The reasoning holds
because of §3.7's ordering:

- Before confirmation, a submission reaches **no model work at all**.
- After confirming their own address, an inadequate submission reaches **one deterministic
  sufficiency check and one email** — no enrichment, no Jev, no report.
- **So the only thing anyone can do unlimited times is mail an address they control.** That is
  self-inflicted inbox noise, not third-party harm. Unlimited is safe *because* confirmation gates
  the queue.

**The one genuine cost, and its control.** Uncapped template C sends are a **send-budget
exhaustion vector** — someone resubmitting hundreds of times consumes the daily ceiling and
`sean.foo@observeco.com`'s reputation. Two rules:

- **All sends count against one ceiling** — report, confirmation and guidance alike. A ceiling that
  only counts successful reports is not a ceiling.
- **At the ceiling, the site stops accepting submissions** rather than silently queueing a backlog.
  An honest "we're at capacity today, try tomorrow" beats a queue that quietly grows and then
  bursts.

**Repeated failure on the same slot is a product signal, not a user problem.** If resubmissions
cluster on one field, the form is asking the question badly. Guidance emails name which slots went
missing on each attempt, so the pattern is measurable (§8.2) and informs the form's copy — which is
the useful answer to "is refusal terminal" now that it is unlimited.

**The mechanism (unchanged): A + B.**

| Layer | What it is | Cost |
|---|---|---|
| **A. Deterministic** | Slot presence, placeholder rejection (`asdf`, `test`, `n/a`, repeated single characters), duplicate-answer detection | free, instant, no model |
| **B. One Jev sufficiency judgment** | One narrow closed question on the residue: *"does this contain enough to assess market position, competitors and customer?"* | ~1 call, negligible |

A+B respects the measured doctrine in `jev-protocol-fit-audit` — *if code resolves the unit, make
zero calls* — because the model only sees what the deterministic layer cannot decide.

**Threshold calibration.** The floor is set so **all six calibration cases pass comfortably**, then
tested against deliberately degraded variants. Refuses a known-good case → too high. Accepts a
degraded one → too low.

**The generic positioning sentence is a report, not a guidance email.** *"We provide quality service
and value to our customers"* is fluent, long, and **not a position** — and that is **the finding**,
not a data-quality failure. The report names it: *"You haven't defined what makes you different.
That is the first thing to fix."* Guidance is reserved for genuine emptiness. The
**"we don't have one" checkbox** makes the honest path easy and cannot be penalised.

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
| ACRA / data.gov.sg (open, SSIC-filterable) | Market headroom · Competitive room |
| Competitor set via search | Relative strength |
| Competitor messaging via fetch | Relative strength · Mental advantage |
| Competitor size/tenure | Relative strength · Defensibility |

### 4.5 Non-load-bearing by construction

Per the cannot-refuse contract: **the form answers alone must carry all six scores.** Enrichment
is best-effort behind a hard timeout. A failed fetch degrades depth, never existence.

---

## 5. L3 — Scoring

### 5.1 The six dimensions

**Calibrated** (§10.7). The previous set described here was **older than 0.9.0** — it named
`Market headroom / Competitive pressure / Position availability / Defensibility / Demand reach`,
whereas the live 0.9.0 file already carried `competitive_room` and `mental_advantage`. The change
is therefore both **two dimensions** and **the weights**.

| # | Dimension | Weight | What it measures |
|---|---|---|---|
| 1 | Relative strength | 25% | For each buying situation it competes in, how firmly does it hold that situation against the named occupants of it? Judged **per situation**, never as one share fight — positioning is about product categories, not industries. |
| 2 | Mental advantage | 20% | How much mind the brand holds in its segment. A **magnitude**, not a competitive claim: a brand can hold a great deal of mind while close rivals hold a similar amount. **Independent of closure** — a closed brand can still be the first name that comes to mind. |
| 3 | Defensibility | 20% | The challenger's cost to displace it: the accumulated barriers the business **holds**, not the differentiator its form claims. |
| 4 | Competitive room | 15% | **Landscape, not business.** Fragmented and uncontested = 5; few giants and a price war = 1. |
| 5 | Market headroom | 10% | Is there unmet demand? Dropped automatically where supply is capacity-elastic (A3). |
| 6 | Demand reach | 10% | Can it find and reach an identifiable paying group? Addressability, not demand size. A business **currently trading** is at least 3. |

**Positioning carries 70%** (relative strength + mental advantage + defensibility), because the
brief is *viability through differentiation*, not industry attractiveness.

**Two reversals to note.** `competitive pressure` treated a crowded market as *bad*;
`competitive_room` scores a **fragmented** market as **favourable** — the earlier polarity was
backwards. And `position availability` — whether a word was unclaimed — is replaced by
`relative_strength`, which measures the position actually **held against the derived competitive
set**, because an unclaimed word nobody buys is not a position. This one is not a renaming: a
business can occupy an unclaimed word and still lose to a rival that owns the buying situation.

**Weights are no longer hypotheses.** D6 said they would be refined by calibration; that
refinement is done (§10.7), against 120 human-graded businesses across 27 categories.

### 5.2 Variable dimension set (required by D7)

A dimension that cannot clear is dropped and stated. **The scorer and the report renderer must
support N dimensions from day one** — weights renormalised at runtime, not hardcoded in the
template. A hardcoded five-bar layout makes a four-dimension ship a rewrite.

**This is now a measured normal case, not an edge case.** `market_headroom` is dropped in **95% of
cases** (114 of 120) because A3 finds the supply capacity-elastic. A five-dimension render is
therefore the exception, and four- and five-dimension paths are what the renderer will run every
day.

### 5.3 One rubric, two implementations

The Python calibration harness and the production scorer must read **the same rubric JSON**.
Otherwise calibration validates a scorer that is not the one shipped. This is the most likely way
to fool ourselves.

### 5.3.1 The rubric promotion step — DONE (`promote_rubric.py`)

**This predicted failure occurred, and closed on 2026-09-27.** `rubric.json` sat at **0.9.0 with
`relative_strength` absent** while §10.7's results described 1.8.0 — so every calibration result
described a rubric nothing served. It was the *silent* failure this section warns about: a
calibrated rubric that nothing loads raises no error and produces no symptom until a client is
shown a score from the retired model.

**Resolution: `rubric.json` is now 1.8.0**, promoted through a gated script.

| Step | Requirement | Status |
|---|---|---|
| 1 | The chosen rubric is promoted to `specs/calibration/rubric.json` — the single path both implementations read | **DONE** — 0.9.0 → 1.8.0 |
| 2 | The promoted file's `_meta.version` **must** equal its top-level `version`; the harness fails loudly on a mismatch | enforced before promotion |
| 3 | Superseded rubrics are retained as `rubric-v<X>.json` for the audit trail, never left as the live file | 1.0.0–1.8.0 retained |
| 4 | No report is served unless the loaded rubric's `_meta.version` is the promoted one | **build — belongs to the scorer** |

**The promotion is a script, not a copy, because a copy cannot refuse.** `promote_rubric.py`
validates six conditions and exits non-zero rather than promoting a bad file:

1. `version` and `_meta.version` agree — the mismatch that once let two different files both claim
   `1.2.0` and defeated the harness's own mixed-version guard;
2. all six calibrated dimensions are present;
3. weights sum to 100;
4. `relative_strength` **has** a weight — its absence is the 0.9.0 defect;
5. the band table is present and starts at Fragile;
6. **no score gates survive** — calibration removed them (§5.4), so a file carrying them is stale.

**Step 4 is still open**, and it is the one that matters in production: the scorer must refuse to
serve a report whose rubric version is not the promoted one. The promotion gate protects the
*rubric*; step 4 protects the *report*. Until the scorer exists, a stale rubric can still be
loaded by anything that reads the path directly.

### 5.4 Two refusals, and no score gates ⚠

**Calibrated (§10.7). This section previously specified six score gates; calibration tested and
removed them. A superseded note at the end of this section records why, because the reasoning
matters more than the deletion.**

**There are no score gates.** A gate turns *"this business has no moat"* into *"we cannot assess
this business"* — different statements, and the second one discards exactly the negative signal
the report exists to deliver. **A low dimension score is a finding** — reported, reasoned about,
and named in the verdict. It is never grounds for refusal.

**Two refusals remain, and both mean "we cannot answer" — never "the answer is bad".**

| Refusal | Trigger | Output |
|---|---|---|
| **Assessability** | The business cannot be analysed from any available input (the classifier's `refuse_when` choice) | `REFUSED_UNASSESSABLE` — no composite |
| **Input quality** | The §3.10 floor is not met | `REFUSED_INPUT_QUALITY`, naming the missing signals — no composite |

Neither is a third gate on low scores. The assessability classifier is asked **first and carries
no weight**: it selects whether the instrument can judge the business at all, and is not a scored
dimension.

**The composite** is computed whenever any dimension is scored, over the scored dimensions only,
with weights renormalised at runtime and the weights actually used recorded (§5.2).

```
composite = round( Σ ( level_i / count_i ) × weight_used_i )
```

**Note the formula: the level is divided by its `count`, not by `count − 1`.** The lowest level
therefore contributes `1/count`, so the composite **floor is ≈20, not 0**. This is stated because
a reported "scale compression" defect turned out to be a replication error using `count − 1`
(§10.7) — it is easy to "fix" a scale that is not broken.

**Bands (calibrated):** Fragile 5–37 · Contested 38–57 · Viable, conditional 58–76 · Strong
77–100. Band edges are derived from level-means, so they do **not** move when weights move.

> **⚠ The band table is INTEGER and does not tile the number line.** There are **gaps at
> 37–38, 57–58 and 76–77**. A composite must be **rounded to an integer before band lookup**.
> This is not cosmetic: a *second implementation* that banded the unrounded float had 11 of 114
> cases fall into a gap, match no band, and hit the fallback — which returned the **extreme**
> band. A case at 37.037 read **"Strong"** instead of Fragile: **a three-band error, from a
> rounding omission.** Three measurement scripts carried exactly this bug.
>
> **The rounding is part of the contract, not an implementation detail** — a production scorer
> that bands a float will disagree with the harness on ~10% of cases, all of them near a
> boundary. Either state rounding as required, or make the table contiguous (e.g. `5–37.99`,
> `38–57.99`, …). **The second option is safer for a second implementation** and is recommended
> as a small follow-up: an implementation cannot forget to round what does not need rounding.
> The harness itself already guards against the general case by *raising* on an unmapped
> composite (`run_jev.py:150`) rather than returning a fallback, which is why the defect
> surfaced only in the re-implementations.

**The compensating-flaw concern is real, and the calibrated weights made it WORSE.**
Measured (F11, verified against the live file's own weights): a submission scoring **0 on Market
headroom** — a textbook category trap — **and maximum on every other dimension** reaches
**85/100, band "Strong"** under the original weights. **Under the calibrated weights it reaches
90/100.** Dropping market headroom's weight to 10% *reduced the penalty for failing it*, exactly
in the dimension a category trap shows up in.

Calibration established that gating is the wrong remedy — refusing the report loses the finding
entirely. **The remedy is disclosure: the report always names the weakest dimension and the
single largest weighted shortfall**, computed as a predicate (§5.5), never written by a model. A
compensating flaw is therefore *stated in the verdict* rather than averaged away or suppressed.

**This is the most important open question in the scoring design.** Disclosure is a weaker
control than a gate, and it is chosen here on the evidence that the gate refused 8 live
businesses out of 10 firings. If disclosure proves insufficient in the canary, the alternative
is **not** to restore the gates but to make the shortfall **structural** — e.g. a category trap
caps the reported band — which is a display decision, not a scoring one.

**Weight concentration is the second control.** Positioning carries 70% across three correlated
dimensions, so a submission cannot reach the top band on market attractiveness alone.

> **Superseded — why the gates were removed.** The gate layer specified here was tested against a
> 75-case blind run. The `defensibility ≥ 2` gate fired on 10 cases, and **8 of those 10 were
> live, large businesses** — KFC, Burger King, Zoff, Harvey Norman, Spectacle Hut, Pure Fitness,
> Virgin Active, R&B Tea. **The model was not wrong about them:** a generic fried-chicken chain
> genuinely has no moat. The gate turned *"this business has no moat"* into *"we cannot assess
> this business"*, and refusing those 8 cases removed exactly the negative signal the report
> exists to deliver. Removing the gates eliminated 8 false refusals out of 10 firings.
>
> This is the same class of bug the floors of 1 produced (a control that cannot fire on the
> condition it exists to catch). **The floors were fixed; the gates themselves were the wrong
> instrument.** A gate failure is not a useless report — it is a *wrong* one, because it answers
> "can this be analysed?" when the finding is "this business is weak".

### 5.5 The verdict and the one gate must be computed, not written

If a language model writes the verdict sentence, two identical submissions can produce different
verdicts — and §10.2's reproducibility claim becomes false. **A report we cannot reproduce is a
report we cannot defend.**

- **The verdict is a predicate** over (band, weakest dimension, any refusal). The sentence is a
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

The six dimensions, their weights, the **level texts** and the band boundaries **are the method**.
A competitor can submit once, receive a report, and reverse-engineer a meaningful part of it.

**The level texts are the most exposed part of the asset.** A single submission returned against a
known input reveals which level each dimension landed on, and the reasoning attached to it — enough
to reconstruct a working approximation of the scale. There are no longer gate thresholds to protect
(§5.4), which removes one exposure and does nothing about this one.

The substance is withheld (§7.2), so the exposure is bounded — but it is real. **The report shows
scores and reasoning without exposing the criteria text, the weights or the band boundaries.** No
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

**The benchmark adds a second metric, and it is the leading indicator for the first.** §7.7.1 makes
the benchmark both the reciprocity engine *and* the dataset's growth mechanism — so the **benchmark
opt-in rate** (§8.2) predicts whether the dataset compounds. **A low opt-in rate is not a
compliance inconvenience; it is the asset failing to accumulate.** Track it as a funnel metric
alongside call bookings, because it moves first and tells you why the dataset is or is not growing.

**What the benchmark changes about the report itself.** The report was to withhold the substance and
withhold the answer. The benchmark changes that: **the comparison is the reason to submit, so a
report that contains no comparison has removed its own incentive.** The report must carry the
**contributor's own position against the pool** — and the *comparison* is what is given away, while
the *analysis of what to do about it* is what the paid engagement sells. That is a cleaner line than
"withhold the substance", and it is the line §7.7.1's thin-cell rule protects.

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
A backup that lives in the same provider as the data is not a durability story.

### 7.7 The data is research, and that needs its own consent purpose

Sean's point, and it is the more valuable half of the exchange: **a quality submission is not only
a report request — it is primary research.** Self-reported price points, competitor counts and
positioning sentences from SG SMEs are exactly the raw material behind the industry-dataset claim
your consulting offer already makes as its moat. Most consultancies buy that data or synthesise it.
This collects it as a byproduct of a free service.

**It is a third purpose, and it cannot ride on the other two. DECIDED (D19): a separate, unticked
consent box, and the dataset claim stays conditional on it.**

| # | Purpose | Basis |
|---|---|---|
| 1 | Deliver the requested report | Required to perform what was asked |
| 2 | Follow-up / nurture about ObserveCo's services | Optional, separate |
| 3 | **Aggregate market research and industry datasets** | Optional, separate — **new** |

Purpose 3 must be its own line and its own row. Absorbing research use into "we'll send you a
report" is the same bundling failure §3.2 already forbids — and it is worse here, because the
contributor receives nothing extra for it.

**This is a TRADE, not a request.** *(Revised — the first pass asked a favour, which is why its
opt-in rate would have been poor. The benchmark model treats it as an exchange, and the exchange is
what makes the rate real.)*

| | They give | They get |
|---|---|---|
| **Purpose 1** — always | ~15 form answers | Their scored report. **Never conditional on anything** |
| **Purpose 3** — opt-in | Consent to aggregate use | **The benchmark** — how they compare to the pool |

**The checkbox is not "may we use your data for research". It is the unlock for the comparison
itself.** Same consent, same unticked default, same own row — but a reason to tick that a favour
does not supply. This is the model salary surveys and benchmarking consortia run, and it works
because the thing withheld is *collective*, not *personal*.

**⚠ The tension this creates, stated plainly, because it could make the design unlawful if blurred.**
The earlier draft said *"refusal costs nothing."* Under reciprocity that is **no longer literally
true** — declining loses the benchmark. Three rules reconcile it, and the third is the load-bearing
one:

| Rule | Why |
|---|---|
| **Unticked by default** | A pre-ticked box is not consent under the PDPA. Ticking must be an act |
| **Own row, own timestamp** | Consent must be evidenced per purpose. One "agreed to terms" row cannot prove *which* purposes were agreed |
| **The withheld benefit must be the COLLECTIVE GOOD, never the SERVICE** | The report is what they asked for and is never gated. The benchmark cannot exist without contributions, so giving it only to contributors is an honest exchange, not coercion. **If declining ever degrades the scored report, the consent is coerced and the purpose is void** |

**A fourth source, with its own basis — do not fold it into purpose 3.** Purpose 3 covers what the
submitter *tells us*. The report also enriches submissions from public sources (§4) — Places data,
review text, registries. That material has **different provenance and different rules**, and §7.3's
claimed/observed/not-checked split exists precisely to keep them apart.

The commercial consequence is uncomfortable and worth stating: **a dataset built only from consented
form answers is thin; the enriched material is the valuable part.** If enrichment cannot be used in
the dataset, the "SG industry datasets" claim rests on self-reported text alone — which is a
materially weaker asset than §7.7's premise assumes. **This needs its own determination** (is
aggregated public-source business data personal data at all?) before the claim can lean on it.

**A withheld consent is a data-loss decision, not just a compliance one.** Every submission whose
box is unticked is permanently unavailable to the dataset — it can still be scored, but never
aggregated. The dataset's coverage is therefore a direct function of how the checkbox is worded and
placed, and the opt-in rate should be **tracked from day one**, because a rate of, say, 30% is a
materially weaker asset than the design assumes — and a rate near 0% means the dataset claim must
come down.

**The claim stays conditional (this is the part that is easy to get wrong).** §7.7's commercial
premise — that each submission compounds the "we maintain SG industry datasets" claim — holds
**only while enough contributors consent.** So the claim is not licensed by shipping the checkbox;
it is licensed by the measured opt-in rate combined with the k-anonymity floor below. Until both
hold, the positioning line is aspirational and must not be presented as established. **Two
independent gates, and neither one alone is sufficient.**

**Withdrawal is not the same as non-consent.** A contributor who consented and later withdraws
falls under §7.5 deletion plus the "strip and aggregate" rule below — but anything already
**truly anonymised** cannot be un-mixed, and that must be disclosed in the consent wording before
the box is ticked, not discovered afterwards.

**The retention interplay is the interesting part.** §7.5 says contacts who never convert are
deleted soonest. That is compatible with keeping the *research* — **if** the contribution is
genuinely anonymised rather than merely pseudonymised. That distinction is the whole design:

| Form | PDPA status | May it survive deletion? |
|---|---|---|
| Identifiable (name/email/company attached) | Personal data | **No** |
| Pseudonymised (keyed back via an ID we hold) | **Still personal data** — re-identifiable | **No** |
| Pseudonymous, licensed, quasi-identifiers disclosed | Still personal data — **but the working commercial case** | **Contract-bound, not anonymised** |
| Truly anonymised (no key exists, no re-identification path) | Not personal data | **Yes** |

**⚠ A third path exists and it is what actually works at scale — read it before assuming the binary.**
Levels.fyi publishes records carrying **employer, title, level and location**, stripped only of name,
email and contact details, and warns contributors plainly to *"read what we can and cannot promise
about anonymity."* It then **licenses that data for a fee**, which is what funds the free service
(verified, `RESEARCH-benchmark-model.md` §1). **That is not anonymisation** — it is pseudonymous data
with disclosed quasi-identifiers, held together by **contractual anti-re-identification terms** on
the recipient rather than by a technical guarantee.

**Why this matters here:** §7.7's binary (identifiable → delete; anonymised → keep) implied the only
compliant dataset is a fully anonymised one. The market suggests otherwise — the commercially viable
asset is **contract-bound pseudonymous data**, which stays personal data and therefore stays subject
to deletion and withdrawal. **Choosing this path is a decision, not a default**, and it trades
stronger utility for weaker privacy claims. **It also means k-anonymity is not the only control
available** — contract is the second.

**D25's floor is affected either way:** a floor of 5 protects *employees*, who are not each other's
competitors. Ours are. **Payscale's published floor of five — verified — is the right shape and the
wrong number for a small, concentrated market.**

So the deletion job must **strip and aggregate before it deletes**, and the aggregate must be built
so it cannot be re-associated. "We deleted the contact but kept the row" is not anonymisation.

### 7.7.1 The cold start is not a cold start — the calibration corpus is the seed ⚠

**This is the finding that de-risks the whole dataset premise, and it was sitting in the repository.**
The benchmark model's hardest problem is the first contributor: *why submit to a pool with nothing
in it?* **The pool already exists** — §10.7's 120 businesses across 27 categories **are** the
research, collected as part of calibration.

| | Calibration corpus (§10.7) | Measured |
|---|---|---|
| Businesses | 120 across 27 categories | — |
| Categories clearing a **minimum cell of 5** | **11 of 27** | **88 of 120 businesses inside them** |
| Categories clearing 8 | 4 | bubble-tea, home-baking, home-nails, home-facial |
| Categories below 5 | 16 | 32 businesses — mostly n=1 |

**Two consequences, and they point the same way:**

1. **The reciprocity engine can be shown working on day one, honestly** — the first contributors get
   a real comparison, not a placeholder, in the 11 thick categories.
2. **The minimum cell is not a hypothetical threshold, it is a measured constraint.** With 16 of 27
   categories below 5, most *first* submissions land in a cell too thin to compare. **So the design
   must answer honestly at thin cells** — and the rule below applies from the first submission.
   **The two-tier disclosure is the resolution (D25):** the 11 categories clearing 5 publish an
   **emerging** comparison immediately and honestly, while the 4 clearing 8 carry the full standard
   detail. A flat raised floor would have suppressed 19 categories and left the engine with nothing
   to trade.

**⚠ The Singapore-specific re-identification risk, which no generic k-anonymity floor addresses.**
A salary survey's contributors are mostly not each other's direct competitors. **Ours are.** In a
category with exactly 5 businesses in Singapore, a "5-business median price" may be identifiable by
the five themselves — each knows four of the numbers. **A cell of 5 is defensible for a national
salary curve and may not be defensible for a 5-outlier SG category.** Two mitigations, and both are
needed:

- **The floor does not apply to *their own* comparison at a thin cell** — a contributor may see how
  they sit against the pool. What they may **not** see is the pool decomposed, because the
  decomposition is the re-identification path.
- **⚠ CORRECTED (stream 5): the norm is SUPPRESSION, not widening.** An earlier version of this
  section said "widen rather than suppress", reasoning that suppression leaves a thin-cell
  contributor with nothing. **Practitioner rule sets do the opposite** — Mercer *"the data is
  suppressed"*, Empsight *"suppressed and are not recorded in the report"*, WorldatWork *"does not
  publish or otherwise make available"*, Effectory aggregates upward. **Widening survives as a
  secondary technique** (Payscale *"pulling back from a local search to a broader geographic area"*;
  Effectory aggregating to a parent level), not as the primary answer. See
  `RESEARCH-benchmark-model.md` Appendix §2.
- **Secondary suppression is mandatory if any total is ever shown.** The formal discipline is
  statistical disclosure control: hide the unsafe cell, **and** hide others so the first cannot be
  recovered by subtraction from published totals (Effectory states it: *"The sum of all non-reported
  respondents within a level must be at least five"*). Reporting *"40 businesses, 6 sub-segments,
  one withheld"* tells the reader the withheld cell is the remainder.
- **A report emailed to ONE contributor is a one-to-one output**, and carries the same disclosure
  checks as a published one. That is the cleaner statement of what the floor protects, and it
  extends the discipline to every personalised output.
- **A concentration cap is required IN ADDITION to the floor**, and this was missing. A count floor
  does not stop a single contributor being recoverable: in an SG category of 5 where one business is
  dominant, a "5-business median price" is approximately that business's price. The industry pairs
  the two — **25%** (Milliman, Empsight), **50%** (Payscale Peer), **70%** (Agri Stats 2026). For a
  concentrated SG category, **25% is the defensible end.**
- **⚠ The refusal message must NOT state the cell size.** *"We cannot compare you because only 3
  businesses like yours are in our data"* has disclosed the contributor count — and in a small
  market, possibly the category's size. Agri Stats' 2026 judgment expressly targets *"Flags"* that
  reveal contributor counts. **The same discipline applies to who took part: do not publish a
  participant list.** APQC and Mercer do publish them (trading confidentiality for credibility);
  we should not.

**Two operational rules on the dataset:**

- **A k-anonymity floor on anything surfaced.** No published or client-facing figure may be derived
  from a segment with fewer than a minimum number of contributors — otherwise the "aggregate" names
  one business. The floor is a threshold to set, but a floor is required.
- **A boundary on reuse.** Numbers a client disclosed to us must not be presented back as
  competitor intelligence in *another* client's paid analysis. That is a conflict of interest and a
  trust failure, and it is worth stating because the commercial temptation to blend sources is real.
  Aggregate, anonymised market shape is defensible; "one of our clients told us Competitor X charges
  S$12" is not.

**Why this matters commercially:** the dataset claim in your positioning
(`observeco-consulting-pivot-positioning.md`) is *"we maintain SG industry datasets"* — currently
maintained by hand. Purpose 3 turns each consenting free submission into a contribution to that
asset. It is the compounding reason to run the free report at all, beyond lead capture.

**But the claim is now CONDITIONAL, and this is a deliberate downgrade from how it read before.**
It holds only while (a) the measured opt-in rate supports it and (b) every surfaced figure clears
the k-anonymity floor. **D19 authorised the mechanism; it did not license the claim.** An untracked
opt-in rate cannot support a public positioning line, so the rate is a **launch-tracked metric**,
not an afterthought.

### 7.8 Where the form data may and may not be used

A boundary that keeps §7.7 lawful and the offer credible:

- **May** be used: to produce that submitter's report; in aggregate, anonymised form, in datasets,
  whitepapers and analysis — subject to the k-anonymity floor.
- **May not** be used: as competitor intelligence in another client's paid engagement;
  in marketing copy in a way that identifies the submitter or their business; or to train a model
  without purpose 3 disclosed as including that.

### 7.9 The competitive fact this design has to answer for ⚠

**Singapore already provides the free thing, at state scale** (`RESEARCH-benchmark-model.md` §7):

- **10 SME Centres give free business advisory to ~25,000 SMEs a year.**
- **From 2027 they add "diagnostic toolkits" for capability gaps** — i.e. the state is moving into
  free business diagnostics.
- **EDG subsidises up to 50% of eligible costs, including third-party consultancy fees — but
  management-consultancy costs require a TR 43 / SS 680 certified consultant.**

**This is the sharpest strategic constraint on the free report, and it was absent from every prior
version of this spec.** A free positioning report competes, in the target SME segment, with a free
government advisory service that already reaches 25,000 SMEs a year.

**Three consequences, and the third is the most actionable:**

1. **"Free" is not the differentiator.** The alternative is free *and* state-backed. The free report
   must be differentiated on what a SME Centre cannot do — **a specific, evidence-based, comparative
   positioning judgment on their business**, not general advisory.
2. **The 2027 diagnostic toolkits are a deadline, not a footnote.** If the state ships capability-gap
   diagnostics in 2027, the window for this asset as a novelty closes.
3. **EDG's certification requirement is simultaneously a barrier and an unlock.** Management-
   consultancy fees are only subsidisable through a **TR 43 / SS 680 certified** consultant. That is
   a checkable gate — and it converts a S$500 price objection into an eligible, part-funded one. **If
   the paid tier is aimed at SMEs, certification is a commercial lever, not a compliance detail.**

**A second structural finding, on channel.** Referral dominates professional-services buying —
**71%** of buyers find a firm by asking someone against **11%** via online search, and **41%** of new
clients at benchmarked consultancies come from referrals while only **12%** of firms have a referral
strategy. **The free report is therefore not the primary acquisition channel. It is a credibility
artefact that a referral-led sale converts on** — which is consistent with its stated job
("qualification, not volume", §1) and is a reason not to over-invest in driving traffic to it.

**And the benchmark gap is now measurable:** Bain's free diagnostic is benchmarked on **250+
companies** and its paid assessment on **~1,200**; BCG claims **10,000+**. **Ours is 120.** That is
not a reason not to ship — §7.7.1's 11 categories can carry a real comparison today, under the
**emerging** tier — but it is the number that decides when the *positioning* claim "we maintain SG
industry datasets" starts to be true rather than aspirational.

**The gap is a credibility problem, not a coverage problem.** The majors' free diagnostics are
credible *because* the pool behind them is large; ours will be read as thin until it is not. That
argues for **labelling coverage honestly from the start** (the emerging/standard split) rather than
presenting a 5-business comparison and a 1,200-business comparison in the same voice.

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
| **Benchmark opt-in rate** | **The dataset's growth rate (§7.7.1). Moves before call bookings, and a low rate means the asset is not accumulating** |
| **Benchmark shown vs withheld, by category** | Whether the thin-cell rule is suppressing most comparisons — if nearly everything is withheld, the reciprocity engine is not working and the opt-in rate will follow |
| Contributors per category | Drives when a category clears the minimum cell (§7.7.1); the coverage map of the dataset |
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
it never shows the criteria text, the weights or raw model payloads. Nor does it expose
`rubric_version` in a body a competitor can read.

**The model pin is not currently enforced by the rubric.** §5.9 cites `jev-1.13.0` as the pinned
dependency, but the rubric records its model as **`jev-latest`** — so the pin lives in this
document, not in the artifact that determines behaviour. Either pin the version in the rubric or
record that enforcement is external; leaving the two disagreeing means §5.9's mitigation reads as
stronger than it is.

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

### 10.1.1 Two corpora, two jobs — do not conflate them

The six cases above are a **canary**, not the calibration corpus. They answer different questions
and must not be merged.

| | Canary corpus (§10.1) | Calibration corpus (§10.7) |
|---|---|---|
| Size | 6 fixed cases | 120 businesses, 27 categories |
| Input | form-shaped, from real engagements | form-shaped, mixed real and authored |
| Purpose | **detect drift** — same input, fixed expected output, run on a schedule | **measure agreement** — how closely the instrument tracks a human grader |
| Changes over time? | **Never.** A canary whose fixture moves detects nothing | Grows as coverage gaps close |
| What a failure means | The model or the rubric moved | The instrument is not yet calibrated |

**The corpus is complete and baselined (was: 1 of 6).** All six cases now exist as form-shaped
fixtures in `specs/calibration/canary/`, and the launch gate can run. See §10.8 for the build, the
result, and the caveat that governs how the fixtures may be interpreted.

**They are AUTHORED from the engagement analyses, not captured from client intake forms.** No raw
intake form exists for any of the six engagements, so the form fields were reconstructed from the
analysis documents and the per-dimension expected vectors are an **assistant mapping** of each
engagement's conclusion onto the six calibrated dimensions — not a recorded client label. **The
band is the bar; the dimension vector is not** (§10.6). §10.8 states the consequence.

**A caveat that survives from §10.5:** all six were authored by the same person, so they are not
drawn from the population the free form actually sees. The 120-case corpus addresses that
distribution gap — which is precisely why both are needed, and why neither replaces the other.

### 10.2 Provenance — every report carries

`rubric_version` · `rubric_meta_version` · `model_id` (as returned by the API) · `prompt_hash` ·
`input_hash` · `enrichment_sources[]` · `dimensions_used[]` · **`weights_used`** · `refusals[]` ·
`generated_at`

**`weights_used` is required, not optional:** weights are renormalised at runtime whenever a
dimension is dropped (§5.2), so the effective weighting of a report cannot be reconstructed from
the rubric alone. **`rubric_meta_version` is recorded separately** because the retracted bug in
§10.7 arose from two version fields disagreeing — if they can differ, both must be captured.
`refusals[]` replaces `gates_evaluated`; refusals are the only gate-like outcomes remaining (§5.4).

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
5. **The human baseline now exists, and it changed the design.** This item previously read that
   no baseline had ever been measured. It has: Sean graded **120 businesses across 27 categories**
   at dimension level, blind to the instrument's scores, plus a separate composite regrade. That
   is the reference set for §10.7 — twenty times the scale this item originally asked for.

   Its findings were not merely reassuring. **Each one moved the method:**
   - His grades **redefined `mental_advantage`** — how much mind the brand holds, and
     **independent of closure**. The instrument had been suppressing a closed brand to 1 when the
     brand was still the first name Singaporeans think of for bubble tea.
   - He **confirmed `competitive_room`'s polarity the reverse of 0.9.0** and closed it out.
   - He **halved the disputes on `defensibility`** by naming what it should measure — *"took
     decades and huge capital"*. The instrument had been scoring the differentiator a form
     **claims** rather than the barrier a business **holds**.
   - **59 of 61 of his composite entries copied the instrument's own score** into the adjacent
     column. Dimension scores had their own distributions, so they were not copied — but this is
     why **composites in §10.7 are recomputed from his dimension scores**, never taken from his
     composite column. Any agreement figure that used his composite would have been an artefact.

   **One caveat survives and must be stated:** a single grader's labels can be calibrated *to*
   rather than calibrated *against*. A second independent grader would separate the two, and is
   not available. This is the honest boundary of what §10.7 proves.

### 10.6 Launch gate

**Ship the scored report when the instrument clears the following, on the corpora in §10.1 and
§10.7.**

| Criterion | Bar | Measured |
|---|---|---|
| Band agreement | ≥90% of cases within **one band** of the reference label | **100%** (n=114) |
| Gross band error | ≤5% of cases **two or more bands** off | **0%** |
| Dimension disputes | ≤5% of dimension scores **≥2 levels** apart | **2.8%** |
| Canary cases present | All six (§10.1), running and baselined | **6 of 6 — gate RUNS** (§10.8) |
| Canary agreement | Every canary within **one band** of its engagement conclusion | **6 of 6**; 4 of 6 exact (§10.8) |
| Negative controls | Every control **fails**, each with its own predicted failure reason | **not built** — the one open row |

**Dimension-exact agreement is explicitly NOT the bar.** It sits at 56.5%, and requiring it would
hold the product to a granularity a five-point human-judged scale does not support. **The client
sees a band and a narrative, never a number (§5.8)** — so band agreement is the measure that
matches what can actually be wrong from the client's side. This supersedes the earlier "every
dimension within ±1 level", which was never met and was replaced by decision D20.

**Disagreement triage — judge-vs-corpus disagreement is UNRESOLVED until hand-read.** Do not
default to "Jev is wrong"; that has been the wrong call before.

| Branch | Condition | Action |
|---|---|---|
| J1 | Hand-read confirms Jev missed | Fix criterion/unit/gate. Jev was wrong. |
| J2 | Hand-read confirms the analysis missed it | Correct the label — **a finding about our own method** |
| J3 | Both defensible | Dimension genuinely ambiguous → **drop it and state it** (D7) |

---

### 10.7 What calibration established (v1.2.0 → v1.8.0)

**Method.** 120 businesses across 27 categories, form-shaped inputs, scored under a rubric whose
every change was isolated to **one dimension** with the other five asserted byte-identical as a
control. Reference labels: Sean's blind dimension grades (§10.5 item 5). The canary corpus of
§10.1 is built and baselined separately (§10.8) and is **not** part of this measurement.

**One defect class accounted for every improvement: the instrument was reading the SUBMISSION
instead of the BUSINESS.**

| Dimension | What it read | What it must read |
|---|---|---|
| `demand_reach` | whether the form *named* a channel | whether the business demonstrably reaches buyers — currently trading sets a floor of 3 |
| `relative_strength` | one share fight against every named competitor | the position held **per situation**, corroborated |
| `mental_advantage` | whether the *model* could articulate a retrieval occasion | whether the *segment* holds the brand in mind |
| `defensibility` | the differentiator the form **claims** | the accumulated barriers the business **holds** |

**Two recurring mechanical causes.** (1) The form's `undercut_on` field is the business
**self-reporting its weakness**, and it was being scored as the verdict — **candour was punished**.
(2) **Absence of detail in a form was read as absence in the world.** A business with seven outlets
was scored as having no route to buyers because its form was terse.

**Corroboration is dimension-specific.** The same physical fact has *opposite* implications in
different dimensions: closure destroys **reach** (`demand_reach`) but not **memory**
(`mental_advantage`). A single shared "physical evidence" rule was tested and is too blunt.

**Measured trajectory.** Noise floor ±0.4 pts / ±2 cases, established by re-running one rubric
twice — 19 of 720 cells moved, symmetrically (9 down, 10 up), so the movement below is real:

| | exact | disputes ≥2 | offset |
|---|---|---|---|
| v1.2.0 baseline | 66.7% | 8.6% | +0.23 |
| v1.6.0 | 55.9% | 4.7% | +0.09 |
| **v1.8.0** | 56.5% | **2.8%** | +0.09 |

**Exact agreement fell while disputes halved, and that is the intended trade.** Exact
disagreement was converted into *adjacent* disagreement: cells at gap 0 fell 319 → 271 while
gap ≥2 fell **41 → 23**. **A wrong band misleads a client; an adjacent one does not.** Since the
client sees a band, disputes are the measure matching the product.

**Product-level result.** Both composites computed on the harness formula (§5.4):

| | n | same band | within one band | two or more off |
|---|---|---|---|---|
| all cases | 114 | **69.3%** | **100.0%** | **0.0%** |
| target segment (grader's band = Fragile or Contested) | 60 | **85.0%** | **100.0%** | **0.0%** |

**"Exact" here means an exact BAND match, not an exact dimension score** — the bar D1 set is band
agreement, and dimension-exactness is explicitly not the bar (R5, §10.6). Dimension-cell
exactness on the target segment is 68.3% (205/300 cells) and is reported for completeness only.

**The target segment is where the instrument is strongest** (85.0% same-band versus 69.3% overall),
which is the right way round: that is the segment D3 names as the lead magnet's audience.

**No case is two or more bands out, on either the full set or the target segment.** If the
instrument errs, it errs by one band — which is the failure mode a band-first design tolerates.

**What calibration did NOT establish.**
- **Agreement, not accuracy.** The reference labels are one human's; correlated error between the
  instrument and that human would agree and still both be wrong (§10.5 item 1).
- **A second grader is absent**, so calibrated-*to* versus calibrated-*against* is unresolved.
- **The weakest region is the top end** — a −7.7 mean composite offset for businesses the grader
  rated 80+, which is off-target but real.
- **The lowest band is a thin cell.** The grader placed only **7** of 114 cases in Fragile (the
  instrument placed 8), so any figure quoted for that band rests on seven cases, not thirty.
- **One defect I reported and then retracted — and it propagated.** I reported the composite as
  "compressed" (+13 at the low end, −4.5 at the high end). It was **my own replication bug**: I
  used `(level−1)/(count−1)` where the harness uses `level/count`, so I was comparing a floor-0
  scale against a floor-20 one. Verified against the harness's stored output and retracted.

  **The same bug had already spread into the band measurement.** Six analysis scripts carried it,
  so they compared *my* harness composite against *the grader's* min-max composite — two different
  scales. That is where the claim "26 of the 34 Fragile businesses are promoted to Contested"
  came from, and it was **false**: on one consistent formula it is **1 of 7**, and the direction of
  error reverses — the instrument is **harsher** than the grader on 23 cases and more generous on
  12. The promotion problem does not exist.

  **This is recorded because it reached a decision.** The false promotion finding was one of the
  facts used to argue that the weak end needed re-targeting, and D3 was answered partly on that
  basis. The conclusion (target weak-positioning SMEs) still stands on the band table above — the
  target segment is 100% within one band — but it stands on **corrected** numbers, not on the
  retracted one.

> **The single lesson worth carrying, now twice-earned:** any re-implementation of a harness
> calculation must be verified against the harness's own stored output **before** any finding is
> built on it — and when the bug is found, **every script that shared the formula is a suspect
> finding, not just the one that found it.** The first retraction covered the composite; the
> second, six scripts and a claim that had already reached a decision. One
> cheap call would have caught the retracted finding above.

---

### 10.8 The canary — built, baselined, running

**This section exists because the corpus did not.** §10.1.1 recorded that five of the six canary
cases did not exist, which made §10.6's launch gate unrunnable. It now runs.

**Where the fixtures came from.** The six source engagements still exist on disk as full
competitive analyses, so the fixtures were **authored from them** rather than invented:

| Case | Source analysis | Engagement conclusion | Fixture band |
|---|---|---|---|
| C1 GreenPackers | `~/projects/Greenpackers/…/GreenPackers_Competitive_Analysis.md` | Fringe, <1%; guerrilla warfare the only play | Fragile |
| C2 CaiCa | `~/projects/CaiCa/…/CaiCa_Competitive_Analysis.md` | Reason-to-purchase not strong | Contested |
| C3 PetDirectory | `~/projects/PetDirectory/…/PetDirectory_Competitive_Analysis.md` | Market real, position open, demand side unbuilt | Contested |
| C4 SGFitness | `~/SGFitness/…/SGFitness_Competitive_Analysis_Summary.md` | White space in a specific demographic | Fragile |
| C5 SaladShop | `~/SaladShop/…/SaladShop_Competitive_Analysis_Summary.md` | CBD saturated; white space outside it | Fragile |
| C6 Bonefirm | `~/projects/Bonefirm/…/Bonefirm_Competitive_Analysis.md` | Feasible, with one condition (B1) | Viable, conditional |

**⚠ They are AUTHORED, not captured.** No raw intake form exists for any of the six engagements, so
the form fields are **reconstructed from the analyses**, and the per-dimension expected vectors are
an **assistant mapping** of each conclusion onto the six dimensions — **not a recorded client
label.** This is the corpus's principal weakness and it is stated rather than hidden. It does not
stop the canary doing its job (the question it answers is *"has behaviour moved?"*, which needs no
human label — see the two-rung design below), but it does mean the *expected* values are not
independent evidence of correctness. **To make this a real gold set, the same move that produced
§10.7 is needed: Sean grades the six cases blind.**

**The runner: two rungs, and why.** `specs/calibration/run_canary.py`

| Rung | Does | When |
|---|---|---|
| `--rung record` | Runs the corpus and writes `canary/_reference.json` | **Once.** Refuses to overwrite without `--force` |
| `--rung check` | Runs and compares against the stored reference | The scheduled job |

A canary cannot compare against itself. The first run has no reference, so it records one; every
later run compares. **A `check` run with no reference exits 2 and fails loudly** — a canary that
reports green because it has nothing to compare against is worse than no canary at all.

**Drift is band-only.** Per D1 and §10.6, the comparison is the **band**. A dimension that moves
without moving the band is **advisory** and printed as such, not a failure — dimension-exactness is
explicitly not the bar. The report separates the **drift verdict** (against the frozen reference)
from an **informational** comparison against the engagement conclusions, because conflating the two
is how a canary gets tuned into a calibration set and stops detecting anything.

**The result. The gate now passes:**

| | Result |
|---|---|
| Canary cases present | **6 of 6** |
| Within one band of the engagement conclusion | **6 of 6** |
| Exact band | **4 of 6** |
| Gross band error (two or more) | **0** |
| Drift check against the reference | **PASS — no band moved** |

**Two disagreements, both informative, and deliberately NOT tuned away:**

- **C6 Bonefirm — instrument scored `defensibility` 2 where Sean's own blind grade was 4.** A
  **second, independent corpus flagging the same dimension** §10.7 already identifies as the
  largest remaining dispute source (7.0%). Convergence from an unrelated direction is the more
  credible kind of evidence, and this is why the fixture was left alone.
- **C1 GreenPackers — instrument read Contested where the engagement concluded Fragile** (it
  scored `relative_strength` 3 against a sub-1% fringe business facing BioPak's verified moat).

**Fixtures are frozen by design.** §10.1.1: *"a canary whose fixture moves detects nothing."*
Adjusting an expected value so the instrument agrees would convert the canary into a
self-fulfilling test that passes forever and detects nothing. **The disagreements are recorded as
findings, not reconciled in the fixture.**

**A pre-launch caveat that applies to C4 and C5.** Both are venture *concepts* rather than trading
businesses, so their conclusions ("white space identified") are statements about the **market**, not
about a position held. The instrument reads an unlaunched venture as **Fragile** — it holds nothing
— while the finding the engagement actually reached lives in `competitive_room`. **For these two
cases the band under-expresses the conclusion, and a failure there would not mean Jev missed the
white space.** Recorded in each fixture's `_meta` so no future reader over-reads it.

**A known sensitivity, recorded because it sits on a cliff.** C6's `defensibility` 3-vs-4 is the
documented uncertainty (Sean's own 3.5–4 hedge). At 4 the case lands at composite 61 with margin; at
3 it lands at **58 — exactly the Viable boundary.** The fixture uses the human label (4); the
sensitivity is stated because a 1-point move flipping the band is a fact worth knowing before it
happens in production.

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
| F10 | `content-spec-v1.md` promised *"Get your free positioning snapshot"* — caption *"5 slides. Your market, mini competitive scan. No obligation."* — and it appears on **no live page** (verified: no `.html` in `website/` contains it) | This feature is that promise, re-scoped. **⚠ The promised artifact is 5 SLIDES; 095 builds a web report.** The hero and pricing page of `content-spec-v1.md` have never been published, so no promise is currently broken — but either 095 must emit a slide-shaped artifact or the promise must be reworded before those sections go live |
| F11 | A category trap (0 on Market headroom) reaches **85/100 — "Strong"** under the original weights — **re-verified, and 90/100 under the calibrated weights** | ~~The composite must be gated~~ **Gates removed; the concern is now handled by disclosure and is the open question in §5.4** |

**Backend note:** the pricing research in §6.1 ran on the keyless fallback because the configured
ddgs backend failed that call. Re-verify figures against the providers' own pages before a
purchasing decision.

---

## 13. Decisions required

| # | Decision | My recommendation |
|---|---|---|
| **D11** | **Email confirmation before send** (§3.7) | **ACCEPTED** — with Turnstile at submission |
| **D12** | **Input-quality floor** (§3.10) — where the guidance path fires | **ACCEPTED** — guidance email, unlimited attempts |
| **D13** | **Gate thresholds** for G1–G5 (§5.4) | ~~Start at the stated values, calibrate~~ **SUPERSEDED** — the gates were removed by calibration (§5.4, §10.7). No thresholds remain to set |
| **D14** | **Jurisdiction** (§9) — scope the offer to SG, or build a GDPR path | Scope to SG explicitly |
| **D15** | **Retention periods** (§7.5) | Provisional table stands as the starting point |
| **D16** | **Human baseline** (§10.5) | **FULFILLED — and exceeded.** Sean graded **120 businesses across 27 categories** blind, plus a composite regrade, not the six cases proposed here. Results in §10.7. Caveat carried: a second grader is absent |
| **D17** | **Nurture cadence and exit rules** (D3) | Defer — low priority, architecture supports it |
| **D18** | **The name** (D1) | KIV |
| **D19** | **Research purpose** (§7.7) — consent to use submissions in aggregate research | **ACCEPTED and REVISED — a TRADE, not a favour.** The consent unlocks the **benchmark** (their position vs the pool); the scored report is never gated. Unticked default, own consent row. The withheld benefit must be the **collective good**, never the service — if declining degrades the report the consent is coerced and void. Claim stays CONDITIONAL on the measured opt-in rate *and* the k-anonymity floor |
| **D24** | **Enrichment provenance** (§7.7) — may enriched *public-source* material enter the dataset? | **OPEN — Sean to decide.** A dataset built only from consented form answers is thin; the enriched material is the valuable part. If enrichment cannot be used, the "SG industry datasets" claim rests on self-reported text alone. Needs a determination on whether aggregated public-source business data is personal data at all |
| **D25** | **Minimum cell size, SG-adjusted** (§7.7.1) | **OPEN — recommendation REVISED.** A flat raised floor of 8 suppresses 19 of 27 categories and kills the reciprocity engine. **Recommended instead: a TWO-TIER disclosure, modelled on Culture Amp** — an **emerging** tier (floor 5, comparison shown and labelled as thin coverage) and a **standard** tier (floor 8+, full cut detail). This keeps the engine alive in the 11 categories that clear 5 while keeping the stricter guarantee where the data supports it (4 categories). **Both controls are needed in any case: a concentration cap (25% for a concentrated SG category) and secondary suppression if any total is shown.** Industry floor is 5 (Mercer, Milliman, Empsight, Payscale, Pave, WorldatWork); the two-tier structure is verified to exist at Culture Amp, its thresholds are not |
| **D28** | **Submission identity/validation gate** (§7.7.1) | **OPEN — Sean to decide.** Fabrication is not detectable statistically — ISO 26362 catches it with an identity gate (*"validate the claimed identity of new panel members"*). Our form is anonymous and a self-report costs nothing to fake. **APQC's 80% completion minimum before any report issues is a cheap structural control** that pairs with the §3.10 input-quality floor. Does the free report require a verified business identity, or stay anonymous? |
| **D26** | **The third path — contract-bound pseudonymous licensing** (§7.7) | **OPEN — Sean to decide.** Levels.fyi licenses records carrying employer/title/level/location, stripped of contact details, under contractual anti-re-identification terms — **not anonymisation, and it works at scale.** Adopting it yields a far stronger dataset than anonymisation-only, at the cost of a weaker privacy claim and continued PDPA deletion/withdrawal exposure. **This is the single decision that most determines whether the dataset is an asset or a curiosity** |
| **D27** | **EDG certification (TR 43 / SS 680)** (§7.9) | **OPEN — Sean to decide.** Management-consultancy fees are EDG-subsidisable **only** through a certified consultant. Certification converts the S$500 price objection into a part-funded eligible cost, and is a checkable gate. Worth a cost/benefit look if the paid tier targets SMEs |
| **D20** | **Launch criterion** (§10.6) — dimension exactness vs band agreement | **ACCEPTED — band agreement.** ≥90% within one band, ≤5% two-or-more off. Dimension-exact is explicitly not the bar (it sits at 56.5% and is not achievable on a 5-point human-judged scale) |
| **D21** | **No score gates** (§5.4) — keep, or remove as calibration measured | **ACCEPTED — removed.** The `defensibility ≥ 2` gate produced 8 false refusals out of 10 firings on live, large businesses. Low scores are findings, not refusals. Only assessability and input-quality refusals remain |
| **D22** | **Rubric promotion** (§5.3.1) — which file is live | **DONE — `rubric.json` promoted 0.9.0 → 1.8.0 via `promote_rubric.py`**, which validates six conditions and refuses on any failure. Step 4 (the scorer must refuse a non-promoted rubric) remains a build item |
| **D23** | **Canary restoration** (§10.8) | **DONE — 6 of 6 present and baselined.** Fixtures authored from the six source engagement analyses; `run_canary.py` runs them. Result: 6 of 6 within one band, 4 of 6 exact, 0 gross errors. **Caveat: AUTHORED, not client-captured — the expected vectors are an assistant mapping, not a recorded client label. A blind regrade by Sean would make them a real gold set** |

---

## 14. What this spec does not claim

- That Jev will clear the gate on the canary **as independent evidence**. The corpus now runs and
  passes (§10.8), but its expected values are **authored from** the engagements rather than captured
  from intake forms, so it evidences *"behaviour has not moved"* more strongly than it evidences
  *"the behaviour is correct"*. A blind regrade by Sean would close that gap.
- That clearing the gate proves accuracy. §10.5 — it proves **agreement**, against one grader.
- That the weights are correct. They are **calibrated** (§10.7, D20), which is stronger than a
  hypothesis and weaker than accuracy: they track one human across 120 businesses, and a second
  grader would test whether that human was right.
- That calibration has been **deployed end to end**. Half of it has: `rubric.json` is promoted to
  1.8.0 (§5.3.1), so the live file and the harness now read the same rubric. **But there is still no
  production scorer** — `jev` exists only inside the calibration harness — so nothing serves a
  report yet, and step 4 of §5.3.1 (the scorer must refuse a non-promoted rubric) is unbuilt.
- That enrichment will be reliable — §4.5 makes it non-load-bearing.
- That the current Stripe path works — F1 says it does not.
- That any provider choice is permanent — §6.3 keeps it reversible.
- That the free report can ship before calibration clears — §10.6 is a hard gate.
- That the open-relay risk is closed — it is identified (§3.7) and needs D11. It is **the most
  serious gap in the design** (§3.7) and the largest item still standing between this spec and
  MVP-0.
- That the research-dataset claim is licensed. **It is conditional** (§7.7): permitted only while
  the measured opt-in rate supports it *and* every surfaced figure clears the k-anonymity floor.
  D19 authorised the mechanism, not the claim.
