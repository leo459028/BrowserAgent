# Runbook

本 runbook 說明如何在本機 Docker Compose 驗證 V1.1 Operations Center 與 production-like Compose 設定。

## 1. 啟動 Stack

```powershell
copy .env.example .env
docker compose up -d --build
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

- `Browser Agent v1.1 Operations Center`
- `Production Alerting Center`（7 大規則狀態、Webhook 狀態指示、Test Dispatch）
- `Trace Inspector`（分散式追蹤 Trace ID 查詢與 Span 樹狀檢視）
- `Operations Readiness`
- `Production Readiness`
- `Observability`
- `Artifact Backend`
- `Reliability / DLQ`
- `Visual Step Replay & Replay Timeline`

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

V1.1 會額外回傳：

- `production.status` 與 `production.checks`
- `observability.otel_ready` 與 `observability.log_schema_fields`
- `summary` 與即時評估的 7 大維運告警清單

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

若要用外部 IdP token 操作 `/operations`，可在 Identity / RBAC 區塊貼上 `External bearer token`。V1.1 不提供完整 login/callback/session flow。

## 5. Normal Task E2E 與 Visual Step Replay 驗證

1. 在 `/operations` 左側 `Create Task` 卡片選擇 `Normal planner task`，點擊 `Create task`。
2. 任務建立後進入 `pending_approval`（待審核）狀態，左下方列表選中該任務。
3. 此時右上角的 **`Approve selected` 按鈕會由灰轉綠（啟用狀態）**。點擊進行人工核准。
4. Worker 消費佇列並執行瀏覽器流程，執行完畢後任務狀態轉為綠色 `completed`（右上角 `Approve selected` 自動恢復為灰色鎖定，防止重複審查）。
5. 在右側 `Visual Step Replay` 點選步驟分頁標籤（如 Step 1、Step 2），可即時查看該步驟的耗時（ms）、Span ID、DOM 摘要，並在右側預覽截圖縮圖（點擊縮圖開啟高解析度原圖）。
6. 將任務的 Trace ID 貼入左側 `Trace Inspector`，點選 `Lookup`，可檢視完整跨服務之 Span 階層追蹤圖。

## 6. DLQ Operations

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

## 7. 維運疑難排解與升級說明

### 既有 V1.0 升級至 V1.1
- V1.1 採 100% 向後相容設計，資料庫 **無須 Migration**。
- 若既有 Docker 容器已在運行，更新代碼後只需執行重新建置更新映像檔：
  ```powershell
  docker compose up -d --build api worker
  ```
- 容器更新後可直接開啟 `http://localhost:8000/operations` 檢視新功能。

### Kafka / Zookeeper Stale Session 處理
若容器重啟時出現 `NodeExists` 或 Zookeeper session timeout 導致 Kafka 退出，請重啟相依服務：
```powershell
docker compose restart zookeeper kafka api worker
```

## 8. 測試命令

```powershell
pytest -q
python -m compileall src tests worker alembic
git diff --check
docker compose exec -T api pytest -q
docker compose --env-file .env.production.example -f docker-compose.prod.yml config
```
