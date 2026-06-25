# Installation & Upgrade Test Playbook — The First-Run Lens

**Product:** ObserveCo
**Status:** Living — update as lessons accumulate
**Version:** 2.0 — 2026-06-19
**Version History:**
| Version | Date | What changed |
|---------|------|-------------|
| 1.0 | 2026-06-19 | Initial creation — 8 scenarios covering fresh install, upgrade, downgrade, and failure modes |
| 2.0 | 2026-06-19 | Independent review: fixed default port (8123→9119), fixed DB name (observeco.db→pulse.db), added 5 missing scenarios (port collision, OBSERVECO_HOME override, headless mode, old data migration, startup validation), added Expert Prompts for Hound, added Playbook Inventory cross-ref, added master-fidelity-gate.md Layer F cross-ref, added Lessons Learned entries, standardized format to match sibling playbooks |

**Source:** Beachhead readiness — Phase 0 removed all Sean-specific artifacts. The product must now survive a stranger's first `pip install observeco` on a machine that has never seen it. No playbook existed for this class of test.

**Relationship to other playbooks:** This playbook sits **downstream** of requirements-fidelity-playbook.md (spec hardening) and **upstream** of ux-testing-playbook.md (first-run UX). It catches the class of problem where the code is correct but the *installation experience* is broken — the product works on the developer's machine but fails on a clean install.

## Playbook Inventory

The full playbook system has 12 documents, organized by flow:

| Order | Playbook | Role |
|-------|----------|------|
| 1 | requirements-fidelity-playbook.md | Spec hardening (upstream gate) |
| 2 | spec-gated-workflow-playbook.md | 4-phase gated spec process (SPECIFY → PLAN → TASKS → IMPLEMENT) |
| 3 | coding-fidelity-playbook.md | Code matches spec |
| 4 | ui-testing-playbook.md | Visual consistency & design system integrity |
| 5 | ux-testing-playbook.md | Human experience lens |
| 6 | system-design-testing-playbook.md | Architecture & daemon lens |
| 7 | agent-governance-playbook.md | Session mastery for agents |
| 8 | **installation-test-playbook.md** | **Installation & upgrade testing (this document)** |
| 9 | orchestration-anti-patterns-playbook.md | Multi-agent governance patterns |
| 10 | security-stride-playbook.md | STRIDE threat model + OWASP LLM Top 10 |
| 11 | master-fidelity-gate.md | Integration gate (combines all playbooks) |
| 12 | playbook-evolution-meta.md | Self-improvement loop |

Refer to this inventory when the playbook system is referenced in other documents. Registered in master-fidelity-gate.md (Layer J) and playbook-evolution-meta.md (version table) on 2026-06-19.

---

## 1. Thesis

**The product works on the developer's machine. The product fails on the stranger's machine.**

Every installation failure in this project traces to one root: the developer tests against their own environment (Hermes installed, config populated, DB seeded, agents running) and never validates the *empty state* — a machine with no Hermes, no config, no DB, no agents, no API keys.

This document is not a deployment guide. It is an **installation testing process** — a repeatable way to catch the class of problem, not the instance.

| This playbook catches | Other playbooks catch |
|----------------------|----------------------|
| Does `pip install observeco` succeed? | Does the code match the spec? |
| Does `observeco dashboard` start on a clean machine? | Does the UI render correctly? |
| Does Hermes upgrade break ObserveCo? | Does the daemon survive a crash? |
| Does ObserveCo upgrade preserve data? | Are all states (empty, loading, error) described? |

---

## 2. The 13 Installation Scenarios

Every installation failure falls into one of these thirteen scenarios.

### Scenario 1: Fresh Install — No Hermes, No Config, No DB

**Pattern:** A user on a new Mac Mini runs `pip install observeco && observeco dashboard` for the first time. No Hermes agent is installed. No `~/.hermes/` directory exists. No `pulse.db` exists. No API keys are set.

**What must happen:**
- `pip install observeco` succeeds (all dependencies resolve)
- `observeco dashboard` starts on its default port (9119) without crashing
- Dashboard renders with empty state — no tracebacks, no "Internal Server Error"
- All panels show appropriate "no data" messages, not blank/white sections
- No Python tracebacks in terminal output
- No crash on first page load
- Dashboard is usable: navigation works, tabs switch, no infinite loading spinners

