#!/usr/bin/env python3
"""MIND TEST — the precondition gate (§4.6.4.7) and the attribution test (§4.6.4.4).

Spec: obs-spec-095 section 4.6.4 (and 4.6.3 for the claim-vs-claims fallback).

WHY THIS EXISTS
    Sean's three-way rule (§4.6.4.1) says: with INDEPENDENT CUSTOMER EVIDENCE, compare the customers'
    own words against the brand's published claim -- agree means the position is real, disagree means
    FLAG IT. With NO such evidence the brand is new/unobserved and its CLAIM is assessed against its
    COMPETITORS' CLAIMS only, with the limit stated, never smoothed over.

    This module is the part of that rule the tool must run per submission: the PRECONDITION that says
    whether a corpus can answer the question at all, and the ATTRIBUTION test that decides agree vs
    disagree when it can.

THE RULE THIS MODULE ENCODES, AND WHERE IT CAME FROM (all measured, none assumed)
    §4.6.4.4 Test 2: the claim is real only when a review NAMES THE RIVAL as the comparison. "I go here
    instead of X because..." is the sentence that proves a position exists; a review with no competitor
    in it is CATEGORY TALK, and category talk corroborates nobody.

    §4.6.4.7: 0 of 59 managed-IT Google reviews named an alternative. §4.6.4.6: same in 12,633
    food-retail reviews. THE CAUSE IS STRUCTURAL -- GOOGLE REVIEWS ARE POST-PURCHASE. Their author has
    already chosen. So the discriminator is not B2C-vs-B2B, it is WHETHER THE REVIEW FORM ASKS THE
    COMPARISON QUESTION. G2 / Capterra / TrustRadius / Clutch / Gartner Peer Insights solicit it
    ("what alternatives did you consider"); Google's form does not. Attribution is absent from a
    post-purchase corpus BY CONSTRUCTION, not by scarcity, and more volume will not produce it.

    THEREFORE `can_mind_test` NEVER REASONS ABOUT A PLATFORM. It reads a registry the CALLER supplies.
    A platform absent from that registry is UNKNOWN -- never YES. This session was burned twice by
    reasoning instead of measuring, so the guess path does not exist.

THE THREE EXCLUSIONS THE ATTRIBUTION TEST NEEDS (each of these bit us for real, §4.6.4.5/§4.6.4.6)
    1. SELF-MATCH. "tiong bahru" matched inside "Tiong Bahru Bakery" and produced 9 fake rival mentions
       for the brand it named. Fixed twice over: the brand's own name is MASKED out of its own review
       text before any rival is scanned for, AND a rival whose name is a token-subset of the brand's
       name (either direction) is dropped as an alias of the brand.
    2. COMMON-WORD BRAND NAMES. Whole-word matching alone does NOT fix this: "corner" in "bottom left
       corner" and "crunch" in "lacks crunch" are whole words. So rival names whose EVERY token is in
       the caller's `generic` set are dropped. The generic set is CALLER-SUPPLIED knowledge -- the
       module will not guess that "corner" is a common word.
    3. A BRAND LITERALLY NAMED AFTER A GENERIC PHRASE. "Salad Shop" collected 168 of 449 hits and every
       one was a false positive; a frequency filter could not remove it because the brand IS the phrase.
       No cleverness fixes this -- only the caller's generic set can. The module refuses to pretend
       otherwise: an unlisted generic-phrase brand is counted, and that is the caller's limit to state.

WHAT THIS MODULE WILL NOT DO
    - It never invents evidence. No corpus, empty text, too-thin text, a bot wall or navigation chrome
      -> a REFUSAL with the reason and a stated limit. (§4.6.4.4: "too few reviews to test at all --
      report the count and refuse the verdict". §4.6.4.7: Clutch returned an 813-character shell and
      DesignRush/TechBehemoths 1,465/1,590 characters that were NAVIGATION MENUS, and a naive extractor
      rendered those menus as vendor names. A block page rendering as ordinary text is the protocol's
      worst documented failure, so the corpus type is checked before anything is counted.)
    - It never lets vocabulary overlap decide on its own. Test 1 (overlap) is necessary but NOT
      SUFFICIENT; Test 2 (attribution) is the discriminator (§4.6.4.4). A keyword miss is weak
      evidence and is labelled as such (§4.6.4.5 limit 2), never read as "the claim is unperceived".
    - It never reports INCONCLUSIVE as a divergence. "No rival named" is category talk, not
      disagreement (§4.6.4.5).
    - It makes no network call, uses no clock and no randomness: same input -> byte-identical output.

USAGE
    from mind_test import can_mind_test, attribution, mind_verdict, MEASURED_REGISTRY
    can_mind_test("google_maps", MEASURED_REGISTRY)            -> "NO"
    attribution(reviews, "Tiong Bahru Bakery", rivals, generic)  -> per-rival counts + excerpts
    mind_verdict(claim, reviews, brand, rivals, generic, platform, registry) -> the three-way outcome

SELF-TEST (synthetic fixtures, no network):
    python3 mind_test.py
"""
from __future__ import annotations

import json
import re
from typing import Iterable, Mapping

__all__ = [
    "can_mind_test", "attribution", "mind_verdict", "corpus_quality", "claim_terms",
    "render_finding", "MEASURED_REGISTRY", "DEFAULT_GENERIC",
    "CAN_YES", "CAN_NO", "CAN_UNKNOWN", "VERDICTS",
]

# ---------------------------------------------------------------------------------------------------
# 1. THE PRECONDITION (§4.6.4.7)
# ---------------------------------------------------------------------------------------------------

CAN_YES, CAN_NO, CAN_UNKNOWN = "YES", "NO", "UNKNOWN"

# ⚠ A CONVENIENCE REGISTRY FOR CALLERS -- NOT A DEFAULT. `can_mind_test` never falls back to it; the
# registry is a REQUIRED argument, so a missing platform is UNKNOWN rather than a silent YES.
#
# Every value below is either named in the spec's measurement or it is ABSENT. Nothing is inferred:
MEASURED_REGISTRY: dict[str, bool] = {
    # §4.6.4.7 (measured): these forms ASK the comparison question -- "what alternatives did you
    # consider", "what do you dislike", "what problems does it solve" -- so the comparison appears
    # in the review text.
    "g2": True,
    "capterra": True,
    "trustradius": True,
    "clutch": True,
    "gartner_peer_insights": True,
    # §4.6.4.6 / §4.6.4.7 (measured): POST-PURCHASE forms ("how was your experience"). Attribution is
    # absent by construction: 0 of 59 managed-IT reviews, 0 of 12,633 food-retail reviews.
    "google_maps": False,
    "trustpilot": False,
    "yelp": False,
    # ⚠ DELIBERATELY ABSENT, so the answer is UNKNOWN rather than a guess: product_hunt, the
    # marketplace review sites (AppExchange / AWS Marketplace / Shopify App Store) and the analyst
    # peer-review sections are all listed as SOURCES in §4.6.4.3, but §4.6.4.7's discriminator is the
    # REVIEW FORM and no one read those forms. Add a key here only after reading the form.
}

