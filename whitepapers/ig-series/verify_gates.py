#!/usr/bin/env python3
"""
Content/structure gates for the IG carousel series.

Run with the SYSTEM python (PIL is broken in the Hermes venv):
    env -u PYTHONPATH -u VIRTUAL_ENV /usr/bin/python3 verify_gates.py [post]

Exit 0 = every gate passed. Exit 1 = at least one failed.
"""
import glob
import re
import struct
import sys
from html.parser import HTMLParser
from pathlib import Path

from PIL import Image

HERE = Path(__file__).parent
ASSET_RE = re.compile(r'<img src="([^"]+)"')
CANVAS = (247, 246, 243)          # --canvas #f7f6f3
SLIDE_SIZE = (1080, 1350)
FORBIDDEN = ["#3b82f6", "#8b5cf6", "#6366f1", "#0f172a", "#1e293b", "#273548"]
FURNITURE = ['class="overline"', 'class="counter"', 'class="brand"', 'class="source"']
# Reader-facing leak guard. AMENDED 2026-09-19: book context is now INTENTIONAL
# (Sean: "use the front and back cover page to start with... give the context that
# the content of the post relates to the book"). The book may be named by TITLE.
# What stays banned: internal document terms, and the bare series index in the
# footer wordmark (an unexplained "Book 1" is noise to a reader).
LEAK = ["whitepaper", "White Paper", "book 1", "book 2", "Book 1", "Book 2"]
FOOTER_TAG = "/ Singapore"
# The retired pulse/heartbeat icon. `assets/brand/LOGO_STYLE_GUIDE.md` bans it:
# "Do not reintroduce the old pulse/heartbeat icon — retired with the consulting
# pivot." The brand is a text-only wordmark ("ObserveCo." serif + teal period).
# Signature of the banned mark: the polyline/pulse path or the <circle class="mark">.
RETIRED_MARK = ['class="mark"', "polyline points=", '<circle cx="64" cy="64"']
VOID = {"br", "img", "meta", "link", "input", "hr"}


def png_size(path):
    return struct.unpack(">II", open(path, "rb").read(24)[16:24])


def well_formed(path):
    """True if every tag is opened and closed in order."""
    class V(HTMLParser):
        def __init__(self):
            super().__init__()
            self.stack, self.errs = [], []

        def handle_starttag(self, tag, attrs):
            if tag not in VOID:
                self.stack.append(tag)

        def handle_endtag(self, tag):
            if self.stack and self.stack[-1] == tag:
                self.stack.pop()
            elif tag in self.stack:
                self.errs.append(tag)

    v = V()
    v.feed(open(path).read())
    return not (v.errs or v.stack)


def bars_exact(path):
    """(n_bars, max_width_error_pp, is_descending) for a bars slide, else None."""
    rows = re.findall(
        r'bar-name">(.*?)</div>.*?width:([\d.]+)%.*?bar-val">(.*?)</div>',
        open(path).read(), re.S)
    if not rows:
        return None

    def num(v):
        m = re.match(r"S?\$?([\d.]+)([KM])?", v.strip().replace("&amp;", "&"))
        if m is None:
            raise ValueError(f"unparseable bar value: {v!r}")
        return float(m.group(1)) * (1000 if m.group(2) == "M" else 1)

    vals = [(n, num(v), float(w)) for n, w, v in rows]   # pattern order: name, width, value
    mx = max(v[1] for v in vals)
    err = max(abs(round(v[1] / mx * 100, 1) - v[2]) for v in vals)
    desc = all(vals[i][1] >= vals[i + 1][1] for i in range(len(vals) - 1))
    return len(vals), err, desc


def slide_id(path):
    """post02-slide03-what-is-observeco.html -> 'post02-03'. Disambiguates the
    per-slide gate labels when a run spans several posts."""
    head, _, tail = path.partition("-slide")
    return f"{head}-{tail.split('-')[0]}" if tail else path


def cols_semantics(path):
    """Check column ranking matches the labels.

    The teal ramp encodes a recommendation (rank1 = strongest). A "Not this"
    column must never be the strongest one, and a "This" column must be. Returns
    a list of complaints; empty means OK. Returns None if the slide has no cols.
    """
    src = open(path).read()
    cols = re.findall(
        r'class="col (rank\d)"><div class="col-label">(.*?)</div>', src, re.S)
    if not cols:
        return None
    bad = []
    for rank, label in cols:
        text = re.sub(r"<[^>]+>", "", label).strip()
        if re.match(r"(not|no|don'?t)\b", text, re.I) and rank == "rank1":
            bad.append(f'negative column "{text}" is ranked strongest ({rank})')
        if text.lower() in ("this", "yes") and rank != "rank1":
            bad.append(f'positive column "{text}" is not ranked strongest ({rank})')
    return bad


def counter_seq(paths):
    """Check the `NN / TT` slide counters are sequential and agree on the total.

    A slide counter is hand-written per slide, so it silently drifts whenever a
    slide is inserted or removed: post01 shipped `02 / 06` alongside `04 / 07`,
    `05 / 07` ... and every pixel gate still passed. Slides are numbered by
    filename order (render order), which is the reader's order.

    Returns a list of complaints; empty means OK. Chromeless slides (bare covers)
    carry no counter and are skipped.
    """
    bad = []
    tot = None
    for i, p in enumerate(paths, 1):
        src = open(p).read()
        m = re.search(r'class="counter">\s*(\d+)\s*/\s*(\d+)\s*<', src)
        if not m:
            continue                      # bare cover — no counter by design
        num, total = int(m.group(1)), int(m.group(2))
        if tot is None:
            tot = total
        elif total != tot:
            bad.append(f"{slide_id(p)}: total {total} != {tot}")
        if num != i:
            bad.append(f"{slide_id(p)}: numbered {num} but is slide {i}")
    return bad


