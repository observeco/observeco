"""Probe Driver Registry — typed probe classes with @register decorator.

Phase 7.4: Replaces 132-line if/else chain in _probe_agent() with
a registry of typed probes, each in its own file under probe/.
"""

from __future__ import annotations

import json
import re
import subprocess
import time
from dataclasses import dataclass
from typing import Optional

import httpx

from observeco.config import AgentConfig


@dataclass
class ProbeResult:
    """Standard probe result."""
    status: str  # "alive", "dead", "error"
    latency_ms: float
    error: str = ""
    metadata: str = ""

    @property
    def is_alive(self) -> bool:
        return self.status == "alive"


# -- Registry ------------------------------------------------------------------

_PROBE_REGISTRY: dict[str, type["BaseProbe"]] = {}


def register(*schemes: str):
    """Decorator: register a probe class for one or more URL schemes."""
    def decorator(cls):
        for scheme in schemes:
            _PROBE_REGISTRY[scheme.lower()] = cls
        return cls
    return decorator


def get_probe(scheme: str) -> Optional[type["BaseProbe"]]:
    """Look up a probe class by scheme name."""
    return _PROBE_REGISTRY.get(scheme.lower())


def list_probe_types() -> list[str]:
    """List all registered probe scheme names."""
    return list(_PROBE_REGISTRY.keys())


class BaseProbe:
    """Abstract base for all probes."""

    def probe(self, agent: AgentConfig, timeout: float = 10.0) -> ProbeResult:
        """Execute probe against an agent. Must be overridden."""
        raise NotImplementedError


# -- HTTP Probe ----------------------------------------------------------------

@register("http", "https")
class HttpProbe(BaseProbe):
    def probe(self, agent: AgentConfig, timeout: float = 10.0) -> ProbeResult:
        start = time.time()
        try:
            resp = httpx.get(agent.health_check, timeout=timeout)
            latency = (time.time() - start) * 1000
            metadata = ""
            if resp.status_code < 500 and resp.text.strip():
                try:
                    body = resp.json()
                    if isinstance(body, dict) and "metadata" in body:
                        metadata = json.dumps(body["metadata"])
                except (json.JSONDecodeError, ValueError):
                    pass
            if resp.status_code < 500:
                return ProbeResult("alive", latency, "", metadata)
            return ProbeResult("error", latency, f"HTTP {resp.status_code}", "")
        except httpx.TimeoutException:
            return ProbeResult("dead", (time.time() - start) * 1000, "timeout", "")
        except Exception as e:
            return ProbeResult("error", (time.time() - start) * 1000, str(e)[:200], "")


# -- launchd Probe ------------------------------------------------------------

@register("launchd")
class LaunchdProbe(BaseProbe):
    def probe(self, agent: AgentConfig, timeout: float = 10.0) -> ProbeResult:
        if not agent.health_check:
            return ProbeResult("error", 0, "no health check", "")
        label = agent.health_check[len("launchd:"):]
        start = time.time()
        try:
            result = subprocess.run(
                ["launchctl", "list", label],
                capture_output=True, text=True, timeout=5,
            )
            latency = (time.time() - start) * 1000
            if result.returncode == 0:
                return ProbeResult("alive", latency, "", "")
            return ProbeResult("dead", latency, result.stderr[:200] or result.stdout[:200], "")
        except subprocess.TimeoutExpired:
            return ProbeResult("dead", (time.time() - start) * 1000, "timeout", "")
        except FileNotFoundError:
            return ProbeResult("dead", (time.time() - start) * 1000, "launchctl not found", "")
        except Exception as e:
            return ProbeResult("error", (time.time() - start) * 1000, str(e)[:200], "")


# -- Docker Probe -------------------------------------------------------------

