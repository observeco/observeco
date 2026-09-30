"""run_negative_controls.py — spec 095 section 10.6: the negative-control gate, built.

WHAT THIS PROVES
    Spec 8.6: "a scorer that cannot fail is not a scorer." Section 10.6's launch gate has one open
    row -- "Every control FAILS, each with its own predicted failure reason". Five controls, each
    isolating a distinct failure mode, each with its expectation recorded in the fixture BEFORE the
    run. A post-hoc explanation is not evidence.

WHY MORE THAN ONE CONTROL
    Section 3.10 item 4: "One negative control proves the scorer CAN fail -- not that it fails for
    the right reason." Several controls are needed, spanning distinct failure modes. So each fixture
    carries its OWN `predicted_failure`, and this harness checks the control against THAT, not
    against a blanket "score is low".

WHAT COUNTS AS PASSING
    A control PASSES when the failure its fixture predicted actually occurs.
    A control FAILS when it does not -- and THAT is a finding about the instrument, not about the
    control. In particular:
      * a control that returns a normal scored report when its input was empty means the scorer
        fabricated a judgement from nothing;
      * a fluent-but-empty control scoring >= 3 on position_strength means the instrument is reading
        FLUENCY instead of position -- the very defect that produced the PS/MA duplication.

USAGE
    python3 run_negative_controls.py [--rubric rubric.json] [--outdir nc-runs]
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
NC_DIR = HERE / "negative-controls"


def run_case(path, rubric, outdir):
    r = subprocess.run([sys.executable, str(HERE / "run_jev.py"), str(path),
                        "--rubric", rubric, "--outdir", outdir],
                       capture_output=True, text=True, cwd=HERE)
    # ⚠⚠ EXIT 3 IS NOT A BROKEN RUN — IT IS THE GATE FIRING, WHICH IS WHAT THE CONTROL WANTS.
    # `preflight_gate.py` documents it explicitly: "sys.exit(3)  # guidance, not failure". A
    # submission that fails the pre-flight gate never reaches scoring, so there is no run
    # artifact -- and the harness treated any non-zero return as COULD NOT RUN.
    #
    # Measured: NC01-empty was reported as "RUN FAILED: PRE-FLIGHT REFUSED ... missing required
    # slots: positioning, category" -- i.e. the control's PREDICTED failure being counted as the
    # harness being unable to measure it. NC01 predicts "input_sufficiency = insufficient"; the
    # gate refused it before sufficiency could even be asked. Refusing at the door IS the
    # predicted failure mode for an empty submission.
    #
    # ⚠ THE GENERAL FORM, AND WHY THIS IS WORTH FIXING RATHER THAN DOCUMENTING: a harness that
    # counts a CORRECT refusal as a measurement failure will report failure exactly when the
    # instrument behaves properly -- so the gate can never be green, and a real regression
    # becomes indistinguishable from this known noise. That is the same class as the stale
    # rubric default in run_canary.py (6.7.7): the gate failing for a reason unrelated to what
    # it tests.
    if r.returncode == 3:
        return {"__preflight_refused__": True,
                "refused": True, "band": None,
                "input_sufficiency": {"answer": "insufficient"},
                "refusal_text": (r.stderr or r.stdout)[-400:]}, ""
    if r.returncode != 0:
        return None, (r.stderr or r.stdout)[-400:]
    for p in sorted((HERE / outdir).glob("jev-*.json")):
        d = json.loads(p.read_text())
        if d.get("case") == json.loads(Path(path).read_text())["_meta"]["case"]:
            return d, ""
    return None, "no run file produced"


def evaluate(fixture, out):
    """Check the control against ITS OWN predicted failure. Returns (passed, reason)."""
    meta = fixture["_meta"]
    predicted = meta.get("predicted_failure", "")
    dims = out.get("dimensions_display_1to5") or {}
    suff = out.get("input_sufficiency") or {}
    suff_verdict = suff.get("answer") if isinstance(suff, dict) else suff
    insufficient = str(suff_verdict).lower().startswith("insufficient")
    refused = bool(out.get("refused")) or out.get("band") is None

    # Control 1 -- empty input: must refuse, or at minimum flag insufficiency
    if "input_sufficiency" in predicted and "insufficient" in predicted and "OR" not in predicted:
        ok = insufficient or refused
        if ok and out.get("__preflight_refused__"):
            # ⚠ SAY WHICH DOOR IT FAILED AT. "insufficient" and "refused before sufficiency was
            # asked" are different mechanisms; collapsing them would hide that the gate stopped
            # this submission earlier than the control's text anticipated.
            return True, ("REFUSED AT THE PRE-FLIGHT GATE — the empty submission never reached "
                          "scoring, which is the predicted outcome")
        return ok, ("refused/insufficient as predicted" if ok else
                    "SCORED AN EMPTY SUBMISSION (sufficiency=%r, band=%r)"
                    % (suff_verdict, out.get("band")))

    # Control 2 -- contradictory: either insufficient, or competitive_room bottoms out
    if "OR" in predicted:
        cr = dims.get("competitive_room")
        ok = insufficient or refused or (cr is not None and cr <= 1)
        if not ok:
            return False, ("NEITHER fired: sufficiency=%r competitive_room=%s band=%r"
                           % (suff_verdict, cr, out.get("band")))
        # ⚠ NAME THE BRANCH THAT ACTUALLY FIRED. The old line printed the competitive_room value
        # unconditionally -- "insufficient/refused, or competitive_room=3" -- so a PASS reported
        # a number (3) that does NOT satisfy the predicted <= 1, and a reader cannot tell which
        # of the two conditions carried it. Measured on NC02: it passed on the refusal branch
        # while printing competitive_room=3, which reads as a contradiction.
        if refused or insufficient:
            return True, ("REFUSED (sufficiency=%r, band=%r) — the refusal branch fired; "
                          "competitive_room=%s did not need to." % (suff_verdict,
                                                                    out.get("band"), cr))
        return True, "competitive_room=%s satisfied the <= 1 branch" % cr

    # Control 3 -- generic filler: must not score mid on position_strength or mental_advantage
    if "position_strength <= 2" in predicted and "mental_advantage" in predicted:
        ps, ma = dims.get("position_strength"), dims.get("mental_advantage")
        ok = (ps is not None and ps <= 2)
        return ok, ("position_strength=%s (mental_advantage=%s)" % (ps, ma) if ok else
                    "FLUENCY READ AS POSITION: position_strength=%s, mental_advantage=%s" % (ps, ma))

    # Control 4 -- owned claim: position_strength must be low
    if "position_strength <= 2" in predicted:
        ps = dims.get("position_strength")
        ok = ps is not None and ps <= 2
        return ok, ("position_strength=%s" % ps if ok else
                    "OWNS NOTHING YET SCORED %s -- an occupied flank read as available" % ps)

    # Control 5 -- asserted but unevidenced: capped at 3
    if "position_strength <= 3" in predicted:
        ps = dims.get("position_strength")
        ok = ps is not None and ps <= 3
        return ok, ("position_strength=%s (capped as predicted)" % ps if ok else
                    "UNEVIDENCED ASSERTION SCORED %s -- adjectives bought a flank" % ps)

    return False, "no usable prediction in the fixture"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rubric", default="rubric.json")
    ap.add_argument("--outdir", default="nc-runs")
    args = ap.parse_args()

    fixtures = sorted(NC_DIR.glob("NC*.json"))
    if not fixtures:
        print("FATAL: no negative controls found in %s" % NC_DIR, file=sys.stderr)
        return 2

    print("=" * 96)
    print("NEGATIVE CONTROLS — every control MUST fail, for the reason recorded before the run")
    print("  rubric: %s   controls: %d" % (args.rubric, len(fixtures)))
    print("=" * 96)

    passed, failed = [], []
    for fp in fixtures:
        fx = json.loads(fp.read_text())
        cid = fx["_meta"]["case"]
        out, err = run_case(fp, args.rubric, args.outdir)
        if out is None:
            failed.append((cid, "RUN FAILED: %s" % err))
            print("\n  %-20s COULD NOT RUN — %s" % (cid, err[:160]))
            continue
        ok, reason = evaluate(fx, out)
        (passed if ok else failed).append((cid, reason))
        print("\n  %-20s %s" % (cid, "PASS" if ok else "FAIL"))
        print("      predicted : %s" % fx["_meta"]["predicted_failure"][:150])
        print("      observed  : %s" % reason[:150])
        print("      band      : %s   composite: %s" %
              (out.get("band"), out.get("composite")))

    print("\n" + "=" * 96)
    print("  %d of %d controls failed as predicted." % (len(passed), len(fixtures)))
    if failed:
        print("\n  ⚠ CONTROLS THAT DID NOT FAIL AS PREDICTED — each is a finding about the INSTRUMENT,")
        print("    not about the control:")
        for cid, reason in failed:
            print("    - %-20s %s" % (cid, reason[:170]))
    print("=" * 96)
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
