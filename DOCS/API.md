# API

Base URL：

```text
http://localhost:8000
```

V1.0 預設啟用 Auth/RBAC。除了 `/healthz`、`/readyz`、`/operations` 與 local dev token endpoint 之外，API 需要：

```text
Authorization: Bearer <JWT>
```

## Auth

### `POST /v1/auth/local-token`

本機開發與 Operations Center 使用的 token endpoint。只有 `AUTH_LOCAL_TOKENS_ENABLED=true` 時啟用。

Request：

```json
{"role": "operator"}
```

可用 role：`creator`、`approver`、`operator`、`admin`。

### `GET /v1/auth/me`

回傳目前 token actor 與 permissions。`AUTH_MODE=local` 使用 HS256 local dev token；`AUTH_MODE=jwks` 使用 `AUTH_JWKS_URL` 驗證 RS256/JWKS token。

## Operations

### `GET /operations`

回傳 `Browser Agent v1.0 Operations Center`。可用來建立 task、核准、查 readiness、Reliability/DLQ、bulk replay、quarantine、metrics、audit、Replay Timeline、Planner/SkillHub、artifact preview/access。

### `GET /v1/ops/readiness`

需要 `operator` 或 `admin`。回傳 app version、auth mode、local token 狀態、DB readiness、reliability store、Kafka config、artifact backend、worker identity、DLQ topic 與 warnings。

## Health 與 Metrics

- `GET /healthz`：公開 health。
- `GET /readyz`：公開 database readiness。
- `GET /metrics`：需要 `operator` 或 `admin`。

## Tasks

### `POST /v1/tasks`

需要 `creator` 或 `admin`。支援 `Idempotency-Key`。同 tenant 同 key 同 payload 回既有 task；同 key 不同 payload 回 `409`。

### `GET /v1/tasks`

需要 authenticated actor。回傳同 tenant recent tasks。

### `GET /v1/tasks/{task_id}`

需要 authenticated actor。只允許讀同 tenant task。

### `POST /v1/tasks/{task_id}/approve`

需要 `approver` 或 `admin`。核准 `pending_approval` task，狀態轉為 `queued`，並發布 `agent.tasks.queued`。

### `GET /v1/tasks/{task_id}/audit`

需要 `approver`、`operator` 或 `admin`。回傳 task audit timeline。

### `GET /v1/tasks/{task_id}/replay`

需要 `approver`、`operator` 或 `admin`。回傳 Replay-lite timeline，包含 audit、steps、artifacts、evaluation。

## Reliability / DLQ

- `GET /v1/reliability`：operator/admin 查 reliability settings。
- `GET /v1/dlq/tasks`：operator/admin 查 failed DLQ tasks。
- `POST /v1/dlq/tasks/{task_id}/replay`：單筆 replay。
- `POST /v1/dlq/tasks/bulk-replay`：批次 replay，body 包含 `task_ids` 與 optional `note`。
- `POST /v1/dlq/tasks/{task_id}/quarantine`：標記 poison task，bulk replay 會跳過 quarantined task。

## Artifacts

### `GET /v1/artifacts/{artifact_id}/content`

需要 authenticated actor。支援 local filesystem 與 `s3://bucket/key` artifact。Access checks：

- artifact 必須存在。
- artifact 所屬 task tenant 必須符合 token tenant。
- local artifact path 必須在 `ARTIFACT_BASE_PATH` 之內。

## Skills

- `POST /v1/skills`：需要 `admin`，註冊同 tenant SkillHub capability。
- `GET /v1/skills`：需要 authenticated actor，列出同 tenant skills。
