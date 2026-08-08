#!/usr/bin/env python3
"""Tests for the reconstruction round-trip mechanism.

Pins the honest finding: tracked-state reconstruction is lossless, but
untracked-file CONTENT is not captured (spawn_untracked records paths only), so
a subagent that creates a new file reconstructs it as an empty placeholder.

The status-based comparison in reconstruction_roundtrip.py cannot see this
loss (it shows path presence, not content). These tests compare CONTENT
directly so the gap is pinned by a failing test, not just described.
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))
import reconstruction_roundtrip as rt


def _make_repo() -> str:
    """Create a throwaway git repo with one committed file."""
    repo = tempfile.mkdtemp(prefix="rt-test-")
    subprocess.run(["git", "-C", repo, "init", "-q"], check=True)
    subprocess.run(["git", "-C", repo, "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", repo, "config", "user.name", "t"], check=True)
    p = Path(repo) / "seed.txt"
    p.write_text("seed\n")
    subprocess.run(["git", "-C", repo, "add", "seed.txt"], check=True)
    subprocess.run(["git", "-C", repo, "commit", "-q", "-m", "seed"], check=True)
    return repo


def _restore_into(worktree: str, state: dict) -> None:
    rt.restore_state(worktree, state)


def test_tracked_edit_roundtrips_lossless():
    """A tracked edit reconstructs with identical content."""
    repo = _make_repo()
    wt = tempfile.mkdtemp(prefix="rt-wt-")
    subprocess.run(["git", "-C", repo, "worktree", "add", "--detach", wt, "HEAD"], check=True)
    try:
        (Path(wt) / "seed.txt").write_text("seed\nEDITED\n")
        state = rt.capture_state(wt)
        rest = tempfile.mkdtemp(prefix="rt-rest-")
        subprocess.run(["git", "-C", repo, "worktree", "add", "--detach", rest, "HEAD"], check=True)
        try:
            _restore_into(rest, state)
            assert (Path(rest) / "seed.txt").read_text() == "seed\nEDITED\n", "tracked edit content lost"
        finally:
            subprocess.run(["git", "-C", repo, "worktree", "remove", "--force", rest], check=True)
    finally:
        subprocess.run(["git", "-C", repo, "worktree", "remove", "--force", wt], check=True)


def test_untracked_content_is_lost():
    """A subagent-created file reconstructs EMPTY — content is not captured.

    This is the honest gap: spawn_untracked records paths only. The status-based
    comparison in the round-trip script cannot see this; this content comparison
    pins it as a known lossy case.
    """
    repo = _make_repo()
    wt = tempfile.mkdtemp(prefix="rt-wt-")
    subprocess.run(["git", "-C", repo, "worktree", "add", "--detach", wt, "HEAD"], check=True)
    try:
        (Path(wt) / "new_file.py").write_text("def real():\n    return 42\n")
        state = rt.capture_state(wt)
        rest = tempfile.mkdtemp(prefix="rt-rest-")
        subprocess.run(["git", "-C", repo, "worktree", "add", "--detach", rest, "HEAD"], check=True)
        try:
            _restore_into(rest, state)
            restored = (Path(rest) / "new_file.py").read_text()
            # The gap: content is lost. This test documents the CURRENT behavior.
            assert restored == "", (
                f"expected empty placeholder (content not captured), got: {restored!r}"
            )
        finally:
            subprocess.run(["git", "-C", repo, "worktree", "remove", "--force", rest], check=True)
    finally:
        subprocess.run(["git", "-C", repo, "worktree", "remove", "--force", wt], check=True)


def test_untracked_path_is_present():
    """The untracked file's PATH is preserved even though content is lost."""
    repo = _make_repo()
    wt = tempfile.mkdtemp(prefix="rt-wt-")
    subprocess.run(["git", "-C", repo, "worktree", "add", "--detach", wt, "HEAD"], check=True)
    try:
        (Path(wt) / "new_file.py").write_text("content\n")
        state = rt.capture_state(wt)
        rest = tempfile.mkdtemp(prefix="rt-rest-")
        subprocess.run(["git", "-C", repo, "worktree", "add", "--detach", rest, "HEAD"], check=True)
        try:
            _restore_into(rest, state)
            assert (Path(rest) / "new_file.py").exists(), "untracked path not recreated"
        finally:
            subprocess.run(["git", "-C", repo, "worktree", "remove", "--force", rest], check=True)
    finally:
        subprocess.run(["git", "-C", repo, "worktree", "remove", "--force", wt], check=True)
