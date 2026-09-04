from __future__ import annotations

from fastapi.testclient import TestClient

import browser_agent.auth as auth
from browser_agent.api import create_app
from tests.test_v10_auth_jwks import _jwks, _jwks_settings, _jwt


def test_jwks_url_takes_precedence_over_oidc_discovery(monkeypatch):
    requested_urls = []

    def fake_fetch_json(url: str, timeout_seconds: int) -> dict:
        requested_urls.append(url)
        return _jwks()

    settings = _jwks_settings(
        auth_jwks_url="https://idp.example.test/keys",
        auth_oidc_issuer_url="https://issuer.example.test",
        auth_jwks_request_timeout_seconds=3,
        auth_jwks_cache_ttl_seconds=60,
    )
    monkeypatch.setattr(auth, "get_settings", lambda: settings)
    monkeypatch.setattr(auth, "_fetch_json_url", fake_fetch_json)
    client = TestClient(create_app())

    response = client.get("/v1/auth/me", headers={"Authorization": f"Bearer {_jwt()}"})

    assert response.status_code == 200
    assert requested_urls == ["https://idp.example.test/keys"]


def test_oidc_discovery_resolves_jwks_uri_when_direct_jwks_url_is_missing(monkeypatch):
    requested_urls = []

    def fake_fetch_json(url: str, timeout_seconds: int) -> dict:
        requested_urls.append(url)
        if url.endswith("/.well-known/openid-configuration"):
            return {"jwks_uri": "https://issuer.example.test/keys"}
        return _jwks()

    settings = _jwks_settings(
        auth_jwks_url="",
        auth_oidc_issuer_url="https://issuer.example.test/",
        auth_jwks_request_timeout_seconds=3,
        auth_jwks_cache_ttl_seconds=60,
    )
    monkeypatch.setattr(auth, "get_settings", lambda: settings)
    monkeypatch.setattr(auth, "_fetch_json_url", fake_fetch_json)
    client = TestClient(create_app())

    response = client.get("/v1/auth/me", headers={"Authorization": f"Bearer {_jwt()}"})

    assert response.status_code == 200
    assert requested_urls == [
        "https://issuer.example.test/.well-known/openid-configuration",
        "https://issuer.example.test/keys",
    ]


def test_oidc_discovery_rejects_missing_jwks_uri(monkeypatch):
    def fake_fetch_json(url: str, timeout_seconds: int) -> dict:
        return {"issuer": "https://bad-issuer.example.test"}

    settings = _jwks_settings(
        auth_jwks_url="",
        auth_oidc_issuer_url="https://bad-issuer.example.test",
        auth_jwks_request_timeout_seconds=3,
        auth_jwks_cache_ttl_seconds=60,
    )
    monkeypatch.setattr(auth, "get_settings", lambda: settings)
    monkeypatch.setattr(auth, "_fetch_json_url", fake_fetch_json)
    client = TestClient(create_app())

    response = client.get("/v1/auth/me", headers={"Authorization": f"Bearer {_jwt()}"})

    assert response.status_code == 401
