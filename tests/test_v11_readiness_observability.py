from __future__ import annotations

from types import SimpleNamespace

from fastapi.testclient import TestClient

import browser_agent.api as api
from browser_agent.api import create_app
from browser_agent.auth import create_access_token, local_dev_actor_for_role


def test_production_readiness_reports_ready_for_hardened_compose_settings(monkeypatch):
    monkeypatch.setattr(api, "get_settings", lambda: _settings())
    monkeypatch.setattr(api, "get_reliability_store", lambda settings=None: _ReadyStore(), raising=False)
    app = create_app()
    app.dependency_overrides[api.get_session] = lambda: _ReadySession()
    client = TestClient(app)

    response = client.get("/v1/ops/readiness", headers=_auth("operator"))

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert body["app"]["version"] == "1.1.0"
    assert body["production"]["status"] == "ready"
    assert body["production"]["checks"]["local_tokens_disabled"]["status"] == "pass"
    assert body["production"]["checks"]["jwks_or_oidc_configured"]["status"] == "pass"
    assert body["observability"]["otel_ready"] is True
    assert body["observability"]["otel_enabled"] is False
    assert "correlation_id" in body["observability"]["log_schema_fields"]


def test_production_readiness_marks_hard_failures_not_ready(monkeypatch):
    monkeypatch.setattr(
        api,
        "get_settings",
        lambda: _settings(
            app_secret_key="change-me",
            auth_local_tokens_enabled=True,
            auth_jwks_url="",
            auth_oidc_issuer_url="",
            kafka_bootstrap_servers="",
            artifact_backend="local",
            reliability_store="memory",
        ),
    )
    monkeypatch.setattr(api, "get_reliability_store", lambda settings=None: _ReadyStore("memory"), raising=False)
    app = create_app()
    app.dependency_overrides[api.get_session] = lambda: _ReadySession()
    client = TestClient(app)

    response = client.get("/v1/ops/readiness", headers=_auth("operator"))

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "not_ready"
    assert body["production"]["status"] == "not_ready"
    failed = {
        name
        for name, check in body["production"]["checks"].items()
        if check["status"] == "fail"
    }
    assert {
        "local_tokens_disabled",
        "secret_key_rotated",
        "jwks_or_oidc_configured",
        "redis_reliability_store",
        "kafka_configured",
        "s3_artifact_backend",
    }.issubset(failed)


def test_correlation_middleware_preserves_header_and_parses_traceparent(monkeypatch):
    monkeypatch.setattr(api, "get_settings", lambda: _settings(app_env="local"))
    app = create_app()
    client = TestClient(app)
    traceparent = "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"

    response = client.get(
        "/healthz",
        headers={"X-Correlation-ID": "cid-v11", "traceparent": traceparent},
    )

    assert response.status_code == 200
    assert response.headers["X-Correlation-ID"] == "cid-v11"
    assert response.json()["status"] == "ok"


def test_correlation_middleware_generates_header_when_missing(monkeypatch):
    monkeypatch.setattr(api, "get_settings", lambda: _settings(app_env="local"))
    app = create_app()
    client = TestClient(app)

    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.headers["X-Correlation-ID"]


def _auth(role: str) -> dict:
    token = create_access_token(local_dev_actor_for_role(role))
    return {"Authorization": f"Bearer {token}"}


def _settings(**overrides):
    values = {
        "app_name": "browser-agent",
        "app_version": "1.1.0",
        "app_env": "production",
        "app_log_level": "INFO",
        "app_secret_key": "prod-secret-for-tests",
        "auth_mode": "jwks",
        "auth_jwt_issuer": "browser-agent-idp",
        "auth_jwt_audience": "browser-agent-api",
        "auth_jwks_url": "https://idp.example.test/keys",
        "auth_oidc_issuer_url": "",
        "auth_local_tokens_enabled": False,
        "reliability_store": "redis",
        "kafka_bootstrap_servers": "kafka:9092",
        "artifact_backend": "s3",
        "artifact_base_path": "/data/artifacts",
        "minio_bucket": "browser-agent",
        "worker_service_id": "worker-prod",
        "task_lock_ttl_seconds": 300,
        "dlq_topic": "agent.tasks.dlq",
        "otel_enabled": False,
        "otel_service_name": "browser-agent",
        "otel_exporter_otlp_endpoint": "",
        "otel_resource_attributes": "service.namespace=browser-agent,deployment.environment=production",
        "otel_propagators": "tracecontext,baggage",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


class _ReadyStore:
    def __init__(self, backend="redis"):
        self.backend = backend

    def status(self):
        return {"backend": self.backend, "available": True}


class _ReadySession:
    def execute(self, statement):
        return None

    def close(self):
        return None
