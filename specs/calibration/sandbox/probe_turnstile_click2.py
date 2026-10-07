"""Click the Turnstile checkbox by coordinates (Playwright cannot see the isolated CF frame).

If a real human click produces a token, the "no token" report is closed. A Managed challenge is
SUPPOSED to resist automation, so a failure here is not necessarily a failure for Sean -- but a
success is conclusive.
"""
import os
import time

from playwright.sync_api import sync_playwright

URL = "http://%s:%s/" % (os.environ.get("PROBE_HOST", "127.0.0.1"),
                        os.environ.get("PROBE_PORT", "8765"))

with sync_playwright() as p:
    b = p.chromium.launch(headless=False)
    pg = b.new_page(viewport={"width": 1100, "height": 900})
    pg.goto(URL, wait_until="domcontentloaded", timeout=45000)
    time.sleep(6)

    print("iframes in DOM:", pg.eval_on_selector_all(
        "iframe", "els => els.map(e => (e.src||'').slice(0,80))"))

    w = pg.query_selector("div:has(> div > input[name=cf-turnstile-response])")
    w.scroll_into_view_if_needed()
    time.sleep(1)
    box = w.bounding_box()
    print("widget box after scroll:", box)

    # the checkbox sits on the left edge of the widget
    cx, cy = box["x"] + 26, box["y"] + box["height"] / 2
    print("clicking at", (cx, cy))
    pg.mouse.move(cx, cy)
    time.sleep(0.4)
    pg.mouse.click(cx, cy)

    tok = ""
    for i in range(30):
        time.sleep(2)
        tok = pg.eval_on_selector("input[name=cf-turnstile-response]", "e => e.value") or ""
        if tok:
            print("  ✅ TOKEN after %ds  len=%d  %s..." % ((i + 1) * 2, len(tok), tok[:45]))
            break
    if not tok:
        print("  ✗ no token after 60s (expected for an automated browser on a Managed challenge)")
    pg.screenshot(path="/tmp/turnstile-clicked.png")
    b.close()
