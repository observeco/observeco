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

# ⚠ BANDS ARE READ FROM THE RUBRIC, NEVER HARDCODED.
# This constant used to be `[("Fragile",5,39),("Contested",40,59),...]` while the rubric
# says Fragile 5-37, Contested 38-57, Viable 58-76, Strong 77-100. A report whose idea of
# a band disagrees with the instrument that produced the score is the same defect class as
# the hardcoded weights this file already fixed once. Kept only as a last-resort default
# when no rubric can be read at all.
BANDS_FALLBACK = [("Fragile", 5, 37), ("Contested", 38, 57),
                  ("Viable, conditional", 58, 76), ("Strong", 77, 100)]


def bands_from(rubric: dict) -> list:
    """The rubric's own band ladder. Falls back only if the rubric is unreadable."""
    b = ((rubric or {}).get("_meta") or {}).get("bands")
    if not b:
        return BANDS_FALLBACK
    try:
        return [(str(name), int(lo), int(hi)) for name, lo, hi in b]
    except Exception:
        return BANDS_FALLBACK

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

# ── WRITTEN FOR THE SUBMITTER, NOT FOR US ────────────────────────────────────
# Sean: "the form feels like it is written for someone internal and not front facing.
# A new user would get turned off. The report should provide definitions and explain
# the results to be useful to the user."
# So every term the report uses is defined where it is used, and the band ladder says
# what each band means for the BUSINESS rather than what number it is.
DIM_MEANING = {
    "position_strength": "How clearly you own a claim your rivals do not. Your single "
                         "biggest driver.",
    "mental_advantage": "Whether people think of YOU unprompted when they need what "
                        "you sell.",
    "defensibility": "How hard it would be for a rival to copy what makes you different.",
    "competitive_room": "How much margin is left for you after the big players set the "
                        "price.",
    "market_headroom": "Whether demand in your category is growing, already met, or "
                       "shrinking.",
    "demand_reach": "Whether the customers you describe can actually be found, and do pay.",
}

# What each band means for the business — the viability ladder.
BAND_MEANING = {
    "GATE": "Something has to be resolved before your position matters at all. The "
            "scores below describe what you told us, not what your business is worth.",
    "Fragile": "NOT VIABLE as it stands. Something structural is in the way — this is "
               "not an effort problem. Fix the blocked thing before spending on growth.",
    "Contested": "VIABLE, but not on this plan. There is a real business here; the way "
                 "you are differentiating is not yet doing the work. This is the "
                 "commonest place for a good operator with an undefined position — and "
                 "it is the cheapest band to move out of.",
    "Viable, conditional": "VIABLE, subject to one check. Your position can hold; the "
                           "single thing named below decides whether it does.",
    "Strong": "VIABLE AND DEFENSIBLE. Your position is distinct, and copying it would "
              "be slow or expensive for a rival.",
}

# ⚠ WHAT THE BAND IS NOT: it is not a probability of success, and not a credit score.
# It describes the POSITION, not the business's worth or its founder's ability.
BAND_CAVEAT = ("This band describes your POSITION, not your business's worth or your "
               "ability as an operator. It is not a probability of success.")

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


