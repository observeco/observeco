"""CLI commands for the Anomaly Detection plugin."""

from __future__ import annotations

import argparse
import json
import sys

from .anomaly_core import detect_anomalies, format_anomalies
from . import STATE_DB


def register_cli(subparser: argparse.ArgumentParser) -> None:
    subs = subparser.add_subparsers(dest="anomaly_action")

    # scan
    scan_p = subs.add_parser("scan", help="Scan for anomalies")
    scan_p.add_argument("--lookback", type=int, default=60, help="Lookback minutes (default: 60)")
    scan_p.add_argument("--json", action="store_true", help="Output as JSON")

    subparser.set_defaults(func=anomaly_command)


def anomaly_command(args: argparse.Namespace) -> int:
    action = getattr(args, "anomaly_action", None)
    if not action:
        print("Usage: hermes anomaly {scan}")
        return 2

    try:
        if action == "scan":
            return _cmd_scan(args)
        else:
            print(f"Unknown anomaly action: {action}")
            return 2
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def _cmd_scan(args) -> int:
    if not STATE_DB.exists():
        print(f"state.db not found at {STATE_DB}")
        return 1

    anomalies = detect_anomalies(str(STATE_DB), lookback_minutes=args.lookback)

    if args.json:
        print(json.dumps(anomalies, indent=2))
    else:
        print(f"Anomaly Scan — last {args.lookback} minutes")
        print()
        print(format_anomalies(anomalies))

    return 0 if not anomalies else 1  # exit 1 if anomalies found (for CI)