import uuid

import pytest

import worker.consumer as consumer
from worker.runner import coerce_task_id


def test_coerce_task_id_accepts_uuid_instance():
    task_id = uuid.uuid4()

    assert coerce_task_id(task_id) == task_id


def test_coerce_task_id_accepts_uuid_string():
    task_id = uuid.uuid4()

    assert coerce_task_id(str(task_id)) == task_id


def test_run_task_with_retries_retries_until_success(monkeypatch):
    task_id = uuid.uuid4()
    attempts = []

    def fake_run_task(received_task_id, mark_failed_on_error):
        attempts.append((received_task_id, mark_failed_on_error))
        if len(attempts) < 3:
            raise RuntimeError("temporary failure")

    failed = []
    monkeypatch.setattr(consumer, "run_task", fake_run_task)
    monkeypatch.setattr(consumer, "mark_task_failed_by_id", lambda *args, **kwargs: failed.append((args, kwargs)))
    monkeypatch.setattr(consumer.time, "sleep", lambda seconds: None)

    consumer._run_task_with_retries(task_id, max_attempts=3, backoff_seconds=0)

    assert attempts == [
        (task_id, False),
        (task_id, False),
        (task_id, False),
    ]
    assert failed == []


def test_run_task_with_retries_marks_failed_after_final_attempt(monkeypatch):
    task_id = uuid.uuid4()
    attempts = []
    failed = []

    def fake_run_task(received_task_id, mark_failed_on_error):
        attempts.append((received_task_id, mark_failed_on_error))
        raise RuntimeError("permanent failure")

    monkeypatch.setattr(consumer, "run_task", fake_run_task)
    monkeypatch.setattr(consumer, "mark_task_failed_by_id", lambda *args, **kwargs: failed.append((args, kwargs)))
    monkeypatch.setattr(consumer.time, "sleep", lambda seconds: None)

    with pytest.raises(RuntimeError, match="permanent failure"):
        consumer._run_task_with_retries(task_id, max_attempts=2, backoff_seconds=0)

    assert attempts == [
        (task_id, False),
        (task_id, False),
    ]
    assert failed[0][0][0] == task_id
    assert str(failed[0][0][1]) == "permanent failure"
    assert failed[0][1]["duration_seconds"] >= 0
