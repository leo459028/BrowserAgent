# Implementation Status

最後更新：2026-05-21

## 摘要

Repository 目前已完成 **v0.5 Auth/RBAC 與 Production Approval** implementation slice。這仍是 production-grade scaffold，不是完整 production product；尚未接入外部 OIDC/JWKS、Kubernetes、DLQ、production artifact object storage 或 production operator UI。

## 已完成 Components

- FastAPI app factory 與 router。
- `/healthz`、`/readyz`。
- Auth endpoints：`POST /v1/auth/demo-token`、`GET /v1/auth/me`。
- Local JWT auth：HS256、issuer/audience/expiry validation。
- RBAC roles：creator、approver、operator、admin。
- Request-scoped tenant/user context。
- `/metrics` 需 operator/admin。
- `POST /v1/tasks` 需 creator/admin，並使用 token actor 寫入 `created_by`。
- `GET /v1/tasks`、`GET /v1/tasks/{task_id}` 依 token tenant 查詢。
- `GET /v1/tasks/{task_id}/audit` 需 approver/operator/admin。
- `POST /v1/tasks/{task_id}/approve` 需 approver/admin，approval actor 來自 token。
- `GET /v1/artifacts/{artifact_id}/content` 依 token tenant 做 access check。
- `POST /v1/skills` 需 admin；`GET /v1/skills` 需 authenticated actor。
- SQLAlchemy ORM models 與 Alembic initial migration skeleton。
- Kafka producer/consumer wrapper。
- Worker consumer loop 與 Playwright browser runner。
- Heuristic Planner `heuristic-v0.4`、schema validation、deterministic fallback。
- SkillHub registration 與 resolver metadata integration。
- Evaluator。
- Local artifact store、governance metadata、no-op redaction hook。
- JSON logging。
- Docker Compose local stack。
- `/demo` v0.5 Dashboard：Identity/RBAC、production approval、Planner/SkillHub、audit、metrics、artifact governance。
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

## Dashboard

`GET /demo` 顯示 `Browser Agent v0.5 Dashboard`，可執行：

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
- Worker service identity。
- 外部 LLM provider integration。
- 第三方 SkillHub tool execution。
- Per-action confirmation。
- Redis locks、rate limiting、dedupe。
- DLQ 與 poison message replay tooling。
- Worker autoscaling。
- MinIO/S3 active artifact backend。
- Browser session replay UI。
- Kubernetes manifests。
- CI pipeline。
- Production secret management。
- Distributed tracing。
