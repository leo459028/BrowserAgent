from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

import browser_agent.api as api
from browser_agent import models
from browser_agent.api import create_app
from browser_agent.auth import create_access_token, local_dev_actor_for_role

TENANT_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


def test_session_vault_list_and_revoke():
    art_id = uuid.uuid4()
    task_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    session_artifact = models.TaskArtifact(
        id=art_id,
        task_id=task_id,
        artifact_type="storage_state",
        uri="memory://storage_state.json",
        sha256="fake-hash",
        metadata_={
            "session_name": "vendor-session",
            "cookies_count": 5,
            "backend": "local",
            "status": "valid",
        },
        created_at=now,
    )
    task = models.Task(
        id=task_id,
        tenant_id=TENANT_ID,
        title="Session Test Task",
        instructions="...",
        status="completed",
        artifacts=[session_artifact],
    )

    class _FakeSession:
        def __init__(self):
            self.added = []

        def execute(self, stmt):
            return SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: [session_artifact]))

        def add(self, item):
            self.added.append(item)

        def commit(self):
            pass

        def close(self):
            pass

    app = create_app()
    app.dependency_overrides[api.get_session] = lambda: _FakeSession()
    client = TestClient(app)

    token_operator = create_access_token(local_dev_actor_for_role("operator"))
    token_admin = create_access_token(local_dev_actor_for_role("admin"))

    # 1. 查詢 sessions 清單
    res = client.get("/v1/sessions", headers={"Authorization": f"Bearer {token_operator}"})
    assert res.status_code == 200
    sessions = res.json()
    assert len(sessions) == 1
    assert sessions[0]["session_name"] == "vendor-session"
    assert sessions[0]["cookies_count"] == 5

    # 2. 撤銷 session (需 admin 權限)
    res_del = client.delete("/v1/sessions/vendor-session", headers={"Authorization": f"Bearer {token_admin}"})
    assert res_del.status_code == 200
    del_data = res_del.json()
    assert del_data["revoked"] is True
    assert del_data["session_name"] == "vendor-session"
    assert session_artifact.metadata_["status"] == "revoked"
