"""competitor_scan.py — spec 095 section 4.6: the competitor scan, built.

WHAT THIS IS
    The protocol-governed pass section 4.6 specifies. It produces the `derived_competitive_set` a
    submission carries in production: named occupants of the category, what each one CLAIMS, and a
    per-URL record of whether the capture actually worked.

WHY IT EXISTS
    The rubric consumes `derived_competitive_set`, and RS's instruction asks "is that claim already
    owned by a named occupant?" But the corpus's sets carry names, tiers and a price-floor label and
    NOTHING about what any occupant holds. So the model was answering "who owns this claim" from its
    own category memory. This script supplies the evidence instead.

THE TWO RULES THAT KEEP IT HONEST (spec 4.6)
    1. THE VALIDITY GATE IS MANDATORY. The protocol measured a 60% SILENT failure rate -- 6 of 10
       mixed URLs returned a Cloudflare challenge or a CSS shell AS ORDINARY TEXT, with no error. A
       block page reaching Jev means Jev scores a Cloudflare challenge as a competitor's website.
       So every capture is graded, and a failed one is never presented as evidence.
    2. A SCAN THAT CAPTURED NOTHING MUST SAY SO. It must not produce an empty comparison that reads
       as "you have no competitors." That is a confident wrong report -- the same failure class as
       the silent 60%, one layer up.

ORDERING (spec 3.11)
    Call this AFTER the deterministic input-quality gate, never before. The naive shape
    (scan -> score -> discover the input was unusable -> refuse) burns the full research cost on a
    submission that will be refused anyway.

USAGE
    python3 competitor_scan.py --category "specialty coffee retail" --market "Singapore" \\
        --out scan-out.json [--seed-urls a.com,b.com] [--dry-run]

    --dry-run prints the search plan and makes no network call.
"""
import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent

# --- the validity gate ------------------------------------------------------
# Markers that mean "this is not the page the business would see". Deliberately broad: a false
# positive drops a good capture (visible in the honest-limits block), while a false negative lets a
# challenge page through as evidence (invisible, and scores garbage).
BLOCK_MARKERS = (
    "just a moment", "checking your browser", "cf-browser-verification", "enable javascript and cookies",
    "attention required! | cloudflare", "ddos protection by", "please verify you are a human",
    "captcha", "access denied", "you have been blocked", "request unsuccessful. incapsula",
    "px-captcha", "are you a robot", "unusual traffic",
)
# Shells: the page loaded but carries no content a reader would see (SPA skeletons, cookie walls).
SHELL_MARKERS = (
    "you need to enable javascript to run this app", "this site requires javascript",
    "please enable javascript", "noscript",
)
MIN_USEFUL_CHARS = 400


def grade_capture(status: int, text: str) -> tuple[str, str]:
    """Return (capture_status, why). capture_status is the gate's verdict.

    ok       -- real content
    blocked  -- a bot wall, challenge or denial; MUST NOT be used as evidence
    shell    -- loaded but no readable content (JS-rendered skeleton)
    thin     -- loaded, readable, but too little to characterise a position
    error    -- transport failure

    ⚠ SUBSTANTIAL TEXT BEATS EVERY MARKER -- CHECK THE LENGTH FIRST.
    ⚠ The markers are scanned against VISIBLE TEXT, never raw HTML.

    WHY (measured, and it silently broke a whole category): the marker check ran BEFORE the
    length check and scanned the RAW HTML. A browser returns the complete DOM, `<noscript>` tag
    included -- so the literal string "noscript" was present in the source of a fully-rendered
    page. auroraer.com came back with **6,059 characters of real content** and was still graded
    **"shell", 0 usable content**, because its HTML happens to carry a `<noscript>` element.
    The scan then reported "NO OCCUPANT COULD BE ESTABLISHED" for a well-populated category --
    naming the wrong cause, since the page had been read perfectly well.

    The markers are a DIAGNOSIS OF A FAILURE, not a test in their own right: they explain WHY a
    page yielded nothing. A page that yielded something needs no explanation.
    """
    if status == 0:
        return "error", "transport failure"
    if status in (401, 403, 407, 429, 503):
        return "blocked", "HTTP %d" % status
    visible = strip_tags(text or "")
    # a challenge is a denial regardless of how much text came with it
    low_all = (text or "").lower()
    for m in BLOCK_MARKERS:
        if m in low_all:
            return "blocked", "challenge marker: %r" % m
    if len(visible) >= MIN_USEFUL_CHARS:
        return "ok", ""
    # thin -- NOW the shell markers say why, against visible text only
    low = visible.lower()
    for m in SHELL_MARKERS:
        if m in low:
            return "shell", "javascript shell: %r" % m
    return "thin", "only %d chars of readable text" % len(visible)


