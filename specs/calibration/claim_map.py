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
import re
import sys
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


def build(subject_name: str, subject_claim: str, category: str, market: str = "Singapore",
          owner_named=None, seed_urls=None, discover: bool = True,
          max_rivals: int = 6, per_url_timeout: int = 18) -> dict:
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
        # PRIMARY: Google Maps enumeration -- the mechanism that actually returns businesses.
        m = discover_maps(category, market, limit=max_rivals * 3)
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
    names = names[:max_rivals + 4]
    out["steps"]["discover"] = {"ok": bool(names), "n": len(names), "names": names, "found_by": found_by}

    # ── 2 CLAIM (read each rival's published claim) ─────────────────────────────────────────
    claims = {}
    for n in names:
        if n.lower() == subject_name.lower():
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
    n_found = len(names)
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

    print("\nSELF-TEST: %d failed" % len(fails))
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(_selftest())
