from fastapi.testclient import TestClient

from browser_agent.api import create_app


def test_operations_route_renders_v10_operations_center():
    client = TestClient(create_app())

    response = client.get("/operations")

    assert response.status_code == 200
    assert "Browser Agent v1.0 Operations Center" in response.text
    assert "Operations Readiness" in response.text
    assert "Artifact Backend" in response.text
    assert "Bulk DLQ" in response.text
    assert "Replay Timeline" in response.text
    assert "Register built-in skills" in response.text
    assert "demo" not in response.text.lower()


def test_legacy_dashboard_route_is_not_the_v10_entrypoint():
    client = TestClient(create_app())

    response = client.get("/demo")

    assert response.status_code == 404
