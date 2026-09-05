# Test Report

最後更新：2026-09-05

## V1.2 完整實作（Scheduled Tasks + Session Vault + Video Replay + OTLP Exporter + K8s/KEDA）測試結果

日期：2026-09-05

本次完整落實 V1.2 核心增強：
1. **Scheduled Tasks 定時巡檢調度引擎**：標準 5 欄位 Cron 表達式解析（零外部依賴純 Python）、Redis 分散式搶鎖（`scheduler:lock`，TTL 55s）、`concurrency_policy: skip/allow` 防重入調度、手動立即觸發與背景自動派發。
2. **Session Vault 工作階段保險箱**：Playwright `storage_state` Cookies/localStorage 憑證治理、多租戶安全隔離、自動跨任務免登入注入、過期狀態追蹤與 `DELETE /v1/sessions/{session_name}` 一鍵強制撤銷。
3. **全行程 WebM 瀏覽器視訊錄製與播放器**：Playwright 全螢幕視訊錄製、自動寫入 ArtifactStore（Local/S3）、`/v1/tasks/{id}/video` 串流端點、Operations Center 內建 HTML5 Video 播放器。
4. **OpenTelemetry OTLP Exporter**：非同步背景 Batch Span Exporter，支援標準 OTLP HTTP/JSON 協議將跨服務 Traces 串流導出至外部 APM（Jaeger/Tempo/Datadog），具備丟棄保護與 `/v1/ops/otlp/status` 維運透明度。
5. **Kubernetes 生產 Manifests 套件與 KEDA**：完整 `deploy/k8s/` Kustomization 套件（API, Worker, ConfigMap, Secret, Service, Ingress），以及基於 Kafka Consumer Group Lag 自動將 Worker 水平擴展（1~10 Pods）之 KEDA ScaledObject。
6. **Operations Center UI 升級**：V1.2 頂部標題、K8s Mode / OTLP Exporter 指示徽章、Scheduled Tasks 排程管理面板、Session Vault 工作階段面板、WebM Video 播放器卡片。

### 1. Host 測試結果

```powershell
pytest -q
```
**結果：84 passed, 1 warning in 3.48s**（17 個測試模組全數通過）。

新增測試模組明細：
- `tests/test_v12_scheduler.py`：Cron 解析演算法（星號、步進、範圍、列表）、Redis 分散式鎖競爭、並行策略（skip/allow）與任務派發。
- `tests/test_v12_session_vault.py`：Storage State 序列化保存、同租戶自動注入復用、跨租戶隔離與撤銷保護。
- `tests/test_v12_video_artifact.py`：WebM 錄影產生、ArtifactStore 寫入、Task Replay 整合與 Video URL 解析。
- `tests/test_v12_otlp_exporter.py`：Batch Span 非同步收集、隊列容量保護、批次推播組裝與狀態查詢。
- `tests/test_v12_apis.py`：Scheduled Tasks CRUD 與手動觸發、Session 列表與撤銷、Video 串流端點、Readiness K8s/OTLP 區塊、Operations Center V1.2 UI 元素。

語法與代碼編譯檢查：
```powershell
python -m compileall src tests worker alembic
```
**結果：語法檢查全部通過，exit code 0。**

Git Diff 格式檢查：
```powershell
git diff --check
```
**結果：完全整潔無尾隨空白，exit code 0。**

Kubernetes Manifests Kustomize 檢查：
```powershell
kubectl kustomize deploy/k8s/
```
**結果：全套 Kubernetes 物件（ConfigMap, Secret, Service, Deployment, Ingress, ScaledObject）格式解析完全正確，exit code 0。**

Production-like Compose Config 檢查：
```powershell
docker compose --env-file .env.production.example -f docker-compose.prod.yml config
```
**結果：配置結構正確解析，exit code 0。**

### 2. Docker 容器內自動化測試結果

在 Docker Compose 7 大容器（API, Worker, Postgres, Redis, Kafka, Zookeeper, MinIO）完整啟動下執行：
```powershell
docker compose exec -T api pytest -q
```
**結果：84 passed, 2 warnings in 3.04s**（容器內與 Host 端全套測試 100% 一致通過）。

### 3. 真實瀏覽器端到端測試結果（Playwright Chromium Real Browser Test）

執行命令：
```powershell
docker compose exec -T -e BASE_URL=http://api:8000 worker python scripts/comprehensive_browser_test.py
```
**測試結果：11 大步驟全數通過（Exit 0）！**

