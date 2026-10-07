"""promote_rubric.py — spec 095 section 5.3.1: the rubric promotion step.

Why this is a script and not a copy command
-------------------------------------------
Spec 5.3 says: "The Python calibration harness and the production scorer must read the same
rubric JSON. This is the most likely way to fool ourselves." It happened: the file a scorer
would load (rubric.json) sat at 0.9.0 with no position_strength, while calibration validated
1.8.0 in a differently-named file. Nothing was serving the instrument that was validated.

This script is the gate. It refuses to promote unless every condition holds, and it fails
loudly rather than leaving a half-promoted file.
"""
import importlib
import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
LIVE = HERE / "rubric.json"

# 1.19.0: position_strength is the current name for the dimension formerly called
# position_strength. The gate must accept a file carrying EITHER -- every frozen historical
# rubric uses the old name.
SIX = ["position_strength", "mental_advantage", "defensibility",
       "competitive_room", "market_headroom", "demand_reach"]
LEGACY = {"position_strength": "relative_strength"}
def _has(d, container):
    return d in container or LEGACY.get(d) in container


def load(p):
    return json.loads(Path(p).read_text())


def vtuple(v):
    """Version key for ordering. Naive string compare is WRONG here: '1.19.0' < '1.8.0' lexically,
    so a string compare would rate the newer rubric as older and block an upgrade as a rollback."""
    parts = []
    for p in str(v).split("."):
        try:
            parts.append(int(p))
        except ValueError:
            parts.append(0)
    return tuple(parts)


