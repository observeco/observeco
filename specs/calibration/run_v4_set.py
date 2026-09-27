"""Run the deduped v4 corpus (121 businesses) under rubric v1.0.0 (six dimensions).

Writes to runs-v4/ so the 0.9.0 baseline in runs/ is never touched.
Records the rubric version per run file -- a corpus split across rubric versions is
invalid, so this asserts a single version across the whole run.
"""
import glob
import json
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUBRIC = "rubric-v1.0.0.json"
OUTDIR = "runs-v4"
PROGRESS = HERE / "v4_progress.json"

cases = sorted(p for p in glob.glob(str(HERE / "inputs-v4" / "*.json"))
               if not p.endswith("_index.json"))
print("cases to run: %d" % len(cases))

progress = {}
if PROGRESS.exists():
    progress = json.loads(PROGRESS.read_text())
    print("resuming: %d already done" % len(progress))

start = time.time()
fail = 0
for i, p in enumerate(cases, 1):
    name = Path(p).name
    if name in progress and progress[name].get("case"):
        continue
    cmd = [sys.executable, str(HERE / "run_jev.py"), p,
           "--rubric", RUBRIC, "--outdir", OUTDIR]
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=str(HERE))
    if r.returncode != 0:
        fail += 1
        progress[name] = {"error": (r.stderr or "")[-400:]}
        print("  %-42s FAILED" % name)
    else:
        # read back what was written
        out = None
        try:
            idx = json.loads((HERE / "inputs-v4" / "_index.json").read_text())
            cid = idx["companies"][name[:-5]]["case"]
            out = json.loads((HERE / OUTDIR / ("jev-%s.json" % cid)).read_text())
            progress[name] = {"case": cid, "composite": out.get("composite"),
                              "band": out.get("band"),
                              "rubric_version": out.get("rubric_version"),
                              "gates": out.get("gates_firing") or []}
        except Exception as e:
            fail += 1
            progress[name] = {"error": "readback: %s" % e}
        if out:
            comp = out.get("composite")
            band = "GATE" if comp is None else str(comp)
            print("  %-42s %-6s %s" % (name, band,
                                       out.get("band") if comp is not None else
                                       ",".join(out.get("gates_firing") or [])))
    PROGRESS.write_text(json.dumps(progress, indent=2))
    time.sleep(0.4)   # stay under the rate limit

print()
print("complete: %d | failed: %d | %.0fs" % (
    len([v for v in progress.values() if v.get("case")]), fail, time.time() - start))

# --- integrity: one rubric version across the whole corpus -------------------
versions = {v.get("rubric_version") for v in progress.values() if v.get("case")}
print("rubric versions present: %s" % sorted(x for x in versions if x))
if len(versions) != 1:
    print("** FATAL: corpus split across rubric versions -- INVALID **")
else:
    print("single rubric version across the corpus: OK")
