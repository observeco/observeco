# Fleet Health Classification & Verdict Contract

**Status:** ADOPTED — passed adversarial review (deleg_68cb02e6, round 2 of Rev 8: "PASSED — ever_alive-gate dead-code bug fixed, both exclusion categories reachable, nothing new fundamentally broke"). Now the build authority.
**Date:** 2026-08-08
**Source of truth for:** `_classify_agent`, `_fleet_verdict`,
`get_agent_status_summary()` in the ObserveCo dashboard.

---

## 0. Why prior discriminators were wrong

- **Config-based** (Rev 4-5): half the fleet (12 pgrep-alive Hermes agents) has
  no health_check yet runs fine. Excluding them hides 12 healthy agents.
- **is_active-based** (Rev 1-3): all is_active=0, cannot discriminate.
- **Behavioral-only** (Rev 6): correctly split the 38, but hid real outages — a
  dead managed daemon and a configured-never-run daemon both vanished into
  neutral/benign categories.

The behavioral re-grounding was right on the *monitored boundary*, but it
dropped the *config* signal that distinguishes a managed outage from benign
idle. **The two signals answer different questions:**

- `ever_alive` → **is this agent monitored?** (has anything been observed)
- qualifying `health_check` → **is this agent managed?** (is a down state an
  outage that must alert, or benign on-demand idle)

---

## 1. The three signals and five categories

**Signal A — ever_alive** (has this agent ever had an alive pulse?):
- `False` → NOT OBSERVED (never seen running).
- `True` → was monitored at some point.

**Signal B — alive_now** (latest pulse is alive?):
- Determines healthy vs not-running.

