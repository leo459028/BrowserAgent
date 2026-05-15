from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

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
    assert task.status == "approved"
    assert bus.published[0][0] == "agent.tasks.approved"


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
                metadata={"media_type": "image/png"},
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
            "metadata": {"media_type": "image/png"},
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
    assert "Browser Agent Demo" in response.text
    assert "https://example.com" in response.text


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
