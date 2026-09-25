"""EXPERIMENT — does market_headroom measure the right thing?

SEAN'S INSIGHT: "when I think about the market headroom for ASML, should there even be a
credible albeit small competitor, it should really open up the space? The problem now is the
market is congested because ASML has the monopoly and can't expand beyond its current capacity"

WHAT THE EVIDENCE SHOWS:
  * ASML produces ~50-60 EUV systems/year. A leading-edge fab needs 10-20. So the world can
    commission only ~3-4 new leading-edge fabs per year.
  * Backlog ~EUR 38.8bn = ~1.5 years of revenue. Most 2027 output already committed.
  * Lead times push fab commissioning 12-24 months beyond announced schedules.
  * "The world cannot build more leading-edge chips than ASML can ship machines to print."
  * Buyers (TSMC, Samsung, Intel) "compete for finite ASML allocation" -> the queue is real.

So: demand MASSIVELY exceeds supply. The market is congested precisely BECAUSE the monopoly
cannot expand capacity. A second supplier would ADD capacity and therefore EXPAND the market.

THE DEFECT: the current question asks "is there room for a new or small ENTRANT to be
chosen?" -- a CROWDING question. For ASML it returns 3 because the market is closed to
entrants. But ASML's market is not short of headroom; it is short of SUPPLY. The dimension
conflates "is this category crowded" with "is there unmet demand".

That also means market_headroom and competitive_room are near-DUPLICATES: one asks "is there
room for an entrant", the other "how much room does competition leave". Neither measures
unmet demand at all.

METHOD: same state, same model, cases chosen. ONLY the headroom question changes.
FALSIFICATION: if the new question does not OPEN the gap between a supply-constrained
monopoly and a demand-served crowded market, the reframe has failed.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from run_jev import call_jev, build_state, read_env_key  # noqa: E402

OLD_Q = {
    "type": "score",
    "instructions": (
        "Judge ONLY market headroom: is there room for a new or small entrant to be chosen in "
        "this category at all? Ignore how good this particular business is, ignore its brand, "
        "and ignore how differentiated it is. Consider whether the category the business names "
        "is a real category a buyer would recognise, whether it is growing or shrinking, and "
        "whether new entrants do get chosen in it. A category can be large and still be a trap "
        "if the label is contested or the buyer does not shop that way."),
    "criteria": [
        "No headroom. The category named is a trap - contested, or an artefact of how the business describes itself - and there is no identifiable category in which a buyer could choose them.",
        "Very little. The category is real but shrinking, or so broad the business cannot be placed within it.",
        "Moderate. A real category with real buyers, but flat, or structurally unfavourable to new entrants.",
        "Good. A real, growing category in which new entrants do visibly get chosen.",
        "Strong. A large, growing category with documented, growing demand and plenty of room for new entrants.",
    ],
}

NEW_Q = {
    "type": "score",
    "instructions": (
        "Judge ONLY market headroom: is there more DEMAND in this category than is currently "
        "being SERVED? Judge whether buyers are getting what they need, or whether demand is "
        "going unmet - people waiting, being rationed, turned away, going without, or paying "
        "inflated prices because supply cannot keep up. Do NOT judge how crowded the category "
        "is, and do NOT judge whether a new entrant would be welcomed; those are separate "
        "questions. A category served by a single supplier who cannot expand fast enough to "
        "meet orders is NOT a trap - it is under-supplied, and unmet demand is headroom. "
        "Equally, a large category where supply already meets demand has little headroom, "
        "however big it is, because any new entrant must take share from someone."),
    "criteria": [
        "No demand. There is no identifiable buying demand for this category at all.",
        "Demand is served. Buyers can get this easily; supply meets or exceeds what is wanted, and the category is flat or shrinking.",
        "Demand is met, contested. Real, steady demand, but supply already satisfies it - a new entrant must take share from an incumbent rather than serve unmet need.",
        "Demand exceeds supply. Buyers wait, are rationed, or pay inflated prices because supply cannot keep up, and the shortfall is growing.",
        "Demand far exceeds supply. The category cannot serve the demand that exists; buyers are allocated, queued or going without, and the constraint is the binding limit on the whole market.",
    ],
}

CASES = [
    # file, label, what we expect the NEW question to reveal
    ("inputs/E1-asml.json", "SUPPLY-CONSTRAINED", "~1.5yr backlog, rationed allocation -> HIGH"),
    ("inputs/08-bubbletea.json", "CROWDED, DEMAND SERVED", "62+ brands, supply abundant -> LOW-MID"),
    ("inputs/C9-b2b-it-services.json", "CROWDED, DEMAND SERVED", "6+ undifferentiated rivals -> LOW-MID"),
    ("inputs/N1-closedbusiness.json", "NO DEMAND", "dead business -> LOW"),
]


def ask(path: Path, q: dict, model: str) -> dict:
    payload = json.loads(path.read_text())
    state = build_state(payload)
    res = call_jev(state, {"headroom": q}, model)
    if not res:
        raise SystemExit(f"call failed: {path.name}")
    a = (res.get("answers") or {}).get("headroom") or {}
    return {"score": a.get("score"), "conf": a.get("confidence"),
            "dist": a.get("probabilities")}


def main() -> int:
    if not read_env_key("TYPESAFE_API_KEY"):
        return 2
    rows = []
    for rel, label, expect in CASES:
        p = HERE / rel
        old = ask(p, OLD_Q, "jev-latest")
        new = ask(p, NEW_Q, "jev-latest")
        rows.append((p.stem, label, expect, old, new))
        print(f"  {p.stem:26} old={old['score']}  new={new['score']}")

    print()
    print("DOES THE REFRAME MEASURE UNMET DEMAND INSTEAD OF CROWDING?")
    print("=" * 100)
    print(f"{'case':26}{'label':24}{'OLD':>7}{'NEW':>7}   expectation")
    print("-" * 100)
    for name, label, expect, old, new in rows:
        print(f"{name:26}{label:24}{old['score']:>7}{new['score']:>7}   {expect}")

    by = {n: (o, w) for n, _l, _e, o, w in rows}
    print()
    print("FALSIFICATION TEST — separation between supply-constrained and demand-served")
    print("-" * 100)
    if "E1-asml" in by:
        a_o, a_n = by["E1-asml"]
        crowded = [v[1]["score"] for k, v in by.items()
                   if k != "E1-asml" and v[1]["score"] is not None]
        o_crowded = [v[0]["score"] for k, v in by.items()
                     if k != "E1-asml" and v[0]["score"] is not None]
        print(f"  ASML          old {a_o['score']}  -> new {a_n['score']}")
        print(f"  others        old {o_crowded}  -> new {crowded}")
        if a_n["score"] is not None and crowded:
            gap_new = a_n["score"] - max(crowded)
            gap_old = (a_o["score"] or 0) - max(o_crowded) if o_crowded else 0
            print(f"  gap (ASML - best other):  old {gap_old:+.2f}  new {gap_new:+.2f}")
            print("  verdict:", "PASS — reframe opens the gap" if gap_new > gap_old
                  else "FAIL — reframe does not separate")

    print()
    print("DISTRIBUTIONS")
    print("-" * 100)
    for name, _l, _e, old, new in rows:
        print(f"  {name:26} old {old['dist']}")
        print(f"  {'':26} new {new['dist']}")

    (HERE / "runs" / "experiment-headroom-reframe.json").write_text(
        json.dumps([{"case": n, "label": l, "old": o, "new": w}
                    for n, l, _e, o, w in rows], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
