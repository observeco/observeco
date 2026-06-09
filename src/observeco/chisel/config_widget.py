#!/usr/bin/env python3
"""Config hygiene dashboard widget — Pro-locked embedded view.

Generates an HTML card for the ObserveCo dashboard showing config health score,
findings, and one-click fix. Pro-gated.

Called as an API endpoint (HTMX) or CLI report.
"""

import time
from pathlib import Path
from typing import Optional

from observeco.chisel.config_scanner import CONFIG_PATH, scan_config

# ── Dashboard widget generator ──────────────────────────────────────────────


def generate_widget_html(hermes_home: Optional[str] = None) -> str:
    """Generate an HTML widget card for the ObserveCo dashboard.

    Returns raw HTML for HTMX insertion. Empty string if error.
    """
    from observeco import license as lic
    is_pro = lic.require_pro()

    if hermes_home:
        report = scan_config(Path(hermes_home) / "config.yaml")
    else:
        report = scan_config(CONFIG_PATH)

    if report.config_health_score == 0 and not report.findings:
        return ""

    # Build findings list
    findings_html = ""
    for i, f in enumerate(report.findings[:5]):  # show top 5
        icon = {"critical": "🔴", "warning": "🟡", "info": "ℹ️"}.get(f.severity, "?")
        fixable = ""
        if f.auto_fixable and is_pro:
            fixable = f'<button onclick="fixConfigHygiene(\'{f.check}\')" style="background:transparent;border:1px solid #6366f1;color:#a5b4fc;border-radius:6px;padding:2px 10px;font-size:11px;cursor:pointer;margin-left:8px;">Fix</button>'
        findings_html += f"""<div style="display:flex;align-items:flex-start;gap:8px;padding:6px 0;border-bottom:1px solid #1e293b;font-size:12px;line-height:1.4;">
    <div style="flex-shrink:0;">{icon}</div>
    <div>
        <div style="color:#e2e8f0;">{f.description[:100]}</div>
        <div style="color:#94a3b8;font-size:11px;margin-top:2px;">~{f.estimated_waste_tok} tok/session{fixable}</div>
    </div>
</div>"""

    if not findings_html:
        return ""

    # Color-code health score
    if report.config_health_score >= 80:
        score_color = "#22c55e"
    elif report.config_health_score >= 50:
        score_color = "#eab308"
    else:
        score_color = "#ef4444"

    # Waste-to-cost explanation
    waste_k = round(report.total_waste_tok / 1000, 1)
    upsell = ""
    if not is_pro:
        upsell = f"""<div style="display:flex;align-items:center;gap:8px;padding:8px 12px;background:#1e1b4b;border-radius:8px;margin-top:8px;font-size:12px;">
    <span style="font-size:16px;">🔒</span>
    <span style="color:#94a3b8;flex:1;">Auto-detect token waste patterns that cost ~{waste_k}K tok/session — no manual audit needed</span>
    <button onclick="showBrainPro()" style="background:#6366f1;border:none;color:white;border-radius:6px;padding:4px 14px;font-size:12px;cursor:pointer;">Pro →</button>
</div>"""
    if is_pro:
        # Scheduled scan info
        last_scan = time.strftime("%H:%M", time.localtime())
        upsell = f"""<div style="display:flex;align-items:center;gap:8px;padding:8px 12px;background:#0f172a;border-radius:8px;margin-top:8px;font-size:11px;color:#94a3b8;">
    <span>🔄 Scans daily</span>
    <span style="flex:1;"></span>
    <span>Last scan: {last_scan}</span>
</div>"""

    html = f"""<div id="config-health-widget" style="background:#0f172a;border:1px solid #1e293b;border-radius:12px;padding:16px;margin:8px 0;">
    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:4px;">
        <div style="display:flex;align-items:center;gap:8px;">
            <span style="font-size:14px;">⚙️</span>
            <span style="font-size:14px;font-weight:600;color:#e2e8f0;">Config Health</span>
        </div>
        <div style="display:flex;align-items:center;gap:6px;">
            <div style="width:40px;height:40px;border-radius:50%;background:conic-gradient({score_color} {report.config_health_score}%, #1e293b 0%);display:flex;align-items:center;justify-content:center;">
                <div style="width:32px;height:32px;border-radius:50%;background:#0f172a;display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:700;color:{score_color};">{report.config_health_score}</div>
            </div>
        </div>
    </div>
    <div style="font-size:11px;color:#64748b;margin:0 0 10px 0;line-height:1.5;">
        Each finding represents tokens wasted <strong>every turn</strong> — duplicated boilerplate, stale references, cache misses. Streamlining topics removes redundant instructions, so the LLM processes less noise per request. At 50+ turns/day, waste compounds fast.
    </div>
    {findings_html}
    {upsell}
</div>"""

    return html
