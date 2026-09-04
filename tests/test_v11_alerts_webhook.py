from __future__ import annotations

from types import SimpleNamespace
from fastapi.testclient import TestClient

import browser_agent.api as api
from browser_agent.alerts import dispatch_alert_webhook, evaluate_alerts
from browser_agent.api import create_app
from browser_agent.auth import create_access_token, local_dev_actor_for_role


class _FakeAlertSession:
    def __init__(self, failed_tasks=None):
        self.failed_tasks = failed_tasks or []
        self.audit_entries = []

    def execute(self, statement):
        return _FakeResult(self.failed_tasks)

    def add(self, entity):
        self.audit_entries.append(entity)

    def commit(self):
        pass

    def close(self):
        pass


class _FakeResult:
    def __init__(self, rows):
        self.rows = rows

    def scalars(self):
        return self

    def all(self):
        return self.rows


def test_evaluate_alerts_logic():
    settings = SimpleNamespace(
        alert_webhook_url="",
        alert_dlq_threshold=5,
        alert_auth_failures_threshold=10,
        alert_quarantine_threshold=3,
        artifact_backend="local",
        reliability_store="memory",
    )
    session = _FakeAlertSession()
    data = evaluate_alerts(session, settings)
    assert data["status"] in {"healthy", "warning", "critical"}
    assert "rules" in data
    assert len(data["rules"]) == 7
    rule_ids = {r["id"] for r in data["rules"]}
    assert {
        "api_health",
        "database_health",
        "dlq_threshold",
        "auth_failure_spike",
        "quarantine_spike",
        "reliability_store",
        "artifact_storage",
    } == rule_ids


def test_alerts_api_and_permissions():
    app = create_app()
    session = _FakeAlertSession()
    app.dependency_overrides[api.get_session] = lambda: session
    client = TestClient(app)

    # 401 without auth
    res = client.get("/v1/ops/alerts")
    assert res.status_code == 401

    # creator cannot read alerts (403)
    creator_token = create_access_token(local_dev_actor_for_role("creator"))
    res_creator = client.get("/v1/ops/alerts", headers={"Authorization": f"Bearer {creator_token}"})
    assert res_creator.status_code == 403

    # operator can read alerts
    operator_token = create_access_token(local_dev_actor_for_role("operator"))
    headers = {"Authorization": f"Bearer {operator_token}"}
    res_ops = client.get("/v1/ops/alerts", headers=headers)
    assert res_ops.status_code == 200
    body = res_ops.json()
    assert "status" in body
    assert len(body["rules"]) == 7


def test_alert_test_dispatch():
    app = create_app()
    session = _FakeAlertSession()
    app.dependency_overrides[api.get_session] = lambda: session
    client = TestClient(app)

    operator_token = create_access_token(local_dev_actor_for_role("operator"))
    headers = {"Authorization": f"Bearer {operator_token}"}

    payload = {"rule_id": "dlq_threshold", "note": "Simulation alert for pytest", "level": "warning"}
    res = client.post("/v1/ops/alerts/test-dispatch", json=payload, headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["dispatched"] is True
    assert data["rule_id"] == "dlq_threshold"
    assert data["dispatched_by"] == "operator@example.com"
    assert len(session.audit_entries) == 1


def test_webhook_nonblocking_resilience():
    from unittest.mock import patch
    import urllib.error

    settings = SimpleNamespace(alert_webhook_url="")
    assert dispatch_alert_webhook("test_rule", "note", settings) is False

    mock_settings = SimpleNamespace(
        alert_webhook_url="https://hooks.slack.com/services/mock",
        alert_webhook_timeout_seconds=0.5,
        app_name="browser-agent",
        app_env="test",
    )
    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("mock network error")):
        dispatched = dispatch_alert_webhook("test_rule", "resilience test", mock_settings)
        assert dispatched is True

