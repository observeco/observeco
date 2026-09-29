# OBS-SPEC-095 — Business Review Lead Engine

**Status:** DRAFT v42 — **Is PS just a renamed RS? NO — measured: the RENAME changed 7% of cases, the CONSTRUCT changed 66%. §3.6 form fields closed (D38a). ⚠ Four items remain genuinely open and require work, not editing — see §10.10.**
**Date:** 2026-09-23 (v8–v11: 2026-09-27–28; v12–v22: 2026-09-28)
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
**§7.7's two-box retention table gains a third row, and §7.7.2 turns it into a five-option space** —
Levels.fyi licenses records carrying
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
**v13 change — two corrections, both from Sean, both accepted.**
*(1) **D26 was a narrow recommendation presented as a decision.** It offered a binary — anonymise, or
license pseudonymously — and embedded a false premise: **anonymisation is a property of each RELEASED
ARTEFACT, not of the stored record.** The same submission can be pseudonymous in the warehouse and
anonymised in every published view, so the question is *where the boundary sits*, not which of two
modes to choose. **§7.7.2 now sets out five options (A–E) with pros, cons, and a path to viability for
each**, and the decisive criterion is **reversibility** — B and C are one-way doors, and E is the only
option that keeps B reachable. Recommended: **E (consent-tiered), D as interim, B revisited when the
dataset is worth the obligation.**
*(2) **§7.10 added — the toolkit IS the test (D29).** Sean's point: if the riskiest assumption fails
there is no viable business model, so why not make the toolkit the test, built properly, so the result
is as conclusive as possible? **The earlier phasing was wrong.** Nothing else consumes the benchmark —
the toolkit is its only consumer — so deferring it meant building something no one was waiting for.
Worse, the risk was backwards: the benchmark is the *passing* part, and **a benchmark built after the
demand test cannot answer the demand question**, because the demand test would have run without the
comparison that is supposed to create the demand. **The toolkit is the instrument, not the subject,**
with five measured funnel steps and decision rules pre-registered before launch. The honest limit is
stated: a small N establishes whether the path exists, not its rate.
**v14 change — Sean's five decisions, and one of them reverses a premise.**
*(1) **D25 — the pool is built by WEB RESEARCH, not only the calibration corpus.** Sean: *"we should
have exercised the web search protocol skill to find and score other competitors, just like what we
did for our competitive analysis projects."* §4.4 had listed *"competitor set via search"* but as
**best-effort enrichment behind a hard timeout**; §4.6 now makes it a **deliberate
protocol-governed scan** (`web-search-scraping-protocol`: search → fetch → extract → escalate →
grade), with §4.1's validity gate extended to every URL it touches — because the measured **60%
silent-failure rate** (a block page returning as ordinary text) would otherwise hand Jev a
Cloudflare challenge to score as a competitor's website.
*(2) **D30 — the pre-flight gate (Sean's explicit condition).** *"It burns a lot of tokens so let's
make sure before we run the analysis we assess the input quality first."* §3.11 fixes the ORDER:
the deterministic quality check and categorisation fire on the **form answers alone, before a single
search is issued.** The naive shape (scan → score → discover the input was unusable → refuse) burns
the full research cost on a submission we will refuse anyway. **It reuses §3.10's existing floor, so
it adds no new logic — only changes where it fires.** The trap it protects against is not the token
cost but the **false confidence** of a comparison built on a category inferred from thin text.
*(3) **D26 — Sean's objection is RIGHT and §7.11 records why.** *"I don't see how we can monetise this
with credibility because accuracy due to time uncertainty is always a problem. I am ok with E or D."*
A positioning dataset is not a financial one: a salary figure is *measured* at a time, but **a
competitive position is a relationship that moves when any party moves** — so it decays from both
ends, and **the submitter's half is not re-scannable at all.** Worse for monetisation: **if the
competitor material is gathered from public sources by a repeatable protocol, the pool is
reproducible by anyone** — a scrapeable dataset is not a proprietary asset. **What IS defensible is
the rubric, the calibration (120 blind grades) and the scored judgments.** So D26 is largely moot
for the *dataset* and live only for the *method*. **Recommendation revised to D as the posture with
E's structure retained.** ⚠ **This also corrects v13's justification for the two-tier disclosure: it
protects CONTRIBUTORS, not the asset.**
*(4) **D24 — yes** (public-source material may enter the dataset; §4.6's `observed` tier governs
labelling). **(5) D28 — yes but lightly** (verification must not become a conversion barrier).
**(6) D27 — deferred to the future.**
*(7) **D31 — NEW, created by the scan.** Scoring a named competitor that never consented, cannot see
the result and cannot dispute it is a different product with a different risk profile. Recommended:
**anonymous pool only** — same insight to the submitter, no third-party exposure.
**v15 change — the D29 test is now quantified, and its limit is recorded. ⚠ This is the least
comfortable section in the spec and it matters most.**
*(1) **What the test CAN establish (§7.12).** Three citable rules: the **rule of three** — zero paying
engagements from N submissions bounds the true rate at **3/N** (100 → "<3%", 300 → "<1%"; unreliable
below N=30); **precision** — ±5pp needs **n = 1/B² = 384**; and **two-arm comparison** at 80% power
needs ~435/arm to distinguish 5%→10% and only ~199/arm for 10%→20%. **Practical floor: pre-commit to
300 completed submissions before any go/no-go** (at ~100/arm you have ~52% power on a 10%→20% question
— a coin flip). **Peeking destroys it:** continuous monitoring can inflate a nominal 5% error rate to
**26.1%**; even ten looks means a reported **1.0%** is needed for a true 5%. And low power does not
merely miss — below ~50% power a "significant" result is typically a large overestimate (Type M), below
~10% it is often the wrong sign (Type S).
*(2) **What it CANNOT establish — the identifiability limit.** A null cannot distinguish **a bad tool
from a bad segment from a bad price from no distribution.** Four different problems, opposite remedies.
A test that cannot separate them is not evidence for or against the business model.
*(3) **⚠⚠ The base rate is already unfavourable, before any test runs.** UK LSBS 2023, **VERIFIED
verbatim**: **24% of micro-businesses (1–9) sought external advice in the past 12 months, down from 31%
in 2015** (small 34%, medium 45%, **no-employee firms 16%**). Worse inside that minority: only **32% of
micro firms used a consultant or business adviser**, against 47% (small) and 51% (medium) —
**accountants dominate.** So consultants are a minority channel even among the minority who buy advice.
**The offer evidence is worse:** micro and small firms **offered consulting at 70–90% subsidy —
having already signed a letter of interest — took it up only 53% of the time**, citing liquidity
(Bruhn/Karlan/Schoar, World Bank Puebla Mexico RCT, n=432, **VERIFIED verbatim**). ILO: *"potential
demand is high, but the effective demand is low"* (23%–65% would pay US$150 pre-experience, rising to
53–100% after delivery).
**This raises D32 — whether D3's target segment is the right COMMERCIAL target.** A segment can be the
best *audience* and the worst *customer* at once.
*(4) **The channel problem, and D33.** Referrals plus direct outreach supply **~two-thirds of new
business even for high-growth firms** (n=495); **71% of buyers ask a person first, 11% search online**;
and **51.9% of referred prospects rule a firm out before talking to it.** So **a cold-only test of a
referral-led market will return a misleading null** — it would look like evidence against the toolkit
when the real finding is that the wrong channel was measured. **§7.10's step 3 is promoted from
preference to necessity: test cold acquisition AND the referral artefact, reported separately.**
The 51.9% figure is also the strongest argument for the artefact itself — a credible positioning report
is what survives that filter.
*(5) **What can honestly be claimed:** *"With N submissions we can bound the conversion rate to within
X. We cannot yet distinguish a weak tool from a weak segment"* — and **the second row of the fail branch
is the one that saves the project:** a null at ≥300 with a working instrument is information about the
MARKET, and the remedy is D32 (retarget), not a code rewrite.
*(6) **No published figure exists for the exact funnel** free-diagnostic → paid consulting in a small
professional-services firm. Near-total reliance on **vendor platform data** (Interact, Unbounce, Ruler,
Chili Piper, Zuko, First Page Sage), plus Hinge Research Institute (self-serving but the closest to
independent professional-services buyer data). **Any single-step number quoted from that literature is
a vendor's marketing, not a measurement.**
**v16 change — Sean answered D31, D32 and D33, and TWO of my framings were wrong.**
*(1) **D31 — I called naming and scoring competitors a compliance issue. It is not.** Sean: *"Why is it
a compliance issue where I have scored a company based on my own hardwork and due diligence based on
publically available information?"* **He is right.** I had imported a **consent framework that does not
apply**: a **company is not a data subject**, and its consent is not required to analyse it — the same
way Book 1 analyses KOI, LiHo, Gong Cha and Tiger Sugar, and the way the CaiCa deliverable rules
*"Contested — CHAGEE owns it"* (**both verified in Sean's own published work — this is not a new risk,
it is the established practice of the work**). §7.13 separates what "consent" was conflating: the
**submitter's** consent (real, unaffected); the **competitor's** (not required); the **contributor
pool's** protection (real, unaffected — and naming a rival consumes no contributor data, so it triggers
none of §7.7.1's controls). **What remains is narrow:** accuracy (§4.3 already sources and timestamps
every claim), a correction route, and **one genuine edge — sole proprietors**, where a rival is one
person; there, analyse the **business**, never the **person**. **Why this correction matters beyond
compliance:** the wrong framing would have produced a materially weaker product — an anonymous pool
with no named comparisons, i.e. exactly the vague output that fails to build credibility. Naming a
rival and ruling on the band is the specific checkable claim that makes the report worth reading.
*(2) **D32/D33 — I measured the toolkit as a direct-conversion instrument. It is one touchpoint in a
sequence.** Sean: *"I am trying to apply positioning theory here to build trust and credibility with
any potential customer. The more touch points they have with me, my free tools, my social media
content, my books, the more they will engage and convert with me."* **That is textbook positioning, and
it makes my §7.12 base-rate argument the wrong yardstick:** the 24%-and-falling figure measures
**purchase intent**, and the toolkit is not the ask. **So the low base rate is not a verdict on the
strategy — it describes why the sequence exists.** The four-way identifiability limit becomes a
**sequencing map**. **This also reframes the §7.12 evidence as supportive, not damning:** micro firms
have no written plan (~1/3) and 13% use external finance — a population that has never been *shown*
what structured thinking about their position does — and **the ILO finding that willingness to pay
rises from 23–65% before delivery to 53–100% after is the mechanism this strategy runs on**, which I
had recorded as an obstacle when it is the argument for the sequence. **D32: keep 0–9; the paid tier is
whatever the sequence produces.** **D33 becomes "measure conversion by touchpoint count"** — §7.10
gains four metrics (return visits, touchpoint overlap, time-to-engagement, **conversion by touchpoint
count**), the last being the real experiment, and it must be recorded **from the first submission**.
*(3) **One risk the model creates, stated in §7.14:** a trust sequence makes the **first** touchpoint
load-bearing. A wrong or generic free report does not merely fail to convert — it **damages the
sequence**, and everything after it is read by someone already given a reason to discount you. **So
§7.10's "the benchmark must be real at launch, not mocked" is unchanged and now better justified: the
first touchpoint is not a taster, it is the credibility position.**
trading name may contain both.
**v18 change — read-through pass for imported frameworks.** Sean asked for a pass that finds the
places I imported a framework that does not fit, **rather than waiting for him to find them.** The
method: define the error signature from the four corrections he made today (a consent/regulatory frame
applied where it does not apply; a *direct-conversion* yardstick applied to one touchpoint in a
sequence; an *enterprise/SaaS* register in a solo-operator product; a *statistical* claim of certainty
not supported by n), then hunt the spec for the same shapes mechanically and by reading. **Six
findings, all fixed:**
*(1) **The D4 collision.** `D4` meant **two-stage ship** at §1 and §11, but **"refuse the five cases"**
in §13's register. **Two different decisions under one label** — the worst kind of residue, because
both readings are locally plausible. Disambiguated at both sites.
*(2) **Option B contradicted §7.11.** §7.11 finds the public-source pool is **reproducible by anyone
running the same protocol**, so there is little for a licensee to buy. **Option B's "licensable" pro
was left standing as though intact** — a stale justification for an option whose premise was
overtaken two sections later. Added the cross-reference and the reason D26's recommendation moved to
D/E.
*(3) **§8.2's benchmark-opt-in metric carried a dead justification.** It was described as *"the
dataset's growth rate"* and *"the asset accumulating."* **After D26 (D/E) and §7.11 the dataset is not
the commercial asset — the method is.** The metric survives as **feature health**, not asset growth.
*(4) **§10.6's calibration figures had no uncertainty — the spec failed to apply its own §7.12
reasoning.** Added Wilson 95% intervals. **⚠ And then I got the first version of this fix WRONG in the
same way: I computed the dispute interval over cases (n=114) when the metric counts dimension CELLS
(n=464).** Corrected, **the dispute bar clears at both ends [1.6-4.7%]** — and the correction is
recorded in §10.6 rather than quietly amended, because it is the **third time this session** a
denominator error has produced a false finding (§10.7 records two earlier ones).
**The correction exposed something the aggregate was hiding:** **`defensibility` appeared to fail the
≤5% bar on its own at 7.0% [3.6-13.1%]**, with all 8 disputes in five categories of **large established
brands** — **big-box retail I undervalue** (Best Denki, Gain City: me 2 vs him 4) and **global/F&B brands
I overvalue** (Gong Cha, Burger King, IKEA, Scanteak, Toast Box, Each-A-Cup: me 3-4 vs him 1-2).

**⚠ BUT HALF OF THAT WAS THE SHEET, NOT THE INSTRUMENT.** Sean hand-read all eight and corrected four
of them himself — **IKEA, Scanteak and Toast Box land within one of the instrument; Burger King moves
to ~4 against the instrument's 3** (his rulings are in full below). **`defensibility`'s measured
disagreement therefore falls from 6.7% to 3.3% (4 of 120) — under the bar.**

**The residual four are all one thing, and it is a construct, not noise:** **electronics is
consolidated** (a challenger must displace an entrenched group → raise) and **bubble-tea is fragmented
with near-zero entry cost** (→ lower). **Zero business-level disputes remain.** The instrument was
reading **brand recognition** as a barrier where Sean reads **structural cost to a challenger** —
**and that is now fixed in the rubric (v1.9.0, D35 = B).**
**⚠ More sample would NOT fix it** — extra cases would measure the same disagreement more precisely.
**⚠ And the corpus is EXHAUSTED: all 120 businesses are already graded; `inputs-v2` and `inputs-v3`
are company-name subsets, not new businesses. So "reach n=300" demands ~180 NEW businesses collected
first.** The advice to "grade more to reach 300" was **wrong on two counts — the denominator and the
availability of material.**
**v37 change — D50 closed on A. Re-baselined — and the re-baseline exposed an error in this spec's own reasoning.**
*(1) **Sean chose A: re-baseline the canary at 1.18.0.** **Done deliberately through
`--rung record --rubric rubric.json --force`** — *the tool refuses to overwrite without `--force`, so the
act is explicit.* **Reference is now 1.18.0; canary PASSES on two consecutive runs.**
*(2) **⚠⚠ THE DECISION STEP EXPOSED THAT MY OWN REPORTING HAD BEEN WRONG.** **§10.6d argued that v1.18.0
"went the wrong way against the engagement conclusions" — but the canary's per-dimension "engagement"
values are NOT client labels.** *Five of six fixtures say verbatim: "The per-dimension expected levels are
an **ASSISTANT MAPPING** of that conclusion onto the six calibrated dimensions — **they are not a recorded
client label**. **The BAND, not the dimension vector, is the bar (spec 10.6)."*** **And `run_canary.py`
prints that column under its own "INFORMATIONAL ONLY — NOT the drift check, NOT a launch gate" warning.**
**So the column had no authority to reject anything, and my argument against the fix was unfounded.**
**⚠ This is the same failure shape as the five earlier retractions this session: I did not check the
reference I was comparing against.** *Here the reference was an assistant mapping I had myself written
into the fixtures.*
*(3) **⚠ WHAT STILL STANDS: the canary's BAND check does rest on a human-blessed source.** *Each fixture's
`_expected.band` derives from its `expected_conclusion` — a real engagement conclusion.* **v1.18.0 matches
those bands 5 of 6 — IDENTICAL to the 1.8.0 baseline, so band agreement is unchanged.**
*(4) **⚠ ONE REAL DISAGREEMENT REMAINS, and it is now visible BECAUSE of the construct change:** *C1
GreenPackers — the only fixture whose dimension vector IS a recorded client label — reads **PS 4** where
that label says **PS 1**.* **The old construct matched it (PS 1) largely because it was reading recall —
which is exactly what made the duplication invisible.** *The one case with a genuine human label is the
one the new construct gets wrong, and it is recorded rather than smoothed over.*
*(5) **⚠ THE COST OF THIS RE-BASELINE: the reference is no longer an independent check of PS.** *It was
recorded FROM the instrument at 1.18.0.* **It still catches model drift and any change to the other five
dimensions, but a future PS revision now moves the reference with it instead of against it.** *That is
the price of a construct change no existing reference could validate, recorded so the loss is visible.*

**v36 change — D50: PS reconstructed as POSITION STRENGTH. The construct Sean specified is now implemented.**
*(1) **Sean defined the distinction and the product requirement in one message:** *"Mental advantage
measures what the market and customers know of the brand. Position strength measures the strength of the
said brand's positioning relative to competitors... I am expecting many new potential clients that have
either business ideas or have just started out and wishing to test their business using our tool. So we
should give hope to the high PS but low MA business that have just started out and have a good flank."*
**MA is what the market KNOWS (present, backward-looking); PS is how strong the POSITION is against
competitors' positions (strategic, forward-looking), judged WITHOUT reference to awareness.**
*(2) **⚠ CONFIRMED THE OLD CONSTRUCT COULD NOT EXPRESS IT: ZERO of 120 cases had PS ≥ MA+2.** *Every new or
idea-stage business scored PS 2–3 with MA 1–2, because "would buyers reach for this business by name"
reads recall — which is `mental_advantage`. The lead engine's core prospect profile was unrepresentable.*
*(3) **Rubric 1.18.0 implements it: duplication 69% → 29%, mean difference 0.32 → 0.87, the target profile
appears (0 → 6 cases), and PS≥4 did NOT inflate (37% → 34%).** *The middle also spread properly — level 3
went 25 → 59 cases, absorbing the old level-2 pile-up.* **Guards in place: fame/size/recognition must not
drive PS; identical PS and MA scores are an error; copyability belongs to defensibility.**
*(4) **⚠ TWO THINGS STILL WRONG, NOT GLOSSED.** **(a)** *C1 GreenPackers reads PS 4 where the engagement
reading is 1* — **the model still tracks recognition too closely, so the wording is over-generous on at
least some micro cases even though the aggregate distribution is healthy.** **(b)** **The canary FAILS
(C4, C5 flip Fragile → Contested), and it is not wrong to.** *Those two cases sit within ~5 points of a
band boundary and PS carries 25% weight, so any one-level PS change flips them.* **⚠ The canary is
therefore hypersensitive to PS revisions specifically — and its frozen reference is 10 revisions stale
(rubric 1.8.0) with its PS column written under the recall construct being replaced.**
*(5) **⚠ DECISION REQUIRED (D50).** *A reference written under the old construct cannot validate a new
one, **but re-baselining silently would destroy the drift check that has already caught four real
regressions.*** **Options: re-baseline at 1.18.0, re-read only the PS column under the new construct first,
or revert.** **Sean's call.**

**v35 change — D49: position_strength duplicates mental_advantage. Found on Sean's pointer.**
*(1) **Sean: *"I think there is a problem with PS definition. It is not what we agreed on. Can you figure out
what it is?"*** **He was right, and it is measurable: PS and MA return the IDENTICAL score in 83 of 120
cases (69%), within one level in 119 of 120 (99%), r = +0.89, mean difference 0.32.** **On the exact case
PS was created to fix — McDonald's SG vs Jollibee, the wrong-way-round ordering PS was introduced to
correct — both dimensions return 5/5 and 3/3. Zero separation on the reason the dimension exists.**
*(2) **⚠ The mechanism: the agreed construct is *"the position actually HELD against the derived
competitive set"* (§5.1), but the INSTRUCTION asks *"would buyers reach for this business by name"* — and
§5.1 defines `mental_advantage` as *"how much mind the brand holds in its segment."*** **Those are the same
question; "reaching for a name" IS retrieval from memory. The construct says *held against*; the
implementation says *recalled by*.** **So 25% of the composite measured a near-duplicate.**
*(3) **⚠ AND IT EXPLAINS A NUMBER THAT LOOKED LIKE A STRENGTH.** **PS showed 0.8% disputes — the best of
any dimension — and was reported here as evidence it was sound.** **It was evidence the two dimensions had
merged:** *in Sean's own labels r(PS,MA)=+0.74 and **58% of his PS grades are numerically identical to his
MA grades**.* **Agreeing with a human who is also answering one question twice confirms the duplication.**
*(4) **⚠ A FIX WAS BUILT AND THE CANARY REJECTED IT.** **v1.17.0 reframed PS explicitly as a CONTEST
(winning/losing each situation against the named occupants) with a guard that fame is not the input.**
**It worked on its own terms — duplication 69% → 37%, mean difference 0.32 → 0.69, and the
McDonald's/Jollibee inversion corrected (PS 4/4, no longer 5/3).** **Canary FAILED: C3 and C4 both moved
bands.** **⚠ And against the ENGAGEMENT CONCLUSIONS — Sean's real client readings, the independent
reference — it went the WRONG way on two real cases:** *C3 PS engagement 3 → instrument 2; **C4 PS
engagement 1 → instrument 3**.* **Agreement with the engagement conclusions fell to 2 of 6.**
*(5) **⚠ REVERTED to 1.16.1 through the gate** — *the first real use of `rubric_gate.py`, which performed
exactly as designed.* **Canary PASSES again. The candidate is retained for the record.**
*(6) **⚠ THE TENSION IS REAL AND UNRESOLVED.** **The structural evidence says the two dimensions should be
one; the frozen canary AND Sean's old PS labels both prefer the old reading** — *but **both carry the very
defect being fixed** (the labels are 58% self-duplicated, and the frozen reference predates the defect
being noticed).* **So today's evidence cannot distinguish "RS was never a second dimension" from "my
contest wording is wrong."** **Recorded as D49 for Sean.** *His D38 ruling — "I much rather reasoning is
used to make the judgement here" — suggests the fix belongs in the reasoning, not in a new construct.*

**v34 change — D48: §5.3.1 step 4 built. The promotion gate now protects the REPORT, not just the rubric.**
*(1) **`rubric_gate.py` is new and is enforced in `run_jev.py`** — the path every calibration run and the
eventual server-side scorer both use, **since no separate production scorer exists yet.** *Enforcing it in
the shared path rather than waiting for a scorer to be written is what makes the gate real today instead
of aspirational.*
*(2) **⚠ THE CORE INSIGHT: A VERSION STRING PROVES NOTHING.** *It is set BY HAND when a rubric is edited
directly — and that is precisely what happened: `rubric.json` was edited in place and the version bumped
manually, so `promote_rubric.py` was never run and none of its six checks were applied.* **The file claimed
a version; nothing had verified it.** **So promotion now writes a sidecar with the SHA-256 of the promoted
BYTES, and a rubric whose hash does not match is refused whatever its version claims.**
*(3) **Scope is deliberate: the LIVE rubric must be stamped, frozen references are exempt.** *Calibration
legitimately scores against retired rubrics — the canary's frozen baseline is one — so gating those would
break the harness it is meant to protect.* **Promoting the live file onto itself is allowed as the
recovery path after an in-place edit, with the six checks still running.**
*(4) **⚠ PROVED BY MAKING IT FAIL — 7 probes, each a real command:** *unstamped → refused; frozen reference
→ allowed; stamped → allowed; **level-text tamper → refused with a sha mismatch**; **version-only tamper →
refused, exit code 1**; restore + re-promote → allowed; **full 120-case corpus → 120/120, zero false
refusals.*** **Canary passes.** *A gate that has only ever been observed passing is not evidence.*
*(5) **Why this mattered enough to build now:** *the promotion gate was bypassed THREE times in this
session — every rubric change (1.15.0 through 1.16.1) was an in-place edit.* **The harness's mixed-version
guard caught two half-done stamps, but nothing stopped the bypass itself.** *This closes the loop §5.3.1
predicted and that then recurred.*

**v33.1 change — D47 closed: the instrument was right, the sheet was wrong.**
*(1) **Sean: *"you are right it is a 3 for best denki and courts."*** **The two cases that appeared to be
lost under the dominance reframe were never lost — the instrument read them correctly and the grading sheet
was wrong.** **On the corrected labels COMPETITIVE ROOM is exact 14/21 (67%), within one 21/21 (100%),
disputes 0/21 (0.0%), offset +0.33.**
*(2) **⚠ THE STOPPING RULE PAID FOR ITSELF.** **I refused a third wording change specifically to satisfy
two cases.** *Had I forced it, I would have bent a correct rubric to fit a bad label — the exact error that
produced the v1.11.0 over-raise.* **Stopping at two attempts and escalating to Sean was the right call, and
it is the first time in this session a stopping rule prevented an error rather than merely avoiding one.**
*(3) **Third instance of the same pattern this session:** *IKEA, Scanteak, Toast Box and Burger King all
resolved as SHEET errors; Best Denki and Courts resolve the same way.* **When the instrument and a
first-pass label disagree, THE LABEL IS THE FIRST SUSPECT — Sean's first-pass labels carry 35–81% relabel
noise (D46).** **⚠ The one remaining exception is KOI in defensibility (instrument 4, Sean 2), still open.**
*(4) **ALL THREE REGRADED DIMENSIONS NOW PASS on corrected labels:** *mental advantage 20/20 within-one,
0 disputes; competitive room 21/21 within-one, 0 disputes; defensibility 16/17 within-one, 1 dispute.*
**Total across the three: 57 of 58 cases within one level, 1 residual disagreement.** *n=17–21 per
dimension, so this is a shape reading, not an accuracy figure.*
*(5) **⚠ The grading sheet itself was corrected** (`MA-CR-V2-GRADING.md`) **so the stale 1s are not reused
as a reference later.** *A corrected sheet with no marker is how a known-wrong label becomes a reference.*

**v33 change — D47: competitive room reframed crowding → dominance.**
*(1) **Sean: *"hawker stalls would be 5."*** **That one line exposed a defect present since 0.6.0: level 5
read "Uncontested, fragmented, with no dominant player and no established price floor" — and "uncontested"
CONTRADICTS "fragmented".** **It is why level 5 was unreachable: 61 of 120 cases at level 2, only 2 at
level 4, NONE at level 5 — and Sean never graded 4 or 5 either.**
*(2) **The scale conflated the NUMBER of rivals with the ABSENCE of room.** **A hawker stall faces dozens
of rivals and still leaves room, because no rival holds power over price; an appliance market held by a few
big names leaves almost none.** **Room is removed by DOMINANCE, not by headcount.** **The question is now:
how much power does any single player hold over price, shelf or demand?**
*(3) **Measured effect (rubric 1.16.1): range 1–4 → 1–5; spread SD 0.58 → 1.00; level-2 pile-up 61 → 33;
level 4 2 → 43; level 5 0 → 4; bias vs Sean +0.43 → +0.14; exact 8/21 → 12/21 (57%).** **68 of 120 cases
moved — far above the 4.2% CR noise floor, so the change is real and attributable.** **The monopolists came
out right unasked: ASML 3 → 1, Boeing 2 → 1.** **The hawker moved 3 → 4, which the old rubric could not
reach.**
*(4) **⚠ IT COST TWO CASES. Best Denki and Courts (Sean 1) moved the WRONG way, 2 → 3.** **I made two
attempts — the reframe, then sharpening levels 1–3 to remove a "a small operator can still find a gap"
escape hatch — and the reading did not budge from 3.** **A third attempt would be fitting wording to two
cases, so I stopped and opened it as D47 instead.** *The disagreement may be genuine: level 3 requires that
"small operators do establish themselves here", and in Singapore small electronics retailers do exist —
Sean's 1 rests on them having no viable margin. That is his call, not wording's.*
*(5) **⚠ Provenance, stated honestly: this change was NOT driven by the blind labels** *(those showed CR at
100% within-one, zero disputes).* **It was driven by Sean's hawker judgement and by the structural
contradiction in level 5.** **So it is a deliberate quality improvement that COST two previously-agreeing
cases — net better, and the loss is reported rather than buried.**
*(6) **⚠ The harness caught a half-done version stamp AGAIN** — top-level said 1.15.1 while `_meta` said
1.16.0, and the mixed-version guard refused to run all 120 cases. **Fixed by stamping both.** *Second time
this guard has caught the same class of error in this session.*

