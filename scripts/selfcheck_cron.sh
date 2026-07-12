#!/usr/bin/env bash
# ObserveCo turn-capture self-check watchdog.
# Runs the pipeline health probe daily. Silent on success (no Hermes message).
# On failure, surfaces the assertion detail so it lands in the Alerts tab.
set -uo pipefail
PY="/opt/homebrew/opt/python@3.14/bin/python3.14"
REPO="/Users/seanfzc/projects/observeco"
OUT="$($PY -m observeco.cli selfcheck 2>&1)"
CODE=$?
if [ "$CODE" -ne 0 ]; then
  echo "$OUT"   # non-empty stdout -> Hermes delivers the failure alert
fi
exit "$CODE"
