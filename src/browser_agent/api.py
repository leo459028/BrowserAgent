from __future__ import annotations

import hashlib
import json
import logging
import time
import uuid
from io import BytesIO
from datetime import datetime, timezone
from pathlib import Path
from fastapi import APIRouter, Body, Depends, FastAPI, Header, HTTPException, WebSocket, WebSocketDisconnect
from fastapi import Request
from fastapi.responses import FileResponse, PlainTextResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from .config import get_settings
from .db import get_session_factory
from . import models
from .auth import (
    ActorContext,
    create_access_token,
    local_dev_actor_for_role,
    get_current_actor,
    require_roles,
    generate_oidc_pkce,
    build_oidc_auth_url,
    exchange_oidc_code_for_token,
)
from .crypto.kms import get_kms_provider, decrypt_session_vault_payload
from .services.live_telemetry import get_telemetry_broadcaster
from .services.dlp import get_dlp_service
from .services.federation import get_federation_manager

from .schemas import (
    AlertTestDispatchRequest,
    DlqBulkReplayRequest,
    DlqQuarantineRequest,
    LocalTokenRequest,
    TaskCreateRequest,
    TaskApproveRequest,
    SkillCreateRequest,
    ScheduledTaskCreateRequest,
    ScheduledTaskUpdateRequest,
    ScheduledTaskOut,
    TaskInteractRequest,
    TaskPauseRequest,
    MatrixTaskCreateRequest,
    FederationHeartbeatRequest,
)
from .services.scheduler import compute_next_run, evaluate_scheduled_tasks, trigger_scheduled_task
from .tracing.exporter import get_otlp_exporter
from .orchestrator import Orchestrator
from .skillhub import SkillHub
from .kafka import get_bus
from .logging import configure_logging
from .audit import write_audit
from .reliability import get_reliability_store
from .services.tasks import set_task_status
from .services.artifacts import build_artifact_store_from_settings
from .metrics import HTTP_DURATION, HTTP_REQUESTS, PRODUCTION_READINESS
from .request_context import (
    LOG_SCHEMA_FIELDS,
    build_request_context,
    get_request_context,
    request_context_payload,
    reset_request_context,
    set_request_context,
)

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))
logger = logging.getLogger(__name__)

def get_session():
    session = get_session_factory()()
    try:
        yield session
    finally:
        session.close()

DEFAULT_TASK_PAYLOAD = {
    "title": "Capture example.com",
    "instructions": "Open the allowlisted site and capture a screenshot.",
    "priority": 1,
    "risk_level": "low",
    "metadata": {
        "domains": ["example.com"],
        "start_url": "https://example.com",
        "expected_domain": "example.com",
        "record_video": True,
    },
}

@router.get("/healthz")
def healthz():
    return {"status": "ok"}

@router.get("/readyz")
def readyz(session: Session = Depends(get_session)):
    session.execute(select(1))
    return {"status": "ready"}

@router.get("/metrics")
def metrics(actor: ActorContext = Depends(require_roles("operator", "admin"))):
    return PlainTextResponse(generate_latest(), media_type=CONTENT_TYPE_LATEST)

@router.get("/operations")
def operations(request: Request):
    return templates.TemplateResponse(
        request,
        "operations.html",
        {
            "default_payload": DEFAULT_TASK_PAYLOAD,
            "available_roles": ["creator", "approver", "operator", "admin"],
        },
    )

@router.get("/", include_in_schema=False)
def root_redirect():
    return RedirectResponse(url="/operations", status_code=307)

@router.get("/operation", include_in_schema=False)
def operation_redirect():
    return RedirectResponse(url="/operations", status_code=307)

@router.get("/v1/auth/me")
def auth_me(actor: ActorContext = Depends(get_current_actor)):
    return serialize_actor(actor)

@router.post("/v1/auth/local-token")
def create_local_token(req: LocalTokenRequest):
    settings = get_settings()
    if not settings.auth_local_tokens_enabled:
        raise HTTPException(status_code=404, detail="local dev tokens disabled")
    try:
        actor = local_dev_actor_for_role(req.role)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    token = create_access_token(actor, settings=settings)
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": settings.auth_token_ttl_seconds,
        "actor": serialize_actor(actor),
    }


@router.get("/v1/ops/readiness")
def operations_readiness(
    actor: ActorContext = Depends(require_roles("operator", "admin")),
    session: Session = Depends(get_session),
):
    settings = get_settings()
    checks = {}
    warnings = []
    db_ready = True
    try:
        session.execute(select(1))
    except Exception as exc:
        db_ready = False
        checks["database_error"] = str(exc)
    store = get_reliability_store(settings)
    reliability_status = store.status()
    artifact_backend = settings.artifact_backend.lower()
    if settings.auth_mode.lower() == "jwks" and not getattr(settings, "auth_jwks_url", "") and not getattr(settings, "auth_oidc_issuer_url", ""):
        warnings.append("AUTH_JWKS_URL or AUTH_OIDC_ISSUER_URL is not configured")
    checks.update({
        "database": {"ready": db_ready},
        "reliability": reliability_status,
        "kafka": {
            "configured": bool(settings.kafka_bootstrap_servers),
            "bootstrap_servers": settings.kafka_bootstrap_servers,
        },
        "artifact_backend": {
            "backend": artifact_backend,
            "bucket": settings.minio_bucket if artifact_backend == "s3" else None,
            "base_path": settings.artifact_base_path if artifact_backend == "local" else None,
        },
        "kubernetes": {
            "detected": bool(__import__("os").environ.get("KUBERNETES_SERVICE_HOST") or __import__("os").path.exists("/var/run/secrets/kubernetes.io/serviceaccount")),
            "platform": "kubernetes" if bool(__import__("os").environ.get("KUBERNETES_SERVICE_HOST") or __import__("os").path.exists("/var/run/secrets/kubernetes.io/serviceaccount")) else "docker_or_standalone",
        },
    })
    production = build_production_readiness(settings, reliability_status)
    observability = build_observability_readiness(settings)
    status = "ready" if db_ready and reliability_status.get("available", True) and not warnings else "degraded"
    if not db_ready or reliability_status.get("available") is False:
        status = "not_ready"
    if production["enabled"] and production["status"] == "not_ready":
        status = "not_ready"
    elif production["enabled"] and production["status"] == "degraded" and status == "ready":
        status = "degraded"
    PRODUCTION_READINESS.set({"ready": 1, "degraded": 0, "not_ready": -1}.get(status, -1))
    return {
        "status": status,
        "app": {"name": settings.app_name, "version": settings.app_version, "env": settings.app_env},
        "auth": {
            "mode": settings.auth_mode,
            "local_tokens_enabled": settings.auth_local_tokens_enabled,
            "issuer": settings.auth_jwt_issuer,
            "audience": settings.auth_jwt_audience,
        },
        "worker": {
            "service_id": settings.worker_service_id,
            "task_lock_ttl_seconds": settings.task_lock_ttl_seconds,
        },
        "dlq": {"topic": settings.dlq_topic},
        "checks": checks,
        "production": production,
        "observability": observability,
        "warnings": warnings,
    }


