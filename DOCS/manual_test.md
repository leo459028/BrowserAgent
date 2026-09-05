# V1.4 Operations Center Manual Test

本文件說明如何手動驗證 BrowserAgent V1.4 Operations Center（維運中心）。

## 啟動與環境準備

```powershell
docker compose up -d --build
```

執行資料庫遷移（包含 V1.4 `0004_v14_federation_and_matrix`）：
```powershell
docker compose exec -T api alembic upgrade head
```

開啟瀏覽器進入 Operations Center：

```text
http://127.0.0.1:8000/operations
```
> **提示**：系統具備自動容錯轉址，無論輸入 `http://localhost:8000/operations`、`http://localhost:8000/operation` 或首頁根路徑 `http://localhost:8000/`，皆會自動重定向至 Operations Center。

---

## 介面頂部指標與狀態徽章導覽

開啟頁面後，頂部標題與狀態導覽列呈現最新系統指標：
- **版本標題**：顯示 `Browser Agent v1.4 Operations Center (維運中心)`，並保留向下相容提示文字（`Browser Agent v1.2 Operations Center compatible`）。
- **DLP Shield 徽章**（`#dlp-shield-badge`）：指示 Zero-Trust 動態資料防洩狀態（綠色 `DLP Shield: Active`）。
- **Cluster Federation 徽章**（`#cluster-fed-badge`）：指示多叢集排程同盟與租約狀態（綠色 `Cluster: Federation Online`）。
- **SSO Login 按鈕**：右上角醒目的 `SSO Login with IdP` 按鈕，支援一鍵發起 PKCE 授權碼登入流程。
- **System Alert Badge**：即時呈現系統健康狀態（如綠色 `All Systems Normal` 或黃色 `Alerting`）。
- **Vault KMS Badge**：指示目前 Session Vault KMS 加密狀態（如 `Vault: KMS (AES-256-GCM)`）。
- **K8s Badge**：指示目前執行環境是否位於 Kubernetes 叢集內部（`Platform: K8s/Helm Ready`）。
- **OTLP Badge**：指示 OpenTelemetry OTLP Batch Span Exporter 狀態（`OTLP: Ready`）。
- **身分與角色切換區塊**：可於 `Identity / RBAC (身份認證與角色權限)` 快速切換 `creator`、`approver`、`operator`、`admin` 四大角色測試權限隔離。


---

## 完整人工測試流程（Step-by-Step UI Guide）

### 步驟 1：建立帶有指定核心或矩陣派發之任務（Create Task & Matrix Dispatch）
1. 捲動至左側中段的 **`Create Task (建立任務)`** 卡片。
2. 於 `Scenario` 下拉選單選擇 `Normal planner task`。
3. **選擇瀏覽器核心**：透過 **`Browser Engine (執行核心)`** 下拉選單（`#browser-engine-select`），可選擇 `Chromium (Default)`、`Firefox` 或 `WebKit`。
4. **確認 Zero-Trust DLP 防護**：確保核取方塊 **`Zero-Trust Dynamic DLP Masking & Redaction`**（`#dlp-toggle`）為勾選狀態。
5. **單一任務建立**：點擊深綠色的 **`Create task`** 按鈕，建立單一指定核心之任務。
6. **一鍵跨瀏覽器矩陣派發**：亦可直接點選深藍色的 **`Dispatch Matrix (3 Engines)`** 按鈕（`#create-matrix-task`），系統自動平行生成 Chromium、Firefox、WebKit 三筆任務並共享同一 `matrix_id`。

### 步驟 2：觀察待審核狀態與審批按鈕啟用
1. 任務建立成功後，左下角的 **`Recent Tasks (近期任務)`** 列表頂部會出現新任務，狀態標籤顯示為黃色的 **`PENDING_APPROVAL`**。
2. 點選該任務，右上方 **`Task Detail (任務詳情)`** 會更新其任務詳情（包含 Browser Engine 與 Matrix ID 屬性）。
3. 此時，右上角的 **`Approve selected`** 按鈕會**立即由灰色鎖定狀態切換為亮綠色啟用狀態**（滑鼠懸停顯示「Click to approve this task」）。

