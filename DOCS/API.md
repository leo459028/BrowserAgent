# API

Base URL：

```text
http://localhost:8000
```

v0.6 預設啟用 Auth/RBAC。除了 `/healthz`、`/readyz`、`/demo` 與 local demo token endpoint 之外，API 需要：

```text
Authorization: Bearer <JWT>
```

JWT 是本機簽發的 OIDC-compatible token，claims 包含 `iss`、`aud`、`sub`、`tenant_id`、`email`、`roles`、`exp`。

## Auth

### `POST /v1/auth/demo-token`

本機測試用 token endpoint。只有 `AUTH_DEMO_TOKENS_ENABLED=true` 時啟用。

Request：

```json
{"role": "creator"}
```

可用 role：

- `creator`
- `approver`
- `operator`
- `admin`

Response：

```json
{
  "access_token": "jwt",
  "token_type": "bearer",
  "expires_in": 3600,
  "actor": {
    "user_id": "uuid",
    "tenant_id": "00000000-0000-0000-0000-000000000001",
    "email": "creator@example.com",
    "roles": ["creator"],
    "permissions": ["artifact:read", "skill:read", "task:create", "task:read"]
  }
}
```

### `GET /v1/auth/me`

回傳目前 token actor 與 permission summary。

## Dashboard

### `GET /demo`

回傳 `Browser Agent v0.6 Dashboard`。Dashboard 可用來：

- 查詢 Reliability / DLQ 狀態，包含 store、rate limit、worker identity、DLQ topic。
- 執行 Idempotency smoke test。
- 查詢 DLQ failed tasks，並用 operator token replay。
- 切換 creator、approver、operator、admin demo roles。
- 用 creator/admin 建立 task。
- 用 approver/admin 核准 `pending_approval` task。
- 用 operator/admin 查詢 metrics、task、audit、artifact。
- 測試 operator 建立 task 時的 `403` forbidden scenario。
- 查詢 Planner validation、SkillHub resolution、steps、evaluation、artifacts。

`/demo` 仍是本機測試 Dashboard，不是 production operator UI。

## Health 與 Metrics

### `GET /healthz`

公開 endpoint。

```json
{"status": "ok"}
```

### `GET /readyz`

公開 endpoint，執行 database `select(1)` readiness check。

```json
{"status": "ready"}
```

### `GET /metrics`

需要 `operator` 或 `admin` token。回傳 Prometheus exposition text。

主要 metrics：

- `browser_agent_tasks_created_total`
- `browser_agent_tasks_executed_total`
- `browser_agent_tasks_failed_total`
- `browser_agent_tasks_dlq_total`
- `browser_agent_task_duration_seconds`

注意：目前 metrics 為 process-local；API `/metrics` 不會包含 worker process counters。

## Tasks

### `POST /v1/tasks`

需要 `creator` 或 `admin`。建立 task、執行 instruction/policy checks、寫入 audit，並發布 `agent.tasks.created`。

可選 header：

```text
Idempotency-Key: capture-example-001
```

同一個 tenant 使用相同 `Idempotency-Key` 與相同 request payload 時，API 會回傳既有 task，不會重複建立 task 或重複發布 `agent.tasks.created`。同 key 但 payload 不同會回 `409`。task create 也會套用 per tenant/user rate limit；超過時回 `429`。

Request：

```json
{
  "title": "Collect pricing",
  "instructions": "Open the allowlisted site and capture a screenshot.",
  "priority": 5,
  "risk_level": "medium",
  "metadata": {
    "domains": ["example.com"],
    "start_url": "https://example.com",
    "expected_domain": "example.com"
  }
}
```

Response：

```json
{
  "task_id": "uuid",
  "status": "pending_approval",
  "correlation_id": "uuid-or-client-provided-id",
  "created_at": "2026-05-22T...",
  "idempotency": {
    "key": "capture-example-001",
    "replayed": false
  }
}
```

Behavior：

