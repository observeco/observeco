#!/usr/bin/env python3
"""
ObserveCo — Singapore Trends Daily Collector
===========================================
Pulls topic-specific rising/momentum signal across SG-relevant sources and
writes a single daily shortlist markdown to plans/sg-trends/YYYY-MM-DD.md.

The output is DATA + INSIGHT for Sean to run his positioning filter. This
script does NOT apply any positioning logic and does NOT post/publish.

RELEVANCE LAYER (2026-09-09 rebuild): every trend is classified into an
ObserveCo book domain (the small-business profiles a Singaporean would create
a business in — money, food, pets, retail, travel, demographics, government,
AI, positioning, education, health, beauty, property, transport, repair,
heritage). Only book-relevant trends are surfaced; celebrity/sports/news noise
is dropped. Grouped by domain in Section 1.

Sources (verified working 2026-09-08):
  1. Google Trends SG            — trends.google.com/trending?geo=SG  (via Playwright)
  2. TikTok Creative Center SG   — ads.tiktok.com trends hub (region=SG) (via Playwright)
  3. TikTok Top Ads (SG) [Option B] — ads.tiktok.com topads, brand headlines (via Playwright)
  4. Hacker News (Algolia)       — hn.algolia.com search, SG company keywords (via httpx)
  5. Instagram SG trending       — instagram.com/popular/singapore-trending (category-level, via Playwright)
  (Reddit + X-WOEID stubbed: Reddit now OAuth-gated, X needs paid API + xurl)

Products & Companies section [Option A]: matches a curated SG brand lexicon against
today's Google Trends queries + HN stories to surface brand-level signal explicitly.

Run:  .venv/bin/python scripts/sg_trends_collect.py [--out DIR]
Cron: 0 8 * * *  cd /path/observeco-main && .venv/bin/python scripts/sg_trends_collect.py >> logs/sg_trends.log 2>&1
"""

from __future__ import annotations

import argparse
import html
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_OUT = Path(__file__).resolve().parent.parent / "plans" / "sg-trends"

# ── Seed: SG companies + tech/product keywords we want HN signal on ──────────
SG_HN_KEYWORDS = [
    "Grab",
    "Shopee",
    "Sea Limited",
    "ST Engg",
    "GovTech",
    "Singtel",
    "DBS",
    "OCBC",
    "Marina Bay Sands",
    "Singapore tourism",
    "agent observability",
    "LLM observability",
    "token cost",
    "AI agent",
    "Temasek",
    "GIC",
    "PropertyGuru",
    "Grab Holdings",
]
HN_QUOTED = " OR ".join(f'"{k}"' for k in SG_HN_KEYWORDS)

# The full set of seed strings the collector actually queries. Single source of
# truth: sg_trends_quality.py imports this so the gate verifies against exactly
# what was queried (a gate checking a narrower list would flag legitimate hits).
HN_QUERY_SEEDS = ["Singapore"] + SG_HN_KEYWORDS

# How far back an HN story can be and still count as "trending". Algolia's
# default ranking has no time component, so without this the digest surfaces
# all-time high-score stories (2012 SpaceX, 2013 FT "Death in Singapore") and
# calls them today's signal. 48h covers a daily run with overlap for weekends.
HN_WINDOW_HOURS = 48
_HN_RX_CACHE: dict[str, re.Pattern] = {}


def _kw_re(kw: str) -> re.Pattern:
    """Word-boundary matcher for a seed keyword.

    Algolia matches prefixes and word-forms, so "Grab" returns "grabs" and
    "Graber", "DBS" returns "DBs". Those are false positives, not SG signal.

    Short ALL-CAPS seeds (DBS, GIC, OCBC) match case-SENSITIVELY — IGNORECASE
    would otherwise collapse "DBS" onto "DBs" and re-introduce the bug this
    function exists to kill. Everything else matches case-insensitively.

    ponytail: naive boundary match. Known ceiling — 2-char alnum seeds like "M1"
    collide with legitimate product names (Apple M1), which no regex can
    disambiguate; those need a negative lexicon or removal from the seed list.
    Upgrade path: field-weighted search plus a hand-kept negative lexicon.
    """
    rx = _HN_RX_CACHE.get(kw)
    if rx is None:
        flags = 0 if (kw.isupper() and len(kw) <= 5) else re.IGNORECASE
        rx = re.compile(r"\b" + re.escape(kw) + r"\b", flags)
        _HN_RX_CACHE[kw] = rx
    return rx

