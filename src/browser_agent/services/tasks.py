from __future__ import annotations

from datetime import datetime, timezone
from sqlalchemy.orm import Session
from .. import models

def get_task(session: Session, task_id):
    return session.get(models.Task, task_id)

def set_task_status(session: Session, task: models.Task, status: str, extra: dict | None = None):
    task.status = status
    task.updated_at = datetime.now(timezone.utc)
    if extra:
        task.metadata = {**(task.metadata or {}), **extra}
    session.add(task)
    return task

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
