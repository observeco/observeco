#!/usr/bin/env python3
"""Workbench profile tracker — per-profile session capture + pin validation.

Scans every Hermes profile's state.db and reports, per profile:
  - session counts (total, by source)
  - capture rate (sessions with git_sha populated)
  - pin agreement: for each captured session, does the captured git_sha's repo
    match the repo paths the session's own tool calls touched?

The pin-agreement column is the FIRST job, not aggregation. A tracker that
reports "N sessions captured" without reporting whether the pins are RIGHT
would let a systematic wrong-cwd bug accumulate silently for weeks. A
confidently-wrong SHA is worse than a NULL: NULL excludes, a wrong pin produces
a reconstruction that looks valid and isn't.

Reports per-profile, never pooled by default. Different profiles plausibly do
different work in different repos; pooling them would repeat the cron-content
mistake at a larger scale (summary says "sessions", trajectories say five
different populations).

Usage:
    python3 profile_tracker.py [--profiles-dir ~/.hermes/profiles] [--json]
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

# Repo roots to recognize in tool-call paths (extend as needed). A session's
# touched-repo is the repo root of the paths in its tool calls.
KNOWN_REPOS = [
    "/Users/seanfzc/projects/observeco",
    "/Users/seanfzc/projects/observeco-main",
    "/Users/seanfzc/projects/observeco-cap",
    "/Users/seanfzc/projects/rqgm-core",
    "/Users/seanfzc/projects/EvoSkill-RQGM",
    "/Users/seanfzc/projects/open-design",
    "/Users/seanfzc/.hermes/hermes-agent",
]


def repo_for_path(p: str) -> str | None:
    """Return the known repo root containing path p, or None."""
    for repo in KNOWN_REPOS:
        if p == repo or p.startswith(repo + "/"):
            return repo
    return None


def extract_touched_repos(content: str) -> set[str]:
    """Extract repo roots from a tool message's content JSON (path fields)."""
    repos = set()
    if not content:
        return repos
    # find all path-like strings in the content
    for m in re.finditer(r'"path"\s*:\s*"([^"]+)"', content):
        r = repo_for_path(m.group(1))
        if r:
            repos.add(r)
    # also catch paths in "matches" arrays and plain text
    for m in re.finditer(r'/(?:Users/seanfzc/projects/[^"\\\s]+|Users/seanfzc/\.hermes/hermes-agent)', content):
        r = repo_for_path(m.group(0))
        if r:
            repos.add(r)
    return repos


def session_touched_repos(conn, session_id: str) -> set[str]:
    """All repo roots the session's tool calls touched."""
    repos = set()
    rows = conn.execute(
        "SELECT content FROM messages WHERE session_id=? AND role='tool' AND content IS NOT NULL",
        (session_id,),
    ).fetchall()
    for r in rows:
        repos |= extract_touched_repos(r["content"])
    return repos


def pin_agreement(conn, session_id: str, git_sha: str) -> str:
    """Does the captured git_sha's repo match the session's touched repos?

    Returns 'agree', 'mismatch', 'no_tool_paths', or 'unresolvable'.
    """
    if not git_sha:
        return "no_sha"
    # Check touched repos FIRST — a session with no tool paths can't be
    # validated regardless of whether the SHA resolves. (Order matters: a
    # session with no tool calls should report no_tool_paths, not unresolvable.)
    touched = session_touched_repos(conn, session_id)
    if not touched:
        return "no_tool_paths"
    # resolve the SHA's repo: find which known repo contains this commit
    sha_repo = None
    for repo in KNOWN_REPOS:
        try:
            import subprocess
            r = subprocess.run(
                ["git", "-C", repo, "cat-file", "-e", git_sha + "^{commit}"],
                capture_output=True, text=True, timeout=5,
            )
            if r.returncode == 0:
                sha_repo = repo
                break
        except Exception:
            continue
    if sha_repo is None:
        return "unresolvable"
    return "agree" if sha_repo in touched else "mismatch"


