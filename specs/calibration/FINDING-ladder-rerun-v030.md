# FINDING — Full ladder re-run on the reframed dimension (rubric 0.3.0)

**Date:** 2026-09-25
**Status:** EXECUTED. 12 cases, one model (`jev-1.13.0`), `position_availability` →
`mental_advantage`, confidence floor active.

---

## 1. The headline

**KOI — the market leader — now scores 76 "Strong". It was 66 "Viable".**

That is the first "Strong" band in the project, and it went to the case that deserves it. It
also completes a three-case proof that the old dimension was broken: KOI at **2/5** (old) →
**4/5** (new), on the same business with the same evidence.

| | old | new | Δ |
|---|---:|---:|---:|
| **KOI** | 66 Viable | **76 Strong** | **+10** |
| C2 ActiveSG | 59 Contested | 72 Viable | **+13** |
| C6 Eu Yan Sang | 67 Viable | 72 Viable | +5 |
| C5 hawker | 68 Viable | 73 Viable | +5 |
| C9 B2B | 53 Contested | 58 Contested | +5 |
| ObserveCo | 63 Viable | 68 Viable | +5 |
| C4 Sheng Siong | 62 Viable | 64 Viable | +2 |
| C3 Pet Lovers | 67 Viable | 67 Viable | 0 |
| Bonefirm | 59 Contested | 59 Contested | 0 |
| CaiCa | 53 Contested | 53 Contested | 0 |
| N2 KOI stripped | 53 Contested | 52 Contested | −1 |
| N1 closed | GATE | GATE | 0 |

### Separation improved: 6 → 9 points

```
OLD: leaders [59, 66, 67, 67]  troubled [53, 53, 53]  -> gap 6
NEW: leaders [67, 72, 72, 76]  troubled [52, 53, 58]  -> gap 9
```

**The change did what it was supposed to do, and the effect is concentrated where the defect
was** — KOI +10 and ActiveSG +13 are the two incumbent cases the old dimension penalised.

---

## 2. Monotonicity — mostly holds, and one real failure

```
DEAD      MA=1   N1 closed business
STRIPPED  MA=2   N2 KOI minus differentiator
FAILING   MA=2   CaiCa
CROWDED   MA=3   C9 B2B managed IT
LEADER    MA=3   C3 Pet Lovers Centre      <-- FAILURE
STRONG*   MA=4   C4 Sheng Siong
UNPROVEN  MA=4   ObserveCo
LEADER    MA=4   KOI
LEADER    MA=4   C6 Eu Yan Sang
STRONG*   MA=5   C5 Michelin hawker
LEADER*   MA=5   C2 ActiveSG
```

**The bottom of the ladder is clean.** Dead → stripped → failing → crowded → leader, in order.

**But the top is not.** **C3 Pet Lovers Centre — the largest pet retail chain in SEA, 69
Singapore stores, trading since 1973 — scores 3/5, below a single hawker stall (5/5) and below
a subsidised public gym (5/5).**

That is a genuine ordering failure, not a rounding artefact, and it is the open defect this
run exposed. Two candidate explanations, neither yet tested:
- **Pet retail is a low-salience category** — nobody is *retrieved* for "buying pet food" the
  way they are for "cheap gym" or "great noodles". If so, **the dimension is category-sensitive
  in a way we haven't controlled for**, and cross-category comparison is invalid.
- **The relative framing under-reads large-but-unremarkable incumbents** — being big and
  expected makes it hard to over-index. This would mean the measure is *relative to size* in a
  way that structurally caps leaders.

**These have opposite implications and I cannot distinguish them from this run.**

---

## 3. Inflation risk — did NOT materialise

The live risk flagged before this run: *does the relative framing reward smallness per se?*

```
micro mean MA 3.25   (N1=1, bonefirm=3, observeco=4, C5=5)
large mean MA 3.67   (N2=2, C3=3, KOI=4, C6=4, C4=4, C2=5)
```

**Large players score HIGHER on average than micro players.** The framing does not
systematically reward smallness, and the `n=3` suspicion from the earlier 4-case experiment
does not survive the full ladder.

**One upper-anchor concern remains:** C5 (a single hawker stall) at **5/5** and its interval
came back **5–5** at 0.80 coverage — a *decisive* maximum for a one-stall operation. Whether a
Michelin-starred stall is truly *"the first retrieval for one or more valuable,
frequently-occurring buying situations"* at the same level as a national programme is arguable.
The relative framing says "huge over-index for its size" — which is defensible, but it means
**the top anchor conflates "punches above its weight" with "is the market's first retrieval."**

---

## 4. Confidence fixes — the floor fired

**3 of 12 runs reported a dimension as `unscored` rather than rendering a number:**

| Case | dimension withheld | coverage |
|---|---|---|
| C2 ActiveSG | `defensibility` | below 0.20 |
| N2 KOI stripped | `demand_reach` | below 0.20 |
| N1 closed business | `demand_reach` | below 0.20 |

**This is the first time the harness has withheld a judgment instead of printing one.** Under
the old code each of these would have been rendered as a score. C2's `defensibility` being
withheld is notable: it is exactly the *"advantage granted by policy rather than built"*
question flagged in the previous control round — the model genuinely cannot read it, and now
says so instead of guessing.

Also now recorded per dimension:
- **`evidence_coverage`** — the honest name for what was called `confidence`
- **`judgment_intervals`** — e.g. KOI `expected 3.59`, 80% band **3–4**; N1 closed `1–2`
- **`weights_used_renormalised`** — so any composite is auditable
- **`_caveat`** on every artifact: *coverage is not the probability the judgment is right*

---

## 5. What this does and does not establish

**Established:**
- the reframe **fixes the inversion** (KOI 2→4, and the ladder's leader/failing gap widened
  6→9 against independent ground truth);
- the inversion was **zero signal, not weak signal** (−0.05 gap vs 0.08 noise floor);
- the **coverage floor works** and withheld 3 judgments in 12 runs;
- the inflation risk **did not materialise** in aggregate (micro 3.25 < large 3.67).

**Not established — and now the priority:**
- **C3/C5 ordering failure.** Pet Lovers Centre below a hawker stall is unexplained. Either
  the dimension is category-sensitive or it caps incumbents. **Must be resolved before any
  cross-category claim, and before shipping.**
- **Zero human labels.** Still the #1 blocker, unchanged, and the paper's prescription
  (a human-labelled calibration set) is the same requirement.
- **One run per case.** No repeat-measurement on 11 of 12 — noise was measured on only 2 cases.
- **Weights unchanged** (15/20/25/25/15). They were declared, not calibrated, and the
  composite moved largely because the reframed dimension now produces different raw scores.

---

## 6. Recommendation, in order

1. **Resolve the C3/C5 ordering failure before anything else.** Cheapest test: run the
   dimension on 2–3 more **low-salience incumbents** (a hardware chain, a pharmacy chain). If
   they all score 3, the dimension is salience-biased and needs a category term.
2. **Fix the top anchor.** Split "punches above its weight" from "is the market's first
   retrieval" — they are being merged and it is what lets a hawker stall tie a national
   programme.
3. **Do not re-weight yet.** Weights are uncalibrated and changing them now would confound
   this result.
4. **Sean labels 3 cases blind.** Unchanged, and now more valuable: the dimension is finally
   producing spread, so a human comparison would be informative rather than degenerate.
