# obs-spec-090: Alert Escalation Chains

**Status:** 🔴 Spec (2026-07-20) — New
**Product:** ObserveCo (Free + Pro)
**Depends on:** obs-spec-017 (push alerts), existing `alert_subscriptions` table, existing `ack_alert()`, existing `_dispatch_alert()`
**Owner:** Main

---

## §1 Problem

ObserveCo fires alerts (Telegram, webhook, email) but has **no multi-level escalation**. A P1 alert and a P3 alert go to the same channel with the same urgency. There's no:
- L1 → wait N min → L2 (different channel) → wait → L3 (page)
- Suppression windows (don't re-alert within X minutes for same issue)
- On-call scheduling or rotation

**Gap:** The preflight-watchdog we just built is a point solution. Generalize it.

---

## §2 Architecture

### §2.1 Escalation Levels

| Level | Channel | Wait Before Escalate | Example |
|-------|---------|---------------------|---------|
| L1 | Telegram topic | 5 min | "Agent X is down" |
| L2 | Telegram DM + email | 15 min | "Agent X still down after 5min" |
| L3 | SMS / phone (Pro) | 30 min | "Agent X down 30min — critical" |

Each level is configurable per agent and per alert type.

### §2.2 Suppression Windows

```
Same alert type + same agent + within N minutes → suppress
Default: 5 min for warnings, 15 min for errors, 60 min for critical
```

Stored in `alert_subscriptions` table extension:

```sql
ALTER TABLE alert_subscriptions ADD COLUMN suppression_minutes INTEGER DEFAULT 5;
ALTER TABLE alert_subscriptions ADD COLUMN escalation_enabled INTEGER DEFAULT 0;
ALTER TABLE alert_subscriptions ADD COLUMN escalation_levels TEXT DEFAULT '[]';
-- escalation_levels JSON: [{"level": 1, "channel": "telegram", "wait_min": 5},
--                          {"level": 2, "channel": "email", "wait_min": 15}]
```

### §2.3 Escalation Engine

New file: `alerts/escalation.py`

```python
def evaluate_escalation(agent: str, alert_type: str, first_fired_at: int) -> Optional[dict]:
    """Check if an active alert should escalate to the next level.
    
    Returns escalation action dict or None if no escalation needed.
    """
    config = get_escalation_config(agent, alert_type)
    if not config or not config.get("enabled"):
        return None
    
    elapsed = time.time() - first_fired_at
    for level in sorted(config["levels"], key=lambda l: l["level"]):
        if elapsed >= level["wait_min"] * 60 and not _level_already_fired(agent, alert_type, level["level"]):
            return level
    return None
```

### §2.4 Integration with Existing Systems

| System | Integration |
|--------|-------------|
| `alert_delivery_log` | Escalation events logged with `level` field |
| `ack_alert()` | Acknowledging an alert at any level cancels all pending escalations |
| `_dispatch_alert()` | Extended to accept `level` parameter |
| `heal/escalation.py` | Existing LLM escalation becomes L3+ (after human escalation exhausted) |

---

## §3 Implementation

### Phase 1: Backend (~150 lines)

| File | Change |
|------|--------|
| `db.py` | Extend `alert_subscriptions` table with suppression/escalation columns. Add `get_escalation_config()`, `set_escalation_config()`, `log_escalation()`, `get_pending_escalations()` |
| `alerts/escalation.py` | New file: escalation engine, suppression window check, level tracking |
| `watch_consumers.py` | Add escalation tick (every 60s, checks pending alerts for escalation) |

### Phase 2: Dashboard (~50 lines)

| File | Change |
|------|--------|
| `dashboard/server.py` | Add `/api/alert-config/{agent}` endpoint for escalation config |
| `dashboard/templates/` | Escalation config section in alert management surface |

---

## §4 Edge Cases

- **Acknowledged during escalation:** If user acks at L1, L2/L3 never fire
- **Alert resolved before escalation:** If agent recovers during L1→L2 wait, escalation cancelled
- **Multiple alerts same agent:** Only the highest-severity active alert drives escalation
- **Channel unreachable at escalation time:** Log failure, retry at next escalation level
- **No escalation config:** Default to single-level (current behavior — no change)

---

## §5 Pro Gating

- **Free:** L1→L2 escalation (Telegram→email), configurable suppression windows
- **Pro:** L3 (SMS/phone), on-call scheduling, custom escalation chains per agent, escalation history export

---

## §6 Success Criteria

| Metric | Target |
|--------|--------|
| Escalation fires within 30s of configured wait | 95th percentile |
| False escalations (alert resolved before escalation fires) | <1 per week |
| Suppression window accuracy | 100% — no duplicate alerts within window |
