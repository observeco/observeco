#!/usr/bin/env python3
"""Workbench batch runner — clean k=3 self-replay with all environment gates.

Terminating instrument for Track 0. Produces the four-number table.

Gates (each promotes a previously-missed environment lie to an enforced check):
- per-trial FRESH worktree (isolation) — trials share nothing
- precondition gate — verify the worktree reproduces the failure state
  (target absent) BEFORE each trial; abort-and-log on violation
- explicit cwd=WORKTREE at spawn (never inherit ambient cwd)
- containment assertion — post-trial, every write path must be under the
  worktree root; reads into sibling repos flagged; violation fails the trial
- run record with agent-side provenance (cwd, model, budget) + a
  summary-vs-trajectory verdict field (both logged every trial, incl. agreements)

A candidate passes at >=2/3 clean trials.
"""
from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path

REPO = "/Users/seanfzc/projects/observeco"
STATE_DB = os.path.expanduser("~/.hermes/state.db")
RESULTS_DIR = "/tmp/workbench-results"

# Sibling repo roots — reads into these are containment violations
# (an agent free to read here can locate a merged answer key).
SIBLING_ROOTS = [
    "/Users/seanfzc/projects/observeco",
    "/Users/seanfzc/projects/observeco-main",
    "/Users/seanfzc/projects/observeco-cap",
    "/Users/seanfzc/projects/rqgm-core",
    "/Users/seanfzc/projects/EvoSkill-RQGM",
    "/Users/seanfzc/projects/open-design",
]


def now_iso() -> str:
    return datetime.now().isoformat()