_CAN_KEYS = ("solicits_alternatives", "asks_comparison", "comparative")


def can_mind_test(platform: str, registry: "dict | None") -> str:
    """Can this platform's corpus be mind-tested at all? YES / NO / UNKNOWN.

    ⚠ THIS FUNCTION NEVER GUESSES. It does not know anything about any platform. It reads the
    registry the CALLER supplies, which maps platform -> whether the review form solicits
    alternatives. A platform that is not in the registry is UNKNOWN -- expressly NOT YES. A value it
    cannot interpret is UNKNOWN too; an unreadable registry is not a licence to assume comparison is
    present. (§4.6.4.7: "it is not B2C-vs-B2B, it is whether the review form asks the comparison
    question" -- and the spec's precondition is measurable BEFORE any capture: read the review form.)

    Returned values are always one of the three constants, so a caller can branch on them exhaustively.

    Accepted value shapes, and nothing else:
        True / False                     the form does / does not solicit alternatives
        1 / 0                            the same, from JSON that lost its booleans
        {"solicits_alternatives": bool}  or "asks_comparison" / "comparative" -- a richer record
        anything else                    UNKNOWN
    """
    if not isinstance(registry, Mapping) or platform is None:
        return CAN_UNKNOWN
    key = str(platform).strip().lower()
    if not key:
        return CAN_UNKNOWN
    for raw_name, value in registry.items():
        if str(raw_name).strip().lower() != key:
            continue
        if isinstance(value, bool):                      # before the int check: bool IS an int
            return CAN_YES if value else CAN_NO
        if isinstance(value, int) and value in (0, 1):
            return CAN_YES if value else CAN_NO
        if isinstance(value, Mapping):
            for rich_key in _CAN_KEYS:
                inner = value.get(rich_key)
                if isinstance(inner, bool):
                    return CAN_YES if inner else CAN_NO
            return CAN_UNKNOWN                            # a record with no such key states nothing
        return CAN_UNKNOWN
    return CAN_UNKNOWN                                    # absent is absent, never a YES


# ---------------------------------------------------------------------------------------------------
# 2. TOKEN MATCHING -- whole-word, case-insensitive, hyphen/apostrophe tolerant
# ---------------------------------------------------------------------------------------------------

_TOKEN_RE = re.compile(r"[a-z0-9]+")
_JOIN = r"[\s'\u2019\-]*"     # what may sit between two tokens of one name: space, apostrophe, hyphen


def tokenise(text: str) -> list[str]:
    """Lowercased alphanumeric tokens. Hyphens and apostrophes separate ('Stuff'D' -> stuff, d),
    which is what makes whole-word matching tolerant of 'Tiong-Bahru' vs 'Tiong Bahru'."""
    return _TOKEN_RE.findall((text or "").lower())


def _name_pattern(name: str) -> re.Pattern | None:
    """A whole-word pattern for a brand name, case-insensitive.

    Tokens are joined by `[\\s'\\u2019\\-]*` so "Paris Baguette" also matches "paris-baguette" and
    "ParisBaguette", while the lookarounds `(?<![a-z0-9])` / `(?![a-z0-9])` keep it WHOLE-WORD:
    "paris baguettes" is NOT a match for "Paris Baguette" (§4.6.4.6 exclusion (b) demands whole-word
    matching; the plural miss is a known, stated recall limit, not a bug).
    """
    toks = tokenise(name)
    if not toks:
        return None
    body = _JOIN.join(re.escape(t) for t in toks)
    return re.compile(r"(?<![a-z0-9])" + body + r"(?![a-z0-9])", re.I)


def _brand_mask_pattern(brand: str) -> re.Pattern | None:
    """Same shape as `_name_pattern`, used to MASK the brand out of its own review text."""
    return _name_pattern(brand)


def _is_self_alias(rival: str, brand: str) -> bool:
    """Is this 'rival' actually the reviewed brand under another name? (§4.6.4.5 defect 4.)

    True when the rival's token set is a subset of the brand's token set OR vice versa -- so
    "Tiong Bahru" and "Tiong Bahru Bakery Singapore" are both recognised as the brand
    "Tiong Bahru Bakery", and are dropped instead of counted. Deliberately over-inclusive: dropping a
    real rival costs recall, whereas counting the brand itself fabricates evidence, which is worse.
    """
    r, b = set(tokenise(rival)), set(tokenise(brand))
    if not r or not b:
        return False
    return r <= b or b <= r


def _is_generic(name: str, generic_tokens: set[str]) -> bool:
    """Is this rival name made ENTIRELY of common words the caller declared generic?

    The rule is all-tokens-generic, and it is conservative on purpose: "Corner" (tokens {corner}) and
    "Salad Shop" (tokens {salad, shop}) are dropped when the caller lists those words; "Paris
    Baguette" survives because "paris" is not generic. The caller's set is the load-bearing input --
    the module will not decide for itself that a word is common, because that decision is exactly the
    one that produced 168 false positives for a brand called "Salad Shop" (§4.6.4.6).
    """
    toks = tokenise(name)
    return bool(toks) and all(t in generic_tokens for t in toks)


DEFAULT_GENERIC = frozenset({
    # The measured cases (§4.6.4.6): words that a real brand in the corpus was named after, and words
    # that appeared inside ordinary review prose. Supplied to the test as a caller's set; the function
    # still takes `generic` as a required argument.
    "crunch", "corner", "grains", "daily", "salad", "shop", "stuff", "super",
})


# ---------------------------------------------------------------------------------------------------
# 3. CORPUS TYPE -- refuse chrome and bot walls before counting anything
# ---------------------------------------------------------------------------------------------------

# §4.6.4.7: Clutch returned an 813-character shell; DesignRush 1,465 and TechBehemoths 1,590 chars, and
# BOTH WERE NAVIGATION MENUS. A block page rendering as ordinary text is the protocol's worst
# documented failure. Refusing is always the safe direction here: a refusal is a STATED LIMIT, whereas
# counting a menu produces a fabricated finding.
BOT_WALL_MARKERS = (
    "just a moment", "enable javascript", "verify you are human", "checking your browser",
    "attention required", "access denied", "403 forbidden", "are you a robot", "unusual traffic",
    "captcha", "cloudflare", "ray id", "please enable cookies", "ddos protection", "request blocked",
)

