from __future__ import annotations

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

from fastapi.testclient import TestClient

import browser_agent.api as api
from browser_agent import models
from browser_agent.api import create_app
from browser_agent.auth import create_access_token, local_dev_actor_for_role
from browser_agent.runner import _artifact_media_type

TENANT_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


def test_artifact_media_type_video_and_storage_state():
    assert _artifact_media_type("video") == "video/webm"
    assert _artifact_media_type("storage_state") == "application/json"


def test_video_endpoint_and_replay_integration():
    task_id = uuid.uuid4()
    video_art_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    video_art = models.TaskArtifact(
        id=video_art_id,
        task_id=task_id,
        artifact_type="video",
        uri="local:///tmp/video.webm",
        sha256="fake-webm-hash",
        metadata_={"backend": "local", "content_type": "video/webm"},
        created_at=now,
    )
    task = models.Task(
        id=task_id,
        tenant_id=TENANT_ID,
        title="Video Recording Task",
        instructions="Record test",
        status="completed",
        artifacts=[video_art],
        steps=[],
    )

    class _FakeSession:
        def get(self, entity, entity_id):
            if entity is models.Task and entity_id == task_id:
                return task
            return None

        def execute(self, stmt):
            return SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: []))

        def close(self):
            pass

    app = create_app()
    app.dependency_overrides[api.get_session] = lambda: _FakeSession()
    client = TestClient(app)

    token = create_access_token(local_dev_actor_for_role("operator"))
    headers = {"Authorization": f"Bearer {token}"}

    # 1. 測試 replay 輸出包含 video_artifact_id 與 video_url
    rep_res = client.get(f"/v1/tasks/{task_id}/replay", headers=headers)
    assert rep_res.status_code == 200
    rep_data = rep_res.json()
    assert rep_data["video_artifact_id"] == str(video_art_id)
    assert rep_data["video_url"] == f"/v1/artifacts/{video_art_id}/content"

    # 2. 測試 /v1/tasks/{task_id}/video 端點
    vid_res = client.get(f"/v1/tasks/{task_id}/video", headers=headers, follow_redirects=False)
    assert vid_res.status_code == 307
    assert vid_res.headers["location"] == f"/v1/artifacts/{video_art_id}/content"
