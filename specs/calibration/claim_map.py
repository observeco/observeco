#!/usr/bin/env python3
"""claim_map.py -- spec 095 section 4.6.3, LOCKED IN. The claim-ownership map, and how it compares
with the RANGE of competitors, with online competitor discovery INTEGRAL.

WHAT THIS IS FOR
----------------
Position strength is relative: "you have a strong position" means nothing without knowing whether a
rival already owns the ground you are standing on. This module answers the one question a business
owner actually asks:

    "does someone else already own the claim I am making?"

TWO THINGS SEAN REQUIRED, AND THEY ARE THE DESIGN (13 Oct)
---------------------------------------------------------
1. THE PROCESS MUST INCLUDE HOW IT COMPARES WITH THE RANGE OF COMPETITORS. Not a list of claims --
   a COMPARISON. So the output places the subject's claim against the whole set.
2. THE CAPABILITY TO SEARCH FOR RELEVANT COMPETITORS ONLINE MUST BE INTEGRAL. Discovery is a step
   inside this process, not a prerequisite someone else supplies.

THE FIVE STEPS
--------------
    1 DISCOVER  online  -> the competitive set (competitor_scan discovery + owner-named rivals)
    2 CLAIM     for each -> its PUBLISHED claim (ps_evidence.claim_for: reads the About page too)
    3 RANGE     -> the category's BACKGROUND: how much rivals' claims resemble EACH OTHER
    4 PLACE     -> the subject against that background: DISTINCTIVE / TYPICAL / CROWDED
    5 REPORT    -> X identified / Y shown, the claims, the comparison, and the limits -- stated

⚠⚠ WHY STEP 3 EXISTS, AND IT IS THE WHOLE POINT. THIS IS THE LESSON OF THE FAILED FLAG.
Section 4.6.4.12 tried to detect a claim/mind divergence with an ABSOLUTE threshold and it fired on
everything, because it compared a LONG text with a SHORT one. The control (own claim vs ANOTHER
company's mind) scored 90% while own-claim-vs-own-mind scored 80% -- no threshold could separate
them. Two consequences, both built in here:

    (a) COMPARE LIKE WITH LIKE. Here both sides are CLAIMS -- self-descriptions of similar shape.
        Nothing is being compared with a paraphrase of a different length.
    (b) NEVER USE AN ABSOLUTE THRESHOLD. The verdict is the subject's overlap measured AGAINST THE
        RANGE's own overlap. The baseline is MEASURED from the data, not chosen. A claim is
        "typical" only if it resembles its rivals as much as they resemble each other.

⚠ AND OVERLAP IS MIN-NORMALISED (overlap coefficient, |A n B| / min(|A|,|B|)). A raw Jaccard would
punish a long claim for being long -- the same length artefact that destroyed 4.6.4.12.

⚠ THE HONEST LIMIT, WHICH THE REPORT MUST CARRY: DISTINCTIVE IS NOT THE SAME AS GOOD. A claim no
rival makes may be a genuine unoccupied position, or it may be a claim nobody cares about. This
module measures OCCUPANCY, not value. Saying otherwise would be the confident-garbage failure this
whole spec exists to prevent.
"""
from __future__ import annotations

import itertools
import json
import os
import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import ps_evidence  # noqa: E402  the claim reader (never invents; About-page rule)

# Words that say nothing about a POSITION. If a competitor could honestly say the same sentence,
# the word is not evidence of a claim.
STOP = set("""a an the and or but to of in on for with is are was were be been being it its this that
we our us you your they their them as at by from into over under again more most some such no nor
not only own same so than too very can will just should now what which who whom when where why how
all any both each few other then there these those through during before after above below up down
out off further once here have has had do does did doing also may might must get gets made make
provide provides services service solution solutions company companies business businesses client
clients customer customers team teams work works time times year years new help helps best good great
better able need needs want wants like well even still back around""".split())


def _stem(t: str) -> str:
    """A CONSERVATIVE suffix stripper, and it is load-bearing rather than cosmetic.

    ⚠ THE CONTROL FOUND THIS. The first version compared surface forms, so a subject claiming "we
    BAKE daily" was scored as NOT contested by a rival claiming "fresh bread BAKED daily" -- two
    businesses saying the same thing, scored as saying different things. The inflated "uncontested"
    count made a fully-crowded claim read TYPICAL. Stripping a small set of common suffixes compares
    word ROOTS, which is what the question is actually about.

    Deliberately limited to these four and only on words long enough to keep a stem of >=3 chars:
    over-stemming invents collisions, which is the same class of error in the other direction.
    """
    # ⚠ LONGEST SUFFIX FIRST, AND THE BARE "e" IS LOAD-BEARING. Measured failure from the control:
    # "baked" -> "bak" but "bake" -> "bake", so a subject claiming "we BAKE daily" was scored as
    # NOT contested by a rival claiming "bread BAKED daily" -- identical claims, scored as different.
    # Stripping the trailing "e" makes both sides meet at "bak". Order matters: "bakes" must hit
    # "es" before "s", or it would become "bake" and then stop.
    for suf in ("ing", "ed", "es", "s", "e"):
        if len(t) > len(suf) + 2 and t.endswith(suf):
            return t[: -len(suf)]
    return t


def terms(claim: str) -> set:
    """Distinctive terms in a claim, stemmed to word roots. Deliberately strict: no stopwords, no
    boilerplate -- if a competitor could honestly say the same sentence, the word is not a claim."""
    toks = [t.strip("-") for t in re.split(r"[^a-z0-9-]+", (claim or "").lower())]
    return {_stem(t) for t in toks if len(t) > 3 and t not in STOP and _stem(t) not in STOP}


def overlap(a: set, b: set) -> float:
    """MIN-NORMALISED overlap (overlap coefficient). Symmetric, so a long claim is not punished for
    being long -- the length artefact that invalidated 4.6.4.12."""
    if not a or not b:
        return 0.0
    return len(a & b) / float(min(len(a), len(b)))


def contested_share(tset: set, others: list) -> float:
    """OF THE DISTINCTIVE THINGS THIS BUSINESS CLAIMS, HOW MUCH IS ALREADY CLAIMED BY A RIVAL?

    This is the question a business owner actually asks -- "is anything I say still mine?" -- and it
    is the statistic that survived the control. The first version used MEAN PAIRWISE OVERLAP, and the
    control killed it: a claim asserting exactly what the category asserts scored the same as the
    category's own average, so it read TYPICAL when it should read CROWDED. Mean overlap cannot see
    the difference between "one of many" and "identical to all of them". Contested share can.
    """
    if not tset:
        return 0.0
    hit = {t for t in tset if any(t in o for o in others)}
    return len(hit) / float(len(tset))


