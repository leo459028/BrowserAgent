# Implementation Status

最後更新：2026-05-22

## 摘要

Repository 目前已完成 **v0.6 Reliability Foundation** implementation slice。這仍是 production-grade scaffold，不是完整 production product；尚未接入外部 OIDC/JWKS、Kubernetes、production artifact object storage、production operator UI、secrets vault 或 distributed tracing。

## 已完成 Components

- FastAPI app factory 與 router。
- `/healthz`、`/readyz`。
- Auth endpoints：`POST /v1/auth/demo-token`、`GET /v1/auth/me`。
- Local JWT auth：HS256、issuer/audience/expiry validation。
- RBAC roles：creator、approver、operator、admin。
- Request-scoped tenant/user context。
- `/metrics` 需 operator/admin。
- Reliability store abstraction：host 預設 memory，Docker 使用 Redis。
- `POST /v1/tasks` 支援 `Idempotency-Key`、request hash conflict check 與 task create rate limiting。
- `GET /v1/reliability` 需 operator/admin。
- `GET /v1/dlq/tasks` 與 `POST /v1/dlq/tasks/{task_id}/replay` 需 operator/admin。
- `POST /v1/tasks` 需 creator/admin，並使用 token actor 寫入 `created_by`。
- `GET /v1/tasks`、`GET /v1/tasks/{task_id}` 依 token tenant 查詢。
- `GET /v1/tasks/{task_id}/audit` 需 approver/operator/admin。
- `POST /v1/tasks/{task_id}/approve` 需 approver/admin，approval actor 來自 token。
- `GET /v1/artifacts/{artifact_id}/content` 依 token tenant 做 access check。
- `POST /v1/skills` 需 admin；`GET /v1/skills` 需 authenticated actor。
- SQLAlchemy ORM models 與 Alembic initial migration skeleton。
- Kafka producer/consumer wrapper。
- Worker consumer loop 與 Playwright browser runner。
- Worker service identity、task lock、config-driven retries/timeouts。
- Final failure DLQ metadata、`agent.tasks.dlq` event 與 replay flow。
- GitHub Actions CI workflow：`pytest -q`、`compileall`、`git diff --check`。
- Heuristic Planner `heuristic-v0.4`、schema validation、deterministic fallback。
- SkillHub registration 與 resolver metadata integration。
- Evaluator。
- Local artifact store、governance metadata、no-op redaction hook。
- JSON logging。
- Docker Compose local stack。
- `/demo` v0.6 Dashboard：Reliability/DLQ、Identity/RBAC、production approval、Planner/SkillHub、audit、metrics、artifact governance。
- Bootstrap script：schema、demo tenant/users、Kafka topics。
- API 支援 `X-Correlation-ID`。

## v0.5 Auth/RBAC

Demo users：

- `ops@example.com`：admin。
- `creator@example.com`：creator。
- `approver@example.com`：approver。
- `operator@example.com`：operator。

JWT claims：

```json
{
  "iss": "browser-agent-local",
  "aud": "browser-agent-api",
  "sub": "user-uuid",
  "tenant_id": "tenant-uuid",
  "email": "approver@example.com",
  "roles": ["approver"],
  "exp": 1770000000
}
```

## Production Approval

Approval API 不再信任 request body 的 `approved_by`。成功 approval 會：

- 設定 `tasks.approved_by` 為 token user UUID。
- 建立 `approvals` row，`approved_by` 為 token email。
- 寫入 `task.approved` 與 `task.queued` audit。
- 在 audit payload 與 Kafka event 中保存 `actor_user_id`、`actor_email`、`actor_roles`。

## v0.6 Reliability Foundation

已完成：

- `src/browser_agent/reliability.py`：memory/Redis-backed rate limit 與 task lock。
- `tasks.idempotency_key` 實作 task create 去重；同 tenant 同 key 同 payload replay，payload 不同回 `409`。
- `idx_tasks_tenant_idempotency_key` partial unique index。
- task create rate limit；超過回 `429`。
- worker audit actor 使用 `service:<WORKER_SERVICE_ID>`。
- worker 使用 reliability lock 避免同 task 重複執行。
- worker final failure 寫入 `tasks.metadata.reliability.dlq`，發布 `agent.tasks.dlq`，並增加 `browser_agent_tasks_dlq_total` metric。
- operator/admin 可查 DLQ tasks 並 replay 回 `queued`。

## Dashboard

`GET /demo` 顯示 `Browser Agent v0.6 Dashboard`，可執行：

- Reliability / DLQ 狀態查詢。
- Idempotency smoke test。
- DLQ failed task 查詢與 replay。
- role selector 與 `/v1/auth/me` identity check。
- operator forbidden create smoke test。
- normal planner task。
- fallback planner task。
- SkillHub resolved task。
- SkillHub missing task。
- redaction metadata task。
- high-risk、sensitive instruction、blocked-domain cases。
- approval、runtime health、metrics、audit timeline、steps、evaluation、artifact preview、Artifact Query。

## 尚未完成

- 外部 OIDC/JWKS。
- 外部 LLM provider integration。
- 第三方 SkillHub tool execution。
- Per-action confirmation。
- Worker autoscaling。
- MinIO/S3 active artifact backend。
- Browser session replay UI。
- Kubernetes manifests。
- CI pipeline。
- Production secret management。
- Distributed tracing。
