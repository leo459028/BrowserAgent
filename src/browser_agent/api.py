from __future__ import annotations

import uuid
from pathlib import Path
from fastapi import APIRouter, Depends, FastAPI, HTTPException
from fastapi import Request
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from .config import get_settings
from .db import get_session_factory
from . import models
from .schemas import TaskCreateRequest, TaskApproveRequest, SkillCreateRequest
from .orchestrator import Orchestrator
from .skillhub import SkillHub
from .kafka import get_bus
from .logging import configure_logging

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))

def get_session():
    session = get_session_factory()()
    try:
        yield session
    finally:
        session.close()

def _tenant_id() -> uuid.UUID:
    return uuid.UUID("00000000-0000-0000-0000-000000000001")

def _actor() -> uuid.UUID:
    return uuid.UUID("00000000-0000-0000-0000-000000000002")

def _demo_actor_label() -> str:
    return "ops@example.com"

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
def metrics():
    return PlainTextResponse(generate_latest(), media_type=CONTENT_TYPE_LATEST)

@router.get("/demo")
def demo(request: Request):
    return templates.TemplateResponse(
        request,
        "demo.html",
        {
            "demo_payload": DEMO_TASK_PAYLOAD,
            "demo_actor": _demo_actor_label(),
        },
    )

@router.post("/v1/tasks")
def create_task(req: TaskCreateRequest, session: Session = Depends(get_session)):
    settings = get_settings()
    bus = get_bus(settings.kafka_bootstrap_servers)
    orch = Orchestrator(session, bus)
    try:
        task = orch.create_task(_tenant_id(), _actor(), req.model_dump())
        session.commit()
    except ValueError as exc:
        session.rollback()
        raise HTTPException(status_code=400, detail=str(exc))
    return {
        "task_id": str(task.id),
        "status": task.status,
        "created_at": task.created_at.isoformat(),
    }

@router.get("/v1/tasks/{task_id}")
def get_task(task_id: str, session: Session = Depends(get_session)):
    task = session.get(models.Task, uuid.UUID(task_id))
    if not task:
        raise HTTPException(status_code=404, detail="task not found")
    return serialize_task(task)

@router.get("/v1/artifacts/{artifact_id}/content")
def get_artifact_content(artifact_id: str, session: Session = Depends(get_session)):
    artifact = session.get(models.TaskArtifact, uuid.UUID(artifact_id))
    if not artifact:
        raise HTTPException(status_code=404, detail="artifact not found")
    settings = get_settings()
    path = resolve_artifact_file_path(settings.artifact_base_path, artifact.uri)
    metadata = artifact.metadata_ or {}
    media_type = metadata.get("media_type") or "application/octet-stream"
    response = FileResponse(path, media_type=media_type, filename=path.name)
    response.headers["Content-Disposition"] = f'inline; filename="{path.name}"'
    return response

def serialize_task(task) -> dict:
    metadata = getattr(task, "metadata_", None)
    if metadata is None:
        metadata = getattr(task, "metadata", {})
    artifacts = [
        {
            "id": str(a.id),
            "artifact_type": a.artifact_type,
            "uri": a.uri,
            "sha256": a.sha256,
            "metadata": getattr(a, "metadata_", None) if getattr(a, "metadata_", None) is not None else getattr(a, "metadata", {}),
            "created_at": a.created_at.isoformat(),
            "download_url": f"/v1/artifacts/{a.id}/content",
        }
        for a in sorted(getattr(task, "artifacts", []), key=lambda x: x.created_at)
    ]
    return {
        "id": str(task.id),
        "tenant_id": str(task.tenant_id),
        "title": task.title,
        "instructions": task.instructions,
        "status": task.status,
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

@router.post("/v1/tasks/{task_id}/approve")
def approve_task(task_id: str, req: TaskApproveRequest, session: Session = Depends(get_session)):
    settings = get_settings()
    bus = get_bus(settings.kafka_bootstrap_servers)
    orch = Orchestrator(session, bus)
    task = session.get(models.Task, uuid.UUID(task_id))
    if not task:
        raise HTTPException(status_code=404, detail="task not found")
    approval = orch.approve_task(task, _actor(), req.approved_by, req.note)
    session.commit()
    return {
        "task_id": str(task.id),
        "approval_id": str(approval.id),
        "status": task.status,
    }

@router.post("/v1/skills")
def create_skill(req: SkillCreateRequest, session: Session = Depends(get_session)):
    skillhub = SkillHub(session)
    skill = skillhub.register(_tenant_id(), _actor(), req)
    session.commit()
    return {
        "skill_id": str(skill.id),
        "name": skill.name,
        "version": skill.version,
        "status": "created",
    }

@router.get("/v1/skills")
def list_skills(session: Session = Depends(get_session)):
    skills = session.execute(select(models.Skill).order_by(models.Skill.created_at.desc())).scalars().all()
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
    app = FastAPI(title=settings.app_name, version="1.0.0")
    app.include_router(router)
    return app
