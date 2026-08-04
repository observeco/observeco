#!/usr/bin/env python3
"""Workbench selection — mine completed sessions into candidate drafts.

Per spec v0.1. Produces candidate drafts for the batch runner, with a
derived-vs-authored split, a marker_strength field, and a decision log
that records provenance + rejections + original first-user-message.

Derived fields must be exact; authored fields are null/provisional.
The fixture test (test_workbench_selection.py) is what validates this.
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
import subprocess
from datetime import datetime

REPO = "/Users/seanfzc/projects/observeco"
STATE_DB = os.path.expanduser("~/.hermes/state.db")
SIBLING_ROOTS = [
    "/Users/seanfzc/projects/observeco",
    "/Users/seanfzc/projects/observeco-main",
    "/Users/seanfzc/projects/observeco-cap",
]
WRITE_TOOL_NAMES = {"patch", "write_file", "file_write"}
TEST_PATTERNS = [
    re.compile(r"\bpytest\b"),
    re.compile(r"\bnpm\s+test\b"),
    re.compile(r"\bunittest\b"),
    re.compile(r"\bgo\s+test\b"),
    re.compile(r"\bcargo\s+test\b"),
]


def now_iso() -> str:
    return datetime.now().isoformat()


def connect_state():
    conn = sqlite3.connect(f"file:{STATE_DB}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def parse_tool_calls(tc_json: str) -> list[tuple[str, dict]]:
    calls = []
    try:
        for c in json.loads(tc_json):
            fn = c.get("function", {})
            args = fn.get("arguments", "")
            try:
                args = json.loads(args) if isinstance(args, str) else args
            except Exception:
                args = {}
            calls.append((fn.get("name", ""), args))
    except Exception:
        pass
    return calls


def repo_from_path(s: str) -> list[str]:
    if not s:
        return []
    found = []
    for r in ["observeco"]:
        if re.search(rf"/Users/seanfzc/projects/{re.escape(r)}(?:[/\"\\])", s):
            found.append(r)
    return found


def terminal_write_repo(args: dict) -> list[str]:
    cmd = args.get("command", "") if isinstance(args, dict) else str(args)
    return [
        r
        for r in ["observeco"]
        if re.search(rf"cd\s+/Users/seanfzc/projects/{re.escape(r)}", cmd)
        or re.search(rf"git\s+(commit|push|add)\b.*/Users/seanfzc/projects/{re.escape(r)}", cmd)
    ]


def write_targets(sid: str) -> dict[str, int]:
    conn = connect_state()
    try:
        rows = conn.execute(
            "SELECT tool_calls FROM messages WHERE session_id=? AND tool_calls IS NOT NULL AND tool_calls != ''",
            (sid,),
        ).fetchall()
    finally:
        conn.close()
    counts = {}
    for r in rows:
        for name, args in parse_tool_calls(r["tool_calls"]):
            arg_str = json.dumps(args)
            repos = repo_from_path(arg_str)
            if not repos:
                continue
            if name in WRITE_TOOL_NAMES:
                for repo in repos:
                    counts[repo] = counts.get(repo, 0) + 1
            elif name == "terminal":
                tw = terminal_write_repo(args)
                if tw:
                    for repo in tw:
                        counts[repo] = counts.get(repo, 0) + 1
    return counts


def recover_start_sha(sid: str) -> str | None:
    conn = connect_state()
    try:
        row = conn.execute("SELECT started_at FROM sessions WHERE id=?", (sid,)).fetchone()
    finally:
        conn.close()
    if not row:
        return None
    ts = datetime.fromtimestamp(row["started_at"]).strftime("%Y-%m-%d %H:%M:%S")
    r = subprocess.run(
        ["git", "-C", REPO, "log", "--oneline", "-1", f"--until={ts}"],
        capture_output=True, text=True, timeout=10,
    )
    return r.stdout.strip().split()[0] if r.stdout.strip() else None


def session_duration(sid: str) -> int:
    conn = connect_state()
    try:
        row = conn.execute("SELECT started_at, ended_at FROM sessions WHERE id=?", (sid,)).fetchone()
    finally:
        conn.close()
    if not row or not row["ended_at"]:
        return 300
    return max(int(row["ended_at"] - row["started_at"]), 1)


def first_user_message(sid: str) -> str:
    conn = connect_state()
    try:
        row = conn.execute(
            "SELECT content FROM messages WHERE session_id=? AND role='user' "
            "AND content IS NOT NULL ORDER BY timestamp ASC LIMIT 1",
            (sid,),
        ).fetchone()
    finally:
        conn.close()
    return row["content"] if row else ""


def most_frequent_write_rel(sid: str) -> str | None:
    """Most-frequent write tool target path, relative to repo root."""
    conn = connect_state()
    try:
        rows = conn.execute(
            "SELECT tool_calls FROM messages WHERE session_id=? AND tool_calls IS NOT NULL AND tool_calls != ''",
            (sid,),
        ).fetchall()
    finally:
        conn.close()
    path_counts = {}
    for r in rows:
        for name, args in parse_tool_calls(r["tool_calls"]):
            if name not in WRITE_TOOL_NAMES:
                continue
            p = args.get("path", "") if isinstance(args, dict) else ""
            if not p:
                continue
            # resolve relative to repo root for both abs and rel
            if p.startswith("/Users/seanfzc/projects/observeco/"):
                rel = p[len("/Users/seanfzc/projects/observeco/") :]
            elif p.startswith("./"):
                rel = p[2:]
            elif p.startswith("/"):
                continue
            else:
                rel = p
            path_counts[rel] = path_counts.get(rel, 0) + 1
    if not path_counts:
        return None
    return max(path_counts.items(), key=lambda kv: kv[1])[0]


def has_test_commands(sid: str) -> tuple[bool, str]:
    """Did the session run a test command? Returns (found, command_preview)."""
    conn = connect_state()
    try:
        rows = conn.execute(
            "SELECT tool_calls FROM messages WHERE session_id=? AND tool_calls IS NOT NULL AND tool_calls != ''",
            (sid,),
        ).fetchall()
    finally:
        conn.close()
    for r in rows:
        for name, args in parse_tool_calls(r["tool_calls"]):
            if name != "terminal":
                continue
            cmd = args.get("command", "") if isinstance(args, dict) else ""
            for pat in TEST_PATTERNS:
                if pat.search(cmd):
                    return True, cmd[:120]
    return False, ""


def subject_symbol(task: str) -> str | None:
    """Extract the symbol the task names (backtick-quoted or obvious artifact)."""
    if not task:
        return None
    # backtick-quoted identifier
    m = re.search(r"`([A-Za-z_][A-Za-z0-9_]*)`", task)
    if m:
        return m.group(1)
    # snake_case/camelCase symbol in task text
    m = re.search(r"\b([a-z_][a-z0-9_]{2,})\b", task)
    if m:
        return m.group(1)
    return None


def marker_absent_at_pin(sha: str, rel: str, marker: str) -> bool | None:
    """Check marker absent at pin (precondition). None if can't check."""
    if not sha or not rel or not marker:
        return None
    branch = "wb-select-probe"
    path = f"/tmp/wb-select-probe-{sha[:8]}"
    for c in [
        ["git", "-C", REPO, "worktree", "remove", path, "--force"],
        ["git", "-C", REPO, "branch", "-D", branch],
    ]:
        subprocess.run(c, capture_output=True, text=True, timeout=10)
    r = subprocess.run(
        ["git", "-C", REPO, "worktree", "add", "-b", branch, path, sha],
        capture_output=True, text=True, timeout=30,
    )
    if r.returncode != 0:
        return None
    full = os.path.join(path, rel)
    absent = None
    if os.path.exists(full):
        g = subprocess.run(["grep", "-q", marker, full], capture_output=True, text=True, timeout=10)
        absent = g.returncode == 1
    subprocess.run(["git", "-C", REPO, "worktree", "remove", path, "--force"], capture_output=True, text=True, timeout=10)
    subprocess.run(["git", "-C", REPO, "branch", "-D", branch], capture_output=True, text=True, timeout=10)
    return absent


