from __future__ import annotations

import os
import re
import time
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import datetime, timezone

from .buffer import get_trace_buffer

TRACEPARENT_RE = re.compile(
    r"^(?P<version>[0-9a-f]{2})-(?P<trace_id>[0-9a-f]{32})-(?P<span_id>[0-9a-f]{16})-(?P<trace_flags>[0-9a-f]{2})$"
)


def generate_trace_id() -> str:
    return os.urandom(16).hex()


def generate_span_id() -> str:
    return os.urandom(8).hex()


def parse_traceparent(value: str | None) -> dict[str, str]:
    if not value:
        return {}
    match = TRACEPARENT_RE.match(value.strip())
    if not match:
        return {}
    return match.groupdict()


def format_traceparent(trace_id: str, span_id: str, trace_flags: str = "01") -> str:
    return f"00-{trace_id}-{span_id}-{trace_flags}"


@dataclass
class Span:
    name: str
    trace_id: str
    span_id: str = field(default_factory=generate_span_id)
    parent_span_id: str | None = None
    service: str = "browser-agent"
    start_time: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    end_time: str | None = None
    duration_ms: float | None = None
    status: str = "ok"
    attributes: dict = field(default_factory=dict)
    _start_monotonic: float = field(default_factory=time.monotonic, repr=False)
    _token: object = field(default=None, repr=False)

    def set_attribute(self, key: str, value: object) -> None:
        self.attributes[key] = value

    def finish(self, status: str | None = None) -> None:
        if self.end_time is not None:
            return
        if status:
            self.status = status
        elapsed = time.monotonic() - self._start_monotonic
        self.duration_ms = round(elapsed * 1000, 2)
        self.end_time = datetime.now(timezone.utc).isoformat()
        get_trace_buffer().record(self)

    def __enter__(self) -> Span:
        self._token = _current_span_var.set(self)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if exc_type is not None:
            self.status = "error"
            self.set_attribute("error.type", exc_type.__name__)
            self.set_attribute("error.message", str(exc_val))
        self.finish()
        if self._token is not None:
            _current_span_var.reset(self._token)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "service": self.service,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": self.duration_ms,
            "status": self.status,
            "attributes": dict(self.attributes),
        }


_current_span_var: ContextVar[Span | None] = ContextVar("browser_agent_current_span", default=None)


def get_current_span() -> Span | None:
    return _current_span_var.get()


def start_span(
    name: str,
    trace_id: str | None = None,
    parent_span_id: str | None = None,
    service: str = "browser-agent",
    attributes: dict | None = None,
) -> Span:
    current = get_current_span()
    if trace_id is None:
        trace_id = current.trace_id if current else generate_trace_id()
    if parent_span_id is None and current is not None:
        parent_span_id = current.span_id

    span = Span(
        name=name,
        trace_id=trace_id,
        parent_span_id=parent_span_id,
        service=service,
        attributes=dict(attributes or {}),
    )
    return span
