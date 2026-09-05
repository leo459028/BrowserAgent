from __future__ import annotations

import json
import logging
import threading
import time
from collections import deque
from datetime import datetime, timezone
from typing import Any

import httpx

from .tracer import Span

logger = logging.getLogger(__name__)


class OtlpBatchSpanExporter:
    def __init__(
        self,
        endpoint: str = "",
        service_name: str = "browser-agent",
        batch_size: int = 50,
        flush_interval_seconds: float = 5.0,
        enabled: bool = False,
    ):
        self.endpoint = endpoint
        self.service_name = service_name
        self.batch_size = batch_size
        self.flush_interval_seconds = flush_interval_seconds
        self.enabled = bool(enabled and endpoint)

        self._queue: deque[dict[str, Any]] = deque(maxlen=5000)
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._worker_thread: threading.Thread | None = None

        self.exported_spans_count: int = 0
        self.failed_spans_count: int = 0
        self.last_export_time: str | None = None
        self.last_status: str = "active" if self.enabled else "disabled"

        if self.enabled:
            self._start()

    def _start(self) -> None:
        if self._worker_thread is None or not self._worker_thread.is_alive():
            self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True, name="otlp-exporter-worker")
            self._worker_thread.start()

    def _worker_loop(self) -> None:
        while not self._stop_event.is_set():
            time.sleep(self.flush_interval_seconds)
            self.flush()

    def enqueue(self, span: Span) -> None:
        if not self.enabled:
            return
        with self._lock:
            self._queue.append(span.to_dict())

    def flush(self) -> dict[str, Any]:
        spans_to_export = []
        with self._lock:
            while self._queue and len(spans_to_export) < self.batch_size:
                spans_to_export.append(self._queue.popleft())

        if not spans_to_export:
            return {"exported": 0, "status": "empty"}

        payload = self._build_otlp_payload(spans_to_export)
        success = False
        try:
            headers = {"Content-Type": "application/json"}
            resp = httpx.post(self.endpoint, json=payload, headers=headers, timeout=3.0)
            if resp.status_code in (200, 202):
                success = True
                self.exported_spans_count += len(spans_to_export)
                self.last_status = "ok"
            else:
                self.failed_spans_count += len(spans_to_export)
                self.last_status = f"error_{resp.status_code}"
                logger.warning(f"OTLP export returned HTTP {resp.status_code}: {resp.text[:200]}")
        except Exception as exc:
            self.failed_spans_count += len(spans_to_export)
            self.last_status = f"network_error: {exc}"
            logger.debug(f"Failed to export spans to OTLP endpoint: {exc}")

        self.last_export_time = datetime.now(timezone.utc).isoformat()
        return {
            "exported": len(spans_to_export) if success else 0,
            "success": success,
            "status": self.last_status,
        }

    def _build_otlp_payload(self, spans: list[dict[str, Any]]) -> dict[str, Any]:
        otlp_spans = []
        for s in spans:
            otlp_spans.append({
                "traceId": s.get("trace_id", ""),
                "spanId": s.get("span_id", ""),
                "parentSpanId": s.get("parent_span_id") or "",
                "name": s.get("name", "span"),
                "startTimeUnixNano": self._iso_to_unix_nano(s.get("start_time")),
                "endTimeUnixNano": self._iso_to_unix_nano(s.get("end_time")),
                "status": {"code": 1 if s.get("status") == "ok" else 2},
                "attributes": [
                    {"key": k, "value": {"stringValue": str(v)}}
                    for k, v in (s.get("attributes") or {}).items()
                ],
            })

        return {
            "resourceSpans": [
                {
                    "resource": {
                        "attributes": [
                            {"key": "service.name", "value": {"stringValue": self.service_name}}
                        ]
                    },
                    "scopeSpans": [
                        {
                            "scope": {"name": "browser-agent-tracer", "version": "1.2.0"},
                            "spans": otlp_spans,
                        }
                    ],
                }
            ]
        }

    @staticmethod
    def _iso_to_unix_nano(iso_str: str | None) -> int:
        if not iso_str:
            return int(time.time() * 1e9)
        try:
            dt = datetime.fromisoformat(iso_str)
            return int(dt.timestamp() * 1e9)
        except Exception:
            return int(time.time() * 1e9)

    def status(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "endpoint": self.endpoint,
            "service_name": self.service_name,
            "queue_size": len(self._queue),
            "exported_spans_count": self.exported_spans_count,
            "failed_spans_count": self.failed_spans_count,
            "last_export_time": self.last_export_time,
            "last_status": self.last_status,
        }

    def close(self) -> None:
        self._stop_event.set()
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=1.0)


_global_exporter: OtlpBatchSpanExporter | None = None


def get_otlp_exporter(settings=None) -> OtlpBatchSpanExporter:
    global _global_exporter
    if _global_exporter is None:
        if settings is None:
            from ..config import get_settings
            settings = get_settings()
        endpoint = getattr(settings, "otel_exporter_otlp_endpoint", "")
        service_name = getattr(settings, "otel_service_name", "browser-agent")
        enabled = getattr(settings, "otel_enabled", False) and bool(endpoint)
        _global_exporter = OtlpBatchSpanExporter(
            endpoint=endpoint,
            service_name=service_name,
            enabled=enabled,
        )
    return _global_exporter
