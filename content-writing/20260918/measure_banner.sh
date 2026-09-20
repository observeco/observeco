#!/bin/bash
# Banner-specific check: the banner grid is 1200x480.
# Locate the dark right panel (#2a2f36) and the banner top/bottom via the teal rule.
CHROME="/Users/seanfzc/Library/Caches/ms-playwright/chromium-1234/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing"
DIR="/Users/seanfzc/projects/observeco-main/content-writing/20260918"
TALL="$DIR/.measure/banner-tall.png"

"$CHROME" --headless --disable-gpu --screenshot="$TALL" --window-size=1200,900 --hide-scrollbars "file://$DIR/banner-waymo.html" 2>/dev/null

/usr/bin/python3 -c "
from PIL import Image
im=Image.open('$TALL').convert('RGB'); px=im.load()
# dark panel #2a2f36 lives only inside the banner -> gives exact top/bottom
ys=[y for y in range(im.height) if px[1000,y]==(42,47,54)]
xs=[x for x in range(im.width) if px[x,ys[0]+5]==(42,47,54)] if ys else []
print('dark panel: y', ys[0], '->', ys[-1], '| height', ys[-1]-ys[0]+1)
print('dark panel: x', xs[0], '->', xs[-1], '| width', xs[-1]-xs[0]+1)
print('banner target 1200x480 ->', 'FITS' if (ys[-1]-ys[0]+1)<=480 else 'OVERFLOW')
"
