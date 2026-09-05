# Observability

## Health / Readiness

| Endpoint | 說明 |
|---|---|
| `GET /healthz` | API process health，公開 |
| `GET /readyz` | Database readiness，公開 |
| `GET /v1/ops/readiness` | Operations readiness，需要 operator/admin，包含 production、observability、kubernetes、otlp |
| `GET /v1/ops/alerts` | 即時評估維運系統健康與 7 大規則，需要 operator/admin |
| `GET /v1/ops/traces/{trace_id}` | 查詢端到端 Span 階層追蹤圖，需要 operator/admin |
| `GET /v1/ops/otlp/status` | 查詢 OpenTelemetry OTLP Exporter 導出狀態與隊列深度，需要 operator/admin |
| `POST /v1/ops/otlp/flush` | 手動強制排空並推送佇列中之 Spans，需要 admin |
| `POST /v1/ops/alerts/test-dispatch` | 手動測試外部 Webhook 轉發通道，需要 admin |
| `GET /metrics` | Prometheus exposition text，需要 operator/admin |

`/v1/ops/readiness` 回傳 app version、auth mode、local token 狀態、database、reliability store、Kafka config、artifact backend、worker identity、DLQ topic、Production Readiness、Observability、Kubernetes 狀態、OTLP 狀態與 warnings。

## Metrics

目前 metrics 包含：

- `browser_agent_tasks_created_total`
- `browser_agent_tasks_executed_total`
- `browser_agent_tasks_failed_total`
- `browser_agent_tasks_dlq_total`
- `browser_agent_task_duration_seconds`
- `browser_agent_http_requests_total`
- `browser_agent_http_request_duration_seconds`
- `browser_agent_auth_failures_total`
- `browser_agent_production_readiness`

注意：目前 metrics 仍是 process-local。

## 分散式追蹤（Distributed Tracing）

V1.2 內建基於 W3C `traceparent` 的端到端分散式追蹤與記憶體環形 TraceBuffer：

1. **Context 傳播**：
   - API Middleware 解析或產生 W3C `traceparent`（`00-{trace_id}-{span_id}-{flags}`），並回寫於 HTTP Response Headers 與 `X-Correlation-ID`。
   - 任務發布至 Kafka 時帶入 `trace_context`。
   - Worker 接收任務後延續父級 Trace 上下文，建立 Worker 執行 Span。
2. **Span 生命週期**：
   - 記錄 `trace_id`、`span_id`、`parent_span_id`、`name`、`service_name`、`start_time`、`end_time`、`duration_ms`、`status`、`attributes`。
   - API 請求自動產生 HTTP Span。
   - Worker 自動產生 Task Execution Span，TaskRunner 各執行步驟記錄 `span_id` 與執行耗時。
3. **Trace Inspector**：
   - Operations Center 提供即時 Trace ID 查詢介面，透過 `GET /v1/ops/traces/{trace_id}` 跨進程整合記憶體 TraceBuffer 與 DB Task Steps，展示完整 Span 樹狀追蹤圖。

## OpenTelemetry OTLP Exporter 串流導出

V1.2 正式內建非同步背景 `OtlpBatchSpanExporter`，可將分散式追蹤 Spans 即時推送至外部 APM：

- **協議格式**：採用標準 OTLP HTTP/JSON 規格（`POST /v1/traces`），相容於 Jaeger、Grafana Tempo、Datadog Agent 與 OpenTelemetry Collector。
- **背景批次發送**：Span 產生時非同步放入內部記憶體隊列，累積達到 `OTEL_BATCH_SIZE`（預設 50）或逾時閾值時，以獨立背景執行緒批量推送。
- **過載與丟棄保護**：隊列設有上限（預設 2000 個 Spans），若外部 APM 不可用或發生網路延遲，超過上限之 Spans 將依策略安全丟棄，確保絕不拖垮 API 或 Worker 之核心業務流程。
- **透明維運端點**：維運人員可透過 `GET /v1/ops/otlp/status` 隨時查看已推送 Span 數、丟棄數與佇列積壓深度；緊急情況下可呼叫 `POST /v1/ops/otlp/flush` 強制立即推送。

## 生產告警中心（Production Alerting Center）

V1.2 在 Operations Center 內建即時告警評估與外部 Webhook（Slack / Discord）非阻塞式轉發：

| 規則 ID | 嚴重等級 | 監控訊號 / 條件 | 處置建議 |
|---|---|---|---|
| `dlq_backlog_critical` | Critical | DLQ 失敗任務積壓 >= 5 筆 | 檢查 Worker 錯誤日誌與死信佇列 |
| `task_failure_rate_warning` | Warning | 最近任務失敗率 >= 30% | 檢查目標網頁是否變更或連線逾時 |
| `pending_approval_backlog_info` | Info | 待人工核准任務 >= 10 筆 | 指派 Approver 盡速前往審核 |
| `worker_liveness_critical` | Critical | 距最後任務執行 > 15 分鐘（有排隊任務） | 確認 Worker 容器與 Kafka 連線正常 |
| `db_latency_warning` | Warning | 資料庫 ping 延遲 > 200ms | 檢查 PostgreSQL 主機負載與連線池 |
| `reliability_memory_fallback_warning` | Warning | 生產環境啟用 Memory Reliability Store | 將 `RELIABILITY_STORE` 切換至 Redis |
| `webhook_unconfigured_info` | Info | 未設定外部告警 Webhook URL | 設定 `ALERT_WEBHOOK_URL` 啟用即時推播 |

- **非阻塞 Webhook 轉發**：當檢測到 Warning / Critical 告警時，以背景執行緒非同步推送至 Slack/Discord 或相容之 Webhook URL，設定 3 秒超時，保證不拖慢 API 主線程。
- **測試通道驗證**：管理員可隨時透過 `/v1/ops/alerts/test-dispatch` 驗證 Webhook 配置與外部網絡連通性。

## 可視化步驟回放與視訊錄製（Visual Step & Video Replay）

`GET /v1/tasks/{task_id}/replay` 與 `/v1/tasks/{task_id}/video` 提供完整的操作審計與重現能力：
- **步驟分頁條**：Operations Center 提供步數導航分頁按鈕（Step 1, Step 2, ...）。
- **點選即時預覽**：點選步驟即時展開該步驟之類型（navigate, screenshot, etc.）、狀態、耗時（ms）、對應 Span ID、DOM 結構摘要及截圖縮圖。
- **WebM 全行程視訊播放**：支援任務執行全程高畫質 WebM 錄影，可在 Operations Center 內嵌之 HTML5 播放器中流暢播放與隨意拖曳時間軸。
- **向後相容**：保留原始 Replay Timeline 折疊檢視，滿足現有維運與測試流程。
