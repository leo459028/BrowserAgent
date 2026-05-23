from __future__ import annotations

import uuid
from types import SimpleNamespace

from fastapi.testclient import TestClient

import browser_agent.api as api
from browser_agent import models
from browser_agent.api import create_app
from browser_agent.auth import create_access_token, local_dev_actor_for_role


TENANT_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


def test_dlq_bulk_replay_skips_quarantined_tasks_and_publishes_replay_events(monkeypatch):
    replayable = _failed_dlq_task("pending")
    quarantined = _failed_dlq_task("quarantined")
    session = _FakeSession([replayable, quarantined])
    bus = _FakeBus()
    monkeypatch.setattr(api, "get_bus", lambda bootstrap_servers: bus)
    monkeypatch.setattr(api, "get_settings", lambda: SimpleNamespace(kafka_bootstrap_servers=""))
    app = create_app()
    app.dependency_overrides[api.get_session] = lambda: session
    client = TestClient(app)

    creator_forbidden = client.post(
        "/v1/dlq/tasks/bulk-replay",
        json={"task_ids": [str(replayable.id)]},
        headers=_auth("creator"),
    )
    response = client.post(
        "/v1/dlq/tasks/bulk-replay",
        json={"task_ids": [str(replayable.id), str(quarantined.id)], "note": "retry batch"},
        headers=_auth("operator"),
    )

    assert creator_forbidden.status_code == 403
    assert response.status_code == 200
    assert response.json()["replayed"] == [{"task_id": str(replayable.id), "status": "queued"}]
    assert response.json()["skipped"] == [{"task_id": str(quarantined.id), "reason": "quarantined"}]
    assert replayable.status == "queued"
    assert quarantined.status == "failed"
    assert bus.published[0][0] == "agent.tasks.queued"
    assert session.audit_actions == ["task.dlq_replayed"]


def test_dlq_quarantine_marks_poison_task_and_writes_audit(monkeypatch):
    task = _failed_dlq_task("pending")
    session = _FakeSession([task])
    monkeypatch.setattr(api, "get_settings", lambda: SimpleNamespace(kafka_bootstrap_servers=""))
    app = create_app()
    app.dependency_overrides[api.get_session] = lambda: session
    client = TestClient(app)

    response = client.post(
        f"/v1/dlq/tasks/{task.id}/quarantine",
        json={"reason": "poison message"},
        headers=_auth("operator"),
    )

    assert response.status_code == 200
    assert response.json()["dlq"]["status"] == "quarantined"
    assert task.metadata_["reliability"]["dlq"]["quarantine"]["reason"] == "poison message"
    assert session.audit_actions == ["task.dlq_quarantined"]


def _failed_dlq_task(status):
    return SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=TENANT_ID,
        title="Failed task",
        status="failed",
        correlation_id="cid-dlq",
        metadata_={
            "reliability": {
                "dlq": {
                    "status": status,
                    "topic": "agent.tasks.dlq",
                    "worker_id": "worker-v10-test",
                    "attempts": 1,
                    "error": {"message": "browser crashed"},
                }
            }
        },
        started_at=None,
        completed_at=None,
        updated_at=SimpleNamespace(isoformat=lambda: "2026-05-22T00:00:00+00:00"),
    )


def _auth(role):
    return {"Authorization": f"Bearer {create_access_token(local_dev_actor_for_role(role))}"}


class _FakeBus:
    def __init__(self):
        self.published = []

    def publish(self, topic, key, payload):
        self.published.append((topic, key, payload))


class _FakeSession:
    def __init__(self, tasks):
        self.tasks = tasks
        self.audit_actions = []

    def get(self, entity, entity_id):
        if entity is models.Task:
            return next((task for task in self.tasks if task.id == entity_id), None)
        return None

    def add(self, obj):
        if isinstance(obj, models.AuditLog):
            self.audit_actions.append(obj.action)

    def flush(self):
        return None

    def commit(self):
        return None

    def close(self):
        return None
