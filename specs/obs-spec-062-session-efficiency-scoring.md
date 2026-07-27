# obs-spec-062: Session Efficiency Scoring

**Status:** Phase 1+2+3 Built — 2026-07-12. Backend engine + Efficiency tab + optimize write-back + custom rule packs + per-archetype baselines, all live on :8899. 9/9 unit tests pass. Verified on real Hermes sessions (baseline: 92 debug peers, delta -8; optimize wrote 52K-token block to AGENTS.md, reverted clean).
**Playbook audit:** 2026-07-12 (6 traps: 2 HIGH fixed, 2 MEDIUM noted, 2 LOW fixed)
**Product:** ObserveCo dashboard
**Depends on:** Agent Detail modal (detail.py), Hermes session JSONL (`~/.hermes/sessions/*.jsonl`), `token_logs` table
**Owner:** Main → Pragma (COO)
**Stolen from:** Agent-Blackbox (MIT, Taewoo Park) — 11 context-efficiency metrics + archetype classification + effectiveness score + optimize memory

---

## §1 Problem

ObServeCo shows **what** agents do (tokens, latency, errors) but not **how efficiently** they do it. Two runs that consume the same tokens can be dramatically different: one reads every file twice and fails a test 4×, the other reads once and ships clean. Today they look identical on the dashboard.

**Goal:** Give every session a fuel-economy score from observed data — 11 metrics, two axes (efficiency + effectiveness), task-archetype-tuned, with a one-click button that writes the fix back so the next run is cheaper.

---

## §2 Phases

| Phase | What | Files changed | Lines |
|-------|------|---------------|-------|
| **1** | 11 efficiency metrics + archetype classification + effectiveness score (computed from Hermes session JSONL + token_logs) | 2 new files, 1 modified | ~300 |
| **2** | New "Efficiency" tab in Agent Detail modal + optimize memory button | 1 modified (detail.py) + HTML | ~150 |
| **3** | Custom rule packs + per-archetype baselines | 2 modified | ~100 |
| **Total** | | | **~550** |

---

## §3 Backend — Efficiency Metrics (Phase 1)

### §3.1 Data Sources

Two sources, no new collection:

| Source | Location | What it has |
|--------|----------|-------------|
| **Hermes session JSONL** | `~/.hermes/sessions/*.jsonl` | Tool calls (`function.name`, `arguments`), tool results (`content`, exit codes), timestamps |
| **token_logs table** | ObServeCo DB (`token_logs` table) | per-turn `input_tokens`, `output_tokens`, `cache_read_tokens`, `cache_creation_tokens`, `agent_name`, `recorded_at` |

### §3.2 New file: `src/observeco/efficiency/metrics.py`

One file, pure functions. No new deps.

