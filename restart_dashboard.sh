#!/usr/bin/env bash
# Restart the ObserveCo dashboard cleanly on port 8899.
# launchd manages a single instance via KeepAlive — do NOT pkill here, because
# the freshly-exec'd process also matches "observeco dashboard" and would kill
# itself (the old flapping bug). launchd guarantees one instance; we only wait
# for the port to be free before exec.
set -u

PORT=8899
VENV_PY="/Users/seanfzc/projects/observeco/.venv/bin/python3"
LOG_DIR="/Users/seanfzc/.observeco/logs"
mkdir -p "$LOG_DIR"

# Wait until port is actually free (max ~15s). The killed process's socket can
# linger in TIME_WAIT, so polling is safer than a fixed sleep.
for i in $(seq 1 30); do
  if ! curl -s -o /dev/null --max-time 1 "http://127.0.0.1:${PORT}/" 2>/dev/null; then
    if ! lsof -i :${PORT} -sTCP:LISTEN >/dev/null 2>&1; then
      break
    fi
  fi
  sleep 0.5
done

# Hand off to the real process (exec replaces this shell; launchd tracks python)
exec "$VENV_PY" -u /Users/seanfzc/projects/observeco/.venv/bin/observeco dashboard --port ${PORT} --no-browser
