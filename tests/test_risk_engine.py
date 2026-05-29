"""Tests for the observeco risk engine."""

from observeco.risk_engine import classify_tool_call, classify_text_action, RiskLevel, RiskResult, ToolCall


class TestClassifyToolCall:
    """Test RiskLevel classification for various tool call patterns."""

    def _classify(self, name: str, args: dict):
        tc = ToolCall.from_dict({"name": name, "arguments": args})
        return classify_tool_call(tc)

    def test_read_tool_is_low_risk(self):
        result = self._classify("read", {"path": "/app/src/main.py"})
        assert result.level == RiskLevel.LOW

    def test_write_to_non_sensitive_is_medium(self):
        result = self._classify("write", {"path": "/app/src/test.txt"})
        assert result.level == RiskLevel.MEDIUM

    def test_write_to_env_is_high(self):
        result = self._classify("write", {"path": "/app/.env"})
        assert result.level == RiskLevel.HIGH

    def test_destructive_rm_is_critical(self):
        result = self._classify("exec", {"command": "rm -rf /"})
        assert result.level == RiskLevel.CRITICAL

    def test_git_push_is_high(self):
        result = self._classify("exec", {"command": "git push origin main --force"})
        assert result.level == RiskLevel.HIGH

    def test_ls_is_medium(self):
        result = self._classify("exec", {"command": "ls -la /app"})
        assert result.level == RiskLevel.MEDIUM

    def test_memory_write_is_medium(self):
        result = self._classify("memory_write", {"key": "user_name", "value": "Alice"})
        assert result.level == RiskLevel.MEDIUM

    def test_browser_navigate_is_medium(self):
        result = self._classify("browser_navigate", {"url": "https://example.com"})
        assert result.level == RiskLevel.MEDIUM

    def test_unknown_tool_is_low(self):
        result = self._classify("unknown_custom_tool", {})
        assert result.level == RiskLevel.LOW

    def test_curl_is_medium(self):
        result = self._classify("exec", {"command": "curl https://api.example.com"})
        assert result.level == RiskLevel.MEDIUM

    def test_delete_database_is_critical(self):
        result = self._classify("exec", {"command": "DROP DATABASE production"})
        assert result.level == RiskLevel.CRITICAL


class TestClassifyTextAction:
    """Test text-based action classification."""

    def test_read_action_is_low(self):
        result = classify_text_action("read file")
        assert result.level == RiskLevel.LOW

    def test_rm_action_is_critical(self):
        result = classify_text_action("rm -rf /var/log")
        assert result.level == RiskLevel.CRITICAL

    def test_deploy_action_is_high(self):
        result = classify_text_action("deploy to production")
        assert result.level == RiskLevel.HIGH


class TestRiskResult:
    """Test RiskResult properties."""

    def test_result_has_category(self):
        tc = ToolCall.from_dict({"name": "exec", "arguments": {"command": "ls"}})
        result = classify_tool_call(tc)
        assert hasattr(result, "category")
        assert isinstance(result.category, str)

    def test_result_has_reason(self):
        tc = ToolCall.from_dict({"name": "read", "arguments": {"path": "x"}})
        result = classify_tool_call(tc)
        assert hasattr(result, "reason")
        assert isinstance(result.reason, str)

    def test_result_has_action(self):
        result = classify_text_action("hello")
        assert hasattr(result, "action")
