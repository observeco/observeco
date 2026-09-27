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
RUBRIC = "rubric-v1.7.0.json"
OUTDIR = "runs-v17"
PROGRESS = HERE / "r17_progress.json"

cases = sorted(p for p in glob.glob(str(HERE / "inputs-v4" / "*.json"))
               if not p.endswith("_index.json"))
print("cases: %d" % len(cases))

progress = json.loads(PROGRESS.read_text()) if PROGRESS.exists() else {}
if progress:
    # GUARD 1: refuse to resume off a progress file built by a different rubric.
    # Added after a silent failure: a previous generated runner inherited OUTDIR and
    # PROGRESS from its parent, "resumed" off a stale file, ran NOTHING, printed
    # "complete: 120", and left an EMPTY output directory as the only evidence.
    vs0 = {v.get("rubric_version") for v in progress.values()
           if isinstance(v, dict) and v.get("case")}
    if vs0 and vs0 != {"1.7.0"}:
        sys.exit("FATAL: %s holds rubric versions %s, expected 1.7.0. A stale progress "
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

# GUARD 2: a "complete" run must actually have written files.
n_out = len(list((HERE / OUTDIR).glob("jev-*.json")))
print("output files: %d" % n_out)
if n_out == 0:
    sys.exit("FATAL: run reported complete but %s is EMPTY -- nothing was scored." % OUTDIR)
if vs != {"1.7.0"}:
    sys.exit("FATAL: mixed or wrong rubric versions: %s" % sorted(x for x in vs if x))