# ── Seed 2: SG products & companies we want to surface as brand-level signal ──
# Option A: pulls these names out of Google Trends queries + HN stories and
# groups them into a dedicated "Products & Companies trending in SG" section.
# Expanded to cover the brands named in Book 1 (Small Island, Crowded Market)
# and Book 2 (How a Small Business Gets Chosen).
SG_BRANDS = [
    # E-commerce / marketplaces
    "Shopee",
    "Lazada",
    "Carousell",
    "Amazon",
    "Temu",
    "TikTok Shop",
    "RedMart",
    # Ride / delivery
    "Grab",
    "Gojek",
    "foodpanda",
    "Deliveroo",
    # Banks / fintech
    "DBS",
    "OCBC",
    "UOB",
    "GXS Bank",
    "Trust Bank",
    "MariBank",
    "PayNow",
    "Revolut",
    "GrabPay",
    "Great Eastern",
    "NTUC Income",
    "Prudential",
    # Property
    "PropertyGuru",
    "99.co",
    "Ohmyhome",
    "PropNex",
    "ERA",
    "Huttons",
    "OrangeTee",
    "CapitalLand",
    "HDB",
    "URA",
    # Telco
    "Singtel",
    "StarHub",
    "M1",
    "Circles.Life",
    "GOMO",
    "SIMBA",
    # Retail / FMCG / supermarkets
    "FairPrice",
    "Cold Storage",
    "Sheng Siong",
    "Giant",
    "Guardian",
    "Watsons",
    "Don Don Donki",
    "IKEA",
    "Uniqlo",
    "H&M",
    "SHEIN",
    "Love Bonito",
    "Mustafa",
    "Meidi-ya",
    "RedMart",
    "Khong Guan",
    "Gardenia",
    "Yeo's",
    "Tiger Beer",
    "Tiger Balm",
    "F&N",
    "100PLUS",
    "Old Chang Kee",
    "Lim Chee Guan",
    "Kele",
    "Tai Chong Kok",
    # F&B
    "Koi",
    "LiHO",
    "Chatime",
    "Gong Cha",
    "Tiger Sugar",
    "Starbucks",
    "Luckin",
    "McDonald",
    "KFC",
    "Subway",
    "Mr Coconut",
    "Kopitiam",
    "Kimly",
    "Koufu",
    "Food Republic",
    "Jumbo",
    "Paradise",
    "Putien",
    "Dian Xiao Er",
    "Swee Choon",
    "Spring Court",
    "Red Star",
    "Chatterbox",
    "Shashlik",
    "Muthu's Curry",
    "Komala Vilas",
    "Haidilao",
    # Airlines / travel / hospitality
    "Singapore Airlines",
    "Scoot",
    "Jetstar",
    "Changi Airport",
    "Marina Bay Sands",
    "Resorts World Sentosa",
    "Sentosa",
    "Shangri-La",
    "Capella",
    "Raffles",
    "Universal Studios",
    "Gardens by the Bay",
    # Automotive
    "BYD",
    "Toyota",
    "Tesla",
    "Honda",
    "Hyundai",
    "COE",
    "ComfortDelGro",
    "SBS Transit",
    "SMRT",
    # Health / care
    "IHH",
    "Gleneagles",
    "Mount Elizabeth",
    "Parkway",
    "Raffles Medical",
    "Thomson Medical",
    "Healthway",
    "Fullerton",
    "Econ Healthcare",
    "NTUC Health",
    # Education / tuition
    "Mind Stretcher",
    "The Learning Lab",
    "Kumon",
    "British Council",
    # Beauty / personal care
    "Sigi Skin",
    "Allies of Skin",
    "Skin Inc",
    "Kimage",
    "Leekaja",
    # Tech / gov / funding
    "GovTech",
    "SingPass",
    "MyInfo",
    "Temasek",
    "GIC",
    "Sea Limited",
    "Garena",
    "ShopBack",
    "Ninja Van",
    "ST Engg",
    "Keppel",
    "PSA",
    # Energy / utilities
    "SP Group",
    "Senoko",
    "Tuas Power",
    # Professional services
    "PwC",
    "KPMG",
    "Deloitte",
    "EY",
    "Allen & Gledhill",
    "Rajah & Tann",
    "Drew & Napier",
    # Urban farms
    "Sky Greens",
    "Sustenir",
    "ComCrop",
]

