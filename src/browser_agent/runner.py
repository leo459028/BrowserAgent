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
from .planner import build_planner_metadata
from .skillhub import SkillHub

class TaskRunner:
    def __init__(
        self,
        session: Session,
        artifact_base_path: str,
        headless: bool,
        allowed_domains: set[str],
        timeout_seconds: int = 120,
        worker_actor: str = "worker",
        record_video: bool = True,
    ):
        self.session = session
        self.artifact_store = build_artifact_store(artifact_base_path)
        self.browser = BrowserRunner(headless=headless, timeout_seconds=timeout_seconds, record_video=record_video)
        self.allowed_domains = allowed_domains
        self.planner = HeuristicPlanner()
        self.worker_actor = worker_actor

    def run(self, task: models.Task) -> dict:
        started = time.monotonic()
        plan = self.planner.plan({
            "title": task.title,
            "instructions": task.instructions,
            "risk_level": task.risk_level,
            "metadata": task.metadata_,
        })
        planner_metadata = build_planner_metadata(
            plan,
            {
                "title": task.title,
                "risk_level": task.risk_level,
                "metadata": task.metadata_,
            },
        )
        resolved_plan = resolve_plan_step_skills(
            planner_metadata["plan"],
            tenant_id=task.tenant_id,
            skillhub=SkillHub(self.session),
        )
        unresolved_skills = [
            step["skill"]["name"]
            for step in resolved_plan
            if not step.get("skill", {}).get("resolved")
        ]
        planner_metadata["plan"] = resolved_plan
        planner_metadata["planner"]["skill_resolution"] = {
            "unresolved": unresolved_skills,
            "unresolved_count": len(unresolved_skills),
        }
        task.metadata_ = {**(task.metadata_ or {}), **planner_metadata}
        if planner_metadata["planner"]["fallback_used"]:
            write_audit(
                self.session,
                task.tenant_id,
                self.worker_actor,
                "task.plan_fallback_used",
                "task",
                str(task.id),
                {
                    "validation_errors": planner_metadata["planner"]["validation_errors"],
                    "correlation_id": task.correlation_id,
                },
            )
        if unresolved_skills:
            write_audit(
                self.session,
                task.tenant_id,
                self.worker_actor,
                "task.skill_resolution",
                "task",
                str(task.id),
                {
                    "resolved": False,
                    "unresolved": unresolved_skills,
                    "correlation_id": task.correlation_id,
                },
            )
        set_task_status_with_audit(
            self.session,
            task,
            "executing",
            action="task.execution_started",
            actor=self.worker_actor,
        )
        task.started_at = datetime.now(timezone.utc)
        self.session.add(task)

        task_steps = []
        for i, step in enumerate(resolved_plan, start=1):
            task_steps.append(add_step(
                self.session,
                task=task,
                step_no=i,
                action_type=step["action"],
                instruction=f"Execute {step['action']}",
                target=step.get("target") or step.get("url"),
                input_data=step,
            ))
        self.session.flush()

        use_session = (task.metadata_ or {}).get("use_session")
        loaded_storage_state = None
        if use_session:
            from sqlalchemy import select
            from .crypto.kms import decrypt_session_vault_payload
            session_artifacts = (
                self.session.execute(
                    select(models.TaskArtifact)
                    .join(models.Task, models.Task.id == models.TaskArtifact.task_id)
                    .where(
                        models.Task.tenant_id == task.tenant_id,
                        models.TaskArtifact.artifact_type == "storage_state",
                    )
                    .order_by(models.TaskArtifact.created_at.desc())
                )
                .scalars()
                .all()
            )
            for sa in session_artifacts:
                meta = sa.metadata_ or {}
                if meta.get("session_name") == use_session:
                    try:
                        c_bytes = self.artifact_store.read_bytes(sa.uri)
                        loaded_storage_state = decrypt_session_vault_payload(
                            c_bytes,
                            meta,
                            tenant_id=str(task.tenant_id),
                        )
                        break
                    except Exception:
                        pass

        from .services.live_telemetry import ExecutionAbortedException

        try:
            result = self.browser.execute(
                {
                    "id": str(task.id),
                    "tenant_id": str(task.tenant_id),
                    "metadata": task.metadata_,
                },
                self.artifact_store,
                self.allowed_domains,
                storage_state=loaded_storage_state,
            )
        except ExecutionAbortedException as abort_exc:
            task.completed_at = datetime.now(timezone.utc)
            set_task_status(self.session, task, "aborted")
            task.metadata_ = {
                **(task.metadata_ or {}),
                "aborted": True,
                "abort_reason": abort_exc.reason,
            }
            self.session.add(task)
            write_audit(
                self.session,
                task.tenant_id,
                self.worker_actor,
                "task.aborted",
                "task",
                str(task.id),
                {"reason": abort_exc.reason, "correlation_id": task.correlation_id},
            )
            return task.metadata_


        observations_by_step = {
            observation.get("step_no"): observation
            for observation in result.observations
        }

        trace_context = (task.metadata_ or {}).get("trace_context") or {}
        trace_id = trace_context.get("trace_id") or task.correlation_id or "0" * 32
        parent_span_id = trace_context.get("span_id")

        artifact_records = []
        for artifact in result.artifacts:
            artifact_metadata = _artifact_metadata(artifact)
            art_record = models.TaskArtifact(
                task_id=task.id,
                artifact_type=artifact["type"],
                uri=artifact["uri"],
                sha256=artifact.get("sha256"),
                metadata_=artifact_metadata,
            )
            self.session.add(art_record)
            artifact_records.append(art_record)
            write_audit(
                self.session,
                task.tenant_id,
                self.worker_actor,
                "task.artifact_written",
                "task",
                str(task.id),
                {
                    "artifact_type": artifact["type"],
                    "uri": artifact["uri"],
                    "sha256": artifact.get("sha256"),
                    "content_type": artifact_metadata.get("content_type"),
                    "size_bytes": artifact_metadata.get("size_bytes"),
                    "backend": artifact_metadata.get("backend"),
                    "redaction": artifact_metadata.get("redaction"),
                    "correlation_id": task.correlation_id,
                },
            )
        self.session.flush()

        screenshot_id = None
        video_id = None
        for art in artifact_records:
            if art.artifact_type == "screenshot" and not screenshot_id:
                screenshot_id = str(art.id)
            elif art.artifact_type == "video" and not video_id:
                video_id = str(art.id)

        from .tracing import generate_span_id, get_trace_buffer, Span
        buffer = get_trace_buffer()

        for step in task_steps:
            observation = dict(observations_by_step.get(step.step_no, {}))
            step_span_id = generate_span_id()
            observation["span_id"] = step_span_id
            observation["duration_ms"] = round((time.monotonic() - started) * 1000 / max(len(task_steps), 1), 1)
            if step.action_type == "screenshot" or (step == task_steps[-1] and screenshot_id):
                observation["screenshot_artifact_id"] = screenshot_id
            elif screenshot_id and not observation.get("screenshot_artifact_id"):
                observation["screenshot_artifact_id"] = screenshot_id

            if result.title:
                observation["dom_summary"] = f"Page title: {result.title} | URL: {result.final_url}"

            step.output_data = observation
            step.status = "failed" if observation.get("error") else "completed"
            step.completed_at = datetime.now(timezone.utc)
            self.session.add(step)

            # 記錄 Step Span 至 TraceBuffer
            buffer.record(Span(
                name=f"browser.step:{step.action_type}",
                trace_id=trace_id,
                span_id=step_span_id,
                parent_span_id=parent_span_id,
                service="browser-agent-worker",
                duration_ms=observation["duration_ms"],
                status="error" if step.status == "failed" else "ok",
                attributes={
                    "task_id": str(task.id),
                    "step_no": step.step_no,
                    "action_type": step.action_type,
                    "target": step.target,
                    "self_healed": bool(observation.get("self_healed")),
                },
            ))

        # 統計自癒事件
        healed_steps = [
            s.output_data.get("self_healing")
            for s in task_steps
            if s.output_data and s.output_data.get("self_healed")
        ]
        if healed_steps:
            write_audit(
                self.session,
                task.tenant_id,
                self.worker_actor,
                "task.self_healed",
                "task",
                str(task.id),
                {
                    "healed_count": len(healed_steps),
                    "healed_steps": healed_steps,
                    "correlation_id": task.correlation_id,
                },
            )

        # V1.4 統計人機協同 (HITL) 介入事件
        from .services.live_telemetry import get_telemetry_broadcaster
        from .services.dlp import get_dlp_service

        broadcaster = get_telemetry_broadcaster()
        interventions = broadcaster.get_interventions(str(task.id))
        if interventions:
            task.human_intervened = True
            write_audit(
                self.session,
                task.tenant_id,
                self.worker_actor,
                "task.human_intervened",
                "task",
                str(task.id),
                {
                    "interventions_count": len(interventions),
                    "interventions": interventions,
                    "correlation_id": task.correlation_id,
                },
            )

        # V1.4 Zero-Trust DLP 防護狀態
        dlp = get_dlp_service()
        dlp_status = dlp.get_status()
        if dlp.enabled and (dlp_status["masked_elements_count"] > 0 or dlp_status["redacted_strings_count"] > 0):
            task.dlp_masked = True

        # V1.4 跨瀏覽器引擎紀錄
        engine = str((task.metadata_ or {}).get("browser_engine") or task.browser_engine or "chromium")
        task.browser_engine = engine

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
            self.worker_actor,
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
            "browser_engine": task.browser_engine,
            "matrix_id": task.matrix_id,
            "human_intervened": task.human_intervened,
            "dlp_masked": task.dlp_masked,
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
            **({"video_artifact_id": video_id} if video_id else {}),
            **({"self_healing": {"healed_count": len(healed_steps), "details": healed_steps}} if healed_steps else {}),
            **({"remote_takeover": {"intervened": True, "interventions": interventions}} if interventions else {}),
            **({"dlp": dlp_status} if dlp.enabled else {}),
        }

        self.session.add(task)
        write_audit(
            self.session,
            task.tenant_id,
            self.worker_actor,
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
    if artifact_type == "video":
        return "video/webm"
    if artifact_type == "storage_state":
        return "application/json"
    return "application/octet-stream"


def _artifact_metadata(artifact: dict) -> dict:
    metadata = dict(artifact.get("metadata") or {})
    content_type = artifact.get("content_type") or metadata.get("content_type") or _artifact_media_type(artifact["type"])
    metadata["content_type"] = content_type
    metadata["media_type"] = content_type
    metadata["size_bytes"] = artifact.get("size_bytes", metadata.get("size_bytes"))
    metadata["backend"] = artifact.get("backend", metadata.get("backend", "local"))
    metadata.setdefault("retention", {"policy": "default", "expires_at": None})
    metadata.setdefault("redaction", {"status": "not_applied", "strategy": "noop"})
    return metadata


def resolve_plan_step_skills(steps: list[dict], *, tenant_id, skillhub: SkillHub) -> list[dict]:
    resolved_steps = []
    for step in steps:
        action = step["action"]
        skill_name = f"browser.{action}"
        requested_version = step.get("skill_version")
        skill = skillhub.resolve(tenant_id, skill_name, requested_version)
        resolved = dict(step)
        if skill:
            resolved["skill"] = {
                "name": skill.name,
                "version": skill.version,
                "entrypoint": skill.entrypoint,
                "resolved": True,
            }
        else:
            resolved["skill"] = {
                "name": skill_name,
                "version": requested_version,
                "entrypoint": f"builtin.browser.{action}",
                "resolved": False,
            }
        resolved_steps.append(resolved)
    return resolved_steps
