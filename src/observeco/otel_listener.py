"""Standalone OTLP HTTP listener on port 4318.

Accepts OTel spans from any OpenInference/OpenLLMetry-instrumented agent
and stores them into the ObserveCo pulse.db.

Can run as:
  observeco otel start   — daemon mode
  observeco otel stop    — stop daemon
  observeco otel status  — is it running?
  observeco otel --once  — single-request server, then exit

Uses standard OTLP HTTP port 4318 (OTLP/HTTP) and 4317 (gRPC).
"""

from __future__ import annotations

import json
import logging
import os
import signal
import time
import uuid
from pathlib import Path
from typing import Optional

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from observeco.db import Database
from observeco.dirs import get_data_dir

logger = logging.getLogger(__name__)

# ponytail: lazy — evaluated at first call, not import time, so get_data_dir() failure
# doesn't crash the import.
_DATA_DIR: Path | None = None
_PID_PATH: Path | None = None
_LOG_PATH: Path | None = None


def _get_data_dir() -> Path:
    global _DATA_DIR, _PID_PATH, _LOG_PATH
    if _DATA_DIR is None:
        _DATA_DIR = get_data_dir()
        _PID_PATH = _DATA_DIR / ".otel_listener.pid"
        _LOG_PATH = _DATA_DIR / "otel_listener.log"
    return _DATA_DIR


def _get_pid_path() -> Path:
    _get_data_dir()
    return _PID_PATH  # type: ignore[return-value]


def _get_log_path() -> Path:
    _get_data_dir()
    return _LOG_PATH  # type: ignore[return-value]

app = FastAPI(title="ObserveCo OTel Listener")
db = Database()

# In-memory dedup set: prevents re-ingesting the same span on OTEL exporter retries.
# Bounded to avoid unbounded growth; reset when it exceeds the window.
_seen_spans: set[str] = set()
_SPAN_DEDUP_WINDOW = 50_000


