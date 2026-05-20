# Observability

## Health Checks

| Endpoint | 說明 |
|---|---|
| `GET /healthz` | API process health |
| `GET /readyz` | DB readiness，執行 `select(1)` |
| `GET /metrics` | API process 的 Prometheus exposition |

## Logging

`src/browser_agent/logging.py` 使用 `python-json-logger`。app factory 會依
`APP_LOG_LEVEL` 呼叫 `configure_logging()`。

目前建議在後續版本補強 structured fields：

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

`src/browser_agent/metrics.py` 定義：

- `browser_agent_tasks_created_total`
- `browser_agent_tasks_executed_total`
- `browser_agent_tasks_failed_total`
- `browser_agent_task_duration_seconds`

目前接入位置：

- API process：create task 會增加 `browser_agent_tasks_created_total`。
- Worker process：completed/review task 會增加 `browser_agent_tasks_executed_total` 與 duration histogram。
- Worker process：failed task 會增加 `browser_agent_tasks_failed_total` 與 duration histogram。

重要限制：

- `/metrics` 掛在 API process 上。
- 在 Docker Compose 多 process 架構下，API 的 `/metrics` 不會自動匯總 worker process 的 metrics。
- 實際端到端驗證中，task 已由 worker 完成，但 API `/metrics` 只顯示 API process 的 created counter。

後續建議：

- 使用 Prometheus 分別 scrape API 與 Worker metrics endpoint，或導入 multiprocess metrics。
- 補 policy decision counter，按 reason label。
- 補 browser action duration histogram。
- 補 evaluator score histogram。
- 補 Kafka consume lag，可由 Kafka exporter 或 consumer metrics 提供。

## Audit Log

資料表：`audit_logs`

v0.2 已覆蓋：

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

`GET /v1/tasks/{task_id}/audit` 可讀取單一 task 的 audit timeline，Dashboard 也會顯示。

後續可補：

- `task.step_started`
- `task.step_completed`
- `policy_version`
- `rule_id`
- `planner_version`

## Dashboard

`GET /demo` 是 v0.2 本機 Dashboard，可觀察：

- API health/readiness。
- task 建立與 approval。
- allowlisted/high-risk/sensitive/blocked-domain scenarios。
- recent tasks。
- status flow。
- API process metrics。
- task audit timeline。
- steps。
- evaluation。
- screenshot 與 HTML artifacts。

## Alert 建議

| Alert | 條件 |
|---|---|
| API down | `/healthz` 連續失敗 |
| DB not ready | `/readyz` 連續失敗 |
| Worker not consuming | Kafka lag 高於門檻 |
| High failure rate | review/failed 比例高於門檻 |
| Policy anomaly | policy block/review rate 大幅偏離 baseline |
| Artifact failure | artifact write error > 0 |
| Browser crash spike | Playwright launch/action error 增加 |

