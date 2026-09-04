# API

Base URL：

```text
http://localhost:8000
```

V1.1 預設啟用 Auth/RBAC。除了 `/healthz`、`/readyz`、`/operations` 與 local dev token endpoint 之外，API 需要：

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

回傳目前 token actor 與 permissions。`AUTH_MODE=local` 使用 HS256 local dev token；`AUTH_MODE=jwks` 使用 `AUTH_JWKS_URL` 驗證 RS256/JWKS token。若沒有設定 `AUTH_JWKS_URL`，但有 `AUTH_OIDC_ISSUER_URL`，V1.1 會讀取 OIDC discovery 的 `jwks_uri`。

## Operations

### `GET /operations`

回傳 `Browser Agent v1.1 Operations Center`。可用來建立 task、核准、查 Operations Readiness、Production Readiness、Observability、Production Alerting、Trace Inspector、Visual Step Replay、Reliability/DLQ、bulk replay、quarantine、metrics、audit、Planner/SkillHub、artifact preview/access。

系統支援自動容錯重定向：
- `GET /` ➜ 307 臨時重定向至 `/operations`
- `GET /operation` ➜ 307 臨時重定向至 `/operations`

### `GET /v1/ops/readiness`

需要 `operator` 或 `admin`。回傳 app version、auth mode、local token 狀態、DB readiness、reliability store、Kafka config、artifact backend、worker identity、DLQ topic、Production Readiness、Observability 與 warnings。

V1.1 新增欄位：

- `production.status`：`ready`、`degraded` 或 `not_ready`。
- `production.checks`：檢查 production local token、secret key、JWKS/OIDC、Redis reliability、Kafka、S3 artifact backend。
- `observability.otel_ready`：表示目前 log/request schema 已預留 OTEL 欄位。
- `observability.log_schema_fields`：列出固定 log correlation 欄位。

Production hard failure 會讓整體 `status` 回 `not_ready`。

### `GET /v1/ops/alerts`

需要 `operator` 或 `admin`。即時評估維運系統的 7 大規則，回傳系統整體健康指標與觸發之告警清單：
- `evaluation_time`：評估時間（ISO 8601）。
- `summary`：`{"critical": int, "warning": int, "info": int, "healthy": bool}`。
- `metrics_snapshot`：包含 failure rate、DLQ backlog、pending approval 數量、Worker 心跳、DB 延遲等即時數值。
- `alerts`：觸發之告警項目（含 rule_id、severity、message、metric_name、metric_value、threshold、recommendation）。
- `webhook_enabled`：外部 Webhook（Slack/Discord）是否已設定。

### `POST /v1/ops/alerts/test-dispatch`

需要 `admin`。手動測試外部 Webhook 轉發通道，發送測試告警至 Slack/Discord 或外部 Webhook URL，並記錄 Audit log。
Request body：
```json
{
  "rule_id": "test_alert",
  "severity": "info",
  "message": "Manual test notification from operations center"
}
```

### `GET /v1/ops/traces/{trace_id}`

需要 `operator` 或 `admin`。檢視指定 `trace_id` 的端到端分散式追蹤圖。聚合 API 與 Worker 記憶體中的 TraceBuffer 與資料庫儲存的 Task Steps，回傳：
- `trace_id`：32-char hex trace identifier。
- `span_count`：關聯之 Span 總數。
- `root_service`：進入點服務。
- `spans`：階層式 Spans 列表（包含 span_id、parent_span_id、name、service_name、start_time、end_time、duration_ms、status、attributes、events）。

## Health 與 Metrics

- `GET /healthz`：公開 health。
- `GET /readyz`：公開 database readiness。
- `GET /metrics`：需要 `operator` 或 `admin`。

V1.1 每個 response 會回寫 `X-Correlation-ID`。若 request 帶入 `X-Correlation-ID`，會沿用；未帶入時由 API 產生。API 也會解析 W3C `traceparent`，在 API 與 Worker 間傳遞分佈式追蹤 Context。

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

需要 `approver`、`operator` 或 `admin`。回傳可視化步驟回放（Visual Step Replay）與 Replay Timeline，100% 向後相容：
- `task_id`：任務 ID。
- `trace_id`：此任務綁定之分散式追蹤 Trace ID。
- `steps_visual`：V1.1 新增之步驟視覺化列表，包含 `step_index`、`step_type`、`status`、`duration_ms`、`span_id`、`screenshot_artifact_id`、`dom_summary`。
- `evaluation_summary`：步驟執行摘要評估。
- `timeline`：由 audit、steps、artifacts 組成之向後相容事件時間線。

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
