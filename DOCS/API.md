# API 說明

Base URL：`http://localhost:8000`

API 由 `src/browser_agent/api.py` 定義，目前沒有 auth middleware。所有任務會使用程式內固定 tenant/user UUID：

- tenant：`00000000-0000-0000-0000-000000000001`
- actor：`00000000-0000-0000-0000-000000000002`

如果資料庫沒有對應 tenant/user seed，建立 task 會因 foreign key 失敗。

## Health

### `GET /healthz`

回傳 process-level health。

```json
{"status":"ok"}
```

### `GET /readyz`

會執行 `select(1)` 檢查資料庫連線。

```json
{"status":"ready"}
```

### `GET /metrics`

回傳 Prometheus exposition format。注意：目前 `metrics.py` 定義的 task counters 尚未在流程中遞增，因此 metrics 主要是 Python process/default metrics。

## Tasks

### `POST /v1/tasks`

建立任務並發布 `agent.tasks.created` Kafka event。

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
  "status": "created",
  "created_at": "2026-05-15T..."
}
```

Policy 行為：

- `risk_level` 為 `high` 或 `critical` 會被標記為 `blocked`。
- `metadata.domains` 只允許出現在 `ALLOWLIST_DOMAINS` 的 domain。
- instructions 包含 `payment`, `transfer`, `wire`, `bank`, `password`, `mfa`, `otp`, `login` 會被阻擋。
- instructions 包含 prompt injection 風險字串會直接回 400。

範例：

```powershell
curl.exe -X POST http://localhost:8000/v1/tasks `
  -H "Content-Type: application/json" `
  -d "{\"title\":\"Collect pricing\",\"instructions\":\"Open the allowlisted site and capture a screenshot.\",\"priority\":5,\"risk_level\":\"medium\",\"metadata\":{\"domains\":[\"example.com\"],\"start_url\":\"https://example.com\",\"expected_domain\":\"example.com\"}}"
```

### `GET /v1/tasks/{task_id}`

讀取任務與 task steps。

Response 欄位：

- `id`, `tenant_id`, `title`, `instructions`
- `status`, `priority`, `risk_level`
- `metadata`
- `created_at`, `updated_at`
- `steps[]`

`steps[]` 由 `TaskRunner` 根據 planner output 建立，目前 step 狀態不會在每一步完成後更新。

### `POST /v1/tasks/{task_id}/approve`

核准任務並發布 `agent.tasks.approved` Kafka event。

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
  "status": "approved"
}
```

注意：`tasks.approved_by` 在 ORM 是 UUID 欄位，但 API 目前把 `approved_by` 字串寫入該欄位；這在 PostgreSQL 上可能導致型別錯誤。`approvals.approved_by` 是 text。建議 roadmap 優先修正。

## Skills

### `POST /v1/skills`

註冊 skill。

Request：

```json
{
  "name": "browser.open_url",
  "version": "1.0.0",
  "description": "Open a URL in the browser runner",
  "skill_type": "browser",
  "entrypoint": "browser_agent.services.browser:BrowserRunner",
  "input_schema": {
    "type": "object",
    "properties": {
      "url": {"type": "string"}
    },
    "required": ["url"]
  },
  "output_schema": {
    "type": "object",
    "properties": {
      "final_url": {"type": "string"}
    }
  },
  "policy_tags": ["network", "browser"]
}
```

Response：

```json
{
  "skill_id": "uuid",
  "name": "browser.open_url",
  "version": "1.0.0",
  "status": "created"
}
```

### `GET /v1/skills`

列出 skill registry。

Response：

```json
[
  {
    "id": "uuid",
    "name": "browser.open_url",
    "version": "1.0.0",
    "description": "Open a URL in the browser runner",
    "skill_type": "browser",
    "entrypoint": "browser_agent.services.browser:BrowserRunner",
    "is_active": true
  }
]
```
