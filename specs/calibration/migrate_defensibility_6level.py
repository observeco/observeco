"""Migrate defensibility from a 5-level to a 6-level scale by SPLITTING level 3.

Sean: "a well-protected single formulation should not score the same as something copyable
in months."

Old level 3 conflated two different situations:
  (a) genuine development required, NO protection barrier -- a competitor who commits the
      resources gets there in months. Nothing stops them but their own effort.
  (b) genuine development required AND a barrier obstructs it beyond the work itself --
      a trade secret that cannot be reverse-engineered, a patent that blocks, an undisclosed
      ratio/process, a supply arrangement they cannot obtain.

The E4 test showed adding substantial IP to Bonefirm did NOT move the score (3 -> 3) and
only raised certainty (0.71 -> 0.97), because L3's text literally names "a formulation, a
process, or a technical system". IP was already inside L3. Split it.

MAPPING (old -> new), so no existing judgment changes meaning:
  1 No moat          -> 1 No moat
  2 Shallow          -> 2 Shallow
  3 Real but replicable -> SPLITS into 3 Replicable  and  4 Protected
  4 Durable          -> 5 Durable
  5 Compounding      -> 6 Compounding

Gate floors stay at 2: the BOTTOM of the scale is unchanged, so a floor of 2 still means
"not 'no moat'". Only defensibility gains a level; the other four dimensions stay 5-level,
and each dimension is normalised by ITS OWN level count so a dimension at maximum still
contributes its full weight.
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
p = HERE / "rubric.json"
r = json.loads(p.read_text())
m = r["_meta"]

d = r["questions"]["defensibility"]

d["instructions"] = (
    "Judge ONLY defensibility: how long would it take a well-resourced competitor to copy what "
    "makes this business different, and is there a barrier obstructing them beyond the work "
    "itself? Judge TIME-TO-COPY and OBSTRUCTION, not the type of advantage, and not how much "
    "work the founder did to get there -- effort already spent does not make something "
    "defensible. Consider each claimed differentiator and ask two separate questions. First, "
    "can a competitor buy the same input and relabel it, or must they do real development work "
    "of their own? Second, if they must do the work, is anything stopping them beyond the "
    "effort -- protection that holds, an undisclosed process or ratio, a supply arrangement "
    "they cannot obtain? A differentiator that requires genuine development but is fully "
    "visible and unprotected is REPLICABLE: a committed competitor will get there in months. "
    "The same development work WITH a barrier that obstructs copying is PROTECTED, and that is "
    "materially stronger even though the underlying asset is similar. A differentiator resting "
    "on accumulated trust, an owned channel, a proprietary dataset, or years of relationship "
    "cannot be bought or quickly rebuilt at all."
)

d["levels"] = [
    "No moat. There is no differentiator at all, or the one claimed is a purchasable input any competitor can relabel this quarter.",
    "Shallow. A competitor can copy it in weeks without doing any development of their own -- a claim, a message, or an off-the-shelf ingredient.",
    "Replicable. A competitor must do genuine development work of their own -- a formulation, a process, or a technical system -- so copying takes them months, not weeks. But nothing obstructs them beyond the effort: the approach is visible, known, or inferable, and a committed competitor will get there.",
    "Protected. The same genuine development work is required, AND a barrier obstructs copying beyond the effort itself -- a trade secret that cannot be reverse-engineered, a patent that blocks, an undisclosed process, ratio or sequence, or a supply arrangement a competitor cannot obtain. Copying is not merely expensive; it is obstructed, unlawful, or unavailable.",
    "Durable. Copying takes a competitor a year or more, or requires assets they do not have -- accumulated trust, an owned distribution channel, a proprietary dataset, or years of relationship.",
    "Compounding. Several advantages that reinforce each other, where a well-funded competitor could not replicate the position even given the time.",
]

m["version"] = "0.5.0"
m["level_counts"] = {k: len(v["levels"]) for k, v in r["questions"].items()
                     if isinstance(v, dict) and v.get("type") == "score"}
m["normalisation_note"] = (
    "Composite = sum(display / level_count * weight) over scored dimensions, weights "
    "renormalised across scored dimensions only. Each dimension is normalised by ITS OWN "
    "level count, so a dimension at maximum contributes its full weight regardless of how "
    "many levels it has. Defensibility is 6-level (0.5.0); the other four remain 5-level."
)
m["gate_note"] = (
    "Floors stay at display 2. The 0.5.0 split inserted a level ABOVE the old level 3, so the "
    "BOTTOM of the scale is unchanged and a floor of 2 still means 'not no-moat'."
)
m["bands_note"] = (
    "Bands were calibrated on the 5-level composite. Rescaling to a 6-level defensibility "
    "moves the low boundary by <1 point, so bands are kept unchanged to preserve comparability "
    "with every prior composite. Re-calibrate only after the ladder is re-run and reviewed."
)

m["dimension_change_log"].append({
    "version": "0.5.0",
    "change": "defensibility SPLIT from 5 to 6 levels (old L3 -> new L3 'Replicable' + new L4 'Protected')",
    "reason": (
        "Sean: 'a well-protected single formulation should not score the same as something "
        "copyable in months.' Confirmed by E4-bonefirm-ip: adding explicit trade-secret, "
        "undisclosed-process and non-reverse-engineerable disclosure to Bonefirm left the score "
        "at 3 and raised confidence 0.71 -> 0.97, because old L3's text already named 'a "
        "formulation, a process, or a technical system' -- IP was inside L3 by construction. "
        "The distinction Sean wants is real and was not expressible on the old scale."
    ),
    "evidence": "FINDING-defensibility-ceiling.md; E1 ASML 5/5, E2 Coupang 5/5, E4 vs bonefirm",
})

p.write_text(json.dumps(r, indent=2) + "\n")

print("rubric ->", m["version"])
print("level counts:", json.dumps(m["level_counts"]))
print()
print("DEFENSIBILITY, 6 levels:")
for i, l in enumerate(d["levels"]):
    print(f"  {i+1}) {l[:118]}{'...' if len(l) > 118 else ''}")
print()
print("weights:", json.dumps(m["weights"]))
print("gates  :", json.dumps({k: v for k, v in m["gates"].items() if not k.startswith('_')}))
