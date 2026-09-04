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


def test_visual_replay_response_structure():
    task_id = uuid.uuid4()
    art_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    task = SimpleNamespace(
        id=task_id,
        tenant_id=TENANT_ID,
        title="Visual replay test task",
        status="completed",
        correlation_id="cid-visual-replay-test",
        metadata_={
            "trace_context": {"trace_id": "4bf92f3577b34da6a3ce929d0e0e4736", "span_id": "00f067aa0ba902b7"}
        },
        steps=[
            SimpleNamespace(
                id=uuid.uuid4(),
                step_no=1,
                action_type="screenshot",
                target="body",
                status="completed",
                input_data={"action": "screenshot"},
                output_data={
                    "span_id": "step-span-123",
                    "duration_ms": 150.5,
                    "screenshot_artifact_id": str(art_id),
                    "dom_summary": "Page title: Example",
                },
                error_message=None,
                created_at=now,
            )
        ],
        artifacts=[
            SimpleNamespace(
                id=art_id,
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
        score=1.0,
        verdict="pass",
        checks={"screenshot_present": True},
        created_at=now,
    )
    app = create_app()
    app.dependency_overrides[api.get_session] = lambda: _FakeSession(task, [audit], [evaluation])
    client = TestClient(app)

    token = create_access_token(local_dev_actor_for_role("operator"))
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get(f"/v1/tasks/{task_id}/replay", headers=headers)
    assert res.status_code == 200
    data = res.json()

    assert data["task_id"] == str(task_id)
    assert data["trace_id"] == "4bf92f3577b34da6a3ce929d0e0e4736"
    assert "steps_visual" in data
    assert len(data["steps_visual"]) == 1

    step_out = data["steps_visual"][0]
    assert step_out["step_no"] == 1
    assert step_out["action_type"] == "screenshot"
    assert step_out["duration_ms"] == 150.5
    assert step_out["span_id"] == "step-span-123"
    assert step_out["screenshot_artifact_id"] == str(art_id)
    assert step_out["screenshot_url"] == f"/v1/artifacts/{art_id}/content"
    assert step_out["dom_summary"] == "Page title: Example"

    assert data["evaluation_summary"]["verdict"] == "pass"
    assert data["evaluation_summary"]["score"] == 1.0

    # Timeline backwards compatibility
    assert "timeline" in data
    assert isinstance(data["timeline"], list)


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