# ── Seed 3: ObserveCo book domains — the small-business profiles a Singaporean
# would create a business in, drawn from Book 1 (the map) + Book 2 (the move).
# Each domain carries the keywords used to (a) seed Google Trends related-query
# pulls and (b) classify a raw trend into a domain. This is the RELEVANCE layer:
# it decides which trends are worth Sean's attention for influencer content.
SG_DOMAINS = [
    {
        "name": "Money & finance",
        "book": "Book 1",
        "keywords": [
            "bank",
            "banking",
            "DBS",
            "OCBC",
            "UOB",
            "fintech",
            "payment",
            "PayNow",
            "credit card",
            "loan",
            "mortgage",
            "invest",
            "stock",
            "CPF",
            "insurance",
            "wealth",
            "savings",
            "interest rate",
            "GST",
            "inflation",
            "salary",
            "income",
            "COE",
            "property price",
            "rent",
        ],
    },
    {
        "name": "Food & F&B",
        "book": "Book 1 + 2",
        "keywords": [
            "food",
            "restaurant",
            "hawker",
            "cafe",
            "coffee",
            "bubble tea",
            "delivery",
            "GrabFood",
            "foodpanda",
            "menu",
            "dining",
            "eat",
            "F&B",
            "kopitiam",
            "bakery",
            "curry",
            "noodle",
            "chicken rice",
            "laksa",
            "chili crab",
            "dessert",
            "snack",
        ],
    },
    {
        "name": "Pets",
        "book": "Book 1",
        "keywords": [
            "pet",
            "dog",
            "cat",
            "vet",
            "veterinary",
            "grooming",
            "pet food",
            "boarding",
            "puppy",
            "kitten",
            "animal",
            "pet care",
        ],
    },
    {
        "name": "Retail & e-commerce",
        "book": "Book 1 + 2",
        "keywords": [
            "shop",
            "retail",
            "Shopee",
            "Lazada",
            "e-commerce",
            "online shop",
            "supermarket",
            "grocery",
            "fashion",
            "clothing",
            "apparel",
            "beauty",
            "skincare",
            "cosmetic",
            "mall",
            "boutique",
            "brand",
            "product",
        ],
    },
    {
        "name": "Travel & hospitality",
        "book": "Book 1",
        "keywords": [
            "travel",
            "hotel",
            "airline",
            "flight",
            "tourism",
            "Singapore Airlines",
            "Changi",
            "resort",
            "Marina Bay Sands",
            "Sentosa",
            "cruise",
            "holiday",
            "vacation",
            "tourist",
            "attraction",
        ],
    },
    {
        "name": "Demographics & society",
        "book": "Book 1",
        "keywords": [
            "birth rate",
            "fertility",
            "ageing",
            "elderly",
            "marriage",
            "wedding",
            "household",
            "population",
            "singaporean",
            "child",
            "baby",
            "senior",
            "retirement",
            "demographic",
        ],
    },
    {
        "name": "Government & economy",
        "book": "Book 1",
        "keywords": [
            "government",
            "budget",
            "grant",
            "SME",
            "small business",
            "tax",
            "GST",
            "Enterprise Singapore",
            "economy",
            "GDP",
            "inflation",
            "salary review",
            "civil service",
            "public sector",
            "policy",
            "regulation",
            "compliance",
        ],
    },
    {
        "name": "AI & technology",
        "book": "Book 1",
        "keywords": [
            "AI",
            "artificial intelligence",
            "agent",
            "automation",
            "chatbot",
            "LLM",
            "machine learning",
            "software",
            "app",
            "startup",
            "tech",
            "digital",
            "online",
            "e-commerce",
            "robot",
            "data",
        ],
    },
    {
        "name": "Positioning & branding",
        "book": "Book 2",
        "keywords": [
            "brand",
            "positioning",
            "marketing",
            "pricing",
            "premium",
            "loyalty",
            "customer",
            "differentiation",
            "word",
            "identity",
            "rebrand",
            "advertising",
            "social media",
            "influencer",
            "strategy",
        ],
    },
    {
        "name": "Education & tuition",
        "book": "Book 1",
        "keywords": [
            "tuition",
            "enrichment",
            "school",
            "education",
            "tutor",
            "student",
            "exam",
            "PSLE",
            "O-level",
            "A-level",
            "preschool",
            "childcare",
            "learning",
            "class",
        ],
    },
    {
        "name": "Health & senior care",
        "book": "Book 1",
        "keywords": [
            "health",
            "clinic",
            "doctor",
            "hospital",
            "eldercare",
            "nursing home",
            "care",
            "wellness",
            "supplement",
            "pharmacy",
            "GP",
            "specialist",
            "therapy",
            "rehab",
        ],
    },
    {
        "name": "Beauty & personal care",
        "book": "Book 1",
        "keywords": [
            "beauty",
            "salon",
            "hair",
            "skincare",
            "makeup",
            "spa",
            "nail",
            "barber",
            "cosmetic",
            "facial",
            "lash",
            "aesthetic",
        ],
    },
    {
        "name": "Home & property",
        "book": "Book 1",
        "keywords": [
            "property",
            "real estate",
            "HDB",
            "condo",
            "renovation",
            "interior",
            "home",
            "agent",
            "mortgage",
            "rent",
            "buy",
            "sell",
            "BTO",
        ],
    },
    {
        "name": "Transport & automotive",
        "book": "Book 1",
        "keywords": [
            "car",
            "COE",
            "EV",
            "electric vehicle",
            "BYD",
            "Toyota",
            "taxi",
            "ride",
            "Grab",
            "bus",
            "MRT",
            "transport",
            "driving",
            "license",
        ],
    },
    {
        "name": "Repair & services",
        "book": "Book 1",
        "keywords": [
            "repair",
            "laundry",
            "watch",
            "funeral",
            "cleaning",
            "maintenance",
            "plumber",
            "electrician",
            "handyman",
            "service",
            "tailor",
            "cobbler",
        ],
    },
    {
        "name": "Heritage & local culture",
        "book": "Book 2",
        "keywords": [
            "heritage",
            "tradition",
            "local",
            "Singaporean",
            "culture",
            "iconic",
            "old",
            "history",
            "hawker",
            "kopitiam",
            "kampong",
            "identity",
            "homegrown",
            "national",
        ],
    },
]

# Flatten all domain keywords for matching. Preserve original case so proper
# nouns (DBS, Grab, Shopee) keep their capitalization marker for classify_domain.
DOMAIN_KEYWORDS = {d["name"]: list(d["keywords"]) for d in SG_DOMAINS}


