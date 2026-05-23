from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

import browser_agent.api as api
import worker.consumer as consumer
from browser_agent import models
from browser_agent.api import create_app
from browser_agent.auth import create_access_token, local_dev_actor_for_role


TENANT_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


def test_task_create_idempotency_replays_same_task_without_republishing(monkeypatch):
    session = _FakeSession()
    bus = _FakeBus()
    monkeypatch.setattr(api, "get_bus", lambda bootstrap_servers: bus)
    monkeypatch.setattr(api, "get_reliability_store", lambda settings=None: _AllowingStore(), raising=False)
    app = create_app()
    app.dependency_overrides[api.get_session] = lambda: session
    client = TestClient(app)

    headers = {**_auth(_token("creator")), "Idempotency-Key": "ops-key-1"}
    first = client.post("/v1/tasks", json=_task_payload(), headers=headers)
    second = client.post("/v1/tasks", json=_task_payload(), headers=headers)

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["task_id"] == first.json()["task_id"]
    assert second.json()["idempotency"] == {"key": "ops-key-1", "replayed": True}
    assert [event[0] for event in bus.published].count("agent.tasks.created") == 1


def test_task_create_idempotency_key_conflict_returns_409(monkeypatch):
    session = _FakeSession()
    monkeypatch.setattr(api, "get_bus", lambda bootstrap_servers: _FakeBus())
    monkeypatch.setattr(api, "get_reliability_store", lambda settings=None: _AllowingStore(), raising=False)
    app = create_app()
    app.dependency_overrides[api.get_session] = lambda: session
    client = TestClient(app)

    headers = {**_auth(_token("creator")), "Idempotency-Key": "ops-key-conflict"}
    first = client.post("/v1/tasks", json=_task_payload(), headers=headers)
    changed = _task_payload()
    changed["instructions"] = "Open the allowlisted site and capture HTML only."
    second = client.post("/v1/tasks", json=changed, headers=headers)

    assert first.status_code == 200
    assert second.status_code == 409
    assert second.json()["detail"] == "idempotency key already used with a different payload"


def test_task_create_rate_limit_returns_429(monkeypatch):
    session = _FakeSession()
    store = _DenyingRateLimitStore()
    monkeypatch.setattr(api, "get_bus", lambda bootstrap_servers: _FakeBus())
    monkeypatch.setattr(api, "get_reliability_store", lambda settings=None: store, raising=False)
    monkeypatch.setattr(api, "get_settings", lambda: _settings(task_create_rate_limit_per_minute=1))
    app = create_app()
    app.dependency_overrides[api.get_session] = lambda: session
    client = TestClient(app)

    response = client.post("/v1/tasks", json=_task_payload(), headers=_auth(_token("creator")))

    assert response.status_code == 429
    assert response.json()["detail"] == "task create rate limit exceeded"
    assert session.tasks == []


def test_reliability_status_endpoint_is_operator_only(monkeypatch):
    store = _AllowingStore()
    monkeypatch.setattr(api, "get_reliability_store", lambda settings=None: store, raising=False)
    monkeypatch.setattr(api, "get_settings", lambda: _settings())
    app = create_app()
    app.dependency_overrides[api.get_session] = lambda: _FakeSession()
    client = TestClient(app)

    forbidden = client.get("/v1/reliability", headers=_auth(_token("creator")))
    allowed = client.get("/v1/reliability", headers=_auth(_token("operator")))

    assert forbidden.status_code == 403
    assert allowed.status_code == 200
    assert allowed.json()["worker_service_id"] == "worker-v06-test"
    assert allowed.json()["store"]["backend"] == "memory"


def test_worker_skips_task_when_lock_is_already_held(monkeypatch):
    task_id = uuid.uuid4()
    attempts = []
    store = _LockedStore()
    monkeypatch.setattr(consumer, "get_reliability_store", lambda settings=None: store, raising=False)
    monkeypatch.setattr(consumer, "get_settings", lambda: _settings(max_task_retries=1))
    monkeypatch.setattr(consumer, "run_task", lambda *args, **kwargs: attempts.append((args, kwargs)))

    consumer._run_task_with_retries(task_id, max_attempts=1, backoff_seconds=0)

    assert attempts == []
    assert store.acquire_calls == [f"task:{task_id}"]