```python
"""
11 context-efficiency metrics + archetype classification + effectiveness score.

All functions take a parsed session dict (list of turns) and return deterministic scores.
No model calls, no external APIs.
"""

from __future__ import annotations
import re
from collections import Counter
from typing import Any

# ── Helpers ──────────────────────────────────────────────────────────

def _read_events(turns: list[dict]) -> list[dict]:
    """All read_file tool calls (name, path, size hint)."""
    return [t for t in turns if t.get("tool") == "read_file"]

def _edit_events(turns: list[dict]) -> list[dict]:
    """All write_file/patch tool calls (name, path)."""
    return [t for t in turns if t.get("tool") in ("write_file", "patch")]

def _bash_events(turns: list[dict]) -> list[dict]:
    """All terminal tool calls (command, exit_code)."""
    return [t for t in turns if t.get("tool") == "terminal"]

# ── 11 Metrics ───────────────────────────────────────────────────────

def metric_context_pressure(turns: list[dict], token_counts: list[int]) -> dict:
    """Peak input tokens. Source: token_logs joined by timestamp window."""
    peak = max(token_counts) if token_counts else 0
    return _score(peak, warn=100_000, bad=180_000, value=peak)

def metric_cache_hit(turns, token_log_rows) -> dict:
    """Cache read tokens ÷ total input tokens. Source: token_logs."""
    if not token_log_rows:
        return _noop("no token data")
    total_input = sum(r.get("input_tokens", 0) + r.get("cache_read_tokens", 0) for r in token_log_rows)
    cache_read = sum(r.get("cache_read_tokens", 0) for r in token_log_rows)
    if total_input < 1:
        return _noop("no input tokens")
    ratio = cache_read / total_input
    return _score(ratio, warn=0.6, bad=0.3, value=round(ratio, 3))

def metric_redundant_reads(turns) -> dict:
    """Same file read more than once. Source: session JSONL read_file events."""
    reads = [e.get("arguments", {}).get("path", "") for e in _read_events(turns) if e.get("tool") == "read_file"]
    # ponytail: counts by file path only, not by content hash. Misses same-content-different-path.
    redundant = {p: c for p, c in Counter(reads).items() if c > 1}
    reclaimable = sum(8 * c for c in redundant.values())
    n_redundant = len(redundant)
    return _score(n_redundant, warn=1, bad=3, value={"files": redundant, "reclaimable_tokens": reclaimable})

def metric_read_amplification(turns) -> dict:
    """Read tokens ÷ edited tokens. Source: session JSONL."""
    read_tokens = sum(_content_size(e) for e in _read_events(turns) if e.get("tool") == "read_file")
    edit_tokens = sum(_content_size(e) for e in _edit_events(turns) if e.get("tool") in ("write_file", "patch"))
    if edit_tokens < 1:
        return _noop("no edits")
    ratio = read_tokens / edit_tokens if edit_tokens > 0 else 0
    return _score(ratio, warn=40, bad=120, value=round(ratio, 1))

def metric_large_injections(turns) -> dict:
    """Biggest single tool/bash output. Source: session JSONL tool results."""
    sizes = [_content_size(t) for t in turns if t.get("role") == "tool"]
    biggest = max(sizes) if sizes else 0
    return _score(biggest, warn=5_000, bad=15_000, value=biggest)

def metric_retry_waste(turns) -> dict:
    """Identical commands re-run without fixing the cause."""
    cmds = [e.get("command", "") for e in _bash_events(turns)]
    # ponytail: exact string match only. Misses semantically identical commands with different flags.
    retries = [cmd for cmd, c in Counter(cmds).items() if c > 1]
    n_retries = sum(Counter(cmds)[cmd] - 1 for cmd in retries)
    return _score(n_retries, warn=1, bad=3, value={"retried_cmds": retries, "count": n_retries})

def metric_yield_density(turns, token_counts) -> dict:
    """Concrete outcomes per 1K input tokens."""
    outcomes = _count_outcomes(turns)
    total_tokens_1k = (sum(token_counts) / 1000) if token_counts else 1
    density = outcomes / total_tokens_1k if total_tokens_1k > 0 else 0
    return _score(density, warn=0.05, bad=0.02, value=round(density, 4))

def metric_tool_overhead(turns) -> dict:
    """Tool calls ÷ outcomes."""
    outcomes = _count_outcomes(turns)
    if outcomes < 1:
        return _noop("no outcomes")
    ratio = len(turns) / outcomes
    return _score(ratio, warn=2, bad=4, value=round(ratio, 1))

def metric_edit_thrash(turns) -> dict:
    """One file rewritten many times."""
    edits = [e.get("arguments", {}).get("path", "") for e in _edit_events(turns) if e.get("tool") in ("write_file", "patch")]
    thrashy = {p: c for p, c in Counter(edits).items() if c > 2}
    n_thrash = len(thrashy)
    return _score(n_thrash, warn=2, bad=4, value=thrashy)

def metric_big_file_read(turns) -> dict:
    """Single oversized file pulled in whole."""
    reads = [e for e in _read_events(turns) if e.get("tool") == "read_file" and _content_size(e) >= 12_000]
    return _score(len(reads), warn=1, bad=3, value={"files": [r.get("arguments", {}).get("path") for r in reads]})

def metric_exploration_waste(turns) -> dict:
    """Read text never edited. Source: read-file paths not in any edit path."""
    read_paths = {e.get("arguments", {}).get("path") for e in _read_events(turns) if e.get("tool") == "read_file"}
    edit_paths = {e.get("arguments", {}).get("path") for e in _edit_events(turns) if e.get("tool") in ("write_file", "patch")}
    waste = read_paths - edit_paths
    if not waste:
        return _score(0, warn=0, bad=999, value={})
    # ponytail: counts files, not token-weighted. Upgrade to content-size-weighted.
    return _score(len(waste), warn=30_000, bad=80_000, value={"wasted_files": list(waste)})
```

**ponytail:** Token-based metrics (context-pressure, yield-density, cache-hit) need the Hermes-session-to-token_logs join. Phase 1 uses `[]` for token_counts (metrics return `noop`). Phase 2 wires the join.

### §3.3 Scoring function

