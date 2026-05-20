from __future__ import annotations

import uuid
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from . import models
from .audit import write_audit
from .metrics import TASK_CREATED
from .policy import evaluate_task_policy
from .security import inspect_instructions
from .services.tasks import APPROVABLE_STATUSES, set_task_status, set_task_status_with_audit

class Orchestrator:
    def __init__(self, session: Session, bus):
        self.session = session
        self.bus = bus

    def create_task(self, tenant_id, created_by, payload: dict, correlation_id: str | None = None) -> models.Task:
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
            correlation_id=correlation_id,
            metadata_=payload.get("metadata", {}),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        self.session.add(task)
        self.session.flush()
        TASK_CREATED.inc()
        write_audit(
            self.session,
            tenant_id,
            str(created_by) if created_by else None,
            "task.created",
            "task",
            str(task.id),
            {"correlation_id": correlation_id},
        )

        policy = evaluate_task_policy({
            "risk_level": task.risk_level,
            "metadata": task.metadata_,
            "instructions": task.instructions,
        })
        task.metadata_ = {
            **(task.metadata_ or {}),
            "policy": {
                "decision": "allowed" if policy.allowed else ("requires_approval" if policy.requires_approval else "denied"),
                "reason": policy.reason,
                "requires_approval": policy.requires_approval,
            },
        }
        self.session.add(task)
        if not policy.allowed and not policy.requires_approval:
            set_task_status_with_audit(
                self.session,
                task,
                "blocked",
                action="task.blocked",
                actor=str(created_by) if created_by else None,
                payload={
                    "reason": policy.reason,
                    "policy": task.metadata_["policy"],
                    "correlation_id": correlation_id,
                },
            )
        else:
            set_task_status_with_audit(
                self.session,
                task,
                "pending_approval",
                action="task.pending_approval",
                actor=str(created_by) if created_by else None,
                payload={
                    "reason": policy.reason,
                    "policy": task.metadata_["policy"],
                    "correlation_id": correlation_id,
                },
            )
        self.session.flush()

        self.bus.publish("agent.tasks.created", str(task.id), {
            "event_id": str(uuid.uuid4()),
            "event_type": "task.created",
            "task_id": str(task.id),
            "tenant_id": str(tenant_id),
            "created_by": str(created_by) if created_by else None,
            "correlation_id": correlation_id,
        })
        return task

    def approve_task(
        self,
        task: models.Task,
        approved_by_user_id: uuid.UUID,
        approved_by_label: str,
        note: str | None,
    ) -> models.Approval:
        if task.status not in APPROVABLE_STATUSES:
            raise ValueError(f"cannot approve task in status {task.status}")

        approval = models.Approval(task_id=task.id, approved_by=approved_by_label, note=note)
        task.approved_by = approved_by_user_id
        task.approved_at = datetime.now(timezone.utc)
        self.session.add(approval)
        self.session.add(task)
        write_audit(
            self.session,
            task.tenant_id,
            approved_by_label,
            "task.approved",
            "task",
            str(task.id),
            {"note": note, "correlation_id": getattr(task, "correlation_id", None)},
        )
        set_task_status(
            self.session,
            task,
            "queued",
            {"queued_at": datetime.now(timezone.utc).isoformat()},
        )
        write_audit(
            self.session,
            task.tenant_id,
            approved_by_label,
            "task.queued",
            "task",
            str(task.id),
            {"note": note, "status": task.status, "correlation_id": getattr(task, "correlation_id", None)},
        )
        self.session.flush()
        self.bus.publish("agent.tasks.queued", str(task.id), {
            "event_id": str(uuid.uuid4()),
            "event_type": "task.queued",
            "task_id": str(task.id),
            "tenant_id": str(task.tenant_id),
            "approved_by": approved_by_label,
            "note": note,
            "correlation_id": getattr(task, "correlation_id", None),
        })
        return approval
