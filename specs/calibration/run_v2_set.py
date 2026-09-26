"""Run the 55-case fresh-data validity set. Appends each result as it lands, so
progress survives a timeout. Sleeps between calls (tight loops hit rate-limiting).
"""
import json
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
V2 = HERE / "inputs-v2"
RUNS = HERE / "runs"
PROG = HERE / "v2_progress.json"

files = sorted(f for f in V2.glob("*.json") if not f.name.startswith("_"))
done = {}
if PROG.exists():
    done = json.loads(PROG.read_text())

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
        print("  %-14s FAILED %s" % (f.stem, err.replace("\n", " ")[:110]))
    else:
        d = json.loads(out.read_text())
        done[f.name] = {"case": case, "composite": d.get("composite"),
                        "band": d.get("band"), "secs": round(time.time() - t0, 1),
                        "classification": d.get("classification"),
                        "dims": d.get("dimensions_display_1to5"),
                        "unscored": d.get("dimensions_unscored"),
                        "band_interval": d.get("band_interval")}
        comp = done[f.name]["composite"]
        print("  %-14s %-6s %-24s (%.0fs)"
              % (f.stem, comp if comp is not None else "-",
                 done[f.name]["band"], time.time() - t0))
    PROG.write_text(json.dumps(done, indent=2))
    time.sleep(6)

ok = [v for v in done.values() if "composite" in v or "band" in v]
err = [k for k, v in done.items() if "error" in v]
print()
print("complete: %d | failed: %d" % (len(ok), len(err)))
if err:
    print("failed:", err)
