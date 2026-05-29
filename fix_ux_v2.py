#!/usr/bin/env python3
"""Re-apply all UX fixes that were lost in git revert + fix for ❓ emoji bug."""
import re, sys

INDEX = '/Users/seanfzc/projects/observeco/src/observeco/dashboard/templates/index.html'
SERVER = '/Users/seanfzc/projects/observeco/src/observeco/dashboard/server.py'

# ---- FIX A: htmx document.write -> DOM append ----
with open(INDEX) as f:
    index = f.read()

# The original had document.write in the htmx fallback
old_htmx = '<script src="/static/htmx.min.js"></script>\n    <script>if (!window.htmx) { document.write(\'<script src="https://unpkg.com/htmx.org@1.9.11/dist/htmx.min.js"><\\/script>\'); }</script>'

new_htmx = '<script src="/static/htmx.min.js" onerror="\n  if (!window.htmx) {\n    var s = document.createElement(\'script\');\n    s.src = \'https://unpkg.com/htmx.org@1.9.11/dist/htmx.min.js\';\n    document.head.appendChild(s);\n  }\n"></script>\n    <script>if (!window.htmx) {\n      var s = document.createElement(\'script\');\n      s.src = \'https://unpkg.com/htmx.org@1.9.11/dist/htmx.min.js\';\n      document.head.appendChild(s);\n    }</script>'

if old_htmx in index:
    index = index.replace(old_htmx, new_htmx)
    print('✅ htmx: replaced document.write with DOM append')
else:
    # Check if our fix is already in place
    if 'document.createElement' in index and 'htmx.org' in index:
        print('✅ htmx: fix already in place')
    else:
        print('⚠️ htmx: could not find old pattern, need manual check')

# ---- FIX B: MIT License badge ----
if 'MIT License' not in index:
    mit_badge = '<span style="background:#1e293b;padding:2px 10px;border-radius:6px;font-size:11px;color:#64748b;border:1px solid #334155;">MIT License</span>'
    insert_after = 'AGENT FLEET DASHBOARD'
    if insert_after in index:
        idx = index.find(insert_after) + len(insert_after)
        index = index[:idx] + '\n            ' + mit_badge + index[idx:]
        print('✅ OSS: added MIT License badge')
    else:
        print('⚠️ OSS: could not find insertion point')

if 'Free & Open Source' not in index:
    footer = '<div style="text-align:center;padding:16px 0;border-top:1px solid var(--border);margin-top:16px;"><span style="color:#64748b;font-size:12px;">🧡 Free & Open Source — Pro features are optional. <a href="https://github.com/observeco/observeco" style="color:#38bdf8;text-decoration:none;">Star on GitHub</a></span></div>'
    body_close = '</body>'
    if body_close in index:
        index = index.replace(body_close, footer + '\n' + body_close)
        print('✅ OSS: added Free & Open Source footer')
    else:
        print('⚠️ OSS: could not find </body>')

with open(INDEX, 'w') as f:
    f.write(index)

# ---- FIX C: Font-size bumps in server.py ----
with open(SERVER) as f:
    server = f.read()

# Replace font-size:10px -> 13px EXCEPT badge patterns
changes_10 = 0
changes_11 = 0

for old_size, new_size in [('10px', '13px'), ('11px', '13px')]:
    pattern = re.compile(r'font-size:' + re.escape(old_size))
    matches = list(pattern.finditer(server))
    for m in reversed(matches):  # Reverse to maintain indices
        ctx_start = max(0, m.start() - 60)
        ctx_end = min(len(server), m.end() + 60)
        ctx = server[ctx_start:ctx_end]
        
        # Skip badge/chip patterns
        skip = False
        for marker in ['padding:1px', 'padding:2px', 'NEW', 'border-radius:4px;', 
                        'uppercase', 'letter-spacing', 'graph-toolbar',
                        'scroll to zoom', 'font-size:11px;color:var(--green)',
                        '>Ai<', 'font-size:11px;color:{fw_color}']:
            if marker in ctx:
                skip = True
                break
        if skip:
            continue
        
        server = server[:m.start()] + f'font-size:{new_size}' + server[m.end():]
        if old_size == '10px':
            changes_10 += 1
        else:
            changes_11 += 1

print(f'✅ server.py: bumped {changes_10}x 10px, {changes_11}x 11px to 13px')

