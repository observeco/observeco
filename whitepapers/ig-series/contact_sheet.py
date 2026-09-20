#!/usr/bin/env python3
"""Build a review contact sheet: all slides of one post, side by side.

Run with the SYSTEM python (PIL is broken in the Hermes venv):
    env -u PYTHONPATH -u VIRTUAL_ENV /usr/bin/python3 contact_sheet.py [post]
"""
import glob
import sys

from PIL import Image

W, GAP, PAD = 340, 16, 20
BG = (226, 226, 222)


def main(post="post01"):
    files = sorted(f for f in glob.glob(f"{post}*.png")
                   if f.startswith("post") and "-slide" in f)
    if not files:
        sys.exit(f"no slides found for {post}")

    scaled = []
    for f in files:
        im = Image.open(f).convert("RGB")
        scaled.append(im.resize((W, round(W * im.height / im.width)), Image.LANCZOS))

    h = max(i.height for i in scaled)
    sheet = Image.new(
        "RGB",
        (PAD * 2 + W * len(scaled) + GAP * (len(scaled) - 1), h + PAD * 2),
        BG,
    )
    for i, im in enumerate(scaled):
        sheet.paste(im, (PAD + i * (W + GAP), PAD))

    out = f"CONTACT-SHEET-{post}.png"
    sheet.save(out)
    print(f"{out}  {sheet.size}  ({len(files)} slides)")


if __name__ == "__main__":
    main(*sys.argv[1:])