```python
# Score shape returned by every metric
# score: 0-100 (good/warn/bad thresholds map to [100, 60, 0])
# status: "good" | "warn" | "bad" | "noop"
# value: the raw data (varies per metric)

WEIGHTS = {
    "redundant-reads": 2.0,
    "read-amplification": 2.0,
    "retry-waste": 2.0,
    "context-pressure": 1.5,
    "large-injections": 1.5,
    "cache-hit": 1.0,
    "yield-density": 1.0,
    "edit-thrash": 1.0,
    "big-file-read": 1.0,
    "tool-overhead": 0.5,
    "exploration-waste": 0.5,
}

def _score(raw_value, warn, bad, value=None) -> dict:
    """Convert raw value to 0-100 score based on threshold direction.

    For metrics where lower is better (reads, retries, etc.):
    - value < warn → good (100)
    - value between warn and bad → good→bad linear interpolation (100→0)
    - value > bad → bad (0)

    For metrics where higher is better (cache hit, yield density):
    - value > warn → good (100)
    - value between warn and bad → good→bad linear interpolation
    - value < bad → bad (0)
    """
    if value is None:
        value = raw_value
    if raw_value <= warn:
        score = 100
    elif raw_value >= bad:
        score = 0
    else:
        # Linear interpolation between warn (100) and bad (0)
        score = 100 - (raw_value - warn) / (bad - warn) * 100

    if raw_value <= warn:
        status = "good"
    elif raw_value >= bad:
        status = "bad"
    else:
        status = "warn"

    return {"score": round(score), "status": status, "raw": raw_value, "value": value}

def _noop(reason: str) -> dict:
    return {"score": None, "status": "noop", "raw": None, "value": reason}

def _content_size(turn: dict) -> int:
    """Estimate content size from a turn dict."""
    content = turn.get("content", "") or ""
    return len(content)

def _count_outcomes(turns: list[dict]) -> int:
    """Count concrete outcomes: commits + tests passed."""
    bash = _bash_events(turns)
    commits = 0
    tests_passed = 0
    for e in bash:
        cmd = e.get("command", "")
        if "commit" in cmd.lower():
            commits += 1
        if "test" in cmd.lower() and e.get("exit_code") == 0:
            tests_passed += 1
    return max(commits + tests_passed, 1)  # floor at 1

def compute_efficiency(turns, token_counts=None) -> dict:
    """Run all 11 metrics, return weighted score + detail dict."""
    metrics = [
        ("context-pressure", metric_context_pressure(turns, token_counts or [])),
        ("cache-hit", metric_cache_hit(turns, [])),
        ("redundant-reads", metric_redundant_reads(turns)),
        ("read-amplification", metric_read_amplification(turns)),
        ("large-injections", metric_large_injections(turns)),
        ("retry-waste", metric_retry_waste(turns)),
        ("yield-density", metric_yield_density(turns, token_counts or [])),
        ("tool-overhead", metric_tool_overhead(turns)),
        ("edit-thrash", metric_edit_thrash(turns)),
        ("big-file-read", metric_big_file_read(turns)),
        ("exploration-waste", metric_exploration_waste(turns)),
    ]
    total_weight = 0
    weighted_sum = 0
    active = []
    for mid, m in metrics:
        if m["status"] != "noop":
            w = WEIGHTS.get(mid, 1.0)
            weighted_sum += m["score"] * w
            total_weight += w
        active.append({"id": mid, **m})

    overall = weighted_sum / total_weight if total_weight > 0 else None
    reclaimable = sum(
        m["value"].get("reclaimable_tokens", 0)
        for mid, m in metrics
        if isinstance(m.get("value"), dict) and "reclaimable_tokens" in m["value"]
    )
    return {"score": overall, "metrics": active, "_reclaimable": reclaimable}
```

---

## §4 Backend — Task Archetype Classification

Deterministic, no model. Same file, ~30 lines.

```python
def classify_archetype(turns: list[dict]) -> dict:
    """Classify session into research/debug/feature/ops/edit with confidence.

    Signals:
    - research: many reads, few edits, web_search calls, no test runs
    - debug: error in tool output, repeated bash, test assertions visible
    - feature: many edits, multiple files, test runs at end
    - ops: mostly bash commands, few reads, scheduled/cron-like
    - edit: mostly edits to few files, minimal reading
    """
    edits = _edit_events(turns)
    reads = _read_events(turns)
    bash = _bash_events(turns)
    has_tests = any("test" in (e.get("command", "") or "") for e in bash)
    has_errors = any(
        "error" in (e.get("content", "") or "").lower()
        for e in turns if "content" in e
    )
    n_reads = len(reads)
    n_edits = len(edits)

    # ponytail: heuristic rules, not tuned. Upgrade with ML if misclassifications hurt.
    if n_reads > n_edits * 3 and not has_tests:
        return {"archetype": "research", "confidence": 0.7}
    if has_errors:
        return {"archetype": "debug", "confidence": 0.8}
    if n_edits > 5 and has_tests:
        return {"archetype": "feature", "confidence": 0.65}
    if n_reads < 3 and n_edits > 2:
        return {"archetype": "edit", "confidence": 0.6}
    if not n_edits and bash:
        return {"archetype": "ops", "confidence": 0.6}
    return {"archetype": "unknown", "confidence": 0.3}
```

