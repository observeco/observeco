# FOUNDATION — Competitive Landscape Construction

**Status:** PROPOSAL v2 for Sean's guidance. Supersedes v1, which contradicted itself (§10).
**Date:** 2026-09-23
**Supersedes:** the input model in OBS-SPEC-095 §3.6 and the enrichment layer in §4.

---

## 1. The organising principle

**The competitive set is not "who looks like you". It is "what your customer can buy
instead, and why they would".**

Measured from the delivered analyses. Bonefirm's competitive set is not a list of supplement
brands — it is a **substitution taxonomy**, and its organising sentence says so:

> *"the customer can buy from any of these today. Each row includes its **reason-to-purchase**
> — why the customer buys from them instead of Bonefirm."*

Every row carries the same four columns: **Brand · What · Price · Why customers buy**.

The taxonomy is derived from **the customer's decision**, not the seller's self-image. That is
precisely why the owner cannot supply it: the owner knows who they lose to on the shelf; they
do not think in substitution tiers.

---

## 2. THE tier list — one list, used throughout this document

Eight tiers in a fixed order. Every later section uses **these names and these numbers**.

| # | Tier | What it captures | Always present? |
|---|---|---|---|
| **0** | **The Default** | What the customer does if they buy nothing at all — DIY, do-nothing, live with it | **Always** |
| **1** | **The Cheap Substitute** | The cheapest thing that does the job. **Sets the price floor** | **Always** |
| **2** | **The Direct Set** | Who else sells this exact thing | **Always** |
| **3** | **The Category Incumbent** | Who owns the category **the buyer thinks they are shopping in** | **Always** — and usually where the owner's blindspot lives |
| **4** | **The Adjacent Crossover** | Takes this customer's money on a different axis. Not a substitute — a rival for the wallet | When the buyer has competing priorities |
| **5** | **The Professional Route** | The expert or institutional path — doctor, clinic, consultant, agent | Regulated / high-trust categories |
| **6** | **The Indirect** | Dilutes the budget for the same person without competing on the product | Often |
| **7** | **The Emerging** | Who has entered recently and is not yet visible to the owner | **PAID only — Sean's decision** |

**Tier 7 is a derived tier, and it belongs to the paid service.** Sean's point: *"Tier 7 is
something most customers would expect us to derive for them"* — and the customer genuinely
cannot supply it, because the whole definition of the tier is that these entrants are not yet
visible to them. **It must be derived; it must never be asked.**

**Decision (2026-09-23): Tier 7 is out of the free report and belongs to the paid service.**
This is not only a scope cut — it closes a loop with what the site already sells. The Watch
page promises:

> *"New-entrant alerts, before they take your customers."*
> *"Who registered last quarter, who's quietly scaling, what they're charging."*

**That promise has been unbacked until now.** Tier 7 is what makes it real, and it is also the
only tier whose *value grows with the cadence* — new entrants appearing is quarterly news by
definition, whereas Tiers 0–6 are largely static. So Tier 7 belongs in the recurring product
both commercially and structurally.

---

## 3. Tier 7 is derivable — verified against open SG data

Probed `data.gov.sg` directly (`probe_acra_columns.py`). The ACRA open collection carries the
column set needed:

| Column | What it gives |
|---|---|
| `primary_ssic_code` / `primary_ssic_description` | **Industry classification** |
| `secondary_ssic_code` / `secondary_ssic_description` | Secondary activity |
| `registration_incorporation_date` | **Recency** |
| `entity_name`, `uen`, `entity_status_description` | Identity and whether still live |
| `primary_user_described_activity` | The entity's own plain-language description |
| `postal_code`, `street_name` | Location |
| `former_entity_name1..15` | **Rebrand history** |

53 columns, per-letter bulk CSV, monthly refresh, coverage to 2026-09-16.

**So Tier 7 is answerable from open data:**

> *"Who registered in SSIC `<code>` in the last N months, still live, in `<region>`?"*

**No API key, no gated access.** (ACRA's richer Business Profile Data API is gated behind a
FormSG request — we do not need it for this.)

### Three capabilities this unlocks beyond a name list

1. **Rebrand detection.** `former_entity_name1..15` — a competitor that changed its name is a
   position shift, and the analyses have already found one of these in the wild (the Gymmboxx
   → 24/7 Fitness rebrand surfaced during the fitness review).
2. **User-described activity.** A plain-language description that often reveals the actual
   positioning better than the SSIC code.
3. **Entity status.** We can exclude struck-off and dormant entities, so the list is live
   entrants rather than a registration graveyard.

### The genuine limits — state these, do not paper over them

