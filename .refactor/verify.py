#!/usr/bin/env python3
"""Golden-master verify: re-hit endpoints, diff against golden snapshots.

Usage:
    .venv/bin/python3 .refactor/verify.py              # verify all
    .venv/bin/python3 .refactor/verify.py --chunk c07  # one chunk

Exit 0 if every checked endpoint PASSes, 1 otherwise.
PASS   = 200 + body identical after normalization
REVIEW = 200 but diff remains after masking volatile content (hunks printed)
FAIL   = non-200 or fetch error
"""
import argparse
import difflib
import html as html_mod
import json
import os
import re
import sys
import urllib.request
import urllib.error

BASE_DIR = "/Users/seanfzc/observeco"
GOLDEN = os.path.join(BASE_DIR, ".refactor", "golden")
SERVER = "http://127.0.0.1:8897"

sys.path.insert(0, os.path.join(BASE_DIR, "src"))
from observeco.dashboard.server import _dash_secret as TOKEN  # noqa: E402

# Volatile content masks: value differs run-to-run even with identical code.
MASKS = [
    (re.compile(r"\b1[67]\d{8}(?:\d{3})?\b"), "<TS>"),                 # epoch s/ms
    (re.compile(r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}(:\d{2})?(\.\d+)?(Z|[+-]\d{2}:?\d{2})?"), "<ISO>"),
    (re.compile(r"\b\d{1,2}:\d{2}(:\d{2})?\b"), "<TIME>"),
    (re.compile(r"\b\d+\s*(s|sec|m|min|h|d)\s+ago\b", re.I), "<AGO>"),
    (re.compile(r"\b\d+[smhd]\s*\d*[ms]?\s+ago\b", re.I), "<AGO>"),
    (re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b"), "<UUID>"),
    (re.compile(r"updated[^<]{0,40}", re.I), "updated<AGO>"),
]

def normalize(text):
    for rx, rep in MASKS:
        text = rx.sub(rep, text)
    # Semantically identical HTML must compare equal:
    text = html_mod.unescape(text)          # &#39; vs '  (autoescape artifacts)
    text = re.sub(r">\s+<", "><", text)     # inter-tag whitespace is browser-insignificant
    lines = []
    for ln in text.split("\n"):
        ln = re.sub(r"[ \t]+", " ", ln).rstrip()
        lines.append(ln)
    out = "\n".join(lines)
    out = re.sub(r"\n{3,}", "\n\n", out)
    return out.strip()

def fetch(url):
    req = urllib.request.Request(url, headers={"X-ObserveCo-Token": TOKEN})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except Exception as e:
        return 0, str(e).encode()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--chunk", help="only verify endpoints for this chunk id")
    ap.add_argument("--hunks", type=int, default=5, help="diff hunks to print on REVIEW")
    args = ap.parse_args()

    index = json.load(open(os.path.join(GOLDEN, "index.json")))
    entries = [e for e in index if not e.get("skipped") and not e.get("no_golden")]
    if args.chunk:
        entries = [e for e in entries if e["chunk"] == args.chunk]

    fails = reviews = passes = 0
    for e in entries:
        status, body = fetch(SERVER + e["url"])
        label = f"[{e['chunk']}] {e['url']}"
        if status != 200:
            print(f"FAIL   {label} -> HTTP {status}")
            fails += 1
            continue
        golden_path = os.path.join(GOLDEN, e["file"])
        old = normalize(open(golden_path, encoding="utf-8", errors="replace").read())
        new = normalize(body.decode("utf-8", errors="replace"))
        if old == new:
            print(f"PASS   {label}")
            passes += 1
            continue
        diff = list(difflib.unified_diff(old.split("\n"), new.split("\n"), lineterm="", n=2))
        hunks, cur = [], []
        for ln in diff:
            if ln.startswith("@@") and cur:
                hunks.append(cur); cur = []
            cur.append(ln)
        if cur: hunks.append(cur)
        print(f"REVIEW {label} ({len(hunks)} hunks)")
        for h in hunks[: args.hunks]:
            print("      " + "\n      ".join(h[:12]))
        reviews += 1

    print(f"\n{passes} PASS / {reviews} REVIEW / {fails} FAIL")
    sys.exit(1 if (fails or reviews) else 0)

if __name__ == "__main__":
    main()
