# API

Base URL：

```text
http://localhost:8000
```

目前 API 使用固定 demo identity，正式 auth/RBAC 尚未實作：

- tenant：`00000000-0000-0000-0000-000000000001`
- actor：`00000000-0000-0000-0000-000000000002`
- approver label：`ops@example.com`

## Dashboard

### `GET /demo`

回傳 `Browser Agent v0.4 Dashboard`。Dashboard 可用來：

- 建立 normal planner、fallback planner、SkillHub resolved、SkillHub missing 測試 task。
- 註冊 demo SkillHub skills。
- 核准 `pending_approval` task。
- 查詢 task status、policy reason、Planner validation、SkillHub resolution。
- 查詢 metrics、audit timeline、steps、evaluation、artifacts。
- 預覽 screenshot artifact、開啟 HTML artifact、測試 governed artifact access。

## Health 與 Metrics

### `GET /healthz`

```json
{"status": "ok"}
```

### `GET /readyz`

執行 database `select(1)` readiness check。

```json
{"status": "ready"}
```

### `GET /metrics`

回傳 Prometheus exposition text。主要 metrics：

- `browser_agent_tasks_created_total`
- `browser_agent_tasks_executed_total`
- `browser_agent_tasks_failed_total`
- `browser_agent_task_duration_seconds`

注意：目前 metrics 為 process-local；API `/metrics` 不會包含 worker process 的 counters。

## Tasks

### `POST /v1/tasks`

建立 task、執行 instruction/policy checks、寫入 audit，並發布 `agent.tasks.created`。

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
  "created_at": "2026-05-21T..."
}
```

Policy behavior：

- allowlisted low/medium task 進入 `pending_approval`。
- high/critical risk task 進入 `pending_approval`。
- 敏感指令，例如 `login`、`password`、`payment`、`transfer`，進入 `pending_approval`。
- non-allowlisted domain task 進入 `blocked`。
- prompt-injection 指令回傳 `400`。

### `GET /v1/tasks`

回傳 recent task summaries，供 Dashboard 使用。

Query：

- `limit`：optional，預設 `20`，範圍 `1..100`。

### `GET /v1/tasks/{task_id}`

回傳 task detail，包含：

- task identifiers、title、instructions、status、priority、risk_level、correlation_id。
- `metadata.policy`。
- `metadata.planner`。
- `metadata.plan`。
- `metadata.browser_result`。
- `metadata.evaluation`。
- `steps[]`。
- `artifacts[]`。

v0.4 Planner metadata 範例：

```json
{
  "planner": {
    "version": "heuristic-v0.4",
    "valid": true,
    "source": "heuristic",
    "validation_errors": [],
    "fallback_used": false,
    "fallback_source": null,
    "skill_resolution": {
      "unresolved": ["browser.goto", "browser.screenshot"],
      "unresolved_count": 2
    }
  },
  "plan": [
    {
      "action": "goto",
      "url": "https://example.com",
      "skill": {
        "name": "browser.goto",
        "version": null,
        "entrypoint": "builtin.browser.goto",
        "resolved": false
      }
    }
  ]
}
```

`steps[].input_data.skill` 會保存同一份 resolution 摘要，方便從 task steps 查詢實際採用的 capability。

Artifact summary 範例：

```json
{
  "id": "uuid",
  "artifact_type": "screenshot",
  "uri": "/data/artifacts/2026/05/21/task/screenshot-sha.png",
  "sha256": "hex",
  "content_type": "image/png",
  "size_bytes": 18002,
  "backend": "local",
  "retention": {"policy": "default", "expires_at": null},
  "redaction": {"status": "not_applied", "strategy": "noop"},
  "redaction_status": "not_applied",
  "metadata": {},
  "created_at": "2026-05-21T...",
  "download_url": "/v1/artifacts/{artifact_id}/content"
}
```

### `GET /v1/tasks/{task_id}/audit`

回傳 task audit timeline。典型順序：

```text
task.created -> task.pending_approval -> task.approved -> task.queued ->
task.execution_started -> task.artifact_written -> task.artifact_written ->
task.evaluated -> task.completed
```

v0.4 可能新增：

- `task.plan_fallback_used`
- `task.skill_resolution`

### `POST /v1/tasks/{task_id}/approve`

核准 `pending_approval` task，狀態轉為 `queued`，並發布 `agent.tasks.queued`。

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

`blocked`、`completed`、`failed` 等不可核准狀態會回傳 `409`。

## Artifacts

### `GET /v1/artifacts/{artifact_id}/content`

回傳 screenshot 或 HTML artifact content。

Access checks：

- artifact 必須存在。
- artifact 所屬 task tenant 必須符合 demo tenant。
- local artifact path 必須 resolve 在 `ARTIFACT_BASE_PATH` 之內。
- missing file 回傳 `404`。
- tenant mismatch 或 path traversal 回傳 `403`。

Response 依 artifact metadata 設定 content type，例如 `image/png` 或 `text/html; charset=utf-8`。

## Skills

### `POST /v1/skills`

註冊 demo tenant skill。

Request：

```json
{
  "name": "browser.goto",
  "version": "1.0.0",
  "description": "Built-in browser goto action",
  "skill_type": "browser_action",
  "entrypoint": "browser.goto",
  "input_schema": {"type": "object", "required": ["url"]},
  "output_schema": {"type": "object"},
  "policy_tags": ["browser", "navigation"]
}
```

### `GET /v1/skills`

列出已註冊 skills，包含 `is_active` 欄位。v0.4 runner 會用 `SkillHub.resolve()` 查詢 active 的 `browser.<action>` capability。
