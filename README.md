# BrowserAgent

BrowserAgent 是 enterprise browser agent platform 的 **V1.2：Enterprise Session Vault, Task Scheduling, OTLP Streaming & Video Replay**。目前版本把瀏覽器自動化、人工審核、執行紀錄、artifact 保存、失敗任務處理、定時排程巡檢、工作階段保險箱、全行程影片錄製與 production readiness 檢查整合在一起，讓團隊可以用比較接近營運後台的方式管理 browser agent 工作流。

## 一般版

### BrowserAgent 是什麼？

BrowserAgent 可以把「需要人打開網站、登入系統、查資料、截圖、留下證據」這類工作，整理成可以建立、審核、執行、追蹤與回放的任務流程。

它不是單純的瀏覽器腳本，也不是只在工程師電腦上跑一次的測試工具。V1.2 的重點是 **Operations Center + 無人值守排程巡檢 + Session Vault + 視訊回放**：讓 operator 可以在同一個頁面查看系統是否準備好、production-like 設定是否安全、任務目前跑到哪裡、產生了哪些 artifacts、誰核准過、哪一步失敗、失敗任務能不能 replay，必要時也可以 quarantine 問題任務。

簡單說，它適合拿來做「可被人管理的 browser agent」。瀏覽器負責執行重複性網頁操作，人負責審核高風險任務、看結果、追蹤紀錄與處理例外。

### 它解決什麼問題？

很多公司都有一些工作卡在網頁後台、供應商入口、舊系統、SaaS 管理頁或只能用瀏覽器操作的流程裡。這些流程常見問題是：

- 人工操作很重複，但直接全自動又有風險。
- 單純 script 跑完後，很難知道它到底做了什麼、產生了什麼證據。
- 任務失敗時，只看到錯誤訊息，不容易回頭看發生在哪一步。
- 多人協作時，很難確認誰建立任務、誰核准、誰處理失敗任務。
- 工程測試和營運操作分散在不同工具，非工程人員不容易查詢。

BrowserAgent 的設計方向是把這些流程變成可管理的 task lifecycle。使用者可以建立 browser task，依風險進入 `pending_approval`，核准後由 worker 執行；執行結果會留下 screenshot、HTML 或其他 artifacts，也會留下 audit、metrics、step output 與 replay-lite timeline。

因此它比一般瀏覽器自動化更適合用在營運型工作流：不是只問「能不能跑」，也要能回答「誰讓它跑、跑了什麼、結果在哪、失敗後怎麼處理」。

### Operations Center 可以看到什麼？

V1.2 的主要入口是：

```text
http://localhost:8000/operations
```

Operations Center 目前可以用來：

- 建立 browser task，並查看任務狀態、風險等級、correlation id 與執行結果。
- 對需要人工確認的任務做 approve，再交給 worker 執行。
- 查看 Operations Readiness，確認 DB、Kafka、artifact backend、worker identity、DLQ topic 與 auth mode 是否正常。
- 查看 Production Readiness，確認 production Compose 設定是否關閉 local token、使用 JWKS/OIDC、Redis reliability、Kafka 與 S3 artifact backend。
- 查看 Observability，確認 OTEL-ready 設定、log correlation schema、`X-Correlation-ID` 與 `traceparent` 預留狀態。
- 查看 artifacts，例如 screenshot 或 HTML，並確認它們是存在 local filesystem 還是 MinIO/S3 backend。
- 查看 audit logs，知道任務是誰建立、誰核准、誰 replay 或 quarantine。
- 查看 metrics 與 reliability 狀態，協助判斷系統目前是否健康。
- 查看 DLQ 任務，對失敗任務做單筆 replay、bulk replay，或把 poison task quarantine 起來。
- 查看 Replay Timeline，把 audit、steps、artifacts、evaluation 串成可查詢的事件時間線。
- 查看 Planner / SkillHub 的解析狀態，理解任務在執行前如何被驗證與補充 metadata。

### 適用情境

以下是 BrowserAgent 可以應用的方向。這些是「可應用場景」，不是代表目前已內建每個產業的完整流程；實際導入時仍要依系統權限、資料敏感度、風險控管與公司政策調整。

