"""OpenTelemetry bridge — map OEF events to OTel spans.

Converts ObserveCo events into OpenTelemetry-compatible spans that can be
exported to any OTel backend (Datadog, Grafana, Jaeger, Zipkin).

Usage:
    from observeco.otel_bridge import OTelBridge

    bridge = OTelBridge(service_name="observeco")

    # Convert OEF event to OTel span
    span = bridge.event_to_span(oef_event)
    bridge.export_span(span)

    # Export multiple events
    bridge.export_events(events)
"""
from __future__ import annotations

import hashlib
import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Optional

from .adapters.oef import OEFEvent


@dataclass
class OTelSpan:
    """OpenTelemetry-compatible span."""
    trace_id: str
    span_id: str
    parent_span_id: Optional[str]
    name: str
    kind: str  # "internal", "server", "client", "producer", "consumer"
    start_time: int  # Unix nanoseconds
    end_time: Optional[int]
    status: str  # "OK", "ERROR", "UNSET"
    status_message: str = ""
    attributes: dict = field(default_factory=dict)
    events: list = field(default_factory=list)

    def to_dict(self) -> dict:
        result = {
            "traceId": self.trace_id,
            "spanId": self.span_id,
            "name": self.name,
            "kind": self.kind,
            "startTimeUnixNano": str(self.start_time),
            "status": {"code": self.status},
            "attributes": [
                {"key": k, "value": {"stringValue": str(v)}}
                for k, v in self.attributes.items()
            ],
        }
        if self.parent_span_id:
            result["parentSpanId"] = self.parent_span_id
        if self.end_time:
            result["endTimeUnixNano"] = str(self.end_time)
        if self.status_message:
            result["status"]["message"] = self.status_message
        if self.events:
            result["events"] = self.events
        return result


class OTelBridge:
    """Bridge between OEF events and OpenTelemetry spans."""

    def __init__(self, service_name: str = "observeco"):
        self.service_name = service_name
        self._spans: list[OTelSpan] = []

    def event_to_span(self, event: OEFEvent, parent_trace_id: str = None) -> OTelSpan:
        """Convert an OEF event to an OTel span."""
        trace_id = parent_trace_id or self._generate_trace_id(event)
        span_id = self._generate_span_id(event)

        # Parse timestamp to nanoseconds
        try:
            from datetime import datetime
            dt = datetime.fromisoformat(event.timestamp.replace("Z", "+00:00"))
            start_time = int(dt.timestamp() * 1e9)
        except Exception:
            start_time = int(time.time() * 1e9)

        # Map event type to span kind and name
        kind_map = {
            "tool_call": "client",
            "risk_alert": "internal",
            "error": "internal",
            "heartbeat": "internal",
            "feedback": "internal",
            "response": "internal",
        }

        name_map = {
            "tool_call": f"tool.{event.payload.get('tool_name', 'unknown')}",
            "risk_alert": f"risk.{event.payload.get('risk_level', 'unknown')}",
            "error": f"error.{event.payload.get('error_type', 'unknown')}",
            "heartbeat": "agent.heartbeat",
            "feedback": "user.feedback",
            "response": "agent.response",
        }

        # Map status
        status_map = {
            "tool_call": "OK" if event.payload.get("decision") != "deny" else "ERROR",
            "risk_alert": "OK",
            "error": "ERROR",
            "heartbeat": "OK",
            "feedback": "OK",
            "response": "OK",
        }

        # Build attributes
        attributes = {
            "service.name": self.service_name,
            "agent.id": event.agent_id,
            "agent.runtime": event.runtime,
            "event.channel": event.channel,
            "event.type": event.event_type,
            "event.id": event.event_id,
        }

        # Add event-specific attributes
        if event.event_type == "tool_call":
            attributes["tool.name"] = event.payload.get("tool_name", "")
            attributes["tool.args"] = json.dumps(event.payload.get("tool_args", {}))[:500]
            attributes["risk.level"] = event.payload.get("risk_level", "")
            attributes["risk.decision"] = event.payload.get("decision", "")

        elif event.event_type == "risk_alert":
            attributes["risk.level"] = event.payload.get("risk_level", "")
            attributes["risk.reason"] = event.payload.get("reason", "")
            attributes["risk.tool"] = event.payload.get("tool_name", "")

        elif event.event_type == "error":
            attributes["error.type"] = event.payload.get("error_type", "")
            attributes["error.message"] = event.payload.get("error_message", "")[:500]

        elif event.event_type == "heartbeat":
            attributes["heartbeat.status"] = event.payload.get("status", "")
            attributes["heartbeat.latency_ms"] = str(event.payload.get("latency_ms", 0))

        # Duration (for events with implicit duration)
        end_time = start_time + 1_000_000  # 1ms default

        return OTelSpan(
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=None,
            name=name_map.get(event.event_type, event.event_type),
            kind=kind_map.get(event.event_type, "internal"),
            start_time=start_time,
            end_time=end_time,
            status=status_map.get(event.event_type, "UNSET"),
            attributes=attributes,
        )

    def events_to_trace(self, events: list[OEFEvent]) -> dict:
        """Convert a list of OEF events to an OTel resourceSpans trace."""
        trace_id = self._generate_trace_id(events[0]) if events else self._random_id(32)

        spans = []
        for event in events:
            span = self.event_to_span(event, parent_trace_id=trace_id)
            spans.append(span.to_dict())

        return {
            "resourceSpans": [
                {
                    "resource": {
                        "attributes": [
                            {"key": "service.name", "value": {"stringValue": self.service_name}},
                        ]
                    },
                    "scopeSpans": [
                        {
                            "scope": {"name": "observeco", "version": "0.1.0"},
                            "spans": spans,
                        }
                    ],
                }
            ]
        }

    def export_events(self, events: list[OEFEvent]) -> dict:
        """Export OEF events as OTel trace."""
        return self.events_to_trace(events)

    def export_to_otlp(self, events: list[OEFEvent]) -> str:
        """Export events as OTLP JSON string."""
        trace = self.events_to_trace(events)
        return json.dumps(trace)

    def export_to_jaeger(self, events: list[OEFEvent]) -> list[dict]:
        """Export events in Jaeger-compatible format."""
        spans = []
        for event in events:
            span = self.event_to_span(event)
            jaeger_span = {
                "traceID": span.trace_id,
                "spanID": span.span_id,
                "parentSpanID": span.parent_span_id or "",
                "operationName": span.name,
                "startTime": span.start_time // 1000,  # Jaeger uses microseconds
                "duration": (span.end_time - span.start_time) // 1000 if span.end_time else 0,
                "tags": [
                    {"key": k, "value": str(v)}
                    for k, v in span.attributes.items()
                ],
                "process": {
                    "serviceName": self.service_name,
                    "tags": [],
                },
            }
            spans.append(jaeger_span)
        return {"data": [{"spans": spans}]}

    def _generate_trace_id(self, event: OEFEvent) -> str:
        """Generate a deterministic trace ID from event data."""
        raw = f"{event.agent_id}:{event.event_type}:{event.timestamp}"
        return hashlib.md5(raw.encode()).hexdigest().zfill(32)

    def _generate_span_id(self, event: OEFEvent) -> str:
        """Generate a deterministic span ID from event data."""
        raw = f"{event.event_id}:{event.agent_id}"
        return hashlib.md5(raw.encode()).hexdigest()[:16]

    def _random_id(self, length: int) -> str:
        """Generate a random hex ID."""
        return uuid.uuid4().hex[:length]