# ── RECOMMENDATIONS ──────────────────────────────────────────────────────────
# ⚠ GROUNDED IN THE RUBRIC, NOT INVENTED. Each entry says what the NEXT LEVEL of that
# dimension requires, taken from the rubric's own level language. A recommendation that
# names a move the instrument does not actually reward would be worse than none: it sends
# the user to spend effort on something that cannot move their score.
#
# Sean: "For recommendations, be specific about which areas they could explore to get the
# score up." So each one names the area AND the observable change that would register.
NEXT_LEVEL = {
    "position_strength": {
        1: ("You make no claim a buyer could prefer — you compete on price or availability "
            "alone. START HERE: write down one sentence a rival could not honestly say. If "
            "you cannot, that is the finding.",
            "Pick the situation you want to own — a product, an occasion, a buyer — and "
            "decide what you will be the answer to."),
        2: ("Your claim is either already owned by a named rival, or so generic that "
            "everyone in your category says it. Start by listing the words your "
            "rivals already use — anything they say, you cannot own.",
            "Find a claim that is true of you, matters to the buyer, and that the rivals "
            "you named do NOT make."),
        3: ("You hold a real claim, but several rivals make it or could match it easily. "
            "It is a place held, not an advantage.",
            "Narrow it until it is yours alone — a specific situation, ingredient, "
            "process or buyer the others cannot follow you into."),
        4: ("You have a genuine flank: a distinct claim the rivals you named do not own. "
            "What is missing is being the REFERENCE — the one others are defined against.",
            "Get the claim into the market's language: repeat it until buyers use your "
            "words to describe the category, not just to describe you."),
        5: ("You ARE the reference occupant — rivals are defined against you. Guard it "
            "rather than change it.",
            "Defend the position: keep the claim consistent and do not extend the brand "
            "into categories that dilute it."),
    },
    "mental_advantage": {
        1: ("No one could name you if asked. This is a reach problem before it is a "
            "positioning problem.",
            "Get in front of your buyer repeatedly in one place before widening."),
        2: ("People recognise your name when they see it, but do not think of you "
            "unprompted.",
            "Attach your name to one occasion or need, and be present at that moment "
            "every time."),
        3: ("You surface when someone is considering your category — the ordinary "
            "position of an established local business.",
            "Become one of the first names for a SPECIFIC occasion, not just a known "
            "option in the category."),
        4: ("You come to mind unprompted and are among the first names for your "
            "occasions.",
            "Make the association total — own the occasion itself, so the buyer thinks "
            "of you before they think of the category."),
        5: ("You are the defining association for the category or occasion.",
            "Protect it: consistency beats novelty at this level."),
    },
    "defensibility": {
        1: ("Nothing obstructs a challenger at all — no asset, no licence, no network.",
            "Build ONE asset that takes time to assemble: a licence, a system, a "
            "supply relationship, a data set."),
        2: ("The only thing you hold is a claimed difference anyone can copy in weeks "
            "by buying the same thing.",
            "Turn the message into an ASSET: something accumulated rather than said — "
            "a process, a contract, a proprietary method."),
        3: ("Real work is required to copy you, but nothing OBSTRUCTS a challenger "
            "beyond the cost of doing it.",
            "Add a mechanism that cannot be bought: a licence, a network, scale "
            "economics, or switching costs."),
        4: ("A genuine accumulated barrier exists that a challenger cannot cheaply "
            "assemble.",
            "Reinforce it with a second mechanism so the two protect each other."),
        5: ("Two or more mechanisms reinforce each other — replication would take a "
            "well-resourced rival a decade.",
            "Keep the mechanisms aligned; do not let one degrade while you grow the "
            "other."),
    },
    "competitive_room": {
        1: ("The category is consolidated: one or a few players set price or control "
            "access, and a small operator structurally cannot earn.",
            "Consider whether you are fighting in the right category at all — this is "
            "a structural read, not an effort problem."),
        2: ("A dominant player or a price floor set by much larger rivals squeezes "
            "everyone.",
            "Move where the dominant player's price does not set yours — a segment, "
            "service or format they cannot follow into."),
        3: ("Several strong brands and a general price floor keep margins thin, but "
            "small operators do establish themselves.",
            "Compete on something the price floor does not cover — service, "
            "specialisation, or a buyer who is not price-shopping."),
        4: ("Several players coexist and none dominates.",
            "Establish yourself deliberately before a larger player notices the gap."),
        5: ("Atomised and dominated by nobody — entry is open and margin exists.",
            "Grow fast enough to matter before the structure consolidates."),
    },
    "market_headroom": {
        1: ("There is no identifiable buying demand for this category.",
            "Re-examine whether the category you named is the one your buyer "
            "actually spends in."),
        2: ("Demand is already served — supply meets or exceeds what is wanted.",
            "Serve an unmet SLICE of the category rather than the category as "
            "a whole."),
        3: ("Demand is real and steady but already satisfied — a new entrant must "
            "take share rather than serve unmet need.",
            "Target an underserved buyer inside the category, or a need that is "
            "currently unmet by how existing sellers work."),
        4: ("Demand exceeds supply and the shortfall is growing.",
            "Add capacity deliberately — the constraint is supply, not demand."),
        5: ("The category cannot serve the demand that exists.",
            "Capacity is the binding constraint on the whole market — expand "
            "before rivals do."),
    },
    "demand_reach": {
        1: ("The customer is undefined, or you cannot legally serve the buyers you "
            "name.",
            "Name a specific buyer you CAN serve, then work out how to reach them."),
        2: ("A buyer group is named, but only as a demographic — no evidence you "
            "currently reach them.",
            "Describe the buyer concretely enough to find them, and name the channel "
            "you would use."),
        3: ("You reach a describable segment, but the route is generic or "
            "incidental rather than deliberate.",
            "Make one channel deliberate and targeted — chosen for that buyer "
            "rather than whoever happens to arrive."),
        4: ("You demonstrably generate revenue from an identified buyer through at "
            "least one credible channel.",
            "Deepen the concentration: own a segment completely rather than "
            "serving many thinly."),
        5: ("A tightly defined, paying segment you reach directly and cheaply.",
            "Sustain it and protect the channel's economics."),
    },
}


