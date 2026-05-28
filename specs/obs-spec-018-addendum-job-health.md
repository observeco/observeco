# obs-spec-018: Addendum A — Job Health Lane

**Spec ID:** obs-spec-018 / Addendum A
**Author:** Main (per Sean direction 2026-05-28)
**Status:** Draft
**Extends:** `specs/obs-spec-018-crash-classification.md`
**Location:** `specs/obs-spec-018-addendum-job-health.md`

---

## §1 One-Liner

The crash classification dashboard (obs-spec-018) covers **daemon health** — processes that crash and restart. It does NOT cover **job health** — scheduled tasks that run successfully but produce bad/empty/stale output. This addendum adds a fourth dashboard lane for job-health failures: silent successes that crash classification never catches.

---

## §2 Why

### 2.1 The Gap

Three real incidents from 2026-05-28 demonstrate the gap:

| Incident | Exit Code | Crash | Error Log | Alert | Duration |
|----------|-----------|-------|-----------|-------|----------|
| Travel Dec/Jan JSON parser bug | 0 ✅ | No | No | None | ~7 days (since job creation) |
| Cron metadata stale for agent jobs | 0 ✅ | No | No | None | ~10 days (since provider degradation) |
| Eval gate always 0.0 | 0 ✅ | No | No | None | Unknown (provider-dependent) |

All three are **silent successes** — code ran, returned 0, no crash, no error log, no alert. The existing crash-classification dashboard would show "no daemon restarts" and mark everything green while these jobs produced garbage for weeks.

### 2.2 Why This Happens

Jobs and daemons have different failure modes:

| Dimension | Daemon | Batch Job |
|-----------|--------|-----------|
| Failure signal | Exit code ≠ 0, crash log, OOM | Exit code = 0, output is wrong |
| Detection | Immediate (launchd/launchctl) | Deferred (must inspect output content) |
| Recovery | Auto-restart (launchd KeepAlive) | Next scheduled run (if ever fixed) |
| Observability | Crash logs, uptime metrics | Output size, metric variance, run frequency |

A system that monitors daemons but not jobs has a blind spot the size of its cron schedule.

### 2.3 Complete Silent-Failure Taxonomy

A cron job can fail silently in **16 distinct ways** — exit code 0, no crash, but the work didn't happen or produced bad data:

| # | Failure Class | What Happens | Detection Signal | Auto-Healable? |
|---|--------------|--------------|------------------|----------------|
| 1 | Empty output | Job exits 0, writes 0 bytes or empty array | Output size < threshold | ✅ Re-run |
| 2 | Stale output | Job re-produces exact same content as last run | Output hash == previous hash | ✅ Re-run with fresh flag |
| 3 | Corrupt output | Output is malformed (invalid JSON, truncated) | Schema validation | ✅ Re-run |
| 4 | Error in output | Output contains error text ("403", "rate limit") | String match on known patterns | ✅ Re-run + backoff |
| 5 | Wrong output path | Job writes to old/incorrect location | Expected file doesn't exist at canonical path | ❌ Config fix |
| 6 | Silent data regression | Output structure changed (API response format drift) | Schema validation vs expected schema hash | ❌ Code fix |
| 7 | Volume collapse | Output volume drops significantly vs historical baseline | Output size < 20% of 14-day rolling median | ✅ Re-run |
| 8 | Progressive shrinkage | Output shrinks N% per run over trend window | Linear regression slope < threshold | ❌ Investigate |
| 9 | Latency degradation | Job takes significantly longer (but still within timeout) | Run duration > 2× rolling median | ✅ Re-run with force |
| 10 | Output duplication | Same data processed multiple times | Output hash match across >2 consecutive runs | ❌ Idempotency fix |
| 11 | Schedule slippage | Job doesn't run when expected | `last_run_at` > 2× interval + tolerance | ✅ Force-run |
| 12 | Concurrent overlap | Two runs of same job in-flight simultaneously | Lock file conflict or overlapping timestamps | ✅ Kill + single re-run |
| 13 | Cascading dependency | Job A produced bad data, Job B consumed it without validation | Cross-job output hash chain | ❌ Break the chain |
| 14 | Temp-file leak | Job leaves orphan temp files each run | Temp directory growth > expected cleanup rate | ✅ Auto-cleanup |
| 15 | Zombie subprocesses | Job spawns children that outlive the parent | Child processes owned by job PID tree still alive | ✅ Kill + re-run |
| 16 | Config/environment drift | Job uses wrong config (old API key, stale path) | Config hash != expected config hash at job start | ❌ Re-deploy config |