def build_production_readiness(settings, reliability_status: dict) -> dict:
    env = getattr(settings, "app_env", "local").lower()
    is_production = env in {"prod", "production"}
    checks = {
        "app_env_production": _readiness_check(
            "pass" if is_production else "warn",
            f"APP_ENV={getattr(settings, 'app_env', 'local')}",
        ),
        "local_tokens_disabled": _readiness_check(
            "pass" if not getattr(settings, "auth_local_tokens_enabled", True) else ("fail" if is_production else "warn"),
            "local dev token endpoint is disabled" if not getattr(settings, "auth_local_tokens_enabled", True) else "local dev token endpoint is enabled",
        ),
        "secret_key_rotated": _readiness_check(
            "pass" if getattr(settings, "app_secret_key", "change-me") not in {"", "change-me"} else ("fail" if is_production else "warn"),
            "APP_SECRET_KEY is not the default value" if getattr(settings, "app_secret_key", "change-me") not in {"", "change-me"} else "APP_SECRET_KEY uses the default value",
        ),
        "auth_mode_jwks": _readiness_check(
            "pass" if getattr(settings, "auth_mode", "local").lower() == "jwks" else ("fail" if is_production else "warn"),
            f"AUTH_MODE={getattr(settings, 'auth_mode', 'local')}",
        ),
        "jwks_or_oidc_configured": _readiness_check(
            "pass" if getattr(settings, "auth_jwks_url", "") or getattr(settings, "auth_oidc_issuer_url", "") else ("fail" if is_production else "warn"),
            "JWKS URL or OIDC issuer URL is configured" if getattr(settings, "auth_jwks_url", "") or getattr(settings, "auth_oidc_issuer_url", "") else "JWKS URL and OIDC issuer URL are missing",
        ),
        "redis_reliability_store": _readiness_check(
            "pass" if getattr(settings, "reliability_store", "memory").lower() == "redis" and reliability_status.get("backend") == "redis" else ("fail" if is_production else "warn"),
            f"reliability_store={getattr(settings, 'reliability_store', 'memory')}, backend={reliability_status.get('backend')}",
        ),
        "kafka_configured": _readiness_check(
            "pass" if bool(getattr(settings, "kafka_bootstrap_servers", "")) else ("fail" if is_production else "warn"),
            "Kafka bootstrap servers are configured" if getattr(settings, "kafka_bootstrap_servers", "") else "Kafka bootstrap servers are missing",
        ),
        "s3_artifact_backend": _readiness_check(
            "pass" if getattr(settings, "artifact_backend", "local").lower() == "s3" else ("fail" if is_production else "warn"),
            f"ARTIFACT_BACKEND={getattr(settings, 'artifact_backend', 'local')}",
        ),
    }
    failed = [name for name, check in checks.items() if check["status"] == "fail"]
    warned = [name for name, check in checks.items() if check["status"] == "warn"]
    status = "not_ready" if failed else ("degraded" if warned else "ready")
    return {
        "status": status,
        "enabled": is_production,
        "checks": checks,
        "failures": failed,
        "warnings": warned,
    }


def build_observability_readiness(settings) -> dict:
    exporter = get_otlp_exporter(settings)
    return {
        "otel_ready": True,
        "otel_enabled": bool(getattr(settings, "otel_enabled", False)),
        "otel_service_name": getattr(settings, "otel_service_name", None) or getattr(settings, "app_name", "browser-agent"),
        "otel_exporter_otlp_endpoint_configured": bool(getattr(settings, "otel_exporter_otlp_endpoint", "")),
        "otel_resource_attributes": getattr(settings, "otel_resource_attributes", ""),
        "otel_propagators": getattr(settings, "otel_propagators", "tracecontext,baggage"),
        "otlp_exporter": exporter.status(),
        "log_schema_fields": LOG_SCHEMA_FIELDS,
    }


def _readiness_check(status: str, message: str) -> dict:
    return {"status": status, "message": message}


@router.get("/v1/ops/alerts")
def get_ops_alerts(
    actor: ActorContext = Depends(require_roles("operator", "admin")),
    session: Session = Depends(get_session),
):
    from .alerts import evaluate_alerts
    settings = get_settings()
    return evaluate_alerts(session, settings)


@router.post("/v1/ops/alerts/test-dispatch")
def test_dispatch_alert(
    req: AlertTestDispatchRequest,
    actor: ActorContext = Depends(require_roles("operator", "admin")),
    session: Session = Depends(get_session),
):
    from .alerts import dispatch_alert_webhook
    settings = get_settings()
    webhook_dispatched = dispatch_alert_webhook(
        rule_id=req.rule_id,
        note=req.note,
        settings=settings,
        actor_email=actor.email,
        level=req.level,
    )
    write_audit(
        session,
        actor.tenant_id,
        actor.email,
        "alert.dispatched",
        "alert",
        req.rule_id,
        {
            "rule_id": req.rule_id,
            "note": req.note,
            "level": req.level,
            "webhook_dispatched": webhook_dispatched,
            "webhook_configured": bool(settings.alert_webhook_url),
            "correlation_id": getattr(get_request_context(), "correlation_id", None),
        },
    )
    session.commit()
    return {
        "dispatched": True,
        "rule_id": req.rule_id,
        "level": req.level,
        "note": req.note,
        "webhook_dispatched": webhook_dispatched,
        "webhook_configured": bool(settings.alert_webhook_url),
        "dispatched_by": actor.email,
    }


@router.get("/v1/ops/traces/{trace_id}")
def get_trace_spans(
    trace_id: str,
    actor: ActorContext = Depends(require_roles("operator", "admin")),
    session: Session = Depends(get_session),
):
    from .tracing import get_trace_buffer
    buffer = get_trace_buffer()
    spans = list(buffer.get_trace(trace_id))
    existing_span_ids = {s.get("span_id") for s in spans}

    tasks = session.execute(select(models.Task)).scalars().all()
    for t in tasks:
        tc = (getattr(t, "metadata_", {}) or {}).get("trace_context") or {}
        if tc.get("trace_id") == trace_id or getattr(t, "correlation_id", "") == trace_id:
            for step in getattr(t, "steps", []):
                out = step.output_data or {}
                sid = out.get("span_id")
                if sid and sid not in existing_span_ids:
                    spans.append({
                        "name": f"browser.step:{step.action_type}",
                        "trace_id": trace_id,
                        "span_id": sid,
                        "parent_span_id": tc.get("span_id"),
                        "service": "browser-agent-worker",
                        "start_time": step.created_at.isoformat() if step.created_at else "",
                        "end_time": step.completed_at.isoformat() if step.completed_at else None,
                        "duration_ms": out.get("duration_ms", 100),
                        "status": "error" if step.status == "failed" else "ok",
                        "attributes": {
                            "task_id": str(t.id),
                            "step_no": step.step_no,
                            "action_type": step.action_type,
                            "target": step.target,
                        },
                    })
                    existing_span_ids.add(sid)
            break

    return {
        "trace_id": trace_id,
        "spans_count": len(spans),
        "spans": spans,
    }



def _correlation_id(request: Request) -> str:
    context = get_request_context()
    if context:
        return context.correlation_id
    return request.headers.get("X-Correlation-ID") or str(uuid.uuid4())


def actor_request_payload(actor: ActorContext) -> dict:
    return {**actor.audit_payload(), **request_context_payload()}

