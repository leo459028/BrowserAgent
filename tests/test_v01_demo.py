from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

import browser_agent.api as api
from browser_agent import models
from browser_agent.api import create_app, resolve_artifact_file_path, serialize_task
from browser_agent.orchestrator import Orchestrator


def test_approval_records_demo_user_uuid_on_task_and_display_actor_on_approval():
    actor_id = uuid.UUID("00000000-0000-0000-0000-000000000002")
    task = SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
        approved_by=None,
        approved_at=None,
        status="created",
    )
    session = _FakeSession()
    bus = _FakeBus()

    approval = Orchestrator(session, bus).approve_task(
        task,
        approved_by_user_id=actor_id,
        approved_by_label="ops@example.com",
        note="local demo",
    )

    assert task.approved_by == actor_id
    assert approval.approved_by == "ops@example.com"
    assert task.status == "queued"
    assert bus.published[0][0] == "agent.tasks.queued"


def test_serialize_task_includes_artifacts_summary():
    task_id = uuid.uuid4()
    artifact_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    task = SimpleNamespace(
        id=task_id,
        tenant_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
        title="Capture example",
        instructions="Open example.com",
        status="completed",
        priority=1,
        risk_level="low",
        metadata={"evaluation": {"score": 100, "verdict": "pass"}},
        created_at=now,
        updated_at=now,
        steps=[],
        artifacts=[
            SimpleNamespace(
                id=artifact_id,
                artifact_type="screenshot",
                uri="/data/artifacts/2026/05/16/task/screenshot-a.png",
                sha256="abc123",
                metadata={
                    "media_type": "image/png",
                    "content_type": "image/png",
                    "size_bytes": 256,
                    "backend": "local",
                    "redaction": {"status": "not_applied", "strategy": "noop"},
                },
                created_at=now,
            )
        ],
    )

    payload = serialize_task(task)

    assert payload["id"] == str(task_id)
    assert payload["artifacts"] == [
        {
            "id": str(artifact_id),
            "artifact_type": "screenshot",
            "uri": "/data/artifacts/2026/05/16/task/screenshot-a.png",
            "sha256": "abc123",
            "content_type": "image/png",
            "size_bytes": 256,
            "backend": "local",
            "retention": None,
            "redaction": {"status": "not_applied", "strategy": "noop"},
            "redaction_status": "not_applied",
            "metadata": {
                "media_type": "image/png",
                "content_type": "image/png",
                "size_bytes": 256,
                "backend": "local",
                "redaction": {"status": "not_applied", "strategy": "noop"},
            },
            "created_at": now.isoformat(),
            "download_url": f"/v1/artifacts/{artifact_id}/content",
        }
    ]


def test_resolve_artifact_file_path_rejects_paths_outside_base(tmp_path: Path):
    base = tmp_path / "artifacts"
    base.mkdir()
    outside = tmp_path / "secret.html"
    outside.write_text("secret", encoding="utf-8")

    with pytest.raises(HTTPException) as exc:
        resolve_artifact_file_path(str(base), str(outside))

    assert exc.value.status_code == 403


def test_demo_route_renders_console():
    client = TestClient(create_app())

    response = client.get("/demo")

    assert response.status_code == 200
    assert "Browser Agent v0.3 Dashboard" in response.text
    assert "https://example.com" in response.text
    assert "Audit Timeline" in response.text
    assert "Metrics" in response.text
    assert "Artifact Query" in response.text
    assert "redaction status" in response.text


def test_task_list_api_returns_recent_task_summaries():
    app = create_app()
    now = datetime.now(timezone.utc)
    task = SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
        title="High risk review",
        status="pending_approval",
        correlation_id="cid-list",
        priority=3,
        risk_level="high",
        metadata_={"policy": {"reason": "high-risk task requires manual approval"}},
        created_at=now,
        updated_at=now,
    )
    session = _FakeQuerySession(tasks=[task])
    app.dependency_overrides[api.get_session] = lambda: session

    response = TestClient(app).get("/v1/tasks")

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": str(task.id),
            "title": "High risk review",
            "status": "pending_approval",
            "correlation_id": "cid-list",
            "priority": 3,
            "risk_level": "high",
            "policy": {"reason": "high-risk task requires manual approval"},
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }
    ]


def test_task_audit_api_returns_lifecycle_events():
    app = create_app()
    task_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    audit = SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
        actor="ops@example.com",
        action="task.pending_approval",
        entity_type="task",
        entity_id=str(task_id),
        payload={"reason": "high-risk task requires manual approval"},
        created_at=now,
    )
    session = _FakeQuerySession(audits=[audit])
    app.dependency_overrides[api.get_session] = lambda: session

    response = TestClient(app).get(f"/v1/tasks/{task_id}/audit")

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": str(audit.id),
            "actor": "ops@example.com",
            "action": "task.pending_approval",
            "payload": {"reason": "high-risk task requires manual approval"},
            "created_at": now.isoformat(),
        }
    ]


class _FakeSession:
    def __init__(self):
        self.added = []

    def add(self, obj):
        self.added.append(obj)

    def flush(self):
        return None


class _FakeBus:
    def __init__(self):
        self.published = []

    def publish(self, topic, key, payload):
        self.published.append((topic, key, payload))


class _FakeQuerySession:
    def __init__(self, tasks=None, audits=None):
        self.tasks = tasks or []
        self.audits = audits or []

    def execute(self, statement):
        entity = statement.column_descriptions[0]["entity"]
        if entity is models.Task:
            return _FakeQueryResult(self.tasks)
        if entity is models.AuditLog:
            return _FakeQueryResult(self.audits)
        return _FakeQueryResult([])

    def close(self):
        return None


class _FakeQueryResult:
    def __init__(self, rows):
        self.rows = rows

    def scalars(self):
        return self

    def all(self):
        return self.rows
