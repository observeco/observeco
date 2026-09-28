#!/usr/bin/env python3
"""Prove the interaction lift actually reaches the pointer.

check-infographic-motion.py proves nothing loops; check-exhibit-settle.py
proves the reveals land. Neither says anything about HOVER. This reads the
computed style after a real pointer hover and asserts the surface MOVES --
a colour-only hover passes both of those and still feels dead.

Also asserts the two traps this fix had to dodge:
  * .btn:active (press feedback) must survive the hover transform
  * prefers-reduced-motion must disable the movement entirely

Run:  python3 website/check-interaction-lift.py
Exit: 0 = pass, 1 = fail.
"""

import pathlib
import sys
from glob import glob

from playwright.sync_api import sync_playwright

INDEX = pathlib.Path(__file__).with_name("index.html")
METHOD = pathlib.Path(__file__).with_name("method.html")

# Longer than the 0.24s transition so we read the SETTLED value, not a lerp.
SETTLE_MS = 450

CARDS = [".fork-card", ".stat-card", ".offer-card", ".case-card"]
# .card-item lives on method.html only -- keep it verified, don't assume
# the shared selector list covers it just because the source says so.
METHOD_CARDS = [".card-item"]

# The site sets `html { scroll-behavior: smooth }`. Playwright's hover()
# scrolls into view first, and the smooth scroll is still animating when the
# pointer lands -- the element slides out from under the cursor and :hover
# never matches. That is a harness artifact, not a site defect (a real user's
# pointer does not move because the page scrolled). Pin it to auto so the
# check measures hover, not scroll timing.
KILL_SMOOTH_SCROLL = "html { scroll-behavior: auto !important; }"

# index.html opens with a full-screen intro overlay (#sg-intro, position:fixed
# z-index:1000) that auto-dismisses 3.2s after load. Hovering before that
# measures the OVERLAY, not the page beneath it -- the hit-test lands on
# .map-card and :hover never reaches the card. Dismiss it explicitly so the
# check is not racing a 3.2s timer.
DISMISS_INTRO = """() => {
  const i = document.getElementById('sg-intro');
  if (i) i.style.display = 'none';
}"""

BUTTONS = [".btn-primary", ".btn-ghost"]


def _exe() -> str:
    """The installed chromium build (the pinned one 1.60.0 wants isn't present)."""
    return sorted(glob(str(pathlib.Path(
        "~/Library/Caches/ms-playwright/chromium-*/chrome-mac-arm64/"
        "Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing"
    ).expanduser())),
        key=lambda p: int(p.split("chromium-")[1].split("/")[0]))[-1]


def _translate_y(transform: str) -> float:
    """translateY out of a computed matrix(). 'none' -> 0.0."""
    if not transform or transform == "none":
        return 0.0
    inner = transform.split("(")[1].rstrip(")")
    parts = [p.strip() for p in inner.split(",")]
    return float(parts[5]) if len(parts) >= 6 else 0.0


def main() -> int:
    exe = _exe()
    failures: list[str] = []

    def check(label: str, ok: bool, got) -> None:
        print(f"  {'ok  ' if ok else 'FAIL'}  {label}\n        -> {got}")
        if not ok:
            failures.append(label)

    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=exe)
        try:
            page = browser.new_page()
            page.goto(INDEX.as_uri())
            page.add_style_tag(content=KILL_SMOOTH_SCROLL)
            page.evaluate(DISMISS_INTRO)

            # 1. Base state: nothing permanently shifted off its position.
            for sel in CARDS:
                v = _translate_y(page.eval_on_selector(
                    sel, "e => getComputedStyle(e).transform"))
                check(f"{sel} at rest is NOT shifted", v == 0.0, v)

            # 2. Cards LIFT under a real pointer hover.
            for sel in CARDS:
                page.mouse.move(0, 0)
                page.hover(sel)
                page.wait_for_timeout(SETTLE_MS)
                v = _translate_y(page.eval_on_selector(
                    sel, "e => getComputedStyle(e).transform"))
                check(f"{sel} lifts toward the cursor on hover", v < 0, v)

            # 3. CTAs LIFT, and the press state still fires.
            for sel in BUTTONS:
                page.mouse.move(0, 0)
                page.hover(sel)
                page.wait_for_timeout(SETTLE_MS)
                v = _translate_y(page.eval_on_selector(
                    sel, "e => getComputedStyle(e).transform"))
                check(f"{sel} lifts on hover", v < 0, v)

            page.mouse.move(0, 0)
            page.hover(".btn-primary")
            page.mouse.down()
            page.wait_for_timeout(SETTLE_MS)
            pressed = _translate_y(page.eval_on_selector(
                ".btn-primary", "e => getComputedStyle(e).transform"))
            page.mouse.up()
            check(".btn-primary still presses DOWN (:active survives)",
                  pressed > 0, pressed)

            # 4. method.html -- .card-item is a shared-selector member but only
            #    appears there, so it needs its own pass, not an assumption.
            mp = browser.new_page()
            try:
                mp.goto(METHOD.as_uri())
                mp.add_style_tag(content=KILL_SMOOTH_SCROLL)
                mp.evaluate(DISMISS_INTRO)
                for sel in METHOD_CARDS:
                    v = _translate_y(mp.eval_on_selector(
                        sel, "e => getComputedStyle(e).transform"))
                    check(f"{sel} (method.html) at rest is NOT shifted", v == 0.0, v)
                    mp.mouse.move(0, 0)
                    mp.hover(sel)
                    mp.wait_for_timeout(SETTLE_MS)
                    v = _translate_y(mp.eval_on_selector(
                        sel, "e => getComputedStyle(e).transform"))
                    check(f"{sel} (method.html) lifts on hover", v < 0, v)
            finally:
                mp.close()

            # 5. Reduced motion: the lift must be OFF, not merely un-animated.
            rm = browser.new_context(reduced_motion="reduce")
            try:
                rp = rm.new_page()
                rp.goto(INDEX.as_uri())
                rp.add_style_tag(content=KILL_SMOOTH_SCROLL)
                rp.evaluate(DISMISS_INTRO)
                for sel in CARDS + [".btn-primary"]:
                    rp.mouse.move(0, 0)
                    rp.hover(sel)
                    rp.wait_for_timeout(SETTLE_MS)
                    v = _translate_y(rp.eval_on_selector(
                        sel, "e => getComputedStyle(e).transform"))
                    check(f"reduced-motion: {sel} does NOT move", v == 0.0, v)
            finally:
                rm.close()
        finally:
            browser.close()

    print()
    if failures:
        print(f"FAIL: {len(failures)} interaction(s) have no motion "
              f"feedback: {failures}")
        return 1
    print("PASS: every hover target lifts, press feedback survives, "
          "and reduced-motion is respected.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
