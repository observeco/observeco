# Spec Audit: Runtime Health Section — ObserveCo Master Plan

**Auditor:** Hermes Agent (senior product spec auditor)
**Date:** 2026-06-26
**Scope:** Features #2 (Pulse Check), #3 (Circuit Breakers/Safety Guard), #7 (Heal Tab), #8 (In-Dashboard Alerts), #15 (Auto-Heal), #17 (Push Alerts), #22 (Agent Health Detection Engine), G1/G2/G3 Safety Guardrails, plus new proposals from health-improvement-verified.md
**Playbooks consulted:** requirements-fidelity-playbook.md, coding-fidelity-playbook.md, system-design-testing-playbook.md, ux-testing-playbook.md, master-fidelity-gate.md
**Source:** health-improvement-verified.md (independent codebase analysis)

---

## 1. Findings Table

| # | Finding | Severity | Feature(s) | Evidence | Recommendation |
|---|---------|----------|-------------|----------|---------------|
| F1 | **#15 Auto-Heal status contradiction** — Feature table (line 57) says "✅ Live — dashboard heal config page with per-agent L1/L2 toggles, thresholds, events log, start-watch". Deep-dive §3.15 (line 794) says "✅ Backend / ❌ Dashboard UI". These directly contradict. The deep-dive explicitly states "Dashboard UI missing — no toggle, no status card, no per-agent config." | **CRITICAL** | #15 Auto-Heal | Master plan line 57 vs line 794-800. Feature table claims full dashboard UI exists; deep-dive says it doesn't. This is exactly Trap 7 (Feature Status Without Layer Decomposition). | Resolve contradiction. If dashboard UI is truly missing, update feature table to "✅ Backend / ❌ Dashboard UI" to match deep-dive. If it was recently built, update deep-dive to match feature table. |
| F2 | **#17 Push Alerts status contradiction** — Feature table (line 59) says "✅ Live — dashboard subscription form, test/delete buttons, delivery log". Deep-dive §3.17 (line 1339) says "✅ Backend / ❌ Dashboard UI". Same contradiction pattern as F1. Deep-dive explicitly states "Dashboard UI missing — no subscription management UI, no delivery log view, no test button." | **CRITICAL** | #17 Push Alerts | Master plan line 59 vs line 1339-1345. Same Trap 7 issue. | Resolve contradiction. Update feature table to "✅ Backend / ❌ Dashboard UI" to match deep-dive, or update deep-dive if dashboard UI was built. |
| F3 | **#8 In-Dashboard Alerts has no state coverage** — §3.8 is only 18 lines. No state table, no lifecycle, no loading/empty/error states, no success metrics, no constraints register. It's a value-driver description, not a spec. | **HIGH** | #8 In-Dashboard Alerts | §3.8 (lines 609-627) — only describes the "discovery gap badge" value proposition. No RDR, no states, no ACs, no lifecycle. | Add full RDR with state matrix (loading, empty, error, partial, stale, timeout), lifecycle (start/run/crash/reboot/cleanup), success metrics, and constraints register. |
| F4 | **#2 Pulse Check has no success metrics** — §3.2 describes the mechanism and what the human sees, but has no quantitative success metrics. How fresh must pulse data be? What's the acceptable staleness threshold? How fast must failure be detected? | **HIGH** | #2 Pulse Check | §3.2 (lines 204-268) — no "Success Metrics" section. No quantitative targets for detection latency, data freshness, or uptime. | Add success metrics: detection latency <35s (within 2 cycles), data freshness <60s, false positive rate <1%. |
| F5 | **#3 Safety Guard has no success metrics** — §3.3 describes the mechanism and value calculation but has no quantitative success metrics for guard effectiveness. | **HIGH** | #3 Safety Guard | §3.3 (lines 270-363) — no "Success Metrics" section. | Add success metrics: guard trips within 3 consecutive failures, cooldown accuracy ±10%, zero false trips on healthy agents. |
| F6 | **#22 Agent Health Detection Engine has misleading status** — Feature table says "✅ Layers 1-2 / 🔴 P2-P5" with Free column "✅ All (detection + health — core infra for everything)". The "✅ All" claim is misleading when P2-P5 (platform connectivity, crash analysis, costs, comm tracing, CI/CD) are not built. | **MEDIUM** | #22 Agent Health Detection Engine | Line 64 — "✅ All" in Free column contradicts the partial status. | Change Free column to "✅ Layers 1-2 only" to match the status. Remove "core infra for everything" language. |
| F7 | **#2 Pulse Check has no lifecycle specification** — §3.2 describes steady-state operation but doesn't specify what happens on start (no data yet), crash (daemon dies), reboot (resume from last state), or cleanup (stale data pruning). | **MEDIUM** | #2 Pulse Check | §3.2 (lines 204-268) — no lifecycle section. | Add lifecycle matrix: Start (no data → "Collecting pulses..."), Run (steady state), Crash (daemon restart → resume from last pulse), Reboot (no data gap), Cleanup (prune pulses >7d free, >90d pro). |
| F8 | **#3 Safety Guard has no lifecycle specification** — Same as F7. The guard's behaviour on daemon restart (HealCircuit resets in-memory) is documented in §3.7 but not in §3.3. | **MEDIUM** | #3 Safety Guard | §3.3 (lines 270-363) — no lifecycle section. HealCircuit reset behaviour is in §3.7, not §3.3. | Add lifecycle matrix to §3.3. Cross-reference §3.7 for HealCircuit behaviour. Document that in-memory guard resets on daemon restart. |
| F9 | **#8 In-Dashboard Alerts has no lifecycle** — §3.8 doesn't specify what happens on first load (no alerts yet), crash (alerts lost?), or reboot. | **MEDIUM** | #8 In-Dashboard Alerts | §3.8 — no lifecycle section. | Add lifecycle: Start (empty state), Run (alert accumulation), Crash (last N alerts cached), Reboot (resume from DB), Cleanup (prune resolved alerts). |
| F10 | **#15 Auto-Heal and #17 Push Alerts have no success metrics** — Both have acceptance criteria but no quantitative success metrics. "Toggle enabled → heal daemon picks up config change ≤30s" is an AC, not a success metric. | **MEDIUM** | #15 Auto-Heal, #17 Push Alerts | §3.15 (lines 834-842), §3.17 (lines 1398-1407) — ACs exist but no success metrics section. | Add success metrics: Auto-Heal detection-to-recovery <10s P95, Push Alert delivery <5s P99 for Telegram/email, <30s for Discord. |
| F11 | **#2 Pulse Check has no constraints register** — No cross-platform constraints (pgrep is POSIX-only, Windows needs tasklist), no multi-instance constraints (two daemons writing to same pulse_log), no first-run constraints. | **MEDIUM** | #2 Pulse Check | §3.2 — no constraints register. | Add constraints: Windows process detection (tasklist/Get-Process), multi-instance (instance_id in pulse_log), first-run (no agents yet → empty state). |
| F12 | **#3 Safety Guard has no constraints register** — No cross-platform constraints for process detection, no multi-instance constraints for HealCircuit (in-memory, resets on restart). | **MEDIUM** | #3 Safety Guard | §3.3 — no constraints register. | Add constraints: HealCircuit is in-memory (resets on daemon restart), cross-platform signal handling (SIGTERM vs CTRL_BREAK_EVENT), multi-instance cooldown coordination. |
| F13 | **#15 One-click health fix from alert (health-improvement #15) not in master plan** — The health-improvement analysis identifies that action buttons in push notifications (Telegram inline keyboards, Discord buttons, webhook action URLs) are a high-impact, medium-effort feature. The heal system has `_execute_action()` with restart/cooldown/pip_install/trim/garden_cleanup. Push alerts exist. The missing piece is wiring them together. | **HIGH** | New feature (not in master plan) | health-improvement-verified.md lines 57-58. Heal system has actions, push alerts exist, but no action buttons in notifications. | Add new feature row or sub-feature under #17 Push Alerts: "Action buttons in push notifications — Telegram inline keyboards, Discord buttons, webhook action URLs. Calls /api/trigger-heal or /api/heal-action/{agent}/{action}." |
| F14 | **#13 Agent health report card (weekly digest) not in master plan** — The health-improvement analysis identifies a weekly digest aggregating pulse_log, heal_events, circuit_events, compress_log, token_logs into a push alert. All data exists. | **MEDIUM** | New feature (not in master plan) | health-improvement-verified.md lines 55-56. All data exists in existing tables. Push alert infra is live. | Add new feature row: "Agent Health Report Card — weekly digest via push alert. Aggregates 7d of pulse uptime, auto-heals, circuit trips, compressions, cost. One SQL query per metric, one Jinja2 template." |
| F15 | **G1.4 Turn-Rate Alerting already spec'd but not cross-referenced from health-improvement** — The health-improvement analysis lists N3 (Turn-Rate Alerting) as a new idea, but it's already spec'd as G1.4 in the master plan. This is a documentation gap, not a spec gap. | **LOW** | G1.4 | health-improvement-verified.md lines 90-93 vs master plan lines 102, 8200, 8262-8271. | No action needed — already spec'd. The health-improvement doc correctly notes it's "Already spec'd as G1.4." |
| F16 | **#59 Composite Health Score already spec'd but not cross-referenced from health-improvement** — Same as F15. N1 is already spec'd as #59. | **LOW** | #59 | health-improvement-verified.md lines 82-84 vs master plan lines 123, 8470-8505. | No action needed — already spec'd. |
| F17 | **#33 Anomalies Inbox already spec'd but not cross-referenced from health-improvement** — Same as F15. N2 is already spec'd as #33. | **LOW** | #33 | health-improvement-verified.md lines 86-88 vs master plan lines 87, 5284-5383. | No action needed — already spec'd. |
| F18 | **#39 Tool Efficiency Ranking already spec'd but not cross-referenced from health-improvement** — Same as F15. N4 is already spec'd as #39. | **LOW** | #39 | health-improvement-verified.md lines 94-96 vs master plan lines 95, 6362-6461. | No action needed — already spec'd. |
| F19 | **#17 Push Alerts: Discord not implemented** — Deep-dive §3.17 (line 1345) states "Discord not yet implemented (needs Discord webhook integration)." Feature table says "✅ Live — dashboard subscription form, test/delete buttons, delivery log" which implies all channels are live. | **MEDIUM** | #17 Push Alerts | Line 1345 — "Discord not yet implemented." Feature table doesn't mention this gap. | Add note to feature table: "✅ Telegram/webhook/email / 🔴 Discord pending." Or update deep-dive if Discord was recently built. |
| F20 | **G1.1-G1.6 have no cross-reference verification** — The G1 guardrails reference §14.3.G1.1-6 but don't verify that the deep-dive sections (§14.4-14.7) agree with the feature table rows (lines 99-104). | **LOW** | G1.1-G1.6 | Lines 99-104 vs lines 8195-8293. Both describe the same features but with different levels of detail. No explicit cross-reference verification. | Add cross-reference verification note confirming §14.3 and feature table agree. |

