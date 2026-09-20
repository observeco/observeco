#!/bin/bash
# SG Trends daily runner — collector + quality gate.
#
# Why this exists: the collector needs Playwright, and the interpreter holding a
# *working* Playwright + Chromium is not always the project venv. Hardcoding
# `.venv/bin/python` in the cron prompt silently rots when the venv is
# reprovisioned. Observed 2026-09-16:
#   observeco-main/.venv/bin/python  -> no playwright module at all
#   /usr/bin/python3 (3.9)           -> playwright present, chromium build 1223 MISSING
#   .hermes/hermes-agent/venv        -> playwright + chromium 1234 present, launches OK
# A bare `import playwright` check is NOT enough — it passes on the 3.9
# interpreter whose browser binary is absent. So this checks the chromium
# executable playwright would actually use.
#
# ponytail: interpreter list is hardcoded, with SG_TRENDS_PYTHON as the override.
# Upgrade path: provision playwright into the project venv and delete the search
# loop and the candidate list entirely.
#
# Usage: scripts/run_sg_trends.sh [--out DIR]
# Exit:  0 gate pass · 1 gate fail (stale/regression) · 2 collector could not run

set -uo pipefail

cd "$(dirname "$0")/.." || exit 2

CANDIDATES=(
  "${SG_TRENDS_PYTHON:-}"
  "/Users/seanfzc/.hermes/hermes-agent/venv/bin/python"
  ".venv/bin/python"
  "/usr/bin/python3"
)

PY=""
for cand in "${CANDIDATES[@]}"; do
  [ -n "$cand" ] || continue
  [ -x "$cand" ] || continue
  if "$cand" - <<'PYCHECK'
import os, sys
try:
    from playwright.sync_api import sync_playwright
except Exception:
    sys.exit(1)
with sync_playwright() as p:
    sys.exit(0 if os.path.exists(p.chromium.executable_path) else 1)
PYCHECK
  then
    PY="$cand"
    break
  fi
done

if [ -z "$PY" ]; then
  echo "FATAL: no interpreter found with a working Playwright + Chromium."
  echo "Tried: ${CANDIDATES[*]}"
  echo "Fix: 'playwright install chromium' for one of them, or set SG_TRENDS_PYTHON."
  exit 2
fi

echo "interpreter: $PY"
echo

"$PY" scripts/sg_trends_collect.py "$@" || {
  echo "FATAL: collector failed (see traceback above)."
  exit 2
}

echo
echo "=== quality gate (stale + SG-precision) ==="
"$PY" scripts/sg_trends_quality.py --days 2
GATE=$?

echo
if [ "$GATE" -eq 0 ]; then
  echo "GATE: PASS"
else
  echo "GATE: FAIL (exit $GATE) — digest carries stale or non-SG rows. Report this loudly; do not present the digest as today's signal."
fi
exit "$GATE"
