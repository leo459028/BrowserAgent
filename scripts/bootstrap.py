from __future__ import annotations

import os
import time
import uuid
from datetime import datetime, timezone

from confluent_kafka.admin import AdminClient, NewTopic
from sqlalchemy import text
from sqlalchemy.orm import Session

from browser_agent.config import get_settings
from browser_agent.db import get_engine, get_session_factory, Base
from browser_agent import models  # noqa: F401

DEFAULT_TENANT_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
DEFAULT_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000002")
DEFAULT_USER_EMAIL = "ops@example.com"
DEMO_USERS = [
    (DEFAULT_USER_ID, DEFAULT_USER_EMAIL, "admin"),
    (uuid.UUID("00000000-0000-0000-0000-000000000003"), "creator@example.com", "creator"),
    (uuid.UUID("00000000-0000-0000-0000-000000000004"), "approver@example.com", "approver"),
    (uuid.UUID("00000000-0000-0000-0000-000000000005"), "operator@example.com", "operator"),
]

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
        created_at = datetime.now(timezone.utc)
        session.execute(
            text("""
                INSERT INTO tenants (id, name, status, created_at)
                VALUES (:id, :name, :status, :created_at)
                ON CONFLICT (id) DO UPDATE
                SET name = EXCLUDED.name,
                    status = EXCLUDED.status
            """),
            {
                "id": DEFAULT_TENANT_ID,
                "name": "default",
                "status": "active",
                "created_at": created_at,
            },
        )

        for user_id, email, role in DEMO_USERS:
            session.execute(
                text("""
                    INSERT INTO users (id, tenant_id, email, role, created_at)
                    VALUES (:id, :tenant_id, :email, :role, :created_at)
                    ON CONFLICT (id) DO UPDATE
                    SET tenant_id = EXCLUDED.tenant_id,
                        email = EXCLUDED.email,
                        role = EXCLUDED.role
                """),
                {
                    "id": user_id,
                    "tenant_id": DEFAULT_TENANT_ID,
                    "email": email,
                    "role": role,
                    "created_at": created_at,
                },
            )

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