### 步驟 3：人工審批與多優先佇列分流觀察（Priority Queues）
1. 點擊右上角亮綠色的 **`Approve selected`** 按鈕進行審核。
2. 任務狀態會即時躍遷：`queued` ➜ `executing`。
3. 檢視左側的 **`Queues & Worker Pools (佇列與工作進程池)`** 卡片：
   - 任務依據優先權權重自動被路由分流至對應的 Kafka 主題（`agent.tasks.high`、`agent.tasks.queued` 或 `agent.tasks.batch`）。
   - 專屬 Worker 資源池即時拉取任務並根據指定之 `browser_engine` 喚起對應之 Playwright 實體。

### 步驟 4：雙向即時遠端接管與人機協作（HITL Reverse Control）
1. 當任務狀態處於 `executing` 時，右側的 **`Live Screen Broadcast (WebSocket Telemetry)`** 卡片自動建立 WebSocket 連線（`WS /v1/tasks/{id}/live-stream`）並以 2 FPS 渲染當前網頁畫面。
2. **切換進入接管模式（Pause）**：
   - 點擊卡片頂部橘色的 **`Pause (Takeover)`** 按鈕（`#btn-pause-takeover`）。
   - 接管狀態徽章（`#takeover-status-pill`）即時切換為橘色的 **`PAUSED (TAKEOVER)`**，Worker 暫停自動化腳本推進。
3. **滑鼠座標遠端點擊（Canvas Click）**：
   - 直接在畫面 Canvas 上點選目標網頁按鈕或核取方塊位置。
   - 前端自動計算相對於原始視窗的座標（X, Y），調用 `POST /v1/tasks/{id}/interact` 下發 `action: click`，Worker 即時調用 Playwright 注入點擊。
4. **鍵盤按鍵與文字注入（Remote Key Input）**：
   - 在 **`Remote Key Input`** 輸入框（`#remote-key-input`）鍵入欲輸入的文字或驗證碼（例如 `CAPTCHA_PASS_77`）。
   - 點擊藍色的 **`Send Keys`** 按鈕（`#btn-send-keys`），系統下發 `action: type` 指令至執行中瀏覽器。
5. **恢復自動化推進（Resume）**：
   - 人工干預完成後，點擊綠色的 **`Resume Task`** 按鈕（`#btn-resume-takeover`）。
   - Worker 退出暫停狀態繼續推進後續步驟，系統自動將人機介入總秒數與操作者身分寫入 `task.human_intervened = True` 與 Audit Log。

### 步驟 5：驗證跨瀏覽器矩陣比對看板（Cross-Browser Matrix Comparison）
1. 檢視底部的 **`Cross-Browser Matrix Comparison`** 面板（`#matrix-comparison-section`）。
2. 在 Matrix ID 查詢框輸入矩陣批次號，點擊 **`Compare Matrix`**。
3. 面板即時並列展示三大瀏覽器核心（Chromium / Firefox / WebKit）的執行結果：
   - 各核心之執行狀態（`completed` / `failed`）
   - 總執行耗時（ms）對比
   - 評估 Verdict（`pass` / `fail`）與分數（Score）
   - 是否發生 DOM 選擇器自癒（Self-Healed）
   - 是否套用 DLP 資料防洩遮罩（DLP Masked）
   - 是否有人工介入（Human Intervened）

### 步驟 6：驗證 Zero-Trust DLP 動態防洩與像素遮罩（Zero-Trust DLP）
1. 檢視底部的 **`Zero-Trust Dynamic DLP Status`** 面板（`#dlp-section`）。
2. 面板展示當前動態防洩服務狀態（`active`）、作用中正則規則清單（`password_kv`、`bearer_token`、`jwt_pattern`、`openai_api_key`、`aws_access_key`、`credit_card` 等）。
3. 觀察 Live Stream 畫布或下載截圖 Artifact：
   - 頁面中的密碼輸入框（`input[type="password"]`）均被注入高斯模糊遮罩（`filter: blur(8px)`），像素無法辨識。
   - 任務 Metadata 與日誌中的機密 Token 與 API Keys 皆已替換為 `[REDACTED_TOKEN]` 或 `sk-[REDACTED_KEY]`。