def test_worker_final_failure_marks_dlq_and_publishes_event(monkeypatch):
    task_id = uuid.uuid4()
    store = _AllowingStore()
    bus = _FakeBus()
    failed = []

    def fail_task(received_task_id, mark_failed_on_error):
        raise RuntimeError("browser crashed")

    monkeypatch.setattr(consumer, "get_reliability_store", lambda settings=None: store, raising=False)
    monkeypatch.setattr(consumer, "get_settings", lambda: _settings(max_task_retries=1))
    monkeypatch.setattr(consumer, "get_bus", lambda bootstrap_servers: bus)
    monkeypatch.setattr(consumer, "run_task", fail_task)
    monkeypatch.setattr(
        consumer,
        "mark_task_failed_by_id",
        lambda *args, **kwargs: failed.append((args, kwargs)),
    )
    monkeypatch.setattr(consumer.time, "sleep", lambda seconds: None)

    with pytest.raises(RuntimeError, match="browser crashed"):
        consumer._run_task_with_retries(task_id, max_attempts=1, backoff_seconds=0)

    assert failed[0][0][0] == task_id
    assert failed[0][1]["actor"] == "service:worker-v06-test"
    assert failed[0][1]["dlq_payload"]["status"] == "pending"
    assert bus.published[0][0] == "agent.tasks.dlq"
    assert bus.published[0][2]["task_id"] == str(task_id)
    assert bus.published[0][2]["worker_id"] == "worker-v06-test"


def test_dlq_list_and_replay_are_operator_only(monkeypatch):
    task = _failed_dlq_task()
    session = _FakeSession(tasks=[task])
    bus = _FakeBus()
    monkeypatch.setattr(api, "get_bus", lambda bootstrap_servers: bus)
    monkeypatch.setattr(api, "get_settings", lambda: _settings())
    app = create_app()
    app.dependency_overrides[api.get_session] = lambda: session
    client = TestClient(app)

    creator_list = client.get("/v1/dlq/tasks", headers=_auth(_token("creator")))
    operator_list = client.get("/v1/dlq/tasks", headers=_auth(_token("operator")))
    replay = client.post(f"/v1/dlq/tasks/{task.id}/replay", headers=_auth(_token("operator")))

    assert creator_list.status_code == 403
    assert operator_list.status_code == 200
    assert operator_list.json()[0]["task_id"] == str(task.id)
    assert replay.status_code == 200
    assert replay.json()["status"] == "queued"
    assert task.status == "queued"
    assert task.metadata_["reliability"]["replay"]["count"] == 1
    assert bus.published[0][0] == "agent.tasks.queued"


def test_operations_center_renders_reliability_panel():
    client = TestClient(create_app())

    response = client.get("/operations")

    assert response.status_code == 200
    assert "Browser Agent v1.0 Operations Center" in response.text
    assert "Reliability / DLQ" in response.text
    assert "Idempotency" in response.text


def _task_payload() -> dict:
    return {
        "title": "Capture example",
        "instructions": "Open the allowlisted site and capture a screenshot.",
        "priority": 1,
        "risk_level": "low",
        "metadata": {
            "domains": ["example.com"],
            "start_url": "https://example.com",
            "expected_domain": "example.com",
        },
    }


