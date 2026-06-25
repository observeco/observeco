"""
ObserveCo Transparent API Proxy — Core Server

Task 4.1: Async HTTP proxy that captures token usage from LLM API responses.
Task 4.2: Auth passthrough — forwards Authorization headers, never logs API keys.
Task 4.3: Resilience — connection pooling, retry upstream, graceful error handling.

Usage:
  python -m observeco.proxy.server --port 9200 --upstream https://api.openai.com
  # or via CLI:
  observeco proxy --port 9200
"""

import argparse
import json
import logging
import os
import time
import uuid
from typing import Optional

import httpx
import uvicorn
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import Response, StreamingResponse
from starlette.routing import Route

from observeco.dirs import hermes_home

logger = logging.getLogger("observeco.proxy")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_PORT = 9200
DEFAULT_UPSTREAM = "https://api.openai.com"
REQUEST_TIMEOUT = 300  # seconds — LLM calls can be slow
MAX_RETRIES = 2
RETRY_DELAY = 1.0  # seconds

# Headers to strip from forwarded requests (security)
STRIP_REQUEST_HEADERS = frozenset([
    "host",  # Will be set to upstream host
    "content-length",  # Will be recalculated
    "transfer-encoding",  # Will be set by httpx
])

# Headers to strip from responses (security)
STRIP_RESPONSE_HEADERS = frozenset([
    "transfer-encoding",
    "content-encoding",
    "content-length",
    "connection",
])


# ---------------------------------------------------------------------------
# Token Usage Capture
# ---------------------------------------------------------------------------

def extract_usage_from_response(body: bytes, content_type: str) -> Optional[dict]:
    """
    Extract token usage from LLM API response body.

    Handles:
    - OpenAI/Anthropic standard JSON responses (usage in body)
    - Streaming SSE responses (usage in final chunk)

    Returns dict with keys: input_tokens, output_tokens, cache_creation_tokens,
    cache_read_tokens, model, total_tokens, provider_raw.
    Returns None if usage cannot be extracted.
    """
    try:
        if not body:
            return None

        # Try to parse as JSON (standard non-streaming response)
        if "application/json" in content_type or "text/event-stream" not in content_type:
            try:
                data = json.loads(body)
                return _extract_from_json(data)
            except (json.JSONDecodeError, UnicodeDecodeError):
                pass

        # Try to parse as SSE stream (concatenated chunks)
        return _extract_from_sse(body)

    except Exception as e:
        logger.debug(f"Failed to extract usage: {e}")
        return None


def _extract_from_json(data: dict) -> Optional[dict]:
    """Extract usage from a standard JSON response (OpenAI/Anthropic format)."""
    usage = data.get("usage")
    if not usage:
        return None

    model = data.get("model", "")
    result = {
        "model": model,
        "total_tokens": 0,
        "input_tokens": 0,
        "output_tokens": 0,
        "cache_creation_tokens": 0,
        "cache_read_tokens": 0,
    }

    # OpenAI format: prompt_tokens, completion_tokens
    if "prompt_tokens" in usage:
        result["input_tokens"] = usage.get("prompt_tokens", 0)
        result["output_tokens"] = usage.get("completion_tokens", 0)
        result["total_tokens"] = usage.get("total_tokens",
                                           result["input_tokens"] + result["output_tokens"])

    # Anthropic format: input_tokens, output_tokens
    elif "input_tokens" in usage:
        result["input_tokens"] = usage.get("input_tokens", 0)
        result["output_tokens"] = usage.get("output_tokens", 0)
        result["total_tokens"] = result["input_tokens"] + result["output_tokens"]

    # Cache tokens (OpenAI)
    cache_creation = usage.get("prompt_tokens_details", {}).get("cached_tokens", 0)
    cache_read = usage.get("prompt_tokens_details", {}).get("cached_tokens", 0)
    if cache_creation:
        result["cache_creation_tokens"] = cache_creation
    if cache_read:
        result["cache_read_tokens"] = cache_read

    # Cache tokens (Anthropic)
    cache_creation_input = usage.get("cache_creation_input_tokens", 0)
    cache_read_input = usage.get("cache_read_input_tokens", 0)
    if cache_creation_input:
        result["cache_creation_tokens"] = cache_creation_input
    if cache_read_input:
        result["cache_read_tokens"] = cache_read_input

    return result if result["total_tokens"] > 0 else None