各步驟實際驗證細節：
1. **角色 Token 認證**：成功簽發並驗證 `creator`, `approver`, `operator`, `admin` 4 組 JWT。
2. **Operations Readiness 檢驗**：
   - `app.version`: `1.2.0`
   - `auth.mode`: `local`
   - `artifact_backend.backend`: `s3`
   - `kubernetes.platform`: `docker_or_standalone`
3. **Production Alerting Center**：
   - 7 大維運規則即時評估回傳 `status: healthy`，`active_alerts_count: 0`。
4. **真實 Playwright 瀏覽器任務執行**：
   - 建立任務，目標為白名單網域 `https://example.com`，狀態為 `pending_approval`。
   - Approver 呼叫 `/v1/tasks/{id}/approve` 核准，狀態躍遷至 `queued`。
   - Worker 消費 Kafka 佇列，喚起真實 **Playwright Chromium 瀏覽器** 實體訪問網站。
   - 任務執行成功，狀態變為 `completed`；提取頁面標題 `'Example Domain'`，Evaluation Verdict 為 `pass`，得分 `100.0`。
5. **截圖 Artifact 下載與 Magic Bytes 檢驗**：
   - 透過 `/v1/artifacts/{id}/content` 下載截圖，大小為 `18002 bytes`。
   - 校驗檔案標頭魔術位元組：開頭符合標準 PNG 二進位格式 `\x89PNG\r\n\x1a\n`。
6. **全行程 WebM 視訊錄影下載與 EBML 檢驗**：
   - 任務回放回傳 `video_artifact_id` 與 `video_url`。
   - 透過 `/v1/tasks/{id}/video` 下載視訊串流，大小為 `23287 bytes`。
   - 校驗檔案標頭魔術位元組：開頭符合標準 EBML/WebM 格式 `\x1aE\xdf\xa3`。
7. **Session Vault 治理**：
   - 成功透過 `GET /v1/sessions` 檢索 Storage State 工作階段。
   - 成功呼叫 `DELETE /v1/sessions/{session_name}` 執行一鍵撤銷保護，記錄審計日誌。
8. **Scheduled Tasks 排程調度**：
   - 成功呼叫 `POST /v1/scheduled-tasks` 建立定時排程。
   - 成功呼叫 `POST /v1/scheduled-tasks/{id}/run` 立即手動派發任務，回傳新任務 ID。
9. **Operations Center UI 渲染**：
   - `GET /operations` 正常回應（HTTP 200），包含 `Browser Agent v1.2 Operations Center`、`Scheduled Tasks`、`Session Vault`、`Full WebM Video Recording` 等卡片。
10. **Playwright 直接無頭瀏覽器 UI 測試**：
    - 在 Worker 容器中啟動 Playwright 無頭 Chromium 瀏覽器直接打開 `http://api:8000/operations`。
    - 驗證 Page Title 為 `Browser Agent v1.2 Operations Center`。
    - 驗證 H1 標題為 `Browser Agent v1.2 Operations Center`。
    - 驗證 DOM 節點：`#approve`、`#refresh`、`#k8s-platform-badge`、`#otlp-stream-badge`、`#scheduled-tasks-section`、`#session-vault-section`、`#video-player-card` 全數存在且正常互動。
    - 截取 Operations Center 渲染截圖並保存至 `scratch/operations_dashboard_verified.png`（`124890 bytes`）。

---

## 歷史紀錄：V1.1 完整實作（E2E Tracing + Alerting Center + Visual Step Replay）測試結果

日期：2026-09-04

本次完整落實 V1.1 核心增強：
1. **端到端分散式追蹤（E2E Distributed Tracing）**：基於 W3C `traceparent`、Span 生命週期管理、記憶體環形 TraceBuffer 與 `/v1/ops/traces/{trace_id}` 跨進程樹狀展示。
2. **生產告警中心（Production Alerting Center）**：7 大維運規則即時評估（`GET /v1/ops/alerts`）、外部 Webhook（Slack/Discord）非阻塞背景轉發、手動測試派發通道（`POST /v1/ops/alerts/test-dispatch`）與 Audit 日誌。
3. **可視化步驟回放（Visual Step Replay）**：擴充 `/v1/tasks/{task_id}/replay`，支援步驟分頁條、點選即時預覽截圖縮圖、DOM 結構摘要、執行毫秒耗時與 Span 關聯，100% 向後相容。
4. **Operations Center UI 升級**：System Alert Badge、Production Alerting 卡片、Trace Inspector 面板、Visual Step Replay 步驟分頁導航。

