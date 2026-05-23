# BrowserAgent

BrowserAgent 是 enterprise browser agent platform 的 **V1.0 MVP：Operations Center**。目前版本把瀏覽器自動化、人工審核、執行紀錄、artifact 保存與失敗任務處理整合在一起，讓團隊可以用比較接近營運後台的方式管理 browser agent 工作流。

## 一般版

### BrowserAgent 是什麼？

BrowserAgent 可以把「需要人打開網站、登入系統、查資料、截圖、留下證據」這類工作，整理成可以建立、審核、執行、追蹤與回放的任務流程。

它不是單純的瀏覽器腳本，也不是只在工程師電腦上跑一次的測試工具。V1.0 MVP 的重點是 **Operations Center**：讓 operator 可以在同一個頁面查看系統是否準備好、任務目前跑到哪裡、產生了哪些 artifacts、誰核准過、哪一步失敗、失敗任務能不能 replay，必要時也可以 quarantine 問題任務。

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

V1.0 的主要入口是：

```text
http://localhost:8000/operations
```

Operations Center 目前可以用來：

- 建立 browser task，並查看任務狀態、風險等級、correlation id 與執行結果。
- 對需要人工確認的任務做 approve，再交給 worker 執行。
- 查看 Operations Readiness，確認 DB、Kafka、artifact backend、worker identity、DLQ topic 與 auth mode 是否正常。
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

BrowserAgent V1.0 MVP 還不是可以放心接管所有網頁操作的完整平台。以下情境目前不適合使用，或必須加入額外的人為審核與安全控管：

- 不適合直接執行金流轉帳、證券交易、下單採購、放款核准、保險核保、醫療診斷、法律判斷等高風險決策。
- 不適合繞過網站權限、CAPTCHA、反爬蟲機制、付費牆、使用者同意或服務條款。
- 不適合處理未授權的個資、病歷、財務資料、客戶機密、商業秘密或大量敏感資料。
- 不適合拿來做大規模外部網站抓取、競品監控或任何可能造成對方服務負載的行為，除非已取得明確授權。
- 不適合當成完整 RPA 平台；它目前聚焦在 browser agent task、審核、紀錄、artifact 與營運回放。
- 不適合當成完整企業登入系統；V1.0 支援 local dev token 與可選 JWKS token 驗證，但不包含完整 IdP login flow。
- 不適合當成正式 secrets vault、完整資安控管平台、Kubernetes/Helm 部署平台或瀏覽器影片錄製平台。

### V1.0 MVP 目前限制

- 目前主要驗證環境是本機與 Docker Compose，還不是完整雲端 production deployment。
- `/operations` 是 V1.0 的營運入口，但仍是 MVP；它可以查詢與操作核心流程，不等於完整企業級後台。
- local dev token 只適合本機開發與測試；正式環境應使用 `AUTH_MODE=jwks` 並串接企業既有身分系統。
- Replay-lite 是由 audit、steps、artifacts、evaluation 組成的 timeline，不是完整瀏覽器錄影，也不是 DOM stream。
- Artifact backend 支援 local 與 MinIO/S3；retention、redaction 目前主要以 metadata 表達，尚未等同完整資料生命週期治理。
- Planner 目前偏 MVP 驗證與 metadata 補強，不是完整外部 LLM agent planner。
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

- FastAPI control plane：Auth、task、approval、artifact、SkillHub、readiness、DLQ、replay APIs。
- Auth/RBAC：local HS256 dev token 與 optional JWKS RS256 verifier。
- Roles：`creator`、`approver`、`operator`、`admin`。
- Reliability：Redis/memory rate limit、idempotency、worker lock、DLQ metadata。
- Artifacts：local filesystem 或 MinIO/S3 backend，包含 SHA-256、content type、size、retention、redaction metadata。
- Operations：`/operations` 可操作 task lifecycle、readiness、artifact access、bulk DLQ、Replay-lite timeline。
- Worker：Kafka consumer、Playwright runner、service identity、retry/DLQ。

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

實際測試結果請看 [DOCS/TEST_REPORT.md](DOCS/TEST_REPORT.md)。

### 文件

- [DOCS/OVERVIEW.md](DOCS/OVERVIEW.md)
- [DOCS/API.md](DOCS/API.md)
- [DOCS/ARCHITECTURE.md](DOCS/ARCHITECTURE.md)
  - 架構圖資產：`DOCS/assets/browseragent-architecture.png`
- [DOCS/CONFIGURATION.md](DOCS/CONFIGURATION.md)
- [DOCS/DATA_MODEL.md](DOCS/DATA_MODEL.md)
- [DOCS/RUNBOOK.md](DOCS/RUNBOOK.md)
- [DOCS/SECURITY_AND_POLICY.md](DOCS/SECURITY_AND_POLICY.md)
- [DOCS/USE_CASES.md](DOCS/USE_CASES.md)
