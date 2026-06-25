# Code + System Design Testing Playbook — The Architecture Lens

**Product:** ObserveCo (and all future software projects)
**Status:** Living — update as lessons accumulate
**Version:** 3.3 — 2026-06-12
**Version History:**
| Version | Date | What changed |
|---------|------|-------------|
| 2.0 | 2026-05-30 | Added 9 lenses, Hound prompts, agent priming |
| 2.0 | 2026-05-30 | Added 9 lenses, Hound prompts, agent priming |
| 2.1 | 2026-05-31 | Standardization pass: uniform versioning, cross-ref to Playbook Inventory |
| 3.1 | 2026-05-31 | Standardization pass: all 7 playbooks bumped to v3.1 |
| 3.2 | 2026-06-10 | Added Pattern 8 (Payment Pipeline State Machine). Added Lessons Learned section. |
| 3.3 | 2026-06-12 | Added Pattern 9 (Migration Infrastructure Testing — GS-019 fixes, test matrix, anti-patterns). |

**Source:** Real failure — watch-daemon architecture fix failed on first attempt because no system-level analysis was done before writing code. The fix worked correctly at the function level but was architecturally wrong (SPOF, tied lifecycle, gaps in coverage).

This playbook sits alongside **coding-fidelity-playbook.md** (spec fidelity at the code level) and **ux-testing-playbook.md** (user experience at the perception level) to close the **system-architecture gap**.

---

## 1. Thesis

**The code can be correct. The system can still be wrong.**

Every architectural failure in this project traces to one root: the developer identified the *symptom* (stale data), fixed the *symptom* (add data refresh), and shipped the *symptom fix* — without first mapping the system's data pipeline, failure modes, lifecycle, and cross-environment requirements.

This document is not a code style guide. It is an **architectural testing process** — a repeatable way to catch the class of problem, not the instance.

**The five failure modes this playbook prevents:**

| # | Failure mode | Today's example |
|---|-------------|-----------------|
| 1 | **Lifecycle coupling** — writer dies when reader dies | Watch was a thread inside dashboard. Dashboard restarts → data gap for Pro users |
| 2 | **Coverage gap** — fixed one data source, missed four others | Fixed pulse_log → drift, garden, pathway, circuit_breakers still had no auto-fill |
| 3 | **Silent SPOF** — single crash kills both data collection and UI | Thread crash → no pulses AND no dashboard. User double-loses |
| 4 | **Platform blindspot** — works on POSIX, silent failure on Windows | `os.fork()` only, no `DETACHED_PROCESS`, no `CTRL_BREAK_EVENT` |
| 5 | **Liveness illusion** — heartbeat file exists but process is dead | Checked file age but not PID liveness → false "running" status |

---

## 2. The Pre-Code Protocol: System Analysis Phase

**Before writing a SINGLE line of code for any infrastructure change, run this protocol. It takes 10 minutes and saves 4 hours of rework.**

### 2.1 Step 1: Map the Full Data Pipeline

**Draw the data flow.** For every feature that involves a background writer, daemon, collector, or periodic sweep:

```
┌──────────┐     ┌──────────┐     ┌──────────┐
│  Source  │ ──→ │  Writer  │ ──→ │  Table   │ ──→ │  Reader  │
│  (agent) │     │  (who?)  │     │  (what?) │     │  (who?)  │
└──────────┘     └──────────┘     └──────────┘     └──────────┘
    ↑
  How does the writer get triggered?
  (manual CLI / UI thread / independent daemon / cron / webhook)
```

**Audit checklist — run this BEFORE any implementation:**

```
☐ 1. Enumerate EVERY table the reader (dashboard/UI/CLI) queries
    Search: grep -r "SELECT.*FROM" src/<reader>/
☐ 2. For each table: find EVERY INSERT/UPDATE
    Search: grep -r "INSERT.*<table>" src/
    Search: grep -r "UPDATE.*<table>" src/
☐ 3. For each writer: what is its lifecycle?
    - Manual CLI only? (user must remember to run it)
    - Thread inside reader process? (dies with reader)
    - Independent daemon? (PID file, survives restarts)
    - Webhook receiver? (only writes on external trigger)
    - Nothing at all? (table is never populated)
☐ 4. For each writer: what happens if it crashes?
    - Does data collection resume automatically?
    - Is there a gap? How big?
    - Does the reader detect the gap gracefully?
☐ 5. Is there a SINGLE writer that covers ALL tables it should?
    Or does each table have a different CLI command the user must run?
```

### 2.2 Step 2: Trace the Lifecycle Chain

Ask these questions in order:

| # | Question | Why it matters | How to test |
|---|----------|---------------|-------------|
| 1 | **Who starts the writer?** | If the user must manually start it, 90% won't | Trace from install to running state |
| 2 | **Who keeps it running?** | If it dies when the terminal closes, headless mode is broken | Simulate: close terminal, SSH disconnect, laptop sleep |
| 3 | **Who restarts it on crash?** | If no restart mechanism exists, data stops forever and the user only notices when they open the dashboard | Kill the process. Measure time to recovery |
| 4 | **Who restarts it on reboot?** | If no launchd/systemd/auto-start, machines rebooted for updates lose all data between reboot and next manual start | Check for launchd plist, systemd unit, Windows service |
| 5 | **Does the reader handle stale data gracefully?** | If the writer died 6 hours ago, does the UI show "6h ago" or does it look like everything is fine? | Kill the writer. Wait. Open the UI. |

### 2.3 Step 3: Identify All Failure Modes

For every daemon/background process, enumerate:

**Crash modes:**
- Process crashes → does it restart? Who detects it?
- SQLite locked/missing → does it retry or exit?
- Agent list empty → does it poll forever or exit cleanly?
- Invalid config → does it log a clear error and continue?

