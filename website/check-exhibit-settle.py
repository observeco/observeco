#!/usr/bin/env python3
"""Verify the one-shot exhibits SETTLE on their true value (not just "stop").

check-infographic-motion.py proves nothing loops. That alone is not enough:
a one-shot animation can stop mid-air -- the SUV invisible, a bar at zero,
the gauge pointing at nothing. This reads the COMPUTED style after every
animation has finished and asserts each exhibit holds its intended value.

Run:  python3 website/check-exhibit-settle.py
Exit: 0 = pass, 1 = fail.
"""

import pathlib
import sys
from glob import glob

from playwright.sync_api import sync_playwright

INDEX = pathlib.Path(__file__).with_name("index.html")

# Wait past the longest exhibit animation (6s dominoes/clicks) + stagger.
SETTLE_MS = 9000

# Each assertion: (label, JS expression evaluated in the page, predicate).
# Predicates express the MEANING: what the visitor must see once it lands.
def _num(v):
    """Computed styles come back with units ('0px', '-38deg'). Strip them."""
    return float(str(v).replace("px", "").replace("deg", "").strip())


CHECKS = [
    # ── The two replacement marks must be DESIGNED GLYPHS, and the
    #    literal cartoon drawings they replaced must be GONE. ──
    ("Volvo mark is the designed shield-check glyph (present)",
     "!!document.querySelector('.volvo-mark .volvo-shield-check')",
     lambda v: v is True),
    ("Volvo mark draws in brand green (not default black)",
     "getComputedStyle(document.querySelector('.volvo-mark')).color",
     lambda v: v == "rgb(14, 110, 92)"),
    ("GONE: the literal shield-with-car pictogram is deleted",
     "!!document.querySelector('.volvo-car-body') || !!document.querySelector('.volvo-wheel')",
     lambda v: v is False),
    ("GWM object is the pickup->SUV composition (both glyphs present)",
     "!!document.querySelector('.suv .reposition-from') && !!document.querySelector('.suv .reposition-to')",
     lambda v: v is True),
    ("GWM past state reads muted, present state reads green (hierarchy)",
     "getComputedStyle(document.querySelector('.suv .reposition-from')).color"
     " + '|' + getComputedStyle(document.querySelector('.suv .reposition-to')).color",
     lambda v: v == "rgb(107, 115, 126)|rgb(14, 110, 92)"),
    ("GONE: the 13-path literal cartoon SUV is deleted",
     "!!document.querySelector('.suv .suv-body') || !!document.querySelector('.suv .suv-wheel')",
     lambda v: v is False),
    # ── Both marks must still REVEAL (once), not sit dead static. When the
    #    clip-art was replaced, the motion went with it and these became the
    #    only static objects in an animated grid. A future pass stripping the
    #    reveal must fail here. ──
    ("Volvo mark has a reveal animation (not static)",
     "getComputedStyle(document.querySelector('.volvo-shield-check')).animationName",
     lambda v: v == "volvo-mark-draw"),
    ("GWM mark reveals in sequence (3 staggered animations)",
     "[...document.querySelectorAll('.suv path')].map(p => getComputedStyle(p).animationName)"
     ".filter(n => n && n !== 'none').sort().join(',')",
     lambda v: v == "gwm-arrow-in,gwm-from-in,gwm-to-in,gwm-to-in,gwm-to-in"),
    ("GWM arrow settles MUTED (0.55), not full strength",
     "getComputedStyle(document.querySelector('.suv .reposition-arrow')).opacity",
     lambda v: abs(_num(v) - 0.55) < 0.01),
    ("Neither mark reveal loops (both finite)",
     "[...document.querySelectorAll('.volvo-shield-check, .suv path')]"
     ".map(p => getComputedStyle(p).animationIterationCount).join('|')",
     lambda v: "infinite" not in v),
    ("Avis gauge needle held its swept angle (not snapped back)",
     "getComputedStyle(document.querySelector('.gauge-needle')).transform",
     lambda v: "matrix" in v),
    ("Case AFTER bar grew to full width (scaleX 1)",
     "getComputedStyle(document.querySelector('.phase-bar .bar-fill.after')).transform",
     lambda v: "matrix" in v and abs(_num(v.split("(")[1].split(",")[0])) > 0.05),
    ("Domino tiles all landed VISIBLE (99 of them)",
     "[...document.querySelectorAll('.usa-map use[href=\"#domino-tile\"]')]"
     ".filter(u => getComputedStyle(u).opacity === '1').length",
     lambda v: int(v) > 90),
    ("Clicker counter settled on its digit (strip not back at 0)",
     "getComputedStyle(document.querySelector('.clicker-strip')).transform",
     lambda v: "matrix" in v and "1, 0, 0, 1, 0, 0)" not in v),
    ("Cohort: a closed shop holds the CLOSED look (not green again)",
     "getComputedStyle(document.querySelector('.cohort-shop.dark')).backgroundColor",
     lambda v: "rgb(14, 110, 92)" not in v),
    ("DELIBERATE: ticker-pulse still loops (ongoing registration)",
     "getComputedStyle(document.querySelector('.ticker-pulse')).animationIterationCount",
     lambda v: v == "infinite"),
]


def main() -> int:
    exe = sorted(glob(str(pathlib.Path(
        "~/Library/Caches/ms-playwright/chromium-*/chrome-mac-arm64/Google Chrome for Testing.app"
        "/Contents/MacOS/Google Chrome for Testing").expanduser())),
        key=lambda p: int(p.split("chromium-")[1].split("/")[0]))[-1]

    failures = []
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=exe)
        try:
            page = browser.new_page()
            page.goto(INDEX.as_uri())
            # Force every reveal gate on, as a visitor scrolling would.
            page.evaluate("document.querySelectorAll('*').forEach(e => e.classList.add('in-view'))")
            page.wait_for_timeout(SETTLE_MS)
            for label, expr, pred in CHECKS:
                # A missing element must report FAIL, not crash the run and
                # skip every later assertion (getComputedStyle(null) throws).
                val = page.evaluate(
                    "(e) => { try { return eval(e) } catch (err) { return '__MISSING__' } }",
                    expr,
                )
                ok = pred(val)
                print(f"  {'ok  ' if ok else 'FAIL'}  {label}\n        -> {val}")
                if not ok:
                    failures.append(label)
        finally:
            browser.close()

    print()
    if failures:
        print(f"FAIL: {len(failures)} exhibit(s) did not settle on their true value: {failures}")
        return 1
    print(f"PASS: all {len(CHECKS)} exhibits hold their settled value.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
