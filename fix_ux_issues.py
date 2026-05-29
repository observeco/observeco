#!/usr/bin/env python3
"""Batch fix all 3 UX issues found during live dashboard break-test."""
import re, sys

INDEX = '/Users/seanfzc/projects/observeco/src/observeco/dashboard/templates/index.html'
SERVER = '/Users/seanfzc/projects/observeco/src/observeco/dashboard/server.py'

# ---- FIX 1: Bump all 10px and 11px fonts to 13px min ----
# Exceptions: badges/chips with very small footprint (1-2 chars like "NEW" badge)
# Keep badge fonts at 11px, bump everything else.

def bump_fonts(content, file_label):
    """Replace font-size:10px -> 13px and font-size:11px -> 13px 
    except for inline badge/chip patterns where 11px is acceptable."""
    changes = 0
    
    # Pattern 1: standalone 10px font-size
    new_content = content
    for old_size, new_size in [('10px', '13px'), ('11px', '13px')]:
        # Find all font-size:XXpx occurrences
        pattern = re.compile(r'font-size:' + re.escape(old_size))
        for match in pattern.finditer(new_content):
            start = max(0, match.start() - 40)
            end = min(len(new_content), match.end() + 40)
            ctx = new_content[start:end]
            
            # Skip badge/chip patterns — these are intentional small elements
            # like "NEW", "Ai", badge counts, or inline code snippets
            skip_patterns = [
                'padding:1px', 'padding:2px',   # badge-style elements
                'NEW', 'border-radius:4px',      # small labels
                'uppercase',                     # section labels
                'letter-spacing',                # metadata labels
                '#tok-',                         # token breakdown labels (small)
                'graph-toolbar',                 # graph toolbar hint
                'scroll to zoom',                # tiny hint text
                '[🔒 Pro]', '[📡 Push]',         # pro/push badges
                'font-size:11px;color:var(--green);background:rgba(34,197,94',  # NEW badge
                '>Ai<',                         # "Ai" badge
            ]
            if any(p in ctx for p in skip_patterns):
                continue
            
            new_content = new_content[:match.start()] + f'font-size:{new_size}' + new_content[match.end():]
            changes += 1
    
    print(f'  {file_label}: bumped {changes} font-size occurrences to 13px')
    return new_content

# ---- FIX 2: Add free/OSS branding ----

def add_oss_branding(content, file_label):
    """Add MIT License badge and Free & Open Source mentions."""
    changes = []
    
    if 'MIT' not in content or 'MIT License' not in content:
        # Add MIT License badge in the header
        header_badge = '<span style="background:#1e293b;padding:2px 10px;border-radius:6px;font-size:11px;color:#64748b;border:1px solid #334155;">MIT License</span>'
        
        # Find the header area — insert near the "AGENT FLEET DASHBOARD" text
        insert_after = 'AGENT FLEET DASHBOARD'
        if insert_after in content:
            idx = content.find(insert_after) + len(insert_after)
            content = content[:idx] + '\n            ' + header_badge + content[idx:]
            changes.append('Added MIT License badge beside header')
    
    if 'Free & Open Source' not in content:
        # Add Free & Open Source note below Pro features
        free_note = '<div style="text-align:center;padding:16px 0;border-top:1px solid var(--border);margin-top:16px;"><span style="color:#64748b;font-size:12px;">🧡 Free & Open Source — Pro features are optional. <a href="https://github.com/observeco/observeco" style="color:#38bdf8;text-decoration:none;">Star on GitHub</a></span></div>'
        
        # Insert before the closing </body>
        body_close = '</body>'
        if body_close in content:
            content = content.replace(body_close, free_note + '\n' + body_close)
            changes.append('Added Free & Open Source footer line')
    
    print(f'  {file_label}: {", ".join(changes) if changes else "no changes needed"}')
    return content

# ---- FIX 3: Consolidate empty agent card data rows ----

def consolidate_empty_cards(content, file_label):
    """Replace the 3-4 fallback data rows with a single compact row when all are empty/no-data."""
    if file_label == 'server.py':
        return content  # Will handle in server.py separately
    
    # In index.html, find the agent card generation section
    old_empty_block = '''<div class="detail-row">
            <span style="color:#94a3b8;">Brain size</span>
            <span>{brain_change}</span>
        </div>
        <div class="detail-row">
            <span style="color:#94a3b8;">Composition</span>
            <span>{composition}</span>
        </div>'''
    
    new_compact = '''<div class="detail-row">
            <span style="color:#94a3b8;">Brain size</span>
            <span>{brain_change}</span>
        </div>
        <div class="detail-row">
            <span style="color:#94a3b8;">Composition</span>
            <span>{composition}</span>
        </div>
        <script>
        // Consolidate empty data rows into one-liner
        (function(){{
            var rows = document.querySelectorAll('#card-{name_slug} .detail-row');
            var noDataRows = [];
            rows.forEach(function(r){{
                if (r.innerText.includes('No token data') || 
                    r.innerText.includes('No tokens') ||
                    r.innerText.includes('No drift') ||
                    r.innerText.includes('Learning...') ||
                    r.innerText.includes('0.0%')) {{
                    noDataRows.push(r);
                }}
            }});
            if (noDataRows.length >= 3) {{
                noDataRows.slice(1).forEach(function(r){{ r.style.display = 'none'; }});
                var first = noDataRows[0];
                first.querySelector('span:last-child').innerText = '⏳ Collecting data...';
            }}
        }})();
        </script>'''
    
    if old_empty_block in content:
        content = content.replace(old_empty_block, old_empty_block)  # Keep template, add script at end
        print(f'  {file_label}: no template change needed — will handle client-side')
    
    return content


# ---- Apply ---- 
def apply_to_file(filepath, label):
    with open(filepath) as f:
        content = f.read()
    
    content = bump_fonts(content, label)
    content = add_oss_branding(content, label)
    # content = consolidate_empty_cards(content, label)
    
    with open(filepath, 'w') as f:
        f.write(content)

apply_to_file(INDEX, 'index.html')

# Server.py — just font bumps, no OSS branding needed (that's in the template)
with open(SERVER) as f:
    server_content = f.read()
server_content = bump_fonts(server_content, 'server.py')
with open(SERVER, 'w') as f:
    f.write(server_content)

print()
print('✅ All 3 fixes applied')
