"""D4 — implement the refusal of the synthetic `home-not-permitted` cases.

SEAN'S DECISION: "D4, refuse them."

WHY THIS IS A CORPUS-LEVEL REFUSAL AND NOT A RUBRIC GATE. The 0.9.0 changelog records that
SCORE GATES WERE REMOVED because they did the wrong job: they turned "this business has no
moat" into "we cannot assess this business", which are different statements. Re-adding a gate
here would repeat that error.

The `home-not-permitted` cases are a different situation entirely: they are not businesses at
all. They are SYNTHETIC REPRESENTATIVES of a statutory rule (`HDB Home-Based Business
Scheme`), authored to probe what the rubric does at a legal boundary. No real operator was
measured. Scoring a rule as though it were a business is fabrication, and refusing is the
correct output.

So the refusal is recorded in the CORPUS, not in the rubric: these cases are marked refused
with a stated reason, and are excluded from alignment denominators. The rubric is untouched.

THE PRODUCT-LEVEL REQUIREMENT this implies is recorded separately in the spec: a REAL
business that cannot legally serve its stated market should be refused with a stated reason,
not scored low. That is a genuine product behaviour and a follow-up build item -- it is NOT
implemented here, and this file does not pretend otherwise.
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
INDEX = HERE / "inputs-v4" / "_index.json"
idx = json.loads(INDEX.read_text())

TARGETS = [cid for cid, e in idx["companies"].items() if e.get("cat") == "home-not-permitted"]

REFUSED = {
    "_note": ("Corpus-level refusals. These are NOT scored and NOT counted in any alignment "
              "denominator. Distinct from the assessability gate: that says 'we cannot analyse "
              "this business', this says 'this is not a business, it is a rule representative'. "
              "A REAL not-permitted business is a separate, unimplemented product case."),
    "reason_code": "SYNTHETIC_RULE_REPRESENTATIVE",
    "reason": ("Authored as a representative of the HDB Home-Based Business Scheme boundary, "
               "not measured from a real operator. Scoring a statutory rule as a business "
               "would be fabrication; the rubric exists to prevent exactly that."),
    "decided_by": "Sean, 2026-09-27 (D4)",
    "cases": sorted(TARGETS),
    "names": [idx["companies"][c]["name"] for c in sorted(TARGETS)],
}

out = HERE / "inputs-v4" / "_refused.json"
out.write_text(json.dumps(REFUSED, indent=2) + "\n")

print("wrote inputs-v4/_refused.json")
print()
print("refused %d cases (excluded from scoring and from alignment denominators):" % len(TARGETS))
for c in sorted(TARGETS):
    print("   %-10s %s" % (c, idx["companies"][c]["name"]))
print()
print("rubric untouched -- no score gate added, per the 0.9.0 finding that score gates did")
print("the wrong job. This is a corpus decision.")
