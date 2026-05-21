from __future__ import annotations

import base64
import hashlib
import hmac
import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Iterable

from fastapi import Depends, HTTPException, Request

from .config import Settings, get_settings

DEMO_TENANT_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")

DEMO_ACTORS = {
    "admin": {
        "user_id": uuid.UUID("00000000-0000-0000-0000-000000000002"),
        "email": "ops@example.com",
        "roles": ("admin",),
    },
    "creator": {
        "user_id": uuid.UUID("00000000-0000-0000-0000-000000000003"),
        "email": "creator@example.com",
        "roles": ("creator",),
    },
    "approver": {
        "user_id": uuid.UUID("00000000-0000-0000-0000-000000000004"),
        "email": "approver@example.com",
        "roles": ("approver",),
    },
    "operator": {
        "user_id": uuid.UUID("00000000-0000-0000-0000-000000000005"),
        "email": "operator@example.com",
        "roles": ("operator",),
    },
}

ROLE_PERMISSIONS = {
    "creator": {
        "task:create",
        "task:read",
        "artifact:read",
        "skill:read",
    },
    "approver": {
        "task:read",
        "task:audit:read",
        "task:approve",
        "artifact:read",
        "skill:read",
    },
    "operator": {
        "task:read",
        "task:audit:read",
        "artifact:read",
        "metrics:read",
        "skill:read",
    },
    "admin": {
        "task:create",
        "task:read",
        "task:audit:read",
        "task:approve",
        "artifact:read",
        "metrics:read",
        "skill:read",
        "skill:create",
    },
}


@dataclass(frozen=True)
class ActorContext:
    user_id: uuid.UUID
    tenant_id: uuid.UUID
    email: str
    roles: tuple[str, ...]

    @property
    def permissions(self) -> set[str]:
        return permissions_for_roles(self.roles)

    def audit_payload(self) -> dict:
        return {
            "actor_user_id": str(self.user_id),
            "actor_email": self.email,
            "actor_roles": list(self.roles),
        }


def permissions_for_roles(roles: Iterable[str]) -> set[str]:
    permissions: set[str] = set()
    for role in roles:
        permissions.update(ROLE_PERMISSIONS.get(role, set()))
    return permissions


def demo_actor_for_role(role: str) -> ActorContext:
    spec = DEMO_ACTORS.get(role)
    if not spec:
        raise ValueError(f"unknown demo role {role}")
    return ActorContext(
        user_id=spec["user_id"],
        tenant_id=DEMO_TENANT_ID,
        email=spec["email"],
        roles=tuple(spec["roles"]),
    )


def create_access_token(
    actor: ActorContext,
    *,
    settings: Settings | None = None,
    expires_at: datetime | None = None,
) -> str:
    settings = settings or get_settings()
    now = datetime.now(timezone.utc)
    expires_at = expires_at or now + timedelta(seconds=settings.auth_token_ttl_seconds)
    payload = {
        "iss": settings.auth_jwt_issuer,
        "aud": settings.auth_jwt_audience,
        "sub": str(actor.user_id),
        "tenant_id": str(actor.tenant_id),
        "email": actor.email,
        "roles": list(actor.roles),
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
    }
    return _encode_jwt(payload, settings.app_secret_key)


def decode_access_token(token: str, *, settings: Settings | None = None) -> ActorContext:
    settings = settings or get_settings()
    payload = _decode_jwt(token, settings.app_secret_key)
    if payload.get("iss") != settings.auth_jwt_issuer:
        raise ValueError("invalid token issuer")
    if payload.get("aud") != settings.auth_jwt_audience:
        raise ValueError("invalid token audience")
    exp = payload.get("exp")
    if not isinstance(exp, int) or exp <= int(datetime.now(timezone.utc).timestamp()):
        raise ValueError("token expired")
    roles = payload.get("roles")
    if not isinstance(roles, list) or not all(isinstance(role, str) for role in roles):
        raise ValueError("invalid token roles")
    return ActorContext(
        user_id=uuid.UUID(str(payload["sub"])),
        tenant_id=uuid.UUID(str(payload["tenant_id"])),
        email=str(payload["email"]),
        roles=tuple(roles),
    )


def get_current_actor(request: Request) -> ActorContext:
    settings = get_settings()
    if not settings.auth_enabled:
        return demo_actor_for_role("admin")
    authorization = request.headers.get("Authorization")
    if not authorization or not authorization.startswith("Bearer "):
        raise _auth_error("missing bearer token")
    token = authorization.removeprefix("Bearer ").strip()
    try:
        return decode_access_token(token, settings=settings)
    except Exception as exc:
        raise _auth_error("invalid bearer token") from exc


def require_roles(*allowed_roles: str):
    def dependency(actor: ActorContext = Depends(get_current_actor)) -> ActorContext:
        if "admin" in actor.roles or set(actor.roles).intersection(allowed_roles):
            return actor
        raise HTTPException(status_code=403, detail="insufficient role")

    return dependency


def _auth_error(detail: str) -> HTTPException:
    return HTTPException(
        status_code=401,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def _encode_jwt(payload: dict, secret: str) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    signing_input = ".".join([
        _b64url_json(header),
        _b64url_json(payload),
    ]).encode("ascii")
    signature = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    return f"{signing_input.decode('ascii')}.{_b64url_encode(signature)}"


def _decode_jwt(token: str, secret: str) -> dict:
    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("invalid jwt format")
    signing_input = ".".join(parts[:2]).encode("ascii")
    expected_signature = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    actual_signature = _b64url_decode(parts[2])
    if not hmac.compare_digest(expected_signature, actual_signature):
        raise ValueError("invalid jwt signature")
    header = json.loads(_b64url_decode(parts[0]))
    if header.get("alg") != "HS256":
        raise ValueError("unsupported jwt alg")
    return json.loads(_b64url_decode(parts[1]))


def _b64url_json(value: dict) -> str:
    return _b64url_encode(json.dumps(value, separators=(",", ":"), sort_keys=True).encode("utf-8"))


def _b64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _b64url_decode(value: str) -> bytes:
    padded = value + ("=" * (-len(value) % 4))
    return base64.urlsafe_b64decode(padded.encode("ascii"))
