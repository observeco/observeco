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
from typing import Optional

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from observeco.db import Database
from observeco.dirs import get_data_dir

logger = logging.getLogger(__name__)

_DATA_DIR = get_data_dir()
_PID_PATH = _DATA_DIR / ".otel_listener.pid"

app = FastAPI(title="ObserveCo OTel Listener")
db = Database()


@app.post("/v1/traces")
async def ingest_traces(request: Request):
    """OTLP HTTP endpoint — accept JSON trace payloads."""
    try:
        body = await request.json()
    except json.JSONDecodeError:
        return JSONResponse({"error": "invalid JSON"}, status_code=400)

    if not body or "resourceSpans" not in body:
        return JSONResponse({"error": "missing resourceSpans"}, status_code=400)

    spans_ingested = 0

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
                span_attrs = {}
                for attr in span.get("attributes", []):
                    val = attr.get("value", {})
                    span_attrs[attr.get("key", "")] = str(
                        val.get("stringValue") or
                        val.get("intValue") or
                        val.get("doubleValue") or
                        ""
                    )

                input_tokens = int(span_attrs.get("llm.usage.token_count.prompt", 0))
                output_tokens = int(span_attrs.get("llm.usage.token_count.completion", 0))
                if input_tokens or output_tokens:
                    db.log_trim(
                        agent_name=agent_name,
                        identity=0,
                        skills=0,
                        memory=0,
                        tools=0,
                        guidance=0,
                        total=input_tokens + output_tokens,
                        savings=0,
                    )

                spans_ingested += 1

    return JSONResponse({
        "status": "ok",
        "spans_ingested": spans_ingested,
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
        return int(_PID_PATH.read_text().strip())
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
    return {"running": alive, "pid": pid}


def start(port: int = 4318) -> None:
    """Start the OTel listener as a background daemon process."""
    current = status()
    if current["running"]:
        print(f"OTel listener already running (PID {current['pid']}).")
        return

    # Fork daemon
    try:
        pid = os.fork()
    except (OSError, AttributeError) as e:
        print(f"Could not start OTel listener: {e}")
        return

    if pid > 0:
        _PID_PATH.write_text(str(pid))
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
        os.dup2(devnull, 0)
        os.dup2(devnull, 1)
        os.dup2(devnull, 2)
        os.close(devnull)
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
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")


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
