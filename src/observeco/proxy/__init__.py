"""
ObserveCo Transparent API Proxy — Task 4.1 + 4.2 + 4.3

Sits between LLM agents and providers (OpenAI, Anthropic, etc.).
Captures token usage from responses, logs to token_logs with source='proxy'.
Zero code changes required — agents point base_url at proxy.

Architecture:
  Agent → localhost:9200/v1/* → Proxy → api.openai.com/v1/*
                        ↓ captures usage from response
                  ObserveCo DB (source='proxy')

Run:
  python -m observeco.proxy.server --port 9200
  # or
  observeco proxy --port 9200
"""

from .server import ProxyServer, create_app

__all__ = ["ProxyServer", "create_app"]
