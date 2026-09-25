# FINDING — Defensibility split to 6 levels (rubric 0.5.0)

**Date:** 2026-09-25
**Sean's decision:** *"a well-protected single formulation should not score the same as
something copyable in months."*

---

## 1. What changed

**The old level 3 conflated two different situations:**

| | situation | old score |
|---|---|---|
| **(a)** | genuine development required, **nothing obstructs it** — the approach is visible and a committed competitor gets there | 3 |
| **(b)** | the same development **plus a barrier** — trade secret not reverse-engineerable, a blocking patent, an undisclosed ratio or process, an unobtainable supply arrangement | 3 |

**Both scored 3.** The `E4` test proved it: adding explicit trade-secret, undisclosed-process and
non-reverse-engineerable disclosure to Bonefirm left the score at **3** and only raised
confidence 0.71 → 0.97 — because old level 3's text *already named* "a formulation, a process, or
a technical system". **IP was inside level 3 by construction.**

**Split into two levels:**

```
1  No moat        -- relabel a purchasable input this quarter
2  Shallow        -- weeks, no development of their own
3  Replicable     -- development required, but NOTHING obstructs beyond the effort
4  Protected      -- development required AND a barrier obstructs copying  <-- NEW
5  Durable        -- a year or more, or assets they do not have
6  Compounding    -- reinforcing advantages, unreplicable even given time
```

Anchors stay qualitative and distinct, per the earlier Likert finding — level 4 is a
**different kind** of situation (obstructed), not merely "more months".

---

## 2. Verified — the split does exactly what Sean asked

| case | defensibility | distribution | what it means |
|---|---:|---|---|
| **E4 Bonefirm + explicit IP** | **4/6 Protected** | `{2: 0.20, 3: 0.77}` | 77% mass on "obstructed" |
| **Bonefirm (as submitted)** | **3/6 Replicable** | `{1: 0.09, 2: 0.86}` | 86% mass on "nothing obstructs it" |
| **E1 ASML** | **6/6 Compounding** | — | the new top is reachable |
| E2 Coupang | 5/6 Durable | — | flywheel at Durable |
| C9 B2B (copyable in months) | 2/6 Shallow | — | genuinely thin |

**The two businesses Sean wanted separated are now separated.** Bonefirm-as-submitted sits at 3;
Bonefirm-with-its-IP-depth-disclosed sits at 4. **Same business, one variable changed, one level
of movement** — the first time this dimension has responded to an IP manipulation.

---

## 3. Two implementation defects found and fixed

**Defect 1 — normalisation.** A 6-level defensibility at maximum (6) would have contributed
`6/5 × 25% = 30%`, inflating every composite by ~5 points and making defensibility worth more
than declared. **Fixed:** each dimension is now normalised by **its own level count**
(`level_counts` in the rubric), so a dimension at maximum contributes its full declared weight
regardless of how many levels it has. Verified by manual recomputation on six cases — recorded
composites match hand-computed values exactly.

**Defect 2 — stale artifacts.** `verify_6level.py` caught composites recorded under 0.4.x
normalisation disagreeing with hand computation (ASML recorded 92, manual 87 under the old
denominator; koi recorded 76, manual 73). **Every composite from a pre-0.5.0 run was stale.**
The whole 17-case ladder was re-run under 0.5.0.

**Defect 3 — display label.** Defensibility renders as `/6` now; the other four stay `/5`. A
generic "/5" label would have been silently wrong.

---

## 4. Important: the composite HIDES this change in one place

**`E4` and `Bonefirm` both composite at 56.**

```
E4 Bonefirm+IP :  HR 4  CR 2  MA 2  DEF 4/6  DR 3   -> 56
Bonefirm       :  HR 4  CR 2  MA 3  DEF 3/6  DR 3   -> 56
```

The defensibility gain (+1 level, +4.2 points) was **exactly offset** by a −1 on mental advantage
(−5 points) in the same run. **The composite is unchanged while a real, Sean-directed distinction
moved a full level.**

**This is a product-level warning:** the free report's headline number can be blind to the exact
distinction the report exists to make. The dimension row shows it; the composite erases it. Worth
deciding whether the report leads with the composite or with the dimension that carries the
finding.

---

## 5. Full ladder under 0.5.0

```
92 Strong    E1 ASML              (6/6 Compounding)
78 Strong    E2 Coupang           (5/6)
77 Strong    09 KOI               (5/6)
75 Strong    C5 Michelin hawker   (4/6)
73 Viable    C6 Eu Yan Sang       (5/6)
71 Viable    C2 ActiveSG
70 Viable    ObserveCo            (4/6)
68 Viable    D2 Pet Lovers+cue    (5/6)
66 Viable    C4 Sheng Siong       (4/6)
65 Viable    C3 Pet Lovers        (5/6)
56 Contested bonefirm             (3/6)
56 Contested E4 Bonefirm+IP       (4/6)
46 Contested D1 Watsons           (3/6)
44 Contested N1/... (see runs)
 GATE        N1 closed business
```

**Leader-vs-troubled separation is preserved.** ASML at 92 is the ceiling; the dead business is
still gated.

---

## 6. What this does NOT fix

- **The level-5/6 magnet question is now level 5** — four established incumbents (KOI, C3, C6,
  D2) all land on 5/6 Durable at 0.80–0.88 coverage. The saturation moved up one level rather
  than dissolving.
- **ASML still breaks two dimensions** — `market_headroom` returned 3/5 and `competitive_room`
  was withheld at 0.00 coverage. Both remain challenger-framed.
- **Zero human labels.** Unchanged.
- **Bands were not re-calibrated.** Kept for comparability; the 6-level change moves the low
  boundary by <1 point, so this is safe but should be revisited once the ladder settles.