**Edge cases:**
- What happens when the user runs `start` twice? (should print "already running")
- What happens when the user runs `stop` when it's already stopped? (should print "not running")
- What happens when the PID file is stale (orphan from a killed process)? (should detect via `os.kill(pid, 0)`)
- What happens when the heartbeat file is corrupt? (should handle JSON parse error and treat as "stopped")
- What happens when the DB is busy (another process writing)? (SQLite WAL mode + busy_timeout handles this)
- What happens when the disk is full? (heartbeat write fails silently, next cycle may fail)

**Lifecycle tests:**
```
☐ start → status says running
☐ start when already running → prints error, no duplicate
☐ stop → status says not running
☐ stop when already stopped → prints error
☐ start → kill -9 → status says not running (PID check, not heartbeat-only)
☐ start → reboot → status says not running (no auto-start on boot)
☐ start → wait 2 cycles → check DB has fresh data
☐ start → stop → restart → check no duplicate PID
```

### 2.4 Step 4: Cross-Platform Audit

Before shipping any process-management code, verify against every target OS:

| Concern | POSIX (Mac/Linux) | Windows |
|---------|-------------------|---------|
| Process creation | `os.fork()` + `os.setsid()` | `subprocess.DETACHED_PROCESS` |
| Signal to stop | `signal.SIGTERM` → `signal.SIGKILL` | `signal.CTRL_BREAK_EVENT` |
| PID liveness | `os.kill(pid, 0)` | Same |
| Auto-start on boot | `launchd plist` / `systemd unit` | Windows Service / Task Scheduler |
| Path to daemon binary | `sys.executable -m observeco ...` | Same (subprocess with absolute Python path) |
| Path to data files | `platformdirs` (`~/Library`, `~/.local/share`) | `platformdirs` (`%APPDATA%`) |
| Fork available? | Yes | No (`os.fork()` raises `AttributeError`) |

**The golden rule:** If you use `os.fork()`, `os.setsid()`, or any POSIX-only syscall, **you must have a Windows fallback path** — and it must be tested during CI, not discovered in production by a Windows user.

### 2.5 Step 5: The Architecture Decision Record

Before writing any code, write this brief ADR in the spec or PR description:

```markdown
### ADR: [Feature Name]

**Context:** [What's the data pipeline? Who reads, who writes?]

**Options considered:**
1. Thread inside reader process (rejected: SPOF, coupled lifecycle)
2. Independent daemon with PID file (selected)
3. Cron job (rejected: interval minimum 1 minute, no lifecycle management)

**Chosen option:** [which one and why]

**Failure modes identified:**
- Crash: [how does it recover?]
- Stale data: [what does the UI show?]
- Double-start: [how is it prevented?]
- Orphan PID: [how is it detected?]

**Cross-platform:** [POSIX path / Windows path / both tested]

**Tables written:** [list]
**Tables that should be written but aren't:** [gaps discovered]
```

---

## 3. The Implementation Phase: Code Discipline

### 3.1 Process Lifecycle Code Pattern

Every daemon must support exactly these three states:

```python
# ── REQUIRED interface for every background daemon ──

def start() -> None:
    """Start the daemon. If already running, print error and return.

    Platform-specific:
      POSIX: double-fork + setsid (proper daemonization)
      Windows: subprocess with DETACHED_PROCESS + CREATE_NEW_PROCESS_GROUP
    """
    ...

def stop() -> None:
    """Stop the daemon by signalling its PID.

    Platform-specific:
      POSIX: SIGTERM → SIGKILL after 5s timeout
      Windows: CTRL_BREAK_EVENT (repeated after timeout)
    """
    ...

def status() -> dict:
    """Return {'running': bool, 'pid': int|None, 'heartbeat_age': float|None}.

    Must check BOTH:
      - Does the PID file exist? Read it.
      - Is that PID actually alive? os.kill(pid, 0).
      - (If applicable) Is the heartbeat file fresh?
    """
    ...
```

**Verification checklist for the lifecycle:**
```
☐ start() when stopped → daemon starts, PID file written, heartbeat visible
☐ start() when running → prints "already running", no duplicate process
☐ stop() when running → PID process stopped, PID file deleted
☐ stop() when stopped → prints "not running", no crash
☐ status() when running → running=True, pid is alive, age is < interval*2
☐ status() when stopped → running=False, even if stale heartbeat exists
☐ status() with orphan PID file → running=False, stale file cleaned
☐ status() with corrupt PID file → running=False, no crash
```

### 3.2 Heartbeat File Contract

The heartbeat file is the **contract** between writer and reader. It must:

1. Be written **every cycle** (not just on start/stop)
2. Include `pid` so readers can verify liveness (not just freshness)
3. Include `timestamp` so readers can measure staleness
4. Be written atomically (write temp file, rename → not partial reads)
5. Be readable by any process — no file locks, simple JSON

**Verification:**
```
☐ heartbeat written within 1 cycle of daemon start
☐ heartbeat updated every cycle (check timestamp changes)
☐ heartbeat contains pid matching actual OS process
☐ heartbeat stops updating after daemon stop
☐ corrupt heartbeat file → daemon continues (error logged)
```

### 3.3 The "Who Writes This" Trace

**Rule:** For every table in the database, there must be exactly one comment at the schema definition that says "Written by: [source]".

```python
# Schema comment template:
CREATE TABLE IF NOT EXISTS pulse_log (
    -- Source: observeco watch daemon (every 30s)
    -- Manual fallback: observeco pulse check (one-shot)
    ...
);

CREATE TABLE IF NOT EXISTS pathway_edges (
    -- Source: observeco watch daemon (every 15min)
    -- NOTE: was UNWRITTEN from May 24-30 until daemon rewrite
    ...
);
```

