"""Prove the local bypass works end-to-end, in a REAL browser: form -> submit -> confirm -> report.

Runs against the loopback instance started with SANDBOX_SKIP_CAPTCHA=1. Reports each step so a
failure names the step rather than the whole flow.
"""
import re
import time

from playwright.sync_api import sync_playwright

URL = "http://127.0.0.1:8765/"

with sync_playwright() as p:
    b = p.chromium.launch(headless=False)
    pg = b.new_page(viewport={"width": 1100, "height": 1000})
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)[:160]))

    pg.goto(URL, wait_until="load", timeout=45000)
    pg.fill("input[name=business_name]", "Bypass Test Co")
    pg.fill("input[name=email]", "bypass@observeco.test")
    pg.fill("input[name=category]", "F&B / salad and wraps")
    pg.fill("textarea[name=positioning_sentence]", "made-to-order salads for office workers")
    pg.fill("textarea[name=differentiator]", "cheaper and fresher than salad bars")
    pg.fill("input[name=competitors_named]", "SaladStop!, Supergreen")
    pg.fill("textarea[name=customer_description]", "office workers wanting a quick healthy lunch")

    print("STEP 1 — clicking submit ...")
    pg.click("button[data-submit]")
    pg.wait_for_timeout(9000)
    t = pg.inner_text("body")
    print("   url:", pg.url)
    print("   says 'Check your email':", "Check your email" in t)
    print("   says 'Nothing has been run':", "Nothing has been run" in t)
    print("   captcha error present:", "couldn't verify" in t.lower())

    m = re.search(r"/confirm\?token=([A-Za-z0-9_\-\.]+)", t)
    if not m:
        print("   !! no confirmation link found — stopping")
        print("   body head:", t[:600].replace("\n", " "))
        b.close()
        raise SystemExit(1)
    link = "http://127.0.0.1:8765" + m.group(0)
    print("   confirmation link found")

    print("\nSTEP 2 — visiting the confirmation link (this may run the model) ...")
    pg.goto(link, wait_until="load", timeout=300000)
    pg.wait_for_timeout(2000)
    t2 = pg.inner_text("body")
    print("   url:", pg.url)
    print("   confirmed banner   :", "Confirmed" in t2)
    print("   report present     :", bool(re.search(r"\d+/100", t2)))
    print("   refusal shown      :", "efused" in t2)
    print("   internal bug (bad) :", "INTERNAL BUG" in t2)
    band = re.search(r"(\d+/100\s*—\s*[A-Za-z, ]+)", t2)
    print("   band               :", band.group(1).strip() if band else "(none)")

    print("\nSTEP 3 — re-using the same link must NOT run again ...")
    pg.goto(link, wait_until="load", timeout=60000)
    pg.wait_for_timeout(1500)
    t3 = pg.inner_text("body")
    print("   says 'already':", "already" in t3.lower())

    print("\npage errors:", errs or "(none)")
    b.close()