# ---- FIX D: Consolidate empty Brain+Composition rows ----
# Find and replace the 5 Brain size + Composition row pairs with {brain_composition_html}
# First, find the card generation area marker
marker = '            # Build metric row labels'
new_code = '''            # Build metric row labels
            status_label = {"alive": "\U0001f7e2 Healthy", "dead": "\U0001f534 Dead", "error": "\U0001f7e1 Error"}.get(status, "\u26ab Unknown")
            guard_label = "\U0001f534 Stopped (failed 3x)" if tripped else "\u2705 Guard OK"
            error_row_label = f"\u26a0\ufe0f {recent_error_count} error{'s' if recent_error_count != 1 else ''} in 24h" if recent_error_count > 0 else "- No errors"

            # Brain size / drift
            has_drift_data = bool(drift_sparkline) and drift_data
            drift_label = "\U0001f4c8 Learning..." if not has_drift_data else f"\U0001f4ca {avg_drift:+.1f}%" if drift_data else "\U0001f4ca - Drift stable"
            has_token_data = bool(trim_data)

            # Consolidate empty Brain+Composition rows into one
            if not has_drift_data and not has_token_data:
                # Both empty: single compact row
                brain_composition_html = f"""<div class="metric-row" onclick="loadAgentDetail('{name}')"
                 style="display:flex;justify-content:space-between;align-items:center;padding:6px 8px;border-radius:6px;cursor:pointer;margin-bottom:2px;transition:background 0.15s;"
                 onmouseenter="this.style.background='#1e293b'" onmouseleave="this.style.background='transparent'"
                 title="Click for monitoring details">
                <span style="color:#64748b;font-size:13px;">Monitoring</span>
                <span style="display:flex;align-items:center;gap:6px;">
                    <span style="color:#6b7280;font-size:13px;">\u23f3 No data yet \u2014 run 'observeco watch'</span>
                    <span class="see-details" style="color:#38bdf8;font-size:13px;opacity:0;">See details \u203a</span>
                </span>
            </div>"""
            else:
                brain_composition_html = f"""<div class="metric-row" onclick="loadAgentDetail('{name}')"
                 style="display:flex;justify-content:space-between;align-items:center;padding:6px 8px;border-radius:6px;cursor:pointer;margin-bottom:2px;transition:background 0.15s;"
                 onmouseenter="this.style.background='#1e293b'" onmouseleave="this.style.background='transparent'"
                 title="Click for Brain size / drift details">
                <span style="color:#64748b;font-size:13px;">Brain size</span>
                <span style="display:flex;align-items:center;gap:6px;">
                    <span style="color:#e2e8f0;font-size:13px;">{drift_label}</span>
                    <span class="see-details" style="color:#38bdf8;font-size:13px;opacity:0;">See details \u203a</span>
                </span>
            </div>
            <div class="metric-row" onclick="loadAgentDetail('{name}')"
                 style="display:flex;justify-content:space-between;align-items:center;padding:6px 8px;border-radius:6px;cursor:pointer;margin-bottom:2px;transition:background 0.15s;"
                 onmouseenter="this.style.background='#1e293b'" onmouseleave="this.style.background='transparent'"
                 title="Click for Token composition details">
                <span style="color:#64748b;font-size:13px;">Composition</span>
                <span style="display:flex;align-items:center;gap:6px;">
                        {token_bar_html if trim_data else '<span style="color:#6b7280;font-size:13px;">No token data</span>'}
                    <span class="see-details" style="color:#38bdf8;font-size:13px;opacity:0;">See details \u203a</span>
                </span>
            </div>"""

            cards_html.append(f"""<div class="agent-card" id="card-{name}" data-agent="{name}"'''

old_code = '''            # Build metric row labels
            status_label = {"alive": "\U0001f7e2 Healthy", "dead": "\U0001f534 Dead", "error": "\U0001f7e1 Error"}.get(status, "\u26ab Unknown")
            guard_label = "\U0001f534 Stopped (failed 3x)" if tripped else "\u2705 Guard OK"
            error_row_label = f"\u26a0\ufe0f {recent_error_count} error{'s' if recent_error_count != 1 else ''} in 24h" if recent_error_count > 0 else "- No errors"

            # Brain size / drift
            drift_label = "\U0001f4c8 Learning..." if not drift_sparkline else f"\U0001f4ca {avg_drift:+.1f}%" if drift_data else "\U0001f4ca - Drift stable"

            cards_html.append(f"""<div class="agent-card" id="card-{name}" data-agent="{name}"'''