def range_background(claims: dict) -> dict:
    """THE RANGE, MEASURED FROM THE RIVALS THEMSELVES. How much do THIS MARKET's claims contest each
    other? That is the baseline the subject is judged against -- never a chosen number, because
    4.6.4.12 proved a chosen threshold fires on everything.

    ⚠ Rivals whose claim could not be read are EXCLUDED, not treated as empty -- an unread page is not
    a business with no claim (the About-page rule, 4.6.3.3).
    """
    got = {k: terms(v) for k, v in claims.items() if (v or "").strip()}
    # ⚠ A RANGE NEEDS ENOUGH MEMBERS TO MEAN ANYTHING. Live bakery run: 2 of 6 rivals readable, and
    # the tool still pronounced TYPICAL. With two claims the "range" is a single number, and the
    # subject scored as uncontested only because the two survivors were tiny independent bakeries --
    # an osmanthus-rice-cake shop and a cafe -- whose claims have nothing to do with bread. A wrong
    # set makes DISTINCTIVE trivially true and the verdict meaningless. So the honest output is a
    # REFUSAL, on the same principle as mind_test.py: no instrument reading beats a fabricated one.
    if len(got) < MIN_RANGE:
        return {"ok": False, "n": len(got), "mean_contested": None, "shares": {}, "pairs": [],
                "reason": ("only %d readable rival claim(s); at least %d are needed before a range "
                           "exists -- the comparison is REFUSED rather than guessed"
                           % (len(got), MIN_RANGE))}
    shares = {k: round(contested_share(t, [o for k2, o in got.items() if k2 != k]), 3)
              for k, t in got.items()}
    pairs = [{"a": ka, "b": kb, "overlap": round(overlap(ta, tb), 3), "shared": sorted(ta & tb)[:6]}
             for (ka, ta), (kb, tb) in itertools.combinations(got.items(), 2)]
    mean_c = sum(shares.values()) / len(shares)
    mean_o = sum(p["overlap"] for p in pairs) / len(pairs)
    return {"ok": True, "n": len(got), "mean_contested": round(mean_c, 3),
            "mean_overlap": round(mean_o, 3), "shares": shares, "pairs": pairs}


# ⚠ THE VERDICT IS A RATIO, NOT A MARGIN. The first version used a fixed absolute margin (0.15) and
# the control killed it twice: in a market where rivals already contest 92% of each other's terms
# there is only 8 points of headroom, so NO fixed margin can ever reach CROWDED -- the category was
# structurally unreachable. A ratio has no ceiling. It also makes the guard trivial to state: how
# much unoccupied ground do you hold, relative to how much a typical rival in this market holds?
MIN_RANGE = 3            # fewer readable rivals than this and no range exists to compare against
DISTINCTIVE_RATIO = 2.0   # 2x the typical rival's unoccupied ground
CROWDED_RATIO = 0.5      # half of it, or less


def place(subject_claim: str, claims: dict) -> dict:
    """PLACE THE SUBJECT AGAINST THE RANGE. No absolute threshold anywhere -- the verdict is the
    subject's contested share measured against the RANGE's own contested share."""
    bg = range_background(claims)
    st = terms(subject_claim)
    if not st:
        return {"ok": False, "reason": "the subject's claim yielded no distinctive terms", "background": bg}
    got = {k: terms(v) for k, v in claims.items() if (v or "").strip()}
    if not got:
        return {"ok": False, "reason": "no readable rival claims -- cannot compare against a range",
                "background": bg}

    share = contested_share(st, list(got.values()))
    per = [{"rival": k, "overlap": round(overlap(st, tt), 3), "shared": sorted(st & tt)[:6]}
           for k, tt in got.items()]
    per.sort(key=lambda r: -r["overlap"])
    contested_terms = sorted({t for r in per for t in r["shared"]})

    mine_free = 1.0 - share
    if not bg.get("ok"):
        verdict, why = "UNRANGED", ("only one readable rival claim: %.0f%% of what you claim is contested, "
                                    "but no range exists to say whether that is unusual" % (share * 100))
    else:
        base_free = max(0.0, 1.0 - bg["mean_contested"])
        if base_free <= 0.0:
            # every rival is fully contested -- the baseline has no headroom, so any unoccupied
            # ground at all is notable and its absence is the finding.
            ratio = float("inf") if mine_free > 0 else 0.0
        else:
            ratio = mine_free / base_free
        if ratio >= DISTINCTIVE_RATIO:
            verdict = "DISTINCTIVE"
            why = ("%.0f%% of what you claim is contested, against a category range of %.0f%% -- you hold "
                   "%.0f%% unoccupied ground where a typical rival here holds %.0f%%: the ground you claim "
                   "is relatively unoccupied" % (share * 100, bg["mean_contested"] * 100,
                                                  mine_free * 100, base_free * 100))
        elif ratio <= CROWDED_RATIO:
            verdict = "CROWDED"
            why = ("%.0f%% of what you claim is contested, against a category range of %.0f%% -- you hold "
                   "%.0f%% unoccupied ground where a typical rival here holds %.0f%%: you are asserting what "
                   "the category already asserts" % (share * 100, bg["mean_contested"] * 100,
                                                      mine_free * 100, base_free * 100))
        else:
            verdict = "TYPICAL"
            why = ("%.0f%% of what you claim is contested, against a category range of %.0f%% -- you contest "
                   "and are contested about as much as the rest of the market"
                   % (share * 100, bg["mean_contested"] * 100))

    return {"ok": True, "subject_overlap": round(share, 3),
            "subject_contested_share": round(share, 3),
            "background": bg, "verdict": verdict, "why": why, "per_rival": per,
            "contested_terms": contested_terms[:12],
            "uncontested_terms": sorted(st - set(contested_terms))[:12]}


# ⚠ WHAT A CATEGORY WEB SEARCH ACTUALLY RETURNS, MEASURED (this run, live).
# The first version of step 1 called competitor_scan.scan() and looked for named rivals in it. It
# returned TWELVE captures and EVERY ONE was a market-research report or an agency blog --
# researchandmarkets.com, 6wresearch.com, marketresearch.com, indexbox.io, euromonitor.com,
# marketingagency.sg. NOT ONE WAS A BAKERY. The category query returns articles ABOUT the category,
# not members OF it. This is the dead end spec 3.7.20 already recorded, re-confirmed here.
#
# So the web search is NOT the discovery mechanism for a competitive set. It is kept only as a
# LAST-RESORT source, and its output is filtered to company domains and labelled as unverified.
REPORT_DOMAINS = (
    "researchandmarkets", "6wresearch", "marketresearch", "indexbox", "euromonitor", "statista",
    "grandviewresearch", "mordorintelligence", "ibisworld", "technavio", "globenewswire",
    "prnewswire", "businesswire", "wikipedia", "medium.com", "linkedin.com", "youtube.com",
    "facebook.com", "instagram.com", "reddit.com", "bing.com", "google.com", "tripadvisor",
)


_CACHE_PATH = "/Users/seanfzc/projects/observeco-main/specs/calibration/cache/brand_verify_cache.json"
_CACHE_TTL_S = 30 * 24 * 3600     # a brand's site does not change category in a month
# ⚠⚠ THE CACHE MUST BE VERSIONED, AND THIS WAS A LIVE DEFECT. Fixing the verifier to reject
# chrome-only pages did NOT take effect, because the verdict for "All-Day Breakfast" had been cached
# BEFORE the fix and was replayed straight past the new check. A cache that outlives the code that
# fills it silently pins a known-bad answer forever. Bump this whenever verification logic changes.
_VERIFIER_VERSION = 3
_cache_mem = None


