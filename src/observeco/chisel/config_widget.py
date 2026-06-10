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

    Free: shows health score + findings (diagnostic only)
    Pro: shows health score + findings + one-click Fix buttons + daily scan status

    Returns raw HTML for HTMX insertion. Empty string if no findings.
    """
    from observeco import license as lic
    is_pro = lic.require_pro()

    if hermes_home:
        report = scan_config(Path(hermes_home) / "config.yaml")
    else:
        report = scan_config(CONFIG_PATH)

    if not report.findings:
        return ""

    # Sort findings: critical (25) -> warning (10) -> info (2), then by waste descending
    severity_order = {"critical": 0, "warning": 1, "info": 2}
    sorted_findings = sorted(
        report.findings,
        key=lambda f: (severity_order.get(f.severity, 3), -f.estimated_waste_tok),
    )

    # Build findings list (no cap -- page scrolls naturally)
    # Pro users see Fix buttons (auto-fixable) or manual hints (non-fixable)
    findings_html = ""
    for i, f in enumerate(sorted_findings):
        icon = {"critical": "\U0001f534", "warning": "\U0001f7e1", "info": "\u2139\ufe0f"}.get(f.severity, "?")
        action = ""
        if f.auto_fixable and is_pro:
            btn = '<button onclick="fixConfigHygiene(\'%s\')" style="background:transparent;border:1px solid #6366f1;color:#a5b4fc;border-radius:6px;padding:2px 10px;font-size:11px;cursor:pointer;margin-left:8px;">Fix</button>' % f.check
            action = btn
        elif not f.auto_fixable and is_pro:
            hint_map = {
                "duplicate_prompts": "Consolidate into shared_prompt",
                "stale_references": "Update path in config.yaml",
                "low_cache_ttl": "Raise TTL in config.yaml",
                "orphaned_agents": "Remove agent ref from prompt",
            }
            hint = hint_map.get(f.check, "Manual fix")
            action = ' <span style="color:#64748b;font-size:10px;cursor:default;">%s</span>' % hint
        findings_html += (
            '<div style="display:flex;align-items:flex-start;gap:8px;padding:6px 0;border-bottom:1px solid #1e293b;font-size:12px;line-height:1.4;">\n'
            '    <div style="flex-shrink:0;">%s</div>\n'
            '    <div>\n'
            '        <div style="color:#e2e8f0;">%s</div>\n'
            '        <div style="color:#94a3b8;font-size:11px;margin-top:2px;">~%d tok/session%s</div>\n'
            '    </div>\n'
            '</div>'
        ) % (icon, f.description[:100], f.estimated_waste_tok, action)

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
        upsell = (
            '<div style="display:flex;align-items:center;gap:8px;padding:8px 12px;background:#1e1b4b;border-radius:8px;margin-top:8px;font-size:12px;">\n'
            '    <span style="font-size:16px;">\U0001f512</span>\n'
            '    <span style="color:#94a3b8;flex:1;">One-click Fix \u2014 extract duplicates to system_prompt, raise TTL, clean stale refs \u2014 saves ~%dK tok/session</span>\n'
            '    <button onclick="showBrainPro()" style="background:#6366f1;border:none;color:white;border-radius:6px;padding:4px 14px;font-size:12px;cursor:pointer;">Pro \u2192</button>\n'
            '</div>'
        ) % waste_k
    if is_pro:
        last_scan = time.strftime("%H:%M", time.localtime())
        upsell = (
            '<div style="display:flex;align-items:center;gap:8px;padding:8px 12px;background:#0f172a;border-radius:8px;margin-top:8px;font-size:11px;color:#94a3b8;">\n'
            '    <span>\U0001f504 Scans daily</span>\n'
            '    <span style="flex:1;"></span>\n'
            '    <span>Last scan: %s</span>\n'
            '</div>'
        ) % last_scan

    html = (
        '<div id="config-health-widget" style="background:#0f172a;border:1px solid #1e293b;border-radius:12px;padding:16px;margin:8px 0;">\n'
        '    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:4px;">\n'
        '        <div style="display:flex;align-items:center;gap:8px;">\n'
        '            <span style="font-size:14px;">\u2699\ufe0f</span>\n'
        '            <span style="font-size:14px;font-weight:600;color:#e2e8f0;">Config Health</span>\n'
        '        </div>\n'
        '        <div style="display:flex;align-items:center;gap:6px;">\n'
        '            <div style="width:40px;height:40px;border-radius:50%%;background:conic-gradient(%s %d%%, #1e293b 0%%);display:flex;align-items:center;justify-content:center;">\n'
        '                <div style="width:32px;height:32px;border-radius:50%%;background:#0f172a;display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:700;color:%s;">%d</div>\n'
        '            </div>\n'
        '        </div>\n'
        '    </div>\n'
        '    <div style="font-size:11px;color:#64748b;margin:0 0 10px 0;line-height:1.5;">\n'
        '        Each finding represents tokens wasted <strong>every turn</strong> \u2014 duplicated boilerplate, stale references, cache misses. Streamlining topics removes redundant instructions, so the LLM processes less noise per request. At 50+ turns/day, waste compounds fast.\n'
        '    </div>\n'
        '    %s\n'
        '    %s\n'
        '</div>'
    ) % (score_color, report.config_health_score, score_color, report.config_health_score, findings_html, upsell)

    return html