if old_code in server:
    server = server.replace(old_code, new_code)
    print('✅ Cards: consolidated Brain+Composition rows into brain_composition_html')
else:
    print('⚠️ Cards: could not find exact marker pattern — checking for partial match')
    if 'brain_composition_html' in server:
        print('   (brain_composition_html already present — fix from earlier is intact)')

with open(SERVER, 'w') as f:
    f.write(server)

# ---- FIX E: Replace the 5 Brain size + Composition literal row pairs ----
# After the fix above, the old inline rows still exist in the card templates themselves.
# Find and replace them with {brain_composition_html}

with open(SERVER) as f:
    server = f.read()

# Find Brain size blocks inside cards_html.append — these are the literal rows
# that are now redundant
# Search for the literal pattern starting with "title="Click for Error details"" followed by the Brain+Comp rows
old_brain_comp_pair = '''                </span>
            </div>
            <div class="metric-row" onclick="loadAgentDetail(\'{name}\')"
                 style="display:flex;justify-content:space-between;align-items:center;padding:6px 8px;border-radius:6px;cursor:pointer;margin-bottom:2px;transition:background 0.15s;"
                 onmouseenter="this.style.background=\'#1e293b\'" onmouseleave="this.style.background=\'transparent\'"
                 title="Click for Brain size / drift details">
                <span style="color:#64748b;font-size:13px;">Brain size</span>
                <span style="display:flex;align-items:center;gap:6px;">
                    <span style="color:#e2e8f0;font-size:13px;">{drift_label}</span>
                    <span class="see-details" style="color:#38bdf8;font-size:13px;opacity:0;">See details \u203a</span>
                </span>
            </div>
            <div class="metric-row" onclick="loadAgentDetail(\'{name}\')"
                 style="display:flex;justify-content:space-between;align-items:center;padding:6px 8px;border-radius:6px;cursor:pointer;margin-bottom:2px;transition:background 0.15s;"
                 onmouseenter="this.style.background=\'#1e293b\'" onmouseleave="this.style.background=\'transparent\'"
                 title="Click for Token composition details">
                <span style="color:#64748b;font-size:13px;">Composition</span>
                <span style="display:flex;align-items:center;gap:6px;">
                        {token_bar_html if trim_data else \'<span style="color:#6b7280;font-size:13px;">No token data</span>\'}
                    <span class="see-details" style="color:#38bdf8;font-size:13px;opacity:0;">See details \u203a</span>
                </span>
            </div>'''

# Actually approach: just search for 'title=\"Click for Brain size' and check if those appear
# outside the new brain_composition_html definition
count_brain_size = server.count('title=\"Click for Brain size')
print(f'Brain size blocks remaining: {count_brain_size}')

if count_brain_size > 0:
    # The remaining blocks are inside the f-string card templates themselves.
    # Each f-string starts with cards_html.append(f"""... and has these blocks.
    # We need to replace them with {brain_composition_html}
    # These are in the f-string literal, so {name} is already used
    # Let's find the pattern: Error row -> Brain size row -> Composition row -> </div>\\n</div>
    # and replace the Brain+Comp pair with {brain_composition_html}
    
    # Find all occurrences of 'title=\"Click for Brain size' in f-string content
    # (i.e., NOT inside the brain_composition_html variable definition)
    # Strategy: replace everything between Error row's second </div> and the </div>\\n</div>\\n<div class="agent-detail"
    import re
    
    # Each card template ends one of these rows before agent-detail
    pattern = r'(title="Click for Brain size / drift details">[\s\S]*?</div>\s*</div>\s*<div class="agent-detail")'
    matches = list(re.finditer(pattern, server))
    print(f'Found {len(matches)} Brain+Composition blocks to replace')
    
    for m in reversed(matches):
        full_match = m.group(0)
        replacement = '{brain_composition_html}\n        </div>\n        <div class="agent-detail"'
        server = server[:m.start()] + replacement + server[m.end():]
    
    print(f'✅ Replaced {len(matches)} inline Brain+Comp blocks with {{brain_composition_html}}')

with open(SERVER, 'w') as f:
    f.write(server)

# ---- FINAL COMPILE CHECK ----
import py_compile
try:
    py_compile.compile(SERVER, doraise=True)
    print('\n✅ FINAL COMPILE: OK')
except py_compile.PyCompileError as e:
    print(f'\n❌ FINAL COMPILE: FAILED — {str(e).split(chr(10))[0]}')
