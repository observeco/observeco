"""Renumber a markdown document's H2 sections sequentially from 1.

Needed because inserting a section silently collided with the next one and broke
every "§N" cross-reference. Does a two-pass rewrite to avoid collisions:
  1. map old number -> new number
  2. rewrite headings, then rewrite §N references that pointed at renumbered ones

Usage: python3 renumber_sections.py <file> [--check]
"""
from __future__ import annotations

import re
import sys
from pathlib import Path


def main() -> None:
    path = Path(sys.argv[1])
    check_only = "--check" in sys.argv
    text = path.read_text()

    heads = list(re.finditer(r"^## (\d+[a-z]?)\.", text, re.M))
    old = [m.group(1) for m in heads]
    new = [str(i) for i in range(1, len(heads) + 1)]

    if old == new:
        print(f"section numbers already sequential: {old}")
        return

    print(f"renumbering: {old}")
    print(f"        ->   {new}")

    if check_only:
        sys.exit(1)

    # pass 1: headings, right to left so offsets stay valid
    for m, n in sorted(zip(heads, new), key=lambda p: -p[0].start()):
        text = text[:m.start()] + f"## {n}." + text[m.end():]

    # pass 2: §N cross-references, using the old->new map for the FIRST section
    # that held each old number (duplicates are the bug being fixed, so map to the
    # earliest occurrence, which is the one a reader would have intended)
    remap: dict[str, str] = {}
    for o, n in zip(old, new):
        remap.setdefault(o, n)

    def fix_ref(m: re.Match[str]) -> str:
        num = m.group(1)
        return "§" + (remap.get(num) or num)

    text = re.sub(r"§(\d+[a-z]?)", fix_ref, text)

    path.write_text(text)
    print("done. verify with: python3 check_foundation.py")


if __name__ == "__main__":
    main()