**Verification:** Run this after schema changes:
```bash
grep -B5 "CREATE TABLE.*(" src/observeco/db.py | grep -E "(-- Source|CREATE)"
```
Every table should have a `-- Source:` comment above it. If any table lacks one, it's probably not being written by anything.

### 3.4 The Crash Resilience Pattern

Every daemon loop must survive these without data loss:

```python
while running:
    try:
        # ONE agent failure must not kill the entire cycle
        for agent in agents:
            try:
                probe(agent)
            except Exception as e:
                log_error(e)  # Log and continue
                continue

        # ONE sweep failure must not kill the entire daemon
        try:
            run_drift_scan()
        except Exception:
            pass  # Best-effort sweep, try again next cycle

        # ONE I/O failure must not crash the daemon
        try:
            write_heartbeat()
        except Exception:
            pass  # Next cycle will retry

        sleep(interval)
    except Exception as e:
        log_critical(e)  # Unhandled — but log it before crash
        raise
```

---

## 4. The Verification Phase: Systematic Testing

### 4.1 The Data Pipeline Audit

Run this before marking ANY infrastructure change as done:

```bash
#!/usr/bin/env bash
# data-pipeline-audit.sh
# Run this after any change that adds/modifies a data pipeline.

echo "=== TABLE: WRITER AUDIT ==="
# Find all CREATE TABLE statements
grep "CREATE TABLE.*(" src/observeco/db.py | while read -r line; do
    table=$(echo "$line" | grep -oP 'CREATE TABLE IF NOT EXISTS \K\w+')
    echo "Table: $table"
    echo -n "  Sources: "
    grep -r "INSERT.*$table" src/observeco/ | grep -v "db.py" | grep -oP 'src/\S+' | sort -u | tr '\n' ' '
    echo
    echo -n "  Readers: "
    grep -r "SELECT.*FROM $table" src/observeco/ | grep -oP 'src/\S+' | sort -u | tr '\n' ' '
    echo
    echo
done
```

### 4.2 The Lifecycle Test Suite

Every daemon must pass these 12 tests:

```python
# lifecycle_tests.py — run against any daemon with start/stop/status

def test_start_stop_cycle():
    """start → status shows running → stop → status shows stopped"""
    daemon.start()
    time.sleep(1)
    s = daemon.status()
    assert s["running"], f"Expected running after start, got {s}"
    daemon.stop()
    time.sleep(1)
    s = daemon.status()
    assert not s["running"], f"Expected stopped after stop, got {s}"


def test_double_start():
    """Second start when already running does not create duplicate"""
    daemon.start()
    pid_before = daemon.status()["pid"]
    daemon.start()  # Should fail gracefully
    pid_after = daemon.status()["pid"]
    assert pid_after == pid_before, "PID changed on double-start"
    daemon.stop()


def test_double_stop():
    """Second stop when already stopped does not crash"""
    daemon.start()
    daemon.stop()
    daemon.stop()  # Should fail gracefully
    s = daemon.status()
    assert not s["running"], "Still running after double stop"


def test_data_written():
    """After 2 cycles, check DB has new records"""
    daemon.start()
    time.sleep(interval * 2 + 5)
    # Check pulse_log has recent entries
    assert fresh_pulses_exist(), "No new pulses after 2 cycles"
    # Check heartbeat is fresh
    assert heartbeat_age() < interval * 2, "Heartbeat stale"
    daemon.stop()


def test_kill_and_recover():
    """kill -9, then start again — no orphan conflict"""
    daemon.start()
    pid = daemon.status()["pid"]
    os.kill(pid, 9)  # SIGKILL
    time.sleep(1)
    s = daemon.status()
    assert not s["running"], "Should detect kill signal"
    daemon.start()  # Should succeed (PID file may be stale)
    time.sleep(1)
    s = daemon.status()
    assert s["running"], "Should restart after kill"
    daemon.stop()


def test_orphan_pid_file():
    """Stale PID file with no process — start should clean it"""
    # Write fake PID file
    fake_pid = 999999999
    pid_path.write_text(str(fake_pid))
    s = daemon.status()
    assert not s["running"], "Should not think fake PID is alive"
    daemon.start()
    assert daemon.status()["running"]
    daemon.stop()


def test_corrupt_heartbeat():
    """Corrupt heartbeat file does not crash daemon"""
    hb_path.write_text("not json{")
    daemon.start()  # Should start and overwrite
    time.sleep(interval + 5)
    # Heartbeat should now be valid JSON
    assert is_valid_json(hb_path.read_text())
    daemon.stop()


def test_stale_heartbeat_detected():
    """Reader detects stale heartbeat and treats as NOT running"""
    # Simulate old heartbeat
    import json
    old_data = {"timestamp": int(time.time()) - 99999, "pid": 0}
    hb_path.write_text(json.dumps(old_data))
    s = daemon.status()
    assert not s["running"], "Stale heartbeat should not fool status"


def test_dashboard_auto_launch():
    """Dashboard starts daemon if heartbeat stale"""
    # Kill any existing daemon, make heartbeat stale
    daemon.stop()
    import json
    old_data = {"timestamp": 0, "pid": 0}
    hb_path.write_text(json.dumps(old_data))
    # Start dashboard (mocked)
    from observeco.dashboard.server import _ensure_watch_running
    _ensure_watch_running()
    time.sleep(2)
    daemon.stop()


def test_platform_specific_start():
    """Daemon starts correctly on current platform"""
    daemon.start()
    s = daemon.status()
    assert s["running"]
    # On POSIX: assert os.getsid(s["pid"]) exists (child in own session)
    daemon.stop()


def test_heartbeat_writer_reader_contract():
    """Heartbeat file contains all required fields"""
    daemon.start()
    time.sleep(interval + 5)
    import json
    hb = json.loads(hb_path.read_text())
    assert "pid" in hb, "Heartbeat missing pid"
    assert "timestamp" in hb, "Heartbeat missing timestamp"
    assert "status" in hb, "Heartbeat missing status"
    assert "cycle" in hb, "Heartbeat missing cycle"
    assert hb["pid"] > 0, "Invalid pid in heartbeat"
    daemon.stop()


def test_no_data_gap_on_reader_restart():
    """Reader stops and restarts — writer continues writing"""
    daemon.start()
    time.sleep(interval)  # Let one cycle pass
    # Simulate reader crash by checking data is written
    ts_before = get_last_pulse_timestamp()
    time.sleep(interval * 2)
    ts_after = get_last_pulse_timestamp()
    assert ts_after > ts_before, "Data gap during reader restart simulation"
    daemon.stop()
```