@router.post("/v1/tasks")
def create_task(
    req: TaskCreateRequest,
    request: Request,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    actor: ActorContext = Depends(require_roles("creator", "admin")),
    session: Session = Depends(get_session),
):
    settings = get_settings()
    idempotency_key = _normalize_idempotency_key(idempotency_key)
    request_hash = _request_hash(req.model_dump())
    store = get_reliability_store(settings)
    rate = store.check_rate_limit(
        f"task-create:{actor.tenant_id}:{actor.user_id}",
        settings.task_create_rate_limit_per_minute,
        60,
    )
    if not rate.allowed:
        raise HTTPException(
            status_code=429,
            detail="task create rate limit exceeded",
            headers={"Retry-After": str(rate.reset_seconds)},
        )

    if idempotency_key:
        existing = find_task_by_idempotency_key(session, actor.tenant_id, idempotency_key)
        if existing:
            existing_hash = ((existing.metadata_ or {}).get("reliability") or {}).get("request_hash")
            if existing_hash != request_hash:
                raise HTTPException(
                    status_code=409,
                    detail="idempotency key already used with a different payload",
                )
            return {
                "task_id": str(existing.id),
                "status": existing.status,
                "correlation_id": getattr(existing, "correlation_id", None),
                "created_at": existing.created_at.isoformat(),
                "idempotency": {"key": idempotency_key, "replayed": True},
            }

    bus = get_bus(settings.kafka_bootstrap_servers)
    orch = Orchestrator(session, bus)
    correlation_id = _correlation_id(request)
    try:
        task = orch.create_task(
            actor.tenant_id,
            actor.user_id,
            req.model_dump(),
            correlation_id=correlation_id,
            actor_label=actor.email,
            actor_payload=actor_request_payload(actor),
            idempotency_key=idempotency_key,
            request_hash=request_hash if idempotency_key else None,
        )
        session.commit()
    except ValueError as exc:
        session.rollback()
        raise HTTPException(status_code=400, detail=str(exc))
    return {
        "task_id": str(task.id),
        "status": task.status,
        "browser_engine": getattr(task, "browser_engine", "chromium"),
        "correlation_id": getattr(task, "correlation_id", None),
        "created_at": task.created_at.isoformat(),
        "idempotency": {"key": idempotency_key, "replayed": False} if idempotency_key else None,
    }

@router.get("/v1/reliability")
def reliability_status(actor: ActorContext = Depends(require_roles("operator", "admin"))):
    settings = get_settings()
    store = get_reliability_store(settings)
    return {
        "store": store.status(),
        "worker_service_id": settings.worker_service_id,
        "task_create_rate_limit_per_minute": settings.task_create_rate_limit_per_minute,
        "idempotency_ttl_seconds": settings.idempotency_ttl_seconds,
        "task_lock_ttl_seconds": settings.task_lock_ttl_seconds,
        "max_task_retries": settings.max_task_retries,
        "dlq_topic": settings.dlq_topic,
    }

@router.get("/v1/dlq/tasks")
def list_dlq_tasks(
    limit: int = 20,
    actor: ActorContext = Depends(require_roles("operator", "admin")),
    session: Session = Depends(get_session),
):
    limit = max(1, min(limit, 100))
    tasks = session.execute(
        select(models.Task)
        .where(models.Task.tenant_id == actor.tenant_id, models.Task.status == "failed")
        .order_by(models.Task.updated_at.desc())
        .limit(limit)
    ).scalars().all()
    return [
        serialize_dlq_task(task)
        for task in tasks
        if (((task.metadata_ or {}).get("reliability") or {}).get("dlq"))
    ]

@router.post("/v1/dlq/tasks/{task_id}/replay")
def replay_dlq_task(
    task_id: str,
    actor: ActorContext = Depends(require_roles("operator", "admin")),
    session: Session = Depends(get_session),
):
    settings = get_settings()
    bus = get_bus(settings.kafka_bootstrap_servers)
    task = session.get(models.Task, uuid.UUID(task_id))
    if not task or task.tenant_id != actor.tenant_id:
        raise HTTPException(status_code=404, detail="task not found")
    if not is_replayable_dlq_task(task):
        raise HTTPException(status_code=409, detail="task is not replayable from DLQ")
    replay = apply_dlq_replay(session, task, actor, note="DLQ replay")
    session.flush()
    publish_replay_event(bus, task, actor, "DLQ replay")
    session.commit()
    return {
        "task_id": str(task.id),
        "status": task.status,
        "replay": replay,
    }


@router.post("/v1/dlq/tasks/bulk-replay")
def bulk_replay_dlq_tasks(
    req: DlqBulkReplayRequest,
    actor: ActorContext = Depends(require_roles("operator", "admin")),
    session: Session = Depends(get_session),
):
    settings = get_settings()
    bus = get_bus(settings.kafka_bootstrap_servers)
    replayed = []
    skipped = []
    note = req.note or "DLQ bulk replay"
    for task_id in req.task_ids:
        task = session.get(models.Task, task_id)
        if not task or task.tenant_id != actor.tenant_id:
            skipped.append({"task_id": str(task_id), "reason": "not_found"})
            continue
        dlq = (((task.metadata_ or {}).get("reliability") or {}).get("dlq") or {})
        if dlq.get("status") == "quarantined":
            skipped.append({"task_id": str(task.id), "reason": "quarantined"})
            continue
        if not is_replayable_dlq_task(task):
            skipped.append({"task_id": str(task.id), "reason": "not_replayable"})
            continue
        apply_dlq_replay(session, task, actor, note=note)
        publish_replay_event(bus, task, actor, note)
        replayed.append({"task_id": str(task.id), "status": task.status})
    session.commit()
    return {"replayed": replayed, "skipped": skipped}


@router.post("/v1/dlq/tasks/{task_id}/quarantine")
def quarantine_dlq_task(
    task_id: str,
    req: DlqQuarantineRequest,
    actor: ActorContext = Depends(require_roles("operator", "admin")),
    session: Session = Depends(get_session),
):
    task = session.get(models.Task, uuid.UUID(task_id))
    if not task or task.tenant_id != actor.tenant_id:
        raise HTTPException(status_code=404, detail="task not found")
    metadata = task.metadata_ or {}
    reliability = dict(metadata.get("reliability") or {})
    dlq = dict(reliability.get("dlq") or {})
    if task.status != "failed" or not dlq:
        raise HTTPException(status_code=409, detail="task is not quarantineable from DLQ")
    dlq["status"] = "quarantined"
    dlq["quarantine"] = {
        "reason": req.reason,
        "quarantined_at": datetime.now(timezone.utc).isoformat(),
        "quarantined_by": actor.email,
    }
    reliability["dlq"] = dlq
    task.metadata_ = {**metadata, "reliability": reliability}
    write_audit(
        session,
        task.tenant_id,
        actor.email,
        "task.dlq_quarantined",
        "task",
        str(task.id),
        {
            "correlation_id": task.correlation_id,
            "dlq": dlq,
            **actor_request_payload(actor),
        },
    )
    session.commit()
    return {"task_id": str(task.id), "status": task.status, "dlq": dlq}

@router.get("/v1/tasks")
def list_tasks(
    limit: int = 20,
    actor: ActorContext = Depends(require_roles("creator", "approver", "operator", "admin")),
    session: Session = Depends(get_session),
):
    limit = max(1, min(limit, 100))
    tasks = session.execute(
        select(models.Task)
        .where(models.Task.tenant_id == actor.tenant_id)
        .order_by(models.Task.created_at.desc())
        .limit(limit)
    ).scalars().all()
    return [serialize_task_summary(task) for task in tasks]

@router.get("/v1/tasks/{task_id}")
def get_task(
    task_id: str,
    actor: ActorContext = Depends(require_roles("creator", "approver", "operator", "admin")),
    session: Session = Depends(get_session),
):
    task = session.get(models.Task, uuid.UUID(task_id))
    if not task or task.tenant_id != actor.tenant_id:
        raise HTTPException(status_code=404, detail="task not found")
    return serialize_task(task)

@router.get("/v1/tasks/{task_id}/audit")
def get_task_audit(
    task_id: str,
    actor: ActorContext = Depends(require_roles("approver", "operator", "admin")),
    session: Session = Depends(get_session),
):
    task_uuid = uuid.UUID(task_id)
    entries = session.execute(
        select(models.AuditLog)
        .where(
            models.AuditLog.entity_type == "task",
            models.AuditLog.entity_id == str(task_uuid),
            models.AuditLog.tenant_id == actor.tenant_id,
        )
        .order_by(models.AuditLog.created_at.asc())
    ).scalars().all()
    return [serialize_audit_log(entry) for entry in entries]