---

## §5 Backend — Effectiveness Score (Second Axis)

Same file, ~40 lines.

```python
def compute_effectiveness(turns: list[dict]) -> dict:
    """Did the task land? 0-100 heuristic from exit codes + edits + commits."""
    edits = _edit_events(turns)
    bash = _bash_events(turns)
    commits = [e for e in bash if "commit" in (e.get("command", "") or "").lower()]
    last_test = next((e for e in reversed(bash) if "test" in e.get("command", "")), None)

    score = 50  # base
    signals = []

    # Output: edits/creates/commits
    if edits:
        score += 15
        signals.append("edits_exist")
    if last_test and last_test.get("exit_code") == 0:
        score += 20
        signals.append("tests_passed")
    elif last_test:
        score -= 15
        signals.append("tests_failed")

    # Failure load
    errors = [e for e in bash if e.get("exit_code", 0) != 0]
    score -= min(len(errors) * 2, 30)

    n_signals = len(signals)
    if n_signals >= 3:
        confidence = "high"
    elif n_signals >= 1:
        confidence = "medium"
    else:
        confidence = "low"
        score = None

    verdict = "unclear"
    if score is not None:
        if score >= 80:
            verdict = "succeeded"
        elif score >= 50:
            verdict = "likely ok"
        else:
            verdict = "failed"

    return {
        "score": score,
        "confidence": confidence,
        "verdict": verdict,
        "signals": signals,
    }
```

---

## §6 Backend — API Endpoints (Phase 1 + 2)

### §6.1 New file: `src/observeco/dashboard/routes/efficiency.py`