def scan_profile(db_path: str) -> dict:
    """Report capture + pin-agreement stats for one profile's state.db.

    Uses the canonical realpath as the store identity so symlinked aliases
    (e.g. main -> accelerator) report once, not once per path. A hardlink/symlink
    alias sharing an inode would otherwise double-count a store's volume.
    """
    prof = Path(db_path).parent.name
    realpath = os.path.realpath(db_path)
    try:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        cols = [c[1] for c in conn.execute("PRAGMA table_info(sessions)").fetchall()]
        has_capture = "git_sha" in cols
        if not has_capture:
            conn.close()
            return {"profile": prof, "realpath": realpath, "capture_columns": False, "note": "not yet on new code"}

        total = conn.execute("SELECT COUNT(*) c FROM sessions").fetchone()["c"]
        by_source = {
            r["source"]: r["c"]
            for r in conn.execute("SELECT source, COUNT(*) c FROM sessions GROUP BY source").fetchall()
        }
        captured = conn.execute(
            "SELECT id, git_sha FROM sessions WHERE git_sha IS NOT NULL AND git_sha!=''"
        ).fetchall()
        n_captured = len(captured)

        # staleness: days since the store last saw a write (max started_at)
        last_ts = conn.execute("SELECT MAX(started_at) m FROM sessions").fetchone()["m"]
        days_since = None
        if last_ts:
            from datetime import datetime
            days_since = max(0, round((datetime.now().timestamp() - last_ts) / 86400))

        # pin agreement on captured sessions
        agree = mismatch = no_tool = unresolvable = 0
        for row in captured:
            verdict = pin_agreement(conn, row["id"], row["git_sha"])
            if verdict == "agree": agree += 1
            elif verdict == "mismatch": mismatch += 1
            elif verdict == "no_tool_paths": no_tool += 1
            else: unresolvable += 1

        conn.close()
        return {
            "profile": prof,
            "realpath": realpath,
            "capture_columns": True,
            "total_sessions": total,
            "by_source": by_source,
            "captured": n_captured,
            "capture_rate": round(n_captured / total, 3) if total else 0.0,
            "days_since_last_write": days_since,
            "pin_agree": agree,
            "pin_mismatch": mismatch,
            "pin_no_tool_paths": no_tool,
            "pin_unresolvable": unresolvable,
        }
    except Exception as e:
        return {"profile": prof, "realpath": realpath, "error": str(e)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--profiles-dir", default=os.path.expanduser("~/.hermes/profiles"))
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    dbs = sorted(glob.glob(os.path.join(args.profiles_dir, "*", "state.db")))
    results = [scan_profile(db) for db in dbs]

    # Dedupe by realpath: symlink aliases (main -> accelerator) share one store.
    # Report the canonical realpath once; keep all alias names so the link is visible.
    seen_paths = {}
    for r in results:
        rp = r.get("realpath", "")
        if rp in seen_paths:
            seen_paths[rp]["_aliases"].append(r["profile"])
        else:
            seen_paths[rp] = dict(r)
            seen_paths[rp]["_aliases"] = []
    results = list(seen_paths.values())

    if args.json:
        # drop internal _aliases unless present
        for r in results:
            if r.get("_aliases"):
                r["aliases"] = r.pop("_aliases")
            else:
                r.pop("_aliases", None)
        print(json.dumps(results, indent=2))
        return 0

    # table
    print(f"{'store':14} {'aliases':16} {'cols':5} {'total':6} {'days_idle':9} {'captured':9} {'rate':6} {'agree':6} {'mismatch':8} {'no_tool':8}")
    print("-" * 96)
    for r in results:
        if "error" in r:
            print(f"{r['profile']:14} {'-':16} ERROR: {r['error']}")
            continue
        if not r.get("capture_columns"):
            al = ",".join(r.get("_aliases", [])) or "-"
            print(f"{r['profile']:14} {al:16} {'no':5} {'-':6} {'-':9} {'-':9} {'-':6} (not on new code)")
            continue
        al = ",".join(r.get("_aliases", [])) or "-"
        idle = r.get("days_since_last_write", "-")
        print(
            f"{r['profile']:14} {al:16} {'yes':5} {r['total_sessions']:6} {idle!s:9} "
            f"{r['captured']:9} {r['capture_rate']:6.3f} {r['pin_agree']:6} {r['pin_mismatch']:8} {r['pin_no_tool_paths']:8}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