@router.get("/v1/tasks/{task_id}/replay")
def get_task_replay(
    task_id: str,
    actor: ActorContext = Depends(require_roles("approver", "operator", "admin")),
    session: Session = Depends(get_session),
):
    task_uuid = uuid.UUID(task_id)
    task = session.get(models.Task, task_uuid)
    if not task or task.tenant_id != actor.tenant_id:
        raise HTTPException(status_code=404, detail="task not found")
    audits = session.execute(
        select(models.AuditLog)
        .where(
            models.AuditLog.entity_type == "task",
            models.AuditLog.entity_id == str(task_uuid),
            models.AuditLog.tenant_id == actor.tenant_id,
        )
        .order_by(models.AuditLog.created_at.asc())
    ).scalars().all()
    evaluations = session.execute(
        select(models.Evaluation)
        .where(models.Evaluation.task_id == task_uuid)
        .order_by(models.Evaluation.created_at.asc())
    ).scalars().all()
    timeline = []
    for entry in audits:
        timeline.append({
            "kind": "audit",
            "created_at": entry.created_at.isoformat(),
            "action": entry.action,
            "actor": entry.actor,
            "payload": entry.payload,
        })
    for step in sorted(getattr(task, "steps", []), key=lambda item: item.step_no):
        timeline.append({
            "kind": "step",
            "created_at": step.created_at.isoformat(),
            "step_no": step.step_no,
            "action_type": step.action_type,
            "target": step.target,
            "status": step.status,
            "input_data": step.input_data,
            "output_data": step.output_data,
            "error_message": step.error_message,
        })
    for artifact in sorted(getattr(task, "artifacts", []), key=lambda item: item.created_at):
        payload = serialize_artifact(artifact)
        timeline.append({
            "kind": "artifact",
            "created_at": artifact.created_at.isoformat(),
            "artifact": payload,
        })
    for evaluation in evaluations:
        timeline.append({
            "kind": "evaluation",
            "created_at": evaluation.created_at.isoformat(),
            "evaluator_ver": evaluation.evaluator_ver,
            "score": float(evaluation.score),
            "verdict": evaluation.verdict,
            "checks": evaluation.checks,
        })
    steps_visual = []
    for step in sorted(getattr(task, "steps", []), key=lambda item: item.step_no):
        out = step.output_data or {}
        art_id = out.get("screenshot_artifact_id")
        steps_visual.append({
            "step_no": step.step_no,
            "action_type": step.action_type,
            "target": step.target,
            "status": step.status,
            "duration_ms": out.get("duration_ms", 100),
            "span_id": out.get("span_id"),
            "screenshot_artifact_id": art_id,
            "screenshot_url": f"/v1/artifacts/{art_id}/content" if art_id else None,
            "dom_summary": out.get("dom_summary"),
            "error_message": step.error_message,
        })
    eval_summary = None
    if evaluations:
        last_eval = evaluations[-1]
        eval_summary = {
            "verdict": last_eval.verdict,
            "score": float(last_eval.score),
            "checks": last_eval.checks,
        }
    trace_context = (getattr(task, "metadata_", {}) or {}).get("trace_context") or {}
    trace_id = trace_context.get("trace_id") or getattr(task, "correlation_id", None)

    video_art_id = None
    for artifact in getattr(task, "artifacts", []):
        if artifact.artifact_type == "video":
            video_art_id = str(artifact.id)
            break

    return {
        "task_id": str(task.id),
        "status": task.status,
        "trace_id": trace_id,
        "video_artifact_id": video_art_id,
        "video_url": f"/v1/artifacts/{video_art_id}/content" if video_art_id else None,
        "steps_visual": steps_visual,
        "evaluation_summary": eval_summary,
        "timeline": timeline,
    }

@router.get("/v1/artifacts/{artifact_id}/content")
def get_artifact_content(
    artifact_id: str,
    actor: ActorContext = Depends(require_roles("creator", "approver", "operator", "admin")),
    session: Session = Depends(get_session),
):
    artifact = session.get(models.TaskArtifact, uuid.UUID(artifact_id))
    if not artifact:
        raise HTTPException(status_code=404, detail="artifact not found")
    ensure_artifact_access(artifact, actor.tenant_id)
    settings = get_settings()
    metadata = artifact.metadata_ or {}
    media_type = metadata.get("content_type") or metadata.get("media_type") or "application/octet-stream"
    backend = metadata.get("backend") or getattr(settings, "artifact_backend", "local")
    if backend == "s3" or artifact.uri.startswith("s3://"):
        store = build_artifact_store_from_settings(settings)
        data = store.read_bytes(artifact.uri)
        return Response(
            content=data,
            media_type=media_type,
            headers={"Content-Disposition": f'inline; filename="{Path(artifact.uri).name}"'},
        )
    path = resolve_artifact_file_path(settings.artifact_base_path, artifact.uri)
    response = FileResponse(path, media_type=media_type, filename=path.name)
    response.headers["Content-Disposition"] = f'inline; filename="{path.name}"'
    return response

def serialize_task(task) -> dict:
    metadata = getattr(task, "metadata_", None)
    if metadata is None:
        metadata = getattr(task, "metadata", {})
    artifacts = [
        serialize_artifact(a)
        for a in sorted(getattr(task, "artifacts", []), key=lambda x: x.created_at)
    ]
    return {
        "id": str(task.id),
        "tenant_id": str(task.tenant_id),
        "title": task.title,
        "instructions": task.instructions,
        "status": task.status,
        "correlation_id": getattr(task, "correlation_id", None),
        "priority": task.priority,
        "risk_level": task.risk_level,
        "metadata": metadata,
        "created_at": task.created_at.isoformat(),
        "updated_at": task.updated_at.isoformat() if task.updated_at else None,
        "steps": [
            {
                "id": str(s.id),
                "step_no": s.step_no,
                "action_type": s.action_type,
                "target": s.target,
                "instruction": s.instruction,
                "status": s.status,
                "input_data": s.input_data,
                "output_data": s.output_data,
                "error_message": s.error_message,
            }
            for s in sorted(task.steps, key=lambda x: x.step_no)
        ],
        "artifacts": artifacts,
    }

def serialize_artifact(artifact) -> dict:
    metadata = getattr(artifact, "metadata_", None)
    if metadata is None:
        metadata = getattr(artifact, "metadata", {}) or {}
    content_type = metadata.get("content_type") or metadata.get("media_type")
    redaction = metadata.get("redaction") or {}
    return {
        "id": str(artifact.id),
        "artifact_type": artifact.artifact_type,
        "uri": artifact.uri,
        "sha256": artifact.sha256,
        "content_type": content_type,
        "size_bytes": metadata.get("size_bytes"),
        "backend": metadata.get("backend", "local"),
        "retention": metadata.get("retention"),
        "redaction": redaction,
        "redaction_status": redaction.get("status"),
        "metadata": metadata,
        "created_at": artifact.created_at.isoformat(),
        "download_url": f"/v1/artifacts/{artifact.id}/content",
    }

def serialize_task_summary(task) -> dict:
    metadata = getattr(task, "metadata_", None)
    if metadata is None:
        metadata = getattr(task, "metadata", {})
    return {
        "id": str(task.id),
        "title": task.title,
        "status": task.status,
        "correlation_id": getattr(task, "correlation_id", None),
        "priority": task.priority,
        "risk_level": task.risk_level,
        "policy": (metadata or {}).get("policy"),
        "created_at": task.created_at.isoformat(),
        "updated_at": task.updated_at.isoformat() if task.updated_at else None,
    }