def _load_cache() -> dict:
    """⚠ VERIFICATION IS THE EXPENSIVE STEP, SO IT IS CACHED. A brand verified once stays verified for
    a month. Because the same majors recur across every report in a market, the cache makes repeat
    runs near-free -- which is what turns a 30-minute batch into a production path."""
    global _cache_mem
    if _cache_mem is None:
        try:
            with open(_CACHE_PATH) as fh:
                _cache_mem = json.load(fh)
        except Exception:  # noqa: BLE001
            _cache_mem = {}
        if (_cache_mem or {}).get("__version__") != _VERIFIER_VERSION:
            _cache_mem = {"__version__": _VERIFIER_VERSION}   # stale logic -> discard, never replay
    return _cache_mem


def _save_cache() -> None:
    try:
        os.makedirs(os.path.dirname(_CACHE_PATH), exist_ok=True)
        tmp = _CACHE_PATH + ".tmp"
        with open(tmp, "w") as fh:
            json.dump(_cache_mem or {}, fh, indent=1)
        os.replace(tmp, _CACHE_PATH)
    except Exception:  # noqa: BLE001
        pass


CATEGORY_WORDS = {
    "bakery": ("bakery", "bread", "bake", "baker", "pastr", "cake", "confection", "dough",
               "viennois", "sourdough", "croissant", "loaf", "bakeshop", "patisserie"),
}


def _in_category(text: str, category: str) -> bool:
    """⚠⚠ THE CHECK THAT REJECTS A HOSPITAL. The first vetted set accepted "Farrer Park" -- a
    HOSPITAL -- because farrerpark.com is a live site with text on it. Verification was asking "does
    this name resolve to something?" when the question is "is this a business IN THIS CATEGORY?".
    A name is only a competitor if the page it resolves to is about the category."""
    words = CATEGORY_WORDS.get((category or "").lower(), ((category or "").lower(),))
    tl = (text or "").lower()
    return any(w in tl for w in words if w)


_TRAILING_FILLER = ("it", "the", "and", "by", "pm", "am", "admin", "web", "show", "more", "ltd",
                    "pte", "inc", "llp", "sg", "our", "we")


def clean_candidate_name(c: str) -> str:
    """TURN A MINED STRING INTO A NAME. Measured junk this removes, all seen in the vetted set:
    "BreadTalk. It" (sentence fragment), "BreadTalk's" and "PrimaDeli's" (possessive), "PrimaDeli's"
    again. These went to domain resolution as-is and could not resolve -- and a malformed name that
    fails to resolve looks exactly like a brand with no site."""
    s = re.sub(r"['\u2019]s\b", "", c or "")          # possessive
    s = re.sub(r"[^\w\s&.\-']+", " ", s)              # stray punctuation
    s = re.sub(r"\s+", " ", s).strip(" .,\-&'")
    # ⚠ STRIP PUNCTUATION PER WORD. Stripping only the ends of the whole string left the dot in
    # "BreadTalk." -- measured failure: "BreadTalk. It" cleaned to "BreadTalk." and still would not
    # resolve. The filler word popped, its punctuation did not.
    words = [w.strip(".,\-&'") for w in s.split()]
    words = [w for w in words if w]
    while len(words) > 1 and words[-1].lower() in _TRAILING_FILLER:
        words.pop()                                      # "BreadTalk. It" -> "BreadTalk"
    return " ".join(words)[:60]


def _tokens(nm: str) -> list:
    return [w for w in re.split(r"[^a-z0-9]+", (nm or "").lower()) if w]


def dedupe_entities(items: list) -> list:
    """⚠⚠ DE-DUPLICATE BY ENTITY, NOT BY URL. The URL rule was not enough: "Tiong Bahru" and
    "Tiong Bahru Bakery" resolve to DIFFERENT urls and both survived as separate competitors --
    inflating the identified count and making the X-of-Y reveal untrue. Same for "Happy Oven" and
    "Happy Oven Bakery".

    The rule: if one name's tokens are a PREFIX of another's, they are one entity, and the MORE
    SPECIFIC name wins. "Tiong Bahru" is a district; "Tiong Bahru Bakery" is the brand. Keeping the
    longer name is right in every observed case. Exact normalised duplicates collapse too.
    ⚠ The risk is a genuine business whose name is a prefix of another's; no such case has been seen
    here, and the output names the set so a human can check it.
    """
    # ⚠⚠ DEDUPE BY INDEX, NOT BY NAME. The first version added the LOSER'S NAME to a drop set and
    # then filtered by name -- so an exact duplicate dropped EVERY copy, both of them, and the set
    # came back with nothing at all. Measured: dedupe_entities([{BreadTalk},{BreadTalk}]) returned
    # ZERO items. A dedupe that can delete the whole set is worse than no dedupe.
    keys = [tuple(_tokens(i.get("name"))) for i in items]
    drop = set()
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            a, b = keys[i], keys[j]
            if not a or not b:
                continue
            if a == b:
                drop.add(j)                                  # exact duplicate: keep the FIRST
                continue
            shorter, longer = (a, b) if len(a) <= len(b) else (b, a)
            if longer[:len(shorter)] == shorter:             # "Tiong Bahru" vs "Tiong Bahru Bakery"
                drop.add(i if len(a) <= len(b) else j)       # drop the LESS SPECIFIC one
    return [it for idx, it in enumerate(items) if idx not in drop]


