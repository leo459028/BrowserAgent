# Use Cases

## Use Case：Operator 檢查 Operations Readiness

1. 取得 operator local dev token。
2. 開啟 `/operations`。
3. 查看 `Operations Readiness`。
4. 預期可看到 auth mode、artifact backend、warnings、worker identity、DLQ topic。

## Use Case：Production Readiness Smoke

1. 使用 `.env.production.example` 與 `docker-compose.prod.yml` 產生 Compose config。
2. 以 operator 或外部 IdP bearer token 呼叫 `GET /v1/ops/readiness`。
3. 查看 `production.status` 與 `production.checks`。
4. 預期 production-like 設定會關閉 local dev token、使用 JWKS/OIDC、Redis reliability、Kafka 與 S3 artifact backend。

## Use Case：OTEL-ready Correlation Smoke

1. 對任一 API request 帶入 `X-Correlation-ID`。
2. 可選擇帶入 W3C `traceparent`。
3. 預期 response 回寫同一個 `X-Correlation-ID`。
4. Log schema 中保留 `correlation_id`、`trace_id`、`parent_span_id`、`request_id`、`service_name`、`service_version` 與 `environment`。
5. V1.1 不會送 OTLP，也不代表完整 distributed tracing。

## Use Case：Normal Browser Task（人工建立、審查與步驟回放測試）

1. 在 `/operations` 左側 `Create Task` 卡片選擇 `Normal planner task`。
2. 點擊 `Create task`，任務建立並進入 `pending_approval` 狀態。
3. 左下方 Recent Tasks 點選該任務，右上角 **`Approve selected` 按鈕由灰轉綠（啟用）**。
4. 點擊 `Approve selected` 執行人工審核，任務轉為 `queued` ➜ `executing`。
5. Worker 執行完畢後任務狀態轉為 `completed`（右上角按鈕重回灰色鎖定）。
6. 右下角 `Visual Step Replay` 自動載入步驟分頁標籤（Step 1, Step 2）。點選特定步驟按鈕，即時預覽截圖縮圖、DOM 結構摘要與毫秒耗時。
7. 點選縮圖直接開啟全解析度截圖，展開折疊的 `▶ Raw Timeline Events` 檢驗完整 audit 與 lifecycle 事件。

## Use Case：S3 Artifact Governance

1. Docker Compose 設定 `ARTIFACT_BACKEND=s3`。
2. Task completed 後 artifacts 寫入 MinIO bucket。
3. Operations Center 顯示 artifact backend 為 `s3`。
4. Artifact content endpoint 使用 Bearer token 讀取 screenshot/html。
5. Tenant mismatch 仍回 `403`。

## Use Case：DLQ Bulk Replay

1. Operator 查 `GET /v1/dlq/tasks`。
2. 按 `Bulk DLQ replay` 或呼叫 `POST /v1/dlq/tasks/bulk-replay`。
3. Replayable tasks 回到 `queued`。
4. Quarantined tasks 出現在 skipped list。
5. Audit 寫入 `task.dlq_replayed`。

## Use Case：Quarantine Poison Task

1. Operator 對 failed DLQ task 呼叫 quarantine API。
2. `tasks.metadata.reliability.dlq.status` 變成 `quarantined`。
3. Bulk replay 不會重新排入該 task。
4. Audit 寫入 `task.dlq_quarantined`。

## Use Case：JWKS Auth Smoke

1. 設定 `AUTH_MODE=jwks`、`AUTH_JWKS_URL`、issuer、audience。
2. 用外部 IdP 或測試 JWKS 簽發 RS256 token。
3. 呼叫 `/v1/auth/me`。
4. 預期 valid token 回 actor；bad issuer/audience/expired/bad roles 回 `401`。

## Use Case：OIDC Discovery JWKS Smoke

1. 設定 `AUTH_MODE=jwks`、`AUTH_OIDC_ISSUER_URL`、issuer、audience，並留空 `AUTH_JWKS_URL`。
2. API 會讀取 `AUTH_OIDC_ISSUER_URL/.well-known/openid-configuration`。
3. 從 discovery response 的 `jwks_uri` 取得 JWKS。
4. 驗證 RS256 bearer token；缺少 `jwks_uri` 或 token 不合法時回 `401`。

## Use Case：生產告警中心與 Webhook 測試派發

1. Operator 或 Admin 登入 Operations Center。
2. 頂部儀表板顯示當前系統告警狀態徽章（如 `Healthy` 或 `Alerting`）。
3. 查閱 `Production Alerting Center`，檢視 7 大維運規則（DLQ、失敗率、待審核積壓、Worker 心跳、DB 延遲等）。
4. 點選 `Test Dispatch Webhook` 或以 Admin 呼叫 `POST /v1/ops/alerts/test-dispatch`。
5. 預期外部 Slack/Discord 通道收到非阻塞測試通知，系統寫入 `alert.test_dispatched` 審計日誌。

