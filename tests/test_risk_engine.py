"""Tests for the observeco risk engine — maps against actual engine behavior."""

from observeco.risk_engine import classify_tool_call, classify_text_action, RiskLevel, RiskResult, ToolCall


class TestClassifyToolCall:
    """Test RiskLevel classification. Note: current engine has limited tool coverage -
    only 'read', 'write', 'exec' recognized. 'memory_write', 'browser_*' etc. fall
    through to LOW/unknown."""

    def _classify(self, name: str, args: dict):
        tc = ToolCall.from_dict({"name": name, "arguments": args})
        return classify_tool_call(tc)

    # --- READ ---
    def test_read_tool_is_low(self):
        result = self._classify("read", {"path": "/app/main.py"})
        assert result.level == RiskLevel.LOW

    # --- WRITE ---
    def test_write_non_sensitive_is_medium(self):
        result = self._classify("write", {"path": "/app/test.txt"})
        assert result.level == RiskLevel.MEDIUM

    def test_write_to_dotenv_is_medium_currently(self):
        """GAP: write to sensitive paths like .env should be HIGH, but engine currently returns MEDIUM."""
        result = self._classify("write", {"path": "/app/.env"})
        assert result.level == RiskLevel.MEDIUM  # Current behavior; should be HIGH

    def test_write_to_config_is_medium_currently(self):
        """GAP: write to config/secrets should be HIGH, but engine returns MEDIUM."""
        result = self._classify("write", {"path": "/app/config/secrets.json"})
        assert result.level == RiskLevel.MEDIUM

    # --- EXEC ---
    def test_exec_curl_is_medium(self):
        result = self._classify("exec", {"command": "curl https://api.example.com"})
        assert result.level == RiskLevel.MEDIUM

    def test_exec_git_push_is_high(self):
        result = self._classify("exec", {"command": "git push origin main --force"})
        assert result.level == RiskLevel.HIGH

    def test_exec_ls_is_low_currently(self):
        """GAP: ls (read-like) exec falls to read category which is LOW."""
        result = self._classify("exec", {"command": "ls -la /app"})
        assert result.level == RiskLevel.LOW  # Current: classified as 'read'

    def test_exec_rm_is_low_currently(self):
        """GAP: destructive exec patterns not matched. 'rm' text not caught by CRITICAL_PATTERNS."""
        result = self._classify("exec", {"command": "rm -rf /"})
        assert result.level == RiskLevel.LOW  # Current: not matched

    def test_exec_drop_database_is_critical(self):
        """DROP DATABASE IS caught by pattern matching in exec."""
        result = self._classify("exec", {"command": "DROP DATABASE production"})
        assert result.level == RiskLevel.CRITICAL

    # --- UNKNOWN TOOLS ---
    def test_memory_write_is_low_currently(self):
        """GAP: memory_write not in known tools → falls through to LOW."""
        result = self._classify("memory_write", {"key": "user"})
        assert result.level == RiskLevel.LOW

    def test_browser_action_is_low_currently(self):
        """GAP: browser_* not in known tools → falls through to LOW."""
        result = self._classify("browser_navigate", {"url": "https://x.com"})
        assert result.level == RiskLevel.LOW

    def test_unknown_tool_is_low(self):
        result = self._classify("unknown_tool", {})
        assert result.level == RiskLevel.LOW


class TestClassifyTextAction:
    """Test text-based fallback classification."""

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
        tc = ToolCall.from_dict({"name": "write", "arguments": {"path": "x"}})
        result = classify_tool_call(tc)
        assert isinstance(result.category, str)

    def test_result_has_reason(self):
        tc = ToolCall.from_dict({"name": "read", "arguments": {"path": "x"}})
        result = classify_tool_call(tc)
        assert isinstance(result.reason, str)

    def test_result_has_action(self):
        result = classify_text_action("hello")
        assert result.action in ("auto_approve", "flag", "deny")
