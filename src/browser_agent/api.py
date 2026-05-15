from __future__ import annotations

import uuid
from fastapi import APIRouter, Depends, FastAPI, HTTPException
from fastapi.responses import PlainTextResponse
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
    return {
        "id": str(task.id),
        "tenant_id": str(task.tenant_id),
        "title": task.title,
        "instructions": task.instructions,
        "status": task.status,
        "priority": task.priority,
        "risk_level": task.risk_level,
        "metadata": task.metadata,
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
    }

@router.post("/v1/tasks/{task_id}/approve")
def approve_task(task_id: str, req: TaskApproveRequest, session: Session = Depends(get_session)):
    settings = get_settings()
    bus = get_bus(settings.kafka_bootstrap_servers)
    orch = Orchestrator(session, bus)
    task = session.get(models.Task, uuid.UUID(task_id))
    if not task:
        raise HTTPException(status_code=404, detail="task not found")
    approval = orch.approve_task(task, req.approved_by, req.note)
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
