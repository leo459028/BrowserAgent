from __future__ import annotations

from datetime import datetime, timezone
from sqlalchemy.orm import Session
from . import models

def write_audit(session: Session, tenant_id, actor: str | None, action: str, entity_type: str, entity_id: str, payload: dict):
    session.add(models.AuditLog(
        tenant_id=tenant_id,
        actor=actor,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        payload=payload,
        created_at=datetime.now(timezone.utc),
    ))