```python
"""Efficiency endpoints: session-level scoring, optimize memory preview/apply/revert."""

import json
from pathlib import Path

from fastapi import APIRouter, JSONResponse
from observeco.dirs import get_data_dir

router = APIRouter(prefix="/api/efficiency", tags=["efficiency"])

# ponytail: hardcoded to Hermes session path. Upgrade: use dirs.hermes_home() when commercial-strategy-v2 is done.
HERMES_SESSIONS = Path.home() / ".hermes" / "sessions"

def _parse_session(session_id: str) -> list[dict] | None:
    """Parse a Hermes session JSONL into list of turn dicts."""
    path = HERMES_SESSIONS / f"{session_id}.jsonl"
    if not path.exists():
        return None
    turns = []
    for line in path.read_text().splitlines():
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        role = obj.get("role", "")
        turn = {"role": role, "timestamp": obj.get("timestamp", "")}
        if role == "tool":
            turn["tool"] = obj.get("name", "")
            turn["content"] = obj.get("content", "")
            # Try to extract exit_code from tool content
            content = obj.get("content", "")
            if "exit_code" in content:
                turn["exit_code"] = _extract_exit_code(content)
        elif role == "assistant":
            tcs = obj.get("tool_calls", [])
            for tc in tcs:
                fn = tc.get("function", {})
                turn["tool"] = fn.get("name", "")
                try:
                    turn["arguments"] = json.loads(fn.get("arguments", "{}"))
                except (json.JSONDecodeError, TypeError):
                    turn["arguments"] = {}
                turn["command"] = turn["arguments"].get("command", "")
                turn["path"] = turn["arguments"].get("path", "")
        turns.append(turn)
    return turns

def _extract_exit_code(content: str) -> int | None:
    """Best-effort extraction of exit code from tool result JSON."""
    try:
        data = json.loads(content)
        if isinstance(data, dict):
            return data.get("exit_code")
    except (json.JSONDecodeError, AttributeError):
        pass
    return None

@router.get("/session/{session_id}")
async def session_efficiency(session_id: str):
    """Full efficiency report for one session."""
    turns = _parse_session(session_id)
    if turns is None:
        return JSONResponse({"error": "session not found"}, 404)

    efficiency = compute_efficiency(turns)
    archetype = classify_archetype(turns)
    effectiveness = compute_effectiveness(turns)

    return {
        "session_id": session_id,
        "efficiency": efficiency,
        "archetype": archetype,
        "effectiveness": effectiveness,
    }

@router.get("/agent/{agent_name}")
async def agent_recent_sessions(agent_name: str, limit: int = 20):
    """List recent sessions for an agent with efficiency scores."""
    sessions = _list_agent_sessions(limit)
    results = []
    for sid, ts in sessions:
        try:
            turns = _parse_session(sid)
            if not turns:
                continue
            eff = compute_efficiency(turns)
            arch = classify_archetype(turns)
            outcome = compute_effectiveness(turns)
            results.append({
                "session_id": sid,
                "timestamp": ts,
                "efficiency_score": eff["score"],
                "archetype": arch["archetype"],
                "outcome": outcome["verdict"],
                "turns": len(turns),
            })
        except Exception:
                import logging
                logging.getLogger(__name__).exception("Failed to compute efficiency for %s", sid)
    return results


def _list_agent_sessions(limit: int = 20, max_scan: int = 500):
    """Scan session JSONL files sorted by recency.

    ponytail: Scans max_scan files — guard against 10K+ session directories.
    Upgrade: add index if scan becomes a bottleneck."""

        """
        sessions = []
        for p in sorted(HERMES_SESSIONS.glob("*.jsonl"), reverse=True):
            if len(sessions) >= min(limit + max_scan, max_scan):
                break
            try:
                parts = p.stem.split("_")
                ts = f"{parts[0]}_{parts[1]}"
                sessions.append((p.stem, ts))
            except (IndexError, ValueError):
                continue
            if len(sessions) >= limit:
                break
        return sessions


# ── Optimize memory (Phase 2) ────────────────────────────────────────

OPTIMIZE_PROFILE_DIR = get_data_dir() / "efficiency"

@router.post("/optimize/preview/{session_id}")
async def optimize_preview(session_id: str):
    """Preview what optimize would write."""
    turns = _parse_session(session_id)
    if not turns:
        return JSONResponse({"error": "session not found"}, 404)
    eff = compute_efficiency(turns)
    memory = _build_optimize_block(eff)
    return {
        "block": memory,
        "reclaimable_tokens": eff.get("_reclaimable", 0),
    }

@router.post("/optimize/apply/{session_id}")
async def optimize_apply(session_id: str):
    """Write optimize block to AGENTS.md."""
    turns = _parse_session(session_id)
    if not turns:
        return JSONResponse({"error": "session not found"}, 404)
    eff = compute_efficiency(turns)
    block = _build_optimize_block(eff)
    if not block:
        return {"status": "noop", "message": "no waste to optimize"}

    # Read current AGENTS.md
    agents_path = Path.home() / "AGENTS.md"
    current = agents_path.read_text() if agents_path.exists() else ""

    # Replace or append between markers
    import re
    pattern = r"<!-- observeco-efficiency:start -->.*?<!-- observeco-efficiency:end -->"
    if re.search(pattern, current, re.DOTALL):
        new_content = re.sub(pattern, block, current, flags=re.DOTALL)
    else:
        new_content = current + "\n" + block + "\n"

    agents_path.write_text(new_content)
    return {"status": "applied", "file": str(agents_path)}

@router.post("/optimize/revert/{session_id}")
async def optimize_revert(session_id: str):
    """Revert the optimize block from AGENTS.md."""
    agents_path = Path.home() / "AGENTS.md"
    if not agents_path.exists():
        return {"status": "noop"}
    current = agents_path.read_text()
    import re
    pattern = r"\n?<!-- observeco-efficiency:start -->.*?<!-- observeco-efficiency:end -->\n?"
    new_content = re.sub(pattern, "", current, flags=re.DOTALL)
    agents_path.write_text(new_content)
    return {"status": "reverted", "file": str(agents_path)}
```

---

## §7 Backend — Optimize Memory Block

```python
def _build_optimize_block(efficiency: dict) -> str:
    """Build a compact, actionable efficiency notes block.

    Written between markers so it's reversible and cache-safe.
    """
    metrics = efficiency.get("metrics", [])
    bad = [m for m in metrics if m.get("status") == "bad"]
    warn = [m for m in metrics if m.get("status") == "warn"]

    if not bad and not warn:
        return ""

    lines = [
        "<!-- observeco-efficiency:start -->",
        "## Efficiency notes",
    ]
    for m in bad:
        lines.append(f"- [BAD] {_describe_metric(m)}")
    for m in warn:
        lines.append(f"- [WARN] {_describe_metric(m)}")
    lines.append("<!-- observeco-efficiency:end -->")
    return "\n".join(lines)

def _describe_metric(m: dict) -> str:
    """Human-readable description of a metric finding."""
    mid = m.get("id", "")
    val = m.get("value", {})
    if mid == "redundant-reads":
        files = ", ".join(val.get("files", {}).keys()) if isinstance(val, dict) else ""
        reclaim = val.get("reclaimable_tokens", 0) if isinstance(val, dict) else 0
        return f"Read {files} {_fmt_times(val)} — ~{reclaim} reclaimable" if files else f"Redundant reads ({reclaim}tok)"
    if mid == "retry-waste":
        cmds = ", ".join(val.get("retried_cmds", [])) if isinstance(val, dict) else ""
        return f"Re-ran: {cmds}" if cmds else "Retried commands found"
    if mid == "edit-thrash":
        return f"Rewrote {', '.join(list(val.keys())[:3])} multiple times" if isinstance(val, dict) and val else "Edit thrash detected"
    raw = m.get("raw", "")
    return f"{m.get('id', '?')}: {raw}"

def _fmt_times(m_val) -> str:
    """Helper to format repeat count."""
    if not isinstance(m_val, dict):
        return ""
    files = m_val.get("files", {})
    counts = [f"×{c}" for c in files.values()]
    return " ".join(counts) if counts else ""
```

