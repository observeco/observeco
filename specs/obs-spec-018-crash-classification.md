# ObserveCo — Crash Classification & Restart Quality

**Spec ID:** obs-spec-018
**Author:** Main (per Sean direction 2026-05-28)
**Status:** Draft
**Location:** `specs/obs-spec-018-crash-classification.md`
**Derived from:** Real incident — TOCTOU race in `pragma_acps_watcher.py` caused 6 "daemon crashes" alerts that were actually sub-second KeepAlive restarts with zero data loss.

**Addendum:** This spec has an addendum covering **Job Health** — silent success detection for cron jobs: `specs/obs-spec-018-addendum-job-health.md`

---

## 1. One-Liner

Daemon restarts are normal in agent ecosystems with filesystem-based signal passing. Current monitoring treats every restart as a crash. This feature distinguishes **TOCTOU restarts** (expected, sub-second, zero data loss) from **real crashes** (SIGSEGV, OOM, config errors, persistent failure) — and shows both on a **restart quality timeline** with a rolling false-alarm ratio.

---

## 2. Why

### 2.1 The Problem

- Agent ecosystems using `fswatch`/polling-based signal passing have TOCTOU races: file is consumed between fsnotify notification and `.stat()` call → watcher crashes with `FileNotFoundError` → `launchd` `KeepAlive=true` restarts it in <1s.
- Current monitoring counts these as "6 daemon crashes in 24h" — a false alarm.
- The user feels the system is unreliable when it's operating normally.
- Operator loses trust in alerts. Next real crash gets buried in noise.

### 2.2 What We Learned (Hermes Incident, 2026-05-27)

| Pattern | Count | Real Impact | Recovery |
|---------|-------|-------------|----------|
| TOCTOU race (file consumed between fsnotify and .stat()) | 6 in 24h | Zero — sub-second launchd restart, no data loss | Launchd KeepAlive auto-restores; fix is code change (filter before sort) |
| Gateway connection retries (Telegram token rejection) | 2,544 Tracebacks | Zero — gateway runs fine | Filtered by log exclusion |
| Actual process crash | 0 | — | — |

**Result:** 6 "critical" alerts flagged, 0 actual critical failures.

---

## 3. User Experience

### 3.1 Dashboard — Restart Quality Tab

A new section in the Fleet view showing a **restart quality timeline** per agent.

**Three lanes:**
- 🟢 **Healthy Restart** (launchd KeepAlive, sub-second recovery)
- 🟡 **TOCTOU Race** (file consumed before processing — fixable inefficiency)
- 🔴 **Crash** (SIGSEGV, OOM, config corruption, persistent failure)

**Cards show:**
- Agent name + total restart count in last 24h
- Bar chart: 3-color stacked bar (green / amber / red per restart type)
- "False Alarm Ratio" — crashes labeled as critical that were actually TOCTOU restarts
- Trend arrow: same period yesterday comparison

### 3.2 Restart Detail View

Click an agent → expand shows:
- Timeline of restarts (time, type, duration until recovered)
- Last 3 lines of crash log snippet
- Suggested fix (TOCTOU → code fix suggestion; real crash → ops action)

### 3.3 Alert Behavior

| Restart Type | Alert Severity | Auto-Escalate | User Notified |
|-------------|---------------|---------------|---------------|
| Healthy restart | None (logged only) | Never | No |
| TOCTOU race | Info (logged as inefficiency) | >20 restarts/24h → flag `toctou_race_loop` | No (logged in restart quality view) |
| Real crash | Critical | 3 crashes in 10m → escalate | 🔴 Dashboard alert + push notification |

---

## 4. Data Model

### 4.1 New Table: `restart_log`

Appended to `pulse.db`:

```sql
CREATE TABLE IF NOT EXISTS restart_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_name TEXT NOT NULL,
    restart_type TEXT NOT NULL CHECK(restart_type IN ('healthy', 'toctou', 'crash')),
    duration_ms INTEGER DEFAULT 0,
    crash_log_snippet TEXT,
    evidence TEXT,           -- path to log file + line number
    timestamp INTEGER NOT NULL
);
```

### 4.2 Classification Logic

