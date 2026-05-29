#!/usr/bin/env python3
"""Quick verification script for ObserveCo dashboard fixes."""
import sys, os
sys.path.insert(0, os.path.expanduser('~/projects/observeco'))
from fastapi.testclient import TestClient
from observeco.dashboard.server import app
import re
from collections import Counter

client = TestClient(app)

print('=== FINAL VERIFICATION ===')
print()

# 1. Main page
r = client.get('/')
print(f'[/] HTTP {r.status_code}, {len(r.text)}b')

assert 'document.createElement' in r.text, 'htmx DOM fallback missing'
print('  ✅ htmx DOM append fallback')

assert 'document.write' not in r.text, 'document.write should be gone'
print('  ✅ No document.write')

assert 'MIT License' in r.text, 'MIT badge missing'
print('  ✅ MIT License badge')

assert 'Free & Open Source' in r.text, 'Free footer missing'
print('  ✅ Free & Open Source footer')

# 2. Agent cards
r2 = client.get('/api/agents')
print(f'\n[/api/agents] HTTP {r2.status_code}, {len(r2.text)}b')

assert '{brain_composition_html}' not in r2.text, 'Variable leaked into output'
print('  ✅ brain_composition_html properly evaluated')

cards = re.findall(r'id="card-([^"]+)"', r2.text)
print(f'  ✅ Agent cards: {len(cards)}')

# 3. Font size check
body = re.sub(r'<script[^>]*>.*?</script>', '', r2.text, flags=re.DOTALL)
sizes = Counter(int(s) for s in re.findall(r'font-size:(\d+)px', body))
sub11 = {k:v for k,v in sorted(sizes.items()) if k <= 11}
if sub11:
    print(f'  ⚠️  Sub-12px fonts remaining: {sub11}')
else:
    print('  ✅ All fonts >= 12px')

# 4. Consolidated rows
monitoring = len(re.findall(r'>Monitoring<', r2.text))
brain_size = len(re.findall(r'>Brain size<', r2.text))
if monitoring > 0:
    print(f'  ✅ {monitoring} consolidated Monitoring rows (empty agents)')
else:
    print(f'  All agents have full data: {brain_size} Brain size rows')

# 5. All endpoints
endpoints = ['/', '/api/alerts', '/api/errors', '/api/fleet-summary', '/api/phase',
             '/api/error-state', '/api/heal-log', '/api/restart-quality', '/api/glossary',
             '/api/agents', '/api/agent-detail/accelerator', '/api/pathway-graph']
failed = 0
for path in endpoints:
    r = client.get(path)
    if r.status_code >= 400 or 'Traceback' in r.text:
        failed += 1
        print(f'  ❌ {path} — HTTP {r.status_code}')
        
if failed == 0:
    print(f'  ✅ All {len(endpoints)} endpoints healthy')

print(f'\n{"="*40}')
print('ALL CHECKS PASSED' if failed == 0 else f'{failed} FAILURES')