### 步驟 7：驗證多叢集排程同盟與容災接管（Federation Topology & Failover）
1. 檢視底部的 **`Multi-Cluster Scheduling Federation Topology`** 面板（`#federation-section`）。
2. 面板即時呈現各排程節點之地理區域（Region）、心跳秒數差、活躍排程數與當前 Leader 標籤。
3. **容災切換演練（Force Re-election）**：
   - 點選備援節點旁的 **`Force Re-election`** 按鈕（呼叫 `POST /v1/ops/federation/re-election`）。
   - 系統即時將 Leader 租約強制轉移至備援節點，Leader 標籤即刻更新，驗證跨區域零停機容災接管能力。

### 步驟 8：驗證全行程視訊錄影播放（Full Video Replay）
1. 若任務啟用錄影，右上方會顯示 **`Full WebM Video Recording (Playwright)`** 播放器卡片。
2. 播放器自動掛載 WebM 視訊來源（端點為 `/v1/artifacts/{video_artifact_id}/content`）。
3. 點擊播放按鈕，即可全螢幕或在卡片內觀看 Playwright 瀏覽器操作過程的動態錄影，支援暫停、播放與拖曳進度條。

### 步驟 9：驗證 Session Vault KMS 信封加密與一鍵 Validate / Revoke
1. 檢視右下側的 **`Session Vault (Storage State)`** 卡片。
2. 點擊 **`Refresh`** 載入所有已保存的 `storage_state` 憑證。
3. **一鍵解密完整性校驗**：點擊該憑證旁的 **`Validate`** 按鈕，驗證 KMS 解密迴路與 AAD 租戶完整性校驗。
4. **一鍵強制撤銷**：點選 **`Revoke`** 按鈕確認撤銷，狀態立即更新為 **`revoked`**。

### 步驟 10：驗證定時巡檢排程調度（Scheduled Tasks）
1. 檢視右側中段的 **`Scheduled Tasks (Cron Engine)`** 卡片。
2. 建立新定時排程（Cron 表達式如 `0 9 * * *`）。
3. 點選該排程項目旁的 **`Run Now`**，系統立即派發出全新關聯任務。

### 步驟 11：驗證端到端分散式追蹤與告警中心
1. 複製任務之 **`Trace ID`**，貼入左側 **`Trace Inspector`** 輸入框並點擊 **`Lookup`**，檢視 Span 樹狀追蹤圖。
2. 在左側 **`Production Alerting Center`** 卡片中，點擊 **`Test Dispatch`** 按鈕，輸入備註發送非阻塞測試 Webhook。

### 步驟 12：驗證 Enterprise OIDC SSO 登入與角色隔離（Identity & RBAC）
1. 點擊頂部藍色的 **`SSO Login (OIDC)`** 按鈕，驗證 PKCE 授權跳轉與 HttpOnly `ba_session` Cookie 寫入。
2. 在頂部 Identity 區塊切換身分角色（`creator`, `approver`, `operator`, `admin`），測試端點角色防護隔離。


---

## 常見 UI 疑問與機制說明（FAQ）

### Q1：右上角的 `Approve selected` 按鈕是灰色的，點不下去是正常的嗎？
**答：完全正常！這是系統安全防護設計。**
- `Approve selected` 專門用於審批狀態為 **`pending_approval`（待審核）** 的任務。
- 當尚未選中任務，或目前選中的任務已經是 **`COMPLETED`**、`FAILED`、`QUEUED` 時，系統會自動禁用（disabled 變灰）該按鈕，避免維運人員對非審批中任務重複點擊核准。

### Q2：雙向接管控制條（`Pause`, `Resume`, `Send Keys`）按鈕何時可以使用？
**答：**
- 只有當前選中的任務處於 **`executing`（執行中）** 狀態時，`Pause (Takeover)` 按鈕才會啟用。
- 點擊暫停進入接管狀態後，接管狀態徽章轉為橘色 **`PAUSED (TAKEOVER)`**，此時畫布點擊（Canvas Click）、按鍵輸入框（`Remote Key Input`）、`Send Keys` 與 `Resume Task` 按鈕皆完全啟用。
- 點擊恢復或任務結束後，按鈕會自動恢復防呆鎖定。