### 1. Host 測試結果

```powershell
pytest -q
```
**結果：74 passed, 2 warnings in 3.64s**（測試項目由 66 增加至 74，全部通過）。

語法與代碼編譯檢查：
```powershell
python -m compileall src tests worker alembic
```
**結果：語法檢查全部通過，exit code 0。**

Git Diff 格式檢查：
```powershell
git diff --check
```
**結果：完全整潔無尾隨空白，exit code 0。**

Production-like Compose Config 檢查：
```powershell
docker compose --env-file .env.production.example -f docker-compose.prod.yml config
```
**結果：配置結構正確解析，exit code 0。**

### 2. Docker 容器內測試結果

在 Docker Desktop 啟動且全容器運作狀態下執行：
```powershell
docker compose exec -T api pytest -q
```
**結果：74 passed in 2.62s**（容器內與 Host 測試一致全部通過）。

### 3. Docker 容器環境端到端 Smoke 實測（scratch/smoke_v11.ps1）

針對運行中的 7 個 Docker 容器（API, Worker, Postgres, Redis, Kafka, Zookeeper, MinIO）執行真實端到端流程：
1. **健康與告警檢查**：
   - `GET /healthz` ➜ `{"status": "ok"}`
   - `GET /v1/ops/alerts` ➜ 7 大規則即時評估回傳 `healthy: true`，`critical: 0`, `warning: 0`。
2. **任務完整生命週期與 Tracing 追蹤**：
   - 透過 `POST /v1/tasks` 建立任務，自動生成並綁定 Trace ID。
   - 呼叫 `POST /v1/tasks/{task_id}/approve` 核准任務。
   - Worker 成功消費 Kafka 佇列、啟動 Playwright 瀏覽器執行至 `completed`。
   - MinIO / S3 成功寫入截圖 Artifact。
3. **Visual Step Replay 驗證**：
   - 呼叫 `GET /v1/tasks/{task_id}/replay`。
   - 成功獲取 `steps_visual` 共 2 個步驟（`navigate` 與 `screenshot`）。
   - 各步驟皆具備正確之 `duration_ms`、`span_id`、`dom_summary` 及截圖之 `screenshot_artifact_id`。
   - 原始 `timeline` 保留完整的 lifecycle 事件。
4. **跨進程 Trace Inspector 驗證**：
   - 呼叫 `GET /v1/ops/traces/{trace_id}`。
   - 成功跨進程整合記憶體 TraceBuffer 與 DB Task Steps，獲取 3 個階層式 Spans（HTTP Request, Kafka Publish, Worker Execution）。
5. **外部告警通道測試派發**：
   - 呼叫 `POST /v1/ops/alerts/test-dispatch`。
   - 成功觸發非阻塞轉發，並於 `GET /v1/tasks/{task_id}/audit` 查獲 `alert.test_dispatched` 審計紀錄。

---

## 歷史紀錄：V1.1 Compose Production Readiness + OTEL-ready Schema 測試結果

日期：2026-05-23

本次完成 V1.1 第一階段：`/operations` 升級為 `Browser Agent v1.1 Operations Center`、OIDC discovery JWKS fallback、Production Readiness、Observability panel、HTTP correlation middleware、OTEL-ready log schema、HTTP/auth/readiness metrics、`.env.production.example` 與 `docker-compose.prod.yml`。

### Host 測試

Baseline 實作前：

```text
pytest -q
57 passed, 2 warnings in 6.16s
```

V1.1 RED tests：

```text
pytest tests/test_v11_auth_oidc.py tests/test_v11_readiness_observability.py tests/test_v11_operations_ui.py tests/test_v11_compose_config.py -q
9 failed
```

失敗點符合預期，包含 `_fetch_json_url` 尚不存在、readiness 尚未回 `production` / `observability`、correlation header 尚未回寫、Operations UI 尚未顯示 V1.1 panel，以及 production Compose/env 範本尚不存在。

V1.1 targeted tests：

```text
pytest tests/test_v11_auth_oidc.py tests/test_v11_readiness_observability.py tests/test_v11_operations_ui.py tests/test_v11_compose_config.py -q
9 passed, 2 warnings in 1.81s
```

全套 host tests：

