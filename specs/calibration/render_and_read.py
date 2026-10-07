"""Render a report from an EXISTING run artifact (no model call) and READ IT AS A READER.

Last commit changed four reader-facing strings and was never rendered. This renders real output and
asserts the fidelity claims directly against what the submitter would actually see.

Uses generate_report.render(run, rubric, submission) -- the same entry the sandbox calls.
"""
import json
import os
import re
import sys

BASE = "/Users/seanfzc/projects/observeco-main/specs/calibration"
sys.path.insert(0, BASE)
import generate_report as gr                                          # noqa: E402

run = json.load(open(os.path.join(BASE, "runs/jev-BK01-breadtalk.json")))
sub = None
for cand in ("runs/jev-BK01-breadtalk.submission.json", "inputs-v4/BK01-breadtalk.json"):
    p = os.path.join(BASE, cand)
    if os.path.exists(p):
        sub = json.load(open(p))
        print("submission:", cand)
        break

from pathlib import Path
a, b = gr.render(run, Path(BASE) / "rubric.json", sub)
report = b
print("rendered: version_a %d chars, version_b %d chars" % (len(a), len(b)))
print("=" * 78)

for sec in ["WHAT EACH SCORE MEANS", "WHAT THE BANDS MEAN", "THE ONE THING THAT DECIDES IT",
            "WHERE TO GET THE SCORE UP"]:
    print("  %-32s %s" % (sec, "✅" if sec in report else "✗ MISSING"))

i = report.find("WHAT EACH SCORE MEANS")
j = report.find("WHERE TO GET THE SCORE UP")
print("\n=== WHAT EACH SCORE MEANS (as the reader sees it) ===")
print(report[i:j if j > i else i + 1500])

# ⚠⚠ NORMALISE WHITESPACE BEFORE CHECKING. The previous version searched the rendered text for
# "unmet demand" and reported FAIL -- but the report DOES say "Unmet demand scores high". The
# renderer WRAPS lines, so the phrase arrives as "Unmet\n      demand". A check that requires a
# literal space fails on correct output. Fifth instance this session of an assertion being wrong
# rather than the code -- so the probe normalises first and asserts on the flat text.
flat = " ".join(report.split())
print("\n=== FIDELITY CHECKS (the point of this run) ===")
checks = [
    ("competitive_room: old 'margin is left for you' GONE",
     not re.search(r"margin is left for you", flat, re.I)),
    ("competitive_room: speaks of market structure / power over price",
     bool(re.search(r"space the market leaves|power over price", flat, re.I))),
    ("defensibility: old 'copy what makes you different' GONE",
     not re.search(r"copy what makes you different", flat, re.I)),
    ("defensibility: names what a rival would ASSEMBLE",
     bool(re.search(r"assemble", flat, re.I))),
    ("market_headroom: old 'growing, already met' GONE",
     not re.search(r"category is growing, already met", flat, re.I)),
    ("market_headroom: speaks of unmet demand",
     bool(re.search(r"unmet demand", flat, re.I))),
    ("demand_reach: mentions sust/ained revenue",
     bool(re.search(r"sustain", flat, re.I))),
]
ok_all = True
for label, ok in checks:
    ok_all &= ok
    print("  %-58s %s" % (label, "✅" if ok else "✗ FAIL"))
print("\nALL PASS:", ok_all)
