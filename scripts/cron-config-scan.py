#!/usr/bin/env python3
"""Config hygiene cron — daily scheduled scan + drift detection.

Runs once daily. If config hygiene score drops below threshold,
logs a drift event and surfaces to dashboard.

Usage:
    python3 observeco/scripts/cron-config-scan.py
"""
import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from observeco.chisel.config_scanner import scan_config, CONFIG_PATH


def main():
    report = scan_config(CONFIG_PATH)

    # Log results for dashboard consumption
    output_path = Path.home() / ".hermes" / "cron" / "output" / "config-hygiene.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "ts": int(__import__("time").time()),
        "config_health_score": report.config_health_score,
        "total_waste_tok": report.total_waste_tok,
        "finding_count": len(report.findings),
        "findings": [
            {
                "check": f.check,
                "severity": f.severity,
                "description": f.description[:100],
                "estimated_waste_tok": f.estimated_waste_tok,
            }
            for f in report.findings
        ],
    }
    output_path.write_text(json.dumps(data, indent=2))

    # If score dropped significantly, surface as drift
    # (Comparison would need previous state — for now just log)
    print(f"Config health: {report.config_health_score}/100, {len(report.findings)} findings, ~{report.total_waste_tok} tok/session waste")


if __name__ == "__main__":
    main()