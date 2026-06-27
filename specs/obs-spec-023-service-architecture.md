# obs-spec-023: Service Architecture

**Spec ID:** obs-spec-023
**Status:** DRAFT (v2.1 — audit fixes applied)
**Author:** Pragma
**Date:** 2026-06-12
**Phase:** 3 (Service Reliability)
**Priority:** P0
**Owner:** Pragma
**Standard:** GS-019 (Data & Observability Continuity)
**Master Plan:** §3, Tasks 3.20-3.25

---

## 1. Requirements Decision Record (RDR)

**Problem:** ObserveCo lacks defined service architecture. Failures invisible, no auto-recovery, no upgrade mechanism.

**Solution:** Tiered service architecture with health monitoring, auto-recovery, and update system.

**Key constraint:** Data must never be lost when dashboard closes. Agent data accumulates locally and syncs on next start.

**Success metric:** OTEL listener auto-restarts within 30s of crash. Dashboard shows real-time health. Users can upgrade with one button click.

**State enumeration:**
- Fresh install → First run → No data yet
- Running → Data flowing → Dashboard open
- Dashboard closed → Agent still running → Data accumulates
- Crash → Auto-restart → Recovery
- Upgrade → Version check → Update → Restart
- **Daemon crash → No auto-restart → Data stops flowing (P0 — not covered)**
- **Startup failure → Raw traceback → User stuck (P0 — not covered)**
- **Stale metric → No per-metric staleness indicator → User can't tell which data is fresh (P0 — not covered)**
- **Disk full → No pre-write check → Data loss (P0 — not covered)**
- **DB corruption → No integrity check → Silent data loss (P0 — not covered)**
- **Daemon silent death → No meta-monitor escalation → Nobody knows (P0 — not covered)**

**Lifecycle coverage:** Start, run, crash, reboot, cleanup, stale detection (all covered in §6-7)

**Cross-reference verification:** Master Plan §3, Tasks 3.20-3.25 ✓

---

## 2. Problem

ObserveCo lacks a defined service architecture. Current behavior:

1. **No minimum viable service definition** — unclear what must run for ObserveCo to function
2. **No health monitoring** — failures are invisible until user notices missing data
3. **No auto-recovery** — crashed components stay down until manual restart
4. **No upgrade mechanism** — users must manually git pull + pip install
5. **Dashboard-centric design** — if dashboard closes, data collection may stop

**Sean's direction:** "Define minimum viable service, health monitoring, auto-recovery, and upgrade mechanism. Build full, not MVP."

---

## 3. Current Architecture

### 3.1 Component Map

```
Current: Everything tied to dashboard

observeco dashboard
    ├── OTEL Listener (port 4318)
    ├── Dashboard (port 8787)
    ├── Watch Daemon (optional)
    └── Update Checker (not implemented)
```

### 3.2 Failure Modes

| Failure | Current behavior | Impact |
|---------|------------------|--------|
| Dashboard closes | OTEL listener stops | Data loss |
| OTEL listener crashes | No restart | Data loss |
| Database locked | Timeout error | Partial data loss |
| Port conflict | Startup fails | User stuck |
| Schema outdated | Migration runs | Silent upgrade |
| **Daemon crashes** | **No auto-restart — data stops flowing** | **Silent data gap (P0)** |
| **Startup with missing deps** | **Raw traceback** | **User stuck with no guidance (P0)** |
| **Single metric goes stale** | **No per-metric staleness indicator** | **User can't tell which data is fresh (P0)** |
| **Disk fills up** | **No pre-write check — write fails** | **Data loss (P0)** |
| **DB corruption** | **No integrity check on startup** | **Silent data loss (P0)** |
| **Daemon stops ticking** | **No meta-monitor escalates** | **Nobody knows (P0)** |

---