**What must NOT happen:**
- Crash with `FileNotFoundError: Hermes home not found`
- Crash with `sqlite3.OperationalError: no such table`
- Show Sean's agent names, calendar files, or fake plugins
- Show "0 agents" as a broken card (should be a friendly empty state)
- Hang on startup waiting for Hermes config that doesn't exist

**How to simulate in development:**
```bash
# Method A: Fresh Python venv (fastest, no Docker)
cd /tmp
python3 -m venv observeco-test
source observeco-test/bin/activate
# Verify no ~/.hermes/ exists
test -d ~/.hermes && echo "WARNING: Hermes is installed" || echo "Clean — no Hermes"
# Install from local source
pip install /Users/seanfzc/projects/observeco
observeco dashboard --port 9999
# Test in browser: http://localhost:9999
```

```bash
# Method B: Docker container (most isolated, recommended for final validation)
docker run -it --rm -p 9999:9119 \
  -v /Users/seanfzc/projects/observeco:/app \
  python:3.11-slim bash -c "
    pip install /app && \
    observeco dashboard --port 9119
  "
```

```bash
# Method C: macOS VM (most realistic, for pre-release validation)
# Use a tool like vagrant or tart to spin a clean macOS VM
# Then run the same pip install + observeco dashboard sequence
```

**Detection checklist:**
```
☐ pip install succeeds without errors
☐ observeco dashboard starts without crashing
☐ Dashboard loads in browser (HTTP 200)
☐ No tracebacks in terminal output
☐ All panels show empty states (not blank/white)
☐ Navigation works (tabs, links)
☐ No Sean-specific artifacts visible
☐ Dashboard process can be killed cleanly (Ctrl+C)
```

---

### Scenario 2: Fresh Install — Hermes Present, No ObserveCo

**Pattern:** User has Hermes running with agents. They run `pip install observeco && observeco dashboard` for the first time. Hermes is at `~/.hermes/` with profiles, config.yaml, and active agents.

