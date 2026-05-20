from __future__ import annotations

import uuid
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from .. import models
from .tasks import set_task_status

def create_approval(
    session: Session,
    task: models.Task,
    approved_by_user_id: uuid.UUID,
    approved_by_label: str,
    note: str | None,
):
    approval = models.Approval(task_id=task.id, approved_by=approved_by_label, note=note)
    task.approved_by = approved_by_user_id
    task.approved_at = task.approved_at or datetime.now(timezone.utc)
    set_task_status(session, task, "queued")
    session.add(approval)
    session.add(task)
    return approval