NAV_PHRASES = (
    "about us", "contact us", "privacy policy", "terms of service", "web design companies",
    "ppc agencies", "branding agencies", "all rights reserved", "sign up", "log in", "read more",
    "view all", "cookie policy", "follow us", "submit your",
)
NAV_TOKENS = frozenset({
    "home", "about", "contact", "agencies", "agency", "services", "directory", "pricing", "careers",
    "sitemap", "login", "register", "advertise", "submit", "compare", "faq", "blog", "menu", "search",
    "categories", "companies", "company", "post", "job", "jobs", "next", "previous",
})
_SEP_RE = re.compile(r"\s[/|\u00b7\u00bb]\s")

MIN_REVIEWS = 5        # ⚠ uncalibrated default, and said so. A positioning claim needs a floor.
MIN_TOKENS = 100       # §4.6.4.4: "too few reviews to test at all -- report the count, refuse".
CHROME_SHARE = 0.6     # share of entries that must look like link strips before the corpus is chrome
EXCERPT_MAX = 220
MAX_EXCERPTS_PER_RIVAL = 3


def _chrome_reason(review: str) -> str | None:
    """Why this entry looks like navigation chrome rather than review prose, or None.

    Three signals, all taken from the measured failure shape. A genuine review normally ends a
    sentence, so the separator/label rules require NO sentence punctuation -- that is what keeps
    "great service, good prices" from being read as a menu.
    """
    t = review.strip()
    if not t:
        return None
    low = t.lower()
    toks = set(tokenise(t))
    labels = {p for p in NAV_PHRASES if p in low} | {tok for tok in NAV_TOKENS if tok in toks}
    ended = bool(re.search(r"[.!?][\"')\]]?\s*$", t))
    if len(_SEP_RE.findall(t)) >= 2 and not ended:
        return "separator strip (2+ ' / ' or ' | ' joins) with no sentence punctuation"
    if len(labels) >= 3 and not ended:
        return "3+ navigation labels with no sentence punctuation"
    if len(t) < 40 and not ended and labels:
        return "short fragment carrying a navigation label"
    return None


def _as_list(value) -> list:
    """A list of strings, and never a silent per-character split of a bare string."""
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, Mapping):
        return list(value.keys())
    try:
        return list(value)
    except TypeError:
        return [value]


def corpus_quality(reviews, *, min_reviews: int = MIN_REVIEWS, min_tokens: int = MIN_TOKENS) -> dict:
    """Is this corpus actually review prose about the brand? Order matters, and is deliberate.

    empty -> bot_wall -> navigation_chrome -> too_thin -> ok

    Chrome and walls are tested BEFORE thinness because a small chrome shell must be named as chrome,
    not filed as "too few reviews" (§4.6.4.7's Clutch shell was 813 characters -- not obviously thin,
    and entirely a menu). Naming the CAUSE is the point; "0 reviews" with no reason is the silent
    failure the protocol forbids.
    """
    items = [r.strip() for r in _as_list(reviews) if isinstance(r, str) and r.strip()]
    n_tokens = sum(len(tokenise(r)) for r in items)
    out = {"status": "ok", "reason": "the corpus is review prose", "n_reviews": len(items),
           "n_tokens": n_tokens, "n_chrome": 0, "wall_markers": [], "chrome_examples": []}

    if not items:
        out.update(status="empty", reason="no review text was supplied, so there is no corpus to test")
        return out

    joined = "\n".join(items).lower()
    walls = [m for m in BOT_WALL_MARKERS if m in joined]
    if walls:
        out.update(status="bot_wall", wall_markers=walls,
                   reason="the text carries bot-wall / interstitial markers (%s), so it is a block "
                          "page and not customer voice" % ", ".join(walls))
        return out

    chrome = [i for i, r in enumerate(items) if _chrome_reason(r)]
    out["n_chrome"] = len(chrome)
    out["chrome_examples"] = [items[i][:80] for i in chrome[:3]]
    if len(chrome) >= 2 and len(chrome) / len(items) >= CHROME_SHARE:
        out.update(status="navigation_chrome",
                   reason="%d of %d entries look like navigation chrome rather than review prose "
                          "(e.g. %r) -- this is the shape that rendered as a plausibly fake vendor "
                          "list in the measured Clutch/DesignRush case (spec 4.6.4.7)"
                          % (len(chrome), len(items), out["chrome_examples"][0]))
        return out

    if len(items) < min_reviews or n_tokens < min_tokens:
        out.update(status="too_thin",
                   reason="only %d review(s) / %d token(s) were supplied; the floor is %d / %d. "
                          "Spec 4.6.4.4: report the count and refuse the verdict rather than pressing "
                          "a thin corpus into service" % (len(items), n_tokens, min_reviews, min_tokens))
        return out
    return out


# ---------------------------------------------------------------------------------------------------
# 4. THE ATTRIBUTION TEST (§4.6.4.4 Test 2)
# ---------------------------------------------------------------------------------------------------

def _sentence_at(text: str, start: int, end: int) -> str:
    """The sentence containing [start, end) -- readable evidence, cut to a bounded length."""
    left = max(text.rfind(".", 0, start), text.rfind("!", 0, start), text.rfind("?", 0, start))
    rights = [i for i in (text.find(".", end), text.find("!", end), text.find("?", end)) if i != -1]
    right = min(rights) + 1 if rights else len(text)
    sentence = text[left + 1:right].strip() or text.strip()
    return sentence[:EXCERPT_MAX] + ("..." if len(sentence) > EXCERPT_MAX else "")