def _extract_from_sse(body: bytes) -> Optional[dict]:
    """
    Extract usage from SSE stream by parsing all data: lines.
    Usage is typically in the final chunk.
    """
    try:
        text = body.decode("utf-8", errors="replace")
        last_usage = None

        for line in text.split("\n"):
            if line.startswith("data: ") and line.strip() != "data: [DONE]":
                try:
                    chunk = json.loads(line[6:])
                    if "usage" in chunk and chunk["usage"]:
                        last_usage = _extract_from_json(chunk)
                except (json.JSONDecodeError, KeyError):
                    continue

        return last_usage

    except Exception:
        return None


def _extract_from_ollama_native(body: bytes) -> Optional[dict]:
    """
    Extract usage from ollama's native API format (/api/generate, /api/chat).

    Non-streaming: single JSON with prompt_eval_count / eval_count at top level.
    Streaming: multiple JSON lines, final chunk has done=true with counts.

    Returns dict with keys: input_tokens, output_tokens, total_tokens, model.
    """
    try:
        text = body.decode("utf-8", errors="replace")
    except Exception:
        return None

    # Try non-streaming first (single JSON object)
    try:
        data = json.loads(text)
        return _extract_ollama_counts(data)
    except (json.JSONDecodeError, ValueError):
        pass

    # Streaming: multiple JSON lines, final chunk has the counts
    last_counts = None
    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue
        try:
            chunk = json.loads(line)
            if chunk.get("done"):
                last_counts = _extract_ollama_counts(chunk)
        except (json.JSONDecodeError, ValueError):
            continue

    return last_counts


def _extract_ollama_counts(data: dict) -> Optional[dict]:
    """Extract token counts from an ollama native API response dict."""
    prompt_count = data.get("prompt_eval_count", 0)
    eval_count = data.get("eval_count", 0)
    total = prompt_count + eval_count

    if total == 0:
        return None

    return {
        "model": data.get("model", "ollama"),
        "total_tokens": total,
        "input_tokens": prompt_count,
        "output_tokens": eval_count,
        "cache_creation_tokens": 0,
        "cache_read_tokens": 0,
    }


def _extract_usage_from_stream_chunks(chunks: list[bytes]) -> Optional[dict]:
    """
    Extract usage from collected streaming response chunks.
    Call this after streaming is complete to get the final usage.
    """
    combined = b"".join(chunks)
    return extract_usage_from_response(combined, "text/event-stream")


# ---------------------------------------------------------------------------
# Provider Detection
# ---------------------------------------------------------------------------

def detect_provider(upstream_url: str, model: str) -> str:
    """Detect provider name from upstream URL and model name."""
    url_lower = upstream_url.lower()
    model_lower = model.lower()

    if "openai" in url_lower or model_lower.startswith("gpt-"):
        return "openai"
    elif "anthropic" in url_lower or model_lower.startswith("claude-"):
        return "anthropic"
    elif "deepseek" in url_lower or model_lower.startswith("deepseek"):
        return "deepseek"
    elif "ollama" in url_lower or model_lower.startswith("llama"):
        return "ollama"
    elif "groq" in url_lower:
        return "groq"
    elif "together" in url_lower:
        return "together"
    elif "fireworks" in url_lower:
        return "fireworks"
    elif "mistral" in url_lower or model_lower.startswith("mistral"):
        return "mistral"
    elif "google" in url_lower or "generativelanguage" in url_lower:
        return "google"
    elif "zhipuai" in url_lower or model_lower.startswith("glm"):
        return "zhipuai"
    elif "xiaomi" in url_lower or model_lower.startswith("mimo"):
        return "xiaomi"
    else:
        return "auto-detected"


# ---------------------------------------------------------------------------
# Database Logging
# ---------------------------------------------------------------------------

