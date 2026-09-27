# RETRACTION — "the composite is compressed" was an artefact of MY OWN bug

## What I claimed (commit `0c1e6ea`, and in my report to Sean)

> "My composite scale is COMPRESSED... strictly monotone: +13.0 for Fragile businesses down
> to −4.5 for Very strong ones. I am too generous at the bottom and too harsh at the top."

## Why it was wrong

**I replicated the composite with the wrong formula.** I used

```python
sum((level - 1) / (count - 1) * weight)     # my replication -- 0-100, floor 0
```

The harness actually uses

```python
sum(level / count * weights_used)            # run_jev.py:365 -- floor ~20
```

**The two disagree on 119 of 120 cases.** With the lowest level contributing `1/5` instead
of `0`, the harness's composite floor is about 20, not 0 — and my "compression" was the
signature of comparing a floor-0 scale against a floor-20 one.

**The check that caught it:** on the target segment my dimension scores differed from Sean's
by a total of only **+1.3 composite points**, while my formula reported a **+10.7** composite
gap. Two numbers that cannot both be true — so I verified the replication against the
harness's own stored output instead of trusting it. That is the check I should have run
BEFORE reporting the finding, not after.

## The corrected picture (replication verified 116/116)

**Band agreement — the D1 close condition:**
```
ALL                    n=114   same 69.3%   within-1 100.0%   TWO+ OFF 0.0% (0)
TARGET (weak SMEs)     n= 60   same 85.0%   within-1 100.0%   TWO+ OFF 0.0% (0)
```
**D1's bar is ≥90% within one band and ≤5% two-or-more off. We pass on both counts with
margin — 100% within one band, and zero cases two or more off.**

**The compression does not exist:**
```
Fragile-ish (<35)   n= 3   mean gap  +9.7
Contested  (35-50)  n=31   mean gap  -1.1
Viable     (50-65)  n=41   mean gap  -2.2
Strong     (65-80)  n=25   mean gap  -1.9
Very strong (80+)   n=14   mean gap  -7.7
overall mean -2.2   (I had reported +13.0 at the Fragile end)
```
Not monotone, and the sign is mostly **negative** — I am mildly HARSH, not generous. The one
real effect is at the very top (−7.7 for businesses Sean rates 80+).

**And the promotion story reverses:** I am more generous in **12** cases and harsher in
**23** (I had reported 46 vs 14). Fragile businesses moved out of the Fragile band:
**1 of 7** (I had reported 26 of 34).

## What this costs

**Every composite-level number in commit `0c1e6ea` is void.** It should not be cited. The
dimension-level results are unaffected — `measure_alignment.py` reads stored dimension scores
and never computed a composite — so the v1.2.0 → v1.8.0 trajectory, the noise floor, and the
per-dimension offsets all stand.

## The process failure, stated plainly

I built a composite function, never checked it against the harness's own output, and reported
a structural finding on top of it — **and I reported it as the most important discovery of
the session.** One verification call against a stored run file would have caught it
immediately, and that call was cheap and available the whole time.

**Rule for this project: any re-implementation of a harness calculation must be verified
against the harness's own stored output before any finding is built on it.** I added the
`_meta.version` guard earlier for exactly this class of error and then made the same mistake
one level up.

## Where the project actually stands

**D1 (band close condition): PASSES.** 100% within one band, 0 two-or-more off, 85% exact on
the target segment.
**D2 (band + narrative):** no number is shown, so a −2.2 mean composite offset is invisible
to a client; only band placement matters, and that is 100% within one band.
**D3 (weak-positioning SMEs):** the target segment is the instrument's BEST region — 85%
exact band agreement, and the weakest region is the top end (−7.7), which is off-target.
**D4 (refuse home-not-permitted):** still to implement.
