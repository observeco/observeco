# Installation

## Requirements

- Python 3.10+
- macOS, Linux, or WSL

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

That's it. No config file required for Hermes users. The CLI auto-discovers your agents.
