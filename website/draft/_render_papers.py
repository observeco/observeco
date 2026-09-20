#!/usr/bin/env python3
"""Render whitepapers/0X-*.md into draft site article pages (whitepaper-0N.html)
using pandoc + the consulting design-system shell. Static, no build step."""
import subprocess, glob, os, re

ROOT = "/Users/seanfzc/projects/observeco-main"
WP = os.path.join(ROOT, "whitepapers")
OUTDIR = os.path.join(ROOT, "website", "draft")

META = {
    "01": ("The Landscape", "The Singapore Business Landscape"),
    "02": ("The Demographics", "The Demographic Waves"),
    "03": ("The Industry Map", "The Industry Map"),
    "04": ("The Brand Map", "The Brand Map"),
    "05": ("The AI Map", "The AI Map"),
    "06": ("The Decision Line", "The Decision Line"),
}

NAV = """<header class="site-header">
  <div class="container nav-bar">
    <a class="nav-brand" href="index.html">ObserveCo<span class="dot">.</span></a>
    <button class="nav-toggle" id="navToggle" aria-expanded="false" aria-controls="navLinks">Menu</button>
    <nav class="nav-links" id="navLinks" aria-label="Primary">
      <a href="index.html">Home</a>
      <a href="differentiation-strategy.html">The Strategy</a>
      <a href="differentiation-watch.html">The Watch</a>
      <a href="method.html">The Method</a>
      <a href="case-studies-greenpackers.html">Client Work</a>
      <a href="whitepapers.html" aria-current="page">White Paper</a>
      <a class="nav-cta" href="#contact">Book a call</a>
    </nav>
  </div>
</header>"""

ARTICLE_CSS = """
.wp-article { padding: 40px 0 88px; }
.article-wrap { max-width: 860px; margin: 0 auto; padding: 0 24px; }
.back-link { font-family: var(--font-mono); font-size: 12px; letter-spacing: 0.08em;
  text-transform: uppercase; color: var(--green); text-decoration: none; margin-bottom: 20px; display: inline-block; }
.back-link:hover { color: var(--green-hover); }
.wp-graphic { margin: 32px 0 40px; border-radius: var(--radius-lg); overflow: hidden;
  border: 1px solid var(--border); }
.wp-graphic svg { display: block; width: 100%; height: auto; }
.wp-article article { background: var(--surface); border: 1px solid var(--border);
  border-radius: var(--radius-lg); padding: 48px 56px; }
.meta-series { font-family: var(--font-mono); font-size: 12px; font-weight: 500; letter-spacing: 0.14em;
  text-transform: uppercase; color: var(--green); margin-bottom: 12px; }
.wp-article article > h1:first-child {
  font-family: var(--font-display); font-size: clamp(30px, 4vw, 42px); font-weight: 600;
  line-height: 1.12; letter-spacing: -0.02em; color: var(--fg); margin: 0 0 12px; }
.wp-article article > h2 { font-family: var(--font-display); font-size: 24px; font-weight: 600;
  color: var(--fg); margin: 40px 0 14px; line-height: 1.2; letter-spacing: -0.01em; }
.wp-article article > h3 { font-family: var(--font-display); font-size: 19px; font-weight: 600;
  color: var(--fg); margin: 28px 0 10px; }
.wp-article article p { font-size: 17px; line-height: 1.75; color: var(--fg-2); margin: 0 0 18px; }
.wp-article article p strong { color: var(--fg); font-weight: 600; }
.wp-article article blockquote { border-left: 3px solid var(--green); background: var(--green-dim);
  padding: 16px 22px; border-radius: 0 var(--radius) var(--radius) 0; margin: 24px 0; }
.wp-article article blockquote p { margin: 0; color: var(--fg); }
.wp-article article hr { border: 0; border-top: 1px solid var(--border); margin: 40px 0; }
.wp-article article table { width: 100%; border-collapse: collapse; margin: 22px 0 28px;
  font-size: 14px; line-height: 1.5; }
.wp-article article th { font-family: var(--font-mono); font-size: 11px; letter-spacing: 0.1em;
  text-transform: uppercase; text-align: left; color: var(--green); font-weight: 500;
  border-bottom: 2px solid var(--border); padding: 10px 12px; }
.wp-article article td { border-bottom: 1px solid var(--border-subtle); padding: 10px 12px;
  color: var(--fg-2); vertical-align: top; }
.wp-article article td:first-child, .wp-article article th:first-child { padding-left: 0; }
.wp-article article ul, .wp-article article ol { margin: 0 0 20px; padding-left: 24px; }
.wp-article article li { font-size: 16.5px; line-height: 1.7; color: var(--fg-2); margin-bottom: 8px; }
.wp-article article code { font-family: var(--font-mono); font-size: 13px; background: var(--surface-2);
  padding: 1px 6px; border-radius: 4px; }
@media (max-width: 680px) {
  .wp-article article { padding: 28px 22px; }
  .wp-graphic { margin: 24px 0 28px; }
}
"""

def pandoc_html(num):
    src = sorted(glob.glob(os.path.join(WP, f"{num}-*.md")))[0]
    out = subprocess.run(
        ["pandoc", src, "--from=gfm-tex_math_dollars", "--to=html", "--wrap=none"],
        capture_output=True, text=True)
    if out.returncode != 0:
        raise RuntimeError(f"pandoc failed for {src}: {out.stderr}")
    return out.stdout

def build_page(num, nav_title, doc_title):
    body = pandoc_html(num)
    m = re.search(r"<h1[^>]*>(.*?)</h1>", body, re.S)
    h1 = m.group(1) if m else doc_title
    # drop the leading H1 from the body so we re-insert a styled one
    body = re.sub(r"<h1[^>]*>.*?</h1>", "", body, count=1, flags=re.S)
    # some papers use '#' for both the title and part/section headers (e.g. WP5);
    # demote any remaining H1 in the body to H2 so only the article title is an H1.
    body = re.sub(r"<h1([^>]*)>", r"<h2\1>", body)
    body = re.sub(r"</h1>", "</h2>", body)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{doc_title} — ObserveCo White Papers</title>
<meta name="description" content="ObserveCo Consulting — The Differentiation Playbook for Singapore Small Business. {doc_title}.">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="assets/draft.css">
<script src="assets/draft.js" defer></script>
<script src="assets/white-papers.js" defer></script>
<style>{ARTICLE_CSS}</style>
</head>
<body>
{NAV}
<main>
  <section class="wp-article">
    <div class="article-wrap">
      <a class="back-link" href="whitepapers.html">&larr; All white papers</a>
      <div class="wp-graphic" data-wp-graphic="{num}"></div>
      <article>
        <p class="meta-series">The Differentiation Playbook for Singapore Small Business</p>
        <h1>{h1}</h1>
        {body}
      </article>
    </div>
  </section>
</main>
</body>
</html>
"""

def main():
    for num, (nav_title, doc_title) in META.items():
        page = build_page(num, nav_title, doc_title)
        outpath = os.path.join(OUTDIR, f"whitepaper-{num}.html")
        with open(outpath, "w") as f:
            f.write(page)
        print(f"wrote {outpath} ({len(page)} bytes)")

if __name__ == "__main__":
    main()
