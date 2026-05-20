from __future__ import annotations

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from prometheus_client import generate_latest

from browser_agent import models
from browser_agent.orchestrator import Orchestrator
from browser_agent.services.tasks import mark_task_failed


TENANT_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
ACTOR_ID = uuid.UUID("00000000-0000-0000-0000-000000000002")


def test_allowed_task_is_pending_approval_and_publishes_correlation_id():
    session = _FakeSession()
    bus = _FakeBus()

    task = Orchestrator(session, bus).create_task(
        TENANT_ID,
        ACTOR_ID,
        {
            "title": "Capture example",
            "instructions": "Open the allowlisted site and capture a screenshot.",
            "priority": 1,
            "risk_level": "low",
            "metadata": {
                "domains": ["example.com"],
                "start_url": "https://example.com",
            },
        },
        correlation_id="cid-v02",
    )

    assert task.status == "pending_approval"
    assert task.correlation_id == "cid-v02"
    assert _audit_actions(session) == ["task.created", "task.pending_approval"]
    assert bus.published[0][0] == "agent.tasks.created"
    assert bus.published[0][2]["correlation_id"] == "cid-v02"
    assert b"browser_agent_tasks_created_total" in generate_latest()


def test_blocked_task_remains_blocked_and_records_created_then_blocked_audit():
    session = _FakeSession()
    bus = _FakeBus()

    task = Orchestrator(session, bus).create_task(
        TENANT_ID,
        ACTOR_ID,
        {
            "title": "Blocked domain",
            "instructions": "Open this site.",
            "risk_level": "low",
            "metadata": {"domains": ["evil.com"]},
        },
        correlation_id="cid-blocked",
    )

    assert task.status == "blocked"
    assert _audit_actions(session) == ["task.created", "task.blocked"]
    assert bus.published[0][2]["correlation_id"] == "cid-blocked"
    assert task.metadata_["policy"]["decision"] == "denied"
    assert task.metadata_["policy"]["reason"] == "domain not allowlisted"


def test_high_risk_task_requires_approval_instead_of_blocking():
    session = _FakeSession()
    bus = _FakeBus()

    task = Orchestrator(session, bus).create_task(
        TENANT_ID,
        ACTOR_ID,
        {
            "title": "Review high risk task",
            "instructions": "Open the allowlisted site and prepare a report.",
            "risk_level": "high",
            "metadata": {"domains": ["example.com"]},
        },
        correlation_id="cid-high-risk",
    )

    assert task.status == "pending_approval"
    assert _audit_actions(session) == ["task.created", "task.pending_approval"]
    assert task.metadata_["policy"] == {
        "decision": "requires_approval",
        "reason": "high-risk task requires manual approval",
        "requires_approval": True,
    }


def test_sensitive_instruction_requires_approval_instead_of_blocking():
    session = _FakeSession()
    bus = _FakeBus()

    task = Orchestrator(session, bus).create_task(
        TENANT_ID,
        ACTOR_ID,
        {
            "title": "Review sensitive task",
            "instructions": "Open the allowlisted site and login to check account status.",
            "risk_level": "medium",
            "metadata": {"domains": ["example.com"]},
        },
        correlation_id="cid-sensitive",
    )

    assert task.status == "pending_approval"
    assert _audit_actions(session) == ["task.created", "task.pending_approval"]
    assert task.metadata_["policy"] == {
        "decision": "requires_approval",
        "reason": "sensitive action requires manual approval",
        "requires_approval": True,
    }


def test_approval_moves_pending_approval_task_to_queued():
    task = SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=TENANT_ID,
        approved_by=None,
        approved_at=None,
        status="pending_approval",
        correlation_id="cid-approve",
        metadata_={},
    )
    session = _FakeSession()
    bus = _FakeBus()

    approval = Orchestrator(session, bus).approve_task(
        task,
        approved_by_user_id=ACTOR_ID,
        approved_by_label="ops@example.com",
        note="local demo",
    )

    assert approval.approved_by == "ops@example.com"
    assert task.approved_by == ACTOR_ID
    assert task.status == "queued"
    assert _audit_actions(session) == ["task.approved", "task.queued"]
    assert bus.published[0][0] == "agent.tasks.queued"
    assert bus.published[0][2]["event_type"] == "task.queued"
    assert bus.published[0][2]["correlation_id"] == "cid-approve"


def test_approval_rejects_non_approvable_status():
    task = SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=TENANT_ID,
        approved_by=None,
        approved_at=None,
        status="blocked",
        correlation_id="cid-reject",
        metadata_={},
    )

    with pytest.raises(ValueError, match="cannot approve task in status blocked"):
        Orchestrator(_FakeSession(), _FakeBus()).approve_task(
            task,
            approved_by_user_id=ACTOR_ID,
            approved_by_label="ops@example.com",
            note=None,
        )


def test_mark_task_failed_sets_error_metadata_and_audit():
    now = datetime.now(timezone.utc)
    task = SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=TENANT_ID,
        status="executing",
        correlation_id="cid-failed",
        metadata_={"existing": True},
        updated_at=now,
        completed_at=None,
    )
    session = _FakeSession()

    mark_task_failed(session, task, RuntimeError("browser crashed"), actor="worker-1")

    assert task.status == "failed"
    assert task.completed_at is not None
    assert task.metadata_["existing"] is True
    assert task.metadata_["error"] == {
        "type": "RuntimeError",
        "message": "browser crashed",
    }
    audit = _audit_entries(session)[0]
    assert audit.action == "task.failed"
    assert audit.payload["correlation_id"] == "cid-failed"
    assert audit.payload["error"]["message"] == "browser crashed"


class _FakeSession:
    def __init__(self):
        self.added = []

    def add(self, obj):
        self.added.append(obj)

    def flush(self):
        for obj in self.added:
            if hasattr(obj, "id") and getattr(obj, "id") is None:
                setattr(obj, "id", uuid.uuid4())


class _FakeBus:
    def __init__(self):
        self.published = []

    def publish(self, topic, key, payload):
        self.published.append((topic, key, payload))


def _audit_entries(session):
    return [obj for obj in session.added if isinstance(obj, models.AuditLog)]


def _audit_actions(session):
    return [entry.action for entry in _audit_entries(session)]
