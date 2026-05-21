from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from fastapi.testclient import TestClient

import browser_agent.api as api
from browser_agent import models
from browser_agent.api import create_app
from browser_agent.auth import create_access_token, demo_actor_for_role


TENANT_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
OTHER_TENANT_ID = uuid.UUID("10000000-0000-0000-0000-000000000001")


def test_missing_invalid_and_expired_tokens_return_401(monkeypatch):
    app = create_app()
    app.dependency_overrides[api.get_session] = lambda: _FakeQuerySession()
    client = TestClient(app)

    assert client.get("/v1/tasks").status_code == 401
    assert client.get("/v1/tasks", headers={"Authorization": "Bearer nope"}).status_code == 401

    expired = _token("creator", expires_at=datetime.now(timezone.utc) - timedelta(seconds=1))
    assert client.get("/v1/tasks", headers=_auth(expired)).status_code == 401


def test_operator_cannot_create_task(monkeypatch):
    app = create_app()
    app.dependency_overrides[api.get_session] = lambda: _FakeQuerySession()
    client = TestClient(app)

    response = client.post("/v1/tasks", json=_task_payload(), headers=_auth(_token("operator")))

    assert response.status_code == 403


def test_demo_token_and_auth_me_return_actor_permissions():
    client = TestClient(create_app())

    token_response = client.post("/v1/auth/demo-token", json={"role": "operator"})

    assert token_response.status_code == 200
    token_body = token_response.json()
    assert token_body["token_type"] == "bearer"
    assert token_body["actor"]["email"] == "operator@example.com"

    me_response = client.get("/v1/auth/me", headers=_auth(token_body["access_token"]))

    assert me_response.status_code == 200
    me = me_response.json()
    assert me["email"] == "operator@example.com"
    assert me["roles"] == ["operator"]
    assert "metrics:read" in me["permissions"]


def test_creator_can_create_task_with_request_scoped_actor(monkeypatch):
    session = _FakeQuerySession()
    bus = _FakeBus()
    monkeypatch.setattr(api, "get_bus", lambda bootstrap_servers: bus)
    app = create_app()
    app.dependency_overrides[api.get_session] = lambda: session
    client = TestClient(app)

    response = client.post("/v1/tasks", json=_task_payload(), headers=_auth(_token("creator")))

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "pending_approval"
    task = session.first_added(models.Task)
    assert task.tenant_id == TENANT_ID
    assert task.created_by == demo_actor_for_role("creator").user_id
    audit = session.first_added(models.AuditLog)
    assert audit.actor == "creator@example.com"


def test_creator_cannot_approve_but_approver_can_and_audit_uses_token_actor(monkeypatch):
    task = SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=TENANT_ID,
        approved_by=None,
        approved_at=None,
        status="pending_approval",
        correlation_id="cid-v05-approve",
        metadata_={},
    )
    session = _FakeQuerySession(objects={models.Task: {task.id: task}})
    bus = _FakeBus()
    monkeypatch.setattr(api, "get_bus", lambda bootstrap_servers: bus)
    app = create_app()
    app.dependency_overrides[api.get_session] = lambda: session
    client = TestClient(app)

    forbidden = client.post(f"/v1/tasks/{task.id}/approve", json={}, headers=_auth(_token("creator")))
    assert forbidden.status_code == 403

    approved = client.post(f"/v1/tasks/{task.id}/approve", json={}, headers=_auth(_token("approver")))

    assert approved.status_code == 200
    assert task.status == "queued"
    assert task.approved_by == demo_actor_for_role("approver").user_id
    approval = session.first_added(models.Approval)
    assert approval.approved_by == "approver@example.com"
    approved_audit = [entry for entry in session.added if isinstance(entry, models.AuditLog)][0]
    assert approved_audit.actor == "approver@example.com"
    assert approved_audit.payload["actor_user_id"] == str(demo_actor_for_role("approver").user_id)
    assert approved_audit.payload["actor_email"] == "approver@example.com"
    assert approved_audit.payload["actor_roles"] == ["approver"]
    assert bus.published[0][2]["approved_by"] == "approver@example.com"
    assert bus.published[0][2]["actor_email"] == "approver@example.com"