def recommendations(run: dict, counts: dict, weights: dict) -> list:
    """The moves most likely to raise the score, biggest weighted gap first.

    Ordered by WEIGHTED GAP (how many composite points are recoverable), so the user is
    told what matters most rather than what scores lowest. A dimension at 1/5 carrying
    25% is worth more attention than one at 2/5 carrying 10%.
    """
    dims = run.get("dimensions_display_1to5") or {}
    unscored = set(run.get("dimensions_unscored") or [])
    out = []
    for k, w in weights.items():
        if k in unscored:
            continue
        lvl = dims.get(k)
        if lvl is None:
            continue
        n = counts.get(k, 5)
        # recoverable composite points if this dimension reached its top level
        recoverable = (n - lvl) / max(n - 1, 1) * w
        block = NEXT_LEVEL.get(k, {}).get(int(lvl))
        if not block:
            continue
        what, todo = block
        out.append({"dim": k, "level": int(lvl), "of": n, "weight": w,
                    "recoverable": round(recoverable, 1),
                    "what": what, "todo": todo})
    out.sort(key=lambda d: -d["recoverable"])
    return out


def specifics(submission: dict | None) -> dict:
    """Pull the submitter's OWN words out of the submission.

    ⚠ WHY THIS EXISTS. Sean: "The report is very generic. I would expect some specific
    details relating to the info provided in the form? You need to be maximally helpful
    without giving away everything, just enough to the point where it is compelling and
    clear they need observeco.com to help them with their business."

    The report could not be specific because it only ever read the SCORES. The words the
    business typed -- its claim, its rivals, its customer -- live in the submission, and
    were never passed to the renderer. A read that never quotes the reader back to
    themselves cannot feel like it is about their business.

    ⚠ IT USES THEIR WORDS, IT DOES NOT WRITE NEW ONES. This is deliberately NOT a model
    call: the report is a computed artifact (spec 5.5), and the specificity comes from
    quoting them, not from generating fresh prose about them.
    """
    if not submission:
        return {}
    form = submission.get("form") or {}
    def clean(k):
        v = (form.get(k) or "").strip()
        return v if v and len(v) < 400 else ""
    return {
        "business": clean("business_name"),
        "category": clean("category"),
        "city": clean("city"),
        "claim": clean("positioning_sentence"),
        "different": clean("differentiator"),
        "undercut": clean("undercut_on"),
        "customer": clean("customer_description"),
        "website": clean("website"),
        "price_ours": clean("your_price_point"),
        "price_theirs": clean("their_price_point"),
        "rivals": [r for r in (submission.get("competitors_named") or []) if r][:12],
    }


def is_url(s: str) -> bool:
    """A pasted URL is not a stated claim, and must not be quoted AS one."""
    return bool(s) and (s.strip().startswith(("http://", "https://", "www."))
                        or (" " not in s.strip() and "." in s.strip()
                            and "/" not in s.strip()[:1]))


def norm(name: str) -> str:
    return ALIAS.get(name, name)


def wrap(text: str, width: int) -> list:
    """Wrap plain prose for terminal output. Textwrap, not hand-rolled string math."""
    import textwrap
    return textwrap.wrap(text, width=width) or [""]


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


