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
def search(query: str, limit: int = 8) -> list[str]:
    """Discover candidate URLs. Uses the local extract stack's search when importable; otherwise
    returns nothing and says so -- never invents URLs."""
    try:
        from hermes_tools import web_search  # noqa
    except Exception:
        return []
    try:
        res = web_search(query, limit=limit)
        return [r["url"] for r in (res.get("data", {}).get("web") or [])]
    except Exception:
        return []


def scan(category: str, market: str, seed_urls: list[str], per_url_timeout: int = 20) -> dict:
    started = datetime.now(timezone.utc).isoformat(timespec="seconds")
    queries = [
        "%s %s competitors" % (category, market),
        "best %s %s" % (category, market),
        "%s %s brands" % (category, market),
    ]
    discovered, per_query = [], {}
    for q in queries:
        urls = search(q)
        per_query[q] = urls
        discovered.extend(urls)
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
