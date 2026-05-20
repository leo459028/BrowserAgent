# API

Base URL：`http://localhost:8000`

目前 API 使用固定 demo identity values，尚未實作正式 auth/RBAC。

- tenant：`00000000-0000-0000-0000-000000000001`
- actor：`00000000-0000-0000-0000-000000000002`
- approver label：`ops@example.com`

## Dashboard

### `GET /demo`

提供本機 v0.3 Dashboard，可用來：

- 建立 normal artifact、redaction metadata、high-risk、sensitive instruction、blocked-domain tasks；
- approve `pending_approval` tasks；
- 顯示 task status、policy reason、metrics、audit timeline、steps、evaluation、artifacts；
- 檢視 artifact governance fields：content type、size、SHA、backend、retention、redaction status；
- preview screenshot artifacts、開啟 HTML artifacts、測試 governed artifact access。

## Health 與 Metrics

### `GET /healthz`

回傳 process-level health。

```json
{"status": "ok"}
```

### `GET /readyz`

執行 database `select(1)` readiness check。

```json
{"status": "ready"}
```

### `GET /metrics`

回傳目前 process 的 Prometheus exposition text。Metrics 包含：

- `browser_agent_tasks_created_total`
- `browser_agent_tasks_executed_total`
- `browser_agent_tasks_failed_total`
- `browser_agent_task_duration_seconds`

在 Docker Compose 中，API 與 worker 是不同 process。API `/metrics` 不會聚合 worker process metrics。

## Tasks

### `POST /v1/tasks`

建立 task、執行 instruction/policy checks、記錄 audit，並 publish `agent.tasks.created`。

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
  "created_at": "2026-05-20T..."
}
```

Policy behavior：

- allowlisted low/medium tasks 進入 `pending_approval`；
- high/critical risk tasks 進入 `pending_approval`；
- sensitive instructions，例如 `login`、`password`、`payment`、`transfer`，進入 `pending_approval`；
- non-allowlisted domains 進入 `blocked`；
- 類 prompt-injection instructions 會以 `400` 拒絕。

### `GET /v1/tasks`

回傳 recent task summaries，供 Dashboard 使用。

Query：

- `limit`：optional，預設 `20`，限制在 `1..100`

### `GET /v1/tasks/{task_id}`

回傳 task detail，包含：

- task identifiers、title、instructions、status、priority、risk、correlation ID；
- task metadata，包含 policy、plan、browser result、evaluation、error metadata；
- `steps[]`；
- `artifacts[]`。

Artifact summaries 包含 v0.3 governance fields：

```json
{
  "id": "uuid",
  "artifact_type": "screenshot",
  "uri": "/data/artifacts/2026/05/20/task/screenshot-sha.png",
  "sha256": "hex",
  "content_type": "image/png",
  "size_bytes": 18002,
  "backend": "local",
  "retention": {"policy": "default", "expires_at": null},
  "redaction": {"status": "not_applied", "strategy": "noop"},
  "redaction_status": "not_applied",
  "metadata": {},
  "created_at": "2026-05-20T...",
  "download_url": "/v1/artifacts/{artifact_id}/content"
}
```

### `GET /v1/tasks/{task_id}/audit`

回傳 task audit timeline。成功且已 approval 的 task 預期 lifecycle：

```text
task.created -> task.pending_approval -> task.approved -> task.queued ->
task.execution_started -> task.artifact_written -> task.artifact_written ->
task.evaluated -> task.completed
```

### `POST /v1/tasks/{task_id}/approve`

Approve `pending_approval` task，將其移到 `queued`，並 publish `agent.tasks.queued`。

Request：

```json
{
  "approved_by": "ops@example.com",
  "note": "Approved for local test"
}
```

Response：

```json
{
  "task_id": "uuid",
  "approval_id": "uuid",
  "status": "queued",
  "correlation_id": "uuid-or-client-provided-id"
}
```

`blocked`、`completed`、`failed` 等不可 approval 的 statuses 會回傳 `409`。

## Artifacts

### `GET /v1/artifacts/{artifact_id}/content`

回傳 screenshot 或 HTML artifact content。

Access checks：

- artifact 必須存在；
- artifact 所屬 task tenant 必須符合目前 demo tenant；
- local artifact path 必須 resolve 在 `ARTIFACT_BASE_PATH` 底下；
- missing files 回傳 `404`；
- tenant mismatch 或 path traversal 回傳 `403`。

Response 使用 artifact metadata 中的 content type，例如 `image/png` 或 `text/html; charset=utf-8`，並以 inline 方式回傳。

## Skills

### `POST /v1/skills`

替 demo tenant 註冊 skill。

### `GET /v1/skills`

列出已註冊 skills。