def log_proxy_usage(
    db_path: str,
    agent_name: str,
    usage: dict,
    provider: str,
    upstream_url: str,
    turn_id: Optional[str] = None,
):
    """Log captured token usage to ObserveCo database."""
    try:
        from observeco.db import Database

        db = Database(db_path)
        turn_id = turn_id or f"proxy-{uuid.uuid4().hex[:12]}"

        # Compute cost via ObserveCo's pricing table
        total_tokens = usage.get("total_tokens", 0)
        cost = 0.0
        if provider and provider != "auto-detected":
            try:
                from observeco.tracking.tokens import compute_cost
                cost = compute_cost(total_tokens, provider)
            except Exception:
                pass

        db.log_token_turn(
            agent_name=agent_name,
            turn_id=turn_id,
            total_tokens=total_tokens,
            input_tokens=usage.get("input_tokens", 0),
            output_tokens=usage.get("output_tokens", 0),
            cache_creation_tokens=usage.get("cache_creation_tokens", 0),
            cache_read_tokens=usage.get("cache_read_tokens", 0),
            provider=provider,
            cost=cost,
            cost_computed="tiered" if cost > 0 else "flat",
            source="proxy",
        )
        logger.debug(
            f"Logged proxy usage: agent={agent_name} tokens={total_tokens} "
            f"cost=${cost:.4f} provider={provider}"
        )

    except Exception as e:
        logger.error(f"Failed to log proxy usage: {e}")


# ---------------------------------------------------------------------------
# Proxy Server
# ---------------------------------------------------------------------------