def attribution(reviews, brand: str, rivals, generic, *,
                min_reviews: int = MIN_REVIEWS, min_tokens: int = MIN_TOKENS) -> dict:
    """How many reviews name a RIVAL -- with the three measured exclusions, and no invented zero.

    Returns a dict whose `counts` maps every rival that survived the exclusions to the number of
    REVIEWS naming it (0 included, so an absence is legible rather than missing), `mentions` counts
    total occurrences, and `excerpts` carries the matching sentence(s) with their review index.
    `excluded` records WHY a supplied rival was dropped -- self-alias of the brand, or a declared
    common word -- so a drop is auditable and never silent.

    A refusal (`status: "refused"`) is returned, with empty counts, when the corpus is not review
    prose or when no brand was supplied: without the brand there is no way to exclude self-match, and
    an unexcluded self-match is precisely the defect that produced 9 fake rival mentions (§4.6.4.5).
    """
    reviews = _as_list(reviews)
    out = {
        "status": "ok", "reason": None, "brand": brand, "n_reviews": 0,
        "rivals_supplied": [], "rivals_used": [],
        "excluded": {"brand_self_alias": [], "generic_common_word": []},
        "counts": {}, "mentions": {}, "excerpts": {},
        "attributing_review_indexes": [], "n_reviews_naming_rival": 0, "evidence_present": False,
        "quality": corpus_quality(reviews, min_reviews=min_reviews, min_tokens=min_tokens),
    }

    if not isinstance(brand, str) or not brand.strip():
        out.update(status="refused", reason="no_brand",
                   reason_text="no brand was supplied, so the brand's own name cannot be excluded "
                               "from its own reviews -- refusing rather than reporting a self-match "
                               "as a rival mention (spec 4.6.4.5 defect 4)")
        return out

    quality = out["quality"]
    if quality["status"] != "ok":
        out.update(status="refused", reason=quality["status"], reason_text=quality["reason"])
        return out

    brand_re = _brand_mask_pattern(brand)
    if brand_re is None:
        out.update(status="refused", reason="no_brand",
                   reason_text="the supplied brand reduced to no tokens, so it cannot be masked")
        return out

    generic_tokens: set[str] = set()
    for word in _as_list(generic):
        generic_tokens.update(tokenise(word))

    supplied, seen = [], set()
    for raw in sorted(_as_list(rivals)):
        if not isinstance(raw, str) or not raw.strip():
            continue
        key = raw.strip().lower()
        if key in seen:
            continue
        seen.add(key)
        supplied.append(raw.strip())
    out["rivals_supplied"] = supplied

    kept = []
    for name in supplied:
        if _is_self_alias(name, brand):
            out["excluded"]["brand_self_alias"].append(name)
        elif _is_generic(name, generic_tokens):
            out["excluded"]["generic_common_word"].append(name)
        else:
            kept.append(name)
    out["rivals_used"] = kept

    counts: dict[str, int] = {}
    mentions: dict[str, int] = {}
    excerpts: dict[str, list] = {}
    patterns = {name: _name_pattern(name) for name in kept}

    for i, review in enumerate(reviews):
        if not isinstance(review, str) or not review.strip():
            continue
        out["n_reviews"] += 1
        # ⚠ EXCLUSION (a): mask the brand out of its own review, SAME LENGTH so excerpt offsets stay
        # valid. Without this, a rival name ending inside the brand name ("Tiong Bahru" in "Tiong
        # Bahru Bakery") matches text the customer wrote about the brand itself.
        masked = brand_re.sub(lambda m: "z" * len(m.group(0)), review)
        named = []
        for name in kept:
            rx = patterns[name]
            if rx is None:                            # unreachable: kept names always tokenise
                continue
            spans = list(rx.finditer(masked))
            if not spans:
                continue
            named.append(name)
            counts[name] = counts.get(name, 0) + 1
            mentions[name] = mentions.get(name, 0) + len(spans)
            bucket = excerpts.setdefault(name, [])
            if len(bucket) < MAX_EXCERPTS_PER_RIVAL:
                start, end = spans[0].span()
                bucket.append({"review_index": i, "excerpt": _sentence_at(review, start, end)})
        if named:
            out["attributing_review_indexes"].append(i)

    # Rebuild in `kept` order so the output is byte-stable no matter which review matched first.
    out["counts"] = {name: counts.get(name, 0) for name in kept}
    out["mentions"] = {name: mentions.get(name, 0) for name in kept}
    out["excerpts"] = {name: excerpts.get(name, []) for name in kept}
    out["n_reviews_naming_rival"] = len(out["attributing_review_indexes"])
    out["evidence_present"] = out["n_reviews_naming_rival"] > 0
    return out


# ---------------------------------------------------------------------------------------------------
# 5. TEST 1 -- vocabulary overlap (necessary, NOT sufficient)
# ---------------------------------------------------------------------------------------------------

STOPWORDS = frozenset({
    "the", "a", "an", "and", "or", "of", "to", "for", "in", "on", "at", "by", "with", "we", "our",
    "you", "your", "it", "is", "are", "be", "as", "that", "this", "from", "not", "no", "all", "every",
    "than", "then", "so", "but", "if", "its", "their", "they", "them", "us", "more", "most", "can",
    "will", "just", "only", "own", "one", "two", "out", "up", "down", "over", "into", "about", "after",
    "before", "when", "where", "how", "what", "which", "who", "why", "do", "does", "did", "has", "have",
    "had", "was", "were", "been", "being", "my", "me", "i", "he", "she", "his", "her", "him", "there",
})


def claim_terms(claim: str) -> list[str]:
    """The distinctive terms of a published claim: content tokens, deduped, sorted.

    ⚠ A fixed stopword list and a literal whole-word match, both stated limits: a claim term that is a
    stopword is dropped, and "baked" does not match "bake". §4.6.4.5 limit 2 applies squarely here --
    a keyword MISS is weak evidence and must never be read as "the claim is unperceived".
    """
    seen = []
    for tok in tokenise(claim):
        if len(tok) >= 3 and tok not in STOPWORDS and tok not in seen:
            seen.append(tok)
    return sorted(seen)


def _term_present(term: str, masked_text: str) -> bool:
    rx = _name_pattern(term)
    return bool(rx and rx.search(masked_text))


# ---------------------------------------------------------------------------------------------------
# 6. THE VERDICT (§4.6.4.1's three-way rule)
# ---------------------------------------------------------------------------------------------------

V_AGREES = "AGREES"
V_DISAGREES = "DISAGREES"
V_INCONCLUSIVE = "INCONCLUSIVE"
V_NOT_APPLICABLE = "NOT_APPLICABLE"
V_PRECONDITION_UNKNOWN = "PRECONDITION_UNKNOWN"
V_REFUSED = "REFUSED"
VERDICTS = (V_AGREES, V_DISAGREES, V_INCONCLUSIVE, V_NOT_APPLICABLE, V_PRECONDITION_UNKNOWN, V_REFUSED)

CLAIM_VS_MIND = "claim_vs_mind"
CLAIM_VS_CLAIMS = "claim_vs_claims"

# §4.6.4.1, verbatim in substance: the limit is STATED, never smoothed over.
CLAIM_VS_CLAIMS_LIMIT = ("no independent customer evidence found, so the claim could not be tested "
                         "against what customers actually think (spec 4.6.4.1)")

POST_PURCHASE_LIMIT = ("attribution is absent from this corpus BY CONSTRUCTION, not by scarcity: a "
                       "post-purchase form asks how the visit was, so its authors had already chosen "
                       "and do not narrate the alternative they rejected (measured: 0 of 59 managed-IT "
                       "reviews, spec 4.6.4.7). More volume will not produce it.")

