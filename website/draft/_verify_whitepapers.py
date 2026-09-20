#!/usr/bin/env python3
"""Verify the on-disk whitepaper-0N.html pages tally with the current
book1-map-manuscript.md by re-rendering into a temp dir and diffing."""
import os, sys, tempfile, filecmp, shutil
sys.path.insert(0, "/Users/seanfzc/projects/observeco-main/website/draft")
import _render_manuscript as R

tmp = tempfile.mkdtemp(prefix="wp_verify_")
try:
    # monkeypatch OUTDIR to temp
    R.OUTDIR = tmp
    R.main()
    print("re-rendered into", tmp)
    print()
    mismatches = []
    for num, _ in R.DOC_TITLES:
        on_disk = os.path.join(R.ROOT, "website", "draft", f"whitepaper-{num}.html")
        fresh = os.path.join(tmp, f"whitepaper-{num}.html")
        same = filecmp.cmp(on_disk, fresh, shallow=False)
        status = "MATCH" if same else "DIFF"
        print(f"whitepaper-{num}.html: {status}")
        if not same:
            mismatches.append(num)
    print()
    if not mismatches:
        print("RESULT: ALL 6 pages tally with the manuscript (byte-identical to a fresh render).")
    else:
        print(f"RESULT: {len(mismatches)} page(s) differ from a fresh render: {mismatches}")
        print("Diff the temp files against on-disk to see what changed.")
finally:
    shutil.rmtree(tmp, ignore_errors=True)
