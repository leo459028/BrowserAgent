from __future__ import annotations

from sqlalchemy.orm import Session
from . import models
from .schemas import SkillCreateRequest

class SkillHub:
    def __init__(self, session: Session):
        self.session = session

    def register(self, tenant_id, created_by, spec: SkillCreateRequest) -> models.Skill:
        skill = models.Skill(
            tenant_id=tenant_id,
            created_by=created_by,
            name=spec.name,
            version=spec.version,
            description=spec.description,
            skill_type=spec.skill_type,
            entrypoint=spec.entrypoint,
            input_schema=spec.input_schema,
            output_schema=spec.output_schema,
            policy_tags=spec.policy_tags,
            is_active=True,
        )
        self.session.add(skill)
        self.session.flush()
        return skill

    def resolve(self, tenant_id, name: str, version: str | None = None) -> models.Skill | None:
        q = self.session.query(models.Skill).filter(
            models.Skill.tenant_id == tenant_id,
            models.Skill.name == name,
            models.Skill.is_active.is_(True),
        )
        if version:
            q = q.filter(models.Skill.version == version)
        else:
            q = q.order_by(models.Skill.created_at.desc())
        return q.first()