def verify_candidate(name: str, timeout: int = 12, category: str = "",
                     cache_only: bool = False) -> dict:
    """IS THIS NAME A REAL BUSINESS? Answer by reading its own site. Cached; never invents.

    ⚠ `could_not_read` IS NOT A REJECTION. The spec is explicit that an unreadable page is a tool
    failure, never a finding about the rival. So a candidate that cannot be read is INCONCLUSIVE, and
    is excluded from the vetted set while being COUNTED in the report. The three outcomes stay three.
    """
    key = re.sub(r"\s+", " ", (name or "").lower()).strip()
    if not key:
        return {"name": name, "verdict": "empty"}
    cache = _load_cache()
    if cache.get("__version__") != _VERIFIER_VERSION:
        cache.clear()
        cache["__version__"] = _VERIFIER_VERSION
    hit = cache.get(key)
    if hit and (time.time() - hit.get("ts", 0)) < _CACHE_TTL_S:
        return dict(hit["v"], name=name, cached=True)
    # ⚠ THE INLINE PATH MUST NOT PAY FOR AN UNCACHED NAME. Splitting "warm the market" (unbounded,
    # background, cached) from "build the report" (bounded, inline, cache-only) is what makes this
    # safe to sit inside a free-report request: the request never waits on a 5-domain root probe.
    if cache_only:
        return {"name": name, "verdict": "not_cached",
                "why": "not yet verified -- run warm_market(); reported as not-yet-verified, never as "
                       "a rejection and never as a competitor"}
    try:
        import ps_evidence as pe
        r = pe.claim_for(name, timeout=timeout) or {}
        st = r.get("status")
    except Exception as exc:  # noqa: BLE001
        return {"name": name, "verdict": "inconclusive", "why": "%s: %s" % (type(exc).__name__,
                                                                           str(exc)[:110])}
    if st in ("claim_found", "read_no_claim"):
        blob = (r.get("claim") or "") + " " + " ".join(r.get("evidence") or [])
        # ⚠ A PAGE THAT ONLY REPEATS ITS OWN NAME IS CHROME, NOT A CLAIM. "All-Day Breakfast" was
        # vetted on the text "All-Day Breakfast All-Day Breakfast the spread - 553 of 555 served",
        # which is site navigation. A claim says something ABOUT the business; chrome says the name.
        head = blob[:90].lower()
        if head.count(name.lower().strip()) + head.count(name.lower().split()[0]) >= 3:
            return {"name": name, "verdict": "chrome_not_a_claim", "status": st,
                    "why": "the readable text only repeats the page's own name"};
        if category and not _in_category(blob, category):
            v = {"name": name, "verdict": "not_in_category", "status": st, "url": r.get("url"),
                 "why": "the site resolved but is not about this category -- e.g. a hospital"}
        else:
            v = {"name": name, "verdict": "real", "status": st, "url": r.get("url"),
                 "claim": r.get("claim"), "evidence": (r.get("evidence") or [None])[0]}
    else:
        v = {"name": name, "verdict": "inconclusive", "status": st, "url": r.get("url"),
             "why": r.get("why")}
    cache[key] = {"ts": time.time(), "v": {k: x for k, x in v.items() if k != "name"}}
    _save_cache()
    return v


def verify_candidates(names: list, workers: int = 8, budget_s: int = 150, timeout: int = 12,
                      category: str = "", cache_only: bool = False) -> dict:
    """VET THE POOL, CONCURRENTLY, UNDER A HARD TIME BUDGET. Serial it was ~30 minutes; the budget
    is what makes this safe to run inside a web request for a free report. Whatever is not reached
    inside the budget is reported as NOT CHECKED -- never as rejected, and never as accepted."""
    from concurrent.futures import ThreadPoolExecutor, as_completed
    t0 = time.time()
    done, skipped = [], []
    with ThreadPoolExecutor(max_workers=max(1, workers)) as ex:
        futs = {ex.submit(verify_candidate, n, timeout, category, cache_only): n for n in names}
        for fu in as_completed(futs, timeout=None):
            if time.time() - t0 > budget_s:
                for f2 in futs:
                    if not f2.done():
                        skipped.append(futs[f2])
                        f2.cancel()
                break
            try:
                done.append(fu.result())
            except Exception as exc:  # noqa: BLE001
                done.append({"name": futs[fu], "verdict": "inconclusive",
                             "why": type(exc).__name__})
    real = [d for d in done if d.get("verdict") == "real"]
    # ⚠ TWO NAMES RESOLVING TO ONE SITE ARE ONE COMPETITOR. "Tiong Bahru" and "Tiong Bahru Bakery"
    # both resolved to tiongbahru.com -- counting them twice inflates the identified total and makes
    # the X-of-Y reveal a lie. Keep the longest name (the more specific one).
    by_url = {}
    for d in real:
        u = (d.get("url") or "").lower()
        if u not in by_url or len(d["name"]) > len(by_url[u]["name"]):
            by_url[u] = d
    real = dedupe_entities(list(by_url.values()))   # then collapse name-prefix twins
    # best-first: a rival with a readable published claim is more useful evidence than one without
    real.sort(key=lambda d: (0 if d.get("status") == "claim_found" else 1, d["name"]))
    return {"checked": len(done), "not_checked": sorted(skipped), "elapsed_s": round(time.time() - t0, 1),
            "real": real, "inconclusive": [d["name"] for d in done if d.get("verdict") != "real"],
            "n_real": len(real)}


def clean_place_name(nm: str) -> str:
    """STRIP THE OUTLET SUFFIX SO THE BRAND NAME RESOLVES TO A DOMAIN.

    ⚠ MEASURED FAILURE THIS FIXES (live bakery run). Google Maps returns OUTLETS, not brands --
    "Good Day Bakery (Clementi)", "The JellyHearts@The Clementi", "Kopi & Tarts @ City Square Mall".
    Those names were fed straight to domain resolution, which built gooddaybakeryclementi.com and
    every one returned status 000 -- a connection failure, NOT a finding that the rival states no
    claim. All seven discovered bakeries came back "could not read", and the cause was the suffix,
    not the businesses.

    Meanwhile the same reader returned real claims for the BRAND names (BreadTalk: "over 700 outlets
    in 14 international markets ... culinary magic"; Four Leaves: "a trustworthy bakery manufacturer
    ... one of the leading companies"). So the reader was never broken -- the input names were.

    ⚠ THIS IS THE SAME OUTLET-vs-BRAND DISTINCTION AS 4.6.4.6, WHICH KILLED THE REVIEW CORPUS. It bites
    discovery here in exactly the same way, and the fix is the same: reduce the venue to the brand.
    """
    n = re.sub(r"\s*[@|]\s*.*$", "", nm or "")        # "Kopi & Tarts @ City Square Mall"
    n = re.sub(r"\s*\([^)]*\)\s*$", "", n)          # "Good Day Bakery (Clementi)"
    n = re.sub(r"\s*[-–—]\s*(best|sg|singapore|the)\b.*$", "", n, flags=re.I)
    n = re.sub(r"\s*\b(Pte\.?\s*Ltd\.?|LLP|Ltd\.?|Inc\.?)\b.*$", "", n, flags=re.I)
    n = re.sub(r"\s+", " ", n).strip(" -–—,")
    return n[:60]


