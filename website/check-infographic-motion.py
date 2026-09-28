#!/usr/bin/env python3
"""Assert every home-tab infographic settles once (no infinite loops).

Why this exists: the case-grid and stats-grid exhibits used to run their
reveals on `infinite` 5-6s loops -- bars re-grew, the Great Wall SUV
re-drove in, dominoes re-rippled. Read as a toy, not as data ("looks too
kiddish"). They must settle once, like the site's chart primitives
(.bar / .scurve / .flat-line), which were always one-shot.

This is the one runnable check: it renders index.html in a real browser,
forces every reveal gate on, and reads the COMPUTED animation state.
Measuring beats trusting the stylesheet.

Run:  python3 website/check-infographic-motion.py
Exit: 0 = pass, 1 = fail.
"""

import pathlib
import sys
from glob import glob

from playwright.sync_api import sync_playwright

INDEX = pathlib.Path(__file__).with_name("index.html")
SCOPES = [".case-grid", ".stats-grid", ".process-flow"]

# Deliberately still looping: these are NOT reveal animations. They signal
# ONGOING activity, which is the truthful reading of the data behind them.
# Anything NOT listed here that loops is a regression.
#   ticker-pulse  — "~1 registration every 7 min": a heartbeat, still true.
#   icon-ring-loop — process strip's soft "the process is alive" halo.
ALLOWED_LOOPING = {"ticker-pulse", "icon-ring-loop"}


def installed_chromium():
    """Playwright's pinned build may not be the one on disk (we have 1228/1234,
    the driver wanted 1223). Use rung 4: the already-installed binary.
    ponytail: newest ms-playwright chromium, no download. If a specific build
    is ever required, pin it here instead of globbing."""
    pats = [
        "~/Library/Caches/ms-playwright/chromium-*/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing",
        "~/Library/Caches/ms-playwright/chromium-*/chrome-linux/chrome",
    ]
    found = [p for pat in pats for p in glob(str(pathlib.Path(pat).expanduser()))]
    return sorted(found, key=lambda p: int(p.split("chromium-")[1].split("/")[0]))[-1] if found else None

PROBE = """
(scopes) => {
  const out = [];
  // Strip the injected .in-view so the reported selector is the real one.
  const clean = (el) => {
    const cls = (el.getAttribute('class') || '').split(/\\s+/)
      .filter(c => c && c !== 'in-view').join('.');
    return el.tagName.toLowerCase() + (cls ? '.' + cls : '');
  };
  const push = (scope, el, pseudo, cs) => {
    if (!cs.animationName || cs.animationName === 'none') return;
    out.push({
      scope,
      sel: clean(el) + pseudo,
      name: cs.animationName,
      iter: cs.animationIterationCount,
    });
  };
  for (const scope of scopes) {
    for (const el of document.querySelectorAll(scope + ' *')) {
      push(scope, el, '', getComputedStyle(el));
      push(scope, el, '::after', getComputedStyle(el, '::after'));
      push(scope, el, '::before', getComputedStyle(el, '::before'));
    }
  }
  return out;
}
"""


def main() -> int:
    exe = installed_chromium()
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=exe) if exe else p.chromium.launch()
        try:
            page = browser.new_page()
            page.goto(INDEX.as_uri())
            page.wait_for_timeout(300)
            # Force all reveal gates on so computed styles show animated state.
            page.evaluate("document.querySelectorAll('*').forEach(e => e.classList.add('in-view'))")
            page.wait_for_timeout(150)
            rows = page.evaluate(PROBE, SCOPES)
        finally:
            browser.close()

    looping = [r for r in rows if "infinite" in r["iter"]]
    allowed = [r for r in looping if r["name"] in ALLOWED_LOOPING]
    looping = [r for r in looping if r["name"] not in ALLOWED_LOOPING]
    print(f"animated declarations inside {SCOPES}: {len(rows)}")

    if looping:
        groups = {}
        for r in looping:
            groups.setdefault((r["name"], r["iter"]), []).append(r)
        for (name, it), rs in sorted(groups.items()):
            print(f"  LOOPING  {name:<28} iter={it:<9} x{len(rs):<4} e.g. {rs[0]['sel'][:48]}")
        print(f"\nFAIL: {len(looping)} infographic animation(s) still loop forever "
              f"across {len(groups)} keyframe(s).")
        return 1

    settles = sorted({r["name"] for r in rows if r["name"] not in ALLOWED_LOOPING})
    print(f"  settle-once keyframes ({len(settles)}): " + ", ".join(settles))
    print(f"  allowed ongoing: {sorted({r['name'] for r in allowed})}")
    print(f"\nPASS: {len(rows)} infographic animations; every reveal settles "
          f"(no unintended infinite iteration).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
