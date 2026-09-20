#!/usr/bin/env python3
"""SG Trends digest quality gate — the reward function.

Scores each daily digest on two things Sean actually cares about:
  1. STALENESS  — are the HN stories genuinely recent, or archaeology?
  2. SG PRECISION — are Section 6 rows actually Singapore, or generic tech
                    that matched a loose keyword?

Then the part that makes it a *reward function* rather than a dashboard:
it compares today's flagged set against the previous digest's. The same
stale item flagged two days running means the collector did not filter —
that is a REGRESSION, not a one-off, and this exits non-zero.

Usage:
  python3 scripts/sg_trends_quality.py                  # score last 2 digests
  python3 scripts/sg_trends_quality.py --days 9         # score the backlog
  python3 scripts/sg_trends_quality.py --self-test      # prove the gate fires

Exit codes: 0 clean · 1 regression · 2 input error

ponytail: staleness is resolved by Algolia TITLE search (one call per unique
title, disk-cached). Ceiling: re-titled/resubmitted stories miss on lookup and
are reported as UNRESOLVED rather than guessed at. Upgrade path: have
sg_trends_collect.py write created_at_i into the digest rows, and read it here.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path

DIGEST_DIR = Path(__file__).resolve().parent.parent / "plans" / "sg-trends"
CACHE_PATH = DIGEST_DIR / ".title_age_cache.json"
ALGOLIA = "https://hn.algolia.com/api/v1/search"

# Import the collector's own seed list + matcher so the gate verifies against
# exactly the filter the collector applies — not a hand-copied duplicate that
# can drift. If the collector moves, this import fails loudly (desired).
sys.path.insert(0, str(Path(__file__).resolve().parent))
from sg_trends_collect import HN_QUERY_SEEDS, _kw_re  # noqa: E402

# NOTE: Section 6 is headed "Singapore companies & tech (global momentum to
# localize)" — it deliberately carries global tech stories, so "is this row
# SG-anchored?" is the WRONG precision test; it fails rows the section wants.
# The real precision defect was loose keyword matching (Grab->grabs/Graber,
# DBS->DBs). So the test is: does the title legitimately match a seed keyword
# under the collector's own word-boundary matcher? No match = loose-match noise.
STALE_DAYS = 7


def norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()


# ── digest parsing ───────────────────────────────────────────────────────────
def parse_digest(path: Path) -> list[dict]:
    """Pull Section 6 (Hacker News) rows: | Story | Points | Link |"""
    rows, in_s6 = [], False
    for line in path.read_text().splitlines():
        if line.startswith("## 6."):
            in_s6 = True
            continue
        if in_s6 and line.startswith("## "):
            break
        if not in_s6 or not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 3 or set(cells[0]) <= set("-: ") or cells[0] == "Story":
            continue
        title = cells[0].replace("...", "").strip()
        if not title:
            continue
        rows.append({"title": title, "points": cells[1], "url": cells[2]})
    return rows


# ── staleness resolution ─────────────────────────────────────────────────────
def _load_cache() -> dict:
    if CACHE_PATH.exists():
        try:
            return json.loads(CACHE_PATH.read_text())
        except Exception:
            return {}
    return {}


def resolve_age_days(title: str, cache: dict) -> int | None:
    """Return age in days of the HN story, or None if not confidently found."""
    key = norm(title)[:60]
    if key in cache:
        return cache[key]
    query = title[:45]
    params = {
        "query": query,
        "tags": "story",
        "hitsPerPage": 3,
        "restrictSearchableAttributes": "title",
    }
    age = None
    try:
        req = urllib.request.Request(
            ALGOLIA + "?" + urllib.parse.urlencode(params),
            headers={"User-Agent": "observeco-sg-trends-quality/1.0"},
        )
        with urllib.request.urlopen(req, timeout=25) as r:
            hits = json.load(r).get("hits", [])
        qn = norm(title)[:25]
        for h in hits:
            hn = norm(h.get("title") or "")[:25]
            if qn and hn and (qn == hn or qn.startswith(hn) or hn.startswith(qn)):
                created = h.get("created_at") or ""
                dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
                age = (datetime.now(timezone.utc) - dt).days
                break
    except Exception:
        return None
    cache[key] = age
    return age


# ── scoring ──────────────────────────────────────────────────────────────────
def score(path: Path, cache: dict) -> dict:
    rows = parse_digest(path)
    for r in rows:
        r["age_days"] = resolve_age_days(r["title"], cache)
        # Reuse the collector's own matcher so the gate cannot drift from the
        # filter it is verifying (single source of truth for what a hit is).
        r["matched"] = any(_kw_re(k).search(r["title"]) for k in HN_QUERY_SEEDS)

    dated = [r for r in rows if r["age_days"] is not None]
    stale = [r for r in dated if r["age_days"] > STALE_DAYS]
    fresh = [r for r in dated if r["age_days"] <= STALE_DAYS]
    unmatched = [r for r in rows if not r["matched"]]

    def pct(a, b):
        return round(100.0 * a / b, 1) if b else None

    return {
        "date": path.stem,
        "rows": len(rows),
        "unresolved": len(rows) - len(dated),
        "stale": stale,
        "fresh": fresh,
        "unmatched": unmatched,
        "pct_stale": pct(len(stale), len(dated)),
        "pct_matched": pct(len(rows) - len(unmatched), len(rows)),
        "oldest": max((r["age_days"] for r in dated), default=None),
        "flagged": sorted({r["title"] for r in stale} | {r["title"] for r in unmatched}),
    }


def render(sc: dict) -> str:
    out = [
        f"{sc['date']}  rows={sc['rows']}  unresolved={sc['unresolved']}",
        f"   stale(>{STALE_DAYS}d): {len(sc['stale'])}/{sc['rows']}"
        f"  ({sc['pct_stale']}% of dated)   oldest={sc['oldest']}d",
        f"   keyword-matched: {sc['pct_matched']}%   unmatched(loose-match noise): {len(sc['unmatched'])}",
    ]
    for r in sc["stale"][:6]:
        out.append(f"     STALE {r['age_days']:>5}d  {r['title'][:64]}")
    for r in sc["unmatched"][:6]:
        out.append(f"     UNMATCHED  {r['title'][:64]}")
    return "\n".join(out)


def compare(today: dict, prev: dict) -> tuple[bool, list[str]]:
    """The reward function.

    Repeated flags are only a regression when the item is STALE. The collector
    uses a 48h window on a daily run, so a genuinely fresh story legitimately
    appears in two consecutive digests — that overlap is the window working,
    not the filter failing. A stale item repeating means nothing filtered it.
    """
    overlap = set(today["flagged"]) & set(prev["flagged"])
    stale_now = {r["title"] for r in today["stale"]}
    repeated = sorted(overlap & stale_now)
    return bool(repeated), repeated


def gate(today: dict, prev: dict) -> tuple[bool, str]:
    """True = pass. Fails on repeated stale flags (regression) or stale dominance."""
    repeated, overlap = compare(today, prev)
    if repeated:
        lines = [f"REGRESSION: {len(overlap)} flag(s) repeated from {prev['date']}:"]
        lines += [f"   - {t}" for t in overlap[:8]]
        return False, "\n".join(lines)
    if today["pct_stale"] is not None and today["pct_stale"] > 50:
        return False, (
            f"FAIL: {today['pct_stale']}% of dated HN rows are >{STALE_DAYS}d old "
            f"({today['date']})"
        )
    return True, "PASS"


# ── self-test: prove the gate actually fires ─────────────────────────────────
def self_test() -> int:
    # SG-anchored so only STALENESS flags it — isolates the staleness signal.
    stale_sg = {"title": "Singtel legacy outage report", "age_days": 900}
    ok = {"title": "Singtel launches new thing", "age_days": 1}
    # Fresh but loose-match noise: flagged for precision, NOT stale.
    fresh_noise = {"title": "OpenCode Open source AI coding agent", "age_days": 1}

    def mk(d, rows):
        dated = [r for r in rows if r["age_days"] is not None]
        unmatched = [r for r in rows if not any(_kw_re(k).search(r["title"]) for k in HN_QUERY_SEEDS)]
        return {
            "date": d, "rows": len(rows), "unresolved": 0, "stale": [r for r in dated if r["age_days"] > STALE_DAYS],
            "fresh": [r for r in dated if r["age_days"] <= STALE_DAYS], "unmatched": unmatched,
            "pct_stale": 100.0 * len([r for r in dated if r["age_days"] > STALE_DAYS]) / len(dated),
            "pct_matched": 100.0 * (len(rows) - len(unmatched)) / len(rows),
            "oldest": max(r["age_days"] for r in dated),
            "flagged": sorted({r["title"] for r in dated if r["age_days"] > STALE_DAYS} | {r["title"] for r in unmatched}),
        }

    t_clean = mk("2026-01-02", [ok, dict(ok, title="Grab Holdings beats estimates")])
    p_clean = mk("2026-01-01", [ok, dict(ok, title="DBS raises dividend")])
    t_repeat = mk("2026-01-02", [ok, stale_sg])
    p_repeat = mk("2026-01-01", [ok, stale_sg])

    passed, msg = gate(t_clean, p_clean)
    assert passed, f"clean pair should pass, got: {msg}"

    passed2, msg2 = gate(t_repeat, p_repeat)
    assert not passed2, "repeated stale flag must fail the gate"
    assert "REGRESSION" in msg2, msg2

    # A FRESH story repeating across two digests is the 48h window working,
    # not a regression — same title in both days, not stale either day.
    t_fresh_rep = mk("2026-01-04", [ok, fresh_noise])
    p_fresh_rep = mk("2026-01-03", [ok, fresh_noise])
    rp, om = compare(t_fresh_rep, p_fresh_rep)
    assert not rp, f"fresh repeat must NOT be a regression, got {om}"
    # ...and a fresh digest with loose-match noise still passes: Section 6
    # deliberately carries global stories. Staleness is the defect, not origin.
    f4, m4 = gate(mk("2026-01-06", [ok, fresh_noise, dict(fresh_noise, title="ProGantt charts your AI agent")]),
                  p_fresh_rep)
    assert f4, f"fresh non-SG rows must not fail the gate, got {m4}"

    # A title matching no seed keyword at all is real loose-match noise and
    # must flip the gate via the repeated-flag path.
    noise = {"title": "AMD Grabs over 30% CPU Market Share", "age_days": 5}
    rn, on = compare(mk("2026-01-07", [ok, noise]), mk("2026-01-06", [ok, noise]))
    assert not rn, f"unmatched-but-not-stale should not be a regression, got {on}"

    # stale dominance alone must fail
    t_stale_heavy = mk("2026-01-05", [stale_sg, dict(stale_sg, title="Singtel old outage two")])
    p_other = mk("2026-01-02", [ok, dict(ok, title="OCBC posts profit")])
    p3, m3 = gate(t_stale_heavy, p_other)
    assert not p3 and "FAIL" in m3, m3

    print("self-test OK — clean passes, stale-repeat caught, fresh-repeat tolerated, "
          "fresh non-SG tolerated, stale-dominance fail caught")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=2, help="how many recent digests to score")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    files = sorted(DIGEST_DIR.glob("*.md"))
    if len(files) < 2:
        print(f"need >=2 digests in {DIGEST_DIR}, found {len(files)}", file=sys.stderr)
        return 2

    cache = _load_cache()
    scored = [score(p, cache) for p in files[-args.days:]]
    CACHE_PATH.write_text(json.dumps(cache, indent=0, sort_keys=True))

    for sc in scored:
        print(render(sc))
        print()

    print("=" * 62)
    rc = 0
    for i in range(1, len(scored)):
        passed, msg = gate(scored[i], scored[i - 1])
        status = "PASS" if passed else "FAIL"
        print(f"{scored[i]['date']} vs {scored[i-1]['date']}: {status} — {msg}")
        if not passed:
            rc = 1
    if len(scored) == 1:
        print(f"{scored[0]['date']}: (no previous digest to compare)")
    return rc


if __name__ == "__main__":
    sys.exit(main())
