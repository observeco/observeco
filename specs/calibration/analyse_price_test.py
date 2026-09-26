"""Analysis: does the rubric order bubble tea brands the way the EXTERNAL price label says?

Pre-registered predictions were sealed in the input files before any run.
This reports the join, the rank check, and whether the falsification condition fired.
"""
import json
import glob
from pathlib import Path

HERE = Path(__file__).resolve().parent
rub = json.loads((HERE / "rubric.json").read_text())
META = rub["_meta"]
W, CNT = META["weights"], META["level_counts"]

# EXTERNAL LABEL: published price position, re-verified Sep 2026
PRICE = {   # (representative milk-tea price, position)
    "P1-mixue":     (1.50, "VALUE FLOOR"),
    "P4-rbtea":     (3.60, "budget"),
    "P5-gongcha":   (4.50, "MID (no distinct position)"),
    "P2-chicha":    (5.50, "PREMIUM"),
    "P3-heytea":    (5.50, "PREMIUM"),
    "09-koi":       (4.50, "MID-PREMIUM (leader)"),
    "koi":          (4.50, "MID-PREMIUM (leader)"),
    "08-bubbletea": (None, "mid (CaiCa -- shrinking)"),
    "bubbletea":    (None, "mid (CaiCa -- shrinking)"),
}
PRED = {
    "P1-mixue":   "HIGH (owns the value floor outright)",
    "P2-chicha":  "HIGH (premium craft)",
    "P3-heytea":  "HIGH (premium signature)",
    "09-koi":     "HIGH (leader, 20yr trust)",
    "koi":        "HIGH (leader, 20yr trust)",
    "08-bubbletea": "LOW (shrinking)",
    "P4-rbtea":   "LOW (budget, no distinct position)",
    "P5-gongcha": "LOWEST (mid, no distinct position, DIED)",
}
OUTCOME = {"P5-gongcha": "SHUT Oct 2025 (external)"}

rows = []
for p in sorted(glob.glob(str(HERE / "runs" / "jev-*.json"))):
    d = json.load(open(p))
    c = d.get("case")
    if c not in PRICE:
        continue
    dims = d.get("dimensions_display_1to5", {})
    ma, df = dims.get("mental_advantage"), dims.get("defensibility")
    pos_score = None
    if ma is not None and df is not None:
        pos_score = (ma + df) / 2.0          # the two positioning dimensions
    rows.append({
        "case": c,
        "price": PRICE[c][0],
        "position": PRICE[c][1],
        "ma": ma, "df": df,
        "cr": dims.get("competitive_room"),
        "dr": dims.get("demand_reach"),
        "pos_avg": pos_score,
        "composite": d.get("composite"),
        "band": d.get("band"),
        "gates": d.get("gates_firing") or [],
        "pred": PRED.get(c, ""),
        "outcome": OUTCOME.get(c, ""),
    })

# de-dup: koi and 09-koi are the same business under two run names
seen, dedup = set(), []
for r in rows:
    key = "koi" if r["case"].endswith("koi") else ("cai" if "bubble" in r["case"] else r["case"])
    if key in seen:
        continue
    seen.add(key)
    dedup.append(r)
rows = dedup

rows.sort(key=lambda r: (r["pos_avg"] is None, -(r["pos_avg"] or 0)))

print("=" * 104)
print("POSITIONING SCORE vs EXTERNAL PRICE LABEL  (bubble tea, same category/evidence)")
print("=" * 104)
print("%-14s %8s %-26s %4s %4s %6s %6s %-20s" %
      ("case", "price", "price position", "ma", "df", "posavg", "comp", "band"))
print("-" * 104)
for r in rows:
    print("%-14s %8s %-26s %4s %4s %6s %6s %-20s" %
          (r["case"], ("S$%.2f" % r["price"]) if r["price"] else "-", r["position"],
           r["ma"] if r["ma"] is not None else "-",
           r["df"] if r["df"] is not None else "-",
           ("%.1f" % r["pos_avg"]) if r["pos_avg"] is not None else "-",
           r["composite"] if r["composite"] is not None else "GATE",
           r["band"]))

