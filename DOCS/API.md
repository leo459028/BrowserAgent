# API

Base URL: `http://localhost:8000`

目前 v0.2 仍使用 demo tenant/user，尚未接正式 auth middleware。

- tenant: `00000000-0000-0000-0000-000000000001`
- actor: `00000000-0000-0000-0000-000000000002`
- approver label: `ops@example.com`

## Dashboard

### `GET /demo`

開啟本機 v0.2 Dashboard。Dashboard 可用來建立不同任務情境、核准
`pending_approval` 任務、觀察 lifecycle status、查看 metrics、audit timeline、
steps、evaluation、screenshot 與 HTML artifact。

內建情境包含：

- allowlisted low-risk task
- high-risk task
- sensitive instruction task
- blocked-domain task

## Health 與 Metrics

### `GET /healthz`

回傳 process-level health。

```json
{"status":"ok"}
```

### `GET /readyz`

執行 `select(1)` 檢查資料庫連線。

```json
{"status":"ready"}
```

### `GET /metrics`

回傳 API process 的 Prometheus exposition format。v0.2 核心流程已接上：

- `browser_agent_tasks_created_total`
- `browser_agent_tasks_executed_total`
- `browser_agent_tasks_failed_total`
- `browser_agent_task_duration_seconds`

注意：在 Docker Compose 中 API 與 Worker 是不同 process，API 的 `/metrics` 不會自動匯總 Worker process 裡的 executed/failed/duration metrics。

## Tasks

### `POST /v1/tasks`

建立任務並發布 `agent.tasks.created` Kafka event。可傳入 `X-Correlation-ID`
header；若未提供，API 會產生 UUID 並寫入 task、event 與 audit payload。

Request:

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

Response:

```json
{
  "task_id": "uuid",
  "status": "pending_approval",
  "correlation_id": "uuid-or-client-provided-id",
  "created_at": "2026-05-15T..."
}
```

Policy 行為：

- allowlisted low/medium task 會進入 `pending_approval`。
- `risk_level=high|critical` 會進入 `pending_approval`，並在 metadata/audit 記錄 policy reason。
- instructions 包含 `payment`, `transfer`, `wire`, `bank`, `password`, `mfa`, `otp`, `login` 會進入 `pending_approval`，並記錄 sensitive action reason。
- 非 allowlist domain 會進入 `blocked`。
- prompt injection 類 instruction 會被 request validation 擋下並回 400。

### `GET /v1/tasks`

回傳最近任務摘要，供 Dashboard 顯示任務列表。

Query:

- `limit`: optional，預設 `20`，範圍 `1..100`

Response:

```json
[
  {
    "id": "uuid",
    "title": "High risk review",
    "status": "pending_approval",
    "correlation_id": "cid-list",
    "priority": 3,
    "risk_level": "high",
    "policy": {
      "decision": "requires_approval",
      "reason": "high-risk task requires manual approval",
      "requires_approval": true
    },
    "created_at": "2026-05-15T...",
    "updated_at": "2026-05-15T..."
  }
]
```

### `GET /v1/tasks/{task_id}`

讀取單一 task 詳情，包含 metadata、steps 與 artifacts。

Response 主要欄位：

- `id`, `tenant_id`, `title`, `instructions`
- `status`, `correlation_id`, `priority`, `risk_level`
- `metadata`
- `created_at`, `updated_at`
- `steps[]`
- `artifacts[]`

### `GET /v1/tasks/{task_id}/audit`

回傳單一 task 的 audit timeline，供 Dashboard 顯示 lifecycle events。

Response:

```json
[
  {
    "id": "uuid",
    "actor": "ops@example.com",
    "action": "task.pending_approval",
    "payload": {
      "reason": "high-risk task requires manual approval"
    },
    "created_at": "2026-05-15T..."
  }
]
```

### `POST /v1/tasks/{task_id}/approve`

核准 `pending_approval` 或舊資料中的 `created` 任務。成功後狀態改為
`queued`，並發布 `agent.tasks.queued` Kafka event。若 task 已經
`blocked/completed/failed`，會回 409。

Request:

```json
{
  "approved_by": "ops@example.com",
  "note": "Approved for local test"
}
```

Response:

```json
{
  "task_id": "uuid",
  "approval_id": "uuid",
  "status": "queued",
  "correlation_id": "uuid-or-client-provided-id"
}
```

### `GET /v1/artifacts/{artifact_id}/content`

讀取 screenshot 或 HTML artifact。API 會確認 artifact path 位於
`ARTIFACT_BASE_PATH` 內；若不在 base path 內會回 403。

## Skills

### `POST /v1/skills`

註冊 skill。

### `GET /v1/skills`

列出已註冊 skill。
