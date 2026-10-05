"""TEST THE COMPLETE RE-ANCHORING: all five ladders, live, against Sean's 120 grades.

Injects every rewritten ladder in memory (rubric file untouched), runs the real model over all 120
corpus cases, and compares per-dimension agreement against THE FRESH ORIGINAL RUNS on disk -- so the
before/after is apples-to-apples, same corpus, same model.

Fails loud on a broken join. Reports the top-level award counts and the per-level pull, because the
defect being fixed is COMPRESSION (pull up at low levels, down at high ones).
"""
import concurrent.futures as cf
import copy, csv, glob, json, os, sys, statistics as st
from collections import Counter, defaultdict

BASE = "/Users/seanfzc/projects/observeco-main/specs/calibration"
sys.path.insert(0, BASE)
import run_jev

DRAFT = json.load(open("/tmp/five_ladders.json"))
rub = json.load(open(f"{BASE}/rubric.json"))
rub2 = copy.deepcopy(rub)
for dim, spec in DRAFT.items():
    q = rub2["questions"][dim]
    q["levels"] = list(spec["levels"])
    q["instructions"] = q["instructions"] + "\n\n" + spec["added"]

human = {}
for r in csv.DictReader(open(f"{BASE}/sean-regrade-raw.csv")):
    cid = (r.get("case_id") or "").strip().lower()
    if cid:
        human[cid] = r


def num(x):
    try:
        return float(x)
    except Exception:
        return None


# ORIGINAL fresh runs (before)
orig = {}
for p in glob.glob(f"{BASE}/runs-par/jev-*.json"):
    d = json.load(open(p))
    c = (d.get("case") or "").lower()
    if c:
        orig[c] = d.get("dimensions_display_1to5") or {}

CASES = sorted(p for p in glob.glob(f"{BASE}/inputs-v4/*.json")
               if not os.path.basename(p).startswith("_"))
print("corpus: %d cases" % len(CASES))

DIMS = [("position_strength", "YOUR_RS", 5), ("mental_advantage", "YOUR_MA", 5),
        ("defensibility", "YOUR_DEF", 6), ("competitive_room", "YOUR_CR", 5),
        ("demand_reach", "YOUR_DR", 5)]


def one(path):
    payload = json.load(open(path))
    case = os.path.basename(path)[:-5].lower()   # corpus filenames are mixed-case (BK01)
    try:
        res = run_jev.call_jev(run_jev.build_state(payload),
                               run_jev.build_questions(rub2), rub["_meta"]["model"])
        if res is None:
            return case, None
        out = {}
        for dim, _, _ in DIMS:
            a = (res.get("answers") or {}).get(dim) or {}
            s = a.get("score")
            out[dim] = (int(round(s)) + 1) if isinstance(s, (int, float)) else None
        return case, out
    except Exception as e:
        return case, "ERR:%s:%s" % (type(e).__name__, e)


new = {}
with cf.ThreadPoolExecutor(max_workers=6) as ex:
    for case, got in ex.map(one, CASES):
        new[case] = got
        print(".", end="", flush=True)
print()

errs = [c for c, g in new.items() if not isinstance(g, dict)]
if errs:
    print("\n⚠ %d cases errored: %s" % (len(errs), errs[:5]))

# FAIL LOUD on a bad join -- a silent 0-row join is what hid the case-key mismatch
_joined = sum(1 for c in new if c in human)
print("\nJOIN: %d of %d new results matched a human grade (0 would mean the key is wrong)"
      % (_joined, len(new)))
if _joined < 50:
    raise SystemExit("FATAL: join produced %d rows -- case-key mismatch, not a real result" % _joined)

print("\n" + "=" * 104)
print("%-20s %-10s %5s %8s %8s %9s %9s" % ("dimension", "reading", "n", "his mu", "inst mu",
                                           "mean err", "EXACT"))
print("=" * 104)
summary = {}
for dim, ycol, top in DIMS:
    for label, src in (("BEFORE", orig), ("AFTER", new)):
        rows = []
        for case, h in human.items():
            y = num(h.get(ycol))
            g = src.get(case) or {}
            m = g.get(dim) if isinstance(g, dict) else None
            if y is not None and isinstance(m, (int, float)):
                rows.append((y, m))
        if len(rows) < 10:
            continue
        ex = 100 * sum(1 for y, m in rows if abs(y - m) < 0.5) / len(rows)
        err = st.mean([m - y for y, m in rows])
        summary.setdefault(dim, {})[label] = (len(rows), ex, err)
        print("%-20s %-10s %5d %8.2f %8.2f %+9.2f %8.0f%%"
              % (dim, label, len(rows), st.mean([y for y, _ in rows]),
                 st.mean([m for _, m in rows]), err, ex))
    print()

print("=" * 104)
print("COMPRESSION CHECK — pull at his LOW levels vs his HIGH levels (AFTER)")
print("=" * 104)
for dim, ycol, top in DIMS:
    lo, hi = [], []
    for case, h in human.items():
        y = num(h.get(ycol))
        g = new.get(case) or {}
        m = g.get(dim) if isinstance(g, dict) else None
        if y is not None and isinstance(m, (int, float)):
            (lo if y <= 2 else hi if y >= 4 else []).append(m - y)
    print("   %-20s low(1-2) %+.2f (n=%d)   high(4+) %+.2f (n=%d)"
          % (dim, st.mean(lo) if lo else 0, len(lo), st.mean(hi) if hi else 0, len(hi)))

json.dump(new, open("/tmp/five_ladders_test.json", "w"), indent=1)
print("\nDONE. before/after:", {d: {k: (v[1], round(v[2], 2)) for k, v in s.items()}
                                for d, s in summary.items()})