def serialize_dlq_task(task) -> dict:
    metadata = task.metadata_ or {}
    reliability = metadata.get("reliability") or {}
    return {
        "task_id": str(task.id),
        "title": task.title,
        "status": task.status,
        "correlation_id": task.correlation_id,
        "dlq": reliability.get("dlq"),
        "replay": reliability.get("replay"),
        "updated_at": task.updated_at.isoformat() if task.updated_at else None,
    }


def is_replayable_dlq_task(task) -> bool:
    reliability = ((task.metadata_ or {}).get("reliability") or {})
    dlq = reliability.get("dlq") or {}
    return task.status == "failed" and bool(dlq) and dlq.get("status") != "quarantined"


def apply_dlq_replay(session: Session, task, actor: ActorContext, note: str) -> dict:
    metadata = task.metadata_ or {}
    reliability = dict(metadata.get("reliability") or {})
    dlq = dict(reliability.get("dlq") or {})
    replay = dict(reliability.get("replay") or {})
    replay["count"] = int(replay.get("count") or 0) + 1
    replay["last_replayed_at"] = datetime.now(timezone.utc).isoformat()
    replay["last_replayed_by"] = actor.email
    replay["note"] = note
    dlq["status"] = "replayed"
    reliability["dlq"] = dlq
    reliability["replay"] = replay
    task.metadata_ = {**metadata, "reliability": reliability}
    task.completed_at = None
    task.started_at = None
    set_task_status(session, task, "queued")
    write_audit(
        session,
        task.tenant_id,
        actor.email,
        "task.dlq_replayed",
        "task",
        str(task.id),
        {
            "correlation_id": task.correlation_id,
            "replay": replay,
            **actor_request_payload(actor),
        },
    )
    return replay


def publish_replay_event(bus, task, actor: ActorContext, note: str) -> None:
    bus.publish("agent.tasks.queued", str(task.id), {
        "event_id": str(uuid.uuid4()),
        "event_type": "task.queued",
        "task_id": str(task.id),
        "tenant_id": str(task.tenant_id),
        "approved_by": actor.email,
        "note": note,
        "correlation_id": task.correlation_id,
        **actor_request_payload(actor),
    })

def serialize_audit_log(entry) -> dict:
    return {
        "id": str(entry.id),
        "actor": entry.actor,
        "action": entry.action,
        "payload": entry.payload,
        "created_at": entry.created_at.isoformat(),
    }

def serialize_actor(actor: ActorContext) -> dict:
    return {
        "user_id": str(actor.user_id),
        "tenant_id": str(actor.tenant_id),
        "email": actor.email,
        "roles": list(actor.roles),
        "permissions": sorted(actor.permissions),
    }

def find_task_by_idempotency_key(session: Session, tenant_id: uuid.UUID, key: str):
    return session.execute(
        select(models.Task).where(
            models.Task.tenant_id == tenant_id,
            models.Task.idempotency_key == key,
        )
    ).scalars().first()

def _normalize_idempotency_key(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    if not value:
        return None
    return value[:256]

def _request_hash(payload: dict) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()

def resolve_artifact_file_path(base_path: str, uri: str) -> Path:
    base = Path(base_path).resolve()
    candidate = Path(uri)
    if not candidate.is_absolute():
        candidate = base / candidate
    resolved = candidate.resolve()
    try:
        resolved.relative_to(base)
    except ValueError:
        raise HTTPException(status_code=403, detail="artifact path is outside artifact storage")
    if not resolved.exists():
        raise HTTPException(status_code=404, detail="artifact file not found")
    if not resolved.is_file():
        raise HTTPException(status_code=404, detail="artifact file not found")
    return resolved

def ensure_artifact_access(artifact, tenant_id: uuid.UUID) -> None:
    task = getattr(artifact, "task", None)
    artifact_tenant_id = getattr(task, "tenant_id", None)
    if artifact_tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="artifact tenant mismatch")

@router.post("/v1/tasks/{task_id}/approve")
def approve_task(
    task_id: str,
    req: TaskApproveRequest | None = Body(default=None),
    actor: ActorContext = Depends(require_roles("approver", "admin")),
    session: Session = Depends(get_session),
):
    settings = get_settings()
    bus = get_bus(settings.kafka_bootstrap_servers)
    orch = Orchestrator(session, bus)
    task = session.get(models.Task, uuid.UUID(task_id))
    if not task or task.tenant_id != actor.tenant_id:
        raise HTTPException(status_code=404, detail="task not found")
    try:
        approval = orch.approve_task(
            task,
            actor.user_id,
            actor.email,
            req.note if req else None,
            actor_payload=actor_request_payload(actor),
        )
        session.commit()
    except ValueError as exc:
        session.rollback()
        raise HTTPException(status_code=409, detail=str(exc))
    return {
        "task_id": str(task.id),
        "approval_id": str(approval.id),
        "status": task.status,
        "correlation_id": task.correlation_id,
    }

@router.post("/v1/skills")
def create_skill(
    req: SkillCreateRequest,
    actor: ActorContext = Depends(require_roles("admin")),
    session: Session = Depends(get_session),
):
    skillhub = SkillHub(session)
    skill = skillhub.register(actor.tenant_id, actor.user_id, req)
    session.commit()
    return {
        "skill_id": str(skill.id),
        "name": skill.name,
        "version": skill.version,
        "status": "created",
    }

@router.get("/v1/skills")
def list_skills(
    actor: ActorContext = Depends(get_current_actor),
    session: Session = Depends(get_session),
):
    skills = session.execute(
        select(models.Skill)
        .where(models.Skill.tenant_id == actor.tenant_id)
        .order_by(models.Skill.created_at.desc())
    ).scalars().all()
    return [
        {
            "id": str(s.id),
            "name": s.name,
            "version": s.version,
            "description": s.description,
            "skill_type": s.skill_type,
            "entrypoint": s.entrypoint,
            "is_active": s.is_active,
        }
        for s in skills
    ]


@router.get("/v1/scheduled-tasks")
def list_scheduled_tasks(
    actor: ActorContext = Depends(require_roles("operator", "admin")),
    session: Session = Depends(get_session),
):
    stmt = (
        select(models.ScheduledTask)
        .where(models.ScheduledTask.tenant_id == actor.tenant_id)
        .order_by(models.ScheduledTask.created_at.desc())
    )
    schedules = session.execute(stmt).scalars().all()
    return [
        {
            "id": str(s.id),
            "name": s.name,
            "cron_expression": s.cron_expression,
            "concurrency_policy": s.concurrency_policy,
            "is_active": s.is_active,
            "task_template": s.task_template,
            "last_run_at": s.last_run_at.isoformat() if s.last_run_at else None,
            "next_run_at": s.next_run_at.isoformat() if s.next_run_at else None,
            "created_at": s.created_at.isoformat() if s.created_at else None,
        }
        for s in schedules
    ]


@router.post("/v1/scheduled-tasks")
def create_scheduled_task(
    req: ScheduledTaskCreateRequest,
    actor: ActorContext = Depends(require_roles("creator", "admin")),
    session: Session = Depends(get_session),
):
    try:
        next_run = compute_next_run(req.cron_expression)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    now = datetime.now(timezone.utc)
    sched = models.ScheduledTask(
        tenant_id=actor.tenant_id,
        name=req.name,
        cron_expression=req.cron_expression,
        concurrency_policy=req.concurrency_policy,
        is_active=req.is_active,
        task_template=req.task_template,
        next_run_at=next_run,
        created_by=actor.user_id,
        created_at=now,
        updated_at=now,
    )
    session.add(sched)
    session.commit()
    write_audit(
        session,
        actor.tenant_id,
        actor.email,
        "scheduled_task.created",
        "scheduled_task",
        str(sched.id),
        {"name": sched.name, "cron_expression": sched.cron_expression, "next_run_at": next_run.isoformat()},
    )
    session.commit()
    return {
        "id": str(sched.id),
        "name": sched.name,
        "cron_expression": sched.cron_expression,
        "is_active": sched.is_active,
        "next_run_at": sched.next_run_at.isoformat() if sched.next_run_at else None,
        "created_at": sched.created_at.isoformat() if sched.created_at else now.isoformat(),
    }


