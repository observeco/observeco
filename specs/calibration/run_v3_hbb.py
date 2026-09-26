"""Run the 52-case home-based business set. Appends progress as it lands."""
import json
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
V3 = HERE / "inputs-v3"
RUNS = HERE / "runs"
PROG = HERE / "v3_progress.json"

files = sorted(f for f in V3.glob("*.json") if not f.name.startswith("_"))
done = json.loads(PROG.read_text()) if PROG.exists() else {}
print("running %d cases (%d already done)" % (len(files), len(done)))
for f in files:
    if f.name in done:
        continue
    t0 = time.time()
    r = subprocess.run([sys.executable, "run_jev.py", str(f.relative_to(HERE))],
                       cwd=HERE, capture_output=True, text=True)
    spec = json.loads(f.read_text())
    case = spec["_meta"]["case"]
    out = RUNS / ("jev-%s.json" % case)
    if r.returncode != 0 or not out.exists():
        err = (r.stderr or r.stdout or "")[-300:]
        done[f.name] = {"error": err}
        print("  %-14s FAILED %s" % (f.stem, err.replace("\n", " ")[:100]))
    else:
        d = json.loads(out.read_text())
        done[f.name] = {
            "case": case, "composite": d.get("composite"), "band": d.get("band"),
            "label": spec["_meta"]["PRE_REGISTERED_LABEL"],
            "rubric_version": d.get("rubric_version"),
            "coverage": d.get("evidence_coverage"),
            "dims": d.get("dimensions_display_1to5"),
            "unscored": d.get("dimensions_unscored"),
            "band_interval": d.get("band_interval"),
            "gates": d.get("gates_firing"),
            "secs": round(time.time() - t0, 1),
        }
        print("  %-14s %-6s %-24s cov_min=%.2f (%.0fs)"
              % (f.stem, done[f.name]["composite"] if done[f.name]["composite"] is not None else "-",
                 done[f.name]["band"],
                 min((done[f.name]["coverage"] or {"x": 1}).values()), time.time() - t0))
    PROG.write_text(json.dumps(done, indent=2))
    time.sleep(6)

ok = [v for v in done.values() if "band" in v]
err = [k for k, v in done.items() if "error" in v]
print()
print("complete: %d | failed: %d" % (len(ok), len(err)))
if err:
    print("failed:", err)