## 4. Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Start behavior | Core + Dashboard (Option B) | Separate data collection from visualization |
| Dashboard off | Data accumulates (Option A) | User shouldn't lose data from closing browser |
| Health enforcement | Level 1+2 | Catch real problems, don't overwhelm |
| Dashboard refresh | Auto-refresh | Always current status |
| Auto-recovery | Auto-restart | Reduce manual intervention |
| Update source | GitHub releases | Not on PyPI yet |
| Update frequency | On dashboard load | No background polling |
| Update mechanism | Press button | User controls when to upgrade |

---

## 5. Architecture

### 5.1 Component Tiers

**Tier 1: Core (data collection) — MUST RUN**

| Component | Port | Purpose | Failure impact |
|-----------|------|---------|----------------|
| OTEL Listener | 4318 | Receives traces from agents | No data collected |
| SQLite DB | N/A | Stores all data | No persistence |
| CLI | N/A | User commands | No interaction |
| Proxy Server | 9200 | Captures LLM API calls for exact cost/tool-call tracking | Cost tracking degrades to estimate; agents unaffected (fail-open proxy) |

**Tier 2: Enhanced (visualization + automation) — RECOMMENDED**

| Component | Port | Purpose | Failure impact |
|-----------|------|---------|----------------|
| Web Dashboard | 8787 | Visualization, alerts | Blind (data still collected) |
| Update Checker | N/A | Version notifications | No upgrade prompts |

**Tier 3: Advanced (power users) — OPTIONAL**

| Component | Purpose | Failure impact |
|-----------|---------|----------------|
| Watch Daemon | Auto-heal, compression | No automated fixes |
| Desktop App | Native UI | Use web dashboard |
| SSO/Auth | Multi-user access | Single-user mode |

### 5.2 Service Manager

**New component:** `src/observeco/service.py`

```
observeco service start   → Start OTEL listener + Dashboard
observeco service stop    → Stop all components
observeco service status  → Health check + status
```

**Responsibilities:**
- Start/stop OTEL listener (port 4318)
- Start/stop Dashboard (port 8787)
- Health monitoring (L1 + L2 checks)
- Auto-restart on failure

### 5.3 Data Flow

```
Agent → OTEL Listener (:4318) → SQLite (pulse.db) → Dashboard (:8787)
                                              ↓
                                    Watch Daemon (optional)
```

---

## 6. Constraints Register

### 6.1 Hard Constraints (MUST)

| Constraint | Requirement | Verification |
|------------|-------------|--------------|
| **Cross-platform** | Works on macOS, Linux, Windows | Test on all three before launch |
| **SQLite WAL mode** | Required for concurrent reads/writes | Verify PRAGMA journal_mode=WAL on init |
| **Port availability** | OTEL (4318), Dashboard (8787) | Detect and resolve conflicts |
| **No data loss** | Dashboard close must not lose data | Agent writes to SQLite, dashboard reads |
| **Graceful shutdown** | Flush pending traces, close DB cleanly | SIGTERM handler, 5s timeout |

### 6.2 Soft Constraints (SHOULD)

| Constraint | Requirement | Verification |
|------------|-------------|--------------|
| **Multi-instance** | Only one service manager per machine | PID file lock, prevent duplicate starts |
| **First-time experience** | Clear setup guidance when no data | Dashboard shows setup instructions |
| **Long-running** | 30+ days without restart | Log rotation (7 days), memory monitoring |
| **Resource limits** | CPU <50%, Memory <200MB, FDs <1000 | Health checks include resource monitoring |
| **Offline mode** | Update check fails gracefully | Cache last check, show "Check manually" |

### 6.3 Environment Blindspots

| Environment | Risk | Mitigation |
|-------------|------|------------|
| **Windows** | Process management differs | Use psutil cross-platform API |
| **Docker** | Ports already mapped | Detect container, adjust ports |
| **CI/CD** | No browser for dashboard | CLI-only mode (`observeco status`) |
| **Air-gapped** | No GitHub access | Offline mode, manual update |
| **Multi-user** | Port conflicts | PID file lock, single instance |

---

## 7. Data Continuity (GS-019)

### 7.1 Data Flow Safety

