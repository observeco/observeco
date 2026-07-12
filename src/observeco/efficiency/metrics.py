"""11 context-efficiency metrics + archetype classification + effectiveness score.

All functions take a parsed session (list of turn dicts) and return deterministic
scores. No model calls, no external APIs.

Session turn shape (Hermes JSONL, verified against real data):
- {"role": "assistant", "tool_calls": [{"function": {"name": "...", "arguments": "{...}"}}]}
- {"role": "tool", "name": "search_files", "content": '{"content": "...", "exit_code": 0}'}
- {"role": "user", "content": "..."}
- {"role": "session_meta", "tools": [...]}
"""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path


# ── Helpers ──────────────────────────────────────────────────────────

def _read_events(turns: list[dict]) -> list[dict]:
    """read_file tool calls. Returns the assistant-turn tool_call dicts."""
    out = []
    for t in turns:
        if t.get("role") != "assistant":
            continue
        for tc in t.get("tool_calls", []):
            fn = tc.get("function", {})
            if fn.get("name") == "read_file":
                try:
                    args = json.loads(fn.get("arguments", "{}"))
                except (json.JSONDecodeError, TypeError):
                    args = {}
                out.append({"path": args.get("path", ""), "args": args})
    return out


def _edit_events(turns: list[dict]) -> list[dict]:
    """write_file/patch tool calls."""
    out = []
    for t in turns:
        if t.get("role") != "assistant":
            continue
        for tc in t.get("tool_calls", []):
            fn = tc.get("function", {})
            if fn.get("name") in ("write_file", "patch"):
                try:
                    args = json.loads(fn.get("arguments", "{}"))
                except (json.JSONDecodeError, TypeError):
                    args = {}
                out.append({"path": args.get("path", ""), "args": args})
    return out


def _bash_events(turns: list[dict]) -> list[dict]:
    """terminal tool calls with exit_code extracted from result content."""
    out = []
    for i, t in enumerate(turns):
        if t.get("role") != "assistant":
            continue
        for tc in t.get("tool_calls", []):
            fn = tc.get("function", {})
            if fn.get("name") == "terminal":
                try:
                    args = json.loads(fn.get("arguments", "{}"))
                except (json.JSONDecodeError, TypeError):
                    args = {}
                # Find the matching tool result (next tool turn after this assistant turn)
                exit_code = None
                for t2 in turns[i + 1:]:
                    if t2.get("role") == "tool":
                        exit_code = _extract_exit_code(t2.get("content", ""))
                        break
                out.append({"command": args.get("command", ""), "exit_code": exit_code, "seq": i})
    return out


def _content_size(turn: dict) -> int:
    """Estimate content size from a tool result turn.

    Tool result 'content' is a JSON string like '{"content": "...", "exit_code": 0}'.
    We measure the inner 'content' length; fall back to full string length.
    """
    raw = turn.get("content", "")
    if isinstance(raw, str):
        try:
            obj = json.loads(raw)
            if isinstance(obj, dict) and "content" in obj:
                return len(obj["content"])
        except (json.JSONDecodeError, TypeError):
            pass
        return len(raw)
    if isinstance(raw, dict):
        return len(raw.get("content", ""))
    return 0


def _extract_exit_code(content: str) -> int | None:
    """Exit code from a tool result content string (JSON-encoded)."""
    if not isinstance(content, str):
        return None
    try:
        obj = json.loads(content)
        if isinstance(obj, dict):
            return obj.get("exit_code")
    except (json.JSONDecodeError, TypeError, AttributeError):
        pass
    return None


def _count_outcomes(turns: list[dict]) -> int:
    """Concrete outcomes: commits + tests that passed."""
    bash = _bash_events(turns)
    commits = sum(1 for e in bash if "commit" in e["command"].lower())
    tests_passed = sum(
        1 for e in bash if "test" in e["command"].lower() and e.get("exit_code") == 0
    )
    return max(commits + tests_passed, 1)  # floor at 1


