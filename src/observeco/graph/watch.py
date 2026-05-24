"""`observeco graph watch` — Intelligence-driven file watcher. Re-indexes on change."""

from __future__ import annotations

import hashlib
import sys
import time
from pathlib import Path

from observeco.graph.indexer import Indexer


def run_graph_watch(
    directory: str = ".",
    recursive: bool = True,
    once: bool = False,
    interval: int = 5,
) -> None:
    """Watch Python files in a directory and re-index on change.

    Uses the same intelligence-driven pattern as heal/pulse monitoring.
    Polls filesystem for changes rather than watchdog events (no daemon dependency),
    but the architecture is identical: detect → compute hash → diff → re-index.
    """
    indexer = Indexer()
    root = Path(directory).resolve()

    # Track file state: path → (mtime_ns, size, content_hash)
    file_state: dict[str, tuple[int, int, str]] = {}

    def _scan_and_reindex() -> int:
        """Scan all .py files, re-index changed ones. Returns count of changed files."""
        pattern = "**/*.py" if recursive else "*.py"
        changed_count = 0

        current_files = set()
        for pyfile in root.glob(pattern):
            # Skip common exclusions
            parts = pyfile.parts
            if any(ex in parts for ex in ("__pycache__", ".git", "venv", ".venv",
                                           "node_modules", ".egg-info", "references")):
                continue

            fpath = str(pyfile)
            current_files.add(fpath)

            try:
                stat = pyfile.stat()
                mtime = stat.st_mtime_ns
                size = stat.st_size

                if fpath in file_state:
                    prev_mtime, prev_size, prev_hash = file_state[fpath]
                    # Quick check: mtime and size same → skip hash
                    if prev_mtime == mtime and prev_size == size:
                        continue
                    # Might be changed — re-index
                    source = pyfile.read_text("utf-8")
                    new_hash = hashlib.sha256(source.encode()).hexdigest()
                    if new_hash == prev_hash:
                        file_state[fpath] = (mtime, size, new_hash)
                        continue  # False positive (touch without content change)

                    # Real change detected
                    result = indexer.index_file(fpath, source)
                    file_state[fpath] = (mtime, size, new_hash)
                    changed_count += 1
                    if result.get("status") == "indexed":
                        print(f"  Re-indexed: {fpath} ({result['nodes']} nodes, {result['edges']} edges)")
                    continue

                # New file
                source = pyfile.read_text("utf-8")
                new_hash = hashlib.sha256(source.encode()).hexdigest()
                result = indexer.index_file(fpath, source)
                file_state[fpath] = (mtime, size, new_hash)
                if result.get("status") == "indexed":
                    changed_count += 1
                    print(f"  New: {fpath} ({result['nodes']} nodes)")
                elif result.get("status") == "unchanged":
                    file_state[fpath] = (mtime, size, new_hash)

            except Exception as e:
                print(f"  Error scanning {fpath}: {e}", file=sys.stderr)

        # Check for deleted files
        tracked = set(file_state.keys())
        deleted = tracked - current_files
        for fpath in deleted:
            print(f"  Removed: {fpath}")
            indexer.db.remove_file(fpath)
            del file_state[fpath]
            changed_count += 1

        return changed_count

    print(f"ObserveCo Graph Watch — watching {root}/ for changes")
    stats = indexer.db.get_stats()
    if stats.get("files", 0) > 0:
        print(f"  Currently indexed: {stats['files']} files, {stats['nodes']} nodes, {stats['edges']} edges")
    else:
        print("  No indexed files yet. First scan will index the directory...")

    # Initial scan
    first_run = True
    while True:
        if first_run or not once:
            changed = _scan_and_reindex()
            if changed > 0 or first_run:
                stats = indexer.db.get_stats()
                print(f"  Graph: {stats['files']} files, {stats['nodes']} nodes, {stats['edges']} edges")
            first_run = False

        if once:
            break

        time.sleep(interval)
