"""Render the PM-ladder visuals + banner to PNG using Playwright."""
from playwright.sync_api import sync_playwright

base = "/Users/seanfzc/projects/observeco-main/content-writing/20260908"

# (html, viewport_w, viewport_h, clip_box)
targets = [
    ("fig-pm-01-income-ladder.html", 1200, 440, None),
    ("fig-pm-02-trust-not-effort.html", 1200, 440, None),
    ("banner-pm-ladder.html", 1200, 480, {"x": 0, "y": 0, "width": 1200, "height": 480}),
]

with sync_playwright() as p:
    browser = p.chromium.launch()
    for html, w, h, clip in targets:
        page = browser.new_page(viewport={"width": w, "height": h})
        page.goto(f"file://{base}/{html}")
        page.wait_for_timeout(1600)  # wait for fonts
        png = f"{base}/{html.replace('.html', '.png')}"
        page.screenshot(path=png, clip=clip, full_page=False)
        print("Saved", png)
        page.close()
    browser.close()
