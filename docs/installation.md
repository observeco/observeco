# Installation

## Requirements

- Python 3.10+
- macOS (primary target — Hermes agents on Mac Mini)
- Linux or WSL (partial support)

## Install

```bash
pip install observeco
```

For the dashboard:

```bash
pip install observeco[dashboard]
```

## Verify

```bash
observeco --help
```

You should see the CLI help with `pulse`, `chisel`, `clawforge`, and `dashboard` commands.

## Quick Start

```bash
# Check agent health
observeco pulse check

# Start the dashboard
observeco dashboard
```

That's it. No config file required for Hermes users on macOS. The CLI auto-discovers your Hermes agents.

## Hermes Plugin Setup

For full observability (tracing, evaluation, behavioral monitoring):

```bash
# 1. Enable the Hermes OTEL plugin
hermes plugins enable observability/observeco

# 2. Set the endpoint
echo 'HERMES_OBSERVECO_ENDPOINT=http://127.0.0.1:4318' >> ~/.hermes/.env

# 3. Restart the gateway
launchctl kickstart -k gui/$(id -u)/ai.hermes.gateway

# 4. Start the OTEL listener & dashboard
observeco otel listen start --port 4318
observeco dashboard
```

See [`docs/hermes-plugin-integration.md`](docs/hermes-plugin-integration.md) for the full integration guide.
