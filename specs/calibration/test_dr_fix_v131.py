"""Did v1.3.1 close the demand_reach defect Sean identified?

Three things must hold, and the third is a REGRESSION GUARD:
  1. The four trading businesses he named move to >=3.
  2. DR agreement with his grades improves (slope toward 1).
  3. The home-massage case he AGREED with does NOT move off 1.
     (He said: "Your home massage service number is correct, I am wrong.")
     A fix that lifts every low score is not a fix -- it is a scale shift.
"""
import csv
import json
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
idx = json.loads((HERE / "inputs-v4" / "_index.json").read_text())
rows = list(csv.DictReader(open(HERE / "sean-regrade-raw.csv")))
by = {r["company"]: r for r in rows}


def load(d):
    out = {}
    for p in (HERE / d).glob("jev-*.json"):
        r = json.loads(p.read_text())
        disp = r.get("dimensions_display_1to5") or {}
        un = set(r.get("dimensions_unscored") or [])
        out[r["case"]] = {k: (None if k in un else disp.get(k)) for k in disp}
    return out


def num(x):
    x = ("" if x is None else str(x)).strip()
    if x.lower() in ("n/a", "na", "", "-", "none", "nan"):
        return None
    try:
        return float(x)
    except Exception:
        return None


old = load("runs-v12")
new = load("runs-v131")

print("=" * 84)
print("1. THE CASES SEAN NAMED")
print("=" * 84)
print()
print("  %-32s %-12s %6s %6s %6s" % ("company", "category", "v1.2", "v1.3", "his"))
NAMED = ["Best Denki Singapore", "24/7 Fitness", "Zoff Singapore", "BreadTalk",
         "Harvey Norman Singapore", "Shake Shack Singapore",
         "A home massage service", "A closed bubble tea outlet"]
for nm in NAMED:
    cid = next((c for c, e in idx["companies"].items() if e["name"] == nm), None)
    if not cid:
        continue
    o = (old.get(cid) or {}).get("demand_reach")
    n = (new.get(cid) or {}).get("demand_reach")
    h = num((by.get(nm) or {}).get("YOUR_DR"))
    flag = ""
    if nm == "A home massage service":
        flag = "  <- MUST stay 1" if n == 1 else "  <- REGRESSION"
    elif nm in ("Best Denki Singapore", "24/7 Fitness", "Zoff Singapore", "BreadTalk"):
        flag = "  <- fixed" if (n or 0) >= 3 else "  <- STILL BROKEN"
    print("  %-32s %-12s %6s %6s %6s%s"
          % (nm[:31], idx["companies"][cid]["cat"][:11], o, n, h, flag))

print()
print("=" * 84)
print("2. DR AGREEMENT WITH HIS GRADES — v1.2.0 vs v1.3.1")
print("=" * 84)
print()
for label, run in (("v1.2.0", old), ("v1.3.1", new)):
    pairs = []
    for cid, e in idx["companies"].items():
        m = (run.get(cid) or {}).get("demand_reach")
        h = num((by.get(e["name"]) or {}).get("YOUR_DR"))
        if m is not None and h is not None:
            pairs.append((m, h))
    xs = [a for a, _ in pairs]
    ys = [b for _, b in pairs]
    n = len(pairs)
    mx, my = sum(xs) / n, sum(ys) / n
    cov = sum((a - mx) * (b - my) for a, b in pairs)
    dx = sum((a - mx) ** 2 for a in xs) ** 0.5
    dy = sum((b - my) ** 2 for b in ys) ** 0.5
    r = cov / (dx * dy) if dx and dy else 0
    slope = cov / (dx ** 2) if dx else 0
    exact = sum(1 for a, b in pairs if a == b)
    ge2 = sum(1 for a, b in pairs if b - a >= 2)
    print("  %-8s n=%3d  my mean %.2f  slope %.2f  r %.2f  exact %2d%%  his>=2 above %2d%%"
          % (label, n, mx, slope, r, 100 * exact / n, 100 * ge2 / n))

print()
print("=" * 84)
print("3. DID THE FLOOR BIND? — remaining DR 1s and 2s under v1.3.1")
print("=" * 84)
print()
mi = Counter(int(v) for v in ((new.get(c) or {}).get("demand_reach")
                              for c in idx["companies"]) if v)
print("  v1.3.1 distribution: %s" % dict(sorted(mi.items())))
mi_old = Counter(int(v) for v in ((old.get(c) or {}).get("demand_reach")
                                  for c in idx["companies"]) if v)
print("  v1.2.0 distribution: %s" % dict(sorted(mi_old.items())))
print()
print("  The remaining 1s and 2s should ALL be non-trading / not-legal cases:")
print()
for cid, e in sorted(idx["companies"].items(),
                     key=lambda kv: (new.get(kv[0]) or {}).get("demand_reach") or 9):
    n = (new.get(cid) or {}).get("demand_reach")
    if n is None or n > 2:
        continue
    src = json.loads((HERE / "inputs-v4" / (cid + ".json")).read_text())
    pr = " ".join(str(src.get("form", {}).get("your_price_point") or "").split())[:52]
    h = num((by.get(e["name"]) or {}).get("YOUR_DR"))
    print("    DR%d  %-32s %-16s his=%s" % (n, e["name"][:31], e["cat"][:15], h))
    print("          price: %s" % (pr or "-"))

print()
print("=" * 84)
print("4. BLAST RADIUS — did anything ELSE move?")
print("=" * 84)
print()
moved = []
for cid in idx["companies"]:
    o = (old.get(cid) or {}).get("demand_reach")
    n = (new.get(cid) or {}).get("demand_reach")
    if o != n:
        moved.append((idx["companies"][cid]["name"], o, n))
print("  demand_reach cells changed: %d of %d" % (len(moved), len(idx["companies"])))
for nm, o, n in sorted(moved, key=lambda x: x[0])[:20]:
    print("    %-34s %s -> %s" % (nm[:33], o, n))
if len(moved) > 20:
    print("    ... +%d more" % (len(moved) - 20))
print()
other = 0
for cid in idx["companies"]:
    for d in ("relative_strength", "mental_advantage", "defensibility",
              "competitive_room", "market_headroom"):
        if (old.get(cid) or {}).get(d) != (new.get(cid) or {}).get(d):
            other += 1
print("  cells changed in the OTHER five dimensions: %d  (must be 0)" % other)
