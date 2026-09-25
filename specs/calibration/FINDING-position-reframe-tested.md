# FINDING — Position reframe: TESTED, and it works

**Date:** 2026-09-25
**Status:** EXPERIMENT CONFIRMED. Predicted in `RESEARCH-confidence-and-position.md` §6,
then tested with falsification criteria recorded beforehand.

---

## What was tested

`position_availability` is the rubric's weakest dimension (25% of the composite weight, lowest
confidence in every run). The research finding: it asks an **absolute** question ("is a
position still open?") about a phenomenon the positioning literature says is **always
relative** — mental advantage is measured against *what a brand of that size would be
expected to own*.

**Method that isolates the change:** same state text, same model, same cases. **Only the
question changes.** Old = absolute. New = relative.

---

## Result

| Case | Ground truth | OLD (absolute) | NEW (relative) |
|---|---|---:|---:|
| KOI | market leader | 1.12 | **2.60** |
| CaiCa | failing | 1.17 | 1.22 |
| C5 hawker | Michelin star, 1 stall | 2.84 | **3.72** |
| N1 closed | dead | 0.83 | **0.24** |

*(raw Jev score, 0-indexed 0–4)*

### Falsification test F1 — PASSED

> *If KOI and CaiCa score within 1 level of each other, R1 has failed and the dimension
> should be cut, not patched.*

```
OLD:  KOI 1.12 vs CaiCa 1.17   gap -0.05   (leader scored BELOW the failing brand)
NEW:  KOI 2.60 vs CaiCa 1.22   gap +1.38   (leader correctly ahead)
```

### The gap is not noise — measured

Repeated invocations of the **same input with the same question**:

| Case | repeat values | spread |
|---|---|---:|
| KOI | 1.14, 1.20, 1.12 | 0.08 |
| CaiCa | 1.17, 1.24 | 0.07 |

**Run-to-run noise ≈ 0.08.**
- OLD leader-vs-failing gap: **−0.03** — *smaller than the noise floor.* The inversion
  was not a weak signal; it was **no signal at all.**
- NEW gap: **+1.38** — **17× the noise floor.** This is a real measurement.

### F2 — the ordering is monotonic

```
0.24  N1 closed      (dead)
1.22  CaiCa          (failing)
2.60  KOI            (leader)
3.72  C5 hawker      (Michelin star, single stall)
```

Four cases, four distinct levels, correctly ordered against independent ground truth. The old
dimension produced **1.12 / 1.17 / 2.84 / 0.83** — effectively three-way tied at the bottom.

### The distributions now have shape

| Case | OLD distribution | NEW distribution |
|---|---|---|
| KOI | `{0:0.19, 1:0.55, 2:0.21, 3:0.04, 4:0.01}` | `{2:0.38, 3:0.44, 4:0.11}` |
| C5 hawker | `{3:0.56, 4:0.27}` | `{4:0.77}` |
| N1 closed | `{0:0.34, 1:0.57}` | `{0:0.77}` |

The old KOI distribution put 74% of its mass on levels 0–1 and told us nothing. The new one
places mass on 2–3 — a definite judgment. **Decisive distributions on the closed business and
the hawker; a genuine "mostly this, somewhat higher" on the leader.** That is what a working
measurement looks like.

---

## What the new question says (and why it works)

> "…does this business over-index on buying situations **RELATIVE TO WHAT A BUSINESS OF ITS
> SIZE WOULD BE EXPECTED TO OWN**? This is a RELATIVE measure, never absolute. … A large,
> well-known player holding its situation is **NOT** a low score: holding a situation against
> expected erosion is an advantage. Equally, a tiny player owning one situation
> disproportionately to its size is a **STRONG** advantage."

The old anchors ran ***Taken → Mostly taken → Partly open → Open → Wide open*** — a pure
continuum of *degree*, which is exactly the "comfortable middle" the Likert literature warns
creates central-tendency bias. Level 3 ("Partly open") was a hedge, and the model hedged there
or below.

The new anchors are **qualitatively distinct states** — *over-index nowhere / present but owns
nothing / at expectation / over-indexes on ≥1 / the first retrieval* — so there is no smooth
middle to retreat into. **This is R6's fix and R1's fix working together, and the experiment
cannot separate their contributions.** Flagged honestly as a joint change.

**The key insight it encodes:** the correct question is not *"is the seat free?"* but
*"are you punching above your weight in the buyer's memory?"* — which is the same question for
an incumbent and a challenger. That is why it fixes an inversion the absolute form could not.

---

## Scope of the claim — what this does NOT prove

I can claim **the reframed question discriminates correctly on 4 cases against independent
ground truth, by a margin 17× the measured noise.** I **cannot** yet claim:

- that it works across the full 11-case ladder (only 4 run here);
- that the 5-level anchors are correctly calibrated (the C5 hawker at 3.72 — *"strongly
  over-indexes, first retrieval"* — is arguable: a hawker stall may over-index hugely **for its
  size** yet still not be *first retrieval* for a mass-market buyer. The relative framing may
  be **inflating small players** — that is the live risk of this change);
- **that it agrees with a human.** Still zero human labels on this dimension.

**The inflate-small-players risk is the one to watch.** N1 (dead) went *down* to 0.24 and CaiCa
stayed flat at 1.22, which is reassuring — but a deliberate test would be a tiny, genuinely
excellent niche operator, to check the relative framing does not reward smallness per se.

---

## Recommendation

1. **Adopt the reframe**, rename `position_availability` → `mental_advantage`.
2. **Re-run all 11 controls** on the new dimension before changing the composite weights.
3. **Carry the old dimension's score in the run artifact** for one release, so the change is
   auditable rather than silent.
4. **Test the inflation risk** with a small-excellent-operator case before trusting the
   upper anchors.
5. **Do NOT** treat this as fixing the calibration blocker. It fixes a broken dimension; it
   does not supply the missing human baseline, and the literature's prescription (a
   human-labelled calibration set) remains the only fix for that.