### 4.3 The Cross-Platform Test Matrix

For every process-management change, fill this matrix:

| Test | Mac | Linux | Windows |
|------|-----|-------|---------|
| Daemon starts | ✅ CI | ✅ CI | 🟡 DETACHED_PROCESS + fallback msg |
| Daemon stops | ✅ CI | ✅ CI | 🟡 taskkill fallback |
| status() accurate | ✅ CI | ✅ CI | 🟡 Same os.kill(pid,0) path |
| Data written after 2 cycles | ✅ CI | ✅ CI | 🔴 Not tested |
| Double-start safely handled | ✅ CI | ✅ CI | 🟡 _start_windows guard |
| Orphan PID detected | ✅ CI | ✅ CI | ✅ Same _is_pid_alive path |
| Kill-9 → restart | ✅ CI | ✅ CI | 🟡 taskkill /F fallback |
| Reader auto-launch | ✅ CI | ✅ CI | 🟡 DETACHED_PROCESS in dashboard

**Rule:** Any ❌ or 🔴 in this matrix must be documented as a known limitation in the README and linked to a GitHub issue.

---

## 5. The 9-Lens Detection Framework

Every infrastructure change passes through these 9 lenses before it can merge. Score each 0 (fail) to 5 (perfect). Minimum target: ≥4 per lens, ≥32/45 total.

### Lens 1: Lifecycle Independence

**What it detects:** Writer lifecycle coupled to reader lifecycle.

| Score | Description |
|-------|-------------|
| 0 | Writer is a thread inside reader process |
| 1 | Writer is a thread with no error isolation |
| 2 | Writer is same process but fork/child |
| 3 | Writer is independent process but restarts with reader |
| 4 | Writer is independent, survives reader restart |
| 5 | Writer is independent, auto-started by reader, managed independently |

**Today's score:** Start = 0 (thread) → End = 5 (independent daemon)

### Lens 2: Coverage Completeness

**What it detects:** Fixed one data source but missed others.

```
☐ Every table the reader queries has at least one writer
☐ No table relies on a manual CLI command for data
☐ Writer writes ALL tables it could reasonably write
☐ Schema comments identify the data source for each table
```

**Today's score:** 2/4 — fixed pulse_log but missed drift, garden, pathway, circuit_breakers. Schema comments missing.

### Lens 3: Crash Resilience

**What it detects:** A single failure takes down the entire pipeline.

```
☐ One agent probe failure → logging, continues with other agents
☐ One sweep failure → logging, retries next cycle
☐ One I/O error → logging, retries next cycle
☐ Heartbeat write failure → daemon continues (best effort)
☐ Unhandled exception → logged before crash
```

**Today's score:** 3/5 — per-agent try/catch existed, but no heartbeat write error isolation in original code.

### Lens 4: Liveness Accuracy

**What it detects:** False positives from stale metadata.

```
☐ Status checks heartbeat freshness
☐ Status ALSO checks PID liveness (os.kill(pid, 0))
☐ Status handles corrupt/missing PID file
☐ Status handles corrupt/missing heartbeat
☐ Stale heartbeat with dead PID → "not running"
```

**Today's score:** 2/5 — initial `_ensure_watch_running` checked only heartbeat freshness. PID check added in patch 2.

### Lens 5: Cross-Platform Parity

**What it detects:** POSIX-only code that silently fails on Windows.

```
☐ No os.fork() without Windows subprocess fallback
☐ No os.setsid() without Windows equivalent
☐ No SIGTERM/SIGKILL without Windows CTRL_BREAK_EVENT fallback
☐ No assumptions about /tmp, ~/.observeco — uses platformdirs
☐ All start/stop/status tested on target OS or documented exception
```

**Today's score:** 1/5 — pure POSIX. Windows fix added as post-hoc patches.

### Lens 6: Startup Grace

**What it detects:** The user sees an error or empty state before the system stabilizes.

```
☐ First-time user: daemon auto-started on first dashboard launch
☐ After reboot: daemon dies, dashboard auto-restarts it
☐ After crash: daemon dies, dashboard detects stale heartbeat, restarts
☐ Start-up race: daemon may not have completed first cycle → UI shows "populating..."
☐ Stale data indicator: cards show "last pulse Xh ago" not just "—"
```

**Today's score:** 3/5 — dashboard auto-launches, but no "populating..." state or first-cycle indicator.

### Lens 7: Defensive Coding for the Unknown

**What it detects:** Assumptions about the environment that will break elsewhere.

```
☐ No hardcoded paths (use platformdirs)
☐ No hardcoded /tmp usage
☐ No assumption about Python path (use sys.executable)
☐ No implicit dependency on external commands (pgrep, ps, killall)
☐ No assumption that $HOME is writable
☐ All file operations use try/except with specific exception types
```

**Today's score:** 4/5 — uses platformdirs and sys.executable, but had `os.fork()` without Windows fallback.

