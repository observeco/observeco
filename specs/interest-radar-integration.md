# ObserveCo × Interest Radar — Integration Spec

## Status: v0.1 DRAFT (2026-05-25)
## Owner: Main → Pragma (v1.1 implementation)

---

## Problem

ObserveCo's pulse/drift/self-heal pipeline produces signals on a regular cadence. Without relevance filtering, every signal hits the user with equal priority. Most signals are noise — the user only cares about alerts that relate to what they're currently building.

Interest Radar solves this: every alert gets a relevance score before reaching the user.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        ObserveCo Pipeline                           │
│                                                                     │
│  Pulse Check →  Drift Detection →  Circuit Breaker →  Self-Heal   │
│       │               │                  │              │          │
│       └───────────────┴──────────────────┴──────────────┘          │
│                               │                                     │
│                               ▼                                     │
│                    ┌─────────────────────┐                          │
│                    │  Interest Radar     │                          │
│                    │  batch_judge()      │                          │
│                    └────────┬────────────┘                          │
│                             │                                        │
│                    ┌────────▼────────┐                               │
│                    │  Relevance       │                              │
│                    │  Score > 80?    │                              │
│                    └───┬────────┬────┘                               │
│                   YES  │        │  NO                                │
│                        ▼        ▼                                    │
│                ┌──────────┐  ┌──────────┐                           │
│                │  PUSH    │  │  SILENT  │                           │
│                │  alert   │  │  log only│                           │
│                └──────────┘  └──────────┘                           │
└─────────────────────────────────────────────────────────────────────┘

                        Feedback Loop
                  ┌─── user: 👍 / 👎 ────┐
                  │                       │
                  ▼                       ▼
           update snapshot weight   lower future score
```

---

## Integration Points

### Point 1: Pulse Alert (highest priority)

**Current:** `observeco pulse check` returns health data. When anomaly detected → writes to stdout/log.

**With Radar:** After anomaly detection and BEFORE alert dispatch, pass alert metadata through `batch_judge`:
```python
alert = {
    "title": f"Drift detected: {agent_name} accuracy dropped {delta_pct}%",
    "event_type": "drift_alert",
    "source": f"observeco/{agent_name}"
}
score = interest_radar_batch_judge([alert])
if score >= 80:
    dispatch_alert(alert)  # push to user
elif score >= 60:
    log_alert(alert)       # store, no push
else:
    suppress(alert)         # ignore
```

### Point 2: Circuit Breaker Trip

**Current:** `observeco pulse circuit` trips when consecutive failure threshold exceeded. Writes event to state.

**With Radar:** Circuit breaker trips always dispatch (safety-critical) BUT the alert message includes a relevance justification:
```
🚨 Circuit tripped on [agent]
📡 Relevance: This agent powers [project_name] — action required
```

### Point 3: Self-Heal Log

**Current:** `observeco heal` runs and logs what it attempted.

**With Radar:** After heal runs, pass the heal log through batch_judge. If the affected agent maps to a high-weight project, surface a summary to the user. Otherwise, log silently.

---

## Feedback Loop UI

### What the User Sees

```
🚨 Drift detected: hermes-main accuracy dropped 12% in 24h
📡 High relevance — powers: ObserveCo, Hermes Ecosystem
   Is this relevant? [👍 yes] [👎 no]
```

### Backend Behavior

| Action | Effect |
|--------|--------|
| User clicks **👍** | Increases keyword weights for matching interests in snapshot. "confirm" → snapshot JSON updated. |
| User clicks **👎** | Decreases keyword weights for matching interests. "dismiss" → snapshot JSON updated. |
| User ignores | Alert expires. No weight change. |

### Storage

Feedback stored in `~/.hermes/radar-cache/feedback_log.json`:
```json
{
  "entries": [
    {
      "timestamp": "2026-05-25T08:00:00+08:00",
      "alert_type": "drift",
      "agent": "hermes-main",
      "score_at_time": 92,
      "user_feedback": "confirm",
      "interests_hit": ["Agent Observability", "ObserveCo"]
    }
  ]
}
```

---

## Implementation Plan

| Phase | What | Effort | Depends On |
|-------|------|--------|------------|
| **v0.1** | Add `--radar` flag to `observeco pulse check` that calls batch_judge after detection | 2-3h | Existing interest-radar skill |
| **v0.2** | Wire batch_judge into drift detection cron (before alert dispatch) | 1-2h | v0.1 approval |
| **v0.3** | Feedback UI — 👍/👎 buttons in alert messages, write to feedback_log | 3-4h | v0.2 |
| **v0.4** | Auto-update interest snapshot from feedback_log (periodic cron) | 1h | v0.3 |

---

## Open Questions

1. **Should circuit breaker alerts bypass radar?** — Recommending YES (safety override). Radar is advisory for circuit trips, not a gate.
2. **Snapshot staleness** — If user's interests change, the snapshot needs a refresh mechanism. Current TTL is 6h. For ObserveCo, consider 24h.
3. **Multi-user** — v1.1 consideration. The interest snapshot is currently single-user. Multi-user would need per-user snapshots.

---

## Appendix: CLI Integration Sketch

```bash
# Check with relevance filtering
observeco pulse check --radar

# Output with radar score
Agent: hermes-main | Status: DRIFT (+12% error over 24h)
📡 Relevance: 92/100 — matches "Agent Observability", "ObserveCo"

# Skip radar (default fast path)
observeco pulse check
```