def version_b(run: dict, counts: dict, weights: dict, rubric: dict | None = None,
              sp: dict | None = None) -> str:
    dims = run["dimensions_display_1to5"]
    conf = run["confidence"]
    band = run.get("band")
    gate = gate_dimension(run, counts, weights)
    unscored = set(run.get("dimensions_unscored") or [])
    unresolved = [k for k in weights
                  if k not in unscored and conf.get(k) is not None
                  and conf[k] < CONF_FLAG]
    sp = sp or {}
    out = []
    who = sp.get("business") or ""
    out.append(f"OBSERVECO — YOUR POSITIONING READ")
    if who:
        out.append(f"Prepared for: {who}" + (f" · {sp['category']}" if sp.get("category") else ""))
    out.append("=" * 52)
    out.append("")

    # ── THEIR SITUATION, IN THEIR OWN WORDS ──────────────────────────────────
    # This section is what makes the report about THEIR business rather than about
    # businesses in general. It quotes what they typed and says what it implies —
    # it does not invent findings, and it does not tell them what to do about it.
    if who or sp.get("claim") or sp.get("rivals"):
        out.append("WHAT YOU TOLD US, AND WHAT IT IMPLIES")
        out.append("")
        if sp.get("claim") and not is_url(sp.get("claim")):
            out.append(f"  You said you are different because:")
            for line in wrap(f'"{sp["claim"]}"', 60):
                out.append(f"      {line}")
            ps = dims.get("position_strength")
            if ps is not None and ps <= 2:
                out.append("")
                out.append("      Read literally, that is a claim several of your rivals could")
                out.append("      also make. A customer choosing between you and them")
                out.append("      would have no reason to pick you on this — which is what")
                out.append("      the position strength score reflects.")
            elif ps is not None and ps >= 4:
                out.append("")
                out.append("      That is a genuine distinction, and it is doing real")
                out.append("      work for you.")
            out.append("")
        elif sp.get("website"):
            out.append(f"  You pointed us at {sp['website']} rather than writing a")
            out.append("  positioning statement. That is a perfectly normal answer —")
            out.append("      and it is also the finding: the claim your business makes")
            out.append("      lives on your site, not in something you can say in a")
            out.append("      sentence. We read the site and used it.")
            out.append("")
        if sp.get("rivals"):
            rv = ", ".join(sp["rivals"][:6])
            out.append(f"  The rivals you named:")
            for line in wrap(rv, 60):
                out.append(f"      {line}")
            ps = dims.get("position_strength")
            if ps is not None and ps <= 2:
                out.append("")
                out.append("      The read can say whether a claim is yours only by")
                out.append("      checking it against what THEY say. Naming them was the")
                out.append("      right move — what was missing was a claim none of them")
                out.append("      already owns.")
            out.append("")
        if sp.get("customer"):
            out.append(f"  Your customer, as you describe them:")
            for line in wrap(f'"{sp["customer"]}"', 60):
                out.append(f"      {line}")
            dr = dims.get("demand_reach")
            if dr is not None and dr <= 2:
                out.append("")
                out.append("      That is a buyer group, and a sensible one. What it does")
                out.append("      not yet say is how you reach them deliberately — which")
                out.append("      is what the demand reach score is picking up.")
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
        out.append("WHAT THE BANDS MEAN")
        out.append("")
        for name, lo, hi in bands_from(rubric or {}):
            here = "  <- YOU ARE HERE" if name == band else ""
            out.append(f"  {name.upper():22}{lo}-{hi}{here}")
            for line in wrap(BAND_MEANING.get(name, ""), 62):
                out.append(f"      {line}")
            out.append("")
        out.append(f"  {BAND_CAVEAT}")
        out.append("")
        out.append("WHAT EACH SCORE MEANS")
        out.append("")
        for k in weights:
            out.append(f"  {LABEL.get(k, k):20}{str(dims.get(k, '—')) + '/5' if k not in unscored else 'not scored'}")
            for line in wrap(DIM_MEANING.get(k, ""), 62):
                out.append(f"      {line}")
        out.append("")
        recs = recommendations(run, counts, weights)
        if recs:
            out.append("WHERE TO GET THE SCORE UP")
            out.append("")
            out.append("  Ordered by how much of your score is recoverable, largest first.")
            out.append("")
            for i, d in enumerate(recs[:4], 1):
                out.append(f"  {i}. {LABEL.get(d['dim'], d['dim'])} "
                           f"({d['level']}/{d['of']}) — worth about "
                           f"{d['recoverable']} points")
                for line in wrap("Why it is where it is: " + d["what"], 62):
                    out.append(f"      {line}")
                for line in wrap("Explore: " + d["todo"], 62):
                    out.append(f"      {line}")
                out.append("")
    out.append("WHAT WE DID NOT CHECK")
    out.append("")
    out.append("  We scored what your submission claims. We did NOT cross-check your")
    out.append("  competitors' claims against public registries, verify their pricing,")
    out.append("  or map who owns which word in your category. That is the paid")
    out.append("  analysis.")
    # ⚠ SEAN'S LINE, HELD: "maximally helpful without giving away everything, just enough
    # to the point where it is compelling and clear they need observeco.com to help them."
    # The mechanism is NOT a vague upsell. It is to name, concretely and in THEIR words,
    # the specific question their score turns on -- and then stop exactly there. The
    # self-diagnosis is free and complete; the resolution is the engagement.
    if sp.get("rivals"):
        out.append("")
        rivals_txt = ", ".join(sp["rivals"][:4])
        out.append(f"  Concretely, for you: does {rivals_txt} already own the claim")
        for line in wrap("you are making — and if one does, what is genuinely left that "
                         "is yours? That is the question your position strength score "
                         "turns on, and it is a question about THEIR position. We cannot "
                         "answer it from a form.", 62):
            out.append(f"  {line}")
        out.append("")
        out.append("  Answering it needs someone to read what your rivals publish, map")
        out.append("  which words each one owns, and tell you which claim is still open.")
        out.append("  That is the work behind the score you just read.")
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


def render(run: dict, rubric_path: Path | None,
           submission: dict | None = None) -> tuple[str, str]:
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
    return (version_a(r, counts, weights),
            version_b(r, counts, weights, load_rubric(rubric_path),
                      specifics(submission)))


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
    # the submission, when it sits beside the run file -- so the CLI is as specific as
    # the sandbox. Absent, the report simply has less to quote.
    sub = None
    for cand in (runpath.with_suffix(".submission.json"),
                 runpath.parent / f"{runpath.stem}.payload.json"):
        if cand.exists():
            sub = json.loads(cand.read_text())
            break
    a, b = render(run, Path(args.rubric) if args.rubric else None, sub)

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
