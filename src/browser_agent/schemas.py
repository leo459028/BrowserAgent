from pydantic import BaseModel, Field, ConfigDict
from typing import Any
from uuid import UUID

class TaskCreateRequest(BaseModel):
    title: str
    instructions: str
    priority: int = 0
    risk_level: str = "low"
    metadata: dict[str, Any] = Field(default_factory=dict)

class TaskApproveRequest(BaseModel):
    approved_by: str | None = None
    note: str | None = None

class LocalTokenRequest(BaseModel):
    role: str

class DlqBulkReplayRequest(BaseModel):
    task_ids: list[UUID]
    note: str | None = None

class DlqQuarantineRequest(BaseModel):
    reason: str

class SkillCreateRequest(BaseModel):
    name: str
    version: str
    description: str | None = None
    skill_type: str
    entrypoint: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    policy_tags: list[str] = Field(default_factory=list)

class TaskStepOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    step_no: int
    action_type: str
    target: str | None
    instruction: str
    status: str
    input_data: dict
    output_data: dict
    error_message: str | None

class TaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    title: str
    instructions: str
    status: str
    correlation_id: str | None = None
    priority: int
    risk_level: str
    metadata: dict
    created_at: str
    updated_at: str | None = None
    steps: list[TaskStepOut] = Field(default_factory=list)

class SkillOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    version: str
    description: str | None
    skill_type: str
    entrypoint: str
    input_schema: dict
    output_schema: dict
    policy_tags: list[str]
    is_active: bool