def _failed_dlq_task():
    return SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=TENANT_ID,
        created_by=local_dev_actor_for_role("creator").user_id,
        title="Failed task",
        instructions="Open the allowlisted site.",
        priority=1,
        risk_level="low",
        status="failed",
        approved_by=local_dev_actor_for_role("approver").user_id,
        approved_at=None,
        planned_at=None,
        started_at=None,
        completed_at=None,
        idempotency_key=None,
        correlation_id="cid-dlq",
        metadata_={
            "reliability": {
                "dlq": {
                    "status": "pending",
                    "topic": "agent.tasks.dlq",
                    "worker_id": "worker-v06-test",
                    "attempts": 1,
                    "error": {"type": "RuntimeError", "message": "browser crashed"},
                }
            }
        },
        created_at=SimpleNamespace(isoformat=lambda: "2026-05-22T00:00:00+00:00"),
        updated_at=SimpleNamespace(isoformat=lambda: "2026-05-22T00:00:00+00:00"),
        steps=[],
        artifacts=[],
    )


def _token(role: str) -> str:
    return create_access_token(local_dev_actor_for_role(role))


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _settings(**overrides):
    defaults = {
        "app_name": "browser-agent",
        "app_log_level": "INFO",
        "kafka_bootstrap_servers": "",
        "task_create_rate_limit_per_minute": 60,
        "idempotency_ttl_seconds": 86400,
        "task_lock_ttl_seconds": 300,
        "max_task_retries": 2,
        "worker_service_id": "worker-v06-test",
        "dlq_topic": "agent.tasks.dlq",
        "reliability_store": "memory",
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


class _FakeSession:
    def __init__(self, tasks=None):
        self.tasks = list(tasks or [])
        self.added = []
        self.commits = 0

    def add(self, obj):
        self.added.append(obj)
        if isinstance(obj, models.Task) and obj not in self.tasks:
            self.tasks.append(obj)

    def flush(self):
        for obj in self.added:
            if hasattr(obj, "id") and getattr(obj, "id", None) is None:
                setattr(obj, "id", uuid.uuid4())

    def commit(self):
        self.commits += 1

    def rollback(self):
        return None

    def close(self):
        return None

    def get(self, entity, entity_id):
        if entity is models.Task:
            return next((task for task in self.tasks if task.id == entity_id), None)
        return None

    def execute(self, statement):
        entity = statement.column_descriptions[0]["entity"]
        if entity is models.Task:
            sql = str(statement)
            rows = list(self.tasks)
            params = statement.compile().params
            key = _first_param(params, "idempotency_key")
            tenant = _first_param(params, "tenant_id")
            status = _first_param(params, "status")
            if key is not None:
                rows = [task for task in rows if getattr(task, "idempotency_key", None) == key]
            if tenant is not None:
                rows = [task for task in rows if getattr(task, "tenant_id", None) == tenant]
            if status is not None:
                rows = [task for task in rows if getattr(task, "status", None) == status]
            return _FakeQueryResult(rows)
        return _FakeQueryResult([])


class _FakeQueryResult:
    def __init__(self, rows):
        self.rows = rows

    def scalars(self):
        return self

    def all(self):
        return self.rows

    def first(self):
        return self.rows[0] if self.rows else None

    def scalar_one_or_none(self):
        return self.first()


class _FakeBus:
    def __init__(self):
        self.published = []

    def publish(self, topic, key, payload):
        self.published.append((topic, key, payload))


class _AllowingStore:
    backend = "memory"

    def __init__(self):
        self.acquire_calls = []

    def check_rate_limit(self, scope, limit, window_seconds):
        return SimpleNamespace(allowed=True, remaining=max(limit - 1, 0), reset_seconds=window_seconds)

    def acquire_lock(self, key, owner, ttl_seconds):
        self.acquire_calls.append(key)
        return True

    def release_lock(self, key, owner):
        return True

    def status(self):
        return {"backend": self.backend, "available": True}


class _DenyingRateLimitStore(_AllowingStore):
    def check_rate_limit(self, scope, limit, window_seconds):
        return SimpleNamespace(allowed=False, remaining=0, reset_seconds=60)


class _LockedStore(_AllowingStore):
    def acquire_lock(self, key, owner, ttl_seconds):
        self.acquire_calls.append(key)
        return False


def _first_param(params: dict, prefix: str):
    for key, value in params.items():
        if key.startswith(prefix):
            return value
    return None