class ProxyServer:
    """
    Transparent API proxy for LLM providers.

    Forwards all /v1/* requests to the upstream provider.
    Supports multi-upstream routing via a routing table:
    {provider_name: upstream_url}. Auto-discovered from Hermes config.yaml.
    Captures token usage from responses and logs to ObserveCo DB.
    """

    def __init__(
        self,
        upstream_url: str = DEFAULT_UPSTREAM,
        port: int = DEFAULT_PORT,
        db_path: Optional[str] = None,
        agent_name: str = "proxy-agent",
        routing_table: Optional[dict[str, str]] = None,
    ):
        self.upstream_url = upstream_url.rstrip("/")
        self.default_upstream_url = self.upstream_url  # backup for unresolvable routes
        self.port = port
        self.db_path = db_path or self._default_db_path()
        self.agent_name = agent_name
        self.routing_table = routing_table or {}  # provider_name -> upstream_url
        # Build reverse lookup: first 16 chars of API key -> provider name
        self.auth_key_to_provider: dict[str, str] = {}
        self._load_api_key_mapping()
        self.client: Optional[httpx.AsyncClient] = None
        self._request_count = 0
        self._error_count = 0
        self._total_tokens_captured = 0

    @staticmethod
    def build_routing_table_from_config(config_path: Optional[str] = None) -> dict[str, str]:
        """Auto-discover routing table from Hermes config.yaml.

        Reads providers with _original_base_url and builds a map of
        provider_name -> original_upstream_url for cloud providers only.
        Localhost providers (ollama, llama.cpp) are excluded.
        """
        import yaml
        if config_path is None:
            hh = hermes_home()
            config_path = str(hh / "config.yaml") if hh else os.path.expanduser("~/.hermes/config.yaml")
        if not os.path.exists(config_path):
            return {}
        try:
            with open(config_path) as f:
                config = yaml.safe_load(f)
        except Exception:
            logger.warning(f"Could not parse Hermes config: {config_path}")
            return {}

        table = {}
        providers = config.get("providers", {})
        for name, prov in providers.items():
            orig = prov.get("_original_base_url", "")
            if not orig:
                continue
            # Skip local providers — they go through the local proxy (:9201)
            if "localhost" in orig or "127.0.0.1" in orig:
                continue
            # Strip trailing /v1 since the handler always appends /v1/... paths
            cleaned = orig.rstrip("/")
            if cleaned.endswith("/v1"):
                cleaned = cleaned[:-3]
            table[name] = cleaned

        if table:
            logger.info(f"Auto-discovered routing table: {len(table)} providers")
            for name, url in table.items():
                logger.debug(f"  {name} -> {url}")
        return table

    def _load_api_key_mapping(self) -> None:
        """Build auth_key_to_provider from Hermes config providers.

        Maps first 16 chars of each provider's API key to its provider name,
        so incoming requests can be routed by which API key they present.
        Checks both old (v0.14) and new (v0.16+) config paths.
        """
        import yaml
        hh = hermes_home()
        candidates = [
            str(hh / "config.yaml") if hh else os.path.expanduser("~/.hermes/config.yaml"),
            str(hh / "profiles" / "main" / "config.yaml") if hh else os.path.expanduser("~/.hermes/profiles/main/config.yaml"),
        ]
        for config_path in candidates:
            if not os.path.exists(config_path):
                continue
            try:
                with open(config_path) as f:
                    config = yaml.safe_load(f)
            except Exception:
                continue
            providers = config.get("providers", {})
            for name, prov in providers.items():
                api_key = prov.get("api_key", "")
                if api_key:
                    prefix = api_key[:16]
                    self.auth_key_to_provider[prefix] = name
                    logger.debug(f"API key mapping: {name} -> {prefix}...")
            if self.auth_key_to_provider:
                break  # found keys, stop looking

    def _resolve_upstream(self, body: bytes, headers: dict = None) -> str:
        """Determine the correct upstream URL for this request.

        1. If routing_table is empty, use default upstream_url (backward compatible).
        2. Read API key from Authorization header and match to provider by key prefix.
        3. Fall back to model-name-based routing for unknown API keys.

        Returns a base URL WITHOUT /v1 suffix — the caller always appends /v1/... paths.
        """
        if not self.routing_table:
            return self.upstream_url

        # Route by API key if we have auth_key_to_provider mappings
        if hasattr(self, 'auth_key_to_provider') and self.auth_key_to_provider and headers:
            auth_header = headers.get("authorization", "") or headers.get("Authorization", "")
            if auth_header.startswith("Bearer "):
                api_key = auth_header[7:].strip()
                key_prefix = api_key[:16]
                if key_prefix in self.auth_key_to_provider:
                    provider = self.auth_key_to_provider[key_prefix]
                    if provider in self.routing_table:
                        logger.debug(f"Routed via API key -> provider={provider}")
                        return self._strip_v1_suffix(self.routing_table[provider])

        # Fallback: model-name-based routing (for unknown API keys)
        model = ""
        try:
            if body:
                data = json.loads(body)
                model = data.get("model", "")
        except (json.JSONDecodeError, UnicodeDecodeError):
            pass

        if model:
            # Try direct model-to-provider mapping
            for prov_name, upstream in self.routing_table.items():
                if model.lower().startswith(prov_name.lower() + "-") or model.lower() == prov_name.lower():
                    logger.debug(f"Routed model={model} via name match -> provider={prov_name}")
                    return self._strip_v1_suffix(upstream)

        return self.default_upstream_url

    @staticmethod
    def _strip_v1_suffix(url: str) -> str:
        """Remove trailing /v1 so the handler can safely append /v1/... paths."""
        cleaned = url.rstrip("/")
        if cleaned.endswith("/v1"):
            cleaned = cleaned[:-3]
        return cleaned

    def _default_db_path(self) -> str:
        """Find ObserveCo database path."""
        from observeco.dirs import get_data_dir
        data_dir = get_data_dir()
        return os.path.join(data_dir, "observeco.db")

    async def start(self):
        """Initialize the HTTP client with connection pooling."""
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(REQUEST_TIMEOUT),
            limits=httpx.Limits(
                max_connections=100,
                max_keepalive_connections=20,
                keepalive_expiry=30,
            ),
            follow_redirects=True,
        )
        logger.info(
            f"Proxy started: localhost:{self.port} → {self.upstream_url} "
            f"(db={self.db_path})"
        )

    async def stop(self):
        """Close HTTP client gracefully."""
        if self.client:
            await self.client.aclose()
        logger.info(
            f"Proxy stopped. Stats: requests={self._request_count} "
            f"errors={self._error_count} tokens={self._total_tokens_captured}"
        )

    async def handle_request(self, request: Request) -> Response:
        """
        Core proxy handler. Forwards request to upstream, captures usage.
        """
        self._request_count += 1

        # Build upstream path
        path = request.url.path
        if path.startswith("/v1"):
            upstream_path = path  # /v1/chat/completions → /v1/chat/completions
        else:
            upstream_path = f"/v1{path}"  # /chat/completions → /v1/chat/completions

        # Forward headers (strip hop-by-hop headers)
        headers = {}
        for name, value in request.headers.items():
            if name.lower() not in STRIP_REQUEST_HEADERS:
                headers[name] = value

        # Read request body
        body = await request.body()

        # Detect if client requested streaming
        is_streaming = False
        if body:
            try:
                body_json = json.loads(body)
                is_streaming = body_json.get("stream", False)
            except (json.JSONDecodeError, UnicodeDecodeError):
                pass

        # Resolve upstream URL (multi-upstream routing)
        resolved_base = self._resolve_upstream(body, headers=headers)
        upstream_url = f"{resolved_base}{upstream_path}"
        if request.url.query:
            upstream_url += f"?{request.url.query}"

        # Forward request to upstream with retry
        start_time = time.monotonic()
        response = None

        for attempt in range(MAX_RETRIES + 1):
            try:
                if is_streaming:
                    response = await self._handle_streaming(
                        upstream_url, headers, body, request.method
                    )
                else:
                    response = await self._handle_normal(
                        upstream_url, headers, body, request.method
                    )
                break
            except httpx.ConnectError as e:
                self._error_count += 1
                if attempt < MAX_RETRIES:
                    logger.warning(
                        f"Upstream connect error (attempt {attempt + 1}): {e}"
                    )
                    await self._async_sleep(RETRY_DELAY * (attempt + 1))
                    continue
                # All retries exhausted
                logger.error(f"Upstream unreachable after {MAX_RETRIES + 1} attempts: {e}")
                return Response(
                    content=json.dumps({
                        "error": {
                            "message": f"Upstream provider unavailable: {self.upstream_url}",
                            "type": "proxy_error",
                            "code": "upstream_unreachable",
                        }
                    }),
                    status_code=502,
                    media_type="application/json",
                )
            except httpx.TimeoutException:
                self._error_count += 1
                if attempt < MAX_RETRIES:
                    logger.warning(f"Upstream timeout (attempt {attempt + 1})")
                    await self._async_sleep(RETRY_DELAY * (attempt + 1))
                    continue
                return Response(
                    content=json.dumps({
                        "error": {
                            "message": "Upstream request timed out",
                            "type": "proxy_error",
                            "code": "upstream_timeout",
                        }
                    }),
                    status_code=504,
                    media_type="application/json",
                )
            except Exception as e:
                self._error_count += 1
                logger.error(f"Unexpected proxy error: {e}")
                return Response(
                    content=json.dumps({
                        "error": {
                            "message": f"Proxy error: {str(e)}",
                            "type": "proxy_error",
                            "code": "internal_error",
                        }
                    }),
                    status_code=500,
                    media_type="application/json",
                )
        assert response is not None  # Guaranteed by loop above
        elapsed = time.monotonic() - start_time
        logger.debug(
            f"Proxied {request.method} {path} → {response.status_code} "
            f"({elapsed:.2f}s, streaming={is_streaming})"
        )

        return response

    async def _handle_normal(
        self, url: str, headers: dict, body: bytes, method: str
    ) -> Response | StreamingResponse:
        """Handle non-streaming request."""
        assert self.client is not None

        upstream_response = await self.client.request(
            method=method,
            url=url,
            headers=headers,
            content=body,
        )

        # Capture usage from response
        response_body = upstream_response.content
        content_type = upstream_response.headers.get("content-type", "")

        usage = extract_usage_from_response(response_body, content_type)
        if usage:
            provider = detect_provider(self.upstream_url, usage.get("model", ""))
            self._total_tokens_captured += usage.get("total_tokens", 0)
            # Log asynchronously (don't block the response)
            log_proxy_usage(
                db_path=self.db_path,
                agent_name=self.agent_name,
                usage=usage,
                provider=provider,
                upstream_url=self.upstream_url,
            )

        # Build response headers
        resp_headers = {}
        for name, value in upstream_response.headers.items():
            if name.lower() not in STRIP_RESPONSE_HEADERS:
                resp_headers[name] = value

        return Response(
            content=response_body,
            status_code=upstream_response.status_code,
            headers=resp_headers,
            media_type=content_type or "application/json",
        )

    async def _handle_streaming(
        self, url: str, headers: dict, body: bytes, method: str
    ) -> StreamingResponse:
        """Handle streaming (SSE) request. Captures usage from final chunk."""
        assert self.client is not None

        upstream_response = await self.client.request(
            method=method,
            url=url,
            headers=headers,
            content=body,
        )

        content_type = upstream_response.headers.get("content-type", "")
        resp_headers = {}
        for name, value in upstream_response.headers.items():
            if name.lower() not in STRIP_RESPONSE_HEADERS:
                resp_headers[name] = value

        if upstream_response.status_code >= 400:
            # Error response — not streaming, return as-is
            return Response(
                content=upstream_response.content,
                status_code=upstream_response.status_code,
                headers=resp_headers,
                media_type=content_type,
            )

        # Stream response while capturing chunks for usage extraction
        collected_chunks = []

        async def stream_with_capture():
            try:
                async for chunk in upstream_response.aiter_bytes():
                    collected_chunks.append(chunk)
                    yield chunk
            finally:
                # After streaming complete, extract usage from collected chunks
                if collected_chunks:
                    usage = _extract_usage_from_stream_chunks(collected_chunks)
                    if usage:
                        provider = detect_provider(
                            self.upstream_url, usage.get("model", "")
                        )
                        self._total_tokens_captured += usage.get("total_tokens", 0)
                        log_proxy_usage(
                            db_path=self.db_path,
                            agent_name=self.agent_name,
                            usage=usage,
                            provider=provider,
                            upstream_url=self.upstream_url,
                        )

        return StreamingResponse(
            stream_with_capture(),
            status_code=upstream_response.status_code,
            headers=resp_headers,
            media_type=content_type or "text/event-stream",
        )

    @staticmethod
    async def _async_sleep(seconds: float):
        """Async sleep for retry delay."""
        import asyncio
        await asyncio.sleep(seconds)

    def get_stats(self) -> dict:
        """Return proxy statistics."""
        return {
            "requests": self._request_count,
            "errors": self._error_count,
            "total_tokens_captured": self._total_tokens_captured,
            "upstream": self.upstream_url,
            "port": self.port,
        }


