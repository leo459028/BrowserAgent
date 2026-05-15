from __future__ import annotations

from sqlalchemy.orm import Session
from .. import models

def create_approval(session: Session, task: models.Task, approved_by: str, note: str | None):
    approval = models.Approval(task_id=task.id, approved_by=approved_by, note=note)
    task.approved_by = approved_by
    task.approved_at = task.approved_at or task.created_at
    task.status = "approved"
    session.add(approval)
    session.add(task)
    return approval
