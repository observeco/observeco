#!/usr/bin/env python3
"""PS EVIDENCE PROTOCOL — derive the claim-ownership map that position_strength is scored against.

Spec: obs-spec-095 section 4.6.3.

WHY THIS EXISTS
    The scorer already receives `derived_competitive_set` (run_jev.build_state, lines 79-89), and for
    BK01-breadtalk its `tier_3_category_incumbent` reads:

        "BreadTalk owns 'iconic local', Four Leaves 'everyday', TBB 'artisan'."

    That line IS the answer to position_strength, pre-computed by a human analyst. PS asks "can this
    business own a claim a named rival does not?", and the input already states who owns which claim.
    The corpus's PS grades are therefore as good as that map. In production there is no analyst, so
    the map must be derived. This script derives it.

THE ONE RULE THAT MATTERS (measured, spec 4.6.3.3)
    READ THE ABOUT PAGE, NOT THE HOMEPAGE.

    Reading homepages alone returned "no claim-shaped sentence" for BOTH Four Leaves and Tiong Bahru
    Bakery -- two real rivals it would have recorded as stating nothing. Their About pages carry the
    claims. A modern retailer's homepage is a SHOP (promo tiles, cart strings); the About / Our Story
    page is the MANIFESTO.

    So an empty homepage read is NOT "no claim" -- it is a WRONG-SURFACE READ. The ladder is walked to
    completion before anything is reported as unstated, and the FIRST surface to yield a claim does
    not terminate the pass, because a later surface can contradict it (BreadTalk's claim is on the
    homepage, not its About page).

NOTHING IS INVENTED
    Where the whole ladder is read and yields nothing, the honest output is "read, states no claim".
    Where the read FAILS, the output is "could not be read" -- a blocked read is a stated LIMIT and
    never a finding about the rival (Duke Bakery returned 0 characters in the pilot).
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from competitor_scan import _domain_candidates, strip_tags  # noqa: E402

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120 Safari/537.36")

# The ladder, in order. About-paths FIRST -- see the module docstring.
LADDER_PATHS = [
    "/about-us", "/about", "/our-story", "/pages/about-us", "/pages/our-story",
    "/our-story/", "/pages/about", "/company", "/brand",  # press/PR last: the claim that was announced
    "/press", "/news", "/media",
]

# Claim-shaped language. Verb STEMS, never whole words -- `\bfocus\b` rejected "focusing on original
# leaf fresh milk tea" because "focusing" has no boundary after "focus" (web-search-scraping-protocol).
CLAIM_RE = re.compile(
    r"(since\s+(19|20)\d\d|first|iconic|artisan|craft(ed|s|smanship)?|hand-?made|freshly|everyday|"
    r"daily|award|best[- ]selling|favourit|favorit|trusted|leading|largest|authentic|traditional|"
    r"signature|home[- ]?grown|our mission|known for|renowned|beloved|heritage|obsess|dedicat|"
    r"we (are|set out|strive|believe)|revolutionis|revolutioniz|pioneer)",
    re.I,
)
# The gate's reject list. Menu / order / cart / cookie vocabulary and price lines appear on EVERY site
# in EVERY category, so they are the most-corroborated strings on the web -- they must never be
# mistaken for a claim.
REJECT_RE = re.compile(
    r"(add to cart|order now|checkout|your (cart|order)|saved for easy reordering|cookie|"
    r"delivery (fee|charge)|free delivery|min(imum)? spend|read more|shop now|view (all|menu)|"
    r"sign ?up|log ?in|out of stock|\$\s?\d|\d+\.\d{2})",
    re.I,
)
MIN_LEN, MAX_LEN = 30, 240
VERB_RE = re.compile(r"\b\w+(e|es|ed|ing|s)\b", re.I)


def _fetch(url: str, timeout: int = 20) -> tuple[str, str]:
    """Return (status, text). status is an HTTP code as a string, or ERR."""
    try:
        r = subprocess.run(
            ["curl", "-sL", "--max-time", str(timeout), "-o", "/dev/null", "-w", "%{http_code}", "-A", UA, url],
            capture_output=True, text=True, timeout=timeout + 8,
        )
        code = (r.stdout or "").strip()
        if code != "200":
            return code or "ERR", ""
        h = subprocess.run(
            ["curl", "-sL", "--max-time", str(timeout), "-A", UA, url],
            capture_output=True, text=True, timeout=timeout + 8,
        ).stdout
        return "200", strip_tags(h or "")
    except Exception as exc:                                    # noqa: BLE001
        return "ERR:%s" % type(exc).__name__, ""


def extract_claims(text: str) -> list[str]:
    """Claim-shaped sentences that survive the gate."""
    if not text or len(text) < 200:
        return []
    out = []
    for s in re.split(r"(?<=[.!?])\s+", text):
        s = s.strip()
        if not (MIN_LEN <= len(s) <= MAX_LEN):
            continue
        if REJECT_RE.search(s) or not CLAIM_RE.search(s):
            continue
        if not VERB_RE.search(s):          # a claim asserts something; a label does not
            continue
        out.append(s)
    return out


def ladder(domain_url: str) -> list[str]:
    """⚠ THE HOMEPAGE SITS INSIDE THE FIRST FEW SURFACES, NOT AT THE END.

    The pilot measured BOTH cases: Four Leaves and Tiong Bahru Bakery carry their claims on the
    About page and NOT on the homepage -- while BreadTalk's claim is on the HOMEPAGE and not on its
    About page. So neither surface may be assumed to hold it. With a `max_surfaces` cap, putting the
    homepage last means it is never reached, and BreadTalk would be recorded as stating no claim.
    """
    base = domain_url.rstrip("/")
    root = re.sub(r"^(https?://[^/]+).*$", r"\1", base)
    about = [root + p for p in ("/about-us", "/about", "/our-story", "/pages/about-us", "/pages/our-story")]
    press = [root + p for p in ("/press", "/news", "/media")]
    return about[:3] + [root + "/"] + about[3:] + press


def _names_the_brand(text: str, name: str) -> bool:
    """⚠⚠ DOES THIS PAGE ACTUALLY BELONG TO THE RIVAL? This guard exists because its absence
    manufactured a finding about a rival that was not about the rival at all.

    Measured: "Polar Puffs" resolves to polarpuffs.com.sg, which is BLOCKED from this fetcher (000).
    The live-root ordering therefore promoted polarpuffs.co -- a DIFFERENT SITE -- which answered 200,
    and the function reported `read_no_claim`, i.e. "this rival's page was read and states no claim".
    That is a fabricated finding about a rival, and it is precisely what this module exists to
    prevent. A reading only counts if the page mentions the brand. Requiring every distinctive token
    is deliberately strict: a stranger's site will not say "polar".
    """
    toks = [w for w in re.split(r"[^a-z0-9]+", (name or "").lower()) if len(w) > 3]
    if not toks:
        return True
    tl = (text or "").lower()
    if len(toks) >= 2:
        return all(w in tl for w in toks)
    return tl.count(toks[0]) >= 2      # a lone token must appear more than incidentally


def claim_for(name: str, timeout: int = 20, max_domains: int = 3, max_surfaces: int = 7) -> dict:
    """Derive one rival's published claim. Never invents; distinguishes failure from absence.

    ⚠⚠ THREE DEFECTS THE FIRST RUN FOUND IN THIS FUNCTION ITSELF -- fixed here, recorded so they are
    not reintroduced. All three caused a REAL rival to be reported as stating no claim, and the first
    two are the same mistake the resolver already made once (§3.7.24): committing to one guess.

      1. ONLY THE FIRST CANDIDATE DOMAIN WAS TRIED. `_domain_candidates("Four Leaves")` returns
         `fourleaves.com` first; the real site is `fourleaves.com.sg`. The ladder was then walked
         entirely on the WRONG DOMAIN and the rival came back `could_not_read` -- while a hand read
         of `fourleaves.com.sg/about-us` returned 200 and its claim. Fixed: fall through the
         candidate domains in order.
      2. THE SURFACE CAP TRUNCATED THE LADDER BEFORE THE WINNING SURFACE. With `max_surfaces=4` the
         ladder stopped at [about-us, about, our-story, homepage]; Tiong Bahru Bakery's claim is on
         `/pages/our-story`, which was never reached, so it was reported `read_no_claim` -- again
         contradicting a successful hand read.
      3. THE HOMEPAGE SAT AT THE END. BreadTalk's claim is on the HOMEPAGE, not its About page
         (measured). A cap that truncates would have made it look like it states nothing.

    ⚠ AND THE SAFETY PROPERTY THAT HELD, AND MUST KEEP HOLDING: across all of that, the function
    never invented a claim. A wrong-surface read returns `read_no_claim` and a failed read returns
    `could_not_read` -- never a fabricated finding about the rival.
    """
    cands = [u for u in _domain_candidates(name) if u.startswith("https://")]
    if not cands:
        return {"name": name, "status": "unresolved", "claim": None, "url": None, "evidence": None,
                "why": "no candidate domain could be built from the name"}

    tried: list[str] = []
    # ⚠⚠ RESOLVE THE DOMAIN FIRST -- NEVER WALK THE SURFACE LADDER ON A DOMAIN THAT DOES NOT EXIST.
    # Measured, and this is why a real rival read as could_not_read: _domain_candidates("Four Leaves")
    # puts fourleaves.com FIRST and the real site is fourleaves.com.sg. The ladder walked ALL SEVEN
    # surfaces on the dead domain before moving on, so under a short timeout the correct domain was
    # never reached. One cheap probe per root fixes it: a domain that does not resolve is skipped and
    # live roots are tried FIRST. ⚠ An HTTP error code still walks the ladder -- a 403 or a 404 root
    # says nothing about its /about page, so only genuine connection failures are treated as dead.
    live_roots, dead_roots = [], []
    for root in cands[: max_domains + 2]:
        rstatus, _ = _fetch(root, min(timeout, 5))
        tried.append("%s (root probe):%s" % (root, rstatus))
        (dead_roots if rstatus in ("ERR", "000", "") else live_roots).append(root)
    ordered = live_roots + dead_roots if live_roots else list(cands)

    read_ok = False
    for root in ordered[:max_domains]:
        claims, hits = [], []
        for url in ladder(root)[:max_surfaces]:
            status, text = _fetch(url, timeout)
            tried.append("%s:%s" % (url, status))
            if status != "200":
                continue
            # ⚠ A 200 FROM THE WRONG DOMAIN IS NOT A READING OF THIS RIVAL. Without this guard a
            # blocked-but-correct domain let a stranger's live domain supply the text, and the
            # function asserted "read, states no claim" about a business whose site it never saw.
            if not _names_the_brand(text, name):
                tried.append("%s:200-BUT-NOT-THIS-BRAND (rejected)" % url)
                continue
            read_ok = True
            found = extract_claims(text)
            if found:
                hits.append((url, found))
                claims.extend(found)
        if claims:
            return {"name": name, "status": "claim_found", "url": hits[0][0], "claim": claims[0],
                    "evidence": claims[:4], "surfaces_read": tried}
    if read_ok:
        return {"name": name, "status": "read_no_claim", "url": cands[0], "claim": None, "evidence": None,
                "why": "the page was read and states no claim -- NOT the same as unreadable",
                "surfaces_read": tried}
    return {"name": name, "status": "could_not_read", "url": cands[0], "claim": None, "evidence": None,
            "why": "every candidate domain and surface failed to read; a tool failure, never a finding "
                   "about the rival",
            "surfaces_read": tried}


def build_map(names: list[str], **kw) -> dict:
    rows = [claim_for(n, **kw) for n in names]
    return {
        "occupants": rows,
        "claim_ownership": {r["name"]: r["claim"] for r in rows if r.get("claim")},
        "unstated": [r["name"] for r in rows if r["status"] == "read_no_claim"],
        "unreadable": [r["name"] for r in rows if r["status"] in ("could_not_read", "unresolved")],
    }


if __name__ == "__main__":
    names = sys.argv[1:]
    if not names:
        print(__doc__)
        sys.exit(0)
    print(json.dumps(build_map(names), indent=2, ensure_ascii=False))
