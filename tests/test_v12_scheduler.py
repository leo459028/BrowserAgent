from __future__ import annotations

import uuid
from datetime import datetime, timezone, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock

from browser_agent import models
from browser_agent.services.scheduler import (
    compute_next_run,
    evaluate_scheduled_tasks,
    trigger_scheduled_task,
)

TENANT_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


def test_compute_next_run_various_cron_expressions():
    base = datetime(2026, 9, 5, 8, 0, 0, tzinfo=timezone.utc)

    # 每 5 分鐘
    next_5m = compute_next_run("*/5 * * * *", from_dt=base)
    assert next_5m == datetime(2026, 9, 5, 8, 5, 0, tzinfo=timezone.utc)

    # 每小時整點
    next_hourly = compute_next_run("0 * * * *", from_dt=base)
    assert next_hourly == datetime(2026, 9, 5, 9, 0, 0, tzinfo=timezone.utc)

    # 每天 08:30
    next_daily = compute_next_run("30 8 * * *", from_dt=base)
    assert next_daily == datetime(2026, 9, 5, 8, 30, 0, tzinfo=timezone.utc)

    # 別名 @hourly
    next_alias = compute_next_run("@hourly", from_dt=base)
    assert next_alias == datetime(2026, 9, 5, 9, 0, 0, tzinfo=timezone.utc)


def test_evaluate_scheduled_tasks_dispatches_due_task():
    now = datetime(2026, 9, 5, 8, 0, 0, tzinfo=timezone.utc)
    sched = models.ScheduledTask(
        id=uuid.uuid4(),
        tenant_id=TENANT_ID,
        name="test-due-schedule",
        cron_expression="*/5 * * * *",
        concurrency_policy="skip",
        is_active=True,
        task_template={"title": "Template Title", "instructions": "Do something"},
        next_run_at=now - timedelta(minutes=1),
        created_at=now - timedelta(days=1),
        updated_at=now - timedelta(days=1),
    )

    fake_session = MagicMock()
    fake_session.execute.return_value.scalars.return_value.all.return_value = [sched]
    fake_session.execute.return_value.scalars.return_value.first.return_value = None

    fake_bus = MagicMock()
    fake_settings = SimpleNamespace(
        reliability_store="memory",
        worker_service_id="worker-test",
    )

    result = evaluate_scheduled_tasks(fake_session, fake_bus, fake_settings, current_time=now)
    assert result["status"] == "success"
    assert result["dispatched"] == 1
    assert result["skipped"] == 0
    assert sched.next_run_at is not None
    assert sched.next_run_at > now


def test_evaluate_scheduled_tasks_skips_when_concurrency_policy_skip_and_task_active():
    now = datetime(2026, 9, 5, 8, 0, 0, tzinfo=timezone.utc)
    sched_id = uuid.uuid4()
    sched = models.ScheduledTask(
        id=sched_id,
        tenant_id=TENANT_ID,
        name="test-skip-schedule",
        cron_expression="*/5 * * * *",
        concurrency_policy="skip",
        is_active=True,
        task_template={"title": "Template Title", "instructions": "Do something"},
        next_run_at=now - timedelta(minutes=1),
        created_at=now - timedelta(days=1),
        updated_at=now - timedelta(days=1),
    )

    existing_active_task = models.Task(
        id=uuid.uuid4(),
        tenant_id=TENANT_ID,
        scheduled_task_id=sched_id,
        status="executing",
        title="Active running task",
        instructions="...",
    )

    fake_session = MagicMock()
    # 第一個 query 查 due schedules
    fake_session.execute.return_value.scalars.return_value.all.return_value = [sched]
    # 第二個 query 查是否有 active task
    fake_session.execute.return_value.scalars.return_value.first.return_value = existing_active_task

    fake_bus = MagicMock()
    fake_settings = SimpleNamespace(reliability_store="memory", worker_service_id="worker-test")

    result = evaluate_scheduled_tasks(fake_session, fake_bus, fake_settings, current_time=now)
    assert result["status"] == "success"
    assert result["dispatched"] == 0
    assert result["skipped"] == 1
