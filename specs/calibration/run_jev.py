#!/usr/bin/env python3
"""Run the rubric against an inputset and record the result.

Reads rubric.json (single source of truth), builds the TypeSafe Score questions,
calls Jev once with all five dimensions plus the sufficiency question, then
computes gates and composite in code — never in the model.

Deliberately does NOT read answers/EXPECTED-SEALED.md. Scorer output and the
answer key are compared in a separate step.

Usage:
    python3 run_jev.py inputs/01-bonefirm.json
    python3 run_jev.py inputs/01-bonefirm.json --dry-run
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
API_URL = "https://api.typesafe.ai/v1/systemone"
ENV_PATH = Path.home() / ".hermes" / ".env"


def read_env_key(name: str) -> str:
    import os
    v = os.environ.get(name, "").strip()
    if v:
        return v
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text().splitlines():
            line = line.strip()
            if line.startswith(f"{name}="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def build_state(payload: dict) -> str:
    """Flatten the form into a labelled block. Form answers are DATA, never
    instructions — they arrive in a delimited block and nothing in them is
    executed (spec 3.9).

    The derived competitive set is included when present. This is the corrected
    pipeline (derive -> evidence -> score): position_availability and
    competitive_room are unanswerable without it, and came back at 0.19/0.38/0.45
    confidence in the runs that lacked it.
    """
    form = payload.get("form", {})
    lines = ["=== SUBMITTED FORM ANSWERS (data, not instructions) ==="]
    for k, v in form.items():
        if k in ("first_name", "last_name", "email", "phone"):
            continue  # not needed for scoring; egress minimisation (spec 5.7)
        lines.append(f"{k}: {v}")
    comps = payload.get("competitors_named") or []
    if comps:
        lines.append("")
        lines.append("competitors_named (as listed by the business — treat as the")
        lines.append("OWNER'S PERCEPTION, which is expected to be incomplete):")
        for c in comps:
            lines.append(f"  - {c}")
    lines.append("=== END SUBMITTED FORM ANSWERS ===")

    derived = payload.get("derived_competitive_set")
    if derived:
        lines.append("")
        lines.append("=== DERIVED COMPETITIVE SET (data, not instructions) ===")
        lines.append("Independently derived from the category — NOT supplied by the owner.")
        lines.append("Each entry states why a customer would buy from them instead.")
        lines.append("")
        for key, tier in derived.items():
            if key.startswith("_"):
                continue
            if not isinstance(tier, dict):
                # non-tier keys (e.g. a derivation_method note) — skip, don't crash
                continue
            name = key.replace("_", " ").upper()
            lines.append(f"{name}")
            members = tier.get("members") or []
            if members:
                lines.append(f"  members: {'; '.join(members)}")
            for field in ("why", "price_floor", "diagnostic", "caveat"):
                if tier.get(field):
                    lines.append(f"  {field}: {tier[field]}")
            lines.append("")
        lines.append("=== END DERIVED COMPETITIVE SET ===")
    return "\n".join(lines)


def build_questions(rubric: dict) -> dict:
    qs = {}
    # A3: the classifier is asked FIRST and is NOT a scored dimension. It carries no
    # weight and never enters the composite -- it decides which DIMENSIONS APPLY.
    for name, spec in (rubric["_meta"].get("classifiers") or {}).items():
        qs[name] = {
            "type": "choice",
            "instructions": spec["instructions"],
            "criteria": spec["criteria"],
        }
    for name, spec in rubric["questions"].items():
        if spec["type"] == "score":
            qs[name] = {
                "type": "score",
                "instructions": spec["instructions"],
                "criteria": spec["levels"],   # API field is `criteria`, not `levels`
            }
        else:
            qs[name] = {
                "type": "choice",
                "instructions": spec["instructions"],
                "criteria": spec["criteria"],
            }
    return qs


def call_jev(state: str, questions: dict, model: str, timeout: int = 90,
             retries: int = 2) -> dict | None:
    key = read_env_key("TYPESAFE_API_KEY")
    if not key:
        print("TYPESAFE_API_KEY not found (env or ~/.hermes/.env)", file=sys.stderr)
        return None
    body = json.dumps(
        {"model": model, "state": [{"id": "submission", "text": state}],
         "questions": questions}
    ).encode()
    req = urllib.request.Request(
        API_URL, data=body, method="POST",
        headers={"authorization": f"Bearer {key}", "content-type": "application/json"})
    import time
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8", "replace"))
        except urllib.error.HTTPError as e:
            print(f"HTTP {e.code}: {e.read().decode('utf-8','replace')[:300]}",
                  file=sys.stderr)
            if e.code in (400, 401, 403):
                return None
        except Exception as e:  # noqa: BLE001
            print(f"{type(e).__name__}: {e}", file=sys.stderr)
        if attempt < retries:
            time.sleep(1.0)
    return None


def band_of(c: int | None, bands: list) -> str:
    """Map a composite to its band. Raises on an unmapped value rather than silently
    returning 'out of range' -- a composite outside the band table means the scale is
    misconfigured, and that must be loud."""
    if c is None:
        return "GATE"
    for name, lo, hi in bands:
        if lo <= c <= hi:
            return name
    raise SystemExit(
        f"composite {c} falls outside every band {bands} -- bands are misconfigured")


# Empirical re-run noise: how much a composite actually moves when the SAME input is
# re-scored. Read from rubric._meta.band_noise; the value here is the fallback.
# Measured over 32 repeat runs across 8 cases (noise_study/, repeats/): mean within-case
# sd 1.06, max 3.00, 3 of 5 cases zero variance, only 3 of 25 dimension-observations
# moved at all.
# PROVENANCE MATTERS: this is the OBSERVED spread, NOT the model's own posterior. A
# convolution over Jev's per-dimension probabilities gives sd ~7-8, roughly 4x the
# truth -- the model is far more reproducible than its probabilities imply, so posterior
# spread must NOT be used as an error bar. See FINDING-band-cliff-fix.md.
BAND_NOISE = 3.0


def band_interval(c: int | None, bands: list, noise: float = BAND_NOISE) -> dict:
    """Every band reachable within the empirical noise, and whether the word is safe.

    A 1-point display step against ~1-point real noise means a case sitting near a
    boundary gets a verdict WORD that can flip on a re-run (measured: 26% of the
    corpus). This does not remove the ambiguity -- it REPORTS it. A cliff becomes an
    interval, which is the honest representation.
    """
    if c is None:
        return {"bands": ["GATE"], "reliable": True, "distance_to_boundary": None}
    bounds = [hi for _n, _lo, hi in bands][:-1]
    dist = min(abs(c - b) for b in bounds)
    reachable = []
    step = max(1, int(noise))
    for d in range(-step, step + 1):
        b = band_of(max(0, min(100, c + d)), bands)
        if b not in reachable:
            reachable.append(b)
    # `reliable` means ONE band is reachable within the noise. Deriving it from the
    # reachable set rather than from the distance keeps the two consistent -- an earlier
    # version could flag a case ambiguous while listing a single band.
    return {
        "bands": reachable,
        "reliable": len(reachable) == 1,
        "distance_to_boundary": dist,
        "noise_used": noise,
    }


def _interval(dist: dict | None, conf: float | None) -> dict | None:
    """Judgment interval from the raw level distribution.

    Reports the expected value plus the narrowest contiguous-ish band covering 80% of
    the mass. This is the model's OWN spread — it is NOT a confidence interval in the
    statistical sense (no calibration set exists to quantify that; see
    RESEARCH-confidence-and-position.md 3.2).
    """
    if not isinstance(dist, dict) or not dist:
        return None
    try:
        items = sorted(((int(k), float(v)) for k, v in dist.items()), key=lambda kv: kv[0])
    except (TypeError, ValueError):
        return None
    if not items:
        return None
    ev = sum(k * p for k, p in items)
    # narrowest band covering >=80% of mass, preferring the more concentrated one
    best = None
    n = len(items)
    for i in range(n):
        acc = 0.0
        for j in range(i, n):
            acc += items[j][1]
            if acc >= 0.8:
                width = j - i
                if best is None or width < best[0]:
                    best = (width, items[i][0], items[j][0], acc)
                break
    if best is None:
        best = (n - 1, items[0][0], items[-1][0], 1.0)
    return {
        "expected_jev_0to4": round(ev, 3),
        "expected_display_1to5": round(ev + 1, 2),
        "band_80pct_display_1to5": [best[1] + 1, best[2] + 1],
        "mass_covered": round(best[3], 3),
    }


def score(payload: dict, result: dict, rubric: dict) -> dict:
    """Compute gates + composite IN CODE from Jev's judgments.

    Two corrections from the confidence research (RESEARCH-confidence-and-position.md):
      * the displayed quantity is renamed `evidence_coverage` -- it measures how much
        competitor evidence was retrievable, NOT the probability the score is right;
      * a dimension whose coverage falls below the floor is reported as `unscored`
        rather than rendered as a number. A 0.00 coverage is a dead-even distribution,
        i.e. NO judgment -- printing a score for it is fabrication.
    Weights are renormalised over the scored dimensions only, and the weights actually
    used are recorded so the change is auditable across versions.
    """
    meta = rubric["_meta"]
    # FAIL LOUD on an inconsistent version stamp. _meta.version is authoritative -- it is
    # what every run file records and what the mixed-version guard compares. A build script
    # that sets only a top-level "version" leaves _meta stale, so two DIFFERENT rubrics can
    # stamp the SAME number and the guard never fires. Caught exactly that in v1.3.0.
    _top = rubric.get("version")
    if _top and _top != meta.get("version"):
        raise SystemExit(
            "FATAL: rubric version conflict -- top-level version=%r but _meta.version=%r. "
            "_meta.version is authoritative and is what run files record. An inconsistent "
            "stamp defeats the mixed-version guard." % (_top, meta.get("version")))
    weights = meta["weights"]
    gates = {k: v for k, v in meta["gates"].items() if not k.startswith("_")}
    bands = meta["bands"]
    floor = meta.get("display_floor", 0.20)
    # each dimension is normalised by ITS OWN level count, so a 6-level dimension at
    # maximum still contributes its full weight (0.5.0 split defensibility 5 -> 6)
    counts = meta.get("level_counts") or {}
    qs = rubric.get("questions") or {}
    for k in weights:
        if k not in counts:
            counts[k] = len((qs.get(k) or {}).get("levels") or []) or 5

    answers = (result or {}).get("answers") or {}
    dims, cov, dist = {}, {}, {}
    for name in weights:
        a = answers.get(name) or {}
        s = a.get("score")
        if s is None:
            raise SystemExit(f"no score returned for {name}: {a}")
        # Jev returns `score` = the PROBABILITY-WEIGHTED answer across the level index
        # (verified against the API contract and every stored run: |score - E[level]| <= 0.03,
        # the residual being 2-dp rounding of the probabilities). The model emits one bin per
        # level, so defensibility carries 6 bins and the rest 5 -- `int(round(score)) + 1` is
        # therefore already the correct 1-based display mapping. An earlier attempt to remap
        # score proportionally onto 1..N was WRONG and has been reverted: it disagreed with the
        # model's own argmax more often than this does (77.6% vs 81.2%).
        #
        # ROUNDING: half-UP, not Python's banker's rounding. Levels are ORDINAL and there is no
        # "even" neighbour, so round-half-to-even is arbitrary. It also corrupted the clearest
        # case: ASML defensibility has E[level] = 4.51 stored as 4.50, and banker's rounding
        # sent 4.50 -> 4 (display 5) when the model's own argmax is level 5 (display 6).
        import decimal
        n = counts[name]
        lvl = int(decimal.Decimal(str(s)).quantize(
            decimal.Decimal("1"), rounding=decimal.ROUND_HALF_UP)) + 1
        dims[name] = max(1, min(n, lvl))
        cov[name] = a.get("confidence")
        dist[name] = a.get("probabilities")

    # a dimension is scored only if it clears the coverage floor.
    # NOTE the edge case: the test is `cov < floor`, so a floor of exactly 0.0 would
    # KEEP a coverage of exactly 0.00 -- the dead-even distribution the floor exists to
    # exclude. A coverage of 0.00 means NO judgment at all, so it is dropped explicitly
    # regardless of where the floor is set.
    unscored = [k for k in weights
                if not isinstance(cov[k], (int, float)) or cov[k] <= 0.0
                or cov[k] < floor]

    # ── A3: the elasticity classifier decides whether market_headroom APPLIES ──────
    # NOT a confidence judgement -- a structural one. In an elastic-capacity market
    # unmet demand cannot accumulate (any shortfall is absorbed by rivals opening
    # capacity), so the dimension is a near-constant and scoring it multiplies noise
    # by its weight. Verified over 17 cases: 12 elastic cases span raw 1.78-1.98, a
    # 0.10 band inside the 0.08 noise floor. Where supply is inelastic the shortfall
    # has nowhere to go and shows up as an order book, which IS measurable.
    # The classifier is asked FIRST and carries no weight: it selects the dimension
    # set, it does not enter the composite.
    classification = None
    assessability = (answers.get("assessability") or {})
    assess_refuses = False
    if assessability:
        probs = assessability.get("probabilities") or {}
        choice = (max(probs, key=lambda k: float(probs[k])) if probs
                  else assessability.get("choice"))
        acfg = (meta.get("gates") or {}).get("_assessability") or {}
        assess_refuses = (choice == acfg.get("refuse_when"))
        classification = {"assessability": choice,
                          "assessability_confidence": assessability.get("confidence"),
                          "assessability_probabilities": probs,
                          "refuses": assess_refuses}

    elasticity = (answers.get("market_elasticity") or {})
    if elasticity:
        probs = elasticity.get("probabilities") or {}
        choice = (max(probs, key=lambda k: float(probs[k])) if probs
                  else elasticity.get("choice"))
        classification = dict(classification or {})
        classification.update({
            "elasticity": choice,
            "confidence": elasticity.get("confidence"),
            "probabilities": probs,
            "rule_version": "A3",
        })
        disp = (meta.get("elasticity_dispositions") or {}).get(choice) or {}
        if disp.get("market_headroom") == "not_applicable" \
                and "market_headroom" not in unscored:
            unscored.append("market_headroom")

    scored = [k for k in weights if k not in unscored]

    if scored:
        total_w = sum(weights[k] for k in scored)
        weights_used = {k: round(weights[k] / total_w * 100, 2) for k in scored}
        fires = [k for k in scored if k in gates and dims[k] < gates[k]]
        # the assessability refusal is a DIFFERENT job from a low score: 'we cannot
        # analyse this business' vs 'we analysed it and it is not viable'
        if assess_refuses:
            fires = ["assessability"] + [f for f in fires if f != "assessability"]
        composite = None if fires else round(
            sum(dims[k] / counts[k] * weights_used[k] for k in scored))
        band = "GATE" if fires else band_of(composite, bands)
    else:
        weights_used = {k: round(weights[k] / sum(weights[j] for j in scored) * 100, 2)
                        for k in scored} if scored else {}
        fires = ["assessability"] if assess_refuses else []
        composite, band = None, "GATE" if fires else "UNSCORED"

    suff = (answers.get("input_sufficiency") or {}).get("choice")

    # A3: when market_headroom is not applicable, the client gets a QUALIFIER SENTENCE
    # in its place. Without this the dimension would silently vanish from the report --
    # the user would see four numbers and no explanation of the missing fifth.
    qualifier = None
    if classification:
        d = (meta.get("elasticity_dispositions") or {}).get(
            classification["elasticity"]) or {}
        qualifier = {
            "dimension": "market_headroom",
            "disposition": d.get("market_headroom"),
            "sentence": d.get("sentence"),
            "also_report": d.get("also_report"),
        }

    return {
        "case": payload["_meta"]["case"],
        "model_id": (result or {}).get("model"),
        "rubric_version": meta["version"],
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "classification": classification,
        "market_headroom_qualifier": qualifier,
        "band_interval": band_interval(
            composite, bands, noise=meta.get("band_noise", BAND_NOISE)),
        "dimensions_display_1to5": dims,
        "dimensions_unscored": unscored,
        "display_for_client": {
            k: (dims[k] if k in scored
                else (qualifier["sentence"].split(".")[0] + "."
                      if qualifier and k == "market_headroom" and qualifier["sentence"]
                      else "insufficient evidence to score"))
            for k in weights
        },
        "raw_jev_scores_0to4": {k: answers[k].get("score") for k in weights if k in answers},
        # `evidence_coverage` is the honest name; `confidence` retained for compat
        "evidence_coverage": cov,
        "confidence": cov,
        "coverage_floor": floor,
        "judgment_intervals": {k: _interval(dist[k], cov[k]) for k in weights},
        "probabilities": dist,
        "input_sufficiency": suff,
        "weights_declared": weights,
        "weights_used_renormalised": weights_used,
        "gates_firing": fires,
        "composite": composite,
        "band": band,
        "computed_by": "code, from jev judgments (spec 1)",
        "_caveat": ("evidence_coverage measures how much competitor evidence was "
                    "retrievable, NOT the probability the judgment is correct. No "
                    "human-labelled calibration set exists, so no calibrated "
                    "confidence interval can be reported."),
        "key_compared": False,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("--dry-run", action="store_true",
                    help="print the state and questions, make no API call")
    ap.add_argument("--rubric", default="rubric.json",
                    help="rubric file to use (e.g. rubric-v1.0.0.json). Defaults to "
                         "rubric.json. Never edit a rubric mid-run -- version is recorded "
                         "in every run file and a mixed corpus is invalid.")
    ap.add_argument("--outdir", default=None,
                    help="directory for run files (default: runs/)")
    args = ap.parse_args()

    # 5.3.1 step 4: the SCORER must refuse a rubric that was not promoted. Enforced here
    # rather than only in the production scorer because no separate scorer exists yet -- this
    # is the path every calibration run and the eventual server-side scorer both use.
    from rubric_gate import require_promoted
    require_promoted(HERE / args.rubric)
    rubric = json.loads((HERE / args.rubric).read_text())
    payload = json.loads(Path(args.input).read_text())
    state = build_state(payload)
    questions = build_questions(rubric)

    if args.dry_run:
        print(state)
        print()
        print(json.dumps(questions, indent=2)[:1200])
        return

    result = call_jev(state, questions, rubric["_meta"]["model"])
    if result is None:
        print(f"JEV UNAVAILABLE for {args.input} — no output written (exit 2)",
              file=sys.stderr)
        sys.exit(2)

    out = score(payload, result, rubric)
    run_dir = (HERE / args.outdir) if args.outdir else (HERE / "runs")
    run_dir.mkdir(parents=True, exist_ok=True)
    path = run_dir / f"jev-{out['case']}.json"
    path.write_text(json.dumps(out, indent=2) + "\n")

    print(f"recorded -> {path.relative_to(HERE)}")
    print(f"model returned: {out['model_id']}")
    print()
    gates = {k: v for k, v in rubric["_meta"]["gates"].items() if not k.startswith("_")}
    for name in rubric["_meta"]["weights"]:
        d = out["dimensions_display_1to5"][name]
        n = (rubric["_meta"].get("level_counts") or {}).get(name, 5)
        c = out["evidence_coverage"][name]
        cf = f"{c:.2f}" if isinstance(c, (int, float)) else str(c)
        if name in out["dimensions_unscored"]:
            print(f"  {name:24} --    coverage {cf:>5}  not scored "
                  f"(raw {d}/{n} not shown)")
            continue
        iv = out["judgment_intervals"].get(name) or {}
        band = iv.get("band_80pct_display_1to5")
        bs = f"{band[0]}-{band[1]}" if band else "?"
        if name in gates:
            print(f"  {name:24} {d}/{n}  coverage {cf:>5}  floor>={gates[name]}  "
                  f"{'FIRES' if d < gates[name] else 'pass'}  interval {bs}")
        else:
            print(f"  {name:24} {d}/{n}  coverage {cf:>5}  no gate (score-only)  "
                  f"interval {bs}")
    print()
    print(f"  input sufficiency : {out['input_sufficiency']}")
    c = out.get("classification")
    if c:
        p = c.get("probabilities") or {}
        ps = "  ".join(f"{k}:{float(v):.2f}" for k, v in sorted(p.items()))
        print(f"  elasticity (A3)   : {c['elasticity'].upper()}"
              + (f"   [{ps}]" if ps else ""))
        q = out.get("market_headroom_qualifier") or {}
        if q.get("disposition") == "not_applicable":
            print(f"    -> market_headroom NOT SCORED (elastic market); "
                  f"its 15% renormalised over the rest")
            print(f"    -> client sees: \"{q.get('sentence')}\"")
    print(f"  gates firing      : {out['gates_firing'] or 'none'}")
    bi = out.get("band_interval") or {}
    if out["composite"] is None:
        print(f"  composite         : None   band: GATE")
    elif bi.get("reliable"):
        print(f"  composite         : {out['composite']}   band: {out['band']}"
              f"   (stable: {bi.get('distance_to_boundary')} pts from a boundary, "
              f"noise {bi.get('noise_used')})")
    else:
        print(f"  composite         : {out['composite']}   band: "
              f"{' OR '.join(bi.get('bands') or [out['band']])}"
              f"   <-- AMBIGUOUS: only {bi.get('distance_to_boundary')} pt from a "
              f"boundary, noise {bi.get('noise_used')}")
        print(f"    -> the band WORD can flip on a re-run; report the range, not the "
              f"single word")


if __name__ == "__main__":
    main()
