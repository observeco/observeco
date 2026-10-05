"""ISOLATE THE WINNER + MEASURE THE NOISE FLOOR.

The full five-ladder rewrite moved agreement like this (exact, n=120):
    competitive_room  23% -> 41%   (+18)   clear win
    position_strength 32% -> 35%   (+2.5)  within noise?
    defensibility     54% -> 54%   ( 0)
    mental_advantage  52% -> 49%   (-3)    within noise?
    demand_reach      59% -> 40%   (-19)   clear regression

Two questions before anything is applied:
  1. Does competitive_room's win SURVIVE IN ISOLATION (no other ladder changed)?
  2. What does a repeat run of the SAME config look like -- i.e. is +2.5/-3 real or run noise?

So: run competitive_room-only TWICE. The two runs against each other give the noise floor; the pair
against BEFORE gives the isolated effect.
"""
import concurrent.futures as cf
import copy, csv, glob, json, os, sys, statistics as st

BASE = "/Users/seanfzc/projects/observeco-main/specs/calibration"
sys.path.insert(0, BASE)
import run_jev

DRAFT = json.load(open("/tmp/five_ladders.json"))
ONLY = ["competitive_room"]

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


orig = {}
for p in glob.glob(f"{BASE}/runs-par/jev-*.json"):
    d = json.load(open(p))
    c = (d.get("case") or "").lower()
    if c:
        orig[c] = d.get("dimensions_display_1to5") or {}

rub = json.load(open(f"{BASE}/rubric.json"))
CASES = sorted(p for p in glob.glob(f"{BASE}/inputs-v4/*.json")
               if not os.path.basename(p).startswith("_"))

DIMS = [("position_strength", "YOUR_RS"), ("mental_advantage", "YOUR_MA"),
        ("defensibility", "YOUR_DEF"), ("competitive_room", "YOUR_CR"),
        ("demand_reach", "YOUR_DR")]


def build_rubric(dims):
    r2 = copy.deepcopy(rub)
    for dim in dims:
        spec = DRAFT[dim]
        r2["questions"][dim]["levels"] = list(spec["levels"])
        r2["questions"][dim]["instructions"] = r2["questions"][dim]["instructions"] + "\n\n" + spec["added"]
    return r2


def run(dims, tag):
    r2 = build_rubric(dims)

    def one(path):
        payload = json.load(open(path))
        case = os.path.basename(path)[:-5].lower()
        try:
            res = run_jev.call_jev(run_jev.build_state(payload),
                                   run_jev.build_questions(r2), rub["_meta"]["model"])
            if res is None:
                return case, None
            out = {}
            for dim, _ in DIMS:
                a = (res.get("answers") or {}).get(dim) or {}
                s = a.get("score")
                out[dim] = (int(round(s)) + 1) if isinstance(s, (int, float)) else None
            return case, out
        except Exception as e:
            return case, "ERR:%s" % type(e).__name__

    got = {}
    with cf.ThreadPoolExecutor(max_workers=6) as ex:
        for case, g in ex.map(one, CASES):
            got[case] = g
    j = sum(1 for c in got if c in human)
    print("[%s] ran %d, joined %d" % (tag, len(got), j), flush=True)
    if j < 50:
        raise SystemExit("FATAL: join %d -- case-key mismatch" % j)
    return got


def score(src, dim, ycol):
    rows = []
    for case, h in human.items():
        y = num(h.get(ycol))
        g = src.get(case) or {}
        m = g.get(dim) if isinstance(g, dict) else None
        if y is not None and isinstance(m, (int, float)):
            rows.append((y, m))
    if len(rows) < 10:
        return None
    return (len(rows),
            100 * sum(1 for y, m in rows if abs(y - m) < 0.5) / len(rows),
            st.mean([m - y for y, m in rows]))


A = run(ONLY, "CR-ONLY run A")
B = run(ONLY, "CR-ONLY run B")
json.dump({"A": A, "B": B}, open("/tmp/cr_isolated.json", "w"))

print("\n" + "=" * 100)
print("ISOLATED competitive_room REWRITE  vs  BEFORE,  and  A-vs-B (the noise floor)")
print("=" * 100)
print("%-20s %10s %10s %10s %12s" % ("dimension", "BEFORE", "CR-only A", "CR-only B", "A vs B"))
for dim, ycol in DIMS:
    b = score(orig, dim, ycol)
    a = score(A, dim, ycol)
    c = score(B, dim, ycol)
    if not (b and a and c):
        continue
    ab = 100 * sum(1 for case in human
                   if isinstance((A.get(case) or {}).get(dim), (int, float))
                   and isinstance((B.get(case) or {}).get(dim), (int, float))
                   and (A[case][dim] == B[case][dim])) / max(
        1, sum(1 for case in human
               if isinstance((A.get(case) or {}).get(dim), (int, float))
               and isinstance((B.get(case) or {}).get(dim), (int, float))))
    print("%-20s %9.0f%% %9.0f%% %9.0f%% %11.0f%%" % (dim, b[1], a[1], c[1], ab))
print()
print("%-20s %10s %10s %10s" % ("dimension", "BEFORE err", "A err", "B err"))
for dim, ycol in DIMS:
    b = score(orig, dim, ycol); a = score(A, dim, ycol); c = score(B, dim, ycol)
    if b and a and c:
        print("%-20s %+9.2f %+9.2f %+9.2f" % (dim, b[2], a[2], c[2]))
print("\nDONE")
