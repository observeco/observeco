"""What external evidence of RELATIVE market position does the corpus already hold?

If relative_position is to be a new dimension, its label must be externally verifiable.
Published outlet counts, share and awards are the strongest labels available -- much
stronger than the price label. This checks what is already recorded, and tests whether
an outlet/share anchor reproduces known market orderings.
"""
import glob
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent

PAT = re.compile(r"(\d[\d,]*)\s*(outlets?|stores?|clubs?|restaurants?|branches|"
                 r"supermarkets?|shops?|stalls?)|market leader|largest|no\.\s*1|"
                 r"number one|share of|leading", re.I)

print("=" * 80)
print("EXTERNAL MARKET-POSITION EVIDENCE ALREADY IN THE CORPUS")
print("=" * 80)
print()
n_with = 0
rows = []
for dirn in ("inputs", "inputs-v2", "inputs-v3"):
    for p in sorted(glob.glob(str(HERE / dirn / "*.json"))):
        if p.endswith("_index.json"):
            continue
        try:
            s = json.loads(Path(p).read_text())
        except Exception:
            continue
        m = s.get("_meta", {})
        src = " ".join(str(m.get(k) or "") for k in ("LABEL_SOURCE", "purpose"))
        f = s.get("form", {})
        src += " " + str(f.get("competitors_named") or s.get("competitors_named") or "")
        hits = PAT.findall(src)
        if hits:
            n_with += 1
            rows.append((m.get("case") or "?", m.get("business") or "", src[:150]))

print("cases whose label source already states an outlet count / market rank: %d" % n_with)
print()
for c, b, s in rows[:22]:
    print("  %-22s %-30s %s" % (c, b[:29], " ".join(s.split())[:100]))

print()
print("=" * 80)
print("TEST — does an outlet-count anchor reproduce KNOWN market orderings?")
print("=" * 80)
print()
print("Ground truth gathered in this session (published facts):")
truth = {
    "fast-food": [("McDonald's Singapore", 150, "market leader, 70M customers/yr"),
                  ("Jollibee Singapore", 26, "confirmed EDB/company")],
    "supermarket": [("NTUC FairPrice", 200, "largest chain (approx)"),
                    ("Sheng Siong", 75, "SGX-listed, ~75 stores")],
}
for cat, items in truth.items():
    print("  %s:" % cat)
    for nm, n, note in items:
        print("     %-26s %4d outlets   (%s)" % (nm, n, note))
print()
print("CURRENT RUBRIC ORDER in those categories:")
for cat, ids in (("fast-food", ["FF01", "FF02", "FF03", "FF05", "FF06", "FF04"]),):
    for cid in ids:
        cand = glob.glob(str(HERE / "runs" / ("jev-%s*.json" % cid)))
        if not cand:
            continue
        r = json.loads(Path(cand[0]).read_text())
        d = r.get("dimensions_display_1to5") or {}
        print("     %-6s composite=%-4s  MA=%s DEF=%s CR=%s DR=%s" % (
            cid, r.get("composite"), d.get("mental_advantage"),
            d.get("defensibility"), d.get("competitive_room"), d.get("demand_reach")))
print()
print("=> McDonald's holds 5.8x Jollibee's footprint and the market-leader position,")
print("   yet NO dimension in the rubric records that. MA divides size OUT; CR is")
print("   constant within the category; MH is dropped. The construct Sean names as")
print("   missing has no representation anywhere in the instrument.")
