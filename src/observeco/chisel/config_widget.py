#!/usr/bin/env python3
"""Config hygiene dashboard widget — Pro-locked embedded view.

Generates an HTML card for the ObserveCo dashboard showing config health score,
findings, and one-click fix. Pro-gated.

Called as an API endpoint (HTMX) or CLI report.
"""

import time
from pathlib import Path
from typing import Optional

from observeco.chisel.config_scanner import scan_config

LAST_SCAN_PATH = Path(__file__).resolve().parent.parent / '.config_last_scan'

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
        report = scan_config()

    if not report.findings:
        return (
            '<div id="config-health-widget" style="background:#0f172a;border:1px solid #1e293b;border-radius:12px;padding:16px;margin:8px 0;">'
            '<div style="display:flex;align-items:center;gap:8px;">\n'
            '    <span style="font-size:14px;">✅</span>\n'
            '    <span style="font-size:14px;font-weight:600;color:#22c55e;">Config Health: All Clear</span>\n'
            '</div>\n'
            '<div style="font-size:11px;color:#64748b;margin-top:6px;">No configuration issues detected. Config is optimized.</div>\n'
            '</div>'
        )

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
        if LAST_SCAN_PATH.exists():
            last_scan = LAST_SCAN_PATH.read_text().strip()[-8:]  # HH:MM:SS -> HH:MM
            try:
                from datetime import datetime
                last_scan = datetime.fromisoformat(last_scan).strftime('%H:%M')
            except (ValueError, OSError):
                last_scan = time.strftime('%H:%M', time.localtime())
        else:
            last_scan = 'Never'
        upsell = (
            '<div style="display:flex;align-items:center;gap:8px;padding:8px 12px;background:#0f172a;border-radius:8px;margin-top:8px;font-size:11px;color:#94a3b8;">\n'
            '    <span>\U0001f504 Scans daily</span>\n'
            '    <span style="flex:1;"></span>\n'
            '    <span>Last scan: %s</span>\n'
            '</div>'
        ) % last_scan

    # Fix All button (Pro only)
    fix_all_btn = ""
    if is_pro and any(f.auto_fixable for f in sorted_findings):
        fix_all_btn = (
            '<div style="margin-top:10px;">\n'
            '    <button id="fix-all-config-btn" onclick="fixConfigHygiene()" '
            'style="background:#6366f1;border:none;color:white;border-radius:6px;padding:6px 16px;font-size:12px;cursor:pointer;width:100%;">\n'
            '        \u26a1 Fix All Auto-Fixable Issues\n'
            '    </button>\n'
            '    <div id="fix-config-status" style="font-size:11px;color:#64748b;margin-top:4px;display:none;"></div>\n'
            '</div>'
        )

    html = (
        '<script>\n'
        'function fixConfigHygiene(checkType) {\n'
        '    const statusEl = document.getElementById("fix-config-status");\n'
        '    if (statusEl) { statusEl.style.display = "block"; statusEl.textContent = "Fixing..."; statusEl.style.color = "#94a3b8"; }\n'
        '    fetch("/api/config-hygiene/fix", { method: "POST", headers: {"Content-Type": "application/json", "X-ObserveCo-Token": window.__OBSERVECO_TOKEN || ""}, body: JSON.stringify({check: checkType || "all"}) })\n'
        '        .then(r => r.json())\n'
        '        .then(data => {\n'
        '            if (data.error) {\n'
        '                if (statusEl) { statusEl.textContent = data.error; statusEl.style.color = "#ef4444"; }\n'
        '                return;\n'
        '            }\n'
        '            const fixed = data.fixed || [];\n'
        '            const failed = data.failed || [];\n'
        '            let msg = fixed.length > 0 ? "Fixed: " + fixed.join(", ") : "Nothing to fix";\n'
        '            if (failed.length > 0) msg += " | Failed: " + failed.join(", ");\n'
        '            if (statusEl) { statusEl.textContent = msg + " — refreshing..."; statusEl.style.color = "#22c55e"; }\n'
        '            // Reload the widget after a short delay\n'
        '            setTimeout(() => {\n'
        '                const target = document.getElementById("configHealthCard");\n'
        '                if (target) { htmx.ajax("GET", "/api/config-health", {target: target, swap: "innerHTML"}); }\n'
        '            }, 1500);\n'
        '        })\n'
        '        .catch(err => { if (statusEl) { statusEl.textContent = "Error: " + err; statusEl.style.color = "#ef4444"; } });\n'
        '}\n'
        '</script>\n'
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
        '    %s\n'
        '</div>'
    ) % (score_color, report.config_health_score, score_color, report.config_health_score, findings_html, fix_all_btn, upsell)

    return html