def main(src_name, allow_rollback=False):
    src = HERE / src_name
    if not src.exists():
        print("FATAL: %s does not exist" % src, file=sys.stderr)
        return 2

    V = load(src)
    problems = []

    # 1. version stamps must agree -- the bug that let two different files both claim 1.2.0
    if V.get("version") != V["_meta"].get("version"):
        problems.append("top-level version=%r but _meta.version=%r"
                        % (V.get("version"), V["_meta"].get("version")))

    # 2. the six calibrated dimensions must be present and scored
    missing = [d for d in SIX if not _has(d, V["questions"])]
    if missing:
        problems.append("missing dimensions: %s" % missing)

    # 3. weights must sum to the documented 100
    w = V["_meta"]["weights"]
    if sum(w.values()) != 100:
        problems.append("weights sum to %s, not 100" % sum(w.values()))

    # 4. the position_strength axis must exist -- its absence is what marked the old live file
    if not _has("position_strength", w):
        problems.append("position_strength has no weight (the 0.9.0 defect, under its old name "
                        "relative_strength)")

    # 5. bands must be present and ordered
    bands = V["_meta"]["bands"]
    if len(bands) != 4 or [b[0] for b in bands][0] != "Fragile":
        problems.append("unexpected band table: %s" % bands)

    # 6. score gates must have been removed (they were, by calibration)
    live_gates = {k: v for k, v in (V["_meta"].get("gates") or {}).items()
                  if not k.startswith("_")}
    if live_gates:
        problems.append("score gates present %s -- calibration removed these (spec 5.4)"
                        % live_gates)

    # 7. ⚠ THE REPORT MUST STILL DESCRIBE THIS RUBRIC. generate_report.py is COMPUTED, not
    # model-written (spec 5.5), so when a rubric moves the reader-facing prose does NOT follow it.
    # That is not theoretical: the 1.22.0 re-anchor of competitive_room left the report telling the
    # reader it measured the operator's margin -- the framing the rewrite existed to remove -- and
    # three more dimensions had drifted the same way, found only because someone read the prose.
    # A drift that can only be caught by reading is a drift that will be missed, so it is a
    # promotion condition: promote the rubric and the report must still agree.
    try:
        import check_report_drift as _drift
        importlib.reload(_drift)
        import io as _io
        from contextlib import redirect_stdout as _ro
        _buf = _io.StringIO()
        with _ro(_buf):
            _rc = _drift.main()
        if _rc != 0:
            problems.append("report drift: the reader-facing definitions no longer describe this "
                            "rubric. Run `python3 check_report_drift.py` for the list." +
                            "".join("\n      " + ln.strip()
                                    for ln in _buf.getvalue().splitlines()
                                    if ln.strip().startswith("-")))
    except Exception as _e:                                        # noqa: BLE001
        # ⚠ LOUD, not silent. A guard that cannot run is not a guard that passed -- and this is
        # exactly the swallow that hid the competitor_scan TypeError earlier in this work.
        problems.append("report drift check could not run (%s: %s) -- fix it rather than "
                        "promoting past it" % (type(_e).__name__, _e))

    if problems:
        print("REFUSING TO PROMOTE %s:" % src_name, file=sys.stderr)
        for p in problems:
            print("  - %s" % p, file=sys.stderr)
        return 1

    before = load(LIVE) if LIVE.exists() else None
    before_v = before["_meta"]["version"] if before else "none"

    # ROLLBACK GUARD. Without this, ANY file is a legal promotion target -- including a retired
    # rubric. Found by triggering it: promoting rubric-v1.8.0.json (ten revisions old, carrying the
    # OLD dimension name) silently replaced the live 1.19.0, and the next corpus run scored 120
    # cases against a retired instrument while reporting success. That is the exact failure 5.3.1
    # exists to prevent, in reverse.
    if (not allow_rollback) and before is not None and \
            vtuple(V["_meta"]["version"]) < vtuple(before_v):
        print("REFUSING TO PROMOTE %s: it would ROLL BACK the live rubric." % src_name,
              file=sys.stderr)
        print("  live     : %s" % before_v, file=sys.stderr)
        print("  candidate: %s" % V["_meta"]["version"], file=sys.stderr)
        print("  A retired rubric must never become the live file. If this is intentional, pass",
              file=sys.stderr)
        print("  --allow-rollback, and say why in the commit.", file=sys.stderr)
        return 1
    if src.resolve() == LIVE.resolve():
        # RECOVERY PATH. The candidate IS the live file -- e.g. after an in-place edit that
        # bypassed this script, or after a stamp was lost. The six checks above have still
        # run, and the stamp written below is what the scorer requires, so validating and
        # stamping in place is the correct repair. Refusing here would leave the live rubric
        # permanently unscorable and push the user back to hand-editing.
        print("  note      : candidate is the live file -- validating and stamping in place")
    else:
        shutil.copyfile(src, LIVE)

    after = load(LIVE)
    if after["_meta"]["version"] != V["_meta"]["version"]:
        print("FATAL: promotion produced a mismatched stamp", file=sys.stderr)
        return 2

    # 5.3.1 step 4 -- stamp the promoted bytes so the SCORER can refuse an unpromoted or
    # post-promotion-modified live rubric. The checks above protect the rubric; the stamp is
    # what protects the report.
    import os
    os.environ["PROMOTED_FROM"] = src_name
    from rubric_gate import write_stamp
    stamp = write_stamp(LIVE)
    print("  stamped   : sha256 %s..." % stamp["sha256"][:16])

    print("PROMOTED  %s -> rubric.json" % src_name)
    print("  version   : %s  ->  %s" % (before_v, after["_meta"]["version"]))
    print("  dimensions: %s" % ", ".join(
        (d if d in after["questions"] else LEGACY[d]) for d in SIX if _has(d, after["questions"])))
    print("  weights   : %s" % after["_meta"]["weights"])
    print("  bands     : %s" % [b[0] for b in after["_meta"]["bands"]])
    print("  gates     : %s (score gates removed by calibration)"
          % ({k: v for k, v in (after["_meta"].get("gates") or {}).items()
              if not k.startswith("_")} or "none"))
    print()
    print("  Both implementations now read the same rubric. Verify with:")
    print("    python3 run_canary.py --rung check --rubric rubric.json")
    return 0


if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else "rubric-v1.8.0.json"
    sys.exit(main(src, allow_rollback="--allow-rollback" in sys.argv[2:]))