WEAK_KEYWORD_LIMIT = ("weak evidence, and it must be stated: a keyword miss is not proof that the "
                       "claim is unperceived -- a reviewer may write 'the croissant is way better than "
                       "X' without ever using the word craft (spec 4.6.4.5 limit 2). Flag for a human "
                       "read, not a proven market disagreement.")

NOTES = (
    "Test 1 (vocabulary overlap) is necessary but NOT sufficient; Test 2 (attribution) is the "
    "discriminator (spec 4.6.4.4).",
    "A review that names no competitor is category talk, and category talk corroborates nobody "
    "(spec 4.6.4.4).",
    "INCONCLUSIVE is not a divergence finding; only DISAGREES raises the flag (spec 4.6.4.5).",
    "Every branch states its limit; none is resolved by guessing (spec 4.6.4.1).",
)


def render_finding(verdict: dict) -> str:
    """The finding in plain English, as a consequence rather than a metric (§4.6.4.1)."""
    v = verdict.get("verdict")
    brand = verdict.get("brand")
    claim = verdict.get("published_claim")
    att = verdict.get("attribution") or {}
    n = (verdict.get("corpus") or {}).get("n_reviews", 0)
    k = att.get("n_reviews_naming_rival", 0)
    named = [name for name, c in (att.get("counts") or {}).items() if c]

    if v == V_AGREES:
        return ('%s publishes "%s". %d of %d reviews name a rival and use the claim\'s own language '
                '(%s), so the position is attributed to this brand AGAINST named alternatives (%s) -- '
                'which is what makes it a position rather than category talk. The position is real and '
                'supported at this corpus.' % (brand, claim, k, n,
                                               ", ".join(verdict["test1_vocabulary_overlap"]["found_terms"]),
                                               ", ".join(named)))
    if v == V_DISAGREES:
        return ('FLAG -- %s publishes "%s", and %d of %d reviews do name a rival (%s), so comparison '
                'exists here; but none of those reviews uses the claim\'s language. We say we are '
                '"%s"; our customers\' own words for this brand come from a different vocabulary. %s'
                % (brand, claim, k, n, ", ".join(named), claim, WEAK_KEYWORD_LIMIT))
    if v == V_INCONCLUSIVE:
        return ('%d reviews were read for %s and %d of them names a rival, against %d named '
                'alternative(s) considered. By the attribution test a review with no competitor in it '
                'is category talk, and category talk corroborates nobody -- so the honest result is '
                'INCONCLUSIVE. This is NOT a claim/mind divergence and must not be reported as one.'
                % (n, brand, k, len(att.get("rivals_used") or [])))
    if v == V_NOT_APPLICABLE:
        return ('%s is a post-purchase review form: it asks how the visit was, not what alternatives '
                'were considered. %s No mind test was run; the claim falls to the claim-vs-claims '
                'branch (spec 4.6.3), and the limit is stated: %s.'
                % (verdict.get("platform"), POST_PURCHASE_LIMIT, CLAIM_VS_CLAIMS_LIMIT))
    if v == V_PRECONDITION_UNKNOWN:
        return ('"%s" is not in the comparison-form registry the caller supplied, so whether its '
                'review form solicits alternatives is UNKNOWN -- the module does not guess, because '
                'the form is the discriminator (spec 4.6.4.7). The attribution test was not run; the '
                'claim falls to the claim-vs-claims branch with the limit stated: %s.'
                % (verdict.get("platform"), CLAIM_VS_CLAIMS_LIMIT))
    return ('REFUSED (%s): %s No verdict is issued, and the claim falls to the claim-vs-claims branch '
            'with the limit stated: %s.'
            % ((verdict.get("corpus") or {}).get("status"), (verdict.get("corpus") or {}).get("reason"),
               CLAIM_VS_CLAIMS_LIMIT))


def mind_verdict(published_claim: str, reviews, brand: str, rivals, generic,
                 platform: str, registry: dict, *,
                 min_reviews: int = MIN_REVIEWS, min_tokens: int = MIN_TOKENS) -> dict:
    """Sean's three-way rule for one brand: is the published claim what the customers think?

    THE ORDER, AND IT IS BINDING (§4.6.4.1 then §4.6.4.7 then §4.6.4.4):
      1. No usable corpus -> REFUSED, fall to CLAIM-VS-CLAIMS, limit stated.
      2. Precondition NO -> NOT_APPLICABLE, fall to CLAIM-VS-CLAIMS, limit stated.
      3. Precondition UNKNOWN -> PRECONDITION_UNKNOWN, fall to CLAIM-VS-CLAIMS, limit stated.
         (Never NOT_APPLICABLE: that asserts the corpus is non-comparative, which is not known.)
      4. Precondition YES + attribution found -> AGREES, or DISAGREES when the attributing reviews do
         not use the claim's language. DISAGREES is the flag, and it always carries weak_evidence.
      5. Precondition YES + no attribution -> INCONCLUSIVE, explicitly NOT a divergence.

    `divergence_flag` is True on exactly one verdict, DISAGREES. Vocabulary overlap alone can never
    produce AGREES, because attribution is required to get this far.

    Deterministic: no clock, no randomness, no network; the result contains no timestamp.
    """
    reviews = _as_list(reviews)
    quality = corpus_quality(reviews, min_reviews=min_reviews, min_tokens=min_tokens)
    out = {
        "verdict": None,
        "brand": brand,
        "platform": platform,
        "published_claim": published_claim,
        "precondition": can_mind_test(platform, registry),
        "branch": CLAIM_VS_MIND,
        "divergence_flag": False,
        "weak_evidence": False,
        "limit": None,
        "corpus": quality,
        "attribution": None,
        "test1_vocabulary_overlap": {"status": "not_run", "claim_terms": [], "found_terms": []},
        "test2_attribution": {"status": "not_run", "n_reviews_naming_rival": 0, "rivals_named": []},
        "notes": list(NOTES),
    }

    # --- 1. no usable corpus ------------------------------------------------------------------------
    if quality["status"] != "ok":
        out["verdict"] = V_REFUSED
        out["branch"] = CLAIM_VS_CLAIMS
        out["limit"] = CLAIM_VS_CLAIMS_LIMIT
        out["finding"] = render_finding(out)
        return out

    # --- 2/3. the precondition, read from the CALLER's registry -------------------------------------
    if out["precondition"] != CAN_YES:
        out["verdict"] = V_NOT_APPLICABLE if out["precondition"] == CAN_NO else V_PRECONDITION_UNKNOWN
        out["branch"] = CLAIM_VS_CLAIMS
        out["limit"] = CLAIM_VS_CLAIMS_LIMIT
        out["finding"] = render_finding(out)
        return out

    # --- 4. the attribution test --------------------------------------------------------------------
    att = attribution(reviews, brand, rivals, generic, min_reviews=min_reviews, min_tokens=min_tokens)
    out["attribution"] = att
    if att["status"] != "ok":
        out["verdict"] = V_REFUSED
        out["branch"] = CLAIM_VS_CLAIMS
        out["limit"] = CLAIM_VS_CLAIMS_LIMIT
        out["finding"] = render_finding(out)
        return out

    named = [name for name, count in att["counts"].items() if count]
    out["test2_attribution"] = {
        "status": "attributed" if att["evidence_present"] else "none",
        "n_reviews_naming_rival": att["n_reviews_naming_rival"],
        "rivals_named": named,
        "excluded": att["excluded"],
    }

    if not att["evidence_present"]:
        # YES + no attribution -> INCONCLUSIVE. NOT a divergence finding (§4.6.4.5).
        out["verdict"] = V_INCONCLUSIVE
        out["limit"] = ("no review names a rival, so the corpus cannot settle a positioning question; "
                        "this is category talk, not disagreement (spec 4.6.4.4)")
        out["finding"] = render_finding(out)
        return out

    # Test 1, run over the ATTRIBUTING reviews only -- the ones that carry the comparison.
    terms = claim_terms(published_claim)
    attributing = [r for i, r in enumerate(reviews)
                   if isinstance(r, str) and r.strip() and i in att["attributing_review_indexes"]]
    brand_re = _brand_mask_pattern(brand)
    masked_reviews = [brand_re.sub(lambda m: "z" * len(m.group(0)), r) if brand_re else r
                      for r in attributing]
    found = sorted({t for t in terms
                    if any(_term_present(t, m) for m in masked_reviews)})
    out["test1_vocabulary_overlap"] = {
        "status": "matched" if found else ("no_overlap" if terms else "no_claim_terms"),
        "claim_terms": terms,
        "found_terms": found,
    }

    if found:
        out["verdict"] = V_AGREES
    else:
        out["verdict"] = V_DISAGREES
        out["divergence_flag"] = True
        out["weak_evidence"] = True
        out["limit"] = WEAK_KEYWORD_LIMIT
    out["finding"] = render_finding(out)
    return out