```text
pytest -q
66 passed, 2 warnings in 2.78s
```

語法檢查：

```text
python -m compileall src tests worker alembic
exit code 0
```

Diff whitespace：

```text
git diff --check
exit code 0
```

Production-like Compose config：

```text
docker compose --env-file .env.production.example -f docker-compose.prod.yml config
exit code 0
```

Docker CLI 在 sandbox 內讀取 `C:\Users\leohung\.docker\config.json` 時出現 access denied warning；config 仍成功輸出。

### Docker 驗證

第一次在 sandbox 內執行：

```powershell
docker compose up -d --build
```

失敗原因是無法連線 Docker API：

```text
permission denied while trying to connect to the docker API at npipe:////./pipe/docker_engine
```

依權限流程用 escalated Docker access 重跑後成功：

```text
docker compose up -d --build
exit code 0
```

Container pytest：

```text
docker compose exec -T api pytest -q
66 passed in 2.47s
```

### Docker Operations Smoke

執行項目：

- `GET /operations`
- `POST /v1/auth/local-token` for operator
- `GET /v1/ops/readiness`
- `GET /healthz` with `X-Correlation-ID` and `traceparent`

實際結果：

```json
{
  "operationsV11": true,
  "readinessStatus": "ready",
  "productionStatus": "degraded",
  "otelReady": true,
  "correlationHeader": "cid-v11-smoke"
}
```

`productionStatus` 在預設 local Docker Compose stack 中為 `degraded` 是預期結果，因為該 stack 使用 local dev token 與 `APP_ENV=local`；整體 Operations Readiness 仍為 `ready`。Production-like 設定請用 `.env.production.example` / `docker-compose.prod.yml` 做 config smoke。

### V1.1 Test Coverage

- `/operations` render、V1.1 title、Production Readiness、Observability、external bearer token input。
- JWKS URL 優先於 OIDC discovery。
- `AUTH_OIDC_ISSUER_URL` discovery 可解析 `jwks_uri`，malformed discovery 回 `401`。
- Production Readiness 對 local token、default secret、JWKS/OIDC、Redis reliability、Kafka、S3 backend 做 hard checks。
- `X-Correlation-ID` 保留或自動產生，response header 正確回寫。
- W3C `traceparent` 可解析到 request context；V1.1 不產生 fake trace span。
- Production Compose/env 範本包含 V1.1、JWKS、Redis、S3、OTEL-ready defaults。

### 目前限制

- V1.1 是 OTEL-ready schema，不含 OpenTelemetry SDK、OTLP exporter 或 distributed tracing。
- V1.1 支援 OIDC discovery JWKS verifier，但不含完整 login/callback/session flow。
- 尚未做 Kubernetes/Helm、secrets vault、worker autoscaling 或 browser session DOM replay。
- `.env.production.example` 使用 placeholder IdP/secret 值，只適合 config review 與 smoke，不可直接當正式 secrets 使用。

## V1.0 Operations Center 測試結果

日期：2026-05-22

本次完成 V1.0 MVP：Operations Center route、local dev token endpoint、optional JWKS auth、Operations Readiness、S3/MinIO artifact backend、DLQ bulk replay、DLQ quarantine、Replay-lite timeline，以及相關文件同步。

### Host 測試

Baseline 實作前：

```text
pytest -q -> 47 passed, 2 warnings in 5.18s
```

V1.0 RED tests：

```text
10 failed
```

失敗點符合預期，包含 `/operations` 尚不存在、local token endpoint 尚不存在、JWKS/S3/DLQ bulk/replay-lite 尚未實作。

V1.0 targeted tests：

```text
pytest tests/test_v10_operations_ui.py tests/test_v10_auth_jwks.py tests/test_v10_artifacts_s3.py tests/test_v10_dlq_ops.py tests/test_v10_replay.py -q
10 passed, 2 warnings in 2.30s
```

全套 host tests：

```text
pytest -q
57 passed, 2 warnings in 3.29s
```

語法檢查：

```text
python -m compileall src tests worker alembic
exit code 0
```

Diff whitespace：

```text
git diff --check
exit code 0
```

Warnings：

- `pythonjsonlogger.jsonlogger` deprecation warning。
- `.pytest_cache` 寫入 permission warning；測試通過，不影響結果。

### V1.0 Test Coverage

