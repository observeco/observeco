#!/usr/bin/env python3
"""
Extract the Book 1 cover panels used to OPEN each IG carousel post.

Source of truth: the shipped full-wrap proof
    whitepapers/print/output/final-design/exported/COVER-book1-Signboard-FINAL-print.png
3429x2550 at 3x (trim 5.5x8.5in; back 550 | spine 43 | front 550 design px).

Outputs:
    assets/cover-front.png   front cover, hero-sized
    assets/cover-back.png    back cover, artifact-sized

Run with SYSTEM python (PIL is broken in the Hermes venv):
    env -u PYTHONPATH -u VIRTUAL_ENV /usr/bin/python3 make_covers.py
"""
import os

from PIL import Image

BASE = os.path.dirname(os.path.abspath(__file__))
WRAP = ("/Users/seanfzc/projects/observeco-main/whitepapers/print/output/"
        "final-design/exported/COVER-book1-Signboard-FINAL-print.png")
OUT = os.path.join(BASE, "assets")

# design-space panel geometry (px at 100 px/in), scaled to the exported image
DESIGN_W, SPINE_W = 550, 43
TOTAL_W = DESIGN_W + SPINE_W + DESIGN_W      # 1143

HERO_H = 840        # front cover height on the slide (the hero)
ARTIFACT_H = 340    # back cover height on the slide (proof artifact)

LANCZOS = Image.Resampling.LANCZOS


def fit(panel, height):
    return panel.resize((round(height * panel.width / panel.height), height), LANCZOS)


def main():
    os.makedirs(OUT, exist_ok=True)
    wrap = Image.open(WRAP).convert("RGB")
    scale = wrap.width / TOTAL_W
    h = wrap.height
    print(f"wrap {wrap.size}  scale {scale}")

    # back = 0..550 | spine = 550..593 | front = 593..1143  (design px)
    front = fit(wrap.crop((int((DESIGN_W + SPINE_W) * scale), 0, wrap.width, h)), HERO_H)
    back = fit(wrap.crop((0, 0, int(DESIGN_W * scale), h)), ARTIFACT_H)

    for name, im in (("cover-front", front), ("cover-back", back)):
        path = os.path.join(OUT, f"{name}.png")
        im.save(path, optimize=True)
        print(f"  {name}.png  {im.size}  ({os.path.getsize(path) // 1024} KB)")


if __name__ == "__main__":
    main()
