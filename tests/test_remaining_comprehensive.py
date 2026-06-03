"""Event bus, risk, infra tests."""

from observeco.event_bus import publish, get_events
from observeco.risk_engine import RiskResult, classify_text_action


class TestEventBus:
    def test_publish_no_crash(self):
        publish(None, "test")

    def test_publish_second_no_crash(self):
        publish(None, "test2")

    def test_get_events_returns_list(self):
        e = get_events()
        assert isinstance(e, list)


class TestRiskEngine:
    def test_risk_result_has_fields(self):
        r = RiskResult(level="low", category="test", reason="test", action="none")
        assert r.level == "low"

    def test_classify_text_action(self):
        result = classify_text_action("")
        assert isinstance(result, RiskResult)