# ---------------------------------------------------------------------------
# Starlette App Factory
# ---------------------------------------------------------------------------

def create_app(
    upstream_url: str = DEFAULT_UPSTREAM,
    port: int = DEFAULT_PORT,
    db_path: Optional[str] = None,
    agent_name: str = "proxy-agent",
    routing_table: Optional[dict[str, str]] = None,
) -> Starlette:
    """Create the Starlette ASGI application for the proxy."""
    server = ProxyServer(
        upstream_url=upstream_url,
        port=port,
        db_path=db_path,
        agent_name=agent_name,
        routing_table=routing_table,
    )

    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def lifespan(app):
        await server.start()
        yield
        await server.stop()

    async def health(request: Request) -> Response:
        """Health check endpoint."""
        stats = server.get_stats()
        return Response(
            content=json.dumps({
                "status": "ok",
                "proxy": stats,
            }),
            media_type="application/json",
        )

    async def proxy_handler(request: Request) -> Response:
        """Catch-all handler for /v1/* routes."""
        return await server.handle_request(request)

    async def catchall(request: Request) -> Response:
        """Catch-all for non-/v1 routes — forward to upstream."""
        return await server.handle_request(request)

    app = Starlette(
        routes=[
            Route("/health", health, methods=["GET"]),
            Route("/v1/{path:path}", proxy_handler, methods=["GET", "POST", "PUT", "DELETE", "PATCH"]),
            Route("/{path:path}", catchall, methods=["GET", "POST", "PUT", "DELETE", "PATCH"]),
        ],
        lifespan=lifespan,
    )

    return app