### Lens 8: Observability & Debuggability

**What it detects:** "It works but I have no idea why it broke at 3 a.m."

| Score | Description |
|-------|-------------|
| 0 | No logs, no metrics, no heartbeat |
| 1 | Print-based debug only |
| 2 | Structured logs but no persistent file |
| 3 | Structured logs + heartbeat file + start/stop in logs |
| 4 | All of the above + daemon status is a single CLI command away |
| 5 | Structured logs with trace IDs, heartbeat with cycle counters, Prometheus metrics endpoint, single command to tail all daemon logs |

**Today's score:** 3/5 — structured logs + heartbeat + status command exist, but no trace IDs, no metrics endpoint, no Prometheus.

### Lens 9: Scalability & Multi-Instance Safety

**What it detects:** Assumptions that there will only ever be one instance running.

| Score | Description |
|-------|-------------|
| 0 | No PID file, can trivially start multiple copies |
| 1 | PID file exists but no double-start guard |
| 2 | Double-start guarded but no orphan PID detection |
| 3 | Double-start + orphan PID + stale heartbeat detection |
| 4 | All of the above + shared-mode safety: WAL-mode SQLite for concurrent writers, instance_id per pulse row, shared path validation, team-instance indicator in dashboard |
| 5 | All of the above + paginated agent list with search/filter for 100+ agents, server-side pagination, no card-bloating, performance budget (<1.5s initial render, <300ms filter), no pagination widgets below 25-agent threshold |

**Today's score:** 4/5 — PID file + double-start guard + orphan detection + shared-mode + pagination/search (score 5 when performance budget is CI-enforced).

---

## 6. The Golden Gate — Infrastructure Pre-Merge Checklist

Before ANY infrastructure change merges:

```
□ 1. DATA PIPELINE MAP: Every table the reader queries has a known writer
     (grep INSERT for each table, grep SELECT for each reader)
     File: _______________
     Pass: YES / NO (if NO, cannot merge)

□ 2. LIFECYCLE MATRIX: start/stop/status tested for all 12 lifecycle tests
     Pass: ___/12

□ 3. FAILURE MODES: Crash, double-start, orphan PID, stale heartbeat
     all handled
     Pass: YES / NO

□ 4. CROSS-PLATFORM: POSIX tested, Windows documented or tested
     Pass: YES / DOCUMENTED / NO

□ 5. HEARTBEAT CONTRACT: Heartbeat contains pid + timestamp + status + cycle
     Pass: YES / NO (if NO, reader cannot detect freshness)

□ 6. SCHEMA COMMENTS: Every table has -- Source: comment
     Pass: YES / NO

□ 7. LENS SCORES: All 9 lenses scored ≥4
     Pass: YES / NO (score: ___/45, target ≥32)

□ 8. ADR WRITTEN: Architecture Decision Record in the PR
     Pass: YES / NO

□ 9. STALE DATA HANDLING: UI shows human-readable staleness for every data source
     Pass: YES / NO

□ 10. OBSERVABILITY: Logs structured, heartbeat cycle-counted, status via CLI
      Pass: YES / NO

□ 11. MULTI-INSTANCE SAFE: Double-start guarded, orphan PID detected, no global state
      Pass: YES / NO

□ 12. FIRST-TIME USER: Pipeline works on first install, no manual setup
      Pass: YES / NO
```

**If any NO, the PR cannot merge until the gap has a documented issue or explicit trade-off decision signed off by the lead.**

---

## 7. Today's Retrospective: The Watch Daemon Failure Chain

### What happened

```
1. Sean reports "last pulse 12h ago"
2. I diagnose: watch daemon not running
3. I implement: start watch as thread inside dashboard serve()
4. Sean rejects: "flawed — pro license needs continuous data, dashboard dies → watch dies"
5. I re-architect: independent daemon with PID file, heartbeat, cross-platform
6. Additional bugs found during re-implementation:
   - Drift/garden/pathway/errors had same pattern (no auto-fill)
   - POSIX-only (no Windows)
   - Heartbeat check was file-only, not PID-only
   - No schema comments identifying data sources
```

### Root cause chain

```
┌───────────────────────────────────────────────────────────────┐
│ Lack of architectural analysis BEFORE code                     │
│                                                               │
│ └→ Jumped to implementation on first viable idea              │
│     └→ Didn't enumerate ALL tables the dashboard reads        │
│         └→ Fixed ONE data source, missed FOUR                 │
│     └→ Didn't trace lifecycle: "what happens on restart?"     │
│         └→ Tied writer to reader → Pro data gap               │
│     └→ Didn't consider cross-platform                         │
│         └→ POSIX-only → Windows silent failure                │
│     └→ Didn't consider crash scenarios                        │
│         └→ Thread crash → dashboard crash → double loss       │
│                                                               │
│ Result: Correct fix at function level, wrong fix at system     │
│ level. 4 rework cycles to get to the right architecture.      │
└───────────────────────────────────────────────────────────────┘
```

### What the playbook would have prevented

| Prevention point | Playbook section | Would have caught |
|-----------------|-----------------|-------------------|
| Before code: map all tables | §2.1 Step 1 | Found drift/garden/pathway gaps before patching |
| Before code: trace lifecycle | §2.2 Step 2 | Detected thread-dies-with-dashboard problem |
| Before code: identify failures | §2.3 Step 3 | Detected crash SPOF, double-start, orphan PID |
| Before code: cross-platform | §2.4 Step 4 | Added Windows support before merge |
| During code: heartbeat contract | §3.2 | Heartbeat includes pid for liveness check |
| During code: schema comments | §3.3 | Every table has -- Source: annotation |
| During verification: 12 tests | §4.2 | Caught orphan PID, corrupt heartbeat, stale detection |
| During verification: 9 lenses | §5 | All 5 failure modes caught (score was 2-3/5) |
| Before merge: checklist | §6 | 12-item gate caught coverage gap |

