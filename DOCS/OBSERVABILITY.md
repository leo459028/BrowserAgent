# Observability

## Health Checks

| Endpoint | 說明 |
|---|---|
| `GET /healthz` | API process health |
| `GET /readyz` | 透過 `select(1)` 檢查 database readiness |
| `GET /metrics` | 目前 process 的 Prometheus exposition |

## Logging

`src/browser_agent/logging.py` 透過 `python-json-logger` 設定 JSON logging。`APP_LOG_LEVEL` 控制 log level。

常用 structured fields：

- `task_id`
- `tenant_id`
- `correlation_id`
- `event_id`
- `worker_id`
- `step_no`
- `action_type`
- `target_host`
- `policy_decision`
- `evaluation_verdict`

## Metrics

定義於 `src/browser_agent/metrics.py`：

- `browser_agent_tasks_created_total`
- `browser_agent_tasks_executed_total`
- `browser_agent_tasks_failed_total`
- `browser_agent_task_duration_seconds`

目前 caveat：metrics 是 process-local。在 Docker Compose 中，API `/metrics` 只回報 API process counters，不會聚合 worker counters。

## Audit Log

Audit rows 儲存在 `audit_logs`。目前 lifecycle events 包含：

- `task.created`
- `task.pending_approval`
- `task.blocked`
- `task.approved`
- `task.queued`
- `task.execution_started`
- `task.artifact_written`
- `task.evaluated`
- `task.completed`
- `task.review_required`
- `task.failed`

`GET /v1/tasks/{task_id}/audit` 會回傳單一 task 的 audit timeline，v0.3 Dashboard 也會顯示。

## Dashboard

`GET /demo` 是本機 v0.3 Dashboard，可觀察：

- API health/readiness；
- task creation 與 approval；
- normal artifact、redaction metadata、high-risk、sensitive instruction、blocked-domain scenarios；
- recent tasks 與 status flow；
- API process metrics；
- audit timeline；
- steps 與 evaluation；
- screenshot 與 HTML artifacts；
- artifact governance metadata 與 access checks。

## 建議 Alerts

| Alert | Signal |
|---|---|
| API down | `/healthz` failing |
| DB not ready | `/readyz` failing |
| Worker not consuming | Kafka lag 或 queued tasks 沒有進展 |
| High failure rate | `failed` / `review` status rate |
| Policy anomaly | block/review rate 偏離 baseline |
| Artifact failure | artifact write/access errors |
| Browser crash spike | Playwright launch/action errors |
