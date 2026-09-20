#!/bin/bash
# Render figures + banner for the Aomorie content package (20260917)
# Plain-loop version (macOS bash 3.2 has no associative arrays).

CHROME="/Users/seanfzc/Library/Caches/ms-playwright/chromium-1234/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing"
DIR="/Users/seanfzc/projects/observeco-main/content-writing/20260917"

# name|width,height
ITEMS="fig-aom-01-material|1200,440
fig-aom-02-position|1200,440
fig-aom-03-nine|1200,440
banner-aomorie|1200,480"

while IFS='|' read -r name size; do
  [ -z "$name" ] && continue
  out="$DIR/$name.png"
  html="file://$DIR/$name.html"
  "$CHROME" --headless --disable-gpu --screenshot="$out" --window-size="$size" --hide-scrollbars "$html" 2>/dev/null
  echo "$name -> $out (window $size)"
done <<< "$ITEMS"

echo "--- verify dimensions (PNG header) ---"
/usr/bin/python3 -c "
import struct, glob, os
for p in sorted(glob.glob('$DIR/*.png')):
    w,h=struct.unpack('>II', open(p,'rb').read(24)[16:24])
    print(os.path.basename(p), w, h)
"
