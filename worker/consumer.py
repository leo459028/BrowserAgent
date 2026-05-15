from __future__ import annotations

import json
import logging
import uuid
from sqlalchemy.orm import Session
from sqlalchemy import select

from browser_agent.config import get_settings
from browser_agent.db import get_session_factory
from browser_agent.kafka import get_bus
from browser_agent import models
from worker.runner import run_task

logger = logging.getLogger(__name__)

def main():
    settings = get_settings()
    bus = get_bus(settings.kafka_bootstrap_servers)
    consumer = bus.consumer("browser-agent-worker", ["agent.tasks.created", "agent.tasks.approved"])

    while True:
        msg = consumer.poll(1.0)
        if msg is None:
            continue
        if msg.error():
            logger.warning("kafka message error", extra={"error": str(msg.error())})
            continue

        event = json.loads(msg.value().decode("utf-8"))
        task_id = uuid.UUID(event["task_id"])

        session: Session = get_session_factory()()
        try:
            task = session.execute(select(models.Task).where(models.Task.id == task_id)).scalar_one_or_none()
            if not task:
                consumer.commit(msg)
                continue
            if task.status in {"completed", "review"}:
                consumer.commit(msg)
                continue
            if task.status not in {"approved", "created"}:
                consumer.commit(msg)
                continue

            if task.status == "created" and not task.approved_at:
                session.commit()
                consumer.commit(msg)
                continue

            run_task(task_id)
            consumer.commit(msg)
        except Exception as exc:
            session.rollback()
            logger.exception("task execution failed", extra={"task_id": task_id, "error": str(exc)})
            consumer.commit(msg)
        finally:
            session.close()

if __name__ == "__main__":
    main()