def main(post="post"):
    png = sorted(f for f in glob.glob(f"{post}*.png") if f.startswith("post"))
    htm = sorted(glob.glob(f"{post}*.html"))
    if not htm:
        sys.exit(f"  FAIL: no slides matched {post}*")

    fails = 0

    def gate(ok: bool, label: str, detail: object = "") -> None:
        nonlocal fails
        fails += not ok
        print(f"  {'OK  ' if ok else 'FAIL'} {label:<26} {detail}")

    bad = [p for p in png if png_size(p) != SLIDE_SIZE]
    gate(not bad, "dims 1080x1350", f"({len(png)} slides) {bad}")

    blank = []
    for p in png:
        im = Image.open(p).convert("RGB")
        px = im.load()
        assert px is not None, f"cannot read pixels from {p}"
        uniq = {px[x, y] for x in range(0, im.width, 16) for y in range(0, im.height, 16)}
        if len(uniq) < 50 or px[5, 5] != CANVAS:
            blank.append((p, len(uniq), px[5, 5]))
    gate(not blank, "real render + #f7f6f3", blank)

    leaks = {f: [c for c in FORBIDDEN if c in open(f).read().lower()] for f in htm}
    leaks = {k: v for k, v in leaks.items() if v}
    gate(not leaks, "no forbidden tokens", leaks)

    # Reader-facing leak: internal document terms and the bare footer series index
    # are banned. The book TITLE is allowed (and required) on cover slides.
    bookleak = {f: [t for t in LEAK if t in open(f).read()] for f in htm}
    bookleak = {k: v for k, v in bookleak.items() if v}
    gate(not bookleak, "no document-term leak", bookleak)

    # Brand-asset gate: the retired pulse/heartbeat icon must not come back.
    # It survived unnoticed on every slide footer until the logo became the hero.
    markleak = {f: [t for t in RETIRED_MARK if t in open(f).read()] for f in htm}
    markleak = {k: v for k, v in markleak.items() if v}
    gate(not markleak, "no retired logo mark", markleak)

    # The bare cover slide intentionally has no header/footer chrome; the cover
    # artwork is the hook. Every OTHER slide must carry the full furniture set.
    chromed = [f for f in htm if 'class="slide bare"' not in open(f).read()]
    missing = [f for f in chromed if not all(r in open(f).read() for r in FURNITURE)]
    gate(not missing, "full slide furniture", f"({len(chromed)}/{len(htm)} chromed) {missing}")

    # Every chromed slide carries the same series tag. Drift here is invisible in a
    # per-slide review but shows as an inconsistent footer across the carousel.
    tag_drift = [f for f in chromed if FOOTER_TAG not in open(f).read()]
    gate(not tag_drift, "footer series tag", tag_drift or FOOTER_TAG)

    # Every referenced local asset must exist — a missing <img src> renders a broken
    # icon while every pixel gate still passes.
    dangling = [(f, src) for f in htm
                for src in ASSET_RE.findall(open(f).read())
                if not src.startswith("http") and not (HERE / src).exists()]
    gate(not dangling, "cover assets resolve", dangling)

    broken = [f for f in htm if not well_formed(f)]
    gate(not broken, "HTML well-formed", broken)

    # The <=10 IG limit is PER CAROUSEL, not per run. When called as "post" the
    # glob spans every post, so count slides grouped by their postNN prefix.
    per_post = {}
    for f in htm:
        per_post.setdefault(f.split("-slide")[0], []).append(f)
    over = {k: len(v) for k, v in per_post.items() if len(v) > 10}
    gate(not over, "slide count <= 10 per post",
         f"{ {k: len(v) for k, v in sorted(per_post.items())} }" + (f" OVER={over}" if over else ""))

    # Caption docs restate the slide count ("**Slides:** 9 · ..."). That literal goes
    # stale the moment a slide is inserted, and a doc that contradicts the artifact is
    # worse than no doc. Assert doc == generated reality.
    drift = []
    for pp, files in sorted(per_post.items()):
        doc = HERE / f"00-captions-{pp}.md"
        if not doc.exists():
            drift.append((pp, "caption doc missing"))
            continue
        m = re.search(r"\*\*Slides:\*\*\s*(\d+)", doc.read_text())
        if m and int(m.group(1)) != len(files):
            drift.append((pp, f"doc says {m.group(1)}, actual {len(files)}"))
    gate(not drift, "caption docs match slides", drift or "counts agree")

    checked = 0
    for f in sorted(htm):
        res = cols_semantics(f)
        if res is None:
            continue
        gate(not res, f"cols semantics {slide_id(f)}", res or "ranking matches labels")
        checked += 1
    if not checked:
        print("  --   no comparison columns in this post")

    # Slide counters are hand-written per slide, so they drift silently when a slide
    # is inserted/removed. Check per post — the numbering is per carousel.
    for pp, files in sorted(per_post.items()):
        res = counter_seq(sorted(files))
        gate(not res, f"counter sequence {pp}", res or f"{len(files)} slides sequential")

    checked = 0
    for f in sorted(htm):
        res = bars_exact(f)
        if res is None:
            continue
        n, err, desc = res
        gate(err < 0.5 and desc, f"bars {slide_id(f)}: {n}",
             f"max err {err:.2f}pp, descending={desc}")
        checked += 1
    if not checked:
        print("  --   no bar charts in this post")

    return fails


if __name__ == "__main__":
    sys.exit(1 if main(*sys.argv[1:]) else 0)
