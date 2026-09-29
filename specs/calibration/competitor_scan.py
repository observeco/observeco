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
    """
    if status == 0:
        return "error", "transport failure"
    if status in (401, 403, 407, 429, 503):
        return "blocked", "HTTP %d" % status
    low = (text or "").lower()
    for m in BLOCK_MARKERS:
        if m in low:
            return "blocked", "challenge marker: %r" % m
    for m in SHELL_MARKERS:
        if m in low:
            return "shell", "javascript shell: %r" % m
    if len((text or "").strip()) < MIN_USEFUL_CHARS:
        return "thin", "only %d chars of readable text" % len((text or "").strip())
    return "ok", ""


def fetch(url: str, timeout: int = 20) -> tuple[int, str]:
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


def extract_occupants(ok_captures: list[dict]) -> list[tuple[str, int]]:
    """Mine occupant NAMES out of the readable sources.

    A name qualifies only if it appears in more than one independent source. Returns
    [(name, source_count)] sorted by source count then name.
    """
    counts: dict[str, set[str]] = {}
    for c in ok_captures:
        text = "%s %s" % (c.get("claim") or "", c.get("excerpt") or "")
        host = urllib.parse.urlparse(c["url"]).netloc.lower()
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


def to_competitive_set(result: dict) -> dict:
    """Convert a scan result into the `derived_competitive_set` the rubric consumes.

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
    occupants = extract_occupants(ok)

    members = []
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
        srcs = ", ".join(sorted({urllib.parse.urlparse(c["url"]).netloc.lower()
                                 for c in ok})[:6])
        members.append("_sources read: %s" % srcs)

    out = {}
    if members:
        out["SCANNED OCCUPANTS OF THE CATEGORY"] = {
            "members": members,
            "why": ("Each entry is a named occupant of this category, discovered by search "
                    "and read from its own live site. The claim quoted is what that occupant "
                    "STATES, not what is assumed about it."),
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