| Component | Write | Read | Backup |
|-----------|-------|------|--------|
| OTEL Listener | SQLite (WAL) | None | Auto on migration |
| Dashboard | None | SQLite | N/A |
| Watch Daemon | SQLite | SQLite | Auto on migration |
| Health Checks | Log files | None | N/A |

### 7.2 Migration Safety

| Step | Action | Verification |
|------|--------|--------------|
| Pre-migration | Backup database | Check backup exists |
| Migration | Run SQL migrations | Verify row counts |
| Post-migration | Verify schema version | Check version matches code |
| Rollback | Restore from backup | Verify data integrity |

### 7.3 Recovery Paths

| Failure | Recovery | User action |
|---------|----------|-------------|
| Dashboard crash | Restart dashboard | None (auto) |
| OTEL listener crash | Auto-restart (3 attempts) | None (auto) |
| Database corruption | Restore from backup | `observeco db restore <backup>` |
| Schema mismatch | Auto-migrate | None (auto) |
| Disk full | Stop data collection | Free disk space |

### 7.4 Data Retention

| Data | Retention | Cleanup |
|------|-----------|---------|
| Pulse logs | 90 days | `purge_old_data()` |
| Action log | 90 days | Retention sweep |
| Health logs | 7 days | Log rotation |
| Backups | 5 maximum | Auto-rotation |

---

## 8. Health System

### 8.1 Health Levels

**Level 1: Operational (is it running?)**

| Check | How to verify | Failure signal |
|-------|---------------|----------------|
| OTEL listener responding | HTTP probe on `:4318/v1/traces` (POST with empty body → 400 = alive) | "Agent cannot send data" |
| Dashboard responding | HTTP probe on :8787 | "Dashboard unavailable" |
| Database writable | INSERT + DELETE test row | "Database locked or corrupt" |
| Port available | Socket bind test | "Port 4318 already in use" |

**Level 2: Functional (is it working?)**

| Check | How to verify | Failure signal |
|-------|---------------|----------------|
| Data flowing | Last OTEL event <5 min | "No data received in 6 minutes" |
| Schema current | Version matches code | "Database upgrade available" |
| Disk healthy | Usage <80% | "Disk 85% full — data collection may stop" |
| Agent configured | OTEL endpoint set | "Agent not sending to ObserveCo" |

### 8.2 Health Status Object

```python
@dataclass
class HealthStatus:
    level1: dict  # Operational status (green/red)
    level2: dict  # Functional status (green/yellow/red)
    overall: str  # "healthy" | "degraded" | "critical"
    last_check: float  # Timestamp
    issues: list[HealthIssue]  # Active issues
```

### 8.3 Health Check Frequency

| Check | Frequency | Auto-recovery |
|-------|-----------|---------------|
| OTEL listener | Every 30s | Auto-restart |
| Dashboard | Every 30s | Show error |
| Database | Every 60s | Wait + retry |
| Data flow | Every 60s | Warning banner |
| Schema version | On startup | Run migration |
| Disk usage | Every 5 min | Stop collection |
| Memory usage | Every 5 min | Alert user |
| CPU usage | Every 5 min | Alert user |

### 8.4 Dashboard UI States

| State | Visual | Trigger |
|-------|--------|---------|
| **Loading** | "Checking system health..." | First dashboard load |
| **Healthy** | "● System healthy" (green) | All L1+L2 checks pass |
| **Degraded** | "● System degraded" (yellow) | L1 pass, L2 fail |
| **Critical** | "● System critical" (red banner) | L1 fail |
| **Stale** | "● Health check delayed" (gray) | Last check >5 min ago |

---

## 9. Auto-Recovery

### 9.1 Recovery Actions

| Failure | Auto-fix | User notification |
|---------|----------|-------------------|
| OTEL listener down | Restart daemon | "Restarted OTEL listener" |
| Database locked | Wait + retry | "Database busy, retrying..." |
| Port conflict | Verify process name matches expected ('observeco', 'otel'), then kill; else alert and skip | "Stopped old ObserveCo process on port 4318" or "Port 4318 in use by unknown process - skipping" |
| Disk full | Stop data collection | "Disk full — data collection paused" |
| Schema mismatch | Run migration | "Database upgraded to v20" |
| Memory >200MB | Alert user | "High memory usage — consider restart" |
| CPU >80% | Alert user | "High CPU usage" |

