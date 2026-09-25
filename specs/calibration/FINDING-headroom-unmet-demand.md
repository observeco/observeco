# FINDING — Market headroom reframed: Sean was right, and the fix over-corrected

**Date:** 2026-09-25
**Rubric:** 0.6.0 (market_headroom: crowding → unmet demand; bands extended to 100)
**Trigger:** Sean — *"when I think about the market headroom for ASML, should there even be a
credible albeit small competitor, it should really open up the space? The problem now is the
market is congested because ASML has the monopoly and can't expand beyond its current
capacity."*

---

## 1. Your reading is correct, and the evidence is stronger than the argument

**Verified before changing anything:**

| claim | evidence |
|---|---|
| ASML cannot expand beyond capacity | **~50–60 EUV systems/year**; a leading-edge fab needs **10–20** → the world can commission only **~3–4 new fabs/year** |
| the congestion is real | backlog **~€38.8bn ≈ 1.5 years** of revenue; most **2027 output already committed** |
| buyers are rationed | TSMC, Samsung and Intel "**compete for finite ASML allocation**"; lead times push commissioning **12–24 months** past announced schedules |
| the constraint is the binding limit | *"the world cannot build more leading-edge chips than ASML can ship machines to print"* |
| a second supplier would expand the market | the ceiling is **physical and institutional**, not commercial — more suppliers = more tools = more fabs |

**Your mechanism is exactly right.** Demand far exceeds supply, and the congestion is *caused
by* the monopoly being unable to expand. A credible second supplier would add capacity and
**open up the space**.

---

## 2. The defect — the dimension measured the wrong thing

The old question asked *"is there room for a new or small **entrant** to be chosen?"* — a
**crowding** question. Measured result:

| case | old headroom | truth |
|---|---:|---|
| **ASML** | **1.95 (≈3/5)** | supply-starved, 1.5-yr backlog |
| bubble tea | **2.84 (≈4/5)** | 62+ brands, demand fully served |

**A saturated market outscored a market starved of supply.**

**And it made `market_headroom` a near-duplicate of `competitive_room`** — one asked "is there
room for an entrant", the other "how much room does competition leave". **Neither measured unmet
demand at all.**

---

## 3. The reframe, measured before adopting

| case | OLD | NEW | label |
|---|---:|---:|---|
| **E1 ASML** | 1.95 | **3.33** | supply-constrained |
| bubbletea | 2.84 | **1.88** | crowded, demand served |
| C9 B2B | 2.34 | **1.95** | crowded, demand served |
| N1 closed | 2.32 | **1.67** | no demand |

**Separation (ASML − best other): −0.89 → +1.38.** The reframe does what it was built to do,
and the division of labour with `competitive_room` is now clean:

- **`market_headroom`** = is there unmet demand? *(is the opportunity real)*
- **`competitive_room`** = how hard is it to take? *(is the opportunity reachable)*

---

## 4. But it over-corrected — and this is the honest part

Across the 17-case ladder, `market_headroom` returned **3/5 in 16 cases and 4/5 in one**.

```
raw spread 1.69 - 3.31  (1.62 wide)
distinct display levels used: 2 of 5
```

**The old crowding question discriminated across 5 levels (1.95 → 3.31). The new one uses 2.**
Raw values cluster at **1.88–1.98** — nearly all sitting just under the level-4 boundary of 2.0.
That is the same boundary-vs-noise problem already identified in the gate, now recurring in a
dimension.

**Interpretation:** most of our cases are ordinary businesses in ordinary served markets, and
"demand is met, contested" is a **correct** answer for them. The discrimination I removed was
mostly **noise about crowding**, not signal about demand.

**So the reframe traded one distortion for another:**
- crowding framing → right for challengers, wrong for monopolists
- unmet-demand framing → right for monopolists, flat for everyone else

**Neither alone is sufficient.** The honest conclusion is that `market_headroom` should not be a
single scalar in the composite at all — it should be a **qualifier** (real demand / served /
unmet) with the *type* of headroom reported, not a 1–5 score averaged against everything else.

---

## 5. Composite effects — and a scale defect found

| case | 0.5.0 | 0.6.0 | Δ |
|---|---:|---:|---:|
| **E1 ASML** | 92 | **96 → 91** | +4 then −5 |
| C4 Sheng Siong | 66 | 69 | +3 |
| C3 Pet Lovers | 65 | 67 | +2 |
| koi | 77 | 74 | −3 |
| C6 Eu Yan Sang | 73 | 70 | −3 |
| Coupang | 78 | 75 | −3 |
| ObserveCo | 70 | 65 | −5 |
| Bonefirm | 56 | 51 | −5 |
| N2 stripped | 50 | 46 | −4 |

**Most businesses now score lower** (~3–5 points) — the honest consequence of asking whether
demand is actually unmet rather than whether the market looks open.

**Scale defect found and fixed:** ASML's **96** landed as `out of range` — the top band stopped
at **95**, because the bands were written when every dimension was 5-level and the arithmetic
ceiling was ~95. With defensibility at 6 levels the ceiling is **100**. Top band extended to
100; `band_of()` now **raises** on an unmapped composite instead of silently returning
"out of range".

**Also fixed:** `run_jev.py` was failing silently on transient API errors, so cases vanished
from batch loops with no error (this bit us on koi twice). It now exits **2** with a message.

---

## 6. Recommendation — for Sean's decision

**Do not ship the unmet-demand framing as a drop-in scalar replacement.** It is better than the
crowding framing for the cases that matter most (dominant operators), but it is flatter overall
and it is now sitting on a boundary with less than 0.1 of headroom against 0.08 noise.

Three options:

1. **Qualifier, not score** *(my recommendation)* — `market_headroom` classifies the market as
   *no demand / served / unmet*, and the report states the type. It leaves the composite, which
   removes a weak 15% dimension and makes the remaining four do real work. It also cannot be
   gamed, and it reads plainly to a non-expert.
2. **Keep unmet-demand, widen the anchors** — re-anchor the levels so ordinary served markets
   spread across 2–3 rather than all landing on the same value. More work, keeps the composite
   intact.
3. **Revert to crowding** — restores discrimination but re-establishes the ASML inversion, which
   your argument convincingly shows is wrong.

**My view: option 1.** The reframe proved the concept is right and that the scoring shape is
wrong. A dimension that is flat for 16 of 17 cases is not earning its 15% weight in a composite.
