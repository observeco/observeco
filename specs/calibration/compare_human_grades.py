"""FIRST HUMAN LABELS: compare Sean's grades against the rubric.

His grades were entered in ~/Downloads/grading-sheet.numbers (56 rows) from the sheet as
it stood BEFORE the D1-D3 realignment, so this comparison is against the OLD definitions.

Method:
  1. Validate the composite formula by recomputing MY composite from my own display
     values and checking it reproduces the recorded composite. If it does, the same
     formula can be applied to HIS values -- apples to apples.
  2. Per dimension: mean signed difference (bias), mean absolute difference, correlation.
  3. Composite: his implied vs mine; rank agreement; band agreement.
  4. Test the hypothesis that the MA disagreement is SYSTEMATIC and definitional.
"""
import csv
import json
import statistics
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
DIMS = ["mental_advantage", "defensibility", "competitive_room",
        "market_headroom", "demand_reach"]
ABBR = {"mental_advantage": "MA", "defensibility": "DEF", "competitive_room": "CR",
        "market_headroom": "MH", "demand_reach": "DR"}
W = json.loads((HERE / "rubric.json").read_text())["_meta"]["weights"]

grades = list(csv.DictReader(open(HERE / "sean-grades-raw.csv")))
print("rows in his sheet: %d" % len(grades))

# which run file backs each row? use run_id
def num(x):
    x = (x or "").strip()
    if x.lower() in ("n/a", "na", "n.a.", "n.a", "-", ""):
        return None
    try:
        return float(x)
    except Exception:
        return None

pairs = []
for g in grades:
    rid = (g.get("run_id") or "").strip()
    rp = HERE / "runs" / ("jev-%s.json" % rid)
    if not rp.exists():
        continue
    run = json.loads(rp.read_text())
    d = run.get("dimensions_display_1to5") or {}
    uns = set(run.get("dimensions_unscored") or [])
    mine = {k: (None if k in uns else d.get(k)) for k in DIMS}
    his = {k: num(g.get("YOUR_" + ABBR[k])) for k in DIMS}
    if not any(v is not None for v in his.values()):
        continue
    pairs.append(dict(cid=g["case_id"], name=g["company"], set_=g["set"],
                      tier=g["tier"], mine=mine, his=his,
                      my_comp=run.get("composite"), my_band=run.get("band"),
                      his_band=(g.get("YOUR_BAND") or "").strip(),
                      notes=(g.get("YOUR_NOTES") or "").strip(),
                      rec_mine=run.get("dimensions_display_1to5") or {},
                      unc=uns))

print("rows joined to a run AND with at least one grade: %d" % len(pairs))
print()


def comp_from(dims, uns=None):
    """composite = 19.1667 x weighted mean of display values."""
    num_ = den = 0.0
    for k in DIMS:
        v = dims.get(k)
        if v is None:
            continue
        num_ += v * W[k]
        den += W[k]
    return round(19.1667 * (num_ / den), 0) if den else None


print("=" * 82)
print("STEP 1 — validate the composite formula against MY recorded composites")
print("=" * 82)
errs = []
for p in pairs:
    rec = p["my_comp"]
    calc = comp_from(p["mine"])
    if rec is not None and calc is not None:
        errs.append(abs(rec - calc))
print("  cases checked: %d   mean |error|: %.2f   max: %.2f"
      % (len(errs), statistics.mean(errs), max(errs)))
ok_formula = statistics.mean(errs) < 2.0
print("  formula %s" % ("VALIDATED" if ok_formula else "NOT validated -- treat composite "
                                                  "comparison as indicative only"))

print()
print("=" * 82)
print("STEP 2 — PER-DIMENSION AGREEMENT (his vs mine, on the OLD definitions)")
print("=" * 82)
print()
print("  %-6s %4s  %8s  %8s  %8s  %8s" %
      ("dim", "n", "mean d", "mean|d|", "exact", ">=2 apart"))
for k in DIMS:
    ds = [(p["his"][k] - p["mine"][k]) for p in pairs
          if p["his"][k] is not None and p["mine"][k] is not None]
    if not ds:
        print("  %-6s    0   (never both scored)" % ABBR[k])
        continue
    exact = sum(1 for d in ds if d == 0)
    big = sum(1 for d in ds if abs(d) >= 2)
    print("  %-6s %4d  %+8.2f  %8.2f  %7d%%  %7d%%" % (
        ABBR[k], len(ds), statistics.mean(ds),
        statistics.mean(abs(d) for d in ds),
        100 * exact / len(ds), 100 * big / len(ds)))
print()
print("  mean d  = HIS score minus MINE (positive = he grades HIGHER)")
print("  >=2 apart = a real dispute, not rounding")

print()
print("=" * 82)
print("STEP 3 — MA, THE CONTESTED DIMENSION, CASE BY CASE")
print("=" * 82)
print()
print("  The hypothesis: he grades MA as ABSOLUTE awareness; I grade it SIZE-RELATIVE.")
print("  If so, he should score MA HIGHER specifically for LARGE, FAMOUS businesses.")
print()
large = [p for p in pairs
         if p["his"]["mental_advantage"] is not None
         and p["mine"]["mental_advantage"] is not None]
large.sort(key=lambda p: p["his"]["mental_advantage"] - p["mine"]["mental_advantage"],
           reverse=True)
print("  %-34s %-18s %6s %6s %6s" % ("company", "set", "his", "mine", "diff"))
for p in large[:14]:
    print("  %-34s %-18s %6.0f %6.0f %+6.0f" % (
        p["name"][:33], p["set_"][:17], p["his"]["mental_advantage"],
        p["mine"]["mental_advantage"],
        p["his"]["mental_advantage"] - p["mine"]["mental_advantage"]))
ds = [p["his"]["mental_advantage"] - p["mine"]["mental_advantage"] for p in large]
print()
print("  MA mean difference: %+.2f   (n=%d)" % (statistics.mean(ds), len(ds)))
print("  cases where he scores MA higher: %d   lower: %d   same: %d" % (
    sum(1 for d in ds if d > 0), sum(1 for d in ds if d < 0), sum(1 for d in ds if d == 0)))

print()
print("=" * 82)
print("STEP 4 — COMPOSITE AND ORDERING")
print("=" * 82)
print()
cp = []
for p in pairs:
    mine = comp_from(p["mine"])
    his = comp_from(p["his"])
    if mine is not None and his is not None:
        cp.append((p, mine, his))
print("  cases with both composites computable: %d" % len(cp))
if cp:
    diffs = [h - m for _, m, h in cp]
    print("  composite mean difference (his - mine): %+.1f   mean|diff|: %.1f"
          % (statistics.mean(diffs), statistics.mean(abs(d) for d in diffs)))
    # rank agreement within set
    print()
    print("  my composite vs his implied composite, biggest gaps:")
    for p, m, h in sorted(cp, key=lambda x: -abs(x[2] - x[1]))[:12]:
        print("    %-32s %-16s mine=%3.0f his=%3.0f  diff=%+4.0f" % (
            p["name"][:31], p["set_"][:15], m, h, h - m))

print()
print("=" * 82)
print("STEP 5 — HIS FREE-TEXT NOTES (where the real signal is)")
print("=" * 82)
print()
noted = [p for p in pairs if p["notes"]]
print("  rows with notes: %d of %d" % (len(noted), len(pairs)))
for p in noted[:20]:
    print("  * %-30s %s" % (p["name"][:29], p["notes"][:96]))
