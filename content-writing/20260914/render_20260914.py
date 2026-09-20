#!/usr/bin/env python3
"""Render 2026-09-12 cyber-insurance visuals (package convention).

Usage: <hermes-venv-python> render_20260914.py
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
    ("fig-cyb-01-arithmetic.html", "fig-cyb-01-arithmetic.png", "1200,440"),
    ("fig-cyb-02-rejects-price.html", "fig-cyb-02-rejects-price.png", "1200,440"),
    ("fig-cyb-03-minimums.html", "fig-cyb-03-minimums.png", "1200,440"),
    ("fig-cyb-04-compliance.html", "fig-cyb-04-compliance.png", "1200,440"),
    ("banner-cyber-insurance.html", "banner-cyber-insurance.png", "1200,480"),
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
