"""Render HTML visuals to PNG using Playwright."""
import sys
from playwright.sync_api import sync_playwright

htmls = [
    "x-banner-0.3pct.html",
    "x-visual-token-ratio.html",
    "x-visual-compare.html",
    "x-visual-component-cost.html",
]

viewport_map = {
    "x-banner-0.3pct.html": {"width": 1200, "height": 630},
    "x-visual-token-ratio.html": {"width": 800, "height": 600},
    "x-visual-compare.html": {"width": 800, "height": 500},
    "x-visual-component-cost.html": {"width": 900, "height": 700},
}

base = "/Users/seanfzc/projects/observeco/docs"

with sync_playwright() as p:
    browser = p.chromium.launch()
    for html in htmls:
        vp = viewport_map.get(html, {"width": 800, "height": 600})
        page = browser.new_page(viewport=vp)
        page.goto(f"file://{base}/{html}")
        page.wait_for_timeout(1500)  # wait for fonts/rendering
        png_path = f"{base}/{html.replace('.html', '.png')}"
        page.screenshot(path=png_path, full_page=False)
        print(f"Saved {png_path}")
        page.close()
    browser.close()