```python
def classify_restart(crash_log_path: str, exit_code: int, duration_ms: int = 0) -> str:
    """Classify a daemon restart into healthy/TOCTOU/crash.
    
    duration_ms is the time between process exit and next start (from launchd or pulse).
    Defaults to 0 if unavailable — falls back to log-based classification only.
    """
    # 1. launchd exit codes: 0=clean, negative=signal, 256=exited
    if exit_code == 0:
        return "healthy"  # Clean exit, expected restart
    
    # 2. Check crash log content
    log_text = read_last_n_lines(crash_log_path, 20)
    
    if "FileNotFoundError" in log_text and ".stat()" in log_text:
        return "toctou"  # File consumed between notification and stat
    
    if any(sig in log_text for sig in ["SIGSEGV", "SIGKILL", "SIGABRT", "SIGTERM"]):
        return "crash"
    
    if "OutOfMemoryError" in log_text or "MemoryError" in log_text:
        return "crash"  # OOM
    
    if any(pat in log_text for pat in ["config parse error", "ModuleNotFoundError", 
                                         "PermissionError", "FileNotFoundError"]) \
       and "stat()" not in log_text:
        return "crash"  # Real config/code error
    
    # 3. Duration heuristic: TOCTOU restarts are <2s
    if duration_ms < 2000:
        return "healthy"  # Sub-second restart, likely KeepAlive
    
    return "crash"  # Default to crash if unsure
```

### 4.3 Collection Mechanism

Two modes:

**Mode A — Direct (ObserveCo watch daemon watches launchd):**
- Reads `launchctl list` for exit status changes per agent
- On exit status != 0: reads crash log, classifies, writes to `restart_log`

**Mode B — Log scanner (ObserveCo scans agent logs):**
- Parses `~/.hermes/logs/` for restart/crash markers
- Matches against known TOCTOU patterns (currently excluded logs)
- Classifies and writes to `restart_log`

---

## 5. Integration Points

### 5.1 Existing Code That Needs Updates

| Component | Change | Priority |
|-----------|--------|----------|
| `src/observeco/pulse/check.py` | Add `restart_log` write when agent transitions dead→alive | P1 |
| `src/observeco/pulse/circuit.py` | Exclude TOCTOU restarts from circuit breaker failure counting | P1 |
| `src/observeco/db.py` | Add `restart_log` table + CRUD methods | P1 |
| `src/observeco/dashboard/server.py` | Add restart quality endpoint + htmx panel | P1 |
| `src/observeco/heal.py` | In `_diagnose_agent`, check restart_log for TOCTOU pattern before classifying as crash | P2 |
| `src/observeco/snapshot.py` | Add restart quality to snapshot report | P2 |
| `~/.hermes/scripts/trend_threshold.py` | Already patched — exclude `pragma_acps_watcher.log` | ✅ Done |

### 5.2 Dashboard Changes

New `/api/restart-quality` endpoint returning per-agent restart stats. Dashboard renders a **Restarts** column in fleet view + expandable detail. See mockup for wireframe.

---

## 6. Tier

| Feature | Free | Pro |
|---------|------|-----|
| Restart count (last 24h, all types) | ✅ | ✅ |
| Crash vs TOCTOU breakdown | ❌ | ✅ |
| Restart quality timeline per agent | ❌ | ✅ |
| False-alarm ratio trend | ❌ | ✅ |
| Alert on TOCTOU threshold breach | ❌ | ✅ |
| Auto-filter TOCTOU from circuit breaker | ✅ | ✅ |

---

## 7. Estimated Effort

~2-3 days total:
- `db.py` changes + migration: 2h
- `pulse/check.py` restart classification: 4h
- Dashboard endpoint + htmx panel: 6h
- `heal.py` integration: 2h
- Tests + edge cases: 2h
- Mockup / spec review: 1h

---

## 8. Edge Cases

| Scenario | Handling |
|----------|----------|
| No launchd logs available | Fall back to pulse-based detection (agent transitions dead→alive silently) |
| Log file rotated mid-read | Read from backup log or skip cycle |
| Agent runs on Docker (no launchd) | Use container exit codes instead |
| TOCTOU detection false positive | Use multi-signature matching (FileNotFoundError + .stat() + fsnotify pattern) |
| Agent restart takes >2s but is healthy (heavy init) | Relax duration heuristic to 10s for known slow-start agents |