# ---------------------------------------------------------------------------------------------------
# 7. SELF-TEST -- SYNTHETIC fixtures only. No network. Every corpus below is written by hand and is
#    labelled here as synthetic; none of it is captured customer data.
# ---------------------------------------------------------------------------------------------------

def _fixtures() -> dict:
    return {
        # Brand naming ITSELF repeatedly, naming no rival (§4.6.4.5 defect 4's shape).
        "self_naming": [
            "Tiong Bahru Bakery on Eng Hoon Street has been an iconic cafe in the area for years and "
            "I walk past it daily on my way to work.",
            "Tiong Bahru Bakery keeps a good sourdough and the seating upstairs is quiet enough to "
            "work in for an hour without being bothered.",
            "I have been going to Tiong Bahru Bakery since it opened and the croissants are still the "
            "only reason I keep coming back on weekends.",
            "Tiong Bahru Bakery gets busy at the weekend so I usually arrive early, take a loaf home "
            "and slice it for the family's breakfast.",
            "The team at Tiong Bahru Bakery know my order by now and the coffee is reliable every "
            "single morning before work starts.",
            "Tiong Bahru Bakery has air conditioning, plenty of seats near the window, and the bread "
            "is baked through the day so it is warm.",
        ],
        # Common-word noise in prose + two genuine rival attributions, the second in lower case and
        # a plural decoy that whole-word matching must NOT count.
        "comparison": [
            "The loaf they sold me lacked crunch and the crust went soft by the afternoon, which was "
            "disappointing for the price they charge.",
            "Nice little shop in the bottom left corner of the mall with friendly staff, fair prices "
            "and a short queue at lunchtime.",
            "I have been buying bread here for two years and the grain bowl next door is better "
            "value, though the coffee here is stronger.",
            "I still prefer Paris Baguette for pastries, but their sourdough is better here and it "
            "keeps longer than anything else on the street.",
            "we switched from paris baguette to this place and never looked back, because the crust "
            "stays crisp and the staff remember my order.",
            "Paris baguettes elsewhere are perfectly fine but the bread here keeps for three days in "
            "a paper bag, which matters when I shop weekly.",
        ],
        # A caller's generic set deliberately missing salad/shop -- the module must NOT guess.
        "salad_phrase": [
            "we went to the Salad Shop down the road because it was open later than this place on a "
            "weeknight and we were hungry.",
            "the Salad Shop nearby does the same bowl for two dollars less, so I only come here when "
            "they are closed on Sundays.",
            "I compared it with the salad shop across the street and this one is quieter, though the "
            "portions are smaller and the queue is longer.",
            "The staff here are quick and the seating is comfortable, so it is a decent place to sit "
            "for half an hour during a busy working day.",
            "Prices are fair for the area and the coffee is strong, which is really all I need in the "
            "morning before the office fills up.",
            "It is a reliable weekday lunch spot with a short queue, friendly service and clean "
            "tables, and I have never had a bad meal here.",
        ],
        # Service impressions: about the VISIT, naming no rival, using no claim language.
        "service_impressions": [
            "The staff were friendly and the queue moved quickly at lunchtime, and the cashier "
            "remembered my usual order from the week before.",
            "Great service every time I come in, the team is quick at the counter and the place is "
            "always spotless when I arrive in the morning.",
            "The bread was still warm when I got it, the shop was clean, and the whole visit took "
            "under five minutes from door to door.",
            "Nice seating and air conditioning, the staff were helpful with my questions, though the "
            "prices are a bit high for this part of town.",
            "Friendly team, quick service, and the croissant was fresh that morning; I come here most "
            "weekdays before work and never wait long.",
            "Good place to sit and work for an hour, the coffee was strong, and the people at the "
            "counter were genuinely helpful about the wifi password.",
        ],
        # Attribution present AND the claim's language present -> AGREES.
        "attributed_with_claim_language": [
            "We switched from BreadTalk to this bakery because their artisan sourdough is baked by "
            "hand and you can taste the difference in the crust.",
            "I used to buy from Four Leaves every morning but the artisan loaves here are baked by "
            "hand, so the crumb is far better and it keeps longer.",
            "After trying BreadTalk and Four Leaves I stay with this bakery: the artisan bread is "
            "baked by hand and it shows in the crust every single time.",
            "My family moved here from Four Leaves because the sourdough here is proper artisan "
            "bread, baked by hand every night and cooled before slicing.",
            "Compared with BreadTalk, the artisan sourdough at this bakery is baked by hand and keeps "
            "its crust for two days in a paper bag.",
            "I go here instead of Four Leaves now; the artisan loaves are baked by hand and the staff "
            "remember my order after a few visits.",
        ],
        # Attribution present but the reviewers' vocabulary is a different one -> DISAGREES (flagged).
        "attributed_other_vocabulary": [
            "We switched from BreadTalk to this bakery because they are cheaper and much quicker at "
            "lunchtime when the office empties out.",
            "I used to buy from Four Leaves but this place is cheaper and the queue moves faster, so "
            "I get back to my desk sooner.",
            "Compared with BreadTalk the prices here are lower and the staff are friendlier, which "
            "matters more to me than anything else.",
            "I go here instead of Four Leaves because it is closer to my office, open earlier and "
            "never runs out of the white loaf.",
            "After trying BreadTalk and Four Leaves I stay here: cheaper, faster, open on Sundays and "
            "the parking outside is easy.",
            "My family moved here from Four Leaves because the parking is easier, the queue is "
            "shorter and the whole trip takes half the time.",
        ],
        # The measured chrome shape (Clutch / DesignRush / TechBehemoths: menus only).
        "nav_chrome": [
            "AGENCIES / Web Design Companies / PPC Agencies / Branding Agencies",
            "Home | About Us | Contact | Privacy Policy | Terms of Service",
            "Digital Marketing / SEO Agencies / Social Media Agencies / Web Development Companies",
            "Directory / Find Companies / Compare Reviews / Submit Your Agency",
            "Login | Sign Up | Post a Job | Advertise With Us | Sitemap",
        ],
        "bot_wall": [
            "Just a moment...",
            "Enable JavaScript and cookies to continue",
            "Verify you are human",
            "Checking your browser before accessing clutch.co",
        ],
        "too_thin": ["Great bread.", "Lovely staff."],
        "empty": [],
    }