---

## §3 Detection Signal Types

### Type A: Empty Output

**What it catches:** Jobs that exit 0 but produce consistently empty or trivial output for their type. (#1 in taxonomy)

**Detection logic:**
```
For each job, define expected_output_min_bytes (configurable per job):
  If output_size < expected_output_min_bytes for 2+ consecutive runs:
    → flag: empty_output_job
    → severity: High (data loss risk)
    → auto-heal: Restart job immediately with retry flag
```

**False positive guard:** Require 2 consecutive runs below threshold. A single empty run on a scraping job could be a legitimately empty day (no deals available). Two in a row is probable failure.

**Per-job config example:**
```toml
[job.expected_output]
travel_deals_scraper = 256     # minimum 256 bytes (empty array is ~40 bytes)
eval_gate = 8                   # minimum 8 bytes (score 0.0 is "0.0" = 3 bytes)
daily_digest = 512              # minimum 512 bytes
```

**Existing incidents this would have caught:**
- Travel Dec/Jan → `expected_output_min_bytes = 256`, output was 0 bytes every day → flagged on 2nd run

---

### Type B: Stale Output (Output Hash Match)

**What it catches:** Jobs that produce the exact same output as their last run, indicating no new data was processed or the source didn't refresh. (#2 in taxonomy)

**Detection logic:**
```
For each job, store output_content_hash (SHA256 of stdout/stderr):
  If output_content_hash == previous_output_content_hash for 2+ consecutive runs:
    → flag: stale_output_job
    → severity: Medium (data staleness risk — job ran but produced nothing new)
    → auto-heal: Re-run with FRESH_SOURCE=1 flag (skips any local cache)
```

**False positive guard:** Some jobs legitimately produce identical output (e.g., a static health check that always returns "OK"). Exclude via `allow_identical_output = true` in job config.

**Edge cases:**
- **Timestamp in output:** If job includes a timestamp in every run, hashes never match. Use content-normalized hash (strip timestamps, run IDs, session numbers before hashing) or skip hash detection for such jobs.
- **Deterministic but correct:** A job that processes N input files and produces identical output because the input didn't change is healthy, not stale. Cross-reference with input-change detection: if input files haven't changed, identical output is expected. Only flag if output matches AND input has changed.

**Existing incidents this would have caught:**
- Eval gate producing 0.0 → every run produced the same JSON `{"score": 0.0}` with identical hash → flagged after 2 runs instead of waiting 14 days

---

### Type C: Corrupt Output (Schema Validation)

**What it catches:** Jobs that produce output with correct size but malformed content — invalid JSON, truncated output, encoding issues. (#3 in taxonomy)

**Detection logic:**
```
For each job, define an expected output schema:
  If output is JSON:
    Parse with json.loads(). If parse fails → flag: corrupt_output_job
    If parse succeeds but is truncated (missing closing bracket/brace) → flag: truncated_output_job
  If output is plain text:
    Check for known truncation signatures (last line incomplete, no trailing newline on expected-format jobs)
  If output is structured (CSV, TSV):
    Check row count consistency, column alignment, field count per row
```

**Severity:** High (produced output IS bad — may have already been consumed by downstream jobs)

**Auto-heal:** Re-run job with `OBERVECO_RETRY=1`. If re-run produces valid output, log auto-healed. If also corrupt → escalate (root cause is in the job logic, not transient).

**Schema registry:** Schemas defined per job in config:
```toml
[job.schema]
travel_deals_scraper = "json"        # Must parse as valid JSON
eval_gate = "json"                    # Must parse as valid JSON
daily_metric_report = "csv:5"         # Must be CSV with 5 columns
system_snapshot = "yaml"              # Must parse as valid YAML
```

**Detection depth:**
- **L0 (basic):** Check if file parses at all (json.loads, yaml.safe_load). Catches catastrophic corruption.
- **L1 (structural):** Check field types and required keys exist. Catches API format drift.
- **L2 (semantic):** Check value ranges (no negative timestamps, no N/A where numeric expected). Catches silent regression.

**Existing incidents this would have caught:**
- Travel Dec/Jan JSON parser bug → scraper output was a multi-line JSON, batch runner only read one line → the full output was valid JSON but the partial read was not → Type C would catch the parse failure on the read side

---

### Type D: Error Content in Output

**What it catches:** Jobs that run successfully but embed error text in their output instead of data — API rate limit messages, HTTP 403/500 pages, timeout errors. (#4 in taxonomy)

**Detection logic:**
```
For each job, define error_patterns (list of regex patterns that should NEVER appear in output):
  If any pattern matches output content:
    → flag: error_in_output_job
    → severity: High (data is polluted, downstream consumers get garbage)

Default error patterns (apply to all jobs unless overridden):
  - "rate limit"|"rate_limit"|"429"
  - "403 Forbidden"|"401 Unauthorized"|"Access Denied"
  - "500 Internal Server Error"|"502 Bad Gateway"|"503 Service Unavailable"
  - "timeout"|"timed out"|"TimedOut"
  - "error"|"Error"|"ERROR" (if frequency > 1% of output characters — avoid flagging normal English)
  - "null" (if output is JSON and value frequency anomalously high)
```

**False positive guard:**
- **Language-dependent:** "error" in natural language text is normal. Only flag if error-pattern density exceeds a threshold (e.g., >3 error-related lines in 100 lines of output, or error text >5% of total output size).
- **Expected errors:** Some APIs return error content for legitimate states (e.g., "no results found"). Per-job exclusion list overrides the defaults.

**Auto-heal:** Re-run job with exponential backoff (30s → 60s → 120s) to handle transient API throttling. Max 3 retries before escalating.

**Existing incidents this would have caught:**
- Any scraper whose API returned "403 Forbidden" but the scraper logged it and produced an empty results array — the error text would be in the log but not the output. **This detector needs both output AND log scanning.**

---

### Type E: Volume Collapse (Trend Detection)

**What it catches:** Jobs whose output volume drops significantly below their own historical baseline — not a fixed threshold, but a behavioral anomaly. (#7 in taxonomy)

**Detection logic:**
```
For each job, track output_size over a 14-day rolling window:
  rolling_median = median(output_sizes[-14:])
  rolling_iqr = percentile(output_sizes[-14:], 75) - percentile(output_sizes[-14:], 25)
  lower_bound = rolling_median - 3 * rolling_iqr
  
  If output_size < lower_bound AND output_size < rolling_median * 0.2:
    → flag: volume_collapse_job
    → severity: High (output is 80%+ below normal)
    → auto-heal: Re-run job. If re-run normal, log `transient_volume_collapse`.
```

**Why median + IQR instead of mean + stddev:** Output sizes often have a skewed distribution (most days ~50 records, occasional spike of 200). Median + IQR is robust to these spikes — it measures "normal range" without being dragged upward by outliers.

**Minimum data requirement:** Skip detection until 7 samples collected (allows new jobs to establish baseline).

**False positive guard:** Skip days where a dependent upstream job was known to be broken (cascading flag). A scraper producing 0 results when its data source was down is a symptom, not a root cause.

---

### Type F: Progressive Shrinkage

**What it catches:** Jobs whose output size trends downward over time — not a sudden collapse, but a death by a thousand cuts. (#8 in taxonomy)

**Detection logic:**
```
For each job, track output_size over a 28-day window:
  Compute linear regression: output_size ~ day
  slope = coefficient of day
  If slope < 0 (negative) AND |slope| > threshold (e.g., -1% of baseline per day):
    → flag: progressive_shrinkage_job
    → severity: Medium (gradual degradation — fixable before collapse)
```

**Example:** A job that processed 200 rows/day last month now processes 150 — not a collapse, but a 25% drop over 4 weeks. By the time it hits Type E threshold, it's been broken for weeks.

**Auto-heal:** None — progressive shrinkage is a structural issue (deprecating API, reduced data source, config drift). Flag to Hound for investigation.

---

### Type G: Latency Degradation

**What it catches:** Jobs that still complete within their timeout but take significantly longer than their normal execution time. (#9 in taxonomy)

**Detection logic:**
```
For each job, track run_duration_seconds over a 7-day window:
  rolling_median = median(durations[-7:])
  rolling_mad = median(|d_i - rolling_median| for d_i in durations[-7:])  # Median Absolute Deviation
  
  If run_duration > rolling_median + 3 * rolling_mad:
    → flag: latency_degradation_job
    → severity: Medium (transient) / High (if sustained 2+ runs)
    → auto-heal (transient): Re-run job. If faster, log `transient_latency_spike`.
    → no auto-heal (sustained): Flag to Hound with duration history.
```

**Why MAD instead of stddev:** Like IQR, MAD is robust to outliers. A single 30-minute run doesn't inflate the threshold and cause false negatives on the next run.

**Correlation with other signals:** A latency degradation that coincides with volume collapse (Type E) suggests a source API is throttling or degrading. A latency spike alone suggests local system load (disk I/O, memory pressure, competing cron jobs).

---

### Type H: Output Duplication

**What it catches:** Jobs that produce the exact same output for 3+ consecutive runs, suggesting data is being processed multiple times without deduplication. (#10 in taxonomy)

**Detection logic:**
```
For each job, maintain a rolling window of last 5 output_content_hashes:
  If all 5 hashes are identical AND input files/db state changed between runs:
    → flag: output_duplication_job
    → severity: High (idempotency failure — same data processed repeatedly)
```

**Key distinction from Type B (Stale Output):** Type B flags identical output on 2 consecutive runs and auto-heals via re-run. Type H flags 5 consecutive identical runs even after re-runs succeed — it's a **persistent idempotency problem**, not a transient one.

**Auto-heal:** ❌ Cannot auto-heal. If re-running doesn't change the output, the job's logic is at fault (not consuming the right input, not marking consumed flags, etc.).

---

### Type I: Concurrent Overlap

**What it catches:** Two instances of the same cron job running simultaneously — indicates the FIFO lock is not held, the duration exceeded the schedule interval, or the scheduler started a new run before the previous one finished. (#12 in taxonomy)

**Detection logic:**
```
For each job, track running_instances:
  If running_instances > 1:
    → flag: concurrent_overlap_job
    → severity: High (data corruption risk — two jobs writing same output)
    → auto-heal: Kill the newest instance. Allow the original to complete.
```

**Detection method:**
1. PID file: Job writes its PID to a well-known location on start, removes it on exit. Detector checks if PID file exists AND process is alive.
2. Cron scheduler cross-ref: If `last_started_at < last_completed_at + grace_period`, a new run started before the previous one finished.
3. Output file timestamps: If output file `mtime` changed during a run that shouldn't overlap with another, flag it.

**False positive guard:** Some jobs legitimately overlap (watchdog patterns that tail and re-process). Exclude via `allow_concurrent = true`.

---

### Type J: Cascading Dependency

**What it catches:** Job B consuming bad output from Job A. (#13 in taxonomy)

**Detection logic:**
```
Define job dependency graph:
  If Job A's output is flagged (Types A-H), check all jobs that depend on it:
    For each dependent job D:
      Check D's last_run_at against A's last_failure_at
      If D ran after A's failure AND D produces output matching A's pattern of failure:
        → flag: cascading_failure (A → D)
        → severity: Critical (compound failure)
```

**Auto-heal:** ❌ Cannot auto-heal the downstream — re-running D on bad A data produces the same bad result. Auto-heal A first, then re-run D after A is confirmed healthy.

**Implementation consideration:** Dependency graph needs to be declared (implicit detection via output hash matching is unreliable). Add `[job.depends_on]` to job config:
```toml
[job.depends_on]
daily_aggregator = ["travel_deals_scraper", "news_monitor"]
weekly_report = ["daily_aggregator"]
```

---

### Type K: Temp/Resource Leak

**What it catches:** Jobs that leave orphan temp files, zombie subprocesses, or unreleased resources each run — accumulating over time without crashing. (#14/15 in taxonomy)

**Detection logic (temp files):**
```
For each job, define expected_temp_directory:
  Count orphan files (files in temp dir with mtime older than most recent job run + 1h):
  If orphan_count > max_expected_orphans (default: 5):
    → flag: temp_file_leak_job
    → severity: Low → Medium (escalates if accumulated over 5+ checks)
    → auto-heal: Clean orphan files older than 24h
```

**Detection logic (zombie subprocesses):**
```
For each job, scan process tree for children of the job's main PID:
  If job has exited (no main PID) but child processes remain:
    → flag: zombie_subprocess_job
    → severity: Medium (resource accumulation)
    → auto-heal: Kill orphaned child processes
```

**Safety:** Auto-cleanup only applies to temp files >24h old (prevents cleaning files still in use by a long-running job). Auto-kill only applies to processes whose parent exited >5m ago (prevents killing grandchildren that re-parented to init legitimately).

---

### Type L: Config/Environment Drift

**What it catches:** Jobs that use wrong configuration — stale API keys, rotated credentials, deprecated endpoints, mismatched environment. (#16 in taxonomy)

**Detection logic:**
```
For each job, record config_hash (SHA256 of all config files the job loads at startup):
  If config_hash != expected_config_hash (recorded when job was last healthy):
    → flag: config_drift_job
    → severity: Medium (may cause gradual degradation before collapse)
```

**Detection triggers:**
- **Passive:** Job writes a `config_used` marker to its output or a sidecar file. Detector compares hashes.
- **Active:** Detector reads the job's config file and compares `mtime` — if it changed since last run, re-compute hash and compare.

**Auto-heal:** ❌ Cannot auto-heal — config changes are intentional or require human decision. Flag to Hound with `old_hash` and `new_hash` for investigation.

---

### Type M: Wrong Output Location

**What it catches:** Jobs that write output to an unexpected path — code change redirected output but the monitoring pipeline still reads from the old path. (#5 in taxonomy)

**Detection logic:**
```
For each job, define canonical_output_path:
  Check if canonical_output_path exists and has mtime matching latest run:
  If file doesn't exist OR mtime is older than latest run:
    Search for files created by this job that match expected filename pattern
    Search for recently modified files matching this job's content signature
    If found at different path:
      → flag: output_path_drift_job
      → severity: High (data being produced but not consumed)
```

**Auto-heal:** ❌ Cannot auto-heal — redirecting the pipeline to the new path may not be safe (the new output may have a different format).

---

### Type N: Schedule Anomaly

**What it catches:** Jobs running at the wrong time (timezone drift, DST edge case, clock sync issue) or jobs that should have run multiple times but ran only once (#11 variant).

**Detection logic:**
```
For each job, record expected_time_of_day:
  If abs(run_hour - expected_hour) > schedule_tolerance_hours:
    → flag: schedule_anomaly_job
    → severity: Medium (may cause data to be stale for the wrong period)
```

**Also catch:** Jobs that run N times/day but only produced M < N outputs on a given day. Cross-reference expected frequency vs actual output files per calendar day.

---

## §4 Dashboard — Job Health Lane

### 4.1 Dashboard Integration

Add a **fourth lane** to the crash classification dashboard, between TOCTOU and Crash:

| Lane | Color | What It Shows | Example |
|------|-------|---------------|---------|
| Healthy Restart | 🟢 | launchd KeepAlive, sub-second | Normal watcher restart |
| TOCTOU Race | 🟡 | File consumed before .stat() | pragma_acps_watcher |
| **Job Health** | **🟠** | **Silent successes — all 14 types** | **JSON parser bug, stuck 0.0 score, volume collapse** |
| Crash | 🔴 | SIGSEGV, OOM, config dead | Process death |

### 4.2 Per-Job Health Card

Each card shows:
- **Job name** + schedule frequency
- **Status badge:** 🟢 Healthy / 🟠 Degraded / 🔴 Critical
- **Signal type indicators:** Letter codes for active signals (A=empty, B=stale, C=corrupt, D=error content, E=volume collapse, F=shrinkage, G=latency, H=duplication, I=overlap, J=cascade, K=leak, L=config drift, M=wrong path, N=schedule anomaly)
- **Duration:** How long the issue has persisted (in runs or days)
- **Last known good:** Timestamp of last healthy run
- **Auto-heal status:** ✅ Auto-healed / ⏳ Pending retry / ❌ Manual required

### 4.3 Fleet Heatmap

A compact view showing all active jobs as a grid:

```
Job Name          | Status | Signals              | Duration | Auto-Heal
──────────────────┼────────┼──────────────────────┼──────────┼─────────
Travel Deals      | 🔴     | A C D                | 7d       | ❌ Manual
Eval Gate         | 🔴     | B                    | 28d+     | ❌ Manual
Daily Aggregator  | 🟠     | G                    | 2h       | ✅ Auto-retry
News Monitor      | 🟢     | —                    | —        | —
System Cleanup    | 🟠     | K (3 orphan files)   | 5d       | ✅ Auto-clean
```

### 4.4 Card Detail (Expandable)

Click a job → expand shows:
- **Last 5 runs:** Timestamp, duration, output size, exit code, hash
- **Active signals:** List of active issue types with detection timestamp, severity, confidence level
- **Dependency chain:** Upstream inputs + downstream consumers (with health status of each)
- **Trend chart:** Output size over 14 days (bar chart: green=healthy, orange=shrinkage, red=volume collapse)
- **Auto-heal log:** History of auto-heal actions taken (timestamp, action, outcome)

### 4.5 Tiering

| Signal Type | Free | Pro |
|-------------|------|-----|
| Empty output (Type A) | Count only | ✅ Per-job threshold, auto-heal retry |
| Stale output — hash match (Type B) | Count only | ✅ Content-normalized hash, stale-only detection |
| Corrupt output — schema (Type C) | ❌ | ✅ L0+L1 schema validation, auto-retry |
| Error content (Type D) | ❌ | ✅ Per-job pattern config, auto-retry with backoff |
| Volume collapse — trend (Type E) | ❌ | ✅ 14-day IQR baseline, outlier detection |
| Progressive shrinkage (Type F) | ❌ | ✅ 28-day linear regression, trend alert |
| Latency degradation (Type G) | ❌ | ✅ MAD-based spike detection, per-job thresholds |
| Output duplication (Type H) | ❌ | ✅ 5-run sliding window, idempotency check |
| Concurrent overlap (Type I) | ❌ | ✅ PID file checker, auto-kill new instance |
| Cascading dependency (Type J) | ❌ | ✅ Dependency graph, chain-trace alert |
| Temp/process leak (Type K) | ❌ | ✅ Orphan file counter, zombie process scan |
| Config drift (Type L) | ❌ | ✅ Config hash comparison, drift alert |
| Wrong output path (Type M) | ❌ | ✅ Canonical path check, path scan |
| Schedule anomaly (Type N) | ❌ | ✅ Time-of-day check, frequency cross-ref |
| Auto-heal actions | ❌ | ✅ All healable types (A-G, I, K) |

---

## §5 Auto-Heal Matrix

### 5.1 Per-Type Auto-Heal

| Type | Auto-Heal Action | Safety Limit | Escalation After Limit |
|------|-----------------|-------------|----------------------|
| A — Empty output | Re-run with `OBERVECO_RETRY=1` | 2 retries/h per job | Flag `empty_output_loop` |
| B — Stale output | Re-run with `FRESH_SOURCE=1` | 2 retries/h per job | Flag `stale_output_loop` |
| C — Corrupt output | Re-run with `OBERVECO_RETRY=1` | 3 retries/h per job | Flag `corrupt_output_loop` |
| D — Error content | Re-run with exponential backoff (30s→60s→120s) | 3 retries total | Flag `error_output_loop` |
| E — Volume collapse | Re-run. If normal, log transient | 1 re-run per job | Flag `volume_collapse_persistent` |
| G — Latency spike (transient) | Re-run | 1 re-run per job | Flag `latency_degradation_sustained` |
| I — Concurrent overlap | Kill newest instance | 1 kill per 5m per job | Flag `overlap_loop` |
| K — Temp leak | Clean orphans >24h old | Per directory | Flag if leak persists 5+ checks |
| K — Zombie processes | Kill children with parent exited >5m | Per process tree | Flag if >10 zombies in 1h |
| F, H, J, L, M, N | ❌ Cannot auto-heal — structural issue | N/A | Flag to Hound for investigation |

### 5.2 Combined Safety Limits

| Dimension | Limit | After Limit |
|-----------|-------|-------------|
| Max auto-heal actions per system per hour | 10 total | Write `auto_heal_storm` to Hound |
| Max auto-heal actions per job per hour | 3 per type | Stop retrying, escalate |
| Max concurrent auto-heal actions | 5 (single-threaded queue) | Queue remaining, no skip |
| Max times a job can be auto-healed before forced human review | 5 per 24h | Write `auto_heal_frequent` to Main |

### 5.3 Cascading Auto-Heal

When a job is auto-healed successfully:
1. Check dependency graph for downstream consumers
2. For each downstream that last consumed the (now-known-bad) data:
   - Re-run downstream job(s) once
   - Log `cascading_heal: parent_healed → child_rerun`
3. Do NOT recursively cascade beyond 1 level — if downstream fails again, that's its own problem

---

## §6 Data Model

### 6.1 New Table: `job_health`

Appended to `pulse.db`:

```sql
CREATE TABLE IF NOT EXISTS job_health (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT NOT NULL,
    signal_type TEXT NOT NULL,  -- NOT a CHECK constraint — signal types grow over time
    severity TEXT NOT NULL CHECK(severity IN ('low', 'medium', 'high', 'critical')),
    value_observed TEXT,        -- the value that triggered detection (output_size, duration, etc.)
    baseline_value TEXT,        -- normal/comparison value (threshold, median, expected_min)
    auto_healed INTEGER DEFAULT 0,
    healed_at INTEGER,
    escalated INTEGER DEFAULT 0,
    details TEXT,               -- JSON: additional context per type
    timestamp INTEGER NOT NULL
);

CREATE INDEX idx_job_health_job ON job_health(job_id, timestamp);
CREATE INDEX idx_job_health_active ON job_health(job_id, auto_healed, escalated);
```

`signal_type` is a free-text field (not constrained) because the taxonomy will grow. Current valid values: `empty_output`, `stale_output`, `corrupt_output`, `error_in_output`, `volume_collapse`, `progressive_shrinkage`, `latency_degradation`, `output_duplication`, `concurrent_overlap`, `cascading_failure`, `temp_file_leak`, `zombie_process`, `config_drift`, `output_path_drift`, `schedule_anomaly`.

### 6.2 New Table: `heal_state`

Tracks auto-heal history for safety limits:

```sql
CREATE TABLE IF NOT EXISTS heal_state (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT NOT NULL,
    signal_type TEXT NOT NULL,
    action_type TEXT NOT NULL CHECK(action_type IN ('retry', 'force_run', 'repoll', 'kill', 'cleanup')),
    succeeded INTEGER DEFAULT 0,
    output_hash_after TEXT,     -- hash of output after heal, for verification
    duration_ms INTEGER DEFAULT 0,
    timestamp INTEGER NOT NULL
);
```

### 6.3 New Table: `job_metadata`

Records per-job baseline data for trend detection:

```sql
CREATE TABLE IF NOT EXISTS job_metadata (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT NOT NULL,
    output_size INTEGER DEFAULT 0,
    output_hash TEXT,
    run_duration_ms INTEGER DEFAULT 0,
    config_hash TEXT,           -- hash of job's config at time of run
    temp_file_count INTEGER DEFAULT 0,
    exit_code INTEGER DEFAULT 0,
    timestamp INTEGER NOT NULL
);

CREATE INDEX idx_job_metadata_job ON job_metadata(job_id, timestamp);
```

### 6.4 New Table: `job_dependency_graph`

Declares which jobs depend on which:

```sql
CREATE TABLE IF NOT EXISTS job_dependency_graph (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    parent_job_id TEXT NOT NULL,
    child_job_id TEXT NOT NULL,
    UNIQUE(parent_job_id, child_job_id)
);
```

---

## §7 Integration Points

### 7.1 ObserveCo Product

| Component | Change | Priority |
|-----------|--------|----------|
| `src/observeco/pulse/check.py` | Add job health check step after daemon check | P1 |
| `src/observeco/db.py` | Add 4 new tables + migration | P1 |
| `src/observeco/cron/` | New `job_health_collector.py` — reads cron output sizes, hashes, durations, schema | P1 |
| `src/observeco/cron/` | New `job_health_detector.py` — runs all 14 detection types against collected data | P1 |
| `src/observeco/heal.py` | Add auto-heal methods for types A-E, G, I, K | P1 |
| `src/observeco/dashboard/server.py` | Add Job Health lane endpoint + htmx panel + fleet heatmap | P1 |
| `src/observeco/snapshot.py` | Add job health to weekly snapshot | P2 |
| `src/observeco/cli.py` | Add `observeco job-health --list` and `--detail <job_id>` commands | P2 |
| `src/observeco/config/` | New schema for per-job health config (output thresholds, error patterns, schema defs) | P1 |
| `src/observeco/cron/` | New `cascading_recovery.py` — re-runs downstream jobs after parent auto-heal | P2 |

### 7.2 Ecosystem (Hermes)

| Component | Change | Priority |
|-----------|--------|----------|
| `~/.hermes/scripts/` | New `metric_job_output_size.py` — reports output sizes per job to metrics pipeline | P1 |
| `~/.hermes/scripts/` | New `metric_job_duration.py` — reports run durations per job | P1 |
| `~/.hermes/scripts/` | New `metric_job_output_hash.py` — reports content hashes for stale detection | P1 |
| `~/.hermes/cron/jobs/*.toml` | Add `[job.health]` section to each job for monitoring config | P2 |
| `~/.hermes/standards/GS-013.md` | Add job-health metrics to core metrics table | P1 (see §9) |
| `~/.hermes/standards/GS-014.md` | Add job health exceptions to classification table | P1 (see §9) |
| `~/.hermes/standards/GS-009.md` | Add job-health tracking to work operations | P3 |

---

## §8 Estimated Effort

~7-10 days total for full implementation:

| Phase | Scope | Effort |
|-------|-------|--------|
| **Phase 1 — Core** | DB (4 tables), 3 collector scripts (output size, hash, duration), L0 schema detection (Type C) | 2 days |
| **Phase 2 — Detection** | All 14 detector types, config schema, per-job config files | 4 days |
| **Phase 3 — Auto-Heal** | All healable types (A-E, G, I, K), safety limits, heal state tracking | 2 days |
| **Phase 4 — Dashboard** | Job Health lane, fleet heatmap, card detail view, trend charts | 3 days |
| **Phase 5 — Ecosystem** | Hermes metric scripts, cron configs, GS-013/GS-014 updates | 1 day |
| **Phase 6 — Cascading** | Dependency graph, cascading recovery | 1 day |
| **Total** | | **~13 days** |

---

## §9 Edge Cases & Failure Mode Registry

| Scenario | Handling |
|----------|----------|
| Job produces empty output on first run ever | Skip Type A — job may need sample data. Flag only after 2+ consecutive empty runs. |
| Job produces same output because input hasn't changed | Cross-reference input mtime/hash. If input unchanged, identical output is healthy. Flag only if input changed AND output unchanged. |
| Job output includes dynamic content (timestamps, run IDs) | Content-normalized hash: strip known-dynamic fields before hashing. Declare strippable patterns per job config. |
| Weekly job has no recent data (Monday audit on Sunday) | Type N checks schedule interval (168h = weekly), not wall-clock days. |
| Auto-heal cascades: Type A triggers force-run, which triggers Type B detection | Auto-heal actions excluded from detection for the same job+type within same cycle. |
| Multi-job failure at same time (network outage) | Write `batch_failure` flag instead of N individual flags. Group by common cause. Detect via timestamp clustering. |
| Job config has no health thresholds | Default to skip detection for that type. Opt-in per job per type. |
| Cron scheduler is completely dead | Job health collection script also doesn't run — this is a platform-level failure, not a job failure. Daemon crash dashboard detects it. |
| Detector itself crashes | Each detector runs independently. If detector A fails, detectors B-N still run. Detector failure is a daemon-level crash (covered by obs-spec-018). |
| Schema validation vs. evolving output format | Job output schema can evolve. Store schema_hash alongside config_hash. When schema_hash changes deliberately (code deploy), auto-reset schema validation expectations. |
| Very large output files (>1MB) | Hash and schema-validate the first 64KB only (sample-based detection). Full scan on demand when flagged. |
| Job that normally produces no output (cleanup scripts) | Mark `output_expected: false` in job config. Skip Type A and Type C for these jobs. |
| Zombie process that IS intentionally long-lived (daemon spawned by job) | Only flag processes whose parent exited >5m ago. Grandchildren re-parented to init are not zombies. |
| Config change is intentional (code deploy) | Config hash re-baselined automatically after a deploy. Only flag config drift when there was NO known deploy. |
| Job runs in Docker (no PID to check) | Skip Type I and Type K zombie detection for Docker jobs. Use container-level resource checks instead. |
| Dependency graph has a cycle (Job A → Job B → Job A) | Cycle detection on graph insert. Reject cycles, flag to Hound for resolution. |
| Auto-heal re-run produces same failure | Stop retrying, escalate. The failure is not transient — it's a code/config issue. |
| Multiple signal types fire for same job simultaneously | Report all active signals. Auto-heal processes in priority order: D (error content) > C (corrupt) > A (empty) > B (stale) > E (volume collapse) > G (latency) > rest. |