def marker_in_completion(sid: str, rel: str, marker: str) -> bool:
    """Did the original session's completion contain the marker in its write target?"""
    if not marker:
        return False
    conn = connect_state()
    try:
        rows = conn.execute(
            "SELECT tool_calls FROM messages WHERE session_id=? AND tool_calls IS NOT NULL AND tool_calls != ''",
            (sid,),
        ).fetchall()
    finally:
        conn.close()
    for r in rows:
        for name, args in parse_tool_calls(r["tool_calls"]):
            if name not in WRITE_TOOL_NAMES:
                continue
            p = args.get("path", "") if isinstance(args, dict) else ""
            if p and rel in p and marker in json.dumps(args):
                return True
    return False


def is_cron_content(task: str) -> bool:
    """Detect automated job output masquerading as real user work.

    The 17th-instance law: screen on the TRAJECTORY (the task content), not the
    summary (the session source column). A session may have source=telegram but
    contain cron-job output ('Cronjob Response', 'Canary Benchmark — Daily',
    a job_id) — that is automated work, not a user task, and must be rejected.
    """
    t = (task or "").lower()
    cron_markers = [
        "[replying to:",
        "cronjob response",
        "canary benchmark",
        "job_id:",
        "canary benchmark —",
        "canary benchmark — daily",
        "canary benchmark - daily",
        "account suspension alert",
    ]
    return any(m in t for m in cron_markers)


