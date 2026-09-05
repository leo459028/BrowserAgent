from __future__ import annotations

from collections import deque
from threading import Lock
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .tracer import Span


class TraceBuffer:
    def __init__(self, max_spans: int = 2000):
        self._max_spans = max_spans
        self._spans: deque[Span] = deque(maxlen=max_spans)
        self._lock = Lock()

    def record(self, span: Span) -> None:
        with self._lock:
            self._spans.append(span)
        try:
            from .exporter import get_otlp_exporter
            exporter = get_otlp_exporter()
            if exporter.enabled:
                exporter.enqueue(span)
        except Exception:
            pass

    def get_trace(self, trace_id: str) -> list[dict]:
        with self._lock:
            matched = [span.to_dict() for span in self._spans if span.trace_id == trace_id]
        matched.sort(key=lambda s: s.get("start_time", ""))
        return matched

    def clear(self) -> None:
        with self._lock:
            self._spans.clear()


_global_buffer: TraceBuffer | None = None


def get_trace_buffer() -> TraceBuffer:
    global _global_buffer
    if _global_buffer is None:
        _global_buffer = TraceBuffer()
    return _global_buffer
