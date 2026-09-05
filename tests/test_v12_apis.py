from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

import browser_agent.api as api
from browser_agent import models
from browser_agent.api import create_app
from browser_agent.auth import create_access_token, local_dev_actor_for_role

TENANT_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


def test_scheduled_task_api_crud_and_run():
    sched_id = uuid.uuid4()
    sched = models.ScheduledTask(
        id=sched_id,
        tenant_id=TENANT_ID,
        name="daily-smoke",
        cron_expression="0 8 * * *",
        concurrency_policy="skip",
        is_active=True,
        task_template={"title": "Daily Smoke", "instructions": "test"},
    )

    class _FakeSession:
        def __init__(self):
            self.schedules = {sched_id: sched}

        def get(self, entity, eid):
            if entity is models.ScheduledTask:
                return self.schedules.get(eid)
            return None

        def execute(self, stmt):
            return SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: list(self.schedules.values())))

        def add(self, item):
            if isinstance(item, models.ScheduledTask):
                self.schedules[item.id] = item

        def commit(self):
            pass

        def close(self):
            pass

    app = create_app()
    app.dependency_overrides[api.get_session] = lambda: _FakeSession()
    client = TestClient(app)

    token_creator = create_access_token(local_dev_actor_for_role("creator"))
    token_operator = create_access_token(local_dev_actor_for_role("operator"))

    # 1. 建立排程
    create_res = client.post(
        "/v1/scheduled-tasks",
        headers={"Authorization": f"Bearer {token_creator}"},
        json={
            "name": "new-schedule",
            "cron_expression": "*/10 * * * *",
            "task_template": {"title": "New Auto Task", "instructions": "Run new task"},
        },
    )
    assert create_res.status_code == 200
    create_data = create_res.json()
    assert create_data["name"] == "new-schedule"
    assert create_data["next_run_at"] is not None

    # 2. 列出排程
    list_res = client.get("/v1/scheduled-tasks", headers={"Authorization": f"Bearer {token_operator}"})
    assert list_res.status_code == 200
    list_data = list_res.json()
    assert len(list_data) >= 1

    # 3. 更新排程
    patch_res = client.patch(
        f"/v1/scheduled-tasks/{sched_id}",
        headers={"Authorization": f"Bearer {token_creator}"},
        json={"is_active": False},
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["is_active"] is False


def test_operations_ui_renders_v12_panels_and_badges():
    client = TestClient(create_app())
    res = client.get("/operations")
    assert res.status_code == 200
    html = res.text

    # V1.2 標題與徽章
    assert "Browser Agent v1.2 Operations Center" in html
    assert "k8s-platform-badge" in html
    assert "otlp-stream-badge" in html

    # V1.2 新增面板
    assert "scheduled-tasks-section" in html
    assert "session-vault-section" in html
    assert "step-video-element" in html
    assert "Scheduled Tasks (Cron Engine)" in html
    assert "Session Vault (Storage State)" in html
