from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models
from ..audit import write_audit
from ..orchestrator import Orchestrator
from ..reliability import get_reliability_store


def parse_cron_field(field_str: str, min_val: int, max_val: int) -> set[int]:
    """Parse a single cron field into a set of allowed integers."""
    allowed = set()
    for part in field_str.split(","):
        part = part.strip()
        if not part:
            continue
        if part == "*":
            allowed.update(range(min_val, max_val + 1))
        elif part.startswith("*/"):
            step = int(part[2:])
            allowed.update(range(min_val, max_val + 1, step))
        elif "-" in part:
            start_str, end_str = part.split("-", 1)
            start, end = int(start_str), int(end_str)
            allowed.update(range(start, end + 1))
        else:
            allowed.add(int(part))
    return allowed


def normalize_cron_expression(expr: str) -> str:
    expr = expr.strip()
    aliases = {
        "@yearly": "0 0 1 1 *",
        "@annually": "0 0 1 1 *",
        "@monthly": "0 0 1 * *",
        "@weekly": "0 0 * * 0",
        "@daily": "0 0 * * *",
        "@midnight": "0 0 * * *",
        "@hourly": "0 * * * *",
        "@every_minute": "* * * * *",
        "@every_5m": "*/5 * * * *",
        "@every_10m": "*/10 * * * *",
        "@every_30m": "*/30 * * * *",
    }
    return aliases.get(expr, expr)


def compute_next_run(cron_expr: str, from_dt: datetime | None = None) -> datetime:
    """Compute the next UTC datetime matching the cron expression."""
    cron_expr = normalize_cron_expression(cron_expr)
    parts = cron_expr.split()
    if len(parts) != 5:
        raise ValueError(f"Invalid cron expression: expected 5 fields, got {len(parts)} in '{cron_expr}'")

    min_set = parse_cron_field(parts[0], 0, 59)
    hour_set = parse_cron_field(parts[1], 0, 23)
    dom_set = parse_cron_field(parts[2], 1, 31)
    month_set = parse_cron_field(parts[3], 1, 12)
    dow_set = parse_cron_field(parts[4], 0, 6)

    if from_dt is None:
        from_dt = datetime.now(timezone.utc)
    else:
        if from_dt.tzinfo is None:
            from_dt = from_dt.replace(tzinfo=timezone.utc)

    # 起始時間點進位至下一分鐘（秒數歸零）
    current = from_dt.replace(second=0, microsecond=0) + timedelta(minutes=1)

    # 往後搜尋最多 525,600 分鐘（1年）
    for _ in range(525600):
        if current.month not in month_set:
            # 步進至下個月的第 1 天 00:00
            if current.month == 12:
                current = current.replace(year=current.year + 1, month=1, day=1, hour=0, minute=0)
            else:
                current = current.replace(month=current.month + 1, day=1, hour=0, minute=0)
            continue

        if current.day not in dom_set:
            current = (current + timedelta(days=1)).replace(hour=0, minute=0)
            continue

        # Python weekday: Monday is 0 and Sunday is 6. Standard cron: 0 is Sunday, 6 is Saturday.
        cron_dow = (current.weekday() + 1) % 7
        if cron_dow not in dow_set:
            current = (current + timedelta(days=1)).replace(hour=0, minute=0)
            continue

        if current.hour not in hour_set:
            current = (current + timedelta(hours=1)).replace(minute=0)
            continue

        if current.minute in min_set:
            return current

        current += timedelta(minutes=1)

    raise ValueError(f"Could not find matching next run time for cron expression: '{cron_expr}'")


