from __future__ import annotations

import json
import logging
import time
import uuid
from sqlalchemy.orm import Session
from sqlalchemy import select

from browser_agent.config import get_settings
from browser_agent.db import get_session_factory
from browser_agent.kafka import get_bus
from browser_agent import models
from worker.runner import mark_task_failed_by_id, run_task

logger = logging.getLogger(__name__)

def main():
    settings = get_settings()
    bus = get_bus(settings.kafka_bootstrap_servers)
    consumer = bus.consumer("browser-agent-worker", ["agent.tasks.queued"])

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
            if task.status in {"blocked", "completed", "review", "failed", "cancelled"}:
                consumer.commit(msg)
                continue
            if task.status != "queued":
                consumer.commit(msg)
                continue

            _run_task_with_retries(task_id)
            consumer.commit(msg)
        except Exception as exc:
            session.rollback()
            logger.exception("task execution failed", extra={"task_id": task_id, "error": str(exc)})
            consumer.commit(msg)
        finally:
            session.close()

def _run_task_with_retries(task_id: uuid.UUID, max_attempts: int = 3, backoff_seconds: float = 1.0):
    started = time.monotonic()
    last_error = None
    for attempt in range(1, max_attempts + 1):
        try:
            run_task(task_id, mark_failed_on_error=False)
            return
        except Exception as exc:
            last_error = exc
            logger.exception(
                "task execution attempt failed",
                extra={"task_id": str(task_id), "attempt": attempt, "error": str(exc)},
            )
            if attempt < max_attempts:
                time.sleep(backoff_seconds * attempt)
    mark_task_failed_by_id(
        task_id,
        last_error or RuntimeError("task execution failed"),
        duration_seconds=time.monotonic() - started,
    )
    raise last_error or RuntimeError("task execution failed")

if __name__ == "__main__":
    main()