---

## 2. Status Marker Audit

### Feature Table Status (lines 55-127) vs Deep-Dive Status

| Feature | Feature Table Status | Deep-Dive Status | Actual Codebase Status (from health-improvement) | Verdict |
|---------|---------------------|------------------|--------------------------------------------------|---------|
| **#2 Pulse Check** | ✅ Live | ✅ Live (§3.2) | ✅ Live — watch daemon polls every 30s, writes to pulse_log | ✅ Correct |
| **#3 Safety Guard** | ✅ Live | ✅ Live (§3.3) | ✅ Live — 3-failure trip, 4h cooldown, in-memory HealCircuit | ✅ Correct |
| **#7 Heal Button** | ✅ Live | ✅ Live (§3.7) | ✅ Live — `heal/__init__.py` with `_diagnose_agent()`, `_execute_action()`, HealCircuit | ✅ Correct |
| **#8 In-Dashboard Alerts** | ✅ Live | ✅ Live (§3.8) | ✅ Live — alerts display in dashboard with discovery gap badges | ✅ Correct (but spec is thin) |
| **#15 Auto-Heal** | ✅ Live | ✅ Backend / ❌ Dashboard UI | ✅ Backend (`heal/__init__.py` — 569 lines, L1 auto-restart, L2 proactive) / ❌ Dashboard UI missing | ❌ **CONTRADICTION** — feature table says "✅ Live" but deep-dive says dashboard UI missing |
| **#17 Push Alerts** | ✅ Live | ✅ Backend / ❌ Dashboard UI | ✅ Backend (`alerts/push.py` — 205 lines, Telegram/webhook/email) / ❌ Dashboard UI missing / 🔴 Discord not implemented | ❌ **CONTRADICTION** — feature table says "✅ Live" but deep-dive says dashboard UI missing and Discord not built |
| **#22 Agent Health Detection Engine** | ✅ Layers 1-2 / 🔴 P2-P5 | ✅ Layers 1-2 / 🔴 P2-P5 (§3.22) | ✅ Layers 1-2 (process health, OTel, cross-framework) / 🔴 P2-P5 (platform connectivity, crash analysis, costs, comm tracing, CI/CD) | ⚠️ **Misleading** — Free column says "✅ All (detection + health — core infra for everything)" which contradicts the partial status |
| **G1.1 Self-Monitoring Budget Cap** | 🔴 Planned | 🔴 Planned (§14.3.G1.1) | 🔴 Not built | ✅ Correct |
| **G1.2 Manual Kill Switch** | 🔴 Planned | 🔴 Planned (§14.3.G1.2) | 🔴 Not built | ✅ Correct |
| **G1.3 Activity-Based Circuit Breaker Config** | 🔴 Planned | 🔴 Planned (§14.3.G1.3) | 🔴 Not built | ✅ Correct |
| **G1.4 Turn-Rate Alerting** | 🔴 Planned | 🔴 Planned (§14.3.G1.4) | 🔴 Not built | ✅ Correct |
| **G1.5 Tool-Call Count Per Turn** | 🔴 Planned | 🔴 Planned (§14.3.G1.5) | 🔴 Not built | ✅ Correct |
| **G1.6 Threat Model Documentation** | 🔴 Planned | 🔴 Planned (§14.3.G1.6) | 🔴 Not built | ✅ Correct |
| **G2.1-G2.5** | 🔴 Planned | 🔴 Planned (§14.3.G2) | 🔴 Not built | ✅ Correct |
| **G3.1-G3.3** | 🔴 Planned | 🔴 Planned (§14.3.G3) | 🔴 Not built | ✅ Correct |
| **#33 Anomalies Inbox** | 🔴 Spec | 🔴 Spec (§3.37) | 🔴 Not built | ✅ Correct |
| **#39 Tool Efficiency Ranking** | 🔴 Spec | 🔴 Spec (§3.43) | 🔴 Not built | ✅ Correct |
| **#59 Composite Health Score** | 🔴 Planned | 🔴 Planned (§3.59) | 🔴 Not built | ✅ Correct |