## Use Case：端到端分散式追蹤檢視（Trace Inspector）

1. 在 Operations Center 點選或複製任何任務之 `Trace ID`。
2. 貼入左側 `Trace Inspector` 輸入框，點擊 `Inspect Trace`。
3. 系統呼叫 `GET /v1/ops/traces/{trace_id}`，整合記憶體 TraceBuffer 與資料庫 Task Steps。
4. 預期展示樹狀 Span 清單：包含 HTTP Request、Kafka Publish、Worker Execution 以及各瀏覽器操作步驟（Span ID、耗時毫秒、狀態）。

## Use Case：視覺化步驟回放排查（Visual Step Replay）

1. 在 Operations Center 任務清單選取已完成或失敗之瀏覽器任務。
2. 右側 `Visual Step Replay` 面板自動載入步驟分頁條（Step 1、Step 2 等）。
3. 點選特定步驟按鈕，即時預覽該步驟之動作類型（navigate/screenshot/etc）、耗時（ms）、Span ID、DOM 結構摘要。
4. 若該步驟有截圖，自動顯示點選預覽縮圖，點擊可開啟完整解析度 Artifact，加速故障步驟定位。

## Use Case：Scheduled Tasks 定時巡檢排程調度

1. Operator 在 Operations Center 的 `Scheduled Tasks` 卡片建立定期巡檢任務，設定 Cron 表達式（例如每日早上 9:00 `0 9 * * *`）。
2. 設定任務負載（包含巡檢網站網址、操作步驟、低風險等級）。
3. 系統排程器背景搶取 Redis 分散式鎖，到達指定時間時自動派發全新 Task 進入流程。
4. 若配置 `concurrency_policy: skip`，當上一期巡檢仍在執行或待審核時，系統自動跳過本次派發，避免並發阻塞。
5. 維運人員可隨時點擊 `Run Now` 立即手動派發單次巡檢。

## Use Case：Session Vault 工作階段憑證治理與免登入復用

1. 登入任務完成後，Playwright 提取最新 Cookies 與 localStorage 狀態，以 `storage_state` 格式保存至 Session Vault。
2. 後續同網域與租戶之巡檢任務自動注入該工作階段，無需重複輸入帳密或觸發登入驗證。
3. Operations Center 的 `Session Vault` 卡片即時列出所有儲存的工作階段及其有效狀態與過期標記。

## Use Case：Session Vault 憑證外洩一鍵強制撤銷

1. 當安全性定期密碼輪換或偵測到憑證異常時，Admin 登入 Operations Center。
2. 在 `Session Vault` 列表找到該網域之 Session，點擊 `Revoke` 或呼叫 `DELETE /v1/sessions/{session_name}`。
3. 系統將該 Storage State 標記為 revoked，並寫入 `session.revoked` 審計日誌。
4. 後續任務將不再注入該憑證，強制重新執行完整登入驗證。

## Use Case：Full Video Replay 瀏覽器全行程 WebM 錄影播放

1. 建立任務時勾選啟用錄影（或系統預設啟用）。
2. Worker 在 Playwright 執行全程背景擷取畫面變化，並在任務完成後自動轉化為 WebM 視訊。
3. 視訊檔安全保存至 S3/Local ArtifactStore，並產生專屬串流 URL。
4. Operator 在 Operations Center 選取該任務時，右上側 Video 播放器自動載入視訊，可隨選播放、暫停與拖曳進度條，如同真實觀看工程師操作瀏覽器。

## Use Case：OpenTelemetry OTLP Exporter 串流推送至外部 APM

1. 維運人員配置 `OTEL_EXPORTER_OTLP_ENDPOINT`（如 Jaeger、Tempo 或 Datadog Agent 之 OTLP HTTP 端點）。
2. 系統在背景以非同步隊列批次收集所有 API 與 Worker 之 Span 呼叫鏈。
3. 累積至批次容量或超時時，自動以標準 OTLP JSON 協定推播至外部監控平台。
4. 呼叫 `GET /v1/ops/otlp/status` 或在 Operations Center 監控隊列深度與推播總數；支援 Admin `POST /v1/ops/otlp/flush` 強制立即排空推播。

## Use Case：Kubernetes 與 KEDA 自動擴展 Worker 資源池

1. 平台部署於 Kubernetes 叢集，套用 `deploy/k8s/` Kustomization。
2. KEDA ScaledObject 持續監聽 Kafka 佇列 `agent.tasks.queued` 之 consumer group lag。
3. 當大量定時巡檢同時觸發導致任務積壓時，KEDA 自動觸發 HPA 將 Worker Pod 副本數從 1 自動水平擴展至多達 10 個 Pod。
4. 任務排空後，Worker 叢集自動縮容至基準副本數，節省企業運算資源。
