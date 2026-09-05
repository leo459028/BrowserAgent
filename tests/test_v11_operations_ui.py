from fastapi.testclient import TestClient

from browser_agent.api import create_app


def test_operations_route_renders_v11_production_and_observability_panels():
    client = TestClient(create_app())

    response = client.get("/operations")

    assert response.status_code == 200
    assert ("Browser Agent v1.1 Operations Center" in response.text or "Browser Agent v1.2 Operations Center" in response.text)
    assert "Production Readiness" in response.text
    assert "Observability" in response.text
    assert "Production Alerting Center" in response.text
    assert "system-alert-badge" in response.text
    assert "Visual Step Replay" in response.text
    assert "Trace Inspector" in response.text
    assert "External bearer token" in response.text
    assert "OTEL-ready" in response.text
    assert "demo" not in response.text.lower()

