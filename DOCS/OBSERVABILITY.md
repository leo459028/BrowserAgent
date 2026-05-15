# Observability

## Health checks

| Endpoint | 檢查內容 |
|---|---|
| `GET /healthz` | API process 可回應 |
| `GET /readyz` | DB 可執行 `select(1)` |
| `GET /metrics` | Prometheus exposition |

## Logging

`src/browser_agent/logging.py` 使用 `python-json-logger`，輸出欄位包含：

- `asctime`
- `levelname`
- `name`
- `message`
- `module`
- `funcName`

目前 app factory 會呼叫 `configure_logging(settings.app_log_level)`。

建議新增結構化欄位：

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

目前這些 metrics 沒有在 orchestrator/runner/worker 中被 increment/observe。建議補上：

- create task 成功/失敗 counter
- policy blocked counter，按 reason label
- worker execution counter，按 final status label
- browser action duration histogram
- evaluator score histogram
- Kafka consume lag，需由 Kafka exporter 或 consumer metrics 提供

## Audit log

資料表：`audit_logs`

目前已寫：

- `task.blocked`
- `task.approved`

建議新增：

- `task.created`
- `task.policy_allowed`
- `task.execution_started`
- `task.step_started`
- `task.step_completed`
- `task.artifact_written`
- `task.evaluated`
- `task.completed`
- `task.review_required`
- `task.failed`

## Dashboard 建議

第一版 dashboard 可包含：

- API availability：`/healthz`, `/readyz`
- Task throughput：created/approved/executed per minute
- Success rate：completed vs review/failed
- Policy block rate by reason
- p50/p95 task duration
- Worker error count
- Artifact write error count
- Top blocked domains
- Evaluation score distribution

## Alert 建議

| Alert | 條件 |
|---|---|
| API down | `/healthz` 連續失敗 3 次 |
| DB not ready | `/readyz` 連續失敗 3 次 |
| Worker not consuming | Kafka lag 持續上升 |
| High failure rate | 5 分鐘內 review/failed 比例 > 30% |
| Policy anomaly | policy block rate 突然高於 baseline |
| Artifact failure | artifact write error > 0 |
| Browser crash spike | Playwright launch/action error 持續增加 |

## Traceability

目前 event payload 有 `event_id`、`event_type`、`task_id`、`tenant_id`。建議補上：

- `correlation_id`：從 API request 進入後一路傳遞。
- `causation_id`：標記 event 由哪個 event 觸發。
- `planner_version`、`policy_version`、`evaluator_ver`。
- artifact checksum 與 URI 寫入 `task_artifacts`。
