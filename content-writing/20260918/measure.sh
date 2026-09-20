#!/bin/bash
# TRUNCATION CHECK — measure natural content height of each figure.
# Renders tall, then scans up from the bottom for the last non-background row.
# bg is sampled at y=2 (above the card) because cards rendered flush to the
# viewport edge (padding:0) would otherwise be sampled as their own background.

CHROME="/Users/seanfzc/Library/Caches/ms-playwright/chromium-1234/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing"
DIR="/Users/seanfzc/projects/observeco-main/content-writing/20260918"
mkdir -p "$DIR/.measure"

for name in fig-way-01-inversion fig-way-02-numbers fig-way-03-open banner-waymo; do
  tall="$DIR/.measure/$name-tall.png"
  "$CHROME" --headless --disable-gpu --screenshot="$tall" --window-size=1200,1100 --hide-scrollbars "file://$DIR/$name.html" 2>/dev/null
  /usr/bin/python3 -c "
from PIL import Image
im=Image.open('$tall').convert('RGB'); px=im.load()
bg=px[600,2]                     # above the card, always canvas
first=last=None
for y in range(im.height):
    if any(px[x,y]!=bg for x in range(0,im.width,4)):
        if first is None: first=y
        last=y
print('$name  card top', first, '-> bottom', last+1, '| height', (last-first+1) if first is not None else 0, '(canvas: 440 fig / 480 banner)')
"
done
