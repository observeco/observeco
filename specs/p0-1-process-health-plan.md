# P0-1 Implementation Plan: Agent Process Health Expansion

## Goal
Expand ObserveCo's agent detection and health monitoring to cover:
- macOS launchd services (`launchctl list`)
- Docker containers (`docker ps`)
- Linux systemd units (`systemctl list-units`)
- Windows services (`tasklist` / `Get-Service`)
- Cross-framework agent type labeling

## Phase 1: Detection Expansion (auto_detect.py)

### 1a: launchd service scanner
```python
def scan_launchd() -> list[AgentConfig]:
    """Scan macOS launchd for known agent services."""
    result = subprocess.run(["launchctl", "list"], capture_output=True, text=True, timeout=5)
    # Parse: PID\tStatus\tLabel
    # Label pattern: ai.hermes.{name}, ai.openclaw.{name}, com.observeco.{name}
    # Return agents with health_check = "launchd:{label}" for probe dispatch
```

### 1b: Docker container scanner
```python
def scan_docker() -> list[AgentConfig]:
    """Scan Docker for running containers with agent-sounding names."""
    result = subprocess.run(["docker", "ps", "--format", "{{.Names}}|{{.Image}}|{{.Status}}"],
                          capture_output=True, text=True, timeout=10)
    # Filter containers by name patterns or all
    # health_check = "docker:{container_name}"
```

### 1c: systemd scanner (Linux)
```python
def scan_systemd() -> list[AgentConfig]:
    """Scan systemd for agent service units."""
    result = subprocess.run(["systemctl", "list-units", "--type=service", "--all", "--no-pager"],
                          capture_output=True, text=True, timeout=10)
```

## Phase 2: Probe Expansion (pulse/check.py)

### 2a: launchd probe
When agent.health_check starts with "launchd:", parse the label and run `launchctl print` for detailed status.

### 2b: Docker probe
When agent.health_check starts with "docker:", use `docker inspect` or `docker ps --filter name=`.

### 2c: systemd probe
When health_check starts with "systemd:", use `systemctl is-active`.

## Phase 3: Integration
- Auto-discovered launchd/Docker agents appear in fleet view
- Label shows framework type = "launchd" / "Docker" / "systemd"
- Dashboard shows health status dot for all of them