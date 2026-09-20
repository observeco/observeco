#!/bin/bash
# TRUNCATION CHECK for the Matsuya package (20260918).
# Figures: span-scan with bg sampled ABOVE the card (padding:0 => flush card).
# Banner: probe the in-card dark panel (#2a2f36) for exact geometry.

CHROME="/Users/seanfzc/Library/Caches/ms-playwright/chromium-1234/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing"
DIR="/Users/seanfzc/projects/observeco-main/content-writing/20260918"
mkdir -p "$DIR/.measure"

for name in fig-mat-01-building fig-mat-02-axis fig-mat-03-tell; do
  tall="$DIR/.measure/$name-tall.png"
  "$CHROME" --headless --disable-gpu --screenshot="$tall" --window-size=1200,1000 --hide-scrollbars "file://$DIR/$name.html" 2>/dev/null
  /usr/bin/python3 -c "
from PIL import Image
im=Image.open('$tall').convert('RGB'); px=im.load()
bg=px[600,2]
first=last=None
for y in range(im.height):
    if any(px[x,y]!=bg for x in range(0,im.width,4)):
        if first is None: first=y
        last=y
h=(last-first+1) if first is not None else 0
print(f'$name  top {first} -> bottom {last+1} | height {h}  (canvas 440)  {\"FITS\" if h<=440 else \"OVERFLOW\"}')
"
done

TALL="$DIR/.measure/banner-matsuya-tall.png"
"$CHROME" --headless --disable-gpu --screenshot="$TALL" --window-size=1200,900 --hide-scrollbars "file://$DIR/banner-matsuya.html" 2>/dev/null
/usr/bin/python3 -c "
from PIL import Image
im=Image.open('$TALL').convert('RGB'); px=im.load()
ys=[y for y in range(im.height) if px[1000,y]==(42,47,54)]
xs=[x for x in range(im.width) if px[x,ys[0]+5]==(42,47,54)] if ys else []
h=ys[-1]-ys[0]+1; w=xs[-1]-xs[0]+1
print(f'banner-matsuya  dark panel {w}x{h}  (target panel 400x478)  {\"FITS\" if h<=480 else \"OVERFLOW\"}')
"
