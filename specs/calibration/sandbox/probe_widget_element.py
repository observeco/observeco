"""Capture the Turnstile widget itself, in a HEADED browser (closer to Sean's real one).

Screenshots just the widget element, dumps its text (Cloudflare writes the error INSIDE it),
its computed size, and every cloudflare response status. Headless browsers are often refused by
Turnstile, so a headed run is the fair test.
"""
import time

from playwright.sync_api import sync_playwright

import os
URL = "http://%s:%s/" % (os.environ.get("PROBE_HOST", "127.0.0.1"), os.environ.get("PROBE_PORT", "8765"))
reqs, logs = [], []

with sync_playwright() as p:
    b = p.chromium.launch(headless=False)
    pg = b.new_page(viewport={"width": 1100, "height": 900})
    pg.on("console", lambda m: logs.append("[%s] %s" % (m.type, m.text[:200])))
    pg.on("pageerror", lambda e: logs.append("[pageerror] %s" % str(e)[:200]))
    pg.on("response", lambda r: reqs.append("%s -> %s" % (r.url[:110], r.status))
          if "cloudflare" in r.url else None)

    pg.goto(URL, wait_until="load", timeout=45000)
    pg.wait_for_timeout(9000)                      # give the challenge time to resolve

    w = pg.query_selector(".cf-turnstile")
    if w:
        w.scroll_into_view_if_needed()
        pg.wait_for_timeout(1500)
        w.screenshot(path="/tmp/turnstile_element.png")
        print("widget element screenshot -> /tmp/turnstile_element.png")
    else:
        print("!! no .cf-turnstile element in the DOM")

    info = pg.evaluate("""() => {
        const w = document.querySelector('.cf-turnstile');
        const i = document.querySelector('[name="cf-turnstile-response"]');
        if (!w) return {err: 'widget element missing'};
        const r = w.getBoundingClientRect();
        return {
            text: (w.innerText || '').trim().slice(0, 300),
            html: w.innerHTML.slice(0, 500),
            iframes: w.querySelectorAll('iframe').length,
            token_len: i ? (i.value || '').length : -1,
            box: {w: Math.round(r.width), h: Math.round(r.height)},
        };
    }""")
    print("\n=== widget state ===")
    for k, v in info.items():
        print("   %-10s %s" % (k, v))

    print("\n=== cloudflare responses ===")
    for r in reqs or ["(none)"]:
        print("   ", r)

    print("\n=== console ===")
    for l in logs or ["(none)"]:
        print("   ", l)

    pg.wait_for_timeout(1000)
    b.close()
