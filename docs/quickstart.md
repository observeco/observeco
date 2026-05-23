# Quick Start

## Scenario 1: You run Hermes agents

```bash
pip install observeco[dashboard]
observeco pulse check           # See all agents, alive/dead/error
observeco pulse circuit         # Check circuit breaker state
echo "your prompt" | observeco chisel trim   # Decompose your system prompt
observeco dashboard             # Open the fleet dashboard
```

ObserveCo auto-discovers agents from `~/.hermes/config.yaml` and `~/.hermes/agents/`.

## Scenario 2: You run OpenClaw agents

```bash
observeco clawforge profile     # Profile Kepler's context composition
observeco clawforge load --probe  # Test intent-aware classifier
observeco clawforge garden      # Check memory debt score
```

## Scenario 3: You don't use Hermes or OpenClaw

```bash
observeco agents add my-agent --framework crewai --health-check "http://localhost:8000/health"
observeco pulse check
observeco dashboard
```

## What Next?

- `observeco --help` — full command list
- `docs/commands.md` — detailed flag documentation
- `docs/dashboard.md` — dashboard walkthrough
