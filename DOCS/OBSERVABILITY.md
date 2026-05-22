# Observability

## Health Checks

| Endpoint | 說明 |
|---|---|
| `GET /healthz` | API process health，公開 |
| `GET /readyz` | 執行 database `select(1)` readiness check，公開 |
| `GET /metrics` | Prometheus exposition text，需要 operator/admin token |

## Logging

[src/browser_agent/logging.py](../src/browser_agent/logging.py) 使用 `python-json-logger` 設定 JSON logging。`APP_LOG_LEVEL` 控制 root logger level。

建議觀察欄位：

- `task_id`
- `tenant_id`
- `correlation_id`
- `actor_email`
- `actor_roles`
- `worker_id`
- `step_no`
- `action_type`
- `target_host`
- `policy_decision`
- `evaluation_verdict`

## Metrics

[src/browser_agent/metrics.py](../src/browser_agent/metrics.py) 定義：

- `browser_agent_tasks_created_total`
- `browser_agent_tasks_executed_total`
- `browser_agent_tasks_failed_total`
- `browser_agent_tasks_dlq_total`
- `browser_agent_task_duration_seconds`

注意：metrics 是 process-local。Docker Compose 中 API `/metrics` 只代表 API process counters，不包含 worker process counters。

## Audit Log

`audit_logs` 會保存 task lifecycle、approval actor 與 Planner/SkillHub events。

目前可能出現的 events：

- `task.created`
- `task.pending_approval`
- `task.blocked`
- `task.approved`
- `task.queued`
- `task.plan_fallback_used`
- `task.skill_resolution`
- `task.execution_started`
- `task.artifact_written`
- `task.evaluated`
- `task.completed`
- `task.review_required`
- `task.failed`
- `task.dlq_replayed`

v0.5 以後 approval audit payload 會包含：

- `actor_user_id`
- `actor_email`
- `actor_roles`
- `correlation_id`

`GET /v1/tasks/{task_id}/audit` 需要 approver/operator/admin token。Dashboard 的 `Audit Timeline` panel 會用 operator token 顯示。

v0.6 worker audit actor 會使用 `service:<WORKER_SERVICE_ID>`。Final failure audit payload 會包含 `dlq` metadata；replay 會寫入 `task.dlq_replayed`。

## Dashboard

`GET /demo` 是本機 v0.6 Dashboard，可觀察：

- Reliability store、rate limit、worker service identity、DLQ topic。
- Idempotency smoke test。
- DLQ failed task list 與 replay。
- Identity/RBAC actor 與 permissions。
- operator forbidden create scenario。
- API health/readiness。
- task creation 與 production approval。
- Normal/Fallback/SkillHub/Policy scenarios。
- recent tasks 與 status flow。
- API process metrics。
- audit timeline。
- Planner validation、fallback status、validation errors。
- SkillHub resolved/unresolved metadata。
- steps 與 evaluation。
- screenshot 與 HTML artifacts。
- artifact governance metadata 與 access checks。

## 建議 Alerts

| Alert | Signal |
|---|---|
| API down | `/healthz` failing |
| DB not ready | `/readyz` failing |
| Auth errors spike | `401` rate 異常升高 |
| RBAC denied spike | `403` rate 異常升高 |
| Worker not consuming | queued tasks 長時間未被消費 |
| Kafka unavailable | API/worker bootstrap 等待 Kafka 或 producer/consumer 連線失敗 |
| High failure rate | `failed` / `review` status rate |
| DLQ spike | `browser_agent_tasks_dlq_total` 或 `task.failed` with `dlq` 增加 |
| Rate limited spike | `429` rate 異常升高 |
| Policy anomaly | blocked/requires-approval rate 偏離 baseline |
| Planner fallback spike | `task.plan_fallback_used` event 數量升高 |
| SkillHub unresolved spike | `planner.skill_resolution.unresolved_count` 偏高 |
| Artifact failure | artifact write/access errors |
| Browser crash spike | Playwright launch/action errors |
