#!/usr/bin/env python3
"""Generate the two report versions from a Jev run JSON.

VERSION A — SCORE. The numbers, gates, bands. Machine-precise, no prose.
VERSION B — READ.  The same judgments expressed as a short evidenced read.

Both are built from the run artifact, so neither can drift from the other.
Prose that matters (the verdict, the one gate) is selected by CODE from computed
predicates, never written by a model (spec 5.5).

Usage: python3 generate_report.py observeco
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

BANDS = [("Fragile", 5, 39), ("Contested", 40, 59),
         ("Viable, conditional", 60, 74), ("Strong", 75, 95)]

CONF_ACT = 0.50   # below this, a dimension is not shown as a trusted number
CONF_FLAG = 0.30  # below this, the dimension is materially unresolved

LABEL = {
    "market_headroom": "Market headroom",
    "competitive_room": "Competitive room",
    "position_availability": "Position availability",
    "defensibility": "Defensibility",
    "demand_reach": "Demand reach",
}

WEIGHT = {"market_headroom": 15, "competitive_room": 20,
          "position_availability": 25, "defensibility": 25, "demand_reach": 15}

FLOOR = {k: 2 for k in WEIGHT}

# Verdict sentence, selected by predicate. No model writes this.
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
    "position_availability": "whether the claim you make is one your competitors "
                             "already make",
    "defensibility": "whether what makes you different survives a competitor "
                     "deciding to copy it",
    "demand_reach": "whether the customer you've described can actually be found "
                    "and will pay your price",
}


def bar(score: int, conf: float | None) -> str:
    filled = "#" * score + "." * (5 - score)
    if conf is None:
        return f"[{filled}]   ?"
    if conf < CONF_FLAG:
        return f"[{filled}]   {score}/5  UNRESOLVED (conf {conf:.2f})"
    if conf < CONF_ACT:
        return f"[{filled}]   {score}/5  low confidence ({conf:.2f})"
    return f"[{filled}]   {score}/5  (conf {conf:.2f})"


def weakest(run: dict) -> str:
    """The dimension contributing least, weighted. Deterministic argmin."""
    dims = run["dimensions_display_1to5"]
    return min(WEIGHT, key=lambda k: (dims[k] / 5 * WEIGHT[k], k))


def version_a(run: dict) -> str:
    d = run["dimensions_display_1to5"]
    c = run["confidence"]
    out = []
    out.append("OBSERVECO — POSITIONING SCORECARD")
    out.append("=" * 46)
    out.append("")
    if run["gates_firing"]:
        out.append("  NO COMPOSITE — a gate fired")
        out.append(f"  Gates firing: {', '.join(run['gates_firing'])}")
    else:
        out.append(f"  {run['composite']}/100    {run['band'].upper()}")
    out.append("")
    for k in WEIGHT:
        out.append(f"  {LABEL[k]:24}{bar(d[k], c[k])}")
    out.append("")
    out.append(f"  Input sufficiency : {run['input_sufficiency']}")
    out.append(f"  Model             : {run['model_id']}")
    out.append(f"  Rubric            : {run['rubric_version']}")
    return "\n".join(out)


def version_b(run: dict) -> str:
    d = run["dimensions_display_1to5"]
    c = run["confidence"]
    band = run["band"]
    gate = weakest(run)
    unresolved = [k for k in WEIGHT if c[k] < CONF_FLAG]
    out = []
    out.append("OBSERVECO — YOUR POSITIONING READ")
    out.append("=" * 46)
    out.append("")
    out.append("THE SHORT VERSION")
    out.append("")
    if band == "GATE":
        out.append(f"  {VERDICT['GATE']}")
    else:
        out.append(f"  {run['composite']}/100 — {band}.")
        out.append(f"  {VERDICT[band]}")
    out.append("")
    out.append("WHAT THE SCORES SAY")
    out.append("")
    for k in WEIGHT:
        note = ""
        if c[k] < CONF_FLAG:
            note = "  <- we could not settle this one"
        elif c[k] < CONF_ACT:
            note = "  <- low confidence"
        out.append(f"  {LABEL[k]:24}{d[k]}/5{note}")
    out.append("")
    out.append("THE ONE THING THAT DECIDES IT")
    out.append("")
    out.append(f"  {GATE_TEXT[gate].capitalize()}.")
    out.append("")
    out.append("WHAT WE DID NOT CHECK")
    out.append("")
    out.append("  We read your website and scored what it claims. We did NOT cross-check")
    out.append("  your competitors' claims against public registries, verify their pricing,")
    out.append("  or map who owns which word in your category. That is the paid analysis.")
    if unresolved:
        out.append(f"  We also could not settle: {', '.join(LABEL[k] for k in unresolved)}.")
    out.append("")
    out.append("WHY THIS IS FREE")
    out.append("")
    out.append("  It is generated by AI and reviewed by no one. It is a read on your")
    out.append("  claim, not an analysis of your market. The paid engagement is the second")
    out.append("  thing — and a person owns every answer in it.")
    return "\n".join(out)


def main() -> None:
    case = sys.argv[1] if len(sys.argv) > 1 else "observeco"
    run = json.loads((HERE / "runs" / f"jev-{case}.json").read_text())
    a = version_a(run)
    b = version_b(run)
    print(a)
    print()
    print()
    print(b)
    outdir = HERE / "reports"
    outdir.mkdir(exist_ok=True)
    (outdir / f"{case}-VERSION-A-score.txt").write_text(a + "\n")
    (outdir / f"{case}-VERSION-B-read.txt").write_text(b + "\n")


if __name__ == "__main__":
    main()
