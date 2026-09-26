import json, glob
BASE = "/Users/seanfzc/projects/observeco-main/specs/calibration"

def load(p):
    return json.load(open(p))

rub = load(f"{BASE}/rubric.json")
meta = rub["_meta"]
q = (rub.get("questions") or {}).get("market_headroom") or {}

print("=" * 100)
print("A. THE SCALE THE MODEL IS GIVEN -- market_headroom anchors")
print("=" * 100)
print("type         :", q.get("type"))
print("level_counts :", (meta.get("level_counts") or {}).get("market_headroom"))
print("gate floor   :", (meta.get("gates") or {}).get("market_headroom"))
print()
print("INSTRUCTIONS:")
print((q.get("instructions") or "")[:700])
print()
levels = q.get("levels") or q.get("criteria") or []
for i, lv in enumerate(levels):
    txt = lv if isinstance(lv, str) else json.dumps(lv)
    print("--- level %d (display %d) ---" % (i, i + 1))
    print(txt[:420])
    print()

# ------------------------------------------------------------------ B
rows = []
for p in sorted(glob.glob(f"{BASE}/runs/jev-*.json")):
    d = load(p)
    c = d.get("case")
    if not c:
        continue
    rows.append({
        "case": c,
        "raw": d.get("raw_jev_scores_0to4", {}).get("market_headroom"),
        "probs": (d.get("probabilities") or {}).get("market_headroom") or {},
        "cov": d.get("evidence_coverage", {}).get("market_headroom"),
        "disp": d.get("dimensions_display_1to5", {}).get("market_headroom"),
    })
rows.sort(key=lambda r: r["raw"] or 0)

print("=" * 100)
print("B. DISTRIBUTION -- raw score + the model's own level probabilities")
print("=" * 100)
print("%-24s %6s %5s  %s" % ("case", "raw", "disp", "level probabilities (0..4)   L0mass"))
print("-" * 100)
for r in rows:
    pr = r["probs"]
    if not pr:
        print("%-24s %6s %5s  (none)" % (r["case"], r["raw"], r["disp"]))
        continue
    vec = "  ".join("%s:%.2f" % (k, pr[k]) for k in sorted(pr, key=lambda x: int(x)))
    l0 = float(pr.get("0", 0))
    print("%-24s %6s %5s  %s   %.2f" % (r["case"], r["raw"], r["disp"], vec, l0))

# ------------------------------------------------------------------ C
print()
print("=" * 100)
print("C. WHERE DOES THE MODEL'S MASS ACTUALLY SIT? (mean probability per level)")
print("=" * 100)
lvls = sorted({k for r in rows for k in r["probs"]}, key=lambda x: int(x))
n = len([r for r in rows if r["probs"]])
for L in lvls:
    m = sum(float(r["probs"].get(L, 0)) for r in rows if r["probs"]) / max(n, 1)
    bar = "#" * int(m * 100)
    print("  level %s (display %s): mean mass %.3f  %s" % (L, int(L) + 1, m, bar))

print()
print("  distinct levels with mean mass > 0.10 : %s"
      % [L for L in lvls
         if sum(float(r["probs"].get(L, 0)) for r in rows if r["probs"]) / max(n, 1) > 0.10])
print("  cases with L0 mass > 0.05            : %d of %d"
      % (len([r for r in rows if float((r["probs"] or {}).get("0", 0)) > 0.05]), n))
print("  cases with L4 mass > 0.05            : %d of %d"
      % (len([r for r in rows if float((r["probs"] or {}).get("4", 0)) > 0.05]), n))

# ------------------------------------------------------------------ D
print()
print("=" * 100)
print("D. THE FLOOR QUESTION -- VICOM (1.57) vs N1 CLOSED BUSINESS (1.69)")
print("=" * 100)
for name in ("F3-vicom", "N1-closedbusiness"):
    r = [x for x in rows if x["case"] == name]
    if not r:
        print(name, "not found"); continue
    r = r[0]
    print()
    print("  %s" % name)
    print("    raw=%s  display=%s  coverage=%s" % (r["raw"], r["disp"], r["cov"]))
    print("    probabilities: %s" % json.dumps(r["probs"], sort_keys=True))
    tot = sum(int(k) * float(v) for k, v in r["probs"].items())
    print("    E[level] recomputed = %.3f   (round-half-up -> display %d)"
          % (tot, int(round(tot)) + 1))

print()
for name in ("N1-closedbusiness", "F3-vicom"):
    p = "%s/inputs/%s.json" % (BASE, name)
    try:
        d = load(p)
    except Exception as e:
        print(name, "input unreadable:", e); continue
    m = d.get("_meta", {})
    print("  %s -- business: %s" % (name, m.get("business")))
    print("      purpose: %s" % (m.get("purpose") or m.get("control_type")))
    print("      ground_truth: %s" % (m.get("ground_truth") or "")[:300])
    print()

# ------------------------------------------------------------------ E
print("=" * 100)
print("E. IS raw == E[level]?  (sanity: score is probability-weighted)")
print("=" * 100)
bad = 0
for r in rows:
    if not r["probs"] or r["raw"] is None:
        continue
    ev = sum(int(k) * float(v) for k, v in r["probs"].items())
    if abs(ev - float(r["raw"])) > 0.03:
        print("  MISMATCH %-24s raw=%s  E=%.3f" % (r["case"], r["raw"], ev))
        bad += 1
print("  mismatches: %d  (tolerance 0.03)" % bad)
