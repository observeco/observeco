"""Tests for the observeco risk engine."""

from observeco.risk_engine import classify_tool_call, RiskLevel, RiskResult


class TestClassifyToolCall:
    """Test RiskLevel classification for various tool call patterns."""

    def test_read_tool_is_low_risk(self):
        tool_call = {"name": "read", "arguments": {"path": "/app/src/main.py"}}
        result = classify_tool_call(tool_call)
        assert result.risk_level == RiskLevel.LOW, f"Expected LOW, got {result.risk_level}"

    def test_write_to_non_sensitive_is_medium(self):
        tool_call = {"name": "write", "arguments": {"path": "/app/src/test.txt"}}
        result = classify_tool_call(tool_call)
        assert result.risk_level == RiskLevel.MEDIUM, f"Expected MEDIUM, got {result.risk_level}"

    def test_write_to_sensitive_path_is_high(self):
        tool_call = {"name": "write", "arguments": {"path": "/app/.env"}}
        result = classify_tool_call(tool_call)
        assert result.risk_level == RiskLevel.HIGH, f"Expected HIGH, got {result.risk_level}"

    def test_destructive_exec_is_critical(self):
        tool_call = {"name": "exec", "arguments": {"command": "rm -rf /"}}
        result = classify_tool_call(tool_call)
        assert result.risk_level == RiskLevel.CRITICAL, f"Expected CRITICAL, got {result.risk_level}"

    def test_git_push_is_high(self):
        tool_call = {"name": "exec", "arguments": {"command": "git push origin main --force"}}
        result = classify_tool_call(tool_call)
        assert result.risk_level == RiskLevel.HIGH, f"Expected HIGH, got {result.risk_level}"

    def test_safe_exec_is_medium(self):
        tool_call = {"name": "exec", "arguments": {"command": "ls -la /app"}}
        result = classify_tool_call(tool_call)
        assert result.risk_level == RiskLevel.MEDIUM, f"Expected MEDIUM, got {result.risk_level}"

    def test_memory_write_is_medium(self):
        tool_call = {"name": "memory_write", "arguments": {"key": "user_name", "value": "Alice"}}
        result = classify_tool_call(tool_call)
        assert result.risk_level == RiskLevel.MEDIUM, f"Expected MEDIUM, got {result.risk_level}"

    def test_browser_action_is_medium(self):
        tool_call = {"name": "browser_navigate", "arguments": {"url": "https://example.com"}}
        result = classify_tool_call(tool_call)
        assert result.risk_level == RiskLevel.MEDIUM, f"Expected MEDIUM, got {result.risk_level}"

    def test_unknown_tool_is_low(self):
        tool_call = {"name": "unknown_custom_tool", "arguments": {}}
        result = classify_tool_call(tool_call)
        assert result.risk_level == RiskLevel.LOW, f"Expected LOW, got {result.risk_level}"


class TestRiskLevelEnum:
    """Test RiskLevel enum properties."""

    def test_has_correct_values(self):
        assert RiskLevel.LOW.value == RiskLevel(1).value
        assert RiskLevel.MEDIUM in (RiskLevel.MEDIUM,)