---

## 8. Lessons Learned Log

### 8.1 Template for Future Entries

| Date | What AI/Human did | What actually happened | Failure Mode Prevented | Playbook Section That Would Have Caught It |
|------|-------------------|------------------------|------------------------|-------------------------------------------|
| YYYY-MM-DD | Brief summary of action | What actually went wrong | Which of the 5/9 failure modes | Which § would have caught it |
| | | | | |

### 8.2 2026-05-30 — Watch Daemon v0 Architecture Gap

| What AI/Human did | What actually happened | Failure Mode Prevented | Playbook Section That Would Have Caught It |
|-------------------|------------------------|------------------------|-------------------------------------------|
| Saw "last pulse 12h ago" → patched thread inside dashboard | SPOF + lifecycle coupling | #1 Lifecycle coupling | §2.1 + §2.2 |
| Used `os.fork()` only | Windows silent failure | #4 Platform blindspot | §2.4 |
| Heartbeat freshness only | Liveness illusion | #5 Liveness illusion | §3.2 |
| Fixed pulse_log only | Coverage gap on 4 other tables | #2 Coverage gap | §2.1 + §3.3 |
| Shipped without 12 lifecycle tests | Silent regression risk | All 9 lenses | §4.2 + §5 |

**Lesson:** The code passed every compile-time and runtime check. The architecture failed every system-level check. The gap was not in the code — it was in the *process* of deciding what to build.

### 2026-05-31 — Standardization Pass

| What was wrong | Category | Fix applied |
|----------------|----------|-------------|
| No Version History table — inline version string only | Missing metadata | Added Version History table with 2.0 → 2.1 entries. |
| No cross-reference to Playbook Inventory | Cross-reference gap | Added reference to requirements-fidelity-playbook.md §Playbook Inventory. |

---

## 9. Agent Priming & Anti-Hallucination Rules

**(2026-Specific — Critical for Autonomous Agents)**

This section makes the playbook work when any AI agent is driving the changes autonomously. Before any infrastructure task, prime the agent with:

1. "You are now in **100x System-Architecture Mode**. You MUST run the full Pre-Code Protocol (§2) BEFORE writing any code."

2. "Output the **data pipeline map** and **ADR template** as the very first response — before any code."

3. "Never propose a thread-inside-reader or cron-only solution without first scoring all 9 lenses."

4. "After every patch, run the **12 lifecycle tests** + **data-pipeline-audit.sh** and show me the output verbatim."

5. "If any lens scores <4, you MUST stop and ask for human confirmation before proceeding."

6. "Every `SELECT` in the reader must have a corresponding `INSERT` somewhere. If it doesn't, your architecture is incomplete."

7. "If you use `os.fork()`, you must ALSO have a `sys.platform == 'win32'` fallback. No exceptions."

8. "A heartbeat file is NOT proof that a process is alive. `os.kill(pid, 0)` IS. Check both."

---

## 10. Expert Prompts for Hound

### Prompt A: Pre-Code System Analysis (run first)

```
You are now in 100x System-Architecture Mode.

Run the FULL System-Design Pre-Code Protocol (§2) on [feature].

1. Draw the complete data pipeline map:
   - Every table the reader (dashboard/UI/CLI) queries
   - Every writer (INSERT/UPDATE source) for each table
   - The lifecycle of each writer (thread / daemon / CLI / cron)

2. Trace the full lifecycle chain:
   - Who starts the writer?
   - Who keeps it running?
   - Who restarts it on crash?
   - Who restarts it on reboot?
   - Does the reader handle stale data gracefully?

3. Enumerate ALL failure modes:
   - Crash modes (process, SQLite, empty config, invalid config)
   - Edge cases (double-start, double-stop, orphan PID, corrupt heartbeat)
   - Lifecycle tests (all 8 listed in §2.3)

4. Fill the cross-platform matrix:
   - POSIX path (fork, setsid, SIGTERM, SIGKILL)
   - Windows path (DETACHED_PROCESS, CTRL_BREAK_EVENT)
   - Any gaps → documented known limitation

5. Output the COMPLETE ADR template (§2.5) filled in.

Do not write any code until I reply "ARCHITECTURE APPROVED".
```

### Prompt B: Full Pre-Merge Gate (run before marking done)

```
Execute the complete System-Design Golden Gate (§6) + 12 lifecycle tests + 9-lens scoring on [feature].

1. Run each of the 12 Golden Gate checklist items.
2. For each: output PASS / FAIL / N/A with evidence.
3. Score all 9 lenses (0-5 each). Total ___/45 (target ≥32).
4. Run all 12 lifecycle tests (§4.2) and show results.
5. Run the data-pipeline-audit.sh (§4.1) and show output.
6. Confirm schema comments exist on every table (§3.3).

Output as a table:

| Gate Item | Result | Evidence |
|-----------|--------|----------|
| 1. Data pipeline map | ✅ PASS | grep output shows ... |
| 2. Lifecycle tests | ✅ 12/12 | Test output ... |
| ... | ... | ... |

| Lens | Score | Notes |
|------|-------|-------|
| 1. Lifecycle Independence | 5/5 | ... |
| ... | ... | ... |
| **Total** | **34/45** | **✅ ≥32** |

Only if ALL pass may you say: "Ready for human architecture sign-off."
```

---

## Pattern 9: Migration Infrastructure Testing (GS-019)

**Pattern:** SQLite migration systems with dual definitions (`_SCHEMA_SQL` bootstrap + versioned `MIGRATIONS`) silently skip migrations on fresh installs, mask data loss during recreate-table operations, and have no downgrade protection. Unit tests must cover every GS-019 fix independently.

