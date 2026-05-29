#!/usr/bin/env python3
"""ObserveCo Dashboard API-level audit — run after a fresh server start."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
from fastapi.testclient import TestClient
from observeco.dashboard.server import app
import re
from collections import Counter

client = TestClient(app)

print('=== TESTCLIENT BASELINE AUDIT ===')
print()

# 1. Every endpoint
endpoints = {
    '/': 'Dashboard root',
    '/api/agents': 'Agent cards',
    '/api/alerts': 'Alert feed',
    '/api/errors': 'Error timeline',
    '/api/fleet-summary': 'Fleet bar',
    '/api/phase': 'Phase indicator',
    '/api/error-state': 'Error state banners',
    '/api/delay-banner': 'Delay notice',
    '/api/heal-log': 'Heal log',
    '/api/restart-quality': 'Restart quality',
    '/api/glossary': 'Glossary entries',
    '/api/pathway-graph': 'Pathway graph',
    '/api/pathway-scan': 'Pathway scan',
    '/pathway': 'Pathway page',
}

endpoint_errors = []
for path, name in endpoints.items():
    try:
        r = client.get(path, follow_redirects=False)
        issues = []
        if r.status_code >= 400:
            issues.append(f'HTTP {r.status_code}')
        if 'Traceback' in r.text or 'Internal Server Error' in r.text:
            issues.append('TRACEBACK')
        
        body_no_scripts = re.sub(r'<script[^>]*>.*?</script>', '', r.text, flags=re.DOTALL)
        none_in_html = len(re.findall(r'>\s*None\s*<', body_no_scripts))
        null_in_html = len(re.findall(r'>\s*null\s*<', body_no_scripts))
        if none_in_html > 0:
            issues.append(f'{none_in_html}x None')
        if null_in_html > 0:
            issues.append(f'{null_in_html}x null')
        
        status = ' | '.join(issues) if issues else 'OK'
        print(f'[{status:45s}] {path:25s} ({r.status_code}) {len(r.text):5d}b')
        if status != 'OK':
            endpoint_errors.append((path, status))
    except Exception as e:
        endpoint_errors.append((path, str(e)[:40]))
        print(f'[ERROR: {str(e)[:40]:40s}] {path}')

print()
if endpoint_errors:
    print(f'❌ {len(endpoint_errors)} endpoints with issues:')
    for path, issue in endpoint_errors:
        print(f'  {path}: {issue}')
else:
    print('✅ All endpoints clean (200 + no tracebacks)')

print()
print('=== ENTITY COUNT SANITY ===')
r = client.get('/api/agents')
cards = set(re.findall(r'id="(card-[^"]+)"', r.text))
sections = set(re.findall(r'id="(section-[^"]+)"', r.text))
print(f'  Agent cards: {len(cards)}')
print(f'  Sections: {sections}')

# Framework bias
hermes = len(re.findall(r'Hermes|section-hermes|hermes-', r.text))
openclaw = len(re.findall(r'OpenClaw|section-openclaw|openclaw-', r.text))
other_section = 'section-other' in r.text
print(f'  Hermes refs: {hermes}  OpenClaw refs: {openclaw}  Has "Other" section: {other_section}')
if other_section:
    for m in re.finditer(r'<div[^>]*id="section-other"[^>]*>.*?</div>', r.text, re.DOTALL):
        print(f'    "Other" context: {m.group()[:150]}')

print()
print('=== FONT SIZE CHECK (11px problem) ===')
r_main = client.get('/')
body_no_scripts = re.sub(r'<script[^>]*>.*?</script>', '', r_main.text, flags=re.DOTALL)
font_sizes = re.findall(r'font-size:(\d+)px', body_no_scripts)
size_counts = Counter(int(s) for s in font_sizes)
small_sizes = {k: v for k, v in sorted(size_counts.items()) if k <= 11}
print(f'  All font size counts: {dict(sorted(size_counts.items()))}')
if small_sizes:
    print(f'  ⚠️  Sub-12px fonts found: {small_sizes}')
else:
    print(f'  ✅ No sub-12px fonts')

print()
print('=== SECTION STRUCTURE ===')
section_headers = re.findall(r'<div[^>]*class="section-header"[^>]*>.*?</div>', r_main.text, re.DOTALL)
print(f'  Collapsible sections: {len(section_headers)}')
for h in section_headers:
    clean = re.sub(r'<[^>]+>', ' ', h).strip()
    clean = re.sub(r'\s+', ' ', clean)
    print(f'    {clean[:80]}')

print()
print('=== PRO-TO-FREE BALANCE ===')
pro = len(re.findall(r'[Pp]ro\b', r_main.text))
free_oss = len(re.findall(r'[Ff]ree\b|open.source|OS\s*[Ll]icense|[Mm][Ii][Tt]\b', r_main.text))
print(f'  Pro: {pro}  Free/OSS: {free_oss}')
if pro > free_oss * 3 and free_oss > 0:
    print(f'  ⚠️  Heavy Pro bias: {pro}x Pro vs {free_oss}x free/OSS')
    
print()
print('DONE')
