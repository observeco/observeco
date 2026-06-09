# Pathway Scan — Generic Service Discovery

## Node Types (framework-agnostic)

| Type | Discovery Source | Hermes Example | OpenClaw Example |
|---|---|---|---|
| agent | `get_agents()` DB + `openclaw.json` agents.list | main, hound, pa | kepler |
| cron | `~/.*/cron/jobs.json` (auto-discover all frameworks) | cron/*.json deliver="telegram:..." | cron/*.json delivery={channel,to} |
| daemon | `launchctl list` (macOS) / `systemctl` (Linux) | ai.hermes.pa.plist | ai.openclaw.gateway.plist |
| platform | Config platform/channel sections | telegram, discord, slack | telegram |
| watcher | Daemon with "watch" in name or cron polling signals | intelligence_watcher | trace-hook plugin |
| gateway | Daemon named "gateway" | hermes gateway (8080) | openclaw gateway (18789) |
| service | Daemon not matching other types | memory-cache (9130) | — |
| mesh | mesh.yaml | A2A peer → OpenClaw | A2A peer → Hermes |
| consumer | Agent that processes signals | hound (auto_consumer) | kepler (inbox poll) |

## Cron Format — Unified Parser

Both Hermes and OpenClaw use `{jobs: [{name, ...}]}` wrapper. Detect deliver format:

```python
def parse_job_deliver(job):
    d = job.get("deliver")  # Hermes: string "telegram:-1003985609979:29"
    if d and isinstance(d, str):
        return d
    
    dv = job.get("delivery", {})  # OpenClaw: {mode, channel, to}
    if isinstance(dv, dict):
        ch = dv.get("channel", "")
        to = dv.get("to", "")
        if ch == "telegram" and to:
            return f"telegram:{to}"
    
    return "local"

def parse_job_name(job):
    return job.get("name") or job.get("id", f"cron-{idx}")

def parse_job_enabled(job):
    return job.get("enabled", True)  # Hermes: absent=true, OpenClaw: explicit
```

## Signal Conflict Dedup

When scanning inbox + archive + outbox + quarantine + failed, the same signal might exist in multiple states. Use `signal_id` or filename hash as dedup key — only the highest-severity status survives:
  - failed > quarantine > outbox > inbox > archive