### 9.2 Recovery Limits

| Condition | Limit | Action |
|-----------|-------|--------|
| Restart attempts | 3 in 5 minutes | Stop auto-restart, alert user |
| Database retry | 5 attempts, 1s backoff | Alert user |
| Port conflict | Kill old process only if name matches expected | Restart service |
| Health check stale | >5 min since last check | Show "stale" status |

### 9.3 Service Manager Lifecycle

| Phase | Action | Verification |
|-------|--------|--------------|
| **Start** | Bind ports, start components | All ports listening |
| **Run** | Monitor health, auto-restart | Health checks pass |
| **Shutdown** | SIGTERM → flush DB → close connections | Clean exit, no data loss |
| **Crash** | PID file cleanup, restart | Service recovers |

---

## 10. Update System

### 10.1 Update Flow

```
Dashboard loads
    ↓
Check GitHub API: GET /repos/observeco/observeco/releases/latest
    ↓
Compare with installed version (observeco.__version__)
    ↓
If newer available:
    Show banner: "Update available: v0.3.0 (you have v0.2.0)"
    Button: "Update now"
    ↓
User clicks "Update"
    ↓
Run: pip install --upgrade 'observeco @ git+https://github.com/observeco/observeco.git@{tag_name}'
    ↓
Restart service
```

### 10.2 Update States

| State | UI | Action |
|-------|----|----|
| Checking | "Checking for updates..." | Wait for API |
| No update | Hidden | None |
| Update available | Banner + button | User decides |
| Downloading | Progress bar | Wait |
| Installing | Progress bar | Wait |
| Restarting | "Restarting..." | Auto |
| Failed | Error message | Show retry button |
| Offline | "Update check failed — no internet" | Manual check link |

### 10.3 Version Comparison

```python
# ponytail: sync httpx.get() — fine for dashboard-load trigger (one call, <5s).
# If the update check becomes a background loop, switch to httpx.AsyncClient.
from packaging.version import parse as parse_version
import httpx
import observeco

def check_for_updates() -> UpdateInfo | None:
    """Check GitHub for latest release."""
    try:
        response = httpx.get(
            "https://api.github.com/repos/observeco/observeco/releases/latest",
            timeout=5.0  # 5 second timeout
        )
        latest = response.json()["tag_name"]
        installed = observeco.__version__
        
        if parse_version(latest) > parse_version(installed):
            return UpdateInfo(
                current=installed,
                latest=latest,
                download_url=response.json()["html_url"]
            )
    except (httpx.TimeoutException, httpx.RequestError):
        logger.warning("Update check failed — network unavailable")
    except (KeyError, ValueError) as e:
        logger.warning(f"Update check failed — unexpected API response: {e}")
    return None
```

### 10.4 Offline Fallback

| Scenario | Behavior |
|----------|----------|
| No internet | Show "Check manually" link to GitHub |
| API timeout | Cache last successful check, show cached result |
| GitHub down | Show "Update service unavailable" |

---

## 11. Minimum Viable Install

### 11.1 First Run Flow

```
User runs: observeco dashboard

1. Check if OTEL port available (4318)
2. Check if Dashboard port available (8787)
3. Initialize SQLite database
4. Start OTEL listener
5. Start Dashboard
6. Show status: "System ready — waiting for agent data"
```

### 11.2 Empty State Handling

| Scenario | Dashboard shows |
|----------|-----------------|
| No data yet | "No data yet — configure your agent to send to ObserveCo" |
| Agent configured | "Waiting for first event from your agent" |
| Data arriving | "Last event: 2 minutes ago — 1,234 events today" |

### 11.3 Setup Guidance

When no data available, show:
- Link to setup documentation
- OTEL endpoint: `localhost:4318`
- Example agent configuration
- "Expected: OTEL traces from your agent"

---

## 12. Communication Channels

### 12.1 Dashboard UI

