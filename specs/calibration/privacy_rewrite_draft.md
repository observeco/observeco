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
> **How long we keep it.** Your submission and report are deleted **30 days** after we send you the
> report, unless you asked to be followed up — in which case we keep your contact details until you
> unsubscribe. You can ask us to delete it sooner and we will.

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
> | **The model provider (TypeSafe)** | Your form answers and text fetched from public web pages — **never your email address, and never your business name** | United States |
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
| **P4** | Retention: 30 days post-report; contact kept until unsubscribe | *as above* | ✅ / edit |
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
> can go into Singapore industry benchmarks, and I get the comparison back.
>
> *The report itself is what you asked for. It is never conditional on the boxes above.*

---

### Why each line is worded that way

| Element | Why |
|---|---|
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

**E2 — the k-anonymity FLOOR is not set.** *"No business name" is a promise; **how many** businesses must be
in a cell before a comparison may be shown is a number, and it is not in the spec.* Too low (say 3) and a
reader can re-identify; too high and the benchmark never renders, so the unlock becomes a promise the tool
cannot keep. **This is a threshold, and thresholds are Sean's call.**

**E3 — where this block sits on the form.** *Below the submit button reads as an afterthought and the rate
will show it; above the submit button, next to the report they are asking for, is where the trade is
legible.* **Recommend: directly above the submit button, in the same visual block as the button.**