- 製造業：查供應商入口、下載或截圖交期資訊、查工單狀態、巡檢設備網頁系統、保留檢驗資料畫面與操作紀錄。
- 金融業：查內部後台資料、輔助報表頁面核對、保留合規查詢證據、建立需要人工核准的低風險查詢流程；不建議直接用來執行轉帳、交易、放款核准等高風險動作。
- 零售業：檢查商品頁是否正常、比對價格或庫存頁面、查訂單後台狀態、保存促銷頁或商品異常畫面。
- 資訊服務業：做 SaaS 後台 smoke test、客戶環境巡檢、維運前後狀態截圖、協助客服或 SRE 快速確認系統頁面是否正常。
- 醫療業：輔助非診斷性的行政流程，例如預約頁查詢、院內表單狀態檢查、系統畫面截圖留存；不取代醫師診斷、醫療判斷或臨床決策。
- 旅遊業：查訂房或票務後台狀態、核對行程資料、保存供應商頁面畫面、協助客服確認訂單或異常狀況。
- 物流業：查貨態後台、保存配送異常畫面、核對承運商入口資料、追蹤批次查詢任務是否失敗。
- 教育訓練：檢查 LMS 課程頁、學員後台或作業繳交狀態，保存教學平台操作證據。
- 法務與合規：保存指定頁面的截圖、HTML 與查詢紀錄，協助建立可追溯的查證流程；法律結論仍需由專業人員判斷。
- 客服中心：協助客服查詢多個後台頁面、保留處理紀錄、把重複查詢流程轉成可審核任務。
- 政府與公共服務：查詢公開或內部行政系統狀態、保存流程證據、協助例行巡檢。
- 研究資料蒐集：對授權網站做頁面查詢、截圖與資料留存，協助整理重複性研究流程。

### 目前不適用的情境

BrowserAgent 目前還不是可以放心接管所有網頁操作的完整平台。以下情境目前不適合使用，或必須加入額外的人為審核與安全控管：

- 不適合直接執行金流轉帳、證券交易、下單採購、放款核准、保險核保、醫療診斷、法律判斷等高風險決策。
- 不適合繞過網站權限、CAPTCHA、反爬蟲機制、付費牆、使用者同意或服務條款。
- 不適合處理未授權的個資、病歷、財務資料、客戶機密、商業秘密或大量敏感資料。
- 不適合拿來做大規模外部網站抓取、競品監控或任何可能造成對方服務負載的行為，除非已取得明確授權。
- 不適合當成完整 RPA 平台；它目前聚焦在 browser agent task、審核、紀錄、artifact 與營運回放。
- 不適合當成完整企業登入系統；V1.2 支援 local dev token、JWKS token 驗證與 OIDC discovery，但不包含完整 IdP login flow。
- 不適合當成正式 secrets vault、完整資安控管平台或全代管雲端平台。

### V1.2 目前限制

- 目前提供 Docker Compose 與 Kubernetes Kustomize 生產配置，正式雲端上線仍需搭配企業專屬之 ingress 與 secret 管理機制。
- `/operations` 是 V1.2 的營運入口；它可以查詢與操作核心流程，不等於完整企業級大型後台。
- local dev token 只適合本機開發與測試；production-like 設定應使用 `AUTH_MODE=jwks`，並搭配 `AUTH_JWKS_URL` 或 `AUTH_OIDC_ISSUER_URL`。
- Replay Timeline 提供 audit、steps、artifacts、evaluation 與 WebM 視訊回放，視訊錄影需注意磁碟空間與 retention policy。
- Artifact backend 支援 local 與 MinIO/S3；retention、redaction 目前以 metadata 與生命週期標記表達。
- Planner 目前偏 Heuristic 驗證與 metadata 補強，不是完整外部 LLM agent planner。
- SkillHub 目前聚焦 resolver metadata，不代表已經能安全執行任意第三方 skill。
- 高風險操作仍應保留人為審核、權限分層、測試環境驗證與公司內部安全流程。

### 快速啟動

```powershell
copy .env.example .env
docker compose up -d --build
```

Operations Center：

```text
http://localhost:8000/operations
```

Health check：

```powershell
curl.exe http://localhost:8000/healthz
curl.exe http://localhost:8000/readyz
```

## 技術版

### 主要能力

