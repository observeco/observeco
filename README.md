# ObserveCo

Runtime observability for your AI agents — built for Hermes, works with anything.

```bash
pip install observeco[dashboard] && observeco dashboard
```

[![MIT License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue)](pyproject.toml)

Know if your agents are alive, what's in their context, and when something breaks — all from a single command.

## Quick Start

```bash
pip install observeco
observeco pulse check          # Agent liveness in one command
observeco pulse circuit        # Show circuit breaker state
echo "your prompt" | observeco chisel trim   # Token breakdown
observeco clawforge profile    # Context profile for OpenClaw agents
observeco dashboard            # Web UI with fleet view + error timeline
```

## Features

- **`pulse check`** — alive/dead/error per agent, zero config for Hermes users
- **`pulse circuit`** — N-failure breaker with auto-cooldown
- **`chisel trim`** — system prompt compression with per-component token breakdown
- **`clawforge profile`** — context profiler for OpenClaw: MEMORY.md size, skills, workspace
- **`clawforge load`** — intent-aware classifier that loads only what's needed
- **`dashboard`** — local web UI, ships with the library

All data local. No cloud. No telemetry built with ❤️ for the AI agent community.

## License

MIT
