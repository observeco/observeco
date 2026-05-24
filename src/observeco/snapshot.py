"""`observeco snapshot` — generate living documentation from agent ecosystem data."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional

from observeco.config import load_config
from observeco.db import Database


def _ensure_dir(path: str) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p

def _build_architecture_svg(agents: list[dict], status_summary: dict) -> str:
    now = datetime.now().isoformat()
    n = max(len(agents), 1)
    box_w = 120
    box_h = 50
    pad = 20
    cols = min(n, 4)
    rows = (n + cols - 1) // cols
    svg_w = cols * (box_w + pad) + pad
    svg_h = rows * (box_h + pad) + pad + 40
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{svg_w}" height="{svg_h}" viewBox="0 0 {svg_w} {svg_h}">',
        f'<text x="{svg_w/2}" y="20" text-anchor="middle" font-size="14" font-family="sans-serif" fill="#333">Agent Architecture &mdash; {now[:10]}</text>',
    ]
    for i, agent in enumerate(agents[:n]):
        col = i % cols
        row = i // cols
        x = pad + col * (box_w + pad)
        y = pad + row * (box_h + pad) + 30
        name = agent.get("agent_name", agent.get("name", f"agent-{i}"))
        status = "unknown"
        if status_summary:
            s = status_summary.get(name, {})
            status = s.get("status", "unknown")
        colors = {"alive": "#4ade80", "dead": "#f87171", "error": "#fbbf24", "unknown": "#9ca3af"}
        fill = colors.get(status, "#9ca3af")
        text_color = "#1a1a1a" if status in ("alive", "error", "unknown") else "#fff"
        parts.append(f'<rect x="{x}" y="{y}" width="{box_w}" height="{box_h}" rx="5" fill="{fill}" stroke="#333" stroke-width="1"/>')
        parts.append(f'<text x="{x + box_w/2}" y="{y + box_h/2 + 4}" text-anchor="middle" font-size="11" font-family="sans-serif" fill="{text_color}">{name}</text>')
        parts.append(f'<text x="{x + box_w/2}" y="{y + box_h - 6}" text-anchor="middle" font-size="9" font-family="sans-serif" fill="{text_color}">{status}</text>')
    parts.append("</svg>")
    return "\n".join(parts)

def _build_token_chart_svg(data: list[dict]) -> str:
    now = datetime.now().isoformat()
    if len(data) < 2:
        return '<svg xmlns="http://www.w3.org/2000/svg" width="600" height="200"><text x="300" y="100" text-anchor="middle" font-size="13" font-family="sans-serif" fill="#666">Token data accumulates over ~7 days</text></svg>'
    svg_w = 600
    svg_h = 220
    chart_w = 500
    chart_h = 160
    values = [d.get("total_tokens", d.get("current_tokens", 0)) for d in data[:14]]
    max_val = max(values) if values else 1
    bars = len(values)
    bar_w = min(30, chart_w // bars - 2)
    gap = 2
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{svg_w}" height="{svg_h}">',
        f'<text x="{svg_w/2}" y="20" text-anchor="middle" font-size="14" font-family="sans-serif" fill="#333">Token Evolution &mdash; {now[:10]}</text>',
    ]
    for i, v in enumerate(values):
        x = 50 + i * (bar_w + gap)
        h = (v / max_val) * chart_h
        y = 40 + chart_h - h
        parts.append(f'<rect x="{x}" y="{y}" width="{bar_w}" height="{h}" fill="#60a5fa" rx="2"/>')
        parts.append(f'<text x="{x + bar_w/2}" y="{y - 3}" text-anchor="middle" font-size="9" font-family="sans-serif" fill="#666">{v}</text>')
    parts.append("</svg>")
    return "\n".join(parts)

def _build_error_timeline_svg(errors: list[dict]) -> str:
    now = datetime.now().isoformat()
    if not errors:
        return '<svg xmlns="http://www.w3.org/2000/svg" width="600" height="200"><text x="300" y="100" text-anchor="middle" font-size="13" font-family="sans-serif" fill="#666">No error events recorded yet</text></svg>'
    svg_w = 600
    svg_h = 220
    n = min(len(errors), 20)
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{svg_w}" height="{svg_h}">',
        f'<text x="{svg_w/2}" y="20" text-anchor="middle" font-size="14" font-family="sans-serif" fill="#333">Error Timeline &mdash; {now[:10]}</text>',
        f'<line x1="50" y1="120" x2="{50 + n * 25}" y2="120" stroke="#ccc" stroke-width="1"/>',
    ]
    for i, err in enumerate(errors[:n]):
        x = 50 + i * 25
        severity = err.get("severity", "error")
        colors = {"info": "#60a5fa", "warning": "#fbbf24", "error": "#f87171", "critical": "#ef4444"}
        fill = colors.get(severity, "#f87171")
        r = 5 if severity == "critical" else 4
        parts.append(f'<circle cx="{x}" cy="120" r="{r}" fill="{fill}" stroke="#333" stroke-width="0.5"/>')
        parts.append(f'<text x="{x}" y="135" text-anchor="middle" font-size="7" font-family="sans-serif" fill="#666">{err.get("error_type","?")[:6]}</text>')
    parts.append("</svg>")
    return "\n".join(parts)

def _build_self_healing_log(heal_events: list[dict]) -> str:
    if not heal_events:
        return "# Self-Healing Log\n\nNo self-healing events recorded.\n"
    lines = ["# Self-Healing Log", f"Generated: {datetime.now().isoformat()}", ""]
    for e in heal_events:
        ts = e.get("timestamp", "")
        msg = e.get("error_message", "")
        etype = e.get("error_type", "heal_event")
        lines.append(f"- **{ts}** [{etype}]: {msg[:200]}")
    return "\n".join(lines)

def _build_readme_snapshot(name: str, agents: list, status_summary: dict,
                           token_data: list, errors: list, heal_events: list,
                           has_placeholders: bool) -> str:
    total = len(agents)
    alive = dead = err_count = 0
    for a in agents:
        aname = a.get("agent_name", a.get("name", ""))
        s = status_summary.get(aname, {}).get("status", "unknown")
        if s == "alive":
            alive += 1
        elif s == "dead":
            dead += 1
        elif s == "error":
            err_count += 1
    lines = [
        f"# ObserveCo Snapshot: {name}",
        f"**Generated:** {datetime.now().isoformat()}",
        "**Tool:** ObserveCo `snapshot` command",
        "",
        "## Fleet Summary",
        f"- **{total}** agents total",
        f"- **{alive}** alive",
    ]
    if dead:
        lines.append(f"- **{dead}** dead")
    if err_count:
        lines.append(f"- **{err_count}** with errors")
    lines.extend(["", "## Token Statistics"])
    if token_data:
        total_tokens = sum(d.get("total_tokens", 0) for d in token_data)
        avg_savings = sum(d.get("savings_ratio", 0) for d in token_data) / max(len(token_data), 1)
        lines.append(f"- Total tokens tracked: {total_tokens}")
        lines.append(f"- Average savings ratio: {avg_savings:.1%}")
    else:
        lines.append("- No token data yet -- run `observeco chisel trim` to collect")
        has_placeholders = True
    lines.extend(["", "## Error Summary"])
    if errors:
        lines.append(f"- {len(errors)} errors recorded")
        by_agent = {}
        for e in errors:
            aname = e.get("agent_name", "?")
            by_agent[aname] = by_agent.get(aname, 0) + 1
        for aname, count in sorted(by_agent.items(), key=lambda x: -x[1])[:5]:
            lines.append(f"  - {aname}: {count} errors")
    else:
        lines.append("- No errors recorded")
        has_placeholders = True
    lines.extend(["", "## Drift Summary"])
    try:
        db = Database()
        conn = db._get_conn()
        drift_rows = conn.execute(
            "SELECT agent_name, component, delta_pct, breached FROM chisel_drift "
            "WHERE breached=1 ORDER BY delta_pct DESC LIMIT 10"
        ).fetchall()
        if drift_rows:
            for r in drift_rows:
                lines.append(f"- **{r['agent_name']}**: {r['component']} drifted {r['delta_pct']:.1f}%")
        else:
            lines.append("- No drift thresholds breached")
    except Exception:
        lines.append("- Drift data unavailable")
    lines.extend(["", "## Self-Healing Log"])
    if heal_events:
        for e in heal_events[:5]:
            lines.append(f"- {e.get('timestamp','')}: {e.get('error_message','')[:100]}")
    else:
        lines.append("- No self-healing events recorded")
    if has_placeholders:
        lines.extend(["", "---", "",
                       "> **Note:** Snapshot data incomplete. Run the snapshot command again when agents have been monitored longer for richer visualizations."])
    return "\n".join(line for line in lines if line)

def run_snapshot(snapshot_name: str, output_dir: Optional[str] = None) -> None:
    out_dir = _ensure_dir(output_dir or f"./{snapshot_name}/")
    db = Database()
    load_config()
    agents_raw = db.get_agents()
    status_summary = db.get_agent_status_summary()
    all_errors = db.get_errors(limit=100)
    heal_events = [e for e in all_errors if "heal" in (e.get("error_type", "") or "")]
    try:
        conn = db._get_conn()
        token_data = [dict(r) for r in conn.execute(
            "SELECT * FROM chisel_trims ORDER BY timestamp DESC LIMIT 14"
        ).fetchall()]
    except Exception:
        token_data = []
    has_placeholders = False
    arch_svg = _build_architecture_svg(agents_raw, status_summary)
    (out_dir / "architecture.svg").write_text(arch_svg)
    print(f"  [OK] architecture.svg ({len(arch_svg)} chars)")
    token_svg = _build_token_chart_svg(token_data)
    if "Token data accumulates" in token_svg:
        has_placeholders = True
    (out_dir / "token-evolution-chart.svg").write_text(token_svg)
    print(f"  [OK] token-evolution-chart.svg ({len(token_svg)} chars)")
    error_svg = _build_error_timeline_svg(all_errors[:20])
    if "No error events" in error_svg:
        has_placeholders = True
    (out_dir / "error-timeline.svg").write_text(error_svg)
    print(f"  [OK] error-timeline.svg ({len(error_svg)} chars)")
    heal_md = _build_self_healing_log(heal_events)
    if "No self-healing events" in heal_md:
        has_placeholders = True
    (out_dir / "self-healing-log.md").write_text(heal_md)
    print(f"  [OK] self-healing-log.md ({len(heal_md)} chars)")
    dep_svg = ('<svg xmlns="http://www.w3.org/2000/svg" width="600" height="200">'
               '<text x="300" y="100" text-anchor="middle" font-size="13" font-family="sans-serif" fill="#666">'
               'Not enough data - check back after agents have been running for at least 1 hour'
               '</text></svg>')
    has_placeholders = True
    (out_dir / "dependency-graph.svg").write_text(dep_svg)
    print(f"  [OK] dependency-graph.svg ({len(dep_svg)} chars)")
    readme = _build_readme_snapshot(snapshot_name, agents_raw, status_summary,
                                     token_data, all_errors, heal_events, has_placeholders)
    (out_dir / "README.snapshot.md").write_text(readme)
    print(f"  [OK] README.snapshot.md ({len(readme)} chars)")
    print(f"\nSnapshot '{snapshot_name}' written to {out_dir.resolve()}")
