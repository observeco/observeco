# FINDING — v1.6.0, the noise floor, and the real shape of the trade

## The measurement that changes the interpretation of everything above

**I had been measuring each version against itself and calling any movement an improvement.
So I ran the SAME rubric (v1.6.0) twice and measured the noise floor.**

```
cells compared: 720
cells that changed between two runs of the SAME rubric: 19 (2.6%)
direction of change: {-1: 9, +1: 10}          <- symmetric, no drift

run A: exact 55.9%  disputes 4.7%  offset +0.09  (23 disputes)
run B: exact 56.3%  disputes 5.2%  offset +0.09  (25 disputes)

>>> NOISE FLOOR: exact +/-0.4 pts, disputes +/-0.4 pts, 2 dispute cases
```

**The noise floor is small.** So the between-version movement is not sampling:

```
version       exact   disputes   offset  disputes(count)
v1.2.0        66.7%       8.6%    +0.23       41
v1.3.2        64.5%       7.2%    +0.24       35
v1.4.1        63.0%       6.0%    +0.16       29
v1.5.0        59.1%       5.2%    +0.15       25
v1.6.0        55.9%       4.7%    +0.09       23

v1.2.0 -> v1.6.0:  exact -10.9 pts (floor +/-0.4)  ABOVE
                   disputes -3.8 pts (floor +/-0.4)  ABOVE
                   dispute cases -18  (floor +/-2)    ABOVE
```

**Both movements are real.** Determinism was already established (within-case sd 1.06,
`band_noise 3.0`); this is the run-to-run view of it, and it is tight.

## The mechanism — the trade is not a loss, it is a relabel

```
version   gap0  gap1  gap>=2   %exact
v1.2.0     319   111     41     66.7%
v1.4.1     305   143     29     63.0%
v1.6.0     271   184     23     55.9%
```

**Exact disagreement is being converted into 1-apart disagreement.** Cells move from `gap0`
to `gap1` (111 → 184) while `gap>=2` shrinks (41 → 23).

Read as the business question rather than the statistics:

- **`gap>=2` = the instrument gives the wrong answer.** It puts a business in the wrong band
  and a user would be misled. **This halved (41 → 23).**
- **`gap1` = the instrument is directionally right at a slightly different granularity.** For
  a 5-point scale, adjacent is close; a report saying "roughly this level" is usable.

So the honest characterisation: **the instrument became much better at not being wildly
wrong, and did not become better at being exactly right.** Which of those matters depends on
how the output is used — and that is a product decision, not a measurement one.

**Caveat I will not hide:** `gap0` ALSO fell (319 → 271). So some exact agreement was lost
without even landing adjacent — my scores spread in both directions on some cases, and the
net offset moving from +0.23 to +0.09 masks that. The trade is favourable on the wrongness
measure and unfavourable on the exactness measure; it is not uniformly good.

## What each fix contributed, verified against the noise floor

All above +/-2 dispute cases, so all real:

- **RS (25%)**: disputes 4.2% → 0.8%. The largest single contribution. Sephora 2→4 on 7%
  share — it owns the premium destination. Root cause was anchoring on "the median occupant
  of the set", so a specialist dominating a distinct situation was scored as losing a
  head-on fight it never entered.
- **DR**: disputes 12% → 4.2% in the user's direction. Trading sets a floor of 3.
- **MA**: 29 → 25 disputes, but **Gong Cha still the worst case (me 1, Sean 4)** and the
  level-5 construct question unresolved.
- **DEF**: 29 → 23 contributed; Best Denki and Gain City 1 → 2 (Sean 4) — **only partially
  fixed**.

## The recurring root cause, now demonstrated in four dimensions

**The instrument was reading the SUBMISSION instead of the BUSINESS.**

| dimension | what it read | what it should read |
|---|---|---|
| `demand_reach` | whether the FORM named a channel | whether the business demonstrably reaches buyers |
| `position_strength` | one share fight vs the whole named set + the form's own `undercut_on` confession | the position held per situation, corroborated |
| `mental_advantage` | whether the MODEL could articulate a retrieval occasion | whether the SEGMENT retrieves it |
| `defensibility` | the differentiator the form CLAIMS | the accumulated barriers the business HOLDS |

Two mechanical causes recur: **the form's `undercut_on` is the business self-reporting its
weakness and it was being scored as the verdict** (candour punished), and **absence of detail
in a form was read as absence in the world.**

## The limit of this approach, stated plainly

**Every fix has been a re-word, and every re-word has moved cases by exactly one point.**
Four dimensions have now been through it. The remaining disputes are not wording problems:

1. **MA level 5 (construct).** Sean scores 5 for Courts, Donki, Harvey Norman and Cold
   Storage — businesses whose prices converge within 3–8%. My level 5 says "rivals are not
   close". Either his 5 means *dominant presence* rather than *uncontested*, or the frame
   differs. **No re-wording fixes this; it needs an answer.**
2. **A dimension-specific corroboration doctrine.** Gong Cha (closed) scores MA 1 vs Sean's
   4, because closure destroys REACH (a DR fact, where he agrees it is a 2) but NOT MEMORY
   (an MA fact). **The same physical fact has opposite implications per dimension**, so my
   one shared "physical evidence" rule is too blunt.
3. **The five home-not-permitted cases** sit at MA/DR 1 vs his 3 — synthetic representatives
   of a statutory rule, not real businesses; they may belong in refusal.
