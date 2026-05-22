from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from fastapi import APIRouter, Body, Depends, FastAPI, Header, HTTPException
from fastapi import Request
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from .config import get_settings
from .db import get_session_factory
from . import models
from .auth import ActorContext, create_access_token, demo_actor_for_role, get_current_actor, require_roles
from .schemas import DemoTokenRequest, TaskCreateRequest, TaskApproveRequest, SkillCreateRequest
from .orchestrator import Orchestrator
from .skillhub import SkillHub
from .kafka import get_bus
from .logging import configure_logging
from .audit import write_audit
from .reliability import get_reliability_store
from .services.tasks import set_task_status

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))

def get_session():
    session = get_session_factory()()
    try:
        yield session
    finally:
        session.close()

DEMO_TASK_PAYLOAD = {
    "title": "Capture example.com",
    "instructions": "Open the allowlisted site and capture a screenshot.",
    "priority": 1,
    "risk_level": "low",
    "metadata": {
        "domains": ["example.com"],
        "start_url": "https://example.com",
        "expected_domain": "example.com",
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

@router.get("/demo")
def demo(request: Request):
    return templates.TemplateResponse(
        request,
        "demo.html",
        {
            "demo_payload": DEMO_TASK_PAYLOAD,
            "demo_roles": ["creator", "approver", "operator", "admin"],
        },
    )

@router.get("/v1/auth/me")
def auth_me(actor: ActorContext = Depends(get_current_actor)):
    return serialize_actor(actor)

@router.post("/v1/auth/demo-token")
def create_demo_token(req: DemoTokenRequest):
    settings = get_settings()
    if not settings.auth_demo_tokens_enabled:
        raise HTTPException(status_code=404, detail="demo tokens disabled")
    try:
        actor = demo_actor_for_role(req.role)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    token = create_access_token(actor, settings=settings)
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": settings.auth_token_ttl_seconds,
        "actor": serialize_actor(actor),
    }

def _correlation_id(request: Request) -> str:
    return request.headers.get("X-Correlation-ID") or str(uuid.uuid4())

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
            actor_payload=actor.audit_payload(),
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
    metadata = task.metadata_ or {}
    reliability = dict(metadata.get("reliability") or {})
    dlq = dict(reliability.get("dlq") or {})
    if task.status != "failed" or not dlq:
        raise HTTPException(status_code=409, detail="task is not replayable from DLQ")

    replay = dict(reliability.get("replay") or {})
    replay["count"] = int(replay.get("count") or 0) + 1
    replay["last_replayed_at"] = datetime.now(timezone.utc).isoformat()
    replay["last_replayed_by"] = actor.email
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
            **actor.audit_payload(),
        },
    )
    session.flush()
    bus.publish("agent.tasks.queued", str(task.id), {
        "event_id": str(uuid.uuid4()),
        "event_type": "task.queued",
        "task_id": str(task.id),
        "tenant_id": str(task.tenant_id),
        "approved_by": actor.email,
        "note": "DLQ replay",
        "correlation_id": task.correlation_id,
        **actor.audit_payload(),
    })
    session.commit()
    return {
        "task_id": str(task.id),
        "status": task.status,
        "replay": replay,
    }

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
    path = resolve_artifact_file_path(settings.artifact_base_path, artifact.uri)
    metadata = artifact.metadata_ or {}
    media_type = metadata.get("content_type") or metadata.get("media_type") or "application/octet-stream"
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
            actor_payload=actor.audit_payload(),
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

def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.app_log_level)
    app = FastAPI(title=settings.app_name, version="0.6.0")
    app.include_router(router)
    return app
