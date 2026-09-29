#!/usr/bin/env python3
"""generate_report.py — spec 095: render the client report from a Jev run artifact.

THIS IS THE PRODUCTION REPORT PATH. It replaces an earlier version that could not
represent half the composite.

WHY IT WAS REWRITTEN (three defects in the previous version, all found by inspecting it)
  1. STALE DIMENSION KEY. It keyed the 25%-weight dimension `position_availability`,
     a name the rubric stopped emitting when it became `position_strength` and then
     `position_strength`. The artifact carries `position_strength`, so `c[k]` raised
     KeyError and the script CRASHED.
  2. WRONG WEIGHTS. Its hardcoded WEIGHT table disagreed with the rubric's own
     `_meta.weights` on four of five dimensions (it said market_headroom 15,
     competitive_room 20, defensibility 25, demand_reach 15). The rubric says 10/15/20/10.
     It would have mis-stated the score even if it had not crashed.
  3. SILENTLY DROPPED A DIMENSION. It rendered five dimensions from a hardcoded list
     while the live rubric scores SIX. `mental_advantage` (20% of the composite) and
     `position_strength` (25%) were absent from every report it produced.

THE RULES THIS VERSION FOLLOWS
  - Weights come from the ARTIFACT, falling back to the rubric — never hardcoded.
    A report that disagrees with the instrument it reports on is worse than no report.
  - A dimension the instrument did NOT score (dimensions_unscored) is never rendered as
    a number. It shows the artifact's own qualifier sentence. A bare "N/A" is not
    acceptable (Sean: empty states need an actionable sentence).
  - The verdict sentence and THE ONE THING are COMPUTED predicates, not written by a
    model (spec 5.5). Identical submissions must produce byte-identical reports.
  - THE ONE THING is an argmin over weighted contribution, tie-broken by confidence,
    then by dimension order (spec 5.5). Unscored dimensions cannot be the gate.
  - Artifacts that still say `position_availability` or `position_strength` are ACCEPTED
    via alias, so frozen runs stay readable.
  - An artifact missing a dimension it claims to have is REFUSED, not rendered short.

Usage:
    python3 generate_report.py --run runs-v1190a/jev-BK01-breadtalk.json
    python3 generate_report.py --case breadtalk            # looks in ./runs/
    python3 generate_report.py --run <file> --check        # verify only
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent

BANDS = [("Fragile", 5, 39), ("Contested", 40, 59),
         ("Viable, conditional", 60, 74), ("Strong", 75, 95)]

CONF_ACT = 0.50   # below this, a dimension is not shown as a trusted number
CONF_FLAG = 0.30  # below this, the dimension is materially unresolved

# Aliases: names this dimension has carried. Frozen artifacts stay readable.
ALIAS = {
    "position_availability": "position_strength",
    "relative_strength": "position_strength",
}

LABEL = {
    "market_headroom": "Market headroom",
    "competitive_room": "Competitive room",
    "position_strength": "Position strength",
    "mental_advantage": "Mental advantage",
    "defensibility": "Defensibility",
    "demand_reach": "Demand reach",
}

# Verdict sentence, selected by predicate. No model writes this (spec 5.5).
VERDICT = {
    "GATE": "There is a hard blocker in the way before the position itself matters.",
    "Fragile": "The position is unlikely to hold as things stand.",
    "Contested": "This is winnable, but not on the current plan.",
    "Viable, conditional": "The position can hold, subject to the one check named below.",
    "Strong": "The position is available and defensible.",
}

# The gate sentence: which dimension is doing the most damage, named concretely.
GATE_TEXT = {
    "market_headroom": "whether the category you've named is the one your buyer "
                       "actually shops in",
    "competitive_room": "whether there is any margin left after the price floor "
                        "your competitors set",
    "position_strength": "whether the claim you make is one your competitors "
                         "already make",
    "mental_advantage": "whether anyone thinks of you when they need what you sell",
    "defensibility": "whether what makes you different survives a competitor "
                     "deciding to copy it",
    "demand_reach": "whether the customer you've described can actually be found "
                    "and will pay your price",
}


def norm(name: str) -> str:
    return ALIAS.get(name, name)


def load_rubric(path: Path | None) -> dict:
    """Level counts per dimension come from the rubric, never from a constant."""
    p = path or (HERE / "rubric.json")
    if not p.exists():
        return {}
    return json.loads(p.read_text())


def level_counts(rubric: dict, dims: dict) -> dict:
    counts = {}
    q = rubric.get("questions", {})
    for k in dims:
        block = q.get(k) or q.get(norm(k)) or {}
        n = len(block.get("levels", [])) if isinstance(block, dict) else 0
        counts[k] = n or 5
    return counts


def normalise(run: dict) -> dict:
    """Map alias keys onto canonical keys. Returns a new run dict."""
    out = dict(run)
    for field in ("dimensions_display_1to5", "confidence", "probabilities",
                  "display_for_client", "judgment_intervals"):
        src = run.get(field) or {}
        out[field] = {norm(k): v for k, v in src.items()}
    out["weights_declared"] = {norm(k): v
                               for k, v in (run.get("weights_declared") or {}).items()}
    out["weights_used_renormalised"] = {
        norm(k): v for k, v in (run.get("weights_used_renormalised") or {}).items()}
    out["dimensions_unscored"] = [norm(k) for k in (run.get("dimensions_unscored") or [])]
    return out


def bar(score: float, conf: float | None) -> str:
    n = int(round(score))
    filled = "#" * n + "." * (5 - n)
    if conf is None:
        return f"[{filled}]   ?"
    if conf < CONF_FLAG:
        return f"[{filled}]   {n}/5  UNRESOLVED (conf {conf:.2f})"
    if conf < CONF_ACT:
        return f"[{filled}]   {n}/5  low confidence ({conf:.2f})"
    return f"[{filled}]   {n}/5  (conf {conf:.2f})"


def gate_dimension(run: dict, counts: dict, weights: dict) -> str:
    """Spec 5.5: argmin over weighted contribution, tie-broken by confidence,
    then by dimension order. Unscored dimensions cannot be the gate — the
    instrument did not judge them."""
    dims = run["dimensions_display_1to5"]
    conf = run["confidence"]
    unscored = set(run.get("dimensions_unscored") or [])

    def contrib(k: str) -> float:
        return dims[k] / counts.get(k, 5) * weights.get(k, 0)

    cands = [k for k in weights if k not in unscored and dims.get(k) is not None]
    if not cands:
        return "market_headroom"
    lo = min(contrib(k) for k in cands)
    tied = [k for k in cands if abs(contrib(k) - lo) < 1e-9]
    if len(tied) > 1:
        tied.sort(key=lambda k: (conf.get(k, 1.0), k))   # lower confidence first
    return tied[0]


def version_a(run: dict, counts: dict, weights: dict) -> str:
    dims = run["dimensions_display_1to5"]
    conf = run["confidence"]
    shown = run.get("display_for_client") or {}
    unscored = set(run.get("dimensions_unscored") or [])
    out = []
    out.append("OBSERVECO — POSITIONING SCORECARD")
    out.append("=" * 52)
    out.append("")
    if run.get("gates_firing"):
        out.append("  NO COMPOSITE — a refusal fired")
        out.append(f"  Refusals: {', '.join(run['gates_firing'])}")
        out.append("")
        out.append("  A refusal means we cannot answer this, NOT that the answer")
        out.append("  is bad. Nothing here says your business is weak.")
    else:
        out.append(f"  {run['composite']}/100    {str(run['band']).upper()}")
        bi = run.get("band_interval") or {}
        if bi.get("bands"):
            rel = "reliable" if bi.get("reliable") else "unreliable — near a boundary"
            out.append(f"  Band interval: {bi['bands'][0]}  ({rel}, "
                       f"{bi.get('distance_to_boundary')} from the boundary)")
    out.append("")
    out.append("  DIMENSION            SCORE")
    out.append("  " + "-" * 50)
    for k in weights:
        if k in unscored:
            # NEVER a bare N/A. Use the artifact's own actionable sentence.
            txt = shown.get(k) or "insufficient evidence to score"
            out.append(f"  {LABEL.get(k, k):20}—")
            out.append(f"      {txt}")
        elif dims.get(k) is None:
            out.append(f"  {LABEL.get(k, k):20}not scored")
        else:
            out.append(f"  {LABEL.get(k, k):20}{bar(dims[k], conf.get(k))}")
    out.append("")
    out.append(f"  Input sufficiency : {run.get('input_sufficiency')}")
    out.append("  Weights used      : "
               + ", ".join(f"{str(LABEL.get(k, k))} {v:g}%"
                           for k, v in weights.items()))
    out.append(f"  Model             : {run.get('model_id')}")
    out.append(f"  Rubric            : {run.get('rubric_version')}")
    out.append(f"  Generated         : {run.get('generated_at')}")
    return "\n".join(out)


def version_b(run: dict, counts: dict, weights: dict) -> str:
    dims = run["dimensions_display_1to5"]
    conf = run["confidence"]
    band = run.get("band")
    gate = gate_dimension(run, counts, weights)
    unscored = set(run.get("dimensions_unscored") or [])
    unresolved = [k for k in weights
                  if k not in unscored and conf.get(k) is not None
                  and conf[k] < CONF_FLAG]
    out = []
    out.append("OBSERVECO — YOUR POSITIONING READ")
    out.append("=" * 52)
    out.append("")
    out.append("THE SHORT VERSION")
    out.append("")
    if run.get("gates_firing"):
        out.append("  We could not produce a score for this submission.")
        out.append("  That is a limit on what you told us, not a verdict on the")
        out.append("  business. Reply with more detail and we will run it again.")
    else:
        out.append(f"  {run['composite']}/100 — {band}.")
        out.append(f"  {VERDICT.get(band, VERDICT['Contested'])}")
    out.append("")
    out.append("WHAT THE SCORES SAY")
    out.append("")
    for k in weights:
        if k in unscored:
            out.append(f"  {LABEL.get(k, k):20}we could not score this one")
        elif dims.get(k) is None:
            out.append(f"  {LABEL.get(k, k):20}not scored")
        else:
            note = ""
            if conf.get(k) is not None and conf[k] < CONF_FLAG:
                note = "  <- we could not settle this one"
            elif conf.get(k) is not None and conf[k] < CONF_ACT:
                note = "  <- low confidence"
            out.append(f"  {LABEL.get(k, k):20}{dims[k]}/5{note}")
    out.append("")
    if not run.get("gates_firing"):
        out.append("THE ONE THING THAT DECIDES IT")
        out.append("")
        out.append(f"  {GATE_TEXT.get(gate, '').capitalize()}.")
        out.append("")
    out.append("WHAT WE DID NOT CHECK")
    out.append("")
    out.append("  We scored what your submission claims. We did NOT cross-check your")
    out.append("  competitors' claims against public registries, verify their pricing,")
    out.append("  or map who owns which word in your category. That is the paid")
    out.append("  analysis.")
    if unresolved:
        out.append("  We also could not settle: "
                   + ", ".join(str(LABEL.get(k, k)) for k in unresolved) + ".")
    out.append("")
    out.append("WHY THIS IS FREE")
    out.append("")
    out.append("  It is generated by AI and reviewed by no one. It is a read on your")
    out.append("  claim, not an analysis of your market. The paid engagement is the")
    out.append("  second thing — and a person owns every answer in it.")
    return "\n".join(out)


def render(run: dict, rubric_path: Path | None) -> tuple[str, str]:
    r = normalise(run)
    rubric = load_rubric(rubric_path)
    dims = r.get("dimensions_display_1to5") or {}
    weights = r.get("weights_declared") or rubric.get("_meta", {}).get("weights") or {}
    if not weights:
        raise SystemExit("REFUSED: no weights in the artifact and no rubric to read.")
    counts = level_counts(rubric, dims)
    # A dimension the artifact claims to carry but does not is a REFUSAL, not a
    # short report. Silent omission is the defect this rewrite exists to remove.
    unscored = set(r.get("dimensions_unscored") or [])
    missing = [k for k in weights if k not in dims and k not in unscored]
    if missing:
        raise SystemExit(
            f"REFUSED: artifact is missing dimensions {missing}. Refusing to render a "
            "report that silently omits part of the composite.")
    return version_a(r, counts, weights), version_b(r, counts, weights)


def main() -> None:
    ap = argparse.ArgumentParser(description="render the client report from a run")
    ap.add_argument("case", nargs="?", help="case name; looks in ./runs/jev-<case>.json")
    ap.add_argument("--run", help="path to the run artifact JSON")
    ap.add_argument("--rubric", default=None, help="rubric JSON for level counts")
    ap.add_argument("--outdir", default=None)
    ap.add_argument("--check", action="store_true",
                    help="render and verify; do not write files")
    args = ap.parse_args()

    if args.run:
        runpath = Path(args.run)
    elif args.case:
        runpath = HERE / "runs" / f"jev-{args.case}.json"
    else:
        raise SystemExit("give a case name or --run <file>")
    if not runpath.exists():
        raise SystemExit(f"no such run artifact: {runpath}")

    run = json.loads(runpath.read_text())
    a, b = render(run, Path(args.rubric) if args.rubric else None)

    if args.check:
        print(f"OK  {runpath.name} -> rendered {len(a)} + {len(b)} chars")
        return

    print(a)
    print()
    print()
    print(b)
    outdir = Path(args.outdir) if args.outdir else HERE / "reports"
    outdir.mkdir(parents=True, exist_ok=True)
    stem = runpath.stem.replace("jev-", "")
    (outdir / f"{stem}-VERSION-A-score.txt").write_text(a + "\n")
    (outdir / f"{stem}-VERSION-B-read.txt").write_text(b + "\n")


if __name__ == "__main__":
    main()
