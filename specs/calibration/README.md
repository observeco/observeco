# Calibration Set — OBS-SPEC-095

**Purpose:** determine whether Jev can reproduce an expert judgment about a business's
position from a thin, self-reported form. Everything else in the spec is conventional build;
this is the only unvalidated premise.

**Method:** `specs/obs-spec-095-business-review-lead-engine.md` §10.

> ⚠ **Contains client-derived material.** These reconstructions summarise engagements with real
> businesses (Bonefirm, GreenPackers, CaiCa, PetDirectory, plus two unnamed ventures). Treat as
> internal. Do not publish, and do not serve any of this text to the free-report form.

---

## What each input file is

A **form-shaped reconstruction of the engagement's starting state** — what the business owner
would have typed into the form *before* the analysis was done. Not the analysis. Not the
conclusions. The claims as they stood.

This is the only faithful analogue to production: in production Jev scores a prospect's raw
submission, not a finished document.

## The fidelity rule (the thing to get right)

**Include the client's own blind spots.** The analysis's job was largely to correct these. If the
reconstruction is written from hindsight — with the insights the analysis produced — the
calibration becomes trivially easy and proves nothing about production.

So each file deliberately preserves, where the record supports it:

- the **flawed framing** the owner arrived with
- the **competitor set they actually named** (often missing the real threat)
- the **superlatives and analyst jargon** they used
- the **demographic mistaken for a customer**

Conversely, it must not be artificially degraded: a real owner writes a paragraph, not a null.
The target is *what a competent but unanalysed SG founder would write*, not a worst case.

## What is NOT in the file

- The verdict, the band, the gates, or the recommended position
- Verified competitor facts (prices cross-checked, registries, review corpora)
- Anything the analysis discovered that the owner did not know

## Files

| File | Case | Labelled verdict |
|---|---|---|
| `inputs/01-bonefirm.json` | Bonefirm — menopause supplement | Feasible, one condition (B1) |
| `inputs/02-greenpackers.json` | GreenPackers — compostable packaging | Fringe; guerrilla warfare only |
| `inputs/03-petdirectory.json` | PetDirectory — pet directory | Position open; demand side unbuilt |
| `inputs/04-caica.json` | CaiCa — bubble tea | Reason-to-purchase weak; product repels |
| `inputs/05-sgfitness.json` | SG Fitness venture | White space in a specific segment |
| `inputs/06-saladshop.json` | SaladShop venture | CBD saturated; white space outside it |

## Status

- [ ] Inputs built — **awaiting Sean's fidelity check on 01**
- [ ] Sean's blind scoring run (D16)
- [ ] Rubric JSON
- [ ] Harness + negative controls
- [ ] Jev run
- [ ] Triage (§10.6 J1/J2/J3)