def classify_domain(text: str) -> str | None:
    """Return the first SG domain whose keyword appears in ``text``, or None
    if it's noise (celebrity/sports/news with no book relevance).

    Proper-noun keywords (e.g. "DBS", "Grab", "Shopee") must appear capitalized
    so lowercase homonyms don't false-positive ("free dbs" = databases, not the
    bank). Generic keywords (bank, food, pet) match case-insensitively.
    """
    for name, kws in DOMAIN_KEYWORDS.items():
        for kw in kws:
            if len(kw) < 2:
                continue
            if kw[0].isupper():
                # Proper noun — require the capitalized form.
                pat = re.escape(kw)
                if re.search(r"(?<![A-Za-z0-9])" + pat + r"(?![A-Za-z0-9])", text):
                    return name
            else:
                # Generic keyword — case-insensitive.
                pat = re.escape(kw.lower())
                if re.search(r"(?<![a-z0-9])" + pat + r"(?![a-z0-9])", text.lower()):
                    return name
    return None


def match_brand(text: str) -> str | None:
    """Return the first known SG brand found in ``text``, or None.

    Requires the brand to appear in its proper-noun (capitalized) form so that
    lowercase homonyms don't false-positive — e.g. "free dbs" (databases) and
    "grab a domain" must NOT match the DBS bank or Grab. A brand like "DBS" or
    "Grab" is a proper noun and appears capitalized when genuinely referenced.
    """
    for b in SG_BRANDS:
        if len(b) < 2:
            continue
        # Match the brand as it's written (capitalized proper noun), word-bounded.
        pat = re.escape(b)
        if re.search(r"(?<![A-Za-z0-9])" + pat + r"(?![A-Za-z0-9])", text):
            return b
    return None


def extract_sg_products(google_trends: list[dict], hn: list[dict]) -> list[dict]:
    """Group brand-level signal from Google Trends queries + HN stories into a
    single de-duplicated list. Data only — no positioning applied."""
    out: list[dict] = []
    seen: set[str] = set()

    # Brand mentions hiding inside Google Trends queries (e.g. "DBS Gen Z cards")
    for r in google_trends:
        q = r.get("query", "")
        if "ERROR" in q:
            continue
        b = match_brand(q)
        if b and b not in seen:
            seen.add(b)
            out.append({"brand": b, "evidence": q, "source": "Google Trends"})

    # HN stories that name a brand (company-level momentum)
    for r in hn:
        t = r.get("title", "")
        if "ERROR" in t:
            continue
        b = match_brand(t)
        if b and b not in seen:
            seen.add(b)
            pts = r.get("points", 0) or 0
            out.append({"brand": b, "evidence": t, "source": f"Hacker News ({pts} pts)"})

    return out


def clean(t: str) -> str:
    return " ".join(w for w in t.split())


def now_sg() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


# ─────────────────────────────────────────────────────────────────────────────
# Source 1: Google Trends SG (Playwright)
# ─────────────────────────────────────────────────────────────────────────────
def fetch_google_trends_sg() -> list[dict]:
    from playwright.sync_api import sync_playwright

    rows = []
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        ctx = b.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
        )
        pg = ctx.new_page()
        try:
            pg.goto("https://trends.google.com/trending?geo=SG&hl=en-GB", timeout=45000)
            pg.wait_for_timeout(5000)
            # Trending titles render under the `.mZ3RIc` heading class
            items = pg.evaluate(
                "() => Array.from(document.querySelectorAll('.mZ3RIc')).map(e=>e.innerText)"
                ".filter(t=>t && t.trim().length>3)"
            )
            seen = set()
            for it in items:
                t = " ".join(it.split())
                if t and t not in seen and t != "Trends":
                    seen.add(t)
                    rows.append({"query": t, "source": "google_trends_sg"})
        except Exception as e:
            rows.append({"query": f"GT ERROR: {e}", "source": "google_trends_sg"})
        pg.close()
        ctx.close()
        b.close()
    return rows[:30]


# ─────────────────────────────────────────────────────────────────────────────
# Source 1b: Google Trends SG — seeded related queries around book domains
# Pulls the "rising related queries" for a set of ObserveCo-relevant seed terms
# (e.g. "small business singapore", "pet", "bubble tea") so we surface trends
# that are book-relevant even when they're not in the raw SG trending feed.
# ─────────────────────────────────────────────────────────────────────────────
def fetch_google_trends_seeded() -> list[dict]:
    from playwright.sync_api import sync_playwright

    # Seed terms drawn from the book domains — the things a Singaporean would
    # create a business in. Kept SHORT (Google Trends explore rate-limits hard
    # on many sequential requests) and spread with delays.
    SEED_TERMS = [
        "small business singapore",
        "pet singapore",
        "bubble tea",
        "hawker",
        "tuition singapore",
        "property singapore",
        "e-commerce singapore",
        "startup singapore",
    ]

    rows = []
    seen: set[str] = set()
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        ctx = b.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
        )
        pg = ctx.new_page()
        try:
            for term in SEED_TERMS:
                try:
                    pg.goto(
                        f"https://trends.google.com/trends/explore?q={term}&geo=SG&hl=en-GB",
                        timeout=30000,
                    )
                    pg.wait_for_timeout(4000)
                    body = pg.inner_text("body")
                    # 429 = rate-limited; stop early rather than hammer the endpoint.
                    if "429" in body and "error" in body.lower():
                        break
                    # Related queries render in the "Related queries" panel
                    items = pg.evaluate(
                        "() => Array.from(document.querySelectorAll('.widget-title, "
                        ".related-queries, .mZ3RIc')).map(e=>e.innerText)"
                    )
                    for it in items:
                        for line in it.split("\n"):
                            t = " ".join(line.split())
                            if (
                                t
                                and len(t) > 3
                                and t not in seen
                                and not t.lower().startswith(("related", "rising", "top"))
                            ):
                                seen.add(t)
                                rows.append(
                                    {"query": t, "source": "google_trends_seeded", "seed": term}
                                )
                except Exception:
                    continue
                pg.wait_for_timeout(3000)  # polite delay between terms
        except Exception as e:
            rows.append({"query": f"GT-SEEDED ERROR: {e}", "source": "google_trends_seeded"})
        pg.close()
        ctx.close()
        b.close()
    return rows[:40]


