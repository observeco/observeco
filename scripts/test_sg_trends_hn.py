#!/usr/bin/env python3
"""Check for the SG trends HN collector's keyword matcher.

Guards the two bugs that made the digest surface non-SG archaeology as
"trending" (see scripts/sg_trends_collect.py): loose Algolia matching letting
"Grab" match "grabs"/"Graber" and "DBS" match "DBs", and the absence of a
recency window. Run: python3 scripts/test_sg_trends_hn.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from sg_trends_collect import HN_WINDOW_HOURS, SG_HN_KEYWORDS, _kw_re  # noqa: E402

CASES = [
    # (keyword, title, should_match)
    ("DBS", "Top Ten Time Series DBs", False),
    ("DBS", "Why relational DBs are the standard", False),
    ("DBS", "DBS bank raises rates", True),
    ("Grab", "Space Station grabs SpaceX Dragon ship", False),
    ("Grab", "AMD Grabs over 30% CPU Market Share", False),
    ("Grab", "Bluesky CEO Jay Graber is stepping down", False),
    ("Grab", "Grab Holdings beats estimates", True),
    ("Grab", "Why I left Google to join Grab", True),
    ("GIC", "GIC invests in regional tech", True),
    ("OCBC", "OCBC phishing scam exposed", True),
    ("Singtel", "A single firm is behind hacking scandals", False),
    ("Shopee", "Shopee cuts jobs in Singapore", True),
    ("Temasek", "Temasek writes down FTX stake", True),
    ("PropertyGuru", "Meet the co-founder of PropertyGuru", True),
]


def main() -> int:
    fails = []
    for kw, title, want in CASES:
        got = bool(_kw_re(kw).search(title))
        if got != want:
            fails.append(f"  [{kw}] want={want} got={got} | {title}")

    # Every seed must compile, and the window must be a sane positive int.
    for kw in SG_HN_KEYWORDS:
        _kw_re(kw)
    if not isinstance(HN_WINDOW_HOURS, int) or HN_WINDOW_HOURS <= 0:
        fails.append(f"  HN_WINDOW_HOURS must be a positive int, got {HN_WINDOW_HOURS!r}")

    if fails:
        print(f"FAIL — {len(fails)} case(s):")
        print("\n".join(fails))
        return 1

    print(f"OK — {len(CASES)} keyword cases + {len(SG_HN_KEYWORDS)} seeds compile; "
          f"window={HN_WINDOW_HOURS}h")
    return 0


if __name__ == "__main__":
    sys.exit(main())
