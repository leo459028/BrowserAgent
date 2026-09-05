# Runbook

本 runbook 說明如何在本機 Docker Compose、Kubernetes 與 Helm 3 驗證 V1.3 Operations Center、OIDC SSO、KMS 信封加密、多優先權佇列、WebSocket Live Stream、線上 Abort、選擇器自癒與 production 配置。

## 1. 啟動 Stack

```powershell
copy .env.example .env
docker compose up -d --build
```

執行資料庫遷移：
```powershell
docker compose exec -T api alembic upgrade head
```

檢查：

```powershell
docker compose ps
curl.exe http://127.0.0.1:8000/healthz
curl.exe http://127.0.0.1:8000/readyz
```

## 2. 開啟 Operations Center

```text
http://127.0.0.1:8000/operations
```

應看到：

- `Browser Agent Operations Center`（V1.3）
- 頂部狀態列：K8s Mode、OTLP Exporter 與 SSO Login 按鈕
- `Scheduled Tasks` 卡片（Cron 定時巡檢、建立排程、即時手動觸發）
- `Session Vault` 卡片（儲存的工作階段、KMS 信封加密指示、一鍵 Validate 與 Revoke）
- `Live Telemetry Stream` 卡片（WebSocket 低延遲 JPEG 畫面廣播畫布與 Abort Task 按鈕）
- `Priority Queues Telemetry` 卡片（High, Queued, Batch 深度即時監控）
- `KMS Envelope Encryption Engine` 卡片（Provider, Key ID, 演算法與加解密延遲）
- `Video Replay` 卡片（內建 HTML5 WebM 播放器，隨選隨放瀏覽器錄影）
- `Production Alerting Center`（7 大規則狀態、Webhook 狀態指示、Test Dispatch）
- `Trace Inspector`（分散式追蹤 Trace ID 查詢與 Span 樹狀檢視）
- `Operations Readiness`
- `Production Readiness`
- `Observability`
- `Visual Step Replay & Replay Timeline`（含綠色自癒標籤）

## 3. Auth Smoke

```powershell
$operator = Invoke-RestMethod -Method Post `
  -Uri http://127.0.0.1:8000/v1/auth/local-token `
  -ContentType "application/json" `
  -Body '{"role":"operator"}'

Invoke-RestMethod -Method Get `
  -Uri http://127.0.0.1:8000/v1/auth/me `
  -Headers @{ Authorization = "Bearer $($operator.access_token)" }
```

## 4. Operations Readiness & Alerts 檢視

```powershell
Invoke-RestMethod -Method Get `
  -Uri http://127.0.0.1:8000/v1/ops/readiness `
  -Headers @{ Authorization = "Bearer $($operator.access_token)" }

Invoke-RestMethod -Method Get `
  -Uri http://127.0.0.1:8000/v1/ops/alerts `
  -Headers @{ Authorization = "Bearer $($operator.access_token)" }
```

Docker Compose 預期 artifact backend 為 `s3`，reliability backend 為 `redis`。

## 4.1 測試外部告警通道（Admin）

若設定了 `ALERT_WEBHOOK_URL`（或欲驗證派發流程）：

```powershell
$admin = Invoke-RestMethod -Method Post `
  -Uri http://127.0.0.1:8000/v1/auth/local-token `
  -ContentType "application/json" `
  -Body '{"role":"admin"}'

Invoke-RestMethod -Method Post `
  -Uri http://127.0.0.1:8000/v1/ops/alerts/test-dispatch `
  -Headers @{ Authorization = "Bearer $($admin.access_token)" } `
  -ContentType "application/json" `
  -Body '{"rule_id":"test_alert","severity":"info","message":"Manual verification"}'
