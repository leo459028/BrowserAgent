# API 說明

Base URL：`http://localhost:8000`

API 由 `src/browser_agent/api.py` 定義，目前沒有 auth middleware。所有任務會使用程式內固定 tenant/user UUID：

- tenant：`00000000-0000-0000-0000-000000000001`
- actor：`00000000-0000-0000-0000-000000000002`

如果資料庫沒有對應 tenant/user seed，建立 task 會因 foreign key 失敗。

## Health

## Demo UI

### `GET /demo`

本機 v0.1 demo console。頁面內建 `https://example.com` allowlisted task payload，可一鍵建立任務、核准任務、輪詢狀態，並顯示 evaluation、steps、screenshot preview 與 HTML artifact 連結。

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

`artifacts[]` 會回傳已寫入 `task_artifacts` 的 artifact 摘要，包含：

- `id`
- `artifact_type`
- `uri`
- `sha256`
- `metadata`
- `created_at`
- `download_url`

### `GET /v1/artifacts/{artifact_id}/content`

讀取 screenshot 或 HTML artifact。API 只允許讀取 `ARTIFACT_BASE_PATH` 底下的檔案；若 artifact URI 指向 base path 外部，會回 403。

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

注意：v0.1 demo 仍未實作正式登入。API 會把 `tasks.approved_by` 寫成固定 demo user UUID，並把 request 內的 `approved_by` 字串保存在 `approvals.approved_by` 作為顯示與稽核用 label。

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
