"""Run the v1.11.2 corpus (mental_advantage re-anchored to Sean's labels).

Copy of run_v17_set.py with a fail-loud guard against inheriting a stale OUTDIR/PROGRESS
from its parent -- the exact silent failure that produced an empty runs-v17 and a false
"complete: 120" message.
"""
import glob
import json
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUBRIC = "rubric.json"
OUTDIR = "runs-v1112"
PROGRESS = HERE / "r1112_progress.json"

cases = sorted(p for p in glob.glob(str(HERE / "inputs-v4" / "*.json"))
               if not p.endswith("_index.json"))
print("cases: %d" % len(cases))

progress = json.loads(PROGRESS.read_text()) if PROGRESS.exists() else {}
if progress:
    vs0 = {v.get("rubric_version") for v in progress.values()
           if isinstance(v, dict) and v.get("case")}
    if vs0 and vs0 != {"1.11.2"}:
        sys.exit("FATAL: %s holds rubric versions %s, expected 1.11.2. A stale progress "
                 "file would silently skip every case." % (PROGRESS.name, vs0))
    print("resuming: %d done" % len(progress))

start = time.time()
fail = 0
for p in cases:
    name = Path(p).name
    if name in progress and progress[name].get("case"):
        continue
    r = subprocess.run([sys.executable, str(HERE / "run_jev.py"), p,
                        "--rubric", RUBRIC, "--outdir", OUTDIR],
                       capture_output=True, text=True, cwd=str(HERE))
    if r.returncode != 0:
        fail += 1
        progress[name] = {"error": (r.stderr or "")[-300:]}
        print("  %-38s FAILED" % name)
    else:
        try:
            out = json.loads((HERE / OUTDIR / ("jev-%s.json" % name[:-5])).read_text())
            progress[name] = {"case": name[:-5], "composite": out.get("composite"),
                              "band": out.get("band"),
                              "rubric_version": out.get("rubric_version"),
                              "dims": out.get("dimensions_display_1to5"),
                              "unscored": out.get("dimensions_unscored")}
            print("  %-38s %s" % (name, out.get("composite")))
        except Exception as e:
            fail += 1
            progress[name] = {"error": "readback %s" % e}
    PROGRESS.write_text(json.dumps(progress, indent=2))
    time.sleep(0.3)

print()
print("complete: %d | failed: %d | %.0fs"
      % (len([v for v in progress.values() if v.get("case")]), fail, time.time() - start))
vs = {v.get("rubric_version") for v in progress.values() if v.get("case")}
print("rubric versions: %s" % sorted(x for x in vs if x))

n_out = len(list((HERE / OUTDIR).glob("jev-*.json")))
print("output files: %d" % n_out)
if n_out == 0:
    sys.exit("FATAL: run reported complete but %s is EMPTY -- nothing was scored." % OUTDIR)
if vs != {"1.11.2"}:
    sys.exit("FATAL: mixed or wrong rubric versions: %s" % sorted(x for x in vs if x))