### Q3：`Dispatch Matrix (3 Engines)` 矩陣任務與單一任務有什麼差別？
**答：**
- 單一任務只針對當前下拉選單選中之瀏覽器核心（如 `firefox`）建立一個 Task。
- `Dispatch Matrix (3 Engines)` 會自動為 Chromium、Firefox、WebKit 各建立一筆獨立任務，賦予相同的 `matrix_id`，並在下方 `Cross-Browser Matrix Comparison` 面板聚合分析跨核心渲染差異與相容性。

### Q4：Zero-Trust DLP 遮罩會影響自動化腳本抓取元素嗎？
**答：完全不會！**
- DLP 採用前端 CSS 像素渲染遮罩（`filter: blur(8px)`）與輸出端文字脫敏，Playwright 底層與 DOM 樹之屬性（如 input value 或 selector）依然保持正常運作，既保護視覺影像隱私，又不干擾自動化邏輯。

### Q5：多叢集同盟的 Leader 節點斷線時會發生什麼事？
**答：系統具備自動容災接管（DR Failover）機制！**
- Leader 節點必須每 5 秒刷新租約（TTL 15 秒）。若 Leader 心跳逾期停止刷新，備援叢集節點在下次心跳週期將自動晉升為新 Leader，無縫接管所有定時排程巡檢任務，無單點故障風險。

---

## 最小合格檢查清單（Checklist）

- [ ] 頁面頂部顯示 `Browser Agent v1.4 Operations Center (維運中心)`，右上角帶有 `DLP Shield: Active` 徽章、`Cluster: Federation Online` 徽章、`Alert Badge`、`K8s Badge`、`OTLP Badge` 與 `SSO Login` 按鈕。
- [ ] `Create Task` 卡片提供 `Browser Engine` 核心下拉選單（Chromium, Firefox, WebKit）、`DLP Toggle` 與 `Dispatch Matrix (3 Engines)` 矩陣派發按鈕。
- [ ] `Live Telemetry Stream` 卡片於任務執行時流暢廣播畫面，提供雙向接管控制條（`Pause (Takeover)`, `Resume Task`, `Send Keys`, `Key Input`, `Takeover Status`）與 `Abort Task` 按鈕。
- [ ] 支援在即時畫面畫布上點選座標並發送 `click` 動作，支援在輸入框填寫文字發送 `type` 動作。
- [ ] `Cross-Browser Matrix Comparison` 面板可查詢並展示跨 Chromium/Firefox/WebKit 之耗時、Verdict 與自癒表現差異。
- [ ] `Zero-Trust Dynamic DLP Status` 面板可查詢動態遮罩與脫敏規則清單，且密碼輸入框在畫面與截圖中確實呈現高斯模糊。
- [ ] `Multi-Cluster Scheduling Federation Topology` 面板可檢視跨區域排程節點心跳與 Leader 租約，支援點擊 `Force Re-election` 強制轉移主導權。
- [ ] `Priority Queues Telemetry` 卡片可顯示 High、Queued、Batch 深度與 Worker Pool 狀態。
- [ ] `KMS Envelope Encryption Engine` 卡片顯示 Provider、Key ID 與加解密迴路延遲。
- [ ] `Visual Step Replay` 於自癒情境可正確顯示綠色 `Self-Healed ✓` 徽章，人機介入任務顯示介入審計與總耗時。
- [ ] `Session Vault` 卡片支援檢視 KMS 標籤、一鍵 `Validate` 憑證校驗與一鍵 `Revoke` 撤銷。
- [ ] `Scheduled Tasks` 卡片支援建立排程、`Run Now` 立即派發與 `Pause/Resume` 暫停恢復。
- [ ] `Execution Video Recording` 播放器可加載並播放 WebM 瀏覽器操作錄影。
- [ ] `Production Alerting Center` 顯示 7 大規則狀態指標，支援管理員點選 `Test Dispatch` 發送測試 Webhook。
- [ ] `Trace Inspector` 輸入 Trace ID 可展開階層式 Spans 追蹤樹。
- [ ] `Identity / RBAC` 可切換角色並正確落實權限隔離（creator, approver, operator, admin）。
- [ ] `Normal planner task` 可建立（pending_approval）、核准（queued）、完成（completed）。
- [ ] `Refresh DLQ` 可查 failed tasks，`Bulk DLQ replay` 可操作 non-quarantined tasks。

---

## API 快速自動化檢查（PowerShell 腳本）

