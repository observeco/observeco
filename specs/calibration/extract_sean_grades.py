"""Extract Sean's human grades from ~/Downloads/grading-sheet.numbers.

His grades are the project's first human labels. Two jobs:
  1. Pull them into CSV so they can be joined against the corpus.
  2. Report which companies he graded, and how many of them are DUPLICATES -- so the
     rebuild can keep one canonical entry per business without losing his work.
"""
import json
import re
from collections import defaultdict
from pathlib import Path

from numbers_parser import Document

SRC = Path.home() / "Downloads" / "grading-sheet.numbers"
doc = Document(str(SRC))

print("sheets:", [s.name for s in doc.sheets])
for sh in doc.sheets:
    print()
    print("=" * 80)
    print("SHEET: %s   tables: %s" % (sh.name, [t.name for t in sh.tables]))
    for t in sh.tables:
        print()
        print("--- table %s: %d rows x %d cols ---" % (t.name, t.num_rows, t.num_cols))
        rows = []
        for i, row in enumerate(t.rows(values_only=True)):
            rows.append(["" if v is None else str(v).strip() for v in row])
            if i < 3:
                print("   hdr%d: %s" % (i, [c[:26] for c in rows[-1]][:14]))
        # find the header row (the one containing case_id / company)
        hdr_i = None
        for i, r in enumerate(rows):
            joined = " ".join(r).lower()
            if "case" in joined and "compan" in joined:
                hdr_i = i
                break
        if hdr_i is None:
            print("   (no recognizable header)")
            continue
        hdr = rows[hdr_i]
        print("   header row %d: %s" % (hdr_i, [c[:22] for c in hdr]))
        yi = {c: j for j, c in enumerate(hdr) if c.upper().startswith("YOUR")}
        print("   YOUR columns: %s" % {k: v for k, v in yi.items()})
        # count filled
        data = rows[hdr_i + 1:]
        filled = []
        for r in data:
            if not any(c.strip() for c in r):
                continue
            vals = {k: (r[j] if j < len(r) else "") for k, j in yi.items()}
            if any(v.strip() for v in vals.values()):
                filled.append((r, vals))
        print("   data rows: %d   rows with ANY 'YOUR' value: %d" % (len(data), len(filled)))
        if filled:
            print()
            print("   === GRADED ROWS (first 25) ===")
            ci = hdr.index("case_id") if "case_id" in hdr else 0
            ni = hdr.index("company") if "company" in hdr else 1
            for r, vals in filled[:25]:
                print("     %-24s %-30s %s" % (
                    r[ci][:23], r[ni][:29],
                    " ".join("%s=%s" % (k.replace("YOUR_", ""), v)
                             for k, v in vals.items() if v.strip())))
            if len(filled) > 25:
                print("     ... +%d more" % (len(filled) - 25))
            # dump full to CSV
            out = Path("/Users/seanfzc/projects/observeco-main/specs/calibration/"
                       "sean-grades-raw.csv")
            import csv
            with out.open("w", newline="") as fh:
                w = csv.writer(fh)
                w.writerow(hdr)
                for r in data:
                    if any(c.strip() for c in r):
                        w.writerow(r)
            print()
            print("   -> dumped to %s" % out)
