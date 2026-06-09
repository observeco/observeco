"""
Batch fixes for 7 confirmed bugs:
1. toggleHide does nothing — add hidden filter to backend
2. Metric rows show placeholder text — wire to real /api/agent-detail endpoint
3. Add Agent button does nothing — wire to POST /api/agents/add
4. Status contradiction — add staleness threshold
5. Hermes Agents → Agents (done)
6. Kepler check
7. Pro tiles / error banners check
"""
import sys

sys.path.insert(0, '/Users/seanfzc/projects/observeco')

# 1. Check Kepler rendering
from observeco.db import Database

db = Database()
agents = db.get_agents()
print(f"Total agents in DB: {len(agents)}")
for a in agents:
    print(f"  {a['agent_name']} (fw={a.get('framework','?')})")

# 2. Check what get_agent_status_summary returns for Kepler
summary = db.get_agent_status_summary()
print(f"\nTotal in summary: {len(summary)}")
print(f"Kepler: {summary.get('kepler', 'NOT FOUND')}")

# 3. Check the section rendering logic — what type does Kepler get?
agent_cfg = {a["agent_name"]: a for a in agents}
for name in ['kepler', 'accelerator', 'test-agent-ci']:
    a = agent_cfg.get(name, {})
    fw = a.get("framework", "custom")
    hc = a.get("health_check", "") or ""
    cfg_path = a.get("config_path", "") or ""
    if fw in ("hermes", "openclaw") or "SOUL.md" in cfg_path:
        ntype = "agent"
    elif hc or fw == "service":
        ntype = "service"
    else:
        ntype = "workflow"
    print(f"{name}: fw={fw}, hc={hc}, cfg_path={cfg_path[:30]}, type={ntype}")