- task 的 `tenant_id` 與 `created_by` 來自 token actor。
- 若使用 `Idempotency-Key`，`tasks.idempotency_key` 與 `tasks.metadata.reliability.request_hash` 會保存去重資訊。
- allowlisted low/medium task 仍進入 `pending_approval`，由人核准後才 queued。
- high/critical risk task 進入 `pending_approval`。
- 敏感指令，例如 `login`、`password`、`payment`、`transfer`，進入 `pending_approval`。
- non-allowlisted domain task 進入 `blocked`。
- prompt-injection 指令回傳 `400`。

### `GET /v1/tasks`

需要 authenticated actor。回傳同 tenant recent task summaries。

Query：

- `limit`：optional，預設 `20`，範圍 `1..100`。

### `GET /v1/tasks/{task_id}`

需要 authenticated actor。只允許讀同 tenant task；tenant mismatch 以 `404 task not found` 處理。

回傳 task detail，包含 identifiers、status、metadata、steps、artifacts。

### `GET /v1/tasks/{task_id}/audit`

需要 `approver`、`operator` 或 `admin`。回傳同 tenant task audit timeline。

典型順序：

```text
task.created -> task.pending_approval -> task.approved -> task.queued ->
task.execution_started -> task.artifact_written -> task.evaluated -> task.completed
```

v0.5 以後 approval audit payload 會包含：

```json
{
  "actor_user_id": "uuid",
  "actor_email": "approver@example.com",
  "actor_roles": ["approver"],
  "correlation_id": "cid"
}
```

### `POST /v1/tasks/{task_id}/approve`

需要 `approver` 或 `admin`。核准 `pending_approval` task，狀態轉為 `queued`，並發布 `agent.tasks.queued`。

Request：

```json
{"note": "Approved from v0.6 local smoke test"}
```

`approved_by` request 欄位保留相容但不再被信任；實際 approval actor 一律使用 token actor。

Response：

```json
{
  "task_id": "uuid",
  "approval_id": "uuid",
  "status": "queued",
  "correlation_id": "uuid-or-client-provided-id"
}
```

`blocked`、`completed`、`failed` 等不可核准狀態會回傳 `409`。

## Reliability / DLQ

### `GET /v1/reliability`

需要 `operator` 或 `admin`。回傳目前 reliability store 與 V0.6 reliability 設定摘要。

```json
{
  "store": {"backend": "redis", "available": true},
  "worker_service_id": "worker-local",
  "task_create_rate_limit_per_minute": 60,
  "idempotency_ttl_seconds": 86400,
  "task_lock_ttl_seconds": 300,
  "max_task_retries": 2,
  "dlq_topic": "agent.tasks.dlq"
}
```

### `GET /v1/dlq/tasks`

需要 `operator` 或 `admin`。列出同 tenant、狀態為 `failed` 且有 `tasks.metadata.reliability.dlq` 的 tasks。

### `POST /v1/dlq/tasks/{task_id}/replay`

需要 `operator` 或 `admin`。只允許 replay 同 tenant 且已有 DLQ metadata 的 failed task。成功後 task 會回到 `queued`，寫入 `task.dlq_replayed` audit，並發布 `agent.tasks.queued`。

## Artifacts

### `GET /v1/artifacts/{artifact_id}/content`

需要 authenticated actor。Access checks：

- artifact 必須存在。
- artifact 所屬 task tenant 必須符合 token tenant。
- local artifact path 必須 resolve 在 `ARTIFACT_BASE_PATH` 之內。
- missing file 回傳 `404`。
- tenant mismatch 或 path traversal 回傳 `403`。

Response 依 artifact metadata 設定 content type，例如 `image/png` 或 `text/html; charset=utf-8`。

## Skills

### `POST /v1/skills`

需要 `admin`。註冊同 tenant demo SkillHub capability。

### `GET /v1/skills`

需要 authenticated actor。列出同 tenant 已註冊 skills，包含 `is_active` 欄位。Runner 仍使用 `SkillHub.resolve()` 查詢 active 的 `browser.<action>` capability。