| Limit | Consequence |
|---|---|
| **Registration ≠ trading** | A registered entity may never open. Tier 7 surfaces *candidates*, not established competitors. Must be labelled as such. |
| **Bulk CSV, not a query API** | Per-letter files, no "registered since X in industry Y" endpoint. At ~100 reports/month this is a real processing cost and a caching design question. |
| **SSIC granularity** | Filtering quality depends on the code depth actually populated. Verify per category before claiming precision. |
| **Only where ACRA covers it** | Companies and LLPs, not sole proprietorships registered under the Business Names Act in every case, and not unregistered activity. |
| **A window, not a feed** | Monthly refresh. Fine for a quarterly product; not real-time. |

**Presentation rule:** Tier 7 is labelled **"recently registered in your category"** — never
presented as confirmed competitors. That distinction is the difference between a finding and a
fabrication.

---

## 4. The mapping to Bonefirm — the same eight tiers, populated

This is the proof the tier list fits real work. Bonefirm's delivered analysis has eight
competitive sections, and they map onto the eight tiers:

| # | Tier | Bonefirm's section | Rows |
|---|---|---|---|
| 0 | The Default | §2.8 DIY (diet, exercise, weight-bearing) | the do-nothing path |
| 1 | The Cheap Substitute | §2.1 Generic bone health (mass retail) | Caltrate, Ostelin, Centrum |
| 2 | The Direct Set | §2.2 Joint health (glucosamine/collagen/NEM) | Blackmores, Nature's Way, Kordel's |
| **3** | **The Category Incumbent** | **§2.4 Menopause symptom brands (global)** | **The Better Menopause, Midi Health, Nutrafol** |
| 4 | The Adjacent Crossover | §2.3 Collagen (skin + joint) | Kinohimitsu, Ocean Health |
| 5 | The Professional Route | §2.6 Medical / doctor-adjacent | HRT, bisphosphonates, DEXA |
| 6 | The Indirect | §2.7 General women's health / MLM | budget dilution |
| 7 | The Emerging | *(not present in this analysis)* | — |

**Two things this makes visible.**

**First, the analysis lists its sections in a different order than the tiers.** §2.3 collagen
sits after §2.2 joint health, but collagen is Tier 4 and joint health is Tier 2. The analysis
ordered its sections by *product similarity*; the tier list orders by *the customer's
decision*. **That reordering is mine, and it is the point** — the decision order is what makes
the set generative.

**Second, the owner named only Tiers 1 and 2.** She said Caltrate, Blackmores, Kinohimitsu,
Kordel's, Nature's Way — a cheap substitute, a direct competitor, and one adjacent crossover.
**She did not name her Tier 3, which the analysis identifies as the real competitive frame.**
That omission is the blindspot, and it is now visible as an empty tier rather than as a vague
sense that her list was incomplete.

---

## 5. What generates the set — the minimum inputs

The inputs needed are **not** a competitor list. They are the facts that define the
**substitution space**. Three are already form fields; one is new and critical.

| # | Input | Why it is load-bearing | Already in form? |
|---|---|---|---|
| 1 | **What you sell** | Sets the product category | yes |
| 2 | **"On a best-endeavour basis, what do you think your target customer is trying to achieve?"** | **This generates the substitution space** | **NEW — the critical one** |
| 3 | **Who the customer is, and the trigger that makes them buy now** | Defines the wallet and the moment | yes (partly) |
| 4 | **Your price** | Sets the rung — determines which tiers are visible to this buyer | yes |
| 5 | **Your claim** — what you say makes you different | Sets the contested axis | yes |
| 6 | **URL** *(optional)* | Lets us read rather than rely on self-report | yes |

**Why the wording of input 2 matters.** Sean's correction to my version, and it is
structurally better in three ways:

1. **"Best-endeavour basis"** removes the pressure to be right. The question stops being a
   test the founder can fail and becomes an estimate they can give.
2. **"What do you THINK"** marks it explicitly as belief, not fact. That makes the answer
   **data about the founder's perception** — which is what we actually need, since the
   whole purpose is to compare their perception against the derived set.
3. **"Your TARGET customer"** scopes it. My wording implied the customer they currently
   have; the useful answer is about the customer they are aiming at.

**The framing consequence is the important one.** My version asked for a fact the founder
often does not have, which invites either a wrong answer or no answer. Sean's version asks
for a belief they certainly do have — **so the field becomes reliably answerable, and the
answer becomes a measurement rather than an input to be trusted.**

**It fits the tier model exactly.** The founder's stated target is a "what they think" input;
its job is to be **contrasted** with the derived set (§6 R5), never to define it. The wording
is what makes that honest rather than a trap.

**Where this field came from.** Ask a supplement founder "what do you sell" → "a menopause
supplement" → you get supplement brands, i.e. Tiers 1 and 2 only. Ask what the customer is
trying to achieve → "keep moving without pain, protect her bones before a fracture" → you get
exercise, physiotherapy, calcium, collagen, TCM and menopause brands. **That is Tiers 0–5.**

