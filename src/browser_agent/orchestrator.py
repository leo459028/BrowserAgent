from __future__ import annotations

import uuid
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from . import models
from .policy import evaluate_task_policy
from .security import inspect_instructions

class Orchestrator:
    def __init__(self, session: Session, bus):
        self.session = session
        self.bus = bus

    def create_task(self, tenant_id, created_by, payload: dict) -> models.Task:
        security = inspect_instructions(payload["instructions"])
        if not security.allowed:
            raise ValueError(security.reason)

        task = models.Task(
            tenant_id=tenant_id,
            created_by=created_by,
            title=payload["title"],
            instructions=payload["instructions"],
            priority=payload.get("priority", 0),
            risk_level=payload.get("risk_level", "low"),
            status="created",
            metadata_=payload.get("metadata", {}),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        self.session.add(task)
        self.session.flush()

        policy = evaluate_task_policy({
            "risk_level": task.risk_level,
            "metadata": task.metadata_,
            "instructions": task.instructions,
        })
        if not policy.allowed:
            task.status = "blocked"
            self.session.add(models.AuditLog(
                tenant_id=tenant_id,
                actor=str(created_by) if created_by else None,
                action="task.blocked",
                entity_type="task",
                entity_id=str(task.id),
                payload={"reason": policy.reason},
            ))
        self.session.flush()

        self.bus.publish("agent.tasks.created", str(task.id), {
            "event_id": str(uuid.uuid4()),
            "event_type": "task.created",
            "task_id": str(task.id),
            "tenant_id": str(tenant_id),
            "created_by": str(created_by) if created_by else None,
        })
        return task

    def approve_task(
        self,
        task: models.Task,
        approved_by_user_id: uuid.UUID,
        approved_by_label: str,
        note: str | None,
    ) -> models.Approval:
        approval = models.Approval(task_id=task.id, approved_by=approved_by_label, note=note)
        task.approved_by = approved_by_user_id
        task.approved_at = datetime.now(timezone.utc)
        task.status = "approved"
        self.session.add(approval)
        self.session.add(task)
        self.session.add(models.AuditLog(
            tenant_id=task.tenant_id,
            actor=approved_by_label,
            action="task.approved",
            entity_type="task",
            entity_id=str(task.id),
            payload={"note": note},
        ))
        self.session.flush()
        self.bus.publish("agent.tasks.approved", str(task.id), {
            "event_id": str(uuid.uuid4()),
            "event_type": "task.approved",
            "task_id": str(task.id),
            "tenant_id": str(task.tenant_id),
            "approved_by": approved_by_label,
            "note": note,
        })
        return approval