**Prevent:** Backup storms, silent data loss on migration crash, version corruption on downgrade, orphaned migration tables.

### 9.1 The Dual-Definition Problem

```
_SCHEMA_SQL runs first (IF NOT EXISTS)
    ↓
MIGRATIONS run second (skip if table/column exists)
    ↓
10+ tables exist only in _SCHEMA_SQL with no migration provenance
```

**Why it's dangerous:** On fresh install, `_SCHEMA_SQL` creates all tables. Migrations 2-5 run but are no-ops. The migration chain is decorative — `_SCHEMA_SQL` is the real schema. If a migration adds a column that `_SCHEMA_SQL` doesn't have, the migration silently succeeds (column already exists from bootstrap) but the schema is wrong.

**Test:** Verify `_SCHEMA_SQL` tables match the union of all migration CREATE TABLE statements. Flag any table in `_SCHEMA_SQL` that isn't also created by a migration.

### 9.2 The Six GS-019 Fixes and Their Test Matrix

| Fix | What it prevents | Test approach |
|-----|-----------------|---------------|
| **1. Backup before migrations** | Data loss on failed migration | Mock `backup()`, verify called when `has_pending && has_data()`, not called otherwise |
| **2. Pre/post row count verification** | Silent data loss during migration | Snapshot counts before, verify after, assert warning on >10% drop, assert error when table disappears |
| **3. Stranded table recovery** | Data stranded in `_v11` temp tables after crash | Create `_v11` table with data, drop target, re-init → verify rename + data preserved |
| **4. Downgrade guard** | Version corruption when DB > code | Set `schema_version` higher than `SCHEMA_VERSION`, re-init → verify version unchanged + warning logged |
| **5. Doctor data health checks** | No visibility into schema/backup health | Call `check_data_health()`, assert schema version check, backup recency, stranded table detection |
| **6. Backup rotation + cooldown** | Backup storms from multiple processes | Create N+1 backups → verify only N kept; create recent backup → verify next backup skipped |

### 9.3 The Stranded Table Pattern

Recreate-table migrations (ALTER CHECK constraints) follow this pattern:

```sql
CREATE TABLE target_v11 (...);
INSERT INTO target_v11 SELECT ... FROM target;
DROP TABLE target;
ALTER TABLE target_v11 RENAME TO target;
```

**If crash occurs between DROP and RENAME:** Data is stranded in `_v11`. The target table doesn't exist. All subsequent writes fail silently.

**Recovery pattern (run on every `_init_db()`):**

```python
recovery_map = {
    "pathway_nodes_v11": "pathway_nodes",
    "alert_subscriptions_v15": "alert_subscriptions",
}
for temp_table, target_table in recovery_map.items():
    temp_exists = check sqlite_master for temp_table
    target_exists = check sqlite_master for target_table
    if temp_exists and not target_exists:
        ALTER TABLE temp_table RENAME TO target_table
```

**Test:** Create the `_v11` table manually, drop the target, call `_init_db()` → verify the target exists with data.

### 9.4 The Downgrade Guard Anti-Pattern

**Broken (original code):**

```python
# Force version to current — OVERWRITES higher versions
if current_version < SCHEMA_VERSION:
    conn.execute("INSERT OR REPLACE INTO _meta ...")
    conn.commit()
# Missing: what if current_version > SCHEMA_VERSION?
```

**Fixed:**

```python
if current_version < SCHEMA_VERSION:
    conn.execute("INSERT OR REPLACE INTO _meta ...")
    conn.commit()
elif current_version > SCHEMA_VERSION:
    logger.warning(
        f"GS-019: Database version ({current_version}) > code version "
        f"({SCHEMA_VERSION}). Possible downgrade. Not modifying version."
    )
```

**Test:** Set `_meta(schema_version)` to `SCHEMA_VERSION + 10`, re-init → verify version unchanged + warning logged.

### 9.5 The Backup Cooldown Anti-Pattern

**Original cooldown mechanism (spec):** A `.last_backup` timestamp file.

**Actual implementation:** `_get_last_backup_time()` scans `pulse_*.db` file modification times.

**Why the mismatch matters:** Tests must create actual `pulse_*.db` files with controlled `mtime` — not a `.last_backup` file — to trigger or skip the cooldown.

**Test pattern:**

```python
# Cooldown active: create recent pulse_*.db
(backup_dir / "pulse_recent.db").write_text("backup")
result = db.backup(dest_path=...)  # → False (skipped)

# Cooldown expired: create old pulse_*.db
old_backup = backup_dir / "pulse_old.db"
os.utime(old_backup, (old_time, old_time))  # mtime > 4h ago
result = db.backup(dest_path=...)  # → True (allowed)
```

### 9.6 The caplog Contamination Anti-Pattern

**Problem:** Using `caplog` to verify that `_verify_migration_integrity()` does NOT log warnings fails because `_init_db()` runs first and logs migration skip warnings (e.g., "column already exists"). These contaminate `caplog.text`.

**Fix:** Don't use `caplog` for negative assertions. Instead, patch the specific logger:

```python
logger = logging.getLogger("observeco.db")
with patch.object(logger, "warning") as mock_warn, \
     patch.object(logger, "error") as mock_err:
    db._verify_migration_integrity(pre, post)
mock_warn.assert_not_called()
mock_err.assert_not_called()
```

### 9.7 The Path.touch() Platform Trap

**Problem:** `Path.touch(times=(atime, mtime))` is not supported on all Python versions / platforms. On macOS Python 3.11, it raises `TypeError: Path.touch() got an unexpected keyword argument 'times'`.

**Fix:** Use `os.utime(path, (atime, mtime))` instead — works everywhere.

