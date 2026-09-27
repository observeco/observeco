"""Is Sean's DR critique a DR problem, or a GENERAL flaw in how the instrument reads input?

His charge: "You have blind gaps. You have to corroborate your answer against physical
evidence. Best Denki, 24/7 Fitness, Zoff are able to generate revenue which means it is
able to reach out to successfully attract customers. That automatically challenges your
'no evidence they would pay this price'."

That is a charge about EVIDENCE HANDLING, not about the demand_reach definition. If true,
it should show up wherever a dimension's instruction says "no evidence that..." -- so test
every dimension for the same pattern: low score, yet the corpus carries physical proof.

Also check the deepest form: does the instrument EVER ask for corroboration against
physical evidence?
"""
import glob
import json
import re
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
V12 = json.loads((HERE / "rubric-v1.2.0.json").read_text())
idx = json.loads((HERE / "inputs-v4" / "_index.json").read_text())

DIMS = ["relative_strength", "mental_advantage", "defensibility",
        "competitive_room", "market_headroom", "demand_reach"]

# ---- 1. does any instruction ask for corroboration against evidence? ---------
print("=" * 84)
print("1. DOES THE INSTRUMENT EVER ASK FOR CORROBORATION?")
print("=" * 84)
print()
pat = {
    "corroborate/corroboration": r"corroborat",
    "verify/verified": r"\bverif",
    "physical evidence": r"physical evidence",
    "published evidence": r"published evidence",
    "actually trades/trading": r"\btrading\b|\bactually trades\b",
    "revenue": r"\brevenue\b",
    "does it exist / observable": r"\bobservable\b|\bactually\b",
    "check against the facts": r"check.*(fact|evidence)",
}
for d in DIMS:
    txt = " ".join([str(V12["questions"][d].get("instructions", ""))] +
                   list(V12["questions"][d].get("levels") or []))
    hits = [k for k, rx in pat.items() if re.search(rx, txt, re.I)]
    print("  %-18s %s" % (d, hits if hits else "NONE — no corroboration language"))
print()

# ---- 2. the same pattern in every dimension ---------------------------------
print("=" * 84)
print("2. LOW SCORE vs PHYSICAL EVIDENCE PRESENT — every dimension")
print("=" * 84)
print()
EVID = re.compile(
    r"(\d[\d,]*)\s*(outlets?|stores?|clubs?|restaurants?|branches|shops?)"
    r"|published|store finder|islandwide|revenue|S\$[\d.]|largest|market leader"
    r"|since \d{4}|chain|network|founded", re.I)

mine = {}
for p in (HERE / "runs-v12").glob("jev-*.json"):
    r = json.loads(p.read_text())
    d = r.get("dimensions_display_1to5") or {}
    u = set(r.get("dimensions_unscored") or [])
    mine[r["case"]] = {k: (None if k in u else d.get(k)) for k in d}

for d in DIMS:
    low_with_ev = 0
    low_total = 0
    for cid, e in idx["companies"].items():
        me = (mine.get(cid) or {}).get(d)
        if me is None or me > 2:
            continue
        low_total += 1
        src = json.loads((HERE / "inputs-v4" / (cid + ".json")).read_text())
        meta = src.get("_meta", {})
        form = src.get("form", {})
        ev = " ".join(str(meta.get(k) or "") for k in ("LABEL_SOURCE", "sources"))
        ev += " " + str(form.get("your_price_point") or "") + " " + \
              str(form.get("differentiator") or "")
        if EVID.search(ev):
            low_with_ev += 1
    if low_total:
        print("  %-18s scored <=2 in %3d cases; %3d of those carry physical evidence (%d%%)"
              % (d, low_total, low_with_ev, 100 * low_with_ev / low_total))
    else:
        print("  %-18s never scored <=2" % d)
print()

# ---- 3. the specific question: is DR double-counting RS? --------------------
print("=" * 84)
print("3. THE STRUCTURAL PROBLEM: DR may be measuring the CONSEQUENCE of strong position")
print("=" * 84)
print()
print("  Sean's logic: trading and generating revenue PROVES you reach customers.")
print("  If a business has strong relative_strength, it HAS customers -- so its demand")
print("  reach is proven, and DR collapses into RS. Check the correlation.")
print()
import statistics

rows = []
for cid in idx["companies"]:
    m = mine.get(cid) or {}
    if m.get("demand_reach") is not None and m.get("relative_strength") is not None:
        rows.append((m["relative_strength"], m["demand_reach"]))
xs = [a for a, _ in rows]
ys = [b for _, b in rows]
mx, my = statistics.mean(xs), statistics.mean(ys)
cov = sum((a - mx) * (b - my) for a, b in rows)
dx = sum((a - mx) ** 2 for a in xs) ** 0.5
dy = sum((b - my) ** 2 for b in ys) ** 0.5
r = cov / (dx * dy) if dx and dy else 0
print("  correlation(my RS, my DR) = %.2f  (n=%d)" % (r, len(rows)))
print()
print("  Cross-tab: does a high RS ever come with a low DR?")
print()
print("  %-14s %s" % ("RS \\ DR", "  ".join("DR%d" % i for i in range(1, 6))))
for rs in range(1, 6):
    cells = []
    for dr in range(1, 6):
        n = sum(1 for a, b in rows if int(a) == rs and int(b) == dr)
        cells.append("%4d" % n if n else "   .")
    print("  RS%-12d %s" % (rs, "  ".join(cells)))
print()
contra = [(a, b) for a, b in rows if a >= 4 and b <= 2]
print("  cases with RS >= 4 but DR <= 2 (high standing, low reach): %d" % len(contra))
print("  -> if this count is near zero, DR is redundant with RS")
print("  -> if it is large, the two are genuinely distinct")