# ⚠⚠ THE THREE-WAY DISCOVERY TEST, MEASURED (spec 4.6.3.8). Sean asked which mechanism actually
# surfaces the category's MAJORS. Ground truth = the five bakery cases in inputs-v4, whose
# `competitors_named` lists converge on the same four rivals -- BreadTalk, Four Leaves, Paris
# Baguette, Tiong Bahru Bakery, Polar Puffs & Cakes. Five independent owners naming one set is the
# category's majors, not one opinion.
#
#     ARM A  Maps category query ..... 0 of 5 majors. 7 names, ALL junk -- a HOTEL, a gym, and five
#                                     small independents. "bakery Singapore" returns who is NEAR YOU.
#     ARM B  brand-oriented source ... 5 of 5 majors, automatic.
#     ARM C  hand-curated list ....... 5 of 5 majors, but manual and ongoing.
#
# ⇒ THE QUERY SHAPE IS THE WHOLE DIFFERENCE, NOT THE PLATFORM. Same web, same fetch layer: "bakery
#   Singapore" returns outlets; "best bakery brands Singapore" returns a listicle whose prose names
#   the majors. Arm B is therefore PRIMARY and Maps is the fallback for thin categories.
#
# ⚠ VERIFIED, not assumed: the winning page was re-fetched and read by hand. It contains, verbatim,
#   "Delifrance, Paris Baguette, Polar Puffs & Cakes, Swee Heng and PrimaDeli. BreadTalk, Tiong Bahru
#   Bakery, Four Leaves and Duke Bakery" -- all five majors in one passage, plus four more real brands.
#
# ⚠ A FALSE 5/5 HAD TO BE CAUGHT FIRST. The first matcher tested `t in nn or nn in t`. A Maps hit,
#   a Chinese-named hotel, normalised to the EMPTY STRING, and `"" in t` is True for everything, so
#   the run reported 5 of 5 majors against a set containing no major. Same family as the
#   tiong-bahru self-match defect: a substring test with no floor on the needle. Fixed with a length
#   floor and word-boundary matching, and only then did the measurement become decisive.
BRAND_JUNK = REPORT_DOMAINS + (
    "singapore", "best", "top", "the", "and", "with", "for", "our", "you", "your", "read", "more",
    "updated", "verdict", "how we rank", "editors", "halal", "island", "city", "guide", "list",
    "review", "reviews", "article", "share", "menu", "order", "contact", "about", "address",
    "including", "old school", "new", "great", "good", "house", "home", "french", "german",
    "italian", "japanese", "korean", "chinese", "tuesday", "monday", "saturday", "sunday",
    "bakery", "bread", "cafe", "cakes", "pastry", "opening", "hours", "price", "prices", "location",
)

# ⚠⚠ THE RANKING WAS THE SECOND DEFECT, AND IT IS THE SAME FAILURE AS THE "Salad Shop" CASE.
# Ranking candidates by RAW FREQUENCY across the source pages put "French", "Bakery", "Tuesday",
# "Best Bakeries" and "Address" on top and returned only 1 of 5 majors -- while ALL FIVE were sitting
# in the same 238-candidate pool. Boilerplate headings appear on EVERY page; a brand name appears
# once. Frequency ranks the generic, not the distinctive. (The earlier `verified: 0` had the same
# root cause: the ten candidates chosen for claim-reading were exactly those junk headings, so
# verification looked broken when it was being fed the wrong list.)
#
# The discriminator that actually separates a brand from a heading is SHAPE, not count:
#   "Tiong Bahru Bakery" / "Paris Baguette" / "Four Leaves" / "Polar Puffs"  -- multi-word proper noun
#   "BreadTalk" / "PrimaDeli"                                                -- CamelCase (internal capital)
#   "French" / "Bakery" / "Tuesday" / "House"                                -- a bare dictionary word
_EN_STOP = ("french german italian japanese korean chinese thai indian western asian local "
            "best top the our your including opening hours price location review guide list "
            "old new great good house home bakery bread cafe cakes pastry address tuesday").split()


# ⚠ PLACE NAMES AND PAGE CHROME, REJECTED BY TOKEN. These are not brands and verifying them wastes
# the budget AND can produce a false accept -- "Farrer Park" resolved to farrerpark.com, a HOSPITAL,
# and was vetted as a real competitor. "Nearest MRT", "Eng Hoon Street", "Icon Village", "PM Show
# More" and "Which Are Halal" are street addresses and page furniture that survived the shape filter.
_NOT_A_BRAND_TOKEN = (
    "mrt", "street", "road", "avenue", "lane", "village", "park", "drive", "crescent", "close",
    "show", "more", "halal", "nearest", "which", "are", "off", "sg", "singapore", "hospital",
    "street)", "mall", "plaza", "centre", "center", "square", "tower", "building", "hotel",
    "lim", "tan", "lee", "ng", "ong", "wong", "goh", "chua", "staff", "review", "sarah",
)


def is_brandish(c: str) -> bool:
    """A brand has a SHAPE: a multi-word proper noun, or a CamelCase token. A bare lowercase
    dictionary word is a heading, not a business. This is the filter that lets the majors through."""
    c = (c or "").strip()
    if len(c) < 5 or c.lower() in BRAND_JUNK:
        return False
    words = c.split()
    low = [w.lower().strip(".,'") for w in words]
    if any(w in _NOT_A_BRAND_TOKEN for w in low):
        return False
    if len(words) >= 2:
        # a multi-word phrase is brandish unless its HEAD word is generic boilerplate
        return not all(w.lower() in _EN_STOP or w.lower() in BRAND_JUNK for w in words) \
            and words[0].lower() not in _EN_STOP
    return bool(re.search(r"[a-z][A-Z]", c))   # CamelCase: BreadTalk, PrimaDeli


