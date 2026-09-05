from __future__ import annotations

import httpx
from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient

from browser_agent.api import create_app
from browser_agent.auth import create_access_token, local_dev_actor_for_role
from browser_agent.tracing import (
    Span,
    get_trace_buffer,
    get_otlp_exporter,
)
from browser_agent.tracing.exporter import OtlpBatchSpanExporter


def test_otlp_exporter_enqueue_and_batch_flush():
    exporter = OtlpBatchSpanExporter(
        endpoint="http://fake-collector:4318/v1/traces",
        service_name="test-service",
        batch_size=10,
        enabled=True,
    )

    span = Span(name="test.span", trace_id="1" * 32, span_id="2" * 16)
    span.finish()
    exporter.enqueue(span)

    assert exporter.status()["queue_size"] == 1

    with patch("httpx.post") as mock_post:
        mock_post.return_value = MagicMock(status_code=200, text="OK")
        res = exporter.flush()
        assert res["exported"] == 1
        assert res["success"] is True
        assert exporter.status()["queue_size"] == 0
        assert exporter.status()["exported_spans_count"] == 1


def test_otlp_api_status_and_flush():
    app = create_app()
    client = TestClient(app)
    admin_token = create_access_token(local_dev_actor_for_role("admin"))
    headers = {"Authorization": f"Bearer {admin_token}"}

    # 1. 查詢狀態
    res = client.get("/v1/ops/otlp/status", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "queue_size" in data
    assert "exported_spans_count" in data

    # 2. 手動 flush
    res_flush = client.post("/v1/ops/otlp/flush", headers=headers)
    assert res_flush.status_code == 200
    flush_data = res_flush.json()
    assert flush_data["flushed"] is True
