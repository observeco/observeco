# OBS-SPEC-095 — Business Review Lead Engine

**Status:** DRAFT v3 — architecture, decisions locked. Tactical sequencing deliberately out of scope.
**Date:** 2026-09-23
**Owner:** Sean
**Name:** KIV (D1)
**v2 change:** Refocused on architecture and the constraints we must factor in. Committed
decisions folded in; tactical build order removed.
**v3 change:** Email decisions locked (Resend transactional / Brevo marketing, `mail.observeco.com`).
Added §6.4 — Brevo is a processor, never a contact store. Corrected the now-stale claim that the
provider choice was open.

---

## 1. The product

A page on observeco.com that explains what a full competitive analysis contains, and offers a
free light-touch business review in exchange for name, email and ~15 answers. The review is
generated automatically and emailed. It returns **five dimension scores, a composite index, a
verdict sentence and the one gate that would falsify the position** — a flavour of the full
report, with the substance withheld. Its job is qualification, not volume.

**Scoring doctrine (non-negotiable):** *Jev types the judgments. Code computes the score.*
Jev is a System One labeller returning calibrated probabilities, not an oracle. Every
dimension score must be traceable to a named judgment.

**Committed decisions**

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

---

## 2. Architecture overview

Five layers. The governing principle is **asymmetric failure**: the report must exist even when
every external dependency is down.

```
L1  CAPTURE      form · consent record · contact                        [must not fail]
L2  ENRICHMENT   web-search-scraping-protocol                           [best-effort]
L3  SCORING      Jev · rubric JSON · composite in code                  [gated]
L4  DELIVERY     transactional stream · marketing stream                [must not fail]
L5  CRM          pipeline · stages · suppression · retention
```

**L1 and L4 must never fail. L2 may fail freely. L3 is the only gated layer.** A dead API key
degrades depth — never existence.

---

## 3. L1 — Capture, consent and PDPA architecture

### 3.1 PDPA is an architecture concern, not a page footer

The obligations that produce structural requirements, not copy:

| PDPA obligation | Architectural consequence |
|---|---|
| **Consent must be purpose-specific** | A boolean `consent=true` is not a consent record. Store purpose, timestamp, source, and **the exact consent text version shown**. |
| **Notification** | Purpose, data collected, and a contact point stated at the point of collection. |
| **Withdrawal as easy as giving** | Self-service preference centre. Withdrawal is not a support ticket. |
| **Retention limitation** | A scheduled job that deletes or anonymises. "Forever" is not a retention policy. |
| **Transfer limitation** | Every processor registered with its data category and location. |
| **Do Not Call (DNC)** | **A separate regime.** Applies to outbound phone/WhatsApp marketing. |
| **Breach notification** | Contact data must be identifiable and deletable as a set. |

### 3.2 The two-purpose consent model

Sean's decision: identity first (first name, last name, email) so abandoned forms remain
contactable. That creates **two distinct purposes**, and they must not be bundled:

1. **Report delivery** — required to deliver what was asked for.
2. **Follow-up / nurture** — optional, separately given, separately withdrawable.

A single checkbox covering both is the common PDPA failure. The architecture carries
**per-purpose consent rows**, so withdrawing one does not revoke the other.

The "finish your review" nudge for abandoned forms falls under purpose 1 (it completes the
requested action) — but that first email must not carry marketing content. That constraint
belongs in the template layer.

### 3.3 The DNC boundary is a design advantage

The DNC regime governs outbound marketing to Singapore phone numbers. **A user clicking a
`wa.me` link is user-initiated contact — outside DNC.** Sean's entire site already works this
way, and it is the correct posture, not a workaround.

**Architectural consequence:** inbound WhatsApp is an unrestricted response channel; outbound
WhatsApp marketing requires a DNC check first. The CRM must distinguish the two by recording
*who initiated* on every Activity row. Retrofitting this later means not knowing which contacts
you may lawfully message.