def evaluate_scheduled_tasks(session: Session, bus, settings, current_time: datetime | None = None) -> dict:
    """Evaluate due scheduled tasks and dispatch corresponding Task objects."""
    now = current_time or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    store = get_reliability_store(settings)
    lock_key = "task-scheduler-lock"
    owner = getattr(settings, "worker_service_id", "scheduler")
    acquired = store.acquire_lock(lock_key, owner=owner, ttl_seconds=55)
    if not acquired:
        return {"status": "locked", "dispatched": 0, "skipped": 0}

    dispatched_tasks = []
    skipped_tasks = []

    try:
        stmt = select(models.ScheduledTask).where(
            models.ScheduledTask.is_active == True,
            (models.ScheduledTask.next_run_at == None) | (models.ScheduledTask.next_run_at <= now),
        )
        due_schedules = session.execute(stmt).scalars().all()

        for sched in due_schedules:
            if sched.concurrency_policy == "skip":
                active_task = session.execute(
                    select(models.Task).where(
                        models.Task.scheduled_task_id == sched.id,
                        models.Task.status.in_(["created", "pending_approval", "approved", "queued", "executing"]),
                    )
                ).scalars().first()

                if active_task:
                    write_audit(
                        session,
                        sched.tenant_id,
                        "scheduler",
                        "scheduled_task.skipped",
                        "scheduled_task",
                        str(sched.id),
                        {
                            "scheduled_task_name": sched.name,
                            "reason": "concurrency_skip_active_task_exists",
                            "active_task_id": str(active_task.id),
                        },
                    )
                    sched.last_run_at = now
                    sched.next_run_at = compute_next_run(sched.cron_expression, from_dt=now)
                    session.add(sched)
                    skipped_tasks.append(str(sched.id))
                    continue

            # 派發任務
            orch = Orchestrator(session, bus)
            correlation_id = str(uuid.uuid4())
            payload = dict(sched.task_template)
            payload.setdefault("title", f"Scheduled: {sched.name}")
            payload.setdefault("instructions", f"Executed via scheduled task: {sched.name}")
            payload.setdefault("risk_level", "low")
            payload.setdefault("priority", 1)

            created_task = orch.create_task(
                tenant_id=sched.tenant_id,
                created_by=sched.created_by,
                payload=payload,
                correlation_id=correlation_id,
                actor_label="scheduler",
                actor_payload={"source": "scheduled_task", "scheduled_task_id": str(sched.id)},
            )
            created_task.scheduled_task_id = sched.id
            session.add(created_task)

            sched.last_run_at = now
            sched.next_run_at = compute_next_run(sched.cron_expression, from_dt=now)
            session.add(sched)

            write_audit(
                session,
                sched.tenant_id,
                "scheduler",
                "scheduled_task.triggered",
                "scheduled_task",
                str(sched.id),
                {
                    "scheduled_task_name": sched.name,
                    "generated_task_id": str(created_task.id),
                    "next_run_at": sched.next_run_at.isoformat(),
                },
            )
            dispatched_tasks.append(str(created_task.id))

        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        store.release_lock(lock_key, owner=owner)

    return {
        "status": "success",
        "dispatched": len(dispatched_tasks),
        "dispatched_task_ids": dispatched_tasks,
        "skipped": len(skipped_tasks),
        "skipped_schedule_ids": skipped_tasks,
    }


def trigger_scheduled_task(session: Session, bus, sched: models.ScheduledTask, actor_email: str = "operator") -> models.Task:
    """Manually trigger a scheduled task immediately (Run Now)."""
    now = datetime.now(timezone.utc)
    orch = Orchestrator(session, bus)
    correlation_id = str(uuid.uuid4())
    payload = dict(sched.task_template)
    payload.setdefault("title", f"Manual Run: {sched.name}")
    payload.setdefault("instructions", f"Manually triggered via scheduled task: {sched.name}")
    payload.setdefault("risk_level", "low")
    payload.setdefault("priority", 2)

    created_task = orch.create_task(
        tenant_id=sched.tenant_id,
        created_by=sched.created_by,
        payload=payload,
        correlation_id=correlation_id,
        actor_label=actor_email,
        actor_payload={"source": "scheduled_task_manual", "scheduled_task_id": str(sched.id)},
    )
    created_task.scheduled_task_id = sched.id
    session.add(created_task)

    sched.last_run_at = now
    sched.next_run_at = compute_next_run(sched.cron_expression, from_dt=now)
    session.add(sched)

    write_audit(
        session,
        sched.tenant_id,
        actor_email,
        "scheduled_task.manual_triggered",
        "scheduled_task",
        str(sched.id),
        {
            "scheduled_task_name": sched.name,
            "generated_task_id": str(created_task.id),
            "next_run_at": sched.next_run_at.isoformat(),
        },
    )
    session.commit()
    return created_task