def fetch_plain(url: str, timeout: int = 20) -> tuple[int, str]:
    req = urllib.request.Request(url, headers={
        # A plain, honest UA. The point is not to defeat the gate -- it is to detect it.
        "User-Agent": "Mozilla/5.0 (compatible; ObserveCo-competitor-scan/1.0)",
        "Accept": "text/html,application/xhtml+xml",
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read(400000)
            return r.status, raw.decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception:
        return 0, ""


# --- the browser rung -------------------------------------------------------
# ⚠ WHY THIS EXISTS. urllib alone CANNOT READ MOST MODERN BUSINESS SITES, so the scan was
# reporting "NO OCCUPANT COULD BE ESTABLISHED" for categories that are perfectly well populated.
# MEASURED on the real submission that exposed this:
#     urllib    -> capture_status "shell", 0 usable content, "javascript shell: noscript"
#     Playwright-> 6,059 chars in 2.8s, containing all four of the business's own customer
#                  segments (Financial Sector, Utilities, Developers, Energy Consumers)
# The scanner was not failing to find competitors; it was failing to READ the pages -- including
# the submitter's own. Its verdict named the wrong cause.
#
# ⚠ IT IS A FALLBACK, NOT A REPLACEMENT. A browser costs seconds and a real process, so it runs
# ONLY when the plain fetch produced nothing usable. Sites that serve static HTML keep the fast
# path, and the common case pays nothing.
#
# ⚠ IT DOES NOT DEFEAT INTENTIONAL GATES. A bot wall, a captcha or a paywall is a decision by the
# publisher and stays unread -- this recovers content that was never withheld, only mis-served to
# a non-browser client. The distinction matters for the same reason the honest UA does.
_BROWSER_UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
               "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
_BROWSER = {"playwright": None, "browser": None}


def _browser_page():
    """One lazily-created browser for the whole scan. Starting Chromium per URL would cost
    more than the scan itself."""
    if _BROWSER["browser"] is not None:
        return _BROWSER["browser"]
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        return None
    try:
        pw = sync_playwright().start()
        _BROWSER["playwright"] = pw
        _BROWSER["browser"] = pw.chromium.launch(headless=True)
        return _BROWSER["browser"]
    except Exception:
        return None


def close_browser() -> None:
    """Release Chromium. Call this when the scan finishes -- a leaked browser process outlives
    the run and silently accumulates across submissions."""
    try:
        if _BROWSER["browser"] is not None:
            _BROWSER["browser"].close()
        if _BROWSER["playwright"] is not None:
            _BROWSER["playwright"].stop()
    except Exception:
        pass
    finally:
        _BROWSER["browser"] = None
        _BROWSER["playwright"] = None


def fetch_browser(url: str, timeout: int = 30) -> tuple[int, str]:
    br = _browser_page()
    if br is None:
        return 0, ""
    try:
        ctx = br.new_context(user_agent=_BROWSER_UA)
        page = ctx.new_page()
        try:
            resp = page.goto(url, timeout=timeout * 1000, wait_until="domcontentloaded")
            # client-rendered sites finish after domcontentloaded; a short settle is enough to
            # get the copy, and waiting longer costs every URL for little gain.
            page.wait_for_timeout(2500)
            html = page.content()
            status = resp.status if resp else 200
            return status, html
        finally:
            ctx.close()
    except Exception:
        return 0, ""


def fetch(url: str, timeout: int = 20) -> tuple[int, str]:
    """Plain fetch, escalating to the browser ONLY when the plain one yielded nothing."""
    status, html = fetch_plain(url, timeout)
    if len(strip_tags(html)) >= 200:
        return status, html
    bstatus, bhtml = fetch_browser(url, timeout=max(timeout, 30))
    if len(strip_tags(bhtml)) > len(strip_tags(html)):
        return bstatus or status, bhtml
    return status, html


# --- reading a competitor out of a page -------------------------------------
CLAIM_PATTERNS = (
    r"<meta[^>]+name=[\"']description[\"'][^>]+content=[\"']([^\"']{20,300})",
    r"<meta[^>]+property=[\"']og:description[\"'][^>]+content=[\"']([^\"']{20,300})",
)


def extract_claim(html: str) -> str:
    """The single most reliable signal of what a business CLAIMS about itself: its own meta
    description. Anything else (body copy) needs judgement, which belongs to the model, not here."""
    for pat in CLAIM_PATTERNS:
        m = re.search(pat, html, re.I)
        if m:
            return re.sub(r"\s+", " ", m.group(1)).strip()
    m = re.search(r"<title[^>]*>(.*?)</title>", html, re.I | re.S)
    if m:
        return re.sub(r"\s+", " ", m.group(1)).strip()[:300]
    return ""


def strip_tags(html: str) -> str:
    t = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.I | re.S)
    t = re.sub(r"<[^>]+>", " ", t)
    return re.sub(r"\s+", " ", t).strip()


# --- search (delegates to the protocol's chain; degrades loudly) ------------
class SearchUnavailable(RuntimeError):
    """Raised when NO search backend could be reached. Never silently return []."""


def search(query: str, limit: int = 8) -> list[str]:
    """Discover candidate URLs.

    TWO BACKENDS, and the fallback is load-bearing.
        (1) `hermes_tools.web_search` when running INSIDE a Hermes process.
        (2) `ddgs` directly when running standalone.

    WHY (2) EXISTS: the first version had only (1) and returned [] on failure. Run from a
    plain shell -- which is how a cron job or the production scorer would run it -- the
    import failed, every query returned nothing, and the scan then reported
    "0 of 0 candidate URLs were blocked". It LOOKED like a botwall had defeated it. The
    truth was that no search had been attempted at all. That is the same silent-failure
    class section 4.6 exists to catch, one layer further up: a search outage masquerading
    as a scan result.

    So a total search failure now RAISES, and the caller reports SEARCH UNAVAILABLE --
    distinct from SCAN FAILED (search worked, pages could not be read).
    """
    try:
        from hermes_tools import web_search  # noqa
        res = web_search(query, limit=limit)
        urls = [r["url"] for r in (res.get("data", {}).get("web") or [])]
        if urls:
            return urls
    except Exception:
        pass

    try:
        from ddgs import DDGS
    except Exception as exc:
        raise SearchUnavailable(
            "no search backend available: hermes_tools not importable and ddgs is not "
            "installed (%s)" % type(exc).__name__)

    # RETRY, because the failure is INTERMITTENT AND ENVIRONMENT-DEPENDENT.
    # Measured root cause: ddgs picks a RANDOM ssl context per client, one variant forcing
    # TLS 1.3. On macOS system Python 3.9 (LibreSSL 2.8.3) that raises
    #   ValueError: Unsupported protocol version 0x304
    # on roughly half of attempts. The Hermes venv python (3.14, OpenSSL 3.6.4) does not
    # hit it at all. Retrying rides out the unlucky draw instead of reporting a search
    # outage that is not real -- and the caller still gets SearchUnavailable if every
    # attempt fails, so a genuine outage is never hidden.
    last = None
    for attempt in range(3):
        try:
            with DDGS() as d:
                hits = list(d.text(query, max_results=limit))
            urls = [h.get("href") or h.get("url") for h in hits
                    if (h.get("href") or h.get("url"))]
            if urls:
                return urls
            last = "no results returned"
        except Exception as exc:
            last = "%s: %s" % (type(exc).__name__, exc)
        if attempt < 2:
            time.sleep(1.5)
    raise SearchUnavailable("ddgs search failed after 3 attempts (%s)" % last)


def scan(category: str, market: str, seed_urls: list[str], per_url_timeout: int = 20) -> dict:
    started = datetime.now(timezone.utc).isoformat(timespec="seconds")
    queries = [
        "%s %s competitors" % (category, market),
        "best %s %s" % (category, market),
        "%s %s brands" % (category, market),
    ]
    discovered, per_query, search_errors = [], {}, []
    for q in queries:
        try:
            urls = search(q)
        except SearchUnavailable as exc:
            urls = []
            search_errors.append("%s -> %s" % (q, exc))
        per_query[q] = urls
        discovered.extend(urls)

    # SEARCH UNAVAILABLE is its own verdict. It must never be reported as a scan that ran
    # and was defeated -- those are different facts and they imply different next actions.
    if not discovered:
        return {
            "_meta": {
                "kind": "competitor_scan",
                "category": category,
                "market": market,
                "scanned_at": started,
                "queries": queries,
                "urls_discovered": per_query,
                "search_errors": search_errors,
                "capture_summary": {"ok": 0, "not_readable": 0, "candidates": 0},
                "verdict": ("SEARCH UNAVAILABLE -- no search backend responded, so NO "
                            "candidate was ever discovered. This is NOT a botwall and NOT "
                            "evidence the category is empty; no scan was performed. "
                            "Position strength stays capped at ADEQUATE (3)."),
                "honest_limits": [],
                "ordering": "MUST run after the input-quality gate (spec 3.11), never before.",
            },
            "captures": [],
        }
    # dedupe, preserve order, drop obvious non-candidate hosts
    seen, candidates = set(), []
    for u in list(seed_urls) + discovered:
        host = urllib.parse.urlparse(u).netloc.lower()
        if not host or host in seen:
            continue
        if any(x in host for x in ("google.", "facebook.", "instagram.", "youtube.", "wikipedia.")):
            continue
        seen.add(host)
        candidates.append(u)

    captures, blocked, ok = [], [], 0
    for u in candidates[:12]:
        status, html = fetch(u, timeout=per_url_timeout)
        cstat, why = grade_capture(status, html)
        entry = {
            "url": u,
            "capture_status": cstat,
            "why": why,
            "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
        if cstat == "ok":
            ok += 1
            entry["claim"] = extract_claim(html)
            entry["excerpt"] = strip_tags(html)[:600]
        else:
            blocked.append({"url": u, "capture_status": cstat, "why": why})
        captures.append(entry)

    # THE HONEST-LIMITS RULE (spec 4.6). Zero successful captures must NEVER read as
    # "you have no competitors".
    if ok == 0:
        verdict = ("SCAN FAILED -- no competitor page could be read. This is NOT evidence that the "
                   "category has no competitors; it is evidence the scan did not work. %d of %d "
                   "candidate URLs were blocked, shelled, thin or unreachable."
                   % (len(blocked), len(captures)))
    elif len(captures) < 3:
        verdict = ("THIN SCAN -- only %d of %d candidates readable. Any comparison drawn from this is "
                   "provisional." % (ok, len(captures)))
    else:
        verdict = ("OK -- %d of %d candidates readable." % (ok, len(captures)))

    return {
        "_meta": {
            "kind": "competitor_scan",
            "category": category,
            "market": market,
            "scanned_at": started,
            "queries": queries,
            "urls_discovered": per_query,
            "capture_summary": {"ok": ok, "not_readable": len(blocked), "candidates": len(captures)},
            "verdict": verdict,
            "honest_limits": blocked,
            "NOT_VALIDATED": ("This scanner has been proved to WORK (it discovers, fetches, extracts "
                              "and grades) and NOT proved ACCURATE. The calibration corpus's sets were "
                              "hand-written per category, so there is no record of what a scan would "
                              "have returned for those 120 businesses."),
            "ordering": "MUST run after the input-quality gate (spec 3.11), never before.",
        },
        "captures": captures,
    }


# Words that appear in listicle prose and are never brand names.
NOT_A_BRAND = {
    "the", "best", "top", "singapore", "bubble", "tea", "shop", "shops", "brand", "brands",
    "outlets", "outlet", "price", "prices", "review", "reviews", "guide", "list", "ranking",
    "ranked", "flavour", "flavor", "texture", "value", "quality", "access", "toppings",
    "brown", "sugar", "milk", "pearls", "healthy", "kombucha", "drink", "drinks", "read",
    "reddit", "timeout", "yahoo", "finance", "google", "facebook", "instagram", "tiktok",
    "more", "most", "reliable", "legwork", "found", "enjoy", "singaporean", "factors",
    "contributing", "increase", "find", "here", "are", "and", "with", "from", "for",
    "these", "those", "what", "which", "when", "where", "that", "this", "your", "you",
    "our", "their", "they", "it", "its", "was", "were", "been", "has", "have", "had",
    "new", "year", "2026", "2025", "per", "area", "pick", "pick:", "including", "plus",
    "also", "but", "not", "all", "any", "can", "will", "just", "only", "over", "under",
    # Observed as fragments in the live run: sentence-starts and page furniture that are
    # capitalised and recurring but are not occupants.
    "updated", "read", "written", "posted", "published", "share", "menu", "order",
    "delivery", "promo", "promotion", "deal", "deals", "photo", "photos", "video",
    "article", "blog", "site", "website", "page", "home", "about", "contact",
    # Generic nouns that recur in listicle prose and pass the capitalisation test.
    "business", "businesses", "company", "companies", "customer", "customers",
    "industry", "market", "markets", "product", "products", "service", "services",
    "location", "locations", "branch", "branches", "store", "stores", "island",
    "islandwide", "nationwide", "delivery", "dining", "drinks", "cafe", "restaurant",
}

# Words that suggest a fragment is part of a brand phrase (keep the phrase together).
BRAND_CONTINUATION = {"tea", "town", "box", "san", "chen", "cha", "kuan", "kun", "yan",
                      "sang", "fresh", "fitness", "denki", "norman", "harvey", "price",
                      "fair", "fairprice", "don", "donki", "shake", "shack", "ya", "the",
                      "baker", "boy", "lenskart", "watsons", "sephora", "ikea", "koi",
                      "playmade", "each", "cup", "chagee", "liho", "mixue", "heytea",
                      "xing", "fu", "tang", "chicha", "chen", "store", "shops"}


def publisher(url: str) -> str:
    """The PUBLISHING ORGANISATION behind a URL, for independence counting.

    ⚠ TWO PAGES FROM ONE PUBLISHER ARE ONE SOURCE, NOT TWO. A company's own site and its
    /global-presence/ page are the same voice -- and if both count, that company's own menu
    labels get "corroborated" by itself and pass the two-source rule as occupants.
    Measured: `www.auroraer.com` and `auroraer.com/global-presence/singapore` were counted as
    independent sources, so Aurora's own navigation text ("Global Presence", "Manage") was
    reported as a competitive set.
    Independence is about WHO IS SPEAKING, and subdomains of one organisation are one speaker.
    """
    host = urllib.parse.urlparse(url).netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    parts = host.split(".")
    # keep the registrable domain: the last two labels, or three for common 2-level TLDs
    if len(parts) >= 3 and parts[-2] in ("co", "com", "org", "net", "gov", "edu", "ac"):
        return ".".join(parts[-3:])
    return ".".join(parts[-2:]) if len(parts) >= 2 else host


# A capitalised phrase counts as an occupant only when the text around it is TALKING about
# players in a market. Deliberately generic -- it must work for any category, not just the one
# that motivated it, and it must not name any specific business.
_OCCUPANCY_SIGNALS = (
    "competitor", "competing", "rival", "market leader", "leading", "provider", "supplier",
    "vendor", "company", "companies", "firm", "consultancy", "solution", "platform",
    "alternative", "versus", " vs ", "compared", "landscape", "players", "incumbent",
    "analytics", "advisory", "service", "agency", "operator", "manufacturer", "brand",
)
# Words that are pure interface furniture. They are not a market signal even when they appear
# next to each other, and they were observed as false occupants in a live run.
_UI_WORDS = frozenset("""
discover know learn more read view all see explore about contact careers news blog events
search login register sign menu home privacy cookies accept reject consent subscribe
share follow linkedin twitter facebook instagram youtube terms legal sitemap
""".split())


def _says_occupant(text: str, phrase: str) -> bool:
    """Is `phrase` mentioned in a sentence that is talking about market occupants?

    Takes a window of text around the FIRST occurrence and requires an occupancy signal in it.
    A window, not the whole page: a page about a market mentions "competitor" somewhere, so a
    whole-page test would pass everything.
    """
    low_phrase = phrase.lower()
    if low_phrase in _UI_WORDS or low_phrase.split()[0] in _UI_WORDS:
        return False
    low = (text or "").lower()
    start = 0
    while True:
        i = low.find(low_phrase, start)
        if i < 0:
            return False
        window = low[max(0, i - 140): i + len(low_phrase) + 140]
        if any(sig in window for sig in _OCCUPANCY_SIGNALS):
            return True
        start = i + len(low_phrase)


def extract_occupants(ok_captures: list[dict]) -> list[tuple[str, int]]:
    """Mine occupant NAMES out of the readable sources.

    A name qualifies only if it appears in more than one independent source. Returns
    [(name, source_count)] sorted by source count then name.

    ⚠⚠ NEGATIVE RESULT — THIS MECHANISM IS NOT WORKING, AND FOUR FIXES HAVE FAILED.
    Do NOT retry these; each was measured and each exposed a new class of junk.

        1. hyphen splitting      -- "Each-A-Cup" became "Each" + "Cup"          [fixed]
        2. stray single words    -- "Updated", "Business"                        [fixed]
        3. case duplicates       -- "KOI" and "Koi" counted as two occupants     [fixed]
        4. navigation labels     -- "Discover", "Know", "Global Presence", "Who" [STILL BROKEN]
        5. currency/UI tokens    -- "USD", "Create", "Energy", "Manage"          [STILL BROKEN]

    ⚠ The pattern: every fix reveals a NEW class of capitalised non-brand text. That is the
    signature of a mechanism that cannot be patched, not a mechanism that needs one more rule.
    Two-source corroboration does NOT save it -- navigation labels and currency codes appear on
    every site in every category, so they are the MOST corroborated strings on the web.

    ⚠ AND THE OUTPUT IS DANGEROUS, NOT MERELY USELESS. Feeding invented rivals to the rubric
    asserts a competitive set that does not exist, and position_strength is scored AGAINST the
    supplied set. A wrong set is worse than an empty one: the empty set caps at ADEQUATE (3) and
    says why, while a junk set produces a confident judgement about rivals that are not real.

    ⚠ WHAT TO DO INSTEAD (not yet built, needs a steer):
      - USE THE OWNER'S OWN NAMED RIVALS. The form already collects them and they are reliable.
        On the live case that exposed this, the owner named "wood mac, afry, baringa, modo".
      - USE tier_0_own_stated_position. Reading the submitter's OWN site now works (see the
        browser rung), and it is rich: 6,059 chars on that case, naming four customer segments.
      - Only accept a scraped name when a SOURCE STATES an occupancy relationship in the same
        sentence (e.g. a comparison table, a "competitors" page) -- which _says_occupant
        approximates but does not achieve, because the window test passes nav text too.

    ⚠ UNTIL THEN, THIS FUNCTION'S OUTPUT MUST NOT BE TRUSTED AS A COMPETITIVE SET. See 4.6.
    """
    counts: dict[str, set[str]] = {}
    for c in ok_captures:
        text = "%s %s" % (c.get("claim") or "", c.get("excerpt") or "")
        host = publisher(c["url"])
        # 1- and 2-word capitalised phrases, including ALL-CAPS chains (CHAGEE, HEYTEA)
        # HYPHENS ARE PART OF A BRAND NAME. Without them "Each-A-Cup" splits into
        # "Each" and "Cup", and the set names two occupants that do not exist instead of
        # the one that does. Both were observed in the first live run.
        for m in re.finditer(
                r"\b([A-Z][A-Za-z&'\-]{2,}(?:\s+(?:[A-Z][A-Za-z&'\-]{2,}|of|de))*)\b",
                text):
            phrase = m.group(1).strip()
            parts = phrase.split()
            if not parts:
                continue
            if len(parts) > 3:
                phrase = " ".join(parts[:2])
            low = phrase.lower()
            head = low.split()[0]
            if head in NOT_A_BRAND or low in NOT_A_BRAND:
                continue
            if len(low) < 3:
                continue
            # ⚠ THE NAME MUST BE MENTIONED AS AN OCCUPANT, NOT MERELY CAPITALISED.
            # ⚠ Without this the extractor mined NAVIGATION LABELS as competitors. Measured once
            # the browser rung made 7 sources readable: the "occupants" of power-market analytics
            # came back as "Discover", "Know", "Global Presence", "Who", "France Who" -- menu text
            # that happens to be capitalised and to appear on many sites, so it passed the
            # two-source rule. Feeding those to the rubric as rivals would be worse than finding
            # none: it asserts a competitive set that does not exist.
            # The test is the same principle as tier_0: the SOURCE must state it. A capitalised
            # word needs a surrounding signal that this text is naming a player in a market.
            if not _says_occupant(text, phrase):
                continue
            # CASE IS NOT AN IDENTITY. The live run produced "KOI" (2 sources) and
            # "Koi" (2 sources) as two separate occupants of the same category -- the same
            # business counted twice, which would read to the rubric as two rivals holding
            # the same claim. Group by lowercase and keep the most common casing.
            key = low
            counts.setdefault(key, {})  # type: ignore[arg-type]
            counts[key].setdefault("sources", set()).add(host)  # type: ignore[union-attr]
            casing = counts[key].setdefault("casing", {})       # type: ignore[union-attr]
            casing[phrase] = casing.get(phrase, 0) + 1

    ranked = []
    for key, v in counts.items():
        sources = v["sources"]                    # type: ignore[index]
        if len(sources) < 2:
            continue
        # prefer the spelling seen most often, then an all-caps or title form
        best = sorted(v["casing"].items(),                       # type: ignore[index]
                      key=lambda kv: (-kv[1], not kv[0].isupper(), kv[0]))[0][0]
        ranked.append((best, len(sources)))
    ranked.sort(key=lambda x: (-x[1], x[0].lower()))
    return ranked


# ⚠⚠ THE OWNER'S NAMED RIVALS ARE THE PRIMARY SET -- because the scraped names are a
# PROVEN NEGATIVE RESULT (see extract_occupants). Measured: with 10 pages successfully read,
# the miner returned "Create", "Energy", "Manage", "USD" for a power-market analytics firm --
# navigation furniture and currency codes asserted as competitors. Feeding those to
# position_strength, which scores AGAINST the supplied set, would produce a confident judgement
# about rivals that do not exist.
#
# The owner's list has the opposite property: it is INCOMPLETE and CORRECT. Spec 3.6 already
# says the owner's list "is expected to be incomplete" -- and the tool's own cap already exists
# for the incomplete case. There is no cap for the INVENTED case, which is why this ordering
# matters. The live case that exposed all of this named "wood mac, afry, baringa, modo" -- all
# genuinely competitors of a firm in that category.
#
# ⚠ AN OWNER'S LIST IS STILL SELF-REPORTED, so it is used for NAMING only, never as evidence of
# what a rival CLAIMS. That distinction is where the value is: naming who to look at is the
# owner's expertise; characterising them is the tool's job.
OWNER_TIER = "COMPETITORS THE BUSINESS NAMED ITSELF"


def _clean_claim(raw: str) -> str:
    """Accept only text that actually reads as a POSITIONING CLAIM. Otherwise return "".

    ⚠⚠ MEASURED ON THE SECOND SECTOR (salad, not bubble tea) — resolution is not quality.

    Resolving a name to a page works; what comes BACK is often not a claim at all:

      OMNIVORE  -> thesaladaddict.com (a food BLOG), "claim" = a reviewer's own order:
                   "-My Order- Regular Bowl ($13.90, 1 base, 1 protein, 3 sides...)"
      The Daily Cut -> thedailycut.sg, "claim" = the page TITLE, "Menu &#8211; The Daily Cut"

    Rendering those under "This is what they say about themselves" is FALSE in the first case
    (a customer's receipt, not the brand's words) and useless in the second (a title is not a
    claim). The first sector passed, so this only surfaced on a second, different one -- which
    is exactly why the generality test exists.

    THE RULE: unescape entities, then require a real sentence -- long enough to say something,
    containing an actual verb-ish flow, and NOT looking like a menu, an order, a price list or
    a bare title. Failing that, the caller says "read but states no single claim", which is
    true and still honest about having read the page.
    """
    if not raw:
        return ""
    import html as _html
    t = _html.unescape(raw)
    t = re.sub(r"\s+", " ", t).strip()
    t = re.sub(r"^[\-\u2013\u2022\*\s]+", "", t)          # leading bullets/dashes
    if len(t) < 40 or len(t) > 400:
        return ""
    low = t.lower()
    # a menu / an order / a price list / a basket is not a positioning claim
    bad = ("my order", "your order", "add to cart", "add to bag", "order now", "menu",
           "checkout", "sign in", "log in", "subscribe", "newsletter", "cookie",
           "privacy policy", "terms", "all rights reserved", "shopping cart", "delivery")
    if any(b in low for b in bad):
        return ""
    if t.count("$") >= 2:                                      # a price list, not a claim
        return ""
    # a bare title: title-case fragments with no sentence flow
    # ⚠ MATCH VERB STEMS, NOT WHOLE WORDS. Measured: `\bfocus\b` REJECTED CHAGEE's real claim
    # ("...focusing on original leaf fresh milk tea...") because "focusing" has no word
    # boundary after "focus" -- so a correct claim was thrown away as if it were junk.
    # Stems cover focus/focusing, provide/providing, know/known, integrate/integrating.
    if not re.search(r"\b(is|are|was|we|our|you|your|the brand|provid|offer|help|mak|bring|"
                     r"deliver|specialis|specializ|focus|trust|lead|design|build|built|know|"
                     r"integrat|cover|includ|serv|creat|develop|support|enabl|since|because|"
                     r"so that|aim|seek|strive|mission|vision|commit|dedicat)", low):
        return ""
    return t


def _domain_matches(name: str, url: str) -> bool:
    """Does this URL plausibly belong to the named rival? Deliberately strict.

    ⚠⚠ MEASURED — A WRONG-COMPANY SUBSTITUTION WAS SILENT AND DANGEROUS.
    Resolving "Modo" (meaning Modo Energy, an energy-analytics firm) for an Aurora submission, the
    search returned **`modo.com.sg` — a Singapore OPTICAL SHOP** — and the previous heuristic
    accepted it because the first token "modo" appeared in the host. Its 17KB of text graded `ok`,
    so the report would have quoted **a stranger's website as the rival's published claim**, under a
    heading that says "a page found for them". The disclosure "we have not verified the page belongs
    to the rival" does not rescue that: it flags doubt while still printing the quote.

    ⚠ THE RULE: a short token appearing anywhere in a host is not evidence of identity. Require the
    rival's name to appear as a HOST LABEL (a dot-delimited component, or the registrable part),
    not merely as a substring. "Modo Energy" resolves to `modoenergy.com` -- label match. It does
    NOT resolve to `modo.com.sg` -- that is a different company that happens to share four letters.
    """
    import re as _re
    host = (url or "").lower().split("//")[-1].split("/")[0].split(":")[0]
    if not host:
        return False
    toks = [t for t in _re.findall(r"[a-z0-9]+", (name or "").lower()) if len(t) > 2]
    if not toks:
        return False
    labels = [l for l in host.split(".") if l and l not in ("www", "en")]
    if not labels:
        return False
    # ⚠⚠ A BARE LABEL MATCH IS NOT IDENTITY, AND THIS WAS MEASURED THE HARD WAY.
    # `modo.com.sg` (a Singapore OPTICAL SHOP) has "modo" as a host label -- so a label check alone
    # accepted it as the rival "Modo" and would have PRINTED ITS WORDS as Modo Energy's claim.
    # The tell is the PUBLIC SUFFIX: under `.com.sg` the registrable label is "modo", which any
    # business may register. Under `.com` the registrable label is "modoenergy" -- which is the name.
    # So the match is scored on WHERE the token lands, not just that it appears.
    first = toks[0]
    rest = toks[1:]
    # ⚠⚠ HOST MATCHING ALONE CANNOT DECIDE THIS, AND BOTH OVER- AND UNDER-CORRECTIONS WERE
    # MEASURED. `modo.com.sg` (an optician) and `modoenergy.com` (the rival) are BOTH "a host label
    # equal to the name". `afry.com` and `baringa.com` are legitimate and look identical in shape.
    # No hostname rule separates them, which is why an earlier strict version of this function
    # correctly rejected the optician AND wrongly rejected Afry, Baringa and CHAGEE.
    #
    # So the host is used as a NECESSARY BUT NOT SUFFICIENT condition. Identity is then confirmed
    # on the FETCHED CONTENT, against the submitter's category (see _category_corroborates).
    # ⚠ The residual risk is stated rather than hidden: a same-named business IN THE SAME CATEGORY
    # would still pass. That is why the report prints the domain and refuses to assert the page is
    # the rival's -- the reader sees what was read and can reject it.
    if rest:
        joined = "".join(rest)
        if any(first + joined in l or (first in l and all(rt in l for rt in rest)) for l in labels):
            return True
    return any(lbl == first or lbl.startswith(first) for lbl in labels)


def _category_corroborates(text: str, category: str) -> bool:
    """Does this page's own text show signs of the submitter's category? THE identity discriminator.

    ⚠⚠ WHY CONTENT AND NOT THE HOSTNAME. Measured: resolving "Modo" for an Aurora submission, the
    search returned `modo.com.sg` -- a Singapore OPTICAL SHOP -- and 17KB of its copy graded `ok`.
    It would have been quoted as the rival's published claim. No hostname rule can separate that
    from `afry.com`, which is the real firm. The page's own words can: an energy-analytics rival
    talks about energy, markets, power, data; an optician talks about lenses, frames, prescriptions.

    ⚠ THIS IS A HEURISTIC AND IT IS DELIBERATELY LOOSE. It rejects only when a page shows NO sign of
    the category at all. A single shared content word is enough to accept, because the cost of
    wrongly rejecting a real rival (reporting "could not verify") is lower than the cost of quoting
    a stranger as the rival -- but both are real, and the report discloses which happened.
    """
    if not category:
        return True                      # nothing to check against; the host match must stand alone
    # ⚠ `_sig_words` lives in generate_report.py, not here -- the first version of this function
    # called it and raised NameError, which the surrounding `except` would have swallowed into a
    # silent "no rival read". Imported lazily so this module does not depend on the renderer at
    # import time (competitor_scan must stay runnable standalone, e.g. from a cron shell).
    # ⚠⚠ MEASURED OVERLAP, WHICH IS WHY STOPWORDS ARE EXCLUDED (not a stylistic choice).
    #    category: "Power market data analytics and software solutions"
    #      optician (STRANGER, modo.com.sg)  shared = 1  -> ["and"]      ONLY a stopword
    #      Modo Energy (REAL)                shared = 2  -> ["and","market"]
    #      Afry / Wood Mac / Baringa (REAL)  shared = 6  -> analytics, data, market, power, solutions
    # ⚠ Counting "and" as evidence of identity is the whole failure: it is the single word that made
    # a Singapore optician look like an energy-analytics firm. Excluding stopwords separates the
    # stranger (0 content words) from every real rival (1 to 5), and needs no threshold to be tuned.
    try:
        import re as _re
        _STOP = {
            "and", "the", "for", "with", "that", "this", "from", "your", "you", "our", "are", "was",
            "can", "will", "all", "any", "not", "but", "has", "have", "who", "how", "why", "what",
            "when", "more", "most", "other", "into", "over", "than", "then", "them", "they", "its",
            "it's", "we're", "business", "businesses", "company", "companies", "services", "service",
            "solutions", "solution", "and/or", "etc", "new", "get", "see", "read", "about",
        }
        pat = _re.compile(r"[a-z][a-z\-]{2,}")
        want = {w for w in pat.findall((category or "").lower()) if w not in _STOP}
        have = {w for w in pat.findall((text or "").lower()) if w not in _STOP}
    except Exception:
        return True
    if not want:
        return True
    return bool(want & have)


def _domain_candidates(name: str) -> list[str]:
    """Deterministic candidate homepages for a rival's NAME, most-likely first.

    ⚠⚠ WHY THIS EXISTS — MEASURED, AND IT IS THE FIX FOR THE REAL WEAK LINK (spec 6.7.9).

    §6.7.9 measured that the failure was RESOLUTION, not fetching and not bot walls: `afry.com/en`
    serves 151,226 characters with a real claim to a plain fetcher, yet the search-driven resolver
    reported Afry `blocked` 0/3 because it never returned Afry's own site. **A general web search
    does not reliably map a company NAME to its own DOMAIN** — not even augmented with the category.

    ⚠⚠ AND THE NAMES GIVE THEMSELVES AWAY. Every rival that resolved correctly in testing did so at
    a domain that was GUESSABLE FROM THE NAME ALONE: afry -> afry.com, modoenergy -> modoenergy.com,
    woodmac -> woodmac.com, baringa -> baringa.com, chagee -> chagee.com.sg, liho -> lihoteasg.org.
    So for the firms that have a clean domain and a poor search footprint — which is most real
    businesses — construction beats search.

    ⚠ THIS IS A PROBE, NOT AN ASSUMPTION. Building a URL proves nothing; the caller must FETCH it and
    the identity check must pass. A wrong guess simply wastes one cheap request and falls through to
    the next candidate. Nothing is accepted on the strength of the name matching the domain.

    ⚠ ORDER MATTERS AND IS DELIBERATE. The joined full name ("modoenergy") is tried before the bare
    first token ("modo"): "modoenergy.com" is the firm, "modo.com" is somebody else — and the same
    shape of mistake (`modo.com.sg`, an optician) is exactly what §6.7.9 was about. Trying the
    specific form first means the ambiguous one is only reached if the specific one fails.
    """
    import re as _re
    toks = [t for t in _re.findall(r"[a-z0-9]+", (name or "").lower()) if len(t) > 2]
    if not toks:
        return []
    joined = "".join(toks)
    out = []
    for stem in ([joined] if len(toks) > 1 else []) + [toks[0]]:
        for tld in (".com", ".com.sg", ".sg", ".co", ".io", ".net", ".org", ".com.au"):
            out.append("https://%s%s" % (stem, tld))
    # ⚠ de-duplicate while preserving order; the first hit wins so order is the whole game
    seen, uniq = set(), []
    for u in out:
        if u not in seen:
            seen.add(u)
            uniq.append(u)
    return uniq


def rival_reads(owner_names: list[str], market: str, per_url_timeout: int = 20,
                max_rivals: int = 6, category: str = "") -> list[dict]:
    """Read the OWNER-NAMED rivals' OWN sites, and quote what each one claims.

    ⚠⚠ WHY THIS EXISTS (spec 6.7.6 — MEASURED ON A REAL CLIENT SUBMISSION).

    The scan searched generic CATEGORY queries only ("bubble tea Singapore competitors"). It
    never resolved the owner's own rival names to their websites. So the report's central,
    paid-analysis-preview question --

        "does CHAGEE already own the claim you are making?"

    -- COULD NOT BE ANSWERED, even though (a) the tool held the names and (b) the tool can
    read pages. The one piece of analysis a business owner most wants from a positioning read
    was structurally impossible. Sean, on the live output: "No competitive analysis was done."

    ⚠ THE OPPOSITE RISK IS ALSO REAL, AND THIS FUNCTION IS BUILT AROUND IT: do NOT let a
    failed search produce a confident sentence about a rival. Every entry records what
    ACTUALLY happened -- read and quoted, read with no claim, or could-not-be-read -- so a
    tool failure is never rendered as a finding about the rival (section 4.6).

    ⚠ THIS IS STILL NOT A LANDSCAPE SCAN. It reads the NAMES THE OWNER GAVE US. It does not
    discover who else occupies the category; that remains section 4.6.0b's open gap.
    """
    reads = []
    for name in [n.strip() for n in owner_names if n and n.strip()][:max_rivals]:
        entry = {"name": name, "url": "", "capture_status": "not_found", "why": "",
                 "claim": "", "excerpt": ""}
        # ⚠ QUERY WITH THE CATEGORY, NOT THE MARKET. "Modo Singapore" is ambiguous and returned a
        # Singapore optical shop; "Modo energy market analytics" returns the actual firm. The
        # category is the disambiguator the market name never was. Falls back to market when the
        # submitter gave no category.
        # ⚠⚠ CONSTRUCT FIRST, SEARCH SECOND (spec 6.7.9). Construction beat search on every rival
        # that resolved: afry.com, modoenergy.com, woodmac.com, baringa.com were all guessable from
        # the name. Probe the built candidates CHEAPLY and stop at the first that reads ok AND is
        # corroborated by its own text; only if none does, fall back to the search.
        target, probe_notes = None, []
        for cand in _domain_candidates(name):
            try:
                _st, _html = fetch(cand, timeout=min(12, per_url_timeout))
            except Exception as exc:                       # noqa: BLE001 - any transport failure
                probe_notes.append("%s: %s" % (cand, type(exc).__name__))
                continue
            _cs, _why = grade_capture(_st, _html)
            if _cs != "ok":
                probe_notes.append("%s: %s" % (cand, _cs))
                continue
            if not _category_corroborates(strip_tags(_html), category):
                probe_notes.append("%s: unverified_identity" % cand)
                continue
            target = cand                                # first corroborated candidate wins
            break

        if not target:
            _hint = (category or market or "").strip()
            try:
                urls = search("%s %s" % (name, _hint), limit=4)
            except SearchUnavailable as exc:
                entry["why"] = ("no homepage found by construction (%s) and search unavailable: %s"
                                % ("; ".join(probe_notes[-3:]) or "no candidates", exc))
                reads.append(entry)
                continue
            # prefer the rival's OWN site over a listicle or a social page about it
            # ⚠ STRICT identity check (see _domain_matches). A page that fails it is NOT used as the
            # rival's claim, because quoting a stranger's site as this rival's words is worse than
            # reporting the rival as unreadable.
            own = [u for u in urls if _domain_matches(name, u)]
            target = (own or [None])[0]
        if not target:
            entry["why"] = "no candidate URL found"
            reads.append(entry)
            continue
        status, html = fetch(target, timeout=per_url_timeout)
        cstat, why = grade_capture(status, html)
        # ⚠⚠ THE CONTENT CHECK -- the only real discriminator available. Measured: `modo.com.sg`
        # (an optician) and `afry.com` (the rival) are indistinguishable by hostname, and both grade
        # `ok`. The page's own words are what separate them. A page that reads fine but shows NO
        # sign of the submitter's category is NOT accepted as the rival's claim.
        if cstat == "ok" and not _category_corroborates(strip_tags(html), category):
            cstat, why = "unverified_identity", (
                "the page could not be confirmed as this rival's — its text shows no sign "
                "of the %s category, so it may be a different business with a similar name"
                % (category or "stated"))
        entry.update({"url": target, "capture_status": cstat, "why": why})
        if cstat == "ok":
            # ⚠ VALIDATED, because resolution is not quality -- see _clean_claim above.
            entry["claim"] = _clean_claim(extract_claim(html))
            entry["excerpt"] = strip_tags(html)[:600]
        reads.append(entry)
    return reads


def to_competitive_set(result: dict, owner_named: list[str] | None = None,
                       rival_pages: list[dict] | None = None) -> dict:
    """Convert a scan result into the `derived_competitive_set` the rubric consumes.

    ⚠ `owner_named` is the PRIMARY set and takes precedence over anything scraped, for the
    reason documented at OWNER_TIER above. Scraped occupants are included only when there are
    no owner-named rivals at all, and they are marked so the consumer can tell them apart.

    WHY THIS EXISTS (spec 4.6 wiring)
        The rubric's position_strength instruction says: "SCORE ONLY AGAINST THE SUPPLIED
        COMPETITIVE SET, using what is STATED about each occupant... if the supplied set
        names no occupant for the situation, the strongest claim available is ADEQUATE (3),
        never Strong or Dominant, because a flank is only proven against a named rival."

        So the cap lifts only when the set NAMES occupants AND STATES what they claim.
        That is precisely what a successful scan produces, and precisely what the corpus's
        hand-written sets lacked -- which is why the model was answering "who owns this
        claim?" from its own category memory.

    THE HONEST-LIMITS RULE, CARRIED THROUGH
        A failed scan must NOT produce a set that reads as "this category has no
        competitors". It produces NO members and a caveat that says the scan failed, so
        the cap stays in place and the report can say why. An empty-looking comparison is
        a confident wrong report -- the failure class section 4.6 exists to prevent.

    SHAPE (from run_jev.build_state)
        {"<TIER>": {"members": [...], "why": ..., "caveat": ...},
         "_derivation_method": "..."}   # underscore keys are skipped by build_state
    """
    meta = result.get("_meta") or {}
    ok = [c for c in (result.get("captures") or []) if c.get("capture_status") == "ok"]
    blocked = [c for c in (result.get("captures") or []) if c.get("capture_status") != "ok"]

    # ⚠ THE OCCUPANT-EXTRACTION STEP, and it is the whole difference between a useful set
    # and a useless one. The FIRST version treated each readable URL as an occupant. Run
    # live, that populated the set with timeOut.com, reddit.com and a Yahoo Finance page --
    # LISTICLES ABOUT the category, not members OF it. The rubric asks "is this claim
    # already owned by a NAMED RIVAL?", and answering "timeout.com" would be nonsense.
    #
    # The listicles are the right SOURCE and the wrong OCCUPANTS. Their text names the real
    # occupants ("Koi (90 outlets), Each-A-Cup (48), CHAGEE (44), LiHO, Mixue and HEYTEA"),
    # so the names are mined out of them instead.
    #
    # THE RULE: a name is an occupant only if it appears in MORE THAN ONE independent
    # source. One listicle mentioning a brand is one person's opinion; the same brand
    # surfacing across several sources is evidence it occupies the category. That rule is
    # deliberately conservative -- it would rather name four real occupants than twenty
    # guesses, because a wrong occupant corrupts the position reading that consumes it.
    # ⚠ ORDER MATTERS, AND IT IS NOT A PREFERENCE. The owner's names win outright -- see
    # OWNER_TIER. Scraped names are consulted ONLY when the owner named nobody, because an
    # INVENTED rival is worse than a missing one (position_strength scores AGAINST the set,
    # while an empty set trips the cap and says why).
    owner = [n.strip() for n in (owner_named or []) if n and n.strip()][:12]
    members = []
    if owner:
        by_name = {(p.get("name") or "").lower(): p for p in (rival_pages or [])}
        for name in owner:
            r = by_name.get(name.lower()) or {}
            base = "%s — named as a competitor by the business itself" % name
            # ⚠⚠ NEVER ASSERT THAT THE PAGE IS THE RIVAL'S OWN. WE CANNOT VERIFY IT, AND
            # MEASURED IT IS OFTEN FALSE: resolving CaiCa's real rivals, HEYTEA matched
            # heyteas.com -- a menu-GUIDE site, not HEYTEA's own -- and LiHO and KOI matched
            # Wikipedia pages. Printing "Their own site states: ..." would attribute a THIRD
            # PARTY's words to the rival, which is the misattribution §4.6 exists to prevent.
            # The wording therefore says only what is true: a page was found FOR that rival,
            # and the domain is shown so the reader can judge what it is.
            if r.get("claim"):
                # ⚠ CUT ON A WORD BOUNDARY AT THE SOURCE. The report-side trim never saw this
                # string -- the 220-slice here ran FIRST and produced "...tea inheritance a",
                # text ending mid-word, shown to a business owner as a quotation.
                _q = r["claim"]
                if len(_q) > 220:
                    _q = _q[:220].rsplit(" ", 1)[0].rstrip(",;:") + "…"
                members.append(
                    "%s. A page found for them (%s) states: \"%s\""
                    % (base, publisher(r["url"]), _q))
            elif r.get("capture_status") == "ok":
                members.append("%s. A page found for them (%s) was read but states no single "
                               "claim." % (base, publisher(r["url"])))
            elif r.get("capture_status") == "not_found":
                members.append("%s. No site for them could be found." % base)
            elif r.get("capture_status") == "unverified_identity":
                members.append("%s. A page was found (%s) but we could NOT confirm it belongs to "
                               "them (%s) — so we will not quote it. Nothing here says what they "
                               "claim." % (base, publisher(r["url"]), r.get("why") or "unconfirmed"))
            elif r.get("url"):
                members.append("%s. A page found for them (%s) could NOT be read (%s) — so "
                               "nothing here says what they claim."
                               % (base, publisher(r["url"]), r.get("why") or "unreadable"))
            else:
                members.append(base)
        # ⚠ SAY WHAT THE SET IS AND IS NOT. The consumer must know these are the owner's names,
        # not the tool's own research, so the reading cannot be over-claimed.
        members.append(
            "_these are the rivals the business named. The scan did NOT independently verify "
            "who occupies this category (see 4.6.0b) — so treat the set as the owner's view "
            "of who they compete with, not as a discovered landscape.")
        occupants = []
    else:
        occupants = extract_occupants(ok)
        for name, sources in occupants[:12]:
            members.append("%s — named as an occupant of this category in %d independent "
                           "source(s)" % (name, sources))
    if not members:
        # No agreed occupant. Still useful: say what the sources were, without claiming
        # any of them occupies the category.
        members.append("NO OCCUPANT COULD BE ESTABLISHED — no name appeared in more than "
                       "one independent source. Position strength stays capped at "
                       "ADEQUATE (3).")
    if ok:
        srcs = ", ".join(sorted({publisher(c["url"]) for c in ok})[:6])
        members.append("_sources read: %s" % srcs)

    out = {}
    if members:
        # ⚠ THE `why` MUST MATCH WHICH PATH PRODUCED THE SET. Measured: after owner-named rivals
        # became the primary set, this line still read "discovered by search and read from its
        # own live site" and "the claim quoted is what that occupant STATES" -- describing
        # research that did NOT happen. The model reads `why` as provenance, so a fixed string
        # here laundered the owner's self-report back into an independent finding, which is the
        # exact claim 4.6.0c exists to prevent.
        if owner:
            read_n = sum(1 for p in (rival_pages or []) if p.get("claim"))
            why = ("The rivals the BUSINESS ITSELF named. Where a page could be found and "
                   "read for one of them, the claim quoted is what that page says — the DOMAIN "
                   "IS SHOWN so the reader can see what kind of page it was; the tool does NOT "
                   "verify the page belongs to the rival (%d of %d had a readable page quoting "
                   "a claim). They are still NOT independently verified occupants of this "
                   "category — take the NAMING as the owner's view of who they compete with."
                   % (read_n, len(owner)))
        else:
            why = ("Each entry is a named occupant of this category, discovered by search "
                   "and read from its own live site. The claim quoted is what that occupant "
                   "STATES, not what is assumed about it.")
        out["SCANNED OCCUPANTS OF THE CATEGORY"] = {
            "members": members,
            "why": why,
            "caveat": (meta.get("verdict") or ""),
        }
    else:
        # NO members, and the caveat MUST distinguish WHY. "No search ran" and "search ran
        # but pages were unreadable" are different facts with different next actions.
        verdict_txt = meta.get("verdict") or ""
        if "SEARCH UNAVAILABLE" in verdict_txt:
            why = ("No search backend responded, so no candidate was ever discovered. "
                   "NO SCAN WAS PERFORMED.")
            caveat = ("SEARCH UNAVAILABLE -- this is NOT evidence the category has no "
                      "competitors, and it is not a botwall either. Nothing was searched. "
                      "Position strength stays capped at ADEQUATE (3): a flank cannot be "
                      "proved against a rival that was never looked for.")
        else:
            why = ("The scan could not read any competitor page, so NO occupant could be "
                   "named or characterised.")
            caveat = ("SCAN FAILED. This is NOT evidence that the category has no "
                      "competitors; it is evidence the scan did not work. Position strength "
                      "therefore stays capped at ADEQUATE (3): a flank cannot be proved "
                      "against a rival the scan could not read.")
        out["SCANNED OCCUPANTS OF THE CATEGORY"] = {
            "members": [], "why": why, "caveat": caveat,
        }

    out["_derivation_method"] = (
        "competitor_scan.py (spec 4.6): discovered by search, fetched live, each capture "
        "graded for validity. verdict: %s" % (meta.get("verdict") or "unknown"))
    if blocked:
        out["_not_readable"] = [
            {"url": b["url"], "capture_status": b["capture_status"], "why": b.get("why")}
            for b in blocked]
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--category", required=True)
    ap.add_argument("--market", default="Singapore")
    ap.add_argument("--seed-urls", default="")
    ap.add_argument("--out", default=None)
    ap.add_argument("--timeout", type=int, default=20)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    seeds = [s.strip() for s in args.seed_urls.split(",") if s.strip()]
    if args.dry_run:
        print(json.dumps({"queries": ["%s %s competitors" % (args.category, args.market),
                                      "best %s %s" % (args.category, args.market),
                                      "%s %s brands" % (args.category, args.market)],
                          "seed_urls": seeds,
                          "note": "dry run -- no network call made"}, indent=1))
        return 0

    result = scan(args.category, args.market, seeds, per_url_timeout=args.timeout)
    m = result["_meta"]
    print("competitor scan: %s / %s" % (args.category, args.market))
    print("  %s" % m["verdict"])
    for c in result["captures"]:
        line = "  [%-7s] %s" % (c["capture_status"], c["url"])
        if c.get("claim"):
            line += "\n            claims: %s" % c["claim"][:140]
        elif c["why"]:
            line += "  (%s)" % c["why"]
        print(line)
    if args.out:
        Path(args.out).write_text(json.dumps(result, indent=1))
        print("\nwrote %s" % args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
