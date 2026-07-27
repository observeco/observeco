#!/usr/bin/env python3
"""Verify every metric served by /api/analytics/tokens against raw DB aggregates.

Usage:
    python3 scripts/verify_token_analytics.py [--days 7] [--agent __all__]

Exits 0 if all checks pass, 1 if any mismatch found.
"""

import argparse
import json
import math
import re
import sys
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from observeco.db import Database

# ── helpers ──────────────────────────────────────────────────────────────

PASS = "✓"
FAIL = "✗"


def fmt_tok(n: int) -> str:
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    if n >= 1000:
        return f"{n/1000:.1f}K"
    return str(n)


def fmt_dollar(c: float) -> str:
    if c >= 100:
        return f"${c:.0f}"
    if c >= 1:
        return f"${c:.2f}"
    return f"${c:.4f}"


def round4(x):
    return round(x, 4)


def round5(x):
    return round(x, 5)


def round1(x):
    return round(x, 1)


# ── DB queries ──────────────────────────────────────────────────────────

def get_raw_aggregates(since: int, bucket_sec: int, agent_filter: str, label_fmt: str = "%m/%d"):
    """Query raw token_logs and return dicts matching the route's computation."""
    db = Database()
    conn = db._get_conn()

    # All rows in window
    if agent_filter == "__all__":
        rows = conn.execute(
            "SELECT * FROM token_logs WHERE recorded_at >= ? ORDER BY recorded_at",
            (since,),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM token_logs WHERE recorded_at >= ? AND agent_name = ? ORDER BY recorded_at",
            (since, agent_filter),
        ).fetchall()

    logs = [dict(r) for r in rows]

    # Totals
    total_cost = sum(log.get("cost", 0) or 0 for log in logs)
    total_input = sum(log.get("input_tokens", 0) or 0 for log in logs)
    total_output = sum(log.get("output_tokens", 0) or 0 for log in logs)
    total_cache_read = sum(log.get("cache_read_tokens", 0) or 0 for log in logs)
    total_cache_create = sum(log.get("cache_creation_tokens", 0) or 0 for log in logs)
    total_attributed = sum(
        (log.get("total_tokens", 0) or 0) for log in logs if log.get("source") == "otel"
    )
    total_unattributed = sum(
        (log.get("total_tokens", 0) or 0) for log in logs if log.get("source") != "otel"
    )
    total_all = total_attributed + total_unattributed
    turn_count = len(logs)

    # Per-agent
    agent_data = {}
    for log in logs:
        aname = log.get("agent_name", "unknown")
        if aname not in agent_data:
            agent_data[aname] = {
                "cost": 0, "tokens": 0, "input": 0, "output": 0,
                "cache_read": 0, "cache_create": 0, "count": 0,
                "source": log.get("source", "unknown"),
            }
        d = agent_data[aname]
        d["cost"] += log.get("cost", 0) or 0
        d["tokens"] += log.get("total_tokens", 0) or 0
        d["input"] += log.get("input_tokens", 0) or 0
        d["output"] += log.get("output_tokens", 0) or 0
        d["cache_read"] += log.get("cache_read_tokens", 0) or 0
        d["cache_create"] += log.get("cache_creation_tokens", 0) or 0
        d["count"] += 1

    sorted_agents = sorted(agent_data.items(), key=lambda x: -x[1]["cost"])

    # Day buckets (same logic as route)
    day_buckets = {}
    for log in logs:
        bk = (log.get("recorded_at", 0) // bucket_sec) * bucket_sec
        if bk not in day_buckets:
            day_buckets[bk] = {"cost": 0, "total": 0, "input": 0, "output": 0,
                               "cache": 0, "cache_create": 0, "est": 0, "count": 0}
        day_buckets[bk]["cost"] += log.get("cost", 0) or 0
        day_buckets[bk]["total"] += log.get("total_tokens", 0) or 0
        day_buckets[bk]["input"] += log.get("input_tokens", 0) or 0
        day_buckets[bk]["output"] += log.get("output_tokens", 0) or 0
        day_buckets[bk]["cache"] += log.get("cache_read_tokens", 0) or 0
        day_buckets[bk]["cache_create"] += log.get("cache_creation_tokens", 0) or 0
        day_buckets[bk]["count"] += 1
        if log.get("source") != "otel":
            day_buckets[bk]["est"] += (log.get("input_tokens", 0) or 0) + (log.get("output_tokens", 0) or 0)

    sorted_keys = sorted(day_buckets.keys())

    # Chart data arrays (matching route formulas)
    cost_data = [round4(day_buckets[k]["cost"]) for k in sorted_keys]
    input_data = [day_buckets[k]["input"] // 1000 for k in sorted_keys]
    output_data = [day_buckets[k]["output"] // 1000 for k in sorted_keys]
    cache_data = [day_buckets[k]["cache"] // 1000 for k in sorted_keys]
    est_data = [round(day_buckets[k]["est"] / 1000) for k in sorted_keys]
    total_data = [day_buckets[k]["total"] // 1000 for k in sorted_keys]
    tokens_per_turn = [round(day_buckets[k]["total"] / max(day_buckets[k]["count"], 1)) for k in sorted_keys]
    output_input_ratio = [round(day_buckets[k]["output"] / max(day_buckets[k]["input"], 1), 2) for k in sorted_keys]
    cache_rate_data = [
        round(day_buckets[k]["cache"] / max(day_buckets[k]["input"] + day_buckets[k]["cache"] + day_buckets[k]["cache_create"], 1) * 100, 1)
        for k in sorted_keys
    ]
    cost_per_turn = [round5(day_buckets[k]["cost"] / max(day_buckets[k]["count"], 1)) for k in sorted_keys]

    # est_effective (suppress est where real data exists)
    est_effective = [
        0 if (day_buckets[k]["input"] > 0 or day_buckets[k]["output"] > 0 or day_buckets[k]["cache"] > 0)
        else day_buckets[k]["est"]
        for k in sorted_keys
    ]

    # Derived totals
    attr_pct = round(total_attributed / total_all * 100) if total_all else 0
    overall_cache_rate = round(total_cache_read / max(total_cache_read + total_cache_create, 1) * 100)
    top_agent = sorted_agents[0][0] if sorted_agents else ""
    top_cost = sorted_agents[0][1]["cost"] if sorted_agents else 0
    top_spender_pct = round(top_cost / max(total_cost, 1) * 100)
    stacked_total_k = sum(
        day_buckets[k]["input"] + day_buckets[k]["output"] + day_buckets[k]["cache"] + est_effective[i]
        for i, k in enumerate(sorted_keys)
    ) // 1000

    # suppressed_est
    suppressed_est = any(
        day_buckets[k]["est"] > 0 and est_effective[i] == 0
        for i, k in enumerate(sorted_keys)
    )

    return {
        "labels": [datetime.fromtimestamp(k).strftime(label_fmt) for k in sorted_keys],
        "cost_data": cost_data,
        "total_data": total_data,
        "input_data": input_data,
        "output_data": output_data,
        "cache_data": cache_data,
        "est_data": est_effective,
        "tokens_per_turn": tokens_per_turn,
        "output_input_ratio": output_input_ratio,
        "cache_rate_data": cache_rate_data,
        "cost_per_turn": cost_per_turn,
        "total_cost": total_cost,
        "turn_count": turn_count,
        "overall_cache_rate": overall_cache_rate,
        "attr_pct": attr_pct,
        "top_agent": top_agent,
        "top_spender_pct": top_spender_pct,
        "total_all": total_all,
        "stacked_total_k": stacked_total_k,
        "total_input": total_input,
        "total_output": total_output,
        "total_cache_read": total_cache_read,
        "total_cache_create": total_cache_create,
        "sorted_agents": sorted_agents,
        "suppressed_est": suppressed_est,
    }


def extract_chart_data(html: str) -> dict:
    """Extract all window._*Chart objects from the served HTML."""
    result = {}
    patterns = {
        "_tokenChart": r"window\._tokenChart\s*=\s*(\{.*?\});",
        "_tptChart": r"window\._tptChart\s*=\s*(\{.*?\});",
        "_oirChart": r"window\._oirChart\s*=\s*(\{.*?\});",
        "_cacheRateChart": r"window\._cacheRateChart\s*=\s*(\{.*?\});",
        "_cptChart": r"window\._cptChart\s*=\s*(\{.*?\});",
    }
    for name, pat in patterns.items():
        m = re.search(pat, html, re.DOTALL)
        if m:
            result[name] = json.loads(m.group(1))
    return result


def extract_verdict_values(html: str) -> dict:
    """Extract verdict card values from HTML."""
    result = {}

    # total_cost from verdict card: "$X.XX" or "$X.XXXX"
    m = re.search(r'total cost[^<]*</span>', html)
    if m:
        # The span before contains the dollar value
        pass

    # Simpler: extract from the vc-num spans
    # total cost
    m = re.search(r'total cost[^<]*</span></div>', html)
    if m:
        # Go back to find the dollar value
        pass

    # Actually let's extract from the text patterns
    # "total cost · N calls"
    m = re.search(r'total cost[^·]*·\s*([\d,]+)\s*calls', html)
    if m:
        result["turn_count"] = int(m.group(1).replace(",", ""))

    # "N% fleet cache hit"
    m = re.search(r'(\d+)%\s*fleet cache hit', html)
    if m:
        result["overall_cache_rate"] = int(m.group(1))

    # "N% attributed"
    m = re.search(r'(\d+)%\s*attributed', html)
    if m:
        result["attr_pct"] = int(m.group(1))

    # "N% top spender"
    m = re.search(r'(\d+)%\s*top spender', html)
    if m:
        result["top_spender_pct"] = int(m.group(1))

    # Top agent name
    m = re.search(r'(\d+)%\s*<span[^>]*>([^<]+)</span>\s*top spender', html)
    if m:
        result["top_agent"] = m.group(2)

    # "N agents · X calls indexed" from subtitle
    m = re.search(r'(\d+)\s*agents\s*·\s*([\d.]+[KM]?)\s*calls indexed', html)
    if m:
        result["agent_count"] = int(m.group(1))
        val_str = m.group(2)
        if val_str.endswith("M"):
            result["total_all"] = int(float(val_str[:-1]) * 1_000_000)
        elif val_str.endswith("K"):
            result["total_all"] = int(float(val_str[:-1]) * 1000)
        else:
            result["total_all"] = int(val_str)

    # Tokens/Turn header value
    m = re.search(r'Tokens / Turn[^<]*<span class="cc-val mono">([^<]+)</span>', html)
    if m:
        result["tokens_per_turn_overall"] = m.group(1)

    # Output/Input header value
    m = re.search(r'Output / Input[^<]*<span class="cc-val mono">([^<]+)</span>', html)
    if m:
        result["output_input_overall"] = float(m.group(1))

    # Cache Hit Rate header value
    m = re.search(r'Cache Hit Rate[^<]*<span class="cc-val mono">(\d+)%</span>', html)
    if m:
        result["cache_rate_header"] = int(m.group(1))

    # Cost/Turn header value
    m = re.search(r'Cost / Turn[^<]*<span class="cc-val mono">\$?([^<]+)</span>', html)
    if m:
        result["cost_per_turn_overall"] = m.group(1)

    # Token Composition header value
    m = re.search(r'Token Composition[^<]*<span class="cc-val mono">([^<]+)</span>', html)
    if m:
        result["stacked_total"] = m.group(1)

    return result


def extract_agent_table(html: str) -> list:
    """Extract per-agent rows from the table."""
    agents = []
    # Match each <tr> in the agent table
    # Pattern: <tr ...><td><span class="ag">NAME</span></td><td class="mono r">COST</td><td class="mono r">TOKENS</td>...
    rows = re.findall(
        r'<tr[^>]*>'
        r'\s*<td><span class="ag">([^<]+)</span></td>'
        r'\s*<td class="mono r">([^<]+)</td>'
        r'\s*<td class="mono r">([^<]+)</td>'
        r'\s*<td class="mono">([^<]*)</td>'
        r'\s*<td><span class="dq [^"]+">([^<]+)</span></td>'
        r'\s*<td class="r">.*?<span class="mono"[^>]*>([^<]+)</span>',
        html, re.DOTALL
    )
    for r in rows:
        agents.append({
            "name": r[0],
            "cost_str": r[1],
            "tokens_str": r[2],
            "model": r[3],
            "dq": r[4],
            "cache_str": r[5],
        })
    return agents


# ── Comparison ──────────────────────────────────────────────────────────

def compare_float(label: str, got, expected, tolerance: float = 0.01) -> bool:
    """Compare two floats within tolerance. Returns True if match."""
    if abs(got - expected) <= tolerance:
        return True
    print(f"  {FAIL} {label}: got={got}, expected={expected} (diff={abs(got-expected):.4f})")
    return False


def compare_int(label: str, got, expected) -> bool:
    if got == expected:
        return True
    print(f"  {FAIL} {label}: got={got}, expected={expected}")
    return False


def compare_list(label: str, got: list, expected: list, tolerance: float = 0.01) -> bool:
    if len(got) != len(expected):
        print(f"  {FAIL} {label}: length mismatch got={len(got)} expected={len(expected)}")
        return False
    ok = True
    for i, (g, e) in enumerate(zip(got, expected)):
        if isinstance(g, (int, float)) and isinstance(e, (int, float)):
            if abs(g - e) > tolerance:
                print(f"  {FAIL} {label}[{i}]: got={g}, expected={e}")
                ok = False
        elif g != e:
            print(f"  {FAIL} {label}[{i}]: got={g!r}, expected={e!r}")
            ok = False
    if ok:
        print(f"  {PASS} {label}: {len(got)} values match")
    return ok


# ── Main ────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Verify token analytics route against raw DB")
    parser.add_argument("--days", type=int, default=7, help="Time window in days")
    parser.add_argument("--agent", type=str, default="__all__", help="Agent filter")
    args = parser.parse_args()

    now = int(time.time())
    # Match route's adaptive bucketing
    if args.days == 1:
        bucket_sec = 3600
        n_buckets = 24
        label_fmt = "%H:00"
    else:
        bucket_sec = 86400
        n_buckets = args.days
        label_fmt = "%m/%d"
    since = now - n_buckets * bucket_sec

    print(f"Verifying /api/analytics/tokens?days={args.days}&agent={args.agent}")
    print(f"Window: {args.days}d, since={since} ({time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime(since))})")
    print()

    # 1. Get raw DB aggregates
    print("Querying raw DB...")
    raw = get_raw_aggregates(since, bucket_sec, args.agent, label_fmt)
    print(f"  {len(raw['sorted_agents'])} agents, {raw['turn_count']} calls, {len(raw['labels'])} buckets")
    print()

    # 2. Hit the route
    print("Fetching route...")
    import urllib.request
    url = f"http://127.0.0.1:8899/api/analytics/tokens?days={args.days}&agent={args.agent}"
    req = urllib.request.Request(url)
    req.add_header("X-ObserveCo-Token", "FxrXunlGzEHN6mtX550m6okEgSjfe5xnI84YOIDLLFk")
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        html = resp.read().decode()
    except Exception as e:
        print(f"  {FAIL} Failed to fetch route: {e}")
        sys.exit(1)
    print(f"  {len(html)} bytes received")
    print()

    # 3. Extract chart data
    charts = extract_chart_data(html)
    verdict = extract_verdict_values(html)
    agent_rows = extract_agent_table(html)

    print("=== Chart Data Verification ===")
    all_pass = True

    # Token chart
    if "_tokenChart" in charts:
        tc = charts["_tokenChart"]
        print(f"\nToken Composition Chart:")
        all_pass &= compare_list("cost_data", tc.get("cost_data", []), raw["cost_data"])
        all_pass &= compare_list("total_data", tc.get("total_data", []), raw["total_data"])
        all_pass &= compare_list("input_data", tc.get("input_data", []), raw["input_data"])
        all_pass &= compare_list("output_data", tc.get("output_data", []), raw["output_data"])
        all_pass &= compare_list("cache_data", tc.get("cache_data", []), raw["cache_data"])
        all_pass &= compare_list("est_data", tc.get("est_data", []), raw["est_data"])
        all_pass &= compare_int("suppressed_est", tc.get("suppressed_est", False), raw["suppressed_est"])
    else:
        print(f"  {FAIL} _tokenChart not found in HTML")
        all_pass = False

    # Tokens/Turn chart
    if "_tptChart" in charts:
        tpt = charts["_tptChart"]
        print(f"\nTokens/Turn Chart:")
        all_pass &= compare_list("data", tpt.get("data", []), raw["tokens_per_turn"])
    else:
        print(f"  {FAIL} _tptChart not found")
        all_pass = False

    # Output/Input chart
    if "_oirChart" in charts:
        oir = charts["_oirChart"]
        print(f"\nOutput/Input Chart:")
        all_pass &= compare_list("data", oir.get("data", []), raw["output_input_ratio"])
    else:
        print(f"  {FAIL} _oirChart not found")
        all_pass = False

    # Cache Rate chart
    if "_cacheRateChart" in charts:
        crc = charts["_cacheRateChart"]
        print(f"\nCache Rate Chart:")
        all_pass &= compare_list("data", crc.get("data", []), raw["cache_rate_data"])
    else:
        print(f"  {FAIL} _cacheRateChart not found")
        all_pass = False

    # Cost/Turn chart
    if "_cptChart" in charts:
        cpt = charts["_cptChart"]
        print(f"\nCost/Turn Chart:")
        all_pass &= compare_list("data", cpt.get("data", []), raw["cost_per_turn"])
    else:
        print(f"  {FAIL} _cptChart not found")
        all_pass = False

    # Labels
    print(f"\nLabels:")
    if "_tokenChart" in charts:
        all_pass &= compare_list("labels", charts["_tokenChart"].get("labels", []), raw["labels"])

    print(f"\n=== Header / Verdict Card Verification ===")

    # Turn count
    if "turn_count" in verdict:
        all_pass &= compare_int("turn_count", verdict["turn_count"], raw["turn_count"])

    # Overall cache rate
    if "overall_cache_rate" in verdict:
        all_pass &= compare_int("overall_cache_rate (verdict)", verdict["overall_cache_rate"], raw["overall_cache_rate"])
    if "cache_rate_header" in verdict:
        all_pass &= compare_int("overall_cache_rate (header)", verdict["cache_rate_header"], raw["overall_cache_rate"])

    # Attribution
    if "attr_pct" in verdict:
        all_pass &= compare_int("attr_pct", verdict["attr_pct"], raw["attr_pct"])

    # Top spender
    if "top_spender_pct" in verdict:
        all_pass &= compare_int("top_spender_pct", verdict["top_spender_pct"], raw["top_spender_pct"])

    # Total calls indexed (display rounding — route uses _fmt_tok which rounds to 1 decimal)
    if "total_all" in verdict:
        diff_pct = abs(verdict["total_all"] - raw["total_all"]) / max(raw["total_all"], 1) * 100
        if diff_pct <= 1.0:
            print(f"  {PASS} total_all (calls indexed): {verdict['total_all']} vs raw {raw['total_all']} (diff {diff_pct:.2f}% — display rounding)")
        else:
            print(f"  {FAIL} total_all (calls indexed): got={verdict['total_all']}, expected={raw['total_all']} (diff {diff_pct:.2f}%)")
            all_pass = False

    # Tokens/Turn overall
    if "tokens_per_turn_overall" in verdict:
        expected = fmt_tok(raw["total_all"] // max(raw["turn_count"], 1))
        all_pass &= compare_int("tokens_per_turn_overall", verdict["tokens_per_turn_overall"], expected)

    # Output/Input overall
    if "output_input_overall" in verdict:
        expected = round(raw["total_output"] / max(raw["total_input"], 1), 2)
        all_pass &= compare_float("output_input_overall", verdict["output_input_overall"], expected)

    # Cost/Turn overall
    if "cost_per_turn_overall" in verdict:
        expected = fmt_dollar(raw["total_cost"] / max(raw["turn_count"], 1))
        all_pass &= compare_int("cost_per_turn_overall", verdict["cost_per_turn_overall"], expected)

    print(f"\n=== Per-Agent Table Verification ===")
    print(f"  Route shows {len(agent_rows)} agents, raw has {len(raw['sorted_agents'])}")
    if len(agent_rows) != len(raw["sorted_agents"]):
        print(f"  {FAIL} Agent count mismatch")
        all_pass = False
    else:
        for i, (aname, d) in enumerate(raw["sorted_agents"]):
            if i >= len(agent_rows):
                break
            row = agent_rows[i]
            expected_cost = fmt_dollar(d["cost"])
            expected_tok = fmt_tok(d["tokens"])
            if row["cost_str"] != expected_cost:
                print(f"  {FAIL} {aname} cost: got={row['cost_str']}, expected={expected_cost}")
                all_pass = False
            if row["tokens_str"] != expected_tok:
                print(f"  {FAIL} {aname} tokens: got={row['tokens_str']}, expected={expected_tok}")
                all_pass = False
        print(f"  {PASS} All {len(agent_rows)} agent rows verified")

    print()
    if all_pass:
        print("ALL CHECKS PASSED")
        sys.exit(0)
    else:
        print("SOME CHECKS FAILED — see above")
        sys.exit(1)


if __name__ == "__main__":
    main()
