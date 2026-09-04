from __future__ import annotations

import re
import uuid
from contextvars import ContextVar
from dataclasses import dataclass, replace


TRACEPARENT_RE = re.compile(
    r"^(?P<version>[0-9a-f]{2})-(?P<trace_id>[0-9a-f]{32})-(?P<span_id>[0-9a-f]{16})-(?P<trace_flags>[0-9a-f]{2})$"
)

LOG_SCHEMA_FIELDS = [
    "correlation_id",
    "trace_id",
    "span_id",
    "parent_span_id",
    "request_id",
    "task_id",
    "tenant_id",
    "actor_email",
    "event_name",
    "service_name",
    "service_version",
    "environment",
]


@dataclass(frozen=True)
class RequestContext:
    correlation_id: str
    request_id: str
    trace_id: str | None = None
    span_id: str | None = None
    parent_span_id: str | None = None
    trace_flags: str | None = None
    task_id: str | None = None
    tenant_id: str | None = None
    actor_email: str | None = None
    service_name: str = "browser-agent"
    service_version: str = "1.1.0"
    environment: str = "local"

    def log_fields(self, event_name: str | None = None) -> dict:
        return {
            "correlation_id": self.correlation_id,
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "request_id": self.request_id,
            "task_id": self.task_id,
            "tenant_id": self.tenant_id,
            "actor_email": self.actor_email,
            "event_name": event_name,
            "service_name": self.service_name,
            "service_version": self.service_version,
            "environment": self.environment,
        }

    def trace_context(self) -> dict:
        return {
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "trace_flags": self.trace_flags,
        }


_current_context: ContextVar[RequestContext | None] = ContextVar("browser_agent_request_context", default=None)


def parse_traceparent(value: str | None) -> dict:
    if not value:
        return {}
    match = TRACEPARENT_RE.match(value.strip())
    if not match:
        return {}
    return match.groupdict()


def build_request_context(headers, settings) -> RequestContext:
    from .tracing import generate_span_id, generate_trace_id
    trace = parse_traceparent(headers.get("traceparent"))
    trace_id = trace.get("trace_id") or generate_trace_id()
    span_id = generate_span_id()
    return RequestContext(
        correlation_id=headers.get("X-Correlation-ID") or str(uuid.uuid4()),
        request_id=str(uuid.uuid4()),
        trace_id=trace_id,
        span_id=span_id,
        parent_span_id=trace.get("span_id"),
        trace_flags=trace.get("trace_flags") or "01",
        service_name=getattr(settings, "otel_service_name", None) or getattr(settings, "app_name", "browser-agent"),
        service_version=getattr(settings, "app_version", "1.1.0"),
        environment=getattr(settings, "app_env", "local"),
    )


def set_request_context(context: RequestContext):
    return _current_context.set(context)


def reset_request_context(token) -> None:
    _current_context.reset(token)


def get_request_context() -> RequestContext | None:
    return _current_context.get()


def update_request_context(**values) -> None:
    context = get_request_context()
    if context is None:
        return
    _current_context.set(replace(context, **values))


def request_context_payload() -> dict:
    context = get_request_context()
    if context is None:
        return {}
    return {
        "request_id": context.request_id,
        "trace_context": context.trace_context(),
    }