Competitors are defined by the **job**, not the product. Input 2 converts a product category
into a substitution space.

---

## 6. The generation protocol

Each tier is generated by a question and sourced a specific way — repeatable, not improvised.
The tier names and numbers are exactly those in §2.

| Tier | Generated by asking | Sourced via | Evidence to collect |
|---|---|---|---|
| **0 · The Default** | What does the customer do today if they buy nothing? | Reasoning — often no search needed | What the default costs; why people choose it |
| **1 · The Cheap Substitute** | What is the cheapest thing that does this job? | Search: job + "cheap / budget / free" | **Price** — this establishes the floor |
| **2 · The Direct Set** | Who else sells this exact thing? | Search + registry (SSIC / SFA / ECDA / MOH) | Price + claim |
| **3 · The Category Incumbent** | **Who owns the category the BUYER thinks they are shopping in?** | Search on the **buyer's** category word, not the seller's | **Claim** — what they say they own. The evidence the current pipeline never collects |
| **4 · The Adjacent Crossover** | What else takes this customer's money on a different axis? | The customer's other spend | Price + claim |
| **5 · The Professional Route** | What does the expert or institutional path look like? | Category-dependent (MOH, professional bodies) | What the professional path is and costs |
| **6 · The Indirect** | What dilutes the budget for the same person? | Adjacency | Price + claim |
| **7 · The Emerging** | Who entered recently? | ACRA registration recency, news, funding | Recency evidence |

**One test applies to every row in every tier:**

> **Can this row answer "why would the customer buy from them instead?"**
>
> A row that cannot is a **name**, not a competitor. This filters the set better than any
> similarity rule.

---

## 7. Robustness — how we know the set is good enough

| # | Test | Why |
|---|---|---|
| R1 | **Tier 0 is present and named** | Every analysis names it. If we cannot say what the customer does with no purchase, we have not understood the decision |
| R2 | **Tier 1 establishes a price floor** | The cheapest real alternative bounds what the buyer will pay. Without it, price has no referent |
| R3 | **Tier 3 is populated from the buyer's category word** | Where owner blindspots cluster. An empty Tier 3 means we used the seller's language |
| R4 | **Every row has a reason-to-purchase** | A name without a reason is not evidence of competition |
| R5 | **The owner's named set appears somewhere in the result** | If none of their names appear, we have misread the category — a hard error signal |

**R5 is the safety check.** The owner's list is wrong as a *complete* set, but it is strong
evidence about *their* category placement. If our derived set contains none of their names,
the likelier error is ours.

---

## 8. The human value chain

Sean's point: *"it is probably on me to provide the required guidance for you to chip away.
That is why the human value chain is important."*

| Stage | Machine does | Human does |
|---|---|---|
| **Generate** | Enumerate Tiers 0–7 from the inputs. Breadth is a machine's strength | — |
| **Source** | Fetch each candidate, extract price and claim | — |
| **Contrast** | Compute the delta between the owner's list and the derived set | **Adjudicate which tier is the real frame** |
| **Correct** | — | **Add what is not findable** |
| **Read** | Draft the read | **Decide whether it is honest** |

**Two places only the human can stand:**

1. **The un-findable fact.** Sean knew about Bonefirm's R&D; no fetch surfaces it. Private
   knowledge — a development effort, a relationship, a plan not yet public.
2. **The frame.** Which tier *is* the market. The machine can rank by evidence; only a human
   decides that the menopause brands outrank the shelf brands for this buyer.

That is the value chain: **the machine supplies breadth and evidence; the human supplies the
frame and the un-findable.** The protocol's job is to make the human's two contributions
**cheap** — present the derived set so a human can prune it in minutes, not re-derive it.

---

## 9. What this changes, and what is still open

**Changes:**

1. A **generation stage** is added between collection and scoring. It did not exist.
2. **One new form field** — *"what is your customer trying to achieve?"*
3. The owner's competitor list is re-roled from input data to **blindspot probe + safety
   check (R5)**.
4. The **fetch layer becomes load-bearing** — it is the evidence for Tiers 2–5.
5. **Refusal conditions are now definable:** if input 2 is unstated or unstateable, or Tier 2
   cannot be populated, we cannot construct a set and the report is refused — an observability
   limit on our side, not an input failure by the user.
