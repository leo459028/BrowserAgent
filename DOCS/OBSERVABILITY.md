# Observability

## Health / Readiness / Operations Endpoints

| Endpoint | 說明 |
|---|---|
| `GET /healthz` | API process health，公開 |
| `GET /readyz` | Database readiness，公開 |
| `GET /v1/ops/readiness` | Operations readiness，需要 operator/admin，包含 production、observability、kubernetes、otlp |
| `GET /v1/ops/alerts` | 即時評估維運系統健康與 7 大規則，需要 operator/admin |
| `GET /v1/ops/kms/status` | 查詢 Session Vault KMS 信封加密狀態與健康指標，需要 operator/admin |
| `GET /v1/ops/queues` | 查詢多優先權佇列（High/Queued/Batch）深度與 Worker 資源池分流，需要 operator/admin |
| `GET /v1/ops/dlp/status` | 查詢 Zero-Trust DLP 防護狀態與動態遮罩脫敏規則清單，需要 operator/admin |
| `GET /v1/ops/federation/nodes` | 查詢多叢集同盟拓撲、節點心跳時間戳與 Leader 租約狀態，需要 operator/admin |
| `POST /v1/ops/federation/heartbeat` | 同盟節點定時心跳回報與活躍排程計數，公開/內部 |
| `POST /v1/ops/federation/re-election` | 強制轉移同盟領導權進行維護演練或容災接管，需要 admin |
| `POST /v1/tasks/{id}/pause` | 線上暫停執行中之任務切換進入 HITL 人機協作模式，需要 operator/admin |
| `POST /v1/tasks/{id}/interact` | 下發遠端人機操作指令（click, type, press）至瀏覽器，需要 operator/admin |
| `POST /v1/tasks/{id}/resume` | 恢復暫停之任務推進並記錄介入總耗時審計，需要 operator/admin |
| `POST /v1/tasks/matrix` | 一鍵平行派發跨瀏覽器核心（Chromium, Firefox, WebKit）矩陣任務，需要 creator/admin |
| `GET /v1/tasks/matrix/{matrix_id}` | 查詢跨瀏覽器矩陣任務之聚合結果、差異與狀態，需要 authenticated actor |
| `GET /v1/ops/traces/{trace_id}` | 查詢端到端 Span 階層追蹤圖，需要 operator/admin |
| `GET /v1/ops/otlp/status` | 查詢 OpenTelemetry OTLP Exporter 導出狀態與隊列深度，需要 operator/admin |
| `POST /v1/ops/otlp/flush` | 手動強制排空並推送佇列中之 Spans，需要 admin |
| `POST /v1/ops/alerts/test-dispatch` | 手動測試外部 Webhook 轉發通道，需要 admin |
| `WS /v1/tasks/{task_id}/live-stream` | WebSocket 雙向/單向低延遲 JPEG 畫面幀串流廣播 |
| `GET /v1/sessions/{session_name}/validate` | 即時檢驗指定 Session 憑證解密完整性，需要 operator/admin |
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

## 多優先權佇列可觀測性（Queues Telemetry）

V1.3 引入多優先權加權佇列分流機制，透過 `GET /v1/ops/queues` 提供即時指標：
- **佇列深度**：監控 `agent.tasks.high`、`agent.tasks.queued`、`agent.tasks.batch` 三大 Kafka 主題的未消費任務深度。
- **分流路由計數**：追蹤高優先急件（`high_priority_routed`）、常規任務（`normal_priority_routed`）與批次任務（`batch_priority_routed`）的路由分流總量。
- **Worker 資源池狀態**：展示當前 Worker 資源池名稱（`WORKER_POOL_NAME`）與其訂閱之主題清單，支援資源池動態擴展調度。

## 即時畫面 WebSocket 廣播可觀測性（Live Stream Telemetry）

- **廣播佇列狀態**：`LiveTelemetryService` 監控各運行中任務的畫面推播佇列與訂閱客戶端數量。
- **傳輸速率與延遲**：以非同步事件模型推送 Base64 JPEG 畫面幀（預設 2 FPS），不阻礙 Playwright 執行主迴圈。
- **生命週期事件監控**：即時廣播 `step_started`、`self_healed`、`task_finished` 與 `aborted` 狀態事件。

## 選擇器自我修復可觀測性（Self-Healing Observability）

- **自癒標記**：當 Fallback Cascade 啟動並成功修復選擇器時，任務狀態與步驟 Output 標註 `self_healed: true`。
- **自癒審計事件**：自動寫入 `task.self_healed` 審計日誌，記錄原失效選擇器、修復後選擇器、所採策略（`semantic_attribute`、`text_match`、`dom_structure`）與匹配信心度（confidence）。
- **Operations Center 視覺標籤**：在 Visual Step Replay 步驟分頁與任務詳情中呈現醒目的綠色 `Self-Healed ✓` 徽章。