**What must happen:**
- `observeco dashboard` starts and auto-discovers Hermes agents
- Agent cards render with real agent names (not Sean's)
- Pulse data shows "no data yet" (ObserveCo just started collecting)
- Token/cost panels show empty states
- Dashboard is fully navigable
- No crash from reading Hermes config.yaml

**What must NOT happen:**
- Crash because Hermes config.yaml has unexpected keys
- Show agents from a different user's profiles
- Overwrite or corrupt Hermes config.yaml
- Start collecting data before user explicitly enables it

**How to simulate:**
```bash
# Use the existing development environment (Hermes is already installed)
# Create a fresh venv to simulate "first install"
cd /tmp
python3 -m venv observeco-test
source observeco-test/bin/activate
pip install /Users/seanfzc/projects/observeco
# Verify Hermes is detected
python -c "from observeco.dirs import hermes_home; print('Hermes:', hermes_home())"
observeco dashboard --port 9998
```

**Detection checklist:**
```
☐ Hermes agents auto-discovered (correct names, no Sean artifacts)
☐ Agent cards render with status indicators
☐ Pulse/token panels show empty states
☐ No crash on startup
☐ Hermes config.yaml unchanged (check file modification time)
☐ Dashboard loads in <5 seconds
```

---

### Scenario 3: Hermes Upgrade — ObserveCo Running

**Pattern:** User has been running ObserveCo for weeks. Hermes releases a new version. User upgrades Hermes (e.g., `pip install --upgrade hermes-agent`). ObserveCo is still running during the upgrade.

**What must happen:**
- Hermes upgrade succeeds without ObserveCo interference
- ObserveCo continues running after Hermes upgrade (no crash)
- Agent discovery still works (new Hermes config format is parsed)
- If Hermes config.yaml format changed, ObserveCo adapts gracefully
- No data loss in pulse.db
- Dashboard continues to show real-time data

**What must NOT happen:**
- ObserveCo crashes because Hermes config.yaml has new/removed keys
- Agent list becomes empty after upgrade
- DB connection lost (Hermes upgrade shouldn't touch pulse.db)
- ObserveCo needs restart to pick up new Hermes config

**How to simulate:**
```bash
# 1. Start ObserveCo in background
observeco dashboard --port 9119 &
sleep 2

# 2. Simulate Hermes config format change
# Back up current config
cp ~/.hermes/config.yaml ~/.hermes/config.yaml.bak

# 3. Modify config to simulate new Hermes version format
# (Add a new section, rename a key, change a structure)
python3 -c "
import yaml
with open('$HOME/.hermes/config.yaml') as f:
    config = yaml.safe_load(f)
# Simulate Hermes v0.17 format change
config['providers'] = config.get('providers', {})
config['_version'] = '0.17.0'
config['new_section'] = {'experimental': True}
with open('$HOME/.hermes/config.yaml', 'w') as f:
    yaml.dump(config, f)
print('Simulated Hermes upgrade')
"

# 4. Check ObserveCo is still running
curl -s http://localhost:9119 | head -5

# 5. Restore original config
cp ~/.hermes/config.yaml.bak ~/.hermes/config.yaml

# 6. Kill background ObserveCo
kill %1 2>/dev/null
```

**Detection checklist:**
```
☐ ObserveCo does not crash during/after Hermes upgrade
☐ Agent list remains populated
☐ Dashboard continues to serve pages
☐ No errors in ObserveCo logs
☐ DB data intact (pulse history, token logs preserved)
```

---

### Scenario 4: ObserveCo Upgrade — Environment Unchanged

**Pattern:** User has ObserveCo v0.1.0 installed with data in `pulse.db`. They upgrade to v0.2.0 via `pip install --upgrade observeco`. The environment (Hermes, config, DB) stays the same.

**What must happen:**
- `pip install --upgrade observeco` succeeds
- DB migration runs automatically (or on first `observeco dashboard`)
- All existing data is preserved after migration
- New features appear (if any)
- Old features still work
- No "table already exists" or "no such column" errors
- Config file format is backward-compatible (or auto-migrated)

**What must NOT happen:**
- Data loss during migration
- Migration failure leaves DB in inconsistent state
- Old config keys cause crashes
- User needs to manually run migration commands
- Downgrade path is impossible (should be documented, not necessarily supported)

**How to simulate:**
```bash
# 1. Install old version
pip install /Users/seanfzc/projects/observeco  # current = "old" for this test

# 2. Start ObserveCo, let it create DB and collect some data
observeco dashboard --port 9119 &
sleep 3
# Generate some data
curl -s http://localhost:9119/api/agents > /dev/null
kill %1 2>/dev/null

# 3. Back up the DB
python3 -c "
from observeco.dirs import get_data_dir
import shutil
db_path = get_data_dir() / 'pulse.db'
bak_path = '/tmp/pulse.db.bak'
if db_path.exists():
    shutil.copy2(db_path, bak_path)
    print(f'Backed up {db_path} → {bak_path}')
else:
    print('No DB to back up')
"

# 4. Simulate upgrade by modifying schema version
# (In real test, you'd install the actual new version)
python3 -c "
import sqlite3
from observeco.dirs import get_data_dir
db_path = get_data_dir() / 'pulse.db'
if db_path.exists():
    conn = sqlite3.connect(str(db_path))
    cur = conn.execute('PRAGMA user_version')
    print('Current schema version:', cur.fetchone()[0])
    conn.close()
else:
    print('No DB found — will be created on first start')
"

# 5. Start ObserveCo again — migration should run
observeco dashboard --port 9119 &
sleep 3

# 6. Verify data preserved
python3 -c "
import sqlite3
from observeco.dirs import get_data_dir
db_path = get_data_dir() / 'pulse.db'
if db_path.exists():
    conn = sqlite3.connect(str(db_path))
    cur = conn.execute('PRAGMA user_version')
    print('Schema version after upgrade:', cur.fetchone()[0])
    # Check key tables still have data
    for table in ['agents', 'pulse_log', 'token_logs']:
        try:
            cur = conn.execute(f'SELECT COUNT(*) FROM {table}')
            print(f'{table}: {cur.fetchone()[0]} rows')
        except Exception as e:
            print(f'{table}: ERROR - {e}')
    conn.close()
"

kill %1 2>/dev/null
```

**Detection checklist:**
```
☐ pip install --upgrade succeeds
☐ DB migration runs without errors
☐ All pre-upgrade data is preserved
☐ Dashboard loads and shows historical data
☐ New features are available
☐ Old features still work
☐ No "table already exists" errors in logs
☐ Schema version is updated correctly
```

---

### Scenario 5: ObserveCo Downgrade — Newer DB Schema

**Pattern:** User upgraded to ObserveCo v0.2.0 (schema v3), then downgrades to v0.1.0 (schema v1) via `pip install observeco==0.1.0`. The DB has a newer schema than the code expects.

**What must happen:**
- Downgrade is detected gracefully
- Dashboard starts (doesn't crash on unknown schema)
- User is informed that the DB is from a newer version
- No data corruption
- Optionally: offer to roll back schema (if supported)

**What must NOT happen:**
- Crash with `sqlite3.OperationalError: no such table/column`
- Silent data loss from schema rollback
- Infinite loop trying to migrate "down"
- Corrupt DB that can't be re-upgraded

**How to simulate:**
```bash
# 1. Start with current version (creates latest schema)
observeco dashboard --port 9119 &
sleep 2
kill %1 2>/dev/null

# 2. Manually bump schema version to simulate a future version
python3 -c "
import sqlite3
from observeco.dirs import get_data_dir
db_path = get_data_dir() / 'pulse.db'
if db_path.exists():
    conn = sqlite3.connect(str(db_path))
    conn.execute('PRAGMA user_version = 99')
    conn.commit()
    cur = conn.execute('PRAGMA user_version')
    print('Schema version set to:', cur.fetchone()[0])
    conn.close()
else:
    print('No DB found — create one first by running observeco dashboard')
"

# 3. Start ObserveCo — should detect newer schema
observeco dashboard --port 9119 2>&1 | head -20
```

**Detection checklist:**
```
☐ Dashboard starts without crashing
☐ User-visible message about newer DB schema
☐ No data corruption
☐ DB can be re-upgraded after re-installing newer version
```

---

### Scenario 6: ObserveCo Uninstall + Reinstall — Data Preservation

**Pattern:** User uninstalls ObserveCo (`pip uninstall observeco`), then reinstalls later (`pip install observeco`). The `pulse.db` and config files remain on disk.

**What must happen:**
- `pip uninstall observeco` removes the package but NOT user data
- `pip install observeco` succeeds
- `observeco dashboard` starts and finds existing DB
- All historical data is available
- Config settings are preserved

**What must NOT happen:**
- Uninstall deletes `pulse.db` or config files
- Reinstall creates a fresh empty DB (losing history)
- Reinstall crashes because of stale cache/bytecode

**How to simulate:**
```bash
# 1. Record current data state
python3 -c "
from observeco.dirs import get_data_dir
import sqlite3
db_path = get_data_dir() / 'pulse.db'
if db_path.exists():
    conn = sqlite3.connect(str(db_path))
    cur = conn.execute('SELECT COUNT(*) FROM agents')
    print(f'Pre-uninstall: {cur.fetchone()[0]} agents')
    conn.close()
"

# 2. Uninstall
pip uninstall observeco -y

# 3. Verify data directory still exists
python3 -c "from observeco.dirs import get_data_dir; d=get_data_dir(); print('Data dir:', d, 'exists:', d.exists())"

# 4. Reinstall
pip install /Users/seanfzc/projects/observeco

# 5. Verify data preserved
observeco dashboard --port 9119 &
sleep 2
python3 -c "
from observeco.dirs import get_data_dir
import sqlite3
db_path = get_data_dir() / 'pulse.db'
if db_path.exists():
    conn = sqlite3.connect(str(db_path))
    cur = conn.execute('SELECT COUNT(*) FROM agents')
    print(f'Post-reinstall: {cur.fetchone()[0]} agents')
    conn.close()
"
kill %1 2>/dev/null
```

**Detection checklist:**
```
☐ Uninstall does not delete user data directory
☐ Reinstall finds existing DB
☐ All historical data available
☐ Config settings preserved
☐ No stale bytecode crashes
```

---

### Scenario 7: Offline Install — No Internet

**Pattern:** User is on a machine with no internet access. They have the ObserveCo wheel file (or pip cache) but cannot download dependencies.

**What must happen:**
- `pip install observeco` succeeds from local wheel/cache
- `observeco dashboard` starts
- Dashboard works for local-only features (agent monitoring, pulse data)
- LLM-dependent features show "configure API key" message (not crash)
- No attempt to phone home on startup

**What must NOT happen:**
- Crash because of missing dependency that requires network
- Infinite hang on startup waiting for network
- Silent failure of features that need internet

**How to simulate:**
```bash
# 1. Build the wheel
cd /Users/seanfzc/projects/observeco
pip install build
python -m build --wheel
WHEEL=$(ls dist/observeco-*.whl | tail -1)
echo "Wheel: $WHEEL"

# 2. Create offline environment
cd /tmp
python3 -m venv observeco-offline
source observeco-offline/bin/activate

# 3. Disable network (simulate by using --no-index)
pip install --no-index "$WHEEL" 2>&1 && \
  echo "Offline install succeeded" || \
  echo "Offline install FAILED — missing dependencies:"
# Note: --no-index will fail if dependencies aren't cached.
# For a real offline test, pre-cache all deps or use pip download.

# 4. Start dashboard
observeco dashboard --port 9997 2>&1 | head -10
```

**Detection checklist:**
```
☐ pip install succeeds from local wheel
☐ Dashboard starts without network
☐ Local features work (agent list, pulse data)
☐ LLM features show "configure API key" (not crash)
☐ No network calls on startup
```

---

### Scenario 8: Corrupted DB — Graceful Degradation

**Pattern:** User's `pulse.db` is corrupted (disk full, crash during write, manual edit). They start `observeco dashboard`.

**What must happen:**
- Dashboard starts (doesn't crash on DB open)
- DB error is caught and reported to user
- Dashboard shows "data unavailable" state for DB-dependent panels
- Other features (non-DB) still work
- User can re-initialize DB (via CLI command or auto-recovery)

**What must NOT happen:**
- Crash with unhandled `sqlite3.DatabaseError`
- Infinite retry loop trying to open corrupted DB
- Silent fallback to empty DB (user thinks data is gone)
- Cascade failure (one corrupted table takes down entire dashboard)

**How to simulate:**
```bash
# 1. Back up real DB
python3 -c "
from observeco.dirs import get_data_dir
import shutil
db_path = get_data_dir() / 'pulse.db'
bak_path = '/tmp/pulse.db.good'
if db_path.exists():
    shutil.copy2(db_path, bak_path)
    print(f'Backed up {db_path} → {bak_path}')
else:
    print('No DB to back up — creating a dummy one')
    db_path.parent.mkdir(parents=True, exist_ok=True)
    db_path.write_text('')
"

# 2. Corrupt the DB
python3 -c "
from observeco.dirs import get_data_dir
db_path = get_data_dir() / 'pulse.db'
with open(str(db_path), 'wb') as f:
    f.write(b'this is not a valid sqlite database')
print('DB corrupted')
"

# 3. Start dashboard
observeco dashboard --port 9119 2>&1 | head -20

# 4. Restore good DB
python3 -c "
from observeco.dirs import get_data_dir
from pathlib import Path
import shutil
db_path = get_data_dir() / 'pulse.db'
bak_path = '/tmp/pulse.db.good'
if Path(bak_path).exists():
    shutil.copy2(bak_path, db_path)
    print(f'Restored {bak_path} → {db_path}')
"
```

**Detection checklist:**
```
☐ Dashboard starts without crashing
☐ User-visible error message about DB issue
☐ Non-DB features still work
☐ Recovery path exists (CLI command or auto-recovery)
☐ No infinite retry loop
```

---

### Scenario 9: Port Collision — Dashboard Already Running

**Pattern:** User starts `observeco dashboard` on a machine where port 9119 is already in use (another instance, or another service). The product must handle this gracefully.

**What must happen:**
- Dashboard starts on the next available port (9120, 9121, etc.)
- Terminal output prints: `Port 9119 in use — serving on <actual_port>`
- Dashboard is fully functional on the fallback port
- User can access the dashboard at the fallback URL

**What must NOT happen:**
- Crash with `OSError: [Errno 48] Address already in use`
- Silent fallback with no user-visible message
- Bind to a port outside the 100-port scan range (9119–9219)

**How to simulate:**
```bash
# 1. Start first instance on default port
observeco dashboard --port 9119 --no-browser &
sleep 2

# 2. Start second instance — should auto-fallback
observeco dashboard --port 9119 --no-browser 2>&1 | head -5

# 3. Verify both are serving
curl -s http://127.0.0.1:9119 | head -c 100
echo
curl -s http://127.0.0.1:9120 | head -c 100

# 4. Clean up
kill %1 %2 2>/dev/null
```

**Detection checklist:**
```
☐ Second instance starts without crash
☐ Terminal shows "Port 9119 in use — serving on <port>"
☐ Both dashboards serve HTTP 200
☐ Fallback port is within expected range (9119–9219)
```

---

### Scenario 10: OBSERVECO_HOME Override — Custom Data Directory

**Pattern:** User sets `OBSERVECO_HOME` env var to a custom path before starting ObserveCo. The product must use that path for all data storage.

**What must happen:**
- `OBSERVECO_HOME` is respected for data directory
- All DB files, config, and heartbeat files go under the custom path
- No files written to the default platformdirs location
- Dashboard starts and functions normally

**What must NOT happen:**
- Data written to both locations (split-brain)
- Crash if the custom path doesn't exist (should create it)
- Ignore the env var and use default path

**How to simulate:**
```bash
# 1. Create a temp directory
TMPDIR=$(mktemp -d)
echo "Custom data dir: $TMPDIR"

# 2. Start dashboard with OBSERVECO_HOME override
OBSERVECO_HOME="$TMPDIR" observeco dashboard --port 9119 --no-browser &
sleep 2

# 3. Verify data is in the custom path
ls -la "$TMPDIR/"
python3 -c "
from observeco.dirs import get_data_dir
d = get_data_dir()
print(f'Data dir: {d}')
assert str(d) == '$TMPDIR', f'Expected $TMPDIR, got {d}'
print('OBSERVECO_HOME override works correctly')
"

# 4. Verify default path is empty
python3 -c "
from observeco.dirs import get_data_dir
# Temporarily unset to check default
import os
os.environ.pop('OBSERVECO_HOME', None)
# Need to reimport to get fresh value — but dirs.py caches at module level
# So just check the platformdirs path doesn't have our test data
from pathlib import Path
default = Path.home() / 'Library' / 'Application Support' / 'observeco'
print(f'Default path: {default}')
print(f'Has pulse.db: {(default / \"pulse.db\").exists()}')
"

# 5. Clean up
kill %1 2>/dev/null
rm -rf "$TMPDIR"
```

**Detection checklist:**
```
☐ OBSERVECO_HOME is respected for data directory
☐ All files written under custom path
☐ Default platformdirs path is empty
☐ Dashboard starts without errors
☐ Custom path is created if it doesn't exist
```

---

### Scenario 11: Headless Mode — No Browser Available

**Pattern:** User runs `observeco dashboard --no-browser` on a server or CI environment with no display. The product must start without attempting to open a browser.

**What must happen:**
- Dashboard starts and binds to the specified port
- No attempt to open a browser (no `webbrowser.open()` call)
- Terminal shows the dashboard URL
- Dashboard is accessible via curl/API calls
- Process can be cleanly terminated with Ctrl+C

**What must NOT happen:**
- Crash with `TclError: no display name and no $DISPLAY environment variable`
- Hang waiting for browser to open
- Silent failure (starts but doesn't bind)

**How to simulate:**
```bash
# 1. Start in headless mode
observeco dashboard --port 9119 --no-browser &
sleep 2

# 2. Verify it's serving
curl -s http://127.0.0.1:9119 | head -c 200
echo

# 3. Verify no browser process was spawned
# (On macOS, check if 'observeco' is the only observeco process)
ps aux | grep observeco | grep -v grep

# 4. Clean up
kill %1 2>/dev/null
```

**Detection checklist:**
```
☐ Dashboard starts without DISPLAY error
☐ Dashboard is accessible via curl
☐ No browser window opened
☐ Process can be killed cleanly
```

---

### Scenario 12: Old Data Migration — ~/.observeco/ Exists

**Pattern:** User has an old installation with data in `~/.observeco/` (the legacy path). They install the new version which uses `platformdirs` (e.g., `~/Library/Application Support/observeco/` on macOS). The product must migrate data automatically.

**What must happen:**
- On first start, old data is migrated from `~/.observeco/` to the new platformdirs path
- All files (pulse.db, config, etc.) are copied
- Old directory is removed after successful migration
- No data loss during migration
- Dashboard starts with all historical data available

**What must NOT happen:**
- Crash during migration
- Partial migration (some files copied, some not)
- Data loss if migration fails mid-way
- Both old and new paths have data (split-brain)

**How to simulate:**
```bash
# 1. Create a fake old data directory
OLD_DIR=~/.observeco
mkdir -p "$OLD_DIR"
# Create a dummy pulse.db
python3 -c "
import sqlite3
conn = sqlite3.connect('$OLD_DIR/pulse.db')
conn.execute('CREATE TABLE IF NOT EXISTS agents (id INTEGER PRIMARY KEY, name TEXT)')
conn.execute(\"INSERT INTO agents (name) VALUES ('legacy-agent')\")
conn.commit()
print('Created legacy DB with 1 agent')
conn.close()
"

# 2. Verify old dir exists
ls -la "$OLD_DIR/"

# 3. Start dashboard — migration should run
observeco dashboard --port 9119 --no-browser &
sleep 3

# 4. Verify data is in new location
python3 -c "
from observeco.dirs import get_data_dir
import sqlite3
db_path = get_data_dir() / 'pulse.db'
if db_path.exists():
    conn = sqlite3.connect(str(db_path))
    cur = conn.execute('SELECT COUNT(*) FROM agents')
    print(f'New DB has {cur.fetchone()[0]} agents')
    conn.close()
"

# 5. Verify old dir is gone
if [ -d "$OLD_DIR" ]; then
    echo "WARNING: Old directory still exists — migration may not have run"
else
    echo "Old directory cleaned up — migration successful"
fi

# 6. Clean up
kill %1 2>/dev/null
```

**Detection checklist:**
```
☐ Old data is migrated to new location
☐ All files are copied (not just some)
☐ Old directory is removed after migration
☐ Dashboard starts with historical data
☐ No crash during migration
```

---

### Scenario 13: Startup Validation Failure — Pre-Flight Checks

**Pattern:** User starts `observeco dashboard` but one or more startup validation checks fail (unwritable data dir, port already in use, missing dependencies). The product must report the failure clearly and exit gracefully.

**What must happen:**
- Startup validation (`run_checks()`) runs before the server starts
- If a check fails, a clear error message is printed
- The error message tells the user what to fix
- The process exits with a non-zero exit code
- No partial server start (no port bound, no DB created)

**What must NOT happen:**
- Server starts despite validation failure
- Cryptic error message (traceback instead of user-friendly message)
- Silent failure (process exits 0 but nothing works)
- Partial state (DB created but server not running)

**How to simulate:**
```bash
# 1. Test with unwritable data dir
TMPDIR=$(mktemp -d)
chmod 000 "$TMPDIR"  # Make it unwritable
OBSERVECO_HOME="$TMPDIR" observeco dashboard --port 9119 --no-browser 2>&1 | head -10
chmod 755 "$TMPDIR"
rm -rf "$TMPDIR"

# 2. Test with invalid port (port 0 is invalid)
observeco dashboard --port 0 --no-browser 2>&1 | head -10

# 3. Test with missing db-path parent
observeco dashboard --db-path /nonexistent/path/pulse.db --no-browser 2>&1 | head -10
```

**Detection checklist:**
```
☐ Startup validation runs before server starts
☐ Clear error message on failure
☐ Process exits with non-zero exit code
☐ No partial server state
☐ Error message tells user what to fix
```

---

## 3. The Golden Gate — Pre-Release Installation Checklist

Run this checklist before ANY release that changes installation, upgrade, or first-run behaviour.

```
☐ 1. Fresh install on clean machine (Scenario 1)
    - pip install succeeds
    - observeco dashboard starts
    - Empty states render correctly
    - No tracebacks

☐ 2. Fresh install with Hermes (Scenario 2)
    - Agents auto-discovered
    - No Sean artifacts
    - Hermes config unchanged

☐ 3. Hermes upgrade while ObserveCo running (Scenario 3)
    - No crash during/after upgrade
    - Agent list preserved
    - Config format changes handled gracefully

☐ 4. ObserveCo upgrade (Scenario 4)
    - DB migration runs
    - All data preserved
    - New features available
    - Old features still work

☐ 5. ObserveCo downgrade (Scenario 5)
    - Graceful detection of newer schema
    - No crash
    - Recovery path documented

☐ 6. Uninstall + reinstall (Scenario 6)
    - Data preserved
    - Config preserved
    - No stale cache issues

☐ 7. Offline install (Scenario 7)
    - Wheel installs without network
    - Local features work
    - LLM features degrade gracefully

☐ 8. Corrupted DB (Scenario 8)
    - Dashboard starts
    - Error reported to user
    - Recovery path exists

☐ 9. Port collision (Scenario 9)
    - Auto-fallback to next available port
    - User-visible message about port change

☐ 10. OBSERVECO_HOME override (Scenario 10)
    - Custom data dir respected
    - No split-brain data

☐ 11. Headless mode (Scenario 11)
    - Starts without DISPLAY error
    - No browser attempt

☐ 12. Old data migration (Scenario 12)
    - ~/.observeco/ migrated to platformdirs
    - Old dir cleaned up

☐ 13. Startup validation (Scenario 13)
    - Pre-flight checks run
    - Clear error on failure
```

---

## 4. Expert Prompts for Hound

### Prompt A: Fresh Install Audit

```
You are in 100x Installation-Test Mode.

Given the ObserveCo package at [path], run a complete fresh-install audit:

1. Create a clean Python venv in /tmp
2. pip install the package from local source
3. Start `observeco dashboard --port 9999 --no-browser`
4. Verify:
   - Server starts without tracebacks
   - curl http://localhost:9999 returns HTTP 200
   - Response contains empty-state text (not blank page)
   - No "Hermes home not found" or similar errors in output
5. Check the data directory was created:
   - Run: python3 -c "from observeco.dirs import get_data_dir; print(get_data_dir())"
   - Verify pulse.db exists
6. Kill the server cleanly (Ctrl+C simulation)

Report: PASS/FAIL per check, with exact terminal output.
```

### Prompt B: Upgrade/Downgrade Audit

```
Run a full upgrade/downgrade audit on ObserveCo at [path]:

1. Install current version, start dashboard, generate some data
2. Back up pulse.db
3. Simulate a schema version bump (PRAGMA user_version = 99)
4. Start dashboard — verify graceful downgrade detection
5. Restore backup, verify data integrity
6. Test uninstall + reinstall:
   - pip uninstall -y observeco
   - Verify data dir still exists
   - pip install from source
   - Start dashboard — verify historical data is present

Report: PASS/FAIL per step, with exact terminal output.
```

### Prompt C: Failure Mode Audit

```
Test all installation failure modes for ObserveCo at [path]:

1. Port collision: start two instances, verify auto-fallback
2. OBSERVECO_HOME override: set to custom path, verify data isolation
3. Headless mode: start with --no-browser, verify no DISPLAY error
4. Corrupted DB: overwrite pulse.db with garbage, verify graceful handling
5. Startup validation: test with unwritable data dir, verify clear error

Report: PASS/FAIL per scenario, with exact terminal output and error messages.
```

---

## 5. Lessons Learned

*This section accumulates installation failures caught by this playbook. Each entry documents a real failure mode that escaped previous testing.*

| # | Date | Scenario | What happened | Root cause | Fix |
|---|------|----------|--------------|------------|-----|
| — | — | — | — | — | — |

---

## 6. Registration Checklist

This playbook must be registered in the master-fidelity-gate.md and playbook-evolution-meta.md to be part of the official playbook system.

### master-fidelity-gate.md

- [ ] Add **Layer J: Installation Fidelity** with items covering:
  - J1: Fresh install in clean venv (weight 3)
  - J2: Upgrade preserves data (weight 3)
  - J3: Downgrade handled gracefully (weight 2)
  - J4: Port collision auto-fallback (weight 2)
  - J5: OBSERVECO_HOME override (weight 1)
  - J6: Headless mode (weight 1)
  - J7: Old data migration (weight 2)
  - J8: Startup validation (weight 2)
- [ ] Update scoring table (add ~16 pts, adjust threshold)
- [ ] Add this playbook to the Playbook Inventory reference

### playbook-evolution-meta.md

- [ ] Add this playbook to the version table (v2.0, 2026-06-19)
- [ ] Update stale playbook count from 11 to 12

---

## 7. Appendix: Test Environment Setup

### Docker-based clean-room testing

For the most isolated test, use Docker to simulate a clean machine:

```dockerfile
# Dockerfile.observeco-test
FROM python:3.11-slim

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy and install ObserveCo
COPY . /app
RUN pip install /app

# Expose dashboard port
EXPOSE 9119

# Default: start dashboard
CMD ["observeco", "dashboard", "--port", "9119"]
```

```bash
# Build and run
docker build -t observeco-test -f Dockerfile.observeco-test .
docker run -it --rm -p 9119:9119 observeco-test
```

### macOS VM testing

For macOS-specific testing (launchd, Full Disk Access, etc.):

```bash
# Using tart (https://github.com/cirruslabs/tart)
tart clone ghcr.io/cirruslabs/macos-sequoia-vanilla:latest observeco-test
tart run observeco-test
# Then SSH in and run the test scenarios
```

### Quick smoke test (no Docker, no VM)

```bash
# One-liner for a quick sanity check
cd /tmp && \
  python3 -m venv observeco-smoke && \
  source observeco-smoke/bin/activate && \
  pip install /Users/seanfzc/projects/observeco && \
  timeout 5 observeco dashboard --port 9996 --no-browser 2>&1 || true
```
