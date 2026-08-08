"""Fleet health classification & verdict contract tests.

Source of truth: specs/audit-fleet-health-classification.md (ADOPTED, Rev 8.1,
deleg_68cb02e6). These are the distinguishing tests — each must FAIL on the
current (buggy) implementation and on config-based/class-based/behavioral-only/
hardcoded wrong impls, and PASS on the corrected two-signal one.

Classifier signature (real):
    _classify_agent(pulse, drift, circuit, errors, now, *, ever_alive, managed)

Rules (top-to-bottom, first match wins):
1. ever_alive=False AND managed        -> configured_never_ran (WARNING)
2. ever_alive=False AND NOT managed    -> not_observed (excluded, chip)
3. alive_now=True                      -> healthy
4. ever_alive AND NOT alive_now AND managed    -> managed_down (WARNING/CRITICAL)
5. ever_alive AND NOT alive_now AND NOT managed -> not_running (neutral)

managed = qualifying health_check (launchd:/docker:/systemd:/http://https://).
"""

from __future__ import annotations

import time

from observeco.dashboard.routes import fleet as fleet_mod


def _classify(*, ever_alive: bool, managed: bool, alive_now: bool) -> str:
    """Classify a synthetic agent via the real two-signal _classify_agent."""
    now = int(time.time())
    pulse = {"status": "alive" if alive_now else "dead", "timestamp": now}
    return fleet_mod._classify_agent(
        pulse,
        drift=[],
        circuit={},
        errors=[],
        now=now,
        ever_alive=ever_alive,
        managed=managed,
    )


class TestClassify:
    """The five classifier rules (contract §2)."""

    def test_never_alive_managed_is_configured_never_ran(self):
        """Rule 1: never-alive + managed health_check -> CONFIGURED NEVER RAN."""
        assert _classify(ever_alive=False, managed=True, alive_now=False) == "configured_never_ran"

    def test_never_alive_unmanaged_is_not_observed(self):
        """Rule 2: never-alive + no managed health_check -> NOT OBSERVED."""
        assert _classify(ever_alive=False, managed=False, alive_now=False) == "not_observed"

    def test_alive_now_is_healthy_regardless_of_managed(self):
        """Rule 3: alive_now=True -> HEALTHY, managed irrelevant."""
        assert _classify(ever_alive=True, managed=True, alive_now=True) == "healthy"
        assert _classify(ever_alive=True, managed=False, alive_now=True) == "healthy"

    def test_ever_alive_managed_down_is_managed_down(self):
        """Rule 4: ever-alive, not alive now, managed -> MANAGED DOWN (alert)."""
        assert _classify(ever_alive=True, managed=True, alive_now=False) == "managed_down"

    def test_ever_alive_unmanaged_not_running(self):
        """Rule 5: ever-alive, not alive now, unmanaged -> NOT RUNNING (neutral)."""
        assert _classify(ever_alive=True, managed=False, alive_now=False) == "not_running"

    def test_never_alive_managed_but_alive_now_is_healthy(self):
        """Edge: a never-alive agent that just went alive is HEALTHY (onboarding
        transition — moves into the monitored set automatically)."""
        assert _classify(ever_alive=False, managed=True, alive_now=True) == "healthy"


class TestIsMonitored:
    """The managed discriminator (contract §1)."""

    def test_qualifying_schemes_are_managed(self):
        for hc in ("launchd:ai.hermes.gateway", "docker:container",
                   "systemd:unit", "http://localhost:8080/health",
                   "https://example.com/health"):
            assert fleet_mod._is_monitored(hc) is True, hc

    def test_pgrep_echo_empty_are_not_managed(self):
        for hc in ("pgrep -f my_new_agent", "echo ok", "", None):
            assert fleet_mod._is_monitored(hc) is False, repr(hc)

    def test_substring_http_does_not_qualify(self):
        """'pgrep -f httpserver' must NOT qualify (scheme-literal, not substring)."""
        assert fleet_mod._is_monitored("pgrep -f httpserver") is False


class TestFleetVerdict:
    """Verdict fixture→sentence table (contract §3)."""

    def _verdict(self, counts: dict) -> str:
        return fleet_mod._fleet_verdict(counts)["text"]

    def test_managed_down_is_first(self):
        """Row 1: managed_down > 0 -> DOWN sentence, disclosed denominator."""
        text = self._verdict({"healthy": 24, "managed_down": 1, "not_running": 0,
                              "configured_never_ran": 0, "not_observed": 0})
        assert "DOWN" in text and "of 25" in text, text

    def test_configured_never_ran_alerts(self):
        """Row 2: configured_never_ran > 0 -> alert sentence."""
        text = self._verdict({"healthy": 0, "managed_down": 0, "not_running": 0,
                              "configured_never_ran": 1, "not_observed": 3})
        assert "never ran" in text, text

    def test_not_running_is_neutral(self):
        """Row 4: not_running > 0 -> neutral sentence, not an alert."""
        text = self._verdict({"healthy": 25, "managed_down": 0, "not_running": 2,
                              "configured_never_ran": 0, "not_observed": 11})
        assert "not running" in text, text
        assert "DOWN" not in text, text

    def test_not_observed_disclosed(self):
        """Row 5: not_observed > 0 -> disclosed in sentence."""
        text = self._verdict({"healthy": 25, "managed_down": 0, "not_running": 0,
                              "configured_never_ran": 0, "not_observed": 11})
        assert "not observed" in text, text

    def test_all_healthy(self):
        """Row 6: all healthy -> 'All {H} agents healthy'."""
        text = self._verdict({"healthy": 25, "managed_down": 0, "not_running": 0,
                              "configured_never_ran": 0, "not_observed": 0})
        assert "All 25 agents healthy" in text, text

    def test_zero_observed_never_fake_clean(self):
        """Row 3: nothing observed -> honest sentence, never 'all 0 healthy'."""
        text = self._verdict({"healthy": 0, "managed_down": 0, "not_running": 0,
                              "configured_never_ran": 0, "not_observed": 11})
        assert "No agents observed running yet" in text, text
        assert "all 0 agents healthy" not in text.lower()