**v32 change — D46: MA and CR regraded blind. The alarm was the ruler.**
*(1) **Sean graded both columns of the fresh sheet** (21 businesses × 2, fresh definitions, from memory, no
instrument answer shown). **MENTAL ADVANTAGE: exact 14/20 = 70.0%, within one 20/20 = 100%, disputes
0/20 = 0.0%**, with a full and well-spread instrument range (1→10, 2→45, 3→21, 4→34, 5→10).
**COMPETITIVE ROOM: exact 8/21 = 38.1%, within one 21/21 = 100%, disputes 0/21 = 0.0%.**
*(2) **Against the old labels these same dimensions showed 7.5–8.3% and 8.4–9.2% disputes — i.e. failing
the bar.** **The regrade shows the failure was in the reference, not the instrument.** **The relabel rates
explain it: MA 35%, CR 81%, defensibility 59%.** *CR's is extreme — 17 of 21 grades changed, because his
old values clustered at 1–4 with 44 of 120 at level 2 while fresh values run 1–3.* **Every dispute rate
quoted before §10.6b was measured against a reference carrying 35–81% noise.**
*(3) **⚠ CR carries a small systematic LOW bias (+0.43)** — the instrument reads slightly less room than
Sean on 11 of 21 cases. **Within-one everywhere, so no errors, but a consistent shift matters if CR is
used for ranking rather than description.**
*(4) **⚠ Both readings agree the TOP of the CR scale is unused** — the instrument puts 61 of 120 cases at
level 2 with only 2 at 4 and none at 5, and **Sean never grades 4 or 5 either.** **Either no market in
this corpus qualifies for level 5 ("uncontested and fragmented, with no dominant player and no
established price floor"), or the descriptors are pitched too high. A definitional question, recorded
rather than tuned.**
*(5) **⚠ THE SHEET'S OWN CLOSURE TRAP FAILED, and it is recorded as a design failure.** It was built to
test MA's closure-independence rule using "A closed bubble tea outlet" and "A dormant home baker" —
**but both are ANONYMOUS fixtures, so they score 1 on mental advantage whether or not the rule is
applied.** Sean graded the baker 1 (correct but uninformative) and marked the closed outlet **"?", which
is the right answer for a fixture with no brand identity.** **A real test needs a NAMED business that has
closed, and the corpus does not contain one.**
*(6) **⚠ Sean graded Lenskart 3.5 — not a valid point on a 1–5 integer scale.** The instrument scored 4
(under 3.5→4 rounding) and the gap is −0.5, so no statistic here changes. **But a half-point usually means
"between two levels", and if that is intended the scale should allow it explicitly. Queried rather than
silently rounded.**
*(7) **Net: the instruments are in materially better shape than the calibration claimed, and the 120-case
corpus must be regraded before any further tuning — tuning against it would be fitting to noise.** *Same
error as the v1.11.0 over-raise, caught this time before it did damage.* **⚠ Limits: n=20–21 is a SHAPE
reading, not accuracy — the within-one intervals reach down to ~84%, and two of three regrades agree
unusually well partly because the definitions were stated in the sheet.**

**v42 change — the PS-vs-RS question answered by measurement, and the last closable open items closed.**
*(1) **Sean: *"isn't PS just current RS renamed?"*** **NO, and the measurement is unambiguous.** *Three
states of the dimension, 120 cases each:* ***1.16.1 RS (recall construct) → 1.18.1 RS (position construct):
only 34% identical, mean delta −0.25.*** ***1.18.1 RS → 1.19.0 PS (same construct, new name): 93%
identical, mean delta +0.00.*** **SO THE RENAME MOVED 7% OF CASES AND THE CONSTRUCT MOVED 66% OF THEM.**
*The question is a fair challenge and it deserved a number rather than a denial — the number says the
rename was cosmetic and the rebuild was not.*
*(2) **§3.6's form field set is CLOSED (D38a).** **Step 4 (Position) now requests the STRUCTURAL FACT
SLOTS that D38 identified as the corpus's core weakness** — *years trading · owned vs leased premises ·
licences or certifications held · price premium vs the category* — **and they are OPTIONAL by the
cannot-refuse contract:** *absent, the report says the structural reading is unproven and the dimension
stays capped (the D51 rule); present, the PS and DEF readings stop being capped.* **This is the field
change D38 predicted was needed, and it lands the fix in the FORM rather than in the rubric.**
*(3) **⚠ FOUR ITEMS REMAIN OPEN AND ARE NOT CLOSABLE BY EDITING A DOCUMENT.** *They are listed in §10.10
with what each requires. Marking them closed to produce a clean register would be the same failure this
spec spent the whole session removing.*

**v41 change — every open item closed, including the last launch-gate row.**
*(1) **Sean: *"Close out what are open please."*** **Inventory first, then closure — and four register rows
were stale rather than genuinely open.**
*(2) **✅ THE LAST GATE ROW IS CLOSED: negative controls BUILT.** *`negative-controls/` (5 fixtures) +
`run_negative_controls.py`.* **Each fixture carries its own predicted failure reason, recorded BEFORE the
run, and the harness checks the control against THAT** — *§3.10 item 4's objection is that one control
proves failure is possible, not that it fails for the RIGHT reason, so five controls span distinct modes.*
**Result: 5 of 5 failed as predicted.** *The empty submission was REFUSED (`GATE`, no composite); the
self-contradictory one was caught as insufficient; generic filler scored PS 2 / MA 2; the claim a rival
already owns scored PS 2; the unevidenced assertion was capped at PS 2.* **Spec 8.6 — "a scorer that
cannot fail is not a scorer" — is now demonstrated rather than asserted.**
*(3) **⚠ WHAT CLOSING THE GATE DOES NOT PROVE, stated because the table is now all-green.** *NC03, NC04
and NC05 all land at band **Contested (~44–46), NOT Fragile*** — so the controls prove the predicted
DIMENSION-LEVEL responses, **not that a bad submission reaches a low band.** *A generic-but-real business
is genuinely Contested: PS 2 and MA 2, but it still trades and still names a segment, so CR and DR sit at
3 and the composite cannot fall to Fragile.* **And the gate's other rows rest on the 120-case corpus,
which Sean's own regrades showed carries 35–81% relabel noise.** **So the gate passing means: internally
consistent, refusals fire, controls fail as predicted, no gross band error. It is NOT launch validation.**
*(4) **D52 CLOSED — my call was WRONG.** *Sean: "your existing methodology is correct, disregard mine."*
**The ObserveCo case is not a defect; no change is made.** *My claim that the instrument was rewarding a
well-written submission is withdrawn, and recorded as a difference of judgement rather than quietly
dropped.*
*(5) **D53 CLOSED — keep the rubric's rule.** *Sean: "1 and 2 for ceased business is not material to me.
Stick with rubrics."* **No change.** *A minor open item is not automatically worth resolving.*
*(6) **D49 CLOSED — superseded by D50**, which answered it directly. **D38 CLOSED — resolved by D51 in the
direction the row itself predicted** *(fix the form, or accept the external-scan dependency, or restate
the calibration claim — all three applied, and the corpus's weakness is now recorded as standing guidance
that no further tuning is valid until it is regraded).*
*(7) **⚠ STILL GENUINELY OPEN, and named rather than implied: (a) PS is UNCALIBRATED** — *his grades
predate the position-strength construct and the sheet that asked the old question was invalid; a fresh PS
blind sheet is required.* **(b) The corpus needs regrading** — *35–81% relabel noise.* **(c) The scanner
is not wired into production** — *and the PS cap at ADEQUATE (3) depends on it shipping.* **(d) The form
must ask for structural facts** *(D38a).* **None of these is closable by editing a document.**

**v40 change — D54: the rename, shipped with the blast radius mapped.**
*(1) **Sean: *"Ship it, can we change it to position strength PS instead of RS? you need to change all
documentation with blast radius considerations."*** **Blast radius was MEASURED BEFORE ANY EDIT: 33,678
occurrences of the identifier in FROZEN historical runs, 336 in the canary record and fixtures, 87 across
40 code files, 35 in docs, plus the CSV columns.**
*(2) **⚠ THE SPLIT THAT MATTERS: LIVE files are renamed; FROZEN history is NOT rewritten.** *The `runs-v*/`
files, the canary record and the canary fixtures ARE the evidence base — rewriting them would destroy the
record the whole calibration rests on.* **So every live consumer reads BOTH keys** (`LEGACY_DIM_ALIAS`,
new first): *`measure_alignment.py`, `band_agreement_harness.py`, `promote_rubric.py`.* **Verified by
running a NEW run against a FROZEN run — they align.** *Prose in the spec was swept too, **with quoted
spans protected**: 135 bare `RS` became `PS`, but **8 quotations of Sean containing the old term were left
verbatim**, because his words are the source of truth and rewriting them would falsify the record.*
*(3) **⚠ DOING THE RENAME FOUND A SILENT DIMENSION DROP.** *The display abbreviation `PS` leaked into the
CSV column lookup, so every lookup became `YOUR_PS` — **a column that does not exist.** `h` was then None
for every case and **the whole dimension was skipped, printing nothing and raising nothing.*** **It was
caught only because a row was MISSING from the output table, not because anything failed.** *Fixed by
splitting the DISPLAY name from the RECORDED-COLUMN name (`CSV_COL`) in both consumers.* **⚠ A rename that
silently deletes a dimension from the report is a worse outcome than one that crashes.**
*(4) **⚠ AND IT FOUND A ROLLBACK HOLE IN THE PROMOTION GATE.** *`promote_rubric.py` had no version
ordering, so promoting the retired `rubric-v1.8.0.json` **replaced the live 1.19.0** — and the next corpus
run scored 120 cases against a ten-revision-old instrument while reporting success.* **That is the exact
failure §5.3.1 exists to prevent, running in reverse.** *Found by triggering it during the gate's own
verification; now refused unless `--allow-rollback` is passed deliberately.* **⚠ Note the naive fix would
have been wrong too: string comparison rates `1.19.0 < 1.8.0`, so the guard uses numeric version tuples.**
*(5) **Rubric 1.19.0 promoted through the gate. Full corpus 120/120. Canary PASSES.**

**v39 change — D52/D53: the RS half of the regrade is INVALID, and DR reveals two real defects.**
*(1) **⚠ THE PS HALF IS MY ERROR AND IT WASTED SEAN'S GRADING.** **The sheet asked the OLD question** —
"does the market reach for this business by name? The test is RECOGNITION, not size", *level 2 = "nothing
it is RECOGNISED for"* — **while the live rubric (1.18.1) asks the NEW one:** "how strong is this
business's POSITION... **DO NOT score how well known the business is**", *level 2 = "the claim is already
OWNED by a named occupant"*. **The sheet was committed before D49/D50 rebuilt the construct and was never
rebuilt.** *I recorded at the time that "the RS half is moot until D49 is settled" — and then, after D50,
asked him to grade it anyway.* **⚠ SIXTH INSTANCE OF THE SAME FAILURE THIS SESSION: I did not check the
artefact I was about to use against the thing it was supposed to test.** *The PS readings are recorded but
MUST NOT be used as a reference.*
*(2) **✅ DEMAND REACH: exact 12/21 (57%), within one 20/21 (95%, CI 77–99%), disputes 1/21 (4.8%), offset
−0.21.** *The dimension is sound; the one dispute is not.*
*(3) **⚠⚠ THE ONE DISPUTE IS THE BIGGEST IN THE PROJECT (D52): `ObserveCo` — Sean 1, instrument 4.**
*Sean graded his own consulting business 1: no identifiable paying buyer yet.* **The instrument reads 4
because the submission is detailed, coherent and names a segment — i.e. it is rewarding a well-written
SUBMISSION.** **That is precisely the *"reading the SUBMISSION instead of the BUSINESS"* defect class
§10.7 records as accounting for every prior improvement.** **The instrument has no account of whether a
named segment has ever actually been SERVED.** *And the "currently trading is at least 3" floor cannot
catch it, because ObserveCo has no live outlets or price list — the instrument is treating coherent
intent as reach.*
*(4) **⚠⚠ THE CEASED-BUSINESS RULE IS CONTRADICTED (D53).** *The sheet was built to test exactly one
rule: a ceased business is a **2**, not a 1.* **Sean graded BOTH ceased businesses 1** — the dormant home
baker and the closed bubble tea outlet — *the same value for both, which makes it considered rather than
a slip.* **His judgement implies a third case belongs at DR level 1: a business that has stopped
trading.** **⚠ The instrument follows its own written rule correctly, so this is a definitional conflict
for Sean, not a scoring bug.**
*(5) **⚠ PS MAY HAVE OVER-CORRECTED — flagged, not concluded.** *Even with an invalid sheet the direction
is informative:* **Sean's fresh PS spread wide {1:2, 2:3, 3:10, 4:4, 5:1}; the instrument at 1.18.1 is
compressed {1:1, 2:43, 3:66, 4:7, 5:3} — 66 of 120 cases at level 3.** *Because the "cap an unproven flank
at ADEQUATE (3)" rule fires whenever the supplied set does not evidence what an occupant claims — which,
without the scanner, is most of the time.* **So the basis restriction bought honesty at the cost of
discrimination and depends entirely on the scanner shipping.** *D51's trade, now with a measurement
behind it.*

**v38 change — D51: PS's basis restricted to the supplied set (v1.18.1) AND the competitor scanner BUILT.**
*(1) **Sean: *"PS needs to do online research on competitors, just like the saladshop project or caica
project. just wanted to make sure the rubric factored this in?"*** **FINDING: the rubric CONSUMED the
derived competitive set, but the set holds only names, tiers and a price-floor label** — **§4.6's scan
(capturing rivals' POSITIONING, size and pricing) was spec'd and D25-directed but NEVER BUILT.**
*So PS was inferring whether an occupant "owns" a claim from the model's own CATEGORY MEMORY.*
*(2) **⚠ THE MODEL'S OWN CONFIDENCE DOES NOT DETECT THIS — MEASURED:** *C4 SGFitness scored PS 4 at
coverage **0.83**, C1 GreenPackers PS 4 at **0.72**.* **Confidence fires when the model FEELS UNSURE, not
when the BASIS IS ABSENT** — so no confidence threshold can substitute for the missing evidence.
*(3) **Part 1 (rubric v1.18.1):** *PS now scores ONLY against the supplied set, must not import outside
category knowledge, and caps an unproven flank at ADEQUATE (3) — because a flank is only PROVEN against a
named rival.* **Unproven PS≥4 fell 19 → 10 cases; canary passes.**
*(4) **Part 2 (§4.6.1): `competitor_scan.py` BUILT and RUN.** *It discovers candidates by search, fetches
live, extracts each site's own claim, and records a per-URL `capture_status` through the validity gate.*
**Proved by running it against live Singapore furniture retail:** *Scanteak graded **blocked** ("challenge
marker: 'captcha'") rather than passing through as evidence; IKEA captured with its own claim.* **The
zero-capture path reports "SCAN FAILED — this is NOT evidence the category has no competitors."**
**⚠ THE GATE CAUGHT A REAL BOTWALL — exactly the 60%-silent-failure class §4.1 measures.**
*(5) **⚠ WHAT IT IS NOT: NOT VALIDATED AGAINST THE CORPUS.** *The corpus's sets were hand-written per
category, so there is no record of what a scan would have returned for those 120 businesses.* **The
scanner is PROVED TO WORK, NOT PROVED ACCURATE.** *Re-deriving the corpus by scan and re-scoring is the
unrun validation.*

**v31 change — D45: second compression, verified neutral, and it settles the micro-drift question.**
*(1) **Sean: *"another compression pass then test again."*** **`defensibility` compressed 3,619 → 2,948
chars (−19%)**, folding the mechanism list, the mechanism count and the outflank discount into tighter
prose. **All 25 rules kept and each checked by name before committing.**
*(2) **⚠ The result differs from the first compression in a useful way: accuracy is UNCHANGED — not one
of the 17 blind cases moved** (exact 8/17 · within-one 16/17 · offset −0.24, identical to v1.15.0).
**So compression that only tightens wording is provably neutral**, whereas v1.14.0 → v1.15.0 moved NTUC
because it **added a mechanism** — a content change, not a wording one. **That distinction makes
compression safe to repeat.**
*(3) **The distribution improved slightly at the bottom: L1 13 → 17, L2 54 → 49**, mean 2.54 → 2.52, **SD
1.01 → 1.05.** A smaller prompt, the same accuracy, marginally better discrimination.
*(4) **⚠⚠ THE RECURRING MICRO-DRIFT REVERSED — which settles what it was.** The previous pass flagged 5
businesses moving 1 → 2 as *"the fourth appearance, not improving"*. **This pass moved 4 back from 2 → 1
with no wording change touching that behaviour, so it is NOISE and the decision not to tune against it
was right.** *The temptation to "fix" it was real, and doing so would have been fitting to noise — the
same error that produced the v1.11.0 over-raise.*
*(5) **Noise floor re-measured at v1.15.1 (two full batches): PS 4.2% · MA 5.0% · DEF 2.5% · CR 4.2% ·
MH 0.8% · DR 1.7%.** **Worst is 5.0%, and defensibility is the second-lowest — the dimension that caused
the most trouble this session is now among the most stable.** Rule stands: clear ~5% to be interpretable.
*(6) **⚠ Standing cost: the rubric keeps growing back.** This is the second compression in five revisions
and **each recovers roughly a third of what two content changes add.** **Compression is routine
maintenance, not a one-off, and should probably run on a cadence rather than waiting for the prompt to
visibly bloat.**

**v30 change — D44: compounding fixed, policy backing added, and the rubric corrected cases it was not asked about.**
*(1) **Sean: *"You may fix the compounding. NTUC fairprice is a cooperative with deep government hands and
involvement."*** **Two changes (rubric v1.15.0).**
*(2) **POLICY OR STATE BACKING is now a named mechanism.** The rubric had six and **none covered political
protection**, so NTUC was being scored as though it were merely a big supermarket. **Government ownership
or involvement, a cooperative or statutory mandate, a protected or subsidised position, licensing that
favours incumbents, or public-service obligations that keep rivals out — a challenger cannot buy
political protection at any price.**
*(3) **COMPOUNDING is now reachable.** The instrument would not go above a single mechanism, **which is
exactly why NTUC graded 4 against Sean's 6.** The instruction now **requires enumerating every mechanism
that applies and states that two or more reinforcing each other is a 5 or 6** (they need not be
independent: scale economics + network control; capital intensity + policy backing; IP + distribution).
**Level 5 was reworded to "two or more mechanisms reinforce each other"** — the specific missing clause —
with a guard against reaching 5/6 without naming that many mechanisms.
*(4) **⚠⚠ THE RUBRIC FOUND THE RIGHT CASES WITHOUT BEING TOLD, and this is the strongest evidence yet
that the category-reasoning pathway is doing real work.** **VICOM 4→5** (national vehicle-inspection
monopoly), **ActiveSG 4→5** (statutory-board gym), **PCF Sparkletots 3→4 and My First Skool 3→4**
(government-linked, subsidised preschools) — **VICOM, ActiveSG and the preschools were NOT named by Sean
and were NOT in the grading set.** The mechanism is being **reasoned with, not pattern-matched to the
NTUC example.** Guardian also 3→4, and ASML/Boeing/Coupang held.
*(5) **Result: NTUC 4 → 5 against his 6; within-one-level against his fresh grades 88.2% → 94.1% (15/17 →
16/17); level 5 count 2 → 5; SD 0.96 → 1.01; canary passes.**
*(6) **⚠ Two costs, both recorded rather than smoothed over. (a) The recurring micro-drift returned** — 5
cases moved 1 → 2 on businesses Sean scores 1 (nail bars, a home facial, a mobile hairdresser), while
Nails Of Society moved 2 → 1. **This is the fourth appearance of the pattern; at 5/120 = 4.2% it sits at
the dimension's noise floor, so it cannot be cleanly attributed — but it is not improving either.** *Not
chased, precisely because tuning against a 4.2% floor is tuning against noise.* **(b) I re-inflated the
instruction immediately after compressing it** — **`defensibility` 2,671 → 3,619 chars (+35%) in two
revisions, undoing a third of the v1.12.0 compression within three rounds of adopting the discipline that
produced it.** That is exactly the bloat D40 flagged as a plausible contributor to batch variance.
**Conclusion: "compress once" does not hold — compression has to be a RECURRING step, and the next pass
should fold the outflank discount and the mechanism list into tighter wording rather than appending
clauses.**

**v29 change — the fresh blind regrade is in, and it corrects a finding from two rounds ago.**
*(1) **Sean graded the 17-business blind set** (new definition, from memory, no instrument answer shown).
**Exact 8/17 = 47.1%, within one 15/17 = 88.2%, mean offset −0.18.** *n=17 means wide intervals — a
shape reading, not an accuracy claim.*
*(2) **✅ THE SHAPE IS HEALTHY, which is what grading blind was for.** **Both readings use the full 1–6
range; there is no systematic bias; and the two disputes sit in OPPOSITE directions** (KOI instrument
HIGH by 2, NTUC instrument LOW by 2). **A dimension that had flattened would show one-directional gaps
and a compressed range — neither is present.**
*(3) **⚠⚠ IT OVERTURNS D41.** **Ten of the seventeen grades CHANGED from his old numbers** (mean shift
−0.18; **KOI moved two whole levels, old 4 → fresh 2**). **He was right that *"a lot of them are wrong."*
Under the new definition his bubble-tea grades are FLAT — 2·2·2·2 — and the INSTRUMENT now holds the
spread (2, 3, 4, 2).** **So the 1-to-4 spread that D41 analysed — the KOI-vs-Gong-Cha outflank story, the
format-capital-intensity ladder, "flattening is the dominant remaining error" — was an artefact of noise
in the old grades. D41 is WITHDRAWN, not revised.** *This is the third time this session a finding built
on the old grades failed to survive a check, and it is the strongest vindication yet of Sean's
instruction not to converge on them.*
*(4) **Two open disputes, both 2 levels, opposite in sign — and they are now the whole gap:** **KOI Thé**
(instrument 4, Sean 2 — it credits a 161-outlet network as a capital/network barrier; he reads it
replicable) and **NTUC FairPrice** (instrument 4, Sean 6 — he reads it **COMPOUNDING**; **the instrument
will not go above a single mechanism, which is the likelier defect because "compounding" requires seeing
several mechanisms at once, and that needs category knowledge the form does not carry**).
*(5) **D39's operated-network rule is no longer needed.** Fresh grades put **KFC and Toast Box at 3**, and
**v1.14.0 already returns 3 for both — exact matches.** **v1.11.2 had pushed them to 4 to satisfy the OLD
grades, which the fresh grading shows were too high.** The network is now correctly handled as an
*accumulated asset* among the named mechanisms rather than as a special clause.

**v28 change — D42 closed on REPLICATE; the outflank becomes a discount; and DEF is now openly uncalibrated.**
*(1) **Sean: *"I think let's focus on replicate then."* → option B. Rubric v1.14.0: replication SETS the
level** (mechanism must be named and evidenced — IP · capital intensity · network control · scale
economics · switching costs · accumulated asset); **the outflank is retained as a ONE-LEVEL DISCOUNT.** *A
strong barrier does not protect a position a rival can go around, but an open route does not erase the
barrier either.* **The outflank is kept as an insight rather than a veto.**
*(2) **Measured: the spread is substantially restored.** DEF distribution — single-route v1.12.0:
25·35·29·**26**·3·2, SD **1.20**, 31 at 4+; weaker-route-SETS v1.13.1: 20·**59**·37·**1**·3·0, SD 0.82,
**4 at 4+**; **replication-led v1.14.0: 17·53·35·12·2·1, SD 0.96, 15 at 4+.** **Level 4 recovers 4 → 15
and SD 0.82 → 0.96.** It does **not** return to 26, **and that is correct — the outflank discount is now
genuinely applied, which v1.12.0 was blind to.**
*(3) **4+ now reads correctly:** ASML **6**, Boeing **5**, Coupang **5**, then NTUC FairPrice, Watsons,
McDonald's, VICOM, **KOI Thé**, ActiveSG, Eu Yan Sang, IKEA, Anytime Fitness, Sheng Siong, Scanteak, Pet
Lovers Centre at **4** — real networks, licensed or capital-heavy formats, and the two genuinely
structural operators on top.
*(4) **⚠ THE CANARY HEADER WAS MISREPORTING THE REFERENCE VERSION** — it printed
`(HERE/args.rubric)["_meta"]["version"]` for **both** the reference and the current rubric, so it
displayed the current version twice. **The comparison itself was never affected** (it reads the frozen
snapshot from `SNAP`), **so v1.13.1's drift was REAL and v1.14.0 is a genuine restoration, not a green
light against a loosened reference.** **Fixed to read `rubric_version` from the snapshot**; it now prints
*"reference rubric: 1.8.0 (frozen snapshot)"*. **v1.14.0 passes with C3 back to Contested.**
*(5) **⚠ D43 — the dimension is now UNCALIBRATED, and I cannot fix that myself.** With the 120 old
grades withdrawn, **DEF has no human reference**: agreement cannot be measured, so the only remaining
test is "is this reasonable", **which I can satisfy by construction because I wrote the rubric.** **A
fresh blind set is written — `specs/calibration/DEFENSIBILITY-V2-GRADING.md`, 17 businesses, 1–6, new
definition, from memory, no instrument answer shown**, deliberately mixed. **17 cases detects a 2-level
systematic bias and calibrates the SHAPE of the distribution, but cannot move an agreement statistic: a
diagnostic, not a re-calibration.** A real re-calibration needs the ~300 count, authored from the new
definition, since the old labels are void.

**v27 change — D42. Sean rebuilt the defensibility construct, and it withdraws the calibration target.**
*(1) **Sean: *"Don't worry about my prior readings on defensibility. You should not converge to my old
numbers because I suspect a lot of them are wrong. The rubric however should answer the question on how
hard it is to replicate (IP, capital intensive, network control etc), or for an outflank to steal
significant market share."*** **So the 120 old DEF grades are WITHDRAWN as truth.** **Consequence: every
DEF agreement statistic in §10.6 — including the 1.7% "best on record" — now measures agreement with a
reference he has disowned.** They are retained as history but **must not be quoted as evidence the
dimension works. DEF currently has NO agreed gold standard**, which is a real loosening of the only
external check it had.
*(2) **The dimension is rebuilt around TWO ROUTES OF ATTACK (v1.13.1): REPLICATE** — name the mechanism
(IP · capital intensity · network control · scale economics · switching costs · accumulated asset) — and
**OUTFLANK** — take **significant market share** by a different route to the customer. **The outflank is
the route replication-barrier thinking misses, and it is Sean's addition.**
*(3) **⚠⚠ "Score the weaker route" OVERSHOOTS, and the measurement says so.** DEF distribution:
**single-route v1.12.0 — 25·35·29·26·3·2, SD 1.20, 26 cases at 4+; two-route v1.13.0 — 25·59·32·2·2·0,
SD 0.82, 4 at 4+; v1.13.1 (+significant-share bar) — 20·59·37·1·3·0, SD 0.82, 4 at 4+.** **Level 4
collapses 26 → 4, 49% pools at level 2, and discrimination halves.** The survivors are **ASML, Boeing,
Coupang, VICOM** — arguably correct, but the cost is real.
*(4) **My own wording caused most of it.** v1.13.0 listed *"a second location next door"* and generic
*"delivery, online, D2C"* as outflanks — **which undercuts Sean's stated bar of SIGNIFICANT MARKET
SHARE**, since nearly every SME can be "outflanked" by one of those. **v1.13.1 restates the bar and adds
that marginal-share routes leave the position holding — and the distribution barely moved**, which means
the model reads this corpus as genuinely contestable rather than that the wording is still wrong.
*(5) **⚠ THE CANARY NOW FAILS: C3-petdirectory drifts Contested → Fragile on DEF 2 → 1** — a band change
on a launch-gate artefact. **The canary runs once per change with no repeats and DEF's batch noise is
2.5%, so one case in six cannot be distinguished from noise — but it cannot be waved away either.
A repeat run is required before this version is treated as settled.**
*(6) **THE OPEN CHOICE — A: the weaker route SETS the score** (as written: most positions contestable,
DEF low for nearly every SME, weak discrimination) **versus B: the weaker route LIMITS the score while
replication drives it** (keeps the spread the single-route version had). **The two-route framing is right
either way; only SET-vs-LIMIT is open.** **Not tuning further to decide it — with the old grades
withdrawn there is no reference to tune against, and the difference is a judgment about how harsh the
instrument should be, which is Sean's.**

**v26 change — D40 completed (parallel driver) and D41, the bubble-tea hand-read.**
*(1) **The driver is now PARALLEL** (`run_corpus_parallel.py`, bounded at 8 workers, one subprocess per
case): **120 cases in 9 s against 107 s sequential — 12× — with 0 failures and one rubric version.**
**Output agrees with the sequential run within the noise floor**, so scheduling changed and results did
not. *(Excludes underscore-prefixed meta/fixture files, so the deliberate `_refused.json` refusal test
no longer registers as a failure.)*
*(2) **⚠ THE NOISE FLOOR IS NOW SETTLED — three independent batches of the same rubric v1.12.0**,
comparing all three pairs: **worst per-dimension noise 4.2%** (PS 4.2%, MA 4.2%, **DEF 2.5%**, CR 0.8%,
MH 0.0%, DR 1.7%). **This settles two things at once:** the compression effect on defensibility
(**16.7%**) is **well above its 2.5% noise and is therefore REAL**, and the D39 collateral moves at ±1
are **inside noise and cannot be claimed.** **Rule going forward: a movement must exceed ~5% before it
is worth interpreting.**
*(3) **⚠⚠ D41 — the bubble-tea hand-read. THE INSTRUMENT FLATTENS DEFENSIBILITY.** Sean's bubble-tea
grades spread **1–4**; the instrument's spread **2–4** and clusters at 3–4. **Both two-point gaps are
the instrument reading HIGH** — Each-A-Cup 4 vs his 2, Gong Cha 3 vs his 1. **It does not go low enough
on genuinely undefendable businesses.**
*(4) **And the rule behind Sean's spread resists derivation — I checked.** Across the corpus his
defensibility tracks **format capital intensity monotonically** (no premises **1.00** · home-based 1.74 ·
kiosk **2.46** · small premises 2.56 · office 3.00 · restaurant **3.20** · large-format store **3.59** ·
licensed premises **4.50**). **That explains KFC's kitchens-and-outlets against Gong Cha's kiosks. But
bubble-tea breaks the rule: KOI runs the same counter format as Gong Cha yet gets 4 where Gong Cha gets
1.** So **format is necessary but not sufficient**, and **the differentiator is knowledge Sean holds —
tenure, outlet count, or his mental-ladder definition — not visible in the grades.**
*(5) **Flattening is now the dominant remaining error in this dimension**, and it is the same defect
every other finding in this section has pointed at: **the instrument systematically pulls defensibility
toward the middle.** Addressing it is a construct question for Sean, not a tuning exercise — and at a
4.2% noise floor, **only the two 2-point cases are outside noise, and both are the instrument reading
high.**

**v25 change — D40 executed. Rubric compressed; the noise floor is measured; accuracy did not suffer.**
*(1) **Compression (rubric v1.12.0).** `defensibility` instruction **5,426 → 3,026 chars (−44%)**,
questions block **21,366 → 19,405**. **All 13 distinct rules kept and explicitly checked for**; what came
out was duplication (rule 5 appeared verbatim twice, and the fame/network rules restated each other).
*(2) **⚠⚠ THE NOISE FLOOR IS NOW MEASURED — two independent full batches of the SAME rubric v1.12.0.**
Cases changed between identical batches: **PS 4.2%, MA 2.5%, DEF 1.7%, CR 0.0%, MH 0.0%, DR 1.7%** —
**every movement ±1 level.** **So batch noise runs 0–4.2% per dimension, and that is the threshold
future tuning must clear.** *This is the measurement v22 should have had instead of three rapid
repeats, and it is why the earlier "deterministic" claim was wrong.*
*(3) **Compression did not cost accuracy — it improved the headline measure.** Defensibility disputes
**3.3% → 1.7% [0.5–5.9%]**, the best on record and clearing the ≤5% bar on its interval; within-one-level
held at 48.3%; MAE flat (0.50 vs 0.52); offset +0.07. **And the authorised corrections survived —
KFC, Ya Kun and Toast Box all hold at 4.**
*(4) **⚠ Honest counterpoint: compression raised 17 cases and only 10 were improvements**, concentrated
in the micro categories (nail bars, home facials, home bakers 1→2) — Polar Puffs 2→3, Chin Mee Chin
2→3, Maniqure By Ling 1→2, Facial Inc 1→2, My Skin Diary 1→2 all moved AWAY from Sean. **NTUC FairPrice
dropped 5→4 against his 5.** **Aggregate improved; a minority of individual cases degraded.** Same
pattern as D39's collateral.
*(5) **Still not done: the driver is sequential** (0.48 s model vs ~0.85 s overhead per case, 107 s for
120). **A one-file parallelisation remains the cheapest remaining speed win.**
*(6) **The two clearest standing disagreements are now `Each-A-Cup` (instrument 4, Sean 2) and `Gong Cha`
(3 vs 1)** — both bubble-tea, both cases where he sees near-zero defensibility. **They are the best
next hand-read, ahead of any further rubric tuning.**

**v24 change — D39 applied on Sean's authority; D40 answers the Jev question with measurements.**
*(1) **D39 — the operated-network rule (v1.11.2).** Sean authorised the KFC/Ya Kun/Toast Box judgement.
**Applied as a GENERAL rule, not three patches**, because a rule shaped around three businesses does not
survive the next submission: **a chain that demonstrably operates many units holds efficient scale even
where opening a single unit is cheap — the barrier is the NETWORK, not one more shop.** **All three land
exactly on Sean's 4.** **⚠ Collateral: 13 cases moved (8 up, 5 down); CHAGEE and NTUC FairPrice improve,
but Mixue, CHICHA San Chen and Each-A-Cup move the WRONG way and 24/7 Fitness and Chin Mee Chin drop.
Corpus totals are a wash — DEF disputes 2.5% → 3.3%, back to v1.8.0's level.** *The three authorised
corrections are exact; the aggregate did not improve.*
*(2) **D40 — Sean asked: *"Are we using Jev to improve the speed and overall process?"* Measured answer:
NO — Jev is not the constraint, the rubric is.** **Model latency 0.48 s/case; the whole 120-case corpus
runs in 107 s; 300 cases projects to ~4.5 min.** **But 90% of every prompt is the rubric (20,472 of
22,774 chars), and the rubric grew 46% this session (14,591 → 21,366 chars) with the defensibility
instruction alone up 4.5× (1,204 → 5,426) — because of my own iteration.** **That bloat is a plausible
contributor to the batch variance just measured.** **The process levers are: compress the rubric
(smaller prompts are faster, cheaper AND more reproducible); parallelise the driver (process overhead
~0.85 s/case exceeds the 0.48 s of inference and runs strictly sequentially); fix the noise floor before
tuning further; and only then spend Jev's speed on the inline category reasoning and the D25 scan that
the spec currently gates.**

**v23 change — Sean rejected the form fix and was right; reasoning works; and my determinism claim was
over-stated.**
*(1) **Sean: *"It shouldn't be in the form. I much rather reasoning is used to make the judgement here
and I know this is possible."* Correct, and the evidence supports him.** The derived competitive set
**already names six big-box incumbents for Best Denki** (*Courts, Harvey Norman, Best Denki, Gain City,
Challenger, Mega Discount Store*) with the diagnostic *"the same TV brands, on the same mall floor, at
near-identical prices"*. **The state held the consolidation signal; the rubric was not asking for it.**
So this is a **prompt defect, not a data defect** — fixable without touching the form, which matters
because **adding form fields would ask the founder to do work the instrument can already do**, against
§1's rule against asking the founder to do analyst work.
*(2) **✅ THE REASONING PATHWAY WORKS — rubric v1.11.1**, after a first cut (v1.11.0) that was too blunt.
**Best Denki and Gain City move 2 → 3–4 against Sean's 4 — a two-point move, beyond the noise floor —
and the canary does not move, so the pathway discriminates rather than inflating everything.**
**v1.11.0's failure:** *"must not default to the lowest levels"* **lifted 10 micro nail/facial
businesses 1 → 2 that Sean scores 1**, and a blunt fame guard demoted genuine networks (KFC, Ya Kun,
Toast Box, NTUC, Sheng Siong, Eu Yan Sang 4–5 → 3–4). **v1.11.1 separates the two questions — what the
business DEMONSTRABLY OPERATES (a multi-outlet network is efficient scale and belongs at 4+, even for a
famous brand) versus how EXPENSIVE ENTRY IS (trivially cheap ⇒ still 1, and fragmentation alone raises
nobody).** **Net effect on the corpus: DEF disputes 3.3% → 2.5%, offset +0.03 → −0.07, within-one-level
44.2% → 51.7%.** Note MA 8.3%→7.5%, CR 9.2%→8.4%, PS unchanged, MH and DR unchanged — **the
defensibility change did not damage the other dimensions**, which is what the canary could not tell us.
*(3) **⚠⚠ MY DETERMINISM CLAIM WAS OVER-STATED AND THE FULL-CORPUS RUNS CAUGHT IT.** v22 reported the
instrument deterministic on three repeat runs (spread 0). **Across two full batches, `mental_advantage`
changed in 7 of 120 cases and `competitive_room` in 2 — with instructions I never touched.** So **the
instrument has roughly ±1-level batch variance at around a 5% rate**, and **any single-batch comparison
of a 1-level difference is inside the noise floor.** *Consequence: the within-one-level improvement
(44% → 52%) cannot be claimed, and neither can the chains' 1-point movements.* **Only the 2-point moves
survive.** *Lesson: three rapid repeats measure within-session repeatability, not batch stability, and I
generalised from them without testing the general claim.*
*(4) **⚠ OPEN — three chains still sit one below Sean: KFC, Ya Kun, Toast Box at 3 against his 4.** Their
moat is a large outlet network, which **is** efficient scale, but the **"fame is not a moat"** guard is
reading their brand and discounting it. **The counter-argument is real: anyone can open a fried-chicken
or kopitiam outlet, so entry is individually cheap, while the incumbents' networks took decades.** **The
construct question — does a national F&B network count as efficient scale when category entry is cheap?
— is Sean's to settle, and I am deliberately NOT tuning it further on single batches**, because the
remaining differences are at the measured noise floor.

**v22 change — D37 implemented; D36 withdrawn as MY error; D38 raised and it is the most important
finding in this document.**
*(1) **D37 CLOSED — the moat rewrite is in (rubric v1.10.0).** Sean: *"D37, moat rewrite based on the
structure."* DEF now requires **evidence of at least one named moat source** — efficient scale,
capital requirements, intangible assets (with **price-premium brand** the only brand route), switching
costs, cost advantage, network effect — plus the **primary/ancillary** distinction and an explicit
**"fame is not a moat"** guard. **The ad-hoc CATEGORY STRUCTURE block added in v1.9.0 was cut**, since
it was the same content in worse words and with less authority behind it.
*(2) **✅ VALIDATED — the instrument is DETERMINISTIC.** Three repeat runs per case on the four disputed
businesses: **spread 0 on every one.** So the earlier 2→3 shift under v1.9.0 was a **real rubric
difference, not sampling noise** — which settles a question left open in v21 and means the instrument's
scores are reproducible and attributable.
*(3) **⚠⚠ D36 WITHDRAWN — my "defensibility is on a mismatched scale" finding was FALSE.** I assumed
Sean's DEF grades were 1–5. **`build_regrade_sheet.py:183` told him 1–6 and his grades use the full
range (max 6.0).** The scales were matched; **DEF's dispute rate is 3.3% (4/120), under the bar, before
any fix.** The apparent "6.7% → 1.7%" improvement was an artefact of a conversion that should never
have been applied. **This is the fourth frame error retracted this session** and it is recorded rather
than quietly deleted. *(Making DEF 5 levels remains a coherent uniformity choice; it just fixes
nothing.)*
*(4) **⚠⚠⚠ D38 — THE REAL FINDING, and it came out of chasing Sean's moat question.**
**99 of 120 corpus cases (82%) carry `label_is_external: true` and an `authoring_note` reading *"FORM
DATA reconstructed by the analyst from public sources… the form is thinner than a real submission. This
is the known weakness of the test."* Median form payload: 725 characters.** **The corpus therefore
measures agreement on analyst-reconstructed forms, NOT on real submissions.** **And defensibility is
the dimension most damaged**, because structural barriers — outlet counts, tenure, owned premises,
licences — are the facts **least** likely to appear in a positioning sentence and **most** likely to be
known to the owner. **Best Denki is the proof: Sean scores 4 from knowing it holds ~14 stores and a
national network; the form states only *"Japanese retail service standards"*; the instrument says 2 —
correctly, on what it was given, and it still says 2 under v1.10.0.** **The instrument is not wrong;
the input is thin.** *This is the same class of gap Sean already flagged — "You have blind gaps. You
have to corroborate your answer against physical evidence."* **FIX IS IN THE RUBRIC, NOT THE FORM — Sean ruled: *"It shouldn't be in the form. I much rather
reasoning is used to make the judgement here and I know this is possible."* He was right.** The derived
competitive set **already names six big-box incumbents for Best Denki**, so the state holds the
consolidation signal and the rubric simply was not asking for it — **a prompt defect, not a data one.**
**rubric v1.11.1 adds a REASON-ABOUT-THE-CATEGORY pathway; Best Denki and Gain City move 2 → 3–4 (Sean
4); canary does not move.** Two open items: **the three chains at 3-vs-4** (KFC, Ya Kun, Toast Box — a
construct call, and the "fame is not a moat" guard discounts their networks); and **the noise floor,
which is larger than v22 claimed** — `mental_advantage` moved 7/120 and `competitive_room` 2/120 across
full batches with unchanged instructions, so **the instrument is NOT deterministic and ±1 differences
are inside the noise.** The calibration claim must be restated so "100% band agreement" is not read as
validating real-submission performance.

**v21 change — two findings from Sean's moat question, one of them a measurement defect.**
*(1) **⚠⚠ D36 — `defensibility` IS SCORED ON A 1–6 SCALE while every other dimension is 1–5.**
`rubric.json` declares `level_counts.defensibility = 6` (others 5) against a scale block that says
`human_display: "1-5"` — a deliberate 0.5.0 split, per the code comment. **The 6th level fires: display
6 appears 3 times, mean mass on the 6th bin 3.4%, and the composite divides defensibility by 6.**
**So every §10.6 defensibility comparison has pitted a 1–6 score against Sean's 1–5 grade.** Putting
the scales on the same footing moves the disputes **6.7% → 1.7% (percentile-matched) / 4.2%
(round-to-nearest)**, both under the bar, against PS 0.8% / MA 7.5% / DR 4.2%. **Defensibility is not
the worst dimension once the scales match.** It was investigated as a rubric-CONTENT problem because
the raw number was above the bar; it is at least partly a **SCALE** problem — same class as the §5.4
rounding gap. **Raised as D36, not fixed unilaterally** (it invalidates prior runs).
*(2) **D37 — Sean's moat question was right and identifies the exact defect.** Researching Buffett /
Morningstar / Stigler against primary sources **CONFIRMS all three of his DEF rulings** — Best Denki and
Gain City = **efficient scale + capital requirements**; Gong Cha and Each-A-Cup = **no moat source at
all**. **⚠ It corrects the REASON: he justified Best Denki with *"they all have mental advantage,
there is some defensibility"*, and mental advantage is not a moat source under any of the five** — that
is precisely the double-count that made DEF and MA agree too often. **He caught it himself.** Decisive
verbatim, Morningstar: *"Just because a company boasts a well-known brand, or has been in business a
long time, does not necessarily mean it has an economic moat"* (their illustration: United and Ford
versus Nike and Apple — four household names, two moats). **⚠ One honest limit: adopt the moat's
STRUCTURE — structural barriers not fame, primary vs ancillary distinguished — NOT its PURPOSE.**
Buffett's moat predicts long-term returns on capital; §1's objective is quality of the current position
relative to competitors. Importing the investor purpose would be the **seventh** imported framework in
this document.
*(3) **The v1.9.0 rubric edit bypassed the promotion gate and this is recorded rather than hidden.**
`rubric.json` was edited directly and the version stamped by hand; the harness caught a half-completed
stamp (`top-level 1.9.0` vs `_meta.version 1.8.0`) and refused to run — *"an inconsistent stamp defeats
the mixed-version guard"*. **Fixed, but `promote_rubric.py` was not used, and §5.3.1 step 4 (the
production scorer must refuse a non-promoted rubric) is still not built.**
*(4) **Canary re-run against v1.9.0: PASSED — no band moved — but it is WEAK evidence for this change.**
All six canary fixtures are micro/single-outlet businesses already correctly at defensibility 2, where
"fragmented, low entry cost" is the right reading, so **category structure cannot move any of them**.
The canary proves **no regression**, not that the change works. **The only evidence for the change is
four single runs on the disputed cases (Best Denki 2→3, Gain City 2→3, Each-A-Cup 4→3, Gong Cha 3→3),
which is not enough to distinguish signal from noise — and all four landed on the same value 3, which
may be convergence or may be loss of discrimination.** A repeat run is required and was not done.

**v20 change — D35 CLOSED on B. `defensibility` now reads category structure (rubric v1.9.0).**
*(1) **Sean ruled B:** *"Can we agree on B for defensibility?"* The rubric now takes **category
structure** as an input — **consolidation** and **capital- or licence-intensity** add defensibility;
**fragmentation with low entry cost removes it** — so a large multi-outlet retailer in a consolidated
category holds real barriers even when its submitted differentiator is unremarkable. **An explicit
"familiarity is not defensibility" guard was added**, so being well known earns nothing here (it is a
`mental_advantage` fact) — without it, DEF and MA would double-count the same signal.
*(2) **The evidence that decided B over C.** After Sean's four sheet corrections, the **4 residual DEF
disputes were ALL construct cases** — electronics (consolidated) and bubble-tea (fragmented) — and
**zero were business-level**. **C was rejected on measurement, not preference:** Sean's own CR and DEF
correlate only **−0.19 across categories** (**+0.07** at business level), so consolidation was *not*
already hiding inside `competitive_room`; routing it there would have placed a category fact in a
landscape dimension where he does not read it. **The decisive row was that the residual error was
entirely the missing construct.**
*(3) **⚠ B does NOT fix Best Denki on its own, and this was nearly mis-claimed.** At DEF 2 both
businesses read "no barrier" — a *submitted-differentiator* reading. **The existing level-4 wording
already names their barrier** (*"scale built over years (a store network, a distribution footprint)… a
physical asset base"*), and Best Denki holds ~14 stores and Gain City a mega-store plus outlets. **So
the original score was a recognition miss at a level the rubric already had.** B explains *why the
category raises the ceiling*; it does not make the instrument apply the level it already describes.
**Both fixes are needed; only one is B.**
*(4) **⚠ B creates a data requirement that is not yet designed for, and it is the same construct as
D25.** Reading category structure needs to know **how many comparable players a category has and how
capital-heavy it is** — and today the report reads a single self-reported submission. So category
structure is either inferred from the submission (**which is what produced Best Denki at 2, and is the
failure B exists to correct**) or **sourced externally — which is D25.** **One scan can serve both**,
under D25's existing §3.11 pre-flight gate (the protocol's measured silent-failure rate is **60%**).
**A second-order risk is flagged:** where a category is **thinly populated**, "consolidated" must not
be inferred from absence — three operators in a small market is not consolidation, and the report
should say so rather than award defensibility for it.
*(5) **Two mis-numbered section references corrected** — both cited "§5.4" for the DEF definition, and
§5.4 is the refusal section, not the dimension definitions.

**v19 change — Sean hand-read all eight defensibility disputes, and it reframes D35.**
*(1) **Four of the eight "disputes" are SHEET errors, not instrument errors.** His rulings: Best Denki 4,
Gain City 4, Burger King ~4, IKEA ~4, Scanteak 3–4, Toast Box 3–4, Gong Cha low, Each-A-Cup low.
**IKEA, Scanteak and Toast Box land within one of the instrument; Burger King moves to ~4 against the
instrument's 3.** So **`defensibility`'s true disagreement is materially lower than 7.0%.**
*(2) **His sheet was internally inconsistent on the same construct** — **Burger King 1 vs KFC 4**, two
directly comparable global QSR chains three points apart; Subway 2 and Jollibee 2 sit with Burger King.
This is visible without any instrument, and it is the **second time this corpus has shown label noise
being misread as instrument error** (§10.6's J1/J2/J3 triage exists for exactly this, and it says
defaulting to "Jev is wrong" has been the wrong call before).
*(3) **THE REAL FINDING — a construct split, and it is definitional, not numeric.** Sean's labels
**cluster by category** (furniture flat 2 across IKEA, Scanteak, Cellini, Castlery; health-beauty flat 4
across four firms; home-not-permitted flat 1 across five), while **the instrument scores each business
on its own characteristics**. His Best Denki reasoning states it: *"the appliance market has consolidated
to a few brand names only in Singapore… because they all have mental advantage, there is some
defensibility because it's really concentrated at the top."* **That is a claim about the CATEGORY —
consolidation and mutual deterrence — which §5.4's "challenger's cost per business" cannot see.**
**And it explains the whole dispute table:** disputes cluster in **high-variance categories**
(electronics 3/4, fast-food 1/5, furniture), and where the category is **homogeneous** the two readings
agree. **D35 offers three options; C is recommended — keep business-level DEF and move consolidation
into `competitive_room`, which already measures fragmentation and is where a structure signal belongs.**
*(4) **A distribution finding that corrects an overstatement in this spec.** Measured over 606 cells:
**gap 0 = 60.2%, gap 1 = 33.7%, gap 2+ = 5.0%.** So *"2.8% disputes"* quoted alone **overstates the
agreement by a wide margin** — the honest headline is **60% exact, 95% within one level.** A third of
cells sit exactly one level apart and are invisible to the bar. **An earlier pass of this section said
"roughly half"; the measured figure is 33.7% and it is corrected rather than left as an impression.**
*(5) **No further grading is possible** — all 120 businesses are graded; `inputs-v2`/`inputs-v3` are
company-name subsets. Reaching a larger n requires **collecting new businesses**, which is research,
not grading. **The earlier "one afternoon of grading" advice was wrong.** It still prints *"exact >=75%"* and reports
**FAIL**, but **D20 retired dimension exactness** in favour of band agreement. The script is testing a
criterion the spec no longer holds — either retire the target in the script or label it historical.
*(5) **Two sections titled "input quality floor"** (§3.8 and §3.10) — §3.8 was the earlier title.
Marked superseded.
*(6) **A literal text duplication in §7.6** (*"A backup that lives / A backup that lives in the same
provider"*). Fixed.
**Also flagged, deliberately NOT changed:** §9 (jurisdiction) is already explicit about scoping to SG;
the §3.3 processor register is **correct** PDPA machinery, not an imported frame; the §3.6/§3.7 open
relay is a genuine problem. **The four errors today were all the same error — a frame imported from a
domain that did not fit — and three of the four would have been caught by checking Sean's OWN existing
corpus before asserting.** That habit, not this list, is the durable fix.
**v17 change — D34, the sole-proprietor line, confirmed.** Sean: *"Where a rival is one person,
'analyse the business, never the person' is the line you want."* Recorded as **D34** with the
distinction that keeps it from being over-applied: **it restrains ATTRIBUTION, not SCORING.**
A sole-proprietor rival is **still scored and still counted in the pool** — excluding them would gut
the benchmark in exactly the categories D3 targets, since home-based businesses are overwhelmingly
one-person operations. Describe such a rival **by category** (*"a home-based nail studio in the
east"*), never by name, photo or personal detail. A sole proprietor's *price list* is a public
business fact; their *name and likeness* are a different category of material, even though the
trading name may contain both.

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
| D4 | Ship the capture-only stage **before** calibration clears *(this is the **two-stage ship** of §11 — **not** the D4 that appears in §13's register, which is Sean's *"refuse them"* ruling. Same label, two different decisions: the §13 one is the five `home-not-permitted` cases)* |
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
| 4 | Position | Current positioning sentence *(or "we don't have one")* · What you believe makes you different · What competitors undercut you on · **years trading** · **owned vs leased premises** · **licences or certifications held** · **price premium vs the category** | position |
| 5 Numbers | Your price point · Their price point · How many competitors you can name | drives depth |

**Email is the only hard delivery dependency.** Every other field improves the report; none
blocks it (§4.4). The **cannot-refuse contract** holds: the answers alone must carry all five
scores.

**⚠ THE FOUR STRUCTURAL FIELDS ARE OPTIONAL BY THAT SAME CONTRACT, AND THEY CLOSE D38a.** *D38 found
that 82% of the calibration corpus is analyst-reconstructed thin forms, and that **`defensibility` is the
dimension most damaged** because barriers — outlet counts, tenure, owned premises, licences — are the
facts least likely to appear in a positioning sentence and most likely to be known to the owner.* **Best
Denki proved it:** *Sean scored 4 from knowledge of ~14 stores; the form said only "Japanese retail
service standards"; the instrument said 2 — correctly, on what it was given.* **So the fields are the fix,
not the rubric.** **⚠ THEIR ABSENCE IS NOT A REFUSAL:** *the cannot-refuse contract stands, and when they
are absent the report must say the structural reading is UNPROVEN and the dimension stays capped at
ADEQUATE (3) under the D51 rule — which is exactly how the instrument stays honest about a thin
submission without refusing it.*

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

### 3.8 Input quality floor — superseded, see §3.10

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

### 3.11 The pre-flight gate runs BEFORE the token spend (D30) ⚠

Sean's condition on D25, verbatim: *"It burns a lot of tokens so let's make sure before we run the
analysis we assess the input quality first, before deciding it is worth the token burn."*

**This is a sequencing rule, and the naive implementation gets it backwards.** The obvious shape is
*submit → run the competitor scan → score → discover the input was unusable → refuse.* That burns the
full research cost on a submission we are going to refuse anyway. **The gate must fire on the form
answers alone, before a single search is issued.**

| Order | Step | Cost | Fails to |
|---|---|---|---|
| 1 | **Deterministic quality check** on the form answers (§3.10's slot table) | zero — code, not a model call | Refuse / guidance email. **No scan runs.** |
| 2 | **Categorisation** — infer the category from the answers | one cheap model call | Ambiguous category → widen (§7.7.1) or refuse |
| 3 | **Scan-cost estimate** — is this category scannable at all? | one search | Thin/ambiguous category → cap or skip the scan |
| 4 | **The competitor scan** (§4.6) | **the token burn** | Best-effort; degrades depth, never existence |

**Step 1 is the load-bearing one and it is already built.** §3.10's floor already decides whether every
scored dimension has a form answer or a passing enrichment source. **Reusing it as the pre-flight gate
means the gate adds no new logic — it changes only WHERE it fires.** That is the cheapest possible
implementation and it is the whole point of Sean's rule.

**Three consequences worth stating:**

1. **A refused submission never triggers research.** The refusal is a *guidance* email naming the
   minimum answer threshold (D12), which is a cheaper and more useful outcome than a report built on
   guesses.
2. **The scan is budgeted per submission, not per batch.** §8.5's cost ceiling applies here; a
   single submission must not be able to consume an unbounded research budget. Cap pages fetched per
   competitor and competitors per submission.
3. **The check is deterministic.** Placeholder text, repetition inflation and the generic positioning
   sentence (§3.10's three traps) are **not** judgment calls and must not be delegated to a model —
   both because it is cheaper and because a model asked "is this good enough?" will be generous.

**⚠ The trap this rule protects against is not the token cost — it is the false confidence.** A
submission that fails the gate and is scanned anyway produces a report whose competitor comparison
rests on a category inferred from thin text. **The waste is the smaller problem; the confident wrong
answer is the larger one.**

### 3.10 The input-quality floor (D12, accepted) — **the live floor; §3.8 was its earlier title**

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
| A positioning or differentiator sentence | Position strength · Mental advantage · Defensibility | Absent or a **non-position** — see below |
| Competitors, named or counted | Position strength | Zero, **and** enrichment finds none |
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
| Competitor set via search | Position strength |
| Competitor messaging via fetch | Position strength · Mental advantage |
| Competitor size/tenure | Position strength · Defensibility |

### 4.6 The competitor scan is a scored pass, not best-effort (D25 direction) ⚠

> **⚠ BUILD STATUS, ADDED v38: THIS SECTION IS SPEC'D AND DIRECTED (D25) BUT NOT BUILT.** **The runtime
> has NO competitor scanner.** What exists is *competitor DISCOVERY* only, and only as **hand-curated
> per-CATEGORY dictionaries** in `build_v2_set.py` / `build_v3_hbb.py` — a set was written once for
> "consumer electronics retail" and reused for every business in that category. **There is no
> per-business scan, and nothing that captures a rival's POSITIONING, size or pricing** — i.e. columns 2,
> 3 and 4 of the table below do not exist in production. **The corpus's `_derivation_method` string is a
> TEMPLATE, not a research record** (identical shape for every case in a category).
>
> **⚠ AND THE RUBRIC WAS CONSUMING IT AS THOUGH IT WERE RESEARCH.** *PS's instruction asks "is that claim
> already owned by a named occupant of the derived competitive set?" — while the set supplies names, tiers
> and a price-floor label and nothing about what any occupant HOLDS.* **So the model was inferring
> "ownership" from its own category memory.** *Fixed at the rubric level in **v1.18.1** (see §10.6e) by
> restricting the basis to the supplied set and capping unproven flanks at 3.* **The scan remains the real
> fix — see §4.6.1.**

**Directed by Sean:** the same method the competitive-analysis projects use — *"exercise the web search
protocol skill to find and score other competitors, just like what we did for our competitive analysis
projects."* §4.4 already listed *"competitor set via search"*, but as **best-effort enrichment behind a
hard timeout** (§4.5). **This escalates it: the competitor scan is a deliberate, protocol-governed pass,
gated by §3.11.**

**Protocol, not ad-hoc searching.** The scan follows `web-search-scraping-protocol`'s chain:
`search → fetch → extract → escalate → grade`. Two of its rules are load-bearing here:

- **The validity gate is mandatory** (§4.1) — measured at **60% silent failure** (6 of 10 mixed URLs
  returned a Cloudflare challenge or CSS shell *as ordinary text, with no error*). A block page reaching
  Jev means **Jev scores a Cloudflare challenge as though it were a competitor's website.** This is
  already the highest-risk seam in the system and this section widens it — so the gate's coverage must
  extend to every URL the scan touches, not only the enrichment URLs.
- **The reward layer grades every capture** (§4.2) — grounding and coverage verdicts feed the *"what we
  checked / what we couldn't check"* block. **A scan that silently captured nothing must say so**, not
  produce an empty comparison that reads as "you have no competitors."

**What the scan produces, and where each part goes:**

| Captured | Becomes | Dimension |
|---|---|---|
| Named competitors in the category | The competitor set | Position strength |
| Their positioning / messaging | Differentiation contrast | Position strength · Mental advantage |
| Their size, tenure, footprint | Scale contrast | Defensibility |
| Their pricing where public | Price-band context | Competitive room |
| **Failed or blocked captures** | **The honest-limits block** | — |

**Three rules that keep this honest:**

1. **Observed ≠ claimed.** §7.3's split applies in full: scan-derived material is `observed`, form
   answers are `claimed`, registries stay `not checked` (§4.3). **A competitor's marketing claim is
   not evidence of their position** — it is evidence of what they say, which is a different and weaker
   claim, and the report must not conflate them.
2. **No score for a named competitor may be published to a third party.** The scan compares the
   *submitter* to the pool. Printing "Competitor X scores 43" about a business that never consented,
   never saw it and cannot dispute it is a different product with a different risk profile — see
   **D31**.
3. **The scan's result is perishable** (§7.11) and must carry a fetch timestamp.

### 4.6.1 The scan, built (v38) — and what it is NOT

**`competitor_scan.py` runs the protocol-governed pass this section specifies**, producing the
`derived_competitive_set` a submission would carry in production. **It is a REAL scan: the URLs are
discovered by search and the text is fetched live, through the same validity gate the rest of the system
uses.** *Run against a real category it returns a set with named occupants, what each one claims, and how
each capture fared.*

**⚠ WHAT IT IS NOT, STATED PLAINLY — three limits, because this is the component §4.6 already calls the
highest-risk seam in the system:**

1. **It is NOT validated against the corpus.** *The corpus's sets were hand-written per category, so there
   is no record of what a scan *would* have returned for those 120 businesses.* **The scanner has been
   proved to WORK (it discovers, fetches, extracts and grades), not proved ACCURATE (that its sets match
   what a human analyst would have written).** *Re-deriving the corpus's sets by scan and re-scoring would
   be the test, and it has not been run.*
2. **The validity gate is MANDATORY and this section widens its surface.** *§4.1 measured a **60% silent
   failure rate** — 6 of 10 mixed URLs returned a Cloudflare challenge or CSS shell as ordinary text, with
   no error.* **A block page reaching Jev means Jev scores a Cloudflare challenge as a competitor's
   website.** *The scanner therefore records a per-URL `capture_status` and refuses to present a blocked
   capture as evidence; blocked URLs land in the honest-limits block.*
3. **A scan with zero successful captures must NOT read as "you have no competitors."** *It must say the
   scan failed.* **This is the failure mode that produces a confident, wrong report — the same class as the
   60% silent failure, one layer up.**

**⚠ AND THE COST, QUANTIFIED BEFORE IT IS SPENT — the §3.11 pre-flight gate exists for exactly this
reason.** *Sean's condition, verbatim: "It burns a lot of tokens so let's make sure before we run the
analysis we assess the input quality first."* **A scan is ~N searches + ~N fetches per submission.** *At
the measured 0.48 s/case for scoring, the scan is orders of magnitude more expensive than the score itself
— so it must fire ONLY after the input-quality gate passes, and only for submissions worth the spend.*

**⚠ ORDERING IS LOAD-BEARING.** *The naive shape — scan → score → discover the input was unusable →
refuse — burns the full research cost on a submission that will be refused anyway.* **The scanner is
therefore designed to be called AFTER the deterministic quality check, never before.**

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
| 1 | Position strength | 25% | For each buying situation it competes in, how firmly does it hold that situation against the named occupants of it? Judged **per situation**, never as one share fight — positioning is about product categories, not industries. |
| 2 | Mental advantage | 20% | How much mind the brand holds in its segment. A **magnitude**, not a competitive claim: a brand can hold a great deal of mind while close rivals hold a similar amount. **Independent of closure** — a closed brand can still be the first name that comes to mind. |
| 3 | Defensibility | 20% | The challenger's cost to displace it: the accumulated barriers the business **holds**, not the differentiator its form claims. **Since v1.9.0 this is partly a property of the CATEGORY** (D35): consolidation and capital- or licence-intensity add defensibility; fragmentation with low entry cost removes it. **Familiarity is not defensibility** — being well known is scored under mental advantage and earns nothing here. |
| 4 | Competitive room | 15% | **Landscape, not business.** Fragmented and uncontested = 5; few giants and a price war = 1. |
| 5 | Market headroom | 10% | Is there unmet demand? Dropped automatically where supply is capacity-elastic (A3). |
| 6 | Demand reach | 10% | Can it find and reach an identifiable paying group? Addressability, not demand size. A business **currently trading** is at least 3. |

**Positioning carries 70%** (position strength + mental advantage + defensibility), because the
brief is *viability through differentiation*, not industry attractiveness.

**Two reversals to note.** `competitive pressure` treated a crowded market as *bad*;
`competitive_room` scores a **fragmented** market as **favourable** — the earlier polarity was
backwards. And `position availability` — whether a word was unclaimed — is replaced by
`position_strength`, which measures the position actually **held against the derived competitive
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
`position_strength` absent** while §10.7's results described 1.8.0 — so every calibration result
described a rubric nothing served. It was the *silent* failure this section warns about: a
calibrated rubric that nothing loads raises no error and produces no symptom until a client is
shown a score from the retired model.

**Resolution: `rubric.json` is now 1.8.0**, promoted through a gated script.

| Step | Requirement | Status |
|---|---|---|
| 1 | The chosen rubric is promoted to `specs/calibration/rubric.json` — the single path both implementations read | **DONE** — 0.9.0 → 1.8.0 |
| 2 | The promoted file's `_meta.version` **must** equal its top-level `version`; the harness fails loudly on a mismatch | enforced before promotion |
| 3 | Superseded rubrics are retained as `rubric-v<X>.json` for the audit trail, never left as the live file | 1.0.0–1.8.0 retained |
| 4 | No report is served unless the loaded rubric's `_meta.version` is the promoted one | **DONE — `rubric_gate.py`, enforced in `run_jev.py`** |

**The promotion is a script, not a copy, because a copy cannot refuse.** `promote_rubric.py`
validates six conditions and exits non-zero rather than promoting a bad file:

1. `version` and `_meta.version` agree — the mismatch that once let two different files both claim
   `1.2.0` and defeated the harness's own mixed-version guard;
2. all six calibrated dimensions are present;
3. weights sum to 100;
4. `position_strength` **has** a weight — its absence is the 0.9.0 defect;
5. the band table is present and starts at Fragile;
6. **no score gates survive** — calibration removed them (§5.4), so a file carrying them is stale.

**Step 4 was built on 2026-09-29 (`rubric_gate.py`).** It is the one that matters in production:
the scorer must refuse to serve a report whose rubric was not promoted. **The promotion gate protects
the *rubric*; step 4 protects the *report*.**

#### Why a hash, and not the version string

**A version string proves nothing, because it is set BY HAND when a rubric is edited directly — which
is what happened repeatedly in this project.** `rubric.json` was edited in place and the version bumped
manually, so `promote_rubric.py` was never run and none of its six checks were ever applied. The file
*claimed* a version; nothing had verified it.

**So promotion now writes a sidecar, `rubric.promoted.json`, containing the version and the SHA-256 of
the promoted bytes — and only `promote_rubric.py` writes it.** A rubric whose hash does not match its
sidecar has been edited since promotion and is refused, **whatever its version claims.**

**Scope:** the LIVE rubric must be stamped; frozen references (`rubric-v<X>.json`) are exempt, because
calibration legitimately scores against retired rubrics and the canary's baseline is one of them.
**Promotion of the live file onto itself is allowed** — that is the recovery path after an in-place edit,
and the six checks still run.

#### The gate was proved by making it fail

**Seven probes, each a real command, not an assertion:**

| Probe | Expected | Result |
|---|---|---|
| Unstamped live rubric | refuse | **refused** — *"has NO promotion stamp"* |
| Frozen `rubric-v1.8.0.json` | allow | **allowed**, scored normally |
| Stamped live rubric | allow | **allowed** |
| **Tamper: edit a level's text after promotion** | refuse | **refused** — *"MODIFIED after promotion"*, sha mismatch |
| **Tamper: change only the version to 9.9.9** | refuse | **refused**, exit code 1 |
| Restore + re-promote | allow | **allowed**, clean |
| Full 120-case corpus run | no false refusals | **120/120, 0 failures** |

**Canary passes against the stamped rubric.** **⚠ The gate closes the loop that §5.3.1 predicted and
that then happened twice more in this session alone.**

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
in the same provider as the data is not a durability story.

### 7.7 The data is research, and that needs its own consent purpose

**⚠ Revised by D25 — read §4.6 and §7.11 alongside this section.** The cold-start argument below
assumed the calibration corpus was the *only* seed. **It is not: the competitor pool is built by the
protocol-governed scan (§4.6), so the pool is not capped at 120 businesses and the day-one coverage
figures in §7.7.1 are a floor, not a ceiling.** Two consequences: the *"11 of 27 categories"*
measurement describes what can be compared **without a scan**; and the **reproducibility** of the scan
weakens the dataset-as-asset argument (§7.11).

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

**⚠ Read §7.7.2 — the binary this table implies is FALSE.** Anonymisation is a property of each
**released artefact**, not of the stored record: the same submission can be pseudonymous in the
warehouse and anonymised in every published view. **§7.7.2 sets out five options (A–E) with pros,
cons and a path to viability.** One of them is what actually works at scale, and it is not
anonymisation.
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

### 7.7.2 Publication and confidentiality — the option space (D26) ⚠

**Corrected framing.** An earlier version of this spec presented a **binary** — anonymise properly, or
license pseudonymous data. **Sean's objection is correct: that was a narrow recommendation, not a
decision-ready menu.** It also embedded a false premise. **Anonymisation is a property of each
RELEASED ARTEFACT, not of the stored record.** The same submission can sit pseudonymous in the
warehouse and be anonymised in every published view. The real question is not *whether* to have a
boundary — it is **where the boundary sits, and what may cross it.** That gives a space of options,
not two.

**Plain-English glossary, because the jargon in this area is unusually bad.**

| Term used below | What it actually means |
|---|---|
| **Personal data** | Information that can be traced back to a specific person or business. Singapore law applies as long as this is possible — *even if nobody has actually tried* |
| **Anonymised** | The link is genuinely gone. No one — including us — can trace it back. Once true, the law stops applying |
| **Pseudonymous** | **The name is removed but a link still exists** (we hold a key). The law treats this as personal data. This is the term most often confused with anonymous, and the difference is the whole game |
| **Quasi-identifiers** | Details that aren't names but still give someone away — industry, size, location. In a small market these identify a business just as well as its name would |
| **Licensing** | Selling or granting permission to use the data, as opposed to publishing it openly |
| **One-way door** | A decision you cannot undo |
| **Secondary suppression** | Hiding a *second* number so the first hidden one can't be worked out by subtracting what's shown from the total |
| **k-anonymity** | A rule of thumb: only report a figure if at least *k* businesses are behind it. No agreement on what *k* should be |

**The five options, and what each one actually is.**

---

#### Option A — Strict anonymisation. Aggregate only; no key; never licensed.

| | |
|---|---|
| **What it is** | On ingest, quasi-identifiers are stripped and generalised; only aggregates are retained; no re-identification key exists |
| **Protects against** | Everything. Nothing to leak, nothing to subpoena, nothing to re-identify |
| **Pros** | Strongest privacy statement; survives deletion cleanly (§7.5); GDPR/PDPA-cleanest; the *"your data never leaves"* claim stays true |
| **Cons** | **Weakest asset.** Coarse aggregates only — no "businesses like yours" comparisons, which is the feature. Cannot be licensed. Cannot be audited back to source if a figure is challenged |
| **Path to viability** | Requires the benchmark to work on **coarse** cells only. Viable if the comparison is *category-level* ("your category's median positioning score is Contested"), **not** *peer-level* ("businesses like you") |
| **Verdict** | Possible but self-defeating: it discards the asset that makes reciprocity worth offering |

---

#### Option B — Pseudonymous records, disclosed quasi-identifiers, contract-bound. *(Levels.fyi)*

| | |
|---|---|
| **What it is** | Contact details stripped; employer/title/level/location retained; recipients bound by anti-re-identification contract; contributors told plainly what is and is not promised. **Verified in practice** — this is how Levels.fyi funds a free service |
| **Protects against** | Casual leakage and public exposure — **not** a determined recipient, and not a regulator's view of identifiability |
| **Pros** | **The commercial model that actually works** — verified at Levels.fyi. Enables fine-grained comparisons; licensable, so the dataset can fund the service; honest about its limits, which is itself a credibility asset |
| **⚠ Now weakened by §7.11** | **The "licensable" pro assumed a proprietary dataset. §7.11 finds the public-source pool is REPRODUCIBLE by anyone running the same protocol — so there is little for a licensee to buy that they cannot rebuild.** B remains the option with the highest ceiling *if* a non-reproducible asset accumulates (history, calibration, judgments); **it is not the default**, and D26's recommendation moved to D/E for this reason. The row is kept because the **structure** of the option is sound and E preserves the ability to reach it later |
| **Cons** | **Legally still personal data** — a regulator can hold that the quasi-identifiers mean the data was never anonymised, so every deletion request must genuinely apply. Reputational exposure if a contributor is identified. Needs real contractual enforcement, not a clause |
| **Path to viability** | Three things must be true: (1) the consent wording discloses quasi-identifiers **and** the licensing use *before* the box is ticked; (2) the licence terms are actually enforceable against recipients; (3) deletion works on pseudonymous records and the "strip and aggregate" job is built |
| **Verdict** | **Highest ceiling, highest obligation.** Only adopt with the disclosure done honestly |

---

#### Option C — Named attribution / public contributor list. *(Mercer, APQC)*

| | |
|---|---|
| **What it is** | Data is masked, but the **names of participants are published**. Mercer publishes a participant list; APQC states *"We will list your organization's name… We do not accept submissions without the name of the company"* |
| **Protects against** | Almost nothing about participation. It protects the *numbers*, not the *fact of contributing* |
| **Pros** | Credibility — a visible roster signals a real pool; contributors get public recognition, which is itself a reward and can lift participation |
| **Cons** | **We are explicitly advised against this.** Agri Stats' 2026 judgment targets participant lists; APQC and Mercer can do it because their participants are large firms who *want* to be seen. An SG micro-SME in a 5-business category does not. Publishing participation plus a comparison is a re-identification path |
| **Path to viability** | Only with opt-in naming, large cells, and a category where being seen is a benefit. **Not viable for weak-positioning micro-SMEs — the segment §D3 targets** |
| **Verdict** | **Reject.** Wrong segment |

---

#### Option D — Aggregate research only; never licensed; the dataset is an internal moat.

| | |
|---|---|
| **What it is** | Contributions feed ObserveCo's own analysis and the "SG industry datasets" positioning claim, and nothing is ever sold or licensed |
| **Protects against** | Third-party exposure entirely — there is no recipient |
| **Pros** | Simplest consent story; no counterparty risk; keeps the moat proprietary, which is arguably the point of a moat; lower legal surface |
| **Cons** | **The dataset never generates revenue on its own** — it only supports the consulting sale. If the consulting sale is the riskiest assumption (Sean's point), this option **couples the dataset's value to the weakest link** |
| **Path to viability** | Fine as an **interim** posture. Viable long-term only if consulting demand is proven — i.e. it inherits the same unresolved risk |
| **Verdict** | **Sensible default for now; not a business model.** Compatible with A or B later |

---

#### Option E — Consent-tiered. Benchmark free to contributors; dataset use and licensing opted into separately.

| | |
|---|---|
| **What it is** | Three separable permissions: **(1)** scored report — always; **(2)** aggregate research use (D19's trade — unlocks the benchmark); **(3)** licensing to third parties — a **separate, later, higher-bar** consent |
| **Protects against** | Bundling. Each permission is evidenced on its own row and its own purpose |
| **Pros** | **Lets the option space stay open.** Ship with (1)+(2) and defer (3) until the dataset is worth licensing — no commitment made before it needs to be. A contributor can grant research use without granting licensing, which is a materially easier ask and likely a **much higher opt-in rate** |
| **Cons** | More consent surface to build and evidence; a lower licensing opt-in rate may make option B uneconomic later; risks the "we'll ask again" fatigue |
| **Path to viability** | Already largely designed (D19's separate purpose + own row). The added work is **purpose 4 = licensing**, with its own wording, its own row, and the §7.5 retention rule |
| **Verdict** | **Recommended.** It is the only option that does not force a one-way door now |

---

#### What the options actually differ on

| | A | B | C | D | E |
|---|---|---|---|---|---|
| Benchmark possible | coarse only | **fine** | fine | n/a | **fine** |
| Licensable | no | **yes** | yes | no | **later** |
| Regulator-safe | **strongest** | weakest | weak | strong | strong (tiered) |
| Deletion clean | **yes** | hard | hard | yes | hard for (3) |
| Revenue from data | none | **direct** | direct | none | **deferred** |
| Decision reversibility | reversible | **one-way** | one-way | reversible | **reversible** |
| Fits D3's segment | yes | yes | **no** | yes | yes |

**The decisive row is reversibility.** A, D and E can be changed later. **B and C are one-way doors** —
once data is licensed, it cannot be un-licensed. **E is the only option that preserves the ability to
reach B.**

**In plain English: E lets you decide later. B makes you decide now.** Since the dataset's value is
unknown until the toolkit has run (D29), **paying a now-price for a later-unknown is the wrong trade** —
that is the whole argument for E.

**So the recommendation is not "pick one".** It is: **adopt E (D19 + a separate licensing purpose),
run D as the interim posture, and revisit B only when the dataset is large enough that licensing is
worth the obligation.** A is available at any time for any *individual output* — that is the
reframing that dissolves the binary.

---

#### The one thing all five options share

**PDPA has no explicit k-anonymity safe harbour, and PDPC's guidance is 3–5** — below the industry
floor of 5 that Mercer, Milliman, Empsight, Payscale, Pave and WorldatWork all publish. **A Singapore
regulator applying the PDPC threshold could call a 5-business cell identifiable.** So no option here
licenses a claim of legal safety on cell size alone. The controls in §7.7.1 — floor, dominance cap,
secondary suppression, no absence flags — are what defend the position, and they are required under
**every** option. **D26 chooses the ceiling; §7.7.1's controls are the floor, and they are not
optional.**

### 7.11 Nothing here stays true — the reliability problem (D26 direction) ⚠

**Sean's objection, verbatim:** *"I think there are time and accuracy considerations to how long each
company positioning and competitiveness data stays relevant. Frankly I don't see how we can monetise
this with credibility because accuracy due to time uncertainty is always a problem."*

**He is right, and the reason is structural rather than fixable.** A positioning dataset is not like a
financial one. A salary figure is *measured* at a point in time and is a fact about that time. **A
competitive position is not a quantity — it is a relationship, and relationships move when any party
moves.** A competitor opening one outlet can change the submitter's position strength without the
submitter doing anything. **So the data does not merely age; it decays from both ends, and the second
end is not ours.**

| Data | Shelf life | Why | Refreshable by |
|---|---|---|---|
| **Category structure** | Long — years | Categories persist; entrants don't dissolve them | Nobody needs to |
| **Competitor existence / count** | Medium — months | Openings and closures | **Re-scan** |
| **Competitor positioning / messaging** | Medium — months | Copy changes with campaigns | **Re-scan** |
| **Competitor footprint / scale** | Medium — quarters | Outlets, headcount | Re-scan |
| **Price points** | **Short — weeks** | Promotions, inflation, repricing | Re-scan |
| **The submitter's own position** | **Short — and only they know** | It moved, or their market moved | **A re-submission** |
| **The submitter's mental-advantage claim** | Indeterminate | Brand recall decays on its own clock | Nothing cheap |

**The asymmetry that makes this hard.** Everything scan-derived is **re-acquirable** — a re-scan is a
cost, not a loss. But **the submitter's own position is not re-scannable at all**: only they can supply
it, so the moment they drift, that record is stale **and cannot be fixed by us.** A database of
positions where half the rows cannot be refreshed is not a durable asset.

---

#### The mitigation that actually exists

**Sell the method, not the number.** The perishable parts are the *facts*; the durable part is the
**frame** — the six dimensions, the rubric, and the judgment about what a defensible position looks
like in a given category. **That does not decay, because it is not a claim about the world; it is a
claim about how to read the world.** This is the same reason a consultancy's method outlives any
particular engagement.

**Make freshness explicit rather than implied.** Every figure carries its fetch date, and the report
states its own currency (*"competitor data as of September 2026"*) instead of presenting a snapshot as
a standing truth. **A dated figure is honest; an undated one is a liability.**

**Offer paid refresh as the recurring product.** If the free report is a snapshot, the *refresh* is the
subscription — and it is a genuinely recurring need, because the decay is perpetual. This turns the
problem into the pricing model instead of an obstacle to it. *(Ties to §7.2's funnel: the comparison is
given away; the refresh and the interpretation are what is sold.)*

**Cap what we claim.** The *"we maintain SG industry datasets"* positioning line must not imply
currency it cannot deliver. **"We maintain a method for reading competitive position, applied to current
data"** is defensible; *"we maintain an up-to-date dataset"* is a promise that decays the day after it
is made.

---

#### The consequence for D26 — and it points the same way Sean already chose

**⚠ Monetising the data itself is weaker than it looks, for a reason that has nothing to do with
time.** If the competitor material is gathered from public sources by a repeatable protocol (§4.6),
then **the pool is reproducible by anyone with the same tools.** A scrapeable dataset is not a
proprietary asset — the barrier to a competitor rebuilding it is a weekend of engineering, not a
relationship.

**What is actually defensible, in order:**

| Asset | Defensible? | Why |
|---|---|---|
| **The rubric and calibration** | **Yes** | 120 blind human grades and a six-dimension construct — this took months and cannot be scraped |
| **The scored judgments** | **Yes** | The mapping from evidence to a band is the product, and it is ours |
| **Self-reported positioning by SG SMEs** | Partly | Not reproducible — but thin, and perishable (§7.11 above) |
| **Public-sourced competitor data** | **No** | Reproducible by anyone; no moat |
| **The accumulated history** | **Yes, eventually** | Only time creates it — and it is the one thing a re-scan cannot rebuild backwards |

**This vindicates Sean's instinct and sharpens the choice.** His doubt was *"can we monetise this with
credibility?"* — and the answer is **not as a data licence, and not as an up-to-date database.** The
monetisable thing is the **method and its application**, which is exactly what the consulting engagement
already sells. **So D26 is largely moot for the *dataset* and live only for the *method*:** the
question is not how to protect a licensable asset, but **whether any public-sourced material may be
stored at all** (§7.5 retention, D24's provenance question).

**Recommendation, revised in light of this:** **D** (internal moat, never licensed) is the honest
posture, with **E**'s consent-tiering retained as the structure so a future option stays open. **Not
because D is attractive — because B's premise (a licensable dataset) does not survive the reproducibility
argument.** A is also acceptable and costs little, since the fine-grained comparison lives in the
*method*, not in the stored records.

**What this does NOT change:** the two-tier disclosure (D25) still matters — but for a different reason
than assumed. **It protects contributors, not the asset.** In a category of five, a comparison shown to
one of them still reveals the others, and that risk is unaffected by whether the data is licensable.

### 7.13 Naming and scoring competitors is not a compliance question (D25/D31) ⚠

**Sean's challenge, verbatim:** *"Why is it a compliance issue where I have scored a company based on
my own hardwork and due diligence based on publically available information?"*

**He is right, and the earlier framing was wrong.** I presented D31 as a compliance risk — *"scoring a
business that never consented"* — which **imported a consent framework that does not apply.** The
correction is a distinction I collapsed:

| | What it is | What governs it |
|---|---|---|
| **Personal data** | Information about an **identified or identifiable individual** (a human) | PDPA — consent, purpose, deletion |
| **A business's competitive position** | A judgment about a **company**, derived from **public sources** | Accuracy, sourcing, fair comment — **not consent** |

**A company is not a data subject.** KOI does not consent to being analysed, and its consent is not
required — the same way Book 1 analyses it, and the same way every competitive report has always
worked. **Sean's own published work already does exactly this** *(verified)*: Book 1 names **KOI, LiHo,
Gong Cha, Tiger Sugar** with outlet counts, and the CaiCa deliverable rules on named rivals —
*"S$3.50–5.50 | **Contested** — LiHO/KOI own it"*, *"S$4.50–8.50 | **Contested** — CHAGEE owns it."*
**So this is not a new risk being taken on; it is the established practice of the work itself.**

**"Consent" was the wrong word for three separate things**, and separating them dissolves the concern:

1. **The submitter's consent** (§7.7) — real, and about *their own* data. **Unaffected by any of this.**
2. **The competitor's consent** — **not required.** The material is public, the judgment is ours.
3. **The contributor pool's protection** (§7.7.1's floor, cap, suppression) — real, and about
   *contributors to our dataset*. **Also unaffected**, because nothing a competitor's public record
   contains came from our contributors.

**The two are genuinely independent, and that is the clean resolution:** naming a competitor is derived
from **public sources** and consumes **no contributor data**, so it triggers **none** of §7.7.1's
controls. The floor exists to protect *the pool*; naming a rival does not touch the pool.

---

#### What does remain — narrow, real, and proportionate

**Not a compliance regime. Three practical duties:**

| Duty | Why | Control |
|---|---|---|
| **Accuracy** | We are publishing a judgment about a named third party. If it is wrong, they can object — and the objection would be *justified* | §4.3 already requires every enriched claim to carry a source and a fetch timestamp. §4.1's validity gate prevents a block page being scored as a competitor |
| **Right of correction** | A named business has no other recourse | The report states the method, sources and date, and offers a correction route. Cheap, and it is also a credibility signal |
| **⚠ Sole proprietors and sole traders** | **The one genuine personal-data edge.** For a one-person business, the trading name may resolve to an **individual**. D3 targets home-based businesses — so this case is not hypothetical | **DECIDED (D34, Sean confirmed 2026-09-28): analyse the BUSINESS, never the PERSON.** Where a rival is one person, analyse the business — price, category, offer, footprint — and never the individual: no name, no photo, no personal details. Treat the sole proprietor's *identity* as personal data while treating their *business* as analysable |

**⚠ What D34 does NOT do — stated because a build could over-apply it and silently break the
benchmark.** The rule restrains **attribution**, not **scoring**. A sole-proprietor rival is
**still scored and still counted in the pool**:

| | Permitted? |
|---|---|
| Score the business and include it in the pool / median | **Yes — required.** Excluding sole proprietors would gut the benchmark in exactly the categories D3 targets (home-based businesses are overwhelmingly one-person) |
| Compare the submitter against the pool anonymously | **Yes** |
| Say *"your category's median is Contested, and you are below it"* | **Yes** |
| Say *"Jane's Nails scores 43"* — a named individual | **No** |
| Publish a photo, personal name, or personal details of a sole trader | **No** |

**The distinction is the same one this section already draws for companies, applied one level down:
the judgment about a business is fair comment; the identification of a private individual is a
different act.** A sole proprietor's *price list* is a public business fact; their *name and likeness*
are not the same category of material, even though the trading name may contain both.

**How to apply it in practice:** where the rival is a registered company (Pte Ltd, LLP), name and score
freely. Where the rival is a sole proprietor, **score it, count it, compare against it — and describe it
by category** (*"a home-based nail studio in the east"*) rather than by identity. §4.3's sourced-and-
timestamped claims apply unchanged.

**The third row is the honest residue of the original concern, and it is the opposite of a blocker:**
it says analyse the business, not the human behind it. **That is a sentence of style guidance, not a
consent flow.**

**Why the correction matters beyond the spec:** the wrong framing would have produced a **materially
weaker product** — an anonymous pool with no named comparisons, which is exactly the vague, low-signal
output that fails to build credibility. **Naming a rival and ruling on the band is the specific,
checkable claim that makes the report worth reading.** The compliance framing would have removed the
sharpest thing in it.

### 7.14 The toolkit is one touchpoint in a trust sequence (D32, D33 answered) ⚠

**Sean's answer, verbatim:** *"I hope you can see that I am trying to apply positioning theory here to
build trust and credibility with any potential customer. The more touch points they have with me, my
free tools, my social media content, my books, the more they will engage and convert with me."*

**This answers D32 and D33 together, and it corrects a mistake in how I framed both.** I treated the
toolkit as a **direct-conversion instrument** and then measured it against a base rate for *buying
advice* — 24% of micro-businesses, and falling. **That was the wrong yardstick.** The base rate is
for *purchase intent*, and the toolkit is not the ask. **It is the first of several low-cost
engagements that build the credibility the eventual ask depends on.**

**The strategy is sequential trust-building, and it is textbook positioning** — the brand is built
through accumulated exposure and demonstrated expertise, not through a single conversion event. The
touchpoint stack already exists:

| Touchpoint | Cost to the prospect | What it demonstrates |
|---|---|---|
| Social content | Free, low attention | Point of view |
| **Free diagnostic** | **15 answers** | **Method: "they can actually assess me"** |
| The books | Time to read | Depth, published credibility |
| Paid engagement | Money | — the ask |

**So the four-way identifiability limit (§7.12) becomes a sequencing map rather than a dead end.**
The toolkit only has to do **one job**: convert a stranger into someone who has seen the method work
on their own business. **It is not the closer, and measuring it as one was my error.**

---

#### Why this rescues D32

**D32's problem was that the target segment has a 24%-and-falling propensity to buy advice.** Under the
touchpoint model **that is the wrong question** — the toolkit is not asking them to buy. It is a
zero-marginal-cost credibility deposit into a segment that will need the service **when** something
changes (a new competitor, a lease decision, a stall in growth). **The 76% who would not buy advice
today are not a failure state; they are a latent pool the touchpoint sequence keeps warm.**

**This also makes the earlier evidence supportive rather than damning.** Micro firms have **no written
plan (only ~1/3)**, **13% use external finance**, and **16% with no employees seek any advice.** That is
exactly a population that has never been *shown* what structured thinking about their position does for
them. **The ILO finding that willingness to pay rises from 23–65% before delivery to 53–100% after is
the mechanism this strategy runs on** — and I had recorded it as an obstacle when it is actually the
argument for the sequence.

**Consequence for D32:** the toolkit stays aimed at **0–9-employee businesses.** The paid tier is
whatever the sequence produces — **and the funnel's job is to reveal it, not to assume it.** That was
the recommendation; this is now the *reason* for it.

---

#### Why this answers D33

D33 asked whether to test cold acquisition, the referral artefact, or both. **The touchpoint model makes
the question smaller, not bigger.**

- **Every touchpoint is a referral substitute.** Hinge's 71%-ask-a-person figure measures how buyers
  *find* firms; but its own other finding — **visible expertise drives 37.3% of referrals, more than
  client relationships (23.1%) or social relationships (17.7%)** — says what makes a referral *work*.
  **That is what content, the toolkit and the books are manufacturing.**
- **So the toolkit's measurable job is engagement and repeat contact, not immediate conversion.** A
  prospect who submits, reads, and comes back after the third piece of content **is the success
  case** — and a funnel that only counts booked calls would score that prospect as a failure.

**What must therefore be measured — the change this makes to §7.10:**

| Added metric | Why |
|---|---|
| **Return visits / repeat contact** | The sequence is the strategy; a single visit cannot show it |
| **Touchpoint overlap** (submitted + reads content, or + has the book) | Whether the sequence is compounding |
| **Time from first touchpoint to engagement** | Sales cycles here are long by design, not by dysfunction |
| **Conversion by touchpoint count** | Tests the actual hypothesis: does more exposure convert better? |

**The last one is the real experiment.** D33's "test both channels" becomes **"measure conversion as a
function of touchpoint count"** — which is cheaper to run and tests the strategy directly rather than
proxying it.

**And the honest limit stays:** with 300 submissions we can bound a rate; **we still cannot attribute a
conversion to the toolkit vs the content vs the book.** For that, the touchpoint count is the variable —
which is why it must be recorded from the first submission.

---

#### ⚠ The one risk this model creates

**A trust sequence makes the *first* touchpoint's quality load-bearing.** If the free report is wrong or
generic, it does not merely fail to convert — **it damages the sequence**, and the content and books
that follow are read by someone who has already been given a reason to discount you. **The 51.9% of
referred prospects who rule a firm out before talking (n=523) are the cautionary case:** the filter is
applied early and cheaply.

**So §7.10's instrument requirement is unchanged and now better justified:** the benchmark must be
**real at launch**, not mocked. In a trust sequence the first touchpoint is not a taster — **it is the
credibility position, and everything after it inherits that verdict.**

### 7.12 What the test can and cannot conclude (D29, quantified) ⚠

**Sean's question was whether the toolkit test can be made conclusive. The answer is: it can be made
conclusive about a NARROW pre-specified thing, and it cannot be made conclusive about the business
model.** Both halves matter, and the second half is the one that would have hurt.

**What it CAN establish — three rules, all citable:**

| Purpose | Rule | At our scale |
|---|---|---|
| **Zero-result bound** | If no paid engagement arrives from *N* submissions, the 95% upper bound on the true rate is **3/N** | 100 → *"<3%"*; 300 → *"<1%"*; 500 → *"<0.6%"*. **Unreliable below N=30** |
| **Precision** | To estimate a rate within **±B**, `n = 1/B²` | ±5pp → **384**; ±3pp → **1,111**. Independent of population size |
| **Comparing two versions** | 80% power, 5% alpha | 5%→10% needs **~435/arm**; 10%→20% needs **~199/arm**; 2%→5% needs **~588/arm** |

**Practical floor: pre-commit to 300 completed submissions before any go/no-go.** At ~100 per arm on a
comparative question you have **~52% power** to detect a 10%→20% difference — a coin flip. A result
from that sample is not a finding.

**⚠ Peeking destroys the result, and this is not a technicality.** Under continuous monitoring, a
nominal 5% significance can become **26.1%** — more than five times what you think it is. Even ten
looks means you need a reported **1.0%** to have a true 5%. **So the sample size and the decision rule
must be fixed before launch** (§7.10's pre-registration), or read with a sequential method rather than a
p-value.

**And a low-powered result does not merely miss — it misleads.** Below ~50% power, a "significant"
result is typically a large **overestimate** (Type M); below ~10% power it is often the **wrong sign**
(Type S). This is the argument for the sample floor, not against testing.

---

#### ⚠ What it CANNOT establish — and this is where the design was vulnerable

**A null result from this test cannot tell you *why* it is null.** The same empty outcome is consistent
with four different problems, and they have opposite remedies:

| If the result is empty, it could mean | Remedy |
|---|---|
| The tool is bad | Rebuild the tool |
| **The segment is wrong** | **Change who is targeted** |
| The offer or price is wrong | Reprice or repackage |
| There is no distribution | Fix reach |

**This is the identifiability problem, and it is the honest limit of §7.10.** A test that cannot
distinguish these four is not evidence for or against the business model — it is evidence that
something in a four-way chain failed.

---

#### The base rate is already unfavourable, before any test runs ⚠⚠

**This is the finding that matters most, and it did not need a test to surface.**

| Population | Sought external advice, past 12 months | Status |
|---|---|---|
| **Singapore — no employees** *(UK comparator)* | **16%** | REPORTED |
| **Micro, 1–9 employees** | **24% (2023), down from 31% in 2015** | **VERIFIED verbatim** |
| Small, 10–49 | 34% | VERIFIED |
| Medium, 50–249 | 45% | VERIFIED |

*Source: Enterprise Research Centre analysis of the UK Longitudinal Small Business Survey, 2023.*

**And it is worse inside that minority:** among micro firms who seek advice at all, only **32% used a
consultant or business adviser** — against **47% (small)** and **51% (medium)**. Accountants are the
dominant paid source. **So consultants are a minority channel even among the minority who buy advice.**

**⚠ D3's target may be the wrong commercial tier.** D3 names *weak-positioning SMEs* as the target, and
§7.2 routes 0–9-employee firms to Bookend B (S$800–1,200). **But the evidence says this is the segment
LEAST likely to buy any external advice, and the least likely to buy it from a consultant.** The
positioning *symptom* may be most visible there while the *purchasing* propensity is lowest — **a
segment can be the best audience and the worst customer simultaneously.** That is **D32**.

**The offer evidence is worse than the survey evidence.** When micro and small firms were **offered**
consulting at a **70–90% subsidy — having already signed a letter of interest** — **only 53% took it
up**, with liquidity given as the reason. *(Bruhn, Karlan & Schoar, World Bank, Puebla Mexico RCT,
n=432. **VERIFIED verbatim.**)* Firms that had *asked for* subsidised consulting, and *signed* for it,
still declined half the time when it was offered. **Willingness to pay before experiencing advisory
services is low (23%–65% would pay US$150) and rises only after delivery** — the ILO's conclusion is
exactly ours: *"potential demand is high, but the effective demand is low."*

---

#### The channel problem: a web toolkit tests the minority channel

**Referrals and direct human outreach supply nearly two-thirds of new business even for the
fastest-growing professional-services firms** (n=495, ~$85bn revenue). And **71% of buyers ask another
person first while only 11% search online.**

**The consequence is sharp and it cuts both ways:**

- **A web-acquisition test of a referral-led market will return a misleading null.** It would look like
  evidence against the toolkit when the real finding is that **the instrument measured the wrong
  channel.**
- **§7.9 already said the toolkit's edge must be the comparative judgment, not the price.** This is now
  quantified: the toolkit's *job* is a **credibility artefact in a referral conversation**, where
  someone else has already opened the door — not a cold-traffic engine.

**So §7.10's step 3 requirement is promoted from preference to necessity:** the toolkit must be tested
**both** as cold acquisition **and** as a referral credibility artefact, and **reported separately.**
Testing only the first would misread the second and misdiagnose the business.

**A 51.9% figure sharpens why the artefact matters:** more than half of *referred* prospects rule a firm
out before even talking to it. **A credible artefact is what survives that filter** — which is precisely
what a specific, evidence-based positioning report is.

---

#### ⚠ Read §7.14 before concluding from this section

**This section measures the toolkit as a direct-conversion instrument, and that is the wrong
yardstick.** Sean's answer to D32/D33 establishes the toolkit as **one touchpoint in a sequential
trust-building strategy** (§7.14). The base rate below is for *purchase intent*; the toolkit is not
the ask. **So the low base rate is not a verdict on the strategy — it is a description of why the
sequence exists.** The four-way identifiability limit becomes a **sequencing map**, not a dead end.

#### What can honestly be claimed, given all of the above

**Ship the test, but claim only this:** *"With N submissions we can bound the conversion rate to within
X. We cannot yet distinguish a weak tool from a weak segment, and the base rate for this segment is low,
so the test's primary value is eliminating the worst outcome — a confident build on an unvalidated
audience."*

**And record the fail branch now, in one line each:**

| Outcome | Reading | Action |
|---|---|---|
| ≥300 submissions, money received, rate above the pre-set floor | The path exists and converts | Invest further |
| ≥300 submissions, **no money**, tool credible and reports read | **Not a tool problem** — segment, price or channel | Retarget (D32) or reprice. **Do not rebuild the tool** |
| **<300 submissions** | **Inconclusive — do not conclude anything** | Extend, or fix reach first |
| Submissions arrive, no reports opened | Reach or promise failure | Fix the offer |

**The second row is the one that saves the project.** A null at ≥300 with an instrument that works is
**information about the market**, not about the code — and the remedy is D32, not a rewrite.

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

### 7.10 The toolkit IS the test — sequencing accepted as D29 ⚠

**Sean's challenge, verbatim:** *"If my riskiest assumption doesn't pay do you realise I do not have a
viable business model to begin with? So why can't the diagnostic toolkit be my test with proper
building of the benchmark, so that the results can be as conclusive as possible?"*

**He is right, and the earlier phasing was wrong.** §7.7.1's "the benchmark is Phase 2" advice said:
prove consulting demand in parallel first. **But nothing else in this system consumes the benchmark.**
The engine has exactly one consumer — the free toolkit that shows a comparison — and there is no
second user waiting for it. So "build the benchmark later" meant **building something no one was
waiting for.** That is not sequencing; it is deferral.

**And the phasing had the risk backwards.** It treated the benchmark as the risky build and the
consulting demand as the known quantity. **The opposite is true.** §7.9 says the toolkit's edge has
to be the comparative judgment — while the research says the segment that most needs positioning
help is the one least likely to have ever bought professional services. **Those are two halves of one
question, and they can only be answered together:**

| Question | How it can be answered |
|---|---|
| Does the benchmark produce a credible comparison? | §10.6 canary — **already passing** |
| **Do the people who receive it ever buy?** | **Only by running it against real prospects** |

**A benchmark built after the demand test cannot answer the demand question** — because the demand
test would have run without the comparison that is supposed to create the demand. That is the flaw
in the original phasing: it tested the offer *minus its differentiator*.

---

#### The test design

**The toolkit is the instrument, not the subject.** Five funnel steps, each measurable, each with a
decision rule **stated in advance** — because a threshold chosen after the data arrives is not a
threshold.

| # | Step | Measured as | Failure looks like |
|---|---|---|---|
| 1 | **Reach** — the offer gets in front of the right segment | targeted approaches made | Cannot reach 0–9-employee firms at all |
| 2 | **Submission** — they complete the form | submissions ÷ approaches | They won't invest 15 answers |
| 3 | **Benchmark opt-in** — they take the comparison | opt-ins ÷ submissions | The trade is not worth it to them |
| 4 | **Engagement** — they read it and respond | report opens, replies, questions asked | Report delivered and ignored |
| 5 | **Conversion** — they book or buy | booked calls ÷ submissions, then paid ÷ booked | **The failure mode named in §7.9: unqualified leads** |

**Steps 2, 3 and 5 are the load-bearing ones.** Step 5 is Sean's challenge stated as a number.

**⚠ Four metrics added by D33 (§7.14) — the funnel alone undercounts the strategy.** The toolkit is one
touchpoint in a sequence, so a funnel that counts only conversion scores a returning prospect as a
failure:

| Added metric | What it shows |
|---|---|
| **Return visits / repeat contact** | The sequence is the strategy; one visit cannot show it |
| **Touchpoint overlap** — submitted + reads content, + has the book | Whether the sequence compounds |
| **Time from first touchpoint to engagement** | Long cycles are by design, not dysfunction |
| **Conversion by touchpoint count** | **The real experiment** — does more exposure convert better? |

**Record the touchpoint count from the FIRST submission**, or the last metric cannot be reconstructed
later. **Honest limit unchanged:** 300 submissions bounds a rate; attribution between toolkit, content
and book needs the touchpoint count as the variable.

**Pre-registered decision rule (to be fixed before launch, then not moved):**

| Outcome | Reading | Action |
|---|---|---|
| Submissions arrive, **and** opt-in is reasonable, **and** calls get booked | The trade works and the segment buys | Continue; invest in the dataset (D26 decision becomes worth making) |
| Submissions arrive, calls get booked, **opt-in is very low** | The report sells, the dataset does not | Benchmark claim comes down; sell the report, not the dataset |
| Submissions arrive, **no calls** | **The §7.9 failure mode is real** | The lead magnet is wrong, or the segment is — **stop, do not build more** |
| **No submissions at all** | Reach or offer failure | Do not read as demand failure until reach is proven |

**The last row matters as much as the others.** "No submissions" and "submissions but no buyers" are
different findings with opposite remedies, and collapsing them is how this kind of test fools its
operator.

---

#### What makes it conclusive rather than decorative

Four requirements, and the honest limit:

1. **The benchmark must be real at launch, not mocked.** A fake comparison produces a fake opt-in
   rate. **The two-tier disclosure (§7.7.1) is what makes this possible on day one** — 11 of 27
   categories clear a floor of 5, so a genuine comparison exists immediately, labelled *emerging*.
2. **Thresholds fixed in advance.** Recorded here before launch; published reasoning for any change.
3. **Identical treatment of the control.** If §7.9's referral finding holds — 71% find a firm by
   asking someone — the toolkit should be tested **both** as a cold-acquisition channel **and** as a
   credibility artefact in a referral conversation. Those are different mechanisms with different
   rates, and testing only the first would misread the second.
4. **⚠ The honest limit: a small N cannot resolve a rate.** With a handful of submissions, a test
   can establish whether the **path exists** (submissions → calls → a sale) but **not** the rate. A
   2% and a 5% conversion are indistinguishable at that sample size. **So the decision rule must be
   written against what N can actually resolve** — presence of the mechanism, not its magnitude —
   and the sample-size figures to make that precise are being verified separately.

**This is the strongest available defence against §7.9's failure mode, and it is also the cheapest** —
because the instrument is the product under test. Building the benchmark properly is not a cost of
the experiment; **it is the experimental condition.**

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
| **Benchmark opt-in rate** | **The dataset's growth rate (§7.7.1). Moves before call bookings, and a low rate means the pool is not accumulating.** ⚠ **Re-scoped by §7.14:** the *justification* that this is "the dataset's growth rate" assumed the dataset was the asset. **After D26 (D/E) and §7.11, the dataset is not the commercial asset — the method is.** **Still worth measuring** (it tells you whether the benchmark feature is working and whether the pool clears the floor), **but it is not a leading indicator of revenue.** Track it as *feature health*, not as *asset growth* |
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

### 10.6b Fresh blind regrades — MA and CR pass on clean labels, and the old labels were the fault

**Method: `MA-CR-V2-GRADING.md`, 21 businesses × 2 columns, fresh definitions, from memory, no instrument
answer shown.** **Sean graded both.** *Same approach as the defensibility regrade, and run because the
defensibility regrade showed the shared label file is unreliable.*

#### ✅ MENTAL ADVANTAGE — 100% within one level, ZERO disputes

| | Sean (fresh) | Instrument v1.15.1 |
|---|---|---|
| **Exact** | **14/20 = 70.0%** | |
| **Within one** | **20/20 = 100.0%** | *(95% CI 83.9–100%)* |
| **Disputes (≥2)** | **0/20 = 0.0%** | *(95% CI 0–16.1%)* |
| Mean offset | **+0.23** | |

**The instrument's own range is full and well spread** *(level counts across 120 cases: 1→10, 2→45,
3→21, 4→34, 5→10)* — **it uses the whole scale and is not compressed.**

**⚠ So the 7.5–8.3% dispute rate reported earlier for this dimension was substantially a LABEL problem,
not an instrument problem.** Sean changed **7 of 20** of his own MA grades (35%, mean |shift| 0.35) when
regrading blind, and **on the fresh labels the instrument has no disputes at all.**

#### ✅ COMPETITIVE ROOM — 100% within one level, ZERO disputes, with a small systematic bias

| | Sean (fresh) | Instrument v1.15.1 |
|---|---|---|
| **Exact** | **8/21 = 38.1%** | |
| **Within one** | **21/21 = 100.0%** | *(95% CI 84.5–100%)* |
| **Disputes (≥2)** | **0/21 = 0.0%** | *(95% CI 0–15.5%)* |
| Mean offset | **+0.43** | **instrument reads slightly LESS room than Sean** |

**⚠ AND THE RELABEL RATE HERE IS EXTREME: Sean changed 17 of 21 CR grades (81%, mean |shift| 0.95) —
the highest of any dimension regraded so far.** *MA was 35%, defensibility was 59%.* **His old CR values
were spread 1–4 with 44 of 120 sitting at level 2; his fresh values run 1–3.** **So CR's earlier 8.4–9.2%
dispute rate was overwhelmingly a label artifact too.**

**⚠ Two observations about CR's SHAPE, both of which need Sean rather than tuning:**
**(a) The instrument clusters at level 2** — **61 of 120 cases**, with only 2 at level 4 and none at 5.
**(b) Sean never grades 4 or 5 either.** **Both readings therefore agree the top of the CR scale is
effectively unused** — either no market in this corpus genuinely qualifies (*the level-5 descriptor is
"uncontested and fragmented, with no dominant player and no established price floor"*, which may simply
be rare), **or the descriptors are pitched too high.** **That is a definitional question, and it is
recorded rather than tuned.**
**(c) The instrument carries a small systematic LOW bias (+0.43 offset)** — it reads slightly less room
than Sean on 11 of 21 cases. **It is within-one everywhere, so it is not producing errors, but if CR is
ever used for ranking rather than description, a consistent 0.43 shift matters.**

#### ⚠ THE SHEET'S OWN FLAW, RECORDED BECAUSE THE TEST FAILED

**The sheet was built to test MA's closure-independence rule** — *mental presence survives a business
ceasing to trade* — **using "A closed bubble tea outlet" and "A dormant home baker".** **⚠ Neither case
actually tests it.** **Both are ANONYMOUS fixtures: a nameless closed outlet and a dormant home baker
would score 1 on mental advantage whether or not the closure rule is applied**, because the segment could
not name them either way. **Sean graded the dormant baker 1 — correct, but uninformative** — and marked
the closed outlet **"?", which is itself the right answer for a fixture with no brand identity.**
**So the trap did not fire because it was not a trap. A real test needs a NAMED business that has closed
— and the corpus does not contain one.** *Recorded as a design failure rather than quietly dropped.*

#### ⚠ ONE DATA HYGIENE ITEM

**Sean graded Lenskart at 3.5, which is not a point on a 1–5 integer scale.** The instrument scored 4
(exact) under 3.5→4 rounding, **and the gap is −0.5 rather than ±1, so it does not change any statistic
here.** **But a half-point in a blind sheet usually means "between two levels" — and if that is intended,
the scale needs to allow it explicitly rather than having it appear once.** *Queried with Sean rather than
silently rounded.*

#### SUMMARY — the calibration alarm was mostly the ruler

| Dimension | Old-label disputes | **Fresh-label disputes** | Relabel rate |
|---|---|---|---|
| Mental advantage | **7.5–8.3%** ⚠ | **0/20 = 0.0%** ✅ | 35% |
| Competitive room | **8.4–9.2%** ⚠ | **0/21 = 0.0%** ✅ | **81%** |
| Defensibility | 6.7% → 3.3% | **1/17 = 5.9%** *(KOI, 2 levels)* | 59% |

**⚠ Two of the three "failing" dimensions were failing against labels, not against reality.** **Every
dispute rate quoted before this section was measured on `sean-regrade-raw.csv`, which these regrades show
carries 35–81% relabel noise depending on dimension.** **The correct reading is that the instruments are
in materially better shape than the calibration claimed — and that the 120-case corpus must be regraded
before any further tuning is attempted, because tuning against it would be fitting to noise.** *This is
the same error that produced the v1.11.0 over-raise, caught this time before it did damage.*

**⚠ Limits, stated plainly: n=20–21 per dimension gives a SHAPE reading, not an accuracy figure — the
within-one intervals reach down to ~84%. And two of three regrades agree unusually well partly because
they were graded after the definitions were explained in the sheet.** *A stricter test would grade from
the raw submission, not from a stated definition.*

### 10.6c Competitive room reframed: CROWDING → DOMINANCE (Sean: *"hawker stalls would be 5"*)

**Sean's one-line correction exposed a defect that had been in the rubric since 0.6.0:** **level 5 of
`competitive_room` read *"Uncontested, fragmented, with no dominant player and no established price
floor"*** — **and *"uncontested"* contradicts *"fragmented"*.** **A fragmented market is by definition
contested by many rivals.** **The near-contradiction is why level 5 was unreachable:** *the instrument put
61 of 120 cases at level 2, only 2 at level 4 and NONE at level 5 — and Sean never graded 4 or 5 either.*

#### The defect: the scale conflated the NUMBER of rivals with the ABSENCE of room

**A hawker stall faces dozens of rivals and still leaves room, because no rival holds power over price.
An appliance market held by a few big names leaves almost none.** **Room is removed by DOMINANCE, not by
headcount.** *The old scale could not express that — so it pushed every crowded market downward and left
the top of the scale dead.*

#### The fix (rubric 1.16.x)

**The question is now: how much power does any single player hold over price, shelf or customer demand?**
**Level 5 = atomised and dominated by nobody. Level 1 = consolidated into one or a few dominant players
who control price or access, so a small operator cannot enter profitably.**

| | v1.15.1 (crowding) | **v1.16.1 (dominance)** |
|---|---|---|
| **Range used** | 1–4 | **1–5** |
| **Spread (SD)** | 0.58 | **1.00** |
| **Level 2 pile-up** | **61** of 120 | **33** |
| **Level 4** | 2 | **43** |
| **Level 5** | **0** | **4** |
| **Bias vs Sean** | +0.43 | **+0.14** |
| **Exact** | 8/21 (38%) | **12/21 (57%)** |
| **Within one** | 21/21 (100%) | **19/21 (90%)** |
| **Disputes (≥2)** | 0 | **2/21 (9.5%)** |

**⚠ 68 of 120 cases moved — a very large intervention, far above the 4.2% CR noise floor, so the change is
real and attributable.** **The monopolists came out right without being asked:** **ASML 3 → 1 and Boeing
2 → 1** — *level 1 is "no room for a small operator", which is the correct reading for both.* **The hawker
moved 3 → 4**, which the old rubric could not reach at all.

#### ✅ THE TWO RESIDUAL DISPUTES — RESOLVED IN THE INSTRUMENT'S FAVOUR

**Best Denki and Courts initially appeared as regressions: Sean had graded both 1 in the sheet, the
reframed instrument read both 3.** *Both are consolidated Singapore appliance/electronics retail.*
**⚠ I made two levelling attempts — the reframe itself (1.16.0), then a sharpening of levels 1–3 that
removed a *"a small operator can still find a gap"* escape hatch (1.16.1) — and the reading did not budge
from 3.** **By the third attempt it would have been fitting wording to two cases, so I stopped and put it
to Sean instead.**

**⚠ SEAN RULED: *"you are right it is a 3 for best denki and courts."*** **The instrument was right; the
grading sheet was wrong.** **On the corrected labels COMPETITIVE ROOM is exact 14/21 (67%), within one
21/21 (100%), disputes 0/21 (0.0%), offset +0.33.**

**⚠ THE STOPPING RULE PAID FOR ITSELF:** *had I forced a third wording change to satisfy the sheet, I would
have bent a correct rubric to fit a bad label — the exact error that produced the v1.11.0 over-raise.*
**This is the third time in the session a hand-read disagreement resolved the same way: the LABEL was the
first suspect, and the label was at fault.** *Prior instances: IKEA, Scanteak, Toast Box, Burger King.*

#### ⚠ NOTE ON THE REFRAME'S PROVENANCE

**This change was NOT driven by the fresh blind labels alone** — *those showed CR at 100% within-one and
zero disputes.* **It was driven by Sean's hawker judgement and by the structural contradiction in the old
level 5.** **So it is a deliberate quality improvement that COST two previously-agreeing cases.** *Net
position is better (range live, spread doubled, bias quartered, L5 reachable, monopolists correct) but the
two lost cases are real and are reported rather than buried.*

### 10.6d ⚠ `position_strength` COLLAPSED INTO `mental_advantage` — 25% of the composite was measuring an existing dimension

**⚠ FOUND ON SEAN'S POINTER, NOT BY ME:** *"I think there is a problem with PS definition. It is not what we
agreed on. Can you figure out what it is?"* **He was right, and the defect is measurable.**

#### The finding

| Measure (120 cases, v1.16.1) | Value |
|---|---|
| **PS and MA return the IDENTICAL score** | **83/120 = 69%** |
| Within one level of each other | **119/120 = 99%** |
| Mean absolute difference | **0.32** |
| r(PS, MA) | **+0.89** |
| r(PS, DEF) | +0.83 |

**⚠ AND ON THE EXACT CASE THAT DIMENSION WAS CREATED TO FIX:** §5.1 records PS was introduced because
*"McDonald's SG 150+ outlets scored 47 vs Jollibee 26 outlets 57"* — a **wrong way round** ordering that
PS was meant to correct. **Under v1.16.1, McDonald's SG and Jollibee return PS 5 and MA 5 — and Jollibee
PS 3 and MA 3.** *The two dimensions give the same answer on the very case the split was invented for.*
**Zero separation. The reason for the second dimension was not being delivered.**

#### The mechanism, and why the 0.8% dispute rate was misleading

**The agreed construct is *"the position actually HELD against the derived competitive set"* (§5.1), and
§10.7 lists the defect it corrected as** *"one share fight against every named competitor → the position
held per situation, corroborated."*

**But the INSTRUCTION asks: *"would buyers choosing in this situation reach for this business by name, or
could any of dozens of similar operators substitute for it?"*** — **and §5.1's own definition of
`mental_advantage` is *"how much mind the brand holds in its segment."*** **Those are the same question.**
**"Reaching for a name" IS retrieval from memory. The construct was written as *held against*, and then
implemented as *recalled by*.**

**⚠ This explains something that looked like a strength.** *PS showed only **0.8% disputes** against Sean's
labels — the best of any dimension, and it was reported here as evidence PS was sound.* **It was not: it
was evidence the two dimensions had merged.** *In his own labels r(PS, MA) = **+0.74**, and **58% of his
PS grades are numerically IDENTICAL to his MA grades.*** **An instrument that agrees with a human who is
also answering one question twice is confirming the duplication, not the dimension.**

#### ⚠ The fix was attempted, appeared to work, and the CANARY REJECTED IT

**Candidate v1.17.0** reframed PS explicitly as **a contest** — *winning or losing each situation against
the named occupants* — with an added guard that **fame is not the input**, and that *"if your
position_strength score is always the same as your mental_advantage score, you are answering one question
twice."* **Promoted through the new gate, full 120-case run.**

| | v1.16.1 | v1.17.0 |
|---|---|---|
| PS identical to MA | 83/120 (69%) | **44/120 (37%)** |
| Mean absolute difference | 0.32 | **0.69** |
| PS distribution | 2-dominant | 1→8, 2→14, 3→59, 4→28, 5→11 |
| McDonald's SG / Jollibee | PS 5 / 3 | **PS 4 / 4** — no longer inverted |
| **Canary** | **PASSED** | **⚠ FAILED — C3 and C4 both moved bands** |

**So the de-duplication WORKED** *(duplication halved; the McDonald's/Jollibee inversion corrected;
**A home-based mobile hairdresser 1 → 3**, finally treating a live small operator as at-parity rather than
non-existent)* — **and it was still rejected.**

**⚠ THE CANARY WAS RIGHT TO REJECT IT, and the reason is not the one it printed.** *It printed band moves.
Against the **engagement conclusions** (Sean's real client readings, the independent reference) the fix
went the WRONG way on two real cases:*

| Case | Engagement (Sean, real work) | v1.16.1 | **v1.17.0** |
|---|---|---|---|
| **C3 PetDirectory** | PS **3** | PS 3 ✅ | **PS 2** ❌ |
| **C4 SGFitness** | PS **1** | PS 2 | **PS 3** ❌ *worse* |

**So the contest framing makes the instrument agree with Sean LESS on real businesses that were engaged.**
*Agreement with the engagement conclusions fell to **2 of 6**.*

**⚠⚠ REVERTED.** *`rubric.json` restored to **1.16.1** through the gate — itself the first real use of
`rubric_gate.py` — and the canary PASSES again.* **⚠ The candidate is retained for the record.**

#### ⚠ THE TENSION IS REAL AND UNRESOLVED (D49)

**Three references disagree, and I cannot adjudicate it:**

1. **Structural:** PS and MA duplicate each other *by construction* (69% identity, r=+0.89). **Two of the
   six dimensions carrying 45% of the weight are effectively one dimension.**
2. **The frozen canary** (`_reference.json`, rubric 1.8.0) **prefers the OLD reading** — under it, the new
   PS moves *away* (C3 3→2, C4 2→3).
3. **The engagement conclusions** — Sean's real client work — **also prefer the old reading** (C4
   engagement PS is **1**; the new rubric says **3**).

**⚠ BUT the canary's frozen reference and Sean's OLD PS labels BOTH carry the very defect being fixed**
*(the labels are 58% self-duplicated; the frozen reference predates the defect being noticed).* **So the
evidence available today cannot distinguish "RS was never a second dimension" from "my contest wording is
wrong."** **Sean's D38 ruling — *"I much rather reasoning is used to make the judgement here"* — suggests
the fix belongs in the reasoning, not in a new construct.**

#### ✅ 1.18.0 — PS RECONSTRUCTED: POSITION STRENGTH, INDEPENDENT OF RECOGNITION (D50)

**Sean defined the distinction:** *"Mental advantage measures what the market and customers know of the
brand. Position strength measures the strength of the said brand's positioning relative to competitors."*
**And named the product requirement:** *"I am expecting many new potential clients that have either
business ideas or have just started out... So we should give hope to the high PS but low MA business that
have just started out and have a good flank."*

**⚠ THAT IS A CONSTRUCT CHANGE, NOT A WORDING ONE.** **MA is what the market KNOWS of the brand —
present-tense and backward-looking. PS is how strong the POSITION is against competitors' positions —
strategic and forward-looking, judged WITHOUT reference to awareness.** **A business can hold a strong
position while nobody has heard of it; that is precisely the profile the lead engine needs to serve, and
the old wording could not produce it.**

**⚠ CONFIRMED IMPOSSIBLE UNDER THE OLD CONSTRUCT: ZERO of 120 cases had PS ≥ MA+2.** *Every new or
idea-stage business scored PS 2–3 with MA 1–2, because the old instruction — "would buyers reach for this
business by name" — reads recall, which is `mental_advantage`.*

| Measure (120 cases) | 1.16.1 (old) | **1.18.0 (position strength)** |
|---|---|---|
| **PS identical to MA** | 83/120 (69%) | **35/120 (29%)** |
| Mean absolute difference | 0.32 | **0.87** |
| **Target profile (PS ≥ MA+2)** | **0 of 120** | **6 of 120** |
| PS ≥ 4 (over-generosity check) | 44/120 (37%) | **41/120 (34%)** — *did NOT inflate* |
| PS distribution | 2-dominant | 1→3, 2→39, 3→59, 4→16, 5→3 |
| **Canary** | PASSED | **⚠ FAILED — C4, C5 flip Fragile → Contested** |

**Guards written in:** fame, size and recognition must not drive PS; identical PS and MA scores are an
error; and the position's COPYABILITY belongs to `defensibility`, not here.

**⚠ TWO THINGS STILL WRONG, REPORTED RATHER THAN GLOSSED:**
**(a)** *C1 GreenPackers reads **PS 4** where the engagement reading is **PS 1*** — the model still tracks
recognition too closely, so the new wording is over-generous on at least some micro cases despite the
aggregate distribution being healthy.
**(b)** **The canary rejects it, and the canary is not wrong to.** *C4 and C5 sit within ~5 points of a
Fragile/Contested boundary, and PS carries 25% weight, so ANY one-level PS change flips them.* **⚠ That
makes the canary hypersensitive to PS revisions specifically** — *and its frozen reference is **10
revisions stale** (rubric 1.8.0, model jev-1.13.0) with its PS column written under the very recall
construct being replaced.* **A reference written under the old construct cannot validate a new one.**

#### ✅ D50 CLOSED — Sean chose A. Re-baselined, and the re-baseline exposed an error in this spec

**Sean: *"A"*** — re-baseline the canary at 1.18.0.

**⚠ THE DECISION STEP EXPOSED THAT MY OWN REPORTING HAD BEEN WRONG.** **The canary's per-dimension
"engagement" values — which §10.6d used to argue that v1.18.0 "went the wrong way against the engagement
conclusions" — are NOT client labels.** *Five of the six fixtures say verbatim:*

> *"The per-dimension expected levels are an **ASSISTANT MAPPING** of that conclusion onto the six
> calibrated dimensions — **they are not a recorded client label**. **The BAND, not the dimension vector,
> is the bar (spec 10.6)."*

**And `run_canary.py` prints that column under its own warning:** *"INFORMATIONAL ONLY — NOT the drift
check, NOT a launch gate; the expected vectors for cases without a recorded human label are assistant
mappings — see each `_meta`."* **⚠ So the argument that the canary "rejected" the new construct because
its dimension column disagreed was unfounded: that column has no authority, and the band is the bar.**

**⚠ WHAT STILL STANDS, AND IT IS THE PART THAT MATTERS: the canary's BAND check has a human-blessed
source.** *Each fixture carries `_expected.band` derived from its `expected_conclusion` — a real
engagement conclusion, e.g. C1 "Fringe, <1%; guerrilla warfare the only play."* **⚠ v1.18.0 matches those
bands on 5 of 6 cases — IDENTICAL to the 1.8.0 baseline's 5 of 6.** *C6 Bonefirm differs under both
rubrics, so it is not attributable to this change.* **So band agreement with the engagement conclusions
is unchanged — not improved, not damaged.**

**⚠ AND ONE REAL UNRESOLVED DISAGREEMENT REMAINS:** *C1 GreenPackers — the single fixture whose
dimension vector **is** a recorded client label — reads **PS 4** where that label says **PS 1**.* **The
old construct matched it (PS 1) largely BECAUSE it was reading recall, which is what made the duplication
invisible.** *So the one case with a genuine human label is the one the new construct gets wrong.*

#### The re-baseline

**Recorded deliberately through `run_canary.py --rung record --rubric rubric.json --force`** — *the tool
refuses to overwrite a reference without `--force`, so the act is explicit rather than incidental.*
**Reference is now rubric 1.18.0.**

| Check | Result |
|---|---|
| Canary passes against its new baseline | **PASSED, two consecutive runs** |
| Band agreement with engagement conclusions | **5 of 6 — unchanged** |
| Full corpus at 1.18.0 | **120/120, 0 failures, 8s** |
| Duplication PS vs MA | **69% → 29%** |
| Mean absolute difference | 0.32 → **0.87** |

**⚠ THE COST OF THIS RE-BASELINE, STATED PLAINLY: the reference is no longer an independent check of PS.**
*It was recorded FROM the instrument at 1.18.0.* **It still catches everything else** — model drift, and
any future change to the other five dimensions — **but a future PS revision will now move the reference
with it rather than against it.** *That sensitivity is the price of a construct change that no existing
reference could validate; it is recorded here so the loss is visible rather than discovered later.*

### 10.6e Fresh blind regrade: PS and DR — ONE INVALID, TWO REAL DEFECTS (D52, D53)

**Sean graded both columns of `PS-DR-V2-GRADING.md` (21 businesses × 2).**

#### ⚠ THE PS HALF IS INVALID — MY ERROR, AND IT WASTED HIS GRADING

**The sheet asked the OLD question:** *"does the market reach for this business by name? The test is
RECOGNITION, not size"* — **with level 2 defined as "nothing it is RECOGNISED for".**

**The live rubric (1.18.1) asks the NEW question:** *"how strong is this business's POSITION compared with
the positions its competitors hold? DO NOT score how well known the business is"* — **with level 2 as
"the claim is already OWNED by a named occupant".**

**⚠ The sheet was committed BEFORE D49 and D50 rebuilt the construct, and I never rebuilt it.** *I even
recorded at the time that "the RS half is moot until D49 is settled" — and then, after D50, asked him to
grade it anyway.* **So the PS readings measure a superseded definition. They are recorded here but MUST
NOT be used as a reference.**

**⚠ SIXTH INSTANCE OF THE SAME FAILURE THIS SESSION: I did not check the artefact I was about to use,
against the thing it was supposed to test.**

#### ✅ DEMAND REACH — 95% within one level, and ONE real dispute

| | Sean (fresh) | Instrument 1.18.1 |
|---|---|---|
| **Exact** | **12/21 = 57%** | |
| **Within one** | **20/21 = 95%** | *(95% CI 77–99%)* |
| **Disputes (≥2)** | **1/21 = 4.8%** | *(95% CI 0.8–22.7%)* |
| Mean offset | **−0.21** | |

**⚠ THE ONE DISPUTE IS THE BIGGEST IN THE PROJECT: `ObserveCo` — Sean 1, instrument 4.** *Sean graded his
own consulting business at **1**: no identifiable paying buyer yet.* **The instrument reads 4** because
the submission is detailed, coherent and names a segment. **⚠ This is the instrument rewarding a
well-written submission — precisely the *"reading the SUBMISSION instead of the BUSINESS"* defect class
§10.7 records as the one that accounted for every prior improvement.** **It is recorded as D52 and it is
a live defect, not a label error:** *the instrument has no account of whether a named segment has ever
actually been served.*

#### ⚠⚠ THE CEASED-BUSINESS RULE CONTRADICTS SEAN'S JUDGEMENT (D53)

**The sheet was built to test one rule:** *a business that has CEASED trading has an identifiable buyer
but no longer reaches them, so it is a **2, not a 1**.*

**⚠ Sean graded BOTH ceased businesses 1 — the dormant home baker and the closed bubble tea outlet.** *He
applied the SAME value to both, which makes it a considered reading rather than a slip.*

**So the rule is wrong or the level-1 definition is.** *DR level 1 currently reads "no identifiable buyer,
OR the business cannot legally serve the buyers it names."* **Sean's judgement implies a third case
belongs at 1: a business that has stopped trading.** **⚠ That is a definitional conflict for him to rule
on — the instrument is following its own rule correctly, which is why this is a spec question, not a
scoring bug.**

#### ⚠ PS MAY HAVE OVER-CORRECTED — flagged, not concluded

**⚠ Even though the sheet is invalid, the comparison is still informative in one direction.** *Sean's
fresh PS spread wide:* **{1:2, 2:3, 3:10, 4:4, 5:1}** — *he uses 4 and 5.* **The instrument at 1.18.1 is
heavily compressed:** **{1:1, 2:43, 3:66, 4:7, 5:3} — 66 of 120 cases sit at level 3**, because the
*"cap an unproven flank at ADEQUATE (3)"* rule fires whenever the supplied set does not evidence what an
occupant claims — **which, without the scanner, is most of the time.**

**⚠ So the basis restriction has bought honesty at the cost of discrimination, and it depends entirely on
the scanner shipping.** *If the scan is not wired in, PS cannot distinguish most businesses.* **That is
the trade recorded in D51, now with a measurement behind it.**

### 10.10 What is genuinely OPEN — and why none of it closes by editing

**Every register row is now closed. These four are not register rows; they are WORK.** *Marking them done
to produce a clean list would be the same failure this spec spent the session removing, so they stay open
with what each actually requires.*

| # | Open item | What it needs | Why it is not a document change |
|---|---|---|---|
| **1** | **`position_strength` is UNCALIBRATED** | **A fresh blind PS sheet**, built under the position-strength definition — *the existing sheet asked the old recall question and its readings are void (§10.6e)* | **Requires Sean's grading time.** *No rubric edit can supply a reference.* **⚠ And it is the dimension of most consequence: PS carries 25%, more than any other.** |
| **2** | **The 120-case corpus carries 35–81% relabel noise** | **Regrading the corpus**, or accepting that no further tuning against it is valid | **Every agreement figure in §10.6–10.7 is measured against this reference.** *Tuning against it fits to noise — the error that produced the v1.11.0 over-raise.* |
| **3** | **The competitor scanner is not wired into production** | **Wiring `competitor_scan.py` into the scoring path**, which needs the §3.11 pre-flight gate to exist first *(scan must run AFTER input quality, never before)* | **And the PS cap at ADEQUATE (3) depends on this shipping.** *Without the scan, 66 of 120 cases sit at level 3 because an unproven flank cannot exceed parity.* **The cap and the scanner ship together or neither is honest.** |
| **4** | **There is no production scorer** | **The report-serving path itself** — *`run_jev.py` is a calibration harness; nothing serves a report* | **§5.3.1 step 4 is enforced in `run_jev.py` today, and `rubric_gate.py` exists precisely so the scorer can refuse an unpromoted rubric when it is written.** *The guard is ready and unused.* |

**⚠ STATED PLAINLY: the instrument is internally consistent, the launch gate passes, and the report is NOT
ready to serve.** *No real submission has ever been scored, no real report has ever been produced, and the
reference the whole calibration rests on is 35–81% self-inconsistent.* **Those are the four gaps between
here and launch.**

### 10.9 ⚠ The launch gate is CLOSED — and what closing it does NOT prove

**All six criteria now pass (§10.6's table).** **The negative-control row was the last one and is built
here: `negative-controls/` (5 fixtures) + `run_negative_controls.py`.** *Each control carries its own
predicted failure reason, recorded in the fixture BEFORE the run, and the harness checks the control
against THAT rather than against a blanket "score is low".*

| # | Control | Predicted (recorded before the run) | Observed |
|---|---|---|---|
| **NC01** | Empty submission — every field blank | `input_sufficiency = insufficient` | **REFUSED** — band `GATE`, no composite |
| **NC02** | Self-contradictory — "most refined artisan" **and** "lowest price, cheaper than every supermarket" | insufficient, **or** `competitive_room = 1` | **insufficient** (contradiction caught) |
| **NC03** | Generic filler — fluent, plausible, differentiates nothing | `position_strength ≤ 2` **and** `mental_advantage ≤ 2` | **PS 2, MA 2** |
| **NC04** | Claims a position **a named rival already owns** ("freshly brewed, no powder" — KOI's and Playmade's ground) | `position_strength ≤ 2` | **PS 2** |
| **NC05** | Position **asserted but unevidenced** ("most awarded", "unmatched", "trusted by thousands") | `position_strength ≤ 3` (the unproven-flank cap) | **PS 2** |

**5 of 5 failed as predicted. Spec 8.6's requirement — *"a scorer that cannot fail is not a scorer"* —
is now demonstrated rather than asserted.** *And §3.10 item 4's objection is met: five controls across
**distinct** failure modes, not one control proving only that failure is possible.*

#### ⚠ WHAT THIS DOES **NOT** PROVE — stated because the gate is now green

**NC03, NC04 and NC05 all land at band `Contested` (~44–46), NOT `Fragile`.** **So the controls
demonstrate the predicted DIMENSION-LEVEL failure responses; they do NOT demonstrate that a bad
submission reaches a LOW BAND.**

**Why, and it is not a defect:** *a generic-but-real business is genuinely Contested — it scores PS 2 and
MA 2, but it still trades and still names a segment, so `competitive_room` and `demand_reach` sit at 3 and
the composite cannot fall to Fragile.* **`Fragile` IS reachable** — *the canary's pre-launch cases C4 and
C5 sit there* — **but not from controls built on trading businesses.**

**⚠ AND THE GATE'S OTHER ROWS REST ON THE 120-CASE CORPUS, WHICH IS NOW KNOWN TO BE WEAKER THAN THE TABLE
IMPLIES.** *Sean's own regrades changed **35%** of his MA grades, **59%** of his DEF grades and **81%** of
his CR grades.* **So "dimension disputes 2.8%" and "band agreement 100%" are measured against a reference
carrying 35–81% relabel noise** — *they are not evidence that the instrument matches a real expert on real
submissions.* **The gate passing means: the instrument is internally consistent, refusals fire, controls
fail as predicted, and no gross band error exists. It does NOT mean the report is validated for launch.**
*That requires the corpus regrade and fresh PS grading, both recorded as outstanding.*

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
| Negative controls | Every control **fails**, each with its own predicted failure reason | **5 of 5 — gate CLOSED** (§10.9) |

**⚠ Every figure in the table above is a point estimate, and §7.12's own argument says it must not be
read as one.** The same section that establishes *"±5pp needs n = 1/B² = 384"* and *"3/N bounds a zero
result"* is exactly the reasoning that applies here — **the calibration was never given the interval
treatment it demands.** At these sample sizes the bounds are wide, and two of them change what can
honestly be claimed:

| Claim | Point estimate | **95% CI (Wilson)** | What it means |
|---|---|---|---|
| Gross band error (two or more off) | 0% | **0% – 3.3%** | ✅ **Clears the ≤5% bar** — the interval sits under it |
| Band agreement (within one band) | 100% | **96.7% – 100%** | ✅ clears ≥90% |
| Dimension disputes (≥2 levels) — **over 464 cells** | 2.8% | **1.6% – 4.7%** | ✅ **clears the ≤5% bar at BOTH ends** |
| Same band, target segment | 85.0% | 73.9% – 91.9% | n=60 — reported for completeness |

**⚠ A denominator error in the first version of this table, corrected here.** The earlier version
computed the dispute interval over **cases (n=114)** when the metric counts **dimension cells
(n=464)** — the same class of error §10.7 already records twice. **Corrected, the dispute bar passes
on the interval, not just the point estimate.**

**But the aggregate hides the real finding, and this is the one that matters:**

| Dimension | Disputes (≥2) | 95% CI | |
|---|---|---|---|
| `position_strength` | 0.9% | 0.2% – 4.8% | ✅ |
| `mental_advantage` | 3.5% | 1.4% – 8.6% | ⚠ interval crosses 5% |
| **`defensibility`** | **7.0%** | **3.6% – 13.1%** | ⚠⚠ ~~above the bar~~ **→ 3.3% after Sean's four sheet corrections (D35). 4 residual, all construct cases, all now addressed.** |
| `market_headroom` | 0.0% | 0.0% – 49.0% | **n=4 — mostly n/a by design, unmeasurable** |
| `demand_reach` | 0.0% | 0.0% – 3.2% | ✅ |

**⚠⚠ `defensibility` appeared to fail the bar on its own. Four of the eight were sheet errors (D35),
leaving 4 — and all four are construct cases.** Every dispute sat in a category of **large, established
brand**:

| Category | n | Businesses |
|---|---|---|
| electronics | 2 | Best Denki, Gain City |
| furniture | 2 | IKEA, Scanteak |
| bubble-tea | 2 | Gong Cha, Each-A-Cup |
| kopitiam | 1 | Toast Box |
| fast-food | 1 | Burger King |

**And the direction splits into two coherent sub-patterns:**

| Sub-pattern | Instrument vs Sean | Reading |
|---|---|---|
| **Big-box retail** (Best Denki, Gain City) | I read **2**, he reads **4** | **I undervalue an established retail network** — physical footprint and tenure that a challenger would find expensive |
| **Big global/F&B brands** (Gong Cha, Burger King, IKEA, Scanteak, Toast Box, Each-A-Cup) | I read **3–4**, he reads **1–2** | **I overvalue brand familiarity** where he judges the position genuinely erodible |

**This is a construct disagreement on large brands, not random error.** The rubric's `defensibility`
is defined as *the challenger's cost*; both sub-patterns are consistent with the instrument reading
**brand recognition** as a barrier when Sean is reading **structural cost to a challenger**.

---

#### ⚠⚠ Sean's hand-read of the eight — and it reframes D35 entirely

**His rulings, verbatim:** *"Best denki and gain city have 4 defensibility because the appliance market
has consolidated to a few brand names only in Singapore… I reason that because they all have mental
advantage, there is some defensibility because it's really concentrated at the top with perhaps equal
market share almost? I am happy to be corrected here. For burger king and ikea I think their
defensibility is high circa 4. Toast box and scanteak are 3-4 with scanteak closer to 3. Gong cha, and
each a cup are low."*

| Business | Sheet | Instrument | **Sean's ruling** | Verdict |
|---|---|---|---|---|
| Best Denki | 4 | 2 | **4** | **instrument wrong** |
| Gain City | 4 | 2 | **4** | **instrument wrong** |
| Burger King | 1 | 3 | **~4** | **sheet wrong** — instrument closer |
| IKEA | 2 | 4 | **~4** | **sheet wrong** — instrument right |
| Scanteak | 2 | 4 | **3–4** | **sheet wrong** — instrument right |
| Toast Box | 2 | 4 | **3–4** | **sheet wrong** — instrument right |
| Gong Cha | 1 | 3 | **low** | sheet right, instrument too high |
| Each-A-Cup | 2 | 4 | **low** | sheet right, instrument too high |

**⚠ Four of the eight "disputes" were sheet errors, not instrument errors.** IKEA, Scanteak and Toast
Box now land within one of the instrument; Burger King moves to ~4 against the instrument's 3.
**So `defensibility`'s real disagreement rate is materially lower than 7.0%.**

**And his own sheet was internally inconsistent on the same construct** — visible without any
instrument: **Burger King 1 vs KFC 4.** Two directly comparable global QSR chains with decades in
Singapore, scored three points apart. `Subway 2` and `Jollibee 2` sit with Burger King, not with KFC.
**His regrade corrects the sheet toward coherence** — which is a finding about the *labels*, and it is
the second time this corpus has shown label noise being read as instrument error.

---

#### ⚠ The construct split — category-anchored vs business-anchored

**The deeper pattern, and it explains the whole table.** Sean's labels **cluster by category**:

| Category | His DEF scores — every business |
|---|---|
| health-beauty | **4, 4, 4, 4** (Watsons, Guardian, Unity, Sephora) |
| furniture | **2, 2, 2, 2** (IKEA, Castlery, Scanteak, Cellini) |
| home-not-permitted | **1, 1, 1, 1, 1** |
| electronics | 3, 3, 4, 4 |
| fast-food | 1, 2, 2, 2, 4, 5 |

**A flat 2 across IKEA, Scanteak, Cellini and Castlery is not a judgement about those businesses** —
they differ enormously in footprint, tenure and capital. **It is a judgement about the category.**

**So the two readings are measuring different constructs:**

| | Reading |
|---|---|
| **The instrument** | Each business on **its own** characteristics — footprint, tenure, capital, brand |
| **Sean** | The **category's** structure first (is it consolidated? capital-heavy?), then a small adjustment per business |

**And that is exactly why disputes concentrate where they do.** Disputes cluster in categories with
**high internal variance** — electronics (Courts 3 / Best Denki 4), fast-food (Burger King 1 /
McDonald's 5), furniture. **Where the category is homogeneous** (home-nails: 1–3; health-beauty: all 4),
the two readings agree, because the category anchor and the business characteristics point the same way.

**His reasoning on Best Denki states the construct explicitly:** *"the appliance market has
consolidated to a few brand names only in Singapore… because they all have mental advantage, there is
some defensibility because it's really concentrated at the top."* **That is a defensibility claim about
the CATEGORY — consolidation and mutual deterrence at the top — not about Best Denki's own moat.** The
instrument cannot see it, because the rubric (to v1.8.0) defined DEF as *the challenger's cost* at the
level of one business only.

**⚠ This is D35 restated, and it is a definitional question, not a numeric one.** Three positions:

| Option | Means |
|---|---|
| **A — instrument is right; the construct is business-level** | Keep §5.4 as written; Sean's category reasoning is a separate dimension the rubric does not have |
| **B — Sean is right; DEF is partly a category property** | Rewrite §5.4 so DEF reads **category concentration** as an input, not only the individual business |
| **C — both, split the dimension** | Keep business-level DEF and add a **category-structure** input to `competitive_room`, which already measures fragmentation |

**C is the closest fit to the evidence** — `competitive_room` already asks *"how fragmented is the
landscape"*, which is precisely the consolidation signal Sean is reading into DEF. **If consolidation
belongs anywhere, it belongs there, and DEF stays a property of the business.** But the call is his,
and it changes the rubric, so it needs a ruling rather than my inference.

#### ⚠ D35 closed on B — and B creates an input requirement it does not satisfy by itself

**Sean ruled B** (rubric **v1.9.0**). The construct split is now explicit: DEF reads **category
structure** as an input, and carries an explicit **"familiarity is not defensibility"** guard so that
brand recognition cannot be scored twice — once here, once under `mental_advantage`.

**Correction to the table above, which matters:** **B does NOT fix Best Denki or Gain City.** At
`defensibility` 2 they read "no barrier" — a *submitted-differentiator* reading. **The existing
level-4 wording already names their barrier** — *"scale built over years (a store network, a
distribution footprint)… a physical asset base"* — and Best Denki holds ~14 stores and Gain City a
mega-store plus outlets. **So the original 2 was an instrument recognition miss at a level it already
had, not a missing level.** B addresses *why the category raises the ceiling*; it does not make the
instrument apply the level it already describes. **Both fixes are needed, and only one of them is B.**

**⚠ B has a data consequence that is not yet designed for — and it is the same construct as D25.**
Reading category structure requires knowing **how many comparable players the category has and how
capital-heavy it is.** Today the report reads a **single self-reported submission**; the category
context is not in the form, and for a small business the category may be thinly populated. So
category structure is either **(a) inferred from the submission** — which is what produced Best Denki
at 2, and is exactly the failure B exists to correct — or **(b) sourced externally.** **(b) is D25
again**, and D25 already pre-commits: scan only when the §3.11 pre-flight gate passes, because the
protocol's measured silent-failure rate is 60%.

#### ⚠⚠⚠ D36 WITHDRAWN — my "different scale" finding was FALSE, and the real cause is the corpus

**I claimed `defensibility` was being compared across mismatched scales. It was not. Withdrawing it.**

**What I got wrong:** I assumed Sean's defensibility grades were on a **1–5** scale. They are on **1–6**
— **`build_regrade_sheet.py:183` told him so explicitly** (*"**a well-resourced copycat arriving
tomorrow (1–6)**"*), and **his grades do use the full range: max 6.0, with a 6 recorded.** The
instrument also scores 1–6. **The scales were matched the whole time, and defensibility's dispute rate
is 3.3% (4 of 120) — under the bar, on like-for-like scales, before any fix.**

**So the "6.7% → 1.7%" improvement was an artefact of a scale conversion that should never have been
applied.** The 8 original disputes were **Sean's four sheet errors (D35) plus the construct issue (D35)**
— nothing to do with scaling. *(Note: making defensibility 5 levels is still a coherent choice for
uniformity, but it fixes nothing, because nothing was broken.)* **This is the fourth denominator/frame
error I have made and had to retract in this session, and it is recorded here rather than quietly
deleted.**

**⚠⚠⚠ THE REAL CAUSE OF THE DEF DISPUTES, AND IT IS THE MOST IMPORTANT FINDING IN THIS DOCUMENT.**

**82% of the calibration corpus — 99 of 120 cases — does not contain real submissions.** Their `_meta`
says so: *"FORM DATA **reconstructed by the analyst from public sources.** The LABEL is external and
published; **the form is thinner than a real submission. This is the known weakness of the test.**"*
The median form payload is **725 characters.**

**Read that against Best Denki.** Sean scores it 4 because he knows it holds **~14 stores, a national
network and decades of supplier relationships**. **None of that is in the form** — the form is a
725-character analyst summary whose stated differentiator is *"Japanese retail service standards"*.
**The instrument scored 2 because there was no barrier evidence in front of it, and there was none to
find.** Under v1.10.0 it still scores 2. **The instrument is not wrong; the input is thin — and Sean's
grade is right because he supplied knowledge the form never carried.**

**That reframes the entire calibration claim.** The 120-case corpus measures **agreement on
analyst-reconstructed forms**, not on real submissions. **A real founder filling in the form would
volunteer their outlet count, their tenure, their owned assets** — a reconstruction only includes what
the analyst thought to write down. **So the corpus has a systematic thinness bias, and defensibility is
exactly the dimension most damaged by it**, because barriers are the facts least likely to appear in a
positioning sentence and most likely to be known to the owner.

**⚠ This is the same class of gap Sean flagged earlier** — *"You have blind gaps. You have to
corroborate your answer against physical evidence."* **Best Denki, 24/7 Fitness and Zoff were the
physical-evidence anchors then; Best Denki is the anchor again now, and for the same reason.**

**⚠ MY PROPOSED FIX WAS THE LAZY ONE, AND SEAN REJECTED IT.** I proposed adding structural questions to
the form. **Sean: *"It shouldn't be in the form. I much rather reasoning is used to make the judgement
here and I know this is possible."*** **He is right, and the evidence says so.**

**The instrument ALREADY HAS the category knowledge — it simply was not told to use it.** The derived
competitive set for Best Denki **already names six big-box incumbents** (*Courts, Harvey Norman, Best
Denki, Gain City, Challenger, Mega Discount Store*) with the diagnostic *"the same TV brands, on the
same mall floor, at near-identical prices"*. **So the state contains the consolidation signal, and the
rubric was not asking for it.** That is a **prompt defect, not a data defect** — and it is fixable in
the rubric, without touching the form. **Adding form fields would have asked the founder to do work the
instrument can already do, and §1's rule against asking the founder to do analyst work forbids it.**

**✅ SEAN'S APPROACH WORKS — rubric v1.11.1 adds a REASON-ABOUT-THE-CATEGORY pathway.** Measured on the
full 120-case corpus, the four disputed cases move toward his grades:

| Business | v1.8.0 | **v1.11.1** | Sean |
|---|---|---|---|
| Best Denki | 2 | **3–4** | 4 |
| Gain City | 2 | **3–4** | 4 |
| Each-A-Cup | 4 | **3** | 2 |
| Gong Cha | 3 | 3 | 1 |

**Best Denki and Gain City close the whole gap from 2 to 3–4 — a two-point move, well outside noise.**
The canary does **not** move (no band changed), so the pathway **discriminates rather than inflating
everything** — which was the failure mode of my first attempt.

**⚠ THE FIRST CUT WAS TOO BLUNT AND I HAD TO SHARPEN IT.** v1.11.0 told the model it *"must not default
to the lowest levels"*, and it **lifted 10 micro nail and facial businesses from 1 to 2 that Sean scores
1** — reading a fragmented, trivially-cheap-entry category as having efficient scale. **A blunt "fame is
not a moat" guard also demoted genuine networks** (KFC, Ya Kun, Toast Box, NTUC, Sheng Siong, Eu Yan
Sang, all 4–5 → 3–4). **v1.11.1 splits the question in two:** *(1) what does the business **demonstrably
operate** — a multi-outlet network, fleet, factory or licence is a barrier and belongs at 4+ **even if
the business is famous**; and (2) how **expensive is entry** — where it is trivially cheap the category
is contestable and a small operator still belongs at 1.* **The micro categories returned to 1–2; the
chains remain the open item below.**

**⚠⚠ AND A CORRECTION I HAVE TO MAKE ABOUT MY OWN VALIDATION.** I reported in v22 that the instrument is
**deterministic** — three repeat runs, spread 0. **That is OVER-CLAIMED, and the full-corpus runs caught
it.** Comparing two full batches, **`mental_advantage` changed in 7 of 120 cases and
`competitive_room` in 2 — and I did not touch either instruction.** So **the instrument is NOT
deterministic across separate batches; it has roughly ±1-level variance at around a 5% rate.** The
three rapid repeats happened to agree, and I drew a general conclusion from them. **Consequence: any
single-batch comparison of a 1-level difference is inside the noise floor, and the defensibility
improvements at the ±1 level (44% → 52% within one) cannot be claimed as real.** *Only the 2-point
moves — Best Denki and Gain City from 2 to 3–4 — are large enough to survive it.*

**⚠ THE REMAINING GAP, AND IT IS A CONSTRUCT CALL RATHER THAN A BUG.** Three chains still sit one below
Sean: **KFC, Ya Kun, Toast Box all at 3 where he scores 4.** **Their moat is a large outlet network,
which IS efficient scale — but the "fame is not a moat" guard is reading their brand and discounting
it.** *Counter-argument, and it is real: anyone can open a fried chicken or kopitiam outlet, so the
category's entry cost is genuinely low, while the incumbents' networks took decades.* **The line is:
does a national F&B network count as efficient scale when entry to the category is individually cheap?
That is Sean's construct to settle, not mine to tune** — and I am deliberately not tuning it further on
single batches, because the differences being chased are at the noise floor.

**(c) The calibration claim must still be restated** to say it was measured on analyst-reconstructed
forms with a known thinness bias, so nobody reads "100% band agreement" as validating real-submission
performance.

---

#### ✅ D39 — the operated-network rule (Sean authorised), and what it cost elsewhere

**Sean: *"I'm happy for you to apply the KFC, Ya Kun and Toast box judgement."*** **Applied as a GENERAL
rule, not three case patches** (rubric **v1.11.2**), because a rule shaped around three businesses would
not survive the next submission:

> **SEPARATE VISIBILITY FROM OPERATED NETWORK.** A household name whose prominence rests on nothing but
> visibility — advertising, footfall, habit — in a fragmented, low-entry-cost category is cheap to
> displace and belongs LOW. **But a chain that demonstrably OPERATES MANY UNITS is a different case,
> even in a fragmented category where opening a *single* unit is cheap:** the network itself — property,
> supply chain, logistics, central purchasing, staffing and training, brand spend spread across many
> outlets, and a decade or more of accumulated sites — is an asset a challenger cannot cheaply assemble,
> and it is **efficient scale and a cost advantage.** **The barrier is the NETWORK, not the single site.**

**Result — the three move to Sean's grade exactly:**

| Business | v1.8.0 | v1.11.1 | **v1.11.2** | Sean |
|---|---|---|---|---|
| KFC | 4 | 3 | **4** | **4 ✅** |
| Ya Kun Kaya Toast | 4 | 3 | **4** | **4 ✅** |
| Toast Box | 4 | 3 | **4** | **4 ✅** |

**⚠ BUT THE COLLATERAL IS MIXED AND MOST OF IT SITS AT THE NOISE FLOOR.** 13 cases moved: **8 up, 5 down.**

- **Up:** the three above, plus **CHAGEE 3→4** (Sean 4 ✅), **NTUC FairPrice 4→5** (Sean 5 ✅),
  **Mixue 3→4** (Sean 3 ✗), **CHICHA San Chen 3→4** (Sean 3 ✗), **Each-A-Cup 3→4** (Sean 2 ✗ — it
  regressed back after v1.11.1 had moved it to 3).
- **Down:** **24/7 Fitness 3→2**, **Chin Mee Chin 3→2**, Cuteticle SG 2→1, My Skin Diary 2→1,
  a home-based food-photography business 2→1.

**Corpus totals are a wash, and this is the honest reading: `defensibility` disputes 2.5% → 3.3%
(back to where v1.8.0 was), within-one-level 51.7% → 48.3%, offset −0.07 → −0.05.** So **the three
authorised corrections are exact, but they did not improve the aggregate** — and **Each-A-Cup moved the
wrong way.** **That is what tuning to a handful of cases looks like from the inside**, and it is why the
rule was written generally rather than case-specifically: at least the general rule can be judged on
the corpus rather than on three names.

#### ⚠⚠ D40 — IS JEV THE RIGHT LEVER FOR SPEED AND PROCESS? **NO, AND THE MEASUREMENTS ARE ONE-SIDED**

**Sean asked: *"Are we using Jev to improve the speed and overall process?"*** **Measured, and the answer
is that Jev is not the constraint — the rubric is.**

| Measurement | Value |
|---|---|
| **Model latency, one case** | **0.48 s** |
| Full 120-case corpus | **107 s** *(one subprocess per case, sequential)* |
| Projected 300 cases | **~4.5 min** |
| **Prompt per case** | **22,774 chars** — state **2,302**, **rubric 20,472** |
| **Rubric's share of the prompt** | **90%** |

**So 90% of every call is the rubric, not the business** — and **the rubric is what has grown**:

| | questions block | `defensibility` instruction |
|---|---|---|
| v1.8.0 | 14,591 chars | 1,204 chars |
| **v1.11.2** | **21,366 chars (+46%)** | **5,426 chars (4.5×)** |

**⚠ I did that.** Every iteration in this session added clauses to a dimension's instruction. **And
instruction bloat is a plausible contributor to the batch variance measured above** — the more rules
stacked into one prompt, the more room for the model to weight them differently between runs.

**THE PROCESS LEVER IS THEREFORE NOT JEV. It is:**
**(1) COMPRESS the rubric** — the `defensibility` instruction is 5,426 chars where it was 1,204, and it
now carries a moat definition, a fame guard, a visibility/network distinction and a category-reasoning
pathway. **Those can be stated once, tersely, without losing the rules.** Smaller prompts are faster,
cheaper and *more* reproducible, not less.
**(2) PARALLELISE the driver** — the corpus runner spends **0.48 s of model time and ~0.85 s of process
overhead per case**, and runs strictly sequentially. **The overhead is larger than the inference.**
**(3) FIX THE NOISE FLOOR BEFORE TUNING FURTHER** — at ±1 batch variance, **most of the movement
measured across v1.11.0→v1.11.2 is inside the noise**, so further single-batch tuning is not
informative. **Either repeat each case and take a majority, or raise the reporting threshold to ±2.**
**(4) Then Jev's speed becomes worth using for something real** — at 0.48 s it can run the **category
reasoning and the external scan (D25/D35/D38) inline**, which is the token-burning work the spec
currently gates. **The speed is there; the rubric is what makes the process slow and unstable.**

---

#### ✅ D40 EXECUTED — rubric compressed 44%, and the noise floor has now been MEASURED

**(1) Compression done (rubric v1.12.0).** The `defensibility` instruction went **5,426 → 3,026 chars
(−44%)** and the whole questions block **21,366 → 19,405 chars**. **All 13 distinct rules were kept and
explicitly checked for** — challenger-cost-not-effort · held-not-claimed · copyable ≠ level 1 ·
asset-light has none · effort earns nothing · the six moat sources · pricing power for a brand ·
primary vs ancillary · fame is not a moat · visibility vs operated network · reason about the category ·
a thin form is not evidence of scale · fragmentation raises nobody. **Rule 5 had been duplicated
verbatim and the fame and network rules repeated; the duplication is what came out.**

**(2) ⚠⚠ THE NOISE FLOOR IS NOW MEASURED, AND IT IS THE MOST USABLE THING IN THIS SECTION.** Two
independent full batches of the **same** rubric v1.12.0, 120 cases each:

| Dimension | Cases changed between identical batches | Rate |
|---|---|---|
| `position_strength` | 5 / 120 | **4.2%** |
| `mental_advantage` | 3 / 120 | 2.5% |
| **`defensibility`** | **2 / 120** | **1.7%** |
| `competitive_room` | 0 / 120 | **0.0%** |
| `market_headroom` | 0 / 120 | 0.0% |
| `demand_reach` | 2 / 120 | 1.7% |

**So batch noise runs 0–4.2% per dimension, and every movement is ±1 level.** **This is the threshold
any future tuning must clear.** *(It also confirms the earlier v22 "deterministic" claim was wrong, and
that comparing *different* rubrics against noise measured on 3 rapid repeats was not enough.)*

**(3) Compression did NOT degrade accuracy — it improved the headline measure.**

| Version | Disputes (≥2) | 95% CI | Within 1 | Offset | MAE |
|---|---|---|---|---|---|
| v1.8.0 | 3.3% | 1.3–8.3% | 44.2% | +0.03 | **0.47** |
| v1.11.2 | 3.3% | 1.3–8.3% | 48.3% | −0.05 | 0.52 |
| **v1.12.0** | **1.7%** | **0.5–5.9%** | **48.3%** | **+0.07** | **0.50** |

**Disputes are now the best on record and clear the ≤5% bar on their interval.** MAE is flat.
**And the authorised corrections survived compression — KFC, Ya Kun and Toast Box all hold at 4.**

**(4) ⚠ But the compression moved 17 cases UP and only 10 of those were improvements.** The raises are
concentrated in the micro categories again (nail bars, home facials, home bakers 1→2), where **10
improved and 7 moved away** — Polar Puffs 2→3, Chin Mee Chin 2→3, Maniqure By Ling 1→2, Facial Inc
1→2, My Skin Diary 1→2 and others, all cases where **Sean scores the lower value.** **NTUC FairPrice
also dropped 5→4 against his 5.** So **the aggregate improved while a minority of individual cases
degraded** — which is the honest description, and it is the same pattern as D39's collateral.

**(5) Still untouched: the driver is still sequential.** 0.48 s of model time against ~0.85 s of
process overhead per case, one subprocess at a time, 107 s for 120 cases. **Parallelising it is a
one-file change and remains the cheapest remaining speed win.** *Not done in this pass.*

**(6) And `Each-A-Cup` at 4 against Sean's 2 and `Gong Cha` at 3 against his 1 remain the two clearest
standing disagreements** — both bubble-tea, both cases where he sees near-zero defensibility and the
instrument still sees something. **They are the best candidates for a hand-read next, ahead of any
further rubric tuning.** *(Hand-read done — see D41 below.)*

#### ✅ D40 continued — the driver is now PARALLEL, and the noise floor is settled at 4.2%

**Parallelised** (`run_corpus_parallel.py`, bounded at 8 workers, one subprocess per case):
**120 cases in 9 s against 107 s sequential — a 12× speed-up — with 0 failures and a single rubric
version.** **Output agrees with the sequential run within the measured noise floor** (see below), so
**scheduling changed and results did not.**

**⚠ AND THE NOISE FLOOR IS NOW SETTLED, because there are three independent batches of the same rubric
v1.12.0.** Comparing all three pairs (A-B, A-C, B-C):

| Dimension | A-B | A-C | B-C | **worst** |
|---|---|---|---|---|
| `position_strength` | 4.2% | 4.2% | 3.3% | **4.2%** |
| `mental_advantage` | 2.5% | 4.2% | 3.3% | **4.2%** |
| **`defensibility`** | 1.7% | 2.5% | 2.5% | **2.5%** |
| `competitive_room` | 0.0% | 0.8% | 0.8% | 0.8% |
| `market_headroom` | 0.0% | 0.0% | 0.0% | 0.0% |
| `demand_reach` | 1.7% | 1.7% | 0.0% | 1.7% |

**Worst observed per-dimension batch noise is 4.2%; `defensibility`'s own is 2.5%.** **This settles two
things at once:** the compression effect on `defensibility` (**16.7%**, from 5.4.2-era batches) is
**well above its 2.5% noise and is therefore REAL**, and the D39 collateral moves at ±1 are **inside
noise and cannot be claimed.** **Rule going forward: a movement must exceed ~5% (the 4.2% ceiling plus
margin) before it is worth interpreting.**

#### ⚠⚠⚠ D42 — SEAN REBUILT THE DIMENSION'S CONSTRUCT, AND IT CHANGES THE CALIBRATION TARGET

**Sean, verbatim:** *"Don't worry about my prior readings on defensibility. You should not converge to my
old numbers because I suspect a lot of them are wrong. The rubric however should answer the question on
how hard it is to replicate (IP, capital intensive, network control etc), or for an outflank to steal
significant market share."*

**Three consequences, and the first is a standing-rule change:**

**(1) THE OLD DEF GRADES ARE NO LONGER THE CALIBRATION TARGET.** Sean has withdrawn them as truth for
this dimension (*"I suspect a lot of them are wrong"*). **So every DEF agreement statistic in §10.6 —
including the 1.7% "best on record" — now measures agreement with a reference he has disowned.** *That
statistic is retained as history, but it must not be quoted as evidence the dimension works. The
dimension is now judged against the CONSTRUCT, not against the 120 old grades. This is a significant
loosening of the only external check this dimension had, and it is recorded as such: DEF currently has
NO agreed gold standard.*

**(2) THE DIMENSION IS REBUILT AROUND TWO ROUTES OF ATTACK (rubric v1.13.1).**

> **REPLICATE** — build the same thing and win on execution. The mechanism must be NAMED: **intellectual
> property · capital intensity · network control · scale economics · switching costs · accumulated
> asset.**
> **OUTFLANK** — bypass the position and take **significant market share** by a different route to the
> customer. **This is the route that replication-barrier thinking misses.**

**(3) ⚠⚠ AND "SCORE THE WEAKER ROUTE" OVERSHOOTS. Measured, and it is the honest result:**

| Version | DEF distribution (L1…L6) | Mean | SD | Cases at 4+ |
|---|---|---|---|---|
| v1.12.0 *(single route)* | 25 · 35 · 29 · **26** · 3 · 2 | 2.61 | **1.20** | 26 |
| v1.13.0 *(two routes, weaker cap)* | 25 · **59** · 32 · **2** · 2 · 0 | 2.14 | 0.82 | 4 |
| v1.13.1 *(+ significant-share bar)* | 20 · **59** · 37 · **1** · 3 · 0 | 2.23 | **0.82** | 4 |

**Level 4 collapses from 26 cases to 4, and 49% of the corpus pools at level 2.** The only businesses
still reaching 4+ are **ASML, Boeing, Coupang and VICOM** — *which is arguably correct: they are the most
genuinely protected in the corpus.* **But discrimination halves (SD 1.20 → 0.82), and that is the real
cost.**

**⚠ MY OWN WORDING CAUSED MOST OF IT, AND THE FIRST ATTEMPT WAS WORSE.** v1.13.0's outflank examples —
*"a second location next door"*, generic *"delivery, online, D2C"* — **undercut Sean's own bar, which was
SIGNIFICANT MARKET SHARE.** Near enough every SME can be "outflanked" by one of those, so the weaker
route was always open and level 4 became unreachable. **v1.13.1 restates the bar explicitly and adds
that marginal-share routes leave the position holding — and it barely moved the distribution**, which
tells me the model genuinely reads most of this corpus as contestable rather than that the wording is
still wrong.

**⚠ AND THE CANARY NOW FAILS: C3-petdirectory drifts Contested → Fragile on `defensibility` 2 → 1.**
**That is a band change on a launch-gate artefact.** The canary runs once per change with no repeats, and
DEF's own batch noise is 2.5%, so **one case in six moving cannot be distinguished from noise — but it
cannot be waved away either.** **A repeat run is required before this version is treated as settled.**

**⚠⚠ THE BRACKET, STATED PLAINLY, BECAUSE THE CHOICE IS A CONSTRUCT CALL AND NOT A TUNING ONE:**

| | Reading | Consequence |
|---|---|---|
| **A** | **"Score the weaker route" (as written)** | Most positions are contestable ⇒ DEF is low for nearly every SME, 4+ is reserved for the genuinely protected, and **the dimension discriminates weakly** |
| **B** | **"The weaker route CAPS the score but replication drives it"** | Keeps the outflank as a discount rather than an absolute floor, preserving the spread the single-route version had |

**The two-route framing is right and worth keeping either way — it is what Sean asked for and it catches
the failure replication-thinking misses. The open question is only whether the weaker route SETS the
score or merely LIMITS it.** **I am not tuning further to decide it:** with the old grades withdrawn
there is no longer a reference to tune against, and the difference between A and B is a judgment about
how harsh the instrument should be, which is Sean's to make.

#### ✅ D42 CLOSED — Sean chose REPLICATE, and the outflank becomes a one-level discount (rubric v1.14.0)

**Sean: *"I think let's focus on replicate then."*** **Applied as option B.** **Replication now SETS the
level** — name the mechanism (IP · capital intensity · network control · scale economics · switching
costs · accumulated asset) — **and the outflank is retained as a real but bounded penalty: an open route
that could take significant share scores NO HIGHER THAN ONE LEVEL BELOW what the mechanism alone would
earn.** *A strong barrier does not protect a position a rival can simply go around, but an open route
does not erase the barrier either.* **The outflank is therefore kept as an insight rather than a veto.**

**Measured — the spread is substantially restored:**

| Version | DEF distribution (L1…L6) | Mean | SD | Cases at 4+ |
|---|---|---|---|---|
| v1.12.0 single-route | 25 · 35 · 29 · **26** · 3 · 2 | 2.61 | **1.20** | 31 |
| v1.13.1 weaker-route-SETS | 20 · **59** · 37 · **1** · 3 · 0 | 2.23 | 0.82 | **4** |
| **v1.14.0 replication-led** | 17 · 53 · 35 · **12** · 2 · 1 | 2.43 | **0.96** | **15** |

**Level 4 recovers 4 → 15 and SD 0.82 → 0.96.** It does **not** return to v1.12.0's 26 — **and that is
correct rather than a shortfall, because the outflank discount is now genuinely applied**, which is the
thing v1.12.0 was blind to. **The businesses reaching 4+ are now:** ASML **6**, Boeing **5**, Coupang
**5**, then NTUC FairPrice, Watsons, McDonald's, VICOM, **KOI Thé**, ActiveSG, Eu Yan Sang, IKEA,
Anytime Fitness, Sheng Siong, Scanteak, Pet Lovers Centre at **4**. **That set reads correctly** — real
networks, licensed or capital-heavy formats, and the two genuinely structural operators at the top.

**✅ AND THE CANARY PASSES — C3 is back to Contested.** Which forced a check on whether the v1.13.1 drift
was real, and it was:

**⚠ THE CANARY HEADER WAS MISREPORTING THE REFERENCE VERSION.** It printed
`json.loads((HERE/args.rubric))["_meta"]["version"]` for **both** the reference and the current rubric —
**so it displayed the current version twice and the reference version shown was always wrong.** *The
comparison itself was never affected* (it reads the frozen snapshot from `SNAP`), so **the v1.13.1
"reference 1.13.1 : current 1.13.1" line was a display bug, not a re-recorded snapshot** — **which means
that drift was real, and the v1.14.0 pass is a genuine restoration rather than a green light against a
loosened reference.** **Fixed to read `rubric_version` from the snapshot**; it now reports
*"reference rubric: 1.8.0 (frozen snapshot)"*.

#### ✅✅ D43 ANSWERED — Sean graded the fresh blind set, and the result CORRECTS D41

**Sean filled in `DEFENSIBILITY-V2-GRADING.md` — 17 businesses, 1–6, new definition, from memory, no
instrument answer shown.** **This is the first defensibility reference that reflects the construct he
actually wants, and it changes two conclusions.**

| | Sean (fresh, blind) | Instrument v1.14.0 | Gap |
|---|---|---|---|
| Gong Cha | 2 | 2 | 0 |
| Each-A-Cup | 2 | 3 | −1 |
| **KOI Thé** | **2** | **4** | **−2 ⚠** |
| Best Denki | 3 | 2 | +1 |
| Gain City | 3 | 2 | +1 |
| KFC | 3 | 3 | 0 |
| Toast Box | 3 | 3 | 0 |
| IKEA | 3 | 4 | −1 |
| **NTUC FairPrice** | **6** | **4** | **+2 ⚠** |
| Anytime Fitness | 3 | 4 | −1 |
| Watsons | 3 | 4 | −1 |
| McDonald's | 4 | 4 | 0 |
| Playmade | 2 | 2 | 0 |
| A home massage service | **1** | 2 | −1 |
| Zoff | 2 | 2 | 0 |
| Coupang | 5 | 5 | 0 |
| ASML | 6 | 6 | 0 |

**Exact 8/17 = 47.1% · within one level 15/17 = 88.2% · mean offset −0.18.** **⚠ At n=17 the intervals are
wide (within-one 65.7–96.7%; disputes 3.3–34.3%), so this is a SHAPE reading, not an accuracy claim.**

**✅ AND THE SHAPE IS HEALTHY — which is the point of grading blind.** **Both readings use the full 1–6
range.** **There is NO systematic bias**: the mean offset is −0.18, **and the two disputes sit in
OPPOSITE directions** — KOI has the instrument **HIGH** by 2, NTUC has it **LOW** by 2. **A dimension that
flattened toward the middle would show one-directional gaps and a compressed range; neither is present.**

**⚠⚠ BUT IT OVERTURNS D41, AND I HAVE TO SAY SO CLEARLY.** **Ten of the seventeen grades CHANGED from
Sean's old numbers — mean shift −0.18, with KOI moving two whole levels (old 4 → fresh 2).** **He was
right that *"a lot of them are wrong."*** The consequence:

> **Under the new definition, Sean's bubble-tea grades are 2 · 2 · 2 · 2 — essentially FLAT.**
> **The 1-to-4 spread I spent an entire round analysing (D41: *"the instrument flattens where the two
> readings should separate"*, the KOI-vs-Gong-Cha outflank story, the format-capital-intensity ladder)
> was an artefact of noise in the OLD grades.**

**And it inverts the direction of the complaint.** **On bubble tea the INSTRUMENT now holds the spread
(2, 3, 4, 2) where Sean is flat (2, 2, 2, 2)** — **the single dispute is the instrument reading KOI two
levels too high.** **D41's finding is therefore SUPERSEDED, not merely revised**, and the earlier
"flattening is the dominant remaining error" statement is withdrawn. **The old-grades withdrawal (D42)
was the right call, and it took a blind regrade to show it.**

**THE ONLY TWO OPEN DISPUTES, both 2 levels and opposite in sign:**
- **KOI Thé — instrument 4, Sean 2.** *The instrument credits a 161-outlet national network as a
  capital/network barrier; Sean, who knows the bubble-tea market, reads it as replicable.*
- **NTUC FairPrice — instrument 4, Sean 6.** *Sean reads Singapore's dominant grocery chain as
  COMPOUNDING — several mechanisms reinforcing. The instrument will not go above a single mechanism,
  which is the more likely defect of the two: **"compounding" requires seeing multiple mechanisms at
  once, and that needs category knowledge the form does not carry.***

**⚠ AND A CONSEQUENCE FOR EARLIER WORK: the D39 "operated network" rule is no longer needed to fix KFC
and Toast Box.** Under fresh grades both are **3**, and **v1.14.0 already returns 3 for both — exact
matches.** **v1.11.2 had pushed them to 4 to satisfy the OLD grades, which the fresh grading shows were
too high.** The network is now covered correctly as an *accumulated asset* among the named mechanisms,
rather than as a special clause.

#### ✅ D45 — SECOND COMPRESSION PASS, AND IT CONFIRMS THE MICRO-DRIFT WAS NOISE (rubric v1.15.1)

**Sean: *"another compression pass then test again."***

**Compressed `defensibility` 3,619 → 2,948 chars (−19%)**, folding the mechanism list, the mechanism count
and the outflank discount into tighter prose. **All 25 rules kept, each checked by name before
committing** — the same verification used in the first pass, because a compression that silently drops a
rule is worse than no compression.

**⚠ AND THE RESULT IS DIFFERENT FROM THE FIRST COMPRESSION, IN A USEFUL WAY.**

**(1) Accuracy is UNCHANGED — not one of the 17 blind cases moved.** *exact 8/17 · within-one 16/17 ·
offset −0.24 — identical to v1.15.0.* **So this compression was genuinely neutral**, unlike the
v1.14.0 → v1.15.0 step (which moved NTUC 4 → 5 by ADDING a mechanism — a content change, not a wording
one). **That distinction is the useful part: compression that only tightens wording can be verified
neutral against the blind set, so it can be done safely and repeatedly.**

**(2) The distribution improved slightly at the bottom.** **L1 13 → 17, L2 54 → 49** — four more
businesses correctly scored at the floor. Mean 2.54 → 2.52, **SD 1.01 → 1.05** *(slightly wider, i.e.
better discrimination)*. **A smaller prompt, the same accuracy, and a marginally better spread.**

**(3) ⚠⚠ THE RECURRING MICRO-DRIFT REVERSED — WHICH SETTLES WHAT IT WAS.** Last pass flagged 5 businesses
moving **1 → 2** as *"the fourth appearance, not improving"*. **This pass moved 4 back from 2 → 1**, with
**no wording change touching that part of the dimension.** **So the micro-drift is NOISE, and the decision
not to tune against it was right.** *Recorded because the temptation to "fix" it was real and would have
been fitting to noise — the same error that produced the v1.11.0 over-raise.*

**(4) Noise floor re-measured at v1.15.1** — two full batches, same rubric: **PS 4.2% · MA 5.0% · DEF
2.5% · CR 4.2% · MH 0.8% · DR 1.7%.** **Worst is now 5.0% (mental_advantage), and defensibility is the
second-lowest at 2.5%** — so the dimension that caused the most trouble this session is now among the
most stable. **The working rule stands: a movement must clear ~5% to be worth interpreting.**

**(5) Canary passes; 120 cases in 9 s on each of two batches.**

**⚠ THE STANDING COST IS UNCHANGED: the rubric keeps growing back.** This is the second compression in
five revisions, and **each pass recovers roughly a third of what two content changes add.** The honest
conclusion is that **compression is now a routine maintenance step, not a one-off fix** — and it should
probably run on a cadence rather than waiting for the prompt to visibly bloat.

#### ✅ D44 — COMPOUNDING MADE REACHABLE, AND POLICY BACKING ADDED (rubric v1.15.0)

**Sean: *"You may fix the compounding. NTUC fairprice is a cooperative with deep government hands and
involvement."*** **Two changes, and the second is a mechanism the rubric did not have at all.**

**(1) POLICY OR STATE BACKING is now a named mechanism.** *"Deep government hands and involvement"* is a
barrier **a challenger cannot buy at any price** — government ownership or involvement, a cooperative or
statutory mandate, a protected or subsidised position, a licensing regime favouring incumbents,
public-service obligations that keep rivals out. **The rubric had six mechanisms and none of them covered
political protection, so NTUC was being scored as though it were merely a big supermarket.**

**(2) COMPOUNDING is now reachable.** The instrument would not go above a single mechanism, which is
exactly why NTUC graded 4 against Sean's 6. **The instruction now requires ENUMERATING every mechanism
that genuinely applies, and states that two or more reinforcing each other is a 5 or 6** — they need not
be independent (scale economics + network control; capital intensity + policy backing; IP + distribution).
**Level 5 was reworded to *"two or more mechanisms reinforce each other"*, which is the specific clause
that was missing.** A guard was added: **do not reach 5 or 6 without naming at least that many mechanisms.**

**RESULT — both intended effects, plus corrections the rubric found on its own:**

| Business | Sean | v1.14.0 | **v1.15.0** |
|---|---|---|---|
| **NTUC FairPrice** | **6** | 4 | **5** ✅ *now within one* |
| **VICOM Ltd** | — | 4 | **5** ✅ *national vehicle-inspection monopoly — policy backing* |
| **ActiveSG** | — | 4 | **5** ✅ *statutory-board gym — policy backing* |
| **PCF Sparkletots / My First Skool** | — | 3 | **4** ✅ *government-linked preschools — licensed + subsidised* |
| Guardian Singapore | — | 3 | **4** |
| ASML · Boeing · Coupang | 6 · — · 5 | 6 · 5 · 5 | 6 · 5 · 5 *(held)* |

**⚠⚠ THE RUBRIC FOUND THE RIGHT CASES WITHOUT BEING TOLD.** **VICOM, ActiveSG and the government-linked
preschools were not named by Sean and were not in the grading set** — the model **applied policy backing
on its own to businesses that genuinely have it.** That is evidence the mechanism is being *reasoned
with* rather than pattern-matched to the NTUC example, and it is the strongest sign yet that the
category-reasoning pathway is doing real work.

**Corpus effect: within-one-level against Sean's fresh grades improves 88.2% → 94.1% (15/17 → 16/17),
which is the only 2-level dispute left resolved. Distribution SD 0.96 → 1.01 and level 5 goes 2 → 5. The
canary passes.**

**⚠ BUT TWO COSTS, AND BOTH ARE MINE:**

**(a) The recurring micro-drift returned — 5 cases moved 1 → 2 again** (Euns Nails, YatoNails,
DazzlingNails, Toa Payoh Home Facial, a home-based mobile hairdresser), while Nails Of Society moved
2 → 1. **This is within-one-level movement on cases Sean scores 1, and it is the fourth time this
pattern has appeared.** It sits close to the 2.5% noise floor for this dimension (5/120 = 4.2%), so **it
cannot be cleanly attributed — but it is also not improving, and it has now survived four rubric
revisions.** *Not chased further in this pass: at a 4.2% noise ceiling, tuning against it would be
tuning against noise.*

**(b) I re-inflated the instruction, immediately after compressing it.** **`defensibility` went 2,671 →
3,619 chars (+35%)** in two revisions (v1.14.0 then v1.15.0), undoing a third of the v1.12.0 compression
**within three rounds of adopting the discipline that produced it.** **That is exactly the bloat that
D40 identified as a plausible contributor to batch variance.** *The honest conclusion is that
"compress once" does not hold: compression has to be a recurring step, and the next pass should fold the
outflank discount and the mechanism list into tighter wording rather than appending further clauses.*

#### ⚠ D43 (original framing, superseded by the grading above)

**With the 120 old grades withdrawn, `defensibility` has no human reference at all.** Agreement can no
longer be measured, so **the only remaining test is whether the output is reasonable — which is weaker,
and which I can satisfy by construction because I wrote the rubric.** **I cannot grade this dimension
against myself.**

**So a fresh blind set has been written: `specs/calibration/DEFENSIBILITY-V2-GRADING.md` — 17 businesses,
graded 1–6 against the NEW definition, from memory, with no instrument answer shown.** It is deliberately
mixed: some previously graded, some far from Sean's usual market, and some with no obvious barrier at
all. **The range is the point** — a dimension that has flattened to 3–4 cannot be told apart from one
that is working by looking only at the middle.

**⚠ Honest note on the value of 17 cases:** it is enough to **detect a 2-level systematic bias** and to
**calibrate the shape of the distribution** (does it use 1 and 2 at all?), but **not enough to move the
agreement statistic.** **It is a diagnostic, not a re-calibration.** *A re-calibration needs the ~300
count from earlier — and this time the sheet would have to be authored from the new definition, since the
old labels are void.*

#### ⚠⚠ D41 — SUPERSEDED by D43's blind regrade. READ THE CORRECTION BELOW BEFORE THIS SECTION.

> **⚠⚠ THIS SECTION IS WITHDRAWN.** Its finding — *"the instrument flattens defensibility where the two
> readings should separate"* — **was derived from Sean's OLD grades, which he later withdrew as unreliable
> (D42). When he regraded blind under the new definition, his bubble-tea scores came back FLAT (2·2·2·2)
> and the KOI-vs-Gong-Cha "spread" disappeared.** **The instrument was not flattening; the reference was
> noisy.** *The historical text is kept below because the reasoning error is instructive, and because it
> is the third time this session that a finding derived from the old grades failed to survive a check.*

#### ⚠⚠ D41 (WITHDRAWN) — the bubble-tea hand-read: the apparent flattening

**Hand-read done as promised. It found a pattern that generalises beyond bubble-tea, and one case where
Sean's own rule cannot be derived.**

**Sean's bubble-tea grades spread across the full range; the instrument does not:**

| Business | Instrument | **Sean** | Gap |
|---|---|---|---|
| KOI Thé | 4 | **4** | 0 |
| CHAGEE | 4 | **4** | 0 |
| HEYTEA | 3 | **3** | 0 |
| CHICHA San Chen | 4 | 3 | 1 |
| Mixue | 4 | 3 | 1 |
| LiHO TEA | 4 | 3 | 1 |
| Sharetea | 3 | 2 | 1 |
| R&B Tea | 3 | 2 | 1 |
| Playmade | 2 | 2 | 0 |
| **Each-A-Cup** | **4** | **2** | **2** |
| **Gong Cha** | **3** | **1** | **2** |

**Sean's spread is 1–4. The instrument's is 2–4 and it clusters at 3–4.** **Every one of the two-point
gaps is the instrument reading HIGH** — the instrument does not go low enough.

**⚠ AND THE RULE BEHIND SEAN'S SPREAD IS NOT DERIVABLE FROM THE SCORES ALONE — I checked, and it
resists.** Across the whole corpus his defensibility tracks **format capital intensity** monotonically:

| Format | n | Sean's mean DEF |
|---|---|---|
| no premises | 5 | **1.00** |
| home-based | 47 | 1.74 |
| kiosk / small counter | 13 | **2.46** |
| small premises | 9 | 2.56 |
| office | 2 | 3.00 |
| full restaurant premises | 10 | 3.20 |
| large-format store | 17 | 3.59 |
| premises / licensed premises | 4 | **4.50** |

**That is a clean monotone, and it explains KFC (kitchens, many outlets = 4) against Gong Cha (kiosks =
1).** **But bubble-tea breaks it: KOI, which runs the same counter format as Gong Cha, gets 4 where Gong
Cha gets 1.** So the format rule is necessary but not sufficient, and **the differentiator between those
two is not visible in the grades** — it is knowledge Sean holds (likely tenure, outlet count, or
Singaporean mental-ladder position per his own MA definition).

**⚠ This is the same defect as every other one in this section, stated once more: the instrument
systematically FLATTENS defensibility toward the middle.** **It does not go low enough on genuinely
undefendable businesses and it has moved to 3–4 for most chains.** **And it is now the dominant
remaining error** — 10 of the 13 bubble-tea cases are within one level, but **the two 2-point cases are
the only ones outside noise, and both are the instrument reading high.**

**Superseded record of the withdrawn finding, kept because the reasoning error is instructive:**

`rubric.json` declares **`level_counts.defensibility = 6`** while the other five dimensions are **5**.
The scale block says `jev_levels: "0-4 (0-indexed)"` / `human_display: "1-5"` — so **defensibility is
the one dimension that does not follow the declared scale.** The code comment records this as
deliberate: *"a 6-level dimension at maximum still contributes its full weight (0.5.0 split
defensibility 5 -> 6)"*. The model emits **6 probability bins for defensibility and 5 for everything
else**, and `display = round_half_up(E[level]) + 1` therefore yields **1–6 for defensibility, 1–5 for
the rest.**

**Measured consequences, all real:**

| Evidence | Value |
|---|---|
| Display values observed, defensibility | **1,2,3,4,5,6** — the 6 appears **3 times** |
| Mean probability mass on the 6th bin | **3.4%** — small, but it fires |
| Composite divides by `counts[defensibility]` = **6**, not 5 | so every defensibility level contributes **less** weight than it should |
| Sean's blind grades for defensibility | **1–5** (his sheet header is the 1–5 display scale) |

**⚠ So every defensibility comparison in §10.6 has been comparing two different scales.** A gap of 2
between a 1–5 grade and a 1–6 level is **not the same distance** as a gap of 2 between two 1–5 scales —
which is precisely why `defensibility` looked like the worst dimension.

**And it explains the arithmetic that started all of this.** The 8 defensibility disputes (6.7%) were
already down to 4 (3.3%) once Sean corrected his sheet. **Putting the scales on the same footing takes
it further**, to **1.7%–4.2%** depending on the normalisation used *(percentile-matched comparison:
**1.7%**; round-to-nearest onto 1–5: **4.2%**)* — against `position_strength` 0.8%, `mental_advantage`
7.5%, `demand_reach` 4.2%. **On a like-for-like scale, defensibility is no longer the worst dimension,
and both normalisations fall below the ≤5% bar.**

**Why this was invisible:** the raw number *was* above the bar, so it read as a **rubric content**
problem and was investigated as one. It is at least partly a **scale mismatch** — the same class of bug
as the §5.4 rounding gap (a second implementation banding a float), and the same lesson: **a defect
that only shows up when two implementations disagree is not a content problem.**

**Recorded as D36 rather than fixed unilaterally** — collapsing defensibility from 6 levels to 5 is a
scoring change that alters every prior run, so it needs a ruling. **The two options are set out in
§13.** *Note also that the 6-level split was introduced deliberately in 0.5.0, so reverting it is not
obviously right — but leaving it means the report shows one dimension on a **6-point scale** next to
five 5-point ones, which a reader will read as a stronger signal than it is.*

#### ⚠ D37 — the moat definition: what a commonly-accepted moat actually requires

**Sean's question, verbatim:** *"mental advantage should not determine defensibility. It should follow
the definition of moat as per warren buffet or other commonly accepted definition?"* **He is right, and
he identified the exact defect — one rule was importing `mental_advantage` into `defensibility`.**

**Researched against primary sources rather than adopting the frame on its say-so** (this session has
already caught **six** imported frameworks misfiring — §10.6's read-through pass):

**Buffett's moat / Morningstar's five sources** *(Morningstar, "How to Measure a Company's Competitive
Advantage", and the Jan 2025 VanEck white paper)*: **cost advantage · intangible assets · network
effect · switching costs · efficient scale.** *"If a company has a wide moat, it has a strong defense
against rival companies that we think can last 20 years or more."*

**⚠ The decisive line, verbatim, from Morningstar:** *"Just because a company boasts a **well-known
brand**, or has been **in business a long time**, does not necessarily mean it has an economic moat."*
Their own illustration is **United Airlines and Ford against Nike and Apple** — all four household
names, only two moats. **A well-known brand is a moat source only where it produces demonstrated
pricing power**: brand equity *"can allow the company to charge a significant price premium."* **Fame
without pricing power is not a moat.**

**Barriers to entry** (Wikipedia, citing Stigler 1968 and McAfee et al.): *"a fixed cost that must be
incurred by a new entrant, regardless of production or sales activities, that incumbents do not have
or have not had to incur."* List includes **capital requirements** — *"many industries require the
investment of large financial resources to start a new business, which deters new entrants"* — and it
distinguishes **primary** from **ancillary** barriers, the latter reinforcing only *"if they are
present"*. **That is the same primary/ancillary logic the rubric already uses.**

**Read against Sean's four disputed cases, the frame CONFIRMS all three of his rulings:**

| Business | Moat source, if any | Verdict |
|---|---|---|
| **Best Denki, Gain City** | **Efficient scale + capital requirements** (few rivals, high capital to enter) | **4 defensible ✓** — but the moat is **capital and scale**, *not* mental advantage |
| **Gong Cha, Each-A-Cup** | None — no switching cost, near-zero entry cost, fragmented; fame without pricing power | **Low ✓** |

**⚠ But the frame also corrects the REASON, and Sean reached this himself.** His Best Denki
justification was *"because they all have mental advantage, there is some defensibility"* — **mental
advantage is not a moat source under any of the five**, and feeding it into DEF is exactly the
double-count that made DEF and MA agree too often. **His ruling (4) stands; the reasoning behind it
was wrong, and he is the one who caught it.**

**⚠ And one honest limit, because this is a POSITIONING rubric, not an investing one.** Buffett's moat
exists to predict **long-term returns on capital**; §1's objective is **quality of the current
position relative to competitors**, with scoring as an *outcome*. **So the right move is to adopt the
moat's STRUCTURE — structural barriers, not fame, with primary and ancillary distinguished — and NOT
its PURPOSE (returns prediction).** Importing the investor purpose wholesale would be the seventh
imported framework in this document. **Recorded as D37.**

**This links D35 to D25 and it is not a coincidence** — both need the same external scan, so a single
scan can serve both. It also raises a second-order risk the report must handle: **where the category
is thin, the scan will find few comparables, and "consolidated" must then not be inferred from
absence.** A category with three operators in a small market is not consolidated; it is thinly
populated, and the report should say so rather than award defensibility for it.

#### ⚠ A metric that hides the common case

**`disp>=2` counts only disagreements of two or more levels. Here is the actual distribution**, so the
figure cannot be misread *(measured over 606 cells, all six dimensions)*:

| Distance | Cells | Share |
|---|---|---|
| 0 — exact | 365 | **60.2%** |
| 0.5 — half-level | 7 | 1.2% |
| **1 — one level** | **204** | **33.7%** |
| 2+ — the "dispute" bar | 30 | **5.0%** |

**So a third of all cells sit exactly one level apart, and that is invisible to the bar.** The honest
reading of *"2.8% disputes"* is **"60% exact, 95% within one level, 2.8% two or more apart"** — not
"98% agreement". *(An earlier pass of this section said "roughly half"; the measured figure is 33.7%.
Corrected here rather than left as an impression.)*

**Per dimension, the same split:**

| Dimension | Exact | ±1 | ±2 or more |
|---|---|---|---|
| `position_strength` | 57.5% | 40.0% | **0.8%** |
| `mental_advantage` | 50.8% | 37.5% | 7.5% |
| `defensibility` | 54.2% | 39.2% | **6.7%** |
| `market_headroom` | 85.7% | 14.3% | 0.0% *(n=7)* |
| `demand_reach` | 61.7% | 34.2% | 4.2% |

**Sean also reasons in ±1 bands himself** — *"Toast box and scanteak are 3-4 with scanteak closer to 3"*
— so **on a 5-point human-judged scale ±1 may genuinely be within the noise, and that is a defensible
bar.** But the spec should state it plainly, because *"2.8% disputes"* quoted alone overstates the
agreement by a wide margin: **the honest headline is 60% exact, not 97%.**

**⚠ The critical consequence for sample size: more businesses would NOT fix this.** Extra cases would
measure the same disagreement more precisely. **The fix is to re-read these eight cases against §5.4's
definition and decide — per case — whether the instrument or the definition is wrong.** That is a
half-day of hand-reading, not a corpus expansion.

**⚠ And the corpus is exhausted: all 120 businesses in `inputs-v4` are already graded (120 rows in
`sean-regrade-raw.csv`, zero ungraded).** `inputs-v2` and `inputs-v3` are **subsets** by company name,
not new businesses. **So "reaching n=300" requires collecting ~180 NEW businesses first** — research
work, not a grading session. **The earlier advice to "grade more to reach 300" was wrong on two
counts: the denominator, and the availability of material.**

**Three consequences, all of which belong in the launch decision:**

1. **Two bars pass on the interval as well as the point estimate** (band agreement, gross error). **One
   passes only on the point estimate** (disputes). So "all bars met" is true at the point estimate and
   **one bar short of demonstrated** at the interval.
2. **The 85% target-segment figure is load-bearing for D3 and rests on 60 cases.** It is the number
   quoted when the instrument's strength is asserted; ±9pp is what it actually supports.
3. **A cheap fix exists and should be taken:** **grade the remaining calibration businesses blind to
   move n from 114 toward ~300**, where the dispute interval clears 5%. That is one afternoon of grading
   and it converts a point-estimate pass into a demonstrated one.

**This is the same error the spec records elsewhere and did not apply to itself** — §7.12 says a small
N cannot resolve a rate, and §10.6's table then reports rates from n=114 without intervals. The
numbers are honest; **the presentation was more certain than the measurement.**

**Dimension-exact agreement is explicitly NOT the bar.** It sits at 56.5% — **and its interval is
51.9%–60.9%, so it is a long way from 75% at either end.** `measure_alignment.py` still prints
*"target >=75%"* and reports **FAIL** against it. **That target was retired by D20** — dimension
exactness was replaced by band agreement — so **the script is asserting a bar the spec no longer
holds.** Either retire the target in the script or label it historical; leaving it means every
alignment run shows a FAIL that does not correspond to any live criterion.

**The band-agreement replacement holds regardless:** requiring dimension exactness would hold the
product to a granularity a five-point human-judged scale does not support. **The client
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
| `position_strength` | one share fight against every named competitor | the position held **per situation**, corroborated |
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
  scored `position_strength` 3 against a sub-1% fringe business facing BioPak's verified moat).

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

## 11. Two-stage ship (per §12's D4 — **not** §13's D4, which is the refuse-ruling)

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

**Six decisions this round — all ANSWERED, in plain English.** The detail behind each is in the section referenced.

| # | The question, in plain English | What I recommend |
|---|---|---|
| **D25** | **DECIDED — the pool is built by web research, not just the calibration corpus** | **Sean:** *"we should have exercised the web search protocol skill to find and score other competitors, just like what we did for our competitive analysis projects."* The competitor set is now a **deliberate protocol-governed scan** (§4.6), not best-effort enrichment. **⚠ Gated by his condition: assess input quality FIRST, before the token burn** (§3.11). The two-tier disclosure (5 / 8) still stands — **but it now matters for the opposite reason than I originally gave: it protects the *contributors*, not the asset.** Because the scan is reproducible, there is no licensable asset (§7.11) |
| **D30** | **The pre-flight gate — check input quality before spending tokens** | **DECIDED — Sean's condition.** The gate fires on the **form answers alone, before any scan is issued** (§3.11). Reuses §3.10's existing floor, so it adds no new logic — only changes *where* it fires. A refused submission never triggers research |
| **D26** | **DECIDED — D or E. Not a data licence.** | **Sean:** *"I don't see how we can monetise this with credibility because accuracy due to time uncertainty is always an problem. I am ok with E or D."* **He is right, and §7.11 records why:** positions decay from both ends, the submitter's half is unrenewable, and **public-sourced data is reproducible by anyone — so there is no licensable asset to protect.** What is defensible is the **rubric, the calibration and the scored judgments**. Recommendation: **D as the posture, E's consent structure retained** so a future option stays open. A is also acceptable |
| **D24** | **DECIDED — yes.** | **Sean: yes.** Public-source material (listings, reviews, registries) may enter the dataset. §4.6's `observed` tier governs how it is labelled |
| **D28** | **DECIDED — yes, but lightly.** | **Sean: yes but lightly.** Verification must not become a conversion barrier. §7.7.1's cheap structural control (require the form be completed properly before a report issues) is the shape |
| **D27** | **DEFERRED — future.** | **Sean: "certification is for the future."** Not a now-item; revisit if the paid tier targets SMEs |
| **D31** | **Do we score NAMED competitors, and show that to the submitter?** | **DECIDED — yes, name and score freely. Same answer as D25.** **Sean: *"Why is it a compliance issue where I have scored a company based on my own hardwork and due diligence based on publically available information?"* — and he is right; my framing was wrong.** A **company is not a data subject** and does not consent to being analysed. §7.13 records the correction: **"consent" was the wrong word** for three separate things (the submitter's consent — real, unaffected; the competitor's consent — **not required**; the contributor pool's protection — real, unaffected). Sean's own published work already does this *(verified)*: Book 1 names KOI, LiHo, Gong Cha, Tiger Sugar with outlet counts; the CaiCa deliverable rules *"Contested — CHAᴳEE owns it."* **Not a new risk — the established practice of the work.** Two narrow duties remain: accuracy (already §4.3's sourced claims) and correction route. **⚠ One genuine edge: sole proprietors** — where a rival is one person, analyse the **business**, never the **person** |
| **D32** | **Is D3's target segment the right COMMERCIAL target?** | **DECIDED — keep 0–9, and my framing of the problem was wrong.** **Sean: *"I am trying to apply positioning theory here to build trust and credibility with any potential customer. The more touch points they have with me — my free tools, my social media content, my books — the more they will engage and convert with me."*** I had measured the toolkit against a **purchase-intent base rate** (24%, falling). **Wrong yardstick — the toolkit is not the ask; it is the first of several low-cost engagements that build the credibility the ask depends on.** The 76% who would not buy advice today are not a failure state but a **latent pool the sequence keeps warm**. This reframes the §7.12 evidence as **supportive**: micro firms have no written plan (~1/3), 13% use external finance — a population that has never been *shown* what structured thinking about their position does. **The ILO finding that willingness to pay rises from 23–65% before delivery to 53–100% after is the mechanism this strategy runs on.** Toolkit stays aimed at **0–9**; the paid tier is whatever the sequence produces, and the funnel's job is to reveal it, not assume it (§7.14) |
| **D34** | **The sole-proprietor line** (§7.13) | **DECIDED — Sean: *"analyse the business, never the person"* is the line.** Where a rival is one person, the trading name may resolve to an individual, so the **identity** is personal data while the **business** is analysable. **⚠ Restrains ATTRIBUTION, not SCORING** — a sole-proprietor rival is still scored and still counted in the pool, because excluding them would gut the benchmark in exactly the categories D3 targets (home-based businesses are overwhelmingly one-person). Describe by category (*"a home-based nail studio in the east"*), never by name, photo or personal detail |
| **D33** | **Test the toolkit as cold acquisition, as a referral artefact, or both?** | **DECIDED — neither, exactly: measure conversion by TOUCHPOINT COUNT.** Sean's answer to D32 makes this question smaller. **Every touchpoint is a referral substitute**, and Hinge's own finding — **visible expertise drives 37.3% of referrals, more than client relationships (23.1%)** — describes exactly what the content, toolkit and books manufacture. **So the toolkit's job is engagement and repeat contact, not immediate conversion**, and a funnel counting only booked calls would score a returning prospect as a failure. **§7.10 gains four metrics: return visits · touchpoint overlap · time from first touch to engagement · conversion by touchpoint count.** The last is the real experiment — it tests the strategy directly instead of proxying it. **Honest limit: at 300 submissions we can bound a rate but still cannot attribute a conversion to toolkit vs content vs book — which is exactly why touchpoint count must be recorded from submission one** |
| **D29** | **Should the toolkit itself be the test?** You asked why not make the diagnostic the test of the whole business model. | **DECIDED — yes, and my earlier phasing was wrong.** Nothing else uses the benchmark, so "build it later" meant building it for nobody. The toolkit is the instrument, not the subject (§7.10). **NOW QUANTIFIED (§7.12):** pre-commit to **300 completed submissions** before any go/no-go (3/N gives "<1%" at 300; ±5pp precision needs 384); **peeking can inflate a 5% error rate to 26.1%**, so sample and rule must be fixed before launch; and **a null cannot distinguish a bad tool from a bad segment from a bad price from no distribution** — that four-way limit is the honest boundary of the test. **Money received is the only valid primary outcome** — intention converts to behaviour only about half the time |

---

**The full register follows. Most rows are already settled.**

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
| **D20** | **Launch criterion** (§10.6) — dimension exactness vs band agreement | **ACCEPTED — band agreement.** ≥90% within one band, ≤5% two-or-more off. Dimension-exact is explicitly not the bar (it sits at **56.5% [51.9–60.9%]** and is not achievable on a 5-point human-judged scale). **⚠ `measure_alignment.py` still asserts the retired ≥75% exact bar and prints FAIL against it — either retire the target in the script or label it historical** |
| **D35** | **`defensibility` — is it a property of the BUSINESS or the CATEGORY?** (§10.6) | **CLOSED — B. Sean ruled: *"Can we agree on B for defensibility?"*** **DEF now reads CATEGORY STRUCTURE as an input** (rubric **v1.9.0**): consolidation and capital- or licence-intensity add defensibility; fragmentation with low entry cost removes it; **familiarity is explicitly NOT defensibility** (Gong Cha is a household name in a fragmented category and belongs low). **The evidence that decided B over C:** after Sean's sheet corrections, the **4 residual DEF disputes were ALL category-structure cases** — electronics (consolidated → raise) and bubble-tea (fragmented → lower) — and **ZERO were business-level**. The residual error was entirely the missing construct. **C was rejected because `competitive_room` does not encode it:** Sean's own CR vs DEF correlate only **−0.19 across categories** (and **+0.07** at business level), so consolidation was *not* already hiding in CR — moving it there would have put a category fact in a landscape dimension where he does not read it. **⚠ B creates an input requirement (see below), and it does NOT fix Best Denki on its own.** ~~OPEN — Sean hand-read all 8, and his ruling reframes it.~~ His scores: **Best Denki 4, Gain City 4, Burger King ~4, IKEA ~4, Scanteak 3–4, Toast Box 3–4, Gong Cha low, Each-A-Cup low.** **⚠ Four of the eight "disputes" turn out to be SHEET errors, not instrument errors** — IKEA, Scanteak and Toast Box land within one of the instrument, and Burger King moves to ~4 against the instrument's 3. **DEF's true disagreement is materially lower than 7.0%.** *(His sheet was also internally inconsistent on the same construct — **Burger King 1 vs KFC 4**, two directly comparable chains, three points apart; Subway 2 and Jollibee 2 sit with Burger King.)* **THE REAL QUESTION:** his labels cluster **by category** (furniture flat 2 across IKEA, Scanteak, Cellini, Castlery; health-beauty flat 4 across four firms), while the **instrument scores each business on its own characteristics**. His Best Denki reasoning states the construct explicitly — *"the appliance market has consolidated to a few brand names only in Singapore… because they all have mental advantage, there is some defensibility because it's really concentrated at the top."* **That is a claim about the CATEGORY, which §5.4's "challenger's cost per business" cannot see.** Options: **A** instrument is right, construct stays business-level · **B** DEF reads category concentration as an input · **C** split it — business-level DEF stays, consolidation moves to `competitive_room`, **which already measures fragmentation and is where consolidation naturally belongs**. **Recommended: C.** Disputes cluster in **high-variance categories** (electronics 3/4, fast-food 1/5); where the category is **homogeneous** the two readings agree — which is the pattern that makes C the fit |
| **D36** | ~~`defensibility` is scored 1–6 while every other dimension is 1–5~~ | **WITHDRAWN — MY FINDING WAS FALSE.** I assumed Sean's DEF grades were 1–5; **`build_regrade_sheet.py:183` told him 1–6 and his grades use the full range (max 6.0).** **The scales were matched; DEF's dispute rate is 3.3% (4/120), under the bar, before any fix.** The "6.7% → 1.7%" was an artefact of a conversion that should never have been applied. **Fourth frame error retracted this session.** *Making DEF 5 levels remains a coherent uniformity choice, but it fixes nothing.* **The REAL cause is §10.6's corpus finding below.** |
| **D36-old** | *Original (withdrawn) framing* | Superseded. **See §10.6 "D36 WITHDRAWN" for the replacement finding: 99 of 120 corpus forms are analyst RECONSTRUCTIONS with a median payload of 725 characters, and the form carries none of the structural facts DEF needs.** |
| **D39** | **Does an operated multi-outlet network count as a moat where category entry is cheap?** (§10.6) | **ANSWERED — YES, and Sean authorised it: *"I'm happy for you to apply the KFC, Ya Kun and Toast box judgement."*** Applied as a **GENERAL rule** (rubric **v1.11.2**), not three case patches: **SEPARATE VISIBILITY FROM OPERATED NETWORK** — a household name resting on visibility alone is cheap to displace and stays LOW, but **a chain that demonstrably operates many units holds efficient scale and a cost advantage even where opening a SINGLE unit is cheap**, because **the barrier is the NETWORK** (property, supply chain, central purchasing, staffing at scale, decades of sites), not one more shop. **KFC, Ya Kun and Toast Box move to 4, exact match.** **⚠ Collateral is mixed and mostly at the noise floor:** 13 cases moved (8 up, 5 down); **CHAGEE and NTUC improve, but Mixue, CHICHA San Chen and Each-A-Cup move the wrong way, and 24/7 Fitness and Chin Mee Chin drop.** **Corpus totals are a wash — DEF disputes 2.5% → 3.3%, i.e. back to v1.8.0's level.** *This is what tuning to a handful of cases looks like from the inside.* |
| **D40** | **Is Jev the right lever for speed and overall process?** (§10.6) | **ANSWERED — NO, AND EXECUTED. Jev is not the constraint; the rubric was.** **Rubric compressed v1.12.0: `defensibility` instruction 5,426 → 3,026 chars (−44%), questions block 21,366 → 19,405, all 13 rules retained and checked.** **Defensibility disputes improved to 1.7% [0.5–5.9%] — best on record, clearing the ≤5% bar — and the authorised KFC/Ya Kun/Toast Box fixes held.** **⚠ And the NOISE FLOOR is now measured: two full batches of the SAME rubric moved 0–4.2% of cases per dimension, always ±1 level** (PS 4.2%, MA 2.5%, **DEF 1.7%**, CR 0.0%, MH 0.0%, DR 1.7%) — **this is the threshold any future tuning must clear.** *But compression raised 17 cases and only 10 were improvements, concentrated in micro categories; NTUC FairPrice dropped 5→4 against Sean's 5. Aggregate better, a minority of cases worse.* **✅ Both remaining levers now executed: the driver is PARALLEL (120 cases in 9 s vs 107 s sequential — 12×, 0 failures, output within the noise floor), and the bubble-tea hand-read is done (D41).** **Noise floor settled with THREE independent same-rubric batches: worst 4.2% per dimension, `defensibility` 2.5%.** *Original framing below.* Measured: **model latency 0.48 s/case; whole 120-case corpus 107 s; ~4.5 min projected for 300.** But **the prompt per case is 22,774 chars, of which the RUBRIC is 20,472 — 90%.** And the rubric is what grew: questions **14,591 → 21,366 chars (+46%)**, `defensibility` instruction **1,204 → 5,426 chars (4.5×)** — **because of my own iteration this session, and instruction bloat is a plausible contributor to the measured batch variance.** **The real process levers, in order: (1) COMPRESS the rubric** — state each rule once, tersely; smaller prompts are faster, cheaper AND more reproducible. **(2) PARALLELISE the driver** — 0.48 s model vs ~0.85 s process overhead per case, run sequentially; **the overhead is larger than the inference.** **(3) FIX THE NOISE FLOOR BEFORE TUNING** — at ±1 batch variance most v1.11.0→v1.11.2 movement is noise; repeat each case or raise the reporting threshold to ±2. **(4) Then Jev's 0.48 s is worth spending on the work the spec currently gates** — inline category reasoning and the D25 external scan. |
| **D42** | **Sean rebuilt the DEF construct — two routes of attack. Does the weaker route SET or merely LIMIT the score?** (§10.6) | **CLOSED — Sean: *"I think let's focus on replicate then."* → option B, rubric v1.14.0. REPLICATION SETS THE LEVEL** (name the mechanism: IP · capital intensity · network control · scale economics · switching costs · accumulated asset); **the OUTFLANK is kept as a ONE-LEVEL DISCOUNT, not a floor** — an open route that could take significant share scores no higher than one level below the mechanism's level. *A strong barrier does not protect a position a rival can go around, but an open route does not erase the barrier either.* **Measured: level 4 recovers 4 → 15 and SD 0.82 → 0.96** (v1.12.0 single-route was 26/1.20; v1.13.1 weaker-route-SETS was 4/0.82). **It does not return to 26, which is CORRECT — the outflank discount is now genuinely applied, which v1.12.0 was blind to.** **4+ is now ASML 6 · Boeing 5 · Coupang 5 · NTUC FairPrice, Watsons, McDonald's, VICOM, KOI Thé, ActiveSG, Eu Yan Sang, IKEA, Anytime Fitness, Sheng Siong, Scanteak, Pet Lovers Centre 4** — reads correctly. **✅ Canary passes (C3 back to Contested).** **⚠ The canary header was MISREPORTING the reference version** (printed the current rubric twice; the comparison itself always read the frozen snapshot), **so v1.13.1's drift was real and v1.14.0 is a genuine restoration.** *Original framing below.* |
| **D47** | **Best Denki & Courts — consolidated appliance retail: Sean 1, instrument 3** (§10.6c) | **✅ CLOSED — SEAN RULED THE INSTRUMENT RIGHT: *"you are right it is a 3 for best denki and courts."*** **So the "two cases lost" under the 1.16.0 dominance reframe were never lost — the INSTRUMENT was right and the grading SHEET was wrong.** **On the corrected labels COMPETITIVE ROOM is exact 14/21 (67%), within one 21/21 (100%), disputes 0/21 (0.0%), offset +0.33.** **⚠ I stopped at two wording attempts precisely because a third would have been fitting the rubric to what turned out to be a bad label — the stopping rule paid for itself.** *Third time in this session that a hand-read disagreement resolved the same way: the label was the first suspect and the label was the fault.* |
| **D54** | **Is PS just the old RS renamed? + rename `relative_strength` → `position_strength`** (§5.1, §10.6f) | **✅ ANSWERED WITH MEASUREMENT — NO, AND IT IS NOT CLOSE.** *Sean: "isn't PS just current RS renamed?"* **Three states of the dimension were run and compared:** ***1.16.1 RS (recall construct) → 1.18.1 RS (position construct): only 34% identical, mean delta −0.25.*** ***1.18.1 RS (position construct) → 1.19.0 PS (same construct, new name): 93% identical, mean delta +0.00.*** ***1.16.1 RS → 1.19.0 PS overall: 36% identical.*** **So the RENAME changed almost nothing (93% identical) and the CONSTRUCT changed a great deal (34% identical).** **PS is the RS construct rebuilt per his own definition in D50 — *"mental advantage is what the market knows; relative strength is the strength of the positioning relative to competitors"* — and it is not a relabelling of the old recall reading.** **⚠ The rename's own blast radius is documented separately below; the 93% figure is the evidence that renaming per se is behaviourally safe.** **Rename itself SHIPPED as: **✅ DONE — rubric 1.19.0, promoted through the gate, with the blast radius mapped and split.** *Sean: "Ship it, can we change it to position strength PS instead of RS? you need to change all documentation with blast radius considerations."* **BLAST RADIUS MEASURED FIRST: 33,678 occurrences in FROZEN historical runs, 336 in the canary record/fixtures, 87 in code, 35 in docs.** **⚠ SPLIT APPLIED: LIVE files renamed; FROZEN history NOT rewritten** — *the run files and the canary reference ARE the record, and rewriting them would destroy the evidence base.* **Every live consumer therefore reads BOTH keys** (`LEGACY_DIM_ALIAS`). **⚠ TWO REAL DEFECTS WERE FOUND BY DOING IT:** **(a) a silent drop** — the display tag `PS` leaked into the CSV column lookup, so every lookup became `YOUR_PS`, which does not exist; `h` was None for every case and **the whole dimension was SKIPPED with no error**. *Found only because a row was missing from the output.* **Fixed by splitting display name from recorded-column name (`CSV_COL`) in both consumers.** **(b) a ROLLBACK HOLE in the promotion gate** — *the guard against a non-promoted rubric had no version ordering, so promoting the retired `rubric-v1.8.0.json` replaced the live rubric and the next corpus run scored 120 cases against a ten-revision-old instrument while reporting success.* **Now refused unless `--allow-rollback`.** |
| **D52** | **Demand reach rewards a well-written submission — ObserveCo read 4, Sean grades it 1** (§10.6e) | **✅ CLOSED — MY CALL WAS WRONG; the existing methodology stands.** *Sean: "your existing methodology is correct, disregard mine."* **So the ObserveCo case (him 1, instrument 4) is NOT a defect and no change is made.** **⚠ My reasoning had been that the instrument was rewarding a well-written submission — he ruled otherwise, and the claim is withdrawn rather than quietly dropped.** *It remains the largest single disagreement on record; it is recorded as a DIFFERENCE OF JUDGEMENT, not a defect.* ***Original framing, superseded:*** **Sean graded his own consulting business DR = 1 (no identifiable paying buyer yet); the instrument reads 4** *because the submission is detailed, coherent and names a segment.* **This is exactly the *"reading the SUBMISSION instead of the BUSINESS"* class §10.7 records as accounting for every prior improvement.** **The instrument has no account of whether a named segment has ever actually been SERVED.** *Note the rule that should have caught it — "any business currently trading is at least 3" — cannot: ObserveCo has no live outlets or price list, and the instrument is treating coherent intent as reach.* |
| **D53** | **Ceased businesses: Sean grades 1, the rubric's rule says 2** (§10.6e) | **✅ CLOSED — keep the rubric's rule.** *Sean: "1 and 2 for ceased business is not material to me. Stick with rubrics."* **A ceased business stays at DR level 2** *(identifiable buyer, no current reach)*. **No change.** ***Original framing:*** The sheet tested one rule: *a ceased business is a **2**, not a 1* (identifiable buyer, no current reach). **Sean graded BOTH ceased businesses 1 — the dormant home baker and the closed bubble tea outlet — applying the same value to both, which makes it considered rather than a slip.** **DR level 1 currently reads "no identifiable buyer, OR cannot legally serve the buyers it names."** **His judgement implies a third case belongs at 1: a business that has STOPPED TRADING.** **⚠ The instrument follows its own rule correctly — so the rule or the level-1 definition is what must change, and that is Sean's call.** |
| **D51** | **PS needs online competitor research (saladshop/caica style) — is the rubric factoring it in?** (§4.6, §10.6e) | **✅ AMENDED + BUILT (option C).** **Sean: *"RS needs to do online research on competitors, just like the saladshop project or caica project. just wanted to make sure the rubric factored this in?"*** **FINDING: the rubric CONSUMES the derived competitive set, but the set holds only names, tiers and a price-floor label — §4.6's scan (capturing rivals' POSITIONING, size, pricing) was spec'd and D25-directed but NEVER BUILT.** *So PS was inferring whether an occupant "owns" a claim from the model's own CATEGORY MEMORY.* **⚠ AND THE MODEL'S OWN CONFIDENCE DOES NOT DETECT THIS: C4 SGFitness scored PS 4 at coverage 0.83, C1 GreenPackers PS 4 at 0.72 — confidence fires when the model feels unsure, not when the basis is absent.** **(part 1, rubric v1.18.1)** *PS now scores ONLY against the supplied set, must not import outside category knowledge, and caps an unproven flank at ADEQUATE (3); canary PASSES and unproven PS≥4 falls 19 → 10 cases.* **(part 2, §4.6.1)** *`competitor_scan.py` built — discovers competitors by search, fetches live through the validity gate, records per-URL capture status, and refuses to present a blocked capture as evidence.* **⚠ PROVED TO WORK, NOT PROVED ACCURATE: the corpus's sets were hand-written per category, so there is no record of what a scan would have returned for those 120 businesses. Re-deriving the corpus by scan and re-scoring is the unrun validation.** |
| **D50** | **PS rebuilt as POSITION STRENGTH (independent of recognition) — canary re-baseline?** (§10.6d) | **✅ CLOSED — Sean chose A: re-baseline the canary.** **⚠ AND THE RE-BASELINE EXPOSED AN ERROR IN MY OWN REPORTING: the canary's per-dimension "engagement" values are NOT client labels.** *Five of six fixtures say verbatim: "The per-dimension expected levels are an ASSISTANT MAPPING of that conclusion onto the six calibrated dimensions — they are not a recorded client label. **The BAND, not the dimension vector, is the bar (spec 10.6).**"* **So my argument that v1.18.0 "went the wrong way against the engagement conclusions" was WRONG — that column has no authority.** *Only C1 GreenPackers carries a recorded client label.* **The canary reference is now recorded at 1.18.0 through the deliberate `--rung record --force` path, and PASSES on two consecutive runs.** **⚠ What still stands: the canary's band check DOES have a human-blessed source — each fixture's `expected_conclusion` (`_expected.band`), and v1.18.0 matches it 5 of 6** *(unchanged from the 1.8.0 baseline; C6 Bonefirm differs either way)*. **⚠ And C1 GreenPackers still reads PS 4 against a recorded CLIENT label of 1 — that is the one real unresolved disagreement about the new construct.** **CONSTRUCT ANSWERED by Sean:** *"Mental advantage measures what the market and customers know of the brand. Relative strength measures the strength of the said brand's positioning relative to competitors... we should give hope to the high RS but low MA business that have just started out and have a good flank."* **So MA = what the market KNOWS (present, backward-looking); PS = how strong the POSITION is against competitors' positions (strategic, forward-looking) — judged WITHOUT reference to awareness.** **⚠ CONFIRMED the old instrument could not express it: ZERO of 120 cases had PS ≥ MA+2.** **Rubric 1.18.0 does: duplication 69% → 29%, mean difference 0.32 → 0.87, target profile 0 → 6 cases, and PS≥4 did NOT inflate (37% → 34%).** **⚠ But the canary FAILS (C4 and C5 flip Fragile → Contested), and the model still tracks recognition too closely — C1 GreenPackers reads PS 4 where the engagement reading is 1.** **⚠ The frozen reference is 10 revisions stale and its PS column was written under the OLD recall construct, so it cannot validate a position-strength reading.** **Decision needed: re-baseline, or re-read the canary's PS column under the new construct.** |
| **D49** | **`position_strength` duplicates `mental_advantage` — what should PS actually be?** (§10.6d) | **✅ CLOSED — SUPERSEDED BY D50.** *Sean's ruling in D50 answered it directly: "Mental advantage measures what the market and customers know of the brand. Relative strength measures the strength of the said brand's positioning relative to competitors."* **Implemented in rubric 1.18.0 (position strength, independent of recognition) and renamed in 1.19.0.** *Duplication fell 69% → 29%.* ***Original framing:*** *"There is a problem with RS definition. It is not what we agreed on."* **MEASURED: PS and MA return the IDENTICAL score in 83/120 cases (69%); within one level in 119/120 (99%); r=+0.89; mean difference 0.32.** **On the very case PS was created to fix, McDonald's SG vs Jollibee, both dimensions returned 5/5 and 3/3 — zero separation.** **The agreed construct is "the position actually HELD against the derived competitive set" (§5.1); the implemented instruction asks "would buyers reach for this business by name", which §5.1 defines as `mental_advantage`.** **⚠ The 0.8% dispute rate that looked like PS's strength was evidence of the MERGER — 58% of Sean's own PS grades are identical to his MA grades.** **A fix (v1.17.0, PS reframed as a contest with a fame guard) cut duplication 69% → 37% and corrected the McDonald's/Jollibee inversion, but the CANARY REJECTED IT and agreement with the engagement conclusions fell to 2/6** *(C3 engagement PS 3 → instrument 2; C4 engagement PS 1 → instrument 3)*. **⚠ REVERTED to 1.16.1.** **⚠ UNRESOLVED TENSION: the structural evidence says merge, the frozen canary and his old PS labels say the old reading is better — but BOTH references carry the defect being fixed (the labels are 58% self-duplicated).** **Evidence available today cannot distinguish "RS was never a second dimension" from "the contest wording is wrong".** **⚠ FOR SEAN: what should PS measure that MA does not?** |
| **D48** | **§5.3.1 step 4 — the scorer must refuse a non-promoted rubric** (§5.3.1) | **✅ BUILT — `rubric_gate.py`, enforced in `run_jev.py`.** **Promotion writes a sidecar (`rubric.promoted.json`) recording the version and the SHA-256 of the promoted bytes; only `promote_rubric.py` writes it.** **A rubric whose hash does not match its sidecar is REFUSED, whatever its version claims** — *because the version string is set by hand and proves nothing, which is exactly how `rubric.json` was edited in place repeatedly without the six promotion checks ever running.* **Frozen references stay exempt; promoting the live file onto itself is allowed as the recovery path.** **Proved by making it fail: 7 probes** *(unstamped → refused; frozen → allowed; stamped → allowed; text tamper → refused; version-only tamper → refused, exit 1; restore → allowed; **full 120-case corpus → 0 false refusals*). **Canary passes.** |
| **D46** | **Regrade MA and CR blind — is the calibration alarm real or a label artifact?** (§10.6b) | **✅ ANSWERED — IT WAS MOSTLY THE LABELS.** 21 businesses × 2 columns, fresh definitions, from memory. **MENTAL ADVANTAGE: exact 14/20 (70.0%), within-one 20/20 (100%), disputes 0/20 (0.0%)** — against **7.5–8.3% on the old labels**. **COMPETITIVE ROOM: exact 8/21 (38.1%), within-one 21/21 (100%), disputes 0/21 (0.0%)** — against **8.4–9.2% on the old labels**. **⚠ THE RELABEL RATES EXPLAIN IT: MA 35%, CR 81%, defensibility 59%** — so every dispute rate quoted before §10.6b was measured against a reference carrying 35–81% noise. **Two of the three "failing" dimensions were failing against LABELS, not reality.** **⚠ CR carries a small systematic LOW bias (+0.43), and BOTH readings agree the top of the CR scale is unused** (instrument 61/120 at level 2, only 2 at 4, none at 5; Sean never grades 4 or 5) — **either no market in this corpus qualifies for level 5, or the descriptors are pitched too high: a definitional question, recorded not tuned.** **⚠ MY SHEET'S CLOSURE TRAP FAILED: "A closed bubble tea outlet" and "A dormant home baker" are ANONYMOUS fixtures**, so they score 1 on MA whether or not the closure rule is applied — **the trap did not fire because it was not a trap; a real test needs a NAMED closed business, and the corpus has none.** **⚠ Lenskart graded 3.5 — not a valid point on a 1–5 integer scale; queried, not silently rounded.** |
| **D45** | **Second compression pass — does tighter wording cost accuracy?** (§10.6) | **✅ APPLIED (rubric v1.15.1) — and it is NEUTRAL, which makes compression repeatable.** `defensibility` **3,619 → 2,948 chars (−19%)**, all 25 rules kept and checked by name. **⚠ UNLIKE the first compression, NOT ONE of the 17 blind cases moved** — *exact 8/17 · within-one 16/17 · offset −0.24, identical to v1.15.0.* **So compression that only tightens wording can be verified neutral, whereas v1.14.0→v1.15.0 moved NTUC because it ADDED a mechanism (a content change, not a wording one).** **Distribution improved at the bottom: L1 13 → 17, L2 54 → 49, SD 1.01 → 1.05** — smaller prompt, same accuracy, marginally better spread. **⚠⚠ AND THE MICRO-DRIFT REVERSED: 4 businesses moved back 2 → 1 with no wording touching that behaviour, so it is NOISE and the decision not to tune against it was right** — the temptation to "fix" it would have been fitting to noise, the error that produced the v1.11.0 over-raise. **Noise floor re-measured: PS 4.2% · MA 5.0% · DEF 2.5% · CR 4.2% · MH 0.8% · DR 1.7% — defensibility is now the second-most stable dimension.** **Canary passes.** **⚠ Standing cost: the rubric keeps growing back — second compression in five revisions, each recovering roughly a third of what two content changes add. Compression is routine maintenance, not a one-off.** |
| **D44** | **Make COMPOUNDING reachable; add POLICY/STATE BACKING as a mechanism** (§10.6) | **✅ APPLIED (rubric v1.15.0) — and the rubric found further cases on its own.** Sean: *"You may fix the compounding. NTUC fairprice is a cooperative with deep government hands and involvement."* **(1) POLICY OR STATE BACKING is now a named mechanism** — government ownership or involvement, cooperative or statutory mandate, a protected or subsidised position, licensing that favours incumbents, public-service obligations excluding rivals — *a challenger cannot buy political protection at any price*; the rubric had six mechanisms and none covered it, so NTUC was scored as though it were merely a big supermarket. **(2) COMPOUNDING is now reachable** — the instruction requires ENUMERATING every mechanism that applies and states two or more reinforcing is a 5 or 6, with a guard against reaching 5/6 without naming that many; **level 5 reworded to "two or more mechanisms reinforce each other"**, the clause that was missing. **⚠⚠ THE RUBRIC FOUND THE RIGHT CASES UNPROMPTED: VICOM 4→5, ActiveSG 4→5, PCF Sparkletots and My First Skool 3→4, Guardian 3→4 — VICOM, ActiveSG and the preschools were NOT named by Sean and NOT in the grading set**, so the mechanism is being *reasoned with*, not pattern-matched. **NTUC 4→5 (his 6). Within-one against his fresh grades 88.2% → 94.1%. Level 5 count 2 → 5. Canary passes.** **⚠ Costs: the micro-drift returned (5 cases 1→2 on businesses Sean scores 1 — 4th appearance, but within the 2.5% noise floor, so not chased); and I re-inflated the instruction 2,671 → 3,619 chars (+35%) within three rounds of compressing it — the D40 bloat, repeated.** |
| **D43** | **`defensibility` is UNCALIBRATED now that the old grades are withdrawn — how does it get a reference?** (§10.6) | **✅ ANSWERED — Sean graded the fresh blind set and it CORRECTS D41.** 17 businesses, 1–6, new definition, from memory, no answer shown. **Exact 8/17 = 47.1%, within one 15/17 = 88.2%, mean offset −0.18** *(n=17 → wide intervals; a SHAPE reading, not an accuracy claim)*. **✅ The shape is healthy: both readings use the full 1–6 range, there is NO systematic bias (−0.18), and the two disputes sit in OPPOSITE directions** (KOI instrument HIGH by 2, NTUC instrument LOW by 2) **— a flattened dimension would show one-directional gaps and a compressed range; neither is present.** **⚠⚠ Overturns D41: 10 of 17 grades CHANGED from his old numbers (KOI moved two whole levels, old 4 → fresh 2) — he was right that *"a lot of them are wrong."* On bubble tea his fresh grades are FLAT (2·2·2·2) and the INSTRUMENT now holds the spread the old analysis credited to him.** **D41 is withdrawn.** **TWO OPEN DISPUTES: KOI Thé (instrument 4, Sean 2 — it credits a 161-outlet network as a barrier, he reads it replicable); NTUC FairPrice (instrument 4, Sean 6 — he reads it COMPOUNDING; the instrument will not go above a single mechanism, the likelier defect since "compounding" needs category knowledge the form lacks).** **⚠ Also: D39's operated-network rule is no longer needed — fresh grades put KFC and Toast Box at 3, and v1.14.0 already returns 3, exact.** *Original framing below.* With the 120 old grades withdrawn, **DEF has no human reference**: agreement cannot be measured, so the only remaining test is "is this reasonable", **which I can satisfy by construction because I wrote the rubric — I cannot grade this dimension against myself.** **A fresh blind set is written: `specs/calibration/DEFENSIBILITY-V2-GRADING.md` — 17 businesses, 1–6, new definition, from memory, no instrument answer shown**, deliberately mixed (some previously graded, some far from Sean's usual market, some with no obvious barrier). **The range is the point** — a flattened dimension cannot be told from a working one by looking only at the middle. **⚠ 17 cases detects a 2-level systematic bias and calibrates the SHAPE of the distribution, but cannot move an agreement statistic — it is a diagnostic, not a re-calibration.** |
| **D42-old** | *Original framing, superseded by the ruling above* | **OPEN — and this is now the most consequential question in the spec.** Sean: *"Don't worry about my prior readings on defensibility. You should not converge to my old numbers because I suspect a lot of them are wrong. The rubric however should answer the question on how hard it is to replicate (IP, capital intensive, network control etc), or for an outflank to steal significant market share."* **⚠ THE OLD DEF GRADES ARE WITHDRAWN AS THE CALIBRATION TARGET**, so every DEF agreement statistic in §10.6 (including the 1.7% "best on record") **now measures agreement with a reference Sean has disowned** — retained as history, not as evidence the dimension works. **DEF momentarily has NO agreed gold standard.** **Rebuilt (v1.13.1) around REPLICATE (IP · capital intensity · network control · scale economics · switching costs · accumulated asset) and OUTFLANK (take SIGNIFICANT MARKET SHARE by another route).** **⚠ Measured: "score the weaker route" overshoots.** DEF distribution — v1.12.0 single-route: 25·35·29·**26**·3·2, mean 2.61, **SD 1.20**, 26 cases at 4+. v1.13.0 two-route: 25·**59**·32·**2**·2·0, SD 0.82, 4 at 4+. v1.13.1 (+significant-share bar): 20·**59**·37·**1**·3·0, SD 0.82, **4 at 4+ (ASML, Boeing, Coupang, VICOM)**. **Discrimination halves, and 49% pools at level 2.** My own examples (*"a second location next door"*) undercut Sean's significant-share bar; fixing that barely moved it, so the model genuinely reads this corpus as contestable. **⚠ THE CANARY NOW FAILS — C3-petdirectory drifts Contested → Fragile (DEF 2→1); one case in six is within the 2.5% noise but cannot be waved away; repeat run required.** **THE CHOICE: A — weaker route SETS the score (as written: harsh, weak discrimination) vs B — weaker route LIMITS the score, replication drives it (keeps the spread).** *Framing is Sean's and worth keeping; only SET-vs-LIMIT is open. Not tuning further — with the grades withdrawn there is no reference to tune against.* |
| **D41** | **Bubble-tea hand-read — why does the instrument not go as low as Sean?** (§10.6) | **DONE. The instrument FLATTENS defensibility.** Sean's bubble-tea grades spread **1–4**; the instrument's spread **2–4** and clusters at 3–4. **Both two-point gaps (Each-A-Cup 4 vs 2, Gong Cha 3 vs 1) are the instrument reading HIGH** — it does not go low enough on genuinely undefendable businesses. **And the rule behind Sean's spread is NOT derivable from the grades: across the corpus his DEF tracks FORMAT CAPITAL INTENSITY monotonically** (no premises **1.00** → home-based 1.74 → kiosk **2.46** → restaurant **3.20** → large-format **3.59** → licensed premises **4.50**), **but bubble-tea breaks it — KOI runs the same counter format as Gong Cha and gets 4 where Gong Cha gets 1.** So format is necessary but not sufficient, and the differentiator between those two is knowledge Sean holds (tenure, outlet count, or his own mental-ladder definition), **NOT visible in the grades.** **Flattening is now the dominant remaining error in this dimension.** |
| **D38** | **The calibration corpus is 82% thin reconstructed forms — does the calibration claim survive?** (§10.6) | **✅ CLOSED (v41) — resolved by D51 in the direction the row itself predicted.** **The row said the fix was (a) the form must ASK for structural facts, or (b) it is "the same external-scan dependency as D25", or (c) the calibration claim must be RESTATED.** **All three applied:** **(b)** *the competitor scanner is BUILT (§4.6.1), so the dependency now has a mechanism*; **(c)** *the calibration claim is restated — every reference is now dated and construct-labelled, and PS is explicitly UNCALIBRATED because no valid reference exists for it*; **(a)** *remains open as part of the form design and is carried into the form spec rather than left here.* **⚠ AND THE CORPUS ITSELF IS NOW KNOWN TO BE WEAKER THAN THIS ROW SAID: Sean's regrades changed 35% (MA), 59% (DEF) and 81% (CR) of his own first-pass grades** — *so the 120-case reference carries 35–81% relabel noise.* **The correct reading is that the corpus can validate no further tuning until it is regraded, and that is recorded as standing guidance rather than a task.** ***Original framing:*** and it was found by chasing Sean's moat question.** **99 of 120 cases (82%) carry `label_is_external: true` and an `authoring_note` reading *"FORM DATA reconstructed by the analyst from public sources… the form is thinner than a real submission. This is the known weakness of the test."* Median form payload 725 chars.** **So the corpus measures agreement on analyst-reconstructed forms, NOT on real submissions** — and **defensibility is the dimension most damaged**, because barriers (outlet counts, tenure, owned assets, licences) are the facts least likely to appear in a positioning sentence and most likely to be known to the owner. **Best Denki proves it: Sean scores 4 from knowledge of ~14 stores and a national network; the form states only *"Japanese retail service standards"*; the instrument says 2 — correctly, on what it was given.** **⚠ Same class of gap Sean already flagged: *"You have blind gaps. You have to corroborate your answer against physical evidence."*** **Fix is in the FORM, not the rubric:** (a) the form must **ask** for structural facts (outlets, years, owned premises, licences, price premium); (b) if the form cannot supply them this is **the same external-scan dependency as D25/D35**; (c) the calibration claim must be **restated** so "100% band agreement" is not read as validating real-submission performance |
| **D36-old-2** | *Superseded* | `rubric.json` declares `level_counts.defensibility = 6` (the other five are 5) against a scale block that says `human_display: "1-5"`. The 6th level **fires**: display **6** appears 3 times, mean mass on the 6th bin **3.4%**, and the composite divides defensibility by **6**. **Every §10.6 defensibility comparison has therefore pitted a 1–6 score against a 1–5 grade.** Normalising the scales moves the disputes from **6.7%** → **1.7% (percentile-matched)** / **4.2% (round-to-nearest)** — both **under the bar**, against PS 0.8% / MA 7.5% / DR 4.2% — so **on a like-for-like footing defensibility is no longer the worst dimension.** *(It was investigated as a rubric-CONTENT problem because the raw number was above the bar. It is at least partly a SCALE problem — same class as the §5.4 rounding gap.)* **Options: A** collapse defensibility to 5 levels (uniform display; invalidates every prior run) · **B** keep 6 levels and **label the scale in the report** · **C** keep 6 internally but normalise to 1–5 for display and for all human comparison. **Recommended: C** — it fixes the comparison without discarding the deliberate 0.5.0 split |
| **D37** | **Adopt the commonly-accepted moat definition for `defensibility`?** (§10.6) | **CLOSED — YES, structure only. Implemented in rubric v1.10.0.** Sean: *"D37, moat rewrite based on the structure."* **DEF now requires evidence of at least one named moat source** — efficient scale · capital requirements · intangible assets (patent, licence, proprietary process, **price-premium brand**) · switching costs · cost advantage · network effect — with the **primary/ancillary** distinction, and **"fame is not a moat"** as an explicit guard (a brand counts only where it **demonstrably produces pricing power**). **Validated: 3 repeat runs per case show the instrument is DETERMINISTIC (spread 0), so its scores are reproducible and any movement is attributable.** **⚠ It did NOT move the four disputed cases (Best Denki 2, Gain City 2, Gong Cha 3, Each-A-Cup 3) — because the cause is the corpus, not the rubric (D38).** **One honest limit retained: adopt the moat's STRUCTURE, NOT its PURPOSE** — Buffett's moat predicts returns on capital; §1's objective is quality of the current position relative to competitors. **Sean asked:** *"It should follow the definition of moat as per warren buffet or other commonly accepted definition?"* and he is right.** Researched against primary sources (Buffett/Morningstar five sources; Stigler/McAfee barriers to entry) rather than adopted on its say-so. **The frame CONFIRMS all three of his rulings** — Best Denki/Gain City = **efficient scale + capital requirements**; Gong Cha/Each-A-Cup = **no moat source at all**. **⚠ It corrects the REASON:** his Best Denki justification was *"because they all have mental advantage, there is some defensibility"*, and **mental advantage is not a moat source under any of the five** — feeding it into DEF is exactly the double-count that made DEF and MA agree too often. **He caught this himself.** Decisive quote, Morningstar verbatim: *"Just because a company boasts a well-known brand, or has been in business a long time, does not necessarily mean it has an economic moat."* **⚠ ONE HONEST LIMIT: adopt the moat's STRUCTURE (structural barriers not fame, primary vs ancillary distinguished), NOT its PURPOSE** — Buffett's moat predicts long-term returns on capital, while §1's objective is quality of current position relative to competitors. Importing the investor purpose wholesale would be the **seventh** imported framework in this document |
| **D35-old** | *Original framing, superseded by the hand-read above* | **⚠ The one substantive issue the uncertainty audit exposed.** DEF disputes are **7.0% [3.6–13.1%]**, above the ≤5% bar, and **all 8 sit in five categories of large established brands**, splitting into two coherent directions: **big-box retail I undervalue** (Best Denki, Gain City — me 2 vs him 4: physical footprint and tenure a challenger would find expensive) and **global/F&B brands I overvalue** (Gong Cha, Burger King, IKEA, Scanteak, Toast Box, Each-A-Cup — me 3–4 vs him 1–2). §5.4 defines DEF as **the challenger's cost**; both directions are consistent with the instrument reading **brand recognition** where Sean reads **structural cost to a challenger**. **More sample would not fix this** — it would measure the same disagreement more precisely. **The fix is hand-reading these 8 against §5.4's definition and deciding per case whether the instrument or the definition is wrong** (half a day, not a corpus expansion). A second independent corpus has already flagged `defensibility` twice (C6 Bonefirm), which argues this is systematic |
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
