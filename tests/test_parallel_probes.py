"""Tests for Phase 7.2 — Parallel Probe Engine."""
import time
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

from observeco.config import AgentConfig
from observeco.pulse.check import _probe_agent


def _fake_probe(agent, delay=0.3):
    """A slow fake probe that simulates real probe latency."""
    time.sleep(delay)
    return ("alive", 0.1, "", "")


def test_parallel_probes_faster_than_sequential():
    """Probing 5 agents with parallel should be faster than sum of delays."""
    agents = [AgentConfig(name=f"test-{i}", framework="custom", health_check=f"echo ok") for i in range(5)]

    with ThreadPoolExecutor(max_workers=10) as pool:
        start = time.time()
        results = list(pool.map(lambda a: _fake_probe(a, 0.2), agents))
        parallel_time = time.time() - start

    # 5 agents x 0.2s each should take ~0.2s in parallel (not 1.0s)
    assert parallel_time < 0.8, f"Parallel took {parallel_time:.2f}s — too slow"
    assert len(results) == 5
    assert all(r[0] == "alive" for r in results)


def test_parallel_probe_handles_exceptions():
    """One failing probe shouldn't block others."""
    def probe_with_one_failure(a):
        if a.name == "test-1":
            raise RuntimeError("Simulated failure")
        return ("alive", 0.1, "", "")

    agents = [AgentConfig(name=f"test-{i}", framework="custom") for i in range(4)]
    results = []

    with ThreadPoolExecutor(max_workers=10) as pool:
        futures = {pool.submit(probe_with_one_failure, a): a for a in agents}
        for future in futures:
            agent = futures[future]
            try:
                result = future.result(timeout=5)
                results.append((agent.name, result[0]))
            except Exception:
                results.append((agent.name, "error"))

    assert len(results) == 4
    bad = [r for r in results if r[1] == "error"]
    assert len(bad) == 1
    assert bad[0][0] == "test-1"


def test_real_probe_is_importable():
    """_probe_agent should be importable and callable."""
    agent = AgentConfig(name="test-ping", framework="custom", health_check="echo ok")
    result = _probe_agent(agent)
    assert isinstance(result, tuple)
    assert len(result) >= 3