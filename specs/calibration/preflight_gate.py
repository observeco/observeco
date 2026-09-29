#!/usr/bin/env python3
"""preflight_gate.py — spec 095 section 3.11: the pre-flight gate.

WHY THIS EXISTS
    Section 3.11 (D30), Sean's condition on D25, verbatim: "It burns a lot of tokens so
    let's make sure before we run the analysis we assess the input quality first,
    before deciding it is worth the token burn."

    The naive shape is: submit -> run the competitor scan -> score -> discover the
    input was unusable -> refuse. That burns the full research cost on a submission we
    are going to refuse anyway. THIS GATE FIRES ON THE FORM ANSWERS ALONE, before a
    single search is issued, and before any model call.

WHAT IT DECIDES (section 3.10's slot table, one signal per scored dimension)
    Report    every dimension has a form answer OR a passing enrichment source
    Guidance  at least one dimension has neither -> template C coaching email
    Refused   the business cannot be analysed at all

    There is no third outcome. A submission is never silently dropped.

THE TRAP PAIR THIS GATE MUST NOT MERGE (section 3.10, traps 1 and 3)
    A PLACEHOLDER ("asdf", "test", "-") is treated as ABSENT -> it has nothing to
    analyse, so it goes to guidance.
    A GENERIC BUT GENUINE sentence ("We provide quality service and value to our
    customers") is treated as PRESENT -> it is a real answer containing no position,
    so it is a REPORTABLE FINDING, not a refusal.
    The test is not fluency or length; it is whether a human wrote something they
    meant. A rule that merged the two would either refuse scorable submissions or
    score empty ones.

WHAT THIS GATE DELIBERATELY DOES NOT DO
    It does not scan. It does not call a model. It decides whether either is worth
    doing. That is the whole point of Sean's rule.

Usage:
    python3 preflight_gate.py inputs-v4/EL03-best.json
    python3 preflight_gate.py inputs-v4/EL03-best.json --json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

# ---------------------------------------------------------------------------
# STEERING BLOCK — Sean owns this list. Adding a phrase is a one-line edit.
# ---------------------------------------------------------------------------
# A sentence built ENTIRELY from these is fluent and means nothing. It is still a
# real answer, so it reaches the report as a finding -- it never causes a refusal.
GENERIC_MARKERS = [
    "quality service", "high quality", "highest quality", "best service", "good service",
    "quality products", "great service", "excellent service", "best quality",
    "value for money", "good value", "affordable prices", "reasonable prices",
    "competitive prices", "competitive pricing", "best prices", "lowest prices",
    "customer satisfaction", "customer service", "customer first", "customer-centric",
    "trusted", "reliable", "reliability", "integrity", "honesty", "committed",
    "dedicated", "passionate", "passion for", "commitment to excellence", "excellence",
    "exceed expectations", "go the extra mile", "personalised service",
    "one-stop", "wide range", "variety of", "meet your needs", "tailored solutions",
    "years of experience", "family business", "professional service",
]

# A submission that DECLARES it has no position. Real answer, load-bearing: the
# report says "you haven't defined what makes you different". Not a refusal.
DECLARED_NONE = [
    "we don't have one", "we do not have one", "no positioning", "not sure",
    "none", "n/a", "nothing yet", "don't know", "do not know", "no differentiator",
    "we are the same", "no idea",
]

PLACEHOLDER = re.compile(
    r"^(?:asdf+|test+|testing|todo|xxx+|tbd|nil|none|na|n/a|-+|\.+|_+|\?+|123+|"
    r"\W*|(.)\1{2,})$",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# PER-SLOT MINIMUMS. There is no single global char floor.
# A first pass used one 12-character floor for every slot and REFUSED 100% of the
# real corpus AND all five negative controls -- because legitimate answers in this
# corpus include 'value' (5 chars), '3-5' (3), and 'Bubble tea' (10). The corpus
# itself sets the floor: category min 29, price min 5, competitors min 1.
# ---------------------------------------------------------------------------
SLOT_MIN_CHARS = {
    "category": 8,        # 'Bubble tea', 'Furniture' are real
    "positioning": 10,    # 'we don't have one' is real and load-bearing
    "competitors": 1,     # '1', '3-5'
    "price": 2,           # 'value', 'S$4.50'
    "customer": 8,
    "business_name": 2,
}

# Section 3.6's Required column is the authority on what can cause a refusal.
#   REQUIRED : business name, category, position  (+ email, at delivery)
#   DEPTH    : price point, competitor count -- "drives depth", and fillable by
#              enrichment. A missing depth field must NEVER refuse a submission.
REQUIRED_SLOTS = {"business_name", "category", "positioning"}
DEPTH_SLOTS = {"price", "competitors"}

# Slots whose legitimate answers contain no letter at all.
LETTER_FREE_SLOTS = {"competitors", "price"}

# ---------------------------------------------------------------------------
# TRAP 3 THRESHOLD — set from the corpus, not chosen to fit one control.
# Coverage = share of content words that are generic stems. Measured:
#   corpus (120 real cases): min 0.00, p50 0.00, p90 0.10, p99 0.18, MAX 0.20
#   NC03 (the generic control): 0.55
# A threshold of 0.40 sits between them with margin on both sides. It is
# deliberately NOT 0.55 -- a threshold set exactly at the one example that
# motivated it would be fitting to a single case.
# NOTE: this detector deliberately does NOT fire on any of the 120 real corpus
# cases, which means its precision on real submissions is UNVERIFIED. It is
# calibrated against the synthetic control only.
# ---------------------------------------------------------------------------
GENERIC_COVERAGE = 0.40

GENERIC_STEMS = [
    "passion", "quality", "service", "customer", "dedicat", "commit", "excellen",
    "trust", "reliab", "afford", "value", "competit", "profession", "experience",
    "satisf", "solution", "range", "variety", "standard", "friendly", "honest",
    "integrity", "reputation", "mission", "best", "great", "high", "offer",
    "provide", "deliver", "ensure", "strive", "believe", "focus", "care", "goal",
    "need", "consist",
]


def is_placeholder(text: str, slot: str = "positioning") -> bool:
    """Trap 1 (spec 3.10): a placeholder is treated as ABSENT.

    The length floor is PER SLOT. One global floor was the defect that refused
    the whole corpus.

    The LETTER requirement is also per slot, and getting that wrong was a second
    defect of the same class: `competitors_named_count` legitimately holds '3-5'
    and '2-4', and `your_price_point` holds 'S$4.50'. Demanding a letter marked
    every one of them ABSENT and fired a depth shortfall on all 120 cases.
    The corpus's own vocabulary ('3-5' x57, '2-4' x52, '1-2', '5-8', '1') is the
    authority: a count or price need not contain a letter.
    """
    t = (text or "").strip()
    if len(t) < SLOT_MIN_CHARS.get(slot, 8):
        return True
    if slot not in LETTER_FREE_SLOTS and not re.search(r"[A-Za-z]", t):
        return True
    return bool(PLACEHOLDER.match(t))


def is_declared_none(text: str) -> bool:
    t = (text or "").strip().lower().rstrip(".! ")
    return t in DECLARED_NONE


GENERIC_STOP = {
    "with", "that", "your", "their", "them", "this", "have", "will", "from", "what",
    "when", "which", "they", "been", "more", "most", "than", "also", "into", "over",
    "such", "our", "are", "for", "you", "who", "how", "its", "can", "all", "not",
    "but", "out", "one", "get", "has", "was", "were", "does", "make", "made", "take",
    "want", "like", "just", "very", "and", "the", "each", "we", "us", "it", "is",
    "to", "of", "in", "on", "at", "by", "as", "be", "do", "so", "if", "no",
}


def generic_coverage(text: str) -> float | None:
    """Share of content words that are generic stems. None when too short."""
    tl = (text or "").lower()
    content = [w for w in re.findall(r"[a-z']{4,}", tl) if w not in GENERIC_STOP]
    if len(content) < 3:
        return None
    hits = sum(1 for w in content if any(w.startswith(s) for s in GENERIC_STEMS))
    return hits / len(content)


def is_generic(text: str) -> bool:
    """Trap 3 (spec 3.10): fluent, real, and says nothing.

    NOT a refusal trigger. This is the 'you haven't defined what makes you
    different' finding, and the spec calls it the load-bearing one.

    Fires only when the answer is generic AND carries no specific detail:
      - no digits anywhere (prices, years, counts are specifics), and
      - no proper nouns after the first word (brands, places, channels).
    'We provide quality service' -> generic. 'We supply Michelin kitchens since
    2009' -> specific, because of 'Michelin' and '2009'.
    """
    t = (text or "").strip()
    if len(t) < 12:
        return False
    cov = generic_coverage(t)
    if cov is None or cov < GENERIC_COVERAGE:
        return False
    if re.search(r"\d", t):
        return False
    raw = re.findall(r"[A-Za-z][a-z]{2,}", t)
    proper = [w for i, w in enumerate(raw)
              if i > 0 and w[0].isupper() and w.lower() not in GENERIC_STOP]
    return not proper


def value(form: dict, *names: str) -> str:
    for n in names:
        v = form.get(n)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return ""


def slot_state(form: dict, names: list[str], *, slot: str,
               declared_none_ok: bool = False) -> dict:
    """Return {present, generic, declared_none, field, reason}.

    `slot` selects the per-slot length floor. Passing the wrong slot name here was
    the defect that made the gate refuse the entire corpus.
    """
    raw = value(form, *names)
    field = next((n for n in names if isinstance(form.get(n), str)
                  and form.get(n, "").strip()), None)
    if not raw:
        return {"present": False, "generic": False, "declared_none": False,
                "field": None, "reason": "no answer in any mapped field"}
    if is_declared_none(raw) and declared_none_ok:
        return {"present": True, "generic": True, "declared_none": True, "field": field,
                "reason": "the submitter DECLARED they have no position — a real "
                          "answer, reported as a finding"}
    if is_placeholder(raw, slot):
        return {"present": False, "generic": False, "declared_none": False,
                "field": field, "reason": f"placeholder or too short ({raw[:24]!r})"}
    # Specificity is judged across ALL populated fields for this slot, not just the
    # first one. A terse positioning sentence plus a detailed differentiator is a
    # well-answered slot; judging only the first field flagged Coupang -- whose
    # differentiator is a full flywheel explanation -- as having "no defined position".
    combined = " ".join(v for v in (form.get(n) for n in names)
                        if isinstance(v, str) and v.strip())
    return {"present": True, "generic": is_generic(combined), "declared_none": False,
            "field": field, "reason": "real answer"}


def count_competitors(form: dict) -> int | None:
    """'3-5', '0', 'none', 'unknown' -> an int, or None when not parseable."""
    raw = value(form, "competitors_named_count", "competitors_named")
    if not raw:
        return None
    t = raw.strip().lower()
    if t in {"none", "zero", "n/a", "na", "unknown", "not sure", "don't know"}:
        return 0
    first = re.findall(r"\d+", t)
    if first:
        return int(first[0])
    return None


def evaluate(payload: dict, *, scan_available: bool = False) -> dict:
    form = payload.get("form") or {}
    derived = payload.get("derived_competitive_set") or {}
    flags: list[str] = []

    slots = {
        "business_name": slot_state(form, ["business_name"], slot="business_name"),
        "category": slot_state(form, ["category"], slot="category"),
        "positioning": slot_state(form, ["positioning_sentence", "differentiator"],
                                  slot="positioning", declared_none_ok=True),
        "competitors": slot_state(form,
                                  ["competitors_named_count", "competitors_named"],
                                  slot="competitors"),
        "price": slot_state(form, ["your_price_point", "their_price_point"],
                            slot="price"),
        # NOTE: the slot table requires a customer description. The corpus form carries
        # no such field -- see FORM GAP below.
        "customer": slot_state(form,
                               ["customer", "target_customer", "customer_description"],
                               slot="customer"),
    }

    ncomp = count_competitors(form)
    if slots["competitors"]["present"] and ncomp == 0:
        if derived:
            slots["competitors"]["reason"] = "none named, but a derived set exists"
        elif scan_available:
            slots["competitors"]["reason"] = "none named; the scanner will run"
        else:
            slots["competitors"]["present"] = False
            slots["competitors"]["reason"] = (
                "no competitors named, no derived set, and the scanner is NOT wired "
                "in — this slot cannot be filled")

    # ---- FORM GAP: a slot the spec requires that the form never collects ---------
    form_gap = not any(k in form for k in
                       ("customer", "target_customer", "customer_description"))
    if form_gap:
        flags.append(
            "FORM GAP: section 3.10 requires a CUSTOMER DESCRIPTION slot driving "
            "demand_reach and mental_advantage, but no form field collects one. "
            "Every submission would fail this slot, so it is NOT treated as a "
            "refusal here — it is reported as a spec/implementation gap.")

    # ---- trap 2: repetition inflation -------------------------------------------
    answers = [value(form, "positioning_sentence"), value(form, "differentiator"),
               value(form, "undercut_on")]
    norm = [re.sub(r"\W+", " ", a.lower()).strip() for a in answers if a]
    if len(norm) != len(set(norm)):
        flags.append(
            "REPETITION: the same answer is pasted into more than one field. A "
            "satisfied word count is not a second signal.")

    # ---- trap 3: the generic position is the FINDING, not a refusal --------------
    if slots["positioning"]["present"] and slots["positioning"]["generic"] \
            and not slots["positioning"]["declared_none"]:
        flags.append(
            "NO DEFINED POSITION: the differentiator is fluent but generic. This is a "
            "reportable finding — the report must say so plainly.")
    if slots["positioning"].get("declared_none"):
        flags.append(
            "DECLARED NO POSITION: the submitter said they have no positioning. This "
            "is a real answer and the report's first finding, not a refusal.")

    # ---- REFUSAL is decided ONLY by section 3.6's Required column ----------------
    # price and competitor count "drive depth" and are enrichable, so a missing
    # depth field must NEVER refuse a submission.
    missing = [k for k in REQUIRED_SLOTS if not slots[k]["present"]]
    depth_missing = [k for k in DEPTH_SLOTS if not slots[k]["present"]]
    if depth_missing and not missing:
        flags.append(
            "DEPTH SHORTFALL: " + ", ".join(depth_missing) + " missing. The report "
            "will be thinner on the dimensions these drive, and position strength is "
            "capped at ADEQUATE (3) while the flank is unproven. This is NOT a "
            "refusal — the submission is still scored.")

    outcome = "REFUSED_INPUT_QUALITY" if missing else "REPORT"

    # ---- the scan decision: only worth the token burn if the answer is scorable ---
    run_scan = bool(outcome == "REPORT" and slots["category"]["present"]
                    and slots["positioning"]["present"])

    return {
        "case": (payload.get("_meta") or {}).get("case"),
        "business": (payload.get("_meta") or {}).get("business"),
        "outcome": outcome,
        "run_scan": run_scan,
        "scan_available": scan_available,
        "slots": slots,
        "missing_slots": missing,
        "depth_missing": depth_missing,
        "flags": flags,
        "guidance_email": (outcome == "REFUSED_INPUT_QUALITY"),
    }


def render(res: dict) -> str:
    out = []
    out.append("PRE-FLIGHT GATE (spec 3.11 / D30)")
    out.append("=" * 52)
    out.append(f"  business : {res.get('business')}  [{res.get('case')}]")
    out.append(f"  OUTCOME  : {res['outcome']}")
    out.append(f"  run scan : {'YES' if res['run_scan'] else 'NO — no token burn'}")
    if res["scan_available"] is False:
        out.append("  scan     : NOT WIRED IN (section 4.6 built, not connected)")
    out.append("")
    out.append("  SLOT                       STATE")
    out.append("  " + "-" * 50)
    for k, v in res["slots"].items():
        state = "present" if v["present"] else "MISSING"
        extra = " [generic]" if v.get("generic") else ""
        out.append(f"  {k:26} {state}{extra}")
        out.append(f"      {v['reason']}")
    if res["missing_slots"]:
        out.append("")
        out.append("  MISSING: " + ", ".join(res["missing_slots"]))
        out.append("  -> guidance email (template C), not a refusal. The submission "
                   "is never dropped.")
    if res["flags"]:
        out.append("")
        for f in res["flags"]:
            out.append(f"  ! {f}")
    return "\n".join(out)


def main() -> None:
    ap = argparse.ArgumentParser(description="spec 3.11 pre-flight gate")
    ap.add_argument("input", help="path to a form payload JSON")
    ap.add_argument("--scan-available", action="store_true",
                    help="the section 4.6 scanner is wired in and may fill the "
                         "competitors slot")
    ap.add_argument("--json", action="store_true", help="emit JSON")
    args = ap.parse_args()

    payload = json.loads(Path(args.input).read_text())
    res = evaluate(payload, scan_available=args.scan_available)

    if args.json:
        print(json.dumps(res, indent=2))
    else:
        print(render(res))

    if res["outcome"] == "REFUSED_INPUT_QUALITY":
        sys.exit(3)      # guidance, not failure
    sys.exit(0)


if __name__ == "__main__":
    main()
