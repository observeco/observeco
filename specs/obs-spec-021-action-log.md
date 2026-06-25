# obs-spec-021: Unified Action Log

**Spec ID:** obs-spec-021
**Status:** DRAFT v2
**Author:** Pragma
**Date:** 2026-06-11
**Phase:** 3 (World Class)
**Priority:** P0
**Owner:** Pragma
**Changelog:** v2 — Resolved open questions (per-skill logging, no_action), added Free vs Pro tier gating, added empty/loading/error states, added success metrics, fixed §3.2 vs §5.2 contradiction.

---

## 1. Problem

Every ObserveCo feature that performs an action (compression, healing, drift detection, config fixes, skill compression) logs to its own siloed table. Brain Analysis and Skills Audit have no visibility into what ObserveCo has actually *done* for the user. The user sees dashboards that look static — no proof of value, no history of benefit.

**Sean's direction:** "For every feature where we have real estate that performs actions through observeco, we should capture and display all historical logs. This would massively help brain analysis and skills audit to provide context to users they have already benefited from observeco."

**v2 additions:** Per-skill granularity for skill compression. Log `no_action` results so users see the system checked and found nothing to do. Free vs Pro tier gating with exact display content.

## 2. Existing Siloed Logs

| Table | Feature | Columns | Rows (est.) |
|-------|---------|---------|-------------|
| `compress_log` | Chisel compression | agent_name, mode, before/after_tokens, savings, savings_pct, backup_path, triggered_by, timestamp | 2-10 |
| `heal_events` | Auto-heal L1/L2 | agent_name, event_type, status, duration_ms, details, created_at | 0-50 |
| `restart_log` | Gateway restarts | agent_name, reason, timestamp | 0-20 |
| `alert_log` | Push alerts | channel, target, event_type, message, delivered, delivery_error, created_at | 0-100 |
| `agent_kill_log` | Agent kills | agent_name, reason, killed_by, created_at | 0-10 |
| `chisel_drift` | Token drift tracking | agent_name, component, delta_pct, breached, week_avg_tokens, current_tokens | 0-50 |

**The gap:** No unified query. Brain Analysis can't say "ObserveCo saved you X tokens this month across Y compression runs." Skills Audit can't say "3 skills were compressed, saving Z tokens." The data exists in 6 tables but nobody joins it.

## 3. Solution: Unified `action_log` Table

A single append-only table that captures every meaningful action ObserveCo performs. Each row is one action — one compression run, one heal event, one skill compression, one config fix.

### 3.1 Schema (Migration 18 — note: obs-spec-020 also claims Migration 18; coordinate to use Migration 19 if 020 ships first)

```sql
CREATE TABLE IF NOT EXISTS action_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_name TEXT NOT NULL,
    action_type TEXT NOT NULL,       -- 'compress', 'heal', 'restart', 'alert', 'drift_detect', 'config_fix', 'skill_compress'
    action_detail TEXT NOT NULL,     -- human-readable: "Lite compression: 1200 → 840 tok (-30%)"
    tokens_saved INTEGER DEFAULT 0,  -- tokens saved (0 if not applicable or no_action)
    cost_saved REAL DEFAULT 0.0,     -- estimated $ saved (0 if not applicable)
    status TEXT NOT NULL DEFAULT 'success',  -- 'success', 'failure', 'skipped', 'no_action'
    metadata TEXT DEFAULT '{}',      -- JSON: extra context (before_tokens, after_tokens, mode, etc.)
    triggered_by TEXT DEFAULT 'daemon',  -- 'daemon', 'dashboard', 'cli', 'session_start', 'watchdog'
    created_at INTEGER NOT NULL      -- Unix timestamp
);
CREATE INDEX IF NOT EXISTS idx_action_log_agent ON action_log(agent_name, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_action_log_type ON action_log(action_type, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_action_log_ts ON action_log(created_at DESC);
-- ponytail: UNIQUE index on (agent_name, action_type, created_at, action_detail) drops
-- legitimate distinct actions in the same second. Upgrade path: use a UUID batch_id
-- in metadata for dedup, or widen to (agent_name, action_type, created_at, action_detail, id).
-- For now, the risk is low (same agent, same type, same second, same detail is rare).
CREATE UNIQUE INDEX IF NOT EXISTS idx_action_log_unique ON action_log(agent_name, action_type, created_at, action_detail);
```

### 3.2 Action Types