6. **The free/paid line now follows the tiers** (Sean's decision, 2026-09-23). The free report
   covers **Tiers 0–6** — derived and scored, no Tier 7, no human adjudication. The paid
   engagement adds **Tier 7 (derived new entrants)**, the human frame, the full differentiator
   evaluation and the 90-day roadmap.

### The free/paid boundary, stated in terms of what is actually withheld

| | Free report | Paid engagement |
|---|---|---|
| **Tiers 0–6** | derived, with reasons | same, human-adjudicated |
| **Tier 7 (new entrants)** | **withheld** | derived, with rebrand history |
| **The frame** — which tier *is* the market | **machine-derived, labelled as such** | human-adjudicated |
| Differentiator evaluation, traps, positioning statement, roadmap | withheld | full |

**Why this line holds up.** Each side has something the other cannot have. The free report
genuinely cannot adjudicate the frame — there is no human in the loop. The paid service
genuinely cannot be replaced by the free report, because the most actionable single output
(Tier 7: who just entered your category) and the judgement (which tier is the real market) are
both withheld. Neither side is a partial copy of the other.

**Open questions for Sean:**

1. ~~Does the tier list generalise?~~ **RESOLVED — it generalises.** See §5a.
2. ~~Is "what is your customer trying to achieve?" the right field?~~ **RESOLVED** — Sean's
   wording adopted (see §5). Open sub-question: does "target customer" confuse a founder who
   has no clear target yet?
3. ~~Does the free report present a machine-derived frame?~~ **RESOLVED** — yes, machine-derived
   and labelled as such (Sean's decision).

### 5a. Tier generalisation — TESTED across all six analyses

`test_tier_generalisation.py` maps every delivered analysis's competitive-set sections onto the
eight tiers. Result:

| Tier | Bonefirm | GreenPackers | PetDirectory | CaiCa | SGFitness | SaladShop |
|---|---|---|---|---|---|---|
| 0 The Default | FIT | partial | FIT | partial | FIT | FIT |
| 1 Cheap Substitute | FIT | FIT | partial | FIT | FIT | FIT |
| 2 Direct Set | FIT | FIT | FIT | FIT | FIT | FIT |
| **3 Category Incumbent** | **FIT** | **FIT** | **FIT** | **FIT** | **FIT** | **FIT** |
| 4 Adjacent Crossover | FIT | partial | FIT | FIT | FIT | FIT |
| 5 Professional Route | FIT | absent | absent | absent | FIT | absent |
| 6 The Indirect | FIT | partial | FIT | partial | partial | partial |
| 7 The Emerging | absent | absent | absent | partial | partial | absent |

**MUST-present tiers (0–3): every one is present in every case.** Tier 2 and Tier 3 are FIT
6/6. **No analysis contained a competitive group the taxonomy could not place.**

**Tier 3 is FIT in all six** — and that is the load-bearing result, because Tier 3 is the
blindspot tier. It appeared in every engagement, under a different label each time:

| Case | Tier 3, as the analysis found it |
|---|---|
| Bonefirm | Menopause symptom brands — *"the real frame"* |
| GreenPackers | Incumbent plastic — *"THE MISSING SET... the default purchase for most F&B operators"* |
| PetDirectory | The discovery layer — *"where pet owners actually search for services"* |
| CaiCa | CHAGEE — *"not a bubble tea brand, a tea expert"* |
| SGFitness | The positioning column — the word each player owns |
| SaladShop | SaladStop! owning "health/wellness" |

**Six different industries, six different names for the same tier.** That is the evidence the
taxonomy is structural rather than an artefact of Bonefirm's category.

**Tiers 5–7 are legitimately category-dependent.** No professional route exists for bubble tea
or salad; Tier 7 is absent from most analyses simply because it was not covered. **Absence is
not failure — but it is worth noting that Tier 7 is the tier the analyses were weakest on,
which is consistent with it being the one that needs the ACRA derivation rather than human
research.**

**A methodological note.** The first run of this test reported GreenPackers as ABSENT on
Tier 3. That was **my mapping being too strict, not the taxonomy failing** — I required a
section literally about "the buyer's category word" and missed that §2.2 *"the incumbent
plastic purchase... the default purchase for most F&B operators"* is the same thing. The test
found a real ambiguity; the fix was to the mapping, and the lesson is that a tier test is only
as good as its reading of the sections.

---

## 10. Why v1 was replaced

v1 of this document defined its tiers **twice, differently**. §1 was derived from Bonefirm's
section order; §3 was written as an idealised protocol from scratch. The two were never
reconciled, so **tiers 3 and 4 meant opposite things in the same document** — §1 put the
adjacent crossover at 3 and the category incumbent at 4, while §3 had them the other way
round. Tier 7 differed too: §1 had "Indirect" (Bonefirm's §2.7), §3 had "Emerging."

v2 fixes this by:

1. Defining the tier list **once** — §2 — and referencing it everywhere else.
2. Ordering it by **the customer's decision** rather than by product similarity.
3. Stating explicitly in §3 that the reordering relative to Bonefirm's section order is
   deliberate and mine.

**The lesson worth keeping:** a document that defines its central vocabulary twice will
contradict itself. And a document that reproduces a known contradiction — even labelled as
historical — reintroduces the ambiguity it claims to fix. Define once, reference everywhere,
and remove the old version rather than archiving it in place.