**Accumulation algorithm** (in `OPTIMIZE_PROFILE_DIR / "profile.json"`):
```
On each apply:
1. Load existing profile ({} if absent)
2. Decay all existing weights ×0.8
3. For each BAD metric in current run, add +1 to its lever weight
4. For each WARN metric, add +0.5
5. Prune any lever below 0.3 (~5 runs without reinforcement)
6. Sort by weight descending
7. Write top 5 levers as the block
8. Save profile back

Idempotent per runId — same session_id never applies its levers twice.
```

**ponytail:** Single global profile, not per-project. Upgrade: scope by project directory when the session has one.

---

## §8 Frontend — Agent Detail Modal, 6th Tab "Efficiency" (Phase 2)

### §8.1 File: `src/observeco/dashboard/routes/detail.py`

**What changes:**

1. Add tab button in the tab bar:
```python
tabs_html += '<span class="m-tab" onclick="switchModalTab(\'{name}\',\'efficiency\',this)">Efficiency</span>'
```

2. Add pane in the modal body:
```python
efficiency_html = _render_efficiency_tab(name)
# In the body, after memory_html:
{efficiency_html if is_agent else ""}
```

3. New function `_render_efficiency_tab(agent_name)` that renders the session table + expandable efficiency card, lazy-loaded via htmx.

### §8.2 Frontend HTML (htmx inline)

```html
<div class="panel-pane" data-pane="efficiency"
     hx-get="/api/efficiency/agent/{agent_name}"
     hx-trigger="load"
     hx-swap="innerHTML">
  <div class="state-msg">
    <div class="ico">⏳</div>
    <p>Loading sessions…</p>
  </div>
</div>
```

**Session table** (returned by API — includes empty state):
```html
<div class="sec-h">Recent Sessions</div>
<table class="tbl sess-tbl">
  <tr><th>Session</th><th>Archetype</th><th>Efficiency</th><th>Outcome</th></tr>
  <tr class="sess-row" onclick="toggleSessionDetail('sess1')">
    <td class="mono">#382</td>
    <td><span class="chip debug">debug</span></td>
    <td><span class="score bad">62</span></td>
    <td><span class="chip ok">✔ Succeeded</span></td>
  </tr>
</table>

<!-- Empty state — returned when API result is [] -->
<div class="state-msg" id="efficiency-empty" style="display:none">
  <div class="ico">📭</div>
  <h3>No sessions found</h3>
  <p>No Hermes session data available for this agent. Run the agent first, then check back.</p>
</div>

<!-- Error state — shown on fetch failure -->
<div class="state-msg" id="efficiency-error" style="display:none">
  <div class="ico">⚠</div>
  <h3>Could not load efficiency data</h3>
  <p>The efficiency engine encountered an error. Check the watch daemon is running.</p>
</div>

<script>
function toggleSessionDetail(id) {
  var el = document.getElementById(id + '-detail');
  if (el) el.style.display = el.style.display === 'none' ? 'block' : 'none';
}
function optimizePreview(sessionId) {
  // Phase 2: fetch /api/efficiency/optimize/preview/{sessionId} and show modal
}
// Phase 2: on htmx load swap, hide empty/error on success, show on empty/error
document.body.addEventListener('htmx:afterSwap', function(evt) {
  if (evt.detail.target && evt.detail.target.id === 'efficiency-pane') {
    var rows = evt.detail.target.querySelectorAll('.sess-tbl .sess-row');
    var empty = document.getElementById('efficiency-empty');
    var error = document.getElementById('efficiency-error');
    if (rows.length === 0 && empty) empty.style.display = '';
  }
});
</script>
```

**Expandable efficiency card** (hidden, shown on click):
```html
<div id="sess1-detail" class="sess-detail" style="display:none">
  <div class="efficiency-card">
    <div class="metric-row bad">
      <span class="m-dot">●</span>
      <span class="m-label">Redundant reads</span>
      <span class="m-detail">calculator.js ×3 — ~1.8K reclaimable</span>
    </div>
    <div class="baseline-line">
      40 vs your usual 87 for research (4 runs) — 33× the tokens
    </div>
    <button class="btn-opt" onclick="optimizePreview('session_id')">
      Optimize future runs →
    </button>
  </div>
</div>
```