```

## 4.2 Production-like Compose Config

```powershell
docker compose --env-file .env.production.example -f docker-compose.prod.yml config
```

此命令只檢查 Compose config 是否可被解析，不會啟動服務。範本預期使用 `APP_ENV=production`、`AUTH_MODE=jwks`、`AUTH_LOCAL_TOKENS_ENABLED=false`、`RELIABILITY_STORE=redis` 與 `ARTIFACT_BACKEND=s3`。

## 4.3 Kubernetes 生產套件檢驗

驗證 `deploy/k8s/` 產出之 K8s 物件宣告：

```powershell
kubectl kustomize deploy/k8s/
```

## 4.4 Enterprise Helm 3 Chart 套件檢驗

驗證 `deploy/helm/browser-agent/` 之語法與模板渲染：

```powershell
helm lint deploy/helm/browser-agent
helm template browser-agent deploy/helm/browser-agent
```

## 5. Normal Task E2E、視訊錄影與 Visual Step Replay 驗證

1. 在 `/operations` 左側 `Create Task` 卡片選擇 `Normal planner task`，點擊 `Create task`。
2. 任務建立後進入 `pending_approval`（待審核）狀態，左下方列表選中該任務。
3. 此時右上角的 **`Approve selected` 按鈕會由灰轉綠（啟用狀態）**。點擊進行人工核准。
4. Worker 消費佇列並執行瀏覽器流程，執行完畢後任務狀態轉為綠色 `completed`。
5. 在右側 `Visual Step Replay` 點選步驟分頁標籤（如 Step 1、Step 2），可即時查看該步驟的耗時（ms）、Span ID、DOM 摘要與截圖縮圖。若觸發選擇器自癒，步驟將標註綠色 `Self-Healed ✓`。
6. 若任務啟用錄影，右上側 `Execution Video Recording` 播放器會載入全行程 WebM 錄影，可點擊播放按鈕觀看完整操作流程。
7. 將任務的 Trace ID 貼入左側 `Trace Inspector`，點選 `Lookup`，可檢視完整跨服務之 Span 階層追蹤圖。

## 6. Scheduled Tasks 與 Session Vault 驗證

### Scheduled Tasks 定時巡檢
1. 在 `/operations` 的 `Scheduled Tasks` 卡片點擊 `Create Schedule`，輸入名稱與 Cron 表達式（如 `*/15 * * * *`）。
2. 在列表選中該排程，點擊 `Run Now` 立即派發任務。
3. 任務列表會出現對應的前置任務，依序進行審核與執行。

### Session Vault 工作階段管理與 KMS 驗證
1. 在 `Session Vault` 卡片點擊 `Refresh Sessions`，可查閱目前所有儲存之 Playwright storage_state 憑證及其 KMS 加密標識。
2. 點擊 `Validate` 按鈕，系統呼叫 `/v1/sessions/{name}/validate` 即時執行 KMS 解密迴路校驗，回報有效 Cookie 與 Storage 數量。
3. 當需要撤銷已失效或需輪換的 Session 時，點擊該筆資料旁的 `Revoke`，系統即刻將其標記為已撤銷，後續任務不再重用。

## 6.1 多優先權佇列與 Worker 分流檢視

```powershell
Invoke-RestMethod -Method Get `
  -Uri http://127.0.0.1:8000/v1/ops/queues `
  -Headers @{ Authorization = "Bearer $($operator.access_token)" }
```
可查閱 `agent.tasks.high`、`agent.tasks.queued`、`agent.tasks.batch` 深度與 Worker pool 訂閱情況。

## 6.2 WebSocket Live Stream 廣播與線上 Abort 測試

1. 當有任務處於 `executing` 狀態時，在 Operations Center 點選該任務，`Live Telemetry Stream` 畫布會自動建立 WebSocket 連線（`WS /v1/tasks/{id}/live-stream`）並以 2 FPS 渲染當前頁面截圖。
2. 若需緊急中斷，點選紅色的 **`Abort Task`** 按鈕（呼叫 `POST /v1/tasks/{id}/abort`）。
3. Worker 即時捕獲中止信號，安全釋放 Playwright 資源，任務狀態轉為 `aborted`。

## 7. DLQ Operations

- `Refresh DLQ`：查 failed DLQ tasks。
- 單筆 `replay`：把 failed task 放回 `queued`。
- `Bulk DLQ replay`：批次 replay non-quarantined tasks。
- Quarantine API：

```powershell
Invoke-RestMethod -Method Post `
  -Uri http://127.0.0.1:8000/v1/dlq/tasks/<TASK_ID>/quarantine `
  -Headers @{ Authorization = "Bearer $($operator.access_token)" } `
  -ContentType "application/json" `
  -Body '{"reason":"poison message"}'
```

## 8. 維運疑難排解與升級說明

### 既有版本升級至 V1.3
- 執行資料庫遷移確認最新 schema：
  ```powershell
  alembic upgrade head
  ```
- 重新建置映像檔：
  ```powershell
  docker compose up -d --build api worker
  ```

### Kafka / Zookeeper Stale Session 處理
若容器重啟時出現 `NodeExists` 或 Zookeeper session timeout 導致 Kafka 退出，請重啟相依服務：
```powershell
docker compose restart zookeeper kafka api worker
```

## 9. 測試命令

```powershell
pytest -q
python -m compileall src tests worker alembic
git diff --check
kubectl kustomize deploy/k8s/
helm lint deploy/helm/browser-agent
helm template deploy/helm/browser-agent
docker compose exec -T api pytest -q
docker compose --env-file .env.production.example -f docker-compose.prod.yml config
```
