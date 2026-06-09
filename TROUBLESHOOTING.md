# Troubleshooting

Common issues and fixes for ObserveCo.

---

## 1. `pip install` Fails

### Symptom: Dependency conflict or build error

**Try this first:**
```bash
pip install --upgrade pip
pip install 'observeco[dashboard]'
```

**Still failing?** Install in a fresh virtual environment:
```bash
python3 -m venv ~/obs-venv
source ~/obs-venv/bin/activate
pip install --upgrade pip
pip install 'observeco[dashboard]'
```

**On macOS with Apple Silicon (M1/M2/M3/M4):** Some transitive deps may need build tools:
```bash
xcode-select --install   # if not already installed
```

**Still stuck?** Run with verbose output and share the last ~20 lines:
```bash
pip install 'observeco[dashboard]' -v 2>&1 | tail -20
```

---

## 2. `observeco: command not found` After Install

### Symptom: `zsh: command not found: observeco`

The install succeeded but the binary isn't on your PATH.

**Fix:**
```bash
# Find where observeco was installed
python3 -m site --user-base
# Add to PATH (add this to ~/.zshrc or ~/.bashrc)
export PATH="$HOME/Library/Python/3.11/bin:$PATH"   # macOS example
```

**For pipx users:**
```bash
pipx ensurepath
# Then reopen terminal or source ~/.zshrc
```

To verify it works:
```bash
observeco --version
```

---

## 3. Dashboard Fails to Start

### Symptom: `python -m observeco dashboard` exits immediately or hangs

**Common causes:**

**Port conflict:**
```bash
# Check if port 8090 is already in use
lsof -i :8090
# Kill whatever is using it, or change port:
OBSERVECO_DASHBOARD_PORT=8091 observeco dashboard
```

**Missing extras:**
```bash
# Ensure you installed with dashboard extras
pip install 'observeco[dashboard]'
```

**Browser doesn't open automatically:**
The server is likely running — just open `http://localhost:8090` manually in your browser.

**If the server starts but no content loads:**
```bash
# Check the terminal output for errors
# Then check the daemon is running:
observeco pulse check
```

---

## 4. "No Agents Detected" or Dashboard Shows Empty

### Symptom: Dashboard loads but shows "No agents" or blank fleet

**Step 1 — Is the watch daemon running?**
```bash
observeco pulse check
```
If you see "No agents registered", proceed to step 2.

**Step 2 — Manually add an agent:**
```bash
observeco agent add --name my-agent
```
Or let auto-discovery find them:
```bash
observeco agent discover
```

**Step 3 — Wait 30 seconds** for the first pulse to fire:
```bash
observeco pulse check
```
You should see status dots appear after the first cycle.

**Still empty?** Agents must be actively running on your machine. Check:
```bash
# Are your agents actually running?
ps aux | grep -i hound
ps aux | grep -i hermes
```

**Need help identifying what to monitor?** Run the discovery scan:
```bash
observeco agent discover --verbose
```

---

## 5. Daemon Isn't Running

### Symptom: Dashboard shows stale/expired data, alerts not firing

**Check daemon status:**
```bash
# macOS — check for the launchd service
launchctl list | grep observeco

# Any OS — check process
ps aux | grep observeco | grep -v grep
```

**Start the daemon:**
```bash
observeco daemon start
```

---

## 6. Authentication / License Issues

### Symptom: Dashboard shows "Free" banner, Pro features not accessible

**Check your license status:**
```bash
observeco license status
```

**During 30-day trial:** All Pro features are unlocked automatically on first `observeco dashboard`. No activation needed.

**After trial expires:** Pro features (LLM-powered diagnosis, push alerts, auto-heal) are disabled. Your data and Free features remain fully accessible.

**If you've purchased a Pro license and it's not showing up:**
```bash
observeco license refresh
```

---

## 7. Errors in Dashboard / Logs

### General rule: Check the daemon log first

```bash
# ObserveCo daemon log
cat ~/.observeco/logs/daemon.log

# Pulse check logs
cat ~/.observeco/logs/pulse.log
```

**Key error categories:**

| Error Pattern | Likely Cause | Fix |
|--------------|-------------|-----|
| `Connection refused` | Agent health endpoint down | Check if the agent process is running |
| `Timeout after 10s` | Agent hung, not responding | Restart the agent |
| `No matching process` | Agent process crashed | Restart or check for crashes |
| `Database locked` | Concurrent access | Wait 5s, retry. Only one dashboard instance |
| `Port 8090 in use` | Another service on that port | Use `OBSERVECO_DASHBOARD_PORT=8091` |
| `License validation failed` | Network issue checking license | Run `observeco license refresh` |

---

## 8. Known macOS-Specific Issues

| Issue | Cause | Fix |
|-------|-------|-----|
| `launchctl` not found | Running on non-macOS | Use `docker ps` or `systemctl` alternative |
| Python framework build error | macOS System Integrity Protection | Use Homebrew Python: `brew install python@3.11` |
| Dashboard won't open browser | macOS sandboxing | Open `http://localhost:8090` manually |

---

## Still Stuck?

Create an issue on GitHub with:
1. Your OS and Python version: `python3 --version && uname -a`
2. ObserveCo version: `observeco --version`
3. The exact error message (paste the terminal output)
4. Steps to reproduce
