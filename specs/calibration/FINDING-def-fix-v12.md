# FINDING — v1.2.0: the DEF wording fix measured, and a methodology error caught

## The methodology error (mine)

I built v1.1.0 changing **four dimensions at once** (DEF, CR, DR, MH) in response to Q1–Q6.
That is un-attributable. It produced:

```
DEF  >=2-apart 14% -> 7%   IMPROVED  (the targeted fix)
CR   exact     77% -> 65%  REGRESSED
DR   exact     67% -> 54%  REGRESSED (shift 0.39 -> 0.63)
MH   identical (dropped in 105 of 120 cases, so immaterial)
```

**A change that improves one dimension and harms two is not a fix, and I could not tell
which change did what.** The cause: I treated Sean's six answers as six defects to fix. Only
one was a defect in my wording.

### Reversal reasoning — which answers were actually instructions to change wording?

| Q | His answer | Verdict |
|---|---|---|
| Q1 DEF | "hard to attack because it took decades and huge capital" | **DEFECT** — my wording excluded accumulated scale, a standard barrier |
| Q2 CR | "fragmented BUT walled by dominant players… correct me if I have the scoring wrong" | **Not a defect.** He asked me to correct him; my definition stood (Book 1 supports it). Should not have touched it |
| Q3 DR | "I thought demand reach is these companies have understood and mapped out who their customers are" | **Not a defect.** He was explaining what his score meant. v1.0.0 already graded definability |
| Q4 RS | "positioning of the company relative to competitors — the definition we aligned" | No change requested |
| Q5 MA | "how much they have captured the mental space of the segment" | No change requested |
| Q6 MH | "no unmet demand for car inspections based on the COE supply restrictions" | **HE WAS RIGHT** — keep, but untested |

**Rule recorded:** a user's explanation of what THEIR score meant is not a request to change
the rubric. Separate "you misunderstood my definition" from "your definition is wrong", and
change one dimension at a time so the result is attributable.

---

## v1.2.0 — the clean single-variable test

v1.0.0 with **only** the DEF wording changed (plus the MH instruction note).
`build_rubric_v12.py` asserts every other dimension still matches v1.0.0.

**Result, against Sean's 120 grades:**

```
        v1.0.0                      v1.2.0
dim    shift   exact   >=2     shift   exact   >=2
RS      0.31    72%     4%      0.28    72%     4%     unchanged (control)
MA      0.45    64%    12%      0.45    63%    12%     unchanged (control)
DEF     0.37    73%    14%      0.23    66%     7%     <-- TARGETED
CR      0.21    77%     5%      0.21    77%     5%     unchanged (control)
MH     -0.20    80%     0%     -0.20    80%     0%     unchanged (control)
DR      0.39    67%    12%      0.39    65%    12%     unchanged (control)
```

**Five dimensions are controls and did not move.** Only DEF changed:

- **≥2-apart disagreements halved: 14% → 7%.** This is the metric that matters — at band
  noise 3.0, a 1-point difference is not a real dispute.
- **Shift fell 0.37 → 0.23** (38% of the gap closed).
- **Directionality: 55 → 45 cases where he is ≥2 above me**, and 2 now go the other way.
  Ten fewer real disputes, all concentrated in DEF.
- Exact agreement dipped 73% → 66%. Honest cost: my scores moved up toward his AND spread,
  so fewer land on the same integer. The dispute count is the better measure.

**The Q1 cases specifically — 6 of 7 moved toward him:**

```
                       hisDEF   v1.0.0   v1.2.0
McDonald's                 5        2        4     +2
NTUC FairPrice             5        3        5     exact
KFC                        4        1        2     +1
Sephora                    4        2        3     +1
Unity Pharmacy             4        2        3     +1
Harvey Norman              3        1        2     +1
Best Denki                 4        2        1     -1  (moved away)
```

**The defect was real and the fix works.** My old wording — *"effort already spent does not
make something defensible"* — was written to stop "we worked hard" scoring. But it also read
as excluding *"we built 150 outlets and a national supply chain over 40 years"*, which is a
standard barrier to entry. The revision distinguishes **flow effort** (earns nothing) from
**stock barriers** (count), and states the test as **the challenger's cost**, never the
incumbent's effort.

---

## Q2 — Book 1 supports MY fast-food reading, so I did not change CR

Sean asked to be corrected, and cited Book 1. Checked the source
(`whitepapers/book1-map-manuscript.md:296`):

> *"when the market is capped and the players are many, the default move is to undercut, to
> shave a dollar off the price to steal the customer. That is why price competition is so
> common, and so dangerous, in the Singapore domestic layer. It is the natural physics of a
> small, crowded room, not a phase or a passing fad."*

**So fast food is `CR 2`.** A market can be fragmented AND have no room, because the many
players undercut each other. His level-4 word "fragmented" was what invited a
count-the-players reading, and that is a real wording risk — but v1.1.0's rewrite of it made
agreement *worse*, so the definition stands and the wording question is parked as a
known-weakness rather than fixed blind.

## Q6 — he was right, and the fix is untested

VICOM: I scored market_headroom 3; he marked n/a because **the COE system caps the number of
vehicles, which caps inspection demand.** Regulated demand caps are now stated in the MH
instructions. **But MH is dropped in 105 of 120 cases, so this can affect at most 5 — it is
not measurable on this corpus.** Stated as untested, not as fixed.

---

## THE REAL REMAINING PROBLEM — it is not wording

The level shift **persists on every dimension I did not touch**:

```
RS  +0.28    MA  +0.45    CR  +0.21    DR  +0.39
```

and **45 cases still differ by ≥2.** Fixing one dimension's wording removed 10 disputes out
of 55. **The remaining gap is not a wording defect.** Two candidate explanations, and they
need Sean's judgement because the corpus cannot distinguish them:

1. **He grades absolute, I grade relative.** On every dimension my scale asks "compared with
   what?" — a benchmark, a hypothetical copier, the market. He may be reading each question
   as "how good is this business?" That would produce exactly this pattern: a uniform
   positive shift with equal spread.
2. **My level anchors are systematically too low.** If so the fix is to re-anchor the middle
   of each scale, and his scores are the corrected values.

**Test that would separate them:** ask him to score 3 businesses he considers genuinely
mid-scale (3) and 3 he considers excellent (5), and see whether his "3" lands where my "3"
lands. If his 3 is my 4, it is a level anchor problem. If his 5 is my 5 and his 3 is my 3
but the distribution differs, it is a reading-frame problem.

## Other open items

- **`competitive_room` is scored 4 by him for all six fast-food cases and 2 by me for all
  six** — a disagreement about the MARKET, not any business. With Book 1 supporting 2, this
  is one to watch rather than act on.
- **Five `home-not-permitted` cases are synthetic representatives**, not real businesses
  (Q5). They cannot be scored on mental space captured. They should be **refused**, not
  rescored.
- **No per-dimension REASONING is stored in run files.** Sephora (his RS 5, my 2) could not
  be resolved because I could not reconstruct why I scored 2. This is a build gap, not a
  judgement gap.

## Sources
`build_rubric_v11.py` (the four-variable error), `build_rubric_v12.py` (the clean test),
`run_v11_set.py` / `run_v12_set.py`, `test_v11_improvement.py`,
`test_def_rs_overlap.py`, `whitepapers/book1-map-manuscript.md:296`.
