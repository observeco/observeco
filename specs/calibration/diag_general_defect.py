"""Is the DR defect GENERAL? Examine the biggest remaining disputes in detail.

The DR fix worked because the dimension read the FORM instead of the BUSINESS. I already
found that 4 of 6 dimensions carry NO corroboration language at all. So the same defect
should show up as: my score is low, and a physical fact about the business contradicts it.

Test each large dispute against physical reality:
  Sephora Singapore   RS me 2  him 5
  Best Denki          DEF me 1 him 4
  Bonefirm            RS me 2  him 4
  Don Don Donki       RS me 2  him 4
  Polar Puffs         RS me 2  him 4
  ROA                 RS me 2  him 4
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
V = json.loads((HERE / "rubric-v1.3.2.json").read_text())
idx = json.loads((HERE / "inputs-v4" / "_index.json").read_text())

CASES = [("Sephora Singapore", "relative_strength"),
         ("Best Denki Singapore", "defensibility"),
         ("Bonefirm", "relative_strength"),
         ("Don Don Donki", "relative_strength"),
         ("Polar Puffs & Cakes", "relative_strength"),
         ("ROA", "relative_strength")]

for nm, dim in CASES:
    cid = next((c for c, e in idx["companies"].items() if e["name"] == nm), None)
    if not cid:
        print("!! %s not found" % nm)
        continue
    src = json.loads((HERE / "inputs-v4" / (cid + ".json")).read_text())
    run = json.loads((HERE / "runs-v132" / ("jev-%s.json" % cid)).read_text())
    disp = run.get("dimensions_display_1to5") or {}
    un = set(run.get("dimensions_unscored") or [])
    form = src.get("form", {})
    meta = src.get("_meta", {})

    print("=" * 92)
    print("%s  [%s]   %s" % (nm, idx["companies"][cid]["cat"], dim))
    print("=" * 92)
    print("  my %s = %s   (unscored: %s)"
          % (dim[:18], None if dim in un else disp.get(dim), dim in un))
    print()
    print("  --- WHAT THE FORM GAVE ME ---")
    for k in ("sells_what", "to_whom", "differentiator", "undercut_on",
              "your_price_point", "why_customers_leave"):
        v = " ".join(str(form.get(k) or "").split())
        if v:
            print("   %-20s %s" % (k, v[:150]))
    comps = src.get("competitors_named") or []
    print("   %-20s %s" % ("competitors_named", "; ".join(comps[:6])))
    print()
    print("  --- PHYSICAL EVIDENCE IN THE CORPUS ---")
    for k in ("LABEL", "LABEL_SOURCE", "sources", "note", "external_label"):
        v = meta.get(k)
        if v:
            s = json.dumps(v)[:300] if not isinstance(v, str) else v[:300]
            print("   %-20s %s" % (k, s))
    print()
    print("  --- MY LEVEL LADDER FOR THIS DIMENSION ---")
    q = V["questions"][dim]
    for i, lv in enumerate(q.get("levels") or [], 1):
        mark = "  <-- ME" if (disp.get(dim) == i and dim not in un) else ""
        print("   %d. %s%s" % (i, " ".join(str(lv).split())[:120], mark))
    print()