def connect_state():
    conn = sqlite3.connect(f"file:{STATE_DB}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def recover_start_sha(conn, session_id: str) -> str | None:
    row = conn.execute("SELECT started_at FROM sessions WHERE id=?", (session_id,)).fetchone()
    if not row:
        return None
    ts = datetime.fromtimestamp(row["started_at"]).strftime("%Y-%m-%d %H:%M:%S")
    r = subprocess.run(
        ["git", "-C", REPO, "log", "--oneline", "-1", f"--until={ts}"],
        capture_output=True, text=True, timeout=10,
    )
    return r.stdout.strip().split()[0] if r.stdout.strip() else None


def get_first_user_msg(conn, session_id: str) -> str:
    row = conn.execute(
        "SELECT content FROM messages WHERE session_id=? AND role='user' "
        "AND content IS NOT NULL ORDER BY timestamp ASC LIMIT 1",
        (session_id,),
    ).fetchone()
    return row["content"] if row else ""


def get_agent_provenance(conn, session_id: str) -> dict:
    """Agent-side environment provenance — the unpinned layers we now record."""
    row = conn.execute(
        "SELECT model, model_config, profile_name, source FROM sessions WHERE id=?",
        (session_id,),
    ).fetchone()
    if not row:
        return {}
    return {
        "orig_model": row["model"],
        "orig_model_config": row["model_config"],
        "orig_profile": row["profile_name"],
        "orig_source": row["source"],
    }


def pin_fresh_worktree(sha: str, tag: str) -> tuple[str, str]:
    """Create a fresh namespaced worktree at sha. Returns (path, branch)."""
    branch = f"workbench/{tag}"
    path = f"/tmp/workbench-{tag}"
    for c in [
        ["git", "-C", REPO, "worktree", "remove", path, "--force"],
        ["git", "-C", REPO, "branch", "-D", branch],
    ]:
        subprocess.run(c, capture_output=True, text=True, timeout=15)
    r = subprocess.run(
        ["git", "-C", REPO, "worktree", "add", "-b", branch, path, sha],
        capture_output=True, text=True, timeout=30,
    )
    if r.returncode != 0:
        return "", branch
    return path, branch


def teardown_worktree(path: str, branch: str) -> None:
    for c in [
        ["git", "-C", REPO, "worktree", "remove", path, "--force"],
        ["git", "-C", REPO, "branch", "-D", branch],
    ]:
        subprocess.run(c, capture_output=True, text=True, timeout=15)


def target_present(path: str, marker: str, rel: str) -> bool:
    """Check whether marker appears in rel path under worktree root."""
    r = subprocess.run(
        ["grep", "-q", marker, f"{path}/{rel}"],
        capture_output=True, text=True, timeout=10,
    )
    return r.returncode == 0


def containment_check(tag: str, session_id: str, worktree_root: str) -> dict:
    """Post-trial: parse the session's tool calls, enforce write/read confinement.
    Returns {violated, reason}."""
    conn = connect_state()
    try:
        rows = conn.execute(
            "SELECT tool_calls FROM messages WHERE session_id=? "
            "AND tool_calls IS NOT NULL AND tool_calls != ''",
            (session_id,),
        ).fetchall()
    finally:
        conn.close()

    violations = []
    wt = Path(worktree_root).resolve()
    for r in rows:
        try:
            for c in json.loads(r["tool_calls"]):
                fn = c.get("function", {})
                name = fn.get("name", "")
                args = fn.get("arguments", "")
                try:
                    args = json.loads(args) if isinstance(args, str) else args
                except Exception:
                    args = {}
                if name not in ("patch", "write_file", "file_write", "read_file", "search_files"):
                    continue
                p = args.get("path", "") if isinstance(args, dict) else ""
                if not p:
                    continue
                # Resolve relative paths AGAINST THE WORKTREE, not the runner cwd.
                # The agent's tools run with cwd=worktree, so a relative path like
                # ./src/x means <worktree>/src/x. Resolving against the runner cwd
                # (observeco-main) false-flags legitimate worktree writes.
                rp = (wt / p).resolve() if not os.path.isabs(p) else Path(p).resolve()
                rp = str(rp)
                if name == "search_files":
                    if rp in SIBLING_ROOTS or any(rp.startswith(s + "/") for s in SIBLING_ROOTS):
                        violations.append(f"{name}: search into sibling {rp}")
                    continue
                is_write = name in ("patch", "write_file", "file_write")
                if is_write:
                    # writes MUST be under worktree
                    if not rp.startswith(str(wt)):
                        violations.append(f"{name}: write outside worktree {rp}")
                else:
                    # reads into sibling repos are violations
                    if rp in SIBLING_ROOTS or any(rp.startswith(s + "/") for s in SIBLING_ROOTS):
                        violations.append(f"{name}: read into sibling {rp}")
        except Exception:
            continue
    if violations:
        return {"violated": True, "reason": "; ".join(violations[:5])}
    return {"violated": False, "reason": ""}


def run_clean_k3(candidate: dict) -> dict:
    """Run k=3 self-replay for one candidate with all gates. Returns summary."""
    sid = candidate["id"]
    tag = f"{sid}-{uuid.uuid4().hex[:8]}"
    sha = candidate["sha"]
    model = candidate["model"]
    task = candidate["task"]

    sys.path.insert(0, "/Users/seanfzc/projects/observeco/src")
    from observeco.benchmark.adapters.hermes import HermesBenchmarkAdapter

    trials = []
    for t in range(1, 4):
        entry = {
            "trial": t, "session": sid, "sha": sha, "model": model,
            "started": now_iso(), "status": "pending",
        }
        path, branch = "", ""
        try:
            # 1. fresh worktree per trial
            path, branch = pin_fresh_worktree(sha, f"{tag}-t{t}")
            if not path:
                entry.update({"status": "pin_failed", "reason": "worktree add failed"})
                continue

            # 2. PRECONDITION GATE: worktree must reproduce failure state
            #    (target absent). If present, isolation failed or task invalid.
            if target_present(path, candidate["marker"], candidate["rel"]):
                entry.update({
                    "status": "precondition_violation",
                    "reason": f"target {candidate['marker']} already present at pin (post-fix pin or leak)",
                })
                teardown_worktree(path, branch)
                continue

            # 3. spawn with EXPLICIT cwd= (never inherit ambient cwd)
            adapter = HermesBenchmarkAdapter(
                hermes_bin="hermes", timeout=candidate["budget"],
                agent_profile="", model=model, workdir=path,
            )
            from types import SimpleNamespace

            result = adapter.run_task(
                "workbench-replay",
                SimpleNamespace(
                    input_text=task, context_text="", timeout=candidate["budget"], model=model,
                ),
            )
            entry["elapsed"] = round(time.time() - entry_start(entry), 1)
            entry["model_used"] = result.get("model_used")
            entry["provider_error"] = result.get("provider_error")
            entry["error"] = result.get("error")
            entry["timed_out"] = result.get("timed_out", False)

            # 4. CONTAINMENT: did the agent stay in the worktree?
            # Verdict fields are set HERE (not in the scoring block) so a
            # containment violation still records explicit, honest values
            # instead of silently missing fields.
            #   summary_verdict   = marker check (what a naive summary reports).
            #   containment_verdict = deterministic provenance from the transcript
            #                       (confinement + leakage). NOT trajectory-truth.
            #   trajectory_verdict = None. Never a copy of summary_verdict. Deferred
            #                       to an LLM-judge trajectory pass (token cost per
            #                       run — see workbench-v4 §0 pending list).
            #   needs_review      = True iff containment violated. A violated run is
            #                       quarantined (excluded from the grid) until an
            #                       adjudicator clears it. Disagreement between
            #                       summary and trajectory is unmeasurable today
            #                       (trajectory_verdict is null), so the enforceable
            #                       deterministic gate is containment.
            containment = containment_check(tag, sid, path)
            entry["containment"] = containment
            entry["trajectory_verdict"] = None
            entry["needs_review"] = bool(containment["violated"])
            if containment["violated"]:
                entry["status"] = "containment_violation"
                entry["score_detail"] = "n/a (containment failed)"
                entry["containment_verdict"] = "violated"
                entry["summary_verdict"] = "fail"
                teardown_worktree(path, branch)
                continue

            entry["containment_verdict"] = "clean"

            # 5. SCORE from captured state BEFORE teardown.
            passed = target_present(path, candidate["marker"], candidate["rel"])
            entry["status"] = "pass" if passed else "fail"
            entry["score_detail"] = f"{candidate['marker']} present={passed}"
            entry["summary_verdict"] = "pass" if passed else "fail"
        except Exception as e:  # noqa: BLE001
            entry.update({"status": "exception", "error": str(e)})
        finally:
            if path:
                teardown_worktree(path, branch)
            trials.append(entry)

    passes = sum(1 for t in trials if t["status"] == "pass")
    status = "PASS" if passes >= 2 else "FAIL"
    return {
        "candidate_status": status,
        "session": sid, "model": model, "sha": sha,
        "k": 3, "pass_count": passes,
        "trials": trials,
    }


def entry_start(entry: dict) -> float:
    # helper: parse started ISO to epoch for elapsed calc
    try:
        return datetime.fromisoformat(entry["started"]).timestamp()
    except Exception:
        return time.time()


def main() -> None:
    os.makedirs(RESULTS_DIR, exist_ok=True)
    candidates = load_candidates()
    print("=== WORKBENCH TRACK 0 — CLEAN K=3 BATCH ===")
    print(f"candidates: {len(candidates)}")
    print()

    all_results = []
    for c in candidates:
        print(f"--- {c['id']} ({c['model']}) @ {c['sha']} ---", flush=True)
        res = run_clean_k3(c)
        all_results.append(res)
        print(
            f"  {res['candidate_status']}: {res['pass_count']}/{res['k']} "
            f"[{' '.join(t['status'][:3] for t in res['trials'])}]",
            flush=True,
        )

    out = os.path.join(RESULTS_DIR, f"batch-{int(time.time())}.json")
    with open(out, "w") as f:
        json.dump({"candidates": all_results, "produced": now_iso()}, f, indent=2)
    print(f"\nresult file: {out}")


def load_candidates() -> list[dict]:
    """Load pre-registered candidates from a config file (created by selection)."""
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("--candidates", required=True, help="JSON file of candidates")
    args = p.parse_args()
    with open(args.candidates) as f:
        data = json.load(f)
    return data


if __name__ == "__main__":
    main()
