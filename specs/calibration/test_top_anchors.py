"""TEST: do the rewritten TOP ANCHORS move the instrument's top-level awards up toward Sean's?

Runs the REAL model over the 120-case regrade corpus (inputs-v4 + runs-par), with ONLY the rewritten
level text injected in memory, then compares per-dimension level distributions against Sean's own
grades in sean-regrade-raw.csv.

Fails loud if the corpus is not joined -- a partial join would silently understate the effect.
"""
import concurrent.futures as cf
import copy, csv, glob, json, os, sys, statistics as st
from collections import Counter

BASE = "/Users/seanfzc/projects/observeco-main/specs/calibration"
sys.path.insert(0, BASE)
import run_jev

DRAFT = json.load(open("/tmp/top_anchors.json"))
rub = json.load(open(f"{BASE}/rubric.json"))
rub2 = copy.deepcopy(rub)
for dim, spec in DRAFT.items():
    q = rub2["questions"][dim]
    old_top = q["levels"][-1]
    q["levels"][-1] = spec["levels"][-1]
    q["instructions"] = q["instructions"] + "\n\n" + spec["added"]

# join key: case id -> Sean's grades
human = {}
for r in csv.DictReader(open(f"{BASE}/sean-regrade-raw.csv")):
    cid = (r.get("case_id") or "").strip()
    if cid:
        human[cid.lower()] = r

CASES = sorted(p for p in glob.glob(f"{BASE}/inputs-v4/*.json")
               if not os.path.basename(p).startswith("_"))
print("corpus cases: %d" % len(CASES))

PAIRS = [("mental_advantage", "YOUR_MA"), ("demand_reach", "YOUR_DR"),
         ("competitive_room", "YOUR_CR")]


def num(x):
    try:
        return float(x)
    except Exception:
        return None


def one(path):
    payload = json.load(open(path))
    case = os.path.basename(path)[:-5]
    try:
        state = run_jev.build_state(payload)
        qs = run_jev.build_questions(rub2)
        res = run_jev.call_jev(state, qs, rub["_meta"]["model"])
        if res is None:
            return (case, None)
        got = {}
        for dim, _ in PAIRS:
            a = (res.get("answers") or {}).get(dim) or {}
            s = a.get("score")
            got[dim] = (int(round(s)) + 1) if isinstance(s, (int, float)) else None
        return (case, got)
    except Exception as e:
        return (case, "ERR:%s" % type(e).__name__)


out = {}
with cf.ThreadPoolExecutor(max_workers=6) as ex:
    for case, got in ex.map(one, CASES):
        out[case] = got
        print(".", end="", flush=True)
print()

joined = 0
for dim, ycol in PAIRS:
    rows = []
    for case, got in out.items():
        if not isinstance(got, dict):
            continue
        h = human.get(case.lower())
        if not h:
            continue
        y, m = num(h.get(ycol)), got.get(dim)
        if y is None or m is None:
            continue
        rows.append((y, m))
    if not rows:
        print("%s -- NO JOIN" % dim); continue
    joined += len(rows)
    ys = [r[0] for r in rows]; ms = [r[1] for r in rows]
    top_y = sum(1 for y in ys if y >= (4 if dim == "competitive_room" else 5))
    top_m = sum(1 for m in ms if m >= (4 if dim == "competitive_room" else 5))
    print("\n%-20s n=%d  his mean %.2f  new mean %.2f  diff %+.2f  exact %.0f%%"
          % (dim, len(rows), st.mean(ys), st.mean(ms), st.mean(ys) - st.mean(ms),
             100 * sum(1 for y, m in rows if abs(y - m) < 0.5) / len(rows)))
    print("   TOP-LEVEL AWARDS: his %d  ->  instrument (NEW) %d" % (top_y, top_m))
    yc = Counter(int(round(y)) for y in ys); mc = Counter(int(round(m)) for m in ms)
    for lv in sorted(set(yc) | set(mc)):
        print("      level %d   his %3d   new %3d" % (lv, yc.get(lv, 0), mc.get(lv, 0)))

json.dump(out, open("/tmp/topanchor_test.json", "w"), indent=1)
print("\njoined rows: %d  (0 would mean the join key is wrong)" % joined)
