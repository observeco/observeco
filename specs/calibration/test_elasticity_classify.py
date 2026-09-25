import json, glob, os
base = "/Users/seanfzc/projects/observeco-main/specs/calibration"

runs = {}
for p in sorted(glob.glob(f"{base}/runs/jev-*.json")):
    d = json.load(open(p))
    c = d.get("case")
    if not c:
        continue
    runs[c] = (
        d.get("raw_jev_scores_0to4", {}).get("market_headroom"),
        d.get("dimensions_display_1to5", {}).get("market_headroom"),
        d.get("evidence_coverage", {}).get("market_headroom"),
    )
    if len(runs) == 1:
        print("RUN TOP-LEVEL KEYS:", list(d.keys()))
        print()

print("### OUTCOMES  (n=%d)" % len(runs))
for c in sorted(runs, key=lambda k: runs[k][0] or 0):
    mh, disp, cov = runs[c]
    print("  %-26s raw=%-5s disp=%-5s cov=%s" % (c, mh, disp, cov))

print()
print("### INPUTS")
for p in sorted(glob.glob(f"{base}/inputs/*.json")):
    d = json.load(open(p))
    print("=" * 72)
    print(os.path.basename(p))
    print(json.dumps(d, indent=1)[:950])