| `action_type` | Source | Granularity | What Gets Logged | `tokens_saved` | `cost_saved` |
|---------------|--------|-------------|------------------|----------------|-------------|
| `compress` | `trim.py` | Per agent | Every SOUL.md compression run (one row per agent per run) | `savings` | estimated from savings × pricing |
| `skill_compress` | `skill_compress.py` | **Per skill** | Every individual skill file — compressed or already condensed | `original - compressed` or 0 | estimated or 0 |
| `heal` | `heal/engine.py` | Per event | Every L1 restart, L2 trim, circuit reset | 0 | 0 |
| `restart` | `restart_log` | Per event | Gateway restarts | 0 | 0 |
| `alert` | `alert_log` | Per delivery | Push alerts delivered | 0 | 0 |
| `drift_detect` | `chisel_drift` | Per detection | When drift exceeds threshold | 0 | 0 |
| `config_fix` | `config-health.py` | Per fix | Config hygiene auto-fixes applied | 0 | 0 |

### 3.3 Per-Skill Logging for `skill_compress`

**Decision (v2):** Per-skill, not aggregate. Each skill gets its own row.

**Rationale:** Per-skill logging lets the UI show "3 skills compressed, 2 already condensed" — meaningful context the user can act on. Aggregate would hide which skills are already tight vs which still have room.

**When a batch compression runs over N skills:**
- N rows are inserted into `action_log`, one per skill
- Each row has its own `status`: `"success"` (compressed) or `"no_action"` (already condensed)
- The `metadata` JSON carries batch context: `{"batch_id": "<uuid>", "batch_total_skills": N, "batch_index": i}`

**Example:** Batch runs over 5 skills — chisel-compression (no_action), dreamer-walk (success), commitment-capture (success), hermes-agent (no_action), news-monitoring (success):

```
Row 1: agent="fleet", action_type="skill_compress", action_detail="chisel-compression — already condensed (no further savings)", status="no_action"
Row 2: agent="fleet", action_type="skill_compress", action_detail="dreamer-walk — compressed 1,800 → 1,620 tok (-10%)", status="success"
Row 3: agent="fleet", action_type="skill_compress", action_detail="commitment-capture — compressed 900 → 840 tok (-7%)", status="success"
Row 4: agent="fleet", action_type="skill_compress", action_detail="hermes-agent — already condensed (no further savings)", status="no_action"
Row 5: agent="fleet", action_type="skill_compress", action_detail="news-monitoring — compressed 2,100 → 1,890 tok (-10%)", status="success"
```

### 3.4 `no_action` Logging

**Decision (v2):** Log `no_action` results. When compression runs but finds savings ≤5% (the "already condensed" threshold), insert a row with `status="no_action"`.

**Rationale:** The user needs to see that ObserveCo *checked* and found nothing to do. This is the "already condensed" UX — honest reporting that the system evaluated the content and found it already tight.

**What the user sees:**
- `status="success"` → "compressed 1,800 → 1,620 tok (-10%)" with token/cost savings
- `status="no_action"` → "already condensed (no further savings)" with 0 tokens/cost

