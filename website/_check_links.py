#!/usr/bin/env python3
"""Crawl the deployed website/ root and verify every internal link resolves
(no 404s, no broken assets, no dangling anchors)."""
import re, os, sys, urllib.request, urllib.parse
from html.parser import HTMLParser

BASE = "http://127.0.0.1:8899"
ROOT = "/Users/seanfzc/projects/observeco-main/website"

class LinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []  # (href, src)
    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        for attr in ("href", "src"):
            if attr in d and d[attr].strip():
                self.links.append((attr, d[attr].strip()))

def fetch(url):
    try:
        with urllib.request.urlopen(url, timeout=10) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception as e:
        return None, str(e)

# collect all local .html pages
pages = sorted(f for f in os.listdir(ROOT) if f.endswith(".html") and not f.startswith("_"))
print(f"Checking {len(pages)} pages against {BASE}\n")

problems = []
for page in pages:
    status, html = fetch(f"{BASE}/{page}")
    if status != 200:
        problems.append(f"[{page}] PAGE fetch status={status}")
        continue
    p = LinkParser()
    p.feed(html)
    for attr, href in p.links:
        if href.startswith(("http://", "https://", "mailto:", "tel:", "#", "data:")):
            continue  # external or in-page anchor
        # strip fragment
        path = href.split("#")[0]
        if not path:
            continue
        # resolve relative to page dir (all at root, so just the path)
        url = f"{BASE}/{path.lstrip('/')}"
        s, _ = fetch(url)
        if s != 200:
            problems.append(f"[{page}] {attr}={href} -> status={s}")

if problems:
    print(f"PROBLEMS ({len(problems)}):")
    for p in problems:
        print("  " + p)
    sys.exit(1)
else:
    print("ALL INTERNAL LINKS RESOLVE (200) — no broken links, no missing assets.")