- `/operations` render、V1.0 title、Operations Readiness、Artifact Backend、Bulk DLQ、Replay Timeline panels。
- `/v1/auth/local-token`，舊 token route 不再是入口。
- JWKS mode 驗證 RS256 token，並拒絕 bad issuer/audience/expired/bad roles。
- `S3ArtifactStore` 寫入 governance metadata 並可讀回 bytes。
- Artifact content endpoint 支援 S3 artifact。
- DLQ bulk replay 會 replay pending tasks 並跳過 quarantined tasks。
- DLQ quarantine 寫入 metadata 與 audit。
- Replay-lite endpoint 合併 audit、steps、artifacts、evaluation。

### Docker 驗證

```powershell
docker compose up -d --build
docker compose exec -T api pytest -q
```

第一次 `docker compose exec -T api pytest -q` 逾時，原因是既有 Kafka/Zookeeper stale broker session。Kafka log 顯示：

```text
KeeperErrorCode = NodeExists
```

依 runbook 執行：

```powershell
docker compose restart zookeeper kafka api worker
```

重新執行 container pytest 成功：

```text
57 passed in 2.73s
```

### Docker Operations Smoke

執行項目：

- `GET /operations`
- `POST /v1/auth/local-token` for creator / approver / operator
- `GET /v1/ops/readiness`
- creator `POST /v1/tasks`
- approver `POST /v1/tasks/{task_id}/approve`
- polling operator `GET /v1/tasks/{task_id}`
- operator `GET /v1/tasks/{task_id}/replay`
- operator `GET /v1/tasks/{task_id}/audit`
- operator `GET /v1/artifacts/{artifact_id}/content`
- operator `POST /v1/dlq/tasks/{task_id}/quarantine`
- operator `POST /v1/dlq/tasks/bulk-replay`

實際結果：

```json
{
  "operationsV10": true,
  "readinessStatus": "ready",
  "authMode": "local",
  "artifactBackend": "s3",
  "createdStatus": "pending_approval",
  "approvedStatus": "queued",
  "finalStatus": "completed",
  "artifactCount": 2,
  "firstArtifactBackend": "s3",
  "artifactStatus": 200,
  "artifactContentType": "image/png",
  "replayEvents": 14,
  "auditEvents": 9,
  "dlqCount": 0
}
```

DLQ bulk/quarantine smoke：

```json
{
  "quarantinedStatus": "quarantined",
  "replayedCount": 1,
  "skippedCount": 1,
  "skippedReason": "quarantined",
  "replayedStatus": "queued"
}
```

### 目前限制

- V1.0 有 JWKS verifier，但尚未做完整 IdP login / OIDC discovery flow。
- 尚未做 Kubernetes/Helm、secrets vault、OpenTelemetry tracing。
- Replay-lite 不含 browser session 錄影或 DOM stream。

## 2026-05-23 Architecture image archive and V1.1 refresh

Change scope:
- Renamed the V1.0 architecture image to `DOCS/assets/browseragent-architecture-v1.0.png`.
- Generated the V1.1 architecture image with ChatGPT Image2 and saved it to `DOCS/assets/browseragent-architecture-v1.1.png`.
- Generated a Traditional Chinese V1.1 architecture image with ChatGPT Image2 and saved it to `DOCS/assets/browseragent-architecture-v1.1ch.png`.
- Updated image reference/path notes in `DOCS/ARCHITECTURE.md`, `DOCS/OVERVIEW.md`, and the README technical documentation section.

Commands and results:
- `Test-Path DOCS\assets\browseragent-architecture-v1.0.png` -> `True`
- `Test-Path DOCS\assets\browseragent-architecture-v1.1.png` -> `True`
- `Test-Path DOCS\assets\browseragent-architecture-v1.1ch.png` -> `True`
- `Get-Item DOCS\assets\browseragent-architecture-v1.0.png | Select-Object FullName,Length` -> `Length: 1579844`
- `Get-Item DOCS\assets\browseragent-architecture-v1.1.png | Select-Object FullName,Length` -> `Length: 1442778`
- `Get-Item DOCS\assets\browseragent-architecture-v1.1ch.png | Select-Object FullName,Length` -> `Length: 1498775`
- `git diff --check` -> passed with exit code 0

Limitations:
- No Docker verification was needed because this change only archives a static documentation image and updates Markdown references.
- ChatGPT Image2 can render small text imperfectly; the generated image was visually inspected and kept because it clearly marks V1.1 and matches the current architecture at documentation level.