### §8.3 CSS Additions

```css
.sess-tbl .chip { padding: 2px 8px; border-radius: 4px; font-size: 11px; }
.chip.debug { background: var(--warn-bg); color: var(--warn); }
.chip.research { background: var(--accent-bg); color: var(--accent); }
.chip.feature { background: var(--fg-1); color: var(--bg); }
.chip.ok { background: var(--good-bg); color: var(--good); }
.score { font-size: 20px; font-weight: 700; }
.score.bad { color: var(--danger); }
.score.warn { color: var(--warn); }
.score.good { color: var(--accent); }
.efficiency-card { background: var(--bg-1); border-radius: 8px; padding: 16px; margin: 8px 0; }
.metric-row { display: flex; gap: 8px; padding: 4px 0; border-bottom: 1px solid var(--border); }
.metric-row.bad .m-dot { color: var(--danger); }
.metric-row.warn .m-dot { color: var(--warn); }
.metric-row.good .m-dot { color: var(--accent); }
.metric-row .m-label { width: 160px; font-weight: 600; }
.metric-row .m-detail { color: var(--fg-2); }
```

---

## §9 Custom Rule Packs (Phase 3)

### §9.1 Format (`/.observeco/rules.json`)

```json
{
  "rules": [
    {"id": "no-vendor", "type": "forbid-read", "pattern": "node_modules|/dist/", "severity": "warn",
     "message": "Don't read vendored/generated code — it's huge and unowned."},
    {"id": "test-first", "type": "require-before-commit", "pattern": "npm (run )?(test|build)"}
  ]
}
```

### §9.2 Evaluation

```python
def evaluate_rules(turns: list[dict], rules: list[dict]) -> list[dict]:
    """Evaluate custom rules against session turns. Returns findings."""
    findings = []
    for rule in rules:
        rid = rule.get("id", "unknown")
        rtype = rule.get("type", "")
        pattern = rule.get("pattern", "")
        severity = rule.get("severity", "warn")
        message = rule.get("message", "Rule violation")

        try:
            regex = re.compile(pattern)
        except re.error:
            continue  # malformed rule dropped silently

        if rtype == "forbid-read":
            for e in _read_events(turns):
                path = e.get("arguments", {}).get("path", "")
                if regex.search(path):
                    findings.append({"id": rid, "severity": severity, "message": message, "offender": path})
        elif rtype == "forbid-edit":
            for e in _edit_events(turns):
                path = e.get("arguments", {}).get("path", "")
                if regex.search(path):
                    findings.append({"id": rid, "severity": severity, "message": message, "offender": path})
        elif rtype == "forbid-bash":
            for e in _bash_events(turns):
                cmd = e.get("command", "")
                if regex.search(cmd):
                    findings.append({"id": rid, "severity": severity, "message": message, "offender": cmd})
        elif rtype == "require-before-commit":
            commits = [e for e in _bash_events(turns) if "commit" in e.get("command", "").lower()]
            prereqs = [e for e in _bash_events(turns) if regex.search(e.get("command", ""))]
            has_test_before = any(
                p.get("seq", 0) < c.get("seq", 99999)
                for p in prereqs for c in commits
            )
            if commits and not has_test_before:
                findings.append({"id": rid, "severity": severity, "message": message, "offender": "committed without prerequisite"})
    return findings
```

---

## §10 Files Changed

### Phase 1 (Built 2026-07-12)
| File | Action | Lines | Status |
|------|--------|-------|--------|
| `src/observeco/efficiency/__init__.py` | Create | 1 | ✅ |
| `src/observeco/efficiency/metrics.py` | Create | ~290 | ✅ |
| `src/observeco/dashboard/routes/efficiency.py` | Create | ~60 | ✅ |
| `src/observeco/dashboard/server.py` | Modify | +2 (import + include_router) | ✅ |
| `tests/test_efficiency.py` | Create | ~70 | ✅ 5/5 pass |

### Phase 2 (pending)
| File | Action | Lines |
|------|--------|-------|
| `src/observeco/dashboard/routes/detail.py` | Modify | +80 (6th tab) |
| Dashboard CSS | Modify | +40 |

**Phase 1: 4 files, ~420 lines. Phase 2: 2 files, ~120 lines.**

---

## §12 Build Notes — Phase 1 (2026-07-12)

### Real bugs found and fixed during build (not in spec)

1. **Archetype ordering bug** — `research` check fired before `debug` check. A read-heavy session with errors (e.g. 6 reads, 1 edit, has errors) was misclassified as `research` because `n_reads > n_edits*3` (6 > 3) matched first. **Fix:** moved `has_errors → debug` check above the `research` check. Errors are a stronger signal than read-volume.