**Signal C — qualifying health_check** (launchd:/docker:/systemd:/http://
https://):
- `True` → MANAGED (a down state is an abnormal outage → alert).
- `False` → UNMANAGED (pgrep/echo/empty; a down state is benign — on-demand
  idle or finished-normally, can't distinguish).

| ever_alive | alive_now | managed | Category | In denominator? | Alert? |
|---|---|---|---|---|---|
| T | T | any | HEALTHY | ✅ | no |
| T | F | T | MANAGED DOWN | ✅ | **WARNING/CRITICAL** |
| T | F | F | NOT RUNNING | ✅ | no (neutral) |
| F | F | T | CONFIGURED NEVER RAN | ❌ (excluded) | **WARNING** |
| F | F | F | NOT OBSERVED | ❌ (excluded, chip) | no |

*Note: `F/T` (never-alive with a live pulse) is unreachable — a live pulse
implies the agent has been observed alive. Never-alive agents always have
`alive_now=False`.

**Decision 1 — "not running" is neutral ONLY for unmanaged:** an unmanaged
ever-alive-but-down agent (workspace/kanban) is "not running" — neutral, no
alert, because without expected-lifetime metadata you cannot distinguish
crashed from finished-normally. But a **managed** ever-alive-but-down agent is
MANAGED DOWN — an alert, because a continuously-managed daemon being down is
definitionally abnormal.

**Decision 2 — "not observed" vs "configured never ran":** a never-alive agent
with NO qualifying health_check is "not observed" (benign clickable chip — for
a Hermes profile, never running may be expected). A never-alive agent WITH a
qualifying health_check is CONFIGURED NEVER RAN — it is *configured* to be a
daemon but has never run (crashed at boot, never launched); that is an alert.

---

## 2. `_classify_agent` rules (top-to-bottom, first match wins)

```
1. IF ever_alive = False AND managed              → CONFIGURED NEVER RAN (WARNING)
2. IF ever_alive = False AND NOT managed          → NOT OBSERVED (excluded, chip)
3. IF alive_now = True                            → HEALTHY
4. IF ever_alive AND NOT alive_now AND managed    → MANAGED DOWN (WARNING/CRITICAL)
5. IF ever_alive AND NOT alive_now AND NOT managed → NOT RUNNING (neutral)
```

**The ever_alive gate is load-bearing:** rules 4-5 (`NOT alive_now`) carry the
explicit `ever_alive` predicate, so they only apply to agents that have EVER
been observed alive. A never-alive agent always has `alive_now=False` (a live
pulse implies ever-observed); without the gate it would be swept into MANAGED
DOWN / NOT RUNNING before ever reaching the exclusion rules — making CONFIGURED
NEVER RAN and NOT OBSERVED unreachable dead code. Rules 1-2 handle never-alive
agents FIRST, keeping both exclusion categories reachable.

- `managed` = qualifying health_check (launchd:/docker:/systemd:/http://https://).
- Rules 3-5 are ever-alive (was monitored); they stay in the denominator.
- Rules 1-2 are never-alive; excluded from the denominator, but CONFIGURED
  NEVER RAN alerts while NOT OBSERVED is a benign chip.

---

## 3. Verdict fixture→sentence table

`H` = healthy, `MD` = managed-down, `NR` = not-running (unmanaged),
`CN` = configured-never-ran, `O` = not-observed.
`M` = monitored = H + MD + NR. `E` = excluded = CN + O.

| # | Condition | Verdict sentence | Icon |
|---|---|---|---|
| 1 | `MD > 0` | `{MD} of {M} managed agents are DOWN — {names}` | 🔴 |
| 2 | `CN > 0` | `{CN} configured agents never ran — {O} not observed` | 🟡 |
| 3 | `H = 0 AND MD = 0 AND NR = 0` (nothing ever observed, or all excluded) | `No agents observed running yet — {CN} configured never ran, {O} not observed` | ⚪ |
| 4 | `NR > 0` | `{H} agents healthy — {NR} not running, {O} not observed` | neutral |
| 5 | `O > 0` | `{H} agents healthy — {O} not observed` | 🟢 |
| 6 | `else` (all healthy) | `All {H} agents healthy` | 🟢 |

**Not-observed chip (clickable):** `{O} not observed` lists the agents on click
(the benign story). **Configured-never-ran is a separate visible row** (an
alert, not folded into the chip).

**Onboarding transition (no manual step):** a never-alive agent that first
becomes alive_now moves into the monitored set automatically — from `O`/`CN`
to `H`, driven purely by the next ever_alive flip. Fresh install (all never
alive) shows row 3; when the first starts, it transitions to row 5.

---

## 4. Distinguishing tests

**Test 1 — behavioral, config-blind (the 12):**
> An agent with NO health_check, ever_alive=1, alive_now=1 is HEALTHY — pinned
> to a specific class (e.g. `hermes-agent`), so a class-based impl whose
> "monitored" class set includes it fails on a non-monitored-class fixture.

**Test 2 — managed down is an alert, unmanaged not-running is neutral:**
> A launchd-managed agent (qualifying health_check) ever_alive=1 not-alive-now
> → MANAGED DOWN (alert). An unmanaged agent (pgrep/empty) ever_alive=1
> not-alive-now → NOT RUNNING (neutral, no alert).

**Test 3 — configured-never-ran alerts, not-observed is benign:**
> A never-alive agent WITH qualifying health_check → CONFIGURED NEVER RAN
> (alert). A never-alive agent WITHOUT → NOT OBSERVED (benign chip).

**Test 4 — denominator disclosed, output varies by input (blocks hardcoding):**
> Given distinct fixture sets (e.g. {H:25,NR:2,O:11} and {H:10,MD:1,O:27}),
> the verdict renders the correct per-set sentence. Hardcoding one output
> fails the other fixture.

**Test 5 — onboarding transition:**
> A never-alive agent that first becomes alive_now moves from O/CN to H with
> no manual step; the verdict reflects the flip.

**Test 6 — zero-observed never fake-clean:**
> Given H=0,MD=0,NR=0,CN=0,O>0 → "No agents observed running yet," never
> "all 0 agents healthy."

---

## 5. Build-time verification checklist

- [ ] `_classify_agent` uses ever_alive + alive_now + qualifying health_check
      (managed) per §2.
- [ ] Managed down → alert (WARNING/CRITICAL); unmanaged not-running → neutral.
- [ ] Configured-never-ran → alert; not-observed → benign clickable chip.
- [ ] Verdict accounts for MD/CN/NR/O in every sentence.
- [ ] Onboarding transition automatic.
- [ ] Zero-observed row honest.
- [ ] The 6 tests pass on the corrected impl and FAIL on config-based,
      class-based, behavioral-only, and hardcoded wrong impls.

---

## 6. Changelog

- **Rev 1-5 (2026-08-08):** config-based/is_active discriminators, disproven.
- **Rev 6 (2026-08-08):** behavioral-only (ever_alive). Correctly split the 38
  but hid managed-daemon outages.
- **Rev 7 (2026-08-08):** two-signal model — ever_alive (monitored boundary)
  + qualifying health_check (managed/unmanaged). Managed down → alert; managed
  never-ran → alert; unmanaged not-running/not-observed → neutral/benign.
- **Rev 8 (2026-08-08):** per deleg_a27715da review — added the ever_alive gate
  to classifier rules 3-4 (fixes dead-code CONFIGURED NEVER RAN / NOT OBSERVED),
  reordered verdict rows so fresh-install fires before the healthy rows, and
  corrected the unreachable F/T table rows.
- **Rev 8.1 (2026-08-08):** per deleg_68cb02e6 review — encoded the ever_alive
  gate explicitly in the rule predicates (never-alive handled first as rules
  1-2, no GOTO), added `{O}` to the configured-never-ran verdict row. ADOPTED.