# ── 11 Metrics ───────────────────────────────────────────────────────

def metric_context_pressure(turns: list[dict], token_counts: list[int]) -> dict:
    """Peak input tokens. Source: token_logs (Phase 2 join)."""
    if not token_counts:
        return _noop("no token data")
    peak = max(token_counts)
    return _score(peak, warn=100_000, bad=180_000, value=peak)


def metric_cache_hit(turns: list[dict], token_log_rows: list[dict]) -> dict:
    """Cache read tokens ÷ total input tokens."""
    if not token_log_rows:
        return _noop("no token data")
    total_input = sum(
        r.get("input_tokens", 0) + r.get("cache_read_tokens", 0) for r in token_log_rows
    )
    cache_read = sum(r.get("cache_read_tokens", 0) for r in token_log_rows)
    if total_input < 1:
        return _noop("no input tokens")
    ratio = cache_read / total_input
    return _score(ratio, warn=0.6, bad=0.3, value=round(ratio, 3))


def metric_redundant_reads(turns: list[dict]) -> dict:
    """Same file read more than once."""
    reads = [e["path"] for e in _read_events(turns) if e["path"]]
    # ponytail: path-only, not content-hash. Misses same-content-different-path.
    redundant = {p: c for p, c in Counter(reads).items() if c > 1}
    reclaimable = sum(800 * c for c in redundant.values())  # ~800 tok/file re-read estimate
    return _score(len(redundant), warn=1, bad=3,
                  value={"files": redundant, "reclaimable_tokens": reclaimable})


def metric_read_amplification(turns: list[dict]) -> dict:
    """Read tokens ÷ edited tokens."""
    read_tokens = sum(_content_size({"content": e["args"].get("content", "")}) for e in _read_events(turns))
    edit_tokens = sum(len(e["args"].get("content", "")) for e in _edit_events(turns))
    if edit_tokens < 1:
        return _noop("no edits")
    ratio = read_tokens / edit_tokens
    return _score(ratio, warn=40, bad=120, value=round(ratio, 1))


def metric_large_injections(turns: list[dict]) -> dict:
    """Biggest single tool result size."""
    sizes = [_content_size(t) for t in turns if t.get("role") == "tool"]
    biggest = max(sizes) if sizes else 0
    return _score(biggest, warn=5_000, bad=15_000, value=biggest)


def metric_retry_waste(turns: list[dict]) -> dict:
    """Identical commands re-run."""
    cmds = [e["command"] for e in _bash_events(turns)]
    # ponytail: exact string match only. Misses semantically-identical variants.
    retries = [cmd for cmd, c in Counter(cmds).items() if c > 1]
    n_retries = sum(Counter(cmds)[cmd] - 1 for cmd in retries)
    return _score(n_retries, warn=1, bad=3,
                  value={"retried_cmds": retries, "count": n_retries})


def metric_yield_density(turns: list[dict], token_counts: list[int]) -> dict:
    """Concrete outcomes per 1K input tokens."""
    if not token_counts:
        return _noop("no token data")
    outcomes = _count_outcomes(turns)
    total_tokens_1k = sum(token_counts) / 1000
    density = outcomes / total_tokens_1k if total_tokens_1k > 0 else 0
    return _score(density, warn=0.05, bad=0.02, value=round(density, 4))


def metric_tool_overhead(turns: list[dict]) -> dict:
    """Tool calls ÷ outcomes."""
    outcomes = _count_outcomes(turns)
    if outcomes < 1:
        return _noop("no outcomes")
    n_tool_calls = sum(1 for t in turns if t.get("role") == "assistant" for _ in t.get("tool_calls", []))
    ratio = n_tool_calls / outcomes
    return _score(ratio, warn=2, bad=4, value=round(ratio, 1))


def metric_edit_thrash(turns: list[dict]) -> dict:
    """One file rewritten many times."""
    edits = [e["path"] for e in _edit_events(turns) if e["path"]]
    thrashy = {p: c for p, c in Counter(edits).items() if c > 2}
    return _score(len(thrashy), warn=2, bad=4, value=thrashy)