@router.patch("/v1/scheduled-tasks/{schedule_id}")
def update_scheduled_task(
    schedule_id: str,
    req: ScheduledTaskUpdateRequest,
    actor: ActorContext = Depends(require_roles("creator", "admin")),
    session: Session = Depends(get_session),
):
    sched = session.get(models.ScheduledTask, uuid.UUID(schedule_id))
    if not sched or sched.tenant_id != actor.tenant_id:
        raise HTTPException(status_code=404, detail="scheduled task not found")

    if req.name is not None:
        sched.name = req.name
    if req.cron_expression is not None:
        try:
            sched.cron_expression = req.cron_expression
            sched.next_run_at = compute_next_run(req.cron_expression)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
    if req.concurrency_policy is not None:
        sched.concurrency_policy = req.concurrency_policy
    if req.task_template is not None:
        sched.task_template = req.task_template
    if req.is_active is not None:
        sched.is_active = req.is_active

    sched.updated_at = datetime.now(timezone.utc)
    session.commit()
    write_audit(
        session,
        actor.tenant_id,
        actor.email,
        "scheduled_task.updated",
        "scheduled_task",
        str(sched.id),
        {"name": sched.name, "is_active": sched.is_active},
    )
    session.commit()
    return {
        "id": str(sched.id),
        "name": sched.name,
        "cron_expression": sched.cron_expression,
        "is_active": sched.is_active,
        "next_run_at": sched.next_run_at.isoformat() if sched.next_run_at else None,
    }


@router.post("/v1/scheduled-tasks/{schedule_id}/run")
def run_scheduled_task_immediately(
    schedule_id: str,
    actor: ActorContext = Depends(require_roles("creator", "operator", "admin")),
    session: Session = Depends(get_session),
):
    sched = session.get(models.ScheduledTask, uuid.UUID(schedule_id))
    if not sched or sched.tenant_id != actor.tenant_id:
        raise HTTPException(status_code=404, detail="scheduled task not found")

    settings = get_settings()
    bus = get_bus(settings.kafka_bootstrap_servers)
    task = trigger_scheduled_task(session, bus, sched, actor_email=actor.email)
    return {
        "triggered": True,
        "scheduled_task_id": str(sched.id),
        "task_id": str(task.id),
        "status": task.status,
    }


@router.post("/v1/scheduled-tasks/evaluate")
def evaluate_schedules_endpoint(
    actor: ActorContext = Depends(require_roles("operator", "admin")),
    session: Session = Depends(get_session),
):
    settings = get_settings()
    bus = get_bus(settings.kafka_bootstrap_servers)
    res = evaluate_scheduled_tasks(session, bus, settings)
    return res


@router.get("/v1/sessions")
def list_sessions(
    actor: ActorContext = Depends(require_roles("operator", "admin")),
    session: Session = Depends(get_session),
):
    stmt = (
        select(models.TaskArtifact)
        .join(models.Task, models.Task.id == models.TaskArtifact.task_id)
        .where(
            models.Task.tenant_id == actor.tenant_id,
            models.TaskArtifact.artifact_type == "storage_state",
        )
        .order_by(models.TaskArtifact.created_at.desc())
    )
    artifacts = session.execute(stmt).scalars().all()
    sessions_by_name = {}
    for a in artifacts:
        meta = a.metadata_ or {}
        s_name = meta.get("session_name") or f"session-{str(a.id)[:8]}"
        if s_name not in sessions_by_name:
            sessions_by_name[s_name] = {
                "session_name": s_name,
                "artifact_id": str(a.id),
                "task_id": str(a.task_id),
                "cookies_count": meta.get("cookies_count", 0),
                "created_at": a.created_at.isoformat(),
                "uri": a.uri,
                "backend": meta.get("backend", "local"),
                "status": meta.get("status", "valid"),
                "encryption": meta.get("encryption") or {"encrypted": False, "algorithm": "none"},
            }
    return list(sessions_by_name.values())


@router.post("/v1/sessions/{session_name}/validate")
def validate_session(
    session_name: str,
    actor: ActorContext = Depends(require_roles("operator", "admin")),
    session: Session = Depends(get_session),
):
    stmt = (
        select(models.TaskArtifact)
        .join(models.Task, models.Task.id == models.TaskArtifact.task_id)
        .where(
            models.Task.tenant_id == actor.tenant_id,
            models.TaskArtifact.artifact_type == "storage_state",
        )
        .order_by(models.TaskArtifact.created_at.desc())
    )
    artifacts = session.execute(stmt).scalars().all()
    target_art = None
    for a in artifacts:
        meta = a.metadata_ or {}
        if meta.get("session_name") == session_name:
            target_art = a
            break

    if not target_art:
        raise HTTPException(status_code=404, detail="session not found")

    settings = get_settings()
    artifact_store = build_artifact_store_from_settings(settings)
    try:
        raw_bytes = artifact_store.read_bytes(target_art.uri)
        decrypted = decrypt_session_vault_payload(
            raw_bytes,
            target_art.metadata_ or {},
            tenant_id=str(actor.tenant_id),
        )
        cookies = decrypted.get("cookies", [])
        return {
            "valid": True,
            "session_name": session_name,
            "cookies_count": len(cookies),
            "encryption": (target_art.metadata_ or {}).get("encryption") or {"encrypted": False},
            "status": "valid",
        }
    except Exception as exc:
        return {
            "valid": False,
            "session_name": session_name,
            "error": str(exc),
            "status": "invalid",
        }



@router.delete("/v1/sessions/{session_name}")
def delete_session(
    session_name: str,
    actor: ActorContext = Depends(require_roles("admin")),
    session: Session = Depends(get_session),
):
    stmt = (
        select(models.TaskArtifact)
        .join(models.Task, models.Task.id == models.TaskArtifact.task_id)
        .where(
            models.Task.tenant_id == actor.tenant_id,
            models.TaskArtifact.artifact_type == "storage_state",
        )
    )
    artifacts = session.execute(stmt).scalars().all()
    revoked_count = 0
    for a in artifacts:
        meta = dict(a.metadata_ or {})
        if meta.get("session_name") == session_name:
            meta["status"] = "revoked"
            a.metadata_ = meta
            session.add(a)
            revoked_count += 1

    session.commit()
    write_audit(
        session,
        actor.tenant_id,
        actor.email,
        "session.revoked",
        "session",
        session_name,
        {"revoked_artifacts_count": revoked_count},
    )
    session.commit()
    return {"revoked": True, "session_name": session_name, "count": revoked_count}


@router.get("/v1/tasks/{task_id}/video")
def get_task_video(
    task_id: str,
    actor: ActorContext = Depends(require_roles("creator", "approver", "operator", "admin")),
    session: Session = Depends(get_session),
):
    task = session.get(models.Task, uuid.UUID(task_id))
    if not task or task.tenant_id != actor.tenant_id:
        raise HTTPException(status_code=404, detail="task not found")

    video_art = None
    for a in getattr(task, "artifacts", []):
        if a.artifact_type == "video":
            video_art = a
            break

    if not video_art:
        raise HTTPException(status_code=404, detail="no video recording found for this task")

    return RedirectResponse(url=f"/v1/artifacts/{video_art.id}/content", status_code=307)