def filter_relevant(rows: list[dict]) -> list[dict]:
    """Keep only trends that classify into a book domain (drop celebrity/sports/
    news noise). Each kept row gets a 'domain' tag."""
    out = []
    for r in rows:
        q = r.get("query", "")
        if "ERROR" in q:
            out.append(r)
            continue
        d = classify_domain(q)
        if d:
            r = dict(r)
            r["domain"] = d
            out.append(r)
    return out


# ─────────────────────────────────────────────────────────────────────────────
# Source 2: TikTok Creative Center SG (Playwright)
# ─────────────────────────────────────────────────────────────────────────────
def fetch_tiktok_creative_sg() -> list[dict]:
    from playwright.sync_api import sync_playwright

    rows = []
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        ctx = b.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
        )
        pg = ctx.new_page()
        try:
            pg.goto(
                "https://ads.tiktok.com/business/creativecenter/hashtag/trending/pc/en?region=SG",
                timeout=45000,
            )
            pg.wait_for_timeout(9000)
            body_lines = [ln.strip() for ln in pg.inner_text("body").split("\n") if ln.strip()]
            # Row shape: "#tag" [, <category label>] , <posts>, "Posts", <views>, "Views", ...
            i = 0
            while i < len(body_lines) and len(rows) < 20:
                line = body_lines[i]
                if line.startswith("#") and len(line) > 2 and len(line) < 40:
                    tag = line
                    posts = views = None
                    j = i + 1
                    k = j
                    for k in range(j, min(i + 8, len(body_lines))):
                        if body_lines[k] == "Posts" and posts is None and k > j:
                            posts = body_lines[k - 1]
                        if body_lines[k] == "Views" and k > j:
                            views = body_lines[k - 1]
                            break
                    rows.append(
                        {
                            "hashtag": tag,
                            "posts": posts,
                            "views": views,
                            "source": "tiktok_creative_sg",
                        }
                    )
                    i = k + 1
                else:
                    i += 1
            if not rows:  # fallback: capture all #-prefixed tokens
                seen = set()
                for tok in re.findall(r"#([A-Za-z0-9_]+)", " ".join(body_lines)):
                    if tok not in seen:
                        seen.add(tok)
                        rows.append({"hashtag": "#" + tok, "source": "tiktok_creative_sg"})
        except Exception as e:
            rows.append({"hashtag": f"TT ERROR: {e}", "source": "tiktok_creative_sg"})
        pg.close()
        ctx.close()
        b.close()
    return rows[:20]