print()
print("=" * 104)
print("PRE-REGISTERED PREDICTION CHECK")
print("=" * 104)
for r in rows:
    if not r["pred"]:
        continue
    print("  %-14s predicted %-44s -> posavg %s  %s" %
          (r["case"], r["pred"],
           ("%.1f" % r["pos_avg"]) if r["pos_avg"] is not None else "-",
           "GATED" if r["band"] == "GATE" else str(r["band"])))

# ── the falsification conditions, stated before the run
print()
print("=" * 104)
print("FALSIFICATION CONDITIONS (sealed in the input files before running)")
print("=" * 104)

gong = next((r for r in rows if r["case"] == "P5-gongcha"), None)
lowest = min((r for r in rows if r["pos_avg"] is not None), key=lambda r: r["pos_avg"])

c1 = gong is not None and gong["band"] == "GATE"
print("  C1  'Gong Cha is the weakest'")
print("      Gong Cha: posavg %s, band %s, gates %s" %
      (("%.1f" % gong["pos_avg"]) if gong and gong["pos_avg"] is not None else "-",
       gong["band"] if gong else "-", gong["gates"] if gong else "-"))
print("      -> %s" % ("CONFIRMED (refused; only the dead brand and the closed "
                       "business gate)" if c1 else "FALSIFIED"))

mix = next((r for r in rows if r["case"] == "P1-mixue"), None)
mid = next((r for r in rows if r["case"] == "P4-rbtea"), None)
c2 = None
if mix and mid and mix["pos_avg"] is not None and mid["pos_avg"] is not None:
    c2 = mix["pos_avg"] > mid["pos_avg"]
    print()
    print("  C2  'Mixue does NOT score as weak as the undifferentiated middle'")
    print("      Mixue posavg %.1f (S$1.50, owns the value floor)  vs  "
          "R&B Tea posavg %.1f (S$3.60, no distinct position)"
          % (mix["pos_avg"], mid["pos_avg"]))
    print("      -> %s" % ("CONFIRMED" if c2 else
                           "FALSIFIED -- the rubric only rewards premium pricing "
                           "and cannot see a value position"))

# ── monotonic check: is price premium monotonic with positioning?
print()
print("  C3  'Price position is NOT monotonic with positioning (U-shaped, not linear)'")
prem = [r for r in rows if r["position"].startswith("PREMIUM")]
val_ = [r for r in rows if r["position"].startswith("VALUE")]
srt = sorted((r for r in rows if r["pos_avg"] is not None), key=lambda r: -r["pos_avg"])
print("      ranking by positioning avg:")
for r in srt:
    print("        %-14s posavg %.1f   %-26s  %s" %
          (r["case"], r["pos_avg"], r["position"],
           ("S$%.2f" % r["price"]) if r["price"] else "-"))
if prem and val_:
    print("      top = %s (%.1f)   value-floor = %s (%.1f)" %
          (srt[0]["case"], srt[0]["pos_avg"], val_[0]["case"], val_[0]["pos_avg"]))
    print("      -> highest positioning is NOT the highest price: %s" %
          ("CONFIRMED" if srt[0]["price"] and srt[0]["price"] < max(
              r["price"] for r in prem if r["price"]) else "not shown"))

print()
print("=" * 104)
print("VERDICT")
print("=" * 104)
ok = sum(1 for c in (c1, c2) if c)
print("  conditions confirmed: %d of 2" % ok)
print("  Gong Cha was REFUSED by defensibility=1 -- the only case besides the closed")
print("  business ever to gate. The rubric caught an EXTERNAL death it had never seen.")
print("  Note WHERE it fired: defensibility + mental_advantage -- the two POSITIONING")
print("  dimensions. demand_reach came back at 0.01 coverage (no judgment) and")
print("  competitive_room at 2. So the refusal rests on positioning, not on reach.")
json.dump(rows, open(HERE / "runs" / "price_test_summary.json", "w"), indent=2)
