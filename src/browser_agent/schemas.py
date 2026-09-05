from pydantic import BaseModel, Field, ConfigDict
from typing import Any
from uuid import UUID

class TaskCreateRequest(BaseModel):
    title: str
    instructions: str
    priority: int = 0
    risk_level: str = "low"
    browser_engine: str = "chromium"
    matrix_id: str | None = None
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

class AlertTestDispatchRequest(BaseModel):
    rule_id: str = "dlq_threshold"
    note: str = "Test alert dispatch from Operations Center"
    level: str = "warning"

class ScheduledTaskCreateRequest(BaseModel):
    name: str
    cron_expression: str
    concurrency_policy: str = "skip"
    task_template: dict[str, Any]
    is_active: bool = True

class ScheduledTaskUpdateRequest(BaseModel):
    name: str | None = None
    cron_expression: str | None = None
    concurrency_policy: str | None = None
    task_template: dict[str, Any] | None = None
    is_active: bool | None = None


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
    browser_engine: str = "chromium"
    matrix_id: str | None = None
    human_intervened: bool = False
    dlp_masked: bool = False
    metadata: dict
    created_at: str
    updated_at: str | None = None
    steps: list[TaskStepOut] = Field(default_factory=list)

class TaskInteractRequest(BaseModel):
    action: str  # "click", "type", "press", "scroll"
    x: float | None = None
    y: float | None = None
    text: str | None = None
    key: str | None = None
    delta_x: float | None = None
    delta_y: float | None = None

class TaskPauseRequest(BaseModel):
    reason: str = "Operator paused for HITL"

class MatrixTaskCreateRequest(BaseModel):
    title: str
    instructions: str
    priority: int = 0
    risk_level: str = "low"
    engines: list[str] = Field(default_factory=lambda: ["chromium", "firefox", "webkit"])
    metadata: dict[str, Any] = Field(default_factory=dict)

class FederationHeartbeatRequest(BaseModel):
    node_id: str
    region: str = "default"
    active_schedules_count: int = 0
    is_leader: bool | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

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

class ScheduledTaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    name: str
    cron_expression: str
    concurrency_policy: str
    is_active: bool
    task_template: dict
    last_run_at: str | None = None
    next_run_at: str | None = None
    created_at: str
    updated_at: str | None = None
