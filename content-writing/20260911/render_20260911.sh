#!/bin/bash
# Render True Fitness package visuals via headless Chrome for Testing (no playwright needed).
set -e
BASE="/Users/seanfzc/projects/observeco-main/content-writing/20260911"
CHROME="/Users/seanfzc/Library/Caches/ms-playwright/chromium-1234/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing"

render() { # $1=html $2=w $3=h
  "$CHROME" --headless --disable-gpu --screenshot="$BASE/$1.png" --window-size="$2,$3" --hide-scrollbars "file://$BASE/$1.html"
  echo "Rendered $1"
}

render fig-true-01-numbers 1200 440
render fig-true-02-creditors 1200 440
render fig-true-03-precedent 1200 440
render banner-true-fitness 1200 480
echo "DONE"