**Where `no_action` applies:**
| Action Type | When `no_action` Fires |
|-------------|----------------------|
| `compress` | Compression run yields ≤5% savings (SOUL.md already tight) |
| `skill_compress` | Individual skill yields ≤5% savings |
| `heal` | Never — heal events are always success/failure (they restart or trim, there's no "nothing to do") |
| `config_fix` | Never — config fixes are always applied or skipped |

### 3.5 `action_detail` Format

Every `action_detail` is a pre-formatted human-readable string. No formatting needed at display time.

```
# Compression
"Lite compression: 1,200 → 840 tok (-30%)"
"Full compression: 1,200 → 600 tok (-50%)"
"SOUL.md compression — already condensed (no further savings)"

# Skill Compression (per-skill)
"dreamer-walk — compressed 1,800 → 1,620 tok (-10%)"
"chisel-compression — already condensed (no further savings)"

# Healing
"L1 restart: agent hound restarted (pool timeout)"
"L2 trim: guidance block compressed (1200 → 840 tok)"
"Circuit breaker reset: hound (error rate dropped below threshold)"

# Drift
"Drift detected: hound/skills +12% (1,100 → 1,232 tok)"
"Drift threshold breached: hound/guidance +25%"

# Config
"Config fix: prompt_caching.cache_ttl raised from 5m to 30m"
"Config fix: duplicate reasoning_standards removed from telegram topic"
```

## 4. API Endpoints

### 4.1 `GET /api/action-log`

Returns recent actions with optional filters.

**Query params:**
- `agent` — filter by agent name (default: "all")
- `type` — filter by action_type (default: "all")
- `status` — filter by status (default: "all", options: "success", "no_action", "failure")
- `limit` — max rows (default: 50, max: 200)
- `since` — Unix timestamp (default: all time)

**Response:**
```json
{
  "actions": [
    {
      "id": 1,
      "agent_name": "hound",
      "action_type": "compress",
      "action_detail": "Lite compression: 1,200 → 840 tok (-30%)",
      "tokens_saved": 360,
      "cost_saved": 0.000054,
      "status": "success",
      "triggered_by": "daemon",
      "created_at": 1718100000
    },
    {
      "id": 2,
      "agent_name": "fleet",
      "action_type": "skill_compress",
      "action_detail": "dreamer-walk — compressed 1,800 → 1,620 tok (-10%)",
      "tokens_saved": 180,
      "cost_saved": 0.000027,
      "status": "success",
      "triggered_by": "cli",
      "created_at": 1718100100
    },
    {
      "id": 3,
      "agent_name": "fleet",
      "action_type": "skill_compress",
      "action_detail": "chisel-compression — already condensed (no further savings)",
      "tokens_saved": 0,
      "cost_saved": 0,
      "status": "no_action",
      "triggered_by": "cli",
      "created_at": 1718100100
    }
  ],
  "summary": {
    "total_actions": 47,
    "total_tokens_saved": 12400,
    "total_cost_saved": 0.00186,
    "by_type": {
      "compress": {"count": 12, "tokens_saved": 8400},
      "heal": {"count": 5, "tokens_saved": 0},
      "skill_compress": {"count": 18, "tokens_saved": 4000, "no_action": 8}
    },
    "by_agent": {
      "hound": {"count": 20, "tokens_saved": 6200},
      "pragma": {"count": 15, "tokens_saved": 3100}
    },
    "by_status": {
      "success": 39,
      "no_action": 6,
      "failure": 2
    }
  }
}
```

### 4.2 `GET /api/action-log/cumulative`

Returns cumulative savings over time — the "what has ObserveCo done for me" endpoint.

**Response:**
```json
{
  "period": "all_time",
  "total_tokens_saved": 12400,
  "total_cost_saved": 0.00186,
  "total_actions": 47,
  "actions_by_day": [
    {"date": "2026-06-01", "tokens_saved": 1200, "actions": 3},
    {"date": "2026-06-02", "tokens_saved": 800, "actions": 2}
  ],
  "best_action": {
    "agent_name": "hound",
    "action_detail": "Full compression: 1,200 → 600 tok (-50%)",
    "tokens_saved": 600
  }
}
```

### 4.3 `GET /api/action-log/skill-summary`

Returns per-skill compression summary — the "how are my skills doing" endpoint.

**Response:**
```json
{
  "skills": [
    {
      "skill_name": "dreamer-walk",
      "last_action": "compressed 1,800 → 1,620 tok (-10%)",
      "last_status": "success",
      "total_runs": 3,
      "total_saved": 540,
      "last_run_at": 1718100100
    },
    {
      "skill_name": "chisel-compression",
      "last_action": "already condensed (no further savings)",
      "last_status": "no_action",
      "total_runs": 3,
      "total_saved": 0,
      "last_run_at": 1718100100
    }
  ],
  "batch_summary": {
    "total_skills": 12,
    "compressed": 7,
    "already_condensed": 5,
    "last_batch_at": 1718100100
  }
}
```

## 5. Dashboard Integration — Free vs Pro

### 5.1 Tier Gating Rules

**Free tier** (no active license): All action log dashboard sections show upsell banners. No data is fetched or displayed.

**Pro tier** (active license): Full data displayed. No upsell.

**License check:** `from observeco import license; is_pro = license.require_pro()` — same pattern as Push Alerts and other Pro-gated features.

### 5.2 Brain Analysis — "What ObserveCo Has Done For You" Card

**Location:** Top of Brain Analysis tab, above the token breakdown.

#### Pro (active license):
```
┌─────────────────────────────────────────────────────┐
│  📈 Your ObserveCo Impact                          │
│                                                     │
│  12,400 tokens saved across 47 actions              │
│  $0.0019 estimated cost savings                     │
│                                                     │
│  Last action: Lite compression on hound (2h ago)    │
│                                                     │
│  Breakdown:                                         │
│  • 39 successful actions                            │
│  • 6 checks found content already condensed         │
│  • 2 actions failed                                 │
│                                                     │
│  [View Full History →]                              │
└─────────────────────────────────────────────────────┘
```

**Data source:** `GET /api/action-log/cumulative` + `GET /api/action-log?status=no_action&limit=0` for count.

**Empty state (zero actions):**
```
┌─────────────────────────────────────────────────────┐
│  📈 Your ObserveCo Impact                          │
│                                                     │
│  No actions recorded yet                            │
│                                                     │
│  ObserveCo will log actions automatically as it     │
│  monitors your agents — compression runs, heals,    │
│  drift checks, and config fixes.                    │
│                                                     │
│  Run a compression to start:                        │
│  > observeco chisel --agent all                     │
└─────────────────────────────────────────────────────┘
```

#### Free (no license):
```
┌─────────────────────────────────────────────────────┐
│  📈 Your ObserveCo Impact                          │
│                                                     │
│  🔒 Action history is a Pro feature                 │
│                                                     │
│  See every compression, heal, and fix ObserveCo     │
│  performs — with token savings and cost estimates.   │
│                                                     │
│  [Upgrade to Pro →]                                 │
└─────────────────────────────────────────────────────┘
```

**Upsell button:** Links to `/api/checkout?plan=pro` (dynamic endpoint, not hardcoded URL — per UX trap 23).

### 5.3 Skills Audit — Compression History

**Location:** Inside the Compression Preview section, below the savings cards.

#### Pro (active license):

**Populated state:**
```
┌─────────────────────────────────────────────────────┐
│  📋 Compression History                             │
│                                                     │
│  Last batch: 3 compressed · 2 already condensed     │
│  4,000 tok saved across 18 skill compressions       │
│                                                     │
│  Per-skill breakdown:                               │
│  ✅ dreamer-walk — 1,800 → 1,620 (-10%)            │
│  ✅ commitment-capture — 900 → 840 (-7%)           │
│  ✅ news-monitoring — 2,100 → 1,890 (-10%)         │
│  ⚪ chisel-compression — already condensed          │
│  ⚪ hermes-agent — already condensed                │
│                                                     │
│  [View All History →]                               │
└─────────────────────────────────────────────────────┘
```

**Data source:** `GET /api/action-log/skill-summary`

**Empty state (no compression runs):**
```
┌─────────────────────────────────────────────────────┐
│  📋 Compression History                             │
│                                                     │
│  No compression runs yet                            │
│                                                     │
│  Run skill compression to start saving tokens:      │
│  > observeco chisel --skills                        │
│                                                     │
│  Once compressed, you'll see per-skill breakdowns   │
│  and savings history here.                          │
└─────────────────────────────────────────────────────┘
```

#### Free (no license):
```
┌─────────────────────────────────────────────────────┐
│  📋 Compression History                             │
│                                                     │
│  🔒 Compression history is a Pro feature             │
│                                                     │
│  Track which skills have been compressed, how much  │
│  was saved, and which are already optimized.         │
│                                                     │
│  [Upgrade to Pro →]                                 │
└─────────────────────────────────────────────────────┘
```

### 5.4 Token Optimiser — Activity Feed

**Location:** Replace the current "Recent Compressions" section (lines 2064-2068 in index.html).

#### Pro (active license):

**Populated state:**
```
┌─────────────────────────────────────────────────────┐
│  🕐 Recent Activity                                │
│                                                     │
│  dreamer-walk — compressed 1,800 → 1,620 (-10%)    │
│  3m ago                                             │
│                                                     │
│  hound — L1 restart (pool timeout)                  │
│  1h ago                                             │
│                                                     │
│  chisel-compression — already condensed             │
│  2h ago                                             │
│                                                     │
│  hound — drift detected +12%                        │
│  3h ago                                             │
│                                                     │
│  fleet — config fix: cache_ttl raised 5m → 30m     │
│  1d ago                                             │
└─────────────────────────────────────────────────────┘
```

**Data source:** `GET /api/action-log?limit=5`

**Empty state (no actions):**
```
┌─────────────────────────────────────────────────────┐
│  🕐 Recent Activity                                │
│                                                     │
│  No actions yet                                     │
│                                                     │
│  ObserveCo actions will appear here as they happen  │
│  — compression runs, heals, drift checks, and more. │
└─────────────────────────────────────────────────────┘
```

#### Free (no license):
```
┌─────────────────────────────────────────────────────┐
│  🕐 Recent Activity                                │
│                                                     │
│  🔒 Activity history is a Pro feature                │
│                                                     │
│  See a live feed of every action ObserveCo performs  │
│  — with timestamps and token savings.               │
│                                                     │
│  [Upgrade to Pro →]                                 │
└─────────────────────────────────────────────────────┘
```

## 6. Logging Integration Points

### 6.1 Compression (`trim.py` — `run_compress()`)

After `run_compress()` returns, log to `action_log`:

```python
# In trim.py run_compress(), after result is returned:
from observeco.db import Database
db = Database()
savings_pct = result.get("savings_pct", 0)
db.log_action(
    agent_name=result["agent"],
    action_type="compress",
    action_detail=f"SOUL.md compression — already condensed (no further savings)" if savings_pct <= 5
                 else f"{result['mode'].capitalize()} compression: {result['before_tokens']:,} → {result['after_tokens']:,} tok ({savings_pct:+.1f}%)",
    tokens_saved=result["savings"] if savings_pct > 5 else 0,
    cost_saved=_estimate_cost(result["savings"]) if savings_pct > 5 else 0,
    status="no_action" if savings_pct <= 5 else "success",
    metadata=json.dumps({"mode": result["mode"], "before": result["before_tokens"], "after": result["after_tokens"], "savings_pct": savings_pct}),
    triggered_by="dashboard"
)
```

### 6.2 Healing (`heal_events` — after each heal)

After `heal_events` INSERT, also log to `action_log`:

```python
db.log_action(
    agent_name=agent_name,
    action_type="heal",
    action_detail=f"{event_type}: {details}",
    tokens_saved=0,
    cost_saved=0,
    status=status,
    metadata=json.dumps({"event_type": event_type, "duration_ms": duration_ms}),
    triggered_by="daemon"
)
```

### 6.3 Skill Compression (`skill_compress.py`) — Per-Skill

After batch compression completes, log ONE ROW PER SKILL:

```python
from observeco.db import Database
import uuid
db = Database()
batch_id = str(uuid.uuid4())[:8]

for i, manifest in enumerate(manifests):
    skill_name = manifest["name"]
    original = manifest["original_tokens"]
    compressed = manifest.get("compressed_tokens", original)
    savings_pct = ((original - compressed) / original * 100) if original > 0 else 0

    if manifest.get("compressed") and savings_pct > 5:
        # Skill was compressed
        db.log_action(
            agent_name="fleet",
            action_type="skill_compress",
            action_detail=f"{skill_name} — compressed {original:,} → {compressed:,} tok ({savings_pct:.0f}%)",
            tokens_saved=original - compressed,
            cost_saved=_estimate_cost(original - compressed),
            status="success",
            metadata=json.dumps({"batch_id": batch_id, "batch_total_skills": len(manifests), "batch_index": i}),
            triggered_by="cli"
        )
    else:
        # Skill already condensed — still log it
        db.log_action(
            agent_name="fleet",
            action_type="skill_compress",
            action_detail=f"{skill_name} — already condensed (no further savings)",
            tokens_saved=0,
            cost_saved=0,
            status="no_action",
            metadata=json.dumps({"batch_id": batch_id, "batch_total_skills": len(manifests), "batch_index": i, "savings_pct": savings_pct}),
            triggered_by="cli"
        )
```

### 6.4 Config Fixes (`config-health` — after `--fix`)

```python
db.log_action(
    agent_name="fleet",
    action_type="config_fix",
    action_detail=f"Config fix: {fix_description}",
    tokens_saved=tokens_recovered,  # 0 if unknown
    cost_saved=0,
    status="success",
    metadata=json.dumps({"check": check_name, "before": before_value, "after": after_value}),
    triggered_by="dashboard"
)
```

## 7. Cost Estimation Helper

```python
def _estimate_cost(tokens_saved: int) -> float:
    """Estimate $ saved from tokens saved. Uses DeepSeek V3 pricing as baseline.
    Shown as 'estimated' in UI with footnote about pricing basis."""
    COST_PER_1M_TOKENS = 0.15  # DeepSeek V3 input
    return round((tokens_saved / 1_000_000) * COST_PER_1M_TOKENS, 6)
```

## 8. Backfill Strategy

On first run after migration, backfill `action_log` from existing siloed tables:

```python
def backfill_action_log():
    """One-time backfill from existing tables. Safe to re-run (INSERT OR IGNORE)."""
    conn = db._get_conn()

    # compress_log → action_log
    for row in conn.execute("SELECT * FROM compress_log").fetchall():
        savings_pct = row["savings_pct"]
        detail = (f"SOUL.md compression — already condensed (no further savings)" if savings_pct <= 5
                  else f"{row['mode'].capitalize()} compression: {row['before_tokens']:,} → {row['after_tokens']:,} tok ({savings_pct:+.1f}%)")
        conn.execute(
            "INSERT OR IGNORE INTO action_log (agent_name, action_type, action_detail, tokens_saved, cost_saved, status, metadata, triggered_by, created_at) "
            "VALUES (?, 'compress', ?, ?, ?, ?, ?, ?, ?)",
            (row["agent_name"], detail,
             row["savings"] if savings_pct > 5 else 0,
             _estimate_cost(row["savings"]) if savings_pct > 5 else 0,
             "no_action" if savings_pct <= 5 else "success",
             json.dumps({"mode": row["mode"], "savings_pct": savings_pct}),
             row["triggered_by"], row["timestamp"])
        )

    # heal_events → action_log
    for row in conn.execute("SELECT * FROM heal_events").fetchall():
        detail = f"{row['event_type']}: {row['details']}"
        conn.execute(
            "INSERT OR IGNORE INTO action_log (agent_name, action_type, action_detail, tokens_saved, cost_saved, status, metadata, triggered_by, created_at) "
            "VALUES (?, 'heal', ?, 0, 0, ?, ?, 'daemon', ?)",
            (row["agent_name"], detail, row["status"],
             json.dumps({"event_type": row["event_type"], "duration_ms": row["duration_ms"]}),
             row["created_at"])
        )

    # restart_log → action_log
    for row in conn.execute("SELECT * FROM restart_log").fetchall():
        detail = f"Gateway restart: {row['reason']}"
        conn.execute(
            "INSERT OR IGNORE INTO action_log (agent_name, action_type, action_detail, tokens_saved, cost_saved, status, metadata, triggered_by, created_at) "
            "VALUES (?, 'restart', ?, 0, 0, 'success', '{}', 'daemon', ?)",
            (row["agent_name"], detail, row["timestamp"])
        )

    conn.commit()
```

**Key:** Use `INSERT OR IGNORE` with the unique constraint on `(agent_name, action_type, created_at, action_detail)` to make backfill idempotent.

## 9. Retention

Action logs are small (1 row per action, ~200 bytes). Retain for 90 days by default. Configure via `retention_config` table:

```sql
INSERT OR REPLACE INTO retention_config (table_name, retain_days) VALUES ('action_log', 90);
```

The watch daemon's retention sweep should clean old `action_log` rows.

**After 90-day cleanup:** Dashboard gracefully handles missing old data — the "Your ObserveCo Impact" card shows only the current window's stats. No error, no "data gap" warning.

## 10. Migration

**Migration 18:** Creates `action_log` table + indexes + unique constraint for idempotent backfill.

```sql
CREATE TABLE IF NOT EXISTS action_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_name TEXT NOT NULL,
    action_type TEXT NOT NULL,
    action_detail TEXT NOT NULL,
    tokens_saved INTEGER DEFAULT 0,
    cost_saved REAL DEFAULT 0.0,
    status TEXT NOT NULL DEFAULT 'success',
    metadata TEXT DEFAULT '{}',
    triggered_by TEXT DEFAULT 'daemon',
    created_at INTEGER NOT NULL
);
-- ponytail: UNIQUE index on (agent_name, action_type, created_at, action_detail) drops
-- legitimate distinct actions in the same second. Upgrade path: use a UUID batch_id
-- in metadata for dedup, or widen to (agent_name, action_type, created_at, action_detail, id).
-- For now, the risk is low (same agent, same type, same second, same detail is rare).
CREATE UNIQUE INDEX IF NOT EXISTS idx_action_log_unique ON action_log(agent_name, action_type, created_at, action_detail);
CREATE INDEX IF NOT EXISTS idx_action_log_agent ON action_log(agent_name, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_action_log_type ON action_log(action_type, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_action_log_ts ON action_log(created_at DESC);
```

**Backfill:** Runs automatically on first startup after migration. One-time operation.

## 11. Display Convention

### What to Show

| Context | Tier | What | Format |
|---------|------|------|--------|
| Brain Analysis card | Pro | Cumulative impact | "12,400 tokens saved across 47 actions" |
| Brain Analysis card | Pro | Cost savings | "$0.0019 estimated cost savings" |
| Brain Analysis card | Pro | Last action | "Last action: Lite compression on hound (2h ago)" |
| Brain Analysis card | Pro | Status breakdown | "39 successful · 6 already condensed · 2 failed" |
| Brain Analysis card | Free | Upsell | "🔒 Action history is a Pro feature" |
| Skills Audit compression | Pro | Per-skill breakdown | Per-skill with ✅/⚪ status and savings |
| Skills Audit compression | Pro | Batch summary | "3 compressed · 2 already condensed" |
| Skills Audit compression | Free | Upsell | "🔒 Compression history is a Pro feature" |
| Token Optimiser feed | Pro | Recent actions | Last 5 actions, human-readable with timeAgo |
| Token Optimiser feed | Free | Upsell | "🔒 Activity history is a Pro feature" |
| Empty state (all) | Pro | Helpful guidance | Why empty + CLI command to populate |

### What NOT to Show

- Raw SQL rows
- Timestamps without relative context ("2h ago", not "1718100000")
- Actions with 0 tokens saved as "savings" (show as "action completed" or "already condensed" instead)
- Estimated cost when tokens_saved = 0
- Upsell banners to Pro users
- Real data to Free users (upsell only)

### Time Formatting

```javascript
function timeAgo(unixTs) {
  const diff = Math.floor(Date.now() / 1000) - unixTs;
  if (diff < 60) return 'just now';
  if (diff < 3600) return Math.floor(diff / 60) + 'm ago';
  if (diff < 86400) return Math.floor(diff / 3600) + 'h ago';
  if (diff < 604800) return Math.floor(diff / 86400) + 'd ago';
  return new Date(unixTs * 1000).toLocaleDateString();
}
```

### Glossary Hint for Cost Estimates

The cost savings figure is estimated using DeepSeek V3 pricing as a baseline. Add a glossary hint `?` icon next to the cost number:

```python
"action-log-cost": {
    "title": "Cost Savings Estimate",
    "icon": "💰",
    "one_liner": "How the cost savings number is calculated.",
    "detail": """<div class="glossary-detail">
    <strong>Estimation basis:</strong><br>
    • Uses DeepSeek V3 input pricing: $0.15 per 1M tokens<br>
    • Actual savings depend on which model each agent uses<br>
    • Real-world savings may be higher (Claude: $3/1M, GPT-4: $30/1M)<br><br>
    <strong>Formula:</strong><br>
    <code>cost_saved = (tokens_saved / 1,000,000) × $0.15</code><br><br>
    <span style="color:#64748b;">These are conservative estimates. Your actual savings are likely higher.</span>
</div>""",
    "faq": [
        ("Why DeepSeek pricing?", "DeepSeek V3 is the most commonly used model in the ecosystem. Using its pricing gives a conservative baseline — most agents use more expensive models."),
    ],
}
```

## 12. Empty States — Full Matrix

Every dashboard section that consumes action_log data must handle these states:

| State | Trigger | What to Show |
|-------|---------|-------------|
| **Loading** | API call in flight | Skeleton placeholder (2-3 grey bars, pulsing) |
| **Populated** | `actions.length > 0` | Real data per §5 |
| **Empty (fresh install)** | `actions.length === 0` | Helpful guidance + CLI command to populate |
| **Empty (after retention cleanup)** | Old data pruned, recent exists | Show only recent data, no warning |
| **API error** | fetch fails or server down | "Couldn't load action history. Make sure the dashboard server is running." |
| **Free user** | `is_pro === false` | Upsell banner per §5 |

## 13. Success Criteria

### Quantitative

| Metric | Target | Measurement |
|--------|--------|-------------|
| Action log coverage | ≥90% of ObserveCo actions logged | `SELECT action_type, COUNT(*) FROM action_log GROUP BY action_type` — every type in §3.2 must have rows after 7 days of use |
| no_action logging | 100% of compression runs log result | `SELECT status, COUNT(*) FROM action_log WHERE action_type='compress' GROUP BY status` — both success and no_action must appear |
| Per-skill granularity | 100% of skill compression runs log per-skill | `SELECT COUNT(DISTINCT action_detail) FROM action_log WHERE action_type='skill_compress'` — must equal number of skills in batch |
| API response time | <100ms for `/api/action-log?limit=50` | Verified via TestClient timing |
| Backfill idempotency | Re-running backfill produces identical row count | `SELECT COUNT(*) FROM action_log` before and after second backfill run |
| Free upsell visibility | 100% of Free users see upsell in all 3 sections | Manual verification: open Brain Analysis, Skills Audit, Token Optimiser as Free user |
| Pro data visibility | 100% of Pro users see real data in all 3 sections | Manual verification: same 3 tabs as Pro user |

### Qualitative

- [ ] User can answer "What has ObserveCo done for me?" from Brain Analysis alone
- [ ] User can answer "Which skills are already optimized?" from Skills Audit alone
- [ ] Free user understands what they're missing and how to get it
- [ ] Fresh install shows helpful guidance, not blank sections

## 14. Playbook Audit Results

### Requirements Fidelity (6 Traps)

| Trap | Finding | Status |
|------|---------|--------|
| 1. Happy Path Only | Empty states for fresh install, retention cleanup, and API error now specified (§12) | ✅ Closed |
| 2. Visuals Without States | Loading, empty, error, Free/Pro states specified per section (§5, §12) | ✅ Closed |
| 3. Lifecycle Not Specified | Action_log lifecycle: creation → population → 90-day retention → cleanup → graceful degradation (§9, §12) | ✅ Closed |
| 4. No Success Metrics | 7 quantitative metrics defined with measurement methods (§13) | ✅ Closed |
| 5. Hidden Constraints | Fresh install (zero rows), Free user (no data access), retention cleanup (old data gone) all covered | ✅ Closed |
| 6. Contradictory Refs | §3.2 now says per-skill for skill_compress, §5.3 shows per-skill breakdown — consistent | ✅ Closed |

### Coding Fidelity (relevant pitfalls)

| Pitfall | Application |
|---------|-------------|
| 4.5 Empty state omission | Every section has WHY empty, WHEN, WHAT to do (§12) |
| 4.21 Multi-patch spec inconsistency | §3.2, §3.3, §3.4, §5.2, §5.3, §5.4, §6.3 all use consistent terminology ("already condensed", "no_action", per-skill) |
| 4.28 Spec metric mismatch | Cost formula verified: `tokens_saved / 1M × $0.15` — matches code in §7 |
| 4.38 Double-counting | `tokens_saved` and `cost_saved` are independent display columns — cost is derived from tokens_saved, not a separate computation |

### UX Testing (relevant traps)

| Trap | Application |
|------|-------------|
| 5 Empty State Is Helpful | Every empty state includes CLI command and explanation (§12) |
| 19 Mock Data | No mock data — all sections consume real API responses |
| 25 Misleading Data | Cost estimate has glossary hint explaining assumptions (§11) |
| 26 Subscription State Confusion | Free/Pro gating is binary — no trial/cancelled/expired states to confuse |

### System Design (relevant lenses)

| Lens | Application |
|------|-------------|
| 1 Lifecycle Independence | action_log writer (daemon) independent of reader (dashboard) |
| 2 Coverage Completeness | All 7 action types mapped to source tables (§3.2) |
| 3 Crash Resilience | action_log INSERT failure doesn't block the action itself — log is fire-and-forget |
| 6 Startup Grace | Fresh install shows helpful empty state, not broken UI (§12) |

## 15. Related Specs

- `obs-spec-020` — Token Analytics Dashboard (provides the token_logs data model)
- `obs-spec-015` — Auto-Heal (heal_events source)
- `obs-spec-017` — Push Alerts (alert_log source)
- `chisel-compression` skill — Compression engine, compress_log source
- `compression-status-honest-ux` reference — The "already condensed" pattern this spec extends
- **GS-019** — Data & Observability Continuity (schema evolution rules, backup-before-destructive, dashboard state matrix)

---

**Next steps:** Confirm spec → build Migration 18 → build `db.log_action()` → wire compression (§6.1) → wire skill compression per-skill (§6.3) → wire heal (§6.2) → build API endpoints (§4) → build Free/Pro frontend cards (§5) → backfill (§8) → verify against success criteria (§13).
