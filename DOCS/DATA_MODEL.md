# Data Model

資料模型以 [src/browser_agent/models.py](../src/browser_agent/models.py) 為準。V1.1 不新增資料表或 migration，沿用 `tasks.metadata`、`audit_logs`、`task_steps`、`task_artifacts` 表達 Operations Center、Production Readiness 與 OTEL-ready correlation 所需資料。

## Local Dev Identity

`scripts/bootstrap.py` 會 seed 一組 local dev tenant/users：

| Role | Email | UUID |
|---|---|---|
| admin | `ops@example.com` | `00000000-0000-0000-0000-000000000002` |
| creator | `creator@example.com` | `00000000-0000-0000-0000-000000000003` |
| approver | `approver@example.com` | `00000000-0000-0000-0000-000000000004` |
| operator | `operator@example.com` | `00000000-0000-0000-0000-000000000005` |

Tenant：`00000000-0000-0000-0000-000000000001`。

## Task Metadata

`tasks.metadata` 會包含：

- `policy`：policy decision 與 reason。
- `planner`：Planner version、validation、fallback、SkillHub resolution。
- `plan`：browser action plan 與 resolved skill metadata。
- `browser_result`：final URL、title、observations。
- `evaluation`：score、verdict、checks。
- `reliability`：idempotency、DLQ、replay、quarantine metadata。

V1.1 的 request/task 關聯以 `tasks.correlation_id` 為主。API 與 Worker 在 `tasks.metadata`、audit payload 與 Kafka event 中保留 `trace_context`（`{"trace_id": "...", "span_id": "..."}`），實現端到端分佈式追蹤，零 DB Migration。

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

Worker 執行後會更新 `task_steps.status` 與 `task_steps.output_data`。V1.1 的 `output_data` 擴充記錄以下視覺化步驟回放資訊：

```json
{
  "duration_ms": 124.5,
  "span_id": "e2a1b3c4d5f67890",
  "screenshot_artifact_id": "00000000-0000-0000-0000-000000000099",
  "dom_summary": "Example Domain (url: https://example.com/)",
  "error": null
}
```

## Artifacts

S3 artifact metadata 會包含：

```json
{
  "backend": "s3",
  "bucket": "browser-agent",
  "key": "2026/05/22/<task-id>/screenshot-abc.png",
  "content_type": "image/png",
  "size_bytes": 12345,
  "retention": {"policy": "default", "expires_at": null},
  "redaction": {"status": "not_applied", "strategy": "noop"}
}
```

## Audit Events

新增或常用 events：

- `task.dlq_replayed`
- `task.dlq_quarantined`
- `task.execution_started`
- `task.artifact_written`
- `task.evaluated`
- `task.completed`
- `alert.test_dispatched`（手動測試派發 Webhook 告警紀錄）
