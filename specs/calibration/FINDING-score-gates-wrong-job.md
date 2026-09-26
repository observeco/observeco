# FINDING — the score gates were doing the WRONG JOB (rubric 0.9.0)

**Date:** 2026-09-26
**Trigger:** the 55-case fresh-data validity set. The defect was invisible in 20 cases.

**Rubric:** 0.8.0 -> **0.9.0**

---

## 1. How the fresh data found it

The original 20-case corpus gated twice — 10%. Both were explainable (a closed business
and a dying mid-tier brand), so the gate looked like it was working.

On the fresh 55, it fired **9 times in 43**. And the extra firings were not marginal
businesses. They were:

```
KFC  ·  Burger King  ·  Zoff  ·  Harvey Norman  ·  Spectacle Hut
Pure Fitness  ·  Virgin Active  ·  R&B Tea
```

**Live. Large. Profitable.** The rubric was telling a client *"we cannot assess your
business"* about KFC.

That is the value of an independent sample: at n=20 the defect was a rounding error; at
n=55 it was a fifth of the corpus and obviously wrong.

## 2. The defect is semantic, not numeric

My first instinct was to move the threshold. **Wrong instinct** — there is no threshold
that fixes this, because the gate is reading the right number and drawing the wrong
conclusion.

`defensibility` display 1 means:

> *"No moat. There is no differentiator at all."*

**The model is not wrong about KFC.** A generic fried-chicken chain genuinely has no
moat — the same chicken, the same fryers, no proprietary input, no owned channel. Score
1/6 is a *correct* reading.

The defect is what the gate does with it:

```
"this business has no moat"        -> a valid, informative, LOW score
"we cannot assess this business"   -> a refusal
```

**These are different statements, and conflating them destroys the signal.** A no-moat
business is eminently assessable. Refusing it throws away exactly the negative finding
the report exists to deliver — the client paying S$500 to learn their positioning is
weak would instead be told nothing.

## 3. Measured: the gate does not separate dead from alive

I did not assume this. I checked which businesses carry `defensibility=1`:

```
defensibility = 1 and the business is DEAD  : 2   (closed business, Gong Cha)
defensibility = 1 and the business is ALIVE : 8   (KFC, Burger King, Zoff, ...)
```

**8 of 10 firings were false refusals.** The gate does not distinguish failure from
ordinariness. It distinguishes *has a moat* from *has no moat*, and refuses the latter.

## 4. It contradicted a principle this project had already settled

`FINDING-assessability-gate.md`, written days earlier, states the rule:

> *"Gates should tell the user 'cannot assess', not 'is this business bad'."*

The `defensibility` gate is a **score dimension** gating on its own low score. That is
precisely the error the principle forbids. I wrote the rule, applied it to three dead
gates, and left the two live ones committing the same violation — because at n=20 they
almost never fired.

## 5. The fix, and it repairs two defects at once

**Remove the score gates. Keep the assessability gate** — that one asks the right
question (*"can the method work here?"*), and it fires on ASML alone.

| | before | after |
|---|---:|---:|
| False refusals | 8 | **0** |
| `Fragile` band reachable | no | **yes — 5 cases** |
| Gates / jobs | 2 / wrong | **1 / right** |

```
case                  dims     now    fixed   band      status
BT05-r&b              32214    GATE     40     Contested  ALIVE
EL02-harvey           32212    GATE     32     Fragile    ALIVE
EW02-zoff             32212    GATE     33     Fragile    ALIVE
EW04-spectacle        32213    GATE     32     Fragile    ALIVE
FF02-kfc              32313    GATE     43     Contested  ALIVE
FF03-burger           32413    GATE     48     Contested  ALIVE
GY04-pure             32313    GATE     43     Contested  ALIVE
GY05-virgin           32312    GATE     39     Contested  ALIVE
N1-closedbusiness     32112    GATE     31     Fragile    DEAD
P5-gongcha            32212    GATE     32     Fragile    DEAD
```

**The second repair:** `Fragile` (5-37) was mathematically unreachable — every gating case
had all-2s satisfied so the minimum composite was 38. Removing the score gates makes it
reachable, and the five cases that land there are **exactly the closed and position-less
ones.** The vestigial band was a symptom of the same defect, not a separate problem.

## 6. What this fix does NOT solve — and I should not paper over it

```
N1-closedbusiness (DEAD)          31   Fragile
EL02-harvey       (ALIVE)         32   Fragile
```

**A 1-point gap between a closed business and a live major retailer.**

The rubric scores both as having no distinct position. **That is defensible**: Harvey
Norman sells the same brands at within 3-8% of every rival, so by positioning theory it
genuinely holds no position. And Gong Cha — the one business in this corpus with a
*documented death* — scores 32, adjacent to Harvey Norman's 32.

So the honest statement is:

> **The rubric measures positioning, not survival.** A business with no distinct position
> scores low whether or not it is still trading. That is what a positioning instrument
> should do — but it means a low score is NOT a prediction of failure, and the report
> must never present it as one.

**The alternative fix I did not take:** keep `mental_advantage` floor 2, remove only the
`defensibility` gate. `mental_advantage=1` fires on **exactly one case** — the closed
business. That is a *correct* firing, so that variant is defensible and arguably tighter.
I chose no-score-gates because "a dead business scores 31" is more useful to the client
than "we refuse", and one gate doing one job is easier to reason about. **This is a
judgement call, not a measurement.**

## 7. Methodology error I made — recorded because it will recur

I applied the 0.9.0 rubric change **while the 55-case run was still in flight.** That
split the corpus across two rubric versions:

```
rubric 0.8.0 -> 40 v2 cases   (gates ON)
rubric 0.9.0 -> 14 v2 cases   (gates OFF)
```

**A corpus scored under two rubric versions is not a valid test** — cases early in the
batch gate and late ones do not, purely by timing. It produced a spurious result (SM04 at
37 "Fragile") that would have looked like a finding.

**Caught by checking `rubric_version` in every run file, not by trusting the summary.**

**Rule for next time:** never edit `rubric.json` while a batch run is executing. Wait for
exit, or score into a versioned output directory. Any result from a corpus spanning
versions must be discarded and re-run.
