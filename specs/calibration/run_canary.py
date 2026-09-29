"""run_canary.py — the launch gate of spec 095 section 10.6.

WHAT THIS IS
------------
The canary corpus answers a different question from the calibration corpus (spec 10.1.1):
  - canary      = SAME input, FIXED expected output, run on a schedule. Detects DRIFT.
  - calibration = how closely the instrument tracks a human grader. Measures AGREEMENT.

A canary whose fixture moves detects nothing, so these fixtures are frozen. This script runs
them and compares BAND ONLY -- D1 makes band agreement the bar and spec 10.6 states that
dimension-exact is explicitly NOT the bar.

TWO RUNGS
---------
  --rung record   run and WRITE the reference snapshot, if none exists (first run only)
  --rung check    run and COMPARE against the stored snapshot (the scheduled job)

The split exists because a canary cannot compare against itself. The first run has no
reference, so it records one. Every later run compares. A check run with no snapshot FAILS
LOUDLY rather than silently passing -- a canary that reports green because it has nothing to
compare against is worse than no canary.

MODES
-----
  --dry-run   print the flattened state for each case; make no API call
  --fixture   compare the stored fixtures' _expected blocks against each other and exit;
              no API call. Verifies the corpus is internally consistent and frozen.

Exit codes: 0 pass | 1 FAIL | 2 could not run (no key / model unavailable / no snapshot)
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CANARY_DIR = HERE / "canary"
SNAP = CANARY_DIR / "_reference.json"
RUNS = CANARY_DIR / "runs"


def load_fixtures():
    out = []
    for p in sorted(CANARY_DIR.glob("C*.json")):
        out.append((p, json.loads(p.read_text())))
    return out


def band_of(c, bands):
    if c is None:
        return None
    c = round(c)
    for nm, lo, hi in bands:
        if lo <= c <= hi:
            return nm
    # bands are integer-only and do not tile the line; clamp rather than crash
    return bands[0][0] if c < bands[0][1] else bands[-1][0]


def run_case(path, rubric, outdir, dry):
    """Invoke run_jev.py for one fixture. Returns (case, composite, band, dims) or None."""
    cmd = [sys.executable, str(HERE / "run_jev.py"), str(path),
           "--rubric", rubric, "--outdir", str(outdir)]
    if dry:
        cmd.append("--dry-run")
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=HERE)
    if r.returncode == 2:
        return None, r.stderr.strip()
    if r.returncode != 0:
        return None, (r.stderr.strip() or r.stdout.strip())[-400:]
    out = json.loads((outdir / ("jev-%s.json" % json.loads(path.read_text())["_meta"]["case"])).read_text())
    return out, ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rung", choices=["check", "record"], default="check")
    ap.add_argument("--rubric", default="rubric-v1.8.0.json")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--fixture", action="store_true",
                    help="verify the fixture corpus only; no API call")
    ap.add_argument("--force", action="store_true",
                    help="allow a record run to overwrite an existing reference")
    args = ap.parse_args()

    fixtures = load_fixtures()

    # ---- fixture-only self-check -------------------------------------------------
    if args.fixture or args.dry_run:
        rubric = json.loads((HERE / args.rubric).read_text())
        bands = rubric["_meta"]["bands"]
        print("=" * 92)
        print("CANARY CORPUS — %d fixtures" % len(fixtures))
        print("=" * 92)
        ok = True
        for p, fx in fixtures:
            m, e = fx["_meta"], fx["_expected"]
            comp = None
            # recompute the expected composite from the expected dimension vector, so
            # the fixture states its own band rather than asserting a number
            W = rubric["_meta"]["weights"]
            CNT = {d: len(rubric["questions"][d]["levels"]) for d in W}
            scored = [d for d in W if e["dimensions"].get(d) is not None]
            tot = sum(W[d] for d in scored)
            comp = round(sum(e["dimensions"][d] / CNT[d] * (W[d] / tot * 100) for d in scored))
            band = band_of(comp, bands)
            agree = band == e["band"]
            if not agree:
                ok = False
            print("  %-18s expected band %-20s -> composite %3d = %-20s %s"
                  % (m["case"], e["band"], comp, band, "OK" if agree else "MISMATCH"))
            if args.dry_run:
                print("      source: %s" % m["source_document"])
                for k, v in fx["form"].items():
                    print("        %s: %s" % (k, str(v)[:96]))
                print()
        print()
        print("  fixture self-consistency: %s" % ("PASS" if ok else "FAIL"))
        print("  (each fixture's expected band must equal the band its expected dimension")
        print("   vector produces under the rubric's own weights and level counts)")
        return 0 if ok else 1

    # ---- run ---------------------------------------------------------------------
    rubric = json.loads((HERE / args.rubric).read_text())
    bands = rubric["_meta"]["bands"]

    # ⚠ A CHECK RUN MUST NOT WRITE INTO canary/runs/.
    # WHY THIS CHANGED: both rungs wrote into the COMMITTED `canary/runs/` directory, so
    # every drift check rewrote the reference artifacts it was checking against. Two
    # consequences, both bad: (1) the repo was left dirty after a read-only check, and
    # (2) the checked-in run files silently drifted -- a review of "what the canary
    # recorded" would read the LATEST run rather than the recorded one. A drift check that
    # mutates the thing it measures is not a drift check.
    # A record run still writes the real directory, because that IS its purpose.
    if args.rung == "record":
        RUNS.mkdir(parents=True, exist_ok=True)
        run_dir = RUNS
    else:
        run_dir = CANARY_DIR / "runs-check"
        run_dir.mkdir(parents=True, exist_ok=True)

    results, failures = {}, []
    for p, fx in fixtures:
        out, err = run_case(p, args.rubric, run_dir, False)
        if out is None:
            failures.append((fx["_meta"]["case"], err))
            continue
        d = out["dimensions_display_1to5"]
        results[fx["_meta"]["case"]] = {
            "band": out.get("band"),
            "composite": out.get("composite"),
            "dims": d,
            "rubric_version": (rubric["_meta"]["version"]),
            "model_id": out.get("model_id"),
        }

    if failures:
        print("CANARY COULD NOT RUN — no comparison made (this is NOT a pass)", file=sys.stderr)
        for c, e in failures:
            print("  %s: %s" % (c, e[:300]), file=sys.stderr)
        return 2

    if args.rung == "record":
        if SNAP.exists() and not args.force:
            print("reference already exists at %s — refusing to overwrite on a record run."
                  % SNAP.relative_to(HERE), file=sys.stderr)
            print("Delete it deliberately if you truly mean to re-baseline.", file=sys.stderr)
            return 2
        SNAP.write_text(json.dumps({
            "rubric_version": rubric["_meta"]["version"],
            "note": ("REFERENCE SNAPSHOT for the canary. Fixed output for a fixed input. "
                     "A canary whose fixture moves detects nothing (spec 10.1.1)."),
            "cases": results,
        }, indent=2) + "\n")
        print("recorded reference -> %s" % SNAP.relative_to(HERE))
        return 0

    # ---- check -------------------------------------------------------------------
    if not SNAP.exists():
        print("NO REFERENCE SNAPSHOT at %s." % SNAP.relative_to(HERE), file=sys.stderr)
        print("Run with --rung record once to create it. A canary with nothing to compare")
        print("against must not report green.", file=sys.stderr)
        return 2

    ref = json.loads(SNAP.read_text())["cases"]
    print("=" * 92)
    print("CANARY — drift check")
    print("=" * 92)
    # NOTE: this printed the CURRENT rubric twice (HERE/args.rubric), so the "reference"
    # version shown was always wrong. The snapshot carries its own version -- use it.
    print("  reference rubric: %s (frozen snapshot)    current rubric: %s"
          % (json.loads(SNAP.read_text()).get("rubric_version", "?"),
             rubric["_meta"]["version"]))
    print()
    drift = []
    for case, cur in results.items():
        r = ref.get(case)
        if r is None:
            drift.append((case, "absent from reference", r, cur))
            continue
        if r["band"] != cur["band"]:
            drift.append((case, "band moved", r["band"], cur["band"]))
        else:
            moved = [d for d in cur["dims"]
                     if r["dims"].get(d) != cur["dims"].get(d)]
            cur["_dims_moved"] = moved
        print("  %-18s ref %-20s cur %-20s %s"
              % (case, r["band"], cur["band"],
                 "OK" if r["band"] == cur["band"] else "DRIFT"))
        if r.get("dims"):
            moved = [d for d in cur["dims"] if r["dims"].get(d) != cur["dims"].get(d)]
            if moved:
                print("      dimensions moved (advisory — not a failure, spec 10.6):")
                for d in moved:
                    print("        %-22s %s -> %s" % (d, r["dims"].get(d), cur["dims"].get(d)))
    print()

    # ---- INFORMATIONAL: expected (engagement conclusion) vs actual -----------------
    # This is NOT the drift check and NOT a launch gate. The drift check above compares
    # against the frozen reference (has BEHAVIOUR moved?). This compares against the
    # engagement's own conclusion (does the instrument AGREE?). A canary must never be
    # tuned to make this number look good -- that would destroy its ability to detect drift.
    agree = dis = 0
    print("  " + "-" * 86)
    print("  INFORMATIONAL ONLY — instrument vs the engagement's own conclusion")
    print("  (NOT the drift check, NOT a launch gate; the expected vectors for cases")
    print("   without a recorded human label are assistant mappings — see each _meta)")
    print()
    for case, cur in results.items():
        fx = json.loads((CANARY_DIR / ("%s.json" % case)).read_text())
        e = fx["_expected"]
        hit = e["band"] == cur["band"]
        agree += hit
        dis += (not hit)
        print("    %-18s engagement %-20s instrument %-20s %s"
              % (case, e["band"], cur["band"], "match" if hit else "DIFFERS"))
        if not hit:
            moved = [d for d in e["dimensions"] if cur["dims"].get(d) != e["dimensions"][d]]
            for d in moved:
                print("        %-22s engagement %s -> instrument %s"
                      % (d, e["dimensions"][d], cur["dims"].get(d)))
    print()
    print("    agreement with the engagement conclusions: %d of %d" % (agree, agree + dis))
    print()
    if drift:
        print("  CANARY FAILED — the model or the rubric moved:")
        for c, why, a, b in drift:
            print("    %s: %s (%s -> %s)" % (c, why, a, b))
        return 1
    print("  CANARY PASSED — no band moved across %d cases." % len(results))
    return 0


if __name__ == "__main__":
    sys.exit(main())