### 3.4 Processor register

| Processor | Holds | Location | Note |
|---|---|---|---|
| Supabase | contacts, consent, reports | confirm region | |
| Resend | email address, message content | **US** — transfer clause needed | |
| Brevo | email address, message content, **contact records** | **EU** | marketing stream. Processor only — see §6.4 |
| TypeSafe (Jev) | **form answers only** | US | see §5.5 |
| Google (Places, if used) | business query strings | US | not personal data |

### 3.5 `privacy.html` is a launch prerequisite

Current text states: *"We don't run servers that store your data"*, *"There are no ObserveCo
servers that process or store your data"*, *"We never share your data with third parties. No
third-party data processors."* All three become false on launch. Blocking, not cleanup.

---

## 4. L2 — Enrichment via the web-search-scraping-protocol

Using the Hermes protocol rather than a hand-rolled scraper. It already owns the routing
(`SEARCH → FETCH → EXTRACT → ESCALATE → GRADE`) and — critically — **it already owns the
problem that would silently corrupt this pipeline.**

### 4.1 The load-bearing finding

From the protocol, measured over 10 mixed URLs: **6 (60%) returned a Cloudflare challenge, an
access-denied body, or a CSS-dense shell as "content" — with no error.** `fetch_markdown`
returns a non-empty string; nothing upstream flags it. A figure regex even matched numbers
inside the challenge page's `<style>` block.

**Why this is architecture, not a bug:** enrichment output is fed to Jev as evidence. If a
block page arrives as ordinary text, **Jev scores a Cloudflare challenge as though it were a
competitor's website**, and the report is confidently wrong. The protocol's remedy — gate every
capture on a validity check (challenge signature + prose density + single-unbounded-line) — is
**mandatory, not optional**, and must run before anything reaches L3.

This is the single highest-risk seam in the system.

### 4.2 GRADE supplies the "what we couldn't check" section

The protocol's reward layer already produces the structured verdict this report needs:
grounding for synthesis tasks, coverage for enumeration. That maps directly onto the report's
confidence band and its *"what we checked / what we couldn't check"* block.

**Design consequence:** the honest-limits section is **generated from the grading layer, not
written by the model.** Limits the pipeline observed are real; limits a model narrates are
plausible fiction.

### 4.3 What enrichment feeds

| Input | Feeds dimension |
|---|---|
| ACRA / data.gov.sg (open, SSIC-filterable) | Market headroom |
| Competitor set via search | Competitive pressure |
| Competitor messaging via fetch | Position availability |
| Competitor size/tenure | Defensibility |

### 4.4 Non-load-bearing by construction

Per the cannot-refuse contract: **the form answers alone must carry all five scores.**
Enrichment is best-effort behind a hard timeout. A failed fetch degrades depth, never
existence.

---

## 5. L3 — Scoring

### 5.1 The five dimensions

| # | Dimension | Weight |
|---|---|---|
| 1 | Market headroom | 15% |
| 2 | Competitive pressure | 20% |
| 3 | Position availability | 25% |
| 4 | Defensibility | 25% |
| 5 | Demand reach | 15% |

Weighted toward 3 and 4 because the brief is *viability through differentiation*, not industry
attractiveness. Composite → band: Fragile (5–39) · Contested (40–59) · **Viable, conditional**
(60–74) · Strong (75–95). **Clamped to 5–95 — no score may imply certainty the method lacks.**

### 5.2 Variable dimension set (required by D7)

A dimension that cannot clear is dropped and stated. **The scorer and the report renderer must
therefore support N dimensions from day one** — weights renormalised at runtime, not hardcoded
in the template. A hardcoded five-bar layout makes a four-dimension ship a rewrite.

### 5.3 One rubric, two implementations — one source of truth

The Python calibration harness and the production scorer must read **the same rubric JSON**.
Otherwise calibration validates a scorer that is not the one shipped. This is the most likely
way to fool ourselves.