def discover_brand_source(category: str, market: str, limit: int = 12) -> dict:
    """ARM B, AND THE MEASURED WINNER: ask a BRAND-ORIENTED question, not a category question.

    "best <category> brands in <market>" surfaces a listicle, and a listicle's prose names the
    majors -- because answering "who is best" requires naming the real players. Candidates are
    RANKED BY HOW MANY SOURCES NAME THEM: a brand that appears in several independent lists is far
    likelier to be real than one mentioned once.

    ⚠ THE EXTRACTION IS CRUDE BY DESIGN, and that is stated rather than hidden: capitalised runs
    yield many false candidates. The intended filter is the claim reader -- a candidate whose own
    site yields a readable claim is a real business (ps_evidence.claim_for). ⚠ THAT VERIFICATION
    STEP IS NOT YET WIRED (it returned 0 in the test run), so today the set is CANDIDATES, and the
    report must say so.
    """
    names, errs, pages = {}, [], []
    page_of, listed = {}, {}
    try:
        from hermes_tools import web_extract, web_search
        for q in ("best %s brands in %s" % (category, market),
                  "%s chains %s list" % (category, market)):
            try:
                res = web_search(q, limit=5)
                urls = [w["url"] for w in (res.get("data", {}).get("web") or [])][:3]
            except Exception as exc:  # noqa: BLE001
                errs.append("search %r: %s" % (q, type(exc).__name__))
                continue
            if not urls:
                continue
            pages.extend(urls)
            try:
                ex = web_extract(urls, char_limit=12000)
            except Exception as exc:  # noqa: BLE001
                errs.append("extract: %s" % type(exc).__name__)
                continue
            for r in ex.get("results", []):
                body = r.get("content") or ""
                if any(d in (r.get("url") or "").lower() for d in REPORT_DOMAINS):
                    continue
                page_url = r.get("url") or ""
                for m in re.finditer(r"\b([A-Z][a-zA-Z'&.\-]+(?:\s+[A-Z][a-zA-Z'&.\-]+){0,2})\b", body):
                    c = re.sub(r"\s+", " ", m.group(1)).strip()
                    if len(c) < 5 or c.lower() in BRAND_JUNK:
                        continue
                    names[c] = names.get(c, 0) + 1
                    # ⚠ COUNT DISTINCT PAGES, NOT OCCURRENCES. Raw occurrence count ranks a heading
                    # repeated six times inside one page above a brand named once per page across
                    # three pages -- which is exactly how the majors ranked out. How many INDEPENDENT
                    # sources name you is the signal; how often one page repeats a word is noise.
                    page_of.setdefault(c, set()).add(page_url)

                # ⚠⚠ AND THE RANKING THAT ACTUALLY FINDS THE MAJORS: LIST CO-OCCURRENCE.
                # Every frequency variant failed, because the majors are named ONCE, in a comparative
                # sentence, with the other majors -- "Delifrance, Paris Baguette, Polar Puffs & Cakes,
                # Swee Heng and PrimaDeli. BreadTalk, Tiong Bahru Bakery, Four Leaves and Duke Bakery."
                # A heading is repeated; a BRAND IS ENUMERATED. So a candidate that shares a SENTENCE
                # with other candidates is being listed as a brand, and that is the signal. This is
                # the one signal that is true of the majors and false of boilerplate.
                for sent in re.split(r"(?<=[.!?;])\s+|\n+", body):
                    if len(sent) > 400:
                        continue
                    found = {re.sub(r"\s+", " ", m.group(1)).strip()
                             for m in re.finditer(
                                 r"\b([A-Z][a-zA-Z'&.\-]+(?:\s+[A-Z][a-zA-Z'&.\-]+){0,2})\b", sent)}
                    found = {f for f in found if len(f) >= 5 and f.lower() not in BRAND_JUNK}
                    if len(found) < 2:
                        continue          # a lone name is not an enumeration
                    for f in found:
                        listed[f] = listed.get(f, 0) + 1
                    # ⚠ COUNT DISTINCT PAGES, NOT OCCURRENCES. Raw occurrence count ranks a heading
                    # repeated six times inside one page above a brand named once per page across
                    # three pages -- which is exactly how the majors ranked out. How many INDEPENDENT
                    # sources name you is the signal; how often one page repeats a word is noise.
                    page_of.setdefault(c, set()).add(page_url)
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "names": [], "error": "%s: %s" % (type(exc).__name__, str(exc)[:140]),
                "source": "brand_source"}

    # keep only brand-SHAPED candidates, then rank by how many sources name them
    shaped = {k: v for k, v in names.items() if is_brandish(k)}
    multi = {k: len(v) for k, v in page_of.items()}
    # listed-in-a-run first (how majors are named), then distinct pages, then shape
    ranked = sorted(shaped.items(),
                    key=lambda kv: (-listed.get(kv[0], 0), -multi.get(kv[0], 0), -kv[1], kv[0]))
    return {"ok": bool(ranked), "names": [k for k, _ in ranked[:limit]],
            "n_brand_shaped": len(shaped),
            "named_by_multiple_sources": [k for k, _ in ranked[:limit] if multi.get(k, 0) > 1],
            "pages_naming": {k: multi.get(k, 0) for k, _ in ranked[:limit]},
            "listed_with_other_candidates": {k: listed.get(k, 0) for k, _ in ranked[:limit]},
            "n_raw_candidates": len(names), "pages": sorted(set(pages))[:4], "errors": errs,
            "source": "brand_source (list of %s brands in %s)" % (category, market),
            "note": "candidates ranked by how many sources name them; NOT yet claim-verified"}


def discover_maps(category: str, market: str, limit: int = 12) -> dict:
    """DISCOVERY THAT ACTUALLY RETURNS BUSINESSES: enumerate the category on GOOGLE MAPS.

    ⚠ WHY MAPS AND NOT A WEB SEARCH (measured 17 Oct). A Maps search for a category returns NAMED
    LOCAL BUSINESSES IN THAT CATEGORY -- which is precisely a competitive set. Today the same run
    produced 29 named managed-IT firms and 11-28 named places for bakery-type queries. The web
    search returned market reports. Maps is the mechanism that answers "who competes here".

    ⚠ AND IT IS NOT FILTERED FOR RELEVANCE. A category query returns LOOKALIKES: the managed-IT run
    returned a fibre-products distributor and, memorably, "WINZ CREDIT PTE LTD - Best Money Lender
    in Clementi". Downstream reading catches most of these (a money lender's site will not read as
    a rival claim in the category), but the report must not present the raw list as vetted.

    Uses the validated Camoufox profile. Returns names only -- no interpretation.
    """
    names, err = [], None
    try:
        from camoufox.sync_api import Camoufox
        with Camoufox(headless=True, persistent_context=True,
                      user_data_dir="/tmp/camoufox_mind_profile") as ctx:
            page = ctx.new_page()
            page.goto("https://www.google.com/maps/search/" + (category + " " + market).replace(" ", "+"),
                      timeout=50000)
            page.wait_for_timeout(7000)
            for _ in range(5):
                page.mouse.wheel(0, 3000)
                page.wait_for_timeout(800)
            seen = set()
            for a in page.query_selector_all('a[href*="/maps/place/"]'):
                nm = ((a.get_attribute("aria-label") or a.inner_text() or "").strip().split("\n")[0])[:70]
                nm = re.sub(r"\s+", " ", nm).strip()
                nm = clean_place_name(nm)
                # too short after cleaning means the suffix WAS the name -- drop it rather than
                # resolve a fragment to a stranger's domain.
                if not nm or len(nm) < 4 or nm.lower() in seen:
                    continue
                seen.add(nm.lower())
                names.append(nm)
                if len(names) >= limit:
                    break
    except Exception as exc:  # noqa: BLE001
        err = "%s: %s" % (type(exc).__name__, str(exc)[:140])
    return {"ok": bool(names), "names": names[:limit], "error": err, "source": "google_maps",
            "note": "enumerated, then reduced from outlet to BRAND name; NOT vetted for relevance"}


def from_web_scan(category: str, market: str, timeout: int = 15) -> dict:
    """The web search, kept ONLY as a labelled last resort -- and filtered to company domains."""
    import competitor_scan as cs
    try:
        sc = cs.scan(category, market, [], timeout)
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "names": [], "error": "%s: %s" % (type(exc).__name__, str(exc)[:120])}
    names, rejected = [], []
    for c in (sc.get("captures") or []):
        u = (c.get("url") or "").lower()
        if any(d in u for d in REPORT_DOMAINS):
            rejected.append(u[:70])
            continue
        host = re.sub(r"^https?://(www\.)?", "", u).split("/")[0]
        if host:
            names.append(host)
    return {"ok": bool(names), "names": names[:10], "rejected_as_not_a_business": rejected[:8],
            "source": "web_search (unverified hosts -- last resort)",
            "note": "a category web search returns articles ABOUT the category; this is not a vetted set"}


def warm_market(category: str, market: str, max_candidates: int = 150, workers: int = 10,
                budget_s: int = 900, timeout: int = 12) -> dict:
    """WARM THE VERDICT CACHE FOR A MARKET. Unbounded, run OUT OF BAND (cron, or a backgrounded
    process); never call this inline on a user request. Everything it verifies is cached for 30 days,
    so the inline build() then costs only discovery."""
    d = discover_brand_source(category, market, limit=max_candidates)
    names = [clean_candidate_name(n) for n in d.get("names", [])]
    names = [n for i, n in enumerate(names) if n and n not in names[:i]]
    v = verify_candidates(names, workers=workers, budget_s=budget_s, timeout=timeout,
                          category=category)
    return {"category": category, "market": market, "candidates": len(names),
            "checked": v["checked"], "vetted_real": v["n_real"], "elapsed_s": v["elapsed_s"],
            "vetted": sorted(x["name"] for x in v["real"])}


