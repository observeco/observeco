# obs-spec-015: Auto-Heal L1/L2

**Status:** Draft 2026-05-28
**Product:** ObserveCo
**Depends on:** obs-dp-007 (error history), existing observation-mode heal

## §1 Problem

The heal system is currently **observation-only** — it detects problems, writes diagnoses to the dashboard, and suggests CLI commands. The user must manually run `observeco heal --diagnose` or click "Run Heal Check Now". There's no auto-execution.

For production fleets (3+ agents), manual healing doesn't scale. By the time a human runs a heal check, the agent has been producing bad output for minutes to hours.

## §2 L1 Scope (Auto-Execute)

| Condition | Detection | Action |
|-----------|-----------|--------|
| Dead agent | No heartbeat > 5m | Restart agent with same config |
| Tripped circuit | `circuit_breakers.tripped = 1` | Reset breaker, restart agent |
| Error state | `pulse_log.status = "error"` for 3+ consecutive | Restart agent |

Safety: max 3 restarts/hour per agent. Exceeded → escalate to human (write critical flag).

## §3 L2 Scope (Proactive)

| Condition | Detection | Action |
|-----------|-----------|--------|
| Drift > 15% | `drift.delta_pct > 15` component | Run `chisel trim` on agent |
| Memory debt > 60 | `garden.memory_debt_score > 60` | Run `clawforge garden --apply` |
| Context > 85% of window | Estimated tokens > 0.85 * limit | Trigger chisel pre-response compaction |

## §4 Safety

- **Heal circuit breaker**: 3 failures in 1h → circuit opens for 4h, critical flag written
- **Snapshot before restart**: Heal pipeline MUST save investigation dump before restart
- **Opt-in only**: Requires `--auto-heal` flag or `auto_heal: true` in config

## §5 Implementation

### CLI
```bash
observeco heal --diagnose       # Current: observe only
observeco heal --auto-heal      # New: execute L1 fixes
observeco heal --auto-heal --l2 # New: execute L1 + L2 fixes
```

### DB: New `heal_config` table
```sql
CREATE TABLE IF NOT EXISTS heal_config (
    agent_name TEXT PRIMARY KEY,
    auto_heal INTEGER DEFAULT 0,
    auto_heal_l2 INTEGER DEFAULT 0,
    max_restarts_per_hour INTEGER DEFAULT 3
);
```

### Dashboard
- New "Auto-Heal" section in agent detail → Memory/health tab
- Shows: `🟢 Auto-heal active (L1)` / `🟡 L1 + L2 active` / `⚪ Manual only`
- Toggle button to enable/disable

## §6 Failure Modes

| Failure | Fallback |
|---------|----------|
| Restart fails with same error | Heal circuit opens, escalation flag |
| Trim fails (agent offline) | Skip trim, return to observation mode |
| DB lock during snapshots | Skip snapshot, proceed with restart |
| Config changed between detection and heal | Re-detect before action |
