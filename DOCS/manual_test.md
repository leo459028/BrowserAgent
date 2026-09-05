# V1.3 Operations Center Manual Test

本文件說明如何手動驗證 BrowserAgent V1.3 Operations Center。

## 啟動與環境準備

```powershell
docker compose up -d --build
```

開啟瀏覽器進入 Operations Center：

```text
http://127.0.0.1:8000/operations
```
> **提示**：系統具備自動容錯轉址，無論輸入 `http://localhost:8000/operations`、`http://localhost:8000/operation` 或首頁根路徑 `http://localhost:8000/`，皆會自動重定向至 Operations Center。

---

## 介面頂部指標與狀態徽章導覽

開啟頁面後，頂部標題與狀態導覽列呈現最新系統指標：
- **版本標題**：顯示 `Browser Agent v1.3 Operations Center (維運中心)`。
- **SSO Login 按鈕**：右上角醒目的 `SSO Login with IdP` 按鈕，支援一鍵發起 PKCE 授權碼登入流程。
- **System Alert Badge**：即時呈現系統健康狀態（如綠色 `All Systems Normal` 或黃色 `Alerting`）。
- **Vault KMS Badge**：指示目前 Session Vault KMS 加密狀態（如 `Vault: KMS (AES-256-GCM)`）。
- **K8s Badge**：指示目前執行環境是否位於 Kubernetes 叢集內部（`Platform: K8s/Helm Ready`）。
- **OTLP Badge**：指示 OpenTelemetry OTLP Batch Span Exporter 狀態（`OTLP: Ready`）。
- **身分與角色切換區塊**：可於 `Identity / RBAC (身份認證與角色權限)` 快速切換 `creator`、`approver`、`operator`、`admin` 四大角色測試權限隔離。

---

## 完整人工測試流程（Step-by-Step UI Guide）

### 步驟 1：建立帶有優先權、錄影與 KMS Session 保存之任務（Create Task）
1. 開啟頁面後，捲動至左側中段的 **`Create Task (建立任務)`** 卡片。
2. 於 `Scenario` 下拉選單選擇 `Normal planner task`。
3. 檢查或自訂 JSON Payload（設定 `priority: 2` 急件、錄影開關與 Session 名稱）：
   ```json
   {
     "title": "Portal Inspection & Capture",
     "instructions": "Navigate to portal and inspect dashboard.",
     "priority": 2,
     "risk_level": "low",
     "metadata": {
       "start_url": "https://example.com",
       "domains": ["example.com"],
       "record_video": true,
       "save_session_as": "admin_session"
     }
   }
   ```
4. 點擊深綠色的 **`Create task`** 按鈕。

### 步驟 2：觀察待審核狀態與審批按鈕啟用
1. 任務建立成功後，左下角的 **`Recent Tasks (近期任務)`** 列表頂部會出現這筆新任務，狀態標籤顯示為黃色的 **`PENDING_APPROVAL`**。
2. 點選該任務，右上方 **`Task Detail (任務詳情)`** 會更新其任務詳情。
3. 此時，右上角的 **`Approve selected`** 按鈕會**立即由灰色鎖定狀態切換為亮綠色啟用狀態**（滑鼠懸停顯示「Click to approve this task」）。

### 步驟 3：人工審批與多優先佇列分流觀察（Priority Queues）
1. 點擊右上角亮綠色的 **`Approve selected`** 按鈕進行審核。
2. 任務狀態會即時躍遷：`queued` ➜ `executing`。
3. 檢視左側的 **`Queues & Worker Pools (佇列與工作進程池)`** 卡片：
   - 由於設定了 `priority: 2`（大於 0），任務自動被路由分流至 **`agent.tasks.high`** 高優先權主題。
   - 卡片中顯示 `High Priority: agent.tasks.high`，驗證佇列分流與急件保障機制。

### 步驟 4：瀏覽器即時畫面 WebSocket 廣播串流與線上中斷（Live Stream & Abort）
1. 當任務狀態處於 `executing` 時，右側的 **`Live Screen Broadcast (WebSocket Telemetry) (即時畫面廣播)`** 卡片自動建立 WebSocket 連線（`WS /v1/tasks/{id}/live-stream`）。
2. 卡片中的即時畫布將以低延遲（2 FPS）平滑廣播當前 Playwright 瀏覽器的即時網頁畫面與操作事件。
3. **線上緊急中斷測試**：
   - 若任務仍在執行中，卡片右上角紅色的 **`Abort Execution`** 按鈕呈亮紅可用狀態。
   - 點選 **`Abort Execution`**，系統呼叫 `POST /v1/tasks/{id}/abort`。
   - Worker 即刻捕獲中斷信號，安全釋放 Playwright 上下文，任務狀態即時轉為 **`ABORTED`**，防止失控或陷入死循環。