def metric_big_file_read(turns: list[dict]) -> dict:
    """Single oversized file pulled in whole."""
    reads = [e for e in _read_events(turns) if e["path"] and _content_size({"content": e["args"].get("content", "")}) >= 12_000]
    return _score(len(reads), warn=1, bad=3,
                  value={"files": [r["path"] for r in reads]})


def metric_exploration_waste(turns: list[dict]) -> dict:
    """Read text never edited."""
    read_paths = {e["path"] for e in _read_events(turns) if e["path"]}
    edit_paths = {e["path"] for e in _edit_events(turns) if e["path"]}
    waste = read_paths - edit_paths
    if not waste:
        return _score(0, warn=0, bad=999_999, value={})
    # ponytail: counts files, not token-weighted. Upgrade to content-size-weighted.
    return _score(len(waste), warn=30_000, bad=80_000, value={"wasted_files": list(waste)})


# ── Scoring ──────────────────────────────────────────────────────────

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


def _score(raw_value: float, warn: float, bad: float, value=None) -> dict:
    """Map raw value to 0-100. Lower-is-better for all 11 metrics here.

    raw <= warn  → good (100)
    raw >= bad   → bad (0)
    between      → linear 100→0
    """
    if value is None:
        value = raw_value
    if raw_value <= warn:
        score, status = 100, "good"
    elif raw_value >= bad:
        score, status = 0, "bad"
    else:
        score = round(100 - (raw_value - warn) / (bad - warn) * 100)
        status = "warn"
    return {"score": score, "status": status, "raw": raw_value, "value": value}


def _noop(reason: str) -> dict:
    return {"score": None, "status": "noop", "raw": None, "value": reason}


def compute_efficiency(turns: list[dict], token_counts: list[int] = None, session_id: str = "") -> dict:
    """Run all 11 metrics, return weighted score + per-metric detail.

    If session_id is provided, token-derived metrics (context-pressure,
    cache-hit, yield-density) are fed from token_logs joined by session_id
    (#83). Otherwise they noop (no token data available).
    """
    tc: list[int] = token_counts or []
    # #83: join real token data by session_id when available
    token_log_rows: list[dict] = []
    if session_id:
        try:
            from observeco.tracking.tokens import get_session_tokens
            token_log_rows = get_session_tokens(session_id)
            tc = [r["input_tokens"] for r in token_log_rows]
        except Exception:
            token_log_rows = []
            tc = []
    metrics = [
        ("context-pressure", metric_context_pressure(turns, tc)),
        ("cache-hit", metric_cache_hit(turns, token_log_rows)),
        ("redundant-reads", metric_redundant_reads(turns)),
        ("read-amplification", metric_read_amplification(turns)),
        ("large-injections", metric_large_injections(turns)),
        ("retry-waste", metric_retry_waste(turns)),
        ("yield-density", metric_yield_density(turns, tc)),
        ("tool-overhead", metric_tool_overhead(turns)),
        ("edit-thrash", metric_edit_thrash(turns)),
        ("big-file-read", metric_big_file_read(turns)),
        ("exploration-waste", metric_exploration_waste(turns)),
    ]
    total_weight = 0.0
    weighted_sum = 0.0
    active = []
    for mid, m in metrics:
        if m["status"] != "noop":
            w = WEIGHTS.get(mid, 1.0)
            weighted_sum += m["score"] * w
            total_weight += w
        active.append({"id": mid, **m})

    overall = round(weighted_sum / total_weight) if total_weight > 0 else None
    reclaimable = sum(
        m["value"].get("reclaimable_tokens", 0)
        for mid, m in metrics
        if isinstance(m.get("value"), dict) and "reclaimable_tokens" in m["value"]
    )
    return {"score": overall, "metrics": active, "_reclaimable": reclaimable}