### 5.4 Unit discipline (measured)

Jev returns **one aggregate verdict for a multi-item state** (verified: 42 inputs → 1 answer)
and **blends differently-scoped inputs into ~0.50 confidence**. Therefore:

- Per-competitor judgments **fan out one call each**; code aggregates.
- One narrow judgment per call. Never a batch.
- **Confidence is label-set-width dependent:** `conf = (n·p − 1)/(n − 1)`. A five-level score
  needs a different gate than the 3-option choices gated at 0.70 in `ask_jev.py`.

### 5.5 Egress boundary

Jev sees **form answers and enriched public text only.** Never the CRM, never other contacts,
never client analyses. Deliberate egress decision; belongs in the processor register (§3.4).

---

## 6. L4 — Email architecture

### 6.1 The cost question, answered honestly

At Sean's realistic volume (~100 leads/month × ~4 emails ≈ 400 emails/month), **every option is
free.** The SES advantage materialises only above roughly 500K emails/month.

| Provider | Free tier | Paid entry | At 1M/mo | Notes |
|---|---|---|---|---|
| **Resend** | 3,000/mo (100/day cap) | $20 / 50K | ~$400 | Already half-wired here |
| **Brevo** | 9,000/mo (300/day) | $9 / 5K | ~$249 | Marketing + automation included; EU |
| **AWS SES** | 3,000/mo | $0.10 / 1K | **~$100** | No UI, no templates; sandbox exit by support case |
| SendGrid | **none** (60-day trial) | $19.95 / 50K | enterprise | Free tier retired May 2025 |
| Postmark | 100/mo | $15 / 10K | ~$1,800 | Best transactional; discourages marketing |

**So do not switch to SendGrid.** It costs more than the current setup and buys nothing. The
cheapest genuine option is SES, and it is only cheap in money — it costs templates, suppression
handling and reputation work, which is exactly what we would otherwise have to build. Resend
already sends *through* SES (`send.observeco.com` MX →
`feedback-smtp.ap-northeast-1.amazonses.com`); we are paying for the wrapper.