### 步驟 5：驗證啟發式選擇器自我修復（Heuristic Self-Healing）
1. 當任務因目標網頁 UI 改版而導致原始 CSS/XPath 選擇器失效時，系統自動啟動三級 Fallback Cascade。
2. 任務完成後，檢視右側 **`Visual Step Replay & Replay Timeline (可視化步驟回放與時間軸)`**。
3. 若發生選擇器自癒，步驟分頁標籤上將顯著標註綠色 **`⚡ Self-Healed`** 徽章。
4. 點選該步驟，左側 **`Step Details (步驟詳情)`** 將顯示自癒歷程：包含原始失效選擇器、修復後選擇器、策略（如 `fallback`）與修復後的 target。

### 步驟 6：驗證全行程視訊錄影播放（Full Video Replay）
1. 若任務啟用錄影，右上方會顯示 **`Full WebM Video Recording (Playwright) (全行程 WebM 錄影視訊)`** 播放器卡片。
2. 播放器自動掛載 WebM 視訊來源（端點為 `/v1/artifacts/{video_artifact_id}/content`）。
3. 點擊播放按鈕，即可全螢幕或在卡片內觀看 Playwright 瀏覽器操作過程的動態錄影，支援暫停、播放與拖曳進度條。

### 步驟 7：驗證 Session Vault KMS 信封加密與一鍵 Validate / Revoke
1. 檢視右下側的 **`Session Vault (Storage State) (工作階段保險箱)`** 卡片。
2. 點擊 **`Refresh`** 載入所有已保存的 `storage_state` 憑證（包含步驟 1 保存之 `admin_session`）。
3. 每筆憑證均標註 KMS 加密保護標籤（例如 `KMS (AES-256-GCM)`）。
4. **一鍵解密完整性校驗**：點擊該憑證旁的 **`Validate`** 按鈕。
   - 系統即刻呼叫 `POST /v1/sessions/{name}/validate`，執行 KMS 解密迴路與 AAD 租戶完整性校驗。
   - 驗證成功彈出提示，報告有效 Cookies 數量與加密詳情。
5. **一鍵強制撤銷**：點選 **`Revoke`** 按鈕確認撤銷。狀態立即更新為 **`revoked`**，後續任務不再重用該憑證。

### 步驟 8：驗證定時巡檢排程調度（Scheduled Tasks）
1. 檢視右側中段的 **`Scheduled Tasks (Cron Engine) (定時排程任務)`** 卡片。
2. 展開 **`+ Create New Scheduled Task (+ 建立新定時排程)`**，設定名稱為 `Daily Portal Health Check`，Cron 為 `0 9 * * *`。
3. 列表會列出新排程及其下次預計觸發時間（Next Run）。
4. **手動立即觸發**：在列表中點選該排程項目旁的 **`Run Now`**。系統立即派發出全新關聯任務，顯示於 Recent Tasks 列表中。

### 步驟 9：驗證端到端分散式追蹤與 OTLP 串流（Trace Inspector & OTLP）
1. 在 Task Detail 或 Replay 標題旁，複製該任務的 **`Trace ID`**（32 碼十六進位字串）。
2. 捲動至左側的 **`Observability`** 區塊，找到 **`Trace Inspector`** 輸入框。
3. 貼上 Trace ID 並點擊 **`Lookup`** 按鈕。
4. 下方將展開完整的 Span 樹狀追蹤圖，清晰展示 API 進入點、Kafka 發布、Worker 執行以及各瀏覽器步驟的執行耗時與狀態。

### 步驟 10：驗證告警中心與按鈕互動反饋（Alerting & Actions）
1. **重新整理反饋**：點擊右上角的 **`Refresh`** 按鈕，按鈕會即時切換為 `Refreshing...` ➜ `Refreshed ✓`，並重新載入所有最新指標。
2. **註冊技能反饋**：點擊右上角的 **`Register built-in skills`** 按鈕，按鈕會切換為 `Registering...` ➜ `Registered ✓`。
3. **測試告警通道派發**：在左側 **`Production Alerting Center`** 卡片中，點擊 **`Test Dispatch`** 按鈕，輸入測試備註後確認，系統將發送非阻塞測試 Webhook。

### 步驟 11：驗證 Enterprise OIDC SSO 登入與角色隔離（Identity & RBAC）
1. 點擊頂部藍色的 **`SSO Login (OIDC)`** 按鈕，系統將自動導向 IdP 授權端點（攜帶 PKCE 參數），授權成功後自動導回並寫入 HttpOnly `ba_session` Cookie。
2. 在頂部 Identity 區塊切換身分角色（`creator`, `approver`, `operator`, `admin`）。
3. 切換為 `operator` 嘗試建立任務：系統阻擋並回應 `403 Forbidden`。
4. 切換為 `creator` 嘗試審批任務：審批按鈕禁用或回應 `403 Forbidden`。
5. 切換為 `operator` 嘗試點擊 Session Vault 的 Revoke 按鈕：系統阻擋並回應 `403 Forbidden`（撤銷強制需要 admin）。

