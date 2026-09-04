import pytest
from fastapi.testclient import TestClient

from browser_agent.app import create_app
from browser_agent.tracing import (
    Span,
    format_traceparent,
    generate_span_id,
    generate_trace_id,
    get_trace_buffer,
    parse_traceparent,
    start_span,
)


def test_w3c_traceparent_helpers():
    trace_id = generate_trace_id()
    span_id = generate_span_id()
    assert len(trace_id) == 32
    assert len(span_id) == 16

    header_val = format_traceparent(trace_id, span_id)
    assert header_val.startswith(f"00-{trace_id}-{span_id}-")

    parsed = parse_traceparent(header_val)
    assert parsed["trace_id"] == trace_id
    assert parsed["span_id"] == span_id
    assert parsed["version"] == "00"

    assert parse_traceparent(None) == {}
    assert parse_traceparent("invalid-traceparent") == {}


def test_span_lifecycle_and_buffer():
    buffer = get_trace_buffer()
    buffer.clear()

    trace_id = generate_trace_id()
    with start_span("test.parent", trace_id=trace_id) as parent:
        parent.set_attribute("env", "test")
        with start_span("test.child", trace_id=trace_id, parent_span_id=parent.span_id) as child:
            child.set_attribute("step", 1)

    spans = buffer.get_trace(trace_id)
    assert len(spans) == 2
    names = [s["name"] for s in spans]
    assert "test.parent" in names
    assert "test.child" in names

    child_span = next(s for s in spans if s["name"] == "test.child")
    assert child_span["parent_span_id"] is not None
    assert child_span["duration_ms"] is not None


def test_trace_lookup_api():
    import browser_agent.api as api

    class _FakeSession:
        def execute(self, stmt):
            class _Result:
                def scalars(self):
                    return self
                def all(self):
                    return []
            return _Result()
        def close(self):
            pass

    app = create_app()
    app.dependency_overrides[api.get_session] = lambda: _FakeSession()
    client = TestClient(app)
    buffer = get_trace_buffer()
    buffer.clear()

    trace_id = generate_trace_id()
    span = Span(
        name="api.mock",
        trace_id=trace_id,
        span_id=generate_span_id(),
        service="browser-agent",
        duration_ms=12.5,
    )
    buffer.record(span)

    # 401 without auth
    res_unauth = client.get(f"/v1/ops/traces/{trace_id}")
    assert res_unauth.status_code == 401

    # with operator token
    token_res = client.post("/v1/auth/local-token", json={"role": "operator"})
    token = token_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get(f"/v1/ops/traces/{trace_id}", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["trace_id"] == trace_id
    assert data["spans_count"] == 1
    assert data["spans"][0]["name"] == "api.mock"
