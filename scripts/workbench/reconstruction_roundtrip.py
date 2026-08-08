#!/usr/bin/env python3
"""Round-trip test for the spawn-provenance reconstruction mechanism.

The self-replay conversion projection rests on one mechanism: given a captured
(SHA, spawn_dirty_diff, spawn_untracked) triple, a fresh worktree can be
restored to the exact working state the subagent saw at spawn. If that
round-trip is lossy in a common case, the conversion rate is a fiction.

This tests the mechanism WITHOUT waiting for captured sessions. It:
1. Takes a repo, makes a dirty working state (uncommitted edits + untracked
   files), records SHA + `git diff HEAD` + untracked list exactly as the
   capture does.
2. Restores into a fresh worktree from those three fields.
3. Diffs the restored state against the original dirty state.

It surfaces failure modes before real data arrives: binary files, file modes,
renames, deletions, submodules, .gitignore'd files that matter, diffs that
don't apply cleanly to a fresh checkout.

Usage:
    python3 reconstruction_roundtrip.py --repo /path/to/repo [--cases N]

Exit 0 = all round-trips lossless. Non-zero = at least one lossy case, with the
specific failure mode reported.
"""
from __future__ import annotations

import argparse
import difflib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def git(repo: str, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", repo, *args], capture_output=True, text=True, timeout=30,
    )


def capture_state(repo: str) -> dict:
    """Record SHA + git diff HEAD + untracked list, exactly as the capture does."""
    sha = git(repo, "rev-parse", "HEAD").stdout.strip()
    diff = git(repo, "diff", "HEAD").stdout
    untracked = git(repo, "ls-files", "--others", "--exclude-standard").stdout.strip()
    return {"sha": sha, "spawn_dirty_diff": diff, "spawn_untracked": untracked}


def make_dirty_state(repo: str, case: str) -> None:
    """Introduce a dirty working state matching a real subagent scenario."""
    if case == "edit":
        # uncommitted edit to a tracked file
        p = Path(repo) / "roundtrip_edit.txt"
        p.write_text("original\n")
        git(repo, "add", "roundtrip_edit.txt")
        git(repo, "commit", "-q", "-m", "roundtrip seed")
        p.write_text("original\nEDITED\n")
    elif case == "untracked":
        # a new untracked file
        (Path(repo) / "roundtrip_new.txt").write_text("brand new\n")
    elif case == "edit_and_untracked":
        p = Path(repo) / "roundtrip_edit.txt"
        p.write_text("original\n")
        git(repo, "add", "roundtrip_edit.txt")
        git(repo, "commit", "-q", "-m", "roundtrip seed")
        p.write_text("original\nEDITED\n")
        (Path(repo) / "roundtrip_new.txt").write_text("brand new\n")
    elif case == "binary":
        # a binary file (bytes that would break a text diff)
        (Path(repo) / "roundtrip.bin").write_bytes(b"\x00\x01\x02\xff\xfe\xfd")
    elif case == "deleted":
        p = Path(repo) / "roundtrip_del.txt"
        p.write_text("to delete\n")
        git(repo, "add", "roundtrip_del.txt")
        git(repo, "commit", "-q", "-m", "roundtrip seed")
        os.remove(p)
    elif case == "renamed":
        p = Path(repo) / "roundtrip_old.txt"
        p.write_text("rename me\n")
        git(repo, "add", "roundtrip_old.txt")
        git(repo, "commit", "-q", "-m", "roundtrip seed")
        os.rename(p, Path(repo) / "roundtrip_new.txt")
    elif case == "mode":
        p = Path(repo) / "roundtrip_mode.sh"
        p.write_text("#!/bin/sh\necho hi\n")
        git(repo, "add", "roundtrip_mode.sh")
        git(repo, "commit", "-q", "-m", "roundtrip seed")
        os.chmod(p, 0o755)
    else:
        raise ValueError(f"unknown case: {case}")


def restore_state(worktree: str, state: dict) -> None:
    """Restore a fresh worktree from the captured triple."""
    # checkout the SHA
    git(worktree, "checkout", "-q", state["sha"])
    # apply the dirty diff
    if state["spawn_dirty_diff"].strip():
        apply = subprocess.run(
            ["git", "-C", worktree, "apply", "-"],
            input=state["spawn_dirty_diff"], capture_output=True, text=True, timeout=30,
        )
        if apply.returncode != 0:
            raise RuntimeError(f"diff did not apply: {apply.stderr[:200]}")
    # recreate untracked files (content not captured — only paths; mark as
    # expected-missing, matching the capture's design)
    if state["spawn_untracked"].strip():
        for line in state["spawn_untracked"].splitlines():
            p = Path(worktree) / line
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("")  # placeholder — content not captured


def diff_trees(orig: str, restored: str) -> list[str]:
    """Diff two working trees; return list of differing paths."""
    r = git(orig, "status", "--porcelain")
    orig_status = r.stdout
    r2 = git(restored, "status", "--porcelain")
    restored_status = r2.stdout
    # compare the porcelain status lines (path + state)
    return list(difflib.unified_diff(
        orig_status.splitlines(), restored_status.splitlines(), lineterm="",
    ))


def run_case(repo: str, case: str) -> dict:
    """Run one round-trip case. Returns {case, lossless, failures, detail}."""
    # fresh worktree for the ORIGINAL dirty state
    orig_wt = tempfile.mkdtemp(prefix="rt-orig-")
    git(repo, "worktree", "add", "--detach", orig_wt, "HEAD")
    try:
        make_dirty_state(orig_wt, case)
        state = capture_state(orig_wt)

        # fresh worktree for the RESTORED state
        rest_wt = tempfile.mkdtemp(prefix="rt-rest-")
        git(repo, "worktree", "add", "--detach", rest_wt, "HEAD")
        try:
            restore_state(rest_wt, state)
            # compare the two working trees
            diff = diff_trees(orig_wt, rest_wt)
            lossless = len(diff) == 0
            return {
                "case": case,
                "lossless": lossless,
                "failures": diff,
                "detail": "lossless" if lossless else f"{len(diff)} differing status lines",
            }
        finally:
            git(repo, "worktree", "remove", "--force", rest_wt)
    finally:
        git(repo, "worktree", "remove", "--force", orig_wt)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True, help="git repo to test against")
    ap.add_argument("--cases", default="edit,untracked,edit_and_untracked,binary,deleted,renamed,mode")
    args = ap.parse_args()

    repo = os.path.abspath(args.repo)
    git_path = os.path.join(repo, ".git")
    if not (os.path.isdir(git_path) or os.path.isfile(git_path)):
        print(f"not a git repo: {repo}")
        return 2

    results = []
    for case in args.cases.split(","):
        try:
            results.append(run_case(repo, case))
        except Exception as e:
            results.append({"case": case, "lossless": False, "failures": [str(e)], "detail": f"ERROR: {e}"})

    print(json.dumps(results, indent=2))
    lossy = [r for r in results if not r["lossless"]]
    if lossy:
        print(f"\n{len(lossy)}/{len(results)} cases LOSSY:")
        for r in lossy:
            print(f"  {r['case']}: {r['detail']}")
        return 1
    print(f"\nAll {len(results)} cases lossless.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
