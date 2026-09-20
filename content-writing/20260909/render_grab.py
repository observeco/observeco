"""Render the Grab car marketplace visuals + banner to PNG using Playwright."""
from playwright.sync_api import sync_playwright

base = "/Users/seanfzc/projects/observeco-main/content-writing/20260909"

targets = [
    ("fig-grab-01-word.html", 1200, 440, None),
    ("fig-grab-02-gaps.html", 1200, 440, None),
    ("fig-grab-03-track-record.html", 1200, 440, None),
    ("banner-grab-car.html", 1200, 480, {"x": 0, "y": 0, "width": 1200, "height": 480}),
]

with sync_playwright() as p:
    browser = p.chromium.launch()
    for html, w, h, clip in targets:
        page = browser.new_page(viewport={"width": w, "height": h})
        page.goto(f"file://{base}/{html}")
        page.wait_for_timeout(1600)
        png = f"{base}/{html.replace('.html', '.png')}"
        page.screenshot(path=png, clip=clip, full_page=False)
        print("Saved", png)
        page.close()
    browser.close()