### 9.8 Migration Infrastructure Test Checklist

Before merging any migration infrastructure change, verify:

- [ ] `_has_data()` — returns True when tables have rows, False when empty
- [ ] Backup called when `has_pending && has_data()`, NOT called when no pending or no data
- [ ] Downgrade guard logs warning, doesn't overwrite version when `current > SCHEMA_VERSION`
- [ ] Stranded `_v11` tables detected and renamed on `_init_db()`
- [ ] Stranded recovery is no-op when both tables exist
- [ ] Pre/post row count snapshot works (captures counts for all user tables)
- [ ] Row count verification warns on >10% drop
- [ ] Row count verification errors when table disappears
- [ ] Row count verification skips empty pre-counts (0 rows)
- [ ] Backup rotation keeps only `BACKUP_MAX_COUNT` backups
- [ ] Backup cooldown skips when recent `pulse_*.db` exists
- [ ] Backup cooldown allows when mtime > `BACKUP_COOLDOWN_HOURS`
- [ ] Doctor `check_data_health()` runs schema version, backup recency, stranded table checks
- [ ] All 24 tests in `test_migration_infra.py` pass

---

## New Pattern: Webhook → Feature Propagation Race

**Pattern (addition):** Three independent bugs in a payment pipeline (missing session ID, corrupted encryption key, missing handler call) each passed unit tests. Combined, they created a state where payment succeeded but Pro didn't activate. No single test caught it.

**Pre-flight check (add to pipeline review):**
1. Map the full event chain: event received → data stored → state changed → feature unlocked → UI updated
2. For each transition, verify: does the NEXT step depend on the PREVIOUS step's output being correct?
3. If yes: test with each dependency broken independently. If any one break allows a "successful" outcome with wrong state, the pipeline has a race vulnerability.
4. Specifically for payment pipelines: test with bad encryption key + missing template var + missing handler call. All three must each independently result in clear failure — not silent degraded mode.

## Appendix A: Quick Reference — The Pre-Code Protocol

**Before writing ANY infrastructure code, answer these 7 questions:**

1. **Who reads this data?** (the reader)
2. **Who writes this data?** (every writer for every table the reader touches)
3. **Is every writer independent of the reader?** (lifecycle decoupled?)
4. **What happens when the writer crashes?** (auto-recovery or data gap?)
5. **What happens when the reader restarts?** (does writer survive it?)
6. **What platform are we on?** (POSIX, Windows, or both?)
7. **Where is the heartbeat?** (how does the reader know the writer is alive?)

**If you cannot answer all 7 before writing code, you are not ready to implement.**

## Appendix B: Quick Reference — The "Lazy Developer" Tell

Spot these signs in your own code or a teammate's:

| Tell | What it means | Fix |
|------|---------------|-----|
| Thread started in `serve()` | Writer lifecycle tied to reader | Extract to independent daemon |
| `os.fork()` with no Windows path | Platform assumption | Add `sys.platform == "win32"` branch |
| Heartbeat check is `file.exists()` only | Liveness illusion | Add `os.kill(pid, 0)` check |
| Only ONE table has a writer | Coverage incomplete | Audit ALL tables the reader queries |
| No `-- Source:` comment on schema | Writer unknown to future developers | Add source comment to every table |
| Start/stop/status not implemented | Lifecycle not managed | Add all three before any other code |
| "It works on my machine" | Platform blindspot | Test on Mac + Linux + Windows |
| No PID file | Crash detection impossible | Add PID file + heartbeat |
| Try/except with bare `except:` | Unknown errors swallowed | Use specific exception types |

---

## Appendix C: Template — Architecture Decision Record

Copy this into every infrastructure PR:

```markdown
## ADR: [Feature Name]

### Context
[Map the data pipeline. Who writes? Who reads? What tables?]

### Options
1. [Option A] — [pros/cons]
2. [Option B] — [pros/cons]

### Decision
[Chosen option and why]

### Failure Modes
- Crash: [recovery mechanism]
- Stale data: [UI behavior]
- Double-start: [prevention]
- Orphan PID: [detection]

### Cross-Platform
| Concern | POSIX | Windows |
|---------|-------|---------|
| Creation | | |
| Stop | | |
| Liveness | | |
| Auto-start | | |

### Tables Written
| Table | Writer | Frequency | Auto? |
|-------|--------|-----------|-------|

### Tables NOT Written (gaps)
| Table | Why | Issue |
|-------|-----|-------|

### Lens Scores
1. Lifecycle Independence: ___/5
2. Coverage Completeness: ___/4
3. Crash Resilience: ___/5
4. Liveness Accuracy: ___/5
5. Cross-Platform Parity: ___/5
6. Startup Grace: ___/5
7. Defensive Coding: ___/5
8. Observability & Debuggability: ___/5
9. Scalability & Multi-Instance Safety: ___/5
**Total:** ___/45 (target ≥32)
```

---

## Lessons Learned

| Date | Project | What happened | Root cause | Pattern | Fix applied |
|------|---------|---------------|-----------|---------|-------------|
| 2026-06-09 | ObserveCo | Stripe payment success → Pro not activated — 3 independent bugs (session ID, encryption, trial start) | Payment pipeline treated as single state instead of 3-sub-state machine | Pattern 8 | Added payment pipeline state machine to system design template |
| 2026-06-12 | ObserveCo | Migration infra audit claimed 3 HIGH open → all 4 were already fixed in code. Summary was stale. | Stale audit summary doesn't match implementation state | Pattern 9 | Added migration infrastructure test matrix (24 tests). Always verify audit findings against current code before reporting status. |

*Failure today taught us that the code can be correct and the system can still be wrong. This playbook bridges that gap — forcing the system-level analysis BEFORE the code, and verifying the system-level properties AFTER the code.*
