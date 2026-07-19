"""Tests for feature tier selection functions.

Covers all four rungs of cost_tracking and all three of tool_call_tracking.
"""


from observeco.capability.env_snapshot import EnvSnapshot
from observeco.features.cost_tracking import select_cost_tracking_tier
from observeco.features.tool_call_tracking import select_tool_call_tier

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _snap(**kwargs) -> EnvSnapshot:
    return EnvSnapshot(**kwargs)


# ---------------------------------------------------------------------------
# cost_tracking
# ---------------------------------------------------------------------------


class TestCostTrackingTier:
    def test_proxy_launcher_tier(self):
        """config_parsed + chosen_port → tier 1 (proxy-launcher)."""
        snap = _snap(config_parsed={"profiles": {}}, chosen_port=51877)
        name, quality, _ = select_cost_tracking_tier(snap)
        assert name == "proxy-launcher"
        assert quality == "exact"

    def test_estimate_tier_no_config(self):
        """No config → tier 4 (estimate)."""
        snap = _snap()
        name, quality, _ = select_cost_tracking_tier(snap)
        assert name == "estimate"
        assert quality == "approximate"

    def test_estimate_tier_config_but_no_port(self):
        """config_parsed but no chosen_port → cannot use proxy → estimate."""
        snap = _snap(config_parsed={"providers": []}, chosen_port=None)
        name, quality, _ = select_cost_tracking_tier(snap)
        assert name == "estimate"

    def test_session_store_tier(self):
        """No config, no port, but session_store_path → tier 3."""
        snap = _snap(session_store_path="/home/user/.hermes/sessions")
        name, quality, _ = select_cost_tracking_tier(snap)
        assert name == "session-store"
        assert quality == "near-exact"

    def test_proxy_launcher_wins_over_session_store(self):
        """proxy-launcher wins even if session store is also available."""
        snap = _snap(
            config_parsed={"profiles": {}},
            chosen_port=51877,
            session_store_path="/home/user/.hermes/sessions",
        )
        name, _, _ = select_cost_tracking_tier(snap)
        assert name == "proxy-launcher"

    def test_estimate_is_always_reachable(self):
        """Completely empty snapshot → estimate (bottom rung always available)."""
        snap = EnvSnapshot()
        name, _, _ = select_cost_tracking_tier(snap)
        assert name == "estimate"

    def test_returns_three_tuple(self):
        snap = _snap(config_parsed={"profiles": {}}, chosen_port=1234)
        result = select_cost_tracking_tier(snap)
        assert len(result) == 3
        assert all(isinstance(v, str) for v in result)


# ---------------------------------------------------------------------------
# tool_call_tracking
# ---------------------------------------------------------------------------


class TestToolCallTier:
    def test_proxy_intercept_tier(self):
        """config_parsed + chosen_port → proxy-intercept."""
        snap = _snap(config_parsed={"profiles": {}}, chosen_port=51877)
        name, quality, _ = select_tool_call_tier(snap)
        assert name == "proxy-intercept"
        assert quality == "exact"

    def test_session_store_tier(self):
        """No config/port but session store → session-store."""
        snap = _snap(session_store_path="/home/user/.hermes/sessions")
        name, quality, _ = select_tool_call_tier(snap)
        assert name == "session-store"
        assert quality == "near-exact"

    def test_disabled_tier(self):
        """Nothing available → disabled."""
        snap = _snap()
        name, quality, _ = select_tool_call_tier(snap)
        assert name == "disabled"
        assert quality == "none"

    def test_proxy_wins_over_session_store(self):
        """proxy-intercept takes precedence when both conditions met."""
        snap = _snap(
            config_parsed={"providers": []},
            chosen_port=12345,
            session_store_path="/home/.hermes/sessions",
        )
        name, _, _ = select_tool_call_tier(snap)
        assert name == "proxy-intercept"

    def test_returns_three_tuple(self):
        snap = _snap()
        result = select_tool_call_tier(snap)
        assert len(result) == 3
        assert all(isinstance(v, str) for v in result)

    def test_no_port_only_config(self):
        """config_parsed but no port → cannot use proxy; session store also absent."""
        snap = _snap(config_parsed={"providers": []}, chosen_port=None)
        name, _, _ = select_tool_call_tier(snap)
        assert name == "disabled"
