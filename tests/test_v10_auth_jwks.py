from __future__ import annotations

import base64
import hashlib
import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from fastapi.testclient import TestClient

import browser_agent.auth as auth
from browser_agent.api import create_app


RSA_N = 98895918002280109959841932300891341070911815283623426536996947055139735188778203272410680605792833499676633345945383355140416381815149968711455371440047244618790355525741192158880870224760657951923115034733457330868156241445456437907471831979500678320383239855984417501924636128258320501468961284402374841367
RSA_E = 65537
RSA_D = 4910315046148274681619934505807412970455575429649062818734273245913372572810538679653086877508123353341589711273117131355217890755245098161146768675189796101591786002800561442625628725613009249444043121983625881461776579772324893657281291792040814425977749352511550122328967564958516702720120292131395848993
RSA_N_B64 = "jNUcOp_HyxI3b0xO8BcDb6huLVmuasmwGvX97nxICy7vu8zNXf_v2EOOA8p0fmA4mUVHUNOB6G563E08vu1uuYxloB9D3fJw0hjbU6T0CnPiEEL4R0PQzor0X28G1RknfiRYFY8wpj18QOpdok73fzZn3JvVM3j2agOSX-WdFBc"
RSA_E_B64 = "AQAB"


def test_local_token_endpoint_replaces_legacy_token_name():
    client = TestClient(create_app())

    response = client.post("/v1/auth/local-token", json={"role": "operator"})

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["actor"]["email"] == "operator@example.com"
    assert client.post("/v1/auth/demo-token", json={"role": "operator"}).status_code == 404


def test_jwks_mode_accepts_valid_rs256_token(monkeypatch):
    monkeypatch.setattr(auth, "get_settings", lambda: _jwks_settings())
    monkeypatch.setattr(auth, "_fetch_jwks", lambda settings: _jwks())
    token = _jwt({"roles": ["operator"]})
    client = TestClient(create_app())

    response = client.get("/v1/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.json()["email"] == "jwks-operator@example.com"
    assert response.json()["roles"] == ["operator"]


def test_jwks_mode_rejects_bad_issuer_audience_expiry_and_roles(monkeypatch):
    monkeypatch.setattr(auth, "get_settings", lambda: _jwks_settings())
    monkeypatch.setattr(auth, "_fetch_jwks", lambda settings: _jwks())
    client = TestClient(create_app())

    bad_issuer = client.get("/v1/auth/me", headers={"Authorization": f"Bearer {_jwt({'iss': 'wrong'})}"})
    bad_audience = client.get("/v1/auth/me", headers={"Authorization": f"Bearer {_jwt({'aud': 'wrong'})}"})
    expired = client.get("/v1/auth/me", headers={"Authorization": f"Bearer {_jwt({'exp': _ts(-60)})}"})
    bad_roles = client.get("/v1/auth/me", headers={"Authorization": f"Bearer {_jwt({'roles': 'operator'})}"})

    assert bad_issuer.status_code == 401
    assert bad_audience.status_code == 401
    assert expired.status_code == 401
    assert bad_roles.status_code == 401


def _jwks_settings(**overrides):
    values = {
        "auth_mode": "jwks",
        "auth_jwks_url": "https://idp.example.test/.well-known/jwks.json",
        "auth_jwt_issuer": "browser-agent-idp",
        "auth_jwt_audience": "browser-agent-api",
        "app_secret_key": "unused",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _jwks():
    return {
        "keys": [
            {
                "kty": "RSA",
                "kid": "test-key",
                "alg": "RS256",
                "use": "sig",
                "n": RSA_N_B64,
                "e": RSA_E_B64,
            }
        ]
    }


def _jwt(overrides: dict | None = None) -> str:
    payload = {
        "iss": "browser-agent-idp",
        "aud": "browser-agent-api",
        "sub": "00000000-0000-0000-0000-000000000005",
        "tenant_id": "00000000-0000-0000-0000-000000000001",
        "email": "jwks-operator@example.com",
        "roles": ["operator"],
        "iat": _ts(0),
        "exp": _ts(3600),
    }
    payload.update(overrides or {})
    header = {"alg": "RS256", "typ": "JWT", "kid": "test-key"}
    signing_input = ".".join([_b64json(header), _b64json(payload)]).encode("ascii")
    digest_info = bytes.fromhex("3031300d060960864801650304020105000420") + hashlib.sha256(signing_input).digest()
    key_bytes = (RSA_N.bit_length() + 7) // 8
    padded = b"\x00\x01" + (b"\xff" * (key_bytes - len(digest_info) - 3)) + b"\x00" + digest_info
    signature = pow(int.from_bytes(padded, "big"), RSA_D, RSA_N).to_bytes(key_bytes, "big")
    return f"{signing_input.decode('ascii')}.{_b64(signature)}"


def _ts(delta_seconds: int) -> int:
    return int((datetime.now(timezone.utc) + timedelta(seconds=delta_seconds)).timestamp())


def _b64json(value: dict) -> str:
    return _b64(json.dumps(value, separators=(",", ":"), sort_keys=True).encode("utf-8"))


def _b64(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")