@register("docker")
class DockerProbe(BaseProbe):
    def probe(self, agent: AgentConfig, timeout: float = 10.0) -> ProbeResult:
        if not agent.health_check:
            return ProbeResult("error", 0, "no health check", "")
        container = agent.health_check[len("docker:"):]
        start = time.time()
        try:
            result = subprocess.run(
                ["docker", "ps", "--filter", f"name={container}",
                 "--format", "{{.Status}}"],
                capture_output=True, text=True, timeout=10,
            )
            latency = (time.time() - start) * 1000
            if result.returncode == 0 and result.stdout.strip():
                status = result.stdout.strip()
                if "Up" in status:
                    return ProbeResult("alive", latency, status, "")
                elif "Exited" in status or "Paused" in status or "Created" in status:
                    return ProbeResult("dead", latency, status, "")
                return ProbeResult("error", latency, status[:200], "")
            return ProbeResult("dead", latency, result.stderr[:200] or "container not found", "")
        except subprocess.TimeoutExpired:
            return ProbeResult("dead", (time.time() - start) * 1000, "timeout", "")
        except FileNotFoundError:
            return ProbeResult("error", (time.time() - start) * 1000, "docker CLI not found", "")
        except Exception as e:
            return ProbeResult("error", (time.time() - start) * 1000, str(e)[:200], "")


# -- systemd Probe ------------------------------------------------------------

@register("systemd")
class SystemdProbe(BaseProbe):
    def probe(self, agent: AgentConfig, timeout: float = 10.0) -> ProbeResult:
        if not agent.health_check:
            return ProbeResult("error", 0, "no health check", "")
        unit = agent.health_check[len("systemd:"):]
        start = time.time()
        try:
            result = subprocess.run(
                ["systemctl", "is-active", unit],
                capture_output=True, text=True, timeout=5,
            )
            latency = (time.time() - start) * 1000
            status = result.stdout.strip()
            if result.returncode == 0 and status == "active":
                return ProbeResult("alive", latency, status, "")
            return ProbeResult("dead", latency, status or result.stderr[:200], "")
        except subprocess.TimeoutExpired:
            return ProbeResult("dead", (time.time() - start) * 1000, "timeout", "")
        except FileNotFoundError:
            return ProbeResult("error", (time.time() - start) * 1000, "systemctl not found", "")
        except Exception as e:
            return ProbeResult("error", (time.time() - start) * 1000, str(e)[:200], "")


# -- Shell Command Probe ------------------------------------------------------

@register("shell")
class ShellProbe(BaseProbe):
    def probe(self, agent: AgentConfig, timeout: float = 10.0) -> ProbeResult:
        if not agent.health_check:
            return ProbeResult("error", 0, "no health check", "")
        start = time.time()
        try:
            result = subprocess.run(
                agent.health_check, shell=True, capture_output=True, text=True, timeout=10
            )
            latency = (time.time() - start) * 1000
            if result.returncode == 0:
                return ProbeResult("alive", latency, "", "")
            return ProbeResult("dead", latency, result.stderr[:200] or result.stdout[:200], "")
        except subprocess.TimeoutExpired:
            return ProbeResult("dead", (time.time() - start) * 1000, "timeout", "")
        except Exception as e:
            return ProbeResult("error", (time.time() - start) * 1000, str(e)[:200], "")


# -- pgrep Probe --------------------------------------------------------------

@register("pgrep")
class PgrepProbe(BaseProbe):
    def probe(self, agent: AgentConfig, timeout: float = 10.0) -> ProbeResult:
        start = time.time()
        try:
            result = subprocess.run(
                ["pgrep", "-f", re.escape(agent.name)],
                capture_output=True, text=True, timeout=5,
            )
            latency = (time.time() - start) * 1000
            if result.returncode == 0:
                return ProbeResult("alive", latency, "", "")
            return ProbeResult("dead", latency, "no matching process", "")
        except Exception as e:
            return ProbeResult("error", (time.time() - start) * 1000, str(e)[:200], "")


# -- Resolver -----------------------------------------------------------------

def resolve_probe(agent: AgentConfig) -> BaseProbe:
    """Resolve the correct probe for an agent based on its health_check config.

    Resolution chain:
    1. http/https → HttpProbe
    2. launchd: → LaunchdProbe
    3. docker: → DockerProbe
    4. systemd: → SystemdProbe
    5. shell command (no known scheme) → ShellProbe
    6. None/empty → PgrepProbe
    """
    hc = agent.health_check
    if hc:
        for scheme in ("http://", "https://", "launchd:", "docker:", "systemd:"):
            if hc.startswith(scheme):
                clean = scheme.rstrip("://")
                cls = get_probe(clean)
                if cls:
                    return cls()
        # Fall through to shell probe for unknown commands
        cls = get_probe("shell")
        return cls() if cls else ShellProbe()
    # No health check → pgrep by process name
    cls = get_probe("pgrep")
    return cls() if cls else PgrepProbe()