## KMS 信封加密可觀測性（KMS Crypto Health）

- 透過 `GET /v1/ops/kms/status` 提供透明的加解密健康儀表板：
  - 運行狀態（`healthy` / `degraded`）
  - 當前 KMS Provider（`local`、`aws_kms`、`vault`）
  - 使用中之 Master Key ID 與演算法（AES-256-GCM）
  - 即時測試加密迴路往返耗時（`roundtrip_ms`）

## 分散式追蹤（Distributed Tracing）

V1.3 延續基於 W3C `traceparent` 的端到端分散式追蹤與記憶體環形 TraceBuffer：

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

V1.3 內建非同步背景 `OtlpBatchSpanExporter`，可將分散式追蹤 Spans 即時推送至外部 APM：

- **協議格式**：採用標準 OTLP HTTP/JSON 規格（`POST /v1/traces`），相容於 Jaeger、Grafana Tempo、Datadog Agent 與 OpenTelemetry Collector。
- **背景批次發送**：Span 產生時非同步放入內部記憶體隊列，累積達到 `OTEL_BATCH_SIZE`（預設 50）或逾時閾值時，以獨立背景執行緒批量推送。
- **過載與丟棄保護**：隊列設有上限（預設 2000 個 Spans），若外部 APM 不可用或發生網路延遲，超過上限之 Spans 將依策略安全丟棄，確保絕不拖垮 API 或 Worker 之核心業務流程。
- **透明維運端點**：維運人員可透過 `GET /v1/ops/otlp/status` 隨時查看已推送 Span 數、丟棄數與佇列積壓深度；緊急情況下可呼叫 `POST /v1/ops/otlp/flush` 強制立即推送。

## 生產告警中心（Production Alerting Center）

V1.3 在 Operations Center 內建即時告警評估與外部 Webhook（Slack / Discord）非阻塞式轉發：

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

## 雙向遠端接管可觀測性（HITL Observability）

- **介入狀態徽章**：Operations Center 提供即時接管狀態徽章（`AUTOMATED` / `PAUSED (TAKEOVER)` / `RESUMED`）。
- **介入審計與耗時指標**：
  - 任務屬性 `task.human_intervened` 記錄是否曾有人工介入。
  - 歷程記錄包含介入操作者信箱、暫停原因、介入起始時間戳、恢復時間戳與總介入秒數（`duration_seconds`）。
  - 下發之每次點擊（座標 x, y）或按鍵輸入皆寫入 `task.interacted` 審計日誌。

## 跨瀏覽器矩陣可觀測性（Cross-Browser Matrix Observability）

- **矩陣聚合看板**：在 Operations Center 的 `Cross-Browser Matrix Comparison` 面板，透過 `GET /v1/tasks/matrix/{matrix_id}` 聚合比對。
- **跨核心效能與相容性矩陣**：
  - **核心覆蓋**：比對 Chromium、Firefox、WebKit 之執行狀態（`completed` / `failed`）。
  - **執行耗時比對**：並列展示三大核心之總執行時間（ms）差異。
  - **Verdict 與分數評估**：展示各瀏覽器引擎在相同驗證條件下的 Verdict（`pass` / `fail`）與分數。
  - **自癒表現對比**：追蹤特定瀏覽器是否因渲染結構特異性觸發選擇器自我修復。

## Zero-Trust DLP 動態防洩可觀測性（Zero-Trust DLP Observability）

- **防洩狀態透明度**：透過 `GET /v1/ops/dlp/status` 查閱動態防護狀態、作用中規則數與高斯模糊遮罩配置。
- **資料庫與產物標記**：
  - 凡套用過 CSS 密碼高斯模糊或 Token 脫敏之任務，自動標記 `task.dlp_masked = True`。
  - Operations Center 頂部狀態列提供動態 `DLP Shield: Active` 綠色防護徽章。

## 多叢集排程同盟與容災可觀測性（Federation Topology & Lease Observability）

- **叢集拓撲儀表板**：透過 `GET /v1/ops/federation/nodes` 展示全網排程節點之地理區域（Region）、存活狀態（`online` / `degraded` / `offline`）與活躍排程數。
- **Leader 租約監控**：即時識別當前持有 Leader 派發租約之節點 ID，顯示距上次心跳之秒數（`seconds_since_heartbeat`）。
- **心跳與重選審計**：節點心跳與強制重選（Re-election）事件寫入 Audit Log，確保容災切換全程可溯。
