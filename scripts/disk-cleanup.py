#!/usr/bin/env python3
"""Disk auto-cleanup pipeline — archive stale intelligence / correction files."""
import json
import os
import shutil
import time
from pathlib import Path

STALE_DAYS = 30
STALE_SECS = STALE_DAYS * 86400

TARGET_DIRS = [
    Path.home() / ".hermes" / "intelligence",
    Path.home() / ".observeco",
]

ARCHIVE_DIR = Path.home() / ".observeco" / "archive"
REPORT_PATH = Path.home() / ".observeco" / "archive" / "last-cleanup.json"


def _should_skip(name: str) -> bool:
    """Skip dirs and known system files."""
    return name in (".", "..", ".DS_Store", "last-cleanup.json")


def run_cleanup(dry_run: bool = False) -> dict:
    now = time.time()
    total_freed = 0
    archived = 0

    for target in TARGET_DIRS:
        if not target.exists():
            continue
        for root, dirs, files in os.walk(str(target)):
            for fname in files:
                if _should_skip(fname):
                    continue
                fpath = Path(root) / fname
                try:
                    age = now - fpath.stat().st_mtime
                except OSError:
                    continue
                if age > STALE_SECS:
                    rel = fpath.relative_to(target)
                    arch_path = ARCHIVE_DIR / target.name / rel.parent
                    fsize = fpath.stat().st_size
                    if not dry_run:
                        arch_path.mkdir(parents=True, exist_ok=True)
                        dest = arch_path / fname
                        if dest.exists():
                            dest.unlink()
                        shutil.move(str(fpath), str(dest))
                    total_freed += fsize
                    archived += 1

    report = {
        "dry_run": dry_run,
        "archived_files": archived,
        "total_bytes_freed": total_freed,
        "total_mb_freed": round(total_freed / 1024 / 1024, 2),
        "total_gb_freed": round(total_freed / 1024 / 1024 / 1024, 4),
        "timestamp": int(time.time()),
        "stale_days": STALE_DAYS,
    }

    if not dry_run:
        ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
        REPORT_PATH.write_text(json.dumps(report, indent=2))

    return report


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Just report, don't move")
    args = parser.parse_args()

    report = run_cleanup(dry_run=args.dry_run)
    print(f"Disk cleanup: {report['archived_files']} files archived")
    print(f"Freed: {report['total_mb_freed']} MB ({report['total_gb_freed']} GB)")
    if report["archived_files"] == 0:
        print("No stale files found — everything is current.")