def is_entangled(sha: str, rel: str, candidate_pool: list[dict]) -> bool:
    """Detect sequential-session entanglement: two sessions pinning to the same
    SHA with overlapping target files, where one is a continuation of the other
    (e.g. 'find all X' then 'replace X'). Both would be the same task replayed
    against a shared world — emit one, not both.

    A draft is entangled with an earlier emitted draft if it shares both the
    pin SHA AND the target rel_path. The earlier draft wins; the later is rejected.
    """
    for prior in candidate_pool:
        if prior["sha"] == sha and prior["rel"] == rel:
            return True
    return False


def classify_objective(task: str) -> tuple[bool, str]:
    """Objective if it names a concrete artifact/action and isn't fuzzy. Provisional."""
    t = (task or "").lower()
    t = re.sub(r"^\[[^\]]+\]", "", t)
    objective_re = re.compile(
        r"(add the |add |build the |implement |replace |create |remove |fix |rename |refactor |"
        r"update the |change the |write a |make the |insert |delete )", re.I)
    fuzzy_re = re.compile(
        r"(redesign|scalable|better|intuitive|analysis|investigation|recap|status|check|verify|"
        r"investigat|diagnos|discuss|understand|improve|optimize|clean up|tidy)", re.I)
    has_action = bool(objective_re.search(t))
    has_fuzzy = bool(fuzzy_re.search(t))
    if not has_action:
        return False, "no_action_verb"
    if has_fuzzy:
        m = fuzzy_re.search(t)
        return False, f"fuzzy: {m.group(0) if m else 'unknown'}"
    return True, "objective"


