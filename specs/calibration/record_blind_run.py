"""Record a blind human scoring run (D16) for the OBS-SPEC-095 calibration set.

Writes runs/<who>-blind-<case>.json with the raw scores, the computed composite,
and the gate states — computed from the SCORER'S OWN numbers.

Deliberately does NOT read or print answers/EXPECTED-SEALED.md. The comparison
happens later, in a separate step, so a scored run can never be contaminated by
the key it will be compared against.

Usage:
    python3 record_blind_run.py <case> '<json payload>'
    python3 record_blind_run.py --list
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUNS = HERE / "runs"

DIMS = [
    ("headroom", "Market headroom", 15, 2),
    ("pressure", "Competitive pressure", 20, 2),
    ("position", "Position availability", 25, 2),
    ("defensibility", "Defensibility", 25, 2),
    ("demand", "Demand reach", 15, 2),
]

BANDS = [
    ("Fragile", 5, 39),
    ("Contested", 40, 59),
    ("Viable, conditional", 60, 74),
    ("Strong", 75, 95),
]


def band_of(c: int) -> str:
    for name, lo, hi in BANDS:
        if lo <= c <= hi:
            return name
    return "out of range"


def record(case: str, payload: dict) -> dict:
    dims = payload.get("dimensions") or {}
    missing = [k for k, _n, _w, _f in DIMS if k not in dims]
    if missing:
        raise SystemExit(f"missing dimensions: {missing}")

    fires = []
    weighted = 0.0
    for key, _name, wt, floor in DIMS:
        score = dims[key]
        if not isinstance(score, int) or not 1 <= score <= 5:
            raise SystemExit(f"{key}: score must be an int 1-5, got {score!r}")
        if score < floor:
            fires.append(key)
        weighted += score / 5 * wt

    composite = round(weighted)
    gates_pass = not fires

    payload = dict(payload)
    payload["computed"] = {
        "composite": None if fires else composite,
        "band": "GATE" if fires else band_of(composite),
        "gates_firing": fires,
        "note": (
            "no composite shown; a gate fired"
            if fires
            else f"weighted composite on a 5-95 scale, band {band_of(composite)}"
        ),
    }
    payload["scored_at"] = __import__("datetime").datetime.now().isoformat(timespec="seconds")
    payload["key_compared"] = False

    RUNS.mkdir(parents=True, exist_ok=True)
    who = payload.get("scored_by", "unknown")
    out = RUNS / f"{who}-blind-{case}.json"
    out.write_text(json.dumps(payload, indent=2) + "\n")

    # Report the scorer's own arithmetic only. Never the expected answer.
    print(f"recorded -> {out.relative_to(HERE)}")
    print()
    for key, name, wt, floor in DIMS:
        s = dims[key]
        mark = "FIRES" if s < floor else "pass"
        print(f"  {name:24} {s}/5  floor>={floor}  {mark}")
    print()
    print(f"  gates firing : {fires or 'none'}")
    print(f"  composite    : {payload['computed']['composite']}"
          f"   band: {payload['computed']['band']}")
    print(f"  g6 sufficient: {payload.get('g6_input_sufficient')}")
    return payload


def main() -> None:
    if len(sys.argv) == 2 and sys.argv[1] == "--list":
        RUNS.mkdir(parents=True, exist_ok=True)
        for p in sorted(RUNS.glob("*.json")):
            print(p.name)
        return
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    case = sys.argv[1]
    record(case, json.loads(sys.argv[2]))


if __name__ == "__main__":
    main()
