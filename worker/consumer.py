from __future__ import annotations

import json
import logging
import time
import uuid
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import select

from browser_agent.config import get_settings
from browser_agent.db import get_session_factory
from browser_agent.kafka import get_bus
from browser_agent.metrics import TASK_DLQ
from browser_agent.reliability import get_reliability_store
from browser_agent import models
from worker.runner import mark_task_failed_by_id, run_task

logger = logging.getLogger(__name__)

def main():
    settings = get_settings()
    bus = get_bus(settings.kafka_bootstrap_servers)

    # V1.3 優先權佇列與 Worker 資源池配置
    pool_type = getattr(settings, "worker_pool", "default").lower()
    if getattr(settings, "multi_priority_enabled", True):
        if pool_type == "high-only":
            topics = [settings.queue_high_topic]
        elif pool_type == "batch-only":
            topics = [settings.queue_batch_topic]
        else:
            topics = [settings.queue_high_topic, settings.queue_default_topic, settings.queue_batch_topic]
    else:
        topics = ["agent.tasks.queued"]

    consumer = bus.consumer(f"browser-agent-worker-{pool_type}", topics)


    while True:
        msg = consumer.poll(1.0)
        if msg is None:
            continue
        if msg.error():
            logger.warning("kafka message error", extra={"error": str(msg.error())})
            continue

        event = json.loads(msg.value().decode("utf-8"))
        task_id = uuid.UUID(event["task_id"])
        trace_context = event.get("trace_context") or {}

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

            trace_id = trace_context.get("trace_id") or (task.correlation_id or "").replace("-", "") or "0" * 32
            parent_span_id = trace_context.get("span_id")
            from browser_agent.tracing import generate_span_id, get_trace_buffer, Span
            worker_span_id = generate_span_id()
            updated_trace_context = {
                "trace_id": trace_id,
                "span_id": worker_span_id,
                "parent_span_id": parent_span_id,
            }
            task.metadata_ = {**(task.metadata_ or {}), "trace_context": updated_trace_context}
            session.add(task)
            session.commit()

            logger.info(
                "worker received task",
                extra={
                    "task_id": str(task_id),
                    "correlation_id": event.get("correlation_id"),
                    "trace_id": trace_id,
                    "span_id": worker_span_id,
                    "parent_span_id": parent_span_id,
                    "event_name": "worker.task.received",
                    "service_name": "browser-agent-worker",
                    "service_version": getattr(settings, "app_version", "1.1.0"),
                    "environment": getattr(settings, "app_env", "local"),
                },
            )
            worker_started = time.monotonic()
            _run_task_with_retries(task_id, max_attempts=settings.max_task_retries)
            get_trace_buffer().record(Span(
                name="worker.process_task",
                trace_id=trace_id,
                span_id=worker_span_id,
                parent_span_id=parent_span_id,
                service="browser-agent-worker",
                duration_ms=round((time.monotonic() - worker_started) * 1000, 2),
                status="ok",
                attributes={"task_id": str(task_id)},
            ))
            consumer.commit(msg)
        except Exception as exc:
            session.rollback()
            logger.exception("task execution failed", extra={"task_id": task_id, "error": str(exc)})
            consumer.commit(msg)
        finally:
            session.close()

def _run_task_with_retries(task_id: uuid.UUID, max_attempts: int | None = None, backoff_seconds: float = 1.0):
    settings = get_settings()
    max_attempts = max_attempts or settings.max_task_retries
    worker_id = settings.worker_service_id
    worker_actor = f"service:{worker_id}"
    lock_key = f"task:{task_id}"
    store = get_reliability_store(settings)
    if not store.acquire_lock(lock_key, worker_id, settings.task_lock_ttl_seconds):
        logger.info("task lock already held", extra={"task_id": str(task_id), "worker_id": worker_id})
        return

    started = time.monotonic()
    last_error = None
    try:
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
        final_error = last_error or RuntimeError("task execution failed")
        dlq_payload = _dlq_payload(settings, task_id, worker_id, max_attempts, final_error)
        mark_task_failed_by_id(
            task_id,
            final_error,
            duration_seconds=time.monotonic() - started,
            actor=worker_actor,
            dlq_payload=dlq_payload,
        )
        _publish_dlq_event(settings, task_id, dlq_payload)
        TASK_DLQ.inc()
        raise final_error
    finally:
        store.release_lock(lock_key, worker_id)


def _dlq_payload(settings, task_id: uuid.UUID, worker_id: str, attempts: int, exc: Exception) -> dict:
    return {
        "status": "pending",
        "topic": settings.dlq_topic,
        "worker_id": worker_id,
        "attempts": attempts,
        "failed_at": datetime.now(timezone.utc).isoformat(),
        "error": {
            "type": exc.__class__.__name__,
            "message": str(exc),
        },
        "task_id": str(task_id),
    }


def _publish_dlq_event(settings, task_id: uuid.UUID, dlq_payload: dict) -> None:
    try:
        bus = get_bus(settings.kafka_bootstrap_servers)
        bus.publish(settings.dlq_topic, str(task_id), {
            "event_id": str(uuid.uuid4()),
            "event_type": "task.dlq",
            **dlq_payload,
        })
    except Exception as exc:
        logger.exception("failed to publish dlq event", extra={"task_id": str(task_id), "error": str(exc)})

if __name__ == "__main__":
    main()
