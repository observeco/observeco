# Divergence report — Bonefirm (case 01)

**Date:** 2026-09-23
**Model:** `jev-1.13.0` (no drift — expected and returned identical)
**Rubric:** 0.1.0
**Verdict: the launch gate FAILED on case 1.** But the structure of the failure is more
informative than a pass would have been.

## The three views

| Dimension | Key | Jev | Jev conf | Sean (blind) |
|---|---|---|---|---|
| Market headroom | 4 | **4** ✓ | 0.72 | **4** ✓ |
| Competitive room | 3 | 2 (−1) | **0.85** | 4 (+1) |
| Position availability | 4 | 3 (−1) | **0.19** ⚠ | 5 (+1) |
| Defensibility | 2 | **2** ✓ | 0.75 | 4 (+2) |
| Demand reach | 3 | **3** ✓ | 0.57 | 2 (−1) |
| **Composite** | **63 Viable, conditional** | **54 Contested** | | **79 Strong** |

- **Jev matched the key on 3 of 5 dimensions** — including the binding constraint.
- **Jev's band diverged**: Contested vs Viable, conditional.
- **Sean diverged on 3 of 5**, and by a larger margin (+2 on defensibility).
- **Neither matched the band.** Gate not met.
- **Sufficiency split:** Jev `sufficient`, Sean `insufficient`.

## Finding 1 — Jev got the dimension that matters most exactly right

Defensibility: **Jev 2, key 2, confidence 0.75**, distribution `{0: 0.30, 1: 0.70, 2: 0, 3: 0, 4: 0}`.
It is confident the answer is level 1 — *"Fragile. The differentiator exists on paper but a
competitor can copy it in weeks."*

That is the analysis's central finding: **"NEM is a commodity, not a moat."** Jev reached it from
the form alone, in one call, with no access to the analysis. It also reached demand reach 3 and
market headroom 4 correctly.

**This is the single most encouraging result in the run.** The hardest judgment — the one the
whole engagement turned on — was reproduced, confidently, from thin self-reported input.

## Finding 2 — Jev's competitive-room miss is arguably Jev being RIGHT

Jev scored 2 (*"Very little. A dominant player or a severe price floor; the business is
structurally squeezed"*) at **confidence 0.85**. My key said 3.

The founder's own words in the input: *"Price. Anyone can buy NEM capsules on their own from
Watsons or online for much less. Competitors also keep launching cheaper versions of the same
thing."*

The analysis's own numbers support Jev: Caltrate at **SGD 0.30–0.50/day vs Bonefirm's SGD 8.50/day
— 17–28× cheaper**, and the analysis explicitly says *"Caltrate owns the price floor; Bonefirm
cannot win on price."* That is a **severe price floor**, which is level 1, which is Jev's answer.

**Verdict: J3, leaning J2.** My label of 3 was generous, and Jev's reading is better grounded in
the input the founder actually gave. **The label is the likelier error, not the model.** Hand-read
required before accepting, per §10.6 — do not default to "Jev is wrong."

## Finding 3 — position availability at confidence 0.19 is a RUBRIC defect, and it exposed a
## method/rubric mismatch

Distribution: `{0: 0.02, 1: 0.40, 2: 0.28, 3: 0.24, 4: 0.06}` — confidence **0.19**.

This is not a middling answer; it is **two competing readings the model cannot separate**. Per the
spec's own confidence doctrine, a dimension at 0.19 **must not be displayed as a trusted number**.
So Jev's position score is not evidence about Bonefirm. It is evidence that **the question is
badly formed.**

**And the reason is the important part.** The rubric's instruction says *"consider what the
business actually claims, as stated."* Jev complied. The claimed position is *"the only supplement
Asian women need"* — a superlative every supplement brand makes, so as stated it is **mostly
taken**. Jev's 0.40 mass on level 1 is a defensible reading of the literal claim.

But the **analysis** did not judge the claimed position. It went looking for an available one and
found *bone/joint × menopause*, then scored that. **The analysis answers a different question than
the rubric asks.**

| | Question asked |
|---|---|
| **Rubric (my design)** | Is the position they CLAIM still open? |
| **The method (the analyses)** | What position IS open for them? |

**This is the most valuable output of the run.** Two consequences:

1. **My label of 4 was wrong for the rubric** — I labelled the *available* position, not the
   *claimed* one. The key and the rubric were answering different questions. That is a J2-class
   finding about my own specification, not a model defect.
2. **It clarifies the free/paid boundary, which the spec did not have.** The free report measures
   *whether the claim you already make is available*. The paid engagement's value is *finding the
   claim that is* — which is exactly what the six analyses did, and exactly what a rubric scoring
   the stated claim cannot do. **That is a clean, honest statement of the S$500 delta.**

## Finding 4 — Sean's divergences

| Dimension | Sean | Key | Δ | Read |
|---|---|---|---|---|
| Defensibility | 4 | 2 | **+2** | The largest disagreement in the run. Possibly reasoning from the founder story + education engine, which the analysis *does* call the only durable moat — but as *hard to build*, and the input does not claim it is built |
| Competitive room | 4 | 3 | +1 | Read the market as favourable |
| Demand reach | 2 | 3 | −1 | Only low score; flagged before the comparison as a possible demand over-weight |
| Position availability | 5 | 4 | +1 | Perfect score on a contested proposition |

**Sean's band was Strong (79).** The analysis's own verdict is *"feasible, with one condition"* —
which is materially more cautious. Worth understanding why, because a human baseline that reads
consistently more optimistic than the method is itself a finding.

## Finding 5 — the sufficiency split

Jev: `sufficient`. Sean: `insufficient`. Both defensible and they measure different things — Jev
was asked whether the *content* supports assessment; Sean may have read the bar as "supports a
report I would stand behind."

**This is a §3.10 threshold question, and it is unresolved.** It matters because G6 is what routes
a submission to the guidance email instead of a score.

## What must change before case 02

1. **Re-label position availability** to match the rubric — score the *claimed* position, or change
   the rubric to the method's question. **These are different products**; this is a design decision
   for Sean, not a fix.
2. **Narrow the position-availability question.** A 0.19 confidence means it is two questions
   wearing one label.
3. **Add a confidence floor to the display rule.** A dimension below ~0.5 should not render as a
   number. The spec says this in principle (§5.4) and the run proves it is needed in practice.
4. **Re-examine the competitive-room label** given Finding 2.
5. **Calibrate the sufficiency threshold** (Finding 5).

## The honest headline

**The gate failed. But Jev reproduced the analysis's central judgment — that the differentiator is
not defensible — from the form alone, confidently.** The band divergence is driven by one label
that is probably mine (competitive room) and one question that is probably badly formed (position
availability). **Nothing here says the scorer cannot work. It says the rubric is at v0.1 and two of
its five questions have identifiable defects.**
