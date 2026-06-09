"""Independent Audit: P1-1 Crash Log Analysis.

Tests all layers of crash classification, logging, UI, and heal integration.
"""
import subprocess
import sys

checks = []
def check(name, ok, detail=''):
    checks.append((name, ok, detail))
    sym = 'PASS' if ok else 'FAIL'
    print(f'  [{sym}] {name}')
    if not ok and detail:
        print(f'         {detail}')

print('='*60)
print('INDEPENDENT AUDIT: P1-1 Crash Log Analysis')
print('='*60)
print()

WORK = '/Users/seanfzc/observeco'

# 1. classify_restart classifications
r1 = subprocess.run(
    ['python3', '-c', 'from observeco.pulse.check import classify_restart; r,s,e = classify_restart("test_h", exit_code=0); print(r)'],
    cwd=WORK, capture_output=True, text=True, timeout=15
)
check('1a. classify_restart(exit_code=0) -> healthy',
      r1.returncode == 0 and 'healthy' in r1.stdout.strip())

r2 = subprocess.run(
    ['python3', '-c', 'from observeco.pulse.check import classify_restart; r,s,e = classify_restart("test_t", "FileNotFoundError with .stat()"); print(r)'],
    cwd=WORK, capture_output=True, text=True, timeout=15
)
check('1b. classify_restart(FileNotFoundError+.stat()) -> toctou',
      r2.returncode == 0 and 'toctou' in r2.stdout.strip())

r3 = subprocess.run(
    ['python3', '-c', 'from observeco.pulse.check import classify_restart; r,s,e = classify_restart("test_o", "OutOfMemoryError"); print(r)'],
    cwd=WORK, capture_output=True, text=True, timeout=15
)
check('1c. classify_restart(OOM) -> crash',
      r3.returncode == 0 and 'crash' in r3.stdout.strip())

# 2. DB layer
r4 = subprocess.run(
    ['python3', '-c', '''from observeco.db import Database; d=Database(); d.log_restart("audit_p1","healthy",5); r=d.get_recent_restarts("audit_p1",1); print(len(r), r[0]["restart_type"])'''],
    cwd=WORK, capture_output=True, text=True, timeout=15
)
check('2a. log_restart + get_recent_restarts (wired)',
      r4.returncode == 0 and 'healthy' in r4.stdout)

r5 = subprocess.run(
    ['python3', '-c', 'from observeco.db import Database; d=Database(); s=d.get_restart_summary(); print(type(s).__name__, len(s))'],
    cwd=WORK, capture_output=True, text=True, timeout=15
)
check('2b. get_restart_summary (returns dict)',
      r5.returncode == 0 and 'dict' in r5.stdout)

# 3. Dashboard endpoint (check server is running)
TOKEN = None
try:
    # Get token from CLI
    tr = subprocess.run(
        ['observeco', 'dashboard', '--show-token'],
        capture_output=True, text=True, timeout=10
    )
    for line in tr.stdout.split('\n'):
        if 'Dashboard access token:' in line:
            TOKEN = line.split(':')[1].strip()
except Exception:
    pass

import http.client

try:
    conn = http.client.HTTPConnection('localhost', 9130, timeout=5)
    headers = {'X-ObserveCo-Token': TOKEN} if TOKEN else {}
    conn.request('GET', '/api/restart-quality', headers=headers)
    resp = conn.getresponse()
    body = resp.read().decode()
    conn.close()
    check('3a. /api/restart-quality endpoint (200 + HTML)',
          resp.status == 200 and ('restart-quality-tab' in body or 'restart-fleet' in body or 'No restart' in body))
    check('3b. Fleet summary or empty state renders',
          'restart' in body.lower() and ('restart-fleet' in body or 'legend' in body))
except Exception as e:
    check('3a. /api/restart-quality endpoint', False, str(e))
    check('3b. Fleet summary renders', False, str(e))

# 4. index.html tab and CSS
try:
    with open(f'{WORK}/src/observeco/dashboard/templates/index.html') as f:
        idx = f.read()
    check('4a. index.html has Restarts tab button',
          "switchTab('restarts'" in idx or 'switchTab(&#39;restarts&#39;' in idx)
    check('4b. tabRestarts content div exists',
          'id="tabRestarts"' in idx)
    check('4c. Restart quality CSS classes present',
          'restart-fleet-grid' in idx and 'restart-timeline-row' in idx)
    check('4d. htmx loads restart quality on tab load',
          'hx-get="/api/restart-quality"' in idx)
except Exception as e:
    check('4a. index.html', False, str(e))
    check('4b. tabRestarts', False)
    check('4c. CSS', False)
    check('4d. htmx', False)

# 5. heal TOCTOU integration
try:
    with open(f'{WORK}/src/observeco/heal/__init__.py') as f:
        heal_text = f.read()
    check('5a. heal _diagnose_agent checks restart_log for TOCTOU',
          'get_recent_restarts' in heal_text and 'toctou_count' in heal_text)
    check('5b. heal has toctou_loop diagnosis',
          'toctou_loop' in heal_text and 'code_fix' in heal_text)
except Exception as e:
    check('5a. heal TOCTOU', False, str(e))
    check('5b. heal diagnosis', False)

# 6. Circuit breaker excludes TOCTOU
try:
    with open(f'{WORK}/src/observeco/pulse/check.py') as f:
        pulse_text = f.read()
    check('6a. Circuit only records crash-type failures',
          'rtype == "crash"' in pulse_text and 'reset_breaker' in pulse_text)
except Exception as e:
    check('6a. Circuit TOCTOU exclusion', False, str(e))

print()
passed = sum(1 for _, ok, _ in checks if ok)
total = len(checks)
print(f'= Results: {passed}/{total} PASSED {"✅" if passed == total else "❌ SOME FAILED"} =')
sys.exit(0 if passed == total else 1)
