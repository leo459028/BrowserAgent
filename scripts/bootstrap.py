from __future__ import annotations

import os
import time
import uuid

from confluent_kafka.admin import AdminClient, NewTopic
from sqlalchemy.orm import Session

from browser_agent.config import get_settings
from browser_agent.db import get_engine, get_session_factory, Base
from browser_agent import models  # noqa: F401

DEFAULT_TENANT_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
DEFAULT_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000002")
DEFAULT_USER_EMAIL = "ops@example.com"

TOPICS = [
    "agent.tasks.created",
    "agent.tasks.queued",
    "agent.tasks.failed",
    "agent.tasks.completed",
]

def wait_for_database(max_attempts: int = 30, delay_seconds: float = 2.0):
    last_error = None
    for attempt in range(1, max_attempts + 1):
        try:
            engine = get_engine()
            Base.metadata.create_all(bind=engine)
            return engine
        except Exception as exc:
            last_error = exc
            print(f"database not ready ({attempt}/{max_attempts}): {exc}", flush=True)
            time.sleep(delay_seconds)
    raise RuntimeError("database did not become ready") from last_error

def seed_demo_identity() -> None:
    session: Session = get_session_factory()()
    try:
        tenant = session.get(models.Tenant, DEFAULT_TENANT_ID)
        if not tenant:
            session.add(models.Tenant(
                id=DEFAULT_TENANT_ID,
                name="default",
                status="active",
            ))

        user = session.get(models.User, DEFAULT_USER_ID)
        if not user:
            session.add(models.User(
                id=DEFAULT_USER_ID,
                tenant_id=DEFAULT_TENANT_ID,
                email=DEFAULT_USER_EMAIL,
                role="admin",
            ))

        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

def create_kafka_topics(bootstrap_servers: str, max_attempts: int = 30, delay_seconds: float = 2.0) -> None:
    last_error = None
    for attempt in range(1, max_attempts + 1):
        try:
            admin = AdminClient({"bootstrap.servers": bootstrap_servers})
            futures = admin.create_topics([
                NewTopic(topic, num_partitions=3, replication_factor=1)
                for topic in TOPICS
            ])
            for topic, future in futures.items():
                try:
                    future.result(10)
                    print(f"kafka topic created: {topic}", flush=True)
                except Exception as exc:
                    if "TOPIC_ALREADY_EXISTS" in str(exc):
                        print(f"kafka topic exists: {topic}", flush=True)
                    else:
                        raise
            return
        except Exception as exc:
            last_error = exc
            print(f"kafka not ready ({attempt}/{max_attempts}): {exc}", flush=True)
            time.sleep(delay_seconds)
    raise RuntimeError("kafka did not become ready") from last_error

def main():
    settings = get_settings()
    wait_for_database()
    seed_demo_identity()
    if os.getenv("BOOTSTRAP_KAFKA_TOPICS", "").lower() in {"1", "true", "yes"}:
        create_kafka_topics(settings.kafka_bootstrap_servers)
    print("demo bootstrap complete")

if __name__ == "__main__":
    main()
