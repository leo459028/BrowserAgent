from __future__ import annotations

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from browser_agent import models
from browser_agent.api import ensure_artifact_access, serialize_task
from browser_agent.storage import LocalArtifactStore, NoopArtifactRedactor


TENANT_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


def test_local_artifact_store_returns_governance_metadata(tmp_path):
    store = LocalArtifactStore(tmp_path, redactor=NoopArtifactRedactor())

    stored = store.write_bytes(
        "task-1",
        "html",
        b"<html><body>secret</body></html>",
        suffix=".html",
        content_type="text/html; charset=utf-8",
    )

    assert stored.backend == "local"
    assert stored.sha256
    assert stored.size_bytes == 32
    assert stored.content_type == "text/html; charset=utf-8"
    assert stored.metadata["retention"]["policy"] == "default"
    assert stored.metadata["redaction"] == {
        "status": "not_applied",
        "strategy": "noop",
    }


def test_serialize_task_exposes_v03_artifact_fields():
    now = datetime.now(timezone.utc)
    artifact_id = uuid.uuid4()
    task = SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=TENANT_ID,
        title="Capture example",
        instructions="Open example.com",
        status="completed",
        correlation_id="cid-v03",
        priority=1,
        risk_level="low",
        metadata_={"evaluation": {"score": 100, "verdict": "pass"}},
        created_at=now,
        updated_at=now,
        steps=[],
        artifacts=[
            SimpleNamespace(
                id=artifact_id,
                artifact_type="html",
                uri="/data/artifacts/2026/05/20/task/html-a.html",
                sha256="abc123456789",
                metadata_={
                    "content_type": "text/html; charset=utf-8",
                    "size_bytes": 128,
                    "backend": "local",
                    "redaction": {"status": "not_applied", "strategy": "noop"},
                },
                created_at=now,
            )
        ],
    )

    payload = serialize_task(task)

    assert payload["artifacts"][0]["content_type"] == "text/html; charset=utf-8"
    assert payload["artifacts"][0]["size_bytes"] == 128
    assert payload["artifacts"][0]["backend"] == "local"
    assert payload["artifacts"][0]["redaction_status"] == "not_applied"
    assert payload["artifacts"][0]["download_url"] == f"/v1/artifacts/{artifact_id}/content"


def test_artifact_access_rejects_tenant_mismatch():
    artifact = SimpleNamespace(
        task=SimpleNamespace(tenant_id=uuid.UUID("10000000-0000-0000-0000-000000000001"))
    )

    with pytest.raises(HTTPException) as exc:
        ensure_artifact_access(artifact, TENANT_ID)

    assert exc.value.status_code == 403
    assert exc.value.detail == "artifact tenant mismatch"


def test_artifact_access_allows_matching_tenant():
    artifact = SimpleNamespace(task=SimpleNamespace(tenant_id=TENANT_ID))

    ensure_artifact_access(artifact, TENANT_ID)


def test_runner_artifact_audit_payload_includes_governance_metadata():
    artifact = {
        "type": "screenshot",
        "uri": "/data/artifacts/shot.png",
        "sha256": "abc123",
        "content_type": "image/png",
        "size_bytes": 456,
        "backend": "local",
        "metadata": {"redaction": {"status": "not_applied", "strategy": "noop"}},
    }

    payload = {
        "artifact_type": artifact["type"],
        "uri": artifact["uri"],
        "sha256": artifact["sha256"],
        "content_type": artifact["content_type"],
        "size_bytes": artifact["size_bytes"],
        "backend": artifact["backend"],
        "redaction": artifact["metadata"]["redaction"],
    }

    assert payload == {
        "artifact_type": "screenshot",
        "uri": "/data/artifacts/shot.png",
        "sha256": "abc123",
        "content_type": "image/png",
        "size_bytes": 456,
        "backend": "local",
        "redaction": {"status": "not_applied", "strategy": "noop"},
    }
