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
| **7** | **The Emerging** | Who has entered recently and is not yet visible to the owner | **Always — and derived, not asked** |

**Tier 7 is a derived tier.** Sean's point: *"Tier 7 is something most customers would expect
us to derive for them."* The customer genuinely cannot supply it — the whole definition of the
tier is that these entrants are not yet visible to them. **It must be derived, and it must
never be an optional or paid-only tier.**

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
| 2 | **What your customer is trying to achieve** — the job they are hiring you for, not what you make | **This generates the substitution space** | **NEW — the critical one** |
| 3 | **Who the customer is, and the trigger that makes them buy now** | Defines the wallet and the moment | yes (partly) |
| 4 | **Your price** | Sets the rung — determines which tiers are visible to this buyer | yes |
| 5 | **Your claim** — what you say makes you different | Sets the contested axis | yes |
| 6 | **URL** *(optional)* | Lets us read rather than rely on self-report | yes |

**Why input 2 is the one that matters.** Ask a supplement founder "what do you sell" → "a
menopause supplement" → you get supplement brands, i.e. Tiers 1 and 2 only. Ask "what is she
trying to achieve" → "keep moving without pain, protect her bones before a fracture" → you get
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

**Open questions for Sean:**

1. **Does the tier list generalise?** It fits Bonefirm. Two more analyses would settle it — I
   would derive the set for GreenPackers and PetDirectory and check whether the same eight
   tiers emerge, or whether tiers are category-specific.
2. **Is "what is your customer trying to achieve?" the right field?** It generates the
   substitution space — and it is also the field a struggling founder is least likely to
   answer well. Is there a better way to ask it?
3. **How deep does the free report go?** Tiers 0–3 with reasons is already more than the owner
   knows. Tiers 4–7 plus price mapping starts to *be* the paid deliverable.
4. **Where does the human sit in the free path?** The chain in §8 assumes a human adjudicates
   the frame. The free report has no human. Either it ships a machine-derived frame and says
   so — weaker, and labelled — or it presents no frame at all, only the set and the contrasts.

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
