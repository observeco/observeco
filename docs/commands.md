# Commands

## `observeco pulse check`

Check agent liveness.

```bash
observeco pulse check
observeco pulse check --watch   # Poll every 5s for 3 cycles
```

## `observeco pulse circuit`

Show and manage circuit breakers.

```bash
observeco pulse circuit                              # Show all breakers
observeco pulse circuit --reset my-agent             # Reset a tripped breaker
observeco pulse circuit --threshold my-agent:5       # Set max retries to 5
```

## `observeco chisel trim`

Decompose a system prompt into token breakdown by component.

```bash
echo "You are a helpful assistant..." | observeco chisel trim
```

## `observeco chisel drift`

Show 7-day token allocation drift.

```bash
observeco chisel drift                     # All agents
observeco chisel drift --agent kepler       # Specific agent
```

## `observeco clawforge profile`

Profile OpenClaw agent context composition.

```bash
observeco clawforge profile                  # All OpenClaw agents
observeco clawforge profile --agent kepler   # Specific agent
```

## `observeco clawforge load`

Test intent-aware context classification.

```bash
observeco clawforge load --probe             # Test with sample messages
observeco clawforge load --message "The agent crashed"   # Classify specific message
```

## `observeco clawforge garden`

Scan MEMORY.md for duplicates, contradictions, stale entries.

```bash
observeco clawforge garden                    # Scan all agents
observeco clawforge garden --agent kepler     # Specific agent
observeco clawforge garden --apply            # Fix duplicates automatically
```

## `observeco agents`

Manage agent registration.

```bash
observeco agents discover                     # Auto-discover agents
observeco agents list                         # List all known agents
observeco agents add my-agent                 # Add a custom agent
observeco agents add my-agent --framework openclaw --health-check "curl localhost:8080/health"
```

## `observeco dashboard`

Open the web dashboard.

```bash
observeco dashboard                           # Default port 9119
observeco dashboard --port 8080               # Custom port
observeco dashboard --static                  # Generate static HTML
```
