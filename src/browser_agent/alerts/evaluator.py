from __future__ import annotations

import logging
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models
from ..metrics import AUTH_FAILURES
from ..reliability import get_reliability_store

logger = logging.getLogger(__name__)


def evaluate_alerts(session: Session, settings) -> dict:
    rules = []

    # 1. API Health
    rules.append({
        "id": "api_health",
        "name": "API Health",
        "level": "ok",
        "message": "API control plane is healthy and serving requests",
    })

    # 2. Database Readiness
    db_ok = True
    db_msg = "Database connected and queryable"
    try:
        session.execute(select(1))
    except Exception as exc:
        db_ok = False
        db_msg = f"Database connection failed: {exc}"
    rules.append({
        "id": "database_health",
        "name": "Database Readiness",
        "level": "ok" if db_ok else "critical",
        "message": db_msg,
    })

    # 3. DLQ Threshold
    dlq_threshold = getattr(settings, "alert_dlq_threshold", 5)
    pending_dlq_count = 0
    try:
        failed_tasks = session.execute(
            select(models.Task).where(models.Task.status == "failed")
        ).scalars().all()
        for t in failed_tasks:
            meta = t.metadata_ or {}
            dlq = (meta.get("reliability") or {}).get("dlq") or {}
            if dlq.get("status") == "pending":
                pending_dlq_count += 1
    except Exception as exc:
        logger.warning("failed to query dlq tasks for alert: %s", exc)

    dlq_level = "ok"
    if pending_dlq_count >= dlq_threshold:
        dlq_level = "critical"
    elif pending_dlq_count > 0:
        dlq_level = "warning"

    rules.append({
        "id": "dlq_threshold",
        "name": "DLQ Tasks Accumulation",
        "level": dlq_level,
        "current_value": pending_dlq_count,
        "threshold": dlq_threshold,
        "message": f"Pending DLQ tasks: {pending_dlq_count} (threshold: {dlq_threshold})",
    })

    # 4. Auth Failures Spike
    auth_threshold = getattr(settings, "alert_auth_failures_threshold", 10)
    auth_failures_val = 0
    try:
        auth_failures_val = int(AUTH_FAILURES._value.get())
    except Exception:
        pass

    auth_level = "ok"
    if auth_failures_val >= auth_threshold:
        auth_level = "warning"

    rules.append({
        "id": "auth_failure_spike",
        "name": "Auth Failures Spike",
        "level": auth_level,
        "current_value": auth_failures_val,
        "threshold": auth_threshold,
        "message": f"Auth failures count: {auth_failures_val} (threshold: {auth_threshold})",
    })

    # 5. Quarantine Spike
    quarantine_threshold = getattr(settings, "alert_quarantine_threshold", 3)
    quarantine_count = 0
    try:
        for t in failed_tasks:
            meta = t.metadata_ or {}
            dlq = (meta.get("reliability") or {}).get("dlq") or {}
            if dlq.get("status") == "quarantined":
                quarantine_count += 1
    except Exception:
        pass

    quarantine_level = "ok"
    if quarantine_count >= quarantine_threshold:
        quarantine_level = "warning"

    rules.append({
        "id": "quarantine_spike",
        "name": "Quarantined Poison Tasks",
        "level": quarantine_level,
        "current_value": quarantine_count,
        "threshold": quarantine_threshold,
        "message": f"Quarantined tasks: {quarantine_count} (threshold: {quarantine_threshold})",
    })

    # 6. Reliability Store
    store = get_reliability_store(settings)
    rel_status = store.status()
    rel_available = rel_status.get("available", True)
    rules.append({
        "id": "reliability_store",
        "name": "Reliability Store",
        "level": "ok" if rel_available else "critical",
        "message": f"Reliability backend: {rel_status.get('backend', 'unknown')} (available={rel_available})",
    })

    # 7. Artifact Storage
    artifact_backend = getattr(settings, "artifact_backend", "local").lower()
    rules.append({
        "id": "artifact_storage",
        "name": "Artifact Storage Backend",
        "level": "ok",
        "message": f"Artifact storage backend: {artifact_backend}",
    })

    critical_count = sum(1 for r in rules if r["level"] == "critical")
    warning_count = sum(1 for r in rules if r["level"] == "warning")

    if critical_count > 0:
        overall_status = "critical"
    elif warning_count > 0:
        overall_status = "warning"
    else:
        overall_status = "healthy"

    return {
        "status": overall_status,
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
        "webhook_configured": bool(getattr(settings, "alert_webhook_url", "")),
        "active_alerts_count": critical_count + warning_count,
        "rules": rules,
    }
