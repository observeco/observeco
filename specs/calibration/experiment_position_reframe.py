"""EXPERIMENT — does reframing position_availability as RELATIVE fix the inversion?

Method: hold the state constant, vary ONLY the question. This isolates the rubric
change from everything else.

Falsification criteria (recorded in RESEARCH-confidence-and-position.md BEFORE this ran):
  F1. If KOI and CaiCa score within 1 level of each other -> R1 FAILED, cut the dimension.
  F2. If every strong case scores the same level (no monotonic spread) -> it measures SIZE,
      not advantage.

Same Jev model, same state text, two runs:
  OLD: position_availability  — "is the position still OPEN?"        (absolute)
  NEW: mental_advantage       — "does it over-index vs expectation?" (relative)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from run_jev import (  # noqa: E402
    call_jev, build_state, API_URL, read_env_key,
)


def load_rubric() -> dict:
    return json.loads((HERE / "rubric.json").read_text())


# ---------------------------------------------------------------- the two questions

OLD_Q = {
    "type": "score",
    "instructions": (
        "Judge ONLY position availability: is the position the business wants to occupy "
        "still OPEN, or does someone already own it? Higher means more open. Assess whether "
        "the word or idea the business claims is already owned by a named competitor in the "
        "buyer's mind, and whether the claim is one that competitors could trivially copy or "
        "already share. A claim that several competitors also make is NOT an available "
        "position. Consider what the business actually claims, as stated."
    ),
    "criteria": [
        "Taken and defended. The claimed position is clearly owned by an established competitor.",
        "Mostly taken. The claim is shared by several competitors, or copyable in a season.",
        "Partly open. The claim is not owned outright, but it is not exclusively theirs either.",
        "Open. The position is genuinely unoccupied, with only weak or incidental overlap.",
        "Wide open. The position is clearly unoccupied and the incumbents are not even oriented toward it.",
    ],
}

NEW_Q = {
    "type": "score",
    "instructions": (
        "Judge ONLY mental advantage: does this business over-index on buying situations "
        "RELATIVE TO WHAT A BUSINESS OF ITS SIZE WOULD BE EXPECTED TO OWN? This is a "
        "RELATIVE measure, never absolute. First establish the buying situations (the "
        "occasions, needs and contexts that make a buyer enter this category). Then, for "
        "each, ask whether this business is linked to it MORE STRONGLY than a business of "
        "its size and market position would predict, or LESS STRONGLY. A large, well-known "
        "player holding its situation is NOT a low score: holding a situation against "
        "expected erosion is an advantage. Equally, a tiny player owning one situation "
        "disproportionately to its size is a STRONG advantage. Judge the excess over "
        "expectation, not the raw prominence of the brand."
    ),
    "criteria": [
        "Over-index nowhere. Compared with what a business of this size would be expected to own, it is linked to no buying situation beyond bare presence. It has no situation it is retrieved for.",
        "Over-indexes nowhere but is present. It appears in the category but owns no situation more strongly than its size alone would predict.",
        "At expectation. Linked to its buying situations at roughly the level its size predicts; neither advantaged nor disadvantaged.",
        "Over-indexes on one or more situations. It is retrieved in specific buying situations more strongly than a business of its size would predict.",
        "Strongly over-indexes. It is the first retrieval for one or more valuable, frequently-occurring buying situations, beyond what its size predicts; rivals are not close on those situations.",
    ],
}

CASES = [
    # case file, ground-truth label, description
    ("inputs/09-koi.json",     "LEADER",  "market leader: ~20% share, 88 outlets, 20 yrs"),
    ("inputs/08-bubbletea.json", "FAILING", "CaiCa: 6 outlets -> 3, brand not recalled"),
    ("inputs/C5-michelin-hawker.json", "STRONG*", "Michelin star every yr since 2016, 1 stall"),
    ("inputs/N1-closedbusiness.json", "DEAD", "closed business"),
]


def run(path: Path, question: dict, model: str, rubric: dict) -> dict:
    payload = json.loads(path.read_text())
    state = build_state(payload)          # identical state for both questions
    res = call_jev(state, {"focus": question}, model)
    if not res:
        raise SystemExit(f"call failed for {path.name}")
    a = (res.get("answers") or {}).get("focus") or {}
    return {"score": a.get("score"), "conf": a.get("confidence"),
            "dist": a.get("distribution") or a.get("probabilities"), "raw": res}


def main() -> int:
    rubric = load_rubric()
    model = rubric["_meta"]["model"]
    if not read_env_key("TYPESAFE_API_KEY"):
        print("TYPESAFE_API_KEY missing", file=sys.stderr)
        return 2

    rows = []
    for rel, truth, desc in CASES:
        p = HERE / rel
        if not p.exists():
            print(f"  SKIP (no file): {rel}")
            continue
        old = run(p, OLD_Q, model, rubric)
        new = run(p, NEW_Q, model, rubric)
        rows.append((p.stem, truth, desc, old, new))
        print(f"  {p.stem:26} old={old['score']} new={new['score']}")

    print()
    print("DOES THE RELATIVE FRAMING FIX IT?")
    print("=" * 96)
    print(f"{'case':26}{'truth':10}{'OLD (absolute)':>18}{'NEW (relative)':>18}   desc")
    print("-" * 96)
    for name, truth, desc, old, new in rows:
        o = f"{old['score']}/5" if old["score"] is not None else "n/a"
        n = f"{new['score']}/5" if new["score"] is not None else "n/a"
        print(f"{name:26}{truth:10}{o:>18}{n:>18}   {desc}")

    # F1 — KOI vs CaiCa separation
    by = {n: (t, o, w) for n, t, _d, o, w in rows}
    print()
    print("FALSIFICATION TEST F1 — leader vs failing must separate")
    print("-" * 96)
    if "09-koi" in by and "08-bubbletea" in by:
        _t, koi_o, koi_n = by["09-koi"]
        _t2, cc_o, cc_n = by["08-bubbletea"]
        d_old = (koi_o["score"] or 0) - (cc_o["score"] or 0)
        d_new = (koi_n["score"] or 0) - (cc_n["score"] or 0)
        print(f"  OLD: KOI {koi_o['score']:.2f} vs CaiCa {cc_o['score']:.2f}   gap {d_old:+.2f}")
        print(f"  NEW: KOI {koi_n['score']:.2f} vs CaiCa {cc_n['score']:.2f}   gap {d_new:+.2f}")
        verdict = ("PASS — separated" if d_new >= 1.0
                   else "FAIL — still within 1 level, dimension should be CUT")
        print(f"  verdict: {verdict}")

    print()
    print("DISTRIBUTIONS (does the new framing also widen the raw spread?)")
    print("-" * 96)
    for name, truth, _d, old, new in rows:
        print(f"  {name:26} {truth:10} old dist={old['dist']}  new dist={new['dist']}")

    (HERE / "runs" / "experiment-position-reframe.json").write_text(
        json.dumps([{"case": n, "truth": t, "desc": d,
                     "old": {"score": o["score"], "dist": o["dist"]},
                     "new": {"score": w["score"], "dist": w["dist"]}}
                    for n, t, d, o, w in rows], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
