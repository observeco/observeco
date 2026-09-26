# FINDING — The gate was doing the wrong JOB, not sitting at the wrong THRESHOLD

**Date:** 2026-09-25
**Trigger:** Sean — *"We should have some gates to tell the user that certain businesses or
industries cannot be assessed. It is just that the gates have to be appropriate for the type of
businesses we wish to appreciate. It should work for competitive markets."*
**Script:** `test_assessability_gate.py` → `runs/assessability_gate.json`
**Verdict:** **Correcting my own conclusion. The gates should exist; they were asking the wrong
question. Re-asked as "can we assess this business at all?", a single gate separates the
unassessable from the assessable with a 0.92 margin — and it does so without firing on
Boeing/Airbus or any other concentrated business.**

---

## 1. What I got wrong

Across `FINDING-floor-investigation.md`, `FINDING-gate-boolean-test.md` and
`FINDING-outlier-scope-and-dead-gates.md` I concluded the gates were defective and should be
**deleted**. That conclusion was wrong, and Sean has corrected it.

**My error was diagnosing a threshold problem when the problem was the question.**

The three gates asked:
- *Is there any demand for this category at all?*
- *Does this business have any competitive room?*
- *Can this business reach any customers?*

**All three ask "is this business BAD?"** — and for the population this product serves, the answer
is never yes. Hence unreachable, hence inert.

**Wrong job.** A gate should not ask whether a business is bad. It should ask whether the
**method can work on this business at all.**

**Sean's framing, which is the correct one:** *the gate exists to tell the user that certain
businesses or industries cannot be assessed — and it must be appropriate for the businesses we
want to serve, which are in competitive markets.*

---

## 2. The right question, and why it has a real answer

The product is **positioning analysis**: it finds a place in the customer's mind that rivals have
not already taken.

**That method requires rivals to exist.** With no competitors, there is no occupied position to
find space beside, no contrast to draw, nothing for the analysis to operate on. The report would
be meaningless — not because the business is bad, but because **the instrument has nothing to
measure.**

**The gate's true job: "is this a market in which positioning analysis can be performed?"**

---

## 3. Result

| case | P(no competitive market) | verdict |
|---|---:|---|
| **E1 ASML** | **1.00** | **CANNOT ASSESS** |
| C2 ActiveSG | 0.08 | assessable |
| F3 VICOM | 0.06 | assessable |
| **F1 Boeing/Airbus** | **0.04** | **assessable** |
| C5 Michelin hawker | 0.02 | assessable |
| 07 ObserveCo | 0.01 | assessable |
| **F2 Watsons/Guardian** | **0.00** | **assessable** |
| *all 13 others* | **0.00** | assessable |

```
fires on   : ['E1-asml'] only
missed     : none
over-fired : none
separation : 1.00 vs 0.08  =  0.92
```

**Pre-registered before the run, and both predictions held:**
- ASML **must** fire → **1.00** ✅
- Boeing/Airbus, Watsons/Guardian and all ordinary businesses **must not** fire → max **0.08** ✅

---

## 4. The pair that proves what the gate is measuring

ASML and Boeing/Airbus are **both** extraordinarily concentrated. If the gate were keying on
concentration, size or market power, it would fire on both.

| case | structure | P(cannot assess) |
|---|---|---:|
| **ASML** | sole supplier of EUV worldwide | **1.00** |
| **Boeing/Airbus** | duopoly, ~all large commercial aircraft | **0.04** |
| **Watsons/Guardian** | duopoly, ~32% of SG health & beauty | **0.00** |

**The gate separates a monopoly from duopolies.** Boeing and Airbus compete ferociously for every
order — there is a genuine struggle for position, so the analysis works. ASML has no rival at all.

**This is exactly the "works for competitive markets" property Sean specified.** A duopoly is a
competitive market for these purposes; a sole supplier is not.

---

## 5. This also settles the earlier ASML dispute — correctly, this time

In `FINDING-gate-boolean-test.md` I found ASML firing at 0.65 on the room gate and called it a
**falsification** — the strongest business in the corpus being refused. I then said the fix was to
reframe `competitive_room` for incumbents.

**The observation was right; the conclusion was wrong.** ASML firing was **not** the gate
malfunctioning. It was the gate **correctly detecting that ASML is a case the method cannot work
on** — via a badly-worded question that happened to arrive at the right place.

**The correct fix is not to stop ASML firing. It is to make the gate fire for the right reason,
with wording that cannot be misread as "this business is weak."**

**And this is why the earlier "delete the gates" recommendation was dangerous:** it would have
removed the system's only means of telling a user "we cannot assess your business." The 0.65 signal
was real. I read it as noise and proposed removing the instrument that produced it.

**Fifth instance in this project of a flagged defect being the instrument working — and the
clearest yet, because this time I proposed deleting the instrument.**

---

## 6. Recommended gate set

**Replace the three dead gates with ONE assessability gate.** Keep the two that work.

| gate | question | status |
|---|---|---|
| **assessability** (NEW) | "Does this business compete in a market where other suppliers compete for the same customers?" | **fires on ASML only; separation 0.92** |
| mental_advantage | working | keep as-is |
| defensibility | working | keep as-is |
| ~~market_headroom~~ | "is demand absent?" — unreachable | delete |
| ~~competitive_room~~ | "is room absent?" — unreachable | delete |
| ~~demand_reach~~ | "no route to customers?" — unreachable | delete |

**The two remaining jobs are cleanly distinct:**
- **assessability** — "we cannot produce a meaningful analysis for this business."
- **mental_advantage + defensibility** — "we can analyse it, and it is not viable."

Different messages to the user, different mechanisms. Neither is decorative.

---

## 7. What this does NOT establish

- **n=1 positive.** ASML is the **only** case in the corpus that should trip this gate, so the
  validation rests on one case, as with every other test in this project. **The separation is 0.92
  and the mechanism is clear, but this needs more unassessable cases before shipping.**
- **Sean said "certain businesses or industries" — singular ASML is not that population.** Other
  unassessable classes plausibly exist and this gate does not yet cover them:
  - **statutory sole operators** (a licensed monopoly, a national utility, a sole concessionaire)
  - **a category of one** (a founder whose offering genuinely has no comparator)
  - **pre-revenue / pre-launch** businesses with no market presence to analyse
  - **an industry too new to have formed positions at all**
  **None of these has been tested. The gate as written may or may not catch them.**
- **`N1` (closed business) does NOT fire this gate — 0.00, correctly.** Bubble tea is a competitive
  market. N1 is caught by mental_advantage + defensibility. **The two gate families work on
  different problems, which is the intended design.**
- **The wording is load-bearing and I have tested exactly one version.** "Sole supplier / no
  meaningful alternative" may behave differently on a near-monopoly, a strong brand leader, or a
  business that merely *believes* it has no competitors. **Untested.**
- **I have not verified the gate against the 0.65 room-gate reading.** Whether a business must fail
  both wordings to be truly unassessable is open.
- **Still zero human labels against the rubric.** The #1 validity blocker, untouched by this work.