# ─────────────────────────────────────────────────────────────────────────────
# Source 2b: TikTok Creative Center — Top Ads (SG) → brand/product names (Playwright)
# Option B: pulls brand/ad-creative headlines from TikTok's authorized Top Ads
# surface. Gives brand-level attention signal the hashtag hub doesn't expose.
# NOTE: only ads advertisers have authorized are shown (logged-out limited).
# ─────────────────────────────────────────────────────────────────────────────
def fetch_tiktok_top_ads_sg() -> list[dict]:
    from playwright.sync_api import sync_playwright

    rows = []
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        ctx = b.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
        )
        pg = ctx.new_page()
        try:
            pg.goto(
                "https://ads.tiktok.com/business/creativecenter/inspiration/topads/pc/en"
                "?region=SG&period=30",
                timeout=45000,
            )
            pg.wait_for_timeout(9000)
            body_lines = [ln.strip() for ln in pg.inner_text("body").splitlines() if ln.strip()]
            # Each Top Ads block ENDS with "See analytics" (anchor). Within a block:
            #   ... <headline> ... <likes> "Likes" "Top N%" "CTR" <budget> "Low" ...
            # We slice from the last block start up to (but excluding) "See analytics".
            starts: list[int] = []
            for i, ln in enumerate(body_lines):
                if ln == "See analytics":
                    starts.append(i)
            # A real block ends at each "See analytics"; scan backwards from that
            # marker to locate the block's headline (the most recent candidate line
            # that isn't a stat/menu token).
            STAT_TOKENS = {
                "Likes",
                "CTR",
                "Budget",
                "Low",
                "Medium",
                "High",
                "Posts",
                "Views",
                "See analytics",
                "Video Views",
            }
            # Block-boundary markers: anything before the first ad begins, and
            # the modal/footer junk after the last ad. We only scan backward a
            # bounded window from each anchor.
            ad_titles: dict[int, tuple[str | None, str | None, str | None]] = {}
            for anchor in starts:
                # walk backwards from anchor to find headline + likes + ctr
                likes = ctr = None
                headline = None
                for j in range(anchor - 1, max(anchor - 12, -1), -1):
                    ln = body_lines[j]
                    t = ln.lower()
                    if ln == "Likes" and j - 1 >= 0:
                        likes = body_lines[j - 1]
                        # skip the number we just used
                        j -= 1
                        continue
                    if ln.startswith("Top ") and len(ln) < 10:
                        ctr = ln
                        continue
                    if ln == "CTR" or ln in STAT_TOKENS or t.startswith(("top ", "see ", "©")):
                        continue
                    if len(ln) >= 6:  # first non-token line going up = headline
                        headline = ln
                        break
                if headline:
                    ad_titles[anchor] = (headline, likes, ctr)

            for _anchor, (headline, likes, ctr) in ad_titles.items():
                if len(rows) >= 15:
                    break
                rows.append(
                    {
                        "headline": headline,
                        "likes": likes,
                        "ctr": ctr,
                        "source": "tiktok_top_ads_sg",
                        "brand": match_brand(headline or ""),
                    }
                )
            if not rows and (not body_lines or "ERROR" not in " ".join(body_lines)):
                rows.append({"headline": "No ad rows parsed", "source": "tiktok_top_ads_sg"})
        except Exception as e:
            rows.append({"headline": f"TT-TOPADS ERROR: {e}", "source": "tiktok_top_ads_sg"})
        pg.close()
        ctx.close()
        b.close()
    return rows[:15]


# ─────────────────────────────────────────────────────────────────────────────
# Source 3: Hacker News via Algolia (SG companies/tech) — httpx
# Query each keyword separately (Algolia rejects multi-term OR syntax),
# then merge + sort by points.
# ─────────────────────────────────────────────────────────────────────────────
def fetch_hn_sg() -> list[dict]:
    import httpx

    rows = []
    seen_keys = set()
    url = "https://hn.algolia.com/api/v1/search"
    base = HN_QUERY_SEEDS
    # Recency window. Algolia's default ranking is relevance + all-time
    # popularity, so an unfiltered query returns each keyword's highest-scoring
    # story EVER — then the points sort below pushes 2012-era archaeology to the
    # top of the digest. ponytail: 48h on a daily run means a hot story can
    # appear two digests running; that is the window working, not a bug.
    # Upgrade path: read the previous digest's URL list and drop seen links.
    cutoff_i = int(time.time()) - HN_WINDOW_HOURS * 3600
    try:
        with httpx.Client(timeout=25) as client:
            for kw in base:
                try:
                    resp = client.get(
                        url,
                        params={
                            "query": kw,
                            "tags": "story",
                            "hitsPerPage": 8,
                            "numericFilters": f"created_at_i>{cutoff_i}",
                        },
                    )
                    resp.raise_for_status()
                except Exception:
                    continue
                rx = _kw_re(kw)
                for h in resp.json().get("hits", []):
                    title = h.get("title") or h.get("story_title") or ""
                    object_id = h.get("objectID")
                    if not title or object_id in seen_keys:
                        continue
                    # Word-boundary match: Algolia queryType does prefix/fuzzy
                    # matching, so "Grab" otherwise returns "grabs"/"Graber" and
                    # "DBS" returns "DBs". Those are not SG signal.
                    if rx and not rx.search(title):
                        continue
                    seen_keys.add(object_id)
                    rows.append(
                        {
                            "title": html.unescape(title),
                            "points": h.get("points") or 0,
                            "url": h.get("url")
                            or f"https://news.ycombinator.com/item?id={object_id}",
                            "source": "hn_sg",
                        }
                    )
    except Exception as e:
        rows.append({"title": f"HN ERROR: {e}", "source": "hn_sg"})
    rows.sort(key=lambda r: r.get("points", 0) or 0, reverse=True)
    return rows


# ─────────────────────────────────────────────────────────────────────────────
# Source 4: Instagram SG trending — category-level trend keywords (Playwright)
# NOTE: IG's public trending page gives CATEGORY trend keywords (fashion, food,
# beauty, property, fitness...), NOT a ranked product list. Product-level
# attention is login/paid-gated. This captures the category signal only.
# ─────────────────────────────────────────────────────────────────────────────
def fetch_ig_trending_sg() -> list[dict]:
    from playwright.sync_api import sync_playwright

    rows = []
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        ctx = b.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
        )
        pg = ctx.new_page()
        try:
            pg.goto("https://www.instagram.com/popular/singapore-trending/", timeout=45000)
            pg.wait_for_timeout(7000)
            body = pg.inner_text("body")
            lines = [ln.strip() for ln in body.split("\n") if ln.strip()]
            # Category trend keywords look like "singapore X trends 2026" / "X trends in singapore"
            seen = set()
            for ln in lines:
                low = ln.lower()
                # capture category trend phrases
                if re.search(r"trend", low) and re.search(r"singapore", low) and len(ln) < 60:
                    if ln not in seen:
                        seen.add(ln)
                        rows.append({"trend": ln, "source": "ig_trending_sg"})
        except Exception as e:
            rows.append({"trend": f"IG ERROR: {e}", "source": "ig_trending_sg"})
        pg.close()
        ctx.close()
        b.close()
    return rows[:25]


