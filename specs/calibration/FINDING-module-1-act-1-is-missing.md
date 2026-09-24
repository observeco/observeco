# Finding — the pipeline skipped the first act of Module 1

**Date:** 2026-09-23
**Raised by:** Sean — *"Never expect the list of competitors provided by user to be the full
list. It is up to you to shape it."*
**Severity:** structural. This is not a bug in a step; a whole step is missing.

## What the method says

From `positioning-strategy` (Module 1, "Analyze Competition"), in order:

1. View industry through the positioning lens — hard (macro trends) + soft (consumer perception)
2. **Industry Panorama — macro data table + brand physical/mind performance table**
3. Pin down your position — category membership + market standing
4. Mind Snapshot — category perception → brand perception → differentiated perception
5. Advantage Quadrant
6. Four-Dimension Competitor Model — filter by home territory, price band, market share, mind perception
7. Mind Map — place yourself and rivals in four tiers

And from the Gu Junhui Vacancy Method, step 2: **"don't attack a hilltop already held by a
strong brand"** — which requires knowing who holds the hilltops.

**Steps 1, 2, 6 and 7 are all acts of competitive-landscape construction.** The whole of
Module 1 is *building the competitive set*. Everything downstream — the strategy mode
(leader/#2/#4/#7+), the open spot, the differentiator — is derived **from that set**.

## What my pipeline did

```
owner supplies names  ->  Jev scores 5 dimensions  ->  done
```

It treated the owner's competitor list as **given data**, and asked Jev to score position
availability and competitive room against it. There is no step in my design where the
competitive set is *constructed*. Module 1 step 2 — the one that produces the Industry
Panorama — **does not exist in my pipeline.**

## The measured size of the gap

The owner names 3–5 competitors. The delivered analyses carry:

| Case | Named by owner | Rows in the analysis's competitive set |
|---|---|---|
| Bonefirm | 5 | **17** |
| GreenPackers | — | **36** |
| PetDirectory | — | **13** |

The Bonefirm founder named Caltrate, Blackmores, Kinohimitsu, Kordel's, Nature's Way.
**Every one is mass-market retail.** The analysis's set of 17 contains a four-part
structure the owner's list does not hint at: generic bone health (mass retail), joint health
(glucosamine/collagen/NEM), **collagen as a beauty crossover**, and **menopause symptom
brands (global)**. The analysis then says the *last* group is the real competitive frame.

**The owner's list is systematically biased — not randomly incomplete.** They name the
brands they already lose to on the shelf, because those are the ones they see. They are
blind to the category entrants competing for the same customer on a different axis.

## Why I read the low confidence wrong

The previous finding established that `competitive_room` and `position_availability` are the
low-confidence dimensions because competitor evidence is missing. That was right but shallow.

**The deeper cause: I was asking Jev to judge a competitive landscape against a set the
owner had already biased, and there was no evidence step to correct it.** The confidence was
low because the model was being asked to reason about a landscape nobody had built.

## What this actually is

Sean's framing: *"the competitive landscape is key to positioning theory being of upmost
value."* Positioning is **relative by definition** — a position is a place in the mind
*relative to* who already occupies it. Without the landscape:

- "Is this position available?" has no referent
- "Is there competitive room?" has no referent
- The warfare mode (leader / flanker / guerrilla) and therefore the whole strategy
  **cannot be selected**

**An owner-scored form is not a positioning analysis. It is a self-assessment.** That is the
error, and it explains every symptom this exercise has produced: the flat profile, the
mid-range hedging, the low confidence, and the "position availability" question that could
not land.

## The corrected pipeline

```
1. COLLECT      owner: what they sell, price, their claim, how THEY see competitors
2. DERIVE       build the competitive set from the CATEGORY — not from the owner's list
                  - registry data where it exists (SFA / ECDA / ACRA / MOH)
                  - category search: who competes for this buyer's wallet, on any axis
                  - the four-part structure: direct, substitute, adjacent, emerging
3. EVIDENCE     fetch each derived competitor: what they claim, what they charge
4. CONTRAST     the owner's list vs the derived set  <-- this gap IS a finding
5. SCORE        dimensions now have a landscape to be judged against
6. READ         the report leads with the contrast, not the score
```

**Step 4 is new and it is the most valuable output of the whole product.** The owner named
the shelf; the market is the menopause category. Telling them that — with names and
evidence — is worth more than any score, and it is only visible because we asked for their
list *and then ignored it as an input*.

## What the owner's list is actually for

Not as input data. As a **blindspot probe**. Its role is inverted:

- It is **evidence of the owner's perception**, which the method treats as a fact to be
  worked with ("treat consumer's perception as fact") — but the owner's perception of their
  competitors is exactly the thing most likely to be wrong
- The delta between their list and the derived set measures the size of the blindspot
- A small delta = a sophisticated owner. A large delta = the report's first finding

## Consequences for the design

1. **A step must be added, not fixed.** Competitor derivation is a pipeline stage, sitting
   between collection and scoring. The spec has no such stage.
2. **No dimension can be scored until the landscape exists.** This replaces the previous
   finding's "competitor evidence missing" — the requirement is stronger: the *set itself*
   must be constructed.
3. **Refusal is correct and not a failure.** If the category cannot be derived (no registry,
   no findable peers, a genuinely novel offering), we cannot produce a positioning read at
   all — by definition. That is the observability limit, and it should be surfaced as such.
4. **The free report's honest deliverable.** We can build a competitive set and read the
   owner's claim against it. We cannot do the full mind map, the four-tier model, or the
   warfare-mode selection — those need more evidence. That is a clean free/paid boundary
   that does not depend on a score being right.

## Reproduce

Counts measured from each analysis's competitive-set section
(`awk '/^### 2\.|^## 2\./,/^## 3\.|^### 3\./' <file> | grep -c '^| \*\*'`).