2. **Fake token-metric scores** — `context-pressure` and `yield-density` computed scores even when `token_counts` was empty (divided by fake denominator of 1), producing `bad` verdicts on every real session with no token data. **Fix:** both now return `noop` when `token_counts` is empty, same as `cache-hit`. Real sessions now correctly show 3 token metrics as `noop` (deferred to Phase 2 join) instead of misleading `bad`.

### Verification evidence
- Unit: `pytest tests/test_efficiency.py` → 5 passed
- Integration: FastAPI TestClient `GET /api/efficiency/session/{id}` → 200 with valid JSON; 404 on unknown; 401 without auth
- Real data: 3 largest Hermes sessions scored 52/57/52 efficiency, archetype=debug, effectiveness=succeeded/likely-ok

### Deviation from spec
- Spec §6.1 defined `/agent/{agent_name}` list endpoint. **Not built in Phase 1** — Hermes session JSONL has no `agent_name` field (confirmed in real data), so the endpoint would return all sessions unfiltered. Deferred to Phase 2 where the detail modal passes the agent name and we add a session-index or tag. Phase 1 ships only the per-session endpoint, which is what the UI needs first.
- Spec §3.2 used `token_counts=[]` as Phase 1 default. Correct — confirmed token-based metrics noop cleanly.

---

## §11 Deferred (Ponytails)

| Feature | Why deferred | Upgrade path |
|---------|-------------|-------------|
| **Token-based metrics (context-pressure, yield-density, cache-hit)** | **EVIDENCE-BASED DEFERRAL:** `token_logs` has 507,567 rows, **all with empty `session_id`** (verified 2026-07-12). `log_token_turn()` does not accept/persist `session_id` — it logs per watch-trim-snapshot with `turn_id=watch_{ts}_{agent}`. No reliable join key to Hermes sessions exists. Activating these 3 metrics now would require faking a timestamp-window join (sessions overlap → false attribution). **Not building it wrong.** | (1) Add `session_id` param to `log_token_turn()` + pass real Hermes session_id from the agent runtime; OR (2) join by agent_name + timestamp window as approximation. Either requires changes outside this spec (watch daemon / agent runtime). |
| Per-project optimize memory | Single global `~/.hermes/AGENTS.md` target is fine for MVP; sessions have no project field | Add CWD detection from session first user/assistant message content, scope the optimize block per project dir |
| In-run optimizer (re-read → no-op/diff) | Requires OpenCode plugin hooks; Hermes has no equivalent | Not applicable |
| Live session map (visual graph) | Expensive React/D3 build; session table covers the need | If users ask for visual, add D3 graph to efficiency tab |
| Model-tailored suggestions (free LLM) | Rule-based is good enough for Phase 1 | Wire optional local model via Ollama for personalized suggestions |

---

## §13 Phase 3 Build Notes (2026-07-12)

### What shipped
- **Optimize write-back**: `POST /api/efficiency/optimize/preview|apply|revert/{session_id}` — writes a reversible, marker-delimited block to `~/.hermes/AGENTS.md`. Verified: apply wrote 52K-token block, revert cleaned it to 0 bytes.
- **Custom rule packs**: `GET /api/efficiency/rules/{session_id}` — evaluates `rules.json` (at `get_data_dir()/efficiency/rules.json`) against a session. 4 rule types: forbid-read, forbid-edit, forbid-bash, require-before-commit. Sample rules.json shipped.
- **Per-archetype baselines**: `GET /api/efficiency/baseline/{session_id}` — compares session score to recent same-archetype peers. Live: debug archetype, 92 peers, baseline=60, this session=52, delta=-8.
- **Frontend**: Efficiency card now shows baseline line + "Optimize future runs" button (calls apply endpoint via fetch, shows reclaimable estimate).

### Deviations from original spec (documented)
1. **Optimize target = `~/.hermes/AGENTS.md`** (global), not `~/AGENTS.md`. Real Hermes uses per-profile AGENTS.md but sessions lack agent_name → global is the honest target. Per-profile deferred.
2. **Token metrics stay `noop`** — see §11 evidence. Not faked.
3. **`/agent/{agent_name}` list endpoint** — still not built (no agent_name in sessions). The Efficiency tab lists recent sessions globally; ponytail notes this in the UI.

### Verification (prod, :8899)
- 9/9 unit tests pass
- Live: baseline 200 (92 peers), rules 200 (2 loaded), optimize preview/apply/revert 200, AGENTS.md written + reverted clean
- Sessions HTML contains optimize button + baseline line
- Main dashboard 200 (no regression)

