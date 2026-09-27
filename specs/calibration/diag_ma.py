"""Diagnose the mental_advantage offset (+0.46, disputes 11.7%, the largest remaining).

Worst MA cases, all large retailers, all in my direction:
   Harvey Norman   me 2  him 5 (+3)
   Best Denki      me 2  him 4 (+2)
   Courts          me 3  him 5 (+2)
   Don Don Donki   me 3  him 5 (+2)

Is it the same signature as RS and DR -- scoring the submission instead of the business?
Print the form, the evidence, and MY ladder so the mismatch is visible rather than guessed.
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
V = json.loads((HERE / "rubric-v1.4.1.json").read_text())
idx = json.loads((HERE / "inputs-v4" / "_index.json").read_text())

for nm in ["Harvey Norman Singapore", "Best Denki Singapore", "Courts Singapore",
           "Don Don Donki", "McDonald's Singapore", "Cold Storage"]:
    cid = next((c for c, e in idx["companies"].items() if e["name"] == nm), None)
    if not cid:
        continue
    src = json.loads((HERE / "inputs-v4" / (cid + ".json")).read_text())
    run = json.loads((HERE / "runs-v141" / ("jev-%s.json" % cid)).read_text())
    disp = run.get("dimensions_display_1to5") or {}
    un = set(run.get("dimensions_unscored") or [])
    form = src.get("form", {})
    meta = src.get("_meta", {})

    print("=" * 90)
    print("%s  [%s]    my MA = %s"
          % (nm, idx["companies"][cid]["cat"],
             None if "mental_advantage" in un else disp.get("mental_advantage")))
    print("=" * 90)
    for k in ("sells_what", "to_whom", "differentiator", "undercut_on",
              "your_price_point"):
        v = " ".join(str(form.get(k) or "").split())
        if v:
            print("   %-16s %s" % (k, v[:160]))
    print("   %-16s %s" % ("competitors", "; ".join((src.get("competitors_named") or [])[:6])))
    for k in ("LABEL_SOURCE", "sources"):
        v = meta.get(k)
        if v:
            s = json.dumps(v)[:260] if not isinstance(v, str) else v[:260]
            print("   %-16s %s" % (k, s))
    print()
    print("   MY LADDER (mark = my pick):")
    for i, lv in enumerate(V["questions"]["mental_advantage"].get("levels") or [], 1):
        mark = "  <-- ME" if disp.get("mental_advantage") == i else ""
        print("     %d. %s%s" % (i, " ".join(str(lv).split())[:135], mark))
    print()
