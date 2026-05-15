from __future__ import annotations

import uuid
from sqlalchemy import select
from sqlalchemy.orm import Session
from browser_agent.config import get_settings
from browser_agent.db import get_session_factory
from browser_agent import models
from browser_agent.runner import TaskRunner

def coerce_task_id(task_id: str | uuid.UUID) -> uuid.UUID:
    if isinstance(task_id, uuid.UUID):
        return task_id
    return uuid.UUID(task_id)

def run_task(task_id: str | uuid.UUID):
    session: Session = get_session_factory()()
    try:
        task = session.execute(select(models.Task).where(models.Task.id == coerce_task_id(task_id))).scalar_one()
        settings = get_settings()
        runner = TaskRunner(
            session=session,
            artifact_base_path=settings.artifact_base_path,
            headless=settings.browser_headless,
            allowed_domains=settings.allowlist_domain_set,
        )
        runner.run(task)
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