@app.post("/v1/traces")
async def ingest_traces(request: Request):
    """OTLP HTTP endpoint — accept JSON trace payloads."""
    global _seen_spans
    try:
        body = await request.json()
    except json.JSONDecodeError:
        return JSONResponse({"error": "invalid JSON"}, status_code=400)

    if not body or "resourceSpans" not in body:
        return JSONResponse({"error": "missing resourceSpans"}, status_code=400)

    spans_ingested = 0
    spans_skipped = 0

    for resource_span in body.get("resourceSpans", []):
        resource_attrs = {}
        resource = resource_span.get("resource", {})
        for attr in resource.get("attributes", []):
            val = attr.get("value", {})
            resource_attrs[attr.get("key", "")] = (
                val.get("stringValue") or
                val.get("intValue") or
                val.get("doubleValue") or
                ""
            )

        agent_name = resource_attrs.get("service.name", "otel-agent")
        agent_framework = resource_attrs.get("telemetry.sdk.name", "opentelemetry")

        for scope_span in resource_span.get("scopeSpans", []):
            for span in scope_span.get("spans", []):
                span_name = span.get("name", "")
                # Use a unique fallback when spanId is absent so concurrent
                # spans in the same second don't collide.
                span_id = span.get("spanId", span.get("span_id", uuid.uuid4().hex[:16]))

                # Dedup: skip spans we've already ingested (exporter retries).
                dedup_key = f"{agent_name}:{span_id}"
                if dedup_key in _seen_spans:
                    spans_skipped += 1
                    continue
                _seen_spans.add(dedup_key)
                if len(_seen_spans) > _SPAN_DEDUP_WINDOW:
                    _seen_spans = set()

                status_code = span.get("status", {}).get("code", "UNSET")

                pulse_status = "alive"
                error_msg = ""
                if status_code == 2:  # OTel ERROR
                    pulse_status = "error"
                    error_msg = span.get("status", {}).get("message", "OTel span error")
                    db.log_error(
                        agent_name=agent_name,
                        error_type="otel_span_error",
                        message=f"{span_name}: {error_msg}",
                        severity="error",
                    )

                db.log_pulse(
                    agent_name=agent_name,
                    agent_framework=agent_framework,
                    status=pulse_status,
                    latency_ms=0,
                    error_message=error_msg,
                )

                # Extract token usage (OpenInference convention)
                # Store raw values — prefer int/double, fall back to string
                span_attrs = {}
                for attr in span.get("attributes", []):
                    val = attr.get("value", {})
                    key = attr.get("key", "")
                    if "intValue" in val:
                        span_attrs[key] = val["intValue"]  # keep as int
                    elif "doubleValue" in val:
                        span_attrs[key] = val["doubleValue"]  # keep as float
                    elif "stringValue" in val:
                        span_attrs[key] = val["stringValue"]
                    else:
                        span_attrs[key] = ""

                def _safe_int(v, default=0):
                    """Convert to int, handling str/int/float/None/empty."""
                    if isinstance(v, int):
                        return v
                    if isinstance(v, float):
                        return int(v)
                    try:
                        return int(v) if v not in (None, "") else default
                    except (ValueError, TypeError):
                        return default

                input_tokens = _safe_int(span_attrs.get("llm.usage.token_count.prompt", 0))
                output_tokens = _safe_int(span_attrs.get("llm.usage.token_count.completion", 0))
                if input_tokens or output_tokens:
                    # Provider is in span attrs from the Hermes OTEL plugin
                    provider = str(span_attrs.get("gen_ai.system", span_attrs.get("llm.provider", "unknown")))
                    model = str(span_attrs.get("gen_ai.request.model", span_attrs.get("llm.model_name", span_attrs.get("gen_ai.model", ""))))
                    cache_creation = _safe_int(span_attrs.get("llm.usage.cache_creation_input_tokens", 0))
                    cache_read = _safe_int(span_attrs.get("llm.usage.cache_read_input_tokens", 0))

                    # OpenInference/OpenLLMetry: llm.usage.token_count.prompt is the
                    # TOTAL prompt token count including the cache-read portion.
                    # Normalize to non-cached input only so all sources share the same
                    # DB convention (input_tokens = uncached prompt tokens), preventing
                    # double-counting in the chart formula:
                    #   total = input + output + cache_read + cache_creation
                    non_cached_input = max(0, input_tokens - cache_read)
                    true_total = non_cached_input + output_tokens + cache_creation + cache_read

                    # Existing: write to compress_log (uses original prompt+completion sum)
                    db.log_trim(
                        agent_name=agent_name,
                        identity=0,
                        skills=0,
                        memory=0,
                        tools=0,
                        guidance=0,
                        total=true_total,
                        savings=0,
                    )

                    db.log_token_turn(
                        agent_name=agent_name,
                        turn_id=f"otel_{span_id}",
                        total_tokens=true_total,
                        input_tokens=non_cached_input,
                        output_tokens=output_tokens,
                        cache_creation_tokens=cache_creation,
                        cache_read_tokens=cache_read,
                        provider=provider,
                        source="otel",
                        model=model,
                    )

                spans_ingested += 1

    return JSONResponse({
        "status": "ok",
        "spans_ingested": spans_ingested,
        "spans_skipped_duplicate": spans_skipped,
    })


@app.get("/health")
async def health():
    return JSONResponse({"status": "ok", "port": 4318})


@app.get("/v1/health")
async def otel_health():
    return JSONResponse({"status": "ok"})


# ── Daemon management ──────────────────────────────────────────────────────


def _pid_file() -> Optional[int]:
    try:
        return int(_get_pid_path().read_text().strip())
    except (FileNotFoundError, ValueError, OSError):
        return None


def _is_pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False


def status() -> dict:
    pid = _pid_file()
    alive = pid is not None and _is_pid_alive(pid)
    return {"running": alive, "pid": pid, "log_path": str(_get_log_path())}


