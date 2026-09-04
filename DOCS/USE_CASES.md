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
