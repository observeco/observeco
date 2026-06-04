# Confidence & Recommendation Framework — Implementation Plan

> **For Hermes:** Build spec first (master plan §3.29), then follow plan task-by-task with TDD + independent verification.

**Goal:** Add confidence scoring, false-positive/false-negative risk, and actionable recommendations to every agent card metric row and detail tab in the ObserveCo dashboard.

**Architecture:** A single `_compute_confidence()` function in `server.py` that takes agent signals (pulses, errors, circuit breaker, status duration) and returns confidence/risk/recommendation for each metric row. Rendered as small badges on cards and full sections in detail tabs.

**Kanban tasks:** Create 3 tasks: (1) confidence function, (2) card-level rendering, (3) detail tab rendering.

**Files changed:**
- `specs/observeco-master-plan.md` — new §3.29 (this is the spec)
- `src/observeco/dashboard/server.py` — `_compute_confidence()` + card rendering + detail tabs
- `src/observeco/dashboard/templates/index.html` — no JS changes needed (server-side rendering)
- `tests/` — new test file for confidence scoring

---

## Kanban Tasks

### t_confidence_function
- **What:** Write `_compute_confidence()` that takes pulses, errors, circuit, status, and returns confidence score + FP risk + FN risk + recommendation text
- **Inputs:** agent status, recent pulses, recent errors, circuit breaker state, duration in current state
- **Outputs:** `{"level": "high"|"medium"|"low", "fp_risk": "low"|"moderate"|"high", "fn_risk": "low"|"moderate"|"high", "recommendation": "...", "sources_agree": "...", "detail": "..."}`

### t_card_confidence
- **What:** Add confidence badges + recommendations to agent card metric rows (Health, Guard, Errors)
- **Where:** server.py agent card rendering loop (~line 2440-2510)
- **What shows:** Small colored dot next to each metric value (🟢 High · 🟡 Med · ⚪ Low)

### t_detail_confidence
- **What:** Add full confidence, FP/FN risk, and recommendation section to each detail tab (Health, Guard, Errors)
- **Where:** server.py `_detail_health_tab()`, `_detail_guard_tab()`, `_detail_errors_tab()`
- **What shows:** "Confidence: X · FP risk: Y · FN risk: Z · Recommended action: ..."

---

## Spec: Confidence Scoring Algorithm

### Inputs
All from existing DB queries — no new tables or data sources.

| Signal | Source | Weight |
|--------|--------|--------|
| **Duration** | Pulse timestamps — how long in current status | 1.0x |
| **Consecutive count** | Pulse sequence — how many checks in a row agree | 1.5x |
| **Source agreement** | Pulse status + error count + circuit breaker state | 2.0x |
| **Pattern stability** | Error message consistency | 0.5x |

### Scoring

**Confidence (1-4 scale):**
- **4/4 = HIGH** — All signals agree, state persisted >2h, 3+ consecutive checks
- **2-3/4 = MEDIUM** — Some signals agree, state <30min, 1-2 checks
- **0-1/4 = LOW** — Single source, just changed, isolated reading

**FP risk** (how likely is this flag to be a false alarm?):
- **Low** — Multiple independent sources confirm. State is old. Errors are consistent.
- **Moderate** — Two sources. State is recent. Errors vary.
- **High** — Single source. State just changed. Single reading.

**FN risk** (how likely is a green flag to be missing something?):
- **Low** — Agent just checked. Process confirmed. Consistent pulses.
- **Moderate** — Last check >30min ago. Stale status.
- **High** — No recent pulses. Process not confirmed. Data is >1h old.

### Recommendations

| Condition | Recommendation |
|-----------|---------------|
| Agent dead, high confidence | `➤ Agent has been down for X days. Start it manually: observeco start <name>` |
| Agent dead, low confidence | `➤ Agent may be down. Run observeco pulse check <name> to confirm.` |
| Guard tripped, high confidence | `➤ Guard stopped checking after 3 failures. Wait ~4h for cooldown, or restart the agent.` |
| Guard tripped, low confidence | `➤ Guard triggered but seems isolated. Monitor — it may reset automatically.` |
| Multiple errors, high confidence | `➤ X errors from a dead agent. Restart the agent to stop the noise.` |
| Multiple errors, medium confidence | `➤ X errors — could be transient or ongoing. Run observeco healt --diagnose.` |
| Single error | `➤ Single error — likely transient. No action needed unless it repeats.` |
| Stale running (alive but old) | `➤ Last check was Xh ago. The agent could have died between cycles. Run observeco pulse check.` |
| Perfect health, high confidence | `➤ All clear — 14 consecutive checks passed.` |
| Perfect health, low confidence | `➤ No issues yet — but only X checks recorded. Continue monitoring.` |

---

## Build Plan

### Step 1: Write spec → master plan §3.29
- Read master plan to find right location (after §3.28)
- Write §3.29 with confidence algorithm, recommendation table, rendering spec

### Step 2: Write tests for `_compute_confidence()`
- Test dead agent long duration → high confidence
- Test single missed pulse → low confidence
- Test stale running → medium confidence, high FN risk
- Test perfect health → high confidence, low FP/FN risk
- Test guard tripped → high confidence, low FP risk
- Test single error → medium confidence, high FP risk

### Step 3: Implement `_compute_confidence()`
- ~50 lines in server.py
- Returns dict with level, fp_risk, fn_risk, recommendation, detail

### Step 4: Wire into agent card
- Call `_compute_confidence()` in the card rendering loop
- Add small confidence dot to Health, Guard, Errors rows
- Display recommendation as tooltip or inline text below the row

### Step 5: Wire into detail tabs
- Add confidence header to Health, Guard, Errors tabs
- Show FP/FN risk badges
- Show recommendation as the first section

### Step 6: Run tests + verify
- Run full test suite (270+ tests)
- Manual TestClient verification for dead + alive + stale agents
- Commit and push