### Status Marker Issues Summary

| Issue | Severity | Features Affected |
|-------|----------|-------------------|
| **Contradictory status** — feature table says "✅ Live" but deep-dive says "❌ Dashboard UI missing" | CRITICAL | #15 Auto-Heal, #17 Push Alerts |
| **Misleading Free column** — says "✅ All" when only Layers 1-2 are built | MEDIUM | #22 Agent Health Detection Engine |
| **Missing channel gap** — feature table implies all channels live, but Discord is not implemented | MEDIUM | #17 Push Alerts |

---

## 3. Gap Analysis

### What's Missing from the Master Plan (from health-improvement-verified.md)

| Gap | Source | Effort | Impact | Why It's Missing | Recommended Action |
|-----|--------|--------|--------|------------------|-------------------|
| **One-click health fix from alert** — action buttons in push notifications (Telegram inline keyboards, Discord buttons, webhook action URLs) | health-improvement #15 | ~4h | High | Heal system has `_execute_action()` with restart/cooldown/pip_install/trim/garden_cleanup. Push alerts exist. The wiring between them was never spec'd. | Add as sub-feature under #17 Push Alerts or new feature row. See §4.1. |
| **Agent health report card (weekly digest)** — scheduled push alert aggregating 7d of pulse uptime, auto-heals, circuit trips, compressions, cost | health-improvement #13 | ~3h | Medium | All data exists in existing tables. Push alert infra is live. The weekly digest format was never spec'd. | Add as new feature row. See §4.2. |
| **Composite Health Score (#59)** — already spec'd, not a gap | health-improvement N1 | — | — | Already in master plan as 🔴 Planned | No action needed |
| **Anomalies Inbox (#33)** — already spec'd, not a gap | health-improvement N2 | — | — | Already in master plan as 🔴 Spec | No action needed |
| **Turn-Rate Alerting (G1.4)** — already spec'd, not a gap | health-improvement N3 | — | — | Already in master plan as 🔴 Planned | No action needed |
| **Tool Efficiency Ranking (#39)** — already spec'd, not a gap | health-improvement N4 | — | — | Already in master plan as 🔴 Spec | No action needed |

### Spec Quality Gaps (from playbook traps)

| Gap | Trap | Features Affected | Severity |
|-----|------|-------------------|----------|
| No success metrics for any Runtime Health feature | Trap 4 | #2, #3, #8, #15, #17 | HIGH |
| No lifecycle specification for pulse/guard/alert features | Trap 3 | #2, #3, #8 | MEDIUM |
| No constraints register for pulse/guard features | Trap 5 | #2, #3 | MEDIUM |
| In-Dashboard Alerts has no state coverage at all | Trap 1, Trap 2 | #8 | HIGH |
| Contradictory status markers for #15 and #17 | Trap 6, Trap 7 | #15, #17 | CRITICAL |

---

## 4. Recommended Updates to the Master Plan

### 4.1 New Feature Row: One-Click Health Fix from Alert

Add under #17 Push Alerts or as a new sub-feature:

```
||| **17b** | **Action Buttons in Push Notifications** — Telegram inline keyboards (restart/cooldown/trim), Discord buttons, webhook action URLs. Calls `/api/heal-action/{agent}/{action}`. Requires heal system `_execute_action()` (already built) + push alert infra (already built). | **Alerts** | 🔴 Planned | ❌ Pro | ✅ Same | ~4h | observeco-master-plan.md §3.17 |
```

### 4.2 New Feature Row: Agent Health Report Card

Add as a new feature in the Runtime Health section:

```
||| **64** | **Agent Health Report Card** — weekly digest via push alert. Aggregates 7d of: pulse uptime %, auto-heal count, circuit trips, compressions, token cost. One SQL query per metric, one Jinja2 template. All data exists in pulse_log, heal_events, circuit_events, compress_log, token_logs. | **Alerts** | 🔴 Planned | ✅ Weekly digest in dashboard | ✅ Push delivery + trend comparison | ~3h | observeco-master-plan.md §3.64 |
```

### 4.3 Status Fixes

1. **#15 Auto-Heal**: Change feature table status from "✅ Live" to "✅ Backend / ❌ Dashboard UI" to match deep-dive §3.15. Update Free column from "✅ manual Heal button + dashboard alerts + L2 trends" to "✅ manual Heal button + dashboard alerts + L2 trends / ❌ Dashboard config UI".

2. **#17 Push Alerts**: Change feature table status from "✅ Live" to "✅ Backend (Telegram/webhook/email) / 🔴 Discord / ❌ Dashboard UI" to match deep-dive §3.17. Update Free column from "✅ All channels + delivery log" to "✅ Backend delivery / ❌ Dashboard subscription UI".

3. **#22 Agent Health Detection Engine**: Change Free column from "✅ All (detection + health — core infra for everything)" to "✅ Layers 1-2 only (process health, OTel, cross-framework)".

### 4.4 Deep-Dive Additions

1. **§3.8 In-Dashboard Alerts**: Add full RDR with:
   - State matrix: loading, empty (no alerts), error (data source unreachable), partial (some alert types unavailable), stale (last check >5min)
   - Lifecycle: Start (no alerts yet → "Alerts will appear as events are detected"), Run (continuous accumulation), Crash (last N alerts cached in DB), Reboot (resume from DB)
   - Success metrics: alert display latency <500ms from event to dashboard, zero alerts lost on crash
   - Constraints register: cross-platform (same SQLite backend), multi-instance (instance_id in alert_log)

2. **§3.2 Pulse Check**: Add:
   - Success metrics: detection latency <35s (within 2 cycles), data freshness <60s, false positive rate <1%
   - Lifecycle: Start (no data → "Collecting pulses..."), Crash (daemon restart → resume from last pulse), Cleanup (prune pulses >7d free, >90d pro)
   - Constraints register: Windows process detection (tasklist/Get-Process), multi-instance (instance_id in pulse_log)

3. **§3.3 Safety Guard**: Add:
   - Success metrics: guard trips within 3 consecutive failures, cooldown accuracy ±10%, zero false trips on healthy agents
   - Lifecycle: Start (no failures → "✅ Guard OK"), Crash (HealCircuit resets in-memory → guard state lost), Reboot (fresh start, no stale cooldowns)
   - Constraints register: HealCircuit is in-memory (resets on daemon restart), cross-platform signal handling

### 4.5 Cross-Reference Verification

Add a cross-reference verification note confirming that:
- §3.15 (Auto-Heal) and feature table row for #15 agree on status
- §3.17 (Push Alerts) and feature table row for #17 agree on status
- §14.3 (G1/G2/G3) and feature table rows for G1.1-G3.3 agree on status
- §3.59 (Composite Health Score) and feature table row for #59 agree on status
- §3.37 (Anomalies Inbox) and feature table row for #33 agree on status
- §3.43 (Tool Efficiency Ranking) and feature table row for #39 agree on status

---

## 5. Scoring Against Master Fidelity Gate

### Layer A: Requirements Fidelity

| # | Item | Weight | Score | Notes |
|---|------|--------|-------|-------|
| A1 | RDR written and approved | 3 | 2/3 | #2, #3, #8 have no RDR. #15, #17, G1 features have RDRs. |
| A2 | All 6 spec traps checked and clean | 3 | 1/3 | Traps 1-6 have violations across #2, #3, #8, #15, #17. |
| A3 | State matrix with ≥4 states per story | 2 | 1/2 | #8 has no state matrix. #2, #3 have partial state coverage. #15, #17, G1 have good state coverage. |
| A4 | Success metrics defined and measurable | 3 | 0/3 | No Runtime Health feature has quantitative success metrics. |
| A5 | Constraints register filled | 2 | 0/2 | #2, #3, #8 have no constraints register. #15, #17 have partial. |
| A6 | Cross-references verified current | 1 | 0/1 | #15 and #17 have contradictory cross-references between feature table and deep-dive. |
| **Total** | | **14** | **4/14** | **FAIL (threshold ≥11)** |

### Layer D: System-Design Fidelity (Runtime Health subset)

| # | Item | Weight | Score | Notes |
|---|------|--------|-------|-------|
| D1 | Data pipeline map: every table has known writer | 3 | 3/3 | Pulse_log (watch daemon), heal_events (heal module), circuit_events (safety guard), alert_log (push module) all have known writers. |
| D2 | Lifecycle tests all 12 pass | 3 | 1/3 | #2, #3, #8 have no lifecycle specification. #15, #17 have partial. |
| D4 | Heartbeat contract: pid + timestamp + status + cycle | 3 | 3/3 | Watch daemon heartbeat file is well-documented. |
| D6 | Crash resilience: per-agent + per-sweep error isolation | 3 | 2/3 | Heal module has per-agent error isolation. Pulse check has per-agent try/except. But no explicit crash resilience documentation for alert delivery. |
| **Subtotal** | | **12** | **9/12** | **PASS (threshold ≥9 for this subset)** |

---

## 6. Summary

### Critical Issues (must fix before next spec iteration)
1. **F1/F2**: Resolve contradictory status markers for #15 Auto-Heal and #17 Push Alerts between feature table and deep-dive sections.
2. **F3**: Add full state coverage to #8 In-Dashboard Alerts (currently just a value proposition, not a spec).

### High Issues (should fix this sprint)
3. **F4/F5**: Add success metrics to #2 Pulse Check and #3 Safety Guard.
4. **F13**: Add "One-click health fix from alert" feature to master plan (action buttons in push notifications).
5. **F6**: Fix misleading "✅ All" claim in #22 Agent Health Detection Engine Free column.

### Medium Issues (fix when touching these sections)
6. **F7/F8/F9**: Add lifecycle specification to #2, #3, #8.
7. **F10**: Add success metrics to #15 Auto-Heal and #17 Push Alerts.
8. **F11/F12**: Add constraints register to #2 and #3.
9. **F14**: Add "Agent health report card (weekly digest)" feature to master plan.
10. **F19**: Document Discord gap in #17 Push Alerts feature table.

### Low Issues (documentation only)
11. **F15-F18**: No action needed — N1-N4 are already spec'd in master plan.
12. **F20**: Add cross-reference verification note for G1 features.

### What's Already Good
- **#2 Pulse Check** (§3.2): Excellent scenario table (5 failure modes), clear data pipeline, well-defined consumers.
- **#3 Safety Guard** (§3.3): Excellent value calculation (DB growth math), clear scenario table, well-defined consumers.
- **#7 Heal Button** (§3.7): Clear implementation pattern (HealProposal pattern), well-documented HealCircuit, explicit auto-restart opt-in.
- **#15 Auto-Heal** (§3.15): Comprehensive state table (8 states), clear tier comparison, well-defined ACs.
- **#17 Push Alerts** (§3.17): Comprehensive state table (8 states), clear tier comparison, well-defined ACs.
- **G1.1-G1.6** (§14.3): Detailed ACs, state tables, architecture decisions, pre-mortem analysis.
- **#33 Anomalies Inbox** (§3.37): Full RDR with 8 states, 8 lifecycle items, 10 anomaly types, data pipeline diagram.
- **#39 Tool Efficiency Ranking** (§3.43): Full RDR with 8 states, 8 lifecycle items, cross-reference verification, state matrix, constraints register.
- **#59 Composite Health Score** (§3.59): Clear scoring formula, dashboard display spec, alert thresholds, constraints register, success metrics.
