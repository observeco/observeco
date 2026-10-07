"""The rubric-vs-report drift guard (spec 5.5).

WHY THIS EXISTS. generate_report.py is COMPUTED, not model-written -- there is no second model call,
so the reader-facing prose cannot follow the rubric automatically. When the rubric moves, the
definitions stay put. That is not hypothetical: the 1.22.0 rewrite re-anchored competitive_room to
the market's STRUCTURE, while the report went on telling the reader it measured the operator's
margin -- the exact framing the rewrite existed to remove. Three more dimensions had drifted the
same way and were found only because someone happened to read the prose.

A drift that can only be caught by reading is a drift that will be missed. So this asserts it.

HOW IT WORKS -- mechanical, not clever. For each dimension it requires the reader-facing definition
to actually share vocabulary with the rubric that scores it. A definition written against an older
rubric shares no distinctive term with the current one. It also carries explicit exclusion checks
for the framings the rubric names as forbidden, because those are the failures that matter most.

Exit 0 = no drift. Exit 1 = drift, printed as a list. Run it before promoting a rubric version.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUBRIC = HERE / "rubric.json"


def _flat(s: str) -> str:
    return " ".join((s or "").split())


def reader_definitions() -> dict[str, str]:
    """The submitter-facing definitions, read OUT of the module rather than duplicated here.

    Duplicating them would be its own drift: the guard would pass while the report said something
    else. Importing the real object is the only version that cannot go stale.
    """
    sys.path.insert(0, str(HERE))
    import generate_report as gr
    return {k: _flat(v) for k, v in gr.DIM_MEANING.items()}


def content_words(text: str) -> set[str]:
    stop = {"the", "a", "an", "of", "to", "in", "is", "it", "and", "or", "for", "you", "your",
            "that", "this", "as", "by", "not", "do", "how", "what", "which", "with", "its",
            "be", "are", "from", "than", "would", "can", "if", "at", "on", "so", "no"}
    return {w for w in re.findall(r"[a-z]{4,}", (text or "").lower()) if w not in stop}


# ⚠ EXPLICIT EXCLUSIONS. The rubric names framings it does NOT score. If the reader-facing prose
# uses one, the report is describing a different measurement from the one being made -- which is
# worse than a vague definition, because it is confidently wrong.
#
# ⚠⚠ AND THE CHECK MUST READ NEGATION -- FOUND BY RUNNING IT. The first version fired on the CORRECT
# definition, because the fixed wording says "not by the difference you claim": a disclaimer that
# NAMES the forbidden framing in order to exclude it. A guard that fails on correct code is a guard
# that gets switched off, which is worse than no guard. So a match is discarded when it sits inside
# a negation.
FORBIDDEN = {
    "competitive_room": [
        (r"margin is left for you",
         "the 1.22.0 rewrite moved this to the market's STRUCTURE; 'margin for you' is the "
         "small-operator framing the rewrite removed"),
        (r"size of the business", "the rubric says judge the structure, not the business scored"),
    ],
    "defensibility": [
        (r"makes you different|you claim|stated differentiator",
         "the rubric says the mechanism is NEVER the business's stated differentiator"),
    ],
    "market_headroom": [
        (r"growing|shrinking",
         "the rubric measures UNMET vs SERVED demand, not the category's growth trend"),
    ],
    "mental_advantage": [
        (r"uncontested|exclusive|dominant",
         "mental advantage is not a competitive measure; magnitude, not exclusivity"),
    ],
    "position_strength": [
        (r"well.?known|famous|fame",
         "position strength must not score how well known the business is"),
    ],
}

# a forbidden framing is FINE when the sentence disclaims it. These are the tell-tales.
NEGATION = re.compile(
    r"\b(not|never|no|nothing|rather than|instead of|rather than by|other than|excluding)\b",
    re.I)


def uses_forbidden(definition: str, pat: str) -> re.Match | None:
    """Return the first NON-NEGATED match of `pat`, or None.

    ⚠ A definition may name a framing in order to EXCLUDE it -- "judged by what they would have to
    assemble, not by the difference you claim". Treating that as drift would fail correct prose.
    So walk back from the match to the nearest clause boundary and check for a negator.
    """
    for m in re.finditer(pat, definition, re.I):
        head = definition[:m.start()]
        # the current clause: everything after the last sentence/clause break
        clause = re.split(r"[.;:—]|\bbut\b", head)[-1]
        if NEGATION.search(clause):
            continue                       # explicitly disclaimed -- not drift
        return m
    return None


def main() -> int:
    rubric = json.loads(RUBRIC.read_text())
    q = rubric.get("questions") or {}
    defs = reader_definitions()
    problems: list[str] = []

    print("rubric version:", rubric.get("_meta", {}).get("version"))
    print("=" * 78)

    for dim, definition in defs.items():
        if dim not in q:
            problems.append(f"{dim}: reader definition exists but the rubric has no such dimension")
            continue
        ins = _flat(q[dim].get("instructions", ""))
        shared = content_words(definition) & content_words(ins)
        print("  %-20s shares %2d term(s) with the rubric: %s"
              % (dim, len(shared), sorted(shared)[:6]))

        # ⚠ A definition with NO vocabulary in common with the rubric it describes was written
        # against a different one. This is the mechanical signature of the drift that happened.
        if not shared:
            problems.append(f"{dim}: reader definition shares NO vocabulary with its rubric "
                            f"instruction -- written against a different rubric? def={definition!r}")

        for pat, why in FORBIDDEN.get(dim, []):
            if uses_forbidden(definition, pat):
                problems.append(f"{dim}: uses forbidden framing /{pat}/ -- {why}")

    print()
    if problems:
        print("⚠ DRIFT DETECTED (%d):" % len(problems))
        for p in problems:
            print("   -", p)
        return 1
    print("✅ no drift: every reader-facing definition shares vocabulary with the rubric that scores "
          "it, and none uses a framing the rubric excludes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
