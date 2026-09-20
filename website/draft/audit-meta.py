#!/usr/bin/env python3
"""Audit meta title/description/og/h1 across live observeco site pages."""
import os, re, json

root = "/Users/seanfzc/projects/observeco-main/website"
skip_prefixes = ("draft/", "_old-root-backup-20260831/", "assets/")
html_files = []
for dirpath, dirnames, filenames in os.walk(root):
    rel = os.path.relpath(dirpath, root)
    if rel.startswith(skip_prefixes):
        continue
    for f in sorted(filenames):
        if f.endswith(".html") and f not in ("index-v2.html", "google16c15f4ba5bc0ff9.html"):
            html_files.append(os.path.join(rel, f))

title_re = re.compile(r"<title>(.*?)</title>", re.S)
def meta_content(html, name_or_prop, value):
    # match content="..." on double quotes only so apostrophes inside don't truncate
    m = re.search(r'<meta\s+%s=["\']%s["\']\s+content="([^"]*)"' % (name_or_prop, value), html, re.S)
    return m.group(1) if m else None

desc_re = re.compile(r'<meta\s+name=["\']description["\']\s+content="([^"]*)"', re.S)
ogtitle_re = re.compile(r'<meta\s+property=["\']og:title["\']\s+content="([^"]*)"', re.S)
ogdesc_re = re.compile(r'<meta\s+property=["\']og:description["\']\s+content="([^"]*)"', re.S)
h1_re = re.compile(r"<h1[^>]*>(.*?)</h1>", re.S)

report = []
for f in html_files:
    path = os.path.join(root, f)
    with open(path, encoding="utf-8") as fh:
        content = fh.read()
    title_m = title_re.search(content)
    desc_m = desc_re.search(content)
    og_t = ogtitle_re.search(content)
    og_d = ogdesc_re.search(content)
    h1s = h1_re.findall(content)
    def clean(s):
        return re.sub(r"\s+", " ", s).strip() if s else ""
    title = clean(title_m.group(1)) if title_m else None
    desc = clean(desc_m.group(1)) if desc_m else None
    ogt = clean(og_t.group(1)) if og_t else None
    ogd = clean(og_d.group(1)) if og_d else None
    issues = []
    if title is None:
        issues.append("NO TITLE")
    elif not (30 <= len(title) <= 60):
        issues.append(f"TITLE {len(title)} chars")
    if desc is None:
        issues.append("NO DESC")
    elif len(desc) > 160:
        issues.append(f"DESC {len(desc)} chars")
    if ogt is not None and len(ogt) > 60:
        issues.append(f"OGTITLE {len(ogt)} chars")
    if ogd is not None and len(ogd) > 160:
        issues.append(f"OGDESC {len(ogd)} chars")
    if len(h1s) != 1:
        issues.append(f"H1 count={len(h1s)}")
    report.append({"file": f, "title_len": len(title) if title else 0,
                   "desc_len": len(desc) if desc else 0,
                   "title": title, "desc": desc, "issues": issues})

print(json.dumps(report, indent=1, ensure_ascii=False))