| Element | Use for | Example |
|---------|---------|---------|
| Status bar | Operational status | "● Connected — 1,234 events today" |
| Banner (red) | Critical issues | "OTEL listener down — no data flowing" |
| Banner (yellow) | Warnings | "Database upgrade available" |
| Banner (green) | Success | "System healthy" |
| Banner (gray) | Stale status | "Health check delayed" |

### 12.2 CLI

| Command | Output |
|---------|--------|
| `observeco status` | Full health check with recommendations |
| `observeco service status` | Service-specific status |

### 12.3 Log Files

| Log | Use for | Rotation |
|-----|---------|----------|
| `~/.observeco/logs/observeco.log` | General application logs | 7 days |
| `~/.observeco/logs/errors.log` | Error-only logs | 30 days |
| `~/.observeco/logs/health.log` | Health check results | 7 days |

---

## 13. Success Criteria

### 13.1 Service Reliability

- [ ] OTEL listener auto-restarts within 30s of crash
- [ ] Dashboard shows real-time health status (auto-refresh every 30s)
- [ ] Database lock handled gracefully (retry + backoff)
- [ ] Port conflicts detected and resolved automatically
- [ ] Data accumulates when dashboard is closed

### 13.2 Health Monitoring

- [ ] Level 1 checks (operational) run every 30s
- [ ] Level 2 checks (functional) run every 60s
- [ ] Health status displayed in dashboard status bar
- [ ] Critical issues shown as red banners
- [ ] `observeco status` shows full health report

### 13.3 Auto-Recovery

- [ ] Failed components auto-restart (max 3 attempts in 5 min)
- [ ] Database lock retried with backoff (5 attempts, 1s intervals)
- [ ] Port conflicts resolved by killing old process
- [ ] Disk full triggers data collection pause
- [ ] Schema mismatches trigger automatic migration

### 13.4 Update System

- [ ] GitHub releases checked on dashboard load
- [ ] "Update available" banner shown when newer version exists
- [ ] "Update" button triggers `pip install --upgrade`
- [ ] Service restarts after successful update
- [ ] Update failure shows error with retry option

### 13.5 User Experience

- [ ] First run shows setup guidance when no data available
- [ ] Empty states managed with clear expectations
- [ ] Health issues include actionable guidance
- [ ] Logs available for debugging

### 13.6 Performance Targets

- [ ] Health API responds in <100ms
- [ ] Dashboard loads in <2s
- [ ] `observeco status` completes in <1s
- [ ] Update check completes in <5s (or timeout)
- [ ] OTEL listener restarts in <30s

### 13.7 Uptime Targets

- [ ] Tier 1 components: 99.9% uptime (8.76 hours downtime/year)
- [ ] Tier 2 components: 99% uptime (3.65 days downtime/year)
- [ ] Data loss: <0.1% (1 event per 1000)

---

## 14. Implementation Plan

### Batch 1: Health System (Foundation)

| # | Task | Files | Verification |
|---|------|-------|--------------|
| 1.1 | Health check engine | `health.py` | Unit tests for each check |
| 1.2 | Health status object | `health.py` | Dataclass tests |
| 1.3 | Health API endpoint | `server.py` | API returns correct status |
| 1.4 | Dashboard status bar | `index.html` | UI shows green/yellow/red |

### Batch 2: Service Manager

| # | Task | Files | Verification |
|---|------|-------|--------------|
| 2.1 | Service start/stop | `service.py` | CLI tests |
| 2.2 | Process management | `service.py` | Start/stop/restart tests |
| 2.3 | Port conflict detection | `service.py` | Kill old process test |
| 2.4 | Auto-restart logic | `service.py` | Crash recovery test |

### Batch 3: Update System

| # | Task | Files | Verification |
|---|------|-------|--------------|
| 3.1 | GitHub API client | `updater.py` | Mock API tests |
| 3.2 | Version comparison | `updater.py` | Semver parsing tests |
| 3.3 | Update API endpoint | `server.py` | API returns update info |
| 3.4 | Dashboard update UI | `index.html` | Banner + button test |

