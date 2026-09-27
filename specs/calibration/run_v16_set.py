"""Run the v1.1.0 corpus (120 businesses) and measure whether the revised level wording
closes the level shift that Q1-Q6 identified.

The test: agreement with Sean's regrade before (v1.0.0) and after (v1.1.0).
If the revision worked, the +0.2 to +0.4 shift should shrink and exact agreement rise.
"""
import glob
import json
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUBRIC = "rubric-v1.6.0.json"
OUTDIR = "runs-v16b"
PROGRESS = HERE / "r16b_progress.json"

cases = sorted(p for p in glob.glob(str(HERE / "inputs-v4" / "*.json"))
               if not p.endswith("_index.json"))
print("cases: %d" % len(cases))

progress = json.loads(PROGRESS.read_text()) if PROGRESS.exists() else {}
if progress:
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
if len(vs) != 1:
    print("** FATAL: mixed rubric versions **")
