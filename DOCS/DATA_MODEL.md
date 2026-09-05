# Data Model

資料模型以 [src/browser_agent/models.py](../src/browser_agent/models.py) 為準。V1.2 包含 Alembic migration `0003_v12_scheduled_tasks`，新增 `scheduled_tasks` 資料表與 `tasks.scheduled_task_id` 外鍵欄位，並擴充 Session Vault (`storage_state`) 與全行程錄影 (`video`) Artifacts。

## Local Dev Identity

`scripts/bootstrap.py` 會 seed 一組 local dev tenant/users：

| Role | Email | UUID |
|---|---|---|
| admin | `ops@example.com` | `00000000-0000-0000-0000-000000000002` |
| creator | `creator@example.com` | `00000000-0000-0000-0000-000000000003` |
| approver | `approver@example.com` | `00000000-0000-0000-0000-000000000004` |
| operator | `operator@example.com` | `00000000-0000-0000-0000-000000000005` |

Tenant：`00000000-0000-0000-0000-000000000001`。

## Scheduled Tasks Table (`scheduled_tasks`)

V1.2 新增資料表，用於支援定時巡檢任務排程調度：

| 欄位 | 型別 | 描述 |
|---|---|---|
| `id` | UUID (PK) | 排程唯一識別碼 |
| `tenant_id` | UUID (FK) | 所屬租戶 ID |
| `name` | Text | 排程名稱 |
| `cron_expression` | Text | 標準 5 欄位 Cron 表達式（分 時 日 月 週） |
| `concurrency_policy` | Text | 並行原則：`skip`（預設，跳過派發避免重複）或 `allow`（允許並行） |
| `is_active` | Boolean | 排程啟用開關，預設 `True` |
| `task_template` | JSON | 觸發時所建立 Task 之預設定義模板（title, instructions, risk_level 等） |
| `last_run_at` | DateTime (UTC) | 上次觸發派發時間 |
| `next_run_at` | DateTime (UTC) | 預計下次觸發時間 |
| `created_by` | UUID (FK) | 建立者 User ID |
| `created_at` | DateTime (UTC) | 建立時間戳記 |
| `updated_at` | DateTime (UTC) | 最後更新時間戳記 |

`tasks` 表擴充關聯欄位：
- `scheduled_task_id`：UUID (FK -> `scheduled_tasks.id`, nullable=True)。若任務是由排程自動派發或手動立即觸發，此欄位記錄來源排程 ID。

## Task Metadata

`tasks.metadata` 會包含：

- `policy`：policy decision 與 reason。
- `planner`：Planner version、validation、fallback、SkillHub resolution。
- `plan`：browser action plan 與 resolved skill metadata。
- `browser_result`：final URL、title、observations。
- `evaluation`：score、verdict、checks。
- `reliability`：idempotency、DLQ、replay、quarantine metadata。
- `video_artifact_id`：全行程 WebM 錄影視訊 Artifact ID。
- `trace_context`：`{"trace_id": "...", "span_id": "..."}`。

DLQ metadata 範例：

```json
{
  "reliability": {
    "dlq": {
      "status": "pending",
      "topic": "agent.tasks.dlq",
      "worker_id": "worker-local",
      "attempts": 2,
      "error": {"type": "RuntimeError", "message": "browser crashed"}
    },
    "replay": {
      "count": 1,
      "last_replayed_by": "operator@example.com"
    }
  }
}
```

Quarantine 後 `dlq.status` 會變成 `quarantined`，並新增 `dlq.quarantine.reason`、`quarantined_at`、`quarantined_by`。

## Task Steps

Worker 執行後會更新 `task_steps.status` 與 `task_steps.output_data`。`output_data` 記錄視覺化步驟回放資訊：

```json
{
  "duration_ms": 124.5,
  "span_id": "e2a1b3c4d5f67890",
  "screenshot_artifact_id": "00000000-0000-0000-0000-000000000099",
  "dom_summary": "Example Domain (url: https://example.com/)",
  "error": null
}
```

## Artifacts Specification

ArtifactStore 支援多種媒體型別（Media Types）：

1. **Screenshot**：`media_type="screenshot"`，PNG 格式。
2. **HTML DOM Snapshot**：`media_type="html"`，HTML 格式。
3. **WebM Video Recording**：`media_type="video"`，MIME 為 `video/webm`，全行程瀏覽器螢幕視訊。
4. **Session Vault (Storage State)**：`media_type="storage_state"`，MIME 為 `application/json`。內含 Playwright cookies 與 localStorage 狀態。

Session Artifact Metadata 規格：
```json
{
  "session_name": "portal_admin_session",
  "cookies_count": 5,
  "backend": "local",
  "status": "valid"
}
```

S3 artifact metadata 範例：

```json
{
  "backend": "s3",
  "bucket": "browser-agent",
  "key": "2026/05/22/<task-id>/video-abc.webm",
  "content_type": "video/webm",
  "size_bytes": 543210,
  "retention": {"policy": "default", "expires_at": null},
  "redaction": {"status": "not_applied", "strategy": "noop"}
}
```

## Audit Events

常規與維運 events：

- `task.created`
- `task.approved`
- `task.dlq_replayed`
- `task.dlq_quarantined`
- `task.execution_started`
- `task.artifact_written`
- `task.evaluated`
- `task.completed`
- `alert.test_dispatched`（手動測試派發 Webhook 告警紀錄）
- `scheduled_task.created`
- `scheduled_task.updated`
- `scheduled_task.deleted`
- `scheduled_task.triggered`
- `session.revoked`
- `otlp.flushed`