# ── Archetype ──────────────────────────────────────────────────────────

def classify_archetype(turns: list[dict]) -> dict:
    """Classify session into research/debug/feature/ops/edit with confidence.

    ponytail: heuristic rules, not tuned. Upgrade with ML if misclassifications hurt.
    """
    edits = _edit_events(turns)
    reads = _read_events(turns)
    bash = _bash_events(turns)
    has_tests = any("test" in e["command"].lower() for e in bash)
    has_errors = any(
        "error" in (t.get("content", "") or "").lower()
        for t in turns if t.get("role") == "tool"
    )
    n_reads = len(reads)
    n_edits = len(edits)

    if has_errors:
        return {"archetype": "debug", "confidence": 0.8}
    if n_reads > n_edits * 3 and not has_tests:
        return {"archetype": "research", "confidence": 0.7}
    if n_edits > 5 and has_tests:
        return {"archetype": "feature", "confidence": 0.65}
    if n_reads < 3 and n_edits > 2:
        return {"archetype": "edit", "confidence": 0.6}
    if not n_edits and bash:
        return {"archetype": "ops", "confidence": 0.6}
    return {"archetype": "unknown", "confidence": 0.3}


# ── Effectiveness ───────────────────────────────────────────────────────

def compute_effectiveness(turns: list[dict]) -> dict:
    """Did the task land? 0-100 heuristic from exit codes + edits + commits."""
    edits = _edit_events(turns)
    bash = _bash_events(turns)
    commits = [e for e in bash if "commit" in e["command"].lower()]
    last_test = next((e for e in reversed(bash) if "test" in e["command"].lower()), None)

    score = 50  # base
    signals = []

    if edits:
        score += 15
        signals.append("edits_exist")
    if last_test and last_test.get("exit_code") == 0:
        score += 20
        signals.append("tests_passed")
    elif last_test:
        score -= 15
        signals.append("tests_failed")

    errors = [e for e in bash if e.get("exit_code", 0) not in (None, 0)]
    score -= min(len(errors) * 2, 30)

    n_signals = len(signals)
    if n_signals >= 3:
        confidence = "high"
    elif n_signals >= 1:
        confidence = "medium"
    else:
        confidence = "low"
        score = None

    if score is not None:
        if score >= 80:
            verdict = "succeeded"
        elif score >= 50:
            verdict = "likely ok"
        else:
            verdict = "failed"
    else:
        verdict = "unclear"

    return {"score": score, "confidence": confidence, "verdict": verdict, "signals": signals}


# ── Custom Rule Packs (Phase 3) ──────────────────────────────────────────

def evaluate_rules(turns: list[dict], rules: list[dict]) -> list[dict]:
    """Evaluate custom rules against session turns. Returns findings.

    Rule types: forbid-read, forbid-edit, forbid-bash, require-before-commit.
    Malformed rules (bad regex) are dropped silently (ponytail: log instead).
    """
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
            continue
        if rtype == "forbid-read":
            for e in _read_events(turns):
                path = e["path"]
                if path and regex.search(path):
                    findings.append({"id": rid, "severity": severity, "message": message, "offender": path})
        elif rtype == "forbid-edit":
            for e in _edit_events(turns):
                path = e["path"]
                if path and regex.search(path):
                    findings.append({"id": rid, "severity": severity, "message": message, "offender": path})
        elif rtype == "forbid-bash":
            for e in _bash_events(turns):
                cmd = e["command"]
                if cmd and regex.search(cmd):
                    findings.append({"id": rid, "severity": severity, "message": message, "offender": cmd})
        elif rtype == "require-before-commit":
            commits = [e for e in _bash_events(turns) if "commit" in e["command"].lower()]
            prereqs = [e for e in _bash_events(turns) if regex.search(e["command"])]
            has_prereq_before = any(
                p["seq"] < c["seq"] for p in prereqs for c in commits
            )
            if commits and not has_prereq_before:
                findings.append({"id": rid, "severity": severity, "message": message,
                                 "offender": "committed without prerequisite"})
    return findings