**Recommendation:** keep **Resend** for the transactional stream (already coded, DKIM present,
free tier covers us) and use **Brevo for the marketing stream** (Sean's decision). Treat both as
**swappable**. Cost is not the constraint — the transactional/marketing split is.

### 6.1a The volume that would change this

At ~400 emails/month, every tier is free. The decisions that would reopen the provider choice:

| Trigger | Reconsider |
|---|---|
| Marketing list > ~9,000 sends/month | Brevo free tier exhausted → paid Brevo vs SES |
| Transactional > 3,000/month | Resend free tier exhausted → $20/50K |
| Total > ~500K/month | SES becomes materially cheaper than any wrapper |
| Deliverability problems on the marketing stream | Separate sending IP, not a provider change |

None of these are near. The abstraction in §6.3 exists so the answer can change without a
rewrite.

### 6.2 Two streams — the part that actually matters

Standard practice, and it breaks silently if ignored: **never send marketing through your
transactional path.** Complaint rates from a blast degrade shared IP reputation, and then
report emails start landing in spam.

**Architectural consequence: two streams, separate subdomains, separate reputations.**

| Stream | Subdomain | Provider | Carries | Unsubscribe |
|---|---|---|---|---|
| Transactional | `send.observeco.com` (exists, Resend) | Resend | report, holding, need-more-detail | not required, still advised |
| Marketing | `mail.observeco.com` (**to create**) | **Brevo** | nurture, blasts | **required** |

Both subdomains authenticate by **DKIM alignment**; neither relies on SPF (Brevo's SPF stays
unaligned on shared IPs, and Resend's is already incomplete — §10 F4). DMARC `p=none` reports
rather than rejects, so a misconfiguration degrades silently. Verify each domain reaches
*Authenticated* in its provider dashboard before trusting it.

`mail.observeco.com` does not exist yet — no A record, no TXT. DNS is on Cloudflare
(`isabel`/`ivan.ns.cloudflare.com`).

### 6.3 The provider abstraction (D3)

D3 requires that blasting later is a **configuration change, not a rebuild.** That means a small
interface now, in the shape the codebase already uses:

```
EmailProvider
  send_transactional(to, template, vars, reply_to)
  send_bulk(to, template, vars, unsubscribe_token)
```

Registered by name; selected per stream by config. Resend implements both today; Brevo or SES
can implement either later without touching callers. The existing
`src/observeco/emails/sender.py` + `templates.py` registry is the layer to extend — add a
`stream` field per template rather than replacing the registry.

### 6.4 Brevo is a processor, never a contact store

**This is the constraint that matters most about adding Brevo.**

Brevo is not only an email sender — it stores contacts, has contact attributes, and ships a
**website tracker** that collects "identified contacts" who "have not necessarily subscribed to
receive your emails." Its free tier holds 100,000 contacts.

Used carelessly, that creates a **shadow CRM with its own consent state**, outside the Supabase
consent records in §3.2. The failure is specific and serious: Supabase says "withdrew marketing
consent on 12 Oct"; Brevo still holds the contact in a marketable list. **A second copy of
personal data with no synchronised purpose record is a PDPA problem regardless of which copy is
"authoritative."**

**Doctrine:**

| Rule | Reason |
|---|---|
| Supabase is the **system of record** for contacts and consent. Brevo holds a **projection**. | One authoritative consent state |
| Push to Brevo **only contacts who hold active marketing consent**. | Never mirror the whole CRM |
| On withdrawal, **propagate the deletion** to Brevo synchronously. | Withdrawal must be as easy as giving (§3.1) |
| **Do not install Brevo's website tracker.** | It collects non-subscribers as contacts |
| Do not use Brevo forms, landing pages, or automations as the entry point. | Consent must be captured by us, versioned, in Supabase |
| Suppression lives in Supabase and is checked before every send (§6.5). | A provider swap must not resurrect unsubscribed contacts |

A sync job that pushes consenting contacts into Brevo and removes withdrawn ones keeps the
projection honest. **Treat any contact present in Brevo but absent from Supabase as a defect to
be reconciled, not a lead.**

### 6.5 Own your suppression list

Bounce and complaint suppression must live **in Supabase, checked before every send** — not only
in the provider. Two reasons: providers differ, and a provider swap must not resurrect
unsubscribed contacts. Provider webhooks (`email.bounced`, `email.complained`) write into it.

### 6.5 Unsubscribe must be real

`_UNSUBSCRIBE_LINK` currently points to `https://observeco.com/unsubscribe` → **404**. Needs a
signed-token endpoint, no login required. PDPC's most common enforcement action is ignoring
opt-outs.

### 6.6 The 30s wall

`vercel.json` caps `api/**/*.js` at `maxDuration: 30`. Jev + enrichment + email exceeds this.
**The report is queued and worked asynchronously** — the request path only validates, records,
and returns "on its way."

---

## 7. L5 — CRM

### 7.1 Full pipeline (defined now so nothing is re-scoped later)

| Stage | Entry | Exit | Automatable |
|---|---|---|---|
| 0 Captured | Form submitted | Report queued | ✅ |
| 1 Report delivered | Email sent | Open / click | ✅ |
| 2 Engaged | Opened, no reply | Reply or call booked | ✅ |
| 3 Conversation | Replied / WhatsApp | Sean has spoken to them | ❌ |
| 4 Qualified | Call done | Fit decided | ❌ |
| 5 Proposal | Price quoted | Accept / decline | semi |
| 6 Won | Paid | Delivered | semi |
| 7 Delivered | Engagement closed | Renewal offered | ❌ |
| 8 Watch | Subscription active | Churn | semi |
| 9 Lost / Nurture / Dormant | — | Re-approach | ✅ |

**Entities:** Contact · Company · Report (versioned artifact) · Activity (records *who
initiated* — §3.3) · Deal (stage, value, Stripe linkage) · Sequence · Consent · Suppression.

The schema carries all ten stages from day one, so scaling is a **mapping, not a redesign.**

### 7.2 Stripe

Checkout payments for the paid engagement and the Watch subscription. **A separate webhook
endpoint** from the licensing webhook — that handler writes `licenses` rows with
`product_slug: 'solo'`, and consulting payments are a different entity. Separate endpoints also
mean one product line's webhook failure cannot affect the other.

### 7.3 RLS

Deny anon entirely on every new table; service-role only. The existing licensing schema grants
`licenses_anon_select` with `USING (true)` — anyone holding the anon key can read every row.
That policy must not be cloned.

---

## 8. Regression protocol

The threat model: **a scorer that passed calibration stops being correct without anything
changing on our side.**

### 8.1 Why this is a live risk, not hypothetical

The TypeSafe model is versioned (`jev-1.13.0`) and can change under us. This has already
happened once in this ecosystem: classifier.dev silently swapped its backend from Jev to
`deepseek-v4-flash` and `gemini-3.8-flash` between 2026-09-19 and 2026-09-22 — **three days**.
Standing lesson from that incident: *never assert a model identity from one measurement; always
re-read the `model` field at runtime.*

**Architectural consequence: every report artifact stores the identity of the scorer that
produced it.**

### 8.2 Provenance — every report carries

`rubric_version` · `model_id` (as returned by the API) · `prompt_hash` · `input_hash` ·
`enrichment_sources[]` · `dimensions_used[]` · `generated_at`

A report we cannot reproduce is a report we cannot defend to a paying prospect.

### 8.3 The canary

The six calibration cases run **on a schedule** as a canary job — the same pattern as
ObserveCo's existing canary infrastructure. Same inputs, fixed expected outputs.

| Trigger | Response |
|---|---|
| Any case moves band | **Alert Sean** |
| Composite moves > 8 points on any case | Investigate before next send |
| `model_id` changes | **Alert regardless of scores** — re-baseline and re-verify |
| Negative control stops failing | **Scorer is broken. Halt.** |

The negative control runs every cycle. **A scorer that cannot fail is not a scorer** — the same
class of defect as a test that measures frame rate instead of draw calls.

### 8.4 Degradation ladder

| Tier | Condition | Behaviour |
|---|---|---|
| 1 | Canary green | Scorer live |
| 2 | Canary flags, ≤1 case | Serve reports **stamped with the drift notice**; hold the dimension that moved |
| 3 | Canary fails, >1 case | **Feature-flag the scorer off.** Capture continues. Reports queue `held` |
| 4 | Model unreachable | Queue `held`; never substitute a different model silently |

**Tier 4 is the important one.** Substituting a local model for a judgment task is a documented
failure mode here — a local model scored 12/12 *wrong* at ~0.9 confidence on a comparable
taxonomy. **A confident wrong label is worse than no label.**

### 8.5 Never send a score we do not trust

Reports already in flight when a regression is detected are **held**, not sent. The holding
email is honest: we are re-running your review. No score is promised and none is withdrawn.

### 8.6 Launch gate

**Ship the scored report only when Jev clears all six labelled cases and fails the negative
control as predicted.** "Clears" = same band per case, every dimension within ±1 level, control
fails.

Calibration labels are **the position as it stood at engagement start**, fed to Jev, which must
reproduce the analysed conclusion — the only correct analogue to production, where Jev scores a
form submission rather than a finished analysis.

Six cases: GreenPackers (fringe, guerrilla only) · Bonefirm (feasible, one condition) · CaiCa
(reason-to-purchase weak) · PetDirectory (position open, demand unbuilt) · SGFitness (white
space in a specific segment) · SaladShop (CBD saturated, white space outside it).

**Disagreement triage — the standing rule applies: judge-vs-corpus disagreement is UNRESOLVED
until hand-read.** Do not default to "Jev is wrong"; that has been the wrong call before.

| Branch | Condition | Action |
|---|---|---|
| J1 | Hand-read confirms Jev missed | Fix criterion/unit/gate. Jev was wrong. |
| J2 | Hand-read confirms the analysis missed it | Correct the label — **a finding about our own method** |
| J3 | Both defensible | Dimension genuinely ambiguous → **drop it and state it** (D7) |

---

## 9. Two-stage ship (per D4)

Calibration gates the **scoring** layer only. Capture, payment and delivery do not depend on it.

| Stage | Contents | Gate |
|---|---|---|
| **MVP-0** | Page + form + CRM capture + Stripe for the paid engagement. **No free score.** | Ships when ready |
| **MVP-1** | The free scored report | Calibration clears |

MVP-0 is honest standing alone — it is a lead form for the engagement, which is what the site
already promises. It never promises a score, so **if calibration blocks, no prospect ever learns
we tried.** Prospects captured during MVP-0 gave details for the paid engagement; no "your
report is coming" obligation exists, and the free review can be offered later as a fresh,
honest gift.

Three report templates: **A** report · **B** holding (regression) · **C** need-more-detail
(inputs too thin — names exactly what is missing, never a dead end).

### 9.1 Principle set (applies to every send)

1. Never send a score we don't trust.
2. Never claim human review on a free report.
3. Always carry the confidence band and "what we couldn't check".
4. If we can't score, say precisely what we'd need.
5. Every email carries a working unsubscribe (F3b — currently 404).

---

## 10. Verified findings — constraints on the design

Measured, not assumed.

| # | Finding | Consequence |
|---|---|---|
| F1 | `POST /api/stripe/webhook` → **500** in production (expected 400) | Throw occurs before the `try`; leading hypothesis is an unset `STRIPE_SECRET_KEY`. **The Stripe path cannot be verified until resolved.** |
| F2 | That handler inserts `licenses` rows with `product_slug: 'solo'` | Consulting payments need a **separate endpoint** |
| F3 | `logo.png` → 404 (live logo is `assets/logo.svg` → 200); `/unsubscribe` → **404** | F3b is a PDPA blocker for the marketing stream |
| F4 | DKIM present on `observeco.com`; `send.observeco.com` MX is Resend's SES endpoint, but its SPF omits Amazon SES; DMARC `p=none` | Likely functional via DKIM alignment, but **degrading silently**. Confirm *Verified* in the Resend dashboard. |
| F5 | `sean.foo@observeco.com` is inbound-only (Cloudflare Email Routing) | Sending as it needs only domain authorisation; **set Reply-To explicitly** |
| F6 | `privacy.html` states we run no servers and use no processors | **Launch prerequisite** |
| F7 | `licenses_anon_select` is `USING (true)` | Do not clone this RLS policy |
| F8 | `maxDuration: 30` on `api/**/*.js` | Forces the async queue |
| F9 | **Zero `<form>` elements** across the live site | First-ever data collection |
| F10 | `content-spec-v1.md` promised a free "positioning snapshot"; grep finds it on **no** live page | This feature is that promise, re-scoped |

**Backend note:** the pricing research in §6.1 ran on the keyless fallback because the
configured ddgs backend failed that call. Figures come from vendor pricing pages via secondary
comparisons and should be re-verified against the providers' own pages before being relied on
for a purchasing decision.

---

## 11. What this spec does not claim

- That Jev will clear the gate. §8.6 exists because it may not.
- That the weights are correct — they are a hypothesis for calibration.
- That enrichment will be reliable — §4.4 makes it non-load-bearing.
- That the current Stripe path works — F1 says it does not.
- That any provider choice is permanent — Resend/Brevo are locked as the *current* answer (§6.1),
  and §6.3 exists so either can be swapped without touching callers.
- That the free report can ship before calibration clears — §8.6 is a hard gate.
