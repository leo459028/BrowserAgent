# V1.2 Operations Center Manual Test

本文件說明如何手動驗證 BrowserAgent V1.2 Operations Center。

## 啟動

```powershell
docker compose up -d --build
```

開啟：

```text
http://127.0.0.1:8000/operations
```
> **提示**：系統具備自動容錯轉址，無論輸入 `http://localhost:8000/operations`、`http://localhost:8000/operation` 或首頁根路徑 `http://localhost:8000/`，皆會自動重定向至 Operations Center。

## 完整人工測試流程（Step-by-Step UI Guide）

以下提供維運人員與測試工程師在瀏覽器中進行 V1.2 完整人工功能測試的標準步驟：

### 步驟 1：建立帶有錄影與 Session 儲存的任務（Create Task）
1. 開啟頁面後，將頁面捲動至左側中段的 **`Create Task`** 卡片。
2. 於 `Scenario` 下拉選單選擇 `Normal planner task`。
3. 檢查或自訂 JSON Payload（可包含錄影開關與 Session 名稱）：
   ```json
   {
     "title": "Portal Inspection & Capture",
     "instructions": "Navigate to portal and inspect dashboard.",
     "priority": 1,
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
1. 任務建立成功後，左下角的 **Recent Tasks** 列表頂部會出現這筆新任務，狀態標籤顯示為黃色的 **`PENDING_APPROVAL`**。
2. 點選該任務，右上方 Task Detail 會更新其任務詳情。
3. 此時，右上角的 **`Approve selected`** 按鈕會**立即由灰色鎖定狀態切換為亮綠色啟用狀態**（滑鼠懸停顯示「Click to approve this task」）。

### 步驟 3：執行人工審核與觀察執行流程
1. 點擊右上角亮綠色的 **`Approve selected`** 按鈕進行審核。
2. 任務狀態會即時躍遷：`queued` ➜ `executing`。
3. 背景的 Worker 將消費 Kafka 訊息並啟動 Playwright 瀏覽器訪問網頁並錄製視訊。約 3~8 秒後，任務狀態自動更新為綠色的 **`COMPLETED`**。
4. 此時由於任務已執行完畢，右上角的 `Approve selected` 按鈕會**自動恢復為灰色鎖定狀態**，防止重複審查。

### 步驟 4：驗證視覺化步驟回放（Visual Step Replay）
1. 任務完成後，檢視右側的 **`Visual Step Replay & Replay Timeline`** 區塊。
2. 上方會載入步驟分頁按鈕，例如 `[Step 1: goto ✓]` 與 `[Step 2: screenshot ✓]`。
3. 點擊 **`Step 2: screenshot`** 分頁標籤：
   - **左側步驟詳情**：顯示動作類型（`screenshot`）、耗時毫秒（例如 `598.8 ms`）、對應的 Span ID 與 DOM 摘要。
   - **右側截圖預覽**：直接呈現該步驟所捕獲的網頁畫面縮圖，點擊縮圖可在新分頁開啟完整高解析度原圖。
4. 點擊下方折疊的 `▶ Raw Timeline Events`，可查閱包含審計紀錄、步驟與評估結果之向後相容時間線。

### 步驟 5：驗證全行程視訊錄影播放（Full Video Replay）
1. 若任務指定或系統啟用錄影，右上方會顯示 **`Execution Video Recording`** 播放器卡片。
2. 播放器自動掛載 WebM 視訊來源（端點為 `/v1/tasks/{task_id}/video`）。
3. 點擊播放按鈕，即可全螢幕或在卡片內觀看 Playwright 瀏覽器操作過程的動態錄影，支援暫停、播放與拖曳進度條。

### 步驟 6：驗證工作階段保險箱治理與一鍵撤銷（Session Vault）
1. 檢視左側的 **`Session Vault`** 卡片。
2. 點擊 **`Refresh Sessions`** 載入所有已保存的 `storage_state` 憑證（包含剛剛步驟 1 儲存之 `admin_session`）。
3. **免登入復用**：建立新任務時在 metadata 指定 `"session_name": "admin_session"`，Worker 將自動注入該工作階段，實現跨任務免重複登入。
4. **一鍵強制撤銷**：點選特定 Session 旁的 **`Revoke`** 按鈕確認撤銷。
5. 狀態立即更新為 **`Revoked`**，後續任務不再注入該憑證，並自動寫入 `session.revoked` 審計日誌。

### 步驟 7：驗證定時巡檢排程調度（Scheduled Tasks）
1. 捲動至左側的 **`Scheduled Tasks`** 卡片。
2. 點擊 **`Create Schedule`**，設定名稱為 `Daily Portal Health Check`，Cron 為 `0 9 * * *`。
3. 列表會列出新排程及其下次預計觸發時間（Next Run）。
4. **手動立即觸發**：在列表中點選該排程項目，點擊 **`Run Now`**。系統立即派發出全新關聯任務，顯示於 Recent Tasks 列表中，驗證手動觸發功能。
5. **暫停與恢復**：點選 **`Pause`** 按鈕可將排程暫停（切換為 Inactive），再次點選 **`Resume`** 恢復啟用。

### 步驟 8：驗證端到端分散式追蹤與 OTLP 串流（Trace Inspector & OTLP）
1. 在 Task Detail 或 Replay 標題旁，複製該任務的 **`Trace ID`**（32 碼十六進位字串）。
2. 捲動至左側的 **`Observability`** 區塊，找到 **`Trace Inspector`** 輸入框。
3. 貼上 Trace ID 並點擊 **`Lookup`** 按鈕。
4. 下方將展開完整的 Span 樹狀追蹤圖，清晰展示 API 進入點、Kafka 發布、Worker 執行以及各瀏覽器步驟的執行耗時與狀態。
5. 頁面頂部的 **`OTLP Stream Badge`** 顯示當前 Batch Span 隊列狀態，背景非同步推送到外部 APM。

### 步驟 9：驗證告警中心與按鈕互動反饋（Alerting & Actions）
1. **重新整理反饋**：點擊右上角的 **`Refresh`** 按鈕，按鈕會即時切換為 `Refreshing...` ➜ `Refreshed ✓`，並重新載入所有最新指標。
2. **註冊技能反饋**：點擊右上角的 **`Register built-in skills`** 按鈕，按鈕會切換為 `Registering...` ➜ `Registered ✓`，並於 Create Task 下方顯示註冊完成提示。
3. **測試告警通道派發**：在左側 **`Production Alerting Center`** 卡片中，點擊 **`Test Dispatch`** 按鈕，輸入測試備註後確認，系統將發送非阻塞測試 Webhook 並顯示派發審計紀錄。

### 步驟 10：驗證角色切換與權限隔離（Identity & RBAC）
1. 在頂部 Identity 區塊切換身分角色（`creator`, `approver`, `operator`, `admin`）。
2. 切換為 `operator` 嘗試建立任務：系統阻擋並回應 `403 Forbidden`（建立僅限 creator 或 admin）。
3. 切換為 `creator` 嘗試審批任務：審批按鈕禁用或回應 `403 Forbidden`（審批僅限 approver 或 admin）。
4. 切換為 `operator` 嘗試點擊 Session Vault 的 Revoke 按鈕：系統阻擋並回應 `403 Forbidden`（撤銷憑證強制需要 admin）。

---

## 常見 UI 疑問與機制說明（FAQ）

### Q1：右上角的 `Approve selected` 按鈕是灰色的，點不下去是正常的嗎？
**答：完全正常！這是系統安全防護設計。**
- `Approve selected` 專門用於審批狀態為 **`pending_approval`（待審核）** 的任務。
- 當尚未選中任務，或目前選中的任務已經是 **`COMPLETED`（已完成）**、`FAILED`、`QUEUED` 時，系統會自動禁用（disabled 變灰）該按鈕，避免維運人員對已經執行完成的任務重複點擊核准。

### Q2：右上角的 `Refresh` 與 `Register built-in skills` 按鈕點擊後沒有彈窗？
**答：按鈕均具備就地互動文字反饋與背景非同步處理機制。**
- 點擊 `Refresh` 會觸發全面背景重新拉取，按鈕文字會切換為 `Refreshing...` ➜ `Refreshed ✓`。
- 點擊 `Register built-in skills` 會在後端註冊同租戶 SkillHub 技能，完成後按鈕切換為 `Registered ✓`。

### Q3：為什麼有時看不到 Video 播放器卡片？
**答：視任務設定而定。**
- 只有當任務在建立時包含 `"record_video": true`（或系統設定預設啟用錄影），且 Worker 成功產出 WebM 視訊 Artifact 時，播放器卡片才會自動載入並呈現。
- 若任務未啟用錄影或執行失敗未產生視訊，播放器會呈現佔位提示或隱藏。

### Q4：Scheduled Tasks 的 `Run Now` 與背景 Cron 自動派發有何差異？
**答：**
- **`Run Now`**：手動立即觸發，不受 Cron 表達式時間限制，適合維運人員隨時進行即時巡檢測試。
- **背景 Cron 派發**：每分鐘由背景排程器搶佔 Redis 分散式鎖，比對 Cron 時間到期後自動派發。
- 兩者皆遵循相同的並行原則（`concurrency_policy: skip`）與網域白名單安全檢查。

### Q5：Session Vault 撤銷後會發生什麼事？
**答：**
- 點選 `Revoke` 後，該 Session 的狀態會被標記為 `revoked`，並記錄至審計日誌。
- 即使後續任務指定載入該工作階段名稱，系統也會忽略該憑證，強制 Playwright 重新執行完整登入流程，避免過期或遭洩漏的憑證持續被重用。

---

## 最小合格檢查清單（Checklist）

- [ ] 頁面頂部顯示 `Browser Agent v1.2 Operations Center`，右上角帶有 `System Alert Badge`、`K8s Badge` 與 `OTLP Badge`。
- [ ] `Production Alerting Center` 可載入，顯示 7 大規則狀態指標與 Webhook 指示燈。
- [ ] 管理員點選 `Test Dispatch Webhook` 可觸發測試推播與成功提示。
- [ ] `Scheduled Tasks` 卡片可顯示排程列表，支援建立排程、`Run Now` 立即派發與 `Pause/Resume` 暫停恢復。
- [ ] `Session Vault` 卡片可查閱儲存之 Storage State 工作階段憑證，支援一鍵 `Revoke` 撤銷憑證。
- [ ] `Trace Inspector` 輸入任一任務的 Trace ID，點選 `Inspect Trace` 可展開階層式 Spans 追蹤樹。
- [ ] `Operations Readiness` 與 `Production Readiness` 正確顯示，包含 K8s 與 OTLP 區塊。
- [ ] `Artifact Backend` 在 Docker Compose 顯示 `s3`。
- [ ] `Identity / RBAC` 可切換角色（creator, approver, operator, admin）。
- [ ] `Try operator create` 顯示 `403`。
- [ ] `Normal planner task` 可建立（pending_approval）、核准（queued）、完成（completed）。
- [ ] 右側 `Visual Step Replay` 顯示步驟分頁標籤（Step 1, Step 2 ...），點選即時預覽步驟耗時、DOM 摘要與截圖縮圖。
- [ ] 右側 `Execution Video Recording` 播放器可加載並播放 WebM 瀏覽器操作錄影。
- [ ] 下方折疊 `Replay Timeline` 完整保留歷史 audit 與步驟時間線。
- [ ] `Refresh DLQ` 可查 failed tasks，`Bulk DLQ replay` 可操作 non-quarantined tasks。

---

## API 快速自動化檢查（PowerShell 腳本）

若需要透過命令列快速驗證 V1.2 核心流程，可在 PowerShell 中直接貼上執行以下腳本：

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

# 2. 檢查系統 Readiness、7 大維運告警與 OTLP 狀態
Invoke-RestMethod -Method Get -Uri http://127.0.0.1:8000/v1/ops/readiness -Headers $opHeaders
Invoke-RestMethod -Method Get -Uri http://127.0.0.1:8000/v1/ops/alerts -Headers $opHeaders
Invoke-RestMethod -Method Get -Uri http://127.0.0.1:8000/v1/ops/otlp/status -Headers $opHeaders

# 3. 建立帶有全行程錄影與 Session 保存之任務
$taskBody = @{
    title = "API Smoke Test"
    instructions = "Navigate to allowlisted site and capture screenshot"
    priority = 1
    risk_level = "low"
    metadata = @{
        domains = @("example.com")
        start_url = "https://example.com"
        record_video = $true
        save_session_as = "api_test_session"
    }
} | ConvertTo-Json
$task = Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/v1/tasks -Headers $creatorHeaders -ContentType "application/json" -Body $taskBody

# 4. Approver 核准任務
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/v1/tasks/$($task.task_id)/approve" -Headers $approverHeaders

# 5. 等待 Worker 執行完成
Start-Sleep -Seconds 6

# 6. 檢查 Visual Replay、視訊串流與跨進程 Traces
$replay = Invoke-RestMethod -Method Get -Uri "http://127.0.0.1:8000/v1/tasks/$($task.task_id)/replay" -Headers $opHeaders
$trace = Invoke-RestMethod -Method Get -Uri "http://127.0.0.1:8000/v1/ops/traces/$($task.correlation_id)" -Headers $opHeaders

# 7. 建立定時巡檢排程並立即手動觸發
$schedBody = @{
    name = "Daily API Inspection"
    cron_expression = "0 9 * * *"
    concurrency_policy = "skip"
    is_active = $true
    task_template = @{
        title = "Scheduled Inspection"
        instructions = "Health check"
        risk_level = "low"
        metadata = @{ start_url = "https://example.com"; domains = @("example.com") }
    }
} | ConvertTo-Json
$sched = Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/v1/scheduled-tasks -Headers $creatorHeaders -ContentType "application/json" -Body $schedBody
$runRes = Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/v1/scheduled-tasks/$($sched.id)/run" -Headers $opHeaders

# 8. 查詢 Session Vault 與一鍵撤銷
$sessions = Invoke-RestMethod -Method Get -Uri http://127.0.0.1:8000/v1/sessions -Headers $opHeaders
Invoke-RestMethod -Method Delete -Uri "http://127.0.0.1:8000/v1/sessions/api_test_session" -Headers $adminHeaders
```
