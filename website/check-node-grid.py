#!/usr/bin/env python3
"""Runnable check for the interactive node grid in assets/draft.js.

The failure modes here are all SILENT: nodes that never fade in, a grid
that never fades out, a loop that spins forever on a hidden field, a
canvas that swallows clicks. None of them throw. So this drives the real
page in a real browser and asserts the behaviour.

Run:  ~/.hermes/hermes-agent/venv/bin/python check-node-grid.py [base_url]

Expects a static server for the site root on the given URL (default
http://127.0.0.1:8899). Exits non-zero on the first failed assertion.
"""
import sys
import time

from playwright.sync_api import sync_playwright

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8899"
PAGE = BASE + "/" + (sys.argv[2] if len(sys.argv) > 2 else "index.html")

failures = []


def check(label, cond, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}{(' — ' + detail) if detail else ''}")
    if not cond:
        failures.append(label)


# Read the live animation state out of the mounted grid. `fade` is a closure
# variable, so measure it the way a user would see it: mean alpha of the
# canvas pixels. Two probes, cursor moving vs cursor parked.
PROBE = """(() => {
  const c = document.querySelector('canvas.bg-nodes');
  if (!c) return {mounted: false};
  const g = c.getContext('2d');
  const d = g.getImageData(0, 0, c.width, c.height).data;
  let sum = 0, lit = 0;
  for (let i = 3; i < d.length; i += 4) { sum += d[i]; if (d[i] > 6) lit++; }
  return {mounted: true, meanAlpha: +(sum / (d.length / 4)).toFixed(3), litPixels: lit};
})()"""


with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 1200, "height": 900})
    pg.goto(PAGE, wait_until="load")
    pg.wait_for_timeout(600)

    print("mounted + inert")
    st = pg.evaluate("""(() => {
      const c = document.querySelector('canvas.bg-nodes');
      if (!c) return {mounted:false};
      const cs = getComputedStyle(c);
      return {mounted:true, pe: cs.pointerEvents, z: cs.zIndex,
              pos: cs.position, aria: c.getAttribute('aria-hidden'),
              w: c.width, h: c.height};
    })()""")
    check("canvas mounted", st.get("mounted") is True)
    if st.get("mounted"):
        check("pointer-events: none (never eats clicks)", st["pe"] == "none", st["pe"])
        check("aria-hidden (decorative)", st["aria"] == "true")
        check("positioned fixed", st["pos"] == "fixed", st["pos"])
        check("sized to viewport", st["w"] >= 1200 and st["h"] >= 900,
              f"{st['w']}x{st['h']}")

        # A click at a grid node's coordinates must reach the page underneath.
        hit = pg.evaluate("""(() => {
          const el = document.elementFromPoint(600, 450);
          return el ? el.tagName + '.' + (el.className||'').toString().slice(0,30) : null;
        })()""")
        check("clicks pass through to page content",
              hit is not None and "CANVAS" not in hit, str(hit))

    print("fades in while the cursor moves")
    for i in range(14):
        pg.mouse.move(300 + i * 40, 300 + (i % 3) * 60)
        pg.wait_for_timeout(45)
    moving = pg.evaluate(PROBE)
    check("grid is visible while moving",
          moving.get("litPixels", 0) > 200,
          f"lit={moving.get('litPixels')} meanAlpha={moving.get('meanAlpha')}")

    print("fades out once the cursor stops")
    pg.wait_for_timeout(700)          # still inside IDLE_MS: must stay up
    mid = pg.evaluate(PROBE)
    check("still visible right after stopping (not a snap-off)",
          mid.get("litPixels", 0) > 200, f"lit={mid.get('litPixels')}")

    pg.wait_for_timeout(6000)         # well past IDLE_MS + fade-out
    still = pg.evaluate(PROBE)
    check("dissolves to nothing when idle",
          still.get("litPixels", 0) == 0,
          f"lit={still.get('litPixels')} meanAlpha={still.get('meanAlpha')}")

    print("fades back in on the next move (loop parked, then wakes)")
    woken = False
    for i in range(16):
        pg.mouse.move(200 + i * 45, 500)
        pg.wait_for_timeout(45)
    after = pg.evaluate(PROBE)
    check("returns when the cursor moves again",
          after.get("litPixels", 0) > 200, f"lit={after.get('litPixels')}")

    print("idle CPU: loop must park, not spin")
    # Park it, then count OUR draw calls (clearRect on the node canvas), not
    # browser frames — a frame count passes even if our loop is still spinning.
    pg.wait_for_timeout(6500)
    draws = pg.evaluate("""(() => new Promise(res => {
      const c = document.querySelector('canvas.bg-nodes');
      const g = c.getContext('2d');
      let n = 0;
      const orig = g.clearRect.bind(g);
      g.clearRect = function(){ n++; return orig.apply(null, arguments); };
      setTimeout(() => { g.clearRect = orig; res(n); }, 1500);
    }))""")
    check("grid parks its draw loop while idle (0 draws in 1.5s)",
          draws == 0, f"draws={draws}")

    b.close()

print()
if failures:
    print(f"FAILED: {len(failures)} — {failures}")
    sys.exit(1)
print("all checks passed")
