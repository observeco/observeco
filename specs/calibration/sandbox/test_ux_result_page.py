"""Verify the browser UX on the result page -- the gap the DB check could not cover.

The previous script crashed on inner_text("body") right after the click, because the result page
REPLACES THE DOCUMENT via document.write (see server.report_page: a sandboxed frame blocks native
form POST, so the form posts through fetch and document.write swaps the page). Reading "body" at
the wrong moment finds no body.

This waits for a real marker instead, and checks what a HUMAN would see:
  * the submit step shows "Check your email" and a confirmation link
  * the confirm step shows the report (score, band, per-dimension table)
  * re-using the link shows "already"
"""
import re

from playwright.sync_api import sync_playwright

URL = "http://127.0.0.1:8765/"


def text(pg):
    """innerText via evaluate -- robust to document.write, unlike locator('body')."""
    try:
        return pg.evaluate("() => (document.body ? document.body.innerText : '')") or ""
    except Exception as e:                                     # noqa: BLE001
        return ""

with sync_playwright() as p:
    b = p.chromium.launch(headless=False)
    pg = b.new_page(viewport={"width": 1100, "height": 1000})
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)[:140]))

    pg.goto(URL, wait_until="domcontentloaded", timeout=45000)
    pg.fill("input[name=business_name]", "UX Check Co")
    pg.fill("input[name=email]", "ux@observeco.test")
    pg.fill("input[name=category]", "F&B / salad and wraps")
    pg.fill("textarea[name=positioning_sentence]", "made-to-order salads for office workers")
    pg.fill("textarea[name=differentiator]", "cheaper and fresher than salad bars")
    pg.fill("input[name=competitors_named]", "SaladStop!, Supergreen")
    pg.fill("textarea[name=customer_description]", "office workers wanting a quick healthy lunch")

    print("STEP 1 — submit")
    pg.click("button[data-submit]")
    pg.wait_for_selector("text=Check your email", timeout=60000)
    t1 = text(pg)
    print("   sees 'Check your email' :", "Check your email" in t1)
    print("   sees 'Nothing has been run':", "Nothing has been run" in t1)
    print("   no score shown yet (correct):", not re.search(r"\d+/100", t1))

    # ⚠ READ THE href ATTRIBUTE, NOT THE RENDERED TEXT. The previous version regexed innerText,
    # which can insert a line break into a long URL -- the token came out mangled, the confirm
    # page said "couldn't confirm", and the row stayed `pending`. Reading the attribute is exact.
    href = pg.get_attribute("a[href^='/confirm']", "href")
    print("   href as rendered      :", (href[:38] + "...") if href else "(none)",
          "| len", len(href) if href else 0)
    if not href:
        print("   !! no confirm anchor. page head:", t1[:400].replace("\n", " "))
        b.close(); raise SystemExit(1)
    link = "http://127.0.0.1:8765" + href

    print("\nSTEP 2 — confirm (may take a minute; the model runs here)")
    pg.goto(link, wait_until="domcontentloaded", timeout=300000)
    try:
        pg.wait_for_selector("text=Confirmed", timeout=300000)
    except Exception:                                          # noqa: BLE001
        pass
    t2 = text(pg)
    score = re.search(r"(\d+/100\s*[—-]\s*[A-Za-z, ]+)", t2)
    print("   sees 'Confirmed'      :", "Confirmed" in t2)
    print("   report score+band     :", score.group(1).strip() if score else "(none)")
    print("   per-dimension table   :", "mental_advantage" in t2 or "mental advantage" in t2.lower())
    print("   internal bug (bad)    :", "INTERNAL BUG" in t2)
    print("   refusal (also valid)  :", "efused" in t2)

    print("\nSTEP 3 — re-use the link")
    pg.goto(link, wait_until="domcontentloaded", timeout=60000)
    t3 = text(pg)
    print("   sees 'already'        :", "already" in t3.lower())

    print("\npage errors:", errs or "(none)")
    b.close()
