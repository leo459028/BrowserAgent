from __future__ import annotations

from datetime import datetime, timezone
from sqlalchemy.orm import Session
from .. import models
from ..audit import write_audit
from ..metrics import TASK_DURATION, TASK_FAILED

APPROVABLE_STATUSES = {"created", "pending_approval"}
TERMINAL_STATUSES = {"blocked", "completed", "review", "failed", "cancelled"}

def get_task(session: Session, task_id):
    return session.get(models.Task, task_id)

def set_task_status(session: Session, task: models.Task, status: str, extra: dict | None = None):
    task.status = status
    task.updated_at = datetime.now(timezone.utc)
    if extra:
        task.metadata_ = {**(getattr(task, "metadata_", {}) or {}), **extra}
    session.add(task)
    return task

def set_task_status_with_audit(
    session: Session,
    task: models.Task,
    status: str,
    *,
    action: str,
    actor: str | None = None,
    payload: dict | None = None,
):
    set_task_status(session, task, status)
    write_audit(
        session,
        task.tenant_id,
        actor,
        action,
        "task",
        str(task.id),
        {
            **(payload or {}),
            "status": status,
            "correlation_id": getattr(task, "correlation_id", None),
        },
    )
    return task

def mark_task_failed(
    session: Session,
    task: models.Task,
    exc: Exception,
    actor: str | None = None,
    duration_seconds: float | None = None,
    dlq_payload: dict | None = None,
):
    error = {
        "type": exc.__class__.__name__,
        "message": str(exc),
    }
    task.completed_at = datetime.now(timezone.utc)
    metadata = {**(getattr(task, "metadata_", {}) or {}), "error": error}
    if dlq_payload:
        reliability = dict(metadata.get("reliability") or {})
        reliability["dlq"] = dlq_payload
        metadata["reliability"] = reliability
    task.metadata_ = metadata
    TASK_FAILED.inc()
    if duration_seconds is not None:
        TASK_DURATION.observe(max(duration_seconds, 0.0))
    elif started_at := getattr(task, "started_at", None):
        TASK_DURATION.observe(max((task.completed_at - started_at).total_seconds(), 0.0))
    return set_task_status_with_audit(
        session,
        task,
        "failed",
        action="task.failed",
        actor=actor,
        payload={"error": error, **({"dlq": dlq_payload} if dlq_payload else {})},
    )

def add_step(session: Session, task: models.Task, step_no: int, action_type: str, instruction: str, target: str | None = None, input_data: dict | None = None):
    step = models.TaskStep(
        task_id=task.id,
        step_no=step_no,
        action_type=action_type,
        target=target,
        instruction=instruction,
        status="created",
        input_data=input_data or {},
        output_data={},
    )
    session.add(step)
    session.flush()
    return step
