# privacy.html rewrite — DRAFT for Sean's approval (blocker 4, §3.4)

**Status: DRAFT. Nothing has been applied.** `website/privacy.html` is untouched and still served as-is
with the five now-false statements. This file is the wording to drop in.

**Why this is a rewrite and not an edit:** the live page truthfully describes a product that runs *only*
on your machine. The business review form changes that — an address and a business description now leave
the submitter's machine and land in Supabase. So the page must describe **two paths**: the local
monitoring product (still true, unchanged) and the business review report (new).

---

## PART A — the five statements that are now false

### A1. Line 8 — the meta description (⚠ Google renders this first)

**Now:**
```html
<meta name="description" content="ObserveCo's privacy policy. Local-first AI agent monitoring — your data never leaves your machine.">
```

**Replace with:**
```html
<meta name="description" content="ObserveCo's privacy policy. The desktop product runs local-first; the business review report is submitted and stored with your consent, and this page says exactly what that means.">
```

---

### A2. Line 93 — "The short version"

**Now:**
> **The short version:** ObserveCo runs entirely on your machine. Your data never leaves your computer
> unless you explicitly opt in to telemetry. We don't run servers that store your data. We don't have
> user accounts.

**Replace with:**
> **The short version:** Two things live here, and they behave differently.
>
> **The desktop product** runs on your machine. Its monitoring data never leaves your computer unless you
> switch telemetry on yourself.
>
> **The business review report** is different by design: when you submit the form, what you type — your
> email, your business, and your answers — is sent to us and stored so we can produce the report. We tell
> you below exactly who else touches it, and you control the parts that are optional.

---

### A3. Lines around §2.2 — "This data never leaves your machine"

**Now:** a statement that this data never leaves your machine.

**Replace with:**
> **For the desktop product: this data never leaves your machine.** It is stored locally and is not
> transmitted anywhere. Telemetry is off unless you turn it on.
>
> **For the business review form:** the form is a web form. What you submit is sent to our servers
> (Supabase) so we can build your report and email it to you. That is the whole point of submitting it.
> See *The business review report* below.

---

### A4. Line 144 — "We never share your data"

**Now:**
```html
<li><strong>We never share your data with third parties.</strong> No third-party data processors.</li>
```

**Replace with:**
```html
<li><strong>We don't sell your data, and we never share it for anyone else's marketing.</strong>
We do use a short list of service providers to run the report — a database, an email sender, and a
model provider. They can only use it to provide that service. They're named below.</li>
```

---

## PART B — new section to add: The business review report

*(Place after the existing product sections, before the retention section.)*

> ### The business review report
>
> **What we collect.** Your email address; your business name; and your answers about your business —
> including your category, your positioning sentence, your named competitors, and your customer
> description. If you give a website address, we fetch that page and other publicly available pages to
> read what your business and your competitors publicly say.
>
> **What we do with it.** We produce your report and email it to you.
>
> **Your choices, separately.** When you submit, you are asked three things, and they are not bundled:
>
> | | What it is | Required? |
> |---|---|---|
> | **Your report** | Producing and emailing the report you asked for | *This is the thing you asked for — not a permission* |
> | **Follow-up** | Occasional emails about ObserveCo's services | **Optional — unticked** |
> | **Benchmark** | Using your answers — with no business name, no email, and no personal names — in aggregated comparisons | **Optional — unticked** |
>
> **You can withdraw any of these at any time**, and withdrawing one does not affect the others. Every
> email we send has a working unsubscribe link, and it works whether or not you have an account with us.
>
> **How long we keep it.** We keep your report and the answers behind it for **two years**, so we can stand
> behind a score if you come back to it later. If you asked us to keep in touch, we keep your contact details
> until you unsubscribe or ask us to stop. You can ask us to delete everything at any time and we will.

**✅ CORRECTED — DECIDED BY SEAN (7 Oct): WE KEEP THE DATA.** *The previous version of this line promised
deletion 30 days after the report was sent. **That was wrong twice over: it contradicted his own §7.5, and it
contradicted what he actually wants.***

