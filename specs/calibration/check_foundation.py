"""Assert the foundation document defines its tier vocabulary exactly once.

A document whose central vocabulary is defined twice will contradict itself. This
captured a real defect: v1 defined eight tiers twice, with tiers 3 and 4 swapped.

Runs on FOUNDATION-competitive-landscape.md. Exits non-zero on any disagreement
between the tier tables.

Usage: python3 check_foundation.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

DOC = Path(__file__).resolve().parent / "FOUNDATION-competitive-landscape.md"
CANONICAL = {
    "0": "The Default",
    "1": "The Cheap Substitute",
    "2": "The Direct Set",
    "3": "The Category Incumbent",
    "4": "The Adjacent Crossover",
    "5": "The Professional Route",
    "6": "The Indirect",
    "7": "The Emerging",
}


def tier_tables(text: str) -> list[dict[str, str]]:
    """Every markdown table that IS a tier table.

    A tier table is identified by its HEADER naming a tier column — not merely by
    having numbers in the first column. Without that test this catches the inputs
    table (§4), whose rows are numbered 1-6 and are not tiers at all.
    """
    out = []
    # capture (header line, body rows)
    for header, body in re.findall(
        r"^(\|.*\|)\n\|[-| ]+\|\n((?:\|.*\|\n)+)", text, re.M
    ):
        cols = [c.strip() for c in header.strip("|").split("|")]
        if not any(c.lower().strip("* ") in ("#", "tier") for c in cols):
            continue
        if not any("tier" in c.lower() for c in cols):
            continue

        rows: dict[str, str] = {}
        for line in body.strip().split("\n"):
            cells = [c.strip() for c in line.strip("|").split("|")]
            num = label = None
            for i, c in enumerate(cells):
                m = re.match(r"^\**(\d)\**\s*[·.]?\s*(.*)$", c)
                if m:
                    num = m.group(1)
                    label = re.sub(r"[*]", "", m.group(2)).strip()
                    if not label and i + 1 < len(cells):
                        label = re.sub(r"[*]", "", cells[i + 1]).strip()
                    break
            if num and label:
                # strip a leading tier bullet if the cell was "**3 · Name**"
                label = label.lstrip("·.- ").strip()
                rows[num] = label.split(" — ")[0].split(" - ")[0].strip()
        if len(rows) >= 5:
            out.append(rows)
    return out


def main() -> None:
    text = DOC.read_text()
    tables = tier_tables(text)
    print(f"tier tables found: {len(tables)}")
    for i, t in enumerate(tables):
        print(f"  table {i}: {len(t)} tiers")

    if not tables:
        sys.exit("no tier table found — the doc lost its vocabulary")

    ok = True
    for i, t in enumerate(tables):
        for num, label in t.items():
            want = CANONICAL.get(num)
            if want and label.lower() != want.lower():
                print(f"  MISMATCH table {i} tier {num}: {label!r} != canonical {want!r}")
                ok = False

    # every canonical tier must appear somewhere
    covered = set().union(*tables)
    missing = [n for n in CANONICAL if n not in covered]
    if missing:
        print(f"  MISSING canonical tiers: {missing}")
        ok = False

    print()
    print("single-definition check:", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
