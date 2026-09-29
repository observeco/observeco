"""Parallel corpus runner. The sequential driver spends ~0.85s of process overhead per
case against 0.48s of model time, so the wall-clock is dominated by waiting, not inference.
Concurrency is bounded (default 8) to stay inside API limits; every case is a separate
subprocess, so results are identical to the sequential run -- only the scheduling differs.
Fail-loud: exits non-zero if any case fails or a mixed rubric version appears.
"""
import concurrent.futures as cf
import glob, json, os, subprocess, sys, time
from pathlib import Path
HERE = Path(__file__).resolve().parent
RUBRIC = sys.argv[1] if len(sys.argv) > 1 else "rubric.json"
OUTDIR = sys.argv[2] if len(sys.argv) > 2 else "runs-par"
WORKERS = int(sys.argv[3]) if len(sys.argv) > 3 else 8
os.makedirs(HERE / OUTDIR, exist_ok=True)
cases = sorted(p for p in glob.glob(str(HERE / "inputs-v4" / "*.json"))
               if not os.path.basename(p).startswith("_"))
def one(p):
    r = subprocess.run([sys.executable, str(HERE / "run_jev.py"), p,
                        "--rubric", RUBRIC, "--outdir", OUTDIR],
                       capture_output=True, text=True, cwd=HERE)
    return (p, r.returncode)
t0 = time.time()
fails = []
with cf.ThreadPoolExecutor(max_workers=WORKERS) as ex:
    for p, rc in ex.map(one, cases):
        if rc != 0:
            fails.append(os.path.basename(p))
        else:
            print(".", end="", flush=True)
print()
dt = time.time() - t0
vers = set()
for f in glob.glob(str(HERE / OUTDIR / "jev-*.json")):
    vers.add(json.loads(Path(f).read_text()).get("rubric_version"))
print("cases: %d | failed: %d %s | %.0fs (%.2fs/case) | rubric versions: %s"
      % (len(cases), len(fails), fails[:3], dt, dt/len(cases), sorted(vers)))
if fails or len(vers) != 1:
    sys.exit("FATAL: failures=%d versions=%s" % (len(fails), sorted(vers)))