### Batch 4: Integration

| # | Task | Files | Verification |
|---|------|-------|--------------|
| 4.1 | CLI commands | `cli.py` | `observeco service status` |
| 4.2 | Dashboard integration | `index.html` | End-to-end flow |
| 4.3 | Error handling | All | Graceful failure tests |
| 4.4 | Documentation | README, docs | User guide |

---

## 15. Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| OTEL listener crash loop | Data loss | Max restart attempts, alert user |
| Database corruption | Data loss | Backup before migration, WAL mode |
| Update fails mid-install | Broken install | Rollback to previous version |
| Port conflict resolution kills wrong process | Service disruption | Verify process name before kill |
| GitHub API rate limit | No update check | Cache response, fallback to manual |
| Memory leak in long-running service | Performance degradation | Memory monitoring, restart after 7 days |
| Windows process management | Service won't start | Use psutil cross-platform API |

---

## 16. Dependencies

| Dependency | Version | Purpose |
|------------|---------|---------|
| httpx | >=0.24 | GitHub API calls |
| psutil | >=5.9 | Process management |
| packaging | >=23.0 | Version comparison |

---

*This spec defines the service architecture for ObserveCo. Implementation follows the batch plan with independent verification after each batch.*

---

## 17. Missing Observability Fail-Safes (P0 — Must Fix Before Launch)

Six mission-critical fail-safes are missing from the current architecture. All are P0 — they cause trust erosion on Day 1. Cross-referenced from internal expectations gap document.

### 17.1 Process Supervision

**Problem:** Daemon crashes silently. No auto-restart. No launchd/systemd integration.

**Implementation guidance:**
- Ship a `~/.observeco/observeco.plist` template for macOS launchd
- Ship a `~/.observeco/observeco.service` template for Linux systemd
- `observeco service install` → copies the appropriate template and enables it
- `observeco service uninstall` → disables and removes
- Fallback: `observeco watch` writes a PID file; dashboard checks PID file on startup and re-launches if dead

**ponytail:** launchd/systemd templates are static files — no runtime dependency. PID-file fallback covers non-systemd platforms. If multi-platform process supervision is needed later, switch to a supervisor subprocess (e.g., `supervisord`-lite in Python).

PID-file fallback MUST have a restart limit: max 3 restarts in 5 minutes, then stop and alert. Use a simple counter file next to the PID file. On unsupported platforms (not macOS/not Linux), print "Platform not supported for service installation — use PID-file fallback" and exit 0. After copying template, run launchctl load (macOS) or systemctl daemon-reload && systemctl enable --now (Linux) and verify exit code. On uninstall, first stop the running service, then remove the template.

**Success metrics:**
- Daemon auto-restarts within 30s of crash (measured: kill daemon, check heartbeat cycle count after 35s)
- observeco service install exits 0 and launchctl list | grep observeco shows running
- observeco service uninstall exits 0 and template file is removed
- Restart limit (3 in 5 min) enforced — 4th crash within window does NOT restart

**Failure paths:**
- launchctl load fails — print error with fix instruction, exit 1
- systemctl enable fails — print error with fix instruction, exit 1
- Template already exists on install — print Service already installed, exit 0
- Template does not exist on uninstall — print Service not installed, exit 0

### 17.2 Startup Validation

**Problem:** Raw traceback if data dir missing. No dependency verification.

**Implementation guidance:**
- On `observeco dashboard` / `observeco watch` startup:
  1. Check `~/.observeco/` exists → create if missing
  2. Check SQLite is writable → `PRAGMA quick_check`
  3. Check ports 4318/8787 are available → socket bind test
  4. Check config file exists and is valid YAML
  5. If any check fails → print clear error message with fix instruction, exit 1

**ponytail:** Sequential checks are fine for startup (runs once, <100ms). If the startup sequence grows beyond 10 checks, switch to a parallel check runner with aggregated results.

