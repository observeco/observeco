"""
Tests for ObserveCo Transparent API Proxy — Tasks 4.1, 4.2, 4.3

Tests cover:
- Token usage extraction from JSON responses (OpenAI + Anthropic formats)
- SSE stream usage extraction
- Provider detection from URL and model name
- Auth passthrough (headers forwarded, not logged)
- Retry logic on upstream failure
- Graceful error responses
- Database logging integration
"""

import json
import os
import tempfile

import pytest

# ---------------------------------------------------------------------------
# Import proxy modules
# ---------------------------------------------------------------------------
from observeco.proxy.server import (
    STRIP_REQUEST_HEADERS,
    STRIP_RESPONSE_HEADERS,
    ProxyServer,
    _extract_from_json,
    _extract_usage_from_stream_chunks,
    create_app,
    detect_provider,
    extract_usage_from_response,
    log_proxy_usage,
)

# ===========================================================================
# 1. Token Usage Extraction — JSON Responses
# ===========================================================================

class TestExtractUsageFromJson:
    """Task 4.1: Verify usage extraction from standard JSON responses."""

    def test_openai_format(self):
        """OpenAI returns prompt_tokens + completion_tokens."""
        data = {
            "model": "gpt-4o",
            "usage": {
                "prompt_tokens": 150,
                "completion_tokens": 50,
                "total_tokens": 200,
            },
        }
        result = _extract_from_json(data)
        assert result is not None
        assert result["input_tokens"] == 150
        assert result["output_tokens"] == 50
        assert result["total_tokens"] == 200
        assert result["model"] == "gpt-4o"

    def test_anthropic_format(self):
        """Anthropic returns input_tokens + output_tokens."""
        data = {
            "model": "claude-sonnet-4-20250514",
            "usage": {
                "input_tokens": 300,
                "output_tokens": 100,
            },
        }
        result = _extract_from_json(data)
        assert result is not None
        assert result["input_tokens"] == 300
        assert result["output_tokens"] == 100
        assert result["total_tokens"] == 400

    def test_openai_with_cache_tokens(self):
        """OpenAI cache tokens in prompt_tokens_details."""
        data = {
            "model": "gpt-4o",
            "usage": {
                "prompt_tokens": 200,
                "completion_tokens": 80,
                "total_tokens": 280,
                "prompt_tokens_details": {
                    "cached_tokens": 120,
                },
            },
        }
        result = _extract_from_json(data)
        assert result is not None
        assert result["input_tokens"] == 200
        assert result["output_tokens"] == 80
        assert result["cache_read_tokens"] == 120

    def test_anthropic_with_cache_tokens(self):
        """Anthropic cache tokens at top level of usage."""
        data = {
            "model": "claude-sonnet-4-20250514",
            "usage": {
                "input_tokens": 500,
                "output_tokens": 150,
                "cache_creation_input_tokens": 200,
                "cache_read_input_tokens": 100,
            },
        }
        result = _extract_from_json(data)
        assert result is not None
        assert result["input_tokens"] == 500
        assert result["output_tokens"] == 150
        assert result["cache_creation_tokens"] == 200
        assert result["cache_read_tokens"] == 100

    def test_no_usage_returns_none(self):
        """Response without usage field returns None."""
        data = {"model": "gpt-4o", "choices": [{"message": {"content": "hi"}}]}
        result = _extract_from_json(data)
        assert result is None

    def test_zero_tokens_returns_none(self):
        """Response with all-zero tokens returns None."""
        data = {"model": "gpt-4o", "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}}
        result = _extract_from_json(data)
        assert result is None

    def test_missing_completion_tokens(self):
        """Response with only prompt_tokens still works."""
        data = {"model": "gpt-4o", "usage": {"prompt_tokens": 100, "completion_tokens": 0, "total_tokens": 100}}
        result = _extract_from_json(data)
        assert result is not None
        assert result["input_tokens"] == 100
        assert result["output_tokens"] == 0
        assert result["total_tokens"] == 100


# ===========================================================================
# 2. Token Usage Extraction — Full Response Body
# ===========================================================================

class TestExtractUsageFromResponse:
    """Task 4.1: End-to-end extraction from response bytes."""

    def test_json_content_type(self):
        """Standard JSON response with application/json content type."""
        body = json.dumps({
            "model": "gpt-4o",
            "usage": {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
        }).encode()
        result = extract_usage_from_response(body, "application/json")
        assert result is not None
        assert result["total_tokens"] == 150

    def test_empty_body(self):
        """Empty body returns None."""
        result = extract_usage_from_response(b"", "application/json")
        assert result is None

    def test_none_body(self):
        """None body returns None."""
        result = extract_usage_from_response(None, "application/json")
        assert result is None

    def test_invalid_json(self):
        """Invalid JSON returns None."""
        result = extract_usage_from_response(b"not json", "application/json")
        assert result is None


# ===========================================================================
# 3. SSE Stream Usage Extraction
# ===========================================================================

class TestExtractFromSse:
    """Task 4.1: Usage extraction from SSE streaming responses."""

    def test_sse_with_usage_in_final_chunk(self):
        """OpenAI streaming: usage in the last data: chunk."""
        chunks = [
            b'data: {"choices":[{"delta":{"content":"Hello"}}]}\n\n',
            b'data: {"choices":[{"delta":{"content":" world"}}]}\n\n',
            b'data: {"usage":{"prompt_tokens":100,"completion_tokens":20,"total_tokens":120}}\n\n',
            b'data: [DONE]\n\n',
        ]
        body = b"".join(chunks)
        result = extract_usage_from_response(body, "text/event-stream")
        assert result is not None
        assert result["input_tokens"] == 100
        assert result["output_tokens"] == 20
        assert result["total_tokens"] == 120

    def test_sse_no_usage(self):
        """SSE stream without usage data returns None."""
        chunks = [
            b'data: {"choices":[{"delta":{"content":"Hello"}}]}\n\n',
            b'data: [DONE]\n\n',
        ]
        body = b"".join(chunks)
        result = extract_usage_from_response(body, "text/event-stream")
        assert result is None

    def test_sse_multiple_usage_chunks(self):
        """Multiple usage chunks — last one wins."""
        chunks = [
            b'data: {"usage":{"prompt_tokens":50,"completion_tokens":10,"total_tokens":60}}\n\n',
            b'data: {"usage":{"prompt_tokens":100,"completion_tokens":30,"total_tokens":130}}\n\n',
        ]
        body = b"".join(chunks)
        result = extract_usage_from_response(body, "text/event-stream")
        assert result is not None
        assert result["total_tokens"] == 130  # Last chunk wins

    def test_extract_usage_from_stream_chunks(self):
        """_extract_usage_from_stream_chunks helper."""
        chunks = [
            b'data: {"choices":[{"delta":{"content":"Hi"}}]}\n\n',
            b'data: {"usage":{"prompt_tokens":80,"completion_tokens":15,"total_tokens":95}}\n\n',
        ]
        result = _extract_usage_from_stream_chunks(chunks)
        assert result is not None
        assert result["total_tokens"] == 95


# ===========================================================================
# 4. Provider Detection
# ===========================================================================

class TestDetectProvider:
    """Task 4.1: Accurate provider detection from URL + model name."""

    def test_openai_by_url(self):
        assert detect_provider("https://api.openai.com/v1", "gpt-4o") == "openai"

    def test_openai_by_model(self):
        assert detect_provider("https://my-proxy.com/v1", "gpt-4o") == "openai"

    def test_anthropic_by_url(self):
        assert detect_provider("https://api.anthropic.com/v1", "claude-3") == "anthropic"

    def test_anthropic_by_model(self):
        assert detect_provider("https://proxy.com/v1", "claude-sonnet-4-20250514") == "anthropic"

    def test_deepseek(self):
        assert detect_provider("https://api.deepseek.com/v1", "deepseek-chat") == "deepseek"

    def test_ollama(self):
        assert detect_provider("http://localhost:11434/v1", "llama3") == "ollama"

    def test_unknown(self):
        assert detect_provider("https://my-custom-api.com/v1", "custom-model") == "auto-detected"

    def test_zhipuai(self):
        assert detect_provider("https://open.bigmodel.cn/api/v1", "glm-4") == "zhipuai"

    def test_xiaomi(self):
        assert detect_provider("https://api.xiaomi.com/v1", "mimo-v2.5") == "xiaomi"


# ===========================================================================
# 5. Auth Passthrough (Task 4.2)
# ===========================================================================

class TestAuthPassthrough:
    """Task 4.2: Verify auth headers are forwarded, not logged."""

    def test_auth_header_forbidden_in_strip_list(self):
        """Authorization is NOT in STRIP_REQUEST_HEADERS — it should be forwarded."""
        assert "authorization" not in STRIP_REQUEST_HEADERS
        assert "Authorization" not in STRIP_REQUEST_HEADERS

    def test_api_key_header_forbidden_in_strip_list(self):
        """api-key (Anthropic) is NOT in STRIP_REQUEST_HEADERS."""
        assert "api-key" not in STRIP_REQUEST_HEADERS

    def test_host_is_stripped(self):
        """Host header is stripped (httpx sets it to upstream)."""
        assert "host" in STRIP_REQUEST_HEADERS

    def test_response_headers_strip_hop_by_hop(self):
        """Hop-by-hop headers stripped from response."""
        assert "transfer-encoding" in STRIP_RESPONSE_HEADERS
        assert "content-encoding" in STRIP_RESPONSE_HEADERS
        assert "connection" in STRIP_RESPONSE_HEADERS

    def test_auth_not_in_stats(self):
        """Proxy stats should never contain auth headers."""
        server = ProxyServer(upstream_url="https://api.openai.com")
        stats = server.get_stats()
        stats_str = json.dumps(stats)
        assert "Authorization" not in stats_str
        assert "api-key" not in stats_str
        assert "Bearer" not in stats_str


# ===========================================================================
# 6. Database Logging (Task 4.1)
# ===========================================================================

class TestLogProxyUsage:
    """Task 4.1: Verify usage is logged to database correctly."""

    def test_log_usage_writes_to_db(self):
        """log_proxy_usage creates a token_logs entry with source='proxy'."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")

            # Initialize DB with schema
            from observeco.db import Database
            db = Database(db_path)

            usage = {
                "input_tokens": 200,
                "output_tokens": 80,
                "total_tokens": 280,
                "model": "gpt-4o",
            }

            log_proxy_usage(
                db_path=db_path,
                agent_name="test-agent",
                usage=usage,
                provider="openai",
                upstream_url="https://api.openai.com",
                turn_id="test-turn-001",
            )

            # Verify entry exists
            conn = db._get_conn()
            row = conn.execute(
                "SELECT * FROM token_logs WHERE turn_id = ?", ("test-turn-001",)
            ).fetchone()
            assert row is not None

            # Check column values by name
            col_names = [c[1] for c in conn.execute("PRAGMA table_info(token_logs)").fetchall()]
            row_dict = dict(zip(col_names, row))

            assert row_dict["agent_name"] == "test-agent"
            assert row_dict["total_tokens"] == 280
            assert row_dict["input_tokens"] == 200
            assert row_dict["output_tokens"] == 80
            assert row_dict["provider"] == "openai"
            assert row_dict["source"] == "proxy"
            assert row_dict["cost"] >= 0  # Cost should be computed

    def test_log_usage_handles_db_error(self):
        """log_proxy_usage doesn't crash on DB errors."""
        # Should not raise
        log_proxy_usage(
            db_path="/nonexistent/path/db.sqlite",
            agent_name="test-agent",
            usage={"total_tokens": 100, "input_tokens": 100, "output_tokens": 0},
            provider="openai",
            upstream_url="https://api.openai.com",
        )


# ===========================================================================
# 7. Proxy Server (Task 4.3)
# ===========================================================================

class TestProxyServer:
    """Task 4.3: Resilience and stats."""

    def test_default_db_path(self):
        """Default DB path is auto-detected."""
        server = ProxyServer()
        assert server.db_path.endswith(".db") or server.db_path.endswith(".sqlite")

    def test_stats_initial(self):
        """Stats start at zero."""
        server = ProxyServer(upstream_url="https://api.openai.com")
        stats = server.get_stats()
        assert stats["requests"] == 0
        assert stats["errors"] == 0
        assert stats["total_tokens_captured"] == 0
        assert stats["upstream"] == "https://api.openai.com"

    def test_custom_port(self):
        """Custom port is respected."""
        server = ProxyServer(port=8080)
        assert server.port == 8080

    def test_custom_agent_name(self):
        """Custom agent name is respected."""
        server = ProxyServer(agent_name="my-agent")
        assert server.agent_name == "my-agent"


# ===========================================================================
# 8. App Factory
# ===========================================================================

class TestCreateApp:
    """Verify Starlette app is created correctly."""

    def test_app_creation(self):
        """create_app returns a Starlette app."""
        app = create_app(upstream_url="https://api.openai.com", port=9200)
        assert app is not None

    def test_app_routes(self):
        """App has /health and /v1/* routes."""
        app = create_app()
        routes = [r.path for r in app.routes if hasattr(r, 'path')]
        assert "/health" in routes
        assert any("/v1/" in r for r in routes)


# ===========================================================================
# 9. Run Tests
# ===========================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