def select_session(sid: str, decision_log: list[dict]) -> dict | None:
    """Run all gates for one session. Returns candidate draft or None (logged)."""
    log_entry = {"session_id": sid, "considered": now_iso()}
    decision_log.append(log_entry)

    # 1. write-target
    wt = write_targets(sid)
    if not wt:
        log_entry.update({"gate": "write_target", "outcome": "reject", "reason": "no_repo_write"})
        return None
    repo_root = "observeco"

    # 2. objective screen
    task = first_user_message(sid)

    # 2a. cron-content gate: screen on TRAJECTORY (content), not the source
    # column. A telegram-source session containing cron output is automated
    # work, not a user task — reject before objective classification.
    if is_cron_content(task):
        log_entry.update({"gate": "cron_content", "outcome": "reject", "reason": "cron_job_output", "first_user_msg": task})
        return None

    is_obj, reason = classify_objective(task)
    if not is_obj:
        log_entry.update({"gate": "objective", "outcome": "reject", "reason": reason, "first_user_msg": task})
        return None
    log_entry["first_user_msg"] = task

    # 3. pin sha
    sha = recover_start_sha(sid)
    if not sha:
        log_entry.update({"gate": "pin", "outcome": "reject", "reason": "pin_unrecoverable"})
        return None

    # 4. budget
    dur = session_duration(sid)
    budget = max(dur * 3, 180)

    # 5. rel_path
    rel = most_frequent_write_rel(sid)
    if not rel:
        log_entry.update({"gate": "rel_path", "outcome": "reject", "reason": "no_write_target"})
        return None

    # 6. assertion: tests-as-assertions-first
    has_test, test_cmd = has_test_commands(sid)
    assertion = "tests" if has_test else "subject_symbol"
    test_cmd_used = test_cmd if has_test else None

    # 7. marker + strength
    marker = subject_symbol(task) if not has_test else None
    marker_strength = None
    marker_valid = None
    if marker:
        absent = marker_absent_at_pin(sha, rel, marker)
        present = marker_in_completion(sid, rel, marker)
        if absent is True and present:
            marker_valid = True
            marker_strength = "strong"  # provisional; weak-baseline test decides
        else:
            marker_valid = False
            marker_strength = None
            marker = None  # fall back to human-authored

    draft = {
        "id": sid,
        "source": "selection",
        "model": None,  # filled from session row in batch
        "sha": sha,
        "task": task,
        "task_description": None,  # AUTHORED
        "budget": budget,
        "marker": marker,  # null unless cross-check passed
        "marker_strength": marker_strength,
        "marker_valid": marker_valid,
        "assertion": assertion,
        "test_cmd": test_cmd_used,
        "rel": rel,
        "repo_root": repo_root,
        "objective": "provisional",
    }
    log_entry.update({
        "gate": "all", "outcome": "candidate_draft", "reason": "passed",
        "derived": {k: draft[k] for k in ("sha", "budget", "rel", "repo_root")},
        "authored_pending": ["task_description"] + (["marker"] if marker is None else []),
    })
    return draft


def main() -> None:
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("--days", type=int, default=30, help="lookback days")
    p.add_argument("--min-messages", type=int, default=5)
    p.add_argument("--out", required=True, help="candidate drafts JSON output")
    p.add_argument("--log", required=True, help="decision log JSON output")
    args = p.parse_args()

    conn = connect_state()
    try:
        sessions = conn.execute(
            "SELECT id FROM sessions WHERE ended_at IS NOT NULL "
            "AND ended_at > strftime('%s','now',?) AND source != 'cron' AND message_count >= ?",
            (f"-{args.days} days", args.min_messages),
        ).fetchall()
    finally:
        conn.close()

    decision_log: list[dict] = []
    drafts = []
    for row in sessions:
        d = select_session(row["id"], decision_log)
        if d:
            # Entanglement gate: same pin SHA + same target file as an earlier
            # emitted draft = sequential continuation of one task. Emit the
            # earlier, reject the later (both would replay a shared world).
            if is_entangled(d["sha"], d["rel"], drafts):
                decision_log.append({
                    "session_id": d["id"], "gate": "entanglement", "outcome": "reject",
                    "reason": "same sha+rel as prior draft (shared world)",
                    "first_user_msg": d["task"],
                })
                continue
            drafts.append(d)

    with open(args.out, "w") as f:
        json.dump({"produced": now_iso(), "candidates": drafts}, f, indent=2)
    with open(args.log, "w") as f:
        json.dump({"produced": now_iso(), "decisions": decision_log}, f, indent=2)
    print(f"selection: {len(drafts)} candidate drafts from {len(sessions)} sessions")
    print(f"  drafts -> {args.out}")
    print(f"  decision log -> {args.log}")
    for d in drafts:
        n = 1 if d["marker"] is not None else 2
        print(f"  [{d['id']}] N={n} assertion={d['assertion']} marker={d['marker']!r} sha={d['sha'][:8]}")


if __name__ == "__main__":
    main()