# ─────────────────────────────────────────────────────────────────────────────
def render_markdown(results: dict, date_str: str) -> str:
    lines = [
        f"# SG Trends — {date_str}",
        "",
        "> Daily topic signal for ObserveCo positioning. Data + insight only; "
        "positioning decision is Sean's. Generated by `scripts/sg_trends_collect.py`.",
        "",
    ]

    # ── Section 1: Book-relevant trends (grouped by domain) ───────────────────
    # The heart of the rebuild: only trends that classify into an ObserveCo book
    # domain, grouped so Sean can see which small-business profile each maps to.
    g = results.get("google_trends", [])
    gs = results.get("google_trends_seeded", [])
    hn = results.get("hn", [])
    ig = results.get("ig", [])

    # Collect all relevant trends across sources, tag with domain.
    relevant: list[dict] = []
    for r in filter_relevant(g):
        relevant.append({"text": r["query"], "domain": r["domain"], "src": "Google Trends"})
    for r in filter_relevant(gs):
        relevant.append({"text": r["query"], "domain": r["domain"], "src": "GT seeded"})
    for r in hn:
        t = r.get("title", "")
        if "ERROR" in t:
            continue
        d = classify_domain(t)
        if d:
            relevant.append({"text": t, "domain": d, "src": f"HN ({r.get('points', 0)} pts)"})
    for r in ig:
        t = r.get("trend", "")
        if "ERROR" in t:
            continue
        d = classify_domain(t)
        if d:
            relevant.append({"text": t, "domain": d, "src": "IG"})

    # Group by domain, preserving domain order from SG_DOMAINS.
    lines += ["## 1. Book-relevant trends (what Singaporeans are talking about)", ""]
    lines.append(
        "> Only trends that map to an ObserveCo book domain (the small-business "
        "profiles a Singaporean would create a business in). Grouped by domain — "
        "you apply the positioning angle."
    )
    lines.append("")
    seen_texts: set[str] = set()
    any_relevant = False
    for d in SG_DOMAINS:
        name = d["name"]
        items = [r for r in relevant if r["domain"] == name]
        if not items:
            continue
        any_relevant = True
        lines.append(f"### {name}  ({d['book']})")
        lines.append("")
        for r in items[:6]:
            txt = re.sub(r"[|\n]", " ", r["text"])
            if len(txt) > 80:
                txt = txt[:77] + "..."
            if txt in seen_texts:
                continue
            seen_texts.add(txt)
            lines.append(f"- {txt}  — *{r['src']}*")
        lines.append("")
    if not any_relevant:
        lines.append("_No book-relevant trends today._")
    lines.append("")

    # ── Section 2: Products & Companies trending in SG (Option A) ──────────────
    products = extract_sg_products(g, hn)
    lines += ["## 2. Products & Companies trending in SG", ""]
    if products:
        lines.append("| Brand/Company | Where it surfaced |")
        lines.append("|---|---|")
        for p in products:
            ev = re.sub(r"[|\n]", " ", p["evidence"])
            if len(ev) > 70:
                ev = ev[:67] + "..."
            lines.append(f"| **{p['brand']}** | {p['source']}: “{ev}” |")
    else:
        lines.append("_No brand-specific signal today._")
    lines.append(
        "> Brands are matched from a curated SG lexicon against today's Google Trends "
        "queries + HN stories. Data only — you apply the positioning filter."
    )
    lines.append("")

    # ── Section 3: Google Trends SG (raw, filtered to relevant) ────────────────
    lines += ["## 3. Google Trends — Singapore (past 24h, book-relevant only)", ""]
    rel_g = filter_relevant(g)
    if rel_g:
        for r in rel_g:
            q = re.sub(r"^GT ERROR.*", "", r.get("query", "")).strip()
            if q:
                lines.append(f"- {q}")
    else:
        lines.append("_No book-relevant Google Trends today._")
    if any("ERROR" in r.get("query", "") for r in g):
        lines.append("> ⚠️ Google Trends fetch failed — check network/Playwright.")
    lines.append("")

    # ── Section 4: TikTok Creative Center — trending hashtags ──────────────────
    t = results.get("tiktok", [])
    real = [r for r in t if "ERROR" not in r.get("hashtag", "")]
    lines += ["## 4. TikTok Creative Center — Singapore trending hashtags", ""]
    if real:
        lines.append("| Hashtag | Posts | Views |")
        lines.append("|---|---|---|")
        for r in real[:15]:
            lines.append(
                f"| {r.get('hashtag', '')} | {r.get('posts', '—')} | {r.get('views', '—')} |"
            )
    else:
        lines.append("_No data / blocked._")
    if any("ERROR" in r.get("hashtag", "") for r in t):
        lines.append("> ⚠️ TikTok Creative Center fetch failed — check network/Playwright.")
    lines.append("")

    # ── Section 5: TikTok Creative Center — Top Ads (brands) [Option B] ────────
    top = results.get("tiktok_top_ads", [])
    real_top = [r for r in top if "ERROR" not in r.get("headline", "")]
    lines += ["## 5. TikTok Creative Center — Top Ads (SG, last 30d)", ""]
    if real_top:
        lines.append("| Ad headline | Likes | CTR | Brand? |")
        lines.append("|---|---|---|---|")
        for r in real_top[:15]:
            hh = re.sub(r"[|\n]", " ", r.get("headline", ""))
            if len(hh) > 60:
                hh = hh[:57] + "..."
            br = r.get("brand") or "—"
            lines.append(f"| {hh} | {r.get('likes', '—')} | {r.get('ctr', '—')} | {br} |")
    else:
        lines.append("_No data / blocked._")
    if any("ERROR" in r.get("headline", "") for r in top):
        lines.append("> ⚠️ TikTok Top Ads fetch failed — check network/Playwright.")
    lines.append(
        "> Note: TikTok only shows ads advertisers have authorized; this is a "
        "logged-out partial view, not the full paid ranking."
    )
    lines.append("")

    # ── Section 6: Hacker News ─────────────────────────────────────────────────
    real_hn = [r for r in hn if "ERROR" not in r.get("title", "")]
    lines += ["## 6. Hacker News — Singapore companies & tech (global momentum to localize)", ""]
    if real_hn:
        lines.append("| Story | Points | Link |")
        lines.append("|---|---|---|")
        for r in real_hn[:12]:
            ttl = r.get("title", "")
            if len(ttl) > 70:
                ttl = ttl[:67] + "..."
            ttl_clean = re.sub(r"[|\n]", " ", ttl)
            lines.append(f"| {ttl_clean} | {r.get('points', 0)} | {r.get('url', '')} |")
    else:
        lines.append("_No data._")
    if any("ERROR" in r.get("title", "") for r in hn):
        lines.append("> ⚠️ HN fetch failed — check network/hits.")
    lines.append("")

    # ── Section 7: Instagram ──────────────────────────────────────────────────
    real_ig = [r for r in ig if "ERROR" not in r.get("trend", "")]
    lines += ["## 7. Instagram — Singapore category trends (what SG is paying attention to)", ""]
    if real_ig:
        lines.append("| Category trend |")
        lines.append("|---|")
        for r in real_ig[:20]:
            t = re.sub(r"[|\n]", " ", r.get("trend", ""))
            lines.append(f"| {t} |")
    else:
        lines.append("_No data / blocked._")
    if any("ERROR" in r.get("trend", "") for r in ig):
        lines.append("> ⚠️ Instagram trending fetch failed — check network/Playwright.")
    lines.append("")
    lines.append(
        "> **Note:** Instagram's public trending page gives **category-level** trend keywords (fashion, food, beauty, property, fitness...), not a ranked product list. Product-level attention is login/paid-gated and not scrapable via the free protocol."
    )
    lines.append("")

    lines.append("---")
    lines.append("## Next (stubbed — blocked/paid, not yet wired)")
    lines.append(
        "- **Reddit** r/singapore + r/askSingapore: now OAuth-gated (Reddit hard-blocks `.json`). Needs a Reddit API app + read-only token."
    )
    lines.append(
        "- **X Trends-by-WOEID** (Singapore WOEID 1062617): needs xurl installed + paid X API credits."
    )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    date_str = now_sg()
    args.out.mkdir(parents=True, exist_ok=True)
    outfile = args.out / f"{date_str}.md"

    results = {}
    print(f"[{date_str}] Fetching Google Trends SG...")
    results["google_trends"] = fetch_google_trends_sg()
    print(f"[{date_str}] Fetching Google Trends seeded (book domains)...")
    results["google_trends_seeded"] = fetch_google_trends_seeded()
    print(f"[{date_str}] Fetching TikTok Creative Center SG...")
    results["tiktok"] = fetch_tiktok_creative_sg()
    print(f"[{date_str}] Fetching TikTok Creative Center Top Ads (SG brands)...")
    results["tiktok_top_ads"] = fetch_tiktok_top_ads_sg()
    print(f"[{date_str}] Fetching Hacker News (SG companies/tech)...")
    results["hn"] = fetch_hn_sg()
    print(f"[{date_str}] Fetching Instagram SG trending (category-level)...")
    results["ig"] = fetch_ig_trending_sg()

    md = render_markdown(results, date_str)
    outfile.write_text(md)
    print(f"[{date_str}] Wrote {outfile}")
    print(f"   Google Trends rows: {len(results['google_trends'])}")
    print(f"   Google Trends seeded rows: {len(results['google_trends_seeded'])}")
    print(f"   TikTok hashtag rows: {len(results['tiktok'])}")
    print(f"   TikTok Top Ads rows: {len(results['tiktok_top_ads'])}")
    print(f"   HN story rows: {len(results['hn'])}")
    print(f"   IG category-trend rows: {len(results['ig'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