Explicit error message templates for each check:
- DB check: 'Error: Cannot write to {db_path}\nFix: Run "mkdir -p {db_dir}" or check filesystem permissions'
- Port check: 'Error: Port {port} is in use by {process_name}\nFix: Use "--port {alt_port}" or stop the other process'
- Config check: 'Error: Config file {path} has invalid value for "{key}"\nFix: Expected one of {valid_values}, got "{actual_value}"'

Checks 1-3 (data dir, DB writable, ports) are FATAL — exit 1 on failure. Checks 4-5 (config) are WARNINGS — print warning, continue startup. Add --port and --db-path CLI flags to override defaults on failure.

**Success metrics:**
- 100% of startup failure modes produce structured error messages with fix instructions
- Each check completes within 500ms
- First-time user sees actionable error, not traceback

### 17.3 Stale Data Detection Per-Metric

**Problem:** Global banner exists (§8.4) but every chart needs its own "last updated X ago" label.

**Implementation guidance:**
- Every dashboard chart/table cell that displays a metric appends `(updated Xs ago)` or `(stale — last update Xm ago)`
- Backend: each `/api/...` endpoint returns `last_updated` timestamp alongside data
- Frontend: JS helper `renderStaleness(timestamp)` → green text if <60s, yellow if <5m, red if >5m
- Stale threshold per metric type (pulse: 60s, tokens: 5m, drift: 1h)

**ponytail:** Server-side timestamps are simpler than WebSocket push. If real-time staleness is needed, switch to SSE or WebSocket for push updates.

Every existing /api/... endpoint MUST be updated to include last_updated in its response. Enumerate the endpoints that return time-series data (pulse_log, token_history, drift, error_log, heal_log, alert_log). These are the minimum set. Static endpoints (config, license, glossary) do not need last_updated. Search for all @app.get and @app.post decorators in server.py and add the field to time-series endpoints only. The dashboard auto-refresh loop (every 30s) MUST call renderStaleness() on all visible metrics after each refresh. If the daemon heartbeat is stale (>60s), ALL metrics should show "Daemon may be down — data not flowing" instead of individual staleness labels.

**Success metrics:**
- Staleness labels accurate within 5s of actual staleness
- All time-series API endpoints return last_updated within 1 release cycle
- Daemon death detected and displayed within 90s

### 17.4 Disk Space Management

**Problem:** No pre-write disk check. Write failures cause silent data loss.

**Implementation guidance:**
- Before every write to SQLite, check `shutil.disk_usage(~/.observeco/)`
- Thresholds: <1GB free → warning log + dashboard yellow banner; <100MB free → stop writes, red banner, alert user
- `observeco status` shows disk usage
- Health check (§8.1) already spec'd disk check at 80% — implement it

**ponytail:** `shutil.disk_usage()` is a stat() call — negligible overhead. If the check becomes a bottleneck at high write volume, cache the result for 30s.

Before each write batch/cycle (not before every individual INSERT), check shutil.disk_usage(). For the watch daemon, this means once per probe cycle (~30s). For the dashboard, this means once per request handler.

Before write, check: free_bytes - wal_size > 1024*1024 (1MB buffer). WAL size from os.path.getsize(db_path + "-wal"). After stopping writes due to disk full, check disk every 60s. When free space > 1GB, resume writes automatically and log "Disk space recovered — writes resumed". Cache shutil.disk_usage() result in a module-level variable with a 30s TTL. Use time.monotonic() for cache expiry. Invalidate on write failure. ponytail: This is a TOCTOU race — disk can fill between check and write. Acceptable for a local tool. If data integrity requires atomic pre-check, switch to a write-ahead reservation system.

**Success metrics:**
- Zero data loss events due to disk full
- Writes resume within 60s of disk space recovering above 1GB
- Cache hit rate > 99% (only 1 stat() call per 30s per path)

### 17.5 Data Integrity Verification

**Problem:** No SQLite integrity check on startup. No schema version validation. No WAL recovery.

