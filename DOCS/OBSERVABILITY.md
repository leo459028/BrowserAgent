# Observability

## Health / Readiness

| Endpoint | 說明 |
|---|---|
| `GET /healthz` | API process health，公開 |
| `GET /readyz` | Database readiness，公開 |
| `GET /v1/ops/readiness` | Operations readiness，需要 operator/admin |
| `GET /metrics` | Prometheus exposition text，需要 operator/admin |

`/v1/ops/readiness` 回傳 app version、auth mode、local token 狀態、database、reliability store、Kafka config、artifact backend、worker identity、DLQ topic 與 warnings。

## Metrics

目前 metrics 包含：

- `browser_agent_tasks_created_total`
- `browser_agent_tasks_executed_total`
- `browser_agent_tasks_failed_total`
- `browser_agent_tasks_dlq_total`
- `browser_agent_task_duration_seconds`

注意：目前 metrics 仍是 process-local。

## Audit / Replay

Audit logs 保存 task lifecycle、approval actor、Planner/SkillHub、artifact、DLQ replay/quarantine events。

Replay-lite endpoint：

```text
GET /v1/tasks/{task_id}/replay
```

會把 audit、steps、artifacts、evaluation 組成同一個 timeline，供 Operations Center 顯示。

## 建議 Alerts

| Alert | Signal |
|---|---|
| API down | `/healthz` failing |
| DB not ready | `/readyz` 或 readiness database check failing |
| Auth errors spike | `401` rate 異常升高 |
| RBAC denied spike | `403` rate 異常升高 |
| DLQ spike | `browser_agent_tasks_dlq_total` 或 `task.failed` with DLQ metadata 增加 |
| Quarantine spike | `task.dlq_quarantined` 增加 |
| Artifact backend degraded | readiness artifact backend warning 或 artifact content errors |