@router.get("/v1/ops/otlp/status")
def get_otlp_status(actor: ActorContext = Depends(require_roles("operator", "admin"))):
    settings = get_settings()
    exporter = get_otlp_exporter(settings)
    return exporter.status()


@router.post("/v1/ops/otlp/flush")
def flush_otlp_spans(actor: ActorContext = Depends(require_roles("admin"))):
    settings = get_settings()
    exporter = get_otlp_exporter(settings)
    res = exporter.flush()
    return {"flushed": True, "result": res, "status": exporter.status()}


# --- V1.3 OIDC Authorization Code Flow 端點 ---

_OIDC_PKCE_STORE: dict[str, tuple[str, float]] = {}

@router.get("/v1/auth/oidc/login")
def oidc_login():
    """發起 OIDC SSO 導頁，生成 PKCE 與 state 並重導向至 IdP 授權端點"""
    settings = get_settings()
    state, verifier, challenge = generate_oidc_pkce()
    # 暫存 state 與 verifier (TTL 300s)
    now = time.time()
    _OIDC_PKCE_STORE[state] = (verifier, now + 300)

    auth_url = build_oidc_auth_url(settings, state, challenge)
    return {
        "redirect_url": auth_url,
        "state": state,
        "auth_url": auth_url,
    }


@router.get("/v1/auth/oidc/callback")
def oidc_callback(code: str, state: str, response: Response):
    """處理 IdP 授權回調，交換 Token 並寫入 HttpOnly Session Cookie"""
    settings = get_settings()
    verifier_info = _OIDC_PKCE_STORE.pop(state, None)
    verifier = verifier_info[0] if verifier_info and verifier_info[1] > time.time() else ""

    token_claims = exchange_oidc_code_for_token(settings, code, verifier)

    email = token_claims.get("email") or "sso.user@example.com"
    roles = token_claims.get("roles") or ["operator"]
    sub_id = token_claims.get("sub") or str(uuid.uuid4())

    actor = ActorContext(
        user_id=uuid.UUID(str(sub_id)),
        tenant_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
        email=email,
        roles=tuple(roles),
    )
    access_token = create_access_token(actor, settings=settings)

    # 設置 HttpOnly 安全 Session Cookie
    response.set_cookie(
        key="ba_session",
        value=access_token,
        httponly=True,
        samesite="lax",
        secure=False,  # 本機/開發環境相容
        max_age=settings.auth_token_ttl_seconds,
    )
    return {
        "authenticated": True,
        "email": email,
        "roles": list(roles),
        "message": "OIDC login successful, ba_session cookie set",
        "redirect": "/operations",
    }


@router.post("/v1/auth/logout")
def oidc_logout(response: Response):
    """清除前端 Session Cookie"""
    response.delete_cookie(key="ba_session")
    return {"logged_out": True, "message": "Session cookie cleared"}


# --- V1.3 KMS 信封加密與佇列狀態端點 ---

@router.get("/v1/ops/kms/status")
def get_kms_status(actor: ActorContext = Depends(require_roles("operator", "admin"))):
    """取得當前 Session Vault 之 KMS 信封加密狀態"""
    settings = get_settings()
    provider = get_kms_provider(settings)
    return provider.status()


@router.get("/v1/ops/queues")
def get_queues_status(actor: ActorContext = Depends(require_roles("operator", "admin"))):
    """檢視多優先權佇列與 Worker 資源池配置"""
    settings = get_settings()
    return {
        "multi_priority_enabled": getattr(settings, "multi_priority_enabled", True),
        "worker_pool": getattr(settings, "worker_pool", "default"),
        "topics": {
            "high": getattr(settings, "queue_high_topic", "agent.tasks.high"),
            "default": getattr(settings, "queue_default_topic", "agent.tasks.queued"),
            "batch": getattr(settings, "queue_batch_topic", "agent.tasks.batch"),
            "dlq": getattr(settings, "dlq_topic", "agent.tasks.dlq"),
        },
        "status": "healthy",
    }


# --- V1.3 即時畫面廣播 (Live Stream) 與中斷 (Abort) 端點 ---

@router.get("/v1/tasks/{task_id}/live-frame")
def get_task_live_frame(
    task_id: str,
    actor: ActorContext = Depends(require_roles("creator", "approver", "operator", "admin")),
):
    """取得執行中任務的最新單一畫面幀（供輪詢或降級檢視）"""
    broadcaster = get_telemetry_broadcaster()
    frame = broadcaster.get_latest_frame(task_id)
    if not frame:
        return {"task_id": task_id, "frame_available": False, "message": "No active live frame"}
    return {"task_id": task_id, "frame_available": True, **frame}


@router.post("/v1/tasks/{task_id}/abort")
def abort_task_execution(
    task_id: str,
    actor: ActorContext = Depends(require_roles("operator", "admin")),
    session: Session = Depends(get_session),
):
    """維運人員緊急中斷正在執行中之任務"""
    task = session.get(models.Task, uuid.UUID(task_id))
    if not task or task.tenant_id != actor.tenant_id:
        raise HTTPException(status_code=404, detail="task not found")

    broadcaster = get_telemetry_broadcaster()
    broadcaster.request_abort(task_id, reason=f"Aborted by {actor.email}")

    write_audit(
        session,
        actor.tenant_id,
        actor.email,
        "task.abort_requested",
        "task",
        task_id,
        {"requested_by": actor.email},
    )
    session.commit()
    return {"aborted": True, "task_id": task_id, "message": "Abort signal dispatched to worker"}


@router.websocket("/v1/tasks/{task_id}/live-stream")
async def task_live_stream(websocket: WebSocket, task_id: str):
    """WebSocket 雙向/低延遲畫面幀廣播端點"""
    await websocket.accept()
    broadcaster = get_telemetry_broadcaster()
    queue = await broadcaster.subscribe(task_id)
    try:
        while True:
            payload = await queue.get()
            await websocket.send_json(payload)
            if payload.get("type") == "aborted":
                break
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        logger.debug("Live stream websocket client closed: %s", exc)
    finally:
        await broadcaster.unsubscribe(task_id, queue)


# --- V1.4 雙向即時遠端接管 (HITL) 端點 ---

@router.post("/v1/tasks/{task_id}/interact")
def interact_with_task(
    task_id: str,
    req: TaskInteractRequest,
    actor: ActorContext = Depends(require_roles("operator", "admin")),
    session: Session = Depends(get_session),
):
    """維運人員反向控制瀏覽器 Page（點擊、鍵盤輸入、滾輪等）"""
    task = session.get(models.Task, uuid.UUID(task_id))
    if not task or task.tenant_id != actor.tenant_id:
        raise HTTPException(status_code=404, detail="task not found")

    broadcaster = get_telemetry_broadcaster()
    broadcaster.queue_action(task_id, req.model_dump())
    return {"queued": True, "task_id": task_id, "action": req.action}


@router.post("/v1/tasks/{task_id}/pause")
def pause_task_for_hitl(
    task_id: str,
    req: TaskPauseRequest = Body(default=TaskPauseRequest()),
    actor: ActorContext = Depends(require_roles("operator", "admin")),
    session: Session = Depends(get_session),
):
    """人機協同 (HITL)：暫停任務自動推進，進入接管模式"""
    task = session.get(models.Task, uuid.UUID(task_id))
    if not task or task.tenant_id != actor.tenant_id:
        raise HTTPException(status_code=404, detail="task not found")

    broadcaster = get_telemetry_broadcaster()
    broadcaster.pause_task(task_id, operator=actor.email, reason=req.reason)

    write_audit(
        session,
        actor.tenant_id,
        actor.email,
        "task.paused_for_hitl",
        "task",
        task_id,
        {"requested_by": actor.email, "reason": req.reason},
    )
    session.commit()
    return {"paused": True, "task_id": task_id, "operator": actor.email}


