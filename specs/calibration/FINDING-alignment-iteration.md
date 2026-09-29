# FINDING — the alignment iteration (v1.2.0 → v1.4.1)

## Trajectory, measured with one consistent metric

| version | change | exact | disputes | offset | note |
|---|---|---|---|---|---|
| v1.2.0 | baseline (DEF wording only) | 65.6% | 8.5% | +0.35 | |
| v1.3.2 | DR corroboration fix (trading floor) | 64.5% | 7.2% | +0.29 | |
| v1.4.0 | RS per-situation, not one share fight | 58.1% | 7.5% | +0.10 | over-corrected |
| v1.4.1 | RS + recognition | 63.0% | **6.0%** | **+0.24** | best exact since v1.2.0 |
| **v1.5.0** | MA addressable segment | 59.1% | **5.2%** | **+0.24** | best disputes |

Targets: exact ≥75%, disputes ≤5%, offset ±0.25. **Disputes and offset both improved;
exact agreement did not.** Disputes 8.5% → 5.2% and offset +0.35 → +0.24 across the run.

**v1.5.0 exposed a NEW regression:** Gong Cha (shut all 29 SG outlets) scores MA 1 against
Sean's 4. My "ceased → not retrieved" rule is wrong for mental_advantage: closure destroys
REACH (a DR fact) but not MEMORY (an MA fact). **The same physical fact has opposite
implications for different dimensions, so a corroboration rule must be dimension-specific,
not global.** I had been building one shared "physical evidence" doctrine — this shows it is
too blunt.

**And a construct question a re-word cannot fix:** Sean scores 5 for Courts, Donki, Harvey
Norman and Cold Storage, whose prices converge within 3–8%. My level 5 says "rivals are not
close". Either his 5 means *dominant presence* rather than *uncontested* (my level is
mis-worded), or it is calibration, or he grades absolute standing. **MA has been re-worded
twice and moved three of four cases by exactly one point — a third re-wording is the wrong
move.** This needs an answer from Sean, not another edit.

## THE CENTRAL LESSON: one defect class, found in three dimensions

Every fix that worked was the SAME fix. The instrument reads the **submission**, not the
**business**.

| dimension | what it was reading | what it should read |
|---|---|---|
| `demand_reach` | whether the FORM named a channel | whether the business demonstrably reaches buyers (trading = floor 3) |
| `position_strength` | one share fight vs the whole named set + the form's own `undercut_on` confession | the position held **per situation**, corroborated |
| `defensibility` (next) | the differentiator the form CLAIMS | the accumulated barriers the business **actually holds** |

**Two mechanical causes, both in the same class:**
1. **The form's `undercut_on` field is the business self-reporting its weakness, and the
   scorer was treating that confession as the verdict.** Every large miss has a candid
   `undercut_on` ("most baskets still go to FairPrice"). Honesty was being punished.
2. **Absence of detail in the form was read as evidence of absence in the world.** A
   business with 7 outlets scored as having no route to buyers because the form was terse.

**The rule to carry forward:** absence of detail in a submission is an INPUT-QUALITY problem,
never evidence about the business. Corroborate against physical facts, then score.

## What each fix was worth, per dimension

**`position_strength` (25% weight) — the biggest win.**
- Sephora 2 → 4 (Sean 5): 7% share, but it OWNS the premium destination — the international
  brands list there first. My ladder anchored on "the median occupant of the set", so a
  specialist dominating a distinct situation was scored as losing a head-on fight it never
  entered. This is Sean's own principle: **positioning is about product categories, not
  industries.**
- Don Don Donki 2 → 4 (Sean 4), ROA 2 → 3, Polar Puffs 2 → 3.
- RS disputes **4.2% → 0.8%**, offset **+0.31 → +0.07**, correlation r 0.83 → 0.84.
- **But v1.4.0 over-corrected**: offset flipped to −0.43, exact fell to 44.5%, because small
  home studios (Lash Fairy, Mono Studio, Tee Nail Bar) were lifted to 4 where Sean scores 2.
  **A niche being distinct does not make its occupants strong.** Fixed in v1.4.1 with a
  RECOGNITION requirement — and note the fix is not a return to share-anchoring: Sephora
  stays at 4 on 7% share, because its position is *recognised*. **Smallness is not the test;
  recognition is.**

**`demand_reach` — with a self-inflicted regression caught by testing.**
- Best Denki 2→3, 24/7 Fitness 2→3, Zoff 2→4, BreadTalk 3→4 (Sean 4–5).
- Home massage service correctly **stayed at 1** (Sean agreed with that number).
- **I broke the closed bubble tea outlet: 2 → 3 (v1.3.0), then 1 (v1.3.1), then 2 (v1.3.2).**
  v1.3.0 applied the trading floor to a dead business. v1.3.1 lumped "ceased" with "no
  buyer". The correct placement is 2: a ceased business has an IDENTIFIABLE buyer group, it
  simply no longer reaches them. Only v1.3.2 matches Sean's 2.

## Two process failures of mine, both worth recording

1. **v1.1.0 changed four dimensions at once** — un-attributable, and it hid a CR regression
   inside a DEF improvement. Since then: one dimension per version, with the other five
   asserted **byte-identical** as a control in every build script.
2. **`_meta.version` vs top-level `version`.** My build scripts set only the top-level field,
   so **rubric-v1.3.0 stamped itself "1.2.0"** — two different rubrics carrying the same
   number, which **defeats the harness's own mixed-version guard**. `runs-v12` and `runs-v13`
   both claimed 1.2.0 while holding different content. Fixed with a fail-loud check in
   `run_jev.py`, verified to fire. **The run content was always valid; the label was not.**

## Still open

- **`mental_advantage` is now the largest problem**: offset +0.46, disputes 11.7%, and the
  worst single case (Harvey Norman me 2 / him 5, Best Denki 2/4, Courts 3/5, Don Don Donki
  3/5). All large retailers — the same "score the claim, not the business" signature.
- **`defensibility`**: Best Denki 1/4 and Gain City 1/4. DEF 1 = "nothing obstructs a
  challenger", but both hold store networks — level 4's "scale built over years". I am
  scoring their *claimed* differentiator (Japanese service standards, copyable) instead of
  their *actual* barrier. Next fix.
- The five `home-not-permitted` cases sit at MA 1 / DR 1 while Sean scores 3. They are
  synthetic representatives of a statutory rule, not real businesses — they may belong in
  refusal rather than at a low score.
- Exact agreement (63%) is below target while disputes (6.0%) are close. My scores spread as
  they move; I judge dispute count the better measure of a usable instrument.
