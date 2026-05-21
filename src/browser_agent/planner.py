from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any


SUPPORTED_ACTIONS = {"goto", "click", "fill", "press", "wait", "extract_text", "screenshot"}
PLANNER_VERSION = "heuristic-v0.4"


@dataclass(frozen=True)
class PlannerValidationError:
    step_no: int
    action: str | None
    message: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "step_no": self.step_no,
            "action": self.action,
            "message": self.message,
        }


@dataclass(frozen=True)
class PlannerStep:
    action: str
    input_data: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return dict(self.input_data)


@dataclass(frozen=True)
class PlannerOutput:
    goal: str | None
    version: str
    source: str
    steps: list[PlannerStep]
    risk_level: str
    valid: bool
    errors: list[dict[str, Any]]


def validate_plan_output(output: dict[str, Any]) -> PlannerOutput:
    steps = output.get("steps")
    errors: list[PlannerValidationError] = []
    validated_steps: list[PlannerStep] = []

    if not isinstance(steps, list) or not steps:
        errors.append(PlannerValidationError(0, None, "steps must be a non-empty list"))
        steps = []

    for index, step in enumerate(steps, start=1):
        if not isinstance(step, dict):
            errors.append(PlannerValidationError(index, None, "step must be an object"))
            continue
        action = step.get("action")
        if action not in SUPPORTED_ACTIONS:
            errors.append(PlannerValidationError(index, action, f"unsupported action: {action}"))
            continue
        errors.extend(_validate_step_fields(index, action, step))
        if not _is_json_serializable(step):
            errors.append(PlannerValidationError(index, action, "step input_data must be JSON serializable"))
            continue
        validated_steps.append(PlannerStep(action=action, input_data=dict(step)))

    return PlannerOutput(
        goal=output.get("goal"),
        version=output.get("version") or PLANNER_VERSION,
        source=output.get("source") or "heuristic",
        steps=validated_steps,
        risk_level=output.get("risk_level", "low"),
        valid=not errors,
        errors=[error.as_dict() for error in errors],
    )


def deterministic_fallback_plan(task: dict[str, Any]) -> dict[str, Any]:
    metadata = task.get("metadata") or {}
    start_url = metadata.get("start_url")
    steps: list[dict[str, Any]] = []
    if start_url:
        steps.append({"action": "goto", "url": start_url})
    steps.append({"action": "screenshot"})
    return {
        "goal": task.get("title"),
        "version": PLANNER_VERSION,
        "source": "fallback",
        "steps": steps,
        "risk_level": task.get("risk_level", "low"),
    }


def build_planner_metadata(output: dict[str, Any], task: dict[str, Any]) -> dict[str, Any]:
    validated = validate_plan_output(output)
    fallback_used = not validated.valid
    final_output = deterministic_fallback_plan(task) if fallback_used else output
    final_validated = validate_plan_output(final_output)
    return {
        "planner": {
            "version": validated.version,
            "valid": validated.valid,
            "source": validated.source,
            "validation_errors": validated.errors,
            "fallback_used": fallback_used,
            "fallback_source": final_validated.source if fallback_used else None,
        },
        "plan": [step.as_dict() for step in final_validated.steps],
    }


def _validate_step_fields(step_no: int, action: str, step: dict[str, Any]) -> list[PlannerValidationError]:
    errors: list[PlannerValidationError] = []
    if action == "goto" and not step.get("url"):
        errors.append(PlannerValidationError(step_no, action, "goto requires url"))
    if action in {"click", "extract_text"} and not step.get("target"):
        errors.append(PlannerValidationError(step_no, action, f"{action} requires target"))
    if action == "fill":
        if not step.get("target"):
            errors.append(PlannerValidationError(step_no, action, "fill requires target"))
        if "value" not in step:
            errors.append(PlannerValidationError(step_no, action, "fill requires value"))
    if action == "press":
        if not step.get("target"):
            errors.append(PlannerValidationError(step_no, action, "press requires target"))
        if "value" not in step:
            errors.append(PlannerValidationError(step_no, action, "press requires value"))
    if action == "wait":
        ms = step.get("ms")
        if not isinstance(ms, int) or ms < 0:
            errors.append(PlannerValidationError(step_no, action, "wait requires non-negative integer ms"))
    return errors


def _is_json_serializable(value: Any) -> bool:
    try:
        json.dumps(value)
    except (TypeError, ValueError):
        return False
    return True
