from __future__ import annotations

import uuid
from types import SimpleNamespace

from fastapi.testclient import TestClient

import browser_agent.api as api
from browser_agent import models
from browser_agent.api import create_app
from browser_agent.auth import create_access_token, local_dev_actor_for_role
from browser_agent.storage import S3ArtifactStore


TENANT_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


def test_s3_artifact_store_writes_governance_metadata_and_reads_content():
    client = _FakeS3Client()
    store = S3ArtifactStore(
        endpoint_url="http://minio:9000",
        access_key="minio",
        secret_key="minio12345",
        bucket="browser-agent",
        client=client,
    )

    stored = store.write_bytes("task-1", "html", b"<html></html>", suffix=".html", content_type="text/html")
    read_back = store.read_bytes(stored.uri)

    assert stored.backend == "s3"
    assert stored.uri.startswith("s3://browser-agent/")
    assert stored.metadata["bucket"] == "browser-agent"
    assert stored.metadata["key"].endswith(".html")
    assert stored.metadata["content_type"] == "text/html"
    assert stored.metadata["redaction"]["status"] == "not_applied"
    assert read_back == b"<html></html>"


def test_artifact_content_endpoint_streams_s3_artifact(monkeypatch):
    artifact_id = uuid.uuid4()
    artifact = SimpleNamespace(
        id=artifact_id,
        task=SimpleNamespace(tenant_id=TENANT_ID),
        uri="s3://browser-agent/2026/05/22/task/html-a.html",
        metadata_={"content_type": "text/html; charset=utf-8", "backend": "s3"},
    )
    session = _FakeSession({models.TaskArtifact: {artifact_id: artifact}})
    store = _FakeArtifactStore()
    monkeypatch.setattr(api, "build_artifact_store_from_settings", lambda settings: store)
    monkeypatch.setattr(api, "get_settings", lambda: SimpleNamespace(artifact_backend="s3"))
    app = create_app()
    app.dependency_overrides[api.get_session] = lambda: session

    response = TestClient(app).get(
        f"/v1/artifacts/{artifact_id}/content",
        headers={"Authorization": f"Bearer {create_access_token(local_dev_actor_for_role('operator'))}"},
    )

    assert response.status_code == 200
    assert response.content == b"<html>from s3</html>"
    assert response.headers["content-type"].startswith("text/html")


class _FakeS3Client:
    def __init__(self):
        self.objects = {}

    def put_object(self, Bucket, Key, Body, ContentType):
        self.objects[(Bucket, Key)] = bytes(Body)

    def get_object(self, Bucket, Key):
        return {"Body": SimpleNamespace(read=lambda: self.objects[(Bucket, Key)])}

    def head_bucket(self, Bucket):
        return {}

    def create_bucket(self, Bucket):
        return {}


class _FakeArtifactStore:
    backend = "s3"

    def read_bytes(self, uri):
        assert uri == "s3://browser-agent/2026/05/22/task/html-a.html"
        return b"<html>from s3</html>"


class _FakeSession:
    def __init__(self, objects):
        self.objects = objects

    def get(self, entity, entity_id):
        return self.objects.get(entity, {}).get(entity_id)

    def close(self):
        return None