@router.post("/v1/tasks/{task_id}/resume")
def resume_task_after_hitl(
    task_id: str,
    actor: ActorContext = Depends(require_roles("operator", "admin")),
    session: Session = Depends(get_session),
):
    """恢復任務自動化執行流程"""
    task = session.get(models.Task, uuid.UUID(task_id))
    if not task or task.tenant_id != actor.tenant_id:
        raise HTTPException(status_code=404, detail="task not found")

    broadcaster = get_telemetry_broadcaster()
    broadcaster.resume_task(task_id, operator=actor.email)

    write_audit(
        session,
        actor.tenant_id,
        actor.email,
        "task.resumed_from_hitl",
        "task",
        task_id,
        {"resumed_by": actor.email},
    )
    session.commit()
    return {"resumed": True, "task_id": task_id, "operator": actor.email}


# --- V1.4 跨瀏覽器矩陣執行 (Cross-Browser Matrix) 端點 ---

@router.post("/v1/tasks/matrix")
def create_cross_browser_matrix_tasks(
    req: MatrixTaskCreateRequest,
    request: Request,
    actor: ActorContext = Depends(require_roles("creator", "admin")),
    session: Session = Depends(get_session),
):
    """一鍵派發跨瀏覽器矩陣任務（Chromium / Firefox / WebKit）"""
    settings = get_settings()
    bus = get_bus(settings.kafka_bootstrap_servers)
    orch = Orchestrator(session, bus)
    matrix_id = f"matrix-{uuid.uuid4().hex[:12]}"
    correlation_id = _correlation_id(request)

    created_tasks = []
    engines = req.engines if req.engines else ["chromium", "firefox", "webkit"]
    for eng in engines:
        payload = {
            "title": f"[{eng.capitalize()}] {req.title}",
            "instructions": req.instructions,
            "priority": req.priority,
            "risk_level": req.risk_level,
            "browser_engine": eng,
            "matrix_id": matrix_id,
            "metadata": {
                **req.metadata,
                "browser_engine": eng,
                "matrix_id": matrix_id,
            },
        }
        try:
            t = orch.create_task(
                actor.tenant_id,
                actor.user_id,
                payload,
                correlation_id=f"{correlation_id}-{eng}",
                actor_label=actor.email,
                actor_payload=actor_request_payload(actor),
            )
            created_tasks.append(t)
        except ValueError as exc:
            session.rollback()
            raise HTTPException(status_code=400, detail=str(exc))

    session.commit()
    return {
        "matrix_id": matrix_id,
        "total_tasks": len(created_tasks),
        "tasks": [
            {
                "task_id": str(t.id),
                "browser_engine": t.browser_engine,
                "status": t.status,
                "title": t.title,
            }
            for t in created_tasks
        ],
    }


@router.get("/v1/tasks/matrix/{matrix_id}")
def get_matrix_tasks_summary(
    matrix_id: str,
    actor: ActorContext = Depends(get_current_actor),
    session: Session = Depends(get_session),
):
    """查詢跨瀏覽器矩陣任務之聚合結果、差異與狀態"""
    tasks = (
        session.execute(
            select(models.Task)
            .where(models.Task.tenant_id == actor.tenant_id, models.Task.matrix_id == matrix_id)
            .order_by(models.Task.created_at.asc())
        )
        .scalars()
        .all()
    )
    if not tasks:
        raise HTTPException(status_code=404, detail="matrix not found")

    tasks_out = []
    for t in tasks:
        meta = t.metadata_ or {}
        eval_data = meta.get("evaluation") or {}
        tasks_out.append({
            "task_id": str(t.id),
            "browser_engine": t.browser_engine,
            "status": t.status,
            "title": t.title,
            "verdict": eval_data.get("verdict"),
            "score": eval_data.get("score"),
            "self_healed": bool(meta.get("self_healing")),
            "dlp_masked": getattr(t, "dlp_masked", False),
            "human_intervened": getattr(t, "human_intervened", False),
            "video_artifact_id": meta.get("video_artifact_id"),
            "created_at": t.created_at.isoformat(),
            "completed_at": t.completed_at.isoformat() if t.completed_at else None,
        })

    return {
        "matrix_id": matrix_id,
        "total_tasks": len(tasks_out),
        "tasks": tasks_out,
    }


# --- V1.4 Zero-Trust DLP 與 Multi-Cluster Federation 端點 ---

@router.get("/v1/ops/dlp/status")
def get_dlp_status_endpoint(actor: ActorContext = Depends(require_roles("operator", "admin"))):
    """查詢 Zero-Trust DLP 動態情境防護引擎狀態"""
    dlp = get_dlp_service()
    return dlp.get_status()


@router.get("/v1/ops/federation/nodes")
def get_federation_topology_endpoint(actor: ActorContext = Depends(require_roles("operator", "admin"))):
    """查詢多叢集排程同盟之節點清單與拓撲狀態"""
    mgr = get_federation_manager()
    return mgr.get_topology()


@router.post("/v1/ops/federation/heartbeat")
def post_federation_heartbeat_endpoint(
    req: FederationHeartbeatRequest,
    actor: ActorContext = Depends(require_roles("operator", "admin")),
    session: Session = Depends(get_session),
):
    """註冊或更新同盟節點心跳"""
    mgr = get_federation_manager()
    node = mgr.register_heartbeat(
        node_id=req.node_id,
        region=req.region,
        active_schedules_count=req.active_schedules_count,
        metadata=req.metadata,
        is_leader=req.is_leader,
        db_session=session,
    )
    return {"registered": True, "node": node}


@router.post("/v1/ops/federation/re-election")
def force_federation_reelection_endpoint(
    target_node_id: str | None = Body(default=None, embed=True),
    actor: ActorContext = Depends(require_roles("admin")),
):
    """強制轉移或重新選舉同盟叢集 Leader 節點"""
    mgr = get_federation_manager()
    new_leader = mgr.force_reelection(target_node_id=target_node_id)
    return {"re_elected": True, "leader_node_id": new_leader}


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(getattr(settings, "app_log_level", "INFO"))
    app = FastAPI(title=getattr(settings, "app_name", "browser-agent"), version=getattr(settings, "app_version", "1.4.0"))


    @app.middleware("http")
    async def correlation_middleware(request: Request, call_next):
        context = build_request_context(request.headers, get_settings())
        token = set_request_context(context)
        started = time.monotonic()
        try:
            response = await call_next(request)
            response.headers["X-Correlation-ID"] = context.correlation_id
            HTTP_REQUESTS.labels(request.method, request.url.path, str(response.status_code)).inc()
            HTTP_DURATION.labels(request.method, request.url.path).observe(time.monotonic() - started)
            active_context = get_request_context() or context
            logger.info(
                "http request completed",
                extra={
                    **active_context.log_fields("http.request"),
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_ms": round((time.monotonic() - started) * 1000, 2),
                },
            )
            from .tracing import get_trace_buffer, Span
            get_trace_buffer().record(Span(
                name=f"http.{request.method}:{request.url.path}",
                trace_id=context.trace_id,
                span_id=context.span_id,
                parent_span_id=context.parent_span_id,
                service=context.service_name,
                duration_ms=round((time.monotonic() - started) * 1000, 2),
                status="ok" if response.status_code < 400 else "error",
                attributes={
                    "http.method": request.method,
                    "http.path": request.url.path,
                    "http.status_code": response.status_code,
                },
            ))
            return response
        finally:
            reset_request_context(token)

    app.include_router(router)
    return app
