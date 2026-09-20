#!/bin/bash
# Render figures + banner for the CONSTRUCTION ROBOTS content package (20260917).
# Plain-loop version — macOS bash 3.2 has no associative arrays.
# Kept separate from render_20260917.sh (the Aomorie package in the same date folder).

CHROME="/Users/seanfzc/Library/Caches/ms-playwright/chromium-1234/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing"
DIR="/Users/seanfzc/projects/observeco-main/content-writing/20260917"

# name|width,height
ITEMS="fig-rob-01-arithmetic|1200,440
fig-rob-02-tender|1200,440
fig-rob-03-layers|1200,440
banner-construction-robots|1200,480"

while IFS='|' read -r name size; do
  [ -z "$name" ] && continue
  out="$DIR/$name.png"
  html="file://$DIR/$name.html"
  "$CHROME" --headless --disable-gpu --screenshot="$out" --window-size="$size" --hide-scrollbars "$html" 2>&1 | grep -i "written to file" || echo "  (no confirm for $name)"
done <<< "$ITEMS"

echo "--- verify dimensions (PNG header) ---"
/usr/bin/python3 -c "
import struct, glob, os
for p in sorted(glob.glob('$DIR/fig-rob-*.png')) + sorted(glob.glob('$DIR/banner-construction-robots.png')):
    w,h=struct.unpack('>II', open(p,'rb').read(24)[16:24])
    print(os.path.basename(p), w, h)
"
