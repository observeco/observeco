"""Extend the composite bands to cover the full 5-100 range.

A composite of 96 was produced (ASML, rubric 0.6.0) and landed 'out of range' because the top
band stopped at 95. The bands were written when every dimension was 5-level and the ceiling
was lower; with defensibility at 6 levels and market_headroom able to reach 5, the arithmetic
ceiling is now 100.
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
p = HERE / "rubric.json"
r = json.loads(p.read_text())
m = r["_meta"]
old = m["bands"]
m["bands"] = [["Fragile", 5, 39], ["Contested", 40, 59],
              ["Viable, conditional", 60, 74], ["Strong", 75, 100]]
m["band_change_note"] = (
    "Top band extended 95 -> 100 in 0.6.0. A composite of 96 was produced and fell outside the "
    "scale. Reason: defensibility now has 6 levels and market_headroom can reach 5, so the "
    "arithmetic maximum is 100, not the ~95 the bands were originally written against. Lower "
    "boundaries are unchanged so every historical composite keeps its band."
)
p.write_text(json.dumps(r, indent=2) + "\n")
print("bands:", old, "->", m["bands"])
print("rubric:", m["version"])
