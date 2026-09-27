"""Extract Sean's REGRADE (v1.0.0, six dimensions) from ~/Downloads/regrade-sheet.numbers.

He said his numbers are in, and pointed at grading-sheet.csv -- but that file has 0 filled
rows. The live file is regrade-sheet.numbers (modified today), which is the sheet generated
with the new six-dimension columns. Extract it and report what he filled.
"""
import csv
import json
from pathlib import Path

from numbers_parser import Document

SRC = Path.home() / "Downloads" / "regrade-sheet.numbers"
doc = Document(str(SRC))
out_csv = Path("/Users/seanfzc/projects/observeco-main/specs/calibration/"
               "sean-regrade-raw.csv")

for sh in doc.sheets:
    for t in sh.tables:
        rows = [list(r) for r in t.rows(values_only=True)]
        print("table %s: %d rows x %d cols" % (t.name, len(rows), len(rows[0])))
        hdr = ["" if v is None else str(v).strip() for v in rows[0]]
        print()
        print("header:")
        for i, h in enumerate(hdr):
            print("   [%2d] %s" % (i, h))
        yi = {h: i for i, h in enumerate(hdr) if h.startswith("YOUR")}
        print()
        print("YOUR columns: %s" % {k: v for k, v in yi.items()})

        body = rows[1:]
        filled = 0
        for r in body:
            vals = [str(r[j]).strip() if j < len(r) and r[j] is not None else ""
                    for j in yi.values()]
            if any(v and v.lower() not in ("none", "nan") for v in vals):
                filled += 1
        print()
        print("data rows: %d" % len(body))
        print("rows with ANY YOUR value: %d" % filled)

        with out_csv.open("w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(hdr)
            for r in body:
                w.writerow(["" if v is None else v for v in r])
        print()
        print("-> %s" % out_csv)
