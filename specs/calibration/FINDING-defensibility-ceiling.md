# FINDING — Defensibility: the ceiling exists, the middle is a magnet, and IP sits at level 3

**Date:** 2026-09-25
**Rubric:** 0.4.1
**Trigger:** Sean — *"I think any company that has significant IP or flywheel will have high
defensibility. Microsoft, Amazon, Tesla etc. These companies are a 5. In fairness, Bonefirm is
probably a 3.5 - 4 depending on their IP depth."*

---

## 1. You were right, and this is the first time level 5 has been reached

**Zero of the 16 prior cases scored 5, and no input ever mentioned a patent, trade secret,
flywheel or switching cost. Level 5 was unreachable by construction.** I built three cases to
test your claim directly.

| case | defensibility | raw | coverage | distribution |
|---|---:|---:|---:|---|
| **E1 ASML** (2,000+ EUV patents, 100% monopoly, exclusive Zeiss supply) | **5/5** | 3.63 | 0.69 | `{3: 0.31, 4: 0.66}` |
| **E2 Coupang** (self-owned logistics flywheel, decade-long loss barrier) | **5/5** | 3.57 | 0.64 | `{3: 0.43, 4: 0.57}` |

**Both halves of your claim hold. The dimension recognises IP *and* flywheels at level 5.**

**ASML composite 92 — the highest in the project** (was KOI 76). Coupang 82.

**The level-5 text reads:** *"Compounding. Several advantages that reinforce each other, where a
well-funded competitor could not replicate the position even given the time."* ASML's case —
patents + exclusive optics + non-substitutable integration + installed-base lock-in + 5,000-supplier
network — is that definition almost literally. A 100% EUV monopoly scored 5.

---

## 2. But IP does NOT cross the 3/4 boundary — your hedge does not resolve

**The decisive test.** `E4-bonefirm-ip` is Bonefirm, identical in every respect, with an explicit
disclosure added: the formulation is protected as a **trade secret** (not a patent, so it never
expires), the extraction and sequencing are **undisclosed**, and the manufacturing process is
**proprietary and not available through a supplier**.

| | defensibility | raw | coverage |
|---|---:|---:|---:|
| Bonefirm (original) | 3/5 | 1.65 | 0.71 |
| **Bonefirm + explicit IP** | **3/5** | **2.01** | **0.97** |

**The score did not move. The certainty did — 0.71 → 0.97.**

Distribution went `{2: 0.70}` → **`{2: 0.96}`** — mass *concentrated* on level 3. Adding
substantial IP made the model **more confident at 3, not inclined toward 4.**

### Why — the answer is in the level text

**Level 3 names the IP explicitly:**
> *"Real but replicable. A competitor must do genuine development work of their own — **a
> formulation, a process, or a technical system** — so copying takes them months, not weeks."*

**Level 4 names:** *"accumulated trust, an owned distribution channel, a **proprietary dataset**,
or years of relationship."*

**Patented and trade-secret IP is listed inside level 3. The only IP-like asset at level 4 is a
proprietary dataset.** So a formulation-based moat is a 3 **by construction** — no amount of IP
depth on a formulation can reach 4.

**Consequence: your "3.5–4 depending on their IP depth" cannot resolve.** The lever you named
does not move the dimension. Bonefirm is a 3 unless the *type* of asset changes, and Jev's 3 is
in line with your revised reading.

**Separately: you revised your own blind label from 4 to 3.5–4** — converging on Jev's 3, from
the same direction. Worth recording: the blind label disagreed, the reflection agreed.

---

## 3. Level 4 is a magnet, and the top is *less* confident than the middle

Four established incumbents, same run:

| case | raw |
|---|---:|
| C6 Eu Yan Sang | 2.91 |
| C3 Pet Lovers Centre | 2.89 |
| KOI | 2.89 |
| D2 Pet Lovers + cue | 2.83 |

**Spread 0.08 — exactly the measured noise floor.** A 146-year TCM icon, a 20-year tea chain and a
51-year pet chain are statistically the same number, each at **0.85–0.88 coverage** with ~88% of
mass on level 4.

**And the confidence ordering is inverted:**
- level-4 magnets → coverage **0.85–0.88** (very certain)
- level-5 ceiling cases → coverage **0.64–0.69** (least certain of any high scorer)

**The model is most confident in the saturated middle and least confident at the top**, where the
judgment requires assessing whether a well-funded competitor could *ever* replicate. That is the
harder question and the one the scale needs most.

---

## 4. Two dimensions measure a challenger's problem — the same defect as position_availability

**ASML produced two anomalies that are not ASML's fault:**

| dimension | result | why |
|---|---|---|
| `market_headroom` | **3/5** | the dimension asks *"is there room for a new or small entrant"* — **irrelevant to a 100% monopolist** |
| `competitive_room` | **withheld, coverage 0.00** | defined as *"how much room does competition leave"* — **with no competition there is no answer** |

**This is the same defect class I already found in `position_availability`** — an absolute framing
that inverts or fails for incumbents. `market_headroom` is written for an entrant. For ASML the
honest reading is "the market is closed to entrants, and that is the *strength*" — the opposite of
a low score.

**A 100% monopoly broke `competitive_room` into a withheld judgment.** The floor caught it (good),
but the dimension needs an incumbent branch, or the free report will mis-serve exactly the
established businesses most likely to pay for the paid engagement.

---

## 5. Full ladder, ranked

```
 5  E1 ASML (new ceiling)        3  observeco / bonefirm / E4-bonefirm-ip / C5 hawker /
 5  E2 Coupang                      C4 Sheng Siong / C2 ActiveSG (coverage 0.00, withheld)
 4  koi / D2 plc-cue / C6 euyansang / C3 petlovers
 2  bubbletea / N2 stripped / D1 watsons / C9 b2b
 1  N1 closed
```
Composites: **92 ASML** · 82 Coupang · 76 KOI · 73 C5 · 72 C2/C6 · 68 observeco · 67 C3/D2 ·
64 C4 · 59 bonefirm · 58 C9 · 54 E4 · 53 bubbletea · 52 N2 · 44 D1 · GATE N1.

---

## 6. Recommendation

1. **Keep the 1–5 scale** — level 5 exists and discriminates. Your IP/flywheel reading is confirmed.
2. **Split level 3** if IP-based moats should be distinguishable from mere copyable claims. Right
   now a trade-secret formulation and "we'll copy it in months" are the same score. Consider:
   3a *replicable despite protection* vs 3b *protected — development required, but not durable*.
3. **Add an incumbent branch to `market_headroom` and `competitive_room`** — a monopoly should be
   scored on defensibility of the position, not on room for entrants that cannot exist.
4. **Do not expect IP depth to move Bonefirm off 3.** It structurally cannot.
5. **The level-4 magnet matters for the product:** the free report will rank most established
   applicants identically at 4, so the report's differentiation among them must come from other
   dimensions and the narrative — not from defensibility.