# ---------------------------------------------------------------------------
# CLI Entry Point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="ObserveCo Transparent API Proxy"
    )
    parser.add_argument(
        "--port", type=int, default=DEFAULT_PORT,
        help=f"Port to listen on (default: {DEFAULT_PORT})"
    )
    parser.add_argument(
        "--upstream", type=str, default=DEFAULT_UPSTREAM,
        help=f"Upstream provider URL (default: {DEFAULT_UPSTREAM})"
    )
    parser.add_argument(
        "--db", type=str, default=None,
        help="Path to ObserveCo database (auto-detected if not set)"
    )
    parser.add_argument(
        "--agent", type=str, default="proxy-agent",
        help="Agent name for logging (default: proxy-agent)"
    )
    parser.add_argument(
        "--log-level", type=str, default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Log level (default: INFO)"
    )
    parser.add_argument(
        "--routing", type=str, default=None,
        help="JSON routing table: {\"provider_name\": \"upstream_url\"} (auto-discovered if not set)"
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Parse routing table from CLI arg, or auto-discover
    routing_table = None
    if args.routing:
        try:
            routing_table = json.loads(args.routing)
            if not isinstance(routing_table, dict):
                logger.warning("--routing must be a JSON object, ignoring")
                routing_table = None
        except json.JSONDecodeError as e:
            logger.warning(f"Invalid --routing JSON: {e}, using auto-discovery")
    if routing_table is None:
        routing_table = ProxyServer.build_routing_table_from_config()

    app = create_app(
        upstream_url=args.upstream,
        port=args.port,
        db_path=args.db,
        agent_name=args.agent,
        routing_table=routing_table,
    )

    logger.info(f"Starting ObserveCo Proxy on port {args.port}")
    uvicorn.run(app, host="0.0.0.0", port=args.port, log_level=args.log_level.lower())


if __name__ == "__main__":
    main()