def _self_test() -> int:
    """Every fixture is synthetic. Prints PASS/FAIL per check and a final count."""
    fx = _fixtures()
    reg = {"google_maps": False, "trustpilot": False, "yelp": False,
           "g2": True, "capterra": True, "clutch": True}
    generic = set(DEFAULT_GENERIC)
    claim = "artisan sourdough baked by hand"
    brand = "Nordic Bakehouse"
    results = []

    def check(label, ok, detail=""):
        ok = bool(ok)
        results.append((label, ok))
        print("%s  %-46s %s" % ("PASS" if ok else "FAIL", label, detail))

    # 1-4: the precondition
    check("01 PRECONDITION_NO_GOOGLE_MAPS", can_mind_test("google_maps", reg) == CAN_NO,
          can_mind_test("google_maps", reg))
    check("02 PRECONDITION_YES_G2", can_mind_test("g2", reg) == CAN_YES, can_mind_test("g2", reg))
    check("03 PRECONDITION_UNKNOWN_UNREGISTERED",
          can_mind_test("some_forum", reg) == CAN_UNKNOWN
          and can_mind_test("anywhere", {}) == CAN_UNKNOWN
          and can_mind_test("anywhere", None) == CAN_UNKNOWN,
          "absent registry key, empty registry, None registry -> all UNKNOWN")
    check("04 PRECONDITION_NEVER_GUESSES_FROM_VALUE",
          can_mind_test("odd", {"odd": None}) == CAN_UNKNOWN
          and can_mind_test("odd", {"odd": "yes"}) == CAN_UNKNOWN
          and can_mind_test("odd", {"odd": {"unrelated": True}}) == CAN_UNKNOWN
          and can_mind_test("odd", {"odd": {"solicits_alternatives": True}}) == CAN_YES
          and can_mind_test("GOOGLE_MAPS", reg) == CAN_NO,
          "uninterpretable values -> UNKNOWN; rich record honoured; key case-insensitive")

    # 5-6: self-match, the defect that produced 9 fake rival mentions
    self5 = attribution(fx["self_naming"], "Tiong Bahru Bakery", ["Tiong Bahru", "Paris Baguette"],
                        generic)
    check("05 SELF_MATCH_BRAND_REPEATED",
          self5["status"] == "ok" and self5["counts"] == {"Paris Baguette": 0}
          and self5["n_reviews_naming_rival"] == 0
          and self5["excluded"]["brand_self_alias"] == ["Tiong Bahru"],
          "6/6 reviews name the brand itself; rivals counted=%r, self-alias dropped=%r"
          % (self5["counts"], self5["excluded"]["brand_self_alias"]))
    self6 = attribution(fx["self_naming"], "Tiong Bahru", ["Bahru Bakery"], generic)
    check("06 SELF_MATCH_MASKED_ACROSS_BRAND_NAME",
          self6["status"] == "ok" and self6["counts"] == {"Bahru Bakery": 0}
          and self6["n_reviews_naming_rival"] == 0,
          "'Bahru Bakery' is not a token-subset of 'Tiong Bahru', so only the text mask can stop it "
          "matching inside 'Tiong Bahru Bakery' -- counted=%r" % self6["counts"])

    # 7-9: generic words, whole-word matching, and the module's refusal to guess genericity
    comp = attribution(fx["comparison"], brand, ["Crunch", "Corner", "Paris Baguette"], generic)
    check("07 GENERIC_WORD_RIVAL_EXCLUDED",
          comp["status"] == "ok"
          and comp["excluded"]["generic_common_word"] == ["Corner", "Crunch"]
          and comp["counts"] == {"Paris Baguette": 2}
          and comp["mentions"] == {"Paris Baguette": 2},
          "dropped=%r kept counts=%r" % (comp["excluded"]["generic_common_word"], comp["counts"]))
    check("08 WHOLE_WORD_CASE_INSENSITIVE",
          comp["mentions"]["Paris Baguette"] == 2 and comp["n_reviews_naming_rival"] == 2
          and comp["attributing_review_indexes"] == [3, 4]
          and comp["excerpts"]["Paris Baguette"][0]["review_index"] == 3,
          "lower-case match counted; the plural 'Paris baguettes' decoy (review 5) is NOT counted; "
          "excerpt from review 3: %r" % comp["excerpts"]["Paris Baguette"][0]["excerpt"][:60])
    salad = attribution(fx["salad_phrase"], brand, ["Salad Shop"], {"crunch"})
    check("09 GENERIC_PHRASE_BRAND_IS_THE_CALLERS_LIMIT",
          salad["status"] == "ok" and salad["counts"] == {"Salad Shop": 3}
          and salad["excluded"]["generic_common_word"] == [],
          "'Salad Shop' IS the generic phrase and defeats frequency filtering (spec 4.6.4.6); with "
          "salad/shop absent from the caller's generic set it is counted -- the module does not guess: "
          "%r" % salad["counts"])

    # 10: no brand -> refuse, because self-match cannot be excluded
    nobrand = attribution(fx["comparison"], "", ["Paris Baguette"], generic)
    check("10 BLANK_BRAND_REFUSED",
          nobrand["status"] == "refused" and nobrand["reason"] == "no_brand" and nobrand["counts"] == {},
          nobrand["reason_text"][:70])

    # 11-13: the three-way outcome's non-mind branches
    inc = mind_verdict(claim, fx["service_impressions"], brand, ["Paris Baguette"], generic, "g2", reg)
    check("11 INCONCLUSIVE_NO_ATTRIBUTION",
          inc["verdict"] == V_INCONCLUSIVE and inc["divergence_flag"] is False
          and inc["branch"] == CLAIM_VS_MIND and inc["precondition"] == CAN_YES
          and inc["test2_attribution"]["status"] == "none",
          "verdict=%s divergence_flag=%s" % (inc["verdict"], inc["divergence_flag"]))
    gm = mind_verdict(claim, fx["service_impressions"], brand, ["Paris Baguette"], generic,
                      "google_maps", reg)
    check("12 NOT_APPLICABLE_GOOGLE_MAPS",
          gm["verdict"] == V_NOT_APPLICABLE and gm["branch"] == CLAIM_VS_CLAIMS
          and gm["precondition"] == CAN_NO and gm["divergence_flag"] is False
          and gm["limit"] == CLAIM_VS_CLAIMS_LIMIT
          and "no independent customer evidence found" in gm["finding"],
          "verdict=%s branch=%s limit stated=%s" % (gm["verdict"], gm["branch"], bool(gm["limit"])))
    unk = mind_verdict(claim, fx["service_impressions"], brand, ["Paris Baguette"], generic,
                       "some_forum", reg)
    check("13 PRECONDITION_UNKNOWN_VERDICT",
          unk["verdict"] == V_PRECONDITION_UNKNOWN and unk["branch"] == CLAIM_VS_CLAIMS
          and unk["precondition"] == CAN_UNKNOWN and unk["verdict"] != V_NOT_APPLICABLE,
          "unregistered platform is UNKNOWN, and is NOT silently treated as non-comparative")

    # 14-15: the mind branch -- agreement, and the flag
    agr = mind_verdict(claim, fx["attributed_with_claim_language"], brand, ["BreadTalk", "Four Leaves"],
                       generic, "g2", reg)
    check("14 AGREES_ATTRIBUTION_AND_OVERLAP",
          agr["verdict"] == V_AGREES and agr["divergence_flag"] is False
          and agr["test2_attribution"]["status"] == "attributed"
          and agr["test2_attribution"]["n_reviews_naming_rival"] == 6
          and agr["test1_vocabulary_overlap"]["status"] == "matched"
          and agr["test1_vocabulary_overlap"]["found_terms"] == ["artisan", "baked", "hand", "sourdough"],
          "verdict=%s rivals_named=%r found_terms=%r"
          % (agr["verdict"], agr["test2_attribution"]["rivals_named"],
             agr["test1_vocabulary_overlap"]["found_terms"]))
    dis = mind_verdict(claim, fx["attributed_other_vocabulary"], brand, ["BreadTalk", "Four Leaves"],
                       generic, "g2", reg)
    check("15 DISAGREES_ATTRIBUTION_WITHOUT_OVERLAP",
          dis["verdict"] == V_DISAGREES and dis["divergence_flag"] is True and dis["weak_evidence"] is True
          and dis["test1_vocabulary_overlap"]["found_terms"] == []
          and "FLAG" in dis["finding"] and "not proof" in dis["limit"],
          "verdict=%s flag=%s weak_evidence=%s (overlap is necessary, so a mismatch still only flags)"
          % (dis["verdict"], dis["divergence_flag"], dis["weak_evidence"]))

    # 16-19: refusals -- no verdict is ever issued from unusable text
    for label, corpus, want in (("16 REFUSED_BOT_WALL", fx["bot_wall"], "bot_wall"),
                                ("17 REFUSED_NAV_CHROME", fx["nav_chrome"], "navigation_chrome"),
                                ("18 REFUSED_EMPTY", fx["empty"], "empty"),
                                ("19 REFUSED_TOO_THIN", fx["too_thin"], "too_thin")):
        r = mind_verdict(claim, corpus, brand, ["Paris Baguette"], generic, "g2", reg)
        q = corpus_quality(corpus)
        check(label,
              r["verdict"] == V_REFUSED and r["branch"] == CLAIM_VS_CLAIMS
              and q["status"] == want and r["limit"] == CLAIM_VS_CLAIMS_LIMIT
              and r["verdict"] not in (V_AGREES, V_DISAGREES, V_INCONCLUSIVE)
              and r["attribution"] is None,
              "quality=%s n=%d" % (q["status"], q["n_reviews"]))
    none_reviews = mind_verdict(claim, None, brand, ["Paris Baguette"], generic, "g2", reg)
    check("18b REFUSED_NONE_CORPUS (no crash)",
          none_reviews["verdict"] == V_REFUSED and none_reviews["corpus"]["status"] == "empty",
          "reviews=None is refused, not iterated")

    # 20: determinism
    a = json.dumps(mind_verdict(claim, fx["attributed_with_claim_language"], brand,
                                ["BreadTalk", "Four Leaves"], generic, "g2", reg),
                   sort_keys=True, ensure_ascii=False)
    b = json.dumps(mind_verdict(claim, fx["attributed_with_claim_language"], brand,
                                ["BreadTalk", "Four Leaves"], generic, "g2", reg),
                   sort_keys=True, ensure_ascii=False)
    c = json.dumps(attribution(fx["comparison"], brand, ["Crunch", "Paris Baguette"], generic),
                   sort_keys=True, ensure_ascii=False)
    d = json.dumps(attribution(fx["comparison"], brand, ["Paris Baguette", "Crunch"], generic),
                   sort_keys=True, ensure_ascii=False)
    check("20 DETERMINISTIC_BYTE_IDENTICAL",
          a == b and c == d and "timestamp" not in a and "generated_at" not in a,
          "same input -> identical bytes; rival argument order does not change the output")

    passed = sum(1 for _, ok in results if ok)
    print("\nSELF-TEST: %d checks, %d passed, %d failed" % (len(results), passed, len(results) - passed))
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(_self_test())
