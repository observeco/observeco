#!/usr/bin/env python3
"""Build a print-ready A5 PDF from a book markdown file using pandoc + weasyprint."""
import subprocess, sys, os

BOOKS = {
    "book1": {
        "md": "/Users/seanfzc/projects/observeco-main/whitepapers/book1-map-manuscript.md",
        "title": "Where the Money Is",
        "subtitle": "How Singapore's domestic market really works, and what no one tells you",
        "out": "/tmp/book1-print.pdf",
    },
    "book2": {
        "md": "/Users/seanfzc/projects/observeco-main/whitepapers/book2-from-small-to-big-manuscript.md",
        "title": "How a Small Business Gets Chosen",
        "subtitle": "Lessons from Established Singapore Brands",
        "out": "/tmp/book2-print.pdf",
    },
}

CSS = "/Users/seanfzc/projects/observeco-main/whitepapers/print/book-print.css"
PRINTVENV = "/tmp/printvenv/bin/python"

def build(book):
    cfg = BOOKS[book]
    # 1. pandoc md -> html (fragment, no standalone wrapper)
    html = subprocess.run(
        ["pandoc", cfg["md"], "-f", "markdown", "-t", "html5", "--standalone",
         "--metadata", f"title={cfg['title']}"],
        capture_output=True, text=True)
    if html.returncode != 0:
        print("pandoc error:", html.stderr); return False
    body = html.stdout

    # Fix relative image paths -> absolute (HTML is written to /tmp, so relative paths break)
    VIS_ABS = "/Users/seanfzc/projects/observeco-main/whitepapers/visuals/"
    body = body.replace('src="visuals/', f'src="{VIS_ABS}')

    # 2. Wrap in print-ready HTML with title page + CSS
    wrapped = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{cfg['title']}</title>
<link rel="stylesheet" href="{CSS}">
</head>
<body>
<div class="titlepage">
  <h1>{cfg['title']}</h1>
  <div class="subtitle">{cfg['subtitle']}</div>
  <div class="author">Sean Foo, founder of ObserveCo</div>
</div>
{body}
</body>
</html>"""

    html_path = f"/tmp/{book}-print.html"
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(wrapped)

    # 3. weasyprint html -> pdf
    r = subprocess.run(
        [PRINTVENV, "-m", "weasyprint", html_path, cfg["out"]],
        capture_output=True, text=True, env={**os.environ, "PYTHONPATH": ""})
    if r.returncode != 0:
        print("weasyprint error:", r.stderr[-800:]); return False
    print(f"Built {cfg['out']}")
    return True

if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "book1"
    ok = build(which)
    sys.exit(0 if ok else 1)
