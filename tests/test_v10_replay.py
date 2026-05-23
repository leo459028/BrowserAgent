from __future__ import annotations

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

from fastapi.testclient import TestClient

import browser_agent.api as api
from browser_agent import models
from browser_agent.api import create_app
from browser_agent.auth import create_access_token, local_dev_actor_for_role


TENANT_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


def test_task_replay_timeline_combines_audit_steps_artifacts_and_evaluation():
    task_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    task = SimpleNamespace(
        id=task_id,
        tenant_id=TENANT_ID,
        title="Replay task",
        status="completed",
        metadata_={"evaluation": {"score": 100, "verdict": "pass"}},
        steps=[
            SimpleNamespace(
                id=uuid.uuid4(),
                step_no=1,
                action_type="goto",
                target="https://example.com",
                status="completed",
                input_data={"action": "goto"},
                output_data={"final_url": "https://example.com"},
                error_message=None,
                created_at=now,
            )
        ],
        artifacts=[
            SimpleNamespace(
                id=uuid.uuid4(),
                artifact_type="screenshot",
                uri="s3://browser-agent/shot.png",
                sha256="abc",
                metadata_={"backend": "s3", "content_type": "image/png"},
                created_at=now,
            )
        ],
    )
    audit = SimpleNamespace(
        id=uuid.uuid4(),
        actor="service:worker-local",
        action="task.execution_started",
        payload={"status": "executing"},
        created_at=now,
    )
    evaluation = SimpleNamespace(
        id=uuid.uuid4(),
        task_id=task_id,
        evaluator_ver="1.0.0",
        score=100,
        verdict="pass",
        checks={"final_url": True},
        created_at=now,
    )
    app = create_app()
    app.dependency_overrides[api.get_session] = lambda: _FakeSession(task, [audit], [evaluation])

    response = TestClient(app).get(f"/v1/tasks/{task_id}/replay", headers=_auth("operator"))

    assert response.status_code == 200
    body = response.json()
    assert body["task_id"] == str(task_id)
    assert body["timeline"][0]["kind"] == "audit"
    assert body["timeline"][1]["kind"] == "step"
    assert body["timeline"][2]["kind"] == "artifact"
    assert body["timeline"][3]["kind"] == "evaluation"
    assert body["timeline"][1]["output_data"] == {"final_url": "https://example.com"}


def _auth(role):
    return {"Authorization": f"Bearer {create_access_token(local_dev_actor_for_role(role))}"}


class _FakeSession:
    def __init__(self, task, audits, evaluations):
        self.task = task
        self.audits = audits
        self.evaluations = evaluations

    def get(self, entity, entity_id):
        if entity is models.Task and entity_id == self.task.id:
            return self.task
        return None

    def execute(self, statement):
        entity = statement.column_descriptions[0]["entity"]
        if entity is models.AuditLog:
            return _FakeResult(self.audits)
        if entity is models.Evaluation:
            return _FakeResult(self.evaluations)
        return _FakeResult([])

    def close(self):
        return None


class _FakeResult:
    def __init__(self, rows):
        self.rows = rows

    def scalars(self):
        return self

    def all(self):
        return self.rows
