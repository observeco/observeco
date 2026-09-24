"""Compare the three views of Bonefirm: Jev, Sean (blind), and the sealed key.

Produces the divergence table. Does NOT adjudicate — that is a hand-read.

Usage: python3 compare.py bonefirm
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DIMS = ["market_headroom", "competitive_room", "position_availability",
        "defensibility", "demand_reach"]
# The blind-run widget used SHORT keys; the rubric and Jev run use LONG keys.
# Mismatched keys here would silently produce a None and, in production, would
# mean the human baseline and the scorer were never compared at all.
ALIAS = {
    "headroom": "market_headroom",
    "pressure": "competitive_room",
    "position": "position_availability",
    "defensibility": "defensibility",
    "demand": "demand_reach",
}
BANDS = [("Fragile", 5, 39), ("Contested", 40, 59),
         ("Viable, conditional", 60, 74), ("Strong", 75, 95)]


def band_of(c):
    for n, lo, hi in BANDS:
        if lo <= c <= hi:
            return n
    return "GATE"


def load_key(case: str) -> dict:
    """Parse the sealed key for one case. Kept dumb and explicit — the key is
    prose, so this reads the dimension table by regex and the composite line."""
    txt = (HERE / "answers" / "EXPECTED-SEALED.md").read_text()
    # split on the case headings
    blocks = re.split(r"\n### \d\d — ", txt)
    want = {"bonefirm": "Bonefirm", "greenpackers": "GreenPackers",
            "petdirectory": "PetDirectory", "caica": "CaiCa",
            "sgfitness": "SG Fitness venture", "saladshop": "SaladShop venture"}
    target = want[case]
    blk = next(b for b in blocks[1:] if b.split("\n")[0].strip() == target)
    dims = {}
    for m in re.finditer(r"\| ([A-Z][a-z ]+) \| \*\*(\d)\*\* \|", blk):
        name = m.group(1).strip().lower()
        key = {"market headroom": "market_headroom",
               "competitive pressure": "competitive_room",
               "position availability": "position_availability",
               "defensibility": "defensibility",
               "demand reach": "demand_reach"}.get(name)
        if key:
            dims[key] = int(m.group(2))
    cm = re.search(r"\*\*Composite: (\d+) → ([^*]+)\*\*", blk)
    gate = re.search(r"\*\*G(\d) FIRES\*\*", blk)
    return {"dimensions": dims,
            "composite": int(cm.group(1)) if cm else None,
            "band": cm.group(2).strip() if cm else ("GATE" if gate else None),
            "gate_fires": bool(gate)}


def main() -> None:
    case = sys.argv[1] if len(sys.argv) > 1 else "bonefirm"
    jev = json.loads((HERE / "runs" / f"jev-{case}.json").read_text())
    human = json.loads((HERE / "runs" / f"sean-blind-{case}.json").read_text())
    key = load_key(case)

    hd = {ALIAS.get(k, k): v for k, v in human["dimensions"].items()}
    unmapped = set(hd) - set(DIMS)
    if unmapped:
        raise SystemExit(f"human run has unmapped dimension keys: {unmapped}")

    for d in DIMS:
        if d not in hd:
            raise SystemExit(f"human run is missing {d} — refusing to print a "
                             f"comparison with a hole in it")

    print(f"BONEFIRM — three views\n")
    print(f"  model      : {jev['model_id']}  rubric {jev['rubric_version']}")
    print(f"  sufficiency: jev={jev['input_sufficiency']}  "
          f"sean={human.get('g6_input_sufficient')}")
    print()
    print(f"  {'dimension':24}{'jev':>12}{'conf':>7}{'sean':>7}{'key':>6}"
          f"{'jev-sean':>10}{'jev-key':>9}")
    for d in DIMS:
        j = jev["dimensions_display_1to5"][d]
        c = jev["confidence"][d]
        s = hd.get(d)
        k = key["dimensions"].get(d)
        print(f"  {d:24}{j:>12}{c:>7.2f}{s:>7}{k:>6}"
              f"{j - s:>10}{j - k:>9}")
    print()
    print(f"  {'':24}{'composite':>12}{'band':>22}")
    print(f"  {'jev':24}{jev['composite']:>12}{jev['band']:>22}")
    print(f"  {'sean':24}{human['computed']['composite']:>12}"
          f"{human['computed']['band']:>22}")
    print(f"  {'key':24}{key['composite']:>12}{key['band']:>22}")
    print()
    band_match = jev["band"] == key["band"]
    print(f"  jev band == key band : {band_match}")
    human_match = human["computed"]["band"] == key["band"]
    print(f"  sean band == key band: {human_match}")
    print()
    print("  jev's lowest-confidence dimension:",
          min(DIMS, key=lambda d: jev["confidence"][d]),
          f"({min(jev['confidence'].values()):.2f})")


if __name__ == "__main__":
    main()