**Implementation guidance:**
- On startup: `PRAGMA integrity_check` → if fails, print error, offer `observeco db repair` (restore from backup)
- On startup: `PRAGMA schema_version` → compare against expected version from code
- On startup: `PRAGMA journal_mode=WAL` → verify WAL mode is active
- `observeco db check` CLI command runs integrity_check on demand
- Empty state: No DB file → print "No database found at {path} — nothing to check" and exit 0.
- `observeco db repair` restores from latest backup

**ponytail:** PRAGMA integrity_check reads every page — O(n) on DB size. For DBs > 100MB, use PRAGMA quick_check instead (checks header + first page only, ~100x faster). For DBs < 100MB, use full integrity_check. Upgrade path: switch to sqlite3's built-in incremental integrity checking for zero-downtime verification.

If integrity_check fails, start dashboard in READ-ONLY degraded mode. Show banner: "Database integrity issue detected — data may be incomplete. Run observeco db repair to restore from backup." Do NOT exit. After integrity_check, run PRAGMA foreign_key_check. If orphaned rows found, log warning with count and table names. Before restoring from backup, run PRAGMA integrity_check on the backup file. If backup is also corrupted, print "Backup is corrupted — no valid restore point available" and do NOT overwrite the current DB.

**Success metrics:**
- 100% of simulated DB corruptions detected on startup
- Dashboard starts in degraded mode (not crash) on integrity failure
- integrity_check completes within 5s for DBs < 100MB, within 1s for quick_check on DBs > 100MB

### 17.6 Self-Monitoring / Meta-Monitoring

**Problem:** Heartbeat file exists (§9.3) but no meta-monitor that escalates when the daemon stops ticking.

**Implementation guidance:**
- Watch daemon writes a heartbeat file every cycle: `~/.observeco/.daemon_heartbeat.json` with `{pid, last_tick, cycle_count, uptime_seconds, status}`
- Dashboard reads heartbeat on every page load
- If heartbeat is >60s stale → show "⚠️ Daemon may be down — data not flowing" banner
- If heartbeat is >300s stale → show "🔴 Daemon is down — data collection stopped" banner with restart button
- `observeco status` checks heartbeat freshness and reports daemon health

**ponytail:** File-based heartbeat is the simplest cross-process signal. If sub-second precision is needed, switch to a Unix domain socket or shared memory segment.

When reading heartbeat file, wrap json.loads() in try/except. On JSON decode error, treat as "heartbeat corrupted — daemon may be down" (same as >60s stale). On graceful daemon shutdown (SIGTERM), delete the heartbeat file. On crash, the file remains — dashboard detects staleness. Dashboard MUST verify BOTH heartbeat freshness AND PID liveness (os.kill(pid, 0)) before declaring the daemon running.

In addition to checking last_tick freshness, verify cycle_count is greater than the previous reading. If cycle_count hasn't increased in 2 checks, show "Daemon appears stuck — heartbeat updating but not progressing". observeco status MUST check heartbeat freshness and report daemon health as part of its output, not just the dashboard.

**Success metrics:**
- Daemon death detected within 90s (heartbeat > 60s stale + PID not alive)
- Corrupted heartbeat file handled without crash (dashboard shows daemon may be down)
- Stuck daemon (cycle_count not incrementing) detected within 2 heartbeat cycles
Empty state: No heartbeat file → report "Daemon not running — no heartbeat file found" as part of status output.

### 17.7 Cross-Reference

| Fail-Safe | State Enumeration (§1) | Failure Modes (§3.2) | Health System (§8) | Auto-Recovery (§9) |
|-----------|----------------------|---------------------|-------------------|-------------------|
| Process supervision | ✓ Added | ✓ Added | — | — |
| Startup validation | ✓ Added | ✓ Added | — | — |
| Stale data per-metric | ✓ Added | ✓ Added | — | — |
| Disk space | ✓ Added | ✓ Added | §8.1 (spec'd, not implemented) | §9.1 (spec'd, not implemented) |
| Data integrity | ✓ Added | ✓ Added | — | — |
| Self-monitoring | ✓ Added | ✓ Added | — | §9.3 (heartbeat exists, escalation missing) |

**See also:** internal expectations gap document (all 15 items with P0/P1/P2 ranking), internal strategic documents.
