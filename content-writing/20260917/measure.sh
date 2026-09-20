#!/bin/bash
# Measure natural content height for each visual (render tall, find last non-background row)
CHROME="/Users/seanfzc/Library/Caches/ms-playwright/chromium-1234/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing"
DIR="/Users/seanfzc/projects/observeco-main/content-writing/20260917"
TMP="$DIR/.measure"
mkdir -p "$TMP"

for f in fig-aom-01-material fig-aom-02-position fig-aom-03-nine banner-aomorie; do
  "$CHROME" --headless --disable-gpu --screenshot="$TMP/$f.png" --window-size=1200,1100 --hide-scrollbars "file://$DIR/$f.html" 2>/dev/null
done

/usr/bin/python3 -c "
from PIL import Image
import glob, os
for p in sorted(glob.glob('$TMP/*.png')):
    im=Image.open(p).convert('RGB'); px=im.load()
    bg=px[3,3]
    last=0
    for y in range(im.height-1,-1,-1):
        if any(px[x,y]!=bg for x in range(0,im.width,4)):
            last=y; break
    print(os.path.basename(p), '-> content bottom y =', last, '| needed height ~', last+1)
"