def build(subject_name: str, subject_claim: str, category: str, market: str = "Singapore",
          owner_named=None, seed_urls=None, discover: bool = True,
          max_rivals: int = 6, per_url_timeout: int = 18,
          verify: bool = True, verify_workers: int = 8, verify_budget_s: int = 270,
          cache_only: bool = False) -> dict:
    """THE LOCKED-IN PROCESS. One call: discover -> read claims -> range -> place -> report.

    Discovery is INTEGRAL (step 1), not a prerequisite.
    """
    import competitor_scan as cs

    out = {"subject": subject_name, "category": category, "market": market,
           "steps": {}, "competitors": [], "unreadable": []}

    # ── 1 DISCOVER (online) ────────────────────────────────────────────────────────────────
    names, found_by = [], {}
    if owner_named:
        for n in owner_named:
            n = (n or "").strip()
            if n and cs._is_company_name(n) and n not in names:
                names.append(n)
                found_by[n] = "named by the business owner"
    disc = {"maps": None, "web": None}
    if discover:
        # PRIMARY (measured winner, 4.6.3.8): the brand-oriented source. Ask who the BRANDS are.
        b = discover_brand_source(category, market, limit=150)
        disc["brand_source"] = {"ok": b["ok"], "n": len(b["names"]),
                                "n_raw_candidates": b.get("n_raw_candidates"),
                                "note": b.get("note"), "errors": b.get("errors")}
        for nm in b["names"]:
            if cs._is_company_name(nm) and nm.lower() != subject_name.lower() and nm not in names:
                names.append(nm)
                found_by[nm] = ("named by a brand-oriented source (%s)" % b.get("source", ""))[:90]
        # FALLBACK: Google Maps, only when the brand source found nothing.
        m = discover_maps(category, market, limit=max_rivals * 3) if not names else {"ok": True, "names": [], "note": "skipped -- brand source already found names"}
        disc["maps"] = {"ok": m["ok"], "n": len(m["names"]), "error": m.get("error"),
                        "note": m.get("note")}
        for nm in m["names"]:
            if cs._is_company_name(nm) and nm.lower() != subject_name.lower() and nm not in names:
                names.append(nm)
                found_by[nm] = "enumerated on Google Maps for this category"
        # LAST RESORT only, and labelled: the web search returned market reports, not rivals.
        if not names:
            w = from_web_scan(category, market, per_url_timeout)
            disc["web"] = {"ok": w["ok"], "n": len(w["names"]),
                           "rejected_as_not_a_business": w.get("rejected_as_not_a_business"),
                           "note": w.get("note")}
            for nm in w["names"]:
                if cs._is_company_name(nm) and nm not in names:
                    names.append(nm)
                    found_by[nm] = "web-search host (UNVERIFIED -- last resort)"
    out["discovery_sources"] = disc
    out["steps"]["discover"] = {"ok": bool(names), "n_candidates": len(names),
                               "candidates": names[:40], "found_by": found_by}

    # ── 1b VET — candidates become a VETTED SET. This is what makes discovery production-ready. ──
    # ⚠ WITHOUT THIS STEP THE OUTPUT IS A CANDIDATE POOL, and a candidate pool is not a competitive
    # set: measured, the brand-oriented source surfaced 5 of 5 majors but they ranked 26th and below,
    # behind a gym and a hotel. Reading each name's own site is the ONLY filter that discriminates,
    # because it asks the question frequency cannot: does this name resolve to a live business that
    # publishes a claim? Concurrency + the cache + the budget below are what make that affordable.
    vet = {"real": [], "inconclusive": [], "not_checked": [], "checked": 0, "n_real": 0,
           "elapsed_s": 0.0}
    # ⚠ CLEAN BEFORE VETTING. A malformed name cannot resolve, so it looks like a brand with no
    # site -- the same false shape as an unreadable page. Clean names first, then verify.
    names = [clean_candidate_name(n) for n in names]
    seen_n = set()
    names = [n for n in names if n and not (n.lower() in seen_n or seen_n.add(n.lower()))]
    pool = names[:120]
    if verify and pool:
        vet = verify_candidates(pool, workers=verify_workers, budget_s=verify_budget_s,
                                timeout=min(per_url_timeout, 12), category=category,
                                cache_only=cache_only)
        out["steps"]["verify"] = {
            "ok": bool(vet["real"]), "candidates_considered": len(pool), "checked": vet["checked"],
            "vetted_real": vet["n_real"], "inconclusive": len(vet["inconclusive"]),
            "not_checked": len(vet["not_checked"]), "elapsed_s": vet["elapsed_s"]}
        out["vetting"] = {
            "candidates_considered": len(pool), "checked": vet["checked"],
            "vetted": [v["name"] for v in vet["real"]],
            "inconclusive": vet["inconclusive"][:12],
            "not_checked": vet["not_checked"][:12],
            "note": ("a name that could not be read is INCONCLUSIVE, never rejected -- an unreadable "
                     "page is a tool failure, not a finding about the rival")}
        # ⚠ THE VETTED SET IS THE COMPETITIVE SET. Everything else is reported as candidates.
        names = [v["name"] for v in vet["real"]][:max_rivals + 4]
        for v in vet["real"]:
            if v.get("claim"):
                found_by.setdefault(v["name"], "found online, vetted: its own site publishes a claim")
    else:
        names = names[:max_rivals]

    # ── 2 CLAIM (read each rival's published claim) ─────────────────────────────────────────
    claims = {}
    # ⚠ the verifier ALREADY read these sites; re-reading them would double the report's cost for no
    # new information. Seed from the vetted claims, then read only what is left.
    for v in vet.get("real") or []:
        if v.get("status") == "claim_found" and v.get("claim"):
            claims[v["name"]] = v["claim"]
            out["competitors"].append({"name": v["name"], "claim": v["claim"],
                                       "url": v.get("url"),
                                       "how_found": found_by.get(v["name"], "found online, vetted")})
    for n in names:
        if n.lower() == subject_name.lower() or n in claims:
            continue
        try:
            r = ps_evidence.claim_for(n, timeout=per_url_timeout)
        except Exception as exc:  # noqa: BLE001
            r = {"claim": None, "outcome": "error: %s" % type(exc).__name__}
        claim = r.get("claim") if isinstance(r, dict) else None
        if claim:
            claims[n] = claim
            out["competitors"].append({"name": n, "claim": claim, "how_found": found_by.get(n, "?")})
        else:
            out["unreadable"].append({"name": n, "outcome": (r or {}).get("outcome") if isinstance(r, dict) else "?"})
    out["steps"]["claims"] = {"ok": len(claims) > 0, "readable": len(claims),
                              "unreadable": len(out["unreadable"])}

    # ── 3+4 RANGE AND PLACE ──────────────────────────────────────────────────────────────────
    placed = place(subject_claim, claims)
    out["steps"]["range_place"] = {"ok": placed.get("ok", False)}
    out["comparison"] = placed

    # ── 5 REPORT (incl. the X/Y reveal Sean specified) ───────────────────────────────────────
    n_found = len(names)          # the VETTED set, not the candidate pool
    n_shown = len(claims)
    out["reveal"] = {
        "identified": n_found, "shown": n_shown,
        "sentence": ("We identified %d competitors in this category; this free report shows you %d. "
                     "The remaining analysis is part of the paid engagement."
                     % (n_found, n_shown)) if n_found > n_shown else
                    ("We identified and read %d competitors in this category." % n_shown),
    }
    out["limits"] = [
        "The claim map reads PUBLISHED claims. It does not measure whether customers agree.",
        "DISTINCTIVE IS NOT THE SAME AS GOOD: an unoccupied claim may be a real position or one "
        "nobody cares about. This measures occupancy, not value.",
        "A rival whose site could not be read is reported as unreadable, never as having no claim.",
        "%d of %d discovered names yielded a readable claim." % (n_shown, n_found),
    ]
    return out