def start(port: int = 4318) -> None:
    """Start the OTel listener as a background daemon process."""
    current = status()
    if current["running"]:
        print(f"OTel listener already running (PID {current['pid']}).")
        return

    import platform
    import sys

    if platform.system() == "Windows":
        # Windows: use subprocess with CREATE_NEW_PROCESS_GROUP
        import subprocess
        creation_flags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
        process = subprocess.Popen(
            [sys.executable, "-c",
             f"from observeco.otel_listener import _run_server; _run_server({port})"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            creationflags=creation_flags,
        )
        _get_pid_path().write_text(str(process.pid))
        print(f"OTel listener started on port {port} (PID {process.pid}).")
    else:
        # Unix: double-fork daemon
        try:
            pid = os.fork()
        except (OSError, AttributeError) as e:
            print(f"Could not start OTel listener: {e}")
            return

        if pid > 0:
            _get_pid_path().write_text(str(pid))
            print(f"OTel listener started on port {port} (PID {pid}).")
            return

        try:
            os.setsid()
        except OSError:
            os._exit(1)

        try:
            pid2 = os.fork()
        except OSError:
            os._exit(1)
        if pid2 > 0:
            os._exit(0)

        try:
            devnull = os.open(os.devnull, os.O_RDWR)
            log_fd = os.open(str(_get_log_path()), os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
            os.dup2(devnull, 0)   # stdin → /dev/null
            os.dup2(log_fd, 1)    # stdout → log file
            os.dup2(log_fd, 2)    # stderr → log file (captures uvicorn errors)
            os.close(devnull)
            os.close(log_fd)
        except OSError:
            pass

        _PID_PATH.write_text(str(os.getpid()))
        _run_server(port=port)


def stop() -> None:
    """Stop the OTel listener."""
    current = status()
    if not current["running"]:
        print("OTel listener is not running.")
        return

    pid = current["pid"]
    print(f"Stopping OTel listener (PID {pid})...")
    os.kill(pid, signal.SIGTERM)
    for _ in range(50):
        time.sleep(0.1)
        if not _is_pid_alive(pid):
            break
    if _is_pid_alive(pid):
        try:
            os.kill(pid, signal.SIGKILL)
        except OSError:
            pass
    _PID_PATH.unlink(missing_ok=True)
    print("OTel listener stopped.")


def _run_server(port: int = 4318) -> None:
    """Run the FastAPI server (called in daemon child process)."""
    try:
        uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")
    except Exception:  # noqa: BLE001
        # Write crash reason to log file before exiting so the stopped-bridge
        # failure mode is diagnosable (previously swallowed by /dev/null).
        try:
            with open(str(_LOG_PATH), "a") as f:
                import traceback
                f.write(f"\n[otel_listener crash] port={port}\n")
                traceback.print_exc(file=f)
        except OSError:
            pass
        raise


def _daemon_entry(port: int) -> None:
    """Entry point for daemon process (must be module-level for pickling)."""
    try:
        devnull = os.open(os.devnull, os.O_RDWR)
        log_fd = os.open(str(_LOG_PATH), os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
        os.dup2(devnull, 0)
        os.dup2(log_fd, 1)
        os.dup2(log_fd, 2)
        os.close(devnull)
        os.close(log_fd)
    except OSError:
        pass

    _PID_PATH.write_text(str(os.getpid()))
    _run_server(port=port)


def run_once(port: int = 4318) -> None:
    """Run server in foreground (for testing)."""
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")


# ── CLI entry point ────────────────────────────────────────────────────────


def cli_main(args: list[str]) -> None:
    """Handle CLI subcommands for the OTel listener."""
    if not args:
        print("Usage: observeco otel [start|stop|status|--once]")
        return

    cmd = args[0]
    port = 4318
    if len(args) > 1 and args[1].isdigit():
        port = int(args[1])

    if cmd == "start":
        start(port=port)
    elif cmd == "stop":
        stop()
    elif cmd == "status":
        s = status()
        if s["running"]:
            print(f"OTel listener running (PID {s['pid']}) on port {port}.")
        else:
            print("OTel listener not running.")
    elif cmd == "--once":
        run_once(port=port)
    else:
        print(f"Unknown command: {cmd}")
        print("Usage: observeco otel [start|stop|status|--once]")
