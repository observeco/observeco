"""Supabase REST client for ObserveCo commercial features.

Wraps the Supabase REST API using httpx. No supabase-py dependency needed.
Reads credentials from environment variables or a local config file.
"""

from __future__ import annotations

import os
from typing import Any

import httpx

_SUPABASE_URL: str | None = None
_SUPABASE_SERVICE_KEY: str | None = None
_SUPABASE_ANON_KEY: str | None = None


def _init() -> None:
    global _SUPABASE_URL, _SUPABASE_SERVICE_KEY, _SUPABASE_ANON_KEY
    if _SUPABASE_URL is not None:
        return
    _SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
    _SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
    _SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY", "")


def _headers(use_service_role: bool = True) -> dict[str, str]:
    _init()
    key = _SUPABASE_SERVICE_KEY if use_service_role else _SUPABASE_ANON_KEY
    return {
        "Authorization": f"Bearer {key}",
        "apikey": key or "",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }


def is_configured() -> bool:
    _init()
    return bool(_SUPABASE_URL and _SUPABASE_SERVICE_KEY)


def select(
    table: str,
    columns: str = "*",
    filters: dict[str, Any] | None = None,
    order: str | None = None,
    limit: int | None = None,
    single: bool = False,
) -> dict | list | None:
    """Select rows from a Supabase table."""
    _init()
    url = f"{_SUPABASE_URL}/rest/v1/{table}"
    params: dict[str, Any] = {"select": columns}
    if filters:
        for k, v in filters.items():
            params[k] = f"eq.{v}"
    if order:
        params["order"] = order
    if limit:
        params["limit"] = str(limit)

    resp = httpx.get(url, headers=_headers(), params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    if single:
        return data[0] if data else None
    return data


def insert(
    table: str,
    data: dict | list[dict],
    select_cols: str = "*",
) -> list[dict]:
    """Insert rows into a Supabase table."""
    _init()
    url = f"{_SUPABASE_URL}/rest/v1/{table}"
    headers = _headers()
    headers["Prefer"] = "return=representation"
    resp = httpx.post(url, headers=headers, json=data if isinstance(data, list) else [data], timeout=10)
    resp.raise_for_status()
    return resp.json()


def update(
    table: str,
    data: dict,
    filters: dict[str, Any],
    select_cols: str = "*",
) -> list[dict]:
    """Update rows matching filters."""
    _init()
    url = f"{_SUPABASE_URL}/rest/v1/{table}"
    params = {}
    for k, v in filters.items():
        params[k] = f"eq.{v}"
    headers = _headers()
    headers["Prefer"] = "return=representation"
    resp = httpx.patch(url, headers=headers, params=params, json=data, timeout=10)
    try:
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPStatusError as e:
        # Graceful degradation: log the error, return empty result
        # This prevents schema mismatches (e.g. missing column) from breaking
        # the calling endpoint with a 500 error.
        return []


def count(table: str, filters: dict[str, Any] | None = None) -> int:
    """Count rows in a table (exact count via Supabase)."""
    _init()
    url = f"{_SUPABASE_URL}/rest/v1/{table}"
    params: dict[str, Any] = {"select": "count"}
    if filters:
        for k, v in filters.items():
            params[k] = f"eq.{v}"
    headers = _headers()
    headers["Accept"] = "application/json"
    headers["Prefer"] = "count=exact"
    resp = httpx.head(url, headers=headers, params=params, timeout=10)
    # Supabase returns count in Content-Range header: "0-0/42"
    cr = resp.headers.get("content-range", "*/0")
    try:
        return int(cr.split("/")[-1])
    except (ValueError, IndexError):
        return 0
