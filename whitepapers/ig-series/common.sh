# Shared config for the IG carousel scripts. Source this, don't re-declare.
#   . "$(dirname "$0")/common.sh"

DIR="/Users/seanfzc/projects/observeco-main/whitepapers/ig-series"

# Chrome for Testing (Playwright cache). file:// is blocked in the Hermes browser
# tool, so every render/measure step goes through headless Chrome instead.
CHROME="/Users/seanfzc/Library/Caches/ms-playwright/chromium-1234/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing"

# PIL is broken in the Hermes venv (ImportError: _imaging) — use system python.
PY="env -u PYTHONPATH -u VIRTUAL_ENV /usr/bin/python3"
