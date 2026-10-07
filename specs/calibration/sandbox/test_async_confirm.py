"""Prove /confirm no longer blocks: measure the confirm response time, then poll /status.

The defect being closed (3.7.5): /confirm ran the whole pipeline inline, so the browser sat on a
blank page for ~4 minutes. It must now return in well under a second, with the work continuing in
the background and the result reachable at /status/<id>.

A pass needs BOTH:
  * /confirm returns fast (assert < 5s; it should be milliseconds)
  * the report becomes reachable afterwards (the work really did continue)
"""
import os
import re
import time

from playwright.sync_api import sync_playwright

URL = "http://%s:%s/" % (os.environ.get("PROBE_HOST", "127.0.0.1"),
                        os.environ.get("PROBE_PORT", "8765"))

with sync_playwright() as p:
    b = p.chromium.launch(headless=False)
    pg = b.new_page(viewport={"width": 1100, "height": 1000})

    pg.goto(URL, wait_until="domcontentloaded", timeout=45000)
    pg.fill("input[name=business_name]", "Async Check Co")
    pg.fill("input[name=email]", "async@observeco.test")
    pg.fill("input[name=category]", "F&B / salad and wraps")
    pg.fill("textarea[name=positioning_sentence]", "made-to-order salads for office workers")
    pg.fill("textarea[name=differentiator]", "cheaper and fresher than salad bars")
    pg.fill("input[name=competitors_named]", "SaladStop!, Supergreen")
    pg.fill("textarea[name=customer_description]", "office workers wanting a quick healthy lunch")

    print("STEP 1 — submit")
    pg.click("button[data-submit]")
    pg.wait_for_selector("text=Check your email", timeout=60000)
    href = pg.get_attribute("a[href^='/confirm']", "href")
    print("   confirm link len:", len(href or ""))
    link = "http://127.0.0.1:8765" + href

    print("\nSTEP 2 — confirm (TIMED)")
    t0 = time.time()
    pg.goto(link, wait_until="domcontentloaded", timeout=120000)
    dt = time.time() - t0
    body = pg.evaluate("() => document.body ? document.body.innerText : ''") or ""
    print("   /confirm returned in %.2fs  (was ~240s)" % dt)
    print("   shows the acknowledgement:", "running your review" in body.lower())
    print("   does NOT show a score   :", not re.search(r"\d+/100", body))
    print("   VERDICT /confirm fast   :", "✅ PASS" if dt < 5 else "✗ STILL BLOCKING")

    m = re.search(r"/status/(\d+)", pg.content())
    if not m:
        print("   !! no /status link on the acknowledgement page")
        b.close(); raise SystemExit(1)
    st = "http://127.0.0.1:8765" + m.group(0)
    print("\nSTEP 3 — poll", st)
    ok = False
    for i in range(40):
        time.sleep(10)
        pg.goto(st, wait_until="domcontentloaded", timeout=60000)
        t = pg.evaluate("() => document.body ? document.body.innerText : ''") or ""
        sc = re.search(r"(\d+/100\s*[—-]\s*[A-Za-z, ]+)", t)
        if sc:
            print("   ✅ REPORT after %ds: %s" % ((i + 1) * 10, sc.group(1).strip()))
            print("   dimension table:", "mental advantage" in t.lower() or "mental_advantage" in t)
            ok = True
            break
        if "could not produce" in t.lower():
            print("   ✗ run stopped:", t[:200].replace("\n", " "))
            break
        print("   ... %ds still running" % ((i + 1) * 10))
    print("\n   VERDICT work continued:", "✅ PASS" if ok else "✗ FAIL")
    b.close()
