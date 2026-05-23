"""OpenTelemetry trace ingestion endpoint (OTLP JSON).

Accepts standard OTLP JSON traces at POST /v1/traces.
Maps span attributes to pulse_log and error tables.
Compatible with any OTel-instrumented agent framework.
"""

from __future__ import annotations

import json
import time
from typing import Optional

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from observeco.db import Database

router = APIRouter()
db = Database()


@router.post("/v1/traces")
async def ingest_traces(request: Request):
    """Accept OTLP JSON traces and map to ObserveCo data model."""
    try:
        body = await request.json()
    except json.JSONDecodeError:
        return JSONResponse({"error": "invalid JSON"}, status_code=400)

    if not body or "resourceSpans" not in body:
        return JSONResponse({"error": "missing resourceSpans"}, status_code=400)

    now = int(time.time())
    spans_ingested = 0

    for resource_span in body.get("resourceSpans", []):
        resource_attrs = {}
        resource = resource_span.get("resource", {})
        for attr in resource.get("attributes", []):
            resource_attrs[attr.get("key", "")] = attr.get("value", {}).get("stringValue", "")

        agent_name = (
            resource_attrs.get("service.name", "unknown")
            .replace("service.name", "")
            .strip()
        )
        if not agent_name:
            agent_name = "otel-agent"

        agent_framework = resource_attrs.get("telemetry.sdk.name", "opentelemetry")

        for scope_span in resource_span.get("scopeSpans", []):
            for span in scope_span.get("spans", []):
                span_id = span.get("spanId", "unknown")
                span_name = span.get("name", "")
                status_code = span.get("status", {}).get("code", "UNSET")
                span_kind = span.get("kind", 0)

                # Map OTel status to pulse status
                pulse_status = "alive"
                error_msg = ""
                if status_code == 2:  # ERROR
                    pulse_status = "error"
                    error_msg = span.get("status", {}).get("message", "OTel span error")
                    db.log_error(
                        agent_name=agent_name,
                        error_type="otel_span_error",
                        error_message=f"{span_name}: {error_msg}",
                        severity="error",
                    )

                # Record pulse
                db.log_pulse(
                    agent_name=agent_name,
                    agent_framework=agent_framework,
                    status=pulse_status,
                    latency_ms=0,
                )

                # Extract token usage if present (OpenInference convention)
                span_attrs = {}
                for attr in span.get("attributes", []):
                    key = attr.get("key", "")
                    val = attr.get("value", {})
                    # OTel attributes can be stringValue, intValue, doubleValue
                    actual = val.get("stringValue") or val.get("intValue") or val.get("doubleValue") or ""
                    span_attrs[key] = str(actual)

                # Track LLM token usage if available
                input_tokens = int(span_attrs.get("llm.usage.token_count.prompt", 0))
                output_tokens = int(span_attrs.get("llm.usage.token_count.completion", 0))
                if input_tokens or output_tokens:
                    db.log_trim(
                        agent_name=agent_name,
                        identity_tokens=0,
                        skills_tokens=0,
                        memory_tokens=0,
                        tools_tokens=0,
                        guidance_tokens=0,
                        total_tokens=input_tokens + output_tokens,
                        savings_ratio=0,
                    )

                spans_ingested += 1

    return JSONResponse({
        "status": "ok",
        "spans_ingested": spans_ingested,
    })


@router.get("/health")
async def health():
    return JSONResponse({"status": "ok"})