可在 PowerShell 中直接執行以下腳本，一鍵驗證 V1.4 核心端點：

```powershell
# 1. 取得各角色 Token
$operator = Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/v1/auth/local-token -ContentType "application/json" -Body '{"role":"operator"}'
$creator = Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/v1/auth/local-token -ContentType "application/json" -Body '{"role":"creator"}'
$approver = Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/v1/auth/local-token -ContentType "application/json" -Body '{"role":"approver"}'
$admin = Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/v1/auth/local-token -ContentType "application/json" -Body '{"role":"admin"}'

$opHeaders = @{ Authorization = "Bearer $($operator.access_token)" }
$creatorHeaders = @{ Authorization = "Bearer $($creator.access_token)" }
$approverHeaders = @{ Authorization = "Bearer $($approver.access_token)" }
$adminHeaders = @{ Authorization = "Bearer $($admin.access_token)" }

# 2. 檢驗 V1.4 DLP 狀態與多叢集同盟拓撲
$dlpStatus = Invoke-RestMethod -Method Get -Uri http://127.0.0.1:8000/v1/ops/dlp/status -Headers $opHeaders
Write-Host "DLP Status: $($dlpStatus.status), Active Rules: $($dlpStatus.active_rules.Count)" -ForegroundColor Cyan

$fedNodes = Invoke-RestMethod -Method Get -Uri http://127.0.0.1:8000/v1/ops/federation/nodes -Headers $opHeaders
Write-Host "Cluster Status: $($fedNodes.cluster_status), Leader Node: $($fedNodes.leader_node_id)" -ForegroundColor Cyan

# 3. 建立單一 Firefox 核心瀏覽器任務
$ffTaskBody = @{
    title = "Firefox Rendering Verification"
    instructions = "Navigate to allowlisted site and verify layout"
    browser_engine = "firefox"
    priority = 1
    risk_level = "low"
    metadata = @{
        domains = @("example.com")
        start_url = "https://example.com"
    }
} | ConvertTo-Json
$ffTask = Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/v1/tasks -Headers $creatorHeaders -ContentType "application/json" -Body $ffTaskBody
Write-Host "Created Task ID: $($ffTask.task_id), Engine: $($ffTask.browser_engine)" -ForegroundColor Green

# 4. 驗證雙向遠端接管 API (Pause / Interact / Resume)
$pauseRes = Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/v1/tasks/$($ffTask.task_id)/pause" -Headers $opHeaders -ContentType "application/json" -Body '{"reason":"Manual Inspection"}'
Write-Host "Task Paused for HITL: $($pauseRes.paused)" -ForegroundColor Yellow

$interactRes = Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/v1/tasks/$($ffTask.task_id)/interact" -Headers $opHeaders -ContentType "application/json" -Body '{"action":"click","x":150.0,"y":200.0}'
Write-Host "Action Queued: $($interactRes.queued)" -ForegroundColor Yellow

$resumeRes = Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/v1/tasks/$($ffTask.task_id)/resume" -Headers $opHeaders
Write-Host "Task Resumed: $($resumeRes.resumed)" -ForegroundColor Green

# 5. 一鍵派發跨瀏覽器矩陣任務 (Chromium, Firefox, WebKit)
$matrixBody = @{
    title = "E2E Cross-Browser Matrix Suite"
    instructions = "Verify form layout and submission across all 3 engines"
    engines = @("chromium", "firefox", "webkit")
    priority = 1
    risk_level = "low"
    metadata = @{
        domains = @("example.com")
        start_url = "https://example.com"
    }
} | ConvertTo-Json
$matrixRes = Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/v1/tasks/matrix -Headers $creatorHeaders -ContentType "application/json" -Body $matrixBody
Write-Host "Matrix Dispatched! Matrix ID: $($matrixRes.matrix_id), Total Tasks: $($matrixRes.total_tasks)" -ForegroundColor Cyan

# 6. 查詢矩陣聚合結果
$matrixSummary = Invoke-RestMethod -Method Get -Uri "http://127.0.0.1:8000/v1/tasks/matrix/$($matrixRes.matrix_id)" -Headers $opHeaders
Write-Host "Matrix Tasks Count: $($matrixSummary.tasks.Count)" -ForegroundColor Green

Write-Host "V1.4 API Verification Completed Successfully!" -ForegroundColor Green
```