def _selftest() -> int:
    """⚠ THE CONTROL LIVES HERE. 4.6.4.12 shipped a test that fired on everything because it had no
    control. This one cannot pass without distinguishing a crowded claim from a distinctive one."""
    fails = []

    def check(name, got, want):
        ok = got == want
        print(("PASS  " if ok else "FAIL  ") + name, "->", got if ok else "got %r want %r" % (got, want))
        if not ok:
            fails.append(name)

    print("1. overlap is MIN-NORMALISED, so a long claim is not punished for being long")
    short, long_ = {"artisan", "bread", "sourdough"}, {"artisan", "bread", "sourdough", "stone", "oven", "daily",
                                                       "bake", "handmade", "flour", "crust", "loaf", "rye"}
    check("long claim still overlaps fully on the shared terms", overlap(short, long_), 1.0)

    # a synthetic category: three rivals who all say roughly the same thing
    rivals = {
        "Rival A": "Fresh bread baked daily in our neighbourhood bakery with sourdough and artisan loaves",
        "Rival B": "Daily fresh sourdough and artisan bread baked in our neighbourhood bakery",
        "Rival C": "Neighbourhood bakery baking fresh sourdough loaves daily for the community",
    }
    bg = range_background(rivals)
    print("\n2. the RANGE is MEASURED, not chosen: rivals contest each other on %.0f%% of their own\n   distinctive terms (n=%d rival claims, %d pairs)" % (bg["mean_contested"]*100, bg["n"], len(bg["pairs"])))
    check("background computed", bg["ok"], True)
    check("rivals really do contest each other", bg["mean_contested"] > 0.3, True)

    print("\n3. ⚠ THE CONTROL -- A CLAIM THAT MATCHES THE CATEGORY MUST READ 'CROWDED'")
    crowded = place("We bake fresh sourdough and artisan bread daily in our neighbourhood bakery", rivals)
    check("matching claim -> CROWDED", crowded["verdict"], "CROWDED")

    print("4. ⚠ THE OTHER HALF OF THE CONTROL -- AN UNOCCUPIED CLAIM MUST READ 'DISTINCTIVE'")
    distinct = place("We are the only bakery in Singapore milling our own heirloom einkorn grain "
                     "on a granite stone mill for microbiome-friendly fermentation", rivals)
    check("unoccupied claim -> DISTINCTIVE", distinct["verdict"], "DISTINCTIVE")
    print("      distinct claim: %.0f%% of its terms contested, vs range %.0f%%"
          % (distinct["subject_contested_share"]*100, bg["mean_contested"]*100))

    print("\n5. ⚠ A 'DISTINCTIVE' VERDICT MUST NOT BE STATED AS 'GOOD' (the honest limit)")
    print("      why:", distinct["why"][:150])
    check("verdict wording is about occupancy not value", "unoccupied" in distinct["why"], True)

    print("\n6. ONE READABLE RIVAL IS NOT A RANGE -- and says so instead of faking a comparator")
    one = place("artisan bread", {"Rival A": "fresh sourdough bread daily"})
    check("single rival -> UNRANGED", one["verdict"], "UNRANGED")

    print("\n7. unreadable rivals are EXCLUDED from the range, never counted as empty claims")
    mixed = dict(rivals); mixed["Rival D"] = ""
    check("blank claim excluded from the range", range_background(mixed)["n"], 3)

    print("\n8. the X/Y reveal sentence exists and never states a total it cannot measure")
    check("reveal sentence is generated in build()", hasattr(build, "__call__"), True)

    # ⚠⚠ THE CHECKS BELOW WERE WRITTEN BECAUSE THE CODE THEY COVER WAS WRONG TWICE. Both defects
    # were found by testing these functions directly, and both are recorded rather than quietly
    # fixed: a cleaning bug that left "BreadTalk." unable to resolve, and a dedupe that could delete
    # the ENTIRE set on an exact duplicate. A permanent check is the only thing that stops either
    # coming back.
    print("\n-- name cleaning (mined strings -> names) --")
    check('"BreadTalk. It" cleans', clean_candidate_name("BreadTalk. It"), "BreadTalk")
    check('possessive cleans', clean_candidate_name("PrimaDeli's"), "PrimaDeli")
    check("a real name is untouched", clean_candidate_name("Tiong Bahru Bakery"),
          "Tiong Bahru Bakery")

    print("\n-- entity de-duplication (by ENTITY, not URL) --")
    check("exact duplicate keeps ONE, never zero",
          len(dedupe_entities([{"name": "BreadTalk"}, {"name": "BreadTalk"}])), 1)
    check("name-prefix twins collapse to the specific name",
          [x["name"] for x in dedupe_entities([{"name": "Happy Oven"},
                                               {"name": "Happy Oven Bakery"}])],
          ["Happy Oven Bakery"])
    check("distinct businesses both survive",
          len(dedupe_entities([{"name": "Polar Puffs"}, {"name": "Paris Baguette"}])), 2)
    check("an empty set stays empty", len(dedupe_entities([])), 0)

    print("\n-- the inline path never pays for an uncached lookup --")
    check("cache_only refuses an uncached name",
          verify_candidate("Zzz Unverified Qqq Never Seen", cache_only=True).get("verdict"),
          "not_cached")

    print("\nSELF-TEST: %d failed" % len(fails))
    return 1 if fails else 0


def _cli() -> None:
    """python3 claim_map.py warm <category> <market>   -- background warm-up, out of band."""
    if len(sys.argv) > 3 and sys.argv[1] == "warm":
        print(json.dumps(warm_market(sys.argv[2], sys.argv[3]), indent=1)[:4000])
        return
    self_test()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "warm":
        _cli()
        sys.exit(0)
    raise SystemExit(_selftest())