- **FastAPI Control Plane**：Auth、task、approval、artifact、SkillHub、readiness、alerts、traces、DLQ、scheduled tasks、session vault、video replay、OTLP exporter APIs。
- **Scheduled Tasks 調度引擎**：標準 5 欄位 Cron 表達式解析、分散式 Redis 鎖（TTL 55s）、任務防重入（concurrency_policy: skip/allow）、手動立即觸發與背景自動巡檢。
- **Session Vault (Storage State)**：Playwright Cookies 與 localStorage 狀態封裝為 `storage_state` Artifact，自動跨任務注入免重複登入、租戶隔離、狀態過期與一鍵撤銷保護。
- **Video Replay 全行程視訊錄製**：Playwright WebM 全螢幕執行錄影，自動持久化至 ArtifactStore，Operations Center 內建 HTML5 播放器與 `/v1/tasks/{id}/video` 即時串流。
- **OpenTelemetry OTLP Exporter**：背景非同步 Batch Span Exporter，支援標準 OTLP HTTP/JSON 協議串流推送 Spans 至外部 APM（Jaeger、Datadog、OpenTelemetry Collector），附帶隊列丟棄保護與即時狀態監控。
- **Kubernetes 生產 Manifests 套件與 KEDA**：提供完整 `deploy/k8s/` 生產套件（API、Worker、ConfigMap、Secret、Ingress），以及依 Kafka Topic Lag 自動水平擴展 Worker Pod 的 KEDA ScaledObject 藍圖。
- **Auth/RBAC**：local HS256 dev token、JWKS RS256 verifier 與 OIDC discovery 取得 `jwks_uri`。
- **Roles**：`creator`、`approver`、`operator`、`admin`。
- **Distributed Tracing**：W3C `traceparent` Context 傳播、Span 生命週期管理、環形記憶體 TraceBuffer、跨進程 Trace Inspector。
- **Production Alerting Center**：7 大維運規則即時評估、外部 Webhook（Slack/Discord）非阻塞非同步轉發、手動測試派發通道與審計日誌。
- **Visual Step Replay**：步驟分頁導航條、點選即時預覽截圖縮圖、DOM 摘要與毫秒級步驟執行耗時分析。
- **Reliability**：Redis/memory rate limit、idempotency、worker lock、scheduler lock、DLQ metadata。
- **Artifacts**：local filesystem 或 MinIO/S3 backend，包含 SHA-256、content type、size、retention、redaction metadata。
- **Operations**：`/operations` 整合 Task Lifecycle、Scheduled Tasks、Session Vault、Video Replay、Production Alerting、Trace Inspector、Visual Step Replay、Production Readiness、Observability、artifact access、bulk DLQ。
- **Worker**：Kafka consumer、Playwright runner、service identity、retry/DLQ、video capture、session persistence。

### 取得 local dev token

```powershell
$token = Invoke-RestMethod -Method Post `
  -Uri http://localhost:8000/v1/auth/local-token `
  -ContentType "application/json" `
  -Body '{"role":"creator"}'
```

### 建立 Task

```powershell
curl.exe -X POST http://localhost:8000/v1/tasks `
  -H "Authorization: Bearer $($token.access_token)" `
  -H "Content-Type: application/json" `
  -H "Idempotency-Key: capture-example-001" `
  -d '{
    "title":"Capture example",
    "instructions":"Open the allowlisted site and capture a screenshot.",
    "priority":1,
    "risk_level":"low",
    "metadata":{
      "domains":["example.com"],
      "start_url":"https://example.com",
      "expected_domain":"example.com"
    }
  }'
```

### 基本測試

```powershell
pytest -q
python -m compileall src tests worker alembic
git diff --check
```

Docker 可用時：

```powershell
docker compose exec -T api pytest -q
```

Kubernetes Manifests 驗證：

```powershell
kubectl kustomize deploy/k8s/
```

Production-like Compose config 可審查：

```powershell
docker compose --env-file .env.production.example -f docker-compose.prod.yml config
```

實際測試結果請看 [DOCS/TEST_REPORT.md](DOCS/TEST_REPORT.md)。

### 文件

- [DOCS/OVERVIEW.md](DOCS/OVERVIEW.md)
- [DOCS/API.md](DOCS/API.md)
- [DOCS/ARCHITECTURE.md](DOCS/ARCHITECTURE.md)
  - 架構圖資產：繁中版 `DOCS/assets/browseragent-architecture-v1.2ch.png`、英文版 `DOCS/assets/browseragent-architecture-v1.2en.png`
- [DOCS/CONFIGURATION.md](DOCS/CONFIGURATION.md)
- [DOCS/DATA_MODEL.md](DOCS/DATA_MODEL.md)
- [DOCS/OBSERVABILITY.md](DOCS/OBSERVABILITY.md)
- [DOCS/ROADMAP.md](DOCS/ROADMAP.md)
- [DOCS/RUNBOOK.md](DOCS/RUNBOOK.md)
- [DOCS/SECURITY_AND_POLICY.md](DOCS/SECURITY_AND_POLICY.md)
- [DOCS/USE_CASES.md](DOCS/USE_CASES.md)
- [DOCS/DEVELOPMENT.md](DOCS/DEVELOPMENT.md)
- [DOCS/manual_test.md](DOCS/manual_test.md)
- [DOCS/TEST_REPORT.md](DOCS/TEST_REPORT.md)
