"""measure_alignment.py — ONE consistent metric, so every iteration is comparable.

The problem this solves: each iteration was measured with a different ad-hoc script, so
results were not comparable across versions. This fixes the metric once and reports it the
same way for every run directory.

TARGETS (satisfactory alignment):
    exact agreement   >= 75%
    disputes (>=2)    <= 5%
    level offset      within +/- 0.25

COMPETITIVE_ROOM IS CLOSED. Sean: "Your definition and application of CR is correct. This
is closed out. I was wrong." and then directed that his CR numbers be adopted. So CR is
reported as agreed and is EXCLUDED from the open-dispute count -- it is no longer something
being tuned, and letting it drag the metric would misdirect the iteration.
"""
import csv
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DIMS = ["relative_strength", "mental_advantage", "defensibility",
        "competitive_room", "market_headroom", "demand_reach"]
ABBR = {"relative_strength": "RS", "mental_advantage": "MA", "defensibility": "DEF",
        "competitive_room": "CR", "market_headroom": "MH", "demand_reach": "DR"}
CLOSED = {"competitive_room"}

T_EXACT, T_DISP, T_OFF = 75.0, 5.0, 0.25


def num(x):
    x = ("" if x is None else str(x)).strip()
    if x.lower() in ("n/a", "na", "", "-", "none", "nan"):
        return None
    try:
        return float(x)
    except Exception:
        return None


def load(run_dir):
    out = {}
    for p in (HERE / run_dir).glob("jev-*.json"):
        r = json.loads(p.read_text())
        disp = r.get("dimensions_display_1to5") or {}
        un = set(r.get("dimensions_unscored") or [])
        out[r["case"]] = {k: (None if k in un else disp.get(k)) for k in DIMS}
    return out


def refused_cases():
    """Corpus-level refusals (synthetic rule representatives). Excluded from every
    denominator -- a rule is not a business, so scoring agreement against it would be
    measuring the wrong thing. See build_refusals.py."""
    f = HERE / "inputs-v4" / "_refused.json"
    if not f.exists():
        return set()
    return set(json.loads(f.read_text()).get("cases") or [])


def stats(pairs):
    n = len(pairs)
    if n < 3:
        return None
    xs = [a for a, _ in pairs]
    ys = [b for _, b in pairs]
    mx, my = sum(xs) / n, sum(ys) / n
    cov = sum((a - mx) * (b - my) for a, b in pairs)
    dx = sum((a - mx) ** 2 for a in xs) ** 0.5
    dy = sum((b - my) ** 2 for b in ys) ** 0.5
    return {
        "n": n, "his": my, "mine": mx, "off": my - mx,
        "slope": cov / (dx ** 2) if dx else 0, "r": cov / (dx * dy) if dx and dy else 0,
        "exact": 100 * sum(1 for a, b in pairs if a == b) / n,
        "disp": 100 * sum(1 for a, b in pairs if abs(b - a) >= 2) / n,
        "up": sum(1 for a, b in pairs if b - a >= 2),
        "down": sum(1 for a, b in pairs if a - b >= 2),
    }


def main(run_dir):
    idx = json.loads((HERE / "inputs-v4" / "_index.json").read_text())
    rows = list(csv.DictReader(open(HERE / "sean-regrade-raw.csv")))
    by = {r["company"]: r for r in rows}
    mine = load(run_dir)
    refused = refused_cases()

    print("=" * 92)
    print("ALIGNMENT — %s   (CR closed/adopted per Sean; %d refused cases excluded)"
          % (run_dir, len(refused)))
    print("=" * 92)
    print()
    print("  %-4s %4s %6s %6s %7s %7s %7s %9s" %
          ("dim", "n", "his", "mine", "offset", "exact", "disp>=2", "slope/r"))
    print("  " + "-" * 70)
    overall = []
    for d in DIMS:
        pairs = []
        for cid, e in idx["companies"].items():
            if cid in refused:
                continue
            m = (mine.get(cid) or {}).get(d)
            h = num((by.get(e["name"]) or {}).get("YOUR_" + ABBR[d]))
            if d in CLOSED and h is not None:
                m = h                      # CR adopted: his number is the answer
            if m is not None and h is not None:
                pairs.append((m, h))
        s = stats(pairs)
        if not s:
            continue
        flag = ""
        if d in CLOSED:
            flag = "  CLOSED"
        else:
            overall.append(s)
            if s["exact"] < T_EXACT or s["disp"] > T_DISP or abs(s["off"]) > T_OFF:
                flag = "  <- open"
            else:
                flag = "  ok"
        print("  %-4s %4d %6.2f %6.2f %+7.2f %6.1f%% %6.1f%%   %.2f/%.2f%s"
              % (ABBR[d], s["n"], s["his"], s["mine"], s["off"], s["exact"],
                 s["disp"], s["slope"], s["r"], flag))

    print()
    print("  " + "-" * 70)
    n = sum(s["n"] for s in overall)
    wex = sum(s["exact"] * s["n"] for s in overall) / n
    wdi = sum(s["disp"] * s["n"] for s in overall) / n
    wof = sum(s["off"] * s["n"] for s in overall) / n
    disp_total = sum(s["up"] + s["down"] for s in overall)
    print("  OPEN DIMENSIONS (RS MA DEF MH DR):")
    print("    exact agreement  %.1f%%   %s (target >=%.0f%%)"
          % (wex, "PASS" if wex >= T_EXACT else "FAIL", T_EXACT))
    print("    disputes (>=2)   %.1f%%   %s (target <=%.0f%%)"
          % (wdi, "PASS" if wdi <= T_DISP else "FAIL", T_DISP))
    print("    level offset     %+.2f   %s (target +/-%.2f)"
          % (wof, "PASS" if abs(wof) <= T_OFF else "FAIL", T_OFF))
    print("    dispute count    %d cases total (%d he-above, %d me-above)"
          % (disp_total, sum(s["up"] for s in overall),
             sum(s["down"] for s in overall)))
    print()

    # worst remaining cases, so the next iteration has a target
    print("  WORST REMAINING (top 12 by |gap| across open dims):")
    print()
    bad = []
    for d in DIMS:
        if d in CLOSED:
            continue
        for cid, e in idx["companies"].items():
            m = (mine.get(cid) or {}).get(d)
            h = num((by.get(e["name"]) or {}).get("YOUR_" + ABBR[d]))
            if m is None or h is None:
                continue
            if abs(h - m) >= 2:
                bad.append((abs(h - m), ABBR[d], e["name"], e["cat"], m, h))
    bad.sort(key=lambda x: -x[0])
    for g, dm, nm, cat, m, h in bad[:12]:
        print("    %-4s %-32s %-14s me %g  him %g  (%s%g)"
              % (dm, nm[:31], cat[:13], m, h, "+" if h > m else "", h - m))
    if len(bad) > 12:
        print("    ... +%d more" % (len(bad) - 12))
    print()
    return wex, wdi, wof


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "runs-v132")
