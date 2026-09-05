from __future__ import annotations

import uuid
import time
from sqlalchemy import select
from sqlalchemy.orm import Session
from browser_agent.config import get_settings
from browser_agent.db import get_session_factory
from browser_agent import models
from browser_agent.runner import TaskRunner
from browser_agent.services.tasks import mark_task_failed

def coerce_task_id(task_id: str | uuid.UUID) -> uuid.UUID:
    if isinstance(task_id, uuid.UUID):
        return task_id
    return uuid.UUID(task_id)

def run_task(task_id: str | uuid.UUID, *, mark_failed_on_error: bool = True):
    session: Session = get_session_factory()()
    task_uuid = coerce_task_id(task_id)
    started = time.monotonic()
    try:
        task = session.execute(select(models.Task).where(models.Task.id == task_uuid)).scalar_one()
        settings = get_settings()
        runner = TaskRunner(
            session=session,
            artifact_base_path=settings.artifact_base_path,
            headless=settings.browser_headless,
            allowed_domains=settings.allowlist_domain_set,
            timeout_seconds=settings.task_timeout_seconds,
            worker_actor=f"service:{settings.worker_service_id}",
            record_video=settings.worker_record_video_default,
        )
        runner.run(task)
        session.commit()
    except Exception as exc:
        session.rollback()
        if mark_failed_on_error:
            mark_task_failed_by_id(task_uuid, exc, duration_seconds=time.monotonic() - started)
        raise
    finally:
        session.close()

def mark_task_failed_by_id(
    task_id: uuid.UUID,
    exc: Exception | None = None,
    duration_seconds: float | None = None,
    actor: str = "worker",
    dlq_payload: dict | None = None,
):
    session: Session = get_session_factory()()
    try:
        task = session.execute(select(models.Task).where(models.Task.id == task_id)).scalar_one_or_none()
        if not task:
            return
        mark_task_failed(
            session,
            task,
            exc or RuntimeError("task execution failed"),
            actor=actor,
            duration_seconds=duration_seconds,
            dlq_payload=dlq_payload,
        )
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
