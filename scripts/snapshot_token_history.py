#!/usr/bin/env python3
"""Daily cron: snapshot fleet tokens into token_history table.

Called by Hermes cron. Hits the dashboard API endpoint to record today's
fleet token usage so the 90-day trend chart shows real data.
"""
import json
import os
import sys
import time
import urllib.request
from pathlib import Path

DASHBOARD_URL = os.environ.get("OBSERVECO_DASHBOARD_URL", "http://localhost:8123")
# Read token from env or the persisted secret file
TOKEN = os.environ.get("OBSERVECO_TOKEN", "")
if not TOKEN:
    secret_path = Path.home() / ".observeco" / ".dashboard_secret"
    if secret_path.exists():
        TOKEN = secret_path.read_text().strip()


def snapshot():
    url = f"{DASHBOARD_URL}/api/token-history/snapshot"
    req = urllib.request.Request(url, method="POST")
    if TOKEN:
        req.add_header("X-ObserveCo-Token", TOKEN)
    req.add_header("Content-Type", "application/json")

    # Retry up to 3 times with backoff for transient failures (dashboard restart)
    last_err = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read())
                if data.get("ok"):
                    print(f"✅ Snapshot recorded: {data['input_tokens']} input tokens, {data['agents']} agents")
                else:
                    print(f"⚠️ Snapshot endpoint returned: {data}")
                return
        except Exception as e:
            last_err = e
            if attempt < 2:
                time.sleep(2 ** attempt)  # 1s, 2s backoff
            continue

    print(f"❌ Snapshot failed after 3 attempts: {last_err}", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    snapshot()
