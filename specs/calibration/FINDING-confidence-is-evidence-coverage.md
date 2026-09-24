# Finding — confidence is an evidence-coverage report, not a model property

**Date:** 2026-09-23
**Raised by:** Sean — *"Don't you think your low confidence scores have a recurring theme?"*
**Status:** design error confirmed. Corrects spec §4.5 and §5.1.

## The pattern

| Case | Dimension | Conf | Needs competitor evidence |
|---|---|---|---|
| bonefirm | competitive_room | **0.80** | yes |
| bonefirm | position_availability | **0.19** | yes |
| observeco | competitive_room | **0.38** | yes |
| observeco | position_availability | **0.45** | yes |

Self-reportable dimensions (market headroom, defensibility, demand reach), all six
measurements across two cases: **0.56 – 0.80**, mean **0.64**.
Competitor-dependent dimensions: **0.19 – 0.80**, mean **0.46**.

In **ObserveCo** the two competitor-dependent dimensions are the two lowest, in order.
In **Bonefirm** `position_availability` is the lowest by a wide margin (0.19 vs next 0.65).

## The exception that identifies the real cause

**Bonefirm's `competitive_room` scored 0.80 — the HIGHEST in that case.** That breaks the
simple "needs competitor evidence" story, and the reason is instructive:

> The Bonefirm founder **volunteered** competitor prices — *"probably S$0.50 to S$1 a day
> for the pharmacy brands."*
> The ObserveCo site gives competitor prices for the free substitutes but **no prices for
> the paid comparables**, and `competitive_room` fell to 0.38.

So the theme is **not** "this dimension is hard." It is:

> **Confidence tracks how much competitor EVIDENCE we actually supplied — not the model's
> certainty and not the volume of the input.**

## What evidence the pipeline actually collected

| Evidence type | Collected? |
|---|---|
| Competitor **names** | Yes — owner self-report, both cases |
| Competitor **prices** | Bonefirm only, because the founder volunteered them |
| Competitor **positioning** | **Never.** No competitor site was ever fetched |

`position_availability` asks *"is the position already owned?"* That question **cannot be
answered without competitor positioning**, and the pipeline has never collected any. Jev is
being asked to judge ownership with zero visibility into what the owners say.

**It is answering honestly. The question is unanswerable as fed.**

## The design error

The spec says (§4.5, §5.1):

> *"Per the cannot-refuse contract: the form answers alone must carry all five scores.
> Enrichment is best-effort behind a hard timeout. A failed fetch degrades depth, never
> existence."*

**That is wrong, and this data proves it.** The form answers cannot carry
`competitive_room` and `position_availability` — that is **45% of the composite weight**.
Those two dimensions are structurally dependent on evidence the owner cannot reliably
supply and the form never asks for.

**I declared the layer that makes 45% of the score possible to be optional.**

Worse, the input model I proposed (ask the owner) *cannot* fix it. Asking "who do you
compete with?" returns names. It does not return their positioning, and a self-report of
competitor positioning would be second-hand at best.

## The unifying insight

This also explains the flat profile — every dimension scoring 3 or 4 on ObserveCo, nothing
low, which I had tentatively blamed on the rubric not discriminating mid-range.

**It is the same phenomenon.** When Jev lacks evidence, it hedges toward the middle of the
scale. The clustering and the low confidence are one signal, not two:

> **Low confidence and mid-range scores are both the model correctly reporting that it
> cannot separate what it cannot see.**

So the rubric does not need a wider range. **It needs evidence.**

## What this changes

1. **Confidence is a coverage report, not a quality score.** It should be presented to Sean
   as *"we did not gather enough evidence for this dimension"* — actionable on our side —
   rather than *"the model is unsure"* — which reads as a model limitation.
2. **Enrichment is load-bearing, not best-effort.** The competitor-fetch layer must be
   promoted. Specifically: fetch each named competitor's site, extract what they claim, and
   feed that to `position_availability` and `competitive_room`.
3. **The cannot-refuse contract must be restated.** If competitor evidence cannot be
   observed, we cannot credibly score 45% of the composite. Refusal is correct there — and
   it is an **observability limit on our side**, not an input-quality failure by the user.
4. **Dimension-level evidence requirements must be declared.** Each dimension should name
   the evidence it needs, and the pipeline should check coverage before asking the model.
   A dimension asked without its required evidence should return `unscored`, not a hedge.

## The honest note

I built a form that asks the owner for the things the owner is least able to supply, then
marked the layer that could supply them as optional, then read the resulting low confidence
as noise rather than as the diagnostic it was.

**The low confidence was the instrument telling me the evidence was missing. I read it as
the instrument being unsure.**

## Reproduce

`python3 specs/calibration/diagnose_confidence.py`