# ── Per-Archetype Baseline (Phase 3) ──────────────────────────────────────

def compute_baseline(session_id: str, archetype: str, sessions_dir=None) -> dict:
    """Compare this session's efficiency to recent same-archetype sessions.

    ponytail: scans recent sessions globally (no agent filter). Compares
    efficiency score of same-archetype peers only. Returns baseline stats.
    """
    import glob
    import os

    if sessions_dir is None:
        from observeco.config import hermes_home
        home = hermes_home()
        sessions_dir = (home / "sessions") if home else Path.home() / ".hermes" / "sessions"

    files = sorted(glob.glob(str(sessions_dir / "*.jsonl")), key=os.path.getmtime, reverse=True)[:100]
    peer_scores = []
    for p in files:
        stem = os.path.basename(p).replace(".jsonl", "")
        if stem == session_id:
            continue
        try:
            turns = _parse_session_for_baseline(p)
        except Exception:
            continue
        if classify_archetype(turns)["archetype"] == archetype:
            eff = compute_efficiency(turns)
            if eff["score"] is not None:
                peer_scores.append(eff["score"])

    if not peer_scores:
        return {"archetype": archetype, "peer_count": 0, "baseline": None,
                "delta": None, "verdict": "no peers yet"}

    baseline = round(sum(peer_scores) / len(peer_scores))
    # current session score passed separately; here we return peer stats
    return {"archetype": archetype, "peer_count": len(peer_scores),
            "baseline": baseline, "min": min(peer_scores), "max": max(peer_scores)}


def _parse_session_for_baseline(path: Path | str) -> list[dict]:
    """Parse a session file for baseline comparison (lightweight)."""
    turns = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if obj.get("role") in ("assistant", "tool", "user", "session_meta"):
                turns.append(obj)
    return turns


# ── Optimize Memory Block (Phase 3) ──────────────────────────────────────

OPTIMIZE_MARKER_START = "<!-- observeco-efficiency:start -->"
OPTIMIZE_MARKER_END = "<!-- observeco-efficiency:end -->"


def build_optimize_block(efficiency: dict) -> str:
    """Build a compact, actionable efficiency notes block (reversible, marked)."""
    metrics = efficiency.get("metrics", [])
    bad = [m for m in metrics if m.get("status") == "bad"]
    warn = [m for m in metrics if m.get("status") == "warn"]
    if not bad and not warn:
        return ""

    lines = [OPTIMIZE_MARKER_START, "## Efficiency notes (auto-generated by ObserveCo)"]
    for m in bad:
        lines.append(f"- [BAD] {_describe_metric(m)}")
    for m in warn:
        lines.append(f"- [WARN] {_describe_metric(m)}")
    lines.append(OPTIMIZE_MARKER_END)
    return "\n".join(lines)


def _describe_metric(m: dict) -> str:
    """Human-readable description of a metric finding."""
    mid = m.get("id", "")
    val = m.get("value", {})
    if mid == "redundant-reads" and isinstance(val, dict):
        files = ", ".join(list(val.get("files", {}).keys())[:3])
        reclaim = val.get("reclaimable_tokens", 0)
        return f"Read {files} repeatedly — ~{reclaim:,} tokens reclaimable" if files else f"Redundant reads (~{reclaim:,}t)"
    if mid == "retry-waste" and isinstance(val, dict):
        cmds = ", ".join(val.get("retried_cmds", [])[:2])
        return f"Re-ran commands: {cmds}" if cmds else "Retry waste detected"
    if mid == "edit-thrash" and isinstance(val, dict):
        files = ", ".join(list(val.keys())[:3])
        return f"Rewrote {files} multiple times" if files else "Edit thrash detected"
    if mid == "large-injections" and isinstance(val, dict):
        return f"Largest single injection: {val.get('value', '?')} chars"
    return f"{mid}: {m.get('raw', '?')}"