def test_operator_can_read_metrics_but_creator_cannot():
    client = TestClient(create_app())

    assert client.get("/metrics", headers=_auth(_token("operator"))).status_code == 200
    assert client.get("/metrics", headers=_auth(_token("creator"))).status_code == 403


def test_admin_can_register_skill(monkeypatch):
    session = _FakeQuerySession()
    app = create_app()
    app.dependency_overrides[api.get_session] = lambda: session
    client = TestClient(app)

    response = client.post(
        "/v1/skills",
        json={
            "name": "browser.goto",
            "version": "1.0.0",
            "description": "demo",
            "skill_type": "browser_action",
            "entrypoint": "browser.goto",
            "input_schema": {"type": "object"},
            "output_schema": {"type": "object"},
            "policy_tags": ["browser"],
        },
        headers=_auth(_token("admin")),
    )

    assert response.status_code == 200
    skill = session.first_added(models.Skill)
    assert skill.tenant_id == TENANT_ID
    assert skill.created_by == demo_actor_for_role("admin").user_id


def test_artifact_content_uses_token_tenant_for_access_check(monkeypatch):
    artifact = SimpleNamespace(
        id=uuid.uuid4(),
        task=SimpleNamespace(tenant_id=OTHER_TENANT_ID),
        uri="missing.png",
        metadata_={"content_type": "image/png"},
    )
    session = _FakeQuerySession(objects={models.TaskArtifact: {artifact.id: artifact}})
    app = create_app()
    app.dependency_overrides[api.get_session] = lambda: session
    client = TestClient(app)

    response = client.get(f"/v1/artifacts/{artifact.id}/content", headers=_auth(_token("creator")))

    assert response.status_code == 403
    assert response.json()["detail"] == "artifact tenant mismatch"


def _task_payload() -> dict:
    return {
        "title": "Capture example",
        "instructions": "Open the allowlisted site and capture a screenshot.",
        "priority": 1,
        "risk_level": "low",
        "metadata": {
            "domains": ["example.com"],
            "start_url": "https://example.com",
            "expected_domain": "example.com",
        },
    }


def _token(role: str, *, expires_at: datetime | None = None) -> str:
    return create_access_token(demo_actor_for_role(role), expires_at=expires_at)


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


class _FakeBus:
    def __init__(self):
        self.published = []

    def publish(self, topic, key, payload):
        self.published.append((topic, key, payload))


class _FakeQuerySession:
    def __init__(self, tasks=None, audits=None, skills=None, objects=None):
        self.tasks = tasks or []
        self.audits = audits or []
        self.skills = skills or []
        self.objects = objects or {}
        self.added = []

    def add(self, obj):
        self.added.append(obj)

    def flush(self):
        for obj in self.added:
            if hasattr(obj, "id") and getattr(obj, "id") is None:
                setattr(obj, "id", uuid.uuid4())

    def commit(self):
        return None

    def rollback(self):
        return None

    def close(self):
        return None

    def get(self, entity, entity_id):
        return self.objects.get(entity, {}).get(entity_id)

    def execute(self, statement):
        entity = statement.column_descriptions[0]["entity"]
        if entity is models.Task:
            return _FakeQueryResult(self.tasks)
        if entity is models.AuditLog:
            return _FakeQueryResult(self.audits)
        if entity is models.Skill:
            return _FakeQueryResult(self.skills)
        return _FakeQueryResult([])

    def first_added(self, model_type):
        return next(obj for obj in self.added if isinstance(obj, model_type))


class _FakeQueryResult:
    def __init__(self, rows):
        self.rows = rows

    def scalars(self):
        return self

    def all(self):
        return self.rows

    def first(self):
        return self.rows[0] if self.rows else None
