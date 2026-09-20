#!/usr/bin/env python3
"""Render 2026-09-12 watch-tide visuals (package convention).

Usage: <hermes-venv-python> render_20260912.py
Requires: headless Chrome for Testing (chromium-1234) — see observeco-trending-content-package skill.
"""
import os
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
CHROME = os.path.expanduser(
    "~/Library/Caches/ms-playwright/chromium-1234/chrome-mac-arm64/"
    "Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing"
)

JOBS = [
    ("fig-watch-01-exports.html", "fig-watch-01-exports.png", "1200,440"),
    ("fig-watch-02-waves.html", "fig-watch-02-waves.png", "1200,440"),
    ("fig-watch-03-structure.html", "fig-watch-03-structure.png", "1200,440"),
    ("fig-watch-04-tides.html", "fig-watch-04-tides.png", "1200,440"),
    ("banner-watch-tide.html", "banner-watch-tide.png", "1200,480"),
]

for html, png, size in JOBS:
    src = os.path.join(HERE, html)
    out = os.path.join(HERE, png)
    subprocess.run(
        [CHROME, "--headless", "--disable-gpu",
         f"--screenshot={out}", f"--window-size={size}", "--hide-scrollbars",
         f"file://{src}"],
        check=True,
    )
    print(f"rendered {png}")
