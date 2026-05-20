from __future__ import annotations

import time
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from . import models
from .audit import write_audit
from .evaluator import evaluate_execution
from .metrics import TASK_DURATION, TASK_EXECUTED
from .services.browser import BrowserRunner
from .services.tasks import set_task_status, set_task_status_with_audit, add_step
from .services.artifacts import build_artifact_store
from .llm import HeuristicPlanner

class TaskRunner:
    def __init__(self, session: Session, artifact_base_path: str, headless: bool, allowed_domains: set[str]):
        self.session = session
        self.artifact_store = build_artifact_store(artifact_base_path)
        self.browser = BrowserRunner(headless=headless)
        self.allowed_domains = allowed_domains
        self.planner = HeuristicPlanner()

    def run(self, task: models.Task) -> dict:
        started = time.monotonic()
        plan = self.planner.plan({
            "title": task.title,
            "instructions": task.instructions,
            "risk_level": task.risk_level,
            "metadata": task.metadata_,
        })
        task.metadata_ = {**(task.metadata_ or {}), "plan": plan["steps"]}
        set_task_status_with_audit(
            self.session,
            task,
            "executing",
            action="task.execution_started",
            actor="worker",
        )
        task.started_at = datetime.now(timezone.utc)
        self.session.add(task)

        for i, step in enumerate(plan["steps"], start=1):
            add_step(
                self.session,
                task=task,
                step_no=i,
                action_type=step["action"],
                instruction=f"Execute {step['action']}",
                target=step.get("target") or step.get("url"),
                input_data=step,
            )
        self.session.flush()

        result = self.browser.execute(
            {
                "id": str(task.id),
                "metadata": task.metadata_,
            },
            self.artifact_store,
            self.allowed_domains,
        )

        for artifact in result.artifacts:
            self.session.add(models.TaskArtifact(
                task_id=task.id,
                artifact_type=artifact["type"],
                uri=artifact["uri"],
                sha256=artifact.get("sha256"),
                metadata_={"media_type": _artifact_media_type(artifact["type"])},
            ))
            write_audit(
                self.session,
                task.tenant_id,
                "worker",
                "task.artifact_written",
                "task",
                str(task.id),
                {
                    "artifact_type": artifact["type"],
                    "uri": artifact["uri"],
                    "sha256": artifact.get("sha256"),
                    "correlation_id": task.correlation_id,
                },
            )

        eval_result = evaluate_execution(
            {"metadata": task.metadata_},
            {
                "final_url": result.final_url,
                "html": result.html,
                "artifacts": result.artifacts,
            },
        )

        self.session.add(models.Evaluation(
            task_id=task.id,
            evaluator_ver="1.0.0",
            score=eval_result.score,
            verdict=eval_result.verdict,
            checks=eval_result.checks,
        ))
        write_audit(
            self.session,
            task.tenant_id,
            "worker",
            "task.evaluated",
            "task",
            str(task.id),
            {
                "score": eval_result.score,
                "verdict": eval_result.verdict,
                "correlation_id": task.correlation_id,
            },
        )
        task.completed_at = datetime.now(timezone.utc)
        final_status = "completed" if eval_result.verdict == "pass" else "review"
        set_task_status(self.session, task, final_status)
        task.metadata_ = {
            **(task.metadata_ or {}),
            "browser_result": {
                "final_url": result.final_url,
                "title": result.title,
                "observations": result.observations,
            },
            "evaluation": {
                "score": eval_result.score,
                "verdict": eval_result.verdict,
                "checks": eval_result.checks,
            },
        }
        self.session.add(task)
        write_audit(
            self.session,
            task.tenant_id,
            "worker",
            "task.completed" if final_status == "completed" else "task.review_required",
            "task",
            str(task.id),
            {"status": final_status, "correlation_id": task.correlation_id},
        )
        TASK_EXECUTED.inc()
        TASK_DURATION.observe(time.monotonic() - started)
        return task.metadata_


def _artifact_media_type(artifact_type: str) -> str:
    if artifact_type == "screenshot":
        return "image/png"
    if artifact_type == "html":
        return "text/html; charset=utf-8"
    return "application/octet-stream"