**⚠ §7.5 ALREADY SPECIFIED A KEEP POLICY — the 30-day sentence was the error, not the code.** *§7.5 ("Retention
must name a period") defines retention **per category** and never says "delete everything": consent records kept
longest (they are the evidence that made processing lawful), **reports medium — 24 months — "defensible if a
prospect disputes a score"**, contacts who never converted shortest, enrichment cache days. **The 30-day
sentence came from the confirmation-email draft, where it applies to a DIFFERENT case, and I carried it into the
page by mistake.***

**⚠⚠ AND THE TWO PROMISES ARE GENUINELY DIFFERENT — SEPARATING THEM IS THE FIX.** *The confirmation email says
**"If this wasn't you, ignore this email … We'll delete your details within 30 days."** That is about the
**unconfirmed** case — someone who never asked for a report. **`purge_expired()` implements exactly that**:
`DELETE FROM confirmations WHERE status='pending'`.* ***So the email's promise is the RIGHT promise and needs one
thing only — a scheduler, since the function is currently never called.*** *The page describes the **confirmed**
case, where the customer asked for the report and may want it later. **Different case, different period, different
obligation. They were never the same sentence.***

**⚠ STILL REQUIRED BEFORE THIS SHIPS — and it is engineering, not wording:**
1. **A retention decision per category** — §7.5's table still carries provisional periods as a choice for Sean;
   the sentence above uses its report figure (**24 months**), stated in plain English as "two years".
2. **A purge that covers confirmed rows** — `purge_expired()` handles `pending` only, which is correct for the
   email promise and **insufficient** for this one.
3. **A scheduler** — no function runs unless something calls it, and nothing does today.

---

## PART C — new section to add: Who else touches your data

*(Named processors. This replaces the "no third-party processors" claim with the truth.)*

> ### Who else touches your data
>
> We keep this list short, and we name each one:
>
> | Provider | What they hold | Where |
> |---|---|---|
> | **Supabase** | Your contact record, your consent record, your report | **Singapore** (`ap-southeast-1`) |
> | **Cloudflare Turnstile** | A bot check when you submit the form — no profile of you | Global |
> | **Resend** | Your email address and the message we send | United States |
> | **Brevo** | Your email address, if and only if you opted into follow-up | European Union |
> | **The model provider (TypeSafe)** | Your business name, the answers you typed, and text fetched from public web pages | United States |

**⚠ WHAT WE DO *NOT* SEND, AND WHY THAT IS THE HONEST VERSION OF THIS LINE.** *Your **email address** and
**phone number** are stripped before anything is sent — verified in the code that builds the request, not
assumed. **Your business name is not stripped, because the scoring needs it**: a positioning read is a
comparison against the rivals in your category, and the model resolves and reasons about who those are by
name. So the earlier draft of this line — *"never your email address, and never your business name"* — was
**false**, and promising it would have been a written statement of something the product does not do.

**✅ MEASURED 7 Oct — the trade is no longer a guess (spec §3.7.19).** *Both arms of the 120-case corpus were
run on rubric 1.22.0, differing only in whether `business_name` was sent.* **Without the name: band agreement
with your 120 grades fell from 100% within-1 to 96%, and the cases that changed went DOWN in 53 of 58 — a mean
loss of 5.32 points, above the ±4-point noise floor. The damage concentrates on famous brands (MA 4–5: −8.7 to
−8.9; MA 1–2: −2.0), because the name is how the model recognises who the rivals are.***

**So the name is not a label, it is brand recognition — and dropping it would make the instrument measurably
worse. On D3 though (weak-positioning SMEs, the actual market) both arms are identical, so the name is
insurance against brands we are not targeting.** *Decision: the name stays, and the promise keeps the honest
form above.* **Reproduce:** `SANDBOX_STRIP_BUSINESS_NAME=1` on `run_corpus_parallel.py`.
>
> **We don't sell your data, and we don't share it with anyone else.** These providers are contracted to
> us and can only use your data to provide their service to us.

---

## PART D — the root `privacy.html` (not served)

`vercel.json` sets `outputDirectory: "website"`, so **only `website/privacy.html` is served**. The root
copy (199 lines, *different* content) is dead weight and a trap — the next person edits the wrong file.
**Recommend: delete it, or reduce it to a one-line pointer** to `website/privacy.html`.

---

## Sign-off needed

| # | Decision | My draft | Your call |
|---|---|---|---|
| **P1** | A1 meta description wording | *as above* | ✅ / edit |
| **P2** | A2–A4 replacements | *as above* | ✅ / edit |
| **P3** | The three consent labels (matches `004_consent_records.sql`) | *Your report / Follow-up / Benchmark* | ✅ / edit |
| **P4** | Retention wording | ✅ **DECIDED — keep the data** (two years for the report; see above) | period: ✅ / edit |
| **P4b** | §7.5's other periods — consent (longest), unconverted contacts (shortest), enrichment cache (days) | *provisional in §7.5* | ✅ / edit |
| **P5** | Supabase region | ✅ **`ap-southeast-1` (Singapore)** — supplied 7 Oct | done |
| **P6** | Delete the root `privacy.html`? | *yes* | ✅ / edit |

*Once P1–P6 are settled: drop A1–A4 in place, append Parts B and C, delete the root copy, then the page
and the consent wiring go in together so the wording and the checkboxes can never disagree.*


---

## PART E — the consent block on the form (DRAFT for approval)

**⚠ These must ship with Parts A–C above.** The notice and the checkboxes describe the same three
purposes; if they disagree, the evidential value is gone (§7.7).

**The spec's governing rule (§7.7):** *"The checkbox is not 'may we use your data for research'. It is the
**unlock for the comparison itself**."* And the hard constraint beside it: *"the withheld benefit must be
the COLLECTIVE GOOD, never the SERVICE"* — **the report is never gated**, or the consent is coerced.

**So there are TWO checkboxes, not three** — purpose 1 is the thing they asked for, not a permission they
grant. **Giving it a checkbox would blur exactly the distinction §7.7 draws.** It gets a line of text.

---

### The block, as it would appear

> **We'll produce your report and email it to you.** Two optional extras below — both unticked. Tick only
> what you want.
>
> ☐ **Keep me posted** — occasional emails about ObserveCo's services, and what we're learning from these
> reviews.
>
> ☐ **Show me how I compare.** My answers — with no business name, no email address and no personal names —
> can go into Singapore industry benchmarks, and I get the comparison back **on a best-endeavours basis**.
>
> *The report itself is what you asked for. It is never conditional on the boxes above.*

---

### Why each line is worded that way

| Element | Why |
|---|---|
| **"on a best-endeavours basis"** *(Sean's phrase, 7 Oct)* | **The honest qualifier, and it resolves E2's cold-start problem.** *A comparison **cannot be guaranteed**: the category pool may be too thin to render one, and rival pages may not be readable (§4.6.0a). **It promises the attempt, not the outcome** — which is exactly what the trade requires. Note it makes **any total-count claim** in the same breath impossible: a count reads as verified, and best-endeavours is explicitly not* |
| **"Show me how I compare"** as the label | *It names the BENEFIT, not the permission.* The spec is explicit that the research checkbox must read as the unlock for the comparison — a request framed as "may we use your data" is what produces a near-zero rate, and a near-zero rate forces the dataset claim down |
| **"and I get the comparison back"** | *Makes the exchange explicit: they give aggregation rights, they get the benchmark. The spec calls this a TRADE, and says the first draft's "favour" framing is why its rate would have been poor* |
| **"with no business name, no email address and no personal names"** | *The spec's k-anonymity promise, stated where the decision is made rather than buried in the policy. D34's rule — "analyse the business, never the person" — is the same line* |
| **"Keep me posted"** | *Separate purpose, separate row, plain English. Bundling follow-up with the report is the §3.2 failure* |
| **"both unticked"** | *A pre-ticked box is not consent under the PDPA. Stating it plainly also raises the rate, because it removes the suspicion of a trick* |
| **"never conditional on the boxes above"** | *The coercion guard. If declining ever degrades the scored report, the consent is void and the purpose with it* |

---

### Two open points I could not settle from here

**E1 — enriched public-source material is a SEPARATE question, and the label must not overpromise.**
§7.7 says purpose 3 covers **what the submitter tells us**. The report *also* enriches from public sources
(Places data, review text, registries) — different provenance, different rules, and the spec flags it as
needing **its own determination** before the dataset claim leans on it. **So the label deliberately says
"my answers", not "my report" or "everything we find".** *If it said "everything", it would promise a use
the spec has not yet justified.*

**✅ E3 — SEAN'S X/Y COMPETITOR-REVEAL (7 Oct): the DIRECTION is adopted, the number is BLOCKED.**
*Sean: "we have identified a total of X number of competitors, but since it is a free report we are only
showing you Y. To unlock the remaining competitors, please consider using our full services."*
**The boundary is sound and already exists** — the free report already says ownership is "the paid analysis".
**But X has no honest denominator today**, and I reproduced why (§3.7.20): the occupant miner is a documented
negative result (four fixes failed) and on a live bakery scan it returned **`"Number of"` as a competitor**;
the category search returns articles *about* the category, not members *of* it; and the free path **never runs
the scan at all** (`server.py:261`, off by default). **So the honest sentence today would read "we identified 0
competitors and are showing you 2".** *The unlock that fixes it is in-hand: the scan's **capture** layer works
(11 of 12 readable) — only the name-extraction is broken — and fixing it also fixes the live report's
"it would not let us read it".*
**⚠ THE ONE RULE THAT KEEPS THIS LEGAL:** *withhold the **analysis**, never the **accuracy** of what is already
shown. A free report deliberately made thinner is coerced consent wearing a product name (§7.7).*
**⚠ And "best endeavours" contradicts "a total of X" in one sentence** — resolution: **the count is stated
only when measured; otherwise no number.**

**E2 — the k-anonymity FLOOR is not set.** *"No business name" is a promise; **how many** businesses must be
in a cell before a comparison may be shown is a number, and it is not in the spec.* Too low (say 3) and a
reader can re-identify; too high and the benchmark never renders, so the unlock becomes a promise the tool
cannot keep. **This is a threshold, and thresholds are Sean's call.**

**E3 — where this block sits on the form.** *Below the submit button reads as an afterthought and the rate
will show it; above the submit button, next to the report they are asking for, is where the trade is
legible.* **Recommend: directly above the submit button, in the same visual block as the button.**