---

## 常見 UI 疑問與機制說明（FAQ）

### Q1：右上角的 `Approve selected` 按鈕是灰色的，點不下去是正常的嗎？
**答：完全正常！這是系統安全防護設計。**
- `Approve selected` 專門用於審批狀態為 **`pending_approval`（待審核）** 的任務。
- 當尚未選中任務，或目前選中的任務已經是 **`COMPLETED`**、`FAILED`、`QUEUED` 時，系統會自動禁用（disabled 變灰）該按鈕，避免維運人員對非審批中任務重複點擊核准。

### Q2：`Live Telemetry Stream` 畫面何時會動態推播？
**答：**
- 只有當任務處於 **`executing`（執行中）** 狀態，且維運人員於左側選中該任務時，前端才會向 `WS /v1/tasks/{id}/live-stream` 建立 WebSocket 連線並以 2 FPS 渲染當前網頁畫面。
- 當任務完成、失敗或中止後，畫布會鎖定在最後畫面幀並顯示相應狀態標籤。

### Q3：`Abort Task` 按鈕為什麼有時是灰色的？
**答：**
- `Abort Task` 僅在選中狀態為 `executing` 的執行中任務時亮紅啟用。任務一旦完成、中斷或尚未開始執行，按鈕自動鎖定，防止發送無效的中止指令。

### Q4：綠色 `Self-Healed ✓` 標籤出現的時機？
**答：**
- 只有當任務在執行過程中，初始 CSS/XPath 選擇器失效，且啟發式自癒引擎藉由語意標籤或文字特徵比對成功找到替代元素時，才會記錄自癒事件並在步驟中顯示綠色徽章。如果原本選擇器直接執行成功，則不會觸發自癒，也不會出現該標記。

### Q5：Session Vault 的 `Validate` 按鈕在做什麼？
**答：**
- 點選 `Validate` 會透過後端 KMS 加密引擎即時執行解密迴路，驗證該 Storage State 的 AES-256-GCM 驗證標籤與租戶 AAD 是否相符，並解析校驗 Cookie 的結構完整性，讓維運人員在派發重要巡檢前預先確認免登入憑證依然有效。

---

## 最小合格檢查清單（Checklist）

- [ ] 頁面頂部顯示 `Browser Agent Operations Center (V1.3)`，右上角帶有 `SSO Login (OIDC)` 按鈕、`Alert Badge`、`K8s Badge` 與 `OTLP Badge`。
- [ ] `Priority Queues Telemetry` 卡片可顯示 High、Queued、Batch 深度與 Worker Pool 狀態。
- [ ] `KMS Envelope Encryption Engine` 卡片顯示 Provider（local/aws_kms/vault）、Key ID 與加解密迴路延遲。
- [ ] `Live Telemetry Stream` 畫布於任務執行時可連線並流暢渲染畫面幀，支援點選 `Abort Task` 中斷任務。
- [ ] `Visual Step Replay` 於自癒情境可正確顯示綠色 `Self-Healed ✓` 徽章與自癒歷程。
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

可在 PowerShell 中直接執行以下腳本，一鍵驗證 V1.3 核心端點：

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

# 2. 檢查 V1.3 KMS 狀態、優先佇列與 7 大告警
Invoke-RestMethod -Method Get -Uri http://127.0.0.1:8000/v1/ops/kms/status -Headers $opHeaders
Invoke-RestMethod -Method Get -Uri http://127.0.0.1:8000/v1/ops/queues -Headers $opHeaders
Invoke-RestMethod -Method Get -Uri http://127.0.0.1:8000/v1/ops/alerts -Headers $opHeaders

# 3. 建立高優先權急件任務（Priority > 0）
$taskBody = @{
    title = "High Priority Inspection"
    instructions = "Navigate to allowlisted site and capture screenshot"
    priority = 2
    risk_level = "low"
    metadata = @{
        domains = @("example.com")
        start_url = "https://example.com"
        record_video = $true
        save_session_as = "v13_test_session"
    }
} | ConvertTo-Json
$task = Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/v1/tasks -Headers $creatorHeaders -ContentType "application/json" -Body $taskBody

# 4. Approver 核准任務
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/v1/tasks/$($task.task_id)/approve" -Headers $approverHeaders

# 5. 等待 Worker 執行完成
Start-Sleep -Seconds 6

# 6. 檢驗 Session Vault KMS 憑證完整性與一鍵撤銷
Invoke-RestMethod -Method Get -Uri "http://127.0.0.1:8000/v1/sessions/v13_test_session/validate" -Headers $opHeaders
Invoke-RestMethod -Method Delete -Uri "http://127.0.0.1:8000/v1/sessions/v13_test_session" -Headers $adminHeaders

Write-Host "V1.3 API Verification Completed Successfully!" -ForegroundColor Green
```
