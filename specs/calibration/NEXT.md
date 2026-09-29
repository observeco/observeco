# OBS-SPEC-095 — WHAT'S NEXT

Written after the calibration work closed the D1 bar. Four findings change the shape of
what remains, and they are stated first because they are the reason the old next-step list
is wrong.

---

## The four findings that reset the plan

**1. THERE IS NO PRODUCTION SCORER.** `jev` appears only inside `specs/calibration/`. Every
one of the 120 runs was made by the calibration harness, which is a research instrument.
§5.3 of the spec requires "one rubric, two implementations" — the harness and the production
scorer must read the same file or calibration validates something that never ships. **The
second implementation does not exist.**

**2. THE RUBRIC A SCORER WOULD LOAD IS STILL 0.9.0.** `specs/calibration/rubric.json` is the
five-dimension 0.9.0 file. **`position_strength` is absent from it.** So none of the v1.1–v1.8
work is deployed anywhere: the dimensions are calibrated in files that nothing serves from.

**3. THE SPEC'S OWN CANARY CORPUS IS 5 OF 6 MISSING.** §10.1 names six real engagements
(GreenPackers, Bonefirm, CaiCa, PetDirectory, SGFitness, SaladShop). Of those, **only
Bonefirm exists in the corpus.** The 120-case corpus built here is a different and much
larger thing — a *population* sample — and it does not replace the canary. §10.6's launch
gate cannot be run at all with five cases absent.

**4. THE SPEC ALREADY PREDICTED THE HIGHEST-VALUE WORK.** §10.5 item 5: *"There is no human
baseline... The cheapest fix is one hour of work: Sean scores the six cases blind... that
single number is the only evidence that the instrument measures something real."* **Sean's
120 blind dimension grades have delivered this, at twenty times the scale the spec asked
for.** That gap in the spec is closed by the regrade corpus, and the spec should say so.

---

## Track A — MVP-0, which does not depend on any of this

§11 splits the ship. **MVP-0 is page + form + CRM capture + Stripe. No free score.** It is
gated on nothing in §10. **This is what unblocks revenue, and it is blocked by legal and
compliance work, not by calibration.** From the spec's own gap list:

| # | Item | Spec ref | State |
|---|---|---|---|
| A1 | `privacy.html` — a launch **prerequisite**, not a footer | §3.4 | **not built** |
| A2 | The form is an **open relay** — the spec calls this "the most serious gap in the design" ⚠ | §3.7 | **not fixed** |
| A3 | Input-quality floor (D12, open) | §3.8, §3.10 | open |
| A4 | `/unsubscribe` must be real — currently 404 | §6.6 | **broken** |
| A5 | Retention must name a period | §7.5 | undefined |
| A6 | Two-purpose consent model + processor register | §3.2, §3.3 | designed, not built |
| A7 | Untrusted input must be contained | §3.9 | not built |

**A2 is the one I would do first.** An open relay on a public form is an abuse vector that
gets a domain blocklisted, and it is independent of every scoring question.

## Track B — MVP-1, the free scored report

| # | Item | Why | State |
|---|---|---|---|
| B1 | **Build the production scorer** reading the rubric file | §5.3 — without it calibration validated nothing that ships | **missing** |
| B2 | **Promote the chosen rubric to `rubric.json`** | nothing serves v1.8.0 today; the live file is 0.9.0 without RS | pending decision |
| B3 | **Restore the 6 canary cases** as form-shaped inputs | §10.1; 5 of 6 absent, so §10.6 cannot be run | **5 missing** |
| B4 | **Multi-control negative set** | §10.5 #4 — one control proves the scorer *can* fail, not that it fails for the right reason | 2 candidates only |
| B5 | **Update §10.6's launch gate** to the agreed bar | it still says "every dimension within ±1 level"; D1 replaced that with band agreement | stale |
| B6 | **Wire §10.2 provenance fields** into the report | `rubric_version`, `prompt_hash`, `input_hash`, `model_id`… | not built |
| B7 | **Canary on a schedule** + degradation ladder | §10.3, §10.4 | not built |

## Track C — calibration, the small remainder

| # | Item | State |
|---|---|---|
| C1 | Defensibility — Best Denki and Gain City sit at 2 against Sean's 4; `defensibility` is the last dimension with a live construct complaint | partial |
| C2 | §10.5 #1 — the gate measures **agreement, not accuracy**; correlated errors agree and are still both wrong | inherent, must be stated |
| C3 | The top end is the weakest region (−7.7 for businesses Sean rates 80+), and it is off-target per D3 | known, low priority |
| C4 | A second independent human grader — would separate calibration from overfitting on Sean's 120 labels | not available |

---

## Recommendation, in order

**1. MVP-0, because it needs none of the calibration work and it is what sells the S$500
engagement.** A2 (open relay) then A1 (`privacy.html`) then A4 (unsubscribe). These are
legal exposure, not polish.

**2. B1 + B2, because they are the difference between a validated instrument and a
validated *file*.** A rubric that nothing loads is a research artefact. This is one build
item and it makes everything done here real.

**3. B3, because the launch gate in §10.6 is currently unrunnable.** Five of six canary cases
do not exist. §10.6 is the gate the spec itself set for shipping the free report.

**4. B4 + B5, because the gate as written tests the wrong thing** (dimension ±1 rather than
band) and has too few controls to distinguish a broken scorer from a lucky one.

**5. C1 last.** `defensibility` is the only dimension with a live construct complaint and it
is a one-point gap on two cases. It does not gate anything.

---

## The correction this turn produced

**The spec's §10.5 item 5 asked for one hour of Sean's blind scoring and called it "the only
evidence that the instrument measures something real." That now exists at 120 graded
businesses across 27 categories — twenty times the scale requested — plus a 116-case
product-level band measurement, a measured noise floor (±0.4 pts), and a 100%-within-one-band
result on the target segment.**

**The spec should be updated to record that the human baseline it asked for is no longer
missing.** Leaving the paragraph as-is would understate the evidence and invite someone to
redo work that is done.
